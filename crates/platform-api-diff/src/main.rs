//! Run one call plan against one platform API implementation.
//!
//! `platform-api-diff --impl pyo3|native PLAN.json` opens the platform as
//! the plan says and makes its calls, printing one line per step: what was
//! called and the `Debug` text of what came back.  Run once per
//! implementation, in separate processes over the same platform state, and
//! the two outputs are equal exactly when the implementations answered the
//! same.  What the calls did besides answer -- syslog, files, stdout --
//! is the caller's to capture around each run.
//!
//! A plan is a JSON list of steps:
//!
//! ```json
//! [["open", "h1", "thermalctld"],
//!  ["call", "h1", "get_fans", ["ALL"]],
//!  ["call", "h1", "get_thermals", ["ALL", ["psus[0]/thermals[0]"]]],
//!  ["call", "h1", "set_fan_led", ["fan_drawers[0]/fans[0]", "red"]],
//!  ["sleep", 12],
//!  ["shell", "cp -a /run/hw-management /tmp/snapshot"],
//!  ["finalize", "h1"]]
//! ```
//!
//! Arguments are JSON: column sets as `"ALL"`, `"NONE"` or a list of column
//! names; devices as the keys the snapshots publish, and `get_thermals`'
//! skip list as a list of them; colours as their spelling; thresholds as
//! numbers.

use std::collections::HashMap;
use std::io::Write;
use std::time::Duration;

use platform_api::*;
use platform_provider::{open, Platform, PlatformImpl};
use serde_json::Value;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    std::process::exit(run_plan(&args, &mut std::io::stdout()));
}

/// The whole run, one line per step on `out`: 2 for a bad command line or
/// plan, else 0.
fn run_plan(args: &[String], out: &mut dyn Write) -> i32 {
    let (which, plan) = match args {
        [_, flag, which, plan] if flag == "--impl" => (which.clone(), plan.clone()),
        _ => {
            eprintln!("usage: platform-api-diff --impl pyo3|native PLAN.json");
            return 2;
        }
    };
    let which: PlatformImpl = match which.parse() {
        Ok(w) => w,
        Err(e) => {
            eprintln!("{e}");
            return 2;
        }
    };
    let text = match std::fs::read_to_string(&plan) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("{plan}: {e}");
            return 2;
        }
    };
    let steps: Vec<Value> = match serde_json::from_str(&text) {
        Ok(Value::Array(s)) => s,
        _ => {
            eprintln!("{plan}: not a JSON list of steps");
            return 2;
        }
    };
    let mut handles: HashMap<String, Platform> = HashMap::new();
    for (n, step) in steps.iter().enumerate() {
        let line = run(which, &mut handles, step);
        let _ = writeln!(out, "STEP {n} {} => {line}", compact(step));
        let _ = out.flush();
    }
    0
}

fn compact(v: &Value) -> String {
    serde_json::to_string(v).unwrap_or_default()
}

fn run(which: PlatformImpl, handles: &mut HashMap<String, Platform>, step: &Value) -> String {
    let s = step.as_array().cloned().unwrap_or_default();
    let word = |i: usize| s.get(i).and_then(Value::as_str).unwrap_or("").to_string();
    match word(0).as_str() {
        "open" => match open(&word(2), which) {
            Ok(p) => {
                handles.insert(word(1), p);
                "Ok".to_string()
            }
            Err(e) => format!("Err({e:?})"),
        },
        "sleep" => {
            let secs = s.get(1).and_then(Value::as_f64).unwrap_or(0.0);
            std::thread::sleep(Duration::from_secs_f64(secs));
            "Ok".to_string()
        }
        // A command between calls, for snapshotting what the calls so far
        // left behind; the exit status is part of the output.
        "shell" => match std::process::Command::new("sh")
            .arg("-c")
            .arg(word(1))
            .status()
        {
            Ok(st) => format!("{:?}", st.code()),
            Err(e) => format!("{e}"),
        },
        "finalize" => match handles.get_mut(&word(1)) {
            Some(p) => {
                p.finalize();
                "Ok".to_string()
            }
            None => "no such handle".to_string(),
        },
        "call" => match handles.get_mut(&word(1)) {
            Some(p) => {
                let args = s
                    .get(3)
                    .and_then(Value::as_array)
                    .cloned()
                    .unwrap_or_default();
                call(p, &word(2), &args)
            }
            None => "no such handle".to_string(),
        },
        other => format!("unknown step {other:?}"),
    }
}

