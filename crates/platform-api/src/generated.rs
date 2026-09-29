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
//! The platform API, in Rust.
//!
//! GENERATED from platform_api/facade.pyi by generator/generate.py.  Do not
//! edit: regenerate.
//!
//! In phase 1 the only implementation is the PyO3 bridge in `platform-pyo3`,
//! which calls a vendor's existing Python.  In phase 2 a vendor implements
//! this trait natively and the bridge stops being registered; the daemons see
//! the same trait either way, which is the whole point of declaring it here
//! rather than in the bridge.
//!
//! Every method returns `Result`.  A platform that does not implement
//! something answers `Err(PlatformError::NotSupported)`, which is how the
//! caller tells "this platform has no PSU LED" from "the PSU LED is off" --
//! a distinction the Python API loses, because there a getter that raises and
//! a getter that returns None are the same event.

use crate::{PlatformError, Threshold};


/// `LedColor`, as declared in the stub.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum LedColor {
    /// `green`
    Green,
    /// `amber`
    Amber,
    /// `red`
    Red,
    /// `off`
    Off,
}

impl LedColor {
    /// The spelling the Python side uses.  The two must not drift, so both
    /// come from the one declaration.
    pub fn as_str(&self) -> &'static str {
        match self {
            LedColor::Green => "green",
            LedColor::Amber => "amber",
            LedColor::Red => "red",
            LedColor::Off => "off",
        }
    }

    /// `None` for a value the stub does not declare -- a vendor inventing a
    /// colour is a platform bug, not a variant to add here quietly.
    // Not `FromStr`: an undeclared value is an absent reading, not an error
    // with a type of its own, and every caller wants the `Option`.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "green" => Some(LedColor::Green),
            "amber" => Some(LedColor::Amber),
            "red" => Some(LedColor::Red),
            "off" => Some(LedColor::Off),
            _ => None,
        }
    }
}

impl std::fmt::Display for LedColor {
    /// The spelling the Python side uses, so that a log line and a DB row
    /// cannot disagree about what colour was asked for.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// `FanDirection`, as declared in the stub.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum FanDirection {
    /// `intake`
    Intake,
    /// `exhaust`
    Exhaust,
    /// `N/A`
    NA,
}

impl FanDirection {
    /// The spelling the Python side uses.  The two must not drift, so both
    /// come from the one declaration.
    pub fn as_str(&self) -> &'static str {
        match self {
            FanDirection::Intake => "intake",
            FanDirection::Exhaust => "exhaust",
            FanDirection::NA => "N/A",
        }
    }

    /// `None` for a value the stub does not declare -- a vendor inventing a
    /// colour is a platform bug, not a variant to add here quietly.
    // Not `FromStr`: an undeclared value is an absent reading, not an error
    // with a type of its own, and every caller wants the `Option`.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "intake" => Some(FanDirection::Intake),
            "exhaust" => Some(FanDirection::Exhaust),
            "N/A" => Some(FanDirection::NA),
            _ => None,
        }
    }
}

impl std::fmt::Display for FanDirection {
    /// The spelling the Python side uses, so that a log line and a DB row
    /// cannot disagree about what colour was asked for.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// `FanKind`, as declared in the stub.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum FanKind {
    /// `drawer`
    Drawer,
    /// `module`
    Module,
    /// `psu`
    Psu,
    /// `pdb`
    Pdb,
}

impl FanKind {
    /// The spelling the Python side uses.  The two must not drift, so both
    /// come from the one declaration.
    pub fn as_str(&self) -> &'static str {
        match self {
            FanKind::Drawer => "drawer",
            FanKind::Module => "module",
            FanKind::Psu => "psu",
            FanKind::Pdb => "pdb",
        }
    }

    /// `None` for a value the stub does not declare -- a vendor inventing a
    /// colour is a platform bug, not a variant to add here quietly.
    // Not `FromStr`: an undeclared value is an absent reading, not an error
    // with a type of its own, and every caller wants the `Option`.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "drawer" => Some(FanKind::Drawer),
            "module" => Some(FanKind::Module),
            "psu" => Some(FanKind::Psu),
            "pdb" => Some(FanKind::Pdb),
            _ => None,
        }
    }
}

impl std::fmt::Display for FanKind {
    /// The spelling the Python side uses, so that a log line and a DB row
    /// cannot disagree about what colour was asked for.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// `PowerEntityKind`, as declared in the stub.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum PowerEntityKind {
    /// `psu`
    Psu,
    /// `pdb`
    Pdb,
}

impl PowerEntityKind {
    /// The spelling the Python side uses.  The two must not drift, so both
    /// come from the one declaration.
    pub fn as_str(&self) -> &'static str {
        match self {
            PowerEntityKind::Psu => "psu",
            PowerEntityKind::Pdb => "pdb",
        }
    }

    /// `None` for a value the stub does not declare -- a vendor inventing a
    /// colour is a platform bug, not a variant to add here quietly.
    // Not `FromStr`: an undeclared value is an absent reading, not an error
    // with a type of its own, and every caller wants the `Option`.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "psu" => Some(PowerEntityKind::Psu),
            "pdb" => Some(PowerEntityKind::Pdb),
            _ => None,
        }
    }
}

impl std::fmt::Display for PowerEntityKind {
    /// The spelling the Python side uses, so that a log line and a DB row
    /// cannot disagree about what colour was asked for.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// `ModuleType`, as declared in the stub.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum ModuleType {
    /// `SUPERVISOR`
    Supervisor,
    /// `LINE-CARD`
    LineCard,
    /// `FABRIC-CARD`
    FabricCard,
    /// `DPU`
    Dpu,
    /// `SWITCH-HOST`
    SwitchHost,
}

impl ModuleType {
    /// The spelling the Python side uses.  The two must not drift, so both
    /// come from the one declaration.
    pub fn as_str(&self) -> &'static str {
        match self {
            ModuleType::Supervisor => "SUPERVISOR",
            ModuleType::LineCard => "LINE-CARD",
            ModuleType::FabricCard => "FABRIC-CARD",
            ModuleType::Dpu => "DPU",
            ModuleType::SwitchHost => "SWITCH-HOST",
        }
    }

    /// `None` for a value the stub does not declare -- a vendor inventing a
    /// colour is a platform bug, not a variant to add here quietly.
    // Not `FromStr`: an undeclared value is an absent reading, not an error
    // with a type of its own, and every caller wants the `Option`.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "SUPERVISOR" => Some(ModuleType::Supervisor),
            "LINE-CARD" => Some(ModuleType::LineCard),
            "FABRIC-CARD" => Some(ModuleType::FabricCard),
            "DPU" => Some(ModuleType::Dpu),
            "SWITCH-HOST" => Some(ModuleType::SwitchHost),
            _ => None,
        }
    }
}

impl std::fmt::Display for ModuleType {
    /// The spelling the Python side uses, so that a log line and a DB row
    /// cannot disagree about what colour was asked for.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// `ModuleStatus`, as declared in the stub.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum ModuleStatus {
    /// `Empty`
    Empty,
    /// `Offline`
    Offline,
    /// `PoweredDown`
    Powereddown,
    /// `Present`
    Present,
    /// `Fault`
    Fault,
    /// `Online`
    Online,
}

impl ModuleStatus {
    /// The spelling the Python side uses.  The two must not drift, so both
    /// come from the one declaration.
    pub fn as_str(&self) -> &'static str {
        match self {
            ModuleStatus::Empty => "Empty",
            ModuleStatus::Offline => "Offline",
            ModuleStatus::Powereddown => "PoweredDown",
            ModuleStatus::Present => "Present",
            ModuleStatus::Fault => "Fault",
            ModuleStatus::Online => "Online",
        }
    }

    /// `None` for a value the stub does not declare -- a vendor inventing a
    /// colour is a platform bug, not a variant to add here quietly.
    // Not `FromStr`: an undeclared value is an absent reading, not an error
    // with a type of its own, and every caller wants the `Option`.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "Empty" => Some(ModuleStatus::Empty),
            "Offline" => Some(ModuleStatus::Offline),
            "PoweredDown" => Some(ModuleStatus::Powereddown),
            "Present" => Some(ModuleStatus::Present),
            "Fault" => Some(ModuleStatus::Fault),
            "Online" => Some(ModuleStatus::Online),
            _ => None,
        }
    }
}

impl std::fmt::Display for ModuleStatus {
    /// The spelling the Python side uses, so that a log line and a DB row
    /// cannot disagree about what colour was asked for.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// `SensorKind`, as declared in the stub.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum SensorKind {
    /// `voltage`
    Voltage,
    /// `current`
    Current,
}

impl SensorKind {
    /// The spelling the Python side uses.  The two must not drift, so both
    /// come from the one declaration.
    pub fn as_str(&self) -> &'static str {
        match self {
            SensorKind::Voltage => "voltage",
            SensorKind::Current => "current",
        }
    }

    /// `None` for a value the stub does not declare -- a vendor inventing a
    /// colour is a platform bug, not a variant to add here quietly.
    // Not `FromStr`: an undeclared value is an absent reading, not an error
    // with a type of its own, and every caller wants the `Option`.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "voltage" => Some(SensorKind::Voltage),
            "current" => Some(SensorKind::Current),
            _ => None,
        }
    }
}

impl std::fmt::Display for SensorKind {
    /// The spelling the Python side uses, so that a log line and a DB row
    /// cannot disagree about what colour was asked for.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// `LeakSeverity`, as declared in the stub.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum LeakSeverity {
    /// `MINOR`
    Minor,
    /// `CRITICAL`
    Critical,
}

