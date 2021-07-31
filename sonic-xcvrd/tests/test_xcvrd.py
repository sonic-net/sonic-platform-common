import os
import sys
import time

import unittest
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

class TestXcvrdScript(object):

    def test_xcvrd_helper_class_run(self):
        Y_cable_task = YCableTableUpdateTask()

    @patch('xcvrd.xcvrd.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
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
    def test_post_port_dom_info_to_db(self):
        logical_port_name = "Ethernet0"
        stop_event = threading.Event()
        dom_tbl = Table("STATE_DB", TRANSCEIVER_DOM_SENSOR_TABLE)
        post_port_dom_info_to_db(logical_port_name, dom_tbl, stop_event)

    @patch('xcvrd.xcvrd.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    def test_del_port_sfp_dom_info_from_db(self):
        logical_port_name = "Ethernet0"
        stop_event = threading.Event()
        dom_tbl = Table("STATE_DB", TRANSCEIVER_DOM_SENSOR_TABLE)
        init_tbl = Table("STATE_DB", TRANSCEIVER_INFO_TABLE)
        del_port_sfp_dom_info_from_db(logical_port_name, init_tbl, dom_tbl)

    @patch('xcvrd.xcvrd.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
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
        stop_event = threading.Event()
        dom_tbl = Table("STATE_DB", TRANSCEIVER_DOM_SENSOR_TABLE)
        post_port_dom_threshold_info_to_db(logical_port_name, dom_tbl, stop_event)

    @patch('xcvrd.xcvrd.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_is_replaceable', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_get_transceiver_info', MagicMock(return_value={'type': '22.75',
                                                                                'hardware_rev': '0.5',
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
        stop_event = threading.Event()
        dom_tbl = Table("STATE_DB", TRANSCEIVER_DOM_SENSOR_TABLE)
        transceiver_dict = {}
        post_port_sfp_info_to_db(logical_port_name, dom_tbl, transceiver_dict, stop_event)

    @patch('xcvrd.xcvrd.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd.platform_sfputil', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_is_replaceable', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_get_transceiver_info', MagicMock(return_value={'type': '22.75',
                                                                                'hardware_rev': '0.5',
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
        logical_port_name = "Ethernet0"
        stop_event = threading.Event()
        post_port_sfp_dom_info_to_db(True, stop_event)

    @patch('xcvrd.xcvrd.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd.platform_sfputil', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd._wrapper_get_presence', MagicMock(return_value=True))
    @patch('xcvrd.xcvrd._wrapper_is_replaceable', MagicMock(return_value=True))
    def test_init_port_sfp_status_tbl(self):
        stop_event = threading.Event()
        init_port_sfp_status_tbl(stop_event)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper._wrapper_get_presence', MagicMock(return_value=True))
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
        mux_tbl = Table("STATE_DB", y_cable_helper.MUX_CABLE_INFO_TABLE)
        rc = post_port_mux_info_to_db(logical_port_name, mux_tbl)
        assert(rc != -1)

    @patch('xcvrd.xcvrd_utilities.y_cable_helper.y_cable_platform_sfputil', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper.logical_port_name_to_physical_port_list', MagicMock(return_value=[0]))
    @patch('xcvrd.xcvrd_utilities.y_cable_helper._wrapper_get_presence', MagicMock(return_value=True))
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
        mux_tbl = Table("STATE_DB", y_cable_helper.MUX_CABLE_STATIC_INFO_TABLE)
        rc = post_port_mux_static_info_to_db(logical_port_name, mux_tbl)
        assert(rc != -1)

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

    def test_sfp_insert_events(self):
        from xcvrd.xcvrd import _wrapper_soak_sfp_insert_event
        sfp_insert_events = {}
        insert = port_dict = {1:'1', 2:'1', 3:'1', 4:'1', 5:'1'}
        start = time.time()
        while True:
            _wrapper_soak_sfp_insert_event(sfp_insert_events, insert)
            assert not bool(insert)
            if time.time() - start > MGMT_INIT_TIME_DELAY_SECS:
                break
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