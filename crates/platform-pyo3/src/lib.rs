//
// SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
// Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//! Phase 1: a Rust daemon reaching a vendor's Python platform API.
//!
//! [`Bridge`] holds one Python object -- the facade -- and nothing else. The
//! per-method bodies are generated; what is written by hand here is the error
//! mapping and the four attribute readers, because those are decisions rather
//! than projections of the stub.

use platform_api::{PlatformError, Threshold};
use pyo3::exceptions::{PyKeyError, PyNotImplementedError};
use pyo3::prelude::*;
use pyo3::types::PyString;

mod generated;

/// A Rust handle on `platform_api.facade.PlatformApi`.
pub struct Bridge {
    facade: Py<PyAny>,
}

impl Bridge {
    /// Build a facade over the vendor's chassis.
    ///
    /// The vendor package is named by the caller rather than imported here:
    /// which `sonic_platform` is installed is a property of the image, and
    /// hard-coding it would stop the conformance suite driving this over a
    /// mock.
    /// `syslog_ident` becomes `sys.argv[0]`.  That is where
    /// `sonic_py_common.logger.Logger` takes its syslog identifier from when
    /// the caller passes none, and the vendor packages never pass one.  An
    /// embedded interpreter starts with `sys.argv` empty, so without this every
    /// line the vendor's Python logs arrives tagged `pmon#:` -- unreadable in
    /// syslog, and invisible to the `pmon#<daemon>` patterns sonic-mgmt's
    /// loganalyzer matches on.  Pass the same identifier the daemon logs under.
    pub fn new(vendor_module: &str, syslog_ident: &str) -> Result<Self, PlatformError> {
        Python::with_gil(|py| {
            py.import("sys")
                .and_then(|sys| sys.setattr("argv", vec![syslog_ident]))
                .map_err(|e| err(py, e))?;
            let chassis = py
                .import(vendor_module)
                .and_then(|m| m.getattr("Platform"))
                .and_then(|p| p.call0())
                .and_then(|p| p.call_method0("get_chassis"))
                .map_err(|e| err(py, e))?;
            release_python_signal_handlers(py);
            let facade = py
                .import("platform_api.facade")
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
/// and the per-module thermal links.  Measured on an SN5640: after stopping
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
/// Resetting to `SIG_DFL` here, before the caller installs its own handler,
/// leaves the interpreter with nothing to run: process lifetime belongs to the
/// Rust side, which is the whole arrangement in phase 1.
/// Best-effort on purpose: `signal.signal()` raises off the main thread, and
/// this crate is also constructed from worker threads (thermalctld builds a
/// second bridge for its leak updater).  There it is a no-op that must not turn
/// a working bridge into a failed one -- and it is unnecessary, because the
/// vendor's own installer has the same main-thread guard.
fn release_python_signal_handlers(py: Python<'_>) {
    let Ok(signal) = py.import("signal") else { return };
    let Ok(dfl) = signal.getattr("SIG_DFL") else { return };
    for name in ["SIGTERM", "SIGINT"] {
        if let Ok(signum) = signal.getattr(name) {
            let _ = signal.call_method1("signal", (signum, &dfl));
        }
    }
}

/// A Python exception, as the platform API spells the same thing.
///
/// `NotImplementedError` is the one that matters: the facade raises it for an
/// action a platform does not implement, and a caller that saw it as a generic
/// backend failure would log an error every polling cycle on hardware that is
/// working exactly as designed.
pub(crate) fn err(py: Python<'_>, e: PyErr) -> PlatformError {
    let text = e.value(py).to_string();
    if e.is_instance_of::<PyNotImplementedError>(py) {
        PlatformError::NotSupported(text)
    } else if e.is_instance_of::<PyKeyError>(py) {
        PlatformError::NotFound(text)
    } else {
        PlatformError::Backend(text)
    }
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
    s.extract()
        .map(Some)
        .map_err(|e| err(row.py(), e))
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

/// A limit going the other way: Rust to Python.
///
/// A setter that turned every limit into a float would write 105.0 where the
/// caller said 105, and the platform would store what it was given.
pub(crate) fn thr_arg(py: Python<'_>, t: Threshold) -> Py<PyAny> {
    match t {
        Threshold::Int(v) => v.into_pyobject(py).unwrap().into_any().unbind(),
        Threshold::Float(v) => v.into_pyobject(py).unwrap().into_any().unbind(),
    }
}

/// A limit column, keeping the side of `Union[int, float]` it arrived on.
///
/// Checked int-first, and with bools excluded: `bool` is a subclass of `int`
/// in Python, so `isinstance(True, int)` is true and an unguarded read would
/// turn a flag into the threshold `1`.
pub(crate) fn threshold(
    row: &Bound<'_, PyAny>,
    key: &str,
) -> Result<Option<Threshold>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() {
        return Ok(None);
    }
    if v.extract::<bool>().is_err() {
        if let Ok(i) = v.extract::<i64>() {
            return Ok(Some(Threshold::Int(i)));
        }
    }
    v.extract::<f64>()
        .map(|f| Some(Threshold::Float(f)))
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

/// A numeric column, read as f64 whatever the platform returned.
///
/// The base classes document float and vendors return int as readily; the
/// generator casts back to the declared width afterwards. Reading as f64 here
/// rather than asking for the narrow type is what stops a platform reporting
/// a whole-number speed as `50.0` from failing extraction.
pub(crate) fn num(row: &Bound<'_, PyAny>, key: &str) -> Result<Option<f64>, PlatformError> {
    let v = attr(row, key)?;
    // "N/A" for the same reason as in `flag`: a reading the platform could not
    // take is absent, not a type error.
    if v.is_none() || is_na(&v) {
        return Ok(None);
    }
    v.extract::<f64>().map(Some).map_err(|e| err(row.py(), e))
}

// ── Tests ─────────────────────────────────────────────────────────────────────
//
// The bridge against a real facade lives in tests/bridge_test.rs.  What is here
// is the two things that cannot be reached through one: a column shape the
// facade never produces, and a shutdown step whose whole effect is on the
// interpreter.

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
