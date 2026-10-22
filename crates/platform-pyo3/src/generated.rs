//! Rust calling the Python facade, through PyO3.
//!
//! GENERATED from sonic_platform_api/facade.pyi by generator/generate.py.  Do
//! not edit: regenerate.
//!
//! One GIL acquisition per call, and one call per polling cycle per row type.
//! That is the reason the facade is flat: reaching the base classes directly
//! would cross the boundary once per attribute per device, and a chassis with
//! sixty transceivers has thousands of attributes.
//!
//! Nothing here holds a Python object other than the facade itself.  No row
//! carries a handle, no argument is a callback, and no call re-enters Python
//! from Rust from Python -- the thermal manager's chassis argument is held on
//! the Python side, which is what `tm_*` being argument-less means.

use pyo3::prelude::*;

use platform_api::{
    LedColor, FanKind, PowerEntityKind, ThermalKind, ModuleType, ModuleStatus, SensorKind, EepromUpdate, LeakSeverity, ChangeEventKind,
    ThermalInfo, FanInfo, FanDrawerInfo, PsuInfo, ChassisInfo, ModuleInfo, ComponentInfo, SensorInfo, LeakProfile, LeakSensorInfo, WatchdogInfo, ChangeEvent, ChangeEventBatch, PcieDevice, PcieAerStat, StorageDeviceInfo, EepromTlv, AsicInfo, BmcInfo, ModuleRebootCause, ModuleMidplaneDownReason, BmcResult,
    ThermalInfoCols, FanInfoCols, FanDrawerInfoCols, ChassisInfoCols, ModuleInfoCols,
    DeviceKey, Number, PlatformApi, PlatformError,
};

use crate::{err, flag, int_of, int_or_float, int_or_float_arg, integer, rows, text, Bridge};


