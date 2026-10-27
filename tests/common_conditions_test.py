"""Unit tests for sonic_platform_base.sonic_thermal_control.common_conditions."""

import pytest

from sonic_platform_base.sonic_thermal_control.common_conditions import (
    DefaultCondition, FanDrawerPresenceCondition, FanPresenceCondition, OPERATORS,
    PsuPresenceCondition, ThermalOverThresholdCondition)
from sonic_platform_base.sonic_thermal_control.common_infos import (
    FanDrawerInfo, FanInfo, PsuInfo, ThermalInfo)
from sonic_platform_base.sonic_thermal_control.thermal_json_object import ThermalJsonObject


class FakeDrawerInfo:
    def __init__(self, present): self._present = present
    def get_num_present_fan_drawers(self): return self._present


class FakeFanInfo:
    def __init__(self, present): self._present = present
    def get_num_present_fans(self): return self._present


class FakePsuInfo:
    def __init__(self, present): self._present = present
    def get_num_present_psus(self): return self._present


class FakeThermalInfo:
    def __init__(self, high=False, critical=False): self._high, self._critical = high, critical
    def is_over_high_threshold(self): return self._high
    def is_over_high_critical_threshold(self): return self._critical


def drawers(n):
    return {FanDrawerInfo.INFO_NAME: FakeDrawerInfo(n)}


def loaded(cls, **json_obj):
    condition = cls()
    condition.load_from_json(json_obj)
    return condition


# --- registration -----------------------------------------------------------------------

@pytest.mark.parametrize("type_name, cls", [
    ('fandrawer.presence', FanDrawerPresenceCondition),
    ('fan.presence', FanPresenceCondition),
    ('psu.presence', PsuPresenceCondition),
    ('thermal.over.threshold', ThermalOverThresholdCondition),
    ('default.operation', DefaultCondition),
])
def test_condition_is_registered(type_name, cls):
    # Given a condition type name used in policy files
    # When it is looked up in the registry
    registered = ThermalJsonObject.get_type({'type': type_name})

    # Then it resolves to the matching condition class
    assert registered is cls


# --- the whole point: one class replaces nine ---------------------------------------------

@pytest.mark.parametrize("present, expected", [(0, True), (1, True), (2, True), (3, False)])
def test_two_or_fewer_drawers(present, expected):
    # Given a condition for at most two fan drawers
    condition = loaded(FanDrawerPresenceCondition, op='<=', count=2)

    # When it is checked against a given number of present drawers
    matched = condition.is_match(drawers(present))

    # Then it matches only up to two
    assert matched is expected


@pytest.mark.parametrize("count", [1, 2, 3, 4, 5, 6, 7, 8])
def test_exact_count_replaces_the_per_count_classes(count):
    # Given a condition for an exact drawer count
    condition = loaded(FanDrawerPresenceCondition, op='==', count=count)

    # When it is checked against that count and one more
    at_count = condition.is_match(drawers(count))
    one_more = condition.is_match(drawers(count + 1))

    # Then it matches only the exact count
    assert at_count is True
    assert one_more is False


@pytest.mark.parametrize("op", sorted(OPERATORS))
def test_every_operator_is_usable(op):
    # Given a drawer condition using one of the supported operators
    condition = loaded(FanDrawerPresenceCondition, op=op, count=4)

    # When it is checked against an equal and a larger drawer count
    at_four = condition.is_match(drawers(4))
    at_nine = condition.is_match(drawers(9))

    # Then it agrees with the operator itself
    assert at_four is OPERATORS[op](4, 4)
    assert at_nine is OPERATORS[op](9, 4)


def test_zero_present_is_covered():
    # Given a condition for no drawers present
    condition = loaded(FanDrawerPresenceCondition, op='==', count=0)

    # When no drawers are present
    matched = condition.is_match(drawers(0))

    # Then it matches
    assert matched is True


# --- validation -------------------------------------------------------------------------

def test_rejects_unknown_operator():
    # Given an operator the condition does not support
    # When the condition is loaded with it
    # Then it is rejected
    with pytest.raises(ValueError, match='unknown op'):
        loaded(FanDrawerPresenceCondition, op='=<', count=2)


@pytest.mark.parametrize("count", [-1, 1.5, "2", None, True])
def test_rejects_bad_count(count):
    # Given a count that is not a non-negative integer
    # When the condition is loaded with it
    # Then it is rejected
    with pytest.raises(ValueError, match='non-negative integer'):
        loaded(FanDrawerPresenceCondition, op='<=', count=count)


@pytest.mark.parametrize("json_obj", [{'op': '<='}, {'count': 2}, {}])
def test_rejects_missing_fields(json_obj):
    # Given a condition definition missing its op or count
    # When the condition is loaded from it
    # Then it is rejected
    with pytest.raises(ValueError, match='requires'):
        FanDrawerPresenceCondition().load_from_json(json_obj)


