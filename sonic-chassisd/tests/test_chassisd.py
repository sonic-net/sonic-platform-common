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

# Add mocked_libs path so that the file under test can load mocked modules from there
mocked_libs_path = os.path.join(test_path, 'mocked_libs')
sys.path.insert(0, mocked_libs_path)

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
CHASSIS_MODULE_INFO_SERIAL_FIELD = 'serial'

CHASSIS_INFO_KEY_TEMPLATE = 'CHASSIS {}'
CHASSIS_INFO_CARD_NUM_FIELD = 'module_num'

CHASSIS_ASIC_PCI_ADDRESS_FIELD = 'asic_pci_address'
CHASSIS_ASIC_ID_IN_MODULE_FIELD = 'asic_id_in_module'

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
    serial = "FC1000101"
    module_type = ModuleBase.MODULE_TYPE_FABRIC
    module = MockModule(index, name, desc, module_type, slot, serial)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_ONLINE
    module.set_oper_status(status)

    chassis.module_list.append(module)

    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis, slot,
                                   module.supervisor_slot)
    module_updater.module_db_update()
    fvs = module_updater.module_table.get(name)
    assert desc == fvs[CHASSIS_MODULE_INFO_DESC_FIELD]
    assert slot == int(fvs[CHASSIS_MODULE_INFO_SLOT_FIELD])
    assert status == fvs[CHASSIS_MODULE_INFO_OPERSTATUS_FIELD]
    assert serial == fvs[CHASSIS_MODULE_INFO_SERIAL_FIELD]


def test_moduleupdater_check_invalid_name():
    chassis = MockChassis()
    index = 0
    name = "TEST-CARD0"
    desc = "36 port 400G card"
    slot = 2
    serial = "TS1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_PRESENT
    module.set_oper_status(status)

    chassis.module_list.append(module)

    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis, slot,
                                   module.supervisor_slot)
    module_updater.module_db_update()
    fvs = module_updater.module_table.get(name)
    assert fvs == None


def test_moduleupdater_check_status_update():
    chassis = MockChassis()
    index = 0
    name = "LINE-CARD0"
    desc = "36 port 400G card"
    slot = 1
    serial = "LC1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_ONLINE
    module.set_oper_status(status)
    chassis.module_list.append(module)

    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis, slot,
                                   module.supervisor_slot)
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
    serial = "LC1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)

    # Set initial state
    status = ModuleBase.MODULE_STATUS_ONLINE
    module.set_oper_status(status)
    chassis.module_list.append(module)

    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis, slot,
                                   module.supervisor_slot)
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
    serial = "TC1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)

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
    serial = "LC1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)

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
    serial = "LC1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)

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
    serial = "LC1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)

    # No modules
    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis, slot,
                                   module.supervisor_slot)
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

def test_midplane_presence_modules():
    chassis = MockChassis()

    #Supervisor
    index = 0
    name = "SUPERVISOR0"
    desc = "Supervisor card"
    slot = 16
    serial = "RP1000101"
    module_type = ModuleBase.MODULE_TYPE_SUPERVISOR
    supervisor = MockModule(index, name, desc, module_type, slot, serial)
    supervisor.set_midplane_ip()
    chassis.module_list.append(supervisor)

    #Linecard
    index = 1
    name = "LINE-CARD0"
    desc = "36 port 400G card"
    slot = 1
    serial = "LC1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)
    module.set_midplane_ip()
    chassis.module_list.append(module)

    #Fabric-card
    index = 1
    name = "FABRIC-CARD0"
    desc = "Switch fabric card"
    slot = 17
    serial = "FC1000101"
    module_type = ModuleBase.MODULE_TYPE_FABRIC
    fabric = MockModule(index, name, desc, module_type, slot, serial)
    chassis.module_list.append(fabric)

    #Run on supervisor
    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis, slot,
                                   module.supervisor_slot)
    module_updater.supervisor_slot = supervisor.get_slot()
    module_updater.my_slot = supervisor.get_slot()
    module_updater.modules_num_update()
    module_updater.module_db_update()
    module_updater.check_midplane_reachability()

    midplane_table = module_updater.midplane_table
    #Check only one entry in database
    assert 1 == midplane_table.size()

    #Check fields in database
    name = "LINE-CARD0"
    fvs = midplane_table.get(name)
    assert fvs != None
    assert module.get_midplane_ip() == fvs[CHASSIS_MIDPLANE_INFO_IP_FIELD]
    assert str(module.is_midplane_reachable()) == fvs[CHASSIS_MIDPLANE_INFO_ACCESS_FIELD]

    #Set access of line-card to down
    module.set_midplane_reachable(False)
    module_updater.check_midplane_reachability()
    fvs = midplane_table.get(name)
    assert fvs != None
    assert module.get_midplane_ip() == fvs[CHASSIS_MIDPLANE_INFO_IP_FIELD]
    assert str(module.is_midplane_reachable()) == fvs[CHASSIS_MIDPLANE_INFO_ACCESS_FIELD]

    #Deinit
    module_updater.deinit()
    fvs = midplane_table.get(name)
    assert fvs == None

