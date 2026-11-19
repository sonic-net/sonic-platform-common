//! `ModuleBase`'s method bodies: module state transitions in STATE_DB, the
//! graceful-shutdown handshake with the gNOI shutdown daemon, and the PCI
//! and sensord handling around a module's power changes.
//!
//! Every step calls back through the object, as `self.` does in Python, so
//! a vendor's overrides (`get_name`, `set_admin_state`, `pci_detach`, ...)
//! are the ones that run.  Failures are written to stderr in Python's words.

use std::io::Write;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use crate::db::Db;
use crate::io;
use crate::json;
use crate::object::PyObject;
use crate::py::{py_int, PyErr, PyResult, PyVal};

const PCI_OPERATION_LOCK_FILE_PATH: &str = "/var/lock/{}_pci.lock";
const SENSORD_OPERATION_LOCK_FILE_PATH: &str = "/var/lock/sensord.lock";
const TRANSITION_OPERATION_LOCK_FILE_PATH: &str = "/var/lock/{}_transition.lock";
const PCIE_DETACH_INFO_TABLE: &str = "PCIE_DETACH_INFO";
const PCIE_OPERATION_DETACHING: &str = "detaching";
const PCIE_OPERATION_ATTACHING: &str = "attaching";

const TRANSITION_TIMEOUT_DEFAULTS: [(&str, i128); 5] = [
    ("startup", 300),
    ("shutdown", 180),
    ("reboot", 240),
    ("halt_services", 60),
    ("recovery", 600),
];

fn stderr(msg: &str) {
    let _ = std::io::stderr().write_all(msg.as_bytes());
}

fn now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

/// `self.is_host`, as ModuleBase's constructor decides it.
fn is_host() -> bool {
    !io::exists("/.dockerenv")
}

/// `get_state_db()`: `daemon_base.db_connect("STATE_DB")`, once.  Python
/// keeps one per module object; one per process answers the same.
fn state_db() -> PyResult<Arc<Db>> {
    static DB: Mutex<Option<Arc<Db>>> = Mutex::new(None);
    let mut slot = DB
        .lock()
        .map_err(|_| PyErr::runtime_error("STATE_DB lock poisoned"))?;
    if let Some(db) = slot.as_ref() {
        return Ok(db.clone());
    }
    let db = Arc::new(Db::connect("STATE_DB")?);
    *slot = Some(db.clone());
    Ok(db)
}

/// `with open(path, 'w') as f: fcntl.flock(f, LOCK_EX)`: held until drop.
struct FileLock(std::fs::File);

impl FileLock {
    fn take(path: &str) -> PyResult<FileLock> {
        use std::os::fd::AsRawFd;
        let f =
            std::fs::File::create(io::real(path)).map_err(|e| PyErr::from_io(&e, Some(path)))?;
        // SAFETY: the descriptor is the open file's, alive for the call.
        if unsafe { libc::flock(f.as_raw_fd(), libc::LOCK_EX) } != 0 {
            return Err(PyErr::from_io(&std::io::Error::last_os_error(), None));
        }
        Ok(FileLock(f))
    }
}

impl Drop for FileLock {
    fn drop(&mut self) {
        use std::os::fd::AsRawFd;
        // SAFETY: as above.
        unsafe { libc::flock(self.0.as_raw_fd(), libc::LOCK_UN) };
    }
}

fn name_of<S: PyObject + ?Sized>(s: &S) -> PyResult<String> {
    Ok(s.get_name()?.py_str())
}

fn transition_lock<S: PyObject + ?Sized>(s: &S) -> PyResult<FileLock> {
    FileLock::take(&TRANSITION_OPERATION_LOCK_FILE_PATH.replace("{}", &name_of(s)?))
}

