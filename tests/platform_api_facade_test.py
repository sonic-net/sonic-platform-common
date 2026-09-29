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
"""The generated facade, against a chassis that misbehaves the way real ones do.

Every mock below reproduces something a shipped platform actually does: a PSU
that is not present, a platform with no PDBs at all, a sensor that reports
'N/A' where a float is declared, a device with no name.  A facade that only
works against a well-behaved chassis would not survive first contact -- the
whole reason the daemons each grew a `try_get()` is that none of this is rare.
"""

import contextlib
import enum
import sys
from unittest import mock

import pytest

try:
    import sonic_py_common  # noqa: F401
except ImportError:
    # Reaching sonic_platform_base.sensor_fs runs the package __init__, which
    # imports sfp_base -> sonic_xcvr -> sonic_py_common.  Same stub the
    # repository's own tests use (tests/bmc_watchdog_test.py:13).
    sys.modules['sonic_py_common'] = mock.MagicMock()
    sys.modules['sonic_py_common.logger'] = mock.MagicMock()
    sys.modules['sonic_py_common.syslogger'] = mock.MagicMock()

from platform_api.facade import (ChassisInfoCols, FanDrawerInfoCols, FanInfoCols,
                                 ModuleInfoCols, PlatformApi)


class Thermal(object):
    def __init__(self, name=None, temp=None, high=None):
        self._name, self._temp, self._high = name, temp, high

    def get_name(self):
        if self._name is None:
            raise NotImplementedError
        return self._name

    def get_temperature(self):
        return self._temp

    def get_high_threshold(self):
        return self._high

    def is_replaceable(self):
        raise NotImplementedError


class Fan(object):
    def __init__(self, name, speed=None, direction=None):
        self._name, self._speed, self._direction = name, speed, direction
        self.led = None

    def get_name(self):
        return self._name

    def get_speed(self):
        return self._speed

    def get_direction(self):
        return self._direction

    def set_status_led(self, color):
        self.led = color
        return True


class Drawer(object):
    def __init__(self, name, fans):
        self._name, self._fans = name, fans

    def get_name(self):
        return self._name

    def get_all_fans(self):
        return self._fans


class Psu(object):
    def __init__(self, name=None, present=True, thermals=(), fans=()):
        self._name, self._present = name, present
        self._thermals, self._fans = list(thermals), list(fans)

    def get_name(self):
        if self._name is None:
            raise NotImplementedError
        return self._name

    def get_presence(self):
        return self._present

    def get_all_thermals(self):
        return self._thermals

    def get_all_fans(self):
        return self._fans


class Module(object):
    def __init__(self, name, thermals=(), psus=(), fans=()):
        self._name = name
        self._thermals, self._psus, self._fans = list(thermals), list(psus), list(fans)

    def get_name(self):
        return self._name

    def get_all_thermals(self):
        return self._thermals

    def get_all_psus(self):
        return self._psus

    def get_all_fans(self):
        return self._fans


class Chassis(object):
    def __init__(self, thermals=(), psus=(), modules=(), drawers=(), modular=False,
                 eeprom=None):
        self._thermals, self._psus = list(thermals), list(psus)
        self._modules, self._drawers = list(modules), list(drawers)
        self._modular = modular
        self.led = None
        # None means the platform has no get_eeprom at all, which is one of the
        # three ways not to have one that the hatch has to survive.
        self._eeprom = eeprom

    def get_eeprom(self):
        if self._eeprom is None:
            raise NotImplementedError
        return self._eeprom

    def get_all_thermals(self):
        return self._thermals

    def get_all_psus(self):
        return self._psus

    def get_all_pdbs(self):
        # A PSU-based platform: the source is absent, not empty.
        raise NotImplementedError

    def get_all_modules(self):
        return self._modules

    def get_all_fan_drawers(self):
        return self._drawers

    def is_modular_chassis(self):
        return self._modular

    def set_status_led(self, color):
        self.led = color
        return True


def names(rows):
    return [(r.name, r.parent_name) for r in rows]


# -- traversal -------------------------------------------------------------

def test_chassis_thermals_are_published_under_chassis_1():
    api = PlatformApi(Chassis(thermals=[Thermal('ASIC', 42.5)]))
    assert names(api.get_thermals()) == [('ASIC', 'chassis 1')]


def test_absent_psu_contributes_no_thermals():
    api = PlatformApi(Chassis(psus=[
        Psu('PSU-1', present=True, thermals=[Thermal('t1', 40.0)]),
        Psu('PSU-2', present=False, thermals=[Thermal('t2', 41.0)]),
    ]))
    assert names(api.get_thermals()) == [('t1', 'PSU-1')]


def test_psu_without_a_name_falls_back_to_its_index():
    api = PlatformApi(Chassis(psus=[Psu(None, thermals=[Thermal('t', 1.0)])]))
    assert names(api.get_thermals()) == [('t', 'PSU 1')]


def test_a_platform_with_no_pdbs_is_not_an_error():
    # Chassis.get_all_pdbs raises; the source is declared optional.
    api = PlatformApi(Chassis(thermals=[Thermal('ASIC', 1.0)]))
    assert len(api.get_thermals()) == 1


def test_module_thermals_only_on_a_modular_chassis():
    mod = Module('LC1', thermals=[Thermal('m', 30.0)])
    assert api_thermal_count(Chassis(modules=[mod], modular=False)) == 0
    assert api_thermal_count(Chassis(modules=[mod], modular=True)) == 1


def api_thermal_count(chassis):
    return len(PlatformApi(chassis).get_thermals())


def test_four_hop_traversal_nests_the_parent_name():
    # chassis -> module -> psu -> thermal, the deepest chain any consumer walks.
    mod = Module('LC1', psus=[Psu(None, thermals=[Thermal('t', 50.0)])])
    api = PlatformApi(Chassis(modules=[mod], modular=True))
    assert names(api.get_thermals()) == [('t', 'LC1 PSU 1')]


def test_declared_source_order_is_preserved():
    api = PlatformApi(Chassis(
        thermals=[Thermal('c', 1.0)],
        psus=[Psu('P', thermals=[Thermal('p', 2.0)])],
        modules=[Module('M', thermals=[Thermal('m', 3.0)])],
        modular=True,
    ))
    assert [n for n, _p in names(api.get_thermals())] == ['c', 'p', 'm']


# -- values ----------------------------------------------------------------

def test_na_is_a_missing_reading_not_a_value():
    api = PlatformApi(Chassis(thermals=[Thermal('t', 'N/A')]))
    assert api.get_thermals()[0].temperature is None


def test_a_number_returned_as_a_string_is_coerced():
    api = PlatformApi(Chassis(thermals=[Thermal('t', '51')]))
    assert api.get_thermals()[0].temperature == 51.0


def test_an_unimplemented_getter_reads_as_absent():
    api = PlatformApi(Chassis(thermals=[Thermal('t', 20.0, high=None)]))
    assert api.get_thermals()[0].high_threshold is None


def test_a_nameless_thermal_takes_the_key_its_consumers_publish():
    api = PlatformApi(Chassis(psus=[Psu('PSU-1', thermals=[Thermal(None, 1.0)])]))
    assert api.get_thermals()[0].name == 'PSU-1 Thermal 1'


def test_is_replaceable_defaults_rather_than_vanishing():
    # Thermal.is_replaceable raises; the field is declared with a default.
    api = PlatformApi(Chassis(thermals=[Thermal('t', 1.0)]))
    assert api.get_thermals()[0].is_replaceable is False


def test_a_getter_that_takes_the_device_name_is_called_with_it():
    """`WithName()`: `ModuleBase.get_module_state_transition(module_name)` takes
    the name, and Python passes it (`chassisd:1271`).

    A zero-argument call raises, and the row is built eagerly, so that one
    column would take the whole row with it -- on a SmartSwitch NPU that left
    chassisd logging "Failed to read the modules" every cycle with
    CHASSIS_MIDPLANE_TABLE empty.
    """
    class M(Module):
        def __init__(self, name):
            super(M, self).__init__(name)
            self.seen = None

        def get_module_state_transition(self, module_name):
            self.seen = module_name
            return True

    m = M('DPU0')
    row, = PlatformApi(Chassis(modules=[m])).get_modules()
    assert row.state_transition is True
    assert m.seen == 'DPU0', 'the getter was not given the device name'


def test_a_name_getter_that_answers_nothing_leaves_the_column_absent():
    """No name, no call: the name is read through the same `get_name()` the
    row's own `name` column uses, so the two cannot drift apart."""
    class M(Module):
        def __init__(self):
            super(M, self).__init__('unused')
            self.called = False

        def get_name(self):
            return None

        def get_module_state_transition(self, module_name):
            self.called = True
            return True

    m = M()
    row, = PlatformApi(Chassis(modules=[m])).get_modules()
    assert row.state_transition is None
    assert not m.called


def test_a_name_getter_that_declines_leaves_the_column_absent():
    """NotImplementedError from the named getter is an absent column, not a
    dead row."""
    class M(Module):
        def get_module_state_transition(self, module_name):
            raise NotImplementedError

    row, = PlatformApi(Chassis(modules=[M('DPU0')])).get_modules()
    assert row.state_transition is None


def test_a_with_name_column_is_declinable_like_any_other():
    """`WithName` used to return before the projection gate, so the bit
    existed and turned nothing off.  psud declines this column."""
    class M(Module):
        def __init__(self, name):
            super(M, self).__init__(name)
            self.called = False

        def get_module_state_transition(self, module_name):
            self.called = True
            return True

    m = M('DPU0')
    row, = PlatformApi(Chassis(modules=[m])).get_modules(ModuleInfoCols.PRESENCE)
    assert not m.called, 'a declined WithName column was read'
    assert row.state_transition is None


def test_a_vendor_that_narrowed_a_signature_loses_only_that_column():
    """`Narrowed()`: `ChassisBase.get_dpu_id` is `(self, **kwargs)` in the base
    class and `(self, name)` on Mellanox, so the row's zero-argument call
    raises TypeError on a SmartSwitch NPU.

    The row is built eagerly, so without this that one column would take the
    whole `ChassisInfo` with it, and a caller that only wanted `is_smartswitch`
    would read None and conclude the platform is a fixed switch.
    """
    class C(object):
        def get_name(self):
            return 'chassis 1'

        def is_smartswitch(self):
            return True

        def get_dpu_id(self, name):        # narrowed: no zero-arg call
            return 3

    row = PlatformApi(C()).get_chassis_info()
    assert row.dpu_id is None, 'a narrowed getter should read as absent'
    assert row.is_smartswitch is True, 'and must not take the row with it'


def test_a_type_error_anywhere_else_is_not_swallowed():
    """`_call` deliberately does not catch TypeError: everywhere but a
    `Narrowed()` column it means the generator emitted the wrong call."""
    class C(object):
        def get_name(self):
            return 'chassis 1'

        def get_serial(self, required):    # not declared Narrowed
            return 'x'

    with pytest.raises(TypeError):
        PlatformApi(C()).get_chassis_info()


