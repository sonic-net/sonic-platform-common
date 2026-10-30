//! The generated native facade against the Python facade and bridge.
//!
//! One scripted chassis, built twice: as Python objects derived from the real
//! `sonic_platform_base` classes and read through `sonic_platform_api.facade`
//! and `platform-pyo3`, and as [`DynObject`]s read through [`BaseFacade`].
//! Every method of the platform API is called on both, and both the answer and
//! the sequence of platform methods it called must be identical.  The scripts
//! are random -- values of the right type, of the wrong type, sentinels,
//! `None`, the `NotImplementedError` class returned, exceptions raised --
//! because what the two facades must agree on is precisely what a vendor's
//! oddities do.
//!
//! Needs `PYTHONPATH` to include the repository root, as the bridge's own
//! tests do.

use std::collections::HashMap;
use std::ffi::CString;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, OnceLock};

use platform_api::*;
use platform_base::escape_hatch::EscapeHatches;
use platform_base::object::DynObject;
use platform_base::{BaseClass, BaseFacade, Exc, PyErr, PyObject, PyVal};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyModule, PyTuple};

// ── scenarios ───────────────────────────────────────────────────────────────

#[derive(Clone, Debug)]
enum SVal {
    None,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    List(Vec<SVal>),
    Tuple(Vec<SVal>),
    Dict(Vec<(SVal, SVal)>),
    NotImpl,
    Severity(&'static str),
    Obj(usize),
}

#[derive(Clone, Debug)]
enum Ans {
    Val(SVal),
    Raise(&'static str, String),
}

struct Node {
    class: String,
    base: BaseClass,
    answers: HashMap<&'static str, Ans>,
}

/// A deterministic generator, so a failure names the seed that reproduces it.
struct Rng(u64);

impl Rng {
    fn next(&mut self) -> u64 {
        self.0 = self
            .0
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.0 >> 33
    }
    fn below(&mut self, n: u64) -> u64 {
        self.next() % n
    }
    fn chance(&mut self, pct: u64) -> bool {
        self.below(100) < pct
    }
    fn pick<'a, T>(&mut self, v: &'a [T]) -> &'a T {
        &v[self.below(v.len() as u64) as usize]
    }
}

const NAMES: &[&str] = &[
    "fan1", "PSU 1", "drawer 1", "Module 1", "DPU0", "thermal1", "x",
];
const ERRORS: &[&str] = &["KeyError", "TypeError", "RuntimeError", "IndexError"];

struct Gen {
    rng: Rng,
    nodes: Vec<Node>,
    seed: u64,
    /// stormond's disks: a name, and the node answering for it, or None for
    /// a disk no utility class handles.
    disks: Vec<(String, Option<usize>)>,
}

impl Gen {
    /// An answer of no particular type: what a vendor's oddity looks like.
    fn junk(&mut self) -> Ans {
        let r = &mut self.rng;
        match r.below(17) {
            0 => Ans::Val(SVal::None),
            1 => Ans::Val(SVal::NotImpl),
            2 => Ans::Raise("NotImplementedError", String::new()),
            3 => Ans::Raise("NotImplementedError", "nope".into()),
            4 => Ans::Val(SVal::Str("N/A".into())),
            5 => Ans::Val(SVal::Str(" n/a ".into())),
            6 => Ans::Val(SVal::Bool(r.chance(50))),
            7 => Ans::Val(SVal::Int(r.below(300) as i64 - 50)),
            8 => Ans::Val(SVal::Float((r.below(20000) as f64) / 100.0 - 10.0)),
            9 => Ans::Val(SVal::Str(format!("{}", r.below(200)))),
            10 => Ans::Val(SVal::Str(format!("{}.5", r.below(200)))),
            11 => Ans::Val(SVal::Str(r.pick(NAMES).to_string())),
            12 => Ans::Raise("ValueError", "bad value".into()),
            13 => Ans::Raise(r.pick::<&str>(ERRORS), "boom".into()),
            14 => Ans::Val(SVal::Tuple(vec![
                SVal::Str(r.pick(NAMES).to_string()),
                SVal::Str("detail".into()),
            ])),
            // Integers no f64 holds exactly, and the edges of the widths.
            15 => Ans::Val(SVal::Int(*r.pick(&[
                (1 << 53) + 1,
                i64::MAX,
                i64::MIN,
                i64::from(u32::MAX) + 1,
                i64::from(i32::MIN) - 1,
            ]))),
            _ => Ans::Val(SVal::List(vec![SVal::Int(1)])),
        }
    }

    /// A plausible answer, most of the time, and junk otherwise.
    fn scalar(&mut self, kind: &str) -> Ans {
        if self.rng.chance(30) {
            return self.junk();
        }
        let r = &mut self.rng;
        Ans::Val(match kind {
            "bool" => SVal::Bool(r.chance(50)),
            "pct" => SVal::Int(r.below(101) as i64),
            "int" => SVal::Int(r.below(10) as i64),
            "float" => SVal::Float((r.below(20000) as f64) / 100.0),
            "name" => SVal::Str(r.pick(NAMES).to_string()),
            "led" => SVal::Str(
                r.pick(&["green", "red", "amber", "off", "green_blink"])
                    .to_string(),
            ),
            "thr" => {
                if r.chance(50) {
                    SVal::Int(r.below(130) as i64)
                } else {
                    SVal::Float((r.below(13000) as f64) / 100.0)
                }
            }
            "tuple" => SVal::Tuple(vec![
                SVal::Str(r.pick(NAMES).to_string()),
                SVal::Str("why".into()),
            ]),
            "sev" => SVal::Severity(if r.chance(50) { "MINOR" } else { "CRITICAL" }),
            _ => SVal::Str(format!("s{}", r.below(10))),
        })
    }

    fn node(&mut self, prefix: &str, base: BaseClass) -> usize {
        let id = self.nodes.len();
        self.nodes.push(Node {
            class: format!("{prefix}_{}_{id}", self.seed),
            base,
            answers: HashMap::new(),
        });
        id
    }

    fn set(&mut self, id: usize, method: &'static str, a: Ans) {
        self.nodes[id].answers.insert(method, a);
    }

    /// Script `method` with probability `pct`, else leave the base class's.
    fn maybe(&mut self, id: usize, method: &'static str, kind: &str, pct: u64) {
        if self.rng.chance(pct) {
            let a = self.scalar(kind);
            self.set(id, method, a);
        }
    }

    fn device(&mut self, id: usize) {
        self.maybe(id, "get_name", "name", 85);
        self.maybe(id, "get_presence", "bool", 70);
        self.maybe(id, "get_status", "bool", 60);
        self.maybe(id, "get_model", "str", 50);
        self.maybe(id, "get_serial", "str", 50);
        self.maybe(id, "get_revision", "str", 30);
        self.maybe(id, "get_position_in_parent", "int", 50);
        self.maybe(id, "is_replaceable", "bool", 50);
    }

