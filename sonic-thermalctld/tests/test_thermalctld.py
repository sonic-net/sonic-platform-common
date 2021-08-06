import os
import sys
import multiprocessing
from imp import load_source  # TODO: Replace with importlib once we no longer need to support Python 2

# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

import pytest
tests_path = os.path.dirname(os.path.abspath(__file__))

# Add mocked_libs path so that the file under test can load mocked modules from there
mocked_libs_path = os.path.join(tests_path, 'mocked_libs')
sys.path.insert(0, mocked_libs_path)


import swsscommon
# Check we are using the mocked package
assert len(swsscommon.__path__) == 1
assert(os.path.samefile(swsscommon.__path__[0], os.path.join(mocked_libs_path, 'swsscommon')))

from sonic_py_common import daemon_base

from .mock_platform import MockChassis, MockFan, MockPsu, MockSfp, MockThermal

daemon_base.db_connect = mock.MagicMock()

# Add path to the file under test so that we can load it
modules_path = os.path.dirname(tests_path)
scripts_path = os.path.join(modules_path, 'scripts')
sys.path.insert(0, modules_path)

load_source('thermalctld', os.path.join(scripts_path, 'thermalctld'))
import thermalctld


TEMPER_INFO_TABLE_NAME = 'TEMPERATURE_INFO'


@pytest.fixture(scope='function', autouse=True)
def configure_mocks():
    thermalctld.FanStatus.log_notice = mock.MagicMock()
    thermalctld.FanStatus.log_warning = mock.MagicMock()
    thermalctld.FanUpdater.log_notice = mock.MagicMock()
    thermalctld.FanUpdater.log_warning = mock.MagicMock()
    thermalctld.TemperatureStatus.log_notice = mock.MagicMock()
    thermalctld.TemperatureStatus.log_warning = mock.MagicMock()
    thermalctld.TemperatureUpdater.log_notice = mock.MagicMock()
    thermalctld.TemperatureUpdater.log_warning = mock.MagicMock()

    yield

    thermalctld.FanStatus.log_notice.reset()
    thermalctld.FanStatus.log_warning.reset()
    thermalctld.FanUpdater.log_notice.reset()
    thermalctld.FanUpdater.log_notice.reset()
    thermalctld.TemperatureStatus.log_notice.reset()
    thermalctld.TemperatureStatus.log_warning.reset()
    thermalctld.TemperatureUpdater.log_warning.reset()
    thermalctld.TemperatureUpdater.log_warning.reset()


class TestFanStatus(object):
    """
    Test cases to cover functionality in FanStatus class
    """
    def test_check_speed_value_available(self):
        fan_status = thermalctld.FanStatus()

        ret = fan_status._check_speed_value_available(30, 32, 5, True)
        assert ret == True
        assert fan_status.log_warning.call_count == 0

        ret = fan_status._check_speed_value_available(thermalctld.NOT_AVAILABLE, 32, 105, True)
        assert ret == False
        assert fan_status.log_warning.call_count == 1
        fan_status.log_warning.assert_called_with('Invalid tolerance value: 105')

        # Reset
        fan_status.log_warning.reset_mock()

        ret = fan_status._check_speed_value_available(thermalctld.NOT_AVAILABLE, 32, 5, False)
        assert ret == False
        assert fan_status.log_warning.call_count == 0

        ret = fan_status._check_speed_value_available(thermalctld.NOT_AVAILABLE, 32, 5, True)
        assert ret == False
        assert fan_status.log_warning.call_count == 1
        fan_status.log_warning.assert_called_with('Fan speed or target_speed or tolerance became unavailable, speed=N/A, target_speed=32, tolerance=5')

    def test_set_presence(self):
        fan_status = thermalctld.FanStatus()
        ret = fan_status.set_presence(True)
        assert fan_status.presence
        assert not ret

        ret = fan_status.set_presence(False)
        assert not fan_status.presence
        assert ret

    def test_set_under_speed(self):
        fan_status = thermalctld.FanStatus()
        ret = fan_status.set_under_speed(thermalctld.NOT_AVAILABLE, thermalctld.NOT_AVAILABLE, thermalctld.NOT_AVAILABLE)
        assert not ret

        ret = fan_status.set_under_speed(thermalctld.NOT_AVAILABLE, thermalctld.NOT_AVAILABLE, 0)
        assert not ret

        ret = fan_status.set_under_speed(thermalctld.NOT_AVAILABLE, 0, 0)
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

    def test_set_over_speed(self):
        fan_status = thermalctld.FanStatus()
        ret = fan_status.set_over_speed(thermalctld.NOT_AVAILABLE, thermalctld.NOT_AVAILABLE, thermalctld.NOT_AVAILABLE)
        assert not ret

        ret = fan_status.set_over_speed(thermalctld.NOT_AVAILABLE, thermalctld.NOT_AVAILABLE, 0)
        assert not ret

        ret = fan_status.set_over_speed(thermalctld.NOT_AVAILABLE, 0, 0)
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