def test_every_projected_row_declines_the_columns_it_was_not_asked_for():
    """The three rows psud narrows, each checked the same way.

    Statement coverage cannot answer this: the per-column gates all live inside
    one multi-line `return <Row>(...)`, so coverage.py attributes them to the
    `return` and reports them covered whichever way each gate went.  Only a
    test that watches the getters can tell a declined column from a read one.
    """
    def watched(obj, getters):
        obj.asked = []
        for g in getters:
            def record(_g=g):
                obj.asked.append(_g)
                return None
            setattr(obj, g, record)
        return obj

    # --- FanDrawerInfo: psud wants presence and power draw, not the serial.
    drawer = watched(Drawer('D1', []), ['get_serial', 'get_model', 'get_status',
                                        'get_status_led', 'get_presence'])
    api = PlatformApi(Chassis(drawers=[drawer]))
    row, = api.get_fan_drawers(
        FanDrawerInfoCols.PRESENCE | FanDrawerInfoCols.MAXIMUM_CONSUMED_POWER)
    assert 'get_presence' in drawer.asked
    assert 'get_serial' not in drawer.asked and 'get_model' not in drawer.asked
    assert row.serial is None and row.model is None
    assert row.name == 'D1'

    # --- ModuleInfo: the same, and not the midplane chassisd cares about.
    module = watched(Module('DPU0'), ['get_presence', 'get_serial',
                                      'is_midplane_reachable', 'get_midplane_ip'])
    api = PlatformApi(Chassis(modules=[module]))
    row, = api.get_modules(
        ModuleInfoCols.PRESENCE | ModuleInfoCols.MAXIMUM_CONSUMED_POWER)
    assert 'get_presence' in module.asked
    assert 'is_midplane_reachable' not in module.asked
    assert 'get_midplane_ip' not in module.asked
    assert row.is_midplane_reachable is None and row.midplane_ip is None

    # --- And asking for nothing declinable still yields a named row, which is
    # what `_find_<row>()` walks these for.
    module2 = watched(Module('DPU1'), ['get_presence', 'get_serial'])
    row, = PlatformApi(Chassis(modules=[module2])).get_modules(ModuleInfoCols.NONE)
    assert module2.asked == []
    assert row.name == 'DPU1'


def test_a_shared_call_is_declined_with_the_columns_that_slice_it():
    """`_share_calls` hoists one call for the columns that slice it; a
    projection has to be able to decline that call too.

    `ChassisBase.get_reboot_cause` is the case that matters: it is shared by
    `reboot_cause` and `reboot_cause_detail`, and mlnx's implementation has a
    `_wait_reboot_cause_ready()` sleep loop.  pcied asks for one column of
    twenty (`is_smartswitch`) and should not wait for a reboot cause nobody
    wanted.
    """
    class Chassis1(object):
        def __init__(self):
            self.asked = []

        def get_name(self):
            return 'chassis 1'

        def is_smartswitch(self):
            return True

        def get_reboot_cause(self):
            self.asked.append('get_reboot_cause')
            return ('cause', '')

    chassis = Chassis1()
    api = PlatformApi(chassis)

    row = api.get_chassis_info(ChassisInfoCols.IS_SMARTSWITCH)
    assert row.is_smartswitch is True
    assert chassis.asked == [], 'a shared call ran for columns nobody asked for'
    assert row.reboot_cause is None

    # And it does run when a column that slices it is asked for.
    row = api.get_chassis_info(ChassisInfoCols.REBOOT_CAUSE)
    assert chassis.asked == ['get_reboot_cause']
    assert row.reboot_cause == 'cause'


def test_a_declined_column_is_not_read_at_all():
    """`Snapshot(projected=True)`: the getter behind a column the caller did
    not ask for does not run.

    Not an optimisation.  Mellanox's `PsuFan.is_under_speed` reads
    `psu{n}_fan_min`, which a switched-off PSU leaves readable and empty, and
    `read_from_file` logs that at ERR before raising the exception the caller
    swallows.  psud discards the column and polls at 3s; thermalctld uses it
    and polls at 60s.  Whoever asks pays, under their own syslog identifier.
    """
    fan = Fan('f1', 50, 'intake')
    fan.asked = []
    for getter in ('get_speed', 'get_target_speed', 'get_direction',
                   'is_under_speed', 'is_over_speed', 'get_status',
                   'get_model', 'get_serial'):
        def record(_g=getter):
            fan.asked.append(_g)
            return None
        setattr(fan, getter, record)
    api = PlatformApi(Chassis(drawers=[Drawer('D1', [fan])]))

    # What psud asks for: direction, speed and LED.
    cols = FanInfoCols.DIRECTION | FanInfoCols.SPEED_PCT | FanInfoCols.STATUS_LED
    row, = api.get_fans(cols)

    assert 'is_under_speed' not in fan.asked, 'a declined column was read'
    assert 'is_over_speed' not in fan.asked
    assert sorted(fan.asked) == ['get_direction', 'get_speed']
    assert row.is_under_speed is None and row.is_over_speed is None
    # Always read: `_find_fan_info()` resolves an action's target by walking
    # these same rows, so a row that could not name itself would be useless.
    assert row.name == 'f1'


def test_the_default_projection_reads_every_column():
    """A caller that has not thought about columns reads what it always read."""
    fan = Fan('f1', 50, 'intake')
    row, = PlatformApi(Chassis(drawers=[Drawer('D1', [fan])])).get_fans()
    assert row.speed_pct == 50 and row.direction == 'intake'


def test_resolving_a_name_does_not_read_the_other_columns():
    """`_find_fan_info` walks every fan to resolve one name.  Reading each
    one's speed and thresholds on the way is work no action asked for."""
    fan = Fan('f1', 50, 'intake')
    fan.asked = []
    for getter in ('get_speed', 'is_under_speed'):
        def record(_g=getter):
            fan.asked.append(_g)
            return None
        setattr(fan, getter, record)
    api = PlatformApi(Chassis(drawers=[Drawer('D1', [fan])]))

    assert api._find_fan_info('f1') is fan
    assert fan.asked == [], 'a name lookup read columns it had no use for'


def test_fan_direction_na_is_a_value_and_survives():
    # FanBase.FAN_DIRECTION_NOT_APPLICABLE is the string 'N/A'.  Treating it
    # as a sentinel here would delete the only answer the platform gave.
    drawer = Drawer('D1', [Fan('f1', 50, 'N/A')])
    api = PlatformApi(Chassis(drawers=[drawer]))
    assert api.get_fans()[0].direction == 'N/A'


class _Eeprom(object):
    """What `chassis.get_eeprom()` hands back.  `update_eeprom_db` returns 0 for
    success, which is the convention syseepromd:91 checks."""

    def __init__(self, data=b'raw', rc=0):
        self._data, self._rc, self.wrote = data, rc, None

    def read_eeprom(self):
        if self._data is None:
            raise NotImplementedError
        return self._data

    def update_eeprom_db(self, data):
        self.wrote = data
        return self._rc


def test_the_platform_writes_its_own_eeprom_table():
    # The row surface cannot carry Name/Len/TlvHeader, so this hatch exists to
    # let the platform's own writer publish EEPROM_INFO.  What it must not do is
    # lose the vendor's success convention on the way across.
    eeprom = _Eeprom()
    api = PlatformApi(Chassis(eeprom=eeprom))
    assert api.eeprom_update_db() is True
    assert eeprom.wrote == b'raw', 'the bytes read must be the bytes written'


def test_a_failed_eeprom_write_is_false_not_an_exception():
    # syseepromd logs and leaves the table alone; a raise here would kill the
    # daemon on a platform whose EEPROM is briefly unreadable.
    api = PlatformApi(Chassis(eeprom=_Eeprom(rc=-1)))
    assert api.eeprom_update_db() is False


def test_an_unreadable_or_absent_eeprom_is_false():
    assert PlatformApi(Chassis(eeprom=_Eeprom(data=None))).eeprom_update_db() is False
    assert PlatformApi(Chassis()).eeprom_update_db() is False, 'no get_eeprom at all'


def test_a_vendor_enum_crosses_as_the_string_the_stub_declares():
    # Every enumerated column is declared `Literal[...]`, i.e. a str, and the
    # Rust bridge downcasts to str.  A vendor is free to answer with an
    # `enum.Enum` whose value is that string instead -- mlnx's
    # get_leak_severity() does, and on hardware that failed the whole row read
    # and left LIQUID_COOLING_INFO empty, silently, because the daemon treats
    # a failed read as "no sensors".
    class Direction(enum.Enum):
        INTAKE = 'intake'

    drawer = Drawer('D1', [Fan('f1', 50, Direction.INTAKE)])
    api = PlatformApi(Chassis(drawers=[drawer]))
    fan = api.get_fans()[0]
    assert fan.direction == 'intake'
    assert isinstance(fan.direction, str), 'an enum member would not cross'


def test_source_fixes_the_fields_that_say_where_a_row_came_from():
    api = PlatformApi(Chassis(
        drawers=[Drawer('D1', [Fan('df', 30)])],
        psus=[Psu('P1', fans=[Fan('pf', 40)])],
    ))
    by_name = {f.name: f for f in api.get_fans()}
    assert (by_name['df'].kind, by_name['df'].drawer_name) == ('drawer', 'D1')
    assert (by_name['pf'].kind, by_name['pf'].drawer_name) == ('psu', 'N/A')


def test_a_pdb_fan_is_a_row_and_says_which_it_is():
    """psud publishes PDB fans (`psud:942`, which runs over PSUs and PDBs
    alike); thermalctld's FanUpdater walks drawers, modules and PSUs and stops
    (`thermalctld:396-407`).  One row list serves both daemons, so the source
    they disagree about has to be nameable -- and has to come last, or adding it
    would reorder what thermalctld publishes."""
    class WithPdb(Chassis):
        def get_all_pdbs(self):
            return [Psu('PDB-1', fans=[Fan('pdbf', 20)])]

    api = WithPdb(psus=[Psu('P1', fans=[Fan('pf', 40)])])
    assert [(f.name, f.kind, f.parent_name) for f in PlatformApi(api).get_fans()] == [
        ('pf', 'psu', 'P1'),
        ('pdbf', 'pdb', 'PDB-1'),
    ]


# -- actions ---------------------------------------------------------------

def test_an_action_addresses_the_row_by_the_name_the_snapshot_published():
    fan = Fan('f1', 50)
    api = PlatformApi(Chassis(drawers=[Drawer('D1', [fan])]))
    published = api.get_fans()[0].name
    api.set_fan_led(published, 'amber')
    assert fan.led == 'amber'


def test_an_unknown_row_name_is_a_key_error():
    api = PlatformApi(Chassis(drawers=[Drawer('D1', [Fan('f1', 50)])]))
    with pytest.raises(KeyError):
        api.set_fan_led('nope', 'red')


def test_a_chassis_level_action_needs_no_row():
    chassis = Chassis()
    PlatformApi(chassis).set_chassis_led('green')
    assert chassis.led == 'green'


def test_an_action_a_platform_does_not_implement_says_so():
    class Bare(Chassis):
        set_status_led = None

    with pytest.raises(NotImplementedError):
        PlatformApi(Bare()).set_chassis_led('green')


# -- escape hatch ----------------------------------------------------------

class Manager(object):
    calls = []

    @classmethod
    def initialize(cls):
        cls.calls.append('initialize')

    @classmethod
    def load(cls, path):
        cls.calls.append('load')

    @classmethod
    def init_thermal_algorithm(cls, chassis):
        cls.calls.append('init_thermal_algorithm')

    @classmethod
    def run_policy(cls, chassis):
        cls.calls.append('run_policy')

    @classmethod
    def get_interval(cls):
        return 60.0

    @classmethod
    def stop(cls):
        cls.calls.append('stop')

    @classmethod
    def deinitialize(cls):
        cls.calls.append('deinitialize')


