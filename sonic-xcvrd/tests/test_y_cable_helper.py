from xcvrd.xcvrd_utilities.port_mapping import *
from xcvrd.xcvrd_utilities.sfp_status_helper import *
from xcvrd.xcvrd_utilities.y_cable_helper import *
from xcvrd.xcvrd import *
import copy
import os
import sys
import time

if sys.version_info >= (3, 3):
    from unittest.mock import MagicMock, patch
else:
    from mock import MagicMock, patch

from sonic_py_common import daemon_base
from swsscommon import swsscommon
from sonic_platform_base.sfp_base import SfpBase
from .mock_swsscommon import Table


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
        Y_cable_task = YCableTableUpdateTask(None)

    def test_y_cable_helper_format_mapping_identifier1(self):
        rc = format_mapping_identifier("ABC        ")
        assert(rc == "abc")

    def test_y_cable_helper_format_mapping_identifier_no_instance(self):
        rc = format_mapping_identifier(None)
        assert(rc == None)

    def test_y_cable_wrapper_get_transceiver_info(self):
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'Microsoft',
                                                                   'model': 'model1'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "Microsoft")
        assert(model == "model1")

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_chassis')
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

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_transceiver_info_with_platform_chassis_not_implemented(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_transceiver_info.side_effect = NotImplementedError
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'microsoft',
                                                                   'model': 'simulated'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "microsoft")
        assert(model == "simulated")

    def test_y_cable_wrapper_get_presence(self):
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_presence.return_value = True

            presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_presence_with_platform_chassis(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_presence = MagicMock(return_value=True)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_presence_with_platform_chassis_raise_exception(self, mock_chassis):

        mock_object = MagicMock(spec=SfpBase)
        mock_object.get_presence = MagicMock(side_effect=NotImplementedError)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_presence.return_value = True

            assert(y_cable_wrapper_get_presence(1) == True)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.get_muxcable_info', MagicMock(return_value={'tor_active': 'self',
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
        port_mapping = PortMapping()
        mux_tbl = Table("STATE_DB", y_cable_helper.MUX_CABLE_INFO_TABLE)
        rc = post_port_mux_info_to_db(logical_port_name, port_mapping, mux_tbl)
        assert(rc != -1)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.get_muxcable_static_info', MagicMock(return_value={'read_side': 'self',
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
        port_mapping = PortMapping()
        mux_tbl = Table("STATE_DB", y_cable_helper.MUX_CABLE_STATIC_INFO_TABLE)
        rc = post_port_mux_static_info_to_db(logical_port_name, port_mapping, mux_tbl)
        assert(rc != -1)

    def test_y_cable_helper_format_mapping_identifier1(self):
        rc = format_mapping_identifier("ABC        ")
        assert(rc == "abc")

    def test_y_cable_helper_format_mapping_identifier_no_instance(self):
        rc = format_mapping_identifier(None)
        assert(rc == None)

    def test_y_cable_wrapper_get_transceiver_info(self):
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'Microsoft',
                                                                   'model': 'model1'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "Microsoft")
        assert(model == "model1")

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_chassis')
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

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_transceiver_info_with_platform_chassis_not_implemented(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_transceiver_info.side_effect = NotImplementedError
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'microsoft',
                                                                   'model': 'simulated'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "microsoft")
        assert(model == "simulated")

    def test_y_cable_wrapper_get_presence(self):
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_presence.return_value = True

            presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_chassis')
    def test_y_cable_wrapper_get_presence_with_platform_chassis(self, mock_chassis):

        mock_object = MagicMock()
        mock_object.get_presence = MagicMock(return_value=True)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    def test_y_cable_toggle_mux_torA_update_status_true(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = y_cable_toggle_mux_torA(1)

        assert(rc == 1)

    def test_y_cable_toggle_mux_torA_no_port_instance(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as port_instance:

            port_instance.get.return_value = None
            rc = y_cable_toggle_mux_torA(1)

        assert(rc == -1)

    def test_y_cable_toggle_mux_torA_update_status_exception(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as port_instance:

            port_instance.get.return_value = "simulated_port"
            port_instance.toggle_mux_to_tor_a.return_value = Exception(NotImplementedError)

            rc = y_cable_toggle_mux_torA(1)

        assert(rc == -1)

    def test_y_cable_toggle_mux_torA_update_status_true(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = y_cable_toggle_mux_torA(1)

        assert(rc == 1)

    def test_y_cable_toggle_mux_torB_no_port_instance(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as port_instance:

            port_instance.get.return_value = None
            rc = y_cable_toggle_mux_torB(1)

        assert(rc == -1)

    def test_y_cable_toggle_mux_torB_update_status_exception(self):
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as port_instance:

            port_instance.get.return_value = "simulated_port"
            port_instance.toggle_mux_to_tor_a.return_value = Exception(NotImplementedError)

            rc = y_cable_toggle_mux_torB(1)

        assert(rc == -1)

    def test_y_cable_toggle_mux_torB_update_status_true(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_b.return_value = True
            patched_util.get.return_value = mock_toggle_object

            rc = y_cable_toggle_mux_torB(1)

        assert(rc == 2)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_1_active(self):
        read_side = 1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object
            port_mapping = PortMapping()

            rc = update_tor_active_side(read_side, state, logical_port_name, port_mapping)

        assert(rc == 1)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_2_active(self):
        read_side = 2
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_b.return_value = True
            patched_util.get.return_value = mock_toggle_object
            port_mapping = PortMapping()

            rc = update_tor_active_side(read_side, state, logical_port_name, port_mapping)

        assert(rc == 2)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_1_standby(self):
        read_side = 1
        state = "standby"
        logical_port_name = "Ethernet0"
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_b.return_value = True
            patched_util.get.return_value = mock_toggle_object
            port_mapping = PortMapping()

            rc = update_tor_active_side(read_side, state, logical_port_name, port_mapping)

        assert(rc == 2)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_tor_active_side_2_standby(self):
        read_side = 2
        state = "standby"
        logical_port_name = "Ethernet0"
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object
            port_mapping = PortMapping()

            rc = update_tor_active_side(read_side, state, logical_port_name, port_mapping)

        assert(rc == 1)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_update_tor_active_side_no_cable_presence(self):
        read_side = 1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object
            port_mapping = PortMapping()

            rc = update_tor_active_side(read_side, state, logical_port_name, port_mapping)

        assert(rc == -1)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_update_tor_active_side_multiple_mappings(self):
        read_side = 1
        state = "active"
        logical_port_name = "Ethernet0"
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            mock_toggle_object = MagicMock()
            mock_toggle_object.toggle_mux_to_tor_a.return_value = True
            patched_util.get.return_value = mock_toggle_object
            port_mapping = PortMapping()

            rc = update_tor_active_side(read_side, state, logical_port_name, port_mapping)

        assert(rc == -1)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_physical_port_from_logical_port(self):
        port_mapping = PortMapping()
        instance = get_ycable_physical_port_from_logical_port("Ethernet0", port_mapping)

        assert(instance == 0)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_get_ycable_physical_port_from_logical_port_physical_port_not_present(self):
        port_mapping = PortMapping()
        instance = get_ycable_physical_port_from_logical_port("Ethernet0", port_mapping)

        assert(instance == -1)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value={}))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_get_ycable_physical_port_from_logical_port_physical_port_list_empty(self):

        port_mapping = PortMapping()
        instance = get_ycable_physical_port_from_logical_port("Ethernet0", port_mapping)

        assert(instance == -1)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_port_instance_from_logical_port(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            patched_util.get.return_value = 0
            port_mapping = PortMapping()
            instance = get_ycable_port_instance_from_logical_port("Ethernet0", port_mapping)

        assert(instance == 0)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_get_ycable_port_instance_from_logical_port_no_presence(self):
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            patched_util.get.return_value = 0
            port_mapping = PortMapping()
            instance = get_ycable_port_instance_from_logical_port("Ethernet0", port_mapping)

        assert(instance == PORT_INSTANCE_ERROR)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_port_instance_from_logical_port_no_port_instance(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_get():
                pass

            patched_util.get.return_value = mock_get()
            port_mapping = PortMapping()
            instance = get_ycable_port_instance_from_logical_port("E", port_mapping)

        assert(instance == PORT_INSTANCE_ERROR)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_port_instance_from_logical_port_multiple_mapping(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            patched_util.get.return_value = 0
            port_mapping = PortMapping()
            instance = get_ycable_port_instance_from_logical_port("Ethernet0", port_mapping)

        assert(instance == -1)

    def test_update_table_mux_status_for_response_tbl(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        status = "standby"

        test_table = swsscommon.Table(appl_db[asic_index], "XCVRD_TEST_TABLE")
        update_table_mux_status_for_response_tbl(test_table, status, logical_port_name)

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

        rc = set_result_and_delete_port(result, actual_result, command_table, response_table, port)
        assert(rc == None)

    def test_delete_port_from_y_cable_table(self):
        logical_port_name = "Ethernet0"
        appl_db = "TEST_DB"
        y_cable_tbl = swsscommon.Table(appl_db[0], "XCVRD_Y_CBL_TABLE")

        rc = delete_port_from_y_cable_table(logical_port_name, y_cable_tbl)
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_port_instance_none(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_get():
                pass

            patched_util.get.return_value = mock_get()
            port_mapping = PortMapping()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, port_mapping, asic_index, appl_db, read_side)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_read_side_none(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_read_side():
                pass

            read_side = mock_read_side()

            patched_util.get.return_value = 0
            port_mapping = PortMapping()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, port_mapping, asic_index, appl_db, read_side)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_active_side_none(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_mux_direction():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            port_mapping = PortMapping()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, port_mapping, asic_index, appl_db, read_side)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_active_side_is_read_side(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 1

            patched_util.get.return_value = PortInstanceHelper()
            port_mapping = PortMapping()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, port_mapping, asic_index, appl_db, read_side)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_active_side_not_read_side(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 2

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 1

            patched_util.get.return_value = PortInstanceHelper()
            port_mapping = PortMapping()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, port_mapping, asic_index, appl_db, read_side)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_update_appdb_port_mux_cable_response_table_active_side_status_unknown(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 4

            patched_util.get.return_value = PortInstanceHelper()
            port_mapping = PortMapping()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, port_mapping, asic_index, appl_db, read_side)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    def test_update_appdb_port_mux_cable_response_table_no_presence_status_unknown(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 4

            patched_util.get.return_value = PortInstanceHelper()
            port_mapping = PortMapping()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, port_mapping, asic_index, appl_db, read_side)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    def test_update_appdb_port_mux_cable_response_table_invalid_ycable_mapping(self):
        asic_index = 0
        appl_db = "TEST_DB"
        logical_port_name = "Ethernet0"
        read_side = 1

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_mux_direction(self):
                    return 4

            patched_util.get.return_value = PortInstanceHelper()
            port_mapping = PortMapping()

            rc = update_appdb_port_mux_cable_response_table(
                logical_port_name, port_mapping, asic_index, appl_db, read_side)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_read_y_cable_and_update_statedb_port_tbl_invalid_ycable_mapping(self):

        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        rc = read_y_cable_and_update_statedb_port_tbl(logical_port_name, port_mapping, statedb_port_tbl[asic_index])
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_none(self):

        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_get():
                pass

            patched_util.get.return_value = mock_get()
            rc = read_y_cable_and_update_statedb_port_tbl(logical_port_name, port_mapping, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_get_presence_false(self):

        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            def mock_get():
                pass

            patched_util.get.return_value = mock_get()
            rc = read_y_cable_and_update_statedb_port_tbl(logical_port_name, port_mapping, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_get_read_side_exception(self):

        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                # Defining function without self argument creates an exception,
                # which is what we want for this test.
                def get_read_side():
                    pass

            patched_util.get.return_value = PortInstanceHelper()
            rc = read_y_cable_and_update_statedb_port_tbl(logical_port_name, port_mapping, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_get_mux_dir_exception(self):

        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
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
            rc = read_y_cable_and_update_statedb_port_tbl(logical_port_name, port_mapping, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_status_active(self):

        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_read_side(self):
                    return 1

                def get_mux_direction(self):
                    return 1

            patched_util.get.return_value = PortInstanceHelper()
            rc = read_y_cable_and_update_statedb_port_tbl(logical_port_name, port_mapping, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_status_standby(self):

        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_read_side(self):
                    return 1

                def get_mux_direction(self):
                    return 2

            patched_util.get.return_value = PortInstanceHelper()
            rc = read_y_cable_and_update_statedb_port_tbl(logical_port_name, port_mapping, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_read_y_cable_and_update_statedb_port_tbl_port_instance_status_unknown(self):

        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        statedb_port_tbl = {}
        asic_index = 0
        appl_db = "TEST_DB"

        statedb_port_tbl[asic_index] = swsscommon.Table(
            appl_db[asic_index], "STATEDB_PORT_TABLE")

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1

                def get_read_side(self):
                    return 1

                def get_mux_direction(self):
                    return 0

            patched_util.get.return_value = PortInstanceHelper()
            rc = read_y_cable_and_update_statedb_port_tbl(logical_port_name, port_mapping, statedb_port_tbl[asic_index])
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_create_tables_and_insert_mux_unknown_entries(self):

        state_db = {}
        asic_index = 0
        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()

        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}

        rc = create_tables_and_insert_mux_unknown_entries(
            state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping)
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_status_false(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = False
        fvs = [('state', "manual")]
        port_mapping = PortMapping()
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
            state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_state_absent(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('badstate', "auto")]
        port_mapping = PortMapping()
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
            state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_bad_state_value(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "badvalue")]
        port_mapping = PortMapping()
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
            state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=False))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_no_presence(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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
            state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_no_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = None

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0, 1, 2]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_multiple_port_instances(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'Microsoft', 'model': 'simulated'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_no_vendor_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'bad_manufacturer': 'Microsoft', 'model': 'simulated'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_no_model_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'Microsoft', 'bad_model': 'simulated'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_invalid_vendor_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'not_Microsoft', 'model': 'simulated'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_invalid_model_port_info(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'Microsoft', 'model': 'bad_model1'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_update_mux_table_entry_module_dir_none(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {
                'manufacturer': 'not_Microsoft', 'model': 'simulated'}

            with patch('sonic_y_cable.y_cable_vendor_mapping.mapping') as mock_mapping:
                mock_mapping.get.return_value = None

                rc = check_identifier_presence_and_update_mux_table_entry(
                    state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
                assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('sonic_y_cable.y_cable_vendor_mapping.mapping.get', MagicMock(return_value={"Microsoft": {"module": "test_module"}}))
    def test_check_identifier_presence_and_update_mux_table_entry_module_none(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'not_Microsoft', 'model': 'model1'}

            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('sonic_y_cable.y_cable_vendor_mapping.mapping.get', MagicMock(return_value={"simulated": "microsoft.y_cable_simulated"}))
    def test_check_identifier_presence_and_update_mux_table_entry_module_microsoft(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'microsoft', 'model': 'simulated'}

            sys.modules['builtins.getattr'] = MagicMock()
            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('sonic_y_cable.y_cable_vendor_mapping.mapping.get', MagicMock(return_value={"simulated": "microsoft.y_cable_simulated"}))
    def test_check_identifier_presence_and_update_mux_table_entry_module_microsoft_y_cable_presence_false(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = [False]

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'microsoft', 'model': 'simulated'}

            sys.modules['builtins.getattr'] = MagicMock()
            rc = check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, port_mapping, y_cable_presence)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_check_identifier_presence_and_delete_mux_table_entry(self):

        asic_index = 0
        logical_port_name = "Ethernet0"
        status = True
        fvs = [('state', "auto"), ('read_side', 1)]
        port_mapping = PortMapping()
        state_db = {}
        test_db = "TEST_DB"
        y_cable_tbl = {}
        static_tbl = {}
        mux_tbl = {}
        port_tbl = {}
        y_cable_presence = [True]
        delete_change_event = [True]

        port_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], "PORT_INFO_TABLE")
        port_tbl[asic_index].get.return_value = (status, fvs)

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as port_instance:
            rc = check_identifier_presence_and_delete_mux_table_entry(
                state_db, port_tbl, asic_index, logical_port_name, y_cable_presence, port_mapping, delete_change_event)
            assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_chassis')
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil')
    @patch('swsscommon.swsscommon.Table')
    def test_init_ports_status_for_y_cable(self, platform_chassis, platform_sfp, mock_swsscommon_table):

        platform_sfp = MagicMock()
        platform_chassis = MagicMock()

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        port_mapping = PortMapping()
        port_mapping.get_asic_id_for_logical_port = mock_get_asic_id
        port_mapping.logical_port_list = (['Ethernet0', 'Ethernet4'])

        y_cable_presence = [True]

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_swsscommon_table.return_value = mock_table

        rc = init_ports_status_for_y_cable(platform_sfp, platform_chassis,
                                           y_cable_presence, port_mapping, stop_event=threading.Event())

        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('swsscommon.swsscommon.Table')
    def test_change_ports_status_for_y_cable_change_event(self, mock_swsscommon_table):

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        port_mapping = PortMapping()
        port_mapping.get_asic_id_for_logical_port = mock_get_asic_id

        y_cable_presence = [True]
        logical_port_dict = {'Ethernet0': '1'}

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        change_ports_status_for_y_cable_change_event(
            logical_port_dict, port_mapping, y_cable_presence, stop_event=threading.Event())

        mock_swsscommon_table.assert_called()

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('swsscommon.swsscommon.Table')
    def test_change_ports_status_for_y_cable_change_event_sfp_removed(self, mock_swsscommon_table):

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        port_mapping = PortMapping()
        port_mapping.get_asic_id_for_logical_port = mock_get_asic_id
        port_mapping.logical_port_list = (['Ethernet0', 'Ethernet4'])

        y_cable_presence = [True]
        logical_port_dict = {'Ethernet0': '1'}

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        change_ports_status_for_y_cable_change_event(
            logical_port_dict, port_mapping, y_cable_presence, stop_event=threading.Event())

        mock_swsscommon_table.assert_called()

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('swsscommon.swsscommon.Table')
    def test_change_ports_status_for_y_cable_change_event_sfp_unknown(self, mock_swsscommon_table):

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        port_mapping = PortMapping()
        port_mapping.get_asic_id_for_logical_port = mock_get_asic_id

        y_cable_presence = [True]
        logical_port_dict = {'Ethernet0': '2'}

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        change_ports_status_for_y_cable_change_event(
            logical_port_dict, port_mapping, y_cable_presence, stop_event=threading.Event())

        mock_swsscommon_table.assert_called()

    @patch('swsscommon.swsscommon.Table')
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    def test_delete_ports_status_for_y_cable(self, mock_swsscommon_table):

        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        port_mapping = PortMapping()
        port_mapping.get_asic_id_for_logical_port = mock_get_asic_id
        port_mapping.logical_port_list = (['Ethernet0', 'Ethernet4'])

        rc = delete_ports_status_for_y_cable(port_mapping)

        mock_swsscommon_table.assert_called()

    def test_check_identifier_presence_and_update_mux_info_entry(self):
        asic_index = 0
        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        state_db = {}
        test_db = "TEST_DB"
        mux_tbl = {}

        mux_tbl[asic_index] = swsscommon.Table(
            test_db[asic_index], MUX_CABLE_INFO_TABLE)

        rc = check_identifier_presence_and_update_mux_info_entry(
            state_db, mux_tbl, asic_index, logical_port_name, port_mapping)
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances')
    def test_get_firmware_dict(self, port_instance):

        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
        port_instance.download_firmware_status = 1

        physical_port = 1
        target = "simulated_target"
        side = "a"
        mux_info_dict = {}
        logical_port_name = "Ethernet0"

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0

            status = True
            fvs = [('state', "auto"), ('read_side', 1)]
            Table = MagicMock()
            Table.get.return_value = (status, fvs)

            rc = get_firmware_dict(physical_port, port_instance, target, side, mux_info_dict, logical_port_name)

            assert(mux_info_dict['version_a_active'] == None)
            assert(mux_info_dict['version_a_inactive'] == None)
            assert(mux_info_dict['version_a_next'] == None)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances')
    def test_get_firmware_dict_download_status_failed_exception(self, port_instance):

        port_instance = MagicMock()
        port_instance.FIRMWARE_DOWNLOAD_STATUS_FAILED = -1
        port_instance.download_firmware_status = -1
        port_instance.get_firmware_version = MagicMock(side_effect=NotImplementedError)

        physical_port = 1
        target = "simulated_target"
        side = "a"
        mux_info_dict = {}
        logical_port_name = "Ethernet0"

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0

            status = True
            fvs = [('state', "auto"), ('read_side', 1)]
            Table = MagicMock()
            Table.get.return_value = (status, fvs)

            rc = get_firmware_dict(physical_port, port_instance, target, side, mux_info_dict, logical_port_name)

            assert(mux_info_dict['version_a_active'] == "N/A")
            assert(mux_info_dict['version_a_inactive'] == "N/A")
            assert(mux_info_dict['version_a_next'] == "N/A")

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances')
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

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:

            patched_util.get_asic_id_for_logical_port.return_value = 0

            status = True
            fvs = [('state', "auto"), ('read_side', 1)]
            Table = MagicMock()
            Table.get.return_value = (status, fvs)

            rc = get_firmware_dict(physical_port, port_instance, target, side, mux_info_dict, logical_port_name)

            assert(mux_info_dict['version_a_active'] == "2021")
            assert(mux_info_dict['version_a_inactive'] == "2020")
            assert(mux_info_dict['version_a_next'] == "2022")

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.get_asic_id_for_logical_port', MagicMock(return_value=0))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_info(self):
        physical_port = 20
        port_mapping = PortMapping()
        logical_port_name = "Ethernet20"

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.download_firmware_status = 1
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

            with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0

                rc = get_muxcable_info(physical_port, logical_port_name, port_mapping)

                assert(rc['tor_active'] == 'active')
                assert(rc['mux_direction'] == 'self')
                assert(rc['internal_voltage'] == 0.5)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.get_asic_id_for_logical_port', MagicMock(return_value=0))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_info_exceptions(self):
        physical_port = 20
        port_mapping = PortMapping()
        logical_port_name = "Ethernet20"

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:

            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 1
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 1
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.download_firmware_status = 1
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

            with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
                patched_util.get_asic_id_for_logical_port.return_value = 0

                rc = get_muxcable_info(physical_port, logical_port_name, port_mapping)

                assert(rc['tor_active'] == 'unknown')
                assert(rc['mux_direction'] == 'unknown')
                assert(rc['self_eye_height_lane1'] == 'N/A')

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.get_asic_id_for_logical_port', MagicMock(return_value=0))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_locks', MagicMock(return_value=[0]))
    def test_get_muxcable_static_info(self):
        physical_port = 0
        port_mapping = PortMapping()
        logical_port_name = "Ethernet0"

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            class PortInstanceHelper():
                def __init__(self):
                    self.EEPROM_ERROR = -1
                    self.TARGET_NIC = 0
                    self.TARGET_TOR_A = 1
                    self.TARGET_TOR_B = 2
                    self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS = 1
                    self.download_firmware_status = 1
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

            rc = get_muxcable_static_info(physical_port, logical_port_name, port_mapping)

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

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.get_asic_id_for_logical_port', MagicMock(return_value=0))
    def test_post_mux_static_info_to_db(self):
        is_warm_start = True

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        port_mapping = PortMapping()
        port_mapping.get_asic_id_for_logical_port = mock_get_asic_id
        port_mapping.logical_port_list = (['Ethernet0', 'Ethernet4'])

        stop_event = threading.Event()
        stop_event.is_set = MagicMock(return_value=False)

        rc = post_mux_static_info_to_db(is_warm_start, port_mapping, stop_event)
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.get_asic_id_for_logical_port', MagicMock(return_value=0))
    def test_post_mux_info_to_db(self):
        is_warm_start = True

        mock_logical_port_name = [""]

        def mock_get_asic_id(mock_logical_port_name):
            return 0

        port_mapping = PortMapping()
        port_mapping.get_asic_id_for_logical_port = mock_get_asic_id
        port_mapping.logical_port_list = (['Ethernet0', 'Ethernet4'])

        stop_event = threading.Event()
        stop_event.is_set = MagicMock(return_value=False)

        rc = post_mux_info_to_db(is_warm_start, port_mapping, stop_event)
        assert(rc == None)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances')
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
        rc = set_show_firmware_fields("Ethernet0", mux_info_dict, xcvrd_show_fw_res_tbl)

        assert(rc == 0)
