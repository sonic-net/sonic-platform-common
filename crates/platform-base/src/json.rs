//! `json.loads`, into Python values, and with Python's errors.
//!
//! A port of CPython's C scanner (`Modules/_json.c`, 3.13): what it accepts
//! (NaN and Infinity, any whitespace of ` \t\n\r`), what it builds (dicts in
//! document order, a repeated key keeping its first place and last value,
//! integers that stay integers), and how it fails -- the message and the
//! character position of every `JSONDecodeError`, which callers log.
//!
//! Two things a Rust string cannot hold are approximated: a lone surrogate
//! from a `\uD800`-style escape becomes U+FFFD, and an integer past the range
//! of i128 becomes the nearest float.

use crate::io;
use crate::py::{PyErr, PyResult, PyVal};

struct Scanner<'a> {
    s: &'a [char],
}

/// `JSONDecodeError(msg, doc, pos)`: `'%s: line %d column %d (char %d)'`.
fn error(chars: &[char], msg: &str, pos: usize) -> PyErr {
    let before = &chars[..pos.min(chars.len())];
    let lineno = before.iter().filter(|&&c| c == '\n').count() + 1;
    let colno = match before.iter().rposition(|&c| c == '\n') {
        Some(nl) => pos - nl,
        None => pos + 1,
    };
    PyErr::other(
        "JSONDecodeError",
        format!("{msg}: line {lineno} column {colno} (char {pos})"),
    )
}

/// What the scanner raises: a decode error, or `StopIteration(idx)` -- no
/// value starts here -- which the caller words as "Expecting value".
enum Fail {
    Error(PyErr),
    Stop(usize),
}

type Scan<T> = Result<T, Fail>;

