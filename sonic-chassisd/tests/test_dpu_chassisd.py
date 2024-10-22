import os
import sys
import mock
import pytest
from imp import load_source

from mock import Mock, MagicMock, patch
from sonic_py_common import daemon_base

from .mock_platform import MockDpuChassis

SYSLOG_IDENTIFIER = 'dpu_chassisd_test'

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


@pytest.mark.parametrize('conf_db, app_db, expected_state', [
    ({'Ethernet0': {}}, {'Ethernet0': [True, 'up']}, 'up'),
    ({'Ethernet0': {}}, {'Ethernet0': [True, 'down']}, 'down'),
    ({'Ethernet0': {}}, {'Ethernet0': [False, None]}, 'down'),
    ({'Ethernet0': {}, 'Ethernet4': {}}, {'Ethernet0': [True, 'up'], 'Ethernet4': [True, 'up']}, 'up'),
    ({'Ethernet0': {}, 'Ethernet4': {}}, {'Ethernet0': [True, 'up'], 'Ethernet4': [True, 'down']}, 'down'),
    ({'Ethernet0': {}, 'Ethernet4': {}}, {'Ethernet0': [True, 'up'], 'Ethernet4': [False, None]}, 'down'),
])
def test_dpu_dataplane_state_update_common(conf_db, app_db, expected_state):
    chassis = MockDpuChassis()

    with mock.patch.object(swsscommon.ConfigDBConnector, 'get_table', side_effect=lambda *args: conf_db):
        with mock.patch.object(swsscommon.Table, 'hget', side_effect=lambda intf, _: app_db[intf]):
            dpu_updater = DpuStateUpdater(SYSLOG_IDENTIFIER, chassis)

            state = dpu_updater.get_dp_state()

            assert state == expected_state


@pytest.mark.parametrize('db, expected_state', [
    ([True, 'UP'], 'up'),
    ([True, 'DOWN'], 'down'),
    ([False, None], 'down'),
])
def test_dpu_controlplane_state_update_common(db, expected_state):
    chassis = MockDpuChassis()

    with mock.patch.object(swsscommon.Table, 'hget', side_effect=lambda *args: db):
        dpu_updater = DpuStateUpdater(SYSLOG_IDENTIFIER, chassis)

        state = dpu_updater.get_cp_state()

        assert state == expected_state


@pytest.mark.parametrize('state, expected_state', [
    (True, 'up'),
    (False, 'down'),
])
def test_dpu_state_update_api(state, expected_state):
    chassis = MockDpuChassis()
    chassis.get_controlplane_state = MagicMock(return_value=state)
    chassis.get_dataplane_state = MagicMock(return_value=state)

    dpu_updater = DpuStateUpdater(SYSLOG_IDENTIFIER, chassis)

    state = dpu_updater.get_cp_state()
    assert state == expected_state

    state = dpu_updater.get_dp_state()
    assert state == expected_state


@pytest.mark.parametrize('dpu_id, dp_state, cp_state, expected_state', [
    (0, False, False, {'DPU0': 
        {'dpu_data_plane_state': 'down', 'dpu_data_plane_time': '2000-01-01 00:00:00', 
         'dpu_control_plane_state': 'down', 'dpu_control_plane_time': '2000-01-01 00:00:00'}}),
    (0, False, True, {'DPU0': 
        {'dpu_data_plane_state': 'down', 'dpu_data_plane_time': '2000-01-01 00:00:00', 
         'dpu_control_plane_state': 'up', 'dpu_control_plane_time': '2000-01-01 00:00:00'}}),
    (0, True, True, {'DPU0': 
        {'dpu_data_plane_state': 'up', 'dpu_data_plane_time': '2000-01-01 00:00:00', 
         'dpu_control_plane_state': 'up', 'dpu_control_plane_time': '2000-01-01 00:00:00'}}),
])
def test_dpu_state_update(dpu_id, dp_state, cp_state, expected_state):
    chassis = MockDpuChassis()

    chassis.get_dpu_id = MagicMock(return_value=dpu_id)
    chassis.get_dataplane_state = MagicMock(return_value=dp_state)
    chassis.get_controlplane_state = MagicMock(return_value=cp_state)

    chassis_state_db = {}

    def hset(key, field, value):
        print(key, field, value)
        if key not in chassis_state_db:
            chassis_state_db[key] = {}

        chassis_state_db[key][field] = value
    
    def hdel(key, field):
        del chassis_state_db[key][field]
        if not chassis_state_db[key]:
            del chassis_state_db[key]

    with mock.patch.object(swsscommon.Table, 'hset', side_effect=hset) as hset_mock:
        with mock.patch.object(swsscommon.Table, 'hdel', side_effect=hdel) as hdel_mock:
            dpu_updater = DpuStateUpdater(SYSLOG_IDENTIFIER, chassis)
            dpu_updater._time_now = MagicMock(return_value='2000-01-01 00:00:00')

            dpu_updater.update_state()

            assert chassis_state_db == expected_state

            dpu_updater.deinit()

            # After the deinit we assume that the DPU state is down.
            assert chassis_state_db == {'DPU0': 
                {'dpu_data_plane_state': 'down', 'dpu_data_plane_time': '2000-01-01 00:00:00', 
                 'dpu_control_plane_state': 'down', 'dpu_control_plane_time': '2000-01-01 00:00:00'}}