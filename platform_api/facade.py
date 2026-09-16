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
"""The Python facade over the vendor's platform API.

GENERATED from platform_api/facade.pyi by generator/generate.py.  Do not edit:
regenerate.  Adding a field or a row is one edit, to the stub.

Every base-class call here goes through `_call`, which treats a `None` return
exactly as it treats `NotImplementedError`.  That is not a simplification --
it is what every daemon's own `try_get()` already does (thermalctld:104,
psud:272, chassisd:183, sensormond:36, bmcctld:297), and the facade has to
reproduce it or the rows it publishes differ from the rows the Python daemons
publish today.
"""

from typing import Literal

from . import _escape_hatch

# Base-class methods a consumer reaches that this facade deliberately does not
# declare, and why.  Here at runtime as well as in the stub so that the answer
# to "why is there no get_num_psus" is in the module somebody is reading.
OMITTED = (
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
    ("ChassisBase.get_all_fans", "already reached through drawer, module or PSU"),
    ("LiquidCoolingBase.get_leak_sensor_status", "duplicate of get_all_leak_sensors"),
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
    ("LeakSensorProfileBase.get_leak_max_minor_duration_sec", "LeakProfile.max_minor_duration_sec"),
    ("PlatformBase.get_chassis", "the bridge\u0027s constructor, not a facade call"),
    ("ModuleBase.get_state_db", "the caller opens its own DB connection"),
)


LedColor = Literal["green", "amber", "red", "off"]
FanDirection = Literal["intake", "exhaust", "N/A"]
FanKind = Literal["drawer", "module", "psu"]
PowerEntityKind = Literal["psu", "pdb"]
ModuleType = Literal["SUPERVISOR", "LINE-CARD", "FABRIC-CARD", "DPU", "SWITCH-HOST"]
ModuleStatus = Literal["Empty", "Offline", "PoweredDown", "Present", "Fault", "Online"]
SensorKind = Literal["voltage", "current"]
LeakSeverity = Literal["MINOR", "CRITICAL"]
ChangeEventKind = Literal["removed", "inserted", "i2c_stuck", "bad_eeprom", "unsupported_cable", "high_temperature", "bad_cable"]


def _call(fn, default=None):
    """Invoke a base-class getter, or say it is not there.

    Three ways a platform declines to answer, collapsed into one: the method
    is absent, it raises `NotImplementedError`, or it returns None.  A fourth
    -- `return NotImplementedError`, which five base-class methods write and
    which hands back a truthy class object -- is caught here too.
    """
    if fn is None:
        return default
    try:
        r = fn()
    except NotImplementedError:
        return default
    if r is None or r is NotImplementedError:
        return default
    return r


def _get(obj, name):
    return getattr(obj, name, None)


def _iter(seq):
    return seq if seq is not None else ()


def _pairs(mapping):
    """A mapping as (key, value) pairs, in the order the platform read them.

    Nothing for a platform that answered something other than a mapping: this
    runs in a polling loop, and the alternative is an AttributeError every
    cycle on hardware that is merely unusual.
    """
    return mapping.items() if hasattr(mapping, 'items') else ()


def _one(obj):
    """A singular accessor as a list of at most one.

    `get_watchdog()` answers one object or nothing.  Iterating it directly
    would be a TypeError on most platforms, and on one that answered a string
    it would be one row per character.
    """
    return () if obj is None else (obj,)


def _default(v, d):
    return d if v is None else v


def _at(v, i):
    """One slot of a fixed-arity tuple return.

    A platform that answered with something unindexable, or with a shorter
    tuple than the base class documents, reads as absent rather than as a
    crash in a polling loop.
    """
    if v is None:
        return None
    try:
        return v[i]
    except (TypeError, IndexError, KeyError):
        return None


def _fmt(v, template, parent, i):
    """A name, or the key its consumers already publish it under."""
    if v is not None:
        return str(v)
    return template.format(parent=parent, i=i + 1)


def _scalar(v, sentinels, coerce_from):
    """`Observed()`: a sentinel is a missing reading, not a value.

    Vendors return the number as int, str or a numpy scalar as readily as
    float, at positions the base class documents as float.  Both this and the
    Rust bridge normalise through the same declared table, so the two sides
    cannot disagree about what "no reading" looks like.
    """
    if v is None:
        return None
    for s in sentinels:
        if v == s:
            return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    for kind in coerce_from:
        if kind == 'str' and isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return None
        if kind == 'int':
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    return None



