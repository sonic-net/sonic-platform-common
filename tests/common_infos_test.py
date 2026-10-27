"""Unit tests for sonic_platform_base.sonic_thermal_control.common_infos."""

import pytest

from sonic_platform_base.sonic_thermal_control.common_infos import (
    ChassisInfo, FanDrawerInfo, FanInfo, PsuInfo, ThermalInfo)
from sonic_platform_base.sonic_thermal_control.thermal_json_object import ThermalJsonObject


class FakeFan:
    def __init__(self, present=True, healthy=True):
        self._present, self._healthy = present, healthy

    def get_presence(self):
        return self._present

    def get_status(self):
        return self._healthy


class FakeDrawer:
    def __init__(self, present=True):
        self._present = present

    def get_presence(self):
        return self._present


class FakeThermal:
    def __init__(self, temperature=40.0, high=80.0, critical=95.0):
        self._temperature, self._high, self._critical = temperature, high, critical

    def get_temperature(self):
        return self._temperature

    def get_high_threshold(self):
        return self._high

    def get_high_critical_threshold(self):
        return self._critical


class FakeSfp:
    def __init__(self, thermals=()):
        self._thermals = list(thermals)

    def get_all_thermals(self):
        return self._thermals


class FakePsu:
    def __init__(self, present=True, thermals=(), fans=()):
        self._present, self._thermals, self._fans = present, list(thermals), list(fans)

    def get_presence(self):
        return self._present

    def get_all_thermals(self):
        return self._thermals

    def get_all_fans(self):
        return self._fans


class FakeChassis:
    def __init__(self, fans=(), drawers=(), thermals=(), sfps=(), psus=(), manager=None):
        self._fans, self._drawers = list(fans), list(drawers)
        self._thermals, self._sfps, self._psus = list(thermals), list(sfps), list(psus)
        self._manager = manager

    def get_all_fans(self):
        return self._fans

    def get_all_fan_drawers(self):
        return self._drawers

    def get_all_thermals(self):
        return self._thermals

    def get_all_sfps(self):
        return self._sfps

    def get_all_psus(self):
        return self._psus

    def get_thermal_manager(self):
        return self._manager


# --- registration -----------------------------------------------------------------------

@pytest.mark.parametrize("type_name, cls", [
    ('fan_info', FanInfo),
    ('fan_drawer_info', FanDrawerInfo),
    ('thermal_info', ThermalInfo),
    ('psu_info', PsuInfo),
    ('chassis_info', ChassisInfo),
])
def test_info_type_is_registered(type_name, cls):
    # Given an info type name used in policy files
    # When it is looked up in the registry
    registered = ThermalJsonObject.get_type({'type': type_name})

    # Then it resolves to the matching info class
    assert registered is cls


@pytest.mark.parametrize("cls", [FanInfo, FanDrawerInfo, ThermalInfo, PsuInfo, ChassisInfo])
def test_info_name_and_type_alias_agree(cls):
    # Given an info class
    # When its name and type alias are compared
    # Then they are the same string
    assert cls.INFO_NAME == cls.INFO_TYPE


def test_registers_exactly_the_five_info_types():
    # Scoped to this module's own classes: the registry is global, so other common modules
    # imported in the same session legitimately add to it.
    # Given the common_infos module has been imported
    from sonic_platform_base.sonic_thermal_control import common_infos

    # When the registry is filtered to the classes it defines
    registered = {name for name, cls in ThermalJsonObject._object_type_dict.items()
                  if getattr(cls, '__module__', None) == common_infos.__name__}

    # Then exactly the five common info types are present
    assert registered == {'fan_info', 'fan_drawer_info', 'thermal_info',
                          'psu_info', 'chassis_info'}


# --- FanInfo ----------------------------------------------------------------------------

def test_fan_info_splits_presence_and_faults():
    # Given a present fan, an absent fan and a present but faulty fan
    present, absent, faulty = FakeFan(), FakeFan(present=False), FakeFan(healthy=False)
    info = FanInfo()

    # When fan info is collected for the first time
    info.collect(FakeChassis(fans=[present, absent, faulty]))

    # Then each fan lands in the right set, and the first pass counts as a change
    assert info.get_presence_fans() == {present, faulty}
    assert info.get_absence_fans() == {absent}
    assert info.get_fault_fans() == {faulty}
    assert info.get_num_present_fans() == 2
    assert info.is_presence_changed() is True
    assert info.is_status_changed() is True


def test_fan_info_reports_no_change_on_a_steady_second_pass():
    # Given a chassis whose fans do not change
    chassis = FakeChassis(fans=[FakeFan(), FakeFan(present=False)])
    info = FanInfo()

    # When fan info is collected twice
    info.collect(chassis)
    info.collect(chassis)

    # Then the second pass reports no presence or status change
    assert info.is_presence_changed() is False
    assert info.is_status_changed() is False


def test_fan_info_moves_a_fan_between_sets_when_it_is_removed():
    # Given fan info collected while a fan is present
    fan = FakeFan()
    chassis = FakeChassis(fans=[fan])
    info = FanInfo()
    info.collect(chassis)

    # When the fan is removed and info is collected again
    fan._present = False
    info.collect(chassis)

    # Then the fan moves to the absent set and a presence change is reported
    assert info.get_presence_fans() == set()
    assert info.get_absence_fans() == {fan}
    assert info.is_presence_changed() is True


# --- FanDrawerInfo ----------------------------------------------------------------------

