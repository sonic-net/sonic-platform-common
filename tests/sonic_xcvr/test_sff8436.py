from mock import MagicMock, patch
import pytest
import traceback
import random

from sonic_platform_base.sonic_xcvr.api.public.sff8436 import Sff8436Api
from sonic_platform_base.sonic_xcvr.codes.public.sff8436 import Sff8436Codes
from sonic_platform_base.sonic_xcvr.mem_maps.public.sff8436 import Sff8436MemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.fields import consts


class TestSff8436(object):
    codes = Sff8436Codes
    mem_map = Sff8436MemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = Sff8436Api(eeprom)

    def test_api(self):
        """
        Verify all api access valid fields
        """
        self.api.get_model()
        self.api.get_serial()
        self.api.get_transceiver_info()
        self.api.get_transceiver_dom_real_value()
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
        self.api.tx_disable(True)
        self.api.tx_disable_channel(0x5, True)
        self.api.get_power_override()
        self.api.get_power_set()
        self.reader.return_value = bytearray([0xFF])
        self.api.set_power_override(True, True)
        self.reader.return_value = None
        self.api.is_flat_memory()
        self.api.get_tx_power_support()
        self.api.get_rx_power_support()
        self.api.is_copper()
        self.api.get_temperature_support()
        self.api.get_voltage_support()
        self.api.get_rx_los_support()
        self.api.get_tx_bias_support()
        self.api.get_tx_fault_support()
        self.api.get_tx_disable_support()
        self.api.get_transceiver_thresholds_support()
        self.api.get_lpmode_support()
        self.api.get_power_override_support()
        self.api.set_lpmode(True)
        self.api.get_lpmode()

    @pytest.mark.parametrize("mock_response, expected", [
        (bytearray([0x0]), "Power Class 1 Module (1.5W max. Power consumption)"),
        (bytearray([0x40]), "Power Class 2 Module (2.0W max. Power consumption)"),
        (bytearray([0x80]), "Power Class 3 Module (2.5W max. Power consumption)"),
        (bytearray([0xC0]), "Power Class 4 Module (3.5W max. Power consumption)")
    ])
    def test_power_class(self, mock_response, expected):
        self.api.xcvr_eeprom.reader = MagicMock()
        self.api.xcvr_eeprom.reader.return_value = mock_response
        result = self.api.xcvr_eeprom.read(consts.POWER_CLASS_FIELD)
        assert result == expected


    @pytest.mark.parametrize("mock_response, expected", [
       (bytearray([0x02, 0x0]), "Longwave laser (LC)"),
       (bytearray([0x01, 0x0]), "Electrical inter-enclosure (EN)"),
       (bytearray([0x0, 0x80]), "Electrical intra-enclosure"),
       (bytearray([0x0, 0x40]), "Shortwave laser w/o OFC (SN)"),
       (bytearray([0x0, 0x20]), "Shortwave laser w OFC (SL)"),
       (bytearray([0x0, 0x10]), "Longwave Laser (LL)")
    ])
    def test_fiber_channel_transmitter_tech(self, mock_response, expected):
        self.api.xcvr_eeprom.reader = MagicMock()
        self.api.xcvr_eeprom.reader.return_value = mock_response
        result = self.api.xcvr_eeprom.read(consts.FIBRE_CHANNEL_TRANSMITTER_TECH_FIELD)
        assert result == expected

    def test_is_copper(self):
        with patch.object(self.api, 'xcvr_eeprom') as mock_eeprom:
            mock_eeprom.read = MagicMock()
            mock_eeprom.read.return_value = None
            assert self.api.is_copper() is None
            mock_eeprom.read.return_value = '40GBASE-CR4'
            assert self.api.is_copper()
            self.api._is_copper = None
            mock_eeprom.read.return_value = 'SR'
            assert not self.api.is_copper()

    def test_simulate_copper(self):
        with patch.object(self.api, 'is_copper', return_value=True):
            assert self.api.get_rx_power() == ['N/A'] * self.api.NUM_CHANNELS
            assert self.api.get_module_temperature() == 'N/A'
            assert self.api.get_voltage() == 'N/A'
            assert not self.api.get_tx_power_support()
            assert not self.api.get_rx_power_support()
            assert not self.api.get_rx_power_support()
            assert not self.api.get_temperature_support()
            assert not self.api.get_voltage_support()

    def test_random_read_fail(self):
        def mock_read_raw(offset, size):
            i = random.randint(0, 1)
            return None if i == 0 else b'0' * size

        self.api.xcvr_eeprom.reader = mock_read_raw

        run_num = 5
        while run_num > 0:
            try:
                self.api.get_transceiver_dom_real_value()
                self.api.get_transceiver_info()
                self.api.get_transceiver_threshold_info()
            except:
                assert 0, traceback.format_exc()
            run_num -= 1

    def test_get_lpmode(self):
        self.api.get_lpmode_support = MagicMock()
        self.api.get_lpmode_support.return_value = True
        self.api.get_power_override_support = MagicMock()
        self.api.get_power_override_support.return_value = True
        self.api.get_power_set = MagicMock()
        self.api.get_power_set.return_value = True
        self.api.get_power_override = MagicMock()
        self.api.get_power_override.return_value = True
        assert self.api.get_lpmode()
        self.api.get_power_set.return_value = False
        self.api.get_power_override.return_value = True
        assert not self.api.get_lpmode()
        self.api.get_lpmode_support.return_value = False
        self.api.get_power_override_support.return_value = False
        assert not self.api.get_lpmode()

    def test_set_lpmode(self):
        self.api.get_lpmode_support = MagicMock()
        self.api.get_lpmode_support.return_value = True
        self.api.get_power_override_support = MagicMock()
        self.api.get_power_override_support.return_value = True
        self.api.set_power_override = MagicMock()
        self.api.set_power_override.return_value = True
        assert self.api.set_lpmode(True)
        assert self.api.set_lpmode(False)
        self.api.get_lpmode_support.return_value = False
        self.api.get_power_override_support.return_value = False
        assert not self.api.set_lpmode(True)

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                0,
                [False, False, False, False]
            ],
            {
                "tx_disabled_channel": 0,
                "tx1disable": False,
                "tx2disable": False,
                "tx3disable": False,
                "tx4disable": False,
            }
        ),
        (
            [
                None,
                None
            ],
            None
        )
    ])
    def test_get_transceiver_status(self, mock_response, expected):
        self.api.get_tx_disable_channel = MagicMock()
        self.api.get_tx_disable_channel.return_value = mock_response[0]
        self.api.get_tx_disable = MagicMock()
        self.api.get_tx_disable.return_value = mock_response[1]
        result = self.api.get_transceiver_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                [False, False, False, False],
                [False, False, False, False],
            ],
            {
                'tx1fault': False,
                'tx2fault': False,
                'tx3fault': False,
                'tx4fault': False,
                'rx1los': False,
                'rx2los': False,
                'rx3los': False,
                'rx4los': False,
            }
        ),
        (
            [
                None,
                None
            ],
            None
        )
    ])
    def test_get_transceiver_status_flags(self, mock_response, expected):
        self.api.get_rx_los = MagicMock()
        self.api.get_rx_los.return_value = mock_response[0]
        self.api.get_tx_fault = MagicMock()
        self.api.get_tx_fault.return_value = mock_response[1]
        result = self.api.get_transceiver_status_flags()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                50,
                3.3,
                [70, 70, 70, 70],
                [0.1, 0.1, 0.1, 0.1],
                [0.1, 0.1, 0.1, 0.1],
                True, True, True, True, True, True
            ],
            {
                'temperature': 50,
                'voltage': 3.3,
                'tx1power': -10.0, 'tx2power': -10.0, 'tx3power': -10.0, 'tx4power': -10.0,
                'rx1power': -10.0, 'rx2power': -10.0, 'rx3power': -10.0, 'rx4power': -10.0,
                'tx1bias': 70, 'tx2bias': 70, 'tx3bias': 70, 'tx4bias': 70,
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
        result = self.api.get_transceiver_dom_real_value()
        assert result == expected


