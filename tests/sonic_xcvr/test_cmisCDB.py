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
        codes = CmisCode
        mem_map = CmisMemMap(codes)
        reader = MagicMock(return_value=None)
        writer = MagicMock()
        xcvr_eeprom = XcvrEeprom(reader, writer, mem_map)
        api = CmisApi(xcvr_eeprom)
        api.cdb = CmisCdbApi(xcvr_eeprom)
        return api.cdb
    
    @pytest.mark.parametrize("mock_response, expected", [
        (64, False),
        (0, True)
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
        ([1], 1),
        ([128,128,128], 128)
    ])
    def test_cdb1_chkstatus(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.xcvr_eeprom.read = MagicMock()
        cdb.xcvr_eeprom.read.side_effect = mock_response
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
        cdb.xcvr_eeprom.read_raw = MagicMock()
        cdb.xcvr_eeprom.read_raw.return_value = mock_response[2]
        result = cdb.read_cdb()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([1], (None, None, None)),
        ([128, 128, 128], (None, None, None)),
    ])
    def test_cmd0000h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.cmd0000h()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([1], 1),
        ([128, 128, 64], 64)
    ])
    def test_cmd0001h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.cmd0001h()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([1], (None, None, None)),
        ([64, 64, 64], (None, None, None)),
    ])
    def test_cmd0040h(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.cmd0040h()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([1], (None, None, None)),
        ([64, 64, 64], (None, None, None)),
    ])
    def test_get_fw_management_features(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.get_fw_management_features()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([1], (None, None, None)),
        ([64, 64, 64], (None, None, None)),
    ])
    def test_get_fw_info(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.get_fw_info()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        ([3, bytearray(b'\x00\x00\x00'), 1000000], [1], 1),
        ([3, bytearray(b'\x00\x00\x00'), 1000000], [64, 64, 64], 64)
    ])
    def test_start_fw_download(self, input_param, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.start_fw_download(*input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([1], 1),
        ([64, 64, 64], 64),
    ])
    def test_abort_fw_download(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.abort_fw_download()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        ([100, bytearray(116)], [1], 1),
        ([100, bytearray(116)], [64, 64, 64], 64)
    ])
    def test_block_write_lpl(self, input_param, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.block_write_lpl(*input_param)
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        ([100, bytearray(2048), True, 100], [1], 1),
        ([100, bytearray(2047), False, 100], [64, 64, 64], 64),
    ])
    def test_block_write_epl(self, input_param, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.block_write_epl(*input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([1], 1),
        ([64, 64, 64], 64),
    ])
    def test_validate_fw_image(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.validate_fw_image()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([1], 1),
        ([64, 64, 64], 64),
    ])
    def test_run_fw_image(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.run_fw_image()
        assert result == expected
        
    @pytest.mark.parametrize("mock_response, expected", [
        ([1], 1),
        ([64, 64, 64], 64),
    ])
    def test_commit_fw_image(self, mock_response, expected):
        cdb = self.mock_cdb_api()
        cdb.cdb1_chkstatus = MagicMock()
        cdb.cdb1_chkstatus.side_effect = mock_response
        result = cdb.commit_fw_image()
        assert result == expected
    

    