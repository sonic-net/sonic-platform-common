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
"""The part of the facade a type alone cannot say.

`facade.pyi` declares what the cross-language platform API looks like.  A type
says a thermal row carries a temperature; it does not say which base-class
method that temperature is read from, in what order rows from four different
places are concatenated, or what a vendor returning the string 'N/A' should
become.  Those are declared here, as arguments to `Annotated[...]` on fields
and to `@platform_method(...)` on methods.

Declarations only: this module has no runtime counterpart and nothing imports
it.  The generator reads `facade.pyi` with `ast` from the standard library --
it never imports the stub and never needs a type checker to run.  The classes
exist so that `mypy --strict` type-checks the metadata itself, which is how a
misspelled base-class path or a malformed flatten plan gets caught.
"""

from dataclasses import dataclass
from typing import Callable, Literal, Optional, TypeVar, Union

# --------------------------------------------------------------------------
# Field-level
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class From:
    """The base-class method this field is read from.

    Written as `Class.method`, e.g. `From("ThermalBase.get_temperature")`.
    The generator emits the call into `facade.py` wrapped in the standard
    not-implemented handling, so a field never needs its own error path.

    This is also what the conformance scan checks a vendor's `sonic_platform`
    against: every path named here must exist on the vendor's object.

    A path may name more than one getter: `"LeakageSensorBase.get_leak_profile
    .get_type"` calls each in turn, which is how a column that lives one
    object further down becomes a column here rather than a second row type.
    Any hop answering None makes the whole field absent.

    `at` picks one slot out of a tuple return.  Several base-class getters
    hand back a fixed-arity tuple -- `get_reboot_cause()` is `(cause, detail)`
    -- and the row carries them as separate columns, because a consumer that
    wanted them together would have to know the arity anyway.
    """

    path: str
    at: Optional[int] = ...

@dataclass(frozen=True)
class Parent:
    """This field carries the parent name the flatten plan resolved.

    The thermal that a PSU owns is published under that PSU's name, not the
    thermal's own; `parent_name` is how a consumer tells two identically named
    sensors apart.  There is no base-class call behind it.
    """

@dataclass(frozen=True)
class WithName:
    """This getter takes the device's own name, so the row must pass it.

    `ModuleBase.get_module_state_transition(self, module_name)`
    (`module_base.py:709`) has always required the name -- this is not a vendor
    narrowing, it is a getter the base class declares with an argument, and a
    `From` that names it reads as a zero-argument column unless this says
    otherwise.  Python passes it: `chassisd:1271` is
    `try_get(module.get_module_state_transition, module_name, default=False)`.

    Declared the plain way, the generated call raised
    `TypeError: get_module_state_transition() missing 1 required positional
    argument: 'module_name'`, which on a SmartSwitch NPU cost the whole
    `ModuleInfo` row: chassisd logged "Failed to read the modules" every cycle
    and published no `CHASSIS_MIDPLANE_TABLE` at all.  Measured on a SmartSwitch.

    The name comes from the same `get_name()` the row's `name` column uses, so
    the argument cannot disagree with the key the row is published under.
    """

@dataclass(frozen=True)
class Narrowed:
    """Vendors may narrow this getter's signature, so calling it can TypeError.

    `ChassisBase.get_dpu_id` is declared `get_dpu_id(self, **kwargs)`, which a
    zero-argument call satisfies.  Mellanox overrides it as
    `get_dpu_id(self, name)` (`chassis.py:1764`) -- a *required* positional --
    so on a SmartSwitch NPU the call raises
    `TypeError: get_dpu_id() missing 1 required positional argument: 'name'`.

    The conformance scan does not catch this: it checks that every path named
    in a `From` exists on the vendor object, not that the arity still matches.

    Why it matters more than one column: the facade builds a row eagerly, so
    every field is read on every call.  Without this, one vendor's narrowed
    signature takes down the whole `ChassisInfo` row, and a caller that only
    wanted `is_smartswitch` gets nothing.  Measured on a SmartSwitch: the Rust
    chassisd read `None` for the row, concluded the platform was a fixed
    switch, and exited "not supported" on a SmartSwitch with four live DPUs.

    Python never hits it because it never makes the call on the NPU --
    `chassisd:1748` is inside `DpuStateUpdater`, which runs only on the DPU,
    where the BlueField `sonic_platform` does take no argument.  Declaring the
    quirk gives the same answer on both: absent on the NPU, the id on the DPU.

    A TypeError becomes an absent field, like `NotImplementedError`.  It is
    deliberately not a global rule in `_call`: everywhere else a TypeError is a
    generator bug, and swallowing those would hide them.
    """

