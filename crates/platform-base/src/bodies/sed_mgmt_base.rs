//! `SedMgmtBase`'s method bodies: the password changes, run by the common
//! scripts with the TPM bank addresses from the SED config file.

use std::sync::Arc;

use crate::io;
use crate::logger::{self, Logger, ModuleLogger};
use crate::object::PyObject;
use crate::py::{PyErr, PyResult, PyVal};
use crate::subprocess;

const SED_CONFIG_PATH: &str = "/etc/sonic/sed_config.conf";
const SED_PW_CHANGE_SCRIPT: &str = "/usr/local/bin/sed_pw_change.sh";
const SED_PW_RESET_SCRIPT: &str = "/usr/local/bin/sed_pw_reset.sh";

/// The module's `logger = Logger('sed_mgmt_base')`.
pub static LOGGER: ModuleLogger = ModuleLogger::new();

/// `import sonic_platform_base.sed_mgmt_base`: what a vendor module that
/// imports it runs where its import statement stands.
pub fn import() {
    logger::import("sonic_platform_base.sed_mgmt_base", || {
        let _ = LOGGER.set(Arc::new(Logger::new(Some("sed_mgmt_base"))));
    });
}

fn logger() -> Arc<Logger> {
    import();
    LOGGER
        .get_or_init(|| Arc::new(Logger::new(Some("sed_mgmt_base"))))
        .clone()
}

/// `_read_sed_config_value(key)`: the value of the first `key=` line, or
/// None -- for a missing file, an empty value, or anything that raises.
fn read_sed_config_value(key: &str) -> PyVal {
    let Ok(text) = io::read_text(SED_CONFIG_PATH) else {
        return PyVal::None;
    };
    let prefix = format!("{key}=");
    for line in text.replace("\r\n", "\n").replace('\r', "\n").split('\n') {
        let line = crate::py::strip(line);
        if let Some((_, v)) = line.split_once('=').filter(|_| line.starts_with(&prefix)) {
            let v = crate::py::strip(v);
            return if v.is_empty() {
                PyVal::None
            } else {
                PyVal::str(v)
            };
        }
    }
    PyVal::None
}

/// `SedMgmtBase.get_tpm_bank_a_address`.
pub fn get_tpm_bank_a_address<S: PyObject + ?Sized>(_s: &S) -> PyResult<PyVal> {
    Ok(read_sed_config_value("tpm_bank_a"))
}

/// `SedMgmtBase.get_tpm_bank_b_address`.
pub fn get_tpm_bank_b_address<S: PyObject + ?Sized>(_s: &S) -> PyResult<PyVal> {
    Ok(read_sed_config_value("tpm_bank_b"))
}

/// `n < v` (or `n > v`) for the int `len()` answers.
fn cmp_len(n: usize, op: &str, v: &PyVal) -> PyResult<bool> {
    let n = n as f64;
    let x = match v {
        PyVal::Int(i) => *i as f64,
        PyVal::Bool(b) => f64::from(u8::from(*b)),
        PyVal::Float(f) => *f,
        other => {
            return Err(PyErr::type_error(format!(
                "'{op}' not supported between instances of 'int' and '{}'",
                other.type_name()
            )))
        }
    };
    Ok(if op == "<" { n < x } else { n > x })
}

/// An argv element: what `Popen` accepts.
fn arg(v: &PyVal) -> PyResult<&str> {
    match v {
        PyVal::Str(s) => Ok(s),
        other => Err(PyErr::type_error(format!(
            "expected str, bytes or os.PathLike object, not {}",
            other.type_name()
        ))),
    }
}

/// The bank addresses, or the error logged when either is missing.
fn banks<S: PyObject + ?Sized>(s: &S) -> PyResult<Option<(PyVal, PyVal)>> {
    let bank_a = s.get_tpm_bank_a_address()?;
    let bank_b = s.get_tpm_bank_b_address()?;
    if !bank_a.truthy() || !bank_b.truthy() {
        logger().log_error(&format!(
            "TPM bank address is not valid: bank_a: {}, bank_b: {}. Check {SED_CONFIG_PATH}.",
            bank_a.py_str(),
            bank_b.py_str()
        ));
        return Ok(None);
    }
    Ok(Some((bank_a, bank_b)))
}

fn run_script(script: &str, bank_a: &PyVal, bank_b: &PyVal, pw: &str) -> PyResult<()> {
    subprocess::check_call_quiet(&[script, "-a", arg(bank_a)?, "-b", arg(bank_b)?, "-p", pw])
}

/// `SedMgmtBase.change_sed_password`.
pub fn change_sed_password<S: PyObject + ?Sized>(s: &S, new_password: &str) -> PyResult<PyVal> {
    let r = (|| -> PyResult<bool> {
        let min_len = s.get_min_sed_password_len()?;
        let max_len = s.get_max_sed_password_len()?;
        let n = new_password.chars().count();
        if cmp_len(n, "<", &min_len)? || cmp_len(n, ">", &max_len)? {
            logger().log_error(&format!(
                "SED password length is not valid: {n}. min_len: {}, max_len: {}",
                min_len.py_str(),
                max_len.py_str()
            ));
            return Ok(false);
        }
        let Some((bank_a, bank_b)) = banks(s)? else {
            return Ok(false);
        };
        run_script(SED_PW_CHANGE_SCRIPT, &bank_a, &bank_b, new_password)?;
        Ok(true)
    })();
    Ok(PyVal::Bool(r.unwrap_or_else(|e| {
        logger().log_error(&format!("Failed to change SED password: {}", e.str()));
        false
    })))
}