    /// A list of children of one kind, or one of the ways not to have any.
    fn children(&mut self, max: u64, mut make: impl FnMut(&mut Gen) -> usize) -> Ans {
        match self.rng.below(10) {
            0 => Ans::Val(SVal::None),
            1 => Ans::Raise("NotImplementedError", String::new()),
            2 => Ans::Val(SVal::List(vec![SVal::None, SVal::Str("odd".into())])),
            _ => {
                let n = self.rng.below(max + 1);
                Ans::Val(SVal::List((0..n).map(|_| SVal::Obj(make(self))).collect()))
            }
        }
    }

    fn fan(&mut self) -> usize {
        let id = self.node("Fan", BaseClass::FanBase);
        self.device(id);
        for (m, k) in [
            ("get_speed", "pct"),
            ("get_target_speed", "pct"),
            ("get_speed_tolerance", "pct"),
        ] {
            self.maybe(id, m, k, 70);
        }
        // A fan that is not there and whose readings raise: thermalctld does
        // not ask it (thermalctld:471-478), psud's absorbing read does.
        if self.rng.chance(20) {
            self.set(id, "get_presence", Ans::Val(SVal::Bool(false)));
            self.set(id, "get_speed", Ans::Raise("RuntimeError", "absent".into()));
            self.set(id, "get_direction", Ans::Raise("ValueError", String::new()));
        }
        self.maybe(id, "get_direction", "str", 60);
        self.maybe(id, "is_under_speed", "bool", 30);
        self.maybe(id, "is_over_speed", "bool", 30);
        self.maybe(id, "get_status_led", "led", 60);
        self.maybe(id, "set_status_led", "bool", 50);
        self.maybe(id, "set_speed", "bool", 50);
        id
    }

    fn thermal(&mut self) -> usize {
        let id = self.node("Thermal", BaseClass::ThermalBase);
        self.device(id);
        self.maybe(id, "get_temperature", "float", 80);
        for m in [
            "get_high_threshold",
            "get_low_threshold",
            "get_high_critical_threshold",
            "get_low_critical_threshold",
        ] {
            self.maybe(id, m, "thr", 60);
        }
        self.maybe(id, "get_minimum_recorded", "float", 40);
        self.maybe(id, "get_maximum_recorded", "float", 40);
        id
    }

    fn psu(&mut self, base: BaseClass) -> usize {
        let id = self.node(
            if base == BaseClass::PdbBase {
                "Pdb"
            } else {
                "Psu"
            },
            base,
        );
        self.device(id);
        for m in [
            "get_voltage",
            "get_current",
            "get_power",
            "get_input_voltage",
            "get_input_current",
            "get_temperature",
            "get_maximum_supplied_power",
            "get_psu_power_warning_suppress_threshold",
            "get_psu_power_critical_threshold",
            "get_input_power",
            "get_output_voltage",
            "get_output_current",
            "get_output_power",
        ] {
            self.maybe(id, m, "float", 55);
        }
        for m in [
            "get_voltage_high_threshold",
            "get_voltage_low_threshold",
            "get_temperature_high_threshold",
        ] {
            self.maybe(id, m, "thr", 50);
        }
        self.maybe(id, "get_powergood_status", "bool", 60);
        self.maybe(id, "get_status_led", "led", 50);
        self.maybe(id, "set_status_led", "bool", 40);
        self.maybe(id, "set_status_master_led", "bool", 20);
        self.maybe(id, "get_status_master_led", "led", 20);
        if self.rng.chance(70) {
            let a = self.children(2, |g| g.fan());
            self.set(id, "get_all_fans", a);
        }
        if self.rng.chance(70) {
            let a = self.children(2, |g| g.thermal());
            self.set(id, "get_all_thermals", a);
        }
        id
    }

    fn component(&mut self) -> usize {
        let k = self.node("Component", BaseClass::ComponentBase);
        for (m, kind) in [
            ("get_name", "name"),
            ("get_description", "str"),
            ("get_firmware_version", "str"),
        ] {
            self.maybe(k, m, kind, 70);
        }
        for m in ["install_firmware", "update_firmware"] {
            self.maybe(k, m, "bool", 40);
        }
        for m in [
            "get_available_firmware_version",
            "get_firmware_update_notification",
        ] {
            self.maybe(k, m, "str", 40);
        }
        self.maybe(k, "auto_update_firmware", "int", 40);
        k
    }

    fn sensor(&mut self, base: BaseClass) -> usize {
        let s = self.node("Sensor", base);
        self.device(s);
        self.maybe(s, "get_value", "float", 70);
        self.maybe(s, "get_unit", "str", 50);
        for m in [
            "get_high_threshold",
            "get_low_threshold",
            "get_high_critical_threshold",
            "get_low_critical_threshold",
        ] {
            self.maybe(s, m, "thr", 50);
        }
        self.maybe(s, "get_minimum_recorded", "float", 30);
        self.maybe(s, "get_maximum_recorded", "float", 30);
        self.maybe(s, "set_high_threshold", "bool", 40);
        self.maybe(s, "set_low_threshold", "bool", 40);
        s
    }

    fn module(&mut self) -> usize {
        let id = self.node("Module", BaseClass::ModuleBase);
        self.device(id);
        for (m, k) in [
            ("get_description", "str"),
            ("get_slot", "int"),
            ("get_type", "str"),
            ("get_oper_status", "str"),
            ("get_maximum_consumed_power", "float"),
            ("get_base_mac", "str"),
            ("get_dpu_id", "int"),
            ("get_midplane_ip", "str"),
            ("is_midplane_reachable", "bool"),
            ("get_reboot_cause", "tuple"),
            ("get_midplane_down_reason", "tuple"),
        ] {
            self.maybe(id, m, k, 60);
        }
        // ModuleBase bodies are not ported natively yet: always scripted.
        for m in [
            "get_module_state_transition",
            "set_module_state_transition",
            "clear_module_state_transition",
            "clear_module_gnoi_halt_in_progress",
            "module_pre_shutdown",
            "module_post_startup",
            "set_admin_state_gracefully",
        ] {
            let a = self.scalar("bool");
            self.set(id, m, a);
        }
        for m in ["reboot", "set_admin_state", "do_power_cycle"] {
            self.maybe(id, m, "bool", 50);
        }
        for (m, max) in [
            ("get_all_fans", 1),
            ("get_all_psus", 1),
            ("get_all_thermals", 1),
        ] {
            if self.rng.chance(50) {
                let a = match m {
                    "get_all_fans" => self.children(max, |g| g.fan()),
                    "get_all_psus" => self.children(max, |g| g.psu(BaseClass::PsuBase)),
                    _ => self.children(max, |g| g.thermal()),
                };
                self.set(id, m, a);
            }
        }
        if self.rng.chance(50) {
            let a = Ans::Val(SVal::List(vec![
                SVal::Tuple(vec![
                    SVal::Str("0".into()),
                    SVal::Str("0000:01:00.0".into()),
                ]),
                SVal::Tuple(vec![SVal::Int(1)]),
                SVal::Int(7),
            ]));
            self.set(id, "get_all_asics", a);
        }
        if self.rng.chance(40) {
            let a = Ans::Val(SVal::Dict(vec![
                (SVal::Str("0x21".into()), SVal::Str("SN".into())),
                (SVal::Str("0x22".into()), SVal::None),
            ]));
            self.set(id, "get_system_eeprom_info", a);
        }
        // Read through the module only on a modular chassis.
        if self.rng.chance(40) {
            let a = self.children(1, |g| g.component());
            self.set(id, "get_all_components", a);
        }
        for (getter, base) in [
            ("get_all_voltage_sensors", BaseClass::VoltageSensorBase),
            ("get_all_current_sensors", BaseClass::CurrentSensorBase),
        ] {
            if self.rng.chance(30) {
                // More than one, so that a nameless one's fallback carries
                // an index past 1 (sensormond's '{} voltage_sensor {}').
                let a = self.children(2, |g| g.sensor(base));
                self.set(id, getter, a);
            }
        }
        id
    }

