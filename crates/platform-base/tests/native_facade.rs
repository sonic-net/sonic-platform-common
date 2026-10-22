//! What the native facade does beyond reading rows.

use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};

use platform_api::{
    DeviceKey, FanDrawerInfoCols, FanInfoCols, Number, PlatformApi, PlatformError, ThermalInfoCols,
    ThermalKind,
};
use platform_base::escape_hatch::EscapeHatches;
use platform_base::object::DynObject;
use platform_base::{atexit, BaseClass, BaseFacade, PyErr, PyResult, PyVal};

/// `finalize()` is Python's interpreter exit: every `atexit` handler, the
/// last registered first, each once.  Its own test binary, as the handlers
/// are process-wide.
#[test]
fn finalize_runs_the_atexit_handlers_last_first_and_once() {
    let ran = Arc::new(Mutex::new(Vec::new()));
    for n in [1, 2] {
        let ran = ran.clone();
        atexit::register(move || ran.lock().unwrap().push(n));
    }
    let mut facade = BaseFacade::new(PyVal::None, EscapeHatches::new());
    facade.finalize();
    assert_eq!(*ran.lock().unwrap(), [2, 1]);
    facade.finalize();
    assert_eq!(*ran.lock().unwrap(), [2, 1]);
}

static SHUTDOWNS: AtomicUsize = AtomicUsize::new(0);

fn vendor_shutdown() {
    SHUTDOWNS.fetch_add(1, Ordering::SeqCst);
    panic!("a hook that fails");
}

/// `notify_shutdown()` runs the vendor's hook once per process, whichever
/// handle asks and however often, and a hook that fails does not fail the
/// shutdown.  The only test here that notifies: the once is process-wide.
#[test]
fn notify_shutdown_runs_the_vendors_hook_once_and_never_fails() {
    let mut first = BaseFacade::new(
        PyVal::None,
        EscapeHatches::new().on_shutdown(vendor_shutdown),
    );
    let mut second = BaseFacade::new(
        PyVal::None,
        EscapeHatches::new().on_shutdown(vendor_shutdown),
    );
    assert_eq!(SHUTDOWNS.load(Ordering::SeqCst), 0);
    assert_eq!(first.notify_shutdown(), Ok(()));
    assert_eq!(first.notify_shutdown(), Ok(()));
    std::thread::spawn(move || assert_eq!(second.notify_shutdown(), Ok(())))
        .join()
        .unwrap();
    assert_eq!(SHUTDOWNS.load(Ordering::SeqCst), 1);
}

