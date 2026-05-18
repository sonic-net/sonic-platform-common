from unittest.mock import mock_open
from mock import MagicMock
from mock import patch
from mock import PropertyMock
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
        expected_value = 4

        m = mock_open(read_data="0")
        with patch("builtins.open", m):
            self.sfp_optoe_api.set_optoe_max_bank_size(expected_value)

        m.assert_any_call(expected_path)
        m.assert_any_call(expected_path, mode='w')
        m().write.assert_called_once_with(str(expected_value))

    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_max_bank_size_skips_when_value_matches(self, mock_get_eeprom_path):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        expected_path = "/sys/bus/i2c/devices/1-0050/max_bank_size"

        m = mock_open(read_data="4")
        with patch("builtins.open", m):
            self.sfp_optoe_api.set_optoe_max_bank_size(4)

        m.assert_called_once_with(expected_path)
        m().write.assert_not_called()

    @patch('sonic_platform_base.sonic_xcvr.sfp_optoe_base.SfpBase.refresh_xcvr_api')
    @patch.object(SfpOptoeBase, 'set_optoe_max_bank_size')
    @patch.object(SfpOptoeBase, '_read_optoe_max_bank_size')
    @patch.object(SfpOptoeBase, 'bank', new_callable=PropertyMock)
    def test_refresh_xcvr_api_bank_zero_skips_sync(self, mock_bank, mock_read, mock_set, mock_super):
        mock_bank.return_value = 0
        self.sfp_optoe_api.refresh_xcvr_api()
        mock_read.assert_not_called()
        mock_set.assert_not_called()
        mock_super.assert_called_once()

    @patch('sonic_platform_base.sonic_xcvr.sfp_optoe_base.SfpBase.refresh_xcvr_api')
    @patch.object(SfpOptoeBase, 'set_optoe_max_bank_size')
    @patch.object(SfpOptoeBase, '_read_optoe_max_bank_size')
    @patch.object(SfpOptoeBase, 'bank', new_callable=PropertyMock)
    def test_refresh_xcvr_api_nonzero_bank_writes_max_bank_size(self, mock_bank, mock_read, mock_set, mock_super):
        mock_bank.return_value = 1
        mock_read.return_value = 4
        self.sfp_optoe_api.refresh_xcvr_api()
        mock_set.assert_called_once_with(4)
        mock_super.assert_called_once()

    @pytest.mark.parametrize("id_byte, flat_mem_byte, banks_byte, expected", [
        # Non-CMIS IDs short-circuit before any further reads
        (0x03, None, None, None),       # SFP
        (0x0D, None, None, None),       # QSFP+
        (0x11, None, None, None),       # QSFP28
        # Flat-memory CMIS modules short-circuit before the banks-byte read
        (0x18, 0x80, None, None),       # bit 7 set: flat memory
        (0x18, 0xFF, None, None),       # bit 7 set + other bits: still flat
        # All four CMIS IDs reach the banks-byte read when flat_mem=0
        (0x18, 0x00, 0x00, 0),          # QSFP-DD, 1 bank -> sysfs 0 (banking off)
        (0x19, 0x00, 0x01, 2),          # OSFP, 2 banks
        (0x1b, 0x00, 0x02, 4),          # DSFP, 4 banks
        (0x1e, 0x00, 0x01, 2),          # QSFP+ CMIS, 2 banks
        # Bits 0-6 in byte 2 are ignored by the &0x80 flat-mem mask
        (0x18, 0x7F, 0x02, 4),          # all bits except bit 7: still paged
        # Reserved encoding 0b11 in banks byte maps to None
        (0x18, 0x00, 0x03, None),
        # Bits 2-7 in banks byte 142 are ignored by the &0x03 mask
        (0x18, 0x00, 0x62, 4),          # VDM/Diag bits set + 0b10 in low bits
        (0x18, 0x00, 0xFB, None),       # high bits set + 0b11 reserved in low bits
        # Read failures propagate as None
        (None, None, None, None),       # ID byte read fails
        (0x18, None, None, None),       # flat-mem byte read fails
        (0x18, 0x00, None, None),       # banks byte read fails
    ])
    def test_read_optoe_max_bank_size(self, id_byte, flat_mem_byte, banks_byte, expected):
        def fake_read(offset, num_bytes):
            if offset == 0:
                return bytearray([id_byte]) if id_byte is not None else None
            if offset == 2:
                return bytearray([flat_mem_byte]) if flat_mem_byte is not None else None
            if offset == 270:
                return bytearray([banks_byte]) if banks_byte is not None else None
            return None
        with patch.object(SfpOptoeBase, 'read_eeprom', side_effect=fake_read):
            assert self.sfp_optoe_api._read_optoe_max_bank_size() == expected

    def test_set_power(self):
        mode = 1
        with pytest.raises(NotImplementedError):
            self.sfp_optoe_api.set_power(mode)
 
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