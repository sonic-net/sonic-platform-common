from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.sff8024 import Sff8024
from sonic_platform_base.sonic_xcvr.codes.public.cmis_code import CmisCode

class TestCmis(object):

    def mock_cmis_api(self):
        codes = CmisCode
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
        (
            'QSFP-DD Double Density 8X Pluggable Transceiver',
            'QSFP-DD Double Density 8X Pluggable Transceiver'
        )
    ])
    def test_get_module_type(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_module_type()
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
            ("Single Mode Fiber (SMF)", "400ZR", "400ZR"),
            ("Multimode Fiber (MMF)", "100GE BiDi", "100GE BiDi"),
            ("Passive Copper Cable", "Copper cable", "Copper cable"),
            ("Active Cable Assembly", "Active Loopback module", "Active Loopback module"),
            ("BASE-T", "1000BASE-T (Clause 40)", "1000BASE-T (Clause 40)"),
            ("ABCD", "ABCD", "Unknown media interface")
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
        (-10, -10)
    ])
    def test_get_tx_config_power(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_tx_config_power()
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
        (
            [0,1,0],
            [11520, 20480, -2560, 19200, 0],
            {'monitor value': 45, 'high alarm': 80, 'low alarm': -10, 'high warn': 75, 'low warn': 0}
        ),
        (
            [0,0,0],
            [11520, 20480, -2560, 19200, 0],
            {'monitor value': 45, 'high alarm': 80, 'low alarm': -10, 'high warn': 75, 'low warn': 0}
        ),
        (
            [0,1,1],
            [11520, 20480, -2560, 19200, 0],
            None
        ),
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
        (
            [0,1,0],
            [32767, 65534, 0, 49150.5, 0],
            {'monitor value': 1, 'high alarm': 2, 'low alarm': 0, 'high warn': 1.5, 'low warn': 0}
        ),
        (
            [1,0,0],
            [32767, 65534, 0, 49150.5, 0],
            {'monitor value': 1, 'high alarm': 2, 'low alarm': 0, 'high warn': 1.5, 'low warn': 0}
        ),
        (
            [0,0,0],
            [32767, 65534, 0, 49150.5, 0],
            None
        ),
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
        ([False, 1.0], 100, 100.0),
        ([True, 1.0], 32668, -100.0),
    ])
    def test_get_custom_field(self, input_param, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_custom_field(*input_param)
        assert result == expected

    def test_get_vdm_api(self):
        api = self.mock_cmis_api()
        api.vdm = api.get_vdm_api()


    @pytest.mark.parametrize("mock_response, expected",[
        (
            {'Pre-FEC BER Average Media Input': {1: [0.001, 0.0125, 0, 0.01, 0, False, False, False, False]}},
            {'Pre-FEC BER Average Media Input': {1: [0.001, 0.0125, 0, 0.01, 0, False, False, False, False]}}
        )
    ])
    def test_get_vdm(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.vdm = MagicMock()
        api.vdm.get_vdm_allpage = MagicMock()
        api.vdm.get_vdm_allpage.return_value = mock_response
        result = api.get_vdm()
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
        (1, (False, False, True))
    ])
    def test_get_module_firmware_fault_state_changed(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.return_value = mock_response
        result = api.get_module_firmware_fault_state_changed()
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
        ([-20, 0], (-20,0))
    ])
    def test_get_supported_power_config(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response
        result = api.get_supported_power_config()
        assert result == expected

    @pytest.mark.parametrize("input_param",[
        (True), (False)
    ])
    def test_reset_module(self, input_param):
        api = self.mock_cmis_api()
        api.reset_module(input_param)

    @pytest.mark.parametrize("input_param",[
        (True), (False)
    ])
    def test_set_low_power(self, input_param):
        api = self.mock_cmis_api()
        api.set_low_power(input_param)

    @pytest.mark.parametrize("input_param, mock_response",[
        (-10, (-14, -9)),
        (-8, (-12, -8)),
    ])
    def test_set_tx_power(self, input_param, mock_response):
        api = self.mock_cmis_api()
        api.get_supported_power_config = MagicMock()
        api.get_supported_power_config.return_value = mock_response
        api.set_tx_power(input_param)

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

    @pytest.mark.parametrize("input_param, mock_response",[
        ('none', {
            'host_side_input_loopback_supported': True,
            'host_side_output_loopback_supported': True,
            'media_side_input_loopback_supported': True,
            'media_side_output_loopback_supported': True
        }),
        ('host-side-input', {
            'host_side_input_loopback_supported': True,
            'host_side_output_loopback_supported': True,
            'media_side_input_loopback_supported': True,
            'media_side_output_loopback_supported': True
        }),
        ('host-side-output', {
            'host_side_input_loopback_supported': True,
            'host_side_output_loopback_supported': True,
            'media_side_input_loopback_supported': True,
            'media_side_output_loopback_supported': True
        }),
        ('media-side-input', {
            'host_side_input_loopback_supported': True,
            'host_side_output_loopback_supported': True,
            'media_side_input_loopback_supported': True,
            'media_side_output_loopback_supported': True
        }),
        ('media-side-output', {
            'host_side_input_loopback_supported': True,
            'host_side_output_loopback_supported': True,
            'media_side_input_loopback_supported': True,
            'media_side_output_loopback_supported': True
        }),
    ])
    def test_set_loopback_mode(self, input_param, mock_response):
        api = self.mock_cmis_api()
        api.get_loopback_capability = MagicMock()
        api.get_loopback_capability.return_value = mock_response
        api.set_loopback_mode(input_param)

    def test_get_cdb_api(self):
        api = self.mock_cmis_api()
        api.cdb = api.get_cdb_api()

    @pytest.mark.parametrize("input_param, mock_response1, mock_response2, expected", [
        (
            False,
            [0x77, 0xff],
            [18, 35, (0, 7, 112, 255, 255, 16, 0, 0, 19, 136, 0, 100, 3, 232, 19, 136, 58, 152)],
            (112, 2048, False, True, 2048)
        ),
        (
            True,
            [0x77, 0xff],
            [18, 35, (0, 7, 112, 255, 255, 1, 0, 0, 19, 136, 0, 100, 3, 232, 19, 136, 58, 152)],
            (112, 2048, True, True, 2048)
        ),
    ])
    def test_get_module_fw_upgrade_feature(self, input_param, mock_response1, mock_response2, expected):
        api = self.mock_cmis_api()
        api.xcvr_eeprom.read = MagicMock()
        api.xcvr_eeprom.read.side_effect = mock_response1
        api.cdb = MagicMock()
        api.cdb.cmd0041h = MagicMock()
        api.cdb.cmd0041h.return_value = mock_response2
        api.cdb.cdb_chkcode = MagicMock()
        api.cdb.cdb_chkcode.return_value = mock_response2[1]
        result = api.get_module_fw_upgrade_feature(input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            [110, 26, (3, 3, 0, 0, 0, 1, 1, 4, 3, 0, 0, 100, 3, 232, 19, 136, 58, 152, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 4, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)],
            ('0.0.1', 1, 1, 0, '0.0.0', 0, 0, 0)
        ),
        (
            [110, 26, (48, 3, 0, 0, 0, 1, 1, 4, 3, 0, 0, 100, 3, 232, 19, 136, 58, 152, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 4, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)],
            ('0.0.1', 0, 0, 0, '0.0.0', 1, 1, 0)
        ),
    ])
    def test_get_module_fw_info(self, mock_response, expected):
        api = self.mock_cmis_api()
        api.cdb = MagicMock()
        api.cdb.cmd0100h = MagicMock()
        api.cdb.cmd0100h.return_value = mock_response
        api.cdb.cdb_chkcode = MagicMock()
        api.cdb.cdb_chkcode.return_value = mock_response[1]
        result = api.get_module_fw_info()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response", [
        (1, 1),
        (1, 64)
    ])
    def test_module_fw_run(self, input_param, mock_response):
        api = self.mock_cmis_api()
        api.cdb = MagicMock()
        api.cdb.cmd0109h = MagicMock()
        api.cdb.cmd0109h.return_value = mock_response
        api.module_fw_run(input_param)

    @pytest.mark.parametrize("mock_response", [
        (1), (64)
    ])
    def test_module_fw_commit(self, mock_response):
        api = self.mock_cmis_api()
        api.cdb = MagicMock()
        api.cdb.cmd010Ah = MagicMock()
        api.cdb.cmd010Ah.return_value = mock_response
        api.module_fw_commit()
    
    # @pytest.mark.parametrize("input_param", [
    #     (112, 2048, True, True, 2048, 'abc'),
    #     (112, 2048, False, True, 2048, 'abc')
    # ])
    # def test_module_FW_download(self, input_param):
    #     api = self.mock_cmis_api()
    #     api.cdb = MagicMock()
    #     api.module_FW_download(*input_param)


    @pytest.mark.parametrize("input_param, mock_response", [
        (
            'abc',
            (112, 2048, True, True, 2048)
        )
    ])
    def test_module_fw_upgrade(self, input_param, mock_response):
        api = self.mock_cmis_api()
        api.cdb = MagicMock()
        api.cdb.get_module_fw_upgrade_feature = MagicMock()
        api.cdb.get_module_fw_upgrade_feature.return_value = mock_response
        api.cdb.module_fw_upgrade(input_param)
    
    @pytest.mark.parametrize("mock_response", [
        (
            ('0.0.0', 1, 1, 0, '0.0.1', 0, 0, 0),
            ('0.0.0', 1, 1, 0, '0.0.1', 0, 0, 1),
        )
    ])
    def test_module_fw_switch(self, mock_response):
        api = self.mock_cmis_api()
        api.cdb = MagicMock()
        api.cdb.get_module_fw_info = MagicMock()
        api.cdb.get_module_fw_info.return_value = mock_response
        api.cdb.module_fw_switch()


