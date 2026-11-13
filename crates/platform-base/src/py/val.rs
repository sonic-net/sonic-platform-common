//! A Python value.

use std::fmt;
use std::sync::Arc;

use super::fmt::{float_repr, str_repr};
use crate::object::PyObject;

/// A member of a Python `enum.Enum`, such as `LeakSeverity.MINOR`.
///
/// Carried by name and value, not by a Rust enum: the facade reads its
/// `.value`, and its `str()` and `repr()` are Python's, so a native answer has
/// to be able to say all three.
#[derive(Clone, Debug, PartialEq)]
pub struct PyEnum {
    pub class: &'static str,
    pub name: &'static str,
    pub value: Box<PyVal>,
}

/// One Python value, as a getter in `sonic_platform` returns it.
///
/// The variants are the types vendors actually answer with.  `Int` is wide
/// rather than unbounded: no platform reading comes near 2^127.
#[derive(Clone, Default)]
pub enum PyVal {
    #[default]
    None,
    Bool(bool),
    Int(i128),
    Float(f64),
    Str(String),
    Bytes(Vec<u8>),
    Tuple(Vec<PyVal>),
    List(Vec<PyVal>),
    /// In insertion order, as a Python dict iterates.
    Dict(Vec<(PyVal, PyVal)>),
    Enum(PyEnum),
    /// The class `NotImplementedError` itself, *returned* rather than raised.
    ///
    /// Five base-class methods do this -- `return NotImplementedError` -- and
    /// the facade treats it as "no answer".  It is a truthy object, so code
    /// that tests it with `if` sees it as true.
    NotImplementedClass,
    /// A platform object: a fan, a PSU, the chassis.
    Obj(Arc<dyn PyObject>),
}

impl PyVal {
    pub fn str<S: Into<String>>(s: S) -> PyVal {
        PyVal::Str(s.into())
    }

    pub fn int<I: Into<i128>>(i: I) -> PyVal {
        PyVal::Int(i.into())
    }

    pub fn obj<O: PyObject + 'static>(o: O) -> PyVal {
        PyVal::Obj(Arc::new(o))
    }

    pub fn is_none(&self) -> bool {
        matches!(self, PyVal::None)
    }

    /// `type(v).__name__`.
    pub fn type_name(&self) -> String {
        match self {
            PyVal::None => "NoneType".into(),
            PyVal::Bool(_) => "bool".into(),
            PyVal::Int(_) => "int".into(),
            PyVal::Float(_) => "float".into(),
            PyVal::Str(_) => "str".into(),
            PyVal::Bytes(_) => "bytes".into(),
            PyVal::Tuple(_) => "tuple".into(),
            PyVal::List(_) => "list".into(),
            PyVal::Dict(_) => "dict".into(),
            PyVal::Enum(e) => e.class.into(),
            PyVal::NotImplementedClass => "type".into(),
            PyVal::Obj(o) => o.py_class().into(),
        }
    }

    /// `bool(v)`.
    pub fn truthy(&self) -> bool {
        match self {
            PyVal::None => false,
            PyVal::Bool(b) => *b,
            PyVal::Int(i) => *i != 0,
            PyVal::Float(f) => *f != 0.0,
            PyVal::Str(s) => !s.is_empty(),
            PyVal::Bytes(b) => !b.is_empty(),
            PyVal::Tuple(v) | PyVal::List(v) => !v.is_empty(),
            PyVal::Dict(d) => !d.is_empty(),
            PyVal::Enum(_) | PyVal::NotImplementedClass | PyVal::Obj(_) => true,
        }
    }

    /// `str(v)`.
    pub fn py_str(&self) -> String {
        match self {
            PyVal::Str(s) => s.clone(),
            PyVal::Enum(e) => format!("{}.{}", e.class, e.name),
            PyVal::NotImplementedClass => "<class 'NotImplementedError'>".into(),
            other => other.py_repr(),
        }
    }

    /// `repr(v)`.
    pub fn py_repr(&self) -> String {
        match self {
            PyVal::None => "None".into(),
            PyVal::Bool(true) => "True".into(),
            PyVal::Bool(false) => "False".into(),
            PyVal::Int(i) => i.to_string(),
            PyVal::Float(f) => float_repr(*f),
            PyVal::Str(s) => str_repr(s),
            PyVal::Bytes(b) => bytes_repr(b),
            PyVal::Tuple(v) if v.len() == 1 => format!("({},)", v[0].py_repr()),
            PyVal::Tuple(v) => format!("({})", join_repr(v)),
            PyVal::List(v) => format!("[{}]", join_repr(v)),
            PyVal::Dict(d) => format!(
                "{{{}}}",
                d.iter()
                    .map(|(k, v)| format!("{}: {}", k.py_repr(), v.py_repr()))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
            PyVal::Enum(e) => format!("<{}.{}: {}>", e.class, e.name, e.value.py_repr()),
            PyVal::NotImplementedClass => "<class 'NotImplementedError'>".into(),
            PyVal::Obj(o) => format!("<{} object>", o.py_class()),
        }
    }

    /// `a == b`, with Python's numeric tower: `True == 1 == 1.0`.
    pub fn py_eq(&self, other: &PyVal) -> bool {
        use PyVal::*;
        match (self, other) {
            (None, None) | (NotImplementedClass, NotImplementedClass) => true,
            (Str(a), Str(b)) => a == b,
            (Bytes(a), Bytes(b)) => a == b,
            (Tuple(a), Tuple(b)) | (List(a), List(b)) => {
                a.len() == b.len() && a.iter().zip(b).all(|(x, y)| x.py_eq(y))
            }
            (Dict(a), Dict(b)) => {
                a.len() == b.len()
                    && a.iter()
                        .all(|(k, v)| b.iter().any(|(k2, v2)| k.py_eq(k2) && v.py_eq(v2)))
            }
            (Enum(a), Enum(b)) => a.class == b.class && a.name == b.name,
            (Obj(a), Obj(b)) => Arc::ptr_eq(a, b),
            _ => match (self.as_number(), other.as_number()) {
                (Some(Num::I(a)), Some(Num::I(b))) => a == b,
                (Some(a), Some(b)) => a.as_f64() == b.as_f64(),
                _ => false,
            },
        }
    }

    /// The items `for x in v` visits, or `None` if `v` is not iterable.
    ///
    /// A dict iterates its keys and a string its characters, as in Python.
    pub fn iter_items(&self) -> Option<Vec<PyVal>> {
        match self {
            PyVal::Tuple(v) | PyVal::List(v) => Some(v.clone()),
            PyVal::Dict(d) => Some(d.iter().map(|(k, _)| k.clone()).collect()),
            PyVal::Str(s) => Some(s.chars().map(|c| PyVal::Str(c.to_string())).collect()),
            PyVal::Bytes(b) => Some(b.iter().map(|x| PyVal::Int(i128::from(*x))).collect()),
            _ => None,
        }
    }

    pub(crate) fn as_number(&self) -> Option<Num> {
        match self {
            PyVal::Bool(b) => Some(Num::I(i128::from(*b))),
            PyVal::Int(i) => Some(Num::I(*i)),
            PyVal::Float(f) => Some(Num::F(*f)),
            _ => None,
        }
    }
}

