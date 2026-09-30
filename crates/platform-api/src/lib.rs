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
//! Everything in [`generated`] comes from `platform_api/facade.pyi`, with two
//! exceptions: the error type below, and [`PlatformApi::finalize`], which the
//! trait template appends because a lifecycle hook has no place in a stub of
//! vendor calls.

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

#[cfg(test)]
mod tests {
    //! The generated column sets, exercised at run time.
    //!
    //! `FanInfoCols::DIRECTION.with(..)` in a daemon is a `const` expression:
    //! rustc folds it at compile time, so `-C instrument-coverage` records the
    //! function as never executed and the behaviour as never checked.  These
    //! call the same functions from a run-time context, which is the only way
    //! a wrong bit or a wrong name gets caught.

    use crate::{FanInfoCol, FanInfoCols, ModuleInfoCol, ModuleInfoCols};

    #[test]
    fn a_column_set_holds_exactly_the_columns_put_in_it() {
        let cols = FanInfoCols::of(FanInfoCol::SpeedPct).with(FanInfoCols::STATUS_LED);
        assert!(cols.contains(FanInfoCol::SpeedPct));
        assert!(cols.contains(FanInfoCol::StatusLed));
        assert!(!cols.contains(FanInfoCol::IsUnderSpeed));
        assert_eq!(cols.bits().count_ones(), 2);
    }

    #[test]
    fn all_is_every_column_and_none_is_no_column() {
        assert_eq!(
            FanInfoCols::ALL.bits().count_ones() as usize,
            FanInfoCol::ALL.len(),
            "ALL and the column list disagree about how many there are"
        );
        for col in FanInfoCol::ALL {
            assert!(FanInfoCols::ALL.contains(*col), "{} missing from ALL", col.as_str());
            assert!(!FanInfoCols::NONE.contains(*col));
        }
    }

    #[test]
    fn a_column_bit_is_its_declared_position() {
        // The discriminant is the wire format the facade reads: a column that
        // moved would still compile and would read a different column's value.
        assert_eq!(FanInfoCol::PositionInParent.bit(), 1);
        assert_eq!(FanInfoCol::IsUnderSpeed as u8, 9);
        assert_eq!(FanInfoCol::IsUnderSpeed.bit(), 1 << 9);
    }

    #[test]
    fn a_column_set_says_which_columns_it_holds() {
        // `Debug` exists so a projection in a log line can be read.  Printing
        // the number would say nothing the reader could act on.
        let cols = FanInfoCols::of(FanInfoCol::Direction).with(FanInfoCols::SPEED_PCT);
        // The names are the Python spelling, which is what a log line has to
        // be greppable against.
        assert_eq!(format!("{cols:?}"), "FanInfoCols[speed_pct|direction]");
        assert_eq!(format!("{:?}", FanInfoCols::NONE), "FanInfoCols[]");
    }

    #[test]
    fn every_column_names_itself() {
        // `as_str` is otherwise only reached from an assertion message, so it
        // is never run while the tests pass -- and a wrong name there is a
        // wrong name in whatever diagnosis it was written for.
        assert_eq!(FanInfoCol::IsOverSpeed.as_str(), "is_over_speed");
        assert_eq!(ModuleInfoCol::MidplaneIp.as_str(), "midplane_ip");
        for col in ModuleInfoCol::ALL {
            assert!(!col.as_str().is_empty());
            assert!(ModuleInfoCols::of(*col).contains(*col));
        }
    }

    /// A trait method a platform does not implement says so, and says which:
    /// the default is what every implementation without the answer inherits,
    /// and a caller tells "not implemented" from a failure by it.
    #[test]
    fn a_threshold_compares_as_a_float_whichever_python_returned() {
        assert_eq!(crate::Threshold::Int(105).as_f64(), 105.0);
        assert_eq!(crate::Threshold::Float(105.5).as_f64(), 105.5);
    }

    #[test]
    fn an_error_says_which_kind_of_failure_it_is() {
        use crate::PlatformError::{Backend, NotFound, NotSupported};
        assert_eq!(NotSupported("get_fans".into()).to_string(), "not supported: get_fans");
        assert_eq!(NotFound("PSU 9".into()).to_string(), "not found: PSU 9");
        assert_eq!(Backend("EIO".into()).to_string(), "platform error: EIO");
    }

    #[test]
    fn a_platform_that_cannot_say_why_a_midplane_went_down_is_not_supported() {
        struct Nothing;
        impl crate::PlatformApi for Nothing {}
        match crate::PlatformApi::get_module_midplane_down_reason(&mut Nothing, "DPU0") {
            Err(crate::PlatformError::NotSupported(what)) => {
                assert_eq!(what, "get_module_midplane_down_reason")
            }
            other => panic!("expected NotSupported, got {other:?}"),
        }
    }
}
