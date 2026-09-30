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
//! Opening the platform API, without naming which implementation.
//!
//! A daemon asks for a platform and is handed one.  It never writes
//! `platform_pyo3::Bridge`, which is what lets a second implementation arrive
//! without a daemon changing: the arms live in [`generated`], the choice lives
//! in [`open`], and both are here.
//!
//! Two separate questions, deliberately not collapsed into one:
//!
//! * **Is an implementation available?**  A build-time fact -- an
//!   implementation is a crate, and crates are chosen when the binary is
//!   built.  Answered by the `platform-native` feature.
//! * **Which one should this daemon use?**  A run-time choice, answered by
//!   [`PlatformImpl`] and ultimately by `platform_api_<daemon>` in
//!   `pmon_daemon_control.json`.
//!
//! Collapsing them -- "it is compiled in, so use it" -- is the shape of a bug
//! this tree has already had once: `rules/docker-platform-monitor.mk` adds the
//! Rust daemon debs to every image, and a supervisord template that read an
//! absent key as "yes" would have started six never-before-run arm64 daemons
//! on BlueField.  Availability is not permission.

use std::fmt;
use std::str::FromStr;

use platform_api::PlatformError;

mod generated;

pub use generated::Platform;

/// Which implementation to open.
///
/// Only `FromStr`, not a derived `clap::ValueEnum`: clap's `value_parser!`
/// falls back to `FromStr`, so a daemon still gets `--platform-api native`
/// parsed and rejected for it, and this crate does not take a dependency on a
/// command-line library to say which implementations exist.
///
/// A third implementation is a variant here.  Every daemon accepts it the day
/// it is added, having never mentioned any of them.
#[derive(Copy, Clone, Debug, Default, PartialEq, Eq)]
pub enum PlatformImpl {
    /// The vendor's Python, reached through PyO3.  The default because it is
    /// what every platform runs today, and an unset switch has to mean the
    /// implementation a platform has always had.
    #[default]
    Pyo3,
    /// A native Rust implementation.
    Native,
}

impl PlatformImpl {
    /// The spelling `pmon_daemon_control.json` uses.
    pub fn as_str(&self) -> &'static str {
        match self {
            PlatformImpl::Pyo3 => "pyo3",
            PlatformImpl::Native => "native",
        }
    }
}

impl fmt::Display for PlatformImpl {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

impl FromStr for PlatformImpl {
    type Err = String;

    /// The error text reaches an operator by way of a daemon that refused to
    /// start, so it names what was given and what is accepted rather than
    /// saying "invalid value".
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "pyo3" => Ok(PlatformImpl::Pyo3),
            "native" => Ok(PlatformImpl::Native),
            other => Err(format!(
                "`{other}` is not a platform API implementation; expected `pyo3` or `native`"
            )),
        }
    }
}

/// The Python module a vendor ships its platform API in.
///
/// One copy here rather than an identical `const VENDOR_MODULE` in each of six
/// daemons, which had to agree and had nothing making them.  Only the PyO3 arm
/// has any use for it, and the bridge still takes it as an argument, so
/// `platform-pyo3/tests/bridge_test.rs` can still point it at a mock.
const VENDOR_MODULE: &str = "sonic_platform.platform";

