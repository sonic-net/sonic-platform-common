//! `ThermalManagerBase`'s method bodies.

use std::sync::Mutex;

use crate::json;
use crate::object::PyObject;
use crate::py::{int_of_float, py_int, PyErr, PyResult, PyVal};

/// The class attributes `load()` writes and the other methods read.
///
/// In Python they live on whichever class `cls` is, falling back to
/// `ThermalManagerBase`'s; a process has one thermal manager class, so one
/// set of them is the same thing.  `_policy_dict` and `_thermal_info_dict`
/// stay empty: an entry needs a condition, action or info type registered
/// through `@thermal_json_object`, and nothing native registers one -- so
/// `load()` raises exactly where Python would on any policy or info entry.
struct State {
    fan_speed_when_suspend: Option<i128>,
    run_thermal_algorithm_at_boot_up: Option<bool>,
    interval: i128,
    running: bool,
}

static STATE: Mutex<State> = Mutex::new(State {
    fan_speed_when_suspend: None,
    run_thermal_algorithm_at_boot_up: None,
    interval: 60,
    running: true,
});

fn with_state<T>(f: impl FnOnce(&mut State) -> T) -> PyResult<T> {
    STATE
        .lock()
        .map(|mut s| f(&mut s))
        .map_err(|_| PyErr::runtime_error("thermal manager state poisoned"))
}

fn exception(msg: String) -> PyErr {
    PyErr::other("Exception", msg)
}

/// `key in obj`, for what `json.load` can produce.
fn contains(obj: &PyVal, key: &str) -> PyResult<bool> {
    match obj {
        PyVal::Dict(items) => Ok(items
            .iter()
            .any(|(k, _)| matches!(k, PyVal::Str(s) if s == key))),
        PyVal::List(items) => Ok(items.iter().any(|v| matches!(v, PyVal::Str(s) if s == key))),
        PyVal::Str(s) => Ok(s.contains(key)),
        other => Err(PyErr::type_error(format!(
            "argument of type '{}' is not iterable",
            other.type_name()
        ))),
    }
}

/// `for x in obj`, for what `json.load` can produce.
fn iterate(obj: &PyVal) -> PyResult<Vec<PyVal>> {
    match obj {
        PyVal::Dict(items) => Ok(items.iter().map(|(k, _)| k.clone()).collect()),
        PyVal::List(items) => Ok(items.clone()),
        PyVal::Str(s) => Ok(s.chars().map(|c| PyVal::Str(c.to_string())).collect()),
        other => Err(PyErr::type_error(format!(
            "'{}' object is not iterable",
            other.type_name()
        ))),
    }
}

/// `ThermalJsonObject.get_type(json_obj)`, with nothing registered.
fn get_type(json_obj: &PyVal) -> PyResult<PyVal> {
    if contains(json_obj, "type")? {
        let type_str = json::index(json_obj, "type")?;
        return Err(exception(format!(
            "ThermalJsonObject type {} not found",
            type_str.py_str()
        )));
    }
    Err(exception(
        "Invalid policy file, type field must be presented".into(),
    ))
}

/// `ThermalPolicy().load_from_json(json_policy)`: every condition and action
/// needs a registered type, and a policy needs at least one of each.
fn load_policy_from_json(json_obj: &PyVal) -> PyResult<()> {
    if !contains(json_obj, "name")? {
        return Err(exception("name field not found in policy".into()));
    }
    json::index(json_obj, "name")?;
    for field in ["conditions", "actions"] {
        if contains(json_obj, field)? {
            if let Some(first) = iterate(json::index(json_obj, field)?)?.first() {
                get_type(first)?;
            }
        }
    }
    Err(exception(
        "A policy requires at least 1 action and 1 condition".into(),
    ))
}

/// `int(x)` on a JSON value.
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

/// `ThermalManagerBase.get_interval`.
#[allow(unused_variables)]
pub fn get_interval<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    with_state(|st| PyVal::Int(st.interval))
}