impl LeakSeverity {
    /// The spelling the Python side uses.  The two must not drift, so both
    /// come from the one declaration.
    pub fn as_str(&self) -> &'static str {
        match self {
            LeakSeverity::Minor => "MINOR",
            LeakSeverity::Critical => "CRITICAL",
        }
    }

    /// `None` for a value the stub does not declare -- a vendor inventing a
    /// colour is a platform bug, not a variant to add here quietly.
    // Not `FromStr`: an undeclared value is an absent reading, not an error
    // with a type of its own, and every caller wants the `Option`.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "MINOR" => Some(LeakSeverity::Minor),
            "CRITICAL" => Some(LeakSeverity::Critical),
            _ => None,
        }
    }
}

impl std::fmt::Display for LeakSeverity {
    /// The spelling the Python side uses, so that a log line and a DB row
    /// cannot disagree about what colour was asked for.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}

/// `ChangeEventKind`, as declared in the stub.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum ChangeEventKind {
    /// `removed`
    Removed,
    /// `inserted`
    Inserted,
    /// `i2c_stuck`
    I2cStuck,
    /// `bad_eeprom`
    BadEeprom,
    /// `unsupported_cable`
    UnsupportedCable,
    /// `high_temperature`
    HighTemperature,
    /// `bad_cable`
    BadCable,
}

impl ChangeEventKind {
    /// The spelling the Python side uses.  The two must not drift, so both
    /// come from the one declaration.
    pub fn as_str(&self) -> &'static str {
        match self {
            ChangeEventKind::Removed => "removed",
            ChangeEventKind::Inserted => "inserted",
            ChangeEventKind::I2cStuck => "i2c_stuck",
            ChangeEventKind::BadEeprom => "bad_eeprom",
            ChangeEventKind::UnsupportedCable => "unsupported_cable",
            ChangeEventKind::HighTemperature => "high_temperature",
            ChangeEventKind::BadCable => "bad_cable",
        }
    }

    /// `None` for a value the stub does not declare -- a vendor inventing a
    /// colour is a platform bug, not a variant to add here quietly.
    // Not `FromStr`: an undeclared value is an absent reading, not an error
    // with a type of its own, and every caller wants the `Option`.
    #[allow(clippy::should_implement_trait)]
    pub fn from_str(s: &str) -> Option<Self> {
        match s {
            "removed" => Some(ChangeEventKind::Removed),
            "inserted" => Some(ChangeEventKind::Inserted),
            "i2c_stuck" => Some(ChangeEventKind::I2cStuck),
            "bad_eeprom" => Some(ChangeEventKind::BadEeprom),
            "unsupported_cable" => Some(ChangeEventKind::UnsupportedCable),
            "high_temperature" => Some(ChangeEventKind::HighTemperature),
            "bad_cable" => Some(ChangeEventKind::BadCable),
            _ => None,
        }
    }
}

impl std::fmt::Display for ChangeEventKind {
    /// The spelling the Python side uses, so that a log line and a DB row
    /// cannot disagree about what colour was asked for.
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}


/// One temperature sensor, wherever in the tree it is mounted.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ThermalInfo {
    pub name: String,
    pub parent_name: String,
    pub position_in_parent: Option<i32>,
    pub is_replaceable: bool,
    pub temperature: Option<f64>,
    pub high_threshold: Option<Threshold>,
    pub low_threshold: Option<Threshold>,
    pub high_critical_threshold: Option<Threshold>,
    pub low_critical_threshold: Option<Threshold>,
    pub min_recorded: Option<f64>,
    pub max_recorded: Option<f64>,
}

/// One fan.  `kind` says where it is mounted, which is what decides
/// whether `drawer_name` means anything.
#[derive(Debug, Clone, PartialEq)]
pub struct FanInfo {
    pub name: String,
    pub kind: FanKind,
    pub parent_name: String,
    pub drawer_name: String,
    pub position_in_parent: Option<i32>,
    pub presence: bool,
    pub status: bool,
    pub is_replaceable: bool,
    pub model: Option<String>,
    pub serial: Option<String>,
    pub speed_pct: Option<u32>,
    pub target_speed_pct: Option<u32>,
    pub direction: Option<FanDirection>,
    pub is_under_speed: Option<bool>,
    pub is_over_speed: Option<bool>,
    pub status_led: Option<LedColor>,
}

/// One declinable column of `FanInfo`.
///
/// The discriminant is the bit this column occupies in `FanInfoCols`,
/// and it is the wire format the facade reads -- the same `generate.py` pass
/// writes both, so they cannot be numbered differently.  Adding a column
/// appends; reordering the stub renumbers the wire.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum FanInfoCol {
    /// `position_in_parent`, from `DeviceBase.get_position_in_parent`.
    PositionInParent = 0,
    /// `presence`, from `DeviceBase.get_presence`.
    Presence = 1,
    /// `status`, from `DeviceBase.get_status`.
    Status = 2,
    /// `is_replaceable`, from `DeviceBase.is_replaceable`.
    IsReplaceable = 3,
    /// `model`, from `DeviceBase.get_model`.
    Model = 4,
    /// `serial`, from `DeviceBase.get_serial`.
    Serial = 5,
    /// `speed_pct`, from `FanBase.get_speed`.
    SpeedPct = 6,
    /// `target_speed_pct`, from `FanBase.get_target_speed`.
    TargetSpeedPct = 7,
    /// `direction`, from `FanBase.get_direction`.
    Direction = 8,
    /// `is_under_speed`, from `FanBase.is_under_speed`.
    IsUnderSpeed = 9,
    /// `is_over_speed`, from `FanBase.is_over_speed`.
    IsOverSpeed = 10,
    /// `status_led`, from `FanBase.get_status_led`.
    StatusLed = 11,
}

impl FanInfoCol {
    /// Every column, in declaration order.
    pub const ALL: &'static [FanInfoCol] = &[
        FanInfoCol::PositionInParent,
        FanInfoCol::Presence,
        FanInfoCol::Status,
        FanInfoCol::IsReplaceable,
        FanInfoCol::Model,
        FanInfoCol::Serial,
        FanInfoCol::SpeedPct,
        FanInfoCol::TargetSpeedPct,
        FanInfoCol::Direction,
        FanInfoCol::IsUnderSpeed,
        FanInfoCol::IsOverSpeed,
        FanInfoCol::StatusLed,
    ];

    /// The bit this column sets in a `FanInfoCols`.
    pub const fn bit(self) -> u64 {
        1u64 << (self as u8)
    }

    /// The column's name, for `Debug` and for reading a log line.
    pub const fn as_str(self) -> &'static str {
        match self {
            FanInfoCol::PositionInParent => "position_in_parent",
            FanInfoCol::Presence => "presence",
            FanInfoCol::Status => "status",
            FanInfoCol::IsReplaceable => "is_replaceable",
            FanInfoCol::Model => "model",
            FanInfoCol::Serial => "serial",
            FanInfoCol::SpeedPct => "speed_pct",
            FanInfoCol::TargetSpeedPct => "target_speed_pct",
            FanInfoCol::Direction => "direction",
            FanInfoCol::IsUnderSpeed => "is_under_speed",
            FanInfoCol::IsOverSpeed => "is_over_speed",
            FanInfoCol::StatusLed => "status_led",
        }
    }
}

/// Which columns of `FanInfo` a caller wants read.
///
/// **Columns outside the set are unspecified, not guaranteed absent.** An
/// implementation that has no notion of columns may fill them anyway and is
/// still correct; the set is a hint that lets a caller decline work, not a
/// promise about what it will not receive.  That is what keeps this parameter
/// implementable by something that is not the PyO3 facade.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct FanInfoCols(u64);

impl FanInfoCols {
    /// Nothing declinable: the columns that come from the traversal are still
    /// read, which is what makes a by-name lookup possible.
    pub const NONE: Self = FanInfoCols(0);
    /// Every column -- what a caller that has not thought about it should pass.
    pub const ALL: Self = FanInfoCols(4095);
    pub const POSITION_IN_PARENT: Self = FanInfoCols(1u64 << 0);
    pub const PRESENCE: Self = FanInfoCols(1u64 << 1);
    pub const STATUS: Self = FanInfoCols(1u64 << 2);
    pub const IS_REPLACEABLE: Self = FanInfoCols(1u64 << 3);
    pub const MODEL: Self = FanInfoCols(1u64 << 4);
    pub const SERIAL: Self = FanInfoCols(1u64 << 5);
    pub const SPEED_PCT: Self = FanInfoCols(1u64 << 6);
    pub const TARGET_SPEED_PCT: Self = FanInfoCols(1u64 << 7);
    pub const DIRECTION: Self = FanInfoCols(1u64 << 8);
    pub const IS_UNDER_SPEED: Self = FanInfoCols(1u64 << 9);
    pub const IS_OVER_SPEED: Self = FanInfoCols(1u64 << 10);
    pub const STATUS_LED: Self = FanInfoCols(1u64 << 11);

    /// The set holding just this column.  Lets a caller name a column once,
    /// as a `FanInfoCol`, instead of once as a column and again as a
    /// constant that has to be spelled the same way.
    pub const fn of(col: FanInfoCol) -> Self {
        FanInfoCols(col.bit())
    }

    /// Both sets.  `const` so a daemon can state its columns once, at the top.
    pub const fn with(self, other: Self) -> Self {
        FanInfoCols(self.0 | other.0)
    }

    /// Whether one column was asked for.
    pub const fn contains(self, col: FanInfoCol) -> bool {
        self.0 & col.bit() != 0
    }

    /// The wire form.  For the bridge; a caller should name columns instead.
    pub const fn bits(self) -> u64 {
        self.0
    }
}

