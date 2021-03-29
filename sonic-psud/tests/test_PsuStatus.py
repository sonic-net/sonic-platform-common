import os
import sys
from imp import load_source  # Replace with importlib once we no longer need to support Python 2

# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

from .mock_platform import MockPsu

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


class TestPsuStatus(object):
    """
    Test cases to cover functionality of PsuStatus class
    """

    def test_set_presence(self):
        mock_logger = mock.MagicMock()
        mock_psu = MockPsu("PSU 1", 0, True, True)

        psu_status = psud.PsuStatus(mock_logger, mock_psu)
        assert psu_status.presence == False

        # Test toggling presence to True
        ret = psu_status.set_presence(True)
        assert ret == True
        assert psu_status.presence == True

        # Test toggling presence to False
        ret = psu_status.set_presence(False)
        assert ret == True
        assert psu_status.presence == False

        # Test attempting to set presence to the same as the current value
        ret = psu_status.set_presence(False)
        assert ret == False
        assert psu_status.presence == False

    def test_set_power_good(self):
        mock_logger = mock.MagicMock()
        mock_psu = MockPsu("PSU 1", 0, True, True)

        psu_status = psud.PsuStatus(mock_logger, mock_psu)
        assert psu_status.power_good == False

        # Test toggling power_good to True
        ret = psu_status.set_power_good(True)
        assert ret == True
        assert psu_status.power_good == True

        # Test attempting to set power_good to the same as the current value (return value should be False)
        ret = psu_status.set_power_good(True)
        assert ret == False
        assert psu_status.power_good == True

        # Test toggling power_good to False
        ret = psu_status.set_power_good(False)
        assert ret == True
        assert psu_status.power_good == False

        # Test attempting to set power_good to the same as the current value (return value should be False)
        ret = psu_status.set_power_good(False)
        assert ret == False
        assert psu_status.power_good == False

    def test_set_voltage(self):
        mock_logger = mock.MagicMock()
        mock_psu = MockPsu("PSU 1", 0, True, True)

        psu_status = psud.PsuStatus(mock_logger, mock_psu)
        assert psu_status.voltage_good == False

        # Pass in a good voltage
        ret = psu_status.set_voltage(12.0, 12.5, 11.5)
        assert ret == True
        assert psu_status.voltage_good == True

        # Pass in a another good voltage successively (return value should be False)
        ret = psu_status.set_voltage(11.9, 12.5, 11.5)
        assert ret == False
        assert psu_status.voltage_good == True

        # Pass in a high voltage
        ret = psu_status.set_voltage(12.6, 12.5, 11.5)
        assert ret == True
        assert psu_status.voltage_good == False

        # Pass in a another bad voltage successively (return value should be False)
        ret = psu_status.set_voltage(12.7, 12.5, 11.5)
        assert ret == False
        assert psu_status.voltage_good == False

        # Pass in a good (high edge case) voltage
        ret = psu_status.set_voltage(12.5, 12.5, 11.5)
        assert ret == True
        assert psu_status.voltage_good == True

        # Pass in a low voltage
        ret = psu_status.set_voltage(11.4, 12.5, 11.5)
        assert ret == True
        assert psu_status.voltage_good == False

        # Pass in a good (low edge case) voltage
        ret = psu_status.set_voltage(11.5, 12.5, 11.5)
        assert ret == True
        assert psu_status.voltage_good == True

        # Test passing parameters as None when voltage_good == True
        ret = psu_status.set_voltage(None, 12.5, 11.5)
        assert ret == False
        assert psu_status.voltage_good == True
        ret = psu_status.set_voltage(11.5, None, 11.5)
        assert ret == False
        assert psu_status.voltage_good == True
        ret = psu_status.set_voltage(11.5, 12.5, None)
        assert ret == False
        assert psu_status.voltage_good == True

        # Test passing parameters as None when voltage_good == False
        psu_status.voltage_good = False
        ret = psu_status.set_voltage(None, 12.5, 11.5)
        assert ret == False
        assert psu_status.voltage_good == True
        psu_status.voltage_good = False
        ret = psu_status.set_voltage(11.5, None, 11.5)
        assert ret == False
        assert psu_status.voltage_good == True
        psu_status.voltage_good = False
        ret = psu_status.set_voltage(11.5, 12.5, None)
        assert ret == False
        assert psu_status.voltage_good == True

    def test_set_temperature(self):
        mock_logger = mock.MagicMock()
        mock_psu = MockPsu("PSU 1", 0, True, True)

        psu_status = psud.PsuStatus(mock_logger, mock_psu)
        assert psu_status.temperature_good == False

        # Pass in a good temperature
        ret = psu_status.set_temperature(20.123, 50.0)
        assert ret == True
        assert psu_status.temperature_good == True

        # Pass in a another good temperature successively (return value should be False)
        ret = psu_status.set_temperature(31.456, 50.0)
        assert ret == False
        assert psu_status.temperature_good == True

        # Pass in a high temperature
        ret = psu_status.set_temperature(50.001, 50.0)
        assert ret == True
        assert psu_status.temperature_good == False

        # Pass in a another bad temperature successively (return value should be False)
        ret = psu_status.set_temperature(50.0, 50.0)
        assert ret == False
        assert psu_status.temperature_good == False

        # Pass in a good (high edge case) temperature
        ret = psu_status.set_temperature(49.999, 50.0)
        assert ret == True
        assert psu_status.temperature_good == True

        # Test passing parameters as None when temperature_good == True
        ret = psu_status.set_temperature(None, 50.0)
        assert ret == False
        assert psu_status.temperature_good == True
        ret = psu_status.set_temperature(20.123, None)
        assert ret == False
        assert psu_status.temperature_good == True

        # Test passing parameters as None when temperature_good == False
        psu_status.temperature_good = False
        ret = psu_status.set_temperature(None, 50.0)
        assert ret == False
        assert psu_status.temperature_good == True
        psu_status.temperature_good = False
        ret = psu_status.set_temperature(20.123, None)
        assert ret == False
        assert psu_status.temperature_good == True

    def test_is_ok(self):
        mock_logger = mock.MagicMock()
        mock_psu = MockPsu("PSU 1", 0, True, True)

        psu_status = psud.PsuStatus(mock_logger, mock_psu)
        psu_status.presence = True
        psu_status.power_good = True
        psu_status.voltage_good = True
        psu_status.temperature_good = True
        ret = psu_status.is_ok()
        assert ret == True

        psu_status.presence = False
        ret = psu_status.is_ok()
        assert ret == False

        psu_status.presence = True
        ret = psu_status.is_ok()
        assert ret == True

        psu_status.power_good = False
        ret = psu_status.is_ok()
        assert ret == False

        psu_status.power_good = True
        ret = psu_status.is_ok()
        assert ret == True

        psu_status.voltage_good = False
        ret = psu_status.is_ok()
        assert ret == False

        psu_status.voltage_good = True
        ret = psu_status.is_ok()
        assert ret == True

        psu_status.temperature_good = False
        ret = psu_status.is_ok()
        assert ret == False

        psu_status.temperature_good = True
        ret = psu_status.is_ok()
        assert ret == True