def test_midplane_presence_supervisor():
    chassis = MockChassis()

    #Supervisor
    index = 0
    name = "SUPERVISOR0"
    desc = "Supervisor card"
    slot = 16
    serial = "RP1000101"
    module_type = ModuleBase.MODULE_TYPE_SUPERVISOR
    supervisor = MockModule(index, name, desc, module_type, slot, serial)
    supervisor.set_midplane_ip()
    chassis.module_list.append(supervisor)

    #Linecard
    index = 1
    name = "LINE-CARD0"
    desc = "36 port 400G card"
    slot = 1
    serial = "LC1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)
    module.set_midplane_ip()
    chassis.module_list.append(module)

    #Fabric-card
    index = 1
    name = "FABRIC-CARD0"
    desc = "Switch fabric card"
    slot = 17
    serial = "FC1000101"
    module_type = ModuleBase.MODULE_TYPE_FABRIC
    fabric = MockModule(index, name, desc, module_type, slot, serial)
    chassis.module_list.append(fabric)

    #Run on supervisor
    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis, slot,
                                   module.supervisor_slot)
    module_updater.supervisor_slot = supervisor.get_slot()
    module_updater.my_slot = module.get_slot()
    module_updater.modules_num_update()
    module_updater.module_db_update()
    module_updater.check_midplane_reachability()

    midplane_table = module_updater.midplane_table
    #Check only one entry in database
    assert 1 == midplane_table.size()

    #Check fields in database
    name = "SUPERVISOR0"
    fvs = midplane_table.get(name)
    assert fvs != None
    assert supervisor.get_midplane_ip() == fvs[CHASSIS_MIDPLANE_INFO_IP_FIELD]
    assert str(supervisor.is_midplane_reachable()) == fvs[CHASSIS_MIDPLANE_INFO_ACCESS_FIELD]

    #Set access of line-card to down
    supervisor.set_midplane_reachable(False)
    module_updater.check_midplane_reachability()
    fvs = midplane_table.get(name)
    assert fvs != None
    assert supervisor.get_midplane_ip() == fvs[CHASSIS_MIDPLANE_INFO_IP_FIELD]
    assert str(supervisor.is_midplane_reachable()) == fvs[CHASSIS_MIDPLANE_INFO_ACCESS_FIELD]

    #Deinit
    module_updater.deinit()
    fvs = midplane_table.get(name)
    assert fvs == None

def test_asic_presence():
    chassis = MockChassis()

    #Supervisor
    index = 0
    name = "SUPERVISOR0"
    desc = "Supervisor card"
    slot = 16
    serial = "RP1000101"
    module_type = ModuleBase.MODULE_TYPE_SUPERVISOR
    supervisor = MockModule(index, name, desc, module_type, slot, serial)
    supervisor.set_midplane_ip()
    chassis.module_list.append(supervisor)

    #Linecard
    index = 1
    name = "LINE-CARD0"
    desc = "36 port 400G card"
    slot = 1
    serial = "LC1000101"
    module_type = ModuleBase.MODULE_TYPE_LINE
    module = MockModule(index, name, desc, module_type, slot, serial)
    module.set_midplane_ip()
    chassis.module_list.append(module)

    #Fabric-card with asics
    index = 1
    name = "FABRIC-CARD0"
    desc = "Switch fabric card"
    slot = 17
    serial = "FC1000101"
    module_type = ModuleBase.MODULE_TYPE_FABRIC
    fabric_asic_list = [("4", "0000:04:00.0"), ("5", "0000:05:00.0")]
    fabric = MockModule(index, name, desc, module_type, slot, serial, fabric_asic_list)
    chassis.module_list.append(fabric)

    #Run on supervisor
    module_updater = ModuleUpdater(SYSLOG_IDENTIFIER, chassis,
                                   module.supervisor_slot,
                                   module.supervisor_slot)
    module_updater.modules_num_update()
    module_updater.module_db_update()
    module_updater.check_midplane_reachability()

    #Asic presence on fabric module
    fabric.set_oper_status(ModuleBase.MODULE_STATUS_ONLINE)
    module_updater.module_db_update()
    fabric_asic_table = module_updater.asic_table
    assert len(fabric_asic_table.getKeys()) == 2

    def verify_fabric_asic(asic_name, asic_pci_address, module_name, asic_id_in_module):
        fvs = fabric_asic_table.get(asic_name)
        assert fvs[CHASSIS_ASIC_PCI_ADDRESS_FIELD] == asic_pci_address
        assert fvs[CHASSIS_MODULE_INFO_NAME_FIELD] == module_name
        assert fvs[CHASSIS_ASIC_ID_IN_MODULE_FIELD] == asic_id_in_module

    verify_fabric_asic("asic4", "0000:04:00.0", name, "0")
    verify_fabric_asic("asic5", "0000:05:00.0", name, "1")

    #Card goes down and asics should be gone
    fabric.set_oper_status(ModuleBase.MODULE_STATUS_OFFLINE)
    module_updater.module_db_update()
    assert len(fabric_asic_table.getKeys()) == 0

    #Deinit
    fabric.set_oper_status(ModuleBase.MODULE_STATUS_ONLINE)
    module_updater.module_db_update()
    module_updater.deinit()
    midplane_table = module_updater.midplane_table
    fvs = midplane_table.get(name)
    assert fvs == None
    verify_fabric_asic("asic4", "0000:04:00.0", name, "0")
    verify_fabric_asic("asic5", "0000:05:00.0", name, "1")

