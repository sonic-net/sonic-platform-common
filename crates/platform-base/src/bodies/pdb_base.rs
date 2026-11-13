//! `PdbBase`'s method bodies: a PDB answers its PSU-shaped readings from its
//! output ones.

use crate::object::PyObject;
use crate::py::{PyResult, PyVal};

/// `PdbBase.get_voltage`: `return self.get_output_voltage()`.
pub fn get_voltage<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    s.get_output_voltage()
}

/// `PdbBase.get_current`: `return self.get_output_current()`.
pub fn get_current<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    s.get_output_current()
}

/// `PdbBase.get_power`: `return self.get_output_power()`.
pub fn get_power<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    s.get_output_power()
}
