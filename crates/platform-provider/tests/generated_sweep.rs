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
//! Every forwarder in the enum, called, with what Python received asserted.
//!
//! GENERATED from platform_api/facade.pyi by generator/generate.py.  Do not
//! edit: regenerate.
//!
//! `src/generated.rs` is sixty methods of delegation that a template wrote,
//! and it is tempting to argue from the template: one loop body, no branches,
//! so one method standing for the rest.  That argument is about the
//! generator.  It is not evidence about the code that shipped, it is not what
//! a coverage report measures, and it stops being true the day someone hand
//! -edits the generated file.  So: all sixty, called.  (`finalize` is the
//! sixty-first arm and the one the stub does not describe, so it is not
//! generated here; `delegation_test.rs` covers it.)
//!
//! What is asserted is the argument list Python was handed, not merely that
//! something happened.  A forwarder can only really go wrong one way -- by
//! passing its parameters on in the wrong order -- and only where two of them
//! share a type, which eight of these methods have: `(component,
//! image_path)`, `(task_id, filename, path)`, `(bus, dev, func)`.  Rust will
//! not catch a swap there, and neither would a test that only checked the
//! call arrived.  Every value below is therefore distinct and states its own
//! position.
//!
//! The facade here records and refuses rather than answering.  Return
//! conversion belongs to platform-pyo3, whose `bridge_test.rs` drives it
//! against mocks that answer; repeating it here would test the bridge a
//! second time and the enum no better.

use std::ffi::CStr;

use platform_api::{
    LedColor, FanInfoCols, FanDrawerInfoCols, ChassisInfoCols, ModuleInfoCols, Threshold, PlatformApi,
};
use platform_provider::Platform;
use pyo3::ffi::c_str;
use pyo3::prelude::*;
use pyo3::types::PyModule;

/// A facade that writes down what it was asked and then declines.
///
/// `__getattr__` means it answers to all sixty-one names without listing any,
/// so it cannot fall behind the stub the way a hand-written double would.
/// Refusing keeps every method the same shape regardless of what it returns:
/// the exception is the bridge's problem, and the caller discards it.
const RECORDER: &CStr = c_str!(
    r#"
class Facade:
    def __init__(self):
        self.calls = []
    def __getattr__(self, name):
        def record(*args):
            self.calls.append('%s%r' % (name, args))
            raise NotImplementedError(name)
        return record
"#
);

/// A `Platform::Pyo3` over a recording facade, and the facade to read after.
fn platform() -> (Platform, Py<PyAny>) {
    Python::with_gil(|py| {
        let m =
            PyModule::from_code(py, RECORDER, c_str!("recorder.py"), c_str!("recorder")).unwrap();
        let facade = m.getattr("Facade").unwrap().call0().unwrap();
        (
            Platform::Pyo3(platform_pyo3::Bridge::from_facade(facade.clone().unbind())),
            facade.unbind(),
        )
    })
}

/// What Python was asked, once.
///
/// Exactly one call, because the failure this guards against is an arm that
/// answers out of the enum without reaching an implementation at all -- which
/// records nothing, and which the caller cannot otherwise tell from a platform
/// that declined.
fn one_call(facade: &Py<PyAny>) -> String {
    Python::with_gil(|py| {
        let calls: Vec<String> = facade.bind(py).getattr("calls").unwrap().extract().unwrap();
        assert_eq!(calls.len(), 1, "one call into Python, got {calls:?}");
        calls.into_iter().next().unwrap()
    })
}

#[test]
fn get_chassis_info_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_chassis_info(ChassisInfoCols::ALL);
    assert_eq!(one_call(&facade), "get_chassis_info(524287,)");
}

#[test]
fn get_modules_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_modules(ModuleInfoCols::ALL);
    assert_eq!(one_call(&facade), "get_modules(65535,)");
}

#[test]
fn get_thermals_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_thermals();
    assert_eq!(one_call(&facade), "get_thermals()");
}

#[test]
fn get_fans_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_fans(FanInfoCols::ALL);
    assert_eq!(one_call(&facade), "get_fans(4095,)");
}

#[test]
fn get_fan_drawers_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_fan_drawers(FanDrawerInfoCols::ALL);
    assert_eq!(one_call(&facade), "get_fan_drawers(255,)");
}

#[test]
fn get_psus_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_psus();
    assert_eq!(one_call(&facade), "get_psus()");
}

#[test]
fn get_components_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_components();
    assert_eq!(one_call(&facade), "get_components()");
}

#[test]
fn get_sensors_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_sensors();
    assert_eq!(one_call(&facade), "get_sensors()");
}

#[test]
fn get_leak_profiles_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_leak_profiles();
    assert_eq!(one_call(&facade), "get_leak_profiles()");
}

#[test]
fn get_leak_sensors_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_leak_sensors();
    assert_eq!(one_call(&facade), "get_leak_sensors()");
}

#[test]
fn get_eeprom_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_eeprom();
    assert_eq!(one_call(&facade), "get_eeprom()");
}

