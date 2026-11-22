//! `sonic_platform_base.sonic_pcie.pcie_common.PcieUtil`: pcie.yaml checked
//! against the devices sysfs shows, and a device's AER counters.
//!
//! A vendor with its own `Pcie` class implements [`PcieApi`] over this one
//! and hands the escape hatch a constructor for it.

use crate::io;
use crate::py::{PyErr, PyResult, PyVal};

/// What pcied asks of a PCIe object.
pub trait PcieApi: Send + Sync {
    /// `get_pcie_check()`: the configured devices, each with a `result`.
    fn get_pcie_check(&self) -> PyResult<PyVal>;
    /// `get_pcie_aer_stats(domain, bus, dev, func)`: counters by severity.
    fn get_pcie_aer_stats(&self, domain: i64, bus: i64, dev: i64, func: i64) -> PyResult<PyVal>;
}

/// `print(msg)`, to the daemon's stdout.
fn print(msg: &str) {
    use std::io::Write;
    let _ = writeln!(std::io::stdout(), "{msg}");
}

/// `PcieUtil(path)`.
pub struct PcieUtil {
    pub config_path: String,
}

impl PcieUtil {
    pub fn new(path: &str) -> PcieUtil {
        PcieUtil {
            config_path: path.to_string(),
        }
    }

    /// `load_config_file()`: `self.confInfo`.  Without the file it prints
    /// two lines and calls `sys.exit()` -- a `SystemExit`, which no
    /// `except Exception` stops.
    pub fn load_config_file(&self) -> PyResult<PyVal> {
        let file = format!("{}/pcie.yaml", self.config_path);
        match io::read_text(&file) {
            Ok(text) => crate::yaml::safe_load(&text),
            Err(e) if e.exc.is_os_error() => {
                print(&format!("Error: {}", e.str()));
                print("Not found config file, please add a config file manually, or generate it by running [pcieutil pcie_generate]");
                Err(PyErr::other("SystemExit", ""))
            }
            Err(e) => Err(e),
        }
    }

    /// `check_pcie_sysfs(domain, bus, device, func)`.
    pub fn check_pcie_sysfs(&self, domain: i128, bus: i128, device: i128, func: i128) -> bool {
        io::exists(&dev_path(domain, bus, device, func))
    }
}

/// `'%04x:%02x:%02x.%d' % (domain, bus, device, func)` under the PCI devices.
pub fn dev_path(domain: i128, bus: i128, device: i128, func: i128) -> String {
    let hex = |v: i128, w: usize| {
        if v < 0 {
            format!("-{:0w$x}", -v, w = w.saturating_sub(1))
        } else {
            format!("{v:0w$x}")
        }
    };
    format!(
        "/sys/bus/pci/devices/{}:{}:{}.{func}",
        hex(domain, 4),
        hex(bus, 2),
        hex(device, 2)
    )
}

/// `int(value, base=16)` on what yaml gave: only a string converts.
pub fn int_hex(v: &PyVal) -> PyResult<i128> {
    match v {
        PyVal::Str(s) => crate::py::py_int_base(s, 16),
        _ => Err(PyErr::type_error(
            "int() can't convert non-string with explicit base",
        )),
    }
}

/// `d[key]` on a yaml mapping: KeyError, or TypeError off a mapping.
pub fn item(d: &PyVal, key: &str) -> PyResult<PyVal> {
    crate::json::index(d, key).cloned()
}

/// `d[key] = value` on a yaml mapping.
pub fn set_item(d: &mut PyVal, key: &str, value: PyVal) -> PyResult<()> {
    match d {
        PyVal::Dict(items) => {
            match items
                .iter_mut()
                .find(|(k, _)| matches!(k, PyVal::Str(s) if s == key))
            {
                Some(e) => e.1 = value,
                None => items.push((PyVal::str(key), value)),
            }
            Ok(())
        }
        other => Err(PyErr::type_error(format!(
            "'{}' object does not support item assignment",
            other.type_name()
        ))),
    }
}

/// `for x in value`, for what yaml gave.
pub fn iterate(v: &PyVal) -> PyResult<Vec<PyVal>> {
    v.iter_items()
        .ok_or_else(|| PyErr::type_error(format!("'{}' object is not iterable", v.type_name())))
}

impl PcieApi for PcieUtil {
    fn get_pcie_check(&self) -> PyResult<PyVal> {
        let conf = self.load_config_file()?;
        let mut out = Vec::new();
        for mut item_conf in iterate(&conf)? {
            let bus = int_hex(&item(&item_conf, "bus")?)?;
            let dev = int_hex(&item(&item_conf, "dev")?)?;
            let func = int_hex(&item(&item_conf, "fn")?)?;
            let result = if self.check_pcie_sysfs(0, bus, dev, func) {
                "Passed"
            } else {
                "Failed"
            };
            set_item(&mut item_conf, "result", PyVal::str(result))?;
            out.push(item_conf);
        }
        // The same list object, mutated in place.
        Ok(match conf {
            PyVal::List(_) => PyVal::List(out),
            other => other,
        })
    }

