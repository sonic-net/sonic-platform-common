//! Phase 1: a Rust daemon reaching a vendor's Python platform API.
//!
//! [`Bridge`] holds one Python object -- the facade -- and nothing else. The
//! per-method bodies are generated; what is written by hand here is the error
//! mapping and the four attribute readers, because those are decisions rather
//! than projections of the stub.

use platform_api::{Number, PlatformError};
use pyo3::exceptions::PyNotImplementedError;
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyInt, PyString};

// The generator's output, held byte for byte to what `generate.py --check`
// regenerates: rustfmt leaves it as written.
#[rustfmt::skip]
mod generated;

/// The generated facade's module: where `PlatformApi` and `DeviceNotFound` live.
const FACADE_MODULE: &str = "sonic_platform_api.facade";

/// The hand-written half of the facade: where the vendor's shutdown handlers
/// are kept for `notify_shutdown()`.
const HATCH_MODULE: &str = "sonic_platform_api._escape_hatch";

/// A Rust handle on `sonic_platform_api.facade.PlatformApi`.
pub struct Bridge {
    facade: Py<PyAny>,
}

impl Bridge {
    /// Build a facade over the vendor's chassis.
    ///
    /// The vendor package is named by the caller rather than imported here:
    /// which `sonic_platform` is installed is a property of the image, and
    /// hard-coding it would stop the tests driving this over a mock.
    /// `syslog_ident` becomes `sys.argv[0]`.  That is where
    /// `sonic_py_common.logger.Logger` takes its syslog identifier from when
    /// the caller passes none, and the vendor packages never pass one.  An
    /// embedded interpreter starts with `sys.argv` empty, so without this every
    /// line the vendor's Python logs arrives tagged `pmon#:` -- unreadable in
    /// syslog, and invisible to the `pmon#<daemon>` patterns sonic-mgmt's
    /// loganalyzer matches on.  Pass the same identifier the daemon logs under.
    ///
    /// The process's SIGTERM and SIGINT dispositions are the same afterwards
    /// as before, whatever the vendor's import and constructor installed (see
    /// [`ShutdownSignals`]), so a daemon may install its own handlers before
    /// building a bridge or after.  What the vendor installed in Python is
    /// kept, not run: the daemon hands it the shutdown with
    /// `notify_shutdown()` (see [`release_python_signal_handlers`]).
    pub fn new(vendor_module: &str, syslog_ident: &str) -> Result<Self, PlatformError> {
        Python::with_gil(|py| {
            py.import("sys")
                .and_then(|sys| sys.setattr("argv", vec![syslog_ident]))
                .map_err(|e| err(py, e))?;
            // Put back on every way out of here, the failed ones included.
            let mut signals = ShutdownSignals::save();
            let hatch = py.import(HATCH_MODULE).map_err(|e| err(py, e))?;
            // A handler the vendor installs while its chassis is built then
            // chains to a no-op, not to `SIG_DFL`.  False off the main thread.
            let armed = hatch
                .call_method0("arm_shutdown_capture")
                .and_then(|v| v.is_truthy())
                .unwrap_or(false);
            let chassis = py
                .import(vendor_module)
                .and_then(|m| m.getattr("Platform"))
                .and_then(|p| p.call0())
                .and_then(|p| p.call_method0("get_chassis"));
            if armed && chassis.is_ok() {
                let _ = hatch.call_method0("capture_shutdown_handlers");
            }
            release_python_signal_handlers(py);
            if armed {
                // After the reset: `signal.signal()` runs what is pending first.
                signals.deferred = hatch
                    .call_method0("disarm_shutdown_capture")
                    .and_then(|v| v.extract())
                    .unwrap_or_default();
            }
            drop(signals);
            let chassis = chassis.map_err(|e| err(py, e))?;
            let facade = py
                .import(FACADE_MODULE)
                .and_then(|m| m.getattr("PlatformApi"))
                .and_then(|c| c.call1((chassis,)))
                .map_err(|e| err(py, e))?;
            Ok(Bridge {
                facade: facade.unbind(),
            })
        })
    }