class ThermalInfo(object):
    """One temperature sensor, wherever in the tree it is mounted."""

    __slots__ = ('name', 'parent_name', 'position_in_parent', 'is_replaceable', 'temperature', 'high_threshold', 'low_threshold', 'high_critical_threshold', 'low_critical_threshold', 'min_recorded', 'max_recorded', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('ThermalInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'ThermalInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, ThermalInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class FanInfo(object):
    """One fan.  `kind` says where it is mounted, which is what decides
    whether `drawer_name` means anything."""

    __slots__ = ('name', 'kind', 'parent_name', 'drawer_name', 'position_in_parent', 'presence', 'status', 'is_replaceable', 'model', 'serial', 'speed_pct', 'target_speed_pct', 'direction', 'is_under_speed', 'is_over_speed', 'status_led', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('FanInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'FanInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, FanInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class FanDrawerInfo(object):
    """One fan drawer: the field-replaceable unit a chassis fan sits in."""

    __slots__ = ('name', 'position_in_parent', 'presence', 'status', 'is_replaceable', 'model', 'serial', 'status_led', 'maximum_consumed_power', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('FanDrawerInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'FanDrawerInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, FanDrawerInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class PsuInfo(object):
    """A PSU or a PDB.  `PdbBase` extends `PsuBase` and psud publishes both
    into the same table, so they are one row type with a `kind`."""

    __slots__ = ('name', 'kind', 'position_in_parent', 'presence', 'is_replaceable', 'model', 'serial', 'revision', 'power_good', 'status_led', 'voltage', 'current', 'power', 'input_voltage', 'input_current', 'input_power', 'temperature', 'temperature_high_threshold', 'voltage_high_threshold', 'voltage_low_threshold', 'maximum_supplied_power', 'power_warning_suppress_threshold', 'power_critical_threshold', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('PsuInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'PsuInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, PsuInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class ChassisInfo(object):
    """The chassis itself.  A singleton: there is one, and it is the device."""

    __slots__ = ('name', 'presence', 'model', 'serial', 'revision', 'status', 'base_mac', 'is_modular_chassis', 'is_smartswitch', 'is_dpu', 'is_bmc', 'is_liquid_cooled', 'reboot_cause', 'reboot_cause_detail', 'my_slot', 'supervisor_slot', 'dpu_id', 'dataplane_state', 'controlplane_state', 'status_led', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('ChassisInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'ChassisInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, ChassisInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class ModuleInfo(object):
    """One line card, fabric card, supervisor or DPU."""

    __slots__ = ('name', 'parent_name', 'position_in_parent', 'presence', 'status', 'is_replaceable', 'model', 'serial', 'description', 'slot', 'type', 'oper_status', 'base_mac', 'dpu_id', 'maximum_consumed_power', 'midplane_ip', 'is_midplane_reachable', 'reboot_cause', 'reboot_cause_detail', 'state_transition', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('ModuleInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'ModuleInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, ModuleInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class ComponentInfo(object):
    """One field-upgradeable component: a BIOS, a CPLD, an FPGA, an SSD."""

    __slots__ = ('name', 'parent_name', 'description', 'firmware_version', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('ComponentInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'ComponentInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, ComponentInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class SensorInfo(object):
    """One voltage or current sensor.

    `kind` rather than two row types: the columns are identical, the daemon
    publishes them to two tables off the same loop, and a consumer that wanted
    only one filters."""

    __slots__ = ('name', 'kind', 'parent_name', 'position_in_parent', 'is_replaceable', 'unit', 'value', 'high_threshold', 'low_threshold', 'high_critical_threshold', 'low_critical_threshold', 'min_recorded', 'max_recorded', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('SensorInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'SensorInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, SensorInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class LeakProfile(object):
    """A named leak policy, published once at start-up.

    Separate from `LeakSensorInfo` because the daemon publishes it to its own
    table once rather than every cycle, and because several sensors share one."""

    __slots__ = ('type', 'max_minor_duration_sec', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('LeakProfile got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'LeakProfile(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, LeakProfile):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class LeakSensorInfo(object):
    """One liquid-cooling leak sensor."""

    __slots__ = ('name', 'parent_name', 'sensor_type', 'location', 'is_leak', 'is_ok', 'severity', 'profile_type', 'profile_max_minor_duration_sec', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('LeakSensorInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'LeakSensorInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, LeakSensorInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class WatchdogInfo(object):
    """The hardware watchdog.  A singleton per chassis."""

    __slots__ = ('is_armed', 'remaining_time', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('WatchdogInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'WatchdogInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, WatchdogInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class ChangeEvent(object):
    """One device that changed, out of the two-level mapping the base class
    returns.

    `{'fan': {'0': '0', '2': '1'}, 'sfp': {'11': '0'}}` becomes three rows.
    The nesting carries no information a row cannot: the outer key is the
    device type and the inner key is the device id, and a consumer that wanted
    them grouped can group them."""

    __slots__ = ('device_type', 'device_id', 'status', 'kind', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('ChangeEvent got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'ChangeEvent(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, ChangeEvent):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class ChangeEventBatch(object):
    """What one `get_change_event` call answered.

    `ok` is carried rather than raised on.  It reads like a success flag and
    is not one: `ok=False` is how a platform reports a system-level event,
    with the detail in the mapping under the key the daemon watches for
    (xcvrd:301-323 maps the pair to SYSTEM_NOT_READY or SYSTEM_FAIL).  A
    facade that raised on it would delete that path.

    `ok=True` with no events is the ordinary timeout: nothing changed."""

    __slots__ = ('ok', 'events', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('ChangeEventBatch got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'ChangeEventBatch(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, ChangeEventBatch):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class EepromTlv(object):
    """One entry of a system EEPROM.

    The base class answers a mapping whose keys are ONIE TLV codes as hex
    strings on the chassis, and Redfish field names on the BMC.  Neither key
    set is enumerable ahead of time -- which is exactly why this is rows and
    not columns."""

    __slots__ = ('source', 'parent_name', 'code', 'value', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('EepromTlv got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'EepromTlv(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, EepromTlv):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class AsicInfo(object):
    """One ASIC on a module, and where it sits on the PCI bus."""

    __slots__ = ('parent_name', 'asic_id', 'pci_address', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('AsicInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'AsicInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, AsicInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class BmcInfo(object):
    """The board management controller.  A list of at most one."""

    __slots__ = ('name', 'presence', 'model', 'serial', 'revision', 'status', 'is_replaceable', 'version', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('BmcInfo got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'BmcInfo(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, BmcInfo):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class BmcResult(object):
    """What a BMC command answered.

    Every BMC method returns `(code, message)`, with 0 meaning success. The
    code is carried rather than raised on: the CLI prints the message on a
    non-zero code and carries on, and a facade that raised would turn a
    reported failure into an exception the caller has to translate back."""

    __slots__ = ('code', 'message', 'session_id', 'token', 'task_id', )

    def __init__(self, **fields):
        """Keyword-only, and uniform across every row.

        Spelling the columns out again here would duplicate `__slots__`, which
        is the list the stub already carries -- and a constructor that drifts
        from it is exactly what the generator exists to prevent.
        """
        for key in self.__slots__:
            setattr(self, key, fields.pop(key, None))
        if fields:
            raise TypeError('BmcResult got unexpected field(s): %s'
                            % ', '.join(sorted(fields)))

    def __repr__(self):
        return 'BmcResult(%s)' % ', '.join(
            '%s=%r' % (k, getattr(self, k)) for k in self.__slots__)

    def __eq__(self, other):
        if not isinstance(other, BmcResult):
            return NotImplemented
        return all(getattr(self, k) == getattr(other, k) for k in self.__slots__)


class PlatformApi(object):
    """Rows and actions over a vendor's `ChassisBase`."""

    def __init__(self, chassis):
        self._chassis = chassis
        self._hatch = _escape_hatch.EscapeHatches(chassis)

    def _row_thermal_info(self, dev, parent, i, fixed):
        return ThermalInfo(
            name=_fmt(_call(_get(dev, 'get_name')), '{parent} Thermal {i}', parent, i),
            parent_name=parent,
            position_in_parent=_default(_call(_get(dev, 'get_position_in_parent')), -1),
            is_replaceable=_default(_call(_get(dev, 'is_replaceable')), False),
            temperature=_scalar(_call(_get(dev, 'get_temperature')), ('N/A',), ('int', 'str')),
            high_threshold=_scalar(_call(_get(dev, 'get_high_threshold')), ('N/A',), ('int', 'str')),
            low_threshold=_scalar(_call(_get(dev, 'get_low_threshold')), ('N/A',), ('int', 'str')),
            high_critical_threshold=_scalar(_call(_get(dev, 'get_high_critical_threshold')), ('N/A',), ('int', 'str')),
            low_critical_threshold=_scalar(_call(_get(dev, 'get_low_critical_threshold')), ('N/A',), ('int', 'str')),
            min_recorded=_scalar(_call(_get(dev, 'get_minimum_recorded')), ('N/A',), ('int', 'str')),
            max_recorded=_scalar(_call(_get(dev, 'get_maximum_recorded')), ('N/A',), ('int', 'str')),
        )

    def _walk_thermal_info(self):
        """Every ThermalInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # ChassisBase.get_all_thermals
        for i, dev in enumerate(_iter(_call(_get(self._chassis, 'get_all_thermals')))):
            out.append((self._row_thermal_info(dev, 'chassis 1', i, {}), dev))
        # PsuBase.get_all_thermals via ChassisBase.get_all_psus
        for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_psus')))):
            if not _call(_get(o0, 'get_presence')):
                continue
            p0 = _fmt(_call(_get(o0, 'get_name')), 'PSU {i}', '', i0)
            for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_thermals')))):
                out.append((self._row_thermal_info(dev, p0, i, {}), dev))
        # PdbBase.get_all_thermals via ChassisBase.get_all_pdbs
        try:
            for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_pdbs')))):
                if not _call(_get(o0, 'get_presence')):
                    continue
                p0 = _fmt(_call(_get(o0, 'get_name')), 'PDB {i}', '', i0)
                for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_thermals')))):
                    out.append((self._row_thermal_info(dev, p0, i, {}), dev))
        except NotImplementedError:
            pass
        # ModuleBase.get_all_thermals via ChassisBase.get_all_modules
        if _call(_get(self._chassis, 'is_modular_chassis')):
            for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_modules')))):
                p0 = _fmt(_call(_get(o0, 'get_name')), 'Module {i}', '', i0)
                for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_thermals')))):
                    out.append((self._row_thermal_info(dev, p0, i, {}), dev))
        # PsuBase.get_all_thermals via ChassisBase.get_all_modules -> ModuleBase.get_all_psus
        if _call(_get(self._chassis, 'is_modular_chassis')):
            for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_modules')))):
                p0 = _fmt(_call(_get(o0, 'get_name')), 'Module {i}', '', i0)
                for i1, o1 in enumerate(_iter(_call(_get(o0, 'get_all_psus')))):
                    if not _call(_get(o1, 'get_presence')):
                        continue
                    p1 = _fmt(_call(_get(o1, 'get_name')), '{parent} PSU {i}', p0, i1)
                    for i, dev in enumerate(_iter(_call(_get(o1, 'get_all_thermals')))):
                        out.append((self._row_thermal_info(dev, p1, i, {}), dev))
        return out


    def _row_fan_info(self, dev, parent, i, fixed):
        return FanInfo(
            name=_fmt(_call(_get(dev, 'get_name')), '{parent} fan {i}', parent, i),
            kind=fixed['kind'],
            parent_name=parent,
            drawer_name=fixed['drawer_name'],
            position_in_parent=_default(_call(_get(dev, 'get_position_in_parent')), -1),
            presence=_default(_call(_get(dev, 'get_presence')), False),
            status=_default(_call(_get(dev, 'get_status')), False),
            is_replaceable=_default(_call(_get(dev, 'is_replaceable')), False),
            model=_call(_get(dev, 'get_model')),
            serial=_call(_get(dev, 'get_serial')),
            speed_pct=_scalar(_call(_get(dev, 'get_speed')), ('N/A',), ('int', 'str')),
            target_speed_pct=_scalar(_call(_get(dev, 'get_target_speed')), ('N/A',), ('int', 'str')),
            direction=_call(_get(dev, 'get_direction')),
            is_under_speed=_call(_get(dev, 'is_under_speed')),
            is_over_speed=_call(_get(dev, 'is_over_speed')),
            status_led=_call(_get(dev, 'get_status_led')),
        )

    def _walk_fan_info(self):
        """Every FanInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # FanDrawerBase.get_all_fans via ChassisBase.get_all_fan_drawers
        for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_fan_drawers')))):
            p0 = _fmt(_call(_get(o0, 'get_name')), 'chassis 1', '', i0)
            for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_fans')))):
                out.append((self._row_fan_info(dev, p0, i, {'kind': 'drawer', 'drawer_name': p0}), dev))
        # ModuleBase.get_all_fans via ChassisBase.get_all_modules
        for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_modules')))):
            p0 = _fmt(_call(_get(o0, 'get_name')), 'Module {i}', '', i0)
            for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_fans')))):
                out.append((self._row_fan_info(dev, p0, i, {'kind': 'module', 'drawer_name': 'N/A'}), dev))
        # PsuBase.get_all_fans via ChassisBase.get_all_psus
        for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_psus')))):
            p0 = _fmt(_call(_get(o0, 'get_name')), 'PSU {i}', '', i0)
            for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_fans')))):
                out.append((self._row_fan_info(dev, p0, i, {'kind': 'psu', 'drawer_name': 'N/A'}), dev))
        return out

    def _find_fan_info(self, name):
        """The device behind a published FanInfo name."""
        for row, dev in self._walk_fan_info():
            if row.name == name:
                return dev
        raise KeyError('no FanInfo named %r' % name)


    def _row_fan_drawer_info(self, dev, parent, i, fixed):
        return FanDrawerInfo(
            name=_fmt(_call(_get(dev, 'get_name')), 'drawer {i}', parent, i),
            position_in_parent=_default(_call(_get(dev, 'get_position_in_parent')), -1),
            presence=_default(_call(_get(dev, 'get_presence')), False),
            status=_call(_get(dev, 'get_status')),
            is_replaceable=_default(_call(_get(dev, 'is_replaceable')), False),
            model=_call(_get(dev, 'get_model')),
            serial=_call(_get(dev, 'get_serial')),
            status_led=_call(_get(dev, 'get_status_led')),
            maximum_consumed_power=_scalar(_call(_get(dev, 'get_maximum_consumed_power')), ('N/A',), ('int', 'str')),
        )

    def _walk_fan_drawer_info(self):
        """Every FanDrawerInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # ChassisBase.get_all_fan_drawers
        for i, dev in enumerate(_iter(_call(_get(self._chassis, 'get_all_fan_drawers')))):
            out.append((self._row_fan_drawer_info(dev, 'chassis 1', i, {}), dev))
        return out

    def _find_fan_drawer_info(self, name):
        """The device behind a published FanDrawerInfo name."""
        for row, dev in self._walk_fan_drawer_info():
            if row.name == name:
                return dev
        raise KeyError('no FanDrawerInfo named %r' % name)


    def _row_psu_info(self, dev, parent, i, fixed):
        return PsuInfo(
            name=_fmt(_call(_get(dev, 'get_name')), 'PSU {i}', parent, i),
            kind=fixed['kind'],
            position_in_parent=_default(_call(_get(dev, 'get_position_in_parent')), -1),
            presence=_default(_call(_get(dev, 'get_presence')), False),
            is_replaceable=_default(_call(_get(dev, 'is_replaceable')), False),
            model=_call(_get(dev, 'get_model')),
            serial=_call(_get(dev, 'get_serial')),
            revision=_call(_get(dev, 'get_revision')),
            power_good=_default(_call(_get(dev, 'get_powergood_status')), False),
            status_led=_call(_get(dev, 'get_status_led')),
            voltage=_scalar(_call(_get(dev, 'get_voltage')), ('N/A',), ('int', 'str')),
            current=_scalar(_call(_get(dev, 'get_current')), ('N/A',), ('int', 'str')),
            power=_scalar(_call(_get(dev, 'get_power')), ('N/A',), ('int', 'str')),
            input_voltage=_scalar(_call(_get(dev, 'get_input_voltage')), ('N/A',), ('int', 'str')),
            input_current=_scalar(_call(_get(dev, 'get_input_current')), ('N/A',), ('int', 'str')),
            input_power=_scalar(_call(_get(dev, 'get_input_power')), ('N/A',), ('int', 'str')),
            temperature=_scalar(_call(_get(dev, 'get_temperature')), ('N/A',), ('int', 'str')),
            temperature_high_threshold=_scalar(_call(_get(dev, 'get_temperature_high_threshold')), ('N/A',), ('int', 'str')),
            voltage_high_threshold=_scalar(_call(_get(dev, 'get_voltage_high_threshold')), ('N/A',), ('int', 'str')),
            voltage_low_threshold=_scalar(_call(_get(dev, 'get_voltage_low_threshold')), ('N/A',), ('int', 'str')),
            maximum_supplied_power=_scalar(_call(_get(dev, 'get_maximum_supplied_power')), ('N/A',), ('int', 'str')),
            power_warning_suppress_threshold=_scalar(_call(_get(dev, 'get_psu_power_warning_suppress_threshold')), ('N/A',), ('int', 'str')),
            power_critical_threshold=_scalar(_call(_get(dev, 'get_psu_power_critical_threshold')), ('N/A',), ('int', 'str')),
        )

    def _walk_psu_info(self):
        """Every PsuInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # ChassisBase.get_all_psus
        for i, dev in enumerate(_iter(_call(_get(self._chassis, 'get_all_psus')))):
            out.append((self._row_psu_info(dev, 'PSU {i}', i, {'kind': 'psu'}), dev))
        # ChassisBase.get_all_pdbs
        try:
            for i, dev in enumerate(_iter(_call(_get(self._chassis, 'get_all_pdbs')))):
                out.append((self._row_psu_info(dev, 'PDB {i}', i, {'kind': 'pdb'}), dev))
        except NotImplementedError:
            pass
        return out

    def _find_psu_info(self, name):
        """The device behind a published PsuInfo name."""
        for row, dev in self._walk_psu_info():
            if row.name == name:
                return dev
        raise KeyError('no PsuInfo named %r' % name)


    def _row_chassis_info(self, dev, parent, i, fixed):
        return ChassisInfo(
            name=_default(_call(_get(dev, 'get_name')), 'chassis 1'),
            presence=_default(_call(_get(dev, 'get_presence')), True),
            model=_call(_get(dev, 'get_model')),
            serial=_call(_get(dev, 'get_serial')),
            revision=_call(_get(dev, 'get_revision')),
            status=_call(_get(dev, 'get_status')),
            base_mac=_call(_get(dev, 'get_base_mac')),
            is_modular_chassis=_default(_call(_get(dev, 'is_modular_chassis')), False),
            is_smartswitch=_default(_call(_get(dev, 'is_smartswitch')), False),
            is_dpu=_default(_call(_get(dev, 'is_dpu')), False),
            is_bmc=_default(_call(_get(dev, 'is_bmc')), False),
            is_liquid_cooled=_default(_call(_get(dev, 'is_liquid_cooled')), False),
            reboot_cause=_at(_call(_get(dev, 'get_reboot_cause')), 0),
            reboot_cause_detail=_at(_call(_get(dev, 'get_reboot_cause')), 1),
            my_slot=_scalar(_call(_get(dev, 'get_my_slot')), ('N/A',), ('int', 'str')),
            supervisor_slot=_scalar(_call(_get(dev, 'get_supervisor_slot')), ('N/A',), ('int', 'str')),
            dpu_id=_scalar(_call(_get(dev, 'get_dpu_id')), ('N/A',), ('int', 'str')),
            dataplane_state=_call(_get(dev, 'get_dataplane_state')),
            controlplane_state=_call(_get(dev, 'get_controlplane_state')),
            status_led=_call(_get(dev, 'get_status_led')),
        )

    def _walk_chassis_info(self):
        """Every ChassisInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        out.append((self._row_chassis_info(self._chassis, 'chassis 1', 0, {}), self._chassis))
        return out


    def _row_module_info(self, dev, parent, i, fixed):
        return ModuleInfo(
            name=_fmt(_call(_get(dev, 'get_name')), 'Module {i}', parent, i),
            parent_name=parent,
            position_in_parent=_default(_call(_get(dev, 'get_position_in_parent')), -1),
            presence=_default(_call(_get(dev, 'get_presence')), False),
            status=_call(_get(dev, 'get_status')),
            is_replaceable=_default(_call(_get(dev, 'is_replaceable')), False),
            model=_call(_get(dev, 'get_model')),
            serial=_call(_get(dev, 'get_serial')),
            description=_call(_get(dev, 'get_description')),
            slot=_scalar(_call(_get(dev, 'get_slot')), ('N/A',), ('int', 'str')),
            type=_call(_get(dev, 'get_type')),
            oper_status=_call(_get(dev, 'get_oper_status')),
            base_mac=_call(_get(dev, 'get_base_mac')),
            dpu_id=_scalar(_call(_get(dev, 'get_dpu_id')), ('N/A',), ('int', 'str')),
            maximum_consumed_power=_scalar(_call(_get(dev, 'get_maximum_consumed_power')), ('N/A',), ('int', 'str')),
            midplane_ip=_call(_get(dev, 'get_midplane_ip')),
            is_midplane_reachable=_call(_get(dev, 'is_midplane_reachable')),
            reboot_cause=_at(_call(_get(dev, 'get_reboot_cause')), 0),
            reboot_cause_detail=_at(_call(_get(dev, 'get_reboot_cause')), 1),
            state_transition=_call(_get(dev, 'get_module_state_transition')),
        )

    def _walk_module_info(self):
        """Every ModuleInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # ChassisBase.get_all_modules
        for i, dev in enumerate(_iter(_call(_get(self._chassis, 'get_all_modules')))):
            out.append((self._row_module_info(dev, 'chassis 1', i, {}), dev))
        return out

    def _find_module_info(self, name):
        """The device behind a published ModuleInfo name."""
        for row, dev in self._walk_module_info():
            if row.name == name:
                return dev
        raise KeyError('no ModuleInfo named %r' % name)


    def _row_component_info(self, dev, parent, i, fixed):
        return ComponentInfo(
            name=_fmt(_call(_get(dev, 'get_name')), '{parent} component {i}', parent, i),
            parent_name=parent,
            description=_call(_get(dev, 'get_description')),
            firmware_version=_call(_get(dev, 'get_firmware_version')),
        )

    def _walk_component_info(self):
        """Every ComponentInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # ChassisBase.get_all_components
        for i, dev in enumerate(_iter(_call(_get(self._chassis, 'get_all_components')))):
            out.append((self._row_component_info(dev, 'chassis 1', i, {}), dev))
        # ModuleBase.get_all_components via ChassisBase.get_all_modules
        if _call(_get(self._chassis, 'is_modular_chassis')):
            for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_modules')))):
                p0 = _fmt(_call(_get(o0, 'get_name')), 'Module {i}', '', i0)
                for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_components')))):
                    out.append((self._row_component_info(dev, p0, i, {}), dev))
        return out

    def _find_component_info(self, name):
        """The device behind a published ComponentInfo name."""
        for row, dev in self._walk_component_info():
            if row.name == name:
                return dev
        raise KeyError('no ComponentInfo named %r' % name)


    def _row_sensor_info(self, dev, parent, i, fixed):
        return SensorInfo(
            name=_fmt(_call(_get(dev, 'get_name')), '{parent} sensor {i}', parent, i),
            kind=fixed['kind'],
            parent_name=parent,
            position_in_parent=_default(_call(_get(dev, 'get_position_in_parent')), -1),
            is_replaceable=_default(_call(_get(dev, 'is_replaceable')), False),
            unit=_call(_get(dev, 'get_unit')),
            value=_scalar(_call(_get(dev, 'get_value')), ('N/A',), ('int', 'str')),
            high_threshold=_scalar(_call(_get(dev, 'get_high_threshold')), ('N/A',), ('int', 'str')),
            low_threshold=_scalar(_call(_get(dev, 'get_low_threshold')), ('N/A',), ('int', 'str')),
            high_critical_threshold=_scalar(_call(_get(dev, 'get_high_critical_threshold')), ('N/A',), ('int', 'str')),
            low_critical_threshold=_scalar(_call(_get(dev, 'get_low_critical_threshold')), ('N/A',), ('int', 'str')),
            min_recorded=_scalar(_call(_get(dev, 'get_minimum_recorded')), ('N/A',), ('int', 'str')),
            max_recorded=_scalar(_call(_get(dev, 'get_maximum_recorded')), ('N/A',), ('int', 'str')),
        )

    def _walk_sensor_info(self):
        """Every SensorInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # EscapeHatches.voltage_sensors_from_yaml
        for i, dev in enumerate(_iter(self._hatch.voltage_sensors_from_yaml())):
            out.append((self._row_sensor_info(dev, 'chassis 1', i, {'kind': 'voltage'}), dev))
        # ChassisBase.get_all_voltage_sensors
        for i, dev in enumerate(_iter(_call(_get(self._chassis, 'get_all_voltage_sensors')))):
            out.append((self._row_sensor_info(dev, 'chassis 1', i, {'kind': 'voltage'}), dev))
        # ModuleBase.get_all_voltage_sensors via ChassisBase.get_all_modules
        if _call(_get(self._chassis, 'is_modular_chassis')):
            for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_modules')))):
                p0 = _fmt(_call(_get(o0, 'get_name')), 'Module {i}', '', i0)
                for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_voltage_sensors')))):
                    out.append((self._row_sensor_info(dev, p0, i, {'kind': 'voltage'}), dev))
        # EscapeHatches.current_sensors_from_yaml
        for i, dev in enumerate(_iter(self._hatch.current_sensors_from_yaml())):
            out.append((self._row_sensor_info(dev, 'chassis 1', i, {'kind': 'current'}), dev))
        # ChassisBase.get_all_current_sensors
        for i, dev in enumerate(_iter(_call(_get(self._chassis, 'get_all_current_sensors')))):
            out.append((self._row_sensor_info(dev, 'chassis 1', i, {'kind': 'current'}), dev))
        # ModuleBase.get_all_current_sensors via ChassisBase.get_all_modules
        if _call(_get(self._chassis, 'is_modular_chassis')):
            for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_modules')))):
                p0 = _fmt(_call(_get(o0, 'get_name')), 'Module {i}', '', i0)
                for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_current_sensors')))):
                    out.append((self._row_sensor_info(dev, p0, i, {'kind': 'current'}), dev))
        return out

    def _find_sensor_info(self, name):
        """The device behind a published SensorInfo name."""
        for row, dev in self._walk_sensor_info():
            if row.name == name:
                return dev
        raise KeyError('no SensorInfo named %r' % name)


    def _row_leak_profile(self, dev, parent, i, fixed):
        return LeakProfile(
            type=_fmt(_call(_get(dev, 'get_type')), 'profile {i}', parent, i),
            max_minor_duration_sec=_scalar(_call(_get(dev, 'get_leak_max_minor_duration_sec')), ('N/A',), ('int', 'str')),
        )

    def _walk_leak_profile(self):
        """Every LeakProfile paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # LiquidCoolingBase.get_all_profiles via ChassisBase.get_liquid_cooling
        try:
            o0 = _call(_get(self._chassis, 'get_liquid_cooling'))
            i0 = 0
            if o0 is not None:
                p0 = _fmt(None, 'chassis 1', '', i0)
                for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_profiles')))):
                    out.append((self._row_leak_profile(dev, p0, i, {}), dev))
        except NotImplementedError:
            pass
        return out


    def _row_leak_sensor_info(self, dev, parent, i, fixed):
        return LeakSensorInfo(
            name=_fmt(_call(_get(dev, 'get_name')), 'leakage{i}', parent, i),
            parent_name=parent,
            sensor_type=_call(_get(dev, 'get_leak_sensor_type')),
            location=_call(_get(dev, 'get_leak_sensor_location')),
            is_leak=_call(_get(dev, 'is_leak')),
            is_ok=_call(_get(dev, 'is_leak_sensor_ok')),
            severity=_call(_get(dev, 'get_leak_severity')),
            profile_type=_call(_get(_call(_get(dev, 'get_leak_profile')), 'get_type')),
            profile_max_minor_duration_sec=_scalar(_call(_get(_call(_get(dev, 'get_leak_profile')), 'get_leak_max_minor_duration_sec')), ('N/A',), ('int', 'str')),
        )

    def _walk_leak_sensor_info(self):
        """Every LeakSensorInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # LiquidCoolingBase.get_all_leak_sensors via ChassisBase.get_liquid_cooling
        try:
            o0 = _call(_get(self._chassis, 'get_liquid_cooling'))
            i0 = 0
            if o0 is not None:
                p0 = _fmt(None, 'chassis 1', '', i0)
                for i, dev in enumerate(_iter(_call(_get(o0, 'get_all_leak_sensors')))):
                    out.append((self._row_leak_sensor_info(dev, p0, i, {}), dev))
        except NotImplementedError:
            pass
        return out


    def _row_watchdog_info(self, dev, parent, i, fixed):
        return WatchdogInfo(
            is_armed=_call(_get(dev, 'is_armed')),
            remaining_time=_scalar(_call(_get(dev, 'get_remaining_time')), ('N/A',), ('int', 'str')),
        )

    def _walk_watchdog_info(self):
        """Every WatchdogInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # ChassisBase.get_watchdog
        try:
            for i, dev in enumerate(_one(_call(_get(self._chassis, 'get_watchdog')))):
                out.append((self._row_watchdog_info(dev, 'chassis 1', i, {}), dev))
        except NotImplementedError:
            pass
        return out




    def _row_eeprom_tlv(self, dev, parent, i, fixed):
        return EepromTlv(
            source=fixed['source'],
            parent_name=parent,
            code=fixed['code'],
            value=fixed['value'],
        )

    def _walk_eeprom_tlv(self):
        """Every EepromTlv paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # ChassisBase.get_system_eeprom_info (mapping)
        try:
            for i, (k, v) in enumerate(_pairs(_call(_get(self._chassis, 'get_system_eeprom_info')))):
                out.append((self._row_eeprom_tlv(None, 'chassis 1', i, {'source': 'chassis', 'code': str(k), 'value': None if v is None else str(v)}), None))
        except NotImplementedError:
            pass
        # ModuleBase.get_system_eeprom_info (mapping) via ChassisBase.get_all_modules
        try:
            if _call(_get(self._chassis, 'is_modular_chassis')):
                for i0, o0 in enumerate(_iter(_call(_get(self._chassis, 'get_all_modules')))):
                    p0 = _fmt(_call(_get(o0, 'get_name')), 'Module {i}', '', i0)
                    for i, (k, v) in enumerate(_pairs(_call(_get(o0, 'get_system_eeprom_info')))):
                        out.append((self._row_eeprom_tlv(None, p0, i, {'source': 'module', 'code': str(k), 'value': None if v is None else str(v)}), None))
        except NotImplementedError:
            pass
        # BMCBase.get_eeprom (mapping) via ChassisBase.get_bmc
        try:
            o0 = _call(_get(self._chassis, 'get_bmc'))
            i0 = 0
            if o0 is not None:
                p0 = _fmt(None, 'BMC', '', i0)
                for i, (k, v) in enumerate(_pairs(_call(_get(o0, 'get_eeprom')))):
                    out.append((self._row_eeprom_tlv(None, p0, i, {'source': 'bmc', 'code': str(k), 'value': None if v is None else str(v)}), None))
        except NotImplementedError:
            pass
        return out



    def _row_bmc_info(self, dev, parent, i, fixed):
        return BmcInfo(
            name=_default(_call(_get(dev, 'get_name')), 'BMC'),
            presence=_default(_call(_get(dev, 'get_presence')), False),
            model=_call(_get(dev, 'get_model')),
            serial=_call(_get(dev, 'get_serial')),
            revision=_call(_get(dev, 'get_revision')),
            status=_call(_get(dev, 'get_status')),
            is_replaceable=_default(_call(_get(dev, 'is_replaceable')), False),
            version=_call(_get(dev, 'get_version')),
        )

    def _walk_bmc_info(self):
        """Every BmcInfo paired with the device it was read from.

        One traversal serves both the snapshot and the by-name lookup, so an
        action cannot disagree with the snapshot about what a row is called.
        """
        out = []
        # ChassisBase.get_bmc
        try:
            for i, dev in enumerate(_one(_call(_get(self._chassis, 'get_bmc')))):
                out.append((self._row_bmc_info(dev, 'chassis 1', i, {}), dev))
        except NotImplementedError:
            pass
        return out



    def get_chassis_info(self):
        """The chassis.

A singleton, so it is not a `list`: there is one chassis and the
traversal that would flatten it has nothing to walk."""
        return self._walk_chassis_info()[0][0]

    def get_modules(self):
        """Every ModuleInfo, in declared order."""
        return [row for row, _dev in self._walk_module_info()]

    def get_thermals(self):
        """Every ThermalInfo, in declared order."""
        return [row for row, _dev in self._walk_thermal_info()]

    def get_fans(self):
        """Every FanInfo, in declared order."""
        return [row for row, _dev in self._walk_fan_info()]

    def get_fan_drawers(self):
        """Every FanDrawerInfo, in declared order."""
        return [row for row, _dev in self._walk_fan_drawer_info()]

    def get_psus(self):
        """Every PsuInfo, in declared order."""
        return [row for row, _dev in self._walk_psu_info()]

    def get_components(self):
        """Every ComponentInfo, in declared order."""
        return [row for row, _dev in self._walk_component_info()]

    def get_sensors(self):
        """Every SensorInfo, in declared order."""
        return [row for row, _dev in self._walk_sensor_info()]

    def get_leak_profiles(self):
        """Published once at start-up, so read on call rather than cached."""
        return [row for row, _dev in self._walk_leak_profile()]

    def get_leak_sensors(self):
        """Every LeakSensorInfo, in declared order."""
        return [row for row, _dev in self._walk_leak_sensor_info()]

    def get_eeprom(self):
        """Every system EEPROM entry the platform exposes, chassis and BMC."""
        return [row for row, _dev in self._walk_eeprom_tlv()]

    def get_bmcs(self):
        """A list of at most one, for the same reason as `get_watchdogs`."""
        return [row for row, _dev in self._walk_bmc_info()]

    def get_watchdogs(self):
        """A list of at most one.

Not a singleton: a platform without a watchdog has none, and a
singleton accessor would have to invent a row to say so."""
        return [row for row, _dev in self._walk_watchdog_info()]

    def set_fan_led(self, fan, color):
        """Set the LED on one fan.

        Separate from `set_fan_drawer_led` on purpose.  thermalctld sets the
        fan's LED and then its drawer's with the same colour, tolerating
        either being unimplemented (thermalctld:547-550); folding the two into
        one call would hide which of them a platform refused."""
        dev = self._find_fan_info(fan)
        fn = _get(dev, 'set_status_led')
        if fn is None:
            raise NotImplementedError('FanBase.set_status_led is not implemented')
        return fn(color)

    def set_fan_drawer_led(self, drawer, color):
        """"""
        dev = self._find_fan_drawer_info(drawer)
        fn = _get(dev, 'set_status_led')
        if fn is None:
            raise NotImplementedError('FanDrawerBase.set_status_led is not implemented')
        return fn(color)

    def set_fan_speed(self, fan, speed):
        """"""
        dev = self._find_fan_info(fan)
        fn = _get(dev, 'set_speed')
        if fn is None:
            raise NotImplementedError('FanBase.set_speed is not implemented')
        return fn(speed)

    def set_psu_led(self, psu, color):
        """"""
        dev = self._find_psu_info(psu)
        fn = _get(dev, 'set_status_led')
        if fn is None:
            raise NotImplementedError('PsuBase.set_status_led is not implemented')
        return fn(color)

    def get_psu_master_led(self, psu):
        """The colour of the LED every hot-swappable PSU shares.

        `PsuBase.get_status_master_led` is a `@classmethod` over a class
        attribute, so any PSU answers for all of them; the row name is how the
        facade reaches an instance to ask."""
        dev = self._find_psu_info(psu)
        fn = _get(dev, 'get_status_master_led')
        if fn is None:
            raise NotImplementedError('PsuBase.get_status_master_led is not implemented')
        return fn()

    def set_psu_master_led(self, psu, color):
        """One LED shared by every hot-swappable PSU.

        Addressed through a PSU row like the getter, and for the same reason:
        `set_status_master_led` is a `@classmethod` on `PsuBase`, so any PSU
        sets it for all of them -- but it is not on the chassis, and reaching
        for it there would fail on every platform."""
        dev = self._find_psu_info(psu)
        fn = _get(dev, 'set_status_master_led')
        if fn is None:
            raise NotImplementedError('PsuBase.set_status_master_led is not implemented')
        return fn(color)

    def reboot_module(self, module, reboot_type):
        """"""
        dev = self._find_module_info(module)
        fn = _get(dev, 'reboot')
        if fn is None:
            raise NotImplementedError('ModuleBase.reboot is not implemented')
        return fn(reboot_type)

    def set_module_admin_state(self, module, up):
        """"""
        dev = self._find_module_info(module)
        fn = _get(dev, 'set_admin_state')
        if fn is None:
            raise NotImplementedError('ModuleBase.set_admin_state is not implemented')
        return fn(up)

    def set_module_admin_state_gracefully(self, module, up):
        """Admin-down that lets the module's services stop first.

        Separate from `set_module_admin_state` because it blocks for as long
        as the halt takes, and a caller polling on a timer needs to know which
        of the two it asked for."""
        dev = self._find_module_info(module)
        fn = _get(dev, 'set_admin_state_gracefully')
        if fn is None:
            raise NotImplementedError('ModuleBase.set_admin_state_gracefully is not implemented')
        return fn(up)

    def power_cycle_module(self, module):
        """"""
        dev = self._find_module_info(module)
        fn = _get(dev, 'do_power_cycle')
        if fn is None:
            raise NotImplementedError('ModuleBase.do_power_cycle is not implemented')
        return fn()

    def module_pre_shutdown(self, module):
        """"""
        dev = self._find_module_info(module)
        fn = _get(dev, 'module_pre_shutdown')
        if fn is None:
            raise NotImplementedError('ModuleBase.module_pre_shutdown is not implemented')
        return fn()

    def module_post_startup(self, module):
        """"""
        dev = self._find_module_info(module)
        fn = _get(dev, 'module_post_startup')
        if fn is None:
            raise NotImplementedError('ModuleBase.module_post_startup is not implemented')
        return fn()

    def set_module_state_transition(self, module, transition_type):
        """`pass_key`: the base class takes the module's own name as well."""
        dev = self._find_module_info(module)
        fn = _get(dev, 'set_module_state_transition')
        if fn is None:
            raise NotImplementedError('ModuleBase.set_module_state_transition is not implemented')
        return fn(module, transition_type)

    def clear_module_state_transition(self, module):
        """"""
        dev = self._find_module_info(module)
        fn = _get(dev, 'clear_module_state_transition')
        if fn is None:
            raise NotImplementedError('ModuleBase.clear_module_state_transition is not implemented')
        return fn(module)

    def clear_module_gnoi_halt(self, module):
        """"""
        dev = self._find_module_info(module)
        fn = _get(dev, 'clear_module_gnoi_halt_in_progress')
        if fn is None:
            raise NotImplementedError('ModuleBase.clear_module_gnoi_halt_in_progress is not implemented')
        return fn()

    def set_sensor_high_threshold(self, sensor, value):
        """"""
        dev = self._find_sensor_info(sensor)
        fn = _get(dev, 'set_high_threshold')
        if fn is None:
            raise NotImplementedError('SensorBase.set_high_threshold is not implemented')
        return fn(value)

    def set_sensor_low_threshold(self, sensor, value):
        """"""
        dev = self._find_sensor_info(sensor)
        fn = _get(dev, 'set_low_threshold')
        if fn is None:
            raise NotImplementedError('SensorBase.set_low_threshold is not implemented')
        return fn(value)

    def get_available_firmware_version(self, component, image_path):
        """"""
        dev = self._find_component_info(component)
        fn = _get(dev, 'get_available_firmware_version')
        if fn is None:
            raise NotImplementedError('ComponentBase.get_available_firmware_version is not implemented')
        return fn(image_path)

    def get_firmware_update_notification(self, component, image_path):
        """"""
        dev = self._find_component_info(component)
        fn = _get(dev, 'get_firmware_update_notification')
        if fn is None:
            raise NotImplementedError('ComponentBase.get_firmware_update_notification is not implemented')
        return fn(image_path)

    def install_firmware(self, component, image_path):
        """"""
        dev = self._find_component_info(component)
        fn = _get(dev, 'install_firmware')
        if fn is None:
            raise NotImplementedError('ComponentBase.install_firmware is not implemented')
        return fn(image_path)

    def update_firmware(self, component, image_path):
        """`ComponentBase.update_firmware` returns False on a missing path and
        nothing at all on success, so there is no value worth declaring."""
        dev = self._find_component_info(component)
        fn = _get(dev, 'update_firmware')
        if fn is None:
            raise NotImplementedError('ComponentBase.update_firmware is not implemented')
        return fn(image_path)

    def auto_update_firmware(self, component, image_path, boot_type):
        """Returns one of `ComponentBase.FW_AUTO_*`."""
        dev = self._find_component_info(component)
        fn = _get(dev, 'auto_update_firmware')
        if fn is None:
            raise NotImplementedError('ComponentBase.auto_update_firmware is not implemented')
        return fn(image_path, boot_type)

    def arm_watchdog(self, seconds):
        """Arm, and say for how long it actually armed.

        `WatchdogBase.arm` answers the seconds it settled on, which need not
        be the seconds asked for, and -1 on failure."""
        target = _call(_get(self._chassis, 'get_watchdog'))
        fn = _get(target, 'arm')
        if fn is None:
            raise NotImplementedError('ChassisBase.get_watchdog.arm is not implemented')
        return fn(seconds)

    def disarm_watchdog(self):
        """"""
        target = _call(_get(self._chassis, 'get_watchdog'))
        fn = _get(target, 'disarm')
        if fn is None:
            raise NotImplementedError('ChassisBase.get_watchdog.disarm is not implemented')
        return fn()

    def initialize_system_led(self):
        """The base class spells this `initizalize_system_led`.

        The typo is part of the shipped API, so `Calls` carries it; the facade
        does not have to repeat it."""
        fn = _get(self._chassis, 'initizalize_system_led')
        if fn is None:
            raise NotImplementedError('ChassisBase.initizalize_system_led is not implemented')
        return fn()

    def init_midplane_switch(self):
        """"""
        fn = _get(self._chassis, 'init_midplane_switch')
        if fn is None:
            raise NotImplementedError('ChassisBase.init_midplane_switch is not implemented')
        return fn()

    def set_chassis_led(self, color):
        """The whole platform API surface healthd reaches.

        `health_checker/manager.py:77`.  It is not a pmon daemon -- it runs on
        the host -- which is why this one method is worth naming."""
        fn = _get(self._chassis, 'set_status_led')
        if fn is None:
            raise NotImplementedError('ChassisBase.set_status_led is not implemented')
        return fn(color)

    def change_sed_password(self, new_password):
        """"""
        target = _call(_get(self._chassis, 'get_sed_mgmt'))
        fn = _get(target, 'change_sed_password')
        if fn is None:
            raise NotImplementedError('ChassisBase.get_sed_mgmt.change_sed_password is not implemented')
        return fn(new_password)

    def reset_sed_password(self):
        """"""
        target = _call(_get(self._chassis, 'get_sed_mgmt'))
        fn = _get(target, 'reset_sed_password')
        if fn is None:
            raise NotImplementedError('ChassisBase.get_sed_mgmt.reset_sed_password is not implemented')
        return fn()

    def bmc_open_session(self):
        """Hand-written: every BMC command answers a tuple, and not the same tuple: (code, message), (code, (message, (session_id, token))) and (code, (task_id, message)) all appear. Unpacking each into one row shape is a decision per method rather than a rule."""
        return self._hatch.bmc_open_session()

    def bmc_close_session(self, session_id):
        """Hand-written: see bmc_open_session"""
        return self._hatch.bmc_close_session(session_id)

    def bmc_reset_root_password(self):
        """Hand-written: see bmc_open_session"""
        return self._hatch.bmc_reset_root_password()

    def bmc_reset(self, graceful):
        """Hand-written: see bmc_open_session"""
        return self._hatch.bmc_reset(graceful)

    def bmc_update_firmware(self, image_path):
        """Hand-written: see bmc_open_session"""
        return self._hatch.bmc_update_firmware(image_path)

    def bmc_trigger_debug_log_dump(self):
        """Hand-written: see bmc_open_session"""
        return self._hatch.bmc_trigger_debug_log_dump()

    def bmc_get_debug_log_dump(self, task_id, filename, path):
        """Hand-written: see bmc_open_session"""
        return self._hatch.bmc_get_debug_log_dump(task_id, filename, path)

    def get_asics(self):
        """Hand-written: get_all_asics answers a list of (asic_id, pci_address) tuples rather than a list of device objects, so there is nothing for a flatten plan to call a getter on."""
        return self._hatch.get_asics()

    def tm_initialize(self):
        """Hand-written: get_thermal_manager() returns a class, not an instance; its twelve methods are all @classmethod over process-global state, and run_policy takes the chassis back as an argument. The facade holds the chassis and passes it, so these four calls take no arguments and the bridge never re-enters Python from Rust from Python."""
        return self._hatch.tm_initialize()

    def tm_run_policy(self):
        """Hand-written: see tm_initialize"""
        return self._hatch.tm_run_policy()

    def tm_get_interval(self):
        """Hand-written: see tm_initialize"""
        return self._hatch.tm_get_interval()

    def tm_deinitialize(self):
        """Hand-written: see tm_initialize"""
        return self._hatch.tm_deinitialize()

    def get_change_event(self, timeout_ms):
        """Hand-written: get_change_event returns a two-level mapping whose leaf is a stringly-typed enumeration documented only in prose, and whose outer keys vary by platform. Flattening it into rows is mechanical, but deciding that `ok` is data rather than an error is not: ok=False is how a platform reports a system-level event, not how it reports a failed call."""
        return self._hatch.get_change_event(timeout_ms)