class TestFanUpdater(object):
    """
    Test cases to cover functionality in FanUpdater class
    """
    def test_deinit(self):
        fan_updater = thermalctld.FanUpdater(MockChassis(), multiprocessing.Event())
        fan_updater.fan_status_dict = {'key1': 'value1', 'key2': 'value2'}
        fan_updater.table._del = mock.MagicMock()

        fan_updater.deinit()
        assert fan_updater.table._del.call_count == 2
        expected_calls = [mock.call('key1'), mock.call('key2')]
        fan_updater.table._del.assert_has_calls(expected_calls, any_order=True)

    @mock.patch('thermalctld.try_get', mock.MagicMock(return_value=thermalctld.NOT_AVAILABLE))
    @mock.patch('thermalctld.update_entity_info', mock.MagicMock())
    def test_refresh_fan_drawer_status_fan_drawer_get_name_not_impl(self):
        # Test case where fan_drawer.get_name is not implemented
        fan_updater = thermalctld.FanUpdater(MockChassis(), multiprocessing.Event())
        mock_fan_drawer = mock.MagicMock()
        fan_updater._refresh_fan_drawer_status(mock_fan_drawer, 1)
        assert thermalctld.update_entity_info.call_count == 0

    # TODO: Add a test case for _refresh_fan_drawer_status with a good fan drawer

    def test_update_fan_with_exception(self):
        chassis = MockChassis()
        chassis.make_error_fan()
        fan = MockFan()
        fan.make_over_speed()
        chassis.get_all_fans().append(fan)

        fan_updater = thermalctld.FanUpdater(chassis, multiprocessing.Event())
        fan_updater.update()
        assert fan.get_status_led() == MockFan.STATUS_LED_COLOR_RED
        assert fan_updater.log_warning.call_count == 1

        # TODO: Clean this up once we no longer need to support Python 2
        if sys.version_info.major == 3:
            fan_updater.log_warning.assert_called_with("Failed to update fan status - Exception('Failed to get speed')")
        else:
            fan_updater.log_warning.assert_called_with("Failed to update fan status - Exception('Failed to get speed',)")

    def test_set_fan_led_exception(self):
        fan_status = thermalctld.FanStatus()
        mock_fan_drawer = mock.MagicMock()
        mock_fan = MockFan()
        mock_fan.set_status_led = mock.MagicMock(side_effect=NotImplementedError)

        fan_updater = thermalctld.FanUpdater(MockChassis(), multiprocessing.Event())
        fan_updater._set_fan_led(mock_fan_drawer, mock_fan, 'Test Fan', fan_status)
        assert fan_updater.log_warning.call_count == 1
        fan_updater.log_warning.assert_called_with('Failed to set status LED for fan Test Fan, set_status_led not implemented')

    def test_fan_absent(self):
        chassis = MockChassis()
        chassis.make_absent_fan()
        fan_updater = thermalctld.FanUpdater(chassis, multiprocessing.Event())
        fan_updater.update()
        fan_list = chassis.get_all_fans()
        assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
        assert fan_updater.log_warning.call_count == 2
        expected_calls = [
            mock.call('Fan removed warning: FanDrawer 0 fan 1 was removed from the system, potential overheat hazard'),
            mock.call('Insufficient number of working fans warning: 1 fan is not working')
        ]
        assert fan_updater.log_warning.mock_calls == expected_calls

        fan_list[0].set_presence(True)
        fan_updater.update()
        assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
        assert fan_updater.log_notice.call_count == 2
        expected_calls = [
            mock.call('Fan removed warning cleared: FanDrawer 0 fan 1 was inserted'),
            mock.call('Insufficient number of working fans warning cleared: all fans are back to normal')
        ]
        assert fan_updater.log_notice.mock_calls == expected_calls

    def test_fan_faulty(self):
        chassis = MockChassis()
        chassis.make_faulty_fan()
        fan_updater = thermalctld.FanUpdater(chassis, multiprocessing.Event())
        fan_updater.update()
        fan_list = chassis.get_all_fans()
        assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
        assert fan_updater.log_warning.call_count == 2
        expected_calls = [
            mock.call('Fan fault warning: FanDrawer 0 fan 1 is broken'),
            mock.call('Insufficient number of working fans warning: 1 fan is not working')
        ]
        assert fan_updater.log_warning.mock_calls == expected_calls

        fan_list[0].set_status(True)
        fan_updater.update()
        assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
        assert fan_updater.log_notice.call_count == 2
        expected_calls = [
            mock.call('Fan fault warning cleared: FanDrawer 0 fan 1 is back to normal'),
            mock.call('Insufficient number of working fans warning cleared: all fans are back to normal')
        ]
        assert fan_updater.log_notice.mock_calls == expected_calls

    def test_fan_under_speed(self):
        chassis = MockChassis()
        chassis.make_under_speed_fan()
        fan_updater = thermalctld.FanUpdater(chassis, multiprocessing.Event())
        fan_updater.update()
        fan_list = chassis.get_all_fans()
        assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
        assert fan_updater.log_warning.call_count == 1
        fan_updater.log_warning.assert_called_with('Fan low speed warning: FanDrawer 0 fan 1 current speed=1, target speed=2, tolerance=0')

        fan_list[0].make_normal_speed()
        fan_updater.update()
        assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
        assert fan_updater.log_notice.call_count == 1
        fan_updater.log_notice.assert_called_with('Fan low speed warning cleared: FanDrawer 0 fan 1 speed is back to normal')

    def test_fan_over_speed(self):
        chassis = MockChassis()
        chassis.make_over_speed_fan()
        fan_updater = thermalctld.FanUpdater(chassis, multiprocessing.Event())
        fan_updater.update()
        fan_list = chassis.get_all_fans()
        assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_RED
        assert fan_updater.log_warning.call_count == 1
        fan_updater.log_warning.assert_called_with('Fan high speed warning: FanDrawer 0 fan 1 target speed=1, current speed=2, tolerance=0')

        fan_list[0].make_normal_speed()
        fan_updater.update()
        assert fan_list[0].get_status_led() == MockFan.STATUS_LED_COLOR_GREEN
        assert fan_updater.log_notice.call_count == 1
        fan_updater.log_notice.assert_called_with('Fan high speed warning cleared: FanDrawer 0 fan 1 speed is back to normal')

    def test_update_psu_fans(self):
        chassis = MockChassis()
        psu = MockPsu()
        mock_fan = MockFan()
        psu._fan_list.append(mock_fan)
        chassis._psu_list.append(psu)
        fan_updater = thermalctld.FanUpdater(chassis, multiprocessing.Event())
        fan_updater.update()
        assert fan_updater.log_warning.call_count == 0

        fan_updater._refresh_fan_status = mock.MagicMock(side_effect=Exception("Test message"))
        fan_updater.update()
        assert fan_updater.log_warning.call_count == 1

        # TODO: Clean this up once we no longer need to support Python 2
        if sys.version_info.major == 3:
            fan_updater.log_warning.assert_called_with("Failed to update PSU fan status - Exception('Test message')")
        else:
            fan_updater.log_warning.assert_called_with("Failed to update PSU fan status - Exception('Test message',)")


