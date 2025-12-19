# test_cdb_fw.py
import pytest
from mock import MagicMock, patch, mock_open, call
#from unittest.mock import patch, mock_open, call
from sonic_platform_base.sonic_xcvr.cdb.cdb_fw import CdbFwHandler
from sonic_platform_base.sonic_xcvr.fields import cdb_consts

class TestCdbFwHandler:
    """Test cases for CdbFwHandler class"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.reader = MagicMock()
        self.writer = MagicMock()
        self.mem_map = MagicMock()
        
        # Mock the parent class initialization
        with patch.object(CdbFwHandler, 'initFwHandler', return_value=True):
            self.handler = CdbFwHandler(self.reader, self.writer, self.mem_map)
    
    def test_init_success(self):
        """Test successful initialization"""
        # Create a fresh handler without mocking initFwHandler
        handler = object.__new__(CdbFwHandler)
        # Initialize parent class
        super(CdbFwHandler, handler).__init__(self.reader, self.writer, self.mem_map)
        # Set initial attributes
        handler.start_payload_size = 0
        handler.is_lpl_only = False
        handler.rw_length_ext = 0
        
        # Mock methods
        handler.send_cmd = MagicMock(return_value=True)
        handler.read_reply = MagicMock(return_value={
            cdb_consts.CDB_START_CMD_PAYLOAD_SIZE: 128,
            cdb_consts.CDB_WRITE_MECHANISM: "EPL",
            cdb_consts.CDB_READ_WRITE_LENGTH_EXT: 2040
        })
        
        # Manually call initFwHandler
        assert handler.initFwHandler() == True
    
    def test_init_failure_graceful(self):
        """Test initialization failure is handled gracefully"""
        with patch.object(CdbFwHandler, 'initFwHandler', return_value=False):
            handler = CdbFwHandler(self.reader, self.writer, self.mem_map)
            assert handler is not None
    
    def test_initFwHandler_send_cmd_failure(self):
        """Test initFwHandler when send_cmd fails"""
        # Create a new handler to test initFwHandler
        handler = object.__new__(CdbFwHandler)
        super(CdbFwHandler, handler).__init__(self.reader, self.writer, self.mem_map)
        handler.start_payload_size = 0
        handler.is_lpl_only = False
        handler.rw_length_ext = 0

        handler.send_cmd = MagicMock(return_value=False)

        result = handler.initFwHandler()

        assert result == True

    def test_initFwHandler_read_reply_none(self):
        """Test initFwHandler when read_reply returns None"""
        # Create a new handler to test initFwHandler
        handler = object.__new__(CdbFwHandler)
        super(CdbFwHandler, handler).__init__(self.reader, self.writer, self.mem_map)
        handler.start_payload_size = 0
        handler.is_lpl_only = False
        handler.rw_length_ext = 0

        handler.send_cmd = MagicMock(return_value=True)
        handler.read_reply = MagicMock(return_value=None)

        result = handler.initFwHandler()

        assert result == True

    def test_initFwHandler_lpl_only(self):
        """Test initFwHandler with LPL only mechanism"""
        # Create a new handler to test initFwHandler
        handler = object.__new__(CdbFwHandler)
        super(CdbFwHandler, handler).__init__(self.reader, self.writer, self.mem_map)
        handler.start_payload_size = 0
        handler.is_lpl_only = False
        handler.rw_length_ext = 0
        
        handler.send_cmd = MagicMock(return_value=True)
        handler.read_reply = MagicMock(return_value={
            cdb_consts.CDB_START_CMD_PAYLOAD_SIZE: 64,
            cdb_consts.CDB_WRITE_MECHANISM: "LPL",
            cdb_consts.CDB_READ_WRITE_LENGTH_EXT: 1000
        })
        
        result = handler.initFwHandler()
        assert result == True

    def test_initFwHandler_epl_mechanism(self):
        """Test initFwHandler with EPL mechanism"""
        # Create a new handler to test initFwHandler
        handler = object.__new__(CdbFwHandler)
        super(CdbFwHandler, handler).__init__(self.reader, self.writer, self.mem_map)
        handler.start_payload_size = 0
        handler.is_lpl_only = False
        handler.rw_length_ext = 0
        
        handler.send_cmd = MagicMock(return_value=True)
        handler.read_reply = MagicMock(return_value={
            cdb_consts.CDB_START_CMD_PAYLOAD_SIZE: 256,
            cdb_consts.CDB_WRITE_MECHANISM: "EPL",
            cdb_consts.CDB_READ_WRITE_LENGTH_EXT: 5000
        })
        
        result = handler.initFwHandler()
        assert result == True
    
    def test_get_firmware_info_success(self):
        """Test successful get_firmware_info"""
        expected_reply = {"version": "1.0.0", "build": "12345"}
        self.handler.send_cmd = MagicMock(return_value=True)
        self.handler.read_reply = MagicMock(return_value=expected_reply)
        
        result = self.handler.get_firmware_info()
        
        assert result == expected_reply
        self.handler.send_cmd.assert_called_once_with(cdb_consts.CDB_GET_FIRMWARE_INFO_CMD)
        self.handler.read_reply.assert_called_once_with(cdb_consts.CDB_GET_FIRMWARE_INFO_CMD)
    
    def test_get_firmware_info_send_failure(self):
        """Test get_firmware_info when send_cmd fails"""
        self.handler.send_cmd = MagicMock(return_value=False)
        
        result = self.handler.get_firmware_info()
        
        assert result == False
        self.handler.send_cmd.assert_called_once_with(cdb_consts.CDB_GET_FIRMWARE_INFO_CMD)
    
    @patch("builtins.open", new_callable=mock_open, read_data=b"A" * 512)
    def test_start_fw_download_success(self, mock_file):
        """Test successful start_fw_download"""
        self.handler.start_payload_size = 128
        self.handler.send_cmd = MagicMock(return_value=True)
        
        # Mock the file operations
        mock_file.return_value.seek.return_value = None
        mock_file.return_value.tell.return_value = 512  # Mock file size
        
        result = self.handler.start_fw_download("/path/to/firmware.bin")
        
        assert result == True
        mock_file.assert_called_once_with("/path/to/firmware.bin", 'rb')
        self.handler.send_cmd.assert_called_once()
        
        # Verify payload
        call_args = self.handler.send_cmd.call_args
        payload = call_args[0][1]
        assert payload["imgsize"] == 512
        assert payload["imghdr"] == b"A" * 128
        
    @patch("builtins.open", new_callable=mock_open, read_data=b"A" * 512)
    def test_start_fw_download_no_header(self, mock_file):
        """Test start_fw_download with no header required"""
        self.handler.start_payload_size = 0
        self.handler.send_cmd = MagicMock(return_value=True)
        
        # Mock the file operations
        mock_file.return_value.seek.return_value = None
        mock_file.return_value.tell.return_value = 512  # Mock file size
        
        result = self.handler.start_fw_download("/path/to/firmware.bin")
        
        assert result == True
        # Verify payload has None for header
        call_args = self.handler.send_cmd.call_args
        payload = call_args[0][1]
        assert payload["imgsize"] == 512
        assert payload["imghdr"] is None    
    
    @patch("builtins.open", new_callable=mock_open, read_data=b"A" * 50)
    def test_start_fw_download_file_too_small(self, mock_file):
        """Test start_fw_download with file too small for header"""
        self.handler.start_payload_size = 128
        
        # Mock the file operations
        mock_file.return_value.seek.return_value = None
        mock_file.return_value.tell.return_value = 50  # Mock file size
        
        with pytest.raises(ValueError, match="Firmware image file is too small"):
            self.handler.start_fw_download("/path/to/firmware.bin")
    
    def test_run_fw_image_default_params(self):
        """Test run_fw_image with default parameters"""
        self.handler.send_cmd = MagicMock(return_value=True)
        
        result = self.handler.run_fw_image()
        
        assert result == True
        self.handler.send_cmd.assert_called_once_with(
            cdb_consts.CDB_RUN_FIRMWARE_IMAGE_CMD,
            {"runmode": 0x0, "delay": 2},
            timeout=cdb_consts.CDB_RUN_FIRMWARE_CMD_TIMEOUT
        )
    
    def test_run_fw_image_custom_params(self):
        """Test run_fw_image with custom parameters"""
        self.handler.send_cmd = MagicMock(return_value=True)
        
        result = self.handler.run_fw_image(runmode=0x2, resetdelay=5)
        
        assert result == True
        self.handler.send_cmd.assert_called_once_with(
            cdb_consts.CDB_RUN_FIRMWARE_IMAGE_CMD,
            {"runmode": 0x2, "delay": 5},
            timeout=cdb_consts.CDB_RUN_FIRMWARE_CMD_TIMEOUT
        )
    
    def test_complete_fw_download(self):
        """Test complete_fw_download"""
        self.handler.send_cmd = MagicMock(return_value=True)
        
        result = self.handler.complete_fw_download()
        
        assert result == True
        self.handler.send_cmd.assert_called_once_with(cdb_consts.CDB_COMPLETE_FIRMWARE_DOWNLOAD_CMD)
    
    def test_commit_fw_image(self):
        """Test commit_fw_image"""
        self.handler.send_cmd = MagicMock(return_value=True)
        
        result = self.handler.commit_fw_image()
        
        assert result == True
        self.handler.send_cmd.assert_called_once_with(cdb_consts.CDB_COMMIT_FIRMWARE_IMAGE_CMD)
    
    def test_abort_fw_download(self):
        """Test abort_fw_download"""
        self.handler.send_cmd = MagicMock(return_value=True)
        
        result = self.handler.abort_fw_download()
        
        assert result == True
        self.handler.send_cmd.assert_called_once_with(cdb_consts.CDB_ABORT_FIRMWARE_DOWNLOAD_CMD)
    
    @patch("builtins.open", new_callable=mock_open)
    def test_download_fw_image_lpl_success(self, mock_file):
        """Test successful download_fw_image with LPL only"""
        # Setup file content
        file_data = b"H" * 128 + b"D" * 1024  # Header + Data
        mock_file.return_value.read.side_effect = [
            b"H" * 128,  # Header read
            b"D" * 1024,  # First data chunk
            b""  # EOF
        ]
        
        self.handler.start_payload_size = 128
        self.handler.rw_length_ext = 1024
        self.handler.is_lpl_only = True
        self.handler.write_lpl_block = MagicMock(return_value=True)
        
        result, bytes_written = self.handler.download_fw_image("/path/to/firmware.bin")
        
        assert result == True
        assert bytes_written == 1024
        self.handler.write_lpl_block.assert_called_once_with(0, b"D" * 1024)
    
    @patch("builtins.open", new_callable=mock_open)
    def test_download_fw_image_epl_success(self, mock_file):
        """Test successful download_fw_image with EPL"""
        # Setup file content
        mock_file.return_value.read.side_effect = [
            b"H" * 256,  # Header read
            b"D" * 2048,  # First data chunk
            b"E" * 1024,  # Second data chunk
            b""  # EOF
        ]
        
        self.handler.start_payload_size = 256
        self.handler.rw_length_ext = 2048
        self.handler.is_lpl_only = False
        self.handler.write_epl_pages = MagicMock(return_value=True)
        self.handler.write_epl_block = MagicMock(return_value=True)
        
        result, bytes_written = self.handler.download_fw_image("/path/to/firmware.bin")
        
        assert result == True
        assert bytes_written == 3072  # 2048 + 1024
        assert self.handler.write_epl_pages.call_count == 2
        assert self.handler.write_epl_block.call_count == 2
        
        # Verify calls
        calls = self.handler.write_epl_block.call_args_list
        assert calls[0] == call(0, b"D" * 2048)
        assert calls[1] == call(2048, b"E" * 1024)
    
    @patch("builtins.open", new_callable=mock_open)
    def test_download_fw_image_no_header(self, mock_file):
        """Test download_fw_image with no header required"""
        mock_file.return_value.read.side_effect = [
            b"D" * 512,  # Data chunk
            b""  # EOF
        ]
        
        self.handler.start_payload_size = 0
        self.handler.rw_length_ext = 1024
        self.handler.is_lpl_only = True
        self.handler.write_lpl_block = MagicMock(return_value=True)
        
        result, bytes_written = self.handler.download_fw_image("/path/to/firmware.bin")
        
        assert result == True
        assert bytes_written == 512
    
    @patch("builtins.open", new_callable=mock_open)
    def test_download_fw_image_epl_write_failure(self, mock_file):
        """Test download_fw_image with EPL write failure"""
        mock_file.return_value.read.side_effect = [
            b"H" * 128,  # Header
            b"D" * 1024,  # Data
        ]
        
        self.handler.start_payload_size = 128
        self.handler.rw_length_ext = 1024
        self.handler.is_lpl_only = False
        self.handler.write_epl_pages = MagicMock(return_value=True)
        self.handler.write_epl_block = MagicMock(return_value=False)
        
        result, bytes_written = self.handler.download_fw_image("/path/to/firmware.bin")
        
        assert result == False
        assert bytes_written == 0
    
    def test_download_fw_image_file_not_found(self):
        """Test download_fw_image with file not found"""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            result, bytes_written = self.handler.download_fw_image("/nonexistent/file.bin")
            
            assert result == False
            assert bytes_written == 0
    
    @patch("builtins.open", new_callable=mock_open, read_data=b"A" * 50)
    def test_download_fw_image_file_too_small(self, mock_file):
        """Test download_fw_image with file too small for header"""
        self.handler.start_payload_size = 128
        
        result, bytes_written = self.handler.download_fw_image("/path/to/firmware.bin")
        
        assert result == False
        assert bytes_written == 0
    
    @patch("builtins.open", new_callable=mock_open)
    def test_download_fw_image_generic_exception(self, mock_file):
        """Test download_fw_image with generic exception"""
        mock_file.return_value.read.side_effect = Exception("Test exception")
        self.handler.abort_fw_download = MagicMock(return_value=True)
        
        result, bytes_written = self.handler.download_fw_image("/path/to/firmware.bin")
        
        assert result == False
        assert bytes_written == 0
        self.handler.abort_fw_download.assert_called_once()
    
    @patch("builtins.open", new_callable=mock_open)
    def test_download_fw_image_multiple_chunks(self, mock_file):
        """Test download_fw_image with multiple data chunks"""
        # Setup multiple chunks
        mock_file.return_value.read.side_effect = [
            b"H" * 64,   # Header
            b"A" * 512,  # Chunk 1
            b"B" * 512,  # Chunk 2
            b"C" * 256,  # Chunk 3 (partial)
            b""          # EOF
        ]
        
        self.handler.start_payload_size = 64
        self.handler.rw_length_ext = 512
        self.handler.is_lpl_only = True
        self.handler.write_lpl_block = MagicMock(return_value=True)
        
        result, bytes_written = self.handler.download_fw_image("/path/to/firmware.bin")
        
        assert result == True
        assert bytes_written == 1280  # 512 + 512 + 256
        assert self.handler.write_lpl_block.call_count == 3
        
        # Verify calls
        calls = self.handler.write_lpl_block.call_args_list
        assert calls[0] == call(0, b"A" * 512)
        assert calls[1] == call(512, b"B" * 512)
        assert calls[2] == call(1024, b"C" * 256)
    
    def test_download_fw_image_empty_file_with_header(self):
        """Test download_fw_image with empty file when header is required"""
        with patch("builtins.open", mock_open(read_data=b"")):
            self.handler.start_payload_size = 128
            
            result, bytes_written = self.handler.download_fw_image("/path/to/empty.bin")
            
            assert result == False
            assert bytes_written == 0
    
    def test_download_fw_image_empty_file_no_header(self):
        """Test download_fw_image with empty file when no header required"""
        with patch("builtins.open", mock_open(read_data=b"")):
            self.handler.start_payload_size = 0
            
            result, bytes_written = self.handler.download_fw_image("/path/to/empty.bin")
            
            assert result == True
            assert bytes_written == 0


# Integration tests
class TestCdbFwHandlerIntegration:
    """Integration tests for CdbFwHandler"""
    
    @patch("builtins.open", new_callable=mock_open)
    def test_full_firmware_update_flow_lpl(self, mock_file):
        """Test complete firmware update flow with LPL"""
        # Setup
        reader = MagicMock()
        writer = MagicMock()
        mem_map = MagicMock()
        
        # Mock successful initialization
        with patch.object(CdbFwHandler, 'send_cmd', return_value=True):
            with patch.object(CdbFwHandler, 'read_reply', return_value={
                cdb_consts.CDB_START_CMD_PAYLOAD_SIZE: 64,
                cdb_consts.CDB_WRITE_MECHANISM: "LPL",
                cdb_consts.CDB_READ_WRITE_LENGTH_EXT: 240
            }):
                handler = CdbFwHandler(reader, writer, mem_map)
        
        # Setup file content and operations for start_fw_download
        mock_file.return_value.read.side_effect = [
            b"H" * 64,   # Header for start
            b"H" * 64,   # Header for download
            b"D" * 248,  # Data chunk
            b""          # EOF
        ]
        mock_file.return_value.seek.return_value = None
        mock_file.return_value.tell.return_value = 312  # 64 + 248
        
        # Mock methods
        handler.send_cmd = MagicMock(return_value=True)
        handler.write_lpl_block = MagicMock(return_value=True)
        
        # Execute full flow
        assert handler.start_fw_download("/path/to/fw.bin") == True
        result, bytes_written = handler.download_fw_image("/path/to/fw.bin")
        print(f"Download result: {result}, Bytes written: {bytes_written}")
        assert handler.complete_fw_download() == True
        assert handler.run_fw_image() == True
        assert handler.commit_fw_image() == True