def test_fan_drawer_info_counts_only_present_drawers():
    # Given a chassis with three drawers, one of them absent
    info = FanDrawerInfo()

    # When drawer info is collected
    info.collect(FakeChassis(fans=[FakeFan()],
                             drawers=[FakeDrawer(), FakeDrawer(present=False), FakeDrawer()]))

    # Then only the present drawers are counted, but all drawers and fans are listed
    assert info.get_num_present_fan_drawers() == 2
    assert len(info.get_fan_drawers()) == 3
    assert len(info.get_fans()) == 1


def test_fan_drawer_info_with_no_drawers():
    # Given a chassis with no fan drawers
    info = FanDrawerInfo()

    # When drawer info is collected
    info.collect(FakeChassis())

    # Then no drawers are counted as present
    assert info.get_num_present_fan_drawers() == 0


# --- ThermalInfo ------------------------------------------------------------------------

def test_thermal_info_includes_sfp_thermals():
    # Given a chassis with one thermal of its own and an SFP carrying two more
    info = ThermalInfo()

    # When thermal info is collected
    info.collect(FakeChassis(thermals=[FakeThermal()],
                             sfps=[FakeSfp([FakeThermal(), FakeThermal()])]))

    # Then the SFP thermals are included alongside the chassis one
    assert len(info.get_thermals()) == 3


def test_thermal_info_exposes_the_manager():
    # Given a chassis with a thermal manager
    manager = object()
    info = ThermalInfo()

    # When thermal info is collected
    info.collect(FakeChassis(manager=manager))

    # Then the info hands back that manager
    assert info.get_thermal_manager() is manager


def test_thermal_info_flags_are_clear_when_cool():
    # Given a sensor well below its thresholds
    info = ThermalInfo()

    # When thermal info is collected
    info.collect(FakeChassis(thermals=[FakeThermal(temperature=40.0)]))

    # Then no threshold flag is raised
    assert info.is_over_high_threshold() is False
    assert info.is_over_high_critical_threshold() is False
    assert info.is_over_threshold() is False


def test_thermal_info_flags_high_but_not_critical():
    # Given a sensor between its high and critical thresholds
    info = ThermalInfo()

    # When thermal info is collected
    info.collect(FakeChassis(thermals=[FakeThermal(temperature=85.0)]))

    # Then the high flag is raised but the critical one is not
    assert info.is_over_high_threshold() is True
    assert info.is_over_high_critical_threshold() is False
    assert info.is_over_threshold() is True


def test_thermal_info_flags_critical():
    # Given a sensor above its critical threshold
    info = ThermalInfo()

    # When thermal info is collected
    info.collect(FakeChassis(thermals=[FakeThermal(temperature=99.0)]))

    # Then the critical flag is raised
    assert info.is_over_high_critical_threshold() is True
    assert info.is_over_threshold() is True


def test_thermal_info_ignores_sensors_with_no_reading():
    # Given a sensor that returns no temperature
    info = ThermalInfo()

    # When thermal info is collected
    info.collect(FakeChassis(thermals=[FakeThermal(temperature=None)]))

    # Then it does not raise a threshold flag
    assert info.is_over_threshold() is False


def test_thermal_info_ignores_sensors_with_no_thresholds():
    # Given a very hot sensor that has no thresholds
    info = ThermalInfo()

    # When thermal info is collected
    info.collect(FakeChassis(thermals=[FakeThermal(temperature=200.0, high=None, critical=None)]))

    # Then it does not raise a threshold flag
    assert info.is_over_threshold() is False


def test_thermal_info_clears_flags_when_the_sensor_cools():
    # Given thermal info collected while a sensor is over its critical threshold
    thermal = FakeThermal(temperature=99.0)
    chassis = FakeChassis(thermals=[thermal])
    info = ThermalInfo()
    info.collect(chassis)
    assert info.is_over_threshold() is True

    # When the sensor cools and info is collected again
    thermal._temperature = 40.0
    info.collect(chassis)

    # Then the threshold flag is cleared
    assert info.is_over_threshold() is False


# --- PsuInfo / ChassisInfo --------------------------------------------------------------

def test_psu_info_gathers_presence_thermals_and_fans():
    # Given a present PSU with a thermal and a fan, and an absent PSU
    present = FakePsu(thermals=[FakeThermal()], fans=[FakeFan()])
    absent = FakePsu(present=False)
    info = PsuInfo()

    # When PSU info is collected
    info.collect(FakeChassis(psus=[present, absent]))

    # Then PSUs are split by presence and the PSU thermals and fans are gathered
    assert info.get_presence_psus() == {present}
    assert info.get_absence_psus() == {absent}
    assert info.get_num_present_psus() == 1
    assert len(info.get_thermals()) == 1
    assert len(info.get_fans()) == 1


def test_psu_info_recomputes_presence_each_pass():
    # Given PSU info collected while a PSU is present
    psu = FakePsu()
    chassis = FakeChassis(psus=[psu])
    info = PsuInfo()
    info.collect(chassis)

    # When the PSU is removed and info is collected again
    psu._present = False
    info.collect(chassis)

    # Then the PSU moves to the absent set
    assert info.get_presence_psus() == set()
    assert info.get_absence_psus() == {psu}


def test_chassis_info_returns_the_chassis():
    # Given a chassis
    chassis = FakeChassis()
    info = ChassisInfo()

    # When chassis info is collected
    info.collect(chassis)

    # Then it hands back the same chassis
    assert info.get_chassis() is chassis
