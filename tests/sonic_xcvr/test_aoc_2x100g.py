from unittest.mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.api.hisense.aoc_2x100g import CmisAocSingleBankApi
from sonic_platform_base.sonic_xcvr.fields import cdb_consts

class TestCmisAocSingleBankApi(object):
    codes = CmisCodes
    mem_map = CmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = CmisAocSingleBankApi(eeprom)

    def _fw_info(self, a_oper=False, a_admin=False, a_valid=False, b_oper=False, b_admin=False, b_valid=False,
                 a_maj=0, a_min=0, a_bld=0, b_maj=0, b_min=0, b_bld=0, f_maj=0, f_min=0, f_bld=0):
        return {
            cdb_consts.CDB1_FIRMWARE_STATUS: {
                cdb_consts.CDB1_BANKA_OPER_STATUS: a_oper,
                cdb_consts.CDB1_BANKA_ADMIN_STATUS: a_admin,
                cdb_consts.CDB1_BANKA_VALID_STATUS: a_valid,
                cdb_consts.CDB1_BANKB_OPER_STATUS: b_oper,
                cdb_consts.CDB1_BANKB_ADMIN_STATUS: b_admin,
                cdb_consts.CDB1_BANKB_VALID_STATUS: b_valid,
            },
            cdb_consts.CDB1_IMAGE_INFO: 7,
            cdb_consts.CDB1_BANKA_MAJOR_VERSION: a_maj,
            cdb_consts.CDB1_BANKA_MINOR_VERSION: a_min,
            cdb_consts.CDB1_BANKA_BUILD_VERSION: a_bld,
            cdb_consts.CDB1_BANKB_MAJOR_VERSION: b_maj,
            cdb_consts.CDB1_BANKB_MINOR_VERSION: b_min,
            cdb_consts.CDB1_BANKB_BUILD_VERSION: b_bld,
            cdb_consts.CDB1_FACTORY_MAJOR_VERSION: f_maj,
            cdb_consts.CDB1_FACTORY_MINOR_VERSION: f_min,
            cdb_consts.CDB1_FACTORY_BUILD_VERSION: f_bld,
        }

    def test_get_module_fw_info_single_bank(self):
        """Image A running, inactive firmware read from EEPROM."""
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = self._fw_info(
            a_oper=True, a_admin=True, b_valid=True, a_maj=2, a_min=5, a_bld=3, f_maj=1, f_min=6)
        self.api._cdb_fw_hdlr = mock_fw_hdlr
        self.api._init_cdb_fw_handler = True
        self.api.get_module_inactive_firmware = MagicMock(return_value='1.1')
        result = self.api.get_module_fw_info()
        assert result['status'] is True
        assert result['result'] == ('2.5.3', 1, 1, 0, 'N/A', 0, 0, 1, '2.5.3', '1.1.0')
        assert 'Inactive Firmware: 1.1.0' in result['info']

    def test_get_module_fw_info_eeprom_read_error(self):
        """Image A running and EEPROM returns None, inactive = N/A."""
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = self._fw_info(
            a_oper=True, a_admin=True, b_valid=True, a_maj=2, a_min=5, a_bld=3, f_maj=1, f_min=6)
        self.api._cdb_fw_hdlr = mock_fw_hdlr
        self.api._init_cdb_fw_handler = True
        self.api.get_module_inactive_firmware = MagicMock(return_value=None)
        result = self.api.get_module_fw_info()
        assert result['status'] is True
        assert result['result'] == ('2.5.3', 1, 1, 0, 'N/A', 0, 0, 1, '2.5.3', 'N/A')
        assert 'Inactive Firmware: N/A' in result['info']

    def test_get_module_fw_info_cdb_not_supported(self):
        """CDB not supported."""
        self.api._cdb_fw_hdlr = None
        self.api._init_cdb_fw_handler = False
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': 'CDB Not supported', 'result': None}

    def test_get_module_fw_info_handler_init_failed(self):
        """CDB FW handler init failed."""
        self.api._cdb_fw_hdlr = None
        self.api._init_cdb_fw_handler = True
        self.api._create_cdb_fw_handler = MagicMock(return_value=None)
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': 'CDB Not supported', 'result': None}

    def test_get_module_fw_info_cdb_returns_none(self):
        """CDB returns None firmware info."""
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = None
        mock_fw_hdlr.get_cmd_status_code.return_value = None
        self.api._cdb_fw_hdlr = mock_fw_hdlr
        self.api._init_cdb_fw_handler = True
        result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': 'Failed to get firmware info', 'result': 0}
