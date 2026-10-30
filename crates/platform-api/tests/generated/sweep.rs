//! Every default the trait declares, every enum value and every column, run.
//!
//! GENERATED from sonic_platform_api/facade.pyi by generator/generate.py.  Do
//! not edit: regenerate.
//!
//! Nothing else calls a default: the bridge and the provider override every
//! method.  But the defaults are the contract a test double, or a native
//! implementation that is not finished, stands on -- an empty list where a
//! platform simply has none of a thing, `NotSupported` naming the method where
//! an empty answer would be a lie.  So each is called here on an
//! implementation that overrides nothing, and its answer is checked against
//! what the trait says it is.
//!
//! The enums and the column sets are spelled here and again in Python, from
//! the one stub.  Every value is round-tripped and every column's bit and name
//! read back, so a drift between the spellings fails here rather than in a DB
//! row.

use platform_api::*;

/// An implementation of nothing: every answer below is the trait's own.
struct Nothing;

impl PlatformApi for Nothing {}

#[test]
fn finalize_does_nothing_by_default() {
    Nothing.finalize();
}

#[test]
fn get_sfps_defaults_to_empty() {
    match Nothing.get_sfps() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_sfps is not the trait's default"),
    }
}

#[test]
fn get_chassis_info_defaults_to_not_supported() {
    match Nothing.get_chassis_info(ChassisInfoCols::ALL) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "get_chassis_info"),
        _ => panic!("get_chassis_info is not the trait's default"),
    }
}

#[test]
fn get_modules_defaults_to_empty() {
    match Nothing.get_modules(ModuleInfoCols::ALL) {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_modules is not the trait's default"),
    }
}

#[test]
fn get_thermals_defaults_to_empty() {
    match Nothing.get_thermals(ThermalInfoCols::ALL, &[DeviceKey::from("skip0"), DeviceKey::from("skip1")]) {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_thermals is not the trait's default"),
    }
}

#[test]
fn get_fans_defaults_to_empty() {
    match Nothing.get_fans(FanInfoCols::ALL, true) {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_fans is not the trait's default"),
    }
}

#[test]
fn get_fan_drawers_defaults_to_empty() {
    match Nothing.get_fan_drawers(FanDrawerInfoCols::ALL) {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_fan_drawers is not the trait's default"),
    }
}

#[test]
fn get_psus_defaults_to_empty() {
    match Nothing.get_psus() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_psus is not the trait's default"),
    }
}

#[test]
fn get_components_defaults_to_empty() {
    match Nothing.get_components() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_components is not the trait's default"),
    }
}

#[test]
fn get_sensors_defaults_to_empty() {
    match Nothing.get_sensors() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_sensors is not the trait's default"),
    }
}

#[test]
fn get_leak_profiles_defaults_to_empty() {
    match Nothing.get_leak_profiles() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_leak_profiles is not the trait's default"),
    }
}

#[test]
fn get_leak_sensors_defaults_to_empty() {
    match Nothing.get_leak_sensors() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_leak_sensors is not the trait's default"),
    }
}

#[test]
fn get_eeprom_defaults_to_empty() {
    match Nothing.get_eeprom() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_eeprom is not the trait's default"),
    }
}

#[test]
fn get_bmcs_defaults_to_empty() {
    match Nothing.get_bmcs() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_bmcs is not the trait's default"),
    }
}

#[test]
fn get_watchdogs_defaults_to_empty() {
    match Nothing.get_watchdogs() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_watchdogs is not the trait's default"),
    }
}

#[test]
fn sfp_get_presence_defaults_to_not_supported() {
    match Nothing.sfp_get_presence(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_presence"),
        _ => panic!("sfp_get_presence is not the trait's default"),
    }
}

#[test]
fn sfp_is_replaceable_defaults_to_not_supported() {
    match Nothing.sfp_is_replaceable(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_is_replaceable"),
        _ => panic!("sfp_is_replaceable is not the trait's default"),
    }
}

#[test]
fn sfp_get_reset_status_defaults_to_not_supported() {
    match Nothing.sfp_get_reset_status(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_reset_status"),
        _ => panic!("sfp_get_reset_status is not the trait's default"),
    }
}

#[test]
fn sfp_get_lpmode_defaults_to_not_supported() {
    match Nothing.sfp_get_lpmode(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_lpmode"),
        _ => panic!("sfp_get_lpmode is not the trait's default"),
    }
}

#[test]
fn sfp_get_error_description_defaults_to_not_supported() {
    match Nothing.sfp_get_error_description(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_error_description"),
        _ => panic!("sfp_get_error_description is not the trait's default"),
    }
}

#[test]
fn sfp_get_type_defaults_to_not_supported() {
    match Nothing.sfp_get_type(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_type"),
        _ => panic!("sfp_get_type is not the trait's default"),
    }
}

#[test]
fn sfp_has_method_defaults_to_not_supported() {
    match Nothing.sfp_has_method(&DeviceKey::from("arg0"), "arg1") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_has_method"),
        _ => panic!("sfp_has_method is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_info_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_info(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_info"),
        _ => panic!("sfp_get_transceiver_info is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_info_firmware_versions_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_info_firmware_versions(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_info_firmware_versions"),
        _ => panic!("sfp_get_transceiver_info_firmware_versions is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_status_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_status(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_status"),
        _ => panic!("sfp_get_transceiver_status is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_status_flags_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_status_flags(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_status_flags"),
        _ => panic!("sfp_get_transceiver_status_flags is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_dom_real_value_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_dom_real_value(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_dom_real_value"),
        _ => panic!("sfp_get_transceiver_dom_real_value is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_dom_flags_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_dom_flags(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_dom_flags"),
        _ => panic!("sfp_get_transceiver_dom_flags is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_threshold_info_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_threshold_info(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_threshold_info"),
        _ => panic!("sfp_get_transceiver_threshold_info is not the trait's default"),
    }
}

#[test]
fn sfp_get_temperature_defaults_to_not_supported() {
    match Nothing.sfp_get_temperature(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_temperature"),
        _ => panic!("sfp_get_temperature is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_pm_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_pm(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_pm"),
        _ => panic!("sfp_get_transceiver_pm is not the trait's default"),
    }
}

#[test]
fn sfp_is_transceiver_vdm_supported_defaults_to_not_supported() {
    match Nothing.sfp_is_transceiver_vdm_supported(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_is_transceiver_vdm_supported"),
        _ => panic!("sfp_is_transceiver_vdm_supported is not the trait's default"),
    }
}

