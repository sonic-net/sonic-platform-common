//! `TlvInfoDecoder`'s method bodies.
//!
//! Both read the instance's EEPROM path and cache, which a native object
//! holds itself -- so they are not answered here.  The decoder itself is
//! [`crate::eeprom_tlvinfo::TlvInfoDecoder`]: a vendor's EEPROM object builds
//! one and answers these two through it.

use crate::object::PyObject;
use crate::py::{PyErr, PyResult, PyVal};

/// `TlvInfoDecoder.read_eeprom`.
#[allow(unused_variables)]
pub fn read_eeprom<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Err(PyErr::not_ported("TlvInfoDecoder.read_eeprom"))
}

/// `TlvInfoDecoder.update_eeprom_db`.
#[allow(unused_variables)]
pub fn update_eeprom_db<S: PyObject + ?Sized>(s: &S, e: PyVal) -> PyResult<PyVal> {
    Err(PyErr::not_ported("TlvInfoDecoder.update_eeprom_db"))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::object::{BaseClass, DynObject};

    #[test]
    fn the_decoder_s_eeprom_methods_say_they_are_not_ported() {
        let d = DynObject {
            class: "TlvInfoDecoder",
            base: BaseClass::TlvInfoDecoder,
            handler: Box::new(|_, _, _| None),
        };
        for (r, what) in [
            (read_eeprom(&d), "TlvInfoDecoder.read_eeprom"),
            (
                update_eeprom_db(&d, PyVal::None),
                "TlvInfoDecoder.update_eeprom_db",
            ),
        ] {
            let e = r.expect_err("not ported");
            assert!(e.str().contains(what), "{}", e.str());
        }
    }
}
