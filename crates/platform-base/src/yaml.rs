//! `yaml.safe_load` for the configuration files platform code reads: block
//! sequences and mappings of scalars, as PyYAML 1.1 resolves them.
//!
//! The resolution is the part that matters: an unquoted `08` is the string
//! "08" (not an octal number), `10` is the int 10, `yes` is True -- and what
//! a caller does next (`int(value, 16)` raises on an int) follows from it.
//! Flow collections, anchors, tags, block scalars (`|`, `>`), directives and
//! timestamps are not supported and raise; no file the platform reads uses
//! them.  A plain or quoted scalar that goes on over several lines is folded
//! as YAML folds it.

use crate::py::{PyErr, PyResult, PyVal};

fn error(msg: impl Into<String>) -> PyErr {
    PyErr::other("YAMLError", msg)
}

/// One significant line: its indent and the text after it, comments gone.
struct Line {
    indent: usize,
    text: String,
    number: usize,
    /// A comment came between this line and the significant one before it,
    /// on a line of its own or at that line's end.  A comment ends a plain
    /// scalar, so this line cannot go on with one.
    after_comment: bool,
}

/// Whether a quote at `i` opens a scalar: only at a value's start -- first
/// on the line, after `key:`, after a sequence dash or in a flow collection.
/// Anywhere else it is a literal character of a plain scalar.
fn opens_scalar(text: &str, i: usize) -> bool {
    let before = text[..i].trim_end();
    before.is_empty() || (i > before.len() && before.ends_with([':', '-', ',', '[', '{']))
}

/// `text` without a trailing comment -- `#` at the start or after
/// whitespace, outside quotes -- given whether a quoted scalar from an
/// earlier line is still open, which it updates.
fn strip_comment<'a>(text: &'a str, open: &mut Option<u8>) -> &'a str {
    let b = text.as_bytes();
    let mut i = 0;
    while i < b.len() {
        match *open {
            Some(b'\'') => {
                if b[i] == b'\'' {
                    if b.get(i + 1) == Some(&b'\'') {
                        i += 2;
                        continue;
                    }
                    *open = None;
                }
            }
            Some(_) => {
                if b[i] == b'\\' {
                    i += 2;
                    continue;
                }
                if b[i] == b'"' {
                    *open = None;
                }
            }
            None => {
                if (b[i] == b'\'' || b[i] == b'"') && opens_scalar(text, i) {
                    *open = Some(b[i]);
                } else if b[i] == b'#' && (i == 0 || b[i - 1] == b' ' || b[i - 1] == b'\t') {
                    return &text[..i];
                }
            }
        }
        i += 1;
    }
    text
}

fn lines(text: &str) -> PyResult<Vec<Line>> {
    let mut out: Vec<Line> = Vec::new();
    let mut open = None;
    // A comment since the last significant line.
    let mut comment = false;
    for (n, raw) in text.lines().enumerate() {
        if open.is_none() && raw.starts_with('\t') {
            return Err(error(format!(
                "found character '\\t' that cannot start any token (line {})",
                n + 1
            )));
        }
        let stripped = strip_comment(raw, &mut open);
        let has_comment = stripped.len() < raw.len();
        let body = stripped.trim_end();
        if body.trim().is_empty() || body == "..." {
            comment |= has_comment;
            continue;
        }
        let mut text = body;
        if body == "---" || body.starts_with("--- ") {
            if !out.is_empty() {
                return Err(error("expected a single document in the stream"));
            }
            // `--- 5`: the document may start on the marker's own line.
            text = body[3..].trim_start();
            if text.is_empty() {
                comment |= has_comment;
                continue;
            }
        }
        let indent = body.len() - text.trim_start().len();
        out.push(Line {
            indent,
            text: text.trim_start().to_string(),
            number: n + 1,
            after_comment: comment,
        });
        comment = has_comment;
    }
    Ok(out)
}

/// `yaml.safe_load(text)`.
pub fn safe_load(text: &str) -> PyResult<PyVal> {
    let ls = lines(text)?;
    if ls.is_empty() {
        return Ok(PyVal::None);
    }
    let mut pos = 0;
    let indent = ls[0].indent;
    let v = node(&ls, &mut pos, indent)?;
    if pos < ls.len() {
        return Err(error(format!(
            "expected <document end>, but found more content (line {})",
            ls[pos].number
        )));
    }
    Ok(v)
}

/// The node starting at `ls[*pos]`, all of whose lines are at `indent`.
fn node(ls: &[Line], pos: &mut usize, indent: usize) -> PyResult<PyVal> {
    if is_dash(&ls[*pos].text) {
        sequence(ls, pos, indent, None)
    } else if split_key(&ls[*pos].text).is_some() {
        mapping(ls, pos, indent, None)
    } else {
        let v = scalar(&ls[*pos].text)?;
        *pos += 1;
        Ok(v)
    }
}