#[derive(Clone, Copy)]
pub(crate) enum Num {
    I(i128),
    F(f64),
}

impl Num {
    pub(crate) fn as_f64(self) -> f64 {
        match self {
            Num::I(i) => i as f64,
            Num::F(f) => f,
        }
    }
}

fn join_repr(v: &[PyVal]) -> String {
    v.iter().map(PyVal::py_repr).collect::<Vec<_>>().join(", ")
}

fn bytes_repr(b: &[u8]) -> String {
    let quote = if b.contains(&b'\'') && !b.contains(&b'"') {
        '"'
    } else {
        '\''
    };
    let mut out = String::from("b");
    out.push(quote);
    for &c in b {
        match c {
            b'\\' => out.push_str("\\\\"),
            b'\t' => out.push_str("\\t"),
            b'\n' => out.push_str("\\n"),
            b'\r' => out.push_str("\\r"),
            c if c as char == quote => {
                out.push('\\');
                out.push(quote);
            }
            0x20..=0x7e => out.push(c as char),
            c => out.push_str(&format!("\\x{c:02x}")),
        }
    }
    out.push(quote);
    out
}

impl fmt::Debug for PyVal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.py_repr())
    }
}

impl PartialEq for PyVal {
    /// Structural equality for tests: `1 == 1.0` is *not* equal here, because
    /// a test of what a getter answered has to tell an int from a float.
    fn eq(&self, other: &PyVal) -> bool {
        use PyVal::*;
        match (self, other) {
            (None, None) | (NotImplementedClass, NotImplementedClass) => true,
            (Bool(a), Bool(b)) => a == b,
            (Int(a), Int(b)) => a == b,
            (Float(a), Float(b)) => a.to_bits() == b.to_bits() || a == b,
            (Str(a), Str(b)) => a == b,
            (Bytes(a), Bytes(b)) => a == b,
            (Tuple(a), Tuple(b)) | (List(a), List(b)) => a == b,
            (Dict(a), Dict(b)) => a == b,
            (Enum(a), Enum(b)) => a == b,
            (Obj(a), Obj(b)) => Arc::ptr_eq(a, b),
            _ => false,
        }
    }
}