fn arg_str(args: &[Value], i: usize) -> String {
    args.get(i)
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string()
}

/// A device key: what every row-addressed action takes.  A plan writes the
/// key a snapshot published, not the device's name.
fn arg_key(args: &[Value], i: usize) -> DeviceKey {
    DeviceKey::from(arg_str(args, i))
}

fn arg_i64(args: &[Value], i: usize) -> i64 {
    args.get(i).and_then(Value::as_i64).unwrap_or(0)
}

fn arg_bool(args: &[Value], i: usize) -> bool {
    args.get(i).and_then(Value::as_bool).unwrap_or(false)
}

fn arg_color(args: &[Value], i: usize) -> Result<LedColor, String> {
    let s = arg_str(args, i);
    LedColor::from_str(&s).ok_or_else(|| format!("bad colour {s:?}"))
}

fn arg_number(args: &[Value], i: usize) -> Number {
    match args.get(i) {
        Some(v) if v.is_i64() => Number::Int(v.as_i64().unwrap_or(0)),
        Some(v) => Number::Float(v.as_f64().unwrap_or(0.0)),
        None => Number::Int(0),
    }
}

/// A column set from `"ALL"`, `"NONE"` or a list of names.
macro_rules! cols {
    ($args:expr, $set:ident, $col:ident) => {{
        match $args.first() {
            Some(Value::String(s)) if s == "NONE" => $set::NONE,
            Some(Value::Array(names)) => {
                let mut c = $set::NONE;
                for col in $col::ALL {
                    if names.iter().any(|n| n.as_str() == Some(col.as_str())) {
                        c = c.with($set::of(*col));
                    }
                }
                c
            }
            _ => $set::ALL,
        }
    }};
}