/// Whether `text` is a sequence entry: a dash alone or before a space.
fn is_dash(text: &str) -> bool {
    text == "-" || text.starts_with("- ")
}

/// A block sequence at `indent`; `first` is the text of an entry that shares
/// its line with an outer sequence's dash, as in `- - 1`.
fn sequence(ls: &[Line], pos: &mut usize, indent: usize, first: Option<String>) -> PyResult<PyVal> {
    let mut items = Vec::new();
    let mut pending = first;
    loop {
        let text = match pending.take() {
            Some(t) => t,
            None if *pos < ls.len() && ls[*pos].indent == indent && is_dash(&ls[*pos].text) => {
                ls[*pos].text.clone()
            }
            None => break,
        };
        let rest = text[1..].trim_start().to_string();
        // The column the entry's own content starts at.
        let child = indent + (text.len() - rest.len());
        if rest.is_empty() {
            *pos += 1;
            if *pos < ls.len() && ls[*pos].indent > indent {
                let child = ls[*pos].indent;
                items.push(node(ls, pos, child)?);
            } else {
                items.push(PyVal::None);
            }
        } else if is_dash(&rest) {
            items.push(sequence(ls, pos, child, Some(rest))?);
        } else if split_key(&rest).is_some() {
            // `- key: value` opens a mapping whose keys sit two columns in.
            items.push(mapping(ls, pos, child, Some(rest))?);
        } else {
            let start = *pos;
            *pos += 1;
            items.push(flow_scalar(ls, pos, &rest, indent, start)?);
        }
    }
    Ok(PyVal::List(items))
}

/// A block mapping at `indent`; `first` is the text of an entry that shares
/// its line with a sequence dash.
fn mapping(ls: &[Line], pos: &mut usize, indent: usize, first: Option<String>) -> PyResult<PyVal> {
    let mut items: Vec<(PyVal, PyVal)> = Vec::new();
    let mut pending = first;
    loop {
        let text = match pending.take() {
            Some(t) => t,
            None => {
                if *pos >= ls.len() || ls[*pos].indent != indent {
                    break;
                }
                ls[*pos].text.clone()
            }
        };
        let Some((k, v)) = split_key(&text) else {
            return Err(error(format!(
                "could not find expected ':' (line {})",
                ls[*pos].number
            )));
        };
        let key = scalar(k)?;
        *pos += 1;
        let value = if v.is_empty() {
            if *pos < ls.len() && ls[*pos].indent > indent {
                let child = ls[*pos].indent;
                node(ls, pos, child)?
            } else if *pos < ls.len() && ls[*pos].indent == indent && is_dash(&ls[*pos].text) {
                // A sequence may sit at its key's own indent.
                sequence(ls, pos, indent, None)?
            } else {
                PyVal::None
            }
        } else {
            flow_scalar(ls, pos, v, indent, *pos - 1)?
        };
        // A later duplicate key wins, as in PyYAML.
        match items.iter_mut().find(|(ek, _)| ek.py_eq(&key)) {
            Some(e) => e.1 = value,
            None => items.push((key, value)),
        }
    }
    Ok(PyVal::Dict(items))
}

/// Whether a quoted scalar opened in `text` is still open at its end.
fn quote_open(text: &str) -> bool {
    let t = text.trim();
    match t.as_bytes().first() {
        Some(b'\'') => {
            let b = &t.as_bytes()[1..];
            let mut i = 0;
            while i < b.len() {
                if b[i] == b'\'' {
                    if b.get(i + 1) == Some(&b'\'') {
                        i += 2;
                        continue;
                    }
                    return false;
                }
                i += 1;
            }
            true
        }
        Some(b'"') => {
            let b = &t.as_bytes()[1..];
            let mut i = 0;
            while i < b.len() {
                match b[i] {
                    b'\\' => i += 2,
                    b'"' => return false,
                    _ => i += 1,
                }
            }
            true
        }
        _ => false,
    }
}

/// A scalar that starts on line `start` with `text` and may go on over the
/// following lines: a quoted one until its closing quote, a plain one while
/// the lines are indented past `indent`.  Line breaks fold as YAML folds
/// them -- a single break is a space, each blank line a newline.
fn flow_scalar(
    ls: &[Line],
    pos: &mut usize,
    text: &str,
    indent: usize,
    start: usize,
) -> PyResult<PyVal> {
    let quoted = text.trim_start().starts_with(['\'', '"']);
    if quoted && !quote_open(text) {
        return scalar(text);
    }
    let mut joined = text.trim_end().to_string();
    let mut last = ls[start].number;
    let mut open = quoted;
    while *pos < ls.len() && (open || ls[*pos].indent > indent) {
        let l = &ls[*pos];
        if !quoted && (l.after_comment || is_dash(&l.text) || split_key(&l.text).is_some()) {
            break;
        }
        for _ in last + 1..l.number {
            joined.push('\n');
        }
        if l.number == last + 1 {
            joined.push(' ');
        }
        joined.push_str(l.text.trim());
        last = l.number;
        *pos += 1;
        if quoted {
            open = quote_open(&joined);
            if !open {
                break;
            }
        }
    }
    if quoted && open {
        return Err(error(
            "found unexpected end of stream while scanning a quoted scalar",
        ));
    }
    scalar(&joined)
}