impl Scanner<'_> {
    fn err(&self, msg: &str, pos: usize) -> Fail {
        Fail::Error(error(self.s, msg, pos))
    }

    fn at(&self, i: usize) -> Option<char> {
        self.s.get(i).copied()
    }

    fn skip_ws(&self, mut i: usize) -> usize {
        while matches!(self.at(i), Some(' ' | '\t' | '\n' | '\r')) {
            i += 1;
        }
        i
    }

    fn matches(&self, i: usize, word: &str) -> bool {
        let w: Vec<char> = word.chars().collect();
        self.s.get(i..i + w.len()) == Some(&w[..])
    }

    /// `scan_once(s, idx)`: one value, and where it ends.
    fn scan_once(&self, idx: usize) -> Scan<(PyVal, usize)> {
        let Some(c) = self.at(idx) else {
            return Err(Fail::Stop(idx));
        };
        match c {
            '"' => self.scanstring(idx + 1).map(|(s, e)| (PyVal::Str(s), e)),
            '{' => self.parse_object(idx + 1),
            '[' => self.parse_array(idx + 1),
            'n' if self.matches(idx, "null") => Ok((PyVal::None, idx + 4)),
            't' if self.matches(idx, "true") => Ok((PyVal::Bool(true), idx + 4)),
            'f' if self.matches(idx, "false") => Ok((PyVal::Bool(false), idx + 5)),
            'N' if self.matches(idx, "NaN") => Ok((PyVal::Float(f64::NAN), idx + 3)),
            'I' if self.matches(idx, "Infinity") => Ok((PyVal::Float(f64::INFINITY), idx + 8)),
            '-' if self.matches(idx, "-Infinity") => Ok((PyVal::Float(f64::NEG_INFINITY), idx + 9)),
            _ => self.match_number(idx),
        }
    }

    /// `_match_number_unicode`.
    fn match_number(&self, start: usize) -> Scan<(PyVal, usize)> {
        let digit = |i: usize| self.at(i).is_some_and(|c| c.is_ascii_digit());
        let len = self.s.len();
        let mut idx = start;
        if self.at(idx) == Some('-') {
            idx += 1;
            if idx >= len {
                return Err(Fail::Stop(start));
            }
        }
        match self.at(idx) {
            Some('1'..='9') => {
                idx += 1;
                while digit(idx) {
                    idx += 1;
                }
            }
            Some('0') => idx += 1,
            _ => return Err(Fail::Stop(start)),
        }
        let mut is_float = false;
        if idx + 1 < len && self.at(idx) == Some('.') && digit(idx + 1) {
            is_float = true;
            idx += 2;
            while digit(idx) {
                idx += 1;
            }
        }
        if idx + 1 < len && matches!(self.at(idx), Some('e' | 'E')) {
            let e_start = idx;
            idx += 1;
            if idx + 1 < len && matches!(self.at(idx), Some('-' | '+')) {
                idx += 1;
            }
            while digit(idx) {
                idx += 1;
            }
            if digit(idx - 1) {
                is_float = true;
            } else {
                idx = e_start;
            }
        }
        let num: String = self.s[start..idx].iter().collect();
        let v = if is_float {
            PyVal::Float(num.parse::<f64>().unwrap_or(f64::NAN))
        } else {
            match num.parse::<i128>() {
                Ok(i) => PyVal::Int(i),
                Err(_) => PyVal::Float(num.parse::<f64>().unwrap_or(f64::NAN)),
            }
        };
        Ok((v, idx))
    }

    /// `scanstring(s, end)`: `end` is just past the opening quote.
    fn scanstring(&self, end: usize) -> Scan<(String, usize)> {
        let begin = end - 1;
        let len = self.s.len();
        let mut out = String::new();
        let mut next = end;
        loop {
            let Some(c) = self.at(next) else {
                return Err(self.err("Unterminated string starting at", begin));
            };
            if c == '"' {
                return Ok((out, next + 1));
            }
            if c != '\\' {
                if (c as u32) <= 0x1f {
                    return Err(self.err("Invalid control character at", next));
                }
                out.push(c);
                next += 1;
                continue;
            }
            next += 1;
            let Some(c) = self.at(next) else {
                return Err(self.err("Unterminated string starting at", begin));
            };
            if c != 'u' {
                let ch = match c {
                    '"' => '"',
                    '\\' => '\\',
                    '/' => '/',
                    'b' => '\u{8}',
                    'f' => '\u{c}',
                    'n' => '\n',
                    'r' => '\r',
                    't' => '\t',
                    _ => return Err(self.err("Invalid \\escape", next - 1)),
                };
                out.push(ch);
                next += 1;
                continue;
            }
            // \uXXXX, and a low surrogate's escape right after a high one.
            next += 1;
            let hex4 = |at: usize| -> Option<u32> {
                if at + 4 >= len {
                    return None;
                }
                let s: String = self.s[at..at + 4].iter().collect();
                if s.chars().all(|c| c.is_ascii_hexdigit()) {
                    u32::from_str_radix(&s, 16).ok()
                } else {
                    None
                }
            };
            let Some(mut u) = hex4(next) else {
                return Err(self.err("Invalid \\uXXXX escape", next - 1));
            };
            next += 4;
            if (0xd800..=0xdbff).contains(&u)
                && next + 6 < len
                && self.at(next) == Some('\\')
                && self.at(next + 1) == Some('u')
            {
                let Some(u2) = hex4(next + 2) else {
                    return Err(self.err("Invalid \\uXXXX escape", next + 1));
                };
                if (0xdc00..=0xdfff).contains(&u2) {
                    u = 0x10000 + (((u - 0xd800) << 10) | (u2 - 0xdc00));
                    next += 6;
                }
            }
            out.push(char::from_u32(u).unwrap_or('\u{fffd}'));
        }
    }

    /// `_parse_object_unicode`: `idx` is just past the `{`.
    fn parse_object(&self, idx: usize) -> Scan<(PyVal, usize)> {
        let mut items: Vec<(PyVal, PyVal)> = Vec::new();
        let mut idx = self.skip_ws(idx);
        if self.at(idx) == Some('}') {
            return Ok((PyVal::Dict(items), idx + 1));
        }
        loop {
            if self.at(idx) != Some('"') {
                return Err(self.err("Expecting property name enclosed in double quotes", idx));
            }
            let (key, e) = self.scanstring(idx + 1)?;
            idx = self.skip_ws(e);
            if self.at(idx) != Some(':') {
                return Err(self.err("Expecting ':' delimiter", idx));
            }
            idx = self.skip_ws(idx + 1);
            let (val, e) = match self.scan_once(idx) {
                Ok(v) => v,
                Err(Fail::Stop(i)) => return Err(self.err("Expecting value", i)),
                Err(e) => return Err(e),
            };
            match items
                .iter_mut()
                .find(|(k, _)| matches!(k, PyVal::Str(s) if *s == key))
            {
                Some(slot) => slot.1 = val,
                None => items.push((PyVal::Str(key), val)),
            }
            idx = self.skip_ws(e);
            match self.at(idx) {
                Some('}') => return Ok((PyVal::Dict(items), idx + 1)),
                Some(',') => {}
                _ => return Err(self.err("Expecting ',' delimiter", idx)),
            }
            let comma = idx;
            idx = self.skip_ws(idx + 1);
            if self.at(idx) == Some('}') {
                return Err(self.err("Illegal trailing comma before end of object", comma));
            }
        }
    }

    /// `_parse_array_unicode`: `idx` is just past the `[`.
    fn parse_array(&self, idx: usize) -> Scan<(PyVal, usize)> {
        let mut items = Vec::new();
        let mut idx = self.skip_ws(idx);
        if self.at(idx) == Some(']') {
            return Ok((PyVal::List(items), idx + 1));
        }
        loop {
            let (val, e) = match self.scan_once(idx) {
                Ok(v) => v,
                Err(Fail::Stop(i)) => return Err(self.err("Expecting value", i)),
                Err(e) => return Err(e),
            };
            items.push(val);
            idx = self.skip_ws(e);
            match self.at(idx) {
                Some(']') => return Ok((PyVal::List(items), idx + 1)),
                Some(',') => {}
                _ => return Err(self.err("Expecting ',' delimiter", idx)),
            }
            let comma = idx;
            idx = self.skip_ws(idx + 1);
            if self.at(idx) == Some(']') {
                return Err(self.err("Illegal trailing comma before end of array", comma));
            }
        }
    }
}

