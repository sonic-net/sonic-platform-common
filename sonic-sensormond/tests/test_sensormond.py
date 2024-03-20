import os
import sys
import yaml
import multiprocessing
from imp import load_source
from unittest import mock
import pytest
from sonic_py_common import daemon_base
from swsscommon import swsscommon

# Setup load paths for mocked modules

tests_path = os.path.dirname(os.path.abspath(__file__))
mocked_libs_path = os.path.join(tests_path, 'mocked_libs')
sys.path.insert(0, mocked_libs_path)
modules_path = os.path.dirname(tests_path)
scripts_path = os.path.join(modules_path, 'scripts')
sys.path.insert(0, modules_path)

# Import mocked modules

from .mock_swsscommon import Table, FieldValuePairs
from .mock_platform import MockChassis, MockVoltageSensor, MockCurrentSensor

# Load file under test
load_source('sensormond', os.path.join(scripts_path, 'sensormond'))
import sensormond

daemon_base.db_connect = mock.MagicMock()
swsscommon.Table = Table
swsscommon.FieldValuePairs = FieldValuePairs

VOLTAGE_INFO_TABLE_NAME = 'VOLTAGE_INFO'
CURRENT_INFO_TABLE_NAME = 'CURRENT_INFO'

@pytest.fixture(scope='function', autouse=True)
def configure_mocks():
    sensormond.SensorStatus.log_notice = mock.MagicMock()
    sensormond.SensorStatus.log_warning = mock.MagicMock()
    sensormond.VoltageUpdater.log_notice = mock.MagicMock()
    sensormond.VoltageUpdater.log_warning = mock.MagicMock()
    sensormond.CurrentUpdater.log_notice = mock.MagicMock()
    sensormond.CurrentUpdater.log_warning = mock.MagicMock()

    yield

    sensormond.SensorStatus.log_notice.reset()
    sensormond.SensorStatus.log_warning.reset()
    sensormond.VoltageUpdater.log_notice.reset()
    sensormond.VoltageUpdater.log_warning.reset()
    sensormond.CurrentUpdater.log_notice.reset()
    sensormond.CurrentUpdater.log_warning.reset()

def test_sensor_status_set_over_threshold():
    sensor_status = sensormond.SensorStatus()
    ret = sensor_status.set_over_threshold(sensormond.NOT_AVAILABLE, sensormond.NOT_AVAILABLE)
    assert not ret

    ret = sensor_status.set_over_threshold(sensormond.NOT_AVAILABLE, 0)
    assert not ret

    ret = sensor_status.set_over_threshold(0, sensormond.NOT_AVAILABLE)
    assert not ret

    ret = sensor_status.set_over_threshold(2, 1)
    assert ret
    assert sensor_status.over_threshold

    ret = sensor_status.set_over_threshold(1, 2)
    assert ret
    assert not sensor_status.over_threshold


def test_sensor_status_set_under_threshold():
    sensor_status = sensormond.SensorStatus()
    ret = sensor_status.set_under_threshold(sensormond.NOT_AVAILABLE, sensormond.NOT_AVAILABLE)
    assert not ret

    ret = sensor_status.set_under_threshold(sensormond.NOT_AVAILABLE, 0)
    assert not ret

    ret = sensor_status.set_under_threshold(0, sensormond.NOT_AVAILABLE)
    assert not ret

    ret = sensor_status.set_under_threshold(1, 2)
    assert ret
    assert sensor_status.under_threshold

    ret = sensor_status.set_under_threshold(2, 1)
    assert ret
    assert not sensor_status.under_threshold


def test_sensor_status_set_not_available():
    SENSOR_NAME = 'Chassis 1 Sensor 1'
    sensor_status = sensormond.SensorStatus()
    sensor_status.value = 20.0

    sensor_status.set_value(SENSOR_NAME, sensormond.NOT_AVAILABLE)
    assert sensor_status.value is None
    assert sensor_status.log_warning.call_count == 1
    sensor_status.log_warning.assert_called_with('Value of {} became unavailable'.format(SENSOR_NAME))