class TestThermalMonitor(object):
    """
    Test cases to cover functionality in ThermalMonitor class
    """
    def test_main(self):
        mock_chassis = MockChassis()
        thermal_monitor = thermalctld.ThermalMonitor(mock_chassis)
        thermal_monitor.fan_updater.update = mock.MagicMock()
        thermal_monitor.temperature_updater.update = mock.MagicMock()

        thermal_monitor.main()
        assert thermal_monitor.fan_updater.update.call_count == 1
        assert thermal_monitor.temperature_updater.update.call_count == 1


def test_insufficient_fan_number():
    fan_status1 = thermalctld.FanStatus()
    fan_status2 = thermalctld.FanStatus()

    fan_status1.set_presence(False)
    fan_status2.set_fault_status(False)
    assert thermalctld.FanStatus.get_bad_fan_count() == 2
    assert fan_status1.get_bad_fan_count() == 2
    assert fan_status2.get_bad_fan_count() == 2

    thermalctld.FanStatus.reset_fan_counter()
    assert thermalctld.FanStatus.get_bad_fan_count() == 0
    assert fan_status1.get_bad_fan_count() == 0
    assert fan_status2.get_bad_fan_count() == 0

    chassis = MockChassis()
    chassis.make_absent_fan()
    chassis.make_faulty_fan()
    fan_updater = thermalctld.FanUpdater(chassis, multiprocessing.Event())
    fan_updater.update()
    assert fan_updater.log_warning.call_count == 3
    expected_calls = [
        mock.call('Fan removed warning: FanDrawer 0 fan 1 was removed from the system, potential overheat hazard'),
        mock.call('Fan fault warning: FanDrawer 1 fan 1 is broken'),
        mock.call('Insufficient number of working fans warning: 2 fans are not working')
    ]
    assert fan_updater.log_warning.mock_calls == expected_calls

    fan_list = chassis.get_all_fans()
    fan_list[0].set_presence(True)
    fan_updater.update()
    assert fan_updater.log_notice.call_count == 1
    fan_updater.log_warning.assert_called_with('Insufficient number of working fans warning: 1 fan is not working')

    fan_list[1].set_status(True)
    fan_updater.update()
    assert fan_updater.log_notice.call_count == 3
    expected_calls = [
            mock.call('Fan removed warning cleared: FanDrawer 0 fan 1 was inserted'),
            mock.call('Fan fault warning cleared: FanDrawer 1 fan 1 is back to normal'),
        mock.call('Insufficient number of working fans warning cleared: all fans are back to normal')
    ]
    assert fan_updater.log_notice.mock_calls == expected_calls


