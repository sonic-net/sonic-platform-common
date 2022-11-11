from ycable.ycable_utilities.y_cable_helper import *
from ycable.ycable import *
from .mock_swsscommon import Table
from sonic_platform_base.sfp_base import SfpBase
from swsscommon import swsscommon
from sonic_py_common import daemon_base
import copy
import os
import sys
import time
import traceback

if sys.version_info >= (3, 3):
    from unittest.mock import MagicMock, patch
else:
    from mock import MagicMock, patch


daemon_base.db_connect = MagicMock()
swsscommon.Table = MagicMock()
swsscommon.ProducerStateTable = MagicMock()
swsscommon.SubscriberStateTable = MagicMock()
swsscommon.SonicDBConfig = MagicMock()
#swsscommon.Select = MagicMock()

sys.modules['sonic_y_cable'] = MagicMock()
sys.modules['sonic_y_cable.y_cable'] = MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "ycable")
sys.path.insert(0, modules_path)

os.environ["YCABLE_UNIT_TESTING"] = "1"


class TestYcableScript(object):

    @patch("time.sleep", side_effect=Exception("Ignore it for just breaking the thread"))
    def test_ycable_info_helper_class_run(self, mocked_sleep):
        with patch('ycable.ycable.platform_sfputil') as patched_util:
            patched_util.logical.return_value = ['Ethernet0', 'Ethernet4']
            patched_util.get_asic_id_for_logical_port.return_value = 0
            y_cable_presence = [True]
            stopping_event = MagicMock()
            sfp_error_event = MagicMock()
            Y_cable_state_task = YcableStateUpdateTask(sfp_error_event, y_cable_presence)
            Y_cable_state_task.task_process = MagicMock()
            Y_cable_state_task.task_stopping_event = MagicMock()
            Y_cable_state_task.start()
            Y_cable_state_task.join()
            Y_cable_task = YcableInfoUpdateTask(y_cable_presence)
            Y_cable_task.task_thread = MagicMock()
            Y_cable_task.task_stopping_event = MagicMock()
            Y_cable_task.task_stopping_event.is_set = MagicMock()
            Y_cable_task.start()
            Y_cable_task.join()
            Y_cable_state_task.task_stopping_event.return_value.is_set.return_value = True
            #Y_cable_state_task.task_worker(stopping_event, sfp_error_event, y_cable_presence)
            # For now just check if exception is thrown for UT purposes
            try:
                Y_cable_task.task_worker([True])
            except Exception as e:
                pass

    @patch("swsscommon.swsscommon.Select", MagicMock())
    @patch("swsscommon.swsscommon.Select.addSelectable", MagicMock())
    @patch("swsscommon.swsscommon.Select.select", MagicMock())
    def test_ycable_helper_class_run_loop(self):
        Y_cable_task = YCableTableUpdateTask()
        Y_cable_cli_task = YCableCliUpdateTask()
        Y_cable_task.task_stopping_event = MagicMock()
        Y_cable_cli_task.task_stopping_event = MagicMock()
        Y_cable_task.task_thread = MagicMock()
        Y_cable_task.task_thread.start = MagicMock()
        Y_cable_task.task_thread.join = MagicMock()
        #Y_cable_task.task_stopping_event.return_value.is_set.return_value = False
        swsscommon.SubscriberStateTable.return_value.pop.return_value = (True, True, {"read_side": "2"})
        Y_cable_task.task_worker()
        Y_cable_task.start()
        Y_cable_task.join()
        Y_cable_cli_task.task_cli_worker()
        Y_cable_cli_task.start()
        Y_cable_cli_task.join()

    @patch("swsscommon.swsscommon.Select", MagicMock())
    @patch("swsscommon.swsscommon.Select.addSelectable", MagicMock())
    def test_ycable_helper_class_run(self):
        Y_cable_task = YCableTableUpdateTask()
        Y_cable_task.task_stopping_event = MagicMock()
        Y_cable_task.task_thread = MagicMock()
        Y_cable_task.task_thread.start = MagicMock()
        Y_cable_task.task_thread.join = MagicMock()
        Y_cable_task.task_stopping_event.return_value.is_set.return_value = True
        Y_cable_task.task_worker()
        Y_cable_task.start()
        Y_cable_task.join()

    def test_detect_port_in_error_status(self):

        mock_obj = MagicMock()
        mock_obj.get = MagicMock(return_value=(True, {"status": "2"}))
        rc = detect_port_in_error_status("Ethernet0", mock_obj)

        assert(rc == True)

    def test_put_all_values_from_list_to_db(self):

        mock_obj = MagicMock()
        mock_obj.get = MagicMock(return_value=(True, {"status": "2"}))
        res = ["1", "2"]
        rc = put_all_values_from_list_to_db(res, mock_obj, "Ethernet0")

        assert(rc == None)

    def test_put_all_values_from_dict_to_db(self):

        mock_obj = MagicMock()
        mock_obj.get = MagicMock(return_value=(True, {"status": "2"}))
        res = {"1": "2"}
        rc = put_all_values_from_dict_to_db(res, mock_obj, "Ethernet0")

        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.get_muxcable_info', MagicMock(return_value={'tor_active': 'self',
                                                                                               'time_post': '2022-Sep-23 00:09:16.968812',
                                                                                               'mux_direction': 'self',
                                                                                               'manual_switch_count': '7',
                                                                                               'auto_switch_count': '71',
                                                                                               'link_status_self': 'up',
                                                                                               'link_status_peer': 'up',
                                                                                               'link_status_nic': 'up',
                                                                                               'nic_lane1_active': 'True',
                                                                                               'nic_lane2_active': 'True',
                                                                                               'nic_lane3_active': 'True',
                                                                                               'nic_lane4_active': 'True',
                                                                                               'self_eye_height_lane1': '500',
                                                                                               'self_eye_height_lane2': '510',
                                                                                               'peer_eye_height_lane1': '520',
                                                                                               'peer_eye_height_lane2': '530',
                                                                                               'nic_eye_height_lane1': '742',
                                                                                               'nic_eye_height_lane2': '750',
                                                                                               'internal_temperature': '28',
                                                                                               'internal_voltage': '3.3',
                                                                                               'nic_temperature': '20',
                                                                                               'nic_voltage': '2.7',
                                                                                               'version_nic_active': '1.6MS',
                                                                                               'version_nic_inactive': '1.7MS',
                                                                                               'version_nic_next': '1.7MS',
                                                                                               'version_self_active': '1.6MS',
                                                                                               'version_self_inactive': '1.7MS',
                                                                                               'version_self_next': '1.7MS',
                                                                                               'version_peer_active': '1.6MS',
                                                                                               'version_peer_inactive': '1.7MS',
                                                                                               'version_peer_next': '1.7MS'}))
    def test_post_port_mux_info_to_db(self):
        logical_port_name = "Ethernet0"
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        rc = post_port_mux_info_to_db(logical_port_name, mux_tbl,asic_index, y_cable_tbl, 'active-standby')
        assert(rc != -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.get_muxcable_static_info', MagicMock(return_value={'read_side': 'self',
                                                                                                      'nic_lane1_precursor1': '1',
                                                                                                      'nic_lane1_precursor2': '-7',
                                                                                                      'nic_lane1_maincursor': '-1',
                                                                                                      'nic_lane1_postcursor1': '11',
                                                                                                      'nic_lane1_postcursor2': '11',
                                                                                                      'nic_lane2_precursor1': '12',
                                                                                                      'nic_lane2_precursor2': '7',
                                                                                                      'nic_lane2_maincursor': '7',
                                                                                                      'nic_lane2_postcursor1': '7',
                                                                                                      'nic_lane2_postcursor2': '7',
                                                                                                      'tor_self_lane1_precursor1': '17',
                                                                                                      'tor_self_lane1_precursor2': '17',
                                                                                                      'tor_self_lane1_maincursor': '17',
                                                                                                      'tor_self_lane1_postcursor1': '17',
                                                                                                      'tor_self_lane1_postcursor2': '17',
                                                                                                      'tor_self_lane2_precursor1': '7',
                                                                                                      'tor_self_lane2_precursor2': '7',
                                                                                                      'tor_self_lane2_maincursor': '7',
                                                                                                      'tor_self_lane2_postcursor1': '7',
                                                                                                      'tor_self_lane2_postcursor2': '7',
                                                                                                      'tor_peer_lane1_precursor1': '7',
                                                                                                      'tor_peer_lane1_precursor2': '7',
                                                                                                      'tor_peer_lane1_maincursor': '17',
                                                                                                      'tor_peer_lane1_postcursor1': '7',
                                                                                                      'tor_peer_lane1_postcursor2': '17',
                                                                                                      'tor_peer_lane2_precursor1': '7',
                                                                                                      'tor_peer_lane2_precursor2': '7',
                                                                                                      'tor_peer_lane2_maincursor': '17',
                                                                                                      'tor_peer_lane2_postcursor1': '7',
                                                                                                      'tor_peer_lane2_postcursor2': '17'}))
    def test_post_port_mux_static_info_to_db(self):
        logical_port_name = "Ethernet0"
        mux_tbl = Table("STATE_DB", y_cable_helper.MUX_CABLE_STATIC_INFO_TABLE)
        rc = post_port_mux_static_info_to_db(logical_port_name, mux_tbl)
        assert(rc != -1)

    def test_y_cable_helper_format_mapping_identifier1(self):
        rc = format_mapping_identifier("ABC        ")
        assert(rc == "abc")

    def test_y_cable_wrapper_get_transceiver_info(self):
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'Microsoft',
                                                                   'model': 'model1'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "Microsoft")
        assert(model == "model1")

    def test_y_cable_wrapper_get_presence(self):
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_presence.return_value = True

            presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_physical_port_from_logical_port(self):
        instance = get_ycable_physical_port_from_logical_port("Ethernet0")

        assert(instance == 0)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_port_instance_from_logical_port(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            patched_util.get.return_value = 0
            instance = get_ycable_port_instance_from_logical_port("Ethernet0")

        assert(instance == 0)

    def test_set_show_firmware_fields(self):

        mux_info_dict = {}
        ycable_show_fw_res_tbl = Table("STATE_DB", "XCVRD_SHOW_FW_RES")
        mux_info_dict['version_self_active'] = '0.8'
        mux_info_dict['version_self_inactive'] = '0.7'
        mux_info_dict['version_self_next'] = '0.7'
        mux_info_dict['version_peer_active'] = '0.8'
        mux_info_dict['version_peer_inactive'] = '0.7'
        mux_info_dict['version_peer_next'] = '0.7'
        mux_info_dict['version_nic_active'] = '0.8'
        mux_info_dict['version_nic_inactive'] = '0.7'
        mux_info_dict['version_nic_next'] = '0.7'
        rc = set_show_firmware_fields("Ethernet0", mux_info_dict, ycable_show_fw_res_tbl)

        assert(rc == 0)

    @patch('sonic_py_common.device_info.get_paths_to_platform_and_hwsku_dirs', MagicMock(return_value=('/tmp', None)))
    @patch('swsscommon.swsscommon.WarmStart', MagicMock())
    @patch('ycable.ycable.platform_sfputil', MagicMock())
    @patch('ycable.ycable.DaemonYcable.load_platform_util', MagicMock())
    def test_DaemonYcable_init_deinit(self):
        ycable = DaemonYcable(SYSLOG_IDENTIFIER)
        ycable.init()
        ycable.deinit()
        sig = "event"
        frame = MagicMock()
        ycable.signal_handler(sig, frame)
        # TODO: fow now we only simply call ycable.init/deinit without any further check, it only makes sure that
        # ycable.init/deinit will not raise unexpected exception. In future, probably more check will be added

    @patch('sonic_py_common.device_info.get_paths_to_platform_and_hwsku_dirs', MagicMock(return_value=('/tmp', None)))
    @patch('swsscommon.swsscommon.WarmStart', MagicMock())
    @patch('ycable.ycable.platform_sfputil', MagicMock())
    @patch('ycable.ycable.DaemonYcable.load_platform_util', MagicMock())
    @patch('ycable.ycable.YcableInfoUpdateTask', MagicMock())
    @patch('ycable.ycable.YcableStateUpdateTask', MagicMock())
    @patch('ycable.ycable_utilities.y_cable_helper.init_ports_status_for_y_cable', MagicMock())
    def test_DaemonYcable_init_deinit_full(self):
        ycable = DaemonYcable(SYSLOG_IDENTIFIER)
        ycable.init = MagicMock()
        ycable.init.return_value = MagicMock()
        ycable.stop_event = MagicMock()
        ycable.stop_event.wait.return_value = True
        ycable.run()
        # TODO: fow now we only simply call ycable.init/deinit without any further check, it only makes sure that
        # ycable.init/deinit will not raise unexpected exception. In future, probably more check will be added

    @patch('ycable.ycable_utilities.y_cable_helper.change_ports_status_for_y_cable_change_event', MagicMock(return_value=0))
    def test_handle_state_update_task(self):
        
        port = "Ethernet0"
        fvp_dict = {}
        y_cable_presence = False
        stopping_event = None
        rc = handle_state_update_task(port, fvp_dict, y_cable_presence, stopping_event)
        assert(rc == None)


def wait_until(total_wait_time, interval, call_back, *args, **kwargs):
    wait_time = 0
    while wait_time <= total_wait_time:
        try:
            if call_back(*args, **kwargs):
                return True
        except:
            pass
        time.sleep(interval)
        wait_time += interval
    return False


class TestYcableScriptException(object):

    @patch("swsscommon.swsscommon.Select", MagicMock(side_effect=NotImplementedError))
    @patch("swsscommon.swsscommon.Select.addSelectable", MagicMock(side_effect=NotImplementedError))
    @patch("swsscommon.swsscommon.Select.select", MagicMock(side_effect=NotImplementedError))
    def test_ycable_helper_class_run_loop_with_exception(self):



        Y_cable_cli_task = YCableCliUpdateTask()
        expected_exception_start = None
        expected_exception_join = None
        trace = None
        try:
            Y_cable_cli_task.start()
            Y_cable_cli_task.task_cli_worker()
        except Exception as e1:
            expected_exception_start  = e1
            trace = traceback.format_exc()


        try:
            Y_cable_cli_task.join()
        except Exception as e2:
            expected_exception_join = e2

        """
        #Handy debug Helpers or else use import logging
        #f = open("newfile", "w")
        #f.write(format(e2))
        #f.write(format(m1))
        #f.write(trace)
        """

        assert(type(expected_exception_start) == type(expected_exception_join))
        assert(expected_exception_start.args == expected_exception_join.args)
        assert("NotImplementedError" in str(trace) and "effect" in str(trace))
        assert("sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py" in str(trace))
        assert("swsscommon.Select" in str(trace))