    /// Wrap a facade the caller already has.  Used by the tests, and by
    /// anything that needs a chassis this crate did not construct.
    pub fn from_facade(facade: Py<PyAny>) -> Self {
        Bridge { facade }
    }
}

/// Run the interpreter's `atexit` handlers before the process goes away.
///
/// A Python daemon exits through `sys.exit()`, so CPython finalisation runs
/// whatever the vendor registered with `atexit`.  A Rust daemon exits through
/// `std::process::exit()`, which finalises nothing -- so those handlers are
/// silently skipped, and every one of them is cleanup the vendor expected to
/// happen.
///
/// This is not hypothetical.  mlnx's `thermal_updater.py:92` registers
/// `clean_thermal_data` this way; it removes `/run/hw-management/thermal/asic`
/// and the per-module thermal links.  Measured on one switch: after stopping
/// the Python daemon the file is gone, after stopping the Rust one it is still
/// there, stale, with nothing updating it.  Nothing else in either daemon
/// touches those paths -- `ThermalManager.deinitialize()` only stops the timer
/// and re-suspends hw-management-tc, and `unlink_hw_mgmt_thermal_files()` runs
/// at start-up and only on SPC1.
///
/// `atexit._run_exitfuncs()` rather than `Py_FinalizeEx()`: it runs exactly the
/// handlers and nothing else.  Full finalisation would also tear down every
/// extension module the vendor imported, which is a much larger promise to keep
/// on a code path that runs while the switch is being shut down.
///
/// Idempotent -- CPython clears each callback as it runs it -- and best-effort,
/// because failing to clean up must not stop the daemon exiting.
pub fn run_python_atexit_handlers() {
    Python::with_gil(|py| {
        match py
            .import("atexit")
            .and_then(|m| m.call_method0("_run_exitfuncs"))
        {
            Ok(_) => {}
            Err(e) => {
                let msg = e.to_string();
                // Nowhere to log to from this crate, and the daemon is on its
                // way out; say it where a stderr-to-syslog pipe will catch it.
                eprintln!("atexit handlers failed during shutdown: {msg}");
                let _ = py;
            }
        }
    });
}

/// Hand the process's shutdown signals back to the caller.
///
/// Constructing a vendor chassis can install Python-level SIGTERM/SIGINT
/// handlers -- mlnx's `Chassis.__init__` calls `utils.watch_shutdown_signals()`
/// (chassis.py:151), which chains onto `signal.getsignal(sig)`.  In a Python
/// daemon that is the daemon's own handler and the chain is harmless.  Here it
/// is `SIG_DFL`, because a Rust handler is installed at the OS level where
/// `getsignal` cannot see it, and the vendor's fallback for `SIG_DFL` is
/// `signal.signal(signum, SIG_DFL); os.kill(os.getpid(), signum)` -- so the
/// first time Rust re-enters Python after SIGTERM, the interpreter runs that
/// at a bytecode boundary and the process dies mid-shutdown.  On hardware that
/// meant `tm_deinitialize()` never ran and hw-management-tc was left driving
/// fans off temperatures nobody was updating any more.
///
/// Resetting the interpreter's table to `SIG_DFL` leaves it with nothing to
/// run: process lifetime belongs to the Rust side, which is the whole
/// arrangement in phase 1.  `signal.signal()` sets the OS-level disposition as
/// well, and [`ShutdownSignals`] then puts that back to what the process had
/// before the vendor was constructed.
///
/// Best-effort on purpose: `signal.signal()` raises off the main thread, and
/// this crate is also constructed from worker threads (thermalctld builds a
/// second bridge for its leak updater).  There it is a no-op that must not turn
/// a working bridge into a failed one -- and it is unnecessary, because the
/// vendor's own installer has the same main-thread guard.
///
/// What the vendor's handler is *for* is not lost with it.  mlnx's sets an
/// event that ends its readiness waits -- the 300 s one in
/// `ThermalUpdater.start()` on SPC1 among them -- and a daemon that never set
/// it sat in that wait at shutdown until supervisord killed it, its STATE_DB
/// rows left behind.  So before the build the table is armed with a no-op
/// (`arm_shutdown_capture()`), the handler the vendor installs on top of it is
/// kept (`capture_shutdown_handlers()`), and the daemon's `notify_shutdown()`
/// runs it: the event is set, and the chain ends in the no-op rather than in
/// `os.kill`.
fn release_python_signal_handlers(py: Python<'_>) {
    let Ok(signal) = py.import("signal") else {
        return;
    };
    let Ok(dfl) = signal.getattr("SIG_DFL") else {
        return;
    };
    for name in ["SIGTERM", "SIGINT"] {
        if let Ok(signum) = signal.getattr(name) {
            let _ = signal.call_method1("signal", (signum, &dfl));
        }
    }
}

