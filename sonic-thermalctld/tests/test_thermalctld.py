import os
import sys
from imp import load_source

from mock import Mock, MagicMock, patch
from sonic_py_common import daemon_base

from .mock_platform import MockChassis, MockFan, MockThermal

SYSLOG_IDENTIFIER = 'thermalctld_test'
NOT_AVAILABLE = 'N/A'

daemon_base.db_connect = MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)

os.environ["THERMALCTLD_UNIT_TESTING"] = "1"
load_source('thermalctld', scripts_path + '/thermalctld')
from thermalctld import *


TEMPER_INFO_TABLE_NAME = 'TEMPERATURE_INFO'

def setup_function():
    FanStatus.log_notice = MagicMock()
    FanStatus.log_warning = MagicMock()
    FanUpdater.log_notice = MagicMock()
    FanUpdater.log_warning = MagicMock()
    TemperatureStatus.log_notice = MagicMock()
    TemperatureStatus.log_warning = MagicMock()
    TemperatureUpdater.log_notice = MagicMock()
    TemperatureUpdater.log_warning = MagicMock()


def teardown_function():
    FanStatus.log_notice.reset()
    FanStatus.log_warning.reset()
    FanUpdater.log_notice.reset()
    FanUpdater.log_notice.reset()
    TemperatureStatus.log_notice.reset()
    TemperatureStatus.log_warning.reset()
    TemperatureUpdater.log_warning.reset()
    TemperatureUpdater.log_warning.reset()


def test_fanstatus_set_presence():
    fan_status = FanStatus(SYSLOG_IDENTIFIER)
    ret = fan_status.set_presence(True)
    assert fan_status.presence
    assert not ret

    ret = fan_status.set_presence(False)
    assert not fan_status.presence
    assert ret


def test_fanstatus_set_under_speed():
    fan_status = FanStatus(SYSLOG_IDENTIFIER)
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
    fan_status = FanStatus(SYSLOG_IDENTIFIER)
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
    fan_updater = FanUpdater(SYSLOG_IDENTIFIER, chassis)
    fan_updater.update()
    fan_list = chassis.get_all_fans()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
    fan_updater.log_warning.assert_called()

    fan_list[0].presence = True
    fan_updater.update()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
    fan_updater.log_notice.assert_called()


def test_fanupdater_fan_fault():
    chassis = MockChassis()
    chassis.make_fault_fan()
    fan_updater = FanUpdater(SYSLOG_IDENTIFIER, chassis)
    fan_updater.update()
    fan_list = chassis.get_all_fans()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
    fan_updater.log_warning.assert_called()

    fan_list[0].status = True
    fan_updater.update()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
    fan_updater.log_notice.assert_called()


def test_fanupdater_fan_under_speed():
    chassis = MockChassis()
    chassis.make_under_speed_fan()
    fan_updater = FanUpdater(SYSLOG_IDENTIFIER, chassis)
    fan_updater.update()
    fan_list = chassis.get_all_fans()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
    fan_updater.log_warning.assert_called_once()

    fan_list[0].make_normal_speed()
    fan_updater.update()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
    fan_updater.log_notice.assert_called_once()


def test_fanupdater_fan_over_speed():
    chassis = MockChassis()
    chassis.make_over_speed_fan()
    fan_updater = FanUpdater(SYSLOG_IDENTIFIER, chassis)
    fan_updater.update()
    fan_list = chassis.get_all_fans()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
    fan_updater.log_warning.assert_called_once()

    fan_list[0].make_normal_speed()
    fan_updater.update()
    assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
    fan_updater.log_notice.assert_called_once()


def test_insufficient_fan_number():
    fan_status1 = FanStatus(SYSLOG_IDENTIFIER)
    fan_status2 = FanStatus(SYSLOG_IDENTIFIER)
    fan_status1.set_presence(False)
    fan_status2.set_fault_status(False)
    assert FanStatus.get_bad_fan_count() == 2
    FanStatus.reset_fan_counter()
    assert FanStatus.get_bad_fan_count() == 0

    chassis = MockChassis()
    chassis.make_absence_fan()
    chassis.make_fault_fan()
    fan_updater = FanUpdater(SYSLOG_IDENTIFIER, chassis)
    fan_updater.update()
    assert fan_updater.log_warning.call_count == 3
    fan_updater.log_warning.assert_called_with('Insufficient number of working fans warning: 2 fans are not working.')

    fan_list = chassis.get_all_fans()
    fan_list[0].presence = True
    fan_updater.update()
    assert fan_updater.log_notice.call_count == 1
    fan_updater.log_warning.assert_called_with('Insufficient number of working fans warning: 1 fans are not working.')
    
    fan_list[1].status = True
    fan_updater.update()
    assert fan_updater.log_notice.call_count == 3
    fan_updater.log_notice.assert_called_with('Insufficient number of working fans warning cleared: all fans are back to normal.')


