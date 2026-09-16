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
//! Phase 1: a Rust daemon reaching a vendor's Python platform API.
//!
//! [`Bridge`] holds one Python object -- the facade -- and nothing else. The
//! per-method bodies are generated; what is written by hand here is the error
//! mapping and the four attribute readers, because those are decisions rather
//! than projections of the stub.

use platform_api::{PlatformError, Threshold};
use pyo3::exceptions::{PyKeyError, PyNotImplementedError};
use pyo3::prelude::*;
use pyo3::types::PyString;

mod generated;

/// A Rust handle on `platform_api.facade.PlatformApi`.
pub struct Bridge {
    facade: Py<PyAny>,
}

impl Bridge {
    /// Build a facade over the vendor's chassis.
    ///
    /// The vendor package is named by the caller rather than imported here:
    /// which `sonic_platform` is installed is a property of the image, and
    /// hard-coding it would stop the conformance suite driving this over a
    /// mock.
    pub fn new(vendor_module: &str) -> Result<Self, PlatformError> {
        Python::with_gil(|py| {
            let chassis = py
                .import(vendor_module)
                .and_then(|m| m.getattr("Platform"))
                .and_then(|p| p.call0())
                .and_then(|p| p.call_method0("get_chassis"))
                .map_err(|e| err(py, e))?;
            let facade = py
                .import("platform_api.facade")
                .and_then(|m| m.getattr("PlatformApi"))
                .and_then(|c| c.call1((chassis,)))
                .map_err(|e| err(py, e))?;
            Ok(Bridge {
                facade: facade.unbind(),
            })
        })
    }

    /// Wrap a facade the caller already has.  Used by the tests, and by
    /// anything that needs a chassis this crate did not construct.
    pub fn from_facade(facade: Py<PyAny>) -> Self {
        Bridge { facade }
    }
}

/// A Python exception, as the platform API spells the same thing.
///
/// `NotImplementedError` is the one that matters: the facade raises it for an
/// action a platform does not implement, and a caller that saw it as a generic
/// backend failure would log an error every polling cycle on hardware that is
/// working exactly as designed.
pub(crate) fn err(py: Python<'_>, e: PyErr) -> PlatformError {
    let text = e.value(py).to_string();
    if e.is_instance_of::<PyNotImplementedError>(py) {
        PlatformError::NotSupported(text)
    } else if e.is_instance_of::<PyKeyError>(py) {
        PlatformError::NotFound(text)
    } else {
        PlatformError::Backend(text)
    }
}

fn attr<'py>(row: &Bound<'py, PyAny>, key: &str) -> Result<Bound<'py, PyAny>, PlatformError> {
    row.getattr(key).map_err(|e| err(row.py(), e))
}

/// A string column, or None.
///
/// The facade has already resolved fallbacks, so a None here means the column
/// is genuinely absent rather than that a name lookup failed.
pub(crate) fn text(row: &Bound<'_, PyAny>, key: &str) -> Result<Option<String>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() {
        return Ok(None);
    }
    let s = v
        .downcast::<PyString>()
        .map_err(|_| PlatformError::Backend(format!("{key} is not a string")))?;
    s.extract()
        .map(Some)
        .map_err(|e| err(row.py(), e))
}

pub(crate) fn flag(row: &Bound<'_, PyAny>, key: &str) -> Result<Option<bool>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() {
        return Ok(None);
    }
    v.extract::<bool>().map(Some).map_err(|e| err(row.py(), e))
}

/// A limit going the other way: Rust to Python.
///
/// A setter that turned every limit into a float would write 105.0 where the
/// caller said 105, and the platform would store what it was given.
pub(crate) fn thr_arg(py: Python<'_>, t: Threshold) -> Py<PyAny> {
    match t {
        Threshold::Int(v) => v.into_pyobject(py).unwrap().into_any().unbind(),
        Threshold::Float(v) => v.into_pyobject(py).unwrap().into_any().unbind(),
    }
}

/// A limit column, keeping the side of `Union[int, float]` it arrived on.
///
/// Checked int-first, and with bools excluded: `bool` is a subclass of `int`
/// in Python, so `isinstance(True, int)` is true and an unguarded read would
/// turn a flag into the threshold `1`.
pub(crate) fn threshold(
    row: &Bound<'_, PyAny>,
    key: &str,
) -> Result<Option<Threshold>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() {
        return Ok(None);
    }
    if v.extract::<bool>().is_err() {
        if let Ok(i) = v.extract::<i64>() {
            return Ok(Some(Threshold::Int(i)));
        }
    }
    v.extract::<f64>()
        .map(|f| Some(Threshold::Float(f)))
        .map_err(|e| err(row.py(), e))
}

/// A column that is a list of rows.
///
/// Takes the reader for the inner row, which is generated, so this stays one
/// function however many nested rows there turn out to be.
pub(crate) fn rows<T>(
    row: &Bound<'_, PyAny>,
    key: &str,
    read: fn(&Bound<'_, PyAny>) -> Result<T, PlatformError>,
) -> Result<Vec<T>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() {
        return Ok(Vec::new());
    }
    let mut out = Vec::new();
    for item in v.try_iter().map_err(|e| err(row.py(), e))? {
        out.push(read(&item.map_err(|e| err(row.py(), e))?)?);
    }
    Ok(out)
}

/// A numeric column, read as f64 whatever the platform returned.
///
/// The base classes document float and vendors return int as readily; the
/// generator casts back to the declared width afterwards. Reading as f64 here
/// rather than asking for the narrow type is what stops a platform reporting
/// a whole-number speed as `50.0` from failing extraction.
pub(crate) fn num(row: &Bound<'_, PyAny>, key: &str) -> Result<Option<f64>, PlatformError> {
    let v = attr(row, key)?;
    if v.is_none() {
        return Ok(None);
    }
    v.extract::<f64>().map(Some).map_err(|e| err(row.py(), e))
}