/// The OS-level dispositions of SIGTERM and SIGINT, put back when dropped.
///
/// `signal.signal()` is `sigaction()` underneath, so the vendor's installer and
/// [`release_python_signal_handlers`] both replace whatever the process had --
/// including a handler the daemon installed before opening the platform, which
/// would then be gone without a trace: SIGTERM would kill the process outright,
/// without `tm_deinitialize()` or the atexit handlers, the failure the reset
/// exists to prevent.  Saved before the vendor is imported and restored once
/// the interpreter's table is reset, they leave the bridge neutral, so the
/// order a daemon opens the platform and installs its handlers in no longer
/// matters.
///
/// While the chassis is built the interpreter's no-op stands in for the
/// daemon's handler, so a signal sent then reaches the no-op instead.  It is
/// kept in `deferred` and raised again once the daemon's handler is back: a
/// SIGTERM sent during start-up still stops the daemon.
struct ShutdownSignals {
    saved: Vec<(libc::c_int, libc::sigaction)>,
    deferred: Vec<libc::c_int>,
}

impl ShutdownSignals {
    fn save() -> Self {
        let mut saved = Vec::new();
        for sig in [libc::SIGTERM, libc::SIGINT] {
            // SAFETY: an all-zero `sigaction` is a valid value to read into, and
            // a null `act` only reads the current disposition.
            let mut old: libc::sigaction = unsafe { std::mem::zeroed() };
            if unsafe { libc::sigaction(sig, std::ptr::null(), &mut old) } == 0 {
                saved.push((sig, old));
            }
        }
        ShutdownSignals {
            saved,
            deferred: Vec::new(),
        }
    }
}

impl Drop for ShutdownSignals {
    fn drop(&mut self) {
        for (sig, old) in &self.saved {
            // SAFETY: `old` is the disposition the kernel reported for `sig`.
            unsafe { libc::sigaction(*sig, old, std::ptr::null_mut()) };
        }
        for sig in &self.deferred {
            // SAFETY: raising a signal whose disposition was just restored.
            unsafe { libc::raise(*sig) };
        }
    }
}

/// A Python exception, as the platform API spells the same thing.
///
/// `NotImplementedError` is the one that matters: the facade raises it for an
/// action a platform does not implement, and a caller that saw it as a generic
/// backend failure would log an error every polling cycle on hardware that is
/// working exactly as designed.
///
/// `NotFound` is the facade's `DeviceNotFound` -- a key that leads to no
/// device -- and nothing else.  Any `KeyError` used to be, and a vendor getter
/// whose dictionary lookup missed then read as "no such device" rather than
/// as the backend failure it is.
pub(crate) fn err(py: Python<'_>, e: PyErr) -> PlatformError {
    let text = e.value(py).to_string();
    if e.is_instance_of::<PyNotImplementedError>(py) {
        PlatformError::NotSupported(text)
    } else if is_device_not_found(py, &e) {
        PlatformError::NotFound(text)
    } else {
        PlatformError::Backend(text)
    }
}