    fn get_pcie_aer_stats(&self, domain: i64, bus: i64, dev: i64, func: i64) -> PyResult<PyVal> {
        aer_stats(&dev_path(
            domain.into(),
            bus.into(),
            dev.into(),
            func.into(),
        ))
    }
}

/// The AER counters under `dev_path`: `{'correctable': {..}, 'fatal': {..},
/// 'non_fatal': {..}}`, each line `field value` -- any other shape raises
/// the `ValueError` of `field, value = line.split()`.
pub fn aer_stats(dev_path: &str) -> PyResult<PyVal> {
    let mut out = Vec::new();
    for (severity, file) in [
        ("correctable", "aer_dev_correctable"),
        ("fatal", "aer_dev_fatal"),
        ("non_fatal", "aer_dev_nonfatal"),
    ] {
        let mut fields: Vec<(PyVal, PyVal)> = Vec::new();
        let path = io::join(dev_path, file);
        if io::is_file(&path) {
            let text = io::read_text(&path)?;
            for line in text.split_inclusive('\n') {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() != 2 {
                    return Err(PyErr::value_error(if parts.len() < 2 {
                        format!(
                            "not enough values to unpack (expected 2, got {})",
                            parts.len()
                        )
                    } else {
                        "too many values to unpack (expected 2)".to_string()
                    }));
                }
                let key = PyVal::str(parts[0]);
                match fields.iter_mut().find(|(k, _)| k.py_eq(&key)) {
                    Some(e) => e.1 = PyVal::str(parts[1]),
                    None => fields.push((key, PyVal::str(parts[1]))),
                }
            }
        }
        out.push((PyVal::str(severity), PyVal::Dict(fields)));
    }
    Ok(PyVal::Dict(out))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::testing::Root;

    const PLATFORM: &str = "/usr/share/sonic/platform";

    fn device(root: &Root, name: &str) {
        std::fs::create_dir_all(root.real(&format!("/sys/bus/pci/devices/{name}"))).unwrap();
    }

    #[test]
    fn each_configured_device_passes_if_sysfs_has_it() {
        let root = Root::new();
        root.write(
            &format!("{PLATFORM}/pcie.yaml"),
            "- bus: '00'\n  dev: '1f'\n  fn: '0'\n  id: a0b2\n  name: 'SMBus: Intel'\n- bus: '01'\n  dev: '00'\n  fn: '1'\n  id: 1533\n  name: Ethernet\n  result: stale\n",
        );
        device(&root, "0000:00:1f.0");
        let util = PcieUtil::new(PLATFORM);
        assert_eq!(
            util.get_pcie_check().unwrap().py_repr(),
            "[{'bus': '00', 'dev': '1f', 'fn': '0', 'id': 'a0b2', 'name': 'SMBus: Intel', 'result': 'Passed'}, \
             {'bus': '01', 'dev': '00', 'fn': '1', 'id': 1533, 'name': 'Ethernet', 'result': 'Failed'}]"
        );
        assert!(util.check_pcie_sysfs(0, 0, 0x1f, 0));
        assert!(!util.check_pcie_sysfs(0, 0, 0x1f, 1));
        // A file with no devices is no list to go through.
        root.write(&format!("{PLATFORM}/pcie.yaml"), "# nothing\n");
        assert_eq!(
            util.get_pcie_check().unwrap_err().str(),
            "'NoneType' object is not iterable"
        );
    }

    #[test]
    fn a_device_entry_python_cannot_read_raises_as_in_python() {
        let root = Root::new();
        let check = |yaml: &str| {
            root.write(&format!("{PLATFORM}/pcie.yaml"), yaml);
            let e = PcieUtil::new(PLATFORM).get_pcie_check().unwrap_err();
            format!("{}: {}", e.exc.name(), e.str())
        };
        // An unquoted 00 is the int 0, which int(x, 16) refuses.
        assert_eq!(
            check("- bus: 00\n  dev: '00'\n  fn: '0'\n"),
            "TypeError: int() can't convert non-string with explicit base"
        );
        assert_eq!(
            check("- bus: '00'\n  dev: zz\n  fn: '0'\n"),
            "ValueError: invalid literal for int() with base 16: 'zz'"
        );
        assert_eq!(check("- bus: '00'\n  dev: '00'\n"), "KeyError: 'fn'");
        assert_eq!(
            check("- 5\n"),
            "TypeError: 'int' object is not subscriptable"
        );
        assert_eq!(
            check("-\n"),
            "TypeError: 'NoneType' object is not subscriptable"
        );
        assert_eq!(
            check("- bus\n"),
            "TypeError: string indices must be integers, not 'str'"
        );
        assert_eq!(
            check("- - 1\n"),
            "TypeError: list indices must be integers or slices, not str"
        );
    }

    #[test]
    fn without_a_config_file_it_exits() {
        let _root = Root::new();
        let e = PcieUtil::new(PLATFORM).get_pcie_check().unwrap_err();
        assert_eq!((e.exc.name(), e.str()), ("SystemExit", String::new()));
    }

    #[test]
    fn int_hex_is_int_base_16() {
        let int = |s: &str| int_hex(&PyVal::str(s)).map_err(|e| e.str());
        assert_eq!(int("1f"), Ok(31));
        assert_eq!(int(" 0x1F "), Ok(31));
        assert_eq!(int("0X1f"), Ok(31));
        assert_eq!(int("-1"), Ok(-1));
        assert_eq!(int("+a"), Ok(10));
        assert_eq!(int("1_f"), Ok(31));
        assert_eq!(
            int(""),
            Err("invalid literal for int() with base 16: ''".to_string())
        );
        assert_eq!(
            int("zz"),
            Err("invalid literal for int() with base 16: 'zz'".to_string())
        );
        assert_eq!(
            int("_1"),
            Err("invalid literal for int() with base 16: '_1'".to_string())
        );
        assert_eq!(
            int("1_"),
            Err("invalid literal for int() with base 16: '1_'".to_string())
        );
        assert_eq!(
            int_hex(&PyVal::Int(1)).unwrap_err().str(),
            "int() can't convert non-string with explicit base"
        );
    }

    #[test]
    fn device_paths_format_as_percent_formatting_does() {
        assert_eq!(dev_path(0, 0, 0x1f, 2), "/sys/bus/pci/devices/0000:00:1f.2");
        assert_eq!(dev_path(1, 0x3b, 0, 0), "/sys/bus/pci/devices/0001:3b:00.0");
        assert_eq!(
            dev_path(0, -1, 0x1f, 2),
            "/sys/bus/pci/devices/0000:-1:1f.2"
        );
        assert_eq!(dev_path(-1, 0, 0, 0), "/sys/bus/pci/devices/-001:00:00.0");
    }

    #[test]
    fn aer_counters_come_by_severity() {
        let root = Root::new();
        let dev = "/sys/bus/pci/devices/0000:01:00.0";
        let util = PcieUtil::new(PLATFORM);
        assert_eq!(
            util.get_pcie_aer_stats(0, 1, 0, 0).unwrap().py_repr(),
            "{'correctable': {}, 'fatal': {}, 'non_fatal': {}}"
        );
        root.write(
            &format!("{dev}/aer_dev_correctable"),
            "RxErr 1\nBadTLP 0\nTOTAL_ERR_COR 3\nRxErr 2\n",
        );
        root.write(
            &format!("{dev}/aer_dev_fatal"),
            "Undefined 0\nTOTAL_ERR_FATAL 0\n",
        );
        root.write(&format!("{dev}/aer_dev_nonfatal"), "TOTAL_ERR_NONFATAL 4");
        assert_eq!(
            util.get_pcie_aer_stats(0, 1, 0, 0).unwrap().py_repr(),
            "{'correctable': {'RxErr': '2', 'BadTLP': '0', 'TOTAL_ERR_COR': '3'}, \
             'fatal': {'Undefined': '0', 'TOTAL_ERR_FATAL': '0'}, 'non_fatal': {'TOTAL_ERR_NONFATAL': '4'}}"
        );
        // `field, value = line.split()` on any other shape.
        root.write(&format!("{dev}/aer_dev_fatal"), "a b c\n");
        assert_eq!(
            aer_stats(dev).unwrap_err().str(),
            "too many values to unpack (expected 2)"
        );
        root.write(&format!("{dev}/aer_dev_fatal"), "a\n");
        assert_eq!(
            aer_stats(dev).unwrap_err().str(),
            "not enough values to unpack (expected 2, got 1)"
        );
        root.write(&format!("{dev}/aer_dev_fatal"), "\n");
        assert_eq!(
            aer_stats(dev).unwrap_err().str(),
            "not enough values to unpack (expected 2, got 0)"
        );
    }

    #[test]
    fn yaml_values_are_indexed_and_set_as_python_does() {
        let mut d = PyVal::Dict(vec![(PyVal::str("a"), PyVal::Int(1))]);
        set_item(&mut d, "a", PyVal::Int(2)).unwrap();
        set_item(&mut d, "b", PyVal::Int(3)).unwrap();
        assert_eq!(d.py_repr(), "{'a': 2, 'b': 3}");
        assert_eq!(item(&d, "b").unwrap().py_repr(), "3");
        assert_eq!(item(&d, "c").unwrap_err().str(), "'c'");
        let mut l = PyVal::List(vec![]);
        assert_eq!(
            set_item(&mut l, "a", PyVal::None).unwrap_err().str(),
            "'list' object does not support item assignment"
        );
        assert_eq!(
            iterate(&PyVal::Int(1)).unwrap_err().str(),
            "'int' object is not iterable"
        );
        assert_eq!(iterate(&PyVal::List(vec![PyVal::Int(1)])).unwrap().len(), 1);
    }
}
