//! The base-class methods whose default is code rather than a constant.
//!
//! `object.rs` calls these where `generator/native.py` found a body in
//! `sonic_platform_base`.  Each is that body, ported.  The ones that read
//! instance state a native object keeps itself, and the BMC's, which no
//! native platform reaches yet, fail as not ported rather than guess.

pub mod bmc_base;
pub mod chassis_base;
pub mod fan_base;
pub mod leakage_sensor_base;
pub mod liquid_cooling_base;
pub mod module_base;
pub mod pdb_base;
pub mod psu_base;
pub mod sed_mgmt_base;
pub mod thermal_manager_base;
pub mod tlv_info_decoder;
