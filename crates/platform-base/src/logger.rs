//! `sonic_py_common.logger.Logger`, and the `syslog` module under it.
//!
//! What a vendor's log lines look like is decided by process-global state, the
//! way the C library keeps it: every `Logger()` construction calls `openlog`,
//! so the identifier of the *last* one constructed tags every line any of them
//! logs afterwards.  A vendor package builds one per module at import time and
//! some lazily, so the tag on a given line depends on what was imported before
//! it.  A native implementation reproduces that by constructing its loggers at
//! the points its Python counterpart did (see [`import`]), and by going
//! through the same C calls.
//!
//! The Rust daemons log through their own socket, not through `openlog`, as
//! they do when the vendor is Python: what is shared here is shared only among
//! the vendor's own lines.

use std::collections::HashSet;
use std::ffi::CString;
use std::sync::atomic::{AtomicBool, AtomicI32, Ordering};
use std::sync::{Arc, Mutex};

pub const LOG_ERR: i32 = libc::LOG_ERR;
pub const LOG_WARNING: i32 = libc::LOG_WARNING;
pub const LOG_NOTICE: i32 = libc::LOG_NOTICE;
pub const LOG_INFO: i32 = libc::LOG_INFO;
pub const LOG_DEBUG: i32 = libc::LOG_DEBUG;

/// The Python syslog module's view of the connection: open or not, and with
/// which identifier.  The identifier is kept alive here because `openlog`
/// keeps the pointer, not the string.
struct State {
    open: bool,
    idents: Vec<CString>,
}

static STATE: Mutex<State> = Mutex::new(State {
    open: false,
    idents: Vec::new(),
});
static ARGV0: Mutex<Option<String>> = Mutex::new(None);

/// `sys.argv[0]`, which the PyO3 bridge sets to the daemon's syslog
/// identifier and which a `Logger()` with no identifier uses.
pub fn set_argv0(ident: &str) {
    if let Ok(mut a) = ARGV0.lock() {
        *a = Some(ident.to_string());
    }
}

/// `os.path.basename(sys.argv[0])`.
pub fn argv0() -> String {
    let a = ARGV0
        .lock()
        .ok()
        .and_then(|a| a.clone())
        .unwrap_or_default();
    a.rsplit('/').next().unwrap_or("").to_string()
}

/// `syslog.openlog(ident, logoption, facility)`.
pub fn openlog(ident: &str, option: i32, facility: i32) {
    let Ok(mut st) = STATE.lock() else { return };
    let c = CString::new(ident.replace('\0', "")).unwrap_or_default();
    // SAFETY: `c` is moved into `idents` below and never dropped while the
    // process runs, so the pointer openlog keeps stays valid.
    unsafe { libc::openlog(c.as_ptr(), option, facility) };
    st.idents.push(c);
    st.open = true;
}

/// `syslog.closelog()`.
pub fn closelog() {
    let Ok(mut st) = STATE.lock() else { return };
    // SAFETY: no arguments; closes the C library's connection.
    unsafe { libc::closelog() };
    st.open = false;
}

/// `syslog.syslog(priority, msg)`: opens with `sys.argv[0]` first if nothing
/// is open, as CPython's module does.
pub fn syslog(priority: i32, msg: &str) {
    let open = STATE.lock().map(|s| s.open).unwrap_or(true);
    if !open {
        openlog(&argv0(), 0, libc::LOG_USER);
    }
    let Ok(c) = CString::new(msg.replace('\0', "")) else {
        return;
    };
    // SAFETY: a "%s" format with one valid C string argument.
    unsafe { libc::syslog(priority, c"%s".as_ptr(), c.as_ptr()) };
}

/// A `Logger`.  Its minimum priority is its own; the identifier it opened
/// with belongs to the process.
pub struct Logger {
    min: AtomicI32,
}

impl Logger {
    /// `Logger(log_identifier)`: `openlog` now, NOTICE as the threshold.
    pub fn new(ident: Option<&str>) -> Logger {
        let ident = ident.map_or_else(argv0, str::to_string);
        openlog(&ident, libc::LOG_NDELAY, libc::LOG_USER);
        Logger {
            min: AtomicI32::new(LOG_NOTICE),
        }
    }

    pub fn set_min_log_priority(&self, priority: i32) {
        self.min.store(priority, Ordering::Relaxed);
    }

    /// `log(priority, msg)`: sent if at or above the threshold.
    pub fn log(&self, priority: i32, msg: &str) {
        if self.min.load(Ordering::Relaxed) >= priority {
            syslog(priority, msg);
        }
    }

    pub fn log_error(&self, msg: &str) {
        self.log(LOG_ERR, msg)
    }
    pub fn log_warning(&self, msg: &str) {
        self.log(LOG_WARNING, msg)
    }
    pub fn log_notice(&self, msg: &str) {
        self.log(LOG_NOTICE, msg)
    }
    pub fn log_info(&self, msg: &str) {
        self.log(LOG_INFO, msg)
    }
    pub fn log_debug(&self, msg: &str) {
        self.log(LOG_DEBUG, msg)
    }
}

