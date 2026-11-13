//! The locale's codec: what `open()` decodes files with, what `text=True`
//! decodes command output with, and what argv and paths are encoded with on
//! their way to the kernel.
//!
//! The daemons embed Python with `Py_InitializeEx`, CPython's compat
//! configuration: no UTF-8 mode (`PYTHONUTF8` is ignored there) and no C
//! locale coercion, so LC_CTYPE comes from the environment as `setlocale`
//! reads it.  pmon's supervisord passes no LANG or LC_*, which makes it the C
//! locale and the codec ASCII: a byte above 0x7f in a sysfs file is a
//! `UnicodeDecodeError`, a non-ASCII argument a `UnicodeEncodeError`.

use std::sync::OnceLock;

use super::err::{Exc, PyErr, PyResult};
use super::val::PyVal;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Codec {
    Utf8,
    Ascii,
    Latin1,
}

impl Codec {
    fn name(self) -> &'static str {
        match self {
            Codec::Utf8 => "utf-8",
            Codec::Ascii => "ascii",
            Codec::Latin1 => "latin-1",
        }
    }
}

/// The codec of the locale the environment names, read once.
///
/// This crate's own unit tests answer pmon's instead -- the C locale, ASCII --
/// whatever the host running them is set to: they describe what the daemons
/// do under supervisord, and on a UTF-8 desktop they would otherwise test
/// something else.
pub fn locale() -> Codec {
    static C: OnceLock<Codec> = OnceLock::new();
    *C.get_or_init(|| {
        if cfg!(test) {
            Codec::Ascii
        } else {
            from_environment()
        }
    })
}

/// The locale's codec as `setlocale(LC_CTYPE, "")` would find it: a locale
/// that is not installed leaves C in place, as `setlocale` failing does.
/// Code sets other than these three are taken as UTF-8.
fn from_environment() -> Codec {
    // SAFETY: newlocale/nl_langinfo_l/freelocale on a locale object of our
    // own; unlike setlocale, nothing process-wide changes.
    let codeset = unsafe {
        let loc = libc::newlocale(libc::LC_CTYPE_MASK, c"".as_ptr(), std::ptr::null_mut());
        if loc.is_null() {
            return Codec::Ascii;
        }
        let p = libc::nl_langinfo_l(libc::CODESET, loc);
        let s = if p.is_null() {
            String::new()
        } else {
            std::ffi::CStr::from_ptr(p).to_string_lossy().into_owned()
        };
        libc::freelocale(loc);
        s
    };
    match codeset.as_str() {
        "ANSI_X3.4-1968" | "ASCII" | "" => Codec::Ascii,
        "ISO-8859-1" => Codec::Latin1,
        _ => Codec::Utf8,
    }
}

/// `bytes.decode(codec)`, strict.
pub fn decode(codec: Codec, b: &[u8]) -> PyResult<String> {
    let bad = |start: usize, end: usize, reason: &str| {
        PyErr::new(
            Exc::Other("UnicodeDecodeError"),
            vec![
                PyVal::str(codec.name()),
                PyVal::Bytes(b.to_vec()),
                PyVal::int(start as i128),
                PyVal::int(end as i128),
                PyVal::str(reason),
            ],
        )
    };
    match codec {
        Codec::Latin1 => Ok(b.iter().map(|&c| c as char).collect()),
        Codec::Ascii => match b.iter().position(|&c| c > 0x7f) {
            Some(i) => Err(bad(i, i + 1, "ordinal not in range(128)")),
            None => Ok(b.iter().map(|&c| c as char).collect()),
        },
        Codec::Utf8 => std::str::from_utf8(b).map(str::to_string).map_err(|e| {
            let i = e.valid_up_to();
            match e.error_len() {
                None => bad(i, b.len(), "unexpected end of data"),
                Some(n) if (0xc2..=0xf4).contains(&b[i]) => {
                    bad(i, i + n, "invalid continuation byte")
                }
                Some(n) => bad(i, i + n, "invalid start byte"),
            }
        }),
    }
}

