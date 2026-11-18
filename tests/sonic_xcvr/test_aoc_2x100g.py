from unittest.mock import MagicMock, patch

from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.api.hisense.aoc_2x100g import CmisAocSingleBankApi
from sonic_platform_base.sonic_xcvr.fields import cdb_consts, consts

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
        with patch.object(self.api, 'is_cdb_supported', return_value=True), \
             patch.object(self.api, 'get_module_inactive_firmware', return_value='1.1'):
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
        # Scoped so the None-returning mock does not leak into later tests on
        # the shared api instance.
        with patch.object(self.api, 'is_cdb_supported', return_value=True), \
             patch.object(self.api, 'get_module_inactive_firmware', return_value=None):
            result = self.api.get_module_fw_info()
        assert result['status'] is True
        assert result['result'] == ('2.5.3', 1, 1, 0, 'N/A', 0, 0, 1, '2.5.3', 'N/A')
        assert 'Inactive Firmware: N/A' in result['info']

    def test_get_module_fw_info_cdb_not_supported(self):
        """CDB not advertised: versions come from the lower memory registers."""
        self.api._cdb_fw_hdlr = None
        self.api._init_cdb_fw_handler = False
        eeprom_values = {
            consts.ACTIVE_FW_MAJOR_REV: 1,
            consts.ACTIVE_FW_MINOR_REV: 2,
            consts.INACTIVE_FW_MAJOR_REV: 3,
            consts.INACTIVE_FW_MINOR_REV: 4,
        }
        with patch.object(self.api, 'is_cdb_supported', return_value=False), \
             patch.object(self.api.xcvr_eeprom, 'read', side_effect=eeprom_values.get), \
             patch.object(self.api, 'is_flat_memory', return_value=False):
            result = self.api.get_module_fw_info()
        # CmisApi attaches the lower memory versions to failure returns.
        assert result == {'status': False, 'info': 'CDB Not supported', 'result': None,
                          'active_firmware': '1.2', 'inactive_firmware': '3.4'}

    def test_get_module_fw_info_handler_init_failed(self):
        """CDB advertised, but the CDB FW handler failed to initialize."""
        self.api._cdb_fw_hdlr = None
        self.api._init_cdb_fw_handler = True
        self.api._create_cdb_fw_handler = MagicMock(return_value=None)
        with patch.object(self.api, 'is_cdb_supported', return_value=True):
            result = self.api.get_module_fw_info()
        # CmisApi attaches the lower memory versions to failure returns; the
        # eeprom mock reads None, which the readers report as N/A.
        assert result == {'status': False, 'info': 'CDB Not supported', 'result': None,
                          'active_firmware': 'N/A', 'inactive_firmware': 'N/A'}

    def test_get_module_fw_info_cdb_returns_none(self):
        """CDB returns None firmware info."""
        mock_fw_hdlr = MagicMock()
        mock_fw_hdlr.get_firmware_info.return_value = None
        mock_fw_hdlr.get_cmd_status_code.return_value = None
        self.api._cdb_fw_hdlr = mock_fw_hdlr
        self.api._init_cdb_fw_handler = True
        with patch.object(self.api, 'is_cdb_supported', return_value=True):
            result = self.api.get_module_fw_info()
        assert result == {'status': False, 'info': 'Failed to get firmware info', 'result': 0,
                          'active_firmware': 'N/A', 'inactive_firmware': 'N/A'}
