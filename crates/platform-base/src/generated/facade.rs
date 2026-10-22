//! The platform API over native platform objects.
//!
//! GENERATED from sonic_platform_api/facade.pyi by generator/generate.py.  Do
//! not edit: regenerate.
//!
//! Line for line, what `sonic_platform_api/facade.py` does over a vendor's
//! Python objects and then what `platform-pyo3` does with the rows it gets
//! back -- the same traversals, in the same order, calling the same getters,
//! with the same normalisation, and failing with the same text.  A row is
//! built in two steps for that reason: its columns as Python values first
//! (`Py<Row>`, the facade's row object), then read into the Rust row
//! (`read_<row>`, the bridge's reader).  See `generator/native.py` for which
//! function each piece stands for.
#![allow(
    clippy::redundant_closure_call,
    clippy::needless_borrow,
    // The singleton walk is the same shape as every other: a list it pushes to.
    clippy::vec_init_then_push,
    // An absorbed column is `Ok(<its read>)` whatever the read is; where the
    // read is one call, its `?` and the `Ok` cancel.
    clippy::needless_question_mark
)]

use platform_api::{
    LedColor, FanKind, PowerEntityKind, ThermalKind, ModuleType, ModuleStatus, SensorKind, EepromUpdate, LeakSeverity, ChangeEventKind,
    ThermalInfo, FanInfo, FanDrawerInfo, PsuInfo, ChassisInfo, ModuleInfo, ComponentInfo, SensorInfo, LeakProfile, LeakSensorInfo, WatchdogInfo, ChangeEvent, ChangeEventBatch, PcieDevice, PcieAerStat, StorageDeviceInfo, EepromTlv, AsicInfo, BmcInfo, ModuleRebootCause, ModuleMidplaneDownReason, BmcResult,
    ThermalInfoCols, FanInfoCols, FanDrawerInfoCols, ChassisInfoCols, ModuleInfoCols,
    DeviceKey, Number, PlatformApi, PlatformError,
};

use std::collections::HashSet;

use crate::escape_hatch::EscapeHatches;
use crate::facade_rt::*;
use crate::py::{Exc, PyErr, PyResult, PyVal};


/// `ThermalInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyThermalInfo {
    pub name: PyVal,
    pub kind: PyVal,
    pub parent_name: PyVal,
    pub key: PyVal,
    pub parent_key: PyVal,
    pub position_in_parent: PyVal,
    pub temperature: PyVal,
    pub is_replaceable: PyVal,
    pub min_recorded: PyVal,
    pub max_recorded: PyVal,
    pub high_threshold: PyVal,
    pub low_threshold: PyVal,
    pub high_critical_threshold: PyVal,
    pub low_critical_threshold: PyVal,
    pub error: PyVal,
    pub error_repr: PyVal,
    pub error_column: PyVal,
}

/// The bridge's read of one `ThermalInfo`.
pub fn read_thermal_info(row: &PyThermalInfo) -> Result<ThermalInfo, PlatformError> {
    Ok(ThermalInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        kind: rd_text("kind", &row.kind)?.and_then(|s| ThermalKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        parent_name: rd_text("parent_name", &row.parent_name)?.unwrap_or_default(),
        key: rd_text("key", &row.key)?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: rd_text("parent_key", &row.parent_key)?.map(DeviceKey::from),
        position_in_parent: rd_int::<i32>(&row.position_in_parent)?,
        temperature: rd_number(&row.temperature)?,
        is_replaceable: rd_flag(&row.is_replaceable)?.unwrap_or(false),
        min_recorded: rd_number(&row.min_recorded)?,
        max_recorded: rd_number(&row.max_recorded)?,
        high_threshold: rd_number(&row.high_threshold)?,
        low_threshold: rd_number(&row.low_threshold)?,
        high_critical_threshold: rd_number(&row.high_critical_threshold)?,
        low_critical_threshold: rd_number(&row.low_critical_threshold)?,
        error: rd_text("error", &row.error)?,
        error_repr: rd_text("error_repr", &row.error_repr)?,
        error_column: rd_text("error_column", &row.error_column)?,
    })
}

/// `FanInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyFanInfo {
    pub name: PyVal,
    pub kind: PyVal,
    pub parent_name: PyVal,
    pub key: PyVal,
    pub parent_key: PyVal,
    pub drawer_name: PyVal,
    pub position_in_parent: PyVal,
    pub is_replaceable: PyVal,
    pub presence: PyVal,
    pub speed_pct: PyVal,
    pub target_speed_pct: PyVal,
    pub is_under_speed: PyVal,
    pub is_over_speed: PyVal,
    pub status: PyVal,
    pub direction: PyVal,
    pub model: PyVal,
    pub serial: PyVal,
    pub status_led: PyVal,
    pub error: PyVal,
    pub error_repr: PyVal,
    pub error_column: PyVal,
}

/// The bridge's read of one `FanInfo`.
pub fn read_fan_info(row: &PyFanInfo) -> Result<FanInfo, PlatformError> {
    Ok(FanInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        kind: rd_text("kind", &row.kind)?.and_then(|s| FanKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        parent_name: rd_text("parent_name", &row.parent_name)?.unwrap_or_default(),
        key: rd_text("key", &row.key)?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: rd_text("parent_key", &row.parent_key)?.map(DeviceKey::from),
        drawer_name: rd_text("drawer_name", &row.drawer_name)?.unwrap_or_default(),
        position_in_parent: rd_int::<i32>(&row.position_in_parent)?,
        is_replaceable: rd_flag(&row.is_replaceable)?.unwrap_or(false),
        presence: rd_flag(&row.presence)?.unwrap_or(false),
        speed_pct: rd_number(&row.speed_pct)?,
        target_speed_pct: rd_number(&row.target_speed_pct)?,
        is_under_speed: rd_flag(&row.is_under_speed)?,
        is_over_speed: rd_flag(&row.is_over_speed)?,
        status: rd_flag(&row.status)?.unwrap_or(false),
        direction: rd_text("direction", &row.direction)?,
        model: rd_text("model", &row.model)?,
        serial: rd_text("serial", &row.serial)?,
        status_led: rd_text("status_led", &row.status_led)?,
        error: rd_text("error", &row.error)?,
        error_repr: rd_text("error_repr", &row.error_repr)?,
        error_column: rd_text("error_column", &row.error_column)?,
    })
}

/// `FanDrawerInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyFanDrawerInfo {
    pub name: PyVal,
    pub key: PyVal,
    pub position_in_parent: PyVal,
    pub presence: PyVal,
    pub status: PyVal,
    pub is_replaceable: PyVal,
    pub model: PyVal,
    pub serial: PyVal,
    pub status_led: PyVal,
    pub maximum_consumed_power: PyVal,
}

/// The bridge's read of one `FanDrawerInfo`.
pub fn read_fan_drawer_info(row: &PyFanDrawerInfo) -> Result<FanDrawerInfo, PlatformError> {
    Ok(FanDrawerInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        key: rd_text("key", &row.key)?.map(DeviceKey::from).unwrap_or_default(),
        position_in_parent: rd_int::<i32>(&row.position_in_parent)?,
        presence: rd_flag(&row.presence)?.unwrap_or(false),
        status: rd_flag(&row.status)?,
        is_replaceable: rd_flag(&row.is_replaceable)?.unwrap_or(false),
        model: rd_text("model", &row.model)?,
        serial: rd_text("serial", &row.serial)?,
        status_led: rd_text("status_led", &row.status_led)?,
        maximum_consumed_power: rd_number(&row.maximum_consumed_power)?,
    })
}

/// `PsuInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyPsuInfo {
    pub name: PyVal,
    pub kind: PyVal,
    pub key: PyVal,
    pub position_in_parent: PyVal,
    pub presence: PyVal,
    pub is_replaceable: PyVal,
    pub model: PyVal,
    pub serial: PyVal,
    pub revision: PyVal,
    pub power_good: PyVal,
    pub status_led: PyVal,
    pub voltage: PyVal,
    pub current: PyVal,
    pub power: PyVal,
    pub input_voltage: PyVal,
    pub input_current: PyVal,
    pub input_power: PyVal,
    pub temperature: PyVal,
    pub temperature_high_threshold: PyVal,
    pub voltage_high_threshold: PyVal,
    pub voltage_low_threshold: PyVal,
    pub maximum_supplied_power: PyVal,
    pub power_warning_suppress_threshold: PyVal,
    pub power_critical_threshold: PyVal,
}

/// The bridge's read of one `PsuInfo`.
pub fn read_psu_info(row: &PyPsuInfo) -> Result<PsuInfo, PlatformError> {
    Ok(PsuInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        kind: rd_text("kind", &row.kind)?.and_then(|s| PowerEntityKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        key: rd_text("key", &row.key)?.map(DeviceKey::from).unwrap_or_default(),
        position_in_parent: rd_int::<i32>(&row.position_in_parent)?,
        presence: rd_flag(&row.presence)?.unwrap_or(false),
        is_replaceable: rd_flag(&row.is_replaceable)?.unwrap_or(false),
        model: rd_text("model", &row.model)?,
        serial: rd_text("serial", &row.serial)?,
        revision: rd_text("revision", &row.revision)?,
        power_good: rd_flag(&row.power_good)?.unwrap_or(false),
        status_led: rd_text("status_led", &row.status_led)?,
        voltage: rd_number(&row.voltage)?,
        current: rd_number(&row.current)?,
        power: rd_number(&row.power)?,
        input_voltage: rd_number(&row.input_voltage)?,
        input_current: rd_number(&row.input_current)?,
        input_power: rd_number(&row.input_power)?,
        temperature: rd_number(&row.temperature)?,
        temperature_high_threshold: rd_number(&row.temperature_high_threshold)?,
        voltage_high_threshold: rd_number(&row.voltage_high_threshold)?,
        voltage_low_threshold: rd_number(&row.voltage_low_threshold)?,
        maximum_supplied_power: rd_number(&row.maximum_supplied_power)?,
        power_warning_suppress_threshold: rd_number(&row.power_warning_suppress_threshold)?,
        power_critical_threshold: rd_number(&row.power_critical_threshold)?,
    })
}

/// `ChassisInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyChassisInfo {
    pub name: PyVal,
    pub presence: PyVal,
    pub model: PyVal,
    pub serial: PyVal,
    pub revision: PyVal,
    pub status: PyVal,
    pub base_mac: PyVal,
    pub is_modular_chassis: PyVal,
    pub is_smartswitch: PyVal,
    pub is_dpu: PyVal,
    pub is_bmc: PyVal,
    pub is_liquid_cooled: PyVal,
    pub reboot_cause: PyVal,
    pub reboot_cause_detail: PyVal,
    pub my_slot: PyVal,
    pub supervisor_slot: PyVal,
    pub dpu_id: PyVal,
    pub dataplane_state: PyVal,
    pub controlplane_state: PyVal,
    pub status_led: PyVal,
}

/// The bridge's read of one `ChassisInfo`.
pub fn read_chassis_info(row: &PyChassisInfo) -> Result<ChassisInfo, PlatformError> {
    Ok(ChassisInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        presence: rd_flag(&row.presence)?.unwrap_or(true),
        model: rd_text("model", &row.model)?,
        serial: rd_text("serial", &row.serial)?,
        revision: rd_text("revision", &row.revision)?,
        status: rd_flag(&row.status)?,
        base_mac: rd_text("base_mac", &row.base_mac)?,
        is_modular_chassis: rd_flag(&row.is_modular_chassis)?.unwrap_or(false),
        is_smartswitch: rd_flag(&row.is_smartswitch)?.unwrap_or(false),
        is_dpu: rd_flag(&row.is_dpu)?.unwrap_or(false),
        is_bmc: rd_flag(&row.is_bmc)?.unwrap_or(false),
        is_liquid_cooled: rd_flag(&row.is_liquid_cooled)?.unwrap_or(false),
        reboot_cause: rd_text("reboot_cause", &row.reboot_cause)?,
        reboot_cause_detail: rd_text("reboot_cause_detail", &row.reboot_cause_detail)?,
        my_slot: rd_int::<i64>(&row.my_slot)?,
        supervisor_slot: rd_int::<i64>(&row.supervisor_slot)?,
        dpu_id: rd_int::<i64>(&row.dpu_id)?,
        dataplane_state: rd_flag(&row.dataplane_state)?,
        controlplane_state: rd_flag(&row.controlplane_state)?,
        status_led: rd_text("status_led", &row.status_led)?,
    })
}