@dataclass(frozen=True)
class Truthy:
    """This field is consumed in a boolean context, so normalise it like one.

    `LeakageSensorBase.is_leak` is declared `bool` and Mellanox returns
    `False`, `True`, or the string `'N/A'` when the sysfs read fails
    (`liquid_cooling.py:46-57`).  The Python daemon never compares it to
    anything -- `thermalctld:676` is a bare `if sensor_is_leak:` -- so `'N/A'`,
    a non-empty string, counts as **leaking**.  Reading the sysfs file is the
    only way to know, and a detector that cannot read its sensor must not
    report the tank is dry.

    Declaring it `Observed(sentinels=('N/A',))` would be the natural-looking
    choice and is wrong: that turns the sentinel into None, None is falsy, and
    a switch with a failed leak sensor reports `leaking=No` while `bmcctld`
    waits for a CRITICAL that never comes.  Measured on slm-111: Python wrote
    `leaking=Yes` / `device_leak_status=CRITICAL`, the sentinel-to-None port
    wrote `No` / `None`.

    The rule: `None` stays absent -- Python's `if None:` is false too -- and
    anything else becomes `bool(value)`.  A real `bool` is unaffected.
    """

@dataclass(frozen=True)
class Observed:
    """The declared type, and what vendors actually return.

    The base class documents `float`.  Vendors return int, str, numpy scalars,
    and sentinels where there is no reading -- `'N/A'` appears in `pdb_base`,
    `sensor_fs` and `xcvr_api` at positions declared as numbers.

    The normalisation happens once, in the generated Python facade: by the time
    a row crosses into Rust the value is already a number or None.  What this
    declaration buys on the Rust side is the type -- `Option<f64>` rather than
    something looser -- and the guarantee that only one implementation of the
    rule exists to disagree with itself.

    `sentinels` become None.  `coerce_from` names the Python types worth
    attempting a conversion from before giving up.
    """

    sentinels: tuple[object, ...] = ...
    coerce_from: tuple[str, ...] = ...

# --------------------------------------------------------------------------
# Flattening: how a row is assembled out of the base-class object tree
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Via:
    """One hop of a flatten plan, when a bare path will not do.

    `single` is for a hop that yields one object rather than a list --
    `ChassisBase.get_liquid_cooling`, `get_watchdog`, `get_bmc`.  Without it
    the generated traversal would iterate the object, which for most of them
    means a TypeError and for a string would mean one row per character.

    A bare string in `via` is this with `single=False`, which is the common
    case and stays readable.
    """

    path: str
    single: bool = ...