impl From<bool> for PyVal {
    fn from(b: bool) -> Self {
        PyVal::Bool(b)
    }
}
impl From<&str> for PyVal {
    fn from(s: &str) -> Self {
        PyVal::Str(s.to_string())
    }
}
impl From<String> for PyVal {
    fn from(s: String) -> Self {
        PyVal::Str(s)
    }
}
impl From<f64> for PyVal {
    fn from(f: f64) -> Self {
        PyVal::Float(f)
    }
}
impl From<i64> for PyVal {
    fn from(i: i64) -> Self {
        PyVal::Int(i128::from(i))
    }
}
impl From<i32> for PyVal {
    fn from(i: i32) -> Self {
        PyVal::Int(i128::from(i))
    }
}
impl From<u32> for PyVal {
    fn from(i: u32) -> Self {
        PyVal::Int(i128::from(i))
    }
}
impl<T: Into<PyVal>> From<Option<T>> for PyVal {
    fn from(o: Option<T>) -> Self {
        o.map_or(PyVal::None, Into::into)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::object::BaseClass;

    struct Fan;

    impl PyObject for Fan {
        fn py_class(&self) -> &'static str {
            "Fan"
        }
        fn base_class(&self) -> BaseClass {
            BaseClass::FanBase
        }
    }

    fn minor() -> PyVal {
        PyVal::Enum(PyEnum {
            class: "LeakSeverity",
            name: "MINOR",
            value: Box::new(PyVal::Int(1)),
        })
    }

    #[test]
    fn types_truth_and_text_are_pythons() {
        let fan = PyVal::obj(Fan);
        let names: Vec<String> = [
            PyVal::Bytes(vec![]),
            PyVal::Dict(vec![]),
            minor(),
            fan.clone(),
        ]
        .iter()
        .map(PyVal::type_name)
        .collect();
        assert_eq!(names, ["bytes", "dict", "LeakSeverity", "Fan"]);
        assert!(!PyVal::Bytes(vec![]).truthy() && PyVal::Bytes(b"x".to_vec()).truthy());
        assert!(!PyVal::Dict(vec![]).truthy() && PyVal::Dict(vec![(1.into(), 2.into())]).truthy());
        assert_eq!(minor().py_str(), "LeakSeverity.MINOR");
        assert_eq!(minor().py_repr(), "<LeakSeverity.MINOR: 1>");
        assert_eq!(
            PyVal::NotImplementedClass.py_repr(),
            "<class 'NotImplementedError'>"
        );
        assert_eq!(fan.py_repr(), "<Fan object>");
        assert_eq!(format!("{:?}", PyVal::from(Some("a"))), "'a'");
    }

    #[test]
    fn bytes_repr_picks_its_quote_and_escapes() {
        assert_eq!(PyVal::Bytes(b"it's".to_vec()).py_repr(), r#"b"it's""#);
        assert_eq!(
            PyVal::Bytes(b"say \"hi\"".to_vec()).py_repr(),
            r#"b'say "hi"'"#
        );
        assert_eq!(
            PyVal::Bytes(b"a\\b\t\n\r\x00'\"\x7f".to_vec()).py_repr(),
            r#"b'a\\b\t\n\r\x00\'"\x7f'"#
        );
    }

    #[test]
    fn equality_is_pythons_for_py_eq_and_structural_for_eq() {
        let ab = PyVal::Dict(vec![(1.into(), "a".into()), (2.into(), "b".into())]);
        let ba = PyVal::Dict(vec![(2.into(), "b".into()), (1.into(), "a".into())]);
        assert!(ab.py_eq(&ba) && ab != ba);
        assert!(!ab.py_eq(&PyVal::Dict(vec![(1.into(), "a".into())])));
        assert!(
            PyVal::None.py_eq(&PyVal::None)
                && PyVal::NotImplementedClass.py_eq(&PyVal::NotImplementedClass)
        );
        assert!(PyVal::Bytes(b"x".to_vec()).py_eq(&PyVal::Bytes(b"x".to_vec())));
        assert!(minor().py_eq(&minor()) && minor() == minor());
        let fan = PyVal::obj(Fan);
        assert!(fan.py_eq(&fan.clone()) && fan == fan.clone() && !fan.py_eq(&PyVal::obj(Fan)));
        assert_eq!(PyVal::Bool(true), true.into());
        assert_eq!(PyVal::Bytes(b"x".to_vec()), PyVal::Bytes(b"x".to_vec()));
        assert_eq!(PyVal::List(vec![1.into()]), PyVal::List(vec![1.into()]));
        assert_eq!(ab, ab.clone());
        assert_ne!(PyVal::Int(1), PyVal::Float(1.0));
        assert_eq!(PyVal::from(2.5f64), PyVal::Float(2.5));
        assert_eq!(PyVal::from(-3i64), PyVal::Int(-3));
        assert_eq!(PyVal::from(7u32), PyVal::Int(7));
        assert_eq!(PyVal::from(None::<i32>), PyVal::None);
    }

    #[test]
    fn iterating_a_dict_gives_its_keys_and_bytes_their_ints() {
        let d = PyVal::Dict(vec![("x".into(), 1.into()), ("y".into(), 2.into())]);
        assert_eq!(d.iter_items(), Some(vec!["x".into(), "y".into()]));
        assert_eq!(
            PyVal::Bytes(b"ab".to_vec()).iter_items(),
            Some(vec![97.into(), 98.into()])
        );
        assert_eq!(Num::I(3).as_f64(), 3.0);
    }
}
