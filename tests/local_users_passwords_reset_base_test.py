'''
Test LocalUsersConfigurationResetBase module
'''
import subprocess
import pytest
from mock import patch, mock_open
from sonic_platform_base.local_users_passwords_reset_base import LocalUsersConfigurationResetBase


DEFAULT_USERS_JSON_EXAMPLE_OUTPUT = '''
{
    "admin": {
        "expire": "false",
        "password": "HASHED_PASSWORD_123"
    }
}
'''


class TestLocalUsersConfigurationResetBase:
    '''
    Collection of LocalUsersConfigurationResetBase test methods
    '''
    @staticmethod
    def test_local_users_passwords_reset_base():
        '''
        Verify unimplemented methods
        '''
        base = LocalUsersConfigurationResetBase()
        not_implemented_methods = [
            (base.should_trigger,)]

        for method in not_implemented_methods:
            expected_exception = False
            try:
                func = method[0]
                args = method[1:]
                func(*args)
            except Exception as exc:
                expected_exception = isinstance(exc, NotImplementedError)
            assert expected_exception

    @patch('subprocess.call')
    def test_reset_passwords_method(self, mock_subproc_call):
        '''
        Test the reset passwords static method
        '''
        LocalUsersConfigurationResetBase.reset_password(
            user='admin',
            hashed_password='HASHED_PASSWORD_123',
            expire=True)
        mock_subproc_call.assert_any_call(["echo 'admin:HASHED_PASSWORD_123' | sudo chpasswd -e"], shell=True)
        mock_subproc_call.assert_any_call(['sudo', 'passwd', '-e', 'admin'])

    @patch('subprocess.call')
    @patch("builtins.open", new_callable=mock_open, read_data=DEFAULT_USERS_JSON_EXAMPLE_OUTPUT)
    def test_basic_flow_resetting_users_triggered(self, mock_open, mock_subproc_call):
        '''
        Test the basic flow of resetting local users when long button press is detected
        '''
        LocalUsersConfigurationResetBase().start()
        mock_subproc_call.assert_any_call(["echo 'admin:HASHED_PASSWORD_123' | sudo chpasswd -e"], shell=True)
        mock_subproc_call.assert_any_call(['sudo', 'passwd', '-e', 'admin'])