/// `ThermalManagerBase.init_thermal_algorithm`: on `run_at_boot_up: false`
/// with a suspend speed, every fan the chassis and its PSUs list is set to it.
#[allow(unused_variables)]
pub fn init_thermal_algorithm<S: PyObject + ?Sized>(s: &S, chassis: PyVal) -> PyResult<PyVal> {
    let (run, speed) = with_state(|st| {
        (
            st.run_thermal_algorithm_at_boot_up,
            st.fan_speed_when_suspend,
        )
    })?;
    // start_/stop_thermal_control_algorithm are no-ops nobody overrides.
    if run != Some(false) {
        return Ok(PyVal::None);
    }
    let Some(speed) = speed else {
        return Ok(PyVal::None);
    };
    let PyVal::Obj(c) = &chassis else {
        return Err(PyErr::missing(&chassis.type_name(), "get_all_fans"));
    };
    for fan in iterate(&c.get_all_fans()?)? {
        set_speed(&fan, speed)?;
    }
    for psu in iterate(&c.get_all_psus()?)? {
        let PyVal::Obj(p) = &psu else {
            return Err(PyErr::missing(&psu.type_name(), "get_all_fans"));
        };
        for fan in iterate(&p.get_all_fans()?)? {
            set_speed(&fan, speed)?;
        }
    }
    Ok(PyVal::None)
}

fn set_speed(fan: &PyVal, speed: i128) -> PyResult<()> {
    match fan {
        PyVal::Obj(f) => f.set_speed(speed).map(|_| ()),
        other => Err(PyErr::missing(&other.type_name(), "set_speed")),
    }
}

/// `ThermalManagerBase.load(policy_file_name)`.
#[allow(unused_variables)]
pub fn load<S: PyObject + ?Sized>(s: &S, policy_file_name: &str) -> PyResult<PyVal> {
    let json_obj = json::load(policy_file_name)?;
    if contains(&json_obj, "policies")? {
        for json_policy in iterate(json::index(&json_obj, "policies")?)? {
            // _load_policy: the name first, then the policy itself.
            if !contains(&json_policy, "name")? {
                return Err(exception("name not found in policy".into()));
            }
            json::index(&json_policy, "name")?;
            load_policy_from_json(&json_policy)?;
        }
    }
    if contains(&json_obj, "info_types")? {
        if let Some(first) = iterate(json::index(&json_obj, "info_types")?)?.first() {
            get_type(first)?;
        }
    }
    if contains(&json_obj, "thermal_control_algorithm")? {
        let config = json::index(&json_obj, "thermal_control_algorithm")?;
        if contains(config, "run_at_boot_up")? {
            let v = match json::index(config, "run_at_boot_up")? {
                PyVal::Str(s) => s.to_lowercase() == "true",
                other => return Err(PyErr::missing(&other.type_name(), "lower")),
            };
            with_state(|st| st.run_thermal_algorithm_at_boot_up = Some(v))?;
        }
        if contains(config, "fan_speed_when_suspend")? {
            let v = py_int_of(json::index(config, "fan_speed_when_suspend")?)?;
            with_state(|st| st.fan_speed_when_suspend = Some(v))?;
        }
    }
    if contains(&json_obj, "interval")? {
        let v = py_int_of(json::index(&json_obj, "interval")?)?;
        with_state(|st| st.interval = v)?;
    }
    Ok(PyVal::None)
}

/// `ThermalManagerBase.run_policy`: nothing to run without a policy, and no
/// policy can be loaded (see `State`).
#[allow(unused_variables)]
pub fn run_policy<S: PyObject + ?Sized>(s: &S, chassis: PyVal) -> PyResult<PyVal> {
    Ok(PyVal::None)
}

