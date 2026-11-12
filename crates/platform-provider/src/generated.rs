//! Every implementation of the platform API, behind one concrete type.
//!
//! GENERATED from sonic_platform_api/facade.pyi by generator/generate.py.  Do
//! not edit: regenerate.
//!
//! [`Platform`] is an enum rather than a `Box<dyn PlatformApi>` because
//! chassisd takes the platform through a generic parameter and hands the same
//! borrow to a power cycler (`PlatformCycler<'a, P: PlatformApi>`, which the
//! daemon's own comment records as deliberate: "the two cannot both be taken
//! through one trait object").  A trait object there does not compile even
//! with `?Sized`, because `&mut P` with `P: ?Sized` cannot be unsized to
//! `&mut dyn PlatformApi`.  A `Sized` enum keeps every one of those signatures
//! working unchanged, which is what lets a second implementation arrive
//! without a daemon being touched.
//!
//! The delegation below is mechanical and long.  It is generated for the same
//! reason the trait is: so the arms cannot drift from the trait, or from each
//! other, when a method is added to the stub.

use platform_api::{
    LedColor, EepromUpdate, ThermalInfo, FanInfo, FanDrawerInfo, PsuInfo, ChassisInfo, ModuleInfo, ComponentInfo, SensorInfo, LeakProfile, LeakSensorInfo, WatchdogInfo, SfpInfo, ChangeEventBatch, PcieDevice, PcieAerStat, StorageDeviceInfo, EepromTlv, AsicInfo, BmcInfo, ModuleRebootCause, ModuleMidplaneDownReason, BmcResult, ThermalInfoCols, FanInfoCols, FanDrawerInfoCols, ChassisInfoCols, ModuleInfoCols, Number, DeviceKey,
    PlatformApi, PlatformError,
};

/// The implementation this call opened.
///
/// One arm, because the PyO3 bridge is the only implementation there is.  A
/// native one becomes a second variant here and a second arm in each
/// forwarder below, and no daemon changes.
pub enum Platform {
    /// The vendor's Python, reached through PyO3.
    Pyo3(platform_pyo3::Bridge),
}

impl PlatformApi for Platform {