class TestVoltageUpdater(object):
    """
    Test cases to cover functionality in VoltageUpdater class
    """
    def test_deinit(self):
        chassis = MockChassis()
        voltage_updater = sensormond.VoltageUpdater(chassis, [])
        voltage_updater.voltage_status_dict = {'key1': 'value1', 'key2': 'value2'}
        voltage_updater.table = Table("STATE_DB", "xtable")
        voltage_updater.table._del = mock.MagicMock()
        voltage_updater.table.getKeys = mock.MagicMock(return_value=['key1','key2'])
        voltage_updater.phy_entity_table = Table("STATE_DB", "ytable")
        voltage_updater.phy_entity_table._del = mock.MagicMock()
        voltage_updater.phy_entity_table.getKeys = mock.MagicMock(return_value=['key1','key2'])
        voltage_updater.chassis_table = Table("STATE_DB", "ctable")
        voltage_updater.chassis_table._del = mock.MagicMock()
        voltage_updater.is_chassis_system = True

        voltage_updater.__del__()
        assert voltage_updater.table.getKeys.call_count == 1
        assert voltage_updater.table._del.call_count == 2
        expected_calls = [mock.call('key1'), mock.call('key2')]
        voltage_updater.table._del.assert_has_calls(expected_calls, any_order=True)

    def test_over_voltage(self):
        chassis = MockChassis()
        chassis.make_over_threshold_voltage_sensor()
        voltage_updater = sensormond.VoltageUpdater(chassis, [])
        voltage_updater.update()
        voltage_sensor_list = chassis.get_all_voltage_sensors()
        assert voltage_updater.log_warning.call_count == 1
        voltage_updater.log_warning.assert_called_with('High voltage warning: chassis 1 voltage_sensor 1 current voltage 3mV, high threshold 2mV')

        voltage_sensor_list[0].make_normal_value()
        voltage_updater.update()
        assert voltage_updater.log_notice.call_count == 1
        voltage_updater.log_notice.assert_called_with('High voltage warning cleared: chassis 1 voltage_sensor 1 voltage restored to 2mV, high threshold 3mV')

    def test_under_voltage(self):
        chassis = MockChassis()
        chassis.make_under_threshold_voltage_sensor()
        voltage_updater = sensormond.VoltageUpdater(chassis, [])
        voltage_updater.update()
        voltage_sensor_list = chassis.get_all_voltage_sensors()
        assert voltage_updater.log_warning.call_count == 1
        voltage_updater.log_warning.assert_called_with('Low voltage warning: chassis 1 voltage_sensor 1 current voltage 1mV, low threshold 2mV')

        voltage_sensor_list[0].make_normal_value()
        voltage_updater.update()
        assert voltage_updater.log_notice.call_count == 1
        voltage_updater.log_notice.assert_called_with('Low voltage warning cleared: chassis 1 voltage_sensor 1 voltage restored to 2mV, low threshold 1mV')

    def test_update_voltage_sensor_with_exception(self):
        chassis = MockChassis()
        chassis.make_error_voltage_sensor()
        voltage_sensor = MockVoltageSensor()
        voltage_sensor.make_over_threshold()
        chassis.get_all_voltage_sensors().append(voltage_sensor)

        voltage_updater = sensormond.VoltageUpdater(chassis, [])
        voltage_updater.update()
        assert voltage_updater.log_warning.call_count == 2

        if sys.version_info.major == 3:
            expected_calls = [
                mock.call("Failed to update voltage_sensor status for chassis 1 voltage_sensor 1 - Exception('Failed to get voltage')"),
                mock.call('High voltage warning: chassis 1 voltage_sensor 2 current voltage 3mV, high threshold 2mV')
            ]
        else:
            expected_calls = [
                mock.call("Failed to update voltage_sensor status for chassis 1 voltage_sensor 1 - Exception('Failed to get voltage',)"),
                mock.call('High voltage warning: chassis 1 voltage_sensor 2 current voltage 3mV, high threshold 2mV')
            ]
        assert voltage_updater.log_warning.mock_calls == expected_calls

    def test_update_module_voltage_sensors(self):
        chassis = MockChassis()
        chassis.make_module_voltage_sensor()
        chassis.set_modular_chassis(True)
        voltage_updater = sensormond.VoltageUpdater(chassis, [])
        voltage_updater.update()
        assert len(voltage_updater.module_voltage_sensors) == 1
        
        chassis._module_list = []
        voltage_updater.update()
        assert len(voltage_updater.module_voltage_sensors) == 0