#[test]
fn sfp_is_vdm_statistic_supported_defaults_to_not_supported() {
    match Nothing.sfp_is_vdm_statistic_supported(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_is_vdm_statistic_supported"),
        _ => panic!("sfp_is_vdm_statistic_supported is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_vdm_real_value_basic_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_vdm_real_value_basic(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_vdm_real_value_basic"),
        _ => panic!("sfp_get_transceiver_vdm_real_value_basic is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_vdm_real_value_statistic_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_vdm_real_value_statistic(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_vdm_real_value_statistic"),
        _ => panic!("sfp_get_transceiver_vdm_real_value_statistic is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_vdm_flags_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_vdm_flags(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_vdm_flags"),
        _ => panic!("sfp_get_transceiver_vdm_flags is not the trait's default"),
    }
}

#[test]
fn sfp_get_transceiver_vdm_thresholds_defaults_to_not_supported() {
    match Nothing.sfp_get_transceiver_vdm_thresholds(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_transceiver_vdm_thresholds"),
        _ => panic!("sfp_get_transceiver_vdm_thresholds is not the trait's default"),
    }
}

#[test]
fn sfp_get_vdm_freeze_status_defaults_to_not_supported() {
    match Nothing.sfp_get_vdm_freeze_status(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_vdm_freeze_status"),
        _ => panic!("sfp_get_vdm_freeze_status is not the trait's default"),
    }
}

#[test]
fn sfp_get_vdm_unfreeze_status_defaults_to_not_supported() {
    match Nothing.sfp_get_vdm_unfreeze_status(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_vdm_unfreeze_status"),
        _ => panic!("sfp_get_vdm_unfreeze_status is not the trait's default"),
    }
}

#[test]
fn sfp_set_lpmode_defaults_to_not_supported() {
    match Nothing.sfp_set_lpmode(&DeviceKey::from("arg0"), true) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_set_lpmode"),
        _ => panic!("sfp_set_lpmode is not the trait's default"),
    }
}

#[test]
fn sfp_reset_defaults_to_not_supported() {
    match Nothing.sfp_reset(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_reset"),
        _ => panic!("sfp_reset is not the trait's default"),
    }
}

#[test]
fn sfp_remove_xcvr_api_defaults_to_not_supported() {
    match Nothing.sfp_remove_xcvr_api(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_remove_xcvr_api"),
        _ => panic!("sfp_remove_xcvr_api is not the trait's default"),
    }
}

#[test]
fn sfp_freeze_vdm_stats_defaults_to_not_supported() {
    match Nothing.sfp_freeze_vdm_stats(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_freeze_vdm_stats"),
        _ => panic!("sfp_freeze_vdm_stats is not the trait's default"),
    }
}

#[test]
fn sfp_unfreeze_vdm_stats_defaults_to_not_supported() {
    match Nothing.sfp_unfreeze_vdm_stats(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_unfreeze_vdm_stats"),
        _ => panic!("sfp_unfreeze_vdm_stats is not the trait's default"),
    }
}

#[test]
fn sfp_read_eeprom_defaults_to_none() {
    match Nothing.sfp_read_eeprom(&DeviceKey::from("arg0"), 2, 3) {
        Ok(None) => {}
        _ => panic!("sfp_read_eeprom is not the trait's default"),
    }
}

#[test]
fn sfp_write_eeprom_defaults_to_none() {
    match Nothing.sfp_write_eeprom(&DeviceKey::from("arg0"), 2, &[0, 128, 255]) {
        Ok(None) => {}
        _ => panic!("sfp_write_eeprom is not the trait's default"),
    }
}

#[test]
fn sfp_is_flat_memory_defaults_to_not_supported() {
    match Nothing.sfp_is_flat_memory(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_is_flat_memory"),
        _ => panic!("sfp_is_flat_memory is not the trait's default"),
    }
}

#[test]
fn sfp_get_module_type_abbreviation_defaults_to_not_supported() {
    match Nothing.sfp_get_module_type_abbreviation(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_module_type_abbreviation"),
        _ => panic!("sfp_get_module_type_abbreviation is not the trait's default"),
    }
}

#[test]
fn sfp_is_coherent_module_defaults_to_not_supported() {
    match Nothing.sfp_is_coherent_module(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_is_coherent_module"),
        _ => panic!("sfp_is_coherent_module is not the trait's default"),
    }
}

#[test]
fn sfp_get_module_state_defaults_to_not_supported() {
    match Nothing.sfp_get_module_state(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_module_state"),
        _ => panic!("sfp_get_module_state is not the trait's default"),
    }
}

#[test]
fn sfp_get_cmis_rev_defaults_to_not_supported() {
    match Nothing.sfp_get_cmis_rev(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_cmis_rev"),
        _ => panic!("sfp_get_cmis_rev is not the trait's default"),
    }
}

#[test]
fn sfp_get_application_advertisement_defaults_to_not_supported() {
    match Nothing.sfp_get_application_advertisement(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_application_advertisement"),
        _ => panic!("sfp_get_application_advertisement is not the trait's default"),
    }
}

#[test]
fn sfp_get_datapath_state_defaults_to_not_supported() {
    match Nothing.sfp_get_datapath_state(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_datapath_state"),
        _ => panic!("sfp_get_datapath_state is not the trait's default"),
    }
}

#[test]
fn sfp_get_config_datapath_hostlane_status_defaults_to_not_supported() {
    match Nothing.sfp_get_config_datapath_hostlane_status(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_config_datapath_hostlane_status"),
        _ => panic!("sfp_get_config_datapath_hostlane_status is not the trait's default"),
    }
}

#[test]
fn sfp_get_dpinit_pending_defaults_to_not_supported() {
    match Nothing.sfp_get_dpinit_pending(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "sfp_get_dpinit_pending"),
        _ => panic!("sfp_get_dpinit_pending is not the trait's default"),
    }
}

#[test]
fn set_fan_led_defaults_to_not_supported() {
    match Nothing.set_fan_led(&DeviceKey::from("arg0"), LedColor::Green) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_fan_led"),
        _ => panic!("set_fan_led is not the trait's default"),
    }
}

#[test]
fn set_fan_drawer_led_defaults_to_not_supported() {
    match Nothing.set_fan_drawer_led(&DeviceKey::from("arg0"), LedColor::Green) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_fan_drawer_led"),
        _ => panic!("set_fan_drawer_led is not the trait's default"),
    }
}

#[test]
fn set_fan_speed_defaults_to_not_supported() {
    match Nothing.set_fan_speed(&DeviceKey::from("arg0"), 2) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_fan_speed"),
        _ => panic!("set_fan_speed is not the trait's default"),
    }
}

