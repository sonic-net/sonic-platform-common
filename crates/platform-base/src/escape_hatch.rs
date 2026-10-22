//! `sonic_platform_api/_escape_hatch.py`, over native objects.
//!
//! The bodies the generator cannot derive.  Each method here is the Python
//! method of the same name, followed by the bridge's read of what it returns,
//! so that a daemon sees the same rows and the same errors either way.

use std::cell::RefCell;
use std::sync::atomic::{AtomicBool, Ordering};

use platform_api::{
    AsicInfo, BmcResult, ChangeEventBatch, DeviceKey, EepromUpdate, PcieAerStat, PcieDevice,
    PlatformError, StorageDeviceInfo,
};

use crate::device_info;
use crate::facade::{
    read_asic_info, read_bmc_result, read_change_event_batch, read_pcie_aer_stat, read_pcie_device,
    read_storage_device_info, PyAsicInfo, PyBmcResult, PyChangeEvent, PyChangeEventBatch,
    PyPcieAerStat, PyPcieDevice, PyStorageDeviceInfo,
};
use crate::facade_rt::{self, call, err, ret_num};
use crate::io;
use crate::object::PyObject;
use crate::pcie::{PcieApi, PcieUtil};
use crate::py::{int_of_float, py_float, py_int, Exc, PyErr, PyResult, PyVal};
use crate::storage::StorageDevices;

/// `thermalctld:ThermalControlDaemon.POLICY_FILE`; the facade owns it once.
pub const POLICY_FILE: &str = "/usr/share/sonic/platform/thermal_policy.json";

/// The file `sensormond:SensorMonitorDaemon.__init__` reads, under the
/// platform directory.
pub const SENSORS_YAML: &str = "sensors.yaml";

/// The seven statuses `ChassisBase.get_change_event` documents, named.
const CHANGE_EVENT_KINDS: &[(&str, &str)] = &[
    ("0", "removed"),
    ("1", "inserted"),
    ("2", "i2c_stuck"),
    ("3", "bad_eeprom"),
    ("4", "unsupported_cable"),
    ("5", "high_temperature"),
    ("6", "bad_cable"),
];

/// `obj.name(...)` called directly, as Python code does outside `_call`: a
/// method that is not there is an `AttributeError`, not "no answer".
fn direct<F>(obj: &PyVal, name: &str, f: F) -> PyResult<PyVal>
where
    F: FnOnce(&dyn PyObject) -> PyResult<PyVal>,
{
    let attr_error = |class: &str| {
        PyErr::new(
            Exc::AttributeError,
            vec![PyVal::Str(format!(
                "'{class}' object has no attribute '{name}'"
            ))],
        )
    };
    match obj {
        PyVal::Obj(o) => match f(o.as_ref()) {
            Err(e) if e.exc == Exc::Missing => Err(attr_error(o.py_class())),
            other => other,
        },
        other => Err(attr_error(&other.type_name())),
    }
}

/// `getattr(obj, name, None)` then the call: `Ok(None)` when it is not there.
fn optional<F>(obj: &PyVal, f: F) -> PyResult<Option<PyVal>>
where
    F: FnOnce(&dyn PyObject) -> PyResult<PyVal>,
{
    match obj {
        PyVal::Obj(o) => match f(o.as_ref()) {
            Err(e) if e.exc == Exc::Missing => Ok(None),
            other => other.map(Some),
        },
        _ => Ok(None),
    }
}

/// `int(v)`.
fn py_int_of(v: &PyVal) -> PyResult<i128> {
    match v {
        PyVal::Int(i) => Ok(*i),
        PyVal::Bool(b) => Ok(i128::from(*b)),
        PyVal::Float(f) => int_of_float(*f),
        PyVal::Str(s) => py_int(s),
        other => Err(PyErr::type_error(format!(
            "int() argument must be a string, a bytes-like object or a real number, not '{}'",
            other.type_name()
        ))),
    }
}

/// `float(v)`.
fn py_float_of(v: &PyVal) -> PyResult<f64> {
    match v {
        PyVal::Float(f) => Ok(*f),
        PyVal::Int(i) => Ok(*i as f64),
        PyVal::Bool(b) => Ok(if *b { 1.0 } else { 0.0 }),
        PyVal::Str(s) => py_float(s),
        other => Err(PyErr::type_error(format!(
            "float() argument must be a string or a real number, not '{}'",
            other.type_name()
        ))),
    }
}

/// `v[i]`, raising what Python raises.
fn py_index(v: &PyVal, i: usize) -> PyResult<PyVal> {
    match v {
        PyVal::Tuple(items) | PyVal::List(items) => items
            .get(i)
            .cloned()
            .ok_or_else(|| PyErr::index_error(format!("{} index out of range", v.type_name()))),
        PyVal::Str(s) => s
            .chars()
            .nth(i)
            .map(|c| PyVal::Str(c.to_string()))
            .ok_or_else(|| PyErr::index_error("string index out of range")),
        PyVal::Bytes(b) => b
            .get(i)
            .map(|x| PyVal::Int(i128::from(*x)))
            .ok_or_else(|| PyErr::index_error("index out of range")),
        PyVal::Dict(d) => {
            let key = PyVal::Int(i as i128);
            d.iter()
                .find(|(k, _)| k.py_eq(&key))
                .map(|(_, v)| v.clone())
                .ok_or_else(|| PyErr::key_error(key))
        }
        other => Err(PyErr::type_error(format!(
            "'{}' object is not subscriptable",
            other.type_name()
        ))),
    }
}

/// `a, b = v`: exactly two items, `TypeError` or `ValueError` otherwise.
fn unpack2(v: &PyVal) -> PyResult<(PyVal, PyVal)> {
    let items = v.iter_items().ok_or_else(|| {
        PyErr::type_error(format!(
            "cannot unpack non-iterable {} object",
            v.type_name()
        ))
    })?;
    match <[PyVal; 2]>::try_from(items) {
        Ok([a, b]) => Ok((a, b)),
        Err(items) if items.len() < 2 => Err(PyErr::value_error(format!(
            "not enough values to unpack (expected 2, got {})",
            items.len()
        ))),
        Err(_) => Err(PyErr::value_error("too many values to unpack (expected 2)")),
    }
}

/// `None if v is None else str(v)`.
fn opt_str(v: &PyVal) -> PyVal {
    if v.is_none() {
        PyVal::None
    } else {
        PyVal::Str(v.py_str())
    }
}

/// `EscapeHatches`: per facade, as the Python one is per facade.
///
/// State behind `RefCell` because the generated walks borrow the facade
/// immutably while a provider here caches; a facade is used from one thread at
/// a time (`PlatformApi` is `Send`, not `Sync`).
#[derive(Default)]
pub struct EscapeHatches {
    manager: RefCell<PyVal>,
    loaded: RefCell<bool>,
    sensors_data: RefCell<Option<PyVal>>,
    eeprom: RefCell<PyVal>,
    /// `from sonic_platform.pcie import Pcie; Pcie(platform_path)`, when
    /// the vendor has one.
    pcie_factory: Option<PcieFactory>,
    pcie: RefCell<Option<std::sync::Arc<dyn PcieApi>>>,
    pcie_tried: RefCell<bool>,
    storage: RefCell<Option<StorageDevices>>,
    storage_tried: RefCell<bool>,
    /// What `notify_shutdown()` runs, when the vendor has something to abort.
    shutdown: Option<ShutdownHook>,
}

/// A vendor's `Pcie(platform_path)`.
pub type PcieFactory = fn(&str) -> PyResult<std::sync::Arc<dyn PcieApi>>;

/// What a vendor's Python package does in the SIGTERM handler it installs
/// while its chassis is built, besides chaining on: mlnx's sets the event its
/// readiness waits abort on (`utils.watch_shutdown_signals()`).  The bridge
/// keeps that handler for `notify_shutdown()` to run; a native vendor hands
/// its counterpart to [`EscapeHatches::on_shutdown`].  Process-wide, as the
/// handler is.
pub type ShutdownHook = fn();

