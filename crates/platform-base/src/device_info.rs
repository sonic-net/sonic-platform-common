//! `sonic_py_common.device_info`, the parts platform code calls.

use crate::io;
use crate::py::{Exc, PyErr, PyResult, PyVal};

pub const HOST_DEVICE_PATH: &str = "/usr/share/sonic/device";
pub const CONTAINER_PLATFORM_PATH: &str = "/usr/share/sonic/platform";
pub const MACHINE_CONF_PATH: &str = "/host/machine.conf";
pub const PLATFORM_ENV_CONF_FILENAME: &str = "platform_env.conf";

/// `get_machine_info()`: `machine.conf` as key/value pairs, in file order;
/// a file that is there and will not read raises, as Python's `open()` does.
pub fn get_machine_info() -> PyResult<Option<Vec<(String, String)>>> {
    if !io::is_file(MACHINE_CONF_PATH) {
        return Ok(None);
    }
    let text = io::read_text(MACHINE_CONF_PATH)?;
    let mut out: Vec<(String, String)> = Vec::new();
    for line in text.split_inclusive('\n') {
        let tokens: Vec<&str> = line.split('=').collect();
        if tokens.len() < 2 {
            continue;
        }
        let (k, v) = (tokens[0].to_string(), tokens[1].trim().to_string());
        // A dict: a later line for the same key replaces the earlier one.
        match out.iter_mut().find(|(k2, _)| *k2 == k) {
            Some(e) => e.1 = v,
            None => out.push((k, v)),
        }
    }
    Ok(Some(out))
}

/// `get_platform()`: `$PLATFORM`, then `machine.conf`.
///
/// Python falls back to CONFIG_DB last; inside pmon `$PLATFORM` is always
/// set, so that branch is not reached by anything this crate serves.
pub fn get_platform() -> PyResult<Option<String>> {
    if let Ok(p) = std::env::var("PLATFORM") {
        if !p.is_empty() {
            return Ok(Some(p));
        }
    }
    let Some(info) = get_machine_info()? else {
        return Ok(None);
    };
    for key in ["onie_platform", "aboot_platform"] {
        if let Some((_, v)) = info.iter().find(|(k, _)| k == key) {
            return Ok(Some(v.clone()));
        }
    }
    Ok(None)
}

/// The platform, if Python's `if platform:` would take it: `get_platform()`
/// answers machine.conf's `onie_platform=` as it is, empty included, and
/// the callers that test it treat an empty one as none.
fn platform_if_set() -> PyResult<Option<String>> {
    Ok(get_platform()?.filter(|p| !p.is_empty()))
}

/// `get_platform_env_conf_file_path()`.
pub fn get_platform_env_conf_file_path() -> PyResult<Option<String>> {
    let mut candidates = vec![io::join(
        CONTAINER_PLATFORM_PATH,
        PLATFORM_ENV_CONF_FILENAME,
    )];
    if let Some(p) = platform_if_set()? {
        candidates.push(io::join(
            &io::join(HOST_DEVICE_PATH, &p),
            PLATFORM_ENV_CONF_FILENAME,
        ));
    }
    Ok(candidates.into_iter().find(|c| io::is_file(c)))
}

/// `is_platform_env_key_present(key)`: `<key>=1` in `platform_env.conf`.
pub fn is_platform_env_key_present(key: &str) -> PyResult<bool> {
    let Some(path) = get_platform_env_conf_file_path()? else {
        return Ok(false);
    };
    let text = io::read_text(&path)?;
    for line in text.split_inclusive('\n') {
        let tokens: Vec<&str> = line.split('=').collect();
        if tokens.len() < 2 {
            continue;
        }
        if tokens[0].trim().to_lowercase() == key.trim().to_lowercase() {
            return Ok(tokens[1].trim() == "1");
        }
    }
    Ok(false)
}

/// `is_switch_bmc()`.
pub fn is_switch_bmc() -> PyResult<bool> {
    is_platform_env_key_present("switch_bmc")
}

/// `is_switch_host()`.
pub fn is_switch_host() -> PyResult<bool> {
    is_platform_env_key_present("switch_host")
}

