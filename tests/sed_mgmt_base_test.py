"""
    sed_mgmt_base_test.py

    Unit tests for SedMgmtBase class.
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

from sonic_platform_base.sed_mgmt_base import (
    SedMgmtBase,
    _read_sed_config_value,
)


class TestSedMgmtBase:
    """Test class for SedMgmtBase."""

    def test_abstract_methods_raise_not_implemented(self):
        """Test that abstract getters raise NotImplementedError."""
        class IncompleteSedMgmt(SedMgmtBase):
            pass

        sed = IncompleteSedMgmt()
        not_implemented_methods = [
            [sed.get_min_sed_password_len],
            [sed.get_max_sed_password_len],
            [sed.get_default_sed_password],
        ]
        for method_list in not_implemented_methods:
            with pytest.raises(NotImplementedError):
                method_list[0]()

    @mock.patch('sonic_platform_base.sed_mgmt_base._read_sed_config_value')
    def test_get_tpm_bank_addresses_from_config(self, mock_read):
        """Test that base get_tpm_bank_a/b use config reader."""
        mock_read.side_effect = lambda k: {'tpm_bank_a': '0x81010001', 'tpm_bank_b': '0x81010002'}.get(k)
        class IncompleteSedMgmt(SedMgmtBase):
            def get_min_sed_password_len(self):
                return 8
            def get_max_sed_password_len(self):
                return 124
            def get_default_sed_password(self):
                return None

        sed = IncompleteSedMgmt()
        assert sed.get_tpm_bank_a_address() == '0x81010001'
        assert sed.get_tpm_bank_b_address() == '0x81010002'
        assert mock_read.call_count == 2


class ConcreteSedMgmt(SedMgmtBase):
    """Concrete implementation of SedMgmtBase for testing."""

    def get_min_sed_password_len(self):
        return 8

    def get_max_sed_password_len(self):
        return 124

    def get_default_sed_password(self):
        return 'default_secret'

    def get_tpm_bank_a_address(self):
        return '0x81010001'

    def get_tpm_bank_b_address(self):
        return '0x81010002'


class TestSedMgmtBaseWithConcrete:
    """Test SedMgmtBase methods that require concrete implementation."""

    def test_change_sed_password_length_too_short(self):
        """Test change_sed_password returns False when password too short."""
        sed = ConcreteSedMgmt()
        assert sed.change_sed_password('short') is False

    def test_change_sed_password_length_too_long(self):
        """Test change_sed_password returns False when password too long."""
        sed = ConcreteSedMgmt()
        long_pw = 'a' * 125
        assert sed.change_sed_password(long_pw) is False

    def test_change_sed_password_missing_bank_a(self):
        """Test change_sed_password returns False when bank_a is missing."""
        sed = ConcreteSedMgmt()
        with mock.patch.object(sed, 'get_tpm_bank_a_address', return_value=None):
            assert sed.change_sed_password('validpassword123') is False

    def test_change_sed_password_missing_bank_b(self):
        """Test change_sed_password returns False when bank_b is missing."""
        sed = ConcreteSedMgmt()
        with mock.patch.object(sed, 'get_tpm_bank_b_address', return_value=''):
            assert sed.change_sed_password('validpassword123') is False

    @mock.patch('subprocess.check_call')
    def test_change_sed_password_success(self, mock_check_call):
        """Test change_sed_password succeeds and calls script with correct args."""
        sed = ConcreteSedMgmt()
        result = sed.change_sed_password('validpassword123')
        assert result is True
        mock_check_call.assert_called_once()
        call_args = mock_check_call.call_args[0][0]
        assert call_args[0] == SedMgmtBase.SED_PW_CHANGE_SCRIPT
        assert '-a' in call_args and '0x81010001' in call_args
        assert '-b' in call_args and '0x81010002' in call_args
        assert '-p' in call_args and 'validpassword123' in call_args

    @mock.patch('subprocess.check_call')
    def test_change_sed_password_script_fails(self, mock_check_call):
        """Test change_sed_password returns False when script raises."""
        import subprocess
        mock_check_call.side_effect = subprocess.CalledProcessError(1, 'sed_pw_change.sh')
        sed = ConcreteSedMgmt()
        assert sed.change_sed_password('validpassword123') is False

    def test_reset_sed_password_no_default(self):
        """Test reset_sed_password returns False when default password is None."""
        sed = ConcreteSedMgmt()
        with mock.patch.object(sed, 'get_default_sed_password', return_value=None):
            assert sed.reset_sed_password() is False

    def test_reset_sed_password_missing_bank_a(self):
        """Test reset_sed_password returns False when bank_a is missing."""
        sed = ConcreteSedMgmt()
        with mock.patch.object(sed, 'get_tpm_bank_a_address', return_value=None):
            assert sed.reset_sed_password() is False

    @mock.patch('subprocess.check_call')
    def test_reset_sed_password_success(self, mock_check_call):
        """Test reset_sed_password succeeds and calls script with default password."""
        sed = ConcreteSedMgmt()
        result = sed.reset_sed_password()
        assert result is True
        mock_check_call.assert_called_once()
        call_args = mock_check_call.call_args[0][0]
        assert call_args[0] == SedMgmtBase.SED_PW_RESET_SCRIPT
        assert '-a' in call_args and '0x81010001' in call_args
        assert '-b' in call_args and '0x81010002' in call_args
        assert '-p' in call_args and 'default_secret' in call_args

    @mock.patch('subprocess.check_call')
    def test_reset_sed_password_script_fails(self, mock_check_call):
        """Test reset_sed_password returns False when script raises."""
        import subprocess
        mock_check_call.side_effect = subprocess.CalledProcessError(1, 'sed_pw_reset.sh')
        sed = ConcreteSedMgmt()
        assert sed.reset_sed_password() is False


class TestReadSedConfigValue:
    """Test _read_sed_config_value helper."""

    def test_read_sed_config_value_missing_file(self):
        """Test _read_sed_config_value returns None when file is missing."""
        with mock.patch('builtins.open', side_effect=OSError(2, 'No such file')):
            assert _read_sed_config_value('tpm_bank_a') is None

    def test_read_sed_config_value_found(self):
        """Test _read_sed_config_value returns value when key present."""
        with mock.patch('builtins.open', mock.mock_open(read_data='tpm_bank_a=0x81010001\ntpm_bank_b=0x81010002\n')):
            assert _read_sed_config_value('tpm_bank_a') == '0x81010001'
            assert _read_sed_config_value('tpm_bank_b') == '0x81010002'

    def test_read_sed_config_value_key_missing(self):
        """Test _read_sed_config_value returns None when key not in file."""
        with mock.patch('builtins.open', mock.mock_open(read_data='other=value\n')):
            assert _read_sed_config_value('tpm_bank_a') is None