def test_signal_handler():
    exit_code = 0
    daemon_chassisd = ChassisdDaemon(SYSLOG_IDENTIFIER)
    daemon_chassisd.stop.set = MagicMock()
    daemon_chassisd.log_info = MagicMock()
    daemon_chassisd.log_warning = MagicMock()

    # Test SIGHUP
    daemon_chassisd.signal_handler(signal.SIGHUP, None)
    assert daemon_chassisd.log_info.call_count == 1
    daemon_chassisd.log_info.assert_called_with("Caught signal 'SIGHUP' - ignoring...")
    assert daemon_chassisd.log_warning.call_count == 0
    assert daemon_chassisd.stop.set.call_count == 0
    assert exit_code == 0

    # Reset
    daemon_chassisd.log_info.reset_mock()
    daemon_chassisd.log_warning.reset_mock()
    daemon_chassisd.stop.set.reset_mock()

    # Test SIGINT
    test_signal = signal.SIGINT
    daemon_chassisd.signal_handler(test_signal, None)
    assert daemon_chassisd.log_info.call_count == 1
    daemon_chassisd.log_info.assert_called_with("Caught {} signal 'SIGINT' - exiting...".format(128 + test_signal))
    assert daemon_chassisd.log_warning.call_count == 0
    assert daemon_chassisd.stop.set.call_count == 1

    # Reset
    daemon_chassisd.log_info.reset_mock()
    daemon_chassisd.log_warning.reset_mock()
    daemon_chassisd.stop.set.reset_mock()

    # Test SIGTERM
    test_signal = signal.SIGTERM
    daemon_chassisd.signal_handler(test_signal, None)
    assert daemon_chassisd.log_info.call_count == 1
    daemon_chassisd.log_info.assert_called_with("Caught {} signal 'SIGTERM' - exiting...".format(128 + test_signal))
    assert daemon_chassisd.log_warning.call_count == 0
    assert daemon_chassisd.stop.set.call_count == 1

    # Reset
    daemon_chassisd.log_info.reset_mock()
    daemon_chassisd.log_warning.reset_mock()
    daemon_chassisd.stop.set.reset_mock()
    exit_code = 0

    # Test an unhandled signal
    daemon_chassisd.signal_handler(signal.SIGUSR1, None)
    assert daemon_chassisd.log_warning.call_count == 1
    daemon_chassisd.log_warning.assert_called_with("Caught unhandled signal 'SIGUSR1' - ignoring...")
    assert daemon_chassisd.log_info.call_count == 0
    assert daemon_chassisd.stop.set.call_count == 0
    assert exit_code == 0

def test_daemon_run_supervisor():
    # Test the chassisd run
    daemon_chassisd = ChassisdDaemon(SYSLOG_IDENTIFIER)
    daemon_chassisd.stop = MagicMock()
    daemon_chassisd.stop.wait.return_value = True
    daemon_chassisd.run()

def test_daemon_run_linecard():
    # Test the chassisd run
    daemon_chassisd = ChassisdDaemon(SYSLOG_IDENTIFIER)
    daemon_chassisd.stop = MagicMock()
    daemon_chassisd.stop.wait.return_value = True

    import sonic_platform.platform
    with patch.object(sonic_platform.platform.Chassis, 'get_my_slot') as mock:
       mock.return_value = sonic_platform.platform.Platform().get_chassis().get_supervisor_slot() + 1
       daemon_chassisd.run()