/// `ThermalManagerBase.stop`.
#[allow(unused_variables)]
pub fn stop<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
    with_state(|st| st.running = false)?;
    Ok(PyVal::None)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::object::{BaseClass, DynObject};
    use crate::testing::Root;
    use std::sync::Arc;

    fn err<T>(r: PyResult<T>) -> (String, String) {
        match r {
            Ok(_) => panic!("an error expected"),
            Err(e) => (e.exc.name().to_string(), e.str()),
        }
    }

    /// An object of `base` whose `method` answers `value`.
    fn obj(base: BaseClass, method: &'static str, value: PyVal) -> PyVal {
        PyVal::Obj(Arc::new(DynObject {
            class: "Obj",
            base,
            handler: Box::new(move |_, m, _| (m == method).then(|| Ok(value.clone()))),
        }))
    }

    /// A fan whose `set_speed` calls land in `speeds`.
    fn fan(speeds: &Arc<Mutex<Vec<String>>>) -> PyVal {
        let speeds = speeds.clone();
        PyVal::Obj(Arc::new(DynObject {
            class: "Fan",
            base: BaseClass::FanBase,
            handler: Box::new(move |_, m, args| {
                (m == "set_speed").then(|| {
                    speeds.lock().unwrap().push(args[0].py_repr());
                    Ok(PyVal::Bool(true))
                })
            }),
        }))
    }

    #[test]
    fn a_policy_file_loads_as_python_loads_it_and_suspends_the_fans() {
        let root = Root::new();
        let tm = DynObject {
            class: "ThermalManager",
            base: BaseClass::ThermalManagerBase,
            handler: Box::new(|_, _, _| None),
        };
        let path = "/usr/share/sonic/platform/thermal_policy.json";
        assert_eq!(err(load(&tm, path)).0, "FileNotFoundError");
        let load_json = |json: &str| {
            root.write(path, json);
            load(&tm, path)
        };
        let exception = |msg: &str| ("Exception".to_string(), msg.to_string());
        assert_eq!(
            err(load_json(r#"{"policies": [{"conditions": []}]}"#)),
            exception("name not found in policy")
        );
        assert_eq!(
            err(load_json(
                r#"{"policies": [{"name": "p", "conditions": [{"type": "fan.any.absence"}]}]}"#
            )),
            exception("ThermalJsonObject type fan.any.absence not found")
        );
        assert_eq!(
            err(load_json(
                r#"{"policies": [{"name": "p", "actions": [{"speed": "100"}]}]}"#
            )),
            exception("Invalid policy file, type field must be presented")
        );
        assert_eq!(
            err(load_json(
                r#"{"policies": [{"name": "p", "conditions": []}]}"#
            )),
            exception("A policy requires at least 1 action and 1 condition")
        );
        assert_eq!(
            err(load_json(r#"{"policies": "n"}"#)),
            exception("name not found in policy")
        );
        assert_eq!(
            err(load_json(r#"{"policies": 5}"#)),
            ("TypeError".into(), "'int' object is not iterable".into())
        );
        assert_eq!(
            err(load_json(r#"{"info_types": [{"type": "fan_info"}]}"#)),
            exception("ThermalJsonObject type fan_info not found")
        );
        assert_eq!(
            err(load_json(r#"{"info_types": [5]}"#)),
            (
                "TypeError".into(),
                "argument of type 'int' is not iterable".into()
            )
        );
        assert_eq!(
            err(load_json(
                r#"{"thermal_control_algorithm": {"run_at_boot_up": 1}}"#
            )),
            (
                "AttributeError".into(),
                "'int' object has no attribute 'lower'".into()
            )
        );
        assert_eq!(
            err(load_json(
                r#"{"thermal_control_algorithm": {"fan_speed_when_suspend": "x"}}"#
            ))
            .0,
            "ValueError"
        );
        assert_eq!(
            err(load_json(r#"{"interval": [1]}"#)).1,
            "int() argument must be a string, a bytes-like object or a real number, not 'list'"
        );
        for (interval, want) in [("2.5", 2), ("true", 1), (r#""30""#, 30)] {
            load_json(&format!(r#"{{"interval": {interval}, "info_types": []}}"#)).unwrap();
            assert_eq!(get_interval(&tm).unwrap(), PyVal::Int(want));
        }

        // run_at_boot_up false: the suspend speed, to every fan.
        let speeds = Arc::default();
        let psu = obj(
            BaseClass::PsuBase,
            "get_all_fans",
            PyVal::List(vec![fan(&speeds)]),
        );
        let chassis = DynObject {
            class: "Chassis",
            base: BaseClass::ChassisBase,
            handler: {
                let (fans, psus) = (
                    PyVal::List(vec![fan(&speeds), fan(&speeds)]),
                    PyVal::List(vec![psu]),
                );
                Box::new(move |_, m, _| match m {
                    "get_all_fans" => Some(Ok(fans.clone())),
                    "get_all_psus" => Some(Ok(psus.clone())),
                    _ => None,
                })
            },
        };
        let chassis = PyVal::Obj(Arc::new(chassis));
        load_json(r#"{"thermal_control_algorithm": {"run_at_boot_up": "False", "fan_speed_when_suspend": "60"}}"#).unwrap();
        assert_eq!(
            init_thermal_algorithm(&tm, chassis.clone()).unwrap(),
            PyVal::None
        );
        assert_eq!(*speeds.lock().unwrap(), ["60", "60", "60"]);
        // A speed past a C long loads, and reaches the fans as it is.
        load_json(r#"{"thermal_control_algorithm": {"run_at_boot_up": "False", "fan_speed_when_suspend": "99999999999999999999"}}"#).unwrap();
        speeds.lock().unwrap().clear();
        init_thermal_algorithm(&tm, chassis.clone()).unwrap();
        assert_eq!(*speeds.lock().unwrap(), ["99999999999999999999"; 3]);
        assert_eq!(
            err(init_thermal_algorithm(&tm, PyVal::None)),
            (
                "AttributeError".into(),
                "'NoneType' object has no attribute 'get_all_fans'".into()
            )
        );
        let odd = |fans: PyVal, psus: PyVal| {
            let c = DynObject {
                class: "Chassis",
                base: BaseClass::ChassisBase,
                handler: Box::new(move |_, m, _| match m {
                    "get_all_fans" => Some(Ok(fans.clone())),
                    "get_all_psus" => Some(Ok(psus.clone())),
                    _ => None,
                }),
            };
            err(init_thermal_algorithm(&tm, PyVal::Obj(Arc::new(c)))).1
        };
        assert_eq!(
            odd(PyVal::List(vec![PyVal::Int(1)]), PyVal::List(vec![])),
            "'int' object has no attribute 'set_speed'"
        );
        assert_eq!(
            odd(PyVal::List(vec![]), PyVal::List(vec![PyVal::Int(1)])),
            "'int' object has no attribute 'get_all_fans'"
        );
        // run_at_boot_up true: the fans are left alone.
        load_json(r#"{"thermal_control_algorithm": {"run_at_boot_up": "true"}}"#).unwrap();
        speeds.lock().unwrap().clear();
        init_thermal_algorithm(&tm, chassis).unwrap();
        assert!(speeds.lock().unwrap().is_empty());
        assert_eq!(run_policy(&tm, PyVal::None).unwrap(), PyVal::None);
        assert_eq!(stop(&tm).unwrap(), PyVal::None);
        // The class attributes, as ThermalManagerBase starts them.
        with_state(|st| {
            *st = State {
                fan_speed_when_suspend: None,
                run_thermal_algorithm_at_boot_up: None,
                interval: 60,
                running: true,
            }
        })
        .unwrap();
        assert_eq!(
            init_thermal_algorithm(&tm, PyVal::None).unwrap(),
            PyVal::None
        );
    }
}
