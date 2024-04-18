from unittest.mock import patch
from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.api.public.cmisTargetFWUpgrade import TARGET_E0_VALUE, TARGET_LIST, CmisTargetFWUpgradeAPI
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

    @pytest.mark.parametrize("set_firmware_result, module_type, exception_raised", [
        (False, 'QSFP+ or later with CMIS', False),
        (True, 'Unknown', False),
        (True, 'QSFP+ or later with CMIS', True)
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info_firmware_versions', MagicMock(side_effect=({}, Exception('error'), {})))
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmisTargetFWUpgrade.CmisTargetFWUpgradeAPI._get_server_firmware_version', MagicMock())
    @patch('traceback.format_exception')
    def test_get_transceiver_info_firmware_versions_failure(self, mock_format_exception, set_firmware_result, module_type, exception_raised):
        expected_output = {'active_firmware': 'N/A', 'inactive_firmware': 'N/A', 'e1_active_firmware': 'N/A',\
                            'e1_inactive_firmware': 'N/A', 'e2_active_firmware': 'N/A', 'e2_inactive_firmware': 'N/A',\
                            'e1_server_firmware': 'N/A', 'e2_server_firmware': 'N/A'}
        self.api.set_firmware_download_target_end = MagicMock(return_value=set_firmware_result)
        self.api.get_module_type = MagicMock(return_value=module_type)

        result = self.api.get_transceiver_info_firmware_versions()
        assert result == expected_output

        assert self.api.set_firmware_download_target_end.call_count == len(TARGET_LIST) + 1
        # Ensure that FW version is read for all targets
        for index, call in enumerate(self.api.set_firmware_download_target_end.call_args_list):
            args, _ = call
            # Ensure target is restore to E0 after reading FW version from all targets
            if index == len(TARGET_LIST):
                assert args[0] == TARGET_E0_VALUE
            else:
                assert args[0] == TARGET_LIST[index]

        if exception_raised:
            assert mock_format_exception.call_count == 1
            assert self.api._get_server_firmware_version.call_count == 1
        else:
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
                assert self.api.set_firmware_download_target_end.call_count == len(TARGET_LIST) + 1

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