/// `_shutdown_notified`: the hook runs once per process, whichever handle
/// asks first.
static SHUTDOWN_NOTIFIED: AtomicBool = AtomicBool::new(false);

impl EscapeHatches {
    pub fn new() -> Self {
        EscapeHatches::default()
    }

    /// The hatches for a vendor with its own `sonic_platform.pcie.Pcie`.
    pub fn with_pcie(factory: PcieFactory) -> Self {
        EscapeHatches {
            pcie_factory: Some(factory),
            ..EscapeHatches::default()
        }
    }

    /// The hatches over disks that did not come from `/sys/block`: what
    /// setting `_storage` does to the Python ones.
    pub fn with_storage(devices: StorageDevices) -> Self {
        EscapeHatches {
            storage: RefCell::new(Some(devices)),
            storage_tried: RefCell::new(true),
            ..EscapeHatches::default()
        }
    }

    /// These hatches, with `hook` as what `notify_shutdown()` runs.
    pub fn on_shutdown(mut self, hook: ShutdownHook) -> Self {
        self.shutdown = Some(hook);
        self
    }

    // -- thermal manager ---------------------------------------------------

    /// `_get()`: the manager, or None; `NotImplementedError` is None.
    fn manager(&self, chassis: &PyVal) -> PyResult<PyVal> {
        if self.manager.borrow().is_none() {
            match optional(chassis, |o| o.get_thermal_manager()) {
                Ok(None) => return Ok(PyVal::None),
                Err(e) if e.exc == Exc::NotImplementedError => return Ok(PyVal::None),
                Err(e) => return Err(e),
                Ok(Some(m)) => *self.manager.borrow_mut() = m,
            }
        }
        Ok(self.manager.borrow().clone())
    }

    /// `tm_initialize()`: here a `NotImplementedError` from
    /// `get_thermal_manager()` is let through, as thermalctld expects.
    pub fn tm_initialize(&self, chassis: &PyVal) -> Result<(), PlatformError> {
        (|| -> PyResult<()> {
            if self.manager.borrow().is_none() {
                if let Some(m) = optional(chassis, |o| o.get_thermal_manager())? {
                    *self.manager.borrow_mut() = m;
                }
            }
            let mgr = self.manager.borrow().clone();
            if mgr.is_none() {
                return Ok(());
            }
            direct(&mgr, "initialize", |o| o.initialize())?;
            direct(&mgr, "load", |o| o.load(POLICY_FILE))?;
            direct(&mgr, "init_thermal_algorithm", |o| {
                o.init_thermal_algorithm(chassis.clone())
            })?;
            *self.loaded.borrow_mut() = true;
            Ok(())
        })()
        .map_err(err)
    }

    /// `tm_run_policy()`: nothing unless loaded.
    pub fn tm_run_policy(&self, chassis: &PyVal) -> Result<(), PlatformError> {
        (|| -> PyResult<()> {
            let mgr = self.manager(chassis)?;
            if mgr.is_none() || !*self.loaded.borrow() {
                return Ok(());
            }
            direct(&mgr, "run_policy", |o| o.run_policy(chassis.clone()))?;
            Ok(())
        })()
        .map_err(err)
    }