def test_thermal_manager_lifecycle_takes_no_arguments_across_the_boundary():
    Manager.calls = []

    class WithManager(Chassis):
        def get_thermal_manager(self):
            return Manager

    api = PlatformApi(WithManager())
    api.tm_initialize()
    api.tm_run_policy()
    assert api.tm_get_interval() == 60.0
    api.tm_deinitialize()
    assert Manager.calls == ['initialize', 'load', 'init_thermal_algorithm',
                             'run_policy', 'stop', 'deinitialize']


def test_a_platform_without_a_thermal_manager_is_quiet():
    api = PlatformApi(Chassis())
    api.tm_initialize()
    api.tm_run_policy()
    api.tm_deinitialize()
    assert api.tm_get_interval() is None


def test_a_platform_whose_manager_is_none_starts_quietly():
    class NoManager(Chassis):
        def get_thermal_manager(self):
            return None

    api = PlatformApi(NoManager())
    api.tm_initialize()
    api.tm_run_policy()
    assert api.tm_get_interval() is None


def test_run_policy_without_a_successful_load_does_nothing():
    Manager.calls = []

    class WithManager(Chassis):
        def get_thermal_manager(self):
            return Manager

    PlatformApi(WithManager()).tm_run_policy()
    assert Manager.calls == []


# -- chassis and modules ---------------------------------------------------

class RichChassis(Chassis):
    """A chassis that answers the things ChassisInfo asks for."""

    def __init__(self, **kw):
        Chassis.__init__(self, **kw)
        self.inited_led = False

    def get_name(self):
        raise NotImplementedError

    def get_reboot_cause(self):
        return ('Watchdog', 'counted down')

    def get_my_slot(self):
        # Five base-class methods return the exception class instead of
        # raising it.  That is truthy, and a caller that trusted it would
        # publish a slot number of <class NotImplementedError>.
        return NotImplementedError

    def get_supervisor_slot(self):
        return '2'

    def initizalize_system_led(self):
        self.inited_led = True
        return True


class FullModule(Module):
    def __init__(self, name, **kw):
        Module.__init__(self, name, **kw)
        self.rebooted = None
        self.transition = None

    def get_type(self):
        return 'LINE-CARD'

    def get_oper_status(self):
        return 'Online'

    def get_slot(self):
        return 3

    def get_reboot_cause(self):
        return ('Software', 'requested')

    def get_midplane_down_reason(self):
        return ('Power Loss', 'DPU power rail dropped')

    def reboot(self, reboot_type):
        self.rebooted = reboot_type
        return True

    def set_module_state_transition(self, module_name, transition_type):
        self.transition = (module_name, transition_type)
        return True


def test_the_chassis_is_one_row_not_a_list():
    info = PlatformApi(RichChassis()).get_chassis_info()
    assert not isinstance(info, list)
    assert info.name == 'chassis 1'


def test_a_predicate_a_platform_does_not_answer_is_a_no():
    info = PlatformApi(RichChassis()).get_chassis_info()
    assert info.is_modular_chassis is False
    assert info.is_smartswitch is False
    assert info.is_liquid_cooled is False


def test_a_tuple_return_becomes_two_columns():
    info = PlatformApi(RichChassis()).get_chassis_info()
    assert (info.reboot_cause, info.reboot_cause_detail) == ('Watchdog', 'counted down')


def test_returning_the_exception_class_reads_as_absent():
    info = PlatformApi(RichChassis()).get_chassis_info()
    assert info.my_slot is None, 'NotImplementedError is truthy; it is not a slot'


def test_a_slot_reported_as_a_string_is_a_number():
    assert PlatformApi(RichChassis()).get_chassis_info().supervisor_slot == 2


def test_modules_carry_the_strings_the_base_class_defines():
    api = PlatformApi(RichChassis(modules=[FullModule('LC1')], modular=True))
    mod = api.get_modules()[0]
    assert (mod.name, mod.type, mod.oper_status, mod.slot) == \
        ('LC1', 'LINE-CARD', 'Online', 3)
    # The reboot cause is not a column.  `ModuleBase.get_reboot_cause` logs on
    # Mellanox (`module.py:477,482`), and as a column the eagerly built row
    # asked it once per polling cycle -- 358 syslog lines against Python's 20
    # on a SmartSwitch.  It is a method now, asked when a module moves.
    assert not hasattr(mod, 'reboot_cause')
    # And it carries both halves of what the base class answers.  Taking only
    # the cause is bug 14: the detail is what chassisd publishes as the
    # record's `comment`, and dropping it wrote `N/A` on a SmartSwitch where the
    # Python daemon wrote 'Reset due to Power off'.
    rc = api.get_module_reboot_cause('LC1')
    assert (rc.cause, rc.detail) == ('Software', 'requested')


def test_a_module_that_cannot_say_why_it_rebooted_says_so():
    """An action is not a column: a platform without the getter gets a
    NotImplementedError the caller can see, not a row with an absent field.

    The distinction matters because chassisd asks this when a module moves,
    and a silent None there would be published as a reboot record with no
    cause -- indistinguishable from a module that rebooted for no reason.
    """
    api = PlatformApi(Chassis(modules=[Module('LC1')]))
    with pytest.raises(NotImplementedError, match='ModuleBase.get_reboot_cause'):
        api.get_module_reboot_cause('LC1')


def test_a_module_says_why_its_midplane_went_down():
    """chassisd asks when a DPU's midplane goes down without a planned
    transition, and publishes both halves joined.  One call, both slots."""
    api = PlatformApi(RichChassis(modules=[FullModule('LC1')], modular=True))
    reason = api.get_module_midplane_down_reason('LC1')
    assert (reason.reason, reason.detail) == ('Power Loss', 'DPU power rail dropped')
    assert not hasattr(api.get_modules()[0], 'midplane_down_reason')


def test_a_midplane_down_reason_given_as_a_string_is_the_whole_reason():
    """chassisd takes a bare string as the reason itself.  Indexing it the
    way the tuple is indexed would publish its first character."""
    class StringModule(FullModule):
        def get_midplane_down_reason(self):
            return 'Power Loss'
    api = PlatformApi(RichChassis(modules=[StringModule('LC1')], modular=True))
    reason = api.get_module_midplane_down_reason('LC1')
    assert (reason.reason, reason.detail) == ('Power Loss', None)


def test_a_module_that_cannot_say_why_its_midplane_went_down_says_so():
    """Like the reboot cause, an action the platform lacks is an error the
    caller sees; chassisd then publishes the reason as 'Unknown'."""
    api = PlatformApi(Chassis(modules=[Module('LC1')]))
    with pytest.raises(NotImplementedError, match='ModuleBase.get_midplane_down_reason'):
        api.get_module_midplane_down_reason('LC1')


def test_two_columns_of_one_getter_share_one_call():
    """Bug 15: `reboot_cause` and `reboot_cause_detail` are `at=0` and `at=1`
    of one `get_reboot_cause()`, and each column used to expand its own call.

    The two answers need not agree.  mlnx's `Chassis.get_reboot_cause`
    (chassis.py:1421) returns from whichever sysfs flag matches, and its two
    branches mean different things -- `(cause, '')` from the major one,
    `(HARDWARE_OTHER, cause)` from the minor.  A flag cleared between the two
    calls pastes one slot of each answer into a row that was never produced.

    The chassis here answers differently every time it is asked, so a row
    built from two calls cannot come out consistent; one built from a single
    call can only be one of the pairs.
    """
    answers = [('Watchdog', ''), ('Hardware - Other', 'reset_from_asic')]

    class Flapping(object):
        def __init__(self):
            self.calls = 0

        def get_reboot_cause(self):
            self.calls += 1
            return answers[min(self.calls - 1, len(answers) - 1)]

    chassis = Flapping()
    info = PlatformApi(chassis).get_chassis_info()

    assert chassis.calls == 1, 'the row must ask once, not once per column'
    assert (info.reboot_cause, info.reboot_cause_detail) == answers[0], \
        'both halves must come from the same reading'


def test_a_module_action_reaches_the_module():
    mod = FullModule('LC1')
    PlatformApi(RichChassis(modules=[mod])).reboot_module('LC1', 'DPU')
    assert mod.rebooted == 'DPU'


def test_pass_key_hands_the_module_its_own_name():
    mod = FullModule('LC1')
    PlatformApi(RichChassis(modules=[mod])).set_module_state_transition('LC1', 'recovery')
    assert mod.transition == ('LC1', 'recovery')


def test_the_base_class_typo_stays_in_the_base_class():
    chassis = RichChassis()
    PlatformApi(chassis).initialize_system_led()
    assert chassis.inited_led


# -- components and sensors ------------------------------------------------

class Component(object):
    def __init__(self, name, version=None):
        self._name, self._version = name, version
        self.installed = None

    def get_name(self):
        return self._name

    def get_firmware_version(self):
        return self._version

    def get_available_firmware_version(self, image_path):
        return 'from ' + image_path

    def install_firmware(self, image_path):
        self.installed = image_path
        return True


class Sensor(object):
    def __init__(self, name, value=None, unit=None):
        self._name, self._value, self._unit = name, value, unit
        self.high = None

    def get_name(self):
        return self._name

    def get_value(self):
        return self._value

    def get_unit(self):
        return self._unit

    def set_high_threshold(self, value):
        self.high = value
        return True


class SensorChassis(Chassis):
    def __init__(self, voltage=(), current=(), components=(), **kw):
        Chassis.__init__(self, **kw)
        self._v, self._c, self._comp = list(voltage), list(current), list(components)

    def get_all_voltage_sensors(self):
        return self._v

    def get_all_current_sensors(self):
        return self._c

    def get_all_components(self):
        return self._comp


def test_components_come_from_the_chassis_and_from_modules():
    mod = Module('LC1')
    mod.get_all_components = lambda: [Component('LC1-CPLD')]
    api = PlatformApi(SensorChassis(components=[Component('BIOS', '1.2')],
                                    modules=[mod], modular=True))
    rows = api.get_components()
    assert [(r.name, r.parent_name) for r in rows] == \
        [('BIOS', 'chassis 1'), ('LC1-CPLD', 'LC1')]
    assert rows[0].firmware_version == '1.2'


def test_a_firmware_query_takes_an_argument_and_is_not_a_column():
    api = PlatformApi(SensorChassis(components=[Component('BIOS')]))
    assert api.get_available_firmware_version('BIOS', '/tmp/fw.bin') == 'from /tmp/fw.bin'


def test_a_component_action_reaches_the_component():
    comp = Component('BIOS')
    PlatformApi(SensorChassis(components=[comp])).install_firmware('BIOS', '/tmp/fw.bin')
    assert comp.installed == '/tmp/fw.bin'


def test_voltage_then_current_in_the_order_the_daemon_publishes():
    api = PlatformApi(SensorChassis(
        voltage=[Sensor('v1', 3300, 'mV')],
        current=[Sensor('c1', 1200, 'mA')],
    ))
    rows = api.get_sensors()
    assert [(r.name, r.kind, r.unit) for r in rows] == \
        [('v1', 'voltage', 'mV'), ('c1', 'current', 'mA')]


def test_a_platform_with_no_sensors_yaml_is_the_common_case():
    # The provider swallows a missing file; the row list is just the chassis'.
    api = PlatformApi(SensorChassis(voltage=[Sensor('v1', 1.0)]))
    assert len(api.get_sensors()) == 1


