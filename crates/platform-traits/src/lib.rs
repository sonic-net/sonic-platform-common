//
// SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
// Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// Apache-2.0
//

//! Vendor-agnostic platform API traits for SONiC thermal daemons.
//!
//! Every type and trait here corresponds 1-to-1 with the Python platform-API
//! layer.  The Rust implementation for each vendor lives in a separate crate
//! (e.g. `platform-mellanox`) that depends on this one.

// ── Data structures ──────────────────────────────────────────────────────────

/// Threshold value, preserving the original Python type.
///
/// Python's `str(int(105)) == "105"` but `str(float(105.0)) == "105.0"`.
/// Downstream DB readers (e.g. `show platform temperature`) rely on the exact
/// string format, so the int/float distinction must survive the Rust boundary.
#[derive(Debug, Clone, Copy)]
pub enum Threshold {
    /// Originated from a Python `int`. Written to STATE_DB without a decimal
    /// point: e.g. `"105"`.
    Int(i64),
    /// Originated from a Python `float` (or read from a sysfs file). Written
    /// with a decimal point: e.g. `"105.0"`.
    Float(f64),
}

impl Threshold {
    /// Return the threshold value as an f64 for arithmetic comparison.
    pub fn as_f64(self) -> f64 {
        match self {
            Self::Int(v) => v as f64,
            Self::Float(v) => v,
        }
    }
}

/// Thermal sensor reading and metadata.
#[derive(Debug, Clone)]
pub struct ThermalInfo {
    pub name: String,
    /// `"chassis 1"`, PSU name, or transceiver module name.
    pub parent_name: String,
    /// 1-based index within the parent.
    pub position_in_parent: u32,
    /// Temperature in °C; `None` means the sensor is not readable.
    pub temperature: Option<f64>,
    pub high_threshold: Option<Threshold>,
    pub low_threshold: Option<Threshold>,
    pub high_critical_threshold: Option<Threshold>,
    pub low_critical_threshold: Option<Threshold>,
    /// Minimum temperature recorded since daemon start, maintained by the
    /// platform implementation across calls to `get_thermals()`.
    ///
    /// `None` where the platform does not record it, which is what Python's
    /// `ThermalBase.get_minimum_recorded()` raising `NotImplementedError`
    /// means downstream: `thermalctld`'s `try_get` returns `N/A`.  Mellanox is
    /// one such platform; Arista, Celestica, Micas, Ruijie and Ragile are not.
    pub min_recorded: Option<f64>,
    /// Maximum temperature recorded since daemon start.  `None` on the same
    /// terms as [`Self::min_recorded`].
    pub max_recorded: Option<f64>,
    /// Whether the component can be hot-swapped.
    pub is_replaceable: bool,
}

/// Fan role within the chassis.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FanKind {
    Drawer,
    Psu,
    Module,
}

/// Airflow direction.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FanDirection {
    Intake,
    Exhaust,
}

/// Fan reading and metadata.
#[derive(Debug, Clone)]
pub struct FanInfo {
    pub name: String,
    pub kind: FanKind,
    /// Name of the containing drawer, or empty for PSU/Module fans.
    pub drawer_name: String,
    /// Name of the direct parent (drawer, PSU, or module).
    pub parent_name: String,
    /// 1-based index within the parent.
    pub position_in_parent: u32,
    pub presence: bool,
    /// `true` = operating normally, `false` = fault.
    pub status: bool,
    /// 0–100 %.
    pub speed_pct: Option<u32>,
    /// 0–100 %.
    pub target_speed_pct: Option<u32>,
    pub direction: Option<FanDirection>,
    pub is_under_speed: Option<bool>,
    pub is_over_speed: Option<bool>,
    pub is_replaceable: bool,
    pub model: Option<String>,
    pub serial: Option<String>,
    /// Current LED color, re-read after `set_fan_led()` to confirm hardware
    /// applied the requested color.
    pub status_led: Option<String>,
}

/// Fan drawer reading and metadata.
#[derive(Debug, Clone)]
pub struct FanDrawerInfo {
    pub name: String,
    /// 1-based index within chassis.
    pub position_in_parent: u32,
    pub presence: bool,
    /// The drawer's own health, where the platform reports one.
    ///
    /// `None` means it does not, which is what Mellanox does — `DeviceBase`
    /// raises `NotImplementedError` there — and formats as `N/A`, matching
    /// Python's `try_get(fan_drawer.get_status)`.
    pub status: Option<bool>,
    pub is_replaceable: bool,
    pub model: Option<String>,
    pub serial: Option<String>,
    pub status_led: Option<String>,
}

