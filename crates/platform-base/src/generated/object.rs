//! Platform objects, as the native facade and the escape hatches reach them.
//!
//! GENERATED from sonic_platform_api/facade.pyi and sonic_platform_base by
//! generator/generate.py.  Do not edit: regenerate.
//!
//! One trait for every platform object, the way Python has one attribute
//! lookup for every object.  A method is here if the facade or the escape
//! hatches call it; its default is what the object's *base class* answers,
//! found the way Python resolves the method (`generator/native.py`,
//! `default_of`).  A native fan overriding nothing therefore answers what a
//! Python fan overriding nothing answers, and a method its base class does
//! not define answers [`Exc::Missing`](crate::py::Exc::Missing) -- the
//! `getattr(obj, name, None)` the facade reads as "not implemented".

use crate::py::{PyErr, PyResult, PyVal};

/// The base class a platform object derives from, which decides its defaults.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BaseClass {
    /// Derives from none of them: every method below is missing.
    Object,
    ChassisBase,
    ModuleBase,
    FanBase,
    FanDrawerBase,
    PsuBase,
    PdbBase,
    ThermalBase,
    SensorBase,
    VoltageSensorBase,
    CurrentSensorBase,
    LiquidCoolingBase,
    LeakageSensorBase,
    LeakSensorProfileBase,
    ComponentBase,
    WatchdogBase,
    BMCBase,
    SedMgmtBase,
    ThermalManagerBase,
    TlvInfoDecoder,
}

/// A platform object: the chassis, a fan, a PSU, the thermal manager.
///
/// Methods take `&self`: Python objects are shared and mutate themselves, so
/// an implementation keeps what changes behind its own locks.
pub trait PyObject: Send + Sync {
    /// The vendor's class name, as `type(obj).__name__` spells it.
    fn py_class(&self) -> &'static str;

    /// The base class, which decides every default below.
    fn base_class(&self) -> BaseClass;

