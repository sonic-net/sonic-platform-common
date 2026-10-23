//! `sonic_platform_base.bmc_base`: a BMC reached through its Redfish API.
//!
//! `BMCBase` keeps state -- the address and the Redfish client with its
//! session -- so it is a struct here, [`Bmc`], generic over the vendor's
//! part: the [`BmcVendor`] callbacks Python leaves abstract, and the vendor's
//! own `_login` and `get_version` where it overrides them.  Every method a
//! vendor does not override is the base class's, as in Python.

use std::sync::Arc;

use crate::device_info;
use crate::logger::{self, Logger, ModuleLogger};
use crate::object::{BaseClass, PyObject};
use crate::py::{ops, PyErr, PyResult, PyVal};
use crate::redfish_client::{self as rf, is_exception, Credentials, RedfishClient};

pub const CURL_PATH: &str = "/usr/bin/curl";
pub const BMC_NAME: &str = "BMC";
pub const ROOT_ACCOUNT: &str = "root";

/// The module's `logger = Logger('bmc_base')`.
pub static LOGGER: ModuleLogger = ModuleLogger::new();

/// `import sonic_platform_base.bmc_base`: redfish_client first, as its
/// import statement comes before the logger.
pub fn import() {
    logger::import("sonic_platform_base.bmc_base", || {
        rf::import();
        let _ = LOGGER.set(Arc::new(Logger::new(Some("bmc_base"))));
    });
}

fn log() -> Arc<Logger> {
    import();
    LOGGER
        .get_or_init(|| Arc::new(Logger::new(Some("bmc_base"))))
        .clone()
}

/// What a vendor's BMC class supplies.  The defaults are BMCBase's: the
/// callbacks raise `NotImplementedError`, `_login` is the generic one.
pub trait BmcVendor: Send + Sync + Sized + 'static {
    fn py_class(&self) -> &'static str;
    /// `_get_login_user_callback()`.
    fn get_login_user(&self) -> PyResult<PyVal> {
        Err(PyErr::not_implemented())
    }
    /// `_get_login_password_callback()`.
    fn get_login_password(&self) -> PyResult<PyVal> {
        Err(PyErr::not_implemented())
    }
    /// `_get_default_root_password()`.
    fn get_default_root_password(&self) -> PyResult<PyVal> {
        Err(PyErr::not_implemented())
    }
    /// `get_firmware_id()`: given the BMC, as a vendor may ask the BMC.
    fn get_firmware_id(_bmc: &Bmc<Self>) -> PyResult<PyVal> {
        Err(PyErr::not_implemented())
    }
    /// `_get_eeprom_id()`.
    fn get_eeprom_id(&self) -> PyResult<PyVal> {
        Err(PyErr::not_implemented())
    }
    /// `_login()`.
    fn login(bmc: &Bmc<Self>) -> PyResult<i128> {
        bmc.base_login()
    }
    /// `get_version()`.
    fn get_version(bmc: &Bmc<Self>) -> PyResult<PyVal> {
        bmc.base_get_version()
    }
}

/// A `BMCBase` instance.
pub struct Bmc<V: BmcVendor> {
    addr: PyVal,
    pub rf_client: RedfishClient,
    pub vendor: V,
}

impl<V: BmcVendor> Credentials for Bmc<V> {
    fn user(&self) -> PyResult<PyVal> {
        self.vendor.get_login_user()
    }
    fn password(&self) -> PyResult<PyVal> {
        self.vendor.get_login_password()
    }
}

impl<V: BmcVendor> Bmc<V> {
    /// `BMCBase.__init__(addr)`: the Redfish client is built -- and logs --
    /// with the object.
    pub fn new(addr: PyVal, vendor: V) -> Bmc<V> {
        Bmc::with_curl(addr, vendor, CURL_PATH)
    }

    /// `new`, with its Redfish client running another cURL.
    pub fn with_curl(addr: PyVal, vendor: V, curl_path: &str) -> Bmc<V> {
        import();
        let rf_client = RedfishClient::new(curl_path, &addr.py_str());
        Bmc {
            addr,
            rf_client,
            vendor,
        }
    }

    /// `BMCBase._login()`.
    pub fn base_login(&self) -> PyResult<i128> {
        if self.rf_client.has_login() {
            return Ok(rf::ERR_CODE_OK);
        }
        self.rf_client.login(self, true)
    }

    /// `_login()`, the vendor's if it has one.
    pub fn login(&self) -> PyResult<i128> {
        V::login(self)
    }

    /// `get_firmware_id()`, the vendor's.
    pub fn get_firmware_id(&self) -> PyResult<PyVal> {
        V::get_firmware_id(self)
    }

    /// `_logout()`.
    pub fn logout(&self) -> PyResult<i128> {
        if self.rf_client.has_login() {
            return self.rf_client.logout(self, None);
        }
        Ok(rf::ERR_CODE_OK)
    }

    /// `@with_session_management`: log in, run, log out -- and on an
    /// exception, log it, log out (whatever that raises escapes), and answer
    /// `(ERR_CODE_GENERIC_ERROR, str(e))`.
    fn with_session(
        &self,
        name: &str,
        api: impl FnOnce() -> PyResult<(i128, PyVal)>,
    ) -> PyResult<PyVal> {
        let r = (|| -> PyResult<(i128, PyVal)> {
            self.login()?;
            let (ret, data) = api()?;
            if ret != rf::ERR_CODE_OK {
                log().log_notice(&format!("Failed to execute {name}: {ret}"));
            }
            self.logout()?;
            Ok((ret, data))
        })();
        let (ret, data) = match r {
            Ok(v) => v,
            Err(e) if is_exception(&e) => {
                log().log_error(&format!("Exception in {name}: {}", e.str()));
                self.logout()?;
                log().log_notice(&format!(
                    "Logged out from BMC in exception handler of {name}"
                ));
                (rf::ERR_CODE_GENERIC_ERROR, PyVal::Str(e.str()))
            }
            Err(e) => return Err(e),
        };
        Ok(PyVal::Tuple(vec![PyVal::Int(ret), data]))
    }

