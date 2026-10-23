//! What the generated native facade is made of.
//!
//! Two layers, because the PyO3 path has two: `sonic_platform_api/facade.py`
//! turns a vendor's answers into rows (`_call`, `_scalar`, `_text`, ...), and
//! then `platform-pyo3` reads each row's attributes into Rust (`text`, `flag`,
//! `num`, `threshold`, `int_cast`, `err`).  A native implementation is held to
//! what the two do *together*, so both are here, function for function, over
//! [`PyVal`] instead of Python objects.  Each carries the name of the function
//! it stands for; change one only alongside the other.

use platform_api::{Number, PlatformError};

use crate::object::PyObject;
use crate::py::{py_float, py_int, Exc, PyErr, PyResult, PyVal};

// ── facade.py ───────────────────────────────────────────────────────────────

/// `_get(dev, name)` and the call, in one step.
///
/// Python's `getattr(dev, name, None)` is None for anything that is not a
/// platform object -- a vendor list holding `None`, a string -- and the facade
/// then reads the column as unimplemented.  Here that is [`Exc::Missing`], as
/// it is for a method the object's base class does not define.
pub fn get<F>(dev: &PyVal, f: F) -> PyResult<PyVal>
where
    F: FnOnce(&dyn PyObject) -> PyResult<PyVal>,
{
    match dev {
        PyVal::Obj(o) => f(o.as_ref()),
        other => Err(PyErr::missing(&other.type_name(), "?")),
    }
}

/// `_call(fn)`: absent, `NotImplementedError` raised, `None`, or
/// `NotImplementedError` returned are all "no answer".  Anything else raised
/// propagates and takes the row -- and the snapshot -- with it.
pub fn call(r: PyResult<PyVal>) -> PyResult<PyVal> {
    match r {
        Err(e) if matches!(e.exc, Exc::Missing | Exc::NotImplementedError) => Ok(PyVal::None),
        Ok(PyVal::None) | Ok(PyVal::NotImplementedClass) => Ok(PyVal::None),
        other => other,
    }
}

/// `_call_narrowed(fn)`: `_call`, and a `TypeError` is no answer as well.
pub fn call_narrowed(r: PyResult<PyVal>) -> PyResult<PyVal> {
    match call(r) {
        Err(e) if e.exc == Exc::TypeError => Ok(PyVal::None),
        other => other,
    }
}

/// `_call_with_name(name_fn, fn)`: the getter takes the device's own name.
///
/// Python looks the getter up before it reads the name, and reads no name for
/// a getter that is not there.  A native method is only found by calling it,
/// so here the name is read first -- one `get_name` call more, through the
/// same getter the row's own `name` column has already called.
pub fn call_with_name<N, F>(dev: &PyVal, name_fn: N, f: F) -> PyResult<PyVal>
where
    N: FnOnce(&dyn PyObject) -> PyResult<PyVal>,
    F: FnOnce(&dyn PyObject, PyVal) -> PyResult<PyVal>,
{
    let PyVal::Obj(o) = dev else {
        return Ok(PyVal::None);
    };
    let name = call(name_fn(o.as_ref()))?;
    if name.is_none() {
        return Ok(PyVal::None);
    }
    // `fn(name)` passes whatever `get_name` answered, string or not.
    match f(o.as_ref(), name) {
        Err(e) if matches!(e.exc, Exc::NotImplementedError | Exc::Missing) => Ok(PyVal::None),
        Ok(PyVal::NotImplementedClass) => Ok(PyVal::None),
        other => other,
    }
}

/// `_iter(seq)`: `None` is nothing; anything else is iterated, and something
/// that is not iterable raises `TypeError` as `for` would.
pub fn iter(v: PyVal) -> PyResult<Vec<PyVal>> {
    if v.is_none() {
        return Ok(Vec::new());
    }
    v.iter_items()
        .ok_or_else(|| PyErr::type_error(format!("'{}' object is not iterable", v.type_name())))
}

/// `_one(obj)`: a singular accessor as a list of at most one.
pub fn one(v: PyVal) -> Vec<PyVal> {
    if v.is_none() {
        Vec::new()
    } else {
        vec![v]
    }
}

/// `_pairs(mapping)`: a dict's items in order, nothing for anything else.
pub fn pairs(v: PyVal) -> Vec<(PyVal, PyVal)> {
    match v {
        PyVal::Dict(d) => d,
        _ => Vec::new(),
    }
}