def test_unloaded_condition_refuses_to_match():
    # Given a condition that was never loaded from JSON
    # When it is checked
    # Then it is rejected
    with pytest.raises(ValueError, match='not loaded'):
        FanDrawerPresenceCondition().is_match(drawers(1))


def test_missing_info_type_raises_rather_than_silently_not_matching():
    # Given a loaded drawer condition
    condition = loaded(FanDrawerPresenceCondition, op='<=', count=2)

    # When it is checked without fan drawer info collected
    # Then it is rejected with a hint to add the info type
    with pytest.raises(ValueError, match='add it to info_types'):
        condition.is_match({})


# --- other condition types ----------------------------------------------------------------

def test_fan_and_psu_presence():
    # Given a fan condition for no fans and a PSU condition for fewer than two PSUs
    fan_condition = loaded(FanPresenceCondition, op='==', count=0)
    psu_condition = loaded(PsuPresenceCondition, op='<', count=2)

    # When no fans and one PSU are present
    fan_matched = fan_condition.is_match({FanInfo.INFO_NAME: FakeFanInfo(0)})
    psu_matched = psu_condition.is_match({PsuInfo.INFO_NAME: FakePsuInfo(1)})

    # Then both conditions match
    assert fan_matched is True
    assert psu_matched is True


@pytest.mark.parametrize("threshold, high, critical, expected", [
    ('high', True, False, True),
    ('high', False, True, False),
    ('high_critical', False, True, True),
    ('high_critical', True, False, False),
])
def test_thermal_over_threshold(threshold, high, critical, expected):
    # Given a condition on one threshold level and thermal info with some flags raised
    condition = loaded(ThermalOverThresholdCondition, threshold=threshold)
    info = {ThermalInfo.INFO_NAME: FakeThermalInfo(high=high, critical=critical)}

    # When the condition is checked
    matched = condition.is_match(info)

    # Then it matches only when its own threshold's flag is raised
    assert matched is expected


def test_threshold_defaults_to_high_not_critical():
    # Given a threshold condition with no threshold set, and only the high flag raised
    condition = loaded(ThermalOverThresholdCondition)
    info = {ThermalInfo.INFO_NAME: FakeThermalInfo(high=True, critical=False)}

    # When the condition is checked
    matched = condition.is_match(info)

    # Then it matches, because it watches the high threshold by default
    assert matched is True


def test_rejects_unknown_threshold():
    # Given a threshold name the condition does not know
    # When the condition is loaded with it
    # Then it is rejected
    with pytest.raises(ValueError, match='unknown threshold'):
        loaded(ThermalOverThresholdCondition, threshold='toasty')


def test_thermal_condition_needs_its_info_type():
    # Given a threshold condition
    # When it is checked without thermal info collected
    # Then it is rejected with a hint to add the info type
    with pytest.raises(ValueError, match='add it to info_types'):
        loaded(ThermalOverThresholdCondition).is_match({})


def test_default_condition_always_matches():
    # Given the default condition
    # When it is checked with no info and with drawer info
    with_nothing = DefaultCondition().is_match({})
    with_drawers = DefaultCondition().is_match(drawers(0))

    # Then it matches both times
    assert with_nothing is True
    assert with_drawers is True


# --- equality, which the policy manager relies on to spot duplicate policies -------------

def _load(cls, json_obj):
    condition = cls()
    condition.load_from_json(json_obj)
    return condition


def test_presence_condition_differs_from_another_type_with_the_same_parameters():
    # Given a drawer condition and a PSU condition with the same op and count
    drawers = _load(FanDrawerPresenceCondition, {"op": "<=", "count": 2})
    psus = _load(PsuPresenceCondition, {"op": "<=", "count": 2})

    # When they are compared
    # Then they are not equal
    assert drawers != psus


def test_equal_presence_conditions_hash_alike():
    # Given two drawer conditions with identical parameters
    first = _load(FanDrawerPresenceCondition, {"op": "<=", "count": 2})
    second = _load(FanDrawerPresenceCondition, {"op": "<=", "count": 2})

    # When they are compared and put in a set
    # Then they are equal and collapse to one entry
    assert first == second
    assert len({first, second}) == 1


def test_threshold_conditions_compare_by_threshold():
    # Given an explicit high, a defaulted high and a critical threshold condition
    high = _load(ThermalOverThresholdCondition, {"threshold": "high"})
    also_high = _load(ThermalOverThresholdCondition, {})
    critical = _load(ThermalOverThresholdCondition, {"threshold": "high_critical"})

    # When they are compared and put in a set
    # Then the two high conditions are equal and the critical one stands apart
    assert high == also_high
    assert high != critical
    assert len({high, also_high, critical}) == 2


def test_threshold_condition_differs_from_another_type():
    # Given a threshold condition and the default condition
    threshold = _load(ThermalOverThresholdCondition, {})
    default = DefaultCondition()

    # When they are compared
    # Then they are not equal
    assert threshold != default
