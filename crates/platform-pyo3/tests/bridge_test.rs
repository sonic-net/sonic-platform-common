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

use platform_api::{ChassisInfoCols, FanDrawerInfoCols, FanInfoCols, LedColor, ModuleInfoCols, PlatformApi, PlatformError};
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

class FwComponent(Component):
    # BIOS answers neither, so the not-supported path stays covered by the
    # component that does not have them; this one covers the answered path.
    def get_available_firmware_version(self, image_path):
        return '2.0 from ' + image_path
    def get_firmware_update_notification(self, image_path):
        return 'cold reboot required for ' + image_path

class Eeprom:
    # syseepromd's whole platform surface: read the bytes, hand them back to
    # the platform's own writer.  0 is success, as it is in Python.
    def __init__(self):
        self.written = None
    def read_eeprom(self):
        return b'TlvInfo'
    def update_eeprom_db(self, data):
        self.written = data
        return 0

class PcieUtil:
    # `pcie.yaml` columns, hex strings and all -- plus one malformed entry,
    # because one bad line in that file must not cost the parts list.
    def get_pcie_check(self):
        return [{'name': 'ASIC', 'bus': '05', 'dev': '1f', 'fn': '0', 'result': 'Passed'},
                {'name': 'NIC', 'bus': '06', 'dev': '00', 'fn': '1', 'result': 'Failed'},
                {'name': 'malformed'}]
    def get_pcie_aer_stats(self, bus, dev, func):
        return {'correctable': {'RxErr': '3', 'BadTLP': '0'},
                'fatal': {},
                'non_fatal': {'TLP': '1'}}

class Disk:
    def __init__(self, name):
        self._name, self.fetched = name, []
    def fetch_parse_info(self, path):
        self.fetched.append(path)
    def get_model(self):
        return 'INTEL SSDSC'
    def get_serial(self):
        return 'PHDW1'
    def get_firmware(self):
        return 'EDA7602Q'
    def get_health(self):
        return '98'
    def get_temperature(self):
        return '31'
    def get_disk_io_reads(self):
        return '100'
    def get_disk_io_writes(self):
        return '200'
    def get_reserved_blocks(self):
        return '1'
    def get_fs_io_reads(self):
        return 4242
    def get_fs_io_writes(self):
        return 2121

class StorageDevices:
    # A disk with a utility class and one without: stormond must publish both.
    def __init__(self):
        self.devices = {'sda': Disk('sda'), 'sdb': None}

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
    # Every command answers (code, payload), and the payload is a different
    # shape in each -- which is why the escape hatch unpacks them one at a time
    # rather than by a rule.  The three shapes are all here.
    def open_session(self):
        return (0, ('opened', ('sid-1', 'tok-1')))
    def close_session(self, session_id):
        return (0, 'closed ' + session_id)
    def reset_root_password(self):
        return (0, 'reset')
    def request_bmc_reset(self, graceful):
        return (0, 'graceful' if graceful else 'hard')
    def update_firmware(self, image_path):
        return (0, ('flashed ' + image_path, ['cpld']))
    def trigger_bmc_debug_log_dump(self):
        return (0, ('task-9', 'started'))          # task id first, unlike the rest
    def get_bmc_debug_log_dump(self, task_id, filename, path):
        return (0, path + '/' + filename + ' for ' + task_id)

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

class UnreadableLeakSensor(LeakSensor):
    # What mlnx returns when the sysfs read fails: not a bool, and not None.
    # `liquid_cooling.py:46-57` returns the string 'N/A' from is_leak().
    def is_leak(self):
        return 'N/A'

class NarrowedDpuId:
    # What mlnx does: ChassisBase declares get_dpu_id(self, **kwargs), which a
    # zero-argument call satisfies, and SmartSwitchChassis narrows it to a
    # required positional (chassis.py:1764).
    def get_dpu_id(self, name):
        return 7

class LiquidCooling:
    def get_all_leak_sensors(self):
        return [LeakSensor('leak-1'), UnreadableLeakSensor('leak-2')]
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
    # Takes the module's name, the way ModuleBase declares it
    # (module_base.py:709) -- a zero-argument call raises, and the row is built
    # eagerly, so getting this wrong costs every other column too.
    def get_module_state_transition(self, module_name):
        return module_name == 'LC1'
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
    def get_reboot_cause(self):
        return ('Software', 'requested by user')
    def get_midplane_down_reason(self):
        return ('Power Loss', 'DPU power rail dropped')
    def get_all_components(self):
        return [FwComponent('LC-CPLD')]
    def get_all_voltage_sensors(self):
        return [Sensor('lc-v')]
    def get_all_current_sensors(self):
        return []

