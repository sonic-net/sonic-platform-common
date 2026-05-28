from unittest.mock import mock_open
from mock import MagicMock
from mock import patch
from mock import PropertyMock
import pytest
from sonic_platform_base.sonic_xcvr.sfp_optoe_base import SfpOptoeBase
from sonic_platform_base.sonic_xcvr.optoe_eeprom_rw import SFP_OPTOE_UPPER_PAGE0_OFFSET, SFP_OPTOE_PAGE_SELECT_OFFSET
from sonic_platform_base.sonic_xcvr.api.public.c_cmis import CCmisApi
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.c_cmis import CCmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom 
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes 
from sonic_platform_base.sonic_xcvr.api.public.sff8472 import Sff8472Api


class TestSfpOptoeBase(object): 
 
    codes = CmisCodes 
    mem_map = CCmisMemMap(codes) 
    reader = MagicMock(return_value=None) 
    writer = MagicMock() 
    eeprom = XcvrEeprom(reader, writer, mem_map) 
    sfp_optoe_api = SfpOptoeBase() 
    ccmis_api = CCmisApi(eeprom, init_cdb_fw_handler=False) 
    cmis_api = CmisApi(eeprom, init_cdb_fw_handler=False) 
    sff8472_api = Sff8472Api(eeprom)
 
    def test_is_transceiver_vdm_supported_non_cmis(self):
        self.sfp_optoe_api.get_xcvr_api = MagicMock(return_value=self.sff8472_api)
        with pytest.raises(NotImplementedError):
            self.sfp_optoe_api.is_transceiver_vdm_supported()

    def test_is_vdm_statistic_supported_non_cmis(self):
        self.sfp_optoe_api.get_xcvr_api = MagicMock(return_value=self.sff8472_api)
        with pytest.raises(NotImplementedError):
            self.sfp_optoe_api.is_vdm_statistic_supported()

    def test_get_transceiver_vdm_real_value_basic_non_cmis(self):
        self.sfp_optoe_api.get_xcvr_api = MagicMock(return_value=self.sff8472_api)
        with pytest.raises(NotImplementedError):
            self.sfp_optoe_api.get_transceiver_vdm_real_value_basic()

    def test_get_transceiver_vdm_real_value_statistic_non_cmis(self):
        self.sfp_optoe_api.get_xcvr_api = MagicMock(return_value=self.sff8472_api)
        with pytest.raises(NotImplementedError):
            self.sfp_optoe_api.get_transceiver_vdm_real_value_statistic()

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [ 
        (0, cmis_api, 0), 
        (1, cmis_api, 1),
        (None, None, False),
        (False, cmis_api, False),
    ]) 
    def test_freeze_vdm_stats(self, mock_response1, mock_response2, expected): 
        self.sfp_optoe_api.get_xcvr_api = MagicMock() 
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2  
        self.cmis_api.freeze_vdm_stats = MagicMock() 
        self.cmis_api.freeze_vdm_stats.return_value = mock_response1 
         
        result = self.sfp_optoe_api.freeze_vdm_stats() 
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (0, cmis_api, 0),
        (1, cmis_api, 1),
        (None, None, False),
        (False, cmis_api, False),
    ])
    def test_unfreeze_vdm_stats(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.cmis_api.unfreeze_vdm_stats = MagicMock()
        self.cmis_api.unfreeze_vdm_stats.return_value = mock_response1

        result = self.sfp_optoe_api.unfreeze_vdm_stats()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (0, cmis_api, 0),
        (1, cmis_api, 1),
        (None, None, None),
        (False, cmis_api, False),
    ])
    def test_get_rx_disable_channel(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.cmis_api.get_rx_disable_channel = MagicMock()
        self.cmis_api.get_rx_disable_channel.return_value = mock_response1

        result = self.sfp_optoe_api.get_rx_disable_channel()
        assert result == expected


    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (0, cmis_api, 0),
        (1, cmis_api, 1),
        (None, None, False),
        (False, cmis_api, False),
    ])
    def test_get_vdm_freeze_status(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.cmis_api.get_vdm_freeze_status = MagicMock()
        self.cmis_api.get_vdm_freeze_status.return_value = mock_response1

        result = self.sfp_optoe_api.get_vdm_freeze_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (0, cmis_api, 0),
        (1, cmis_api, 1), 
        (None, None, False),
        (False, cmis_api, False),
    ])
    def test_get_vdm_unfreeze_status(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.cmis_api.get_vdm_unfreeze_status = MagicMock()
        self.cmis_api.get_vdm_unfreeze_status.return_value = mock_response1
        
        result = self.sfp_optoe_api.get_vdm_unfreeze_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (True, cmis_api, True),
        (False, cmis_api, False),
        (None, None, None),
    ])
    def test_is_vdm_statistic_supported(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.cmis_api.is_vdm_statistic_supported = MagicMock()
        self.cmis_api.is_vdm_statistic_supported.return_value = mock_response1

        result = self.sfp_optoe_api.is_vdm_statistic_supported()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        ({'key1': 1.0}, cmis_api, {'key1': 1.0}),
        (None, cmis_api, None),
        (None, None, None),
    ])
    def test_get_transceiver_vdm_real_value_basic(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.cmis_api.get_transceiver_vdm_real_value_basic = MagicMock()
        self.cmis_api.get_transceiver_vdm_real_value_basic.return_value = mock_response1

        result = self.sfp_optoe_api.get_transceiver_vdm_real_value_basic()
        assert result == expected

    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        ({'key1': 1.0}, cmis_api, {'key1': 1.0}),
        (None, cmis_api, None),
        (None, None, None),
    ])
    def test_get_transceiver_vdm_real_value_statistic(self, mock_response1, mock_response2, expected):
        self.sfp_optoe_api.get_xcvr_api = MagicMock()
        self.sfp_optoe_api.get_xcvr_api.return_value = mock_response2
        self.cmis_api.get_transceiver_vdm_real_value_statistic = MagicMock()
        self.cmis_api.get_transceiver_vdm_real_value_statistic.return_value = mock_response1

        result = self.sfp_optoe_api.get_transceiver_vdm_real_value_statistic()
        assert result == expected

    @patch("builtins.open", new_callable=mock_open)
    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_write_timeout_success(self, mock_get_eeprom_path, mock_open):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        expected_path = "/sys/bus/i2c/devices/1-0050/write_timeout"
        expected_timeout = 1

        self.sfp_optoe_api.set_optoe_write_timeout(expected_timeout)

        mock_open.assert_called_once_with(expected_path, mode='w')
        mock_open().write.assert_called_once_with(str(expected_timeout))

    @patch("builtins.open", new_callable=mock_open)
    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_write_timeout_ioerror(self, mock_get_eeprom_path, mock_open):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        expected_timeout = 1
        mock_open.side_effect = IOError

        self.sfp_optoe_api.set_optoe_write_timeout(expected_timeout)

        mock_open.assert_called()

    @patch("builtins.open", new_callable=mock_open)
    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_write_timeout_oserror(self, mock_get_eeprom_path, mock_open):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        expected_timeout = 1
        mock_open.side_effect = OSError

        self.sfp_optoe_api.set_optoe_write_timeout(expected_timeout)

        mock_open.assert_called()

    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_max_bank_size_success(self, mock_get_eeprom_path):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        expected_path = "/sys/bus/i2c/devices/1-0050/max_bank_size"

        m = mock_open(read_data="0")
        with patch("builtins.open", m):
            self.sfp_optoe_api.set_optoe_max_bank_size(4)

        m.assert_any_call(expected_path)
        m.assert_any_call(expected_path, mode='w')
        m().write.assert_called_once_with("4")

    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_max_bank_size_skips_when_value_matches(self, mock_get_eeprom_path):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        expected_path = "/sys/bus/i2c/devices/1-0050/max_bank_size"

        m = mock_open(read_data="4")
        with patch("builtins.open", m):
            self.sfp_optoe_api.set_optoe_max_bank_size(4)

        m.assert_called_once_with(expected_path)
        m().write.assert_not_called()

    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_max_bank_size_missing_sysfs_is_noop(self, mock_get_eeprom_path):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        m = mock_open()
        m.side_effect = FileNotFoundError

        with patch("builtins.open", m):
            self.sfp_optoe_api.set_optoe_max_bank_size(4)

        m.assert_called_once_with("/sys/bus/i2c/devices/1-0050/max_bank_size")

    @patch('sonic_platform_base.sonic_xcvr.sfp_optoe_base.SfpBase.refresh_xcvr_api')
    @patch.object(SfpOptoeBase, 'set_optoe_max_bank_size')
    @patch.object(SfpOptoeBase, 'bank', new_callable=PropertyMock)
    def test_refresh_xcvr_api_bank_zero_skips_sync(self, mock_bank, mock_set, mock_super):
        mock_bank.return_value = 0
        self.sfp_optoe_api._xcvr_api = MagicMock()

        self.sfp_optoe_api.refresh_xcvr_api()

        self.sfp_optoe_api._xcvr_api.get_max_supported_banks.assert_not_called()
        mock_set.assert_not_called()
        mock_super.assert_called_once()

    @patch('sonic_platform_base.sonic_xcvr.sfp_optoe_base.SfpBase.refresh_xcvr_api')
    @patch.object(SfpOptoeBase, 'set_optoe_max_bank_size')
    @patch.object(SfpOptoeBase, 'bank', new_callable=PropertyMock)
    def test_refresh_xcvr_api_nonzero_bank_writes_max_bank_size(self, mock_bank, mock_set, mock_super):
        mock_bank.return_value = 1
        self.sfp_optoe_api._xcvr_api = MagicMock()
        self.sfp_optoe_api._xcvr_api.get_max_supported_banks.return_value = 4

        self.sfp_optoe_api.refresh_xcvr_api()

        self.sfp_optoe_api._xcvr_api.get_max_supported_banks.assert_called_once()
        mock_set.assert_called_once_with(4)
        mock_super.assert_called_once()

    @patch('sonic_platform_base.sonic_xcvr.sfp_optoe_base.SfpBase.refresh_xcvr_api')
    @patch.object(SfpOptoeBase, 'set_optoe_max_bank_size')
    @patch.object(SfpOptoeBase, 'bank', new_callable=PropertyMock)
    def test_refresh_xcvr_api_nonzero_bank_noop_when_api_unsupported(self, mock_bank, mock_set, mock_super):
        mock_bank.return_value = 1
        self.sfp_optoe_api._xcvr_api = MagicMock()
        self.sfp_optoe_api._xcvr_api.get_max_supported_banks.side_effect = AttributeError

        self.sfp_optoe_api.refresh_xcvr_api()

        mock_set.assert_not_called()
        mock_super.assert_called_once()

    @patch.object(CmisApi, 'is_flat_memory', return_value=True)
    def test_get_max_supported_banks_flat_mem(self, _mock_flat):
        assert self.cmis_api.get_max_supported_banks() == 0

    @patch.object(CmisApi, 'is_flat_memory', return_value=False)
    def test_get_max_supported_banks_reads_banks_supported_field(self, _mock_flat):
        self.cmis_api.xcvr_eeprom.read = MagicMock(return_value=4)

        result = self.cmis_api.get_max_supported_banks()

        self.cmis_api.xcvr_eeprom.read.assert_called_once_with('BanksSupported')
        assert result == 4

    def test_set_power(self):
        mode = 1
        with pytest.raises(NotImplementedError):
            self.sfp_optoe_api.set_power(mode)

    def test_get_lpmode_via_pin_not_implemented(self):
        with pytest.raises(NotImplementedError):
            SfpOptoeBase().get_lpmode_via_pin()

    def test_set_lpmode_via_pin_not_implemented(self):
        with pytest.raises(NotImplementedError):
            SfpOptoeBase().set_lpmode_via_pin(True)
 
    def test_default_page(self):
        with patch("builtins.open", mock_open(read_data=b'\x01')) as mocked_file:
            self.sfp_optoe_api.write_eeprom =  MagicMock(return_value=True)
            self.sfp_optoe_api.get_optoe_current_page = MagicMock(return_value=0x10)
            self.sfp_optoe_api.get_eeprom_path = MagicMock(return_value='/sys/class/eeprom')
            data = self.sfp_optoe_api.read_eeprom(SFP_OPTOE_UPPER_PAGE0_OFFSET, 1)
            mocked_file.assert_called_once_with("/sys/class/eeprom", mode='rb', buffering=0)
            assert data == b'\x01'
            self.sfp_optoe_api.write_eeprom.assert_called_once_with(SFP_OPTOE_PAGE_SELECT_OFFSET, 1, b'\x00')
            self.sfp_optoe_api.get_optoe_current_page.assert_called_once()