/// Whether `e` is the facade's `DeviceNotFound`.
///
/// Looked up rather than held: the facade is imported once and then cached by
/// Python, and an error raised before it could be imported is not one.
fn is_device_not_found(py: Python<'_>, e: &PyErr) -> bool {
    py.import(FACADE_MODULE)
        .and_then(|m| m.getattr("DeviceNotFound"))
        .map(|cls| e.value(py).is_instance(&cls).unwrap_or(false))
        .unwrap_or(false)
}

fn attr<'py>(row: &Bound<'py, PyAny>, key: &str) -> Result<Bound<'py, PyAny>, PlatformError> {
    row.getattr(key).map_err(|e| err(row.py(), e))
}

/// A string column, or None.
///
/// The facade has already resolved fallbacks, so a None here means the column
/// is genuinely absent rather than that a name lookup failed.
pub(crate) fn text(row: &Bound<'_, PyAny>, key: &str) -> Result<Option<String>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() {
        return Ok(None);
    }
    let s = v
        .downcast::<PyString>()
        .map_err(|_| PlatformError::Backend(format!("{key} is not a string")))?;
    s.extract().map(Some).map_err(|e| err(row.py(), e))
}

/// The platform API's not-available sentinel is the string "N/A", and vendors
/// return it from methods whose base class declares a number or a bool.  mlnx's
/// `LeakageSensor.is_leak` (liquid_cooling.py:46-57) returns `False`, `True`, or
/// `"N/A"` when the sysfs file cannot be read.
///
/// Extracting that as the declared type fails, and on hardware the failure did
/// not stop at the field: it aborted the whole leak-sensor read, the leak
/// updater logged "leak detection is not running", and LIQUID_COOLING_INFO kept
/// showing `leaking=No` / `leak_sensor_status=Good`.  A broken sensor silently
/// switched off leak detection while the switch reported itself healthy.
///
/// The declared type is `Optional[...]`, and "N/A" is exactly what that option
/// is for, so it reads as absent rather than as an error.
fn is_na(v: &Bound<'_, PyAny>) -> bool {
    v.extract::<String>()
        .map(|s| s.trim().eq_ignore_ascii_case("n/a"))
        .unwrap_or(false)
}

pub(crate) fn flag(row: &Bound<'_, PyAny>, key: &str) -> Result<Option<bool>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() || is_na(&v) {
        return Ok(None);
    }
    v.extract::<bool>().map(Some).map_err(|e| err(row.py(), e))
}

/// A number going the other way: Rust to Python.
///
/// A setter that turned every limit into a float would write 105.0 where the
/// caller said 105, and the platform would store what it was given.
pub(crate) fn int_or_float_arg(py: Python<'_>, t: Number) -> Py<PyAny> {
    match t {
        Number::Int(v) => v.into_pyobject(py).unwrap().into_any().unbind(),
        Number::Float(v) => v.into_pyobject(py).unwrap().into_any().unbind(),
    }
}

/// A reading or a limit, keeping the side of `Union[int, float]` it arrived on.
///
/// Checked int-first, and with bools read as absent: `bool` is a subclass of
/// `int` in Python, so `isinstance(True, int)` is true, `True` extracts as the
/// integer 1 and as the float 1.0 alike, and an unguarded read would turn a
/// flag into the limit `1`.  Excluding bools from the int arm alone is not
/// enough -- the float arm below takes them just as readily -- so a bool is
/// turned away before either arm runs.  A flag where a number is declared is
/// bad data, not the number one; the facade drops it for the same reason, and
/// this guard is for a row that did not come through the facade.
///
/// "N/A" is absent here as it is in `flag` and `num`: a limit the platform
/// could not read is a missing limit, and failing the extraction would take
/// the whole row -- every sensor's limits -- with it.
pub(crate) fn int_or_float(
    row: &Bound<'_, PyAny>,
    key: &str,
) -> Result<Option<Number>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() || is_na(&v) || v.is_instance_of::<PyBool>() {
        return Ok(None);
    }
    if let Ok(i) = v.extract::<i64>() {
        return Ok(Some(Number::Int(i)));
    }
    v.extract::<f64>()
        .map(|f| Some(Number::Float(f)))
        .map_err(|e| err(row.py(), e))
}

