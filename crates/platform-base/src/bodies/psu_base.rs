//! `PsuBase`'s method bodies: the master LED, which is class-level state.
//!
//! `PsuBase.__init__` sets `PsuBase._psu_master_led_color = 'off'` every time
//! any PSU is constructed; `set_status_master_led` is a classmethod that sets
//! the attribute on the class it was called through; `get_status_master_led`
//! reads it through that class, so it finds the nearest class in the MRO that
//! has one, falling back to `PsuBase`'s (None until a PSU has been built).

use std::collections::HashMap;
use std::sync::Mutex;

use crate::object::PyObject;
use crate::py::{PyResult, PyVal};

/// `PsuBase._psu_master_led_color`.
static BASE: Mutex<Option<String>> = Mutex::new(None);
/// The same attribute, set on a vendor class.
static BY_CLASS: Mutex<Option<HashMap<&'static str, String>>> = Mutex::new(None);

/// What `PsuBase.__init__` does to the master LED, for a vendor PSU's
/// constructor to call where its Python one runs `super().__init__()`.
pub fn init() {
    if let Ok(mut b) = BASE.lock() {
        *b = Some("off".to_string());
    }
}

/// `PsuBase.get_status_master_led`.
pub fn get_status_master_led<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    let by_class = BY_CLASS.lock().ok();
    for class in s.py_mro() {
        if let Some(c) = by_class
            .as_ref()
            .and_then(|m| m.as_ref())
            .and_then(|m| m.get(class))
        {
            return Ok(PyVal::Str(c.clone()));
        }
    }
    Ok(BASE
        .lock()
        .ok()
        .and_then(|b| b.clone())
        .map_or(PyVal::None, PyVal::Str))
}

/// `PsuBase.set_status_master_led`: on the class it was called through.
pub fn set_status_master_led<S: PyObject + ?Sized>(s: &S, color: &str) -> PyResult<PyVal> {
    if let Ok(mut m) = BY_CLASS.lock() {
        m.get_or_insert_with(HashMap::new)
            .insert(s.py_class(), color.to_string());
    }
    Ok(PyVal::Bool(true))
}
