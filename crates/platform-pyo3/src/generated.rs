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
//! Rust calling the Python facade, through PyO3.
//!
//! GENERATED from platform_api/facade.pyi by generator/generate.py.  Do not
//! edit: regenerate.
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
    LedColor, FanDirection, FanKind, PowerEntityKind, ModuleType, ModuleStatus, SensorKind, LeakSeverity, ChangeEventKind,
    ThermalInfo, FanInfo, FanDrawerInfo, PsuInfo, ChassisInfo, ModuleInfo, ComponentInfo, SensorInfo, LeakProfile, LeakSensorInfo, WatchdogInfo, ChangeEvent, ChangeEventBatch, EepromTlv, AsicInfo, BmcInfo, BmcResult,
    PlatformApi, PlatformError, Threshold,
};

use crate::{err, flag, num, rows, text, thr_arg, threshold, Bridge};


/// Read one `ThermalInfo` off the object the facade returned.
fn thermal_info(row: &Bound<'_, PyAny>) -> Result<ThermalInfo, PlatformError> {
    Ok(ThermalInfo {
        name: text(row, "name")?.unwrap_or_default(),
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        position_in_parent: num(row, "position_in_parent")?.map(|v| v as i32).unwrap_or(-1),
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        temperature: num(row, "temperature")?,
        high_threshold: threshold(row, "high_threshold")?,
        low_threshold: threshold(row, "low_threshold")?,
        high_critical_threshold: threshold(row, "high_critical_threshold")?,
        low_critical_threshold: threshold(row, "low_critical_threshold")?,
        min_recorded: num(row, "min_recorded")?,
        max_recorded: num(row, "max_recorded")?,
    })
}