#[test]
fn set_psu_led_defaults_to_not_supported() {
    match Nothing.set_psu_led(&DeviceKey::from("arg0"), LedColor::Green) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_psu_led"),
        _ => panic!("set_psu_led is not the trait's default"),
    }
}

#[test]
fn get_module_reboot_cause_defaults_to_not_supported() {
    match Nothing.get_module_reboot_cause(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "get_module_reboot_cause"),
        _ => panic!("get_module_reboot_cause is not the trait's default"),
    }
}

#[test]
fn get_module_midplane_down_reason_defaults_to_not_supported() {
    match Nothing.get_module_midplane_down_reason(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "get_module_midplane_down_reason"),
        _ => panic!("get_module_midplane_down_reason is not the trait's default"),
    }
}

#[test]
fn get_psu_master_led_defaults_to_not_supported() {
    match Nothing.get_psu_master_led(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "get_psu_master_led"),
        _ => panic!("get_psu_master_led is not the trait's default"),
    }
}

#[test]
fn set_psu_master_led_defaults_to_not_supported() {
    match Nothing.set_psu_master_led(&DeviceKey::from("arg0"), LedColor::Green) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_psu_master_led"),
        _ => panic!("set_psu_master_led is not the trait's default"),
    }
}

#[test]
fn reboot_module_defaults_to_not_supported() {
    match Nothing.reboot_module(&DeviceKey::from("arg0"), "arg1") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "reboot_module"),
        _ => panic!("reboot_module is not the trait's default"),
    }
}

#[test]
fn set_module_admin_state_defaults_to_not_supported() {
    match Nothing.set_module_admin_state(&DeviceKey::from("arg0"), true) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_module_admin_state"),
        _ => panic!("set_module_admin_state is not the trait's default"),
    }
}

#[test]
fn set_module_admin_state_gracefully_defaults_to_not_supported() {
    match Nothing.set_module_admin_state_gracefully(&DeviceKey::from("arg0"), true) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_module_admin_state_gracefully"),
        _ => panic!("set_module_admin_state_gracefully is not the trait's default"),
    }
}

#[test]
fn power_cycle_module_defaults_to_not_supported() {
    match Nothing.power_cycle_module(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "power_cycle_module"),
        _ => panic!("power_cycle_module is not the trait's default"),
    }
}

#[test]
fn module_pre_shutdown_defaults_to_not_supported() {
    match Nothing.module_pre_shutdown(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "module_pre_shutdown"),
        _ => panic!("module_pre_shutdown is not the trait's default"),
    }
}

#[test]
fn module_post_startup_defaults_to_not_supported() {
    match Nothing.module_post_startup(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "module_post_startup"),
        _ => panic!("module_post_startup is not the trait's default"),
    }
}

#[test]
fn set_module_state_transition_defaults_to_not_supported() {
    match Nothing.set_module_state_transition(&DeviceKey::from("arg0"), "arg1") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_module_state_transition"),
        _ => panic!("set_module_state_transition is not the trait's default"),
    }
}

#[test]
fn clear_module_state_transition_defaults_to_not_supported() {
    match Nothing.clear_module_state_transition(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "clear_module_state_transition"),
        _ => panic!("clear_module_state_transition is not the trait's default"),
    }
}

#[test]
fn clear_module_gnoi_halt_defaults_to_not_supported() {
    match Nothing.clear_module_gnoi_halt(&DeviceKey::from("arg0")) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "clear_module_gnoi_halt"),
        _ => panic!("clear_module_gnoi_halt is not the trait's default"),
    }
}

#[test]
fn set_sensor_high_threshold_defaults_to_not_supported() {
    match Nothing.set_sensor_high_threshold(&DeviceKey::from("arg0"), Number::Int(2)) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_sensor_high_threshold"),
        _ => panic!("set_sensor_high_threshold is not the trait's default"),
    }
}

#[test]
fn set_sensor_low_threshold_defaults_to_not_supported() {
    match Nothing.set_sensor_low_threshold(&DeviceKey::from("arg0"), Number::Int(2)) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_sensor_low_threshold"),
        _ => panic!("set_sensor_low_threshold is not the trait's default"),
    }
}

#[test]
fn get_module_key_defaults_to_none() {
    match Nothing.get_module_key("arg0") {
        Ok(None) => {}
        _ => panic!("get_module_key is not the trait's default"),
    }
}

#[test]
fn get_component_key_defaults_to_none() {
    match Nothing.get_component_key("arg0") {
        Ok(None) => {}
        _ => panic!("get_component_key is not the trait's default"),
    }
}

#[test]
fn get_module_component_key_defaults_to_none() {
    match Nothing.get_module_component_key("arg0", "arg1") {
        Ok(None) => {}
        _ => panic!("get_module_component_key is not the trait's default"),
    }
}

#[test]
fn get_available_firmware_version_defaults_to_not_supported() {
    match Nothing.get_available_firmware_version(&DeviceKey::from("arg0"), "arg1") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "get_available_firmware_version"),
        _ => panic!("get_available_firmware_version is not the trait's default"),
    }
}

#[test]
fn get_firmware_update_notification_defaults_to_not_supported() {
    match Nothing.get_firmware_update_notification(&DeviceKey::from("arg0"), "arg1") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "get_firmware_update_notification"),
        _ => panic!("get_firmware_update_notification is not the trait's default"),
    }
}

#[test]
fn install_firmware_defaults_to_not_supported() {
    match Nothing.install_firmware(&DeviceKey::from("arg0"), "arg1") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "install_firmware"),
        _ => panic!("install_firmware is not the trait's default"),
    }
}

#[test]
fn update_firmware_defaults_to_not_supported() {
    match Nothing.update_firmware(&DeviceKey::from("arg0"), "arg1") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "update_firmware"),
        _ => panic!("update_firmware is not the trait's default"),
    }
}

#[test]
fn auto_update_firmware_defaults_to_not_supported() {
    match Nothing.auto_update_firmware(&DeviceKey::from("arg0"), "arg1", "arg2") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "auto_update_firmware"),
        _ => panic!("auto_update_firmware is not the trait's default"),
    }
}

#[test]
fn arm_watchdog_defaults_to_not_supported() {
    match Nothing.arm_watchdog(1) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "arm_watchdog"),
        _ => panic!("arm_watchdog is not the trait's default"),
    }
}

#[test]
fn disarm_watchdog_defaults_to_not_supported() {
    match Nothing.disarm_watchdog() {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "disarm_watchdog"),
        _ => panic!("disarm_watchdog is not the trait's default"),
    }
}

#[test]
fn initialize_system_led_defaults_to_not_supported() {
    match Nothing.initialize_system_led() {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "initialize_system_led"),
        _ => panic!("initialize_system_led is not the trait's default"),
    }
}

