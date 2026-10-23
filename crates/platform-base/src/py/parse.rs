//! `int(s)` and `float(s)` on a string, with Python's rules and its errors.
//!
//! Vendors parse sysfs text with these, and what they accept and how they fail
//! decides what a getter answers: `int(" 42\n")` is 42, `int("4.2")` raises,
//! and the message of what it raises is logged verbatim.

use super::err::PyErr;
use super::fmt::str_repr;

/// The first code point of each run of Unicode decimal digits (category Nd,
/// Unicode 15.1 as in Python 3.13): what `\d` matches in a `str` pattern and
/// what `int()` reads as a digit.
pub const ND_ZEROS: [u32; 68] = [
    0x30, 0x660, 0x6f0, 0x7c0, 0x966, 0x9e6, 0xa66, 0xae6, 0xb66, 0xbe6, 0xc66, 0xce6, 0xd66,
    0xde6, 0xe50, 0xed0, 0xf20, 0x1040, 0x1090, 0x17e0, 0x1810, 0x1946, 0x19d0, 0x1a80, 0x1a90,
    0x1b50, 0x1bb0, 0x1c40, 0x1c50, 0xa620, 0xa8d0, 0xa900, 0xa9d0, 0xa9f0, 0xaa50, 0xabf0, 0xff10,
    0x104a0, 0x10d30, 0x11066, 0x110f0, 0x11136, 0x111d0, 0x112f0, 0x11450, 0x114d0, 0x11650,
    0x116c0, 0x11730, 0x118e0, 0x11950, 0x11c50, 0x11d50, 0x11da0, 0x11f50, 0x16a60, 0x16ac0,
    0x16b50, 0x1d7ce, 0x1d7d8, 0x1d7e2, 0x1d7ec, 0x1d7f6, 0x1e140, 0x1e2f0, 0x1e4f0, 0x1e950,
    0x1fbf0,
];

/// A decimal digit's value, in any script.
pub fn decimal_value(c: char) -> Option<u32> {
    let u = c as u32;
    ND_ZEROS
        .iter()
        .find(|&&z| (z..=z + 9).contains(&u))
        .map(|z| u - z)
}

/// What `int()` and `float()` parse (`_PyUnicode_TransformDecimalAndSpaceToASCII`):
/// a decimal digit of any script as its ASCII digit, other whitespace as a
/// space, and anything else past ASCII as a `?` that ends the text.
pub fn to_ascii_number(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        if (c as u32) < 127 {
            out.push(c);
        } else if is_py_space(c) {
            out.push(' ');
        } else if let Some(d) = decimal_value(c) {
            out.push(char::from(b'0' + d as u8));
        } else {
            out.push('?');
            break;
        }
    }
    out
}

/// `Py_ISSPACE`: the space `int()` and `float()` skip around a number --
/// ASCII only, so not `\x1c`..`\x1f`, which `str.strip()` removes.
pub fn is_number_space(c: char) -> bool {
    matches!(c, ' ' | '\t' | '\n' | '\r' | '\x0b' | '\x0c')
}

/// `int(s)` -- base 10.
pub fn py_int(s: &str) -> Result<i128, PyErr> {
    py_int_base(s, 10)
}

/// `int(s, base)` on a string, base 0 or 2 to 36, by CPython's rules: a sign,
/// a `0x`/`0o`/`0b` prefix where the base allows it (base 0 takes its base
/// from it), and single underscores between digits -- or one right after a
/// prefix.  Base 0 refuses a leading zero on a non-zero decimal.
pub fn py_int_base(s: &str, base: u32) -> Result<i128, PyErr> {
    // `%.200R`: the repr cut to 200 characters, as CPython formats it.
    let bad = || {
        let r: String = str_repr(s).chars().take(200).collect();
        PyErr::value_error(format!("invalid literal for int() with base {base}: {r}"))
    };
    let a = to_ascii_number(s);
    let t = a.trim_matches(is_number_space);
    let (neg, body) = split_sign(t);
    let prefix = body.get(..2).map(str::to_ascii_lowercase);
    let (radix, digits, prefixed) = match (base, prefix.as_deref()) {
        (0 | 16, Some("0x")) => (16, &body[2..], true),
        (0 | 8, Some("0o")) => (8, &body[2..], true),
        (0 | 2, Some("0b")) => (2, &body[2..], true),
        (0, _) => (10, body, false),
        (b, _) => (b, body, false),
    };
    let digits = if prefixed {
        digits.strip_prefix('_').unwrap_or(digits)
    } else {
        digits
    };
    let mut clean = String::with_capacity(digits.len());
    let mut after_digit = false;
    for c in digits.chars() {
        if c == '_' && after_digit {
            after_digit = false;
        } else if c.is_digit(radix) {
            clean.push(c);
            after_digit = true;
        } else {
            return Err(bad());
        }
    }
    if !after_digit {
        return Err(bad());
    }
    if base == 0 && radix == 10 && clean.starts_with('0') && clean.bytes().any(|c| c != b'0') {
        return Err(bad());
    }
    let v = i128::from_str_radix(&clean, radix).map_err(|_| bad())?;
    Ok(if neg { -v } else { v })
}

