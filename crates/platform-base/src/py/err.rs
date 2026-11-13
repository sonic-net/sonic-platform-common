//! A Python exception.

use std::fmt;
use std::io;

use platform_api::PlatformError;

use super::val::PyVal;

/// The exception classes platform code raises and catches.
///
/// Only the ones something distinguishes: the facade catches
/// `NotImplementedError` and `TypeError`, the bridge maps `DeviceNotFound`,
/// vendors catch `ValueError`, `IOError` and their subclasses.  Anything else
/// keeps its class name for `repr()` and is otherwise just an error.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Exc {
    NotImplementedError,
    KeyError,
    /// The facade's `DeviceNotFound(KeyError)`: no device at a key, or not a
    /// key at all.  A `KeyError` a vendor raises is not one.
    DeviceNotFound,
    IndexError,
    TypeError,
    ValueError,
    AttributeError,
    RuntimeError,
    OverflowError,
    ZeroDivisionError,
    /// `OSError` and its errno subclasses, by the class name Python picks --
    /// `TimeoutError` among them, as `os_error(ETIMEDOUT)` makes it.
    OSError(&'static str),
    /// `subprocess.CalledProcessError`, `json.JSONDecodeError` and the like.
    Other(&'static str),
    /// Not a Python exception: the attribute does not exist at all.
    ///
    /// `getattr(obj, name, None)` answering None, which the facade reads as
    /// "not implemented" without calling anything.  A trait default answers
    /// this for a method the object's base class does not define, so that a
    /// native object is missing exactly the methods its Python counterpart is.
    Missing,
}

impl Exc {
    pub fn name(&self) -> &'static str {
        match self {
            Exc::NotImplementedError => "NotImplementedError",
            Exc::KeyError => "KeyError",
            Exc::DeviceNotFound => "DeviceNotFound",
            Exc::IndexError => "IndexError",
            Exc::TypeError => "TypeError",
            Exc::ValueError => "ValueError",
            Exc::AttributeError | Exc::Missing => "AttributeError",
            Exc::RuntimeError => "RuntimeError",
            Exc::OverflowError => "OverflowError",
            Exc::ZeroDivisionError => "ZeroDivisionError",
            Exc::OSError(n) | Exc::Other(n) => n,
        }
    }

    /// `isinstance(e, OSError)` -- `IOError` is the same class in Python 3.
    pub fn is_os_error(&self) -> bool {
        matches!(self, Exc::OSError(_))
    }

    /// `isinstance(e, KeyError)`: `DeviceNotFound` is one.
    pub fn is_key_error(&self) -> bool {
        matches!(self, Exc::KeyError | Exc::DeviceNotFound)
    }
}

/// A raised exception: its class and its `args`.
#[derive(Clone, PartialEq)]
pub struct PyErr {
    pub exc: Exc,
    pub args: Vec<PyVal>,
    /// `OSError.filename`, which `str()` shows and `args` does not hold.
    pub filename: Option<String>,
}

pub type PyResult<T> = Result<T, PyErr>;

impl PyErr {
    pub fn new(exc: Exc, args: Vec<PyVal>) -> PyErr {
        PyErr {
            exc,
            args,
            filename: None,
        }
    }

    fn with_msg(exc: Exc, msg: impl Into<String>) -> PyErr {
        PyErr::new(exc, vec![PyVal::Str(msg.into())])
    }

    /// `raise NotImplementedError` -- no arguments, so `str()` is empty.
    pub fn not_implemented() -> PyErr {
        PyErr::new(Exc::NotImplementedError, vec![])
    }

    pub fn not_implemented_msg(msg: impl Into<String>) -> PyErr {
        PyErr::with_msg(Exc::NotImplementedError, msg)
    }

    pub fn key_error(key: impl Into<PyVal>) -> PyErr {
        PyErr::new(Exc::KeyError, vec![key.into()])
    }

    /// `raise DeviceNotFound(msg)`, from `_parse_key` and `_find_<row>`.
    pub fn device_not_found(msg: impl Into<String>) -> PyErr {
        PyErr::with_msg(Exc::DeviceNotFound, msg)
    }

    pub fn index_error(msg: impl Into<String>) -> PyErr {
        PyErr::with_msg(Exc::IndexError, msg)
    }

    pub fn type_error(msg: impl Into<String>) -> PyErr {
        PyErr::with_msg(Exc::TypeError, msg)
    }

    pub fn value_error(msg: impl Into<String>) -> PyErr {
        PyErr::with_msg(Exc::ValueError, msg)
    }

    pub fn runtime_error(msg: impl Into<String>) -> PyErr {
        PyErr::with_msg(Exc::RuntimeError, msg)
    }

    pub fn overflow_error(msg: impl Into<String>) -> PyErr {
        PyErr::with_msg(Exc::OverflowError, msg)
    }

    pub fn other(class: &'static str, msg: impl Into<String>) -> PyErr {
        PyErr::with_msg(Exc::Other(class), msg)
    }