def test_a_sensor_threshold_is_set_on_the_sensor_the_snapshot_named():
    sensor = Sensor('v1', 3300)
    api = PlatformApi(SensorChassis(voltage=[sensor]))
    api.set_sensor_high_threshold('v1', 3600)
    assert sensor.high == 3600


# -- liquid cooling and watchdog -------------------------------------------

class Profile(object):
    def __init__(self, type_, secs):
        self._type, self._secs = type_, secs

    def get_type(self):
        return self._type

    def get_leak_max_minor_duration_sec(self):
        return self._secs


class LeakSensor(object):
    def __init__(self, name=None, leak=False, ok=True, severity=None, profile=None):
        self._name, self._leak, self._ok = name, leak, ok
        self._severity, self._profile = severity, profile

    def get_name(self):
        if self._name is None:
            raise NotImplementedError
        return self._name

    def is_leak(self):
        return self._leak

    def is_leak_sensor_ok(self):
        return self._ok

    def get_leak_severity(self):
        return self._severity

    def get_leak_profile(self):
        if self._profile is None:
            raise NotImplementedError
        return self._profile


class LiquidCooling(object):
    def __init__(self, sensors=(), profiles=()):
        self._sensors, self._profiles = list(sensors), list(profiles)

    def get_all_leak_sensors(self):
        return self._sensors

    def get_all_profiles(self):
        return self._profiles


class Watchdog(object):
    def __init__(self, armed=False, remaining=-1):
        self._armed, self._remaining = armed, remaining
        self.armed_for = None

    def is_armed(self):
        return self._armed

    def get_remaining_time(self):
        return self._remaining

    def arm(self, seconds):
        self.armed_for = seconds
        return seconds


class CooledChassis(Chassis):
    def __init__(self, liquid=None, watchdog=None, **kw):
        Chassis.__init__(self, **kw)
        self._liquid, self._watchdog = liquid, watchdog

    def get_liquid_cooling(self):
        if self._liquid is None:
            raise NotImplementedError
        return self._liquid

    def get_watchdog(self):
        if self._watchdog is None:
            raise NotImplementedError
        return self._watchdog


def test_a_singular_hop_is_not_iterated():
    # get_liquid_cooling() answers one object; iterating it would be a
    # TypeError, and the traversal has to reach through it instead.
    lc = LiquidCooling(sensors=[LeakSensor('leak-a')])
    rows = PlatformApi(CooledChassis(liquid=lc)).get_leak_sensors()
    assert [r.name for r in rows] == ['leak-a']


def test_a_platform_without_liquid_cooling_has_no_leak_rows():
    assert PlatformApi(CooledChassis()).get_leak_sensors() == []
    assert PlatformApi(CooledChassis()).get_leak_profiles() == []


def test_a_nameless_leak_sensor_gets_the_daemons_own_fallback():
    lc = LiquidCooling(sensors=[LeakSensor(None)])
    assert PlatformApi(CooledChassis(liquid=lc)).get_leak_sensors()[0].name == 'leakage1'


def test_a_two_hop_field_reaches_through_the_profile():
    profile = Profile('rack', 30)
    lc = LiquidCooling(sensors=[LeakSensor('leak-a', profile=profile)])
    row = PlatformApi(CooledChassis(liquid=lc)).get_leak_sensors()[0]
    assert (row.profile_type, row.profile_max_minor_duration_sec) == ('rack', 30)


def test_a_sensor_with_no_profile_leaves_the_profile_columns_absent():
    lc = LiquidCooling(sensors=[LeakSensor('leak-a')])
    row = PlatformApi(CooledChassis(liquid=lc)).get_leak_sensors()[0]
    assert row.profile_type is None
    assert row.profile_max_minor_duration_sec is None


def test_profiles_are_their_own_row():
    lc = LiquidCooling(profiles=[Profile('rack', 30), Profile('row', 0)])
    rows = PlatformApi(CooledChassis(liquid=lc)).get_leak_profiles()
    assert [(r.type, r.max_minor_duration_sec) for r in rows] == [('rack', 30), ('row', 0)]


def test_a_singular_leaf_yields_at_most_one_row():
    assert PlatformApi(CooledChassis()).get_watchdogs() == []
    rows = PlatformApi(CooledChassis(watchdog=Watchdog(True, 42))).get_watchdogs()
    assert len(rows) == 1
    assert (rows[0].is_armed, rows[0].remaining_time) == (True, 42)


def test_a_chained_action_reaches_through_the_chassis():
    wd = Watchdog()
    assert PlatformApi(CooledChassis(watchdog=wd)).arm_watchdog(60) == 60
    assert wd.armed_for == 60


# -- change events ---------------------------------------------------------

class EventChassis(Chassis):
    def __init__(self, answer, **kw):
        Chassis.__init__(self, **kw)
        self._answer = answer
        self.timeout = None

    def get_change_event(self, timeout=0):
        self.timeout = timeout
        if self._answer is None:
            raise NotImplementedError
        return self._answer


def test_a_two_level_mapping_becomes_rows():
    api = PlatformApi(EventChassis((True, {'fan': {'0': '0', '2': '1'},
                                           'sfp': {'11': '0'}})))
    batch = api.get_change_event(1000)
    assert batch.ok is True
    assert sorted((e.device_type, e.device_id, e.status) for e in batch.events) == \
        [('fan', '0', '0'), ('fan', '2', '1'), ('sfp', '11', '0')]


def test_the_documented_statuses_are_named_and_the_rest_pass_through():
    api = PlatformApi(EventChassis((True, {'sfp': {'1': '2', '2': '9'}})))
    by_id = {e.device_id: e for e in api.get_change_event(0).events}
    assert (by_id['1'].status, by_id['1'].kind) == ('2', 'i2c_stuck')
    # A vendor is not limited to the seven; the raw value survives.
    assert (by_id['2'].status, by_id['2'].kind) == ('9', None)


def test_ok_false_is_data_not_an_error():
    # A platform reports a system-level event this way; raising here would
    # delete the path xcvrd:301-323 depends on.
    # xcvrd:68-72: EVENT_ON_ALL_SFP is the device id '-1' inside the 'sfp'
    # mapping, and the status is the system event.
    api = PlatformApi(EventChassis((False, {'sfp': {'-1': 'system_not_ready'}})))
    batch = api.get_change_event(0)
    assert batch.ok is False
    assert [(e.device_type, e.device_id, e.status) for e in batch.events] == \
        [('sfp', '-1', 'system_not_ready')]
    assert batch.events[0].kind is None, 'a system event is not one of the seven'


def test_a_malformed_inner_value_does_not_take_the_others_with_it():
    api = PlatformApi(EventChassis((True, {'sfp': 'nonsense', 'fan': {'0': '1'}})))
    batch = api.get_change_event(0)
    assert [(e.device_type, e.device_id) for e in batch.events] == [('fan', '0')]


def test_a_quiet_timeout_is_ok_with_no_events():
    batch = PlatformApi(EventChassis((True, {}))).get_change_event(500)
    assert (batch.ok, batch.events) == (True, [])


def test_the_timeout_reaches_the_platform():
    chassis = EventChassis((True, {}))
    PlatformApi(chassis).get_change_event(250)
    assert chassis.timeout == 250


def test_a_platform_without_change_events_says_so():
    with pytest.raises(NotImplementedError):
        PlatformApi(EventChassis(None)).get_change_event(0)


def test_an_answer_that_is_not_a_pair_is_not_a_crash_in_a_polling_loop():
    with pytest.raises(NotImplementedError):
        PlatformApi(EventChassis('nonsense')).get_change_event(0)


# -- eeprom, asics, bmc ----------------------------------------------------

class Bmc(object):
    def __init__(self, eeprom=None, version=None):
        self._eeprom, self._version = eeprom, version
        self.closed = None

    def get_name(self):
        return 'BMC'

    def get_version(self):
        return self._version

    def get_eeprom(self):
        return self._eeprom if self._eeprom is not None else {}

    def open_session(self):
        return (0, ('ok', ('sess-1', 'tok-1')))

    def close_session(self, session_id):
        self.closed = session_id
        return (0, 'closed')

    def reset_root_password(self):
        return (7, 'denied')

    def trigger_bmc_debug_log_dump(self):
        return (0, ('task-9', None))


class AsicModule(Module):
    def __init__(self, name, asics):
        Module.__init__(self, name)
        self._asics = asics

    def get_all_asics(self):
        return self._asics


class BigChassis(Chassis):
    def __init__(self, eeprom=None, bmc=None, **kw):
        Chassis.__init__(self, **kw)
        self._eeprom, self._bmc = eeprom, bmc

    def get_system_eeprom_info(self):
        if self._eeprom is None:
            raise NotImplementedError
        return self._eeprom

    def get_bmc(self):
        if self._bmc is None:
            raise NotImplementedError
        return self._bmc


def test_a_mapping_becomes_one_row_per_entry():
    api = PlatformApi(BigChassis(eeprom={'0x21': 'MSN4700', '0x23': 'MT2035'}))
    rows = api.get_eeprom()
    assert [(r.source, r.code, r.value) for r in rows] == \
        [('chassis', '0x21', 'MSN4700'), ('chassis', '0x23', 'MT2035')]


def test_mapping_rows_come_from_chassis_and_bmc_alike():
    api = PlatformApi(BigChassis(eeprom={'0x21': 'X'},
                                 bmc=Bmc(eeprom={'Model': 'BF3'})))
    assert [(r.source, r.code) for r in api.get_eeprom()] == \
        [('chassis', '0x21'), ('bmc', 'Model')]


def test_a_platform_with_no_system_eeprom_is_not_an_error():
    assert PlatformApi(BigChassis()).get_eeprom() == []


def test_asics_are_tuples_and_a_short_one_loses_only_its_address():
    mod = AsicModule('LC1', [('4', '0000:05:00.0'), ('5',)])
    rows = PlatformApi(BigChassis(modules=[mod])).get_asics()
    assert [(r.parent_name, r.asic_id, r.pci_address) for r in rows] == \
        [('LC1', '4', '0000:05:00.0'), ('LC1', '5', None)]


def test_the_bmc_is_a_list_of_at_most_one():
    assert PlatformApi(BigChassis()).get_bmcs() == []
    rows = PlatformApi(BigChassis(bmc=Bmc(version='1.4'))).get_bmcs()
    assert len(rows) == 1 and rows[0].version == '1.4'


def test_a_bmc_command_carries_its_code_rather_than_raising():
    # config/bmc.py prints the message on a non-zero code and carries on.
    res = PlatformApi(BigChassis(bmc=Bmc())).bmc_reset_root_password()
    assert (res.code, res.message) == (7, 'denied')


def test_open_session_unpacks_two_levels_of_tuple():
    res = PlatformApi(BigChassis(bmc=Bmc())).bmc_open_session()
    assert (res.code, res.session_id, res.token) == (0, 'sess-1', 'tok-1')


def test_a_debug_dump_puts_the_task_id_where_the_message_usually_is():
    res = PlatformApi(BigChassis(bmc=Bmc())).bmc_trigger_debug_log_dump()
    assert (res.code, res.task_id, res.message) == (0, 'task-9', None)


def test_a_bmc_command_reaches_the_bmc():
    bmc = Bmc()
    PlatformApi(BigChassis(bmc=bmc)).bmc_close_session('sess-1')
    assert bmc.closed == 'sess-1'


def test_a_platform_without_a_bmc_says_so():
    with pytest.raises(NotImplementedError):
        PlatformApi(BigChassis()).bmc_open_session()