    fn chassis(seed: u64) -> Gen {
        let mut g = Gen {
            rng: Rng(seed.wrapping_mul(2654435761) ^ 0x9e3779b97f4a7c15),
            nodes: Vec::new(),
            seed,
            disks: Vec::new(),
        };
        let c = g.node("Chassis", BaseClass::ChassisBase);
        g.device(c);
        for (m, k) in [
            ("get_base_mac", "str"),
            ("get_reboot_cause", "tuple"),
            ("get_status_led", "led"),
            ("get_my_slot", "int"),
            ("get_supervisor_slot", "int"),
            ("get_dpu_id", "int"),
            ("is_modular_chassis", "bool"),
            ("is_smartswitch", "bool"),
            ("is_dpu", "bool"),
            ("is_bmc", "bool"),
            ("is_liquid_cooled", "bool"),
            ("get_dataplane_state", "bool"),
            ("get_controlplane_state", "bool"),
            ("set_status_led", "bool"),
            ("initizalize_system_led", "bool"),
            ("init_midplane_switch", "bool"),
            ("get_module_index", "int"),
        ] {
            g.maybe(c, m, k, 55);
        }
        let a = g.children(2, |g| g.thermal());
        g.set(c, "get_all_thermals", a);
        let a = g.children(2, |g| {
            let d = g.node("Drawer", BaseClass::FanDrawerBase);
            g.device(d);
            // A drawer that names itself 'N/A', as a virtual one does: its
            // fans are the chassis's.
            if g.rng.chance(25) {
                g.set(d, "get_name", Ans::Val(SVal::Str("N/A".into())));
            }
            g.maybe(d, "get_status_led", "led", 50);
            g.maybe(d, "set_status_led", "bool", 50);
            g.maybe(d, "get_maximum_consumed_power", "float", 50);
            let fans = g.children(2, |g| g.fan());
            g.set(d, "get_all_fans", fans);
            d
        });
        g.set(c, "get_all_fan_drawers", a);
        let a = g.children(2, |g| g.psu(BaseClass::PsuBase));
        g.set(c, "get_all_psus", a);
        if g.rng.chance(50) {
            let a = g.children(1, |g| g.psu(BaseClass::PdbBase));
            g.set(c, "get_all_pdbs", a);
        }
        if g.rng.chance(60) {
            let a = g.children(2, |g| g.module());
            g.set(c, "get_all_modules", a);
        }
        if g.rng.chance(50) {
            let a = g.children(2, |g| g.component());
            g.set(c, "get_all_components", a);
        }
        for (getter, base) in [
            ("get_all_voltage_sensors", BaseClass::VoltageSensorBase),
            ("get_all_current_sensors", BaseClass::CurrentSensorBase),
        ] {
            if g.rng.chance(40) {
                let a = g.children(3, |g| g.sensor(base));
                g.set(c, getter, a);
            }
        }
        if g.rng.chance(50) {
            let lc = g.node("LiquidCooling", BaseClass::LiquidCoolingBase);
            let sensors = g.children(2, |g| {
                let s = g.node("Leak", BaseClass::LeakageSensorBase);
                // State-backed in the base class: always scripted.
                for (m, k) in [
                    ("get_name", "name"),
                    ("is_leak", "bool"),
                    ("is_leak_sensor_ok", "bool"),
                    ("get_leak_sensor_type", "str"),
                    ("get_leak_sensor_location", "str"),
                    ("get_leak_severity", "sev"),
                ] {
                    let a = g.scalar(k);
                    g.set(s, m, a);
                }
                if g.rng.chance(50) {
                    let p = g.node("Profile", BaseClass::LeakSensorProfileBase);
                    let a = g.scalar("str");
                    g.set(p, "get_type", a);
                    let a = g.scalar("int");
                    g.set(p, "get_leak_max_minor_duration_sec", a);
                    g.set(s, "get_leak_profile", Ans::Val(SVal::Obj(p)));
                }
                s
            });
            g.set(lc, "get_all_leak_sensors", sensors);
            let profiles = g.children(2, |g| {
                let p = g.node("Profile", BaseClass::LeakSensorProfileBase);
                let a = g.scalar("str");
                g.set(p, "get_type", a);
                let a = g.scalar("int");
                g.set(p, "get_leak_max_minor_duration_sec", a);
                p
            });
            g.set(lc, "get_all_profiles", profiles);
            g.set(c, "get_liquid_cooling", Ans::Val(SVal::Obj(lc)));
        }
        if g.rng.chance(50) {
            let w = g.node("Watchdog", BaseClass::WatchdogBase);
            for (m, k) in [
                ("is_armed", "bool"),
                ("get_remaining_time", "int"),
                ("arm", "int"),
                ("disarm", "bool"),
            ] {
                g.maybe(w, m, k, 70);
            }
            g.set(c, "get_watchdog", Ans::Val(SVal::Obj(w)));
        }
        if g.rng.chance(40) {
            let s = g.node("Sed", BaseClass::SedMgmtBase);
            for m in ["change_sed_password", "reset_sed_password"] {
                let a = g.scalar("bool");
                g.set(s, m, a);
            }
            g.set(c, "get_sed_mgmt", Ans::Val(SVal::Obj(s)));
        }
        if g.rng.chance(40) {
            let b = g.node("Bmc", BaseClass::BMCBase);
            for (m, k) in [
                ("get_name", "name"),
                ("get_presence", "bool"),
                ("get_model", "str"),
                ("get_serial", "str"),
                ("get_revision", "str"),
                ("get_status", "bool"),
                ("is_replaceable", "bool"),
                ("get_version", "str"),
                ("get_position_in_parent", "int"),
            ] {
                let a = g.scalar(k);
                g.set(b, m, a);
            }
            let eeprom = Ans::Val(SVal::Dict(vec![(
                SVal::Str("Model".into()),
                SVal::Str("BMC".into()),
            )]));
            g.set(b, "get_eeprom", eeprom);
            for m in [
                "open_session",
                "close_session",
                "reset_root_password",
                "request_bmc_reset",
                "update_firmware",
                "trigger_bmc_debug_log_dump",
                "get_bmc_debug_log_dump",
            ] {
                let a = match g.rng.below(5) {
                    0 => g.junk(),
                    1 => Ans::Val(SVal::Tuple(vec![
                        SVal::Int(0),
                        SVal::Tuple(vec![
                            SVal::Str("ok".into()),
                            SVal::Tuple(vec![SVal::Str("sid".into()), SVal::Str("tok".into())]),
                        ]),
                    ])),
                    2 => Ans::Val(SVal::Tuple(vec![
                        SVal::Str("3".into()),
                        SVal::Str("msg".into()),
                    ])),
                    3 => Ans::Val(SVal::List(vec![SVal::Int(1), SVal::None])),
                    _ => Ans::Val(SVal::Tuple(vec![
                        SVal::Int(0),
                        SVal::List(vec![SVal::Str("t1".into()), SVal::Str("done".into())]),
                    ])),
                };
                g.set(b, m, a);
            }
            g.set(c, "get_bmc", Ans::Val(SVal::Obj(b)));
        }
        if g.rng.chance(50) {
            let a = Ans::Val(SVal::Dict(vec![
                (
                    SVal::Str("0x24".into()),
                    SVal::Str("00:11:22:33:44:55".into()),
                ),
                (SVal::Int(37), SVal::Int(5)),
            ]));
            g.set(c, "get_system_eeprom_info", a);
        }
        if g.rng.chance(60) {
            let tm = g.node("ThermalManager", BaseClass::ThermalManagerBase);
            for m in [
                "initialize",
                "load",
                "init_thermal_algorithm",
                "run_policy",
                "stop",
                "deinitialize",
            ] {
                let a = if g.rng.chance(80) {
                    Ans::Val(SVal::None)
                } else {
                    g.junk()
                };
                g.set(tm, m, a);
            }
            let a = g.scalar("float");
            g.set(tm, "get_interval", a);
            g.set(c, "get_thermal_manager", Ans::Val(SVal::Obj(tm)));
        } else if g.rng.chance(50) {
            g.set(
                c,
                "get_thermal_manager",
                Ans::Raise("NotImplementedError", String::new()),
            );
        }
        if g.rng.chance(50) {
            let e = g.node("Eeprom", BaseClass::Object);
            let a = if g.rng.chance(70) {
                Ans::Val(SVal::Str("raw".into()))
            } else {
                g.junk()
            };
            g.set(e, "read_eeprom", a);
            let a = if g.rng.chance(70) {
                Ans::Val(SVal::Int(0))
            } else {
                g.junk()
            };
            g.set(e, "update_eeprom_db", a);
            g.set(c, "get_eeprom", Ans::Val(SVal::Obj(e)));
        }
        if g.rng.chance(50) {
            let a = match g.rng.below(3) {
                0 => g.junk(),
                1 => Ans::Val(SVal::Tuple(vec![
                    SVal::Bool(true),
                    SVal::Dict(vec![
                        (
                            SVal::Str("sfp".into()),
                            SVal::Dict(vec![
                                (SVal::Str("1".into()), SVal::Str("1".into())),
                                (SVal::Int(2), SVal::Int(9)),
                            ]),
                        ),
                        (SVal::Str("fan".into()), SVal::Int(3)),
                    ]),
                ])),
                _ => Ans::Val(SVal::Tuple(vec![SVal::Bool(false), SVal::None])),
            };
            g.set(c, "get_change_event", a);
        }
        // Disks, each read in stormond's two passes; a getter that raises
        // costs that disk that pass.
        for d in 0..g.rng.below(4) {
            let name = format!("sd{}", (b'a' + d as u8) as char);
            if g.rng.chance(15) {
                g.disks.push((name, None));
                continue;
            }
            let n = g.node("Disk", BaseClass::Object);
            for (m, k, pct) in [
                ("get_model", "str", 90),
                ("get_serial", "str", 90),
                ("fetch_parse_info", "none", 90),
                ("get_firmware", "str", 90),
                ("get_health", "str", 90),
                ("get_temperature", "str", 90),
                ("get_fs_io_reads", "int", 90),
                ("get_fs_io_writes", "int", 90),
                ("get_disk_io_reads", "str", 90),
                ("get_disk_io_writes", "str", 90),
                ("get_reserved_blocks", "str", 90),
            ] {
                if g.rng.chance(pct) {
                    let a = if k == "none" && g.rng.chance(80) {
                        Ans::Val(SVal::None)
                    } else {
                        g.scalar(k)
                    };
                    g.set(n, m, a);
                }
            }
            g.disks.push((name, Some(n)));
        }
        g
    }
}

