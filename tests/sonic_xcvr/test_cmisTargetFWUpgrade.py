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

    @pytest.mark.parametrize("target,write_results,accessible,exception,expected_result", [
        (1, [False, True, True, True], True, None, False),  # Failed to set target mode
        (1, [True, False, True, True], True, None, False),  # Failed to set page select byte
        (1, [True, True, True, True], False, None, False),  # Remote target not accessible
        (1, [True, True, True, True], True, Exception("Simulated exception"), False),  # Exception occurred
        (1, [True, True, True, True], True, None, True),    # All operations successful
        (0, [True, True, True, True], True, None, True),    # Target is E0, all operations successful
    ])
    def test_set_firmware_download_target_end(self, target, write_results, accessible, exception, expected_result):
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.write.side_effect = write_results
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmisTargetFWUpgrade.CmisTargetFWUpgradeAPI._is_remote_target_accessible', return_value=accessible):
            with patch('sonic_platform_base.sonic_xcvr.api.public.cmisTargetFWUpgrade.CmisTargetFWUpgradeAPI._restore_target_to_E0', return_value=False):
                if exception is not None:
                    self.api.xcvr_eeprom.write.side_effect = exception

                result = self.api.set_firmware_download_target_end(target)
                assert result == expected_result
                if result:
                    expected_call_count = 0
                else:
                    expected_call_count = 1
                assert self.api._restore_target_to_E0.call_count == expected_call_count

    @pytest.mark.parametrize("set_firmware_result, exception_raised", [
        (False, False),
        (True, True)
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info_firmware_versions', MagicMock(side_effect=({}, Exception('error'), {})))
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmisTargetFWUpgrade.CmisTargetFWUpgradeAPI._get_server_firmware_version', MagicMock())
    @patch('traceback.format_exception')
    def test_get_transceiver_info_firmware_versions_failure(self, mock_format_exception, set_firmware_result, exception_raised):
        expected_output = {'active_firmware': 'N/A', 'inactive_firmware': 'N/A', 'e1_active_firmware': 'N/A',\
                            'e1_inactive_firmware': 'N/A', 'e2_active_firmware': 'N/A', 'e2_inactive_firmware': 'N/A',\
                            'e1_server_firmware': 'N/A', 'e2_server_firmware': 'N/A'}
        self.api.set_firmware_download_target_end = MagicMock(return_value=set_firmware_result)

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

                result = self.api.get_transceiver_info_firmware_versions()
                assert result == expected_output
                assert self.api.set_firmware_download_target_end.call_count == len(TARGET_LIST) + 1

    @pytest.mark.parametrize("module_type, expected_result", [
        ('Unknown', False),
        ('QSFP+ or later with CMIS', True)
    ])
    def test_is_remote_target_accessible(self, module_type, expected_result):
        # Mock the get_module_type method to return the parameterized module_type
        self.api.get_module_type = MagicMock(return_value=module_type)

        # Call the method and check the result
        result = self.api._is_remote_target_accessible()
        assert result == expected_result

    def test_restore_target_to_E0(self):
        self.api.xcvr_eeprom.write = MagicMock()
        assert self.api._restore_target_to_E0() == False
        self.api.xcvr_eeprom.write.assert_called_once()


    @pytest.mark.parametrize("magic_byte, checksum, server_fw_version_byte_array, expected", [
        (0, 0, (), {'server_firmware': 'N/A'}),
        (0, 0x98, [0, 0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 5, 0x8d], {'server_firmware': 'N/A'}), # Magic byte is 0 but other values are valid
        (0xAC, 0x98, ([0, 0, 0, 1, 0, 0, 0, 5, 0, 0, 0, 0, 0, 0, 5, 0x8d], "1.5.0.1421"), {'server_firmware': '1.5.0.1421'}),
        (0xff, 0xff, ([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff], "N/A"), {'server_firmware': 'N/A'}),
        (0xAC, 0x98, ([0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff], "N/A"), {'server_firmware': 'N/A'})
    ])
    def test_get_server_firmware_version(self, magic_byte, checksum, server_fw_version_byte_array, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = [magic_byte, checksum, server_fw_version_byte_array]

        result = self.api._get_server_firmware_version()
        assert result == expected