    /// `tm_get_interval()`: seconds as a float, None without a manager.
    pub fn tm_get_interval(&self, chassis: &PyVal) -> Result<Option<f64>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let mgr = self.manager(chassis)?;
            if mgr.is_none() {
                return Ok(PyVal::None);
            }
            let interval = match direct(&mgr, "get_interval", |o| o.get_interval()) {
                Err(e) if e.exc == Exc::NotImplementedError => return Ok(PyVal::None),
                other => other?,
            };
            if interval.is_none() {
                return Ok(PyVal::None);
            }
            Ok(PyVal::Float(py_float_of(&interval)?))
        })()
        .map_err(err)?;
        ret_num(&v)
    }

    /// `tm_deinitialize()`: `stop()`, then `deinitialize()`.
    pub fn tm_deinitialize(&self, chassis: &PyVal) -> Result<(), PlatformError> {
        (|| -> PyResult<()> {
            let mgr = self.manager(chassis)?;
            if mgr.is_none() {
                return Ok(());
            }
            match direct(&mgr, "stop", |o| o.stop()) {
                Err(e) if e.exc == Exc::NotImplementedError => {}
                other => {
                    other?;
                }
            }
            direct(&mgr, "deinitialize", |o| o.deinitialize())?;
            *self.loaded.borrow_mut() = false;
            Ok(())
        })()
        .map_err(err)
    }

    /// `tm_stop()`: `stop()` alone, what thermalctld's signal handler does.
    pub fn tm_stop(&self, chassis: &PyVal) -> Result<(), PlatformError> {
        (|| -> PyResult<()> {
            let mgr = self.manager(chassis)?;
            if mgr.is_none() {
                return Ok(());
            }
            match direct(&mgr, "stop", |o| o.stop()) {
                Err(e) if e.exc == Exc::NotImplementedError => Ok(()),
                other => other.map(|_| ()),
            }
        })()
        .map_err(err)
    }

    // -- shutdown ----------------------------------------------------------

    /// `notify_shutdown()`: the vendor's hook, once per process, and never an
    /// error -- a hook that panics is reported and the shutdown goes on, as
    /// the Python one writes a handler's exception to stderr.
    pub fn notify_shutdown(&self, _chassis: &PyVal) -> Result<(), PlatformError> {
        if SHUTDOWN_NOTIFIED.swap(true, Ordering::SeqCst) {
            return Ok(());
        }
        if let Some(hook) = self.shutdown {
            if std::panic::catch_unwind(hook).is_err() {
                eprintln!("vendor shutdown hook failed");
            }
        }
        Ok(())
    }

    // -- system EEPROM -----------------------------------------------------

    /// `_eeprom_obj()`: cached; `NotImplementedError` is None.
    fn eeprom_obj(&self, chassis: &PyVal) -> PyResult<PyVal> {
        if self.eeprom.borrow().is_none() {
            match optional(chassis, |o| o.get_eeprom()) {
                Ok(None) => return Ok(PyVal::None),
                Err(e) if e.exc == Exc::NotImplementedError => return Ok(PyVal::None),
                Err(e) => return Err(e),
                Ok(Some(v)) => *self.eeprom.borrow_mut() = v,
            }
        }
        Ok(self.eeprom.borrow().clone())
    }

    /// `eeprom_update_db()`: `read_eeprom()` then `update_eeprom_db(data)`,
    /// saying which half failed.
    pub fn eeprom_update_db(&self, chassis: &PyVal) -> Result<EepromUpdate, PlatformError> {
        let swallow = |e: &PyErr| {
            matches!(
                e.exc,
                Exc::NotImplementedError | Exc::AttributeError | Exc::Missing
            )
        };
        (|| -> PyResult<EepromUpdate> {
            let eeprom = self.eeprom_obj(chassis)?;
            if eeprom.is_none() {
                return Ok(EepromUpdate::ReadFailed);
            }
            let data = match direct(&eeprom, "read_eeprom", |o| o.read_eeprom()) {
                Err(e) if swallow(&e) => return Ok(EepromUpdate::ReadFailed),
                other => other?,
            };
            if data.is_none() {
                return Ok(EepromUpdate::ReadFailed);
            }
            match direct(&eeprom, "update_eeprom_db", |o| o.update_eeprom_db(data)) {
                Err(e) if swallow(&e) => Ok(EepromUpdate::UpdateFailed),
                Ok(failed) if failed.truthy() => Ok(EepromUpdate::UpdateFailed),
                other => other.map(|_| EepromUpdate::Updated),
            }
        })()
        .map_err(err)
    }

    // -- sensors.yaml ------------------------------------------------------

    /// `_sensors_yaml()`: the platform's sensors.yaml, or `{}`.
    fn sensors_yaml(&self) -> PyResult<PyVal> {
        if let Some(d) = self.sensors_data.borrow().as_ref() {
            return Ok(d.clone());
        }
        let path = device_info::get_platform()
            .ok()
            .flatten()
            .map(|p| {
                if io::is_dir(device_info::CONTAINER_PLATFORM_PATH) {
                    device_info::CONTAINER_PLATFORM_PATH.to_string()
                } else {
                    io::join(device_info::HOST_DEVICE_PATH, &p)
                }
            })
            .map(|dir| io::join(&dir, SENSORS_YAML));
        // Python swallows every failure here, so a platform without the file
        // -- the common case -- has no sensors from it.  One *with* the file
        // needs `SensorFs`, which is not ported yet; that is said, not
        // swallowed.
        let data = match path {
            Some(p) if io::exists(&p) => {
                return Err(PyErr::not_ported(format!("{p} (sensors.yaml)")))
            }
            _ => PyVal::Dict(Vec::new()),
        };
        *self.sensors_data.borrow_mut() = Some(data.clone());
        Ok(data)
    }

    /// `voltage_sensors_from_yaml()`.
    pub fn voltage_sensors_from_yaml(&self) -> PyResult<PyVal> {
        self.sensors_from_yaml()
    }

    /// `current_sensors_from_yaml()`.
    pub fn current_sensors_from_yaml(&self) -> PyResult<PyVal> {
        self.sensors_from_yaml()
    }

    fn sensors_from_yaml(&self) -> PyResult<PyVal> {
        match self.sensors_yaml()? {
            PyVal::Dict(d) if d.is_empty() => Ok(PyVal::List(Vec::new())),
            _ => Err(PyErr::not_ported("SensorFs.factory")),
        }
    }

    // -- PCIe and storage --------------------------------------------------

    /// `_pcie_util()`: the vendor's `Pcie`, else the base `PcieUtil`, else
    /// None; tried once.  An exception that is not an `Exception` gets out,
    /// and leaves None behind.
    fn pcie_util(&self) -> PyResult<Option<std::sync::Arc<dyn PcieApi>>> {
        if *self.pcie_tried.borrow() {
            return Ok(self.pcie.borrow().clone());
        }
        *self.pcie_tried.borrow_mut() = true;
        let Ok((platform_path, _hwsku)) = device_info::get_paths_to_platform_and_hwsku_dirs()
        else {
            return Ok(None);
        };
        let made = match self.pcie_factory {
            Some(factory) => match factory(&platform_path) {
                Ok(p) => p,
                // `except Exception`, which a `SystemExit` gets past.
                Err(e) if crate::redfish_client::is_exception(&e) => {
                    std::sync::Arc::new(PcieUtil::new(&platform_path))
                }
                Err(e) => return Err(e),
            },
            None => std::sync::Arc::new(PcieUtil::new(&platform_path)),
        };
        *self.pcie.borrow_mut() = Some(made.clone());
        Ok(Some(made))
    }

    /// `get_pcie_devices()`: `get_pcie_check()`, with the yaml's hex strings
    /// parsed; an entry that does not parse is skipped.
    ///
    /// A platform without a pcie.yaml answers with `sys.exit()` -- two lines
    /// on stdout and a `SystemExit`, on every call.  It is the empty parts
    /// list it means, and the utility is dropped, as the Python hatch drops
    /// it, so the next call does not print the same two lines again.
    pub fn get_pcie_devices(&self, _chassis: &PyVal) -> Result<Vec<PcieDevice>, PlatformError> {
        let rows = (|| -> PyResult<Vec<PyPcieDevice>> {
            let Some(util) = self.pcie_util()? else {
                return Ok(Vec::new());
            };
            let answer = match util.get_pcie_check() {
                Err(e)
                    if matches!(
                        e.exc,
                        Exc::NotImplementedError | Exc::AttributeError | Exc::Missing
                    ) =>
                {
                    return Ok(Vec::new())
                }
                Err(e) if e.exc.name() == "SystemExit" => {
                    *self.pcie.borrow_mut() = None;
                    return Ok(Vec::new());
                }
                other => other?,
            };
            let mut rows = Vec::new();
            let items = if answer.truthy() {
                crate::pcie::iterate(&answer)?
            } else {
                Vec::new()
            };
            for item in items {
                let PyVal::Dict(_) = item else {
                    return Err(PyErr::missing(&item.type_name(), "get"));
                };
                let parsed = (|| -> PyResult<PyPcieDevice> {
                    let hex = |k: &str| -> PyResult<PyVal> {
                        let v = crate::pcie::item(&item, k)?;
                        crate::pcie::int_hex(&PyVal::Str(v.py_str())).map(PyVal::Int)
                    };
                    Ok(PyPcieDevice {
                        name: PyVal::Str(
                            crate::json::get(&item, "name").map_or_else(String::new, PyVal::py_str),
                        ),
                        bus: hex("bus")?,
                        dev: hex("dev")?,
                        r#fn: hex("fn")?,
                        present: PyVal::Bool(
                            crate::json::get(&item, "result")
                                .is_some_and(|r| r.py_eq(&PyVal::str("Passed"))),
                        ),
                    })
                })();
                match parsed {
                    Ok(r) => rows.push(r),
                    Err(e) if matches!(e.exc, Exc::KeyError | Exc::TypeError | Exc::ValueError) => {
                        continue
                    }
                    Err(e) => return Err(e),
                }
            }
            Ok(rows)
        })()
        .map_err(err)?;
        rows.iter().map(read_pcie_device).collect()
    }

    /// `get_pcie_aer_stats(bus, dev, func)`: flattened out of its three
    /// severities.
    pub fn get_pcie_aer_stats(
        &self,
        _chassis: &PyVal,
        bus: i64,
        dev: i64,
        func: i64,
    ) -> Result<Vec<PcieAerStat>, PlatformError> {
        let rows = (|| -> PyResult<Vec<PyPcieAerStat>> {
            let Some(util) = self.pcie_util()? else {
                return Ok(Vec::new());
            };
            let answer = match util.get_pcie_aer_stats(0, bus, dev, func) {
                Err(e)
                    if matches!(
                        e.exc,
                        Exc::NotImplementedError | Exc::AttributeError | Exc::Missing
                    ) =>
                {
                    return Ok(Vec::new())
                }
                other => other?,
            };
            // `(answer or {}).items()`, and the same for each severity's
            // fields: nothing is nothing, and anything else that is not a
            // dict is the `AttributeError` its `.items()` raises.
            let or_empty = |v: PyVal| {
                if v.truthy() {
                    v
                } else {
                    PyVal::Dict(Vec::new())
                }
            };
            let mut rows = Vec::new();
            for (severity, fields) in crate::py::ops::items(&or_empty(answer))? {
                for (field, value) in crate::py::ops::items(&or_empty(fields))? {
                    rows.push(PyPcieAerStat {
                        severity: PyVal::Str(severity.py_str()),
                        field: PyVal::Str(field.py_str()),
                        value: PyVal::Str(value.py_str()),
                    });
                }
            }
            Ok(rows)
        })()
        .map_err(err)?;
        rows.iter().map(read_pcie_aer_stat).collect()
    }

    /// `get_storage_devices()`.
    pub fn get_storage_devices(
        &self,
        _chassis: &PyVal,
    ) -> Result<Vec<StorageDeviceInfo>, PlatformError> {
        if !*self.storage_tried.borrow() {
            *self.storage_tried.borrow_mut() = true;
            // Any exception from the constructor is None.
            *self.storage.borrow_mut() = StorageDevices::new().ok();
        }
        let mut guard = self.storage.borrow_mut();
        let Some(devices) = guard.as_mut() else {
            return Ok(Vec::new());
        };
        // A counter the daemon does arithmetic on: the getter answered, and
        // whether its answer is a number is not a failure of the refresh.
        let count = |v: PyVal| -> PyResult<PyVal> {
            if matches!(v, PyVal::Bool(_)) {
                return Ok(PyVal::None);
            }
            match crate::storage::int_of(&v) {
                Ok(i) => Ok(PyVal::Int(i)),
                Err(e) if matches!(e.exc, Exc::TypeError | Exc::ValueError) => Ok(PyVal::None),
                Err(e) => Err(e),
            }
        };
        let text = |v: PyVal| PyVal::Str(v.py_str());
        let mut order: Vec<usize> = (0..devices.devices.len()).collect();
        order.sort_by(|a, b| devices.devices[*a].0.cmp(&devices.devices[*b].0));
        let mut rows = Vec::new();
        for i in order {
            let (name, obj) = &mut devices.devices[i];
            let mut row = PyStorageDeviceInfo {
                name: PyVal::Str(name.clone()),
                available: PyVal::Bool(obj.is_some()),
                model: PyVal::str("N/A"),
                serial: PyVal::str("N/A"),
                firmware: PyVal::str("N/A"),
                health: PyVal::str("N/A"),
                temperature: PyVal::str("N/A"),
                disk_io_reads: PyVal::str("N/A"),
                disk_io_writes: PyVal::str("N/A"),
                reserved_blocks: PyVal::str("N/A"),
                fs_io_reads: PyVal::None,
                fs_io_writes: PyVal::None,
                static_error: PyVal::None,
                error: PyVal::None,
            };
            let Some(obj) = obj.as_mut() else {
                rows.push(row);
                continue;
            };
            // stormond's two passes, each in a `try` of its own: model and
            // serial, then the refresh.
            match (|| -> PyResult<(PyVal, PyVal)> {
                let model = text(obj.get_model()?);
                Ok((model, text(obj.get_serial()?)))
            })() {
                Ok((model, serial)) => (row.model, row.serial) = (model, serial),
                Err(e) => row.static_error = PyVal::Str(e.str()),
            }
            let path = io::join(crate::storage::BLKDEV_BASE_PATH, name);
            match (|| -> PyResult<[PyVal; 8]> {
                obj.fetch_parse_info(&path)?;
                let firmware = text(obj.get_firmware()?);
                let health = text(obj.get_health()?);
                let temperature = text(obj.get_temperature()?);
                let fs_io_reads = count(obj.get_fs_io_reads()?)?;
                let fs_io_writes = count(obj.get_fs_io_writes()?)?;
                let disk_io_reads = text(obj.get_disk_io_reads()?);
                let disk_io_writes = text(obj.get_disk_io_writes()?);
                Ok([
                    firmware,
                    health,
                    temperature,
                    fs_io_reads,
                    fs_io_writes,
                    disk_io_reads,
                    disk_io_writes,
                    text(obj.get_reserved_blocks()?),
                ])
            })() {
                Ok([fw, health, temp, reads, writes, dreads, dwrites, reserved]) => {
                    row.firmware = fw;
                    row.health = health;
                    row.temperature = temp;
                    row.fs_io_reads = reads;
                    row.fs_io_writes = writes;
                    row.disk_io_reads = dreads;
                    row.disk_io_writes = dwrites;
                    row.reserved_blocks = reserved;
                }
                Err(e) => row.error = PyVal::Str(e.str()),
            }
            rows.push(row);
        }
        rows.iter().map(read_storage_device_info).collect()
    }

    // -- change events -----------------------------------------------------

    /// `get_change_event(timeout_ms)`: the two-level mapping, flattened.
    pub fn get_change_event(
        &self,
        chassis: &PyVal,
        timeout_ms: i64,
    ) -> Result<ChangeEventBatch, PlatformError> {
        let batch = (|| -> PyResult<PyChangeEventBatch> {
            let Some(answer) = optional(chassis, |o| o.get_change_event(i128::from(timeout_ms)))?
            else {
                return Err(PyErr::not_implemented_msg(
                    "ChassisBase.get_change_event is not implemented",
                ));
            };
            let (ok, mapping) = unpack2(&answer).map_err(|e| match e.exc {
                Exc::TypeError | Exc::ValueError => PyErr::not_implemented_msg(
                    "ChassisBase.get_change_event did not answer (bool, dict)",
                ),
                _ => e,
            })?;
            let mut events = Vec::new();
            if let PyVal::Dict(mapping) = mapping {
                for (device_type, changes) in mapping {
                    let PyVal::Dict(changes) = changes else {
                        continue;
                    };
                    for (device_id, status) in changes {
                        let status = status.py_str();
                        let kind = CHANGE_EVENT_KINDS
                            .iter()
                            .find(|(k, _)| *k == status)
                            .map_or(PyVal::None, |(_, v)| PyVal::str(*v));
                        events.push(PyChangeEvent {
                            device_type: PyVal::Str(device_type.py_str()),
                            device_id: PyVal::Str(device_id.py_str()),
                            status: PyVal::Str(status),
                            kind,
                        });
                    }
                }
            }
            Ok(PyChangeEventBatch {
                ok: PyVal::Bool(ok.truthy()),
                events,
            })
        })()
        .map_err(err)?;
        read_change_event_batch(&batch)
    }

    // -- asics -------------------------------------------------------------

    /// `get_asics()`: `ModuleBase.get_all_asics()` per module, flattened.
    pub fn get_asics(&self, chassis: &PyVal) -> Result<Vec<AsicInfo>, PlatformError> {
        let rows = (|| -> PyResult<Vec<PyAsicInfo>> {
            let mut rows = Vec::new();
            let modules = call(facade_rt::get(chassis, |o| o.get_all_modules()))?;
            let modules = if modules.truthy() {
                modules
            } else {
                PyVal::Tuple(Vec::new())
            };
            let items = modules.iter_items().ok_or_else(|| {
                PyErr::type_error(format!("'{}' object is not iterable", modules.type_name()))
            })?;
            for (index, module) in items.iter().enumerate() {
                let name = call(facade_rt::get(module, |o| o.get_name()))?;
                let name = if name.truthy() {
                    name
                } else {
                    PyVal::Str(format!("Module {}", index + 1))
                };
                let entries = call(facade_rt::get(module, |o| o.get_all_asics()))?;
                let entries = if entries.truthy() {
                    entries
                } else {
                    PyVal::Tuple(Vec::new())
                };
                let entries = entries.iter_items().ok_or_else(|| {
                    PyErr::type_error(format!("'{}' object is not iterable", entries.type_name()))
                })?;
                for entry in entries {
                    let lookup_err = |e: &PyErr| {
                        matches!(e.exc, Exc::TypeError | Exc::IndexError | Exc::KeyError)
                    };
                    let asic_id = match py_index(&entry, 0) {
                        Ok(v) => PyVal::Str(v.py_str()),
                        Err(e) if lookup_err(&e) => continue,
                        Err(e) => return Err(e),
                    };
                    let address = match py_index(&entry, 1) {
                        Ok(v) => PyVal::Str(v.py_str()),
                        Err(e) if lookup_err(&e) => PyVal::None,
                        Err(e) => return Err(e),
                    };
                    rows.push(PyAsicInfo {
                        parent_name: name.clone(),
                        asic_id,
                        pci_address: address,
                    });
                }
            }
            Ok(rows)
        })()
        .map_err(err)?;
        rows.iter().map(read_asic_info).collect()
    }

    // -- BMC commands ------------------------------------------------------

    /// `_bmc()`.
    fn bmc(&self, chassis: &PyVal) -> PyResult<PyVal> {
        let bmc = call(facade_rt::get(chassis, |o| o.get_bmc()))?;
        if bmc.is_none() {
            return Err(PyErr::not_implemented_msg(
                "ChassisBase.get_bmc is not implemented",
            ));
        }
        Ok(bmc)
    }

    /// `_bmc_call(method, *args)`: `(int(code), payload)`.
    fn bmc_call<F>(&self, chassis: &PyVal, method: &str, f: F) -> PyResult<(i128, PyVal)>
    where
        F: FnOnce(&dyn PyObject) -> PyResult<PyVal>,
    {
        let bmc = self.bmc(chassis)?;
        let Some(answer) = optional(&bmc, f)? else {
            return Err(PyErr::not_implemented_msg(format!(
                "BMCBase.{method} is not implemented"
            )));
        };
        let (code, payload) = unpack2(&answer).map_err(|e| match e.exc {
            Exc::TypeError | Exc::ValueError => PyErr::not_implemented_msg(format!(
                "BMCBase.{method} did not answer (code, payload)"
            )),
            _ => e,
        })?;
        Ok((py_int_of(&code)?, payload))
    }

    /// `_result(method, *args)`.
    fn result<F>(&self, chassis: &PyVal, method: &str, f: F) -> Result<BmcResult, PlatformError>
    where
        F: FnOnce(&dyn PyObject) -> PyResult<PyVal>,
    {
        let row = (|| -> PyResult<PyBmcResult> {
            let (code, payload) = self.bmc_call(chassis, method, f)?;
            Ok(PyBmcResult {
                code: PyVal::Int(code),
                message: opt_str(&payload),
                ..Default::default()
            })
        })()
        .map_err(err)?;
        read_bmc_result(&row)
    }

    /// `bmc_open_session()`: `(code, (message, (session_id, token)))`.
    pub fn bmc_open_session(&self, chassis: &PyVal) -> Result<BmcResult, PlatformError> {
        let row = (|| -> PyResult<PyBmcResult> {
            let (code, payload) = self.bmc_call(chassis, "open_session", |o| o.open_session())?;
            let (message, credentials) = match unpack2(&payload) {
                Ok((m, c)) => (m, c),
                Err(e) if matches!(e.exc, Exc::TypeError | Exc::ValueError) => {
                    (opt_str(&payload), PyVal::None)
                }
                Err(e) => return Err(e),
            };
            let (mut session_id, mut token) = (PyVal::None, PyVal::None);
            if credentials.truthy() {
                let pair = py_index(&credentials, 0)
                    .and_then(|a| py_index(&credentials, 1).map(|b| (a, b)));
                match pair {
                    Ok((a, b)) => {
                        session_id = PyVal::Str(a.py_str());
                        token = PyVal::Str(b.py_str());
                    }
                    Err(e) if matches!(e.exc, Exc::TypeError | Exc::IndexError | Exc::KeyError) => {
                    }
                    Err(e) => return Err(e),
                }
            }
            Ok(PyBmcResult {
                code: PyVal::Int(code),
                message: opt_str(&message),
                session_id,
                token,
                ..Default::default()
            })
        })()
        .map_err(err)?;
        read_bmc_result(&row)
    }

    pub fn bmc_close_session(
        &self,
        chassis: &PyVal,
        session_id: &str,
    ) -> Result<BmcResult, PlatformError> {
        self.result(chassis, "close_session", |o| o.close_session(session_id))
    }

    pub fn bmc_reset_root_password(&self, chassis: &PyVal) -> Result<BmcResult, PlatformError> {
        self.result(chassis, "reset_root_password", |o| o.reset_root_password())
    }

    pub fn bmc_reset(&self, chassis: &PyVal, graceful: bool) -> Result<BmcResult, PlatformError> {
        self.result(chassis, "request_bmc_reset", |o| {
            o.request_bmc_reset(graceful)
        })
    }

    /// `bmc_update_firmware(image_path)`: `(code, (message, components))`.
    pub fn bmc_update_firmware(
        &self,
        chassis: &PyVal,
        image_path: &str,
    ) -> Result<BmcResult, PlatformError> {
        let row = (|| -> PyResult<PyBmcResult> {
            let (code, payload) = self.bmc_call(chassis, "update_firmware", |o| {
                o.update_firmware(image_path)
            })?;
            let message = match unpack2(&payload) {
                Ok((m, _components)) => m,
                Err(e) if matches!(e.exc, Exc::TypeError | Exc::ValueError) => payload,
                Err(e) => return Err(e),
            };
            Ok(PyBmcResult {
                code: PyVal::Int(code),
                message: opt_str(&message),
                ..Default::default()
            })
        })()
        .map_err(err)?;
        read_bmc_result(&row)
    }

    /// `bmc_trigger_debug_log_dump()`: `(code, (task_id, message))`.
    pub fn bmc_trigger_debug_log_dump(&self, chassis: &PyVal) -> Result<BmcResult, PlatformError> {
        let row = (|| -> PyResult<PyBmcResult> {
            let (code, payload) = self.bmc_call(chassis, "trigger_bmc_debug_log_dump", |o| {
                o.trigger_bmc_debug_log_dump()
            })?;
            let (task_id, message) = match unpack2(&payload) {
                Ok(pair) => pair,
                Err(e) if matches!(e.exc, Exc::TypeError | Exc::ValueError) => {
                    (PyVal::None, opt_str(&payload))
                }
                Err(e) => return Err(e),
            };
            Ok(PyBmcResult {
                code: PyVal::Int(code),
                message: opt_str(&message),
                task_id: opt_str(&task_id),
                ..Default::default()
            })
        })()
        .map_err(err)?;
        read_bmc_result(&row)
    }

    pub fn bmc_get_debug_log_dump(
        &self,
        chassis: &PyVal,
        task_id: &str,
        filename: &str,
        path: &str,
    ) -> Result<BmcResult, PlatformError> {
        self.result(chassis, "get_bmc_debug_log_dump", |o| {
            o.get_bmc_debug_log_dump(task_id, filename, path)
        })
    }

    // -- from a name to a key -------------------------------------------------
    //
    // `_escape_hatch.py`'s three, line for line: each resolves a name the way
    // the Python consumer it replaces does, and answers the key the walk would
    // have published for that device.

    /// `get_module_key`: chassisd's `get_module_index(key)` (chassisd:323).
    pub fn get_module_key(
        &self,
        chassis: &PyVal,
        name: &str,
    ) -> Result<Option<DeviceKey>, PlatformError> {
        let index = match facade_rt::get(chassis, |o| o.get_module_index(name)) {
            Err(e) if e.exc == Exc::Missing => {
                return Err(err(PyErr::not_implemented_msg(
                    "ChassisBase.get_module_index is not implemented",
                )))
            }
            other => other.map_err(err)?,
        };
        // `isinstance(index, int) and not isinstance(index, bool) and index >= 0`
        Ok(match index {
            PyVal::Int(i) if i >= 0 => Some(DeviceKey::from(format!("modules[{i}]"))),
            _ => None,
        })
    }

    /// `get_component_key`: fwutil's `chassis component <name>`.
    pub fn get_component_key(
        &self,
        chassis: &PyVal,
        name: &str,
    ) -> Result<Option<DeviceKey>, PlatformError> {
        (|| -> PyResult<Option<DeviceKey>> {
            let comps = facade_rt::get(chassis, |o| o.get_all_components())?;
            let what = format!(
                "chassis component {}",
                PyVal::Str(name.to_string()).py_repr()
            );
            Ok(the_one(named(&comps, name)?, &what)?
                .map(|at| DeviceKey::from(format!("components[{at}]"))))
        })()
        .map_err(err)
    }

    /// `get_module_component_key`: fwutil's `module <module> component <name>`.
    pub fn get_module_component_key(
        &self,
        chassis: &PyVal,
        module: &str,
        name: &str,
    ) -> Result<Option<DeviceKey>, PlatformError> {
        (|| -> PyResult<Option<DeviceKey>> {
            if !facade_rt::get(chassis, |o| o.is_modular_chassis())?.truthy() {
                return Ok(None);
            }
            let modules = facade_rt::get(chassis, |o| o.get_all_modules())?;
            let mod_what = format!("module {}", PyVal::Str(module.to_string()).py_repr());
            let Some(at) = the_one(named(&modules, module)?, &mod_what)? else {
                return Ok(None);
            };
            let card = facade_rt::iter(if modules.truthy() {
                modules
            } else {
                PyVal::None
            })?
            .into_iter()
            .nth(at)
            .unwrap_or(PyVal::None);
            let comps = facade_rt::get(&card, |o| o.get_all_components())?;
            let what = format!(
                "component {} on module {}",
                PyVal::Str(name.to_string()).py_repr(),
                PyVal::Str(module.to_string()).py_repr()
            );
            Ok(the_one(named(&comps, name)?, &what)?
                .map(|comp| DeviceKey::from(format!("modules[{at}]/components[{comp}]"))))
        })()
        .map_err(err)
    }
}