/// Read one `FanInfo` off the object the facade returned.
fn fan_info(row: &Bound<'_, PyAny>) -> Result<FanInfo, PlatformError> {
    Ok(FanInfo {
        name: text(row, "name")?.unwrap_or_default(),
        kind: text(row, "kind")?.and_then(|s| FanKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        drawer_name: text(row, "drawer_name")?.unwrap_or_default(),
        position_in_parent: num(row, "position_in_parent")?.map(|v| v as i32).unwrap_or(-1),
        presence: flag(row, "presence")?.unwrap_or(false),
        status: flag(row, "status")?.unwrap_or(false),
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        speed_pct: num(row, "speed_pct")?.map(|v| v as u32),
        target_speed_pct: num(row, "target_speed_pct")?.map(|v| v as u32),
        direction: text(row, "direction")?.and_then(|s| FanDirection::from_str(&s)),
        is_under_speed: flag(row, "is_under_speed")?,
        is_over_speed: flag(row, "is_over_speed")?,
        status_led: text(row, "status_led")?.and_then(|s| LedColor::from_str(&s)),
    })
}

/// Read one `FanDrawerInfo` off the object the facade returned.
fn fan_drawer_info(row: &Bound<'_, PyAny>) -> Result<FanDrawerInfo, PlatformError> {
    Ok(FanDrawerInfo {
        name: text(row, "name")?.unwrap_or_default(),
        position_in_parent: num(row, "position_in_parent")?.map(|v| v as i32).unwrap_or(-1),
        presence: flag(row, "presence")?.unwrap_or(false),
        status: flag(row, "status")?,
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        status_led: text(row, "status_led")?.and_then(|s| LedColor::from_str(&s)),
        maximum_consumed_power: num(row, "maximum_consumed_power")?,
    })
}

/// Read one `PsuInfo` off the object the facade returned.
fn psu_info(row: &Bound<'_, PyAny>) -> Result<PsuInfo, PlatformError> {
    Ok(PsuInfo {
        name: text(row, "name")?.unwrap_or_default(),
        kind: text(row, "kind")?.and_then(|s| PowerEntityKind::from_str(&s)).ok_or_else(|| PlatformError::Backend("kind is missing or not a declared value".to_string()))?,
        position_in_parent: num(row, "position_in_parent")?.map(|v| v as i32).unwrap_or(-1),
        presence: flag(row, "presence")?.unwrap_or(false),
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        revision: text(row, "revision")?,
        power_good: flag(row, "power_good")?.unwrap_or(false),
        status_led: text(row, "status_led")?.and_then(|s| LedColor::from_str(&s)),
        voltage: num(row, "voltage")?,
        current: num(row, "current")?,
        power: num(row, "power")?,
        input_voltage: num(row, "input_voltage")?,
        input_current: num(row, "input_current")?,
        input_power: num(row, "input_power")?,
        temperature: num(row, "temperature")?,
        temperature_high_threshold: threshold(row, "temperature_high_threshold")?,
        voltage_high_threshold: threshold(row, "voltage_high_threshold")?,
        voltage_low_threshold: threshold(row, "voltage_low_threshold")?,
        maximum_supplied_power: num(row, "maximum_supplied_power")?,
        power_warning_suppress_threshold: num(row, "power_warning_suppress_threshold")?,
        power_critical_threshold: num(row, "power_critical_threshold")?,
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
        my_slot: num(row, "my_slot")?.map(|v| v as i64),
        supervisor_slot: num(row, "supervisor_slot")?.map(|v| v as i64),
        dpu_id: num(row, "dpu_id")?.map(|v| v as i64),
        dataplane_state: flag(row, "dataplane_state")?,
        controlplane_state: flag(row, "controlplane_state")?,
        status_led: text(row, "status_led")?.and_then(|s| LedColor::from_str(&s)),
    })
}

/// Read one `ModuleInfo` off the object the facade returned.
fn module_info(row: &Bound<'_, PyAny>) -> Result<ModuleInfo, PlatformError> {
    Ok(ModuleInfo {
        name: text(row, "name")?.unwrap_or_default(),
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
        position_in_parent: num(row, "position_in_parent")?.map(|v| v as i32).unwrap_or(-1),
        presence: flag(row, "presence")?.unwrap_or(false),
        status: flag(row, "status")?,
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        model: text(row, "model")?,
        serial: text(row, "serial")?,
        description: text(row, "description")?,
        slot: num(row, "slot")?.map(|v| v as i64),
        r#type: text(row, "type")?.and_then(|s| ModuleType::from_str(&s)),
        oper_status: text(row, "oper_status")?.and_then(|s| ModuleStatus::from_str(&s)),
        base_mac: text(row, "base_mac")?,
        dpu_id: num(row, "dpu_id")?.map(|v| v as i64),
        maximum_consumed_power: num(row, "maximum_consumed_power")?,
        midplane_ip: text(row, "midplane_ip")?,
        is_midplane_reachable: flag(row, "is_midplane_reachable")?,
        reboot_cause: text(row, "reboot_cause")?,
        reboot_cause_detail: text(row, "reboot_cause_detail")?,
        state_transition: flag(row, "state_transition")?,
    })
}

/// Read one `ComponentInfo` off the object the facade returned.
fn component_info(row: &Bound<'_, PyAny>) -> Result<ComponentInfo, PlatformError> {
    Ok(ComponentInfo {
        name: text(row, "name")?.unwrap_or_default(),
        parent_name: text(row, "parent_name")?.unwrap_or_default(),
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
        position_in_parent: num(row, "position_in_parent")?.map(|v| v as i32).unwrap_or(-1),
        is_replaceable: flag(row, "is_replaceable")?.unwrap_or(false),
        unit: text(row, "unit")?,
        value: num(row, "value")?,
        high_threshold: threshold(row, "high_threshold")?,
        low_threshold: threshold(row, "low_threshold")?,
        high_critical_threshold: threshold(row, "high_critical_threshold")?,
        low_critical_threshold: threshold(row, "low_critical_threshold")?,
        min_recorded: num(row, "min_recorded")?,
        max_recorded: num(row, "max_recorded")?,
    })
}

/// Read one `LeakProfile` off the object the facade returned.
fn leak_profile(row: &Bound<'_, PyAny>) -> Result<LeakProfile, PlatformError> {
    Ok(LeakProfile {
        r#type: text(row, "type")?.unwrap_or_default(),
        max_minor_duration_sec: num(row, "max_minor_duration_sec")?.map(|v| v as i64),
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
        profile_max_minor_duration_sec: num(row, "profile_max_minor_duration_sec")?.map(|v| v as i64),
    })
}

/// Read one `WatchdogInfo` off the object the facade returned.
fn watchdog_info(row: &Bound<'_, PyAny>) -> Result<WatchdogInfo, PlatformError> {
    Ok(WatchdogInfo {
        is_armed: flag(row, "is_armed")?,
        remaining_time: num(row, "remaining_time")?.map(|v| v as i64),
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

/// Read one `BmcResult` off the object the facade returned.
fn bmc_result(row: &Bound<'_, PyAny>) -> Result<BmcResult, PlatformError> {
    Ok(BmcResult {
        code: num(row, "code")?.map(|v| v as i64).unwrap_or(Default::default()),
        message: text(row, "message")?,
        session_id: text(row, "session_id")?,
        token: text(row, "token")?,
        task_id: text(row, "task_id")?,
    })
}

impl PlatformApi for Bridge {

    fn get_chassis_info(&mut self) -> Result<ChassisInfo, PlatformError> {
        Python::with_gil(|py| {
            let row = self
                .facade
                .bind(py)
                .call_method0("get_chassis_info")
                .map_err(|e| err(py, e))?;
            chassis_info(&row)
        })
    }

    fn get_modules(&mut self) -> Result<Vec<ModuleInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_modules")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(module_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_thermals(&mut self) -> Result<Vec<ThermalInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_thermals")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(thermal_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_fans(&mut self) -> Result<Vec<FanInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_fans")
                .map_err(|e| err(py, e))?;
            let mut out = Vec::new();
            for row in rows.try_iter().map_err(|e| err(py, e))? {
                let row = row.map_err(|e| err(py, e))?;
                out.push(fan_info(&row)?);
            }
            Ok(out)
        })
    }

    fn get_fan_drawers(&mut self) -> Result<Vec<FanDrawerInfo>, PlatformError> {
        Python::with_gil(|py| {
            let rows = self
                .facade
                .bind(py)
                .call_method0("get_fan_drawers")
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

    fn set_fan_led(&mut self, fan: &str, color: LedColor) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_fan_led", (fan, color.as_str(), ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn set_fan_drawer_led(&mut self, drawer: &str, color: LedColor) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_fan_drawer_led", (drawer, color.as_str(), ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn set_fan_speed(&mut self, fan: &str, speed: u32) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_fan_speed", (fan, speed, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn set_psu_led(&mut self, psu: &str, color: LedColor) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_psu_led", (psu, color.as_str(), ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn get_psu_master_led(&mut self, psu: &str) -> Result<Option<LedColor>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_psu_master_led", (psu, ))
                .map_err(|e| err(py, e))?;
            let s: Option<String> = v.extract().map_err(|e| err(py, e))?;
            let out = s.and_then(|s| LedColor::from_str(&s));
            Ok(out)
        })
    }

    fn set_psu_master_led(&mut self, psu: &str, color: LedColor) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_psu_master_led", (psu, color.as_str(), ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn reboot_module(&mut self, module: &str, reboot_type: &str) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("reboot_module", (module, reboot_type, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn set_module_admin_state(&mut self, module: &str, up: bool) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_module_admin_state", (module, up, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn set_module_admin_state_gracefully(&mut self, module: &str, up: bool) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_module_admin_state_gracefully", (module, up, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn power_cycle_module(&mut self, module: &str) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("power_cycle_module", (module, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn module_pre_shutdown(&mut self, module: &str) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("module_pre_shutdown", (module, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn module_post_startup(&mut self, module: &str) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("module_post_startup", (module, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn set_module_state_transition(&mut self, module: &str, transition_type: &str) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_module_state_transition", (module, transition_type, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn clear_module_state_transition(&mut self, module: &str) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("clear_module_state_transition", (module, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn clear_module_gnoi_halt(&mut self, module: &str) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("clear_module_gnoi_halt", (module, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn set_sensor_high_threshold(&mut self, sensor: &str, value: Threshold) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_sensor_high_threshold", (sensor, thr_arg(py, value), ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn set_sensor_low_threshold(&mut self, sensor: &str, value: Threshold) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_sensor_low_threshold", (sensor, thr_arg(py, value), ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn get_available_firmware_version(&mut self, component: &str, image_path: &str) -> Result<Option<String>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_available_firmware_version", (component, image_path, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn get_firmware_update_notification(&mut self, component: &str, image_path: &str) -> Result<Option<String>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("get_firmware_update_notification", (component, image_path, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn install_firmware(&mut self, component: &str, image_path: &str) -> Result<Option<bool>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("install_firmware", (component, image_path, ))
                .map_err(|e| err(py, e))?;
            v.extract().map_err(|e| err(py, e))
        })
    }

    fn update_firmware(&mut self, component: &str, image_path: &str) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("update_firmware", (component, image_path, ))
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn auto_update_firmware(&mut self, component: &str, image_path: &str, boot_type: &str) -> Result<Option<i64>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("auto_update_firmware", (component, image_path, boot_type, ))
                .map_err(|e| err(py, e))?;
            let n: Option<f64> = v.extract().map_err(|e| err(py, e))?;
            Ok(n.map(|x| x as i64))
        })
    }

    fn arm_watchdog(&mut self, seconds: i64) -> Result<Option<i64>, PlatformError> {
        Python::with_gil(|py| {
            let v = self
                .facade
                .bind(py)
                .call_method1("arm_watchdog", (seconds, ))
                .map_err(|e| err(py, e))?;
            let n: Option<f64> = v.extract().map_err(|e| err(py, e))?;
            Ok(n.map(|x| x as i64))
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

    fn initialize_system_led(&mut self) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("initialize_system_led", ())
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn init_midplane_switch(&mut self) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("init_midplane_switch", ())
                .map_err(|e| err(py, e))?;
            Ok(())
        })
    }

    fn set_chassis_led(&mut self, color: LedColor) -> Result<(), PlatformError> {
        Python::with_gil(|py| {
            self.facade
                .bind(py)
                .call_method1("set_chassis_led", (color.as_str(), ))
                .map_err(|e| err(py, e))?;
            Ok(())
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
}
