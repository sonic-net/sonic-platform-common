from mock import MagicMock
import sys
import pytest
import random
import traceback

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
        self.api.get_transceiver_status()
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
        self.api.tx_disable_channel(0x5, True)
        self.reader.return_value = None
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

    def test_random_read_fail(self):
        def mock_read_raw(offset, size):
            i = random.randint(0, 1)
            return None if i == 0 else b'0' * size

        self.api.xcvr_eeprom.reader = mock_read_raw

        run_num = 5
        while run_num > 0:
            try:
                self.api.get_transceiver_bulk_status()
                self.api.get_transceiver_info()
                self.api.get_transceiver_threshold_info()
            except:
                assert 0, traceback.format_exc()
            run_num -= 1

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                [False],
                [False],
                0,
                [False]
            ],
            {
                "tx_disabled_channel": 0,
                "tx1disable": False,
                'txfault1': False,
                'rxlos1': False,
            }
        ),
        (
            [
                None,
                None,
                None,
                None
            ],
            None
        )
    ])
    def test_get_transceiver_status(self, mock_response, expected):
        self.api.get_rx_los = MagicMock()
        self.api.get_rx_los.return_value = mock_response[0]
        self.api.get_tx_fault = MagicMock()
        self.api.get_tx_fault.return_value = mock_response[1]
        self.api.get_tx_disable_channel = MagicMock()
        self.api.get_tx_disable_channel.return_value = mock_response[2]
        self.api.get_tx_disable = MagicMock()
        self.api.get_tx_disable.return_value = mock_response[3]
        result = self.api.get_transceiver_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                50,
                3.3,
                [70],
                [0.1],
                [0.1],
                True, True, True, True, True, True
            ],
            {
                'temperature': 50,
                'voltage': 3.3,
                'tx1power': -10.0, 'tx2power': 'N/A', 'tx3power': 'N/A', 'tx4power': 'N/A',
                'rx1power': -10.0, 'rx2power': 'N/A', 'rx3power': 'N/A', 'rx4power': 'N/A',
                'tx1bias': 70, 'tx2bias': 'N/A', 'tx3bias': 'N/A', 'tx4bias': 'N/A',
            }
        )
    ])
    def test_get_transceiver_bulk_status(self, mock_response, expected):
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
        result = self.api.get_transceiver_bulk_status()
        assert result == expected

    def test_dump_eeprom(self):
        with pytest.raises(ValueError):
            self.api.dump_eeprom(-1)

        self.api.is_active_cable = MagicMock(return_value=False)
        self.api.xcvr_eeprom.read_raw = MagicMock()
        self.api.xcvr_eeprom.read_raw.return_value = bytearray([x for x in range(128)])
        output = self.api.dump_eeprom(0)
        expected_output = """        A0h dump
        00000000 00 01 02 03 04 05 06 07  08 09 0a 0b 0c 0d 0e 0f |................|
        00000010 10 11 12 13 14 15 16 17  18 19 1a 1b 1c 1d 1e 1f |................|
        00000020 20 21 22 23 24 25 26 27  28 29 2a 2b 2c 2d 2e 2f | !"#$%&'()*+,-./|
        00000030 30 31 32 33 34 35 36 37  38 39 3a 3b 3c 3d 3e 3f |0123456789:;<=>?|
        00000040 40 41 42 43 44 45 46 47  48 49 4a 4b 4c 4d 4e 4f |@ABCDEFGHIJKLMNO|
        00000050 50 51 52 53 54 55 56 57  58 59 5a 5b 5c 5d 5e 5f |PQRSTUVWXYZ[\]^_|
        00000060 60 61 62 63 64 65 66 67  68 69 6a 6b 6c 6d 6e 6f |`abcdefghijklmno|
        00000070 70 71 72 73 74 75 76 77  78 79 7a 7b 7c 7d 7e 7f |pqrstuvwxyz{|}~.|"""
        assert output == expected_output

        self.api.is_active_cable.return_value = True
        self.api.xcvr_eeprom.read_raw.return_value = bytearray([x for x in range(256)])
        output = self.api.dump_eeprom(0)
        expected_output = """        A0h dump
        00000000 00 01 02 03 04 05 06 07  08 09 0a 0b 0c 0d 0e 0f |................|
        00000010 10 11 12 13 14 15 16 17  18 19 1a 1b 1c 1d 1e 1f |................|
        00000020 20 21 22 23 24 25 26 27  28 29 2a 2b 2c 2d 2e 2f | !"#$%&'()*+,-./|
        00000030 30 31 32 33 34 35 36 37  38 39 3a 3b 3c 3d 3e 3f |0123456789:;<=>?|
        00000040 40 41 42 43 44 45 46 47  48 49 4a 4b 4c 4d 4e 4f |@ABCDEFGHIJKLMNO|
        00000050 50 51 52 53 54 55 56 57  58 59 5a 5b 5c 5d 5e 5f |PQRSTUVWXYZ[\]^_|
        00000060 60 61 62 63 64 65 66 67  68 69 6a 6b 6c 6d 6e 6f |`abcdefghijklmno|
        00000070 70 71 72 73 74 75 76 77  78 79 7a 7b 7c 7d 7e 7f |pqrstuvwxyz{|}~.|
        00000080 80 81 82 83 84 85 86 87  88 89 8a 8b 8c 8d 8e 8f |................|
        00000090 90 91 92 93 94 95 96 97  98 99 9a 9b 9c 9d 9e 9f |................|
        000000a0 a0 a1 a2 a3 a4 a5 a6 a7  a8 a9 aa ab ac ad ae af |................|
        000000b0 b0 b1 b2 b3 b4 b5 b6 b7  b8 b9 ba bb bc bd be bf |................|
        000000c0 c0 c1 c2 c3 c4 c5 c6 c7  c8 c9 ca cb cc cd ce cf |................|
        000000d0 d0 d1 d2 d3 d4 d5 d6 d7  d8 d9 da db dc dd de df |................|
        000000e0 e0 e1 e2 e3 e4 e5 e6 e7  e8 e9 ea eb ec ed ee ef |................|
        000000f0 f0 f1 f2 f3 f4 f5 f6 f7  f8 f9 fa fb fc fd fe ff |................|"""
        assert output == expected_output

        self.api.xcvr_eeprom.read_raw.return_value = bytearray([x for x in range(128)])
        output = self.api.dump_eeprom(1)
        print(output)
        expected_output = """
        A2h dump (lower 128 bytes)
        00000000 00 01 02 03 04 05 06 07  08 09 0a 0b 0c 0d 0e 0f |................|
        00000010 10 11 12 13 14 15 16 17  18 19 1a 1b 1c 1d 1e 1f |................|
        00000020 20 21 22 23 24 25 26 27  28 29 2a 2b 2c 2d 2e 2f | !"#$%&'()*+,-./|
        00000030 30 31 32 33 34 35 36 37  38 39 3a 3b 3c 3d 3e 3f |0123456789:;<=>?|
        00000040 40 41 42 43 44 45 46 47  48 49 4a 4b 4c 4d 4e 4f |@ABCDEFGHIJKLMNO|
        00000050 50 51 52 53 54 55 56 57  58 59 5a 5b 5c 5d 5e 5f |PQRSTUVWXYZ[\]^_|
        00000060 60 61 62 63 64 65 66 67  68 69 6a 6b 6c 6d 6e 6f |`abcdefghijklmno|
        00000070 70 71 72 73 74 75 76 77  78 79 7a 7b 7c 7d 7e 7f |pqrstuvwxyz{|}~.|"""
        assert output == expected_output