/// Whether a power entity is a PSU or a power distribution board.
///
/// `psud` keeps two lists and publishes them under different key templates —
/// `PSU {n}` and `PDB {n}` (`psud:69-70`) — but reads both through the same
/// accessor names, so one struct carries both and the kind picks the key.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PowerEntityKind {
    Psu,
    Pdb,
}

/// One PSU or PDB, read fresh each cycle.
///
/// Every optional field is `None` exactly where Python returns `None`, which
/// `psud`'s `try_get` turns into `N/A`.  Note that this is a narrower thing
/// than "the file could not be read": Mellanox's `read_int_from_file` defaults
/// to `0`, so a PSU that is powered good but whose sysfs file is missing
/// reports `Some(0.0)` here and `0.0` in Python.  Collapsing the two into
/// `None` would publish `N/A` where Python publishes `0.0`.
#[derive(Debug, Clone, PartialEq)]
pub struct PsuInfo {
    pub name: String,
    pub kind: PowerEntityKind,
    /// 1-based index within the chassis.
    pub position_in_parent: u32,
    pub presence: bool,
    /// Python's `get_powergood_status()`.  Most readings are gated on it: a
    /// PSU that is present but not delivering power reports `None` for its
    /// electrical values rather than a stale or zero reading.
    pub power_good: bool,
    pub is_replaceable: bool,
    /// `None` where the platform does not carry the value, which formats as
    /// `N/A` — the same string Python's literal `'N/A'` produces.
    pub model: Option<String>,
    pub serial: Option<String>,
    pub revision: Option<String>,
    pub status_led: Option<String>,
    /// Output side, in volts / amperes / watts.
    pub voltage: Option<f64>,
    pub current: Option<f64>,
    pub power: Option<f64>,
    /// Input side.
    pub input_voltage: Option<f64>,
    pub input_current: Option<f64>,
    /// Always `None` for a PSU: `PsuBase` defines no input-power accessor, so
    /// there is nothing to report.  A PDB does define `get_input_power()`.
    pub input_power: Option<f64>,
    pub temperature: Option<f64>,
    pub temperature_high_threshold: Option<f64>,
    /// Output-voltage limits, where the hardware advertises them.  A platform
    /// that does not publish a capability file reports `None` for both even
    /// though the min/max files may exist.
    pub voltage_high_threshold: Option<f64>,
    pub voltage_low_threshold: Option<f64>,
    pub maximum_supplied_power: Option<f64>,
    /// Power thresholds derived from ambient temperature rather than read from
    /// a file, so they move as the box heats up.  `psud` re-reads them every
    /// cycle for that reason.
    pub power_warning_suppress_threshold: Option<f64>,
    pub power_critical_threshold: Option<f64>,
}

/// Static chassis metadata.
#[derive(Debug, Clone, Default)]
pub struct ChassisInfo {
    pub is_modular_chassis: bool,
    pub is_smartswitch: bool,
    pub is_dpu: bool,
    pub is_liquid_cooled: bool,
    /// Slot number on a modular chassis, or DPU id on a SmartSwitch DPU.
    ///
    /// `None` where the platform is neither, or where the id does not resolve —
    /// in which case the slot-suffixed table is not written at all.
    pub slot_or_dpu_id: Option<u32>,
}

/// Python's `LeakSeverity`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LeakSeverity {
    Minor,
    Critical,
}

impl LeakSeverity {
    /// The string STATE_DB carries, matching Python's `LeakSeverity.value`.
    pub fn as_str(self) -> &'static str {
        match self {
            LeakSeverity::Minor => "MINOR",
            LeakSeverity::Critical => "CRITICAL",
        }
    }
}

/// One row of `LEAK_PROFILE`.
#[derive(Debug, Clone, PartialEq)]
pub struct LeakProfile {
    pub profile_type: String,
    /// How long a `MINOR` leak may persist before it becomes `CRITICAL`.
    /// `None` means never, which is Python's `inf`.
    pub max_minor_duration_sec: Option<f64>,
}

