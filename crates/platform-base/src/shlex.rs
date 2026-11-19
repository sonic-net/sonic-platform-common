//! `shlex.split(s)`: POSIX mode, no comments -- how the Redfish client turns
//! the curl command lines it builds as strings into argv.

use crate::py::{PyErr, PyResult};

const WHITESPACE: &str = " \t\r\n";

/// `shlex.split(s)`.
pub fn split(s: &str) -> PyResult<Vec<String>> {
    let mut chars = s.chars();
    let mut out = Vec::new();
    // `None` is the lexer's end state.
    let mut state = Some(' ');
    loop {
        let mut token = String::new();
        let mut quoted = false;
        let mut escaped_state = ' ';
        loop {
            let next = chars.next();
            match state {
                None => break,
                Some(' ') => match next {
                    None => {
                        state = None;
                        break;
                    }
                    Some(c) if WHITESPACE.contains(c) => {
                        if !token.is_empty() || quoted {
                            break;
                        }
                    }
                    Some('\\') => {
                        escaped_state = 'a';
                        state = Some('\\');
                    }
                    Some(c @ ('\'' | '"')) => state = Some(c),
                    Some(c) => {
                        token.push(c);
                        state = Some('a');
                    }
                },
                Some(q @ ('\'' | '"')) => {
                    quoted = true;
                    match next {
                        None => return Err(PyErr::value_error("No closing quotation")),
                        Some(c) if c == q => state = Some('a'),
                        Some('\\') if q == '"' => {
                            escaped_state = q;
                            state = Some('\\');
                        }
                        Some(c) => token.push(c),
                    }
                }
                Some('\\') => {
                    let Some(c) = next else {
                        return Err(PyErr::value_error("No escaped character"));
                    };
                    // Inside double quotes only \\ and \" are escapes.
                    if escaped_state == '"' && c != '\\' && c != '"' {
                        token.push('\\');
                    }
                    token.push(c);
                    state = Some(escaped_state);
                }
                Some(_) => match next {
                    None => {
                        state = None;
                        break;
                    }
                    Some(c) if WHITESPACE.contains(c) => {
                        state = Some(' ');
                        if !token.is_empty() || quoted {
                            break;
                        }
                    }
                    Some(c @ ('\'' | '"')) => state = Some(c),
                    Some('\\') => {
                        escaped_state = 'a';
                        state = Some('\\');
                    }
                    Some(c) => token.push(c),
                },
            }
        }
        // An empty token that was never quoted is the end of input.
        if token.is_empty() && !quoted {
            return Ok(out);
        }
        out.push(token);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// One JSON array per line, `[input, answer]`, the answer a list of
    /// tokens or the ValueError's text: tests/data/shlex.jsonl, or the corpus
    /// `SHLEX_CORPUS` names.
    #[test]
    fn corpus_matches_python() {
        let text = match std::env::var("SHLEX_CORPUS") {
            Ok(path) => std::fs::read_to_string(path).unwrap(),
            Err(_) => include_str!("../tests/data/shlex.jsonl").to_string(),
        };
        let mut bad = 0;
        for line in text.lines() {
            let v = crate::json::loads(line).unwrap();
            let crate::py::PyVal::List(pair) = v else {
                panic!()
            };
            let crate::py::PyVal::Str(input) = &pair[0] else {
                panic!()
            };
            let got = match split(input) {
                Ok(t) => crate::py::PyVal::List(t.into_iter().map(crate::py::PyVal::Str).collect()),
                Err(e) => crate::py::PyVal::Str(e.str()),
            };
            if !got.py_eq(&pair[1]) {
                bad += 1;
                eprintln!(
                    "{input:?}: python {} native {}",
                    pair[1].py_repr(),
                    got.py_repr()
                );
            }
        }
        assert_eq!(bad, 0);
    }

    #[test]
    fn splits_as_shlex_does() {
        assert_eq!(
            split(r#"/usr/bin/curl -k -H "X-Auth-Token: abc" -d '{"UserName" : "u"}' -w "\nHTTP Status Code: %{http_code}""#).unwrap(),
            ["/usr/bin/curl", "-k", "-H", "X-Auth-Token: abc", "-d", r#"{"UserName" : "u"}"#, "-w", "\\nHTTP Status Code: %{http_code}"]
        );
        assert_eq!(
            split(r#"a\ b "c\"d" '' x"'y'"z"#).unwrap(),
            ["a b", "c\"d", "", "x'y'z"]
        );
        assert_eq!(split("  ").unwrap(), Vec::<String>::new());
        assert_eq!(split("'abc").unwrap_err().str(), "No closing quotation");
        assert_eq!(split("abc\\").unwrap_err().str(), "No escaped character");
        assert_eq!(split(r#""a\$b""#).unwrap(), ["a\\$b"]);
    }
}