class TestCurrentUpdater(object):
    """
    Test cases to cover functionality in CurrentUpdater class
    """
    def test_deinit(self):
        chassis = MockChassis()
        current_updater = sensormond.CurrentUpdater(chassis, [])
        current_updater.current_status_dict = {'key1': 'value1', 'key2': 'value2'}
        current_updater.table = Table("STATE_DB", "xtable")
        current_updater.table._del = mock.MagicMock()
        current_updater.table.getKeys = mock.MagicMock(return_value=['key1','key2'])
        current_updater.phy_entity_table = Table("STATE_DB", "ytable")
        current_updater.phy_entity_table._del = mock.MagicMock()
        current_updater.phy_entity_table.getKeys = mock.MagicMock(return_value=['key1','key2'])
        current_updater.chassis_table = Table("STATE_DB", "ctable")
        current_updater.chassis_table._del = mock.MagicMock()
        current_updater.is_chassis_system = True

        current_updater.__del__()
        assert current_updater.table.getKeys.call_count == 1
        assert current_updater.table._del.call_count == 2
        expected_calls = [mock.call('key1'), mock.call('key2')]
        current_updater.table._del.assert_has_calls(expected_calls, any_order=True)

    def test_over_current(self):
        chassis = MockChassis()
        chassis.make_over_threshold_current_sensor()
        current_updater = sensormond.CurrentUpdater(chassis, [])
        current_updater.update()
        current_sensor_list = chassis.get_all_current_sensors()
        assert current_updater.log_warning.call_count == 1
        current_updater.log_warning.assert_called_with('High Current warning: chassis 1 current_sensor 1 current Current 3mA, high threshold 2mA')

        current_sensor_list[0].make_normal_value()
        current_updater.update()
        assert current_updater.log_notice.call_count == 1
        current_updater.log_notice.assert_called_with('High Current warning cleared: chassis 1 current_sensor 1 current restored to 2mA, high threshold 3mA')

    def test_under_current(self):
        chassis = MockChassis()
        chassis.make_under_threshold_current_sensor()
        current_updater = sensormond.CurrentUpdater(chassis, [])
        current_updater.update()
        current_sensor_list = chassis.get_all_current_sensors()
        assert current_updater.log_warning.call_count == 1
        current_updater.log_warning.assert_called_with('Low current warning: chassis 1 current_sensor 1 current current 1mA, low threshold 2mA')

        current_sensor_list[0].make_normal_value()
        current_updater.update()
        assert current_updater.log_notice.call_count == 1
        current_updater.log_notice.assert_called_with('Low current warning cleared: chassis 1 current_sensor 1 current restored to 2mA, low threshold 1mA')

    def test_update_current_sensor_with_exception(self):
        chassis = MockChassis()
        chassis.make_error_current_sensor()
        current_sensor = MockCurrentSensor()
        current_sensor.make_over_threshold()
        chassis.get_all_current_sensors().append(current_sensor)

        current_updater = sensormond.CurrentUpdater(chassis, [])
        current_updater.update()
        assert current_updater.log_warning.call_count == 2

        if sys.version_info.major == 3:
            expected_calls = [
                mock.call("Failed to update current_sensor status for chassis 1 current_sensor 1 - Exception('Failed to get current')"),
                mock.call('High Current warning: chassis 1 current_sensor 2 current Current 3mA, high threshold 2mA')
            ]
        else:
            expected_calls = [
                mock.call("Failed to update current_sensor status for chassis 1 current_sensor 1 - Exception('Failed to get current',)"),
                mock.call('High Current warning: chassis 1 current_sensor 2 current Current 3mA, high threshold 2mA')
            ]
        assert current_updater.log_warning.mock_calls == expected_calls

    def test_update_module_current_sensors(self):
        chassis = MockChassis()
        chassis.make_module_current_sensor()
        chassis.set_modular_chassis(True)
        current_updater = sensormond.CurrentUpdater(chassis, [])
        current_updater.update()
        assert len(current_updater.module_current_sensors) == 1
        
        chassis._module_list = []
        current_updater.update()
        assert len(current_updater.module_current_sensors) == 0

# Modular chassis-related tests