# -- every action, against a device that records what it was asked ---------
#
# The generated action bodies are five lines each and they all look alike, so
# a spot check of two of them proves nothing about the other twenty.  What can
# go wrong is the declaration, not the template: a `Calls()` naming a method
# the device does not have, or an `On()` pointing at the wrong row -- which is
# how `set_psu_master_led` came to reach for a PsuBase classmethod on the
# chassis, where no platform has it.

class Recorder(object):
    """A device that answers any of the methods it is told to, recording each."""

    def __init__(self, name, answers=()):
        self._name = name
        self.calls = []
        for method in answers:
            setattr(self, method, self._record(method))

    def _record(self, method):
        def call(*args):
            self.calls.append((method, args))
            return True
        return call

    def get_name(self):
        return self._name

    def get_presence(self):
        return True


class RecordingChassis(object):
    """A chassis holding one device of each kind, each a Recorder."""

    def __init__(self, methods):
        self.chassis = Recorder('chassis 1', methods)
        self.fan = Recorder('fan 1', methods)
        self.drawer = Recorder('D1', methods)
        self.psu = Recorder('P1', methods)
        self.module = Recorder('M1', methods)
        self.component = Recorder('C1', methods)
        self.sensor = Recorder('v1', methods)
        self.watchdog = Recorder('wd', methods)
        self.sed = Recorder('sed', methods)

    # the chassis' own surface
    def __getattr__(self, attr):
        return getattr(self.__dict__['chassis'], attr)

    def get_all_fan_drawers(self):
        self.drawer.get_all_fans = lambda: [self.fan]
        return [self.drawer]

    def get_all_psus(self):
        self.psu.get_all_fans = lambda: []
        self.psu.get_all_thermals = lambda: []
        return [self.psu]

    def get_all_pdbs(self):
        raise NotImplementedError

    def get_all_modules(self):
        for empty in ('get_all_fans', 'get_all_thermals', 'get_all_psus',
                      'get_all_components', 'get_all_voltage_sensors',
                      'get_all_current_sensors'):
            setattr(self.module, empty, lambda: [])
        self.module.get_system_eeprom_info = lambda: {}
        return [self.module]

    def get_all_thermals(self):
        return []

    def get_all_components(self):
        return [self.component]

    def get_all_voltage_sensors(self):
        return [self.sensor]

    def get_all_current_sensors(self):
        return []

    def is_modular_chassis(self):
        return True

    def get_watchdog(self):
        return self.watchdog

    def get_sed_mgmt(self):
        return self.sed

    def get_liquid_cooling(self):
        raise NotImplementedError

    def get_bmc(self):
        raise NotImplementedError

    def get_system_eeprom_info(self):
        raise NotImplementedError


# (facade method, args, which device should have been asked, base-class method)
ACTIONS = [
    ('set_fan_led', ('fan 1', 'amber'), 'fan', 'set_status_led'),
    ('set_fan_speed', ('fan 1', 30), 'fan', 'set_speed'),
    ('set_fan_drawer_led', ('D1', 'green'), 'drawer', 'set_status_led'),
    ('set_psu_led', ('P1', 'red'), 'psu', 'set_status_led'),
    ('get_psu_master_led', ('P1',), 'psu', 'get_status_master_led'),
    ('set_psu_master_led', ('P1', 'green'), 'psu', 'set_status_master_led'),
    ('set_sensor_high_threshold', ('v1', 10), 'sensor', 'set_high_threshold'),
    ('set_sensor_low_threshold', ('v1', 1), 'sensor', 'set_low_threshold'),
    ('install_firmware', ('C1', '/i'), 'component', 'install_firmware'),
    ('update_firmware', ('C1', '/i'), 'component', 'update_firmware'),
    ('auto_update_firmware', ('C1', '/i', 'cold'), 'component', 'auto_update_firmware'),
    ('get_available_firmware_version', ('C1', '/i'), 'component',
     'get_available_firmware_version'),
    ('get_firmware_update_notification', ('C1', '/i'), 'component',
     'get_firmware_update_notification'),
    ('reboot_module', ('M1', 'DPU'), 'module', 'reboot'),
    ('set_module_admin_state', ('M1', True), 'module', 'set_admin_state'),
    ('set_module_admin_state_gracefully', ('M1', True), 'module',
     'set_admin_state_gracefully'),
    ('power_cycle_module', ('M1',), 'module', 'do_power_cycle'),
    ('module_pre_shutdown', ('M1',), 'module', 'module_pre_shutdown'),
    ('module_post_startup', ('M1',), 'module', 'module_post_startup'),
    ('set_module_state_transition', ('M1', 'rec'), 'module',
     'set_module_state_transition'),
    ('clear_module_state_transition', ('M1',), 'module',
     'clear_module_state_transition'),
    ('clear_module_gnoi_halt', ('M1',), 'module',
     'clear_module_gnoi_halt_in_progress'),
    ('set_chassis_led', ('green',), 'chassis', 'set_status_led'),
    ('initialize_system_led', (), 'chassis', 'initizalize_system_led'),
    ('init_midplane_switch', (), 'chassis', 'init_midplane_switch'),
    ('arm_watchdog', (60,), 'watchdog', 'arm'),
    ('disarm_watchdog', (), 'watchdog', 'disarm'),
    ('change_sed_password', ('pw',), 'sed', 'change_sed_password'),
    ('reset_sed_password', (), 'sed', 'reset_sed_password'),
]


@pytest.mark.parametrize('method,args,device,expected', ACTIONS,
                         ids=[a[0] for a in ACTIONS])
def test_an_action_asks_the_right_device_for_the_right_method(
        method, args, device, expected):
    chassis = RecordingChassis([expected])
    getattr(PlatformApi(chassis), method)(*args)
    recorded = [name for name, _a in getattr(chassis, device).calls]
    assert recorded == [expected], (
        '%s should have called %s.%s' % (method, device, expected))


@pytest.mark.parametrize('method,args,device,expected', ACTIONS,
                         ids=[a[0] for a in ACTIONS])
def test_an_action_a_platform_does_not_implement_names_what_is_missing(
        method, args, device, expected):
    # The device answers nothing, so every action must report which base-class
    # method it wanted -- not AttributeError from somewhere deeper.
    chassis = RecordingChassis([])
    with pytest.raises(NotImplementedError) as caught:
        getattr(PlatformApi(chassis), method)(*args)
    assert expected in str(caught.value)


@pytest.mark.parametrize('method,args,device,expected', ACTIONS,
                         ids=[a[0] for a in ACTIONS])
def test_an_action_passes_its_arguments_through(method, args, device, expected):
    chassis = RecordingChassis([expected])
    getattr(PlatformApi(chassis), method)(*args)
    passed = getattr(chassis, device).calls[0][1]
    # With On(), the first argument is the row name and is consumed by the
    # lookup -- unless the declaration says pass_key, which only
    # set_module_state_transition and clear_module_state_transition do.
    if method.endswith('module_state_transition'):
        assert passed == args
    elif device in ('chassis', 'watchdog', 'sed'):
        assert passed == args
    else:
        assert passed == args[1:]


# -- the generated row classes --------------------------------------------
#
# Seventeen row types, each with the same three generated dunders.  Driven off
# whatever the module declares rather than a list written here, so a row added
# to the stub is covered the moment it is generated.

import inspect

from platform_api import facade as facade_module

ROW_CLASSES = [
    obj for _name, obj in inspect.getmembers(facade_module, inspect.isclass)
    if hasattr(obj, '__slots__') and obj.__module__ == facade_module.__name__
]


def test_the_module_declares_the_rows_the_stub_does():
    assert len(ROW_CLASSES) >= 17, 'rows went missing from the generated module'


@pytest.mark.parametrize('row_cls', ROW_CLASSES, ids=lambda c: c.__name__)
def test_a_row_defaults_every_column_to_absent(row_cls):
    row = row_cls()
    assert all(getattr(row, key) is None for key in row.__slots__)


@pytest.mark.parametrize('row_cls', ROW_CLASSES, ids=lambda c: c.__name__)
def test_a_row_is_equal_to_one_built_the_same_way(row_cls):
    values = {key: 'v-%s' % key for key in row_cls.__slots__}
    assert row_cls(**values) == row_cls(**values)
    if row_cls.__slots__:
        other = dict(values)
        other[row_cls.__slots__[0]] = 'different'
        assert row_cls(**values) != row_cls(**other)


@pytest.mark.parametrize('row_cls', ROW_CLASSES, ids=lambda c: c.__name__)
def test_a_row_is_not_equal_to_something_that_is_not_a_row(row_cls):
    assert row_cls().__eq__(object()) is NotImplemented


@pytest.mark.parametrize('row_cls', ROW_CLASSES, ids=lambda c: c.__name__)
def test_a_row_repr_names_its_class_and_every_column(row_cls):
    text = repr(row_cls())
    assert text.startswith(row_cls.__name__ + '(')
    assert all(key in text for key in row_cls.__slots__)


@pytest.mark.parametrize('row_cls', ROW_CLASSES, ids=lambda c: c.__name__)
def test_a_row_refuses_a_column_it_does_not_have(row_cls):
    # A generated builder that drifted from the stub would pass a field this
    # row has never heard of; silently dropping it is how that goes unnoticed.
    with pytest.raises(TypeError) as caught:
        row_cls(no_such_column=1)
    assert 'no_such_column' in str(caught.value)


# -- the helpers the generated code is made of -----------------------------

def test_call_treats_absent_raising_and_none_alike():
    assert facade_module._call(None) is None
    assert facade_module._call(lambda: None) is None
    assert facade_module._call(_raiser(NotImplementedError)) is None
    # Five base-class methods return the exception class instead of raising.
    assert facade_module._call(lambda: NotImplementedError) is None
    assert facade_module._call(lambda: 0) == 0, 'a falsy answer is still an answer'
    assert facade_module._call(lambda: None, 'fallback') == 'fallback'


def _raiser(exc):
    def f():
        raise exc
    return f


def test_scalar_coerces_from_the_declared_types_only():
    scalar = facade_module._scalar
    assert scalar(1.5, (), ()) == 1.5
    assert scalar('12', ('N/A',), ('int', 'str')) == 12
    assert scalar('1.5', ('N/A',), ('str',)) == 1.5
    assert scalar('nonsense', (), ('str',)) is None
    assert scalar(object(), (), ('int',)) is None
    assert scalar(None, (), ()) is None
    # A bool where a number is declared is bad data, not 0 or 1.
    assert scalar(True, (), ()) is None
    # Nothing to coerce from: the value is dropped rather than guessed at.
    assert scalar('12', (), ()) is None


def test_at_reads_one_slot_and_survives_a_short_answer():
    at = facade_module._at
    assert at(('a', 'b'), 1) == 'b'
    assert at(('a',), 1) is None
    assert at(None, 0) is None
    assert at(42, 0) is None, 'an unindexable answer is absent, not a crash'


def test_pairs_and_one_and_iter_answer_emptily():
    assert list(facade_module._pairs(None)) == []
    assert list(facade_module._pairs('not a mapping')) == []
    assert list(facade_module._pairs({'a': 1})) == [('a', 1)]
    assert facade_module._one(None) == ()
    assert facade_module._one('x') == ('x',)
    assert facade_module._iter(None) == ()
    assert facade_module._iter([1]) == [1]


