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
//! The SONiC platform API as Rust sees it.
//!
//! Everything in [`generated`] comes from `platform_api/facade.pyi`; only the
//! error type below is written by hand, because it is the one thing that is
//! not a projection of the stub.

mod generated;

pub use generated::*;

/// A temperature or voltage limit, remembering whether Python said int or float.
///
/// `types.pyi` declares `Threshold = Union[int, float]` because vendors return
/// both, and that union is not decoration: `show platform temperature` reads
/// these back out of STATE_DB as strings, so `105` and `105.0` are different
/// answers. Collapsing the union to f64 at the boundary would rewrite one as
/// the other on every platform that reports integral limits.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Threshold {
    /// A Python `int`. Written without a decimal point: `"105"`.
    Int(i64),
    /// A Python `float`. Written with one: `"105.0"`.
    Float(f64),
}

impl Threshold {
    /// The value as f64, for comparison rather than for display.
    pub fn as_f64(self) -> f64 {
        match self {
            Threshold::Int(v) => v as f64,
            Threshold::Float(v) => v,
        }
    }
}

/// Why a platform call did not produce an answer.
///
/// The Python API cannot express this distinction: there, a getter that raises
/// `NotImplementedError` and one that returns `None` are the same event, and
/// every daemon's `try_get()` collapses them. Keeping them apart here is what
/// lets a caller tell "this platform has no PSU LED" from "the PSU LED is off".
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PlatformError {
    /// The platform does not implement this.  Not an error to log loudly:
    /// most of the base class is unimplemented on most platforms.
    NotSupported(String),
    /// A row was addressed by a name no row has.
    NotFound(String),
    /// The platform tried and failed -- an I/O error, a malformed reading, or
    /// an exception the backend did not expect.
    Backend(String),
}

impl std::fmt::Display for PlatformError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PlatformError::NotSupported(what) => write!(f, "not supported: {what}"),
            PlatformError::NotFound(what) => write!(f, "not found: {what}"),
            PlatformError::Backend(what) => write!(f, "platform error: {what}"),
        }
    }
}

impl std::error::Error for PlatformError {}
