from unittest.mock import mock_open
from mock import MagicMock 
from mock import patch 
import pytest 
from sonic_platform_base.sonic_xcvr.sfp_optoe_base import SfpOptoeBase, SFP_OPTOE_UPPER_PAGE0_OFFSET, SFP_OPTOE_PAGE_SELECT_OFFSET
from sonic_platform_base.sonic_xcvr.api.public.c_cmis import CCmisApi
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.c_cmis import CCmisMemMap 
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
    ccmis_api = CCmisApi(eeprom) 
    cmis_api = CmisApi(eeprom) 
    sff8472_api = Sff8472Api(eeprom)
 
    def test_is_transceiver_vdm_supported_non_cmis(self):
        self.sfp_optoe_api.get_xcvr_api = MagicMock(return_value=self.sff8472_api)
        try:
            self.sfp_optoe_api.is_transceiver_vdm_supported()
        except NotImplementedError:
            exception_raised = True
        assert exception_raised

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

    def test_set_power(self):
        mode = 1
        try:
            self.sfp_optoe_api.set_power(mode)
        except NotImplementedError:
            exception_raised = True
        assert exception_raised
 
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