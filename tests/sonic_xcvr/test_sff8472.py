from mock import MagicMock
import sys
import pytest

from sonic_platform_base.sonic_xcvr.api.public.sff8472 import Sff8472Api
from sonic_platform_base.sonic_xcvr.codes.public.sff8472 import Sff8472Codes
from sonic_platform_base.sonic_xcvr.fields.public.sff8472 import VoltageField
from sonic_platform_base.sonic_xcvr.mem_maps.public.sff8472 import Sff8472MemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.fields import consts

class TestSff8472(object):
    codes = Sff8472Codes
    mem_map = Sff8472MemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = Sff8472Api(eeprom)
    is_py2 = sys.version_info < (3,)

    def test_api(self):
        """
        Verify all api access valid fields    
        """
        self.api.get_model()
        self.api.get_serial()
        self.api.get_transceiver_info()
        self.api.get_transceiver_bulk_status()
        self.api.get_transceiver_threshold_info()
        self.api.get_rx_los()
        self.api.get_tx_fault()
        self.api.get_tx_disable()
        self.api.get_tx_disable_channel()
        self.api.get_module_temperature()
        self.api.get_voltage()
        self.api.get_tx_bias()
        self.api.get_tx_power()
        self.api.get_rx_power()
        self.reader.return_value = bytearray([0xFF])
        self.api.tx_disable(True)
        self.reader.return_value = None
        self.api.tx_disable_channel(0x5, True)
        self.api.is_flat_memory()
        self.api.get_temperature_support()
        self.api.get_voltage_support()
        self.api.get_tx_power_support()
        self.api.get_rx_power_support()
        self.api.get_rx_los_support()
        self.api.get_tx_bias_support()
        self.api.get_tx_fault_support()
        self.api.get_tx_disable_support()
        self.api.get_transceiver_thresholds_support()
        self.api.get_lpmode_support()
        self.api.get_power_override_support()

    def test_temp(self):
        temp_field = self.mem_map.get_field(consts.TEMPERATURE_FIELD)
        data = bytearray([0x80, 0x00])
        deps = {
           consts.INT_CAL_FIELD: True,
           consts.EXT_CAL_FIELD: False, 
           consts.T_SLOPE_FIELD: 1,
           consts.T_OFFSET_FIELD: 0,
        }
        decoded = temp_field.decode(data, **deps)
        assert decoded == -128

        data = bytearray([0x0F, 0xFF])
        deps = {
           consts.INT_CAL_FIELD: False,
           consts.EXT_CAL_FIELD: True, 
           consts.T_SLOPE_FIELD: 2,
           consts.T_OFFSET_FIELD: 10,
        }
        decoded = temp_field.decode(data, **deps)
        assert decoded == 32 if self.is_py2 else 32.03125

    def test_voltage(self):
        voltage_field = self.mem_map.get_field(consts.VOLTAGE_FIELD)
        data = bytearray([0xFF, 0xFF])
        deps = {
           consts.INT_CAL_FIELD: True,
           consts.EXT_CAL_FIELD: False, 
           consts.T_SLOPE_FIELD: 1,
           consts.T_OFFSET_FIELD: 0,
        }
        decoded = voltage_field.decode(data, **deps)
        expected = 6 if self.is_py2 else 6.5535
        assert decoded == expected

        data = bytearray([0x7F, 0xFF])
        deps = {
           consts.INT_CAL_FIELD: False,
           consts.EXT_CAL_FIELD: True, 
           consts.V_SLOPE_FIELD: 2,
           consts.V_OFFSET_FIELD: 10,
        }
        decoded = voltage_field.decode(data, **deps)
        assert decoded == 6 if self.is_py2 else 6.5544

    def test_tx_bias(self):
        tx_bias_field = self.mem_map.get_field(consts.TX_BIAS_FIELD)
        data = bytearray([0xFF, 0xFF])
        deps = {
           consts.INT_CAL_FIELD: True,
           consts.EXT_CAL_FIELD: False, 
           consts.TX_I_SLOPE_FIELD: 1,
           consts.TX_I_OFFSET_FIELD: 0,
        }
        decoded = tx_bias_field.decode(data, **deps)
        expected = 131 if self.is_py2 else 131.07
        assert decoded == expected

        data = bytearray([0x7F, 0xFF])
        deps = {
           consts.INT_CAL_FIELD: False,
           consts.EXT_CAL_FIELD: True, 
           consts.TX_I_SLOPE_FIELD: 2,
           consts.TX_I_OFFSET_FIELD: 10,
        }
        decoded = tx_bias_field.decode(data, **deps)
        assert decoded == 131 if self.is_py2 else 131.088

    def test_tx_power(self):
        tx_power_field = self.mem_map.get_field(consts.TX_POWER_FIELD)
        data = bytearray([0xFF, 0xFF])
        deps = {
           consts.INT_CAL_FIELD: True,
           consts.EXT_CAL_FIELD: False, 
           consts.TX_PWR_SLOPE_FIELD: 1,
           consts.TX_PWR_OFFSET_FIELD: 0,
        }
        decoded = tx_power_field.decode(data, **deps)
        expected = 6 if self.is_py2 else 6.5535
        assert decoded == expected

        data = bytearray([0x7F, 0xFF])
        deps = {
           consts.INT_CAL_FIELD: False,
           consts.EXT_CAL_FIELD: True, 
           consts.TX_PWR_SLOPE_FIELD: 2,
           consts.TX_PWR_OFFSET_FIELD: 10,
        }
        decoded = tx_power_field.decode(data, **deps)
        assert decoded == 6 if self.is_py2 else 6.5544

    def test_rx_power(self):
        rx_power_field = self.mem_map.get_field(consts.RX_POWER_FIELD)
        data = bytearray([0xFF, 0xFF])
        deps = {
           consts.INT_CAL_FIELD: True,
           consts.EXT_CAL_FIELD: False, 
           consts.RX_PWR_0_FIELD: 0,
           consts.RX_PWR_1_FIELD: 1,
           consts.RX_PWR_2_FIELD: 0,
           consts.RX_PWR_3_FIELD: 0,
           consts.RX_PWR_4_FIELD: 0,
        }
        decoded = rx_power_field.decode(data, **deps)
        expected = 6 if self.is_py2 else 6.5535
        assert decoded == expected

        deps = {
           consts.INT_CAL_FIELD: False,
           consts.EXT_CAL_FIELD: True, 
           consts.RX_PWR_0_FIELD: 10,
           consts.RX_PWR_1_FIELD: 2,
           consts.RX_PWR_2_FIELD: 0.1,
           consts.RX_PWR_3_FIELD: 0.01,
           consts.RX_PWR_4_FIELD: 0.001,
        }
        decoded = rx_power_field.decode(data, **deps)
        assert decoded == 209.713

    @pytest.mark.parametrize("mock_response, expected", [
        (bytearray([0x04, 0x0]), "Shortwave laser, linear RX (SA)"),
        (bytearray([0x02, 0x0]), "Longwave laser (LC)"),
        (bytearray([0x01, 0x0]), "Electrical inter-enclosure (EL)"),
        (bytearray([0x0, 0x80]), "Electrical intra-enclosure (EL)"),
        (bytearray([0x0, 0x40]), "Shortwave laser w/o OFC (SN)"),
        (bytearray([0x0, 0x20]), "Shortwave laser w OFC (SL)"),
        (bytearray([0x0, 0x10]), "Longwave Laser (LL)")
    ])
    def test_fiber_channel_transmitter_tech(self, mock_response, expected):
        self.api.xcvr_eeprom.reader = MagicMock()
        self.api.xcvr_eeprom.reader.return_value = mock_response
        result = self.api.xcvr_eeprom.read(consts.FIBRE_CHANNEL_TRANSMITTER_TECH_FIELD)
        assert result == expected