/// `ModuleInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyModuleInfo {
    pub name: PyVal,
    pub parent_name: PyVal,
    pub key: PyVal,
    pub parent_key: PyVal,
    pub position_in_parent: PyVal,
    pub presence: PyVal,
    pub status: PyVal,
    pub is_replaceable: PyVal,
    pub model: PyVal,
    pub serial: PyVal,
    pub description: PyVal,
    pub slot: PyVal,
    pub r#type: PyVal,
    pub oper_status: PyVal,
    pub base_mac: PyVal,
    pub dpu_id: PyVal,
    pub maximum_consumed_power: PyVal,
    pub midplane_ip: PyVal,
    pub is_midplane_reachable: PyVal,
    pub state_transition: PyVal,
}

/// The bridge's read of one `ModuleInfo`.
pub fn read_module_info(row: &PyModuleInfo) -> Result<ModuleInfo, PlatformError> {
    Ok(ModuleInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        parent_name: rd_text("parent_name", &row.parent_name)?.unwrap_or_default(),
        key: rd_text("key", &row.key)?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: rd_text("parent_key", &row.parent_key)?.map(DeviceKey::from),
        position_in_parent: rd_int::<i32>(&row.position_in_parent)?,
        presence: rd_flag(&row.presence)?.unwrap_or(false),
        status: rd_flag(&row.status)?,
        is_replaceable: rd_flag(&row.is_replaceable)?.unwrap_or(false),
        model: rd_text("model", &row.model)?,
        serial: rd_text("serial", &row.serial)?,
        description: rd_text("description", &row.description)?,
        slot: rd_int::<i64>(&row.slot)?,
        r#type: rd_text("type", &row.r#type)?.and_then(|s| ModuleType::from_str(&s)),
        oper_status: rd_text("oper_status", &row.oper_status)?.and_then(|s| ModuleStatus::from_str(&s)),
        base_mac: rd_text("base_mac", &row.base_mac)?,
        dpu_id: rd_int::<i64>(&row.dpu_id)?,
        maximum_consumed_power: rd_number(&row.maximum_consumed_power)?,
        midplane_ip: rd_text("midplane_ip", &row.midplane_ip)?,
        is_midplane_reachable: rd_flag(&row.is_midplane_reachable)?,
        state_transition: rd_flag(&row.state_transition)?,
    })
}

/// `ComponentInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyComponentInfo {
    pub name: PyVal,
    pub parent_name: PyVal,
    pub key: PyVal,
    pub parent_key: PyVal,
    pub description: PyVal,
    pub firmware_version: PyVal,
}

/// The bridge's read of one `ComponentInfo`.
pub fn read_component_info(row: &PyComponentInfo) -> Result<ComponentInfo, PlatformError> {
    Ok(ComponentInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        parent_name: rd_text("parent_name", &row.parent_name)?.unwrap_or_default(),
        key: rd_text("key", &row.key)?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: rd_text("parent_key", &row.parent_key)?.map(DeviceKey::from),
        description: rd_text("description", &row.description)?,
        firmware_version: rd_text("firmware_version", &row.firmware_version)?,
    })
}

/// `SensorInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PySensorInfo {
    pub name: PyVal,
    pub kind: PyVal,
    pub parent_name: PyVal,
    pub key: PyVal,
    pub parent_key: PyVal,
    pub position_in_parent: PyVal,
    pub value: PyVal,
    pub is_replaceable: PyVal,
    pub unit: PyVal,
    pub min_recorded: PyVal,
    pub max_recorded: PyVal,
    pub high_threshold: PyVal,
    pub low_threshold: PyVal,
    pub high_critical_threshold: PyVal,
    pub low_critical_threshold: PyVal,
    pub error: PyVal,
    pub error_repr: PyVal,
    pub error_column: PyVal,
}

/// The bridge's read of one `SensorInfo`.
pub fn read_sensor_info(row: &PySensorInfo) -> Result<SensorInfo, PlatformError> {
    Ok(SensorInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        kind: rd_text("kind", &row.kind)?.and_then(|s| SensorKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        parent_name: rd_text("parent_name", &row.parent_name)?.unwrap_or_default(),
        key: rd_text("key", &row.key)?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: rd_text("parent_key", &row.parent_key)?.map(DeviceKey::from),
        position_in_parent: rd_int::<i32>(&row.position_in_parent)?,
        value: rd_number(&row.value)?,
        is_replaceable: rd_flag(&row.is_replaceable)?.unwrap_or(false),
        unit: rd_text("unit", &row.unit)?,
        min_recorded: rd_number(&row.min_recorded)?,
        max_recorded: rd_number(&row.max_recorded)?,
        high_threshold: rd_number(&row.high_threshold)?,
        low_threshold: rd_number(&row.low_threshold)?,
        high_critical_threshold: rd_number(&row.high_critical_threshold)?,
        low_critical_threshold: rd_number(&row.low_critical_threshold)?,
        error: rd_text("error", &row.error)?,
        error_repr: rd_text("error_repr", &row.error_repr)?,
        error_column: rd_text("error_column", &row.error_column)?,
    })
}

/// `LeakProfile` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyLeakProfile {
    pub r#type: PyVal,
    pub max_minor_duration_sec: PyVal,
}

/// The bridge's read of one `LeakProfile`.
pub fn read_leak_profile(row: &PyLeakProfile) -> Result<LeakProfile, PlatformError> {
    Ok(LeakProfile {
        r#type: rd_text("type", &row.r#type)?.unwrap_or_default(),
        max_minor_duration_sec: rd_int::<i64>(&row.max_minor_duration_sec)?,
    })
}

/// `LeakSensorInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyLeakSensorInfo {
    pub name: PyVal,
    pub parent_name: PyVal,
    pub sensor_type: PyVal,
    pub location: PyVal,
    pub is_leak: PyVal,
    pub is_ok: PyVal,
    pub severity: PyVal,
    pub profile_type: PyVal,
    pub profile_max_minor_duration_sec: PyVal,
}

/// The bridge's read of one `LeakSensorInfo`.
pub fn read_leak_sensor_info(row: &PyLeakSensorInfo) -> Result<LeakSensorInfo, PlatformError> {
    Ok(LeakSensorInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        parent_name: rd_text("parent_name", &row.parent_name)?.unwrap_or_default(),
        sensor_type: rd_text("sensor_type", &row.sensor_type)?,
        location: rd_text("location", &row.location)?,
        is_leak: rd_flag(&row.is_leak)?,
        is_ok: rd_flag(&row.is_ok)?,
        severity: rd_text("severity", &row.severity)?.and_then(|s| LeakSeverity::from_str(&s)),
        profile_type: rd_text("profile_type", &row.profile_type)?,
        profile_max_minor_duration_sec: rd_int::<i64>(&row.profile_max_minor_duration_sec)?,
    })
}

/// `WatchdogInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyWatchdogInfo {
    pub is_armed: PyVal,
    pub remaining_time: PyVal,
}

/// The bridge's read of one `WatchdogInfo`.
pub fn read_watchdog_info(row: &PyWatchdogInfo) -> Result<WatchdogInfo, PlatformError> {
    Ok(WatchdogInfo {
        is_armed: rd_flag(&row.is_armed)?,
        remaining_time: rd_int::<i64>(&row.remaining_time)?,
    })
}

/// `ChangeEvent` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyChangeEvent {
    pub device_type: PyVal,
    pub device_id: PyVal,
    pub status: PyVal,
    pub kind: PyVal,
}

/// The bridge's read of one `ChangeEvent`.
pub fn read_change_event(row: &PyChangeEvent) -> Result<ChangeEvent, PlatformError> {
    Ok(ChangeEvent {
        device_type: rd_text("device_type", &row.device_type)?.unwrap_or_default(),
        device_id: rd_text("device_id", &row.device_id)?.unwrap_or_default(),
        status: rd_text("status", &row.status)?.unwrap_or_default(),
        kind: rd_text("kind", &row.kind)?.and_then(|s| ChangeEventKind::from_str(&s)),
    })
}

/// `ChangeEventBatch` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyChangeEventBatch {
    pub ok: PyVal,
    pub events: Vec<PyChangeEvent>,
}

/// The bridge's read of one `ChangeEventBatch`.
pub fn read_change_event_batch(row: &PyChangeEventBatch) -> Result<ChangeEventBatch, PlatformError> {
    Ok(ChangeEventBatch {
        ok: rd_flag(&row.ok)?.unwrap_or(false),
        events: row.events.iter().map(read_change_event).collect::<Result<Vec<_>, _>>()?,
    })
}

/// `PcieDevice` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyPcieDevice {
    pub name: PyVal,
    pub bus: PyVal,
    pub dev: PyVal,
    pub r#fn: PyVal,
    pub present: PyVal,
}

/// The bridge's read of one `PcieDevice`.
pub fn read_pcie_device(row: &PyPcieDevice) -> Result<PcieDevice, PlatformError> {
    Ok(PcieDevice {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        bus: rd_int::<i64>(&row.bus)?.unwrap_or(Default::default()),
        dev: rd_int::<i64>(&row.dev)?.unwrap_or(Default::default()),
        r#fn: rd_int::<i64>(&row.r#fn)?.unwrap_or(Default::default()),
        present: rd_flag(&row.present)?.unwrap_or(false),
    })
}

/// `PcieAerStat` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyPcieAerStat {
    pub severity: PyVal,
    pub field: PyVal,
    pub value: PyVal,
}

/// The bridge's read of one `PcieAerStat`.
pub fn read_pcie_aer_stat(row: &PyPcieAerStat) -> Result<PcieAerStat, PlatformError> {
    Ok(PcieAerStat {
        severity: rd_text("severity", &row.severity)?.unwrap_or_default(),
        field: rd_text("field", &row.field)?.unwrap_or_default(),
        value: rd_text("value", &row.value)?.unwrap_or_default(),
    })
}

/// `StorageDeviceInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyStorageDeviceInfo {
    pub name: PyVal,
    pub available: PyVal,
    pub model: PyVal,
    pub serial: PyVal,
    pub firmware: PyVal,
    pub health: PyVal,
    pub temperature: PyVal,
    pub disk_io_reads: PyVal,
    pub disk_io_writes: PyVal,
    pub reserved_blocks: PyVal,
    pub fs_io_reads: PyVal,
    pub fs_io_writes: PyVal,
    pub static_error: PyVal,
    pub error: PyVal,
}

/// The bridge's read of one `StorageDeviceInfo`.
pub fn read_storage_device_info(row: &PyStorageDeviceInfo) -> Result<StorageDeviceInfo, PlatformError> {
    Ok(StorageDeviceInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        available: rd_flag(&row.available)?.unwrap_or(false),
        model: rd_text("model", &row.model)?.unwrap_or_default(),
        serial: rd_text("serial", &row.serial)?.unwrap_or_default(),
        firmware: rd_text("firmware", &row.firmware)?.unwrap_or_default(),
        health: rd_text("health", &row.health)?.unwrap_or_default(),
        temperature: rd_text("temperature", &row.temperature)?.unwrap_or_default(),
        disk_io_reads: rd_text("disk_io_reads", &row.disk_io_reads)?.unwrap_or_default(),
        disk_io_writes: rd_text("disk_io_writes", &row.disk_io_writes)?.unwrap_or_default(),
        reserved_blocks: rd_text("reserved_blocks", &row.reserved_blocks)?.unwrap_or_default(),
        fs_io_reads: rd_int::<i64>(&row.fs_io_reads)?,
        fs_io_writes: rd_int::<i64>(&row.fs_io_writes)?,
        static_error: rd_text("static_error", &row.static_error)?,
        error: rd_text("error", &row.error)?,
    })
}

/// `EepromTlv` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyEepromTlv {
    pub source: PyVal,
    pub parent_name: PyVal,
    pub code: PyVal,
    pub value: PyVal,
}

/// The bridge's read of one `EepromTlv`.
pub fn read_eeprom_tlv(row: &PyEepromTlv) -> Result<EepromTlv, PlatformError> {
    Ok(EepromTlv {
        source: rd_text("source", &row.source)?.unwrap_or_default(),
        parent_name: rd_text("parent_name", &row.parent_name)?.unwrap_or_default(),
        code: rd_text("code", &row.code)?.unwrap_or_default(),
        value: rd_text("value", &row.value)?,
    })
}

/// `AsicInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyAsicInfo {
    pub parent_name: PyVal,
    pub asic_id: PyVal,
    pub pci_address: PyVal,
}

/// The bridge's read of one `AsicInfo`.
pub fn read_asic_info(row: &PyAsicInfo) -> Result<AsicInfo, PlatformError> {
    Ok(AsicInfo {
        parent_name: rd_text("parent_name", &row.parent_name)?.unwrap_or_default(),
        asic_id: rd_text("asic_id", &row.asic_id)?.unwrap_or_default(),
        pci_address: rd_text("pci_address", &row.pci_address)?,
    })
}

