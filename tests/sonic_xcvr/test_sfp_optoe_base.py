from mock import MagicMock

from sonic_platform_base.sonic_xcvr import sfp_optoe_base
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes


class TestSfpOptoeBase:
    codes = CmisCodes
    mem_map = CmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    old_read_func = eeprom.read
    api = CmisApi(eeprom)

    def test_read_eeprom_by_page(self):
        sfp = sfp_optoe_base.SfpOptoeBase()
        sfp.get_xcvr_api = MagicMock(return_value=TestSfpOptoeBase.api)
        sfp.read_eeprom = MagicMock(return_value=bytearray([0]))
        assert sfp.read_eeprom_by_page(0, 0, 1) is not None

        sfp.get_xcvr_api.return_value = None
        assert sfp.read_eeprom_by_page(0, 0, 1) is None

    def test_write_eeprom(self):
        sfp = sfp_optoe_base.SfpOptoeBase()
        sfp.get_xcvr_api = MagicMock(return_value=TestSfpOptoeBase.api)
        sfp.write_eeprom = MagicMock(return_value=True)
        data = bytearray([0])
        assert sfp.write_eeprom_by_page(0, 0, data) is True

        sfp.get_xcvr_api.return_value = None
        assert sfp.write_eeprom_by_page(0, 0, data) is False
