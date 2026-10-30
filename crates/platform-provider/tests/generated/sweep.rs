//! Every forwarder in the enum, called, with what Python received asserted.
//!
//! GENERATED from sonic_platform_api/facade.pyi by generator/generate.py.  Do
//! not edit: regenerate.
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
    LedColor, ThermalInfoCols, FanInfoCols, FanDrawerInfoCols, ChassisInfoCols, ModuleInfoCols, Number, DeviceKey, PlatformApi,
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
fn get_sfps_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_sfps();
    assert_eq!(one_call(&facade), "get_sfps()");
}

#[test]
fn get_chassis_info_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_chassis_info(ChassisInfoCols::ALL);
    assert_eq!(one_call(&facade), "get_chassis_info(1048575,)");
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
    let _ = p.get_thermals(ThermalInfoCols::ALL, &[DeviceKey::from("skip0"), DeviceKey::from("skip1")]);
    assert_eq!(one_call(&facade), "get_thermals(511, ['skip0', 'skip1'])");
}

#[test]
fn get_fans_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_fans(FanInfoCols::ALL, true);
    assert_eq!(one_call(&facade), "get_fans(4095, True)");
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
fn sfp_get_presence_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_presence(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_presence('arg0',)");
}

#[test]
fn sfp_is_replaceable_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_is_replaceable(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_is_replaceable('arg0',)");
}

#[test]
fn sfp_get_reset_status_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_reset_status(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_reset_status('arg0',)");
}

#[test]
fn sfp_get_lpmode_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_lpmode(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_lpmode('arg0',)");
}

#[test]
fn sfp_get_error_description_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_error_description(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_error_description('arg0',)");
}

#[test]
fn sfp_get_type_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_type(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_type('arg0',)");
}

#[test]
fn sfp_has_method_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_has_method(&DeviceKey::from("arg0"), "arg1");
    assert_eq!(one_call(&facade), "sfp_has_method('arg0', 'arg1')");
}

#[test]
fn sfp_get_transceiver_info_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_info(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_info('arg0',)");
}

#[test]
fn sfp_get_transceiver_info_firmware_versions_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_info_firmware_versions(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_info_firmware_versions('arg0',)");
}

#[test]
fn sfp_get_transceiver_status_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_status(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_status('arg0',)");
}

#[test]
fn sfp_get_transceiver_status_flags_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_status_flags(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_status_flags('arg0',)");
}

#[test]
fn sfp_get_transceiver_dom_real_value_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_dom_real_value(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_dom_real_value('arg0',)");
}

#[test]
fn sfp_get_transceiver_dom_flags_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_dom_flags(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_dom_flags('arg0',)");
}

#[test]
fn sfp_get_transceiver_threshold_info_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_threshold_info(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_threshold_info('arg0',)");
}

#[test]
fn sfp_get_temperature_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_temperature(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_temperature('arg0',)");
}

#[test]
fn sfp_get_transceiver_pm_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_pm(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_pm('arg0',)");
}

#[test]
fn sfp_is_transceiver_vdm_supported_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_is_transceiver_vdm_supported(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_is_transceiver_vdm_supported('arg0',)");
}

#[test]
fn sfp_is_vdm_statistic_supported_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_is_vdm_statistic_supported(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_is_vdm_statistic_supported('arg0',)");
}

#[test]
fn sfp_get_transceiver_vdm_real_value_basic_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_vdm_real_value_basic(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_vdm_real_value_basic('arg0',)");
}

#[test]
fn sfp_get_transceiver_vdm_real_value_statistic_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_vdm_real_value_statistic(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_vdm_real_value_statistic('arg0',)");
}

#[test]
fn sfp_get_transceiver_vdm_flags_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_vdm_flags(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_vdm_flags('arg0',)");
}

#[test]
fn sfp_get_transceiver_vdm_thresholds_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_transceiver_vdm_thresholds(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_transceiver_vdm_thresholds('arg0',)");
}

#[test]
fn sfp_get_vdm_freeze_status_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_vdm_freeze_status(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_vdm_freeze_status('arg0',)");
}

#[test]
fn sfp_get_vdm_unfreeze_status_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_vdm_unfreeze_status(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_vdm_unfreeze_status('arg0',)");
}