    /// The attribute is not there; see [`Exc::Missing`].
    pub fn missing(class: &str, attr: &str) -> PyErr {
        PyErr::with_msg(
            Exc::Missing,
            format!("'{class}' object has no attribute '{attr}'"),
        )
    }

    /// Code here that a native implementation has not ported, rather than a
    /// platform that does not implement something.  Fails loudly: it is a
    /// `RuntimeError`, not a `NotImplementedError` the facade would swallow.
    pub fn not_ported(what: impl fmt::Display) -> PyErr {
        PyErr::runtime_error(format!("not ported to the native platform API: {what}"))
    }

    /// `OSError(errno, strerror, filename)`, of the subclass Python raises
    /// for that errno.
    pub fn os_error(errno: i32, filename: Option<&str>) -> PyErr {
        PyErr {
            exc: Exc::OSError(os_error_class(errno)),
            args: vec![PyVal::Int(i128::from(errno)), PyVal::Str(strerror(errno))],
            filename: filename.map(str::to_string),
        }
    }

    /// What Python raises for the same failed I/O.
    pub fn from_io(e: &io::Error, filename: Option<&str>) -> PyErr {
        match e.raw_os_error() {
            Some(errno) => PyErr::os_error(errno, filename),
            None => match e.kind() {
                // Text decoding is the only non-errno failure `open().read()`
                // has; Python names the codec and the byte, which a vendor's
                // except clause does not look at.
                io::ErrorKind::InvalidData => PyErr::other(
                    "UnicodeDecodeError",
                    "'utf-8' codec can't decode bytes: invalid start byte",
                ),
                _ => PyErr::new(Exc::OSError("OSError"), vec![PyVal::Str(e.to_string())]),
            },
        }
    }

    pub fn is(&self, exc: &Exc) -> bool {
        &self.exc == exc
    }

    /// `str(e)`.
    pub fn str(&self) -> String {
        if self.exc.is_os_error() {
            if let [PyVal::Int(errno), PyVal::Str(strerror)] = self.args.as_slice() {
                return match &self.filename {
                    Some(f) => format!(
                        "[Errno {errno}] {strerror}: {}",
                        PyVal::Str(f.clone()).py_repr()
                    ),
                    None => format!("[Errno {errno}] {strerror}"),
                };
            }
        }
        if let Some(s) = super::codec::error_str(self) {
            return s;
        }
        match (&self.exc, self.args.as_slice()) {
            (_, []) => String::new(),
            // KeyError alone shows its one argument as `repr()`: the key
            // `'fan1'` prints with its quotes.  A subclass inherits that.
            (Exc::KeyError | Exc::DeviceNotFound, [k]) => k.py_repr(),
            (_, [one]) => one.py_str(),
            (_, many) => PyVal::Tuple(many.to_vec()).py_str(),
        }
    }

    /// `repr(e)`, which is what `'... - {}'.format(repr(e))` logs.
    pub fn repr(&self) -> String {
        let args = self
            .args
            .iter()
            .map(PyVal::py_repr)
            .collect::<Vec<_>>()
            .join(", ");
        format!("{}({})", self.exc.name(), args)
    }

    /// What the bridge turns this into when it reaches a daemon.
    ///
    /// `NotFound` is the facade's `DeviceNotFound` and nothing else: a
    /// `KeyError` a vendor's getter raises -- a dictionary miss in a sysfs
    /// table -- is the backend failure it is, not "no such device".
    pub fn to_platform(&self) -> PlatformError {
        let text = self.str();
        match self.exc {
            Exc::NotImplementedError => PlatformError::NotSupported(text),
            Exc::DeviceNotFound => PlatformError::NotFound(text),
            _ => PlatformError::Backend(text),
        }
    }
}

impl fmt::Debug for PyErr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.repr())
    }
}

impl fmt::Display for PyErr {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.str())
    }
}

impl From<PyErr> for PlatformError {
    fn from(e: PyErr) -> PlatformError {
        e.to_platform()
    }
}

/// The `OSError` subclass CPython raises for an errno (PEP 3151).
fn os_error_class(errno: i32) -> &'static str {
    match errno {
        2 => "FileNotFoundError",
        1 | 13 => "PermissionError",
        3 => "ProcessLookupError",
        4 => "InterruptedError",
        10 => "ChildProcessError",
        17 => "FileExistsError",
        20 => "NotADirectoryError",
        21 => "IsADirectoryError",
        32 | 108 => "BrokenPipeError",
        104 => "ConnectionResetError",
        111 => "ConnectionRefusedError",
        103 => "ConnectionAbortedError",
        110 => "TimeoutError",
        11 | 114 | 115 => "BlockingIOError",
        _ => "OSError",
    }
}

