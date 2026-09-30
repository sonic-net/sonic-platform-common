#
# SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
# Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Units, so that a reader of the facade knows what a bare number means.

These are aliases, not new types: the base classes return plain numbers and
the facade does not wrap them.  What the alias buys is that `get_voltage`
returning `Volt` and `get_speed` returning `Percent` no longer read alike, and
that the generator has a name to hang a Rust type on.

Optionality is deliberately NOT folded into these aliases.  Almost every
facade field is `Optional[...]`, because every daemon's `try_get()` treats a
`None` return from the base class as "not implemented" exactly as it treats
`NotImplementedError` (thermalctld:104, psud:272, chassisd:183,
sensormond:36, bmcctld:297).  Writing that `Optional` out at each field keeps
the stub honest about what the generated code returns -- if the alias hid it,
`stubtest` would be comparing against a type nobody wrote down.
"""

from typing import Union

# Temperature, in degrees Celsius.
Celsius = float

# A temperature or voltage limit.  Vendors return int here as often as float,
# and the difference is outside what `stubtest` can check -- it verifies shape,
# not types.  The union is the honest declaration.
Threshold = Union[int, float]

# Fan speed as a percentage of maximum, 0-100.
Percent = int

# Fan speed in revolutions per minute.
Rpm = int

Watt = float
Volt = float
Ampere = float

# 1-based position of a device within its parent; -1 when unknown.
PositionInParent = int

# 0-based selector accepted by the indexed base-class accessors.  The facade
# addresses rows by name instead, so this appears only in the ABC mirror --
# where the parameter must keep the name `index`, because the conformance
# suite's server dispatches on that name through inspect.signature().
Index = int

Count = int