/// `float(s)`.
pub fn py_float(s: &str) -> Result<f64, PyErr> {
    let bad = || {
        PyErr::value_error(format!(
            "could not convert string to float: {}",
            str_repr(s)
        ))
    };
    let a = to_ascii_number(s);
    let t = a.trim_matches(is_number_space);
    let (neg, body) = split_sign(t);
    let lower = body.to_ascii_lowercase();
    let v = match lower.as_str() {
        "inf" | "infinity" => f64::INFINITY,
        "nan" => f64::NAN,
        _ => {
            let clean = strip_underscores(body).ok_or_else(bad)?;
            if !is_decimal_float(&clean) {
                return Err(bad());
            }
            clean.parse::<f64>().map_err(|_| bad())?
        }
    };
    Ok(if neg { -v } else { v })
}

/// `int(f)` for a float: truncation toward zero.
pub fn int_of_float(f: f64) -> Result<i128, PyErr> {
    if f.is_nan() {
        return Err(PyErr::value_error("cannot convert float NaN to integer"));
    }
    if f.is_infinite() {
        return Err(PyErr::overflow_error(
            "cannot convert float infinity to integer",
        ));
    }
    Ok(f.trunc() as i128)
}

fn split_sign(t: &str) -> (bool, &str) {
    if let Some(r) = t.strip_prefix('-') {
        (true, r)
    } else if let Some(r) = t.strip_prefix('+') {
        (false, r)
    } else {
        (false, t)
    }
}

/// Underscores only between two digits, as Python's literals allow.
fn strip_underscores(s: &str) -> Option<String> {
    let b = s.as_bytes();
    let mut out = String::with_capacity(s.len());
    for (i, &c) in b.iter().enumerate() {
        if c == b'_' {
            let ok =
                i > 0 && i + 1 < b.len() && b[i - 1].is_ascii_digit() && b[i + 1].is_ascii_digit();
            if !ok {
                return None;
            }
        } else {
            out.push(c as char);
        }
    }
    Some(out)
}

/// `digits [. digits] [e [sign] digits]`, or `. digits ...`; at least one digit.
fn is_decimal_float(s: &str) -> bool {
    let (mant, exp) = match s.find(['e', 'E']) {
        Some(i) => (&s[..i], Some(&s[i + 1..])),
        None => (s, None),
    };
    let (int, frac) = match mant.split_once('.') {
        Some((a, b)) => (a, Some(b)),
        None => (mant, None),
    };
    let all_digits = |x: &str| x.bytes().all(|b| b.is_ascii_digit());
    if !all_digits(int) || !frac.is_none_or(all_digits) {
        return false;
    }
    if int.is_empty() && frac.is_none_or(str::is_empty) {
        return false;
    }
    match exp {
        None => true,
        Some(e) => {
            let e = e.strip_prefix(['+', '-']).unwrap_or(e);
            !e.is_empty() && all_digits(e)
        }
    }
}

/// `str.splitlines()`: every line boundary Python knows, `\r\n` as one,
/// no empty line after a trailing break.
pub fn splitlines(s: &str) -> Vec<&str> {
    let mut out = Vec::new();
    let mut start = 0;
    let mut it = s.char_indices().peekable();
    while let Some((i, c)) = it.next() {
        if matches!(
            c,
            '\n' | '\r'
                | '\u{b}'
                | '\u{c}'
                | '\u{1c}'
                | '\u{1d}'
                | '\u{1e}'
                | '\u{85}'
                | '\u{2028}'
                | '\u{2029}'
        ) {
            out.push(&s[start..i]);
            let mut end = i + c.len_utf8();
            if c == '\r' && it.peek().is_some_and(|&(_, n)| n == '\n') {
                it.next();
                end += 1;
            }
            start = end;
        }
    }
    if start < s.len() {
        out.push(&s[start..]);
    }
    out
}

/// `str.split()`: runs of whitespace separate, none at either end.
pub fn split_ws(s: &str) -> Vec<&str> {
    s.split(is_py_space).filter(|p| !p.is_empty()).collect()
}

/// `s.strip()`.
pub fn strip(s: &str) -> &str {
    s.trim_matches(is_py_space)
}

