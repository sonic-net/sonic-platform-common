//
// SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
// Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//! The generated bridge against the generated facade, over a mock chassis.
//!
//! Both sides of the boundary come from the one stub, so what these tests
//! actually check is that the two projections agree: that a column the facade
//! normalised to None arrives as None, that a name the facade resolved is the
//! name an action can address, and that a Python exception becomes the Rust
//! variant a caller can act on.
//!
//! Requires `PYTHONPATH` to include the repository root, so that
//! `platform_api.facade` imports.  `cargo test` from the crate directory will
//! not find it on its own; see generator/check.sh.

use platform_api::{LedColor, PlatformApi, PlatformError};
use platform_pyo3::Bridge;
use pyo3::ffi::c_str;
use pyo3::prelude::*;
use pyo3::types::PyModule;

/// A chassis that misbehaves the way shipped ones do: a PSU that is not
/// present, no PDBs at all, a sensor reporting 'N/A', another reporting a
/// number as a string, and a thermal with no name.
const MOCK: &std::ffi::CStr = c_str!(
    r#"
class Thermal:
    def __init__(self, name, temp, high=None, low=None):
        self._name, self._temp = name, temp
        self._high, self._low = high, low
    def get_high_threshold(self):
        return self._high
    def get_low_threshold(self):
        return self._low
    def get_name(self):
        if self._name is None:
            raise NotImplementedError
        return self._name
    def get_temperature(self):
        return self._temp
    def is_replaceable(self):
        raise NotImplementedError

class Fan:
    def __init__(self, name):
        self._name = name
        self.led = None
    def get_name(self):
        return self._name
    def get_speed(self):
        return 50.0            # a whole number, as a float
    def get_direction(self):
        return 'N/A'           # FAN_DIRECTION_NOT_APPLICABLE: a value
    def set_status_led(self, color):
        self.led = color
        return True

class Drawer:
    def __init__(self, name, fans):
        self._name, self._fans = name, fans
    def get_name(self):
        return self._name
    def get_all_fans(self):
        return self._fans

class Psu:
    def __init__(self, name, present, thermals):
        self._name, self._present, self._thermals = name, present, thermals
    def get_name(self):
        return self._name
    def get_presence(self):
        return self._present
    def get_all_thermals(self):
        return self._thermals
    def get_all_fans(self):
        return []

class Module:
    def __init__(self, name):
        self._name = name
        self.rebooted = None
    def get_name(self):
        return self._name
    def get_type(self):
        return 'LINE-CARD'
    def get_oper_status(self):
        return 'Online'
    def get_reboot_cause(self):
        return ('Software', 'requested')
    def is_midplane_reachable(self):
        return NotImplementedError     # the class, not a raise
    def reboot(self, reboot_type):
        self.rebooted = reboot_type
        return True
    def get_all_thermals(self):
        return []
    def get_all_psus(self):
        return []
    def get_all_fans(self):
        return []

class Chassis:
    def __init__(self):
        self.fan = Fan('fan 1')
        self.drawer = Drawer('drawer 1', [self.fan])
        self._psus = [Psu('PSU-1', True, [Thermal(None, '51')]),
                      Psu('PSU-2', False, [Thermal('hidden', 1.0)])]
        self.led = None
        self.module = Module('LC1')
    def get_reboot_cause(self):
        return ('Watchdog', 'counted down')
    def get_my_slot(self):
        return NotImplementedError     # the class, not a raise
    def get_change_event(self, timeout=0):
        return (True, {'fan': {'2': '1'}, 'sfp': {'11': '0', '12': '9'}})
    def get_all_thermals(self):
        return [Thermal('ASIC', 42.5, 105, -5.0),   # int and float limits
                Thermal('CPU', 'N/A'),
                Thermal('ODD', 1.0, True)]     # a bool where a limit belongs
    def get_all_psus(self):
        return self._psus
    def get_all_pdbs(self):
        raise NotImplementedError
    def get_all_modules(self):
        return [self.module]
    def get_all_fan_drawers(self):
        return [self.drawer]
    def is_modular_chassis(self):
        return True
    def set_status_led(self, color):
        self.led = color
        return True

CHASSIS = Chassis()
"#
);