// ── the two trees ───────────────────────────────────────────────────────────

type Trace = Arc<Mutex<Vec<String>>>;

fn to_pyval(v: &SVal, objs: &[OnceLock<Arc<dyn PyObject>>]) -> PyVal {
    match v {
        SVal::None => PyVal::None,
        SVal::Bool(b) => PyVal::Bool(*b),
        SVal::Int(i) => PyVal::Int(i128::from(*i)),
        SVal::Float(f) => PyVal::Float(*f),
        SVal::Str(s) => PyVal::Str(s.clone()),
        SVal::List(v) => PyVal::List(v.iter().map(|x| to_pyval(x, objs)).collect()),
        SVal::Tuple(v) => PyVal::Tuple(v.iter().map(|x| to_pyval(x, objs)).collect()),
        SVal::Dict(d) => PyVal::Dict(
            d.iter()
                .map(|(k, x)| (to_pyval(k, objs), to_pyval(x, objs)))
                .collect(),
        ),
        SVal::NotImpl => PyVal::NotImplementedClass,
        SVal::Severity(n) => PyVal::Enum(platform_base::py::PyEnum {
            class: "LeakSeverity",
            name: n,
            value: Box::new(PyVal::Str(n.to_string())),
        }),
        SVal::Obj(i) => PyVal::Obj(objs[*i].get().expect("built").clone()),
    }
}

fn arg_repr(v: &PyVal) -> String {
    match v {
        // Python's side shows any non-builtin -- an object, a class -- this way.
        PyVal::Obj(_) | PyVal::NotImplementedClass | PyVal::Enum(_) => "<obj>".into(),
        other => other.py_repr(),
    }
}

fn exc_of(name: &str) -> Exc {
    match name {
        "NotImplementedError" => Exc::NotImplementedError,
        "ValueError" => Exc::ValueError,
        "KeyError" => Exc::KeyError,
        "TypeError" => Exc::TypeError,
        "RuntimeError" => Exc::RuntimeError,
        "IndexError" => Exc::IndexError,
        other => panic!("{other}"),
    }
}

fn build_rust(nodes: &[Node], trace: &Trace) -> PyVal {
    let objs: Arc<Vec<OnceLock<Arc<dyn PyObject>>>> =
        Arc::new((0..nodes.len()).map(|_| OnceLock::new()).collect());
    for (i, n) in nodes.iter().enumerate() {
        let class: &'static str = Box::leak(n.class.clone().into_boxed_str());
        let answers = n.answers.clone();
        let trace = trace.clone();
        let objs2 = objs.clone();
        let o = DynObject {
            class,
            base: n.base,
            handler: Box::new(move |_s, method, args| {
                let a = answers.get(method)?;
                trace.lock().unwrap().push(format!(
                    "{class}.{method}({})",
                    args.iter().map(arg_repr).collect::<Vec<_>>().join(", ")
                ));
                Some(match a {
                    Ans::Val(v) => Ok(to_pyval(v, &objs2)),
                    Ans::Raise(e, msg) => Err(PyErr::new(
                        exc_of(e),
                        if msg.is_empty() {
                            vec![]
                        } else {
                            vec![PyVal::Str(msg.clone())]
                        },
                    )),
                })
            }),
        };
        // What `PsuBase.__init__` does, as the Python object's construction does.
        if matches!(n.base, BaseClass::PsuBase | BaseClass::PdbBase) {
            platform_base::bodies::psu_base::init();
        }
        let _ = objs[i].set(Arc::new(o));
    }
    PyVal::Obj(objs[0].get().unwrap().clone())
}

