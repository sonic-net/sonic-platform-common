"""
    bmc_fw_update_test.py

    Unit tests for bmc_fw_update module
"""

import sys
import pytest

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

try:
    from sonic_py_common import logger
except ImportError:
    sys.modules['sonic_py_common'] = mock.MagicMock()
    sys.modules['sonic_py_common.logger'] = mock.MagicMock()

from sonic_platform_base import bmc_fw_update


class TestBMCFWUpdate:
    """Test class for bmc_fw_update module"""

    @mock.patch('sys.exit')
    @mock.patch('sonic_py_common.logger.Logger')
    def test_main_success_bmc_firmware_updated(self, mock_logger_class, mock_exit):
        """Test successful firmware update with BMC firmware component updated"""
        mock_logger = mock.MagicMock()
        mock_bmc = mock.MagicMock()
        mock_chassis = mock.MagicMock()
        mock_platform = mock.MagicMock()
        mock_chassis.get_bmc.return_value = mock_bmc
        mock_platform.get_chassis.return_value = mock_chassis
        mock_sonic_platform = mock.MagicMock()
        mock_sonic_platform.platform.Platform.return_value = mock_platform
        mock_logger_class.return_value = mock_logger
        mock_bmc.update_firmware.return_value = (0, ('Success', ['BMC_FW_0', 'OTHER_FW']))
        mock_bmc.get_firmware_id.return_value = 'BMC_FW_0'
        mock_bmc.request_bmc_reset.return_value = (0, 'BMC reset successful')

        test_args = ['bmc_fw_update.py', '/path/to/firmware.bin']
        with mock.patch.dict(sys.modules, {'sonic_platform': mock_sonic_platform}):
            with mock.patch.object(sys, 'argv', test_args):
                bmc_fw_update.main()

        mock_logger_class.assert_called_once_with('bmc_fw_update')
        mock_chassis.get_bmc.assert_called_once()
        mock_bmc.update_firmware.assert_called_once_with('/path/to/firmware.bin')
        mock_bmc.get_firmware_id.assert_called_once()
        mock_bmc.request_bmc_reset.assert_called_once()
        mock_exit.assert_not_called()

    @mock.patch('sys.exit')
    @mock.patch('sonic_py_common.logger.Logger')
    def test_main_success_no_bmc_reset_needed(self, mock_logger_class, mock_exit):
        """Test successful firmware update without BMC reset"""
        mock_logger = mock.MagicMock()
        mock_bmc = mock.MagicMock()
        mock_chassis = mock.MagicMock()
        mock_platform = mock.MagicMock()
        mock_chassis.get_bmc.return_value = mock_bmc
        mock_platform.get_chassis.return_value = mock_chassis
        mock_sonic_platform = mock.MagicMock()
        mock_sonic_platform.platform.Platform.return_value = mock_platform
        mock_logger_class.return_value = mock_logger
        mock_bmc.update_firmware.return_value = (0, ('Success', ['OTHER_FW_1', 'OTHER_FW_2']))
        mock_bmc.get_firmware_id.return_value = 'BMC_FW_0'

        test_args = ['bmc_fw_update.py', '/path/to/firmware.bin']
        with mock.patch.dict(sys.modules, {'sonic_platform': mock_sonic_platform}):
            with mock.patch.object(sys, 'argv', test_args):
                bmc_fw_update.main()

        mock_bmc.update_firmware.assert_called_once_with('/path/to/firmware.bin')
        mock_bmc.get_firmware_id.assert_called_once()
        mock_bmc.request_bmc_reset.assert_not_called()
        mock_exit.assert_not_called()

    @mock.patch('sys.exit')
    @mock.patch('sonic_py_common.logger.Logger')
    def test_main_missing_arguments(self, mock_logger_class, mock_exit):
        """Test main with missing arguments"""
        mock_logger = mock.MagicMock()
        mock_sonic_platform = mock.MagicMock()
        mock_logger_class.return_value = mock_logger

        test_args = ['bmc_fw_update.py']
        with mock.patch.dict(sys.modules, {'sonic_platform': mock_sonic_platform}):
            with mock.patch.object(sys, 'argv', test_args):
                bmc_fw_update.main()

        mock_logger.log_error.assert_any_call("Missing firmware image path argument")
        mock_exit.assert_called_with(1)

    @mock.patch('sys.exit')
    @mock.patch('sonic_py_common.logger.Logger')
    def test_main_no_bmc_instance(self, mock_logger_class, mock_exit):
        """Test main when BMC instance is None"""
        mock_logger = mock.MagicMock()
        mock_chassis = mock.MagicMock()
        mock_platform = mock.MagicMock()
        mock_chassis.get_bmc.return_value = None
        mock_platform.get_chassis.return_value = mock_chassis
        mock_sonic_platform = mock.MagicMock()
        mock_sonic_platform.platform.Platform.return_value = mock_platform
        mock_logger_class.return_value = mock_logger

        test_args = ['bmc_fw_update.py', '/path/to/firmware.bin']
        with mock.patch.dict(sys.modules, {'sonic_platform': mock_sonic_platform}):
            with mock.patch.object(sys, 'argv', test_args):
                bmc_fw_update.main()

        mock_logger.log_error.assert_any_call("Failed to get BMC instance from chassis")
        mock_exit.assert_called_with(1)

    @mock.patch('sys.exit')
    @mock.patch('sonic_py_common.logger.Logger')
    def test_main_update_firmware_failure(self, mock_logger_class, mock_exit):
        """Test main when firmware update fails"""
        mock_logger = mock.MagicMock()
        mock_bmc = mock.MagicMock()
        mock_chassis = mock.MagicMock()
        mock_platform = mock.MagicMock()
        mock_chassis.get_bmc.return_value = mock_bmc
        mock_platform.get_chassis.return_value = mock_chassis
        mock_sonic_platform = mock.MagicMock()
        mock_sonic_platform.platform.Platform.return_value = mock_platform
        mock_logger_class.return_value = mock_logger
        mock_bmc.update_firmware.return_value = (1, ('Update failed', []))

        test_args = ['bmc_fw_update.py', '/path/to/firmware.bin']
        with mock.patch.dict(sys.modules, {'sonic_platform': mock_sonic_platform}):
            with mock.patch.object(sys, 'argv', test_args):
                bmc_fw_update.main()

        mock_logger.log_error.assert_called_once_with('Failed to update BMC firmware. Error 1: Update failed')
        mock_exit.assert_called_once_with(1)

    @mock.patch('sys.exit')
    @mock.patch('sonic_py_common.logger.Logger')
    def test_main_bmc_reset_failure(self, mock_logger_class, mock_exit):
        """Test main when BMC reset fails"""
        mock_logger = mock.MagicMock()
        mock_bmc = mock.MagicMock()
        mock_chassis = mock.MagicMock()
        mock_platform = mock.MagicMock()
        mock_chassis.get_bmc.return_value = mock_bmc
        mock_platform.get_chassis.return_value = mock_chassis
        mock_sonic_platform = mock.MagicMock()
        mock_sonic_platform.platform.Platform.return_value = mock_platform
        mock_logger_class.return_value = mock_logger
        mock_bmc.update_firmware.return_value = (0, ('Success', ['BMC_FW_0']))
        mock_bmc.get_firmware_id.return_value = 'BMC_FW_0'
        mock_bmc.request_bmc_reset.return_value = (1, 'Reset failed')

        test_args = ['bmc_fw_update.py', '/path/to/firmware.bin']
        with mock.patch.dict(sys.modules, {'sonic_platform': mock_sonic_platform}):
            with mock.patch.object(sys, 'argv', test_args):
                bmc_fw_update.main()

        mock_logger.log_error.assert_called_once_with('Failed to restart BMC. Error 1: Reset failed')
        mock_exit.assert_called_once_with(1)
