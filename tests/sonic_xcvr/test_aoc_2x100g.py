from unittest.mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.api.hisense.aoc_2x100g import CmisAocSingleBankApi
from sonic_platform_base.sonic_xcvr.fields import cdb_consts

def _compose_fw_info(a_oper, a_admin, a_valid, b_oper, b_admin, b_valid, a_maj, a_min, a_bld, b_maj, b_min, b_bld, f_maj, f_min, f_bld, img_info=7):
    return {
        cdb_consts.CDB1_FIRMWARE_STATUS: {
            cdb_consts.CDB1_BANKA_OPER_STATUS: a_oper, cdb_consts.CDB1_BANKA_ADMIN_STATUS: a_admin, cdb_consts.CDB1_BANKA_VALID_STATUS: a_valid,
            cdb_consts.CDB1_BANKB_OPER_STATUS: b_oper, cdb_consts.CDB1_BANKB_ADMIN_STATUS: b_admin, cdb_consts.CDB1_BANKB_VALID_STATUS: b_valid,
        },
        cdb_consts.CDB1_IMAGE_INFO: img_info,
        cdb_consts.CDB1_BANKA_MAJOR_VERSION: a_maj, cdb_consts.CDB1_BANKA_MINOR_VERSION: a_min, cdb_consts.CDB1_BANKA_BUILD_VERSION: a_bld,
        cdb_consts.CDB1_BANKB_MAJOR_VERSION: b_maj, cdb_consts.CDB1_BANKB_MINOR_VERSION: b_min, cdb_consts.CDB1_BANKB_BUILD_VERSION: b_bld,
        cdb_consts.CDB1_FACTORY_MAJOR_VERSION: f_maj, cdb_consts.CDB1_FACTORY_MINOR_VERSION: f_min, cdb_consts.CDB1_FACTORY_BUILD_VERSION: f_bld,
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
    def test_get_module_fw_info(self, mock_response, expected):
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = mock_response
        self.api.cdb = MagicMock()
        self.api._init_cdb_fw_handler = True
        self.api._cdb_fw_hdlr = mock_fw_hdlr
        self.api.get_module_inactive_firmware = MagicMock(return_value=expected[0])
        result = self.api.get_module_fw_info()
        assert result['status'] == expected[1]['status']
        assert result['result'] == expected[1]['result']

    def test_get_module_fw_info_cdb_none(self):
        self.api.cdb = None
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': "CDB Not supported", 'result': None}

    def test_get_module_fw_info_handler_none(self):
        self.api.cdb = MagicMock()
        self.api._init_cdb_fw_handler = False
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': "CDB FW handler init failed", 'result': None}

    def test_get_module_fw_info_fw_info_none(self):
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = None
        self.api.cdb = MagicMock()
        self.api._init_cdb_fw_handler = True
        self.api._cdb_fw_hdlr = mock_fw_hdlr
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': "Failed to get firmware info", 'result': None}

    def test_get_module_fw_info_fw_info_false(self):
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = False
        self.api.cdb = MagicMock()
        self.api._init_cdb_fw_handler = True
        self.api._cdb_fw_hdlr = mock_fw_hdlr
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': "Failed to get firmware info", 'result': None}