def test_fmt_prefers_what_the_platform_said():
    fmt = facade_module._fmt
    assert fmt('real name', '{parent} thing {i}', 'P', 0) == 'real name'
    assert fmt(None, '{parent} thing {i}', 'P', 0) == 'P thing 1'
    assert fmt(7, 'x', 'P', 0) == '7', 'a non-string name is still a name'


def test_omitted_is_readable_at_runtime():
    # It is in the module so that "why is there no get_num_psus" has an answer
    # where somebody is already looking.
    assert any(path == 'ChassisBase.get_num_psus'
               for path, _reason in facade_module.OMITTED)
    assert all(reason for _path, reason in facade_module.OMITTED)


# -- the hand-written half, against answers that are the wrong shape -------
#
# Everything here is an escape hatch precisely because the answer's shape is
# not something a declaration can pin down. That makes a platform answering
# something unexpected the normal failure, not the exotic one.

class OddBmc(object):
    def __init__(self, **answers):
        self._answers = answers

    def __getattr__(self, attr):
        if attr not in self._answers:
            raise AttributeError(attr)
        return lambda *args: self._answers[attr]


class OddChassis(Chassis):
    def __init__(self, bmc=None, **kw):
        Chassis.__init__(self, **kw)
        self._bmc = bmc

    def get_bmc(self):
        if self._bmc is None:
            raise NotImplementedError
        return self._bmc


def test_a_bmc_command_that_did_not_answer_a_pair_says_so():
    api = PlatformApi(OddChassis(bmc=OddBmc(reset_root_password='not a pair')))
    with pytest.raises(NotImplementedError) as caught:
        api.bmc_reset_root_password()
    assert 'reset_root_password' in str(caught.value)


def test_a_bmc_that_lacks_the_command_says_which_one():
    api = PlatformApi(OddChassis(bmc=OddBmc()))
    with pytest.raises(NotImplementedError) as caught:
        api.bmc_close_session('s')
    assert 'close_session' in str(caught.value)


def test_open_session_without_credentials_still_carries_the_code():
    # config/bmc.py:41 checks for exactly this before reading them.
    api = PlatformApi(OddChassis(bmc=OddBmc(open_session=(4, ('denied', None)))))
    res = api.bmc_open_session()
    assert (res.code, res.message, res.session_id, res.token) == (4, 'denied', None, None)


def test_open_session_whose_payload_is_not_a_pair_degrades_to_a_message():
    api = PlatformApi(OddChassis(bmc=OddBmc(open_session=(1, 'flat message'))))
    res = api.bmc_open_session()
    assert (res.code, res.message, res.session_id) == (1, 'flat message', None)


def test_open_session_with_short_credentials_keeps_neither_half():
    api = PlatformApi(OddChassis(bmc=OddBmc(open_session=(0, ('ok', ('only-one',))))))
    res = api.bmc_open_session()
    assert (res.session_id, res.token) == (None, None)


def test_a_debug_dump_whose_payload_is_flat_degrades_to_a_message():
    api = PlatformApi(OddChassis(
        bmc=OddBmc(trigger_bmc_debug_log_dump=(2, 'busy'))))
    res = api.bmc_trigger_debug_log_dump()
    assert (res.code, res.task_id, res.message) == (2, None, 'busy')


def test_update_firmware_drops_the_component_list_it_does_not_declare():
    api = PlatformApi(OddChassis(
        bmc=OddBmc(update_firmware=(0, ('done', ['bmc', 'cpld'])))))
    assert PlatformApi(OddChassis(bmc=OddBmc(
        update_firmware=(0, ('done', ['bmc']))))).bmc_update_firmware('/i').message == 'done'
    assert api.bmc_update_firmware('/i').code == 0


def test_bmc_reset_passes_the_graceful_flag():
    api = PlatformApi(OddChassis(bmc=OddBmc(request_bmc_reset=(0, 'ok'))))
    assert api.bmc_reset(True).code == 0


def test_get_debug_log_dump_is_an_ordinary_pair():
    api = PlatformApi(OddChassis(bmc=OddBmc(get_bmc_debug_log_dump=(0, '/tmp/d'))))
    assert api.bmc_get_debug_log_dump('t', 'f', '/tmp').message == '/tmp/d'


def test_asics_on_a_platform_with_no_modules_is_empty():
    assert PlatformApi(Chassis()).get_asics() == []


def test_an_asic_entry_that_is_not_indexable_is_skipped():
    mod = Module('LC1')
    mod.get_all_asics = lambda: [42, ('4', '0000:05:00.0')]
    rows = PlatformApi(Chassis(modules=[mod])).get_asics()
    assert [(r.asic_id, r.pci_address) for r in rows] == [('4', '0000:05:00.0')]


def test_a_module_with_no_name_still_parents_its_asics():
    mod = Module('LC1')
    mod.get_name = lambda: None
    mod.get_all_asics = lambda: [('4', 'addr')]
    assert PlatformApi(Chassis(modules=[mod])).get_asics()[0].parent_name == 'Module 1'


def test_the_sensors_yaml_provider_is_quiet_when_there_is_no_file():
    from platform_api import _escape_hatch
    hatch = _escape_hatch.EscapeHatches(Chassis())
    assert hatch.voltage_sensors_from_yaml() == []
    assert hatch.current_sensors_from_yaml() == []
    # Read once: the second call must not go back to the filesystem.
    assert hatch._sensors_yaml() == {}


def test_the_sensors_yaml_is_read_once_from_the_platform_directory(tmp_path):
    pytest.importorskip('yaml')
    yml = tmp_path / 'sensors.yaml'
    yml.write_text('voltage_sensors:\n- {name: yaml-v, sensor: /sys/x}\n')
    hatch = _hatch()
    with platform_dir(str(tmp_path)):
        assert hatch._sensors_yaml() == {
            'voltage_sensors': [{'name': 'yaml-v', 'sensor': '/sys/x'}]}
        yml.write_text('current_sensors: []\n')
        assert 'voltage_sensors' in hatch._sensors_yaml()


def test_an_empty_sensors_yaml_is_a_platform_with_no_yaml_sensors(tmp_path):
    pytest.importorskip('yaml')
    (tmp_path / 'sensors.yaml').write_text('')
    with platform_dir(str(tmp_path)):
        assert _hatch().voltage_sensors_from_yaml() == []


def test_a_sensors_yaml_entry_the_factory_cannot_build_is_no_sensors():
    """`SensorFs.factory` indexes each entry as a mapping; a malformed file
    must cost the file's sensors, not the chassis' own."""
    hatch = _hatch()
    hatch._sensors_data = {'voltage_sensors': 'not a list of sensors'}
    assert hatch.voltage_sensors_from_yaml() == []


# -- pcie ------------------------------------------------------------------
#
# pcied is the one daemon that does not reach the platform through the chassis,
# so its two hatches are the only ones a chassis fixture cannot drive.


class FakePcie(object):
    """What `PcieUtil.get_pcie_check()` and `get_pcie_aer_stats()` answer."""

    def __init__(self, check=(), aer=None):
        self._check, self._aer = list(check), aer or {}

    def get_pcie_check(self):
        return self._check

    def get_pcie_aer_stats(self, bus, dev, func):
        return self._aer


def _hatch_with_pcie(pcie):
    from platform_api import _escape_hatch
    hatch = _escape_hatch.EscapeHatches(Chassis())
    hatch._pcie, hatch._pcie_tried = pcie, True
    return hatch


def test_pcie_rows_carry_the_yamls_hex_numbers_as_numbers():
    """The daemon's STATE_DB key is `%02x:%02x.%d` of these, so a string that
    was never parsed could not be re-formatted into it."""
    hatch = _hatch_with_pcie(FakePcie(check=[
        {'name': 'RootPort', 'bus': '03', 'dev': '0a', 'fn': '1', 'result': 'Passed'},
    ]))
    row, = hatch.get_pcie_devices()
    assert (row.name, row.bus, row.dev, row.fn, row.present) == ('RootPort', 3, 10, 1, True)


def test_anything_but_passed_is_a_device_that_was_not_found():
    hatch = _hatch_with_pcie(FakePcie(check=[
        {'name': 'A', 'bus': '00', 'dev': '00', 'fn': '0', 'result': 'Failed'},
        {'name': 'B', 'bus': '00', 'dev': '01', 'fn': '0'},
    ]))
    assert [r.present for r in hatch.get_pcie_devices()] == [False, False]


def test_one_malformed_pcie_entry_does_not_lose_the_parts_list():
    """pcie.yaml is hand-written per platform.  A daemon that reported nothing
    because of one bad line would hide every device that is genuinely missing."""
    hatch = _hatch_with_pcie(FakePcie(check=[
        {'name': 'bad', 'bus': 'zz', 'dev': '00', 'fn': '0', 'result': 'Passed'},
        {'name': 'good', 'bus': '01', 'dev': '00', 'fn': '0', 'result': 'Passed'},
    ]))
    assert [r.name for r in hatch.get_pcie_devices()] == ['good']


def test_aer_stats_flatten_to_one_row_per_counter():
    hatch = _hatch_with_pcie(FakePcie(aer={
        'correctable': {'BadTLP': '0', 'BadDLLP': '2'},
        'fatal': {},
        'non_fatal': {'RxOF': '1'},
    }))
    rows = hatch.get_pcie_aer_stats(1, 0, 0)
    assert {(r.severity, r.field, r.value) for r in rows} == {
        ('correctable', 'BadTLP', '0'),
        ('correctable', 'BadDLLP', '2'),
        ('non_fatal', 'RxOF', '1'),
    }


def test_a_platform_with_no_pcie_module_answers_empty_rather_than_raising():
    from platform_api import _escape_hatch
    hatch = _escape_hatch.EscapeHatches(Chassis())
    hatch._pcie_tried = True
    assert hatch.get_pcie_devices() == []
    assert hatch.get_pcie_aer_stats(0, 0, 0) == []


# -- storage ---------------------------------------------------------------


class FakeDisk(object):
    """An SsdUtil-shaped object: readings are only current after a fetch."""

    def __init__(self, health='98', broken=()):
        self.fetched = []
        self._health = health
        self._broken = set(broken)

    def fetch_parse_info(self, path):
        self.fetched.append(path)

    def _answer(self, name, value):
        if name in self._broken:
            raise NotImplementedError(name)
        return value

    def get_model(self):
        return self._answer('get_model', 'SAMSUNG MZ')

    def get_serial(self):
        return self._answer('get_serial', 'S3Z')

    def get_firmware(self):
        return self._answer('get_firmware', 'EDA7602Q')

    def get_health(self):
        return self._answer('get_health', self._health)

    def get_temperature(self):
        return self._answer('get_temperature', '31')

    def get_disk_io_reads(self):
        return self._answer('get_disk_io_reads', '100')

    def get_disk_io_writes(self):
        return self._answer('get_disk_io_writes', '200')

    def get_reserved_blocks(self):
        return self._answer('get_reserved_blocks', '1')

    def get_fs_io_reads(self):
        return self._answer('get_fs_io_reads', 4242)

    def get_fs_io_writes(self):
        return self._answer('get_fs_io_writes', 2121)


def _hatch_with_storage(devices):
    from platform_api import _escape_hatch

    class Devices(object):
        pass

    d = Devices()
    d.devices = devices
    hatch = _escape_hatch.EscapeHatches(Chassis())
    hatch._storage, hatch._storage_tried = d, True
    return hatch