    /// The vendor's classes from most derived up, as `type(obj).__mro__`
    /// would name them before the base classes.  Only class-level state reads
    /// it -- `PsuBase`'s master LED is an attribute of whichever class set it.
    fn py_mro(&self) -> Vec<&'static str> {
        vec![self.py_class()]
    }

    /// Reached as WatchdogBase.
    fn arm(&self, seconds: i128) -> PyResult<PyVal> {
        defaults::arm(self, seconds)
    }
    /// Reached as ComponentBase.
    fn auto_update_firmware(&self, image_path: &str, boot_type: &str) -> PyResult<PyVal> {
        defaults::auto_update_firmware(self, image_path, boot_type)
    }
    /// Reached as SedMgmtBase.
    fn change_sed_password(&self, new_password: &str) -> PyResult<PyVal> {
        defaults::change_sed_password(self, new_password)
    }
    /// Reached as ModuleBase.
    fn clear_module_gnoi_halt_in_progress(&self) -> PyResult<PyVal> {
        defaults::clear_module_gnoi_halt_in_progress(self)
    }
    /// Reached as ModuleBase.
    fn clear_module_state_transition(&self, module_name: PyVal) -> PyResult<PyVal> {
        defaults::clear_module_state_transition(self, module_name)
    }
    /// Reached as BMCBase.
    fn close_session(&self, session_id: &str) -> PyResult<PyVal> {
        defaults::close_session(self, session_id)
    }
    /// Reached as ThermalManagerBase.
    fn deinitialize(&self) -> PyResult<PyVal> {
        defaults::deinitialize(self)
    }
    /// Reached as WatchdogBase.
    fn disarm(&self) -> PyResult<PyVal> {
        defaults::disarm(self)
    }
    /// Reached as ModuleBase.
    fn do_power_cycle(&self) -> PyResult<PyVal> {
        defaults::do_power_cycle(self)
    }
    /// Reached as ModuleBase.
    fn get_all_asics(&self) -> PyResult<PyVal> {
        defaults::get_all_asics(self)
    }
    /// Reached as ChassisBase, ModuleBase.
    fn get_all_components(&self) -> PyResult<PyVal> {
        defaults::get_all_components(self)
    }
    /// Reached as ChassisBase, ModuleBase.
    fn get_all_current_sensors(&self) -> PyResult<PyVal> {
        defaults::get_all_current_sensors(self)
    }
    /// Reached as ChassisBase.
    fn get_all_fan_drawers(&self) -> PyResult<PyVal> {
        defaults::get_all_fan_drawers(self)
    }
    /// Reached as FanDrawerBase, ModuleBase, PsuBase.
    fn get_all_fans(&self) -> PyResult<PyVal> {
        defaults::get_all_fans(self)
    }
    /// Reached as LiquidCoolingBase.
    fn get_all_leak_sensors(&self) -> PyResult<PyVal> {
        defaults::get_all_leak_sensors(self)
    }
    /// Reached as ChassisBase.
    fn get_all_modules(&self) -> PyResult<PyVal> {
        defaults::get_all_modules(self)
    }
    /// Reached as ChassisBase.
    fn get_all_pdbs(&self) -> PyResult<PyVal> {
        defaults::get_all_pdbs(self)
    }
    /// Reached as LiquidCoolingBase.
    fn get_all_profiles(&self) -> PyResult<PyVal> {
        defaults::get_all_profiles(self)
    }
    /// Reached as ChassisBase, ModuleBase.
    fn get_all_psus(&self) -> PyResult<PyVal> {
        defaults::get_all_psus(self)
    }
    /// Reached as ChassisBase, PsuBase, PdbBase, ModuleBase.
    fn get_all_thermals(&self) -> PyResult<PyVal> {
        defaults::get_all_thermals(self)
    }
    /// Reached as ChassisBase, ModuleBase.
    fn get_all_voltage_sensors(&self) -> PyResult<PyVal> {
        defaults::get_all_voltage_sensors(self)
    }
    /// Reached as ComponentBase.
    fn get_available_firmware_version(&self, image_path: &str) -> PyResult<PyVal> {
        defaults::get_available_firmware_version(self, image_path)
    }
    /// Reached as ChassisBase, ModuleBase.
    fn get_base_mac(&self) -> PyResult<PyVal> {
        defaults::get_base_mac(self)
    }
    /// Reached as ChassisBase.
    fn get_bmc(&self) -> PyResult<PyVal> {
        defaults::get_bmc(self)
    }
    /// Reached as BMCBase.
    fn get_bmc_debug_log_dump(&self, task_id: &str, filename: &str, path: &str) -> PyResult<PyVal> {
        defaults::get_bmc_debug_log_dump(self, task_id, filename, path)
    }
    /// Reached as ChassisBase.
    fn get_change_event(&self, timeout: i128) -> PyResult<PyVal> {
        defaults::get_change_event(self, timeout)
    }
    /// Reached as ChassisBase.
    fn get_controlplane_state(&self) -> PyResult<PyVal> {
        defaults::get_controlplane_state(self)
    }
    /// Reached as PsuBase.
    fn get_current(&self) -> PyResult<PyVal> {
        defaults::get_current(self)
    }
    /// Reached as ChassisBase.
    fn get_dataplane_state(&self) -> PyResult<PyVal> {
        defaults::get_dataplane_state(self)
    }
    /// Reached as SedMgmtBase.
    fn get_default_sed_password(&self) -> PyResult<PyVal> {
        defaults::get_default_sed_password(self)
    }
    /// Reached as ModuleBase, ComponentBase.
    fn get_description(&self) -> PyResult<PyVal> {
        defaults::get_description(self)
    }
    /// Reached as FanBase.
    fn get_direction(&self) -> PyResult<PyVal> {
        defaults::get_direction(self)
    }
    /// Reached as ChassisBase, ModuleBase.
    fn get_dpu_id(&self) -> PyResult<PyVal> {
        defaults::get_dpu_id(self)
    }
    /// Reached as BMCBase, ChassisBase.
    fn get_eeprom(&self) -> PyResult<PyVal> {
        defaults::get_eeprom(self)
    }
    /// Reached as ComponentBase.
    fn get_firmware_update_notification(&self, image_path: &str) -> PyResult<PyVal> {
        defaults::get_firmware_update_notification(self, image_path)
    }
    /// Reached as ComponentBase.
    fn get_firmware_version(&self) -> PyResult<PyVal> {
        defaults::get_firmware_version(self)
    }
    /// Reached as ThermalBase, SensorBase.
    fn get_high_critical_threshold(&self) -> PyResult<PyVal> {
        defaults::get_high_critical_threshold(self)
    }
    /// Reached as ThermalBase, SensorBase.
    fn get_high_threshold(&self) -> PyResult<PyVal> {
        defaults::get_high_threshold(self)
    }
    /// Reached as PsuBase.
    fn get_input_current(&self) -> PyResult<PyVal> {
        defaults::get_input_current(self)
    }
    /// Reached as PdbBase.
    fn get_input_power(&self) -> PyResult<PyVal> {
        defaults::get_input_power(self)
    }
    /// Reached as PsuBase.
    fn get_input_voltage(&self) -> PyResult<PyVal> {
        defaults::get_input_voltage(self)
    }
    /// Reached as ThermalManagerBase.
    fn get_interval(&self) -> PyResult<PyVal> {
        defaults::get_interval(self)
    }
    /// Reached as LeakSensorProfileBase, LeakageSensorBase.
    fn get_leak_max_minor_duration_sec(&self) -> PyResult<PyVal> {
        defaults::get_leak_max_minor_duration_sec(self)
    }
    /// Reached as LeakageSensorBase.
    fn get_leak_profile(&self) -> PyResult<PyVal> {
        defaults::get_leak_profile(self)
    }
    /// Reached as LeakageSensorBase.
    fn get_leak_sensor_location(&self) -> PyResult<PyVal> {
        defaults::get_leak_sensor_location(self)
    }
    /// Reached as LeakageSensorBase.
    fn get_leak_sensor_type(&self) -> PyResult<PyVal> {
        defaults::get_leak_sensor_type(self)
    }
    /// Reached as LeakageSensorBase.
    fn get_leak_severity(&self) -> PyResult<PyVal> {
        defaults::get_leak_severity(self)
    }
    /// Reached as ChassisBase.
    fn get_liquid_cooling(&self) -> PyResult<PyVal> {
        defaults::get_liquid_cooling(self)
    }
    /// Reached as ThermalBase, SensorBase.
    fn get_low_critical_threshold(&self) -> PyResult<PyVal> {
        defaults::get_low_critical_threshold(self)
    }
    /// Reached as ThermalBase, SensorBase.
    fn get_low_threshold(&self) -> PyResult<PyVal> {
        defaults::get_low_threshold(self)
    }
    /// Reached as SedMgmtBase.
    fn get_max_sed_password_len(&self) -> PyResult<PyVal> {
        defaults::get_max_sed_password_len(self)
    }
    /// Reached as FanDrawerBase, ModuleBase.
    fn get_maximum_consumed_power(&self) -> PyResult<PyVal> {
        defaults::get_maximum_consumed_power(self)
    }
    /// Reached as ThermalBase, SensorBase.
    fn get_maximum_recorded(&self) -> PyResult<PyVal> {
        defaults::get_maximum_recorded(self)
    }
    /// Reached as PsuBase.
    fn get_maximum_supplied_power(&self) -> PyResult<PyVal> {
        defaults::get_maximum_supplied_power(self)
    }
    /// Reached as ModuleBase.
    fn get_midplane_down_reason(&self) -> PyResult<PyVal> {
        defaults::get_midplane_down_reason(self)
    }
    /// Reached as ModuleBase.
    fn get_midplane_ip(&self) -> PyResult<PyVal> {
        defaults::get_midplane_ip(self)
    }
    /// Reached as SedMgmtBase.
    fn get_min_sed_password_len(&self) -> PyResult<PyVal> {
        defaults::get_min_sed_password_len(self)
    }
    /// Reached as ThermalBase, SensorBase.
    fn get_minimum_recorded(&self) -> PyResult<PyVal> {
        defaults::get_minimum_recorded(self)
    }
    /// Reached as DeviceBase.
    fn get_model(&self) -> PyResult<PyVal> {
        defaults::get_model(self)
    }
    /// Reached as ChassisBase.
    fn get_module_index(&self, module_name: &str) -> PyResult<PyVal> {
        defaults::get_module_index(self, module_name)
    }
    /// Reached as ModuleBase.
    fn get_module_state_transition(&self, module_name: PyVal) -> PyResult<PyVal> {
        defaults::get_module_state_transition(self, module_name)
    }
    /// Reached as ChassisBase.
    fn get_my_slot(&self) -> PyResult<PyVal> {
        defaults::get_my_slot(self)
    }
    /// Reached as DeviceBase, ModuleBase, ComponentBase, LeakageSensorBase.
    fn get_name(&self) -> PyResult<PyVal> {
        defaults::get_name(self)
    }
    /// Reached as ModuleBase.
    fn get_oper_status(&self) -> PyResult<PyVal> {
        defaults::get_oper_status(self)
    }
    /// Reached as PdbBase.
    fn get_output_current(&self) -> PyResult<PyVal> {
        defaults::get_output_current(self)
    }
    /// Reached as PdbBase.
    fn get_output_power(&self) -> PyResult<PyVal> {
        defaults::get_output_power(self)
    }
    /// Reached as PdbBase.
    fn get_output_voltage(&self) -> PyResult<PyVal> {
        defaults::get_output_voltage(self)
    }
    /// Reached as ModuleBase.
    fn get_pci_bus_info(&self) -> PyResult<PyVal> {
        defaults::get_pci_bus_info(self)
    }
    /// Reached as DeviceBase.
    fn get_position_in_parent(&self) -> PyResult<PyVal> {
        defaults::get_position_in_parent(self)
    }
    /// Reached as PsuBase.
    fn get_power(&self) -> PyResult<PyVal> {
        defaults::get_power(self)
    }
    /// Reached as PsuBase.
    fn get_powergood_status(&self) -> PyResult<PyVal> {
        defaults::get_powergood_status(self)
    }
    /// Reached as DeviceBase.
    fn get_presence(&self) -> PyResult<PyVal> {
        defaults::get_presence(self)
    }
    /// Reached as PsuBase.
    fn get_psu_power_critical_threshold(&self) -> PyResult<PyVal> {
        defaults::get_psu_power_critical_threshold(self)
    }
    /// Reached as PsuBase.
    fn get_psu_power_warning_suppress_threshold(&self) -> PyResult<PyVal> {
        defaults::get_psu_power_warning_suppress_threshold(self)
    }
    /// Reached as ChassisBase, ModuleBase.
    fn get_reboot_cause(&self) -> PyResult<PyVal> {
        defaults::get_reboot_cause(self)
    }
    /// Reached as WatchdogBase.
    fn get_remaining_time(&self) -> PyResult<PyVal> {
        defaults::get_remaining_time(self)
    }
    /// Reached as DeviceBase.
    fn get_revision(&self) -> PyResult<PyVal> {
        defaults::get_revision(self)
    }
    /// Reached as ChassisBase.
    fn get_sed_mgmt(&self) -> PyResult<PyVal> {
        defaults::get_sed_mgmt(self)
    }
    /// Reached as DeviceBase.
    fn get_serial(&self) -> PyResult<PyVal> {
        defaults::get_serial(self)
    }
    /// Reached as ModuleBase.
    fn get_slot(&self) -> PyResult<PyVal> {
        defaults::get_slot(self)
    }
    /// Reached as FanBase.
    fn get_speed(&self) -> PyResult<PyVal> {
        defaults::get_speed(self)
    }
    /// Reached as FanBase.
    fn get_speed_tolerance(&self) -> PyResult<PyVal> {
        defaults::get_speed_tolerance(self)
    }
    /// Reached as DeviceBase.
    fn get_status(&self) -> PyResult<PyVal> {
        defaults::get_status(self)
    }
    /// Reached as FanBase, FanDrawerBase, PsuBase, ChassisBase.
    fn get_status_led(&self) -> PyResult<PyVal> {
        defaults::get_status_led(self)
    }
    /// Reached as PsuBase.
    fn get_status_master_led(&self) -> PyResult<PyVal> {
        defaults::get_status_master_led(self)
    }
    /// Reached as ChassisBase.
    fn get_supervisor_slot(&self) -> PyResult<PyVal> {
        defaults::get_supervisor_slot(self)
    }
    /// Reached as ChassisBase, ModuleBase.
    fn get_system_eeprom_info(&self) -> PyResult<PyVal> {
        defaults::get_system_eeprom_info(self)
    }
    /// Reached as FanBase.
    fn get_target_speed(&self) -> PyResult<PyVal> {
        defaults::get_target_speed(self)
    }
    /// Reached as ThermalBase, PsuBase.
    fn get_temperature(&self) -> PyResult<PyVal> {
        defaults::get_temperature(self)
    }
    /// Reached as PsuBase.
    fn get_temperature_high_threshold(&self) -> PyResult<PyVal> {
        defaults::get_temperature_high_threshold(self)
    }
    /// Reached as ChassisBase.
    fn get_thermal_manager(&self) -> PyResult<PyVal> {
        defaults::get_thermal_manager(self)
    }
    /// Reached as SedMgmtBase.
    fn get_tpm_bank_a_address(&self) -> PyResult<PyVal> {
        defaults::get_tpm_bank_a_address(self)
    }
    /// Reached as SedMgmtBase.
    fn get_tpm_bank_b_address(&self) -> PyResult<PyVal> {
        defaults::get_tpm_bank_b_address(self)
    }
    /// Reached as ModuleBase, LeakSensorProfileBase, LeakageSensorBase.
    fn get_type(&self) -> PyResult<PyVal> {
        defaults::get_type(self)
    }
    /// Reached as SensorBase.
    fn get_unit(&self) -> PyResult<PyVal> {
        defaults::get_unit(self)
    }
    /// Reached as SensorBase.
    fn get_value(&self) -> PyResult<PyVal> {
        defaults::get_value(self)
    }
    /// Reached as BMCBase.
    fn get_version(&self) -> PyResult<PyVal> {
        defaults::get_version(self)
    }
    /// Reached as PsuBase.
    fn get_voltage(&self) -> PyResult<PyVal> {
        defaults::get_voltage(self)
    }
    /// Reached as PsuBase.
    fn get_voltage_high_threshold(&self) -> PyResult<PyVal> {
        defaults::get_voltage_high_threshold(self)
    }
    /// Reached as PsuBase.
    fn get_voltage_low_threshold(&self) -> PyResult<PyVal> {
        defaults::get_voltage_low_threshold(self)
    }
    /// Reached as ChassisBase.
    fn get_watchdog(&self) -> PyResult<PyVal> {
        defaults::get_watchdog(self)
    }
    /// Reached as ChassisBase.
    fn init_midplane_switch(&self) -> PyResult<PyVal> {
        defaults::init_midplane_switch(self)
    }
    /// Reached as ThermalManagerBase.
    fn init_thermal_algorithm(&self, chassis: PyVal) -> PyResult<PyVal> {
        defaults::init_thermal_algorithm(self, chassis)
    }
    /// Reached as ThermalManagerBase.
    fn initialize(&self) -> PyResult<PyVal> {
        defaults::initialize(self)
    }
    /// Reached as ChassisBase.
    fn initizalize_system_led(&self) -> PyResult<PyVal> {
        defaults::initizalize_system_led(self)
    }
    /// Reached as ComponentBase.
    fn install_firmware(&self, image_path: &str) -> PyResult<PyVal> {
        defaults::install_firmware(self, image_path)
    }
    /// Reached as WatchdogBase.
    fn is_armed(&self) -> PyResult<PyVal> {
        defaults::is_armed(self)
    }
    /// Reached as ChassisBase.
    fn is_bmc(&self) -> PyResult<PyVal> {
        defaults::is_bmc(self)
    }
    /// Reached as ChassisBase.
    fn is_dpu(&self) -> PyResult<PyVal> {
        defaults::is_dpu(self)
    }
    /// Reached as LeakageSensorBase.
    fn is_leak(&self) -> PyResult<PyVal> {
        defaults::is_leak(self)
    }
    /// Reached as LeakageSensorBase.
    fn is_leak_sensor_ok(&self) -> PyResult<PyVal> {
        defaults::is_leak_sensor_ok(self)
    }
    /// Reached as ChassisBase.
    fn is_liquid_cooled(&self) -> PyResult<PyVal> {
        defaults::is_liquid_cooled(self)
    }
    /// Reached as ModuleBase.
    fn is_midplane_reachable(&self) -> PyResult<PyVal> {
        defaults::is_midplane_reachable(self)
    }
    /// Reached as ChassisBase.
    fn is_modular_chassis(&self) -> PyResult<PyVal> {
        defaults::is_modular_chassis(self)
    }
    /// Reached as FanBase.
    fn is_over_speed(&self) -> PyResult<PyVal> {
        defaults::is_over_speed(self)
    }
    /// Reached as DeviceBase.
    fn is_replaceable(&self) -> PyResult<PyVal> {
        defaults::is_replaceable(self)
    }
    /// Reached as ChassisBase.
    fn is_smartswitch(&self) -> PyResult<PyVal> {
        defaults::is_smartswitch(self)
    }
    /// Reached as FanBase.
    fn is_under_speed(&self) -> PyResult<PyVal> {
        defaults::is_under_speed(self)
    }
    /// Reached as ThermalManagerBase.
    fn load(&self, policy_file_name: &str) -> PyResult<PyVal> {
        defaults::load(self, policy_file_name)
    }
    /// Reached as ModuleBase.
    fn module_post_startup(&self) -> PyResult<PyVal> {
        defaults::module_post_startup(self)
    }
    /// Reached as ModuleBase.
    fn module_pre_shutdown(&self) -> PyResult<PyVal> {
        defaults::module_pre_shutdown(self)
    }
    /// Reached as BMCBase.
    fn open_session(&self) -> PyResult<PyVal> {
        defaults::open_session(self)
    }
    /// Reached as ModuleBase.
    fn pci_detach(&self) -> PyResult<PyVal> {
        defaults::pci_detach(self)
    }
    /// Reached as ModuleBase.
    fn pci_reattach(&self) -> PyResult<PyVal> {
        defaults::pci_reattach(self)
    }
    /// Reached as TlvInfoDecoder.
    fn read_eeprom(&self) -> PyResult<PyVal> {
        defaults::read_eeprom(self)
    }
    /// Reached as ModuleBase.
    fn reboot(&self, reboot_type: &str) -> PyResult<PyVal> {
        defaults::reboot(self, reboot_type)
    }
    /// Reached as BMCBase.
    fn request_bmc_reset(&self, graceful: bool) -> PyResult<PyVal> {
        defaults::request_bmc_reset(self, graceful)
    }
    /// Reached as BMCBase.
    fn reset_root_password(&self) -> PyResult<PyVal> {
        defaults::reset_root_password(self)
    }
    /// Reached as SedMgmtBase.
    fn reset_sed_password(&self) -> PyResult<PyVal> {
        defaults::reset_sed_password(self)
    }
    /// Reached as ThermalManagerBase.
    fn run_policy(&self, chassis: PyVal) -> PyResult<PyVal> {
        defaults::run_policy(self, chassis)
    }
    /// Reached as ModuleBase.
    fn set_admin_state(&self, up: PyVal) -> PyResult<PyVal> {
        defaults::set_admin_state(self, up)
    }
    /// Reached as ModuleBase.
    fn set_admin_state_gracefully(&self, up: PyVal) -> PyResult<PyVal> {
        defaults::set_admin_state_gracefully(self, up)
    }
    /// Reached as SensorBase.
    fn set_high_threshold(&self, value: PyVal) -> PyResult<PyVal> {
        defaults::set_high_threshold(self, value)
    }
    /// Reached as SensorBase.
    fn set_low_threshold(&self, value: PyVal) -> PyResult<PyVal> {
        defaults::set_low_threshold(self, value)
    }
    /// Reached as ModuleBase.
    fn set_module_state_transition(&self, module_name: PyVal, transition_type: &str) -> PyResult<PyVal> {
        defaults::set_module_state_transition(self, module_name, transition_type)
    }
    /// Reached as FanBase.
    fn set_speed(&self, speed: i128) -> PyResult<PyVal> {
        defaults::set_speed(self, speed)
    }
    /// Reached as FanBase, FanDrawerBase, PsuBase, ChassisBase.
    fn set_status_led(&self, color: &str) -> PyResult<PyVal> {
        defaults::set_status_led(self, color)
    }
    /// Reached as PsuBase.
    fn set_status_master_led(&self, color: &str) -> PyResult<PyVal> {
        defaults::set_status_master_led(self, color)
    }
    /// Reached as ThermalManagerBase.
    fn stop(&self) -> PyResult<PyVal> {
        defaults::stop(self)
    }
    /// Reached as BMCBase.
    fn trigger_bmc_debug_log_dump(&self) -> PyResult<PyVal> {
        defaults::trigger_bmc_debug_log_dump(self)
    }
    /// Reached as TlvInfoDecoder.
    fn update_eeprom_db(&self, e: PyVal) -> PyResult<PyVal> {
        defaults::update_eeprom_db(self, e)
    }
    /// Reached as ComponentBase, BMCBase.
    fn update_firmware(&self, image_path: &str) -> PyResult<PyVal> {
        defaults::update_firmware(self, image_path)
    }
}