/// A column that is a list of rows.
///
/// Takes the reader for the inner row, which is generated, so this stays one
/// function however many nested rows there turn out to be.
pub(crate) fn rows<T>(
    row: &Bound<'_, PyAny>,
    key: &str,
    read: fn(&Bound<'_, PyAny>) -> Result<T, PlatformError>,
) -> Result<Vec<T>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() {
        return Ok(Vec::new());
    }
    let mut out = Vec::new();
    for item in v.try_iter().map_err(|e| err(row.py(), e))? {
        out.push(read(&item.map_err(|e| err(row.py(), e))?)?);
    }
    Ok(out)
}

/// An integer column, narrowed to the width the stub declares.
///
/// An `int` crosses exactly; only a `float` goes through `int_cast`.  Reading
/// every number as f64 first, as this once did, rounded a counter past 2^53
/// to the nearest even value and made `i64::MAX` no reading at all.
pub(crate) fn integer<T: TryFrom<i128>>(
    row: &Bound<'_, PyAny>,
    key: &str,
) -> Result<Option<T>, PlatformError> {
    let v = attr(row, key)?;
    // "N/A" for the same reason as in `num`.
    if is_na(&v) {
        return Ok(None);
    }
    int_of(&v).map_err(|e| err(row.py(), e))
}

/// A value narrowed to `T`, as `integer` narrows a column: None for None, an
/// `int` exactly, and anything else through its float.  What an action
/// answering an integer is read with.
pub(crate) fn int_of<T: TryFrom<i128>>(v: &Bound<'_, PyAny>) -> PyResult<Option<T>> {
    if v.is_none() {
        return Ok(None);
    }
    if v.is_instance_of::<PyInt>() {
        // An `int` no i128 holds is one no declared width holds either.
        return Ok(v.extract::<i128>().ok().and_then(|i| T::try_from(i).ok()));
    }
    Ok(int_cast(v.extract::<f64>()?))
}

/// A float narrowed to the integer width the stub declares.
///
/// Truncates toward zero, as `as` would: a vendor reporting `50.7` for a
/// percentage means fifty, and that is what a Python daemon formatting it with
/// `int()` publishes.  What `as` gets wrong is everything else -- it
/// saturates, so `-1` becomes a `u32` 0, `NaN` becomes 0, and `1e12` becomes
/// `u32::MAX`, each a plausible reading nobody took.  A fan reporting `-1`
/// for "could not read" would cross as a stopped fan.
///
/// None rather than an error, for the reason `num` reads "N/A" as None: a
/// value that cannot be the declared quantity is a reading the platform could
/// not take, and the columns this reads are `Optional` for exactly that.  An
/// error would take the whole row -- and with it the snapshot -- for one bad
/// column, which is the failure `is_na` exists to stop.  A non-optional
/// column falls back to its declared default, and a non-optional return
/// value reports the absence as an error where it is unwrapped.
pub(crate) fn int_cast<T: TryFrom<i128>>(v: f64) -> Option<T> {
    if !v.is_finite() {
        return None;
    }
    // `as i128` saturates too, but at bounds no 64-bit target can hold, so a
    // value too large for any of them still fails the `try_from` below.
    T::try_from(v.trunc() as i128).ok()
}

