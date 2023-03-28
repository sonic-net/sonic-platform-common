from mock import MagicMock, patch
import traceback
import random

from sonic_platform_base.sonic_xcvr.api.public.sff8436 import Sff8436Api
from sonic_platform_base.sonic_xcvr.codes.public.sff8436 import Sff8436Codes
from sonic_platform_base.sonic_xcvr.mem_maps.public.sff8436 import Sff8436MemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom


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
                self.api.get_transceiver_bulk_status()
                self.api.get_transceiver_info()
                self.api.get_transceiver_threshold_info()
            except:
                assert 0, traceback.format_exc()
            run_num -= 1
