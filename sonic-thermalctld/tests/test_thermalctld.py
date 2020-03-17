import os
import sys
from mock import Mock, MagicMock, patch
from sonic_daemon_base import daemon_base
from .mock_platform import MockChassis, MockFan, MockThermal

daemon_base.db_connect = MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)

from imp import load_source

load_source('thermalctld', scripts_path + '/thermalctld')
from thermalctld import *


def setup_function():
    logger.log_notice = MagicMock()
    logger.log_warning = MagicMock()


def teardown_function():
    logger.log_notice.reset()
    logger.log_warning.reset()


def test_fanstatus_set_presence():
    fan_status = FanStatus()
    ret = fan_status.set_presence(True)
    assert fan_status.presence
    assert not ret

    ret = fan_status.set_presence(False)
    assert not fan_status.presence
    assert ret


def test_fanstatus_set_under_speed():
    fan_status = FanStatus()
    ret = fan_status.set_under_speed(NOT_AVAILABLE, NOT_AVAILABLE, NOT_AVAILABLE)
    assert not ret

    ret = fan_status.set_under_speed(NOT_AVAILABLE, NOT_AVAILABLE, 0)
    assert not ret

    ret = fan_status.set_under_speed(NOT_AVAILABLE, 0, 0)
    assert not ret

    ret = fan_status.set_under_speed(0, 0, 0)
    assert not ret

    ret = fan_status.set_under_speed(80, 100, 19)
    assert ret
    assert fan_status.under_speed
    assert not fan_status.is_ok()

    ret = fan_status.set_under_speed(81, 100, 19)
    assert ret
    assert not fan_status.under_speed
    assert fan_status.is_ok()


def test_fanstatus_set_over_speed():
    fan_status = FanStatus()
    ret = fan_status.set_over_speed(NOT_AVAILABLE, NOT_AVAILABLE, NOT_AVAILABLE)
    assert not ret

    ret = fan_status.set_over_speed(NOT_AVAILABLE, NOT_AVAILABLE, 0)
    assert not ret

    ret = fan_status.set_over_speed(NOT_AVAILABLE, 0, 0)
    assert not ret

    ret = fan_status.set_over_speed(0, 0, 0)
    assert not ret

    ret = fan_status.set_over_speed(120, 100, 19)
    assert ret
    assert fan_status.over_speed
    assert not fan_status.is_ok()

    ret = fan_status.set_over_speed(120, 100, 21)
    assert ret
    assert not fan_status.over_speed
    assert fan_status.is_ok()


def test_fanupdater_fan_absence():
    chassis = MockChassis()
    chassis.make_absence_fan()
    fan_updater = FanUpdater(chassis)
    fan_updater.update()
    fan_list = chassis.get_all_fans()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
    logger.log_warning.assert_called_once()

    fan_list[0].presence = True
    fan_updater.update()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
    logger.log_notice.assert_called_once()


def test_fanupdater_fan_under_speed():
    chassis = MockChassis()
    chassis.make_under_speed_fan()
    fan_updater = FanUpdater(chassis)
    fan_updater.update()
    fan_list = chassis.get_all_fans()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
    logger.log_warning.assert_called_once()

    fan_list[0].make_normal_speed()
    fan_updater.update()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
    logger.log_notice.assert_called_once()


def test_fanupdater_fan_over_speed():
    chassis = MockChassis()
    chassis.make_over_speed_fan()
    fan_updater = FanUpdater(chassis)
    fan_updater.update()
    fan_list = chassis.get_all_fans()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
    logger.log_warning.assert_called_once()

    fan_list[0].make_normal_speed()
    fan_updater.update()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
    logger.log_notice.assert_called_once()


def test_temperature_status_set_over_temper():
    temperatue_status = TemperatureStatus()
    ret = temperatue_status.set_over_temperature(NOT_AVAILABLE, NOT_AVAILABLE)
    assert not ret

    ret = temperatue_status.set_over_temperature(NOT_AVAILABLE, 0)
    assert not ret

    ret = temperatue_status.set_over_temperature(0, NOT_AVAILABLE)
    assert not ret

    ret = temperatue_status.set_over_temperature(2, 1)
    assert ret
    assert temperatue_status.over_temperature

    ret = temperatue_status.set_over_temperature(1, 2)
    assert ret
    assert not temperatue_status.over_temperature


def test_temperstatus_set_under_temper():
    temperature_status = TemperatureStatus()
    ret = temperature_status.set_under_temperature(NOT_AVAILABLE, NOT_AVAILABLE)
    assert not ret

    ret = temperature_status.set_under_temperature(NOT_AVAILABLE, 0)
    assert not ret

    ret = temperature_status.set_under_temperature(0, NOT_AVAILABLE)
    assert not ret

    ret = temperature_status.set_under_temperature(1, 2)
    assert ret
    assert temperature_status.under_temperature

    ret = temperature_status.set_under_temperature(2, 1)
    assert ret
    assert not temperature_status.under_temperature


def test_temperupdater_over_temper():
    chassis = MockChassis()
    chassis.make_over_temper_thermal()
    temperature_updater = TemperatureUpdater(chassis)
    temperature_updater.update()
    thermal_list = chassis.get_all_thermals()
    logger.log_warning.assert_called_once()

    thermal_list[0].make_normal_temper()
    temperature_updater.update()
    logger.log_notice.assert_called_once()


def test_temperupdater_under_temper():
    chassis = MockChassis()
    chassis.make_under_temper_thermal()
    temperature_updater = TemperatureUpdater(chassis)
    temperature_updater.update()
    thermal_list = chassis.get_all_thermals()
    logger.log_warning.assert_called_once()

    thermal_list[0].make_normal_temper()
    temperature_updater.update()
    logger.log_notice.assert_called_once()


def test_update_fan_with_exception():
    chassis = MockChassis()
    chassis.make_error_fan()
    fan = MockFan()
    fan.make_over_speed()
    chassis.get_all_fans().append(fan)

    fan_updater = FanUpdater(chassis)
    fan_updater.update()
    assert fan.get_status_led() == MockFan.STATUS_LED_COLOR_RED
    logger.log_warning.assert_called()


def test_update_thermal_with_exception():
    chassis = MockChassis()
    chassis.make_error_thermal()
    thermal = MockThermal()
    thermal.make_over_temper()
    chassis.get_all_thermals().append(thermal)

    temperature_updater = TemperatureUpdater(chassis)
    temperature_updater.update()
    logger.log_warning.assert_called()
