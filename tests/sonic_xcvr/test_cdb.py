# test_cdb.py
import pytest
import struct
from unittest.mock import MagicMock, patch
from sonic_platform_base.sonic_xcvr.mem_maps.public.cdb import (
    CdbMemMap, CDBCommand, CdbStatusQuery, CdbGetFirmwareInfo,
    CdbGetFirmwareMgmtFeatures, CdbStartFirmwareDownload,
    CdbAbortFirmwareDownload, CdbCompleteFirmwareDownload,
    CdbRunFirmwareDownload, CdbCommitFirmwareDownload,
    CdbWriteLplBlock, CdbWriteEplBlock
)
from sonic_platform_base.sonic_xcvr.fields import cdb_consts
from sonic_platform_base.sonic_xcvr.cdb.cdb import CdbCmdHandler


class MockCodes:
    """Mock codes class for testing"""
    CDB_QUERY_STATUS = MagicMock()
    CDB_WRITE_METHOD = MagicMock()
    CDB_READ_METHOD = MagicMock()


class TestCdbMemMap:
    """Test cases for CdbMemMap class"""
    
    def setup_method(self):
        self.codes = MockCodes()
        self.mem_map = CdbMemMap(self.codes)
    
    def test_init(self):
        """Test CdbMemMap initialization"""
        assert self.mem_map.codes == self.codes
        assert hasattr(self.mem_map, 'query_status')
        assert hasattr(self.mem_map, 'cdb1_status')
        assert hasattr(self.mem_map, 'cdb1_firmware_info')
        assert hasattr(self.mem_map, 'cdb_firmware_mgmt_features')
        assert hasattr(self.mem_map, 'cdb1_query_status_cmd')
        assert hasattr(self.mem_map, 'cdb1_firmware_info_cmd')
        assert hasattr(self.mem_map, 'cdb1_firmware_mgmt_features_cmd')
        assert hasattr(self.mem_map, 'cdb1_start_fw_download_cmd')
        assert hasattr(self.mem_map, 'cdb1_abort_fw_download_cmd')
        assert hasattr(self.mem_map, 'cdb1_complete_fw_download_cmd')
        assert hasattr(self.mem_map, 'cdb1_run_fw_download_cmd')
        assert hasattr(self.mem_map, 'cdb1_commit_fw_download_cmd')
        assert hasattr(self.mem_map, 'cdb1_write_lpl_block_cmd')
        assert hasattr(self.mem_map, 'cdb1_write_epl_block_cmd')
    
    def test_getaddr(self):
        """Test getaddr method"""
        # Test default page size
        assert self.mem_map.getaddr(0, 0) == 0
        assert self.mem_map.getaddr(1, 0) == 128
        assert self.mem_map.getaddr(1, 10) == 138
        assert self.mem_map.getaddr(2, 20) == 276
        
        # Test custom page size
        assert self.mem_map.getaddr(1, 10, page_size=256) == 266
        assert self.mem_map.getaddr(2, 20, page_size=256) == 532
    
    def test_get_all_cdb_cmds(self):
        """Test _get_all_cdb_cmds method"""
        # First call should populate the cdb_cmds dict
        cmds = self.mem_map._get_all_cdb_cmds()
        assert isinstance(cmds, dict)
        assert len(cmds) > 0
        
        # Verify all CDB command objects are included
        expected_cmd_ids = [
            cdb_consts.CDB_QUERY_STATUS_CMD,
            cdb_consts.CDB_GET_FIRMWARE_INFO_CMD,
            cdb_consts.CDB_GET_FIRMWARE_MGMT_FEATURES_CMD,
            cdb_consts.CDB_START_FIRMWARE_DOWNLOAD_CMD,
            cdb_consts.CDB_ABORT_FIRMWARE_DOWNLOAD_CMD,
            cdb_consts.CDB_COMPLETE_FIRMWARE_DOWNLOAD_CMD,
            cdb_consts.CDB_RUN_FIRMWARE_IMAGE_CMD,
            cdb_consts.CDB_COMMIT_FIRMWARE_IMAGE_CMD,
            cdb_consts.CDB_WRITE_FIRMWARE_LPL_CMD,
            cdb_consts.CDB_WRITE_FIRMWARE_EPL_CMD
        ]
        
        for cmd_id in expected_cmd_ids:
            assert cmd_id in cmds
        
        # Second call should return the cached dict
        cmds2 = self.mem_map._get_all_cdb_cmds()
        assert cmds2 is cmds
    
    def test_get_cdb_cmd(self):
        """Test get_cdb_cmd method"""
        # Test getting existing command
        cmd = self.mem_map.get_cdb_cmd(cdb_consts.CDB_QUERY_STATUS_CMD)
        assert cmd is not None
        assert isinstance(cmd, CdbStatusQuery)
        
        # Test getting non-existent command
        cmd = self.mem_map.get_cdb_cmd(0xFFFF)
        assert cmd is None