/// `json.loads(text)`.
pub fn loads(text: &str) -> PyResult<PyVal> {
    let chars: Vec<char> = text.chars().collect();
    if chars.first() == Some(&'\u{feff}') {
        return Err(error(
            &chars,
            "Unexpected UTF-8 BOM (decode using utf-8-sig)",
            0,
        ));
    }
    let sc = Scanner { s: &chars };
    let start = sc.skip_ws(0);
    let (v, end) = match sc.scan_once(start) {
        Ok(v) => v,
        Err(Fail::Stop(i)) => return Err(error(&chars, "Expecting value", i)),
        Err(Fail::Error(e)) => return Err(e),
    };
    let end = sc.skip_ws(end);
    if end != chars.len() {
        return Err(error(&chars, "Extra data", end));
    }
    Ok(v)
}

/// `json.load(open(path))`.
pub fn load(path: &str) -> PyResult<PyVal> {
    loads(&io::read_text(path)?)
}

/// `d[key]` on a dict answered by [`load`]: `KeyError` if absent, `TypeError`
/// if it is not a dict.
pub fn index<'a>(d: &'a PyVal, key: &str) -> PyResult<&'a PyVal> {
    match d {
        PyVal::Dict(items) => items
            .iter()
            .find(|(k, _)| matches!(k, PyVal::Str(s) if s == key))
            .map(|(_, v)| v)
            .ok_or_else(|| PyErr::key_error(key)),
        // A str key on anything but a dict raises, worded by type: `string
        // indices must be integers`, `list indices must be ...`, `... is not
        // subscriptable` -- `getitem`'s words for it.
        other => Err(crate::py::ops::getitem(other, &PyVal::str(key))
            .expect_err("only a dict is subscripted by a str")),
    }
}

