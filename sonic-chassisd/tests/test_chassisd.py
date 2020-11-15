import os
import sys
from imp import load_source

from mock import Mock, MagicMock, patch
from sonic_py_common import daemon_base

from .mock_platform import MockChassis, MockModule
from .mock_module_base import ModuleBase

SYSLOG_IDENTIFIER = 'chassisd_test'
NOT_AVAILABLE = 'N/A'

daemon_base.db_connect = MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)

os.environ["CHASSISD_UNIT_TESTING"] = "1"
load_source('chassisd', scripts_path + '/chassisd')
from chassisd import *


CHASSIS_MODULE_INFO_NAME_FIELD = 'name'
CHASSIS_MODULE_INFO_DESC_FIELD = 'desc'
CHASSIS_MODULE_INFO_SLOT_FIELD = 'slot'
CHASSIS_MODULE_INFO_OPERSTATUS_FIELD = 'oper_status'

CHASSIS_INFO_KEY_TEMPLATE = 'CHASSIS {}'
CHASSIS_INFO_CARD_NUM_FIELD = 'module_num'

def setup_function():
    ModuleUpdater.log_notice = MagicMock()
    ModuleUpdater.log_warning = MagicMock()


def teardown_function():
    ModuleUpdater.log_notice.reset()
    ModuleUpdater.log_warning.reset()


def test_moduleupdater_check_valid_fields():
    chassis = MockChassis()
    index = 0
    name = "FABRIC-CARD0"
    desc = "Switch Fabric Module"
    slot = 10
    module_type = ModuleBase.MODULE_TYPE_FABRIC
    module = MockModule(index, name, desc, module_type, slot)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_ONLINE
    module.set_oper_status(status)

    chassis.module_list.append(module)

    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis)
    module_updater.module_db_update()
    fvs = module_updater.module_table.get(name)
    assert desc == fvs[CHASSIS_MODULE_INFO_DESC_FIELD]
    assert slot == int(fvs[CHASSIS_MODULE_INFO_SLOT_FIELD])
    assert status == fvs[CHASSIS_MODULE_INFO_OPERSTATUS_FIELD]

def test_moduleupdater_check_invalid_name():
    chassis = MockChassis()
    index = 0
    name = "TEST-CARD0"
    desc = "36 port 400G card"
    slot = 2
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_PRESENT
    module.set_oper_status(status)

    chassis.module_list.append(module)

    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis)
    module_updater.module_db_update()
    fvs = module_updater.module_table.get(name)
    assert fvs == None

def test_moduleupdater_check_status_update():
    chassis = MockChassis()
    index = 0
    name = "LINE-CARD0"
    desc = "36 port 400G card"
    slot = 1
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_ONLINE
    module.set_oper_status(status)
    chassis.module_list.append(module)

    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis)
    module_updater.module_db_update()
    fvs = module_updater.module_table.get(name)
    print('Initial DB-entry {}'.format(fvs))
    assert status == fvs[CHASSIS_MODULE_INFO_OPERSTATUS_FIELD]

    # Update status
    status = ModuleBase.MODULE_STATUS_OFFLINE
    module.set_oper_status(status)
    fvs = module_updater.module_table.get(name)
    print('Not updated DB-entry {}'.format(fvs))
    assert status != fvs[CHASSIS_MODULE_INFO_OPERSTATUS_FIELD]

    # Update status and db
    module_updater.module_db_update()
    fvs = module_updater.module_table.get(name)
    print('Updated DB-entry {}'.format(fvs))
    assert status == fvs[CHASSIS_MODULE_INFO_OPERSTATUS_FIELD]

def test_moduleupdater_check_deinit():
    chassis = MockChassis()
    index = 0
    name = "LINE-CARD0"
    desc = "36 port 400G card"
    slot = 1
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_ONLINE
    module.set_oper_status(status)
    chassis.module_list.append(module)

    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis)
    module_updater.modules_num_update()
    module_updater.module_db_update()
    fvs = module_updater.module_table.get(name)
    assert status == fvs[CHASSIS_MODULE_INFO_OPERSTATUS_FIELD]

    module_table = module_updater.module_table
    module_updater.deinit()
    fvs = module_table.get(name)
    assert fvs == None

def test_configupdater_check_valid_names():
    chassis = MockChassis()
    index = 0
    name = "TEST-CARD0"
    desc = "36 port 400G card"
    slot = 1
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_ONLINE
    module.set_oper_status(status)
    chassis.module_list.append(module)

    config_updater = ModuleConfigUpdater(SYSLOG_IDENTIFIER, chassis)
    admin_state = 0
    config_updater.module_config_update(name, admin_state)

    # No change since invalid key
    assert module.get_admin_state() != admin_state

def test_configupdater_check_valid_index():
    chassis = MockChassis()
    index = -1
    name = "LINE-CARD0"
    desc = "36 port 400G card"
    slot = 1
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_ONLINE
    module.set_oper_status(status)
    chassis.module_list.append(module)

    config_updater = ModuleConfigUpdater(SYSLOG_IDENTIFIER, chassis)
    admin_state = 0
    config_updater.module_config_update(name, admin_state)

    # No change since invalid index
    assert module.get_admin_state() != admin_state

def test_configupdater_check_admin_state():
    chassis = MockChassis()
    index = 0
    name = "LINE-CARD0"
    desc = "36 port 400G card"
    slot = 1
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_ONLINE
    module.set_oper_status(status)
    chassis.module_list.append(module)

    config_updater = ModuleConfigUpdater(SYSLOG_IDENTIFIER, chassis)
    admin_state = 0
    config_updater.module_config_update(name, admin_state)
    assert module.get_admin_state() == admin_state

    admin_state = 1
    config_updater.module_config_update(name, admin_state)
    assert module.get_admin_state() == admin_state

def test_configupdater_check_num_modules():
    chassis = MockChassis()
    index = 0
    name = "LINE-CARD0"
    desc = "36 port 400G card"
    slot = 1
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot)

    # No modules
    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis)
    module_updater.modules_num_update()
    fvs = module_updater.chassis_table.get(CHASSIS_INFO_KEY_TEMPLATE.format(1))
    assert fvs == None

    # Add a module
    chassis.module_list.append(module)
    module_updater.modules_num_update()
    fvs = module_updater.chassis_table.get(CHASSIS_INFO_KEY_TEMPLATE.format(1))
    assert chassis.get_num_modules() == int(fvs[CHASSIS_INFO_CARD_NUM_FIELD])

    module_updater.deinit()
    fvs = module_updater.chassis_table.get(CHASSIS_INFO_KEY_TEMPLATE.format(1))
    assert fvs == None
