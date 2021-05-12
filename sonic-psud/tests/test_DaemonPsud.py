import datetime
import os
import sys
from imp import load_source  # Replace with importlib once we no longer need to support Python 2

import pytest

# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock
from sonic_py_common import daemon_base

from .mock_platform import MockChassis, MockFan, MockPsu

SYSLOG_IDENTIFIER = 'psud_test'
NOT_AVAILABLE = 'N/A'

daemon_base.db_connect = mock.MagicMock()

tests_path = os.path.dirname(os.path.abspath(__file__))

# Add mocked_libs path so that the file under test can load mocked modules from there
mocked_libs_path = os.path.join(tests_path, "mocked_libs")
sys.path.insert(0, mocked_libs_path)

# Add path to the file under test so that we can load it
modules_path = os.path.dirname(tests_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)
load_source('psud', os.path.join(scripts_path, 'psud'))
import psud


class TestDaemonPsud(object):
    """
    Test cases to cover functionality in DaemonPsud class
    """

    def test_signal_handler(self):
        psud.platform_chassis = MockChassis()
        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)
        daemon_psud.stop_event.set = mock.MagicMock()
        daemon_psud.log_info = mock.MagicMock()
        daemon_psud.log_warning = mock.MagicMock()

        # Test SIGHUP
        daemon_psud.signal_handler(psud.signal.SIGHUP, None)
        assert daemon_psud.log_info.call_count == 1
        daemon_psud.log_info.assert_called_with("Caught signal 'SIGHUP' - ignoring...")
        assert daemon_psud.log_warning.call_count == 0
        assert daemon_psud.stop_event.set.call_count == 0
        assert psud.exit_code == 0

        # Reset
        daemon_psud.log_info.reset_mock()
        daemon_psud.log_warning.reset_mock()
        daemon_psud.stop_event.set.reset_mock()

        # Test SIGINT
        test_signal = psud.signal.SIGINT
        daemon_psud.signal_handler(test_signal, None)
        assert daemon_psud.log_info.call_count == 1
        daemon_psud.log_info.assert_called_with("Caught signal 'SIGINT' - exiting...")
        assert daemon_psud.log_warning.call_count == 0
        assert daemon_psud.stop_event.set.call_count == 1
        assert psud.exit_code == (128 + test_signal)

        # Reset
        daemon_psud.log_info.reset_mock()
        daemon_psud.log_warning.reset_mock()
        daemon_psud.stop_event.set.reset_mock()

        # Test SIGTERM
        test_signal = psud.signal.SIGTERM
        daemon_psud.signal_handler(test_signal, None)
        assert daemon_psud.log_info.call_count == 1
        daemon_psud.log_info.assert_called_with("Caught signal 'SIGTERM' - exiting...")
        assert daemon_psud.log_warning.call_count == 0
        assert daemon_psud.stop_event.set.call_count == 1
        assert psud.exit_code == (128 + test_signal)

        # Reset
        daemon_psud.log_info.reset_mock()
        daemon_psud.log_warning.reset_mock()
        daemon_psud.stop_event.set.reset_mock()
        psud.exit_code = 0

        # Test an unhandled signal
        daemon_psud.signal_handler(psud.signal.SIGUSR1, None)
        assert daemon_psud.log_warning.call_count == 1
        daemon_psud.log_warning.assert_called_with("Caught unhandled signal 'SIGUSR1' - ignoring...")
        assert daemon_psud.log_info.call_count == 0
        assert daemon_psud.stop_event.set.call_count == 0
        assert psud.exit_code == 0

    def test_run(self):
        psud.platform_chassis = MockChassis()
        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)
        daemon_psud._update_psu_entity_info = mock.MagicMock()
        daemon_psud.update_psu_data = mock.MagicMock()
        daemon_psud._update_led_color = mock.MagicMock()
        daemon_psud.update_psu_chassis_info = mock.MagicMock()

        daemon_psud.run()
        assert daemon_psud.first_run is False

    def test_update_psu_data(self):
        mock_psu1 = MockPsu("PSU 1", 0, True, True)
        mock_psu2 = MockPsu("PSU 2", 1, True, True)

        psud.platform_chassis = MockChassis()
        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)
        daemon_psud._update_single_psu_data = mock.MagicMock()
        daemon_psud.log_warning = mock.MagicMock()

        # Test platform_chassis is None
        psud.platform_chassis = None
        daemon_psud.update_psu_data()
        assert daemon_psud._update_single_psu_data.call_count == 0
        assert daemon_psud.log_warning.call_count == 0

        # Test with mocked platform_chassis
        psud.platform_chassis = MockChassis()
        psud.platform_chassis._psu_list = [mock_psu1, mock_psu2]
        daemon_psud.update_psu_data()
        assert daemon_psud._update_single_psu_data.call_count == 2
        expected_calls = [mock.call(1, mock_psu1), mock.call(2, mock_psu2)]
        assert daemon_psud._update_single_psu_data.mock_calls == expected_calls
        assert daemon_psud.log_warning.call_count == 0

        daemon_psud._update_single_psu_data.reset_mock()

        # Test _update_single_psu_data() throws exception
        daemon_psud._update_single_psu_data.side_effect = Exception("Test message")
        daemon_psud.update_psu_data()
        assert daemon_psud._update_single_psu_data.call_count == 2
        expected_calls = [mock.call(1, mock_psu1), mock.call(2, mock_psu2)]
        assert daemon_psud._update_single_psu_data.mock_calls == expected_calls
        assert daemon_psud.log_warning.call_count == 2
        expected_calls = [mock.call("Failed to update PSU data - Test message")] * 2
        assert daemon_psud.log_warning.mock_calls == expected_calls

    @mock.patch('psud._wrapper_get_psu_presence', mock.MagicMock())
    @mock.patch('psud._wrapper_get_psu_status', mock.MagicMock())
    def test_update_single_psu_data(self):
        psud._wrapper_get_psu_presence.return_value = True
        psud._wrapper_get_psu_status.return_value = True

        psu1 = MockPsu('PSU 1', 0, True, 'Fake Model', '12345678', '1234')
        psud.platform_chassis = MockChassis()
        psud.platform_chassis._psu_list.append(psu1)

        expected_fvp = psud.swsscommon.FieldValuePairs(
            [(psud.PSU_INFO_MODEL_FIELD, 'Fake Model'),
             (psud.PSU_INFO_SERIAL_FIELD, '12345678'),
             (psud.PSU_INFO_REV_FIELD, '1234'),
             (psud.PSU_INFO_TEMP_FIELD, '30.0'),
             (psud.PSU_INFO_TEMP_TH_FIELD, '50.0'),
             (psud.PSU_INFO_VOLTAGE_FIELD, '12.0'),
             (psud.PSU_INFO_VOLTAGE_MIN_TH_FIELD, '11.0'),
             (psud.PSU_INFO_VOLTAGE_MAX_TH_FIELD, '13.0'),
             (psud.PSU_INFO_CURRENT_FIELD, '8.0'),
             (psud.PSU_INFO_POWER_FIELD, '100.0'),
             (psud.PSU_INFO_FRU_FIELD, 'True'),
             ])

        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)
        daemon_psud.psu_tbl = mock.MagicMock()
        daemon_psud._update_single_psu_data(1, psu1)
        daemon_psud.psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(1), expected_fvp)

    def test_set_psu_led(self):
        mock_logger = mock.MagicMock()
        mock_psu = MockPsu("PSU 1", 0, True, True)
        psu_status = psud.PsuStatus(mock_logger, mock_psu)

        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)

        psu_status.presence = True
        psu_status.power_good = True
        psu_status.voltage_good = True
        psu_status.temperature_good = True
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert mock_psu.get_status_led() == mock_psu.STATUS_LED_COLOR_GREEN

        psu_status.presence = False
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert mock_psu.get_status_led() == mock_psu.STATUS_LED_COLOR_RED

        psu_status.presence = True
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert mock_psu.get_status_led() == mock_psu.STATUS_LED_COLOR_GREEN

        psu_status.power_good = False
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert mock_psu.get_status_led() == mock_psu.STATUS_LED_COLOR_RED

        psu_status.power_good = True
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert mock_psu.get_status_led() == mock_psu.STATUS_LED_COLOR_GREEN

        psu_status.voltage_good = False
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert mock_psu.get_status_led() == mock_psu.STATUS_LED_COLOR_RED

        psu_status.voltage_good = True
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert mock_psu.get_status_led() == mock_psu.STATUS_LED_COLOR_GREEN

        psu_status.temperature_good = False
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert mock_psu.get_status_led() == mock_psu.STATUS_LED_COLOR_RED

        psu_status.temperature_good = True
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert mock_psu.get_status_led() == mock_psu.STATUS_LED_COLOR_GREEN

        # Test set_status_led not implemented
        mock_psu.set_status_led = mock.MagicMock(side_effect=NotImplementedError)
        daemon_psud.log_warning = mock.MagicMock()
        daemon_psud._set_psu_led(mock_psu, psu_status)
        assert daemon_psud.log_warning.call_count == 1
        daemon_psud.log_warning.assert_called_with("set_status_led() not implemented")

    def test_update_led_color(self):
        mock_psu = MockPsu("PSU 1", 0, True, True)
        mock_logger = mock.MagicMock()
        psu_status = psud.PsuStatus(mock_logger, mock_psu)

        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)
        daemon_psud.psu_tbl = mock.MagicMock()
        daemon_psud._update_psu_fan_led_status = mock.MagicMock()

        # If psud.platform_chassis is None, _update_psu_fan_led_status() should do nothing
        psud.platform_chassis = None
        daemon_psud._update_led_color()
        assert daemon_psud.psu_tbl.set.call_count == 0
        assert daemon_psud._update_psu_fan_led_status.call_count == 0

        psud.platform_chassis = MockChassis()
        daemon_psud.psu_status_dict[1] = psu_status
        expected_fvp = psud.swsscommon.FieldValuePairs([('led_status', MockPsu.STATUS_LED_COLOR_OFF)])
        daemon_psud._update_led_color()
        assert daemon_psud.psu_tbl.set.call_count == 1
        daemon_psud.psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(1), expected_fvp)
        assert daemon_psud._update_psu_fan_led_status.call_count == 1
        daemon_psud._update_psu_fan_led_status.assert_called_with(mock_psu, 1)

        daemon_psud.psu_tbl.reset_mock()
        daemon_psud._update_psu_fan_led_status.reset_mock()

        mock_psu.set_status_led(MockPsu.STATUS_LED_COLOR_GREEN)
        expected_fvp = psud.swsscommon.FieldValuePairs([('led_status', MockPsu.STATUS_LED_COLOR_GREEN)])
        daemon_psud._update_led_color()
        assert daemon_psud.psu_tbl.set.call_count == 1
        daemon_psud.psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(1), expected_fvp)
        assert daemon_psud._update_psu_fan_led_status.call_count == 1
        daemon_psud._update_psu_fan_led_status.assert_called_with(mock_psu, 1)

        daemon_psud.psu_tbl.reset_mock()
        daemon_psud._update_psu_fan_led_status.reset_mock()

        mock_psu.set_status_led(MockPsu.STATUS_LED_COLOR_RED)
        expected_fvp = psud.swsscommon.FieldValuePairs([('led_status', MockPsu.STATUS_LED_COLOR_RED)])
        daemon_psud._update_led_color()
        assert daemon_psud.psu_tbl.set.call_count == 1
        daemon_psud.psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(1), expected_fvp)
        assert daemon_psud._update_psu_fan_led_status.call_count == 1
        daemon_psud._update_psu_fan_led_status.assert_called_with(mock_psu, 1)

        daemon_psud.psu_tbl.reset_mock()
        daemon_psud._update_psu_fan_led_status.reset_mock()

        # Test exception handling
        mock_psu.get_status_led = mock.Mock(side_effect=NotImplementedError)
        expected_fvp = psud.swsscommon.FieldValuePairs([('led_status', psud.NOT_AVAILABLE)])
        daemon_psud._update_led_color()
        assert daemon_psud.psu_tbl.set.call_count == 1
        daemon_psud.psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(1), expected_fvp)
        assert daemon_psud._update_psu_fan_led_status.call_count == 1
        daemon_psud._update_psu_fan_led_status.assert_called_with(mock_psu, 1)

    def test_update_psu_fan_led_status(self):
        mock_fan = MockFan("PSU 1 Test Fan 1", MockFan.FAN_DIRECTION_INTAKE)
        mock_psu = MockPsu("PSU 1", 0, True, True)
        mock_psu._fan_list = [mock_fan]
        mock_logger = mock.MagicMock()

        psud.platform_chassis = MockChassis()

        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)
        daemon_psud.fan_tbl = mock.MagicMock()

        expected_fvp = psud.swsscommon.FieldValuePairs([(psud.FAN_INFO_LED_STATUS_FIELD, MockFan.STATUS_LED_COLOR_OFF)])
        daemon_psud._update_psu_fan_led_status(mock_psu, 1)
        assert daemon_psud.fan_tbl.set.call_count == 1
        daemon_psud.fan_tbl.set.assert_called_with("PSU 1 Test Fan 1", expected_fvp)

        daemon_psud.fan_tbl.set.reset_mock()

        # Test Fan.get_status_led not implemented
        mock_fan.get_status_led = mock.Mock(side_effect=NotImplementedError)
        expected_fvp = psud.swsscommon.FieldValuePairs([(psud.FAN_INFO_LED_STATUS_FIELD, psud.NOT_AVAILABLE)])
        daemon_psud._update_psu_fan_led_status(mock_psu, 1)
        assert daemon_psud.fan_tbl.set.call_count == 1
        daemon_psud.fan_tbl.set.assert_called_with("PSU 1 Test Fan 1", expected_fvp)

        daemon_psud.fan_tbl.set.reset_mock()

        # Test Fan.get_name not implemented
        mock_fan.get_name = mock.Mock(side_effect=NotImplementedError)
        daemon_psud._update_psu_fan_led_status(mock_psu, 1)
        assert daemon_psud.fan_tbl.set.call_count == 1
        daemon_psud.fan_tbl.set.assert_called_with("PSU 1 FAN 1", expected_fvp)

    @mock.patch('psud.PsuChassisInfo', mock.MagicMock())
    def test_update_psu_chassis_info(self):
        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)

        # If psud.platform_chassis is None, update_psu_chassis_info() should do nothing
        psud.platform_chassis = None
        daemon_psud.psu_chassis_info = None
        daemon_psud.update_psu_chassis_info()
        assert daemon_psud.psu_chassis_info is None

        # Now we mock platform_chassis, so that daemon_psud.psu_chassis_info should be instantiated and run_power_budget() should be called
        psud.platform_chassis = MockChassis()
        daemon_psud.update_psu_chassis_info()
        assert daemon_psud.psu_chassis_info is not None
        assert daemon_psud.psu_chassis_info.run_power_budget.call_count == 1

    def test_update_psu_entity_info(self):
        mock_psu1 = MockPsu("PSU 1", 0, True, True)
        mock_psu2 = MockPsu("PSU 2", 1, True, True)

        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)
        daemon_psud._update_single_psu_entity_info = mock.MagicMock()

        # If psud.platform_chassis is None, _update_psu_entity_info() should do nothing
        psud.platform_chassis = None
        daemon_psud._update_psu_entity_info()
        assert daemon_psud._update_single_psu_entity_info.call_count == 0

        psud.platform_chassis = MockChassis()
        psud.platform_chassis._psu_list = [mock_psu1]
        daemon_psud._update_psu_entity_info()
        assert daemon_psud._update_single_psu_entity_info.call_count == 1
        daemon_psud._update_single_psu_entity_info.assert_called_with(1, mock_psu1)

        daemon_psud._update_single_psu_entity_info.reset_mock()
        psud.platform_chassis._psu_list = [mock_psu1, mock_psu2]
        daemon_psud._update_psu_entity_info()
        assert daemon_psud._update_single_psu_entity_info.call_count == 2
        expected_calls = [mock.call(1, mock_psu1), mock.call(2, mock_psu2)]
        assert daemon_psud._update_single_psu_entity_info.mock_calls == expected_calls

        # Test behavior if _update_single_psu_entity_info raises an exception
        daemon_psud._update_single_psu_entity_info.reset_mock()
        daemon_psud._update_single_psu_entity_info.side_effect = Exception("Test message")
        daemon_psud.log_warning = mock.MagicMock()
        psud.platform_chassis._psu_list = [mock_psu1]
        daemon_psud._update_psu_entity_info()
        assert daemon_psud._update_single_psu_entity_info.call_count == 1
        daemon_psud._update_single_psu_entity_info.assert_called_with(1, mock_psu1)
        assert daemon_psud.log_warning.call_count == 1
        daemon_psud.log_warning.assert_called_with("Failed to update PSU data - Test message")

    @mock.patch('psud.try_get', mock.MagicMock(return_value=0))
    def test_update_single_psu_entity_info(self):
        mock_psu1 = MockPsu("PSU 1", 0, True, True)

        expected_fvp = psud.swsscommon.FieldValuePairs(
            [('position_in_parent', '0'),
             ('parent_name', psud.CHASSIS_INFO_KEY),
             ])

        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)
        daemon_psud.phy_entity_tbl = mock.MagicMock()

        daemon_psud._update_single_psu_entity_info(0, mock_psu1)
        daemon_psud.phy_entity_tbl.set.assert_called_with('PSU 0', expected_fvp)

    @mock.patch('psud.datetime')
    def test_update_psu_fan_data(self, mock_datetime):
        fake_time = datetime.datetime(2021, 1, 1, 12, 34, 56)
        mock_datetime.now.return_value = fake_time

        mock_fan = MockFan("PSU 1 Test Fan 1", MockFan.FAN_DIRECTION_INTAKE)
        mock_psu1 = MockPsu("PSU 1", 0, True, True)
        mock_psu1._fan_list = [mock_fan]
        mock_logger = mock.MagicMock()

        psud.platform_chassis = MockChassis()
        psud.platform_chassis._psu_list = [mock_psu1]

        daemon_psud = psud.DaemonPsud(SYSLOG_IDENTIFIER)
        daemon_psud.fan_tbl = mock.MagicMock()

        expected_fvp = psud.swsscommon.FieldValuePairs(
            [(psud.FAN_INFO_PRESENCE_FIELD, "True"),
             (psud.FAN_INFO_STATUS_FIELD, "True"),
             (psud.FAN_INFO_DIRECTION_FIELD, mock_fan.get_direction()),
             (psud.FAN_INFO_SPEED_FIELD, str(mock_fan.get_speed())),
             (psud.FAN_INFO_TIMESTAMP_FIELD, fake_time.strftime('%Y%m%d %H:%M:%S'))
             ])
        daemon_psud._update_psu_fan_data(mock_psu1, 1)
        assert daemon_psud.fan_tbl.set.call_count == 1
        daemon_psud.fan_tbl.set.assert_called_with("PSU 1 Test Fan 1", expected_fvp)

        daemon_psud.fan_tbl.set.reset_mock()
