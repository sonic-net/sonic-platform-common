from .mock_swsscommon import Table
from sonic_platform_base.sfp_base import SfpBase
from swsscommon import swsscommon
from sonic_py_common import daemon_base
from ycable.ycable_utilities.y_cable_helper import *
from ycable.ycable import *
import copy
import os
import sys
import time

if sys.version_info >= (3, 3):
    from unittest.mock import MagicMock, patch, mock_open
else:
    from mock import MagicMock, patch, mock_open


daemon_base.db_connect = MagicMock()
swsscommon.Table = MagicMock()

sys.modules['sonic_y_cable'] = MagicMock()
sys.modules['sonic_y_cable.y_cable'] = MagicMock()

os.environ["Y_CABLE_HELPER_UNIT_TESTING"] = "1"


class helper_logger:
    mock_arg = MagicMock()

    def log_error(self, mock_arg):
        return True

    def log_warning(self, mock_arg):
        return True

    def log_debug(self, mock_arg):
        return True


class TestYCableScript(object):
    def test_xcvrd_helper_class_run(self):
        Y_cable_task = YCableTableUpdateTask()

    def test_y_cable_helper_format_mapping_identifier1(self):
        rc = format_mapping_identifier("ABC        ")
        assert(rc == "abc")

    def test_y_cable_helper_format_mapping_identifier_no_instance(self):
        rc = format_mapping_identifier(None)
        assert(rc == None)

    def test_gather_arg_from_db_and_check_for_type(self):

        arg_tbl = {"Ethernet0": (True, {"abc": "x", "def": "y"})}
        dic = {"key": "value"}
        rc = gather_arg_from_db_and_check_for_type(
            arg_tbl, "Ethernet0", "key", dic, "abc")

        assert(rc == ("x", "value", {'abc': 'x', 'def': 'y'}))

    def test_gather_arg_from_db_and_check_for_none_type(self):

        arg_tbl = {"Ethernet0": (True, {"abcd": "x", "def": "y"})}
        dic = {"key": "value"}
        rc = gather_arg_from_db_and_check_for_type(
            arg_tbl, "Ethernet0", "key", dic, "abc")

        assert(rc == (None, "value"), {'abcd': 'x', 'def': 'y'})

    def test_y_cable_wrapper_get_transceiver_info(self):
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'Microsoft',
                                                                   'model': 'model1'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "Microsoft")
        assert(model == "model1")

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_transceiver_info_with_platform_chassis(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_transceiver_info.return_value = {'type': '1000_BASE_SX_SFP',
                                                         'hardware_rev': '5',
                                                         'serial': 'PEP3L5D',
                                                         'manufacturer': 'FINISAR',
                                                         'model': 'ABC',
                                                         'connector': 'LC',
                                                         'encoding': '8B10B',
                                                         'ext_identifier': 'SFP',
                                                         'ext_rateselect_compliance': 'DEF',
                                                         'cable_length': '850',
                                                         'nominal_bit_rate': '100',
                                                         'specification_compliance': 'GHI',
                                                         'vendor_date': '2021-01-01',
                                                         'vendor_oui': '00:90:65'}

        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        received_xcvr_info = y_cable_wrapper_get_transceiver_info(1)

        type = received_xcvr_info.get('type')
        model = received_xcvr_info.get('model')
        vendor_date = received_xcvr_info.get('vendor_date')

        assert(type == "1000_BASE_SX_SFP")
        assert(model == "ABC")
        assert(vendor_date == "2021-01-01")

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_transceiver_info_with_platform_chassis_not_implemented(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_transceiver_info.side_effect = NotImplementedError
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'microsoft',
                                                                   'model': 'simulated'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "microsoft")
        assert(model == "simulated")

    def test_y_cable_wrapper_get_presence(self):
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_presence.return_value = True

            presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_presence_with_platform_chassis(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_presence = MagicMock(return_value=True)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_presence_with_platform_chassis_raise_exception(self, mock_chassis):

        mock_object = MagicMock(spec=SfpBase)
        mock_object.get_presence = MagicMock(side_effect=NotImplementedError)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_presence.return_value = True

            assert(y_cable_wrapper_get_presence(1) == True)

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
        asic_index = 0
        logical_port_name = "Ethernet0"
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
        mux_tbl = Table("STATE_DB", "Y_CABLE_STATIC_INFO_TABLE")
        y_cable_tbl = Table("STATE_DB", "Y_CABLE_STATIC_INFO_TABLE")
        rc = post_port_mux_static_info_to_db(logical_port_name, mux_tbl, y_cable_tbl)
        assert(rc != -1)

    def test_y_cable_helper_format_mapping_identifier1(self):
        rc = format_mapping_identifier("ABC        ")
        assert(rc == "abc")

    def test_y_cable_helper_format_mapping_identifier_no_instance(self):
        rc = format_mapping_identifier(None)
        assert(rc == None)

    def test_y_cable_wrapper_get_transceiver_info(self):
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'Microsoft',
                                                                   'model': 'model1'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "Microsoft")
        assert(model == "model1")

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_transceiver_info_with_platform_chassis(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_transceiver_info.return_value = {'type': '1000_BASE_SX_SFP',
                                                         'hardware_rev': '5',
                                                         'serial': 'PEP3L5D',
                                                         'manufacturer': 'FINISAR',
                                                         'model': 'ABC',
                                                         'connector': 'LC',
                                                         'encoding': '8B10B',
                                                         'ext_identifier': 'SFP',
                                                         'ext_rateselect_compliance': 'DEF',
                                                         'cable_length': '850',
                                                         'nominal_bit_rate': '100',
                                                         'specification_compliance': 'GHI',
                                                         'vendor_date': '2021-01-01',
                                                         'vendor_oui': '00:90:65'}

        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        received_xcvr_info = y_cable_wrapper_get_transceiver_info(1)

        type = received_xcvr_info.get('type')
        model = received_xcvr_info.get('model')
        vendor_date = received_xcvr_info.get('vendor_date')

        assert(type == "1000_BASE_SX_SFP")
        assert(model == "ABC")
        assert(vendor_date == "2021-01-01")

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_transceiver_info_with_platform_chassis_not_implemented(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_transceiver_info.side_effect = NotImplementedError
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'microsoft',
                                                                   'model': 'simulated'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "microsoft")
        assert(model == "simulated")

    def test_y_cable_wrapper_get_presence(self):
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_presence.return_value = True

            presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_presence_with_platform_chassis(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_presence = MagicMock(return_value=True)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    def test_y_cable_toggle_mux_torA_update_status_true(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = y_cable_toggle_mux_torA(1)

        assert(rc == 1)

    def test_y_cable_toggle_mux_torA_no_port_instance(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as port_instance:

            port_instance.get.return_value = None
            rc = y_cable_toggle_mux_torA(1)

        assert(rc == -1)

    def test_y_cable_toggle_mux_torA_update_status_exception(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as port_instance:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 0

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass
                def toggle_mux_to_tor_a():
                    raise NotImplementedError

            port_instance.get.return_value = PortInstanceHelper()


            rc = y_cable_toggle_mux_torA(1)

        assert(rc == -1)

    def test_y_cable_toggle_mux_torA_update_status_true(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = y_cable_toggle_mux_torA(1)

        assert(rc == 1)

    def test_y_cable_toggle_mux_torB_no_port_instance(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as port_instance:

            port_instance.get.return_value = None
            rc = y_cable_toggle_mux_torB(1)

        assert(rc == -1)

    def test_y_cable_toggle_mux_torB_update_status_exception(self):
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as port_instance:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 0

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass
                def toggle_mux_to_tor_a():
                    raise NotImplementedError

            port_instance.get.return_value = PortInstanceHelper()

            rc = y_cable_toggle_mux_torB(1)

        assert(rc == -1)

    def test_y_cable_toggle_mux_torB_update_status_true(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_b.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = y_cable_toggle_mux_torB(1)

        assert(rc == 2)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_1_active(self):
        read_side = 1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (1, 1))

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_2_active(self):
        read_side = 2
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_b.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (2,2))

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_1_standby(self):
        read_side = 1
        state = "standby"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_b.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (2,1))

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_2_standby(self):
        read_side = 2
        state = "standby"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (1,2))

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_update_tor_active_side_no_cable_presence(self):
        read_side = 1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (-1,-1))

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_update_tor_active_side_multiple_mappings(self):
        read_side = 1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (-1,-1))

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_with_read_update(self):
        read_side = -1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            mock_toggle_object.get_read_side.return_value = 1
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (1, 1))

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_with_read_update(self):
        read_side = -1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_b.return_value = True
            mock_toggle_object.get_read_side.return_value = 2
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (2, 1))

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_with_read_update(self):
        read_side = -1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_b.return_value = True
            mock_toggle_object.get_read_side.return_value = -1
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (-1, -1))

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_with_read_update_with_exception(self):
        read_side = -1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_b.return_value = True
            mock_toggle_object.get_read_side =  MagicMock(
                                side_effect=NotImplementedError)
            patched_util.get.return_value = mock_toggle_object

            rc = update_tor_active_side(read_side, state, logical_port_name)

        assert(rc == (-1, -1))

    def test_get_mux_cable_info_without_presence(self):

        rc = get_muxcable_info_without_presence()

        assert(rc['tor_active'] == 'unknown')
        assert(rc['mux_direction'] == 'unknown')
        assert(rc['manual_switch_count'] == 'N/A')
        assert(rc['auto_switch_count'] == 'N/A')


    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_physical_port_from_logical_port(self):
        instance = get_ycable_physical_port_from_logical_port("Ethernet0")

        assert(instance == 0)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_get_ycable_physical_port_from_logical_port_physical_port_not_present(self):
        instance = get_ycable_physical_port_from_logical_port("Ethernet0")

        assert(instance == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value={}))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_get_ycable_physical_port_from_logical_port_physical_port_list_empty(self):

        instance = get_ycable_physical_port_from_logical_port("Ethernet0")

        assert(instance == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_port_instance_from_logical_port(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            patched_util.get.return_value = 0
            instance = get_ycable_port_instance_from_logical_port("Ethernet0")

        assert(instance == 0)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_get_ycable_port_instance_from_logical_port_no_presence(self):
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            patched_util.get.return_value = 0
            instance = get_ycable_port_instance_from_logical_port("Ethernet0")

        assert(instance == PORT_INSTANCE_ERROR)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_port_instance_from_logical_port_no_port_instance(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_get():
                pass

            patched_util.get.return_value = mock_get()
            instance = get_ycable_port_instance_from_logical_port("E")

        assert(instance == PORT_INSTANCE_ERROR)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_port_instance_from_logical_port_multiple_mapping(self):

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            patched_util.get.return_value = 0
            instance = get_ycable_port_instance_from_logical_port("Ethernet0")

        assert(instance == -1)

    def test_update_table_mux_status_for_response_tbl(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        status = "standby"

        test_table = swsscommon.Table(appl_db[asic_index], "XCVRD_TEST_TABLE")
        update_table_mux_status_for_response_tbl(
            test_table, status, logical_port_name)

        rc = test_table.get(logical_port_name)

        # Since the table class is mocked, the most we can test for is that get doesn't return None
        assert(type(rc) != None)

    def test_set_result_and_delete_port(self):

        result = "result"
        actual_result = "pass"
        appl_db = "TEST_DB"
        port = 0

        command_table = swsscommon.Table(appl_db[0], "XCVRD_COMMAND_TABLE")
        response_table = swsscommon.Table(appl_db[1], "XCVRD_RESPONSE_TABLE")

        rc = set_result_and_delete_port(
            result, actual_result, command_table, response_table, port)
        assert(rc == None)

    def test_delete_port_from_y_cable_table(self):
        logical_port_name = "Ethernet0"
        appl_db = "TEST_DB"
        y_cable_tbl = swsscommon.Table(appl_db[0], "XCVRD_Y_CBL_TABLE")

        rc = delete_port_from_y_cable_table(logical_port_name, y_cable_tbl)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_port_instance_none(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1
        mux_response_tbl = {}
        mux_response_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_get():
                pass

            patched_util.get.return_value = mock_get()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, asic_index, appl_db, read_side, mux_response_tbl)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_read_side_none(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        mux_response_tbl = {}
        mux_response_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_read_side():
                pass

            read_side = mock_read_side()

            patched_util.get.return_value = 0

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, asic_index, appl_db, read_side, mux_response_tbl)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_active_side_none(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1
        mux_response_tbl = {}
        mux_response_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, asic_index, appl_db, read_side, mux_response_tbl)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_active_side_is_read_side(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1
        mux_response_tbl = {}
        mux_response_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 1

            patched_util.get.return_value = PortInstanceHelper()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, asic_index, appl_db, read_side, mux_response_tbl)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_active_side_not_read_side(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 2
        mux_response_tbl = {}
        mux_response_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 1

            patched_util.get.return_value = PortInstanceHelper()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, asic_index, appl_db, read_side, mux_response_tbl)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_active_side_status_unknown(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1
        mux_response_tbl = {}
        mux_response_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 4

            patched_util.get.return_value = PortInstanceHelper()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, asic_index, appl_db, read_side, mux_response_tbl)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_update_appdb_port_mux_cable_response_table_no_presence_status_unknown(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1
        mux_response_tbl = {}
        mux_response_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 4

            patched_util.get.return_value = PortInstanceHelper()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, asic_index, appl_db, read_side, mux_response_tbl)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    def test_update_appdb_port_mux_cable_response_table_invalid_ycable_mapping(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1
        mux_response_tbl = {}
        mux_response_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 4

            patched_util.get.return_value = PortInstanceHelper()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, asic_index, appl_db, read_side, mux_response_tbl)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_read_y_cable_and_update_statedb_port_tbl_invalid_ycable_mapping(self):

        logical_port_name = "Ethernet0"
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        rc = read_y_cable_and_update_statedb_port_tbl(
            logical_port_name, statedb_port_tbl[asic_index])
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_none(self):

        logical_port_name = "Ethernet0"
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_get():
                pass

            patched_util.get.return_value = mock_get()
            rc = read_y_cable_and_update_statedb_port_tbl(
                logical_port_name, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_get_presence_false(self):

        logical_port_name = "Ethernet0"
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_get():
                pass

            patched_util.get.return_value = mock_get()
            rc = read_y_cable_and_update_statedb_port_tbl(
                logical_port_name, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_get_read_side_exception(self):

        logical_port_name = "Ethernet0"
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_read_side():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = read_y_cable_and_update_statedb_port_tbl(
                logical_port_name, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_get_mux_dir_exception(self):

        logical_port_name = "Ethernet0"
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_read_side(self):
                    return 1

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = read_y_cable_and_update_statedb_port_tbl(
                logical_port_name, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_status_active(self):

        logical_port_name = "Ethernet0"
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_read_side(self):
                    return 1

                def get_mux_direction(self):
                    return 1

            patched_util.get.return_value = PortInstanceHelper()
            rc = read_y_cable_and_update_statedb_port_tbl(
                logical_port_name, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_status_standby(self):

        logical_port_name = "Ethernet0"
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_read_side(self):
                    return 1

                def get_mux_direction(self):
                    return 2

            patched_util.get.return_value = PortInstanceHelper()
            rc = read_y_cable_and_update_statedb_port_tbl(
                logical_port_name, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_status_unknown(self):

        logical_port_name = "Ethernet0"
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_read_side(self):
                    return 1

                def get_mux_direction(self):
                    return 0

            patched_util.get.return_value = PortInstanceHelper()
            rc = read_y_cable_and_update_statedb_port_tbl(
                logical_port_name, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_create_tables_and_insert_mux_unknown_entries(self):

        state_db = {}
        asic_index = 0
        logical_port_name = "Ethernet0"

        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "STATIC_TABLE")
        static_tbl[asic_index].get.return_value = (status, fvs)

        rc = create_tables_and_insert_mux_unknown_entries(
            state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_status_false(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = False
        fvs = [('state', "manual")]
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        rc = check_identifier_presence_and_update_mux_table_entry(
            state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_state_absent(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('badstate', "auto")]
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        rc = check_identifier_presence_and_update_mux_table_entry(
            state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_bad_state_value(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "badvalue")]
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        rc = check_identifier_presence_and_update_mux_table_entry(
            state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_no_presence(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        rc = check_identifier_presence_and_update_mux_table_entry(
            state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_no_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = None

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_multiple_port_instances(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'Microsoft', 'model': 'simulated'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_no_vendor_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'bad_manufacturer': 'Microsoft', 'model': 'simulated'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_no_model_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'Microsoft', 'bad_model': 'simulated'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_invalid_vendor_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'not_Microsoft', 'model': 'simulated'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name,  y_cable_presence)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_invalid_model_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]

        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'Microsoft', 'model': 'bad_model1'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name,  y_cable_presence)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_module_dir_none(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]

        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'not_Microsoft', 'model': 'simulated'}

            with patch('sonic_y_cable.y_cable_vendor_mapping.mapping') as mock_mapping:
                mock_mapping.get.return_value = None

                rc = check_identifier_presence_and_update_mux_table_entry(
                    state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name,  y_cable_presence)
                assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('sonic_y_cable.y_cable_vendor_mapping.mapping.get', MagicMock(return_value={"Microsoft": {"module": "test_module"}}))
    def test_check_identifier_presence_and_update_mux_table_entry_module_none(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]

        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = True

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'not_Microsoft', 'model': 'model1'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name,  y_cable_presence)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('sonic_y_cable.y_cable_vendor_mapping.mapping.get', MagicMock(return_value={"simulated": "microsoft.y_cable_simulated"}))
    def test_check_identifier_presence_and_update_mux_table_entry_module_microsoft(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]

        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = [True]

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'microsoft', 'model': 'simulated'}

            sys.modules['builtins.getattr'] = MagicMock()
            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name,  y_cable_presence)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('sonic_y_cable.y_cable_vendor_mapping.mapping.get', MagicMock(return_value={"simulated": "microsoft.y_cable_simulated"}))
    def test_check_identifier_presence_and_update_mux_table_entry_module_microsoft_y_cable_presence_false(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]

        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = [False]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_STATIC_INFO_TABLE)

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'microsoft', 'model': 'simulated'}

            sys.modules['builtins.getattr'] = MagicMock()
            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name,  y_cable_presence)
            assert(rc == None)


    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_delete_mux_table_entry(self):

        asic_index = 0
        logical_port_name = "Ethernet0"

        state_db = {}
        test_db = "TEST_DB"
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = [True]
        delete_change_event = [True]
        fvs = [('state', "auto"), ('read_side', 1)]
        asic_index = 0
        status = True
        y_cable_tbl = {}
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "STATIC_TABLE")
        static_tbl[asic_index].get.return_value = (status, fvs)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "MUX_TABLE")
        mux_tbl[asic_index].get.return_value = (status, fvs)

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as port_instance:
            rc = check_identifier_presence_and_delete_mux_table_entry(
                state_db, port_tbl, asic_index, logical_port_name, y_cable_presence,  delete_change_event, y_cable_tbl, static_tbl, mux_tbl)
            assert(rc == None)
        


    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_chassis')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.process_loopback_interface_and_get_read_side',MagicMock(return_value=0))
    def test_init_ports_status_for_y_cable(self, platform_chassis, platform_sfp, mock_swsscommon_table):

        platform_sfp = MagicMock()
        platform_chassis = MagicMock()

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        y_cable_presence = [True]

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_swsscommon_table.return_value = mock_table
        state_db = {}
        test_db = "TEST_DB"
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        port_table_keys = {}
        loopback_keys = {}
        grpc_config = {}
        hw_mux_cable_tbl, hw_mux_cable_tbl_peer = {}, {}
        y_cable_presence = [True]
        delete_change_event = [True]
        fvs = [('state', "auto"), ('read_side', 1)]
        asic_index = 0
        status = True
        y_cable_tbl = {}
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "STATIC_TABLE")
        static_tbl[asic_index].get.return_value = (status, fvs)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "MUX_TABLE")
        mux_tbl[asic_index].get.return_value = (status, fvs)

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        grpc_config[asic_index] = swsscommon.Table(
            test_db[asic_index], "GRPC_CONFIG")
        grpc_config[asic_index].get.return_value = (status, fvs)
        fwd_state_response_tbl = {}

        rc = init_ports_status_for_y_cable(platform_sfp, platform_chassis, y_cable_presence,  state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, port_table_keys, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, grpc_config, fwd_state_response_tbl, stop_event=threading.Event())

        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    @patch('ycable.ycable_utilities.y_cable_helper.check_identifier_presence_and_setup_channel', MagicMock(return_value=(None)))
    @patch('ycable.ycable_utilities.y_cable_helper.process_loopback_interface_and_get_read_side',MagicMock(return_value=0))
    @patch('swsscommon.swsscommon.Table')
    def test_change_ports_status_for_y_cable_change_event(self, mock_swsscommon_table):

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        state_db = {}
        y_cable_presence = [True]
        logical_port_dict = {'Ethernet0': '1'}

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(
            side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table
        port_tbl, port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}
        port_table_keys[0] = ['Ethernet0']
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0

            rc = change_ports_status_for_y_cable_change_event(
                logical_port_dict,  y_cable_presence, port_tbl, port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl, state_db, stop_event=threading.Event())

            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    @patch('ycable.ycable_utilities.y_cable_helper.check_identifier_presence_and_setup_channel', MagicMock(return_value=(None)))
    @patch('ycable.ycable_utilities.y_cable_helper.process_loopback_interface_and_get_read_side',MagicMock(return_value=0))
    @patch('swsscommon.swsscommon.Table')
    def test_change_ports_status_for_y_cable_change_event_sfp_removed(self, mock_swsscommon_table):

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        y_cable_presence = [True]
        logical_port_dict = {'Ethernet0': '1'}
        state_db = {}

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(
            side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table
        port_tbl, port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}
        port_table_keys[0] = ['Ethernet0']

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0
            rc = change_ports_status_for_y_cable_change_event(
                logical_port_dict,  y_cable_presence,  port_tbl, port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl, state_db, stop_event=threading.Event())

            assert(rc == None)


    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    @patch('ycable.ycable_utilities.y_cable_helper.check_identifier_presence_and_setup_channel', MagicMock(return_value=(None)))
    @patch('ycable.ycable_utilities.y_cable_helper.process_loopback_interface_and_get_read_side',MagicMock(return_value=0))
    @patch('swsscommon.swsscommon.Table')
    def test_change_ports_status_for_y_cable_change_event_sfp_removed_with_false(self, mock_swsscommon_table):

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        y_cable_presence = [True]
        logical_port_dict = {'Ethernet0': '0'}
        state_db = {}

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(
            side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        fvs = [('state', "auto"), ('read_side', 1)]
        test_db = "TEST_DB"
        port_tbl = {}
        asic_index = 0
        status = True
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}
        port_table_keys[0] = ['Ethernet0']

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0
            rc = change_ports_status_for_y_cable_change_event(
                logical_port_dict,  y_cable_presence,  port_tbl, port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl, state_db, stop_event=threading.Event())

            assert(rc == None)


    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    @patch('ycable.ycable_utilities.y_cable_helper.check_identifier_presence_and_setup_channel', MagicMock(return_value=(None)))
    @patch('ycable.ycable_utilities.y_cable_helper.process_loopback_interface_and_get_read_side',MagicMock(return_value=0))
    @patch('swsscommon.swsscommon.Table')
    def test_change_ports_status_for_y_cable_change_event_sfp_removed_with_removal(self, mock_swsscommon_table):

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        y_cable_presence = [True]
        logical_port_dict = {'Ethernet0': '0'}
        state_db = {}

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(
            side_effect=[(True, (('index', 1),  ('state', "auto"), ('read_side', 1))), (True, (('index', 2), ('state', "auto"), ('read_side', 1)))])
        mock_swsscommon_table.return_value = mock_table

        fvs = [('state', "auto"), ('read_side', 1)]
        test_db = "TEST_DB"
        port_tbl ,y_cable_tbl = {}, {}
        asic_index = 0
        status = True
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)

        port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl = {}, {}, {}, {}, {}, {}, {}, {}, {}
        port_table_keys[0] = ['Ethernet0']

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0
            rc = change_ports_status_for_y_cable_change_event(
                logical_port_dict,  y_cable_presence,  port_tbl, port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl, state_db, stop_event=threading.Event())

            assert(rc == None)










    
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.process_loopback_interface_and_get_read_side',MagicMock(return_value=0))
    @patch('swsscommon.swsscommon.Table')
    def test_change_ports_status_for_y_cable_change_event_sfp_unknown(self, mock_swsscommon_table):

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        y_cable_presence = [True]
        logical_port_dict = {'Ethernet0': '2'}
        state_db = {}

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(
            side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table
        port_tbl, port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}
        port_table_keys[0] = ['Ethernet0']
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0
            rc = change_ports_status_for_y_cable_change_event(
                logical_port_dict,  y_cable_presence,port_tbl, port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl, state_db, stop_event=threading.Event())

            assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    def test_delete_ports_status_for_y_cable(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(
            side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        mock_logical_port_name = [""]
        state_db = {}
        test_db = "TEST_DB"
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        fvs = [('state', "auto"), ('read_side', 1)]
        asic_index = 0
        status = True
        y_cable_tbl = {}
        grpc_config = {}
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "STATIC_TABLE")
        static_tbl[asic_index].get.return_value = (status, fvs)
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "MUX_TABLE")
        mux_tbl[asic_index].get.return_value = (status, fvs)

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        grpc_config[asic_index] = swsscommon.Table(
            test_db[asic_index], "GRPC_CONFIG")


        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.logical.return_value = ['Ethernet0', 'Ethernet4']
            patched_util.get_asic_id_for_logical_port.return_value = 0

            rc = delete_ports_status_for_y_cable(y_cable_tbl, static_tbl, mux_tbl, port_tbl, grpc_config)

            mock_swsscommon_table.assert_called()

    def test_check_identifier_presence_and_update_mux_info_entry(self):
        asic_index = 0
        logical_port_name = "Ethernet0"

        state_db = {}
        test_db = "TEST_DB"
        status = True
        mux_tbl = {}
        y_cable_tbl = {}
        static_tbl = {}
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "STATIC_TABLE")
        static_tbl[asic_index].get.return_value = (status, fvs)


        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.logical.return_value = ['Ethernet0', 'Ethernet4']
            rc = check_identifier_presence_and_update_mux_info_entry(
                state_db, mux_tbl, asic_index, logical_port_name, y_cable_tbl, static_tbl)

            assert(rc == None)


    def test_check_identifier_presence_and_update_mux_info_entry_with_false(self):
        asic_index = 0
        logical_port_name = "Ethernet0"

        state_db = {}
        test_db = "TEST_DB"
        status = False
        mux_tbl = {}
        y_cable_tbl = {}
        static_tbl = {}
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        static_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "STATIC_TABLE")
        static_tbl[asic_index].get.return_value = (status, fvs)


        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.logical.return_value = ['Ethernet0', 'Ethernet4']
            rc = check_identifier_presence_and_update_mux_info_entry(
                state_db, mux_tbl, asic_index, logical_port_name, y_cable_tbl, static_tbl)

            assert(rc == None)







    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    def test_get_firmware_dict(self, port_instance, mock_swsscommon_table):

        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.download_firmware_status = 1

        test_db = "TEST_DB"
        physical_port = 1
        target = "simulated_target"
        side = "a"
        mux_info_dict = {}
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        mux_tbl = {}
        asic_index = 0
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        mux_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0


            rc = get_firmware_dict(
                physical_port, port_instance, target, side, mux_info_dict, logical_port_name, mux_tbl)

            assert(mux_info_dict['version_a_active'] == None)
            assert(mux_info_dict['version_a_inactive'] == None)
            assert(mux_info_dict['version_a_next'] == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    def test_get_firmware_dict_asic_error(self, port_instance):

        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.download_firmware_status = 1

        physical_port = 1
        target = "simulated_target"
        side = "a"
        mux_info_dict = {}
        logical_port_name = "Ethernet0"
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        mux_tbl = {}
        asic_index = 0
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        mux_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0

            status = True
            fvs = [('state', "auto"), ('read_side', 1)]
            Table = MagicMock()
            Table.get.return_value = (status, fvs)
            swsscommon.Table.return_value.get.return_value = (
                False, {"read_side": "2"})

            rc = get_firmware_dict(
                physical_port, port_instance, target, side, mux_info_dict, logical_port_name, mux_tbl)

            assert(mux_info_dict['version_a_active'] == "N/A")
            assert(mux_info_dict['version_a_inactive'] == "N/A")
            assert(mux_info_dict['version_a_next'] == "N/A")

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    def test_get_firmware_dict_download_status_failed_exception(self, port_instance):

        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_FAILED = -1
        port_instance.download_firmware_status = -1
        port_instance.get_firmware_version = MagicMock(
            side_effect=NotImplementedError)

        physical_port = 1
        target = "simulated_target"
        side = "a"
        mux_info_dict = {}
        logical_port_name = "Ethernet0"
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        mux_tbl = {}
        asic_index = 0
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        mux_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0

            status = True
            fvs = [('state', "auto"), ('read_side', 1)]
            Table = MagicMock()
            Table.get.return_value = (status, fvs)

            rc = get_firmware_dict(
                physical_port, port_instance, target, side, mux_info_dict, logical_port_name, mux_tbl)

            assert(mux_info_dict['version_a_active'] == "N/A")
            assert(mux_info_dict['version_a_inactive'] == "N/A")
            assert(mux_info_dict['version_a_next'] == "N/A")

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    def test_get_firmware_dict_download_status_failed(self, port_instance):

        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_FAILED = -1
        port_instance.download_firmware_status = -1
        port_instance.get_firmware_version = MagicMock(
            return_value={"version_active": "2021", "version_inactive": "2020", "version_next": "2022"})

        physical_port = 1
        target = "simulated_target"
        side = "a"
        mux_info_dict = {}
        logical_port_name = "Ethernet0"
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        mux_tbl = {}
        asic_index = 0
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        mux_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0

            status = True
            fvs = [('state', "auto"), ('read_side', 1)]
            Table = MagicMock()
            Table.get.return_value = (status, fvs)

            rc = get_firmware_dict(
                physical_port, port_instance, target, side, mux_info_dict, logical_port_name, mux_tbl)

            assert(mux_info_dict['version_a_active'] == "2021")
            assert(mux_info_dict['version_a_inactive'] == "2020")
            assert(mux_info_dict['version_a_next'] == "2022")

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    def test_get_muxcable_info(self, platform_sfputil):
        physical_port = 20

        logical_port_name = "Ethernet20"
        swsscommon.Table.return_value.get.return_value = (
            True, {"read_side": "1"})
        platform_sfputil.get_asic_id_for_logical_port = 0
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_active_linked_tor_side(self):
                    return 1

                def get_mux_direction(self):
                    return 1

                def get_switch_count_total(self, switch_count):
                    return 1

                def get_eye_heights(self, tgt_tor):
                    return 500

                def is_link_active(self, tgt_nic):
                    return True

                def get_local_temperature(self):
                    return 22.75

                def get_local_voltage(self):
                    return 0.5

                def get_nic_voltage(self):
                    return 2.7

                def get_nic_temperature(self):
                    return 20

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0

                rc = get_muxcable_info(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

                assert(rc['tor_active'] == 'active')
                assert(rc['mux_direction'] == 'self')
                assert(rc['internal_voltage'] == 0.5)


    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    def test_get_muxcable_info_with_false(self, platform_sfputil):
        physical_port = 20

        logical_port_name = "Ethernet20"
        swsscommon.Table.return_value.get.return_value = (
            False, {"read_side": "1"})
        platform_sfputil.get_asic_id_for_logical_port = 0
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = False
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_active_linked_tor_side(self):
                    return 1

                def get_mux_direction(self):
                    return 1

                def get_switch_count_total(self, switch_count):
                    return 1

                def get_eye_heights(self, tgt_tor):
                    return 500

                def is_link_active(self, tgt_nic):
                    return True

                def get_local_temperature(self):
                    return 22.75

                def get_local_voltage(self):
                    return 0.5

                def get_nic_voltage(self):
                    return 2.7

                def get_nic_temperature(self):
                    return 20

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0

                rc = get_muxcable_info(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

                assert(rc == -1)


    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    def test_get_muxcable_info_peer_side(self, platform_sfputil):
        physical_port = 20

        logical_port_name = "Ethernet20"
        platform_sfputil.get_asic_id_for_logical_port = 0
        swsscommon.Table.return_value.get.return_value = (
            True, {"read_side": "2"})
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 2)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)


        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_active_linked_tor_side(self):
                    return 1

                def get_mux_direction(self):
                    return 1

                def get_switch_count_total(self, switch_count):
                    return 1

                def get_eye_heights(self, tgt_tor):
                    return 500

                def is_link_active(self, tgt_nic):
                    return True

                def get_local_temperature(self):
                    return 22.75

                def get_local_voltage(self):
                    return 0.5

                def get_nic_voltage(self):
                    return 2.7

                def get_nic_temperature(self):
                    return 20

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0

                rc = get_muxcable_info(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

                assert(rc['tor_active'] == 'standby')
                assert(rc['mux_direction'] == 'peer')
                assert(rc['internal_voltage'] == 0.5)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_info_exceptions(self, platform_sfputil):
        physical_port = 20

        logical_port_name = "Ethernet20"
        platform_sfputil.get_asic_id_for_logical_port = 0
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)


        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_active_linked_tor_side():
                    return 1

                def get_mux_direction():
                    return 1

                def get_switch_count_total(self, switch_count):
                    return 1

                def get_eye_heights(tgt_tor):
                    return 500

                def is_link_active(self, tgt_nic):
                    return True

                def get_local_temperature():
                    return 22.75

                def get_local_voltage():
                    return 0.5

                def get_nic_voltage():
                    return 2.7

                def get_nic_temperature():
                    return 20

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0

                rc = get_muxcable_info(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

                assert(rc['tor_active'] == 'unknown')
                assert(rc['mux_direction'] == 'unknown')
                assert(rc['self_eye_height_lane1'] == 'N/A')

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_info_true_exceptions_peer_side(self, platform_sfputil):
        physical_port = 20

        logical_port_name = "Ethernet20"
        platform_sfputil.get_asic_id_for_logical_port = 0
        swsscommon.Table.return_value.get.return_value = (
            True, {"read_side": "2"})
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 2)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)


        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_active_linked_tor_side(self):
                    raise NotImplementedError

                def get_mux_direction(self):
                    raise NotImplementedError

                def get_switch_count_total(self, switch_count):
                    raise NotImplementedError

                def get_eye_heights(self, tgt_tor):
                    raise NotImplementedError

                def is_link_active(self, tgt_nic):
                    return False

                def get_local_temperature(self):
                    raise NotImplementedError

                def get_local_voltage(self):
                    raise NotImplementedError

                def get_nic_voltage(self):
                    raise NotImplementedError

                def get_nic_temperature(self):
                    raise NotImplementedError

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0

                rc = get_muxcable_info(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

                assert(rc['tor_active'] == 'unknown')
                assert(rc['mux_direction'] == 'unknown')
                assert(rc['self_eye_height_lane1'] == 'N/A')

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_info_true_exceptions(self, platform_sfputil):
        physical_port = 20

        logical_port_name = "Ethernet20"
        platform_sfputil.get_asic_id_for_logical_port = 0
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)


        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_active_linked_tor_side(self):
                    raise NotImplementedError

                def get_mux_direction(self):
                    raise NotImplementedError

                def get_switch_count_total(self, switch_count):
                    raise NotImplementedError

                def get_eye_heights(self, tgt_tor):
                    raise NotImplementedError

                def is_link_active(self, tgt_nic):
                    return False

                def get_local_temperature(self):
                    raise NotImplementedError

                def get_local_voltage(self):
                    raise NotImplementedError

                def get_nic_voltage(self):
                    raise NotImplementedError

                def get_nic_temperature(self):
                    raise NotImplementedError

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0

                rc = get_muxcable_info(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

                assert(rc['tor_active'] == 'unknown')
                assert(rc['mux_direction'] == 'unknown')
                assert(rc['self_eye_height_lane1'] == 'N/A')

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_info_exceptions_peer_side(self, platform_sfputil):
        physical_port = 20

        logical_port_name = "Ethernet20"
        platform_sfputil.get_asic_id_for_logical_port = 0
        swsscommon.Table.return_value.get.return_value = (
            True, {"read_side": "2"})
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 2)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)


        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_active_linked_tor_side():
                    return 1

                def get_mux_direction():
                    return 1

                def get_switch_count_total(self, switch_count):
                    return 1

                def get_eye_heights(tgt_tor):
                    return 500

                def is_link_active(self, tgt_nic):
                    return True

                def get_local_temperature():
                    return 22.75

                def get_local_voltage():
                    return 0.5

                def get_nic_voltage():
                    return 2.7

                def get_nic_temperature():
                    return 20

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0

                rc = get_muxcable_info(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

                assert(rc['tor_active'] == 'unknown')
                assert(rc['mux_direction'] == 'unknown')
                assert(rc['self_eye_height_lane1'] == 'N/A')

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_static_info(self, platform_sfputil):
        physical_port = 0

        asic_index = 0
        logical_port_name = "Ethernet0"
        test_db = "TEST_DB"
        y_cable_tbl = {}
        status = True
        fvs = [('state', "auto"), ('read_side', 2)]

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        platform_sfputil.get_asic_id_for_logical_port = 0
        swsscommon.Table.return_value.get.return_value = (
            True, {"read_side": "1"})
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 0
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 2
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.download_firmware_status = 1
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_target_cursor_values(self, i, tgt):
                    if (tgt == self.TARGET_NIC):
                        return ([1, 7, 7, 1, 0])
                    elif (tgt == self.TARGET_TOR_A):
                        return ([17, 17, 17, 17, 17])
                    elif (tgt == self.TARGET_TOR_B):
                        return ([-17, -17, -17, -17, -17])

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0
                rc = get_muxcable_static_info(physical_port, logical_port_name, y_cable_tbl)

                assert (rc['read_side'] == 'tor1')
                assert (rc['nic_lane1_precursor1'] == 1)
                assert (rc['nic_lane1_precursor2'] == 7)
                assert (rc['nic_lane1_maincursor'] == 7)
                assert (rc['nic_lane1_postcursor1'] == 1)
                assert (rc['nic_lane1_postcursor2'] == 0)

                assert (rc['nic_lane2_precursor1'] == 1)
                assert (rc['nic_lane2_precursor2'] == 7)
                assert (rc['nic_lane2_maincursor'] == 7)
                assert (rc['nic_lane2_postcursor1'] == 1)
                assert (rc['nic_lane2_postcursor2'] == 0)

                assert (rc['tor_self_lane1_precursor1'] == 17)
                assert (rc['tor_self_lane1_precursor2'] == 17)
                assert (rc['tor_self_lane1_maincursor'] == 17)
                assert (rc['tor_self_lane1_postcursor1'] == 17)
                assert (rc['tor_self_lane1_postcursor2'] == 17)

                assert (rc['tor_self_lane2_precursor1'] == 17)
                assert (rc['tor_self_lane2_precursor2'] == 17)
                assert (rc['tor_self_lane2_maincursor'] == 17)
                assert (rc['tor_self_lane2_postcursor1'] == 17)
                assert (rc['tor_self_lane2_postcursor2'] == 17)

                assert (rc['tor_peer_lane1_precursor1'] == -17)
                assert (rc['tor_peer_lane1_precursor2'] == -17)
                assert (rc['tor_peer_lane1_maincursor'] == -17)
                assert (rc['tor_peer_lane1_postcursor1'] == -17)
                assert (rc['tor_peer_lane1_postcursor2'] == -17)

                assert (rc['tor_peer_lane2_precursor1'] == -17)
                assert (rc['tor_peer_lane2_precursor2'] == -17)
                assert (rc['tor_peer_lane2_maincursor'] == -17)
                assert (rc['tor_peer_lane2_postcursor1'] == -17)
                assert (rc['tor_peer_lane2_postcursor2'] == -17)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_static_info_read_side_peer(self, platform_sfputil):
        physical_port = 0

        asic_index = 0
        logical_port_name = "Ethernet0"

        test_db = "TEST_DB"
        status = True
        y_cable_tbl = {}
        fvs = [('state', "auto"), ('read_side', 2)]

        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        #swsscommon.Table = MagicMock()
        # this patch is already done as global instance
        platform_sfputil.get_asic_id_for_logical_port = 0
        swsscommon.Table.return_value.get.return_value = (
            True, {"read_side": "2"})
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 0
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 2
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.download_firmware_status = 1
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_target_cursor_values(self, i, tgt):
                    if (tgt == self.TARGET_NIC):
                        return ([1, 7, 7, 1, 0])
                    elif (tgt == self.TARGET_TOR_A):
                        return ([-17, -17, -17, -17, -17])
                    elif (tgt == self.TARGET_TOR_B):
                        return ([-17, -17, -17, -17, -17])

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0
                rc = get_muxcable_static_info(physical_port, logical_port_name, y_cable_tbl)

                assert (rc['read_side'] == 'tor2')
                assert (rc['nic_lane1_precursor1'] == 1)
                assert (rc['nic_lane1_precursor2'] == 7)
                assert (rc['nic_lane1_maincursor'] == 7)
                assert (rc['nic_lane1_postcursor1'] == 1)
                assert (rc['nic_lane1_postcursor2'] == 0)

                assert (rc['nic_lane2_precursor1'] == 1)
                assert (rc['nic_lane2_precursor2'] == 7)
                assert (rc['nic_lane2_maincursor'] == 7)
                assert (rc['nic_lane2_postcursor1'] == 1)
                assert (rc['nic_lane2_postcursor2'] == 0)

                assert (rc['tor_self_lane1_precursor1'] == -17)
                assert (rc['tor_self_lane1_precursor2'] == -17)
                assert (rc['tor_self_lane1_maincursor'] == -17)
                assert (rc['tor_self_lane1_postcursor1'] == -17)
                assert (rc['tor_self_lane1_postcursor2'] == -17)

                assert (rc['tor_self_lane2_precursor1'] == -17)
                assert (rc['tor_self_lane2_precursor2'] == -17)
                assert (rc['tor_self_lane2_maincursor'] == -17)
                assert (rc['tor_self_lane2_postcursor1'] == -17)
                assert (rc['tor_self_lane2_postcursor2'] == -17)

                assert (rc['tor_peer_lane1_precursor1'] == -17)
                assert (rc['tor_peer_lane1_precursor2'] == -17)
                assert (rc['tor_peer_lane1_maincursor'] == -17)
                assert (rc['tor_peer_lane1_postcursor1'] == -17)
                assert (rc['tor_peer_lane1_postcursor2'] == -17)

                assert (rc['tor_peer_lane2_precursor1'] == -17)
                assert (rc['tor_peer_lane2_precursor2'] == -17)
                assert (rc['tor_peer_lane2_maincursor'] == -17)
                assert (rc['tor_peer_lane2_postcursor1'] == -17)
                assert (rc['tor_peer_lane2_postcursor2'] == -17)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_static_info_read_side_peer_exceptions(self, platform_sfputil):
        physical_port = 0

        asic_index = 0
        logical_port_name = "Ethernet0"
        test_db = "TEST_DB"
        y_cable_tbl = {}

        status = True
        fvs = [('state', "auto"), ('read_side', 2)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)
        #swsscommon.Table = MagicMock()
        # this patch is already done as global instance
        platform_sfputil.get_asic_id_for_logical_port = 0
        swsscommon.Table.return_value.get.return_value = (
            True, {"read_side": "2"})
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 0
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 2
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.download_firmware_status = 1
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_target_cursor_values(self, i, tgt):
                    raise NotImplementedError

            patched_util.get.return_value = PortInstanceHelper()

            with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0
                rc = get_muxcable_static_info(physical_port, logical_port_name, y_cable_tbl)

                assert (rc['read_side'] == 'tor2')
                assert (rc['nic_lane1_precursor1'] == "N/A")

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    def test_task_download_firmware_worker(self, port_instance, mock_swsscommon_table):
        port = "Ethernet0"
        physical_port = 0
        file_full_path = "/path/to/file"

        def mock_download_fw(filepath):
            return 0

        port_instance.download_firmware = mock_download_fw

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table

        rc = {}

        task_download_firmware_worker(port, physical_port, port_instance, file_full_path,
                                      xcvrd_down_fw_rsp_tbl, xcvrd_down_fw_cmd_sts_tbl, rc)

        assert(rc[0] == 0)

    def test_set_show_firmware_fields(self):

        mux_info_dict = {}
        xcvrd_show_fw_res_tbl = Table("STATE_DB", "XCVRD_SHOW_FW_RES")
        mux_info_dict['version_self_active'] = '0.8'
        mux_info_dict['version_self_inactive'] = '0.7'
        mux_info_dict['version_self_next'] = '0.7'
        mux_info_dict['version_peer_active'] = '0.8'
        mux_info_dict['version_peer_inactive'] = '0.7'
        mux_info_dict['version_peer_next'] = '0.7'
        mux_info_dict['version_nic_active'] = '0.8'
        mux_info_dict['version_nic_inactive'] = '0.7'
        mux_info_dict['version_nic_next'] = '0.7'
        rc = set_show_firmware_fields(
            "Ethernet0", mux_info_dict, xcvrd_show_fw_res_tbl)

        assert(rc == 0)

    @patch('sonic_py_common.device_info.get_paths_to_platform_and_hwsku_dirs', MagicMock(return_value=('/tmp', None)))
    @patch('swsscommon.swsscommon.WarmStart', MagicMock())
    @patch('ycable.ycable.platform_sfputil', MagicMock())
    @patch('ycable.ycable.DaemonYcable.load_platform_util', MagicMock())
    def test_DaemonYcable_init_deinit(self):
        ycable = DaemonYcable(SYSLOG_IDENTIFIER)
        ycable.init()
        ycable.deinit()

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "enable", {"mode_value": "0",
                                                                                                                                 "lane_mask": "0",
                                                                                                                                 "direction": "0"})))
    def test_handle_config_prbs_cmd_arg_tbl_notification_no_port(self, port_instance, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_prbs": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "enable", {"mode_value": "0",
                                                                                                                                 "lane_mask": "0",
                                                                                                                                 "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    def test_handle_config_prbs_cmd_arg_tbl_notification_no_instance(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_prbs": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "enable", {"mode_value": "0",
                                                                                                                                 "lane_mask": "0",
                                                                                                                                 "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_prbs_cmd_arg_tbl_notification_with_instance_enable(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_prbs": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "disable", {"mode_value": "0",
                                                                                                                                  "lane_mask": "0",
                                                                                                                                  "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_prbs_cmd_arg_tbl_notification_with_instance_disable(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_prbs": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "reset", {"mode_value": "0",
                                                                                                                                "lane_mask": "0",
                                                                                                                                "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_prbs_cmd_arg_tbl_notification_with_instance_reset(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_prbs": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "anlt", {"mode": "0",
                                                                                                                               "lane_mask": "0",
                                                                                                                               "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_prbs_cmd_arg_tbl_notification_with_instance_anlt_enable(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_anlt.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_prbs": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "anlt", {"modex": "0",
                                                                                                                               "lane_mask": "0",
                                                                                                                               "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_prbs_cmd_arg_tbl_notification_with_instance_anlt_disable(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_anlt.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_prbs": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"mode": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_prbs_cmd_arg_tbl_notification_with_instance_fec_enable(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_prbs": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_prbs_cmd_arg_tbl_notification_with_instance_fec_disable(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_prbs": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_prbs_cmd_arg_tbl_notification_else_value(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_prbs_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_prbs_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_prbs_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_abc": True}

        rc = handle_config_prbs_cmd_arg_tbl_notification(
            fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_loop_cmd_arg_tbl_notification_else_value(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_loop_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_loop_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_loop_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_abc": True}

        rc = handle_config_loop_cmd_arg_tbl_notification(
            fvp, xcvrd_config_loop_cmd_arg_tbl, xcvrd_config_loop_cmd_sts_tbl, xcvrd_config_loop_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_loop_cmd_arg_tbl_notification_else_value(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_loop_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_loop_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_loop_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_loop": True}

        rc = handle_config_loop_cmd_arg_tbl_notification(
            fvp, xcvrd_config_loop_cmd_arg_tbl, xcvrd_config_loop_cmd_sts_tbl, xcvrd_config_loop_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    def test_handle_config_loop_cmd_arg_tbl_notification_no_port(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_loop_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_loop_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_loop_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_loop": True}

        rc = handle_config_loop_cmd_arg_tbl_notification(
            fvp, xcvrd_config_loop_cmd_arg_tbl, xcvrd_config_loop_cmd_sts_tbl, xcvrd_config_loop_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_loop_cmd_arg_tbl_notification_no_instance(self, port_instance, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_loop_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_loop_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_loop_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_loop": True}

        rc = handle_config_loop_cmd_arg_tbl_notification(
            fvp, xcvrd_config_loop_cmd_arg_tbl, xcvrd_config_loop_cmd_sts_tbl, xcvrd_config_loop_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "enable", {"enable": "0",
                                                                                                                                 "lane_mask": "0",
                                                                                                                                 "mode_value": "0",
                                                                                                                                 "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_loop_cmd_arg_tbl_notification_enable(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_loop_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_loop_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_loop_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_loopback_mode.return_value = True
        port_instance.disable_loopback_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_loop": True}

        rc = handle_config_loop_cmd_arg_tbl_notification(
            fvp, xcvrd_config_loop_cmd_arg_tbl, xcvrd_config_loop_cmd_sts_tbl, xcvrd_config_loop_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "disable", {"disable": "0",
                                                                                                                                  "lane_mask": "0",
                                                                                                                                  "mode_value": "0",
                                                                                                                                  "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_loop_cmd_arg_tbl_notification_disable(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_loop_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_config_loop_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_loop_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_loopback_mode.return_value = True
        port_instance.disable_loopback_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_loop": True}

        rc = handle_config_loop_cmd_arg_tbl_notification(
            fvp, xcvrd_config_loop_cmd_arg_tbl, xcvrd_config_loop_cmd_sts_tbl, xcvrd_config_loop_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_show_event_cmd_arg_tbl_notification_else_value(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_event_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_event_rsp_tbl = mock_swsscommon_table
        xcvrd_show_event_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.PRBS_DIRECTION_BOTH = 2
        port_instance.enable_prbs_mode.return_value = True
        port_instance.disable_prbs_mode.return_value = True
        port_instance.reset.return_value = True
        port_instance.set_fec_mode.return_value = True
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"config_loop": True}

        rc = handle_show_event_cmd_arg_tbl_notification(
            fvp, xcvrd_show_event_cmd_sts_tbl, xcvrd_show_event_rsp_tbl, xcvrd_show_event_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_show_event_cmd_arg_tbl_notification_get_log(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_event_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_event_rsp_tbl = mock_swsscommon_table
        xcvrd_show_event_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_event_log.return_value = ["log 1", "log 2"]

        asic_index = 0
        port = "Ethernet0"
        fvp = {"show_event": True}

        rc = handle_show_event_cmd_arg_tbl_notification(
            fvp, xcvrd_show_event_cmd_sts_tbl, xcvrd_show_event_rsp_tbl, xcvrd_show_event_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_show_event_cmd_arg_tbl_notification_get_actual_log(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_event_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_event_rsp_tbl = mock_swsscommon_table
        xcvrd_show_event_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_event_log.return_value = ["log 1", "log 2"]
        port_instance_helper.return_value = port_instance
        asic_index = 0
        port = "Ethernet0"
        fvp = {"show_event": True}

        rc = handle_show_event_cmd_arg_tbl_notification(
            fvp, xcvrd_show_event_cmd_sts_tbl, xcvrd_show_event_rsp_tbl, xcvrd_show_event_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_show_event_cmd_arg_tbl_notification_get_no_log(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_event_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_event_rsp_tbl = mock_swsscommon_table
        xcvrd_show_event_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_event_log.return_value = Exception(
            NotImplementedError)

        asic_index = 0
        port = "Ethernet0"
        fvp = {"show_event": True}

        rc = handle_show_event_cmd_arg_tbl_notification(
            fvp, xcvrd_show_event_cmd_sts_tbl, xcvrd_show_event_rsp_tbl, xcvrd_show_event_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_show_event_cmd_arg_tbl_notification_no_port(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_event_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_event_rsp_tbl = mock_swsscommon_table
        xcvrd_show_event_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_event_log.return_value = ["log 1", "log 2"]
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"show_event": True}

        rc = handle_show_event_cmd_arg_tbl_notification(
            fvp, xcvrd_show_event_cmd_sts_tbl, xcvrd_show_event_rsp_tbl, xcvrd_show_event_res_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    def test_handle_show_event_cmd_arg_tbl_notification_no_instance(self, port_instance, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_event_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_event_rsp_tbl = mock_swsscommon_table
        xcvrd_show_event_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_event_log.return_value = ["log 1", "log 2"]

        asic_index = 0
        port = "Ethernet0"
        fvp = {"show_event": True}

        rc = handle_show_event_cmd_arg_tbl_notification(
            fvp, xcvrd_show_event_cmd_sts_tbl, xcvrd_show_event_rsp_tbl, xcvrd_show_event_res_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_no_status(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_fec_rsp_tbl = mock_swsscommon_table
        xcvrd_show_fec_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_fec_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()

        asic_index = 0
        port = "Ethernet0"
        fvp = {"show_event": True}

        rc = handle_get_fec_cmd_arg_tbl_notification(
            fvp, xcvrd_show_fec_rsp_tbl, xcvrd_show_fec_cmd_sts_tbl, xcvrd_show_fec_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_no_port(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_fec_rsp_tbl = mock_swsscommon_table
        xcvrd_show_fec_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_fec_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_fec": True}

        rc = handle_get_fec_cmd_arg_tbl_notification(
            fvp, xcvrd_show_fec_rsp_tbl, xcvrd_show_fec_cmd_sts_tbl, xcvrd_show_fec_res_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_no_instance(self, port_instance, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_fec_rsp_tbl = mock_swsscommon_table
        xcvrd_show_fec_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_fec_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance_helper = port_instance

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_fec": True}

        rc = handle_get_fec_cmd_arg_tbl_notification(
            fvp, xcvrd_show_fec_rsp_tbl, xcvrd_show_fec_cmd_sts_tbl, xcvrd_show_fec_res_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_result(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_fec_rsp_tbl = mock_swsscommon_table
        xcvrd_show_fec_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_fec_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_fec_mode.return_value = 0
        port_instance.get_anlt.return_value = 0
        port_instance.get_speed.return_value = 0

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_fec": True}

        rc = handle_get_fec_cmd_arg_tbl_notification(
            fvp, xcvrd_show_fec_rsp_tbl, xcvrd_show_fec_cmd_sts_tbl, xcvrd_show_fec_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_no_status(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()

        asic_index = 0
        port = "Ethernet0"
        fvp = {"show_event": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_no_port(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_no_instance(self, port_instance, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}
        
        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "ber", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_ber(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_ber_info.return_value = ["100", "200"]

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(None, "ber", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_ber_no_target(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_ber_info.return_value = ["100", "200"]

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == -1)

    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "ber", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_ber_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_ber_info(self):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)


    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(None, "ber", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_ber_with_no_target(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_ber_info(self):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == -1)


    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "eye", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_eye_with_with_correct_values(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_eye_heights(self, target):
                    return [1, 2, 3]


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)


    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "eye", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_eye_with_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_eye_heights(self, target):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)

    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(None, "eye", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_eye_with_with_no_target(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_eye_heights(self, target):
                    return [1, 2, 3]


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == -1)



    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec_stats", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_fec_stats_with_with_correct_values(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_fec_stats(self, target):
                    return {1:"1"}


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)


    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec_stats", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_fec_stats_with_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_fec_stats(self, target):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)

    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(None, "fec_stats", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_fec_stats_with_with_no_target(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_eye_heights(self, target):
                    return [1, 2, 3]


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == -1)


    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "pcs_stats", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_pcs_stats_with_with_correct_values(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_pcs_stats(self, target):
                    return {1:"1"}


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)


    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "pcs_stats", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_pcs_stats_with_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_pcs_stats(self, target):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)

    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(None, "pcs_stats", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_pcs_stats_with_with_no_target(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_eye_heights(self, target):
                    return [1, 2, 3]


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == -1)


    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "cable_alive", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_alive_status_with_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_alive_status():
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)

    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "health_check", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_health_check_with_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def health_check(self):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)


    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "reset_cause", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_reset_cause_with_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def reset_cause(self):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)

    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "operation_time", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_operation_time_with_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def operation_time(self):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)

    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "debug_dump", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_debug_dump_with_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def debug_dump_registers(self, option):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)


    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "debug_dump", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_debug_dump_with_correct_values(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def debug_dump_registers(self, option= None):
                    return {1:"1"}


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)

    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "queue_info", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_queue_info_with_correct_values(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def queue_info(self):
                    return {1:"1"}


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)

    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "queue_info", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_queue_info_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def queue_info(self):
                    raise NotImplementedError


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)




    #@patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    #@patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "ber", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_ber_with_with_correct_values(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_ber_info(self, target):
                    return [1, 2, 3]


            patched_util.get.return_value = PortInstanceHelper()
            asic_index = 0
            port = "Ethernet0"
            fvp = {"get_ber": True}

            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)


    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "eye", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_eye(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_eye_info.return_value = ["100", "200"]

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)



    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "eye", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_eye_with_exception(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_ber_info(self):
                    raise NotImplementedError
            patched_util.get.return_value = PortInstanceHelper()


            rc = handle_show_ber_cmd_arg_tbl_notification(
                fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
            assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec_stats", {"modex": "0",
                                                                                                                                    "lane_mask": "0",
                                                                                                                                    "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_fec_stats(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_fec_stats.return_value = {"100": "200"}

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "pcs_stats", {"modex": "0",
                                                                                                                                    "lane_mask": "0",
                                                                                                                                    "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_pcs_stats(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_pcs_stats.return_value = {"100": "200"}

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "cable_alive", {"modex": "0",
                                                                                                                                      "lane_mask": "0",
                                                                                                                                      "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_alive_status(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.get_alive_status.return_value = True

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "health_check", {"modex": "0",
                                                                                                                                      "lane_mask": "0",
                                                                                                                                      "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_cable_health(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.health_check.return_value = True

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "health_check", {"modex": "0",
                                                                                                                                      "lane_mask": "0",
                                                                                                                                      "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_cable_health(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.health_check.return_value = True

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "reset_cause", {"modex": "0",
                                                                                                                                      "lane_mask": "0",
                                                                                                                                      "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_reset_cause_correct_values(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.reset_cause.return_value = "xyz was reset"

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "operation_time", {"modex": "0",
                                                                                                                                      "lane_mask": "0",
                                                                                                                                      "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_operation_time(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.operation_time.return_value = 0

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "queue_info", {"modex": "0",
                                                                                                                                      "lane_mask": "0",
                                                                                                                                      "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_queue_info(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.queue_info.return_value = {"1":"2"}

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "debug_dump", {"modex": "0",
                                                                                                                                     "lane_mask": "0",
                                                                                                                                     "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_get_fec_cmd_arg_tbl_notification_get_debug_dump_registers(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_ber_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_ber_rsp_tbl = mock_swsscommon_table
        xcvrd_show_ber_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_ber_res_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.debug_dump_registers.return_value = {"register1": "100"}

        asic_index = 0
        port = "Ethernet0"
        fvp = {"get_ber": True}

        rc = handle_show_ber_cmd_arg_tbl_notification(
            fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port)
        assert(rc == None)
    """

    def handle_config_firmware_roll_cmd_arg_tbl_notification(fvp, xcvrd_roll_fw_cmd_sts_tbl, xcvrd_roll_fw_rsp_tbl, asic_index, port):

            fvp_dict = dict(fvp)


            if "rollback_firmware" in fvp_dict:
                file_name = fvp_dict["rollback_firmware"]
                status = 'False'

                if file_name == 'null':
                    file_full_path = None
                else:
                    file_full_path = '/usr/share/sonic/firmware/{}'.format(file_name)
                    if not os.path.isfile(file_full_path):
                        helper_logger.log_error("Error: cli cmd mux rollback firmware file does not exist port {} file {}".format(port, file_name))
                        set_result_and_delete_port('status', status, xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)
                        break



                physical_port = get_ycable_physical_port_from_logical_port(port)
                if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
                    # error scenario update table accordingly
                    helper_logger.log_warning("Error: Could not get physical port for cli cmd mux rollback firmware port {}".format(port))
                    set_result_and_delete_port('status', status, xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)
                    break

                port_instance = get_ycable_port_instance_from_logical_port(port)
                if port_instance is None or port_instance in port_mapping_error_values:
                    # error scenario update table accordingly
                    helper_logger.log_warning("Error: Could not get port instance for cli cmd mux rollback firmware port {}".format(port))
                    set_result_and_delete_port('status', status, xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)

                with y_cable_port_locks[physical_port]:
                    try:
                        status = port_instance.rollback_firmware(file_full_path)
                    except Exception as e:
                        status = -1
                        helper_logger.log_warning("Failed to execute the rollback_firmware API for port {} due to {}".format(physical_port,repr(e)))
                set_result_and_delete_port('status', status, xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)
            else:
                helper_logger.log_error("Wrong param for cli cmd mux rollback firmware port {}".format(port))
                set_result_and_delete_port('status', 'False', xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)
    """

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_firmware_roll_cmd_arg_tbl_notification_no_port(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()

        asic_index = 0
        port = "Ethernet0"
        fvp = {"rollback_firmware": "null"}

        rc = handle_config_firmware_roll_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_firmware_roll_cmd_arg_tbl_notification_no_instance(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table

        asic_index = 0
        port = "Ethernet0"
        fvp = {"rollback_firmware": "null"}

        rc = handle_config_firmware_roll_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_firmware_roll_cmd_arg_tbl_notification_with_instance(self, port_instance, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()

        asic_index = 0
        port = "Ethernet0"
        fvp = {"rollback_firmware": "null"}

        rc = handle_config_firmware_roll_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_handle_config_firmware_roll_cmd_arg_tbl_notification_no_port_and_instance(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()

        asic_index = 0
        port = "Ethernet0"
        fvp = {"rollback_firmware": "null"}

        rc = handle_config_firmware_roll_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_firmware_down_cmd_arg_tbl_notification_no_port(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"download_firmware": "null"}

        rc = handle_config_firmware_down_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, asic_index, port, task_download_firmware_thread)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_firmware_down_cmd_arg_tbl_notification_else_condition(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"downoad_firmware": "null"}

        rc = handle_config_firmware_down_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, asic_index, port, task_download_firmware_thread)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('threading.Thread')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_firmware_down_cmd_arg_tbl_notification_with_instance(self, port_instance, mock_swsscommon_table, port_instance_helper, thread_obj):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        thread_instance = MagicMock()
        thread_instance.start = MagicMock()
        thread_obj = thread_instance
        port_instance_helper = port_instance

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"download_firmware": "null"}

        rc = handle_config_firmware_down_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, asic_index, port, task_download_firmware_thread)
        assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_firmware_down_cmd_arg_tbl_notification_no_instance(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"download_firmware": "null"}

        rc = handle_config_firmware_down_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, asic_index, port, task_download_firmware_thread)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_firmware_acti_cmd_arg_tbl_notification_no_port(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        xcvrd_acti_fw_cmd_arg_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"activate_firmware": "null"}

        rc = handle_config_firmware_acti_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, xcvrd_acti_fw_cmd_arg_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_firmware_acti_cmd_arg_tbl_notification_else_condition(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        xcvrd_acti_fw_cmd_arg_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"down_firmware": "null"}

        rc = handle_config_firmware_acti_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, xcvrd_acti_fw_cmd_arg_tbl, asic_index, port)
        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances')
    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_port_instance_from_logical_port')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_config_firmware_acti_cmd_arg_tbl_notification_with_instance(self, port_instance, mock_swsscommon_table, port_instance_helper):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        xcvrd_acti_fw_cmd_arg_tbl = mock_swsscommon_table
        port_instance = MagicMock()
        port_instance.activate_firmware = MagicMock(return_value=True)
        thread_instance = MagicMock()
        thread_instance.start = MagicMock()
        thread_obj = thread_instance
        port_instance_helper = port_instance

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"activate_firmware": "null"}

        rc = handle_config_firmware_acti_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, xcvrd_acti_fw_cmd_arg_tbl, asic_index, port)
        assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_firmware_acti_cmd_arg_tbl_notification_no_instance(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        xcvrd_acti_fw_cmd_arg_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"activate_firmware": "null"}

        rc = handle_config_firmware_acti_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, xcvrd_acti_fw_cmd_arg_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_firmware_show_cmd_arg_tbl_notification_no_port(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        xcvrd_acti_fw_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_fw_res_tbl = mock_swsscommon_table
        mux_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"firmware_version": "null"}

        rc = handle_show_firmware_show_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, xcvrd_show_fw_res_tbl, asic_index, port, mux_tbl)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_firmware_show_cmd_arg_tbl_notification_else_condition(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        xcvrd_acti_fw_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_fw_res_tbl = mock_swsscommon_table
        mux_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"down_firmware": "null"}

        rc = handle_show_firmware_show_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, xcvrd_show_fw_res_tbl, asic_index, port, mux_tbl)
        assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_show_firmware_show_cmd_arg_tbl_notification_with_instance(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        xcvrd_acti_fw_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_fw_res_tbl = mock_swsscommon_table
        mux_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"firmware_version": "null"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.MUX_TOGGLE_STATUS_INPROGRESS = 1
                    self.MUX_TOGGLE_STATUS_FAILED = 2
                    self.MUX_TOGGLE_STATUS_NOT_INITIATED_OR_FINISHED = 2
                    self.mux_toggle_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"

                def get_read_side(self):
                    return 1

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_show_firmware_show_cmd_arg_tbl_notification(
                fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, xcvrd_show_fw_res_tbl, asic_index, port, mux_tbl)
            assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_firmware_show_cmd_arg_tbl_notification_no_instance(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_down_fw_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_down_fw_rsp_tbl = mock_swsscommon_table
        xcvrd_acti_fw_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_fw_res_tbl = mock_swsscommon_table
        mux_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"firmware_version": "null"}

        rc = handle_show_firmware_show_cmd_arg_tbl_notification(
            fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, xcvrd_show_fw_res_tbl, asic_index, port, mux_tbl)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_mux_switchmode_cmd_arg_tbl_notification_no_port(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        xcvrd_acti_fw_cmd_arg_tbl = mock_swsscommon_table
        xcvrd_show_fw_res_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"config": "null"}

        rc = handle_config_mux_switchmode_arg_tbl_notification(
            fvp, xcvrd_config_hwmode_swmode_cmd_sts_tbl, xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_mux_switchmode_cmd_arg_tbl_notification_else_condition(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"down_firmware": "null"}

        rc = handle_config_mux_switchmode_arg_tbl_notification(
            fvp, xcvrd_config_hwmode_swmode_cmd_sts_tbl, xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_config_mux_switchmode_cmd_arg_tbl_notification_with_instance_manual(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"config": "manual"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"
                    self.SWITCHING_MODE_MANUAL = "manual"

                def get_read_side(self):
                    return 1

                def set_switching_mode(self, mode):
                    return True

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_config_mux_switchmode_arg_tbl_notification(
                fvp, xcvrd_config_hwmode_swmode_cmd_sts_tbl, xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port)
            assert(rc == None)


    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_config_mux_switchmode_cmd_arg_tbl_notification_with_instance_manual_with_exception(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"config": "manual"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"
                    self.SWITCHING_MODE_MANUAL = "manual"

                def get_read_side(self):
                    return 1

                def set_switching_mode(self, mode):
                    raise NotImplementedError

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_config_mux_switchmode_arg_tbl_notification(
                fvp, xcvrd_config_hwmode_swmode_cmd_sts_tbl, xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port)
            assert(rc == -1)

        fvp = {"config": "auto"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"
                    self.SWITCHING_MODE_MANUAL = "manual"

                def get_read_side(self):
                    return 1

                def set_switching_mode(self, mode):
                    raise NotImplementedError

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_config_mux_switchmode_arg_tbl_notification(
                fvp, xcvrd_config_hwmode_swmode_cmd_sts_tbl, xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port)
            assert(rc == -1)


        fvp = {"config": "xyz"}
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"
                    self.SWITCHING_MODE_MANUAL = "manual"

                def get_read_side(self):
                    return 1

                def set_switching_mode(self, mode):
                    raise NotImplementedError

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_config_mux_switchmode_arg_tbl_notification(
                fvp, xcvrd_config_hwmode_swmode_cmd_sts_tbl, xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port)
            assert(rc == -1)


    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_mux_switchmode_cmd_arg_tbl_notification_no_instance(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_rsp_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"config": "manual"}

        rc = handle_config_mux_switchmode_arg_tbl_notification(
            fvp, xcvrd_config_hwmode_swmode_cmd_sts_tbl, xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_config_mux_switchmode_cmd_arg_tbl_notification_with_instance_auto(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"config": "auto"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"
                    self.SWITCHING_MODE_MANUAL = "manual"
                    self.SWITCHING_MODE_AUTO = "auto"

                def get_read_side(self):
                    return 1

                def set_switching_mode(self, mode):
                    return True

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_config_mux_switchmode_arg_tbl_notification(
                fvp, xcvrd_config_hwmode_swmode_cmd_sts_tbl, xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port)
            assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_mux_switchmode_cmd_arg_tbl_notification_no_port(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        hw_mux_cable_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"state": "null"}

        rc = handle_show_hwmode_swmode_cmd_arg_tbl_notification(
            fvp, xcvrd_show_hwmode_swmode_cmd_sts_tbl, xcvrd_show_hwmode_swmode_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_mux_switchmode_cmd_arg_tbl_notification_else_condition(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_rsp_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"down_firmware": "null"}

        rc = handle_show_hwmode_swmode_cmd_arg_tbl_notification(
            fvp, xcvrd_show_hwmode_swmode_cmd_sts_tbl, xcvrd_show_hwmode_swmode_rsp_tbl, asic_index, port)
        assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_show_mux_switchmode_cmd_arg_tbl_notification_with_instance_manual(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"state": "manual"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = 0
                    self.SWITCHING_MODE_MANUAL = 0
                    self.SWITCHING_MODE_AUTO = 1

                def get_read_side(self):
                    return 1

                def get_switching_mode(self):
                    return 0

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_show_hwmode_swmode_cmd_arg_tbl_notification(
                fvp, xcvrd_show_hwmode_swmode_cmd_sts_tbl, xcvrd_show_hwmode_swmode_rsp_tbl, asic_index, port)
            assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_mux_switchmode_cmd_arg_tbl_notification_no_instance(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_rsp_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"state": "manual"}

        rc = handle_show_hwmode_swmode_cmd_arg_tbl_notification(
            fvp, xcvrd_show_hwmode_swmode_cmd_sts_tbl, xcvrd_show_hwmode_swmode_rsp_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_show_mux_switchmode_cmd_arg_tbl_notification_with_instance_auto(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_swmode_rsp_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"state": "auto"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"
                    self.SWITCHING_MODE_MANUAL = 0
                    self.SWITCHING_MODE_AUTO = 1

                def get_read_side(self):
                    return 1

                def get_switching_mode(self):
                    return 1

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_show_hwmode_swmode_cmd_arg_tbl_notification(
                fvp, xcvrd_show_hwmode_swmode_cmd_sts_tbl, xcvrd_show_hwmode_swmode_rsp_tbl, asic_index, port)
            assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_mux_state_cmd_arg_tbl_notification_no_port(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        hw_mux_cable_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"config": "active"}

        rc = handle_config_hwmode_state_cmd_arg_tbl_notification(
            fvp, xcvrd_config_hwmode_state_cmd_sts_tbl,  xcvrd_config_hwmode_state_rsp_tbl, hw_mux_cable_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_mux_switchmode_cmd_arg_tbl_notification_else_condition(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        hw_mux_cable_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"down_firmware": "null"}

        rc = handle_config_hwmode_state_cmd_arg_tbl_notification(
            fvp, xcvrd_config_hwmode_state_cmd_sts_tbl,  xcvrd_config_hwmode_state_rsp_tbl, hw_mux_cable_tbl, asic_index, port)
        assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_config_mux_state_cmd_arg_tbl_notification_with_instance_manual(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        hw_mux_cable_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"config": "active"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = 0
                    self.SWITCHING_MODE_MANUAL = 0
                    self.SWITCHING_MODE_AUTO = 1

                def get_read_side(self):
                    return 1

                def get_switching_mode(self):
                    return 0

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_config_hwmode_state_cmd_arg_tbl_notification(
                fvp, xcvrd_config_hwmode_state_cmd_sts_tbl,  xcvrd_config_hwmode_state_rsp_tbl, hw_mux_cable_tbl, asic_index, port)
            assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_config_mux_state_cmd_arg_tbl_notification_with_instance_cmd_arg(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        hw_mux_cable_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"config": "active"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = 0
                    self.SWITCHING_MODE_MANUAL = 0
                    self.SWITCHING_MODE_AUTO = 1

                def get_read_side(self):
                    return 3

                def get_switching_mode(self):
                    return 0

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_config_hwmode_state_cmd_arg_tbl_notification(
                fvp, xcvrd_config_hwmode_state_cmd_sts_tbl,  xcvrd_config_hwmode_state_rsp_tbl, hw_mux_cable_tbl, asic_index, port)
            assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_config_mux_state_cmd_arg_tbl_notification_no_instance(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        hw_mux_cable_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"config": "active"}

        rc = handle_config_hwmode_state_cmd_arg_tbl_notification(
            fvp, xcvrd_config_hwmode_state_cmd_sts_tbl,  xcvrd_config_hwmode_state_rsp_tbl, hw_mux_cable_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_config_mux_state_cmd_arg_tbl_notification_with_instance_auto(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        hw_mux_cable_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"config": "active"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"
                    self.SWITCHING_MODE_MANUAL = 0
                    self.SWITCHING_MODE_AUTO = 1

                def get_read_side(self):
                    return 1

                def get_switching_mode(self):
                    return 1

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_config_hwmode_state_cmd_arg_tbl_notification(
                fvp, xcvrd_config_hwmode_state_cmd_sts_tbl,  xcvrd_config_hwmode_state_rsp_tbl, hw_mux_cable_tbl, asic_index, port)
            assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_mux_state_cmd_arg_tbl_notification_no_port(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_hwmode_dir_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_res_tbl = mock_swsscommon_table
        hw_mux_cable_tbl =mock_swsscommon_table
        port_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"state": "active"}

        rc = handle_show_hwmode_state_cmd_arg_tbl_notification(
            fvp, port_tbl, xcvrd_show_hwmode_dir_cmd_sts_tbl, xcvrd_show_hwmode_dir_rsp_tbl, xcvrd_show_hwmode_dir_res_tbl, hw_mux_cable_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_mux_state_cmd_arg_tbl_notification_else_condition(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_hwmode_dir_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_res_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        hw_mux_cable_tbl =mock_swsscommon_table
        port_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"down_firmware": "null"}

        rc = handle_show_hwmode_state_cmd_arg_tbl_notification(
            fvp, port_tbl, xcvrd_show_hwmode_dir_cmd_sts_tbl, xcvrd_show_hwmode_dir_rsp_tbl, xcvrd_show_hwmode_dir_res_tbl, hw_mux_cable_tbl, asic_index, port)
        assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-standby")))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_show_mux_state_cmd_arg_tbl_notification_with_instance_manual(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_hwmode_dir_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_res_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        port_tbl = mock_swsscommon_table
        hw_mux_cable_tbl =mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"state": "active"}

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = 0
                    self.SWITCHING_MODE_MANUAL = 0
                    self.SWITCHING_MODE_AUTO = 1

                def get_read_side(self):
                    return 1

                def get_mux_direction(self):
                    return 1

                def get_switching_mode(self):
                    return 0

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_show_hwmode_state_cmd_arg_tbl_notification(
                fvp, port_tbl, xcvrd_show_hwmode_dir_cmd_sts_tbl, xcvrd_show_hwmode_dir_rsp_tbl, xcvrd_show_hwmode_dir_res_tbl, hw_mux_cable_tbl, asic_index, port)
            assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "fec", {"modex": "0",
                                                                                                                              "lane_mask": "0",
                                                                                                                              "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-standby")))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_handle_show_mux_state_cmd_arg_tbl_notification_no_instance(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_table.get = MagicMock(
            side_effect=[(True, (('state', "auto"), ("soc_ipv4", "192.168.0.1/32"))), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        xcvrd_show_hwmode_dir_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_res_tbl = mock_swsscommon_table
        hw_mux_cable_tbl =mock_swsscommon_table
        port_tbl = mock_swsscommon_table

        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        fvp = {"state": "active"}

        rc = handle_show_hwmode_state_cmd_arg_tbl_notification(
            fvp, port_tbl, xcvrd_show_hwmode_dir_cmd_sts_tbl, xcvrd_show_hwmode_dir_rsp_tbl, xcvrd_show_hwmode_dir_res_tbl, hw_mux_cable_tbl, asic_index, port)
        assert(rc == -1)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.gather_arg_from_db_and_check_for_type', MagicMock(return_value=(0, "activate_firmware", {"modex": "0",
                                                                                                                                            "lane_mask": "0",
                                                                                                                                            "direction": "0"})))
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-standby")))
    @patch('os.path.isfile', MagicMock(return_value=True))
    @patch('time.sleep', MagicMock(return_value=True))
    def test_handle_show_mux_state_cmd_arg_tbl_notification_with_instance_auto_active_standby(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_table.get = MagicMock(
            side_effect=[(True, (('state', "auto"), ("soc_ipv4", "192.168.0.1/32"))), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_res_tbl = mock_swsscommon_table
        port_tbl = mock_swsscommon_table
        asic_index = 0
        task_download_firmware_thread = {}
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"state": "active"}
        hw_mux_cable_tbl = {}
        test_db = "TEST_DB"
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")

        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_FAILED = 2
                    self.download_firmware_status = 0
                    self.SWITCH_COUNT_MANUAL = "manual"
                    self.SWITCH_COUNT_AUTO = "auto"
                    self.SWITCHING_MODE_MANUAL = 0
                    self.SWITCHING_MODE_AUTO = 1

                def get_read_side(self):
                    return 1

                def get_switching_mode(self):
                    return 1

                def get_mux_direction(self):
                    return 2

            patched_util.get.return_value = PortInstanceHelper()
            rc = handle_show_hwmode_state_cmd_arg_tbl_notification(
                fvp, port_tbl, xcvrd_show_hwmode_dir_cmd_sts_tbl, xcvrd_show_hwmode_dir_rsp_tbl, xcvrd_show_hwmode_dir_res_tbl, hw_mux_cable_tbl, asic_index, port)
            assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    def test_handle_show_mux_state_cmd_arg_tbl_notification_with_instance_auto_active_active_none(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_table.get = MagicMock(
            side_effect=[(True, (('state', "auto"), ("soc_ipv4", "192.168.0.1/32"))), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_res_tbl = mock_swsscommon_table
        port_tbl = mock_swsscommon_table
        asic_index = 0
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"state": "active"}
        swsscommon.Table.return_value.get.return_value = (
                True, {"read_side": "2", "state": "active"})
        hw_mux_cable_tbl = {}
        test_db = "TEST_DB"
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")

        rc = handle_show_hwmode_state_cmd_arg_tbl_notification(
            fvp, port_tbl, xcvrd_show_hwmode_dir_cmd_sts_tbl, xcvrd_show_hwmode_dir_rsp_tbl, xcvrd_show_hwmode_dir_res_tbl, hw_mux_cable_tbl, asic_index, port)
        assert(rc == None)

    @patch('swsscommon.swsscommon.Table')
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('ycable.ycable_utilities.y_cable_helper.get_ycable_physical_port_from_logical_port', MagicMock(return_value=(0)))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    def test_handle_show_mux_state_cmd_arg_tbl_notification_with_instance_auto_active_active(self, mock_swsscommon_table, platform_sfputil):

        mock_table = MagicMock()
        mock_table.get = MagicMock(
            side_effect=[(True, (('state', "auto"), ("soc_ipv4", "192.168.0.1/32"))), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        xcvrd_config_hwmode_state_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_config_hwmode_state_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_cmd_sts_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_rsp_tbl = mock_swsscommon_table
        xcvrd_show_hwmode_dir_res_tbl = mock_swsscommon_table
        port_tbl = mock_swsscommon_table
        asic_index = 0
        port = "Ethernet0"
        platform_sfputil.get_asic_id_for_logical_port = 0
        fvp = {"state": "active"}
        swsscommon.Table.return_value.get.return_value = (
                False, {"read_side": "2", "state": "active"})
        hw_mux_cable_tbl = {}
        test_db = "TEST_DB"
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")

        rc = handle_show_hwmode_state_cmd_arg_tbl_notification(
            fvp, port_tbl, xcvrd_show_hwmode_dir_cmd_sts_tbl, xcvrd_show_hwmode_dir_rsp_tbl, xcvrd_show_hwmode_dir_res_tbl, hw_mux_cable_tbl, asic_index, port)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.setup_grpc_channel_for_port', MagicMock(return_value=(None,None)))
    def test_retry_setup_grpc_channel_for_port_incorrect(self):

        status = False
        fvs = [('state', "auto"), ('read_side', 1)]
        Table = MagicMock()
        Table.get.return_value = (status, fvs)
        swsscommon.Table.return_value.get.return_value = (
                False, {"cable_type": "active-active", "soc_ipv4":"192.168.0.1/32", "state":"active"})
        port_tbl = {}
        test_db = "TEST_DB"
        asic_index = 0
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        grpc_client , fwd_state_response_tbl = {}, {}
        rc = retry_setup_grpc_channel_for_port("Ethernet0", 0, port_tbl, grpc_client, fwd_state_response_tbl)
        assert(rc == False)

    @patch('ycable.ycable_utilities.y_cable_helper.setup_grpc_channel_for_port', MagicMock(return_value=(None,None)))
    def test_retry_setup_grpc_channel_for_port_correct_none_val(self):

        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        Table = MagicMock()
        Table.get.return_value = (status, fvs)
        swsscommon.Table.return_value.get.return_value = (
                True, {"cable_type": "active-active", "soc_ipv4":"192.168.0.1/32", "state":"active"})
        port_tbl = {}
        test_db = "TEST_DB"
        asic_index = 0
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        grpc_client , fwd_state_response_tbl = {}, {}
        rc = retry_setup_grpc_channel_for_port("Ethernet0", 0, port_tbl, grpc_client, fwd_state_response_tbl)
        assert(rc == False)

    def test_process_loopback_interface_and_get_read_side_rc(self):

        loopback_keys = [["Loopback3|10.212.64.2/3", "Loopback3|2603:1010:100:d::1/128"]]
        rc = process_loopback_interface_and_get_read_side(loopback_keys)
        assert(rc == 0)
        Table = MagicMock()
        Table.get.return_value = (status, fvs)
        swsscommon.Table.return_value.get.return_value = (
                True, {"cable_type": "active-active", "soc_ipv4":"192.168.0.1/32", "state":"active"})
        port_tbl = {}
        test_db = "TEST_DB"
        asic_index = 0
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        grpc_client , fwd_state_response_tbl = {}, {}
        rc = retry_setup_grpc_channel_for_port("Ethernet0", 0 , port_tbl, grpc_client, fwd_state_response_tbl )
        assert(rc == False)

    @patch('ycable.ycable_utilities.y_cable_helper.setup_grpc_channel_for_port', MagicMock(return_value=(True,True)))
    def test_retry_setup_grpc_channel_for_port_correct(self):

        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        Table = MagicMock()
        Table.get.return_value = (status, fvs)
        swsscommon.Table.return_value.get.return_value = (
                True, {"cable_type": "active-active", "soc_ipv4":"192.168.0.1/32", "state":"active"})
        port_tbl = {}
        test_db = "TEST_DB"
        asic_index = 0
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        grpc_client , fwd_state_response_tbl = {}, {}
        rc = retry_setup_grpc_channel_for_port("Ethernet0", 0, port_tbl, grpc_client, fwd_state_response_tbl)
        assert(rc == True)

    @patch('ycable.ycable_utilities.y_cable_helper.setup_grpc_channel_for_port', MagicMock(return_value=(None,None)))
    def test_retry_setup_grpc_channel_for_port_correct_none_val(self):

        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        Table = MagicMock()
        Table.get.return_value = (status, fvs)
        swsscommon.Table.return_value.get.return_value = (
                True, {"cable_type": "active-active", "soc_ipv4":"192.168.0.1/32", "state":"active"})
        port_tbl = {}
        test_db = "TEST_DB"
        asic_index = 0
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        grpc_client , fwd_state_response_tbl = {}, {}
        rc = retry_setup_grpc_channel_for_port("Ethernet0", 0, port_tbl, grpc_client, fwd_state_response_tbl)
        assert(rc == False)

    def test_process_loopback_interface_and_get_read_side_rc(self):

        loopback_keys = [["Loopback3|10.212.64.2/3", "Loopback3|2603:1010:100:d::1/128"]]
        rc = process_loopback_interface_and_get_read_side(loopback_keys)
        assert(rc == 0)

    def test_process_loopback_interface_and_get_read_side_rc_true(self):

        loopback_keys = [["Loopback3|10.212.64.1/3", "Loopback3|2603:1010:100:d::1/128"]]
        rc = process_loopback_interface_and_get_read_side(loopback_keys)
        assert(rc == 1)

    def test_process_loopback_interface_and_get_read_side_false(self):

        loopback_keys = [["Loopback2|10.212.64.1/3", "Loopback3|2603:1010:100:d::1/128"]]
        rc = process_loopback_interface_and_get_read_side(loopback_keys)
        assert(rc == -1)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_setup_channel(self):

        status = True
        fvs = [('state', "auto"), ('read_side', 1), ('cable_type','active-active'), ('soc_ipv4','192.168.0.1')]

        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        hw_mux_cable_tbl = {}
        hw_mux_cable_tbl_peer = {}
        port_tbl = {}
        read_side = 0
        asic_index = 0
        y_cable_presence = [True]
        delete_change_event = [True]

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "HW_TABLE1")
        hw_mux_cable_tbl_peer[asic_index] = swsscommon.Table(
            test_db[asic_index], "HW_TABLE2")
        grpc_client , fwd_state_response_tbl = {}, {}
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "MUX_INFO_TABLE")

        rc = check_identifier_presence_and_setup_channel("Ethernet0", port_tbl, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index, read_side, mux_tbl, y_cable_presence, grpc_client, fwd_state_response_tbl)

        assert(rc == None)

    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_setup_channel_with_false_status(self):

        status = False
        fvs = [('state', "auto"), ('read_side', 1), ('cable_type','active-active'), ('soc_ipv4','192.168.0.1')]

        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        hw_mux_cable_tbl = {}
        hw_mux_cable_tbl_peer = {}
        port_tbl = {}
        read_side = 0
        asic_index = 0
        y_cable_presence = [True]
        delete_change_event = [True]
        swsscommon.Table.return_value.get.return_value = (
            False, {"config": "1"})

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "HW_TABLE1")
        hw_mux_cable_tbl_peer[asic_index] = swsscommon.Table(
            test_db[asic_index], "HW_TABLE2")
        grpc_client , fwd_state_response_tbl = {}, {}
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "MUX_INFO_TABLE")

        rc = check_identifier_presence_and_setup_channel("Ethernet0", port_tbl, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index, read_side, mux_tbl, y_cable_presence, grpc_client, fwd_state_response_tbl)

        assert(rc == None)


    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.setup_grpc_channel_for_port', MagicMock(return_value=(None, None)))
    def test_check_identifier_presence_and_setup_channel_with_mock(self):

        status = True
        fvs = [('state', "auto"), ('read_side', 1), ('cable_type','active-active'), ('soc_ipv4','192.168.0.1')]

        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        hw_mux_cable_tbl = {}
        hw_mux_cable_tbl_peer = {}
        port_tbl = {}
        read_side = 0
        asic_index = 0
        y_cable_presence = [True]
        delete_change_event = [True]

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "HW_TABLE1")
        hw_mux_cable_tbl_peer[asic_index] = swsscommon.Table(
            test_db[asic_index], "HW_TABLE2")
        grpc_client , fwd_state_response_tbl = {}, {}

        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "MUX_INFO_TABLE")

        rc = check_identifier_presence_and_setup_channel("Ethernet0", port_tbl, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index, read_side, mux_tbl, y_cable_presence, grpc_client, fwd_state_response_tbl)
        assert(rc == None)


    @patch('ycable.ycable_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('ycable.ycable_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('ycable.ycable_utilities.y_cable_helper.setup_grpc_channel_for_port', MagicMock(return_value=(None, None)))
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_stubs', MagicMock(return_value={}))
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_channels', MagicMock(return_value={}))
    def test_check_identifier_presence_and_setup_channel_with_mock_not_none(self):

        status = True
        fvs = [('state', "auto"), ('read_side', 1), ('cable_type','active-active'), ('soc_ipv4','192.168.0.1')]

        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        hw_mux_cable_tbl = {}
        hw_mux_cable_tbl_peer = {}
        port_tbl = {}
        read_side = 0
        asic_index = 0
        y_cable_presence = [True]
        delete_change_event = [True]

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "HW_TABLE1")
        hw_mux_cable_tbl_peer[asic_index] = swsscommon.Table(
            test_db[asic_index], "HW_TABLE2")
        grpc_client , fwd_state_response_tbl = {}, {}
        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "MUX_INFO_TABLE")

        rc = check_identifier_presence_and_setup_channel("Ethernet0", port_tbl, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index, read_side, mux_tbl, y_cable_presence, grpc_client, fwd_state_response_tbl)

        assert(rc == None)

    @patch('proto_out.linkmgr_grpc_driver_pb2_grpc.DualToRActiveStub', MagicMock(return_value=True))
    def test_setup_grpc_channel_for_port(self):

        status = True
        fvs = [('state', "auto"), ('read_side', 1), ('cable_type','active-standby'), ('soc_ipv4','192.168.0.1')]
        grpc_client , fwd_state_response_tbl = {}, {}
        asic_index = 0
        Table = MagicMock()
        Table.get.return_value = (status, fvs)
        #swsscommon.Table.return_value.get.return_value = (
        #        True, { 'config', {'type': 'secure'}})
        swsscommon.Table.return_value.get.return_value = (
            True, {"config": "1"})
        test_db = "TEST_DB"
        asic_index = 0
        grpc_client[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0
            (channel, stub) = setup_grpc_channel_for_port("Ethernet0", "192.168.0.1", asic_index, grpc_client, fwd_state_response_tbl, False)

        assert(stub == True)
        assert(channel != None)

    @patch('proto_out.linkmgr_grpc_driver_pb2_grpc.DualToRActiveStub', MagicMock(return_value=True))
    def test_setup_grpc_channel_for_port_get_false(self):

        status = False
        fvs = [('state', "auto"), ('read_side', 1), ('cable_type','active-standby'), ('soc_ipv4','192.168.0.1')]
        grpc_client , fwd_state_response_tbl = {}, {}
        asic_index = 0
        Table = MagicMock()
        Table.get.return_value = (status, fvs)
        #swsscommon.Table.return_value.get.return_value = (
        #        True, { 'config', {'type': 'secure'}})
        swsscommon.Table.return_value.get.return_value = (
            False, {"config": "1"})
        test_db = "TEST_DB"
        asic_index = 0
        grpc_client[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0
            (channel, stub) = setup_grpc_channel_for_port("Ethernet0", "192.168.0.1", asic_index, grpc_client, fwd_state_response_tbl, False)

        assert(stub == True)
        assert(channel != None)



    def test_connect_channel(self):

        with patch('grpc.channel_ready_future') as patched_util:

            patched_util.result.return_value = 0
            rc = connect_channel(patched_util, None, None)
            assert(rc == None)

    def test_setup_grpc_channels(self):

        stop_event = MagicMock()
        stop_event.is_set.return_value = False
        with patch('ycable.ycable_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.logical.return_value = ['Ethernet0', 'Ethernet4']
            patched_util.get_asic_id_for_logical_port.return_value = 0
            loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, port_tbl, loopback_tbl, port_table_keys, grpc_client, fwd_state_response_tbl = {}, {}, {}, {}, {}, {}, {}, {}
            rc = setup_grpc_channels(stop_event, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, port_tbl, loopback_tbl, port_table_keys, grpc_client, fwd_state_response_tbl)

            assert(rc == None)


    def test_check_mux_cable_port_type_get_none(self):

        stop_event = MagicMock()
        test_db = "TEST_DB"
        status = False
        asic_index = 0
        fvs = [('state', "auto"), ('read_side', 1), ('cable_type','active-active'), ('soc_ipv4','192.168.0.1')]
        stop_event.is_set.return_value = False
        port_tbl = {}
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        
        rc = check_mux_cable_port_type("Ethernet0", port_tbl, 0)
        assert(rc == (False, None))


    def test_check_mux_cable_port_type_get_correct(self):

        stop_event = MagicMock()
        status = True
        asic_index = 0
        test_db = "TEST_DB"
        fvs = [('state', "auto"), ('read_side', 1), ('cable_type','active-active'), ('soc_ipv4','192.168.0.1')]
        stop_event.is_set.return_value = False
        port_tbl = {}
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        
        rc = check_mux_cable_port_type("Ethernet0", port_tbl, 0)
        assert(rc == (True, "active-active"))


    def test_check_mux_cable_port_type_get_correct_standby(self):

        stop_event = MagicMock()
        status = True
        asic_index = 0
        test_db = "TEST_DB"
        fvs = [('state', "auto"), ('read_side', 1), ('cable_type','active-standby'), ('soc_ipv4','192.168.0.1')]
        stop_event.is_set.return_value = False
        port_tbl = {}
        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)
        
        rc = check_mux_cable_port_type("Ethernet0", port_tbl, 0)
        assert(rc == (True, "active-standby"))


    def test_parse_grpc_response_hw_mux_cable_change_state(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0]
                self.state = [True]


        response = Response_Helper()
        
        rc = parse_grpc_response_hw_mux_cable_change_state(True, response, 0, "Ethernet0")
        assert(rc == "active")


    def test_parse_grpc_response_hw_mux_cable_change_state_standby(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0]
                self.state = [False]


        response = Response_Helper()
        
        rc = parse_grpc_response_hw_mux_cable_change_state(True, response, 0, "Ethernet0")
        assert(rc == "standby")


    def test_parse_grpc_response_hw_mux_cable_change_state_unknown(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [1]
                self.state = [False]


        response = Response_Helper()
        
        rc = parse_grpc_response_hw_mux_cable_change_state(True, response, 0, "Ethernet0")
        assert(rc == "unknown")


    def test_parse_grpc_response_hw_mux_cable_change_state_unknown_false(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [1]
                self.state = [False]


        response = Response_Helper()
        
        rc = parse_grpc_response_hw_mux_cable_change_state(False, response, 0, "Ethernet0")
        assert(rc == "unknown")


    def test_parse_grpc_response_forwarding_state_unknown_false(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [1]
                self.state = [False]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(False, None, 0, port)
        assert(rc == ("unknown", "unknown"))


    def test_parse_grpc_response_forwarding_state_active_standby_true(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True,False]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 0, port)
        assert(rc == ("active", "standby"))


    def test_parse_grpc_response_forwarding_state_active_active_true(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True,True]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 0, port)
        assert(rc == ("active", "active"))


    def test_parse_grpc_response_forwarding_state_active_standby_true_read_side(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True,False]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 1, port)
        assert(rc == ("standby", "active"))


    def test_parse_grpc_response_forwarding_state_active_active_true_read_side(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True,True]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 1, port)
        assert(rc == ("active", "active"))


    def test_parse_grpc_response_forwarding_state_active_active_true(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True,True]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 1, port)
        assert(rc == ("active", "active"))


    def test_parse_grpc_response_forwarding_state_active_standby_true(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [False,True]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 1, port)
        assert(rc == ("standby", "active"))


    def test_parse_grpc_response_forwarding_state_active_standby_true(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [False,True]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 0, port)
        assert(rc == ("standby", "active"))


    def test_parse_grpc_response_forwarding_state_standby_standby_true(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [False,False]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 1, port)
        assert(rc == ("standby", "standby"))


    def test_parse_grpc_response_forwarding_state_standby_standby_true(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [False,False]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 0, port)
        assert(rc == ("standby", "standby"))


    def test_parse_grpc_response_forwarding_state_active_active_with_true_read_side(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True,True]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 0, port)
        assert(rc == ("active", "active"))


    def test_parse_grpc_response_forwarding_state_standby_standby_with_true_read_side(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [False,False]


        response = Response_Helper()
        port = "Ethernet4"
        
        rc = parse_grpc_response_forwarding_state(True, response, 1, port)
        assert(rc == ("standby", "standby"))


    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_stubs', MagicMock(return_value={}))
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_channels', MagicMock(return_value={}))
    def test_parse_grpc_response_forwarding_state_standby_standby_with_true_read_side(self):

        status = True
        asic_index = 0
        test_db = "TEST_DB"
        port = "Ethernet0"
        fvs_m = [('command', "probe"), ('read_side', 1), ('cable_type','active-standby'), ('soc_ipv4','192.168.0.1')]
        hw_mux_cable_tbl = {}
        fwd_state_response_tbl = {}
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        fwd_state_response_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        hw_mux_cable_tbl[asic_index].get.return_value = (status, fvs_m)
        
        rc = handle_fwd_state_command_grpc_notification(fvs_m, hw_mux_cable_tbl, fwd_state_response_tbl, asic_index, port, "TestDB")
        assert(rc == True)

    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_stubs', MagicMock(return_value={}))
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_channels', MagicMock(return_value={}))
    def test_parse_grpc_response_forwarding_state_standby_standby_with_true_read_side(self):

        status = True
        asic_index = 0
        test_db = "TEST_DB"
        port = "Ethernet0"
        fvs_m = [('command', "probe"), ('read_side', 1), ('cable_type','active-standby'), ('soc_ipv4','192.168.0.1')]
        hw_mux_cable_tbl = {}
        hw_mux_cable_tbl_peer = {}
        fwd_state_response_tbl = {}
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        hw_mux_cable_tbl_peer[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        fwd_state_response_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        hw_mux_cable_tbl[asic_index].get.return_value = (status, fvs_m)
        
        rc = put_init_values_for_grpc_states(port, '0', hw_mux_cable_tbl, hw_mux_cable_tbl_peer, 0)
        assert(rc == None)
        
        
    def test_get_mux_cable_static_info_without_presence(self):

        rc = get_muxcable_static_info_without_presence()

        assert(rc['read_side'] == '-1')
        assert(rc['nic_lane1_precursor1'] == 'N/A')
        assert(rc['nic_lane1_precursor1'] == 'N/A')
        assert(rc['nic_lane1_postcursor1'] == 'N/A')
        assert(rc['nic_lane1_postcursor2'] == 'N/A')

    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_get_grpc_credentials(self):
        
        kvp = {}
        type = None

        rc = get_grpc_credentials(type, kvp)

        assert(rc == None)


    @patch('builtins.open')
    @patch('os.path.isfile', MagicMock(return_value=True))
    def test_get_grpc_credentials_root(self, open):
        
        kvp = {"ca_crt": "file"}
        type = "server" 

        mock_file = MagicMock()
        mock_file.read = MagicMock(return_value=bytes('abcdefgh', 'utf-8'))
        open.return_value = mock_file
        rc = get_grpc_credentials(type, kvp)

        assert(rc != None)


    @patch('ycable.ycable_utilities.y_cable_helper.disable_telemetry')
    def test_handle_ycable_enable_disable_tel_notification(self, patch):

        fvp_m = {"disable_telemetry": "True"}
        rc = handle_ycable_enable_disable_tel_notification(fvp_m, "Y_CABLE")
        assert(rc == None)

    def test_handle_ycable_enable_disable_tel_notification_probe(self):

        fvp_m = {"log_verbosity": "notice"}
        rc = handle_ycable_enable_disable_tel_notification(fvp_m, "Y_CABLE")
        assert(rc == None)

        fvp_m = {"log_verbosity": "debug"}
        rc = handle_ycable_enable_disable_tel_notification(fvp_m, "Y_CABLE")
        assert(rc == None)


    @patch('builtins.open')
    def test_apply_grpc_secrets_configuration(self, open):

        parsed_data = {'GRPCCLIENT': {'config': {'type': 'secure', 'auth_level': 'server', 'log_level': 'info'}, 'certs': {'client_crt': 'one.crt', 'client_key': 'one.key', 'ca_crt': 'ss.crt', 'grpc_ssl_credential': 'jj.tsl'}}}

        asic_index = 0
        grpc_client = {}
        test_db = {}
        test_db[asic_index] = 'xyz'
        grpc_client[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        #json_load.return_value = parsed_data
        with patch('json.load') as patched_util:
            patched_util.return_value = parsed_data
            rc = apply_grpc_secrets_configuration(None, grpc_client)
            assert(rc == None)



    def test_handle_ycable_active_standby_probe_notification(self):

        test_db = "TEST_DB"
        status = True
        port_m = "Ethernet0"
        fvp_m = [('command', "probe"), ('read_side', 1), ('cable_type','active-standby'), ('soc_ipv4','192.168.0.1')]
        fvp_dict = {"command": "probe"}
        hw_mux_cable_tbl = {}
        y_cable_response_tbl = {}
        asic_index = 0
        hw_mux_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        y_cable_response_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        hw_mux_cable_tbl[asic_index].get.return_value = (status, fvp_m)

        rc = handle_ycable_active_standby_probe_notification("active-standby", fvp_dict, test_db, hw_mux_cable_tbl, port_m, asic_index, y_cable_response_tbl)
        assert(rc == True)


    def test_parse_grpc_response_link_and_oper_state_down_down(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [False,False]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 1, "oper_state", "Ethernet4")
        assert(rc == ("down", "down"))

    def test_parse_grpc_response_link_and_oper_state_up_down(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True,False]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 1, "oper_state", "Ethernet4")
        assert(rc == ("down", "up"))

    def test_parse_grpc_response_link_and_oper_state_up_up(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True, True]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 1, "oper_state", "Ethernet4")
        assert(rc == ("up", "up"))
        
    def test_parse_grpc_response_link_and_oper_state_down_down_read_side_zero(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [False,False]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 0, "oper_state", "Ethernet4")
        assert(rc == ("down", "down"))

    def test_parse_grpc_response_link_and_oper_state_up_down_read_side_zero(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True,False]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 0, "oper_state", "Ethernet4")
        assert(rc == ("up", "down"))

    def test_parse_grpc_response_link_and_oper_state_up_up_read_side_zero(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True, True]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 0, "oper_state", "Ethernet4")
        assert(rc == ("up", "up"))
        
    def test_parse_grpc_response_link_and_oper_state_down_down_read_side_zero_unknown(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [False,False]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(False, response, 0, "oper_state", "Ethernet4")
        assert(rc == ("unknown", "unknown"))

    def test_parse_grpc_response_link_and_oper_state_up_down_read_side_zero(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0]
                self.state = [False]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 0, "oper_state", "Ethernet4")
        assert(rc == ("unknown", "unknown"))

    def test_parse_grpc_response_link_and_oper_state_up_up_read_side_zero(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 0, "link_state", "Ethernet4")
        assert(rc == ("unknown", "unknown"))
        
    def test_parse_grpc_response_link_and_oper_state_down_down_read_side_zero_link_state(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [False,False]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 0, "link_state", "Ethernet4")
        assert(rc == ("down", "down"))

    def test_parse_grpc_response_link_and_oper_state_up_down_read_side_zero_link_state(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True,False]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 0, "link_state", "Ethernet4")
        assert(rc == ("up", "down"))

    def test_parse_grpc_response_link_and_oper_state_up_up_read_side_zero_link_state(self):

        class Response_Helper():
            def __init__(self):
                self.portid = [0,1]
                self.state = [True, True]


        response = Response_Helper()
        
        rc = parse_grpc_response_link_and_oper_state(True, response, 0, "link_state", "Ethernet4")
        assert(rc == ("up", "up"))
        
    def test_get_muxcable_info_for_active_active(self):
        physical_port = 20

        logical_port_name = "Ethernet20"
        swsscommon.Table.return_value.get.return_value = (
            True, {"read_side": "1"})
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)

        rc = get_muxcable_info_for_active_active(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

        assert(rc['self_mux_direction'] == 'unknown')
        assert(rc['peer_mux_direction'] == 'unknown')
        assert(rc['mux_direction_probe_count'] == 'unknown')
        assert(rc['peer_mux_direction_probe_count'] == 'unknown')

    def test_get_muxcable_info_for_active_active_with_false(self):
        physical_port = 20

        logical_port_name = "Ethernet20"
        swsscommon.Table.return_value.get.return_value = (
            False, {"read_side": "1"})
        asic_index = 0
        y_cable_tbl = {}
        mux_tbl = {}
        test_db = "TEST_DB"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        y_cable_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "Y_CABLE_TABLE")
        y_cable_tbl[asic_index].get.return_value = (status, fvs)

        rc = get_muxcable_info_for_active_active(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

        assert(rc != None)




    @patch("grpc.aio.secure_channel")
    @patch("proto_out.linkmgr_grpc_driver_pb2_grpc.GracefulRestartStub")
    def test_ycable_graceful_client(self, channel, stub):


        mock_channel = MagicMock()
        channel.return_value = mock_channel

        mock_stub = MagicMock()
        mock_stub.NotifyGracefulRestartStart = MagicMock(return_value=[4, 5])
        stub.return_value = mock_stub


        read_side = 1
        Y_cable_restart_client = GracefulRestartClient("Ethernet48", None, read_side)


class TestYcableScriptExecution(object):

    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.Select.TIMEOUT', MagicMock(return_value=None))
    @patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj', MagicMock())
    #@patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj.getDbConnector', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    def test_ycable_helper_cli_worker(self, mock_select, mock_sub_table):

        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(
            side_effect=[('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable

        stop_event = threading.Event()
        
        asic_index = 0
        Y_cable_cli_task = YCableCliUpdateTask()
        Y_cable_cli_task.task_stopping_event.is_set = MagicMock(side_effect=[False, True])

        #Y_cable_cli_task.task_stopping_event.is_set = MagicMock(side_effect=False)

        expected_exception_start = None
        expected_exception_join = None
            #Y_cable_cli_task.start()
        Y_cable_cli_task.task_cli_worker()
        Y_cable_cli_task.task_stopping_event.clear()
       
        assert swsscommon.Select.select.call_count == 1
        #y_cable_helper.handle_show_hwmode_state_cmd_arg_tbl_notification.assert_called() 
        Y_cable_cli_task_n = YCableCliUpdateTask()
        Y_cable_cli_task_n.task_stopping_event.is_set = MagicMock(side_effect=[False, True])

        mock_selectable.pop = MagicMock(
            side_effect=[('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)

        Y_cable_cli_task_n.task_cli_worker()
        assert swsscommon.Select.select.call_count == 2



    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.Select.TIMEOUT', MagicMock(return_value=None))
    @patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj', MagicMock())
    #@patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj.getDbConnector', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    def test_ycable_helper_cli_worker_execution(self, mock_select, mock_sub_table):

        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(
            side_effect=[(False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False) ,('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), (None, None, None), (None, None, None)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable

        stop_event = threading.Event()
        
        asic_index = 0
        Y_cable_cli_task = YCableCliUpdateTask()
        Y_cable_cli_task.task_stopping_event.is_set = MagicMock(side_effect=[False, True])
        Y_cable_cli_task.cli_table_helper.xcvrd_show_hwmode_dir_cmd_tbl[asic_index].return_value = mock_selectable

        #Y_cable_cli_task.task_stopping_event.is_set = MagicMock(side_effect=False)

        expected_exception_start = None
        expected_exception_join = None
        trace = None
        """
        try:
            #Y_cable_cli_task.start()
            Y_cable_cli_task.task_cli_worker()
            time.sleep(5)
            Y_cable_cli_task.task_stopping_event.clear()
        except Exception as e1:
            expected_exception_start  = e1
            trace = traceback.format_exc()
        """


    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.Select.TIMEOUT', MagicMock(return_value=None))
    @patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj', MagicMock())
    #@patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj.getDbConnector', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    #@patch('swsscommon.swsscommon.Table')
    def test_ycable_helper_table_worker(self, mock_select, mock_sub_table):

        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(
            side_effect=[('Ethernet0', swsscommon.SET_COMMAND, (('state', 'active'), )), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable


        Y_cable_task = YCableTableUpdateTask()
        Y_cable_task.task_stopping_event.is_set = MagicMock(side_effect=[False, True])
        mock_table = MagicMock()
        """mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(
            side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table
        """
        Y_cable_task.hw_mux_cable_tbl_keys = MagicMock(side_effect={0:["Ethernet0", "Ethernet4"]})
        Y_cable_task.task_worker()
        assert swsscommon.Select.select.call_count == 1


    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.Select.TIMEOUT', MagicMock(return_value=None))
    @patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj', MagicMock())
    #@patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj.getDbConnector', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    def test_ycable_helper_table_worker_active_active(self, mock_select, mock_sub_table):

        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(
            side_effect=[('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable


        Y_cable_task = YCableTableUpdateTask()
        Y_cable_task.task_stopping_event.is_set = MagicMock(side_effect=[False, True])
        Y_cable_task.task_worker()
        assert swsscommon.Select.select.call_count == 1



    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.Select.TIMEOUT', MagicMock(return_value=None))
    @patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj', MagicMock())
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_stubs', MagicMock(return_value={}))
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_channels', MagicMock(return_value={}))
    #@patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj.getDbConnector', MagicMock())
    @patch('swsscommon.swsscommon.FieldValuePairs', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    #@patch('swsscommon.swsscommon.Table')
    def test_ycable_helper_table_worker_probe_active_active(self, mock_select, mock_sub_table):

        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(
            side_effect=[(False, False, False), (False, False, False), (False, False, False), ('Ethernet0', swsscommon.SET_COMMAND, (('state', 'active'), )), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable


        Y_cable_task = YCableTableUpdateTask()
        Y_cable_task.task_stopping_event.is_set = MagicMock(side_effect=[False, True])
        """
        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(
            side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table
        """
        
        Y_cable_task.hw_mux_cable_tbl_keys = MagicMock(side_effect={0:["Ethernet0", "Ethernet4"]})
        Y_cable_task.task_worker()
        assert swsscommon.Select.select.call_count == 1







    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.Select.TIMEOUT', MagicMock(return_value=None))
    @patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj', MagicMock())
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_stubs', MagicMock(return_value={}))
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_channels', MagicMock(return_value={}))
    @patch('swsscommon.swsscommon.FieldValuePairs', MagicMock())
    #@patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj.getDbConnector', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    #@patch('swsscommon.swsscommon.Table')
    def test_ycable_helper_table_worker_probe_active(self, mock_select, mock_sub_table):

        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(
            side_effect=[(False, False, False), (False, False, False), ('Ethernet0', swsscommon.SET_COMMAND, (('state', 'active'), ('command', 'probe'),)), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable


        Y_cable_task = YCableTableUpdateTask()
        Y_cable_task.task_stopping_event.is_set = MagicMock(side_effect=[False, True])
        """
        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(
            side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table
        """
        
        Y_cable_task.hw_mux_cable_tbl_keys = MagicMock(side_effect={0:["Ethernet0", "Ethernet4"]})
        Y_cable_task.task_worker()
        assert swsscommon.Select.select.call_count == 1






    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.Select.TIMEOUT', MagicMock(return_value=None))
    @patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj', MagicMock())
    #@patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj.getDbConnector', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    #@patch('swsscommon.swsscommon.Table')
    def test_ycable_helper_table_worker_probe(self, mock_select, mock_sub_table):

        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(
            side_effect=[(False, False, False), ('Ethernet0', swsscommon.SET_COMMAND, (('state', 'active'), )), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable


        Y_cable_task = YCableTableUpdateTask()
        Y_cable_task.task_stopping_event.is_set = MagicMock(side_effect=[False, True])
        #mock_table = MagicMock()
        #mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        swsscommon.Table.return_value.get.return_value = (
                True, {"read_side": "1", "state":"active"})
        #mock_table.get = MagicMock(
        #    side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        swsscommon.Table.return_value.getKeys.return_value = (
            ['Ethernet0', 'Ethernet4'])
        #mock_swsscommon_table.return_value = mock_table
        
        Y_cable_task.task_worker()
        assert swsscommon.Select.select.call_count == 1


    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.Select.TIMEOUT', MagicMock(return_value=None))
    @patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj', MagicMock())
    #@patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj.getDbConnector', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    #@patch('swsscommon.swsscommon.Table')
    def test_ycable_helper_table_worker_toggle(self, mock_select, mock_sub_table):

        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(
            side_effect=[('Ethernet0', swsscommon.SET_COMMAND, (('state', 'active'), )), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable


        Y_cable_task = YCableTableUpdateTask()
        Y_cable_task.task_stopping_event.is_set = MagicMock(side_effect=[False, True])
        #mock_table = MagicMock()
        #mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        swsscommon.Table.return_value.get.return_value = (
                True, {"read_side": "1", "state":"active"})
        #mock_table.get = MagicMock(
        #    side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        swsscommon.Table.return_value.getKeys.return_value = (
            ['Ethernet0', 'Ethernet4'])
        #mock_swsscommon_table.return_value = mock_table
        
        Y_cable_task.task_worker()
        assert swsscommon.Select.select.call_count == 1


    @patch('ycable.ycable_utilities.y_cable_helper.check_mux_cable_port_type', MagicMock(return_value=(True,"active-active")))
    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.Select.TIMEOUT', MagicMock(return_value=None))
    @patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj', MagicMock())
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_stubs', MagicMock(return_value={}))
    @patch('ycable.ycable_utilities.y_cable_helper.grpc_port_channels', MagicMock(return_value={}))
    @patch('swsscommon.swsscommon.FieldValuePairs', MagicMock())
    #@patch('swsscommon.swsscommon.CastSelectableToRedisSelectObj.getDbConnector', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    #@patch('swsscommon.swsscommon.Table')
    def test_ycable_helper_table_worker_toggle_active_active(self, mock_select, mock_sub_table):

        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(
            side_effect=[('Ethernet0', swsscommon.SET_COMMAND, (('state', 'active'), ("command", "probe"),)), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False), (False, False, False)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable


        Y_cable_task = YCableTableUpdateTask()
        Y_cable_task.task_stopping_event.is_set = MagicMock(side_effect=[False, True])
        #mock_table = MagicMock()
        #mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        swsscommon.Table.return_value.get.return_value = (
                True, {"read_side": "1", "state":"active"})
        #mock_table.get = MagicMock(
        #    side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        swsscommon.Table.return_value.getKeys.return_value = (
            ['Ethernet0', 'Ethernet4'])
        #mock_swsscommon_table.return_value = mock_table
        
        Y_cable_task.task_worker()
        assert swsscommon.Select.select.call_count == 1


