//! Python's operators on values whose type the code does not check: parsed
//! JSON, mostly, where `'error' in response` is a key test on a dict, a
//! substring test on a str, and a `TypeError` on a number -- and each of those
//! decides which branch, and which log line, follows.

use super::err::{PyErr, PyResult};
use super::val::PyVal;

/// `item in container`.
pub fn contains(container: &PyVal, item: &PyVal) -> PyResult<bool> {
    match container {
        PyVal::Dict(d) => Ok(d.iter().any(|(k, _)| k.py_eq(item))),
        PyVal::List(v) | PyVal::Tuple(v) => Ok(v.iter().any(|x| x.py_eq(item))),
        PyVal::Str(s) => match item {
            PyVal::Str(sub) => Ok(s.contains(sub.as_str())),
            other => Err(PyErr::type_error(format!(
                "'in <string>' requires string as left operand, not {}",
                other.type_name()
            ))),
        },
        // A byte value, or a run of bytes.
        PyVal::Bytes(b) => match item {
            PyVal::Int(i) => match u8::try_from(*i) {
                Ok(byte) => Ok(b.contains(&byte)),
                Err(_) => Err(PyErr::value_error("byte must be in range(0, 256)")),
            },
            PyVal::Bytes(sub) => {
                Ok(sub.is_empty() || b.windows(sub.len()).any(|w| w == sub.as_slice()))
            }
            other => Err(PyErr::type_error(format!(
                "a bytes-like object is required, not '{}'",
                other.type_name()
            ))),
        },
        other => Err(PyErr::type_error(format!(
            "argument of type '{}' is not iterable",
            other.type_name()
        ))),
    }
}

/// `key in container` for a str key.
pub fn has(container: &PyVal, key: &str) -> PyResult<bool> {
    contains(container, &PyVal::str(key))
}

/// `obj[key]`.
pub fn getitem(obj: &PyVal, key: &PyVal) -> PyResult<PyVal> {
    match obj {
        PyVal::Dict(d) => d
            .iter()
            .find(|(k, _)| k.py_eq(key))
            .map(|(_, v)| v.clone())
            .ok_or_else(|| PyErr::key_error(key.clone())),
        PyVal::List(v) | PyVal::Tuple(v) => {
            let what = if matches!(obj, PyVal::List(_)) {
                "list"
            } else {
                "tuple"
            };
            let i = match key {
                PyVal::Int(i) => *i,
                PyVal::Bool(b) => i128::from(*b),
                other => {
                    return Err(PyErr::type_error(format!(
                        "{what} indices must be integers or slices, not {}",
                        other.type_name()
                    )))
                }
            };
            let n = v.len() as i128;
            let j = if i < 0 { i + n } else { i };
            if j < 0 || j >= n {
                return Err(PyErr::index_error(format!("{what} index out of range")));
            }
            Ok(v[j as usize].clone())
        }
        PyVal::Str(s) => {
            let i = match key {
                PyVal::Int(i) => *i,
                PyVal::Bool(b) => i128::from(*b),
                other => {
                    return Err(PyErr::type_error(format!(
                        "string indices must be integers, not '{}'",
                        other.type_name()
                    )))
                }
            };
            let chars: Vec<char> = s.chars().collect();
            let n = chars.len() as i128;
            let j = if i < 0 { i + n } else { i };
            if j < 0 || j >= n {
                return Err(PyErr::index_error("string index out of range"));
            }
            Ok(PyVal::Str(chars[j as usize].to_string()))
        }
        // An item of bytes is an int.
        PyVal::Bytes(b) => {
            let i = match key {
                PyVal::Int(i) => *i,
                PyVal::Bool(x) => i128::from(*x),
                other => {
                    return Err(PyErr::type_error(format!(
                        "byte indices must be integers or slices, not {}",
                        other.type_name()
                    )))
                }
            };
            let n = b.len() as i128;
            let j = if i < 0 { i + n } else { i };
            if j < 0 || j >= n {
                return Err(PyErr::index_error("index out of range"));
            }
            Ok(PyVal::Int(i128::from(b[j as usize])))
        }
        other => Err(PyErr::type_error(format!(
            "'{}' object is not subscriptable",
            other.type_name()
        ))),
    }
}

/// `obj[key]` for a str key.
pub fn item(obj: &PyVal, key: &str) -> PyResult<PyVal> {
    getitem(obj, &PyVal::str(key))
}

/// `obj.get(key, default)`: only a dict has it.
pub fn get(obj: &PyVal, key: &str, default: PyVal) -> PyResult<PyVal> {
    match obj {
        PyVal::Dict(d) => Ok(d
            .iter()
            .find(|(k, _)| matches!(k, PyVal::Str(s) if s == key))
            .map_or(default, |(_, v)| v.clone())),
        other => Err(no_attr(other, "get")),
    }
}

/// `AttributeError: 'int' object has no attribute 'get'`.
pub fn no_attr(obj: &PyVal, name: &str) -> PyErr {
    PyErr::new(
        super::err::Exc::AttributeError,
        vec![PyVal::Str(format!(
            "'{}' object has no attribute '{name}'",
            obj.type_name()
        ))],
    )
}

/// `len(obj)`.
pub fn len(obj: &PyVal) -> PyResult<usize> {
    match obj {
        PyVal::Dict(d) => Ok(d.len()),
        PyVal::List(v) | PyVal::Tuple(v) => Ok(v.len()),
        PyVal::Str(s) => Ok(s.chars().count()),
        PyVal::Bytes(b) => Ok(b.len()),
        other => Err(PyErr::type_error(format!(
            "object of type '{}' has no len()",
            other.type_name()
        ))),
    }
}