#[test]
fn init_midplane_switch_defaults_to_not_supported() {
    match Nothing.init_midplane_switch() {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "init_midplane_switch"),
        _ => panic!("init_midplane_switch is not the trait's default"),
    }
}

#[test]
fn set_chassis_led_defaults_to_not_supported() {
    match Nothing.set_chassis_led("arg0") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "set_chassis_led"),
        _ => panic!("set_chassis_led is not the trait's default"),
    }
}

#[test]
fn change_sed_password_defaults_to_not_supported() {
    match Nothing.change_sed_password("arg0") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "change_sed_password"),
        _ => panic!("change_sed_password is not the trait's default"),
    }
}

#[test]
fn reset_sed_password_defaults_to_not_supported() {
    match Nothing.reset_sed_password() {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "reset_sed_password"),
        _ => panic!("reset_sed_password is not the trait's default"),
    }
}

#[test]
fn bmc_open_session_defaults_to_not_supported() {
    match Nothing.bmc_open_session() {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "bmc_open_session"),
        _ => panic!("bmc_open_session is not the trait's default"),
    }
}

#[test]
fn bmc_close_session_defaults_to_not_supported() {
    match Nothing.bmc_close_session("arg0") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "bmc_close_session"),
        _ => panic!("bmc_close_session is not the trait's default"),
    }
}

#[test]
fn bmc_reset_root_password_defaults_to_not_supported() {
    match Nothing.bmc_reset_root_password() {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "bmc_reset_root_password"),
        _ => panic!("bmc_reset_root_password is not the trait's default"),
    }
}

#[test]
fn bmc_reset_defaults_to_not_supported() {
    match Nothing.bmc_reset(true) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "bmc_reset"),
        _ => panic!("bmc_reset is not the trait's default"),
    }
}

#[test]
fn bmc_update_firmware_defaults_to_not_supported() {
    match Nothing.bmc_update_firmware("arg0") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "bmc_update_firmware"),
        _ => panic!("bmc_update_firmware is not the trait's default"),
    }
}

#[test]
fn bmc_trigger_debug_log_dump_defaults_to_not_supported() {
    match Nothing.bmc_trigger_debug_log_dump() {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "bmc_trigger_debug_log_dump"),
        _ => panic!("bmc_trigger_debug_log_dump is not the trait's default"),
    }
}

#[test]
fn bmc_get_debug_log_dump_defaults_to_not_supported() {
    match Nothing.bmc_get_debug_log_dump("arg0", "arg1", "arg2") {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "bmc_get_debug_log_dump"),
        _ => panic!("bmc_get_debug_log_dump is not the trait's default"),
    }
}

#[test]
fn get_asics_defaults_to_empty() {
    match Nothing.get_asics() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_asics is not the trait's default"),
    }
}

#[test]
fn tm_initialize_defaults_to_nothing() {
    match Nothing.tm_initialize() {
        Ok(()) => {}
        _ => panic!("tm_initialize is not the trait's default"),
    }
}

#[test]
fn tm_run_policy_defaults_to_nothing() {
    match Nothing.tm_run_policy() {
        Ok(()) => {}
        _ => panic!("tm_run_policy is not the trait's default"),
    }
}

#[test]
fn tm_get_interval_defaults_to_none() {
    match Nothing.tm_get_interval() {
        Ok(None) => {}
        _ => panic!("tm_get_interval is not the trait's default"),
    }
}

#[test]
fn tm_deinitialize_defaults_to_nothing() {
    match Nothing.tm_deinitialize() {
        Ok(()) => {}
        _ => panic!("tm_deinitialize is not the trait's default"),
    }
}

#[test]
fn tm_stop_defaults_to_nothing() {
    match Nothing.tm_stop() {
        Ok(()) => {}
        _ => panic!("tm_stop is not the trait's default"),
    }
}

#[test]
fn notify_shutdown_defaults_to_nothing() {
    match Nothing.notify_shutdown() {
        Ok(()) => {}
        _ => panic!("notify_shutdown is not the trait's default"),
    }
}

#[test]
fn eeprom_update_db_defaults_to_not_supported() {
    match Nothing.eeprom_update_db() {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "eeprom_update_db"),
        _ => panic!("eeprom_update_db is not the trait's default"),
    }
}

#[test]
fn get_storage_devices_defaults_to_empty() {
    match Nothing.get_storage_devices() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_storage_devices is not the trait's default"),
    }
}

#[test]
fn get_pcie_devices_defaults_to_empty() {
    match Nothing.get_pcie_devices() {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_pcie_devices is not the trait's default"),
    }
}

#[test]
fn get_pcie_aer_stats_defaults_to_empty() {
    match Nothing.get_pcie_aer_stats(1, 2, 3) {
        Ok(rows) => assert!(rows.is_empty()),
        _ => panic!("get_pcie_aer_stats is not the trait's default"),
    }
}

#[test]
fn get_change_event_defaults_to_not_supported() {
    match Nothing.get_change_event(1) {
        Err(PlatformError::NotSupported(what)) => assert_eq!(what, "get_change_event"),
        _ => panic!("get_change_event is not the trait's default"),
    }
}

#[test]
fn every_led_color_value_round_trips() {
    assert_eq!(LedColor::from_str("green"), Some(LedColor::Green));
    assert_eq!(LedColor::Green.to_string(), "green");
    assert_eq!(LedColor::from_str("amber"), Some(LedColor::Amber));
    assert_eq!(LedColor::Amber.to_string(), "amber");
    assert_eq!(LedColor::from_str("red"), Some(LedColor::Red));
    assert_eq!(LedColor::Red.to_string(), "red");
    assert_eq!(LedColor::from_str("off"), Some(LedColor::Off));
    assert_eq!(LedColor::Off.to_string(), "off");
    assert_eq!(LedColor::from_str("undeclared"), None);
}

#[test]
fn every_fan_kind_value_round_trips() {
    assert_eq!(FanKind::from_str("drawer"), Some(FanKind::Drawer));
    assert_eq!(FanKind::Drawer.to_string(), "drawer");
    assert_eq!(FanKind::from_str("module"), Some(FanKind::Module));
    assert_eq!(FanKind::Module.to_string(), "module");
    assert_eq!(FanKind::from_str("psu"), Some(FanKind::Psu));
    assert_eq!(FanKind::Psu.to_string(), "psu");
    assert_eq!(FanKind::from_str("pdb"), Some(FanKind::Pdb));
    assert_eq!(FanKind::Pdb.to_string(), "pdb");
    assert_eq!(FanKind::from_str("undeclared"), None);
}