/// `_named(devices, name)`: the positions of the devices whose `get_name()`
/// is `name`.  `devices or ()`: nothing for a falsy answer.
fn named(devices: &PyVal, name: &str) -> PyResult<Vec<usize>> {
    let want = PyVal::Str(name.to_string());
    let items = if devices.truthy() {
        facade_rt::iter(devices.clone())?
    } else {
        Vec::new()
    };
    let mut out = Vec::new();
    for (i, dev) in items.iter().enumerate() {
        let PyVal::Obj(o) = dev else {
            return Err(PyErr::missing(&dev.type_name(), "get_name"));
        };
        if o.get_name()?.py_eq(&want) {
            out.push(i);
        }
    }
    Ok(out)
}

/// `_the_one(positions, what)`: the only match, None for none, and a
/// `ValueError` for more than one.
fn the_one(positions: Vec<usize>, what: &str) -> PyResult<Option<usize>> {
    if positions.len() > 1 {
        return Err(PyErr::value_error(format!(
            "{what} is ambiguous: {} devices answer to it",
            positions.len()
        )));
    }
    Ok(positions.first().copied())
}

#[cfg(test)]
mod tests {
    use std::sync::{Arc, Mutex};

    use platform_api::PlatformApi;

    use super::*;
    use crate::object::{BaseClass, DynObject};
    use crate::testing::Root;
    use crate::BaseFacade;