const PY_SUPPORT: &str = r#"
import builtins, sys, types

def _stub(name, **attrs):
    m = types.ModuleType(name)
    m.__path__ = []
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

class _Quiet(object):
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return lambda *a, **k: None

if 'sonic_py_common' not in sys.modules:
    di = _stub('sonic_py_common.device_info', is_switch_bmc=lambda: False, get_cpo_data=lambda *a, **k: None)
    lg = _stub('sonic_py_common.logger', Logger=_Quiet)
    sl = _stub('sonic_py_common.syslogger', SysLogger=_Quiet)
    _stub('sonic_py_common', device_info=di, logger=lg, syslogger=sl)

from sonic_platform_base.chassis_base import ChassisBase
from sonic_platform_base.module_base import ModuleBase
from sonic_platform_base.fan_base import FanBase
from sonic_platform_base.fan_drawer_base import FanDrawerBase
from sonic_platform_base.psu_base import PsuBase
from sonic_platform_base.pdb_base import PdbBase
from sonic_platform_base.thermal_base import ThermalBase
from sonic_platform_base.sensor_base import SensorBase, VoltageSensorBase, CurrentSensorBase
from sonic_platform_base.liquid_cooling_base import (
    LiquidCoolingBase, LeakageSensorBase, LeakSensorProfileBase, LeakSeverity)
from sonic_platform_base.component_base import ComponentBase
from sonic_platform_base.watchdog_base import WatchdogBase
from sonic_platform_base.bmc_base import BMCBase
from sonic_platform_base.sed_mgmt_base import SedMgmtBase
from sonic_platform_base.sonic_thermal_control.thermal_manager_base import ThermalManagerBase

BASES = {c.__name__: c for c in (
    ChassisBase, ModuleBase, FanBase, FanDrawerBase, PsuBase, PdbBase, ThermalBase,
    SensorBase, VoltageSensorBase, CurrentSensorBase, LiquidCoolingBase,
    LeakageSensorBase, LeakSensorProfileBase, ComponentBase, WatchdogBase, BMCBase,
    SedMgmtBase, ThermalManagerBase)}
BASES['Object'] = object

TRACE = []

def _r(a):
    if isinstance(a, (str, int, float, bool, list, tuple, dict, type(None))):
        return repr(a)
    return '<obj>'

def build(nodes):
    objs = [None] * len(nodes)

    def conv(v):
        tag = v[0]
        if tag == 'none':
            return None
        if tag in ('bool', 'int', 'float', 'str'):
            return v[1]
        if tag == 'list':
            return [conv(x) for x in v[1]]
        if tag == 'tuple':
            return tuple(conv(x) for x in v[1])
        if tag == 'dict':
            return {conv(k): conv(x) for k, x in v[1]}
        if tag == 'notimpl':
            return NotImplementedError
        if tag == 'sev':
            return LeakSeverity[v[1]]
        if tag == 'obj':
            return objs[v[1]]
        raise AssertionError(tag)

    for i, (cname, bname, answers) in enumerate(nodes):
        ns = {}
        for meth, ans in answers:
            def f(self, *args, _cn=cname, _m=meth, _a=ans):
                TRACE.append('%s.%s(%s)' % (_cn, _m, ', '.join(_r(a) for a in args)))
                if _a[0] == 'raise':
                    raise getattr(builtins, _a[1])(*_a[2])
                return conv(_a[1])
            ns[meth] = f
        base = BASES[bname]
        cls = type(cname, (base,), ns)
        # Only the methods a scenario scripts are the class's; an abstract
        # base would refuse to construct, so its abstract set is cleared.
        cls.__abstractmethods__ = frozenset()
        if bname == 'BMCBase':
            objs[i] = cls('169.254.0.1')
        elif bname == 'LeakageSensorBase':
            objs[i] = cls('leak')
        else:
            objs[i] = cls()
    global OBJS
    OBJS = objs
    return objs[0]

def facade(chassis):
    from sonic_platform_api.facade import PlatformApi
    return PlatformApi(chassis)

def set_storage(api, disks):
    # What `StorageDevices()` would have found: a name per disk, and its
    # utility object or None.
    class Devices(object):
        pass
    d = Devices()
    d.devices = {name: (None if n is None else OBJS[n]) for name, n in disks}
    api._hatch._storage, api._hatch._storage_tried = d, True
"#;

fn sval_to_py<'py>(py: Python<'py>, v: &SVal) -> Bound<'py, PyAny> {
    let tagged = |tag: &str, inner: Bound<'py, PyAny>| -> Bound<'py, PyAny> {
        PyTuple::new(py, [tag.into_pyobject(py).unwrap().into_any(), inner])
            .unwrap()
            .into_any()
    };
    let seq = |v: &[SVal]| -> Bound<'py, PyAny> {
        let items: Vec<_> = v.iter().map(|x| sval_to_py(py, x)).collect();
        PyList::new(py, items).unwrap().into_any()
    };
    match v {
        SVal::None => PyTuple::new(py, ["none"]).unwrap().into_any(),
        SVal::Bool(b) => tagged("bool", b.into_pyobject(py).unwrap().to_owned().into_any()),
        SVal::Int(i) => tagged("int", i.into_pyobject(py).unwrap().into_any()),
        SVal::Float(f) => tagged("float", f.into_pyobject(py).unwrap().into_any()),
        SVal::Str(s) => tagged("str", s.into_pyobject(py).unwrap().into_any()),
        SVal::List(v) => tagged("list", seq(v)),
        SVal::Tuple(v) => tagged("tuple", seq(v)),
        SVal::Dict(d) => {
            let items: Vec<_> = d
                .iter()
                .map(|(k, x)| {
                    PyTuple::new(py, [sval_to_py(py, k), sval_to_py(py, x)])
                        .unwrap()
                        .into_any()
                })
                .collect();
            tagged("dict", PyList::new(py, items).unwrap().into_any())
        }
        SVal::NotImpl => PyTuple::new(py, ["notimpl"]).unwrap().into_any(),
        SVal::Severity(n) => tagged("sev", n.into_pyobject(py).unwrap().into_any()),
        SVal::Obj(i) => tagged("obj", i.into_pyobject(py).unwrap().into_any()),
    }
}

fn ans_to_py<'py>(py: Python<'py>, a: &Ans) -> Bound<'py, PyAny> {
    match a {
        Ans::Val(v) => PyTuple::new(
            py,
            [
                "val".into_pyobject(py).unwrap().into_any(),
                sval_to_py(py, v),
            ],
        )
        .unwrap()
        .into_any(),
        Ans::Raise(e, msg) => {
            let args: Vec<Bound<'py, PyAny>> = if msg.is_empty() {
                vec![]
            } else {
                vec![msg.into_pyobject(py).unwrap().into_any()]
            };
            PyTuple::new(
                py,
                [
                    "raise".into_pyobject(py).unwrap().into_any(),
                    e.into_pyobject(py).unwrap().into_any(),
                    PyTuple::new(py, args).unwrap().into_any(),
                ],
            )
            .unwrap()
            .into_any()
        }
    }
}

