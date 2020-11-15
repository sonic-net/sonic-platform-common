import os
import sys
from imp import load_source

from mock import Mock, MagicMock, patch
from sonic_py_common import daemon_base

from .mock_platform import MockChassis, MockPsu, MockFanDrawer, MockModule
from .mock_device_base import DeviceBase

SYSLOG_IDENTIFIER = 'psud_test'
NOT_AVAILABLE = 'N/A'

daemon_base.db_connect = MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)

os.environ["PSUD_UNIT_TESTING"] = "1"
load_source('psud', scripts_path + '/psud')
from psud import *

CHASSIS_INFO_TABLE = 'CHASSIS_INFO'
CHASSIS_INFO_KEY_TEMPLATE = 'chassis {}'

CHASSIS_INFO_POWER_CONSUMER_FIELD = 'Consumed Power {}'
CHASSIS_INFO_POWER_SUPPLIER_FIELD = 'Supplied Power {}'
CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD = 'Total Consumed Power'
CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD = 'Total Supplied Power'
CHASSIS_INFO_POWER_KEY_TEMPLATE = 'chassis_power_budget {}'

def setup_function():
    PsuChassisInfo.log_notice = MagicMock()
    PsuChassisInfo.log_warning = MagicMock()


def teardown_function():
    PsuChassisInfo.log_notice.reset()
    PsuChassisInfo.log_warning.reset()

#Test cases to cover functionality in PsuChassisInfo class
def test_psuchassis_check_psu_supplied_power():
    chassis = MockChassis()
    psu1 = MockPsu(True, True, "PSU 1")
    psu1_power = 510.0
    psu1.set_maximum_supplied_power(psu1_power)
    chassis.psu_list.append(psu1)

    psu2 = MockPsu(True, True, "PSU 2")
    psu2_power = 800.0
    psu2.set_maximum_supplied_power(psu2_power)
    chassis.psu_list.append(psu2)

    psu3 = MockPsu(True, True, "PSU 3")
    psu3_power = 350.0
    psu3.set_maximum_supplied_power(psu3_power)
    chassis.psu_list.append(psu3)

    total_power = psu1_power + psu2_power + psu3_power
    state_db = daemon_base.db_connect("STATE_DB")
    chassis_tbl = swsscommon.Table(state_db, CHASSIS_INFO_TABLE)
    chassis_info = PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)
    chassis_info.run_power_budget(chassis_tbl)
    fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))

    #Check if supplied power is recorded in DB
    assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD])

    #Check if psu1 is not present
    psu1.set_presence(False)
    total_power = psu2_power + psu3_power
    chassis_info.run_power_budget(chassis_tbl)
    fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))
    assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD])

    #Check if psu2 status is NOT_OK
    psu2.set_status(False)
    total_power = psu3_power
    chassis_info.run_power_budget(chassis_tbl)
    fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))
    assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD])

def test_psuchassis_check_consumed_power():
    chassis = MockChassis()
    fan_drawer1 = MockFanDrawer(True, True, "FanDrawer 1")
    fan_drawer1_power = 510.0
    fan_drawer1.set_maximum_consumed_power(fan_drawer1_power)
    chassis.fan_drawer_list.append(fan_drawer1)

    module1 = MockFanDrawer(True, True, "Module 1")
    module1_power = 700.0
    module1.set_maximum_consumed_power(module1_power)
    chassis.module_list.append(module1)

    total_power = fan_drawer1_power + module1_power
    state_db = daemon_base.db_connect("STATE_DB")
    chassis_tbl = swsscommon.Table(state_db, CHASSIS_INFO_TABLE)
    chassis_info = PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)
    chassis_info.run_power_budget(chassis_tbl)
    fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))

    #Check if supplied power is recorded in DB
    assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])

    #Check if fan_drawer1 present
    fan_drawer1.set_presence(False)
    total_power = module1_power
    chassis_info.run_power_budget(chassis_tbl)
    fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))
    assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])

    #Check if module1 present
    fan_drawer1.set_presence(True)
    module1.set_presence(False)
    total_power = fan_drawer1_power
    chassis_info.run_power_budget(chassis_tbl)
    fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))
    assert total_power == float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])

def test_psuchassis_check_power_budget():
    chassis = MockChassis()
    psu = MockPsu(True, True, "PSU 1")
    psu1_power = 510.0
    psu.set_maximum_supplied_power(psu1_power)
    chassis.psu_list.append(psu)

    fan_drawer1 = MockFanDrawer(True, True, "FanDrawer 1")
    fan_drawer1_power = 510.0
    fan_drawer1.set_maximum_consumed_power(fan_drawer1_power)
    chassis.fan_drawer_list.append(fan_drawer1)

    module1 = MockFanDrawer(True, True, "Module 1")
    module1_power = 700.0
    module1.set_maximum_consumed_power(module1_power)
    chassis.module_list.append(module1)

    state_db = daemon_base.db_connect("STATE_DB")
    chassis_tbl = swsscommon.Table(state_db, CHASSIS_INFO_TABLE)
    chassis_info = PsuChassisInfo(SYSLOG_IDENTIFIER, chassis)

    #Check if supplied_power < consumed_power
    chassis_info.run_power_budget(chassis_tbl)
    if chassis_info.update_master_status():
        chassis_info._set_psu_master_led(chassis_info.master_status_good)
    fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))

    assert float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD]) < float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])
    assert chassis_info.master_status_good == False
    assert MockPsu.get_status_master_led() == DeviceBase.STATUS_LED_COLOR_RED

    #Add a PSU
    psu = MockPsu(True, True, "PSU 2")
    psu2_power = 800.0
    psu.set_maximum_supplied_power(psu2_power)
    chassis.psu_list.append(psu)

    #Check if supplied_power > consumed_power
    chassis_info.run_power_budget(chassis_tbl)
    if chassis_info.update_master_status():
        chassis_info._set_psu_master_led(chassis_info.master_status_good)
    fvs = chassis_tbl.get(CHASSIS_INFO_POWER_KEY_TEMPLATE.format(1))

    assert float(fvs[CHASSIS_INFO_TOTAL_POWER_SUPPLIED_FIELD]) > float(fvs[CHASSIS_INFO_TOTAL_POWER_CONSUMED_FIELD])
    assert chassis_info.master_status_good == True
    assert MockPsu.get_status_master_led() == DeviceBase.STATUS_LED_COLOR_GREEN
