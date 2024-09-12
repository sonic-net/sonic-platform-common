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

from .mock_platform import MockChassis, MockPsu, MockFanDrawer, MockModule

SYSLOG_IDENTIFIER = 'test_PsuChassisInfo'
NOT_AVAILABLE = 'N/A'

daemon_base.db_connect = mock.MagicMock()

tests_path = os.path.dirname(os.path.abspath(__file__))

# Add mocked_libs path so that the file under test can load mocked modules from there
mocked_libs_path = os.path.join(tests_path, "mocked_libs")
sys.path.insert(0, mocked_libs_path)

# We also need to load the mocked swsscommon locally for use below
load_source('swsscommon', os.path.join(mocked_libs_path, 'swsscommon', 'swsscommon.py'))
import swsscommon as mock_swsscommon

# Add path to the file under test so that we can load it
modules_path = os.path.dirname(tests_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)
load_source('psud', os.path.join(scripts_path, 'psud'))
import psud


CHASSIS_INFO_TABLE = 'CHASSIS_INFO'
CHASSIS_INFO_KEY_TEMPLATE = 'chassis {}'

CHASSIS_INFO_POWER_CONSUMER_FIELD = 'Consumed Power {}'
CHASSIS_INFO_POWER_SUPPLIER_FIELD = 'Supplied Power {}'
CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD = 'Total Consumed Power'
CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD = 'Total Supplied Power'
CHASSIS_INFO_POWER_KEY_TEMPLATE = 'chassis_power_budget {}'


@pytest.fixture(scope="class")
def mock_log_methods():
    psud.PsuChassisInfo.log_notice = mock.MagicMock()
    psud.PsuChassisInfo.log_warning = mock.MagicMock()
    yield
    psud.PsuChassisInfo.log_notice.reset()
    psud.PsuChassisInfo.log_warning.reset()