/// `__del__`: a `Logger` that goes away closes the connection, and the next
/// line logged by anything reopens it under `sys.argv[0]`.
impl Drop for Logger {
    fn drop(&mut self) {
        closelog();
    }
}

static IMPORTED: Mutex<Option<HashSet<&'static str>>> = Mutex::new(None);

/// `import <module>`, as far as logging sees it: the first time only, run
/// `init` -- which constructs the module's loggers -- exactly where Python
/// would have executed the module body.  Later imports are no-ops, as they
/// are in Python.  Answers whether this call did the import.
pub fn import(module: &'static str, init: impl FnOnce()) -> bool {
    let first = IMPORTED
        .lock()
        .map(|mut m| m.get_or_insert_with(HashSet::new).insert(module))
        .unwrap_or(false);
    if first {
        init();
    }
    first
}

/// `import <module>` for a module whose body can raise: it counts as
/// imported only once `init` succeeds, so a failed import is retried --
/// body and all -- by the next `import`, as Python retries it.
pub fn import_fallible<E>(
    module: &'static str,
    init: impl FnOnce() -> Result<(), E>,
) -> Result<(), E> {
    let done = IMPORTED
        .lock()
        .map(|m| m.as_ref().is_some_and(|m| m.contains(module)))
        .unwrap_or(false);
    if done {
        return Ok(());
    }
    init()?;
    if let Ok(mut m) = IMPORTED.lock() {
        m.get_or_insert_with(HashSet::new).insert(module);
    }
    Ok(())
}

/// A module-level logger: built by the module's import, shared afterwards.
pub type ModuleLogger = std::sync::OnceLock<Arc<Logger>>;

/// Whether `logging.basicConfig()` has run: from then on the root logger
/// has a stderr handler, at DEBUG, and every record that propagates to it is
/// written there as `LEVEL:name:message`.  The vendor's liquid_cooling module
/// does this on import, which reaches far beyond its own logger -- every
/// SysLogger line after it is printed to stderr as well.
static ROOT_STDERR: AtomicBool = AtomicBool::new(false);

/// `logging.basicConfig(level=logging.DEBUG)`.
pub fn basic_config() {
    ROOT_STDERR.store(true, Ordering::Relaxed);
}

fn stderr_line(line: &str) {
    use std::io::Write;
    let _ = writeln!(std::io::stderr(), "{line}");
}

/// `logging.getLogger(name).log(level, msg)` for a logger with no handler
/// and no level of its own: the root logger decides.  Before `basicConfig`
/// that is `logging.lastResort` -- WARNING and above, the bare message.
pub fn py_log(name: &str, level: PyLevel, msg: &str) {
    if ROOT_STDERR.load(Ordering::Relaxed) {
        stderr_line(&format!("{}:{name}:{msg}", level.name()));
    } else if level >= PyLevel::Warning {
        stderr_line(msg);
    }
}

/// `sonic_py_common.syslogger.SysLogger`: Python `logging` with a
/// `SysLogHandler` on `/dev/log`, which the vendor uses beside `Logger`.
///
/// It takes no part in `openlog`: each line is its own datagram,
/// `<PRI>name[pid]: message\0`, formatted by Python, with no timestamp and
/// LOG_USER as the facility.  The threshold is `logging.NOTICE` -- which
/// syslogger defines as INFO + 1 -- and nothing in the platform changes it.
#[derive(Clone, Debug)]
pub struct SysLogger {
    name: String,
}

/// Python `logging` levels, as SysLogger defines them.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum PyLevel {
    Debug = 10,
    Info = 20,
    Notice = 21,
    Warning = 30,
    Error = 40,
}

impl PyLevel {
    /// `logging.getLevelName(level)`.
    pub fn name(self) -> &'static str {
        match self {
            PyLevel::Debug => "DEBUG",
            PyLevel::Info => "INFO",
            PyLevel::Notice => "NOTICE",
            PyLevel::Warning => "WARNING",
            PyLevel::Error => "ERROR",
        }
    }
}

impl SysLogger {
    /// `SysLogger(log_identifier)`: the identifier, or `sys.argv[0]`'s base
    /// name when there is none.
    pub fn new(identifier: Option<&str>) -> SysLogger {
        SysLogger {
            name: identifier.map_or_else(argv0, str::to_string),
        }
    }

    /// `log(priority, msg)`.
    ///
    /// Python reconnects once and, failing that, prints a "--- Logging
    /// error ---" report to stderr; a pmon container always has `/dev/log`,
    /// so a failed send is dropped here.  The socket is found through
    /// [`io::real`](crate::io::real), so a test's root can listen on it.
    pub fn log(&self, level: PyLevel, msg: &str) {
        if level < PyLevel::Notice {
            return;
        }
        let pri = match level {
            PyLevel::Error => LOG_ERR,
            PyLevel::Warning => LOG_WARNING,
            PyLevel::Notice => LOG_NOTICE,
            PyLevel::Info => LOG_INFO,
            PyLevel::Debug => LOG_DEBUG,
        };
        let line = format!(
            "<{}>{}[{}]: {msg}\0",
            libc::LOG_USER | pri,
            self.name,
            std::process::id()
        );
        if let Ok(sock) = std::os::unix::net::UnixDatagram::unbound() {
            let _ = sock.send_to(line.as_bytes(), crate::io::real("/dev/log"));
        }
        // The record propagates to the root logger too.
        if ROOT_STDERR.load(Ordering::Relaxed) {
            stderr_line(&format!("{}:{}:{msg}", level.name(), self.name));
        }
    }

