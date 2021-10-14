from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.api.public.cmisCDB import CmisCdbApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.sff8024 import Sff8024
from sonic_platform_base.sonic_xcvr.codes.public.cmis_code import CmisCode

class TestCDB(object):

    def mock_cdb_api(self):
        codes = {'sff8024':Sff8024, 'cmis_code':CmisCode}
        mem_map = CmisMemMap(codes)
        reader = MagicMock(return_value=None)
        writer = MagicMock()
        xcvr_eeprom = XcvrEeprom(reader, writer, mem_map)
        api = CmisApi(xcvr_eeprom)
        api.cdb = CmisCdbApi(xcvr_eeprom)
        return api.cdb
    
    @pytest.mark.parametrize("mock_response, expected", [
        (64, False)
    ])
    def test_cdb1_chkflags(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.xcvr_eeprom.read = MagicMock()
        cdb.xcvr_eeprom.read.return_value = mock_response
        result = cdb.cdb1_chkflags()
        assert result == expected

    @pytest.mark.parametrize("input_param, expected", [
        (bytearray(b'\x00'), 255)
    ])
    def test_cdb_chkcode(self, input_param, expected):
        cdb = self.mock_cdb_api()
        result = cdb.cdb_chkcode(input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_cdb1_chkstatus(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.xcvr_eeprom.read = MagicMock()
        cdb.xcvr_eeprom.read.return_value = mock_response
        result = cdb.cdb1_chkstatus()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            [18, 35, (0, 7, 112, 255, 255, 16, 0, 0, 19, 136, 0, 100, 3, 232, 19, 136, 58, 152)],
            (18, 35, (0, 7, 112, 255, 255, 16, 0, 0, 19, 136, 0, 100, 3, 232, 19, 136, 58, 152))
        )
    ])
    def test_read_cdb(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.xcvr_eeprom.read = MagicMock()
        cdb.xcvr_eeprom.read.side_effect = mock_response[0:2]
        cdb.xcvr_eeprom.read_flexible = MagicMock()
        cdb.xcvr_eeprom.read_flexible.return_value = mock_response[2]
        result = cdb.read_cdb()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_cmd0001h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0001h()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, (None, None, None))
    ])
    def test_cmd0040h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0040h()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, (None, None, None))
    ])
    def test_cmd0041h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0041h()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, (None, None, None))
    ])
    def test_cmd0100h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0100h()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        ([3, bytearray(b'\x00\x00\x00'), 1000000], 1, 1)
    ])
    def test_cmd0101h(self, input_param, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0101h(*input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_cmd0102h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0102h()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        ([100, bytearray(116)], 1, 1)
    ])
    def test_cmd0103h(self, input_param, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0103h(*input_param)
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        ([100, bytearray(2048), True, 2048], 1, 1)
    ])
    def test_cmd0104h(self, input_param, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0104h(*input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_cmd0107h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0107h()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_cmd0109h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd0109h()
        assert result == expected
        
    @pytest.mark.parametrize("mock_response, expected", [
        (1, 1)
    ])
    def test_cmd010Ah(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.return_value = mock_response
        result = cdb.cmd010Ah()
        assert result == expected
    

    