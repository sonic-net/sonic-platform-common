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
"""The cross-language platform API.

This stub is the source of truth.  Three things are generated from it and none
may be hand-edited:

    facade.py                           the Python implementation, which walks
                                        the vendor's existing base-class object
                                        tree and returns these rows
    crates/platform-pyo3/src/           the PyO3 bridge, which lets a Rust
                                        daemon call facade.py
    crates/platform-api/src/            the pure Rust trait and structs, which
                                        a vendor implements natively later

The shape is rows and actions, not an object tree.  The base classes hand back
objects -- 62 methods return one -- and a daemon polling them crosses the
language boundary once per attribute of per device.  A row crosses once for the
whole batch, carries no handle, and takes no callback, so the bridge needs
neither shared ownership nor re-entrancy.

Rows are addressed by name rather than by index.  The indexed base-class
accessors are 0-based in some places and 1-based in others, and return None
rather than raising when the index is out of range.

Scope is the union of what the four consumer groups actually reach -- the ten
PMON daemons, healthd, the CLI and the conformance suite.  `generator/
inventory.json` records that union and is what this file is checked against.

Not everything here is derived.  Four methods are `EscapeHatch`; see meta.pyi.

Status: thermal / fan / fan drawer / power slice.  Chassis, module, sensor,
component, SFP and leak rows follow the same pattern and are not yet written.
"""

from typing import Annotated, ClassVar, Final, Literal, Optional

from .meta import (
    Calls,
    EscapeHatch,
    Flatten,
    FlattenSource,
    From,
    Observed,
    On,
    Parent,
    Snapshot,
    Unsupported,
    Via,
    platform_method,
)
from .types import (
    Ampere,
    Celsius,
    PositionInParent,
    Percent,
    Threshold,
    Volt,
    Watt,
)

# A reading that is absent rather than zero.  Vendors spell it this way at
# positions the base class declares as numbers, so it is normalised to None --
# except on `FanInfo.direction`, where 'N/A' is a value and not a sentinel
# (`FanBase.FAN_DIRECTION_NOT_APPLICABLE`).
_MISSING: Observed = Observed(sentinels=("N/A",), coerce_from=("int", "str"))

LedColor = Literal["green", "amber", "red", "off"]
FanDirection = Literal["intake", "exhaust", "N/A"]
FanKind = Literal["drawer", "module", "psu"]
PowerEntityKind = Literal["psu", "pdb"]

# ModuleBase.MODULE_TYPE_*; the strings the base class defines, not new ones.
ModuleType = Literal["SUPERVISOR", "LINE-CARD", "FABRIC-CARD", "DPU", "SWITCH-HOST"]
# ModuleBase.MODULE_STATUS_*.
ModuleStatus = Literal["Empty", "Offline", "PoweredDown", "Present", "Fault", "Online"]
SensorKind = Literal["voltage", "current"]
# LeakageSensorBase.LEAK_SEVERITY_*; the enum member names, as strings.
LeakSeverity = Literal["MINOR", "CRITICAL"]

# The seven status strings `ChassisBase.get_change_event` documents, named.
# The base class describes them only in prose, as '0' through '6'.
ChangeEventKind = Literal[
    "removed",             # '0'
    "inserted",            # '1'
    "i2c_stuck",           # '2'
    "bad_eeprom",          # '3'
    "unsupported_cable",   # '4'
    "high_temperature",    # '5'
    "bad_cable",           # '6'
]

# --------------------------------------------------------------------------
# Rows
# --------------------------------------------------------------------------

class ThermalInfo:
    """One temperature sensor, wherever in the tree it is mounted."""

    name: Annotated[
        str,
        From("DeviceBase.get_name"),
        Unsupported(on="default", default="{parent} Thermal {i}"),
    ]
    parent_name: Annotated[str, Parent()]
    position_in_parent: Annotated[
        PositionInParent, From("DeviceBase.get_position_in_parent"),
        Unsupported(on="default", default=-1),
    ]
    is_replaceable: Annotated[
        bool, From("DeviceBase.is_replaceable"), Unsupported(on="default", default=False),
    ]

    temperature: Annotated[Optional[Celsius], From("ThermalBase.get_temperature"), _MISSING]
    high_threshold: Annotated[
        Optional[Threshold], From("ThermalBase.get_high_threshold"), _MISSING
    ]
    low_threshold: Annotated[
        Optional[Threshold], From("ThermalBase.get_low_threshold"), _MISSING
    ]
    high_critical_threshold: Annotated[
        Optional[Threshold], From("ThermalBase.get_high_critical_threshold"), _MISSING
    ]
    low_critical_threshold: Annotated[
        Optional[Threshold], From("ThermalBase.get_low_critical_threshold"), _MISSING
    ]
    min_recorded: Annotated[
        Optional[Celsius], From("ThermalBase.get_minimum_recorded"), _MISSING
    ]
    max_recorded: Annotated[
        Optional[Celsius], From("ThermalBase.get_maximum_recorded"), _MISSING
    ]

    # Order reproduces thermalctld._collect_thermals (thermalctld:1100-1145).
    # A PSU that is not present contributes nothing; the PDB source is absent
    # rather than empty on a PSU-based platform; module thermals exist only on
    # a modular chassis.
    def __init__(self, **fields: object) -> None:
        """Keyword-only.  The columns are the fields declared above; naming
        them again in a signature would be the one list written twice."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                "ChassisBase.get_all_thermals",
                parent_default="chassis 1",
            ),
            FlattenSource(
                "PsuBase.get_all_thermals",
                via=("ChassisBase.get_all_psus",),
                when="get_presence",
                parent="get_name",
                parent_default="PSU {i}",
            ),
            FlattenSource(
                "PdbBase.get_all_thermals",
                via=("ChassisBase.get_all_pdbs",),
                when="get_presence",
                parent="get_name",
                parent_default="PDB {i}",
                optional=True,
            ),
            FlattenSource(
                "ModuleBase.get_all_thermals",
                via=("ChassisBase.get_all_modules",),
                when_chassis="is_modular_chassis",
                parent="get_name",
                parent_default="Module {i}",
            ),
            FlattenSource(
                "PsuBase.get_all_thermals",
                via=("ChassisBase.get_all_modules", "ModuleBase.get_all_psus"),
                when="get_presence",
                when_chassis="is_modular_chassis",
                parent="get_name",
                parent_default=("Module {i}", "{parent} PSU {i}"),
            ),
        )
    )

class FanInfo:
    """One fan.  `kind` says where it is mounted, which is what decides
    whether `drawer_name` means anything."""

    name: Annotated[
        str,
        From("DeviceBase.get_name"),
        Unsupported(on="default", default="{parent} fan {i}"),
    ]
    kind: Annotated[FanKind, Parent()]
    parent_name: Annotated[str, Parent()]
    # 'N/A' for a fan that is not in a drawer.  Left as the string rather than
    # None because that is what the consumers already publish.
    drawer_name: Annotated[str, Parent()]
    position_in_parent: Annotated[
        PositionInParent, From("DeviceBase.get_position_in_parent"),
        Unsupported(on="default", default=-1),
    ]

    presence: Annotated[bool, From("DeviceBase.get_presence"), Unsupported(on="default", default=False)]
    status: Annotated[bool, From("DeviceBase.get_status"), Unsupported(on="default", default=False)]
    is_replaceable: Annotated[
        bool, From("DeviceBase.is_replaceable"), Unsupported(on="default", default=False)
    ]
    model: Annotated[Optional[str], From("DeviceBase.get_model")]
    serial: Annotated[Optional[str], From("DeviceBase.get_serial")]

    speed_pct: Annotated[Optional[Percent], From("FanBase.get_speed"), _MISSING]
    target_speed_pct: Annotated[Optional[Percent], From("FanBase.get_target_speed"), _MISSING]
    # No sentinel handling: FAN_DIRECTION_NOT_APPLICABLE is the string 'N/A',
    # so here it is a value rather than a missing reading.
    direction: Annotated[Optional[FanDirection], From("FanBase.get_direction")]
    is_under_speed: Annotated[Optional[bool], From("FanBase.is_under_speed")]
    is_over_speed: Annotated[Optional[bool], From("FanBase.is_over_speed")]
    status_led: Annotated[Optional[LedColor], From("FanBase.get_status_led")]

    # thermalctld:396-409 -- drawers, then modules, then PSUs.  A drawer fan
    # whose drawer has no name is published under the chassis.
    def __init__(self, **fields: object) -> None:
        """Keyword-only.  The columns are the fields declared above; naming
        them again in a signature would be the one list written twice."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                "FanDrawerBase.get_all_fans",
                via=("ChassisBase.get_all_fan_drawers",),
                parent="get_name",
                parent_default="chassis 1",
                sets=(("kind", "drawer"), ("drawer_name", "@parent")),
            ),
            FlattenSource(
                "ModuleBase.get_all_fans",
                via=("ChassisBase.get_all_modules",),
                parent="get_name",
                parent_default="Module {i}",
                sets=(("kind", "module"), ("drawer_name", "N/A")),
            ),
            FlattenSource(
                "PsuBase.get_all_fans",
                via=("ChassisBase.get_all_psus",),
                parent="get_name",
                parent_default="PSU {i}",
                sets=(("kind", "psu"), ("drawer_name", "N/A")),
            ),
        )
    )

