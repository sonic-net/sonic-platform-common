//! `BMCBase`'s method bodies.
//!
//! Two answer without an instance -- the name is a constant and presence is
//! the switch's configuration -- and are ported.  The rest talk to the BMC
//! over a Redfish session the instance holds; [`crate::bmc::Bmc`] is the BMC
//! object that has one, and these fail as not ported for any other.

use crate::object::PyObject;
use crate::py::{PyErr, PyResult, PyVal};

/// `BMCBase.close_session`.
#[allow(unused_variables)]
pub fn close_session<S: PyObject + ?Sized>(s: &S, session_id: &str) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.close_session"))
}

/// `BMCBase.get_bmc_debug_log_dump`.
#[allow(unused_variables)]
pub fn get_bmc_debug_log_dump<S: PyObject + ?Sized>(
    s: &S,
    task_id: &str,
    filename: &str,
    path: &str,
) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.get_bmc_debug_log_dump"))
}

/// `BMCBase.get_eeprom`.
#[allow(unused_variables)]
pub fn get_eeprom<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.get_eeprom"))
}

/// `BMCBase.get_model`.
#[allow(unused_variables)]
pub fn get_model<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.get_model"))
}

/// `BMCBase.get_name`: `BMCBase.BMC_NAME`.
#[allow(unused_variables)]
pub fn get_name<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Ok(PyVal::str(crate::bmc::BMC_NAME))
}

/// `BMCBase.get_presence`.
#[allow(unused_variables)]
pub fn get_presence<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Ok(PyVal::Bool(crate::bmc::presence()?))
}

/// `BMCBase.get_serial`.
#[allow(unused_variables)]
pub fn get_serial<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.get_serial"))
}

/// `BMCBase.get_status`.
#[allow(unused_variables)]
pub fn get_status<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.get_status"))
}

/// `BMCBase.get_version`.
#[allow(unused_variables)]
pub fn get_version<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.get_version"))
}

/// `BMCBase.open_session`.
#[allow(unused_variables)]
pub fn open_session<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.open_session"))
}

/// `BMCBase.request_bmc_reset`.
#[allow(unused_variables)]
pub fn request_bmc_reset<S: PyObject + ?Sized>(s: &S, graceful: bool) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.request_bmc_reset"))
}

/// `BMCBase.reset_root_password`.
#[allow(unused_variables)]
pub fn reset_root_password<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.reset_root_password"))
}

/// `BMCBase.trigger_bmc_debug_log_dump`.
#[allow(unused_variables)]
pub fn trigger_bmc_debug_log_dump<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.trigger_bmc_debug_log_dump"))
}

/// `BMCBase.update_firmware`.
#[allow(unused_variables)]
pub fn update_firmware<S: PyObject + ?Sized>(s: &S, image_path: &str) -> PyResult<PyVal> {
    Err(PyErr::not_ported("BMCBase.update_firmware"))
}

#[cfg(test)]
mod tests {
    use crate::bmc::{Bmc, BmcVendor};
    use crate::py::PyVal;

    struct Vendor;

    impl BmcVendor for Vendor {
        fn py_class(&self) -> &'static str {
            "Vendor"
        }
    }

    /// The two that need no instance answer as the base class does.
    #[test]
    fn the_name_and_presence_need_no_session() {
        let root = crate::testing::Root::new();
        let b = Bmc::with_curl(PyVal::str("169.254.0.1"), Vendor, "/nonexistent/curl");
        assert_eq!(super::get_name(&b).unwrap().py_repr(), "'BMC'");
        assert_eq!(
            super::get_presence(&b).unwrap().py_repr(),
            "False",
            "not a switch host"
        );
        // A platform_env.conf that will not read raises, as in Python.
        let env = "/usr/share/sonic/platform/platform_env.conf";
        root.write(env, "");
        std::fs::write(root.real(env), b"switch_host=1\xff\n").unwrap();
        assert_eq!(
            super::get_presence(&b).unwrap_err().exc.name(),
            "UnicodeDecodeError"
        );
    }

    /// What a BMC object that is not `bmc::Bmc` would run for the rest: not
    /// ported, as they need the Redfish session `Bmc` holds.
    #[test]
    fn every_session_body_is_not_ported() {
        let b = Bmc::with_curl(PyVal::str("169.254.0.1"), Vendor, "/nonexistent/curl");
        assert_eq!(b.vendor.py_class(), "Vendor");
        let results = [
            ("close_session", super::close_session(&b, "s1")),
            (
                "get_bmc_debug_log_dump",
                super::get_bmc_debug_log_dump(&b, "7", "dump.tar", "/tmp"),
            ),
            ("get_eeprom", super::get_eeprom(&b)),
            ("get_model", super::get_model(&b)),
            ("get_serial", super::get_serial(&b)),
            ("get_status", super::get_status(&b)),
            ("get_version", super::get_version(&b)),
            ("open_session", super::open_session(&b)),
            ("request_bmc_reset", super::request_bmc_reset(&b, true)),
            ("reset_root_password", super::reset_root_password(&b)),
            (
                "trigger_bmc_debug_log_dump",
                super::trigger_bmc_debug_log_dump(&b),
            ),
            (
                "update_firmware",
                super::update_firmware(&b, "/tmp/bmc.fwpkg"),
            ),
        ];
        for (name, r) in results {
            let e = r.err().unwrap();
            assert_eq!(
                (e.exc.name(), e.str()),
                (
                    "RuntimeError",
                    format!("not ported to the native platform API: BMCBase.{name}")
                )
            );
        }
    }
}
