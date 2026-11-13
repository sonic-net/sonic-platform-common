//! Python's values and exceptions, as far as a platform API reaches them.
//!
//! A native implementation has to answer exactly what the vendor's Python
//! answered, through a facade and a bridge that both decide by the *type* of
//! the answer: `105` and `105.0` are different thresholds, `'N/A'` is absent in
//! one column and a leak in another, a bool where a number belongs is dropped.
//! So the native side answers in the same terms -- [`PyVal`] -- and fails in
//! the same terms -- [`PyErr`], whose `str()` is what reaches syslog and
//! `PlatformError` text.

pub mod codec;
mod err;
mod fmt;
pub mod intset;
pub mod ops;
mod parse;
mod val;

pub use err::{Exc, PyErr, PyResult};
pub use fmt::{float_repr, str_repr};
pub use parse::{
    decimal_value, int_of_float, is_number_space, is_py_space, py_float, py_int, py_int_base,
    split_ws, splitlines, strip, to_ascii_number, ND_ZEROS,
};
pub use val::{PyEnum, PyVal};