/// `_load_transition_timeouts()`: platform.json's, else the defaults; read
/// once per process -- a class attribute -- even when it fails part way.
/// Asking for the platform comes before the `try`: a machine.conf that will
/// not read raises, and nothing is cached.
fn load_transition_timeouts() -> PyResult<Vec<(&'static str, i128)>> {
    static CACHE: Mutex<Option<Vec<(&'static str, i128)>>> = Mutex::new(None);
    let Ok(mut cache) = CACHE.lock() else {
        return Ok(TRANSITION_TIMEOUT_DEFAULTS.to_vec());
    };
    if let Some(c) = cache.as_ref() {
        return Ok(c.clone());
    }
    let mut timeouts = TRANSITION_TIMEOUT_DEFAULTS.to_vec();
    let path = if is_host() {
        format!(
            "/usr/share/sonic/device/{}/platform.json",
            crate::device_info::get_platform()?.unwrap_or_else(|| "None".into())
        )
    } else {
        "/usr/share/sonic/platform/platform.json".to_string()
    };
    let r = (|| -> PyResult<()> {
        if !io::exists(&path) {
            return Ok(());
        }
        let data = json::load(&path)?;
        for (key, field, extra) in [
            ("startup", "dpu_startup_timeout", 0),
            ("shutdown", "dpu_shutdown_timeout", 0),
            ("reboot", "dpu_reboot_timeout", 0),
            ("halt_services", "dpu_halt_services_timeout", 10),
        ] {
            let current = timeouts
                .iter()
                .find(|(k, _)| *k == key)
                .map_or(0, |(_, v)| *v);
            let v = match json::get(&data, field) {
                Some(v) => crate::storage::int_of(v)?,
                None => current,
            };
            if let Some(e) = timeouts.iter_mut().find(|(k, _)| *k == key) {
                e.1 = v + extra;
            }
        }
        Ok(())
    })();
    if let Err(e) = r {
        stderr(&format!(
            "Error loading transition timeouts from {path}: {}\n",
            e.str()
        ));
    }
    *cache = Some(timeouts.clone());
    Ok(timeouts)
}

fn timeout_of(kind: &str) -> PyResult<i128> {
    Ok(load_transition_timeouts()?
        .iter()
        .find(|(k, _)| *k == kind)
        .map_or(0, |(_, v)| *v))
}

fn module_key(name: &str) -> String {
    format!("CHASSIS_MODULE_TABLE|{name}")
}

/// `ModuleBase.get_module_state_transition(module_name)`: the flag, cleared
/// first if it has outlived its transition's timeout.
pub fn get_module_state_transition<S: PyObject + ?Sized>(
    s: &S,
    module_name: PyVal,
) -> PyResult<PyVal> {
    let PyVal::Str(name) = &module_name else {
        return Err(PyErr::missing(&module_name.type_name(), "upper"));
    };
    let key = module_key(&name.to_uppercase());
    let db = state_db()?;
    let _lock = transition_lock(s)?;
    let r = (|| -> PyResult<bool> {
        let flag = db.hget(&key, "transition_in_progress")?;
        if flag.as_deref() == Some("True") {
            let start = db.hget(&key, "transition_start_time")?;
            let kind = db.hget(&key, "transition_type")?;
            if let (Some(start), Some(kind)) = (start, kind) {
                let start = py_int(&start)?;
                if now() as i128 - start > timeout_of(&kind)? {
                    clear_transition_fields(&db, name);
                    return Ok(false);
                }
            }
        }
        Ok(flag.as_deref() == Some("True"))
    })();
    Ok(PyVal::Bool(r.unwrap_or(false)))
}

/// `_clear_transition_fields(module_name)`, under a lock the caller holds.
fn clear_transition_fields(db: &Db, module_name: &str) -> bool {
    let name = module_name.to_uppercase();
    let key = module_key(&name);
    let r = (|| -> PyResult<()> {
        db.hdel(&key, &["transition_in_progress"])?;
        db.hdel(&key, &["transition_type"])?;
        db.hdel(&key, &["transition_start_time"])?;
        Ok(())
    })();
    match r {
        Ok(()) => true,
        Err(e) => {
            stderr(&format!(
                "Error clearing transition flag for module {name}: {}\n",
                e.str()
            ));
            false
        }
    }
}

/// `ModuleBase.clear_module_state_transition(module_name)`.
pub fn clear_module_state_transition<S: PyObject + ?Sized>(
    s: &S,
    module_name: PyVal,
) -> PyResult<PyVal> {
    let _lock = transition_lock(s)?;
    let PyVal::Str(name) = &module_name else {
        return Err(PyErr::missing(&module_name.type_name(), "upper"));
    };
    let db = state_db()?;
    Ok(PyVal::Bool(clear_transition_fields(&db, name)))
}

/// `ModuleBase.set_module_state_transition(module_name, transition_type)`:
/// set unless one is in progress and not yet timed out.
pub fn set_module_state_transition<S: PyObject + ?Sized>(
    s: &S,
    module_name: PyVal,
    transition_type: &str,
) -> PyResult<PyVal> {
    let kind = transition_type.to_lowercase();
    if !TRANSITION_TIMEOUT_DEFAULTS.iter().any(|(k, _)| *k == kind) {
        stderr(&format!("Invalid transition type: {kind}\n"));
        return Ok(PyVal::Bool(false));
    }
    let PyVal::Str(name) = &module_name else {
        return Err(PyErr::missing(&module_name.type_name(), "upper"));
    };
    let name = name.to_uppercase();
    let key = module_key(&name);
    let db = state_db()?;
    let _lock = transition_lock(s)?;
    let r = (|| -> PyResult<bool> {
        let set = |t: i128| -> PyResult<()> {
            db.hset(&key, &[("transition_in_progress", "True")])?;
            db.hset(&key, &[("transition_type", kind.as_str())])?;
            db.hset(&key, &[("transition_start_time", &t.to_string())])?;
            Ok(())
        };
        if db.hget(&key, "transition_in_progress")?.is_none() {
            set(now() as i128)?;
            return Ok(true);
        }
        let Some(start) = db.hget(&key, "transition_start_time")? else {
            stderr(&format!(
                "Missing start time for transition flag on module: {name}\n"
            ));
            return Ok(false);
        };
        let start = py_int(&start)?;
        let current = now() as i128;
        if current - start > timeout_of(&kind)? {
            set(current)?;
            return Ok(true);
        }
        stderr(&format!(
            "Transition already in progress for module: {name}\n"
        ));
        Ok(false)
    })();
    Ok(PyVal::Bool(r.unwrap_or_else(|e| {
        stderr(&format!(
            "Error setting transition flag for module {name}: {}\n",
            e.str()
        ));
        false
    })))
}

fn gnoi_halt_in_progress<S: PyObject + ?Sized>(s: &S) -> PyResult<bool> {
    let key = module_key(&name_of(s)?);
    let db = state_db()?;
    let _lock = transition_lock(s)?;
    Ok(db
        .hget(&key, "gnoi_halt_in_progress")
        .map(|v| v.as_deref() == Some("True"))
        .unwrap_or(false))
}

fn set_gnoi_halt_in_progress<S: PyObject + ?Sized>(s: &S) -> PyResult<bool> {
    let key = module_key(&name_of(s)?);
    let db = state_db()?;
    let _lock = transition_lock(s)?;
    Ok(db.hset(&key, &[("gnoi_halt_in_progress", "True")]).is_ok())
}

/// `ModuleBase.clear_module_gnoi_halt_in_progress`.
pub fn clear_module_gnoi_halt_in_progress<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    let key = module_key(&name_of(s)?);
    let db = state_db()?;
    let _lock = transition_lock(s)?;
    Ok(PyVal::Bool(
        db.hdel(&key, &["gnoi_halt_in_progress"]).is_ok(),
    ))
}