class FanDrawerInfo:
    """One fan drawer: the field-replaceable unit a chassis fan sits in."""

    name: Annotated[
        str, From("DeviceBase.get_name"), Unsupported(on="default", default="drawer {i}")
    ]
    position_in_parent: Annotated[
        PositionInParent, From("DeviceBase.get_position_in_parent"),
        Unsupported(on="default", default=-1),
    ]
    presence: Annotated[bool, From("DeviceBase.get_presence"), Unsupported(on="default", default=False)]
    status: Annotated[Optional[bool], From("DeviceBase.get_status")]
    is_replaceable: Annotated[
        bool, From("DeviceBase.is_replaceable"), Unsupported(on="default", default=False)
    ]
    model: Annotated[Optional[str], From("DeviceBase.get_model")]
    serial: Annotated[Optional[str], From("DeviceBase.get_serial")]
    status_led: Annotated[Optional[LedColor], From("FanDrawerBase.get_status_led")]
    maximum_consumed_power: Annotated[
        Optional[Watt], From("FanDrawerBase.get_maximum_consumed_power"), _MISSING
    ]

    def __init__(self, **fields: object) -> None:
        """Keyword-only.  The columns are the fields declared above; naming
        them again in a signature would be the one list written twice."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(FlattenSource("ChassisBase.get_all_fan_drawers", parent_default="chassis 1"),)
    )

class PsuInfo:
    """A PSU or a PDB.  `PdbBase` extends `PsuBase` and psud publishes both
    into the same table, so they are one row type with a `kind`."""

    name: Annotated[
        str, From("DeviceBase.get_name"), Unsupported(on="default", default="PSU {i}")
    ]
    kind: Annotated[PowerEntityKind, Parent()]
    position_in_parent: Annotated[
        PositionInParent, From("DeviceBase.get_position_in_parent"),
        Unsupported(on="default", default=-1),
    ]
    presence: Annotated[bool, From("DeviceBase.get_presence"), Unsupported(on="default", default=False)]
    is_replaceable: Annotated[
        bool, From("DeviceBase.is_replaceable"), Unsupported(on="default", default=False)
    ]
    model: Annotated[Optional[str], From("DeviceBase.get_model")]
    serial: Annotated[Optional[str], From("DeviceBase.get_serial")]
    revision: Annotated[Optional[str], From("DeviceBase.get_revision")]

    power_good: Annotated[
        bool, From("PsuBase.get_powergood_status"), Unsupported(on="default", default=False)
    ]
    status_led: Annotated[Optional[LedColor], From("PsuBase.get_status_led")]

    voltage: Annotated[Optional[Volt], From("PsuBase.get_voltage"), _MISSING]
    current: Annotated[Optional[Ampere], From("PsuBase.get_current"), _MISSING]
    power: Annotated[Optional[Watt], From("PsuBase.get_power"), _MISSING]
    input_voltage: Annotated[Optional[Volt], From("PsuBase.get_input_voltage"), _MISSING]
    input_current: Annotated[Optional[Ampere], From("PsuBase.get_input_current"), _MISSING]
    input_power: Annotated[Optional[Watt], From("PdbBase.get_input_power"), _MISSING]

    temperature: Annotated[Optional[Celsius], From("PsuBase.get_temperature"), _MISSING]
    temperature_high_threshold: Annotated[
        Optional[Threshold], From("PsuBase.get_temperature_high_threshold"), _MISSING
    ]
    voltage_high_threshold: Annotated[
        Optional[Threshold], From("PsuBase.get_voltage_high_threshold"), _MISSING
    ]
    voltage_low_threshold: Annotated[
        Optional[Threshold], From("PsuBase.get_voltage_low_threshold"), _MISSING
    ]
    maximum_supplied_power: Annotated[
        Optional[Watt], From("PsuBase.get_maximum_supplied_power"), _MISSING
    ]
    power_warning_suppress_threshold: Annotated[
        Optional[Watt], From("PsuBase.get_psu_power_warning_suppress_threshold"), _MISSING
    ]
    power_critical_threshold: Annotated[
        Optional[Watt], From("PsuBase.get_psu_power_critical_threshold"), _MISSING
    ]

    # psud's publication order: PSUs by index, then PDBs by index.  PDBs are
    # absent rather than empty on a PSU-based platform.
    def __init__(self, **fields: object) -> None:
        """Keyword-only.  The columns are the fields declared above; naming
        them again in a signature would be the one list written twice."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                "ChassisBase.get_all_psus",
                parent_default="PSU {i}",
                sets=(("kind", "psu"),),
            ),
            FlattenSource(
                "ChassisBase.get_all_pdbs",
                parent_default="PDB {i}",
                optional=True,
                sets=(("kind", "pdb"),),
            ),
        )
    )


