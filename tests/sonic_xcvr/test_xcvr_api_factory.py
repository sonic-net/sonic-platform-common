from unittest.mock import patch
from mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
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

    def mock_reader(self, start, length):
        return bytes([0x18])

    @pytest.mark.parametrize("reader, expected_api", [
        (mock_reader_sff8636, Sff8636Api),
        (mock_reader_sff8436, Sff8436Api),
    ])
    def test_create_xcvr_api_8436_8636(self, reader, expected_api):
        self.api.reader = reader
        api = self.api.create_xcvr_api()
        assert isinstance(api, expected_api)