    /// `wait_until_redfish_ready(timeout, interval)`.
    pub fn wait_until_redfish_ready(&self, timeout: f64, interval: f64) -> PyResult<i128> {
        self.rf_client
            .wait_until_redfish_ready(self, timeout, interval)
    }

    /// `_change_login_password(password, user=None)`.
    pub fn change_login_password(
        &self,
        password: &str,
        user: Option<&str>,
    ) -> PyResult<(i128, PyVal)> {
        self.rf_client
            .redfish_api_change_login_password(self, password, user)
    }

    /// `_get_firmware_version(fw_id)`.
    pub fn get_firmware_version_of(&self, fw_id: &PyVal) -> PyResult<PyVal> {
        self.with_session("_get_firmware_version", || {
            self.rf_client
                .redfish_api_get_firmware_version(self, &fw_id.py_str())
        })
    }

    /// `_get_eeprom_info(eeprom_id)`.
    pub fn get_eeprom_info(&self, eeprom_id: &PyVal) -> PyResult<PyVal> {
        self.with_session("_get_eeprom_info", || {
            self.rf_client
                .redfish_api_get_eeprom_info(self, &eeprom_id.py_str())
        })
    }

    /// `_is_bmc_eeprom_content_valid(eeprom_info)`.
    fn is_bmc_eeprom_content_valid(&self, eeprom_info: &PyVal) -> PyResult<bool> {
        if eeprom_info.is_none() || ops::len(eeprom_info)? == 0 {
            return Ok(false);
        }
        let got_error = ops::get(eeprom_info, "error", PyVal::None)?;
        if got_error.truthy() {
            log().log_error(&format!(
                "Got error when querying eeprom: {}",
                got_error.py_str()
            ));
            return Ok(false);
        }
        Ok(true)
    }

    /// The `(ret, data)` a decorated call answers.
    fn unpack(t: PyVal) -> PyResult<(PyVal, PyVal)> {
        match t {
            PyVal::Tuple(mut v) if v.len() == 2 => {
                let data = v.pop().unwrap_or_default();
                let ret = v.pop().unwrap_or_default();
                Ok((ret, data))
            }
            _ => Err(PyErr::value_error(
                "not enough values to unpack (expected 2)",
            )),
        }
    }

    fn eeprom(&self) -> PyResult<PyVal> {
        let r = (|| -> PyResult<PyVal> {
            let id = self.vendor.get_eeprom_id()?;
            let (ret, info) = Self::unpack(self.get_eeprom_info(&id)?)?;
            if !self.is_bmc_eeprom_content_valid(&info)? || !ret.py_eq(&PyVal::Int(rf::ERR_CODE_OK))
            {
                log().log_error(&format!("Failed to get BMC EEPROM info: {}", ret.py_str()));
                return Ok(PyVal::Dict(vec![]));
            }
            Ok(info)
        })();
        match r {
            Err(e) if is_exception(&e) => {
                log().log_error(&format!("Failed to get BMC EEPROM info: {}", e.str()));
                Ok(PyVal::Dict(vec![]))
            }
            other => other,
        }
    }

    fn eeprom_field(&self, key: &str) -> PyResult<PyVal> {
        let info = self.eeprom()?;
        if !self.is_bmc_eeprom_content_valid(&info)? {
            return Ok(PyVal::None);
        }
        ops::get(&info, key, PyVal::None)
    }

    /// `BMCBase.get_version()`.
    pub fn base_get_version(&self) -> PyResult<PyVal> {
        let r = (|| -> PyResult<PyVal> {
            let id = self.get_firmware_id()?;
            let (ret, version) = Self::unpack(self.get_firmware_version_of(&id)?)?;
            if !ret.py_eq(&PyVal::Int(rf::ERR_CODE_OK)) {
                log().log_error(&format!(
                    "Failed to get BMC firmware version: {}",
                    ret.py_str()
                ));
                return Ok(PyVal::str("N/A"));
            }
            Ok(version)
        })();
        match r {
            Err(e) if is_exception(&e) => {
                log().log_error(&format!("Failed to get BMC firmware version: {}", e.str()));
                Ok(PyVal::str("N/A"))
            }
            other => other,
        }
    }

    fn presence(&self) -> PyResult<bool> {
        presence()
    }
}

/// `BMCBase.get_presence()`: a switch host with a BMC configured.  Not the
/// instance's: what any BMC object answers.
pub fn presence() -> PyResult<bool> {
    Ok(device_info::is_switch_host()? && device_info::get_bmc_data().is_some_and(|d| d.truthy()))
}