fn support(py: Python<'_>) -> Bound<'_, PyModule> {
    let code = CString::new(PY_SUPPORT).unwrap();
    PyModule::from_code(py, &code, c"native_diff_support.py", c"native_diff_support").unwrap()
}

fn build_python(
    py: Python<'_>,
    m: &Bound<'_, PyModule>,
    nodes: &[Node],
    disks: &[(String, Option<usize>)],
) -> Py<PyAny> {
    let spec: Vec<Bound<'_, PyAny>> = nodes
        .iter()
        .map(|n| {
            let base = format!("{:?}", n.base);
            let mut answers: Vec<_> = n.answers.iter().collect();
            answers.sort_by_key(|(k, _)| **k);
            let answers: Vec<Bound<'_, PyAny>> = answers
                .into_iter()
                .map(|(k, a)| {
                    PyTuple::new(
                        py,
                        [k.into_pyobject(py).unwrap().into_any(), ans_to_py(py, a)],
                    )
                    .unwrap()
                    .into_any()
                })
                .collect();
            PyTuple::new(
                py,
                [
                    n.class.as_str().into_pyobject(py).unwrap().into_any(),
                    base.as_str().into_pyobject(py).unwrap().into_any(),
                    PyList::new(py, answers).unwrap().into_any(),
                ],
            )
            .unwrap()
            .into_any()
        })
        .collect();
    let chassis = m
        .getattr("build")
        .unwrap()
        .call1((PyList::new(py, spec).unwrap(),))
        .unwrap();
    let api = m.getattr("facade").unwrap().call1((chassis,)).unwrap();
    m.getattr("set_storage")
        .unwrap()
        .call1((&api, disks.to_vec()))
        .unwrap();
    api.unbind()
}

/// A disk the native hatches read: answers as the generator scripted them,
/// traced as the Python one traces its calls, and an `AttributeError` for a
/// method it was not given -- as a Python object without one raises.
struct ScriptedDisk {
    class: String,
    answers: HashMap<&'static str, Ans>,
    trace: Trace,
}

impl ScriptedDisk {
    fn ask(&self, method: &str, args: &[PyVal]) -> platform_base::PyResult<PyVal> {
        let Some(a) = self.answers.get(method) else {
            return Err(PyErr::new(
                Exc::AttributeError,
                vec![PyVal::Str(format!(
                    "'{}' object has no attribute '{method}'",
                    self.class
                ))],
            ));
        };
        self.trace.lock().unwrap().push(format!(
            "{}.{method}({})",
            self.class,
            args.iter().map(arg_repr).collect::<Vec<_>>().join(", ")
        ));
        match a {
            Ans::Val(v) => Ok(to_pyval(v, &[])),
            Ans::Raise(e, msg) => Err(PyErr::new(
                exc_of(e),
                if msg.is_empty() {
                    vec![]
                } else {
                    vec![PyVal::Str(msg.clone())]
                },
            )),
        }
    }
}

impl platform_base::storage::StorageDisk for ScriptedDisk {
    fn fetch_parse_info(&mut self, diskdev: &str) -> platform_base::PyResult<()> {
        self.ask("fetch_parse_info", &[PyVal::Str(diskdev.to_string())])
            .map(|_| ())
    }
    fn get_model(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_model", &[])
    }
    fn get_serial(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_serial", &[])
    }
    fn get_firmware(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_firmware", &[])
    }
    fn get_health(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_health", &[])
    }
    fn get_temperature(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_temperature", &[])
    }
    fn get_fs_io_reads(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_fs_io_reads", &[])
    }
    fn get_fs_io_writes(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_fs_io_writes", &[])
    }
    fn get_disk_io_reads(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_disk_io_reads", &[])
    }
    fn get_disk_io_writes(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_disk_io_writes", &[])
    }
    fn get_reserved_blocks(&self) -> platform_base::PyResult<PyVal> {
        self.ask("get_reserved_blocks", &[])
    }
}

fn build_storage(
    nodes: &[Node],
    disks: &[(String, Option<usize>)],
    trace: &Trace,
) -> platform_base::storage::StorageDevices {
    platform_base::storage::StorageDevices {
        devices: disks
            .iter()
            .map(|(name, n)| {
                let disk = n.map(|n| {
                    Box::new(ScriptedDisk {
                        class: nodes[n].class.clone(),
                        answers: nodes[n].answers.clone(),
                        trace: trace.clone(),
                    }) as Box<dyn platform_base::storage::StorageDisk>
                });
                (name.clone(), disk)
            })
            .collect(),
    }
}

fn py_trace(py: Python<'_>, m: &Bound<'_, PyModule>) -> Vec<String> {
    let t = m.getattr("TRACE").unwrap();
    let out: Vec<String> = t.extract().unwrap();
    t.call_method0("clear").unwrap();
    let _ = py;
    out
}

// ── the calls ───────────────────────────────────────────────────────────────

/// Keys that reach each kind of addressed device, positions past the end, a
/// provider's devices, and keys that do not parse.
const KEYS: &[&str] = &[
    "fan_drawers[0]/fans[0]",
    "fan_drawers[0]/fans[1]",
    "fan_drawers[1]/fans[1]",
    "fan_drawers[2]/fans[0]",
    "fan_drawers[0]",
    "fan_drawers[1]",
    "modules[0]/fans[0]",
    "modules[1]/fans[1]",
    "psus[0]/fans[0]",
    "psus[1]/fans[1]",
    "pdbs[0]/fans[0]",
    "psus[0]",
    "psus[1]",
    "pdbs[0]",
    "modules[0]",
    "modules[1]",
    "modules[2]",
    "components[0]",
    "components[1]",
    "modules[0]/components[0]",
    "modules[1]/components[1]",
    "voltage_sensors[0]",
    "current_sensors[0]",
    "modules[0]/voltage_sensors[0]",
    "modules[0]/current_sensors[0]",
    "voltage_sensors_from_yaml[0]",
    "fan_drawers[0]/psus[0]",
    "fans[0]",
    "x",
    "",
    "/",
    "fan_drawers[01]/fans[0]",
    "fan_drawers[-1]",
    "fan_drawers[0]/",
    "Fan_drawers[0]",
];

/// What `get_thermals` is told to read only in part: thermals of every
/// source, one past the end, and keys of nothing.
const SKIP: &[&str] = &[
    "thermals[0]",
    "psus[0]/thermals[1]",
    "pdbs[0]/thermals[0]",
    "modules[1]/thermals[0]",
    "modules[0]/psus[0]/thermals[0]",
    "thermals[9]",
    "fans[0]",
    "x",
];

/// Every method, with arguments that hit and miss, as (label, Debug of answer).
fn calls<P: PlatformApi>(
    p: &mut P,
    mut after: impl FnMut(&str) -> Vec<String>,
) -> Vec<(String, String, Vec<String>)> {
    let mut out = Vec::new();
    macro_rules! c {
        ($label:expr, $e:expr) => {{
            let r = format!("{:?}", $e);
            let label = $label.to_string();
            let t = after(&label);
            out.push((label, r, t));
        }};
    }
    c!("chassis ALL", p.get_chassis_info(ChassisInfoCols::ALL));
    c!("chassis NONE", p.get_chassis_info(ChassisInfoCols::NONE));
    c!(
        "chassis some",
        p.get_chassis_info(
            ChassisInfoCols::REBOOT_CAUSE
                .with(ChassisInfoCols::IS_SMARTSWITCH)
                .with(ChassisInfoCols::MODEL)
        )
    );
    c!("modules ALL", p.get_modules(ModuleInfoCols::ALL));
    c!("modules NONE", p.get_modules(ModuleInfoCols::NONE));
    // Skipped keys read only the unguarded columns; one never answered, and
    // one that is not a key at all, read nothing differently.
    let skip: Vec<DeviceKey> = SKIP.iter().map(|k| DeviceKey::from(*k)).collect();
    c!("thermals ALL", p.get_thermals(ThermalInfoCols::ALL, &[]));
    c!("thermals NONE", p.get_thermals(ThermalInfoCols::NONE, &[]));
    c!("thermals skip", p.get_thermals(ThermalInfoCols::ALL, &skip));
    c!(
        "thermals some",
        p.get_thermals(
            ThermalInfoCols::TEMPERATURE
                .with(ThermalInfoCols::HIGH_THRESHOLD)
                .with(ThermalInfoCols::POSITION_IN_PARENT),
            &skip
        )
    );
    c!(
        "thermals no temperature",
        p.get_thermals(
            ThermalInfoCols::HIGH_THRESHOLD.with(ThermalInfoCols::MAX_RECORDED),
            &[]
        )
    );
    c!("fans ALL", p.get_fans(FanInfoCols::ALL, false));
    c!("fans NONE", p.get_fans(FanInfoCols::NONE, false));
    c!(
        "fans some",
        p.get_fans(
            FanInfoCols::PRESENCE
                .with(FanInfoCols::SPEED_PCT)
                .with(FanInfoCols::IS_UNDER_SPEED),
            false
        )
    );
    // psud's way: each column on its own.
    c!("fans ALL absorbed", p.get_fans(FanInfoCols::ALL, true));
    c!(
        "fans psud absorbed",
        p.get_fans(
            FanInfoCols::PRESENCE
                .with(FanInfoCols::SPEED_PCT)
                .with(FanInfoCols::DIRECTION),
            true
        )
    );
    c!("drawers ALL", p.get_fan_drawers(FanDrawerInfoCols::ALL));
    c!("drawers NONE", p.get_fan_drawers(FanDrawerInfoCols::NONE));
    c!("psus", p.get_psus());
    c!("components", p.get_components());
    c!("sensors", p.get_sensors());
    c!("leak profiles", p.get_leak_profiles());
    c!("leak sensors", p.get_leak_sensors());
    c!("eeprom", p.get_eeprom());
    c!("bmcs", p.get_bmcs());
    c!("watchdogs", p.get_watchdogs());
    for n in NAMES {
        c!(format!("module key {n}"), p.get_module_key(n));
        c!(format!("component key {n}"), p.get_component_key(n));
        for m in NAMES {
            c!(
                format!("module component key {m} {n}"),
                p.get_module_component_key(m, n)
            );
        }
    }
    for k in KEYS {
        let n = &DeviceKey::from(*k);
        c!(format!("set_fan_led {n}"), p.set_fan_led(n, LedColor::Red));
        c!(format!("set_fan_speed {n}"), p.set_fan_speed(n, 55));
        c!(
            format!("set_fan_drawer_led {n}"),
            p.set_fan_drawer_led(n, LedColor::Green)
        );
        c!(format!("set_psu_led {n}"), p.set_psu_led(n, LedColor::Off));
        c!(format!("get_psu_master_led {n}"), p.get_psu_master_led(n));
        c!(
            format!("set_psu_master_led {n}"),
            p.set_psu_master_led(n, LedColor::Green)
        );
        c!(
            format!("get_psu_master_led again {n}"),
            p.get_psu_master_led(n)
        );
        c!(
            format!("module reboot cause {n}"),
            p.get_module_reboot_cause(n)
        );
        c!(
            format!("module midplane reason {n}"),
            p.get_module_midplane_down_reason(n)
        );
        c!(format!("reboot_module {n}"), p.reboot_module(n, "cold"));
        c!(format!("admin {n}"), p.set_module_admin_state(n, true));
        c!(
            format!("admin down {n}"),
            p.set_module_admin_state(n, false)
        );
        c!(
            format!("admin graceful {n}"),
            p.set_module_admin_state_gracefully(n, false)
        );
        c!(format!("power cycle {n}"), p.power_cycle_module(n));
        c!(format!("pre {n}"), p.module_pre_shutdown(n));
        c!(format!("post {n}"), p.module_post_startup(n));
        c!(
            format!("set transition {n}"),
            p.set_module_state_transition(n, "shutdown")
        );
        c!(
            format!("clear transition {n}"),
            p.clear_module_state_transition(n)
        );
        c!(format!("gnoi {n}"), p.clear_module_gnoi_halt(n));
        c!(
            format!("sensor high {n}"),
            p.set_sensor_high_threshold(n, Threshold::Int(90))
        );
        c!(
            format!("sensor low {n}"),
            p.set_sensor_low_threshold(n, Threshold::Float(1.5))
        );
        c!(
            format!("fw avail {n}"),
            p.get_available_firmware_version(n, "/img")
        );
        c!(
            format!("fw notif {n}"),
            p.get_firmware_update_notification(n, "/img")
        );
        c!(format!("fw install {n}"), p.install_firmware(n, "/img"));
        c!(format!("fw update {n}"), p.update_firmware(n, "/img"));
        c!(
            format!("fw auto {n}"),
            p.auto_update_firmware(n, "/img", "cold")
        );
    }
    c!("arm", p.arm_watchdog(30));
    c!("disarm", p.disarm_watchdog());
    c!("init system led", p.initialize_system_led());
    c!("init midplane", p.init_midplane_switch());
    c!("chassis led", p.set_chassis_led("amber_blink"));
    c!("sed change", p.change_sed_password("pw"));
    c!("sed reset", p.reset_sed_password());
    c!("asics", p.get_asics());
    c!("change event", p.get_change_event(1000));
    c!("bmc open", p.bmc_open_session());
    c!("bmc close", p.bmc_close_session("sid"));
    c!("bmc rootpw", p.bmc_reset_root_password());
    c!("bmc reset", p.bmc_reset(true));
    c!("bmc fw", p.bmc_update_firmware("/fw"));
    c!("bmc dump", p.bmc_trigger_debug_log_dump());
    c!("bmc get dump", p.bmc_get_debug_log_dump("t1", "f", "/p"));
    c!("tm interval before", p.tm_get_interval());
    c!("tm run before", p.tm_run_policy());
    c!("tm stop before", p.tm_stop());
    c!("tm init", p.tm_initialize());
    c!("tm interval", p.tm_get_interval());
    c!("tm run", p.tm_run_policy());
    c!("tm stop", p.tm_stop());
    c!("tm deinit", p.tm_deinitialize());
    c!("storage", p.get_storage_devices());
    c!("storage again", p.get_storage_devices());
    c!("eeprom update", p.eeprom_update_db());
    c!("eeprom update again", p.eeprom_update_db());
    out
}

static NATIVE_SHUTDOWNS: AtomicUsize = AtomicUsize::new(0);

fn native_vendor_shutdown() {
    NATIVE_SHUTDOWNS.fetch_add(1, Ordering::SeqCst);
    panic!("the vendor's shutdown hook failed");
}

/// `notify_shutdown()` with a vendor whose shutdown handler records and then
/// fails: on both sides it runs once, whichever handle asks and however
/// often, as SIGTERM, and every call answers `Ok`.  The Python handler is
/// put where the bridge keeps the one it captured.  Once per process on both
/// sides, so run once, before the seeds -- whose calls never notify.
fn compare_shutdown(failures: &mut Vec<String>) {
    const VENDOR: &std::ffi::CStr = pyo3::ffi::c_str!(
        "import signal\n\
         from sonic_platform_api import _escape_hatch\n\
         RUNS = []\n\
         def handler(signum, frame):\n\
         \x20   RUNS.append((signum, frame))\n\
         \x20   raise RuntimeError(\"the vendor's shutdown handler failed\")\n\
         _escape_hatch._shutdown_handlers[signal.SIGTERM] = handler\n"
    );
    let (py_answers, py_runs) = Python::with_gil(|py| {
        let m = PyModule::from_code(
            py,
            VENDOR,
            pyo3::ffi::c_str!("vend.py"),
            pyo3::ffi::c_str!("vend_shutdown"),
        )
        .unwrap();
        let facade = |py: Python<'_>| {
            let f = py
                .import("sonic_platform_api.facade")
                .unwrap()
                .getattr("PlatformApi")
                .unwrap()
                .call1((py.None(),))
                .unwrap();
            platform_pyo3::Bridge::from_facade(f.unbind())
        };
        let (mut a, mut b) = (facade(py), facade(py));
        let answers = vec![
            a.notify_shutdown(),
            a.notify_shutdown(),
            b.notify_shutdown(),
        ];
        let runs: Vec<(i32, Option<i32>)> = m.getattr("RUNS").unwrap().extract().unwrap();
        (answers, runs)
    });
    let mut a = BaseFacade::new(
        PyVal::None,
        EscapeHatches::new().on_shutdown(native_vendor_shutdown),
    );
    let mut b = BaseFacade::new(
        PyVal::None,
        EscapeHatches::new().on_shutdown(native_vendor_shutdown),
    );
    let rs_answers = vec![
        a.notify_shutdown(),
        a.notify_shutdown(),
        b.notify_shutdown(),
    ];
    if py_answers != rs_answers {
        failures.push(format!(
            "notify_shutdown:\n  python: {py_answers:?}\n  native: {rs_answers:?}"
        ));
    }
    if py_runs != [(libc::SIGTERM, None)] || NATIVE_SHUTDOWNS.load(Ordering::SeqCst) != 1 {
        failures.push(format!(
            "notify_shutdown ran the vendor's handler:\n  python: {py_runs:?}\n  native: {} time(s)",
            NATIVE_SHUTDOWNS.load(Ordering::SeqCst)
        ));
    }
}

