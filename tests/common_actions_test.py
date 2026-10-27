"""Unit tests for sonic_platform_base.sonic_thermal_control.common_actions."""

import pytest

from sonic_platform_base.sonic_thermal_control import common_actions
from sonic_platform_base.sonic_thermal_control.common_actions import (
    FanControlError, SetFanSpeedAction, ThermalControlAlgorithmAction, get_fans,
    set_all_fan_speeds)
from sonic_platform_base.sonic_thermal_control.common_infos import (
    FanDrawerInfo, FanInfo, ThermalInfo)
from sonic_platform_base.sonic_thermal_control.thermal_json_object import ThermalJsonObject
from sonic_platform_base.thermal_base import ThermalBase

CONFIG = {
    "fan_limits": {"min": 30, "max": 100},
    "pid_domains": {"asic": {"KP": 10, "KI": 0.1, "KD": 5}},
}


class FakeFan:
    """Only the FanBase API that the actions use."""

    def __init__(self, accepts=True, raises=False):
        self.speed = None
        self._accepts, self._raises = accepts, raises

    def set_speed(self, speed):
        if self._raises:
            raise RuntimeError("i2c timeout")
        self.speed = speed
        return self._accepts


class FakeThermal:
    """A PID-controlled thermal; domain=None makes it one the PID must ignore."""

    def __init__(self, temperature=40.0, setpoint=80.0, domain='asic', name='t'):
        self._temperature, self._setpoint = temperature, setpoint
        self._domain, self._name = domain, name

    def get_temperature(self): return self._temperature
    def get_pid_setpoint(self): return self._setpoint
    def get_pid_domain(self): return self._domain
    def get_name(self): return self._name


class FakeManager:
    def __init__(self, interval=5): self._interval = interval
    def get_interval(self): return self._interval


class FakeDrawerInfo:
    def __init__(self, fans): self._fans = fans
    def get_fans(self): return self._fans


class FakeFanInfo:
    def __init__(self, fans): self._fans = set(fans)
    def get_presence_fans(self): return self._fans


class FakeThermalInfo:
    def __init__(self, thermals, manager=None):
        self._thermals, self._manager = thermals, manager or FakeManager()
    def get_thermals(self): return self._thermals
    def get_thermal_manager(self): return self._manager


def info_dict(fans=None, thermals=None, use_fan_info=False):
    d = {}
    if fans is not None:
        key = FanInfo.INFO_NAME if use_fan_info else FanDrawerInfo.INFO_NAME
        d[key] = FakeFanInfo(fans) if use_fan_info else FakeDrawerInfo(fans)
    if thermals is not None:
        d[ThermalInfo.INFO_NAME] = FakeThermalInfo(thermals)
    return d


@pytest.fixture
def algo(monkeypatch):
    monkeypatch.setattr(common_actions, 'load_thermal_config', lambda *a, **k: CONFIG)
    action = ThermalControlAlgorithmAction()
    action.load_from_json({})
    return action


# --- registration -----------------------------------------------------------------------

@pytest.mark.parametrize("type_name, cls", [
    ('fan.all.set_speed', SetFanSpeedAction),
    ('thermal.control_algo', ThermalControlAlgorithmAction),
])
def test_action_is_registered(type_name, cls):
    # Given an action type name used in policy files
    # When it is looked up in the registry
    registered = ThermalJsonObject.get_type({'type': type_name})

    # Then it resolves to the matching action class
    assert registered is cls


# --- fan source -------------------------------------------------------------------------

def test_prefers_fan_drawer_info():
    # Given fans collected through fan drawer info
    fan = FakeFan()

    # When the fans are looked up
    found = get_fans(info_dict(fans=[fan]))

    # Then they come from the drawer info
    assert found == [fan]


def test_falls_back_to_fan_info():
    # Given fans collected only through fan info
    fan = FakeFan()

    # When the fans are looked up
    found = get_fans(info_dict(fans=[fan], use_fan_info=True))

    # Then they come from the fan info
    assert found == [fan]


def test_raises_when_no_fan_info_collected():
    # Given no fan or drawer info was collected
    # When the fans are looked up
    # Then it is rejected with a hint to add an info type
    with pytest.raises(FanControlError, match='add one to info_types'):
        get_fans({})


