from unittest.mock import patch
from mock import MagicMock
import pytest
import traceback
import random
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi, CMIS_VDM_KEY_TO_DB_PREFIX_KEY_MAP, THRESHOLD_TYPE_STR_MAP
from sonic_platform_base.sonic_xcvr.api.public.cmis import FLAG_TYPE_STR_MAP, CMIS_XCVR_INFO_DEFAULT_DICT
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.codes.public.sff8024 import Sff8024
from sonic_platform_base.sonic_xcvr.fields import consts

class TestCmis(object):
    codes = CmisCodes
    mem_map = CmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    old_read_func = eeprom.read
    api = CmisApi(eeprom)

    def clear_cache(self, method_name=None):
        """
        Clear cached API return values for methods decorated with read_only_cached_api_return.
        If method_name is provided, clear only that cache; otherwise clear all caches.
        """
        if method_name:
            cache_name = f'_{method_name}_cache'
            if hasattr(self.api, cache_name):
                delattr(self.api, cache_name)
        else:
            for attr in list(self.api.__dict__.keys()):
                if attr.startswith('_') and attr.endswith('_cache'):
                    delattr(self.api, attr)

    def setup_method(self, method):
        """Clear cached values before each test case."""
        self.clear_cache()

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

    def test_get_cable_length_type(self):
        assert self.api.get_cable_length_type() == "Length Cable Assembly(m)"

    @pytest.mark.parametrize("mock_response, expected", [
        ("0.0", "0.0"),
        ("1.2", "1.2")
    ])
    def test_get_cable_length(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_cable_length()
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
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = False
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
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = False
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

    def test_is_copper(self):
      with patch.object(self.api, 'xcvr_eeprom') as mock_eeprom:
         mock_eeprom.read = MagicMock()
         mock_eeprom.read.return_value = None
         assert self.api.is_copper() is None
         self.api.get_module_media_type = MagicMock()
         self.api.get_module_media_type.return_value = "passive_copper_media_interface"
         assert self.api.is_copper()
         self.api.get_module_media_type.return_value = "active_cable_media_interface"
         assert not self.api.is_copper()
         self.api.get_module_media_type.return_value = "sm_media_interface"
         assert not self.api.is_copper()

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
        (
            {
                consts.TX_POWER_HIGH_ALARM_FLAG: {'TxPowerHighAlarmFlag1': 0},
                consts.TX_POWER_LOW_ALARM_FLAG: {'TxPowerLowAlarmFlag1': 0},
                consts.TX_POWER_HIGH_WARN_FLAG: {'TxPowerHighWarnFlag1': 0},
                consts.TX_POWER_LOW_WARN_FLAG: {'TxPowerLowWarnFlag1': 0}
            },
            {
                'tx_power_high_alarm': {'TxPowerHighAlarmFlag1': False},
                'tx_power_low_alarm': {'TxPowerLowAlarmFlag1': False},
                'tx_power_high_warn': {'TxPowerHighWarnFlag1': False},
                'tx_power_low_warn': {'TxPowerLowWarnFlag1': False}
            }
        ),
        (None, None)
    ])
    def test_get_tx_power_flag(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_tx_power_flag()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            {
                consts.TX_BIAS_HIGH_ALARM_FLAG: {'TxBiasHighAlarmFlag1': 0},
                consts.TX_BIAS_LOW_ALARM_FLAG: {'TxBiasLowAlarmFlag1': 0},
                consts.TX_BIAS_HIGH_WARN_FLAG: {'TxBiasHighWarnFlag1': 0},
                consts.TX_BIAS_LOW_WARN_FLAG: {'TxBiasLowWarnFlag1': 0}
            },
            {
                'tx_bias_high_alarm': {'TxBiasHighAlarmFlag1': False},
                'tx_bias_low_alarm': {'TxBiasLowAlarmFlag1': False},
                'tx_bias_high_warn': {'TxBiasHighWarnFlag1': False},
                'tx_bias_low_warn': {'TxBiasLowWarnFlag1': False}
            }
        ),
        (None, None)
    ])
    def test_get_tx_bias_flag(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_tx_bias_flag()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            {
                consts.RX_POWER_HIGH_ALARM_FLAG: {'RxPowerHighAlarmFlag1': 0},
                consts.RX_POWER_LOW_ALARM_FLAG: {'RxPowerLowAlarmFlag1': 0},
                consts.RX_POWER_HIGH_WARN_FLAG: {'RxPowerHighWarnFlag1': 0},
                consts.RX_POWER_LOW_WARN_FLAG: {'RxPowerLowWarnFlag1': 0}
            },
            {
                'rx_power_high_alarm': {'RxPowerHighAlarmFlag1': False},
                'rx_power_low_alarm': {'RxPowerLowAlarmFlag1': False},
                'rx_power_high_warn': {'RxPowerHighWarnFlag1': False},
                'rx_power_low_warn': {'RxPowerLowWarnFlag1': False}
            }
        ),
        (None, None)
    ])
    def test_get_rx_power_flag(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
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
        ([True, 2, {'LaserBiasTx1Field': 2, 'LaserBiasTx2Field': 2, 'LaserBiasTx3Field': 2, 'LaserBiasTx4Field': 2, 'LaserBiasTx5Field': 2, 'LaserBiasTx6Field': 2, 'LaserBiasTx7Field': 2, 'LaserBiasTx8Field': 2}],
        [8, 8, 8, 8, 8, 8, 8, 8]),
        ([True, 3, {'LaserBiasTx1Field': 2, 'LaserBiasTx2Field': 2, 'LaserBiasTx3Field': 2, 'LaserBiasTx4Field': 2, 'LaserBiasTx5Field': 2, 'LaserBiasTx6Field': 2, 'LaserBiasTx7Field': 2, 'LaserBiasTx8Field': 2}],
        [2, 2, 2, 2, 2, 2, 2, 2]),
        ([False, 0, {'LaserBiasTx1Field': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([None, 0, None], None)
    ])
    def test_get_tx_bias(self, mock_response, expected):
        self.api.get_tx_bias_support = MagicMock()
        self.api.get_tx_bias_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response[1:]
        result = self.api.get_tx_bias()
        assert result == expected

    def test_get_tx_bias_neg(self):
        self.api.get_tx_bias_support = MagicMock(return_value=True)
        self.api.xcvr_eeprom.read = MagicMock()
        # scale_raw is None, verify no crash
        self.api.xcvr_eeprom.read.return_value = None
        self.api.get_tx_bias()
        # scale_raw is 1, tx_bias is None, verify no crash
        self.api.xcvr_eeprom.read.side_effect = [1, None]
        self.api.get_tx_bias()

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
        (
            [
                True,
                {
                    'OpticalPowerTx1Field': 0, 'OpticalPowerTx2Field': 0,
                    'OpticalPowerTx3Field': 0, 'OpticalPowerTx4Field': 0,
                    'OpticalPowerTx5Field': 0, 'OpticalPowerTx6Field': 0,
                    'OpticalPowerTx7Field': 0, 'OpticalPowerTx8Field': 0
                }
            ],
            [0, 0, 0, 0, 0, 0, 0, 0]
        ),
        ([False, {'OpticalPowerTx1Field': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([True, None], None)
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
        (
            [
                True,
                {
                    'OpticalPowerRx1Field': 0, 'OpticalPowerRx2Field': 0,
                    'OpticalPowerRx3Field': 0, 'OpticalPowerRx4Field': 0,
                    'OpticalPowerRx5Field': 0, 'OpticalPowerRx6Field': 0,
                    'OpticalPowerRx7Field': 0, 'OpticalPowerRx8Field': 0
                }
            ],
            [0, 0, 0, 0, 0, 0, 0, 0]
        ),
        ([False, {'OpticalPowerRx1Field': 0}], ['N/A','N/A','N/A','N/A','N/A','N/A','N/A','N/A']),
        ([True, None], None)
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

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, {'RxLOS1': 0}], [False]),
        ([False, {'RxLOS1': 0}], ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']),
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
    def test_get_rx_disable_support(self, mock_response, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_rx_disable_support()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, 0x00], [False, False, False, False, False, False, False, False]),
        ([False, 0x00], ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']),
        ([None, None], None),
        ([True, None], None)
    ])
    def test_get_rx_disable(self, mock_response, expected):
        self.api.get_rx_disable_support = MagicMock()
        self.api.get_rx_disable_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_rx_disable()
        assert result == expected

    @pytest.mark.parametrize("input_param", [
        (True), (False)
    ])
    def test_rx_disable(self, input_param):
        rc = self.api.rx_disable(input_param)
        assert(rc != None)

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, 0x00], 0),
        ([False, 0x00], 'N/A'),
        ([None, None], None)
    ])
    def test_get_rx_disable_channel(self, mock_response, expected):
        self.api.get_rx_disable_support = MagicMock()
        self.api.get_rx_disable_support.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_rx_disable_channel()
        assert result == expected

    @pytest.mark.parametrize("mock_response, input_param", [
        (0, (0xff, True)),
        (0, (0, True)),
        (0, (0, False)),
        (0, (1, False)),
        (0, (1, True)),
        (None, (0, False))
    ])
    def test_rx_disable_channel(self, mock_response, input_param):
        self.api.get_rx_disable_channel = MagicMock()
        self.api.get_rx_disable_channel.return_value = mock_response
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.write.return_value = mock_response
        rc = self.api.rx_disable_channel(*input_param)
        assert(rc != None)

    @pytest.mark.parametrize("mock_response, expected", [
        (1, ['TuningComplete']),
        (62, ['TargetOutputPowerOOR', 'FineTuningOutOfRange', 'TuningNotAccepted',
              'InvalidChannel', 'WavelengthUnlocked']),
    ])
    def test_get_laser_tuning_summary(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_laser_tuning_summary()
        assert result == expected

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
        ("sm_media_interface", "sm_media_interface")
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
            ("sm_media_interface", "400ZR", "400ZR"),
            ("nm_850_media_interface", "100GE BiDi", "100GE BiDi"),
            ("passive_copper_media_interface", "Copper cable", "Copper cable"),
            ("active_cable_media_interface", "Active Loopback module", "Active Loopback module"),
            ("base_t_media_interface", "1000BASE-T (Clause 40)", "1000BASE-T (Clause 40)"),
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

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (True, '1', 0 ),
        (False, None, 0),
        (False, '500', 5000.0),
        (False, '1000', 10000.0),
        (False, '5000', 5000.0),
        (False, '60000', 60000.0),
    ])
    def test_get_datapath_init_duration(self, mock_response1, mock_response2, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response2
        result = self.api.get_datapath_init_duration()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (True, '10', 0 ),
        (False, None, 0),
        (False, '50', 50.0),
        (False, '6000000', 6000000.0),
    ])
    def test_get_datapath_deinit_duration(self, mock_response1, mock_response2, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response2
        result = self.api.get_datapath_deinit_duration()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (True, '10', 0 ),
        (False, None, 0),
        (False, '8', 8.0),
        (False, '5000000', 5000000.0),
    ])
    def test_get_datapath_tx_turnon_duration(self, mock_response1, mock_response2, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response2
        result = self.api.get_datapath_tx_turnon_duration()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (True, '1', 0 ),
        (False, None, 0),
        (False, '6', 6.0),
        (False, '80000', 80000.0),
    ])
    def test_get_datapath_tx_turnoff_duration(self, mock_response1, mock_response2, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response2
        result = self.api.get_datapath_tx_turnoff_duration()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (True, '10', 0 ),
        (False, None, 0),
        (False, '8', 8.0),
        (False, '5000000', 5000000.0),
    ])
    def test_get_module_pwr_up_duration(self, mock_response1, mock_response2, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response2
        result = self.api.get_module_pwr_up_duration()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (True, '1', 0 ),
        (False, None, 0),
        (False, '6', 6.0),
        (False, '80000', 80000.0),
    ])
    def test_get_module_pwr_down_duration(self, mock_response1, mock_response2, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response2
        result = self.api.get_module_pwr_down_duration()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (8, 8)
    ])
    def test_get_host_lane_count(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_host_lane_count()
        assert result == expected

    @pytest.mark.parametrize("appl, expected", [
        (0, 0),
        (1, 4),
        (2, 1),
        (3, 0)
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_application_advertisement', MagicMock(return_value =
        {
            1: {
                'host_electrical_interface_id': '400GAUI-8 C2M (Annex 120E)',
                'module_media_interface_id': '400GBASE-DR4 (Cl 124)',
                'media_lane_count': 4,
                'host_lane_count': 8,
                'host_lane_assignment_options': 1,
                'media_lane_assignment_options': 1
            },
            2: {
                'host_electrical_interface_id': '100GAUI-2 C2M (Annex 135G)',
                'module_media_interface_id': '100G-LR/100GBASE-LR1 (Cl 140)',
                'media_lane_count': 1,
                'host_lane_count': 2,
                'host_lane_assignment_options': 85,
                'media_lane_assignment_options': 15
            }
        }
    ))
    def test_get_media_lane_count(self, appl, expected):
        result = self.api.get_media_lane_count(appl)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ('C-band tunable laser', 'C-band tunable laser')
    ])
    def test_get_media_interface_technology(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_media_interface_technology()
        assert result == expected

    @pytest.mark.parametrize("appl, expected", [
        (0, 0),
        (1, 1),
        (2, 17),
        (3, 0)
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_application_advertisement', MagicMock(return_value =
        {
            1: {
                'host_electrical_interface_id': '400GAUI-8 C2M (Annex 120E)',
                'module_media_interface_id': '400GBASE-DR4 (Cl 124)',
                'media_lane_count': 4,
                'host_lane_count': 8,
                'host_lane_assignment_options': 1
            },
            2: {
                'host_electrical_interface_id': 'CAUI-4 C2M (Annex 83E)',
                'module_media_interface_id': 'Active Cable assembly with BER < 5x10^-5',
                'media_lane_count': 4,
                'host_lane_count': 4,
                'host_lane_assignment_options': 17
            }
        }
    ))
    def test_get_host_lane_assignment_option(self, appl, expected):
        result = self.api.get_host_lane_assignment_option(appl)
        assert result == expected

    @pytest.mark.parametrize("appl, expected", [
        (0, 0),
        (1, 1),
        (2, 15),
        (3, 0)
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_application_advertisement', MagicMock(return_value =
        {
            1: {
                'host_electrical_interface_id': '400GAUI-8 C2M (Annex 120E)',
                'module_media_interface_id': '400GBASE-DR4 (Cl 124)',
                'media_lane_count': 4,
                'host_lane_count': 8,
                'host_lane_assignment_options': 1,
                'media_lane_assignment_options': 1
            },
            2: {
                'host_electrical_interface_id': '100GAUI-2 C2M (Annex 135G)',
                'module_media_interface_id': '100G-LR/100GBASE-LR1 (Cl 140)',
                'media_lane_count': 1,
                'host_lane_count': 2,
                'host_lane_assignment_options': 85,
                'media_lane_assignment_options': 15
            }
        }
    ))
    def test_get_media_lane_assignment_option(self, appl, expected):
        result = self.api.get_media_lane_assignment_option(appl)
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
            {'monitor value': 'N/A', 'high alarm': 'N/A', 'low alarm': 'N/A', 'high warn': 'N/A', 'low warn': 'N/A'}
        ),
    ])
    def test_get_laser_temperature(self, mock_response1, mock_response2, expected):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = False
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

    def test_reset(self):
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.get_module_state = MagicMock()
        self.api.get_module_state.return_value = 'ModuleReady'
        result = self.api.reset()
        assert result
        assert self.api.xcvr_eeprom.write.call_count == 1
        kall = self.api.xcvr_eeprom.write.call_args
        assert kall is not None
        assert kall[0] == (consts.MODULE_LEVEL_CONTROL, 0x8)

    @pytest.mark.parametrize("lpmode", [
        True, False
    ])
    def test_set_low_power(self, lpmode):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = True
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.write.return_value = True
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = False
        self.api.get_lpmode_support = MagicMock()
        self.api.get_lpmode_support.return_value = True
        self.api.get_module_state = MagicMock()
        self.api.get_lpmode = MagicMock()
        self.api.get_lpmode.return_value = True
        self.api.get_module_state.return_value = "ModuleReady"
        self.api.set_lpmode(lpmode)
        self.api.set_lpmode(lpmode, wait_state_change = False)

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

    @pytest.mark.parametrize("input_param, mock_response, expected",[
        ([0xf, True], None, False),
        ([0xf, True], {
            'host_side_input_loopback_supported': False,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_host_loopback_supported': True,
        }, False),
        ([0xf, True], {
            'host_side_input_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_host_loopback_supported': False,
        }, False),
        ([0xf, True], {
            'host_side_input_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': False,
            'per_lane_host_loopback_supported': True,
        }, False),
        ([0xf, True], {
            'host_side_input_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_host_loopback_supported': True,
        }, True),
        ([0xf, False], {
            'host_side_input_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_host_loopback_supported': True,
        }, True),
    ])
    def test_set_host_input_loopback(self, input_param, mock_response, expected):
        self.api.get_loopback_capability = MagicMock()
        self.api.get_loopback_capability.return_value = mock_response
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = [0x0f,0x0f]
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.write.return_value = True
        result = self.api.set_host_input_loopback(input_param[0], input_param[1])
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected",[
        ([0xf, True], None, False),
        ([0xf, True], {
            'host_side_output_loopback_supported': False,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_host_loopback_supported': True,
        }, False),
        ([0xf, True], {
            'host_side_output_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_host_loopback_supported': False,
        }, False),
        ([0xf, True], {
            'host_side_output_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': False,
            'per_lane_host_loopback_supported': True,
        }, False),
        ([0xf, True], {
            'host_side_output_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_host_loopback_supported': True,
        }, True),
        ([0xf, False], {
            'host_side_output_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_host_loopback_supported': True,
        }, True),
    ])
    def test_set_host_output_loopback(self, input_param, mock_response, expected):
        self.api.get_loopback_capability = MagicMock()
        self.api.get_loopback_capability.return_value = mock_response
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = [0x0f,0x0f]
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.write.return_value = True
        result = self.api.set_host_output_loopback(input_param[0], input_param[1])
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected",[
        ([0xf, True], None, False),
        ([0xf, True], {
            'media_side_input_loopback_supported': False,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_media_loopback_supported': True,
        }, False),
        ([0xf, True], {
            'media_side_input_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_media_loopback_supported': False,
        }, False),
        ([0xf, True], {
            'media_side_input_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': False,
            'per_lane_media_loopback_supported': True,
        }, False),
        ([0xf, True], {
            'media_side_input_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_media_loopback_supported': True,
        }, True),
        ([0xf, False], {
            'media_side_input_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_media_loopback_supported': True,
        }, True),
    ])
    def test_set_media_input_loopback(self, input_param, mock_response, expected):
        self.api.get_loopback_capability = MagicMock()
        self.api.get_loopback_capability.return_value = mock_response
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = [0x0f,0x0f]
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.write.return_value = True
        result = self.api.set_media_input_loopback(input_param[0], input_param[1])
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected",[
        ([0xf, True], None, False),
        ([0xf, True], {
            'media_side_output_loopback_supported': False,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_media_loopback_supported': True,
        }, False),
        ([0xf, True], {
            'media_side_output_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_media_loopback_supported': False,
        }, False),
        ([0xf, True], {
            'media_side_output_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': False,
            'per_lane_media_loopback_supported': True,
        }, False),
        ([0xf, True], {
            'media_side_output_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_media_loopback_supported': True,
        }, True),
        ([0xf, False], {
            'media_side_output_loopback_supported': True,
            'simultaneous_host_media_loopback_supported': True,
            'per_lane_media_loopback_supported': True,
        }, True),
    ])
    def test_set_media_output_loopback(self, input_param, mock_response, expected):
        self.api.get_loopback_capability = MagicMock()
        self.api.get_loopback_capability.return_value = mock_response
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = [0x0f,0x0f]
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.write.return_value = True
        result = self.api.set_media_output_loopback(input_param[0], input_param[1])
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected",[
        (['none', 0], True, True),
        (['host-side-input', 0x0F, True], True, True),
        (['host-side-output', 0x0F, True], True, True),
        (['media-side-input', 0x0F, True], True, True),
        (['media-side-output', 0x0F, True], True, True),
        (['host-side-input', 0xF0, False], True, True),
        (['host-side-output', 0xF0, False], True, True),
        (['media-side-input', 0xF0, False], True, True),
        (['media-side-output', 0xF0, False], True, True),
        (['', 0xF0, False], True, False),

    ])
    def test_set_loopback_mode(self, input_param, mock_response, expected):
        self.api.set_host_input_loopback = MagicMock()
        self.api.set_host_input_loopback.return_value = mock_response
        self.api.set_host_output_loopback = MagicMock()
        self.api.set_host_output_loopback.return_value = mock_response
        self.api.set_media_input_loopback = MagicMock()
        self.api.set_media_input_loopback.return_value = mock_response
        self.api.set_media_output_loopback = MagicMock()
        self.api.set_media_output_loopback.return_value = mock_response
        result = self.api.set_loopback_mode(input_param[0], input_param[1])
        assert result == expected

    def test_is_transceiver_vdm_supported_no_vdm(self):
        self.api.vdm = None
        assert self.api.is_transceiver_vdm_supported() == False

    def test_is_transceiver_vdm_supported_true(self):
        self.api.vdm = MagicMock()
        self.api.xcvr_eeprom.read = MagicMock(return_value=1)
        assert self.api.is_transceiver_vdm_supported() == True

    def test_is_transceiver_vdm_supported_false(self):
        self.api.vdm = MagicMock()
        self.api.xcvr_eeprom.read = MagicMock(return_value=0)
        assert self.api.is_transceiver_vdm_supported() == False

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                True,
                {'Pre-FEC BER Average Media Input': {1: [0.001, 0.0125, 0, 0.01, 0, False, False, False, False]}},
            ],
            {'Pre-FEC BER Average Media Input': {1: [0.001, 0.0125, 0, 0.01, 0, False, False, False, False]}}
        ),
        (
            [False, {}], {}
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

    @pytest.mark.parametrize("mock_response, expected", [
        ({'status':1, 'rpl':(128, 1, [0] * 128)}, {'status': True, 'info': "", 'result': 0}),
        ({'status':1, 'rpl':(None, 1, [0] * 128)}, {'status': False, 'info': "", 'result': 0}),
        ({'status':1, 'rpl':(128, None, [0] * 128)}, {'status': False, 'info': "", 'result': 0}),
        ({'status':1, 'rpl':(128, 0, [0] * 128)}, {'status': False, 'info': "", 'result': None}),
        ({'status':1, 'rpl':(128, 1, [67, 3, 2, 2, 3, 183] + [0] * 104)}, {'status': True, 'info': "", 'result': None}),
        ({'status':1, 'rpl':(128, 1, [52, 3, 2, 2, 3, 183] + [0] * 104)}, {'status': True, 'info': "", 'result': None}),
        ({'status':1, 'rpl':(110, 1, [3, 3, 2, 2, 3, 183] + [0] * 104)}, {'status': True, 'info': "", 'result': None}),
        ({'status':1, 'rpl':(110, 1, [48, 3, 2, 2, 3, 183] + [0] * 104)}, {'status': True, 'info': "", 'result': None}),
        ({'status':0x46, 'rpl':(128, 0, [0] * 128)}, {'status': False, 'info': "", 'result': None}),
    ])
    def test_get_module_fw_info(self, mock_response, expected):
        self.api.cdb = MagicMock()
        self.api.cdb.cdb_chkcode = MagicMock()
        self.api.cdb.cdb_chkcode.return_value = 1
        self.api.get_module_active_firmware = MagicMock()
        self.api.get_module_active_firmware.return_value = "1.0"
        self.api.get_module_inactive_firmware = MagicMock()
        self.api.get_module_inactive_firmware.return_value = "1.1"
        self.api.cdb.get_fw_info = MagicMock()
        self.api.cdb.get_fw_info.return_value = mock_response
        result = self.api.get_module_fw_info()
        if result['status'] == False: # Check 'result' when 'status' == False for distinguishing error type.
            assert result['result'] == expected['result']
        assert result['status'] == expected['status']

    @pytest.mark.parametrize("mock_response, expected", [
        ({'status':0, 'rpl':(18, 0, [0] * 18)}, {'status': False, 'info': "", 'feature': None}),
        ({'status':1, 'rpl':(18, 1, [0] * 18)}, {'status': True,  'info': "", 'feature': (0, 8, False, True, 16)})
    ])
    def test_get_module_fw_mgmt_feature(self, mock_response, expected):
        self.api.cdb = MagicMock()
        self.api.cdb.cdb_chkcode = MagicMock()
        self.api.cdb.cdb_chkcode.return_value = 1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = [1, 1]
        self.api.cdb.get_fw_management_features = MagicMock()
        self.api.cdb.get_fw_management_features.return_value = mock_response
        result = self.api.get_module_fw_mgmt_feature()
        assert result['feature'] == expected['feature']

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        (1, 1,  (True, 'Module FW run: Success\n')),
        (1, 64,  (False, 'Module FW run: Fail\nFW_run_status 64\n')),
    ])
    def test_module_fw_run(self, input_param, mock_response, expected):
        self.api.cdb = MagicMock()
        self.api.cdb.run_fw_image = MagicMock()
        self.api.cdb.run_fw_image.return_value = mock_response
        result = self.api.module_fw_run(input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, (True, 'Module FW commit: Success\n')),
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
            [{'status': True, 'info': '', 'result': ('a', 1, 1, 0, 'b', 0, 0, 0, 'a', 'b')}, {'status': True, 'info': '', 'feature': (112, 2048, True, True, 2048)}, (True, ''), (True, '')],
            (True, '')
        ),
        (
            'abc',
            [{'status': False, 'info': '', 'result': None}, {'status': True, 'info': '', 'feature': (112, 2048, True, True, 2048)}, (True, ''), (True, '')],
            (False, '')
        ),
        (
            'abc',
            [{'status': True, 'info': '', 'result': ('a', 1, 1, 0, 'b', 0, 0, 0, 'a', 'b')}, {'status': False, 'info': '', 'feature': None}, (True, ''), (True, '')],
            (False, '')
        ),
        (
            'abc',
            [{'status': True, 'info': '', 'result': ('a', 1, 1, 0, 'b', 0, 0, 0, 'a', 'b')}, {'status': True, 'info': '', 'feature': (112, 2048, True, True, 2048)}, (False, ''), (True, '')],
            (False, '')
        ),
    ])
    def test_module_fw_upgrade(self, input_param, mock_response, expected):
        self.api.get_module_fw_info = MagicMock()
        self.api.get_module_fw_info.return_value = mock_response[0]
        self.api.get_module_fw_mgmt_feature = MagicMock()
        self.api.get_module_fw_mgmt_feature.return_value = mock_response[1]
        self.api.module_fw_download = MagicMock()
        self.api.module_fw_download.return_value = mock_response[2]
        self.api.module_fw_switch = MagicMock()
        self.api.module_fw_switch.return_value = mock_response[3]
        result = self.api.module_fw_upgrade(input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([0, 0, 0],
        {
            'type': 'QSFP-DD Double Density 8X Pluggable Transceiver',
            'type_abbrv_name': 'QSFP-DD',
            'model': 'ABCD',
            'encoding': 'N/A',
            'ext_identifier': 'Power Class 8 (20.0W Max)',
            'ext_rateselect_compliance': 'N/A',
            'cable_type': 'Length Cable Assembly(m)',
            'cable_length': 0.0,
            'nominal_bit_rate': 'N/A',
            'specification_compliance': 'sm_media_interface',
            'application_advertisement': 'N/A',
            'media_lane_count': 1,
            'vendor_rev': '0.0',
            'host_electrical_interface': '400GAUI-8 C2M (Annex 120E)',
            'vendor_oui': 'xx-xx-xx',
            'manufacturer': 'VENDOR_NAME',
            'media_interface_technology': '1550 nm DFB',
            'media_interface_code': '400ZR, DWDM, amplified',
            'serial': '00000000',
            'host_lane_count': 8,
            'active_apsel_hostlane1': 1,
            'active_apsel_hostlane2': 1,
            'active_apsel_hostlane3': 1,
            'active_apsel_hostlane4': 1,
            'active_apsel_hostlane5': 1,
            'active_apsel_hostlane6': 1,
            'active_apsel_hostlane7': 1,
            'active_apsel_hostlane8': 1,
            'hardware_rev': '0.0',
            'cmis_rev': '5.0',
            'media_lane_assignment_option': 1,
            'connector': 'LC',
            'host_lane_assignment_option': 1,
            'vendor_date': '21010100',
            'vdm_supported': True,
        })
    ])
    def test_get_transceiver_info(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        def mock_read(field):
            if field == consts.APPLS_ADVT_FIELD:
                return {
                    1: {
                        'host_electrical_interface_id': '400GAUI-8 C2M (Annex 120E)',
                        'module_media_interface_id': '400GBASE-DR4 (Cl 124)',
                        'media_lane_count': 1,
                        'host_lane_count': 8,
                        'host_lane_assignment_options': 1,
                        'media_lane_assignment_options': 1
                    }
                }
            elif field == consts.MEDIA_TYPE_FIELD:
                return 'sm_media_interface'
            elif field == consts.EXT_IDENTIFIER_FIELD:
                return {'Power Class': 'Power Class 8', 'MaxPower': 20.0}
            elif field == consts.IDENTIFIER_FIELD:
                return 'QSFP-DD Double Density 8X Pluggable Transceiver'
            elif field == consts.IDENTIFIER_ABBRV_FIELD:
                return 'QSFP-DD'
            elif field == consts.VENDOR_SN_FIELD:
                return '00000000'
            elif field == consts.VENDOR_NAME_FIELD:
                return 'VENDOR_NAME'
            elif field == consts.VENDOR_PN_FIELD:
                return 'ABCD'
            elif field == consts.CONNECTOR_FIELD:
                return 'LC'
            elif field == consts.CABLE_LENGTH_FIELD:
                return 0.0
            elif field == consts.VENDOR_DATE_FIELD:
                return '21010100'
            elif field == consts.VENDOR_OUI_FIELD:
                return 'xx-xx-xx'
            return None
        self.api.xcvr_eeprom.read.side_effect = mock_read

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                50,
                3.3,
                [70, 70, 70, 70, 70, 70, 70, 70],
                [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
                [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
                True, True, True, True, True, True,
                {'monitor value': 40}
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
                'laser_temperature': 40
            }
        ),
        (
            [
                50, 3.3,
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                None,
                None,
                False, False, False, False, False, False,
                {'monitor value': 40},
                None,
            ],
            None
        ),
        (
            [
                50, 3.3,
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                ['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A'],
                False, False, False, False, True, True,
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
                'laser_temperature': 40
            }
        )
    ])
    def test_get_transceiver_dom_real_value(self, mock_response, expected):
        self.api.get_module_temperature = MagicMock()
        self.api.get_module_temperature.return_value = mock_response[0]
        self.api.get_voltage = MagicMock()
        self.api.get_voltage.return_value = mock_response[1]
        self.api.get_tx_bias = MagicMock()
        self.api.get_tx_bias.return_value = mock_response[2]
        self.api.get_rx_power = MagicMock()
        self.api.get_rx_power.return_value = mock_response[3]
        self.api.get_tx_power = MagicMock()
        self.api.get_tx_power.return_value = mock_response[4]
        self.api.get_rx_los_support = MagicMock()
        self.api.get_rx_los_support.return_value = mock_response[5]
        self.api.get_tx_fault_support = MagicMock()
        self.api.get_tx_fault_support.return_value = mock_response[6]
        self.api.get_tx_disable_support = MagicMock()
        self.api.get_tx_disable_support.return_value = mock_response[7]
        self.api.get_tx_bias_support = MagicMock()
        self.api.get_tx_bias_support.return_value = mock_response[8]
        self.api.get_tx_power_support = MagicMock()
        self.api.get_tx_power_support.return_value = mock_response[9]
        self.api.get_rx_power_support = MagicMock()
        self.api.get_rx_power_support.return_value = mock_response[10]
        self.api.get_laser_temperature = MagicMock()
        self.api.get_laser_temperature.return_value = mock_response[11]
        result = self.api.get_transceiver_dom_real_value()
        assert result == expected

    @pytest.mark.parametrize(
        "module_flag, tx_power_flag_dict, rx_power_flag_dict, tx_bias_flag_dict, aux_mon_types, expected_result",
        [
            # Test case 1: All flags present
            (
                {
                    'case_temp_flags': {
                        'case_temp_high_alarm_flag': True,
                        'case_temp_low_alarm_flag': False,
                        'case_temp_high_warn_flag': True,
                        'case_temp_low_warn_flag': False
                    },
                    'voltage_flags': {
                        'voltage_high_alarm_flag': True,
                        'voltage_low_alarm_flag': False,
                        'voltage_high_warn_flag': True,
                        'voltage_low_warn_flag': False
                    },
                    'aux2_flags': {
                        'aux2_high_alarm_flag': True,
                        'aux2_low_alarm_flag': False,
                        'aux2_high_warn_flag': True,
                        'aux2_low_warn_flag': False
                    },
                    'aux3_flags': {
                        'aux3_high_alarm_flag': True,
                        'aux3_low_alarm_flag': False,
                        'aux3_high_warn_flag': True,
                        'aux3_low_warn_flag': False
                    }
                },
                {
                    'tx_power_high_alarm': {f'TxPowerHighAlarmFlag{i}': i % 2 == 1 for i in range(1, 9)},
                    'tx_power_low_alarm': {f'TxPowerLowAlarmFlag{i}': i % 2 == 0 for i in range(1, 9)},
                    'tx_power_high_warn': {f'TxPowerHighWarnFlag{i}': i % 2 == 1 for i in range(1, 9)},
                    'tx_power_low_warn': {f'TxPowerLowWarnFlag{i}': i % 2 == 0 for i in range(1, 9)}
                },
                {
                    'rx_power_high_alarm': {f'RxPowerHighAlarmFlag{i}': i % 2 == 1 for i in range(1, 9)},
                    'rx_power_low_alarm': {f'RxPowerLowAlarmFlag{i}': i % 2 == 0 for i in range(1, 9)},
                    'rx_power_high_warn': {f'RxPowerHighWarnFlag{i}': i % 2 == 1 for i in range(1, 9)},
                    'rx_power_low_warn': {f'RxPowerLowWarnFlag{i}': i % 2 == 0 for i in range(1, 9)}
                },
                {
                    'tx_bias_high_alarm': {f'TxBiasHighAlarmFlag{i}': i % 2 == 1 for i in range(1, 9)},
                    'tx_bias_low_alarm': {f'TxBiasLowAlarmFlag{i}': i % 2 == 0 for i in range(1, 9)},
                    'tx_bias_high_warn': {f'TxBiasHighWarnFlag{i}': i % 2 == 1 for i in range(1, 9)},
                    'tx_bias_low_warn': {f'TxBiasLowWarnFlag{i}': i % 2 == 0 for i in range(1, 9)}
                },
                (0, 1, 0),
                {
                    'tempHAlarm': True,
                    'tempLAlarm': False,
                    'tempHWarn': True,
                    'tempLWarn': False,
                    'vccHAlarm': True,
                    'vccLAlarm': False,
                    'vccHWarn': True,
                    'vccLWarn': False,
                    'tx1powerHAlarm': True,
                    'tx1powerLAlarm': False,
                    'tx1powerHWarn': True,
                    'tx1powerLWarn': False,
                    'tx2powerHAlarm': False,
                    'tx2powerLAlarm': True,
                    'tx2powerHWarn': False,
                    'tx2powerLWarn': True,
                    'tx3powerHAlarm': True,
                    'tx3powerLAlarm': False,
                    'tx3powerHWarn': True,
                    'tx3powerLWarn': False,
                    'tx4powerHAlarm': False,
                    'tx4powerLAlarm': True,
                    'tx4powerHWarn': False,
                    'tx4powerLWarn': True,
                    'tx5powerHAlarm': True,
                    'tx5powerLAlarm': False,
                    'tx5powerHWarn': True,
                    'tx5powerLWarn': False,
                    'tx6powerHAlarm': False,
                    'tx6powerLAlarm': True,
                    'tx6powerHWarn': False,
                    'tx6powerLWarn': True,
                    'tx7powerHAlarm': True,
                    'tx7powerLAlarm': False,
                    'tx7powerHWarn': True,
                    'tx7powerLWarn': False,
                    'tx8powerHAlarm': False,
                    'tx8powerLAlarm': True,
                    'tx8powerHWarn': False,
                    'tx8powerLWarn': True,
                    'rx1powerHAlarm': True,
                    'rx1powerLAlarm': False,
                    'rx1powerHWarn': True,
                    'rx1powerLWarn': False,
                    'rx2powerHAlarm': False,
                    'rx2powerLAlarm': True,
                    'rx2powerHWarn': False,
                    'rx2powerLWarn': True,
                    'rx3powerHAlarm': True,
                    'rx3powerLAlarm': False,
                    'rx3powerHWarn': True,
                    'rx3powerLWarn': False,
                    'rx4powerHAlarm': False,
                    'rx4powerLAlarm': True,
                    'rx4powerHWarn': False,
                    'rx4powerLWarn': True,
                    'rx5powerHAlarm': True,
                    'rx5powerLAlarm': False,
                    'rx5powerHWarn': True,
                    'rx5powerLWarn': False,
                    'rx6powerHAlarm': False,
                    'rx6powerLAlarm': True,
                    'rx6powerHWarn': False,
                    'rx6powerLWarn': True,
                    'rx7powerHAlarm': True,
                    'rx7powerLAlarm': False,
                    'rx7powerHWarn': True,
                    'rx7powerLWarn': False,
                    'rx8powerHAlarm': False,
                    'rx8powerLAlarm': True,
                    'rx8powerHWarn': False,
                    'rx8powerLWarn': True,
                    'tx1biasHAlarm': True,
                    'tx1biasLAlarm': False,
                    'tx1biasHWarn': True,
                    'tx1biasLWarn': False,
                    'tx2biasHAlarm': False,
                    'tx2biasLAlarm': True,
                    'tx2biasHWarn': False,
                    'tx2biasLWarn': True,
                    'tx3biasHAlarm': True,
                    'tx3biasLAlarm': False,
                    'tx3biasHWarn': True,
                    'tx3biasLWarn': False,
                    'tx4biasHAlarm': False,
                    'tx4biasLAlarm': True,
                    'tx4biasHWarn': False,
                    'tx4biasLWarn': True,
                    'tx5biasHAlarm': True,
                    'tx5biasLAlarm': False,
                    'tx5biasHWarn': True,
                    'tx5biasLWarn': False,
                    'tx6biasHAlarm': False,
                    'tx6biasLAlarm': True,
                    'tx6biasHWarn': False,
                    'tx6biasLWarn': True,
                    'tx7biasHAlarm': True,
                    'tx7biasLAlarm': False,
                    'tx7biasHWarn': True,
                    'tx7biasLWarn': False,
                    'tx8biasHAlarm': False,
                    'tx8biasLAlarm': True,
                    'tx8biasHWarn': False,
                    'tx8biasLWarn': True,
                    'lasertempHAlarm': True,
                    'lasertempLAlarm': False,
                    'lasertempHWarn': True,
                    'lasertempLWarn': False
                }
            ),
        ]
    )
    def test_get_transceiver_dom_flags(self, module_flag, tx_power_flag_dict, rx_power_flag_dict, tx_bias_flag_dict, aux_mon_types, expected_result):
        self.api.get_module_level_flag = MagicMock(return_value=module_flag)
        self.api.get_tx_power_flag = MagicMock(return_value=tx_power_flag_dict)
        self.api.get_rx_power_flag = MagicMock(return_value=rx_power_flag_dict)
        self.api.get_tx_bias_flag = MagicMock(return_value=tx_bias_flag_dict)
        self.api.get_aux_mon_type = MagicMock(return_value=aux_mon_types)
        self.api.is_flat_memory = MagicMock(return_value=False)

        result = self.api.get_transceiver_dom_flags()
        assert result == expected_result

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
            ],
            {
                'temphighalarm': 80, 'templowalarm': 0, 'temphighwarning': 75, 'templowwarning': 10,
                'vcchighalarm': 3.5, 'vcclowalarm': 3.1, 'vcchighwarning': 3.45, 'vcclowwarning': 3.15,
                'txpowerhighalarm': 0.0, 'txpowerlowalarm': -20.0, 'txpowerhighwarning': 0.0, 'txpowerlowwarning': -20.0,
                'rxpowerhighalarm': 0.0, 'rxpowerlowalarm': -20.0, 'rxpowerhighwarning': 0.0, 'rxpowerlowwarning': -20.0,
                'txbiashighalarm': 180, 'txbiaslowalarm': 20, 'txbiashighwarning': 160, 'txbiaslowwarning': 40,
                'lasertemphighalarm': 80, 'lasertemplowalarm': 10, 'lasertemphighwarning': 75, 'lasertemplowwarning': 20,
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
        result = self.api.get_transceiver_threshold_info()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                'ModuleReady', 'No Fault detected',
                False,
                {'DP1State': 'DataPathActivated', 'DP2State': 'DataPathActivated',
                 'DP3State': 'DataPathActivated', 'DP4State': 'DataPathActivated',
                 'DP5State': 'DataPathActivated', 'DP6State': 'DataPathActivated',
                 'DP7State': 'DataPathActivated', 'DP8State': 'DataPathActivated'},
                {
                    'TxOutputStatus1': True, 'TxOutputStatus2': True,
                    'TxOutputStatus3': True, 'TxOutputStatus4': True,
                    'TxOutputStatus5': True, 'TxOutputStatus6': True,
                    'TxOutputStatus7': True, 'TxOutputStatus8': True
                },
                {
                    'RxOutputStatus1': True, 'RxOutputStatus2': True,
                    'RxOutputStatus3': True, 'RxOutputStatus4': True,
                    'RxOutputStatus5': True, 'RxOutputStatus6': True,
                    'RxOutputStatus7': True, 'RxOutputStatus8': True
                },
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
                0, [False, False, False, False, False, False, False, False],
                [False, True, False, False, False, False, False, False],
            ],
            {
                'module_state': 'ModuleReady',
                'module_fault_cause': 'No Fault detected',
                'DP1State': 'DataPathActivated',
                'DP2State': 'DataPathActivated',
                'DP3State': 'DataPathActivated',
                'DP4State': 'DataPathActivated',
                'DP5State': 'DataPathActivated',
                'DP6State': 'DataPathActivated',
                'DP7State': 'DataPathActivated',
                'DP8State': 'DataPathActivated',
                'tx1OutputStatus': True,
                'tx2OutputStatus': True,
                'tx3OutputStatus': True,
                'tx4OutputStatus': True,
                'tx5OutputStatus': True,
                'tx6OutputStatus': True,
                'tx7OutputStatus': True,
                'tx8OutputStatus': True,
                'rx1OutputStatusHostlane': True,
                'rx2OutputStatusHostlane': True,
                'rx3OutputStatusHostlane': True,
                'rx4OutputStatusHostlane': True,
                'rx5OutputStatusHostlane': True,
                'rx6OutputStatusHostlane': True,
                'rx7OutputStatusHostlane': True,
                'rx8OutputStatusHostlane': True,
                "tx_disabled_channel": 0,
                "tx1disable": False,
                "tx2disable": False,
                "tx3disable": False,
                "tx4disable": False,
                "tx5disable": False,
                "tx6disable": False,
                "tx7disable": False,
                "tx8disable": False,
                'config_state_hostlane1': 'ConfigSuccess',
                'config_state_hostlane2': 'ConfigSuccess',
                'config_state_hostlane3': 'ConfigSuccess',
                'config_state_hostlane4': 'ConfigSuccess',
                'config_state_hostlane5': 'ConfigSuccess',
                'config_state_hostlane6': 'ConfigSuccess',
                'config_state_hostlane7': 'ConfigSuccess',
                'config_state_hostlane8': 'ConfigSuccess',
                'dpdeinit_hostlane1' : False,
                'dpdeinit_hostlane2' : True,
                'dpdeinit_hostlane3' : False,
                'dpdeinit_hostlane4' : False,
                'dpdeinit_hostlane5' : False,
                'dpdeinit_hostlane6' : False,
                'dpdeinit_hostlane7' : False,
                'dpdeinit_hostlane8' : False,
                'dpinit_pending_hostlane1': False,
                'dpinit_pending_hostlane2': False,
                'dpinit_pending_hostlane3': False,
                'dpinit_pending_hostlane4': False,
                'dpinit_pending_hostlane5': False,
                'dpinit_pending_hostlane6': False,
                'dpinit_pending_hostlane7': False,
                'dpinit_pending_hostlane8': False,
            }
        ),
        (
            [
                'ModuleReady', 'No Fault detected',
                True,
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

                None, None, None
            ],
            {
                'module_state': 'ModuleReady',
                'module_fault_cause': 'No Fault detected',
            }
        )
    ])
    def test_get_transceiver_status(self, mock_response, expected):
        self.api.get_module_state = MagicMock()
        self.api.get_module_state.return_value = mock_response[0]
        self.api.get_module_fault_cause = MagicMock()
        self.api.get_module_fault_cause.return_value = mock_response[1]
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = mock_response[2]
        self.api.get_datapath_state = MagicMock()
        self.api.get_datapath_state.return_value = mock_response[3]
        self.api.get_tx_output_status = MagicMock()
        self.api.get_tx_output_status.return_value = mock_response[4]
        self.api.get_rx_output_status = MagicMock()
        self.api.get_rx_output_status.return_value = mock_response[5]
        self.api.get_config_datapath_hostlane_status = MagicMock()
        self.api.get_config_datapath_hostlane_status.return_value = mock_response[6]
        self.api.get_dpinit_pending = MagicMock()
        self.api.get_dpinit_pending.return_value = mock_response[7]

        self.api.get_tx_disable_channel = MagicMock()
        self.api.get_tx_disable_channel.return_value = mock_response[8]
        self.api.get_tx_disable = MagicMock()
        self.api.get_tx_disable.return_value = mock_response[9]
        with patch.object(self.api, 'get_datapath_deinit', return_value=mock_response[10]):
            result = self.api.get_transceiver_status()
            assert result == expected

    @pytest.mark.parametrize(
        "module_faults, tx_fault, tx_los, tx_cdr_lol, tx_eq_fault, rx_los, rx_cdr_lol, expected_result",
        [
            # Test case 1: All flags present for lanes 1 to 8
            (
                (True, False, True),
                [True, False, True, False, True, False, True, False],
                [False, True, False, True, False, True, False, True],
                [True, False, True, False, True, False, True, False],
                [False, True, False, True, False, True, False, True],
                [True, False, True, False, True, False, True, False],
                [False, True, False, True, False, True, False, True],
                {
                    'datapath_firmware_fault': True,
                    'module_firmware_fault': False,
                    'module_state_changed': True,
                    'tx1fault': True,
                    'tx2fault': False,
                    'tx3fault': True,
                    'tx4fault': False,
                    'tx5fault': True,
                    'tx6fault': False,
                    'tx7fault': True,
                    'tx8fault': False,
                    'rx1los': True,
                    'rx2los': False,
                    'rx3los': True,
                    'rx4los': False,
                    'rx5los': True,
                    'rx6los': False,
                    'rx7los': True,
                    'rx8los': False,
                    'tx1los_hostlane': False,
                    'tx2los_hostlane': True,
                    'tx3los_hostlane': False,
                    'tx4los_hostlane': True,
                    'tx5los_hostlane': False,
                    'tx6los_hostlane': True,
                    'tx7los_hostlane': False,
                    'tx8los_hostlane': True,
                    'tx1cdrlol_hostlane': True,
                    'tx2cdrlol_hostlane': False,
                    'tx3cdrlol_hostlane': True,
                    'tx4cdrlol_hostlane': False,
                    'tx5cdrlol_hostlane': True,
                    'tx6cdrlol_hostlane': False,
                    'tx7cdrlol_hostlane': True,
                    'tx8cdrlol_hostlane': False,
                    'tx1_eq_fault': False,
                    'tx2_eq_fault': True,
                    'tx3_eq_fault': False,
                    'tx4_eq_fault': True,
                    'tx5_eq_fault': False,
                    'tx6_eq_fault': True,
                    'tx7_eq_fault': False,
                    'tx8_eq_fault': True,
                    'rx1cdrlol': False,
                    'rx2cdrlol': True,
                    'rx3cdrlol': False,
                    'rx4cdrlol': True,
                    'rx5cdrlol': False,
                    'rx6cdrlol': True,
                    'rx7cdrlol': False,
                    'rx8cdrlol': True
                }
            ),
        ]
    )
    def test_get_transceiver_status_flags(self, module_faults, tx_fault, tx_los, tx_cdr_lol, tx_eq_fault, rx_los, rx_cdr_lol, expected_result):
        self.api.get_module_firmware_fault_state_changed = MagicMock(return_value=module_faults)
        self.api.get_tx_fault = MagicMock(return_value=tx_fault)
        self.api.get_tx_los = MagicMock(return_value=tx_los)
        self.api.get_tx_cdr_lol = MagicMock(return_value=tx_cdr_lol)
        self.api.get_rx_los = MagicMock(return_value=rx_los)
        self.api.get_rx_cdr_lol = MagicMock(return_value=rx_cdr_lol)
        with patch.object(self.api, 'get_tx_adaptive_eq_fail_flag', return_value=tx_eq_fault), \
             patch.object(self.api, 'is_flat_memory', return_value=False):
            result = self.api.get_transceiver_status_flags()
            assert result == expected_result

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

    def generate_vdm_real_value_expected_dict(base_dict):
        default_dict = dict()
        for _, db_prefix_key_map in CMIS_VDM_KEY_TO_DB_PREFIX_KEY_MAP.items():
                default_dict.update({f'{db_prefix_key_map}{i}': 'N/A' for i in range(1, 9)})

        default_dict.update(base_dict)
        return default_dict
    @pytest.mark.parametrize(
        "vdm_raw_dict, expected_result",
        [
            # Test case 1: VDM descriptor partially advertised
            (
                {
                    'Laser Temperature [C]' : {
                        1: [10.0, None, None, None, None, None, None, None, None],
                        2: [20.0, None, None, None, None, None, None, None, None],
                        3: [30.0, None, None, None, None, None, None, None, None],
                        4: [40.0, None, None, None, None, None, None, None, None],
                        5: [50.0, None, None, None, None, None, None, None, None],
                        6: [60.0, None, None, None, None, None, None, None, None],
                        7: [70.0, None, None, None, None, None, None, None, None],
                        8: [80.0, None, None, None, None, None, None, None, None]},
                    'eSNR Media Input [dB]' : {1: [22.94921875, None, None, None, None, None, None, None, None]}
                },
                generate_vdm_real_value_expected_dict(
                    {
                        'laser_temperature_media1': 10.0,
                        'laser_temperature_media2': 20.0,
                        'laser_temperature_media3': 30.0,
                        'laser_temperature_media4': 40.0,
                        'laser_temperature_media5': 50.0,
                        'laser_temperature_media6': 60.0,
                        'laser_temperature_media7': 70.0,
                        'laser_temperature_media8': 80.0,
                        'esnr_media_input1' : 22.94921875,
                    }
                )
            ),
        ]
    )
    def test_get_transceiver_vdm_real_value(self, vdm_raw_dict, expected_result):
        self.api.vdm = MagicMock()
        self.api.vdm.VDM_REAL_VALUE = MagicMock()
        self.api.get_vdm = MagicMock(return_value=vdm_raw_dict)

        result = self.api.get_transceiver_vdm_real_value()
        assert result == expected_result

    def generate_vdm_thrsholds_expected_dict(base_dict):
        default_dict = dict()
        for _, db_prefix_key_map in CMIS_VDM_KEY_TO_DB_PREFIX_KEY_MAP.items():
                for _, thrshold_type_str in THRESHOLD_TYPE_STR_MAP.items():
                    default_dict.update({f'{db_prefix_key_map}_{thrshold_type_str}{i}': 'N/A' for i in range(1, 9)})

        default_dict.update(base_dict)
        return default_dict

    @pytest.mark.parametrize(
        "vdm_raw_dict, expected_result",
        [
            # Test case 1: VDM descriptor partially advertised
            (
                    { #Laser temperature media 1 is halarm
                    'Laser Temperature [C]': {
                        1: [None, 90.0, -5.0, 85.0, 0.0, None, None, None, None],
                        2: [None, 90.0, -5.0, 85.0, 0.0, None, None, None, None],
                        3: [None, 90.0, -5.0, 85.0, 0.0, None, None, None, None],
                        4: [None, 90.0, -5.0, 85.0, 0.0, None, None, None, None],
                        5: [None, 90.0, -5.0, 85.0, 0.0, None, None, None, None],
                        6: [None, 90.0, -5.0, 85.0, 0.0, None, None, None, None],
                        7: [None, 90.0, -5.0, 85.0, 0.0, None, None, None, None],
                        8: [None, 90.0, -5.0, 85.0, 0.0, None, None, None, None],
                    },
                },
                generate_vdm_thrsholds_expected_dict(
                    {
                        **{f'laser_temperature_media_{alarm_type}{lane}': value for lane in range(1, 9) for alarm_type, value in zip(['halarm', 'hwarn', 'lwarn', 'lalarm'], [90.0, 85.0, 0.0, -5.0])}
                    }
                )
            ),
        ]
    )
    def test_get_transceiver_vdm_thresholds(self, vdm_raw_dict, expected_result):
        self.api.vdm = MagicMock()
        self.api.vdm.VDM_THRESHOLD = MagicMock()
        self.api.get_vdm = MagicMock(return_value=vdm_raw_dict)

        result = self.api.get_transceiver_vdm_thresholds()
        assert result == expected_result

    def generate_vdm_flags_expected_dict(base_dict):
        default_dict = dict()
        for _, db_prefix_key_map in CMIS_VDM_KEY_TO_DB_PREFIX_KEY_MAP.items():
                for _, flag_type_str in FLAG_TYPE_STR_MAP.items():
                    default_dict.update({f'{db_prefix_key_map}_{flag_type_str}{i}': 'N/A' for i in range(1, 9) for flag_type in ['halarm', 'hwarn', 'lwarn', 'lalarm']})

        default_dict.update(base_dict)
        return default_dict
    @pytest.mark.parametrize(
        "vdm_raw_dict, expected_result",
        [
            # Test case 1: VDM descriptor partially advertised
            (
                    { #Laser temperature media 1 is halarm
                    'Laser Temperature [C]': {
                        1: [None, None, None, None, None, True, False, False, False],
                        2: [None, None, None, None, None, False, False, False, False],
                        3: [None, None, None, None, None, False, False, False, False],
                        4: [None, None, None, None, None, False, False, False, False],
                        5: [None, None, None, None, None, False, False, False, False],
                        6: [None, None, None, None, None, False, False, False, False],
                        7: [None, None, None, None, None, False, False, False, False],
                        8: [None, None, None, None, None, False, False, False, False],
                    },
                },
                generate_vdm_flags_expected_dict(
                    {
                        **{f'laser_temperature_media_{alarm_type}{lane}': False for lane in range(1, 9) for alarm_type in ['halarm', 'hwarn', 'lwarn', 'lalarm']},
                        'laser_temperature_media_halarm1': True
                    }
                )
            ),
        ]
    )
    def test_get_transceiver_vdm_flags(self, vdm_raw_dict, expected_result):
        self.api.vdm = MagicMock()
        self.api.vdm.VDM_FLAG = MagicMock()
        self.api.get_vdm = MagicMock(return_value=vdm_raw_dict)

        result = self.api.get_transceiver_vdm_flags()
        assert result == expected_result

    def test_cable_len(self):
        cable_len_field = self.mem_map.get_field(consts.LENGTH_ASSEMBLY_FIELD)
        data = bytearray([0xFF])
        dep = {consts.LEN_MULT_FIELD: 0b11}
        decoded = cable_len_field.decode(data, **dep)
        assert decoded == 6300

    def test_set_datapath_init(self):
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.read = MagicMock()

        self.api.xcvr_eeprom.read.side_effect = [0x3, 0x00]
        self.api.set_datapath_init(0xff)
        kall = self.api.xcvr_eeprom.write.call_args
        assert kall is not None
        assert kall[0] == (consts.DATAPATH_DEINIT_FIELD, 0xff)

        self.api.xcvr_eeprom.read.side_effect = [0x4, 0x00]
        self.api.set_datapath_init(0xff)
        kall = self.api.xcvr_eeprom.write.call_args
        assert kall is not None
        assert kall[0] == (consts.DATAPATH_DEINIT_FIELD, 0x00)

    def test_set_datapath_deinit(self):
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.read = MagicMock()

        self.api.xcvr_eeprom.read.side_effect = [0x3, 0x00]
        self.api.set_datapath_deinit(0xff)
        kall = self.api.xcvr_eeprom.write.call_args
        assert kall is not None
        assert kall[0] == (consts.DATAPATH_DEINIT_FIELD, 0x00)

        self.api.xcvr_eeprom.read.side_effect = [0x4, 0x00]
        self.api.set_datapath_deinit(0xff)
        kall = self.api.xcvr_eeprom.write.call_args
        assert kall is not None
        assert kall[0] == (consts.DATAPATH_DEINIT_FIELD, 0xff)

    @pytest.mark.parametrize("mock_response, expected", [
        (None, None),
        (0x00, [False for _ in range(8)]),
        (0xff, [True for _ in range(8)]),
        (0x0f, [True, True, True, True, False, False, False, False]),
    ])
    def test_get_datapath_deinit(self, mock_response, expected):
        self.api.xcvr_eeprom = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response

        assert self.api.get_datapath_deinit() == expected

    def test_get_application_advertisement(self):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = [
            {
                consts.HOST_ELECTRICAL_INTERFACE + "_1": "400GAUI-8 C2M (Annex 120E)",
                consts.MODULE_MEDIA_INTERFACE_SM + "_1": "400GBASE-DR4 (Cl 124)",
                consts.MEDIA_LANE_COUNT + "_1": 4,
                consts.HOST_LANE_COUNT + "_1": 8,
                consts.HOST_LANE_ASSIGNMENT_OPTION + "_1": 0x01,
                consts.MEDIA_LANE_ASSIGNMENT_OPTION + "_1": 0x02
            },
            Sff8024.MODULE_MEDIA_TYPE[2]
        ]
        result = self.api.get_application_advertisement()

        assert len(result) == 1
        assert result[1]['host_electrical_interface_id'] == '400GAUI-8 C2M (Annex 120E)'
        assert result[1]['module_media_interface_id'] == '400GBASE-DR4 (Cl 124)'
        assert result[1]['host_lane_count'] == 8
        assert result[1]['media_lane_count'] == 4
        assert result[1]['host_lane_assignment_options'] == 0x01
        assert result[1]['media_lane_assignment_options'] == 0x02

    def test_get_application_advertisement_apps_with_missing_data(self):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = [
            {
                consts.HOST_ELECTRICAL_INTERFACE + "_1": "400GAUI-8 C2M (Annex 120E)",
                consts.HOST_ELECTRICAL_INTERFACE + "_2": None,
                consts.HOST_ELECTRICAL_INTERFACE + "_3": "200GAUI-8 C2M (Annex 120C)",
                consts.HOST_ELECTRICAL_INTERFACE + "_4": "40GBASE-CR4 (Clause 85)",
                consts.HOST_ELECTRICAL_INTERFACE + "_5": "50GBASE-CR (Clause 126)",
                consts.HOST_ELECTRICAL_INTERFACE + "_6": "200GBASE-CR4 (Clause 136)",
                consts.HOST_ELECTRICAL_INTERFACE + "_7": "200GAUI-2-S C2M (Annex 120G)",
                consts.HOST_ELECTRICAL_INTERFACE + "_8": "800G S C2M (placeholder)",

                consts.MODULE_MEDIA_INTERFACE_SM + "_1": "400GBASE-DR4 (Cl 124)",
                consts.MODULE_MEDIA_INTERFACE_SM + "_2": "25GBASE-LR (Cl 114)",
                consts.MODULE_MEDIA_INTERFACE_SM + "_3": "40GBASE-LR4 (Cl 87)",
                consts.MODULE_MEDIA_INTERFACE_SM + "_4": None,
                consts.MODULE_MEDIA_INTERFACE_SM + "_5": "10GBASE-LR (Cl 52)",
                consts.MODULE_MEDIA_INTERFACE_SM + "_6": "50GBASE-FR (Cl 139)",
                consts.MODULE_MEDIA_INTERFACE_SM + "_7": "100GBASE-DR (Cl 140)",
                consts.MODULE_MEDIA_INTERFACE_SM + "_8": "800GBASE-DR8 (placeholder)",

                consts.MEDIA_LANE_COUNT + "_1": 4,
                consts.MEDIA_LANE_COUNT + "_2": 4,
                consts.MEDIA_LANE_COUNT + "_3": 4,
                consts.MEDIA_LANE_COUNT + "_4": 4,
                consts.MEDIA_LANE_COUNT + "_5": None,
                consts.MEDIA_LANE_COUNT + "_6": 4,
                consts.MEDIA_LANE_COUNT + "_7": 4,
                consts.MEDIA_LANE_COUNT + "_8": 4,

                consts.HOST_LANE_COUNT + "_1": 8,
                consts.HOST_LANE_COUNT + "_2": 8,
                consts.HOST_LANE_COUNT + "_3": 8,
                consts.HOST_LANE_COUNT + "_4": 8,
                consts.HOST_LANE_COUNT + "_5": 8,
                consts.HOST_LANE_COUNT + "_6": 8,
                consts.HOST_LANE_COUNT + "_7": 8,
                consts.HOST_LANE_COUNT + "_8": None,

                consts.HOST_LANE_ASSIGNMENT_OPTION + "_1": 0x01,
                consts.HOST_LANE_ASSIGNMENT_OPTION + "_2": 0x01,
                consts.HOST_LANE_ASSIGNMENT_OPTION + "_3": 0x01,
                consts.HOST_LANE_ASSIGNMENT_OPTION + "_4": 0x01,
                consts.HOST_LANE_ASSIGNMENT_OPTION + "_5": 0x01,
                consts.HOST_LANE_ASSIGNMENT_OPTION + "_6": 0x01,
                consts.HOST_LANE_ASSIGNMENT_OPTION + "_7": None,
                consts.HOST_LANE_ASSIGNMENT_OPTION + "_8": 0x01,

                consts.MEDIA_LANE_ASSIGNMENT_OPTION + "_1": 0x02,
                consts.MEDIA_LANE_ASSIGNMENT_OPTION + "_2": 0x02,
                consts.MEDIA_LANE_ASSIGNMENT_OPTION + "_3": 0x02,
                consts.MEDIA_LANE_ASSIGNMENT_OPTION + "_4": 0x02,
                consts.MEDIA_LANE_ASSIGNMENT_OPTION + "_5": 0x02,
                consts.MEDIA_LANE_ASSIGNMENT_OPTION + "_6": 0x02,
                consts.MEDIA_LANE_ASSIGNMENT_OPTION + "_7": 0x02,
                consts.MEDIA_LANE_ASSIGNMENT_OPTION + "_8": 0x02
            },
            Sff8024.MODULE_MEDIA_TYPE[2],
            None,
            Sff8024.MODULE_MEDIA_TYPE[2],
            Sff8024.MODULE_MEDIA_TYPE[2],
            Sff8024.MODULE_MEDIA_TYPE[2],
            Sff8024.MODULE_MEDIA_TYPE[2],
            Sff8024.MODULE_MEDIA_TYPE[2],
            Sff8024.MODULE_MEDIA_TYPE[2]
        ]
        result = self.api.get_application_advertisement()

        assert len(result) == 3

        assert result[1]['host_electrical_interface_id'] == '400GAUI-8 C2M (Annex 120E)'
        assert result[1]['module_media_interface_id'] == '400GBASE-DR4 (Cl 124)'
        assert result[1]['host_lane_count'] == 8
        assert result[1]['media_lane_count'] == 4
        assert result[1]['host_lane_assignment_options'] == 0x01
        assert result[1]['media_lane_assignment_options'] == 0x02

        assert result[6]['host_electrical_interface_id'] == '200GBASE-CR4 (Clause 136)'
        assert result[6]['module_media_interface_id'] == '50GBASE-FR (Cl 139)'
        assert result[6]['host_lane_count'] == 8
        assert result[6]['media_lane_count'] == 4
        assert result[6]['host_lane_assignment_options'] == 0x01
        assert result[6]['media_lane_assignment_options'] == 0x02

    def test_get_application_advertisement_non_support(self):
        self.api.xcvr_eeprom.read = MagicMock(return_value = None)
        self.api.is_flat_memory = MagicMock(return_value = False)
        result = self.api.get_application_advertisement()
        assert result == {}

    def test_get_application(self):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = 0x20

        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = False
        appl = self.api.get_application(0)
        assert appl == 2

        appl = self.api.get_application(2)
        assert appl == 2

        appl = self.api.get_application(self.api.NUM_CHANNELS)
        assert appl == 0

        self.api.is_flat_memory.return_value = True
        appl = self.api.get_application(0)
        assert appl == 0

        appl = self.api.get_application(2)
        assert appl == 0

        appl = self.api.get_application(self.api.NUM_CHANNELS)
        assert appl == 0

    def test_set_application(self):
        self.api.xcvr_eeprom.write = MagicMock()

        self.api.xcvr_eeprom.write.call_count = 0
        self.api.set_application(0x00, 1, 0)
        assert self.api.xcvr_eeprom.write.call_count == 0

        self.api.xcvr_eeprom.write.call_count = 0
        self.api.set_application(0x01, 1, 1)
        assert self.api.xcvr_eeprom.write.call_count == 1

        self.api.xcvr_eeprom.write.call_count = 0
        self.api.set_application(0x0f, 1, 1)
        assert self.api.xcvr_eeprom.write.call_count == 4

        self.api.xcvr_eeprom.write.call_count = 0
        self.api.set_application(0xff, 1, 1)
        assert self.api.xcvr_eeprom.write.call_count == 8

        self.api.xcvr_eeprom.write.call_count = 0
        self.api.set_application(0x7fffffff, 1, 1)
        assert self.api.xcvr_eeprom.write.call_count == self.api.NUM_CHANNELS

    @pytest.mark.parametrize("datapath_state,config_state", [
        ( {
            'DP1State': 'DataPathDeactivated',
            'DP2State': 'DataPathDeactivated',
            'DP3State': 'DataPathDeactivated',
            'DP4State': 'DataPathDeactivated',
            'DP5State': 'DataPathDeactivated',
            'DP6State': 'DataPathDeactivated',
            'DP7State': 'DataPathDeactivated',
            'DP8State': 'DataPathDeactivated',
          },
          {
            'ConfigStatusLane1': 'ConfigSuccess',
            'ConfigStatusLane2': 'ConfigSuccess',
            'ConfigStatusLane3': 'ConfigSuccess',
            'ConfigStatusLane4': 'ConfigSuccess',
            'ConfigStatusLane5': 'ConfigSuccess',
            'ConfigStatusLane6': 'ConfigSuccess',
            'ConfigStatusLane7': 'ConfigSuccess',
            'ConfigStatusLane8': 'ConfigSuccess' 
          } )
    ])
    def test_decommission_all_datapaths(self, datapath_state, config_state):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.set_datapath_deinit = MagicMock(return_value = True)

        self.api.get_datapath_state = MagicMock()
        self.api.get_datapath_state.return_value = datapath_state
        self.api.get_config_datapath_hostlane_status = MagicMock()
        self.api.get_config_datapath_hostlane_status.return_value = config_state
        assert True == self.api.decommission_all_datapaths()

    def test_set_module_si_eq_pre_settings(self):
        optics_si_dict = { "OutputEqPreCursorTargetRx":{
                             "OutputEqPreCursorTargetRx1":2, "OutputEqPreCursorTargetRx2":2, "OutputEqPreCursorTargetRx3":2, "OutputEqPreCursorTargetRx4":2,
                             "OutputEqPreCursorTargetRx5":2, "OutputEqPreCursorTargetRx6":2, "OutputEqPreCursorTargetRx7":2, "OutputEqPreCursorTargetRx8":2 }
                         }
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.write = MagicMock()
        mock_resp = [0x1, 0x7]
        self.api.xcvr_eeprom.read.side_effect = mock_resp
        self.api.stage_custom_si_settings(0x01, optics_si_dict)
        assert self.api.xcvr_eeprom.write.call_count == 1

    def test_set_module_si_eq_en_settings(self):
        optics_si_dict = { "AdaptiveInputEqEnableTx":{
                             "AdaptiveInputEqEnableTx1": 2, "AdaptiveInputEqEnableTx2": 2, "AdaptiveInputEqEnableTx3": 2, "AdaptiveInputEqEnableTx4": 2,
                             "AdaptiveInputEqEnableTx5": 2, "AdaptiveInputEqEnableTx6": 2, "AdaptiveInputEqEnableTx7": 2, "AdaptiveInputEqEnableTx8": 2,}
                         }
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.write = MagicMock()
        mock_resp = [0x1, 0x3]
        self.api.xcvr_eeprom.read.side_effect = mock_resp
        self.api.stage_custom_si_settings(0xff, optics_si_dict)
        assert self.api.xcvr_eeprom.write.call_count == 8

    def test_set_module_si_eq_recall_settings(self):
        optics_si_dict = { "AdaptiveInputEqRecalledTx":{
                             "AdaptiveInputEqRecalledTx1":1, "AdaptiveInputEqRecalledTx2":1, "AdaptiveInputEqRecalledTx3":1, "AdaptiveInputEqRecalledTx4":1,
                             "AdaptiveInputEqRecalledTx5":1, "AdaptiveInputEqRecalledTx6":1, "AdaptiveInputEqRecalledTx7":1, "AdaptiveInputEqRecalledTx8":1 }
                         }
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.write = MagicMock()
        mock_resp = [0x1]
        self.api.xcvr_eeprom.read.side_effect = mock_resp
        self.api.stage_custom_si_settings(0x0f, optics_si_dict)
        assert self.api.xcvr_eeprom.write.call_count == 4

    def test_set_module_si_eq_post_settings(self):
        optics_si_dict = { "OutputEqPostCursorTargetRx":{
                             "OutputEqPostCursorTargetRx1":2, "OutputEqPostCursorTargetRx2":2, "OutputEqPostCursorTargetRx3":2, "OutputEqPostCursorTargetRx4":2,
                             "OutputEqPostCursorTargetRx5":2, "OutputEqPostCursorTargetRx6":2, "OutputEqPostCursorTargetRx7":2, "OutputEqPostCursorTargetRx8":2 }
                         }
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.write = MagicMock()
        mock_resp = [0x1, 0x7]
        self.api.xcvr_eeprom.read.side_effect = mock_resp
        self.api.stage_custom_si_settings(0x01, optics_si_dict)
        assert self.api.xcvr_eeprom.write.call_count == 1

    def test_set_module_si_fixed_en_settings(self):
        optics_si_dict = { "FixedInputEqTargetTx":{
                             "FixedInputEqTargetTx1":1, "FixedInputEqTargetTx2":1, "FixedInputEqTargetTx3":1, "FixedInputEqTargetTx4":1,
                             "FixedInputEqTargetTx5":1, "FixedInputEqTargetTx6":1, "FixedInputEqTargetTx7":1, "FixedInputEqTargetTx8":1 }
                         }
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.write = MagicMock()
        mock_resp = [0x1, 0x1]
        self.api.xcvr_eeprom.read.side_effect = mock_resp
        self.api.stage_custom_si_settings(0xff, optics_si_dict)
        assert self.api.xcvr_eeprom.write.call_count == 8

    def test_set_module_cdr_enable_tx_settings(self):
        optics_si_dict = { "CDREnableTx":{
                              "CDREnableTx1":1, "CDREnableTx2":1, "CDREnableTx3":1, "CDREnableTx4":1,
                              "CDREnableTx5":0, "CDREnableTx6":0, "CDREnableTx7":0, "CDREnableTx8":0 }
                        }
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.write = MagicMock()
        mock_resp = [0x1]
        self.api.xcvr_eeprom.read.side_effect = mock_resp
        self.api.stage_custom_si_settings(0x0f, optics_si_dict)
        assert self.api.xcvr_eeprom.write.call_count == 4

    def test_set_module_cdr_enable_rx_settings(self):
        optics_si_dict = { "CDREnableRx":{
                              "CDREnableRx1":1, "CDREnableRx2":1, "CDREnableRx3":1, "CDREnableRx4":1,
                              "CDREnableRx5":0, "CDREnableRx6":0, "CDREnableRx7":0, "CDREnableRx8":0 }
                        }
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.write = MagicMock()
        mock_resp = [0x1]
        self.api.xcvr_eeprom.read.side_effect = mock_resp
        self.api.stage_custom_si_settings(0xff, optics_si_dict)
        assert self.api.xcvr_eeprom.write.call_count == 8

    def test_set_module_OutputAmplitudeTargetRx_settings(self):
        optics_si_dict = { "OutputAmplitudeTargetRx":{
                             "OutputAmplitudeTargetRx1":1, "OutputAmplitudeTargetRx2":1, "OutputAmplitudeTargetRx3":1, "OutputAmplitudeTargetRx4":1,
                             "OutputAmplitudeTargetRx5":1, "OutputAmplitudeTargetRx6":1, "OutputAmplitudeTargetRx7":1, "OutputAmplitudeTargetRx8":1 }
                         }
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.write = MagicMock()
        mock_resp = [0x1, 0x7]
        self.api.xcvr_eeprom.read.side_effect = mock_resp
        self.api.stage_custom_si_settings(0x0f, optics_si_dict)
        assert self.api.xcvr_eeprom.write.call_count == 4

    def test_get_error_description(self):
        with patch.object(self.api, 'is_flat_memory') as mock_method:
            mock_method.return_value = False
            self.api.get_module_state = MagicMock()
            self.api.get_module_state.return_value = 'ModuleReady'
            self.api.get_datapath_state = MagicMock()
            self.api.get_datapath_state.return_value = {
                'DP1State': 'DataPathActivated',
                'DP2State': 'DataPathActivated',
                'DP3State': 'DataPathActivated',
                'DP4State': 'DataPathActivated',
                'DP5State': 'DataPathActivated',
                'DP6State': 'DataPathActivated',
                'DP7State': 'DataPathActivated',
                'DP8State': 'DataPathActivated'
            }
            self.api.get_config_datapath_hostlane_status = MagicMock()
            self.api.get_config_datapath_hostlane_status.return_value = {
                'ConfigStatusLane1': 'ConfigSuccess',
                'ConfigStatusLane2': 'ConfigSuccess',
                'ConfigStatusLane3': 'ConfigSuccess',
                'ConfigStatusLane4': 'ConfigSuccess',
                'ConfigStatusLane5': 'ConfigSuccess',
                'ConfigStatusLane6': 'ConfigSuccess',
                'ConfigStatusLane7': 'ConfigSuccess',
                'ConfigStatusLane8': 'ConfigSuccess'
            }
            self.api.xcvr_eeprom.read = MagicMock()
            self.api.xcvr_eeprom.read.return_value = 0x10

            result = self.api.get_error_description()
            assert result is 'OK'
            
            self.api.get_config_datapath_hostlane_status.return_value = {
                'ConfigStatusLane1': 'ConfigRejected',
                'ConfigStatusLane2': 'ConfigRejected',
                'ConfigStatusLane3': 'ConfigRejected',
                'ConfigStatusLane4': 'ConfigRejected',
                'ConfigStatusLane5': 'ConfigRejected',
                'ConfigStatusLane6': 'ConfigRejected',
                'ConfigStatusLane7': 'ConfigRejected',
                'ConfigStatusLane8': 'ConfigRejected'
            }
            result = self.api.get_error_description()
            assert result is 'ConfigRejected'
            
            self.api.get_datapath_state.return_value = {
                'DP1State': 'DataPathDeactivated',
                'DP2State': 'DataPathActivated',
                'DP3State': 'DataPathActivated',
                'DP4State': 'DataPathActivated',
                'DP5State': 'DataPathActivated',
                'DP6State': 'DataPathActivated',
                'DP7State': 'DataPathActivated',
                'DP8State': 'DataPathActivated'
            }
            result = self.api.get_error_description()
            assert result is 'DataPathDeactivated'

    def test_random_read_fail(self):
        def mock_read_raw(offset, size):
            i = random.randint(0, 1)
            return None if i == 0 else b'0' * size

        self.api.xcvr_eeprom.read = self.old_read_func
        self.api.xcvr_eeprom.reader = mock_read_raw

        run_num = 5
        while run_num > 0:
            try:
                self.api.get_transceiver_dom_real_value()
                self.api.get_transceiver_info()
                self.api.get_transceiver_threshold_info()
                self.api.get_transceiver_status()
            except:
                assert 0, traceback.format_exc()
            run_num -= 1

    def test_get_transceiver_info_firmware_versions(self):
        self.api.get_module_fw_info = MagicMock()
        self.api.get_module_fw_info.return_value = None
        expected_result = {"active_firmware" : "N/A", "inactive_firmware" : "N/A"}
        result = self.api.get_transceiver_info_firmware_versions()
        assert result == expected_result

        self.api.get_module_fw_info = MagicMock()
        self.api.get_module_fw_info.side_effect = {'result': TypeError}
        result = self.api.get_transceiver_info_firmware_versions()
        assert result == expected_result

        expected_result = {"active_firmware" : "2.0.0", "inactive_firmware" : "1.0.0"}
        self.api.get_module_fw_info.side_effect = [{'result': ( '', '', '', '', '', '', '', '','2.0.0', '1.0.0')}]
        result = self.api.get_transceiver_info_firmware_versions()
        assert result == expected_result


    @pytest.mark.parametrize("mock_flat_memory, mock_response, expected", [
        (False, True, True),
        (False, False, False),
        (False, None, None),
        (True, True, False),
    ])
    def test_get_tx_adaptive_eq_fail_flag_supported(self, mock_flat_memory, mock_response, expected):
        with patch.object(self.api, 'is_flat_memory', return_value=mock_flat_memory):
            self.api.xcvr_eeprom.read = MagicMock(return_value=mock_response)
            result = self.api.get_tx_adaptive_eq_fail_flag_supported()
            assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([True, {'TxAdaptiveEqFailFlag1': 1, 'TxAdaptiveEqFailFlag2': 0}], [True, False]),
        ([False, {'TxAdaptiveEqFailFlag1': 1, 'TxAdaptiveEqFailFlag2': 0}], ['N/A' for _ in range(8)]),
        ([None, None], None),
        ([True, None], None)
    ])
    def test_get_tx_adaptive_eq_fail_flag(self, mock_response, expected):
        self.api.get_tx_adaptive_eq_fail_flag_supported = MagicMock()
        self.api.get_tx_adaptive_eq_fail_flag_supported.return_value = mock_response[0]
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[1]
        result = self.api.get_tx_adaptive_eq_fail_flag()
        assert result == expected