/// Read one `ThermalInfo` off the object the facade returned.
fn thermal_info(row: &Bound<'_, PyAny>) -> Result<ThermalInfo, PlatformError> {
    Ok(ThermalInfo {
        name: text(row, "name")?.unwrap_or_default(),
        kind: text(row, "kind")?.and_then(|s| ThermalKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        key: text(row, "key")?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: text(row, "parent_key")?.map(DeviceKey::from),
        position_in_parent: integer::<i32>(row, "position_in_parent")?,
        temperature: int_or_float(row, "temperature")?,
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        min_recorded: int_or_float(row, "min_recorded")?,
        max_recorded: int_or_float(row, "max_recorded")?,
        high_threshold: int_or_float(row, "high_threshold")?,
        low_threshold: int_or_float(row, "low_threshold")?,
        high_critical_threshold: int_or_float(row, "high_critical_threshold")?,
        low_critical_threshold: int_or_float(row, "low_critical_threshold")?,
        error: text(row, "error")?,
        error_repr: text(row, "error_repr")?,
        error_column: text(row, "error_column")?,
    })
}

/// Read one `FanInfo` off the object the facade returned.
fn fan_info(row: &Bound<'_, PyAny>) -> Result<FanInfo, PlatformError> {
    Ok(FanInfo {
        name: text(row, "name")?.unwrap_or_default(),
        kind: text(row, "kind")?.and_then(|s| FanKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        key: text(row, "key")?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: text(row, "parent_key")?.map(DeviceKey::from),
        drawer_name: text(row, "drawer_name")?.unwrap_or_default(),
        position_in_parent: integer::<i32>(row, "position_in_parent")?,
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        presence: flag(row, "presence")?.unwrap_or(false),
        speed_pct: int_or_float(row, "speed_pct")?,
        target_speed_pct: int_or_float(row, "target_speed_pct")?,
        is_under_speed: flag(row, "is_under_speed")?,
        is_over_speed: flag(row, "is_over_speed")?,
        status: flag(row, "status")?.unwrap_or(false),
        direction: text(row, "direction")?,
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        status_led: text(row, "status_led")?,
        error: text(row, "error")?,
        error_repr: text(row, "error_repr")?,
        error_column: text(row, "error_column")?,
    })
}

/// Read one `FanDrawerInfo` off the object the facade returned.
fn fan_drawer_info(row: &Bound<'_, PyAny>) -> Result<FanDrawerInfo, PlatformError> {
    Ok(FanDrawerInfo {
        name: text(row, "name")?.unwrap_or_default(),
        key: text(row, "key")?.map(DeviceKey::from).unwrap_or_default(),
        position_in_parent: integer::<i32>(row, "position_in_parent")?,
        presence: flag(row, "presence")?.unwrap_or(false),
        status: flag(row, "status")?,
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        status_led: text(row, "status_led")?,
        maximum_consumed_power: int_or_float(row, "maximum_consumed_power")?,
    })
}

/// Read one `PsuInfo` off the object the facade returned.
fn psu_info(row: &Bound<'_, PyAny>) -> Result<PsuInfo, PlatformError> {
    Ok(PsuInfo {
        name: text(row, "name")?.unwrap_or_default(),
        kind: text(row, "kind")?.and_then(|s| PowerEntityKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        key: text(row, "key")?.map(DeviceKey::from).unwrap_or_default(),
        position_in_parent: integer::<i32>(row, "position_in_parent")?,
        presence: flag(row, "presence")?.unwrap_or(false),
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        revision: text(row, "revision")?,
        power_good: flag(row, "power_good")?.unwrap_or(false),
        status_led: text(row, "status_led")?,
        voltage: int_or_float(row, "voltage")?,
        current: int_or_float(row, "current")?,
        power: int_or_float(row, "power")?,
        input_voltage: int_or_float(row, "input_voltage")?,
        input_current: int_or_float(row, "input_current")?,
        input_power: int_or_float(row, "input_power")?,
        temperature: int_or_float(row, "temperature")?,
        temperature_high_threshold: int_or_float(row, "temperature_high_threshold")?,
        voltage_high_threshold: int_or_float(row, "voltage_high_threshold")?,
        voltage_low_threshold: int_or_float(row, "voltage_low_threshold")?,
        maximum_supplied_power: int_or_float(row, "maximum_supplied_power")?,
        power_warning_suppress_threshold: int_or_float(row, "power_warning_suppress_threshold")?,
        power_critical_threshold: int_or_float(row, "power_critical_threshold")?,
    })
}

/// Read one `ChassisInfo` off the object the facade returned.
fn chassis_info(row: &Bound<'_, PyAny>) -> Result<ChassisInfo, PlatformError> {
    Ok(ChassisInfo {
        name: text(row, "name")?.unwrap_or_default(),
        presence: flag(row, "presence")?.unwrap_or(true),
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        revision: text(row, "revision")?,
        status: flag(row, "status")?,
        base_mac: text(row, "base_mac")?,
        is_modular_chassis: flag(row, "is_modular_chassis")?.unwrap_or(false),
        is_smartswitch: flag(row, "is_smartswitch")?.unwrap_or(false),
        is_dpu: flag(row, "is_dpu")?.unwrap_or(false),
        is_bmc: flag(row, "is_bmc")?.unwrap_or(false),
        is_liquid_cooled: flag(row, "is_liquid_cooled")?.unwrap_or(false),
        reboot_cause: text(row, "reboot_cause")?,
        reboot_cause_detail: text(row, "reboot_cause_detail")?,
        my_slot: integer::<i64>(row, "my_slot")?,
        supervisor_slot: integer::<i64>(row, "supervisor_slot")?,
        dpu_id: integer::<i64>(row, "dpu_id")?,
        dataplane_state: flag(row, "dataplane_state")?,
        controlplane_state: flag(row, "controlplane_state")?,
        status_led: text(row, "status_led")?,
    })
}

/// Read one `ModuleInfo` off the object the facade returned.
fn module_info(row: &Bound<'_, PyAny>) -> Result<ModuleInfo, PlatformError> {
    Ok(ModuleInfo {
        name: text(row, "name")?.unwrap_or_default(),
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        key: text(row, "key")?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: text(row, "parent_key")?.map(DeviceKey::from),
        position_in_parent: integer::<i32>(row, "position_in_parent")?,
        presence: flag(row, "presence")?.unwrap_or(false),
        status: flag(row, "status")?,
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        description: text(row, "description")?,
        slot: integer::<i64>(row, "slot")?,
        r#type: text(row, "type")?.and_then(|s| ModuleType::from_str(&s)),
        oper_status: text(row, "oper_status")?.and_then(|s| ModuleStatus::from_str(&s)),
        base_mac: text(row, "base_mac")?,
        dpu_id: integer::<i64>(row, "dpu_id")?,
        maximum_consumed_power: int_or_float(row, "maximum_consumed_power")?,
        midplane_ip: text(row, "midplane_ip")?,
        is_midplane_reachable: flag(row, "is_midplane_reachable")?,
        state_transition: flag(row, "state_transition")?,
    })
}

/// Read one `ComponentInfo` off the object the facade returned.
fn component_info(row: &Bound<'_, PyAny>) -> Result<ComponentInfo, PlatformError> {
    Ok(ComponentInfo {
        name: text(row, "name")?.unwrap_or_default(),
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        key: text(row, "key")?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: text(row, "parent_key")?.map(DeviceKey::from),
        description: text(row, "description")?,
        firmware_version: text(row, "firmware_version")?,
    })
}

/// Read one `SensorInfo` off the object the facade returned.
fn sensor_info(row: &Bound<'_, PyAny>) -> Result<SensorInfo, PlatformError> {
    Ok(SensorInfo {
        name: text(row, "name")?.unwrap_or_default(),
        kind: text(row, "kind")?.and_then(|s| SensorKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        key: text(row, "key")?.map(DeviceKey::from).unwrap_or_default(),
        parent_key: text(row, "parent_key")?.map(DeviceKey::from),
        position_in_parent: integer::<i32>(row, "position_in_parent")?,
        value: int_or_float(row, "value")?,
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        unit: text(row, "unit")?,
        min_recorded: int_or_float(row, "min_recorded")?,
        max_recorded: int_or_float(row, "max_recorded")?,
        high_threshold: int_or_float(row, "high_threshold")?,
        low_threshold: int_or_float(row, "low_threshold")?,
        high_critical_threshold: int_or_float(row, "high_critical_threshold")?,
        low_critical_threshold: int_or_float(row, "low_critical_threshold")?,
        error: text(row, "error")?,
        error_repr: text(row, "error_repr")?,
        error_column: text(row, "error_column")?,
    })
}

/// Read one `LeakProfile` off the object the facade returned.
fn leak_profile(row: &Bound<'_, PyAny>) -> Result<LeakProfile, PlatformError> {
    Ok(LeakProfile {
        r#type: text(row, "type")?.unwrap_or_default(),
        max_minor_duration_sec: integer::<i64>(row, "max_minor_duration_sec")?,
    })
}

/// Read one `LeakSensorInfo` off the object the facade returned.
fn leak_sensor_info(row: &Bound<'_, PyAny>) -> Result<LeakSensorInfo, PlatformError> {
    Ok(LeakSensorInfo {
        name: text(row, "name")?.unwrap_or_default(),
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        sensor_type: text(row, "sensor_type")?,
        location: text(row, "location")?,
        is_leak: flag(row, "is_leak")?,
        is_ok: flag(row, "is_ok")?,
        severity: text(row, "severity")?.and_then(|s| LeakSeverity::from_str(&s)),
        profile_type: text(row, "profile_type")?,
        profile_max_minor_duration_sec: integer::<i64>(row, "profile_max_minor_duration_sec")?,
    })
}

/// Read one `WatchdogInfo` off the object the facade returned.
fn watchdog_info(row: &Bound<'_, PyAny>) -> Result<WatchdogInfo, PlatformError> {
    Ok(WatchdogInfo {
        is_armed: flag(row, "is_armed")?,
        remaining_time: integer::<i64>(row, "remaining_time")?,
    })
}

/// Read one `ChangeEvent` off the object the facade returned.
fn change_event(row: &Bound<'_, PyAny>) -> Result<ChangeEvent, PlatformError> {
    Ok(ChangeEvent {
        device_type: text(row, "device_type")?.unwrap_or_default(),
        device_id: text(row, "device_id")?.unwrap_or_default(),
        status: text(row, "status")?.unwrap_or_default(),
        kind: text(row, "kind")?.and_then(|s| ChangeEventKind::from_str(&s)),
    })
}

/// Read one `ChangeEventBatch` off the object the facade returned.
fn change_event_batch(row: &Bound<'_, PyAny>) -> Result<ChangeEventBatch, PlatformError> {
    Ok(ChangeEventBatch {
        ok: flag(row, "ok")?.unwrap_or(Default::default()),
        events: rows(row, "events", change_event)?,
    })
}

/// Read one `PcieDevice` off the object the facade returned.
fn pcie_device(row: &Bound<'_, PyAny>) -> Result<PcieDevice, PlatformError> {
    Ok(PcieDevice {
        name: text(row, "name")?.unwrap_or_default(),
        bus: integer::<i64>(row, "bus")?.unwrap_or(Default::default()),
        dev: integer::<i64>(row, "dev")?.unwrap_or(Default::default()),
        r#fn: integer::<i64>(row, "fn")?.unwrap_or(Default::default()),
        present: flag(row, "present")?.unwrap_or(Default::default()),
    })
}

/// Read one `PcieAerStat` off the object the facade returned.
fn pcie_aer_stat(row: &Bound<'_, PyAny>) -> Result<PcieAerStat, PlatformError> {
    Ok(PcieAerStat {
        severity: text(row, "severity")?.unwrap_or_default(),
        field: text(row, "field")?.unwrap_or_default(),
        value: text(row, "value")?.unwrap_or_default(),
    })
}

/// Read one `StorageDeviceInfo` off the object the facade returned.
fn storage_device_info(row: &Bound<'_, PyAny>) -> Result<StorageDeviceInfo, PlatformError> {
    Ok(StorageDeviceInfo {
        name: text(row, "name")?.unwrap_or_default(),
        available: flag(row, "available")?.unwrap_or(Default::default()),
        model: text(row, "model")?.unwrap_or_default(),
        serial: text(row, "serial")?.unwrap_or_default(),
        firmware: text(row, "firmware")?.unwrap_or_default(),
        health: text(row, "health")?.unwrap_or_default(),
        temperature: text(row, "temperature")?.unwrap_or_default(),
        disk_io_reads: text(row, "disk_io_reads")?.unwrap_or_default(),
        disk_io_writes: text(row, "disk_io_writes")?.unwrap_or_default(),
        reserved_blocks: text(row, "reserved_blocks")?.unwrap_or_default(),
        fs_io_reads: integer::<i64>(row, "fs_io_reads")?,
        fs_io_writes: integer::<i64>(row, "fs_io_writes")?,
        static_error: text(row, "static_error")?,
        error: text(row, "error")?,
    })
}

/// Read one `EepromTlv` off the object the facade returned.
fn eeprom_tlv(row: &Bound<'_, PyAny>) -> Result<EepromTlv, PlatformError> {
    Ok(EepromTlv {
        source: text(row, "source")?.unwrap_or_default(),
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        code: text(row, "code")?.unwrap_or_default(),
        value: text(row, "value")?,
    })
}

/// Read one `AsicInfo` off the object the facade returned.
fn asic_info(row: &Bound<'_, PyAny>) -> Result<AsicInfo, PlatformError> {
    Ok(AsicInfo {
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        asic_id: text(row, "asic_id")?.unwrap_or_default(),
        pci_address: text(row, "pci_address")?,
    })
}

/// Read one `BmcInfo` off the object the facade returned.
fn bmc_info(row: &Bound<'_, PyAny>) -> Result<BmcInfo, PlatformError> {
    Ok(BmcInfo {
        name: text(row, "name")?.unwrap_or_default(),
        presence: flag(row, "presence")?.unwrap_or(false),
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        revision: text(row, "revision")?,
        status: flag(row, "status")?,
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        version: text(row, "version")?,
    })
}

/// Read one `ModuleRebootCause` off the object the facade returned.
fn module_reboot_cause(row: &Bound<'_, PyAny>) -> Result<ModuleRebootCause, PlatformError> {
    Ok(ModuleRebootCause {
        cause: text(row, "cause")?,
        detail: text(row, "detail")?,
    })
}

/// Read one `ModuleMidplaneDownReason` off the object the facade returned.
fn module_midplane_down_reason(row: &Bound<'_, PyAny>) -> Result<ModuleMidplaneDownReason, PlatformError> {
    Ok(ModuleMidplaneDownReason {
        reason: text(row, "reason")?,
        detail: text(row, "detail")?,
    })
}

/// Read one `BmcResult` off the object the facade returned.
fn bmc_result(row: &Bound<'_, PyAny>) -> Result<BmcResult, PlatformError> {
    Ok(BmcResult {
        code: integer::<i64>(row, "code")?.unwrap_or(Default::default()),
        message: text(row, "message")?,
        session_id: text(row, "session_id")?,
        token: text(row, "token")?,
        task_id: text(row, "task_id")?,
    })
}

impl PlatformApi for Bridge {

    fn get_chassis_info(&mut self, cols: ChassisInfoCols) -> Result<ChassisInfo, PlatformError> {
        Python::with_gil(|py| {
            let row = self
                .facade
                .bind(py)
                .call_method1("get_chassis_info", (cols.bits(),))
                .map_err(|e| err(py, e))?;
            chassis_info(&row)
        })
    }

    fn get_modules(&mut self, cols: ModuleInfoCols) -> Result<Vec<ModuleInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method1("get_modules", (cols.bits(),))
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(module_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_thermals(&mut self, cols: ThermalInfoCols, skip: &[DeviceKey]) -> Result<Vec<ThermalInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method1("get_thermals", (cols.bits(), skip.iter().map(DeviceKey::as_str).collect::<Vec<_>>(),))
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(thermal_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_fans(&mut self, cols: FanInfoCols, absorb: bool) -> Result<Vec<FanInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method1("get_fans", (cols.bits(), absorb,))
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(fan_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_fan_drawers(&mut self, cols: FanDrawerInfoCols) -> Result<Vec<FanDrawerInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method1("get_fan_drawers", (cols.bits(),))
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(fan_drawer_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_psus(&mut self) -> Result<Vec<PsuInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_psus")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(psu_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_components(&mut self) -> Result<Vec<ComponentInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_components")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(component_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_sensors(&mut self) -> Result<Vec<SensorInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_sensors")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(sensor_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_leak_profiles(&mut self) -> Result<Vec<LeakProfile>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_leak_profiles")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(leak_profile(&row)?);
            }
            Ok(out)
        })
    }

    fn get_leak_sensors(&mut self) -> Result<Vec<LeakSensorInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_leak_sensors")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(leak_sensor_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_eeprom(&mut self) -> Result<Vec<EepromTlv>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_eeprom")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(eeprom_tlv(&row)?);
            }
            Ok(out)
        })
    }

    fn get_bmcs(&mut self) -> Result<Vec<BmcInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_bmcs")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(bmc_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_watchdogs(&mut self) -> Result<Vec<WatchdogInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_watchdogs")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(watchdog_info(&row)?);
            }
            Ok(out)
        })
    }

    fn set_fan_led(&mut self, fan: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_fan_led", (fan.as_str(), color.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_fan_drawer_led(&mut self, drawer: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_fan_drawer_led", (drawer.as_str(), color.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_fan_speed(&mut self, fan: &DeviceKey, speed: i64) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_fan_speed", (fan.as_str(), speed, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_psu_led(&mut self, psu: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_psu_led", (psu.as_str(), color.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn get_module_reboot_cause(&mut self, module: &DeviceKey) -> Result<ModuleRebootCause, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_module_reboot_cause", (module.as_str(), ))
                .map_err(|e| err(py, e))?;
            module_reboot_cause(&v)
        })
    }

    fn get_module_midplane_down_reason(&mut self, module: &DeviceKey) -> Result<ModuleMidplaneDownReason, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_module_midplane_down_reason", (module.as_str(), ))
                .map_err(|e| err(py, e))?;
            module_midplane_down_reason(&v)
        })
    }

    fn get_psu_master_led(&mut self, psu: &DeviceKey) -> Result<Option<String>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_psu_master_led", (psu.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_psu_master_led(&mut self, psu: &DeviceKey, color: LedColor) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_psu_master_led", (psu.as_str(), color.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn reboot_module(&mut self, module: &DeviceKey, reboot_type: &str) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("reboot_module", (module.as_str(), reboot_type, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_module_admin_state(&mut self, module: &DeviceKey, up: bool) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_module_admin_state", (module.as_str(), up, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_module_admin_state_gracefully(&mut self, module: &DeviceKey, up: bool) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_module_admin_state_gracefully", (module.as_str(), up, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn power_cycle_module(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("power_cycle_module", (module.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn module_pre_shutdown(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("module_pre_shutdown", (module.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn module_post_startup(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("module_post_startup", (module.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_module_state_transition(&mut self, module: &DeviceKey, transition_type: &str) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_module_state_transition", (module.as_str(), transition_type, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn clear_module_state_transition(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("clear_module_state_transition", (module.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn clear_module_gnoi_halt(&mut self, module: &DeviceKey) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("clear_module_gnoi_halt", (module.as_str(), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_sensor_high_threshold(&mut self, sensor: &DeviceKey, value: Number) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_sensor_high_threshold", (sensor.as_str(), int_or_float_arg(py, value), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_sensor_low_threshold(&mut self, sensor: &DeviceKey, value: Number) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_sensor_low_threshold", (sensor.as_str(), int_or_float_arg(py, value), ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn get_module_key(&mut self, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_module_key", (name, ))
                .map_err(|e| err(py, e))?;
            let s: Option<String> = v.extract().map_err(|e| err(py, e))?;
            let out = s.map(DeviceKey::from);
            Ok(out)
        })
    }

    fn get_component_key(&mut self, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_component_key", (name, ))
                .map_err(|e| err(py, e))?;
            let s: Option<String> = v.extract().map_err(|e| err(py, e))?;
            let out = s.map(DeviceKey::from);
            Ok(out)
        })
    }

    fn get_module_component_key(&mut self, module: &str, name: &str) -> Result<Option<DeviceKey>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_module_component_key", (module, name, ))
                .map_err(|e| err(py, e))?;
            let s: Option<String> = v.extract().map_err(|e| err(py, e))?;
            let out = s.map(DeviceKey::from);
            Ok(out)
        })
    }

    fn get_available_firmware_version(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<String>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_available_firmware_version", (component.as_str(), image_path, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn get_firmware_update_notification(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<String>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_firmware_update_notification", (component.as_str(), image_path, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn install_firmware(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("install_firmware", (component.as_str(), image_path, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn update_firmware(&mut self, component: &DeviceKey, image_path: &str) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("update_firmware", (component.as_str(), image_path, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn auto_update_firmware(&mut self, component: &DeviceKey, image_path: &str, boot_type: &str) -> Result<Option<i64>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("auto_update_firmware", (component.as_str(), image_path, boot_type, ))
                .map_err(|e| err(py, e))?;
            let n = int_of::<i64>(&v).map_err(|e| err(py, e))?;
            Ok(n)
        })
    }

    fn arm_watchdog(&mut self, seconds: i64) -> Result<Option<i64>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("arm_watchdog", (seconds, ))
                .map_err(|e| err(py, e))?;
            let n = int_of::<i64>(&v).map_err(|e| err(py, e))?;
            Ok(n)
        })
    }

    fn disarm_watchdog(&mut self) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("disarm_watchdog", ())
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn initialize_system_led(&mut self) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("initialize_system_led", ())
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn init_midplane_switch(&mut self) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("init_midplane_switch", ())
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn set_chassis_led(&mut self, color: &str) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("set_chassis_led", (color, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn change_sed_password(&mut self, new_password: &str) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("change_sed_password", (new_password, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn reset_sed_password(&mut self) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("reset_sed_password", ())
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn bmc_open_session(&mut self) -> Result<BmcResult, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("bmc_open_session", ())
                .map_err(|e| err(py, e))?;
            bmc_result(&v)
        })
    }

    fn bmc_close_session(&mut self, session_id: &str) -> Result<BmcResult, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("bmc_close_session", (session_id, ))
                .map_err(|e| err(py, e))?;
            bmc_result(&v)
        })
    }

    fn bmc_reset_root_password(&mut self) -> Result<BmcResult, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("bmc_reset_root_password", ())
                .map_err(|e| err(py, e))?;
            bmc_result(&v)
        })
    }

    fn bmc_reset(&mut self, graceful: bool) -> Result<BmcResult, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("bmc_reset", (graceful, ))
                .map_err(|e| err(py, e))?;
            bmc_result(&v)
        })
    }

    fn bmc_update_firmware(&mut self, image_path: &str) -> Result<BmcResult, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("bmc_update_firmware", (image_path, ))
                .map_err(|e| err(py, e))?;
            bmc_result(&v)
        })
    }

    fn bmc_trigger_debug_log_dump(&mut self) -> Result<BmcResult, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("bmc_trigger_debug_log_dump", ())
                .map_err(|e| err(py, e))?;
            bmc_result(&v)
        })
    }

    fn bmc_get_debug_log_dump(&mut self, task_id: &str, filename: &str, path: &str) -> Result<BmcResult, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("bmc_get_debug_log_dump", (task_id, filename, path, ))
                .map_err(|e| err(py, e))?;
            bmc_result(&v)
        })
    }

    fn get_asics(&mut self) -> Result<Vec<AsicInfo>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_asics", ())
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for item in v.try_iter().map_err(|e| err(py, e))? {
                out.push(asic_info(&item.map_err(|e| err(py, e))?)?);
            }
            Ok(out)
        })
    }

    fn tm_initialize(&mut self) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("tm_initialize", ())
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn tm_run_policy(&mut self) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("tm_run_policy", ())
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn tm_get_interval(&mut self) -> Result<Option<f64>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("tm_get_interval", ())
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn tm_deinitialize(&mut self) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("tm_deinitialize", ())
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn tm_stop(&mut self) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("tm_stop", ())
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn notify_shutdown(&mut self) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("notify_shutdown", ())
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn eeprom_update_db(&mut self) -> Result<EepromUpdate, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("eeprom_update_db", ())
                .map_err(|e| err(py, e))?;
            let s: Option<String> = v.extract().map_err(|e| err(py, e))?;
            let out = s.and_then(|s| EepromUpdate::from_str(&s));
            out.ok_or_else(|| PlatformError::Backend("EepromUpdate is not a declared value".to_string()))
        })
    }

    fn get_storage_devices(&mut self) -> Result<Vec<StorageDeviceInfo>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_storage_devices", ())
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for item in v.try_iter().map_err(|e| err(py, e))? {
                out.push(storage_device_info(&item.map_err(|e| err(py, e))?)?);
            }
            Ok(out)
        })
    }

    fn get_pcie_devices(&mut self) -> Result<Vec<PcieDevice>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_pcie_devices", ())
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for item in v.try_iter().map_err(|e| err(py, e))? {
                out.push(pcie_device(&item.map_err(|e| err(py, e))?)?);
            }
            Ok(out)
        })
    }

    fn get_pcie_aer_stats(&mut self, bus: i64, dev: i64, func: i64) -> Result<Vec<PcieAerStat>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_pcie_aer_stats", (bus, dev, func, ))
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for item in v.try_iter().map_err(|e| err(py, e))? {
                out.push(pcie_aer_stat(&item.map_err(|e| err(py, e))?)?);
            }
            Ok(out)
        })
    }

    fn get_change_event(&mut self, timeout_ms: i64) -> Result<ChangeEventBatch, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_change_event", (timeout_ms, ))
                .map_err(|e| err(py, e))?;
            change_event_batch(&v)
        })
    }

    /// Run Python's `atexit` handlers before the process goes away.
    ///
    /// Vendor cleanup registered with `atexit` runs on a Python daemon's
    /// `sys.exit()` and on nothing here: `process::exit` finalises no
    /// interpreter.  See [`crate::run_python_atexit_handlers`].
    fn finalize(&mut self) {
        crate::run_python_atexit_handlers();
    }
}