/// One leak sensor, read fresh each cycle.
#[derive(Debug, Clone, PartialEq)]
pub struct LeakSensorInfo {
    pub name: String,
    /// False when the sensor itself is faulty, which is a different thing from
    /// it reporting a leak.
    pub is_ok: bool,
    pub is_leak: bool,
    /// `None` when the platform reports no severity.
    pub severity: Option<LeakSeverity>,
    /// Key into the profiles from `get_leak_profiles`, for the `MINOR`
    /// escalation timer.
    pub profile_type: Option<String>,
    pub sensor_type: String,
    pub location: String,
}

// ── Error type ────────────────────────────────────────────────────────────────

#[derive(Debug)]
pub enum PlatformError {
    Io(std::io::Error),
    /// The requested operation is not implemented for this platform.
    NotSupported(String),
    Other(String),
}

impl std::fmt::Display for PlatformError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Io(e) => write!(f, "I/O error: {e}"),
            Self::NotSupported(s) => write!(f, "not supported: {s}"),
            Self::Other(s) => write!(f, "{s}"),
        }
    }
}

impl std::error::Error for PlatformError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io(e) => Some(e),
            _ => None,
        }
    }
}

impl From<std::io::Error> for PlatformError {
    fn from(e: std::io::Error) -> Self {
        Self::Io(e)
    }
}

// ── ThermalManager trait ──────────────────────────────────────────────────────

/// Platform-specific thermal management lifecycle.
///
/// Mirrors Python's `ThermalManagerBase`.  Default implementations are no-ops
/// so vendors only need to override what they actually use.
pub trait ThermalManager: Send {
    /// Called once at daemon startup.
    ///
    /// Mellanox: suspends `hw-management-tc` and starts the `ThermalUpdater`
    /// background thread that writes hw-management sysfs files.
    fn initialize(&mut self) -> Result<(), PlatformError> {
        Ok(())
    }

    /// Run the platform's fan-speed policy.
    ///
    /// `platform` is how the policy reads what it is deciding on — Python
    /// passes the chassis for exactly that, and its `run_policy` starts by
    /// collecting thermal information from it
    /// (`thermal_manager_base.py:178-195`).  A policy that could not read the
    /// platform could not be written.
    ///
    /// Mellanox: no-op — fan policy is owned by `hw-management-tc`, and every
    /// Mellanox `thermal_policy.json` ships with no policies in it.
    fn run_policy(&mut self, platform: &mut dyn PlatformApi) -> Result<(), PlatformError> {
        let _ = platform;
        Ok(())
    }

    /// How often [`Self::run_policy`] should run, in seconds.
    ///
    /// Python keeps this on the manager because it comes from the platform's
    /// `thermal_policy.json` rather than from the daemon's command line
    /// (`thermal_manager_base.py:29`, `:155`, `:228`), and it is deliberately
    /// *not* the interval the fan and temperature updaters run at: Python runs
    /// the policy on its own loop, on its own thread.
    ///
    /// 60 is the base class's default, which is what a platform whose file
    /// omits the key gets — Mellanox's every file does.
    fn get_interval(&self) -> f64 {
        60.0
    }

    /// Called at daemon shutdown (after the main loop exits).
    ///
    /// Mellanox: cancels `ThermalUpdater` and restores `hw-management-tc`.
    fn deinitialize(&mut self) {}
}

// ── PlatformApi trait ─────────────────────────────────────────────────────────

/// Full platform chassis API consumed by `thermalctld-rs`.
///
/// All methods are synchronous: sysfs I/O is blocking, and the daemon runs on
/// a `current_thread` Tokio runtime where short blocking calls in each polling
/// cycle are acceptable.
pub trait PlatformApi: Send {
    /// Static chassis metadata (e.g. is_modular, is_liquid_cooled).
    fn chassis_info(&self) -> Result<ChassisInfo, PlatformError>;

    /// All thermal sensors aggregated from chassis, PSU, and SFP modules.
    ///
    /// `&mut self` allows the implementation to update min/max_recorded fields
    /// in-place between polling cycles.
    fn get_thermals(&mut self) -> Result<Vec<ThermalInfo>, PlatformError>;

    /// All fan drawers.
    fn get_fan_drawers(&self) -> Result<Vec<FanDrawerInfo>, PlatformError>;

    /// All fans, flattened across all drawers/PSUs.
    fn get_fans(&self) -> Result<Vec<FanInfo>, PlatformError>;

