"""
Loading a real multi-policy file through ThermalManagerBase.

The per-condition tests exercise conditions in isolation, which is not enough: the manager
rejects two policies whose conditions compare equal, and the base class compares conditions
by type alone. A single parameterised condition class therefore has to define equality
itself. These tests load whole policy files the way thermalctld does.
"""

import json
import os

import pytest

from sonic_platform_base.sonic_thermal_control import (   # noqa: F401  (registers types)
    common_actions, common_conditions, common_infos)
from sonic_platform_base.sonic_thermal_control.common_conditions import (
    FanDrawerPresenceCondition, ThermalOverThresholdCondition)
from sonic_platform_base.sonic_thermal_control.thermal_config import (
    get_domain_setpoint, get_pid_domains, load_thermal_config)
from sonic_platform_base.sonic_thermal_control.thermal_manager_base import ThermalManagerBase


class Manager(ThermalManagerBase):
    pass


def load(tmp_path, policies):
    Manager._policy_dict = {}
    Manager._thermal_info_dict = {}
    path = tmp_path / "thermal_policy.json"
    path.write_text(json.dumps({
        "interval": 5,
        "info_types": [{"type": "fan_drawer_info"}, {"type": "thermal_info"}],
        "policies": policies,
    }))
    Manager.load(str(path))
    return Manager


def drawer_policy(name, op, count, speed):
    return {"name": name,
            "conditions": [{"type": "fandrawer.presence", "op": op, "count": count}],
            "actions": [{"type": "fan.all.set_speed", "speed": speed}]}


def test_graduated_policy_loads(tmp_path):
    """The shape this platform actually ships: one policy per drawer count."""
    # Given a policy file with one policy per drawer count plus a range policy
    # When the manager loads it
    manager = load(tmp_path, [
        drawer_policy("One fan drawer present", "==", 1, 100),
        drawer_policy("Two fan drawers present", "==", 2, 95),
        drawer_policy("Three fan drawers present", "==", 3, 80),
        drawer_policy("Four fan drawers present", "==", 4, 75),
        drawer_policy("More than two", ">", 2, 50),
    ])

    # Then every policy is kept
    assert len(manager._policy_dict) == 5


def test_same_count_different_operator_is_not_a_duplicate(tmp_path):
    # Given two policies on the same drawer count but different operators
    # When the manager loads them
    manager = load(tmp_path, [drawer_policy("at most two", "<=", 2, 100),
                              drawer_policy("exactly two", "==", 2, 95)])

    # Then both are kept
    assert len(manager._policy_dict) == 2


def test_genuinely_identical_conditions_are_still_rejected(tmp_path):
    """The duplicate check must keep working - two policies cannot guard on the same thing."""
    # Given two policies with identical conditions
    # When the manager loads them
    # Then it is rejected as a duplicate
    with pytest.raises(Exception, match="duplicate conditions"):
        load(tmp_path, [drawer_policy("first", "==", 2, 100),
                        drawer_policy("second", "==", 2, 95)])


def test_threshold_conditions_differ_by_threshold(tmp_path):
    # Given a high-threshold policy and a critical-threshold policy
    # When the manager loads them
    manager = load(tmp_path, [
        {"name": "high", "conditions": [{"type": "thermal.over.threshold",
                                         "threshold": "high"}],
         "actions": [{"type": "fan.all.set_speed", "speed": 80}]},
        {"name": "critical", "conditions": [{"type": "thermal.over.threshold",
                                             "threshold": "high_critical"}],
         "actions": [{"type": "fan.all.set_speed", "speed": 100}]},
    ])

    # Then both are kept
    assert len(manager._policy_dict) == 2


# --- the equality contract the manager depends on --------------------------------------

def make(cls, **json_obj):
    obj = cls()
    obj.load_from_json(json_obj)
    return obj


def test_equality_distinguishes_count():
    # Given two drawer conditions that differ only in count
    # When they are compared
    # Then they are not equal
    assert make(FanDrawerPresenceCondition, op="==", count=1) != \
           make(FanDrawerPresenceCondition, op="==", count=2)