impl std::fmt::Debug for FanInfoCols {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "FanInfoCols[")?;
        let mut first = true;
        for col in FanInfoCol::ALL {
            if self.contains(*col) {
                if !first {
                    write!(f, "|")?;
                }
                write!(f, "{}", col.as_str())?;
                first = false;
            }
        }
        write!(f, "]")
    }
}

/// One fan drawer: the field-replaceable unit a chassis fan sits in.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct FanDrawerInfo {
    pub name: String,
    pub position_in_parent: Option<i32>,
    pub presence: bool,
    pub status: Option<bool>,
    pub is_replaceable: bool,
    pub model: Option<String>,
    pub serial: Option<String>,
    pub status_led: Option<LedColor>,
    pub maximum_consumed_power: Option<f64>,
}

/// One declinable column of `FanDrawerInfo`.
///
/// The discriminant is the bit this column occupies in `FanDrawerInfoCols`,
/// and it is the wire format the facade reads -- the same `generate.py` pass
/// writes both, so they cannot be numbered differently.  Adding a column
/// appends; reordering the stub renumbers the wire.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum FanDrawerInfoCol {
    /// `position_in_parent`, from `DeviceBase.get_position_in_parent`.
    PositionInParent = 0,
    /// `presence`, from `DeviceBase.get_presence`.
    Presence = 1,
    /// `status`, from `DeviceBase.get_status`.
    Status = 2,
    /// `is_replaceable`, from `DeviceBase.is_replaceable`.
    IsReplaceable = 3,
    /// `model`, from `DeviceBase.get_model`.
    Model = 4,
    /// `serial`, from `DeviceBase.get_serial`.
    Serial = 5,
    /// `status_led`, from `FanDrawerBase.get_status_led`.
    StatusLed = 6,
    /// `maximum_consumed_power`, from `FanDrawerBase.get_maximum_consumed_power`.
    MaximumConsumedPower = 7,
}

impl FanDrawerInfoCol {
    /// Every column, in declaration order.
    pub const ALL: &'static [FanDrawerInfoCol] = &[
        FanDrawerInfoCol::PositionInParent,
        FanDrawerInfoCol::Presence,
        FanDrawerInfoCol::Status,
        FanDrawerInfoCol::IsReplaceable,
        FanDrawerInfoCol::Model,
        FanDrawerInfoCol::Serial,
        FanDrawerInfoCol::StatusLed,
        FanDrawerInfoCol::MaximumConsumedPower,
    ];

    /// The bit this column sets in a `FanDrawerInfoCols`.
    pub const fn bit(self) -> u64 {
        1u64 << (self as u8)
    }

    /// The column's name, for `Debug` and for reading a log line.
    pub const fn as_str(self) -> &'static str {
        match self {
            FanDrawerInfoCol::PositionInParent => "position_in_parent",
            FanDrawerInfoCol::Presence => "presence",
            FanDrawerInfoCol::Status => "status",
            FanDrawerInfoCol::IsReplaceable => "is_replaceable",
            FanDrawerInfoCol::Model => "model",
            FanDrawerInfoCol::Serial => "serial",
            FanDrawerInfoCol::StatusLed => "status_led",
            FanDrawerInfoCol::MaximumConsumedPower => "maximum_consumed_power",
        }
    }
}

/// Which columns of `FanDrawerInfo` a caller wants read.
///
/// **Columns outside the set are unspecified, not guaranteed absent.** An
/// implementation that has no notion of columns may fill them anyway and is
/// still correct; the set is a hint that lets a caller decline work, not a
/// promise about what it will not receive.  That is what keeps this parameter
/// implementable by something that is not the PyO3 facade.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct FanDrawerInfoCols(u64);

impl FanDrawerInfoCols {
    /// Nothing declinable: the columns that come from the traversal are still
    /// read, which is what makes a by-name lookup possible.
    pub const NONE: Self = FanDrawerInfoCols(0);
    /// Every column -- what a caller that has not thought about it should pass.
    pub const ALL: Self = FanDrawerInfoCols(255);
    pub const POSITION_IN_PARENT: Self = FanDrawerInfoCols(1u64 << 0);
    pub const PRESENCE: Self = FanDrawerInfoCols(1u64 << 1);
    pub const STATUS: Self = FanDrawerInfoCols(1u64 << 2);
    pub const IS_REPLACEABLE: Self = FanDrawerInfoCols(1u64 << 3);
    pub const MODEL: Self = FanDrawerInfoCols(1u64 << 4);
    pub const SERIAL: Self = FanDrawerInfoCols(1u64 << 5);
    pub const STATUS_LED: Self = FanDrawerInfoCols(1u64 << 6);
    pub const MAXIMUM_CONSUMED_POWER: Self = FanDrawerInfoCols(1u64 << 7);

    /// The set holding just this column.  Lets a caller name a column once,
    /// as a `FanDrawerInfoCol`, instead of once as a column and again as a
    /// constant that has to be spelled the same way.
    pub const fn of(col: FanDrawerInfoCol) -> Self {
        FanDrawerInfoCols(col.bit())
    }

    /// Both sets.  `const` so a daemon can state its columns once, at the top.
    pub const fn with(self, other: Self) -> Self {
        FanDrawerInfoCols(self.0 | other.0)
    }

    /// Whether one column was asked for.
    pub const fn contains(self, col: FanDrawerInfoCol) -> bool {
        self.0 & col.bit() != 0
    }

    /// The wire form.  For the bridge; a caller should name columns instead.
    pub const fn bits(self) -> u64 {
        self.0
    }
}

impl std::fmt::Debug for FanDrawerInfoCols {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "FanDrawerInfoCols[")?;
        let mut first = true;
        for col in FanDrawerInfoCol::ALL {
            if self.contains(*col) {
                if !first {
                    write!(f, "|")?;
                }
                write!(f, "{}", col.as_str())?;
                first = false;
            }
        }
        write!(f, "]")
    }
}

/// A PSU or a PDB.  `PdbBase` extends `PsuBase` and psud publishes both
/// into the same table, so they are one row type with a `kind`.
#[derive(Debug, Clone, PartialEq)]
pub struct PsuInfo {
    pub name: String,
    pub kind: PowerEntityKind,
    pub position_in_parent: Option<i32>,
    pub presence: bool,
    pub is_replaceable: bool,
    pub model: Option<String>,
    pub serial: Option<String>,
    pub revision: Option<String>,
    pub power_good: bool,
    pub status_led: Option<LedColor>,
    pub voltage: Option<f64>,
    pub current: Option<f64>,
    pub power: Option<f64>,
    pub input_voltage: Option<f64>,
    pub input_current: Option<f64>,
    pub input_power: Option<f64>,
    pub temperature: Option<f64>,
    pub temperature_high_threshold: Option<Threshold>,
    pub voltage_high_threshold: Option<Threshold>,
    pub voltage_low_threshold: Option<Threshold>,
    pub maximum_supplied_power: Option<f64>,
    pub power_warning_suppress_threshold: Option<f64>,
    pub power_critical_threshold: Option<f64>,
}

/// The chassis itself.  A singleton: there is one, and it is the device.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ChassisInfo {
    pub name: String,
    pub presence: bool,
    pub model: Option<String>,
    pub serial: Option<String>,
    pub revision: Option<String>,
    pub status: Option<bool>,
    pub base_mac: Option<String>,
    pub is_modular_chassis: bool,
    pub is_smartswitch: bool,
    pub is_dpu: bool,
    pub is_bmc: bool,
    pub is_liquid_cooled: bool,
    pub reboot_cause: Option<String>,
    pub reboot_cause_detail: Option<String>,
    pub my_slot: Option<i64>,
    pub supervisor_slot: Option<i64>,
    pub dpu_id: Option<i64>,
    pub dataplane_state: Option<bool>,
    pub controlplane_state: Option<bool>,
    pub status_led: Option<LedColor>,
}

/// One declinable column of `ChassisInfo`.
///
/// The discriminant is the bit this column occupies in `ChassisInfoCols`,
/// and it is the wire format the facade reads -- the same `generate.py` pass
/// writes both, so they cannot be numbered differently.  Adding a column
/// appends; reordering the stub renumbers the wire.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum ChassisInfoCol {
    /// `presence`, from `DeviceBase.get_presence`.
    Presence = 0,
    /// `model`, from `DeviceBase.get_model`.
    Model = 1,
    /// `serial`, from `DeviceBase.get_serial`.
    Serial = 2,
    /// `revision`, from `DeviceBase.get_revision`.
    Revision = 3,
    /// `status`, from `DeviceBase.get_status`.
    Status = 4,
    /// `base_mac`, from `ChassisBase.get_base_mac`.
    BaseMac = 5,
    /// `is_modular_chassis`, from `ChassisBase.is_modular_chassis`.
    IsModularChassis = 6,
    /// `is_smartswitch`, from `ChassisBase.is_smartswitch`.
    IsSmartswitch = 7,
    /// `is_dpu`, from `ChassisBase.is_dpu`.
    IsDpu = 8,
    /// `is_bmc`, from `ChassisBase.is_bmc`.
    IsBmc = 9,
    /// `is_liquid_cooled`, from `ChassisBase.is_liquid_cooled`.
    IsLiquidCooled = 10,
    /// `reboot_cause`, from `ChassisBase.get_reboot_cause`.
    RebootCause = 11,
    /// `reboot_cause_detail`, from `ChassisBase.get_reboot_cause`.
    RebootCauseDetail = 12,
    /// `my_slot`, from `ChassisBase.get_my_slot`.
    MySlot = 13,
    /// `supervisor_slot`, from `ChassisBase.get_supervisor_slot`.
    SupervisorSlot = 14,
    /// `dpu_id`, from `ChassisBase.get_dpu_id`.
    DpuId = 15,
    /// `dataplane_state`, from `ChassisBase.get_dataplane_state`.
    DataplaneState = 16,
    /// `controlplane_state`, from `ChassisBase.get_controlplane_state`.
    ControlplaneState = 17,
    /// `status_led`, from `ChassisBase.get_status_led`.
    StatusLed = 18,
}