    /// An object of `base` answering `answers` by method name, and as its
    /// base class otherwise: a Python class built with `type()`.
    fn obj(base: BaseClass, answers: Vec<(&'static str, PyResult<PyVal>)>) -> PyVal {
        PyVal::Obj(Arc::new(DynObject {
            class: "Scripted",
            base,
            handler: Box::new(move |_: &dyn PyObject, name: &str, _: &[PyVal]| {
                answers
                    .iter()
                    .find(|(n, _)| *n == name)
                    .map(|(_, r)| r.clone())
            }),
        }))
    }

    fn chassis(answers: Vec<(&'static str, PyResult<PyVal>)>) -> PyVal {
        obj(BaseClass::ChassisBase, answers)
    }

    fn s(v: &str) -> PyVal {
        PyVal::str(v)
    }

    fn backend(m: &str) -> PlatformError {
        PlatformError::Backend(m.to_string())
    }

    fn unsupported(m: &str) -> PlatformError {
        PlatformError::NotSupported(m.to_string())
    }

    #[test]
    fn a_thermal_manager_that_lacks_a_method_raises_attribute_error() {
        // `mgr.initialize()`, called directly as Python calls it.
        let c = chassis(vec![(
            "get_thermal_manager",
            Ok(obj(BaseClass::Object, vec![])),
        )]);
        assert_eq!(
            EscapeHatches::new().tm_initialize(&c),
            Err(backend("'Scripted' object has no attribute 'initialize'"))
        );
        let c = chassis(vec![("get_thermal_manager", Ok(s("tm")))]);
        assert_eq!(
            EscapeHatches::new().tm_initialize(&c),
            Err(backend("'str' object has no attribute 'initialize'"))
        );
    }

    #[test]
    fn tm_initialize_asks_for_the_manager_itself_and_runs_it() {
        let mgr = obj(
            BaseClass::ThermalManagerBase,
            vec![
                ("initialize", Ok(PyVal::None)),
                ("load", Ok(PyVal::None)),
                ("init_thermal_algorithm", Ok(PyVal::None)),
                ("run_policy", Ok(PyVal::None)),
                ("get_interval", Ok(PyVal::Int(5))),
                ("stop", Ok(PyVal::None)),
                ("deinitialize", Ok(PyVal::None)),
            ],
        );
        let h = EscapeHatches::new();
        let c = chassis(vec![("get_thermal_manager", Ok(mgr))]);
        assert_eq!(h.tm_initialize(&c), Ok(()));
        assert_eq!(h.tm_run_policy(&c), Ok(()));
        assert_eq!(h.tm_get_interval(&c), Ok(Some(5.0)));
        assert_eq!(h.tm_stop(&c), Ok(()));
        assert_eq!(h.tm_deinitialize(&c), Ok(()));
    }

    #[test]
    fn tm_stop_is_stop_alone_and_quiet_without_one() {
        let c = chassis(vec![(
            "get_thermal_manager",
            Ok(obj(
                BaseClass::ThermalManagerBase,
                vec![("stop", Err(PyErr::new(Exc::NotImplementedError, vec![])))],
            )),
        )]);
        assert_eq!(EscapeHatches::new().tm_stop(&c), Ok(()));
        let c = chassis(vec![(
            "get_thermal_manager",
            Ok(obj(
                BaseClass::ThermalManagerBase,
                vec![("stop", Err(PyErr::value_error("busy")))],
            )),
        )]);
        assert_eq!(EscapeHatches::new().tm_stop(&c), Err(backend("busy")));
        let c = obj(BaseClass::Object, vec![]);
        assert_eq!(EscapeHatches::new().tm_stop(&c), Ok(()));
    }

    #[test]
    fn a_chassis_without_a_thermal_manager_has_none_until_it_raises() {
        // No such method, or None answered: nothing to do.
        for c in [
            obj(BaseClass::Object, vec![]),
            chassis(vec![("get_thermal_manager", Ok(PyVal::None))]),
        ] {
            let h = EscapeHatches::new();
            assert_eq!(h.tm_initialize(&c), Ok(()));
            assert_eq!(h.tm_get_interval(&c), Ok(None));
            assert_eq!(h.tm_run_policy(&c), Ok(()));
            assert_eq!(h.tm_deinitialize(&c), Ok(()));
        }
        // Anything but NotImplementedError gets out of every call.
        let c = chassis(vec![(
            "get_thermal_manager",
            Err(PyErr::value_error("bad")),
        )]);
        assert_eq!(
            EscapeHatches::new().tm_get_interval(&c),
            Err(backend("bad"))
        );
    }

    #[test]
    fn the_eeprom_object_is_asked_for_once_and_its_absence_is_a_failed_read() {
        use std::sync::atomic::{AtomicUsize, Ordering};

        let h = EscapeHatches::new();
        assert_eq!(
            h.eeprom_update_db(&obj(BaseClass::Object, vec![])),
            Ok(EepromUpdate::ReadFailed)
        );
        // A vendor's KeyError is a backend failure, not "no such device".
        let c = chassis(vec![("get_eeprom", Err(PyErr::key_error(s("x"))))]);
        assert_eq!(
            EscapeHatches::new().eeprom_update_db(&c),
            Err(PlatformError::Backend("'x'".into()))
        );

        // Once: `get_eeprom()` opens a device on some platforms, and
        // syseepromd asks every minute.
        let asked = Arc::new(AtomicUsize::new(0));
        let eeprom = obj(
            BaseClass::TlvInfoDecoder,
            vec![
                ("read_eeprom", Ok(PyVal::Bytes(vec![1]))),
                ("update_eeprom_db", Ok(PyVal::Int(0))),
            ],
        );
        let counted = asked.clone();
        let c = PyVal::obj(DynObject {
            class: "Scripted",
            base: BaseClass::ChassisBase,
            handler: Box::new(move |_: &dyn PyObject, name: &str, _: &[PyVal]| {
                (name == "get_eeprom").then(|| {
                    counted.fetch_add(1, Ordering::SeqCst);
                    Ok(eeprom.clone())
                })
            }),
        });
        let h = EscapeHatches::new();
        assert_eq!(h.eeprom_update_db(&c), Ok(EepromUpdate::Updated));
        assert_eq!(h.eeprom_update_db(&c), Ok(EepromUpdate::Updated));
        assert_eq!(asked.load(Ordering::SeqCst), 1);
    }

    #[test]
    fn a_change_event_that_is_not_a_pair_is_not_implemented() {
        let h = EscapeHatches::new();
        assert_eq!(
            h.get_change_event(&obj(BaseClass::Object, vec![]), 10),
            Err(unsupported(
                "ChassisBase.get_change_event is not implemented"
            ))
        );
        for answer in [PyVal::Int(5), PyVal::List(vec![PyVal::Bool(true)])] {
            let c = chassis(vec![("get_change_event", Ok(answer))]);
            assert_eq!(
                h.get_change_event(&c, 10),
                Err(unsupported(
                    "ChassisBase.get_change_event did not answer (bool, dict)"
                ))
            );
        }
        // A str of two is a pair: ok='a', and a mapping without items.
        let c = chassis(vec![("get_change_event", Ok(s("ab")))]);
        assert_eq!(
            h.get_change_event(&c, 10),
            Ok(ChangeEventBatch {
                ok: true,
                events: vec![]
            })
        );
    }

    #[test]
    fn asic_entries_are_read_like_python_indexes_them() {
        let entries = PyVal::List(vec![
            PyVal::Dict(vec![(PyVal::Int(0), s("x"))]),
            s("ab"),
            PyVal::Int(7),
            PyVal::Tuple(vec![s("only")]),
        ]);
        let module = obj(
            BaseClass::ModuleBase,
            vec![
                ("get_name", Ok(PyVal::None)),
                ("get_all_asics", Ok(entries)),
            ],
        );
        let c = chassis(vec![("get_all_modules", Ok(PyVal::List(vec![module])))]);
        let row = |id: &str, addr: Option<&str>| AsicInfo {
            parent_name: "Module 1".into(),
            asic_id: id.into(),
            pci_address: addr.map(str::to_string),
        };
        assert_eq!(
            EscapeHatches::new().get_asics(&c),
            Ok(vec![row("x", None), row("a", Some("b")), row("only", None)])
        );
        // Modules, or a module's asics, that cannot be iterated raise, as the
        // `for` over them does in Python.
        let c = chassis(vec![("get_all_modules", Ok(PyVal::Int(5)))]);
        assert_eq!(
            EscapeHatches::new().get_asics(&c),
            Err(backend("'int' object is not iterable"))
        );
        let module = obj(
            BaseClass::ModuleBase,
            vec![("get_all_asics", Ok(PyVal::Float(1.5)))],
        );
        let c = chassis(vec![("get_all_modules", Ok(PyVal::Tuple(vec![module])))]);
        assert_eq!(
            EscapeHatches::new().get_asics(&c),
            Err(backend("'float' object is not iterable"))
        );
    }

    fn with_bmc(answers: Vec<(&'static str, PyResult<PyVal>)>) -> PyVal {
        chassis(vec![("get_bmc", Ok(obj(BaseClass::BMCBase, answers)))])
    }

    #[test]
    fn a_bmc_command_answers_code_and_payload_or_is_not_implemented() {
        let h = EscapeHatches::new();
        // A BMC with no such method, or one that is not an object at all.
        for bmc in [obj(BaseClass::Object, vec![]), s("bmc")] {
            let c = chassis(vec![("get_bmc", Ok(bmc))]);
            assert_eq!(
                h.bmc_open_session(&c),
                Err(unsupported("BMCBase.open_session is not implemented"))
            );
        }
        let c = with_bmc(vec![("reset_root_password", Ok(PyVal::Int(3)))]);
        assert_eq!(
            h.bmc_reset_root_password(&c),
            Err(unsupported(
                "BMCBase.reset_root_password did not answer (code, payload)"
            ))
        );
        // `int(code)`, of whatever the code is.
        let result = |code: i64, message: &str| BmcResult {
            code,
            message: Some(message.into()),
            ..Default::default()
        };
        let c = with_bmc(vec![(
            "request_bmc_reset",
            Ok(PyVal::Tuple(vec![PyVal::Bool(true), s("m")])),
        )]);
        assert_eq!(h.bmc_reset(&c, true), Ok(result(1, "m")));
        let c = with_bmc(vec![(
            "request_bmc_reset",
            Ok(PyVal::Tuple(vec![PyVal::Float(2.9), s("m")])),
        )]);
        assert_eq!(h.bmc_reset(&c, false), Ok(result(2, "m")));
        let c = with_bmc(vec![(
            "close_session",
            Ok(PyVal::Tuple(vec![PyVal::List(vec![]), s("m")])),
        )]);
        assert_eq!(
            h.bmc_close_session(&c, "sid"),
            Err(backend(
                "int() argument must be a string, a bytes-like object or a real number, not 'list'"
            ))
        );
    }

    #[test]
    fn open_session_credentials_are_indexed_or_left_out() {
        let open = |credentials: PyVal| {
            let c = with_bmc(vec![(
                "open_session",
                Ok(PyVal::Tuple(vec![
                    PyVal::Int(0),
                    PyVal::Tuple(vec![s("ok"), credentials]),
                ])),
            )]);
            let r = EscapeHatches::new().bmc_open_session(&c).unwrap();
            (r.session_id, r.token)
        };
        let both = (Some("sid".to_string()), Some("tok".to_string()));
        assert_eq!(
            open(PyVal::Dict(vec![
                (PyVal::Int(0), s("sid")),
                (PyVal::Int(1), s("tok"))
            ])),
            both
        );
        assert_eq!(
            open(PyVal::Dict(vec![(PyVal::Int(0), s("sid"))])),
            (None, None)
        );
        assert_eq!(open(PyVal::Tuple(vec![s("sid")])), (None, None));
        assert_eq!(open(PyVal::Int(5)), (None, None));
    }

    #[test]
    fn sensors_yaml_is_not_ported_where_a_platform_has_one() {
        let root = Root::new();
        // No platform at all: nothing from the yaml.
        assert_eq!(
            EscapeHatches::new().voltage_sensors_from_yaml().unwrap(),
            PyVal::List(vec![])
        );
        root.write("/host/machine.conf", "onie_platform=x86_64-sweep-r0\n");
        // The host's device directory, without the file.
        assert_eq!(
            EscapeHatches::new().current_sensors_from_yaml().unwrap(),
            PyVal::List(vec![])
        );
        root.write(
            "/usr/share/sonic/device/x86_64-sweep-r0/sensors.yaml",
            "voltage_sensors: []\n",
        );
        let e = EscapeHatches::new()
            .voltage_sensors_from_yaml()
            .unwrap_err();
        assert_eq!(
            e.str(),
            "not ported to the native platform API: /usr/share/sonic/device/x86_64-sweep-r0/sensors.yaml (sensors.yaml)"
        );
        // In pmon, the platform directory is mounted where the container sees it.
        root.write(
            "/usr/share/sonic/platform/sensors.yaml",
            "voltage_sensors: []\n",
        );
        let e = EscapeHatches::new()
            .current_sensors_from_yaml()
            .unwrap_err();
        assert_eq!(e.str(), "not ported to the native platform API: /usr/share/sonic/platform/sensors.yaml (sensors.yaml)");
    }

    /// No pcie.yaml: `PcieUtil` answers with `sys.exit()`.  That is no
    /// devices, and the utility is not asked again -- every call would
    /// otherwise print its two lines.
    #[test]
    fn a_pcie_utility_that_exits_is_no_devices_and_is_dropped() {
        use std::sync::atomic::{AtomicUsize, Ordering};
        static ASKED: AtomicUsize = AtomicUsize::new(0);
        struct Exits;
        impl PcieApi for Exits {
            fn get_pcie_check(&self) -> PyResult<PyVal> {
                ASKED.fetch_add(1, Ordering::SeqCst);
                Err(PyErr::other("SystemExit", ""))
            }
            fn get_pcie_aer_stats(&self, _d: i64, _b: i64, _v: i64, _f: i64) -> PyResult<PyVal> {
                unreachable!("not asked")
            }
        }
        fn exits(_: &str) -> PyResult<Arc<dyn PcieApi>> {
            Ok(Arc::new(Exits))
        }

        let _root = with_a_platform();
        let mut f = BaseFacade::new(chassis(vec![]), EscapeHatches::with_pcie(exits));
        assert_eq!(f.get_pcie_devices(), Ok(vec![]));
        assert_eq!(f.get_pcie_devices(), Ok(vec![]));
        assert_eq!(ASKED.load(Ordering::SeqCst), 1, "asked once, then dropped");
    }

    /// A platform directory and a hwsku, which is what the PCIe utility is
    /// made from.
    fn with_a_platform() -> Root {
        let root = Root::new();
        root.write("/host/machine.conf", "onie_platform=x86_64-sweep-r0\n");
        std::fs::create_dir_all(root.real(device_info::CONTAINER_PLATFORM_PATH)).unwrap();
        let redis = crate::testing::FakeRedis::get();
        redis.install(&root);
        redis.set(crate::testing::CONFIG_DB, "CONFIG_DB_INITIALIZED", "1");
        redis.hset(
            crate::testing::CONFIG_DB,
            "DEVICE_METADATA|localhost",
            &[("hwsku", "SKU")],
        );
        root
    }

    /// `(answer or {}).items()`, a severity's fields the same: nothing is no
    /// counters, and an answer that is not a dict raises its `AttributeError`
    /// rather than reading as none.
    #[test]
    fn aer_counters_are_read_as_python_reads_them() {
        static ANSWER: Mutex<Option<PyVal>> = Mutex::new(None);
        struct Answers;
        impl PcieApi for Answers {
            fn get_pcie_check(&self) -> PyResult<PyVal> {
                unreachable!("not asked")
            }
            fn get_pcie_aer_stats(&self, _d: i64, _b: i64, _v: i64, _f: i64) -> PyResult<PyVal> {
                Ok(ANSWER.lock().unwrap().clone().unwrap_or_default())
            }
        }
        fn answers(_: &str) -> PyResult<Arc<dyn PcieApi>> {
            Ok(Arc::new(Answers))
        }

        let _root = with_a_platform();
        let mut f = BaseFacade::new(chassis(vec![]), EscapeHatches::with_pcie(answers));
        let mut ask = |v: PyVal| {
            *ANSWER.lock().unwrap() = Some(v);
            f.get_pcie_aer_stats(1, 2, 3)
        };
        assert_eq!(ask(PyVal::None), Ok(vec![]));
        let none_fields = PyVal::Dict(vec![(PyVal::str("correctable"), PyVal::None)]);
        assert_eq!(ask(none_fields), Ok(vec![]));
        let one = PyVal::Dict(vec![(
            PyVal::str("fatal"),
            PyVal::Dict(vec![(PyVal::str("DLP"), PyVal::Int(2))]),
        )]);
        let rows = ask(one).unwrap();
        assert_eq!(
            (
                rows[0].severity.as_str(),
                rows[0].field.as_str(),
                rows[0].value.as_str()
            ),
            ("fatal", "DLP", "2")
        );
        let e = ask(PyVal::List(vec![PyVal::Int(1)])).unwrap_err();
        assert!(
            e.to_string()
                .contains("'list' object has no attribute 'items'"),
            "{e}"
        );
    }

    #[test]
    fn without_a_platform_directory_there_are_no_pcie_devices() {
        let _root = Root::new();
        fn never(_: &str) -> PyResult<Arc<dyn PcieApi>> {
            panic!("no platform directory: the factory is not reached");
        }
        let mut f = BaseFacade::new(chassis(vec![]), EscapeHatches::with_pcie(never));
        assert_eq!(f.get_pcie_devices(), Ok(vec![]));
        assert_eq!(f.get_pcie_aer_stats(0, 1, 2), Ok(vec![]));
    }

    #[test]
    fn storage_devices_are_every_disk_but_loop_and_boot_sorted_by_name() {
        let root = Root::new();
        std::fs::create_dir_all(root.real("/sys/block/loop0")).unwrap();
        std::fs::create_dir_all(root.real("/sys/block/mmcblk41boot0")).unwrap();
        std::fs::create_dir_all(root.real("/sys/block/sdq")).unwrap();
        std::fs::create_dir_all(root.real("/sys/block/mmcblk41/device")).unwrap();
        root.write("/sys/block/mmcblk42/device/name", "8GTF4R\n");
        root.write("/sys/block/mmcblk42/device/serial", "0x0123abcd\n");
        root.write("/sys/block/mmcblk42/device/fwrev", "0x0300000000000000\n");
        root.write("/sys/block/mmcblk42/device/life_time", "0x01 0x02\n");
        // Disk names no other test uses: psutil's wrap correction is per name
        // and process-wide.
        root.write(
            "/proc/diskstats",
            "179 8 mmcblk42 100 0 200 0 300 0 400 0 0 0 0\n",
        );
        let mut f = BaseFacade::new(chassis(vec![]), EscapeHatches::new());
        let na = || "N/A".to_string();
        let disk = |name: &str,
                    model: &str,
                    serial: &str,
                    firmware: &str,
                    health: &str,
                    io: Option<(i64, i64)>| StorageDeviceInfo {
            name: name.into(),
            available: true,
            model: model.into(),
            serial: serial.into(),
            firmware: firmware.into(),
            health: health.into(),
            temperature: na(),
            disk_io_reads: na(),
            disk_io_writes: na(),
            reserved_blocks: na(),
            fs_io_reads: io.map(|io| io.0),
            fs_io_writes: io.map(|io| io.1),
            static_error: None,
            // `str(NotImplementedError())`: stormond logs it, empty.
            error: io.is_none().then(String::new),
        };
        let want = vec![
            // Nothing in its device directory: `str(None)` for its model and
            // serial, and a health that raises NotImplementedError, which
            // ends stormond's refresh of it (stormond:339-393): none of it.
            disk("mmcblk41", "None", "None", "N/A", "N/A", None),
            disk(
                "mmcblk42",
                "8GTF4R",
                "0x0123abcd",
                "0x0300000000000000",
                "90.0",
                Some((100, 300)),
            ),
            // An sd disk on neither ATA, NVMe nor USB has no utility class.
            StorageDeviceInfo {
                name: "sdq".into(),
                model: na(),
                serial: na(),
                firmware: na(),
                health: na(),
                temperature: na(),
                disk_io_reads: na(),
                disk_io_writes: na(),
                reserved_blocks: na(),
                ..Default::default()
            },
        ];
        assert_eq!(f.get_storage_devices(), Ok(want.clone()));
        // Built once, read each time.
        assert_eq!(f.get_storage_devices(), Ok(want));
        assert!(matches!(f.chassis(), PyVal::Obj(_)));
    }

    #[test]
    fn a_reading_that_raises_costs_that_disk_its_refresh_and_not_the_call() {
        // `data.split()[1]` on a one-word life_time: IndexError, which
        // stormond catches per disk (stormond:339-393) and logs as `str(ex)`.
        let root = Root::new();
        root.write("/sys/block/mmcblk43/device/life_time", "0x05\n");
        let rows = EscapeHatches::new()
            .get_storage_devices(&PyVal::None)
            .unwrap();
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0].error.as_deref(), Some("list index out of range"));
        assert_eq!(
            (rows[0].static_error.as_deref(), rows[0].firmware.as_str()),
            (None, "N/A")
        );
    }

    #[test]
    fn without_sys_block_there_is_no_storage() {
        let _root = Root::new();
        assert_eq!(
            EscapeHatches::new().get_storage_devices(&PyVal::None),
            Ok(vec![])
        );
    }
}