/// `os.strerror(errno)`: the C library's text, which is what Python shows.
fn strerror(errno: i32) -> String {
    let s = io::Error::from_raw_os_error(errno).to_string();
    // Rust appends " (os error N)"; the C text is everything before it.
    match s.rfind(" (os error ") {
        Some(i) => s[..i].to_string(),
        None => s,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn an_os_error_prints_the_way_python_prints_it() {
        let e = PyErr::os_error(2, Some("/run/hw-management/thermal/fan1_speed_get"));
        assert_eq!(
            e.repr(),
            "FileNotFoundError(2, 'No such file or directory')"
        );
        assert_eq!(
            e.str(),
            "[Errno 2] No such file or directory: '/run/hw-management/thermal/fan1_speed_get'"
        );
        assert_eq!(
            PyErr::os_error(13, None).str(),
            "[Errno 13] Permission denied"
        );
        assert_eq!(
            PyErr::os_error(5, None).repr(),
            "OSError(5, 'Input/output error')"
        );
    }

    #[test]
    fn a_bare_raise_is_empty_and_a_key_error_quotes_its_key() {
        assert_eq!(PyErr::not_implemented().str(), "");
        assert_eq!(PyErr::not_implemented().repr(), "NotImplementedError()");
        assert_eq!(
            PyErr::key_error("no FanInfo named 'fan1'").str(),
            "\"no FanInfo named 'fan1'\""
        );
        assert_eq!(PyErr::value_error("bad").repr(), "ValueError('bad')");
    }

    #[test]
    fn the_bridge_mapping_is_by_class() {
        assert!(
            matches!(PyErr::not_implemented().to_platform(), PlatformError::NotSupported(m) if m.is_empty())
        );
        assert!(
            matches!(PyErr::device_not_found("x").to_platform(), PlatformError::NotFound(m) if m == "'x'")
        );
        assert!(
            matches!(PyErr::key_error("x").to_platform(), PlatformError::Backend(m) if m == "'x'")
        );
        assert_eq!(
            PyErr::device_not_found("no FanInfo at 'k'").repr(),
            "DeviceNotFound(\"no FanInfo at 'k'\")"
        );
        assert!(Exc::DeviceNotFound.is_key_error() && Exc::KeyError.is_key_error());
        assert!(
            matches!(PyErr::value_error("v").to_platform(), PlatformError::Backend(m) if m == "v")
        );
    }

    #[test]
    fn each_class_is_named_as_python_names_it() {
        let names: Vec<&str> = [
            PyErr::key_error("k"),
            PyErr::index_error("i"),
            PyErr::type_error("t"),
            PyErr::runtime_error("r"),
            PyErr::overflow_error("o"),
            PyErr::new(Exc::ZeroDivisionError, vec![]),
        ]
        .iter()
        .map(|e| e.exc.name())
        .collect();
        assert_eq!(
            names,
            [
                "KeyError",
                "IndexError",
                "TypeError",
                "RuntimeError",
                "OverflowError",
                "ZeroDivisionError"
            ]
        );
        // A timeout is the errno subclass, an OSError like the rest of them.
        let timeout = PyErr::os_error(110, None);
        assert!(timeout.is(&Exc::OSError("TimeoutError")) && timeout.exc.is_os_error());
        assert!(PyErr::runtime_error("r").is(&Exc::RuntimeError));
        assert_eq!(
            PyErr::not_ported("SFP xcvr").str(),
            "not ported to the native platform API: SFP xcvr"
        );
    }

    #[test]
    fn an_errno_picks_the_subclass_python_picks() {
        let classes: Vec<&str> = [
            1, 3, 4, 10, 11, 13, 17, 20, 21, 32, 103, 104, 108, 110, 111, 114, 115, 5,
        ]
        .iter()
        .map(|n| PyErr::os_error(*n, None).exc.name())
        .collect();
        assert_eq!(
            classes,
            [
                "PermissionError",
                "ProcessLookupError",
                "InterruptedError",
                "ChildProcessError",
                "BlockingIOError",
                "PermissionError",
                "FileExistsError",
                "NotADirectoryError",
                "IsADirectoryError",
                "BrokenPipeError",
                "ConnectionAbortedError",
                "ConnectionResetError",
                "BrokenPipeError",
                "TimeoutError",
                "ConnectionRefusedError",
                "BlockingIOError",
                "BlockingIOError",
                "OSError"
            ]
        );
        assert_eq!(
            PyErr::os_error(17, Some("x")).to_string(),
            "[Errno 17] File exists: 'x'"
        );
    }

    #[test]
    fn io_errors_without_an_errno_and_many_args() {
        let bad = io::Error::new(io::ErrorKind::InvalidData, "x");
        assert_eq!(PyErr::from_io(&bad, None).exc.name(), "UnicodeDecodeError");
        let other = io::Error::other("boom");
        assert_eq!(PyErr::from_io(&other, None).repr(), "OSError('boom')");
        let many = PyErr::new(Exc::ValueError, vec![1.into(), "a".into()]);
        assert_eq!(
            (many.str(), format!("{many:?}")),
            ("(1, 'a')".to_string(), "ValueError(1, 'a')".to_string())
        );
        assert!(
            matches!(PlatformError::from(PyErr::runtime_error("r")), PlatformError::Backend(m) if m == "r")
        );
    }
}