#[test]
fn the_native_facade_answers_what_the_python_facade_and_bridge_answer() {
    let mut failures = Vec::new();
    compare_shutdown(&mut failures);
    let seeds: u64 = std::env::var("DIFF_SEEDS")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(300);
    // What the scenarios must have reached somewhere, or the comparison of
    // those paths proves nothing: (what, found in this label, this text).
    let mut reached: Vec<(&str, &str, &str, bool)> = vec![
        (
            "a disk whose refresh raised",
            "storage",
            "error: Some(",
            false,
        ),
        (
            "a disk whose model or serial raised",
            "storage",
            "static_error: Some(",
            false,
        ),
        (
            "a fan that failed, by column",
            "fans ALL",
            "error_column: Some(",
            false,
        ),
        (
            "an EEPROM that would not read",
            "eeprom update",
            "ReadFailed",
            false,
        ),
        (
            "an EEPROM that would not write",
            "eeprom update",
            "UpdateFailed",
            false,
        ),
        ("an EEPROM that did", "eeprom update", "Updated", false),
        (
            "an absent fan, read per row",
            "fans ALL",
            "presence: false, speed_pct: None",
            false,
        ),
        (
            "an absent fan, read absorbing",
            "fans ALL absorbed",
            "presence: false",
            false,
        ),
        (
            "an integral reading",
            "thermals ALL",
            "temperature: Some(Int(",
            false,
        ),
        (
            "a fractional reading",
            "thermals ALL",
            "temperature: Some(Float(",
            false,
        ),
    ];
    let mut admin_ints = false;
    for seed in 0..seeds {
        let g = Gen::chassis(seed);

        // Python first: its constructors and ours both reset the PSU master
        // LED, so each tree is built right before it is read.
        let (py_results, rs_results) = Python::with_gil(|py| {
            let m = support(py);
            let facade = build_python(py, &m, &g.nodes, &g.disks);
            py_trace(py, &m);
            let mut bridge = platform_pyo3::Bridge::from_facade(facade);
            let py_results = calls(&mut bridge, |_| py_trace(py, &m));

            let trace: Trace = Arc::new(Mutex::new(Vec::new()));
            let chassis = build_rust(&g.nodes, &trace);
            let storage = build_storage(&g.nodes, &g.disks, &trace);
            let mut native = BaseFacade::new(chassis, EscapeHatches::with_storage(storage));
            let rs_results = calls(&mut native, |_| std::mem::take(&mut *trace.lock().unwrap()));
            (py_results, rs_results)
        });

        for (label, py, pt) in &py_results {
            for r in reached.iter_mut() {
                if label.as_str() == r.1 && py.contains(r.2) {
                    r.3 = true;
                }
            }
            admin_ints |= pt.iter().any(|t| t.contains(".set_admin_state(1)"));
        }
        for ((label, py, pt), (_, rs, rt)) in py_results.iter().zip(&rs_results) {
            if py != rs {
                failures.push(format!(
                    "seed {seed} {label}:\n  python: {py}\n  native: {rs}"
                ));
            } else if pt != rt {
                failures.push(format!(
                    "seed {seed} {label}: same answer, different calls:\n  python: {pt:?}\n  native: {rt:?}"
                ));
            }
        }
        if failures.len() > 20 {
            break;
        }
    }
    assert!(
        failures.is_empty(),
        "{} differences:\n{}",
        failures.len(),
        failures.join("\n")
    );
    if seeds >= 300 {
        let missed: Vec<_> = reached.iter().filter(|r| !r.3).map(|r| r.0).collect();
        assert!(missed.is_empty(), "no scenario reached: {missed:?}");
        assert!(admin_ints, "no scenario handed a module its admin state");
    }
}
