//! `ChassisBase`'s method bodies: the system LED, which a switch BMC does not
//! have and every other platform has to implement.

use crate::device_info;
use crate::object::PyObject;
use crate::py::{PyErr, PyResult, PyVal};

/// `ChassisBase.get_status_led`.
#[allow(unused_variables)]
pub fn get_status_led<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    if device_info::is_switch_bmc()? {
        return Ok(PyVal::str("N/A"));
    }
    Err(PyErr::not_implemented())
}

/// `ChassisBase.set_status_led`.
#[allow(unused_variables)]
pub fn set_status_led<S: PyObject + ?Sized>(s: &S, color: &str) -> PyResult<PyVal> {
    if device_info::is_switch_bmc()? {
        return Ok(PyVal::Bool(false));
    }
    Err(PyErr::not_implemented())
}

/// `ChassisBase.initizalize_system_led` (sic).
#[allow(unused_variables)]
pub fn initizalize_system_led<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    if device_info::is_switch_bmc()? {
        return Ok(PyVal::Bool(true));
    }
    Err(PyErr::not_implemented())
}
