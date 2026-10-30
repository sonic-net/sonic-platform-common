//! `Bridge::new` leaves the process's shutdown signals as it found them.
//!
//! A test binary of its own, with one test: `signal.signal()` works only on
//! the thread that started the interpreter, and here that is this test's
//! thread.  In `bridge_test.rs` any of the tests may start it, so a vendor's
//! installer there runs off the main thread and changes nothing.
//!
//! Requires `PYTHONPATH` to include the repository root, as `bridge_test.rs`
//! does.

use platform_pyo3::Bridge;
use pyo3::ffi::c_str;
use pyo3::prelude::*;
use pyo3::types::PyModule;

extern "C" fn daemon_handler(_: libc::c_int) {}

fn handler_of(sig: libc::c_int) -> libc::sighandler_t {
    // SAFETY: a null `act` only reads the current disposition into `old`.
    let mut old: libc::sigaction = unsafe { std::mem::zeroed() };
    assert_eq!(
        unsafe { libc::sigaction(sig, std::ptr::null(), &mut old) },
        0
    );
    old.sa_sigaction
}

/// mlnx's `Chassis.__init__` installs Python handlers for both signals
/// (`utils.watch_shutdown_signals()`), and the bridge then resets them to
/// `SIG_DFL`; both are `sigaction()` underneath.  A daemon that installed its
/// own handlers first would lose them, and SIGTERM would then kill it without
/// `tm_deinitialize()` or the atexit handlers.
#[test]
fn a_handler_installed_before_the_bridge_is_still_installed_after_it() {
    let ours = daemon_handler as extern "C" fn(libc::c_int) as libc::sighandler_t;
    for sig in [libc::SIGTERM, libc::SIGINT] {
        // SAFETY: installing a handler that does nothing.
        let mut act: libc::sigaction = unsafe { std::mem::zeroed() };
        act.sa_sigaction = ours;
        assert_eq!(
            unsafe { libc::sigaction(sig, &act, std::ptr::null_mut()) },
            0
        );
    }

    const VENDOR: &std::ffi::CStr = c_str!(
        "import signal\n\
         INSTALLED = []\n\
         class _C:\n\
         \x20   def get_name(self): return 'chassis 1'\n\
         class Platform:\n\
         \x20   def __init__(self):\n\
         \x20       for sig in (signal.SIGTERM, signal.SIGINT):\n\
         \x20           signal.signal(sig, lambda *a: None)\n\
         \x20           INSTALLED.append(sig)\n\
         \x20   def get_chassis(self): return _C()\n"
    );
    let vendor = Python::with_gil(|py| {
        let m = PyModule::from_code(py, VENDOR, c_str!("vend.py"), c_str!("vend_main")).unwrap();
        py.import("sys")
            .unwrap()
            .getattr("modules")
            .unwrap()
            .set_item("vend_main", &m)
            .unwrap();
        m.unbind()
    });

    assert!(Bridge::new("vend_main", "thermalctld").is_ok());

    Python::with_gil(|py| {
        // Otherwise the vendor's installer raised, nothing was replaced, and
        // what follows proves nothing.
        assert_eq!(
            vendor.bind(py).getattr("INSTALLED").unwrap().len().unwrap(),
            2
        );
        // The interpreter is left with nothing of the vendor's to run.
        let signal = py.import("signal").unwrap();
        let dfl = signal.getattr("SIG_DFL").unwrap();
        for name in ["SIGTERM", "SIGINT"] {
            let sig = signal.getattr(name).unwrap();
            assert!(signal
                .call_method1("getsignal", (sig,))
                .unwrap()
                .eq(&dfl)
                .unwrap());
        }
    });
    for sig in [libc::SIGTERM, libc::SIGINT] {
        assert_eq!(
            handler_of(sig),
            ours,
            "signal {sig}: the daemon's handler is gone"
        );
    }
}