#[test]
fn every_power_entity_kind_value_round_trips() {
    assert_eq!(PowerEntityKind::from_str("psu"), Some(PowerEntityKind::Psu));
    assert_eq!(PowerEntityKind::Psu.to_string(), "psu");
    assert_eq!(PowerEntityKind::from_str("pdb"), Some(PowerEntityKind::Pdb));
    assert_eq!(PowerEntityKind::Pdb.to_string(), "pdb");
    assert_eq!(PowerEntityKind::from_str("undeclared"), None);
}

#[test]
fn every_thermal_kind_value_round_trips() {
    assert_eq!(ThermalKind::from_str("chassis"), Some(ThermalKind::Chassis));
    assert_eq!(ThermalKind::Chassis.to_string(), "chassis");
    assert_eq!(ThermalKind::from_str("psu"), Some(ThermalKind::Psu));
    assert_eq!(ThermalKind::Psu.to_string(), "psu");
    assert_eq!(ThermalKind::from_str("pdb"), Some(ThermalKind::Pdb));
    assert_eq!(ThermalKind::Pdb.to_string(), "pdb");
    assert_eq!(ThermalKind::from_str("module"), Some(ThermalKind::Module));
    assert_eq!(ThermalKind::Module.to_string(), "module");
    assert_eq!(ThermalKind::from_str("module_psu"), Some(ThermalKind::ModulePsu));
    assert_eq!(ThermalKind::ModulePsu.to_string(), "module_psu");
    assert_eq!(ThermalKind::from_str("undeclared"), None);
}

#[test]
fn every_module_type_value_round_trips() {
    assert_eq!(ModuleType::from_str("SUPERVISOR"), Some(ModuleType::Supervisor));
    assert_eq!(ModuleType::Supervisor.to_string(), "SUPERVISOR");
    assert_eq!(ModuleType::from_str("LINE-CARD"), Some(ModuleType::LineCard));
    assert_eq!(ModuleType::LineCard.to_string(), "LINE-CARD");
    assert_eq!(ModuleType::from_str("FABRIC-CARD"), Some(ModuleType::FabricCard));
    assert_eq!(ModuleType::FabricCard.to_string(), "FABRIC-CARD");
    assert_eq!(ModuleType::from_str("DPU"), Some(ModuleType::Dpu));
    assert_eq!(ModuleType::Dpu.to_string(), "DPU");
    assert_eq!(ModuleType::from_str("SWITCH-HOST"), Some(ModuleType::SwitchHost));
    assert_eq!(ModuleType::SwitchHost.to_string(), "SWITCH-HOST");
    assert_eq!(ModuleType::from_str("undeclared"), None);
}

#[test]
fn every_module_status_value_round_trips() {
    assert_eq!(ModuleStatus::from_str("Empty"), Some(ModuleStatus::Empty));
    assert_eq!(ModuleStatus::Empty.to_string(), "Empty");
    assert_eq!(ModuleStatus::from_str("Offline"), Some(ModuleStatus::Offline));
    assert_eq!(ModuleStatus::Offline.to_string(), "Offline");
    assert_eq!(ModuleStatus::from_str("PoweredDown"), Some(ModuleStatus::PoweredDown));
    assert_eq!(ModuleStatus::PoweredDown.to_string(), "PoweredDown");
    assert_eq!(ModuleStatus::from_str("Present"), Some(ModuleStatus::Present));
    assert_eq!(ModuleStatus::Present.to_string(), "Present");
    assert_eq!(ModuleStatus::from_str("Fault"), Some(ModuleStatus::Fault));
    assert_eq!(ModuleStatus::Fault.to_string(), "Fault");
    assert_eq!(ModuleStatus::from_str("ProvisionReady"), Some(ModuleStatus::ProvisionReady));
    assert_eq!(ModuleStatus::ProvisionReady.to_string(), "ProvisionReady");
    assert_eq!(ModuleStatus::from_str("ProvisionPending"), Some(ModuleStatus::ProvisionPending));
    assert_eq!(ModuleStatus::ProvisionPending.to_string(), "ProvisionPending");
    assert_eq!(ModuleStatus::from_str("Provisioned"), Some(ModuleStatus::Provisioned));
    assert_eq!(ModuleStatus::Provisioned.to_string(), "Provisioned");
    assert_eq!(ModuleStatus::from_str("Online"), Some(ModuleStatus::Online));
    assert_eq!(ModuleStatus::Online.to_string(), "Online");
    assert_eq!(ModuleStatus::from_str("undeclared"), None);
}

#[test]
fn every_sensor_kind_value_round_trips() {
    assert_eq!(SensorKind::from_str("voltage"), Some(SensorKind::Voltage));
    assert_eq!(SensorKind::Voltage.to_string(), "voltage");
    assert_eq!(SensorKind::from_str("current"), Some(SensorKind::Current));
    assert_eq!(SensorKind::Current.to_string(), "current");
    assert_eq!(SensorKind::from_str("undeclared"), None);
}

#[test]
fn every_eeprom_update_value_round_trips() {
    assert_eq!(EepromUpdate::from_str("updated"), Some(EepromUpdate::Updated));
    assert_eq!(EepromUpdate::Updated.to_string(), "updated");
    assert_eq!(EepromUpdate::from_str("read_failed"), Some(EepromUpdate::ReadFailed));
    assert_eq!(EepromUpdate::ReadFailed.to_string(), "read_failed");
    assert_eq!(EepromUpdate::from_str("update_failed"), Some(EepromUpdate::UpdateFailed));
    assert_eq!(EepromUpdate::UpdateFailed.to_string(), "update_failed");
    assert_eq!(EepromUpdate::from_str("undeclared"), None);
}

#[test]
fn every_leak_severity_value_round_trips() {
    assert_eq!(LeakSeverity::from_str("MINOR"), Some(LeakSeverity::Minor));
    assert_eq!(LeakSeverity::Minor.to_string(), "MINOR");
    assert_eq!(LeakSeverity::from_str("CRITICAL"), Some(LeakSeverity::Critical));
    assert_eq!(LeakSeverity::Critical.to_string(), "CRITICAL");
    assert_eq!(LeakSeverity::from_str("undeclared"), None);
}