class Loaded:
    def __init__(self):
        self.watchdog = Watchdog()
        self.eeprom = Eeprom()
    # Narrowed exactly as mlnx narrows it: ChassisBase declares
    # get_dpu_id(self, **kwargs), SmartSwitchChassis takes a required
    # positional (chassis.py:1764).  The row must still be readable.
    def get_dpu_id(self, name):
        return 7
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
    def get_eeprom(self):
        return self.eeprom
    def get_watchdog(self):
        return self.watchdog
    def get_reboot_cause(self):
        return ('Watchdog', 'timed out')

CHASSIS = Loaded()
PCIE = PcieUtil()
STORAGE = StorageDevices()
"#
);

/// The facade over the loaded chassis, with the two objects that do not come
/// through the chassis installed by hand.
///
/// `get_pcie_devices` and `get_storage_devices` are the two methods whose
/// backing object the escape hatch constructs itself -- `sonic_platform.pcie`
/// with a fallback to `PcieUtil`, and `StorageDevices()` walking /sys/block --
/// so a mock chassis cannot reach them. Setting the cached handle and its
/// `_tried` flag is the same seam the Python tests use (`_hatch_with_storage`).
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
        let hatch = facade.getattr("_hatch").unwrap();
        hatch.setattr("_pcie", m.getattr("PCIE").unwrap()).unwrap();
        hatch.setattr("_pcie_tried", true).unwrap();
        hatch.setattr("_storage", m.getattr("STORAGE").unwrap()).unwrap();
        hatch.setattr("_storage_tried", true).unwrap();
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
    assert_eq!(api.get_fans(FanInfoCols::ALL).unwrap()[0].speed_pct, Some(50));
}

#[test]
fn fan_direction_na_crosses_as_a_value() {
    use platform_api::FanDirection;
    let (mut api, _chassis) = bridge();
    assert_eq!(api.get_fans(FanInfoCols::ALL).unwrap()[0].direction, Some(FanDirection::NA));
}

#[test]
fn an_action_addresses_the_row_by_the_name_the_snapshot_published() {
    let (mut api, chassis) = bridge();
    let name = api.get_fans(FanInfoCols::ALL).unwrap()[0].name.clone();
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
    let name = api.get_fans(FanInfoCols::ALL).unwrap()[0].name.clone();
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
    let info = api.get_chassis_info(ChassisInfoCols::ALL).unwrap();
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
    assert_eq!(api.get_chassis_info(ChassisInfoCols::ALL).unwrap().my_slot, None);
    assert_eq!(api.get_modules(ModuleInfoCols::ALL).unwrap()[0].is_midplane_reachable, None);
}