@pytest.mark.usefixtures("mock_log_methods")
class TestPsuChassisInfo(object):
    """
    Test cases to cover functionality in PsuChassisInfo class
    """

    def test_update_master_status(self):
        chassis = MockChassis()
        chassis_info = psud.PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)

        # With first_run set as True
        # Test good values while in bad state
        chassis_info.total_supplied_power = 510.0
        chassis_info.total_consumed_power = 350.0
        chassis_info.master_status_good = False
        ret = chassis_info.update_master_status()
        assert ret == True
        assert chassis_info.master_status_good == True

        # Test good values while in good state
        ret = chassis_info.update_master_status()
        assert ret == False
        assert chassis_info.master_status_good == True

        # Test unknown total_supplied_power (0.0)
        chassis_info.total_supplied_power = 0.0
        chassis_info.master_status_good = False
        ret = chassis_info.update_master_status()
        assert ret == False
        assert chassis_info.master_status_good == False

        # Test bad values while in good state
        chassis_info.total_supplied_power = 300.0
        chassis_info.total_consumed_power = 350.0
        chassis_info.master_status_good = True
        ret = chassis_info.update_master_status()
        assert ret == True
        assert chassis_info.master_status_good == False

        # With first_run set as False
        chassis_info.first_run = False

        # Test good values while in bad state
        chassis_info.total_supplied_power = 510.0
        chassis_info.total_consumed_power = 350.0
        chassis_info.master_status_good = False
        ret = chassis_info.update_master_status()
        assert ret == True
        assert chassis_info.master_status_good == True

        # Test good values while in good state
        ret = chassis_info.update_master_status()
        assert ret == False
        assert chassis_info.master_status_good == True

        # Test unknown total_supplied_power (0.0)
        chassis_info.total_supplied_power = 0.0
        chassis_info.master_status_good = True
        ret = chassis_info.update_master_status()
        assert ret == False
        assert chassis_info.master_status_good == True

        # Test unknown total_consumed_power (0.0)
        chassis_info.total_supplied_power = 510.0
        chassis_info.total_consumed_power = 0.0
        chassis_info.master_status_good = False
        ret = chassis_info.update_master_status()
        assert ret == False
        assert chassis_info.master_status_good == False

        # Test bad values while in good state
        chassis_info.total_supplied_power = 300.0
        chassis_info.total_consumed_power = 350.0
        chassis_info.master_status_good = True
        ret = chassis_info.update_master_status()
        assert ret == True
        assert chassis_info.master_status_good == False

        # Test bad values while in good state
        ret = chassis_info.update_master_status()
        assert ret == False
        assert chassis_info.master_status_good == False


    def test_supplied_power(self):
        chassis = MockChassis()
        psu1 = MockPsu("PSU 1", 0, True, True)
        psu1_power = 510.0
        psu1.set_maximum_supplied_power(psu1_power)
        chassis._psu_list.append(psu1)

        psu2 = MockPsu("PSU 2", 1, True, True)
        psu2_power = 800.0
        psu2.set_maximum_supplied_power(psu2_power)
        chassis._psu_list.append(psu2)

        psu3 = MockPsu("PSU 3", 2, True, True)
        psu3_power = 350.0
        psu3.set_maximum_supplied_power(psu3_power)
        chassis._psu_list.append(psu3)

        total_power = psu1_power + psu2_power + psu3_power
        state_db = daemon_base.db_connect("STATE_DB")
        chassis_tbl = mock_swsscommon.Table(state_db, CHASSIS_INFO_TABLE)
        chassis_info = psud.PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)
        chassis_info.run_power_budget(chassis_tbl)
        fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))

        # Check if supplied power is recorded in DB
        assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD])

        # Check if psu1 is not present
        psu1.set_presence(False)
        total_power = psu2_power + psu3_power
        chassis_info.run_power_budget(chassis_tbl)
        fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))
        assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD])

        # Check if psu2 status is NOT_OK
        psu2.set_status(False)
        total_power = psu3_power
        chassis_info.run_power_budget(chassis_tbl)
        fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))
        assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD])

    def test_consumed_power(self):
        chassis = MockChassis()
        fan_drawer1 = MockFanDrawer("FanDrawer 1", 0, True, True)
        fan_drawer1_power = 510.0
        fan_drawer1.set_maximum_consumed_power(fan_drawer1_power)
        chassis._fan_drawer_list.append(fan_drawer1)

        module1 = MockModule("Module 1", 0, True, True)
        module1_power = 700.0
        module1.set_maximum_consumed_power(module1_power)
        chassis._module_list.append(module1)

        total_power = fan_drawer1_power + module1_power
        state_db = daemon_base.db_connect("STATE_DB")
        chassis_tbl = mock_swsscommon.Table(state_db, CHASSIS_INFO_TABLE)
        chassis_info = psud.PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)
        chassis_info.run_power_budget(chassis_tbl)
        fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))

        # Check if supplied power is recorded in DB
        assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])

        # Check if fan_drawer1 present
        fan_drawer1.set_presence(False)
        total_power = module1_power
        chassis_info.run_power_budget(chassis_tbl)
        fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))
        assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])

        # Check if module1 present
        fan_drawer1.set_presence(True)
        module1.set_presence(False)
        total_power = fan_drawer1_power
        chassis_info.run_power_budget(chassis_tbl)
        fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))
        assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])

    def test_power_budget(self):
        chassis = MockChassis()
        psu1 = MockPsu("PSU 1", 0, True, True)
        psu1_power = 510.0
        psu1.set_maximum_supplied_power(psu1_power)
        chassis._psu_list.append(psu1)

        fan_drawer1 = MockFanDrawer("FanDrawer 1", 0, True, True)
        fan_drawer1_power = 510.0
        fan_drawer1.set_maximum_consumed_power(fan_drawer1_power)
        chassis._fan_drawer_list.append(fan_drawer1)

        module1 = MockModule("Module 1", 0, True, True)
        module1_power = 700.0
        module1.set_maximum_consumed_power(module1_power)
        chassis._module_list.append(module1)

        state_db = daemon_base.db_connect("STATE_DB")
        chassis_tbl = mock_swsscommon.Table(state_db, CHASSIS_INFO_TABLE)
        chassis_info = psud.PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)
        chassis_info.first_run = False

        # Check case where supplied_power < consumed_power
        chassis_info.run_power_budget(chassis_tbl)
        chassis_info.update_master_status()
        fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))

        assert float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD]) < float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])
        assert chassis_info.master_status_good == False

        # We cannot call get_status_master_led() on our mocked PSUs, because
        # they are not instantiated from the same Psu class loaded in psud,
        # so we must call it on the class there.
        assert psud.Psu.get_status_master_led() == MockPsu.STATUS_LED_COLOR_RED

        # Add a PSU
        psu2 = MockPsu("PSU 2", 1, True, True)
        psu2_power = 800.0
        psu2.set_maximum_supplied_power(psu2_power)
        chassis._psu_list.append(psu2)

        # Check case where supplied_power > consumed_power
        chassis_info.run_power_budget(chassis_tbl)
        chassis_info.update_master_status()
        fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))

        assert float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD]) > float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])
        assert chassis_info.master_status_good == True

        # We cannot call get_status_master_led() on our mocked PSUs, because
        # they are not instantiated from the same Psu class loaded in psud,
        # so we must call it on the class there.
        assert psud.Psu.get_status_master_led() == MockPsu.STATUS_LED_COLOR_GREEN

    def test_first_run(self):
        chassis = MockChassis()
        chassis_info = psud.PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)

        chassis_info.total_supplied_power = 0.0
        chassis_info.total_consumed_power = 350.0
        chassis_info.master_status_good = False
        ret = chassis_info.update_master_status()
        assert ret == True
        assert psud.Psu.get_status_master_led() == MockPsu.STATUS_LED_COLOR_RED

        # first time with good power usage
        chassis_info = psud.PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)
        chassis_info.total_supplied_power = 510.0
        chassis_info.total_consumed_power = 350.0
        ret = chassis_info.update_master_status()
        assert ret == True
        assert psud.Psu.get_status_master_led() == MockPsu.STATUS_LED_COLOR_GREEN

        chassis_info = psud.PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)
        chassis_info.total_supplied_power = 510.0
        chassis_info.total_consumed_power = 350.0
        chassis_info.master_status_good = True
        ret = chassis_info.update_master_status()
        assert ret == True
        assert psud.Psu.get_status_master_led() == MockPsu.STATUS_LED_COLOR_GREEN

    def test_get_psu_key(self):
        assert psud.get_psu_key(0) == psud.PSU_INFO_KEY_TEMPLATE.format(0)
        assert psud.get_psu_key(1) == psud.PSU_INFO_KEY_TEMPLATE.format(1)

    def test_try_get(self):
        # Test a proper, working callback
        GOOD_CALLBACK_RETURN_VALUE = "This is a test"

        def callback1():
            return GOOD_CALLBACK_RETURN_VALUE

        ret = psud.try_get(callback1)
        assert ret == GOOD_CALLBACK_RETURN_VALUE

        # Ensure try_get returns default value if callback returns None
        DEFAULT_VALUE = "Default value"

        def callback2():
            return None

        ret = psud.try_get(callback2, default=DEFAULT_VALUE)
        assert ret == DEFAULT_VALUE

        # Ensure try_get returns default value if callback returns None
        def callback3():
            raise NotImplementedError

        ret = psud.try_get(callback3, default=DEFAULT_VALUE)
        assert ret == DEFAULT_VALUE