/// `BmcInfo` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyBmcInfo {
    pub name: PyVal,
    pub presence: PyVal,
    pub model: PyVal,
    pub serial: PyVal,
    pub revision: PyVal,
    pub status: PyVal,
    pub is_replaceable: PyVal,
    pub version: PyVal,
}

/// The bridge's read of one `BmcInfo`.
pub fn read_bmc_info(row: &PyBmcInfo) -> Result<BmcInfo, PlatformError> {
    Ok(BmcInfo {
        name: rd_text("name", &row.name)?.unwrap_or_default(),
        presence: rd_flag(&row.presence)?.unwrap_or(false),
        model: rd_text("model", &row.model)?,
        serial: rd_text("serial", &row.serial)?,
        revision: rd_text("revision", &row.revision)?,
        status: rd_flag(&row.status)?,
        is_replaceable: rd_flag(&row.is_replaceable)?.unwrap_or(false),
        version: rd_text("version", &row.version)?,
    })
}

/// `ModuleRebootCause` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyModuleRebootCause {
    pub cause: PyVal,
    pub detail: PyVal,
}

/// The bridge's read of one `ModuleRebootCause`.
pub fn read_module_reboot_cause(row: &PyModuleRebootCause) -> Result<ModuleRebootCause, PlatformError> {
    Ok(ModuleRebootCause {
        cause: rd_text("cause", &row.cause)?,
        detail: rd_text("detail", &row.detail)?,
    })
}

/// `ModuleMidplaneDownReason` as the facade builds it: one Python value per column.
#[derive(Clone, Debug, Default)]
pub struct PyModuleMidplaneDownReason {
    pub reason: PyVal,
    pub detail: PyVal,
}

/// The bridge's read of one `ModuleMidplaneDownReason`.
pub fn read_module_midplane_down_reason(row: &PyModuleMidplaneDownReason) -> Result<ModuleMidplaneDownReason, PlatformError> {
    Ok(ModuleMidplaneDownReason {
        reason: rd_text("reason", &row.reason)?,
        detail: rd_text("detail", &row.detail)?,
    })
}

/// `BmcResult` as the facade builds it: one Python value per column.
#[derive(Clone, Default)]
pub struct PyBmcResult {
    pub code: PyVal,
    pub message: PyVal,
    pub session_id: PyVal,
    pub token: PyVal,
    pub task_id: PyVal,
}

/// The facade's `__repr__`: token said to be there, not shown.
impl std::fmt::Debug for PyBmcResult {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PyBmcResult")
            .field("code", &self.code)
            .field("message", &self.message)
            .field("session_id", &self.session_id)
            .field("token", &if self.token.is_none() { PyVal::None } else { PyVal::str("<redacted>") })
            .field("task_id", &self.task_id)
            .finish()
    }
}

/// The bridge's read of one `BmcResult`.
pub fn read_bmc_result(row: &PyBmcResult) -> Result<BmcResult, PlatformError> {
    Ok(BmcResult {
        code: rd_int::<i64>(&row.code)?.unwrap_or(Default::default()),
        message: rd_text("message", &row.message)?,
        session_id: rd_text("session_id", &row.session_id)?,
        token: rd_text("token", &row.token)?,
        task_id: rd_text("task_id", &row.task_id)?,
    })
}

/// `fixed[name]`: a column the traversal supplies; `KeyError` if it does not.
fn fixed_get(fixed: &[(&str, PyVal)], name: &str) -> PyResult<PyVal> {
    fixed
        .iter()
        .find(|(k, _)| *k == name)
        .map(|(_, v)| v.clone())
        .ok_or_else(|| PyErr::key_error(name))
}

/// `_fmt(v, template, parent, i, **fixed)` for a template that also names
/// fields the source fixes -- a sensor's `{kind}` (`names`).  Those are put
/// in first, as `str()` would spell them, then `{parent}` and `{i}`.
fn fmt_name_with(
    v: &PyVal,
    template: &str,
    parent: &str,
    i: usize,
    fixed: &[(&str, PyVal)],
    names: &[&str],
) -> PyResult<PyVal> {
    if !v.is_none() {
        return Ok(PyVal::Str(v.py_str()));
    }
    let mut t = template.to_string();
    for n in names {
        let field = format!("{}{}{}", '{', n, '}');
        t = t.replace(&field, &fixed_get(fixed, n)?.py_str());
    }
    Ok(fmt_name(&PyVal::None, &t, parent, i))
}

/// `PlatformApi` over a vendor's `ChassisBase`.
pub struct BaseFacade {
    chassis: PyVal,
    hatch: EscapeHatches,
}

impl BaseFacade {
    /// The facade over `chassis`; `hatch` carries what the escape hatches
    /// need from the vendor beyond the chassis itself.
    pub fn new(chassis: PyVal, hatch: EscapeHatches) -> Self {
        BaseFacade { chassis, hatch }
    }

    pub fn chassis(&self) -> &PyVal {
        &self.chassis
    }


