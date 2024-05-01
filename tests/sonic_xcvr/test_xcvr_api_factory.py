from unittest.mock import patch
from mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.api.credo.aec_800g import CmisAec800gApi
from sonic_platform_base.sonic_xcvr.mem_maps.credo.aec_800g import CmisAec800gMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.credo.aec_800g import CmisAec800gCodes
from sonic_platform_base.sonic_xcvr.api.innolight.fr_800g import CmisFr800gApi
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.xcvr_api_factory import XcvrApiFactory
from sonic_platform_base.sonic_xcvr.api.public.sff8636 import Sff8636Api
from sonic_platform_base.sonic_xcvr.api.public.sff8436 import Sff8436Api

def mock_reader_sff8636(start, length):
    return bytes([0x0d]) if start == 0 else bytes ([0x06])

def mock_reader_sff8436(start, length):
    return bytes([0x0d]) if start == 0 else bytes ([0x00])

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

    def mock_reader(self, start, length):
        return bytes([0x18])

    @patch('sonic_platform_base.sonic_xcvr.xcvr_api_factory.XcvrApiFactory._get_vendor_name', MagicMock(return_value='Credo'))
    @patch('sonic_platform_base.sonic_xcvr.xcvr_api_factory.XcvrApiFactory._get_vendor_part_num', MagicMock(return_value='CAC81X321M2MC1MS'))
    def test_create_xcvr_api(self):
        self.api.reader = self.mock_reader
        CmisAec800gCodes = MagicMock()
        CmisAec800gMemMap = MagicMock()
        XcvrEeprom = MagicMock()
        CmisAec800gApi = MagicMock()
        self.api.create_xcvr_api()

    @patch('sonic_platform_base.sonic_xcvr.xcvr_api_factory.XcvrApiFactory._get_vendor_name', MagicMock(return_value='CISCO-INNOLIGHT'))
    @patch('sonic_platform_base.sonic_xcvr.xcvr_api_factory.XcvrApiFactory._get_vendor_part_num', MagicMock(return_value='T-DH8CNT-NCI'))
    def test_create_xcvr_api(self):
        self.api.reader = self.mock_reader
        CmisCodes = MagicMock()
        CmisMemMap = MagicMock()
        XcvrEeprom = MagicMock()
        CmisFr800gApi = MagicMock()
        self.api.create_xcvr_api()

    @pytest.mark.parametrize("reader, expected_api", [
        (mock_reader_sff8636, Sff8636Api),
        (mock_reader_sff8436, Sff8436Api),
    ])
    def test_create_xcvr_api_8436_8636(self, reader, expected_api):
        self.api.reader = reader
        api = self.api.create_xcvr_api()
        assert isinstance(api, expected_api)