#[test]
fn sfp_set_lpmode_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_set_lpmode(&DeviceKey::from("arg0"), true);
    assert_eq!(one_call(&facade), "sfp_set_lpmode('arg0', True)");
}

#[test]
fn sfp_reset_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_reset(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_reset('arg0',)");
}

#[test]
fn sfp_remove_xcvr_api_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_remove_xcvr_api(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_remove_xcvr_api('arg0',)");
}

#[test]
fn sfp_freeze_vdm_stats_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_freeze_vdm_stats(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_freeze_vdm_stats('arg0',)");
}

#[test]
fn sfp_unfreeze_vdm_stats_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_unfreeze_vdm_stats(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_unfreeze_vdm_stats('arg0',)");
}

#[test]
fn sfp_read_eeprom_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_read_eeprom(&DeviceKey::from("arg0"), 2, 3);
    assert_eq!(one_call(&facade), "sfp_read_eeprom('arg0', 2, 3)");
}

#[test]
fn sfp_write_eeprom_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_write_eeprom(&DeviceKey::from("arg0"), 2, &[0, 128, 255]);
    assert_eq!(one_call(&facade), "sfp_write_eeprom('arg0', 2, b'\\x00\\x80\\xff')");
}

#[test]
fn sfp_is_flat_memory_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_is_flat_memory(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_is_flat_memory('arg0',)");
}

#[test]
fn sfp_get_module_type_abbreviation_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_module_type_abbreviation(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_module_type_abbreviation('arg0',)");
}

#[test]
fn sfp_is_coherent_module_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_is_coherent_module(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_is_coherent_module('arg0',)");
}

#[test]
fn sfp_get_module_state_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_module_state(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_module_state('arg0',)");
}

#[test]
fn sfp_get_cmis_rev_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_cmis_rev(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_cmis_rev('arg0',)");
}

#[test]
fn sfp_get_application_advertisement_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_application_advertisement(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_application_advertisement('arg0',)");
}

#[test]
fn sfp_get_datapath_state_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_datapath_state(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_datapath_state('arg0',)");
}

#[test]
fn sfp_get_config_datapath_hostlane_status_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_config_datapath_hostlane_status(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_config_datapath_hostlane_status('arg0',)");
}

#[test]
fn sfp_get_dpinit_pending_forwards() {
    let (mut p, facade) = platform();
    let _ = p.sfp_get_dpinit_pending(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "sfp_get_dpinit_pending('arg0',)");
}

#[test]
fn set_fan_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_fan_led(&DeviceKey::from("arg0"), LedColor::Green);
    assert_eq!(one_call(&facade), "set_fan_led('arg0', 'green')");
}

#[test]
fn set_fan_drawer_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_fan_drawer_led(&DeviceKey::from("arg0"), LedColor::Green);
    assert_eq!(one_call(&facade), "set_fan_drawer_led('arg0', 'green')");
}

#[test]
fn set_fan_speed_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_fan_speed(&DeviceKey::from("arg0"), 2);
    assert_eq!(one_call(&facade), "set_fan_speed('arg0', 2)");
}

#[test]
fn set_psu_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_psu_led(&DeviceKey::from("arg0"), LedColor::Green);
    assert_eq!(one_call(&facade), "set_psu_led('arg0', 'green')");
}

#[test]
fn get_module_reboot_cause_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_module_reboot_cause(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "get_module_reboot_cause('arg0',)");
}

#[test]
fn get_module_midplane_down_reason_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_module_midplane_down_reason(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "get_module_midplane_down_reason('arg0',)");
}

#[test]
fn get_psu_master_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_psu_master_led(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "get_psu_master_led('arg0',)");
}

#[test]
fn set_psu_master_led_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_psu_master_led(&DeviceKey::from("arg0"), LedColor::Green);
    assert_eq!(one_call(&facade), "set_psu_master_led('arg0', 'green')");
}

#[test]
fn reboot_module_forwards() {
    let (mut p, facade) = platform();
    let _ = p.reboot_module(&DeviceKey::from("arg0"), "arg1");
    assert_eq!(one_call(&facade), "reboot_module('arg0', 'arg1')");
}

#[test]
fn set_module_admin_state_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_module_admin_state(&DeviceKey::from("arg0"), true);
    assert_eq!(one_call(&facade), "set_module_admin_state('arg0', True)");
}

