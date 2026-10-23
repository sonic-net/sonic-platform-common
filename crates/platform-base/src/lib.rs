//! `sonic_platform_base` in Rust: what a native platform API is written against.
//!
//! A vendor's Python `sonic_platform` is a tree of objects derived from the
//! base classes, read through `sonic_platform_api/facade.py`.  A native one is
//! the same tree in Rust -- objects implementing [`PyObject`], answering in
//! [`PyVal`] and failing in [`PyErr`] -- read through [`BaseFacade`], which is
//! that facade generated a second time, for Rust.  What the base classes do
//! for a vendor (their default methods, the thermal manager, PCIe and storage
//! checks) is here too, so that a vendor overriding nothing answers what a
//! Python one overriding nothing answers.  The TLV EEPROM decoder is here as
//! well, as a type a vendor's EEPROM object builds on ([`eeprom_tlvinfo`]):
//! its methods read instance state the base class cannot reach.

pub mod atexit;
pub mod bmc;
pub mod bodies;
pub mod db;
pub mod device_info;
pub mod eeprom_tlvinfo;
pub mod escape_hatch;
pub mod facade_rt;
pub mod io;
pub mod json;
pub mod logger;
pub mod multi_asic;
pub mod pcie;
pub mod py;
pub mod redfish_client;
pub mod shlex;
pub mod storage;
pub mod subprocess;
#[cfg(any(test, feature = "testing"))]
pub mod testing;
pub mod yaml;

// The generator's output, held byte for byte to what `generate.py --check`
// regenerates: rustfmt leaves it as written.
#[rustfmt::skip]
mod generated;

pub use generated::facade::{self as facade, BaseFacade};
pub use generated::object::{self as object, defaults, BaseClass, PyObject};
pub use py::{Exc, PyErr, PyResult, PyVal};