    pub fn log_error(&self, msg: &str) {
        self.log(PyLevel::Error, msg)
    }
    pub fn log_warning(&self, msg: &str) {
        self.log(PyLevel::Warning, msg)
    }
    pub fn log_notice(&self, msg: &str) {
        self.log(PyLevel::Notice, msg)
    }
    pub fn log_info(&self, msg: &str) {
        self.log(PyLevel::Info, msg)
    }
    pub fn log_debug(&self, msg: &str) {
        self.log(PyLevel::Debug, msg)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::testing::Root;
    use std::time::Duration;

    #[test]
    fn a_logger_sends_at_or_above_its_threshold() {
        let before = ARGV0.lock().unwrap().clone();
        set_argv0("/usr/local/bin/unit-test-daemon");
        assert_eq!(argv0(), "unit-test-daemon");
        let named = Logger::new(Some("unit-test"));
        let unnamed = Logger::new(None);
        assert_eq!(named.min.load(Ordering::Relaxed), LOG_NOTICE);
        for l in [&named, &unnamed] {
            l.log_error("error");
            l.log_warning("warning");
            l.log_notice("notice");
            l.log_info("info: below the threshold");
            l.log_debug("debug: below the threshold");
        }
        named.set_min_log_priority(LOG_DEBUG);
        assert_eq!(named.min.load(Ordering::Relaxed), LOG_DEBUG);
        named.log_debug("debug");
        // Dropping one closes the connection; the next line reopens it.
        drop(unnamed);
        syslog(LOG_NOTICE, "reopened");
        closelog();
        syslog(LOG_INFO, "reopened under sys.argv[0]");
        *ARGV0.lock().unwrap() = before;
    }

    #[test]
    fn a_module_is_imported_once_unless_its_body_fails() {
        let mut runs = 0;
        assert!(import("unit_test.module_a", || runs += 1));
        assert!(!import("unit_test.module_a", || runs += 1));
        assert_eq!(runs, 1);
        assert_eq!(
            import_fallible("unit_test.module_b", || Err("raised")),
            Err("raised")
        );
        assert_eq!(
            import_fallible("unit_test.module_b", || Ok::<(), &str>(())),
            Ok(())
        );
        assert_eq!(
            import_fallible("unit_test.module_b", || Err("not run again")),
            Ok(())
        );
    }

    #[test]
    fn sys_logger_lines_are_python_s_datagrams() {
        let root = Root::new();
        std::fs::create_dir_all(root.real("/dev")).unwrap();
        let sock = std::os::unix::net::UnixDatagram::bind(root.real("/dev/log")).unwrap();
        sock.set_read_timeout(Some(Duration::from_millis(500)))
            .unwrap();
        let l = SysLogger::new(Some("syslogger-test"));
        l.log_debug("below NOTICE: dropped");
        l.log_info("below NOTICE: dropped");
        l.log_notice("hello");
        l.log_warning("careful");
        l.log_error("broken");
        let mut got = Vec::new();
        let mut buf = [0u8; 512];
        while let Ok(n) = sock.recv(&mut buf) {
            let line = String::from_utf8_lossy(&buf[..n]).into_owned();
            if line.contains("syslogger-test[") {
                got.push(line);
            }
        }
        let pid = std::process::id();
        assert_eq!(
            got,
            [
                format!("<13>syslogger-test[{pid}]: hello\0"),
                format!("<12>syslogger-test[{pid}]: careful\0"),
                format!("<11>syslogger-test[{pid}]: broken\0"),
            ]
        );
        assert_eq!(SysLogger::new(None).name, argv0());
    }

    #[test]
    fn python_logging_reaches_stderr_as_the_root_logger_decides() {
        assert_eq!(
            [
                PyLevel::Debug,
                PyLevel::Info,
                PyLevel::Notice,
                PyLevel::Warning,
                PyLevel::Error
            ]
            .map(PyLevel::name),
            ["DEBUG", "INFO", "NOTICE", "WARNING", "ERROR"]
        );
        assert!(PyLevel::Notice > PyLevel::Info && PyLevel::Notice < PyLevel::Warning);
        // logging.lastResort: WARNING and up, the bare message.
        py_log("unit_test", PyLevel::Info, "not shown");
        py_log("unit_test", PyLevel::Warning, "unit test: shown bare");
        basic_config();
        py_log(
            "unit_test",
            PyLevel::Debug,
            "unit test: shown as DEBUG:unit_test:...",
        );
        SysLogger::new(Some("unit_test")).log_notice("unit test: also on stderr");
        ROOT_STDERR.store(false, Ordering::Relaxed);
    }
}