def test_updater_voltage_sensor_check_modular_chassis():
    chassis = MockChassis()
    assert chassis.is_modular_chassis() == False

    voltage_updater = sensormond.VoltageUpdater(chassis, [])
    assert voltage_updater.chassis_table == None

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(-1)
    voltage_updater = sensormond.VoltageUpdater(chassis, [])
    assert voltage_updater.chassis_table == None

    my_slot = 1
    chassis.set_my_slot(my_slot)
    voltage_updater = sensormond.VoltageUpdater(chassis, [])
    assert voltage_updater.chassis_table != None
    assert voltage_updater.chassis_table.table_name == '{}_{}'.format(VOLTAGE_INFO_TABLE_NAME, str(my_slot))


def test_updater_voltage_sensor_check_chassis_table():
    chassis = MockChassis()

    voltage_sensor1 = MockVoltageSensor()
    chassis.get_all_voltage_sensors().append(voltage_sensor1)

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(1)
    voltage_updater = sensormond.VoltageUpdater(chassis, [])

    voltage_updater.update()
    assert voltage_updater.chassis_table.get_size() == chassis.get_num_voltage_sensors()

    voltage_sensor2 = MockVoltageSensor()
    chassis.get_all_voltage_sensors().append(voltage_sensor2)
    voltage_updater.update()
    assert voltage_updater.chassis_table.get_size() == chassis.get_num_voltage_sensors()

def test_updater_voltage_sensor_check_min_max():
    chassis = MockChassis()

    voltage_sensor = MockVoltageSensor(1)
    chassis.get_all_voltage_sensors().append(voltage_sensor)

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(1)
    voltage_updater = sensormond.VoltageUpdater(chassis, [])

    voltage_updater.update()
    slot_dict = voltage_updater.chassis_table.get(voltage_sensor.get_name())
    assert slot_dict['minimum_voltage'] == str(voltage_sensor.get_minimum_recorded())
    assert slot_dict['maximum_voltage'] == str(voltage_sensor.get_maximum_recorded())


def test_updater_current_sensor_check_modular_chassis():
    chassis = MockChassis()
    assert chassis.is_modular_chassis() == False

    current_updater = sensormond.CurrentUpdater(chassis, [])
    assert current_updater.chassis_table == None

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(-1)
    current_updater = sensormond.CurrentUpdater(chassis, [])
    assert current_updater.chassis_table == None

    my_slot = 1
    chassis.set_my_slot(my_slot)
    current_updater = sensormond.CurrentUpdater(chassis, [])
    assert current_updater.chassis_table != None
    assert current_updater.chassis_table.table_name == '{}_{}'.format(CURRENT_INFO_TABLE_NAME, str(my_slot))


def test_updater_current_sensor_check_chassis_table():
    chassis = MockChassis()

    current_sensor1 = MockCurrentSensor()
    chassis.get_all_current_sensors().append(current_sensor1)

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(1)
    current_updater = sensormond.CurrentUpdater(chassis, [])

    current_updater.update()
    assert current_updater.chassis_table.get_size() == chassis.get_num_current_sensors()

    current_sensor2 = MockCurrentSensor()
    chassis.get_all_current_sensors().append(current_sensor2)
    current_updater.update()
    assert current_updater.chassis_table.get_size() == chassis.get_num_current_sensors()


def test_updater_current_sensor_check_min_max():
    chassis = MockChassis()

    current_sensor = MockCurrentSensor(1)
    chassis.get_all_current_sensors().append(current_sensor)

    chassis.set_modular_chassis(True)
    chassis.set_my_slot(1)
    current_updater = sensormond.CurrentUpdater(chassis, [])

    current_updater.update()
    slot_dict = current_updater.chassis_table.get(current_sensor.get_name())
    assert slot_dict['minimum_current'] == str(current_sensor.get_minimum_recorded())
    assert slot_dict['maximum_current'] == str(current_sensor.get_maximum_recorded())