/// `_default(v, d)`.
pub fn default(v: PyVal, d: PyVal) -> PyVal {
    if v.is_none() {
        d
    } else {
        v
    }
}

/// `_at(v, i)`: one slot of a tuple; a bare string is slot 0 only.
pub fn at(v: &PyVal, i: usize) -> PyVal {
    match v {
        PyVal::None => PyVal::None,
        PyVal::Str(_) => {
            if i == 0 {
                v.clone()
            } else {
                PyVal::None
            }
        }
        PyVal::Tuple(items) | PyVal::List(items) => items.get(i).cloned().unwrap_or_default(),
        PyVal::Bytes(b) => b.get(i).map_or(PyVal::None, |x| PyVal::Int(i128::from(*x))),
        PyVal::Dict(d) => {
            let key = PyVal::Int(i as i128);
            d.iter()
                .find(|(k, _)| k.py_eq(&key))
                .map_or(PyVal::None, |(_, v)| v.clone())
        }
        _ => PyVal::None,
    }
}

/// `_fmt(v, template, parent, i)`: a name, or the key consumers already use.
///
/// The templates only ever name `{parent}` and `{i}`, which `str.format`
/// replaces; `i` is 1-based.
pub fn fmt_name(v: &PyVal, template: &str, parent: &str, i: usize) -> PyVal {
    if !v.is_none() {
        return PyVal::Str(v.py_str());
    }
    PyVal::Str(
        template
            .replace("{parent}", parent)
            .replace("{i}", &(i + 1).to_string()),
    )
}

/// `_present(v, missing)`: a parent's name, or None where it answered one of
/// `missing` -- `FlattenSource(parent_missing=...)`.
pub fn present(v: &PyVal, missing: &[&str]) -> PyVal {
    if v.is_none() || missing.contains(&v.py_str().as_str()) {
        return PyVal::None;
    }
    v.clone()
}

/// `_raw(v)`: what a parent answered, as thermalctld publishes it --
/// `str(try_get())`, 'N/A' for no answer.
pub fn raw(v: &PyVal) -> PyVal {
    PyVal::Str(if v.is_none() {
        "N/A".to_string()
    } else {
        v.py_str()
    })
}

/// `fixed['key'] in skip`: whether a skippable row is one the caller named.
pub fn skipped(fixed: &[(&str, PyVal)], skip: &std::collections::HashSet<&str>) -> PyResult<bool> {
    match fixed.iter().find(|(k, _)| *k == "key") {
        Some((_, v)) => Ok(skip.contains(v.py_str().as_str())),
        None => Err(PyErr::key_error("key")),
    }
}

/// `_text(v)`: a string column, made a string.
pub fn text(v: PyVal) -> PyVal {
    match v {
        PyVal::None | PyVal::Str(_) => v,
        PyVal::Enum(e) => match *e.value {
            PyVal::Str(s) => PyVal::Str(s),
            other => PyVal::Str(other.py_str()),
        },
        other => PyVal::Str(other.py_str()),
    }
}

/// `_truthy(v)`: `None` stays `None`, anything else is `bool(v)`.
pub fn truthy(v: PyVal) -> PyVal {
    if v.is_none() {
        PyVal::None
    } else {
        PyVal::Bool(v.truthy())
    }
}

/// `_scalar(v, sentinels, coerce_from)`: a sentinel is a missing reading.
pub fn scalar(v: PyVal, sentinels: &[PyVal], coerce_from: &[&str]) -> PyResult<PyVal> {
    if v.is_none() || sentinels.iter().any(|s| v.py_eq(s)) {
        return Ok(PyVal::None);
    }
    match v {
        PyVal::Bool(_) => return Ok(PyVal::None),
        PyVal::Int(_) | PyVal::Float(_) => return Ok(v),
        _ => {}
    }
    for kind in coerce_from {
        if *kind == "str" {
            if let PyVal::Str(s) = &v {
                return Ok(py_float(s).map_or(PyVal::None, PyVal::Float));
            }
        }
        if *kind == "int" {
            // A string is `int(v)` first, which keeps every digit of a whole
            // number; one `int()` refuses ('45.7') is left to the `str` kind.
            if let PyVal::Str(s) = &v {
                match py_int(s) {
                    Ok(i) => return Ok(PyVal::Int(i)),
                    Err(e) if e.exc == Exc::ValueError => continue,
                    Err(e) => return Err(e),
                }
            }
            // Otherwise an integral number is `int(v)` and anything else
            // `float(v)`, catching `TypeError` and `ValueError`.  The numbers
            // have been answered above, so what is left to convert is bytes
            // -- ASCII digits, as `float(b'...')` reads them.
            if let PyVal::Bytes(b) = &v {
                if let Some(f) = std::str::from_utf8(b)
                    .ok()
                    .filter(|s| s.is_ascii())
                    .and_then(|s| py_float(s).ok())
                {
                    return Ok(PyVal::Float(f));
                }
            }
        }
    }
    Ok(PyVal::None)
}

