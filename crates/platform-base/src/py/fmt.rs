//! `repr()` of a float and of a string, as CPython spells them.

/// `repr(f)` -- also `str(f)` in Python 3.
///
/// The shortest digits that read back as the same float, which is what Rust's
/// formatting produces too; what differs is the layout.  Python switches to
/// exponent notation below 1e-4 and at 1e16 and above, writes the exponent
/// with a sign and at least two digits (`1e+16`, `1.5e-05`), and always shows
/// a fraction in fixed notation (`100.0`).  Rust never uses an exponent in
/// `{}`.  A temperature or a power that reaches a log line or a sysfs write
/// goes through here, and `105.0` written as `105` is a different file.
pub fn float_repr(f: f64) -> String {
    if f.is_nan() {
        return "nan".into();
    }
    if f.is_infinite() {
        return if f > 0.0 { "inf".into() } else { "-inf".into() };
    }
    if f == 0.0 {
        return if f.is_sign_negative() {
            "-0.0".into()
        } else {
            "0.0".into()
        };
    }
    // `{:e}` is the shortest round-trip digits, as `d.ddde<exp>`.
    let sci = format!("{:e}", f.abs());
    let (mant, exp) = sci.split_once('e').unwrap_or((sci.as_str(), "0"));
    let exp: i32 = exp.parse().unwrap_or(0);
    let digits: String = mant.chars().filter(|c| *c != '.').collect();
    let sign = if f < 0.0 { "-" } else { "" };

    if (-4..16).contains(&exp) {
        let body = if exp >= 0 {
            let int_len = exp as usize + 1;
            if digits.len() <= int_len {
                format!("{}{}.0", digits, "0".repeat(int_len - digits.len()))
            } else {
                format!("{}.{}", &digits[..int_len], &digits[int_len..])
            }
        } else {
            format!("0.{}{}", "0".repeat((-exp - 1) as usize), digits)
        };
        format!("{sign}{body}")
    } else {
        let mant = if digits.len() == 1 {
            digits
        } else {
            format!("{}.{}", &digits[..1], &digits[1..])
        };
        let esign = if exp < 0 { '-' } else { '+' };
        format!("{sign}{mant}e{esign}{:02}", exp.abs())
    }
}

/// `repr(s)` for a `str`.
///
/// Single quotes unless the string holds a single quote and no double one;
/// backslash, the chosen quote and the usual control characters escaped;
/// other non-printables as `\xNN`, `\uNNNN` or `\UNNNNNNNN`.  Printable
/// non-ASCII is kept, as Python 3 keeps it.
pub fn str_repr(s: &str) -> String {
    let quote = if s.contains('\'') && !s.contains('"') {
        '"'
    } else {
        '\''
    };
    let mut out = String::with_capacity(s.len() + 2);
    out.push(quote);
    for c in s.chars() {
        match c {
            '\\' => out.push_str("\\\\"),
            '\t' => out.push_str("\\t"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            c if c == quote => {
                out.push('\\');
                out.push(c);
            }
            c if (c as u32) < 0x20 || c as u32 == 0x7f => {
                out.push_str(&format!("\\x{:02x}", c as u32))
            }
            c if (c as u32) >= 0x80 && !is_printable(c) => {
                let n = c as u32;
                if n <= 0xff {
                    out.push_str(&format!("\\x{n:02x}"))
                } else if n <= 0xffff {
                    out.push_str(&format!("\\u{n:04x}"))
                } else {
                    out.push_str(&format!("\\U{n:08x}"))
                }
            }
            c => out.push(c),
        }
    }
    out.push(quote);
    out
}

/// An approximation of `str.isprintable()` for non-ASCII: control and
/// format characters, separators other than the space, and unassigned or
/// private-use code points are not printable.  Platform strings are ASCII in
/// practice; this only has to be right where it is cheap to be.
fn is_printable(c: char) -> bool {
    let n = c as u32;
    !(c.is_control()
        || (0x80..=0x9f).contains(&n)
        || n == 0xa0
        || n == 0xad
        || (0x2000..=0x200f).contains(&n)
        || (0x2028..=0x202f).contains(&n)
        || (0xe000..=0xf8ff).contains(&n)
        || n == 0xfeff)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_float_reads_the_way_python_prints_it() {
        // Each pair is (value, what `repr()` prints in CPython 3.13).
        let cases: &[(f64, &str)] = &[
            (105.0, "105.0"),
            (0.5, "0.5"),
            (12.1, "12.1"),
            (1e16, "1e+16"),
            (1.5e16, "1.5e+16"),
            (9999999999999998.0, "9999999999999998.0"),
            (1e-4, "0.0001"),
            (1.5e-5, "1.5e-05"),
            (1e-5, "1e-05"),
            (123456.789, "123456.789"),
            (-2.5, "-2.5"),
            (0.1 + 0.2, "0.30000000000000004"),
            (1e100, "1e+100"),
            (-0.0, "-0.0"),
            (f64::INFINITY, "inf"),
            (f64::NEG_INFINITY, "-inf"),
            (f64::NAN, "nan"),
        ];
        for (v, want) in cases {
            assert_eq!(float_repr(*v), *want, "{v:e}");
        }
    }

    #[test]
    fn a_string_quotes_the_way_python_quotes_it() {
        assert_eq!(str_repr("fan1"), "'fan1'");
        assert_eq!(str_repr("it's"), "\"it's\"");
        assert_eq!(str_repr("a'b\"c"), "'a\\'b\"c'");
        assert_eq!(str_repr("a\nb\\"), "'a\\nb\\\\'");
        assert_eq!(str_repr("\x01"), "'\\x01'");
        assert_eq!(str_repr("é"), "'é'");
    }
}