class ChassisInfo:
    """The chassis itself.  A singleton: there is one, and it is the device."""

    name: Annotated[str, From("DeviceBase.get_name"),
                    Unsupported(on="default", default="chassis 1")]
    presence: Annotated[bool, From("DeviceBase.get_presence"),
                        Unsupported(on="default", default=True)]
    model: Annotated[Optional[str], From("DeviceBase.get_model")]
    serial: Annotated[Optional[str], From("DeviceBase.get_serial")]
    revision: Annotated[Optional[str], From("DeviceBase.get_revision")]
    status: Annotated[Optional[bool], From("DeviceBase.get_status")]

    base_mac: Annotated[Optional[str], From("ChassisBase.get_base_mac")]

    # Five predicates that decide what else a consumer asks for.  Each has a
    # literal default in the base class, so a platform that says nothing is
    # saying no rather than declining to answer.
    is_modular_chassis: Annotated[bool, From("ChassisBase.is_modular_chassis"),
                                  Unsupported(on="default", default=False)]
    is_smartswitch: Annotated[bool, From("ChassisBase.is_smartswitch"),
                              Unsupported(on="default", default=False)]
    is_dpu: Annotated[bool, From("ChassisBase.is_dpu"),
                      Unsupported(on="default", default=False)]
    is_bmc: Annotated[bool, From("ChassisBase.is_bmc"),
                      Unsupported(on="default", default=False)]
    is_liquid_cooled: Annotated[bool, From("ChassisBase.is_liquid_cooled"),
                                Unsupported(on="default", default=False)]

    # `get_reboot_cause()` is (cause, detail).
    reboot_cause: Annotated[Optional[str], From("ChassisBase.get_reboot_cause", at=0)]
    reboot_cause_detail: Annotated[Optional[str], From("ChassisBase.get_reboot_cause", at=1)]

    # Declared int although the base class documents "integer or string" and
    # the conformance suite accepts either.  A slot is a number; normalising
    # it here is the point of having a facade.  Both of these are among the
    # five base-class methods that `return NotImplementedError` rather than
    # raising it, which reads as absent.
    my_slot: Annotated[Optional[int], From("ChassisBase.get_my_slot"), _MISSING]
    supervisor_slot: Annotated[
        Optional[int], From("ChassisBase.get_supervisor_slot"), _MISSING
    ]
    dpu_id: Annotated[Optional[int], From("ChassisBase.get_dpu_id"), _MISSING]

    dataplane_state: Annotated[Optional[bool], From("ChassisBase.get_dataplane_state")]
    controlplane_state: Annotated[Optional[bool], From("ChassisBase.get_controlplane_state")]
    status_led: Annotated[Optional[LedColor], From("ChassisBase.get_status_led")]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

class ModuleInfo:
    """One line card, fabric card, supervisor or DPU."""

    name: Annotated[str, From("ModuleBase.get_name"),
                    Unsupported(on="default", default="Module {i}")]
    parent_name: Annotated[str, Parent()]
    position_in_parent: Annotated[
        PositionInParent, From("DeviceBase.get_position_in_parent"),
        Unsupported(on="default", default=-1),
    ]
    presence: Annotated[bool, From("DeviceBase.get_presence"),
                        Unsupported(on="default", default=False)]
    status: Annotated[Optional[bool], From("DeviceBase.get_status")]
    is_replaceable: Annotated[bool, From("DeviceBase.is_replaceable"),
                              Unsupported(on="default", default=False)]
    model: Annotated[Optional[str], From("DeviceBase.get_model")]
    serial: Annotated[Optional[str], From("DeviceBase.get_serial")]

    description: Annotated[Optional[str], From("ModuleBase.get_description")]
    slot: Annotated[Optional[int], From("ModuleBase.get_slot"), _MISSING]
    type: Annotated[Optional[ModuleType], From("ModuleBase.get_type")]
    oper_status: Annotated[Optional[ModuleStatus], From("ModuleBase.get_oper_status")]
    base_mac: Annotated[Optional[str], From("ModuleBase.get_base_mac")]
    dpu_id: Annotated[Optional[int], From("ModuleBase.get_dpu_id"), _MISSING]
    maximum_consumed_power: Annotated[
        Optional[Watt], From("ModuleBase.get_maximum_consumed_power"), _MISSING
    ]
    midplane_ip: Annotated[Optional[str], From("ModuleBase.get_midplane_ip")]
    # Another `return NotImplementedError`, so absent rather than truthy.
    is_midplane_reachable: Annotated[
        Optional[bool], From("ModuleBase.is_midplane_reachable")
    ]
    reboot_cause: Annotated[Optional[str], From("ModuleBase.get_reboot_cause", at=0)]
    reboot_cause_detail: Annotated[Optional[str], From("ModuleBase.get_reboot_cause", at=1)]
    state_transition: Annotated[
        Optional[bool], From("ModuleBase.get_module_state_transition")
    ]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource("ChassisBase.get_all_modules", parent_default="chassis 1"),
        )
    )


class ComponentInfo:
    """One field-upgradeable component: a BIOS, a CPLD, an FPGA, an SSD."""

    name: Annotated[str, From("ComponentBase.get_name"),
                    Unsupported(on="default", default="{parent} component {i}")]
    parent_name: Annotated[str, Parent()]
    description: Annotated[Optional[str], From("ComponentBase.get_description")]
    firmware_version: Annotated[
        Optional[str], From("ComponentBase.get_firmware_version")
    ]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource("ChassisBase.get_all_components", parent_default="chassis 1"),
            FlattenSource(
                "ModuleBase.get_all_components",
                via=("ChassisBase.get_all_modules",),
                when_chassis="is_modular_chassis",
                parent="get_name",
                parent_default="Module {i}",
            ),
        )
    )

