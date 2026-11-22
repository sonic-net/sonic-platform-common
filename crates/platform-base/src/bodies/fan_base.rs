//! `FanBase`'s method bodies.

use crate::object::PyObject;
use crate::py::{PyErr, PyResult, PyVal};

/// `FanBase.is_under_speed`: `speed * 100 < target_speed * (100 - tolerance)`.
pub fn is_under_speed<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    let (speed, target, tolerance) = checked(s)?;
    Ok(PyVal::Bool(speed * 100 < target * (100 - tolerance)))
}

/// `FanBase.is_over_speed`: `speed * 100 > target_speed * (100 + tolerance)`.
pub fn is_over_speed<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    let (speed, target, tolerance) = checked(s)?;
    Ok(PyVal::Bool(speed * 100 > target * (100 + tolerance)))
}

/// The three readings, read in the base class's order and held to its rules:
/// each an `int` (a bool is one, in Python) between 0 and 100, or the call
/// raises `TypeError`/`ValueError` with the base class's own text.
fn checked<S: PyObject + ?Sized>(s: &S) -> PyResult<(i128, i128, i128)> {
    let speed = s.get_speed()?;
    let target = s.get_target_speed()?;
    let tolerance = s.get_speed_tolerance()?;
    let mut out = [0i128; 3];
    for (slot, (param, value)) in out.iter_mut().zip([
        ("speed", &speed),
        ("target speed", &target),
        ("speed tolerance", &tolerance),
    ]) {
        let n = match value {
            PyVal::Int(i) => *i,
            PyVal::Bool(b) => i128::from(*b),
            other => {
                return Err(PyErr::type_error(format!(
                    "Fan {param} is not an integer value: {param}={}",
                    other.py_str()
                )))
            }
        };
        if !(0..=100).contains(&n) {
            return Err(PyErr::value_error(format!(
                "Fan {param} is not a valid percentage value: {param}={}",
                value.py_str()
            )));
        }
        *slot = n;
    }
    Ok((out[0], out[1], out[2]))
}