impl ChassisInfoCol {
    /// Every column, in declaration order.
    pub const ALL: &'static [ChassisInfoCol] = &[
        ChassisInfoCol::Presence,
        ChassisInfoCol::Model,
        ChassisInfoCol::Serial,
        ChassisInfoCol::Revision,
        ChassisInfoCol::Status,
        ChassisInfoCol::BaseMac,
        ChassisInfoCol::IsModularChassis,
        ChassisInfoCol::IsSmartswitch,
        ChassisInfoCol::IsDpu,
        ChassisInfoCol::IsBmc,
        ChassisInfoCol::IsLiquidCooled,
        ChassisInfoCol::RebootCause,
        ChassisInfoCol::RebootCauseDetail,
        ChassisInfoCol::MySlot,
        ChassisInfoCol::SupervisorSlot,
        ChassisInfoCol::DpuId,
        ChassisInfoCol::DataplaneState,
        ChassisInfoCol::ControlplaneState,
        ChassisInfoCol::StatusLed,
    ];

    /// The bit this column sets in a `ChassisInfoCols`.
    pub const fn bit(self) -> u64 {
        1u64 << (self as u8)
    }

    /// The column's name, for `Debug` and for reading a log line.
    pub const fn as_str(self) -> &'static str {
        match self {
            ChassisInfoCol::Presence => "presence",
            ChassisInfoCol::Model => "model",
            ChassisInfoCol::Serial => "serial",
            ChassisInfoCol::Revision => "revision",
            ChassisInfoCol::Status => "status",
            ChassisInfoCol::BaseMac => "base_mac",
            ChassisInfoCol::IsModularChassis => "is_modular_chassis",
            ChassisInfoCol::IsSmartswitch => "is_smartswitch",
            ChassisInfoCol::IsDpu => "is_dpu",
            ChassisInfoCol::IsBmc => "is_bmc",
            ChassisInfoCol::IsLiquidCooled => "is_liquid_cooled",
            ChassisInfoCol::RebootCause => "reboot_cause",
            ChassisInfoCol::RebootCauseDetail => "reboot_cause_detail",
            ChassisInfoCol::MySlot => "my_slot",
            ChassisInfoCol::SupervisorSlot => "supervisor_slot",
            ChassisInfoCol::DpuId => "dpu_id",
            ChassisInfoCol::DataplaneState => "dataplane_state",
            ChassisInfoCol::ControlplaneState => "controlplane_state",
            ChassisInfoCol::StatusLed => "status_led",
        }
    }
}

/// Which columns of `ChassisInfo` a caller wants read.
///
/// **Columns outside the set are unspecified, not guaranteed absent.** An
/// implementation that has no notion of columns may fill them anyway and is
/// still correct; the set is a hint that lets a caller decline work, not a
/// promise about what it will not receive.  That is what keeps this parameter
/// implementable by something that is not the PyO3 facade.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct ChassisInfoCols(u64);

impl ChassisInfoCols {
    /// Nothing declinable: the columns that come from the traversal are still
    /// read, which is what makes a by-name lookup possible.
    pub const NONE: Self = ChassisInfoCols(0);
    /// Every column -- what a caller that has not thought about it should pass.
    pub const ALL: Self = ChassisInfoCols(524287);
    pub const PRESENCE: Self = ChassisInfoCols(1u64 << 0);
    pub const MODEL: Self = ChassisInfoCols(1u64 << 1);
    pub const SERIAL: Self = ChassisInfoCols(1u64 << 2);
    pub const REVISION: Self = ChassisInfoCols(1u64 << 3);
    pub const STATUS: Self = ChassisInfoCols(1u64 << 4);
    pub const BASE_MAC: Self = ChassisInfoCols(1u64 << 5);
    pub const IS_MODULAR_CHASSIS: Self = ChassisInfoCols(1u64 << 6);
    pub const IS_SMARTSWITCH: Self = ChassisInfoCols(1u64 << 7);
    pub const IS_DPU: Self = ChassisInfoCols(1u64 << 8);
    pub const IS_BMC: Self = ChassisInfoCols(1u64 << 9);
    pub const IS_LIQUID_COOLED: Self = ChassisInfoCols(1u64 << 10);
    pub const REBOOT_CAUSE: Self = ChassisInfoCols(1u64 << 11);
    pub const REBOOT_CAUSE_DETAIL: Self = ChassisInfoCols(1u64 << 12);
    pub const MY_SLOT: Self = ChassisInfoCols(1u64 << 13);
    pub const SUPERVISOR_SLOT: Self = ChassisInfoCols(1u64 << 14);
    pub const DPU_ID: Self = ChassisInfoCols(1u64 << 15);
    pub const DATAPLANE_STATE: Self = ChassisInfoCols(1u64 << 16);
    pub const CONTROLPLANE_STATE: Self = ChassisInfoCols(1u64 << 17);
    pub const STATUS_LED: Self = ChassisInfoCols(1u64 << 18);

    /// The set holding just this column.  Lets a caller name a column once,
    /// as a `ChassisInfoCol`, instead of once as a column and again as a
    /// constant that has to be spelled the same way.
    pub const fn of(col: ChassisInfoCol) -> Self {
        ChassisInfoCols(col.bit())
    }

    /// Both sets.  `const` so a daemon can state its columns once, at the top.
    pub const fn with(self, other: Self) -> Self {
        ChassisInfoCols(self.0 | other.0)
    }

    /// Whether one column was asked for.
    pub const fn contains(self, col: ChassisInfoCol) -> bool {
        self.0 & col.bit() != 0
    }

    /// The wire form.  For the bridge; a caller should name columns instead.
    pub const fn bits(self) -> u64 {
        self.0
    }
}

impl std::fmt::Debug for ChassisInfoCols {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "ChassisInfoCols[")?;
        let mut first = true;
        for col in ChassisInfoCol::ALL {
            if self.contains(*col) {
                if !first {
                    write!(f, "|")?;
                }
                write!(f, "{}", col.as_str())?;
                first = false;
            }
        }
        write!(f, "]")
    }
}

/// One line card, fabric card, supervisor or DPU.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ModuleInfo {
    pub name: String,
    pub parent_name: String,
    pub position_in_parent: Option<i32>,
    pub presence: bool,
    pub status: Option<bool>,
    pub is_replaceable: bool,
    pub model: Option<String>,
    pub serial: Option<String>,
    pub description: Option<String>,
    pub slot: Option<i64>,
    pub r#type: Option<ModuleType>,
    pub oper_status: Option<ModuleStatus>,
    pub base_mac: Option<String>,
    pub dpu_id: Option<i64>,
    pub maximum_consumed_power: Option<f64>,
    pub midplane_ip: Option<String>,
    pub is_midplane_reachable: Option<bool>,
    pub state_transition: Option<bool>,
}

/// One declinable column of `ModuleInfo`.
///
/// The discriminant is the bit this column occupies in `ModuleInfoCols`,
/// and it is the wire format the facade reads -- the same `generate.py` pass
/// writes both, so they cannot be numbered differently.  Adding a column
/// appends; reordering the stub renumbers the wire.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum ModuleInfoCol {
    /// `position_in_parent`, from `DeviceBase.get_position_in_parent`.
    PositionInParent = 0,
    /// `presence`, from `DeviceBase.get_presence`.
    Presence = 1,
    /// `status`, from `DeviceBase.get_status`.
    Status = 2,
    /// `is_replaceable`, from `DeviceBase.is_replaceable`.
    IsReplaceable = 3,
    /// `model`, from `DeviceBase.get_model`.
    Model = 4,
    /// `serial`, from `DeviceBase.get_serial`.
    Serial = 5,
    /// `description`, from `ModuleBase.get_description`.
    Description = 6,
    /// `slot`, from `ModuleBase.get_slot`.
    Slot = 7,
    /// `type`, from `ModuleBase.get_type`.
    Type = 8,
    /// `oper_status`, from `ModuleBase.get_oper_status`.
    OperStatus = 9,
    /// `base_mac`, from `ModuleBase.get_base_mac`.
    BaseMac = 10,
    /// `dpu_id`, from `ModuleBase.get_dpu_id`.
    DpuId = 11,
    /// `maximum_consumed_power`, from `ModuleBase.get_maximum_consumed_power`.
    MaximumConsumedPower = 12,
    /// `midplane_ip`, from `ModuleBase.get_midplane_ip`.
    MidplaneIp = 13,
    /// `is_midplane_reachable`, from `ModuleBase.is_midplane_reachable`.
    IsMidplaneReachable = 14,
    /// `state_transition`, from `ModuleBase.get_module_state_transition`.
    StateTransition = 15,
}