impl<V: BmcVendor> PyObject for Bmc<V> {
    fn py_class(&self) -> &'static str {
        self.vendor.py_class()
    }
    fn base_class(&self) -> BaseClass {
        BaseClass::BMCBase
    }
    fn get_name(&self) -> PyResult<PyVal> {
        Ok(PyVal::str(BMC_NAME))
    }
    fn get_presence(&self) -> PyResult<PyVal> {
        Ok(PyVal::Bool(self.presence()?))
    }
    fn get_model(&self) -> PyResult<PyVal> {
        self.eeprom_field("Model")
    }
    fn get_serial(&self) -> PyResult<PyVal> {
        self.eeprom_field("SerialNumber")
    }
    fn get_revision(&self) -> PyResult<PyVal> {
        Ok(PyVal::str("N/A"))
    }
    /// One ping, a second's wait: a ping that fails is False, one that
    /// cannot run raises.
    fn get_status(&self) -> PyResult<PyVal> {
        if !self.presence()? {
            return Ok(PyVal::Bool(false));
        }
        let addr = match &self.addr {
            PyVal::Str(s) => s.clone(),
            other => {
                return Err(PyErr::type_error(format!(
                    "expected str, bytes or os.PathLike object, not {}",
                    other.type_name()
                )))
            }
        };
        let argv = ["/usr/bin/ping", "-c", "1", "-W", "1", addr.as_str()];
        match crate::subprocess::communicate(&argv) {
            Ok(c) if c.returncode == 0 => Ok(PyVal::Bool(true)),
            Ok(_) => Ok(PyVal::Bool(false)),
            Err(e) => Err(e),
        }
    }
    fn is_replaceable(&self) -> PyResult<PyVal> {
        Ok(PyVal::Bool(false))
    }
    fn get_eeprom(&self) -> PyResult<PyVal> {
        self.eeprom()
    }
    fn get_version(&self) -> PyResult<PyVal> {
        V::get_version(self)
    }
    fn open_session(&self) -> PyResult<PyVal> {
        self.rf_client.open_session(self)
    }
    fn close_session(&self, session_id: &str) -> PyResult<PyVal> {
        self.with_session("close_session", || {
            self.rf_client
                .close_session(self, session_id)
                .map(|(r, m)| (r, PyVal::Str(m)))
        })
    }
    fn trigger_bmc_debug_log_dump(&self) -> PyResult<PyVal> {
        self.with_session("trigger_bmc_debug_log_dump", || {
            self.rf_client
                .redfish_api_trigger_bmc_debug_log_dump(self)
                .map(|(r, (t, m))| (r, PyVal::Tuple(vec![t, m])))
        })
    }
    /// With `timeout=120`, the base class's default: the trait, like the
    /// facade it serves, never passes one.
    fn get_bmc_debug_log_dump(&self, task_id: &str, filename: &str, path: &str) -> PyResult<PyVal> {
        self.with_session("get_bmc_debug_log_dump", || {
            self.rf_client
                .redfish_api_get_bmc_debug_log_dump(self, task_id, filename, path, 120.0)
                .map(|(r, m)| (r, PyVal::Str(m)))
        })
    }
    fn update_firmware(&self, fw_image: &str) -> PyResult<PyVal> {
        self.with_session("update_firmware", || {
            log().log_notice(&format!("Installing BMC firmware image {fw_image}"));
            let id = self.get_firmware_id()?;
            let (ret, msg, updated) =
                self.rf_client
                    .redfish_api_update_firmware(self, fw_image, &[id], true, 1800.0)?;
            log().log_notice(&format!("Firmware update result: {ret}"));
            if !msg.is_empty() {
                log().log_notice(&msg);
            }
            Ok((
                ret,
                PyVal::Tuple(vec![PyVal::Str(msg), PyVal::List(updated)]),
            ))
        })
    }
    fn request_bmc_reset(&self, graceful: bool) -> PyResult<PyVal> {
        let kind = if graceful {
            rf::REDFISH_BMC_GRACEFUL_RESTART
        } else {
            rf::REDFISH_BMC_FORCE_RESTART
        };
        self.with_session("request_bmc_reset", || {
            self.rf_client.redfish_api_request_bmc_reset(self, kind)
        })
    }
    fn reset_root_password(&self) -> PyResult<PyVal> {
        self.with_session("reset_root_password", || {
            let (ret, saved_min_length) =
                self.rf_client.redfish_api_get_min_password_length(self)?;
            if ret != rf::ERR_CODE_OK {
                let msg = format!(
                    "Failed to get current min password length: {}",
                    saved_min_length.py_str()
                );
                log().log_error(&msg);
                return Ok((ret, PyVal::Str(msg)));
            }
            let default_root_password = self.vendor.get_default_root_password()?;
            if !default_root_password.truthy() {
                log().log_error("BMC root account default password not found");
                return Ok((
                    rf::ERR_CODE_GENERIC_ERROR,
                    PyVal::str("BMC root account default password not found"),
                ));
            }
            let new_min_length = PyVal::Int(ops::len(&default_root_password)? as i128);
            let (ret, err_msg) = self
                .rf_client
                .redfish_api_set_min_password_length(self, &new_min_length)?;
            if ret != rf::ERR_CODE_OK {
                let msg = format!(
                    "Failed to set min password length to {}: {}",
                    new_min_length.py_str(),
                    err_msg.py_str()
                );
                log().log_error(&msg);
                return Ok((ret, PyVal::Str(msg)));
            }
            log().log_notice(&format!(
                "Set min password length to {}",
                new_min_length.py_str()
            ));
            let (ret, err_msg) =
                self.change_login_password(&default_root_password.py_str(), Some(ROOT_ACCOUNT))?;
            if ret != rf::ERR_CODE_OK {
                let msg = format!("Failed to change root password: {}", err_msg.py_str());
                log().log_error(&msg);
                self.rf_client
                    .redfish_api_set_min_password_length(self, &saved_min_length)?;
                return Ok((ret, PyVal::Str(msg)));
            }
            log().log_notice(&format!(
                "Changed BMC root password to default: {}",
                default_root_password.py_str()
            ));
            let (ret, err_msg) = self
                .rf_client
                .redfish_api_set_min_password_length(self, &saved_min_length)?;
            if ret != rf::ERR_CODE_OK {
                let msg = format!(
                    "Failed to restore min password length to {}: {}",
                    saved_min_length.py_str(),
                    err_msg.py_str()
                );
                log().log_error(&msg);
                return Ok((ret, PyVal::Str(msg)));
            }
            log().log_notice(&format!(
                "Restored min password length to {}",
                saved_min_length.py_str()
            ));
            Ok((rf::ERR_CODE_OK, PyVal::str("")))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::testing::{Answer, FakeCurl, Root};
    use std::io::Write;
    use std::path::{Path, PathBuf};

    /// A vendor whose password is a file's, so a script can change it between
    /// steps.
    struct TestVendor {
        pw: PathBuf,
    }

    impl BmcVendor for TestVendor {
        fn py_class(&self) -> &'static str {
            "TestBMC"
        }
        fn get_login_user(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("nosuser"))
        }
        fn get_login_password(&self) -> PyResult<PyVal> {
            if !self.pw.exists() {
                return Err(PyErr::other("Exception", "no password file"));
            }
            Ok(PyVal::str(crate::py::strip(
                &std::fs::read_to_string(&self.pw).unwrap_or_default(),
            )))
        }
        fn get_default_root_password(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("R00tDefault!"))
        }
        fn get_firmware_id(_bmc: &Bmc<Self>) -> PyResult<PyVal> {
            Ok(PyVal::str("MGX_FW_BMC_0"))
        }
        fn get_eeprom_id(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("BMC_eeprom"))
        }
    }

    fn arg(a: &PyVal, i: usize) -> PyVal {
        ops::getitem(a, &PyVal::Int(i as i128)).unwrap_or_default()
    }

    fn arg_s(a: &PyVal, i: usize) -> String {
        arg(a, i).py_str()
    }

    fn arg_f(a: &PyVal, i: usize) -> f64 {
        match arg(a, i) {
            PyVal::Int(n) => n as f64,
            PyVal::Float(f) => f,
            _ => 0.0,
        }
    }

    fn pair_list(v: Vec<(PyVal, PyVal)>) -> PyVal {
        PyVal::List(
            v.into_iter()
                .map(|(a, b)| PyVal::Tuple(vec![a, b]))
                .collect(),
        )
    }

    fn t2(r: i128, v: PyVal) -> PyVal {
        PyVal::Tuple(vec![PyVal::Int(r), v])
    }

    fn call(b: &Bmc<TestVendor>, name: &str, a: &PyVal) -> PyResult<PyVal> {
        Ok(match name {
            "get_name" => b.get_name()?,
            "get_presence" => b.get_presence()?,
            "get_model" => b.get_model()?,
            "get_serial" => b.get_serial()?,
            "get_revision" => b.get_revision()?,
            "get_status" => b.get_status()?,
            "is_replaceable" => b.is_replaceable()?,
            "get_eeprom" => b.get_eeprom()?,
            "get_version" => b.get_version()?,
            "open_session" => b.open_session()?,
            "close_session" => b.close_session(&arg_s(a, 0))?,
            "reset_root_password" => b.reset_root_password()?,
            "request_bmc_reset" => b.request_bmc_reset(arg(a, 0).truthy())?,
            "update_firmware" => b.update_firmware(&arg_s(a, 0))?,
            "trigger_bmc_debug_log_dump" => b.trigger_bmc_debug_log_dump()?,
            "get_bmc_debug_log_dump" => {
                b.get_bmc_debug_log_dump(&arg_s(a, 0), &arg_s(a, 1), &arg_s(a, 2))?
            }
            "_login" => PyVal::Int(b.login()?),
            "_logout" => PyVal::Int(b.logout()?),
            "wait_until_redfish_ready" => {
                PyVal::Int(b.wait_until_redfish_ready(arg_f(a, 0), arg_f(a, 1))?)
            }
            "_get_firmware_version" => b.get_firmware_version_of(&arg(a, 0))?,
            "_get_eeprom_info" => b.get_eeprom_info(&arg(a, 0))?,
            "_change_login_password" => {
                let u = arg(a, 1);
                let (r, m) = b.change_login_password(
                    &arg_s(a, 0),
                    if u.is_none() { None } else { Some(u.py_str()) }.as_deref(),
                )?;
                t2(r, m)
            }
            _ => PyVal::str("bad call"),
        })
    }

    fn rf_call(b: &Bmc<TestVendor>, name: &str, a: &PyVal) -> PyResult<PyVal> {
        let c = &b.rf_client;
        Ok(match name {
            "has_login" => PyVal::Bool(c.has_login()),
            "login" => PyVal::Int(c.login(b, true)?),
            "logout" => PyVal::Int(c.logout(b, None)?),
            "invalidate_session" => {
                c.invalidate_session();
                PyVal::None
            }
            "redfish_api_get_firmware_list" => {
                let (r, l) = c.redfish_api_get_firmware_list(b)?;
                t2(r, pair_list(l))
            }
            "redfish_api_get_eeprom_list" => {
                let (r, l) = c.redfish_api_get_eeprom_list(b)?;
                t2(
                    r,
                    pair_list(l.into_iter().map(|(k, v)| (PyVal::Str(k), v)).collect()),
                )
            }
            "redfish_api_get_firmware_version" => {
                let (r, v) = c.redfish_api_get_firmware_version(b, &arg_s(a, 0))?;
                t2(r, v)
            }
            "redfish_api_get_eeprom_info" => {
                let (r, v) = c.redfish_api_get_eeprom_info(b, &arg_s(a, 0))?;
                t2(r, v)
            }
            "redfish_api_get_min_password_length" => {
                let (r, v) = c.redfish_api_get_min_password_length(b)?;
                t2(r, v)
            }
            "redfish_api_set_min_password_length" => {
                let (r, v) = c.redfish_api_set_min_password_length(b, &arg(a, 0))?;
                t2(r, v)
            }
            _ => PyVal::str("bad call"),
        })
    }

    /// Unit-test vendors: `Plain` leaves BMCBase's abstract callbacks
    /// alone, `Named` names its firmware, `Own` also has its own version.
    struct Plain;
    struct Named;
    struct Own;

    impl BmcVendor for Plain {
        fn py_class(&self) -> &'static str {
            "Plain"
        }
        fn get_login_user(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("nosuser"))
        }
        fn get_login_password(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("pw"))
        }
    }

    impl BmcVendor for Named {
        fn py_class(&self) -> &'static str {
            "Named"
        }
        fn get_login_user(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("nosuser"))
        }
        fn get_login_password(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("pw"))
        }
        fn get_firmware_id(_bmc: &Bmc<Self>) -> PyResult<PyVal> {
            Ok(PyVal::str("FW_UNIT"))
        }
    }

    impl BmcVendor for Own {
        fn py_class(&self) -> &'static str {
            "Own"
        }
        fn get_version(_bmc: &Bmc<Self>) -> PyResult<PyVal> {
            Ok(PyVal::str("own"))
        }
    }

    const FW_UNIT: &str = "/redfish/v1/UpdateService/FirmwareInventory/FW_UNIT";

    #[test]
    fn get_version_is_the_vendors_or_the_base_classes() {
        let curl = crate::testing::FakeCurl::new();
        let addr = || PyVal::str("169.254.0.1");
        // No firmware ID: NotImplementedError, logged, and 'N/A'.
        let plain = Bmc::with_curl(addr(), Plain, &curl.path());
        assert_eq!(
            plain.get_firmware_id().map_err(|e| e.exc.name()),
            Err("NotImplementedError")
        );
        assert_eq!(plain.get_version().unwrap().py_repr(), "'N/A'");
        assert!(curl.take_requests().is_empty());
        // The base class's: the vendor's ID, in a session of its own.
        let named = Bmc::with_curl(addr(), Named, &curl.path());
        curl.reply("GET", FW_UNIT, 200, r#"{"Version": "7.1"}"#);
        assert_eq!(named.get_version().unwrap().py_repr(), "'7.1'");
        assert_eq!(
            curl.take_requests(),
            [
                "POST /redfish/v1/SessionService/Sessions",
                &format!("GET {FW_UNIT}"),
                "DELETE /redfish/v1/SessionService/Sessions/s1"
            ]
        );
        assert!(!named.rf_client.has_login());
        // A member the BMC does not have is an error code, so 'N/A'.
        curl.forget("GET", FW_UNIT);
        assert_eq!(named.get_version().unwrap().py_repr(), "'N/A'");
        // A vendor's own.
        let own = Bmc::with_curl(addr(), Own, &curl.path());
        assert_eq!(own.get_version().unwrap().py_repr(), "'own'");
        // BMCBase's callbacks raise until a vendor gives them.
        assert_eq!(
            own.vendor.get_login_user().map_err(|e| e.exc.name()),
            Err("NotImplementedError")
        );
        assert_eq!(
            own.vendor.get_login_password().map_err(|e| e.exc.name()),
            Err("NotImplementedError")
        );
    }

    #[test]
    fn a_bmc_is_named_bmc_and_its_class_is_the_vendors() {
        let b = Bmc::new(PyVal::str("169.254.0.1"), Plain);
        assert_eq!(b.get_name().unwrap().py_repr(), "'BMC'");
        assert_eq!(b.py_class(), "Plain");
    }

    #[test]
    fn a_firmware_update_targets_the_vendors_firmware_id() {
        let curl = crate::testing::FakeCurl::new();
        let named = Bmc::with_curl(PyVal::str("169.254.0.1"), Named, &curl.path());
        let r = named.update_firmware("/nonexistent/bmc.fwpkg").unwrap();
        assert!(r.py_repr().starts_with("(-"), "{}", r.py_repr());
        assert_eq!(
            curl.take_requests(),
            [
                "POST /redfish/v1/SessionService/Sessions",
                "POST /redfish/v1/UpdateService/update-multipart",
                "DELETE /redfish/v1/SessionService/Sessions/s1"
            ]
        );
    }

    const LOGIN: &str = "POST /redfish/v1/SessionService/Sessions";
    const LOGOUT: &str = "DELETE /redfish/v1/SessionService/Sessions/s1";
    const EEPROM: &str = "/redfish/v1/Chassis/BMC_eeprom";
    const ACCOUNT_SERVICE: &str = "/redfish/v1/AccountService";
    const ROOT_ACCOUNT: &str = "/redfish/v1/AccountService/Accounts/root";

    /// A vendor with every callback: root's default password is `root_pw`.
    struct Unit {
        root_pw: &'static str,
    }

    impl BmcVendor for Unit {
        fn py_class(&self) -> &'static str {
            "Unit"
        }
        fn get_login_user(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("nosuser"))
        }
        fn get_login_password(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("pw"))
        }
        fn get_default_root_password(&self) -> PyResult<PyVal> {
            Ok(PyVal::str(self.root_pw))
        }
        fn get_firmware_id(_bmc: &Bmc<Self>) -> PyResult<PyVal> {
            Ok(PyVal::str("MGX_FW_BMC_0"))
        }
        fn get_eeprom_id(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("BMC_eeprom"))
        }
    }

    fn unit(curl: &FakeCurl, root_pw: &'static str) -> Bmc<Unit> {
        Bmc::with_curl(PyVal::str("169.254.0.1"), Unit { root_pw }, &curl.path())
    }

    fn get(path: &str) -> String {
        format!("GET {path}")
    }

    fn patch(path: &str) -> String {
        format!("PATCH {path}")
    }

    #[test]
    fn eeprom_fields_come_from_a_good_eeprom_only() {
        let curl = FakeCurl::new();
        let b = unit(&curl, "R00t!");
        curl.reply("GET", EEPROM, 200, r#"{"Model": "P4501-0001", "SerialNumber": "MT2401X00042", "Status": {"State": "Enabled"}}"#);
        assert_eq!(b.get_model().unwrap().py_repr(), "'P4501-0001'");
        assert_eq!(b.get_serial().unwrap().py_repr(), "'MT2401X00042'");
        assert_eq!(
            b.get_eeprom().unwrap().py_repr(),
            "{'Model': 'P4501-0001', 'SerialNumber': 'MT2401X00042', 'State': 'Enabled', 'Health': 'Ok', 'HealthRollup': 'Ok'}"
        );
        assert_eq!(
            curl.take_requests(),
            [
                LOGIN,
                &get(EEPROM),
                LOGOUT,
                LOGIN,
                &get(EEPROM),
                LOGOUT,
                LOGIN,
                &get(EEPROM),
                LOGOUT
            ]
        );
        // An error answer: no fields.
        curl.forget("GET", EEPROM);
        assert_eq!(b.get_eeprom().unwrap().py_repr(), "{}");
        assert_eq!(b.get_model().unwrap().py_repr(), "None");
        // A body that is no dict: the decorator catches the AttributeError
        // and answers its text, which is no eeprom either.
        curl.reply("GET", EEPROM, 200, "[1]");
        assert_eq!(
            b.get_eeprom_info(&PyVal::str("BMC_eeprom"))
                .unwrap()
                .py_repr(),
            "(-12, \"'list' object has no attribute 'items'\")"
        );
        assert!(!b.rf_client.has_login());
        assert_eq!(b.get_eeprom().unwrap().py_repr(), "{}");
        // No eeprom ID: NotImplementedError, logged.
        let plain = Bmc::with_curl(PyVal::str("169.254.0.1"), Plain, &curl.path());
        assert_eq!(plain.get_eeprom().unwrap().py_repr(), "{}");
        assert_eq!(plain.get_serial().unwrap().py_repr(), "None");
    }

    #[test]
    fn a_bmc_is_present_on_a_switch_host_with_bmc_data() {
        let curl = FakeCurl::new();
        let root = Root::new();
        let b = unit(&curl, "R00t!");
        assert_eq!(b.get_presence().unwrap().py_repr(), "False");
        assert_eq!(b.get_status().unwrap().py_repr(), "False");
        root.write(
            "/usr/share/sonic/platform/platform_env.conf",
            "switch_host=1\n",
        );
        root.write("/etc/sonic/bmc.json", r#"{"bmc_addr": "169.254.0.1"}"#);
        assert_eq!(b.get_presence().unwrap().py_repr(), "True");
        let odd = Bmc::with_curl(PyVal::Int(5), Unit { root_pw: "" }, &curl.path());
        assert_eq!(
            odd.get_status().map_err(|e| e.str()).err().as_deref(),
            Some("expected str, bytes or os.PathLike object, not int")
        );
        // One ping, where there is a ping to run.
        let local = Bmc::with_curl(PyVal::str("127.0.0.1"), Unit { root_pw: "" }, &curl.path());
        match local.get_status() {
            Ok(PyVal::Bool(_)) => {}
            Err(e) => assert_eq!(e.exc.name(), "FileNotFoundError"),
            Ok(other) => panic!("{}", other.py_repr()),
        }
        assert_eq!(b.get_revision().unwrap().py_repr(), "'N/A'");
        assert_eq!(b.is_replaceable().unwrap().py_repr(), "False");
    }

    #[test]
    fn resetting_root_s_password_puts_the_minimum_length_back() {
        let curl = FakeCurl::new();
        curl.reply("GET", ACCOUNT_SERVICE, 200, r#"{"MinPasswordLength": 8}"#);
        curl.reply("PATCH", ACCOUNT_SERVICE, 204, "");
        curl.reply("PATCH", ROOT_ACCOUNT, 204, "");
        let b = unit(&curl, "R00tDefault!");
        let reset = || b.reset_root_password().unwrap().py_repr();
        assert_eq!(reset(), "(0, '')");
        assert_eq!(
            curl.take_requests(),
            [
                LOGIN,
                &get(ACCOUNT_SERVICE),
                &patch(ACCOUNT_SERVICE),
                &patch(ROOT_ACCOUNT),
                &patch(ACCOUNT_SERVICE),
                LOGOUT
            ]
        );
        let cmds = curl.take_commands();
        assert!(
            cmds[2].contains(r#"{"MinPasswordLength": 12}"#),
            "{}",
            cmds[2]
        );
        assert!(
            cmds[3].contains(r#"{"Password" : "R00tDefault!"}"#),
            "{}",
            cmds[3]
        );
        assert!(
            cmds[4].contains(r#"{"MinPasswordLength": 8}"#),
            "{}",
            cmds[4]
        );
        let refused = r#"{"error": {"message": "nope"}}"#;
        curl.answers(
            "PATCH",
            ACCOUNT_SERVICE,
            &[Answer::Reply(204, ""), Answer::Reply(400, refused)],
        );
        assert_eq!(
            reset(),
            "(-12, 'Failed to restore min password length to 8: nope')"
        );
        curl.reply("PATCH", ACCOUNT_SERVICE, 204, "");
        curl.reply(
            "PATCH",
            ROOT_ACCOUNT,
            400,
            r#"{"error": {"message": "weak"}}"#,
        );
        curl.take_requests();
        assert_eq!(reset(), "(-12, 'Failed to change root password: weak')");
        assert_eq!(
            curl.take_requests()
                .iter()
                .filter(|r| **r == patch(ACCOUNT_SERVICE))
                .count(),
            2
        );
        curl.reply("PATCH", ACCOUNT_SERVICE, 400, refused);
        assert_eq!(
            reset(),
            "(-12, 'Failed to set min password length to 12: nope')"
        );
        assert_eq!(
            unit(&curl, "").reset_root_password().unwrap().py_repr(),
            "(-12, 'BMC root account default password not found')"
        );
        curl.fail("GET", ACCOUNT_SERVICE, 7, "no route");
        assert_eq!(
            reset(),
            "(-10, 'Failed to get current min password length: Error: no route')"
        );
        // No default password: NotImplementedError, which the decorator
        // answers as its (empty) text.
        curl.reply("GET", ACCOUNT_SERVICE, 200, r#"{"MinPasswordLength": 8}"#);
        let plain = Bmc::with_curl(PyVal::str("169.254.0.1"), Plain, &curl.path());
        assert_eq!(plain.reset_root_password().unwrap().py_repr(), "(-12, '')");
    }

    #[test]
    fn the_harness_drives_every_bmc_and_redfish_call() {
        let curl = FakeCurl::new();
        let _root = Root::new();
        let fw = "/redfish/v1/UpdateService/FirmwareInventory";
        curl.reply(
            "GET",
            &format!("{fw}/MGX_FW_BMC_0"),
            200,
            r#"{"Version": "88.0002.1200"}"#,
        );
        curl.reply("GET", fw, 200, r#"{"Members": [{"@odata.id": "/redfish/v1/UpdateService/FirmwareInventory/MGX_FW_BMC_0"}]}"#);
        curl.reply(
            "GET",
            "/redfish/v1/Chassis",
            200,
            r#"{"Members": [{"@odata.id": "/redfish/v1/Chassis/BMC_eeprom"}]}"#,
        );
        curl.reply(
            "GET",
            EEPROM,
            200,
            r#"{"Model": "P4501-0001", "SerialNumber": "MT2401X00042"}"#,
        );
        curl.reply("GET", ACCOUNT_SERVICE, 200, r#"{"MinPasswordLength": 12}"#);
        curl.reply("PATCH", ACCOUNT_SERVICE, 204, "");
        curl.reply("PATCH", ROOT_ACCOUNT, 204, "");
        curl.reply(
            "PATCH",
            "/redfish/v1/AccountService/Accounts/nosuser",
            204,
            "",
        );
        curl.reply(
            "POST",
            "/redfish/v1/Managers/BMC_0/Actions/Manager.Reset",
            204,
            "",
        );
        curl.reply(
            "POST",
            "/redfish/v1/Managers/BMC_0/LogServices/Dump/Actions/LogService.CollectDiagnosticData",
            202,
            r#"{"TaskStatus": "OK", "Id": "7"}"#,
        );
        curl.reply(
            "GET",
            "/redfish/v1/TaskService/Tasks/7",
            200,
            r#"{"PercentComplete": 100, "TaskStatus": "OK", "Messages": [], "Payload": {"HttpHeaders": ["Location: /redfish/v1/Managers/BMC_0/LogServices/Dump/Entries/3"]}}"#,
        );
        curl.reply(
            "GET",
            "/redfish/v1/Managers/BMC_0/LogServices/Dump/Entries/3/attachment",
            200,
            "DUMP",
        );
        curl.reply(
            "POST",
            "/redfish/v1/UpdateService/update-multipart",
            202,
            r#"{"TaskStatus": "OK", "Id": "9"}"#,
        );
        curl.reply(
            "GET",
            "/redfish/v1/TaskService/Tasks/9",
            200,
            r#"{"PercentComplete": 100, "TaskStatus": "OK", "Messages": [{"MessageId": "ResourceEvent.1.0.UpdateSuccessful", "MessageArgs": ["MGX_FW_BMC_0", "x"]}]}"#,
        );
        curl.reply(
            "GET",
            "/redfish/v1/SessionService/Sessions",
            200,
            r#"{"Members": [{"@odata.id": "/redfish/v1/SessionService/Sessions/s1"}]}"#,
        );
        let dir = curl.dir().to_path_buf();
        let script = format!(
            r#"[["new", "169.254.0.1"], ["password", null], ["call", "_login", []], ["password", "pw1"], ["state", {{"users": {{}}}}],
            ["call", "get_name", []], ["call", "get_presence", []], ["call", "get_model", []], ["call", "get_serial", []],
            ["call", "get_revision", []], ["call", "get_status", []], ["call", "is_replaceable", []], ["call", "get_eeprom", []],
            ["call", "get_version", []], ["call", "_get_firmware_version", ["MGX_FW_BMC_0"]], ["call", "_get_eeprom_info", ["BMC_eeprom"]],
            ["call", "_change_login_password", ["N3w!", null]], ["call", "_login", []], ["call", "_change_login_password", ["N3w!", "root"]],
            ["call", "_logout", []], ["call", "open_session", []], ["call", "close_session", ["s1"]], ["call", "reset_root_password", []],
            ["call", "request_bmc_reset", [true]], ["call", "request_bmc_reset", [false]], ["call", "update_firmware", ["/tmp/fw/bmc.fwpkg"]],
            ["call", "trigger_bmc_debug_log_dump", []], ["call", "get_bmc_debug_log_dump", ["7", "dump.tar", "{dir}"]],
            ["call", "wait_until_redfish_ready", [1, 0.1]], ["call", "nope", []],
            ["rf", "has_login", []], ["rf", "login", []], ["rf", "has_login", []], ["rf", "redfish_api_get_firmware_list", []],
            ["rf", "redfish_api_get_eeprom_list", []], ["rf", "redfish_api_get_firmware_version", ["MGX_FW_BMC_0"]],
            ["rf", "redfish_api_get_eeprom_info", ["BMC_eeprom"]], ["rf", "redfish_api_get_min_password_length", []],
            ["rf", "redfish_api_set_min_password_length", [12]], ["rf", "invalidate_session", []], ["rf", "logout", []], ["rf", "nope", []],
            ["nope"], ["password", null], ["call", "get_version", []], ["call", "get_name", [], "extra"]]"#,
            dir = dir.display()
        );
        let eeprom = "{'Model': 'P4501-0001', 'SerialNumber': 'MT2401X00042', 'State': 'Ok', 'Health': 'Ok', 'HealthRollup': 'Ok'}";
        let mut out = Vec::new();
        let new = |addr| {
            Bmc::with_curl(
                addr,
                TestVendor {
                    pw: dir.join("password"),
                },
                &curl.path(),
            )
        };
        run_steps(&crate::json::loads(&script).unwrap(), &dir, &new, &mut out);
        let results: Vec<String> = String::from_utf8(out)
            .unwrap()
            .lines()
            .map(|l| {
                l.split_once(" => ")
                    .map_or(String::new(), |(_, r)| r.to_string())
            })
            .collect();
        let want = [
            "'ok'",
            "'ok'",
            "-8",
            "'ok'",
            "'ok'",
            "'BMC'",
            "False",
            "'P4501-0001'",
            "'MT2401X00042'",
            "'N/A'",
            "False",
            "False",
            eeprom,
            "'88.0002.1200'",
            "(0, '88.0002.1200')",
            &format!("(0, {eeprom})"),
            "(-5, 'Error: Not login')",
            "0",
            "(0, '')",
            "0",
            "(0, ('Login successful', ('s1', 'tok1')))",
            "(0, 'Session closed successfully')",
            "(0, '')",
            "(0, '')",
            "(0, '')",
            "(0, ('', ['MGX_FW_BMC_0']))",
            "(0, ('7', None))",
            "(0, '')",
            "0",
            "'bad call'",
            "False",
            "0",
            "True",
            "(0, [('MGX_FW_BMC_0', '88.0002.1200')])",
            &format!("(0, [('BMC_eeprom', {eeprom})])"),
            "(0, '88.0002.1200')",
            &format!("(0, {eeprom})"),
            "(0, 12)",
            "(0, '')",
            "None",
            "0",
            "'bad call'",
            "'bad op'",
            "'ok'",
            "'N/A'",
            "'BMC'",
        ];
        assert_eq!(results, want);
        assert_eq!(
            std::fs::read_to_string(dir.join("dump.tar")).unwrap(),
            "DUMP"
        );
        assert!(!dir.join("password").exists());
    }

    /// Runs `steps` -- a script of `new`, `state`, `password`, `call` and `rf`
    /// steps -- against the BMCs `new` makes, with the fake service's state
    /// and the password file in `dir`: a line per step.
    fn run_steps(
        steps: &PyVal,
        dir: &Path,
        new: &dyn Fn(PyVal) -> Bmc<TestVendor>,
        out: &mut dyn Write,
    ) {
        let mut b: Option<Bmc<TestVendor>> = None;
        for (i, st) in ops::iterate(steps).unwrap().iter().enumerate() {
            let op = arg_s(st, 0);
            let r: PyResult<PyVal> = match op.as_str() {
                "new" => {
                    b = Some(new(arg(st, 1)));
                    Ok(PyVal::str("ok"))
                }
                "state" => {
                    let _ = std::fs::write(
                        dir.join("state.json"),
                        crate::redfish_client::tests_json_dumps(&arg(st, 1)),
                    );
                    Ok(PyVal::str("ok"))
                }
                "password" => {
                    match arg(st, 1) {
                        PyVal::None => {
                            let _ = std::fs::remove_file(dir.join("password"));
                        }
                        p => {
                            let _ = std::fs::write(dir.join("password"), p.py_str());
                        }
                    }
                    Ok(PyVal::str("ok"))
                }
                "call" => call(b.as_ref().unwrap(), &arg_s(st, 1), &arg(st, 2)),
                "rf" => rf_call(b.as_ref().unwrap(), &arg_s(st, 1), &arg(st, 2)),
                _ => Ok(PyVal::str("bad op")),
            };
            let line = match r {
                Ok(v) => v.py_repr(),
                Err(e) => format!("raise {}: {}", e.exc.name(), e.str()),
            };
            let _ = writeln!(
                out,
                "STEP {i} {} => {line}",
                crate::redfish_client::tests_json_dumps(st)
            );
        }
    }
}