/// `raise DeviceNotFound('no <Row> at %r' % key)`, from `_find_<row>`.
pub fn not_found(row: &str, key: &str) -> PyErr {
    PyErr::device_not_found(format!(
        "no {row} at {}",
        PyVal::Str(key.to_string()).py_repr()
    ))
}

/// `_parse_key(key)`: a DeviceKey as its steps, (collection, position or
/// None), outermost first; `DeviceNotFound` for anything that is not one.
pub fn parse_key(key: &str) -> PyResult<Vec<(String, Option<usize>)>> {
    let bad = || {
        PyErr::device_not_found(format!(
            "not a device key: {}",
            PyVal::Str(key.to_string()).py_repr()
        ))
    };
    if key.is_empty() {
        return Err(bad());
    }
    let mut path = Vec::new();
    for step in key.split('/') {
        // `^([a-z][a-z0-9_]*)(?:\[(0|[1-9][0-9]*)\])?$`
        let (name, pos) = match step.split_once('[') {
            Some((name, rest)) => {
                let digits = rest.strip_suffix(']').ok_or_else(bad)?;
                let canonical = digits == "0" || (!digits.is_empty() && !digits.starts_with('0'));
                if !canonical || !digits.bytes().all(|b| b.is_ascii_digit()) {
                    return Err(bad());
                }
                (name, Some(digits.parse::<usize>().map_err(|_| bad())?))
            }
            None => (step, None),
        };
        let mut chars = name.bytes();
        let first_ok = chars.next().is_some_and(|b| b.is_ascii_lowercase());
        if !first_ok || !chars.all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_') {
            return Err(bad());
        }
        path.push((name.to_string(), pos));
    }
    Ok(path)
}

/// `_shape(path)`: the collections, and which steps carry a position.
pub fn shape(path: &[(String, Option<usize>)]) -> Vec<(&str, bool)> {
    path.iter()
        .map(|(name, pos)| (name.as_str(), pos.is_some()))
        .collect()
}

/// `_nth(seq, pos)`: the device at `pos` in a collection, None past its end
/// or where the collection holds `None`.
pub fn nth(seq: PyVal, pos: Option<usize>) -> PyResult<Option<PyVal>> {
    let items = iter(seq)?;
    Ok(pos
        .and_then(|p| items.into_iter().nth(p))
        .filter(|v| !v.is_none()))
}

/// `raise NotImplementedError('<Class.method> is not implemented')`, from an
/// action whose object has no such method.
pub fn not_implemented(calls: &str) -> PyErr {
    PyErr::not_implemented_msg(format!("{calls} is not implemented"))
}

/// An action's getter, absent: `fn = _get(dev, m); if fn is None: raise ...`.
pub fn action(r: PyResult<PyVal>, calls: &str) -> PyResult<PyVal> {
    match r {
        Err(e) if e.exc == Exc::Missing => Err(not_implemented(calls)),
        other => other,
    }
}

// ── platform-pyo3 ───────────────────────────────────────────────────────────

/// `err(py, e)`: the bridge's mapping of a Python exception.
pub fn err(e: PyErr) -> PlatformError {
    e.to_platform()
}

/// PyO3's text for a value that is not the type it was extracted as.
fn downcast(v: &PyVal, to: &str) -> PlatformError {
    PlatformError::Backend(format!(
        "'{}' object cannot be converted to '{to}'",
        v.type_name()
    ))
}

/// `is_na(v)`: the string "n/a", trimmed, in any case.
fn is_na(v: &PyVal) -> bool {
    matches!(v, PyVal::Str(s) if s.trim().eq_ignore_ascii_case("n/a"))
}

/// `text(row, key)`.
pub fn rd_text(key: &str, v: &PyVal) -> Result<Option<String>, PlatformError> {
    match v {
        PyVal::None => Ok(None),
        PyVal::Str(s) => Ok(Some(s.clone())),
        _ => Err(PlatformError::Backend(format!("{key} is not a string"))),
    }
}