class TestCDBCommand:
    """Test cases for CDBCommand base class"""
    
    def test_init_default(self):
        """Test CDBCommand initialization with default values"""
        cmd = CDBCommand()
        assert cmd.cmd_id == 0
        assert cmd.epl == 0
        assert cmd.lpl == 0
        assert cmd.rpl == struct.pack(">H", 0)
        assert cmd.page == cdb_consts.LPL_PAGE
        assert cmd.offset == cdb_consts.CDB_LPL_CMD_START_OFFSET
        assert cmd.rpl_field is None
    
    def test_init_custom(self):
        """Test CDBCommand initialization with custom values"""
        cmd = CDBCommand(cmd_id=0x1234, epl=100, lpl=50, rpl_field="test_field")
        assert cmd.cmd_id == 0x1234
        assert cmd.epl == 100
        assert cmd.lpl == 50
        assert cmd.rpl_field == "test_field"
    
    def test_init_invalid_epl(self):
        """Test CDBCommand initialization with invalid epl"""
        with pytest.raises(AssertionError):
            CDBCommand(epl=2048)
        
        with pytest.raises(AssertionError):
            CDBCommand(epl=-1)
    
    def test_init_invalid_lpl(self):
        """Test CDBCommand initialization with invalid lpl"""
        with pytest.raises(AssertionError):
            CDBCommand(lpl=256)
        
        with pytest.raises(AssertionError):
            CDBCommand(lpl=-1)
    
    def test_get_reply_field(self):
        """Test get_reply_field method"""
        cmd = CDBCommand(rpl_field="test_reply")
        assert cmd.get_reply_field() == "test_reply"
    
    def test_checksum(self):
        """Test checksum calculation"""
        cmd = CDBCommand()
        
        # Test empty data
        result = cmd.checksum(b'')
        assert result == b'\xff'
        
        # Test single byte
        result = cmd.checksum(b'\x01')
        assert result == b'\xfe'
        
        # Test multiple bytes
        result = cmd.checksum(b'\x01\x02\x03')
        assert result == b'\xf9'
        
        # Test overflow handling
        result = cmd.checksum(b'\xff\xff')
        assert result == b'\x01'
    
    def test_getaddr(self):
        """Test getaddr method"""
        cmd = CDBCommand()
        cmd.page = 1
        cmd.offset = 10
        assert cmd.getaddr() == 138
    
    def test_get_size(self):
        """Test get_size method"""
        cmd = CDBCommand()
        assert cmd.get_size() == 6
    
    def test_encode_no_payload(self):
        """Test encode method without payload"""
        cmd = CDBCommand(cmd_id=0x1234, epl=0, lpl=0)
        encoded = cmd.encode()
        
        # Verify structure: id(2) + epl(2) + lpl(1) + checksum(1) + rpl(2)
        assert len(encoded) == 8
        assert encoded[:2] == b'\x12\x34'  # cmd_id
        assert encoded[2:4] == b'\x00\x00'  # epl
        assert encoded[4] == 0  # lpl
        # Checksum calculation for header: 0x12 + 0x34 + 0x00 + 0x00 + 0x00 = 0x46
        # Checksum = 0xff - 0x46 = 0xb9
        assert encoded[5] == 0xb9  # checksum
        assert encoded[6:8] == b'\x00\x00'  # rpl
    
    def test_encode_with_payload(self):
        """Test encode method with payload"""
        cmd = CDBCommand(cmd_id=0x1234, epl=0, lpl=0)
        payload = b'\x01\x02\x03'
        encoded = cmd.encode(payload)
        
        # Verify structure: id(2) + epl(2) + lpl(1) + checksum(1) + rpl(2) + payload(3)
        assert len(encoded) == 11
        assert encoded[:2] == b'\x12\x34'  # cmd_id
        assert encoded[2:4] == b'\x00\x00'  # epl
        assert encoded[4] == 3  # lpl (payload length)
        # Checksum calculation for header + payload: 0x12 + 0x34 + 0x00 + 0x00 + 0x03 + 0x01 + 0x02 + 0x03 = 0x4f
        # Checksum = 0xff - 0x4f = 0xb0
        assert encoded[5] == 0xb0  # checksum
        assert encoded[6:8] == b'\x00\x00'  # rpl
        assert encoded[8:] == payload  # payload
    
    def test_decode(self):
        """Test decode method"""
        cmd = CDBCommand()
        raw_data = b'\x12\x34\x00\x10\x02\xb9\x00\x01\x00\x20'
        
        decoded = cmd.decode(raw_data)
        assert decoded["cmd_id"] == 0x1234
        assert decoded["epl"] == 0x0010
        assert decoded["lpl"] == 0x02
        assert decoded["checksum"] == 0xb9
        assert decoded["rpl"] == 0x0001
        assert decoded["delay"] == 0x2000  # Note: decoded as big-endian