impl ModuleInfoCol {
    /// Every column, in declaration order.
    pub const ALL: &'static [ModuleInfoCol] = &[
        ModuleInfoCol::PositionInParent,
        ModuleInfoCol::Presence,
        ModuleInfoCol::Status,
        ModuleInfoCol::IsReplaceable,
        ModuleInfoCol::Model,
        ModuleInfoCol::Serial,
        ModuleInfoCol::Description,
        ModuleInfoCol::Slot,
        ModuleInfoCol::Type,
        ModuleInfoCol::OperStatus,
        ModuleInfoCol::BaseMac,
        ModuleInfoCol::DpuId,
        ModuleInfoCol::MaximumConsumedPower,
        ModuleInfoCol::MidplaneIp,
        ModuleInfoCol::IsMidplaneReachable,
        ModuleInfoCol::StateTransition,
    ];

    /// The bit this column sets in a `ModuleInfoCols`.
    pub const fn bit(self) -> u64 {
        1u64 << (self as u8)
    }

    /// The column's name, for `Debug` and for reading a log line.
    pub const fn as_str(self) -> &'static str {
        match self {
            ModuleInfoCol::PositionInParent => "position_in_parent",
            ModuleInfoCol::Presence => "presence",
            ModuleInfoCol::Status => "status",
            ModuleInfoCol::IsReplaceable => "is_replaceable",
            ModuleInfoCol::Model => "model",
            ModuleInfoCol::Serial => "serial",
            ModuleInfoCol::Description => "description",
            ModuleInfoCol::Slot => "slot",
            ModuleInfoCol::Type => "type",
            ModuleInfoCol::OperStatus => "oper_status",
            ModuleInfoCol::BaseMac => "base_mac",
            ModuleInfoCol::DpuId => "dpu_id",
            ModuleInfoCol::MaximumConsumedPower => "maximum_consumed_power",
            ModuleInfoCol::MidplaneIp => "midplane_ip",
            ModuleInfoCol::IsMidplaneReachable => "is_midplane_reachable",
            ModuleInfoCol::StateTransition => "state_transition",
        }
    }
}

/// Which columns of `ModuleInfo` a caller wants read.
///
/// **Columns outside the set are unspecified, not guaranteed absent.** An
/// implementation that has no notion of columns may fill them anyway and is
/// still correct; the set is a hint that lets a caller decline work, not a
/// promise about what it will not receive.  That is what keeps this parameter
/// implementable by something that is not the PyO3 facade.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
pub struct ModuleInfoCols(u64);

impl ModuleInfoCols {
    /// Nothing declinable: the columns that come from the traversal are still
    /// read, which is what makes a by-name lookup possible.
    pub const NONE: Self = ModuleInfoCols(0);
    /// Every column -- what a caller that has not thought about it should pass.
    pub const ALL: Self = ModuleInfoCols(65535);
    pub const POSITION_IN_PARENT: Self = ModuleInfoCols(1u64 << 0);
    pub const PRESENCE: Self = ModuleInfoCols(1u64 << 1);
    pub const STATUS: Self = ModuleInfoCols(1u64 << 2);
    pub const IS_REPLACEABLE: Self = ModuleInfoCols(1u64 << 3);
    pub const MODEL: Self = ModuleInfoCols(1u64 << 4);
    pub const SERIAL: Self = ModuleInfoCols(1u64 << 5);
    pub const DESCRIPTION: Self = ModuleInfoCols(1u64 << 6);
    pub const SLOT: Self = ModuleInfoCols(1u64 << 7);
    pub const TYPE: Self = ModuleInfoCols(1u64 << 8);
    pub const OPER_STATUS: Self = ModuleInfoCols(1u64 << 9);
    pub const BASE_MAC: Self = ModuleInfoCols(1u64 << 10);
    pub const DPU_ID: Self = ModuleInfoCols(1u64 << 11);
    pub const MAXIMUM_CONSUMED_POWER: Self = ModuleInfoCols(1u64 << 12);
    pub const MIDPLANE_IP: Self = ModuleInfoCols(1u64 << 13);
    pub const IS_MIDPLANE_REACHABLE: Self = ModuleInfoCols(1u64 << 14);
    pub const STATE_TRANSITION: Self = ModuleInfoCols(1u64 << 15);

    /// The set holding just this column.  Lets a caller name a column once,
    /// as a `ModuleInfoCol`, instead of once as a column and again as a
    /// constant that has to be spelled the same way.
    pub const fn of(col: ModuleInfoCol) -> Self {
        ModuleInfoCols(col.bit())
    }

    /// Both sets.  `const` so a daemon can state its columns once, at the top.
    pub const fn with(self, other: Self) -> Self {
        ModuleInfoCols(self.0 | other.0)
    }

    /// Whether one column was asked for.
    pub const fn contains(self, col: ModuleInfoCol) -> bool {
        self.0 & col.bit() != 0
    }

    /// The wire form.  For the bridge; a caller should name columns instead.
    pub const fn bits(self) -> u64 {
        self.0
    }
}

impl std::fmt::Debug for ModuleInfoCols {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "ModuleInfoCols[")?;
        let mut first = true;
        for col in ModuleInfoCol::ALL {
            if self.contains(*col) {
                if !first {
                    write!(f, "|")?;
                }
                write!(f, "{}", col.as_str())?;
                first = false;
            }
        }
        write!(f, "]")
    }
}

/// One field-upgradeable component: a BIOS, a CPLD, an FPGA, an SSD.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ComponentInfo {
    pub name: String,
    pub parent_name: String,
    pub description: Option<String>,
    pub firmware_version: Option<String>,
}

/// One voltage or current sensor.
///
/// `kind` rather than two row types: the columns are identical, the daemon
/// publishes them to two tables off the same loop, and a consumer that wanted
/// only one filters.
#[derive(Debug, Clone, PartialEq)]
pub struct SensorInfo {
    pub name: String,
    pub kind: SensorKind,
    pub parent_name: String,
    pub position_in_parent: Option<i32>,
    pub is_replaceable: bool,
    pub unit: Option<String>,
    pub value: Option<f64>,
    pub high_threshold: Option<Threshold>,
    pub low_threshold: Option<Threshold>,
    pub high_critical_threshold: Option<Threshold>,
    pub low_critical_threshold: Option<Threshold>,
    pub min_recorded: Option<f64>,
    pub max_recorded: Option<f64>,
}

/// A named leak policy, published once at start-up.
///
/// Separate from `LeakSensorInfo` because the daemon publishes it to its own
/// table once rather than every cycle, and because several sensors share one.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct LeakProfile {
    pub r#type: String,
    pub max_minor_duration_sec: Option<i64>,
}

/// One liquid-cooling leak sensor.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct LeakSensorInfo {
    pub name: String,
    pub parent_name: String,
    pub sensor_type: Option<String>,
    pub location: Option<String>,
    pub is_leak: Option<bool>,
    pub is_ok: Option<bool>,
    pub severity: Option<LeakSeverity>,
    pub profile_type: Option<String>,
    pub profile_max_minor_duration_sec: Option<i64>,
}

/// The hardware watchdog.  A singleton per chassis.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct WatchdogInfo {
    pub is_armed: Option<bool>,
    pub remaining_time: Option<i64>,
}

/// One device that changed, out of the two-level mapping the base class
/// returns.
///
/// `{'fan': {'0': '0', '2': '1'}, 'sfp': {'11': '0'}}` becomes three rows.
/// The nesting carries no information a row cannot: the outer key is the
/// device type and the inner key is the device id, and a consumer that wanted
/// them grouped can group them.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ChangeEvent {
    pub device_type: String,
    pub device_id: String,
    pub status: String,
    pub kind: Option<ChangeEventKind>,
}

/// What one `get_change_event` call answered.
///
/// `ok` is carried rather than raised on.  It reads like a success flag and
/// is not one: `ok=False` is how a platform reports a system-level event,
/// with the detail in the mapping under the key the daemon watches for
/// (xcvrd:301-323 maps the pair to SYSTEM_NOT_READY or SYSTEM_FAIL).  A
/// facade that raised on it would delete that path.
///
/// `ok=True` with no events is the ordinary timeout: nothing changed.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ChangeEventBatch {
    pub ok: bool,
    pub events: Vec<ChangeEvent>,
}

/// One device out of the platform's `pcie.yaml`, and whether it is there.
///
/// `PcieUtil.get_pcie_check()` answers the parsed config file with a `result`
/// column added, so what comes back is the *expected* inventory annotated with
/// what was found -- not a scan of the bus.  A device the yaml does not list
/// does not appear here however present it is, which is the point: pcied is
/// checking the machine against its own parts list.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct PcieDevice {
    pub name: String,
    pub bus: i64,
    pub dev: i64,
    pub r#fn: i64,
    pub present: bool,
}

/// One AER counter of one PCIe device.
///
/// `get_pcie_aer_stats` answers `{severity: {field: count}}` for three fixed
/// severities.  The nesting carries nothing a row cannot, and pcied itself
/// flattens it straight back to `severity|field` before writing (`pcied:133`).
#[derive(Debug, Clone, PartialEq, Default)]
pub struct PcieAerStat {
    pub severity: String,
    pub field: String,
    pub value: String,
}

/// One storage disk of the switch, as stormond publishes it.
///
/// `StorageDevices` walks `/sys/block` and hands each disk to a factory that
/// answers an `SsdUtil`, an `EmmcUtil`, a `UsbUtil` -- or `None`, for a disk
/// none of them handles.  That `None` is carried here as `available=False`
/// rather than dropped: a disk the switch has and cannot read about is a fact,
/// and stormond says so (`stormond:309`, `:332`).
///
/// Every reading but the two counters is carried as the string Python would
/// have written.  The daemon only ever `str()`s them on the way to STATE_DB,
/// and a column that guessed at a number would have to guess again at how to
/// print it.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct StorageDeviceInfo {
    pub name: String,
    pub available: bool,
    pub model: String,
    pub serial: String,
    pub firmware: String,
    pub health: String,
    pub temperature: String,
    pub disk_io_reads: String,
    pub disk_io_writes: String,
    pub reserved_blocks: String,
    pub fs_io_reads: Option<i64>,
    pub fs_io_writes: Option<i64>,
}