/// `_graceful_shutdown_handler()`: ask the gNOI daemon to halt the module's
/// services and wait for it to clear the flag, at most the halt timeout.
fn graceful_shutdown_handler<S: PyObject + ?Sized>(s: &S) -> PyResult<bool> {
    let name = name_of(s)?;
    let halt_timeout = timeout_of("halt_services")?;
    let end = now() + halt_timeout as f64;
    if !set_gnoi_halt_in_progress(s)? {
        stderr(&format!(
            "Failed to set gnoi_halt_in_progress flag for module: {name}\n"
        ));
        return Ok(false);
    }
    while now() <= end {
        if !gnoi_halt_in_progress(s)? {
            return Ok(true);
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    if now() >= end {
        clear_module_gnoi_halt_in_progress(s)?;
        stderr(&format!(
            "Shutdown timeout reached for module: {name}. Proceeding with shutdown.\n"
        ));
        return Ok(true);
    }
    Ok(false)
}

/// `ModuleBase.set_admin_state_gracefully(up)`: `up` as the caller passed it
/// -- chassisd's 1 or 0 -- and `set_admin_state` given True or False, as the
/// base class gives it.
pub fn set_admin_state_gracefully<S: PyObject + ?Sized>(s: &S, up: PyVal) -> PyResult<PyVal> {
    let name = s.get_name()?;
    if up.truthy() {
        if !s
            .set_module_state_transition(name.clone(), "startup")?
            .truthy()
        {
            stderr("Failed to set module state transition for admin state UP\n");
            return Ok(PyVal::Bool(false));
        }
        let status = s.set_admin_state(PyVal::Bool(true))?;
        if !s.module_post_startup()?.truthy() {
            stderr("module_post_startup() failed\n");
        }
        if !s.clear_module_state_transition(name.clone())?.truthy() {
            stderr("Failed to clear module state transition for admin state UP\n");
        }
        return Ok(status);
    }
    if !s
        .set_module_state_transition(name.clone(), "shutdown")?
        .truthy()
    {
        stderr("Failed to set module state transition for admin state DOWN\n");
        return Ok(PyVal::Bool(false));
    }
    if !graceful_shutdown_handler(s)? {
        stderr(&format!(
            "Graceful shutdown handler failed or timed out for module: {}\n",
            name.py_str()
        ));
    }
    if !s.module_pre_shutdown()?.truthy() {
        stderr("module_pre_shutdown() failed\n");
    }
    let status = s.set_admin_state(PyVal::Bool(false))?;
    if !s.clear_module_state_transition(name)?.truthy() {
        stderr("Failed to clear module state transition for admin state DOWN\n");
    }
    Ok(status)
}

/// `pci_entry_state_db(pcie_string, operation)`.
fn pci_entry_state_db(pcie: &str, operation: &str) {
    let r = (|| -> PyResult<()> {
        let db = state_db()?;
        let key = format!("{PCIE_DETACH_INFO_TABLE}|{pcie}");
        if operation == PCIE_OPERATION_ATTACHING {
            db.del(&key)?;
            return Ok(());
        }
        db.hset(&key, &[("bus_info", pcie)])?;
        db.hset(&key, &[("dpu_state", operation)])?;
        Ok(())
    })();
    if let Err(e) = r {
        stderr(&format!(
            "Failed to write pcie bus info to state database: {}\n",
            e.str()
        ));
    }
}

fn bus_list(v: &PyVal) -> PyResult<Vec<String>> {
    Ok(crate::pcie::iterate(v)?.iter().map(PyVal::py_str).collect())
}

/// `handle_pci_removal()`.
fn handle_pci_removal<S: PyObject + ?Sized>(s: &S) -> bool {
    let r = (|| -> PyResult<bool> {
        let buses = bus_list(&s.get_pci_bus_info()?)?;
        let _lock = FileLock::take(&PCI_OPERATION_LOCK_FILE_PATH.replace("{}", &name_of(s)?))?;
        for bus in &buses {
            pci_entry_state_db(bus, PCIE_OPERATION_DETACHING);
        }
        Ok(s.pci_detach()?.truthy())
    })();
    r.unwrap_or_else(|e| {
        stderr(&format!("Failed to handle PCI removal: {}\n", e.str()));
        false
    })
}

/// `handle_pci_rescan()`.
fn handle_pci_rescan<S: PyObject + ?Sized>(s: &S) -> bool {
    let r = (|| -> PyResult<bool> {
        let buses = bus_list(&s.get_pci_bus_info()?)?;
        let _lock = FileLock::take(&PCI_OPERATION_LOCK_FILE_PATH.replace("{}", &name_of(s)?))?;
        let rv = s.pci_reattach()?.truthy();
        for bus in &buses {
            pci_entry_state_db(bus, PCIE_OPERATION_ATTACHING);
        }
        Ok(rv)
    })();
    r.unwrap_or_else(|e| {
        stderr(&format!("Failed to handle PCI rescan: {}\n", e.str()));
        false
    })
}

/// `subprocess.call(argv, stdout=DEVNULL)`: the exit code, or the
/// exception of a command that cannot start.
fn call(argv: &[String]) -> PyResult<i32> {
    let st = Command::new(&argv[0])
        .args(&argv[1..])
        .stdout(Stdio::null())
        .status()
        .map_err(|e| PyErr::from_io(&e, Some(&argv[0])))?;
    use std::os::unix::process::ExitStatusExt;
    Ok(st.code().or_else(|| st.signal().map(|s| -s)).unwrap_or(-1))
}

fn in_pmon(cmd: &[&str]) -> Vec<String> {
    let mut v: Vec<String> = Vec::new();
    if is_host() {
        v.extend(["docker", "exec", "pmon"].map(String::from));
    }
    v.extend(cmd.iter().map(|s| s.to_string()));
    v
}

/// `handle_sensor_removal()`: the module's sensors.d ignore file put in
/// place, and sensord restarted, when the platform ships one.
fn handle_sensor_removal<S: PyObject + ?Sized>(s: &S) -> bool {
    let r = (|| -> PyResult<bool> {
        let name = name_of(s)?;
        let source = format!(
            "/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_{name}.conf"
        );
        let target = format!("/etc/sensors.d/ignore_sensors_{name}.conf");
        if call(&in_pmon(&["test", "-f", &source]))? != 0 {
            return Ok(true);
        }
        call(&in_pmon(&["cp", &source, &target]))?;
        let _lock = FileLock::take(SENSORD_OPERATION_LOCK_FILE_PATH)?;
        call(&in_pmon(&["service", "sensord", "restart"]))?;
        Ok(true)
    })();
    r.unwrap_or_else(|e| {
        stderr(&format!("Failed to handle sensor removal: {}\n", e.str()));
        false
    })
}

/// `handle_sensor_addition()`: the ignore file removed, sensord restarted.
fn handle_sensor_addition<S: PyObject + ?Sized>(s: &S) -> bool {
    let r = (|| -> PyResult<bool> {
        let name = name_of(s)?;
        let target = format!("/etc/sensors.d/ignore_sensors_{name}.conf");
        if call(&in_pmon(&["test", "-f", &target]))? != 0 {
            return Ok(true);
        }
        call(&in_pmon(&["rm", &target]))?;
        let _lock = FileLock::take(SENSORD_OPERATION_LOCK_FILE_PATH)?;
        call(&in_pmon(&["service", "sensord", "restart"]))?;
        Ok(true)
    })();
    r.unwrap_or_else(|e| {
        stderr(&format!("Failed to handle sensor addition: {}\n", e.str()));
        false
    })
}

/// `ModuleBase.module_pre_shutdown`: sensors first, then PCI.
pub fn module_pre_shutdown<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    let sensor = handle_sensor_removal(s);
    let pci = handle_pci_removal(s);
    Ok(PyVal::Bool(pci && sensor))
}

/// `ModuleBase.module_post_startup`: PCI first, then sensors.
pub fn module_post_startup<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    let pci = handle_pci_rescan(s);
    let sensor = handle_sensor_addition(s);
    Ok(PyVal::Bool(pci && sensor))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::object::{BaseClass, DynObject};
    use crate::testing::{FakeRedis, Root, STATE_DB};

    type Calls = Arc<Mutex<Vec<String>>>;

    /// A module named `name` whose vendor methods answer `answers`; every
    /// other is ModuleBase's.  The calls it gets are kept in `calls`.
    fn module(name: &'static str, answers: Vec<(&'static str, PyVal)>, calls: &Calls) -> DynObject {
        let calls = calls.clone();
        DynObject {
            class: "DpuModule",
            base: BaseClass::ModuleBase,
            handler: Box::new(move |_, m, _| {
                calls.lock().unwrap().push(m.to_string());
                if m == "get_name" {
                    return Some(Ok(PyVal::str(name)));
                }
                answers
                    .iter()
                    .find(|(k, _)| *k == m)
                    .map(|(_, v)| Ok(v.clone()))
            }),
        }
    }

    fn fields(key: &str) -> Vec<String> {
        FakeRedis::get()
            .hgetall(STATE_DB, key)
            .into_iter()
            .map(|(f, v)| format!("{f}={v}"))
            .collect()
    }

    fn vendor_calls(calls: &Calls) -> Vec<String> {
        let vendor = [
            "set_admin_state",
            "pci_detach",
            "pci_reattach",
            "module_pre_shutdown",
            "module_post_startup",
        ];
        calls
            .lock()
            .unwrap()
            .drain(..)
            .filter(|c| vendor.contains(&c.as_str()))
            .collect()
    }

    /// The gNOI shutdown daemon: clears `name`'s halt flag once it is set.
    fn gnoi_daemon(name: &'static str) -> std::thread::JoinHandle<bool> {
        std::thread::spawn(move || {
            let key = module_key(name);
            for _ in 0..250 {
                if fields(&key).contains(&"gnoi_halt_in_progress=True".to_string()) {
                    FakeRedis::get().hdel(STATE_DB, &key, "gnoi_halt_in_progress");
                    return true;
                }
                std::thread::sleep(Duration::from_millis(20));
            }
            false
        })
    }

    #[test]
    fn module_transitions_and_admin_state_changes_follow_module_base() {
        let root = Root::new();
        let redis = FakeRedis::get();
        redis.install(&root);
        root.write("/.dockerenv", "");
        root.write(
            "/usr/share/sonic/platform/platform.json",
            r#"{"dpu_startup_timeout": 5, "dpu_shutdown_timeout": 7, "dpu_halt_services_timeout": -9}"#,
        );
        let calls: Calls = Arc::default();
        let dpu = module("DPU0", vec![], &calls);
        let key = module_key("DPU0");
        // No lock directory: the lock file cannot be made.
        assert_eq!(
            dpu.get_module_state_transition(PyVal::str("dpu0"))
                .map_err(|e| e.exc.name()),
            Err("FileNotFoundError")
        );
        std::fs::create_dir_all(root.real("/var/lock")).unwrap();

        assert_eq!(
            dpu.set_module_state_transition(PyVal::str("dpu0"), "Startup")
                .unwrap(),
            PyVal::Bool(true)
        );
        let f = fields(&key);
        assert_eq!(
            f[..2],
            [
                "transition_in_progress=True".to_string(),
                "transition_type=startup".to_string()
            ]
        );
        assert!(f[2].starts_with("transition_start_time="));
        assert_eq!(
            dpu.get_module_state_transition(PyVal::str("dpu0")).unwrap(),
            PyVal::Bool(true)
        );
        // One in progress, and not timed out.
        assert_eq!(
            dpu.set_module_state_transition(PyVal::str("dpu0"), "shutdown")
                .unwrap(),
            PyVal::Bool(false)
        );
        assert_eq!(
            dpu.set_module_state_transition(PyVal::str("dpu0"), "bogus")
                .unwrap(),
            PyVal::Bool(false)
        );
        // Timed out: cleared on reading, replaced on setting.
        redis.hset(STATE_DB, &key, &[("transition_start_time", "0")]);
        assert_eq!(
            dpu.get_module_state_transition(PyVal::str("DPU0")).unwrap(),
            PyVal::Bool(false)
        );
        assert!(fields(&key).is_empty());
        redis.hset(
            STATE_DB,
            &key,
            &[
                ("transition_in_progress", "True"),
                ("transition_type", "reboot"),
                ("transition_start_time", "0"),
            ],
        );
        assert_eq!(
            dpu.set_module_state_transition(PyVal::str("dpu0"), "reboot")
                .unwrap(),
            PyVal::Bool(true)
        );
        assert_eq!(
            dpu.clear_module_state_transition(PyVal::str("dpu0"))
                .unwrap(),
            PyVal::Bool(true)
        );
        assert!(fields(&key).is_empty());
        // A flag without a start time, or with one that is not a number.
        redis.hset(STATE_DB, &key, &[("transition_in_progress", "True")]);
        assert_eq!(
            dpu.set_module_state_transition(PyVal::str("dpu0"), "startup")
                .unwrap(),
            PyVal::Bool(false)
        );
        redis.hset(
            STATE_DB,
            &key,
            &[
                ("transition_type", "startup"),
                ("transition_start_time", "soon"),
            ],
        );
        assert_eq!(
            dpu.set_module_state_transition(PyVal::str("dpu0"), "startup")
                .unwrap(),
            PyVal::Bool(false)
        );
        assert_eq!(
            dpu.get_module_state_transition(PyVal::str("dpu0")).unwrap(),
            PyVal::Bool(false)
        );
        assert_eq!(
            dpu.get_module_state_transition(PyVal::Int(0))
                .map_err(|e| e.str()),
            Err("'int' object has no attribute 'upper'".into())
        );
        // A transition already under way stops an admin change.
        assert_eq!(
            dpu.set_admin_state_gracefully(PyVal::Bool(true)).unwrap(),
            PyVal::Bool(false)
        );
        assert_eq!(
            dpu.set_admin_state_gracefully(PyVal::Bool(false)).unwrap(),
            PyVal::Bool(false)
        );
        assert_eq!(
            dpu.clear_module_state_transition(PyVal::str("dpu0"))
                .unwrap(),
            PyVal::Bool(true)
        );
        assert_eq!(
            dpu.clear_module_gnoi_halt_in_progress().unwrap(),
            PyVal::Bool(true)
        );

        // Up: admin state, then PCI rescan and sensors, then the flag cleared.
        let buses = PyVal::List(vec![PyVal::str("0000:08:00.0"), PyVal::str("0000:09:00.0")]);
        let answers = vec![
            ("set_admin_state", PyVal::Bool(true)),
            ("get_pci_bus_info", buses.clone()),
            ("pci_reattach", PyVal::Bool(true)),
            ("pci_detach", PyVal::Bool(true)),
        ];
        let dpu1 = module("DPU1", answers.clone(), &calls);
        redis.hset(
            STATE_DB,
            "PCIE_DETACH_INFO|0000:08:00.0",
            &[("bus_info", "0000:08:00.0")],
        );
        assert_eq!(
            dpu1.set_admin_state_gracefully(PyVal::Bool(true)).unwrap(),
            PyVal::Bool(true)
        );
        assert_eq!(
            vendor_calls(&calls),
            ["set_admin_state", "module_post_startup", "pci_reattach"]
        );
        assert!(!redis.exists(STATE_DB, "PCIE_DETACH_INFO|0000:08:00.0"));
        assert!(fields(&module_key("DPU1")).is_empty());

        // Down: the gNOI daemon halts services, then sensors and PCI, then power.
        let daemon = gnoi_daemon("DPU1");
        assert_eq!(
            dpu1.set_admin_state_gracefully(PyVal::Bool(false)).unwrap(),
            PyVal::Bool(true)
        );
        assert!(daemon.join().unwrap());
        assert_eq!(
            vendor_calls(&calls),
            ["module_pre_shutdown", "pci_detach", "set_admin_state"]
        );
        assert_eq!(
            fields("PCIE_DETACH_INFO|0000:09:00.0"),
            ["bus_info=0000:09:00.0", "dpu_state=detaching"]
        );
        assert!(fields(&module_key("DPU1")).is_empty());
        // Nobody clears the flag: the halt timeout ends the wait, if it is short.
        if timeout_of("halt_services").unwrap() <= 2 {
            assert_eq!(
                dpu1.set_admin_state_gracefully(PyVal::Bool(false)).unwrap(),
                PyVal::Bool(true)
            );
            assert!(fields(&module_key("DPU1")).is_empty());
        }

        // A vendor that says no along the way: each failure is reported, and
        // the admin state is still what set_admin_state answers.
        let mut failing = answers;
        failing.retain(|(k, _)| !["get_pci_bus_info", "set_admin_state"].contains(k));
        failing.extend([
            ("module_post_startup", PyVal::Bool(false)),
            ("clear_module_state_transition", PyVal::Bool(false)),
            ("set_admin_state", PyVal::Bool(false)),
        ]);
        let dpu2 = module("DPU2", failing, &calls);
        assert_eq!(
            dpu2.set_admin_state_gracefully(PyVal::Bool(true)).unwrap(),
            PyVal::Bool(false)
        );
        redis.hdel(STATE_DB, &module_key("DPU2"), "transition_in_progress");
        let daemon = gnoi_daemon("DPU2");
        assert_eq!(
            dpu2.set_admin_state_gracefully(PyVal::Bool(false)).unwrap(),
            PyVal::Bool(false)
        );
        assert!(daemon.join().unwrap());
        // No PCI bus info: post startup and pre shutdown both fail.
        assert_eq!(dpu2.module_pre_shutdown().unwrap(), PyVal::Bool(false));
        assert_eq!(
            dpu2.get_pci_bus_info().map_err(|e| e.exc.name()),
            Err("NotImplementedError")
        );
        calls.lock().unwrap().clear();

        // A database that fails: every write is reported and answered False.
        let broken = module(
            "BROKEN",
            vec![
                ("set_module_state_transition", PyVal::Bool(true)),
                ("clear_module_state_transition", PyVal::Bool(true)),
                ("set_admin_state", PyVal::Bool(true)),
                (
                    "get_pci_bus_info",
                    PyVal::List(vec![PyVal::str("BROKEN:00.0")]),
                ),
                ("pci_detach", PyVal::Bool(true)),
            ],
            &calls,
        );
        assert_eq!(
            broken
                .set_admin_state_gracefully(PyVal::Bool(false))
                .unwrap(),
            PyVal::Bool(true)
        );
        assert_eq!(
            clear_module_state_transition(&broken, PyVal::str("broken")).unwrap(),
            PyVal::Bool(false)
        );
        assert_eq!(
            set_module_state_transition(&broken, PyVal::str("broken"), "startup").unwrap(),
            PyVal::Bool(false)
        );
        assert_eq!(
            broken.clear_module_gnoi_halt_in_progress().unwrap(),
            PyVal::Bool(false)
        );

        // On the host, the sensor commands run in pmon.
        assert_eq!(in_pmon(&["test", "-f", "x"]), ["test", "-f", "x"]);
        std::fs::remove_file(root.real("/.dockerenv")).unwrap();
        assert_eq!(in_pmon(&["rm", "x"]), ["docker", "exec", "pmon", "rm", "x"]);
        assert_eq!(
            call(&["/nonexistent/tool".into()]).map_err(|e| e.exc.name()),
            Err("FileNotFoundError")
        );
    }
}