    /// Set the status LED on a fan or drawer.
    ///
    /// Not supported by default, as [`set_psu_led`](Self::set_psu_led) is: a
    /// platform whose fan LEDs are not software-controllable should not have to
    /// write a method to say so.
    fn set_fan_led(
        &mut self,
        fan_name: &str,
        drawer_name: &str,
        color: &str,
    ) -> Result<(), PlatformError> {
        // Kept on one line: tarpaulin attributes a multi-line `format!` to its
        // first line and reports the argument line as never hit.
        Err(PlatformError::NotSupported(format!("fan LED for {fan_name} in {drawer_name} -> {color}")))
    }

    /// Leak sensor profiles, published once to `LEAK_PROFILE` at start-up.
    ///
    /// Empty by default: a platform without liquid cooling publishes nothing
    /// and the daemon's leak thread never starts.
    fn get_leak_profiles(&self) -> Vec<LeakProfile> {
        Vec::new()
    }

    /// Leak sensors, read once per leak poll.  Empty by default.
    fn get_leak_sensors(&self) -> Vec<LeakSensorInfo> {
        Vec::new()
    }

    /// All PSUs and PDBs, flattened, in `psud`'s publication order: PSUs by
    /// index, then PDBs by index.
    ///
    /// `&mut self` because a platform may cache what it parses — Mellanox
    /// re-reads a PSU's VPD only when the file's mtime changes.  Empty by
    /// default: a platform with no power entities publishes nothing.
    fn get_psus(&mut self) -> Result<Vec<PsuInfo>, PlatformError> {
        Ok(Vec::new())
    }

    /// Set the status LED on a PSU.
    ///
    /// Not supported by default.  Mellanox drives one LED shared by every
    /// hot-swappable PSU, so the colour published back in
    /// [`PsuInfo::status_led`] is the aggregate, not what was just requested.
    fn set_psu_led(&mut self, psu_name: &str, color: &str) -> Result<(), PlatformError> {
        // Kept on one line: tarpaulin attributes a multi-line `format!` to its
        // first line and reports the argument line as never hit.
        Err(PlatformError::NotSupported(format!("status LED for {psu_name} -> {color}")))
    }

    /// Return the platform-specific thermal manager.
    ///
    /// Called once from `main()`.  The returned object is driven by
    /// `Monitor::run()` during each polling cycle.
    fn get_thermal_manager(&self) -> Box<dyn ThermalManager>;
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A platform that implements only what the trait demands, so every default
    /// body below is the one being measured.  This is also the shape a vendor
    /// starts from, which makes the defaults' behaviour part of the contract
    /// rather than an implementation detail.
    struct BareMinimum;

    struct BareManager;
    impl ThermalManager for BareManager {}

    impl PlatformApi for BareMinimum {
        fn chassis_info(&self) -> Result<ChassisInfo, PlatformError> {
            Ok(ChassisInfo::default())
        }
        fn get_thermals(&mut self) -> Result<Vec<ThermalInfo>, PlatformError> {
            Ok(Vec::new())
        }
        fn get_fan_drawers(&self) -> Result<Vec<FanDrawerInfo>, PlatformError> {
            Ok(Vec::new())
        }
        fn get_fans(&self) -> Result<Vec<FanInfo>, PlatformError> {
            Ok(Vec::new())
        }
        fn get_thermal_manager(&self) -> Box<dyn ThermalManager> {
            Box::new(BareManager)
        }
    }

    // ── Threshold ─────────────────────────────────────────────────────────

    /// The int/float distinction exists so the daemon can reproduce Python's
    /// `str()`; arithmetic has to see through it either way.
    #[test]
    fn a_threshold_compares_as_a_number_whichever_python_type_it_came_from() {
        assert_eq!(Threshold::Int(105).as_f64(), 105.0);
        assert_eq!(Threshold::Float(105.0).as_f64(), 105.0);
        assert!(Threshold::Float(104.9).as_f64() < Threshold::Int(105).as_f64());
    }

    // ── LeakSeverity ──────────────────────────────────────────────────────

    /// STATE_DB carries Python's `LeakSeverity.value` verbatim, so these two
    /// strings are a wire format and not a display choice.
    #[test]
    fn leak_severity_spells_itself_the_way_state_db_expects() {
        assert_eq!(LeakSeverity::Minor.as_str(), "MINOR");
        assert_eq!(LeakSeverity::Critical.as_str(), "CRITICAL");
    }