class TestCdbStatusQuery:
    """Test cases for CdbStatusQuery class"""
    
    def test_init(self):
        """Test CdbStatusQuery initialization"""
        cmd = CdbStatusQuery()
        assert cmd.cmd_id == cdb_consts.CDB_QUERY_STATUS_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 2
        assert cmd.rpl_field == cdb_consts.CDB1_QUERY_STATUS
    
    def test_encode_default_delay(self):
        """Test encode with default delay"""
        cmd = CdbStatusQuery()
        encoded = cmd.encode()
        
        # Extract payload from encoded data
        payload = encoded[8:]  # Skip header (8 bytes)
        assert len(payload) == 2
        assert struct.unpack(">H", payload)[0] == 0x0010
    
    def test_encode_custom_delay(self):
        """Test encode with custom delay"""
        cmd = CdbStatusQuery()
        encoded = cmd.encode(delay=0x1234)
        
        # Extract payload from encoded data
        payload = encoded[8:]  # Skip header (8 bytes)
        assert len(payload) == 2
        assert struct.unpack(">H", payload)[0] == 0x1234


class TestCdbGetFirmwareInfo:
    """Test cases for CdbGetFirmwareInfo class"""
    
    def test_init(self):
        """Test CdbGetFirmwareInfo initialization"""
        cmd = CdbGetFirmwareInfo()
        assert cmd.cmd_id == cdb_consts.CDB_GET_FIRMWARE_INFO_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 0
        assert cmd.rpl_field == cdb_consts.CDB1_FIRMWARE_INFO


class TestCdbGetFirmwareMgmtFeatures:
    """Test cases for CdbGetFirmwareMgmtFeatures class"""
    
    def test_init(self):
        """Test CdbGetFirmwareMgmtFeatures initialization"""
        cmd = CdbGetFirmwareMgmtFeatures()
        assert cmd.cmd_id == cdb_consts.CDB_GET_FIRMWARE_MGMT_FEATURES_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 0
        assert cmd.rpl_field == cdb_consts.CDB_FIRMWARE_MGMT_FEATURES


class TestCdbStartFirmwareDownload:
    """Test cases for CdbStartFirmwareDownload class"""
    
    def test_init(self):
        """Test CdbStartFirmwareDownload initialization"""
        cmd = CdbStartFirmwareDownload()
        assert cmd.cmd_id == cdb_consts.CDB_START_FIRMWARE_DOWNLOAD_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 0
    
    def test_encode(self):
        """Test encode method"""
        cmd = CdbStartFirmwareDownload()
        payload = {
            "imgsize": 0x12345678,
            "imghdr": b'\xAA\xBB\xCC\xDD'
        }
        encoded = cmd.encode(payload)
        
        # Extract LPL data from encoded command
        lpl_data = encoded[8:]  # Skip header (8 bytes)
        
        # Verify image size (first 4 bytes)
        assert struct.unpack(">I", lpl_data[:4])[0] == 0x12345678
        
        # Verify reserved field (next 4 bytes should be 0)
        assert struct.unpack(">I", lpl_data[4:8])[0] == 0
        
        # Verify image header
        assert lpl_data[8:] == b'\xAA\xBB\xCC\xDD'