/// `key: value` at the first `: ` (or trailing `:`) outside quotes.
fn split_key(text: &str) -> Option<(&str, &str)> {
    let b = text.as_bytes();
    let (mut sq, mut dq) = (false, false);
    for i in 0..b.len() {
        match b[i] {
            b'\'' if !dq => sq = !sq,
            b'"' if !sq => dq = !dq,
            b':' if !sq && !dq && (i + 1 == b.len() || b[i + 1] == b' ') => {
                return Some((text[..i].trim(), text[i + 1..].trim()));
            }
            _ => {}
        }
    }
    None
}

/// A scalar, quoted or plain.
fn scalar(text: &str) -> PyResult<PyVal> {
    let t = text.trim();
    if let Some(inner) = t.strip_prefix('\'') {
        let inner = inner.strip_suffix('\'').ok_or_else(|| {
            error("found unexpected end of stream while scanning a quoted scalar")
        })?;
        return Ok(PyVal::Str(inner.replace("''", "'")));
    }
    if let Some(inner) = t.strip_prefix('"') {
        let inner = inner.strip_suffix('"').ok_or_else(|| {
            error("found unexpected end of stream while scanning a quoted scalar")
        })?;
        return unescape(inner).map(PyVal::Str);
    }
    match t {
        "[]" => return Ok(PyVal::List(Vec::new())),
        "{}" => return Ok(PyVal::Dict(Vec::new())),
        _ => {}
    }
    if t.starts_with(['[', '{', '&', '*', '!', '|', '>', '%', '@', '`']) {
        return Err(error(format!("unsupported YAML construct: {t}")));
    }
    resolve_plain(t)
}

fn unescape(s: &str) -> PyResult<String> {
    let mut out = String::new();
    let mut it = s.chars();
    while let Some(c) = it.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        let e = it.next().ok_or_else(|| error("unexpected end of escape"))?;
        // Exactly `n` hex digits: `\x4` is an error, not U+0004.
        let hex = |n: usize, it: &mut std::str::Chars<'_>| -> PyResult<char> {
            let h: String = it.by_ref().take(n).collect();
            Some(&h)
                .filter(|h| h.len() == n && h.bytes().all(|c| c.is_ascii_hexdigit()))
                .and_then(|h| u32::from_str_radix(h, 16).ok())
                .and_then(char::from_u32)
                .ok_or_else(|| error(format!("bad escape \\{e}{h}")))
        };
        out.push(match e {
            '0' => '\0',
            'a' => '\x07',
            'b' => '\x08',
            't' | '\t' => '\t',
            'n' => '\n',
            'v' => '\x0b',
            'f' => '\x0c',
            'r' => '\r',
            'e' => '\x1b',
            ' ' => ' ',
            '"' => '"',
            '/' => '/',
            '\\' => '\\',
            'N' => '\u{85}',
            '_' => '\u{a0}',
            'L' => '\u{2028}',
            'P' => '\u{2029}',
            'x' => hex(2, &mut it)?,
            'u' => hex(4, &mut it)?,
            'U' => hex(8, &mut it)?,
            other => return Err(error(format!("found unknown escape character '{other}'"))),
        });
    }
    Ok(out)
}

fn all(s: &str, f: impl Fn(u8) -> bool) -> bool {
    !s.is_empty() && s.bytes().all(f)
}

/// PyYAML's implicit resolvers for a plain scalar, in its order.
fn resolve_plain(t: &str) -> PyResult<PyVal> {
    match t {
        "yes" | "Yes" | "YES" | "true" | "True" | "TRUE" | "on" | "On" | "ON" => {
            return Ok(PyVal::Bool(true))
        }
        "no" | "No" | "NO" | "false" | "False" | "FALSE" | "off" | "Off" | "OFF" => {
            return Ok(PyVal::Bool(false))
        }
        "" | "~" | "null" | "Null" | "NULL" => return Ok(PyVal::None),
        _ => {}
    }
    if let Some(v) = as_int(t) {
        return Ok(PyVal::Int(v));
    }
    if let Some(v) = as_float(t) {
        return Ok(PyVal::Float(v));
    }
    if is_timestamp(t) {
        return Err(error(format!("YAML timestamps are not supported: {t}")));
    }
    Ok(PyVal::Str(t.to_string()))
}