def test_a_disk_is_parsed_before_it_is_read():
    """`get_firmware` and friends answer whatever the last parse produced, so a
    row read without one is the constructor's reading and not this cycle's.

    The block-device root comes from `storage_devices`, which imports `blkinfo`
    through `usb.py`; it is faked so the test does not depend on that being
    installed, or on another test having put a mock of it on the path."""
    disk = FakeDisk()
    name = 'sonic_platform_base.sonic_storage.storage_devices'
    with fake_modules(**{name: _module(name, BLKDEV_BASE_PATH='/dev')}):
        row, = _hatch_with_storage({'sda': disk}).get_storage_devices()
    assert disk.fetched == ['/dev/sda']
    assert (row.name, row.available, row.firmware, row.health) == (
        'sda', True, 'EDA7602Q', '98')
    assert (row.fs_io_reads, row.fs_io_writes) == (4242, 2121)


def test_a_disk_with_no_utility_class_is_a_row_that_says_so():
    """`StorageDevices` maps such a disk to None.  Dropping it would make a
    switch with an unreadable disk look like a switch without one."""
    row, = _hatch_with_storage({'sdb': None}).get_storage_devices()
    assert (row.name, row.available) == ('sdb', False)
    assert row.model == 'N/A' and row.fs_io_reads is None


def test_one_unreadable_field_does_not_cost_the_rest_of_the_disk():
    disk = FakeDisk(broken=('get_temperature', 'get_fs_io_reads'))
    row, = _hatch_with_storage({'sda': disk}).get_storage_devices()
    assert row.temperature == 'N/A'
    assert row.fs_io_reads is None
    assert row.firmware == 'EDA7602Q', 'the rest of the disk still reads'


def test_the_counters_cross_as_numbers_and_the_readings_as_text():
    """The daemon subtracts one cycle's counters from the last to find what
    happened while it was down; the other columns it only ever prints."""
    row, = _hatch_with_storage({'sda': FakeDisk()}).get_storage_devices()
    assert isinstance(row.fs_io_reads, int)
    assert isinstance(row.temperature, str)


def test_a_platform_with_no_storage_object_answers_empty():
    from platform_api import _escape_hatch
    hatch = _escape_hatch.EscapeHatches(Chassis())
    hatch._storage_tried = True
    assert hatch.get_storage_devices() == []


# -- how the two non-chassis hatches find their object -------------------------
#
# Both reach outside this repo, and the *order* they try in is the behaviour:
# a vendor that ships its own class must win over the base one, and neither
# being there must not be an error.  The tests above inject the object; these
# drive the construction itself, with the modules faked into sys.modules.


@contextlib.contextmanager
def fake_modules(**modules):
    """Put modules on `sys.modules` for the duration, and take them off again."""
    import sys
    saved = {name: sys.modules.get(name) for name in modules}
    try:
        for name, mod in modules.items():
            if mod is None:
                sys.modules[name] = None      # import raises ImportError
            else:
                sys.modules[name] = mod
        yield
    finally:
        for name, old in saved.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old


def _module(name, **attrs):
    import types
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


def _hatch():
    from platform_api import _escape_hatch
    return _escape_hatch.EscapeHatches(Chassis())


@contextlib.contextmanager
def platform_dir(path='/usr/share/sonic/platform'):
    """`device_info.get_paths_to_platform_and_hwsku_dirs()` answering.

    On a real switch it reads the platform out of machine.conf; here it raises,
    and the hatch treats that as "no platform" and stops before the import --
    so a test of the import order has to get past it first.
    """
    from sonic_py_common import device_info
    with mock.patch.object(device_info, 'get_paths_to_platform_and_hwsku_dirs',
                           return_value=(path, path + '/hwsku')):
        yield


def test_a_vendors_own_pcie_class_wins_over_the_base_one():
    """`sonic_platform.pcie.Pcie` is the vendor's; `PcieUtil` is the fallback
    every platform has.  Taking the fallback first would ignore a vendor that
    went to the trouble of implementing its own."""
    built = []

    class VendorPcie(object):
        def __init__(self, path):
            built.append(path)

    hatch = _hatch()
    with platform_dir(), fake_modules(
        sonic_platform=_module('sonic_platform'),
        **{'sonic_platform.pcie': _module('sonic_platform.pcie', Pcie=VendorPcie)},
    ):
        util = hatch._pcie_util()
    assert isinstance(util, VendorPcie)
    assert built == ['/usr/share/sonic/platform'], 'built with the platform directory'


def test_a_pcie_object_is_not_built_without_a_platform_directory():
    """`device_info` answering nothing means there is no platform to read a
    pcie.yaml out of, and constructing against a path that does not exist
    would fail later and further away."""
    assert _hatch()._pcie_util() is None


def test_a_platform_without_its_own_pcie_class_falls_back_to_the_base_one():
    from sonic_platform_base.sonic_pcie.pcie_common import PcieUtil
    hatch = _hatch()
    with platform_dir(), fake_modules(**{'sonic_platform.pcie': None}):
        util = hatch._pcie_util()
    assert isinstance(util, PcieUtil)


def test_a_platform_with_neither_pcie_class_is_not_an_error():
    """The rows come back empty and pcied says it found nothing, which is the
    same thing the Python daemon does with a missing config file."""
    hatch = _hatch()
    with platform_dir(), fake_modules(**{
        'sonic_platform.pcie': None,
        'sonic_platform_base.sonic_pcie.pcie_common': None,
    }):
        assert hatch._pcie_util() is None
    assert hatch.get_pcie_devices() == []
    assert hatch.get_pcie_aer_stats(0, 0, 0) == []


def test_the_pcie_object_is_built_once():
    """`get_pcie_check` runs every minute forever; constructing the object
    parses the platform's yaml, and doing that per cycle would be a file read
    a minute for the life of the switch."""
    built = []

    class VendorPcie(object):
        def __init__(self, path):
            built.append(path)

    hatch = _hatch()
    with platform_dir(), fake_modules(
        sonic_platform=_module('sonic_platform'),
        **{'sonic_platform.pcie': _module('sonic_platform.pcie', Pcie=VendorPcie)},
    ):
        hatch._pcie_util()
        hatch._pcie_util()
    assert len(built) == 1


def test_a_pcie_object_that_raises_answers_empty_rather_than_propagating():
    class Refusing(object):
        def get_pcie_check(self):
            raise NotImplementedError

        def get_pcie_aer_stats(self, bus, dev, func):
            raise NotImplementedError

    hatch = _hatch()
    hatch._pcie, hatch._pcie_tried = Refusing(), True
    assert hatch.get_pcie_devices() == []
    assert hatch.get_pcie_aer_stats(0, 0, 0) == []


def test_the_storage_object_is_built_once_and_absence_is_not_an_error():
    built = []

    class FakeDevices(object):
        def __init__(self):
            built.append(1)
            self.devices = {}

    hatch = _hatch()
    with fake_modules(**{'sonic_platform_base.sonic_storage.storage_devices':
                         _module('sonic_platform_base.sonic_storage.storage_devices',
                                 StorageDevices=FakeDevices)}):
        assert hatch._storage_devices() is not None
        hatch._storage_devices()
    assert len(built) == 1

    hatch = _hatch()
    with fake_modules(**{'sonic_platform_base.sonic_storage.storage_devices': None}):
        assert hatch._storage_devices() is None
    assert hatch.get_storage_devices() == []


def test_a_disk_whose_parse_fails_still_publishes_what_it_has():
    """stormond's own per-device `except` fires after its dict is half-built
    and it writes nothing; this writes the readings the constructor saw, which
    is a stale row rather than no row."""
    class Stubborn(FakeDisk):
        def fetch_parse_info(self, path):
            raise OSError('smartctl not found')

    row, = _hatch_with_storage({'sda': Stubborn()}).get_storage_devices()
    assert row.available is True
    assert row.firmware == 'EDA7602Q', 'the constructor\'s reading, not this cycle\'s'


def test_the_facade_forwards_the_non_chassis_methods_to_the_hatch():
    """These three are the only snapshot methods whose object does not come
    from the chassis, so the facade cannot reach them the way it reaches the
    rest -- and a generated delegation that named the wrong hatch method would
    be caught nowhere else."""
    api = PlatformApi(Chassis())
    api._hatch._pcie, api._hatch._pcie_tried = FakePcie(
        check=[{'name': 'A', 'bus': '01', 'dev': '00', 'fn': '0', 'result': 'Passed'}],
        aer={'correctable': {'BadTLP': '0'}},
    ), True
    api._hatch._storage, api._hatch._storage_tried = _module('d', devices={'sda': FakeDisk()}), True

    assert [r.name for r in api.get_pcie_devices()] == ['A']
    assert [(r.severity, r.field) for r in api.get_pcie_aer_stats(1, 0, 0)] == [
        ('correctable', 'BadTLP')]
    assert [r.name for r in api.get_storage_devices()] == ['sda']


# -- the eeprom hatch's three ways to have nothing -----------------------------


def test_a_platform_with_no_eeprom_at_all_answers_false():
    """Three ways not to have one, and a platform uses all three: no method,
    a method that raises, and a method that answers None."""
    hatch = _hatch()
    assert hatch.eeprom_update_db() is False          # Chassis().get_eeprom raises

    class NoMethod(object):
        pass

    from platform_api import _escape_hatch
    assert _escape_hatch.EscapeHatches(NoMethod()).eeprom_update_db() is False


def test_an_eeprom_that_cannot_be_read_leaves_the_table_alone():
    """False rather than raising: the daemon logs and leaves the table as it
    was, which beats half of one."""
    class Unreadable(object):
        def read_eeprom(self):
            raise NotImplementedError

    class Empty(object):
        def read_eeprom(self):
            return None

    class Unwritable(object):
        def read_eeprom(self):
            return b'raw'

        def update_eeprom_db(self, data):
            raise NotImplementedError

    from platform_api import _escape_hatch
    for eeprom in (Unreadable(), Empty(), Unwritable()):
        hatch = _escape_hatch.EscapeHatches(Chassis(eeprom=eeprom))
        assert hatch.eeprom_update_db() is False


def test_the_platforms_own_writer_reports_success_as_zero():
    """`update_eeprom_db` is Python's, and its contract is the shell's: 0 is
    success.  Returning it unchanged would invert the answer."""
    class Eeprom(object):
        def __init__(self, rc):
            self.rc = rc

        def read_eeprom(self):
            return b'raw'

        def update_eeprom_db(self, data):
            return self.rc

    from platform_api import _escape_hatch
    assert _escape_hatch.EscapeHatches(Chassis(eeprom=Eeprom(0))).eeprom_update_db() is True
    assert _escape_hatch.EscapeHatches(Chassis(eeprom=Eeprom(1))).eeprom_update_db() is False


def test_a_thermal_manager_that_refuses_to_report_an_interval():
    class Refusing(object):
        @classmethod
        def get_interval(cls):
            raise NotImplementedError

        @classmethod
        def initialize(cls):
            pass

        @classmethod
        def load(cls, path):
            pass

        @classmethod
        def init_thermal_algorithm(cls, chassis):
            pass

    class WithRefusing(Chassis):
        def get_thermal_manager(self):
            return Refusing

    api = PlatformApi(WithRefusing())
    api.tm_initialize()
    assert api.tm_get_interval() is None


def test_a_thermal_manager_interval_is_seconds_however_it_was_declared():
    class IntInterval(object):
        @classmethod
        def get_interval(cls):
            return 60          # the base class declares int; vendors return float

    class WithInt(Chassis):
        def get_thermal_manager(self):
            return IntInterval

    assert PlatformApi(WithInt()).tm_get_interval() == 60.0