/// `for x in obj`.
pub fn iterate(obj: &PyVal) -> PyResult<Vec<PyVal>> {
    obj.iter_items()
        .ok_or_else(|| PyErr::type_error(format!("'{}' object is not iterable", obj.type_name())))
}

/// The str a str method is called on, or the `AttributeError` calling it
/// on anything else raises.
pub fn as_str<'a>(obj: &'a PyVal, method: &str) -> PyResult<&'a str> {
    match obj {
        PyVal::Str(s) => Ok(s),
        other => Err(no_attr(other, method)),
    }
}

/// `dict.items()`, or the `AttributeError`.
pub fn items(obj: &PyVal) -> PyResult<Vec<(PyVal, PyVal)>> {
    match obj {
        PyVal::Dict(d) => Ok(d.clone()),
        other => Err(no_attr(other, "items")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn operators_answer_and_fail_as_python() {
        let d = PyVal::Dict(vec![(PyVal::str("error"), PyVal::Int(1))]);
        assert!(has(&d, "error").unwrap());
        assert!(has(&PyVal::str("an error"), "error").unwrap());
        assert_eq!(
            has(&PyVal::Int(3), "error").unwrap_err().str(),
            "argument of type 'int' is not iterable"
        );
        assert_eq!(
            item(&PyVal::List(vec![]), "a").unwrap_err().str(),
            "list indices must be integers or slices, not str"
        );
        assert_eq!(
            item(&PyVal::str("x"), "a").unwrap_err().str(),
            "string indices must be integers, not 'str'"
        );
        assert_eq!(item(&d, "x").unwrap_err().str(), "'x'");
        assert_eq!(
            item(&PyVal::None, "x").unwrap_err().str(),
            "'NoneType' object is not subscriptable"
        );
        assert_eq!(
            get(&PyVal::List(vec![]), "x", PyVal::None)
                .unwrap_err()
                .str(),
            "'list' object has no attribute 'get'"
        );
        assert_eq!(
            getitem(&PyVal::List(vec![PyVal::Int(1)]), &PyVal::Int(-1))
                .unwrap()
                .py_repr(),
            "1"
        );
    }

    #[test]
    fn in_a_str_needs_a_str() {
        assert_eq!(
            contains(&"abc".into(), &1.into()).unwrap_err().str(),
            "'in <string>' requires string as left operand, not int"
        );
    }

    #[test]
    fn indexing_is_pythons() {
        let l = PyVal::List(vec![1.into(), 2.into()]);
        assert_eq!(getitem(&l, &true.into()).unwrap(), PyVal::Int(2));
        assert_eq!(
            getitem(&l, &5.into()).unwrap_err().str(),
            "list index out of range"
        );
        let s: PyVal = "héllo".into();
        assert_eq!(getitem(&s, &1.into()).unwrap(), PyVal::str("é"));
        assert_eq!(getitem(&s, &(-1).into()).unwrap(), PyVal::str("o"));
        assert_eq!(getitem(&s, &false.into()).unwrap(), PyVal::str("h"));
        assert_eq!(
            getitem(&s, &5.into()).unwrap_err().str(),
            "string index out of range"
        );
    }

    /// Bytes are a sequence of ints, as everywhere else in Python.
    #[test]
    fn bytes_are_a_sequence_of_ints() {
        let b = PyVal::Bytes(b"abc".to_vec());
        assert_eq!(getitem(&b, &0.into()).unwrap(), PyVal::Int(97));
        assert_eq!(getitem(&b, &(-1).into()).unwrap(), PyVal::Int(99));
        assert_eq!(
            getitem(&b, &5.into()).unwrap_err().str(),
            "index out of range"
        );
        assert_eq!(
            item(&b, "x").unwrap_err().str(),
            "byte indices must be integers or slices, not str"
        );
        assert!(contains(&b, &97.into()).unwrap());
        assert!(contains(&b, &PyVal::Bytes(b"bc".to_vec())).unwrap());
        assert!(!contains(&b, &PyVal::Bytes(b"ca".to_vec())).unwrap());
        assert_eq!(
            contains(&b, &300.into()).unwrap_err().str(),
            "byte must be in range(0, 256)"
        );
        assert_eq!(
            has(&b, "a").unwrap_err().str(),
            "a bytes-like object is required, not 'str'"
        );
    }

    #[test]
    fn len_and_items_are_pythons() {
        assert_eq!(len(&PyVal::Dict(vec![(1.into(), 2.into())])).unwrap(), 1);
        assert_eq!(len(&PyVal::Tuple(vec![1.into(), 2.into()])).unwrap(), 2);
        assert_eq!(len(&"héllo".into()).unwrap(), 5);
        assert_eq!(len(&PyVal::Bytes(b"abc".to_vec())).unwrap(), 3);
        assert_eq!(
            len(&5.into()).unwrap_err().str(),
            "object of type 'int' has no len()"
        );
        assert_eq!(
            items(&PyVal::Dict(vec![(1.into(), 2.into())])).unwrap(),
            vec![(1.into(), 2.into())]
        );
        assert_eq!(
            items(&PyVal::List(vec![])).unwrap_err().str(),
            "'list' object has no attribute 'items'"
        );
    }
}