class SensorInfo:
    """One voltage or current sensor.

    `kind` rather than two row types: the columns are identical, the daemon
    publishes them to two tables off the same loop, and a consumer that wanted
    only one filters.
    """

    name: Annotated[str, From("DeviceBase.get_name"),
                    Unsupported(on="default", default="{parent} sensor {i}")]
    kind: Annotated[SensorKind, Parent()]
    parent_name: Annotated[str, Parent()]
    position_in_parent: Annotated[
        PositionInParent, From("DeviceBase.get_position_in_parent"),
        Unsupported(on="default", default=-1),
    ]
    is_replaceable: Annotated[bool, From("DeviceBase.is_replaceable"),
                              Unsupported(on="default", default=False)]

    # SensorBase.get_unit is a classmethod returning 'mV' or 'mA'.  Carried as
    # data because the daemon publishes it, and because a consumer reading a
    # bare number off a sensor it did not choose needs to be told.
    unit: Annotated[Optional[str], From("SensorBase.get_unit")]
    value: Annotated[Optional[float], From("SensorBase.get_value"), _MISSING]
    high_threshold: Annotated[
        Optional[Threshold], From("SensorBase.get_high_threshold"), _MISSING
    ]
    low_threshold: Annotated[
        Optional[Threshold], From("SensorBase.get_low_threshold"), _MISSING
    ]
    high_critical_threshold: Annotated[
        Optional[Threshold], From("SensorBase.get_high_critical_threshold"), _MISSING
    ]
    low_critical_threshold: Annotated[
        Optional[Threshold], From("SensorBase.get_low_critical_threshold"), _MISSING
    ]
    min_recorded: Annotated[
        Optional[float], From("SensorBase.get_minimum_recorded"), _MISSING
    ]
    max_recorded: Annotated[
        Optional[float], From("SensorBase.get_maximum_recorded"), _MISSING
    ]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    # sensormond:209 and :356.  All voltage, then all current; within each,
    # the sensors.yaml ones before the chassis' own, because the daemon
    # concatenates in that order and the row index is what a consumer sees.
    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                provider="voltage_sensors_from_yaml",
                reaches=("SensorFs.factory",),
                parent_default="chassis 1",
                sets=(("kind", "voltage"),),
            ),
            FlattenSource(
                "ChassisBase.get_all_voltage_sensors",
                parent_default="chassis 1",
                sets=(("kind", "voltage"),),
            ),
            FlattenSource(
                "ModuleBase.get_all_voltage_sensors",
                via=("ChassisBase.get_all_modules",),
                when_chassis="is_modular_chassis",
                parent="get_name",
                parent_default="Module {i}",
                sets=(("kind", "voltage"),),
            ),
            FlattenSource(
                provider="current_sensors_from_yaml",
                reaches=("SensorFs.factory",),
                parent_default="chassis 1",
                sets=(("kind", "current"),),
            ),
            FlattenSource(
                "ChassisBase.get_all_current_sensors",
                parent_default="chassis 1",
                sets=(("kind", "current"),),
            ),
            FlattenSource(
                "ModuleBase.get_all_current_sensors",
                via=("ChassisBase.get_all_modules",),
                when_chassis="is_modular_chassis",
                parent="get_name",
                parent_default="Module {i}",
                sets=(("kind", "current"),),
            ),
        )
    )


class LeakProfile:
    """A named leak policy, published once at start-up.

    Separate from `LeakSensorInfo` because the daemon publishes it to its own
    table once rather than every cycle, and because several sensors share one.
    """

    type: Annotated[str, From("LeakSensorProfileBase.get_type"),
                    Unsupported(on="default", default="profile {i}")]
    max_minor_duration_sec: Annotated[
        Optional[int],
        From("LeakSensorProfileBase.get_leak_max_minor_duration_sec"),
        _MISSING,
    ]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                "LiquidCoolingBase.get_all_profiles",
                via=(Via("ChassisBase.get_liquid_cooling", single=True),),
                parent_default="chassis 1",
                optional=True,
            ),
        )
    )

class LeakSensorInfo:
    """One liquid-cooling leak sensor."""

    name: Annotated[str, From("LeakageSensorBase.get_name"),
                    Unsupported(on="default", default="leakage{i}")]
    parent_name: Annotated[str, Parent()]
    sensor_type: Annotated[
        Optional[str], From("LeakageSensorBase.get_leak_sensor_type")
    ]
    location: Annotated[
        Optional[str], From("LeakageSensorBase.get_leak_sensor_location")
    ]
    is_leak: Annotated[Optional[bool], From("LeakageSensorBase.is_leak")]
    is_ok: Annotated[Optional[bool], From("LeakageSensorBase.is_leak_sensor_ok")]
    severity: Annotated[
        Optional[LeakSeverity], From("LeakageSensorBase.get_leak_severity")
    ]

    # Two hops: the sensor's profile, then the profile's own columns.  A row
    # rather than a handle, because what the daemon needs off the profile is
    # two scalars and it needs them on every sensor it escalates.
    profile_type: Annotated[
        Optional[str], From("LeakageSensorBase.get_leak_profile.get_type")
    ]
    profile_max_minor_duration_sec: Annotated[
        Optional[int],
        From("LeakageSensorBase.get_leak_profile.get_leak_max_minor_duration_sec"),
        _MISSING,
    ]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    # thermalctld:657 walks `liquid_cooling.leakage_sensors` -- the attribute,
    # not `get_all_leak_sensors()`.  The facade calls the method: a consumer
    # reaching past the API into an attribute is the thing this layer exists
    # to stop, and the two are the same list on every platform that has both.
    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                "LiquidCoolingBase.get_all_leak_sensors",
                via=(Via("ChassisBase.get_liquid_cooling", single=True),),
                parent_default="chassis 1",
                optional=True,
            ),
        )
    )

class WatchdogInfo:
    """The hardware watchdog.  A singleton per chassis."""

    is_armed: Annotated[Optional[bool], From("WatchdogBase.is_armed")]
    # -1 when unarmed, which the base class documents and which is not the
    # same as "this platform has no watchdog".
    remaining_time: Annotated[
        Optional[int], From("WatchdogBase.get_remaining_time"), _MISSING
    ]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                "ChassisBase.get_watchdog",
                parent_default="chassis 1",
                single=True,
                optional=True,
            ),
        )
    )