/// A platform object answering `answers` and nothing else.
fn obj(base: BaseClass, answers: Vec<(&'static str, PyResult<PyVal>)>) -> PyVal {
    let answers: HashMap<&'static str, PyResult<PyVal>> = answers.into_iter().collect();
    PyVal::Obj(Arc::new(DynObject {
        class: "Scripted",
        base,
        handler: Box::new(move |_s, method, _args| answers.get(method).cloned()),
    }))
}

fn name(n: &str) -> PyResult<PyVal> {
    Ok(PyVal::str(n))
}

/// The facade's own semantics, natively; the differential test holds them
/// equal to Python's.  A virtual drawer named 'N/A' puts its fans under the
/// chassis; a thermal whose threshold read fails is still a row; a skipped
/// thermal reads only what Python reads for one that is not due; a PDB that
/// cannot say whether it is present still has its thermals published; a
/// PDB with no name is 'PDB 1', not 'PSU 1'.
#[test]
fn the_native_facade_isolates_a_failing_device_and_names_as_the_daemons_do() {
    let fan = obj(
        BaseClass::FanBase,
        vec![
            ("get_name", name("fan1")),
            ("get_presence", Ok(PyVal::Bool(true))),
        ],
    );
    let drawer = obj(
        BaseClass::FanDrawerBase,
        vec![
            ("get_name", name("N/A")),
            ("get_all_fans", Ok(PyVal::List(vec![fan]))),
        ],
    );
    let hot = obj(
        BaseClass::ThermalBase,
        vec![
            ("get_name", name("t1")),
            ("get_temperature", Ok(PyVal::Float(40.0))),
            ("get_high_threshold", Err(PyErr::os_error(5, None))),
            ("get_low_threshold", Ok(PyVal::Float(1.0))),
        ],
    );
    let cold = obj(
        BaseClass::ThermalBase,
        vec![
            ("get_name", name("t2")),
            ("get_temperature", Ok(PyVal::None)),
        ],
    );
    let pdb_thermal = obj(BaseClass::ThermalBase, vec![("get_name", name("pt"))]);
    let pdb = obj(
        BaseClass::PdbBase,
        vec![("get_all_thermals", Ok(PyVal::List(vec![pdb_thermal])))],
    );
    let chassis = obj(
        BaseClass::ChassisBase,
        vec![
            ("get_all_fan_drawers", Ok(PyVal::List(vec![drawer]))),
            ("get_all_thermals", Ok(PyVal::List(vec![hot, cold]))),
            ("get_all_pdbs", Ok(PyVal::List(vec![pdb]))),
        ],
    );
    let mut f = BaseFacade::new(chassis, EscapeHatches::new());

    let fans = f.get_fans(FanInfoCols::ALL, false).unwrap();
    assert_eq!(
        (fans[0].parent_name.as_str(), fans[0].drawer_name.as_str()),
        ("chassis 1", "N/A")
    );
    let drawers = f.get_fan_drawers(FanDrawerInfoCols::ALL).unwrap();
    assert_eq!(drawers[0].name, "N/A");

    let thermals = f.get_thermals(ThermalInfoCols::ALL, &[]).unwrap();
    let names: Vec<_> = thermals
        .iter()
        .map(|t| (t.name.as_str(), t.kind, t.key.as_str()))
        .collect();
    assert_eq!(
        names,
        [
            ("t1", ThermalKind::Chassis, "thermals[0]"),
            ("t2", ThermalKind::Chassis, "thermals[1]"),
            ("pt", ThermalKind::Pdb, "pdbs[0]/thermals[0]"),
        ]
    );
    let t1 = &thermals[0];
    assert_eq!(
        (t1.temperature, t1.high_threshold, t1.low_threshold),
        (Some(Number::Float(40.0)), None, None)
    );
    assert_eq!(t1.error.as_deref(), Some("[Errno 5] Input/output error"));
    assert_eq!(
        t1.error_repr.as_deref(),
        Some("OSError(5, 'Input/output error')")
    );
    // The getter that raised: the high limit, read before the low one in
    // thermalctld's order, which is why the low one is absent.
    assert_eq!(t1.error_column.as_deref(), Some("high_threshold"));
    assert_eq!(
        (thermals[1].error.as_deref(), thermals[1].low_threshold),
        (None, None)
    );

    let skip = [DeviceKey::from("thermals[0]")];
    let skipped = f.get_thermals(ThermalInfoCols::ALL, &skip).unwrap();
    assert_eq!(
        (skipped[0].temperature, skipped[0].error.as_deref()),
        (None, None)
    );
    assert_eq!(skipped[1].name, "t2");

    let psus = f.get_psus().unwrap();
    assert_eq!(psus[0].name, "PDB 1");

    // Only a key that leads nowhere is NotFound.
    assert!(matches!(
        f.set_fan_led(
            &DeviceKey::from("fan_drawers[1]/fans[0]"),
            platform_api::LedColor::Red
        ),
        Err(PlatformError::NotFound(_))
    ));
}

/// A PSU that has been pulled is asked what psud asks of any PSU, and not
/// for power good or a reading, which psud asks only `if presence:`
/// (psud:767, 779-789): a driver that tries the I/O on an empty slot would
/// spend its retries on every snapshot.
#[test]
fn an_absent_psu_is_not_asked_what_only_a_present_one_answers() {
    let asked = Arc::new(Mutex::new(Vec::new()));
    let log = asked.clone();
    let psu = PyVal::Obj(Arc::new(DynObject {
        class: "Pulled",
        base: BaseClass::PsuBase,
        handler: Box::new(move |_s, method, _args| {
            log.lock().unwrap().push(method.to_string());
            Some(match method {
                "get_presence" => Ok(PyVal::Bool(false)),
                "get_model" => name("M"),
                // ENXIO, what the I/O on an empty slot ends in.
                _ => Err(PyErr::os_error(6, None)),
            })
        }),
    }));
    let chassis = obj(
        BaseClass::ChassisBase,
        vec![("get_all_psus", Ok(PyVal::List(vec![psu])))],
    );
    let mut f = BaseFacade::new(chassis, EscapeHatches::new());

    let psus = f.get_psus().unwrap();
    let row = &psus[0];
    assert_eq!(
        (row.presence, row.power_good, row.voltage, row.temperature),
        (false, false, None, None)
    );
    assert_eq!(
        row.model.as_deref(),
        Some("M"),
        "what psud asks of any PSU, it asks"
    );
    let asked = asked.lock().unwrap();
    for reading in [
        "get_powergood_status",
        "get_voltage",
        "get_current",
        "get_power",
        "get_input_voltage",
        "get_input_current",
        "get_input_power",
        "get_temperature",
        "get_temperature_high_threshold",
        "get_voltage_high_threshold",
        "get_voltage_low_threshold",
        "get_maximum_supplied_power",
    ] {
        assert!(
            !asked.iter().any(|m| m == reading),
            "{reading} asked of a pulled PSU"
        );
    }
}

/// A sensor with no name is named as sensormond names it: by kind, and
/// numbered within its parent (sensormond:246, 394); a module's start again
/// at 1.  With no sensors.yaml there is nothing for the chassis' own to count
/// on from.
#[test]
fn a_nameless_sensor_is_named_by_kind_and_position() {
    let nameless = |base| obj(base, vec![("get_value", Ok(PyVal::Float(1.0)))]);
    let module = obj(
        BaseClass::ModuleBase,
        vec![
            ("get_name", name("LC1")),
            (
                "get_all_current_sensors",
                Ok(PyVal::List(vec![nameless(BaseClass::CurrentSensorBase)])),
            ),
        ],
    );
    let chassis = obj(
        BaseClass::ChassisBase,
        vec![
            (
                "get_all_voltage_sensors",
                Ok(PyVal::List(vec![
                    obj(BaseClass::VoltageSensorBase, vec![("get_name", name("v0"))]),
                    nameless(BaseClass::VoltageSensorBase),
                ])),
            ),
            ("is_modular_chassis", Ok(PyVal::Bool(true))),
            ("get_all_modules", Ok(PyVal::List(vec![module]))),
        ],
    );
    let mut f = BaseFacade::new(chassis, EscapeHatches::new());
    let names: Vec<_> = f
        .get_sensors()
        .unwrap()
        .into_iter()
        .map(|s| (s.name, s.key.to_string()))
        .collect();
    assert_eq!(
        names,
        [
            ("v0".to_string(), "voltage_sensors[0]".to_string()),
            (
                "chassis 1 voltage_sensor 2".to_string(),
                "voltage_sensors[1]".to_string()
            ),
            (
                "LC1 current_sensor 1".to_string(),
                "modules[0]/current_sensors[0]".to_string()
            ),
        ]
    );
}