/// `flag(row, key)`.
pub fn rd_flag(v: &PyVal) -> Result<Option<bool>, PlatformError> {
    match v {
        PyVal::None => Ok(None),
        v if is_na(v) => Ok(None),
        PyVal::Bool(b) => Ok(Some(*b)),
        other => Err(downcast(other, "PyBool")),
    }
}

/// PyO3's `f64` extraction: `PyFloat_AsDouble`.
fn as_f64(v: &PyVal) -> Result<f64, PlatformError> {
    match v {
        PyVal::Float(f) => Ok(*f),
        PyVal::Bool(b) => Ok(if *b { 1.0 } else { 0.0 }),
        // Always finite: an i128 is far inside a float's range, so the
        // `OverflowError` Python raises for a larger int cannot arise.
        PyVal::Int(i) => Ok(*i as f64),
        other => Err(PlatformError::Backend(format!(
            "must be real number, not {}",
            other.type_name()
        ))),
    }
}

/// `integer::<T>(row, key)`: an `int` exactly, a float truncated, None where
/// `T` cannot hold it.
pub fn rd_int<T: TryFrom<i128>>(v: &PyVal) -> Result<Option<T>, PlatformError> {
    if is_na(v) {
        return Ok(None);
    }
    ret_int(v)
}

/// `int_of::<T>(v)`, for an action's answer.
pub fn ret_int<T: TryFrom<i128>>(v: &PyVal) -> Result<Option<T>, PlatformError> {
    match v {
        PyVal::None => Ok(None),
        PyVal::Int(i) => Ok(T::try_from(*i).ok()),
        PyVal::Bool(b) => Ok(T::try_from(i128::from(*b)).ok()),
        other => as_f64(other).map(int_cast),
    }
}

/// `int_or_float(row, key)`: int first, a bool is absent.
pub fn rd_number(v: &PyVal) -> Result<Option<Number>, PlatformError> {
    if v.is_none() || is_na(v) || matches!(v, PyVal::Bool(_)) {
        return Ok(None);
    }
    if let PyVal::Int(i) = v {
        if let Ok(i) = i64::try_from(*i) {
            return Ok(Some(Number::Int(i)));
        }
    }
    as_f64(v).map(|f| Some(Number::Float(f)))
}

/// `int_or_float_arg(py, t)`: a number going to the platform as Python's.
pub fn number_val(t: Number) -> PyVal {
    match t {
        Number::Int(i) => PyVal::Int(i128::from(i)),
        Number::Float(f) => PyVal::Float(f),
    }
}

/// `int_cast::<T>(v)`: truncation toward zero, `None` where `T` cannot hold it.
pub fn int_cast<T: TryFrom<i128>>(v: f64) -> Option<T> {
    if !v.is_finite() {
        return None;
    }
    T::try_from(v.trunc() as i128).ok()
}

/// `v.extract::<Option<bool>>()`, for an action's answer.
pub fn ret_bool(v: &PyVal) -> Result<Option<bool>, PlatformError> {
    match v {
        PyVal::None => Ok(None),
        PyVal::Bool(b) => Ok(Some(*b)),
        other => Err(downcast(other, "PyBool")),
    }
}

/// `v.extract::<Option<String>>()`, for an action's answer.
pub fn ret_str(v: &PyVal) -> Result<Option<String>, PlatformError> {
    match v {
        PyVal::None => Ok(None),
        PyVal::Str(s) => Ok(Some(s.clone())),
        other => Err(downcast(other, "PyString")),
    }
}