class ChangeEvent:
    """One device that changed, out of the two-level mapping the base class
    returns.

    `{'fan': {'0': '0', '2': '1'}, 'sfp': {'11': '0'}}` becomes three rows.
    The nesting carries no information a row cannot: the outer key is the
    device type and the inner key is the device id, and a consumer that wanted
    them grouped can group them.
    """

    device_type: Annotated[str, Parent()]
    device_id: Annotated[str, Parent()]
    # What the platform said, unchanged.  Vendors are not limited to the seven
    # documented values and a facade that dropped an eighth would be hiding
    # the one event somebody needed.
    status: Annotated[str, Parent()]
    # The same thing named, when it is one of the seven.  None otherwise.
    kind: Annotated[Optional[ChangeEventKind], Parent()]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

class ChangeEventBatch:
    """What one `get_change_event` call answered.

    `ok` is carried rather than raised on.  It reads like a success flag and
    is not one: `ok=False` is how a platform reports a system-level event,
    with the detail in the mapping under the key the daemon watches for
    (xcvrd:301-323 maps the pair to SYSTEM_NOT_READY or SYSTEM_FAIL).  A
    facade that raised on it would delete that path.

    `ok=True` with no events is the ordinary timeout: nothing changed.
    """

    ok: Annotated[bool, Parent()]
    events: Annotated[list[ChangeEvent], Parent()]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""


class EepromTlv:
    """One entry of a system EEPROM.

    The base class answers a mapping whose keys are ONIE TLV codes as hex
    strings on the chassis, and Redfish field names on the BMC.  Neither key
    set is enumerable ahead of time -- which is exactly why this is rows and
    not columns.
    """

    source: Annotated[str, Parent()]
    parent_name: Annotated[str, Parent()]
    code: Annotated[str, Parent()]
    value: Annotated[Optional[str], Parent()]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                mapping="ChassisBase.get_system_eeprom_info",
                parent_default="chassis 1",
                optional=True,
                sets=(("source", "chassis"), ("code", "@key"), ("value", "@value")),
            ),
            FlattenSource(
                mapping="ModuleBase.get_system_eeprom_info",
                via=("ChassisBase.get_all_modules",),
                when_chassis="is_modular_chassis",
                parent="get_name",
                parent_default="Module {i}",
                optional=True,
                sets=(("source", "module"), ("code", "@key"), ("value", "@value")),
            ),
            FlattenSource(
                mapping="BMCBase.get_eeprom",
                via=(Via("ChassisBase.get_bmc", single=True),),
                parent_default="BMC",
                optional=True,
                sets=(("source", "bmc"), ("code", "@key"), ("value", "@value")),
            ),
        )
    )

class AsicInfo:
    """One ASIC on a module, and where it sits on the PCI bus."""

    parent_name: Annotated[str, Parent()]
    asic_id: Annotated[str, Parent()]
    pci_address: Annotated[Optional[str], Parent()]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

class BmcInfo:
    """The board management controller.  A list of at most one."""

    name: Annotated[str, From("DeviceBase.get_name"),
                    Unsupported(on="default", default="BMC")]
    presence: Annotated[bool, From("DeviceBase.get_presence"),
                        Unsupported(on="default", default=False)]
    model: Annotated[Optional[str], From("DeviceBase.get_model")]
    serial: Annotated[Optional[str], From("DeviceBase.get_serial")]
    revision: Annotated[Optional[str], From("DeviceBase.get_revision")]
    status: Annotated[Optional[bool], From("DeviceBase.get_status")]
    is_replaceable: Annotated[bool, From("DeviceBase.is_replaceable"),
                              Unsupported(on="default", default=False)]
    version: Annotated[Optional[str], From("BMCBase.get_version")]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                "ChassisBase.get_bmc",
                parent_default="chassis 1",
                single=True,
                optional=True,
            ),
        )
    )

class BmcResult:
    """What a BMC command answered.

    Every BMC method returns `(code, message)`, with 0 meaning success. The
    code is carried rather than raised on: the CLI prints the message on a
    non-zero code and carries on, and a facade that raised would turn a
    reported failure into an exception the caller has to translate back.
    """

    code: Annotated[int, Parent()]
    message: Annotated[Optional[str], Parent()]
    # open_session answers (code, (message, (session_id, token))); a debug-log
    # dump answers (code, (task_id, message)).  Both are absent elsewhere.
    session_id: Annotated[Optional[str], Parent()]
    token: Annotated[Optional[str], Parent()]
    task_id: Annotated[Optional[str], Parent()]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

# --------------------------------------------------------------------------
# Deliberately not here
# --------------------------------------------------------------------------

