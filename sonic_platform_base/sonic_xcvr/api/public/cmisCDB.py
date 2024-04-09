"""
    cmisCDB.py

    Implementation of APIs related to CDB commands
"""
import logging
from ...fields import consts
from ..xcvr_api import XcvrApi
import struct
import time

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

LPLPAGE = 0x9f
CDB_RPL_OFFSET = 136
CDB_WRITE_MSG_START = 130
PAGE_LENGTH = 128
INIT_OFFSET = 128
CMDLEN = 2
MAX_WAIT = 600


class CmisCdbApi(XcvrApi):
    def __init__(self, xcvr_eeprom):
        super(CmisCdbApi, self).__init__(xcvr_eeprom)
        self.cdb_instance_supported = self.xcvr_eeprom.read(consts.CDB_SUPPORT)
        self.failed_status_dict = self.xcvr_eeprom.mem_map.codes.CDB_FAIL_STATUS
        #assert self.cdb_instance_supported != 0

    def cdb1_chkflags(self):
        '''
        This function detects if there is datapath or module firmware fault.
        If there is no firmware fault, it checks if CDB command completes.
        It retruns True if the CDB command is incomplete and returns False if complete

        Bit 7: L-Cdb2CommandComplete Latched Flag to indicate completion of the CDB command
        for CDB block 2. Support is advertised in field 01h:163.7-6

        Bit 6: L-Cdb1CommandComplete Latched Flag to indicate completion of the CDB command
        for CDB block 1. Support is advertised in field 01h:163.7-6

        Bit 5-3: - Reserved

        Bit 2: L-DataPathFirmwareFault Latched Flag to indicate that subordinated firmware in an
        auxiliary device for processing transmitted or received
        signals (e.g. a DSP) has failed.

        Bit 1: L-ModuleFirmwareFault Latched Flag to indicate that self-supervision of the main
        module firmware has detected a failure in the main module
        firmware itself. There are several possible causes of the
        error such as program memory becoming corrupted and
        incomplete firmware loading.

        Bit 0: L-ModuleStateChanged Latched Flag to indicate a Module State Change
        '''
        status = self.xcvr_eeprom.read(consts.MODULE_FIRMWARE_FAULT_INFO)
        datapath_firmware_fault = bool((status >> 2) & 0x1)
        module_firmware_fault = bool((status >> 1) & 0x1)
        cdb1_command_complete = bool((status >> 6) & 0x1)
        assert not datapath_firmware_fault
        assert not module_firmware_fault
        if cdb1_command_complete:
            return False
        else:
            return True

    def cdb_chkcode(self, cmd):
        '''
        This function calculates and returns the checksum of a CDB command
        '''
        checksum = 0
        for byte in cmd:
            checksum += byte
        return 0xff - (checksum & 0xff)

    def cdb1_chkstatus(self):
        '''
        This function checks the CDB status.
        The format of returned values is busy flag, failed flag and cause

        CDB command status
        Bit 7: CdbIsBusy
        Bit 6: CdbHasFailed
        Bit 5-0: CdBCommandResult
        Coarse Status     CdbIsBusy       CdbHasFailed
        IN PROGRESS       1               X (dont care)
        SUCCESS           0               0
        FAILED            0               1

        IN PROGRESS
            00h=Reserved
            01h=Command is captured but not processed
            02h=Command checking is in progress
            03h=Previous CMD was ABORTED by CMD Abort
            04h-1Fh=Reserved
            20h-2Fh=Reserved
            30h-3Fh=Custom

        SUCCESS
            00h=Reserved
            01h=Command completed successfully
            02h=Reserved
            03h=Previous CMD was ABORTED by CMD Abort
            04h-1Fh=Reserved
            20h-2Fh=Reserved
            30h-3Fh=Custom

        FAILED
            00h=Reserved
            01h=CMDCode unknown
            02h=Parameter range error or parameter not supported
            03h=Previous CMD was not ABORTED by CMD Abort
            04h=Command checking time out
            05h=CdbCheckCode Error
            06h=Password related error (command specific meaning)
            07h=Command not compatible with operating status
            08h-0Fh=Reserved for STS command checking error
            10h-1Fh=Reserved
            20h-2Fh=For individual STS command or task error
            30h-3Fh=Custom
        '''
        status = self.xcvr_eeprom.read(consts.CDB1_STATUS)
        is_busy = bool(((0x80 if status is None else status) >> 7) & 0x1)
        cnt = 0
        while is_busy and cnt < MAX_WAIT:
            time.sleep(0.1)
            status = self.xcvr_eeprom.read(consts.CDB1_STATUS)
            is_busy = bool(((0x80 if status is None else status) >> 7) & 0x1)
            cnt += 1
        return status

    def write_cdb(self, cmd):
        '''
        This function writes a CDB command to page 0x9f
        '''
        self.xcvr_eeprom.write_raw(LPLPAGE*PAGE_LENGTH+CDB_WRITE_MSG_START, len(cmd)-CMDLEN, cmd[CMDLEN:])
        self.xcvr_eeprom.write_raw(LPLPAGE*PAGE_LENGTH+INIT_OFFSET, CMDLEN, cmd[:CMDLEN])

    def read_cdb(self):
        '''
        This function reads the reply of a CDB command from page 0x9f.
        It returns the reply message of a CDB command.
        rpllen is the length (number of bytes) of rpl
        rpl_chkcode is the check code of rpl and can be calculated by cdb_chkcode()
        rpl is the reply message.
        '''
        rpllen = self.xcvr_eeprom.read(consts.CDB_RPL_LENGTH)
        rpl_chkcode = self.xcvr_eeprom.read(consts.CDB_RPL_CHKCODE)
        rpl = self.xcvr_eeprom.read_raw(LPLPAGE*PAGE_LENGTH+CDB_RPL_OFFSET, rpllen)
        return rpllen, rpl_chkcode, rpl

    # Query status
    def query_cdb_status(self):
        '''
        This QUERY Status command may be used to retrieve the password acceptance
        status and to perform a test of the CDB interface.
        It returns the reply message of this CDB command 0000h.
        '''
        cmd = bytearray(b'\x00\x00\x00\x00\x02\x00\x00\x00\x00\x10')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Query CDB status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Query CDB status: Fail- ' + status_txt
        else:
            txt = 'Query CDB status: Success'
        logger.info(txt)
        return self.read_cdb()

    # Enter password
    def module_enter_password(self, psw = 0x00001011):
        '''
        The Enter Password command allows the host to enter a host password
        The default host password is 00001011h. CDB command 0001h puts the
        password in Page 9Fh, Byte 136-139.
        It returns the status of CDB command 0001h
        '''
        psw = struct.pack('>L', psw)
        cmd = bytearray(b'\x00\x01\x00\x00\x04\x00\x00\x00') + psw
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Enter password status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Enter password status: Fail- ' + status_txt
        else:
            txt = 'Enter password status: Success'
        logger.info(txt)
        return status

    def get_module_feature(self):
        '''
        This command is used to query which CDB commands are supported.
        It returns the reply message of this CDB command 0040h.
        '''
        cmd = bytearray(b'\x00\x40\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Get module feature status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Get module feature status: Fail- ' + status_txt
        else:
            txt = 'Get module feature status: Success'
        logger.info(txt)
        return self.read_cdb()

    # Firmware Update Features Supported
    def get_fw_management_features(self):
        '''
        This command is used to query supported firmware update features
        It returns the reply message of this CDB command 0041h.
        '''
        cmd = bytearray(b'\x00\x41\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Get firmware management feature status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Get firmware management feature status: Fail- ' + status_txt
        else:
            txt = 'Get firmware management feature status: Success'
        logger.info(txt)
        return self.read_cdb()

    # Get FW info
    def get_fw_info(self):
        '''
        This command returns the firmware versions and firmware default running
        images that reside in the module
        It returns the reply message of this CDB command 0100h.
        '''
        cmd = bytearray(b'\x01\x00\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Get firmware info status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Get firmware info status: Fail- ' + status_txt
        else:
            txt = 'Get firmware info status: Success'
        logger.info(txt)
        return self.read_cdb()

    # Start FW download
    def start_fw_download(self, startLPLsize, header, imagesize):
        '''
        This command starts the firmware download
        It returns the status of CDB command 0101h
        '''
        # pwd_status = self.module_enter_password()
        # logger.info('Module password enter status is %d' %pwd_status)
        logger.info("Image size is {}".format(imagesize))
        cmd = bytearray(b'\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        cmd[132-INIT_OFFSET] = startLPLsize + 8
        cmd[136-INIT_OFFSET] = (imagesize >> 24) & 0xff
        cmd[137-INIT_OFFSET] = (imagesize >> 16) & 0xff
        cmd[138-INIT_OFFSET] = (imagesize >> 8)  & 0xff
        cmd[139-INIT_OFFSET] = (imagesize >> 0)  & 0xff
        cmd += header
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        time.sleep(2)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Start firmware download status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Start firmware download status: Fail- ' + status_txt
        else:
            txt = 'Start firmware download status: Success'
        logger.info(txt)
        return status

    # Abort FW download
    def abort_fw_download(self):
        '''
        This command aborts the firmware download
        It returns the status of CDB command 0102h
        '''
        # pwd_status = self.module_enter_password()
        # logger.info('Module password enter status is %d' %pwd_status)
        cmd = bytearray(b'\x01\x02\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Abort firmware download status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Abort firmware download status: Fail- ' + status_txt
        else:
            txt = 'Abort firmware download status: Success'
        logger.info(txt)
        return status

    # Download FW with LPL
    def block_write_lpl(self, addr, data):
        '''
        This command writes one block of the firmware image into the LPL
        It returns the status of CDB command 0103h
        '''
        # lpl_len includes 136-139, four bytes, data is 116-byte long.
        lpl_len = len(data) + 4
        cmd = bytearray(b'\x01\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        cmd[132-INIT_OFFSET] = lpl_len & 0xff
        cmd[136-INIT_OFFSET] = (addr >> 24) & 0xff
        cmd[137-INIT_OFFSET] = (addr >> 16) & 0xff
        cmd[138-INIT_OFFSET] = (addr >> 8)  & 0xff
        cmd[139-INIT_OFFSET] = (addr >> 0)  & 0xff
        # pad data to 116 bytes just in case, make sure to fill all 0x9f page
        paddedPayload = data.ljust(116, b'\x00')
        cmd += paddedPayload
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'LPL firmware download status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'LPL firmware download status: Fail- ' + status_txt
        else:
            txt = 'LPL firmware download status: Success'
        logger.info(txt)
        return status

    #  Download FW with EPL
    def block_write_epl(self, addr, data, autopaging_flag, writelength):
        '''
        This command writes one block of the firmware image into the EPL
        It returns the status of CDB command 0104h
        '''
        epl_len = len(data)
        subtime = time.time()
        if not autopaging_flag:
            pages = epl_len // PAGE_LENGTH
            if (epl_len % PAGE_LENGTH) != 0:
                pages += 1
            # write to page 0xA0 - 0xAF (max of 16 pages)
            for pageoffset in range(pages):
                next_page = 0xa0 + pageoffset
                if PAGE_LENGTH*(pageoffset + 1) <= epl_len:
                    datachunk = data[PAGE_LENGTH*pageoffset : PAGE_LENGTH*(pageoffset + 1)]
                    self.xcvr_eeprom.write_raw(next_page*PAGE_LENGTH+INIT_OFFSET, PAGE_LENGTH, datachunk)
                else:
                    datachunk = data[PAGE_LENGTH*pageoffset : ]
                    self.xcvr_eeprom.write_raw(next_page*PAGE_LENGTH+INIT_OFFSET, len(datachunk), datachunk)
        else:
            sections = epl_len // writelength
            if (epl_len % writelength) != 0:
                sections += 1
            # write to page 0xA0 - 0xAF (max of 16 pages), with length of writelength per piece
            for offset in range(0, epl_len, writelength):
                if offset + writelength <= epl_len:
                    datachunk = data[offset : offset + writelength]
                    self.xcvr_eeprom.write_raw(0xA0*PAGE_LENGTH+offset+INIT_OFFSET, writelength, datachunk)
                else:
                    datachunk = data[offset : ]
                    self.xcvr_eeprom.write_raw(0xA0*PAGE_LENGTH+offset+INIT_OFFSET, len(datachunk), datachunk)
        subtimeint = time.time()-subtime
        logger.info('%dB write time:  %.2fs' %(epl_len, subtimeint))
        cmd = bytearray(b'\x01\x04\x08\x00\x04\x00\x00\x00')
        addr_byte = struct.pack('>L',addr)
        cmd += addr_byte
        cmd[130-INIT_OFFSET] = (epl_len >> 8) & 0xff
        cmd[131-INIT_OFFSET] =  epl_len       & 0xff
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'EPL firmware download status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'EPL firmware download status: Fail- ' + status_txt
        else:
            txt = 'EPL firmware download status: Success'
        logger.info(txt)
        return status

    # FW download complete
    def validate_fw_image(self):
        '''
        When this command is issued, the module shall validate the complete
        image and then return success or failure
        It returns the status of CDB command 0107h
        '''
        cmd = bytearray(b'\x01\x07\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Firmware download complete status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Firmware download complete status: Fail- ' + status_txt
        else:
            txt = 'Firmware download complete status: Success'
        logger.info(txt)
        return status

    # Run FW image
    # mode:
    # 00h = Traffic affecting Reset to Inactive Image.
    # 01h = Attempt Hitless Reset to Inactive Image
    # 02h = Traffic affecting Reset to Running Image.
    # 03h = Attempt Hitless Reset to Running Image
    def run_fw_image(self, mode = 0x01):
        '''
        The host uses this command to run a selected image from module internal firmware banks
        It returns the status of CDB command 0109h
        '''
        cmd = bytearray(b'\x01\x09\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00')
        cmd[137-INIT_OFFSET] = mode
        cmd[138-INIT_OFFSET] = 2 # Delay to Reset 512 ms
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        delay = int.from_bytes(cmd[138-INIT_OFFSET:138+2-INIT_OFFSET], byteorder='big') + 50 # Add few ms on setting time.
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Run firmware status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Run firmware status: Fail- ' + status_txt
        else:
            txt = 'Run firmware status: Success'
        logger.info(txt)
        time.sleep(delay/1000) # Wait "delay time" to avoid other cmd sent before "run_fw_image" start.
        return status

    # Commit FW image
    def commit_fw_image(self):
        '''
        A Commit is the process where the running image is set to be the image to be used on exit from module
        reset. In other words, a committed image is the image that will run and is expected to be a 'good' firmware
        version to run upon any resets (including watch dog).

        This command is used to switch the committed image after the firmware update process, when the new
        firmware is running and when the host has determined that the new firmware is working properly. The module
        shall only execute a Commit Image command on the image that it is currently running. If a non-running image
        is allowed to be committed, it is possible that a bad version may be committed and attempted to run after the
        next module reset.

        It returns the status of CDB command 010Ah
        '''
        cmd = bytearray(b'\x01\x0A\x00\x00\x00\x00\x00\x00')
        cmd[133-INIT_OFFSET] = self.cdb_chkcode(cmd)
        self.write_cdb(cmd)
        status = self.cdb1_chkstatus()
        if (status != 0x1):
            if status > 127:
                txt = 'Commit firmware status: Busy'
            else:
                status_txt = self.failed_status_dict.get(status & 0x3f, "Unknown")
                txt = 'Commit firmware status: Fail- ' + status_txt
        else:
            txt = 'Commit firmware status: Success'
        logger.info(txt)
        return status