class TestCdbAbortFirmwareDownload:
    """Test cases for CdbAbortFirmwareDownload class"""
    
    def test_init(self):
        """Test CdbAbortFirmwareDownload initialization"""
        cmd = CdbAbortFirmwareDownload()
        assert cmd.cmd_id == cdb_consts.CDB_ABORT_FIRMWARE_DOWNLOAD_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 0


class TestCdbCompleteFirmwareDownload:
    """Test cases for CdbCompleteFirmwareDownload class"""
    
    def test_init(self):
        """Test CdbCompleteFirmwareDownload initialization"""
        cmd = CdbCompleteFirmwareDownload()
        assert cmd.cmd_id == cdb_consts.CDB_COMPLETE_FIRMWARE_DOWNLOAD_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 0


class TestCdbRunFirmwareDownload:
    """Test cases for CdbRunFirmwareDownload class"""
    
    def test_init(self):
        """Test CdbRunFirmwareDownload initialization"""
        cmd = CdbRunFirmwareDownload()
        assert cmd.cmd_id == cdb_consts.CDB_RUN_FIRMWARE_IMAGE_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 4
    
    def test_encode(self):
        """Test encode method"""
        cmd = CdbRunFirmwareDownload()
        payload = {
            "runmode": 0x01,
            "delay": 0x1234
        }
        encoded = cmd.encode(payload)
        
        # Extract LPL data from encoded command
        lpl_data = encoded[8:]  # Skip header (8 bytes)
        
        # Verify reserved byte (first byte should be 0)
        assert lpl_data[0] == 0
        
        # Verify runmode
        assert lpl_data[1] == 0x01
        
        # Verify delay
        assert struct.unpack(">H", lpl_data[2:4])[0] == 0x1234


class TestCdbCommitFirmwareDownload:
    """Test cases for CdbCommitFirmwareDownload class"""
    
    def test_init(self):
        """Test CdbCommitFirmwareDownload initialization"""
        cmd = CdbCommitFirmwareDownload()
        assert cmd.cmd_id == cdb_consts.CDB_COMMIT_FIRMWARE_IMAGE_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 0


class TestCdbWriteLplBlock:
    """Test cases for CdbWriteLplBlock class"""
    
    def test_init(self):
        """Test CdbWriteLplBlock initialization"""
        cmd = CdbWriteLplBlock()
        assert cmd.cmd_id == cdb_consts.CDB_WRITE_FIRMWARE_LPL_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 0
    
    def test_encode_valid(self):
        """Test encode method with valid data"""
        cmd = CdbWriteLplBlock()
        payload = {
            "blkaddr": 0x12345678,
            "blkdata": b'\x01\x02\x03\x04'
        }
        encoded = cmd.encode(payload)
        
        # Extract LPL data from encoded command
        lpl_data = encoded[8:]  # Skip header (8 bytes)
        
        # Verify block address
        assert struct.unpack(">I", lpl_data[:4])[0] == 0x12345678
        
        # Verify block data
        assert lpl_data[4:] == b'\x01\x02\x03\x04'
    
    def test_encode_max_size(self):
        """Test encode with maximum allowed LPL size"""
        cmd = CdbWriteLplBlock()
        # Maximum LPL payload size minus 4 bytes for block address
        max_data_size = cdb_consts.LPL_MAX_PAYLOAD_SIZE - 4
        payload = {
            "blkaddr": 0x00000000,
            "blkdata": b'\x00' * max_data_size
        }
        
        # Should not raise an assertion error
        encoded = cmd.encode(payload)
        assert len(encoded[8:]) == cdb_consts.LPL_MAX_PAYLOAD_SIZE
    
