"""
   cdb.py

   CDB Command handler
"""

import struct
import time
from sonic_py_common.syslogger import SysLogger
from ..fields import cdb_consts
from ..xcvr_eeprom import XcvrEeprom

SYSLOG_IDENTIFIER = "Cdb"
log = SysLogger(SYSLOG_IDENTIFIER)
log.logger.propagate = False

class CdbCmdHandler(XcvrEeprom):
    def __init__(self, reader, writer, mem_map):
        super(CdbCmdHandler, self).__init__(reader, writer, mem_map)
        self.last_cmd_status = None

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
            timeout = cdb_consts.CDB_MAX_ACCESS_HOLD_OFF_PERIOD + cdb_consts.CDB_TIMEOUT_SAFETY_MARGIN
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
        self.last_cmd_status = None
        # Write the command to the CDB
        if True != self.write_cmd(cdb_cmd_id, payload):
            log.log_notice("Failed to write CDB command: {}".format(cdb_cmd_id))
            return None

        # Wait for the command to complete
        ret, status = self.wait_for_cdb_status(timeout)
        self.last_cmd_status = status
        if not ret:
            log.log_notice("CDB command: {} failed to complete or read status".format(cdb_cmd_id))
            return None

        is_busy = status[cdb_consts.CDB1_IS_BUSY]
        if True == is_busy:
            log.log_notice("CDB command: {} is busy with status: {}".format(cdb_cmd_id, status[cdb_consts.CDB1_STATUS]))
            return False

        is_failed = status[cdb_consts.CDB1_HAS_FAILED]
        if True == is_failed:
            log.log_notice("CDB command: {} failed with status: {}".format(cdb_cmd_id, status[cdb_consts.CDB1_STATUS]))
            return False

        return status[cdb_consts.CDB1_STATUS] == 0x1

    def get_last_cmd_status(self):
        """
        Get the status of the last CDB command
        Returns None if Module failed to reply to I2C command
        """
        status = self.read(cdb_consts.CDB1_COMMAND_RESULT)
        return status

    def get_cmd_status_code(self):
        """
        Get the cached status dict from the last send_cmd call.
        Returns None if no command was sent or I2C failed.
        """
        return self.last_cmd_status

    def _get_cmis_rev(self):
        """
        Read the CMIS revision the module complies to (00h:1).

        Returns a (major, minor) tuple, or None if it could not be read.
        """
        rev = self.read(cdb_consts.CDB_CMIS_REVISION)
        if rev is None:
            return None
        return (rev >> 4, rev & 0x0F)

    def _supports_password_cmd_result(self):
        """
        Whether the PasswordCmdResult register (00h:42.3-0) is defined for this
        module. It was introduced in CMIS 5.3; on earlier modules those bits are
        reserved, so their value must not be used to judge password acceptance.

        Returns False if the CMIS revision cannot be determined, so the code
        does not interpret a reserved register on a legacy module.
        """
        rev = self._get_cmis_rev()
        return rev is not None and rev >= cdb_consts.CDB_PASSWORD_RESULT_MIN_CMIS_REV

    def _read_password_cmd_result(self):
        """
        Poll PasswordCmdResult (00h:42.3-0) until validation completes.

        Per CMIS 8.2.14, after a password entry/change WRITE the module updates
        PasswordCmdResult within tWRITE, and until then may report "validation
        in progress" or reject reads of the register. Poll past those transient
        states, bounded by CDB_PASSWORD_RESULT_POLL_TIMEOUT.

        Returns the 4-bit result code, or None if it could not be determined
        within the timeout.
        """
        elapsed = 0
        while elapsed < cdb_consts.CDB_PASSWORD_RESULT_POLL_TIMEOUT:
            result = self.read(cdb_consts.CDB_PASSWORD_CMD_RESULT)
            if result is not None and \
                    result != cdb_consts.CDB_PASSWORD_RESULT_IN_PROGRESS:
                return result
            time.sleep(cdb_consts.CDB_PASSWORD_RESULT_POLL_INTERVAL / 1000)
            elapsed += cdb_consts.CDB_PASSWORD_RESULT_POLL_INTERVAL
        return None

    def _enter_password_via_cdb(self, password):
        """
        Enter the host password via CDB command 0001h. Fallback for modules that
        do not unlock via the Password Entry Area.
        """
        payload = {"password": password}
        return self.send_cmd(cdb_consts.CDB_ENTER_PASSWORD_CMD, payload)

    def enter_password(self, password=cdb_consts.CDB_DEFAULT_PASSWORD):
        """
        Enter the CMIS host password to unlock protected CDB/EEPROM access.

        Per CMIS 8.2.14 the password is entered by writing the 4-byte value
        (MSB first) to the Password Entry Area at page 00h bytes 122-125. The
        write succeeding at the transport level does NOT mean the password was
        accepted: validation is asynchronous and its outcome is reported in the
        PasswordCmdResult register (00h:42.3-0). So:
          1. Write the password to the Password Entry Area (standard method).
          2. Read PasswordCmdResult to learn whether it was accepted -- but only
             on CMIS 5.3+ modules, where that register is defined. On earlier
             modules the register is reserved, so a successful write is taken
             at face value (best-effort); a module that only unlocks via CDB
             command 0001h is handled reactively by the caller, which re-enters
             the password when a protected CDB command returns
             CDB_PASSWORD_ERROR_STATUS.
          3. Fall back to CDB command 0001h only when the register method is not
             usable (transport write failed, or -- on a 5.3+ module -- the
             PasswordCmdResult could not be determined), for modules that unlock
             via the CDB command.
        A password a 5.3+ module explicitly rejects (PasswordCmdResult = "not
        accepted") is NOT retried via CDB, since the same wrong password would
        be rejected again.

        Returns True if the password was accepted (or, pre-5.3, delivered),
        False/None otherwise.
        """
        if not isinstance(password, int) or \
                password < 0 or password > 0xFFFFFFFF:
            log.log_notice("Invalid password: must be an integer in range 0..0xFFFFFFFF")
            return False

        # Preferred: write the password to the Password Entry Area (MSB first).
        pwd_bytes = bytearray(struct.pack(">I", password))
        if not self.write_raw(cdb_consts.CDB_HOST_PASSWORD_ENTRY_OFFSET,
                              cdb_consts.CDB_HOST_PASSWORD_ENTRY_SIZE, pwd_bytes):
            log.log_notice("Password Entry Area write failed; falling back to CDB command 0001h")
            return self._enter_password_via_cdb(password)

        # PasswordCmdResult (00h:42.3-0) only exists on CMIS 5.3+. On earlier
        # modules the Password Entry Area write is the standard mechanism and
        # there is no register to confirm acceptance, so treat the successful
        # write as success and let the caller's CDB_PASSWORD_ERROR_STATUS path
        # cover modules that unlock only via CDB command 0001h.
        if not self._supports_password_cmd_result():
            return True

        # The write only delivered the password; its acceptance is reported
        # asynchronously in PasswordCmdResult (00h:42.3-0).
        result = self._read_password_cmd_result()
        if result in (cdb_consts.CDB_PASSWORD_RESULT_HOST_ACCEPTED,
                      cdb_consts.CDB_PASSWORD_RESULT_MODULE_ACCEPTED):
            return True

        if result == cdb_consts.CDB_PASSWORD_RESULT_NOT_ACCEPTED:
            # Module honored the Password Entry Area and rejected the password;
            # the CDB command would reject the same password too.
            log.log_notice("Password not accepted by the module (PasswordCmdResult=0x3)")
            return False

        # 5.3+ module but the result is NOT_SUPPORTED or could not be
        # determined: the register method is not usable here, fall back to the
        # CDB command.
        log.log_notice("PasswordCmdResult unavailable (result={}); "
                       "falling back to CDB command 0001h".format(result))
        return self._enter_password_via_cdb(password)
    
    def write_lpl_block(self, blkaddr, blkdata, timeout=None):
        """
        Write LPL block
        """
        payload = {
            "blkaddr" : blkaddr,
            "blkdata" : blkdata
        }
        # Send the CDB write firmware LPL command
        return self.send_cmd(cdb_consts.CDB_WRITE_FIRMWARE_LPL_CMD, payload, timeout=timeout)

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

    def write_epl_block(self, blkaddr, blkdata, timeout=None):
        """
        Write EPL block
        """
        payload = {
            "blkaddr" : blkaddr,
            "blkdata" : blkdata
        }

        # Send the CDB write firmware EPL command
        return self.send_cmd(cdb_consts.CDB_WRITE_FIRMWARE_EPL_CMD, payload, timeout=timeout)