    #[allow(unused_variables)]
    fn row_thermal_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)], cols: u64, skip: &HashSet<&str>) -> PyResult<PyThermalInfo> {
        let mut cols = cols;
        if skipped(fixed, skip)? {
            cols &= 1;
        }
        let mut row = PyThermalInfo {
            name: fmt_name(&text(call(get(dev, |o| o.get_name()))?), "{parent} Thermal {i}", parent, i),
            kind: fixed_get(fixed, "kind")?,
            parent_name: PyVal::Str(parent.to_string()),
            key: fixed_get(fixed, "key")?,
            parent_key: fixed_get(fixed, "parent_key")?,
            position_in_parent: if cols & (1 << 0) != 0 { call(get(dev, |o| o.get_position_in_parent()))? } else { PyVal::None },
            temperature: PyVal::None,
            is_replaceable: PyVal::Bool(false),
            min_recorded: PyVal::None,
            max_recorded: PyVal::None,
            high_threshold: PyVal::None,
            low_threshold: PyVal::None,
            high_critical_threshold: PyVal::None,
            low_critical_threshold: PyVal::None,
            error: PyVal::None,
            error_repr: PyVal::None,
            error_column: PyVal::None,
        };
        // try: ... except Exception as e -- the first getter that raises
        // ends the reading, and the row is still a row; `column` is the
        // one being read when it struck.
        let mut column = "";
        let r: PyResult<()> = (|| {
            column = "temperature";
            row.temperature = if cols & (1 << 1) != 0 { scalar(call(get(dev, |o| o.get_temperature()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None };
            column = "is_replaceable";
            row.is_replaceable = if cols & (1 << 2) != 0 { default(call(get(dev, |o| o.is_replaceable()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) };
            column = "min_recorded";
            row.min_recorded = if !row.temperature.is_none() { if cols & (1 << 3) != 0 { scalar(call(get(dev, |o| o.get_minimum_recorded()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None } } else { PyVal::None };
            column = "max_recorded";
            row.max_recorded = if !row.temperature.is_none() { if cols & (1 << 4) != 0 { scalar(call(get(dev, |o| o.get_maximum_recorded()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None } } else { PyVal::None };
            column = "high_threshold";
            row.high_threshold = if !row.temperature.is_none() { if cols & (1 << 5) != 0 { scalar(call(get(dev, |o| o.get_high_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None } } else { PyVal::None };
            column = "low_threshold";
            row.low_threshold = if !row.temperature.is_none() { if cols & (1 << 6) != 0 { scalar(call(get(dev, |o| o.get_low_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None } } else { PyVal::None };
            column = "high_critical_threshold";
            row.high_critical_threshold = if !row.temperature.is_none() { if cols & (1 << 7) != 0 { scalar(call(get(dev, |o| o.get_high_critical_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None } } else { PyVal::None };
            column = "low_critical_threshold";
            row.low_critical_threshold = if !row.temperature.is_none() { if cols & (1 << 8) != 0 { scalar(call(get(dev, |o| o.get_low_critical_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None } } else { PyVal::None };
            Ok(())
        })();
        if let Err(e) = r {
            row.error = PyVal::Str(e.str());
            row.error_repr = PyVal::Str(e.repr());
            row.error_column = PyVal::Str(column.to_string());
        }
        Ok(row)
    }

    /// Every ThermalInfo, in declared order: `_walk_thermal_info`.
    fn walk_thermal_info(&self, cols: u64, skip: &HashSet<&str>) -> PyResult<Vec<PyThermalInfo>> {
        let mut out = Vec::new();
        // ChassisBase.get_all_thermals
        for (i, dev) in iter(call(get(&self.chassis, |o| o.get_all_thermals()))?)?.into_iter().enumerate() {
            out.push(self.row_thermal_info(&dev, "chassis 1", i, &[("key", PyVal::Str(format!("thermals[{}]", i))), ("parent_key", PyVal::None), ("kind", PyVal::Str("chassis".to_string()))], cols, skip)?);
        }
        // PsuBase.get_all_thermals via ChassisBase.get_all_psus
        for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_psus()))?)?.into_iter().enumerate() {
            if !call(get(&o0, |o| o.get_presence()))?.truthy() {
                continue;
            }
            let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "PSU {i}", "", i0).py_str();
            let k0: String = format!("psus[{}]", i0);
            for (i, dev) in iter(call(get(&o0, |o| o.get_all_thermals()))?)?.into_iter().enumerate() {
                out.push(self.row_thermal_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/thermals[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone())), ("kind", PyVal::Str("psu".to_string()))], cols, skip)?);
            }
        }
        // PdbBase.get_all_thermals via ChassisBase.get_all_pdbs
        // try: ... except NotImplementedError: pass -- rows already
        // collected stay collected.
        let r: PyResult<()> = (|| {
            for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_pdbs()))?)?.into_iter().enumerate() {
                if !default(call(get(&o0, |o| o.get_presence()))?, PyVal::Bool(true)).truthy() {
                    continue;
                }
                let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "PDB {i}", "", i0).py_str();
                let k0: String = format!("pdbs[{}]", i0);
                for (i, dev) in iter(call(get(&o0, |o| o.get_all_thermals()))?)?.into_iter().enumerate() {
                    out.push(self.row_thermal_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/thermals[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone())), ("kind", PyVal::Str("pdb".to_string()))], cols, skip)?);
                }
            }
            Ok(())
        })();
        match r {
            Err(e) if e.exc == Exc::NotImplementedError => {}
            other => other?,
        }
        // ModuleBase.get_all_thermals via ChassisBase.get_all_modules
        if call(get(&self.chassis, |o| o.is_modular_chassis()))?.truthy() {
            for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_modules()))?)?.into_iter().enumerate() {
                let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "Module {i}", "", i0).py_str();
                let k0: String = format!("modules[{}]", i0);
                for (i, dev) in iter(call(get(&o0, |o| o.get_all_thermals()))?)?.into_iter().enumerate() {
                    out.push(self.row_thermal_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/thermals[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone())), ("kind", PyVal::Str("module".to_string()))], cols, skip)?);
                }
            }
        }
        // PsuBase.get_all_thermals via ChassisBase.get_all_modules -> ModuleBase.get_all_psus
        if call(get(&self.chassis, |o| o.is_modular_chassis()))?.truthy() {
            for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_modules()))?)?.into_iter().enumerate() {
                let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "Module {i}", "", i0).py_str();
                let k0: String = format!("modules[{}]", i0);
                for (i1, o1) in iter(call(get(&o0, |o| o.get_all_psus()))?)?.into_iter().enumerate() {
                    if !call(get(&o1, |o| o.get_presence()))?.truthy() {
                        continue;
                    }
                    let p1: String = fmt_name(&call(get(&o1, |o| o.get_name()))?, "{parent} PSU {i}", &p0, i1).py_str();
                    let k1: String = format!("{}/psus[{}]", k0, i1);
                    for (i, dev) in iter(call(get(&o1, |o| o.get_all_thermals()))?)?.into_iter().enumerate() {
                        out.push(self.row_thermal_info(&dev, &p1, i, &[("key", PyVal::Str(format!("{}/thermals[{}]", k1, i))), ("parent_key", PyVal::Str(k1.clone())), ("kind", PyVal::Str("module_psu".to_string()))], cols, skip)?);
                    }
                }
            }
        }
        Ok(out)
    }

    #[allow(unused_variables)]
    fn row_fan_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)], cols: u64, absorb: bool) -> PyResult<PyFanInfo> {
        let mut row = PyFanInfo {
            name: fmt_name(&PyVal::None, "{parent} fan {i}", parent, i),
            kind: fixed_get(fixed, "kind")?,
            parent_name: PyVal::Str(parent.to_string()),
            key: fixed_get(fixed, "key")?,
            parent_key: fixed_get(fixed, "parent_key")?,
            drawer_name: fixed_get(fixed, "drawer_name")?,
            position_in_parent: PyVal::None,
            is_replaceable: PyVal::Bool(false),
            presence: PyVal::Bool(false),
            speed_pct: PyVal::None,
            target_speed_pct: PyVal::None,
            is_under_speed: PyVal::None,
            is_over_speed: PyVal::None,
            status: PyVal::Bool(false),
            direction: PyVal::None,
            model: PyVal::None,
            serial: PyVal::None,
            status_led: PyVal::None,
            error: PyVal::None,
            error_repr: PyVal::None,
            error_column: PyVal::None,
        };
        if absorb {
            // Each getter in a `try` of its own: an exception is that column
            // absent, as psud's `try_get` makes it.
            row.name = match (|| -> PyResult<PyVal> { Ok(fmt_name(&text(call(get(dev, |o| o.get_name()))?), "{parent} fan {i}", parent, i)) })() {
                Ok(v) => v,
                Err(_) => fmt_name(&PyVal::None, "{parent} fan {i}", parent, i),
            };
            row.position_in_parent = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 0) != 0 { call(get(dev, |o| o.get_position_in_parent()))? } else { PyVal::None }) })() {
                Ok(v) => v,
                Err(_) => PyVal::None,
            };
            row.is_replaceable = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 1) != 0 { default(call(get(dev, |o| o.is_replaceable()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) }) })() {
                Ok(v) => v,
                Err(_) => PyVal::Bool(false),
            };
            row.presence = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 2) != 0 { default(call(get(dev, |o| o.get_presence()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) }) })() {
                Ok(v) => v,
                Err(_) => PyVal::Bool(false),
            };
            row.speed_pct = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 3) != 0 { scalar(call(get(dev, |o| o.get_speed()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
                Ok(v) => v,
                Err(_) => PyVal::None,
            };
            row.target_speed_pct = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 4) != 0 { scalar(call(get(dev, |o| o.get_target_speed()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
                Ok(v) => v,
                Err(_) => PyVal::None,
            };
            row.is_under_speed = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 5) != 0 { call(get(dev, |o| o.is_under_speed()))? } else { PyVal::None }) })() {
                Ok(v) => v,
                Err(_) => PyVal::None,
            };
            row.is_over_speed = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 6) != 0 { call(get(dev, |o| o.is_over_speed()))? } else { PyVal::None }) })() {
                Ok(v) => v,
                Err(_) => PyVal::None,
            };
            row.status = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 7) != 0 { default(call(get(dev, |o| o.get_status()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) }) })() {
                Ok(v) => v,
                Err(_) => PyVal::Bool(false),
            };
            row.direction = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 8) != 0 { text(call(get(dev, |o| o.get_direction()))?) } else { PyVal::None }) })() {
                Ok(v) => v,
                Err(_) => PyVal::None,
            };
            row.model = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 9) != 0 { text(call(get(dev, |o| o.get_model()))?) } else { PyVal::None }) })() {
                Ok(v) => v,
                Err(_) => PyVal::None,
            };
            row.serial = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 10) != 0 { text(call(get(dev, |o| o.get_serial()))?) } else { PyVal::None }) })() {
                Ok(v) => v,
                Err(_) => PyVal::None,
            };
            row.status_led = match (|| -> PyResult<PyVal> { Ok(if cols & (1 << 11) != 0 { text(call(get(dev, |o| o.get_status_led()))?) } else { PyVal::None }) })() {
                Ok(v) => v,
                Err(_) => PyVal::None,
            };
        } else {
            // try: ... except Exception as e -- the first getter that raises
            // ends the reading, and the row is still a row; `column` is the
            // one being read when it struck.
            let mut column = "";
            let r: PyResult<()> = (|| {
                column = "name";
                row.name = fmt_name(&text(call(get(dev, |o| o.get_name()))?), "{parent} fan {i}", parent, i);
                column = "position_in_parent";
                row.position_in_parent = if cols & (1 << 0) != 0 { call(get(dev, |o| o.get_position_in_parent()))? } else { PyVal::None };
                column = "is_replaceable";
                row.is_replaceable = if cols & (1 << 1) != 0 { default(call(get(dev, |o| o.is_replaceable()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) };
                column = "presence";
                row.presence = if cols & (1 << 2) != 0 { default(call(get(dev, |o| o.get_presence()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) };
                column = "speed_pct";
                row.speed_pct = if row.presence.truthy() { if cols & (1 << 3) != 0 { scalar(call(get(dev, |o| o.get_speed()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None } } else { PyVal::None };
                column = "target_speed_pct";
                row.target_speed_pct = if row.presence.truthy() { if cols & (1 << 4) != 0 { scalar(call(get(dev, |o| o.get_target_speed()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None } } else { PyVal::None };
                column = "is_under_speed";
                row.is_under_speed = if row.presence.truthy() { if cols & (1 << 5) != 0 { call(get(dev, |o| o.is_under_speed()))? } else { PyVal::None } } else { PyVal::None };
                column = "is_over_speed";
                row.is_over_speed = if row.presence.truthy() { if cols & (1 << 6) != 0 { call(get(dev, |o| o.is_over_speed()))? } else { PyVal::None } } else { PyVal::None };
                column = "status";
                row.status = if row.presence.truthy() { if cols & (1 << 7) != 0 { default(call(get(dev, |o| o.get_status()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) } } else { PyVal::Bool(false) };
                column = "direction";
                row.direction = if row.presence.truthy() { if cols & (1 << 8) != 0 { text(call(get(dev, |o| o.get_direction()))?) } else { PyVal::None } } else { PyVal::None };
                column = "model";
                row.model = if cols & (1 << 9) != 0 { text(call(get(dev, |o| o.get_model()))?) } else { PyVal::None };
                column = "serial";
                row.serial = if cols & (1 << 10) != 0 { text(call(get(dev, |o| o.get_serial()))?) } else { PyVal::None };
                column = "status_led";
                row.status_led = if cols & (1 << 11) != 0 { text(call(get(dev, |o| o.get_status_led()))?) } else { PyVal::None };
                Ok(())
            })();
            if let Err(e) = r {
                row.error = PyVal::Str(e.str());
                row.error_repr = PyVal::Str(e.repr());
                row.error_column = PyVal::Str(column.to_string());
            }
        }
        Ok(row)
    }

    /// Every FanInfo, in declared order: `_walk_fan_info`.
    fn walk_fan_info(&self, cols: u64, absorb: bool) -> PyResult<Vec<PyFanInfo>> {
        let mut out = Vec::new();
        // FanDrawerBase.get_all_fans via ChassisBase.get_all_fan_drawers
        for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_fan_drawers()))?)?.into_iter().enumerate() {
            let r0 = call(get(&o0, |o| o.get_name()))?;
            let p0: String = fmt_name(&present(&r0, &["N/A"]), "chassis 1", "", i0).py_str();
            let k0: String = format!("fan_drawers[{}]", i0);
            for (i, dev) in iter(call(get(&o0, |o| o.get_all_fans()))?)?.into_iter().enumerate() {
                out.push(self.row_fan_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/fans[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone())), ("kind", PyVal::Str("drawer".to_string())), ("drawer_name", raw(&r0))], cols, absorb)?);
            }
        }
        // ModuleBase.get_all_fans via ChassisBase.get_all_modules
        for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_modules()))?)?.into_iter().enumerate() {
            let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "Module {i}", "", i0).py_str();
            let k0: String = format!("modules[{}]", i0);
            for (i, dev) in iter(call(get(&o0, |o| o.get_all_fans()))?)?.into_iter().enumerate() {
                out.push(self.row_fan_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/fans[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone())), ("kind", PyVal::Str("module".to_string())), ("drawer_name", PyVal::Str("N/A".to_string()))], cols, absorb)?);
            }
        }
        // PsuBase.get_all_fans via ChassisBase.get_all_psus
        for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_psus()))?)?.into_iter().enumerate() {
            let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "PSU {i}", "", i0).py_str();
            let k0: String = format!("psus[{}]", i0);
            for (i, dev) in iter(call(get(&o0, |o| o.get_all_fans()))?)?.into_iter().enumerate() {
                out.push(self.row_fan_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/fans[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone())), ("kind", PyVal::Str("psu".to_string())), ("drawer_name", PyVal::Str("N/A".to_string()))], cols, absorb)?);
            }
        }
        // PsuBase.get_all_fans via ChassisBase.get_all_pdbs
        for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_pdbs()))?)?.into_iter().enumerate() {
            let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "PDB {i}", "", i0).py_str();
            let k0: String = format!("pdbs[{}]", i0);
            for (i, dev) in iter(call(get(&o0, |o| o.get_all_fans()))?)?.into_iter().enumerate() {
                out.push(self.row_fan_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/fans[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone())), ("kind", PyVal::Str("pdb".to_string())), ("drawer_name", PyVal::Str("N/A".to_string()))], cols, absorb)?);
            }
        }
        Ok(out)
    }

    /// The device at a published FanInfo key: `_find_fan_info`.
    fn find_fan_info(&self, key: &str) -> PyResult<PyVal> {
        let path = parse_key(key)?;
        // FanDrawerBase.get_all_fans via ChassisBase.get_all_fan_drawers
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("fan_drawers", true), ("fans", true)] {
                return Ok(None);
            }
            let Some(o0) = nth(call(get(&self.chassis, |o| o.get_all_fan_drawers()))?, path[0].1)? else {
                return Ok(None);
            };
            nth(call(get(&o0, |o| o.get_all_fans()))?, path[1].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // ModuleBase.get_all_fans via ChassisBase.get_all_modules
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("modules", true), ("fans", true)] {
                return Ok(None);
            }
            let Some(o0) = nth(call(get(&self.chassis, |o| o.get_all_modules()))?, path[0].1)? else {
                return Ok(None);
            };
            nth(call(get(&o0, |o| o.get_all_fans()))?, path[1].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // PsuBase.get_all_fans via ChassisBase.get_all_psus
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("psus", true), ("fans", true)] {
                return Ok(None);
            }
            let Some(o0) = nth(call(get(&self.chassis, |o| o.get_all_psus()))?, path[0].1)? else {
                return Ok(None);
            };
            nth(call(get(&o0, |o| o.get_all_fans()))?, path[1].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // PsuBase.get_all_fans via ChassisBase.get_all_pdbs
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("pdbs", true), ("fans", true)] {
                return Ok(None);
            }
            let Some(o0) = nth(call(get(&self.chassis, |o| o.get_all_pdbs()))?, path[0].1)? else {
                return Ok(None);
            };
            nth(call(get(&o0, |o| o.get_all_fans()))?, path[1].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        Err(not_found("FanInfo", key))
    }

    #[allow(unused_variables)]
    fn row_fan_drawer_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)], cols: u64) -> PyResult<PyFanDrawerInfo> {
        Ok(PyFanDrawerInfo {
            name: default(text(call(get(dev, |o| o.get_name()))?), PyVal::Str("N/A".to_string())),
            key: fixed_get(fixed, "key")?,
            position_in_parent: if cols & (1 << 0) != 0 { call(get(dev, |o| o.get_position_in_parent()))? } else { PyVal::None },
            presence: if cols & (1 << 1) != 0 { default(call(get(dev, |o| o.get_presence()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) },
            status: if cols & (1 << 2) != 0 { call(get(dev, |o| o.get_status()))? } else { PyVal::None },
            is_replaceable: if cols & (1 << 3) != 0 { default(call(get(dev, |o| o.is_replaceable()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) },
            model: if cols & (1 << 4) != 0 { text(call(get(dev, |o| o.get_model()))?) } else { PyVal::None },
            serial: if cols & (1 << 5) != 0 { text(call(get(dev, |o| o.get_serial()))?) } else { PyVal::None },
            status_led: if cols & (1 << 6) != 0 { text(call(get(dev, |o| o.get_status_led()))?) } else { PyVal::None },
            maximum_consumed_power: if cols & (1 << 7) != 0 { scalar(call(get(dev, |o| o.get_maximum_consumed_power()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None },
        })
    }

    /// Every FanDrawerInfo, in declared order: `_walk_fan_drawer_info`.
    fn walk_fan_drawer_info(&self, cols: u64) -> PyResult<Vec<PyFanDrawerInfo>> {
        let mut out = Vec::new();
        // ChassisBase.get_all_fan_drawers
        for (i, dev) in iter(call(get(&self.chassis, |o| o.get_all_fan_drawers()))?)?.into_iter().enumerate() {
            out.push(self.row_fan_drawer_info(&dev, "chassis 1", i, &[("key", PyVal::Str(format!("fan_drawers[{}]", i))), ("parent_key", PyVal::None)], cols)?);
        }
        Ok(out)
    }

    /// The device at a published FanDrawerInfo key: `_find_fan_drawer_info`.
    fn find_fan_drawer_info(&self, key: &str) -> PyResult<PyVal> {
        let path = parse_key(key)?;
        // ChassisBase.get_all_fan_drawers
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("fan_drawers", true)] {
                return Ok(None);
            }
            nth(call(get(&self.chassis, |o| o.get_all_fan_drawers()))?, path[0].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        Err(not_found("FanDrawerInfo", key))
    }

    #[allow(unused_variables)]
    fn row_psu_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)]) -> PyResult<PyPsuInfo> {
        let mut row = PyPsuInfo {
            name: fmt_name(&PyVal::None, "{parent}", parent, i),
            kind: fixed_get(fixed, "kind")?,
            key: fixed_get(fixed, "key")?,
            position_in_parent: PyVal::None,
            presence: PyVal::Bool(false),
            is_replaceable: PyVal::Bool(false),
            model: PyVal::None,
            serial: PyVal::None,
            revision: PyVal::None,
            power_good: PyVal::Bool(false),
            status_led: PyVal::None,
            voltage: PyVal::None,
            current: PyVal::None,
            power: PyVal::None,
            input_voltage: PyVal::None,
            input_current: PyVal::None,
            input_power: PyVal::None,
            temperature: PyVal::None,
            temperature_high_threshold: PyVal::None,
            voltage_high_threshold: PyVal::None,
            voltage_low_threshold: PyVal::None,
            maximum_supplied_power: PyVal::None,
            power_warning_suppress_threshold: PyVal::None,
            power_critical_threshold: PyVal::None,
        };
        // Each getter in a `try` of its own: an exception is that column
        // absent, as psud's `try_get` makes it.
        row.name = match (|| -> PyResult<PyVal> { Ok(fmt_name(&text(call(get(dev, |o| o.get_name()))?), "{parent}", parent, i)) })() {
            Ok(v) => v,
            Err(_) => fmt_name(&PyVal::None, "{parent}", parent, i),
        };
        row.position_in_parent = match (|| -> PyResult<PyVal> { Ok(call(get(dev, |o| o.get_position_in_parent()))?) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.presence = match (|| -> PyResult<PyVal> { Ok(default(call(get(dev, |o| o.get_presence()))?, PyVal::Bool(false))) })() {
            Ok(v) => v,
            Err(_) => PyVal::Bool(false),
        };
        row.is_replaceable = match (|| -> PyResult<PyVal> { Ok(default(call(get(dev, |o| o.is_replaceable()))?, PyVal::Bool(false))) })() {
            Ok(v) => v,
            Err(_) => PyVal::Bool(false),
        };
        row.model = match (|| -> PyResult<PyVal> { Ok(text(call(get(dev, |o| o.get_model()))?)) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.serial = match (|| -> PyResult<PyVal> { Ok(text(call(get(dev, |o| o.get_serial()))?)) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.revision = match (|| -> PyResult<PyVal> { Ok(text(call(get(dev, |o| o.get_revision()))?)) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.power_good = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { default(call(get(dev, |o| o.get_powergood_status()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) }) })() {
            Ok(v) => v,
            Err(_) => PyVal::Bool(false),
        };
        row.status_led = match (|| -> PyResult<PyVal> { Ok(text(call(get(dev, |o| o.get_status_led()))?)) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.voltage = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_voltage()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.current = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_current()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.power = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_power()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.input_voltage = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_input_voltage()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.input_current = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_input_current()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.input_power = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_input_power()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.temperature = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_temperature()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.temperature_high_threshold = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_temperature_high_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.voltage_high_threshold = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_voltage_high_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.voltage_low_threshold = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_voltage_low_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.maximum_supplied_power = match (|| -> PyResult<PyVal> { Ok(if row.presence.truthy() { scalar(call(get(dev, |o| o.get_maximum_supplied_power()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None }) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.power_warning_suppress_threshold = match (|| -> PyResult<PyVal> { Ok(scalar(call(get(dev, |o| o.get_psu_power_warning_suppress_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])?) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        row.power_critical_threshold = match (|| -> PyResult<PyVal> { Ok(scalar(call(get(dev, |o| o.get_psu_power_critical_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])?) })() {
            Ok(v) => v,
            Err(_) => PyVal::None,
        };
        Ok(row)
    }

    /// Every PsuInfo, in declared order: `_walk_psu_info`.
    fn walk_psu_info(&self) -> PyResult<Vec<PyPsuInfo>> {
        let mut out = Vec::new();
        // ChassisBase.get_all_psus
        for (i, dev) in iter(call(get(&self.chassis, |o| o.get_all_psus()))?)?.into_iter().enumerate() {
            out.push(self.row_psu_info(&dev, &fmt_name(&PyVal::None, "PSU {i}", "", i).py_str(), i, &[("key", PyVal::Str(format!("psus[{}]", i))), ("parent_key", PyVal::None), ("kind", PyVal::Str("psu".to_string()))])?);
        }
        // ChassisBase.get_all_pdbs
        // try: ... except NotImplementedError: pass -- rows already
        // collected stay collected.
        let r: PyResult<()> = (|| {
            for (i, dev) in iter(call(get(&self.chassis, |o| o.get_all_pdbs()))?)?.into_iter().enumerate() {
                out.push(self.row_psu_info(&dev, &fmt_name(&PyVal::None, "PDB {i}", "", i).py_str(), i, &[("key", PyVal::Str(format!("pdbs[{}]", i))), ("parent_key", PyVal::None), ("kind", PyVal::Str("pdb".to_string()))])?);
            }
            Ok(())
        })();
        match r {
            Err(e) if e.exc == Exc::NotImplementedError => {}
            other => other?,
        }
        Ok(out)
    }

    /// The device at a published PsuInfo key: `_find_psu_info`.
    fn find_psu_info(&self, key: &str) -> PyResult<PyVal> {
        let path = parse_key(key)?;
        // ChassisBase.get_all_psus
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("psus", true)] {
                return Ok(None);
            }
            nth(call(get(&self.chassis, |o| o.get_all_psus()))?, path[0].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // ChassisBase.get_all_pdbs
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("pdbs", true)] {
                return Ok(None);
            }
            nth(call(get(&self.chassis, |o| o.get_all_pdbs()))?, path[0].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) if e.exc == Exc::NotImplementedError => {}
            Err(e) => return Err(e),
        }
        Err(not_found("PsuInfo", key))
    }

    #[allow(unused_variables)]
    fn row_chassis_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)], cols: u64) -> PyResult<PyChassisInfo> {
        let _shared0 = if cols & 12288 != 0 { call(get(dev, |o| o.get_reboot_cause()))? } else { PyVal::None };
        Ok(PyChassisInfo {
            name: if cols & (1 << 0) != 0 { default(text(call(get(dev, |o| o.get_name()))?), PyVal::Str("chassis 1".to_string())) } else { PyVal::Str("chassis 1".to_string()) },
            presence: if cols & (1 << 1) != 0 { default(call(get(dev, |o| o.get_presence()))?, PyVal::Bool(true)) } else { PyVal::Bool(true) },
            model: if cols & (1 << 2) != 0 { text(call(get(dev, |o| o.get_model()))?) } else { PyVal::None },
            serial: if cols & (1 << 3) != 0 { text(call(get(dev, |o| o.get_serial()))?) } else { PyVal::None },
            revision: if cols & (1 << 4) != 0 { text(call(get(dev, |o| o.get_revision()))?) } else { PyVal::None },
            status: if cols & (1 << 5) != 0 { call(get(dev, |o| o.get_status()))? } else { PyVal::None },
            base_mac: if cols & (1 << 6) != 0 { text(call(get(dev, |o| o.get_base_mac()))?) } else { PyVal::None },
            is_modular_chassis: if cols & (1 << 7) != 0 { default(call(get(dev, |o| o.is_modular_chassis()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) },
            is_smartswitch: if cols & (1 << 8) != 0 { default(call(get(dev, |o| o.is_smartswitch()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) },
            is_dpu: if cols & (1 << 9) != 0 { default(call(get(dev, |o| o.is_dpu()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) },
            is_bmc: if cols & (1 << 10) != 0 { default(call(get(dev, |o| o.is_bmc()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) },
            is_liquid_cooled: if cols & (1 << 11) != 0 { default(call(get(dev, |o| o.is_liquid_cooled()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) },
            reboot_cause: if cols & (1 << 12) != 0 { text(at(&_shared0.clone(), 0)) } else { PyVal::None },
            reboot_cause_detail: if cols & (1 << 13) != 0 { text(at(&_shared0.clone(), 1)) } else { PyVal::None },
            my_slot: if cols & (1 << 14) != 0 { scalar(call(get(dev, |o| o.get_my_slot()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None },
            supervisor_slot: if cols & (1 << 15) != 0 { scalar(call(get(dev, |o| o.get_supervisor_slot()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None },
            dpu_id: if cols & (1 << 16) != 0 { scalar(call_narrowed(get(dev, |o| o.get_dpu_id()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None },
            dataplane_state: if cols & (1 << 17) != 0 { call(get(dev, |o| o.get_dataplane_state()))? } else { PyVal::None },
            controlplane_state: if cols & (1 << 18) != 0 { call(get(dev, |o| o.get_controlplane_state()))? } else { PyVal::None },
            status_led: if cols & (1 << 19) != 0 { text(call(get(dev, |o| o.get_status_led()))?) } else { PyVal::None },
        })
    }

    /// Every ChassisInfo, in declared order: `_walk_chassis_info`.
    fn walk_chassis_info(&self, cols: u64) -> PyResult<Vec<PyChassisInfo>> {
        let mut out = Vec::new();
        out.push(self.row_chassis_info(&self.chassis, "chassis 1", 0, &[], cols)?);
        Ok(out)
    }

    #[allow(unused_variables)]
    fn row_module_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)], cols: u64) -> PyResult<PyModuleInfo> {
        Ok(PyModuleInfo {
            name: fmt_name(&text(call(get(dev, |o| o.get_name()))?), "Module {i}", parent, i),
            parent_name: PyVal::Str(parent.to_string()),
            key: fixed_get(fixed, "key")?,
            parent_key: fixed_get(fixed, "parent_key")?,
            position_in_parent: if cols & (1 << 0) != 0 { call(get(dev, |o| o.get_position_in_parent()))? } else { PyVal::None },
            presence: if cols & (1 << 1) != 0 { default(call(get(dev, |o| o.get_presence()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) },
            status: if cols & (1 << 2) != 0 { call(get(dev, |o| o.get_status()))? } else { PyVal::None },
            is_replaceable: if cols & (1 << 3) != 0 { default(call(get(dev, |o| o.is_replaceable()))?, PyVal::Bool(false)) } else { PyVal::Bool(false) },
            model: if cols & (1 << 4) != 0 { text(call(get(dev, |o| o.get_model()))?) } else { PyVal::None },
            serial: if cols & (1 << 5) != 0 { text(call(get(dev, |o| o.get_serial()))?) } else { PyVal::None },
            description: if cols & (1 << 6) != 0 { text(call(get(dev, |o| o.get_description()))?) } else { PyVal::None },
            slot: if cols & (1 << 7) != 0 { scalar(call(get(dev, |o| o.get_slot()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None },
            r#type: if cols & (1 << 8) != 0 { text(call(get(dev, |o| o.get_type()))?) } else { PyVal::None },
            oper_status: if cols & (1 << 9) != 0 { text(call(get(dev, |o| o.get_oper_status()))?) } else { PyVal::None },
            base_mac: if cols & (1 << 10) != 0 { text(call(get(dev, |o| o.get_base_mac()))?) } else { PyVal::None },
            dpu_id: if cols & (1 << 11) != 0 { scalar(call(get(dev, |o| o.get_dpu_id()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None },
            maximum_consumed_power: if cols & (1 << 12) != 0 { scalar(call(get(dev, |o| o.get_maximum_consumed_power()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None },
            midplane_ip: if cols & (1 << 13) != 0 { text(call(get(dev, |o| o.get_midplane_ip()))?) } else { PyVal::None },
            is_midplane_reachable: if cols & (1 << 14) != 0 { call(get(dev, |o| o.is_midplane_reachable()))? } else { PyVal::None },
            state_transition: if cols & (1 << 15) != 0 { call_with_name(dev, |o| o.get_name(), |o, n| o.get_module_state_transition(n))? } else { PyVal::None },
        })
    }

    /// Every ModuleInfo, in declared order: `_walk_module_info`.
    fn walk_module_info(&self, cols: u64) -> PyResult<Vec<PyModuleInfo>> {
        let mut out = Vec::new();
        // ChassisBase.get_all_modules
        for (i, dev) in iter(call(get(&self.chassis, |o| o.get_all_modules()))?)?.into_iter().enumerate() {
            out.push(self.row_module_info(&dev, "chassis 1", i, &[("key", PyVal::Str(format!("modules[{}]", i))), ("parent_key", PyVal::None)], cols)?);
        }
        Ok(out)
    }

    /// The device at a published ModuleInfo key: `_find_module_info`.
    fn find_module_info(&self, key: &str) -> PyResult<PyVal> {
        let path = parse_key(key)?;
        // ChassisBase.get_all_modules
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("modules", true)] {
                return Ok(None);
            }
            nth(call(get(&self.chassis, |o| o.get_all_modules()))?, path[0].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        Err(not_found("ModuleInfo", key))
    }

    #[allow(unused_variables)]
    fn row_component_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)]) -> PyResult<PyComponentInfo> {
        Ok(PyComponentInfo {
            name: fmt_name(&text(call(get(dev, |o| o.get_name()))?), "{parent} component {i}", parent, i),
            parent_name: PyVal::Str(parent.to_string()),
            key: fixed_get(fixed, "key")?,
            parent_key: fixed_get(fixed, "parent_key")?,
            description: text(call(get(dev, |o| o.get_description()))?),
            firmware_version: text(call(get(dev, |o| o.get_firmware_version()))?),
        })
    }

    /// Every ComponentInfo, in declared order: `_walk_component_info`.
    fn walk_component_info(&self) -> PyResult<Vec<PyComponentInfo>> {
        let mut out = Vec::new();
        // ChassisBase.get_all_components
        for (i, dev) in iter(call(get(&self.chassis, |o| o.get_all_components()))?)?.into_iter().enumerate() {
            out.push(self.row_component_info(&dev, "chassis 1", i, &[("key", PyVal::Str(format!("components[{}]", i))), ("parent_key", PyVal::None)])?);
        }
        // ModuleBase.get_all_components via ChassisBase.get_all_modules
        if call(get(&self.chassis, |o| o.is_modular_chassis()))?.truthy() {
            for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_modules()))?)?.into_iter().enumerate() {
                let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "Module {i}", "", i0).py_str();
                let k0: String = format!("modules[{}]", i0);
                for (i, dev) in iter(call(get(&o0, |o| o.get_all_components()))?)?.into_iter().enumerate() {
                    out.push(self.row_component_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/components[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone()))])?);
                }
            }
        }
        Ok(out)
    }

    /// The device at a published ComponentInfo key: `_find_component_info`.
    fn find_component_info(&self, key: &str) -> PyResult<PyVal> {
        let path = parse_key(key)?;
        // ChassisBase.get_all_components
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("components", true)] {
                return Ok(None);
            }
            nth(call(get(&self.chassis, |o| o.get_all_components()))?, path[0].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // ModuleBase.get_all_components via ChassisBase.get_all_modules
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("modules", true), ("components", true)] {
                return Ok(None);
            }
            if !call(get(&self.chassis, |o| o.is_modular_chassis()))?.truthy() {
                return Ok(None);
            }
            let Some(o0) = nth(call(get(&self.chassis, |o| o.get_all_modules()))?, path[0].1)? else {
                return Ok(None);
            };
            nth(call(get(&o0, |o| o.get_all_components()))?, path[1].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        Err(not_found("ComponentInfo", key))
    }

    #[allow(unused_variables)]
    fn row_sensor_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)]) -> PyResult<PySensorInfo> {
        let mut row = PySensorInfo {
            name: fmt_name_with(&PyVal::None, "{parent} {kind}_sensor {i}", parent, i, fixed, &["kind"])?,
            kind: fixed_get(fixed, "kind")?,
            parent_name: PyVal::Str(parent.to_string()),
            key: fixed_get(fixed, "key")?,
            parent_key: fixed_get(fixed, "parent_key")?,
            position_in_parent: PyVal::None,
            value: PyVal::None,
            is_replaceable: PyVal::Bool(false),
            unit: PyVal::None,
            min_recorded: PyVal::None,
            max_recorded: PyVal::None,
            high_threshold: PyVal::None,
            low_threshold: PyVal::None,
            high_critical_threshold: PyVal::None,
            low_critical_threshold: PyVal::None,
            error: PyVal::None,
            error_repr: PyVal::None,
            error_column: PyVal::None,
        };
        // try: ... except Exception as e -- the first getter that raises
        // ends the reading, and the row is still a row; `column` is the
        // one being read when it struck.
        let mut column = "";
        let r: PyResult<()> = (|| {
            column = "name";
            row.name = fmt_name_with(&text(call(get(dev, |o| o.get_name()))?), "{parent} {kind}_sensor {i}", parent, i, fixed, &["kind"])?;
            column = "position_in_parent";
            row.position_in_parent = call(get(dev, |o| o.get_position_in_parent()))?;
            column = "value";
            row.value = scalar(call(get(dev, |o| o.get_value()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])?;
            column = "is_replaceable";
            row.is_replaceable = default(call(get(dev, |o| o.is_replaceable()))?, PyVal::Bool(false));
            column = "unit";
            row.unit = if !row.value.is_none() { text(call(get(dev, |o| o.get_unit()))?) } else { PyVal::None };
            column = "min_recorded";
            row.min_recorded = if !row.value.is_none() { scalar(call(get(dev, |o| o.get_minimum_recorded()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None };
            column = "max_recorded";
            row.max_recorded = if !row.value.is_none() { scalar(call(get(dev, |o| o.get_maximum_recorded()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None };
            column = "high_threshold";
            row.high_threshold = if !row.value.is_none() { scalar(call(get(dev, |o| o.get_high_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None };
            column = "low_threshold";
            row.low_threshold = if !row.value.is_none() { scalar(call(get(dev, |o| o.get_low_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None };
            column = "high_critical_threshold";
            row.high_critical_threshold = if !row.value.is_none() { scalar(call(get(dev, |o| o.get_high_critical_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None };
            column = "low_critical_threshold";
            row.low_critical_threshold = if !row.value.is_none() { scalar(call(get(dev, |o| o.get_low_critical_threshold()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])? } else { PyVal::None };
            Ok(())
        })();
        if let Err(e) = r {
            row.error = PyVal::Str(e.str());
            row.error_repr = PyVal::Str(e.repr());
            row.error_column = PyVal::Str(column.to_string());
        }
        Ok(row)
    }

    /// Every SensorInfo, in declared order: `_walk_sensor_info`.
    fn walk_sensor_info(&self) -> PyResult<Vec<PySensorInfo>> {
        let mut out = Vec::new();
        // EscapeHatches.voltage_sensors_from_yaml
        let s0 = out.len();
        for (i, dev) in iter(self.hatch.voltage_sensors_from_yaml()?)?.into_iter().enumerate() {
            out.push(self.row_sensor_info(&dev, "chassis 1", i, &[("key", PyVal::Str(format!("voltage_sensors_from_yaml[{}]", i))), ("parent_key", PyVal::None), ("kind", PyVal::Str("voltage".to_string()))])?);
        }
        // ChassisBase.get_all_voltage_sensors
        let n = out.len() - s0;
        for (i, dev) in iter(call(get(&self.chassis, |o| o.get_all_voltage_sensors()))?)?.into_iter().enumerate() {
            out.push(self.row_sensor_info(&dev, "chassis 1", n + i, &[("key", PyVal::Str(format!("voltage_sensors[{}]", i))), ("parent_key", PyVal::None), ("kind", PyVal::Str("voltage".to_string()))])?);
        }
        // ModuleBase.get_all_voltage_sensors via ChassisBase.get_all_modules
        if call(get(&self.chassis, |o| o.is_modular_chassis()))?.truthy() {
            for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_modules()))?)?.into_iter().enumerate() {
                let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "Module {i}", "", i0).py_str();
                let k0: String = format!("modules[{}]", i0);
                for (i, dev) in iter(call(get(&o0, |o| o.get_all_voltage_sensors()))?)?.into_iter().enumerate() {
                    out.push(self.row_sensor_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/voltage_sensors[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone())), ("kind", PyVal::Str("voltage".to_string()))])?);
                }
            }
        }
        // EscapeHatches.current_sensors_from_yaml
        let s3 = out.len();
        for (i, dev) in iter(self.hatch.current_sensors_from_yaml()?)?.into_iter().enumerate() {
            out.push(self.row_sensor_info(&dev, "chassis 1", i, &[("key", PyVal::Str(format!("current_sensors_from_yaml[{}]", i))), ("parent_key", PyVal::None), ("kind", PyVal::Str("current".to_string()))])?);
        }
        // ChassisBase.get_all_current_sensors
        let n = out.len() - s3;
        for (i, dev) in iter(call(get(&self.chassis, |o| o.get_all_current_sensors()))?)?.into_iter().enumerate() {
            out.push(self.row_sensor_info(&dev, "chassis 1", n + i, &[("key", PyVal::Str(format!("current_sensors[{}]", i))), ("parent_key", PyVal::None), ("kind", PyVal::Str("current".to_string()))])?);
        }
        // ModuleBase.get_all_current_sensors via ChassisBase.get_all_modules
        if call(get(&self.chassis, |o| o.is_modular_chassis()))?.truthy() {
            for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_modules()))?)?.into_iter().enumerate() {
                let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "Module {i}", "", i0).py_str();
                let k0: String = format!("modules[{}]", i0);
                for (i, dev) in iter(call(get(&o0, |o| o.get_all_current_sensors()))?)?.into_iter().enumerate() {
                    out.push(self.row_sensor_info(&dev, &p0, i, &[("key", PyVal::Str(format!("{}/current_sensors[{}]", k0, i))), ("parent_key", PyVal::Str(k0.clone())), ("kind", PyVal::Str("current".to_string()))])?);
                }
            }
        }
        Ok(out)
    }

    /// The device at a published SensorInfo key: `_find_sensor_info`.
    fn find_sensor_info(&self, key: &str) -> PyResult<PyVal> {
        let path = parse_key(key)?;
        // EscapeHatches.voltage_sensors_from_yaml
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("voltage_sensors_from_yaml", true)] {
                return Ok(None);
            }
            nth(self.hatch.voltage_sensors_from_yaml()?, path[0].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // ChassisBase.get_all_voltage_sensors
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("voltage_sensors", true)] {
                return Ok(None);
            }
            nth(call(get(&self.chassis, |o| o.get_all_voltage_sensors()))?, path[0].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // ModuleBase.get_all_voltage_sensors via ChassisBase.get_all_modules
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("modules", true), ("voltage_sensors", true)] {
                return Ok(None);
            }
            if !call(get(&self.chassis, |o| o.is_modular_chassis()))?.truthy() {
                return Ok(None);
            }
            let Some(o0) = nth(call(get(&self.chassis, |o| o.get_all_modules()))?, path[0].1)? else {
                return Ok(None);
            };
            nth(call(get(&o0, |o| o.get_all_voltage_sensors()))?, path[1].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // EscapeHatches.current_sensors_from_yaml
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("current_sensors_from_yaml", true)] {
                return Ok(None);
            }
            nth(self.hatch.current_sensors_from_yaml()?, path[0].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // ChassisBase.get_all_current_sensors
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("current_sensors", true)] {
                return Ok(None);
            }
            nth(call(get(&self.chassis, |o| o.get_all_current_sensors()))?, path[0].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        // ModuleBase.get_all_current_sensors via ChassisBase.get_all_modules
        let found = (|| -> PyResult<Option<PyVal>> {
            if shape(&path) != [("modules", true), ("current_sensors", true)] {
                return Ok(None);
            }
            if !call(get(&self.chassis, |o| o.is_modular_chassis()))?.truthy() {
                return Ok(None);
            }
            let Some(o0) = nth(call(get(&self.chassis, |o| o.get_all_modules()))?, path[0].1)? else {
                return Ok(None);
            };
            nth(call(get(&o0, |o| o.get_all_current_sensors()))?, path[1].1)
        })();
        match found {
            Ok(Some(dev)) => return Ok(dev),
            Ok(None) => {}
            Err(e) => return Err(e),
        }
        Err(not_found("SensorInfo", key))
    }

    #[allow(unused_variables)]
    fn row_leak_profile(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)]) -> PyResult<PyLeakProfile> {
        Ok(PyLeakProfile {
            r#type: fmt_name(&text(call(get(dev, |o| o.get_type()))?), "profile {i}", parent, i),
            max_minor_duration_sec: scalar(call(get(dev, |o| o.get_leak_max_minor_duration_sec()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])?,
        })
    }

    /// Every LeakProfile, in declared order: `_walk_leak_profile`.
    fn walk_leak_profile(&self) -> PyResult<Vec<PyLeakProfile>> {
        let mut out = Vec::new();
        // LiquidCoolingBase.get_all_profiles via ChassisBase.get_liquid_cooling
        // try: ... except NotImplementedError: pass -- rows already
        // collected stay collected.
        let r: PyResult<()> = (|| {
            let o0 = call(get(&self.chassis, |o| o.get_liquid_cooling()))?;
            let i0: usize = 0;
            if !o0.is_none() {
                let p0: String = fmt_name(&PyVal::None, "chassis 1", "", i0).py_str();
                for (i, dev) in iter(call(get(&o0, |o| o.get_all_profiles()))?)?.into_iter().enumerate() {
                    out.push(self.row_leak_profile(&dev, &p0, i, &[])?);
                }
            }
            Ok(())
        })();
        match r {
            Err(e) if e.exc == Exc::NotImplementedError => {}
            other => other?,
        }
        Ok(out)
    }

    #[allow(unused_variables)]
    fn row_leak_sensor_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)]) -> PyResult<PyLeakSensorInfo> {
        Ok(PyLeakSensorInfo {
            name: fmt_name(&text(call(get(dev, |o| o.get_name()))?), "leakage{i}", parent, i),
            parent_name: PyVal::Str(parent.to_string()),
            sensor_type: text(call(get(dev, |o| o.get_leak_sensor_type()))?),
            location: text(call(get(dev, |o| o.get_leak_sensor_location()))?),
            is_leak: truthy(call(get(dev, |o| o.is_leak()))?),
            is_ok: call(get(dev, |o| o.is_leak_sensor_ok()))?,
            severity: text(call(get(dev, |o| o.get_leak_severity()))?),
            profile_type: text(call(get(&call(get(dev, |o| o.get_leak_profile()))?, |o| o.get_type()))?),
            profile_max_minor_duration_sec: scalar(call(get(&call(get(dev, |o| o.get_leak_profile()))?, |o| o.get_leak_max_minor_duration_sec()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])?,
        })
    }

    /// Every LeakSensorInfo, in declared order: `_walk_leak_sensor_info`.
    fn walk_leak_sensor_info(&self) -> PyResult<Vec<PyLeakSensorInfo>> {
        let mut out = Vec::new();
        // LiquidCoolingBase.get_all_leak_sensors via ChassisBase.get_liquid_cooling
        // try: ... except NotImplementedError: pass -- rows already
        // collected stay collected.
        let r: PyResult<()> = (|| {
            let o0 = call(get(&self.chassis, |o| o.get_liquid_cooling()))?;
            let i0: usize = 0;
            if !o0.is_none() {
                let p0: String = fmt_name(&PyVal::None, "chassis 1", "", i0).py_str();
                for (i, dev) in iter(call(get(&o0, |o| o.get_all_leak_sensors()))?)?.into_iter().enumerate() {
                    out.push(self.row_leak_sensor_info(&dev, &p0, i, &[])?);
                }
            }
            Ok(())
        })();
        match r {
            Err(e) if e.exc == Exc::NotImplementedError => {}
            other => other?,
        }
        Ok(out)
    }

    #[allow(unused_variables)]
    fn row_watchdog_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)]) -> PyResult<PyWatchdogInfo> {
        Ok(PyWatchdogInfo {
            is_armed: call(get(dev, |o| o.is_armed()))?,
            remaining_time: scalar(call(get(dev, |o| o.get_remaining_time()))?, &[PyVal::Str("N/A".to_string())], &["int", "str"])?,
        })
    }

    /// Every WatchdogInfo, in declared order: `_walk_watchdog_info`.
    fn walk_watchdog_info(&self) -> PyResult<Vec<PyWatchdogInfo>> {
        let mut out = Vec::new();
        // ChassisBase.get_watchdog
        // try: ... except NotImplementedError: pass -- rows already
        // collected stay collected.
        let r: PyResult<()> = (|| {
            for (i, dev) in one(call(get(&self.chassis, |o| o.get_watchdog()))?).into_iter().enumerate() {
                out.push(self.row_watchdog_info(&dev, "chassis 1", i, &[])?);
            }
            Ok(())
        })();
        match r {
            Err(e) if e.exc == Exc::NotImplementedError => {}
            other => other?,
        }
        Ok(out)
    }

    #[allow(unused_variables)]
    fn row_eeprom_tlv(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)]) -> PyResult<PyEepromTlv> {
        Ok(PyEepromTlv {
            source: fixed_get(fixed, "source")?,
            parent_name: PyVal::Str(parent.to_string()),
            code: fixed_get(fixed, "code")?,
            value: fixed_get(fixed, "value")?,
        })
    }

    /// Every EepromTlv, in declared order: `_walk_eeprom_tlv`.
    fn walk_eeprom_tlv(&self) -> PyResult<Vec<PyEepromTlv>> {
        let mut out = Vec::new();
        // ChassisBase.get_system_eeprom_info (mapping)
        // try: ... except NotImplementedError: pass -- rows already
        // collected stay collected.
        let r: PyResult<()> = (|| {
            for (i, (k, v)) in pairs(call(get(&self.chassis, |o| o.get_system_eeprom_info()))?).into_iter().enumerate() {
                out.push(self.row_eeprom_tlv(&PyVal::None, "chassis 1", i, &[("source", PyVal::Str("chassis".to_string())), ("code", PyVal::Str(k.py_str())), ("value", if v.is_none() { PyVal::None } else { PyVal::Str(v.py_str()) })])?);
            }
            Ok(())
        })();
        match r {
            Err(e) if e.exc == Exc::NotImplementedError => {}
            other => other?,
        }
        // ModuleBase.get_system_eeprom_info (mapping) via ChassisBase.get_all_modules
        // try: ... except NotImplementedError: pass -- rows already
        // collected stay collected.
        let r: PyResult<()> = (|| {
            if call(get(&self.chassis, |o| o.is_modular_chassis()))?.truthy() {
                for (i0, o0) in iter(call(get(&self.chassis, |o| o.get_all_modules()))?)?.into_iter().enumerate() {
                    let p0: String = fmt_name(&call(get(&o0, |o| o.get_name()))?, "Module {i}", "", i0).py_str();
                    for (i, (k, v)) in pairs(call(get(&o0, |o| o.get_system_eeprom_info()))?).into_iter().enumerate() {
                        out.push(self.row_eeprom_tlv(&PyVal::None, &p0, i, &[("source", PyVal::Str("module".to_string())), ("code", PyVal::Str(k.py_str())), ("value", if v.is_none() { PyVal::None } else { PyVal::Str(v.py_str()) })])?);
                    }
                }
            }
            Ok(())
        })();
        match r {
            Err(e) if e.exc == Exc::NotImplementedError => {}
            other => other?,
        }
        // BMCBase.get_eeprom (mapping) via ChassisBase.get_bmc
        // try: ... except NotImplementedError: pass -- rows already
        // collected stay collected.
        let r: PyResult<()> = (|| {
            let o0 = call(get(&self.chassis, |o| o.get_bmc()))?;
            let i0: usize = 0;
            if !o0.is_none() {
                let p0: String = fmt_name(&PyVal::None, "BMC", "", i0).py_str();
                for (i, (k, v)) in pairs(call(get(&o0, |o| o.get_eeprom()))?).into_iter().enumerate() {
                    out.push(self.row_eeprom_tlv(&PyVal::None, &p0, i, &[("source", PyVal::Str("bmc".to_string())), ("code", PyVal::Str(k.py_str())), ("value", if v.is_none() { PyVal::None } else { PyVal::Str(v.py_str()) })])?);
                }
            }
            Ok(())
        })();
        match r {
            Err(e) if e.exc == Exc::NotImplementedError => {}
            other => other?,
        }
        Ok(out)
    }

    #[allow(unused_variables)]
    fn row_bmc_info(&self, dev: &PyVal, parent: &str, i: usize, fixed: &[(&str, PyVal)]) -> PyResult<PyBmcInfo> {
        Ok(PyBmcInfo {
            name: default(text(call(get(dev, |o| o.get_name()))?), PyVal::Str("BMC".to_string())),
            presence: default(call(get(dev, |o| o.get_presence()))?, PyVal::Bool(false)),
            model: text(call(get(dev, |o| o.get_model()))?),
            serial: text(call(get(dev, |o| o.get_serial()))?),
            revision: text(call(get(dev, |o| o.get_revision()))?),
            status: call(get(dev, |o| o.get_status()))?,
            is_replaceable: default(call(get(dev, |o| o.is_replaceable()))?, PyVal::Bool(false)),
            version: text(call(get(dev, |o| o.get_version()))?),
        })
    }

    /// Every BmcInfo, in declared order: `_walk_bmc_info`.
    fn walk_bmc_info(&self) -> PyResult<Vec<PyBmcInfo>> {
        let mut out = Vec::new();
        // ChassisBase.get_bmc
        // try: ... except NotImplementedError: pass -- rows already
        // collected stay collected.
        let r: PyResult<()> = (|| {
            for (i, dev) in one(call(get(&self.chassis, |o| o.get_bmc()))?).into_iter().enumerate() {
                out.push(self.row_bmc_info(&dev, "chassis 1", i, &[])?);
            }
            Ok(())
        })();
        match r {
            Err(e) if e.exc == Exc::NotImplementedError => {}
            other => other?,
        }
        Ok(out)
    }
}

impl PlatformApi for BaseFacade {

    fn get_chassis_info(&mut self, cols: ChassisInfoCols) -> Result<ChassisInfo, PlatformError> {
        let rows = self.walk_chassis_info(cols.bits()).map_err(err)?;
        // `[0]`: the walk is the chassis, always one row.
        let row = rows
            .into_iter()
            .next()
            .ok_or_else(|| err(PyErr::index_error("list index out of range")))?;
        read_chassis_info(&row)
    }

    fn get_modules(&mut self, cols: ModuleInfoCols) -> Result<Vec<ModuleInfo>, PlatformError> {
        let rows = self.walk_module_info(cols.bits()).map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_module_info(row)?);
        }
        Ok(out)
    }

    fn get_thermals(&mut self, cols: ThermalInfoCols, skip: &[DeviceKey]) -> Result<Vec<ThermalInfo>, PlatformError> {
        // `frozenset(skip or ())`.
        let skip: HashSet<&str> = skip.iter().map(DeviceKey::as_str).collect();
        let rows = self.walk_thermal_info(cols.bits(), &skip).map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_thermal_info(row)?);
        }
        Ok(out)
    }

    fn get_fans(&mut self, cols: FanInfoCols, absorb: bool) -> Result<Vec<FanInfo>, PlatformError> {
        let rows = self.walk_fan_info(cols.bits(), absorb).map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_fan_info(row)?);
        }
        Ok(out)
    }

    fn get_fan_drawers(&mut self, cols: FanDrawerInfoCols) -> Result<Vec<FanDrawerInfo>, PlatformError> {
        let rows = self.walk_fan_drawer_info(cols.bits()).map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_fan_drawer_info(row)?);
        }
        Ok(out)
    }

    fn get_psus(&mut self) -> Result<Vec<PsuInfo>, PlatformError> {
        let rows = self.walk_psu_info().map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_psu_info(row)?);
        }
        Ok(out)
    }

    fn get_components(&mut self) -> Result<Vec<ComponentInfo>, PlatformError> {
        let rows = self.walk_component_info().map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_component_info(row)?);
        }
        Ok(out)
    }

    fn get_sensors(&mut self) -> Result<Vec<SensorInfo>, PlatformError> {
        let rows = self.walk_sensor_info().map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_sensor_info(row)?);
        }
        Ok(out)
    }

    fn get_leak_profiles(&mut self) -> Result<Vec<LeakProfile>, PlatformError> {
        let rows = self.walk_leak_profile().map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_leak_profile(row)?);
        }
        Ok(out)
    }

    fn get_leak_sensors(&mut self) -> Result<Vec<LeakSensorInfo>, PlatformError> {
        let rows = self.walk_leak_sensor_info().map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_leak_sensor_info(row)?);
        }
        Ok(out)
    }

    fn get_eeprom(&mut self) -> Result<Vec<EepromTlv>, PlatformError> {
        let rows = self.walk_eeprom_tlv().map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_eeprom_tlv(row)?);
        }
        Ok(out)
    }

    fn get_bmcs(&mut self) -> Result<Vec<BmcInfo>, PlatformError> {
        let rows = self.walk_bmc_info().map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_bmc_info(row)?);
        }
        Ok(out)
    }

    fn get_watchdogs(&mut self) -> Result<Vec<WatchdogInfo>, PlatformError> {
        let rows = self.walk_watchdog_info().map_err(err)?;
        let mut out = Vec::new();
        for row in &rows {
            out.push(read_watchdog_info(row)?);
        }
        Ok(out)
    }

    fn set_fan_led(&mut self, fan: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_fan_info(fan.as_str())?;
            let answer = action(get(&dev, |o| o.set_status_led(color.as_str())), "FanBase.set_status_led")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn set_fan_drawer_led(&mut self, drawer: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_fan_drawer_info(drawer.as_str())?;
            let answer = action(get(&dev, |o| o.set_status_led(color.as_str())), "FanDrawerBase.set_status_led")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn set_fan_speed(&mut self, fan: &DeviceKey, speed: i64) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_fan_info(fan.as_str())?;
            let answer = action(get(&dev, |o| o.set_speed(i128::from(speed))), "FanBase.set_speed")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn set_psu_led(&mut self, psu: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_psu_info(psu.as_str())?;
            let answer = action(get(&dev, |o| o.set_status_led(color.as_str())), "PsuBase.set_status_led")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn get_module_reboot_cause(&mut self, module: &DeviceKey) -> Result<ModuleRebootCause, PlatformError> {
        let v = (|| -> PyResult<PyModuleRebootCause> {
            let dev = self.find_module_info(module.as_str())?;
            let answer = action(get(&dev, |o| o.get_reboot_cause()), "ModuleBase.get_reboot_cause")?;
            Ok(PyModuleRebootCause { cause: at(&answer, 0), detail: at(&answer, 1) })
        })()
        .map_err(err)?;
        read_module_reboot_cause(&v)
    }

    fn get_module_midplane_down_reason(&mut self, module: &DeviceKey) -> Result<ModuleMidplaneDownReason, PlatformError> {
        let v = (|| -> PyResult<PyModuleMidplaneDownReason> {
            let dev = self.find_module_info(module.as_str())?;
            let answer = action(get(&dev, |o| o.get_midplane_down_reason()), "ModuleBase.get_midplane_down_reason")?;
            Ok(PyModuleMidplaneDownReason { reason: at(&answer, 0), detail: at(&answer, 1) })
        })()
        .map_err(err)?;
        read_module_midplane_down_reason(&v)
    }

    fn get_psu_master_led(&mut self, psu: &DeviceKey) -> Result<Option<String>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_psu_info(psu.as_str())?;
            let answer = action(get(&dev, |o| o.get_status_master_led()), "PsuBase.get_status_master_led")?;
            Ok(answer)
        })()
        .map_err(err)?;
        ret_str(&v)
    }

    fn set_psu_master_led(&mut self, psu: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_psu_info(psu.as_str())?;
            let answer = action(get(&dev, |o| o.set_status_master_led(color.as_str())), "PsuBase.set_status_master_led")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn reboot_module(&mut self, module: &DeviceKey, reboot_type: &str) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_module_info(module.as_str())?;
            let answer = action(get(&dev, |o| o.reboot(reboot_type)), "ModuleBase.reboot")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn set_module_admin_state(&mut self, module: &DeviceKey, up: bool) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_module_info(module.as_str())?;
            let answer = action(get(&dev, |o| o.set_admin_state(PyVal::Int(i128::from(up)))), "ModuleBase.set_admin_state")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn set_module_admin_state_gracefully(&mut self, module: &DeviceKey, up: bool) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_module_info(module.as_str())?;
            let answer = action(get(&dev, |o| o.set_admin_state_gracefully(PyVal::Int(i128::from(up)))), "ModuleBase.set_admin_state_gracefully")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn power_cycle_module(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_module_info(module.as_str())?;
            let answer = action(get(&dev, |o| o.do_power_cycle()), "ModuleBase.do_power_cycle")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn module_pre_shutdown(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_module_info(module.as_str())?;
            let answer = action(get(&dev, |o| o.module_pre_shutdown()), "ModuleBase.module_pre_shutdown")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn module_post_startup(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_module_info(module.as_str())?;
            let answer = action(get(&dev, |o| o.module_post_startup()), "ModuleBase.module_post_startup")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn set_module_state_transition(&mut self, module: &DeviceKey, transition_type: &str) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_module_info(module.as_str())?;
            let name = text(call(get(&dev, |o| o.get_name()))?);
            let answer = action(get(&dev, |o| o.set_module_state_transition(name, transition_type)), "ModuleBase.set_module_state_transition")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn clear_module_state_transition(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_module_info(module.as_str())?;
            let name = text(call(get(&dev, |o| o.get_name()))?);
            let answer = action(get(&dev, |o| o.clear_module_state_transition(name)), "ModuleBase.clear_module_state_transition")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn clear_module_gnoi_halt(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_module_info(module.as_str())?;
            let answer = action(get(&dev, |o| o.clear_module_gnoi_halt_in_progress()), "ModuleBase.clear_module_gnoi_halt_in_progress")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn set_sensor_high_threshold(&mut self, sensor: &DeviceKey, value: Number) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_sensor_info(sensor.as_str())?;
            let answer = action(get(&dev, |o| o.set_high_threshold(number_val(value))), "SensorBase.set_high_threshold")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn set_sensor_low_threshold(&mut self, sensor: &DeviceKey, value: Number) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_sensor_info(sensor.as_str())?;
            let answer = action(get(&dev, |o| o.set_low_threshold(number_val(value))), "SensorBase.set_low_threshold")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn get_module_key(&mut self, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        self.hatch.get_module_key(&self.chassis, name)
    }

    fn get_component_key(&mut self, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        self.hatch.get_component_key(&self.chassis, name)
    }

    fn get_module_component_key(&mut self, module: &str, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        self.hatch.get_module_component_key(&self.chassis, module, name)
    }

    fn get_available_firmware_version(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<String>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_component_info(component.as_str())?;
            let answer = action(get(&dev, |o| o.get_available_firmware_version(image_path)), "ComponentBase.get_available_firmware_version")?;
            Ok(answer)
        })()
        .map_err(err)?;
        ret_str(&v)
    }

    fn get_firmware_update_notification(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<String>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_component_info(component.as_str())?;
            let answer = action(get(&dev, |o| o.get_firmware_update_notification(image_path)), "ComponentBase.get_firmware_update_notification")?;
            Ok(answer)
        })()
        .map_err(err)?;
        ret_str(&v)
    }

    fn install_firmware(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_component_info(component.as_str())?;
            let answer = action(get(&dev, |o| o.install_firmware(image_path)), "ComponentBase.install_firmware")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn update_firmware(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_component_info(component.as_str())?;
            let answer = action(get(&dev, |o| o.update_firmware(image_path)), "ComponentBase.update_firmware")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn auto_update_firmware(&mut self, component: &DeviceKey, image_path: &str, boot_type: &str) -> Result<Option<i64>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let dev = self.find_component_info(component.as_str())?;
            let answer = action(get(&dev, |o| o.auto_update_firmware(image_path, boot_type)), "ComponentBase.auto_update_firmware")?;
            Ok(answer)
        })()
        .map_err(err)?;
        ret_int::<i64>(&v)
    }

    fn arm_watchdog(&mut self, seconds: i64) -> Result<Option<i64>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let t0 = call(get(&self.chassis, |o| o.get_watchdog()))?;
            let answer = action(get(&t0, |o| o.arm(i128::from(seconds))), "ChassisBase.get_watchdog.arm")?;
            Ok(answer)
        })()
        .map_err(err)?;
        ret_int::<i64>(&v)
    }

    fn disarm_watchdog(&mut self) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let t0 = call(get(&self.chassis, |o| o.get_watchdog()))?;
            let answer = action(get(&t0, |o| o.disarm()), "ChassisBase.get_watchdog.disarm")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn initialize_system_led(&mut self) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let answer = action(get(&self.chassis, |o| o.initizalize_system_led()), "ChassisBase.initizalize_system_led")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn init_midplane_switch(&mut self) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let answer = action(get(&self.chassis, |o| o.init_midplane_switch()), "ChassisBase.init_midplane_switch")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn set_chassis_led(&mut self, color: &str) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let answer = action(get(&self.chassis, |o| o.set_status_led(color)), "ChassisBase.set_status_led")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn change_sed_password(&mut self, new_password: &str) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let t0 = call(get(&self.chassis, |o| o.get_sed_mgmt()))?;
            let answer = action(get(&t0, |o| o.change_sed_password(new_password)), "ChassisBase.get_sed_mgmt.change_sed_password")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn reset_sed_password(&mut self) -> Result<Option<bool>, PlatformError> {
        let v = (|| -> PyResult<PyVal> {
            let t0 = call(get(&self.chassis, |o| o.get_sed_mgmt()))?;
            let answer = action(get(&t0, |o| o.reset_sed_password()), "ChassisBase.get_sed_mgmt.reset_sed_password")?;
            Ok(truthy(answer))
        })()
        .map_err(err)?;
        ret_bool(&v)
    }

    fn bmc_open_session(&mut self) -> Result<BmcResult, PlatformError> {
        self.hatch.bmc_open_session(&self.chassis)
    }

    fn bmc_close_session(&mut self, session_id: &str) -> Result<BmcResult, PlatformError> {
        self.hatch.bmc_close_session(&self.chassis, session_id)
    }

    fn bmc_reset_root_password(&mut self) -> Result<BmcResult, PlatformError> {
        self.hatch.bmc_reset_root_password(&self.chassis)
    }

    fn bmc_reset(&mut self, graceful: bool) -> Result<BmcResult, PlatformError> {
        self.hatch.bmc_reset(&self.chassis, graceful)
    }

    fn bmc_update_firmware(&mut self, image_path: &str) -> Result<BmcResult, PlatformError> {
        self.hatch.bmc_update_firmware(&self.chassis, image_path)
    }

    fn bmc_trigger_debug_log_dump(&mut self) -> Result<BmcResult, PlatformError> {
        self.hatch.bmc_trigger_debug_log_dump(&self.chassis)
    }

    fn bmc_get_debug_log_dump(&mut self, task_id: &str, filename: &str, path: &str) -> Result<BmcResult, PlatformError> {
        self.hatch.bmc_get_debug_log_dump(&self.chassis, task_id, filename, path)
    }

    fn get_asics(&mut self) -> Result<Vec<AsicInfo>, PlatformError> {
        self.hatch.get_asics(&self.chassis)
    }

    fn tm_initialize(&mut self) -> Result<(), PlatformError> {
        self.hatch.tm_initialize(&self.chassis)
    }

    fn tm_run_policy(&mut self) -> Result<(), PlatformError> {
        self.hatch.tm_run_policy(&self.chassis)
    }

    fn tm_get_interval(&mut self) -> Result<Option<f64>, PlatformError> {
        self.hatch.tm_get_interval(&self.chassis)
    }

    fn tm_deinitialize(&mut self) -> Result<(), PlatformError> {
        self.hatch.tm_deinitialize(&self.chassis)
    }

    fn tm_stop(&mut self) -> Result<(), PlatformError> {
        self.hatch.tm_stop(&self.chassis)
    }

    fn notify_shutdown(&mut self) -> Result<(), PlatformError> {
        self.hatch.notify_shutdown(&self.chassis)
    }

    fn eeprom_update_db(&mut self) -> Result<EepromUpdate, PlatformError> {
        self.hatch.eeprom_update_db(&self.chassis)
    }

    fn get_storage_devices(&mut self) -> Result<Vec<StorageDeviceInfo>, PlatformError> {
        self.hatch.get_storage_devices(&self.chassis)
    }

    fn get_pcie_devices(&mut self) -> Result<Vec<PcieDevice>, PlatformError> {
        self.hatch.get_pcie_devices(&self.chassis)
    }

    fn get_pcie_aer_stats(&mut self, bus: i64, dev: i64, func: i64) -> Result<Vec<PcieAerStat>, PlatformError> {
        self.hatch.get_pcie_aer_stats(&self.chassis, bus, dev, func)
    }

    fn get_change_event(&mut self, timeout_ms: i64) -> Result<ChangeEventBatch, PlatformError> {
        self.hatch.get_change_event(&self.chassis, timeout_ms)
    }

    /// Python's `atexit` handlers, which a native implementation registers in
    /// [`crate::atexit`] where its Python counterpart called `atexit.register`.
    fn finalize(&mut self) {
        crate::atexit::run();
    }
}