pub const ASIC_CONF_FILENAME: &str = "asic.conf";
pub const PLATFORM_JSON_FILE: &str = "platform.json";
pub const GLOBAL_BMC_DATA_FILE: &str = "/etc/sonic/bmc.json";
pub const BMC_BUILD_CONFIG_FILE: &str = "/etc/sonic/bmc_config.json";

/// `get_bmc_build_config()`: the file's JSON, or None on any failure.
pub fn get_bmc_build_config() -> Option<PyVal> {
    if !io::exists(BMC_BUILD_CONFIG_FILE) {
        return None;
    }
    crate::json::load(BMC_BUILD_CONFIG_FILE).ok()
}

/// `get_localhost_info(field)`: `DEVICE_METADATA|localhost`'s field, or None
/// on any failure -- Python swallows them all.
pub fn get_localhost_info(field: &str) -> Option<String> {
    let db = crate::db::Db::connect_config_db().ok()?;
    let key = db.key("DEVICE_METADATA", "localhost");
    db.hget(&key, field).ok().flatten()
}

static HWSKU: std::sync::Mutex<Option<String>> = std::sync::Mutex::new(None);

/// `get_hwsku()`: the first non-empty answer is cached, a failed one is not.
pub fn get_hwsku() -> Option<String> {
    if let Some(h) = HWSKU.lock().ok().and_then(|h| h.clone()) {
        if !h.is_empty() {
            return Some(h);
        }
    }
    let h = get_localhost_info("hwsku");
    if let (Some(v), Ok(mut slot)) = (h.as_ref(), HWSKU.lock()) {
        *slot = Some(v.clone());
    }
    h
}

/// `os.path.join(a, None)`'s error, for callers that join a missing value.
pub fn join_none_error() -> PyErr {
    PyErr::type_error("join() argument must be str, bytes, or os.PathLike object, not 'NoneType'")
}

/// `get_path_to_platform_dir()`.
pub fn get_path_to_platform_dir() -> PyResult<String> {
    // `os.path.join(HOST_DEVICE_PATH, platform)` runs before either check,
    // so a None platform raises even in a container.
    let platform = get_platform()?.ok_or_else(join_none_error)?;
    let host = io::join(HOST_DEVICE_PATH, &platform);
    if io::is_dir(CONTAINER_PLATFORM_PATH) {
        return Ok(CONTAINER_PLATFORM_PATH.to_string());
    }
    if io::is_dir(&host) {
        return Ok(host);
    }
    Err(PyErr::new(
        Exc::OSError("OSError"),
        vec![PyVal::str("Failed to locate platform directory")],
    ))
}

/// `get_path_to_hwsku_dir()`.
pub fn get_path_to_hwsku_dir() -> PyResult<String> {
    let platform_path = get_path_to_platform_dir()?;
    let hwsku = get_hwsku().ok_or_else(join_none_error)?;
    Ok(io::join(&platform_path, &hwsku))
}

/// `get_paths_to_platform_and_hwsku_dirs()`.
pub fn get_paths_to_platform_and_hwsku_dirs() -> PyResult<(String, String)> {
    let platform_path = get_path_to_platform_dir()?;
    let hwsku = get_hwsku().ok_or_else(join_none_error)?;
    let hwsku_path = io::join(&platform_path, &hwsku);
    Ok((platform_path, hwsku_path))
}

/// `get_asic_conf_file_path()`.
///
/// Python yields the candidates from a generator, so the container's
/// asic.conf is found before the platform is asked for.
pub fn get_asic_conf_file_path() -> PyResult<Option<String>> {
    let container = io::join(CONTAINER_PLATFORM_PATH, ASIC_CONF_FILENAME);
    if io::is_file(&container) {
        return Ok(Some(container));
    }
    let Some(p) = platform_if_set()? else {
        return Ok(None);
    };
    let host = io::join(&io::join(HOST_DEVICE_PATH, &p), ASIC_CONF_FILENAME);
    Ok(io::is_file(&host).then_some(host))
}

/// `get_num_npus()`: 1 without an asic.conf; Python's `UnboundLocalError`
/// when the file has no `num_asic` line, which it does not guard against.
pub fn get_num_npus() -> PyResult<i128> {
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
        Some(n) => crate::py::py_int(&n),
        None => Err(PyErr::other(
            "UnboundLocalError",
            "cannot access local variable 'num_npus' where it is not associated with a value",
        )),
    }
}