/// One entry of a system EEPROM.
///
/// The base class answers a mapping whose keys are ONIE TLV codes as hex
/// strings on the chassis, and Redfish field names on the BMC.  Neither key
/// set is enumerable ahead of time -- which is exactly why this is rows and
/// not columns.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct EepromTlv {
    pub source: String,
    pub parent_name: String,
    pub code: String,
    pub value: Option<String>,
}

/// One ASIC on a module, and where it sits on the PCI bus.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct AsicInfo {
    pub parent_name: String,
    pub asic_id: String,
    pub pci_address: Option<String>,
}

/// The board management controller.  A list of at most one.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct BmcInfo {
    pub name: String,
    pub presence: bool,
    pub model: Option<String>,
    pub serial: Option<String>,
    pub revision: Option<String>,
    pub status: Option<bool>,
    pub is_replaceable: bool,
    pub version: Option<String>,
}

/// Why a module last restarted: the cause, and the reason behind it.
///
/// `ModuleBase.get_reboot_cause()` answers `(cause, detail)` and chassisd
/// publishes both -- the cause to `REBOOT_CAUSE|<module>|<ts>.cause` and the
/// detail to its `comment`, which is the half a person reads.  `comment` also
/// reaches `/host/reboot-cause/module/<dpu>/history/*.json` and the
/// `previous-reboot-cause.json` symlink beside it.
///
/// Declaring the method as `Calls(at=0)` carried only the cause, and the stub
/// said so: "nothing consumes the detail".  That was measured false on a
/// SmartSwitch -- against the Python daemon on the same switch, in the same
/// hour, the records read
///
/// ```text
///     python:  'Non-Hardware' | 'Reset due to Power off'
///     rust:    'Non-Hardware' | 'N/A'
/// ```
///
/// A second method with `at=1` would answer the other half, and would also
/// call the vendor getter a second time.  That getter *logs* (`module.py:
/// 477,482`), which is the reason this stopped being a column at all; asking
/// twice would put back half the noise the change removed.  So one call, and
/// a row with both slots in it.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ModuleRebootCause {
    pub cause: Option<String>,
    pub detail: Option<String>,
}

/// Why a module's midplane went down: the reason, and the detail behind it.
///
/// `ModuleBase.get_midplane_down_reason()` answers `(reason, detail)`, the
/// reason being one of the `REBOOT_CAUSE_*` strings.  chassisd asks when a
/// DPU's midplane goes from up to down without a planned transition, joins
/// the halves that are not empty and publishes `Unplanned: '<joined>'`.  One
/// call fills both slots, for the reason `ModuleRebootCause` gives.
///
/// A platform that answers a bare string instead of the tuple gets the whole
/// string as `reason`, which is how chassisd reads it too.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct ModuleMidplaneDownReason {
    pub reason: Option<String>,
    pub detail: Option<String>,
}

/// What a BMC command answered.
///
/// Every BMC method returns `(code, message)`, with 0 meaning success. The
/// code is carried rather than raised on: the CLI prints the message on a
/// non-zero code and carries on, and a facade that raised would turn a
/// reported failure into an exception the caller has to translate back.
#[derive(Debug, Clone, PartialEq, Default)]
pub struct BmcResult {
    pub code: i64,
    pub message: Option<String>,
    pub session_id: Option<String>,
    pub token: Option<String>,
    pub task_id: Option<String>,
}

