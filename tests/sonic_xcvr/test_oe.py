from mock import MagicMock

from sonic_platform_base.sonic_xcvr.api.broadcom.davisson_oe import DavissonTh6OeApi
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoHardwareInfo, OeId
from sonic_platform_base.sonic_xcvr.cpo.oe import OeApiFactory
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.davisson_oe import DavissonTh6OeMemMap


class TestOeApiFactory(object):
    def test_create_api_davisson(self):
        oe = MagicMock()
        oe.bank = 2
        oe.hardware_id = CpoHardwareInfo(oe_id=OeId.BROADCOM_DAVISSON, elsfp_id=None)
        factory = OeApiFactory(oe)

        api = factory.create_api()

        assert isinstance(api, DavissonTh6OeApi)
        assert isinstance(api.xcvr_eeprom.mem_map, DavissonTh6OeMemMap)
        # The device's bank and EEPROM accessors must be threaded through.
        assert api.xcvr_eeprom.mem_map.bank == 2
        assert api.xcvr_eeprom.reader is oe.read_eeprom
        assert api.xcvr_eeprom.writer is oe.write_eeprom