def test_temperature_status_set_over_temper():
    temperature_status = thermalctld.TemperatureStatus()
    ret = temperature_status.set_over_temperature(thermalctld.NOT_AVAILABLE, thermalctld.NOT_AVAILABLE)
    assert not ret

    ret = temperature_status.set_over_temperature(thermalctld.NOT_AVAILABLE, 0)
    assert not ret

    ret = temperature_status.set_over_temperature(0, thermalctld.NOT_AVAILABLE)
    assert not ret

    ret = temperature_status.set_over_temperature(2, 1)
    assert ret
    assert temperature_status.over_temperature

    ret = temperature_status.set_over_temperature(1, 2)
    assert ret
    assert not temperature_status.over_temperature


def test_temperstatus_set_under_temper():
    temperature_status = thermalctld.TemperatureStatus()
    ret = temperature_status.set_under_temperature(thermalctld.NOT_AVAILABLE, thermalctld.NOT_AVAILABLE)
    assert not ret

    ret = temperature_status.set_under_temperature(thermalctld.NOT_AVAILABLE, 0)
    assert not ret

    ret = temperature_status.set_under_temperature(0, thermalctld.NOT_AVAILABLE)
    assert not ret

    ret = temperature_status.set_under_temperature(1, 2)
    assert ret
    assert temperature_status.under_temperature

    ret = temperature_status.set_under_temperature(2, 1)
    assert ret
    assert not temperature_status.under_temperature


def test_temperature_status_set_not_available():
    THERMAL_NAME = 'Chassis 1 Thermal 1'
    temperature_status = thermalctld.TemperatureStatus()
    temperature_status.temperature = 20.0

    temperature_status.set_temperature(THERMAL_NAME, thermalctld.NOT_AVAILABLE)
    assert temperature_status.temperature is None
    assert temperature_status.log_warning.call_count == 1
    temperature_status.log_warning.assert_called_with('Temperature of {} became unavailable'.format(THERMAL_NAME))