/// Open the platform the daemon was told to use.
///
/// `syslog_ident` is who is asking.  The PyO3 arm makes it `sys.argv[0]`,
/// which is where `sonic_py_common.logger.Logger` takes its syslog tag from --
/// without it every line the vendor's Python logs arrives tagged `pmon#:`, and
/// sonic-mgmt's loganalyzer, which matches `pmon#<daemon>`, sees none of them.
///
/// Callable more than once per process and off the main thread: thermalctld's
/// leak updater and chassisd's CONFIG_DB watcher each open their own, because
/// the poll loop holds the first one mutably. Any implementation put behind
/// this function has to keep that true.
pub fn open(syslog_ident: &str, which: PlatformImpl) -> Result<Platform, PlatformError> {
    match which {
        PlatformImpl::Pyo3 => Ok(Platform::Pyo3(platform_pyo3::Bridge::new(
            VENDOR_MODULE,
            syslog_ident,
        )?)),

        #[cfg(feature = "platform-native")]
        PlatformImpl::Native => Ok(Platform::Native(platform_native::Platform::new(
            syslog_ident,
        )?)),

        // The switch named an implementation this build does not carry.  Say
        // so and stop: quietly falling back to the bridge would make a
        // rollout that did not happen look like one that did, and nothing in
        // pmon notices a daemon running the wrong thing -- `critical_processes`
        // is empty, so no checker reads it.
        #[cfg(not(feature = "platform-native"))]
        PlatformImpl::Native => Err(PlatformError::NotSupported(
            "the native platform API is not compiled into this build".to_string(),
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_switch_accepts_the_spellings_the_device_profile_uses() {
        assert_eq!("pyo3".parse(), Ok(PlatformImpl::Pyo3));
        assert_eq!("native".parse(), Ok(PlatformImpl::Native));
    }

    #[test]
    fn an_unknown_spelling_names_itself_and_the_alternatives() {
        // This text is what an operator sees when a device profile has a typo
        // and the daemon will not start, so it has to carry both halves.
        let e = "pyO3".parse::<PlatformImpl>().unwrap_err();
        assert!(e.contains("pyO3"), "{e}");
        assert!(e.contains("pyo3") && e.contains("native"), "{e}");
    }

    #[test]
    fn the_default_is_the_implementation_every_platform_already_runs() {
        // An absent `platform_api_<daemon>` key has to leave a platform on
        // what it has always run.  The clap default and this must agree.
        assert_eq!(PlatformImpl::default(), PlatformImpl::Pyo3);
        assert_eq!(PlatformImpl::default().as_str(), "pyo3");
    }

    #[test]
    fn display_round_trips_through_from_str() {
        for w in [PlatformImpl::Pyo3, PlatformImpl::Native] {
            assert_eq!(w.to_string().parse(), Ok(w));
        }
    }

    /// The vendor module `open` reaches for, with the two attributes
    /// `Bridge::new` walks -- `Platform().get_chassis()` -- and nothing else.
    /// Installed into `sys.modules` under the name the const names, which is
    /// how a test container with no `sonic_platform` package still exercises
    /// the arm every switch actually runs.
    const VENDOR_STUB: &std::ffi::CStr = pyo3::ffi::c_str!(
        r#"
class Chassis:
    pass

class Platform:
    def get_chassis(self):
        return Chassis()
"#
    );

    /// The arm every platform runs today.  Until this existed the only tested
    /// path through `open` was the one that refuses, which is the arm no
    /// build currently takes.
    #[test]
    fn opening_the_pyo3_implementation_reaches_the_vendor_and_names_the_caller() {
        use pyo3::prelude::*;

        Python::with_gil(|py| {
            let m = pyo3::types::PyModule::from_code(
                py,
                VENDOR_STUB,
                pyo3::ffi::c_str!("platform.py"),
                pyo3::ffi::c_str!("sonic_platform.platform"),
            )
            .unwrap();
            let modules = py.import("sys").unwrap().getattr("modules").unwrap();
            // The parent package as well as the module: `VENDOR_MODULE` is
            // dotted, and Python imports `sonic_platform` before it will look
            // at `sonic_platform.platform`, however thoroughly the child is
            // already in `sys.modules`.
            let pkg = pyo3::types::PyModule::new(py, "sonic_platform").unwrap();
            pkg.setattr("platform", &m).unwrap();
            modules.set_item("sonic_platform", &pkg).unwrap();
            modules.set_item(VENDOR_MODULE, &m).unwrap();
        });

        let p = open("thermalctld", PlatformImpl::Pyo3)
            .expect("PYTHONPATH must include the repository root, for platform_api.facade");
        assert!(matches!(p, Platform::Pyo3(_)));

        // Not incidental: `sonic_py_common.logger.Logger` takes its syslog tag
        // from `sys.argv[0]`, so this is the difference between the vendor's
        // Python logging as `pmon#thermalctld` and logging as `pmon#`, which
        // sonic-mgmt's loganalyzer does not match.
        Python::with_gil(|py| {
            let argv: Vec<String> = py
                .import("sys")
                .unwrap()
                .getattr("argv")
                .unwrap()
                .extract()
                .unwrap();
            assert_eq!(argv, ["thermalctld"]);
        });
    }

    /// Asking for an implementation this build does not carry is an error, not
    /// a silent fall back to the other one.
    #[test]
    #[cfg(not(feature = "platform-native"))]
    fn asking_for_native_without_it_compiled_in_is_refused() {
        match open("thermalctld", PlatformImpl::Native) {
            Err(PlatformError::NotSupported(m)) => {
                assert!(m.contains("not compiled into this build"), "{m}")
            }
            Err(e) => panic!("expected NotSupported, got {e:?}"),
            Ok(_) => panic!("opened a platform this build does not carry"),
        }
    }
}