/// What each base class answers, method by method.
pub mod defaults {
    use super::*;

    #[allow(unused_variables)]
    pub fn arm<S: PyObject + ?Sized>(s: &S, seconds: i128) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from WatchdogBase
            BaseClass::WatchdogBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "arm")),
        }
    }
    #[allow(unused_variables)]
    pub fn auto_update_firmware<S: PyObject + ?Sized>(s: &S, image_path: &str, boot_type: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ComponentBase
            BaseClass::ComponentBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "auto_update_firmware")),
        }
    }
    #[allow(unused_variables)]
    pub fn change_sed_password<S: PyObject + ?Sized>(s: &S, new_password: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from SedMgmtBase
            BaseClass::SedMgmtBase => crate::bodies::sed_mgmt_base::change_sed_password(s, new_password),
            _ => Err(PyErr::missing(s.py_class(), "change_sed_password")),
        }
    }
    #[allow(unused_variables)]
    pub fn clear_module_gnoi_halt_in_progress<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ModuleBase
            BaseClass::ModuleBase => crate::bodies::module_base::clear_module_gnoi_halt_in_progress(s),
            _ => Err(PyErr::missing(s.py_class(), "clear_module_gnoi_halt_in_progress")),
        }
    }
    #[allow(unused_variables)]
    pub fn clear_module_state_transition<S: PyObject + ?Sized>(s: &S, module_name: PyVal) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ModuleBase
            BaseClass::ModuleBase => crate::bodies::module_base::clear_module_state_transition(s, module_name),
            _ => Err(PyErr::missing(s.py_class(), "clear_module_state_transition")),
        }
    }
    #[allow(unused_variables)]
    pub fn close_session<S: PyObject + ?Sized>(s: &S, session_id: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::close_session(s, session_id),
            _ => Err(PyErr::missing(s.py_class(), "close_session")),
        }
    }
    #[allow(unused_variables)]
    pub fn deinitialize<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // literal, from ThermalManagerBase
            BaseClass::ThermalManagerBase => Ok(PyVal::None),
            _ => Err(PyErr::missing(s.py_class(), "deinitialize")),
        }
    }
    #[allow(unused_variables)]
    pub fn disarm<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from WatchdogBase
            BaseClass::WatchdogBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "disarm")),
        }
    }
    #[allow(unused_variables)]
    pub fn do_power_cycle<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "do_power_cycle")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_asics<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ModuleBase
            BaseClass::ModuleBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_asics")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_components<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::List(vec![])),
            // state, from ModuleBase
            BaseClass::ModuleBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_components")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_current_sensors<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::List(vec![])),
            // state, from ModuleBase
            BaseClass::ModuleBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_current_sensors")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_fan_drawers<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_fan_drawers")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_fans<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::List(vec![])),
            // state, from ModuleBase
            BaseClass::ModuleBase => Ok(PyVal::List(vec![])),
            // state, from FanDrawerBase
            BaseClass::FanDrawerBase => Ok(PyVal::List(vec![])),
            // state, from PsuBase
            BaseClass::PsuBase => Ok(PyVal::List(vec![])),
            // state, from PsuBase
            BaseClass::PdbBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_fans")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_leak_sensors<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from LiquidCoolingBase
            BaseClass::LiquidCoolingBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_leak_sensors")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_modules<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_modules")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_pdbs<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_pdbs")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_profiles<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from LiquidCoolingBase
            BaseClass::LiquidCoolingBase => crate::bodies::liquid_cooling_base::get_all_profiles(s),
            _ => Err(PyErr::missing(s.py_class(), "get_all_profiles")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_psus<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::List(vec![])),
            // state, from ModuleBase
            BaseClass::ModuleBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_psus")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_thermals<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::List(vec![])),
            // state, from ModuleBase
            BaseClass::ModuleBase => Ok(PyVal::List(vec![])),
            // state, from PsuBase
            BaseClass::PsuBase => Ok(PyVal::List(vec![])),
            // state, from PsuBase
            BaseClass::PdbBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_thermals")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_all_voltage_sensors<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::List(vec![])),
            // state, from ModuleBase
            BaseClass::ModuleBase => Ok(PyVal::List(vec![])),
            _ => Err(PyErr::missing(s.py_class(), "get_all_voltage_sensors")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_available_firmware_version<S: PyObject + ?Sized>(s: &S, image_path: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ComponentBase
            BaseClass::ComponentBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_available_firmware_version")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_base_mac<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ChassisBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_base_mac")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_bmc<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::None),
            _ => Err(PyErr::missing(s.py_class(), "get_bmc")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_bmc_debug_log_dump<S: PyObject + ?Sized>(s: &S, task_id: &str, filename: &str, path: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::get_bmc_debug_log_dump(s, task_id, filename, path),
            _ => Err(PyErr::missing(s.py_class(), "get_bmc_debug_log_dump")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_change_event<S: PyObject + ?Sized>(s: &S, timeout: i128) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ChassisBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_change_event")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_controlplane_state<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ChassisBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_controlplane_state")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_current<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // body, from PdbBase
            BaseClass::PdbBase => crate::bodies::pdb_base::get_current(s),
            _ => Err(PyErr::missing(s.py_class(), "get_current")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_dataplane_state<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ChassisBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_dataplane_state")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_default_sed_password<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from SedMgmtBase
            BaseClass::SedMgmtBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_default_sed_password")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_description<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from ComponentBase
            BaseClass::ComponentBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_description")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_direction<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from FanBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_direction")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_dpu_id<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ChassisBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_dpu_id")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_eeprom<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::None),
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::get_eeprom(s),
            _ => Err(PyErr::missing(s.py_class(), "get_eeprom")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_firmware_update_notification<S: PyObject + ?Sized>(s: &S, image_path: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // literal, from ComponentBase
            BaseClass::ComponentBase => Ok(PyVal::None),
            _ => Err(PyErr::missing(s.py_class(), "get_firmware_update_notification")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_firmware_version<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ComponentBase
            BaseClass::ComponentBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_firmware_version")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_high_critical_threshold<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ThermalBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_high_critical_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_high_threshold<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ThermalBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_high_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_input_current<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_input_current")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_input_power<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PdbBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_input_power")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_input_voltage<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_input_voltage")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_interval<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ThermalManagerBase
            BaseClass::ThermalManagerBase => crate::bodies::thermal_manager_base::get_interval(s),
            _ => Err(PyErr::missing(s.py_class(), "get_interval")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_leak_max_minor_duration_sec<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // literal, from LeakSensorProfileBase
            BaseClass::LeakSensorProfileBase => Ok(PyVal::None),
            _ => Err(PyErr::missing(s.py_class(), "get_leak_max_minor_duration_sec")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_leak_profile<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from LeakageSensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_leak_profile")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_leak_sensor_location<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from LeakageSensorBase
            BaseClass::LeakageSensorBase => Ok(PyVal::Str("unknown".to_string())),
            _ => Err(PyErr::missing(s.py_class(), "get_leak_sensor_location")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_leak_sensor_type<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from LeakageSensorBase
            BaseClass::LeakageSensorBase => Ok(PyVal::Str("unknown".to_string())),
            _ => Err(PyErr::missing(s.py_class(), "get_leak_sensor_type")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_leak_severity<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from LeakageSensorBase
            BaseClass::LeakageSensorBase => crate::bodies::leakage_sensor_base::get_leak_severity(s),
            _ => Err(PyErr::missing(s.py_class(), "get_leak_severity")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_liquid_cooling<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // notimpl, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::NotImplementedClass),
            _ => Err(PyErr::missing(s.py_class(), "get_liquid_cooling")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_low_critical_threshold<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ThermalBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_low_critical_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_low_threshold<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ThermalBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_low_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_max_sed_password_len<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from SedMgmtBase
            BaseClass::SedMgmtBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_max_sed_password_len")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_maximum_consumed_power<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from FanDrawerBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_maximum_consumed_power")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_maximum_recorded<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ThermalBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_maximum_recorded")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_maximum_supplied_power<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_maximum_supplied_power")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_midplane_down_reason<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_midplane_down_reason")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_midplane_ip<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_midplane_ip")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_min_sed_password_len<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from SedMgmtBase
            BaseClass::SedMgmtBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_min_sed_password_len")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_minimum_recorded<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ThermalBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_minimum_recorded")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_model<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from DeviceBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LiquidCoolingBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::get_model(s),
            _ => Err(PyErr::missing(s.py_class(), "get_model")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_module_index<S: PyObject + ?Sized>(s: &S, module_name: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ChassisBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_module_index")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_module_state_transition<S: PyObject + ?Sized>(s: &S, module_name: PyVal) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ModuleBase
            BaseClass::ModuleBase => crate::bodies::module_base::get_module_state_transition(s, module_name),
            _ => Err(PyErr::missing(s.py_class(), "get_module_state_transition")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_my_slot<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // notimpl, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::NotImplementedClass),
            _ => Err(PyErr::missing(s.py_class(), "get_my_slot")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_name<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from DeviceBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LiquidCoolingBase => Err(PyErr::not_implemented()),
            // state, from LeakageSensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_ported("LeakageSensorBase.get_name answers base-class state the implementation has to provide")),
            // raise, from ComponentBase
            BaseClass::ComponentBase => Err(PyErr::not_implemented()),
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::get_name(s),
            _ => Err(PyErr::missing(s.py_class(), "get_name")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_oper_status<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_oper_status")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_output_current<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PdbBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_output_current")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_output_power<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PdbBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_output_power")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_output_voltage<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PdbBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_output_voltage")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_pci_bus_info<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_pci_bus_info")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_position_in_parent<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from DeviceBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LiquidCoolingBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::BMCBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_position_in_parent")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_power<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // body, from PdbBase
            BaseClass::PdbBase => crate::bodies::pdb_base::get_power(s),
            _ => Err(PyErr::missing(s.py_class(), "get_power")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_powergood_status<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_powergood_status")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_presence<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from DeviceBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LiquidCoolingBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::get_presence(s),
            _ => Err(PyErr::missing(s.py_class(), "get_presence")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_psu_power_critical_threshold<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_psu_power_critical_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_psu_power_warning_suppress_threshold<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_psu_power_warning_suppress_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_reboot_cause<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ChassisBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_reboot_cause")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_remaining_time<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from WatchdogBase
            BaseClass::WatchdogBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_remaining_time")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_revision<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from DeviceBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LiquidCoolingBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            // literal, from BMCBase
            BaseClass::BMCBase => Ok(PyVal::Str("N/A".to_string())),
            _ => Err(PyErr::missing(s.py_class(), "get_revision")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_sed_mgmt<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::None),
            _ => Err(PyErr::missing(s.py_class(), "get_sed_mgmt")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_serial<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from DeviceBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LiquidCoolingBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::get_serial(s),
            _ => Err(PyErr::missing(s.py_class(), "get_serial")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_slot<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_slot")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_speed<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from FanBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_speed")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_speed_tolerance<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from FanBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_speed_tolerance")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_status<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from DeviceBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LiquidCoolingBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::get_status(s),
            _ => Err(PyErr::missing(s.py_class(), "get_status")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_status_led<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ChassisBase
            BaseClass::ChassisBase => crate::bodies::chassis_base::get_status_led(s),
            // raise, from FanBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from FanDrawerBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_status_led")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_status_master_led<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from PsuBase
            BaseClass::PsuBase => crate::bodies::psu_base::get_status_master_led(s),
            // body, from PsuBase
            BaseClass::PdbBase => crate::bodies::psu_base::get_status_master_led(s),
            _ => Err(PyErr::missing(s.py_class(), "get_status_master_led")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_supervisor_slot<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // notimpl, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::NotImplementedClass),
            _ => Err(PyErr::missing(s.py_class(), "get_supervisor_slot")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_system_eeprom_info<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ChassisBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_system_eeprom_info")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_target_speed<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from FanBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_target_speed")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_temperature<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            // raise, from ThermalBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_temperature")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_temperature_high_threshold<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_temperature_high_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_thermal_manager<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ChassisBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_thermal_manager")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_tpm_bank_a_address<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from SedMgmtBase
            BaseClass::SedMgmtBase => crate::bodies::sed_mgmt_base::get_tpm_bank_a_address(s),
            _ => Err(PyErr::missing(s.py_class(), "get_tpm_bank_a_address")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_tpm_bank_b_address<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from SedMgmtBase
            BaseClass::SedMgmtBase => crate::bodies::sed_mgmt_base::get_tpm_bank_b_address(s),
            _ => Err(PyErr::missing(s.py_class(), "get_tpm_bank_b_address")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_type<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // literal, from VoltageSensorBase
            BaseClass::VoltageSensorBase => Ok(PyVal::Str("SENSOR_TYPE_VOLTAGE".to_string())),
            // literal, from CurrentSensorBase
            BaseClass::CurrentSensorBase => Ok(PyVal::Str("SENSOR_TYPE_CURRENT".to_string())),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            // literal, from LeakSensorProfileBase
            BaseClass::LeakSensorProfileBase => Ok(PyVal::None),
            _ => Err(PyErr::missing(s.py_class(), "get_type")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_unit<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // literal, from VoltageSensorBase
            BaseClass::VoltageSensorBase => Ok(PyVal::Str("mV".to_string())),
            // literal, from CurrentSensorBase
            BaseClass::CurrentSensorBase => Ok(PyVal::Str("mA".to_string())),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_unit")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_value<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_value")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_version<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::get_version(s),
            _ => Err(PyErr::missing(s.py_class(), "get_version")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_voltage<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // body, from PdbBase
            BaseClass::PdbBase => crate::bodies::pdb_base::get_voltage(s),
            _ => Err(PyErr::missing(s.py_class(), "get_voltage")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_voltage_high_threshold<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_voltage_high_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_voltage_low_threshold<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "get_voltage_low_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn get_watchdog<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::None),
            _ => Err(PyErr::missing(s.py_class(), "get_watchdog")),
        }
    }
    #[allow(unused_variables)]
    pub fn init_midplane_switch<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // notimpl, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::NotImplementedClass),
            _ => Err(PyErr::missing(s.py_class(), "init_midplane_switch")),
        }
    }
    #[allow(unused_variables)]
    pub fn init_thermal_algorithm<S: PyObject + ?Sized>(s: &S, chassis: PyVal) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ThermalManagerBase
            BaseClass::ThermalManagerBase => crate::bodies::thermal_manager_base::init_thermal_algorithm(s, chassis),
            _ => Err(PyErr::missing(s.py_class(), "init_thermal_algorithm")),
        }
    }
    #[allow(unused_variables)]
    pub fn initialize<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // literal, from ThermalManagerBase
            BaseClass::ThermalManagerBase => Ok(PyVal::None),
            _ => Err(PyErr::missing(s.py_class(), "initialize")),
        }
    }
    #[allow(unused_variables)]
    pub fn initizalize_system_led<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ChassisBase
            BaseClass::ChassisBase => crate::bodies::chassis_base::initizalize_system_led(s),
            _ => Err(PyErr::missing(s.py_class(), "initizalize_system_led")),
        }
    }
    #[allow(unused_variables)]
    pub fn install_firmware<S: PyObject + ?Sized>(s: &S, image_path: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ComponentBase
            BaseClass::ComponentBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "install_firmware")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_armed<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from WatchdogBase
            BaseClass::WatchdogBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "is_armed")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_bmc<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // literal, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::Bool(false)),
            _ => Err(PyErr::missing(s.py_class(), "is_bmc")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_dpu<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // literal, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::Bool(false)),
            _ => Err(PyErr::missing(s.py_class(), "is_dpu")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_leak<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from LeakageSensorBase
            BaseClass::LeakageSensorBase => Ok(PyVal::Bool(false)),
            _ => Err(PyErr::missing(s.py_class(), "is_leak")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_leak_sensor_ok<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // state, from LeakageSensorBase
            BaseClass::LeakageSensorBase => Ok(PyVal::Bool(true)),
            _ => Err(PyErr::missing(s.py_class(), "is_leak_sensor_ok")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_liquid_cooled<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // literal, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::Bool(false)),
            _ => Err(PyErr::missing(s.py_class(), "is_liquid_cooled")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_midplane_reachable<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // notimpl, from ModuleBase
            BaseClass::ModuleBase => Ok(PyVal::NotImplementedClass),
            _ => Err(PyErr::missing(s.py_class(), "is_midplane_reachable")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_modular_chassis<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // literal, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::Bool(false)),
            _ => Err(PyErr::missing(s.py_class(), "is_modular_chassis")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_over_speed<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from FanBase
            BaseClass::FanBase => crate::bodies::fan_base::is_over_speed(s),
            _ => Err(PyErr::missing(s.py_class(), "is_over_speed")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_replaceable<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from DeviceBase
            BaseClass::ChassisBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LiquidCoolingBase => Err(PyErr::not_implemented()),
            // raise, from DeviceBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            // literal, from BMCBase
            BaseClass::BMCBase => Ok(PyVal::Bool(false)),
            _ => Err(PyErr::missing(s.py_class(), "is_replaceable")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_smartswitch<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // literal, from ChassisBase
            BaseClass::ChassisBase => Ok(PyVal::Bool(false)),
            _ => Err(PyErr::missing(s.py_class(), "is_smartswitch")),
        }
    }
    #[allow(unused_variables)]
    pub fn is_under_speed<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from FanBase
            BaseClass::FanBase => crate::bodies::fan_base::is_under_speed(s),
            _ => Err(PyErr::missing(s.py_class(), "is_under_speed")),
        }
    }
    #[allow(unused_variables)]
    pub fn load<S: PyObject + ?Sized>(s: &S, policy_file_name: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ThermalManagerBase
            BaseClass::ThermalManagerBase => crate::bodies::thermal_manager_base::load(s, policy_file_name),
            _ => Err(PyErr::missing(s.py_class(), "load")),
        }
    }
    #[allow(unused_variables)]
    pub fn module_post_startup<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ModuleBase
            BaseClass::ModuleBase => crate::bodies::module_base::module_post_startup(s),
            _ => Err(PyErr::missing(s.py_class(), "module_post_startup")),
        }
    }
    #[allow(unused_variables)]
    pub fn module_pre_shutdown<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ModuleBase
            BaseClass::ModuleBase => crate::bodies::module_base::module_pre_shutdown(s),
            _ => Err(PyErr::missing(s.py_class(), "module_pre_shutdown")),
        }
    }
    #[allow(unused_variables)]
    pub fn open_session<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::open_session(s),
            _ => Err(PyErr::missing(s.py_class(), "open_session")),
        }
    }
    #[allow(unused_variables)]
    pub fn pci_detach<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "pci_detach")),
        }
    }
    #[allow(unused_variables)]
    pub fn pci_reattach<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "pci_reattach")),
        }
    }
    #[allow(unused_variables)]
    pub fn read_eeprom<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from TlvInfoDecoder
            BaseClass::TlvInfoDecoder => crate::bodies::tlv_info_decoder::read_eeprom(s),
            _ => Err(PyErr::missing(s.py_class(), "read_eeprom")),
        }
    }
    #[allow(unused_variables)]
    pub fn reboot<S: PyObject + ?Sized>(s: &S, reboot_type: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "reboot")),
        }
    }
    #[allow(unused_variables)]
    pub fn request_bmc_reset<S: PyObject + ?Sized>(s: &S, graceful: bool) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::request_bmc_reset(s, graceful),
            _ => Err(PyErr::missing(s.py_class(), "request_bmc_reset")),
        }
    }
    #[allow(unused_variables)]
    pub fn reset_root_password<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::reset_root_password(s),
            _ => Err(PyErr::missing(s.py_class(), "reset_root_password")),
        }
    }
    #[allow(unused_variables)]
    pub fn reset_sed_password<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from SedMgmtBase
            BaseClass::SedMgmtBase => crate::bodies::sed_mgmt_base::reset_sed_password(s),
            _ => Err(PyErr::missing(s.py_class(), "reset_sed_password")),
        }
    }
    #[allow(unused_variables)]
    pub fn run_policy<S: PyObject + ?Sized>(s: &S, chassis: PyVal) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ThermalManagerBase
            BaseClass::ThermalManagerBase => crate::bodies::thermal_manager_base::run_policy(s, chassis),
            _ => Err(PyErr::missing(s.py_class(), "run_policy")),
        }
    }
    #[allow(unused_variables)]
    pub fn set_admin_state<S: PyObject + ?Sized>(s: &S, up: PyVal) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ModuleBase
            BaseClass::ModuleBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "set_admin_state")),
        }
    }
    #[allow(unused_variables)]
    pub fn set_admin_state_gracefully<S: PyObject + ?Sized>(s: &S, up: PyVal) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ModuleBase
            BaseClass::ModuleBase => crate::bodies::module_base::set_admin_state_gracefully(s, up),
            _ => Err(PyErr::missing(s.py_class(), "set_admin_state_gracefully")),
        }
    }
    #[allow(unused_variables)]
    pub fn set_high_threshold<S: PyObject + ?Sized>(s: &S, value: PyVal) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ThermalBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "set_high_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn set_low_threshold<S: PyObject + ?Sized>(s: &S, value: PyVal) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ThermalBase
            BaseClass::ThermalBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::SensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::VoltageSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::CurrentSensorBase => Err(PyErr::not_implemented()),
            // raise, from SensorBase
            BaseClass::LeakageSensorBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "set_low_threshold")),
        }
    }
    #[allow(unused_variables)]
    pub fn set_module_state_transition<S: PyObject + ?Sized>(s: &S, module_name: PyVal, transition_type: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ModuleBase
            BaseClass::ModuleBase => crate::bodies::module_base::set_module_state_transition(s, module_name, transition_type),
            _ => Err(PyErr::missing(s.py_class(), "set_module_state_transition")),
        }
    }
    #[allow(unused_variables)]
    pub fn set_speed<S: PyObject + ?Sized>(s: &S, speed: i128) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from FanBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "set_speed")),
        }
    }
    #[allow(unused_variables)]
    pub fn set_status_led<S: PyObject + ?Sized>(s: &S, color: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ChassisBase
            BaseClass::ChassisBase => crate::bodies::chassis_base::set_status_led(s, color),
            // raise, from FanBase
            BaseClass::FanBase => Err(PyErr::not_implemented()),
            // raise, from FanDrawerBase
            BaseClass::FanDrawerBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PsuBase => Err(PyErr::not_implemented()),
            // raise, from PsuBase
            BaseClass::PdbBase => Err(PyErr::not_implemented()),
            _ => Err(PyErr::missing(s.py_class(), "set_status_led")),
        }
    }
    #[allow(unused_variables)]
    pub fn set_status_master_led<S: PyObject + ?Sized>(s: &S, color: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from PsuBase
            BaseClass::PsuBase => crate::bodies::psu_base::set_status_master_led(s, color),
            // body, from PsuBase
            BaseClass::PdbBase => crate::bodies::psu_base::set_status_master_led(s, color),
            _ => Err(PyErr::missing(s.py_class(), "set_status_master_led")),
        }
    }
    #[allow(unused_variables)]
    pub fn stop<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from ThermalManagerBase
            BaseClass::ThermalManagerBase => crate::bodies::thermal_manager_base::stop(s),
            _ => Err(PyErr::missing(s.py_class(), "stop")),
        }
    }
    #[allow(unused_variables)]
    pub fn trigger_bmc_debug_log_dump<S: PyObject + ?Sized>(s: &S) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::trigger_bmc_debug_log_dump(s),
            _ => Err(PyErr::missing(s.py_class(), "trigger_bmc_debug_log_dump")),
        }
    }
    #[allow(unused_variables)]
    pub fn update_eeprom_db<S: PyObject + ?Sized>(s: &S, e: PyVal) -> PyResult<PyVal> {
        match s.base_class() {
            // body, from TlvInfoDecoder
            BaseClass::TlvInfoDecoder => crate::bodies::tlv_info_decoder::update_eeprom_db(s, e),
            _ => Err(PyErr::missing(s.py_class(), "update_eeprom_db")),
        }
    }
    #[allow(unused_variables)]
    pub fn update_firmware<S: PyObject + ?Sized>(s: &S, image_path: &str) -> PyResult<PyVal> {
        match s.base_class() {
            // raise, from ComponentBase
            BaseClass::ComponentBase => Err(PyErr::not_implemented()),
            // body, from BMCBase
            BaseClass::BMCBase => crate::bodies::bmc_base::update_firmware(s, image_path),
            _ => Err(PyErr::missing(s.py_class(), "update_firmware")),
        }
    }
}