#[test]
fn every_change_event_kind_value_round_trips() {
    assert_eq!(ChangeEventKind::from_str("removed"), Some(ChangeEventKind::Removed));
    assert_eq!(ChangeEventKind::Removed.to_string(), "removed");
    assert_eq!(ChangeEventKind::from_str("inserted"), Some(ChangeEventKind::Inserted));
    assert_eq!(ChangeEventKind::Inserted.to_string(), "inserted");
    assert_eq!(ChangeEventKind::from_str("i2c_stuck"), Some(ChangeEventKind::I2cStuck));
    assert_eq!(ChangeEventKind::I2cStuck.to_string(), "i2c_stuck");
    assert_eq!(ChangeEventKind::from_str("bad_eeprom"), Some(ChangeEventKind::BadEeprom));
    assert_eq!(ChangeEventKind::BadEeprom.to_string(), "bad_eeprom");
    assert_eq!(ChangeEventKind::from_str("unsupported_cable"), Some(ChangeEventKind::UnsupportedCable));
    assert_eq!(ChangeEventKind::UnsupportedCable.to_string(), "unsupported_cable");
    assert_eq!(ChangeEventKind::from_str("high_temperature"), Some(ChangeEventKind::HighTemperature));
    assert_eq!(ChangeEventKind::HighTemperature.to_string(), "high_temperature");
    assert_eq!(ChangeEventKind::from_str("bad_cable"), Some(ChangeEventKind::BadCable));
    assert_eq!(ChangeEventKind::BadCable.to_string(), "bad_cable");
    assert_eq!(ChangeEventKind::from_str("undeclared"), None);
}

#[test]
fn every_thermal_info_column_has_a_bit_and_a_name_of_its_own() {
    let mut seen = ThermalInfoCols::NONE;
    for col in ThermalInfoCol::ALL {
        assert!(!seen.contains(*col), "{} shares a bit", col.as_str());
        seen = seen.with(ThermalInfoCols::of(*col));
    }
    assert_eq!(seen, ThermalInfoCols::ALL);
    assert_eq!(seen.bits(), ThermalInfoCols::ALL.bits());
    assert_eq!(ThermalInfoCol::PositionInParent.as_str(), "position_in_parent");
    assert_eq!(ThermalInfoCols::POSITION_IN_PARENT, ThermalInfoCols::of(ThermalInfoCol::PositionInParent));
    assert_eq!(ThermalInfoCol::Temperature.as_str(), "temperature");
    assert_eq!(ThermalInfoCols::TEMPERATURE, ThermalInfoCols::of(ThermalInfoCol::Temperature));
    assert_eq!(ThermalInfoCol::IsReplaceable.as_str(), "is_replaceable");
    assert_eq!(ThermalInfoCols::IS_REPLACEABLE, ThermalInfoCols::of(ThermalInfoCol::IsReplaceable));
    assert_eq!(ThermalInfoCol::MinRecorded.as_str(), "min_recorded");
    assert_eq!(ThermalInfoCols::MIN_RECORDED, ThermalInfoCols::of(ThermalInfoCol::MinRecorded));
    assert_eq!(ThermalInfoCol::MaxRecorded.as_str(), "max_recorded");
    assert_eq!(ThermalInfoCols::MAX_RECORDED, ThermalInfoCols::of(ThermalInfoCol::MaxRecorded));
    assert_eq!(ThermalInfoCol::HighThreshold.as_str(), "high_threshold");
    assert_eq!(ThermalInfoCols::HIGH_THRESHOLD, ThermalInfoCols::of(ThermalInfoCol::HighThreshold));
    assert_eq!(ThermalInfoCol::LowThreshold.as_str(), "low_threshold");
    assert_eq!(ThermalInfoCols::LOW_THRESHOLD, ThermalInfoCols::of(ThermalInfoCol::LowThreshold));
    assert_eq!(ThermalInfoCol::HighCriticalThreshold.as_str(), "high_critical_threshold");
    assert_eq!(ThermalInfoCols::HIGH_CRITICAL_THRESHOLD, ThermalInfoCols::of(ThermalInfoCol::HighCriticalThreshold));
    assert_eq!(ThermalInfoCol::LowCriticalThreshold.as_str(), "low_critical_threshold");
    assert_eq!(ThermalInfoCols::LOW_CRITICAL_THRESHOLD, ThermalInfoCols::of(ThermalInfoCol::LowCriticalThreshold));
    assert_eq!(format!("{:?}", ThermalInfoCols::NONE), "ThermalInfoCols[]");
    assert!(format!("{:?}", ThermalInfoCols::ALL).starts_with("ThermalInfoCols["));
}

#[test]
fn every_fan_info_column_has_a_bit_and_a_name_of_its_own() {
    let mut seen = FanInfoCols::NONE;
    for col in FanInfoCol::ALL {
        assert!(!seen.contains(*col), "{} shares a bit", col.as_str());
        seen = seen.with(FanInfoCols::of(*col));
    }
    assert_eq!(seen, FanInfoCols::ALL);
    assert_eq!(seen.bits(), FanInfoCols::ALL.bits());
    assert_eq!(FanInfoCol::PositionInParent.as_str(), "position_in_parent");
    assert_eq!(FanInfoCols::POSITION_IN_PARENT, FanInfoCols::of(FanInfoCol::PositionInParent));
    assert_eq!(FanInfoCol::IsReplaceable.as_str(), "is_replaceable");
    assert_eq!(FanInfoCols::IS_REPLACEABLE, FanInfoCols::of(FanInfoCol::IsReplaceable));
    assert_eq!(FanInfoCol::Presence.as_str(), "presence");
    assert_eq!(FanInfoCols::PRESENCE, FanInfoCols::of(FanInfoCol::Presence));
    assert_eq!(FanInfoCol::SpeedPct.as_str(), "speed_pct");
    assert_eq!(FanInfoCols::SPEED_PCT, FanInfoCols::of(FanInfoCol::SpeedPct));
    assert_eq!(FanInfoCol::TargetSpeedPct.as_str(), "target_speed_pct");
    assert_eq!(FanInfoCols::TARGET_SPEED_PCT, FanInfoCols::of(FanInfoCol::TargetSpeedPct));
    assert_eq!(FanInfoCol::IsUnderSpeed.as_str(), "is_under_speed");
    assert_eq!(FanInfoCols::IS_UNDER_SPEED, FanInfoCols::of(FanInfoCol::IsUnderSpeed));
    assert_eq!(FanInfoCol::IsOverSpeed.as_str(), "is_over_speed");
    assert_eq!(FanInfoCols::IS_OVER_SPEED, FanInfoCols::of(FanInfoCol::IsOverSpeed));
    assert_eq!(FanInfoCol::Status.as_str(), "status");
    assert_eq!(FanInfoCols::STATUS, FanInfoCols::of(FanInfoCol::Status));
    assert_eq!(FanInfoCol::Direction.as_str(), "direction");
    assert_eq!(FanInfoCols::DIRECTION, FanInfoCols::of(FanInfoCol::Direction));
    assert_eq!(FanInfoCol::Model.as_str(), "model");
    assert_eq!(FanInfoCols::MODEL, FanInfoCols::of(FanInfoCol::Model));
    assert_eq!(FanInfoCol::Serial.as_str(), "serial");
    assert_eq!(FanInfoCols::SERIAL, FanInfoCols::of(FanInfoCol::Serial));
    assert_eq!(FanInfoCol::StatusLed.as_str(), "status_led");
    assert_eq!(FanInfoCols::STATUS_LED, FanInfoCols::of(FanInfoCol::StatusLed));
    assert_eq!(format!("{:?}", FanInfoCols::NONE), "FanInfoCols[]");
    assert!(format!("{:?}", FanInfoCols::ALL).starts_with("FanInfoCols["));
}