@dataclass(frozen=True)
class FlattenSource:
    """One place a row type is collected from.

    Modelled on what the daemons already do, because the generated facade has
    to reproduce their behaviour exactly or the migration is not a migration.
    `thermalctld._collect_thermals` is the worked example for every field
    below (thermalctld:1100-1145).

    from_
        The base-class method yielding the leaf devices, e.g.
        `"PsuBase.get_all_thermals"`.
    mapping
        Instead of `from_`, when the base class answers a mapping rather than
        a list of devices.  `get_system_eeprom_info()` is `{tlv_code: value}`
        and `BMCBase.get_eeprom()` is `{field_name: value}`; both become one
        row per entry, with `sets` naming the columns that take the key and
        the value.  Order is the mapping's own, which on every Python since
        3.7 is insertion order -- the order the platform read them in.
    provider
        Instead of `from_`, when the devices do not come from the base class
        at all: the name of a method on the hand-written `EscapeHatches` that
        yields them.  `sensormond` builds part of its sensor list by handing
        `SensorFs.factory` a *class* and a slab of `sensors.yaml`, which is
        not something a declaration can express -- but the rows it produces
        are ordinary rows, and declaring the source keeps them in the same
        order, with the same columns, as the rest.
    via
        How to walk from the chassis to the owner of `from_`, outermost
        first.  `("ChassisBase.get_all_psus",)` for a PSU's thermals;
        `("ChassisBase.get_all_modules", "ModuleBase.get_all_psus")` for the
        four-hop chassis -> module -> psu -> thermal traversal.
    when
        A predicate called on the innermost `via` object, skipping it when
        false.  `"get_presence"` -- a PSU that is not there has no thermals
        worth publishing.
    when_chassis
        A predicate on the chassis gating the whole source.  Module thermals
        are collected only on `"is_modular_chassis"`.
    parent
        The getter supplying the parent name, normally `"get_name"`.  None
        when the parent is fixed, as it is for the chassis' own thermals.
    parent_default
        Used when `parent` is absent or returns nothing.  A format string
        over `{i}`, the 1-based index at that level, and `{parent}`, the
        enclosing level's already-resolved name.  One per `via` level,
        innermost last, so that the four-hop traversal can spell the module's
        fallback and the PSU's separately -- `("Module {i}", "{parent} PSU
        {i}")` is what reproduces thermalctld's nested naming.  A bare string
        is shorthand for a single level, and for a source with no `via` it is
        the fixed parent name.
    single
        The leaf yields one object rather than a list -- `get_watchdog` does.
        The row list is then of length at most one, which is the honest shape:
        a platform without a watchdog has no row, not a row full of None.
    optional
        The whole source is wrapped in the not-implemented handling rather
        than each call within it.  Set for sources a platform may not have at
        all, such as PDBs on a PSU-based platform.
    reaches
        For a `provider=` source, the base-class methods the hand-written
        provider calls.  Same reason as `EscapeHatch.reaches`.
    sets
        Field values this source fixes, for the fields that say where a row
        came from rather than what a device reported -- `FanInfo.kind`, and
        `PsuInfo.kind` distinguishing a PDB from a PSU.  The value `"@parent"`
        means the parent name this source resolved, which is how a drawer fan
        gets a `drawer_name` and a PSU fan gets `'N/A'`; `"@key"` and
        `"@value"` are the two halves of a `mapping=` entry.
    """

    from_: str = ...
    mapping: Optional[str] = ...
    provider: Optional[str] = ...
    via: tuple[Union[str, Via], ...] = ...
    when: Optional[str] = ...
    when_chassis: Optional[str] = ...
    parent: Optional[str] = ...
    parent_default: Union[str, tuple[str, ...]] = ...
    optional: bool = ...
    single: bool = ...
    reaches: tuple[str, ...] = ...
    sets: tuple[tuple[str, object], ...] = ...

@dataclass(frozen=True)
class Flatten:
    """The ordered set of sources a row type is collected from.

    Order is part of the contract: consumers index published rows positionally
    in places, and the Rust and Python sides have to agree row for row or the
    differential test is meaningless.
    """

    sources: tuple[FlattenSource, ...]

# --------------------------------------------------------------------------
# Method-level
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Unsupported:
    """What a facade field or method does when the base class cannot answer.

    On a field, `default` may be a format string over `{i}` and `{parent}`,
    which is how a row whose device has no name still gets the key its
    consumers already publish it under -- `"{parent} Thermal {i}"`.

    `NotImplementedError` and a `None` return are the same event -- every
    daemon's `try_get()` already treats them alike, and five base-class
    methods muddy it further by writing `return NotImplementedError`, which
    hands back a truthy class object rather than raising.  The facade collapses
    all three into one declared outcome.

    none    -- the field or row becomes None; the ordinary case
    default -- substitute `default`, for the methods whose base-class body is
               already a constant
    error   -- propagate, for the handful where a caller must be able to tell
               "unsupported" from "absent"
    """

    on: Literal["none", "default", "error"] = ...
    default: object = ...

@dataclass(frozen=True)
class On:
    """The row an action addresses, when its first parameter is a row name.

    `set_fan_led("fan 3", "amber")` has to find the fan called "fan 3", which
    means walking the same flatten plan the snapshot walks.  Naming the row
    here is what lets the generator reuse that plan instead of a second
    lookup written by hand.

    Absent for an action on the chassis itself, or on class-level state such
    as the PSU master LED.

    `pass_key` is for the handful of base-class methods that take the device's
    own name as their first argument -- `ModuleBase.set_module_state_transition`
    is called on a module *and* handed that module's name.  Without it the
    locator would be consumed by the lookup and the call would go out one
    argument short.
    """

    row: str
    pass_key: bool = ...

