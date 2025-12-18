"""
    bmc_base_test.py

    Unit tests for BMCBase class
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

from sonic_platform_base.bmc_base import BMCBase
from sonic_platform_base.redfish_client import RedfishClient


class TestBMCBase:
    """Test class for BMCBase"""

    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError"""
        bmc = BMCBase('169.254.0.1')
        
        not_implemented_methods = [
            [bmc._get_login_user_callback, [], {}],
            [bmc._get_login_password_callback, [], {}],
            [bmc._get_default_root_password, [], {}],
            [bmc.get_firmware_id, [], {}],
            [bmc._get_eeprom_id, [], {}],
        ]

        for method in not_implemented_methods:
            exception_raised = False
            try:
                func = method[0]
                args = method[1]
                kwargs = method[2]
                func(*args, **kwargs)
            except NotImplementedError:
                exception_raised = True

            assert exception_raised

    def test_get_name(self):
        """Test get_name method"""
        bmc = BMCBase('169.254.0.1')
        assert bmc.get_name() == BMCBase.BMC_NAME

    def test_get_presence_true(self):
        """Test get_presence returns True when BMC data is present"""
        with mock.patch('sonic_py_common.device_info.get_bmc_data', create=True, return_value={'bmc_addr': '169.254.0.1'}):
            bmc = BMCBase('169.254.0.1')
            assert bmc.get_presence() == True

    def test_get_presence_false(self):
        """Test get_presence returns False when BMC data is not present"""
        with mock.patch('sonic_py_common.device_info.get_bmc_data', create=True, return_value=None):
            bmc = BMCBase('169.254.0.1')
            assert bmc.get_presence() == False

    def test_is_replaceable(self):
        """Test is_replaceable returns False"""
        bmc = BMCBase('169.254.0.1')
        assert bmc.is_replaceable() == False

    def test_get_revision(self):
        """Test get_revision returns N/A"""
        bmc = BMCBase('169.254.0.1')
        assert bmc.get_revision() == 'N/A'

    @mock.patch('subprocess.check_output')
    def test_get_status_true(self, mock_subprocess):
        """Test get_status returns True when ping succeeds"""
        mock_subprocess.return_value = b''
        
        with mock.patch.object(BMCBase, 'get_presence', return_value=True):
            bmc = BMCBase('169.254.0.1')
            assert bmc.get_status() == True

    @mock.patch('subprocess.check_output')
    def test_get_status_false_ping_fail(self, mock_subprocess):
        """Test get_status returns False when ping fails"""
        import subprocess
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, 'ping')
        
        with mock.patch.object(BMCBase, 'get_presence', return_value=True):
            bmc = BMCBase('169.254.0.1')
            assert bmc.get_status() == False

    def test_get_status_false_not_present(self):
        """Test get_status returns False when BMC is not present"""
        with mock.patch.object(BMCBase, 'get_presence', return_value=False):
            bmc = BMCBase('169.254.0.1')
            assert bmc.get_status() == False

    def test_get_ip_addr(self):
        """Test _get_ip_addr returns the correct address"""
        bmc = BMCBase('169.254.0.1')
        assert bmc._get_ip_addr() == '169.254.0.1'

    @mock.patch.object(RedfishClient, 'has_login')
    @mock.patch.object(RedfishClient, 'login')
    def test_login_already_logged_in(self, mock_login, mock_has_login):
        """Test _login when already logged in"""
        mock_has_login.return_value = True
        
        bmc = BMCBase('169.254.0.1')
        ret = bmc._login()
        
        assert ret == RedfishClient.ERR_CODE_OK
        mock_login.assert_not_called()

    @mock.patch.object(RedfishClient, 'has_login')
    @mock.patch.object(RedfishClient, 'login')
    def test_login_not_logged_in(self, mock_login, mock_has_login):
        """Test _login when not logged in"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        
        bmc = BMCBase('169.254.0.1')
        ret = bmc._login()
        
        assert ret == RedfishClient.ERR_CODE_OK
        mock_login.assert_called_once()

    @mock.patch.object(RedfishClient, 'has_login')
    @mock.patch.object(RedfishClient, 'logout')
    def test_logout_logged_in(self, mock_logout, mock_has_login):
        """Test _logout when logged in"""
        mock_has_login.return_value = True
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        
        bmc = BMCBase('169.254.0.1')
        ret = bmc._logout()
        
        assert ret == RedfishClient.ERR_CODE_OK
        mock_logout.assert_called_once()

    @mock.patch.object(RedfishClient, 'has_login')
    @mock.patch.object(RedfishClient, 'logout')
    def test_logout_not_logged_in(self, mock_logout, mock_has_login):
        """Test _logout when not logged in"""
        mock_has_login.return_value = False
        
        bmc = BMCBase('169.254.0.1')
        ret = bmc._logout()
        
        assert ret == RedfishClient.ERR_CODE_OK
        mock_logout.assert_not_called()

    def test_is_bmc_eeprom_content_valid_empty(self):
        """Test _is_bmc_eeprom_content_valid with empty data"""
        bmc = BMCBase('169.254.0.1')
        assert bmc._is_bmc_eeprom_content_valid(None) == False
        assert bmc._is_bmc_eeprom_content_valid({}) == False

    def test_is_bmc_eeprom_content_valid_error(self):
        """Test _is_bmc_eeprom_content_valid with error"""
        bmc = BMCBase('169.254.0.1')
        eeprom_info = {'error': 'Some error'}
        assert bmc._is_bmc_eeprom_content_valid(eeprom_info) == False

    def test_is_bmc_eeprom_content_valid_success(self):
        """Test _is_bmc_eeprom_content_valid with valid data"""
        bmc = BMCBase('169.254.0.1')
        eeprom_info = {'Model': 'P3809', 'SerialNumber': '123456'}
        assert bmc._is_bmc_eeprom_content_valid(eeprom_info) == True


class ConcreteBMC(BMCBase):
    """Concrete implementation of BMCBase for testing"""
    
    def _get_login_user_callback(self):
        return 'testuser'
    
    def _get_login_password_callback(self):
        return 'testpass'
    
    def _get_default_root_password(self):
        return 'rootpass'
    
    def get_firmware_id(self):
        return 'BMC_FW_0'
    
    def _get_eeprom_id(self):
        return 'BMC_eeprom'


class TestBMCBaseWithConcrete:
    """Test BMCBase methods that require concrete implementation"""

    @mock.patch.object(RedfishClient, 'redfish_api_get_firmware_version')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_version_success(self, mock_has_login, mock_logout, mock_login, mock_get_fw_version):
        """Test get_version with successful version retrieval"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_fw_version.return_value = (RedfishClient.ERR_CODE_OK, 'V.88.0002.0500')
        
        bmc = ConcreteBMC('169.254.0.1')
        version = bmc.get_version()
        
        assert version == 'V.88.0002.0500'
        mock_get_fw_version.assert_called_once_with('BMC_FW_0')

    @mock.patch.object(RedfishClient, 'redfish_api_get_firmware_version')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_version_failure(self, mock_has_login, mock_logout, mock_login, mock_get_fw_version):
        """Test get_version with failure"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_fw_version.return_value = (RedfishClient.ERR_CODE_GENERIC_ERROR, 'N/A')
        
        bmc = ConcreteBMC('169.254.0.1')
        version = bmc.get_version()
        
        assert version == 'N/A'

    @mock.patch.object(RedfishClient, 'redfish_api_get_firmware_version')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_version_exception(self, mock_has_login, mock_logout, mock_login, mock_get_fw_version):
        """Test get_version with exception"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_fw_version.side_effect = Exception("Test exception")
        
        bmc = ConcreteBMC('169.254.0.1')
        version = bmc.get_version()
        
        assert version == 'N/A'

    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_eeprom_success(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom):
        """Test get_eeprom with successful retrieval"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        eeprom_data = {'Model': 'P3809', 'SerialNumber': '123456'}
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_OK, eeprom_data)
        
        bmc = ConcreteBMC('169.254.0.1')
        result = bmc.get_eeprom()
        
        assert result == eeprom_data
        mock_get_eeprom.assert_called_once_with('BMC_eeprom')

    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_eeprom_failure(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom):
        """Test get_eeprom with failure"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_GENERIC_ERROR, {})
        
        bmc = ConcreteBMC('169.254.0.1')
        result = bmc.get_eeprom()
        
        assert result == {}

    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_eeprom_exception(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom):
        """Test get_eeprom with exception"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_eeprom.side_effect = Exception("Test exception")
        
        bmc = ConcreteBMC('169.254.0.1')
        result = bmc.get_eeprom()
        
        assert result == {}

    def test_wrapper_rf_client_none_exception(self):
        """Test wrapper raises exception when RedfishClient instance is None"""
        bmc = ConcreteBMC('169.254.0.1')
        
        with mock.patch.object(bmc, '_login') as mock_login:
            with mock.patch.object(bmc, '_logout', return_value=RedfishClient.ERR_CODE_OK):
                def login_side_effect():
                    if bmc.rf_client is None:
                        raise Exception('RedfishClient instance is None')
                    return RedfishClient.ERR_CODE_OK
                
                mock_login.side_effect = login_side_effect
                bmc.rf_client = None
                
                ret, data = bmc.trigger_bmc_debug_log_dump()
                
                assert ret == RedfishClient.ERR_CODE_GENERIC_ERROR
                assert 'RedfishClient instance is None' in str(data)

    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_model(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom):
        """Test get_model"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        eeprom_data = {'Model': 'P3809', 'SerialNumber': '123456'}
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_OK, eeprom_data)
        
        bmc = ConcreteBMC('169.254.0.1')
        model = bmc.get_model()
        
        assert model == 'P3809'

    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_model_returns_none(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom):
        """Test get_model returns None when EEPROM is invalid"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_GENERIC_ERROR, {})
        
        bmc = ConcreteBMC('169.254.0.1')
        model = bmc.get_model()
        
        assert model is None

    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_serial(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom):
        """Test get_serial"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        eeprom_data = {'Model': 'P3809', 'SerialNumber': '123456'}
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_OK, eeprom_data)
        
        bmc = ConcreteBMC('169.254.0.1')
        serial = bmc.get_serial()
        
        assert serial == '123456'

    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_serial_returns_none(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom):
        """Test get_serial returns None when EEPROM is invalid"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_OK, {})
        
        bmc = ConcreteBMC('169.254.0.1')
        serial = bmc.get_serial()
        
        assert serial is None

    @mock.patch.object(RedfishClient, 'redfish_api_update_firmware')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_update_firmware_success(self, mock_has_login, mock_logout, mock_login, mock_update_fw):
        """Test update_firmware with success"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_update_fw.return_value = (RedfishClient.ERR_CODE_OK, 'Update successful', ['BMC_FW_0'])
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, (msg, updated_components) = bmc.update_firmware('test_image.bin')
        
        assert ret == RedfishClient.ERR_CODE_OK
        assert msg == 'Update successful'
        assert updated_components == ['BMC_FW_0']
        mock_update_fw.assert_called_once_with('test_image.bin', fw_ids=['BMC_FW_0'])

    @mock.patch.object(RedfishClient, 'redfish_api_trigger_bmc_debug_log_dump')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_trigger_bmc_debug_log_dump(self, mock_has_login, mock_logout, mock_login, mock_trigger):
        """Test trigger_bmc_debug_log_dump"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_trigger.return_value = (RedfishClient.ERR_CODE_OK, ('task_123', None))
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, (task_id, err_msg) = bmc.trigger_bmc_debug_log_dump()
        
        assert ret == RedfishClient.ERR_CODE_OK
        assert task_id == 'task_123'
        assert err_msg is None

    @mock.patch.object(RedfishClient, 'redfish_api_get_bmc_debug_log_dump')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_bmc_debug_log_dump(self, mock_has_login, mock_logout, mock_login, mock_get_dump):
        """Test get_bmc_debug_log_dump"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_dump.return_value = (RedfishClient.ERR_CODE_OK, '')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, err_msg = bmc.get_bmc_debug_log_dump('task_123', 'dump.tar', '/tmp', 60)
        
        assert ret == RedfishClient.ERR_CODE_OK
        mock_get_dump.assert_called_once_with('task_123', 'dump.tar', '/tmp', 60)

    @mock.patch.object(RedfishClient, 'redfish_api_request_bmc_reset')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_request_bmc_reset_graceful(self, mock_has_login, mock_logout, mock_login, mock_reset):
        """Test request_bmc_reset with graceful=True"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_reset.return_value = (RedfishClient.ERR_CODE_OK, '')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, msg = bmc.request_bmc_reset(graceful=True)
        
        assert ret == RedfishClient.ERR_CODE_OK
        mock_reset.assert_called_once_with(RedfishClient.REDFISH_BMC_GRACEFUL_RESTART)

    @mock.patch.object(RedfishClient, 'redfish_api_change_login_password')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_reset_root_password(self, mock_has_login, mock_logout, mock_login, mock_change_pw):
        """Test reset_root_password"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_change_pw.return_value = (RedfishClient.ERR_CODE_OK, 'Password changed')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, msg = bmc.reset_root_password()
        
        assert ret == RedfishClient.ERR_CODE_OK
        assert msg == 'Password changed'
        mock_change_pw.assert_called_once_with('rootpass', BMCBase.ROOT_ACCOUNT)

