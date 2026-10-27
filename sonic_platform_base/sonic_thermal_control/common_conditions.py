"""
Thermal policy conditions shared by platforms.

Platforms currently declare one class per count - fandrawer.one.present through
fandrawer.eight.present and so on - which cannot express "two or fewer" without yet another
class. These take the count and comparison from the policy file instead, so one type covers
every case.

Importing this module registers the types below; see common_infos for why that is opt-in.
"""

import operator

from .common_infos import FanDrawerInfo, FanInfo, PsuInfo, ThermalInfo
from .thermal_condition_base import ThermalPolicyConditionBase
from .thermal_json_object import thermal_json_object

OPERATORS = {
    '<': operator.lt,
    '<=': operator.le,
    '==': operator.eq,
    '!=': operator.ne,
    '>=': operator.ge,
    '>': operator.gt,
}

JSON_FIELD_OP = 'op'
JSON_FIELD_COUNT = 'count'
JSON_FIELD_THRESHOLD = 'threshold'

THRESHOLD_HIGH = 'high'
THRESHOLD_HIGH_CRITICAL = 'high_critical'


def _require_info(thermal_info_dict, info_class, owner):
    info = thermal_info_dict.get(info_class.INFO_NAME)
    if info is None:
        # The policy references an info type it never declared in info_types. Returning
        # False would quietly disable whatever policy this guards, which for a
        # degraded-cooling condition means fans never ramp.
        raise ValueError('{}: {} not collected; add it to info_types'.format(
            owner, info_class.INFO_NAME))
    return info


class ParameterisedCondition(ThermalPolicyConditionBase):
    """
    A condition whose identity includes its parameters, not just its type.

    The base class compares by type alone, which was sufficient when each count had its own
    class. One parameterised class means the comparison has to include the parameters, or
    the manager reads two policies guarded by different counts as duplicates and rejects the
    whole file.
    """

    def _params(self):
        raise NotImplementedError

    def __eq__(self, other):
        if type(self) is not type(other):
            return False
        return self._params() == other._params()

    def __hash__(self):
        return hash((type(self), self._params()))


class PresenceConditionBase(ParameterisedCondition):
    """Compares how many of something is present against a count from the policy file."""

    INFO_CLASS = None

    def __init__(self):
        self._op = None
        self._op_name = None
        self._count = None

    def load_from_json(self, json_obj):
        try:
            op_name = json_obj[JSON_FIELD_OP]
            count = json_obj[JSON_FIELD_COUNT]
        except KeyError:
            raise ValueError('{} requires {} and {}'.format(
                type(self).__name__, JSON_FIELD_OP, JSON_FIELD_COUNT)) from None

        if op_name not in OPERATORS:
            raise ValueError('{}: unknown {} {!r}, expected one of {}'.format(
                type(self).__name__, JSON_FIELD_OP, op_name, sorted(OPERATORS)))
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError('{}: {} must be a non-negative integer, got {!r}'.format(
                type(self).__name__, JSON_FIELD_COUNT, count))

        self._op_name = op_name
        self._op = OPERATORS[op_name]
        self._count = count

    def get_info(self, thermal_info_dict):
        return _require_info(thermal_info_dict, self.INFO_CLASS, type(self).__name__)

    def get_count(self, thermal_info_dict):
        raise NotImplementedError

    def is_match(self, thermal_info_dict):
        if self._op is None:
            raise ValueError('{} was not loaded from JSON'.format(type(self).__name__))
        return self._op(self.get_count(thermal_info_dict), self._count)

    def _params(self):
        return self._op_name, self._count


@thermal_json_object('fandrawer.presence')
class FanDrawerPresenceCondition(PresenceConditionBase):
    """e.g. {"type": "fandrawer.presence", "op": "<=", "count": 2}"""

    INFO_CLASS = FanDrawerInfo

    def get_count(self, thermal_info_dict):
        return self.get_info(thermal_info_dict).get_num_present_fan_drawers()


@thermal_json_object('fan.presence')
class FanPresenceCondition(PresenceConditionBase):
    """e.g. {"type": "fan.presence", "op": "==", "count": 0}"""

    INFO_CLASS = FanInfo

    def get_count(self, thermal_info_dict):
        return self.get_info(thermal_info_dict).get_num_present_fans()


@thermal_json_object('psu.presence')
class PsuPresenceCondition(PresenceConditionBase):
    """e.g. {"type": "psu.presence", "op": "<", "count": 2}"""

    INFO_CLASS = PsuInfo

    def get_count(self, thermal_info_dict):
        return self.get_info(thermal_info_dict).get_num_present_psus()


@thermal_json_object('thermal.over.threshold')
class ThermalOverThresholdCondition(ParameterisedCondition):
    """
    e.g. {"type": "thermal.over.threshold", "threshold": "high_critical"}

    Defaults to the high threshold, the less severe of the two, so an omitted field cannot
    silently arm a shutdown policy.
    """

    def __init__(self):
        self._threshold = THRESHOLD_HIGH

    def load_from_json(self, json_obj):
        threshold = json_obj.get(JSON_FIELD_THRESHOLD, THRESHOLD_HIGH)
        if threshold not in (THRESHOLD_HIGH, THRESHOLD_HIGH_CRITICAL):
            raise ValueError('{}: unknown {} {!r}, expected {!r} or {!r}'.format(
                type(self).__name__, JSON_FIELD_THRESHOLD, threshold,
                THRESHOLD_HIGH, THRESHOLD_HIGH_CRITICAL))
        self._threshold = threshold

    def is_match(self, thermal_info_dict):
        info = _require_info(thermal_info_dict, ThermalInfo, type(self).__name__)
        if self._threshold == THRESHOLD_HIGH_CRITICAL:
            return info.is_over_high_critical_threshold()
        return info.is_over_high_threshold()

    def _params(self):
        return (self._threshold,)


@thermal_json_object('default.operation')
class DefaultCondition(ThermalPolicyConditionBase):
    """Always matches, for the policy that runs when nothing more specific applies."""

    def is_match(self, thermal_info_dict):
        return True
