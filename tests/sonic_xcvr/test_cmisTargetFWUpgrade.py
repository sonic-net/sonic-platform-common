from unittest.mock import patch
from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.api.public.cmisTargetFWUpgrade import CmisTargetFWUpgradeAPI
from sonic_platform_base.sonic_xcvr.codes.public.cmisTargetFWUpgrade import CmisTargetFWUpgradeCodes
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmisTargetFWUpgrade import CmisTargetFWUpgradeMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom

class TestCmis(object):
    codes = CmisTargetFWUpgradeCodes
    mem_map = CmisTargetFWUpgradeMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = CmisTargetFWUpgradeAPI(eeprom)

    @pytest.mark.parametrize("set_firmware_result, module_type", [
        (False, 'QSFP+ or later with CMIS'),
        (True, 'Unknown'),
        (True, 'QSFP+ or later with CMIS')
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info_firmware_versions', MagicMock(side_effect=Exception('error')))
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmisTargetFWUpgrade.CmisTargetFWUpgradeAPI._get_server_firmware_version', MagicMock())
    def test_get_transceiver_info_firmware_versions_failure(self, set_firmware_result, module_type):
        expected_output = {'active_firmware': 'N/A', 'inactive_firmware': 'N/A', 'e1_active_firmware': 'N/A', 'e1_inactive_firmware': 'N/A', 'e2_active_firmware': 'N/A', 'e2_inactive_firmware': 'N/A', 'e1_server_firmware': 'N/A', 'e2_server_firmware': 'N/A'}
        self.api.set_firmware_download_target_end = MagicMock(return_value=set_firmware_result)
        self.api.get_module_type = MagicMock(return_value=module_type)

        result = self.api.get_transceiver_info_firmware_versions()
        assert result == expected_output
        assert self.api.set_firmware_download_target_end.call_count == 4
        self.api._get_server_firmware_version.assert_not_called()

    @pytest.mark.parametrize("fw_info_dict, server_fw_info_dict, expected_output", [
        (({'active_firmware': '1.1.1', 'inactive_firmware': '1.0.0'}, {'active_firmware': '1.1.1', 'inactive_firmware': '1.0.0'}, {'active_firmware': '1.1.1', 'inactive_firmware': '1.0.0'}), ({'server_firmware': '1.5.0.1421'}, {'server_firmware': '1.5.0.1421'}),\
                {'active_firmware': '1.1.1', 'inactive_firmware': '1.0.0', 'e1_active_firmware': '1.1.1', 'e1_inactive_firmware': '1.0.0', 'e2_active_firmware': '1.1.1', 'e2_inactive_firmware': '1.0.0', 'e1_server_firmware': '1.5.0.1421', 'e2_server_firmware': '1.5.0.1421'}),
        (({'active_firmware': '1.1.1', 'inactive_firmware': '1.0.0'}, {'active_firmware': '2.1.1', 'inactive_firmware': '1.0.0'}, {'active_firmware': '1.1.1', 'inactive_firmware': '2.0.1'}), ({'server_firmware': '1223.6.0.739'}, {'server_firmware': '93.5.0.3431'}),\
                {'active_firmware': '1.1.1', 'inactive_firmware': '1.0.0', 'e1_active_firmware': '2.1.1', 'e1_inactive_firmware': '1.0.0', 'e2_active_firmware': '1.1.1', 'e2_inactive_firmware': '2.0.1', 'e1_server_firmware': '1223.6.0.739', 'e2_server_firmware': '93.5.0.3431'})
    ])
    def test_get_transceiver_info_firmware_versions_success(self, fw_info_dict, server_fw_info_dict, expected_output):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info_firmware_versions', side_effect=fw_info_dict):
            with patch('sonic_platform_base.sonic_xcvr.api.public.cmisTargetFWUpgrade.CmisTargetFWUpgradeAPI._get_server_firmware_version', side_effect=server_fw_info_dict):
                self.api.set_firmware_download_target_end = MagicMock(return_value=True)
                self.api.get_module_type = MagicMock(return_value='QSFP+ or later with CMIS')

                result = self.api.get_transceiver_info_firmware_versions()
                assert result == expected_output
                assert self.api.set_firmware_download_target_end.call_count == 4

    @pytest.mark.parametrize("magic_byte, checksum, server_fw_version_byte_array, expected", [
        (0, 0, [], {'server_firmware': 'N/A'}),
        (0, 0x98, [0, 0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 5, 0x8d], {'server_firmware': 'N/A'}), # Magic byte is 0 but other values are valid
        (0xAC, 0x98, [0, 0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 5, 0x8d], {'server_firmware': '1.5.0.1421'}),
        (0xff, 0xff, [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff], {'server_firmware': 'N/A'}),
        (0xAC, 0x98, [0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff], {'server_firmware': 'N/A'})
    ])
    def test_get_server_firmware_version(self, magic_byte, checksum, server_fw_version_byte_array, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = [magic_byte, checksum, server_fw_version_byte_array]

        result = self.api._get_server_firmware_version()
        assert result == expected