#[test]
fn every_fan_drawer_info_column_has_a_bit_and_a_name_of_its_own() {
    let mut seen = FanDrawerInfoCols::NONE;
    for col in FanDrawerInfoCol::ALL {
        assert!(!seen.contains(*col), "{} shares a bit", col.as_str());
        seen = seen.with(FanDrawerInfoCols::of(*col));
    }
    assert_eq!(seen, FanDrawerInfoCols::ALL);
    assert_eq!(seen.bits(), FanDrawerInfoCols::ALL.bits());
    assert_eq!(FanDrawerInfoCol::PositionInParent.as_str(), "position_in_parent");
    assert_eq!(FanDrawerInfoCols::POSITION_IN_PARENT, FanDrawerInfoCols::of(FanDrawerInfoCol::PositionInParent));
    assert_eq!(FanDrawerInfoCol::Presence.as_str(), "presence");
    assert_eq!(FanDrawerInfoCols::PRESENCE, FanDrawerInfoCols::of(FanDrawerInfoCol::Presence));
    assert_eq!(FanDrawerInfoCol::Status.as_str(), "status");
    assert_eq!(FanDrawerInfoCols::STATUS, FanDrawerInfoCols::of(FanDrawerInfoCol::Status));
    assert_eq!(FanDrawerInfoCol::IsReplaceable.as_str(), "is_replaceable");
    assert_eq!(FanDrawerInfoCols::IS_REPLACEABLE, FanDrawerInfoCols::of(FanDrawerInfoCol::IsReplaceable));
    assert_eq!(FanDrawerInfoCol::Model.as_str(), "model");
    assert_eq!(FanDrawerInfoCols::MODEL, FanDrawerInfoCols::of(FanDrawerInfoCol::Model));
    assert_eq!(FanDrawerInfoCol::Serial.as_str(), "serial");
    assert_eq!(FanDrawerInfoCols::SERIAL, FanDrawerInfoCols::of(FanDrawerInfoCol::Serial));
    assert_eq!(FanDrawerInfoCol::StatusLed.as_str(), "status_led");
    assert_eq!(FanDrawerInfoCols::STATUS_LED, FanDrawerInfoCols::of(FanDrawerInfoCol::StatusLed));
    assert_eq!(FanDrawerInfoCol::MaximumConsumedPower.as_str(), "maximum_consumed_power");
    assert_eq!(FanDrawerInfoCols::MAXIMUM_CONSUMED_POWER, FanDrawerInfoCols::of(FanDrawerInfoCol::MaximumConsumedPower));
    assert_eq!(format!("{:?}", FanDrawerInfoCols::NONE), "FanDrawerInfoCols[]");
    assert!(format!("{:?}", FanDrawerInfoCols::ALL).starts_with("FanDrawerInfoCols["));
}

#[test]
fn every_chassis_info_column_has_a_bit_and_a_name_of_its_own() {
    let mut seen = ChassisInfoCols::NONE;
    for col in ChassisInfoCol::ALL {
        assert!(!seen.contains(*col), "{} shares a bit", col.as_str());
        seen = seen.with(ChassisInfoCols::of(*col));
    }
    assert_eq!(seen, ChassisInfoCols::ALL);
    assert_eq!(seen.bits(), ChassisInfoCols::ALL.bits());
    assert_eq!(ChassisInfoCol::Name.as_str(), "name");
    assert_eq!(ChassisInfoCols::NAME, ChassisInfoCols::of(ChassisInfoCol::Name));
    assert_eq!(ChassisInfoCol::Presence.as_str(), "presence");
    assert_eq!(ChassisInfoCols::PRESENCE, ChassisInfoCols::of(ChassisInfoCol::Presence));
    assert_eq!(ChassisInfoCol::Model.as_str(), "model");
    assert_eq!(ChassisInfoCols::MODEL, ChassisInfoCols::of(ChassisInfoCol::Model));
    assert_eq!(ChassisInfoCol::Serial.as_str(), "serial");
    assert_eq!(ChassisInfoCols::SERIAL, ChassisInfoCols::of(ChassisInfoCol::Serial));
    assert_eq!(ChassisInfoCol::Revision.as_str(), "revision");
    assert_eq!(ChassisInfoCols::REVISION, ChassisInfoCols::of(ChassisInfoCol::Revision));
    assert_eq!(ChassisInfoCol::Status.as_str(), "status");
    assert_eq!(ChassisInfoCols::STATUS, ChassisInfoCols::of(ChassisInfoCol::Status));
    assert_eq!(ChassisInfoCol::BaseMac.as_str(), "base_mac");
    assert_eq!(ChassisInfoCols::BASE_MAC, ChassisInfoCols::of(ChassisInfoCol::BaseMac));
    assert_eq!(ChassisInfoCol::IsModularChassis.as_str(), "is_modular_chassis");
    assert_eq!(ChassisInfoCols::IS_MODULAR_CHASSIS, ChassisInfoCols::of(ChassisInfoCol::IsModularChassis));
    assert_eq!(ChassisInfoCol::IsSmartswitch.as_str(), "is_smartswitch");
    assert_eq!(ChassisInfoCols::IS_SMARTSWITCH, ChassisInfoCols::of(ChassisInfoCol::IsSmartswitch));
    assert_eq!(ChassisInfoCol::IsDpu.as_str(), "is_dpu");
    assert_eq!(ChassisInfoCols::IS_DPU, ChassisInfoCols::of(ChassisInfoCol::IsDpu));
    assert_eq!(ChassisInfoCol::IsBmc.as_str(), "is_bmc");
    assert_eq!(ChassisInfoCols::IS_BMC, ChassisInfoCols::of(ChassisInfoCol::IsBmc));
    assert_eq!(ChassisInfoCol::IsLiquidCooled.as_str(), "is_liquid_cooled");
    assert_eq!(ChassisInfoCols::IS_LIQUID_COOLED, ChassisInfoCols::of(ChassisInfoCol::IsLiquidCooled));
    assert_eq!(ChassisInfoCol::RebootCause.as_str(), "reboot_cause");
    assert_eq!(ChassisInfoCols::REBOOT_CAUSE, ChassisInfoCols::of(ChassisInfoCol::RebootCause));
    assert_eq!(ChassisInfoCol::RebootCauseDetail.as_str(), "reboot_cause_detail");
    assert_eq!(ChassisInfoCols::REBOOT_CAUSE_DETAIL, ChassisInfoCols::of(ChassisInfoCol::RebootCauseDetail));
    assert_eq!(ChassisInfoCol::MySlot.as_str(), "my_slot");
    assert_eq!(ChassisInfoCols::MY_SLOT, ChassisInfoCols::of(ChassisInfoCol::MySlot));
    assert_eq!(ChassisInfoCol::SupervisorSlot.as_str(), "supervisor_slot");
    assert_eq!(ChassisInfoCols::SUPERVISOR_SLOT, ChassisInfoCols::of(ChassisInfoCol::SupervisorSlot));
    assert_eq!(ChassisInfoCol::DpuId.as_str(), "dpu_id");
    assert_eq!(ChassisInfoCols::DPU_ID, ChassisInfoCols::of(ChassisInfoCol::DpuId));
    assert_eq!(ChassisInfoCol::DataplaneState.as_str(), "dataplane_state");
    assert_eq!(ChassisInfoCols::DATAPLANE_STATE, ChassisInfoCols::of(ChassisInfoCol::DataplaneState));
    assert_eq!(ChassisInfoCol::ControlplaneState.as_str(), "controlplane_state");
    assert_eq!(ChassisInfoCols::CONTROLPLANE_STATE, ChassisInfoCols::of(ChassisInfoCol::ControlplaneState));
    assert_eq!(ChassisInfoCol::StatusLed.as_str(), "status_led");
    assert_eq!(ChassisInfoCols::STATUS_LED, ChassisInfoCols::of(ChassisInfoCol::StatusLed));
    assert_eq!(format!("{:?}", ChassisInfoCols::NONE), "ChassisInfoCols[]");
    assert!(format!("{:?}", ChassisInfoCols::ALL).starts_with("ChassisInfoCols["));
}