/// The platform, as the daemons see it.
///
/// `&mut self` throughout: an implementation may cache what it reads within a
/// polling cycle, and the snapshot methods are exactly where that cache is
/// refreshed.
pub trait PlatformApi: Send {
    /// The chassis.
    ///
    /// A singleton, so it is not a `list`: there is one chassis and the
    /// traversal that would flatten it has nothing to walk.
    ///
    /// No default: a chassis that cannot describe itself has nothing an empty
    /// value could stand in for.
    fn get_chassis_info(&mut self, cols: ChassisInfoCols) -> Result<ChassisInfo, PlatformError> {
        let _ = (cols,);
        Err(PlatformError::NotSupported("get_chassis_info".to_string()))
    }
    /// Every ModuleInfo, in declared order.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_modules(&mut self, cols: ModuleInfoCols) -> Result<Vec<ModuleInfo>, PlatformError> {
        let _ = (cols,);
        Ok(Vec::new())
    }
    /// Every ThermalInfo, in declared order.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_thermals(&mut self) -> Result<Vec<ThermalInfo>, PlatformError> {
        let _ = ();
        Ok(Vec::new())
    }
    /// Every FanInfo, in declared order.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_fans(&mut self, cols: FanInfoCols) -> Result<Vec<FanInfo>, PlatformError> {
        let _ = (cols,);
        Ok(Vec::new())
    }
    /// Every FanDrawerInfo, in declared order.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_fan_drawers(&mut self, cols: FanDrawerInfoCols) -> Result<Vec<FanDrawerInfo>, PlatformError> {
        let _ = (cols,);
        Ok(Vec::new())
    }
    /// Every PsuInfo, in declared order.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_psus(&mut self) -> Result<Vec<PsuInfo>, PlatformError> {
        let _ = ();
        Ok(Vec::new())
    }
    /// Every ComponentInfo, in declared order.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_components(&mut self) -> Result<Vec<ComponentInfo>, PlatformError> {
        let _ = ();
        Ok(Vec::new())
    }
    /// Every SensorInfo, in declared order.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_sensors(&mut self) -> Result<Vec<SensorInfo>, PlatformError> {
        let _ = ();
        Ok(Vec::new())
    }
    /// Published once at start-up, so read on call rather than cached.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_leak_profiles(&mut self) -> Result<Vec<LeakProfile>, PlatformError> {
        let _ = ();
        Ok(Vec::new())
    }
    /// Every LeakSensorInfo, in declared order.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_leak_sensors(&mut self) -> Result<Vec<LeakSensorInfo>, PlatformError> {
        let _ = ();
        Ok(Vec::new())
    }
    /// Every system EEPROM entry the platform exposes, chassis and BMC.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_eeprom(&mut self) -> Result<Vec<EepromTlv>, PlatformError> {
        let _ = ();
        Ok(Vec::new())
    }
    /// A list of at most one, for the same reason as `get_watchdogs`.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_bmcs(&mut self) -> Result<Vec<BmcInfo>, PlatformError> {
        let _ = ();
        Ok(Vec::new())
    }
    /// A list of at most one.
    ///
    /// Not a singleton: a platform without a watchdog has none, and a
    /// singleton accessor would have to invent a row to say so.
    ///
    /// Order is part of the contract: it is what lets the Rust and the Python
    /// implementations be compared row for row.
    ///
    /// Empty by default, so that adding a row type to the schema does not
    /// break every implementation that does not have one -- a platform with
    /// no BMC should not have to write a method to say so.
    fn get_watchdogs(&mut self) -> Result<Vec<WatchdogInfo>, PlatformError> {
        let _ = ();
        Ok(Vec::new())
    }

    /// Set the LED on one fan.
    ///
    /// Separate from `set_fan_drawer_led` on purpose.  thermalctld sets the
    /// fan's LED and then its drawer's with the same colour, tolerating
    /// either being unimplemented (thermalctld:547-550); folding the two into
    /// one call would hide which of them a platform refused.
    ///
    /// Not supported by default: a platform whose set_fan_led is not
    /// software-controllable should not have to write a method to say so.
    fn set_fan_led(&mut self, fan: &str, color: LedColor) -> Result<(), PlatformError> {
        let _ = fan;
        let _ = color;
        Err(PlatformError::NotSupported("set_fan_led".to_string()))
    }

    /// set_fan_drawer_led
    ///
    /// Not supported by default: a platform whose set_fan_drawer_led is not
    /// software-controllable should not have to write a method to say so.
    fn set_fan_drawer_led(&mut self, drawer: &str, color: LedColor) -> Result<(), PlatformError> {
        let _ = drawer;
        let _ = color;
        Err(PlatformError::NotSupported("set_fan_drawer_led".to_string()))
    }

    /// set_fan_speed
    ///
    /// Not supported by default: a platform whose set_fan_speed is not
    /// software-controllable should not have to write a method to say so.
    fn set_fan_speed(&mut self, fan: &str, speed: u32) -> Result<(), PlatformError> {
        let _ = fan;
        let _ = speed;
        Err(PlatformError::NotSupported("set_fan_speed".to_string()))
    }

    /// set_psu_led
    ///
    /// Not supported by default: a platform whose set_psu_led is not
    /// software-controllable should not have to write a method to say so.
    fn set_psu_led(&mut self, psu: &str, color: LedColor) -> Result<(), PlatformError> {
        let _ = psu;
        let _ = color;
        Err(PlatformError::NotSupported("set_psu_led".to_string()))
    }

    /// Why a module last restarted, asked when it restarts.
    ///
    /// Deliberately not a column of `ModuleInfo`.  A row is built eagerly, so
    /// a column here would be read once per polling cycle -- and on Mellanox
    /// this getter *logs*: `module.py:477,482` emits a NOTICE naming the
    /// reason every time it is called.  As a column it produced 84 identical
    /// NOTICE lines per DPU in a fourteen-minute window on a SmartSwitch, 358
    /// lines where the Python daemon wrote 20, because Python asks only at the
    /// moment a module changes state (`chassisd:896,904`).
    ///
    /// That is not merely noise.  pmon's rsyslog is rate limited, and a flood
    /// of redundant NOTICE spends the budget that a real alarm needs.
    ///
    /// The rule this establishes: a getter with a side effect, or one whose
    /// answer is meaningful per event rather than per cycle, is a method the
    /// caller invokes, not a column the row carries.
    ///
    /// `get_reboot_cause()` answers `(cause, detail)` and both halves are
    /// published; see `ModuleRebootCause` for what taking only the first one
    /// cost, and why the fix is a row rather than a second method.
    ///
    /// Not supported by default: a platform whose get_module_reboot_cause is not
    /// software-controllable should not have to write a method to say so.
    fn get_module_reboot_cause(&mut self, module: &str) -> Result<ModuleRebootCause, PlatformError> {
        let _ = module;
        Err(PlatformError::NotSupported("get_module_reboot_cause".to_string()))
    }

    /// Why a module's midplane went down, asked when it goes down.
    ///
    /// A method rather than a column of `ModuleInfo`, by the rule
    /// `get_module_reboot_cause` states: the answer means something at the
    /// moment of the transition, not on every polling cycle.
    ///
    /// Not supported by default: a platform whose get_module_midplane_down_reason is not
    /// software-controllable should not have to write a method to say so.
    fn get_module_midplane_down_reason(&mut self, module: &str) -> Result<ModuleMidplaneDownReason, PlatformError> {
        let _ = module;
        Err(PlatformError::NotSupported("get_module_midplane_down_reason".to_string()))
    }

    /// The colour of the LED every hot-swappable PSU shares.
    ///
    /// `PsuBase.get_status_master_led` is a `@classmethod` over a class
    /// attribute, so any PSU answers for all of them; the row name is how the
    /// facade reaches an instance to ask.
    ///
    /// Not supported by default: a platform whose get_psu_master_led is not
    /// software-controllable should not have to write a method to say so.
    fn get_psu_master_led(&mut self, psu: &str) -> Result<Option<LedColor>, PlatformError> {
        let _ = psu;
        Err(PlatformError::NotSupported("get_psu_master_led".to_string()))
    }

    /// One LED shared by every hot-swappable PSU.
    ///
    /// Addressed through a PSU row like the getter, and for the same reason:
    /// `set_status_master_led` is a `@classmethod` on `PsuBase`, so any PSU
    /// sets it for all of them -- but it is not on the chassis, and reaching
    /// for it there would fail on every platform.
    ///
    /// Not supported by default: a platform whose set_psu_master_led is not
    /// software-controllable should not have to write a method to say so.
    fn set_psu_master_led(&mut self, psu: &str, color: LedColor) -> Result<(), PlatformError> {
        let _ = psu;
        let _ = color;
        Err(PlatformError::NotSupported("set_psu_master_led".to_string()))
    }

    /// reboot_module
    ///
    /// Not supported by default: a platform whose reboot_module is not
    /// software-controllable should not have to write a method to say so.
    fn reboot_module(&mut self, module: &str, reboot_type: &str) -> Result<(), PlatformError> {
        let _ = module;
        let _ = reboot_type;
        Err(PlatformError::NotSupported("reboot_module".to_string()))
    }

    /// set_module_admin_state
    ///
    /// Not supported by default: a platform whose set_module_admin_state is not
    /// software-controllable should not have to write a method to say so.
    fn set_module_admin_state(&mut self, module: &str, up: bool) -> Result<(), PlatformError> {
        let _ = module;
        let _ = up;
        Err(PlatformError::NotSupported("set_module_admin_state".to_string()))
    }

    /// Admin-down that lets the module's services stop first.
    ///
    /// Separate from `set_module_admin_state` because it blocks for as long
    /// as the halt takes, and a caller polling on a timer needs to know which
    /// of the two it asked for.
    ///
    /// Not supported by default: a platform whose set_module_admin_state_gracefully is not
    /// software-controllable should not have to write a method to say so.
    fn set_module_admin_state_gracefully(&mut self, module: &str, up: bool) -> Result<(), PlatformError> {
        let _ = module;
        let _ = up;
        Err(PlatformError::NotSupported("set_module_admin_state_gracefully".to_string()))
    }

    /// power_cycle_module
    ///
    /// Not supported by default: a platform whose power_cycle_module is not
    /// software-controllable should not have to write a method to say so.
    fn power_cycle_module(&mut self, module: &str) -> Result<(), PlatformError> {
        let _ = module;
        Err(PlatformError::NotSupported("power_cycle_module".to_string()))
    }

    /// module_pre_shutdown
    ///
    /// Not supported by default: a platform whose module_pre_shutdown is not
    /// software-controllable should not have to write a method to say so.
    fn module_pre_shutdown(&mut self, module: &str) -> Result<(), PlatformError> {
        let _ = module;
        Err(PlatformError::NotSupported("module_pre_shutdown".to_string()))
    }

    /// module_post_startup
    ///
    /// Not supported by default: a platform whose module_post_startup is not
    /// software-controllable should not have to write a method to say so.
    fn module_post_startup(&mut self, module: &str) -> Result<(), PlatformError> {
        let _ = module;
        Err(PlatformError::NotSupported("module_post_startup".to_string()))
    }

    /// `pass_key`: the base class takes the module's own name as well.
    ///
    /// Not supported by default: a platform whose set_module_state_transition is not
    /// software-controllable should not have to write a method to say so.
    fn set_module_state_transition(&mut self, module: &str, transition_type: &str) -> Result<(), PlatformError> {
        let _ = module;
        let _ = transition_type;
        Err(PlatformError::NotSupported("set_module_state_transition".to_string()))
    }

    /// clear_module_state_transition
    ///
    /// Not supported by default: a platform whose clear_module_state_transition is not
    /// software-controllable should not have to write a method to say so.
    fn clear_module_state_transition(&mut self, module: &str) -> Result<(), PlatformError> {
        let _ = module;
        Err(PlatformError::NotSupported("clear_module_state_transition".to_string()))
    }

    /// clear_module_gnoi_halt
    ///
    /// Not supported by default: a platform whose clear_module_gnoi_halt is not
    /// software-controllable should not have to write a method to say so.
    fn clear_module_gnoi_halt(&mut self, module: &str) -> Result<(), PlatformError> {
        let _ = module;
        Err(PlatformError::NotSupported("clear_module_gnoi_halt".to_string()))
    }

    /// set_sensor_high_threshold
    ///
    /// Not supported by default: a platform whose set_sensor_high_threshold is not
    /// software-controllable should not have to write a method to say so.
    fn set_sensor_high_threshold(&mut self, sensor: &str, value: Threshold) -> Result<(), PlatformError> {
        let _ = sensor;
        let _ = value;
        Err(PlatformError::NotSupported("set_sensor_high_threshold".to_string()))
    }

    /// set_sensor_low_threshold
    ///
    /// Not supported by default: a platform whose set_sensor_low_threshold is not
    /// software-controllable should not have to write a method to say so.
    fn set_sensor_low_threshold(&mut self, sensor: &str, value: Threshold) -> Result<(), PlatformError> {
        let _ = sensor;
        let _ = value;
        Err(PlatformError::NotSupported("set_sensor_low_threshold".to_string()))
    }

    /// get_available_firmware_version
    ///
    /// Not supported by default: a platform whose get_available_firmware_version is not
    /// software-controllable should not have to write a method to say so.
    fn get_available_firmware_version(&mut self, component: &str, image_path: &str) -> Result<Option<String>, PlatformError> {
        let _ = component;
        let _ = image_path;
        Err(PlatformError::NotSupported("get_available_firmware_version".to_string()))
    }

    /// get_firmware_update_notification
    ///
    /// Not supported by default: a platform whose get_firmware_update_notification is not
    /// software-controllable should not have to write a method to say so.
    fn get_firmware_update_notification(&mut self, component: &str, image_path: &str) -> Result<Option<String>, PlatformError> {
        let _ = component;
        let _ = image_path;
        Err(PlatformError::NotSupported("get_firmware_update_notification".to_string()))
    }

    /// install_firmware
    ///
    /// Not supported by default: a platform whose install_firmware is not
    /// software-controllable should not have to write a method to say so.
    fn install_firmware(&mut self, component: &str, image_path: &str) -> Result<Option<bool>, PlatformError> {
        let _ = component;
        let _ = image_path;
        Err(PlatformError::NotSupported("install_firmware".to_string()))
    }

    /// `ComponentBase.update_firmware` returns False on a missing path and
    /// nothing at all on success, so there is no value worth declaring.
    ///
    /// Not supported by default: a platform whose update_firmware is not
    /// software-controllable should not have to write a method to say so.
    fn update_firmware(&mut self, component: &str, image_path: &str) -> Result<(), PlatformError> {
        let _ = component;
        let _ = image_path;
        Err(PlatformError::NotSupported("update_firmware".to_string()))
    }

    /// Returns one of `ComponentBase.FW_AUTO_*`.
    ///
    /// Not supported by default: a platform whose auto_update_firmware is not
    /// software-controllable should not have to write a method to say so.
    fn auto_update_firmware(&mut self, component: &str, image_path: &str, boot_type: &str) -> Result<Option<i64>, PlatformError> {
        let _ = component;
        let _ = image_path;
        let _ = boot_type;
        Err(PlatformError::NotSupported("auto_update_firmware".to_string()))
    }

    /// Arm, and say for how long it actually armed.
    ///
    /// `WatchdogBase.arm` answers the seconds it settled on, which need not
    /// be the seconds asked for, and -1 on failure.
    ///
    /// Not supported by default: a platform whose arm_watchdog is not
    /// software-controllable should not have to write a method to say so.
    fn arm_watchdog(&mut self, seconds: i64) -> Result<Option<i64>, PlatformError> {
        let _ = seconds;
        Err(PlatformError::NotSupported("arm_watchdog".to_string()))
    }

    /// disarm_watchdog
    ///
    /// Not supported by default: a platform whose disarm_watchdog is not
    /// software-controllable should not have to write a method to say so.
    fn disarm_watchdog(&mut self) -> Result<Option<bool>, PlatformError> {
        Err(PlatformError::NotSupported("disarm_watchdog".to_string()))
    }

    /// The base class spells this `initizalize_system_led`.
    ///
    /// The typo is part of the shipped API, so `Calls` carries it; the facade
    /// does not have to repeat it.
    ///
    /// Not supported by default: a platform whose initialize_system_led is not
    /// software-controllable should not have to write a method to say so.
    fn initialize_system_led(&mut self) -> Result<(), PlatformError> {
        Err(PlatformError::NotSupported("initialize_system_led".to_string()))
    }

    /// init_midplane_switch
    ///
    /// Not supported by default: a platform whose init_midplane_switch is not
    /// software-controllable should not have to write a method to say so.
    fn init_midplane_switch(&mut self) -> Result<(), PlatformError> {
        Err(PlatformError::NotSupported("init_midplane_switch".to_string()))
    }

    /// The whole platform API surface healthd reaches.
    ///
    /// `health_checker/manager.py:77`.  It is not a pmon daemon -- it runs on
    /// the host -- which is why this one method is worth naming.
    ///
    /// Not supported by default: a platform whose set_chassis_led is not
    /// software-controllable should not have to write a method to say so.
    fn set_chassis_led(&mut self, color: LedColor) -> Result<(), PlatformError> {
        let _ = color;
        Err(PlatformError::NotSupported("set_chassis_led".to_string()))
    }

    /// change_sed_password
    ///
    /// Not supported by default: a platform whose change_sed_password is not
    /// software-controllable should not have to write a method to say so.
    fn change_sed_password(&mut self, new_password: &str) -> Result<Option<bool>, PlatformError> {
        let _ = new_password;
        Err(PlatformError::NotSupported("change_sed_password".to_string()))
    }

    /// reset_sed_password
    ///
    /// Not supported by default: a platform whose reset_sed_password is not
    /// software-controllable should not have to write a method to say so.
    fn reset_sed_password(&mut self) -> Result<Option<bool>, PlatformError> {
        Err(PlatformError::NotSupported("reset_sed_password".to_string()))
    }

    /// every BMC command answers a tuple, and not the same tuple: (code, message), (code, (message, (session_id, token))) and (code, (task_id, message)) all appear. Unpacking each into one row shape is a decision per method rather than a rule.
    ///
    /// No default: what this answers has no empty value that is not also a
    /// lie, so a platform that cannot answer has to say so.
    fn bmc_open_session(&mut self) -> Result<BmcResult, PlatformError> {
        Err(PlatformError::NotSupported("bmc_open_session".to_string()))
    }

    /// see bmc_open_session
    ///
    /// No default: what this answers has no empty value that is not also a
    /// lie, so a platform that cannot answer has to say so.
    fn bmc_close_session(&mut self, session_id: &str) -> Result<BmcResult, PlatformError> {
        let _ = session_id;
        Err(PlatformError::NotSupported("bmc_close_session".to_string()))
    }

    /// see bmc_open_session
    ///
    /// No default: what this answers has no empty value that is not also a
    /// lie, so a platform that cannot answer has to say so.
    fn bmc_reset_root_password(&mut self) -> Result<BmcResult, PlatformError> {
        Err(PlatformError::NotSupported("bmc_reset_root_password".to_string()))
    }

    /// see bmc_open_session
    ///
    /// No default: what this answers has no empty value that is not also a
    /// lie, so a platform that cannot answer has to say so.
    fn bmc_reset(&mut self, graceful: bool) -> Result<BmcResult, PlatformError> {
        let _ = graceful;
        Err(PlatformError::NotSupported("bmc_reset".to_string()))
    }

    /// see bmc_open_session
    ///
    /// No default: what this answers has no empty value that is not also a
    /// lie, so a platform that cannot answer has to say so.
    fn bmc_update_firmware(&mut self, image_path: &str) -> Result<BmcResult, PlatformError> {
        let _ = image_path;
        Err(PlatformError::NotSupported("bmc_update_firmware".to_string()))
    }

    /// see bmc_open_session
    ///
    /// No default: what this answers has no empty value that is not also a
    /// lie, so a platform that cannot answer has to say so.
    fn bmc_trigger_debug_log_dump(&mut self) -> Result<BmcResult, PlatformError> {
        Err(PlatformError::NotSupported("bmc_trigger_debug_log_dump".to_string()))
    }

    /// see bmc_open_session
    ///
    /// No default: what this answers has no empty value that is not also a
    /// lie, so a platform that cannot answer has to say so.
    fn bmc_get_debug_log_dump(&mut self, task_id: &str, filename: &str, path: &str) -> Result<BmcResult, PlatformError> {
        let _ = task_id;
        let _ = filename;
        let _ = path;
        Err(PlatformError::NotSupported("bmc_get_debug_log_dump".to_string()))
    }

    /// get_all_asics answers a list of (asic_id, pci_address) tuples rather than a list of device objects, so there is nothing for a flatten plan to call a getter on.
    ///
    /// Empty by default.
    fn get_asics(&mut self) -> Result<Vec<AsicInfo>, PlatformError> {
        Ok(Vec::new())
    }

    /// get_thermal_manager() returns a class, not an instance; its twelve methods are all @classmethod over process-global state, and run_policy takes the chassis back as an argument. The facade holds the chassis and passes it, so these four calls take no arguments and the bridge never re-enters Python...
    ///
    /// A no-op by default: most platforms have no thermal manager, and one
    /// that says so by erroring would have every caller log a warning per
    /// cycle on hardware that is working exactly as designed.
    fn tm_initialize(&mut self) -> Result<(), PlatformError> {
        Ok(())
    }

    /// see tm_initialize
    ///
    /// A no-op by default: most platforms have no thermal manager, and one
    /// that says so by erroring would have every caller log a warning per
    /// cycle on hardware that is working exactly as designed.
    fn tm_run_policy(&mut self) -> Result<(), PlatformError> {
        Ok(())
    }

    /// see tm_initialize
    ///
    /// `None` by default, which is how a platform says it has no answer
    /// rather than that the call failed.
    fn tm_get_interval(&mut self) -> Result<Option<f64>, PlatformError> {
        Ok(None)
    }

    /// see tm_initialize
    ///
    /// A no-op by default: most platforms have no thermal manager, and one
    /// that says so by erroring would have every caller log a warning per
    /// cycle on hardware that is working exactly as designed.
    fn tm_deinitialize(&mut self) -> Result<(), PlatformError> {
        Ok(())
    }

    /// The platform writes this table itself.  `Eeprom.update_eeprom_db()` (sonic_platform_base/sonic_eeprom/eeprom_tlvinfo.py, which every vendor Eeprom subclasses) decodes the raw EEPROM and hmsets EEPROM_INFO through an EepromRedisVisitor: a TlvHeader row, a Checksum row, a State row, and one row...
    ///
    /// No default: what this answers has no empty value that is not also a
    /// lie, so a platform that cannot answer has to say so.
    fn eeprom_update_db(&mut self) -> Result<bool, PlatformError> {
        Err(PlatformError::NotSupported("eeprom_update_db".to_string()))
    }

    /// stormond does not reach the platform through the chassis either: `StorageDevices()` walks /sys/block and picks a utility class per disk, and the object it picks may be None.  The readings are only valid after `fetch_parse_info(/dev/<disk>)` has been called for that disk -- an ordering no column...
    ///
    /// Empty by default.
    fn get_storage_devices(&mut self) -> Result<Vec<StorageDeviceInfo>, PlatformError> {
        Ok(Vec::new())
    }

    /// pcied does not reach the platform through the chassis at all: it constructs `sonic_platform.pcie.Pcie(platform_path)`, or `sonic_platform_base.sonic_pcie.pcie_common.PcieUtil` when the vendor ships none, and that two-step import with a fallback is a decision rather than a call.  The rows are the...
    ///
    /// Empty by default.
    fn get_pcie_devices(&mut self) -> Result<Vec<PcieDevice>, PlatformError> {
        Ok(Vec::new())
    }

    /// Same object as get_pcie_devices, so the same two-step construction; and the answer is a mapping of mappings whose keys are whatever the kernel printed in aer_dev_correctable and its two siblings, which no column list can enumerate.
    ///
    /// Empty by default.
    fn get_pcie_aer_stats(&mut self, bus: i64, dev: i64, func: i64) -> Result<Vec<PcieAerStat>, PlatformError> {
        let _ = bus;
        let _ = dev;
        let _ = func;
        Ok(Vec::new())
    }

    /// get_change_event returns a two-level mapping whose leaf is a stringly-typed enumeration documented only in prose, and whose outer keys vary by platform. Flattening it into rows is mechanical, but deciding that `ok` is data rather than an error is not: ok=False is how a platform reports a...
    ///
    /// No default: what this answers has no empty value that is not also a
    /// lie, so a platform that cannot answer has to say so.
    fn get_change_event(&mut self, timeout_ms: i64) -> Result<ChangeEventBatch, PlatformError> {
        let _ = timeout_ms;
        Err(PlatformError::NotSupported("get_change_event".to_string()))
    }

    /// Release whatever the implementation set up, once, on the way out.
    ///
    /// The one member of this trait that is not a projection of the stub: it
    /// is a lifecycle hook, not a vendor call.  It exists because a daemon
    /// must be able to end without naming the implementation it was given --
    /// the PyO3 bridge has Python `atexit` handlers to run here, a native
    /// implementation has nothing, and `main` should not have to know which
    /// it holds.
    ///
    /// Does nothing by default, so an implementation with no teardown -- and
    /// every test double is one -- says so by staying silent.
    fn finalize(&mut self) {}
}
