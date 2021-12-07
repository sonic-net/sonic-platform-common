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
swsscommon.ProducerStateTable = MagicMock()
swsscommon.SubscriberStateTable = MagicMock()
swsscommon.SonicDBConfig = MagicMock()
#swsscommon.Select = MagicMock()

sys.modules['sonic_y_cable'] = MagicMock()
sys.modules['sonic_y_cable.y_cable'] = MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "xcvrd")
sys.path.insert(0, modules_path)

os.environ["XCVRD_UNIT_TESTING"] = "1"
from xcvrd.xcvrd import *
from xcvrd.xcvrd_utilities.y_cable_helper import *
from xcvrd.xcvrd_utilities.sfp_status_helper import *
from xcvrd.xcvrd_utilities.port_mapping import *

with open(os.path.join(test_path, 'media_settings.json'), 'r') as f:
    media_settings_dict = json.load(f)

media_settings_with_comma_dict = copy.deepcopy(media_settings_dict)
global_media_settings = media_settings_with_comma_dict['GLOBAL_MEDIA_SETTINGS'].pop('1-32')
media_settings_with_comma_dict['GLOBAL_MEDIA_SETTINGS']['1-5,6,7-20,21-32'] = global_media_settings

class TestXcvrdScript(object):
    def test_xcvrd_helper_class_run(self):
        Y_cable_task = YCableTableUpdateTask(None)

    @patch('xcvrd.xcvrd._wrapper_get_sfp_type')
    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_get_transceiver_dom_info', MagicMock(return_value={'temperature': '22.75',
                                                                                    'voltage': '0.5',
                                                                                    'rx1power': '0.7',
                                                                                    'rx2power': '0.7',
                                                                                    'rx3power': '0.7',
                                                                                    'rx4power': '0.7',
                                                                                    'rx5power': '0.7',
                                                                                    'rx6power': '0.7',
                                                                                    'rx7power': '0.7',
                                                                                    'rx8power': '0.7',
                                                                                    'tx1bias': '0.7',
                                                                                    'tx2bias': '0.7',
                                                                                    'tx3bias': '0.7',
                                                                                    'tx4bias': '0.7',
                                                                                    'tx5bias': '0.7',
                                                                                    'tx6bias': '0.7',
                                                                                    'tx7bias': '0.7',
                                                                                    'tx8bias': '0.7',
                                                                                    'tx1power': '0.7',
                                                                                    'tx2power': '0.7',
                                                                                    'tx3power': '0.7',
                                                                                    'tx4power': '0.7',
                                                                                    'tx5power': '0.7',
                                                                                    'tx6power': '0.7',
                                                                                    'tx7power': '0.7',
                                                                                    'tx8power': '0.7', }))
    def test_post_port_dom_info_to_db(self, mock_get_sfp_type):
        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        stop_event = threading.Event()
        dom_tbl = Table("STATE_DB", TRANSCEIVER_DOM_SENSOR_TABLE)
        post_port_dom_info_to_db(logical_port_name, port_mapping, dom_tbl, stop_event)
        mock_get_sfp_type.return_value = 'QSFP_DD'
        post_port_dom_info_to_db(logical_port_name, port_mapping, dom_tbl, stop_event)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    def test_del_port_sfp_dom_info_from_db(self):
        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        dom_tbl = Table("STATE_DB", TRANSCEIVER_DOM_SENSOR_TABLE)
        init_tbl = Table("STATE_DB", TRANSCEIVER_INFO_TABLE)
        del_port_sfp_dom_info_from_db(logical_port_name, port_mapping, init_tbl, dom_tbl)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_get_transceiver_dom_threshold_info', MagicMock(return_value={'temphighalarm': '22.75',
                                                                                              'temphighwarning': '0.5',
                                                                                              'templowalarm': '0.7',
                                                                                              'templowwarning': '0.7',
                                                                                              'vcchighalarm': '0.7',
                                                                                              'vcchighwarning': '0.7',
                                                                                              'vcclowalarm': '0.7',
                                                                                              'vcclowwarning': '0.7',
                                                                                              'txpowerhighalarm': '0.7',
                                                                                              'txpowerlowalarm': '0.7',
                                                                                              'txpowerhighwarning': '0.7',
                                                                                              'txpowerlowwarning': '0.7',
                                                                                              'rxpowerhighalarm': '0.7',
                                                                                              'rxpowerlowalarm': '0.7',
                                                                                              'rxpowerhighwarning': '0.7',
                                                                                              'rxpowerlowwarning': '0.7',
                                                                                              'txbiashighalarm': '0.7',
                                                                                              'txbiaslowalarm': '0.7',
                                                                                              'txbiashighwarning': '0.7',
                                                                                              'txbiaslowwarning': '0.7', }))
    def test_post_port_dom_threshold_info_to_db(self):
        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        stop_event = threading.Event()
        dom_tbl = Table("STATE_DB", TRANSCEIVER_DOM_SENSOR_TABLE)
        post_port_dom_threshold_info_to_db(logical_port_name, port_mapping, dom_tbl, stop_event)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_is_replaceable', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_get_transceiver_info', MagicMock(return_value={'type': '22.75',
                                                                                'vendor_rev': '0.5',
                                                                                'serial': '0.7',
                                                                                'manufacturer': '0.7',
                                                                                'model': '0.7',
                                                                                'vendor_oui': '0.7',
                                                                                'vendor_date': '0.7',
                                                                                'connector': '0.7',
                                                                                'encoding': '0.7',
                                                                                'ext_identifier': '0.7',
                                                                                'ext_rateselect_compliance': '0.7',
                                                                                'cable_type': '0.7',
                                                                                'cable_length': '0.7',
                                                                                'specification_compliance': '0.7',
                                                                                'nominal_bit_rate': '0.7',
                                                                                'application_advertisement': '0.7',
                                                                                'is_replaceable': '0.7',
                                                                                'dom_capability': '0.7', }))
    def test_post_port_sfp_info_to_db(self):
        logical_port_name = "Ethernet0"
        port_mapping = PortMapping()
        stop_event = threading.Event()
        dom_tbl = Table("STATE_DB", TRANSCEIVER_DOM_SENSOR_TABLE)
        transceiver_dict = {}
        post_port_sfp_info_to_db(logical_port_name, port_mapping, dom_tbl, transceiver_dict, stop_event)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd.platform_sfputil', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_is_replaceable', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd.xcvr_table_helper', MagicMock())
    @patch('xcvrd.xcvrd._wrapper_get_transceiver_info', MagicMock(return_value={'type': '22.75',
                                                                                'vendor_rev': '0.5',
                                                                                'serial': '0.7',
                                                                                'manufacturer': '0.7',
                                                                                'model': '0.7',
                                                                                'vendor_oui': '0.7',
                                                                                'vendor_date': '0.7',
                                                                                'connector': '0.7',
                                                                                'encoding': '0.7',
                                                                                'ext_identifier': '0.7',
                                                                                'ext_rateselect_compliance': '0.7',
                                                                                'cable_type': '0.7',
                                                                                'cable_length': '0.7',
                                                                                'specification_compliance': '0.7',
                                                                                'nominal_bit_rate': '0.7',
                                                                                'application_advertisement': '0.7',
                                                                                'is_replaceable': '0.7',
                                                                                'dom_capability': '0.7', }))
    @patch('xcvrd.xcvrd._wrapper_get_transceiver_dom_threshold_info', MagicMock(return_value={'temphighalarm': '22.75',
                                                                                              'temphighwarning': '0.5',
                                                                                              'templowalarm': '0.7',
                                                                                              'templowwarning': '0.7',
                                                                                              'vcchighalarm': '0.7',
                                                                                              'vcchighwarning': '0.7',
                                                                                              'vcclowalarm': '0.7',
                                                                                              'vcclowwarning': '0.7',
                                                                                              'txpowerhighalarm': '0.7',
                                                                                              'txpowerlowalarm': '0.7',
                                                                                              'txpowerhighwarning': '0.7',
                                                                                              'txpowerlowwarning': '0.7',
                                                                                              'rxpowerhighalarm': '0.7',
                                                                                              'rxpowerlowalarm': '0.7',
                                                                                              'rxpowerhighwarning': '0.7',
                                                                                              'rxpowerlowwarning': '0.7',
                                                                                              'txbiashighalarm': '0.7',
                                                                                              'txbiaslowalarm': '0.7',
                                                                                              'txbiashighwarning': '0.7',
                                                                                              'txbiaslowwarning': '0.7', }))
    @patch('xcvrd.xcvrd._wrapper_get_transceiver_dom_info', MagicMock(return_value={'temperature': '22.75',
                                                                                    'voltage': '0.5',
                                                                                    'rx1power': '0.7',
                                                                                    'rx2power': '0.7',
                                                                                    'rx3power': '0.7',
                                                                                    'rx4power': '0.7',
                                                                                    'rx5power': '0.7',
                                                                                    'rx6power': '0.7',
                                                                                    'rx7power': '0.7',
                                                                                    'rx8power': '0.7',
                                                                                    'tx1bias': '0.7',
                                                                                    'tx2bias': '0.7',
                                                                                    'tx3bias': '0.7',
                                                                                    'tx4bias': '0.7',
                                                                                    'tx5bias': '0.7',
                                                                                    'tx6bias': '0.7',
                                                                                    'tx7bias': '0.7',
                                                                                    'tx8bias': '0.7',
                                                                                    'tx1power': '0.7',
                                                                                    'tx2power': '0.7',
                                                                                    'tx3power': '0.7',
                                                                                    'tx4power': '0.7',
                                                                                    'tx5power': '0.7',
                                                                                    'tx6power': '0.7',
                                                                                    'tx7power': '0.7',
                                                                                    'tx8power': '0.7', }))
    def test_post_port_sfp_dom_info_to_db(self):
        port_mapping = PortMapping()
        port_change_event = PortChangeEvent('Ethernet0', 1, 0, PortChangeEvent.PORT_ADD)
        port_mapping.handle_port_change_event(port_change_event)
        stop_event = threading.Event()
        post_port_sfp_dom_info_to_db(True, port_mapping, stop_event)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd.platform_sfputil', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_is_replaceable', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd.xcvr_table_helper', MagicMock())
    def test_init_port_sfp_status_tbl(self):
        port_mapping = PortMapping()
        port_change_event = PortChangeEvent('Ethernet0', 1, 0, PortChangeEvent.PORT_ADD)
        port_mapping.handle_port_change_event(port_change_event)
        stop_event = threading.Event()
        init_port_sfp_status_tbl(port_mapping, stop_event)

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

    def test_y_cable_wrapper_get_transceiver_info(self):
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_transceiver_info_dict.return_value = {'manufacturer': 'Microsoft',
                                                                              'model': 'model1'}

            transceiver_dict = y_cable_wrapper_get_transceiver_info(1)
            vendor = transceiver_dict.get('manufacturer')
            model = transceiver_dict.get('model')

        assert(vendor == "Microsoft")
        assert(model == "model1")

    def test_y_cable_wrapper_get_presence(self):
        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil') as patched_util:
            patched_util.get_presence.return_value = True

            presence = y_cable_wrapper_get_presence(1)

        assert(presence == True)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_physical_port_from_logical_port(self):
        port_mapping = PortMapping()
        instance = get_ycable_physical_port_from_logical_port("Ethernet0", port_mapping)

        assert(instance == 0)

    @patch('xcvrd.xcvrd_utilities.port_mapping.PortMapping.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_wrapper_get_presence', MagicMock(return_value=True))
    def test_get_ycable_port_instance_from_logical_port(self):

        with patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_port_instances') as patched_util:
            patched_util.get.return_value = 0
            port_mapping = PortMapping()
            instance = get_ycable_port_instance_from_logical_port("Ethernet0", port_mapping)

        assert(instance == 0)

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

    def test_get_media_settings_key(self):
        xcvr_info_dict = {
            0: {
                'manufacturer': 'Molex',
                'model': '1064141421',
                'cable_type': 'Length Cable Assembly(m)',
                'cable_length': '255',
                'specification_compliance': "{'10/40G Ethernet Compliance Code': '10GBase-SR'}",
                'type_abbrv_name': 'QSFP+'
            }
        }

        # Test a good 'specification_compliance' value
        result = get_media_settings_key(0, xcvr_info_dict)
        assert result == ['MOLEX-1064141421', 'QSFP+-10GBase-SR-255M']

        # Test a bad 'specification_compliance' value
        xcvr_info_dict[0]['specification_compliance'] = 'N/A'
        result = get_media_settings_key(0, xcvr_info_dict)
        assert result == ['MOLEX-1064141421', 'QSFP+-*']
        # TODO: Ensure that error message was logged

    @patch('xcvrd.xcvrd.g_dict', media_settings_dict)
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    def test_notify_media_setting(self):
        self._check_notify_media_setting(1)

    @patch('xcvrd.xcvrd.g_dict', media_settings_with_comma_dict)
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    def test_notify_media_setting_with_comma(self):
        self._check_notify_media_setting(1)
        self._check_notify_media_setting(6)

    def _check_notify_media_setting(self, index):
        logical_port_name = 'Ethernet0'
        xcvr_info_dict = {
            index: {
                'manufacturer': 'Molex',
                'model': '1064141421',
                'cable_type': 'Length Cable Assembly(m)',
                'cable_length': '255',
                'specification_compliance': "{'10/40G Ethernet Compliance Code': '10GBase-SR'}",
                'type_abbrv_name': 'QSFP+'
            }
        }
        app_port_tbl = Table("APPL_DB", 'PORT_TABLE')
        port_mapping = PortMapping()
        port_change_event = PortChangeEvent('Ethernet0', index, 0, PortChangeEvent.PORT_ADD)
        port_mapping.handle_port_change_event(port_change_event)
        notify_media_setting(logical_port_name, xcvr_info_dict, app_port_tbl, port_mapping)


    def test_detect_port_in_error_status(self):
        class MockTable:
            def get(self, key):
                pass

        status_tbl = MockTable()
        status_tbl.get = MagicMock(return_value=(True, {'error': 'N/A'}))
        assert not detect_port_in_error_status(None, status_tbl)

        status_tbl.get = MagicMock(return_value=(True, {'error': SfpBase.SFP_ERROR_DESCRIPTION_BLOCKING}))
        assert detect_port_in_error_status(None, status_tbl)

    def test_is_error_sfp_status(self):
        error_values = [7, 11, 19, 35]
        for error_value in error_values:
            assert is_error_block_eeprom_reading(error_value)

        assert not is_error_block_eeprom_reading(int(SFP_STATUS_INSERTED))
        assert not is_error_block_eeprom_reading(int(SFP_STATUS_REMOVED))

    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    def test_handle_port_config_change(self, mock_select, mock_sub_table):
        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(side_effect=[('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), (None, None, None)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable

        sel, asic_context = subscribe_port_config_change()
        port_mapping = PortMapping()
        stop_event = threading.Event()
        stop_event.is_set = MagicMock(return_value=False)
        logger = MagicMock()
        handle_port_config_change(sel, asic_context, stop_event, port_mapping, logger, port_mapping.handle_port_change_event)

        assert port_mapping.logical_port_list.count('Ethernet0')
        assert port_mapping.get_asic_id_for_logical_port('Ethernet0') == 0
        assert port_mapping.get_physical_to_logical(1) == ['Ethernet0']
        assert port_mapping.get_logical_to_physical('Ethernet0') == [1]

        mock_selectable.pop = MagicMock(side_effect=[('Ethernet0', swsscommon.DEL_COMMAND, (('index', '1'), )), (None, None, None)])
        handle_port_config_change(sel, asic_context, stop_event, port_mapping, logger, port_mapping.handle_port_change_event)
        assert not port_mapping.logical_port_list
        assert not port_mapping.logical_to_physical
        assert not port_mapping.physical_to_logical
        assert not port_mapping.logical_to_asic

    @patch('swsscommon.swsscommon.Table')
    def test_get_port_mapping(self, mock_swsscommon_table):
        mock_table = MagicMock()
        mock_table.getKeys = MagicMock(return_value=['Ethernet0', 'Ethernet4'])
        mock_table.get = MagicMock(side_effect=[(True, (('index', 1), )), (True, (('index', 2), ))])
        mock_swsscommon_table.return_value = mock_table
        port_mapping = get_port_mapping()
        assert port_mapping.logical_port_list.count('Ethernet0')
        assert port_mapping.get_asic_id_for_logical_port('Ethernet0') == 0
        assert port_mapping.get_physical_to_logical(1) == ['Ethernet0']
        assert port_mapping.get_logical_to_physical('Ethernet0') == [1]

        assert port_mapping.logical_port_list.count('Ethernet4')
        assert port_mapping.get_asic_id_for_logical_port('Ethernet4') == 0
        assert port_mapping.get_physical_to_logical(2) == ['Ethernet4']
        assert port_mapping.get_logical_to_physical('Ethernet4') == [2]


    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    def test_DaemonXcvrd_wait_for_port_config_done(self, mock_select, mock_sub_table):
        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(side_effect=[('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), ('PortConfigDone', None, None)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable
        xcvrd = DaemonXcvrd(SYSLOG_IDENTIFIER)
        xcvrd.wait_for_port_config_done('')
        assert swsscommon.Select.select.call_count == 2

    @patch('xcvrd.xcvrd.DaemonXcvrd.init')
    @patch('xcvrd.xcvrd.DaemonXcvrd.deinit')
    @patch('xcvrd.xcvrd.DomInfoUpdateTask.task_run')
    @patch('xcvrd.xcvrd.SfpStateUpdateTask.task_run')
    @patch('xcvrd.xcvrd.DomInfoUpdateTask.task_stop')
    @patch('xcvrd.xcvrd.SfpStateUpdateTask.task_stop')
    def test_DaemonXcvrd_run(self, mock_task_stop1, mock_task_stop2, mock_task_run1, mock_task_run2, mock_deinit, mock_init):
        mock_init.return_value = (PortMapping(), set())
        xcvrd = DaemonXcvrd(SYSLOG_IDENTIFIER)
        xcvrd.stop_event.wait = MagicMock()
        xcvrd.run()
        # TODO: more check
        assert mock_task_stop1.call_count == 1
        assert mock_task_stop2.call_count == 1
        assert mock_task_run1.call_count == 1
        assert mock_task_run2.call_count == 1
        assert mock_deinit.call_count == 1
        assert mock_init.call_count == 1

    @patch('xcvrd.xcvrd.xcvr_table_helper', MagicMock())
    def test_DomInfoUpdateTask_handle_port_change_event(self):
        port_mapping = PortMapping()
        task = DomInfoUpdateTask(port_mapping)
        port_change_event = PortChangeEvent('Ethernet0', 1, 0, PortChangeEvent.PORT_ADD)
        task.on_port_config_change(port_change_event)
        assert task.port_mapping.logical_port_list.count('Ethernet0')
        assert task.port_mapping.get_asic_id_for_logical_port('Ethernet0') == 0
        assert task.port_mapping.get_physical_to_logical(1) == ['Ethernet0']
        assert task.port_mapping.get_logical_to_physical('Ethernet0') == [1]

        port_change_event = PortChangeEvent('Ethernet0', 1, 0, PortChangeEvent.PORT_REMOVE)
        task.on_port_config_change(port_change_event)
        assert not task.port_mapping.logical_port_list
        assert not task.port_mapping.logical_to_physical
        assert not task.port_mapping.physical_to_logical
        assert not task.port_mapping.logical_to_asic

    @patch('xcvrd.xcvrd_utilities.port_mapping.subscribe_port_config_change', MagicMock(return_value=(None, None)))
    @patch('xcvrd.xcvrd_utilities.port_mapping.handle_port_config_change', MagicMock())
    def test_DomInfoUpdateTask_task_run_stop(self):
        port_mapping = PortMapping()
        task = DomInfoUpdateTask(port_mapping)
        task.task_run([False])
        task.task_stop()
        assert not task.task_thread.is_alive()

    @patch('xcvrd.xcvrd.xcvr_table_helper', MagicMock())
    @patch('xcvrd.xcvrd_utilities.sfp_status_helper.detect_port_in_error_status')
    @patch('xcvrd.xcvrd.post_port_dom_info_to_db')
    @patch('xcvrd.xcvrd.post_port_dom_threshold_info_to_db')
    @patch('swsscommon.swsscommon.Select.addSelectable', MagicMock())
    @patch('swsscommon.swsscommon.SubscriberStateTable')
    @patch('swsscommon.swsscommon.Select.select')
    def test_DomInfoUpdateTask_task_worker(self, mock_select, mock_sub_table, mock_post_dom_th, mock_post_dom_info, mock_detect_error):
        mock_selectable = MagicMock()
        mock_selectable.pop = MagicMock(side_effect=[('Ethernet0', swsscommon.SET_COMMAND, (('index', '1'), )), (None, None, None), (None, None, None)])
        mock_select.return_value = (swsscommon.Select.OBJECT, mock_selectable)
        mock_sub_table.return_value = mock_selectable
        
        port_mapping = PortMapping()
        task = DomInfoUpdateTask(port_mapping)
        task.task_stopping_event.wait = MagicMock(side_effect=[False, True])
        mock_detect_error.return_value = True
        task.task_worker([False])
        assert task.port_mapping.logical_port_list.count('Ethernet0')
        assert task.port_mapping.get_asic_id_for_logical_port('Ethernet0') == 0
        assert task.port_mapping.get_physical_to_logical(1) == ['Ethernet0']
        assert task.port_mapping.get_logical_to_physical('Ethernet0') == [1]
        assert mock_post_dom_th.call_count == 0
        assert mock_post_dom_info.call_count == 0
        mock_detect_error.return_value = False
        task.task_stopping_event.wait = MagicMock(side_effect=[False, True])
        task.task_worker([False])
        assert mock_post_dom_th.call_count == 1
        assert mock_post_dom_info.call_count == 1


    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=False))
    @patch('xcvrd.xcvrd.xcvr_table_helper')
    def test_SfpStateUpdateTask_handle_port_change_event(self, mock_table_helper):
        mock_table = MagicMock()
        mock_table.get = MagicMock(return_value=(False, None))
        mock_table_helper.get_status_tbl = MagicMock(return_value=mock_table)
        mock_table_helper.get_int_tbl = MagicMock(return_value=mock_table)
        mock_table_helper.get_dom_tbl = MagicMock(return_value=mock_table)
        stopping_event = multiprocessing.Event()
        port_mapping = PortMapping()
        retry_eeprom_set = set()
        task = SfpStateUpdateTask(port_mapping, retry_eeprom_set)
        port_change_event = PortChangeEvent('Ethernet0', 1, 0, PortChangeEvent.PORT_ADD)
        wait_time = 5
        while wait_time > 0:
            task.on_port_config_change(stopping_event, [False], port_change_event)
            if task.port_mapping.logical_port_list:
                break
            wait_time -= 1
            time.sleep(1)
        assert task.port_mapping.logical_port_list.count('Ethernet0')
        assert task.port_mapping.get_asic_id_for_logical_port('Ethernet0') == 0
        assert task.port_mapping.get_physical_to_logical(1) == ['Ethernet0']
        assert task.port_mapping.get_logical_to_physical('Ethernet0') == [1]

        port_change_event = PortChangeEvent('Ethernet0', 1, 0, PortChangeEvent.PORT_REMOVE)
        wait_time = 5
        while wait_time > 0:
            task.on_port_config_change(stopping_event, [False], port_change_event)
            if not task.port_mapping.logical_port_list:
                break
            wait_time -= 1
            time.sleep(1)
        assert not task.port_mapping.logical_port_list
        assert not task.port_mapping.logical_to_physical
        assert not task.port_mapping.physical_to_logical
        assert not task.port_mapping.logical_to_asic

    def test_SfpStateUpdateTask_task_run_stop(self):
        port_mapping = PortMapping()
        retry_eeprom_set = set()
        task = SfpStateUpdateTask(port_mapping, retry_eeprom_set)
        sfp_error_event = multiprocessing.Event()
        task.task_run(sfp_error_event, [False])
        assert wait_until(5, 1, task.task_process.is_alive)
        task.task_stop()
        assert wait_until(5, 1, lambda: task.task_process.is_alive() is False)

    @patch('xcvrd.xcvrd.xcvr_table_helper', MagicMock())
    @patch('xcvrd.xcvrd.post_port_sfp_info_to_db')
    def test_SfpStateUpdateTask_retry_eeprom_reading(self, mock_post_sfp_info):
        port_mapping = PortMapping()
        retry_eeprom_set = set()
        task = SfpStateUpdateTask(port_mapping, retry_eeprom_set)
        task.retry_eeprom_reading()
        assert mock_post_sfp_info.call_count == 0

        task.retry_eeprom_set.add('Ethernet0')
        task.last_retry_eeprom_time = time.time()
        task.retry_eeprom_reading()
        assert mock_post_sfp_info.call_count == 0

        task.last_retry_eeprom_time = 0
        mock_post_sfp_info.return_value = SFP_EEPROM_NOT_READY
        task.retry_eeprom_reading()
        assert 'Ethernet0' in task.retry_eeprom_set

        task.last_retry_eeprom_time = 0
        mock_post_sfp_info.return_value = None
        task.retry_eeprom_reading()
        assert 'Ethernet0' not in task.retry_eeprom_set

    def test_SfpStateUpdateTask_mapping_event_from_change_event(self):
        port_mapping = PortMapping()
        retry_eeprom_set = set()
        task = SfpStateUpdateTask(port_mapping, retry_eeprom_set)
        port_dict = {}
        assert task._mapping_event_from_change_event(False, port_dict) == SYSTEM_FAIL
        assert port_dict[EVENT_ON_ALL_SFP] == SYSTEM_FAIL

        port_dict = {EVENT_ON_ALL_SFP: SYSTEM_FAIL}
        assert task._mapping_event_from_change_event(False, port_dict) == SYSTEM_FAIL

        port_dict = {}
        assert task._mapping_event_from_change_event(True, port_dict) == SYSTEM_BECOME_READY
        assert port_dict[EVENT_ON_ALL_SFP] == SYSTEM_BECOME_READY

        port_dict = {1, SFP_STATUS_INSERTED}
        assert task._mapping_event_from_change_event(True, port_dict) == NORMAL_EVENT

    @patch('time.sleep', MagicMock())
    @patch('xcvrd.xcvrd.xcvr_table_helper', MagicMock())
    @patch('xcvrd.xcvrd._wrapper_soak_sfp_insert_event', MagicMock())
    @patch('xcvrd.xcvrd_utilities.port_mapping.subscribe_port_config_change', MagicMock(return_value=(None, None)))
    @patch('xcvrd.xcvrd_utilities.port_mapping.handle_port_config_change', MagicMock())
    @patch('os.kill')
    @patch('xcvrd.xcvrd.SfpStateUpdateTask._mapping_event_from_change_event')
    @patch('xcvrd.xcvrd._wrapper_get_transceiver_change_event')
    @patch('xcvrd.xcvrd.del_port_sfp_dom_info_from_db')
    @patch('xcvrd.xcvrd.notify_media_setting')
    @patch('xcvrd.xcvrd.post_port_dom_threshold_info_to_db')
    @patch('xcvrd.xcvrd.post_port_dom_info_to_db')
    @patch('xcvrd.xcvrd.post_port_sfp_info_to_db')
    @patch('xcvrd.xcvrd.update_port_transceiver_status_table')
    def test_SfpStateUpdateTask_task_worker(self, mock_updata_status, mock_post_sfp_info, mock_post_dom_info, mock_post_dom_th, mock_update_media_setting, mock_del_dom, mock_change_event, mock_mapping_event, mock_os_kill):
        port_mapping = PortMapping()
        retry_eeprom_set = set()
        task = SfpStateUpdateTask(port_mapping, retry_eeprom_set)
        stop_event = multiprocessing.Event()
        sfp_error_event = multiprocessing.Event()
        mock_change_event.return_value = (True, {0:0}, {})
        mock_mapping_event.return_value = SYSTEM_NOT_READY

        # Test state machine: STATE_INIT + SYSTEM_NOT_READY event => STATE_INIT + SYSTEM_NOT_READY event ... => STATE_EXIT
        task.task_worker(stop_event, sfp_error_event, [False])
        assert mock_os_kill.call_count == 1
        assert sfp_error_event.is_set()

        mock_mapping_event.return_value = SYSTEM_FAIL
        mock_os_kill.reset_mock()
        sfp_error_event.clear()
        # Test state machine: STATE_INIT + SYSTEM_FAIL event => STATE_INIT + SYSTEM_FAIL event ... => STATE_EXIT
        task.task_worker(stop_event, sfp_error_event, [False])
        assert mock_os_kill.call_count == 1
        assert sfp_error_event.is_set()

        mock_mapping_event.side_effect = [SYSTEM_BECOME_READY, SYSTEM_NOT_READY]
        mock_os_kill.reset_mock()
        sfp_error_event.clear()
        # Test state machine: STATE_INIT + SYSTEM_BECOME_READY event => STATE_NORMAL + SYSTEM_NOT_READY event ... => STATE_EXIT
        task.task_worker(stop_event, sfp_error_event, [False])
        assert mock_os_kill.call_count == 1
        assert not sfp_error_event.is_set()

        mock_mapping_event.side_effect = [SYSTEM_BECOME_READY, SYSTEM_FAIL] + [SYSTEM_FAIL] * (RETRY_TIMES_FOR_SYSTEM_READY + 1)
        mock_os_kill.reset_mock()
        sfp_error_event.clear()
        # Test state machine: STATE_INIT + SYSTEM_BECOME_READY event => STATE_NORMAL + SYSTEM_FAIL event ... => STATE_INIT
        # + SYSTEM_FAIL event ... => STATE_EXIT
        task.task_worker(stop_event, sfp_error_event, [False])
        assert mock_os_kill.call_count == 1
        assert sfp_error_event.is_set()

        task.port_mapping.handle_port_change_event(PortChangeEvent('Ethernet0', 1, 0, PortChangeEvent.PORT_ADD))
        mock_change_event.return_value = (True, {1:SFP_STATUS_INSERTED}, {})
        mock_mapping_event.side_effect = None
        mock_mapping_event.return_value = NORMAL_EVENT
        mock_post_sfp_info.return_value = SFP_EEPROM_NOT_READY
        stop_event.is_set = MagicMock(side_effect=[False, True])
        # Test state machine: handle SFP insert event, but EEPROM read failure
        task.task_worker(stop_event, sfp_error_event, [False])
        assert mock_updata_status.call_count == 1
        assert mock_post_sfp_info.call_count == 2 # first call and retry call
        assert mock_post_dom_info.call_count == 0
        assert mock_post_dom_th.call_count == 0
        assert mock_update_media_setting.call_count == 0
        assert 'Ethernet0' in task.retry_eeprom_set
        task.retry_eeprom_set.clear()

        stop_event.is_set = MagicMock(side_effect=[False, True])
        mock_post_sfp_info.return_value = None
        mock_updata_status.reset_mock()
        mock_post_sfp_info.reset_mock()
        # Test state machine: handle SFP insert event, and EEPROM read success
        task.task_worker(stop_event, sfp_error_event, [False])
        assert mock_updata_status.call_count == 1
        assert mock_post_sfp_info.call_count == 1
        assert mock_post_dom_info.call_count == 1
        assert mock_post_dom_th.call_count == 1
        assert mock_update_media_setting.call_count == 1

        stop_event.is_set = MagicMock(side_effect=[False, True])
        mock_change_event.return_value = (True, {1:SFP_STATUS_REMOVED}, {})
        mock_updata_status.reset_mock()
        # Test state machine: handle SFP remove event
        task.task_worker(stop_event, sfp_error_event, [False])
        assert mock_updata_status.call_count == 1
        assert mock_del_dom.call_count == 1

        stop_event.is_set = MagicMock(side_effect=[False, True])
        error = int(SFP_STATUS_INSERTED) | SfpBase.SFP_ERROR_BIT_BLOCKING | SfpBase.SFP_ERROR_BIT_POWER_BUDGET_EXCEEDED
        mock_change_event.return_value = (True, {1:error}, {})
        mock_updata_status.reset_mock()
        mock_del_dom.reset_mock()
        # Test state machine: handle SFP error event
        task.task_worker(stop_event, sfp_error_event, [False])
        assert mock_updata_status.call_count == 1
        assert mock_del_dom.call_count == 1

    @patch('xcvrd.xcvrd.xcvr_table_helper')
    @patch('xcvrd.xcvrd._wrapper_get_presence')
    @patch('xcvrd.xcvrd.notify_media_setting')
    @patch('xcvrd.xcvrd.post_port_dom_threshold_info_to_db')
    @patch('xcvrd.xcvrd.post_port_dom_info_to_db')
    @patch('xcvrd.xcvrd.post_port_sfp_info_to_db')
    @patch('xcvrd.xcvrd.update_port_transceiver_status_table')
    def test_SfpStateUpdateTask_on_add_logical_port(self, mock_updata_status, mock_post_sfp_info, mock_post_dom_info, mock_post_dom_th, mock_update_media_setting, mock_get_presence, mock_table_helper):
        class MockTable:
            pass

        status_tbl = MockTable()
        status_tbl.get = MagicMock(return_value=(True, (('status', SFP_STATUS_INSERTED),)))
        status_tbl.set = MagicMock()
        int_tbl = MockTable()
        int_tbl.get = MagicMock(return_value=(True, (('key2', 'value2'),)))
        int_tbl.set = MagicMock()
        dom_tbl = MockTable()
        dom_tbl.get = MagicMock(return_value=(True, (('key3', 'value3'),)))
        dom_tbl.set = MagicMock()
        mock_table_helper.get_status_tbl = MagicMock(return_value=status_tbl)
        mock_table_helper.get_intf_tbl = MagicMock(return_value=int_tbl)
        mock_table_helper.get_dom_tbl = MagicMock(return_value=dom_tbl)

        port_mapping = PortMapping()
        retry_eeprom_set = set()
        task = SfpStateUpdateTask(port_mapping, retry_eeprom_set)
        port_change_event = PortChangeEvent('Ethernet0', 1, 0, PortChangeEvent.PORT_ADD)
        task.port_mapping.handle_port_change_event(port_change_event)
        # SFP information is in the DB, copy the SFP information for the newly added logical port
        task.on_add_logical_port(port_change_event)
        status_tbl.get.assert_called_with('Ethernet0')
        status_tbl.set.assert_called_with('Ethernet0', (('status', SFP_STATUS_INSERTED),))
        int_tbl.get.assert_called_with('Ethernet0')
        int_tbl.set.assert_called_with('Ethernet0', (('key2', 'value2'),))
        dom_tbl.get.assert_called_with('Ethernet0')
        dom_tbl.set.assert_called_with('Ethernet0', (('key3', 'value3'),))

        status_tbl.get.return_value = (False, ())
        mock_get_presence.return_value = True
        mock_post_sfp_info.return_value = SFP_EEPROM_NOT_READY
        # SFP information is not in the DB, and SFP is present, and SFP has no error, but SFP EEPROM reading failed
        task.on_add_logical_port(port_change_event)
        assert mock_updata_status.call_count == 1
        mock_updata_status.assert_called_with('Ethernet0', status_tbl, SFP_STATUS_INSERTED, 'N/A')
        assert mock_post_sfp_info.call_count == 1
        mock_post_sfp_info.assert_called_with('Ethernet0', task.port_mapping, int_tbl, {})
        assert mock_post_dom_info.call_count == 0
        assert mock_post_dom_th.call_count == 0
        assert mock_update_media_setting.call_count == 0
        assert 'Ethernet0' in task.retry_eeprom_set
        task.retry_eeprom_set.clear()

        mock_post_sfp_info.return_value = None
        mock_updata_status.reset_mock()
        mock_post_sfp_info.reset_mock()
        # SFP information is not in the DB, and SFP is present, and SFP has no error, and SFP EEPROM reading succeed
        task.on_add_logical_port(port_change_event)
        assert mock_updata_status.call_count == 1
        mock_updata_status.assert_called_with('Ethernet0', status_tbl, SFP_STATUS_INSERTED, 'N/A')
        assert mock_post_sfp_info.call_count == 1
        mock_post_sfp_info.assert_called_with('Ethernet0', task.port_mapping, int_tbl, {})
        assert mock_post_dom_info.call_count == 1
        mock_post_dom_info.assert_called_with('Ethernet0', task.port_mapping, dom_tbl)
        assert mock_post_dom_th.call_count == 1
        mock_post_dom_th.assert_called_with('Ethernet0', task.port_mapping, dom_tbl)
        assert mock_update_media_setting.call_count == 1
        assert 'Ethernet0' not in task.retry_eeprom_set

        mock_get_presence.return_value = False
        mock_updata_status.reset_mock()
        # SFP information is not in DB and SFP is not present
        task.on_add_logical_port(port_change_event)
        assert mock_updata_status.call_count == 1
        mock_updata_status.assert_called_with('Ethernet0', status_tbl, SFP_STATUS_REMOVED, 'N/A')

        task.sfp_error_dict[1] = (str(SfpBase.SFP_ERROR_BIT_BLOCKING | SfpBase.SFP_ERROR_BIT_POWER_BUDGET_EXCEEDED), {})
        mock_updata_status.reset_mock()
        # SFP information is not in DB, and SFP is not present, and SFP is in error status
        task.on_add_logical_port(port_change_event)
        assert mock_updata_status.call_count == 1
        mock_updata_status.assert_called_with('Ethernet0', status_tbl, task.sfp_error_dict[1][0], 'Blocking EEPROM from being read|Power budget exceeded')

    def test_sfp_insert_events(self):
        from xcvrd.xcvrd import _wrapper_soak_sfp_insert_event
        sfp_insert_events = {}
        insert = port_dict = {1:'1', 2:'1', 3:'1', 4:'1', 5:'1'}
        start = time.time()
        while True:
            _wrapper_soak_sfp_insert_event(sfp_insert_events, insert)
            if time.time() - start > MGMT_INIT_TIME_DELAY_SECS:
                break
            assert not bool(insert)
        assert insert == port_dict


    def test_sfp_remove_events(self):
        from xcvrd.xcvrd import _wrapper_soak_sfp_insert_event
        sfp_insert_events = {}
        insert = {1:'1', 2:'1', 3:'1', 4:'1', 5:'1'}
        removal = {1:'0', 2:'0', 3:'0', 4:'0', 5:'0'}
        port_dict = {1:'0', 2:'0', 3:'0', 4:'0', 5:'0'}
        for x in range(5):
            _wrapper_soak_sfp_insert_event(sfp_insert_events, insert)
            time.sleep(1)
            _wrapper_soak_sfp_insert_event(sfp_insert_events, removal)

        assert port_dict == removal

    @patch('xcvrd.xcvrd.platform_chassis')
    @patch('xcvrd.xcvrd.platform_sfputil')
    def test_wrapper_get_presence(self, mock_sfputil, mock_chassis):
        mock_object = MagicMock()
        mock_object.get_presence = MagicMock(return_value=True)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        from xcvrd.xcvrd import _wrapper_get_presence
        assert _wrapper_get_presence(1)

        mock_object.get_presence = MagicMock(return_value=False)
        assert not _wrapper_get_presence(1)

        mock_chassis.get_sfp = MagicMock(side_effect=NotImplementedError)
        mock_sfputil.get_presence = MagicMock(return_value=True)
        
        assert _wrapper_get_presence(1)

        mock_sfputil.get_presence = MagicMock(return_value=False)
        assert not _wrapper_get_presence(1)

    @patch('xcvrd.xcvrd.platform_chassis')
    def test_wrapper_is_replaceable(self, mock_chassis):
        mock_object = MagicMock()
        mock_object.is_replaceable = MagicMock(return_value=True)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        from xcvrd.xcvrd import _wrapper_is_replaceable
        assert _wrapper_is_replaceable(1)

        mock_object.is_replaceable = MagicMock(return_value=False)
        assert not _wrapper_is_replaceable(1)

        mock_chassis.get_sfp = MagicMock(side_effect=NotImplementedError)
        assert not _wrapper_is_replaceable(1)

    @patch('xcvrd.xcvrd.platform_chassis')
    @patch('xcvrd.xcvrd.platform_sfputil')
    def test_wrapper_get_transceiver_info(self, mock_sfputil, mock_chassis):
        mock_object = MagicMock()
        mock_object.get_transceiver_info = MagicMock(return_value=True)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        from xcvrd.xcvrd import _wrapper_get_transceiver_info
        assert _wrapper_get_transceiver_info(1)

        mock_object.get_transceiver_info = MagicMock(return_value=False)
        assert not _wrapper_get_transceiver_info(1)

        mock_chassis.get_sfp = MagicMock(side_effect=NotImplementedError)
        mock_sfputil.get_transceiver_info_dict = MagicMock(return_value=True)
        
        assert _wrapper_get_transceiver_info(1)

        mock_sfputil.get_transceiver_info_dict = MagicMock(return_value=False)
        assert not _wrapper_get_transceiver_info(1)

    @patch('xcvrd.xcvrd.platform_chassis')
    @patch('xcvrd.xcvrd.platform_sfputil')
    def test_wrapper_get_transceiver_dom_info(self, mock_sfputil, mock_chassis):
        mock_object = MagicMock()
        mock_object.get_transceiver_bulk_status = MagicMock(return_value=True)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        from xcvrd.xcvrd import _wrapper_get_transceiver_dom_info
        assert _wrapper_get_transceiver_dom_info(1)

        mock_object.get_transceiver_bulk_status = MagicMock(return_value=False)
        assert not _wrapper_get_transceiver_dom_info(1)

        mock_chassis.get_sfp = MagicMock(side_effect=NotImplementedError)
        mock_sfputil.get_transceiver_dom_info_dict = MagicMock(return_value=True)
        
        assert _wrapper_get_transceiver_dom_info(1)

        mock_sfputil.get_transceiver_dom_info_dict = MagicMock(return_value=False)
        assert not _wrapper_get_transceiver_dom_info(1)

    @patch('xcvrd.xcvrd.platform_chassis')
    @patch('xcvrd.xcvrd.platform_sfputil')
    def test_wrapper_get_transceiver_dom_threshold_info(self, mock_sfputil, mock_chassis):
        mock_object = MagicMock()
        mock_object.get_transceiver_threshold_info = MagicMock(return_value=True)
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        from xcvrd.xcvrd import _wrapper_get_transceiver_dom_threshold_info
        assert _wrapper_get_transceiver_dom_threshold_info(1)

        mock_object.get_transceiver_threshold_info = MagicMock(return_value=False)
        assert not _wrapper_get_transceiver_dom_threshold_info(1)

        mock_chassis.get_sfp = MagicMock(side_effect=NotImplementedError)
        mock_sfputil.get_transceiver_dom_threshold_info_dict = MagicMock(return_value=True)
        
        assert _wrapper_get_transceiver_dom_threshold_info(1)

        mock_sfputil.get_transceiver_dom_threshold_info_dict = MagicMock(return_value=False)
        assert not _wrapper_get_transceiver_dom_threshold_info(1)

    @patch('xcvrd.xcvrd.platform_chassis')
    @patch('xcvrd.xcvrd.platform_sfputil')
    def test_wrapper_get_transceiver_change_event(self, mock_sfputil, mock_chassis):
        mock_chassis.get_change_event = MagicMock(return_value=(True, {'sfp': 1, 'sfp_error': 'N/A'}))
        from xcvrd.xcvrd import _wrapper_get_transceiver_change_event
        assert _wrapper_get_transceiver_change_event(0) == (True, 1, 'N/A')

        mock_chassis.get_change_event = MagicMock(side_effect=NotImplementedError)
        mock_sfputil.get_transceiver_change_event = MagicMock(return_value=(True, 1))

        assert _wrapper_get_transceiver_change_event(0) == (True, 1, None)

    @patch('xcvrd.xcvrd.platform_chassis')
    def test_wrapper_get_sfp_type(self, mock_chassis):
        mock_object = MagicMock()
        mock_object.sfp_type = 'QSFP'
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        from xcvrd.xcvrd import _wrapper_get_sfp_type
        assert _wrapper_get_sfp_type(1) == 'QSFP'

        mock_chassis.get_sfp = MagicMock(side_effect=NotImplementedError)
        assert not _wrapper_get_sfp_type(1)

    @patch('xcvrd.xcvrd.platform_chassis')
    def test_wrapper_get_sfp_error_description(self, mock_chassis):
        mock_object = MagicMock()
        mock_object.get_error_description = MagicMock(return_value='N/A')
        mock_chassis.get_sfp = MagicMock(return_value=mock_object)
        from xcvrd.xcvrd import _wrapper_get_sfp_error_description
        assert _wrapper_get_sfp_error_description(1) == 'N/A'

        mock_chassis.get_sfp = MagicMock(side_effect=NotImplementedError)
        assert not _wrapper_get_sfp_error_description(1)

    def test_check_port_in_range(self):
        range_str = '1 - 32'
        physical_port = 1
        assert check_port_in_range(range_str, physical_port)

        physical_port = 32
        assert check_port_in_range(range_str, physical_port)

        physical_port = 0
        assert not check_port_in_range(range_str, physical_port)

        physical_port = 33
        assert not check_port_in_range(range_str, physical_port)

    def test_get_media_val_str_from_dict(self):
        media_dict = {'lane0': '1', 'lane1': '2'}
        media_str = get_media_val_str_from_dict(media_dict)
        assert media_str == '1,2'

    def test_get_media_val_str(self):
        num_logical_ports = 1
        lane_dict = {'lane0': '1', 'lane1': '2', 'lane2': '3', 'lane3': '4'}
        logical_idx = 1
        media_str = get_media_val_str(num_logical_ports, lane_dict, logical_idx)
        assert media_str == '1,2,3,4'
        num_logical_ports = 2
        logical_idx = 1
        media_str = get_media_val_str(num_logical_ports, lane_dict, logical_idx)
        assert media_str == '3,4'

    @patch('xcvrd.xcvrd.DaemonXcvrd.load_platform_util', MagicMock())
    @patch('sonic_py_common.device_info.get_paths_to_platform_and_hwsku_dirs', MagicMock(return_value=('/tmp', None)))
    @patch('swsscommon.swsscommon.WarmStart', MagicMock())    
    @patch('xcvrd.xcvrd.DaemonXcvrd.wait_for_port_config_done', MagicMock())
    def test_DaemonXcvrd_init_deinit(self):
        xcvrd = DaemonXcvrd(SYSLOG_IDENTIFIER)
        xcvrd.init()
        xcvrd.deinit()
        # TODO: fow now we only simply call xcvrd.init/deinit without any further check, it only makes sure that
        # xcvrd.init/deinit will not raise unexpected exception. In future, probably more check will be added



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