def test_equality_distinguishes_operator():
    # Given two drawer conditions that differ only in operator
    # When they are compared
    # Then they are not equal
    assert make(FanDrawerPresenceCondition, op="<=", count=2) != \
           make(FanDrawerPresenceCondition, op="==", count=2)


def test_equality_matches_on_identical_parameters():
    # Given two drawer conditions with identical parameters
    a = make(FanDrawerPresenceCondition, op="<=", count=2)
    b = make(FanDrawerPresenceCondition, op="<=", count=2)

    # When they are compared and hashed
    # Then they are equal and hash alike
    assert a == b and hash(a) == hash(b)


def test_threshold_equality():
    # Given threshold conditions on the same and on different thresholds
    # When they are compared
    # Then only those on the same threshold are equal
    assert make(ThermalOverThresholdCondition, threshold="high") != \
           make(ThermalOverThresholdCondition, threshold="high_critical")
    assert make(ThermalOverThresholdCondition, threshold="high") == \
           make(ThermalOverThresholdCondition, threshold="high")


def test_policy_loads_even_when_the_thermal_config_is_missing(tmp_path, monkeypatch):
    """
    On hardware a missing thermal_config.json aborted thermal manager init, so thermalctld
    ran with no policies at all: RUNNING, fans at their last value, nothing cooling. The
    policy must still load so the control action can hold the fans up instead.
    """
    # Given no thermal_config.json on the platform
    from sonic_platform_base.sonic_thermal_control import common_actions
    monkeypatch.setattr(common_actions, 'load_thermal_config', lambda *a, **k: {})

    # When a policy file using the control action is loaded
    manager = load(tmp_path, [
        drawer_policy("One fan drawer present", "==", 1, 100),
        {"name": "thermal control algorithm",
         "conditions": [{"type": "fandrawer.presence", "op": ">", "count": 2}],
         "actions": [{"type": "thermal.control_algo"}]},
    ])

    # Then every policy still loads
    assert len(manager._policy_dict) == 2


# --- the shipped examples ---------------------------------------------------------------

EXAMPLES_DIR = os.path.join(os.path.dirname(common_actions.__file__), "examples")


def test_example_config_is_valid():
    # Given the example thermal_config.json
    # When it is loaded and validated
    config = load_thermal_config(EXAMPLES_DIR)

    # Then both PID groups are configured, and only board has a group-wide target
    assert set(get_pid_domains(config)) == {"asic", "board"}
    assert get_domain_setpoint(config, "board") == 70
    assert get_domain_setpoint(config, "asic") is None


def test_example_policy_loads_with_the_example_config(monkeypatch):
    # Given the example policy file, with the control action reading the example config
    real_load = common_actions.load_thermal_config
    monkeypatch.setattr(common_actions, "load_thermal_config",
                        lambda config_dir=None: real_load(EXAMPLES_DIR))
    Manager._policy_dict = {}
    Manager._thermal_info_dict = {}

    # When the manager loads it the way thermalctld does
    Manager.load(os.path.join(EXAMPLES_DIR, "thermal_policy.json"))

    # Then both policies load and the PID action is fully configured, not in fail-safe mode,
    # with the policy's 75% ceiling
    assert len(Manager._policy_dict) == 2
    pid_policy = Manager._policy_dict["normal operation: PID"]
    algo = next(a for a in pid_policy.actions.values()
                if isinstance(a, common_actions.ThermalControlAlgorithmAction))
    assert algo._degraded is None
    assert algo._max_speed == 75


def test_policy_with_an_unknown_action_type_fails_to_load(tmp_path):
    # Given a policy with an action type that is not registered
    # When the manager loads it
    # Then it is rejected, naming the unknown type
    with pytest.raises(Exception, match='type fan.no_such_action not found'):
        load(tmp_path, [
            {"name": "normal",
             "conditions": [{"type": "fandrawer.presence", "op": ">", "count": 2}],
             "actions": [{"type": "fan.no_such_action"},
                         {"type": "thermal.control_algo"}]},
        ])
