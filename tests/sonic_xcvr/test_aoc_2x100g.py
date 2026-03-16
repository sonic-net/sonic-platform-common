from unittest.mock import patch, MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.api.hisense.aoc_2x100g import CmisAocSingleBankApi

def _compose_fw_info(a_oper, a_admin, a_valid, b_oper, b_admin, b_valid, a_maj, a_min, a_bld, b_maj, b_min, b_bld, f_maj, f_min, f_bld, img_info=7):
    return {
        'Cdb1FirmwareStatus': {
            'CdbBankAOperStatus': a_oper, 'CdbBankAAdminStatus': a_admin, 'CdbBankAValidStatus': a_valid,
            'CdbBankBOperStatus': b_oper, 'CdbBankBAdminStatus': b_admin, 'CdbBankBValidStatus': b_valid,
        },
        'CdbImageInfo': img_info,
        'CdbBankAMajorVersion': a_maj, 'CdbBankAMinorVersion': a_min, 'CdbBankABuildVersion': a_bld,
        'CdbBankBMajorVersion': b_maj, 'CdbBankBMinorVersion': b_min, 'CdbBankBBuildVersion': b_bld,
        'CdbFactoryMajorVersion': f_maj, 'CdbFactoryMinorVersion': f_min, 'CdbFactoryBuildVersion': f_bld,
    }

class TestCmisAocSingleBankApi(object):
    codes = CmisCodes
    mem_map = CmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = CmisAocSingleBankApi(eeprom)

    @pytest.mark.parametrize("mock_response, expected", [
        (_compose_fw_info(True,  True,  False, False, False, True,  2, 5, 3, 0, 0, 0, 1, 6, 0),
         ('1.1', {'status': True, 'result': ('2.5.3', 1, 1, 0, 'N/A', 0, 0, 1, '2.5.3', '1.1.0')})),
        (_compose_fw_info(False, False, False, False, False, True,  1, 0, 1, 0, 0, 0, 1, 0, 0),
         ('0.0', {'status': True, 'result': ('1.0.1', 0, 0, 0, 'N/A', 0, 0, 1, 'N/A', 'N/A')})),
        (_compose_fw_info(False, False, True,  False, False, True,  0, 0, 0, 0, 0, 0, 0, 0, 0),
         ('0.0', {'status': True, 'result': ('N/A', 0, 0, 1, 'N/A', 0, 0, 1, 'N/A', 'N/A')})),
        (_compose_fw_info(False, False, False, True,  True,  False, 1, 4, 0, 1, 3, 0, 1, 6, 0),
         ('1.3', {'status': True, 'result': ('1.4.0', 0, 0, 0, 'N/A', 1, 1, 0, 'N/A', 'N/A')})),
    ])

    @patch('sonic_platform_base.sonic_xcvr.api.hisense.aoc_2x100g.CdbFwHandler')
    def test_get_module_fw_info(self, mock_cdb_fw_cls, mock_response, expected):
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = mock_response
        mock_cdb_fw_cls.return_value = mock_fw_hdlr
        self.api.cdb = MagicMock()
        self.api.get_module_inactive_firmware = MagicMock(return_value=expected[0])
        result = self.api.get_module_fw_info()
        assert result['status'] == expected[1]['status']
        assert result['result'] == expected[1]['result']

    def test_get_module_fw_info_cdb_none(self):
        self.api.cdb = None
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': "CDB Not supported", 'result': None}

    @patch('sonic_platform_base.sonic_xcvr.api.hisense.aoc_2x100g.CdbFwHandler')
    def test_get_module_fw_info_handler_init_fail(self, mock_cdb_fw_cls):
        mock_cdb_fw_cls.side_effect = Exception("Init failed")
        self.api.cdb = MagicMock()
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': "CDB FW handler init failed", 'result': None}

    @patch('sonic_platform_base.sonic_xcvr.api.hisense.aoc_2x100g.CdbFwHandler')
    def test_get_module_fw_info_fw_info_none(self, mock_cdb_fw_cls):
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = None
        mock_cdb_fw_cls.return_value = mock_fw_hdlr
        self.api.cdb = MagicMock()
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': "Failed to get firmware info", 'result': None}

    @patch('sonic_platform_base.sonic_xcvr.api.hisense.aoc_2x100g.CdbFwHandler')
    def test_get_module_fw_info_fw_info_empty(self, mock_cdb_fw_cls):
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = {}
        mock_cdb_fw_cls.return_value = mock_fw_hdlr
        self.api.cdb = MagicMock()
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': "Failed to get firmware info", 'result': None}