#[test]
fn a_module_carries_the_strings_the_base_class_defines() {
    use platform_api::{ModuleStatus, ModuleType};
    let (mut api, _chassis) = bridge();
    let m = &api.get_modules(ModuleInfoCols::ALL).unwrap()[0];
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

    let drawers = api.get_fan_drawers(FanDrawerInfoCols::ALL).unwrap();
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
fn a_getter_that_takes_the_devices_name_is_given_it() {
    // `ModuleBase.get_module_state_transition(module_name)` requires the name.
    // Declared as a plain column the generated call passed nothing, raised, and
    // took the whole ModuleInfo row with it: on a SmartSwitch chassisd logged
    // "Failed to read the modules" every cycle and published no midplane table.
    // The fixture answers true only for its own name, so a stub that passed the
    // wrong string -- or none -- would not satisfy this.
    let mut api = loaded();
    let modules = api.get_modules(ModuleInfoCols::ALL).expect("the row must be readable");
    let m = modules.iter().find(|m| m.name == "LC1").expect("LC1");
    assert_eq!(m.state_transition, Some(true), "the getter must receive this module's own name");
}

#[test]
fn a_narrowed_getter_costs_its_own_column_and_not_the_row() {
    // The failure this guards against is not a missing number: it is that one
    // vendor-narrowed signature raised TypeError while the row was being built
    // eagerly, so `get_chassis_info()` returned Err, and chassisd -- reading
    // that as "no chassis info" -- exited "not supported" on a SmartSwitch
    // with four live DPUs, silently.  The column may be absent; the row may
    // not be.
    let mut api = loaded();
    let info = api.get_chassis_info(ChassisInfoCols::ALL).expect("the row must survive a narrowed getter");
    assert_eq!(info.dpu_id, None, "a narrowed signature reads as absent");
    assert!(info.is_modular_chassis, "the rest of the row is still readable");
}

#[test]
fn a_leak_sensor_that_cannot_be_read_reports_leaking() {
    // The dangerous direction, and the one a strict bool extraction gets wrong.
    //
    // `is_leak()` is declared bool but mlnx answers the string 'N/A' when the
    // sysfs read fails, and the Python daemon's `if sensor_is_leak:`
    // (thermalctld:676) therefore treats it as leaking.  Normalising the
    // sentinel to None instead -- which reads as the obvious thing to do -- put
    // `leaking=No` and `device_leak_status=None` in STATE_DB for a switch whose
    // leak sensor had failed, so bmcctld never saw the CRITICAL it cuts power
    // on.  Measured on slm-111 against the Python daemon on the same box.
    let mut api = loaded();
    let sensors = api.get_leak_sensors().unwrap();
    let faulty = sensors.iter().find(|s| s.name == "leak-2").expect("leak-2 row");
    assert_eq!(faulty.is_leak, Some(true), "'N/A' must not read as 'not leaking'");
}

#[test]
fn the_chassis_row_carries_what_the_platform_answered() {
    let mut api = loaded();
    let info = api.get_chassis_info(ChassisInfoCols::ALL).unwrap();
    assert!(info.is_modular_chassis);
    assert_eq!(info.reboot_cause.as_deref(), Some("Watchdog"));
    assert_eq!(info.reboot_cause_detail.as_deref(), Some("timed out"));
}

#[test]
fn a_component_firmware_query_crosses_with_its_argument() {
    let mut api = loaded();
    // BIOS has no such method, so this is the not-supported path -- which is
    // the one a caller has to be able to tell from a real answer.
    match api.get_available_firmware_version("BIOS", "/tmp/fw.bin") {
        Err(PlatformError::NotSupported(_)) => {}
        other => panic!("expected NotSupported, got {other:?}"),
    }
    // LC-CPLD answers, and the answer must carry the path that was asked
    // about: the image path is the second argument of a two-argument call, and
    // a bridge that dropped it would still compile and still return a string.
    assert_eq!(
        api.get_available_firmware_version("LC-CPLD", "/tmp/fw.bin").unwrap().as_deref(),
        Some("2.0 from /tmp/fw.bin")
    );
    assert_eq!(
        api.get_firmware_update_notification("LC-CPLD", "/tmp/fw.bin").unwrap().as_deref(),
        Some("cold reboot required for /tmp/fw.bin")
    );
}

#[test]
fn a_module_is_asked_for_its_reboot_cause_by_name() {
    // Deliberately not a column of ModuleInfo: on Mellanox this getter logs a
    // NOTICE per call (`module.py:477,482`), so as a column it wrote 358 lines
    // where Python wrote 20. It is a method, and a method has to be handed the
    // module's name.
    let mut api = loaded();
    let rc = api.get_module_reboot_cause("LC1").unwrap();
    // Both halves, from the one call.  Carrying only the cause is bug 14: the
    // detail is what the record's `comment` publishes, and dropping it wrote
    // `N/A` where the Python daemon wrote the reason.
    assert_eq!(rc.cause.as_deref(), Some("Software"));
    assert_eq!(rc.detail.as_deref(), Some("requested by user"));
}

#[test]
fn a_module_is_asked_why_its_midplane_went_down_by_name() {
    // Asked when a DPU's midplane drops without a planned transition, the way
    // the reboot cause is asked when it restarts; one call fills both halves.
    let mut api = loaded();
    let why = api.get_module_midplane_down_reason("LC1").unwrap();
    assert_eq!(why.reason.as_deref(), Some("Power Loss"));
    assert_eq!(why.detail.as_deref(), Some("DPU power rail dropped"));
}

#[test]
fn a_midplane_reason_for_a_module_nobody_has_is_not_found() {
    // The facade raises for a name no row has, and the bridge carries that
    // across as NotFound -- the case chassisd has to tell from a platform
    // that simply has no answer.
    let mut api = loaded();
    match api.get_module_midplane_down_reason("NO-SUCH-DPU") {
        Err(PlatformError::NotFound(_)) => {}
        other => panic!("expected NotFound, got {other:?}"),
    }
}

#[test]
fn the_platform_writes_its_own_eeprom_table() {
    // syseepromd does not publish EEPROM_INFO itself -- `update_eeprom_db()`
    // does, and it needs the bytes `read_eeprom()` returned. The pair crosses
    // as one call so the raw image never has to.
    let mut api = loaded();
    assert!(api.eeprom_update_db().unwrap(), "0 from the platform is success");
}

#[test]
fn the_pcie_parts_list_survives_one_malformed_entry() {
    let mut api = loaded();
    let rows = api.get_pcie_devices().unwrap();
    assert_eq!(
        rows.iter().map(|d| (d.name.as_str(), d.bus, d.dev, d.r#fn, d.present)).collect::<Vec<_>>(),
        vec![("ASIC", 5, 31, 0, true), ("NIC", 6, 0, 1, false)],
        "hex strings are parsed as hex, 'Passed' is the only present, and the \
         entry with no bus is dropped without taking the others with it"
    );
}

#[test]
fn aer_counters_arrive_flattened_out_of_their_severities() {
    let mut api = loaded();
    let mut rows = api.get_pcie_aer_stats(5, 31, 0).unwrap();
    rows.sort_by(|a, b| (&a.severity, &a.field).cmp(&(&b.severity, &b.field)));
    assert_eq!(
        rows.iter().map(|r| (r.severity.as_str(), r.field.as_str(), r.value.as_str())).collect::<Vec<_>>(),
        vec![
            ("correctable", "BadTLP", "0"),
            ("correctable", "RxErr", "3"),
            ("non_fatal", "TLP", "1"),
        ],
        "a severity with no counters contributes no rows"
    );
}

#[test]
fn a_disk_with_no_utility_class_is_still_a_row() {
    // Dropping it would make a switch with an unreadable disk look like a
    // switch without one, and STORAGE_INFO is the only place that shows.
    let mut api = loaded();
    let rows = api.get_storage_devices().unwrap();
    assert_eq!(
        rows.iter().map(|d| (d.name.as_str(), d.available)).collect::<Vec<_>>(),
        vec![("sda", true), ("sdb", false)]
    );
    let sda = &rows[0];
    assert_eq!(sda.firmware, "EDA7602Q");
    assert_eq!(sda.health, "98");
    // The two counters cross as numbers where the readings cross as text,
    // because stormond does arithmetic on these and on none of the others.
    assert_eq!((sda.fs_io_reads, sda.fs_io_writes), (Some(4242), Some(2121)));
    assert_eq!(rows[1].model, "N/A");
    assert_eq!(rows[1].fs_io_reads, None);
}

#[test]
fn every_bmc_command_unpacks_its_own_payload_shape() {
    // Three shapes: (code, message), (code, (message, credentials)) and
    // (code, (task_id, message)) -- task id first in that last one. Unpacking
    // any of them with another's rule yields a row that is the wrong way round
    // and still type-checks.
    let mut api = loaded();

    let open = api.bmc_open_session().unwrap();
    assert_eq!(open.code, 0);
    assert_eq!(open.message.as_deref(), Some("opened"));
    assert_eq!(
        (open.session_id.as_deref(), open.token.as_deref()),
        (Some("sid-1"), Some("tok-1"))
    );

    assert_eq!(api.bmc_close_session("sid-1").unwrap().message.as_deref(), Some("closed sid-1"));
    assert_eq!(api.bmc_reset_root_password().unwrap().message.as_deref(), Some("reset"));
    assert_eq!(api.bmc_reset(true).unwrap().message.as_deref(), Some("graceful"));
    assert_eq!(
        api.bmc_update_firmware("/tmp/bmc.fwpkg").unwrap().message.as_deref(),
        Some("flashed /tmp/bmc.fwpkg"),
        "the component list beside the message is not the message"
    );

    let dump = api.bmc_trigger_debug_log_dump().unwrap();
    assert_eq!((dump.task_id.as_deref(), dump.message.as_deref()), (Some("task-9"), Some("started")));
    assert_eq!(
        api.bmc_get_debug_log_dump("task-9", "d.tar", "/tmp").unwrap().message.as_deref(),
        Some("/tmp/d.tar for task-9")
    );
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

/// The vendor packages build their `Logger` with no identifier, so it falls
/// back to `os.path.basename(sys.argv[0])`.  An embedded interpreter starts
/// with that empty, which on hardware showed up as `ERR pmon#: PDB 1
/// temperature file ... does not exist` where the Python daemon had logged
/// `ERR pmon#thermalctld: ...` -- the same message with the daemon's name
/// stripped off, which is what sonic-mgmt's loganalyzer matches on.
///
/// `Bridge::new` sets it before importing the vendor module, so the import
/// failing here does not stop the assertion from being meaningful.
#[test]
fn the_bridge_names_the_interpreter_for_the_vendor_s_logger() {
    let _ = Bridge::new("a_module_that_does_not_exist", "thermalctld");
    Python::with_gil(|py| {
        let argv: Vec<String> = py
            .import("sys")
            .unwrap()
            .getattr("argv")
            .unwrap()
            .extract()
            .unwrap();
        assert_eq!(argv, vec!["thermalctld".to_string()]);
    });
}

/// mlnx's `Chassis.__init__` calls `utils.watch_shutdown_signals()`, which
/// installs a Python-level SIGTERM handler chained onto `signal.getsignal()`.
/// Under a Rust daemon that reads back `SIG_DFL` -- the Rust handler lives at
/// the OS level, where `getsignal` cannot see it -- and the vendor's fallback
/// for `SIG_DFL` is to restore the default and re-raise, killing the process
/// the first time Rust re-enters Python after SIGTERM.  On hardware that ate
/// the whole shutdown path: `tm_deinitialize()` never ran and hw-management-tc
/// was left driving fans off stale temperatures.
///
/// What is asserted here is the half that is testable off the main thread:
/// handing the signals back must never cost us the bridge.  `signal.signal()`
/// raises anywhere but the main thread, and thermalctld builds a second bridge
/// on its leak thread -- a reset that propagated its failure would take leak
/// detection down with it.  That the reset actually lands is verified on
/// hardware, where the daemon's bridge is built on the main thread.
#[test]
fn handing_the_signals_back_never_costs_us_the_bridge() {
    const VENDOR: &std::ffi::CStr = c_str!(
        "import signal\n\
         class _C:\n\
         \x20   def get_name(self): return 'chassis 1'\n\
         class Platform:\n\
         \x20   def __init__(self):\n\
         \x20       try:\n\
         \x20           signal.signal(signal.SIGTERM, lambda *a: None)\n\
         \x20       except ValueError:\n\
         \x20           pass\n\
         \x20   def get_chassis(self): return _C()\n"
    );
    Python::with_gil(|py| {
        let m = PyModule::from_code(py, VENDOR, c_str!("vend.py"), c_str!("vend_sig")).unwrap();
        py.import("sys")
            .unwrap()
            .getattr("modules")
            .unwrap()
            .set_item("vend_sig", m)
            .unwrap();
    });

    assert!(
        Bridge::new("vend_sig", "thermalctld").is_ok(),
        "a vendor that touches signal handling must still yield a working bridge"
    );
}

/// `finalize` is the daemon's only way out, and it has to reach the vendor.
///
/// A Rust daemon leaves through `std::process::exit`, which finalises no
/// interpreter, so cleanup a vendor registered with `atexit` would simply not
/// run -- on hardware that left hw-management-tc suspended behind a stale ASIC
/// temperature file.  `main` no longer names the bridge, so nothing else
/// checks that the implementation behind the trait still does this: without
/// this test the forwarding could be deleted and every other test would pass.
#[test]
fn finalize_runs_the_handlers_the_vendor_registered() {
    let (mut api, _chassis) = bridge();
    Python::with_gil(|py| {
        let m = PyModule::from_code(
            py,
            c_str!(
                "import atexit\n\
                 RAN = []\n\
                 atexit.register(lambda: RAN.append(1))\n"
            ),
            c_str!("vendor_cleanup.py"),
            c_str!("vendor_cleanup"),
        )
        .unwrap();
        assert_eq!(m.getattr("RAN").unwrap().len().unwrap(), 0);
        api.finalize();
        assert_eq!(
            m.getattr("RAN").unwrap().len().unwrap(),
            1,
            "the vendor's atexit cleanup must run when the daemon finalizes"
        );
    });
}
