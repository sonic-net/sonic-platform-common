from unittest.mock import patch
from mock import MagicMock
import pytest


from sonic_platform_base.sonic_xcvr.api.credo.aec_800g import CmisAec800gApi
from sonic_platform_base.sonic_xcvr.mem_maps.credo.aec_800g import CmisAec800gMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.credo.aec_800g import CmisAec800gCodes
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.xcvr_api_factory import XcvrApiFactory

class BytesMock(bytes):
    def decode(self, encoding='utf-8', errors='strict'):
        return 'DecodedCredo'

class TestXcvrApiFactory(object):
    read_eeprom = MagicMock
    write_eeprom = MagicMock
    api = XcvrApiFactory(read_eeprom, write_eeprom)

    def test_get_vendor_name(self):
        self.api.reader = MagicMock()
        self.api.reader.return_value = b'Credo'
        with patch.object(BytesMock, 'decode', return_value='DecodedCredo'):
            result = self.api._get_vendor_name()
        assert result == 'Credo'.strip()

    def test_get_vendor_part_num(self):
        self.api.reader = MagicMock()
        self.api.reader.return_value = b'CAC81X321M2MC1MS'
        with patch.object(BytesMock, 'decode', return_value='DecodedCAC81X321M2MC1MS'):
            result = self.api._get_vendor_part_num()
        assert result == 'CAC81X321M2MC1MS'.strip()

    def test_create_xcvrd_api(self):
        self._get_id = MagicMock()
        self._get_id.side_effect = 0x18
        self._get_vendor_name= MagicMock()
        self._get_vendor_name.side_effect = 'Credo'
        self._get_vendor_part_num = MagicMock()
        self._get_vendor_part_num.side_effect = 'CAC81X321M2MC1MS'
        CmisAec800gCodes = MagicMock()
        CmisAec800gMemMap = MagicMock()
        XcvrEeprom = MagicMock()
        CmisAec800gApi = MagicMock()
        self.api.create_xcvr_api()
