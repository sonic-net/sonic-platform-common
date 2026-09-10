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

from sonic_platform_base.bmc_base import BMCBase, SONIC_BMC_EEPROM_TLV_MAP
from sonic_platform_base.redfish_client import RedfishClient

OPENBMC_PATCH = mock.patch(
    'sonic_py_common.device_info.get_bmc_os',
    return_value='openbmc')
SONIC_BMC_PATCH = mock.patch(
    'sonic_py_common.device_info.get_bmc_os',
    return_value='sonic')


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

    @mock.patch('sonic_py_common.device_info.is_switch_host', create=True, return_value=True)
    @mock.patch('sonic_py_common.device_info.get_bmc_data', create=True,
                return_value={'bmc_addr': '169.254.0.1'})
    def test_get_presence_true(self, _mock_get_bmc_data, _mock_is_switch_host):
        """Test get_presence returns True on Switch-Host when bmc.json data exists"""
        bmc = BMCBase('169.254.0.1')
        assert bmc.get_presence() is True

    @mock.patch('sonic_py_common.device_info.is_switch_host', create=True, return_value=True)
    @mock.patch('sonic_py_common.device_info.get_bmc_data', create=True, return_value=None)
    def test_get_presence_false_no_bmc_data(self, _mock_get_bmc_data, _mock_is_switch_host):
        """Test get_presence returns False when /etc/sonic/bmc.json is unavailable"""
        bmc = BMCBase('169.254.0.1')
        assert bmc.get_presence() is False

    @mock.patch('sonic_py_common.device_info.is_switch_host', create=True, return_value=False)
    @mock.patch('sonic_py_common.device_info.get_bmc_data', create=True,
                return_value={'bmc_addr': '169.254.0.1'})
    def test_get_presence_false_not_switch_host(self, _mock_get_bmc_data, _mock_is_switch_host):
        """Test get_presence returns False on Switch-BMC even if bmc.json data exists"""
        bmc = BMCBase('169.254.0.1')
        assert bmc.get_presence() is False

    def test_is_replaceable(self):
        """Test is_replaceable returns False"""
        bmc = BMCBase('169.254.0.1')
        assert bmc.is_replaceable() == False

    @OPENBMC_PATCH
    def test_get_revision_openbmc(self, mock_get_bmc_os):
        """Test get_revision returns N/A when BMC OS is openbmc"""
        bmc = BMCBase('169.254.0.1')
        assert bmc.get_revision() == 'N/A'

    @SONIC_BMC_PATCH
    @mock.patch.object(BMCBase, 'get_eeprom')
    def test_get_revision_sonic_bmc_success(self, mock_get_eeprom, mock_get_bmc_os):
        """Test get_revision returns the value from SONiC BMC EEPROM"""
        mock_get_eeprom.return_value = {'Model': 'P4102-A01', 'Revision': 'A02'}
        bmc = BMCBase('169.254.0.1')
        assert bmc.get_revision() == 'A02'

    @SONIC_BMC_PATCH
    @mock.patch.object(BMCBase, 'get_eeprom')
    def test_get_revision_sonic_bmc_missing_field(self, mock_get_eeprom, mock_get_bmc_os):
        """Test get_revision returns N/A when Revision field is absent"""
        mock_get_eeprom.return_value = {'Model': 'P4102-A01'}
        bmc = BMCBase('169.254.0.1')
        assert bmc.get_revision() == 'N/A'

    @SONIC_BMC_PATCH
    @mock.patch.object(BMCBase, 'get_eeprom')
    def test_get_revision_sonic_bmc_invalid_eeprom(self, mock_get_eeprom, mock_get_bmc_os):
        """Test get_revision returns N/A when SONiC BMC EEPROM is empty"""
        mock_get_eeprom.return_value = {}
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

    @mock.patch.object(RedfishClient, 'wait_until_redfish_ready')
    def test_wait_until_redfish_ready_delegates(self, mock_wait):
        """BMCBase.wait_until_redfish_ready passes args/return through to RedfishClient."""
        # Non-zero so the return assertion actually tests pass-through (0 would pass
        # even if the delegator ignored the result and returned OK).
        mock_wait.return_value = RedfishClient.ERR_CODE_TIMEOUT

        bmc = BMCBase('169.254.0.1')
        ret = bmc.wait_until_redfish_ready(timeout=123, interval=7)

        assert ret == RedfishClient.ERR_CODE_TIMEOUT
        mock_wait.assert_called_once_with(123, 7)

    @mock.patch.object(RedfishClient, 'wait_until_redfish_ready')
    def test_wait_until_redfish_ready_default_args(self, mock_wait):
        """BMCBase.wait_until_redfish_ready defaults come from RedfishClient constants."""
        mock_wait.return_value = RedfishClient.ERR_CODE_SERVER_UNREACHABLE

        bmc = BMCBase('169.254.0.1')
        ret = bmc.wait_until_redfish_ready()

        assert ret == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        mock_wait.assert_called_once_with(RedfishClient.READY_POLL_TIMEOUT,
                                          RedfishClient.READY_POLL_INTERVAL)

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

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_firmware_version')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_version_success(self, mock_has_login, mock_logout, mock_login, mock_get_fw_version,
                                 mock_get_bmc_os):
        """Test get_version with successful version retrieval"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_fw_version.return_value = (RedfishClient.ERR_CODE_OK, 'V.88.0002.0500')
        
        bmc = ConcreteBMC('169.254.0.1')
        version = bmc.get_version()
        
        assert version == 'V.88.0002.0500'
        mock_get_fw_version.assert_called_once_with('BMC_FW_0')

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_firmware_version')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_version_failure(self, mock_has_login, mock_logout, mock_login, mock_get_fw_version,
                                 mock_get_bmc_os):
        """Test get_version with failure"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_fw_version.return_value = (RedfishClient.ERR_CODE_GENERIC_ERROR, 'N/A')
        
        bmc = ConcreteBMC('169.254.0.1')
        version = bmc.get_version()
        
        assert version == 'N/A'

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_firmware_version')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_version_exception(self, mock_has_login, mock_logout, mock_login, mock_get_fw_version,
                                   mock_get_bmc_os):
        """Test get_version with exception"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_fw_version.side_effect = Exception("Test exception")
        
        bmc = ConcreteBMC('169.254.0.1')
        version = bmc.get_version()
        
        assert version == 'N/A'

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_eeprom_success(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom,
                                mock_get_bmc_os):
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

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_eeprom_failure(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom,
                                mock_get_bmc_os):
        """Test get_eeprom with failure"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_GENERIC_ERROR, {})
        
        bmc = ConcreteBMC('169.254.0.1')
        result = bmc.get_eeprom()
        
        assert result == {}

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_eeprom_exception(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom,
                                  mock_get_bmc_os):
        """Test get_eeprom with exception"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_eeprom.side_effect = Exception("Test exception")
        
        bmc = ConcreteBMC('169.254.0.1')
        result = bmc.get_eeprom()
        
        assert result == {}

    @SONIC_BMC_PATCH
    @mock.patch.object(ConcreteBMC, '_get_eeprom_from_sonic_bmc_redis')
    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    def test_get_eeprom_sonic_bmc_routes_to_redis(self, mock_get_eeprom, mock_get_sonic_eeprom,
                                                  mock_get_bmc_os):
        """Test get_eeprom uses remote Redis path when BMC OS is sonic"""
        sonic_eeprom = {
            'Model': 'P4102-A01',
            'PartNumber': '699-24102-0100-EB1',
            'SerialNumber': 'MT260560000K',
        }
        mock_get_sonic_eeprom.return_value = sonic_eeprom

        bmc = ConcreteBMC('169.254.0.1')
        result = bmc.get_eeprom()

        assert result == sonic_eeprom
        mock_get_sonic_eeprom.assert_called_once()
        mock_get_eeprom.assert_not_called()

    @SONIC_BMC_PATCH
    @mock.patch.object(ConcreteBMC, '_is_remote_eeprom_initialized', return_value=True)
    @mock.patch.object(ConcreteBMC, 'get_status')
    @mock.patch.object(ConcreteBMC, '_read_eeprom_tlv_value')
    def test_get_eeprom_from_sonic_bmc_redis_success(self, mock_read_tlv, mock_get_status,
                                                      mock_is_initialized, mock_get_bmc_os):
        """Test SONiC BMC EEPROM read from remote STATE_DB TLV fields"""
        mock_read_tlv.side_effect = lambda tlv_code: {
            SONIC_BMC_EEPROM_TLV_MAP['Model']: 'P4102-A01',
            SONIC_BMC_EEPROM_TLV_MAP['PartNumber']: '699-24102-0100-EB1',
            SONIC_BMC_EEPROM_TLV_MAP['SerialNumber']: 'MT260560000K',
            SONIC_BMC_EEPROM_TLV_MAP['Revision']: 'A02',
            SONIC_BMC_EEPROM_TLV_MAP['Manufacturer']: 'NVIDIA',
        }.get(tlv_code)
        mock_get_status.return_value = True

        bmc = ConcreteBMC('169.254.0.1')
        result = bmc._get_eeprom_from_sonic_bmc_redis()

        assert result == {
            'Model': 'P4102-A01',
            'PartNumber': '699-24102-0100-EB1',
            'SerialNumber': 'MT260560000K',
            'Revision': 'A02',
            'Manufacturer': 'NVIDIA',
            'PowerState': 'On',
        }

    @SONIC_BMC_PATCH
    @mock.patch.object(ConcreteBMC, '_is_remote_eeprom_initialized', return_value=True)
    @mock.patch.object(ConcreteBMC, 'get_status')
    @mock.patch.object(ConcreteBMC, '_read_eeprom_tlv_value')
    def test_get_eeprom_from_sonic_bmc_redis_power_off(self, mock_read_tlv, mock_get_status,
                                                        mock_is_initialized, mock_get_bmc_os):
        """Test SONiC BMC EEPROM reports PowerState Off when get_status is False"""
        mock_read_tlv.return_value = None
        mock_get_status.return_value = False

        bmc = ConcreteBMC('169.254.0.1')
        result = bmc._get_eeprom_from_sonic_bmc_redis()

        assert result == {'PowerState': 'Off'}

    @SONIC_BMC_PATCH
    @mock.patch.object(ConcreteBMC, '_is_remote_eeprom_initialized', return_value=True)
    @mock.patch.object(ConcreteBMC, '_read_eeprom_tlv_value', side_effect=Exception("redis down"))
    def test_get_eeprom_from_sonic_bmc_redis_failure(self, mock_read_tlv, mock_is_initialized, mock_get_bmc_os):
        """Test SONiC BMC EEPROM read returns empty dict on failure"""
        bmc = ConcreteBMC('169.254.0.1')
        result = bmc._get_eeprom_from_sonic_bmc_redis()
        assert result == {}

    @SONIC_BMC_PATCH
    @mock.patch.object(ConcreteBMC, '_is_remote_eeprom_initialized', return_value=False)
    @mock.patch.object(ConcreteBMC, 'get_status')
    @mock.patch.object(ConcreteBMC, '_read_eeprom_tlv_value')
    def test_get_eeprom_from_sonic_bmc_redis_not_initialized(self, mock_read_tlv, mock_get_status,
                                                              mock_is_initialized, mock_get_bmc_os):
        """Test SONiC BMC EEPROM read returns empty dict when syseepromd hasn't populated STATE_DB yet"""
        bmc = ConcreteBMC('169.254.0.1')
        result = bmc._get_eeprom_from_sonic_bmc_redis()

        assert result == {}
        mock_read_tlv.assert_not_called()
        mock_get_status.assert_not_called()

    @mock.patch.object(ConcreteBMC, '_get_remote_state_db')
    @mock.patch('swsscommon.swsscommon.Table')
    def test_is_remote_eeprom_initialized_true(self, mock_table_cls, mock_get_remote_state_db):
        """Test _is_remote_eeprom_initialized returns True when State.Initialized is '1'"""
        mock_table = mock.MagicMock()
        mock_table.get.return_value = (True, [('Initialized', '1')])
        mock_table_cls.return_value = mock_table

        bmc = ConcreteBMC('169.254.0.1')
        assert bmc._is_remote_eeprom_initialized() is True
        mock_table.get.assert_called_once_with('State')

    @mock.patch.object(ConcreteBMC, '_get_remote_state_db')
    @mock.patch('swsscommon.swsscommon.Table')
    def test_is_remote_eeprom_initialized_false_not_set(self, mock_table_cls, mock_get_remote_state_db):
        """Test _is_remote_eeprom_initialized returns False when the State key is missing"""
        mock_table = mock.MagicMock()
        mock_table.get.return_value = (False, [])
        mock_table_cls.return_value = mock_table

        bmc = ConcreteBMC('169.254.0.1')
        assert bmc._is_remote_eeprom_initialized() is False

    @mock.patch.object(ConcreteBMC, '_get_remote_state_db')
    @mock.patch('swsscommon.swsscommon.Table')
    def test_is_remote_eeprom_initialized_false_zero(self, mock_table_cls, mock_get_remote_state_db):
        """Test _is_remote_eeprom_initialized returns False when Initialized is not '1'"""
        mock_table = mock.MagicMock()
        mock_table.get.return_value = (True, [('Initialized', '0')])
        mock_table_cls.return_value = mock_table

        bmc = ConcreteBMC('169.254.0.1')
        assert bmc._is_remote_eeprom_initialized() is False

    @OPENBMC_PATCH
    def test_wrapper_rf_client_none_exception(self, mock_get_bmc_os):
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

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_model(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom,
                       mock_get_bmc_os):
        """Test get_model"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        eeprom_data = {'Model': 'P3809', 'SerialNumber': '123456'}
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_OK, eeprom_data)
        
        bmc = ConcreteBMC('169.254.0.1')
        model = bmc.get_model()
        
        assert model == 'P3809'

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_model_returns_none(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom,
                                    mock_get_bmc_os):
        """Test get_model returns None when EEPROM is invalid"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_GENERIC_ERROR, {})
        
        bmc = ConcreteBMC('169.254.0.1')
        model = bmc.get_model()
        
        assert model is None

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_serial(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom,
                        mock_get_bmc_os):
        """Test get_serial"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        eeprom_data = {'Model': 'P3809', 'SerialNumber': '123456'}
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_OK, eeprom_data)
        
        bmc = ConcreteBMC('169.254.0.1')
        serial = bmc.get_serial()
        
        assert serial == '123456'

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_eeprom_info')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_serial_returns_none(self, mock_has_login, mock_logout, mock_login, mock_get_eeprom,
                                     mock_get_bmc_os):
        """Test get_serial returns None when EEPROM is invalid"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_eeprom.return_value = (RedfishClient.ERR_CODE_OK, {})
        
        bmc = ConcreteBMC('169.254.0.1')
        serial = bmc.get_serial()
        
        assert serial is None

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_update_firmware')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_update_firmware_success(self, mock_has_login, mock_logout, mock_login, mock_update_fw,
                                     mock_get_bmc_os):
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

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_trigger_bmc_debug_log_dump')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_trigger_bmc_debug_log_dump(self, mock_has_login, mock_logout, mock_login, mock_trigger,
                                        mock_get_bmc_os):
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

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_bmc_debug_log_dump')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_get_bmc_debug_log_dump(self, mock_has_login, mock_logout, mock_login, mock_get_dump,
                                    mock_get_bmc_os):
        """Test get_bmc_debug_log_dump"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_dump.return_value = (RedfishClient.ERR_CODE_OK, '')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, err_msg = bmc.get_bmc_debug_log_dump('task_123', 'dump.tar', '/tmp', 60)
        
        assert ret == RedfishClient.ERR_CODE_OK
        mock_get_dump.assert_called_once_with('task_123', 'dump.tar', '/tmp', 60)

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_request_bmc_reset')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_request_bmc_reset_graceful(self, mock_has_login, mock_logout, mock_login, mock_reset,
                                        mock_get_bmc_os):
        """Test request_bmc_reset with graceful=True"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_reset.return_value = (RedfishClient.ERR_CODE_OK, '')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, msg = bmc.request_bmc_reset(graceful=True)
        
        assert ret == RedfishClient.ERR_CODE_OK
        mock_reset.assert_called_once_with(RedfishClient.REDFISH_BMC_GRACEFUL_RESTART)

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_set_min_password_length')
    @mock.patch.object(RedfishClient, 'redfish_api_change_login_password')
    @mock.patch.object(RedfishClient, 'redfish_api_get_min_password_length')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_bmc_reset_root_password_success(self, mock_has_login, mock_logout, mock_login, 
                                           mock_get_min_length, mock_change_pw, mock_set_min_length,
                                           mock_get_bmc_os):
        """Test reset_root_password successful flow"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_min_length.return_value = (RedfishClient.ERR_CODE_OK, 12)
        mock_change_pw.return_value = (RedfishClient.ERR_CODE_OK, '')
        mock_set_min_length.return_value = (RedfishClient.ERR_CODE_OK, '')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, msg = bmc.reset_root_password()
        
        assert ret == RedfishClient.ERR_CODE_OK
        assert msg == ''
        mock_get_min_length.assert_called_once()
        mock_set_min_length.assert_any_call(8)
        mock_set_min_length.assert_any_call(12)
        mock_change_pw.assert_called_once_with('rootpass', BMCBase.ROOT_ACCOUNT)

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_min_password_length')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_reset_root_password_no_default_password(self, mock_has_login, mock_logout, mock_login,
                                                      mock_get_min_length, mock_get_bmc_os):
        """Test reset_root_password when _get_default_root_password returns None"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_min_length.return_value = (RedfishClient.ERR_CODE_OK, 12)
        
        bmc = ConcreteBMC('169.254.0.1')
        with mock.patch.object(bmc, '_get_default_root_password', return_value=None):
            with mock.patch.object(bmc, '_change_login_password') as mock_change_pw:
                ret, msg = bmc.reset_root_password()
        assert ret == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert msg == "BMC root account default password not found"
        mock_change_pw.assert_not_called()

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_get_min_password_length')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_bmc_reset_root_password_get_min_length_fail(self, mock_has_login, mock_logout, 
                                                       mock_login, mock_get_min_length, mock_get_bmc_os):
        """Test reset_root_password failure at get min length step"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_min_length.return_value = (RedfishClient.ERR_CODE_GENERIC_ERROR, 'Get failed')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, msg = bmc.reset_root_password()
        
        assert ret == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert 'Failed to get current min password length: Get failed' in msg
        mock_get_min_length.assert_called_once()

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_set_min_password_length')
    @mock.patch.object(RedfishClient, 'redfish_api_get_min_password_length')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_bmc_reset_root_password_set_min_length_fail(self, mock_has_login, mock_logout, 
                                                       mock_login, mock_get_min_length, mock_set_min_length,
                                                       mock_get_bmc_os):
        """Test reset_root_password failure at set min length step"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_min_length.return_value = (RedfishClient.ERR_CODE_OK, 12)
        mock_set_min_length.return_value = (RedfishClient.ERR_CODE_GENERIC_ERROR, 'Set failed')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, msg = bmc.reset_root_password()
        
        assert ret == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert 'Failed to set min password length to 8: Set failed' in msg
        mock_get_min_length.assert_called_once()
        mock_set_min_length.assert_called_once_with(8)

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'redfish_api_set_min_password_length')
    @mock.patch.object(RedfishClient, 'redfish_api_change_login_password')
    @mock.patch.object(RedfishClient, 'redfish_api_get_min_password_length')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_bmc_reset_root_password_change_password_fail(self, mock_has_login, mock_logout, mock_login,
                                                        mock_get_min_length, mock_change_pw, mock_set_min_length,
                                                        mock_get_bmc_os):
        """Test reset_root_password failure at change password step"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_get_min_length.return_value = (RedfishClient.ERR_CODE_OK, 12)
        mock_set_min_length.return_value = (RedfishClient.ERR_CODE_OK, '')
        mock_change_pw.return_value = (RedfishClient.ERR_CODE_GENERIC_ERROR, 'Change failed')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, msg = bmc.reset_root_password()
        
        assert ret == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert 'Failed to change root password: Change failed' in msg
        mock_get_min_length.assert_called_once()
        assert mock_set_min_length.call_count == 2
        mock_change_pw.assert_called_once_with('rootpass', BMCBase.ROOT_ACCOUNT)

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'open_session')
    def test_open_session_success(self, mock_open_session, mock_get_bmc_os):
        """Test open_session with successful session creation"""
        mock_open_session.return_value = (RedfishClient.ERR_CODE_OK, ('Login successful', ('session_123', 'token_abc')))
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, (msg, credentials) = bmc.open_session()
        
        assert ret == RedfishClient.ERR_CODE_OK
        assert msg == 'Login successful'
        assert credentials == ('session_123', 'token_abc')
        mock_open_session.assert_called_once()

    @OPENBMC_PATCH
    @mock.patch.object(RedfishClient, 'close_session')
    @mock.patch.object(RedfishClient, 'login')
    @mock.patch.object(RedfishClient, 'logout')
    @mock.patch.object(RedfishClient, 'has_login')
    def test_close_session_success(self, mock_has_login, mock_logout, mock_login, mock_close_session,
                                   mock_get_bmc_os):
        """Test close_session with successful session closure"""
        mock_has_login.return_value = False
        mock_login.return_value = RedfishClient.ERR_CODE_OK
        mock_logout.return_value = RedfishClient.ERR_CODE_OK
        mock_close_session.return_value = (RedfishClient.ERR_CODE_OK, 'Session closed successfully')
        
        bmc = ConcreteBMC('169.254.0.1')
        ret, msg = bmc.close_session('session_123')
        
        assert ret == RedfishClient.ERR_CODE_OK
        assert msg == 'Session closed successfully'
        mock_close_session.assert_called_once_with('session_123')