def test_signal_handler():
    # Test SIGHUP
    daemon_sensormond = sensormond.SensorMonitorDaemon()
    daemon_sensormond.stop_event.set = mock.MagicMock()
    daemon_sensormond.log_info = mock.MagicMock()
    daemon_sensormond.log_warning = mock.MagicMock()
    daemon_sensormond.signal_handler(sensormond.signal.SIGHUP, None)
    assert daemon_sensormond.log_info.call_count == 1
    daemon_sensormond.log_info.assert_called_with("Caught signal 'SIGHUP' - ignoring...")
    assert daemon_sensormond.log_warning.call_count == 0
    assert daemon_sensormond.stop_event.set.call_count == 0
    assert sensormond.exit_code == 1

    # Test SIGINT
    daemon_sensormond = sensormond.SensorMonitorDaemon()
    daemon_sensormond.stop_event.set = mock.MagicMock()
    daemon_sensormond.log_info = mock.MagicMock()
    daemon_sensormond.log_warning = mock.MagicMock()
    test_signal = sensormond.signal.SIGINT
    daemon_sensormond.signal_handler(test_signal, None)
    assert daemon_sensormond.log_info.call_count == 1
    daemon_sensormond.log_info.assert_called_with("Caught signal 'SIGINT' - exiting...")
    assert daemon_sensormond.log_warning.call_count == 0
    assert daemon_sensormond.stop_event.set.call_count == 1
    assert sensormond.exit_code == (128 + test_signal)

    # Test SIGTERM
    sensormond.exit_code = 1
    daemon_sensormond = sensormond.SensorMonitorDaemon()
    daemon_sensormond.stop_event.set = mock.MagicMock()
    daemon_sensormond.log_info = mock.MagicMock()
    daemon_sensormond.log_warning = mock.MagicMock()
    test_signal = sensormond.signal.SIGTERM
    daemon_sensormond.signal_handler(test_signal, None)
    assert daemon_sensormond.log_info.call_count == 1
    daemon_sensormond.log_info.assert_called_with("Caught signal 'SIGTERM' - exiting...")
    assert daemon_sensormond.log_warning.call_count == 0
    assert daemon_sensormond.stop_event.set.call_count == 1
    assert sensormond.exit_code == (128 + test_signal)

    # Test an unhandled signal
    sensormond.exit_code = 1
    daemon_sensormond = sensormond.SensorMonitorDaemon()
    daemon_sensormond.stop_event.set = mock.MagicMock()
    daemon_sensormond.log_info = mock.MagicMock()
    daemon_sensormond.log_warning = mock.MagicMock()
    daemon_sensormond.signal_handler(sensormond.signal.SIGUSR1, None)
    assert daemon_sensormond.log_warning.call_count == 1
    daemon_sensormond.log_warning.assert_called_with("Caught unhandled signal 'SIGUSR1' - ignoring...")
    assert daemon_sensormond.log_info.call_count == 0
    assert daemon_sensormond.stop_event.set.call_count == 0
    assert sensormond.exit_code == 1

@mock.patch('sonic_py_common.device_info.get_paths_to_platform_and_hwsku_dirs', mock.MagicMock(return_value=(tests_path, '')))
def test_daemon_run():

    import sonic_platform.platform
    class MyPlatform():
        def get_chassis(self):
            return MockChassis()
    sonic_platform.platform.Platform = MyPlatform

    daemon_sensormond = sensormond.SensorMonitorDaemon()
    daemon_sensormond.stop_event.wait = mock.MagicMock(return_value=True)
    ret = daemon_sensormond.run()
    assert ret is False

    daemon_sensormond = sensormond.SensorMonitorDaemon()
    daemon_sensormond.stop_event.wait = mock.MagicMock(return_value=False)
    ret = daemon_sensormond.run()
    assert ret is True


def test_try_get():
    def good_callback():
        return 'good result'

    def unimplemented_callback():
        raise NotImplementedError

    ret = sensormond.try_get(good_callback)
    assert ret == 'good result'

    ret = sensormond.try_get(unimplemented_callback)
    assert ret == sensormond.NOT_AVAILABLE

    ret = sensormond.try_get(unimplemented_callback, 'my default')
    assert ret == 'my default'


def test_update_entity_info():
    mock_table = mock.MagicMock()
    mock_voltage_sensor = MockVoltageSensor()
    expected_fvp = sensormond.swsscommon.FieldValuePairs(
        [('position_in_parent', '1'),
         ('parent_name', 'Parent Name')
         ])

    sensormond.update_entity_info(mock_table, 'Parent Name', 'Key Name', mock_voltage_sensor, 1)
    assert mock_table.set.call_count == 1
    mock_table.set.assert_called_with('Key Name', expected_fvp)


@mock.patch('sensormond.SensorMonitorDaemon.run')
def test_main(mock_run):
    mock_run.return_value = False

    ret = sensormond.main()
    assert mock_run.call_count == 1
    assert  ret != 0