#[test]
fn set_module_admin_state_gracefully_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_module_admin_state_gracefully(&DeviceKey::from("arg0"), true);
    assert_eq!(one_call(&facade), "set_module_admin_state_gracefully('arg0', True)");
}

#[test]
fn power_cycle_module_forwards() {
    let (mut p, facade) = platform();
    let _ = p.power_cycle_module(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "power_cycle_module('arg0',)");
}

#[test]
fn module_pre_shutdown_forwards() {
    let (mut p, facade) = platform();
    let _ = p.module_pre_shutdown(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "module_pre_shutdown('arg0',)");
}

#[test]
fn module_post_startup_forwards() {
    let (mut p, facade) = platform();
    let _ = p.module_post_startup(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "module_post_startup('arg0',)");
}

#[test]
fn set_module_state_transition_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_module_state_transition(&DeviceKey::from("arg0"), "arg1");
    assert_eq!(one_call(&facade), "set_module_state_transition('arg0', 'arg1')");
}

#[test]
fn clear_module_state_transition_forwards() {
    let (mut p, facade) = platform();
    let _ = p.clear_module_state_transition(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "clear_module_state_transition('arg0',)");
}

#[test]
fn clear_module_gnoi_halt_forwards() {
    let (mut p, facade) = platform();
    let _ = p.clear_module_gnoi_halt(&DeviceKey::from("arg0"));
    assert_eq!(one_call(&facade), "clear_module_gnoi_halt('arg0',)");
}

#[test]
fn set_sensor_high_threshold_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_sensor_high_threshold(&DeviceKey::from("arg0"), Number::Int(2));
    assert_eq!(one_call(&facade), "set_sensor_high_threshold('arg0', 2)");
}

#[test]
fn set_sensor_low_threshold_forwards() {
    let (mut p, facade) = platform();
    let _ = p.set_sensor_low_threshold(&DeviceKey::from("arg0"), Number::Int(2));
    assert_eq!(one_call(&facade), "set_sensor_low_threshold('arg0', 2)");
}

#[test]
fn get_module_key_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_module_key("arg0");
    assert_eq!(one_call(&facade), "get_module_key('arg0',)");
}

#[test]
fn get_component_key_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_component_key("arg0");
    assert_eq!(one_call(&facade), "get_component_key('arg0',)");
}

#[test]
fn get_module_component_key_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_module_component_key("arg0", "arg1");
    assert_eq!(one_call(&facade), "get_module_component_key('arg0', 'arg1')");
}

#[test]
fn get_available_firmware_version_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_available_firmware_version(&DeviceKey::from("arg0"), "arg1");
    assert_eq!(one_call(&facade), "get_available_firmware_version('arg0', 'arg1')");
}

#[test]
fn get_firmware_update_notification_forwards() {
    let (mut p, facade) = platform();
    let _ = p.get_firmware_update_notification(&DeviceKey::from("arg0"), "arg1");
    assert_eq!(one_call(&facade), "get_firmware_update_notification('arg0', 'arg1')");
}

#[test]
fn install_firmware_forwards() {
    let (mut p, facade) = platform();
    let _ = p.install_firmware(&DeviceKey::from("arg0"), "arg1");
    assert_eq!(one_call(&facade), "install_firmware('arg0', 'arg1')");
}

#[test]
fn update_firmware_forwards() {
    let (mut p, facade) = platform();
    let _ = p.update_firmware(&DeviceKey::from("arg0"), "arg1");
    assert_eq!(one_call(&facade), "update_firmware('arg0', 'arg1')");
}

#[test]
fn auto_update_firmware_forwards() {
    let (mut p, facade) = platform();
    let _ = p.auto_update_firmware(&DeviceKey::from("arg0"), "arg1", "arg2");
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
    let _ = p.set_chassis_led("arg0");
    assert_eq!(one_call(&facade), "set_chassis_led('arg0',)");
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
fn tm_stop_forwards() {
    let (mut p, facade) = platform();
    let _ = p.tm_stop();
    assert_eq!(one_call(&facade), "tm_stop()");
}

#[test]
fn notify_shutdown_forwards() {
    let (mut p, facade) = platform();
    let _ = p.notify_shutdown();
    assert_eq!(one_call(&facade), "notify_shutdown()");
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
