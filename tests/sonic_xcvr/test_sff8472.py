from mock import MagicMock

from sonic_platform_base.sonic_xcvr.api.public.sff8472 import Sff8472Api
from sonic_platform_base.sonic_xcvr.codes.public.sff8472 import Sff8472Codes
from sonic_platform_base.sonic_xcvr.mem_maps.public.sff8472 import Sff8472MemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom

class TestSff8472(object):
    codes = Sff8472Codes
    mem_map = Sff8472MemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = Sff8472Api(eeprom)

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