# --- set_all_fan_speeds -----------------------------------------------------------------

def test_sets_every_fan():
    # Given two working fans
    fans = [FakeFan(), FakeFan()]

    # When all fan speeds are set
    set_all_fan_speeds(fans, 55)

    # Then every fan runs at that speed
    assert [f.speed for f in fans] == [55, 55]


def test_one_failing_fan_does_not_stop_the_others():
    # Given a fan that raises on write ahead of a working one
    good, bad = FakeFan(), FakeFan(raises=True)

    # When all fan speeds are set
    set_all_fan_speeds([bad, good], 70)

    # Then the working fan is still set
    assert good.speed == 70


def test_raises_when_no_fan_accepts():
    # Given a fan that refuses every speed write
    # When all fan speeds are set
    # Then it is rejected
    with pytest.raises(FanControlError, match='no fan accepted'):
        set_all_fan_speeds([FakeFan(accepts=False)], 70)


def test_raises_on_empty_fan_list():
    # Given no fans at all
    # When all fan speeds are set
    # Then it is rejected
    with pytest.raises(FanControlError, match='no fans available'):
        set_all_fan_speeds([], 70)


# --- simple actions ---------------------------------------------------------------------

def test_set_speed_action():
    # Given a set-speed action for 100% and one fan
    action = SetFanSpeedAction()
    action.load_from_json({'speed': 100})
    fans = [FakeFan()]

    # When the action runs
    action.execute(info_dict(fans=fans))

    # Then the fan is driven to 100%
    assert fans[0].speed == 100


@pytest.mark.parametrize("speed", [-1, 101, "fast", None])
def test_set_speed_rejects_bad_values(speed):
    # Given a speed outside 0-100 or not a number
    # When a set-speed action is loaded with it
    # Then it is rejected
    with pytest.raises(ValueError):
        SetFanSpeedAction().load_from_json({'speed': speed})


def test_set_speed_requires_the_field():
    # Given a set-speed definition with no speed
    # When the action is loaded from it
    # Then it is rejected
    with pytest.raises(ValueError, match='missing speed'):
        SetFanSpeedAction().load_from_json({})


# --- PID control algorithm ----------------------------------------------------------------

def test_missing_config_degrades_to_max_instead_of_refusing_to_load(monkeypatch):
    """
    Raising here would abort the whole policy file and leave the daemon running with no
    policies - outwardly healthy and not cooling. It must load and hold the fans up.
    """
    # Given no thermal_config.json on the platform
    monkeypatch.setattr(common_actions, 'load_thermal_config', lambda *a, **k: {})

    # When the control action is loaded and run
    action = ThermalControlAlgorithmAction()
    action.load_from_json({})            # must not raise
    fans = [FakeFan()]
    action.execute(info_dict(fans=fans, thermals=[FakeThermal()]))

    # Then it loads and holds the fans at full speed
    assert fans[0].speed == 100


def test_missing_config_still_drives_fans_when_thermal_info_is_absent(monkeypatch):
    # Given no thermal_config.json and a loaded control action
    monkeypatch.setattr(common_actions, 'load_thermal_config', lambda *a, **k: {})
    action = ThermalControlAlgorithmAction()
    action.load_from_json({})
    fans = [FakeFan()]

    # When it runs without any thermal info
    action.execute(info_dict(fans=fans))   # no thermal_info at all

    # Then it still drives the fans to full speed
    assert fans[0].speed == 100


def test_cool_switch_settles_at_the_minimum(algo):
    # Given a sensor well below its target
    fans = [FakeFan()]

    # When the PID action runs
    algo.execute(info_dict(fans=fans, thermals=[FakeThermal(temperature=40.0, setpoint=80.0)]))

    # Then the fans sit at the configured minimum
    assert fans[0].speed == 30


def test_hot_switch_drives_fans_up(algo):
    # Given a sensor above its target
    fans = [FakeFan()]

    # When the PID action runs
    algo.execute(info_dict(fans=fans, thermals=[FakeThermal(temperature=95.0, setpoint=80.0)]))

    # Then the fans rise above the minimum
    assert fans[0].speed > 30


