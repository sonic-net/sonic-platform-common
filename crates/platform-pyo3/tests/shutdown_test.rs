//! `notify_shutdown()` hands the daemon's shutdown to the vendor's handler.
//!
//! A test binary of its own, with one test, for the reason `signal_test.rs`
//! is: the vendor's installer, and the bridge's capture of it, work only on
//! the thread that started the interpreter, and here that is this test's.
//!
//! Requires `PYTHONPATH` to include the repository root, as `bridge_test.rs`
//! does.

use std::sync::atomic::{AtomicUsize, Ordering};

use platform_api::PlatformApi;
use platform_pyo3::Bridge;
use pyo3::ffi::c_str;
use pyo3::prelude::*;
use pyo3::types::PyModule;

static DELIVERED: AtomicUsize = AtomicUsize::new(0);

extern "C" fn daemon_handler(_: libc::c_int) {
    DELIVERED.fetch_add(1, Ordering::SeqCst);
}

fn handler_of(sig: libc::c_int) -> libc::sighandler_t {
    // SAFETY: a null `act` only reads the current disposition into `old`.
    let mut old: libc::sigaction = unsafe { std::mem::zeroed() };
    assert_eq!(
        unsafe { libc::sigaction(sig, std::ptr::null(), &mut old) },
        0
    );
    old.sa_sigaction
}

fn register(py: Python<'_>, code: &std::ffi::CStr, name: &std::ffi::CStr) -> Py<PyModule> {
    let m = PyModule::from_code(py, code, c_str!("vend.py"), name).unwrap();
    py.import("sys")
        .unwrap()
        .getattr("modules")
        .unwrap()
        .set_item(name.to_str().unwrap(), &m)
        .unwrap();
    m.unbind()
}

/// A SIGTERM sent while the chassis is built.
const SIGNALLED: &std::ffi::CStr = c_str!(
    "import signal\n\
     class _C:\n\
     \x20   def get_name(self): return 'chassis 1'\n\
     class Platform:\n\
     \x20   def __init__(self):\n\
     \x20       signal.raise_signal(signal.SIGTERM)\n\
     \x20   def get_chassis(self): return _C()\n"
);

/// mlnx's `utils.watch_shutdown_signals()` and `_handle_shutdown_signal`, as
/// shipped: once per process and on the main thread only, set the event,
/// chain to the previous handler, and for `SIG_DFL` restore it and re-raise --
/// which would end this test binary.
const LIKE_MLNX: &std::ffi::CStr = c_str!(
    "import functools, os, signal, threading\n\
     EVENT = threading.Event()\n\
     RUNS = []\n\
     def _handle(previous, signum, frame):\n\
     \x20   RUNS.append(signum)\n\
     \x20   EVENT.set()\n\
     \x20   if callable(previous):\n\
     \x20       previous(signum, frame)\n\
     \x20   elif previous == signal.SIG_DFL:\n\
     \x20       signal.signal(signum, signal.SIG_DFL)\n\
     \x20       os.kill(os.getpid(), signum)\n\
     class _C:\n\
     \x20   def get_name(self): return 'chassis 1'\n\
     INSTALLED = []\n\
     class Platform:\n\
     \x20   def __init__(self):\n\
     \x20       if INSTALLED or threading.current_thread() is not threading.main_thread():\n\
     \x20           return\n\
     \x20       for sig in (signal.SIGTERM, signal.SIGINT):\n\
     \x20           signal.signal(sig, functools.partial(_handle, signal.getsignal(sig)))\n\
     \x20       INSTALLED.append(True)\n\
     \x20   def get_chassis(self): return _C()\n"
);

#[test]
fn the_vendors_handler_runs_on_notify_and_the_daemon_keeps_its_signals() {
    let ours = daemon_handler as extern "C" fn(libc::c_int) as libc::sighandler_t;
    for sig in [libc::SIGTERM, libc::SIGINT] {
        // SAFETY: installing a handler that only counts.
        let mut act: libc::sigaction = unsafe { std::mem::zeroed() };
        act.sa_sigaction = ours;
        assert_eq!(
            unsafe { libc::sigaction(sig, &act, std::ptr::null_mut()) },
            0
        );
    }

    // A SIGTERM sent during start-up lands on the bridge's no-op, and reaches
    // the daemon once its handler is back.
    Python::with_gil(|py| register(py, SIGNALLED, c_str!("vend_signalled")));
    assert!(Bridge::new("vend_signalled", "thermalctld").is_ok());
    assert_eq!(DELIVERED.load(Ordering::SeqCst), 1);

    let vendor = Python::with_gil(|py| register(py, LIKE_MLNX, c_str!("vend_mlnx")));
    let mut api = Bridge::new("vend_mlnx", "thermalctld").unwrap();
    for sig in [libc::SIGTERM, libc::SIGINT] {
        assert_eq!(
            handler_of(sig),
            ours,
            "signal {sig}: the daemon's handler is gone"
        );
    }
    let event_set = |py: Python<'_>| -> bool {
        vendor
            .bind(py)
            .getattr("EVENT")
            .unwrap()
            .call_method0("is_set")
            .unwrap()
            .extract()
            .unwrap()
    };
    assert!(!Python::with_gil(event_set));

    // What the daemon does on SIGTERM.  The vendor's chain ends in the no-op:
    // the process is still here to assert anything at all.
    api.notify_shutdown().unwrap();
    api.notify_shutdown().unwrap();
    // A second handle built off the main thread notifies the same process.
    std::thread::spawn(|| {
        Bridge::new("vend_mlnx", "thermalctld")
            .unwrap()
            .notify_shutdown()
            .unwrap()
    })
    .join()
    .unwrap();

    Python::with_gil(|py| {
        assert!(event_set(py));
        let runs: Vec<i32> = vendor.bind(py).getattr("RUNS").unwrap().extract().unwrap();
        assert_eq!(runs, vec![libc::SIGTERM], "once, as SIGTERM");
    });
    for sig in [libc::SIGTERM, libc::SIGINT] {
        assert_eq!(
            handler_of(sig),
            ours,
            "signal {sig}: the daemon's handler is gone"
        );
    }
    // Nothing raised on the daemon's behalf but the one sent at start-up.
    assert_eq!(DELIVERED.load(Ordering::SeqCst), 1);
}