/// A chassis that answers every accessor, so that every generated reader runs.
///
/// The readers are a mechanical projection of the stub, but a column name is a
/// string the bridge hands to `getattr`: a wrong one fails at run time on
/// hardware and nowhere earlier. Exercising each of them here is what turns
/// that into a test failure.
const LOADED: &std::ffi::CStr = c_str!(
    r#"
class Dev:
    def __init__(self, name, **kw):
        self._name = name
        for k, v in kw.items():
            setattr(self, '_' + k, v)
    def get_name(self):
        return self._name
    def get_presence(self):
        return True
    def get_status(self):
        return True
    def is_replaceable(self):
        return True
    def get_position_in_parent(self):
        return 1
    def get_model(self):
        return 'M'
    def get_serial(self):
        return 'S'
    def get_revision(self):
        return 'R'

class Psu(Dev):
    def get_powergood_status(self):
        return True
    def get_voltage(self):
        return 12.0
    def get_current(self):
        return 3.0
    def get_power(self):
        return 36.0
    def get_temperature(self):
        return 40.0
    def get_temperature_high_threshold(self):
        return 70
    def get_status_led(self):
        return 'green'
    def get_all_fans(self):
        return []
    def get_all_thermals(self):
        return []

class Sensor(Dev):
    def get_value(self):
        return 3300
    def get_unit(self):
        return 'mV'
    def get_high_threshold(self):
        return 3600

class Component(Dev):
    def get_description(self):
        return 'BIOS'
    def get_firmware_version(self):
        return '1.2'

class Watchdog:
    def is_armed(self):
        return True
    def get_remaining_time(self):
        return 42

class Bmc(Dev):
    def get_version(self):
        return '4.5'
    def get_eeprom(self):
        return {'Model': 'BF3'}

class Profile:
    def get_type(self):
        return 'rack'
    def get_leak_max_minor_duration_sec(self):
        return 30

class LeakSensor(Dev):
    def is_leak(self):
        return False
    def is_leak_sensor_ok(self):
        return True
    def get_leak_severity(self):
        return 'MINOR'
    def get_leak_sensor_type(self):
        return 'rope'
    def get_leak_sensor_location(self):
        return 'rear'
    def get_leak_profile(self):
        return Profile()

class LiquidCooling:
    def get_all_leak_sensors(self):
        return [LeakSensor('leak-1')]
    def get_all_profiles(self):
        return [Profile()]

class Drawer(Dev):
    def get_all_fans(self):
        return [Dev('fan-1')]
    def get_status_led(self):
        return 'green'
    def get_maximum_consumed_power(self):
        return 20.0

class Module(Dev):
    def get_type(self):
        return 'LINE-CARD'
    def get_oper_status(self):
        return 'Online'
    def get_all_asics(self):
        return [('4', '0000:05:00.0')]
    def get_system_eeprom_info(self):
        return {'0x22': 'LC'}
    def get_all_thermals(self):
        return []
    def get_all_psus(self):
        return []
    def get_all_fans(self):
        return []
    def get_all_components(self):
        return [Component('LC-CPLD')]
    def get_all_voltage_sensors(self):
        return [Sensor('lc-v')]
    def get_all_current_sensors(self):
        return []

class Loaded:
    def __init__(self):
        self.watchdog = Watchdog()
    def is_modular_chassis(self):
        return True
    def get_all_thermals(self):
        return []
    def get_all_psus(self):
        return [Psu('PSU-1')]
    def get_all_pdbs(self):
        return [Psu('PDB-1')]
    def get_all_modules(self):
        return [Module('LC1')]
    def get_all_fan_drawers(self):
        return [Drawer('D1')]
    def get_all_components(self):
        return [Component('BIOS')]
    def get_all_voltage_sensors(self):
        return [Sensor('sys-v')]
    def get_all_current_sensors(self):
        return [Sensor('sys-c')]
    def get_system_eeprom_info(self):
        return {'0x21': 'MSN4700'}
    def get_liquid_cooling(self):
        return LiquidCooling()
    def get_bmc(self):
        return Bmc('BMC')
    def get_watchdog(self):
        return self.watchdog
    def get_reboot_cause(self):
        return ('Watchdog', 'timed out')

CHASSIS = Loaded()
"#
);