/// `v.extract::<Option<f64>>()`, for an action's answer.
pub fn ret_num(v: &PyVal) -> Result<Option<f64>, PlatformError> {
    if v.is_none() {
        return Ok(None);
    }
    as_f64(v).map(Some)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// An `int` is exact up to the declared width and absent past it; only a
    /// float is truncated.  Read through f64, 2^53 + 1 came back as 2^53 and
    /// `i64::MAX` as nothing.
    #[test]
    fn an_integer_is_read_exactly_and_only_a_float_is_truncated() {
        assert_eq!(
            rd_int::<i64>(&PyVal::Int(9_007_199_254_740_993)).unwrap(),
            Some(9_007_199_254_740_993)
        );
        assert_eq!(
            rd_int::<i64>(&PyVal::Int(i64::MAX.into())).unwrap(),
            Some(i64::MAX)
        );
        assert_eq!(
            rd_int::<i64>(&PyVal::Int(i128::from(i64::MAX) + 1)).unwrap(),
            None
        );
        assert_eq!(rd_int::<u64>(&PyVal::Int(1 << 63)).unwrap(), Some(1 << 63));
        assert_eq!(rd_int::<u32>(&PyVal::Float(50.7)).unwrap(), Some(50));
        assert_eq!(rd_int::<u32>(&PyVal::Int(-1)).unwrap(), None);
        assert_eq!(rd_int::<u32>(&PyVal::Bool(true)).unwrap(), Some(1));
        assert_eq!(rd_int::<u32>(&PyVal::str("N/A")).unwrap(), None);
        assert_eq!(rd_int::<u32>(&PyVal::None).unwrap(), None);
        assert!(rd_int::<u32>(&PyVal::str("hot")).is_err());
        assert_eq!(
            ret_int::<i64>(&PyVal::Int(i64::MIN.into())).unwrap(),
            Some(i64::MIN)
        );
        assert_eq!(ret_int::<i64>(&PyVal::None).unwrap(), None);
    }

    #[test]
    fn scalar_drops_sentinels_and_bools_and_coerces_what_it_is_told() {
        let na = [PyVal::str("N/A")];
        assert_eq!(scalar(PyVal::str("N/A"), &na, &[]).unwrap(), PyVal::None);
        assert_eq!(scalar(PyVal::Bool(true), &na, &[]).unwrap(), PyVal::None);
        assert_eq!(scalar(PyVal::Int(5), &na, &[]).unwrap(), PyVal::Int(5));
        assert_eq!(
            scalar(PyVal::str("12.5"), &na, &["str"]).unwrap(),
            PyVal::Float(12.5)
        );
        assert_eq!(scalar(PyVal::str("x"), &na, &["str"]).unwrap(), PyVal::None);
        assert_eq!(scalar(PyVal::str("7"), &na, &[]).unwrap(), PyVal::None);
        // A string is `int()` first, keeping every digit of a whole number,
        // then the `str` kind's float; past that, `int` is for the numbers
        // that are neither int nor float, which here is bytes.
        assert_eq!(
            scalar(PyVal::str("7"), &na, &["int"]).unwrap(),
            PyVal::Int(7)
        );
        assert_eq!(
            scalar(PyVal::str("7"), &na, &["int", "str"]).unwrap(),
            PyVal::Int(7)
        );
        assert_eq!(
            scalar(PyVal::str("9007199254740993"), &na, &["int", "str"]).unwrap(),
            PyVal::Int(9007199254740993)
        );
        assert_eq!(
            scalar(PyVal::str("45.7"), &na, &["int", "str"]).unwrap(),
            PyVal::Float(45.7)
        );
        assert_eq!(
            scalar(PyVal::str("45.7"), &na, &["int"]).unwrap(),
            PyVal::None
        );
        assert_eq!(
            scalar(PyVal::Bytes(b"45.7".to_vec()), &na, &["int"]).unwrap(),
            PyVal::Float(45.7)
        );
        assert_eq!(
            scalar(PyVal::Bytes(b"x".to_vec()), &na, &["int", "str"]).unwrap(),
            PyVal::None
        );
        assert_eq!(
            scalar(PyVal::List(vec![]), &na, &["int", "str"]).unwrap(),
            PyVal::None
        );
    }

    #[test]
    fn a_parent_name_can_count_as_none_and_its_raw_answer_is_kept() {
        assert_eq!(present(&PyVal::str("N/A"), &["N/A"]), PyVal::None);
        assert_eq!(
            present(&PyVal::str("drawer1"), &["N/A"]),
            PyVal::str("drawer1")
        );
        assert_eq!(present(&PyVal::None, &["N/A"]), PyVal::None);
        assert_eq!(raw(&PyVal::None), PyVal::str("N/A"));
        assert_eq!(raw(&PyVal::Int(3)), PyVal::str("3"));
        let skip: std::collections::HashSet<&str> = ["thermals[1]"].into_iter().collect();
        assert!(skipped(&[("key", PyVal::str("thermals[1]"))], &skip).unwrap());
        assert!(!skipped(&[("key", PyVal::str("thermals[0]"))], &skip).unwrap());
    }

    #[test]
    fn at_takes_a_slot_and_a_bare_string_is_slot_zero() {
        let t = PyVal::Tuple(vec![PyVal::str("a"), PyVal::str("b")]);
        assert_eq!(at(&t, 1), PyVal::str("b"));
        assert_eq!(at(&t, 2), PyVal::None);
        assert_eq!(at(&PyVal::str("reason"), 0), PyVal::str("reason"));
        assert_eq!(at(&PyVal::str("reason"), 1), PyVal::None);
        assert_eq!(at(&PyVal::Int(3), 0), PyVal::None);
    }

    #[test]
    fn the_readers_fail_the_way_pyo3_fails() {
        assert!(
            matches!(rd_flag(&PyVal::Int(1)), Err(PlatformError::Backend(m)) if m == "'int' object cannot be converted to 'PyBool'")
        );
        assert_eq!(rd_flag(&PyVal::str(" N/a ")).unwrap(), None);
        assert!(
            matches!(rd_number(&PyVal::str("x")), Err(PlatformError::Backend(m)) if m == "must be real number, not str")
        );
        assert_eq!(rd_number(&PyVal::Int(105)).unwrap(), Some(Number::Int(105)));
        assert_eq!(
            rd_number(&PyVal::Float(105.0)).unwrap(),
            Some(Number::Float(105.0))
        );
        assert_eq!(rd_number(&PyVal::Bool(true)).unwrap(), None);
        assert!(
            matches!(rd_text("name", &PyVal::Int(1)), Err(PlatformError::Backend(m)) if m == "name is not a string")
        );
        assert_eq!(int_cast::<u32>(-1.0), None);
        assert_eq!(int_cast::<u32>(50.7), Some(50));
    }

    #[test]
    fn at_indexes_bytes_and_dicts_and_misses_quietly() {
        assert_eq!(at(&PyVal::Bytes(vec![7, 8]), 1), PyVal::Int(8));
        assert_eq!(at(&PyVal::Bytes(vec![7]), 1), PyVal::None);
        let d = PyVal::Dict(vec![(PyVal::Int(0), PyVal::str("zero"))]);
        assert_eq!(at(&d, 0), PyVal::str("zero"));
        assert_eq!(at(&d, 1), PyVal::None);
    }

    #[test]
    fn text_of_an_enum_is_its_value_made_a_string() {
        let e = |value| {
            PyVal::Enum(crate::py::PyEnum {
                class: "Severity",
                name: "MINOR",
                value: Box::new(value),
            })
        };
        assert_eq!(text(e(PyVal::str("minor"))), PyVal::str("minor"));
        assert_eq!(text(e(PyVal::Int(1))), PyVal::str("1"));
    }

    #[test]
    fn a_getter_taking_the_name_that_returns_not_implemented_is_no_answer() {
        let dev = PyVal::obj(crate::object::DynObject {
            class: "Module",
            base: crate::BaseClass::ModuleBase,
            handler: Box::new(|_: &dyn PyObject, _: &str, _: &[PyVal]| None),
        });
        let named = |_: &dyn PyObject| Ok(PyVal::str("DPU0"));
        assert_eq!(
            call_with_name(&dev, named, |_, _| Ok(PyVal::NotImplementedClass)).unwrap(),
            PyVal::None
        );
        assert_eq!(
            call_with_name(&dev, named, |_, n| Ok(n)).unwrap(),
            PyVal::str("DPU0")
        );
    }

    #[test]
    fn numbers_too_wide_or_not_finite_are_read_as_pyo3_reads_them() {
        let wide = 1i128 << 70;
        assert_eq!(
            rd_number(&PyVal::Int(wide)).unwrap(),
            Some(Number::Float(wide as f64))
        );
        assert_eq!(int_cast::<i64>(f64::NAN), None);
        assert_eq!(int_cast::<i64>(f64::INFINITY), None);
        assert_eq!(ret_bool(&PyVal::Bool(true)).unwrap(), Some(true));
        assert!(
            matches!(ret_bool(&PyVal::Int(1)), Err(PlatformError::Backend(m)) if m == "'int' object cannot be converted to 'PyBool'")
        );
    }

    #[test]
    fn a_missing_name_reads_as_its_template() {
        assert_eq!(
            fmt_name(&PyVal::None, "{parent} fan {i}", "PSU 1", 0),
            PyVal::str("PSU 1 fan 1")
        );
        assert_eq!(fmt_name(&PyVal::Int(3), "x", "", 0), PyVal::str("3"));
    }
}