# -- a chassis with one of everything --------------------------------------
#
# The sources a minimal mock never reaches: PDBs, module-mounted sensors and
# components, module system EEPROM. Each is a declared source, so each is code
# the generator emitted and nobody had run.

class Pdb(Psu):
    pass


class LoadedModule(Module):
    def __init__(self, name):
        Module.__init__(self, name)

    def get_all_components(self):
        return [Component('LC1-CPLD', '2.0')]

    def get_all_voltage_sensors(self):
        return [Sensor('lc-v', 3300, 'mV')]

    def get_all_current_sensors(self):
        return [Sensor('lc-c', 900, 'mA')]

    def get_system_eeprom_info(self):
        return {'0x22': 'LC-SN'}


class LoadedChassis(Chassis):
    def __init__(self):
        Chassis.__init__(self, modular=True)
        self.pdb = Pdb('PDB-1', thermals=[Thermal('pdb-t', 30.0)])
        self.module = LoadedModule('LC1')

    def get_all_pdbs(self):
        return [self.pdb]

    def get_all_modules(self):
        return [self.module]

    def get_all_voltage_sensors(self):
        return [Sensor('sys-v', 12000, 'mV')]

    def get_all_current_sensors(self):
        return [Sensor('sys-c', 100, 'mA')]

    def get_all_components(self):
        return [Component('BIOS', '1.0')]

    def get_system_eeprom_info(self):
        return {'0x21': 'MSN4700'}


def test_pdb_thermals_and_pdb_rows_both_appear():
    api = PlatformApi(LoadedChassis())
    assert ('pdb-t', 'PDB-1') in names(api.get_thermals())
    assert [(r.name, r.kind) for r in api.get_psus()] == [('PDB-1', 'pdb')]


def test_sensors_come_from_the_chassis_and_from_modules_in_declared_order():
    rows = PlatformApi(LoadedChassis()).get_sensors()
    assert [(r.name, r.kind, r.parent_name) for r in rows] == [
        ('sys-v', 'voltage', 'chassis 1'),
        ('lc-v', 'voltage', 'LC1'),
        ('sys-c', 'current', 'chassis 1'),
        ('lc-c', 'current', 'LC1'),
    ]


def test_components_and_eeprom_reach_into_modules_too():
    api = PlatformApi(LoadedChassis())
    assert [(r.name, r.parent_name) for r in api.get_components()] == \
        [('BIOS', 'chassis 1'), ('LC1-CPLD', 'LC1')]
    assert [(r.source, r.code, r.parent_name) for r in api.get_eeprom()] == \
        [('chassis', '0x21', 'chassis 1'), ('module', '0x22', 'LC1')]


def test_every_snapshot_answers_on_a_loaded_chassis():
    api = PlatformApi(LoadedChassis())
    for method in ('get_thermals', 'get_fans', 'get_fan_drawers', 'get_psus',
                   'get_modules', 'get_components', 'get_sensors', 'get_eeprom',
                   'get_bmcs', 'get_watchdogs', 'get_leak_sensors',
                   'get_leak_profiles', 'get_asics'):
        assert isinstance(getattr(api, method)(), list), method
    assert api.get_chassis_info().is_modular_chassis is True


def test_addressing_a_row_that_no_source_produced_is_a_key_error():
    api = PlatformApi(LoadedChassis())
    with pytest.raises(KeyError):
        api.set_psu_led('nope', 'red')
    with pytest.raises(KeyError):
        api.set_sensor_high_threshold('nope', 1)
    with pytest.raises(KeyError):
        api.reboot_module('nope', 'cold')


# -- the traversal branches a simple mock never reaches ---------------------

class FannedModule(Module):
    """A module that carries its own fans and its own PSUs."""

    def __init__(self, name, fans=(), psus=()):
        Module.__init__(self, name)
        self._own_fans, self._own_psus = list(fans), list(psus)

    def get_all_fans(self):
        return self._own_fans

    def get_all_psus(self):
        return self._own_psus


def test_module_mounted_fans_are_published_under_the_module():
    mod = FannedModule('LC1', fans=[Fan('lc-fan', 40)])
    rows = PlatformApi(Chassis(modules=[mod], modular=True)).get_fans()
    row = [r for r in rows if r.name == 'lc-fan'][0]
    assert (row.kind, row.parent_name, row.drawer_name) == ('module', 'LC1', 'N/A')


def test_an_absent_pdb_contributes_no_thermals():
    class WithPdbs(Chassis):
        def get_all_pdbs(self):
            return [Psu('PDB-1', present=False, thermals=[Thermal('hidden', 1.0)]),
                    Psu('PDB-2', present=True, thermals=[Thermal('shown', 2.0)])]

    assert names(PlatformApi(WithPdbs()).get_thermals()) == [('shown', 'PDB-2')]


def test_an_absent_psu_inside_a_module_contributes_no_thermals():
    # The four-hop source has its own presence guard.
    mod = FannedModule('LC1', psus=[
        Psu('LC-PSU-1', present=False, thermals=[Thermal('hidden', 1.0)]),
        Psu('LC-PSU-2', present=True, thermals=[Thermal('shown', 2.0)]),
    ])
    rows = names(PlatformApi(Chassis(modules=[mod], modular=True)).get_thermals())
    assert rows == [('shown', 'LC-PSU-2')]


def test_addressing_a_drawer_or_component_that_no_source_produced():
    api = PlatformApi(Chassis(drawers=[Drawer('D1', [])]))
    with pytest.raises(KeyError):
        api.set_fan_drawer_led('nope', 'green')
    with pytest.raises(KeyError):
        api.install_firmware('nope', '/i')


def test_sensors_from_the_platform_yaml_are_published_first():
    # sensormond:209 concatenates the file's sensors before the chassis' own,
    # and the row index is what a consumer sees.
    api = PlatformApi(SensorChassis(voltage=[Sensor('sys-v', 12000, 'mV')]))
    api._hatch._sensors_data = {
        'voltage_sensors': [{'name': 'yaml-v', 'sensor': '/sys/x'}],
        'current_sensors': [{'name': 'yaml-c', 'sensor': '/sys/y'}],
    }
    rows = api.get_sensors()
    assert [(r.name, r.kind) for r in rows] == [
        ('yaml-v', 'voltage'), ('sys-v', 'voltage'), ('yaml-c', 'current')]


# -- an optional source whose sequence goes wrong mid-iteration -------------
#
# `_call` already turns a raising accessor into an absent one, so the
# try/except a declared-optional source is wrapped in only earns its keep for
# the two cases `_call` cannot see: an accessor that is a property rather than
# a method, and a lazy sequence that raises after the first item.

def _raises_after(items):
    def gen():
        for item in items:
            yield item
        raise NotImplementedError
    return gen


class LazyChassis(Chassis):
    def __init__(self, **kw):
        Chassis.__init__(self, **kw)
        self.get_all_pdbs = _raises_after([Psu('PDB-1', thermals=[Thermal('t', 1.0)])])
        self.get_system_eeprom_info = _raises_after([])
        self.get_liquid_cooling = _raises_after([])


def test_a_lazy_sequence_that_gives_up_halfway_keeps_what_it_gave():
    api = PlatformApi(LazyChassis())
    assert names(api.get_thermals()) == [('t', 'PDB-1')]
    assert [(r.name, r.kind) for r in api.get_psus()] == [('PDB-1', 'pdb')]


def test_every_optional_source_survives_a_sequence_that_gives_up():
    api = PlatformApi(LazyChassis())
    for method in ('get_eeprom', 'get_leak_sensors', 'get_leak_profiles'):
        assert getattr(api, method)() == [], method


class PropertyChassis(Chassis):
    """A platform exposing accessors as properties that refuse.

    `_get` is a getattr, so the refusal happens at attribute access and never
    reaches `_call` -- which is the other reason an optional source is wrapped,
    and the only one that reaches a source whose leaf is singular.
    """

    @property
    def get_all_pdbs(self):
        raise NotImplementedError

    @property
    def get_watchdog(self):
        raise NotImplementedError

    @property
    def get_bmc(self):
        raise NotImplementedError

    @property
    def get_system_eeprom_info(self):
        raise NotImplementedError

    @property
    def get_liquid_cooling(self):
        raise NotImplementedError


def test_an_accessor_that_refuses_at_attribute_access_is_still_optional():
    api = PlatformApi(PropertyChassis(thermals=[Thermal('ASIC', 1.0)]))
    assert names(api.get_thermals()) == [('ASIC', 'chassis 1')]
    for method in ('get_watchdogs', 'get_bmcs', 'get_eeprom',
                   'get_leak_sensors', 'get_leak_profiles'):
        assert getattr(api, method)() == [], method


def test_a_module_list_that_gives_up_halfway_only_loses_the_optional_source():
    # System EEPROM is declared optional, so a module list that raises while
    # being walked costs the eeprom rows and nothing else.
    class LazyModules(Chassis):
        def __init__(self):
            Chassis.__init__(self, modular=True)
            self.get_all_modules = _raises_after([Module('LC1')])

    assert PlatformApi(LazyModules()).get_eeprom() == []


# -- the hand-written half, remaining refusals ------------------------------

def test_a_thermal_manager_accessor_that_raises_is_reported_once_then_absent():
    # Start-up lets it through, so thermalctld over the facade can log
    # "Thermal manager is not supported on this platform" as its Python
    # `except NotImplementedError` does.  Every call after it reads the
    # manager as absent.
    class Raising(Chassis):
        def get_thermal_manager(self):
            raise NotImplementedError

    api = PlatformApi(Raising())
    with pytest.raises(NotImplementedError):
        api.tm_initialize()
    api.tm_run_policy()
    api.tm_deinitialize()
    assert api.tm_get_interval() is None


def test_a_thermal_manager_that_cannot_be_stopped_is_still_deinitialised():
    calls = []

    class HalfStoppable(object):
        @classmethod
        def initialize(cls):
            calls.append('initialize')

        @classmethod
        def load(cls, path):
            calls.append('load')

        @classmethod
        def init_thermal_algorithm(cls, chassis):
            calls.append('init')

        @classmethod
        def stop(cls):
            raise NotImplementedError

        @classmethod
        def deinitialize(cls):
            calls.append('deinitialize')

    class WithHalf(Chassis):
        def get_thermal_manager(self):
            return HalfStoppable

    api = PlatformApi(WithHalf())
    api.tm_initialize()
    api.tm_deinitialize()
    assert calls == ['initialize', 'load', 'init', 'deinitialize']


def test_a_chassis_with_no_change_event_method_at_all_says_so():
    with pytest.raises(NotImplementedError) as caught:
        PlatformApi(Chassis()).get_change_event(0)
    assert 'get_change_event' in str(caught.value)


def test_a_change_event_whose_mapping_is_not_a_mapping_yields_nothing():
    class OddEvents(Chassis):
        def get_change_event(self, timeout=0):
            return (True, 'not a mapping')

    batch = PlatformApi(OddEvents()).get_change_event(0)
    assert (batch.ok, batch.events) == (True, [])


def test_update_firmware_whose_payload_is_flat_degrades_to_a_message():
    api = PlatformApi(OddChassis(bmc=OddBmc(update_firmware=(0, 'done'))))
    assert api.bmc_update_firmware('/i').message == 'done'