fn loaded() -> Bridge {
    Python::with_gil(|py| {
        let m = PyModule::from_code(py, LOADED, c_str!("loaded.py"), c_str!("loaded")).unwrap();
        let chassis = m.getattr("CHASSIS").unwrap();
        let facade = py
            .import("platform_api.facade")
            .expect("PYTHONPATH must include the repository root")
            .getattr("PlatformApi")
            .unwrap()
            .call1((&chassis,))
            .unwrap();
        Bridge::from_facade(facade.unbind())
    })
}

fn bridge() -> (Bridge, Py<PyAny>) {
    Python::with_gil(|py| {
        let m = PyModule::from_code(py, MOCK, c_str!("mock.py"), c_str!("mock")).unwrap();
        let chassis = m.getattr("CHASSIS").unwrap();
        let facade = py
            .import("platform_api.facade")
            .expect("PYTHONPATH must include the repository root")
            .getattr("PlatformApi")
            .unwrap()
            .call1((&chassis,))
            .unwrap();
        (Bridge::from_facade(facade.unbind()), chassis.unbind())
    })
}

#[test]
fn a_sentinel_arrives_as_absent_and_a_string_arrives_as_a_number() {
    let (mut api, _chassis) = bridge();
    let rows = api.get_thermals().unwrap();

    let asic = rows.iter().find(|r| r.name == "ASIC").unwrap();
    assert_eq!(asic.temperature, Some(42.5));

    let cpu = rows.iter().find(|r| r.name == "CPU").unwrap();
    assert_eq!(cpu.temperature, None, "'N/A' is a missing reading");

    // The PSU's thermal has no name, so the facade gave it the key its
    // consumers publish, and the number it reported as a string is a number.
    let psu = rows.iter().find(|r| r.parent_name == "PSU-1").unwrap();
    assert_eq!(psu.name, "PSU-1 Thermal 1");
    assert_eq!(psu.temperature, Some(51.0));
}

#[test]
fn an_absent_psu_and_a_platform_with_no_pdbs_are_both_quiet() {
    let (mut api, _chassis) = bridge();
    let rows = api.get_thermals().unwrap();
    assert!(rows.iter().all(|r| r.name != "hidden"));
    assert_eq!(rows.len(), 4, "chassis 3 + present PSU 1, no PDBs");
}

#[test]
fn a_field_with_a_declared_default_does_not_arrive_as_a_hole() {
    // Thermal.is_replaceable raises; the stub declares the default.
    let (mut api, _chassis) = bridge();
    assert!(!api.get_thermals().unwrap()[0].is_replaceable);
}

#[test]
fn a_whole_number_reported_as_a_float_still_fits_the_declared_width() {
    let (mut api, _chassis) = bridge();
    assert_eq!(api.get_fans().unwrap()[0].speed_pct, Some(50));
}

#[test]
fn fan_direction_na_crosses_as_a_value() {
    use platform_api::FanDirection;
    let (mut api, _chassis) = bridge();
    assert_eq!(api.get_fans().unwrap()[0].direction, Some(FanDirection::NA));
}

#[test]
fn an_action_addresses_the_row_by_the_name_the_snapshot_published() {
    let (mut api, chassis) = bridge();
    let name = api.get_fans().unwrap()[0].name.clone();
    api.set_fan_led(&name, LedColor::Amber).unwrap();

    Python::with_gil(|py| {
        let led = chassis
            .bind(py)
            .getattr("fan")
            .unwrap()
            .getattr("led")
            .unwrap();
        assert_eq!(led.extract::<String>().unwrap(), "amber");
    });
}

#[test]
fn an_unknown_row_name_is_not_found_rather_than_a_backend_failure() {
    let (mut api, _chassis) = bridge();
    match api.set_fan_led("nope", LedColor::Red) {
        Err(PlatformError::NotFound(_)) => {}
        other => panic!("expected NotFound, got {other:?}"),
    }
}

#[test]
fn something_the_platform_does_not_implement_is_not_supported() {
    // The mock has no set_speed on its fan, so the facade raises
    // NotImplementedError; a caller must be able to tell that from a fault.
    let (mut api, _chassis) = bridge();
    let name = api.get_fans().unwrap()[0].name.clone();
    match api.set_fan_speed(&name, 30) {
        Err(PlatformError::NotSupported(_)) => {}
        other => panic!("expected NotSupported, got {other:?}"),
    }
}

#[test]
fn a_chassis_level_action_needs_no_row() {
    let (mut api, chassis) = bridge();
    api.set_chassis_led(LedColor::Green).unwrap();
    Python::with_gil(|py| {
        let led = chassis.bind(py).getattr("led").unwrap();
        assert_eq!(led.extract::<String>().unwrap(), "green");
    });
}

