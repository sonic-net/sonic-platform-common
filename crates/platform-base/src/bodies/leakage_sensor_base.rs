//! `LeakageSensorBase`'s method bodies.

use crate::object::PyObject;
use crate::py::{PyResult, PyVal};

/// `LeakageSensorBase.get_leak_severity`: `self.leak_severity if self.leaking
/// else None`.  A native object carries no base-class instance state, so this
/// answers what a base instance constructed with its defaults answers: no leak
/// recorded, so None.  An implementation that records leaks overrides it, as
/// it overrides `is_leak`.
pub fn get_leak_severity<S: PyObject + ?Sized>(_s: &S) -> PyResult<PyVal> {
    Ok(PyVal::None)
}