class TestTemperatureUpdater(object):
    """
    Test cases to cover functionality in TemperatureUpdater class
    """
    def test_deinit(self):
        chassis = MockChassis()
        temp_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())
        temp_updater.temperature_status_dict = {'key1': 'value1', 'key2': 'value2'}
        temp_updater.table._del = mock.MagicMock()

        temp_updater.deinit()
        assert temp_updater.table._del.call_count == 2
        expected_calls = [mock.call('key1'), mock.call('key2')]
        temp_updater.table._del.assert_has_calls(expected_calls, any_order=True)
        

    def test_over_temper(self):
        chassis = MockChassis()
        chassis.make_over_temper_thermal()
        temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())
        temperature_updater.update()
        thermal_list = chassis.get_all_thermals()
        assert temperature_updater.log_warning.call_count == 1
        temperature_updater.log_warning.assert_called_with('High temperature warning: chassis 1 Thermal 1 current temperature 3C, high threshold 2C')

        thermal_list[0].make_normal_temper()
        temperature_updater.update()
        assert temperature_updater.log_notice.call_count == 1
        temperature_updater.log_notice.assert_called_with('High temperature warning cleared: chassis 1 Thermal 1 temperature restored to 2C, high threshold 3C')

    def test_under_temper(self):
        chassis = MockChassis()
        chassis.make_under_temper_thermal()
        temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())
        temperature_updater.update()
        thermal_list = chassis.get_all_thermals()
        assert temperature_updater.log_warning.call_count == 1
        temperature_updater.log_warning.assert_called_with('Low temperature warning: chassis 1 Thermal 1 current temperature 1C, low threshold 2C')

        thermal_list[0].make_normal_temper()
        temperature_updater.update()
        assert temperature_updater.log_notice.call_count == 1
        temperature_updater.log_notice.assert_called_with('Low temperature warning cleared: chassis 1 Thermal 1 temperature restored to 2C, low threshold 1C')

    def test_update_psu_thermals(self):
        chassis = MockChassis()
        psu = MockPsu()
        mock_thermal = MockThermal()
        psu._thermal_list.append(mock_thermal)
        chassis._psu_list.append(psu)
        temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())
        temperature_updater.update()
        assert temperature_updater.log_warning.call_count == 0

        temperature_updater._refresh_temperature_status = mock.MagicMock(side_effect=Exception("Test message"))
        temperature_updater.update()
        assert temperature_updater.log_warning.call_count == 1

        # TODO: Clean this up once we no longer need to support Python 2
        if sys.version_info.major == 3:
            temperature_updater.log_warning.assert_called_with("Failed to update thermal status - Exception('Test message')")
        else:
            temperature_updater.log_warning.assert_called_with("Failed to update thermal status - Exception('Test message',)")

    def test_update_sfp_thermals(self):
        chassis = MockChassis()
        sfp = MockSfp()
        mock_thermal = MockThermal()
        sfp._thermal_list.append(mock_thermal)
        chassis._sfp_list.append(sfp)
        temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())
        temperature_updater.update()
        assert temperature_updater.log_warning.call_count == 0

        temperature_updater._refresh_temperature_status = mock.MagicMock(side_effect=Exception("Test message"))
        temperature_updater.update()
        assert temperature_updater.log_warning.call_count == 1

        # TODO: Clean this up once we no longer need to support Python 2
        if sys.version_info.major == 3:
            temperature_updater.log_warning.assert_called_with("Failed to update thermal status - Exception('Test message')")
        else:
            temperature_updater.log_warning.assert_called_with("Failed to update thermal status - Exception('Test message',)")

    def test_update_thermal_with_exception(self):
        chassis = MockChassis()
        chassis.make_error_thermal()
        thermal = MockThermal()
        thermal.make_over_temper()
        chassis.get_all_thermals().append(thermal)

        temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())
        temperature_updater.update()
        assert temperature_updater.log_warning.call_count == 2

        # TODO: Clean this up once we no longer need to support Python 2
        if sys.version_info.major == 3:
            expected_calls = [
                mock.call("Failed to update thermal status - Exception('Failed to get temperature')"),
                mock.call('High temperature warning: chassis 1 Thermal 2 current temperature 3C, high threshold 2C')
            ]
        else:
            expected_calls = [
                mock.call("Failed to update thermal status - Exception('Failed to get temperature',)"),
                mock.call('High temperature warning: chassis 1 Thermal 2 current temperature 3C, high threshold 2C')
            ]
        assert temperature_updater.log_warning.mock_calls == expected_calls