# Base-class methods a consumer reaches but the facade does not declare, each
# with the reason.  Written down so that "decided against" and "not yet
# written" are different numbers in generator/api_coverage.py, rather than one
# undifferentiated backlog that nobody can tell is finished.
OMITTED: Final[tuple[tuple[str, str], ...]] = (
    # A count is the length of the list.  Declaring both would give a platform
    # two ways to disagree with itself, and the daemons already treat a
    # mismatch between get_num_x() and len(get_all_x()) as the platform's bug.
    ("ChassisBase.get_num_components", "len(get_components())"),
    ("ChassisBase.get_num_fans", "len(get_fans())"),
    ("ChassisBase.get_num_fan_drawers", "len(get_fan_drawers())"),
    ("ChassisBase.get_num_modules", "len(get_modules())"),
    ("ChassisBase.get_num_psus", "len(get_psus())"),
    ("ChassisBase.get_num_pdbs", "len(get_psus()) filtered on kind"),
    ("ChassisBase.get_num_thermals", "len(get_thermals())"),
    ("ChassisBase.get_num_sfps", "len(get_sfps())"),
    ("ModuleBase.get_num_components", "len(get_components()) filtered on parent"),
    ("ModuleBase.get_num_fans", "len(get_fans()) filtered on parent"),
    ("ModuleBase.get_num_psus", "len(get_psus()) filtered on parent"),
    ("ModuleBase.get_num_thermals", "len(get_thermals()) filtered on parent"),
    ("ModuleBase.get_num_sfps", "len(get_sfps()) filtered on parent"),
    ("PsuBase.get_num_fans", "len(get_fans()) filtered on parent"),
    ("PsuBase.get_num_thermals", "len(get_thermals()) filtered on parent"),
    ("FanDrawerBase.get_num_fans", "len(get_fans()) filtered on parent"),
    ("LiquidCoolingBase.get_num_leak_sensors", "len(get_leak_sensors())"),
    # Rows are addressed by name.  The indexed accessors are 0-based in some
    # places and 1-based in others, and answer None rather than raising when
    # the index is out of range.
    ("ChassisBase.get_component", "rows are addressed by name"),
    ("ChassisBase.get_fan", "rows are addressed by name"),
    ("ChassisBase.get_fan_drawer", "rows are addressed by name"),
    ("ChassisBase.get_module", "rows are addressed by name"),
    ("ChassisBase.get_psu", "rows are addressed by name"),
    ("ChassisBase.get_pdb", "rows are addressed by name"),
    ("ChassisBase.get_thermal", "rows are addressed by name"),
    ("ChassisBase.get_sfp", "rows are addressed by name"),
    ("ChassisBase.get_cpo", "rows are addressed by name"),
    ("ChassisBase.get_module_index", "rows are addressed by name"),
    ("ModuleBase.get_component", "rows are addressed by name"),
    ("ModuleBase.get_fan", "rows are addressed by name"),
    ("ModuleBase.get_psu", "rows are addressed by name"),
    ("ModuleBase.get_thermal", "rows are addressed by name"),
    ("ModuleBase.get_sfp", "rows are addressed by name"),
    ("PsuBase.get_fan", "rows are addressed by name"),
    ("PsuBase.get_thermal", "rows are addressed by name"),
    ("FanDrawerBase.get_fan", "rows are addressed by name"),
    ("SfpBase.get_thermal", "rows are addressed by name"),
    # ChassisBase.get_all_fans is the flat list of fans mounted directly on
    # the chassis.  FanInfo already collects every fan through its drawer, its
    # module or its PSU; adding this source would double-count on a platform
    # that implements both, and thermalctld does not use it.
    ("ChassisBase.get_all_fans", "already reached through drawer, module or PSU"),
    # Returns the same objects as get_all_leak_sensors(); the docstring says
    # List[str] and the annotation says otherwise, and no consumer reads it as
    # anything but the sensor list.
    ("LiquidCoolingBase.get_leak_sensor_status", "duplicate of get_all_leak_sensors"),
    # The per-device getters the rows already carry as columns.  Listed
    # because the scan counts (class, method) and a column read through
    # DeviceBase does not name the subclass that also declares it.
    ("SensorFs.get_name", "SensorInfo column, read through SensorBase"),
    ("SensorFs.get_value", "SensorInfo column"),
    ("SensorFs.get_position_in_parent", "SensorInfo column"),
    ("SensorFs.get_high_threshold", "SensorInfo column"),
    ("SensorFs.get_low_threshold", "SensorInfo column"),
    ("SensorFs.get_high_critical_threshold", "SensorInfo column"),
    ("SensorFs.get_low_critical_threshold", "SensorInfo column"),
    ("SensorFs.get_minimum_recorded", "SensorInfo column"),
    ("SensorFs.get_maximum_recorded", "SensorInfo column"),
    ("SensorFs.set_high_threshold", "set_sensor_high_threshold"),
    ("SensorFs.set_low_threshold", "set_sensor_low_threshold"),
    ("VoltageSensorBase.get_type", "SensorInfo.kind, fixed by the source"),
    ("VoltageSensorBase.get_unit", "SensorInfo column, read through SensorBase"),
    ("CurrentSensorBase.get_type", "SensorInfo.kind, fixed by the source"),
    ("CurrentSensorBase.get_unit", "SensorInfo column, read through SensorBase"),
    ("SensorBase.get_type", "SensorInfo.kind, fixed by the source"),
    ("PdbBase.get_voltage", "PsuBase.get_voltage; PdbBase delegates to it"),
    ("PdbBase.get_current", "PsuBase.get_current; PdbBase delegates to it"),
    ("PdbBase.get_power", "PsuBase.get_power; PdbBase delegates to it"),
    ("PdbBase.get_output_voltage", "PsuInfo.voltage"),
    ("PdbBase.get_output_current", "PsuInfo.current"),
    ("PdbBase.get_output_power", "PsuInfo.power"),
    ("BMCWatchdog.arm", "WatchdogBase.arm; BMCWatchdog overrides it"),
    ("BMCWatchdog.disarm", "WatchdogBase.disarm"),
    ("BMCWatchdog.is_armed", "WatchdogBase.is_armed"),
    ("BMCWatchdog.get_remaining_time", "WatchdogBase.get_remaining_time"),
    ("LeakSensorProfileBase.get_type", "LeakProfile.type"),
    ("LeakSensorProfileBase.get_leak_max_minor_duration_sec",
     "LeakProfile.max_minor_duration_sec"),
    ("PlatformBase.get_chassis", "the bridge's constructor, not a facade call"),
    # A daemon already has its own DB connection; asking the platform API for
    # one couples every vendor to swsscommon for no benefit the caller cannot
    # get itself.
    ("ModuleBase.get_state_db", "the caller opens its own DB connection"),
)

# --------------------------------------------------------------------------
# The API
# --------------------------------------------------------------------------