def test_ramp_converges_without_windup(algo):
    """A sustained overshoot then a return to target must come back down, not stay pinned."""
    # Given a switch that has run hot for a while
    fans = [FakeFan()]
    thermal = FakeThermal(temperature=95.0, setpoint=80.0)
    d = info_dict(fans=fans, thermals=[thermal])
    for _ in range(20):
        algo.execute(d)
    hot_speed = fans[0].speed

    # When it cools below target and the action keeps running
    thermal._temperature = 60.0
    for _ in range(40):
        algo.execute(d)

    # Then the fans come all the way back down to the minimum
    assert fans[0].speed < hot_speed
    assert fans[0].speed == 30


def test_config_setpoint_overrides_the_sensor(monkeypatch):
    # Given a config that sets a 50C target for the asic domain
    config = dict(CONFIG)
    config['pid_domains'] = {"asic": {"KP": 10, "KI": 0.1, "KD": 5, "setpoint": 50}}
    monkeypatch.setattr(common_actions, 'load_thermal_config', lambda *a, **k: config)
    action = ThermalControlAlgorithmAction()
    action.load_from_json({})
    fans = [FakeFan()]

    # When a 70C sensor, under its own 80C target but over the configured 50C one, is seen
    action.execute(info_dict(fans=fans, thermals=[FakeThermal(temperature=70.0, setpoint=80.0)]))

    # Then the configured target wins and the fans rise
    assert fans[0].speed > 30


def test_skips_thermals_not_under_pid_control(algo):
    # Given a hot sensor that is not under PID control
    fans = [FakeFan()]
    hot_but_excluded = FakeThermal(temperature=150.0, setpoint=80.0, domain=None)

    # When the PID action runs
    algo.execute(info_dict(fans=fans, thermals=[hot_but_excluded]))

    # Then it fails safe to full speed
    assert fans[0].speed == 100  # no usable domain -> fail-safe


def test_failure_falls_back_to_max_speed_without_raising(algo):
    # Given no thermal info was collected
    fans = [FakeFan()]

    # When the PID action runs
    algo.execute(info_dict(fans=fans))  # thermal_info missing

    # Then it drives the fans to full speed instead of raising
    assert fans[0].speed == 100


def test_sensor_without_a_reading_is_ignored(algo):
    # Given one sensor with no reading and one above its target
    fans = [FakeFan()]

    # When the PID action runs
    algo.execute(info_dict(fans=fans, thermals=[
        FakeThermal(temperature=None), FakeThermal(temperature=95.0, setpoint=80.0)]))

    # Then it controls on the readable sensor and the fans rise
    assert fans[0].speed > 30


def test_config_dir_can_be_overridden(tmp_path):
    """Lets the action be exercised off a switch, where the platform dir does not exist."""
    # Given a valid config in a directory of our choosing
    import json
    from sonic_platform_base.sonic_thermal_control import thermal_config
    (tmp_path / thermal_config.CONFIG_FILE_NAME).write_text(json.dumps(CONFIG))

    # When the action is pointed at it and run against a hot sensor
    action = ThermalControlAlgorithmAction()
    action.load_from_json({'config_dir': str(tmp_path)})
    fans = [FakeFan()]
    action.execute(info_dict(fans=fans, thermals=[FakeThermal(temperature=95.0, setpoint=80.0)]))

    # Then it runs the PID from that config and the fans rise
    assert fans[0].speed > 30


def test_fail_safe_that_cannot_find_fans_raises(algo):
    # Given neither fan info nor thermal info was collected
    # When the PID action runs
    # Then its fail-safe cannot reach any fan either, so the error is raised for the
    # thermal manager's own fail-safe to handle
    with pytest.raises(FanControlError):
        algo.execute({})  # no fan info and no thermal info


# --- the policy's max_speed ceiling ----------------------------------------------------------

def load_algo(monkeypatch, json_obj, config=CONFIG):
    monkeypatch.setattr(common_actions, 'load_thermal_config', lambda *a, **k: config)
    action = ThermalControlAlgorithmAction()
    action.load_from_json(json_obj)
    return action


def test_max_speed_caps_the_pid_output(monkeypatch):
    # Given a control action with a 75% ceiling and a very hot sensor
    action = load_algo(monkeypatch, {'max_speed': 75})
    fans = [FakeFan()]

    # When the PID action runs
    action.execute(info_dict(fans=fans, thermals=[FakeThermal(temperature=150.0, setpoint=80.0)]))

    # Then the fans stop at the ceiling
    assert fans[0].speed == 75