# Modular chassis-related tests


def test_updater_thermal_check_modular_chassis():
    chassis = MockChassis()
    assert chassis.is_modular_chassis() == False

    temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())
    assert temperature_updater.chassis_table == None

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(-1)
    temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())
    assert temperature_updater.chassis_table == None

    my_slot = 1
    chassis.set_my_slot(my_slot)
    temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())
    assert temperature_updater.chassis_table != None
    assert temperature_updater.chassis_table.table_name == '{}_{}'.format(TEMPER_INFO_TABLE_NAME, str(my_slot))


def test_updater_thermal_check_chassis_table():
    chassis = MockChassis()

    thermal1 = MockThermal()
    chassis.get_all_thermals().append(thermal1)

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(1)
    temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())

    temperature_updater.update()
    assert temperature_updater.chassis_table.get_size() == chassis.get_num_thermals()

    thermal2 = MockThermal()
    chassis.get_all_thermals().append(thermal2)
    temperature_updater.update()
    assert temperature_updater.chassis_table.get_size() == chassis.get_num_thermals()


def test_updater_thermal_check_min_max():
    chassis = MockChassis()

    thermal = MockThermal(1)
    chassis.get_all_thermals().append(thermal)

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(1)
    temperature_updater = thermalctld.TemperatureUpdater(chassis, multiprocessing.Event())

    temperature_updater.update()
    slot_dict = temperature_updater.chassis_table.get(thermal.get_name())
    assert slot_dict['minimum_temperature'] == str(thermal.get_minimum_recorded())
    assert slot_dict['maximum_temperature'] == str(thermal.get_maximum_recorded())


