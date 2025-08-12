"""
   cdb.py

   CDB Command handler
"""

import time
from ..fields import cdb_consts
from ..xcvr_eeprom import XcvrEeprom

class CdbCmdHandler(XcvrEeprom):
    def __init__(self, reader, writer, mem_map):
        super(CdbCmdHandler, self).__init__(reader, writer, mem_map)

    def read_reply(self, cdb_cmd_id):
        """
        Read a reply from the CDB
        """
        cdb_cmd = self.mem_map.get_cdb_cmd(cdb_cmd_id)
        reply_field = cdb_cmd.get_reply_field()
        if reply_field is not None:
            return self.read(reply_field)
        return None

    def write_cmd(self, cdb_cmd_id, payload=None):
        """
        Write CDB command
        """
        cdb_cmd = self.mem_map.get_cdb_cmd(cdb_cmd_id)
        if payload is not None:
            bytes = cdb_cmd.encode(payload)
        else:
            bytes = cdb_cmd.encode()
        # TODO Check the module capability CdbCommandTriggerMethod to write in single I2C transaction
        # Write the bytes starting from the 3rd byte(0x9F:130)
        self.writer(cdb_cmd.getaddr() + 2, len(bytes) - 2, bytes[2:])
        # Finally write the first two CMD bytes to trigger CDB processing
        return self.writer(cdb_cmd.getaddr(), 2, bytes[:2])
    
    def write_epl_page(self, page, data):
        """
        Write a page of data to the EPL page
        """
        # Write the data to the specified page and offset
        assert len(data) <= cdb_consts.PAGE_SIZE, \
                                    "Data length exceeds page size"
        assert page >= cdb_consts.EPL_PAGE, \
                    "Page number must be greater than or equal to 0xA0"
        return self.write_raw((page * cdb_consts.PAGE_SIZE) + 128, len(data), data)


    def wait_for_cdb_status(self, timeout=None):
        """
        Wait for CDB status to be ready
        Returns False if failed to get the status
        True otherwise
        """
        delay = 0
        if timeout is None:
            timeout = cdb_consts.CDB_MAX_ACCESS_HOLD_OFF_PERIOD  + 5000  # 5 sec safety margin
        status = None

        assert timeout > delay, "Timeout must be greater than delay"

        while (delay < timeout):
            time.sleep(cdb_consts.CDB_MAX_CAPTURE_TIME / 1000)
            delay += cdb_consts.CDB_MAX_CAPTURE_TIME

            status = self.read(cdb_consts.CDB1_CMD_STATUS)
            if (status is None) or \
                    (True == status[cdb_consts.CDB1_IS_BUSY]):
                continue

            if (True == status[cdb_consts.CDB1_HAS_FAILED]):
                break

            if (False == status[cdb_consts.CDB1_IS_BUSY]) and \
                    (False == status[cdb_consts.CDB1_HAS_FAILED]):
                break

        if delay >= timeout or status is None:
            return [False, status]

        return [True, status]

    def send_cmd(self, cdb_cmd_id, payload=None, timeout=None):
        """
        Send CDB command, wait for completion and check status
        """
        # Write the command to the CDB
        if True != self.write_cmd(cdb_cmd_id, payload):
            print(f"Failed to write CDB command: {cdb_cmd_id}")
            return None

        # Wait for the command to complete
        ret, status = self.wait_for_cdb_status(timeout)
        if not ret:
            print(f"CDB command: {cdb_cmd_id} failed to complete or read status")
            return None

        is_busy = status[cdb_consts.CDB1_IS_BUSY]
        if True == is_busy:
            print(f"CDB command: {cdb_cmd_id} is busy with status: {status[cdb_consts.CDB1_STATUS]}")
            return False

        is_failed = status[cdb_consts.CDB1_HAS_FAILED]
        if True == is_failed:
            print(f"CDB command: {cdb_cmd_id} failed with status: {status[cdb_consts.CDB1_STATUS]}")
            return False

        return status[cdb_consts.CDB1_STATUS] == 0x1

    def get_last_cmd_status(self):
        """
        Get the status of the last CDB command
        Returns None if Module failed to reply to I2C command
        """
        status = self.read(cdb_consts.CDB1_COMMAND_RESULT)
        return status
    
    def write_lpl_block(self, blkaddr, blkdata):
        """
        Write LPL block
        """
        payload = {
            "blkaddr" : blkaddr,
            "blkdata" : blkdata
        }
        # Send the CDB write firmware LPL command
        if True != self.write_cmd(cdb_consts.CDB_WRITE_FIRMWARE_LPL_CMD, payload):
            status = self.get_last_cmd_status()
            print(f"Write LPL block status: {status}")

    def write_epl_pages(self, blkdata):
        """
        Write EPL pages starting from page 0xA0
        """
        pages = len(blkdata) // cdb_consts.PAGE_SIZE
        assert pages <= cdb_consts.EPL_MAX_PAGES, "Data exceeds maximum number of EPL pages"

        for page in range(pages):
            page_data = blkdata[page * cdb_consts.PAGE_SIZE : (page + 1) * cdb_consts.PAGE_SIZE]
            assert True == self.write_epl_page(page + cdb_consts.EPL_PAGE, page_data)

        # Handle any remaining data that doesn't fit into a full page
        if len(blkdata) % cdb_consts.PAGE_SIZE != 0:
            remaining_data = blkdata[pages * cdb_consts.PAGE_SIZE:]
            assert True == self.write_epl_page(pages + cdb_consts.EPL_PAGE, remaining_data)

    def write_epl_block(self, blkaddr, blkdata):
        """
        Write EPL block
        """
        payload = {
            "blkaddr" : blkaddr,
            "blkdata" : blkdata
        }

        # Send the CDB write firmware EPL command
        return self.send_cmd(cdb_consts.CDB_WRITE_FIRMWARE_EPL_CMD, payload)