/// `SedMgmtBase.reset_sed_password`.
pub fn reset_sed_password<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    let r = (|| -> PyResult<bool> {
        let default_pw = s.get_default_sed_password()?;
        if !default_pw.truthy() {
            logger().log_error("Failed to get default SED password.");
            return Ok(false);
        }
        let Some((bank_a, bank_b)) = banks(s)? else {
            return Ok(false);
        };
        run_script(SED_PW_RESET_SCRIPT, &bank_a, &bank_b, arg(&default_pw)?)?;
        Ok(true)
    })();
    Ok(PyVal::Bool(r.unwrap_or_else(|e| {
        logger().log_error(&format!("Failed to reset SED password: {}", e.str()));
        false
    })))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::object::{BaseClass, DynObject};
    use crate::testing::Root;

    /// A SedMgmt whose getters answer `answers`; the bank addresses are
    /// SedMgmtBase's, from the config file.
    fn sed(answers: Vec<(&'static str, PyVal)>) -> DynObject {
        DynObject {
            class: "SedMgmt",
            base: BaseClass::SedMgmtBase,
            handler: Box::new(move |_, m, _| {
                answers
                    .iter()
                    .find(|(k, _)| *k == m)
                    .map(|(_, v)| Ok(v.clone()))
            }),
        }
    }

    fn lengths() -> Vec<(&'static str, PyVal)> {
        vec![
            ("get_min_sed_password_len", PyVal::Int(8)),
            ("get_max_sed_password_len", PyVal::Int(16)),
        ]
    }

    #[test]
    fn bank_addresses_are_the_config_file_s_first_matching_line() {
        let root = Root::new();
        let s = sed(vec![]);
        assert_eq!(s.get_tpm_bank_a_address().unwrap(), PyVal::None);
        root.write(
            SED_CONFIG_PATH,
            "# SED\r\n  tpm_bank_a = ignored\ntpm_bank_a= 0x81010001 \r\ntpm_bank_a=0x2\rtpm_bank_b=\n",
        );
        assert_eq!(
            s.get_tpm_bank_a_address().unwrap(),
            PyVal::str("0x81010001")
        );
        assert_eq!(s.get_tpm_bank_b_address().unwrap(), PyVal::None);
        root.write(SED_CONFIG_PATH, "tpm_bank_b=0x81010002");
        assert_eq!(
            s.get_tpm_bank_b_address().unwrap(),
            PyVal::str("0x81010002")
        );
    }

    #[test]
    fn a_password_change_is_checked_then_run_by_the_common_script() {
        let root = Root::new();
        let s = sed(lengths());
        let change = |pw: &str| s.change_sed_password(pw).unwrap();
        // Too short, too long.
        assert_eq!(change("short"), PyVal::Bool(false));
        assert_eq!(change("a-password-far-too-long"), PyVal::Bool(false));
        // No bank addresses.
        assert_eq!(change("password1"), PyVal::Bool(false));
        root.write(
            SED_CONFIG_PATH,
            "tpm_bank_a=0x81010001\ntpm_bank_b=0x81010002\n",
        );
        // The script is not there: the error is logged, and False.
        assert_eq!(change("password1"), PyVal::Bool(false));
        // A length that is not a number is Python's TypeError, caught.
        assert_eq!(
            sed(vec![("get_min_sed_password_len", PyVal::str("8"))])
                .change_sed_password("password1")
                .unwrap(),
            PyVal::Bool(false)
        );
        assert!(cmp_len(9, ">", &PyVal::Float(8.5)).unwrap());
        assert!(!cmp_len(1, "<", &PyVal::Bool(true)).unwrap());
        assert_eq!(
            cmp_len(1, "<", &PyVal::str("8")).map_err(|e| e.str()),
            Err("'<' not supported between instances of 'int' and 'str'".into())
        );
        assert_eq!(
            arg(&PyVal::Int(1)).map_err(|e| e.str()),
            Err("expected str, bytes or os.PathLike object, not int".into())
        );
    }

    #[test]
    fn a_password_reset_uses_the_platform_default() {
        let root = Root::new();
        // No default password.
        assert_eq!(
            sed(vec![]).reset_sed_password().unwrap(),
            PyVal::Bool(false)
        );
        assert_eq!(
            sed(vec![("get_default_sed_password", PyVal::str(""))])
                .reset_sed_password()
                .unwrap(),
            PyVal::Bool(false)
        );
        let s = sed(vec![("get_default_sed_password", PyVal::str("default-pw"))]);
        assert_eq!(s.reset_sed_password().unwrap(), PyVal::Bool(false));
        root.write(
            SED_CONFIG_PATH,
            "tpm_bank_a=0x81010001\ntpm_bank_b=0x81010002\n",
        );
        assert_eq!(s.reset_sed_password().unwrap(), PyVal::Bool(false));
    }
}
