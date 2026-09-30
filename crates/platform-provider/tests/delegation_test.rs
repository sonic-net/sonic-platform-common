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
//! That the enum reaches a real facade, and gets a real answer back.
//!
//! `generated_sweep.rs` calls every forwarder against a facade that records
//! and refuses; it proves each arm passes its arguments on, and nothing about
//! what comes back.  These four go the other way: a genuine
//! `platform_api.facade.PlatformApi` over a mock chassis, so an answer is
//! built, converted, and has to survive the extra layer the enum adds.  One
//! of each shape is enough for that, because the shape is what the return
//! conversion depends on -- a `Vec`, a single row, an action, and `finalize`,
//! which is hand-written rather than generated and is the one arm no other
//! test would notice losing.
//!
//! Requires `PYTHONPATH` to include the repository root, so that
//! `platform_api.facade` imports; see generator/check.sh.

use platform_api::{ChassisInfoCols, FanInfoCols, LedColor, PlatformApi};
use platform_provider::Platform;
use pyo3::ffi::c_str;
use pyo3::prelude::*;
use pyo3::types::PyModule;

/// The smallest chassis the facade will talk to: one drawer holding one fan
/// that can be named and lit.  The drawer is not decoration -- the facade
/// reaches fans through `get_all_fan_drawers`, never off the chassis directly
/// (`facade.py:_walk_fan_info`).  Everything else a reader asks for is absent,
/// which the facade already turns into `None`; that path is platform-pyo3's to
/// test, not this crate's.
const MOCK: &std::ffi::CStr = c_str!(
    r#"
class Fan:
    def __init__(self, name):
        self.name = name
        self.led = None
    def get_name(self):
        return self.name
    def set_status_led(self, color):
        self.led = color
        return True

class Drawer:
    def __init__(self, name, fans):
        self.name = name
        self.fans = fans
    def get_name(self):
        return self.name
    def get_all_fans(self):
        return self.fans

class Chassis:
    def __init__(self):
        self.fan = Fan('fan 1')
        self.drawer = Drawer('drawer 1', [self.fan])
    def get_all_fan_drawers(self):
        return [self.drawer]

CHASSIS = Chassis()
"#
);

/// A `Platform::Pyo3` over the mock, plus the chassis so a test can look at
/// what an action did to it.
fn platform() -> (Platform, Py<PyAny>) {
    Python::with_gil(|py| {
        let m = PyModule::from_code(py, MOCK, c_str!("mock.py"), c_str!("mock")).unwrap();
        let chassis = m.getattr("CHASSIS").unwrap();
        let facade = py
            .import("platform_api.facade")
            .expect("PYTHONPATH must include the repository root")
            .getattr("PlatformApi")
            .unwrap()
            .call1((&chassis,))
            .unwrap();
        (
            Platform::Pyo3(platform_pyo3::Bridge::from_facade(facade.unbind())),
            chassis.unbind(),
        )
    })
}

/// A snapshot that returns rows: the answer has to come back through the enum,
/// not be swallowed by it.
#[test]
fn a_list_snapshot_reaches_the_implementation() {
    let (mut p, _chassis) = platform();
    let fans = p.get_fans(FanInfoCols::ALL).expect("the mock has a fan");
    assert_eq!(fans.len(), 1, "one fan in, one fan out");
    assert_eq!(fans[0].name, "fan 1");
}

/// A singleton snapshot: a different template branch from the list above,
/// because the generator emits `Row` rather than `Vec<Row>`.
#[test]
fn a_singleton_snapshot_reaches_the_implementation() {
    let (mut p, _chassis) = platform();
    p.get_chassis_info(ChassisInfoCols::ALL)
        .expect("a chassis that answers nothing still describes itself");
}

/// An action with arguments: the one shape where a wrong forwarder could pass
/// the parameters in the wrong order and still compile, since both are named.
#[test]
fn an_action_carries_its_arguments_through() {
    let (mut p, chassis) = platform();
    p.set_fan_led("fan 1", LedColor::Green)
        .expect("the mock fan takes a colour");
    Python::with_gil(|py| {
        let led = chassis
            .bind(py)
            .getattr("fan")
            .unwrap()
            .getattr("led")
            .unwrap();
        assert_eq!(
            led.extract::<String>().unwrap(),
            "green",
            "the colour the caller asked for has to be the colour the fan got"
        );
    });
}

/// The hand-written arm.  `finalize` is not projected from the stub, so it is
/// the one method whose forwarding no other test would notice losing.
#[test]
fn finalize_reaches_the_implementation() {
    let (mut p, _chassis) = platform();
    Python::with_gil(|py| {
        let m = PyModule::from_code(
            py,
            c_str!(
                "import atexit\n\
                 RAN = []\n\
                 atexit.register(lambda: RAN.append(1))\n"
            ),
            c_str!("provider_cleanup.py"),
            c_str!("provider_cleanup"),
        )
        .unwrap();
        assert_eq!(m.getattr("RAN").unwrap().len().unwrap(), 0);
        p.finalize();
        assert_eq!(
            m.getattr("RAN").unwrap().len().unwrap(),
            1,
            "the vendor's atexit cleanup has to survive the extra layer"
        );
    });
}
