import os
import sys
import pytest
from mock import MagicMock
from .mock_platform import MockChassis, MockFan

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
sys.path.insert(0, modules_path)

from sonic_platform_base.sonic_thermal_control.thermal_manager_base import ThermalManagerBase
from sonic_platform_base.sonic_thermal_control.thermal_infos import FanInfo, PsuInfo


@pytest.fixture(scope='session', autouse=True)
def thermal_manager():
    policy_file = os.path.join(test_path, 'thermal_policy.json')
    ThermalManagerBase.load(policy_file)

    return ThermalManagerBase


def test_load_policy(thermal_manager):
    assert 'psu_info' in thermal_manager._thermal_info_dict
    assert 'fan_info' in thermal_manager._thermal_info_dict
    assert 'chassis_info' in thermal_manager._thermal_info_dict

    assert 'any fan absence' in thermal_manager._policy_dict
    assert 'any psu absence' in thermal_manager._policy_dict
    assert 'all fan and psu presence' in thermal_manager._policy_dict


def test_fan_info():
    chassis = MockChassis()
    chassis.make_fan_absence()
    fan_info = FanInfo()
    fan_info.collect(chassis)
    assert len(fan_info.get_absence_fans()) == 1
    assert len(fan_info.get_presence_fans()) == 0
    assert fan_info.is_status_changed()

    fan_list = chassis.get_all_fans()
    fan_list[0].presence = True
    fan_info.collect(chassis)
    assert len(fan_info.get_absence_fans()) == 0
    assert len(fan_info.get_presence_fans()) == 1
    assert fan_info.is_status_changed()


def test_psu_info():
    chassis = MockChassis()
    chassis.make_psu_absence()
    psu_info = PsuInfo()
    psu_info.collect(chassis)
    assert len(psu_info.get_absence_psus()) == 1
    assert len(psu_info.get_presence_psus()) == 0
    assert psu_info.is_status_changed()

    psu_list = chassis.get_all_psus()
    psu_list[0].presence = True
    psu_info.collect(chassis)
    assert len(psu_info.get_absence_psus()) == 0
    assert len(psu_info.get_presence_psus()) == 1
    assert psu_info.is_status_changed()


def test_fan_policy(thermal_manager):
    chassis = MockChassis()
    chassis.make_fan_absence()
    chassis.fan_list.append(MockFan())
    thermal_manager.start_thermal_control_algorithm = MagicMock()
    thermal_manager.stop_thermal_control_algorithm = MagicMock()
    thermal_manager.run_policy(chassis)

    fan_list = chassis.get_all_fans()
    assert fan_list[1].speed == 100
    thermal_manager.stop_thermal_control_algorithm.assert_called_once()

    fan_list[0].presence = True
    thermal_manager.run_policy(chassis)
    thermal_manager.start_thermal_control_algorithm.assert_called_once()


def test_psu_policy(thermal_manager):
    chassis = MockChassis()
    chassis.make_psu_absence()
    chassis.fan_list.append(MockFan())
    thermal_manager.start_thermal_control_algorithm = MagicMock()
    thermal_manager.stop_thermal_control_algorithm = MagicMock()
    thermal_manager.run_policy(chassis)

    fan_list = chassis.get_all_fans()
    assert fan_list[0].speed == 100
    thermal_manager.stop_thermal_control_algorithm.assert_called_once()

    psu_list = chassis.get_all_psus()
    psu_list[0].presence = True
    thermal_manager.run_policy(chassis)
    thermal_manager.start_thermal_control_algorithm.assert_called_once()