/// `get_platform_json_data()`: platform.json, or None when there is no
/// platform, no platform directory or no readable JSON.  A machine.conf that
/// will not read raises, as Python asks for the platform outside any `try`.
pub fn get_platform_json_data() -> PyResult<Option<PyVal>> {
    if platform_if_set()?.is_none() {
        return Ok(None);
    }
    // `except OSError`.
    let dir = match get_path_to_platform_dir() {
        Ok(d) => d,
        Err(e) if e.exc.is_os_error() => return Ok(None),
        Err(e) => return Err(e),
    };
    Ok(crate::json::load(&io::join(&dir, PLATFORM_JSON_FILE)).ok())
}

/// `is_smartswitch()`.
pub fn is_smartswitch() -> PyResult<bool> {
    if platform_if_set()?.is_none() {
        return Ok(false);
    }
    Ok(get_platform_json_data()?.is_some_and(|d| crate::json::get(&d, "DPUS").is_some()))
}

/// `is_dpu()`.
pub fn is_dpu() -> PyResult<bool> {
    if platform_if_set()?.is_none() {
        return Ok(false);
    }
    Ok(get_platform_json_data()?.is_some_and(|d| crate::json::get(&d, "DPU").is_some()))
}

/// `get_bmc_data()`: /etc/sonic/bmc.json, or None.
pub fn get_bmc_data() -> Option<PyVal> {
    if !io::exists(GLOBAL_BMC_DATA_FILE) {
        return None;
    }
    crate::json::load(GLOBAL_BMC_DATA_FILE).ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::testing::{FakeRedis, Root, CONFIG_DB};

    fn err<T: std::fmt::Debug>(r: PyResult<T>) -> (String, String) {
        let e = r.expect_err("an error");
        (e.exc.name().to_string(), e.str())
    }

    /// `onie_platform=` with nothing after it: `get_platform()` answers it as
    /// it is, and the callers that test it with `if platform:` take it as no
    /// platform -- here a platform.json sitting in the bare device directory
    /// is not read.
    #[test]
    fn an_empty_platform_is_no_platform_where_python_tests_it() {
        let root = Root::new();
        if env_platform().is_some() {
            return;
        }
        root.write(MACHINE_CONF_PATH, "onie_platform=\n");
        root.write(
            &io::join(HOST_DEVICE_PATH, PLATFORM_JSON_FILE),
            r#"{"DPUS": {}, "DPU": {}}"#,
        );
        assert_eq!(get_platform().unwrap().as_deref(), Some(""));
        assert!(get_platform_json_data().unwrap().is_none());
        assert!(!is_smartswitch().unwrap());
        assert!(!is_dpu().unwrap());
    }

    /// A file that is there and will not read raises, as Python's reading of
    /// it does, and so does every caller Python lets it out of.
    #[test]
    fn a_conf_file_that_will_not_read_raises() {
        let root = Root::new();
        let undecodable = |path: &str, bytes: &[u8]| {
            root.write(path, "");
            std::fs::write(root.real(path), bytes).unwrap();
        };
        undecodable(
            &format!("{CONTAINER_PLATFORM_PATH}/{PLATFORM_ENV_CONF_FILENAME}"),
            b"switch_bmc=1\xff\n",
        );
        assert_eq!(err(is_switch_bmc()).0, "UnicodeDecodeError");
        assert_eq!(err(is_switch_host()).0, "UnicodeDecodeError");
        if env_platform().is_some() {
            return;
        }
        undecodable(MACHINE_CONF_PATH, b"onie_platform=x86_64-\xff-r0\n");
        for e in [
            err(get_machine_info()),
            err(get_platform()),
            err(get_platform_env_conf_file_path()),
            err(get_path_to_platform_dir()),
            err(get_asic_conf_file_path()),
            err(get_platform_json_data()),
            err(is_smartswitch()),
            err(is_dpu()),
        ] {
            assert_eq!(e.0, "UnicodeDecodeError");
        }
        // The container's asic.conf is found before the platform is asked for.
        let asic = format!("{CONTAINER_PLATFORM_PATH}/{ASIC_CONF_FILENAME}");
        root.write(&asic, "num_asic=2\n");
        assert_eq!(get_asic_conf_file_path().unwrap(), Some(asic));
        assert_eq!(get_num_npus().unwrap(), 2);
    }

    /// `$PLATFORM` comes before machine.conf; a test does not change the
    /// process's environment, so it expects whichever is there.
    fn env_platform() -> Option<String> {
        std::env::var("PLATFORM").ok().filter(|p| !p.is_empty())
    }

    /// machine.conf naming a platform: `$PLATFORM`'s, if set, so both agree.
    fn platform(root: &Root) -> String {
        let p = env_platform().unwrap_or_else(|| "x86_64-test-r0".into());
        root.write(MACHINE_CONF_PATH, &format!("onie_platform={p}\n"));
        p
    }

    #[test]
    fn machine_conf_is_read_as_python_reads_it() {
        let root = Root::new();
        assert_eq!(get_machine_info().unwrap(), None);
        assert_eq!(get_platform().unwrap(), env_platform());
        root.write(
            MACHINE_CONF_PATH,
            "onie_machine=x\nonie_platform=x86_64-early-r0\nno equals sign\nonie_platform=x86_64-later-r0\nkey=a=b\n",
        );
        let info = get_machine_info().unwrap().unwrap();
        let value = |k: &str| info.iter().find(|(k2, _)| k2 == k).map(|(_, v)| v.clone());
        assert_eq!(info.len(), 3);
        assert_eq!(value("onie_platform").as_deref(), Some("x86_64-later-r0"));
        assert_eq!(value("key").as_deref(), Some("a"));
        assert_eq!(
            get_platform().unwrap(),
            Some(env_platform().unwrap_or_else(|| "x86_64-later-r0".into()))
        );
        root.write(MACHINE_CONF_PATH, "aboot_platform=x86_64-arista_7050\n");
        assert_eq!(
            get_platform().unwrap(),
            Some(env_platform().unwrap_or_else(|| "x86_64-arista_7050".into()))
        );
        root.write(MACHINE_CONF_PATH, "onie_version=2023\n");
        assert_eq!(get_platform().unwrap(), env_platform());
    }

    #[test]
    fn platform_env_keys_are_read_from_the_container_or_the_host_path() {
        let root = Root::new();
        assert_eq!(get_platform_env_conf_file_path().unwrap(), None);
        assert!(!is_switch_host().unwrap());
        let p = platform(&root);
        let host = format!("{HOST_DEVICE_PATH}/{p}/{PLATFORM_ENV_CONF_FILENAME}");
        root.write(&host, "noise\n SWITCH_HOST = 1 \nswitch_bmc=0\n");
        assert_eq!(
            get_platform_env_conf_file_path().unwrap().as_deref(),
            Some(host.as_str())
        );
        assert!(is_switch_host().unwrap());
        assert!(!is_switch_bmc().unwrap());
        assert!(!is_platform_env_key_present("absent").unwrap());
        let container = format!("{CONTAINER_PLATFORM_PATH}/{PLATFORM_ENV_CONF_FILENAME}");
        root.write(&container, "switch_bmc=1\n");
        assert_eq!(
            get_platform_env_conf_file_path().unwrap().as_deref(),
            Some(container.as_str())
        );
        assert!(is_switch_bmc().unwrap());
        assert!(!is_switch_host().unwrap());
    }

    #[test]
    fn platform_and_hwsku_directories_are_found_as_python_finds_them() {
        let root = Root::new();
        let p = platform(&root);
        assert_eq!(
            err(get_path_to_platform_dir()),
            (
                "OSError".into(),
                "Failed to locate platform directory".into()
            )
        );
        let host = format!("{HOST_DEVICE_PATH}/{p}");
        std::fs::create_dir_all(root.real(&host)).unwrap();
        assert_eq!(get_path_to_platform_dir().unwrap(), host);
        std::fs::create_dir_all(root.real(CONTAINER_PLATFORM_PATH)).unwrap();
        assert_eq!(get_path_to_platform_dir().unwrap(), CONTAINER_PLATFORM_PATH);
        // No CONFIG_DB: no hwsku, and nothing cached.
        assert_eq!(get_localhost_info("hwsku"), None);
        let redis = FakeRedis::get();
        redis.install(&root);
        redis.set(CONFIG_DB, "CONFIG_DB_INITIALIZED", "1");
        redis.hset(
            CONFIG_DB,
            "DEVICE_METADATA|localhost",
            &[("hwsku", "SKU-A"), ("platform", "p")],
        );
        assert_eq!(get_localhost_info("platform").as_deref(), Some("p"));
        assert_eq!(get_localhost_info("absent"), None);
        let sku = get_hwsku().unwrap();
        redis.hset(
            CONFIG_DB,
            "DEVICE_METADATA|localhost",
            &[("hwsku", "SKU-B")],
        );
        assert_eq!(get_hwsku().unwrap(), sku);
        let hwsku_dir = format!("{CONTAINER_PLATFORM_PATH}/{sku}");
        assert_eq!(get_path_to_hwsku_dir().unwrap(), hwsku_dir);
        assert_eq!(
            get_paths_to_platform_and_hwsku_dirs().unwrap(),
            (CONTAINER_PLATFORM_PATH.to_string(), hwsku_dir)
        );
        assert_eq!(
            join_none_error().str(),
            "join() argument must be str, bytes, or os.PathLike object, not 'NoneType'"
        );
    }

    #[test]
    fn without_a_platform_the_platform_directory_raises_even_in_a_container() {
        if std::env::var("PLATFORM").is_ok_and(|p| !p.is_empty()) {
            return;
        }
        let root = Root::new();
        std::fs::create_dir_all(root.real(CONTAINER_PLATFORM_PATH)).unwrap();
        assert_eq!(
            err(get_path_to_platform_dir()),
            (
                "TypeError".into(),
                "join() argument must be str, bytes, or os.PathLike object, not 'NoneType'".into()
            )
        );
    }

    #[test]
    fn platform_json_says_smartswitch_or_dpu() {
        let root = Root::new();
        platform(&root);
        assert!(get_platform_json_data().unwrap().is_none());
        assert!(!is_smartswitch().unwrap() && !is_dpu().unwrap());
        let json = format!("{CONTAINER_PLATFORM_PATH}/{PLATFORM_JSON_FILE}");
        root.write(&json, r#"{"DPUS": {"dpu0": {}}}"#);
        assert!(is_smartswitch().unwrap() && !is_dpu().unwrap());
        root.write(&json, r#"{"DPU": {}}"#);
        assert!(is_dpu().unwrap() && !is_smartswitch().unwrap());
        root.write(&json, "not json");
        assert!(get_platform_json_data().unwrap().is_none());
    }

    #[test]
    fn bmc_files_are_their_json_or_none() {
        let root = Root::new();
        assert_eq!(get_bmc_data(), None);
        assert_eq!(get_bmc_build_config(), None);
        root.write(GLOBAL_BMC_DATA_FILE, r#"{"bmc_addr": "169.254.0.1"}"#);
        root.write(BMC_BUILD_CONFIG_FILE, "{broken");
        assert_eq!(
            get_bmc_data().unwrap().py_repr(),
            "{'bmc_addr': '169.254.0.1'}"
        );
        assert_eq!(get_bmc_build_config(), None);
    }

    #[test]
    fn the_npu_count_is_asic_conf_s() {
        let root = Root::new();
        let p = platform(&root);
        assert_eq!(get_asic_conf_file_path().unwrap(), None);
        assert_eq!(get_num_npus().unwrap(), 1);
        let host = format!("{HOST_DEVICE_PATH}/{p}/{ASIC_CONF_FILENAME}");
        root.write(&host, "NUM_ASIC=3\nDEV_ID_ASIC_0=03:00.0\n");
        assert_eq!(
            get_asic_conf_file_path().unwrap().as_deref(),
            Some(host.as_str())
        );
        assert_eq!(get_num_npus().unwrap(), 3);
        let container = format!("{CONTAINER_PLATFORM_PATH}/{ASIC_CONF_FILENAME}");
        root.write(&container, "DEV_ID_ASIC_0=03:00.0\n");
        assert_eq!(
            err(get_num_npus()),
            (
                "UnboundLocalError".into(),
                "cannot access local variable 'num_npus' where it is not associated with a value"
                    .into()
            )
        );
        root.write(&container, "num_asic=two\n");
        assert_eq!(err(get_num_npus()).0, "ValueError");
    }
}
