"""
   cdb_fw.py

   CDB Firmware Management Command handler
   CMD : 0100h to 011Fh
"""

from ..fields import cdb_consts
from .cdb import CdbCmdHandler

class CdbFwHandler(CdbCmdHandler):
    def __init__(self, reader, writer, mem_map):
        super(CdbFwHandler, self).__init__(reader, writer, mem_map)
        self.start_payload_size = 0
        self.is_lpl_only = False
        self.rw_length_ext = 0

        if not self.initFwHandler():
            # Don’t kill the whole xcvr API if FW mgmt isn’t supported
            print("Warning: CDB firmware handler init failed; disabling FW mgmt for this module")
            # Leave defaults; FW-mgmt calls can just return failure later.
            return

    def initFwHandler(self):
        """
        Initialize the firmware handler
        """
        if True != self.send_cmd(cdb_consts.CDB_GET_FIRMWARE_MGMT_FEATURES_CMD):
            print("Failed to get firmware management features")
            return False

        # Read the firmware management features
        reply = self.read_reply(cdb_consts.CDB_GET_FIRMWARE_MGMT_FEATURES_CMD)
        if reply is None:
            print("Failed to read firmware management features")
            return False

        self.start_payload_size = reply[cdb_consts.CDB_START_CMD_PAYLOAD_SIZE]
        self.is_lpl_only = reply[cdb_consts.CDB_WRITE_MECHANISM] == "LPL"
        self.rw_length_ext = reply[cdb_consts.CDB_READ_WRITE_LENGTH_EXT] + 8

        if self.is_lpl_only:
            self.rw_length_ext = min(cdb_consts.LPL_MAX_PAYLOAD_SIZE, self.rw_length_ext)
        else:
            self.rw_length_ext = min(cdb_consts.EPL_MAX_PAYLOAD_SIZE, self.rw_length_ext)

        return True

    def get_firmware_info(self):
        """
        Get firmware information
        """
        if True != self.send_cmd(cdb_consts.CDB_GET_FIRMWARE_INFO_CMD):
            print("Failed to get firmware info")
            return False

        # Read the firmware info
        return self.read_reply(cdb_consts.CDB_GET_FIRMWARE_INFO_CMD)

    def start_fw_download(self, imgpath):
        """
        Start firmware download
        :param imgpath: path to the firmware image
        """
        with open(imgpath, 'rb') as fw_file:
            fw_file.seek(0, 2)  # Move to the end of the file
            filesize = fw_file.tell() # Get the file size
            fw_file.seek(0, 0)  # Move back to the start of the file
            # Read the image file header bytes
            header_data = None
            if self.start_payload_size > 0:
                header_data = fw_file.read(self.start_payload_size)
                if len(header_data) < self.start_payload_size:
                    raise ValueError(f"Firmware image file is too small < {self.start_payload_size} bytes for header")

        # Verify the header with the module
        payload = {
            "imgsize" : filesize,
            "imghdr" : header_data
        }

        # Send the CDB start firmware download command
        return self.send_cmd(cdb_consts.CDB_START_FIRMWARE_DOWNLOAD_CMD, payload)

    def download_fw_image(self, imgpath):
        """
        Download firmware image using the CDB command(LPL or EPL)
        :param imgpath: path to the firmware image
        """
        try:
            with open(imgpath, 'rb') as fw_file:
                # Step 1. Read the initial payload (header)
                # TODO Skip the header using fseek
                header_data = None
                if self.start_payload_size > 0:
                    header_data = fw_file.read(self.start_payload_size)
                    if len(header_data) < self.start_payload_size:
                        raise ValueError(f"Firmware image file is too small: expected at least {self.start_payload_size} bytes for header")

                # 2 Read and write firmware data in chunks, handling partial chunks
                blkaddr = 0
                while True:
                    # Read a chunk of data up to self.rw_length_ext bytes
                    blkdata = fw_file.read(self.rw_length_ext)

                    # Exit loop if no more data
                    if not blkdata:
                        break

                    # TODO Handle LPL only supported case
                    # TODO Handle auto paging for EPL
                    # Write the block data to the EPL
                    if self.is_lpl_only:
                        self.write_lpl_block(blkaddr, blkdata)
                    else:
                        # For EPL, write the data in pages
                        self.write_epl_pages(blkdata)
                        if True != self.write_epl_block(blkaddr, blkdata):
                            print(f"Failed to write EPL block at address {blkaddr}")
                            return False, blkaddr

                    # Update address for next chunk by the actual number of bytes written
                    blkaddr += len(blkdata)

                return True, blkaddr  # Return success and total bytes written

        except FileNotFoundError:
            print(f"Error: Firmware image file not found: {imgpath}")
            return False, 0
        except ValueError as ve:
            print(f"Error: {str(ve)}")
            return False, 0
        except Exception as e:
            print(f"Error downloading firmware image: {str(e)}")
            self.abort_fw_download()  # Abort on error
        return False, 0

    def run_fw_image(self, runmode=0x0, resetdelay=2):
            """
            Run the firmware image(default is non-hitless reset)
            :param runmode: 0x0: run the image, 0x1:
            reset the module, 0x2: run and reset
            """
            payload = {
                "runmode" : runmode,
                "delay" : resetdelay
            }

            # Send the CDB run firmware image command
            return self.send_cmd(cdb_consts.CDB_RUN_FIRMWARE_IMAGE_CMD, payload,
                                timeout=cdb_consts.CDB_RUN_FIRMWARE_CMD_TIMEOUT)

    def complete_fw_download(self):
        """
        Complete the firmware download
        """
        # Send the CDB complete firmware download command
        return self.send_cmd(cdb_consts.CDB_COMPLETE_FIRMWARE_DOWNLOAD_CMD)

    def commit_fw_image(self):
        return self.send_cmd(cdb_consts.CDB_COMMIT_FIRMWARE_IMAGE_CMD)

    def abort_fw_download(self):
        return self.send_cmd(cdb_consts.CDB_ABORT_FIRMWARE_DOWNLOAD_CMD)