def test_temperature_status_set_over_temper():
    temperatue_status = TemperatureStatus(SYSLOG_IDENTIFIER)
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
    temperature_status = TemperatureStatus(SYSLOG_IDENTIFIER)
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
    temperature_updater = TemperatureUpdater(SYSLOG_IDENTIFIER, chassis)
    temperature_updater.update()
    thermal_list = chassis.get_all_thermals()
    temperature_updater.log_warning.assert_called_once()

    thermal_list[0].make_normal_temper()
    temperature_updater.update()
    temperature_updater.log_notice.assert_called_once()


def test_temperupdater_under_temper():
    chassis = MockChassis()
    chassis.make_under_temper_thermal()
    temperature_updater = TemperatureUpdater(SYSLOG_IDENTIFIER, chassis)
    temperature_updater.update()
    thermal_list = chassis.get_all_thermals()
    temperature_updater.log_warning.assert_called_once()

    thermal_list[0].make_normal_temper()
    temperature_updater.update()
    temperature_updater.log_notice.assert_called_once()


def test_update_fan_with_exception():
    chassis = MockChassis()
    chassis.make_error_fan()
    fan = MockFan()
    fan.make_over_speed()
    chassis.get_all_fans().append(fan)

    fan_updater = FanUpdater(SYSLOG_IDENTIFIER, chassis)
    fan_updater.update()
    assert fan.get_status_led() == MockFan.STATUS_LED_COLOR_RED
    fan_updater.log_warning.assert_called()


def test_update_thermal_with_exception():
    chassis = MockChassis()
    chassis.make_error_thermal()
    thermal = MockThermal()
    thermal.make_over_temper()
    chassis.get_all_thermals().append(thermal)

    temperature_updater = TemperatureUpdater(SYSLOG_IDENTIFIER, chassis)
    temperature_updater.update()
    temperature_updater.log_warning.assert_called()

#Modular chassis related tests
def test_updater_thermal_check_modular_chassis():
    chassis = MockChassis()
    assert chassis.is_modular_chassis() == False

    temperature_updater = TemperatureUpdater(SYSLOG_IDENTIFIER, chassis)
    assert temperature_updater.chassis_table == None

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(-1)
    temperature_updater = TemperatureUpdater(SYSLOG_IDENTIFIER, chassis)
    assert temperature_updater.chassis_table == None

    my_slot = 1
    chassis.set_my_slot(my_slot)
    temperature_updater = TemperatureUpdater(SYSLOG_IDENTIFIER, chassis)
    assert temperature_updater.chassis_table != None
    assert temperature_updater.chassis_table.table_name == TEMPER_INFO_TABLE_NAME+'_'+str(my_slot)

def test_updater_thermal_check_chassis_table():
    chassis = MockChassis()

    thermal1 = MockThermal()
    chassis.get_all_thermals().append(thermal1)

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(1)
    temperature_updater = TemperatureUpdater(SYSLOG_IDENTIFIER, chassis)

    temperature_updater.update()
    assert temperature_updater.chassis_table.get_size() == chassis.get_num_thermals()

    thermal2 = MockThermal()
    chassis.get_all_thermals().append(thermal2)
    temperature_updater.update()
    assert temperature_updater.chassis_table.get_size() == chassis.get_num_thermals()

    temperature_updater.deinit()
    assert temperature_updater.chassis_table.get_size() == 0

def test_updater_thermal_check_min_max():
    chassis = MockChassis()

    thermal = MockThermal()
    chassis.get_all_thermals().append(thermal)

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(1)
    temperature_updater = TemperatureUpdater(SYSLOG_IDENTIFIER, chassis)

    temperature_updater.update()
    slot_dict = temperature_updater.chassis_table.get('Thermal 1')
    assert slot_dict['minimum_temperature'] == str(thermal.get_minimum_recorded())
    assert slot_dict['maximum_temperature'] == str(thermal.get_maximum_recorded())