/// `[-+]?0b[0-1_]+ | [-+]?0[0-7_]+ | [-+]?(0|[1-9][0-9_]*) | [-+]?0x[0-9a-fA-F_]+
/// | [-+]?[1-9][0-9_]*(:[0-5]?[0-9])+`, converted as `construct_yaml_int`.
fn as_int(t: &str) -> Option<i128> {
    let (neg, body) = match t.as_bytes().first() {
        Some(b'-') => (true, &t[1..]),
        Some(b'+') => (false, &t[1..]),
        _ => (false, t),
    };
    let v = if let Some(b) = body.strip_prefix("0b") {
        if !all(b, |c| c == b'0' || c == b'1' || c == b'_') {
            return None;
        }
        i128::from_str_radix(&b.replace('_', ""), 2).ok()?
    } else if let Some(h) = body.strip_prefix("0x") {
        if !all(h, |c| c.is_ascii_hexdigit() || c == b'_') {
            return None;
        }
        i128::from_str_radix(&h.replace('_', ""), 16).ok()?
    } else if body == "0" {
        0
    } else if body.len() > 1 && body.starts_with('0') {
        if !all(&body[1..], |c| (b'0'..=b'7').contains(&c) || c == b'_') {
            return None;
        }
        i128::from_str_radix(&body[1..].replace('_', ""), 8).ok()?
    } else if body.contains(':') {
        let parts: Vec<&str> = body.split(':').collect();
        let first = parts[0];
        if !(first.starts_with(|c: char| ('1'..='9').contains(&c))
            && all(first, |c| c.is_ascii_digit() || c == b'_'))
        {
            return None;
        }
        let mut v: i128 = first.replace('_', "").parse().ok()?;
        for p in &parts[1..] {
            if p.is_empty()
                || p.len() > 2
                || !all(p, |c| c.is_ascii_digit())
                || (p.len() == 2 && p.as_bytes()[0] > b'5')
            {
                return None;
            }
            v = v * 60 + p.parse::<i128>().ok()?;
        }
        v
    } else {
        if !(body.starts_with(|c: char| ('1'..='9').contains(&c))
            && all(body, |c| c.is_ascii_digit() || c == b'_'))
        {
            return None;
        }
        body.replace('_', "").parse().ok()?
    };
    Some(if neg { -v } else { v })
}

/// PyYAML 1.1's float: digits with a dot (and an exponent with a sign),
/// sexagesimal, `.inf`, `.nan`.
fn as_float(t: &str) -> Option<f64> {
    let (neg, body) = match t.as_bytes().first() {
        Some(b'-') => (true, &t[1..]),
        Some(b'+') => (false, &t[1..]),
        _ => (false, t),
    };
    let sign = if neg { -1.0 } else { 1.0 };
    match body {
        ".inf" | ".Inf" | ".INF" => return Some(sign * f64::INFINITY),
        ".nan" | ".NaN" | ".NAN" if !t.starts_with(['-', '+']) => return Some(f64::NAN),
        _ => {}
    }
    let (mant, exp) = match body.find(['e', 'E']) {
        Some(i) => (&body[..i], Some(&body[i + 1..])),
        None => (body, None),
    };
    if let Some(e) = exp {
        let digits = e.strip_prefix(['+', '-'])?;
        if !e.starts_with(['+', '-']) || !all(digits, |c| c.is_ascii_digit()) {
            return None;
        }
    }
    let (int, frac) = mant.split_once('.')?;
    if int.contains(':') {
        return sexagesimal_float(int, frac, exp.is_some()).map(|v| sign * v);
    }
    // `.5` takes no sign: only the digits-first form does.
    let int_ok = (int.is_empty()
        && !t.starts_with(['-', '+'])
        && !frac.is_empty()
        && frac.as_bytes()[0].is_ascii_digit())
        || (int.as_bytes().first().is_some_and(u8::is_ascii_digit)
            && all(int, |c| c.is_ascii_digit() || c == b'_'));
    if !int_ok || !frac.bytes().all(|c| c.is_ascii_digit() || c == b'_') {
        return None;
    }
    let s = format!(
        "{}.{}{}",
        if int.is_empty() { "0" } else { int },
        frac,
        exp.map(|e| format!("e{e}")).unwrap_or_default()
    )
    .replace('_', "");
    s.parse::<f64>().ok().map(|v| sign * v)
}

/// `[0-9][0-9_]*(:[0-5]?[0-9])+\.[0-9_]*` -- no exponent -- converted as
/// `construct_yaml_float` does: each part a float, summed from the last with
/// the base growing by 60.
fn sexagesimal_float(int: &str, frac: &str, has_exp: bool) -> Option<f64> {
    let parts: Vec<&str> = int.split(':').collect();
    let first = parts[0];
    if has_exp
        || !(first.as_bytes().first().is_some_and(u8::is_ascii_digit)
            && all(first, |c| c.is_ascii_digit() || c == b'_'))
        || !frac.bytes().all(|c| c.is_ascii_digit() || c == b'_')
    {
        return None;
    }
    for p in &parts[1..] {
        if p.is_empty()
            || p.len() > 2
            || !all(p, |c| c.is_ascii_digit())
            || (p.len() == 2 && p.as_bytes()[0] > b'5')
        {
            return None;
        }
    }
    let last = format!("{}.{frac}", parts[parts.len() - 1]);
    let mut digits: Vec<String> = parts[..parts.len() - 1]
        .iter()
        .map(|p| p.to_string())
        .collect();
    digits.push(last);
    let (mut value, mut base) = (0.0, 1.0);
    for d in digits.iter().rev() {
        value += d.replace('_', "").parse::<f64>().ok()? * base;
        base *= 60.0;
    }
    Some(value)
}