#[test]
fn get_bmcs_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_bmcs();
    assert_eq!(one_call(&facade), "get_bmcs()");
}

#[test]
fn get_watchdogs_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_watchdogs();
    assert_eq!(one_call(&facade), "get_watchdogs()");
}

#[test]
fn set_fan_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_fan_led("arg0", LedColor::Green);
    assert_eq!(one_call(&facade), "set_fan_led('arg0', 'green')");
}

#[test]
fn set_fan_drawer_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_fan_drawer_led("arg0", LedColor::Green);
    assert_eq!(one_call(&facade), "set_fan_drawer_led('arg0', 'green')");
}

#[test]
fn set_fan_speed_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_fan_speed("arg0", 2);
    assert_eq!(one_call(&facade), "set_fan_speed('arg0', 2)");
}

#[test]
fn set_psu_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_psu_led("arg0", LedColor::Green);
    assert_eq!(one_call(&facade), "set_psu_led('arg0', 'green')");
}

#[test]
fn get_module_reboot_cause_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_module_reboot_cause("arg0");
    assert_eq!(one_call(&facade), "get_module_reboot_cause('arg0',)");
}

#[test]
fn get_module_midplane_down_reason_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_module_midplane_down_reason("arg0");
    assert_eq!(one_call(&facade), "get_module_midplane_down_reason('arg0',)");
}

#[test]
fn get_psu_master_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_psu_master_led("arg0");
    assert_eq!(one_call(&facade), "get_psu_master_led('arg0',)");
}

#[test]
fn set_psu_master_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_psu_master_led("arg0", LedColor::Green);
    assert_eq!(one_call(&facade), "set_psu_master_led('arg0', 'green')");
}

#[test]
fn reboot_module_forwards() {
    let (mut p, facade) = platform();
    let _ = p.reboot_module("arg0", "arg1");
    assert_eq!(one_call(&facade), "reboot_module('arg0', 'arg1')");
}

#[test]
fn set_module_admin_state_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_module_admin_state("arg0", true);
    assert_eq!(one_call(&facade), "set_module_admin_state('arg0', True)");
}

#[test]
fn set_module_admin_state_gracefully_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_module_admin_state_gracefully("arg0", true);
    assert_eq!(one_call(&facade), "set_module_admin_state_gracefully('arg0', True)");
}

#[test]
fn power_cycle_module_forwards() {
    let (mut p, facade) = platform();
    let _ = p.power_cycle_module("arg0");
    assert_eq!(one_call(&facade), "power_cycle_module('arg0',)");
}

#[test]
fn module_pre_shutdown_forwards() {
    let (mut p, facade) = platform();
    let _ = p.module_pre_shutdown("arg0");
    assert_eq!(one_call(&facade), "module_pre_shutdown('arg0',)");
}

#[test]
fn module_post_startup_forwards() {
    let (mut p, facade) = platform();
    let _ = p.module_post_startup("arg0");
    assert_eq!(one_call(&facade), "module_post_startup('arg0',)");
}

#[test]
fn set_module_state_transition_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_module_state_transition("arg0", "arg1");
    assert_eq!(one_call(&facade), "set_module_state_transition('arg0', 'arg1')");
}

#[test]
fn clear_module_state_transition_forwards() {
    let (mut p, facade) = platform();
    let _ = p.clear_module_state_transition("arg0");
    assert_eq!(one_call(&facade), "clear_module_state_transition('arg0',)");
}

#[test]
fn clear_module_gnoi_halt_forwards() {
    let (mut p, facade) = platform();
    let _ = p.clear_module_gnoi_halt("arg0");
    assert_eq!(one_call(&facade), "clear_module_gnoi_halt('arg0',)");
}

#[test]
fn set_sensor_high_threshold_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_sensor_high_threshold("arg0", Threshold::Int(2));
    assert_eq!(one_call(&facade), "set_sensor_high_threshold('arg0', 2)");
}

#[test]
fn set_sensor_low_threshold_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_sensor_low_threshold("arg0", Threshold::Int(2));
    assert_eq!(one_call(&facade), "set_sensor_low_threshold('arg0', 2)");
}

#[test]
fn get_available_firmware_version_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_available_firmware_version("arg0", "arg1");
    assert_eq!(one_call(&facade), "get_available_firmware_version('arg0', 'arg1')");
}

#[test]
fn get_firmware_update_notification_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_firmware_update_notification("arg0", "arg1");
    assert_eq!(one_call(&facade), "get_firmware_update_notification('arg0', 'arg1')");
}

#[test]
fn install_firmware_forwards() {
    let (mut p, facade) = platform();
    let _ = p.install_firmware("arg0", "arg1");
    assert_eq!(one_call(&facade), "install_firmware('arg0', 'arg1')");
}

#[test]
fn update_firmware_forwards() {
    let (mut p, facade) = platform();
    let _ = p.update_firmware("arg0", "arg1");
    assert_eq!(one_call(&facade), "update_firmware('arg0', 'arg1')");
}

