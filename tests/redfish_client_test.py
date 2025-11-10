"""
    redfish_client_test.py

    Unit tests for RedfishClient class
"""

import os
import pytest
import sys
import json

if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

try:
    from sonic_py_common import logger
except ImportError:
    sys.modules['sonic_py_common'] = mock.MagicMock()
    sys.modules['sonic_py_common.logger'] = mock.MagicMock()

from sonic_platform_base.redfish_client import RedfishClient


test_path = os.path.dirname(os.path.abspath(__file__))


def load_redfish_response(fname):
    """Load mock redfish response from file"""
    if not fname:
        return b''
    fpath = os.path.join(test_path, 'mock_data', fname)
    with open(fpath, 'r') as file:
        content = file.read()
    return bytes(f'{content}', 'utf-8')


class TestRedfishClient:
    """Test class for RedfishClient"""
    
    CURL_PATH = '/usr/bin/curl'
    BMC_INTERNAL_IP_ADDR = '169.254.0.1'
    BMC_NOS_ACCOUNT = 'testuser'
    BMC_NOS_ACCOUNT_DEFAULT_PASSWORD = "TestPass123!"

    def user_callback(self):
        return TestRedfishClient.BMC_NOS_ACCOUNT

    def password_callback(self):
        return TestRedfishClient.BMC_NOS_ACCOUNT_DEFAULT_PASSWORD

    @mock.patch('subprocess.Popen')
    def test_login_success(self, mock_popen):
        """Test successful login"""
        side_effects = []
        for fname in ['mock_bmc_login_token_response', \
            'mock_bmc_logout_response']:
            output = (load_redfish_response(fname), b'')
            mock_process = mock.Mock()
            mock_process.communicate.return_value = output
            mock_process.returncode = 0
            side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        assert rf.get_login_token() is not None

        ret = rf.logout()
        assert ret == RedfishClient.ERR_CODE_OK
        assert rf.get_login_token() is None

    @mock.patch('subprocess.Popen')
    def test_login_failure_bad_credential(self, mock_popen):
        """Test login failure with bad credentials"""
        output = (load_redfish_response('mock_bmc_empty_response_auth_failure'), b'')
        mock_popen.return_value.communicate.return_value = output
        mock_popen.return_value.returncode = 0
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_AUTH_FAILURE
        assert rf.get_login_token() is None
    
    @mock.patch('subprocess.Popen')
    def test_get_bmc_version(self, mock_popen):
        """Test getting BMC firmware version"""
        side_effects = []
        for fname in ['mock_bmc_login_token_response', \
            'mock_get_bmc_info_response']:
            output = (load_redfish_response(fname), b'')
            mock_process = mock.Mock()
            mock_process.communicate.return_value = output
            mock_process.returncode = 0
            side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        assert rf.get_login_token() is not None

        ret, version = rf.redfish_api_get_firmware_version('TEST_FW_BMC_0')
        assert ret == RedfishClient.ERR_CODE_OK
        assert version == 'V.88.0002.0500-04'
    
    @mock.patch('subprocess.Popen')
    def test_change_bmc_login_password_root_user_success(self, mock_popen):
        """Test changing BMC login password for root user"""
        side_effects = []
        for fname in ['mock_bmc_login_token_response', \
            'mock_change_bmc_login_password_success_response', \
            'mock_bmc_logout_response', \
            'mock_bmc_login_token_response']:
            output = (load_redfish_response(fname), b'')
            mock_process = mock.Mock()
            mock_process.communicate.return_value = output
            mock_process.returncode = 0
            side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        assert rf.get_login_token() is not None

        ret, err_msg = rf.redfish_api_change_login_password('0penBmcTempPass!', 'root')
        assert ret == RedfishClient.ERR_CODE_OK
    
    @mock.patch('subprocess.Popen')
    def test_trigger_bmc_debug_log_dump_success(self, mock_popen):
        """Test triggering BMC debug log dump"""
        side_effects = []
        for fname in ['mock_bmc_login_token_response', \
            'mock_bmc_debug_log_dump_response']:
            output = (load_redfish_response(fname), b'')
            mock_process = mock.Mock()
            mock_process.communicate.return_value = output
            mock_process.returncode = 0
            side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        assert rf.get_login_token() is not None

        ret, _ = rf.redfish_api_trigger_bmc_debug_log_dump()
        assert ret == RedfishClient.ERR_CODE_OK

    @mock.patch('subprocess.Popen')
    def test_get_bmc_debug_log_dump_success(self, mock_popen):
        """Test getting BMC debug log dump"""
        side_effects = []
        for fname in ['mock_bmc_login_token_response', \
            'mock_bmc_task_query_valid_debug_log_dump',
            'mock_bmc_empty_response']:
            output = (load_redfish_response(fname), b'')
            mock_process = mock.Mock()
            mock_process.communicate.return_value = output
            mock_process.returncode = 0
            side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        assert rf.get_login_token() is not None

        ret, msg = rf.redfish_api_get_bmc_debug_log_dump(task_id='0', filename='test.tar.xz', file_path='/tmp')
        assert ret == RedfishClient.ERR_CODE_OK
    
    @mock.patch('subprocess.Popen')
    def test_get_bmc_eeprom(self, mock_popen):
        """Test getting BMC EEPROM information"""
        side_effects = []
        for fname in ['mock_bmc_login_token_response', \
            'mock_get_bmc_eeprom_response']:
            output = (load_redfish_response(fname), b'')
            mock_process = mock.Mock()
            mock_process.communicate.return_value = output
            mock_process.returncode = 0
            side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        assert rf.get_login_token() is not None

        ret, eeprom_content = rf.redfish_api_get_eeprom_info('BMC_eeprom')
        
        eeprom_dict_file_path = os.path.join(test_path, 'mock_data', 'mock_parsed_bmc_eeprom_dict')
        with open(eeprom_dict_file_path, 'r') as f:
            data = f.read()
            expected_bmc_eeprom_dict_output = json.loads(data)

        assert ret == RedfishClient.ERR_CODE_OK
        assert expected_bmc_eeprom_dict_output == eeprom_content

    @mock.patch('subprocess.Popen')
    def test_has_login(self, mock_popen):
        """Test has_login method"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        assert rf.has_login() == False
        
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_popen.return_value.communicate.return_value = output
        mock_popen.return_value.returncode = 0
        
        rf.login()
        assert rf.has_login() == True

    def test_invalidate_session(self):
        """Test invalidate_session method"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.invalidate_session()
        assert rf.get_login_token() is None
        assert rf.get_session_id() is None

    @mock.patch('subprocess.Popen')
    def test_login_empty_response(self, mock_popen):
        """Test login with empty response"""
        output = (b'HTTP Status Code: 200', b'')
        mock_popen.return_value.communicate.return_value = output
        mock_popen.return_value.returncode = 0
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE

    @mock.patch('subprocess.Popen')
    def test_logout_empty_response(self, mock_popen):
        """Test logout with empty response"""
        side_effects = []
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (b'HTTP Status Code: 200', b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        ret = rf.logout()
        assert ret == RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE

    @mock.patch('subprocess.Popen')
    def test_redfish_api_get_firmware_list(self, mock_popen):
        """Test get_firmware_list"""
        side_effects = []
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_get_firmware_list_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_get_bmc_info_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_get_bmc_info_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        
        ret, fw_list = rf.redfish_api_get_firmware_list()
        assert ret == RedfishClient.ERR_CODE_OK
        assert isinstance(fw_list, list)
        assert len(fw_list) == 2

    @mock.patch('subprocess.Popen')
    def test_redfish_api_get_eeprom_list(self, mock_popen):
        """Test get_eeprom_list"""
        side_effects = []
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_get_eeprom_list_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_get_bmc_eeprom_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_get_bmc_eeprom_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        
        ret, eeprom_list = rf.redfish_api_get_eeprom_list()
        assert ret == RedfishClient.ERR_CODE_OK
        assert isinstance(eeprom_list, list)
        assert len(eeprom_list) == 2

    @mock.patch('subprocess.Popen')
    def test_redfish_api_request_bmc_reset(self, mock_popen):
        """Test request_bmc_reset"""
        side_effects = []
        for fname in ['mock_bmc_login_token_response', \
            'mock_bmc_empty_response']:
            output = (load_redfish_response(fname), b'')
            mock_process = mock.Mock()
            mock_process.communicate.return_value = output
            mock_process.returncode = 0
            side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        
        ret, msg = rf.redfish_api_request_bmc_reset(RedfishClient.REDFISH_BMC_GRACEFUL_RESTART)
        assert ret == RedfishClient.ERR_CODE_OK

    @mock.patch('subprocess.Popen')
    def test_redfish_api_update_firmware(self, mock_popen):
        """Test update_firmware"""
        side_effects = []
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_firmware_update_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_firmware_update_task_complete'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        
        ret, msg = rf.redfish_api_update_firmware('/tmp/test.bin', fw_ids=['BMC_FW_0'], force_update=True)
        assert ret == RedfishClient.ERR_CODE_OK

    @mock.patch('subprocess.Popen')
    def test_redfish_api_update_firmware_no_fw_ids(self, mock_popen):
        """Test update_firmware without fw_ids"""
        side_effects = []
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_firmware_update_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output = (load_redfish_response('mock_firmware_update_task_complete'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        
        ret, msg = rf.redfish_api_update_firmware('/tmp/test.bin', fw_ids=None, force_update=False)
        assert ret == RedfishClient.ERR_CODE_OK

    @mock.patch('subprocess.Popen')
    def test_change_password_with_user(self, mock_popen):
        """Test change password with specific user"""
        side_effects = []
        for fname in ['mock_bmc_login_token_response', \
            'mock_change_bmc_login_password_success_response']:
            output = (load_redfish_response(fname), b'')
            mock_process = mock.Mock()
            mock_process.communicate.return_value = output
            mock_process.returncode = 0
            side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        
        ret, msg = rf.redfish_api_change_login_password('newpass', user='root')
        assert ret == RedfishClient.ERR_CODE_OK

    @mock.patch('subprocess.Popen')
    def test_change_password_with_none_user(self, mock_popen):
        """Test change password with None user (uses default)"""
        side_effects = []
        for fname in ['mock_bmc_login_token_response', \
            'mock_change_bmc_login_password_success_response']:
            output = (load_redfish_response(fname), b'')
            mock_process = mock.Mock()
            mock_process.communicate.return_value = output
            mock_process.returncode = 0
            side_effects.append(mock_process)

        mock_popen.side_effect = side_effects
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)

        ret = rf.login()
        assert ret == RedfishClient.ERR_CODE_OK
        
        ret, msg = rf.redfish_api_change_login_password('newpass', user=None)
        assert ret == RedfishClient.ERR_CODE_OK

    def test_curl_errors_to_redfish_errors_translation(self):
        """Test curl error code translation"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        assert rf._RedfishClient__curl_errors_to_redfish_errors_translation(0) == RedfishClient.ERR_CODE_OK
        assert rf._RedfishClient__curl_errors_to_redfish_errors_translation(6) == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        assert rf._RedfishClient__curl_errors_to_redfish_errors_translation(7) == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        assert rf._RedfishClient__curl_errors_to_redfish_errors_translation(28) == RedfishClient.ERR_CODE_TIMEOUT
        assert rf._RedfishClient__curl_errors_to_redfish_errors_translation(35) == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        
        assert rf._RedfishClient__curl_errors_to_redfish_errors_translation(99) == RedfishClient.ERR_CODE_CURL_FAILURE

    def test_update_token_in_command(self):
        """Test updating token in command"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf._RedfishClient__token = 'new_token_123'
        cmd = '/usr/bin/curl -k -H "X-Auth-Token: old_token" https://169.254.0.1/test'
        new_cmd = rf._RedfishClient__update_token_in_command(cmd)
        
        assert 'X-Auth-Token: new_token_123' in new_cmd
        assert 'old_token' not in new_cmd

    def test_validate_message_args_valid(self):
        """Test validate_message_args with valid message"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.UpdateSuccessful',
            'MessageArgs': ['arg1', 'arg2']
        }
        
        is_valid, err_msg = rf._RedfishClient__validate_message_args(event_msg)
        assert is_valid == True
        assert err_msg == ''

    def test_validate_message_args_missing_args(self):
        """Test validate_message_args with missing MessageArgs"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.UpdateSuccessful'
        }
        
        is_valid, err_msg = rf._RedfishClient__validate_message_args(event_msg)
        assert is_valid == False
        assert 'Missing' in err_msg

    def test_validate_message_args_insufficient_args(self):
        """Test validate_message_args with insufficient MessageArgs"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.UpdateSuccessful',
            'MessageArgs': ['arg1']
        }
        
        is_valid, err_msg = rf._RedfishClient__validate_message_args(event_msg)
        assert is_valid == False
        assert 'less than 2' in err_msg

    def test_update_successful_handler(self):
        """Test update successful handler"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.UpdateSuccessful',
            'MessageArgs': ['BMC_FW_0', 'Success']
        }
        context = {}
        
        ret, err_msg = rf._RedfishClient__update_successful_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_OK
        assert err_msg == ''

    def test_component_update_skipped_handler(self):
        """Test component update skipped handler"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.ComponentUpdateSkipped',
            'MessageArgs': ['BMC_FW_0', 'Identical version']
        }
        context = {}
        
        ret, err_msg = rf._RedfishClient__component_update_skipped_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_OK
        assert context.get('identical_version') == True

    def test_resource_errors_detected_handler_lower_version(self):
        """Test resource errors detected handler with lower version"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected',
            'MessageArgs': ['BMC_FW_0', 'Version is lower than the firmware component comparison stamp']
        }
        context = {}
        
        ret, err_msg = rf._RedfishClient__resource_errors_detected_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_OK
        assert context.get('lower_version') == True
        assert context.get('err_detected') == True

    def test_resource_errors_detected_handler_identical_version(self):
        """Test resource errors detected handler with identical version"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected',
            'MessageArgs': ['BMC_FW_0', 'Component image is identical to the current version']
        }
        context = {}
        
        ret, err_msg = rf._RedfishClient__resource_errors_detected_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_OK
        assert context.get('identical_version') == True
        assert context.get('err_detected', False) == False

    def test_resource_errors_detected_handler_generic_error(self):
        """Test resource errors detected handler with generic error"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected',
            'MessageArgs': ['BMC_FW_0', 'Some generic error message']
        }
        context = {}
        
        ret, err_msg = rf._RedfishClient__resource_errors_detected_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_OK
        assert context.get('err_detected') == True
        assert 'Some generic error message' in context.get('ret_msg', '')

    def test_resource_errors_detected_handler_duplicate_error(self):
        """Test resource errors detected handler doesn't duplicate error messages"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected',
            'MessageArgs': ['BMC_FW_0', 'Duplicate error']
        }
        context = {'ret_msg': 'Error: Duplicate error\n'}
        
        ret, err_msg = rf._RedfishClient__resource_errors_detected_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_OK
        assert context['ret_msg'].count('Duplicate error') == 1

    def test_update_successful_handler_invalid(self):
        """Test update successful handler with invalid message"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.UpdateSuccessful'
        }
        context = {}
        
        ret, err_msg = rf._RedfishClient__update_successful_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
        assert 'Missing' in err_msg

    def test_component_update_skipped_handler_invalid(self):
        """Test component update skipped handler with invalid message"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.ComponentUpdateSkipped',
            'MessageArgs': ['only_one']
        }
        context = {}
        
        ret, err_msg = rf._RedfishClient__component_update_skipped_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
        assert 'less than 2' in err_msg

    def test_resource_errors_detected_handler_invalid(self):
        """Test resource errors detected handler with invalid message"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected'
        }
        context = {}
        
        ret, err_msg = rf._RedfishClient__resource_errors_detected_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
        assert 'Missing' in err_msg

    def test_task_aborted_handler(self):
        """Test task aborted handler"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {
            'MessageId': 'ResourceEvent.1.0.TaskAborted'
        }
        context = {}
        
        ret, err_msg = rf._RedfishClient__task_aborted_handler(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_OK
        assert context.get('aborted') == True
        assert err_msg == ''

    def test_dispatch_event_missing_message_id(self):
        """Test dispatch event with missing MessageId"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        event_msg = {}
        context = {}
        
        ret, err_msg = rf._RedfishClient__dispatch_event(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
        assert "Missing 'MessageId' field" in err_msg

    def test_log_multi_line_str_none(self):
        """Test log_multi_line_str with None"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.log_multi_line_str(None)

    def test_exec_curl_cmd_not_logged_in(self):
        """Test exec_curl_cmd when not logged in"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        cmd = '/usr/bin/curl -k https://169.254.0.1/test'
        ret, http_code, output, error = rf.exec_curl_cmd(cmd)
        
        assert ret == RedfishClient.ERR_CODE_NOT_LOGIN
        assert output == 'Not login'
        assert error == 'Not login'

    def test_get_uri_from_response_success(self):
        """Test __get_uri_from_response with valid response"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        response = json.dumps({
            "Payload": {
                "HttpHeaders": [
                    "Location: /redfish/v1/TaskService/Tasks/123/Attachment/1"
                ]
            }
        })
        
        ret, err_msg, uri = rf._RedfishClient__get_uri_from_response(response)
        assert ret == RedfishClient.ERR_CODE_OK
        assert err_msg == ""
        assert uri == "/redfish/v1/TaskService/Tasks/123/Attachment/1"

    def test_get_uri_from_response_invalid_json(self):
        """Test __get_uri_from_response with invalid JSON"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        response = "invalid json"
        
        ret, err_msg, uri = rf._RedfishClient__get_uri_from_response(response)
        assert ret == RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
        assert 'Invalid JSON format' in err_msg
        assert uri is None

    def test_get_uri_from_response_missing_payload(self):
        """Test __get_uri_from_response with missing Payload"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        response = json.dumps({})
        
        ret, err_msg, uri = rf._RedfishClient__get_uri_from_response(response)
        assert ret == RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
        assert "Missing 'Payload' field" in err_msg
        assert uri is None

    def test_get_uri_from_response_missing_http_headers(self):
        """Test __get_uri_from_response with missing HttpHeaders"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        response = json.dumps({
            "Payload": {}
        })
        
        ret, err_msg, uri = rf._RedfishClient__get_uri_from_response(response)
        assert ret == RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
        assert "Missing 'HttpHeaders' field" in err_msg
        assert uri is None

    def test_get_uri_from_response_missing_location(self):
        """Test __get_uri_from_response with missing Location"""
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        response = json.dumps({
            "Payload": {
                "HttpHeaders": [
                    "Content-Type: application/json"
                ]
            }
        })
        
        ret, err_msg, uri = rf._RedfishClient__get_uri_from_response(response)
        assert ret == RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
        assert "Missing 'Location' field" in err_msg
        assert uri is None

    @mock.patch('subprocess.Popen')
    def test_exec_curl_cmd_no_http_status_code(self, mock_popen):
        """Test exec_curl_cmd when HTTP status code is not found"""
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        
        output_no_status = (b'{"some": "response"}\n', b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_no_status
        mock_process2.returncode = 0
        
        mock_popen.side_effect = [mock_process, mock_process2]
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        cmd = '/usr/bin/curl -k https://169.254.0.1/test'
        ret, http_code, output, error = rf.exec_curl_cmd(cmd)
        
        assert ret == RedfishClient.ERR_CODE_CURL_FAILURE
        assert 'Unexpected curl output' in error

    @mock.patch('subprocess.Popen')
    def test_exec_curl_cmd_curl_error(self, mock_popen):
        """Test exec_curl_cmd with curl error"""
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        
        output_error = (b'', b'curl: (28) Operation timed out')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_error
        mock_process2.returncode = 28
        
        mock_popen.side_effect = [mock_process, mock_process2]
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        cmd = '/usr/bin/curl -k https://169.254.0.1/test'
        
        ret, http_code, output, error = rf._RedfishClient__exec_curl_cmd_internal(cmd)
        
        assert ret == RedfishClient.ERR_CODE_TIMEOUT

    @mock.patch('subprocess.Popen')
    def test_wait_task_completion_invalid_json(self, mock_popen):
        """Test __wait_task_completion with invalid JSON"""
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        
        output_invalid = (b'invalid json\nHTTP Status Code: 200', b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_invalid
        mock_process2.returncode = 0
        
        mock_popen.side_effect = [mock_process, mock_process2]
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        result = rf._RedfishClient__wait_task_completion('test_task_id', timeout=5, sleep_timeout=1)
        
        assert result['ret_code'] == RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
        assert 'Invalid JSON format' in result['ret_msg']

    @mock.patch('subprocess.Popen')
    def test_wait_task_completion_task_not_ok(self, mock_popen):
        """Test __wait_task_completion when task status is not OK"""
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        
        task_response = json.dumps({
            "PercentComplete": 50,
            "TaskStatus": "Failed",
            "Messages": []
        })
        output_task = (f'{task_response}\nHTTP Status Code: 200'.encode(), b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_task
        mock_process2.returncode = 0
        
        mock_popen.side_effect = [mock_process, mock_process2]
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        result = rf._RedfishClient__wait_task_completion('test_task_id', timeout=5, sleep_timeout=1)
        
        assert result['ret_code'] == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert 'Fail to execute the task' in result['ret_msg']

    @mock.patch('subprocess.Popen')
    def test_wait_task_completion_task_aborted(self, mock_popen):
        """Test __wait_task_completion when task is aborted"""
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        
        task_response = json.dumps({
            "PercentComplete": 30,
            "TaskStatus": "Aborted",
            "Messages": [
                {
                    "MessageId": "ResourceEvent.1.0.TaskAborted"
                }
            ]
        })
        output_task = (f'{task_response}\nHTTP Status Code: 200'.encode(), b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_task
        mock_process2.returncode = 0
        
        mock_popen.side_effect = [mock_process, mock_process2]
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        result = rf._RedfishClient__wait_task_completion('test_task_id', timeout=5, sleep_timeout=1)
        
        assert result['ret_code'] == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert result.get('aborted') == True
        assert 'aborted' in result['ret_msg'].lower()

    @mock.patch('subprocess.Popen')
    @mock.patch('time.time')
    @mock.patch('time.sleep')
    def test_wait_task_completion_timeout(self, mock_sleep, mock_time, mock_popen):
        """Test __wait_task_completion with timeout"""
        side_effects = []
        
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        task_response = json.dumps({
            "PercentComplete": 50,
            "TaskStatus": "OK",
            "Messages": []
        })
        output_task = (f'{task_response}\nHTTP Status Code: 200'.encode(), b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_task
        mock_process2.returncode = 0
        side_effects.append(mock_process2)

        mock_time.side_effect = [100, 110]
        
        mock_popen.side_effect = side_effects
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        result = rf._RedfishClient__wait_task_completion('test_task_id', timeout=5, sleep_timeout=1)
        
        assert result['ret_code'] == RedfishClient.ERR_CODE_TIMEOUT
        assert 'timeout' in result['ret_msg'].lower()

    @mock.patch('subprocess.Popen')
    def test_exec_curl_cmd_relogin_success(self, mock_popen):
        """Test exec_curl_cmd with 401 and successful re-login"""
        side_effects = []
        
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output_401 = (b'{"error": "Unauthorized"}\nHTTP Status Code: 401', b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_401
        mock_process2.returncode = 0
        side_effects.append(mock_process2)
        
        output_relogin = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process3 = mock.Mock()
        mock_process3.communicate.return_value = output_relogin
        mock_process3.returncode = 0
        side_effects.append(mock_process3)
        
        output_401_again = (b'{"error": "Unauthorized"}\nHTTP Status Code: 401', b'')
        mock_process4 = mock.Mock()
        mock_process4.communicate.return_value = output_401_again
        mock_process4.returncode = 0
        side_effects.append(mock_process4)
        
        mock_popen.side_effect = side_effects
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        cmd = '/usr/bin/curl -k -H "X-Auth-Token: token" https://169.254.0.1/test'
        ret, http_code, output, error = rf.exec_curl_cmd(cmd)
        
        assert ret == RedfishClient.ERR_CODE_AUTH_FAILURE
        assert 'Authentication failure' in output

    @mock.patch('subprocess.Popen')
    def test_exec_curl_cmd_relogin_failure(self, mock_popen):
        """Test exec_curl_cmd with 401 and failed re-login"""
        side_effects = []
        
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output_401 = (b'{"error": "Unauthorized"}\nHTTP Status Code: 401', b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_401
        mock_process2.returncode = 0
        side_effects.append(mock_process2)
        
        output_login_fail = (b'HTTP Status Code: 401', b'')
        mock_process3 = mock.Mock()
        mock_process3.communicate.return_value = output_login_fail
        mock_process3.returncode = 0
        side_effects.append(mock_process3)
        
        mock_popen.side_effect = side_effects
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        cmd = '/usr/bin/curl -k -H "X-Auth-Token: token" https://169.254.0.1/test'
        ret, http_code, output, error = rf.exec_curl_cmd(cmd)
        
        assert ret == RedfishClient.ERR_CODE_AUTH_FAILURE
        assert 'Authentication failure' in output

    @mock.patch('subprocess.Popen')
    def test_exec_curl_cmd_relogin_other_error(self, mock_popen):
        """Test exec_curl_cmd with 401 and re-login with other error"""
        side_effects = []
        
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output_401 = (b'{"error": "Unauthorized"}\nHTTP Status Code: 401', b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_401
        mock_process2.returncode = 0
        side_effects.append(mock_process2)
        
        output_error = (b'', b'curl: (7) Failed to connect')
        mock_process3 = mock.Mock()
        mock_process3.communicate.return_value = output_error
        mock_process3.returncode = 7
        side_effects.append(mock_process3)
        
        mock_popen.side_effect = side_effects
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        cmd = '/usr/bin/curl -k -H "X-Auth-Token: token" https://169.254.0.1/test'
        ret, http_code, output, error = rf.exec_curl_cmd(cmd)
        
        assert ret == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        assert 'Login failure' in output

    @mock.patch('subprocess.Popen')
    def test_redfish_api_request_bmc_reset_not_ok(self, mock_popen):
        """Test request_bmc_reset when command returns error"""
        side_effects = []
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output_error = (b'', b'curl: (7) Failed to connect')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_error
        mock_process2.returncode = 7
        side_effects.append(mock_process2)
        
        mock_popen.side_effect = side_effects
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        ret, msg = rf.redfish_api_request_bmc_reset()
        
        assert ret == RedfishClient.ERR_CODE_SERVER_UNREACHABLE

    @mock.patch('subprocess.Popen')
    def test_redfish_api_request_bmc_reset_with_json_error(self, mock_popen):
        """Test request_bmc_reset with JSON error response"""
        side_effects = []
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        error_json = json.dumps({
            "error": {
                "code": "Base.1.0.ActionParameterUnknown",
                "message": "Invalid reset type"
            }
        })
        output_json = (f'{error_json}\nHTTP Status Code: 400'.encode(), b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_json
        mock_process2.returncode = 0
        side_effects.append(mock_process2)
        
        mock_popen.side_effect = side_effects
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        ret, msg = rf.redfish_api_request_bmc_reset()
        
        assert ret == RedfishClient.ERR_CODE_UNSUPPORTED_PARAMETER
        assert 'Invalid reset type' in msg

    @mock.patch('subprocess.Popen')
    def test_redfish_api_request_bmc_reset_invalid_json(self, mock_popen):
        """Test request_bmc_reset with invalid JSON"""
        side_effects = []
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        output_invalid = (b'invalid json\nHTTP Status Code: 200', b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_invalid
        mock_process2.returncode = 0
        side_effects.append(mock_process2)
        
        mock_popen.side_effect = side_effects
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        ret, msg = rf.redfish_api_request_bmc_reset()
        
        assert ret == RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
        assert 'Invalid JSON format' in msg

    @mock.patch('subprocess.Popen')
    def test_redfish_api_request_bmc_reset_error_missing_message(self, mock_popen):
        """Test request_bmc_reset with error missing message field"""
        side_effects = []
        output = (load_redfish_response('mock_bmc_login_token_response'), b'')
        mock_process = mock.Mock()
        mock_process.communicate.return_value = output
        mock_process.returncode = 0
        side_effects.append(mock_process)
        
        error_json = json.dumps({
            "error": {
                "code": "Base.1.0.GeneralError"
            }
        })
        output_error = (f'{error_json}\nHTTP Status Code: 400'.encode(), b'')
        mock_process2 = mock.Mock()
        mock_process2.communicate.return_value = output_error
        mock_process2.returncode = 0
        side_effects.append(mock_process2)
        
        mock_popen.side_effect = side_effects
        
        rf = RedfishClient(TestRedfishClient.CURL_PATH,
                           TestRedfishClient.BMC_INTERNAL_IP_ADDR,
                           self.user_callback,
                           self.password_callback)
        
        rf.login()
        ret, msg = rf.redfish_api_request_bmc_reset()
        
        assert ret == RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
        assert "Missing 'message' field" in msg
