from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.fields.consts import LENGTH_ASSEMBLY_FIELD, LEN_MULT_FIELD

class TestCmis(object):
    codes = CmisCodes
    mem_map = CmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = CmisApi(eeprom)

    @pytest.mark.parametrize("mock_response, expected", [
        ("1234567890", "1234567890"),
        ("ABCD", "ABCD")
    ])
    def test_get_model(self, mock_response, expected):
        """
        Verify all api access valid fields
        """
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_model()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("0.0", "0.0"),
        ("1.2", "1.2")
    ])
    def test_get_vendor_rev(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_vendor_rev()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("100000000", "100000000")
    ])
    def test_get_serial(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_serial()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            'QSFP-DD Double Density 8X Pluggable Transceiver',
            'QSFP-DD Double Density 8X Pluggable Transceiver'
        )
    ])
    def test_get_module_type(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_module_type()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("LC", "LC")
    ])
    def test_get_connector_type(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_connector_type()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0, 1], '0.1')
    ])
    def test_get_module_hardware_revision(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_module_hardware_revision()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([5,0], '5.0')
    ])
    def test_get_cmis_rev(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_cmis_rev()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("ModuleReady", "ModuleReady")
    ])
    def test_get_module_state(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_module_state()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("No Fault detected", "No Fault detected")
    ])
    def test_get_module_fault_cause(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_module_fault_cause()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0, 1], '0.1')
    ])
    def test_get_module_active_firmware(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_module_active_firmware()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0, 1], '0.1')
    ])
    def test_get_module_inactive_firmware(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_module_inactive_firmware()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, 55.0], 55.0),
        ([False, 55.0], 'N/A'),
        ([True, None], None),
    ])
    def test_get_module_temperature(self, mock_response, expected):
        self.api.get_temperature_support = MagicMock()
        self.api.get_temperature_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_module_temperature()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, 3.0], 3.0),
        ([False, 3.0], 'N/A'),
        ([True, None], None),
    ])
    def test_get_voltage(self, mock_response, expected):
        self.api.get_voltage_support = MagicMock()
        self.api.get_voltage_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_voltage()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (False, False)
    ])
    def test_is_flat_memory(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.is_flat_memory()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (False, True)
    ])
    def test_get_temperature_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response
        result = self.api.get_temperature_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (False, True)
    ])
    def test_get_voltage_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response
        result = self.api.get_voltage_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([False, True], True)
    ])
    def test_get_rx_los_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_rx_los_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([False, True], True)
    ])
    def test_get_tx_cdr_lol_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_cdr_lol_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, {'TxCDRLOL1': 0}], [False]),
        ([False, {'TxCDRLOL1': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, None], None),
        ([True, None], None)
    ])
    def test_get_tx_cdr_lol(self, mock_response, expected):
        self.api.get_tx_cdr_lol_support = MagicMock()
        self.api.get_tx_cdr_lol_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_cdr_lol()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, {'RxLOS1': 0}], [False]),
        ([False, {'RxLOS1': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, None], None),
        ([True, None], None)
    ])
    def test_get_rx_los(self, mock_response, expected):
        self.api.get_rx_los_support = MagicMock()
        self.api.get_rx_los_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_rx_los()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([False, True], True)
    ])
    def test_get_rx_cdr_lol_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_rx_cdr_lol_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, {'RxCDRLOL1': 0}], [False]),
        ([False, {'RxCDRLOL1': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, None], None),
        ([True, None], None)
    ])
    def test_get_rx_cdr_lol(self, mock_response, expected):
        self.api.get_rx_cdr_lol_support = MagicMock()
        self.api.get_rx_cdr_lol_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_rx_cdr_lol()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([{'TxPowerHighAlarmFlag1':0}, {'TxPowerLowAlarmFlag1':0}, {'TxPowerHighWarnFlag1':0}, {'TxPowerLowWarnFlag1':0}], 
         {
            'tx_power_high_alarm':{
                'TxPowerHighAlarmFlag1': False
            },
            'tx_power_low_alarm':{
                'TxPowerLowAlarmFlag1': False
            },
            'tx_power_high_warn':{
                'TxPowerHighWarnFlag1': False,
            },
            'tx_power_low_warn':{
                'TxPowerLowWarnFlag1': False
            }
         }),
         ([None, None, None, None], None)
    ])
    def test_get_tx_power_flag(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_tx_power_flag()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([{'TxBiasHighAlarmFlag1':0}, {'TxBiasLowAlarmFlag1':0}, {'TxBiasHighWarnFlag1':0}, {'TxBiasLowWarnFlag1':0}], 
         {
            'tx_bias_high_alarm':{
                'TxBiasHighAlarmFlag1': False
            },
            'tx_bias_low_alarm':{
                'TxBiasLowAlarmFlag1': False
            },
            'tx_bias_high_warn':{
                'TxBiasHighWarnFlag1': False,
            },
            'tx_bias_low_warn':{
                'TxBiasLowWarnFlag1': False
            }
         }),
         ([None, None, None, None], None)
    ])
    def test_get_tx_bias_flag(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_tx_bias_flag()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([{'RxPowerHighAlarmFlag1':0}, {'RxPowerLowAlarmFlag1':0}, {'RxPowerHighWarnFlag1':0}, {'RxPowerLowWarnFlag1':0}], 
         {
            'rx_power_high_alarm':{
                'RxPowerHighAlarmFlag1': False
            },
            'rx_power_low_alarm':{
                'RxPowerLowAlarmFlag1': False
            },
            'rx_power_high_warn':{
                'RxPowerHighWarnFlag1': False,
            },
            'rx_power_low_warn':{
                'RxPowerLowWarnFlag1': False
            }
         }),
         ([None, None, None, None], None)
    ])
    def test_get_rx_power_flag(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_rx_power_flag()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ({'TxOutputStatus1': 1}, {'TxOutputStatus1': True}),
        (None, None),
    ])
    def test_get_tx_output_status(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_tx_output_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ({'RxOutputStatus1': 1}, {'RxOutputStatus1': True}),
        (None, None),
    ])
    def test_get_rx_output_status(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_rx_output_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([False, True], True)
    ])
    def test_get_tx_bias_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_bias_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, 2, {'TxBias1': 2}], {'TxBias1': 8}),
        ([True, 3, {'TxBias1': 2}], {'TxBias1': 2}),
        ([False, 0, {'TxBias1': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, 0, None], None)
    ])
    def test_get_tx_bias(self, mock_response, expected):
        self.api.get_tx_bias_support = MagicMock()
        self.api.get_tx_bias_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response[1:]
        result = self.api.get_tx_bias()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([False, True], True)
    ])
    def test_get_tx_power_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_power_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, {'TxPower1': 0}], {'TxPower1': 0}),
        ([False, {'TxPower1': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, None], None)
    ])
    def test_get_tx_power(self, mock_response, expected):
        self.api.get_tx_power_support = MagicMock()
        self.api.get_tx_power_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_power()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([False, True], True)
    ])
    def test_get_rx_power_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_rx_power_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, {'RxPower1': 0}], {'RxPower1': 0}),
        ([False, {'RxPower1': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, None], None)
    ])
    def test_get_rx_power(self, mock_response, expected):
        self.api.get_rx_power_support = MagicMock()
        self.api.get_rx_power_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_rx_power()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([False, True], True)
    ])
    def test_get_tx_fault_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_fault_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, {'TxFault1': 0}], [False]),
        ([False, {'TxFault1': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, None], None),
        ([True, None], None)
    ])
    def test_get_tx_fault(self, mock_response, expected):
        self.api.get_tx_fault_support = MagicMock()
        self.api.get_tx_fault_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_fault()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([False, True], True)
    ])
    def test_get_tx_los_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_los_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, {'TxLOS1': 0}], [False]),
        ([False, {'TxLOS1': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, None], None),
        ([True, None], None)
    ])
    def test_get_tx_los(self, mock_response, expected):
        self.api.get_tx_los_support = MagicMock()
        self.api.get_tx_los_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_los()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([False, True], True)
    ])
    def test_get_tx_disable_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_disable_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, 0x00], [False, False, False, False, False, False, False, False]),
        ([False, 0x00], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, None], None),
        ([True, None], None)
    ])
    def test_get_tx_disable(self, mock_response, expected):
        self.api.get_tx_disable_support = MagicMock()
        self.api.get_tx_disable_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_disable()
        assert result == expected

    @pytest.mark.parametrize("input_param",[
        (True), (False)
    ])
    def test_tx_disable(self,input_param):
        self.api.tx_disable(input_param)

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, 0x00], 0),
        ([False, 0x00], 'N/A'),
        ([None, None], None)
    ])
    def test_get_tx_disable_channel(self, mock_response, expected):
        self.api.get_tx_disable_support = MagicMock()
        self.api.get_tx_disable_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_disable_channel()
        assert result == expected

    @pytest.mark.parametrize("mock_response, input_param",[
        (0, (0xff, True)),
        (0, (0, True)),
        (None, (0, False))
    ])
    def test_tx_disable_channel(self, mock_response, input_param):
        self.api.get_tx_disable_channel = MagicMock()
        self.api.get_tx_disable_channel.return_value = mock_response
        self.api.tx_disable_channel(*input_param)

    def test_get_power_override(self):
        self.api.get_power_override()

    def test_set_power_override(self):
        self.api.set_power_override(None, None)
    @pytest.mark.parametrize("mock_response, expected", [
        (False, True)
    ])
    def test_get_transceiver_thresholds_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response
        result = self.api.get_transceiver_thresholds_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (None, False),
        ('Power Class 1', False),
        ('Power Class 8', True),
    ])
    def test_get_lpmode_support(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_lpmode_support()
        assert result == expected

    def test_get_power_override_support(self, ):
        result = self.api.get_power_override_support()
        assert result == False

    @pytest.mark.parametrize("mock_response, expected", [
        ("Single Mode Fiber (SMF)", "Single Mode Fiber (SMF)")
    ])
    def test_get_module_media_type(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_module_media_type()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ("400GAUI-8 C2M (Annex 120E)", "400GAUI-8 C2M (Annex 120E)")
    ])
    def test_get_host_electrical_interface(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_host_electrical_interface()
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
        self.api.get_module_media_type = MagicMock()
        self.api.get_module_media_type.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response2
        result = self.api.get_module_media_interface()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ('Copper cable', False),
        ('400ZR', True),
    ])
    def test_is_coherent_module(self, mock_response, expected):
        self.api.get_module_media_interface = MagicMock()
        self.api.get_module_media_interface.return_value = mock_response
        result = self.api.is_coherent_module()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (8, 8)
    ])
    def test_get_host_lane_count(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_host_lane_count()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_get_media_lane_count(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_media_lane_count()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ('C-band tunable laser', 'C-band tunable laser')
    ])
    def test_get_media_interface_technology(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_media_interface_technology()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_get_host_lane_assignment_option(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_host_lane_assignment_option()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_get_media_lane_assignment_option(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_media_lane_assignment_option()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ({'ActiveAppSelLane1': 1},
         {'ActiveAppSelLane1': 1})
    ])
    def test_get_active_apsel_hostlane(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_active_apsel_hostlane()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (-10, -10)
    ])
    def test_get_tx_config_power(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_tx_config_power()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, True),
        (None, None),
    ])
    def test_get_media_output_loopback(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_media_output_loopback()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, True),
        (None, None),
    ])
    def test_get_media_input_loopback(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_media_input_loopback()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x00, [False, False, False, False, False, False, False, False]),
        (None, None),
    ])
    def test_get_host_output_loopback(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_host_output_loopback()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0x00, [False, False, False, False, False, False, False, False]),
        (None, None),
    ])
    def test_get_host_input_loopback(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_host_input_loopback()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0xc2, (0,1,0)),
        (None, None)
    ])
    def test_get_aux_mon_type(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_aux_mon_type()
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
        self.api.get_aux_mon_type = MagicMock()
        self.api.get_aux_mon_type.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response2
        result = self.api.get_laser_temperature()
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
        self.api.get_aux_mon_type = MagicMock()
        self.api.get_aux_mon_type.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response2
        result = self.api.get_laser_TEC_current()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ({'ConfigStatusLane1': 'ConfigSuccess'}, 
         {'ConfigStatusLane1': 'ConfigSuccess'})
    ])
    def test_get_config_datapath_hostlane_status(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_config_datapath_hostlane_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ({'DP1State': 'DataPathActivated'}, 
         {'DP1State': 'DataPathActivated'})
    ])
    def test_get_datapath_state(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_datapath_state()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ({'DPInitPending1': 0}, {'DPInitPending1': False}),
        (None, None)
    ])
    def test_get_dpinit_pending(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_dpinit_pending()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([-20, 0], (-20,0))
    ])
    def test_get_supported_power_config(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_supported_power_config()
        assert result == expected

    def test_reset_module(self):
        self.api.reset_module(True)

    def test_set_low_power(self, ):
        self.api.set_low_power(True)

    @pytest.mark.parametrize("mock_response, expected", [
        (   

            [False, 127],
            {
                'simultaneous_host_media_loopback_supported': True,
                'per_lane_media_loopback_supported': True,
                'per_lane_host_loopback_supported': True,
                'host_side_input_loopback_supported': True,
                'host_side_output_loopback_supported': True,
                'media_side_input_loopback_supported': True,
                'media_side_output_loopback_supported': True
            }
        ),
        ([True, 0], None),
        ([False, None], None)
    ])
    def test_get_loopback_capability(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_loopback_capability()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response",[
        ('none',{
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
        (
            'none', None
        )
    ])
    def test_set_loopback_mode(self, input_param, mock_response):
        self.api.get_loopback_capability = MagicMock()
        self.api.get_loopback_capability.return_value = mock_response
        self.api.set_loopback_mode(input_param)

    def test_get_cdb_api(self):
        self.api.get_cdb_api()

    def test_get_vdm_api(self):
        self.api.get_vdm_api()

    @pytest.mark.parametrize("mock_response, expected",[
        (   
            [
                True,
                {'Pre-FEC BER Average Media Input': {1: [0.001, 0.0125, 0, 0.01, 0, False, False, False, False]}},
            ],            
            {'Pre-FEC BER Average Media Input': {1: [0.001, 0.0125, 0, 0.01, 0, False, False, False, False]}}
        ),
        (
            [False, {}], None
        )
    ])
    def test_get_vdm(self, mock_response, expected):
        self.api.get_vdm_support = MagicMock()
        self.api.get_vdm_support.return_value = mock_response[0]
        self.api.vdm = MagicMock()
        self.api.vdm.get_vdm_allpage = MagicMock()
        self.api.vdm.get_vdm_allpage.return_value = mock_response[1]
        result = self.api.get_vdm()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, (False, False, True))
    ])
    def test_get_module_firmware_fault_state_changed(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_module_firmware_fault_state_changed()
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
        }),
        ([None, None, None], None)
    ])
    def test_get_module_level_flag(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_module_level_flag()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response1, mock_response2, expected", [
        (
            False,
            [0x77, 0xff],
            [18, 35, (0, 7, 112, 255, 255, 16, 0, 0, 19, 136, 0, 100, 3, 232, 19, 136, 58, 152)],
            {'status':True, 'info': 'Auto page support: True\nMax write length: 2048\nStart payload size 112\nMax block size 2048\nWrite to EPL supported\nAbort CMD102h supported True\nGet module FW upgrade features time: 0.00 s\n', 'result': (112, 2048, False, True, 2048)}
        ),
        (
            False,
            [0x77, 0xff],
            [18, 35, (0, 7, 112, 255, 255, 1, 0, 0, 19, 136, 0, 100, 3, 232, 19, 136, 58, 152)],
            {'status':True, 'info': 'Auto page support: True\nMax write length: 2048\nStart payload size 112\nMax block size 2048\nWrite to LPL supported\nAbort CMD102h supported True\nGet module FW upgrade features time: 0.00 s\n', 'result': (112, 2048, True, True, 2048)}
        ),
    ])
    def test_get_module_fw_upgrade_feature(self, input_param, mock_response1, mock_response2, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response1
        self.api.cdb = MagicMock()
        self.api.cdb.get_fw_management_features = MagicMock()
        self.api.cdb.get_fw_management_features.return_value = mock_response2
        self.api.cdb.cdb_chkcode = MagicMock()
        self.api.cdb.cdb_chkcode.return_value = mock_response2[1]
        result = self.api.get_module_fw_upgrade_feature(input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            [110, 26, (3, 3, 0, 0, 0, 1, 1, 4, 3, 0, 0, 100, 3, 232, 19, 136, 58, 152, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 4, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)],
            {'status':True, 'info': 'Get module FW info\nImage A Version: 0.0.1\nImage B Version: 0.0.0\nRunning Image: A; Committed Image: A\nGet module FW info time: 0.00 s\n', 'result': ('0.0.1', 1, 1, 0, '0.0.0', 0, 0, 0)}
        ),
        (
            [110, 26, (48, 3, 0, 0, 0, 1, 1, 4, 3, 0, 0, 100, 3, 232, 19, 136, 58, 152, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 4, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 1, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)],
            {'status':True, 'info': 'Get module FW info\nImage A Version: 0.0.1\nImage B Version: 0.0.0\nRunning Image: B; Committed Image: B\nGet module FW info time: 0.00 s\n', 'result': ('0.0.1', 0, 0, 0, '0.0.0', 1, 1, 0)}
        ),
    ])
    def test_get_module_fw_info(self, mock_response, expected):
        self.api.cdb = MagicMock()
        self.api.cdb.get_fw_info = MagicMock()
        self.api.cdb.get_fw_info.return_value = mock_response
        self.api.cdb.cdb_chkcode = MagicMock()
        self.api.cdb.cdb_chkcode.return_value = mock_response[1]
        result = self.api.get_module_fw_info()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        (1, 1,  (True, 'Module FW run: Success\nModule FW run time: 0.00 s\n')),
        (1, 64,  (False, 'Module FW run: Fail\nFW_run_status 64\n')),
    ])
    def test_module_fw_run(self, input_param, mock_response, expected):
        self.api.cdb = MagicMock()
        self.api.cdb.run_fw_image = MagicMock()
        self.api.cdb.run_fw_image.return_value = mock_response
        result = self.api.module_fw_run(input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, (True, 'Module FW commit: Success\nModule FW commit time: 0.00 s\n')),
        (64, (False, 'Module FW commit: Fail\nFW_commit_status 64\n')),
    ])
    def test_module_fw_commit(self, mock_response, expected):
        self.api.cdb = MagicMock()
        self.api.cdb.commit_fw_image = MagicMock()
        self.api.cdb.commit_fw_image.return_value = mock_response
        result = self.api.module_fw_commit()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        (
            'abc',
            [{'status': True, 'info': '', 'result': ('a', 1, 1, 0, 'b', 0, 0, 0)}, {'status': True, 'info': '', 'result': (112, 2048, True, True, 2048)}, (True, ''), (True, '')],
            (True, '')
        ),
        (
            'abc',
            [{'status': False, 'info': '', 'result': None}, {'status': True, 'info': '', 'result': (112, 2048, True, True, 2048)}, (True, ''), (True, '')],
            (False, '')
        ),
        (
            'abc',
            [{'status': True, 'info': '', 'result': ('a', 1, 1, 0, 'b', 0, 0, 0)}, {'status': False, 'info': '', 'result': None}, (True, ''), (True, '')],
            (False, '')
        ),
        (
            'abc',
            [{'status': True, 'info': '', 'result': ('a', 1, 1, 0, 'b', 0, 0, 0)}, {'status': True, 'info': '', 'result': (112, 2048, True, True, 2048)}, (False, ''), (True, '')],
            (False, '')
        ),
    ])
    def test_module_fw_upgrade(self, input_param, mock_response, expected):
        self.api.get_module_fw_info = MagicMock()
        self.api.get_module_fw_info.return_value = mock_response[0]
        self.api.get_module_fw_upgrade_feature = MagicMock()
        self.api.get_module_fw_upgrade_feature.return_value = mock_response[1]
        self.api.module_fw_download = MagicMock()
        self.api.module_fw_download.return_value = mock_response[2]
        self.api.module_fw_switch = MagicMock()
        self.api.module_fw_switch.return_value = mock_response[3]        
        result = self.api.module_fw_upgrade(input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        ([None, None, None, None, None, None, None, None, None, None, None, None, None, None], None),
        (
            [
                {
                    'Extended Identifier': {'Power Class': 'Power Class 8', 'MaxPower': 20.0},
                    'Identifier': 'QSFP-DD Double Density 8X Pluggable Transceiver',
                    'Identifier Abbreviation': 'QSFP-DD',
                    'ModuleHardwareMajorRevision': 0,
                    'ModuleHardwareMinorRevision': 0,
                    'VendorSN': '00000000',
                    'VendorName': 'VENDOR_NAME',
                    'VendorPN': 'ABCD',
                    'Connector': 'LC',
                    'Length Cable Assembly': 0.0,
                    'ModuleMediaType': 'Single Mode Fiber (SMF)',
                    'VendorDate': '21010100',
                    'VendorOUI': 'xx-xx-xx'
                }, 
                '400GAUI-8 C2M (Annex 120E)',
                '400ZR, DWDM, amplified',
                8, 1, 1, 1,
                {'ActiveAppSelLane1': 1, 'ActiveAppSelLane2': 1, 'ActiveAppSelLane3': 1, 'ActiveAppSelLane4': 1,
                 'ActiveAppSelLane5': 1, 'ActiveAppSelLane6': 1, 'ActiveAppSelLane7': 1, 'ActiveAppSelLane8': 1},
                '1550 nm DFB',
                '0.0',
                '5.0',
                '0.1',
                '0.0',
                'Single Mode Fiber (SMF)'
            ],
            {   'type': 'QSFP-DD Double Density 8X Pluggable Transceiver',
                'type_abbrv_name': 'QSFP-DD',
                'model': 'ABCD',
                'encoding': 'N/A',
                'ext_identifier': 'Power Class 8 (20.0W Max)',
                'ext_rateselect_compliance': 'N/A',
                'cable_type': 'Length Cable Assembly(m)',
                'cable_length': 0.0,
                'nominal_bit_rate': 0,
                'specification_compliance': 'Single Mode Fiber (SMF)',
                'application_advertisement': 'N/A',
                'active_firmware': '0.1',
                'media_lane_count': 1,
                'inactive_firmware': '0.0',
                'vendor_rev': '0.0',
                'host_electrical_interface': '400GAUI-8 C2M (Annex 120E)',
                'vendor_oui': 'xx-xx-xx',
                'manufacturer': 'VENDOR_NAME',
                'media_interface_technology': '1550 nm DFB',
                'media_interface_code': '400ZR, DWDM, amplified',
                'serial': '00000000',
                'host_lane_count': 8,
                'active_apsel_hostlane1': 1,
                'active_apsel_hostlane3': 1,
                'active_apsel_hostlane2': 1,
                'active_apsel_hostlane5': 1,
                'active_apsel_hostlane4': 1,
                'active_apsel_hostlane7': 1,
                'active_apsel_hostlane6': 1,
                'active_apsel_hostlane8': 1,
                'hardware_rev': '0.0',
                'cmis_rev': '5.0',
                'media_lane_assignment_option': 1,
                'connector': 'LC',
                'host_lane_assignment_option': 1,
                'vendor_date': '21010100'
            }
        )
    ])
    def test_get_transceiver_info(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[0]
        self.api.get_host_electrical_interface = MagicMock()
        self.api.get_host_electrical_interface.return_value = mock_response[1]
        self.api.get_module_media_interface = MagicMock()
        self.api.get_module_media_interface.return_value = mock_response[2]
        self.api.get_host_lane_count = MagicMock()
        self.api.get_host_lane_count.return_value = mock_response[3]
        self.api.get_media_lane_count = MagicMock()
        self.api.get_media_lane_count.return_value = mock_response[4]
        self.api.get_host_lane_assignment_option = MagicMock()
        self.api.get_host_lane_assignment_option.return_value = mock_response[5]
        self.api.get_media_lane_assignment_option = MagicMock()
        self.api.get_media_lane_assignment_option.return_value = mock_response[6]
        self.api.get_active_apsel_hostlane = MagicMock()
        self.api.get_active_apsel_hostlane.return_value = mock_response[7]
        self.api.get_media_interface_technology = MagicMock()
        self.api.get_media_interface_technology.return_value = mock_response[8]
        self.api.get_vendor_rev = MagicMock()
        self.api.get_vendor_rev.return_value = mock_response[9]
        self.api.get_cmis_rev = MagicMock()
        self.api.get_cmis_rev.return_value = mock_response[10]
        self.api.get_module_active_firmware = MagicMock()
        self.api.get_module_active_firmware.return_value = mock_response[11]
        self.api.get_module_inactive_firmware = MagicMock()
        self.api.get_module_inactive_firmware.return_value = mock_response[12]
        self.api.get_module_media_type = MagicMock()
        self.api.get_module_media_type.return_value = mock_response[13]
        result = self.api.get_transceiver_info()
        assert result == expected


    @pytest.mark.parametrize("mock_response, expected",[
        (
            [   
                [False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False],
                0,
                50,
                3.3,
                {'LaserBiasTx1Field': 70, 'LaserBiasTx2Field': 70,
                 'LaserBiasTx3Field': 70, 'LaserBiasTx4Field': 70,
                 'LaserBiasTx5Field': 70, 'LaserBiasTx6Field': 70,
                 'LaserBiasTx7Field': 70, 'LaserBiasTx8Field': 70},
                {'OpticalPowerRx1Field': 0.1, 'OpticalPowerRx2Field': 0.1,
                 'OpticalPowerRx3Field': 0.1, 'OpticalPowerRx4Field': 0.1,
                 'OpticalPowerRx5Field': 0.1, 'OpticalPowerRx6Field': 0.1,
                 'OpticalPowerRx7Field': 0.1, 'OpticalPowerRx8Field': 0.1,},
                {'OpticalPowerTx1Field': 0.1, 'OpticalPowerTx2Field': 0.1,
                 'OpticalPowerTx3Field': 0.1, 'OpticalPowerTx4Field': 0.1,
                 'OpticalPowerTx5Field': 0.1, 'OpticalPowerTx6Field': 0.1,
                 'OpticalPowerTx7Field': 0.1, 'OpticalPowerTx8Field': 0.1,},
                True, True, True, True, True, True,
                {'monitor value': 40},
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                }
            ],
            {
                'temperature': 50,
                'voltage': 3.3,
                'tx1power': -10.0, 'tx2power': -10.0, 'tx3power': -10.0, 'tx4power': -10.0,
                'tx5power': -10.0, 'tx6power': -10.0, 'tx7power': -10.0, 'tx8power': -10.0, 
                'rx1power': -10.0, 'rx2power': -10.0, 'rx3power': -10.0, 'rx4power': -10.0,
                'rx5power': -10.0, 'rx6power': -10.0, 'rx7power': -10.0, 'rx8power': -10.0, 
                'tx1bias': 70, 'tx2bias': 70, 'tx3bias': 70, 'tx4bias': 70,
                'tx5bias': 70, 'tx6bias': 70, 'tx7bias': 70, 'tx8bias': 70,
                'rx_los': False,
                'tx_fault': False,
                'tx1disable': False, 'tx2disable': False, 'tx3disable': False, 'tx4disable': False,
                'tx5disable': False, 'tx6disable': False, 'tx7disable': False, 'tx8disable': False,
                'tx_disabled_channel': 0,
                'laser_temperature': 40,
                'prefec_ber': 0.001,
                'postfec_ber': 0,
            }
        ),
        (   
            [
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                'N/A',
                50, 3.3, 
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                False, False, False, False, False, False,
                {'monitor value': 40},
                None,
            ],
            {
                'temperature': 50,
                'voltage': 3.3,
                'tx1power': 'N/A', 'tx2power': 'N/A', 'tx3power': 'N/A', 'tx4power': 'N/A',
                'tx5power': 'N/A', 'tx6power': 'N/A', 'tx7power': 'N/A', 'tx8power': 'N/A', 
                'rx1power': 'N/A', 'rx2power': 'N/A', 'rx3power': 'N/A', 'rx4power': 'N/A',
                'rx5power': 'N/A', 'rx6power': 'N/A', 'rx7power': 'N/A', 'rx8power': 'N/A', 
                'tx1bias': 'N/A', 'tx2bias': 'N/A', 'tx3bias': 'N/A', 'tx4bias': 'N/A',
                'tx5bias': 'N/A', 'tx6bias': 'N/A', 'tx7bias': 'N/A', 'tx8bias': 'N/A',
                'rx_los': 'N/A',
                'tx_fault': 'N/A',
                'tx1disable': 'N/A', 'tx2disable': 'N/A', 'tx3disable': 'N/A', 'tx4disable': 'N/A',
                'tx5disable': 'N/A', 'tx6disable': 'N/A', 'tx7disable': 'N/A', 'tx8disable': 'N/A',
                'tx_disabled_channel': 'N/A',
                'laser_temperature': 40
            }


        )
    ])
    def test_get_transceiver_bulk_status(self, mock_response, expected):
        self.api.get_rx_los = MagicMock()
        self.api.get_rx_los.return_value = mock_response[0]
        self.api.get_tx_fault = MagicMock()
        self.api.get_tx_fault.return_value = mock_response[1]
        self.api.get_tx_disable = MagicMock()
        self.api.get_tx_disable.return_value = mock_response[2]
        self.api.get_tx_disable_channel = MagicMock()
        self.api.get_tx_disable_channel.return_value = mock_response[3]
        self.api.get_module_temperature = MagicMock()
        self.api.get_module_temperature.return_value = mock_response[4]
        self.api.get_voltage = MagicMock()
        self.api.get_voltage.return_value = mock_response[5]
        self.api.get_tx_bias = MagicMock()
        self.api.get_tx_bias.return_value = mock_response[6]
        self.api.get_rx_power = MagicMock()
        self.api.get_rx_power.return_value = mock_response[7]
        self.api.get_tx_power = MagicMock()
        self.api.get_tx_power.return_value = mock_response[8]
        self.api.get_rx_los_support = MagicMock()
        self.api.get_rx_los_support.return_value = mock_response[9]
        self.api.get_tx_fault_support = MagicMock()
        self.api.get_tx_fault_support.return_value = mock_response[10]
        self.api.get_tx_disable_support = MagicMock()
        self.api.get_tx_disable_support.return_value = mock_response[11]
        self.api.get_tx_bias_support = MagicMock()
        self.api.get_tx_bias_support.return_value = mock_response[12]
        self.api.get_tx_power_support = MagicMock()
        self.api.get_tx_power_support.return_value = mock_response[13]
        self.api.get_rx_power_support = MagicMock()
        self.api.get_rx_power_support.return_value = mock_response[14]
        self.api.get_laser_temperature = MagicMock()
        self.api.get_laser_temperature.return_value = mock_response[15]
        self.api.get_vdm = MagicMock()
        self.api.get_vdm.return_value = mock_response[16]
        result = self.api.get_transceiver_bulk_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [   
                True,
                {
                    'TempHighAlarm': 80, 'TempLowAlarm': 0, 'TempHighWarning': 75, 'TempLowWarning': 10,
                    'VoltageHighAlarm': 3.5, 'VoltageLowAlarm': 3.1, 'VoltageHighWarning': 3.45, 'VoltageLowWarning': 3.15,
                    'RxPowerHighAlarm': 1.0, 'RxPowerLowAlarm': 0.01, 'RxPowerHighWarning': 1.0, 'RxPowerLowWarning': 0.01,
                    'TxPowerHighAlarm': 1.0, 'TxPowerLowAlarm': 0.01, 'TxPowerHighWarning': 1.0, 'TxPowerLowWarning': 0.01,
                    'TxHighAlarm': 90, 'TxLowAlarm': 10, 'TxHighWarning': 80, 'TxLowWarning': 20,
                },
                1,
                {'high alarm': 80, 'low alarm': 10, 'high warn': 75, 'low warn': 20},
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                }
            ],
            {
                'temphighalarm': 80, 'templowalarm': 0, 'temphighwarning': 75, 'templowwarning': 10,
                'vcchighalarm': 3.5, 'vcclowalarm': 3.1, 'vcchighwarning': 3.45, 'vcclowwarning': 3.15,
                'txpowerhighalarm': 0.0, 'txpowerlowalarm': -20.0, 'txpowerhighwarning': 0.0, 'txpowerlowwarning': -20.0,
                'rxpowerhighalarm': 0.0, 'rxpowerlowalarm': -20.0, 'rxpowerhighwarning': 0.0, 'rxpowerlowwarning': -20.0,
                'txbiashighalarm': 180, 'txbiaslowalarm': 20, 'txbiashighwarning': 160, 'txbiaslowwarning': 40,
                'lasertemphighalarm': 80, 'lasertemplowalarm': 10, 'lasertemphighwarning': 75, 'lasertemplowwarning': 20,
                'prefecberhighalarm': 0.0125, 'prefecberlowalarm': 0, 'prefecberhighwarning': 0.01, 'prefecberlowwarning': 0,
                'postfecberhighalarm': 1, 'postfecberlowalarm': 0, 'postfecberhighwarning': 1, 'postfecberlowwarning': 0,
            }
        ),
        ([None, None, None, None, None], None),
        (
            [False, None, None, None, None],             
            {
                'temphighalarm': 'N/A', 'templowalarm': 'N/A', 'temphighwarning': 'N/A', 'templowwarning': 'N/A',
                'vcchighalarm': 'N/A', 'vcclowalarm': 'N/A', 'vcchighwarning': 'N/A', 'vcclowwarning': 'N/A',
                'txpowerhighalarm': 'N/A', 'txpowerlowalarm': 'N/A', 'txpowerhighwarning': 'N/A', 'txpowerlowwarning': 'N/A',
                'rxpowerhighalarm': 'N/A', 'rxpowerlowalarm': 'N/A', 'rxpowerhighwarning': 'N/A', 'rxpowerlowwarning': 'N/A',
                'txbiashighalarm': 'N/A', 'txbiaslowalarm': 'N/A', 'txbiashighwarning': 'N/A', 'txbiaslowwarning': 'N/A',
            }
        ),
        ([True, None, None, None, None], None)
    ])
    def test_get_transceiver_threshold_info(self, mock_response, expected):
        self.api.get_transceiver_thresholds_support = MagicMock()
        self.api.get_transceiver_thresholds_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response[1:3]
        self.api.get_laser_temperature = MagicMock()
        self.api.get_laser_temperature.return_value = mock_response[3]
        self.api.get_vdm = MagicMock()
        self.api.get_vdm.return_value = mock_response[4]
        result = self.api.get_transceiver_threshold_info()
        assert result == expected    

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                'ModuleReady', 'No Fault detected', (False, False, True),
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
                (0, 0, 0), False,
                {'DP1State': 'DataPathActivated', 'DP2State': 'DataPathActivated',
                 'DP3State': 'DataPathActivated', 'DP4State': 'DataPathActivated',
                 'DP5State': 'DataPathActivated', 'DP6State': 'DataPathActivated',
                 'DP7State': 'DataPathActivated', 'DP8State': 'DataPathActivated'},
                {'TxOutputStatus1': True},
                {
                    'RxOutputStatus1': True, 'RxOutputStatus2': True,
                    'RxOutputStatus3': True, 'RxOutputStatus4': True,
                    'RxOutputStatus5': True, 'RxOutputStatus6': True,
                    'RxOutputStatus7': True, 'RxOutputStatus8': True
                },
                [False],
                [False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False],
                [False],
                [False],
                {
                    'ConfigStatusLane1': 'ConfigSuccess', 'ConfigStatusLane2': 'ConfigSuccess',
                    'ConfigStatusLane3': 'ConfigSuccess', 'ConfigStatusLane4': 'ConfigSuccess',
                    'ConfigStatusLane5': 'ConfigSuccess', 'ConfigStatusLane6': 'ConfigSuccess', 
                    'ConfigStatusLane7': 'ConfigSuccess', 'ConfigStatusLane8': 'ConfigSuccess'
                },
                {
                    'DPInitPending1': False, 'DPInitPending2': False,
                    'DPInitPending3': False, 'DPInitPending4': False,
                    'DPInitPending5': False, 'DPInitPending6': False, 
                    'DPInitPending7': False, 'DPInitPending8': False
                },

                {
                    'tx_power_high_alarm': {'TxPowerHighAlarmFlag1': False},
                    'tx_power_low_alarm': {'TxPowerLowAlarmFlag1': False},
                    'tx_power_high_warn': {'TxPowerHighWarnFlag1': False},
                    'tx_power_low_warn': {'TxPowerLowWarnFlag1': False},
                },
                {
                    'rx_power_high_alarm': {'RxPowerHighAlarmFlag1': False},
                    'rx_power_low_alarm': {'RxPowerLowAlarmFlag1': False},
                    'rx_power_high_warn': {'RxPowerHighWarnFlag1': False},
                    'rx_power_low_warn': {'RxPowerLowWarnFlag1': False},
                },
                {
                    'tx_bias_high_alarm': {'TxBiasHighAlarmFlag1': False},
                    'tx_bias_low_alarm': {'TxBiasLowAlarmFlag1': False},
                    'tx_bias_high_warn': {'TxBiasHighWarnFlag1': False},
                    'tx_bias_low_warn': {'TxBiasLowWarnFlag1': False},
                },
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                }
            ],
            {
                'module_state': 'ModuleReady',
                'module_fault_cause': 'No Fault detected',
                'datapath_firmware_fault': False,
                'module_firmware_fault': False,
                'module_state_changed': True,
                'DP1State': 'DataPathActivated',
                'DP2State': 'DataPathActivated',
                'DP3State': 'DataPathActivated',
                'DP4State': 'DataPathActivated',
                'DP5State': 'DataPathActivated',
                'DP6State': 'DataPathActivated',
                'DP7State': 'DataPathActivated',
                'DP8State': 'DataPathActivated',
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
            }
        ),
        (
            [
                'ModuleReady', 'No Fault detected', (False, False, True),
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
                (0, 0, 0), True,
                {'DP1State': 'DataPathActivated', 'DP2State': 'DataPathActivated',
                 'DP3State': 'DataPathActivated', 'DP4State': 'DataPathActivated',
                 'DP5State': 'DataPathActivated', 'DP6State': 'DataPathActivated',
                 'DP7State': 'DataPathActivated', 'DP8State': 'DataPathActivated'},
                {'TxOutputStatus1': True},
                {
                    'RxOutputStatus1': True, 'RxOutputStatus2': True,
                    'RxOutputStatus3': True, 'RxOutputStatus4': True,
                    'RxOutputStatus5': True, 'RxOutputStatus6': True,
                    'RxOutputStatus7': True, 'RxOutputStatus8': True
                },
                [False],
                [False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False],
                [False],
                [False],
                {
                    'ConfigStatusLane1': 'ConfigSuccess', 'ConfigStatusLane2': 'ConfigSuccess',
                    'ConfigStatusLane3': 'ConfigSuccess', 'ConfigStatusLane4': 'ConfigSuccess',
                    'ConfigStatusLane5': 'ConfigSuccess', 'ConfigStatusLane6': 'ConfigSuccess', 
                    'ConfigStatusLane7': 'ConfigSuccess', 'ConfigStatusLane8': 'ConfigSuccess'
                },
                {
                    'DPInitPending1': False, 'DPInitPending2': False,
                    'DPInitPending3': False, 'DPInitPending4': False,
                    'DPInitPending5': False, 'DPInitPending6': False, 
                    'DPInitPending7': False, 'DPInitPending8': False
                },

                {
                    'tx_power_high_alarm': {'TxPowerHighAlarmFlag1': False},
                    'tx_power_low_alarm': {'TxPowerLowAlarmFlag1': False},
                    'tx_power_high_warn': {'TxPowerHighWarnFlag1': False},
                    'tx_power_low_warn': {'TxPowerLowWarnFlag1': False},
                },
                {
                    'rx_power_high_alarm': {'RxPowerHighAlarmFlag1': False},
                    'rx_power_low_alarm': {'RxPowerLowAlarmFlag1': False},
                    'rx_power_high_warn': {'RxPowerHighWarnFlag1': False},
                    'rx_power_low_warn': {'RxPowerLowWarnFlag1': False},
                },
                {
                    'tx_bias_high_alarm': {'TxBiasHighAlarmFlag1': False},
                    'tx_bias_low_alarm': {'TxBiasLowAlarmFlag1': False},
                    'tx_bias_high_warn': {'TxBiasHighWarnFlag1': False},
                    'tx_bias_low_warn': {'TxBiasLowWarnFlag1': False},
                },
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                }
            ],
            {
                'module_state': 'ModuleReady',
                'module_fault_cause': 'No Fault detected',
                'datapath_firmware_fault': False,
                'module_firmware_fault': False,
                'module_state_changed': True,
                'temphighalarm_flag': False, 'templowalarm_flag': False, 
                'temphighwarning_flag': False, 'templowwarning_flag': False,
                'vcchighalarm_flag': False, 'vcclowalarm_flag': False, 
                'vcchighwarning_flag': False, 'vcclowwarning_flag': False,
                'lasertemphighalarm_flag': False, 'lasertemplowalarm_flag': False, 
                'lasertemphighwarning_flag': False, 'lasertemplowwarning_flag': False,
            }            
        )
    ])
    def test_get_transceiver_status(self, mock_response, expected):
        self.api.get_module_state = MagicMock()
        self.api.get_module_state.return_value = mock_response[0]
        self.api.get_module_fault_cause = MagicMock()
        self.api.get_module_fault_cause.return_value = mock_response[1]
        self.api.get_module_firmware_fault_state_changed = MagicMock()
        self.api.get_module_firmware_fault_state_changed.return_value = mock_response[2]
        self.api.get_module_level_flag = MagicMock()
        self.api.get_module_level_flag.return_value = mock_response[3]
        self.api.get_aux_mon_type = MagicMock()
        self.api.get_aux_mon_type.return_value = mock_response[4]
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[5]
        self.api.get_datapath_state = MagicMock()
        self.api.get_datapath_state.return_value = mock_response[6]
        self.api.get_tx_output_status = MagicMock()
        self.api.get_tx_output_status.return_value = mock_response[7]
        self.api.get_rx_output_status = MagicMock()
        self.api.get_rx_output_status.return_value = mock_response[8]
        self.api.get_tx_fault = MagicMock()
        self.api.get_tx_fault.return_value = mock_response[9]
        self.api.get_tx_los = MagicMock()
        self.api.get_tx_los.return_value = mock_response[10]
        self.api.get_tx_cdr_lol = MagicMock()
        self.api.get_tx_cdr_lol.return_value = mock_response[11]
        self.api.get_rx_los = MagicMock()
        self.api.get_rx_los.return_value = mock_response[12]
        self.api.get_rx_cdr_lol = MagicMock()
        self.api.get_rx_cdr_lol.return_value = mock_response[13]
        self.api.get_config_datapath_hostlane_status = MagicMock()
        self.api.get_config_datapath_hostlane_status.return_value = mock_response[14]
        self.api.get_dpinit_pending = MagicMock()
        self.api.get_dpinit_pending.return_value = mock_response[15]

        self.api.get_tx_power_flag = MagicMock()
        self.api.get_tx_power_flag.return_value = mock_response[16]
        self.api.get_rx_power_flag = MagicMock()
        self.api.get_rx_power_flag.return_value = mock_response[17]
        self.api.get_tx_bias_flag = MagicMock()
        self.api.get_tx_bias_flag.return_value = mock_response[18]
        self.api.get_vdm = MagicMock()
        self.api.get_vdm.return_value = mock_response[19]
        result = self.api.get_transceiver_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                {
                    'simultaneous_host_media_loopback_supported': True,
                    'per_lane_media_loopback_supported': True,
                    'per_lane_host_loopback_supported': True,
                    'host_side_input_loopback_supported': True,
                    'host_side_output_loopback_supported': True,
                    'media_side_input_loopback_supported': True,
                    'media_side_output_loopback_supported': True
                },
                False,
                False,
                [False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False]
            ],
            {
                'simultaneous_host_media_loopback_supported': True,
                'per_lane_media_loopback_supported': True,
                'per_lane_host_loopback_supported': True,
                'host_side_input_loopback_supported': True,
                'host_side_output_loopback_supported': True,
                'media_side_input_loopback_supported': True,
                'media_side_output_loopback_supported': True,
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
        ),
        (
            [None, None, None, None, None],
            {
                'simultaneous_host_media_loopback_supported': 'N/A',
                'per_lane_media_loopback_supported': 'N/A',
                'per_lane_host_loopback_supported': 'N/A',
                'host_side_input_loopback_supported': 'N/A',
                'host_side_output_loopback_supported': 'N/A',
                'media_side_input_loopback_supported': 'N/A',
                'media_side_output_loopback_supported': 'N/A',
                'media_output_loopback': 'N/A',
                'media_input_loopback': 'N/A',
                'host_output_loopback_lane1': 'N/A',
                'host_output_loopback_lane2': 'N/A',
                'host_output_loopback_lane3': 'N/A',
                'host_output_loopback_lane4': 'N/A',
                'host_output_loopback_lane5': 'N/A',
                'host_output_loopback_lane6': 'N/A',
                'host_output_loopback_lane7': 'N/A',
                'host_output_loopback_lane8': 'N/A',
                'host_input_loopback_lane1': 'N/A',
                'host_input_loopback_lane2': 'N/A',
                'host_input_loopback_lane3': 'N/A',
                'host_input_loopback_lane4': 'N/A',
                'host_input_loopback_lane5': 'N/A',
                'host_input_loopback_lane6': 'N/A',
                'host_input_loopback_lane7': 'N/A',
                'host_input_loopback_lane8': 'N/A'
            }
        ),
        (
            [
                {
                    'simultaneous_host_media_loopback_supported': False,
                    'per_lane_media_loopback_supported': False,
                    'per_lane_host_loopback_supported': False,
                    'host_side_input_loopback_supported': False,
                    'host_side_output_loopback_supported': False,
                    'media_side_input_loopback_supported': False,
                    'media_side_output_loopback_supported': False
                },
                False,
                False,
                [False, False, False, False, False, False, False, False],
                [False, False, False, False, False, False, False, False]
            ],
            {
                'simultaneous_host_media_loopback_supported': False,
                'per_lane_media_loopback_supported': False,
                'per_lane_host_loopback_supported': False,
                'host_side_input_loopback_supported': False,
                'host_side_output_loopback_supported': False,
                'media_side_input_loopback_supported': False,
                'media_side_output_loopback_supported': False,
                'media_output_loopback': 'N/A',
                'media_input_loopback': 'N/A',
                'host_output_loopback_lane1': 'N/A',
                'host_output_loopback_lane2': 'N/A',
                'host_output_loopback_lane3': 'N/A',
                'host_output_loopback_lane4': 'N/A',
                'host_output_loopback_lane5': 'N/A',
                'host_output_loopback_lane6': 'N/A',
                'host_output_loopback_lane7': 'N/A',
                'host_output_loopback_lane8': 'N/A',
                'host_input_loopback_lane1': 'N/A',
                'host_input_loopback_lane2': 'N/A',
                'host_input_loopback_lane3': 'N/A',
                'host_input_loopback_lane4': 'N/A',
                'host_input_loopback_lane5': 'N/A',
                'host_input_loopback_lane6': 'N/A',
                'host_input_loopback_lane7': 'N/A',
                'host_input_loopback_lane8': 'N/A'
            }
        )
    ])
    def test_get_transceiver_loopback(self, mock_response, expected):
        self.api.get_loopback_capability = MagicMock()
        self.api.get_loopback_capability.return_value = mock_response[0]
        self.api.get_media_output_loopback = MagicMock()
        self.api.get_media_output_loopback.return_value = mock_response[1]
        self.api.get_media_input_loopback = MagicMock()
        self.api.get_media_input_loopback.return_value = mock_response[2]
        self.api.get_host_output_loopback = MagicMock()
        self.api.get_host_output_loopback.return_value = mock_response[3]
        self.api.get_host_input_loopback = MagicMock()
        self.api.get_host_input_loopback.return_value = mock_response[4]
        result = self.api.get_transceiver_loopback()
        assert result == expected

    def test_cable_len(self):
        cable_len_field = self.mem_map.get_field(LENGTH_ASSEMBLY_FIELD)
        data = bytearray([0xFF])
        dep = {LEN_MULT_FIELD: 0b11}
        decoded = cable_len_field.decode(data, **dep)
        assert decoded == 6300

