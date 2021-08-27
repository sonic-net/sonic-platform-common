from mock import MagicMock

from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes

class TestCmis(object):
    codes = CmisCodes
    mem_map = CmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = CmisApi(eeprom)

    def test_api(self):
        """
        Verify all api access valid fields    
        """
        self.api.get_model()
        self.api.get_transceiver_info()
        self.api.get_transceiver_bulk_status()
        self.api.get_transceiver_threshold_info()
        self.api.get_module_temperature()
        self.api.get_voltage()
        self.api.is_flat_memory()
        self.api.get_temperature_support()
        self.api.get_voltage_support()
        self.api.get_rx_los()
        self.api.get_rx_los_support()
        self.api.get_tx_bias()
        self.api.get_tx_bias_support()
        self.api.get_tx_power()
        self.api.get_tx_power_support()
        self.api.get_rx_power()
        self.api.get_rx_power_support()
        self.api.get_tx_fault()
        self.api.get_tx_fault_support()
        self.api.get_tx_disable_support()
        self.api.get_tx_disable()
        self.api.get_tx_disable_channel()
        self.api.tx_disable(True)
        self.api.tx_disable_channel(0x5, True)
        self.api.get_lpmode_support()
        self.api.get_power_override_support()
