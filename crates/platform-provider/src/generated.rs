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
    LedColor, EepromUpdate, ThermalInfo, FanInfo, FanDrawerInfo, PsuInfo, ChassisInfo, ModuleInfo, ComponentInfo, SensorInfo, LeakProfile, LeakSensorInfo, WatchdogInfo, ChangeEventBatch, PcieDevice, PcieAerStat, StorageDeviceInfo, EepromTlv, AsicInfo, BmcInfo, ModuleRebootCause, ModuleMidplaneDownReason, BmcResult, ThermalInfoCols, FanInfoCols, FanDrawerInfoCols, ChassisInfoCols, ModuleInfoCols, Number, DeviceKey,
    PlatformApi, PlatformError,
};

/// The implementation this call opened.
///
/// Which crate the native arm holds is a build-time fact; which arm is used is
/// the switch the daemon was started with.  The two are separate on purpose: a
/// build can carry an implementation nobody has turned on yet.
pub enum Platform {
    /// The vendor's Python, reached through PyO3.
    Pyo3(platform_pyo3::Bridge),
    /// A native Rust implementation of the same trait -- a vendor's, or the
    /// stub, which cannot be constructed.
    Native(platform_native::Platform),
}

impl PlatformApi for Platform {

    fn get_chassis_info(&mut self, cols: ChassisInfoCols) -> Result<ChassisInfo, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_chassis_info(cols),
            Self::Native(p) => p.get_chassis_info(cols),
        }
    }

    fn get_modules(&mut self, cols: ModuleInfoCols) -> Result<Vec<ModuleInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_modules(cols),
            Self::Native(p) => p.get_modules(cols),
        }
    }

    fn get_thermals(&mut self, cols: ThermalInfoCols, skip: &[DeviceKey]) -> Result<Vec<ThermalInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_thermals(cols, skip),
            Self::Native(p) => p.get_thermals(cols, skip),
        }
    }

    fn get_fans(&mut self, cols: FanInfoCols, absorb: bool) -> Result<Vec<FanInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_fans(cols, absorb),
            Self::Native(p) => p.get_fans(cols, absorb),
        }
    }

    fn get_fan_drawers(&mut self, cols: FanDrawerInfoCols) -> Result<Vec<FanDrawerInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_fan_drawers(cols),
            Self::Native(p) => p.get_fan_drawers(cols),
        }
    }

    fn get_psus(&mut self) -> Result<Vec<PsuInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_psus(),
            Self::Native(p) => p.get_psus(),
        }
    }

    fn get_components(&mut self) -> Result<Vec<ComponentInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_components(),
            Self::Native(p) => p.get_components(),
        }
    }

    fn get_sensors(&mut self) -> Result<Vec<SensorInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_sensors(),
            Self::Native(p) => p.get_sensors(),
        }
    }

    fn get_leak_profiles(&mut self) -> Result<Vec<LeakProfile>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_leak_profiles(),
            Self::Native(p) => p.get_leak_profiles(),
        }
    }

    fn get_leak_sensors(&mut self) -> Result<Vec<LeakSensorInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_leak_sensors(),
            Self::Native(p) => p.get_leak_sensors(),
        }
    }

    fn get_eeprom(&mut self) -> Result<Vec<EepromTlv>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_eeprom(),
            Self::Native(p) => p.get_eeprom(),
        }
    }

    fn get_bmcs(&mut self) -> Result<Vec<BmcInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_bmcs(),
            Self::Native(p) => p.get_bmcs(),
        }
    }

    fn get_watchdogs(&mut self) -> Result<Vec<WatchdogInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_watchdogs(),
            Self::Native(p) => p.get_watchdogs(),
        }
    }

    fn set_fan_led(&mut self, fan: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_fan_led(fan, color),
            Self::Native(p) => p.set_fan_led(fan, color),
        }
    }

    fn set_fan_drawer_led(&mut self, drawer: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_fan_drawer_led(drawer, color),
            Self::Native(p) => p.set_fan_drawer_led(drawer, color),
        }
    }

    fn set_fan_speed(&mut self, fan: &DeviceKey, speed: i64) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_fan_speed(fan, speed),
            Self::Native(p) => p.set_fan_speed(fan, speed),
        }
    }

    fn set_psu_led(&mut self, psu: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_psu_led(psu, color),
            Self::Native(p) => p.set_psu_led(psu, color),
        }
    }

    fn get_module_reboot_cause(&mut self, module: &DeviceKey) -> Result<ModuleRebootCause, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_module_reboot_cause(module),
            Self::Native(p) => p.get_module_reboot_cause(module),
        }
    }

    fn get_module_midplane_down_reason(&mut self, module: &DeviceKey) -> Result<ModuleMidplaneDownReason, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_module_midplane_down_reason(module),
            Self::Native(p) => p.get_module_midplane_down_reason(module),
        }
    }

    fn get_psu_master_led(&mut self, psu: &DeviceKey) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_psu_master_led(psu),
            Self::Native(p) => p.get_psu_master_led(psu),
        }
    }

    fn set_psu_master_led(&mut self, psu: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_psu_master_led(psu, color),
            Self::Native(p) => p.set_psu_master_led(psu, color),
        }
    }

    fn reboot_module(&mut self, module: &DeviceKey, reboot_type: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.reboot_module(module, reboot_type),
            Self::Native(p) => p.reboot_module(module, reboot_type),
        }
    }

    fn set_module_admin_state(&mut self, module: &DeviceKey, up: bool) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_module_admin_state(module, up),
            Self::Native(p) => p.set_module_admin_state(module, up),
        }
    }

    fn set_module_admin_state_gracefully(&mut self, module: &DeviceKey, up: bool) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_module_admin_state_gracefully(module, up),
            Self::Native(p) => p.set_module_admin_state_gracefully(module, up),
        }
    }

    fn power_cycle_module(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.power_cycle_module(module),
            Self::Native(p) => p.power_cycle_module(module),
        }
    }

    fn module_pre_shutdown(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.module_pre_shutdown(module),
            Self::Native(p) => p.module_pre_shutdown(module),
        }
    }

    fn module_post_startup(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.module_post_startup(module),
            Self::Native(p) => p.module_post_startup(module),
        }
    }

    fn set_module_state_transition(&mut self, module: &DeviceKey, transition_type: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_module_state_transition(module, transition_type),
            Self::Native(p) => p.set_module_state_transition(module, transition_type),
        }
    }

    fn clear_module_state_transition(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.clear_module_state_transition(module),
            Self::Native(p) => p.clear_module_state_transition(module),
        }
    }

    fn clear_module_gnoi_halt(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.clear_module_gnoi_halt(module),
            Self::Native(p) => p.clear_module_gnoi_halt(module),
        }
    }

    fn set_sensor_high_threshold(&mut self, sensor: &DeviceKey, value: Number) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_sensor_high_threshold(sensor, value),
            Self::Native(p) => p.set_sensor_high_threshold(sensor, value),
        }
    }

    fn set_sensor_low_threshold(&mut self, sensor: &DeviceKey, value: Number) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_sensor_low_threshold(sensor, value),
            Self::Native(p) => p.set_sensor_low_threshold(sensor, value),
        }
    }

    fn get_module_key(&mut self, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_module_key(name),
            Self::Native(p) => p.get_module_key(name),
        }
    }

    fn get_component_key(&mut self, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_component_key(name),
            Self::Native(p) => p.get_component_key(name),
        }
    }

    fn get_module_component_key(&mut self, module: &str, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_module_component_key(module, name),
            Self::Native(p) => p.get_module_component_key(module, name),
        }
    }

    fn get_available_firmware_version(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_available_firmware_version(component, image_path),
            Self::Native(p) => p.get_available_firmware_version(component, image_path),
        }
    }

    fn get_firmware_update_notification(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<String>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_firmware_update_notification(component, image_path),
            Self::Native(p) => p.get_firmware_update_notification(component, image_path),
        }
    }

    fn install_firmware(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.install_firmware(component, image_path),
            Self::Native(p) => p.install_firmware(component, image_path),
        }
    }

    fn update_firmware(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.update_firmware(component, image_path),
            Self::Native(p) => p.update_firmware(component, image_path),
        }
    }

    fn auto_update_firmware(&mut self, component: &DeviceKey, image_path: &str, boot_type: &str) -> Result<Option<i64>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.auto_update_firmware(component, image_path, boot_type),
            Self::Native(p) => p.auto_update_firmware(component, image_path, boot_type),
        }
    }

    fn arm_watchdog(&mut self, seconds: i64) -> Result<Option<i64>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.arm_watchdog(seconds),
            Self::Native(p) => p.arm_watchdog(seconds),
        }
    }

    fn disarm_watchdog(&mut self) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.disarm_watchdog(),
            Self::Native(p) => p.disarm_watchdog(),
        }
    }

    fn initialize_system_led(&mut self) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.initialize_system_led(),
            Self::Native(p) => p.initialize_system_led(),
        }
    }

    fn init_midplane_switch(&mut self) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.init_midplane_switch(),
            Self::Native(p) => p.init_midplane_switch(),
        }
    }

    fn set_chassis_led(&mut self, color: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.set_chassis_led(color),
            Self::Native(p) => p.set_chassis_led(color),
        }
    }

    fn change_sed_password(&mut self, new_password: &str) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.change_sed_password(new_password),
            Self::Native(p) => p.change_sed_password(new_password),
        }
    }

    fn reset_sed_password(&mut self) -> Result<Option<bool>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.reset_sed_password(),
            Self::Native(p) => p.reset_sed_password(),
        }
    }

    fn bmc_open_session(&mut self) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_open_session(),
            Self::Native(p) => p.bmc_open_session(),
        }
    }

    fn bmc_close_session(&mut self, session_id: &str) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_close_session(session_id),
            Self::Native(p) => p.bmc_close_session(session_id),
        }
    }

    fn bmc_reset_root_password(&mut self) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_reset_root_password(),
            Self::Native(p) => p.bmc_reset_root_password(),
        }
    }

    fn bmc_reset(&mut self, graceful: bool) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_reset(graceful),
            Self::Native(p) => p.bmc_reset(graceful),
        }
    }

    fn bmc_update_firmware(&mut self, image_path: &str) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_update_firmware(image_path),
            Self::Native(p) => p.bmc_update_firmware(image_path),
        }
    }

    fn bmc_trigger_debug_log_dump(&mut self) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_trigger_debug_log_dump(),
            Self::Native(p) => p.bmc_trigger_debug_log_dump(),
        }
    }

    fn bmc_get_debug_log_dump(&mut self, task_id: &str, filename: &str, path: &str) -> Result<BmcResult, PlatformError> {
        match self {
            Self::Pyo3(p) => p.bmc_get_debug_log_dump(task_id, filename, path),
            Self::Native(p) => p.bmc_get_debug_log_dump(task_id, filename, path),
        }
    }

    fn get_asics(&mut self) -> Result<Vec<AsicInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_asics(),
            Self::Native(p) => p.get_asics(),
        }
    }

    fn tm_initialize(&mut self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_initialize(),
            Self::Native(p) => p.tm_initialize(),
        }
    }

    fn tm_run_policy(&mut self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_run_policy(),
            Self::Native(p) => p.tm_run_policy(),
        }
    }

    fn tm_get_interval(&mut self) -> Result<Option<f64>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_get_interval(),
            Self::Native(p) => p.tm_get_interval(),
        }
    }

    fn tm_deinitialize(&mut self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_deinitialize(),
            Self::Native(p) => p.tm_deinitialize(),
        }
    }

    fn tm_stop(&mut self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.tm_stop(),
            Self::Native(p) => p.tm_stop(),
        }
    }

    fn notify_shutdown(&mut self) -> Result<(), PlatformError> {
        match self {
            Self::Pyo3(p) => p.notify_shutdown(),
            Self::Native(p) => p.notify_shutdown(),
        }
    }

    fn eeprom_update_db(&mut self) -> Result<EepromUpdate, PlatformError> {
        match self {
            Self::Pyo3(p) => p.eeprom_update_db(),
            Self::Native(p) => p.eeprom_update_db(),
        }
    }

    fn get_storage_devices(&mut self) -> Result<Vec<StorageDeviceInfo>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_storage_devices(),
            Self::Native(p) => p.get_storage_devices(),
        }
    }

    fn get_pcie_devices(&mut self) -> Result<Vec<PcieDevice>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_pcie_devices(),
            Self::Native(p) => p.get_pcie_devices(),
        }
    }

    fn get_pcie_aer_stats(&mut self, bus: i64, dev: i64, func: i64) -> Result<Vec<PcieAerStat>, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_pcie_aer_stats(bus, dev, func),
            Self::Native(p) => p.get_pcie_aer_stats(bus, dev, func),
        }
    }

    fn get_change_event(&mut self, timeout_ms: i64) -> Result<ChangeEventBatch, PlatformError> {
        match self {
            Self::Pyo3(p) => p.get_change_event(timeout_ms),
            Self::Native(p) => p.get_change_event(timeout_ms),
        }
    }

    /// Forwarded like everything else: the bridge runs Python's `atexit`
    /// handlers, a native implementation is free to do nothing.
    fn finalize(&mut self) {
        match self {
            Self::Pyo3(p) => p.finalize(),
            Self::Native(p) => p.finalize(),
        }
    }
}
