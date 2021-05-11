import os
import sys

# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

from sonic_platform_base.sonic_thermal_control import thermal_manager_base as tmb
from sonic_platform_base.sonic_thermal_control import thermal_info_base
from sonic_platform_base.sonic_thermal_control import thermal_action_base
from sonic_platform_base.sonic_thermal_control import thermal_condition_base
from sonic_platform_base.sonic_thermal_control import thermal_json_object


@thermal_json_object.thermal_json_object('some_info')
class MockThermalInfo(thermal_info_base.ThermalPolicyInfoBase):
    pass


@thermal_json_object.thermal_json_object('action1')
class MockThermalAction1(thermal_action_base.ThermalPolicyActionBase):
    def load_from_json(self, json_obj):
        self.speed = int(json_obj['speed'])


@thermal_json_object.thermal_json_object('action2')
class MockThermalAction2(thermal_action_base.ThermalPolicyActionBase):
    def load_from_json(self, json_obj):
        self.enable = bool(json_obj['enable'])


@thermal_json_object.thermal_json_object('condition1')
class MockThermalCondition1(thermal_condition_base.ThermalPolicyConditionBase):
    pass


@thermal_json_object.thermal_json_object('condition2')
class MockThermalCondition2(thermal_condition_base.ThermalPolicyConditionBase):
    pass


class MockChassis:
    pass


class TestThermalManagerBase:
    @classmethod
    def setup_class(cls):
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        tmb.ThermalManagerBase.load(os.path.join(tests_dir, 'thermal_policy.json'))

    def test_load_policy(self):
        assert tmb.ThermalManagerBase._fan_speed_when_suspend == 60
        assert tmb.ThermalManagerBase._run_thermal_algorithm_at_boot_up

        assert 'some_info' in tmb.ThermalManagerBase._thermal_info_dict
        some_info = tmb.ThermalManagerBase._thermal_info_dict['some_info']
        assert isinstance(some_info, MockThermalInfo)

        assert 'policy1' in tmb.ThermalManagerBase._policy_dict
        assert 'policy2' in tmb.ThermalManagerBase._policy_dict
        policy1 = tmb.ThermalManagerBase._policy_dict['policy1']
        assert MockThermalCondition1 in policy1.conditions
        assert isinstance(policy1.conditions[MockThermalCondition1], MockThermalCondition1)
        assert MockThermalAction1 in policy1.actions
        assert isinstance(policy1.actions[MockThermalAction1], MockThermalAction1)
        policy2 = tmb.ThermalManagerBase._policy_dict['policy2']
        assert MockThermalCondition2 in policy2.conditions
        assert isinstance(policy2.conditions[MockThermalCondition2], MockThermalCondition2)
        assert MockThermalAction2 in policy2.actions
        assert isinstance(policy2.actions[MockThermalAction2], MockThermalAction2)

    def test_run_policy(self):
        MockThermalInfo.collect = mock.MagicMock()
        MockThermalCondition1.is_match = mock.MagicMock(return_value=False)
        MockThermalCondition2.is_match = mock.MagicMock(return_value=True)
        MockThermalAction1.execute = mock.MagicMock()
        MockThermalAction2.execute = mock.MagicMock()
        
        chassis = MockChassis()
        tmb.ThermalManagerBase.run_policy(chassis)
        assert MockThermalInfo.collect.call_count == 1
        assert MockThermalCondition1.is_match.call_count == 1
        assert MockThermalCondition2.is_match.call_count == 1
        assert MockThermalAction1.execute.call_count == 0
        assert MockThermalAction2.execute.call_count == 1

        MockThermalInfo.collect.reset_mock()
        MockThermalCondition1.is_match.reset_mock()
        MockThermalCondition2.is_match.reset_mock()
        tmb.ThermalManagerBase.stop()
        tmb.ThermalManagerBase.run_policy(chassis)
        assert MockThermalInfo.collect.call_count == 0
        assert MockThermalCondition1.is_match.call_count == 0
        assert MockThermalCondition2.is_match.call_count == 0
        
        tmb.ThermalManagerBase._collect_thermal_information = mock.MagicMock()
        tmb.ThermalManagerBase.run_policy(chassis)
        assert MockThermalCondition1.is_match.call_count == 0
        assert MockThermalCondition2.is_match.call_count == 0