/// `str.encode(codec)`: Python reports the whole run of characters the codec
/// cannot take, starting at the first.
pub fn encode_check(codec: Codec, s: &str) -> PyResult<()> {
    let limit = match codec {
        Codec::Utf8 => return Ok(()),
        Codec::Ascii => 0x80,
        Codec::Latin1 => 0x100,
    };
    let chars: Vec<char> = s.chars().collect();
    let Some(start) = chars.iter().position(|&c| c as u32 >= limit) else {
        return Ok(());
    };
    let end = start
        + chars[start..]
            .iter()
            .take_while(|&&c| c as u32 >= limit)
            .count();
    Err(PyErr::new(
        Exc::Other("UnicodeEncodeError"),
        vec![
            PyVal::str(codec.name()),
            PyVal::str(s),
            PyVal::int(start as i128),
            PyVal::int(end as i128),
            PyVal::str(format!("ordinal not in range({limit})")),
        ],
    ))
}

/// `str()` of a `UnicodeDecodeError` or `UnicodeEncodeError`.
pub fn error_str(e: &PyErr) -> Option<String> {
    let [PyVal::Str(enc), obj, PyVal::Int(start), PyVal::Int(end), PyVal::Str(reason)] =
        e.args.as_slice()
    else {
        return None;
    };
    let (start, end) = (*start as usize, *end as usize);
    match (e.exc.name(), obj) {
        ("UnicodeDecodeError", PyVal::Bytes(b)) => Some(if end == start + 1 {
            format!(
                "'{enc}' codec can't decode byte 0x{:02x} in position {start}: {reason}",
                b.get(start)?
            )
        } else {
            format!(
                "'{enc}' codec can't decode bytes in position {start}-{}: {reason}",
                end - 1
            )
        }),
        ("UnicodeEncodeError", PyVal::Str(s)) => Some(if end == start + 1 {
            let c = s.chars().nth(start)? as u32;
            let esc = match c {
                0..=0xff => format!("\\x{c:02x}"),
                0x100..=0xffff => format!("\\u{c:04x}"),
                _ => format!("\\U{c:08x}"),
            };
            format!("'{enc}' codec can't encode character '{esc}' in position {start}: {reason}")
        } else {
            format!(
                "'{enc}' codec can't encode characters in position {start}-{}: {reason}",
                end - 1
            )
        }),
        _ => None,
    }
}

/// Text mode's newline translation on read: `\r\n` and `\r` are `\n`.
pub fn universal_newlines(s: String) -> String {
    if s.contains('\r') {
        s.replace("\r\n", "\n").replace('\r', "\n")
    } else {
        s
    }
}

/// `open(path).read()`'s decoding.
pub fn decode_text(b: &[u8]) -> PyResult<String> {
    decode(locale(), b).map(universal_newlines)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The unit tests run under pmon's locale on any host, and the
    /// environment is still read: one of the three codecs, whatever it is.
    #[test]
    fn the_tests_run_under_pmon_s_locale_and_the_environment_is_still_read() {
        assert_eq!(locale(), Codec::Ascii);
        assert!(matches!(
            from_environment(),
            Codec::Ascii | Codec::Utf8 | Codec::Latin1
        ));
    }

    #[test]
    fn errors_read_as_python_words_them() {
        let e = decode(Codec::Ascii, b"ab\xc3\xa4").unwrap_err();
        assert_eq!(
            e.str(),
            "'ascii' codec can't decode byte 0xc3 in position 2: ordinal not in range(128)"
        );
        assert_eq!(
            e.repr(),
            "UnicodeDecodeError('ascii', b'ab\\xc3\\xa4', 2, 3, 'ordinal not in range(128)')"
        );
        assert_eq!(
            decode(Codec::Utf8, b"\xe2\x82\x28").unwrap_err().str(),
            "'utf-8' codec can't decode bytes in position 0-1: invalid continuation byte"
        );
        assert_eq!(
            decode(Codec::Utf8, b"\xff").unwrap_err().str(),
            "'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"
        );
        assert_eq!(
            decode(Codec::Utf8, b"a\xe2\x82").unwrap_err().str(),
            "'utf-8' codec can't decode bytes in position 1-2: unexpected end of data"
        );
        assert_eq!(decode(Codec::Latin1, b"\xe4").unwrap(), "\u{e4}");
        assert_eq!(
            encode_check(Codec::Ascii, "ÄÖÜäöüßé").unwrap_err().str(),
            "'ascii' codec can't encode characters in position 0-7: ordinal not in range(128)"
        );
        assert_eq!(
            encode_check(Codec::Ascii, "ab\u{20ac}c").unwrap_err().str(),
            "'ascii' codec can't encode character '\\u20ac' in position 2: ordinal not in range(128)"
        );
        assert!(encode_check(Codec::Latin1, "\u{e4}").is_ok());
        assert_eq!(universal_newlines("a\r\nb\rc\n".into()), "a\nb\nc\n");
    }
}