def test_absent_max_speed_uses_the_configured_fan_max(monkeypatch):
    # Given a control action without max_speed and a config allowing up to 90%
    config = dict(CONFIG, fan_limits={"min": 30, "max": 90})
    action = load_algo(monkeypatch, {}, config)
    fans = [FakeFan()]

    # When the PID action runs against a very hot sensor
    action.execute(info_dict(fans=fans, thermals=[FakeThermal(temperature=150.0, setpoint=80.0)]))

    # Then the fans go up to the configured maximum
    assert fans[0].speed == 90


def test_max_speed_above_the_fan_max_is_held_to_the_fan_max(monkeypatch):
    # Given a 95% ceiling in the policy and a config allowing up to 90%
    config = dict(CONFIG, fan_limits={"min": 30, "max": 90})
    action = load_algo(monkeypatch, {'max_speed': 95}, config)
    fans = [FakeFan()]

    # When the PID action runs against a very hot sensor
    action.execute(info_dict(fans=fans, thermals=[FakeThermal(temperature=150.0, setpoint=80.0)]))

    # Then the configured maximum wins
    assert fans[0].speed == 90


def test_max_speed_below_the_fan_min_is_rejected(monkeypatch):
    # Given a config with a 30% minimum
    # When a control action with a 20% ceiling is loaded
    # Then it is rejected, naming both values
    with pytest.raises(ValueError, match='max_speed 20.0 is below the fan minimum 30'):
        load_algo(monkeypatch, {'max_speed': 20})


@pytest.mark.parametrize("max_speed", [-1, 101, "fast", None])
def test_max_speed_rejects_bad_values(monkeypatch, max_speed):
    # Given a max_speed outside 0-100 or not a number
    # When a control action is loaded with it
    # Then it is rejected
    with pytest.raises(ValueError, match='max_speed'):
        load_algo(monkeypatch, {'max_speed': max_speed})


def test_fail_safe_ignores_max_speed(monkeypatch):
    # Given a control action with a 75% ceiling and no thermal info
    action = load_algo(monkeypatch, {'max_speed': 75})
    fans = [FakeFan()]

    # When the PID action runs and fails safe
    action.execute(info_dict(fans=fans))  # thermal_info missing

    # Then the fans go to the configured maximum, not the ceiling
    assert fans[0].speed == 100


# --- PID hooks on ThermalBase ------------------------------------------------------------

class PlainThermal(ThermalBase):
    """A vendor thermal that never heard of the PID hooks."""

    def __init__(self, temperature):
        self._temperature = temperature

    def get_name(self): return 'plain'
    def get_temperature(self): return self._temperature


class PidThermal(PlainThermal):
    """A vendor thermal that opts in by overriding the two ThermalBase hooks."""

    def get_pid_domain(self): return 'asic'
    def get_pid_setpoint(self): return 80.0


def test_thermal_base_hooks_default_to_none():
    # Given a ThermalBase subclass that does not override the PID hooks
    thermal = PlainThermal(temperature=40.0)

    # When its PID domain and setpoint are read
    # Then both are None
    assert thermal.get_pid_domain() is None
    assert thermal.get_pid_setpoint() is None


def test_thermal_without_a_pid_domain_is_ignored_quietly(algo, caplog):
    # Given a hot thermal that does not override the hooks, next to a cool PID thermal
    caplog.set_level("INFO")
    fans = [FakeFan()]
    thermals = [PlainThermal(temperature=150.0), PidThermal(temperature=40.0)]

    # When the PID action runs
    algo.execute(info_dict(fans=fans, thermals=thermals))

    # Then only the PID thermal counts, and nothing is warned about the other one
    assert fans[0].speed == 30
    assert "WARNING" not in caplog.text


def test_thermal_overriding_only_the_base_hooks_is_controlled(algo):
    # Given a thermal 2C over its target that overrides get_pid_domain and
    # get_pid_setpoint only
    fans = [FakeFan()]

    # When the PID action runs
    algo.execute(info_dict(fans=fans, thermals=[PidThermal(temperature=82.0)]))

    # Then the PID sets a speed between the limits rather than failing safe to the maximum
    assert 30 < fans[0].speed < 100
