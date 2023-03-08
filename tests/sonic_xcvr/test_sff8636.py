from mock import MagicMock, patch
import pytest
import random
import traceback

from sonic_platform_base.sonic_xcvr.api.public.sff8636 import Sff8636Api
from sonic_platform_base.sonic_xcvr.codes.public.sff8636 import Sff8636Codes
from sonic_platform_base.sonic_xcvr.mem_maps.public.sff8636 import Sff8636MemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.fields import consts

class TestSff8636(object):
    codes = Sff8636Codes
    mem_map = Sff8636MemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = Sff8636Api(eeprom)

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

    @pytest.mark.parametrize("mock_response, expected", [
        (bytearray([0x0]), "Power Class 1 Module (1.5W max.)"),
        (bytearray([0x40]), "Power Class 2 Module (2.0W max.)"),
        (bytearray([0x80]), "Power Class 3 Module (2.5W max.)"),
        (bytearray([0xC0]), "Power Class 4 Module (3.5W max.)"),
        (bytearray([0xC1]), "Power Class 5 Module (4.0W max.)"),
        (bytearray([0xC2]), "Power Class 6 Module (4.5W max.)"),
        (bytearray([0xC3]), "Power Class 7 Module (5.0W max.)"),
        (bytearray([0x20]), "Power Class 8 Module")
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
                self.api.get_transceiver_bulk_status()
                self.api.get_transceiver_info()
                self.api.get_transceiver_threshold_info()
            except:
                assert 0, traceback.format_exc()
            run_num -= 1