#[test]
fn auto_update_firmware_forwards() {
    let (mut p, facade) = platform();
    let _ = p.auto_update_firmware("arg0", "arg1", "arg2");
    assert_eq!(one_call(&facade), "auto_update_firmware('arg0', 'arg1', 'arg2')");
}

#[test]
fn arm_watchdog_forwards() {
    let (mut p, facade) = platform();
    let _ = p.arm_watchdog(1);
    assert_eq!(one_call(&facade), "arm_watchdog(1,)");
}

#[test]
fn disarm_watchdog_forwards() {
    let (mut p, facade) = platform();
    let _ = p.disarm_watchdog();
    assert_eq!(one_call(&facade), "disarm_watchdog()");
}

#[test]
fn initialize_system_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.initialize_system_led();
    assert_eq!(one_call(&facade), "initialize_system_led()");
}

#[test]
fn init_midplane_switch_forwards() {
    let (mut p, facade) = platform();
    let _ = p.init_midplane_switch();
    assert_eq!(one_call(&facade), "init_midplane_switch()");
}

#[test]
fn set_chassis_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_chassis_led(LedColor::Green);
    assert_eq!(one_call(&facade), "set_chassis_led('green',)");
}

#[test]
fn change_sed_password_forwards() {
    let (mut p, facade) = platform();
    let _ = p.change_sed_password("arg0");
    assert_eq!(one_call(&facade), "change_sed_password('arg0',)");
}

#[test]
fn reset_sed_password_forwards() {
    let (mut p, facade) = platform();
    let _ = p.reset_sed_password();
    assert_eq!(one_call(&facade), "reset_sed_password()");
}

#[test]
fn bmc_open_session_forwards() {
    let (mut p, facade) = platform();
    let _ = p.bmc_open_session();
    assert_eq!(one_call(&facade), "bmc_open_session()");
}

#[test]
fn bmc_close_session_forwards() {
    let (mut p, facade) = platform();
    let _ = p.bmc_close_session("arg0");
    assert_eq!(one_call(&facade), "bmc_close_session('arg0',)");
}

#[test]
fn bmc_reset_root_password_forwards() {
    let (mut p, facade) = platform();
    let _ = p.bmc_reset_root_password();
    assert_eq!(one_call(&facade), "bmc_reset_root_password()");
}

#[test]
fn bmc_reset_forwards() {
    let (mut p, facade) = platform();
    let _ = p.bmc_reset(true);
    assert_eq!(one_call(&facade), "bmc_reset(True,)");
}

#[test]
fn bmc_update_firmware_forwards() {
    let (mut p, facade) = platform();
    let _ = p.bmc_update_firmware("arg0");
    assert_eq!(one_call(&facade), "bmc_update_firmware('arg0',)");
}

#[test]
fn bmc_trigger_debug_log_dump_forwards() {
    let (mut p, facade) = platform();
    let _ = p.bmc_trigger_debug_log_dump();
    assert_eq!(one_call(&facade), "bmc_trigger_debug_log_dump()");
}

#[test]
fn bmc_get_debug_log_dump_forwards() {
    let (mut p, facade) = platform();
    let _ = p.bmc_get_debug_log_dump("arg0", "arg1", "arg2");
    assert_eq!(one_call(&facade), "bmc_get_debug_log_dump('arg0', 'arg1', 'arg2')");
}

#[test]
fn get_asics_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_asics();
    assert_eq!(one_call(&facade), "get_asics()");
}

#[test]
fn tm_initialize_forwards() {
    let (mut p, facade) = platform();
    let _ = p.tm_initialize();
    assert_eq!(one_call(&facade), "tm_initialize()");
}

#[test]
fn tm_run_policy_forwards() {
    let (mut p, facade) = platform();
    let _ = p.tm_run_policy();
    assert_eq!(one_call(&facade), "tm_run_policy()");
}

#[test]
fn tm_get_interval_forwards() {
    let (mut p, facade) = platform();
    let _ = p.tm_get_interval();
    assert_eq!(one_call(&facade), "tm_get_interval()");
}

#[test]
fn tm_deinitialize_forwards() {
    let (mut p, facade) = platform();
    let _ = p.tm_deinitialize();
    assert_eq!(one_call(&facade), "tm_deinitialize()");
}

#[test]
fn eeprom_update_db_forwards() {
    let (mut p, facade) = platform();
    let _ = p.eeprom_update_db();
    assert_eq!(one_call(&facade), "eeprom_update_db()");
}

#[test]
fn get_storage_devices_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_storage_devices();
    assert_eq!(one_call(&facade), "get_storage_devices()");
}

#[test]
fn get_pcie_devices_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_pcie_devices();
    assert_eq!(one_call(&facade), "get_pcie_devices()");
}

#[test]
fn get_pcie_aer_stats_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_pcie_aer_stats(1, 2, 3);
    assert_eq!(one_call(&facade), "get_pcie_aer_stats(1, 2, 3)");
}

#[test]
fn get_change_event_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_change_event(1);
    assert_eq!(one_call(&facade), "get_change_event(1,)");
}