def test_signal_handler():
    # Test SIGHUP
    daemon_thermalctld = thermalctld.ThermalControlDaemon()
    daemon_thermalctld.stop_event.set = mock.MagicMock()
    daemon_thermalctld.log_info = mock.MagicMock()
    daemon_thermalctld.log_warning = mock.MagicMock()
    daemon_thermalctld.thermal_manager.stop = mock.MagicMock()
    daemon_thermalctld.signal_handler(thermalctld.signal.SIGHUP, None)
    daemon_thermalctld.deinit() # Deinit becuase the test will hang if we assert
    assert daemon_thermalctld.log_info.call_count == 1
    daemon_thermalctld.log_info.assert_called_with("Caught signal 'SIGHUP' - ignoring...")
    assert daemon_thermalctld.log_warning.call_count == 0
    assert daemon_thermalctld.stop_event.set.call_count == 0
    assert daemon_thermalctld.thermal_manager.stop.call_count == 0
    assert thermalctld.exit_code == thermalctld.ERR_UNKNOWN

    # Test SIGINT
    daemon_thermalctld = thermalctld.ThermalControlDaemon()
    daemon_thermalctld.stop_event.set = mock.MagicMock()
    daemon_thermalctld.log_info = mock.MagicMock()
    daemon_thermalctld.log_warning = mock.MagicMock()
    daemon_thermalctld.thermal_manager.stop = mock.MagicMock()
    test_signal = thermalctld.signal.SIGINT
    daemon_thermalctld.signal_handler(test_signal, None)
    daemon_thermalctld.deinit() # Deinit becuase the test will hang if we assert
    assert daemon_thermalctld.log_info.call_count == 1
    daemon_thermalctld.log_info.assert_called_with("Caught signal 'SIGINT' - exiting...")
    assert daemon_thermalctld.log_warning.call_count == 0
    assert daemon_thermalctld.stop_event.set.call_count == 1
    assert daemon_thermalctld.thermal_manager.stop.call_count == 1
    assert thermalctld.exit_code == (128 + test_signal)

    # Test SIGTERM
    thermalctld.exit_code = thermalctld.ERR_UNKNOWN
    daemon_thermalctld = thermalctld.ThermalControlDaemon()
    daemon_thermalctld.stop_event.set = mock.MagicMock()
    daemon_thermalctld.log_info = mock.MagicMock()
    daemon_thermalctld.log_warning = mock.MagicMock()
    daemon_thermalctld.thermal_manager.stop = mock.MagicMock()
    test_signal = thermalctld.signal.SIGTERM
    daemon_thermalctld.signal_handler(test_signal, None)
    daemon_thermalctld.deinit() # Deinit becuase the test will hang if we assert
    assert daemon_thermalctld.log_info.call_count == 1
    daemon_thermalctld.log_info.assert_called_with("Caught signal 'SIGTERM' - exiting...")
    assert daemon_thermalctld.log_warning.call_count == 0
    assert daemon_thermalctld.stop_event.set.call_count == 1
    assert daemon_thermalctld.thermal_manager.stop.call_count == 1
    assert thermalctld.exit_code == (128 + test_signal)

    # Test an unhandled signal
    thermalctld.exit_code = thermalctld.ERR_UNKNOWN
    daemon_thermalctld = thermalctld.ThermalControlDaemon()
    daemon_thermalctld.stop_event.set = mock.MagicMock()
    daemon_thermalctld.log_info = mock.MagicMock()
    daemon_thermalctld.log_warning = mock.MagicMock()
    daemon_thermalctld.thermal_manager.stop = mock.MagicMock()
    daemon_thermalctld.signal_handler(thermalctld.signal.SIGUSR1, None)
    daemon_thermalctld.deinit() # Deinit becuase the test will hang if we assert
    assert daemon_thermalctld.log_warning.call_count == 1
    daemon_thermalctld.log_warning.assert_called_with("Caught unhandled signal 'SIGUSR1' - ignoring...")
    assert daemon_thermalctld.log_info.call_count == 0
    assert daemon_thermalctld.stop_event.set.call_count == 0
    assert daemon_thermalctld.thermal_manager.stop.call_count == 0
    assert thermalctld.exit_code == thermalctld.ERR_UNKNOWN


def test_daemon_run():
    daemon_thermalctld = thermalctld.ThermalControlDaemon()
    daemon_thermalctld.stop_event.wait = mock.MagicMock(return_value=True)
    daemon_thermalctld.thermal_manager.get_interval = mock.MagicMock(return_value=60)
    ret = daemon_thermalctld.run()
    daemon_thermalctld.deinit() # Deinit becuase the test will hang if we assert
    assert ret is False

    daemon_thermalctld = thermalctld.ThermalControlDaemon()
    daemon_thermalctld.stop_event.wait = mock.MagicMock(return_value=False)
    daemon_thermalctld.thermal_manager.get_interval = mock.MagicMock(return_value=60)
    ret = daemon_thermalctld.run()
    daemon_thermalctld.deinit() # Deinit becuase the test will hang if we assert
    assert ret is True


def test_try_get():
    def good_callback():
        return 'good result'

    def unimplemented_callback():
        raise NotImplementedError

    ret = thermalctld.try_get(good_callback)
    assert ret == 'good result'

    ret = thermalctld.try_get(unimplemented_callback)
    assert ret == thermalctld.NOT_AVAILABLE

    ret = thermalctld.try_get(unimplemented_callback, 'my default')
    assert ret == 'my default'


def test_update_entity_info():
    mock_table = mock.MagicMock()
    mock_fan = MockFan()
    expected_fvp = thermalctld.swsscommon.FieldValuePairs(
        [('position_in_parent', '1'),
         ('parent_name', 'Parent Name')
         ])

    thermalctld.update_entity_info(mock_table, 'Parent Name', 'Key Name', mock_fan, 1)
    assert mock_table.set.call_count == 1
    mock_table.set.assert_called_with('Key Name', expected_fvp)


@mock.patch('thermalctld.ThermalControlDaemon.run')
def test_main(mock_run):
    mock_run.return_value = False

    ret = thermalctld.main()
    assert mock_run.call_count == 1
    assert  ret != 0
