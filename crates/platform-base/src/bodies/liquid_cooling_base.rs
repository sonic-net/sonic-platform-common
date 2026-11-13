//! `LiquidCoolingBase`'s method bodies.

use crate::object::PyObject;
use crate::py::{PyResult, PyVal};

/// `LiquidCoolingBase.get_all_profiles`: `list(self.profiles.values())`.  A
/// native object carries no base-class instance state, so this answers what a
/// base instance constructed with its defaults answers: no profiles were
/// passed in, so `[]`.  An implementation that has profiles overrides it.
pub fn get_all_profiles<S: PyObject + ?Sized>(_s: &S) -> PyResult<PyVal> {
    Ok(PyVal::List(Vec::new()))
}
