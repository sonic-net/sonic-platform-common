from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.sff8024 import Sff8024
from sonic_platform_base.sonic_xcvr.codes.public.cmis_code import CmisCode

class TestCmis(object):

    def mock_cmis_api(self):
        codes = {'sff8024':Sff8024, 'cmis_code':CmisCode}
        mem_map = CmisMemMap(codes)
        reader = MagicMock(return_value=None)
        writer = MagicMock()
        xcvr_eeprom = XcvrEeprom(reader, writer, mem_map)
        api = CmisApi(xcvr_eeprom)
        return api

    @pytest.mark.parametrize("mock_response, expected", [
        ("1234567890", "1234567890"),
        ("ABCD", "ABCD")
    ])
    def test_get_model(self, mock_response, expected):
        """
        Verify all api access valid fields
        """
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_model()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("0.0", "0.0"),
        ("1.2", "1.2")
    ])
    def test_get_vendor_rev(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_vendor_rev()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("100000000", "100000000")
    ])
    def test_get_vendor_serial(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_vendor_serial()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("1a-1a-1a", "1a-1a-1a")
    ])
    def test_get_vendor_name(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_vendor_name()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("ABCDE", "ABCDE")
    ])
    def test_get_vendor_OUI(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_vendor_OUI()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("21010100", "21010100")
    ])
    def test_get_vendor_date(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_vendor_date()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("LC", "LC")
    ])
    def test_get_connector_type(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_connector_type()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("Single Mode Fiber (SMF)", "Single Mode Fiber (SMF)")
    ])
    def test_get_module_media_type(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_module_media_type()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("400GAUI-8 C2M (Annex 120E)", "400GAUI-8 C2M (Annex 120E)")
    ])
    def test_get_host_electrical_interface(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_host_electrical_interface()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        ("Single Mode Fiber (SMF)", "400ZR", "400ZR")
    ])
    def test_get_module_media_interface(self, mock_response1, mock_response2, expected):
        api = self.mock_cmis_api()
        api.get_module_media_type = MagicMock()
        api.get_module_media_type.return_value = mock_response1
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response2
        result = api.get_module_media_interface()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x81, 8)
    ])
    def test_get_host_lane_count(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_host_lane_count()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x81, 1)
    ])
    def test_get_media_lane_count(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_media_lane_count()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_get_host_lane_assignment_option(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_host_lane_assignment_option()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_get_media_lane_assignment_option(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_media_lane_assignment_option()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x10],
         {'hostlane1': 1, 'hostlane2': 1, 'hostlane3': 1, 'hostlane4': 1,
          'hostlane5': 1, 'hostlane6': 1, 'hostlane7': 1, 'hostlane8': 1})
    ])
    def test_get_active_apsel_hostlane(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_active_apsel_hostlane()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ('C-band tunable laser', 'C-band tunable laser')
    ])
    def test_get_media_interface_technology(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_media_interface_technology()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0, 1], '0.1')
    ])
    def test_get_module_hardware_revision(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_module_hardware_revision()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x50, '5.0')
    ])
    def test_get_cmis_rev(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_cmis_rev()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0, 1], '0.1')
    ])
    def test_get_module_active_firmware(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_module_active_firmware()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0, 1], '0.1')
    ])
    def test_get_module_inactive_firmware(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_module_inactive_firmware()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([45, 80, -10, 75, 0],
         {'monitor value': 45, 'high alarm': 80, 'low alarm': -10, 'high warn': 75, 'low warn': 0})
    ])
    def test_get_module_temperature(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_module_temperature()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([3.3, 3.5, 3.1, 3.45, 3.15],
         {'monitor value': 3.3, 'high alarm': 3.5, 'low alarm': 3.1, 'high warn': 3.45, 'low warn': 3.15})
    ])
    def test_get_module_voltage(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_module_voltage()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([-10, -2, -15, -4, -14],
         {'monitor value lane1': -10, 'high alarm': -2, 'low alarm': -15, 'high warn': -4, 'low warn': -14})
    ])
    def test_get_txpower(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_txpower()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([-10, -2, -15, -4, -14],
         {'monitor value lane1': -10, 'high alarm': -2, 'low alarm': -15, 'high warn': -4, 'low warn': -14})
    ])
    def test_get_rxpower(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_rxpower()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([50, 70, 0, 68, 0],
         {'monitor value lane1': 50, 'high alarm': 70, 'low alarm': 0, 'high warn': 68, 'low warn': 0})
    ])
    def test_get_txbias(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_txbias()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x70, 75)
    ])
    def test_get_freq_grid(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_freq_grid()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (75, 12, 193400),
        (75, -30, 192350),
    ])
    def test_get_laser_config_freq(self, mock_response1, mock_response2, expected):
        api = self.mock_cmis_api()
        api.get_freq_grid = MagicMock()
        api.get_freq_grid.return_value = mock_response1
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response2
        result = api.get_laser_config_freq()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (193100000, 193100)
    ])
    def test_get_current_laser_freq(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_current_laser_freq()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (-10, -10)
    ])
    def test_get_TX_config_power(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_TX_config_power()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, False),
        (1, True),
    ])
    def test_get_media_output_loopback(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_media_output_loopback()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, False),
        (1, True),
    ])
    def test_get_media_input_loopback(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_media_input_loopback()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, [False,False,False,False,False,False,False,False]),
    ])
    def test_get_host_output_loopback(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_host_output_loopback()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, [False,False,False,False,False,False,False,False]),
    ])
    def test_get_host_input_loopback(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_host_input_loopback()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0xc2, (0,1,0)),
    ])
    def test_get_aux_mon_type(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_aux_mon_type()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        ([0,1,0],
        [11520, 20480, -2560, 19200, 0],
        {'monitor value': 45, 'high alarm': 80, 'low alarm': -10, 'high warn': 75, 'low warn': 0}
        )
    ])
    def test_get_laser_temperature(self, mock_response1, mock_response2, expected):
        api = self.mock_cmis_api()
        api.get_aux_mon_type = MagicMock()
        api.get_aux_mon_type.return_value = mock_response1
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response2
        result = api.get_laser_temperature()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        ([0,1,0],
        [32767, 65534, 0, 49150.5, 0],
        {'monitor value': 1, 'high alarm': 2, 'low alarm': 0, 'high warn': 1.5, 'low warn': 0}
        )
    ])
    def test_get_laser_TEC_current(self, mock_response1, mock_response2, expected):
        api = self.mock_cmis_api()
        api.get_aux_mon_type = MagicMock()
        api.get_aux_mon_type.return_value = mock_response1
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response2
        result = api.get_laser_TEC_current()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        ([False, 1.0], 100, 100.0)
    ])
    def test_get_custom_field(self, input_param, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_custom_field(*input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            {'preFEC_BER_avg': 0.001},
            {'preFEC_BER_avg': 0.001}      
        )
    ])
    def test_get_PM(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.ccmis = MagicMock()
        api.ccmis.get_PM_all = MagicMock()
        api.ccmis.get_PM_all.return_value = mock_response
        result = api.get_PM()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            {'Pre-FEC BER Average Media Input': {1: [0.001, 0.0125, 0, 0.01, 0, False, False, False, False]}},
            {'Pre-FEC BER Average Media Input': {1: [0.001, 0.0125, 0, 0.01, 0, False, False, False, False]}}
        )
    ])
    def test_get_VDM(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.vdm = MagicMock()
        api.vdm.get_VDM_allpage = MagicMock()
        api.vdm.get_VDM_allpage.return_value = mock_response
        result = api.get_VDM()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (6, "ModuleReady")
    ])
    def test_get_module_state(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_module_state()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (65, (False, False, True))
    ])
    def test_get_module_firmware_fault_state_changed(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_module_firmware_fault_state_changed()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0, 0, 0],
        {
            'voltage_flags': {
                'voltage_high_alarm_flag': False,
                'voltage_low_alarm_flag': False,
                'voltage_high_warn_flag': False,
                'voltage_low_warn_flag': False
            },
            'case_temp_flags': {
                'case_temp_high_alarm_flag': False,
                'case_temp_low_alarm_flag': False,
                'case_temp_high_warn_flag': False,
                'case_temp_low_warn_flag': False
            },
            'aux1_flags': {
                'aux1_high_alarm_flag': False,
                'aux1_low_alarm_flag': False,
                'aux1_high_warn_flag': False,
                'aux1_low_warn_flag': False
            },
            'aux2_flags': {
                'aux2_high_alarm_flag': False,
                'aux2_low_alarm_flag': False,
                'aux2_high_warn_flag': False,
                'aux2_low_warn_flag': False
            },
            'aux3_flags': {
                'aux3_high_alarm_flag': False,
                'aux3_low_alarm_flag': False,
                'aux3_high_warn_flag': False,
                'aux3_low_warn_flag': False
            },
            'custom_mon_flags': {
                'custom_mon_high_alarm_flag': False,
                'custom_mon_low_alarm_flag': False,
                'custom_mon_high_warn_flag': False,
                'custom_mon_low_warn_flag': False
            }
        })
    ])
    def test_get_module_level_flag(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_module_level_flag()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1145324612, 
         {
            'dp_lane1': 'DataPathActivated',
            'dp_lane2': 'DataPathActivated',
            'dp_lane3': 'DataPathActivated',
            'dp_lane4': 'DataPathActivated',
            'dp_lane5': 'DataPathActivated',
            'dp_lane6': 'DataPathActivated',
            'dp_lane7': 'DataPathActivated',
            'dp_lane8': 'DataPathActivated',
         })
    ])
    def test_get_datapath_state(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_datapath_state()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0xff, 
         {
            'TX_lane1': True,
            'TX_lane2': True,
            'TX_lane3': True,
            'TX_lane4': True,
            'TX_lane5': True,
            'TX_lane6': True,
            'TX_lane7': True,
            'TX_lane8': True,
         })
    ])
    def test_get_tx_output_status(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_tx_output_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0xff, 
         {
            'RX_lane1': True,
            'RX_lane2': True,
            'RX_lane3': True,
            'RX_lane4': True,
            'RX_lane5': True,
            'RX_lane6': True,
            'RX_lane7': True,
            'RX_lane8': True,
         })
    ])
    def test_get_rx_output_status(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_rx_output_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x00, 
         {
            'TX_lane1': False,
            'TX_lane2': False,
            'TX_lane3': False,
            'TX_lane4': False,
            'TX_lane5': False,
            'TX_lane6': False,
            'TX_lane7': False,
            'TX_lane8': False,
         })
    ])
    def test_get_tx_fault(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_tx_fault()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x00, 
         {
            'TX_lane1': False,
            'TX_lane2': False,
            'TX_lane3': False,
            'TX_lane4': False,
            'TX_lane5': False,
            'TX_lane6': False,
            'TX_lane7': False,
            'TX_lane8': False,
         })
    ])
    def test_get_tx_los(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_tx_los()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x00, 
         {
            'TX_lane1': False,
            'TX_lane2': False,
            'TX_lane3': False,
            'TX_lane4': False,
            'TX_lane5': False,
            'TX_lane6': False,
            'TX_lane7': False,
            'TX_lane8': False,
         })
    ])
    def test_get_tx_cdr_lol(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_tx_cdr_lol()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0x00, 0x00, 0x00, 0x00], 
         {
            'tx_power_high_alarm':{
                'TX_lane1': False,
                'TX_lane2': False,
                'TX_lane3': False,
                'TX_lane4': False,
                'TX_lane5': False,
                'TX_lane6': False,
                'TX_lane7': False,
                'TX_lane8': False,
            },
            'tx_power_low_alarm':{
                'TX_lane1': False,
                'TX_lane2': False,
                'TX_lane3': False,
                'TX_lane4': False,
                'TX_lane5': False,
                'TX_lane6': False,
                'TX_lane7': False,
                'TX_lane8': False,
            },
            'tx_power_high_warn':{
                'TX_lane1': False,
                'TX_lane2': False,
                'TX_lane3': False,
                'TX_lane4': False,
                'TX_lane5': False,
                'TX_lane6': False,
                'TX_lane7': False,
                'TX_lane8': False,
            },
            'tx_power_low_warn':{
                'TX_lane1': False,
                'TX_lane2': False,
                'TX_lane3': False,
                'TX_lane4': False,
                'TX_lane5': False,
                'TX_lane6': False,
                'TX_lane7': False,
                'TX_lane8': False,
            }
         })
    ])
    def test_get_tx_power_flag(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_tx_power_flag()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0x00, 0x00, 0x00, 0x00], 
         {
            'tx_bias_high_alarm':{
                'TX_lane1': False,
                'TX_lane2': False,
                'TX_lane3': False,
                'TX_lane4': False,
                'TX_lane5': False,
                'TX_lane6': False,
                'TX_lane7': False,
                'TX_lane8': False,
            },
            'tx_bias_low_alarm':{
                'TX_lane1': False,
                'TX_lane2': False,
                'TX_lane3': False,
                'TX_lane4': False,
                'TX_lane5': False,
                'TX_lane6': False,
                'TX_lane7': False,
                'TX_lane8': False,
            },
            'tx_bias_high_warn':{
                'TX_lane1': False,
                'TX_lane2': False,
                'TX_lane3': False,
                'TX_lane4': False,
                'TX_lane5': False,
                'TX_lane6': False,
                'TX_lane7': False,
                'TX_lane8': False,
            },
            'tx_bias_low_warn':{
                'TX_lane1': False,
                'TX_lane2': False,
                'TX_lane3': False,
                'TX_lane4': False,
                'TX_lane5': False,
                'TX_lane6': False,
                'TX_lane7': False,
                'TX_lane8': False,
            }
         })
    ])
    def test_get_tx_bias_flag(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_tx_bias_flag()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0x00, 0x00, 0x00, 0x00], 
         {
            'rx_power_high_alarm':{
                'RX_lane1': False,
                'RX_lane2': False,
                'RX_lane3': False,
                'RX_lane4': False,
                'RX_lane5': False,
                'RX_lane6': False,
                'RX_lane7': False,
                'RX_lane8': False,
            },
            'rx_power_low_alarm':{
                'RX_lane1': False,
                'RX_lane2': False,
                'RX_lane3': False,
                'RX_lane4': False,
                'RX_lane5': False,
                'RX_lane6': False,
                'RX_lane7': False,
                'RX_lane8': False,
            },
            'rx_power_high_warn':{
                'RX_lane1': False,
                'RX_lane2': False,
                'RX_lane3': False,
                'RX_lane4': False,
                'RX_lane5': False,
                'RX_lane6': False,
                'RX_lane7': False,
                'RX_lane8': False,
            },
            'rx_power_low_warn':{
                'RX_lane1': False,
                'RX_lane2': False,
                'RX_lane3': False,
                'RX_lane4': False,
                'RX_lane5': False,
                'RX_lane6': False,
                'RX_lane7': False,
                'RX_lane8': False,
            }
         })
    ])
    def test_get_rx_power_flag(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_rx_power_flag()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x00, 
         {
            'RX_lane1': False,
            'RX_lane2': False,
            'RX_lane3': False,
            'RX_lane4': False,
            'RX_lane5': False,
            'RX_lane6': False,
            'RX_lane7': False,
            'RX_lane8': False,
         })
    ])
    def test_get_rx_los(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_rx_los()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x00, 
         {
            'RX_lane1': False,
            'RX_lane2': False,
            'RX_lane3': False,
            'RX_lane4': False,
            'RX_lane5': False,
            'RX_lane6': False,
            'RX_lane7': False,
            'RX_lane8': False,
         })
    ])
    def test_get_rx_cdr_lol(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_rx_cdr_lol()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (286331153, 
         {
            'config_DP_status_hostlane1': 'ConfigSuccess',
            'config_DP_status_hostlane2': 'ConfigSuccess',
            'config_DP_status_hostlane3': 'ConfigSuccess',
            'config_DP_status_hostlane4': 'ConfigSuccess',
            'config_DP_status_hostlane5': 'ConfigSuccess',
            'config_DP_status_hostlane6': 'ConfigSuccess',
            'config_DP_status_hostlane7': 'ConfigSuccess',
            'config_DP_status_hostlane8': 'ConfigSuccess',
         })
    ])
    def test_get_config_datapath_hostlane_status(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_config_datapath_hostlane_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, 
         {
            'hostlane1': False,
            'hostlane2': False,
            'hostlane3': False,
            'hostlane4': False,
            'hostlane5': False,
            'hostlane6': False,
            'hostlane7': False,
            'hostlane8': False,
         })
    ])
    def test_get_dpinit_pending(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_dpinit_pending()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, False)
    ])
    def test_get_tuning_in_progress(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_tuning_in_progress()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, False)
    ])
    def test_get_wavelength_unlocked(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_wavelength_unlocked()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, ['TuningComplete'])
    ])
    def test_get_laser_tuning_summary(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_laser_tuning_summary()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([190, -72, 120], (190, -72, 120, 191300, 196100))
    ])
    def test_get_supported_freq_config(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_supported_freq_config()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([-20, 0], (-20,0))
    ])
    def test_get_supported_power_config(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_supported_power_config()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (127,
        {
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_media_loopback_supported': True,
            'per_lane_host_loopback_supported': True,
            'host_side_input_loopback_supported': True,
            'host_side_output_loopback_supported': True,
            'media_side_input_loopback_supported': True,
            'media_side_output_loopback_supported': True
        })
    ])
    def test_get_loopback_capability(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_loopback_capability()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        ([0x77, 0xff], [18, 35, (0, 7, 112, 255, 255, 16, 0, 0, 19, 136, 0, 100, 3, 232, 19, 136, 58, 152)],
        (112, 2048, False, True, 2048)
        )
    ])
    def test_get_module_FW_upgrade_feature(self, mock_response1, mock_response2, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response1
        api.cdb = MagicMock()
        api.cdb.cmd0041h = MagicMock()
        api.cdb.cmd0041h.return_value = mock_response2
        api.cdb.cdb_chkcode = MagicMock()
        api.cdb.cdb_chkcode.return_value = mock_response2[1]
        result = api.get_module_FW_upgrade_feature()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([110, 26, (3, 3, 1, 1, 0, 4, 1, 4, 3, 0, 0, 100, 3, 232, 19, 136, 58, 152, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 4, 1, 4, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)],
        ('1.1.4', 1, 1, 0, '1.1.4', 0, 0, 0)
        )
    ])
    def test_get_module_FW_info(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.cdb = MagicMock()
        api.cdb.cmd0100h = MagicMock()
        api.cdb.cmd0100h.return_value = mock_response
        api.cdb.cdb_chkcode = MagicMock()
        api.cdb.cdb_chkcode.return_value = mock_response[1]
        result = api.get_module_FW_info()
        assert result == expected
        # TODO: call other methods in the api

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                'Single Mode Fiber (SMF)', 
                '400GAUI-8 C2M (Annex 120E)',
                '400ZR, DWDM, amplified',
                8, 1, 1, 1,
                {'hostlane1': 1, 'hostlane2': 1, 'hostlane3': 1, 'hostlane4': 1,
                'hostlane5': 1, 'hostlane6': 1, 'hostlane7': 1, 'hostlane8': 1},
                '1550 nm DFB',
                '0.0',
                '00000000',
                'VENDOR_NAME',
                '0.0',
                'xx-xx-xx',
                '21010100',
                'LC',
                '5.0',
                '0.1',
                '0.0',
                (-20, 0),
                (0xff, -72, 120, 191300, 196100)
            ],
            {
                'active_firmware': '0.1',
                'media_lane_count': 1,
                'supported_min_laser_freq': 191300,
                'inactive_firmware': '0.0',
                'vendor_rev': '0.0',
                'host_electrical_interface': '400GAUI-8 C2M (Annex 120E)',
                'vendor_oui': 'xx-xx-xx',
                'manufacturename': 'VENDOR_NAME',
                'media_interface_technology': '1550 nm DFB',
                'media_interface_code': '400ZR, DWDM, amplified',
                'serialnum': '00000000',
                'module_media_type': 'Single Mode Fiber (SMF)',
                'host_lane_count': 8,
                'active_apsel_hostlane1': 1,
                'active_apsel_hostlane3': 1,
                'active_apsel_hostlane2': 1,
                'active_apsel_hostlane5': 1,
                'active_apsel_hostlane4': 1,
                'active_apsel_hostlane7': 1,
                'active_apsel_hostlane6': 1,
                'supported_max_laser_freq': 196100,
                'active_apsel_hostlane8': 1,
                'hardwarerev': '0.0',
                'specification_compliance': '5.0',
                'media_lane_assignment_option': 1,
                'connector_type': 'LC',
                'host_lane_assignment_option': 1,
                'supported_max_tx_power': 0,
                'supported_min_tx_power': -20,
                'vendor_date': '21010100'
            }
        )
    ])
    def test_get_transceiver_info(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.get_module_media_type = MagicMock()
        api.get_module_media_type.return_value = mock_response[0]
        api.get_host_electrical_interface = MagicMock()
        api.get_host_electrical_interface.return_value = mock_response[1]
        api.get_module_media_interface = MagicMock()
        api.get_module_media_interface.return_value = mock_response[2]
        api.get_host_lane_count = MagicMock()
        api.get_host_lane_count.return_value = mock_response[3]
        api.get_media_lane_count = MagicMock()
        api.get_media_lane_count.return_value = mock_response[4]
        api.get_host_lane_assignment_option = MagicMock()
        api.get_host_lane_assignment_option.return_value = mock_response[5]
        api.get_media_lane_assignment_option = MagicMock()
        api.get_media_lane_assignment_option.return_value = mock_response[6]
        api.get_active_apsel_hostlane = MagicMock()
        api.get_active_apsel_hostlane.return_value = mock_response[7]
        api.get_media_interface_technology = MagicMock()
        api.get_media_interface_technology.return_value = mock_response[8]
        api.get_module_hardware_revision = MagicMock()
        api.get_module_hardware_revision.return_value = mock_response[9]
        api.get_vendor_serial = MagicMock()
        api.get_vendor_serial.return_value = mock_response[10]
        api.get_vendor_name = MagicMock()
        api.get_vendor_name.return_value = mock_response[11]
        api.get_vendor_rev = MagicMock()
        api.get_vendor_rev.return_value = mock_response[12]
        api.get_vendor_OUI = MagicMock()
        api.get_vendor_OUI.return_value = mock_response[13]
        api.get_vendor_date = MagicMock()
        api.get_vendor_date.return_value = mock_response[14]
        api.get_connector_type = MagicMock()
        api.get_connector_type.return_value = mock_response[15]
        api.get_cmis_rev = MagicMock()
        api.get_cmis_rev.return_value = mock_response[16]
        api.get_module_active_firmware = MagicMock()
        api.get_module_active_firmware.return_value = mock_response[17]
        api.get_module_inactive_firmware = MagicMock()
        api.get_module_inactive_firmware.return_value = mock_response[18]
        api.get_supported_power_config = MagicMock()
        api.get_supported_power_config.return_value = mock_response[19]
        api.get_supported_freq_config = MagicMock()
        api.get_supported_freq_config.return_value = mock_response[20]
        result = api.get_transceiver_info()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                {'monitor value': 50},
                {'monitor value': 3.3},
                {'monitor value lane1': 0.1},
                {'monitor value lane1': 0.09},
                {'monitor value lane1': 70},
                {'monitor value': 40},
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                    'Modulator Bias X/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'CD high granularity, short link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'CD low granularity, long link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'DGD [ps]':{1:[5, 30, 0, 25, 0, False, False, False, False]},
                    'SOPMD [ps^2]':{1:[5, 100, 0, 80, 0, False, False, False, False]},
                    'PDL [dB]':{1:[0.5, 3, 0, 2.5, 0, False, False, False, False]},
                    'OSNR [dB]':{1:[30, 100, 26, 80, 27, False, False, False, False]},
                    'eSNR [dB]':{1:[16, 100, 13, 80, 14, False, False, False, False]},
                    'CFO [MHz]':{1:[100, 5000, -5000, 4000, -4000, False, False, False, False]},
                    'Tx Power [dBm]':{1:[-10, 0, -18, -2, -16, False, False, False, False]},
                    'Rx Total Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]},
                    'Rx Signal Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]}
                },
                193100, 193100, -10
            ],
            {
                'temperature': 50,
                'voltage': 3.3,
                'txpower': 0.1,
                'rxpower': 0.09,
                'txbias': 70,
                'laser_temperature': 40,
                'prefec_ber': 0.001,
                'postfec_ber': 0,
                'bias_xi': 50,
                'bias_xq': 50,
                'bias_xp': 50,
                'bias_yi': 50,
                'bias_yq': 50,
                'bias_yp': 50,
                'cd_shortlink': 1000,
                'cd_longlink': 1000,
                'dgd': 5,
                'sopmd': 5,
                'pdl': 0.5,
                'osnr': 30,
                'esnr': 16,
                'cfo': 100,
                'tx_curr_power': -10,
                'rx_tot_power': -10,
                'rx_sig_power': -10,
                'laser_config_freq': 193100,
                'laser_curr_freq': 193100,
                'tx_config_power': -10
            }
        )
    ])
    def test_get_transceiver_bulk_status(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.get_module_temperature = MagicMock()
        api.get_module_temperature.return_value = mock_response[0]
        api.get_module_voltage = MagicMock()
        api.get_module_voltage.return_value = mock_response[1]
        api.get_txpower = MagicMock()
        api.get_txpower.return_value = mock_response[2]
        api.get_rxpower = MagicMock()
        api.get_rxpower.return_value = mock_response[3]
        api.get_txbias = MagicMock()
        api.get_txbias.return_value = mock_response[4]
        api.get_laser_temperature = MagicMock()
        api.get_laser_temperature.return_value = mock_response[5]
        api.get_VDM = MagicMock()
        api.get_VDM.return_value = mock_response[6]
        api.get_laser_config_freq = MagicMock()
        api.get_laser_config_freq.return_value = mock_response[7]
        api.get_current_laser_freq = MagicMock()
        api.get_current_laser_freq.return_value = mock_response[8]
        api.get_TX_config_power = MagicMock()
        api.get_TX_config_power.return_value = mock_response[9]
        result = api.get_transceiver_bulk_status()
        assert result == expected


    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                {'high alarm': 80, 'low alarm': 0, 'high warn': 75, 'low warn': 10},
                {'high alarm': 3.5, 'low alarm': 3.1, 'high warn': 3.45, 'low warn': 3.15},
                {'high alarm': 1.0, 'low alarm': 0.01, 'high warn': 0.7, 'low warn': 0.02},
                {'high alarm': 2.0, 'low alarm': 0.01, 'high warn': 1.0, 'low warn': 0.02},
                {'high alarm': 90, 'low alarm': 10, 'high warn': 80, 'low warn': 20},
                {'high alarm': 80, 'low alarm': 10, 'high warn': 75, 'low warn': 20},
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                    'Modulator Bias X/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'CD high granularity, short link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'CD low granularity, long link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'DGD [ps]':{1:[5, 30, 0, 25, 0, False, False, False, False]},
                    'SOPMD [ps^2]':{1:[5, 100, 0, 80, 0, False, False, False, False]},
                    'PDL [dB]':{1:[0.5, 3, 0, 2.5, 0, False, False, False, False]},
                    'OSNR [dB]':{1:[30, 100, 26, 80, 27, False, False, False, False]},
                    'eSNR [dB]':{1:[16, 100, 13, 80, 14, False, False, False, False]},
                    'CFO [MHz]':{1:[100, 5000, -5000, 4000, -4000, False, False, False, False]},
                    'Tx Power [dBm]':{1:[-10, 0, -18, -2, -16, False, False, False, False]},
                    'Rx Total Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]},
                    'Rx Signal Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]}
                }
            ],
            {
                'temphighalarm': 80, 'templowalarm': 0, 'temphighwarning': 75, 'templowwarning': 10,
                'vcchighalarm': 3.5, 'vcclowalarm': 3.1, 'vcchighwarning': 3.45, 'vcclowwarning': 3.15,
                'txpowerhighalarm': 1.0, 'txpowerlowalarm': 0.01, 'txpowerhighwarning': 0.7, 'txpowerlowwarning': 0.02,
                'rxpowerhighalarm': 2.0, 'rxpowerlowalarm': 0.01, 'rxpowerhighwarning': 1.0, 'rxpowerlowwarning': 0.02,
                'txbiashighalarm': 90, 'txbiaslowalarm': 10, 'txbiashighwarning': 80, 'txbiaslowwarning': 20,
                'lasertemphighalarm': 80, 'lasertemplowalarm': 10, 'lasertemphighwarning': 75, 'lasertemplowwarning': 20,
                'prefecberhighalarm': 0.0125, 'prefecberlowalarm': 0, 'prefecberhighwarning': 0.01, 'prefecberlowwarning': 0,
                'postfecberhighalarm': 1, 'postfecberlowalarm': 0, 'postfecberhighwarning': 1, 'postfecberlowwarning': 0,
                'biasxihighalarm': 90, 'biasxilowalarm': 10, 'biasxihighwarning': 85, 'biasxilowwarning': 15,
                'biasxqhighalarm': 90, 'biasxqlowalarm': 10, 'biasxqhighwarning': 85, 'biasxqlowwarning': 15,
                'biasxphighalarm': 90, 'biasxplowalarm': 10, 'biasxphighwarning': 85, 'biasxplowwarning': 15,
                'biasyihighalarm': 90, 'biasyilowalarm': 10, 'biasyihighwarning': 85, 'biasyilowwarning': 15,
                'biasyqhighalarm': 90, 'biasyqlowalarm': 10, 'biasyqhighwarning': 85, 'biasyqlowwarning': 15,
                'biasyphighalarm': 90, 'biasyplowalarm': 10, 'biasyphighwarning': 85, 'biasyplowwarning': 15,
                'cdshorthighalarm': 2000, 'cdshortlowalarm': 0, 'cdshorthighwarning': 1800, 'cdshortlowwarning': 0,
                'cdlonghighalarm': 2000, 'cdlonglowalarm': 0, 'cdlonghighwarning': 1800, 'cdlonglowwarning': 0,
                'dgdhighalarm': 30, 'dgdlowalarm': 0, 'dgdhighwarning': 25, 'dgdlowwarning': 0,
                'sopmdhighalarm': 100, 'sopmdlowalarm': 0, 'sopmdhighwarning': 80, 'sopmdlowwarning': 0,
                'pdlhighalarm': 3, 'pdllowalarm': 0, 'pdlhighwarning': 2.5, 'pdllowwarning': 0,
                'osnrhighalarm': 100, 'osnrlowalarm': 26, 'osnrhighwarning': 80, 'osnrlowwarning': 27,
                'esnrhighalarm': 100, 'esnrlowalarm': 13, 'esnrhighwarning': 80, 'esnrlowwarning': 14,
                'cfohighalarm': 5000, 'cfolowalarm': -5000, 'cfohighwarning': 4000, 'cfolowwarning': -4000,
                'txcurrpowerhighalarm': 0, 'txcurrpowerlowalarm': -18, 'txcurrpowerhighwarning': -2, 'txcurrpowerlowwarning': -16,
                'rxtotpowerhighalarm': 3, 'rxtotpowerlowalarm': -18, 'rxtotpowerhighwarning': 0, 'rxtotpowerlowwarning': -15,
                'rxsigpowerhighalarm': 3, 'rxsigpowerlowalarm': -18, 'rxsigpowerhighwarning': 0, 'rxsigpowerlowwarning': -15
            }
        )
    ])
    def test_get_transceiver_threshold_info(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.get_module_temperature = MagicMock()
        api.get_module_temperature.return_value = mock_response[0]
        api.get_module_voltage = MagicMock()
        api.get_module_voltage.return_value = mock_response[1]
        api.get_txpower = MagicMock()
        api.get_txpower.return_value = mock_response[2]
        api.get_rxpower = MagicMock()
        api.get_rxpower.return_value = mock_response[3]
        api.get_txbias = MagicMock()
        api.get_txbias.return_value = mock_response[4]
        api.get_laser_temperature = MagicMock()
        api.get_laser_temperature.return_value = mock_response[5]
        api.get_VDM = MagicMock()
        api.get_VDM.return_value = mock_response[6]
        result = api.get_transceiver_threshold_info()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                'ModuleReady', 'No Fault detected', (False, False, True),
                {
                    'dp_lane1': 'DataPathActivated', 'dp_lane2': 'DataPathActivated',
                    'dp_lane3': 'DataPathActivated', 'dp_lane4': 'DataPathActivated',
                    'dp_lane5': 'DataPathActivated', 'dp_lane6': 'DataPathActivated', 
                    'dp_lane7': 'DataPathActivated', 'dp_lane8': 'DataPathActivated'
                },
                {'TX_lane1': True},
                {
                    'RX_lane1': True, 'RX_lane2': True, 'RX_lane3': True, 'RX_lane4': True, 
                    'RX_lane5': True, 'RX_lane6': True, 'RX_lane7': True, 'RX_lane8': True 
                },
                {'TX_lane1': False},
                {
                    'TX_lane1': False, 'TX_lane2': False, 'TX_lane3': False, 'TX_lane4': False, 
                    'TX_lane5': False, 'TX_lane6': False, 'TX_lane7': False, 'TX_lane8': False 
                },
                {
                    'TX_lane1': False, 'TX_lane2': False, 'TX_lane3': False, 'TX_lane4': False, 
                    'TX_lane5': False, 'TX_lane6': False, 'TX_lane7': False, 'TX_lane8': False 
                },
                {'RX_lane1': False},
                {'RX_lane1': False},
                {
                    'config_DP_status_hostlane1': 'ConfigSuccess', 'config_DP_status_hostlane2': 'ConfigSuccess',
                    'config_DP_status_hostlane3': 'ConfigSuccess', 'config_DP_status_hostlane4': 'ConfigSuccess',
                    'config_DP_status_hostlane5': 'ConfigSuccess', 'config_DP_status_hostlane6': 'ConfigSuccess', 
                    'config_DP_status_hostlane7': 'ConfigSuccess', 'config_DP_status_hostlane8': 'ConfigSuccess'
                },
                {
                    'hostlane1': False, 'hostlane2': False,
                    'hostlane3': False, 'hostlane4': False,
                    'hostlane5': False, 'hostlane6': False, 
                    'hostlane7': False, 'hostlane8': False
                },
                False, False, ['TuningComplete'],
                {
                    'case_temp_flags': {
                        'case_temp_high_alarm_flag': False,
                        'case_temp_low_alarm_flag': False,
                        'case_temp_high_warn_flag': False,
                        'case_temp_low_warn_flag': False,
                    },
                    'voltage_flags': {
                        'voltage_high_alarm_flag': False,
                        'voltage_low_alarm_flag': False,
                        'voltage_high_warn_flag': False,
                        'voltage_low_warn_flag': False,
                    },
                    'aux1_flags': {
                        'aux1_high_alarm_flag': False,
                        'aux1_low_alarm_flag': False,
                        'aux1_high_warn_flag': False,
                        'aux1_low_warn_flag': False,
                    },
                    'aux2_flags': {
                        'aux2_high_alarm_flag': False,
                        'aux2_low_alarm_flag': False,
                        'aux2_high_warn_flag': False,
                        'aux2_low_warn_flag': False,
                    },
                    'aux3_flags': {
                        'aux3_high_alarm_flag': False,
                        'aux3_low_alarm_flag': False,
                        'aux3_high_warn_flag': False,
                        'aux3_low_warn_flag': False,
                    }
                },
                (0, 0, 0),
                {
                    'tx_power_high_alarm': {'TX_lane1': False},
                    'tx_power_low_alarm': {'TX_lane1': False},
                    'tx_power_high_warn': {'TX_lane1': False},
                    'tx_power_low_warn': {'TX_lane1': False},
                },
                {
                    'rx_power_high_alarm': {'RX_lane1': False},
                    'rx_power_low_alarm': {'RX_lane1': False},
                    'rx_power_high_warn': {'RX_lane1': False},
                    'rx_power_low_warn': {'RX_lane1': False},
                },
                {
                    'tx_bias_high_alarm': {'TX_lane1': False},
                    'tx_bias_low_alarm': {'TX_lane1': False},
                    'tx_bias_high_warn': {'TX_lane1': False},
                    'tx_bias_low_warn': {'TX_lane1': False},
                },
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                    'Modulator Bias X/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'CD high granularity, short link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'CD low granularity, long link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'DGD [ps]':{1:[5, 30, 0, 25, 0, False, False, False, False]},
                    'SOPMD [ps^2]':{1:[5, 100, 0, 80, 0, False, False, False, False]},
                    'PDL [dB]':{1:[0.5, 3, 0, 2.5, 0, False, False, False, False]},
                    'OSNR [dB]':{1:[30, 100, 26, 80, 27, False, False, False, False]},
                    'eSNR [dB]':{1:[16, 100, 13, 80, 14, False, False, False, False]},
                    'CFO [MHz]':{1:[100, 5000, -5000, 4000, -4000, False, False, False, False]},
                    'Tx Power [dBm]':{1:[-10, 0, -18, -2, -16, False, False, False, False]},
                    'Rx Total Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]},
                    'Rx Signal Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]}
                }
            ],
            {
                'module_state': 'ModuleReady',
                'module_fault_cause': 'No Fault detected',
                'datapath_firmware_fault': False,
                'module_firmware_fault': False,
                'module_state_changed': True,
                'datapath_hostlane1': 'DataPathActivated',
                'datapath_hostlane2': 'DataPathActivated',
                'datapath_hostlane3': 'DataPathActivated',
                'datapath_hostlane4': 'DataPathActivated',
                'datapath_hostlane5': 'DataPathActivated',
                'datapath_hostlane6': 'DataPathActivated',
                'datapath_hostlane7': 'DataPathActivated',
                'datapath_hostlane8': 'DataPathActivated',
                'txoutput_status': True,
                'rxoutput_status_hostlane1': True,
                'rxoutput_status_hostlane2': True,
                'rxoutput_status_hostlane3': True,
                'rxoutput_status_hostlane4': True,
                'rxoutput_status_hostlane5': True,
                'rxoutput_status_hostlane6': True,
                'rxoutput_status_hostlane7': True,
                'rxoutput_status_hostlane8': True,
                'txfault': False,
                'txlos_hostlane1': False,
                'txlos_hostlane2': False,
                'txlos_hostlane3': False,
                'txlos_hostlane4': False,
                'txlos_hostlane5': False,
                'txlos_hostlane6': False,
                'txlos_hostlane7': False,
                'txlos_hostlane8': False,
                'txcdrlol_hostlane1': False,
                'txcdrlol_hostlane2': False,
                'txcdrlol_hostlane3': False,
                'txcdrlol_hostlane4': False,
                'txcdrlol_hostlane5': False,
                'txcdrlol_hostlane6': False,
                'txcdrlol_hostlane7': False,
                'txcdrlol_hostlane8': False,
                'rxlos': False,
                'rxcdrlol': False,
                'config_state_hostlane1': 'ConfigSuccess',
                'config_state_hostlane2': 'ConfigSuccess',
                'config_state_hostlane3': 'ConfigSuccess',
                'config_state_hostlane4': 'ConfigSuccess',
                'config_state_hostlane5': 'ConfigSuccess',
                'config_state_hostlane6': 'ConfigSuccess',
                'config_state_hostlane7': 'ConfigSuccess',
                'config_state_hostlane8': 'ConfigSuccess',
                'dpinit_pending_hostlane1': False,
                'dpinit_pending_hostlane2': False,
                'dpinit_pending_hostlane3': False,
                'dpinit_pending_hostlane4': False,
                'dpinit_pending_hostlane5': False,
                'dpinit_pending_hostlane6': False,
                'dpinit_pending_hostlane7': False,
                'dpinit_pending_hostlane8': False,
                'tuning_in_progress': False,
                'wavelength_unlock_status': False,
                'target_output_power_oor': False,
                'fine_tuning_oor': False,
                'tuning_not_accepted': False,
                'invalid_channel_num': False,
                'tuning_complete': True,
                'temphighalarm_flag': False, 'templowalarm_flag': False, 
                'temphighwarning_flag': False, 'templowwarning_flag': False,
                'vcchighalarm_flag': False, 'vcclowalarm_flag': False, 
                'vcchighwarning_flag': False, 'vcclowwarning_flag': False,
                'lasertemphighalarm_flag': False, 'lasertemplowalarm_flag': False, 
                'lasertemphighwarning_flag': False, 'lasertemplowwarning_flag': False,
                'txpowerhighalarm_flag': False, 'txpowerlowalarm_flag': False, 
                'txpowerhighwarning_flag': False, 'txpowerlowwarning_flag': False,
                'rxpowerhighalarm_flag': False, 'rxpowerlowalarm_flag': False, 
                'rxpowerhighwarning_flag': False, 'rxpowerlowwarning_flag': False,
                'txbiashighalarm_flag': False, 'txbiaslowalarm_flag': False, 
                'txbiashighwarning_flag': False, 'txbiaslowwarning_flag': False,
                'prefecberhighalarm_flag': False, 'prefecberlowalarm_flag': False, 
                'prefecberhighwarning_flag': False, 'prefecberlowwarning_flag': False,
                'postfecberhighalarm_flag': False, 'postfecberlowalarm_flag': False, 
                'postfecberhighwarning_flag': False, 'postfecberlowwarning_flag': False,
                'biasxihighalarm_flag': False, 'biasxilowalarm_flag': False, 
                'biasxihighwarning_flag': False, 'biasxilowwarning_flag': False,
                'biasxqhighalarm_flag': False, 'biasxqlowalarm_flag': False, 
                'biasxqhighwarning_flag': False, 'biasxqlowwarning_flag': False,
                'biasxphighalarm_flag': False, 'biasxplowalarm_flag': False, 
                'biasxphighwarning_flag': False, 'biasxplowwarning_flag': False,
                'biasyihighalarm_flag': False, 'biasyilowalarm_flag': False, 
                'biasyihighwarning_flag': False, 'biasyilowwarning_flag': False,
                'biasyqhighalarm_flag': False, 'biasyqlowalarm_flag': False, 
                'biasyqhighwarning_flag': False, 'biasyqlowwarning_flag': False,
                'biasyphighalarm_flag': False, 'biasyplowalarm_flag': False, 
                'biasyphighwarning_flag': False, 'biasyplowwarning_flag': False,
                'cdshorthighalarm_flag': False, 'cdshortlowalarm_flag': False, 
                'cdshorthighwarning_flag': False, 'cdshortlowwarning_flag': False,
                'cdlonghighalarm_flag': False, 'cdlonglowalarm_flag': False, 
                'cdlonghighwarning_flag': False, 'cdlonglowwarning_flag': False,
                'dgdhighalarm_flag': False, 'dgdlowalarm_flag': False, 
                'dgdhighwarning_flag': False, 'dgdlowwarning_flag': False,
                'sopmdhighalarm_flag': False, 'sopmdlowalarm_flag': False, 
                'sopmdhighwarning_flag': False, 'sopmdlowwarning_flag': False,
                'pdlhighalarm_flag': False, 'pdllowalarm_flag': False, 
                'pdlhighwarning_flag': False, 'pdllowwarning_flag': False,
                'osnrhighalarm_flag': False, 'osnrlowalarm_flag': False, 
                'osnrhighwarning_flag': False, 'osnrlowwarning_flag': False,
                'esnrhighalarm_flag': False, 'esnrlowalarm_flag': False, 
                'esnrhighwarning_flag': False, 'esnrlowwarning_flag': False,
                'cfohighalarm_flag': False, 'cfolowalarm_flag': False, 
                'cfohighwarning_flag': False, 'cfolowwarning_flag': False,
                'txcurrpowerhighalarm_flag': False, 'txcurrpowerlowalarm_flag': False, 
                'txcurrpowerhighwarning_flag': False, 'txcurrpowerlowwarning_flag': False,
                'rxtotpowerhighalarm_flag': False, 'rxtotpowerlowalarm_flag': False, 
                'rxtotpowerhighwarning_flag': False, 'rxtotpowerlowwarning_flag': False,
                'rxsigpowerhighalarm_flag': False, 'rxsigpowerlowalarm_flag': False, 
                'rxsigpowerhighwarning_flag': False, 'rxsigpowerlowwarning_flag': False,
                
            }
        )
    ])
    def test_get_transceiver_status(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.get_module_state = MagicMock()
        api.get_module_state.return_value = mock_response[0]
        api.get_module_fault_cause = MagicMock()
        api.get_module_fault_cause.return_value = mock_response[1]
        api.get_module_firmware_fault_state_changed = MagicMock()
        api.get_module_firmware_fault_state_changed.return_value = mock_response[2]
        api.get_datapath_state = MagicMock()
        api.get_datapath_state.return_value = mock_response[3]
        api.get_tx_output_status = MagicMock()
        api.get_tx_output_status.return_value = mock_response[4]
        api.get_rx_output_status = MagicMock()
        api.get_rx_output_status.return_value = mock_response[5]
        api.get_tx_fault = MagicMock()
        api.get_tx_fault.return_value = mock_response[6]
        api.get_tx_los = MagicMock()
        api.get_tx_los.return_value = mock_response[7]
        api.get_tx_cdr_lol = MagicMock()
        api.get_tx_cdr_lol.return_value = mock_response[8]
        api.get_rx_los = MagicMock()
        api.get_rx_los.return_value = mock_response[9]
        api.get_rx_cdr_lol = MagicMock()
        api.get_rx_cdr_lol.return_value = mock_response[10]
        api.get_config_datapath_hostlane_status = MagicMock()
        api.get_config_datapath_hostlane_status.return_value = mock_response[11]
        api.get_dpinit_pending = MagicMock()
        api.get_dpinit_pending.return_value = mock_response[12]
        api.get_tuning_in_progress = MagicMock()
        api.get_tuning_in_progress.return_value = mock_response[13]
        api.get_wavelength_unlocked = MagicMock()
        api.get_wavelength_unlocked.return_value = mock_response[14]
        api.get_laser_tuning_summary = MagicMock()
        api.get_laser_tuning_summary.return_value = mock_response[15]
        api.get_module_level_flag = MagicMock()
        api.get_module_level_flag.return_value = mock_response[16]
        api.get_aux_mon_type = MagicMock()
        api.get_aux_mon_type.return_value = mock_response[17]
        api.get_tx_power_flag = MagicMock()
        api.get_tx_power_flag.return_value = mock_response[18]
        api.get_rx_power_flag = MagicMock()
        api.get_rx_power_flag.return_value = mock_response[19]
        api.get_tx_bias_flag = MagicMock()
        api.get_tx_bias_flag.return_value = mock_response[20]
        api.get_VDM = MagicMock()
        api.get_VDM.return_value = mock_response[21]
        result = api.get_transceiver_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            {
                'preFEC_BER_avg': 0.001, 'preFEC_BER_min': 0.0008, 'preFEC_BER_max': 0.0012,
                'preFEC_uncorr_frame_ratio_avg': 0, 'preFEC_uncorr_frame_ratio_min': 0, 'preFEC_uncorr_frame_ratio_max': 0,
                'rx_cd_avg': 1400, 'rx_cd_min': 1300, 'rx_cd_max': 1500,
                'rx_dgd_avg': 7.0, 'rx_dgd_min': 5.5, 'rx_dgd_max': 9.2,
                'rx_sopmd_avg': 40, 'rx_sopmd_min': 20, 'rx_sopmd_max': 60,
                'rx_pdl_avg': 1.0, 'rx_pdl_min': 0.8, 'rx_pdl_max': 1.2,
                'rx_osnr_avg': 28, 'rx_osnr_min': 26, 'rx_osnr_max': 30,
                'rx_esnr_avg': 17, 'rx_esnr_min': 15, 'rx_esnr_max': 18,
                'rx_cfo_avg': 200, 'rx_cfo_min': 150, 'rx_cfo_max': 250,
                'tx_power_avg': -10, 'tx_power_min': -9.5, 'tx_power_max': -10.5,
                'rx_power_avg': -8, 'rx_power_min': -7, 'rx_power_max': -9,
                'rx_sigpwr_avg': -8, 'rx_sigpwr_min': -7, 'rx_sigpwr_max': -9,
                'rx_soproc_avg': 5, 'rx_soproc_min': 3, 'rx_soproc_max': 8,
            },
            {
                'prefec_ber_avg': 0.001, 'prefec_ber_min': 0.0008, 'prefec_ber_max': 0.0012,
                'uncorr_frames_avg': 0, 'uncorr_frames_min': 0, 'uncorr_frames_max': 0,
                'cd_avg': 1400, 'cd_min': 1300, 'cd_max': 1500,
                'dgd_avg': 7.0, 'dgd_min': 5.5, 'dgd_max': 9.2,
                'sopmd_avg': 40, 'sopmd_min': 20, 'sopmd_max': 60,
                'pdl_avg': 1.0, 'pdl_min': 0.8, 'pdl_max': 1.2,
                'osnr_avg': 28, 'osnr_min': 26, 'osnr_max': 30,
                'esnr_avg': 17, 'esnr_min': 15, 'esnr_max': 18,
                'cfo_avg': 200, 'cfo_min': 150, 'cfo_max': 250,
                'tx_power_avg': -10, 'tx_power_min': -9.5, 'tx_power_max': -10.5,
                'rx_tot_power_avg': -8, 'rx_tot_power_min': -7, 'rx_tot_power_max': -9,
                'rx_sig_power_avg': -8, 'rx_sig_power_min': -7, 'rx_sig_power_max': -9,
                'soproc_avg': 5, 'soproc_min': 3, 'soproc_max': 8,
            }
        )
    ])
    def test_get_transceiver_PM(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.get_PM = MagicMock()
        api.get_PM.return_value = mock_response
        result = api.get_transceiver_PM()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                False,
                False,
                [False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False]
            ],
            {
                'media_output_loopback': False,
                'media_input_loopback': False,
                'host_output_loopback_lane1': False,
                'host_output_loopback_lane2': False,
                'host_output_loopback_lane3': False,
                'host_output_loopback_lane4': False,
                'host_output_loopback_lane5': False,
                'host_output_loopback_lane6': False,
                'host_output_loopback_lane7': False,
                'host_output_loopback_lane8': False,
                'host_input_loopback_lane1': False,
                'host_input_loopback_lane2': False,
                'host_input_loopback_lane3': False,
                'host_input_loopback_lane4': False,
                'host_input_loopback_lane5': False,
                'host_input_loopback_lane6': False,
                'host_input_loopback_lane7': False,
                'host_input_loopback_lane8': False
            }
        )
    ])
    def test_get_transceiver_loopback(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.get_media_output_loopback = MagicMock()
        api.get_media_output_loopback.return_value = mock_response[0]
        api.get_media_input_loopback = MagicMock()
        api.get_media_input_loopback.return_value = mock_response[1]
        api.get_host_output_loopback = MagicMock()
        api.get_host_output_loopback.return_value = mock_response[2]
        api.get_host_input_loopback = MagicMock()
        api.get_host_input_loopback.return_value = mock_response[3]
        result = api.get_transceiver_loopback()
        assert result == expected