class TestCdbWriteEplBlock:
    """Test cases for CdbWriteEplBlock class"""
    
    def test_init(self):
        """Test CdbWriteEplBlock initialization"""
        cmd = CdbWriteEplBlock()
        assert cmd.cmd_id == cdb_consts.CDB_WRITE_FIRMWARE_EPL_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 4
    
    def test_encode_valid(self):
        """Test encode method with valid data"""
        cmd = CdbWriteEplBlock()
        payload = {
            "blkaddr": 0x87654321,
            "blkdata": b'\xAA' * 100
        }
        encoded = cmd.encode(payload)
        
        # Verify EPL was updated
        assert cmd.epl == 100
        
        # Extract LPL data from encoded command
        lpl_data = encoded[8:]  # Skip header (8 bytes)
        
        # Verify block address (only LPL contains the address)
        assert struct.unpack(">I", lpl_data)[0] == 0x87654321
        
        # Note: EPL block data is written separately, not included in this command
        assert len(lpl_data) == 4  # Only contains block address
    
    def test_encode_max_size(self):
        """Test encode with maximum allowed EPL size"""
        cmd = CdbWriteEplBlock()
        payload = {
            "blkaddr": 0x00000000,
            "blkdata": b'\x00' * cdb_consts.EPL_MAX_PAYLOAD_SIZE
        }
        
        # Should not raise an assertion error
        encoded = cmd.encode(payload)
        assert cmd.epl == cdb_consts.EPL_MAX_PAYLOAD_SIZE
    
    def test_encode_oversized(self):
        """Test encode with oversized data"""
        cmd = CdbWriteEplBlock()
        oversized_data = b'\x00' * (cdb_consts.EPL_MAX_PAYLOAD_SIZE + 1)
        payload = {
            "blkaddr": 0x00000000,
            "blkdata": oversized_data
        }
        
        # Should raise assertion error
        with pytest.raises(AssertionError):
            cmd.encode(payload)
    
    def test_encode_updates_epl(self):
        """Test that encode updates EPL based on block data size"""
        cmd = CdbWriteEplBlock()
        
        # First encode with small data
        payload1 = {
            "blkaddr": 0x00000000,
            "blkdata": b'\x00' * 50
        }
        cmd.encode(payload1)
        assert cmd.epl == 50
        
        # Second encode with larger data
        payload2 = {
            "blkaddr": 0x00000000,
            "blkdata": b'\x00' * 200
        }
        cmd.encode(payload2)
        assert cmd.epl == 200

# Integration tests
class TestIntegration:
    """Integration tests for the complete module"""
    
    def test_command_round_trip(self):
        """Test encoding and decoding of commands"""
        # Test with CdbStatusQuery
        cmd = CdbStatusQuery()
        encoded = cmd.encode(delay=0x5678)
        decoded = cmd.decode(encoded)
        
        assert decoded["cmd_id"] == cdb_consts.CDB_QUERY_STATUS_CMD
        assert decoded["lpl"] == 2
        
    def test_all_commands_in_memmap(self):
        """Verify all command classes are properly instantiated in CdbMemMap"""
        codes = MockCodes()
        mem_map = CdbMemMap(codes)

        # Get all commands
        cmds = mem_map._get_all_cdb_cmds()

        # Verify command types
        assert isinstance(cmds[cdb_consts.CDB_QUERY_STATUS_CMD], CdbStatusQuery)
        assert isinstance(cmds[cdb_consts.CDB_GET_FIRMWARE_INFO_CMD], CdbGetFirmwareInfo)
        assert isinstance(cmds[cdb_consts.CDB_GET_FIRMWARE_MGMT_FEATURES_CMD], CdbGetFirmwareMgmtFeatures)
        assert isinstance(cmds[cdb_consts.CDB_START_FIRMWARE_DOWNLOAD_CMD], CdbStartFirmwareDownload)
        assert isinstance(cmds[cdb_consts.CDB_ABORT_FIRMWARE_DOWNLOAD_CMD], CdbAbortFirmwareDownload)
        assert isinstance(cmds[cdb_consts.CDB_COMPLETE_FIRMWARE_DOWNLOAD_CMD], CdbCompleteFirmwareDownload)
        assert isinstance(cmds[cdb_consts.CDB_RUN_FIRMWARE_IMAGE_CMD], CdbRunFirmwareDownload)
        assert isinstance(cmds[cdb_consts.CDB_COMMIT_FIRMWARE_IMAGE_CMD], CdbCommitFirmwareDownload)
        assert isinstance(cmds[cdb_consts.CDB_WRITE_FIRMWARE_LPL_CMD], CdbWriteLplBlock)
        assert isinstance(cmds[cdb_consts.CDB_WRITE_FIRMWARE_EPL_CMD], CdbWriteEplBlock)