/// What a [`DynObject`] answers a call with: `Some` to answer, `None` to let
/// its base class answer, as a Python method not defined on the class would.
pub type Handler =
    Box<dyn Fn(&dyn PyObject, &str, &[PyVal]) -> Option<PyResult<PyVal>> + Send + Sync>;

/// A platform object whose methods are decided at run time, by name.
///
/// What a Python class built with `type(name, (base,), methods)` is: the
/// methods it was given answer, every other one is its base class's.  The
/// cross-language tests script a chassis this way on both sides.
pub struct DynObject {
    pub class: &'static str,
    pub base: BaseClass,
    pub handler: Handler,
}

impl PyObject for DynObject {
    fn py_class(&self) -> &'static str {
        self.class
    }

    fn base_class(&self) -> BaseClass {
        self.base
    }

    fn arm(&self, seconds: i128) -> PyResult<PyVal> {
        match (self.handler)(self, "arm", &[PyVal::Int(seconds)]) {
            Some(r) => r,
            None => defaults::arm(self, seconds),
        }
    }

    fn auto_update_firmware(&self, image_path: &str, boot_type: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "auto_update_firmware", &[PyVal::Str(image_path.to_string()), PyVal::Str(boot_type.to_string())]) {
            Some(r) => r,
            None => defaults::auto_update_firmware(self, image_path, boot_type),
        }
    }

    fn change_sed_password(&self, new_password: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "change_sed_password", &[PyVal::Str(new_password.to_string())]) {
            Some(r) => r,
            None => defaults::change_sed_password(self, new_password),
        }
    }

    fn clear_module_gnoi_halt_in_progress(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "clear_module_gnoi_halt_in_progress", &[]) {
            Some(r) => r,
            None => defaults::clear_module_gnoi_halt_in_progress(self),
        }
    }

    fn clear_module_state_transition(&self, module_name: PyVal) -> PyResult<PyVal> {
        match (self.handler)(self, "clear_module_state_transition", std::slice::from_ref(&module_name)) {
            Some(r) => r,
            None => defaults::clear_module_state_transition(self, module_name),
        }
    }

    fn close_session(&self, session_id: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "close_session", &[PyVal::Str(session_id.to_string())]) {
            Some(r) => r,
            None => defaults::close_session(self, session_id),
        }
    }

    fn deinitialize(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "deinitialize", &[]) {
            Some(r) => r,
            None => defaults::deinitialize(self),
        }
    }

    fn disarm(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "disarm", &[]) {
            Some(r) => r,
            None => defaults::disarm(self),
        }
    }

    fn do_power_cycle(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "do_power_cycle", &[]) {
            Some(r) => r,
            None => defaults::do_power_cycle(self),
        }
    }

    fn get_all_asics(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_asics", &[]) {
            Some(r) => r,
            None => defaults::get_all_asics(self),
        }
    }

    fn get_all_components(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_components", &[]) {
            Some(r) => r,
            None => defaults::get_all_components(self),
        }
    }

    fn get_all_current_sensors(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_current_sensors", &[]) {
            Some(r) => r,
            None => defaults::get_all_current_sensors(self),
        }
    }

    fn get_all_fan_drawers(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_fan_drawers", &[]) {
            Some(r) => r,
            None => defaults::get_all_fan_drawers(self),
        }
    }

    fn get_all_fans(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_fans", &[]) {
            Some(r) => r,
            None => defaults::get_all_fans(self),
        }
    }

    fn get_all_leak_sensors(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_leak_sensors", &[]) {
            Some(r) => r,
            None => defaults::get_all_leak_sensors(self),
        }
    }

    fn get_all_modules(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_modules", &[]) {
            Some(r) => r,
            None => defaults::get_all_modules(self),
        }
    }

    fn get_all_pdbs(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_pdbs", &[]) {
            Some(r) => r,
            None => defaults::get_all_pdbs(self),
        }
    }

    fn get_all_profiles(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_profiles", &[]) {
            Some(r) => r,
            None => defaults::get_all_profiles(self),
        }
    }

    fn get_all_psus(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_psus", &[]) {
            Some(r) => r,
            None => defaults::get_all_psus(self),
        }
    }

    fn get_all_thermals(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_thermals", &[]) {
            Some(r) => r,
            None => defaults::get_all_thermals(self),
        }
    }

    fn get_all_voltage_sensors(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_all_voltage_sensors", &[]) {
            Some(r) => r,
            None => defaults::get_all_voltage_sensors(self),
        }
    }

    fn get_available_firmware_version(&self, image_path: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "get_available_firmware_version", &[PyVal::Str(image_path.to_string())]) {
            Some(r) => r,
            None => defaults::get_available_firmware_version(self, image_path),
        }
    }

    fn get_base_mac(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_base_mac", &[]) {
            Some(r) => r,
            None => defaults::get_base_mac(self),
        }
    }

    fn get_bmc(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_bmc", &[]) {
            Some(r) => r,
            None => defaults::get_bmc(self),
        }
    }

    fn get_bmc_debug_log_dump(&self, task_id: &str, filename: &str, path: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "get_bmc_debug_log_dump", &[PyVal::Str(task_id.to_string()), PyVal::Str(filename.to_string()), PyVal::Str(path.to_string())]) {
            Some(r) => r,
            None => defaults::get_bmc_debug_log_dump(self, task_id, filename, path),
        }
    }

    fn get_change_event(&self, timeout: i128) -> PyResult<PyVal> {
        match (self.handler)(self, "get_change_event", &[PyVal::Int(timeout)]) {
            Some(r) => r,
            None => defaults::get_change_event(self, timeout),
        }
    }

    fn get_controlplane_state(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_controlplane_state", &[]) {
            Some(r) => r,
            None => defaults::get_controlplane_state(self),
        }
    }

    fn get_current(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_current", &[]) {
            Some(r) => r,
            None => defaults::get_current(self),
        }
    }

    fn get_dataplane_state(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_dataplane_state", &[]) {
            Some(r) => r,
            None => defaults::get_dataplane_state(self),
        }
    }

    fn get_default_sed_password(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_default_sed_password", &[]) {
            Some(r) => r,
            None => defaults::get_default_sed_password(self),
        }
    }

    fn get_description(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_description", &[]) {
            Some(r) => r,
            None => defaults::get_description(self),
        }
    }

    fn get_direction(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_direction", &[]) {
            Some(r) => r,
            None => defaults::get_direction(self),
        }
    }

    fn get_dpu_id(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_dpu_id", &[]) {
            Some(r) => r,
            None => defaults::get_dpu_id(self),
        }
    }

    fn get_eeprom(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_eeprom", &[]) {
            Some(r) => r,
            None => defaults::get_eeprom(self),
        }
    }

    fn get_firmware_update_notification(&self, image_path: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "get_firmware_update_notification", &[PyVal::Str(image_path.to_string())]) {
            Some(r) => r,
            None => defaults::get_firmware_update_notification(self, image_path),
        }
    }

    fn get_firmware_version(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_firmware_version", &[]) {
            Some(r) => r,
            None => defaults::get_firmware_version(self),
        }
    }

    fn get_high_critical_threshold(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_high_critical_threshold", &[]) {
            Some(r) => r,
            None => defaults::get_high_critical_threshold(self),
        }
    }

    fn get_high_threshold(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_high_threshold", &[]) {
            Some(r) => r,
            None => defaults::get_high_threshold(self),
        }
    }

    fn get_input_current(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_input_current", &[]) {
            Some(r) => r,
            None => defaults::get_input_current(self),
        }
    }

    fn get_input_power(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_input_power", &[]) {
            Some(r) => r,
            None => defaults::get_input_power(self),
        }
    }

    fn get_input_voltage(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_input_voltage", &[]) {
            Some(r) => r,
            None => defaults::get_input_voltage(self),
        }
    }

    fn get_interval(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_interval", &[]) {
            Some(r) => r,
            None => defaults::get_interval(self),
        }
    }

    fn get_leak_max_minor_duration_sec(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_leak_max_minor_duration_sec", &[]) {
            Some(r) => r,
            None => defaults::get_leak_max_minor_duration_sec(self),
        }
    }

    fn get_leak_profile(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_leak_profile", &[]) {
            Some(r) => r,
            None => defaults::get_leak_profile(self),
        }
    }

    fn get_leak_sensor_location(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_leak_sensor_location", &[]) {
            Some(r) => r,
            None => defaults::get_leak_sensor_location(self),
        }
    }

    fn get_leak_sensor_type(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_leak_sensor_type", &[]) {
            Some(r) => r,
            None => defaults::get_leak_sensor_type(self),
        }
    }

    fn get_leak_severity(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_leak_severity", &[]) {
            Some(r) => r,
            None => defaults::get_leak_severity(self),
        }
    }

    fn get_liquid_cooling(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_liquid_cooling", &[]) {
            Some(r) => r,
            None => defaults::get_liquid_cooling(self),
        }
    }

    fn get_low_critical_threshold(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_low_critical_threshold", &[]) {
            Some(r) => r,
            None => defaults::get_low_critical_threshold(self),
        }
    }

    fn get_low_threshold(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_low_threshold", &[]) {
            Some(r) => r,
            None => defaults::get_low_threshold(self),
        }
    }

    fn get_max_sed_password_len(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_max_sed_password_len", &[]) {
            Some(r) => r,
            None => defaults::get_max_sed_password_len(self),
        }
    }

    fn get_maximum_consumed_power(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_maximum_consumed_power", &[]) {
            Some(r) => r,
            None => defaults::get_maximum_consumed_power(self),
        }
    }

    fn get_maximum_recorded(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_maximum_recorded", &[]) {
            Some(r) => r,
            None => defaults::get_maximum_recorded(self),
        }
    }

    fn get_maximum_supplied_power(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_maximum_supplied_power", &[]) {
            Some(r) => r,
            None => defaults::get_maximum_supplied_power(self),
        }
    }

    fn get_midplane_down_reason(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_midplane_down_reason", &[]) {
            Some(r) => r,
            None => defaults::get_midplane_down_reason(self),
        }
    }

    fn get_midplane_ip(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_midplane_ip", &[]) {
            Some(r) => r,
            None => defaults::get_midplane_ip(self),
        }
    }

    fn get_min_sed_password_len(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_min_sed_password_len", &[]) {
            Some(r) => r,
            None => defaults::get_min_sed_password_len(self),
        }
    }

    fn get_minimum_recorded(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_minimum_recorded", &[]) {
            Some(r) => r,
            None => defaults::get_minimum_recorded(self),
        }
    }

    fn get_model(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_model", &[]) {
            Some(r) => r,
            None => defaults::get_model(self),
        }
    }

    fn get_module_index(&self, module_name: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "get_module_index", &[PyVal::Str(module_name.to_string())]) {
            Some(r) => r,
            None => defaults::get_module_index(self, module_name),
        }
    }

    fn get_module_state_transition(&self, module_name: PyVal) -> PyResult<PyVal> {
        match (self.handler)(self, "get_module_state_transition", std::slice::from_ref(&module_name)) {
            Some(r) => r,
            None => defaults::get_module_state_transition(self, module_name),
        }
    }

    fn get_my_slot(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_my_slot", &[]) {
            Some(r) => r,
            None => defaults::get_my_slot(self),
        }
    }

    fn get_name(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_name", &[]) {
            Some(r) => r,
            None => defaults::get_name(self),
        }
    }

    fn get_oper_status(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_oper_status", &[]) {
            Some(r) => r,
            None => defaults::get_oper_status(self),
        }
    }

    fn get_output_current(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_output_current", &[]) {
            Some(r) => r,
            None => defaults::get_output_current(self),
        }
    }

    fn get_output_power(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_output_power", &[]) {
            Some(r) => r,
            None => defaults::get_output_power(self),
        }
    }

    fn get_output_voltage(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_output_voltage", &[]) {
            Some(r) => r,
            None => defaults::get_output_voltage(self),
        }
    }

    fn get_pci_bus_info(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_pci_bus_info", &[]) {
            Some(r) => r,
            None => defaults::get_pci_bus_info(self),
        }
    }

    fn get_position_in_parent(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_position_in_parent", &[]) {
            Some(r) => r,
            None => defaults::get_position_in_parent(self),
        }
    }

    fn get_power(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_power", &[]) {
            Some(r) => r,
            None => defaults::get_power(self),
        }
    }

    fn get_powergood_status(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_powergood_status", &[]) {
            Some(r) => r,
            None => defaults::get_powergood_status(self),
        }
    }

    fn get_presence(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_presence", &[]) {
            Some(r) => r,
            None => defaults::get_presence(self),
        }
    }

    fn get_psu_power_critical_threshold(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_psu_power_critical_threshold", &[]) {
            Some(r) => r,
            None => defaults::get_psu_power_critical_threshold(self),
        }
    }

    fn get_psu_power_warning_suppress_threshold(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_psu_power_warning_suppress_threshold", &[]) {
            Some(r) => r,
            None => defaults::get_psu_power_warning_suppress_threshold(self),
        }
    }

    fn get_reboot_cause(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_reboot_cause", &[]) {
            Some(r) => r,
            None => defaults::get_reboot_cause(self),
        }
    }

    fn get_remaining_time(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_remaining_time", &[]) {
            Some(r) => r,
            None => defaults::get_remaining_time(self),
        }
    }

    fn get_revision(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_revision", &[]) {
            Some(r) => r,
            None => defaults::get_revision(self),
        }
    }

    fn get_sed_mgmt(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_sed_mgmt", &[]) {
            Some(r) => r,
            None => defaults::get_sed_mgmt(self),
        }
    }

    fn get_serial(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_serial", &[]) {
            Some(r) => r,
            None => defaults::get_serial(self),
        }
    }

    fn get_slot(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_slot", &[]) {
            Some(r) => r,
            None => defaults::get_slot(self),
        }
    }

    fn get_speed(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_speed", &[]) {
            Some(r) => r,
            None => defaults::get_speed(self),
        }
    }

    fn get_speed_tolerance(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_speed_tolerance", &[]) {
            Some(r) => r,
            None => defaults::get_speed_tolerance(self),
        }
    }

    fn get_status(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_status", &[]) {
            Some(r) => r,
            None => defaults::get_status(self),
        }
    }

    fn get_status_led(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_status_led", &[]) {
            Some(r) => r,
            None => defaults::get_status_led(self),
        }
    }

    fn get_status_master_led(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_status_master_led", &[]) {
            Some(r) => r,
            None => defaults::get_status_master_led(self),
        }
    }

    fn get_supervisor_slot(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_supervisor_slot", &[]) {
            Some(r) => r,
            None => defaults::get_supervisor_slot(self),
        }
    }

    fn get_system_eeprom_info(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_system_eeprom_info", &[]) {
            Some(r) => r,
            None => defaults::get_system_eeprom_info(self),
        }
    }

    fn get_target_speed(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_target_speed", &[]) {
            Some(r) => r,
            None => defaults::get_target_speed(self),
        }
    }

    fn get_temperature(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_temperature", &[]) {
            Some(r) => r,
            None => defaults::get_temperature(self),
        }
    }

    fn get_temperature_high_threshold(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_temperature_high_threshold", &[]) {
            Some(r) => r,
            None => defaults::get_temperature_high_threshold(self),
        }
    }

    fn get_thermal_manager(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_thermal_manager", &[]) {
            Some(r) => r,
            None => defaults::get_thermal_manager(self),
        }
    }

    fn get_tpm_bank_a_address(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_tpm_bank_a_address", &[]) {
            Some(r) => r,
            None => defaults::get_tpm_bank_a_address(self),
        }
    }

    fn get_tpm_bank_b_address(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_tpm_bank_b_address", &[]) {
            Some(r) => r,
            None => defaults::get_tpm_bank_b_address(self),
        }
    }

    fn get_type(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_type", &[]) {
            Some(r) => r,
            None => defaults::get_type(self),
        }
    }

    fn get_unit(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_unit", &[]) {
            Some(r) => r,
            None => defaults::get_unit(self),
        }
    }

    fn get_value(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_value", &[]) {
            Some(r) => r,
            None => defaults::get_value(self),
        }
    }

    fn get_version(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_version", &[]) {
            Some(r) => r,
            None => defaults::get_version(self),
        }
    }

    fn get_voltage(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_voltage", &[]) {
            Some(r) => r,
            None => defaults::get_voltage(self),
        }
    }

    fn get_voltage_high_threshold(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_voltage_high_threshold", &[]) {
            Some(r) => r,
            None => defaults::get_voltage_high_threshold(self),
        }
    }

    fn get_voltage_low_threshold(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_voltage_low_threshold", &[]) {
            Some(r) => r,
            None => defaults::get_voltage_low_threshold(self),
        }
    }

    fn get_watchdog(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "get_watchdog", &[]) {
            Some(r) => r,
            None => defaults::get_watchdog(self),
        }
    }

    fn init_midplane_switch(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "init_midplane_switch", &[]) {
            Some(r) => r,
            None => defaults::init_midplane_switch(self),
        }
    }

    fn init_thermal_algorithm(&self, chassis: PyVal) -> PyResult<PyVal> {
        match (self.handler)(self, "init_thermal_algorithm", std::slice::from_ref(&chassis)) {
            Some(r) => r,
            None => defaults::init_thermal_algorithm(self, chassis),
        }
    }

    fn initialize(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "initialize", &[]) {
            Some(r) => r,
            None => defaults::initialize(self),
        }
    }

    fn initizalize_system_led(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "initizalize_system_led", &[]) {
            Some(r) => r,
            None => defaults::initizalize_system_led(self),
        }
    }

    fn install_firmware(&self, image_path: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "install_firmware", &[PyVal::Str(image_path.to_string())]) {
            Some(r) => r,
            None => defaults::install_firmware(self, image_path),
        }
    }

    fn is_armed(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_armed", &[]) {
            Some(r) => r,
            None => defaults::is_armed(self),
        }
    }

    fn is_bmc(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_bmc", &[]) {
            Some(r) => r,
            None => defaults::is_bmc(self),
        }
    }

    fn is_dpu(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_dpu", &[]) {
            Some(r) => r,
            None => defaults::is_dpu(self),
        }
    }

    fn is_leak(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_leak", &[]) {
            Some(r) => r,
            None => defaults::is_leak(self),
        }
    }

    fn is_leak_sensor_ok(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_leak_sensor_ok", &[]) {
            Some(r) => r,
            None => defaults::is_leak_sensor_ok(self),
        }
    }

    fn is_liquid_cooled(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_liquid_cooled", &[]) {
            Some(r) => r,
            None => defaults::is_liquid_cooled(self),
        }
    }

    fn is_midplane_reachable(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_midplane_reachable", &[]) {
            Some(r) => r,
            None => defaults::is_midplane_reachable(self),
        }
    }

    fn is_modular_chassis(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_modular_chassis", &[]) {
            Some(r) => r,
            None => defaults::is_modular_chassis(self),
        }
    }

    fn is_over_speed(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_over_speed", &[]) {
            Some(r) => r,
            None => defaults::is_over_speed(self),
        }
    }

    fn is_replaceable(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_replaceable", &[]) {
            Some(r) => r,
            None => defaults::is_replaceable(self),
        }
    }

    fn is_smartswitch(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_smartswitch", &[]) {
            Some(r) => r,
            None => defaults::is_smartswitch(self),
        }
    }

    fn is_under_speed(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "is_under_speed", &[]) {
            Some(r) => r,
            None => defaults::is_under_speed(self),
        }
    }

    fn load(&self, policy_file_name: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "load", &[PyVal::Str(policy_file_name.to_string())]) {
            Some(r) => r,
            None => defaults::load(self, policy_file_name),
        }
    }

    fn module_post_startup(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "module_post_startup", &[]) {
            Some(r) => r,
            None => defaults::module_post_startup(self),
        }
    }

    fn module_pre_shutdown(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "module_pre_shutdown", &[]) {
            Some(r) => r,
            None => defaults::module_pre_shutdown(self),
        }
    }

    fn open_session(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "open_session", &[]) {
            Some(r) => r,
            None => defaults::open_session(self),
        }
    }

    fn pci_detach(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "pci_detach", &[]) {
            Some(r) => r,
            None => defaults::pci_detach(self),
        }
    }

    fn pci_reattach(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "pci_reattach", &[]) {
            Some(r) => r,
            None => defaults::pci_reattach(self),
        }
    }

    fn read_eeprom(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "read_eeprom", &[]) {
            Some(r) => r,
            None => defaults::read_eeprom(self),
        }
    }

    fn reboot(&self, reboot_type: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "reboot", &[PyVal::Str(reboot_type.to_string())]) {
            Some(r) => r,
            None => defaults::reboot(self, reboot_type),
        }
    }

    fn request_bmc_reset(&self, graceful: bool) -> PyResult<PyVal> {
        match (self.handler)(self, "request_bmc_reset", &[PyVal::Bool(graceful)]) {
            Some(r) => r,
            None => defaults::request_bmc_reset(self, graceful),
        }
    }

    fn reset_root_password(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "reset_root_password", &[]) {
            Some(r) => r,
            None => defaults::reset_root_password(self),
        }
    }

    fn reset_sed_password(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "reset_sed_password", &[]) {
            Some(r) => r,
            None => defaults::reset_sed_password(self),
        }
    }

    fn run_policy(&self, chassis: PyVal) -> PyResult<PyVal> {
        match (self.handler)(self, "run_policy", std::slice::from_ref(&chassis)) {
            Some(r) => r,
            None => defaults::run_policy(self, chassis),
        }
    }

    fn set_admin_state(&self, up: PyVal) -> PyResult<PyVal> {
        match (self.handler)(self, "set_admin_state", std::slice::from_ref(&up)) {
            Some(r) => r,
            None => defaults::set_admin_state(self, up),
        }
    }

    fn set_admin_state_gracefully(&self, up: PyVal) -> PyResult<PyVal> {
        match (self.handler)(self, "set_admin_state_gracefully", std::slice::from_ref(&up)) {
            Some(r) => r,
            None => defaults::set_admin_state_gracefully(self, up),
        }
    }

    fn set_high_threshold(&self, value: PyVal) -> PyResult<PyVal> {
        match (self.handler)(self, "set_high_threshold", std::slice::from_ref(&value)) {
            Some(r) => r,
            None => defaults::set_high_threshold(self, value),
        }
    }

    fn set_low_threshold(&self, value: PyVal) -> PyResult<PyVal> {
        match (self.handler)(self, "set_low_threshold", std::slice::from_ref(&value)) {
            Some(r) => r,
            None => defaults::set_low_threshold(self, value),
        }
    }

    fn set_module_state_transition(&self, module_name: PyVal, transition_type: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "set_module_state_transition", &[module_name.clone(), PyVal::Str(transition_type.to_string())]) {
            Some(r) => r,
            None => defaults::set_module_state_transition(self, module_name, transition_type),
        }
    }

    fn set_speed(&self, speed: i128) -> PyResult<PyVal> {
        match (self.handler)(self, "set_speed", &[PyVal::Int(speed)]) {
            Some(r) => r,
            None => defaults::set_speed(self, speed),
        }
    }

    fn set_status_led(&self, color: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "set_status_led", &[PyVal::Str(color.to_string())]) {
            Some(r) => r,
            None => defaults::set_status_led(self, color),
        }
    }

    fn set_status_master_led(&self, color: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "set_status_master_led", &[PyVal::Str(color.to_string())]) {
            Some(r) => r,
            None => defaults::set_status_master_led(self, color),
        }
    }

    fn stop(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "stop", &[]) {
            Some(r) => r,
            None => defaults::stop(self),
        }
    }

    fn trigger_bmc_debug_log_dump(&self) -> PyResult<PyVal> {
        match (self.handler)(self, "trigger_bmc_debug_log_dump", &[]) {
            Some(r) => r,
            None => defaults::trigger_bmc_debug_log_dump(self),
        }
    }

    fn update_eeprom_db(&self, e: PyVal) -> PyResult<PyVal> {
        match (self.handler)(self, "update_eeprom_db", std::slice::from_ref(&e)) {
            Some(r) => r,
            None => defaults::update_eeprom_db(self, e),
        }
    }

    fn update_firmware(&self, image_path: &str) -> PyResult<PyVal> {
        match (self.handler)(self, "update_firmware", &[PyVal::Str(image_path.to_string())]) {
            Some(r) => r,
            None => defaults::update_firmware(self, image_path),
        }
    }
}