#[test]
fn a_platform_without_a_thermal_manager_is_quiet() {
    let (mut api, _chassis) = bridge();
    api.tm_initialize().unwrap();
    api.tm_run_policy().unwrap();
    assert_eq!(api.tm_get_interval().unwrap(), None);
    api.tm_deinitialize().unwrap();
}


#[test]
fn the_chassis_crosses_as_one_row() {
    let (mut api, _chassis) = bridge();
    let info = api.get_chassis_info().unwrap();
    assert_eq!(info.reboot_cause.as_deref(), Some("Watchdog"));
    assert_eq!(info.reboot_cause_detail.as_deref(), Some("counted down"));
    assert!(info.is_modular_chassis);
    assert!(!info.is_smartswitch, "a predicate nobody answered is a no");
}

#[test]
fn returning_the_exception_class_crosses_as_absent() {
    // Five base-class methods `return NotImplementedError` rather than
    // raising it.  It is truthy, so an unguarded bridge would publish it.
    let (mut api, _chassis) = bridge();
    assert_eq!(api.get_chassis_info().unwrap().my_slot, None);
    assert_eq!(api.get_modules().unwrap()[0].is_midplane_reachable, None);
}

#[test]
fn a_module_carries_the_strings_the_base_class_defines() {
    use platform_api::{ModuleStatus, ModuleType};
    let (mut api, _chassis) = bridge();
    let m = &api.get_modules().unwrap()[0];
    assert_eq!(m.name, "LC1");
    assert_eq!(m.r#type, Some(ModuleType::LineCard));
    assert_eq!(m.oper_status, Some(ModuleStatus::Online));
}

#[test]
fn a_module_action_reaches_the_module() {
    let (mut api, chassis) = bridge();
    api.reboot_module("LC1", "DPU").unwrap();
    Python::with_gil(|py| {
        let v = chassis
            .bind(py)
            .getattr("module")
            .unwrap()
            .getattr("rebooted")
            .unwrap();
        assert_eq!(v.extract::<String>().unwrap(), "DPU");
    });
}

#[test]
fn a_two_level_mapping_crosses_as_rows() {
    use platform_api::ChangeEventKind;
    let (mut api, _chassis) = bridge();
    let batch = api.get_change_event(100).unwrap();
    assert!(batch.ok);
    let mut seen: Vec<_> = batch
        .events
        .iter()
        .map(|e| (e.device_type.as_str(), e.device_id.as_str(), e.kind))
        .collect();
    seen.sort();
    assert_eq!(
        seen,
        vec![
            ("fan", "2", Some(ChangeEventKind::Inserted)),
            ("sfp", "11", Some(ChangeEventKind::Removed)),
            // A status outside the seven documented ones keeps its raw value
            // and names no kind.
            ("sfp", "12", None),
        ]
    );
    assert_eq!(
        batch.events.iter().find(|e| e.device_id == "12").unwrap().status,
        "9"
    );
}

#[test]
fn a_limit_keeps_the_side_of_the_union_it_arrived_on() {
    use platform_api::Threshold;
    // `show platform temperature` reads these back as strings, so 105 and
    // 105.0 are different answers and the boundary must not rewrite one.
    let (mut api, _chassis) = bridge();
    let rows = api.get_thermals().unwrap();
    let asic = rows.iter().find(|r| r.name == "ASIC").unwrap();
    assert_eq!(asic.high_threshold, Some(Threshold::Int(105)));
    assert_eq!(asic.low_threshold, Some(Threshold::Float(-5.0)));
    let cpu = rows.iter().find(|r| r.name == "CPU").unwrap();
    assert_eq!(cpu.high_threshold, None);
}

#[test]
fn a_bool_is_not_a_limit() {
    // bool is a subclass of int in Python, so `isinstance(True, int)` holds and
    // an unguarded reader would publish the threshold 1. The facade drops it
    // first -- a flag where a number is declared is bad data, not the number
    // one -- so what crosses is absence. The bridge keeps its own guard for a
    // caller that wired it to something other than the generated facade.
    let (mut api, _chassis) = bridge();
    let rows = api.get_thermals().unwrap();
    let odd = rows.iter().find(|r| r.name == "ODD").unwrap();
    assert_eq!(odd.high_threshold, None);
}


// -- every generated reader, against a chassis that answers ----------------

#[test]
fn every_row_type_crosses() {
    use platform_api::{PowerEntityKind, SensorKind};
    let mut api = loaded();

    let psus = api.get_psus().unwrap();
    assert_eq!(
        psus.iter().map(|p| (p.name.as_str(), p.kind)).collect::<Vec<_>>(),
        vec![("PSU-1", PowerEntityKind::Psu), ("PDB-1", PowerEntityKind::Pdb)]
    );
    assert_eq!(psus[0].voltage, Some(12.0));
    assert!(psus[0].power_good);

    let sensors = api.get_sensors().unwrap();
    assert_eq!(
        sensors.iter().map(|s| (s.name.as_str(), s.kind)).collect::<Vec<_>>(),
        vec![
            ("sys-v", SensorKind::Voltage),
            ("lc-v", SensorKind::Voltage),
            ("sys-c", SensorKind::Current),
        ]
    );
    assert_eq!(sensors[0].unit.as_deref(), Some("mV"));

    let components = api.get_components().unwrap();
    assert_eq!(
        components.iter().map(|c| c.name.as_str()).collect::<Vec<_>>(),
        vec!["BIOS", "LC-CPLD"]
    );
    assert_eq!(components[0].firmware_version.as_deref(), Some("1.2"));

    let drawers = api.get_fan_drawers().unwrap();
    assert_eq!(drawers[0].name, "D1");
    assert_eq!(drawers[0].maximum_consumed_power, Some(20.0));

    let eeprom = api.get_eeprom().unwrap();
    assert_eq!(
        eeprom.iter().map(|e| (e.source.as_str(), e.code.as_str())).collect::<Vec<_>>(),
        vec![("chassis", "0x21"), ("module", "0x22"), ("bmc", "Model")]
    );

    let bmcs = api.get_bmcs().unwrap();
    assert_eq!(bmcs.len(), 1);
    assert_eq!(bmcs[0].version.as_deref(), Some("4.5"));

    let watchdogs = api.get_watchdogs().unwrap();
    assert_eq!((watchdogs[0].is_armed, watchdogs[0].remaining_time), (Some(true), Some(42)));

    let asics = api.get_asics().unwrap();
    assert_eq!(
        (asics[0].asic_id.as_str(), asics[0].pci_address.as_deref()),
        ("4", Some("0000:05:00.0"))
    );
}

#[test]
fn a_leak_sensor_reaches_through_its_profile() {
    use platform_api::LeakSeverity;
    let mut api = loaded();

    let profiles = api.get_leak_profiles().unwrap();
    assert_eq!((profiles[0].r#type.as_str(), profiles[0].max_minor_duration_sec), ("rack", Some(30)));

    let sensors = api.get_leak_sensors().unwrap();
    let s = &sensors[0];
    assert_eq!(s.name, "leak-1");
    assert_eq!((s.is_leak, s.is_ok), (Some(false), Some(true)));
    assert_eq!(s.severity, Some(LeakSeverity::Minor));
    assert_eq!(s.sensor_type.as_deref(), Some("rope"));
    // Two hops: the sensor's profile, then the profile's own columns.
    assert_eq!(s.profile_type.as_deref(), Some("rack"));
    assert_eq!(s.profile_max_minor_duration_sec, Some(30));
}

#[test]
fn the_chassis_row_carries_what_the_platform_answered() {
    let mut api = loaded();
    let info = api.get_chassis_info().unwrap();
    assert!(info.is_modular_chassis);
    assert_eq!(info.reboot_cause.as_deref(), Some("Watchdog"));
    assert_eq!(info.reboot_cause_detail.as_deref(), Some("timed out"));
}

#[test]
fn a_component_firmware_query_crosses_with_its_argument() {
    let mut api = loaded();
    // The mock has no such method, so this is the not-supported path -- which
    // is the one a caller has to be able to tell from a real answer.
    match api.get_available_firmware_version("BIOS", "/tmp/fw.bin") {
        Err(PlatformError::NotSupported(_)) => {}
        other => panic!("expected NotSupported, got {other:?}"),
    }
}

// -- every action, and what it marshals ------------------------------------
//
// The method names cannot mismatch: both sides come from the one stub. What
// can go wrong is the marshalling -- an enum that crossed as a Debug string, a
// limit that lost which side of the union it was on, a bool that arrived as 1.

const RECORDER: &std::ffi::CStr = c_str!(
    r#"
class Rec:
    def __init__(self, name):
        self._name = name
        self.calls = []
    def get_name(self):
        return self._name
    def get_presence(self):
        return True
    def reset(self):
        # The row builders call every getter on the way past; an assertion
        # about an action wants only what happened after it was made.
        self.calls = []
    def __getattr__(self, attr):
        if attr.startswith('_') or attr.startswith('get_all') or attr == 'reset':
            raise AttributeError(attr)
        def call(*args):
            self.calls.append((attr, args))
            return True
        return call

class Psu(Rec):
    # The catch-all answers True, which is not a colour; this one is read back
    # as one, so it has to answer like a platform.
    def get_status_master_led(self):
        self.calls.append(('get_status_master_led', ()))
        return 'green'

class Chassis(Rec):
    def __init__(self):
        Rec.__init__(self, 'chassis 1')
        self.fan = Rec('fan-1')
        self.drawer = Rec('D1')
        self.psu = Psu('P1')
        self.module = Rec('M1')
        self.component = Rec('C1')
        self.sensor = Rec('v1')
        self.watchdog = Rec('wd')
        self.sed = Rec('sed')
    def get_all_fan_drawers(self):
        self.drawer.get_all_fans = lambda: [self.fan]
        return [self.drawer]
    def get_all_psus(self):
        self.psu.get_all_fans = lambda: []
        self.psu.get_all_thermals = lambda: []
        return [self.psu]
    def get_all_pdbs(self):
        raise NotImplementedError
    def get_all_modules(self):
        for k in ('get_all_fans', 'get_all_thermals', 'get_all_psus',
                  'get_all_components', 'get_all_voltage_sensors',
                  'get_all_current_sensors'):
            setattr(self.module, k, lambda: [])
        return [self.module]
    def get_all_thermals(self):
        return []
    def get_all_components(self):
        return [self.component]
    def get_all_voltage_sensors(self):
        return [self.sensor]
    def get_all_current_sensors(self):
        return []
    def is_modular_chassis(self):
        return True
    def get_watchdog(self):
        return self.watchdog
    def get_sed_mgmt(self):
        return self.sed
    def get_liquid_cooling(self):
        raise NotImplementedError
    def get_bmc(self):
        raise NotImplementedError
    def get_system_eeprom_info(self):
        raise NotImplementedError

CHASSIS = Chassis()
"#
);

fn recorder() -> (Bridge, Py<PyAny>) {
    Python::with_gil(|py| {
        let m = PyModule::from_code(py, RECORDER, c_str!("rec.py"), c_str!("rec")).unwrap();
        let chassis = m.getattr("CHASSIS").unwrap();
        let facade = py
            .import("platform_api.facade")
            .unwrap()
            .getattr("PlatformApi")
            .unwrap()
            .call1((&chassis,))
            .unwrap();
        (Bridge::from_facade(facade.unbind()), chassis.unbind())
    })
}

/// What the named device recorded, keeping only the methods asked for.
///
/// Filtered rather than reset: an action finds its row by walking the same
/// plan the snapshot walks, so every getter on the way past is recorded from
/// inside the very call being asserted on.
fn calls(chassis: &Py<PyAny>, device: &str, keep: &[&str]) -> Vec<(String, String)> {
    Python::with_gil(|py| {
        // "chassis" is the object itself; anything else is one of its devices.
        // Rec.__getattr__ answers a callable for any name it does not have, so
        // reaching for a device that is not there would silently yield one.
        let dev = if device == "chassis" {
            chassis.bind(py).clone()
        } else {
            chassis.bind(py).getattr(device).unwrap()
        };
        dev.getattr("calls")
            .unwrap()
            .try_iter()
            .unwrap()
            .map(|c| {
                let c = c.unwrap();
                (
                    c.get_item(0).unwrap().extract::<String>().unwrap(),
                    c.get_item(1).unwrap().repr().unwrap().to_string(),
                )
            })
            .filter(|(m, _): &(String, String)| keep.contains(&m.as_str()))
            .collect()
    })
}

#[test]
fn every_action_crosses_and_marshals_what_it_was_given() {
    use platform_api::{LedColor, Threshold};
    let (mut api, chassis) = recorder();

    api.set_fan_led("fan-1", LedColor::Amber).unwrap();
    api.set_fan_speed("fan-1", 30).unwrap();
    assert_eq!(
        calls(&chassis, "fan", &["set_status_led", "set_speed"]),
        vec![
            ("set_status_led".into(), "('amber',)".into()),
            ("set_speed".into(), "(30,)".into()),
        ],
        "a colour crosses as the string the base class declares"
    );

    api.set_fan_drawer_led("D1", LedColor::Green).unwrap();
    assert_eq!(calls(&chassis, "drawer", &["set_status_led"])[0].1, "('green',)");

    api.set_psu_led("P1", LedColor::Red).unwrap();
    api.set_psu_master_led("P1", LedColor::Off).unwrap();
    api.get_psu_master_led("P1").unwrap();
    assert_eq!(
        calls(&chassis, "psu", &["set_status_led", "set_status_master_led", "get_status_master_led"]).iter().map(|(m, _)| m.as_str()).collect::<Vec<_>>(),
        vec!["set_status_led", "set_status_master_led", "get_status_master_led"]
    );

    // A limit keeps its side of Union[int, float] on the way out too.
    api.set_sensor_high_threshold("v1", Threshold::Int(3600)).unwrap();
    api.set_sensor_low_threshold("v1", Threshold::Float(2.5)).unwrap();
    assert_eq!(
        calls(&chassis, "sensor", &["set_high_threshold", "set_low_threshold"]),
        vec![
            ("set_high_threshold".into(), "(3600,)".into()),
            ("set_low_threshold".into(), "(2.5,)".into()),
        ]
    );

    api.install_firmware("C1", "/i").unwrap();
    api.update_firmware("C1", "/i").unwrap();
    api.auto_update_firmware("C1", "/i", "cold").unwrap();
    assert_eq!(
        calls(&chassis, "component", &["install_firmware", "update_firmware", "auto_update_firmware"]).iter().map(|(m, _)| m.as_str()).collect::<Vec<_>>(),
        vec!["install_firmware", "update_firmware", "auto_update_firmware"]
    );

    api.reboot_module("M1", "DPU").unwrap();
    api.set_module_admin_state("M1", true).unwrap();
    api.set_module_admin_state_gracefully("M1", false).unwrap();
    api.power_cycle_module("M1").unwrap();
    api.module_pre_shutdown("M1").unwrap();
    api.module_post_startup("M1").unwrap();
    api.set_module_state_transition("M1", "recovery").unwrap();
    api.clear_module_state_transition("M1").unwrap();
    api.clear_module_gnoi_halt("M1").unwrap();
    let module = calls(&chassis, "module", &["reboot", "set_admin_state",
        "set_admin_state_gracefully", "do_power_cycle", "module_pre_shutdown",
        "module_post_startup", "set_module_state_transition",
        "clear_module_state_transition", "clear_module_gnoi_halt_in_progress"]);
    assert_eq!(module[0], ("reboot".into(), "('DPU',)".into()));
    assert_eq!(module[1], ("set_admin_state".into(), "(True,)".into()),
               "a bool crosses as True, not as 1");
    // pass_key: the locator is the base class's first argument as well.
    assert_eq!(module[6], ("set_module_state_transition".into(),
                           "('M1', 'recovery')".into()));
    assert_eq!(module.len(), 9);

    api.arm_watchdog(60).unwrap();
    api.disarm_watchdog().unwrap();
    assert_eq!(calls(&chassis, "watchdog", &["arm", "disarm"])[0], ("arm".into(), "(60,)".into()));

    api.change_sed_password("pw").unwrap();
    api.reset_sed_password().unwrap();
    assert_eq!(calls(&chassis, "sed", &["change_sed_password", "reset_sed_password"])[0], ("change_sed_password".into(), "('pw',)".into()));

    api.set_chassis_led(LedColor::Green).unwrap();
    api.initialize_system_led().unwrap();
    api.init_midplane_switch().unwrap();
    let ch = calls(&chassis, "chassis", &["set_status_led", "initizalize_system_led",
        "init_midplane_switch"]);
    assert!(ch.iter().any(|(m, a)| m == "set_status_led" && a == "('green',)"));
    // The base class spells it with the typo; the facade does not have to.
    assert!(ch.iter().any(|(m, _)| m == "initizalize_system_led"));
}