// ── Tests ─────────────────────────────────────────────────────────────────────
//
// The bridge against a real facade lives in tests/bridge_test.rs.  What is here
// is what cannot be reached through one: column shapes the facade never
// produces -- a None list, a bool or "N/A" where a limit belongs, which the
// facade drops before they cross -- the integer narrowing on its own, and a
// shutdown step whose whole effect is on the interpreter.

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::ffi::c_str;
    use pyo3::types::PyModule;

    /// A `None` where a list of rows belongs is an empty list, not an error.
    ///
    /// The facade always builds a list, so this branch is not reachable through
    /// it -- which is exactly why it is worth pinning: a platform object handed
    /// straight to a reader, as a future vendor crate would do, has no such
    /// guarantee, and reading `None` as a failure would drop the whole outer
    /// row rather than the one column.
    #[test]
    fn a_column_that_is_none_where_rows_belong_is_no_rows() {
        Python::with_gil(|py| {
            let m = PyModule::from_code(
                py,
                c_str!("class R:\n    events = None\nROW = R()\n"),
                c_str!("none_rows.py"),
                c_str!("none_rows"),
            )
            .unwrap();
            let row = m.getattr("ROW").unwrap();
            let got = rows(&row, "events", |_| Ok(0u8)).unwrap();
            assert!(got.is_empty());
        });
    }

    /// A row object no facade has touched: one attribute per case.
    fn raw_row(py: Python<'_>) -> Bound<'_, PyAny> {
        PyModule::from_code(
            py,
            c_str!(
                r#"
class R:
    yes = True
    no = False
    na = 'N/A'
    na_spaced = ' n/a '
    whole = 105
    real = 105.0
    word = 'hot'
    past_f64 = 9007199254740993
    i64_max = 9223372036854775807
    past_i64 = 9223372036854775808
    past_i128 = 2 ** 200
    half = 50.7
    nothing = None
ROW = R()
"#
            ),
            c_str!("raw_row.py"),
            c_str!("raw_row"),
        )
        .unwrap()
        .getattr("ROW")
        .unwrap()
    }

    /// A bool is not a limit, on either side of the union.
    ///
    /// The old guard only kept `True` out of the int arm; the float arm took
    /// it as 1.0, so a flag where a limit belongs crossed as the threshold 1
    /// -- the very thing the guard's comment said could not happen.  `False`
    /// would have crossed as 0.0, a limit every reading is above.
    #[test]
    fn a_bool_where_a_limit_belongs_is_no_limit_at_all() {
        Python::with_gil(|py| {
            let row = raw_row(py);
            assert_eq!(int_or_float(&row, "yes").unwrap(), None);
            assert_eq!(int_or_float(&row, "no").unwrap(), None);
        });
    }

    /// "N/A" is a limit the platform could not read, as it is a reading for
    /// `num` and a flag for `flag`; failing it would fail the whole row.
    #[test]
    fn a_limit_reported_as_na_is_absent_rather_than_an_error() {
        Python::with_gil(|py| {
            let row = raw_row(py);
            assert_eq!(int_or_float(&row, "na").unwrap(), None);
            assert_eq!(int_or_float(&row, "na_spaced").unwrap(), None);
        });
    }

    /// The guards turn away bools and "N/A" and nothing else: the two sides
    /// of the union still cross as they arrived, and a string that is not the
    /// sentinel is still the type error it always was.
    #[test]
    fn a_limit_still_keeps_its_side_of_the_union_and_garbage_still_fails() {
        Python::with_gil(|py| {
            let row = raw_row(py);
            assert_eq!(int_or_float(&row, "whole").unwrap(), Some(Number::Int(105)));
            assert_eq!(
                int_or_float(&row, "real").unwrap(),
                Some(Number::Float(105.0))
            );
            assert!(matches!(
                int_or_float(&row, "word"),
                Err(PlatformError::Backend(_))
            ));
        });
    }

    /// A number that cannot be the declared integer is absent, not the value
    /// `as` would saturate it to.  Each of these crossed as a plausible
    /// reading: `-1` -- a common "could not read" -- as a stopped fan, `NaN`
    /// as 0, and anything past the width as its maximum.
    #[test]
    fn a_number_the_declared_width_cannot_hold_is_absent_rather_than_saturated() {
        assert_eq!(int_cast::<u32>(-1.0), None);
        assert_eq!(int_cast::<u32>(f64::NAN), None);
        assert_eq!(int_cast::<u32>(f64::INFINITY), None);
        assert_eq!(int_cast::<i64>(f64::NEG_INFINITY), None);
        assert_eq!(int_cast::<u32>(4_294_967_296.0), None);
        assert_eq!(int_cast::<i32>(-2_147_483_649.0), None);
        assert_eq!(int_cast::<u64>(1e30), None);
        assert_eq!(int_cast::<i64>(-1e30), None);
    }

    /// An `int` crosses exactly, however far past 2^53 it is, up to the edge
    /// of the declared width; one past that edge is absent, as a float past
    /// it is.  A float is still truncated, and None and "N/A" are no reading.
    #[test]
    fn an_integer_column_keeps_an_int_exact_and_truncates_only_a_float() {
        Python::with_gil(|py| {
            let row = raw_row(py);
            assert_eq!(
                integer::<i64>(&row, "past_f64").unwrap(),
                Some(9_007_199_254_740_993)
            );
            assert_eq!(integer::<i64>(&row, "i64_max").unwrap(), Some(i64::MAX));
            assert_eq!(integer::<i64>(&row, "past_i64").unwrap(), None);
            assert_eq!(integer::<u64>(&row, "past_i64").unwrap(), Some(1 << 63));
            assert_eq!(integer::<u64>(&row, "past_i128").unwrap(), None);
            assert_eq!(integer::<u32>(&row, "half").unwrap(), Some(50));
            assert_eq!(integer::<u32>(&row, "yes").unwrap(), Some(1));
            assert_eq!(integer::<u32>(&row, "nothing").unwrap(), None);
            assert_eq!(integer::<u32>(&row, "na").unwrap(), None);
            assert!(matches!(
                integer::<u32>(&row, "word"),
                Err(PlatformError::Backend(_))
            ));
        });
    }

    /// What does fit crosses as `as` always carried it: truncated toward zero,
    /// negatives kept where the width is signed, and the edges of the width
    /// still inside it.
    #[test]
    fn a_number_the_declared_width_can_hold_is_truncated_as_before() {
        assert_eq!(int_cast::<u32>(50.0), Some(50));
        assert_eq!(int_cast::<u32>(50.7), Some(50));
        assert_eq!(int_cast::<u32>(-0.5), Some(0));
        assert_eq!(int_cast::<i32>(-1.0), Some(-1));
        assert_eq!(int_cast::<i64>(-7.9), Some(-7));
        assert_eq!(int_cast::<u32>(4_294_967_295.0), Some(u32::MAX));
        assert_eq!(int_cast::<i32>(-2_147_483_648.0), Some(i32::MIN));
    }

    /// The handlers run, and running them is the whole point.
    ///
    /// `thermal_updater.py:92` registers its cleanup with `atexit`, and a Rust
    /// daemon leaving through `std::process::exit` finalises no interpreter, so
    /// on hardware hw-management-tc was left suspended with a stale ASIC
    /// temperature file behind it.  Asserting a handler actually fired is the
    /// only way to tell this function from a no-op.
    #[test]
    fn the_interpreters_exit_handlers_are_given_their_chance() {
        Python::with_gil(|py| {
            let m = PyModule::from_code(
                py,
                c_str!(
                    "import atexit\n\
                     RAN = []\n\
                     atexit.register(lambda: RAN.append(1))\n"
                ),
                c_str!("hooked.py"),
                c_str!("hooked"),
            )
            .unwrap();
            assert!(m.getattr("RAN").unwrap().len().unwrap() == 0);
            run_python_atexit_handlers();
            assert_eq!(
                m.getattr("RAN").unwrap().len().unwrap(),
                1,
                "the handler the vendor registered must have run"
            );
        });
    }
}