class TestCdbCmdHandler:
    """Test cases for CdbCmdHandler write_epl_page and send_cmd methods"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.reader = MagicMock()
        self.writer = MagicMock()
        self.mem_map = MagicMock()
        self.handler = CdbCmdHandler(self.reader, self.writer, self.mem_map)
    
    # Tests for write_epl_page method
    def test_write_epl_page_success(self):
        """Test successful write_epl_page"""
        page = cdb_consts.EPL_PAGE
        data = b'A' * 100
        
        self.handler.write_raw = MagicMock(return_value=True)
        
        result = self.handler.write_epl_page(page, data)
        
        assert result == True
        expected_offset = (page * cdb_consts.PAGE_SIZE) + 128
        self.handler.write_raw.assert_called_once_with(expected_offset, len(data), data)
    
    def test_write_epl_page_full_page(self):
        """Test write_epl_page with full page size data"""
        page = cdb_consts.EPL_PAGE + 5
        data = b'B' * cdb_consts.PAGE_SIZE
        
        self.handler.write_raw = MagicMock(return_value=True)
        
        result = self.handler.write_epl_page(page, data)
        
        assert result == True
        expected_offset = (page * cdb_consts.PAGE_SIZE) + 128
        self.handler.write_raw.assert_called_once_with(expected_offset, cdb_consts.PAGE_SIZE, data)
    
    def test_write_epl_page_data_too_large(self):
        """Test write_epl_page with data exceeding page size"""
        page = cdb_consts.EPL_PAGE
        data = b'C' * (cdb_consts.PAGE_SIZE + 1)
        
        with pytest.raises(AssertionError, match="Data length exceeds page size"):
            self.handler.write_epl_page(page, data)
    
    def test_write_epl_page_invalid_page_number(self):
        """Test write_epl_page with invalid page number"""
        page = cdb_consts.EPL_PAGE - 1  # Page below EPL_PAGE
        data = b'D' * 50
        
        with pytest.raises(AssertionError, match="Page number must be greater than or equal to"):
            self.handler.write_epl_page(page, data)
    
    def test_write_epl_page_minimum_page(self):
        """Test write_epl_page with minimum valid page number"""
        page = cdb_consts.EPL_PAGE  # Minimum valid page
        data = b'E' * 64
        
        self.handler.write_raw = MagicMock(return_value=True)
        
        result = self.handler.write_epl_page(page, data)
        
        assert result == True
        expected_offset = (page * cdb_consts.PAGE_SIZE) + 128
        self.handler.write_raw.assert_called_once_with(expected_offset, len(data), data)
    
    def test_write_epl_page_empty_data(self):
        """Test write_epl_page with empty data"""
        page = cdb_consts.EPL_PAGE
        data = b''
        
        self.handler.write_raw = MagicMock(return_value=True)
        
        result = self.handler.write_epl_page(page, data)
        
        assert result == True
        expected_offset = (page * cdb_consts.PAGE_SIZE) + 128
        self.handler.write_raw.assert_called_once_with(expected_offset, 0, data)
    
    def test_write_epl_page_write_raw_failure(self):
        """Test write_epl_page when write_raw fails"""
        page = cdb_consts.EPL_PAGE
        data = b'F' * 100
        
        self.handler.write_raw = MagicMock(return_value=False)
        
        result = self.handler.write_epl_page(page, data)
        
        assert result == False
    
    # Tests for send_cmd method
    def test_send_cmd_success(self):
        """Test successful send_cmd"""
        cmd_id = cdb_consts.CDB_GET_FIRMWARE_INFO_CMD
        payload = {"test": "data"}
        
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: False,
            cdb_consts.CDB1_HAS_FAILED: False,
            cdb_consts.CDB1_STATUS: 0x1
        }])
        
        result = self.handler.send_cmd(cmd_id, payload)
        
        assert result == True
        self.handler.write_cmd.assert_called_once_with(cmd_id, payload)
        self.handler.wait_for_cdb_status.assert_called_once_with(None)
    
    def test_send_cmd_no_payload(self):
        """Test send_cmd without payload"""
        cmd_id = cdb_consts.CDB_ABORT_FIRMWARE_DOWNLOAD_CMD
        
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: False,
            cdb_consts.CDB1_HAS_FAILED: False,
            cdb_consts.CDB1_STATUS: 0x1
        }])
        
        result = self.handler.send_cmd(cmd_id)
        
        assert result == True
        self.handler.write_cmd.assert_called_once_with(cmd_id, None)
    
    def test_send_cmd_with_timeout(self):
        """Test send_cmd with custom timeout"""
        cmd_id = cdb_consts.CDB_RUN_FIRMWARE_IMAGE_CMD
        timeout = 10000
        
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: False,
            cdb_consts.CDB1_HAS_FAILED: False,
            cdb_consts.CDB1_STATUS: 0x1
        }])
        
        result = self.handler.send_cmd(cmd_id, timeout=timeout)
        
        assert result == True
        self.handler.wait_for_cdb_status.assert_called_once_with(timeout)
    
    def test_send_cmd_write_failure(self):
        """Test send_cmd when write_cmd fails"""
        cmd_id = cdb_consts.CDB_START_FIRMWARE_DOWNLOAD_CMD
        
        self.handler.write_cmd = MagicMock(return_value=False)
        
        result = self.handler.send_cmd(cmd_id)
        
        assert result is None
        self.handler.write_cmd.assert_called_once_with(cmd_id, None)
    
    def test_send_cmd_wait_status_timeout(self):
        """Test send_cmd when wait_for_cdb_status times out"""
        cmd_id = cdb_consts.CDB_COMPLETE_FIRMWARE_DOWNLOAD_CMD
        
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[False, None])
        
        result = self.handler.send_cmd(cmd_id)
        
        assert result is None
    
    def test_send_cmd_status_busy(self):
        """Test send_cmd when status is busy"""
        cmd_id = cdb_consts.CDB_QUERY_STATUS_CMD
        
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: True,
            cdb_consts.CDB1_HAS_FAILED: False,
            cdb_consts.CDB1_STATUS: 0x2
        }])
        
        result = self.handler.send_cmd(cmd_id)
        
        assert result == False
    
    def test_send_cmd_status_failed(self):
        """Test send_cmd when status indicates failure"""
        cmd_id = cdb_consts.CDB_WRITE_FIRMWARE_LPL_CMD
        
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: False,
            cdb_consts.CDB1_HAS_FAILED: True,
            cdb_consts.CDB1_STATUS: 0x3
        }])
        
        result = self.handler.send_cmd(cmd_id)
        
        assert result == False
    
    def test_send_cmd_status_not_success(self):
        """Test send_cmd when status is not 0x1 (success)"""
        cmd_id = cdb_consts.CDB_WRITE_FIRMWARE_EPL_CMD
        
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: False,
            cdb_consts.CDB1_HAS_FAILED: False,
            cdb_consts.CDB1_STATUS: 0x2  # Not 0x1
        }])
        
        result = self.handler.send_cmd(cmd_id)
        
        assert result == False
    
    def test_send_cmd_edge_case_busy_and_failed(self):
        """Test send_cmd edge case where both busy and failed are True"""
        cmd_id = cdb_consts.CDB_COMMIT_FIRMWARE_IMAGE_CMD
        
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: True,
            cdb_consts.CDB1_HAS_FAILED: True,
            cdb_consts.CDB1_STATUS: 0x4
        }])
        
        result = self.handler.send_cmd(cmd_id)
        
        # Should check is_busy first and return False
        assert result == False
    
    # Integration tests combining both methods
    def test_write_epl_integration(self):
        """Test integration of write_epl_page with send_cmd for EPL operations"""
        # Setup EPL write operation
        page = cdb_consts.EPL_PAGE + 2
        data = b'X' * 128
        
        self.handler.write_raw = MagicMock(return_value=True)
        
        # Write EPL page
        result = self.handler.write_epl_page(page, data)
        assert result == True
        
        # Then send EPL command
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: False,
            cdb_consts.CDB1_HAS_FAILED: False,
            cdb_consts.CDB1_STATUS: 0x1
        }])
        
        epl_payload = {"blkaddr": 0x1000, "blkdata": data}
        result = self.handler.send_cmd(cdb_consts.CDB_WRITE_FIRMWARE_EPL_CMD, epl_payload)
        assert result == True
    
    @patch('builtins.print')
    def test_send_cmd_print_messages(self, mock_print):
        """Test that send_cmd prints appropriate error messages"""
        # Test write failure message
        cmd_id = 0x1234
        self.handler.write_cmd = MagicMock(return_value=False)
        
        result = self.handler.send_cmd(cmd_id)
        
        mock_print.assert_called_with(f"Failed to write CDB command: {cmd_id}")
        assert result is None
        
        # Test timeout message
        mock_print.reset_mock()
        self.handler.write_cmd = MagicMock(return_value=True)
        self.handler.wait_for_cdb_status = MagicMock(return_value=[False, None])
        
        result = self.handler.send_cmd(cmd_id)
        
        mock_print.assert_called_with(f"CDB command: {cmd_id} failed to complete or read status")
        assert result is None
        
        # Test busy message
        mock_print.reset_mock()
        status_value = 0x5
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: True,
            cdb_consts.CDB1_HAS_FAILED: False,
            cdb_consts.CDB1_STATUS: status_value
        }])
        
        result = self.handler.send_cmd(cmd_id)
        
        mock_print.assert_called_with(f"CDB command: {cmd_id} is busy with status: {status_value}")
        assert result == False
        
        # Test failed message
        mock_print.reset_mock()
        status_value = 0x6
        self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
            cdb_consts.CDB1_IS_BUSY: False,
            cdb_consts.CDB1_HAS_FAILED: True,
            cdb_consts.CDB1_STATUS: status_value
        }])
        
        result = self.handler.send_cmd(cmd_id)
        
        mock_print.assert_called_with(f"CDB command: {cmd_id} failed with status: {status_value}")
        assert result == False
    
    # Boundary tests
    def test_write_epl_page_max_valid_page(self):
        """Test write_epl_page with maximum valid page number"""
        # Assuming max page is 0xFF
        page = 0xFF
        data = b'Z' * 64
        
        self.handler.write_raw = MagicMock(return_value=True)
        
        result = self.handler.write_epl_page(page, data)
        
        assert result == True
        expected_offset = (page * cdb_consts.PAGE_SIZE) + 128
        self.handler.write_raw.assert_called_once_with(expected_offset, len(data), data)
    
    def test_send_cmd_all_status_combinations(self):
        """Test send_cmd with all possible status combinations"""
        cmd_id = cdb_consts.CDB_GET_FIRMWARE_INFO_CMD
        
        test_cases = [
            # (is_busy, has_failed, status, expected_result)
            (False, False, 0x1, True),   # Success
            (False, False, 0x0, False),  # Not success status
            (False, True, 0x1, False),   # Failed
            (True, False, 0x1, False),   # Busy
            (True, True, 0x1, False),    # Both busy and failed
        ]
        
        for is_busy, has_failed, status, expected in test_cases:
            self.handler.write_cmd = MagicMock(return_value=True)
            self.handler.wait_for_cdb_status = MagicMock(return_value=[True, {
                cdb_consts.CDB1_IS_BUSY: is_busy,
                cdb_consts.CDB1_HAS_FAILED: has_failed,
                cdb_consts.CDB1_STATUS: status
            }])
            
            result = self.handler.send_cmd(cmd_id)
            
            assert result == expected, f"Failed for combination: busy={is_busy}, failed={has_failed}, status={status}"