@dataclass(frozen=True)
class Calls:
    """The base-class method an action invokes.

    Written as `Class.method`, like `From`, and like `From` it may name more
    than one hop: `"ChassisBase.get_watchdog.arm"` reaches the watchdog and
    arms it.  Without it an action is a signature with no body and the
    generator has nothing to emit -- which is the difference between an action
    and an `EscapeHatch`.

    `at` picks one slot out of a tuple return, exactly as it does on `From`.
    `ModuleBase.get_reboot_cause()` answers `(cause, detail)` and the caller
    wants the cause.
    """

    path: str
    at: Optional[int] = ...

@dataclass(frozen=True)
class Snapshot:
    """How often the underlying reads happen.

    A method returning a bare row rather than `list[...]` is a singleton: the
    chassis is the device, so there is nothing to flatten and the row carries
    no `ORDER`.

    per_cycle
        Read once per polling cycle and serve every field of every row from
        that. `get_all_sfps()` over 66 modules at 31 fields each is a second
        of work; doing it per field is what makes a flattened API slower than
        the object tree it replaced rather than faster.
    per_call
        Read on each call.  Correct for anything a caller polls precisely
        because it is expected to change.

    `projected` gives the caller a say in which columns are read.

    Batching the crossing is what `per_cycle` buys: one call carries every
    row, instead of one crossing per field per device.  Filling every *column*
    is a separate choice, and it is not free -- the getters run inside the
    facade, at the same cost the object tree paid, for columns the caller may
    throw away.  Measured on a Mellanox switch: psud reads four of FanInfo's
    sixteen columns, but asking for the snapshot ran `is_under_speed`, whose
    Mellanox implementation reads `psu{n}_fan_min`; with the PSU switched off
    that file is readable and empty, so the read logged a ValueError at ERR
    under psud -- a pairing Python cannot produce, because Python's psud never
    makes that call.  psud polls at 3s and thermalctld at 60s, so the port hit
    a pre-existing race twenty times as often, under the wrong identifier.

    A projected snapshot takes a column set and reads only what is in it.
    **Columns outside the set are unspecified, not guaranteed absent**: an
    implementation with no notion of columns -- a native one reading sysfs
    directly -- may fill them anyway and still be correct.  That keeps the
    parameter a hint rather than an obligation, which is what lets the trait
    outlive this Python implementation.
    """

    scope: Literal["per_call", "per_cycle"]
    projected: bool = ...

@dataclass(frozen=True)
class EscapeHatch:
    """This method's body is hand-written in `_escape_hatch.py`.

    Four things in the surface resist mechanical generation and are declared
    rather than derived:

    - `get_thermal_manager()` returns a class, not an instance, whose twelve
      methods are all `@classmethod` over process-global state, and which
      takes the chassis back as an argument.  The facade holds the chassis and
      passes it, so the Rust side sees four argument-less calls and no
      re-entrancy.
    - `get_xcvr_api()` returns common code with 161 public methods on it, and
      seven sites dispatch on its Python type.
    - `SensorFs.factory(sensor_cls, ...)` takes a class as a parameter.
    - `get_change_event()` returns a two-level mapping whose leaf is a
      stringly-typed enumeration documented only in prose.

    `reason` is required: an escape hatch that nobody justified is a method
    somebody gave up on generating.

    `reaches` names the base-class methods the hand-written body calls.  A
    generated body declares what it touches by construction; a hand-written
    one has to say, or the conformance scan stops knowing that a vendor must
    implement it and the coverage report calls it unfinished forever.
    """

    reason: str
    reaches: tuple[str, ...] = ...

@dataclass(frozen=True)
class Rust:
    """The Rust spelling, where the mechanical mapping is not the right one."""

    name: str

F = TypeVar("F", bound=Callable[..., object])

def platform_method(*spec: object) -> Callable[[F], F]:
    """Attach method-level metadata.

    Variadic so that the metadata composes -- a method can carry an
    `Unsupported` and a `Snapshot`, or be an `EscapeHatch`, without a
    combining type per pairing.
    """