/// PyYAML's timestamp resolver: a date, or a date and time.  Anything else
/// that merely starts like one -- `2024-1abc`, `2024-1-2` -- is a string.
fn is_timestamp(t: &str) -> bool {
    static TIMESTAMP: std::sync::OnceLock<regex::Regex> = std::sync::OnceLock::new();
    TIMESTAMP
        .get_or_init(|| {
            regex::Regex::new(concat!(
                r"^(?:[0-9]{4}-[0-9]{2}-[0-9]{2}",
                r"|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[Tt]|[ \t]+)[0-9]{1,2}:[0-9]{2}:[0-9]{2}",
                r"(?:\.[0-9]*)?(?:[ \t]*(?:Z|[-+][0-9]{1,2}(?::[0-9]{2})?))?)$",
            ))
            .expect("the timestamp pattern compiles")
        })
        .is_match(t)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(v: &str) -> PyVal {
        PyVal::Str(v.into())
    }

    #[test]
    fn plain_scalars_resolve_as_pyyaml_resolves_them() {
        assert!(resolve_plain("08").unwrap().py_eq(&s("08")));
        assert!(resolve_plain("09").unwrap().py_eq(&s("09")));
        assert!(resolve_plain("07").unwrap().py_eq(&PyVal::Int(7)));
        assert!(resolve_plain("00").unwrap().py_eq(&PyVal::Int(0)));
        assert!(resolve_plain("10").unwrap().py_eq(&PyVal::Int(10)));
        assert!(resolve_plain("1533").unwrap().py_eq(&PyVal::Int(1533)));
        assert!(resolve_plain("1e").unwrap().py_eq(&s("1e")));
        assert!(resolve_plain("1e5").unwrap().py_eq(&s("1e5")));
        assert!(resolve_plain("1.5e+3")
            .unwrap()
            .py_eq(&PyVal::Float(1500.0)));
        assert!(resolve_plain("6fe2").unwrap().py_eq(&s("6fe2")));
        assert!(resolve_plain("0x1f").unwrap().py_eq(&PyVal::Int(31)));
        assert!(resolve_plain("1:30").unwrap().py_eq(&PyVal::Int(90)));
        assert!(resolve_plain("yes").unwrap().py_eq(&PyVal::Bool(true)));
        assert!(resolve_plain("Off").unwrap().py_eq(&PyVal::Bool(false)));
        assert!(resolve_plain("~").unwrap().is_none());
        assert!(resolve_plain("3.").unwrap().py_eq(&PyVal::Float(3.0)));
    }

    #[test]
    fn a_pcie_yaml_loads_as_a_list_of_dicts() {
        let text = "## header\n\n- bus: '00'\n  dev: 08\n  fn: '0'\n  id: 1533\n  name: 'Host bridge: Intel Corporation (rev 01)'\n- bus: 09\n  dev: '00'\n  fn: '1'\n  id: a0b2\n  name: \"Ethernet controller\" # trailing\n";
        let v = safe_load(text).unwrap();
        let PyVal::List(items) = v else {
            panic!("not a list")
        };
        assert_eq!(items.len(), 2);
        let get = |d: &PyVal, k: &str| crate::json::get(d, k).cloned().unwrap();
        assert!(get(&items[0], "dev").py_eq(&s("08")));
        assert!(get(&items[0], "id").py_eq(&PyVal::Int(1533)));
        assert!(get(&items[0], "name").py_eq(&s("Host bridge: Intel Corporation (rev 01)")));
        assert!(get(&items[1], "bus").py_eq(&s("09")));
        assert!(get(&items[1], "name").py_eq(&s("Ethernet controller")));
        assert!(safe_load("# only comments\n").unwrap().is_none());
        let folded = "- bus: '00'\n  name: 'PCI bridge: Intel Corporation Xeon E3-1200 v5/E3-1500 v5/6th Gen Core Processor\n    PCIe Controller (x8) (rev 07)'\n  fn: '1'\n- bus: '01'\n  name: Ethernet controller Mellanox\n    Technologies [ConnectX-6\n    Lx]\n";
        let PyVal::List(items) = safe_load(folded).unwrap() else {
            panic!("not a list")
        };
        assert!(get(&items[0], "name").py_eq(&s("PCI bridge: Intel Corporation Xeon E3-1200 v5/E3-1500 v5/6th Gen Core Processor PCIe Controller (x8) (rev 07)")));
        assert!(get(&items[0], "fn").py_eq(&s("1")));
        assert!(get(&items[1], "name").py_eq(&s(
            "Ethernet controller Mellanox Technologies [ConnectX-6 Lx]"
        )));
    }

    /// `(text, repr(yaml.safe_load(text)))` from PyYAML 6.0.2, "ERROR" for
    /// text it rejects.
    const PYYAML: &[(&str, &str)] = &[
        // A sequence at its key's own indent whose first entry is empty.
        ("list:\n-\n- b\n", "{'list': [None, 'b']}"),
        // The document may start on the `---` line.
        ("--- 5\n", "5"),
        ("--- \na: 1\n", "{'a': 1}"),
        // Only what PyYAML's resolver calls a timestamp is one.
        ("a: 2024-1abc\n", "{'a': '2024-1abc'}"),
        ("a: 2024-1-2\n", "{'a': '2024-1-2'}"),
        // A comment ends a plain scalar; the line after it cannot go on with it.
        ("a: x\n  # c\n  y\n", "ERROR"),
        ("a: 1 # c\n  b\n", "ERROR"),
        ("a: x\n  y\n", "{'a': 'x y'}"),
        ("0b101", "5"),
        ("-0b1", "-1"),
        ("0b12", "'0b12'"),
        ("0o17", "'0o17'"),
        ("017", "15"),
        ("0_17", "15"),
        ("019", "'019'"),
        ("0", "0"),
        ("-0", "0"),
        ("+12", "12"),
        ("1_000", "1000"),
        ("0x_1F", "31"),
        ("0x1g", "'0x1g'"),
        ("0xff", "255"),
        ("-0x10", "-16"),
        ("190:20:30", "685230"),
        ("1:60", "'1:60'"),
        ("1:5", "65"),
        ("01:30", "'01:30'"),
        ("1.5", "1.5"),
        ("-1.5", "-1.5"),
        (".5", "0.5"),
        ("+.5", "'+.5'"),
        ("-.5", "'-.5'"),
        ("1.", "1.0"),
        ("1.5e3", "'1.5e3'"),
        ("1.5e+3", "1500.0"),
        ("1.5E-2", "0.015"),
        ("1_000.5", "1000.5"),
        ("._5", "'._5'"),
        ("1e+3", "'1e+3'"),
        (".inf", "inf"),
        ("-.Inf", "-inf"),
        ("+.INF", "inf"),
        (".nan", "nan"),
        ("-.nan", "'-.nan'"),
        (".NaN", "nan"),
        ("yes", "True"),
        ("No", "False"),
        ("ON", "True"),
        ("off", "False"),
        ("TRUE", "True"),
        ("False", "False"),
        ("y", "'y'"),
        ("n", "'n'"),
        ("~", "None"),
        ("null", "None"),
        ("Null", "None"),
        ("NULL", "None"),
        ("nULL", "'nULL'"),
        ("abc", "'abc'"),
        ("08", "'08'"),
        ("09", "'09'"),
        ("0.", "0.0"),
        ("00", "0"),
        ("1:2:3", "3723"),
        ("2001-12", "'2001-12'"),
        ("20011214", "20011214"),
        ("a b", "'a b'"),
        ("x:y", "'x:y'"),
        ("-", "[None]"),
        ("--", "'--'"),
        ("1_", "1"),
        ("_1", "'_1'"),
        ("0b_1", "1"),
        ("0x", "'0x'"),
        ("1__0", "10"),
        ("12:", "{12: None}"),
        (":5", "':5'"),
        ("1.2.3", "'1.2.3'"),
        ("1e5", "'1e5'"),
        ("6fe2", "'6fe2'"),
        (".", "'.'"),
        ("-.", "'-.'"),
        ("+0x1f", "31"),
        ("+0b1", "1"),
        ("0B1", "'0B1'"),
        ("0X1F", "'0X1F'"),
        // quoted_single
        ("a: 'it''s # not a comment'\n", "{'a': \"it's # not a comment\"}"),
        // quoted_double
        ("a: \"tab\\there \\x41\\u00e9\\U0001F600 \\\\ \\\" \\/ \\0 \\a \\b \\v \\f \\r \\e \\N \\_ \\L \\P \\ \"\n", "{'a': 'tab\\there A\u{e9}\u{1f600} \\\\ \" / \\x00 \\x07 \\x08 \\x0b \\x0c \\r \\x1b \\x85 \\xa0 \\u2028 \\u2029  '}"),
        // quoted_double_bad_escape
        ("a: \"\\q\"\n", "ERROR"),
        // quoted_double_bad_hex
        ("a: \"\\xZZ\"\n", "ERROR"),
        // plain_with_hash
        ("a: x#y # comment\nb: \"#\"\n", "{'a': 'x#y', 'b': '#'}"),
        // nested
        ("top:\n  a: 1\n  b:\n    c: [] \n    d: {}\n  e:\n  - 1\n  - two\n  -\n  - k: v\n    l: w\n", "{'top': {'a': 1, 'b': {'c': [], 'd': {}}, 'e': [1, 'two', None, {'k': 'v', 'l': 'w'}]}}"),
        // seq_at_key_indent
        ("list:\n- a\n- b\nnext: 3\n", "{'list': ['a', 'b'], 'next': 3}"),
        // empty_values
        ("a:\nb: \nc: ~\n", "{'a': None, 'b': None, 'c': None}"),
        // dash_alone_nested
        ("-\n  x: 1\n-\n- 3\n", "[{'x': 1}, None, 3]"),
        // dup_keys
        ("a: 1\nb: 2\na: 3\n", "{'a': 3, 'b': 2}"),
        // markers
        ("---\na: 1\n...\n", "{'a': 1}"),
        // marker_with_content
        ("--- \n- 1\n", "[1]"),
        // two_docs
        ("a: 1\n---\nb: 2\n", "ERROR"),
        // tab
        ("\ta: 1\n", "ERROR"),
        // only_comment
        ("# x\n   # y\n", "None"),
        // empty
        ("", "None"),
        // scalar_doc
        ("hello\n", "'hello'"),
        // int_doc
        ("42\n", "42"),
        // quoted_keys
        ("'k 1': v\n\"k: 2\": w\n3: three\nyes: no\n", "{'k 1': 'v', 'k: 2': 'w', 3: 'three', True: False}"),
        // folded_plain
        ("a: one\n  two\n\n  three\nb: x\n", "{'a': 'one two\\nthree', 'b': 'x'}"),
        // folded_quoted
        ("a: 'one\n  two\n\n  three'\nb: \"x\n  y\"\n", "{'a': 'one two\\nthree', 'b': 'x y'}"),
        // folded_seq
        ("- one\n  two\n- three\n", "['one two', 'three']"),
        // unterminated
        ("a: 'one\n  two\n", "ERROR"),
        // unterminated_double
        ("a: \"one\n", "ERROR"),
        // colon_no_space
        ("url: http://x:80/y\n", "{'url': 'http://x:80/y'}"),
        // trailing_colon_key
        ("a:\n  b:\n", "{'a': {'b': None}}"),
        // deeper_then_shallower
        ("a:\n    b: 1\n    c: 2\nd: 3\n", "{'a': {'b': 1, 'c': 2}, 'd': 3}"),
        // more_content
        ("a: 1\n b: 2\n", "ERROR"),
        // bad_mapping
        ("a: 1\nb\n", "ERROR"),
        // key_with_quotes_inside
        ("a: it's\nb: say \"hi\"\n", "{'a': \"it's\", 'b': 'say \"hi\"'}"),
        // quote_after_text
        ("a: x 'y' z\n", "{'a': \"x 'y' z\"}"),
        // comment_after_quote
        ("a: 'x' # c\nb: \"y\" # d\n", "{'a': 'x', 'b': 'y'}"),
        // pcie
        ("- bus: '00'\n  dev: '1f'\n  fn: '0'\n  id: a0b2\n  name: 'SMBus: Intel'\n- bus: '01'\n  dev: '00'\n  fn: '1'\n  id: 1533\n  name: Ethernet\n", "[{'bus': '00', 'dev': '1f', 'fn': '0', 'id': 'a0b2', 'name': 'SMBus: Intel'}, {'bus': '01', 'dev': '00', 'fn': '1', 'id': 1533, 'name': 'Ethernet'}]"),
        // windows_newlines
        ("a: 1\r\nb: two\r\n", "{'a': 1, 'b': 'two'}"),
        // unicode
        ("name: caf\u{e9}\n", "{'name': 'caf\u{e9}'}"),
        // sequences opening on a dash's line
        ("- - 1\n  - 2\n- - 3\n", "[[1, 2], [3]]"),
        ("- - - x\n    - y\n  - z\n", "[[['x', 'y'], 'z']]"),
        ("- -\n    - a\n", "[[['a']]]"),
        ("- -\n  - a\n", "[[None, 'a']]"),
        ("- - a: 1\n    b: 2\n  - c\n", "[[{'a': 1, 'b': 2}, 'c']]"),
        ("k:\n- - 1\n", "{'k': [[1]]}"),
        // sexagesimal floats, and what is not one
        ("a: 1:30.5\nb: -1:30.5\nc: 1:30:00.25\nd: 0:30.\ne: 190:20:30.15\n", "{'a': 90.5, 'b': -90.5, 'c': 5400.25, 'd': 30.0, 'e': 685230.15}"),
        ("a: 1_0:3_0.5\nb: 1:60.5\nc: +1:2.5e1\nd: 1:2.5e+1\n", "{'a': '1_0:3_0.5', 'b': '1:60.5', 'c': '+1:2.5e1', 'd': '1:2.5e+1'}"),
    ];

    /// What PyYAML loads and this does not: flow collections, anchors,
    /// tags, block scalars, timestamps, directives.
    const UNSUPPORTED: &[&str] = &[
        "a: 2024-01-02 10:00:00\n",
        "a: [1, 2]\n",
        "a: {x: 1}\n",
        "a: &x 1\nb: *x\n",
        "a: !!str 1\n",
        "a: |\n  x\n",
        "a: >\n  x\n",
        "a: 2001-12-14\n",
        "%YAML 1.1\n---\na: 1\n",
        "2001-12-14",
    ];

    #[test]
    fn documents_load_as_pyyaml_loads_them() {
        let mut bad = Vec::new();
        for (text, want) in PYYAML {
            let got = match safe_load(text) {
                Ok(v) => v.py_repr(),
                Err(_) => "ERROR".to_string(),
            };
            if got != *want {
                bad.push(format!("{text:?}\n  pyyaml {want}\n  native {got}"));
            }
        }
        assert!(bad.is_empty(), "{}", bad.join("\n"));
    }

    #[test]
    fn unsupported_constructs_raise() {
        for text in UNSUPPORTED {
            let e = safe_load(text).unwrap_err();
            assert_eq!(e.exc.name(), "YAMLError", "{text:?}");
        }
    }

    #[test]
    fn errors_say_where() {
        let msg = |t: &str| safe_load(t).unwrap_err().str();
        assert_eq!(
            msg("\ta: 1\n"),
            "found character '\\t' that cannot start any token (line 1)"
        );
        assert_eq!(
            msg("a: 1\n---\nb: 2\n"),
            "expected a single document in the stream"
        );
        assert_eq!(
            msg("a: 1\n b: 2\n"),
            "expected <document end>, but found more content (line 2)"
        );
        assert_eq!(
            msg("a: 'x\n"),
            "found unexpected end of stream while scanning a quoted scalar"
        );
        assert_eq!(msg("a: \"\\q\"\n"), "found unknown escape character 'q'");
        assert_eq!(msg("a: \"\\xZZ\"\n"), "bad escape \\xZZ");
        assert_eq!(msg("a: \"\\x4\"\n"), "bad escape \\x4");
        assert_eq!(msg("a: \"\\x+4\"\n"), "bad escape \\x+4");
        assert_eq!(msg("a: \"\\u12\"\n"), "bad escape \\u12");
        assert_eq!(
            msg("a: \"x\\\"\n"),
            "found unexpected end of stream while scanning a quoted scalar"
        );
        assert_eq!(msg("a: [1]\n"), "unsupported YAML construct: [1]");
        assert_eq!(
            msg("a: 2001-12-14\n"),
            "YAML timestamps are not supported: 2001-12-14"
        );
    }

    #[test]
    fn a_quote_opens_a_scalar_only_where_a_value_starts() {
        assert!(opens_scalar("'x'", 0));
        assert!(opens_scalar("a: 'x'", 3));
        assert!(opens_scalar("- 'x'", 2));
        assert!(opens_scalar("[a, 'x']", 4));
        assert!(!opens_scalar("it's", 2));
        assert!(!opens_scalar("a:'x'", 2));
        let mut open = None;
        assert_eq!(strip_comment("a: 'x # y' # z", &mut open), "a: 'x # y' ");
        assert_eq!(
            strip_comment("a: \"x\\\" # y\" # z", &mut open),
            "a: \"x\\\" # y\" "
        );
        assert_eq!(strip_comment("a: 'it''s", &mut open), "a: 'it''s");
        assert_eq!(open, Some(b'\''));
        assert_eq!(
            strip_comment("still'' open' # c", &mut open),
            "still'' open' "
        );
        assert_eq!(open, None);
        assert_eq!(strip_comment("#x", &mut open), "");
        assert_eq!(strip_comment("a#x", &mut open), "a#x");
        assert!(quote_open("'it''s"));
        assert!(!quote_open("'it''s'"));
        assert!(quote_open("\"a\\\""));
        assert!(!quote_open("plain"));
    }

    /// `YAML_CORPUS=<dir> YAML_OUT=<file>`: every `*.yaml` under the
    /// directory, as `path<TAB>repr(safe_load(text))`, for comparing with
    /// PyYAML.  Does nothing without the variables.
    #[test]
    fn corpus_dump() {
        let (Ok(dir), Ok(out)) = (std::env::var("YAML_CORPUS"), std::env::var("YAML_OUT")) else {
            return;
        };
        let mut lines = Vec::new();
        let mut stack = vec![std::path::PathBuf::from(dir)];
        while let Some(d) = stack.pop() {
            for e in std::fs::read_dir(&d).unwrap().flatten() {
                let p = e.path();
                if p.is_dir() {
                    stack.push(p);
                } else if p.extension().is_some_and(|x| x == "yaml") {
                    let text = std::fs::read_to_string(&p).unwrap();
                    let r = match safe_load(&text) {
                        Ok(v) => v.py_repr(),
                        Err(e) => format!("ERROR {}", e.str()),
                    };
                    lines.push(format!("{}\t{r}", p.display()));
                }
            }
        }
        lines.sort();
        std::fs::write(out, lines.join("\n") + "\n").unwrap();
    }
}