class PlatformApi:
    def __init__(self, chassis: object) -> None:
        """`chassis` is the vendor's `ChassisBase`, already constructed.

        The facade never imports `sonic_platform` itself: which vendor package
        is in play is the caller's decision, and keeping it out of here is what
        lets the conformance suite drive a facade over a mock.
        """

    # -- snapshots ---------------------------------------------------------

    @platform_method(Snapshot(scope="per_cycle"))
    def get_chassis_info(self) -> ChassisInfo:
        """The chassis.

        A singleton, so it is not a `list`: there is one chassis and the
        traversal that would flatten it has nothing to walk.
        """

    @platform_method(Snapshot(scope="per_cycle"))
    def get_modules(self) -> list[ModuleInfo]: ...
    @platform_method(Snapshot(scope="per_cycle"))
    def get_thermals(self) -> list[ThermalInfo]: ...
    @platform_method(Snapshot(scope="per_cycle"))
    def get_fans(self) -> list[FanInfo]: ...
    @platform_method(Snapshot(scope="per_cycle"))
    def get_fan_drawers(self) -> list[FanDrawerInfo]: ...
    @platform_method(Snapshot(scope="per_cycle"))
    def get_psus(self) -> list[PsuInfo]: ...
    @platform_method(Snapshot(scope="per_cycle"))
    def get_components(self) -> list[ComponentInfo]: ...
    @platform_method(Snapshot(scope="per_cycle"))
    def get_sensors(self) -> list[SensorInfo]: ...

    @platform_method(Snapshot(scope="per_call"))
    def get_leak_profiles(self) -> list[LeakProfile]:
        """Published once at start-up, so read on call rather than cached."""

    @platform_method(Snapshot(scope="per_cycle"))
    def get_leak_sensors(self) -> list[LeakSensorInfo]: ...
    @platform_method(Snapshot(scope="per_cycle"))
    def get_eeprom(self) -> list[EepromTlv]:
        """Every system EEPROM entry the platform exposes, chassis and BMC."""

    @platform_method(Snapshot(scope="per_cycle"))
    def get_bmcs(self) -> list[BmcInfo]:
        """A list of at most one, for the same reason as `get_watchdogs`."""

    @platform_method(Snapshot(scope="per_cycle"))
    def get_watchdogs(self) -> list[WatchdogInfo]:
        """A list of at most one.

        Not a singleton: a platform without a watchdog has none, and a
        singleton accessor would have to invent a row to say so.
        """


    # -- actions, addressed by name ---------------------------------------

    @platform_method(On(row="FanInfo"), Calls("FanBase.set_status_led"), Unsupported(on="error"))
    def set_fan_led(self, fan: str, color: LedColor) -> None:
        """Set the LED on one fan.

        Separate from `set_fan_drawer_led` on purpose.  thermalctld sets the
        fan's LED and then its drawer's with the same colour, tolerating
        either being unimplemented (thermalctld:547-550); folding the two into
        one call would hide which of them a platform refused.
        """

    @platform_method(
        On(row="FanDrawerInfo"), Calls("FanDrawerBase.set_status_led"), Unsupported(on="error")
    )
    def set_fan_drawer_led(self, drawer: str, color: LedColor) -> None: ...
    @platform_method(On(row="FanInfo"), Calls("FanBase.set_speed"), Unsupported(on="error"))
    def set_fan_speed(self, fan: str, speed: Percent) -> None: ...
    @platform_method(On(row="PsuInfo"), Calls("PsuBase.set_status_led"), Unsupported(on="error"))
    def set_psu_led(self, psu: str, color: LedColor) -> None: ...

    @platform_method(
        On(row="PsuInfo"), Calls("PsuBase.get_status_master_led"), Unsupported(on="error")
    )
    def get_psu_master_led(self, psu: str) -> Optional[LedColor]:
        """The colour of the LED every hot-swappable PSU shares.

        `PsuBase.get_status_master_led` is a `@classmethod` over a class
        attribute, so any PSU answers for all of them; the row name is how the
        facade reaches an instance to ask.
        """

    @platform_method(
        On(row="PsuInfo"), Calls("PsuBase.set_status_master_led"), Unsupported(on="error")
    )
    def set_psu_master_led(self, psu: str, color: LedColor) -> None:
        """One LED shared by every hot-swappable PSU.

        Addressed through a PSU row like the getter, and for the same reason:
        `set_status_master_led` is a `@classmethod` on `PsuBase`, so any PSU
        sets it for all of them -- but it is not on the chassis, and reaching
        for it there would fail on every platform.
        """

    @platform_method(On(row="ModuleInfo"), Calls("ModuleBase.reboot"), Unsupported(on="error"))
    def reboot_module(self, module: str, reboot_type: str) -> None: ...
    @platform_method(
        On(row="ModuleInfo"), Calls("ModuleBase.set_admin_state"), Unsupported(on="error")
    )
    def set_module_admin_state(self, module: str, up: bool) -> None: ...
    @platform_method(
        On(row="ModuleInfo"),
        Calls("ModuleBase.set_admin_state_gracefully"),
        Unsupported(on="error"),
    )
    def set_module_admin_state_gracefully(self, module: str, up: bool) -> None:
        """Admin-down that lets the module's services stop first.

        Separate from `set_module_admin_state` because it blocks for as long
        as the halt takes, and a caller polling on a timer needs to know which
        of the two it asked for.
        """

    @platform_method(
        On(row="ModuleInfo"), Calls("ModuleBase.do_power_cycle"), Unsupported(on="error")
    )
    def power_cycle_module(self, module: str) -> None: ...
    @platform_method(
        On(row="ModuleInfo"), Calls("ModuleBase.module_pre_shutdown"), Unsupported(on="error")
    )
    def module_pre_shutdown(self, module: str) -> None: ...
    @platform_method(
        On(row="ModuleInfo"), Calls("ModuleBase.module_post_startup"), Unsupported(on="error")
    )
    def module_post_startup(self, module: str) -> None: ...

    @platform_method(
        On(row="ModuleInfo", pass_key=True),
        Calls("ModuleBase.set_module_state_transition"),
        Unsupported(on="error"),
    )
    def set_module_state_transition(self, module: str, transition_type: str) -> None:
        """`pass_key`: the base class takes the module's own name as well."""

    @platform_method(
        On(row="ModuleInfo", pass_key=True),
        Calls("ModuleBase.clear_module_state_transition"),
        Unsupported(on="error"),
    )
    def clear_module_state_transition(self, module: str) -> None: ...
    @platform_method(
        On(row="ModuleInfo"),
        Calls("ModuleBase.clear_module_gnoi_halt_in_progress"),
        Unsupported(on="error"),
    )
    def clear_module_gnoi_halt(self, module: str) -> None: ...

    @platform_method(
        On(row="SensorInfo"), Calls("SensorBase.set_high_threshold"), Unsupported(on="error")
    )
    def set_sensor_high_threshold(self, sensor: str, value: Threshold) -> None: ...
    @platform_method(
        On(row="SensorInfo"), Calls("SensorBase.set_low_threshold"), Unsupported(on="error")
    )
    def set_sensor_low_threshold(self, sensor: str, value: Threshold) -> None: ...

    # -- component firmware: queries that take an argument -----------------
    #
    # Not columns.  Each answers about an image the caller names, so there is
    # nothing to put in a snapshot -- a row would have to carry an answer for
    # every image that might ever be offered.

    @platform_method(
        On(row="ComponentInfo"),
        Calls("ComponentBase.get_available_firmware_version"),
        Unsupported(on="error"),
    )
    def get_available_firmware_version(
        self, component: str, image_path: str
    ) -> Optional[str]: ...
    @platform_method(
        On(row="ComponentInfo"),
        Calls("ComponentBase.get_firmware_update_notification"),
        Unsupported(on="error"),
    )
    def get_firmware_update_notification(
        self, component: str, image_path: str
    ) -> Optional[str]: ...
    @platform_method(
        On(row="ComponentInfo"), Calls("ComponentBase.install_firmware"),
        Unsupported(on="error"),
    )
    def install_firmware(self, component: str, image_path: str) -> Optional[bool]: ...
    @platform_method(
        On(row="ComponentInfo"), Calls("ComponentBase.update_firmware"),
        Unsupported(on="error"),
    )
    def update_firmware(self, component: str, image_path: str) -> None:
        """`ComponentBase.update_firmware` returns False on a missing path and
        nothing at all on success, so there is no value worth declaring."""

    @platform_method(
        On(row="ComponentInfo"), Calls("ComponentBase.auto_update_firmware"),
        Unsupported(on="error"),
    )
    def auto_update_firmware(
        self, component: str, image_path: str, boot_type: str
    ) -> Optional[int]:
        """Returns one of `ComponentBase.FW_AUTO_*`."""

    # -- watchdog ----------------------------------------------------------

    @platform_method(Calls("ChassisBase.get_watchdog.arm"), Unsupported(on="error"))
    def arm_watchdog(self, seconds: int) -> Optional[int]:
        """Arm, and say for how long it actually armed.

        `WatchdogBase.arm` answers the seconds it settled on, which need not
        be the seconds asked for, and -1 on failure.
        """

    @platform_method(Calls("ChassisBase.get_watchdog.disarm"), Unsupported(on="error"))
    def disarm_watchdog(self) -> Optional[bool]: ...

    @platform_method(Calls("ChassisBase.initizalize_system_led"), Unsupported(on="error"))
    def initialize_system_led(self) -> None:
        """The base class spells this `initizalize_system_led`.

        The typo is part of the shipped API, so `Calls` carries it; the facade
        does not have to repeat it.
        """

    @platform_method(Calls("ChassisBase.init_midplane_switch"), Unsupported(on="error"))
    def init_midplane_switch(self) -> None: ...

    @platform_method(Calls("ChassisBase.set_status_led"), Unsupported(on="error"))
    def set_chassis_led(self, color: LedColor) -> None:
        """The whole platform API surface healthd reaches.

        `health_checker/manager.py:77`.  It is not a pmon daemon -- it runs on
        the host -- which is why this one method is worth naming.
        """

    # -- sed ---------------------------------------------------------------

    @platform_method(
        Calls("ChassisBase.get_sed_mgmt.change_sed_password"), Unsupported(on="error")
    )
    def change_sed_password(self, new_password: str) -> Optional[bool]: ...
    @platform_method(
        Calls("ChassisBase.get_sed_mgmt.reset_sed_password"), Unsupported(on="error")
    )
    def reset_sed_password(self) -> Optional[bool]: ...

    # -- bmc commands ------------------------------------------------------

    @platform_method(
        EscapeHatch(
            reaches=(
                "BMCBase.open_session",
                "BMCBase.close_session",
                "BMCBase.reset_root_password",
                "BMCBase.request_bmc_reset",
                "BMCBase.update_firmware",
                "BMCBase.trigger_bmc_debug_log_dump",
                "BMCBase.get_bmc_debug_log_dump",
                "RedfishClient.open_session",
                "RedfishClient.close_session",
            ),
            reason="every BMC command answers a tuple, and not the same tuple: "
            "(code, message), (code, (message, (session_id, token))) and "
            "(code, (task_id, message)) all appear. Unpacking each into one row "
            "shape is a decision per method rather than a rule.",
        )
    )
    def bmc_open_session(self) -> BmcResult: ...
    @platform_method(EscapeHatch(reason="see bmc_open_session"))
    def bmc_close_session(self, session_id: str) -> BmcResult: ...
    @platform_method(EscapeHatch(reason="see bmc_open_session"))
    def bmc_reset_root_password(self) -> BmcResult: ...
    @platform_method(EscapeHatch(reason="see bmc_open_session"))
    def bmc_reset(self, graceful: bool) -> BmcResult: ...
    @platform_method(EscapeHatch(reason="see bmc_open_session"))
    def bmc_update_firmware(self, image_path: str) -> BmcResult: ...
    @platform_method(EscapeHatch(reason="see bmc_open_session"))
    def bmc_trigger_debug_log_dump(self) -> BmcResult: ...
    @platform_method(EscapeHatch(reason="see bmc_open_session"))
    def bmc_get_debug_log_dump(
        self, task_id: str, filename: str, path: str
    ) -> BmcResult: ...

    # -- asics -------------------------------------------------------------

    @platform_method(
        EscapeHatch(
            reaches=("ModuleBase.get_all_asics",),
            reason="get_all_asics answers a list of (asic_id, pci_address) "
            "tuples rather than a list of device objects, so there is nothing "
            "for a flatten plan to call a getter on.",
        ),
        Snapshot(scope="per_cycle"),
    )
    def get_asics(self) -> list[AsicInfo]: ...

    # -- escape hatches ----------------------------------------------------

    @platform_method(
        EscapeHatch(
            reaches=("ChassisBase.get_thermal_manager",),
            reason="get_thermal_manager() returns a class, not an instance; its twelve "
            "methods are all @classmethod over process-global state, and run_policy "
            "takes the chassis back as an argument. The facade holds the chassis and "
            "passes it, so these four calls take no arguments and the bridge never "
            "re-enters Python from Rust from Python."
        )
    )
    def tm_initialize(self) -> None: ...
    @platform_method(EscapeHatch(reason="see tm_initialize"))
    def tm_run_policy(self) -> None: ...
    @platform_method(EscapeHatch(reason="see tm_initialize"))
    def tm_get_interval(self) -> Optional[float]: ...
    @platform_method(EscapeHatch(reason="see tm_initialize"))
    def tm_deinitialize(self) -> None: ...

    @platform_method(
        EscapeHatch(
            reaches=(
                "ChassisBase.get_change_event",
                "ModuleBase.get_change_event",
            ),
            reason="get_change_event returns a two-level mapping whose leaf is a "
            "stringly-typed enumeration documented only in prose, and whose outer "
            "keys vary by platform. Flattening it into rows is mechanical, but "
            "deciding that `ok` is data rather than an error is not: ok=False is "
            "how a platform reports a system-level event, not how it reports a "
            "failed call."
        ),
        Snapshot(scope="per_call"),
    )
    def get_change_event(self, timeout_ms: int) -> ChangeEventBatch:
        """Block until something changes, or until `timeout_ms` elapses.

        `timeout_ms=0` blocks indefinitely, which is what the base class means
        by it and what the daemons rely on.
        """