/// `d.get(key)`: `None` when absent or when `d` is not a dict.
pub fn get<'a>(d: &'a PyVal, key: &str) -> Option<&'a PyVal> {
    match d {
        PyVal::Dict(items) => items
            .iter()
            .find(|(k, _)| matches!(k, PyVal::Str(s) if s == key))
            .map(|(_, v)| v),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Python's answer for each input, as `repr(json.loads(s))` or
    /// `JSONDecodeError <message>`, one per line (`input<TAB>answer`, inputs
    /// JSON-escaped): tests/data/json.tsv, or the corpus `JSON_CORPUS` names.
    #[test]
    fn corpus_matches_python() {
        let text = match std::env::var("JSON_CORPUS") {
            Ok(path) => std::fs::read_to_string(path).unwrap(),
            Err(_) => include_str!("../tests/data/json.tsv").to_string(),
        };
        let mut bad = 0;
        for line in text.lines() {
            let (input, want) = line.split_once('\t').unwrap();
            let input = match loads(input).unwrap() {
                PyVal::Str(s) => s,
                _ => panic!(),
            };
            let got = match loads(&input) {
                Ok(v) => v.py_repr(),
                Err(e) => format!("{} {}", e.exc.name(), e.str()),
            };
            if got != want {
                bad += 1;
                eprintln!("{input:?}\n  python: {want}\n  native: {got}");
            }
        }
        assert_eq!(bad, 0);
    }

    #[test]
    fn errors_read_as_python_words_them() {
        let e = |s: &str| loads(s).unwrap_err().str();
        assert_eq!(e(""), "Expecting value: line 1 column 1 (char 0)");
        assert_eq!(
            e("{\"a\":1,}"),
            "Illegal trailing comma before end of object: line 1 column 7 (char 6)"
        );
        assert_eq!(
            e("[1 2]"),
            "Expecting ',' delimiter: line 1 column 4 (char 3)"
        );
        assert_eq!(e("\"a\\x\""), "Invalid \\escape: line 1 column 3 (char 2)");
        assert_eq!(
            e("\"\\u12\""),
            "Invalid \\uXXXX escape: line 1 column 3 (char 2)"
        );
        assert_eq!(
            e("{\"a\":\"\n\"}"),
            "Invalid control character at: line 1 column 7 (char 6)"
        );
        assert_eq!(e("01"), "Extra data: line 1 column 2 (char 1)");
        assert_eq!(
            e("{\n\"a\" 1}"),
            "Expecting ':' delimiter: line 2 column 5 (char 6)"
        );
        assert_eq!(
            loads("{\"a\":1,\"b\":2,\"a\":3}").unwrap().py_repr(),
            "{'a': 3, 'b': 2}"
        );
        assert_eq!(
            loads(" [1.5e3, -0, 1E2, \"\\ud83d\\ude00\"] ")
                .unwrap()
                .py_repr(),
            "[1500.0, 0, 100.0, '\u{1f600}']"
        );
    }

    #[test]
    fn indexing_a_non_dict_raises_pythons_type_error() {
        let msg = |v: &str| index(&loads(v).unwrap(), "k").unwrap_err().str();
        assert_eq!(msg(r#""s""#), "string indices must be integers, not 'str'");
        assert_eq!(
            msg("[1]"),
            "list indices must be integers or slices, not str"
        );
        assert_eq!(msg("1"), "'int' object is not subscriptable");
        assert_eq!(msg("null"), "'NoneType' object is not subscriptable");
        assert_eq!(msg("{}"), "'k'");
    }
}