    // ── PlatformError ─────────────────────────────────────────────────────

    #[test]
    fn each_error_says_which_kind_it_is() {
        let io = PlatformError::from(std::io::Error::other("disk gone"));
        assert!(io.to_string().starts_with("I/O error: "));
        assert_eq!(
            PlatformError::NotSupported("PSU status LED".into()).to_string(),
            "not supported: PSU status LED"
        );
        assert_eq!(PlatformError::Other("boom".into()).to_string(), "boom");
    }

    /// Only the I/O variant wraps something; the other two are the end of the
    /// chain, and reporting a source they do not have would loop a caller that
    /// walks it.
    #[test]
    fn only_an_io_error_has_a_source() {
        use std::error::Error;
        let io = PlatformError::from(std::io::Error::other("disk gone"));
        assert!(io.source().is_some());
        assert!(PlatformError::NotSupported("x".into()).source().is_none());
        assert!(PlatformError::Other("x".into()).source().is_none());
    }

    // ── Trait defaults ────────────────────────────────────────────────────

    /// The defaults are how a vendor supports part of the API: a daemon that
    /// reads one gets an empty set and does nothing, rather than an error it
    /// would have to special-case.  This mirrors `ChassisBase`, whose
    /// container accessors return empty lists for the same reason.
    #[test]
    fn unimplemented_accessors_return_nothing_rather_than_failing() {
        let mut p = BareMinimum;
        assert!(p.get_leak_profiles().is_empty());
        assert!(p.get_leak_sensors().is_empty());
        assert!(p.get_psus().unwrap().is_empty());
    }

    /// The defaults that are an error instead of an empty set: a caller asking
    /// to *write* an LED has to learn it did not happen, where a caller reading
    /// a list can simply get none.  Both LED writers behave the same way — an
    /// asymmetry here would make one of them mandatory for a platform that has
    /// neither.
    #[test]
    fn setting_an_led_a_platform_does_not_have_reports_not_supported() {
        let mut p = BareMinimum;
        let err = p.set_psu_led("PSU 1", "green").unwrap_err();
        assert!(matches!(err, PlatformError::NotSupported(_)));
        // The message names both the device and the colour, because it reaches
        // the daemon's log and "not supported" alone does not say what failed.
        assert_eq!(
            err.to_string(),
            "not supported: status LED for PSU 1 -> green"
        );

        let err = p.set_fan_led("fan1", "drawer1", "red").unwrap_err();
        assert!(matches!(err, PlatformError::NotSupported(_)));
        assert_eq!(
            err.to_string(),
            "not supported: fan LED for fan1 in drawer1 -> red"
        );
    }

    /// `ThermalManager`'s lifecycle hooks are all no-ops by default, so a
    /// platform whose fan control lives elsewhere implements none of them.
    #[test]
    fn the_thermal_manager_lifecycle_is_inert_by_default() {
        let mut p = BareMinimum;
        let mut m = p.get_thermal_manager();
        assert!(m.initialize().is_ok());
        assert!(m.run_policy(&mut p).is_ok());
        m.deinitialize();
    }

    /// The policy's interval comes from the platform's `thermal_policy.json`
    /// and not from the daemon's command line, so it lives on the manager.
    /// 60 is `ThermalManagerBase._interval`, which is what a file that omits
    /// the key gets.
    #[test]
    fn the_policy_interval_defaults_to_pythons_sixty_seconds() {
        assert_eq!(BareManager.get_interval(), 60.0);
    }

    /// A policy is handed the platform because that is what it decides on:
    /// Python's `run_policy(chassis)` starts by collecting thermal information
    /// from it, and a policy that could not read the platform could not exist.
    #[test]
    fn a_policy_can_read_the_platform_it_is_deciding_on() {
        struct Reading {
            seen: usize,
        }
        impl ThermalManager for Reading {
            fn run_policy(&mut self, platform: &mut dyn PlatformApi) -> Result<(), PlatformError> {
                self.seen = platform.get_thermals()?.len();
                Ok(())
            }
        }

        let mut p = BareMinimum;
        let mut m = Reading { seen: usize::MAX };
        m.run_policy(&mut p).unwrap();
        assert_eq!(m.seen, 0, "it reached the platform and read an empty set");
    }
}
