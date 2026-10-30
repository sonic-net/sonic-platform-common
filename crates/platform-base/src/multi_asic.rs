//! The parts of `sonic_py_common.multi_asic` a platform API reaches.

use crate::device_info::get_asic_conf_file_path;
use crate::io;
use crate::py::{py_int, PyErr, PyResult};

pub const DEFAULT_NAMESPACE: &str = "";
pub const ASIC_NAME_PREFIX: &str = "asic";

/// `get_num_asics()`: the same reading as `device_info.get_num_npus()`,
/// down to the `UnboundLocalError` on an asic.conf without `num_asic`.
pub fn get_num_asics() -> PyResult<i128> {
    let Some(path) = get_asic_conf_file_path()? else {
        return Ok(1);
    };
    let text = io::read_text(&path)?;
    let mut num: Option<String> = None;
    for line in text.split_inclusive('\n') {
        let tokens: Vec<&str> = line.split('=').collect();
        if tokens.len() < 2 {
            continue;
        }
        if tokens[0].to_lowercase() == "num_asic" {
            num = Some(tokens[1].trim().to_string());
        }
    }
    match num {
        Some(n) => py_int(&n),
        None => Err(PyErr::other(
            "UnboundLocalError",
            "cannot access local variable 'num_asics' where it is not associated with a value",
        )),
    }
}

/// `is_multi_asic()`.
pub fn is_multi_asic() -> PyResult<bool> {
    Ok(get_num_asics()? > 1)
}

/// `get_asic_id_from_name(asic_name)`.
pub fn get_asic_id_from_name(asic_name: &str) -> PyResult<String> {
    match asic_name.strip_prefix(ASIC_NAME_PREFIX) {
        Some(id) => Ok(id.to_string()),
        None => Err(PyErr::value_error(format!(
            "Unknown asic namespace name {asic_name}"
        ))),
    }
}

/// `get_asic_index_from_namespace(namespace)`: 0 on a single-ASIC system.
pub fn get_asic_index_from_namespace(namespace: &str) -> PyResult<i128> {
    if is_multi_asic()? {
        return py_int(&get_asic_id_from_name(namespace)?);
    }
    Ok(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::device_info::{ASIC_CONF_FILENAME, CONTAINER_PLATFORM_PATH};
    use crate::testing::Root;

    fn err<T: std::fmt::Debug>(r: PyResult<T>) -> (String, String) {
        let e = r.expect_err("an error");
        (e.exc.name().to_string(), e.str())
    }

    #[test]
    fn asics_are_counted_and_named_as_python_does() {
        let root = Root::new();
        let conf = format!("{CONTAINER_PLATFORM_PATH}/{ASIC_CONF_FILENAME}");
        assert_eq!(get_num_asics().unwrap(), 1);
        assert!(!is_multi_asic().unwrap());
        assert_eq!(get_asic_index_from_namespace("asic1").unwrap(), 0);
        root.write(&conf, "num_asic=2\n");
        assert!(is_multi_asic().unwrap());
        assert_eq!(get_asic_index_from_namespace("asic1").unwrap(), 1);
        assert_eq!(get_asic_id_from_name("asic12").unwrap(), "12");
        assert_eq!(
            err(get_asic_id_from_name("ns1")),
            (
                "ValueError".into(),
                "Unknown asic namespace name ns1".into()
            )
        );
        assert_eq!(
            err(get_asic_index_from_namespace(DEFAULT_NAMESPACE)).0,
            "ValueError"
        );
        root.write(&conf, "no count here\n");
        assert_eq!(
            err(get_num_asics()),
            (
                "UnboundLocalError".into(),
                "cannot access local variable 'num_asics' where it is not associated with a value"
                    .into()
            )
        );
        assert_eq!(err(is_multi_asic()).0, "UnboundLocalError");
    }
}
