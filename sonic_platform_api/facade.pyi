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

Actions address a device by its `DeviceKey`, the path the traversal took to
reach it, which every addressed row carries.  Not by name: names are not
unique -- two line cards each have a "BIOS" -- and a lookup by name acted on
whichever device came first.  Not by the indexed base-class accessors either:
they are 0-based in some places and 1-based in others, and return None rather
than raising when the index is out of range; a key holds list positions.  A
caller that starts from a name resolves it the way Python's consumers do:
`get_module_key` as chassisd does, `get_component_key` as fwutil does.

Scope is the union of what the four consumer groups actually reach -- the ten
PMON daemons, healthd, the CLI and the conformance suite.  `generator/
inventory.json` records that union, and `generator/api_coverage.py` checks
this file against it.

Not everything here is derived.  A method declared `EscapeHatch` has its body
written by hand in `_escape_hatch.py`, with the reason beside the declaration;
see meta.pyi.

What the consumers reach and this file does not declare is either OMITTED,
with the reason it never will be, or DEFERRED, with the phase that declares it;
`generator/api_coverage.py` counts both.
"""

from typing import Annotated, ClassVar, Final, Literal, Optional

from .meta import (
    Calls,
    EscapeHatch,
    Flatten,
    FlattenSource,
    From,
    Key,
    Narrowed,
    Observed,
    On,
    Parent,
    ParentKey,
    ReadIf,
    RowError,
    Secret,
    Snapshot,
    Truthy,
    Unguarded,
    Unsupported,
    Via,
    WithName,
    platform_method,
)
from .types import (
    Ampere,
    Celsius,
    DeviceKey,
    Json,
    Number,
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

# The four colours `DeviceBase.STATUS_LED_COLOR_*` names: what a daemon sets
# on a fan or a PSU.  An LED is *read* as `str`, because a vendor answers
# with its own colours (mlnx: "orange", "green_blink"), and the Python
# daemons publish whatever it answered.
LedColor = Literal["green", "amber", "red", "off"]
# "pdb" is psud's alone: its `_update_psu_fan_data` runs over PDBs as well as
# PSUs (`psud:757`, `:942`), where thermalctld's FanUpdater walks drawers,
# modules and PSUs only (`thermalctld:396-407`).  One row list serves both, so
# the source they disagree about has to be nameable.
FanKind = Literal["drawer", "module", "psu", "pdb"]
PowerEntityKind = Literal["psu", "pdb"]
# Where a thermal is mounted: one per source of ThermalInfo.  thermalctld
# reads PSU and PDB thermals on the PSU interval and the rest on their own
# (thermalctld:1176-1177), so it has to know which is which without reading
# it out of a name.
ThermalKind = Literal["chassis", "psu", "pdb", "module", "module_psu"]

# ModuleBase.MODULE_TYPE_*; the strings the base class defines, not new ones.
ModuleType = Literal["SUPERVISOR", "LINE-CARD", "FABRIC-CARD", "DPU", "SWITCH-HOST"]
# ModuleBase.MODULE_STATUS_*.
ModuleStatus = Literal[
    "Empty", "Offline", "PoweredDown", "Present", "Fault",
    "ProvisionReady", "ProvisionPending", "Provisioned", "Online",
]
SensorKind = Literal["voltage", "current"]
# What `eeprom_update_db` did.  syseepromd says which half failed before its
# own line: "Failed to read EEPROM" when `read_eeprom()` answered None,
# "Failed to update EEPROM info in database" when `update_eeprom_db()`
# answered an error (syseepromd:85-96).
EepromUpdate = Literal["updated", "read_failed", "update_failed"]
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

    # The name and the position are read outside thermalctld's per-thermal
    # `try` (thermalctld:1156-1157), so one that raises fails the call, as it
    # fails Python's cycle; they are also all a skipped thermal reads.  See
    # `Unguarded` and `Snapshot.skippable`.
    name: Annotated[
        str,
        From("DeviceBase.get_name"),
        Unsupported(on="default", default="{parent} Thermal {i}"),
        Unguarded(),
    ]
    kind: Annotated[ThermalKind, Parent()]
    parent_name: Annotated[str, Parent()]
    # Where the device is, and what `get_thermals(skip=...)` names; see DeviceKey.
    key: Annotated[DeviceKey, Key()]
    parent_key: Annotated[Optional[DeviceKey], ParentKey()]
    # No default here on purpose.  `DeviceBase.get_position_in_parent`
    # documents -1 for "cannot determine", but not one daemon uses that: psud
    # falls back to 0 (psud:932), thermalctld and sensormond fall back to the
    # 1-based index of the device in the loop that is publishing it
    # (thermalctld:123,428,458,1087; sensormond:54).  A default baked in here
    # would have to be wrong for at least two of the three, so the row carries
    # the absence and each daemon applies its own -- which is what the Python
    # it replaces does.  Measured on hardware: PDB rows, where Mellanox does not
    # implement the getter, were published as 0 by psud and as -1 by the port.
    position_in_parent: Annotated[
        Optional[PositionInParent], From("DeviceBase.get_position_in_parent"), Unguarded(),
    ]
    # In thermalctld's order (thermalctld:1245-1253): the temperature and
    # whether the sensor is replaceable, then -- only when there is a
    # temperature -- the recorded extremes and the limits.  A row error names
    # the column being read when it struck, so the order is what says how
    # far Python got.
    temperature: Annotated[Optional[Celsius], From("ThermalBase.get_temperature"), _MISSING]
    is_replaceable: Annotated[
        bool, From("DeviceBase.is_replaceable"), Unsupported(on="default", default=False),
    ]
    min_recorded: Annotated[
        Optional[Celsius], From("ThermalBase.get_minimum_recorded"), _MISSING,
        ReadIf("temperature"),
    ]
    max_recorded: Annotated[
        Optional[Celsius], From("ThermalBase.get_maximum_recorded"), _MISSING,
        ReadIf("temperature"),
    ]
    high_threshold: Annotated[
        Optional[Threshold], From("ThermalBase.get_high_threshold"), _MISSING,
        ReadIf("temperature"),
    ]
    low_threshold: Annotated[
        Optional[Threshold], From("ThermalBase.get_low_threshold"), _MISSING,
        ReadIf("temperature"),
    ]
    high_critical_threshold: Annotated[
        Optional[Threshold], From("ThermalBase.get_high_critical_threshold"), _MISSING,
        ReadIf("temperature"),
    ]
    low_critical_threshold: Annotated[
        Optional[Threshold], From("ThermalBase.get_low_critical_threshold"), _MISSING,
        ReadIf("temperature"),
    ]
    # What went wrong reading this thermal's readings, if anything did; see
    # `RowError`.  thermalctld logs `repr(e)` (thermalctld:1294).
    error: Annotated[Optional[str], RowError()]
    error_repr: Annotated[Optional[str], RowError(repr=True)]
    error_column: Annotated[Optional[str], RowError(column=True)]

    # thermalctld's order (thermalctld:1173-1213).  A PSU that is not present
    # contributes nothing; the PDB source is absent rather than empty on a
    # PSU-based platform; module thermals exist only on a modular chassis.
    #
    # One difference, on a modular chassis only: thermalctld walks a module's
    # thermals and then that module's PSU thermals before the next module
    # (thermalctld:1202-1213), and here each source is whole -- every module's
    # thermals, then every module's PSU thermals.  Nothing published depends on
    # it: a thermal is published under its name, with its position within its
    # own parent, and both are the same either way.
    def __init__(self, **fields: object) -> None:
        """Keyword-only.  The columns are the fields declared above; naming
        them again in a signature would be the one list written twice."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                "ChassisBase.get_all_thermals",
                parent_default="chassis 1",
                sets=(("kind", "chassis"),),
            ),
            FlattenSource(
                "PsuBase.get_all_thermals",
                via=("ChassisBase.get_all_psus",),
                when="get_presence",
                parent="get_name",
                parent_default="PSU {i}",
                sets=(("kind", "psu"),),
            ),
            # `try_get(pdb.get_presence)` (thermalctld:1189): a PDB that does
            # not say whether it is there is taken to be, where a PSU is
            # asked bare and must answer.
            FlattenSource(
                "PdbBase.get_all_thermals",
                via=("ChassisBase.get_all_pdbs",),
                when="get_presence",
                when_unsupported="present",
                parent="get_name",
                parent_default="PDB {i}",
                optional=True,
                sets=(("kind", "pdb"),),
            ),
            FlattenSource(
                "ModuleBase.get_all_thermals",
                via=("ChassisBase.get_all_modules",),
                when_chassis="is_modular_chassis",
                parent="get_name",
                parent_default="Module {i}",
                sets=(("kind", "module"),),
            ),
            FlattenSource(
                "PsuBase.get_all_thermals",
                via=("ChassisBase.get_all_modules", "ModuleBase.get_all_psus"),
                when="get_presence",
                when_chassis="is_modular_chassis",
                parent="get_name",
                parent_default=("Module {i}", "{parent} PSU {i}"),
                sets=(("kind", "module_psu"),),
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
    # Where the device is, and what every action on it takes; see DeviceKey.
    key: Annotated[DeviceKey, Key()]
    parent_key: Annotated[Optional[DeviceKey], ParentKey()]
    # 'N/A' for a fan that is not in a drawer, or whose drawer has no name.
    # Left as the string rather than None because that is what the consumers
    # already publish (thermalctld:450).
    drawer_name: Annotated[str, Parent()]
    # No default here on purpose.  `DeviceBase.get_position_in_parent`
    # documents -1 for "cannot determine", but not one daemon uses that: psud
    # falls back to 0 (psud:932), thermalctld and sensormond fall back to the
    # 1-based index of the device in the loop that is publishing it
    # (thermalctld:123,428,458,1087; sensormond:54).  A default baked in here
    # would have to be wrong for at least two of the three, so the row carries
    # the absence and each daemon applies its own -- which is what the Python
    # it replaces does.  Measured on hardware: PDB rows, where Mellanox does not
    # implement the getter, were published as 0 by psud and as -1 by the port.
    position_in_parent: Annotated[
        Optional[PositionInParent], From("DeviceBase.get_position_in_parent"),
    ]

    # In thermalctld's order (thermalctld:470-479, 529-530): whether the fan
    # is replaceable, its presence, the speeds and their verdicts, its fault
    # status and direction, and -- last, as the row is written -- model and
    # serial.  A row error names the column being read when it struck, so the
    # order is what says how far Python got: past `position_in_parent` it has
    # published the fan's entity row and taken the fan into its LED pass.
    is_replaceable: Annotated[
        bool, From("DeviceBase.is_replaceable"), Unsupported(on="default", default=False)
    ]
    presence: Annotated[bool, From("DeviceBase.get_presence"), Unsupported(on="default", default=False)]
    # Asked only of a fan that is there, as thermalctld asks them only
    # `if presence:` (thermalctld:471-478) -- but not when psud reads a PSU's
    # fans absorbing, which it gates on the PSU's presence instead and never
    # asks the fan for its own (psud:945-950).  See `ReadIf`.
    speed_pct: Annotated[
        Optional[Percent], From("FanBase.get_speed"), _MISSING,
        ReadIf("presence", truthy=True, when_absorbing=False),
    ]
    target_speed_pct: Annotated[
        Optional[Percent], From("FanBase.get_target_speed"), _MISSING,
        ReadIf("presence", truthy=True, when_absorbing=False),
    ]
    is_under_speed: Annotated[
        Optional[bool], From("FanBase.is_under_speed"),
        ReadIf("presence", truthy=True, when_absorbing=False),
    ]
    is_over_speed: Annotated[
        Optional[bool], From("FanBase.is_over_speed"),
        ReadIf("presence", truthy=True, when_absorbing=False),
    ]
    status: Annotated[
        bool, From("DeviceBase.get_status"), Unsupported(on="default", default=False),
        ReadIf("presence", truthy=True, when_absorbing=False),
    ]
    # No sentinel handling: FAN_DIRECTION_NOT_APPLICABLE is the string 'N/A',
    # so here it is a value rather than a missing reading.  A `str` and not the
    # three `FAN_DIRECTION_*`, for the reason an LED is: vendors answer with
    # their own spelling (PDDF's valmaps say "INTAKE", "EXHAUST", "UNKNOWN"),
    # and thermalctld and psud publish whatever they answered.
    direction: Annotated[
        Optional[str], From("FanBase.get_direction"),
        ReadIf("presence", truthy=True, when_absorbing=False),
    ]
    model: Annotated[Optional[str], From("DeviceBase.get_model")]
    serial: Annotated[Optional[str], From("DeviceBase.get_serial")]
    # Read in thermalctld's separate LED pass (thermalctld:558-570), which a
    # caller asks for on its own.
    status_led: Annotated[Optional[str], From("FanBase.get_status_led")]
    # What went wrong reading this fan, if anything did; see `RowError`.
    # thermalctld refreshes each fan in its own `try`, name included
    # (thermalctld:378-384), so no column here is Unguarded.
    error: Annotated[Optional[str], RowError()]
    error_repr: Annotated[Optional[str], RowError(repr=True)]
    error_column: Annotated[Optional[str], RowError(column=True)]

    # thermalctld:396-409 -- drawers, then modules, then PSUs.  A drawer fan
    # whose drawer has no name -- or is named 'N/A', as Mellanox's virtual
    # drawer is (fan_drawer.py:118) -- is published under the chassis, with
    # `drawer_name` 'N/A' (thermalctld:450-456).
    def __init__(self, **fields: object) -> None:
        """Keyword-only.  The columns are the fields declared above; naming
        them again in a signature would be the one list written twice."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(
            FlattenSource(
                "FanDrawerBase.get_all_fans",
                via=("ChassisBase.get_all_fan_drawers",),
                parent="get_name",
                parent_missing=("N/A",),
                parent_default="chassis 1",
                sets=(("kind", "drawer"), ("drawer_name", "@parent_raw")),
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
            # Last, so that the order the other three appear in -- which is the
            # order thermalctld publishes them -- is untouched by their being
            # here.  `PdbBase` extends `PsuBase`, hence the same getter.
            FlattenSource(
                "PsuBase.get_all_fans",
                via=("ChassisBase.get_all_pdbs",),
                parent="get_name",
                parent_default="PDB {i}",
                sets=(("kind", "pdb"), ("drawer_name", "N/A")),
            ),
        )
    )

class FanDrawerInfo:
    """One fan drawer: the field-replaceable unit a chassis fan sits in."""

    # 'N/A' for a drawer that does not name itself: what thermalctld calls it,
    # and the name it publishes nothing under (thermalctld:423-426).  Actions
    # reach a drawer by its key, so the name is only ever shown.
    name: Annotated[
        str, From("DeviceBase.get_name"), Unsupported(on="default", default="N/A")
    ]
    # Where the device is, and what every action on it takes; see DeviceKey.
    key: Annotated[DeviceKey, Key()]
    # No default here on purpose.  `DeviceBase.get_position_in_parent`
    # documents -1 for "cannot determine", but not one daemon uses that: psud
    # falls back to 0 (psud:932), thermalctld and sensormond fall back to the
    # 1-based index of the device in the loop that is publishing it
    # (thermalctld:123,428,458,1087; sensormond:54).  A default baked in here
    # would have to be wrong for at least two of the three, so the row carries
    # the absence and each daemon applies its own -- which is what the Python
    # it replaces does.  Measured on hardware: PDB rows, where Mellanox does not
    # implement the getter, were published as 0 by psud and as -1 by the port.
    position_in_parent: Annotated[
        Optional[PositionInParent], From("DeviceBase.get_position_in_parent"),
    ]
    presence: Annotated[bool, From("DeviceBase.get_presence"), Unsupported(on="default", default=False)]
    status: Annotated[Optional[bool], From("DeviceBase.get_status")]
    is_replaceable: Annotated[
        bool, From("DeviceBase.is_replaceable"), Unsupported(on="default", default=False)
    ]
    model: Annotated[Optional[str], From("DeviceBase.get_model")]
    serial: Annotated[Optional[str], From("DeviceBase.get_serial")]
    status_led: Annotated[Optional[str], From("FanDrawerBase.get_status_led")]
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

    # The source's own fallback, 'PSU {i}' or 'PDB {i}', which is psud's
    # (psud:260-268): an unnamed PDB is not called after a PSU.
    name: Annotated[
        str, From("DeviceBase.get_name"), Unsupported(on="default", default="{parent}")
    ]
    kind: Annotated[PowerEntityKind, Parent()]
    # Where the device is, and what every action on it takes; see DeviceKey.
    key: Annotated[DeviceKey, Key()]
    # No default here on purpose.  `DeviceBase.get_position_in_parent`
    # documents -1 for "cannot determine", but not one daemon uses that: psud
    # falls back to 0 (psud:932), thermalctld and sensormond fall back to the
    # 1-based index of the device in the loop that is publishing it
    # (thermalctld:123,428,458,1087; sensormond:54).  A default baked in here
    # would have to be wrong for at least two of the three, so the row carries
    # the absence and each daemon applies its own -- which is what the Python
    # it replaces does.  Measured on hardware: PDB rows, where Mellanox does not
    # implement the getter, were published as 0 by psud and as -1 by the port.
    position_in_parent: Annotated[
        Optional[PositionInParent], From("DeviceBase.get_position_in_parent"),
    ]
    presence: Annotated[bool, From("DeviceBase.get_presence"), Unsupported(on="default", default=False)]
    is_replaceable: Annotated[
        bool, From("DeviceBase.is_replaceable"), Unsupported(on="default", default=False)
    ]
    model: Annotated[Optional[str], From("DeviceBase.get_model")]
    serial: Annotated[Optional[str], From("DeviceBase.get_serial")]
    revision: Annotated[Optional[str], From("DeviceBase.get_revision")]

    # Asked only of a PSU that is there, as psud asks them only `if presence:`
    # (psud:767, 779-789): a PSU that has been pulled is not asked for what it
    # cannot answer, which on a driver that tries the I/O anyway costs its
    # retries and timeouts in every snapshot.  A PDB's input power, which psud
    # does not read, goes with the other readings.  The LED, the FRU fields
    # and the power thresholds are asked of any PSU (psud:835-836, 883-885).
    power_good: Annotated[
        bool, From("PsuBase.get_powergood_status"), Unsupported(on="default", default=False),
        ReadIf("presence", truthy=True),
    ]
    status_led: Annotated[Optional[str], From("PsuBase.get_status_led")]

    voltage: Annotated[
        Optional[Volt], From("PsuBase.get_voltage"), _MISSING, ReadIf("presence", truthy=True)
    ]
    current: Annotated[
        Optional[Ampere], From("PsuBase.get_current"), _MISSING, ReadIf("presence", truthy=True)
    ]
    power: Annotated[
        Optional[Watt], From("PsuBase.get_power"), _MISSING, ReadIf("presence", truthy=True)
    ]
    input_voltage: Annotated[
        Optional[Volt], From("PsuBase.get_input_voltage"), _MISSING,
        ReadIf("presence", truthy=True),
    ]
    input_current: Annotated[
        Optional[Ampere], From("PsuBase.get_input_current"), _MISSING,
        ReadIf("presence", truthy=True),
    ]
    input_power: Annotated[
        Optional[Watt], From("PdbBase.get_input_power"), _MISSING,
        ReadIf("presence", truthy=True),
    ]

    temperature: Annotated[
        Optional[Celsius], From("PsuBase.get_temperature"), _MISSING,
        ReadIf("presence", truthy=True),
    ]
    temperature_high_threshold: Annotated[
        Optional[Threshold], From("PsuBase.get_temperature_high_threshold"), _MISSING,
        ReadIf("presence", truthy=True),
    ]
    voltage_high_threshold: Annotated[
        Optional[Threshold], From("PsuBase.get_voltage_high_threshold"), _MISSING,
        ReadIf("presence", truthy=True),
    ]
    voltage_low_threshold: Annotated[
        Optional[Threshold], From("PsuBase.get_voltage_low_threshold"), _MISSING,
        ReadIf("presence", truthy=True),
    ]
    maximum_supplied_power: Annotated[
        Optional[Watt], From("PsuBase.get_maximum_supplied_power"), _MISSING,
        ReadIf("presence", truthy=True),
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

    # Declinable, unlike a list row's name: the chassis is walked under the
    # fixed 'chassis 1', so a projected read that does not ask for this one
    # does not call `get_name()`, which on some platforms reads the EEPROM.
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
    dpu_id: Annotated[Optional[int], From("ChassisBase.get_dpu_id"), _MISSING, Narrowed()]

    dataplane_state: Annotated[Optional[bool], From("ChassisBase.get_dataplane_state")]
    controlplane_state: Annotated[Optional[bool], From("ChassisBase.get_controlplane_state")]
    status_led: Annotated[Optional[str], From("ChassisBase.get_status_led")]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

class ModuleInfo:
    """One line card, fabric card, supervisor or DPU."""

    name: Annotated[str, From("ModuleBase.get_name"),
                    Unsupported(on="default", default="Module {i}")]
    parent_name: Annotated[str, Parent()]
    # Where the device is, and what every action on it takes; see DeviceKey.
    key: Annotated[DeviceKey, Key()]
    parent_key: Annotated[Optional[DeviceKey], ParentKey()]
    # No default here on purpose.  `DeviceBase.get_position_in_parent`
    # documents -1 for "cannot determine", but not one daemon uses that: psud
    # falls back to 0 (psud:932), thermalctld and sensormond fall back to the
    # 1-based index of the device in the loop that is publishing it
    # (thermalctld:123,428,458,1087; sensormond:54).  A default baked in here
    # would have to be wrong for at least two of the three, so the row carries
    # the absence and each daemon applies its own -- which is what the Python
    # it replaces does.  Measured on hardware: PDB rows, where Mellanox does not
    # implement the getter, were published as 0 by psud and as -1 by the port.
    position_in_parent: Annotated[
        Optional[PositionInParent], From("DeviceBase.get_position_in_parent"),
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
    state_transition: Annotated[
        Optional[bool], From("ModuleBase.get_module_state_transition"), WithName()
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
    # Where the device is, and what every action on it takes; see DeviceKey.
    key: Annotated[DeviceKey, Key()]
    parent_key: Annotated[Optional[DeviceKey], ParentKey()]
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

    # sensormond's own fallback, `'{} voltage_sensor {}'` and
    # `'{} current_sensor {}'` (sensormond:246, 394).
    name: Annotated[str, From("DeviceBase.get_name"),
                    Unsupported(on="default", default="{parent} {kind}_sensor {i}")]
    kind: Annotated[SensorKind, Parent()]
    parent_name: Annotated[str, Parent()]
    # Where the device is, and what every action on it takes; see DeviceKey.
    key: Annotated[DeviceKey, Key()]
    parent_key: Annotated[Optional[DeviceKey], ParentKey()]
    # No default here on purpose.  `DeviceBase.get_position_in_parent`
    # documents -1 for "cannot determine", but not one daemon uses that: psud
    # falls back to 0 (psud:932), thermalctld and sensormond fall back to the
    # 1-based index of the device in the loop that is publishing it
    # (thermalctld:123,428,458,1087; sensormond:54).  A default baked in here
    # would have to be wrong for at least two of the three, so the row carries
    # the absence and each daemon applies its own -- which is what the Python
    # it replaces does.  Measured on hardware: PDB rows, where Mellanox does not
    # implement the getter, were published as 0 by psud and as -1 by the port.
    position_in_parent: Annotated[
        Optional[PositionInParent], From("DeviceBase.get_position_in_parent"),
    ]
    # In sensormond's order (sensormond:246-271): the value and whether the
    # sensor is replaceable, then -- only when there is a value -- the unit,
    # the recorded extremes and the limits.  A row error names the column
    # being read when it struck, so the order is what says how far Python
    # got.
    value: Annotated[Optional[Number], From("SensorBase.get_value"), _MISSING]
    is_replaceable: Annotated[bool, From("DeviceBase.is_replaceable"),
                              Unsupported(on="default", default=False)]
    # SensorBase.get_unit is a classmethod returning 'mV' or 'mA'.  Carried as
    # data because the daemon publishes it, and because a consumer reading a
    # bare number off a sensor it did not choose needs to be told.
    unit: Annotated[Optional[str], From("SensorBase.get_unit"), ReadIf("value")]
    min_recorded: Annotated[
        Optional[Number], From("SensorBase.get_minimum_recorded"), _MISSING, ReadIf("value"),
    ]
    max_recorded: Annotated[
        Optional[Number], From("SensorBase.get_maximum_recorded"), _MISSING, ReadIf("value"),
    ]
    high_threshold: Annotated[
        Optional[Threshold], From("SensorBase.get_high_threshold"), _MISSING, ReadIf("value"),
    ]
    low_threshold: Annotated[
        Optional[Threshold], From("SensorBase.get_low_threshold"), _MISSING, ReadIf("value"),
    ]
    high_critical_threshold: Annotated[
        Optional[Threshold], From("SensorBase.get_high_critical_threshold"), _MISSING,
        ReadIf("value"),
    ]
    low_critical_threshold: Annotated[
        Optional[Threshold], From("SensorBase.get_low_critical_threshold"), _MISSING,
        ReadIf("value"),
    ]
    # What went wrong reading this sensor, if anything did; see `RowError`.
    # sensormond refreshes each sensor in its own `try`, name included
    # (sensormond:237-311, 385-459).
    error: Annotated[Optional[str], RowError()]
    error_repr: Annotated[Optional[str], RowError(repr=True)]
    error_column: Annotated[Optional[str], RowError(column=True)]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    # sensormond:209 and :356.  All voltage, then all current; within each,
    # the sensors.yaml ones before the chassis' own, because the daemon
    # concatenates in that order and the row index is what a consumer sees.
    # The two are one list there, numbered together, so the chassis source
    # carries the yaml one's index on; a module's sensors start again at 1
    # (sensormond:218-226, 366-374).
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
                index_from_previous=True,
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
                index_from_previous=True,
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
    is_leak: Annotated[Optional[bool], From("LeakageSensorBase.is_leak"), Truthy()]
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


class SfpInfo:
    """A chassis transceiver slot, including empty cages.

    Inventory does not read EEPROM or latched flags. Reads and actions address
    the key individually so a presence check cannot consume a DOM alarm, and
    CMIS bring-up need not decode an entire module for one state field.
    """

    key: Annotated[DeviceKey, Key()]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

    ORDER: ClassVar[Flatten] = Flatten(
        sources=(FlattenSource("ChassisBase.get_all_sfps", parent_default="chassis 1"),)
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



class PcieDevice:
    """One device out of the platform's `pcie.yaml`, and whether it is there.

    `PcieUtil.get_pcie_check()` answers the parsed config file with a `result`
    column added, so what comes back is the *expected* inventory annotated with
    what was found -- not a scan of the bus.  A device the yaml does not list
    does not appear here however present it is, which is the point: pcied is
    checking the machine against its own parts list.
    """

    name: Annotated[str, Parent()]
    # From the yaml as hex strings ('03', '00', '0'); carried as the numbers
    # they denote, because the daemon's key is `%02x:%02x.%d` of them and a
    # string that was never parsed cannot be re-formatted.
    bus: Annotated[int, Parent()]
    dev: Annotated[int, Parent()]
    fn: Annotated[int, Parent()]
    present: Annotated[bool, Parent()]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""

class PcieAerStat:
    """One AER counter of one PCIe device.

    `get_pcie_aer_stats` answers `{severity: {field: count}}` for three fixed
    severities.  The nesting carries nothing a row cannot, and pcied itself
    flattens it straight back to `severity|field` before writing (`pcied:133`).
    """

    severity: Annotated[str, Parent()]
    field: Annotated[str, Parent()]
    # A count, kept as the string the kernel printed.  The sysfs file is a
    # table of decimal counters, but nothing here needs the arithmetic and a
    # number that failed to parse would be worse than the text.
    value: Annotated[str, Parent()]

    def __init__(self, **fields: object) -> None:
        """Keyword-only, as every row is."""



class StorageDeviceInfo:
    """One storage disk of the switch, as stormond publishes it.

    `StorageDevices` walks `/sys/block` and hands each disk to a factory that
    answers an `SsdUtil`, an `EmmcUtil`, a `UsbUtil` -- or `None`, for a disk
    none of them handles.  That `None` is carried here as `available=False`
    rather than dropped: a disk the switch has and cannot read about is a fact,
    and stormond says so (`stormond:309`, `:332`).

    Every reading but the two counters is carried as the string Python would
    have written.  The daemon only ever `str()`s them on the way to STATE_DB,
    and a column that guessed at a number would have to guess again at how to
    print it.
    """

    name: Annotated[str, Parent()]
    available: Annotated[bool, Parent()]
    model: Annotated[str, Parent()]
    serial: Annotated[str, Parent()]
    firmware: Annotated[str, Parent()]
    health: Annotated[str, Parent()]
    temperature: Annotated[str, Parent()]
    disk_io_reads: Annotated[str, Parent()]
    disk_io_writes: Annotated[str, Parent()]
    reserved_blocks: Annotated[str, Parent()]
    # The two the daemon does arithmetic on: it subtracts the previous reading
    # from this one to find what happened while it was not running.  A string
    # that failed to parse would take the whole reconciliation with it, so the
    # parse happens here, once, and `None` means "no baseline this cycle".
    fs_io_reads: Annotated[Optional[int], Parent()]
    fs_io_writes: Annotated[Optional[int], Parent()]
    # What stormond's two passes over this disk would have caught, each as
    # `str(ex)`: its model and serial, read once at start-up and logged at
    # ERR when they raise (stormond:311-332), and its refresh --
    # `fetch_parse_info` and every reading after it -- logged at NOTICE
    # (stormond:335-393).  A disk is a row either way; the readings of a pass
    # that failed are 'N/A' and are not Python's to publish.
    static_error: Annotated[Optional[str], Parent()]
    error: Annotated[Optional[str], Parent()]

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

class ModuleRebootCause:
    """Why a module last restarted: the cause, and the reason behind it.

    `ModuleBase.get_reboot_cause()` answers `(cause, detail)` and chassisd
    publishes both -- the cause to `REBOOT_CAUSE|<module>|<ts>.cause` and the
    detail to its `comment`, which is the half a person reads.  `comment` also
    reaches `/host/reboot-cause/module/<dpu>/history/*.json` and the
    `previous-reboot-cause.json` symlink beside it.

    Declaring the method as `Calls(at=0)` carried only the cause, and the stub
    said so: "nothing consumes the detail".  That was measured false on a
    SmartSwitch -- against the Python daemon on the same switch, in the same
    hour, the records read

        python:  'Non-Hardware' | 'Reset due to Power off'
        rust:    'Non-Hardware' | 'N/A'

    A second method with `at=1` would answer the other half, and would also
    call the vendor getter a second time.  That getter *logs* (`module.py:
    477,482`), which is the reason this stopped being a column at all; asking
    twice would put back half the noise the change removed.  So one call, and
    a row with both slots in it.
    """

    cause: Annotated[Optional[str], From("ModuleBase.get_reboot_cause", at=0)]
    detail: Annotated[Optional[str], From("ModuleBase.get_reboot_cause", at=1)]


class ModuleMidplaneDownReason:
    """Why a module's midplane went down: the reason, and the detail behind it.

    `ModuleBase.get_midplane_down_reason()` answers `(reason, detail)`, the
    reason being one of the `REBOOT_CAUSE_*` strings.  chassisd asks when a
    DPU's midplane goes from up to down without a planned transition, joins
    the halves that are not empty and publishes `Unplanned: '<joined>'`.  One
    call fills both slots, for the reason `ModuleRebootCause` gives.

    A platform that answers a bare string instead of the tuple gets the whole
    string as `reason`, which is how chassisd reads it too.
    """

    reason: Annotated[Optional[str], From("ModuleBase.get_midplane_down_reason", at=0)]
    detail: Annotated[Optional[str], From("ModuleBase.get_midplane_down_reason", at=1)]


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
    # A credential: kept out of every repr and Debug line; see `Secret`.
    token: Annotated[Optional[str], Parent(), Secret()]
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
    # Rows are addressed by key.  The indexed accessors are 0-based in some
    # places and 1-based in others, and answer None rather than raising when
    # the index is out of range.
    ("ChassisBase.get_component", "rows are addressed by key"),
    ("ChassisBase.get_fan", "rows are addressed by key"),
    ("ChassisBase.get_fan_drawer", "rows are addressed by key"),
    ("ChassisBase.get_module", "rows are addressed by key"),
    ("ChassisBase.get_psu", "rows are addressed by key"),
    ("ChassisBase.get_pdb", "rows are addressed by key"),
    ("ChassisBase.get_thermal", "rows are addressed by key"),
    ("ChassisBase.get_sfp", "rows are addressed by key"),
    ("ChassisBase.get_cpo", "rows are addressed by key"),
    ("ModuleBase.get_component", "rows are addressed by key"),
    ("ModuleBase.get_fan", "rows are addressed by key"),
    ("ModuleBase.get_psu", "rows are addressed by key"),
    ("ModuleBase.get_thermal", "rows are addressed by key"),
    ("ModuleBase.get_sfp", "rows are addressed by key"),
    ("PsuBase.get_fan", "rows are addressed by key"),
    ("PsuBase.get_thermal", "rows are addressed by key"),
    ("FanDrawerBase.get_fan", "rows are addressed by key"),
    ("SfpBase.get_thermal", "rows are addressed by key"),
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

# Base-class methods a consumer reaches that a later phase declares, each with
# the phase.  Not omissions -- they are meant to be here -- and not unknown
# either: `generator/api_coverage.py --check` fails on anything a consumer
# reaches that is in none of the facade, OMITTED and this.
#
# Transceivers come with the port of sonic_xcvr, which they are built on;
# xcvrd and sfputil read the Python platform API until then.  The other two
# are reached only by the CLI, which keeps reading Python until its bindings.
DEFERRED: Final[tuple[tuple[str, str], ...]] = (
    ("ChassisBase.get_port_or_cage_type", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.get_num_thermals", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.get_power_override", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.get_rx_los", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.get_rx_power", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.get_tx_bias", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.get_tx_disable", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.get_tx_disable_channel", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.get_tx_fault", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.get_tx_power", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.set_power", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.set_power_override", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.tx_disable", "transceivers: the sonic_xcvr phase"),
    ("SfpBase.tx_disable_channel", "transceivers: the sonic_xcvr phase"),
    ("PcieBase.get_pcie_device", "the CLI phase: only pcieutil reaches it"),
    ("PcieUtil.get_pcie_device", "the CLI phase: only pcieutil reaches it"),
    ("PcieUtil.dump_conf_yaml", "the CLI phase: only pcieutil reaches it"),
    ("StorageBase.get_vendor_output", "the CLI phase: only ssdutil --vendor reaches it"),
    ("SsdUtil.get_vendor_output", "the CLI phase: only ssdutil --vendor reaches it"),
    ("EmmcUtil.get_vendor_output", "the CLI phase: only ssdutil --vendor reaches it"),
    ("UsbUtil.get_vendor_output", "the CLI phase: only ssdutil --vendor reaches it"),
)

# --------------------------------------------------------------------------
# The API
# --------------------------------------------------------------------------

class DeviceNotFound(KeyError):
    """No device at a key: one that names nothing, or that is not a key at all.

    What an action raises for a key that leads nowhere.  A `KeyError`, as a
    lookup that found nothing has always been in Python, and a class of its
    own so that a `KeyError` out of a vendor's getter is not taken for one:
    the Rust bridge maps this, and only this, to `PlatformError::NotFound`.
    """

class PlatformApi:
    def __init__(self, chassis: object) -> None:
        """`chassis` is the vendor's `ChassisBase`, already constructed.

        The facade never imports `sonic_platform` itself: which vendor package
        is in play is the caller's decision, and keeping it out of here is what
        lets the tests drive a facade over a mock.
        """

    # -- snapshots ---------------------------------------------------------

    @platform_method(Snapshot())
    def get_sfps(self) -> list[SfpInfo]:
        """Transceiver slots in chassis list order, addressed by DeviceKey."""

    # Projected: pcied reads one of these twenty columns
    # (`is_smartswitch`) and psud one (`is_modular_chassis`); chassisd
    # reads seven and thermalctld six.  See `Snapshot.projected`.
    @platform_method(Snapshot(projected=True))
    def get_chassis_info(self) -> ChassisInfo:
        """The chassis.

        A singleton, so it is not a `list`: there is one chassis and the
        traversal that would flatten it has nothing to walk.
        """

    # Projected: chassisd reads eleven of these eighteen columns, psud
    # three -- it wants a module's power draw, not its midplane.
    @platform_method(Snapshot(projected=True))
    def get_modules(self) -> list[ModuleInfo]: ...
    # Skippable: thermalctld reads a thermal's readings only when platform.json's
    # `polling_interval` -- or the PSU interval, for a PSU's or a PDB's -- says
    # it is due, and every other cycle only its name and position
    # (thermalctld:1126-1158, 1176-1177).
    @platform_method(Snapshot(projected=True, skippable=True, per_row_errors=True))
    def get_thermals(self) -> list[ThermalInfo]: ...
    # Projected: psud reads four of these sixteen columns and thermalctld
    # nineteen, and two of the ones psud discards -- is_under_speed and
    # is_over_speed -- reach sysfs files a switched-off PSU leaves empty.  See
    # `Snapshot.projected`.
    # Absorbable: thermalctld refreshes a fan in one `try` (thermalctld:378-384),
    # psud reads a PSU's fans one `try_get` at a time (psud:943-960); see
    # `Snapshot.absorbs`.
    @platform_method(Snapshot(projected=True, per_row_errors=True, absorbable=True))
    def get_fans(self) -> list[FanInfo]: ...
    # Projected: thermalctld reads eight of these nine columns, psud three.
    @platform_method(Snapshot(projected=True))
    def get_fan_drawers(self) -> list[FanDrawerInfo]: ...
    # Absorbs: psud reads every column of a PSU through `try_get`, which takes
    # any exception for "no answer" (psud:271-292).
    @platform_method(Snapshot(absorbs=True))
    def get_psus(self) -> list[PsuInfo]: ...
    @platform_method(Snapshot())
    def get_components(self) -> list[ComponentInfo]: ...
    @platform_method(Snapshot(per_row_errors=True))
    def get_sensors(self) -> list[SensorInfo]: ...

    @platform_method(Snapshot())
    def get_leak_profiles(self) -> list[LeakProfile]:
        """The leak policies, which thermalctld publishes once at start-up."""

    @platform_method(Snapshot())
    def get_leak_sensors(self) -> list[LeakSensorInfo]: ...
    @platform_method(Snapshot())
    def get_eeprom(self) -> list[EepromTlv]:
        """Every system EEPROM entry the platform exposes, chassis and BMC."""

    @platform_method(Snapshot())
    def get_bmcs(self) -> list[BmcInfo]:
        """A list of at most one, for the same reason as `get_watchdogs`."""

    @platform_method(Snapshot())
    def get_watchdogs(self) -> list[WatchdogInfo]:
        """A list of at most one.

        Not a singleton: a platform without a watchdog has none, and a
        singleton accessor would have to invent a row to say so.
        """


    # -- transceivers -----------------------------------------------------

    @platform_method(On(row="SfpInfo"), Calls("DeviceBase.get_presence"))
    def sfp_get_presence(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("DeviceBase.is_replaceable"))
    def sfp_is_replaceable(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_reset_status"))
    def sfp_get_reset_status(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_lpmode"))
    def sfp_get_lpmode(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_error_description"))
    def sfp_get_error_description(self, sfp: DeviceKey) -> Optional[str]: ...

    @platform_method(On(row="SfpInfo"), EscapeHatch(
        reason="sfp_type is a vendor attribute, not a base-class getter.",
    ))
    def sfp_get_type(self, sfp: DeviceKey) -> str:
        """The slot's sfp_type attribute, for example QSFP_DD."""

    @platform_method(On(row="SfpInfo"), EscapeHatch(
        reason="Legacy PM capability probing must not invoke a getter or "
        "consume latched flags; hasattr is not a base-class call.",
    ))
    def sfp_has_method(self, sfp: DeviceKey, method: str) -> bool:
        """Whether the SFP exposes a method, without reading hardware."""

    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_transceiver_info"))
    def sfp_get_transceiver_info(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_transceiver_info_firmware_versions"))
    def sfp_get_transceiver_info_firmware_versions(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_transceiver_status"))
    def sfp_get_transceiver_status(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_transceiver_status_flags"))
    def sfp_get_transceiver_status_flags(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), EscapeHatch(
        reaches=("SfpOptoeBase.get_transceiver_dom_real_value", "SfpBase.get_transceiver_bulk_status"),
        reason="Use bulk status only when the modern DOM method is absent, "
        "not when it returns None or raises.",
    ))
    def sfp_get_transceiver_dom_real_value(self, sfp: DeviceKey) -> Json:
        """DOM readings, with the legacy bulk-status fallback."""

    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_transceiver_dom_flags"))
    def sfp_get_transceiver_dom_flags(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_transceiver_threshold_info"))
    def sfp_get_transceiver_threshold_info(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_temperature"))
    def sfp_get_temperature(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_transceiver_pm"))
    def sfp_get_transceiver_pm(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.is_transceiver_vdm_supported"))
    def sfp_is_transceiver_vdm_supported(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.is_vdm_statistic_supported"))
    def sfp_is_vdm_statistic_supported(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_transceiver_vdm_real_value_basic"))
    def sfp_get_transceiver_vdm_real_value_basic(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_transceiver_vdm_real_value_statistic"))
    def sfp_get_transceiver_vdm_real_value_statistic(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_transceiver_vdm_flags"))
    def sfp_get_transceiver_vdm_flags(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_transceiver_vdm_thresholds"))
    def sfp_get_transceiver_vdm_thresholds(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_vdm_freeze_status"))
    def sfp_get_vdm_freeze_status(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.get_vdm_unfreeze_status"))
    def sfp_get_vdm_unfreeze_status(self, sfp: DeviceKey) -> Optional[bool]: ...

    @platform_method(On(row="SfpInfo"), Calls("SfpBase.set_lpmode"))
    def sfp_set_lpmode(self, sfp: DeviceKey, on: bool) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.reset"))
    def sfp_reset(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.remove_xcvr_api"))
    def sfp_remove_xcvr_api(self, sfp: DeviceKey) -> None: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.freeze_vdm_stats"))
    def sfp_freeze_vdm_stats(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpOptoeBase.unfreeze_vdm_stats"))
    def sfp_unfreeze_vdm_stats(self, sfp: DeviceKey) -> Optional[bool]: ...

    @platform_method(On(row="SfpInfo"), EscapeHatch(
        reason="read_eeprom is a platform hook without a base-class declaration; "
        "normalise its bytearray to bytes, preserving a None read miss.",
    ))
    def sfp_read_eeprom(self, sfp: DeviceKey, offset: int, num_bytes: int) -> Optional[bytes]:
        """Read at an optoe-linear offset. None means the read failed."""

    @platform_method(On(row="SfpInfo"), EscapeHatch(
        reason="write_eeprom is a platform hook without a base-class declaration; "
        "its length argument must be derived from the supplied bytes.",
    ))
    def sfp_write_eeprom(self, sfp: DeviceKey, offset: int, data: bytes) -> Optional[bool]:
        """Write bytes at an optoe-linear offset, returning the vendor result."""

    # Resolve get_xcvr_api on every call: module replacement invalidates its
    # cache on the same SFP object the inventory and change-event paths use.
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_xcvr_api.is_flat_memory"))
    def sfp_is_flat_memory(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_xcvr_api.get_module_type_abbreviation"))
    def sfp_get_module_type_abbreviation(self, sfp: DeviceKey) -> Optional[str]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_xcvr_api.is_coherent_module"))
    def sfp_is_coherent_module(self, sfp: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_xcvr_api.get_module_state"))
    def sfp_get_module_state(self, sfp: DeviceKey) -> Optional[str]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_xcvr_api.get_cmis_rev"))
    def sfp_get_cmis_rev(self, sfp: DeviceKey) -> Optional[str]: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_xcvr_api.get_application_advertisement"))
    def sfp_get_application_advertisement(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_xcvr_api.get_datapath_state"))
    def sfp_get_datapath_state(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_xcvr_api.get_config_datapath_hostlane_status"))
    def sfp_get_config_datapath_hostlane_status(self, sfp: DeviceKey) -> Json: ...
    @platform_method(On(row="SfpInfo"), Calls("SfpBase.get_xcvr_api.get_dpinit_pending"))
    def sfp_get_dpinit_pending(self, sfp: DeviceKey) -> Json: ...

    # -- actions, addressed by key ----------------------------------------
    #
    # Each takes the `key` of the row it acts on, and the facade follows that
    # path back to the device: the object a Python consumer would have held
    # from its own traversal.  A key of another row type, or one that no
    # longer leads anywhere, is refused rather than resolved to something else.
    #
    # An action answers what its base-class method answers.  Where that is a
    # bool the action is `Optional[bool]`, None when the vendor returned
    # nothing: chassisd backs off a DPU whose transition lock is held, and an
    # action declared `None` turned the base class's False into success.
    # `generate.py` holds each declaration to the base class's docstring.

    @platform_method(On(row="FanInfo"), Calls("FanBase.set_status_led"))
    def set_fan_led(self, fan: DeviceKey, color: LedColor) -> Optional[bool]:
        """Set the LED on one fan.

        Separate from `set_fan_drawer_led` on purpose.  thermalctld sets the
        fan's LED and then its drawer's with the same colour, tolerating
        either being unimplemented (thermalctld:547-550); folding the two into
        one call would hide which of them a platform refused.
        """

    @platform_method(On(row="FanDrawerInfo"), Calls("FanDrawerBase.set_status_led"))
    def set_fan_drawer_led(self, drawer: DeviceKey, color: LedColor) -> Optional[bool]: ...
    # An int, not a `Percent` reading: what the one caller in the tree hands
    # `FanBase.set_speed`, ThermalManagerBase's `int()` of the configured
    # speed (thermal_manager_base.py:151-152, 221).
    @platform_method(On(row="FanInfo"), Calls("FanBase.set_speed"))
    def set_fan_speed(self, fan: DeviceKey, speed: int) -> Optional[bool]: ...
    @platform_method(On(row="PsuInfo"), Calls("PsuBase.set_status_led"))
    def set_psu_led(self, psu: DeviceKey, color: LedColor) -> Optional[bool]: ...

    @platform_method(On(row="ModuleInfo"), Calls("ModuleBase.get_reboot_cause"))
    def get_module_reboot_cause(self, module: DeviceKey) -> ModuleRebootCause:
        """Why a module last restarted, asked when it restarts.

        Deliberately not a column of `ModuleInfo`.  A row is built eagerly, so
        a column here would be read once per polling cycle -- and on Mellanox
        this getter *logs*: `module.py:477,482` emits a NOTICE naming the
        reason every time it is called.  As a column it produced 84 identical
        NOTICE lines per DPU in a fourteen-minute window on a SmartSwitch, 358
        lines where the Python daemon wrote 20, because Python asks only at the
        moment a module changes state (`chassisd:896,904`).

        That is not merely noise.  pmon's rsyslog is rate limited, and a flood
        of redundant NOTICE spends the budget that a real alarm needs.

        The rule this establishes: a getter with a side effect, or one whose
        answer is meaningful per event rather than per cycle, is a method the
        caller invokes, not a column the row carries.

        `get_reboot_cause()` answers `(cause, detail)` and both halves are
        published; see `ModuleRebootCause` for what taking only the first one
        cost, and why the fix is a row rather than a second method.
        """

    @platform_method(On(row="ModuleInfo"), Calls("ModuleBase.get_midplane_down_reason"))
    def get_module_midplane_down_reason(self, module: DeviceKey) -> ModuleMidplaneDownReason:
        """Why a module's midplane went down, asked when it goes down.

        A method rather than a column of `ModuleInfo`, by the rule
        `get_module_reboot_cause` states: the answer means something at the
        moment of the transition, not on every polling cycle.
        """

    @platform_method(On(row="PsuInfo"), Calls("PsuBase.get_status_master_led"))
    def get_psu_master_led(self, psu: DeviceKey) -> Optional[str]:
        """The colour of the LED every hot-swappable PSU shares.

        `PsuBase.get_status_master_led` is a `@classmethod` over a class
        attribute, so any PSU answers for all of them; a PSU row's key is how
        the facade reaches an instance to ask.
        """

    @platform_method(On(row="PsuInfo"), Calls("PsuBase.set_status_master_led"))
    def set_psu_master_led(self, psu: DeviceKey, color: LedColor) -> Optional[bool]:
        """One LED shared by every hot-swappable PSU.

        Addressed through a PSU row like the getter, and for the same reason:
        `set_status_master_led` is a `@classmethod` on `PsuBase`, so any PSU
        sets it for all of them -- but it is not on the chassis, and reaching
        for it there would fail on every platform.
        """

    @platform_method(On(row="ModuleInfo"), Calls("ModuleBase.reboot"))
    def reboot_module(self, module: DeviceKey, reboot_type: str) -> Optional[bool]: ...
    # `up` reaches the platform as 1 or 0, chassisd's MODULE_ADMIN_UP and
    # MODULE_ADMIN_DOWN (chassisd:103-104, 333, 377, 1422-1423); see `Calls`.
    @platform_method(On(row="ModuleInfo"), Calls("ModuleBase.set_admin_state", ints=("up",)))
    def set_module_admin_state(self, module: DeviceKey, up: bool) -> Optional[bool]: ...
    @platform_method(On(row="ModuleInfo"),
                     Calls("ModuleBase.set_admin_state_gracefully", ints=("up",)))
    def set_module_admin_state_gracefully(self, module: DeviceKey, up: bool) -> Optional[bool]:
        """Admin-down that lets the module's services stop first.

        Separate from `set_module_admin_state` because it blocks for as long
        as the halt takes, and a caller polling on a timer needs to know which
        of the two it asked for.
        """

    @platform_method(On(row="ModuleInfo"), Calls("ModuleBase.do_power_cycle"))
    def power_cycle_module(self, module: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="ModuleInfo"), Calls("ModuleBase.module_pre_shutdown"))
    def module_pre_shutdown(self, module: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="ModuleInfo"), Calls("ModuleBase.module_post_startup"))
    def module_post_startup(self, module: DeviceKey) -> Optional[bool]: ...

    @platform_method(
        On(row="ModuleInfo", pass_key=True),
        Calls("ModuleBase.set_module_state_transition"),
    )
    def set_module_state_transition(self, module: DeviceKey, transition_type: str) -> Optional[bool]:
        """`pass_key`: the base class takes the module's own name as well.

        False is the answer that matters: another operation holds the module
        and has not timed out, and the caller must leave it alone.
        """

    @platform_method(
        On(row="ModuleInfo", pass_key=True),
        Calls("ModuleBase.clear_module_state_transition"),
    )
    def clear_module_state_transition(self, module: DeviceKey) -> Optional[bool]: ...
    @platform_method(On(row="ModuleInfo"), Calls("ModuleBase.clear_module_gnoi_halt_in_progress"))
    def clear_module_gnoi_halt(self, module: DeviceKey) -> Optional[bool]: ...

    @platform_method(On(row="SensorInfo"), Calls("SensorBase.set_high_threshold"))
    def set_sensor_high_threshold(self, sensor: DeviceKey, value: Threshold) -> Optional[bool]: ...
    @platform_method(On(row="SensorInfo"), Calls("SensorBase.set_low_threshold"))
    def set_sensor_low_threshold(self, sensor: DeviceKey, value: Threshold) -> Optional[bool]: ...

    # -- from a name to a key --------------------------------------------
    #
    # A caller that starts from a name -- a CONFIG_DB key, a command-line
    # argument -- resolves it the way the Python consumer it replaces does,
    # rather than the facade guessing which of several devices a name meant.

    @platform_method(
        EscapeHatch(
            reaches=("ChassisBase.get_module_index",),
            reason="answers the key the index leads to, not the index",
        )
    )
    def get_module_key(self, name: str) -> Optional[DeviceKey]:
        """The key of the module `ChassisBase.get_module_index(name)` names.

        chassisd's resolution of a CONFIG_DB module key (chassisd:323): the
        index is the module's position in `get_all_modules()`, and a negative
        one, the base class's and the vendors' way of saying there is no such
        module, answers None.  An exception is the vendor's, as in Python.
        """

    @platform_method(
        EscapeHatch(
            reaches=("ChassisBase.get_all_components", "ComponentBase.get_name"),
            reason="a name is resolved within one parent, and a duplicate is refused",
        )
    )
    def get_component_key(self, name: str) -> Optional[DeviceKey]:
        """The key of the chassis component called `name`.

        fwutil's resolution for `fwutil ... chassis component <name>`
        (`fwutil/lib.py`, `PlatformDataProvider`): by name among the chassis's
        `get_all_components()`.  None when nothing matches.  Where two match,
        fwutil keeps the last one it listed; this raises instead, because
        acting on one of them silently is the defect the key exists to remove.
        """

    @platform_method(
        EscapeHatch(
            reaches=(
                "ChassisBase.is_modular_chassis",
                "ChassisBase.get_all_modules",
                "ModuleBase.get_name",
                "ModuleBase.get_all_components",
                "ComponentBase.get_name",
            ),
            reason="see get_component_key",
        )
    )
    def get_module_component_key(self, module: str, name: str) -> Optional[DeviceKey]:
        """The key of the component called `name` on the module called `module`.

        fwutil's resolution for `fwutil ... module <module> component <name>`:
        the module by its `get_name()` among `get_all_modules()`, on a modular
        chassis only, as fwutil refuses anything else; then the component by
        its name among that module's.  None when either is not there; a
        duplicate at either level raises, as in `get_component_key`.
        """

    # -- component firmware: queries that take an argument -----------------
    #
    # Not columns.  Each answers about an image the caller names, so there is
    # nothing to put in a snapshot -- a row would have to carry an answer for
    # every image that might ever be offered.

    @platform_method(
        On(row="ComponentInfo"),
        Calls("ComponentBase.get_available_firmware_version"),
    )
    def get_available_firmware_version(
        self, component: DeviceKey, image_path: str
    ) -> Optional[str]: ...
    @platform_method(
        On(row="ComponentInfo"),
        Calls("ComponentBase.get_firmware_update_notification"),
    )
    def get_firmware_update_notification(
        self, component: DeviceKey, image_path: str
    ) -> Optional[str]: ...
    @platform_method(On(row="ComponentInfo"), Calls("ComponentBase.install_firmware"))
    def install_firmware(self, component: DeviceKey, image_path: str) -> Optional[bool]: ...
    @platform_method(On(row="ComponentInfo"), Calls("ComponentBase.update_firmware"))
    def update_firmware(self, component: DeviceKey, image_path: str) -> Optional[bool]:
        """`ComponentBase.update_firmware` returns False on a missing path and
        nothing at all on success, so only a False says anything."""

    @platform_method(On(row="ComponentInfo"), Calls("ComponentBase.auto_update_firmware"))
    def auto_update_firmware(
        self, component: DeviceKey, image_path: str, boot_type: str
    ) -> Optional[int]:
        """Returns one of `ComponentBase.FW_AUTO_*`."""

    # -- watchdog ----------------------------------------------------------

    @platform_method(Calls("ChassisBase.get_watchdog.arm"))
    def arm_watchdog(self, seconds: int) -> Optional[int]:
        """Arm, and say for how long it actually armed.

        `WatchdogBase.arm` answers the seconds it settled on, which need not
        be the seconds asked for, and -1 on failure.
        """

    @platform_method(Calls("ChassisBase.get_watchdog.disarm"))
    def disarm_watchdog(self) -> Optional[bool]: ...

    @platform_method(Calls("ChassisBase.initizalize_system_led"))
    def initialize_system_led(self) -> Optional[bool]:
        """The base class spells this `initizalize_system_led`.

        The typo is part of the shipped API, so `Calls` carries it; the facade
        does not have to repeat it.
        """

    @platform_method(Calls("ChassisBase.init_midplane_switch"))
    def init_midplane_switch(self) -> Optional[bool]: ...

    @platform_method(Calls("ChassisBase.set_status_led"))
    def set_chassis_led(self, color: str) -> Optional[bool]:
        """The whole platform API surface healthd reaches.

        `health_checker/manager.py:77`.  It is not a pmon daemon -- it runs on
        the host -- which is why this one method is worth naming.

        The colour is a `str`, not a `LedColor`: healthd takes it from the
        platform's `system_health_monitoring_config.json`, where vendors use
        their own ("amber_blink", "orange_blink", "yellow").  The answer is
        `set_status_led`'s bool, so a caller can log a set that failed.
        """

    # -- sed ---------------------------------------------------------------

    @platform_method(Calls("ChassisBase.get_sed_mgmt.change_sed_password"))
    def change_sed_password(self, new_password: str) -> Optional[bool]: ...
    @platform_method(Calls("ChassisBase.get_sed_mgmt.reset_sed_password"))
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
    @platform_method(EscapeHatch(reason="see tm_initialize"))
    def tm_stop(self) -> None:
        """`ThermalManager.stop()` alone, which thermalctld's signal handler
        calls the moment SIGTERM arrives (thermalctld:1610-1612), well
        before its `deinit()` runs `deinitialize()`."""

    @platform_method(
        EscapeHatch(
            reason="Not a base-class method.  A vendor may install SIGTERM/SIGINT "
            "handlers while its chassis is built so that its readiness waits abort "
            "on shutdown -- mlnx's utils.watch_shutdown_signals() (chassis.py:151), "
            "whose event ends the 300 s wait in ThermalUpdater.start() on SPC1.  In "
            "a Rust daemon the daemon owns the signals, so the bridge keeps those "
            "handlers when the chassis is built and this runs them."
        )
    )
    def notify_shutdown(self) -> None:
        """The daemon is shutting down: let the platform abort what it waits for.

        What a Python daemon gets from the vendor's own signal handler, given
        when the Rust daemon handles SIGTERM or SIGINT, before it joins its
        threads.  Idempotent, safe from any thread and on any handle (what it
        acts on is process-wide), and it never raises: a shutdown is not
        stopped by a vendor handler that failed.
        """

    @platform_method(
        EscapeHatch(
            reaches=("ChassisBase.get_eeprom",),
            reason="The platform writes this table itself.  `Eeprom.update_eeprom_db()` "
            "(sonic_platform_base/sonic_eeprom/eeprom_tlvinfo.py, which every vendor "
            "Eeprom subclasses) decodes the raw EEPROM and hmsets EEPROM_INFO through "
            "an EepromRedisVisitor: a TlvHeader row, a Checksum row, a State row, and "
            "one row per TLV carrying Name, Len and Value. `get_system_eeprom_info()` "
            "-- the source get_eeprom() rows come from -- answers only code->value, so "
            "rebuilding that table from the rows would publish a strictly poorer one "
            "and `show platform syseeprom` would lose the names and lengths. Calling "
            "the platform's own writer keeps the table byte-identical to the Python "
            "daemon's; the alternative is reimplementing ONIE TLV decoding in Rust. "
            "A platform API that writes a database is a layering fault, and phase 2 "
            "cannot carry this method across as-is -- it is declared here so that is "
            "a decision someone makes rather than discovers."
        )
    )
    def eeprom_update_db(self) -> EepromUpdate:
        """Re-read the system EEPROM and let the platform republish EEPROM_INFO.

        `read_failed` when the platform could not read it, `update_failed`
        when it read it and could not write the table; the daemon logs which
        (syseepromd:85-96), and the table is left as it was rather than
        half-written.
        """


    @platform_method(
        EscapeHatch(
            reaches=(
                "StorageBase.fetch_parse_info",
                "StorageBase.get_model",
                "StorageBase.get_serial",
                "StorageBase.get_firmware",
                "StorageBase.get_health",
                "StorageBase.get_temperature",
                "StorageBase.get_disk_io_reads",
                "StorageBase.get_disk_io_writes",
                "StorageBase.get_reserved_blocks",
                "StorageCommon.get_fs_io_reads",
                "StorageCommon.get_fs_io_writes",
            ),
            reason="stormond does not reach the platform through the chassis either: "
            "`StorageDevices()` walks /sys/block and picks a utility class per disk, "
            "and the object it picks may be None.  The readings are only valid after "
            "`fetch_parse_info(/dev/<disk>)` has been called for that disk -- an "
            "ordering no column annotation expresses, and the reason this is one "
            "method rather than eleven.",
        ),
    )
    def get_storage_devices(self) -> list[StorageDeviceInfo]:
        """Every disk in /sys/block, refreshed.

        Calls `fetch_parse_info` for each disk before reading it, which is what
        makes the firmware, health and temperature current rather than whatever
        the constructor saw.
        """

    @platform_method(
        EscapeHatch(
            reaches=("PcieUtil.get_pcie_check",),
            reason="pcied does not reach the platform through the chassis at all: it "
            "constructs `sonic_platform.pcie.Pcie(platform_path)`, or "
            "`sonic_platform_base.sonic_pcie.pcie_common.PcieUtil` when the vendor "
            "ships none, and that two-step import with a fallback is a decision "
            "rather than a call.  The rows are the yaml's own columns with hex "
            "strings parsed; nothing else is reshaped.",
        ),
    )
    def get_pcie_devices(self) -> list[PcieDevice]:
        """Every device `pcie.yaml` expects, and whether the bus has it.

        Empty when the platform ships no config file, which is not an error:
        a platform without PCIe checking simply has nothing to say.
        `PcieUtil.load_config_file` answers a missing one with `sys.exit()`,
        which ends a Python daemon; here it is taken as the empty list it
        means, and the platform is not asked again.
        """

    @platform_method(
        EscapeHatch(
            reaches=("PcieUtil.get_pcie_aer_stats",),
            reason="Same object as get_pcie_devices, so the same two-step "
            "construction; and the answer is a mapping of mappings whose keys are "
            "whatever the kernel printed in aer_dev_correctable and its two "
            "siblings, which no column list can enumerate.",
        ),
    )
    def get_pcie_aer_stats(self, bus: int, dev: int, func: int) -> list[PcieAerStat]:
        """The AER counters of one device, flattened out of the three severities.

        Empty when the device exposes no AER files, which most do not.
        """

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
    )
    def get_change_event(self, timeout_ms: int) -> ChangeEventBatch:
        """Block until something changes, or until `timeout_ms` elapses.

        `timeout_ms=0` blocks indefinitely, which is what the base class means
        by it and what the daemons rely on.
        """