/// `str.strip()`'s idea of whitespace, for what sysfs and command output hold.
pub fn is_py_space(c: char) -> bool {
    c.is_whitespace() || ('\u{1c}'..='\u{1f}').contains(&c)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn splitlines_breaks_where_python_does() {
        assert_eq!(
            splitlines("a\r\nb\rc\n\nd\u{2028}e\u{85}"),
            ["a", "b", "c", "", "d", "e"]
        );
        assert_eq!(splitlines(""), Vec::<&str>::new());
        assert_eq!(split_ws("  a \t b\n"), ["a", "b"]);
    }

    #[test]
    fn int_reads_what_python_reads_and_refuses_what_it_refuses() {
        assert_eq!(py_int("42").unwrap(), 42);
        assert_eq!(py_int(" 42\n").unwrap(), 42);
        assert_eq!(py_int("-7").unwrap(), -7);
        assert_eq!(py_int("+7").unwrap(), 7);
        assert_eq!(py_int("1_000").unwrap(), 1000);
        for bad in ["4.2", "", " ", "0x10", "1__0", "_1", "abc", "1 2"] {
            assert!(py_int(bad).is_err(), "{bad:?}");
        }
        assert_eq!(
            py_int("4.2\n").unwrap_err().str(),
            "invalid literal for int() with base 10: '4.2\\n'"
        );
        // `%.200R`: a long literal is quoted only so far, as CPython's is.
        let long = "x".repeat(300);
        assert_eq!(
            py_int(&long).unwrap_err().str(),
            format!(
                "invalid literal for int() with base 10: '{}",
                "x".repeat(199)
            )
        );
    }

    #[test]
    fn int_with_a_base_is_python_s() {
        // Python 3.13's int(s, base).
        let cases: [(&str, u32, Result<i128, &str>); 17] = [
            ("0x_f", 16, Ok(15)),
            (
                "0x",
                16,
                Err("invalid literal for int() with base 16: '0x'"),
            ),
            ("0b1", 16, Ok(177)),
            (
                "1__0",
                16,
                Err("invalid literal for int() with base 16: '1__0'"),
            ),
            (
                "_1",
                16,
                Err("invalid literal for int() with base 16: '_1'"),
            ),
            ("ff", 16, Ok(255)),
            ("0XFF", 16, Ok(255)),
            (" -0x1f ", 16, Ok(-31)),
            (
                "0x+1",
                16,
                Err("invalid literal for int() with base 16: '0x+1'"),
            ),
            (
                "1_",
                10,
                Err("invalid literal for int() with base 10: '1_'"),
            ),
            ("0o17", 8, Ok(15)),
            ("17", 8, Ok(15)),
            ("0b_1", 2, Ok(1)),
            ("z", 36, Ok(35)),
            ("0_1", 10, Ok(1)),
            ("01", 10, Ok(1)),
            ("01", 0, Err("invalid literal for int() with base 0: '01'")),
        ];
        for (s, base, want) in cases {
            assert_eq!(
                py_int_base(s, base).map_err(|e| e.str()),
                want.map_err(String::from),
                "{s:?} {base}"
            );
        }
    }

    #[test]
    fn digits_and_space_of_any_script_are_read_as_python_reads_them() {
        // Python 3.13's int() and float() over the same text.
        assert_eq!(py_int("\u{661}\u{662}").unwrap(), 12);
        assert_eq!(py_int("1_\u{662}").unwrap(), 12);
        assert_eq!(py_int("\u{2003}5\u{2003}").unwrap(), 5);
        assert_eq!(py_int("\u{85}5").unwrap(), 5);
        assert_eq!(py_float("\u{663}.\u{665}e\u{661}").unwrap(), 35.0);
        // str.strip() removes \x1c..\x1f; int() and float() do not.
        for bad in ["\x1c5", "5\x1f", "5\x7f", "5\u{e9}"] {
            assert!(py_int(bad).is_err() && py_float(bad).is_err(), "{bad:?}");
        }
        assert_eq!(decimal_value('\u{1d7ce}'), Some(0));
        assert_eq!(decimal_value('x'), None);
    }

    #[test]
    fn float_reads_what_python_reads_and_refuses_what_it_refuses() {
        assert_eq!(py_float("12.5").unwrap(), 12.5);
        assert_eq!(py_float(" 3 ").unwrap(), 3.0);
        assert_eq!(py_float(".5").unwrap(), 0.5);
        assert_eq!(py_float("5.").unwrap(), 5.0);
        assert_eq!(py_float("1e3").unwrap(), 1000.0);
        assert_eq!(py_float("-Infinity").unwrap(), f64::NEG_INFINITY);
        assert!(py_float("nan").unwrap().is_nan());
        for bad in ["", ".", "e5", "1e", "N/A", "1,5", "0x1"] {
            assert!(py_float(bad).is_err(), "{bad:?}");
        }
        assert_eq!(
            py_float("N/A").unwrap_err().str(),
            "could not convert string to float: 'N/A'"
        );
    }
}