    fn get_sfps(&self, indices: &[u32]) -> Result<Vec<SfpInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_sfps(indices),
        }
    }

    fn get_chassis_info(&self, cols: ChassisInfoCols) -> Result<ChassisInfo, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_chassis_info(cols),
        }
    }

    fn get_modules(&self, cols: ModuleInfoCols) -> Result<Vec<ModuleInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_modules(cols),
        }
    }

    fn get_thermals(&self, cols: ThermalInfoCols, skip: &[DeviceKey]) -> Result<Vec<ThermalInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_thermals(cols, skip),
        }
    }

    fn get_fans(&self, cols: FanInfoCols, absorb: bool) -> Result<Vec<FanInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_fans(cols, absorb),
        }
    }

    fn get_fan_drawers(&self, cols: FanDrawerInfoCols) -> Result<Vec<FanDrawerInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_fan_drawers(cols),
        }
    }

    fn get_psus(&self) -> Result<Vec<PsuInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_psus(),
        }
    }

    fn get_components(&self) -> Result<Vec<ComponentInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_components(),
        }
    }

    fn get_sensors(&self) -> Result<Vec<SensorInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_sensors(),
        }
    }

    fn get_leak_profiles(&self) -> Result<Vec<LeakProfile>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_leak_profiles(),
        }
    }

    fn get_leak_sensors(&self) -> Result<Vec<LeakSensorInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_leak_sensors(),
        }
    }

    fn get_eeprom(&self) -> Result<Vec<EepromTlv>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_eeprom(),
        }
    }

    fn get_bmcs(&self) -> Result<Vec<BmcInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_bmcs(),
        }
    }

    fn get_watchdogs(&self) -> Result<Vec<WatchdogInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_watchdogs(),
        }
    }

    fn sfp_get_presence(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_presence(sfp),
        }
    }

    fn sfp_is_replaceable(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_is_replaceable(sfp),
        }
    }

    fn sfp_get_reset_status(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_reset_status(sfp),
        }
    }

    fn sfp_get_lpmode(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_lpmode(sfp),
        }
    }

    fn sfp_get_error_description(&self, sfp: &DeviceKey) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_error_description(sfp),
        }
    }

    fn sfp_get_type(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_type(sfp),
        }
    }

    fn sfp_uses_legacy_pm(&self, sfp: &DeviceKey) -> Result<bool, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_uses_legacy_pm(sfp),
        }
    }

    fn sfp_get_transceiver_info(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_info(sfp),
        }
    }

    fn sfp_get_transceiver_info_firmware_versions(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_info_firmware_versions(sfp),
        }
    }

    fn sfp_get_transceiver_status(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_status(sfp),
        }
    }

    fn sfp_get_transceiver_status_flags(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_status_flags(sfp),
        }
    }

    fn sfp_get_transceiver_dom_real_value(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_dom_real_value(sfp),
        }
    }

    fn sfp_get_transceiver_dom_flags(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_dom_flags(sfp),
        }
    }

    fn sfp_get_transceiver_threshold_info(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_threshold_info(sfp),
        }
    }

    fn sfp_get_temperature(&self, sfp: &DeviceKey) -> Result<Option<Number>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_temperature(sfp),
        }
    }

    fn sfp_get_transceiver_pm(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_pm(sfp),
        }
    }

    fn sfp_is_transceiver_vdm_supported(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_is_transceiver_vdm_supported(sfp),
        }
    }

    fn sfp_is_vdm_statistic_supported(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_is_vdm_statistic_supported(sfp),
        }
    }

    fn sfp_get_transceiver_vdm_real_value_basic(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_vdm_real_value_basic(sfp),
        }
    }

    fn sfp_get_transceiver_vdm_real_value_statistic(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_vdm_real_value_statistic(sfp),
        }
    }

    fn sfp_get_transceiver_vdm_flags(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_vdm_flags(sfp),
        }
    }

    fn sfp_get_transceiver_vdm_thresholds(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_transceiver_vdm_thresholds(sfp),
        }
    }

    fn sfp_get_vdm_freeze_status(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_vdm_freeze_status(sfp),
        }
    }

    fn sfp_get_vdm_unfreeze_status(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_vdm_unfreeze_status(sfp),
        }
    }

    fn sfp_set_lpmode(&self, sfp: &DeviceKey, on: bool) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_set_lpmode(sfp, on),
        }
    }

    fn sfp_reset(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_reset(sfp),
        }
    }

    fn sfp_remove_xcvr_api(&self, sfp: &DeviceKey) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_remove_xcvr_api(sfp),
        }
    }

    fn sfp_freeze_vdm_stats(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_freeze_vdm_stats(sfp),
        }
    }

    fn sfp_unfreeze_vdm_stats(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_unfreeze_vdm_stats(sfp),
        }
    }

    fn sfp_read_eeprom(&self, sfp: &DeviceKey, offset: i64, num_bytes: i64) -> Result<Option<Vec<u8>>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_read_eeprom(sfp, offset, num_bytes),
        }
    }

    fn sfp_write_eeprom(&self, sfp: &DeviceKey, offset: i64, data: &[u8]) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_write_eeprom(sfp, offset, data),
        }
    }

    fn sfp_is_flat_memory(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_is_flat_memory(sfp),
        }
    }

    fn sfp_get_module_type_abbreviation(&self, sfp: &DeviceKey) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_module_type_abbreviation(sfp),
        }
    }

    fn sfp_is_coherent_module(&self, sfp: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_is_coherent_module(sfp),
        }
    }

    fn sfp_get_module_state(&self, sfp: &DeviceKey) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_module_state(sfp),
        }
    }

    fn sfp_get_cmis_rev(&self, sfp: &DeviceKey) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_cmis_rev(sfp),
        }
    }

    fn sfp_get_application_advertisement(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_application_advertisement(sfp),
        }
    }

    fn sfp_get_datapath_state(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_datapath_state(sfp),
        }
    }

    fn sfp_get_config_datapath_hostlane_status(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_config_datapath_hostlane_status(sfp),
        }
    }

    fn sfp_get_dpinit_pending(&self, sfp: &DeviceKey) -> Result<String, PlatformError> {
        match self {
            Self::Pyo3(p) => p.sfp_get_dpinit_pending(sfp),
        }
    }

    fn set_fan_led(&self, fan: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_fan_led(fan, color),
        }
    }

    fn set_fan_drawer_led(&self, drawer: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_fan_drawer_led(drawer, color),
        }
    }

    fn set_fan_speed(&self, fan: &DeviceKey, speed: i64) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_fan_speed(fan, speed),
        }
    }

    fn set_psu_led(&self, psu: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_psu_led(psu, color),
        }
    }

    fn get_module_reboot_cause(&self, module: &DeviceKey) -> Result<ModuleRebootCause, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_module_reboot_cause(module),
        }
    }

    fn get_module_midplane_down_reason(&self, module: &DeviceKey) -> Result<ModuleMidplaneDownReason, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_module_midplane_down_reason(module),
        }
    }

    fn get_psu_master_led(&self, psu: &DeviceKey) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_psu_master_led(psu),
        }
    }

    fn set_psu_master_led(&self, psu: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_psu_master_led(psu, color),
        }
    }

    fn reboot_module(&self, module: &DeviceKey, reboot_type: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.reboot_module(module, reboot_type),
        }
    }

    fn set_module_admin_state(&self, module: &DeviceKey, up: bool) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_module_admin_state(module, up),
        }
    }

    fn set_module_admin_state_gracefully(&self, module: &DeviceKey, up: bool) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_module_admin_state_gracefully(module, up),
        }
    }

    fn power_cycle_module(&self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.power_cycle_module(module),
        }
    }

    fn module_pre_shutdown(&self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.module_pre_shutdown(module),
        }
    }

    fn module_post_startup(&self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.module_post_startup(module),
        }
    }

    fn set_module_state_transition(&self, module: &DeviceKey, transition_type: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_module_state_transition(module, transition_type),
        }
    }

    fn clear_module_state_transition(&self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.clear_module_state_transition(module),
        }
    }

    fn clear_module_gnoi_halt(&self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.clear_module_gnoi_halt(module),
        }
    }

    fn set_sensor_high_threshold(&self, sensor: &DeviceKey, value: Number) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_sensor_high_threshold(sensor, value),
        }
    }

    fn set_sensor_low_threshold(&self, sensor: &DeviceKey, value: Number) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_sensor_low_threshold(sensor, value),
        }
    }

    fn get_module_key(&self, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_module_key(name),
        }
    }

    fn get_component_key(&self, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_component_key(name),
        }
    }

    fn get_module_component_key(&self, module: &str, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_module_component_key(module, name),
        }
    }

    fn get_available_firmware_version(&self, component: &DeviceKey, image_path: &str) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_available_firmware_version(component, image_path),
        }
    }

    fn get_firmware_update_notification(&self, component: &DeviceKey, image_path: &str) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_firmware_update_notification(component, image_path),
        }
    }

    fn install_firmware(&self, component: &DeviceKey, image_path: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.install_firmware(component, image_path),
        }
    }

    fn update_firmware(&self, component: &DeviceKey, image_path: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.update_firmware(component, image_path),
        }
    }

    fn auto_update_firmware(&self, component: &DeviceKey, image_path: &str, boot_type: &str) -> Result<Option<i64>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.auto_update_firmware(component, image_path, boot_type),
        }
    }

    fn arm_watchdog(&self, seconds: i64) -> Result<Option<i64>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.arm_watchdog(seconds),
        }
    }

    fn disarm_watchdog(&self) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.disarm_watchdog(),
        }
    }

    fn initialize_system_led(&self) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.initialize_system_led(),
        }
    }

    fn init_midplane_switch(&self) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.init_midplane_switch(),
        }
    }

    fn set_chassis_led(&self, color: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_chassis_led(color),
        }
    }

    fn change_sed_password(&self, new_password: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.change_sed_password(new_password),
        }
    }

    fn reset_sed_password(&self) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.reset_sed_password(),
        }
    }

    fn bmc_open_session(&self) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_open_session(),
        }
    }

    fn bmc_close_session(&self, session_id: &str) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_close_session(session_id),
        }
    }

    fn bmc_reset_root_password(&self) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_reset_root_password(),
        }
    }

    fn bmc_reset(&self, graceful: bool) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_reset(graceful),
        }
    }

    fn bmc_update_firmware(&self, image_path: &str) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_update_firmware(image_path),
        }
    }

    fn bmc_trigger_debug_log_dump(&self) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_trigger_debug_log_dump(),
        }
    }

    fn bmc_get_debug_log_dump(&self, task_id: &str, filename: &str, path: &str) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_get_debug_log_dump(task_id, filename, path),
        }
    }

    fn get_asics(&self) -> Result<Vec<AsicInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_asics(),
        }
    }

    fn tm_initialize(&self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_initialize(),
        }
    }

    fn tm_run_policy(&self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_run_policy(),
        }
    }

    fn tm_get_interval(&self) -> Result<Option<f64>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_get_interval(),
        }
    }

    fn tm_deinitialize(&self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_deinitialize(),
        }
    }

    fn tm_stop(&self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_stop(),
        }
    }

    fn notify_shutdown(&self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.notify_shutdown(),
        }
    }

    fn eeprom_update_db(&self) -> Result<EepromUpdate, PlatformError> {
        match self {
            Self::Pyo3(p) => p.eeprom_update_db(),
        }
    }

    fn get_storage_devices(&self) -> Result<Vec<StorageDeviceInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_storage_devices(),
        }
    }

    fn get_pcie_devices(&self) -> Result<Vec<PcieDevice>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_pcie_devices(),
        }
    }

    fn get_pcie_aer_stats(&self, bus: i64, dev: i64, func: i64) -> Result<Vec<PcieAerStat>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_pcie_aer_stats(bus, dev, func),
        }
    }

    fn get_change_event(&self, timeout_ms: i64) -> Result<ChangeEventBatch, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_change_event(timeout_ms),
        }
    }

    /// Forwarded like everything else: the bridge runs Python's `atexit`
    /// handlers, a native implementation is free to do nothing.
    fn finalize(&self) {
        match self {
            Self::Pyo3(p) => p.finalize(),
        }
    }
}