fn call(p: &mut Platform, method: &str, a: &[Value]) -> String {
    macro_rules! show {
        ($e:expr) => {
            format!("{:?}", $e)
        };
    }
    match method {
        "get_chassis_info" => show!(p.get_chassis_info(cols!(a, ChassisInfoCols, ChassisInfoCol))),
        "get_modules" => show!(p.get_modules(cols!(a, ModuleInfoCols, ModuleInfoCol))),
        "get_thermals" => {
            // [cols, [key, ...]]: the keys to read only in part.
            let skip: Vec<DeviceKey> = match a.get(1) {
                Some(Value::Array(keys)) => keys
                    .iter()
                    .filter_map(Value::as_str)
                    .map(DeviceKey::from)
                    .collect(),
                _ => Vec::new(),
            };
            show!(p.get_thermals(cols!(a, ThermalInfoCols, ThermalInfoCol), &skip))
        }
        "get_fans" => {
            // [cols, absorb]: psud's way when absorb is true.
            let absorb = a.get(1).and_then(Value::as_bool).unwrap_or(false);
            show!(p.get_fans(cols!(a, FanInfoCols, FanInfoCol), absorb))
        }
        "get_fan_drawers" => {
            show!(p.get_fan_drawers(cols!(a, FanDrawerInfoCols, FanDrawerInfoCol)))
        }
        "get_psus" => show!(p.get_psus()),
        "get_components" => show!(p.get_components()),
        "get_sensors" => show!(p.get_sensors()),
        "get_leak_profiles" => show!(p.get_leak_profiles()),
        "get_leak_sensors" => show!(p.get_leak_sensors()),
        "get_eeprom" => show!(p.get_eeprom()),
        "get_bmcs" => show!(p.get_bmcs()),
        "get_watchdogs" => show!(p.get_watchdogs()),
        "get_module_key" => show!(p.get_module_key(&arg_str(a, 0))),
        "get_component_key" => show!(p.get_component_key(&arg_str(a, 0))),
        "get_module_component_key" => {
            show!(p.get_module_component_key(&arg_str(a, 0), &arg_str(a, 1)))
        }
        "set_fan_led" => match arg_color(a, 1) {
            Ok(c) => show!(p.set_fan_led(&arg_key(a, 0), c)),
            Err(e) => e,
        },
        "set_fan_drawer_led" => match arg_color(a, 1) {
            Ok(c) => show!(p.set_fan_drawer_led(&arg_key(a, 0), c)),
            Err(e) => e,
        },
        "set_fan_speed" => show!(p.set_fan_speed(&arg_key(a, 0), arg_i64(a, 1))),
        "set_psu_led" => match arg_color(a, 1) {
            Ok(c) => show!(p.set_psu_led(&arg_key(a, 0), c)),
            Err(e) => e,
        },
        "get_module_reboot_cause" => show!(p.get_module_reboot_cause(&arg_key(a, 0))),
        "get_module_midplane_down_reason" => {
            show!(p.get_module_midplane_down_reason(&arg_key(a, 0)))
        }
        "get_psu_master_led" => show!(p.get_psu_master_led(&arg_key(a, 0))),
        "set_psu_master_led" => match arg_color(a, 1) {
            Ok(c) => show!(p.set_psu_master_led(&arg_key(a, 0), c)),
            Err(e) => e,
        },
        "reboot_module" => show!(p.reboot_module(&arg_key(a, 0), &arg_str(a, 1))),
        "set_module_admin_state" => show!(p.set_module_admin_state(&arg_key(a, 0), arg_bool(a, 1))),
        "set_module_admin_state_gracefully" => {
            show!(p.set_module_admin_state_gracefully(&arg_key(a, 0), arg_bool(a, 1)))
        }
        "power_cycle_module" => show!(p.power_cycle_module(&arg_key(a, 0))),
        "module_pre_shutdown" => show!(p.module_pre_shutdown(&arg_key(a, 0))),
        "module_post_startup" => show!(p.module_post_startup(&arg_key(a, 0))),
        "set_module_state_transition" => {
            show!(p.set_module_state_transition(&arg_key(a, 0), &arg_str(a, 1)))
        }
        "clear_module_state_transition" => show!(p.clear_module_state_transition(&arg_key(a, 0))),
        "clear_module_gnoi_halt" => show!(p.clear_module_gnoi_halt(&arg_key(a, 0))),
        "set_sensor_high_threshold" => {
            show!(p.set_sensor_high_threshold(&arg_key(a, 0), arg_number(a, 1)))
        }
        "set_sensor_low_threshold" => {
            show!(p.set_sensor_low_threshold(&arg_key(a, 0), arg_number(a, 1)))
        }
        "get_available_firmware_version" => {
            show!(p.get_available_firmware_version(&arg_key(a, 0), &arg_str(a, 1)))
        }
        "get_firmware_update_notification" => {
            show!(p.get_firmware_update_notification(&arg_key(a, 0), &arg_str(a, 1)))
        }
        "install_firmware" => show!(p.install_firmware(&arg_key(a, 0), &arg_str(a, 1))),
        "update_firmware" => show!(p.update_firmware(&arg_key(a, 0), &arg_str(a, 1))),
        "auto_update_firmware" => {
            show!(p.auto_update_firmware(&arg_key(a, 0), &arg_str(a, 1), &arg_str(a, 2)))
        }
        "arm_watchdog" => show!(p.arm_watchdog(arg_i64(a, 0))),
        "disarm_watchdog" => show!(p.disarm_watchdog()),
        "initialize_system_led" => show!(p.initialize_system_led()),
        "init_midplane_switch" => show!(p.init_midplane_switch()),
        "set_chassis_led" => show!(p.set_chassis_led(&arg_str(a, 0))),
        "change_sed_password" => show!(p.change_sed_password(&arg_str(a, 0))),
        "reset_sed_password" => show!(p.reset_sed_password()),
        "bmc_open_session" => show!(p.bmc_open_session()),
        "bmc_close_session" => show!(p.bmc_close_session(&arg_str(a, 0))),
        "bmc_reset_root_password" => show!(p.bmc_reset_root_password()),
        "bmc_reset" => show!(p.bmc_reset(arg_bool(a, 0))),
        "bmc_update_firmware" => show!(p.bmc_update_firmware(&arg_str(a, 0))),
        "bmc_trigger_debug_log_dump" => show!(p.bmc_trigger_debug_log_dump()),
        "bmc_get_debug_log_dump" => {
            show!(p.bmc_get_debug_log_dump(&arg_str(a, 0), &arg_str(a, 1), &arg_str(a, 2)))
        }
        "get_asics" => show!(p.get_asics()),
        "tm_initialize" => show!(p.tm_initialize()),
        "tm_run_policy" => show!(p.tm_run_policy()),
        "tm_get_interval" => show!(p.tm_get_interval()),
        "tm_deinitialize" => show!(p.tm_deinitialize()),
        "eeprom_update_db" => show!(p.eeprom_update_db()),
        "get_storage_devices" => show!(p.get_storage_devices()),
        "get_pcie_devices" => show!(p.get_pcie_devices()),
        "get_pcie_aer_stats" => {
            show!(p.get_pcie_aer_stats(arg_i64(a, 0), arg_i64(a, 1), arg_i64(a, 2)))
        }
        "get_change_event" => show!(p.get_change_event(arg_i64(a, 0))),
        other => format!("unknown method {other:?}"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use pyo3::prelude::*;
    use serde_json::json;

    fn scratch(name: &str) -> std::path::PathBuf {
        let dir =
            std::env::temp_dir().join(format!("platform-api-diff-{name}-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn lines(args: &[&str]) -> (i32, String) {
        let args: Vec<String> = args.iter().map(|a| a.to_string()).collect();
        let mut out = Vec::new();
        let rc = run_plan(&args, &mut out);
        (rc, String::from_utf8(out).unwrap())
    }

    #[test]
    fn a_bad_command_line_or_plan_is_refused() {
        let dir = scratch("plans");
        let not_a_list = dir.join("dict.json");
        std::fs::write(&not_a_list, "{}").unwrap();
        let missing = dir.join("missing.json");
        for args in [
            vec!["platform-api-diff"],
            vec!["platform-api-diff", "--impl", "python", "plan.json"],
            vec![
                "platform-api-diff",
                "--impl",
                "native",
                missing.to_str().unwrap(),
            ],
            vec![
                "platform-api-diff",
                "--impl",
                "native",
                not_a_list.to_str().unwrap(),
            ],
        ] {
            assert_eq!(lines(&args), (2, String::new()), "{args:?}");
        }
        // The stub native platform refuses to open, and says why.
        let plan = dir.join("plan.json");
        std::fs::write(
            &plan,
            r#"[["open", "h1", "thermalctld"], ["sleep", 0.01], ["shell", "exit 3"]]"#,
        )
        .unwrap();
        let (rc, out) = lines(&[
            "platform-api-diff",
            "--impl",
            "native",
            plan.to_str().unwrap(),
        ]);
        assert_eq!(rc, 0);
        let out: Vec<&str> = out.lines().collect();
        assert!(
            out[0].starts_with(r#"STEP 0 ["open","h1","thermalctld"] => Err(NotSupported("#),
            "{}",
            out[0]
        );
        assert_eq!(
            out[1..],
            [
                r#"STEP 1 ["sleep",0.01] => Ok"#,
                r#"STEP 2 ["shell","exit 3"] => Some(3)"#
            ]
        );
        let _ = std::fs::remove_dir_all(dir);
    }

    /// Every method, through the bridge, over a chassis with no methods at
    /// all: whatever each answers, none is unknown here.
    #[test]
    fn every_method_is_dispatched() {
        let dir = scratch("vendor");
        let pkg = dir.join("sonic_platform");
        std::fs::create_dir_all(&pkg).unwrap();
        std::fs::write(pkg.join("__init__.py"), "").unwrap();
        std::fs::write(
            pkg.join("platform.py"),
            "class Chassis:\n    pass\n\n\nclass Platform:\n    def get_chassis(self):\n        return Chassis()\n",
        )
        .unwrap();
        Python::with_gil(|py| {
            let path = py.import("sys").and_then(|s| s.getattr("path")).unwrap();
            path.call_method1("insert", (0, dir.to_str().unwrap()))
                .unwrap();
        });
        let mut h = HashMap::new();
        let mut step = |v: Value| run(PlatformImpl::Pyo3, &mut h, &v);
        assert_eq!(step(json!(["open", "h1", "platform-api-diff-test"])), "Ok");
        assert_eq!(
            step(json!(["call", "h2", "get_fans", []])),
            "no such handle"
        );
        assert_eq!(step(json!(["finalize", "h2"])), "no such handle");
        assert_eq!(step(json!(["dance"])), r#"unknown step "dance""#);
        assert_eq!(
            step(json!(["call", "h1", "get_dances", []])),
            r#"unknown method "get_dances""#
        );
        for m in [
            "set_fan_led",
            "set_fan_drawer_led",
            "set_psu_led",
            "set_psu_master_led",
        ] {
            assert_eq!(
                step(json!(["call", "h1", m, ["x", "mauve"]])),
                r#"bad colour "mauve""#
            );
        }
        let calls: Value = serde_json::from_str(
            r#"[
             ["get_chassis_info", ["NONE"]], ["get_chassis_info", [["name", "serial"]]], ["get_modules", ["ALL"]],
             ["get_thermals", []], ["get_fans", ["ALL"]], ["get_fan_drawers", ["ALL"]], ["get_psus", []],
             ["get_components", []], ["get_sensors", []], ["get_leak_profiles", []], ["get_leak_sensors", []],
             ["get_eeprom", []], ["get_bmcs", []], ["get_watchdogs", []],
             ["get_module_key", ["DPU0"]], ["get_component_key", ["BIOS"]],
             ["get_module_component_key", ["LC1", "BIOS"]],
             ["set_fan_led", ["fan1", "red"]], ["set_fan_drawer_led", ["d1", "green"]], ["set_fan_speed", ["fan1", 50]],
             ["set_psu_led", ["PSU 1", "off"]], ["get_module_reboot_cause", ["DPU0"]],
             ["get_module_midplane_down_reason", ["DPU0"]], ["get_psu_master_led", ["PSU 1"]],
             ["set_psu_master_led", ["PSU 1", "green"]], ["reboot_module", ["DPU0", "cold"]],
             ["set_module_admin_state", ["DPU0", true]], ["set_module_admin_state_gracefully", ["DPU0", false]],
             ["power_cycle_module", ["DPU0"]], ["module_pre_shutdown", ["DPU0"]], ["module_post_startup", ["DPU0"]],
             ["set_module_state_transition", ["DPU0", "startup"]], ["clear_module_state_transition", ["DPU0"]],
             ["clear_module_gnoi_halt", ["DPU0"]], ["set_sensor_high_threshold", ["s1", 80]],
             ["set_sensor_low_threshold", ["s1", 1.5]], ["get_available_firmware_version", ["BIOS", "/x"]],
             ["get_firmware_update_notification", ["BIOS", "/x"]], ["install_firmware", ["BIOS", "/x"]],
             ["update_firmware", ["BIOS", "/x"]], ["auto_update_firmware", ["BIOS", "/x", "cold"]],
             ["arm_watchdog", [10]], ["disarm_watchdog", []], ["initialize_system_led", []],
             ["init_midplane_switch", []], ["set_chassis_led", ["green"]], ["change_sed_password", ["pw"]],
             ["reset_sed_password", []], ["bmc_open_session", []], ["bmc_close_session", ["s1"]],
             ["bmc_reset_root_password", []], ["bmc_reset", [true]], ["bmc_update_firmware", ["/x"]],
             ["bmc_trigger_debug_log_dump", []], ["bmc_get_debug_log_dump", ["1", "f", "/tmp"]], ["get_asics", []],
             ["tm_initialize", []], ["tm_run_policy", []], ["tm_get_interval", []], ["tm_deinitialize", []],
             ["eeprom_update_db", []], ["get_change_event", [0]], ["get_storage_devices", []],
             ["get_pcie_devices", []], ["get_pcie_aer_stats", [1, 2, 3]]]"#,
        )
        .unwrap();
        for c in calls.as_array().unwrap() {
            let (m, args) = (c[0].as_str().unwrap(), c[1].clone());
            let got = step(json!(["call", "h1", m, args]));
            assert!(
                !got.starts_with("unknown method") && !got.starts_with("bad colour"),
                "{m}: {got}"
            );
        }
        assert_eq!(step(json!(["finalize", "h1"])), "Ok");
        let _ = std::fs::remove_dir_all(dir);
    }
}