#[test]
fn every_module_info_column_has_a_bit_and_a_name_of_its_own() {
    let mut seen = ModuleInfoCols::NONE;
    for col in ModuleInfoCol::ALL {
        assert!(!seen.contains(*col), "{} shares a bit", col.as_str());
        seen = seen.with(ModuleInfoCols::of(*col));
    }
    assert_eq!(seen, ModuleInfoCols::ALL);
    assert_eq!(seen.bits(), ModuleInfoCols::ALL.bits());
    assert_eq!(ModuleInfoCol::PositionInParent.as_str(), "position_in_parent");
    assert_eq!(ModuleInfoCols::POSITION_IN_PARENT, ModuleInfoCols::of(ModuleInfoCol::PositionInParent));
    assert_eq!(ModuleInfoCol::Presence.as_str(), "presence");
    assert_eq!(ModuleInfoCols::PRESENCE, ModuleInfoCols::of(ModuleInfoCol::Presence));
    assert_eq!(ModuleInfoCol::Status.as_str(), "status");
    assert_eq!(ModuleInfoCols::STATUS, ModuleInfoCols::of(ModuleInfoCol::Status));
    assert_eq!(ModuleInfoCol::IsReplaceable.as_str(), "is_replaceable");
    assert_eq!(ModuleInfoCols::IS_REPLACEABLE, ModuleInfoCols::of(ModuleInfoCol::IsReplaceable));
    assert_eq!(ModuleInfoCol::Model.as_str(), "model");
    assert_eq!(ModuleInfoCols::MODEL, ModuleInfoCols::of(ModuleInfoCol::Model));
    assert_eq!(ModuleInfoCol::Serial.as_str(), "serial");
    assert_eq!(ModuleInfoCols::SERIAL, ModuleInfoCols::of(ModuleInfoCol::Serial));
    assert_eq!(ModuleInfoCol::Description.as_str(), "description");
    assert_eq!(ModuleInfoCols::DESCRIPTION, ModuleInfoCols::of(ModuleInfoCol::Description));
    assert_eq!(ModuleInfoCol::Slot.as_str(), "slot");
    assert_eq!(ModuleInfoCols::SLOT, ModuleInfoCols::of(ModuleInfoCol::Slot));
    assert_eq!(ModuleInfoCol::Type.as_str(), "type");
    assert_eq!(ModuleInfoCols::TYPE, ModuleInfoCols::of(ModuleInfoCol::Type));
    assert_eq!(ModuleInfoCol::OperStatus.as_str(), "oper_status");
    assert_eq!(ModuleInfoCols::OPER_STATUS, ModuleInfoCols::of(ModuleInfoCol::OperStatus));
    assert_eq!(ModuleInfoCol::BaseMac.as_str(), "base_mac");
    assert_eq!(ModuleInfoCols::BASE_MAC, ModuleInfoCols::of(ModuleInfoCol::BaseMac));
    assert_eq!(ModuleInfoCol::DpuId.as_str(), "dpu_id");
    assert_eq!(ModuleInfoCols::DPU_ID, ModuleInfoCols::of(ModuleInfoCol::DpuId));
    assert_eq!(ModuleInfoCol::MaximumConsumedPower.as_str(), "maximum_consumed_power");
    assert_eq!(ModuleInfoCols::MAXIMUM_CONSUMED_POWER, ModuleInfoCols::of(ModuleInfoCol::MaximumConsumedPower));
    assert_eq!(ModuleInfoCol::MidplaneIp.as_str(), "midplane_ip");
    assert_eq!(ModuleInfoCols::MIDPLANE_IP, ModuleInfoCols::of(ModuleInfoCol::MidplaneIp));
    assert_eq!(ModuleInfoCol::IsMidplaneReachable.as_str(), "is_midplane_reachable");
    assert_eq!(ModuleInfoCols::IS_MIDPLANE_REACHABLE, ModuleInfoCols::of(ModuleInfoCol::IsMidplaneReachable));
    assert_eq!(ModuleInfoCol::StateTransition.as_str(), "state_transition");
    assert_eq!(ModuleInfoCols::STATE_TRANSITION, ModuleInfoCols::of(ModuleInfoCol::StateTransition));
    assert_eq!(format!("{:?}", ModuleInfoCols::NONE), "ModuleInfoCols[]");
    assert!(format!("{:?}", ModuleInfoCols::ALL).starts_with("ModuleInfoCols["));
}
