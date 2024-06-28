"""
    y_cable_credo.py

    Implementation of Credo Y-Cable
"""

import math
import time
import struct
import threading
from contextlib import contextmanager

from ctypes import c_int8
from sonic_y_cable.y_cable_base import YCableBase

try:
    import sonic_platform.platform
except ImportError as e:
    pass

class RLocker():
    ACQUIRE_LOCK_TIMEOUT = 15

    def __init__(self):
        self.rlock = threading.RLock()

    @contextmanager
    def acquire_timeout(self, timeout):
        result = self.rlock.acquire(timeout=timeout)
        yield result
        if result:
            self.rlock.release()

class YCable(YCableBase):
    # definitions of the offset with width accommodated for values
    # of MUX register specs of upper page 0x04 starting at 640
    # info eeprom for Y Cable
    OFFSET_IDENTIFIER_LOWER_PAGE     = 0
    OFFSET_INTERNAL_TEMPERATURE      = 22
    OFFSET_INTERNAL_VOLTAGE          = 26
    OFFSET_IDENTIFIER_UPPER_PAGE     = 128
    OFFSET_VENDOR_NAME               = 148
    OFFSET_PART_NUMBER               = 168
    OFFSET_SERIAL_NUMBER             = 196
    OFFSET_DETERMINE_CABLE_READ_SIDE = 640
    OFFSET_CHECK_LINK_ACTIVE         = 641
    OFFSET_SWITCH_MUX_DIRECTION      = 642
    OFFSET_MUX_DIRECTION             = 644
    OFFSET_ACTIVE_TOR_INDICATOR      = 645
    OFFSET_API_VERSION               = 650
    OFFSET_ENABLE_AUTO_SWITCH        = 651
    OFFSET_AUTO_SWITCH_HYSTERESIS    = 652
    OFFSET_MANUAL_SWITCH_COUNT_TOR_A = 653
    OFFSET_AUTO_SWITCH_COUNT         = 657
    OFFSET_NIC_CURSOR_VALUES         = 661
    OFFSET_TOR1_CURSOR_VALUES        = 681
    OFFSET_TOR2_CURSOR_VALUES        = 701
    OFFSET_NIC_MODE_CONFIGURATION    = 721
    OFFSET_NIC_TEMPERATURE           = 727
    OFFSET_NIC_VOLTAGE               = 729
    OFFSET_NIC_SIGNAL_DETECTION      = 731
    OFFSET_MANUAL_SWITCH_COUNT_TOR_B = 737
    OFFSET_EXTEND_SWITCH_COUNT_TYPE  = 741
    OFFSET_EXTEND_SWITCH_COUNT       = 742
    OFFSET_CLEAR_SWITCH_COUNT        = 746
    OFFSET_OPERATION_TIME            = 747
    OFFSET_RESET_CAUSE               = 751    
    OFFSET_CONFIGURE_PRBS_TYPE       = 768
    OFFSET_ENABLE_PRBS               = 769
    OFFSET_INITIATE_BER_MEASUREMENT  = 770
    OFFSET_LANE_1_BER_RESULT         = 771
    OFFSET_INITIATE_EYE_MEASUREMENT  = 784
    OFFSET_LANE_1_EYE_RESULT         = 785
    OFFSET_ENABLE_LOOPBACK           = 793
    OFFSET_TARGET                    = 794
    OFFSET_SYNC_DEBUG_MODE           = 795


    # definition of VSC command byte
    VSC_BYTE_OPCODE     = 128
    VSC_BYTE_STATUS     = 129
    VSC_BYTE_ADDR0      = 130
    VSC_BYTE_ADDR1      = 131
    VSC_BYTE_ADDR2      = 132
    VSC_BYTE_ADDR3      = 133
    VSC_BYTE_DATA0      = 134
    VSC_BYTE_DATA1      = 135
    VSC_BYTE_DATA2      = 136
    VSC_BYTE_DATA3      = 137
    VSC_BYTE_CHKSUM_LSB = 138
    VSC_BYTE_CHKSUM_MSB = 139
    VSC_BYTE_OPTION     = 140

    # firmware upgrade command options
    FWUPD_OPTION_GET_INFO            = 0x01
    FWUPD_OPTION_START               = 0x02
    FWUPD_OPTION_LOCAL_XFER          = 0x03
    FWUPD_OPTION_LOCAL_XFER_COMPLETE = 0x04
    FWUPD_OPTION_UART_XFER           = 0x05
    FWUPD_OPTION_UART_XFER_STATUS    = 0x06
    FWUPD_OPTION_RUN                 = 0x07
    FWUPD_OPTION_COMMIT              = 0x08
    FWUPD_OPTION_SYNC                = 0x09
    FWUPD_OPTION_SYNC_STATUS         = 0x0A
    FWUPD_OPTION_VERIFY_CRC          = 0x0C

    # upper page 0xFA VSC command attribute length
    VSC_CMD_ATTRIBUTE_LENGTH = 141
    VSC_BUFF_SIZE = 512
    VSC_BLOCK_WRITE_LENGTH = 32

    FIRMWARE_INFO_PAYLOAD_SIZE = 48
    EVENTLOG_PAYLOAD_SIZE = 18

    MAX_NUM_LANES = 4

    # definition of MIS memorymap page
    MIS_PAGE_VSC = 0xFA
    MIS_PAGE_FC  = 0xFC

    # eventlog command option
    EVENTLOG_OPTION_DUMP  = 0x01
    EVENTLOG_OPTION_CLEAR = 0x02

    # VSC opcode
    VSC_OPCODE_QUEUE_INFO      = 0x18
    VSC_OPCODE_UART_STAT       = 0x1C
    VSC_OPCODE_SERDES_INFO     = 0x1D
    VSC_OPCODE_DSP_LOADFW_STAT = 0x1F
    VSC_OPCODE_MEM_READ        = 0x40
    VSC_OPCODE_FWUPD           = 0x80
    VSC_OPCODE_EVENTLOG        = 0x81
    VSC_OPCODE_TCM_READ        = 0x82
    VSC_OPCODE_TCM_WRITE       = 0x83
    VSC_OPCODE_FW_CMD          = 0x84
    VSC_OPCODE_FW_CMD_EXT      = 0x85
    VSC_OPCODE_REG_READ        = 0x86
    VSC_OPCODE_REG_WRITE       = 0x87

    BER_TIMEOUT_SECS = 1
    EYE_TIMEOUT_SECS = 1
    GET_DEBUG_MODE_TIMEOUT_SECS = 1
    EXTEND_SWITCH_CNT_TIMEOUT_SECS = 1
    FWUPD_UART_XFER_TIMEOUT_SECS = 120

    # error code of EEPROM
    EEPROM_READ_DATA_INVALID = -1
    EEPROM_ERROR = -1
    EEPROM_TIMEOUT_ERROR = -1
    EEPROM_GENERIC_ERROR = -1

    # side bitamp
    SIDE_BMP_NIC   = 1
    SIDE_BMP_TOR_A = 2
    SIDE_BMP_TOR_B = 4
    SIDE_BMP_ALL   = 7

    CABLE_HEALTHY   = True
    CABLE_UNHEALTHY = False

    # MCU error code
    MCU_EC_NO_ERROR                         = 0
    MCU_EC_GET_FW_INFO_ERROR                = 11
    MCU_EC_UART_TX_BUSY                     = 13
    MCU_EC_FWUPD_ABORT                      = 14
    MCU_EC_FWUPD_HEADER_CRC_ERROR           = 15
    MCU_EC_FWUPD_META_CRC_ERROR             = 16
    MCU_EC_FWUPD_MCU_CRC_ERROR              = 17
    MCU_EC_FWUPD_DSP_CRC_ERROR              = 18
    MCU_EC_FWUPD_SCRIPT_CRC_ERROR           = 19
    MCU_EC_FWUPD_COMPLETE_ERROR             = 20
    MCU_EC_FWUPD_COMMIT_ERROR               = 21
    MCU_EC_INVALID_EVENT_LOG                = 22
    MCU_EC_FWUPD_UART_TIMEOUT               = 26
    MCU_EC_FWUPD_INVALID_SEQUENCE           = 27
    MCU_EC_FWUPD_SYNC_ERROR                 = 28
    MCU_EC_FWUPD_ABORT_FROM_THER_OTHER_SIDE = 30
    MCU_EC_FWUPD_IMAGE_SIZE_ERROR           = 31
    MCU_EC_WAIT_VSC_STATUS_TIMEOUT          = 254
    MCU_EC_UNDEFINED_ERROR                  = 255

    MCU_ERROR_CODE_STRING = {
        MCU_EC_NO_ERROR                        : 'No Error',
        MCU_EC_GET_FW_INFO_ERROR               : 'Get Firmware Info Error',
        MCU_EC_UART_TX_BUSY                    : 'UART TX Busy',
        MCU_EC_FWUPD_ABORT                     : 'Firmware Update Abort',
        MCU_EC_FWUPD_HEADER_CRC_ERROR          : 'Firmware Update Header CRC Error',
        MCU_EC_FWUPD_META_CRC_ERROR            : 'Firmware Update Meta CRC Error',
        MCU_EC_FWUPD_MCU_CRC_ERROR             : 'Firmware Update MCU CRC Error',
        MCU_EC_FWUPD_DSP_CRC_ERROR             : 'Firmware Update DSP CRC Error',
        MCU_EC_FWUPD_SCRIPT_CRC_ERROR          : 'Firmware Update Script CRC Error',
        MCU_EC_FWUPD_COMPLETE_ERROR            : 'Firmware Update Local Transfer Error',
        MCU_EC_FWUPD_COMMIT_ERROR              : 'Firmware Update Commit Error',
        MCU_EC_INVALID_EVENT_LOG               : 'Invalid Event Log',
        MCU_EC_FWUPD_UART_TIMEOUT              : 'Firmware Update UART Timeout',
        MCU_EC_FWUPD_INVALID_SEQUENCE          : 'Invalid Firmware Update Sequence',
        MCU_EC_FWUPD_SYNC_ERROR                : 'Firmware Synchronization Error',
        MCU_EC_FWUPD_ABORT_FROM_THER_OTHER_SIDE: 'Firmware Update Abort from the Other Side',
        MCU_EC_FWUPD_IMAGE_SIZE_ERROR          : 'Firmware Update Image Size Error',
        MCU_EC_WAIT_VSC_STATUS_TIMEOUT         : 'Wait VSC Status Timeout',
        MCU_EC_UNDEFINED_ERROR                 : 'Undefined Error',
    }

    def __init__(self, port, main_logger):
        """
        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
        """
        YCableBase.__init__(self, port, main_logger)

        self.platform_chassis = None
        self.rlock = RLocker()

        try:
            self.platform_chassis = sonic_platform.platform.Platform().get_chassis()
            self.log_info("chassis loaded {}".format(self.platform_chassis))
        except Exception as e:
            self.log_warning("Failed to load chassis due to {}".format(repr(e)))

    def read_mmap(self, page, byte, len=1):
        """
        This API converts memory map page and offset to linear address, then returns eeprom values
        by calling read_eeprom()

        Args:
             page:
                 an Integer, page number of memorymap

             byte:
                 an Integer, byte address of the page

             len:
                 an Integer, length of the reading

        Returns:
            an Integer or bytearray, returns the value of the specified eeprom address, returns 0xFF if it did not succeed
        """
        if byte < 128:
            linear_addr = byte
        else:
            linear_addr = page * 128 + byte

        ret = self.platform_chassis.get_sfp(self.port).read_eeprom(linear_addr, len)

        if ret is None:
            self.log_error('Read Nack!  page:%2X byte:%2X' % (page, byte))
            return 0xFF
        else:
            if len == 1:
                try:
                    return ret[0]
                except Exception as e:
                    self.log_error('Unknown read_mmap error')
                    return 0xFF
            else:
                return ret

    def write_mmap(self, page, byte, value, len=1):
        """
        This API converts memory map page and offset to linear address for calling write_eeprom()

        Args:
             page:
                 an Integer, page number of memorymap

             byte:
                 an Integer, byte address of the page

             value:
                 an Integer or bytearray, value to be written to the address

             len:
                 an Integer, length to be written

        Returns:
            an Boolean, true if succeeded and false if it did not succeed.
        """

        #print ('write page:%02X byte :%02X len:%d type:%s' % (page, byte, len, type(value)))

        if byte < 128:
            linear_addr = byte
        else:
            linear_addr = page * 128 + byte

        if len == 1:
            ba = bytearray([value])
        else:
            ba = value

        ret = self.platform_chassis.get_sfp(self.port).write_eeprom(linear_addr, len, ba)

        if (ret == False):
            self.log_error('Write Failed!  page:%2X byte:%2X value:%2X' % (page, byte, value))

        return ret

    def send_vsc(self, vsc_req_form, timeout=1200):
        """
        This API sends Credo vendor specific command to the MCU

        Args:
             vsc_req_form:
                 a bytearray, command request form follow by vsc command structure

             timeout:
                 an Integer, unit is 5ms, default value is 1200 (6 seconds).

        Returns:
            an Integer, status code of vsc command, find the 'MCU_ERROR_CODE_STRING' for the interpretation.
        """

        if self.platform_chassis is not None:
            for idx in range(129, YCable.VSC_CMD_ATTRIBUTE_LENGTH):
                if vsc_req_form[idx] != None:
                    self.write_mmap(YCable.MIS_PAGE_VSC, idx, vsc_req_form[idx])
            self.write_mmap(YCable.MIS_PAGE_VSC, YCable.VSC_BYTE_OPCODE, vsc_req_form[YCable.VSC_BYTE_OPCODE])

            while True:
                done = self.read_mmap(YCable.MIS_PAGE_VSC, YCable.VSC_BYTE_OPCODE)
                if done == 0:
                    break

                time.sleep(0.005)
                timeout -= 1

                if timeout == 0:
                    self.log_error("wait vsc status value timeout")
                    return YCable.MCU_EC_WAIT_VSC_STATUS_TIMEOUT

            status = self.read_mmap(YCable.MIS_PAGE_VSC, YCable.VSC_BYTE_STATUS)
        else:
            self.log_error("platform_chassis is not loaded, failed to send vsc cmd")
            return YCable.MCU_EC_UNDEFINED_ERROR

        return status

    def fw_cmd(self, cmd, detail1):
        """
        This API sends the firmware command to the serdes chip via VSC cmd

        Args:
             cmd:
                 an Integer, command code of the firmware command

             detail1:
                 an Integer, extra input parameter 1

        Returns:
            a Bytearray, a list of response code and return value
        """
        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FW_CMD
        vsc_req_form[YCable.VSC_BYTE_OPTION] = 0
        vsc_req_form[130]  = (cmd     >> 0) & 0xFF
        vsc_req_form[131]  = (cmd     >> 8) & 0xFF
        vsc_req_form[132]  = (detail1 >> 0) & 0xFF
        vsc_req_form[133]  = (detail1 >> 8) & 0xFF
        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error('fw cmd[%04X] detail1[%04X] error[%04X]' % (cmd, detail1, status))

        response = (self.read_mmap(YCable.MIS_PAGE_VSC, 131) << 8) | self.read_mmap(YCable.MIS_PAGE_VSC, 130)
        param1   = (self.read_mmap(YCable.MIS_PAGE_VSC, 137) << 8) | self.read_mmap(YCable.MIS_PAGE_VSC, 136)

        return [response, param1]

    def fw_cmd_ext(self, cmd, detail1, detail2):
        """
        This API sends the extended firmware command to the serdes chip via VSC cmd

        Args:
             cmd:
                 an Integer, command code of the firmware command

             detail1:
                 an Integer, extra input parameter 1

             detail2:
                 an Integer, extra input parameter 2
        Returns:
            a Bytearray, a list of response code, returned value1 and value2
        """
        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FW_CMD_EXT
        vsc_req_form[YCable.VSC_BYTE_OPTION] = 0
        vsc_req_form[130]  = (cmd     >> 0) & 0xFF
        vsc_req_form[131]  = (cmd     >> 8) & 0xFF
        vsc_req_form[132]  = (detail1 >> 0) & 0xFF
        vsc_req_form[133]  = (detail1 >> 8) & 0xFF
        vsc_req_form[134]  = (detail2 >> 0) & 0xFF
        vsc_req_form[135]  = (detail2 >> 8) & 0xFF
        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error('fw cmd ext[%04X] detail1[%04X] detail2[%04X] error[%04X]' % (cmd, detail1, detail2, status))

        response = (self.read_mmap(YCable.MIS_PAGE_VSC, 131) << 8) | self.read_mmap(YCable.MIS_PAGE_VSC, 130)
        param1   = (self.read_mmap(YCable.MIS_PAGE_VSC, 137) << 8) | self.read_mmap(YCable.MIS_PAGE_VSC, 136)
        param2   = (self.read_mmap(YCable.MIS_PAGE_VSC, 139) << 8) | self.read_mmap(YCable.MIS_PAGE_VSC, 138)

        return [response, param1, param2]

    def tcm_read(self, addr):
        """
        This API sends the tcm read command to the serdes chip via VSC cmd

        Args:
             addr:
                 an Integer, address of tcm space
        Returns:
            an Integer, return data of tcm address
        """

        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_TCM_READ
        vsc_req_form[130]  = (addr >>  0) & 0xFF
        vsc_req_form[131]  = (addr >>  8) & 0xFF
        vsc_req_form[132]  = (addr >> 16) & 0xFF
        vsc_req_form[133]  = (addr >> 24) & 0xFF
        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error('tcm read addr[%04X]  error[%04X]' % (addr, status))
            return -1

        data = (self.read_mmap(YCable.MIS_PAGE_VSC, 134) | (self.read_mmap(YCable.MIS_PAGE_VSC, 135) << 8) |
               (self.read_mmap(YCable.MIS_PAGE_VSC, 136) << 16) | (self.read_mmap(YCable.MIS_PAGE_VSC, 137) << 24))

        return data

    def tcm_write(self, addr, data):
        """
        This API sends the tcm write command to the serdes chip via VSC cmd

        Args:
             addr:
                 an Integer, address of tcm space

             data:
                 an Integer, value to be written to the address

        Returns:
            a boolean, True if the tcm write succeeded and False if it did not succeed.
        """

        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_TCM_WRITE
        vsc_req_form[130]  = (addr >>  0) & 0xFF
        vsc_req_form[131]  = (addr >>  8) & 0xFF
        vsc_req_form[132]  = (addr >> 16) & 0xFF
        vsc_req_form[133]  = (addr >> 24) & 0xFF
        vsc_req_form[134]  = (data >>  0) & 0xFF
        vsc_req_form[135]  = (data >>  8) & 0xFF
        vsc_req_form[136]  = (data >> 16) & 0xFF
        vsc_req_form[137]  = (data >> 24) & 0xFF

        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error('tcm read addr[%04X] data[%04X] error[%04X]' % (addr, data, status))
            return False

        return True

    def tcm_read_atomic(self, addr):
        """
        This API sends the tcm read command to the serdes chip via VSC cmd

        Args:
             addr:
                 an Integer, address of tcm space
        Returns:
            an Integer, return data of tcm address
        """

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_TCM_READ
                    vsc_req_form[130]  = (addr >>  0) & 0xFF
                    vsc_req_form[131]  = (addr >>  8) & 0xFF
                    vsc_req_form[132]  = (addr >> 16) & 0xFF
                    vsc_req_form[133]  = (addr >> 24) & 0xFF
                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('tcm read addr[%04X]  error[%04X]' % (addr, status))
                        return -1

                    data = (self.read_mmap(YCable.MIS_PAGE_VSC, 134) | (self.read_mmap(YCable.MIS_PAGE_VSC, 135) << 8) |
                        (self.read_mmap(YCable.MIS_PAGE_VSC, 136) << 16) | (self.read_mmap(YCable.MIS_PAGE_VSC, 137) << 24))
                else:
                    self.log_error('acquire lock timeout, failed to read serdes tcm register')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to read serdes tcm register")
            return YCable.EEPROM_ERROR

        return data

    def tcm_write_atomic(self, addr, data):
        """
        This API sends the tcm write command to the serdes chip via VSC cmd

        Args:
             addr:
                 an Integer, address of tcm space

             data:
                 an Integer, value to be written to the address

        Returns:
            a boolean, True if the tcm write succeeded and False if it did not succeed.
        """

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_TCM_WRITE
                    vsc_req_form[130]  = (addr >>  0) & 0xFF
                    vsc_req_form[131]  = (addr >>  8) & 0xFF
                    vsc_req_form[132]  = (addr >> 16) & 0xFF
                    vsc_req_form[133]  = (addr >> 24) & 0xFF
                    vsc_req_form[134]  = (data >>  0) & 0xFF
                    vsc_req_form[135]  = (data >>  8) & 0xFF
                    vsc_req_form[136]  = (data >> 16) & 0xFF
                    vsc_req_form[137]  = (data >> 24) & 0xFF

                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('tcm read addr[%04X] data[%04X] error[%04X]' % (addr, data, status))
                        return False
                else:
                    self.log_error('acquire lock timeout, failed to write serdes tcm register')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to write serdes tcm register")
            return YCable.EEPROM_ERROR

        return True

    def reg_read(self, addr):
        """
        This API reads the serdes register via vsc

        Args:
             addr:
                 an Integer, address of the serdes register
        Returns:
            an Integer, return data of the register
        """

        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_REG_READ
        vsc_req_form[130]  = (addr >>  0) & 0xFF
        vsc_req_form[131]  = (addr >>  8) & 0xFF
        vsc_req_form[132]  = (addr >> 16) & 0xFF
        vsc_req_form[133]  = (addr >> 24) & 0xFF
        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error('reg read addr[%04X]  error[%04X]' % (addr, status))
            return -1

        return self.read_mmap(YCable.MIS_PAGE_VSC, 134) | (self.read_mmap(YCable.MIS_PAGE_VSC, 135) << 8)

    def reg_write(self, addr, data):
        """
        This API writes the serdes register via vsc

        Args:
             addr:
                 an Integer, address of the serdes register

             data:
                 an Integer, value to be written to the register address

        Returns:
            a boolean, True if the register write succeeded and False if it did not succeed.
        """

        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_REG_WRITE
        vsc_req_form[130]  = (addr >>  0) & 0xFF
        vsc_req_form[131]  = (addr >>  8) & 0xFF
        vsc_req_form[134]  = (data >>  0) & 0xFF
        vsc_req_form[135]  = (data >>  8) & 0xFF

        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error('reg write addr[%04X] data[%04X] error[%04X]' % (addr, data, status))
            return False

        return True

    def reg_read_atomic(self, addr):
        """
        This API reads the serdes register in atomic method

        Args:
             addr:
                 an Integer, address of the serdes register
        Returns:
            an Integer, return data of the register
        """

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_REG_READ
                    vsc_req_form[130]  = (addr >>  0) & 0xFF
                    vsc_req_form[131]  = (addr >>  8) & 0xFF
                    vsc_req_form[132]  = (addr >> 16) & 0xFF
                    vsc_req_form[133]  = (addr >> 24) & 0xFF
                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('reg read addr[%04X]  error[%04X]' % (addr, status))
                        return YCable.EEPROM_ERROR

                    return self.read_mmap(YCable.MIS_PAGE_VSC, 134) | (self.read_mmap(YCable.MIS_PAGE_VSC, 135) << 8)
                else:
                    self.log_error('acquire lock timeout, failed to read serdes register')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to read serdes register")
            return YCable.EEPROM_ERROR
        
    def reg_write_atomic(self, addr, data):
        """
        This API writes the serdes register in atomic method

        Args:
             addr:
                 an Integer, address of the serdes register

             data:
                 an Integer, value to be written to the register address

        Returns:
            an Integer, 0 if the register write succeeded.
        """

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_REG_WRITE
                    vsc_req_form[130]  = (addr >>  0) & 0xFF
                    vsc_req_form[131]  = (addr >>  8) & 0xFF
                    vsc_req_form[134]  = (data >>  0) & 0xFF
                    vsc_req_form[135]  = (data >>  8) & 0xFF

                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('reg write addr[%04X] data[%04X] error[%04X]' % (addr, data, status))
                        return YCable.EEPROM_ERROR
                else:
                    self.log_error('acquire lock timeout, failed to write serdes register')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to write serdes register")
            return YCable.EEPROM_ERROR

        return 0        

    def toggle_mux_to_tor_a(self):
        """
        This API does a hard switch toggle of the Y cable's MUX regardless of link state to
        TOR A on the port this is called for. This means if the Y cable is actively sending traffic,
        the "get_active_linked_tor_side" API will now return Tor A.
        It also implies that if the link is actively sending traffic on this port,
        Y cable MUX will start forwarding packets from TOR A to NIC, and drop packets from TOR B to NIC
        regardless of previous forwarding state.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a Boolean, True if the toggle succeeded and False if it did not succeed.
        """

        buffer = bytearray([2])
        curr_offset = YCable.OFFSET_SWITCH_MUX_DIRECTION

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
        else:
            self.log_error("platform_chassis is not loaded, failed to toggle mux to TOR A")
            return YCable.EEPROM_ERROR

        return result

    def toggle_mux_to_tor_b(self):
        """
        This API does a hard switch toggle of the Y cable's MUX regardless of link state to
        TOR B. This means if the Y cable is actively sending traffic, the "get_active_linked_tor_side"
        API will now return Tor B. It also implies that if the link is actively sending traffic on this port,
        Y cable. MUX will start forwarding packets from TOR B to NIC, and drop packets from TOR A to NIC
        regardless of previous forwarding state.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a Boolean, True if the toggle succeeded and False if it did not succeed.
        """
        buffer = bytearray([3])
        curr_offset = YCable.OFFSET_SWITCH_MUX_DIRECTION

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
        else:
            self.log_error("platform_chassis is not loaded, failed to toggle mux to TOR B")
            return YCable.EEPROM_ERROR

        return result

    def get_read_side(self):
        """
        This API checks which side of the Y cable the reads are actually getting performed
        from, either TOR A or TOR B or NIC and returns the value.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            One of the following predefined constants:
                TARGET_TOR_A, if reading the Y cable from TOR A side.
                TARGET_TOR_B, if reading the Y cable from TOR B side.
                TARGET_NIC, if reading the Y cable from NIC side.
                TARGET_UNKNOWN, if reading the Y cable API fails.
        """

        curr_offset = YCable.OFFSET_DETERMINE_CABLE_READ_SIDE

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log_error("platform_chassis is not loaded, failed to check read side")
            return YCable.EEPROM_ERROR

        if result is not None:
            if isinstance(result, bytearray):
                if len(result) != 1:
                    self.log_error("Error: for checking mux_cable read side, eeprom read returned a size {} not equal to 1 for port {}".format(
                        len(result), self.port))
                    return YCableBase.TARGET_UNKNOWN
            else:
                self.log_error("Error: for checking mux_cable read_side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                    type(result), self.port))
                return YCableBase.TARGET_UNKNOWN
        else:
            self.log_error(
                "Error: for checking mux_cable read_side, eeprom read returned a None value for port {} which is not expected".format(self.port))
            return YCableBase.TARGET_UNKNOWN

        regval_read = struct.unpack(">B", result)

        if ((regval_read[0] >> 2) & 0x01):
            self.log_info("Reading from TOR A")
            return YCableBase.TARGET_TOR_A
        elif ((regval_read[0] >> 1) & 0x01):
            self.log_info("Reading from TOR B")
            return YCableBase.TARGET_TOR_B
        elif (regval_read[0] & 0x01):
            self.log_info("Reading from NIC side")
            return YCableBase.TARGET_NIC
        else:
            self.log_error("Error: Credo Y Cable unable to get the read side, Cable not plugged/Faulty Cable register value = {} ".format(result))

        return YCableBase.TARGET_UNKNOWN

    def get_mux_direction(self):
        """
        This API checks which side of the Y cable mux is currently point to
        and returns either TOR A or TOR B. Note that this API should return mux-direction
        regardless of whether the link is active and sending traffic or not.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            One of the following predefined constants:
                TARGET_TOR_A, if mux is pointing to TOR A side.
                TARGET_TOR_B, if mux is pointing to TOR B side.
                TARGET_UNKNOWN, if mux direction API fails.
        """

        curr_offset = YCable.OFFSET_MUX_DIRECTION

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log_error(
                "platform_chassis is not loaded, failed to get mux direction")
            return YCable.EEPROM_ERROR

        if result is not None:
            if isinstance(result, bytearray):
                if len(result) != 1:
                    self.log_error("Error: for checking mux_cable mux pointing side, eeprom read returned a size {} not equal to 1 for port {}".format(
                        len(result), self.port))
                    return YCableBase.TARGET_UNKNOWN
            else:
                self.log_error("Error: for checking mux_cable mux pointing side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                    type(result), self.port))
                return YCableBase.TARGET_UNKNOWN
        else:
            self.log_error(
                "Error: for checking mux_cable mux pointing side, eeprom read returned a None value from eeprom read for port {} which is not expected".format(self.port))
            return YCableBase.TARGET_UNKNOWN

        regval_read = struct.unpack(">B", result)

        if ((regval_read[0]) & 0x01):
            self.log_info("mux pointing to TOR A")
            return YCableBase.TARGET_TOR_A
        elif regval_read[0] == 0:
            self.log_info("mux pointing to TOR B")
            return YCableBase.TARGET_TOR_B

        self.log_error("Error: Credo Y Cable unable to check the status mux direction, cable powered off/Faulty Cable register value = {}".format(result))
        return YCableBase.TARGET_UNKNOWN

    def get_active_linked_tor_side(self):
        """
        This API checks which side of the Y cable is actively linked and sending traffic
        and returns either TOR A or TOR B.
        The port on which this API is called for can be referred using self.port.
        This is different from get_mux_direction in a sense it also implies the link on the side
        where mux is pointing to must be active and sending traffic, whereas get_mux_direction
        just tells where the mux is pointing to.

        Args:

        Returns:
            One of the following predefined constants:
                TARGET_TOR_A, if TOR A is actively linked and sending traffic.
                TARGET_TOR_B, if TOR B is actively linked and sending traffic.
                TARGET_UNKNOWN, if checking which side is linked and sending traffic API fails.
        """


        curr_offset = YCable.OFFSET_ACTIVE_TOR_INDICATOR

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log_error(
                "platform_chassis is not loaded, failed to check Active Linked and routing TOR side")
            return YCable.EEPROM_ERROR

        if result is not None:
            if isinstance(result, bytearray):
                if len(result) != 1:
                    self.log_error("Error: for checking mux_cable active linked side, eeprom read returned a size {} not equal to 1 for port {}".format(
                        len(result), self.port))
                    return YCableBase.TARGET_UNKNOWN
            else:
                self.log_error("Error: for checking mux_cable active linked side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                    type(result), self.port))
                return YCableBase.TARGET_UNKNOWN
        else:
            self.log_error(
                "Error: for checking mux_cable active linked side, eeprom read returned a None value from eeprom read for port {} which is not expected".format(self.port))
            return YCableBase.TARGET_UNKNOWN

        regval_read = struct.unpack(">B", result)

        if ((regval_read[0] >> 1) & 0x01):
            self.log_info("TOR B active linked and actively routing")
            return YCableBase.TARGET_TOR_B
        elif ((regval_read[0]) & 0x01):
            self.log_info("TOR A standby linked and actively routing")
            return YCableBase.TARGET_TOR_A
        elif regval_read[0] == 0:
            self.log_info("Nothing linked for routing")
            return YCableBase.TARGET_NIC

        self.log_error("Error: Credo Y Cable unable to get active linked ToR side Cable powered off/Faulty Cable register value = {} ".format(result))
        return YCableBase.TARGET_UNKNOWN

    def is_link_active(self, target):
        """
        This API checks if NIC, TOR_A and TOR_B  of the Y cable's link is active.
        The target specifies which link is supposed to be checked
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the actual target to check the link on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB

        Returns:
            a boolean, True if the link is active
                     , False if the link is not active
        """


        curr_offset = YCable.OFFSET_CHECK_LINK_ACTIVE

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log_error(
                "platform_chassis is not loaded, failed to check if link is Active on target side")
            return YCable.EEPROM_ERROR

        if result is not None:
            if isinstance(result, bytearray):
                if len(result) != 1:
                    self.log_error("Error: for checking mux_cable link is active on target side, eeprom read returned a size {} not equal to 1 for port {}".format(
                        len(result), self.port))
                    return YCableBase.TARGET_UNKNOWN
            else:
                self.log_error("Error: for checking mux_cable link is active on target side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                    type(result), self.port))
                return YCableBase.TARGET_UNKNOWN
        else:
            self.log_error(
                "Error: for checking mux_cable link is active on target side, eeprom read returned a None value from eeprom read for port {} which is not expected".format(self.port))
            return YCable.EEPROM_ERROR

        regval_read = struct.unpack(">B", result)

        if target == YCableBase.TARGET_NIC:
            if (regval_read[0] & 0x01):
                self.log_info("NIC link is up")
                return True
            else:
                return False
        elif target == YCableBase.TARGET_TOR_A:
            if ((regval_read[0] >> 2) & 0x01):
                self.log_info("TOR A link is up")
                return True
            else:
                return False
        elif target == YCableBase.TARGET_TOR_B:
            if ((regval_read[0] >> 1) & 0x01):
                self.log_info("TOR B link is up")
                return True
            else:
                return False
        else:
            return YCableBase.TARGET_UNKNOWN

    def get_eye_heights(self, target):
        """
        This API returns the EYE height value for a specfic port.
        The target could be local side, TOR_A, TOR_B, NIC etc.
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                 One of the following predefined constants, the target on which to get the eye:
                     EYE_PRBS_LOOPBACK_TARGET_LOCAL -> local side,
                     EYE_PRBS_LOOPBACK_TARGET_TOR_A -> TOR A
                     EYE_PRBS_LOOPBACK_TARGET_TOR_B -> TOR B
                     EYE_PRBS_LOOPBACK_TARGET_NIC -> NIC
        Returns:
            a list, with EYE values of lane 0 lane 1 lane 2 lane 3 with corresponding index
        """


        eye_result = []

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    buffer = bytearray([target])
                    curr_offset = YCable.OFFSET_TARGET
                    result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
                    if result is False:
                        return result

                    buffer = bytearray([0])
                    curr_offset = YCable.OFFSET_INITIATE_EYE_MEASUREMENT
                    result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
                    if result is False:
                        return result

                    time_start = time.time()
                    while(True):
                        done = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                        time_now = time.time()
                        time_diff = time_now - time_start
                        if done[0] == 1:
                            break
                        elif time_diff >= YCable.EYE_TIMEOUT_SECS:
                            return YCable.EEPROM_TIMEOUT_ERROR

                    idx = 0
                    for lane in range(YCable.MAX_NUM_LANES):
                        curr_offset = YCable.OFFSET_LANE_1_EYE_RESULT
                        msb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + idx, 1)
                        lsb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + idx + 1, 1)

                        lane_result = (msb_result[0] << 8 | lsb_result[0])
                        eye_result.append(lane_result)
                        idx += 2
                else:
                    self.log_error('acquire lock timeout, failed to get eye height')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get eye height")
            return YCable.EEPROM_ERROR

        return eye_result

    def get_vendor(self):
        """
        This API returns the vendor name of the Y cable for a specfic port.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a string, with vendor name
        """

        curr_offset = YCable.OFFSET_VENDOR_NAME

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 16)
        else:
            self.log_error("platform_chassis is not loaded, failed to get Vendor name")
            return YCable.EEPROM_ERROR

        vendor_name = str(result.decode())

        return vendor_name

    def get_part_number(self):
        """
        This API returns the part number of the Y cable for a specfic port.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a string, with part number
        """
        curr_offset = YCable.OFFSET_PART_NUMBER

        if self.platform_chassis is not None:
            part_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 16)
        else:
            self.log_error("platform_chassis is not loaded, failed to get part number")
            return YCable.EEPROM_ERROR

        part_number = str(part_result.decode())

        return part_number

    def get_serial_number(self):
        """
        This API returns the serial number of the Y cable for a specfic port.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a string, with serial number
        """
        curr_offset = YCable.OFFSET_SERIAL_NUMBER

        if self.platform_chassis is not None:
            part_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 16)
        else:
            self.log_error("platform_chassis is not loaded, failed to get serial number")
            return YCable.EEPROM_ERROR

        part_number = str(part_result.decode())

        return part_number

    def get_switch_count_total(self, switch_count_type, clear_on_read=False):
        """
        This API returns the total switch count to change the Active TOR which has
        been done manually/automatic by the user.
        The port on which this API is called for can be referred using self.port.

        Args:
            switch_count_type:
                One of the following predefined constants, for getting the count type:
                    SWITCH_COUNT_MANUAL -> manual switch count
                    SWITCH_COUNT_AUTO -> automatic switch count
            clear_on_read:
                a boolean, True if the count has to be reset after read to zero
                         , False if the count is not to be reset after read
            Returns:
                an integer, the number of times the Y-cable has been switched
        """

        count = 0

        if self.platform_chassis is not None:
            if switch_count_type == YCableBase.SWITCH_COUNT_MANUAL:
                count = self.get_switch_count_tor_a(clear_on_read) + self.get_switch_count_tor_b(clear_on_read)
            elif switch_count_type == YCableBase.SWITCH_COUNT_AUTO:
                curr_offset = YCable.OFFSET_AUTO_SWITCH_COUNT
                msb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                msb_result_1 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 1, 1)
                msb_result_2 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 2, 1)
                lsb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 3, 1)
                count = (msb_result[0] << 24 | msb_result_1[0] << 16 | msb_result_2[0] << 8 | lsb_result[0])
            else:
                self.log_error("not a valid switch_count_type, failed to get switch count")
                return YCable.EEPROM_ERROR

            if clear_on_read:
                if switch_count_type == YCableBase.SWITCH_COUNT_AUTO:
                    curr_offset = YCable.OFFSET_AUTO_SWITCH_COUNT
                    buffer = bytearray([6])
                    result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
                    if result is False:
                        return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get switch count")
            return YCable.EEPROM_ERROR

        return count

    def get_switch_count_tor_a(self, clear_on_read=False):
        """
        This API returns the switch count to change the Active TOR which has
        been done manually by the user initiated from ToR A
        This is essentially all the successful switches initiated from ToR A. Toggles which were
        initiated to toggle from ToR A and did not succeed do not count.
        The port on which this API is called for can be referred using self.port.

        Args:
            clear_on_read:
                a boolean, True if the count has to be reset after read to zero
                         , False if the count is not to be reset after read

            Returns:
                an integer, the number of times the Y-cable has been switched from ToR A
        """

        curr_offset = YCable.OFFSET_MANUAL_SWITCH_COUNT_TOR_A
        count = 0

        if self.platform_chassis is not None:
            msb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            msb_result_1 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 1, 1)
            msb_result_2 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 2, 1)
            lsb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset+3, 1)
            count = (msb_result[0] << 24 | msb_result_1[0] << 16 | msb_result_2[0] << 8 | lsb_result[0])

            if clear_on_read:
                buffer = bytearray([4])
                curr_offset = YCable.OFFSET_CLEAR_SWITCH_COUNT
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
                if result is False:
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get manual switch count")
            return YCable.EEPROM_ERROR

        return count

    def get_switch_count_tor_b(self, clear_on_read=False):
        """
        This API returns the switch count to change the Active TOR which has
        been done manually by the user initiated from ToR B
        This is essentially all the successful switches initiated from ToR B. Toggles which were
        initiated to toggle from ToR B and did not succeed do not count.
        The port on which this API is called for can be referred using self.port.

        Args:
            clear_on_read:
                a boolean, True if the count has to be reset after read to zero
                         , False if the count is not to be reset after read

            Returns:
                an integer, the number of times the Y-cable has been switched from ToR B
        """

        curr_offset = YCable.OFFSET_MANUAL_SWITCH_COUNT_TOR_B
        count = 0

        if self.platform_chassis is not None:
            msb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            msb_result_1 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 1, 1)
            msb_result_2 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 2, 1)
            lsb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset+3, 1)
            count = (msb_result[0] << 24 | msb_result_1[0] << 16 | msb_result_2[0] << 8 | lsb_result[0])

            if clear_on_read:
                buffer = bytearray([5])
                curr_offset = YCable.OFFSET_CLEAR_SWITCH_COUNT
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
                if result is False:
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get manual switch count")
            return YCable.EEPROM_ERROR

        return count

    def get_switch_count_target(self, switch_count_type, target, clear_on_read=False):
        """
        This API returns the total number of times the Active TOR has
        been done manually/automaticlly toggled towards a target.
        For example, TARGET_TOR_A as target would imply
        how many times the mux has been toggled towards TOR A.
        The port on which this API is called for can be referred using self.port.

        Args:
            switch_count_type:
                One of the following predefined constants, for getting the count type:
                    SWITCH_COUNT_MANUAL -> manual switch count
                    SWITCH_COUNT_AUTO -> automatic switch count
            target:
                One of the following predefined constants, the actual target to check the link on:
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
            clear_on_read:
                a boolean, True if the count has to be reset after read to zero
                         , False if the count is not to be reset after read
            Returns:
                an integer, the number of times manually the Y-cable has been switched
        """

        curr_offset = YCable.OFFSET_EXTEND_SWITCH_COUNT_TYPE

        if switch_count_type == YCableBase.SWITCH_COUNT_MANUAL:
            if target == YCableBase.TARGET_TOR_A:
                buffer = bytearray([0])
            elif target == YCableBase.TARGET_TOR_B:
                buffer = bytearray([1])
            else:
                self.log_error("not a valid target")
                return YCable.EEPROM_ERROR
        elif switch_count_type == YCableBase.SWITCH_COUNT_AUTO:
            if target == YCableBase.TARGET_TOR_A:
                buffer = bytearray([2])
            elif target == YCableBase.TARGET_TOR_B:
                buffer = bytearray([3])
            else:
                self.log_error("not a valid target")
                return YCable.EEPROM_ERROR
        else:
            self.log_error("not a valid switch_count_type, failed to get switch count")
            return YCable.EEPROM_ERROR

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return YCable.EEPROM_ERROR
            time_start = time.time()
            while(True):
                done = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                time_now = time.time()
                time_diff = time_now - time_start
                if done[0] & 0x80:
                    break
                elif time_diff >= YCable.EXTEND_SWITCH_CNT_TIMEOUT_SECS:
                    return YCable.EEPROM_TIMEOUT_ERROR

            curr_offset = YCable.OFFSET_EXTEND_SWITCH_COUNT
            msb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 3, 1)
            msb_result_1 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 2, 1)
            msb_result_2 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 1, 1)
            lsb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            count = (msb_result[0] << 24 | msb_result_1[0] << 16 | msb_result_2[0] << 8 | lsb_result[0])

            if clear_on_read:
                curr_offset = YCable.OFFSET_CLEAR_SWITCH_COUNT
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
                if result is False:
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get switch count target")
            return YCable.EEPROM_ERROR

        return count

    def get_target_cursor_values(self, lane, target):
        """
        This API returns the cursor equalization parameters for a target(NIC, TOR_A, TOR_B).
        This includes pre one, pre two, main, post one, post two, post three cursor values
        If any of the value is not available please return None for that filter
        The port on which this API is called for can be referred using self.port.

        Args:
            lane:
                 an Integer, the lane on which to collect the cursor values
                             1 -> lane 1,
                             2 -> lane 2
                             3 -> lane 3
                             4 -> lane 4
            target:
                One of the following predefined constants, the actual target to get the cursor values on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
            a list, with  pre one, pre two, main, post one, post two, post three cursor values in the order
        """
        curr_offset = YCable.OFFSET_NIC_CURSOR_VALUES

        result = []

        if self.platform_chassis is not None:
            pre1 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5, 1)
            result.append(c_int8(pre1[0]).value)
            pre2 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5 + 1, 1)
            result.append(c_int8(pre2[0]).value)
            main = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5 + 2, 1)
            result.append(c_int8(main[0]).value)
            post1 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5 + 3, 1)
            result.append(c_int8(post1[0]).value)
            post2 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5 + 4, 1)
            result.append(c_int8(post2[0]).value)
        else:
            self.log_error("platform_chassis is not loaded, failed to get target cursor values")
            return YCable.EEPROM_ERROR

        return result

    def set_target_cursor_values(self, lane, cursor_values, target):
        """
        This API sets the cursor equalization parameters for a target(NIC, TOR_A, TOR_B).
        This includes pre one, pre two, main, post one, post two etc. cursor values
        The port on which this API is called for can be referred using self.port.

        Args:
            lane:
                 an Integer, the lane on which to collect the cursor values
                             1 -> lane 1,
                             2 -> lane 2
                             3 -> lane 3
                             4 -> lane 4
            cursor_values:
                a list, with  pre one, pre two, main, post one, post two cursor, post three etc. values in the order
            target:
                One of the following predefined constants, the actual target to get the cursor values on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
            a boolean, True if cursor values setting is successful
                     , False if cursor values setting is not successful
        """
        curr_offset = YCable.OFFSET_NIC_CURSOR_VALUES
        idx = 0
        if self.platform_chassis is not None:
            for data in cursor_values:
                data = data & 0xFF
                buffer = bytearray([data])
                self.platform_chassis.get_sfp(self.port).write_eeprom(
                    curr_offset + (target)*20 + (lane-1)*5 + idx, 1, buffer)
                idx += 1
        else:
            self.log_error("platform_chassis is not loaded, failed to get target cursor values")
            return YCable.EEPROM_ERROR

        return True

    def get_firmware_version(self, target):
        """
        This routine should return the active, inactive and next (committed)
        firmware running on the target. Each of the version values in this context
        could be a string with a major and minor number and a build value.
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the actual target to get the firmware version on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
            a Dictionary:
                 with version_active, version_inactive and version_next keys
                 and their corresponding values

        """
        if self.platform_chassis is not None:
            read_side = self.get_read_side()

            if read_side == YCable.EEPROM_ERROR:
                self.log_error('Fail to get read side in get_firmware_version()')
                return None
            
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                    vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_GET_INFO
                    status = self.send_vsc(vsc_req_form)

                    if status != YCable.MCU_EC_NO_ERROR:
                        ''' should at least return local side fw version if nic is offline'''
                        if status == YCable.MCU_EC_FWUPD_UART_TIMEOUT and (read_side == target):
                            pass
                        else:
                            self.log_error('Get firmware version error (error code:0x%04X)' % (status))
                            return None

                    data = bytearray(YCable.FIRMWARE_INFO_PAYLOAD_SIZE)
                    for byte_idx in range(0, YCable.FIRMWARE_INFO_PAYLOAD_SIZE):
                        curr_offset = 0xfc * 128 + 128 + byte_idx
                        read_out = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                        data[byte_idx] = read_out[0]
                else:
                    self.log_error('acquire lock timeout, failed to get firmware version')
                    return None
        else:
            self.log_error("platform_chassis is not loaded, failed to get firmware version")
            return None

        result = {}
        NUM_MCU_SIDE = 3

        base_addr = int(target * (YCable.FIRMWARE_INFO_PAYLOAD_SIZE / NUM_MCU_SIDE))
        rev_major_slot1 = struct.unpack_from('<B', data[(0 + base_addr):(1 + base_addr)])[0]
        rev_minor_slot1 = struct.unpack_from('<B', data[(2 + base_addr):(3 + base_addr)])[0]
        rev_build_lsb_slot1 = struct.unpack_from('<B', data[(4 + base_addr):(5 + base_addr)])[0]
        rev_build_msb_slot1 = struct.unpack_from('<B', data[(5 + base_addr):(6 + base_addr)])[0]
        rev_major_slot2 = struct.unpack_from('<B', data[(1 + base_addr):(2 + base_addr)])[0]
        rev_minor_slot2 = struct.unpack_from('<B', data[(3 + base_addr):(4 + base_addr)])[0]
        rev_build_lsb_slot2 = struct.unpack_from('<B', data[(6 + base_addr):(7 + base_addr)])[0]
        rev_build_msb_slot2 = struct.unpack_from('<B', data[(7 + base_addr):(8 + base_addr)])[0]
        slot_status = struct.unpack_from('<B', data[(8 + base_addr):(9 + base_addr)])[0]

        if (rev_major_slot1 == 0 and rev_minor_slot1 == 0 and rev_build_lsb_slot1 == 0 and rev_build_msb_slot1 == 0 and rev_major_slot2 == 0 and rev_minor_slot2 == 0 and rev_build_lsb_slot2 == 0 and rev_build_msb_slot2 == 0):
            return None
        else:
            build_slot1 = chr(rev_build_lsb_slot1) + chr(rev_build_msb_slot1)
            version_slot1 = str(rev_major_slot1) + "." + str(rev_minor_slot1)
            build_slot2 = chr(rev_build_lsb_slot2) + chr(rev_build_msb_slot2)
            version_slot2 = str(rev_major_slot2) + "." + str(rev_minor_slot2)

            result["build_slot1"] = build_slot1
            result["version_slot1"] = version_slot1
            result["build_slot2"] = build_slot2
            result["version_slot2"] = version_slot2
            result["run_slot1"] = True if slot_status & 0x01 else False
            result["run_slot2"] = True if slot_status & 0x10 else False
            result["commit_slot1"] = True if slot_status & 0x02 else False
            result["commit_slot2"] = True if slot_status & 0x20 else False
            result["empty_slot1"] = True if slot_status & 0x04 else False
            result["empty_slot2"] = True if slot_status & 0x40 else False

        version_build_slot1 = version_slot1 + build_slot1
        version_build_slot2 = version_slot2 + build_slot2

        result["version_active"] = version_build_slot1 if slot_status & 0x01 else version_build_slot2
        result["version_inactive"] = version_build_slot2 if slot_status & 0x01 else version_build_slot1
        result["version_next"] = version_build_slot1 if slot_status & 0x02 else version_build_slot2

        return result

    def download_firmware(self, fwfile):
        """
        This routine should download and store the firmware on all the
        components of the Y cable of the port for which this API is called..
        This should include any internal transfers, checksum validation etc.
        from TOR to TOR or TOR to NIC side of the firmware specified by the fwfile.
        This basically means that the firmware which is being downloaded should be
        available to be activated (start being utilized by the cable) once this API is
        successfully executed.
        Note that this API should ideally not require any rollback even if it fails
        as this should not interfere with the existing cable functionality because
        this has not been activated yet.
        The port on which this API is called for can be referred using self.port.

        Args:
            fwfile:
                 a string, a path to the file which contains the firmware image.
                 Note that the firmware file can be in the format of the vendor's
                 choosing (binary, archive, etc.). But note that it should be one file
                 which contains firmware for all components of the Y-cable
        Returns:
            One of the following predefined constants:
                FIRMWARE_DOWNLOAD_SUCCESS
                FIRMWARE_DOWNLOAD_FAILURE

                a predefined code stating whether the firmware download was successful
                or an error code as to what was the cause of firmware download failure
        """

        if self.platform_chassis is not None:
            try:
                inFile = open(fwfile, 'rb')
                fwImage = bytearray(inFile.read())
                inFile.close()
            except Exception:
                self.log_error('File Not Found Error: %s' % (fwfile))
                self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

            bin_pid = struct.unpack_from('>B', fwImage[5 : 6])[0]
            mcu_pid = self.read_mmap(0xFB, 187)

            if bin_pid != mcu_pid:
                self.log_error('Firmware binary ID Mismatched Bin[%d] MCU[%d]' % (bin_pid, mcu_pid))
                self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS

            '''
            Firmware update start
            '''
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                    vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_START
                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('Firmware binary start transfer error (error code:%04X)' % (status))
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                        return YCableBase.FIRMWARE_DOWNLOAD_FAILURE
                else:
                    self.log_error('acquire lock timeout, failed to start firmware update')
                    self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                    return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

            '''
            Transfer firmware image to local side MCU
            '''
            total_chunk = len(fwImage) // YCable.VSC_BUFF_SIZE
            chunk_idx = 0
            retry_count = 0
            while chunk_idx < total_chunk:
                with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                    if lock_status:
                        checksum = 0
                        fw_img_offset = chunk_idx * YCable.VSC_BUFF_SIZE
                        for byte_offset in range(YCable.VSC_BUFF_SIZE):
                            checksum += fwImage[fw_img_offset]
                            fw_img_offset += 1
                            if (((byte_offset + 1) % YCable.VSC_BLOCK_WRITE_LENGTH) == 0):
                                page = YCable.MIS_PAGE_FC + byte_offset // 128
                                byte = 128 + ((byte_offset + 1) - YCable.VSC_BLOCK_WRITE_LENGTH) % 128
                                self.write_mmap(page, byte, bytearray(
                                    fwImage[fw_img_offset - YCable.VSC_BLOCK_WRITE_LENGTH: fw_img_offset]), YCable.VSC_BLOCK_WRITE_LENGTH)

                        fw_img_offset = chunk_idx * YCable.VSC_BUFF_SIZE
                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_LOCAL_XFER
                        vsc_req_form[YCable.VSC_BYTE_ADDR0] = (fw_img_offset >> 0) & 0xFF
                        vsc_req_form[YCable.VSC_BYTE_ADDR1] = (fw_img_offset >> 8) & 0xFF
                        vsc_req_form[YCable.VSC_BYTE_ADDR2] = (fw_img_offset >> 16) & 0xFF
                        vsc_req_form[YCable.VSC_BYTE_ADDR3] = (fw_img_offset >> 24) & 0xFF
                        vsc_req_form[YCable.VSC_BYTE_CHKSUM_MSB] = (checksum >> 8) & 0xFF
                        vsc_req_form[YCable.VSC_BYTE_CHKSUM_LSB] = (checksum >> 0) & 0xFF
                        status = self.send_vsc(vsc_req_form)

                        if status == YCable.MCU_EC_NO_ERROR:
                            chunk_idx += 1
                            retry_count = 0
                        else:
                            self.log_error('Firmware binary transfer error (error code:%04X)' % (status))

                            if retry_count == 3:
                                self.log_error('Retry Xfer Fw Bin Error, abort firmware update')
                                self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                                return YCableBase.FIRMWARE_DOWNLOAD_FAILURE
                            retry_count += 1
                    else:
                        self.log_error('acquire lock timeout, failed to xfer firmware')
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                        return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

            '''
            Complete the local side firmware transferring
            '''
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                    vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_LOCAL_XFER_COMPLETE
                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('Veriyf firmware binary error (error code:0x%04X)' % (status))
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                        return YCableBase.FIRMWARE_DOWNLOAD_FAILURE
                else:
                    self.log_error('acquire lock timeout, failed to complete firmware xfer')
                    self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                    return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

            '''
            transfer firmware image from local side MCU to the other two via UART
            '''
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                    vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_UART_XFER
                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('Firmware binary UART transfer error (error code:0x%04X)' % (status))
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                        return YCableBase.FIRMWARE_DOWNLOAD_FAILURE
                else:
                    self.log_error('acquire lock timeout, failed to uart xfer')
                    self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                    return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

            uartXferStartTime = time.time()
            while True:
                with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                    if lock_status:
                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_UART_XFER_STATUS
                        status = self.send_vsc(vsc_req_form)

                        busy = self.read_mmap(YCable.MIS_PAGE_FC, 128)
                        self.read_mmap(YCable.MIS_PAGE_FC, 129)
                        self.read_mmap(YCable.MIS_PAGE_FC, 130)
                        self.read_mmap(YCable.MIS_PAGE_FC, 131)

                        if busy == 0:
                            break

                        if (time.time() - uartXferStartTime) > YCable.FWUPD_UART_XFER_TIMEOUT_SECS:
                            self.log_error(
                                'Get firmware binary UART transfer status error (error code:0x%04X)' % (status))
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

                        time.sleep(1)
                    else:
                        self.log_error('acquire lock timeout, failed to get uart xfer status')
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                        return YCableBase.FIRMWARE_DOWNLOAD_FAILURE
        else:
            self.log_error("platform_chassis is not loaded, failed to download firmware")
            return YCable.EEPROM_ERROR

        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_NOT_INITIATED_OR_FINISHED

        return YCableBase.FIRMWARE_DOWNLOAD_SUCCESS

    def activate_firmware(self, fwfile=None, hitless=False):
        """
        This routine should activate the downloaded firmware on all the
        components of the Y cable of the port for which this API is called..
        This API is meant to be used in conjunction with download_firmware API, and
        should be called once download_firmware API is successful.
        This means that the firmware which has been downloaded should be
        activated (start being utilized by the cable) once this API is
        successfully executed.
        The port on which this API is called for can be referred using self.port.

        Args:
            fwfile (optional):
                 a string, a path to the file which contains the firmware image.
                 Note that the firmware file can be in the format of the vendor's
                 choosing (binary, archive, etc.). But note that it should be one file
                 which contains firmware for all components of the Y-cable. In case the
                 vendor chooses to pass this file in activate_firmware, the API should
                 have the logic to retrieve the firmware version from this file
                 which has to be activated on the components of the Y-Cable
                 this API has been called for.
                 If None is passed for fwfile, the cable should activate whatever
                 firmware is marked to be activated next.
                 If provided, it should retrieve the firmware version(s) from this file, ensure
                 they are downloaded on the cable, then activate them.

            hitless (optional):
                a boolean, True, Hitless upgrade: it will backup/restore the current state
                                 (ex. variables of link status, API attributes...etc.) before
                                 and after firmware upgrade.
                a boolean, False, Non-hitless upgrade: it will update the firmware regardless
                                  the current status, a link flip can be observed during the upgrade.
        Returns:
            One of the following predefined constants:
                FIRMWARE_ACTIVATE_SUCCESS
                FIRMWARE_ACTIVATE_FAILURE
        """
        if self.platform_chassis is not None:
            if fwfile is None:
                with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                    if lock_status:
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS
                        side_bitmap = YCable.SIDE_BMP_ALL

                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_COMMIT
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                        vsc_req_form[YCable.VSC_BYTE_ADDR0]  = side_bitmap
                        status = self.send_vsc(vsc_req_form)
                        if status != YCable.MCU_EC_NO_ERROR:
                            self.log_error('Firmware commit error (error code:%04X)' % (status))
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_RUN
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                        vsc_req_form[YCable.VSC_BYTE_ADDR0]  = side_bitmap
                        vsc_req_form[YCable.VSC_BYTE_ADDR1]  = hitless
                        status = self.send_vsc(vsc_req_form)
                        time.sleep(5)
                        if status != YCable.MCU_EC_NO_ERROR:
                            self.log_error('Firmware run error (error code:%04X)' % (status))
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_NOT_INITIATED_OR_FINISHED
                    else:
                        self.log_error('acquire lock timeout, failed to activate firmware')
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                        return YCableBase.FIRMWARE_ACTIVATE_FAILURE
            else:
                try:
                    inFile = open(fwfile, 'rb')
                    fwImage = bytearray(inFile.read())
                    inFile.close()
                except Exception as e:
                    self.log_error('activate_firmware, open fw bin error(%s), fwfile:%s' % (e, fwfile))
                    return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                build_msb = struct.unpack_from('<B', fwImage[7:8])[0]
                build_lsb = struct.unpack_from('<B', fwImage[8:9])[0]
                rev_major = struct.unpack_from('<B', fwImage[9:10])[0]
                rev_minor = struct.unpack_from('<B', fwImage[10:11])[0]

                version_build_file = str(rev_major) + '.' + str(rev_minor) + chr(build_msb) + chr(build_lsb)

                side_bitmap = 0
                fwVer = self.get_firmware_version(YCableBase.TARGET_NIC)
                if fwVer is None:
                    self.log_error("activate_firmware, failed to get NIC firmware version")
                    return YCableBase.FIRMWARE_ACTIVATE_FAILURE
                else:                  
                    if fwVer['version_inactive'] == version_build_file:
                        side_bitmap |= YCable.SIDE_BMP_NIC

                fwVer = self.get_firmware_version(YCableBase.TARGET_TOR_A)
                if fwVer is None:
                    self.log_error("activate_firmware, failed to get TOR A firmware version")
                    return YCableBase.FIRMWARE_ACTIVATE_FAILURE
                else: 
                    if fwVer['version_inactive'] == version_build_file:
                        side_bitmap |= YCable.SIDE_BMP_TOR_A

                fwVer = self.get_firmware_version(YCableBase.TARGET_TOR_B)
                if fwVer is None:
                    self.log_error("activate_firmware, failed to get TOR B firmware version")
                    return YCableBase.FIRMWARE_ACTIVATE_FAILURE
                else: 
                    if fwVer['version_inactive'] == version_build_file:
                        side_bitmap |= YCable.SIDE_BMP_TOR_B
                    
                if side_bitmap:
                    with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                        if lock_status:
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS
                            vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                            vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_COMMIT
                            vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                            vsc_req_form[YCable.VSC_BYTE_ADDR0]  = side_bitmap
                            status = self.send_vsc(vsc_req_form)
                            if status != YCable.MCU_EC_NO_ERROR:
                                self.log_error('Firmware commit error (error code:%04X)' % (status))
                                self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                                return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                            vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                            vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_RUN
                            vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                            vsc_req_form[YCable.VSC_BYTE_ADDR0]  = side_bitmap
                            vsc_req_form[YCable.VSC_BYTE_ADDR1]  = hitless
                            status = self.send_vsc(vsc_req_form)
                            time.sleep(5)
                            if status != YCable.MCU_EC_NO_ERROR:
                                self.log_error('Firmware run error (error code:%04X)' % (status))
                                self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                                return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_NOT_INITIATED_OR_FINISHED
                        else:
                            self.log_error('acquire lock timeout, failed to activate firmware')
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            return YCableBase.FIRMWARE_ACTIVATE_FAILURE
        else:
            self.log_error("platform_chassis is not loaded, failed to activate firmware")
            return YCableBase.FIRMWARE_ACTIVATE_FAILURE

        return YCableBase.FIRMWARE_ACTIVATE_SUCCESS

    def rollback_firmware(self, fwfile=None):
        """
        This routine should rollback the firmware to the previous version
        which was being used by the cable. This API is intended to be called when the
        user either witnesses an activate_firmware API failure or sees issues with
        newer firmware in regards to stable cable functioning.
        The port on which this API is called for can be referred using self.port.

        Args:
            fwfile (optional):
                 a string, a path to the file which contains the firmware image.
                 Note that the firmware file can be in the format of the vendor's
                 choosing (binary, archive, etc.). But note that it should be one file
                 which contains firmware for all components of the Y-cable. In case the
                 vendor chooses to pass this file in rollback_firmware, the API should
                 have the logic to retrieve the firmware version from this file
                 which should not be activated on the components of the Y-Cable
                 this API has been called for.
                 If None is passed for fwfile, the cable should rollback whatever
                 firmware is marked to be rollback next.
                 If provided, it should retrieve the firmware version(s) from this file, ensure
                 that the firmware is rollbacked to a version which does not match to retrieved version(s).
                 This is exactly the opposite behavior of this param to activate_firmware
        Returns:
            One of the following predefined constants:
                FIRMWARE_ROLLBACK_SUCCESS
                FIRMWARE_ROLLBACK_FAILURE
        """

        if self.platform_chassis is not None:
            if self.activate_firmware(fwfile) == YCableBase.FIRMWARE_ACTIVATE_FAILURE:
                return YCableBase.FIRMWARE_ROLLBACK_FAILURE
        else:
            self.log_error("platform_chassis is not loaded, failed to activate firmware")
            return YCable.EEPROM_ERROR

        return YCableBase.FIRMWARE_ROLLBACK_SUCCESS

    def activate_target_firmware(self, target, fwfile=None, hitless=False):
        """
        This routine should activate the downloaded firmware on specific target
        of the Y cable of the port for which this API is called..
        This API is meant to be used in conjunction with download_firmware API, and
        should be called once download_firmware API is succesful.
        This means that the firmware which has been downloaded should be
        activated (start being utilized by the cable) once this API is
        successfully executed.
        The port on which this API is called for can be referred using self.port.
        Args:
            target:
                One of the following predefined constants, the actual target to activate the firmware on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
            fwfile (optional):
                 a string, a path to the file which contains the firmware image.
                 Note that the firmware file can be in the format of the vendor's
                 choosing (binary, archive, etc.). But note that it should be one file
                 which contains firmware for all components of the Y-cable. In case the
                 vendor chooses to pass this file in activate_firmware, the API should
                 have the logic to retrieve the firmware version from this file
                 which has to be activated on the components of the Y-Cable
                 this API has been called for.
                 If None is passed for fwfile, the cable should activate whatever
                 firmware is marked to be activated next.
                 If provided, it should retrieve the firmware version(s) from this file, ensure
                 they are downloaded on the cable, then activate them.
            hitless (optional):
                a boolean, True, Hitless upgrade: it will backup/restore the current state
                                 (ex. variables of link status, API attributes...etc.) before
                                 and after firmware upgrade.
                a boolean, False, Non-hitless upgrade: it will update the firmware regardless
                                  the current status, a link flip can be observed during the upgrade.
        Returns:
            One of the following predefined constants:
                FIRMWARE_ACTIVATE_SUCCESS
                FIRMWARE_ACTIVATE_FAILURE
        """
        if self.platform_chassis is not None:

            if target == YCableBase.TARGET_NIC:
                act_bmp = YCable.SIDE_BMP_NIC
            elif target == YCableBase.TARGET_TOR_A:
                act_bmp = YCable.SIDE_BMP_TOR_A
            elif target == YCableBase.TARGET_TOR_B:
                act_bmp = YCable.SIDE_BMP_TOR_B
            else:
                act_bmp = YCable.SIDE_BMP_ALL

            if fwfile is None:
                with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                    if lock_status:
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS

                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_COMMIT
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                        vsc_req_form[YCable.VSC_BYTE_ADDR0]  = act_bmp
                        status = self.send_vsc(vsc_req_form)
                        if status != YCable.MCU_EC_NO_ERROR:
                            self.log_error('Firmware commit error (error code:%04X)' % (status))
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_RUN
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                        vsc_req_form[YCable.VSC_BYTE_ADDR0]  = act_bmp
                        vsc_req_form[YCable.VSC_BYTE_ADDR1]  = hitless
                        status = self.send_vsc(vsc_req_form)
                        time.sleep(5)
                        if status != YCable.MCU_EC_NO_ERROR:
                            self.log_error('Firmware run error (error code:%04X)' % (status))
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_NOT_INITIATED_OR_FINISHED
                    else:
                        self.log_error('acquire lock timeout, failed to activate target firmware')
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                        return YCableBase.FIRMWARE_ACTIVATE_FAILURE
            else:
                try:
                    inFile = open(fwfile, 'rb')
                    fwImage = bytearray(inFile.read())
                    inFile.close()
                except Exception as e:
                    self.log_error('activate_target_firmware, open fw bin error(%s), fwfile:%s' % (e, fwfile))
                    return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                build_msb = struct.unpack_from('<B', fwImage[7:8])[0]
                build_lsb = struct.unpack_from('<B', fwImage[8:9])[0]
                rev_major = struct.unpack_from('<B', fwImage[9:10])[0]
                rev_minor = struct.unpack_from('<B', fwImage[10:11])[0]

                version_build_file = str(rev_major) + '.' + str(rev_minor) + chr(build_msb) + chr(build_lsb)

                chk_bitmap = 0
                fwVer = self.get_firmware_version(YCableBase.TARGET_NIC)
                if fwVer is None:
                    self.log_error("activate_target_firmware, failed to get NIC firmware version")
                    return YCableBase.FIRMWARE_ACTIVATE_FAILURE
                else:                  
                    if fwVer['version_inactive'] == version_build_file:
                        chk_bitmap |= YCable.SIDE_BMP_NIC

                fwVer = self.get_firmware_version(YCableBase.TARGET_TOR_A)
                if fwVer is None:
                    self.log_error("activate_target_firmware, failed to get TOR A firmware version")
                    return YCableBase.FIRMWARE_ACTIVATE_FAILURE
                else: 
                    if fwVer['version_inactive'] == version_build_file:
                        chk_bitmap |= YCable.SIDE_BMP_TOR_A

                fwVer = self.get_firmware_version(YCableBase.TARGET_TOR_B)
                if fwVer is None:
                    self.log_error("activate_target_firmware, failed to get TOR B firmware version")
                    return YCableBase.FIRMWARE_ACTIVATE_FAILURE
                else: 
                    if fwVer['version_inactive'] == version_build_file:
                        chk_bitmap |= YCable.SIDE_BMP_TOR_B
                    
                act_bmp = act_bmp & chk_bitmap

                if act_bmp:
                    with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                        if lock_status:
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS
                            vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                            vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_COMMIT
                            vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                            vsc_req_form[YCable.VSC_BYTE_ADDR0]  = act_bmp
                            status = self.send_vsc(vsc_req_form)
                            if status != YCable.MCU_EC_NO_ERROR:
                                self.log_error('Firmware commit error (error code:%04X)' % (status))
                                self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                                return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                            vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                            vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_RUN
                            vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                            vsc_req_form[YCable.VSC_BYTE_ADDR0]  = act_bmp
                            vsc_req_form[YCable.VSC_BYTE_ADDR1]  = hitless
                            status = self.send_vsc(vsc_req_form)
                            time.sleep(5)
                            if status != YCable.MCU_EC_NO_ERROR:
                                self.log_error('Firmware run error (error code:%04X)' % (status))
                                self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                                return YCableBase.FIRMWARE_ACTIVATE_FAILURE

                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_NOT_INITIATED_OR_FINISHED
                        else:
                            self.log_error('acquire lock timeout, failed to activate target firmware')
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            return YCableBase.FIRMWARE_ACTIVATE_FAILURE
        else:
            self.log_error("platform_chassis is not loaded, failed to activate target firmware")
            return YCableBase.FIRMWARE_ACTIVATE_FAILURE

        return YCableBase.FIRMWARE_ACTIVATE_SUCCESS

    def set_switching_mode(self, mode):
        """
        This API enables the auto switching or manual switching feature on the Y-Cable,
        depending upon the mode entered by the user.
        Autoswitch feature if enabled actually does an automatic toggle of the mux in case the active
        side link goes down and basically points the mux to the other side.
        The port on which this API is called for can be referred using self.port.

        Args:
             mode:
                 One of the following predefined constants:
                 SWITCHING_MODE_AUTO
                 SWITCHING_MODE_MANUAL

                 specifies which type of switching mode we set the Y-Cable to
                 either SWITCHING_MODE_AUTO or SWITCHING_MODE_MANUAL

        Returns:
            a Boolean, True if the switch succeeded and False if it did not succeed.
        """

        if mode == YCableBase.SWITCHING_MODE_AUTO:
            buffer = bytearray([1])
        elif mode == YCableBase.SWITCHING_MODE_MANUAL:
            buffer = bytearray([0])
        else:
            self.log_error(
                "ERR: invalid mode provided for autoswitch feature, failed to do a switch")
            return False

        curr_offset = YCable.OFFSET_ENABLE_AUTO_SWITCH

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
        else:
            self.log_error("platform_chassis is not loaded, failed to set switching mode")
            return YCable.EEPROM_ERROR

        return result

    def get_switching_mode(self):
        """
        This API returns which type of switching mode the cable is set to auto/manual
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            One of the following predefined constants:
               SWITCHING_MODE_AUTO if auto switch is enabled.
               SWITCHING_MODE_MANUAL if manual switch is enabled.
        """
        curr_offset = YCable.OFFSET_ENABLE_AUTO_SWITCH

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)

            if result[0] == 1:
                return YCableBase.SWITCHING_MODE_AUTO
            else:
                return YCableBase.SWITCHING_MODE_MANUAL
        else:
            self.log_error("platform_chassis is not loaded, failed to get the switch mode")
            return YCable.EEPROM_ERROR

    def get_nic_temperature(self):
        """
        This API returns nic temperature of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            an Integer, the temperature of the NIC MCU
        """

        curr_offset = YCable.OFFSET_NIC_TEMPERATURE
        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            temp = result[0]
        else:
            self.log_error("platform_chassis is not loaded, failed to get NIC temp")
            return -1

        return temp

    def get_local_temperature(self):
        """
        This API returns local ToR temperature of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            an Integer, the temperature of the local MCU
        """

        curr_offset = YCable.OFFSET_INTERNAL_TEMPERATURE
        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            temp = result[0]
        else:
            self.log_error("platform_chassis is not loaded, failed to get local temp")
            return YCable.EEPROM_ERROR

        return temp

    def get_nic_voltage(self):
        """
        This API returns nic voltage of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a float, the voltage of the NIC MCU
        """

        if self.platform_chassis is not None:
            curr_offset = YCable.OFFSET_NIC_VOLTAGE
            msb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            lsb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset+1, 1)
            voltage = (((msb_result[0] << 8) | lsb_result[0]) * 0.0001)
        else:
            self.log_error("platform_chassis is not loaded, failed to get NIC voltage")
            return -1

        return voltage

    def get_local_voltage(self):
        """
        This API returns local ToR voltage of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a float, the voltage of the local MCU
        """

        if self.platform_chassis is not None:
            curr_offset = YCable.OFFSET_INTERNAL_VOLTAGE
            msb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            lsb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset+1, 1)
            voltage = (((msb_result[0] << 8) | lsb_result[0]) * 0.0001)
        else:
            self.log_error("platform_chassis is not loaded, failed to get local voltage")
            return YCable.EEPROM_ERROR

        return voltage

    def get_alive_status(self):
        """
        This API checks if cable is connected to all the ports and is healthy.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a boolean, True if the cable is alive
                     , False if the cable is not alive
        """

        if self.platform_chassis is not None:
            curr_offset = YCable.OFFSET_NIC_SIGNAL_DETECTION
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 6)
            if result is False:
                return result

            for idx in range(6):
                if result[idx] == 0:
                    return False
        else:
            self.log_error("platform_chassis is not loaded, failed to get active status")
            return YCable.EEPROM_ERROR

        return True

    def reset(self, target):
        """
        This API resets the MCU to which this API is called for.
        The target specifies which MCU is supposed to be reset
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the actual target to check the link on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB

        Returns:
            a boolean, True if the cable is target reset
                     , False if the cable target is not reset
        """

        '''
        use firmare_run cmd to emulate module reset
        '''
        if self.platform_chassis is not None:
            if target != YCableBase.TARGET_NIC and target != YCableBase.TARGET_TOR_A and target != YCableBase.TARGET_TOR_B:
                self.log_error("reset: unsupported target")
                return False

            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_RUN
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                    vsc_req_form[YCable.VSC_BYTE_ADDR0] = (1 << target)
                    vsc_req_form[YCable.VSC_BYTE_ADDR1] = 0
                    status = self.send_vsc(vsc_req_form)

                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error("unable to reset the module")
                        return False

                    if target  == YCableBase.TARGET_NIC:
                        time.sleep(4)
                    else:
                        time.sleep(2)
                else:
                    self.log_error('acquire lock timeout, failed to reset')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to reset")
            return YCable.EEPROM_ERROR

        return True

    def create_port(self, speed, fec_mode_tor = YCableBase.FEC_MODE_NONE, fec_mode_nic = YCableBase.FEC_MODE_NONE, anlt_tor = False, anlt_nic = False):
        """
        This API sets the mode of the cable/port for corresponding lane/FEC etc. configuration as specified.
        The speed specifies which mode is supposed to be set 50G, 100G etc
        the AN/LT specifies if auto-negotiation + link training (AN/LT) has to be enabled
        Note that in case create_port is called multiple times, the most recent api call will take the precedence
        on either of TOR side.
        The port on which this API is called for can be referred using self.port.

        Args:
            speed:
                an Integer, the value for the link speed to be configured (in megabytes).
                examples:
                50000 -> 50G
                100000 -> 100G

            fec_mode_tor:
                One of the following predefined constants, the actual FEC mode for the ToR to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC

            fec_mode_nic:
                One of the following predefined constants, the actual FEC mode for the nic to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC

            anlt_tor:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled on ToR's
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled on ToR's

            anlt_nic:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled on nic
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled on nic


        Returns:
            a boolean, True if the port is configured
                     , False if the port is not configured
        """

        if self.platform_chassis is not None:
            mode = 0
            if speed == 50000:
                mode |= (0 << 6)
            elif speed == 100000:
                mode |= (1 << 6)
            else:
                self.log_error("create port: unsupported speed:%d" % (speed))
                return False

            mode |= (1 << 0) if anlt_nic else (0 << 0)
            mode |= (1 << 1) if anlt_tor else (0 << 1)
            mode |= (1 << 3) if fec_mode_nic == YCableBase.FEC_MODE_RS else (0 << 3)
            mode |= (1 << 4) if fec_mode_tor == YCableBase.FEC_MODE_RS else (0 << 4)

            curr_offset = YCable.OFFSET_NIC_MODE_CONFIGURATION
            buffer = bytearray([mode])
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
        else:
            self.log_error("platform_chassis is not loaded, failed to create port")
            return YCable.EEPROM_ERROR

        return True

    def get_speed(self):
        """
        This API gets the mode of the cable for corresponding lane configuration.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            speed:
                an Integer, the value for the link speed is configured (in megabytes).
                examples:
                50000 -> 50G
                100000 -> 100G
        """

        speed = 0
        if self.platform_chassis is not None:
            curr_offset = YCable.OFFSET_NIC_MODE_CONFIGURATION
            mode = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)

            if (mode[0] >> 6) == 0:
                speed = 50000
            elif (mode[0] >> 6) == 1:
                speed = 100000
            else:
                self.log_error("unsupported speed")
                return -1
        else:
            self.log_error("platform_chassis is not loaded, failed to get speed")
            return YCable.EEPROM_ERROR

        return speed

    def set_fec_mode(self, fec_mode, target):
        """
        This API gets the FEC mode of the cable for which it is set to.
        The port on which this API is called for can be referred using self.port.

        Args:
            fec_mode:
                One of the following predefined constants, the actual FEC mode for the port to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC
            target:
                One of the following predefined constants, the actual target to set the FEC mode on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB


        Returns:
            a boolean, True if the FEC mode is configured
                     , False if the FEC mode is not configured
        """

        if self.platform_chassis is not None:
            curr_offset = YCable.OFFSET_NIC_MODE_CONFIGURATION
            mode = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)

            if target == YCableBase.TARGET_NIC:
                mode[0] &= ~(1 << 3)
                mode[0] |= (1 << 3) if fec_mode == YCableBase.FEC_MODE_RS else (0 << 3)
            elif target == YCableBase.TARGET_TOR_A or target == YCableBase.TARGET_TOR_B:
                mode[0] &= ~(1 << 4)
                mode[0] |= (1 << 4) if fec_mode == YCableBase.FEC_MODE_RS else (0 << 4)
            else:
                self.log_error("set fec mode: unsupported target")
                return False

            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, mode)
            if result is False:
                return result
        else:
            self.log_error("platform_chassis is not loaded, failed to set fec mode")
            return YCable.EEPROM_ERROR

        return True

    def get_fec_mode(self, target):
        """
        This API gets the FEC mode of the cable which it is set to.
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the actual target to FEC mode on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB

        Returns:
            fec_mode:
                One of the following predefined constants, the actual FEC mode for the port to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC
        """

        fec_mode = YCableBase.FEC_MODE_NONE
        if self.platform_chassis is not None:
            curr_offset = YCable.OFFSET_NIC_MODE_CONFIGURATION
            mode = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)

            if target == YCableBase.TARGET_NIC:
                if mode[0] & (1 << 3):
                    fec_mode = YCableBase.FEC_MODE_RS
            elif target == YCableBase.TARGET_TOR_A or target == YCableBase.TARGET_TOR_B:
                if mode[0] & (1 << 4):
                    fec_mode = YCableBase.FEC_MODE_RS
            else:
                self.log_error("get fec mode: unsupported target")
        else:
            self.log_error("platform_chassis is not loaded, failed to get fec mode")
            return YCable.EEPROM_ERROR

        return fec_mode

    def set_anlt(self, enable, target):
        """
        This API enables/disables the cable auto-negotiation + link training (AN/LT).
        The port on which this API is called for can be referred using self.port.

        Args:
            enable:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled
            target:
                One of the following predefined constants, the actual target to get the stats on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB


        Returns:
            a boolean, True if the auto-negotiation + link training (AN/LT) enable/disable specified is configured
                     , False if the auto-negotiation + link training (AN/LT) enable/disable specified is not configured
        """

        if self.platform_chassis is not None:
            curr_offset = YCable.OFFSET_NIC_MODE_CONFIGURATION
            mode = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)

            if target == YCableBase.TARGET_NIC:
                mode[0] &= ~(1 << 0)
                mode[0] |= (1 << 0) if enable else (0 << 0)
            elif target == YCableBase.TARGET_TOR_A or target == YCableBase.TARGET_TOR_B:
                mode[0] &= ~(1 << 1)
                mode[0] |= (1 << 1) if enable else (0 << 1)
            else:
                self.log_error("set anlt: unsupported target")
                return False

            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, mode)
            if result is False:
                return result
        else:
            self.log_error("platform_chassis is not loaded, failed to set anlt")
            return YCable.EEPROM_ERROR

        return True

    def get_anlt(self, target):
        """
        This API gets the auto-negotiation + link training (AN/LT) mode of the cable for corresponding port.
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the actual target to get the AN/LT on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB

        Returns:
            a boolean, True if auto-negotiation + link training (AN/LT) is enabled
                     , False if auto-negotiation + link training (AN/LT) is not enabled
        """

        anlt_mode = False
        if self.platform_chassis is not None:
            curr_offset = YCable.OFFSET_NIC_MODE_CONFIGURATION
            mode = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)

            if target == YCableBase.TARGET_NIC:
                if mode[0] & (1 << 0):
                    anlt_mode = True

            elif target == YCableBase.TARGET_TOR_A or target == YCableBase.TARGET_TOR_B:
                if mode[0] & (1 << 1):
                    anlt_mode = True
            else:
                self.log_error("get anlt: unsupported target")
        else:
            self.log_error("platform_chassis is not loaded, failed to get anlt")
            return YCable.EEPROM_ERROR

        return anlt_mode

    def get_event_log(self, clear_on_read=False):
        """
        This API returns the event log of the cable
        The port on which this API is called for can be referred using self.port.

        Args:
            clear_on_read:
                a boolean, True if the log has to be cleared after read
                         , False if the log is not to be cleared after read

        Returns:
           list:
              a list of strings which correspond to the event logs of the cable
        """

        result = []

        if self.platform_chassis is not None:
            if (clear_on_read):
                with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                    if lock_status:
                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_EVENTLOG
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.EVENTLOG_OPTION_CLEAR
                        status = self.send_vsc(vsc_req_form)

                        if status != YCable.MCU_EC_NO_ERROR:
                            self.log_error("clear event log error(error code:%04X)" % (status))
                            return YCable.EEPROM_ERROR
                    else:
                        self.log_error("acquire lock timeout, failed to clear event log")
                        return YCable.EEPROM_ERROR

            last_read_id = -1

            event_type_str = {
                0x0000: 'EventLog Header',
                0x0001: 'Auto Switch',
                0x0002: 'Manual Switch',
                0x0003: 'BER Measurement',
                0x0004: 'PRBS Generation',
                0x0005: 'Loopback Mode',
                0x0006: 'Eye Measurement',
                0x0007: 'Epoch Time',
                0x0008: 'Temperature',
                0x0009: 'Voltage',
                0x0100: 'Link Down',
                0x0200: 'Firmware Update',
            }

            read_cycle = 0
            while (True):
                with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                    if lock_status:
                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_EVENTLOG
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.EVENTLOG_OPTION_DUMP
                        vsc_req_form[YCable.VSC_BYTE_ADDR0] = (last_read_id >> 0) & 0xFF
                        vsc_req_form[YCable.VSC_BYTE_ADDR1] = (last_read_id >> 8) & 0xFF
                        vsc_req_form[YCable.VSC_BYTE_ADDR2] = (last_read_id >> 16) & 0xFF
                        vsc_req_form[YCable.VSC_BYTE_ADDR3] = (last_read_id >> 24) & 0xFF
                        status = self.send_vsc(vsc_req_form)

                        if status == YCable.MCU_EC_NO_ERROR:
                            fetch_cnt = self.read_mmap(YCable.MIS_PAGE_VSC, 134)
                            if (fetch_cnt == 0):
                                break
                        else:
                            self.log_error("download event log error(error code:%04X)" % (status))
                            return YCable.EEPROM_ERROR

                        event_data = bytearray(YCable.EVENTLOG_PAYLOAD_SIZE * fetch_cnt)

                        for byte_offset in range(0, YCable.EVENTLOG_PAYLOAD_SIZE * fetch_cnt):
                            byte_data = self.read_mmap(YCable.MIS_PAGE_FC, 128 + byte_offset)
                            event_data[byte_offset] = byte_data

                        for curr_idx in range(0, fetch_cnt):
                            byte_offset = curr_idx * YCable.EVENTLOG_PAYLOAD_SIZE
                            event_id = struct.unpack_from('<H', event_data[byte_offset + 0: byte_offset + 2])[0]
                            epoch = struct.unpack_from('<I', event_data[byte_offset + 2: byte_offset + 6])[0]
                            epoch_ms = struct.unpack_from('<H', event_data[byte_offset + 6: byte_offset + 8])[0]
                            event_type = struct.unpack_from('<H', event_data[byte_offset + 8: byte_offset + 10])[0]
                            detail1 = struct.unpack_from('<I', event_data[byte_offset + 10: byte_offset + 14])[0]
                            detail2 = struct.unpack_from('<I', event_data[byte_offset + 14: byte_offset + 18])[0]

                            if epoch != 0xFFFFFFFF:
                                entry = {}

                                entry['EventId'] = event_id
                                entry['Timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(epoch)) + '.%03d' % (epoch_ms)
                                entry['EventType'] = event_type_str[event_type]
                                entry['Detail1'] = detail1
                                entry['Detail2'] = detail2

                                result.append(entry)

                                last_read_id = event_id

                        '''break the while loop if hit maximum read cycle to avoid deadlock'''
                        read_cycle += 1
                        if read_cycle > 150:
                            break
                    else:
                        self.log_error('acquire lock timeout, failed to get event log')
                        return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get event log")
            return YCable.EEPROM_ERROR

        return result

    def get_pcs_stats(self, target):
        """
        This API returns the pcs statistics of the cable
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the actual target to get the stats on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB

        Returns:
           a dictionary:
               a detailed format agreed upon by vendors
        """

        pcs_stats = {}

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    quad = 0
                    ch = 0
                    if target == YCableBase.TARGET_NIC:
                        quad = 0
                    elif target == YCableBase.TARGET_TOR_A:
                        quad = 4
                    elif target == YCableBase.TARGET_TOR_B:
                        quad = 6
                    else:
                        self.log_error("get pcs stats: unsupported target")
                        return pcs_stats

                    base = (quad << 20) + 0xa0000
                    Rx = (ch * 35) + 0x40
                    pcs_stats['Rx Frames OK']         = self.tcm_read(base + 4 * (Rx + 6))
                    pcs_stats['Rx Chk SEQ Errs']      = self.tcm_read(base + 4 * (Rx + 7))
                    pcs_stats['Rx Alignment Errs']    = self.tcm_read(base + 4 * (Rx + 2))
                    pcs_stats['Rx In Errs']           = self.tcm_read(base + 4 * (Rx + 9))
                    pcs_stats['Rx FrameTooLong Errs'] = self.tcm_read(base + 4 * (Rx + 4))
                    pcs_stats['Rx Octets OK']         = self.tcm_read(base + 4 * (Rx + 1))

                    Tx = (ch * 26) + 0xC
                    pcs_stats['Tx Frames OK'] = self.tcm_read(base + 4 * (Tx + 3))
                    pcs_stats['Tx Out Errs']  = self.tcm_read(base + 4 * (Tx + 5))
                    pcs_stats['Tx Octets OK'] = self.tcm_read(base + 4 * (Tx + 1))
                else:
                    self.log_error('acquire lock timeout, failed to get pcs statisics')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get pcs statisics")
            return YCable.EEPROM_ERROR

        return pcs_stats

    def get_fec_stats(self, target):
        """
        This API returns the FEC statistics of the cable
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the actual target to get the stats on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB

        Returns:
           a dictionary:
               a detailed format agreed upon by vendors
        """
        fec_stats = {}

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    quad = 0
                    ch = 0
                    if target == YCableBase.TARGET_NIC:
                        quad = 0
                    elif target == YCableBase.TARGET_TOR_A:
                        quad = 4
                    elif target == YCableBase.TARGET_TOR_B:
                        quad = 6
                    else:
                        self.log_error("get fec stats: unsupported target")
                        return fec_stats

                    base = (quad << 20) + 0xA2800

                    self.tcm_write(base + (3 << 2), 0x10000000 | (1 << ch))

                    lsb = self.tcm_read(base + (8 << 2))
                    msb = self.tcm_read(base + (0 << 2))
                    fec_stats['Total recevied CW'] = (msb << 32) | lsb

                    lsb = self.tcm_read(base + (9 << 2))
                    msb = self.tcm_read(base + (0 << 2))
                    fec_stats['Total correct CW'] = (msb << 32) | lsb

                    lsb = self.tcm_read(base + (10 << 2))
                    msb = self.tcm_read(base + (0 << 2))
                    fec_stats['Total corrected CW'] = (msb << 32) | lsb

                    fec_stats['Total uncorrectable CW'] = self.tcm_read(base + (11 << 2))

                    lsb = self.tcm_read(base + (12 << 2))
                    msb = self.tcm_read(base + ( 0 << 2))
                    fec_stats['Corrected CW ( 1 sym err)'] = (msb << 32) | lsb
                    lsb = self.tcm_read(base + (13 << 2))
                    msb = self.tcm_read(base + ( 0 << 2))
                    fec_stats['Corrected CW ( 2 sym err)'] = (msb << 32) | lsb
                    fec_stats['Corrected CW ( 3 sym err)'] = self.tcm_read(base + (14 << 2))
                    fec_stats['Corrected CW ( 4 sym err)'] = self.tcm_read(base + (15 << 2))
                    fec_stats['Corrected CW ( 5 sym err)'] = self.tcm_read(base + (16 << 2))
                    fec_stats['Corrected CW ( 6 sym err)'] = self.tcm_read(base + (17 << 2))
                    fec_stats['Corrected CW ( 7 sym err)'] = self.tcm_read(base + (18 << 2))
                    fec_stats['Corrected CW ( 8 sym err)'] = self.tcm_read(base + (19 << 2))
                    fec_stats['Corrected CW ( 9 sym err)'] = self.tcm_read(base + (20 << 2))
                    fec_stats['Corrected CW (10 sym err)'] = self.tcm_read(base + (21 << 2))
                    fec_stats['Corrected CW (11 sym err)'] = self.tcm_read(base + (22 << 2))
                    fec_stats['Corrected CW (12 sym err)'] = self.tcm_read(base + (23 << 2))
                    fec_stats['Corrected CW (13 sym err)'] = self.tcm_read(base + (24 << 2))
                    fec_stats['Corrected CW (14 sym err)'] = self.tcm_read(base + (25 << 2))
                    fec_stats['Corrected CW (15 sym err)'] = self.tcm_read(base + (26 << 2))
                else:
                    self.log_error('acquire lock timeout, failed to get fec statisics')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get fec statisics")
            return YCable.EEPROM_ERROR

        return fec_stats

    def set_autoswitch_hysteresis_timer(self, time):
        """
        This API sets the hysteresis timer of the cable. This is basically the time in auto-switch mode
        which the mux has to wait after toggling it once, before again toggling the mux to a different ToR
        The port on which this API is called for can be referred using self.port.

        Args:
            time:
                an Integer, the time value for hysteresis to be set in milliseconds

        Returns:
            a boolean, True if the time is configured
                     , False if the time is not configured
        """
        curr_offset = YCable.OFFSET_AUTO_SWITCH_HYSTERESIS

        buffer = bytearray([time])

        if self.platform_chassis is not None:
            self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
        else:
            self.log_error("platform_chassis is not loaded, failed to set autoswitch hysteresis timer")
            return YCable.EEPROM_ERROR

        return True

    def get_autoswitch_hysteresis_timer(self):
        """
        This API gets the hysteresis timer of the cable. This is basically the time in auto-switch mode
        which the mux has to wait after toggling it once, before again toggling the mux to a different ToR
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            time:
                an Integer, the time value for hysteresis is configured in milliseconds
        """
        curr_offset = YCable.OFFSET_AUTO_SWITCH_HYSTERESIS

        if self.platform_chassis is not None:
            time = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log_error("platform_chassis is not loaded, failed to get autoswitch hysteresis timer")
            return YCable.EEPROM_ERROR

        return int(time[0])

    def restart_anlt(self, target):
        """
        This API restarts auto-negotiation + link training (AN/LT) mode
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the actual target to restart AN/LT on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB

        Returns:
            a boolean, True if restart is successful
                     , False if the restart is not successful
        """

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    lane = 0
                    if target == YCableBase.TARGET_NIC:
                        lane = 0
                    elif target == YCableBase.TARGET_TOR_A:
                        lane = 12
                    elif target == YCableBase.TARGET_TOR_B:
                        lane = 20
                    else:
                        self.log_error("restart anlt: unsupported target")
                        return False

                    self.fw_cmd_ext(0x7040, 0, lane)
                else:
                    self.log_error('acquire lock timeout, failed to restart anlt')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to restart anlt")
            return YCable.EEPROM_ERROR

        return True

    def get_anlt_stats(self, target):
        """
        This API returns auto-negotiation + link training (AN/LT) mode statistics
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the actual target to get AN/LT stats on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB

        Returns:
           a dictionary:
               a detailed format agreed upon by vendors
        """

        anlt_stat = {}
        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    an_sm = 0
                    if target == YCableBase.TARGET_NIC:
                        an_sm = self.reg_read(0x0048)
                        lanes=[0,4]
                    elif target == YCableBase.TARGET_TOR_A:
                        an_sm = self.reg_read(0x5448)
                        lanes=[12,16]
                    elif target == YCableBase.TARGET_TOR_B:
                        an_sm = self.reg_read(0x5C48)
                        lanes=[20,24]
                    else:
                        self.log_error("get anlt stats: unsupported target")

                    anlt_stat['AN_StateMachine'] = an_sm

                    for idx, ln in enumerate(range(lanes[0], lanes[1])):
                        lt_tx1 = self.reg_read(0xB3 | 0x200 * ln)
                        lt_tx2 = self.reg_read(0xB4 | 0x200 * ln)
                        anlt_stat['LT_TX_lane%d' % idx] = [(lt_tx1 >> 8) & 0xFF, lt_tx1 & 0xFF, (lt_tx2 >> 8) & 0xFF, lt_tx2 & 0xFF]
                else:
                    self.log_error('acquire lock timeout, failed to get anlt stat')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get anlt stats")
            return YCable.EEPROM_ERROR

        return anlt_stat

#############################################################################################
###                                  Debug Functionality                                  ###
#############################################################################################

    def set_debug_mode(self, enable):
        """
        This API enables/disables a debug mode that the port is now
        going to be run on. If enabled, this means that PRBS/Loopback etc. type diagnostic mode
        is now going to be run on the port and hence normal traffic will be disabled
        on it if enabled and vice-versa if disabled.
        enable is typically to be used at the software level to inform the software
        that debug APIs will be called afterwords.
        disable will disable any previously enabled debug functionality inside the cable
        so that traffic can pass through. Also it'll inform the software to come out of the debug mode.
        The port on which this API is called for can be referred using self.port.

        Args:
            enable:
            a boolean, True if the debug mode needs to be enabled
                     , False if the debug mode needs to be disabled


        Returns:
            a boolean, True if the enable is successful
                     , False if the enable failed
        """

        raise NotImplementedError

    def get_debug_mode(self):
        """
        This API checks if a debug mode is currently being run on the port
        for which this API is called for.
        This means that PRBS/Loopback etc. type diagnostic mode
        if any are being run on the port this should return True else False.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a boolean, True if debug mode enabled
                     , False if debug mode not enabled
        """

        raise NotImplementedError

    def enable_prbs_mode(self, target, mode_value, lane_mask, direction=YCableBase.PRBS_DIRECTION_BOTH):
        """
        This API configures and enables the PRBS mode/type depending upon the mode_value the user provides.
        The mode_value configures the PRBS Type for generation and BER sensing on a per side basis.
        Target is an integer for selecting which end of the Y cable we want to run PRBS on.
        LaneMap specifies the lane configuration to run the PRBS on.
        Note that this is a diagnostic mode command and must not run during normal traffic/switch operation
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the target on which to enable the PRBS:
                    EYE_PRBS_LOOPBACK_TARGET_LOCAL -> local side,
                    EYE_PRBS_LOOPBACK_TARGET_TOR_A -> TOR A
                    EYE_PRBS_LOOPBACK_TARGET_TOR_B -> TOR B
                    EYE_PRBS_LOOPBACK_TARGET_NIC -> NIC
            mode_value:
                 an Integer, the mode/type for configuring the PRBS mode.

            lane_mask:
                 an Integer, representing the lane_mask to be run PRBS on
                 0bit for lane 0, 1bit for lane1 and so on.
                 for example 3 -> 0b'0011, means running on lane0 and lane1
            direction:
                One of the following predefined constants, the direction to run the PRBS:
                    PRBS_DIRECTION_BOTH
                    PRBS_DIRECTION_GENERATOR
                    PRBS_DIRECTION_CHECKER

        Returns:
            a boolean, True if the enable is successful
                     , False if the enable failed

        """

        buffer = bytearray([target])
        curr_offset = YCable.OFFSET_TARGET

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result

            buffer = bytearray([0])
            curr_offset = YCable.OFFSET_ENABLE_PRBS
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result

            buffer = bytearray([mode_value])
            curr_offset = YCable.OFFSET_CONFIGURE_PRBS_TYPE
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result

            buffer = bytearray([lane_mask])
            curr_offset = YCable.OFFSET_ENABLE_PRBS
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
        else:
            self.log_error("platform_chassis is not loaded, failed to enable the PRBS mode")
            return YCable.EEPROM_ERROR

        return result

    def disable_prbs_mode(self, target, direction):
        """
        This API disables the PRBS mode on the physical port.
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the target on which to disable the PRBS:
                    EYE_PRBS_LOOPBACK_TARGET_LOCAL -> local side,
                    EYE_PRBS_LOOPBACK_TARGET_TOR_A -> TOR A
                    EYE_PRBS_LOOPBACK_TARGET_TOR_B -> TOR B
                    EYE_PRBS_LOOPBACK_TARGET_NIC -> NIC
            direction:
                One of the following predefined constants, the direction to run the PRBS:
                    PRBS_DIRECTION_BOTH
                    PRBS_DIRECTION_GENERATOR
                    PRBS_DIRECTION_CHECKER

        Returns:
            a boolean, True if the disable is successful
                     , False if the disable failed
        """

        buffer = bytearray([target])
        curr_offset = YCable.OFFSET_TARGET

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
            buffer = bytearray([0])
            curr_offset = YCable.OFFSET_ENABLE_PRBS
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
        else:
            self.log_error("platform_chassis is not loaded, failed to disable the PRBS mode")
            return YCable.EEPROM_ERROR

        return result

    def enable_loopback_mode(self, target, lane_mask, mode=YCableBase.LOOPBACK_MODE_NEAR_END):
        """
        This API configures and enables the Loopback mode on the port user provides.
        Target is an integer for selecting which end of the Y cable we want to run loopback on.
        LaneMap specifies the lane configuration to run the loopback on.
        Note that this is a diagnostic mode command and must not run during normal traffic/switch operation
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the target on which to enable the loopback:
                    EYE_PRBS_LOOPBACK_TARGET_LOCAL -> local side,
                    EYE_PRBS_LOOPBACK_TARGET_TOR_A -> TOR A
                    EYE_PRBS_LOOPBACK_TARGET_TOR_B -> TOR B
                    EYE_PRBS_LOOPBACK_TARGET_NIC -> NIC
            mode:
                One of the following predefined constants, the mode to be run for loopback:
                    LOOPBACK_MODE_NEAR_END
                    LOOPBACK_MODE_FAR_END
            lane_mask:
                 an Integer, representing the lane_mask to be run loopback on
                 0bit for lane 0, 1bit for lane1 and so on.
                 for example 3 -> 0b'0011, means running on lane0 and lane1

        Returns:
            a boolean, True if the enable is successful
                     , False if the enable failed
        """

        buffer = bytearray([target])
        curr_offset = YCable.OFFSET_TARGET

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
            buffer = bytearray([lane_mask])
            curr_offset = YCable.OFFSET_ENABLE_LOOPBACK
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
        else:
            self.log_error("platform_chassis is not loaded, failed to enable the loopback mode")
            return YCable.EEPROM_ERROR

        return result

    def disable_loopback_mode(self, target):
        """
        This API disables the Loopback mode on the port user provides.
        Target is an integer for selecting which end of the Y cable we want to run loopback on.
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the target on which to disable the loopback:
                    EYE_PRBS_LOOPBACK_TARGET_LOCAL -> local side,
                    EYE_PRBS_LOOPBACK_TARGET_TOR_A -> TOR A
                    EYE_PRBS_LOOPBACK_TARGET_TOR_B -> TOR B
                    EYE_PRBS_LOOPBACK_TARGET_NIC -> NIC

        Returns:
            a boolean, True if the disable is successful
                     , False if the disable failed
        """
        buffer = bytearray([target])
        curr_offset = YCable.OFFSET_TARGET

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
            buffer = bytearray([0])
            curr_offset = YCable.OFFSET_ENABLE_LOOPBACK
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
        else:
            self.log_error("platform_chassis is not loaded, failed to disable loopback mode")
            return YCable.EEPROM_ERROR

        return result

    def get_loopback_mode(self, target):
        """
        This API returns the Loopback mode on the port which it has been configured to
        Target is an integer for selecting which end of the Y cable we want to run loopback on.
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                One of the following predefined constants, the target on which to disable the loopback:
                    EYE_PRBS_LOOPBACK_TARGET_LOCAL -> local side,
                    EYE_PRBS_LOOPBACK_TARGET_TOR_A -> TOR A
                    EYE_PRBS_LOOPBACK_TARGET_TOR_B -> TOR B
                    EYE_PRBS_LOOPBACK_TARGET_NIC -> NIC

        Returns:
            mode_value:
                One of the following predefined constants, the mode to be run for loopback:
                    LOOPBACK_MODE_NONE
                    LOOPBACK_MODE_NEAR_END
                    LOOPBACK_MODE_FAR_END
        """

        if self.platform_chassis is not None:
            buffer = bytearray([target])
            curr_offset = YCable.OFFSET_TARGET

            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return -1

            buffer = bytearray([0])
            curr_offset = YCable.OFFSET_SYNC_DEBUG_MODE
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return -1
            time_start = time.time()
            while(True):
                done = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                time_now = time.time()
                time_diff = time_now - time_start
                if done[0] == 1:
                    break
                elif time_diff >= YCable.GET_DEBUG_MODE_TIMEOUT_SECS:
                    return YCable.EEPROM_TIMEOUT_ERROR

            curr_offset = YCable.OFFSET_ENABLE_LOOPBACK
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)

            if result[0]:
                return YCableBase.LOOPBACK_MODE_NEAR_END
        else:
            self.log_error("platform_chassis is not loaded, failed to get loopback mode")
            return YCable.EEPROM_ERROR

        return YCableBase.LOOPBACK_MODE_NONE

    def get_ber_info(self, target):
        """
        This API returns the BER (Bit error rate) value for a specfic port.
        The target could be local side, TOR_A, TOR_B, NIC etc.
        The port on which this API is called for can be referred using self.port.

        Args:
            target:
                 One of the following predefined constants, the target on which to get the BER:
                     EYE_PRBS_LOOPBACK_TARGET_LOCAL -> local side,
                     EYE_PRBS_LOOPBACK_TARGET_TOR_A -> TOR A
                     EYE_PRBS_LOOPBACK_TARGET_TOR_B -> TOR B
                     EYE_PRBS_LOOPBACK_TARGET_NIC -> NIC
        Returns:
            a list, with BER values of lane 0 lane 1 lane 2 lane 3 with corresponding index
        """

        buffer = bytearray([target])
        curr_offset = YCable.OFFSET_TARGET

        ber_result = []

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
            buffer = bytearray([0])
            curr_offset = YCable.OFFSET_INITIATE_BER_MEASUREMENT
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
            time_start = time.time()
            while(True):
                done = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                time_now = time.time()
                time_diff = time_now - time_start
                if done[0] == 1:
                    break
                elif time_diff >= YCable.BER_TIMEOUT_SECS:
                    return YCable.EEPROM_TIMEOUT_ERROR

            idx = 0
            curr_offset = YCable.OFFSET_LANE_1_BER_RESULT
            for lane in range(YCable.MAX_NUM_LANES):
                msb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset+idx, 1)
                lsb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset+1+idx, 1)
                lane_result = msb_result[0] * math.pow(10, (lsb_result[0]-24))
                ber_result.append(lane_result)
                idx += 2
        else:
            self.log_error("platform_chassis is not loaded, failed to get ber info")
            return YCable.EEPROM_ERROR

        return ber_result

    def debug_dump_registers(self, option=None):
        """
        This API should dump all registers with meaningful values
        for the cable to be diagnosed for proper functioning.
        This means that for all the fields on relevant vendor-specific pages
        this API should dump the appropriate fields with parsed values
        which would help debug the Y-Cable

        Args:
            option:
                 a string, the option param can be a string which if passed can help a vendor utilize it
                 as an input param or a concatenation of params for a function which they can call internally.
                 This essentially helps if the vendor chooses to dump only some of the registers instead of all
                 the registers, and thus provides more granularity for debugging/printing.
                 For example, the option can serdes_lane0, in this case the vendor would just dump
                 registers related to serdes lane 0.


        Returns:
            a Dictionary:
                 with all the relevant key-value pairs for all the meaningful fields
                 which would help diagnose the cable for proper functioning
        """
        if self.platform_chassis is not None:
            api_ver = self.platform_chassis.get_sfp(self.port).read_eeprom(YCable.OFFSET_API_VERSION, 1)[0]

            result = {}
            result['vendor'] = self.get_vendor()
            result['pn'] = self.get_part_number()
            result['sn'] = self.get_serial_number()
            result['uart_stat'] = self.get_uart_stat()
            result['nic_temp'] = self.get_nic_temperature()
            result['nic_voltage'] = self.get_nic_voltage()
            result['fw_init_status'] = self.get_dsp_fw_init_stat()
            result['serdes_detect'] = self.get_dsp_link_detect()

            if api_ver >= 0x18:
                result['queue_info'] = self.queue_info()

            if '1MS' in result['pn']:
                lanes = [0,1,12,13,16,17]
            else:
                lanes = [0,1,2,3,12,13,14,15,20,21,22,23]

            for ln in list(lanes):
                data = self.get_serdes_params(ln)
                serdes = {}
                serdes['ch_est']    = struct.unpack_from('<f', data[  4 :  8])[0]
                serdes['of']        = struct.unpack_from('<H', data[  8 : 10])[0]
                serdes['hf']        = struct.unpack_from('<H', data[ 10 : 12])[0]
                serdes['ctle1']     = struct.unpack_from('<H', data[ 14 : 16])[0]
                serdes['ctle2']     = struct.unpack_from('<H', data[ 16 : 18])[0]
                serdes['delta']     = struct.unpack_from('<h', data[ 18 : 20])[0]
                serdes['eye']       = struct.unpack_from('<H', data[ 30 : 32])[0]
                serdes['ppm']       = struct.unpack_from('<h', data[ 40 : 42])[0]
                serdes['adp_cnt']   = struct.unpack_from('<H', data[ 56 : 58])[0]
                serdes['adp_done']  = struct.unpack_from('<B', data[ 58 : 59])[0]
                serdes['agc_g1']    = struct.unpack_from('<H', data[ 59 : 61])[0]
                serdes['agc_g2']    = struct.unpack_from('<H', data[ 61 : 63])[0]
                serdes['exit_code'] = struct.unpack_from('<H', data[112 :114])[0]
                serdes['pll_tx']    = struct.unpack_from('<H', data[ 42 : 44])[0]
                serdes['pll_rx']    = struct.unpack_from('<H', data[ 44 : 46])[0]
                serdes['f1']        = struct.unpack_from('<h', data[ 46 : 48])[0]
                serdes['f2']        = struct.unpack_from('<h', data[ 48 : 50])[0]
                serdes['f3']        = struct.unpack_from('<h', data[ 50 : 52])[0]
                serdes['temp']      = struct.unpack_from('<b', data[111 :112])[0]

                result['serde_lane_%d' % ln] = serdes
        else:
            self.log_error("platform_chassis is not loaded, failed to dump registers")
            return YCable.EEPROM_ERROR

        return result

    def queue_info(self):
        """
        This API should dump all the meaningful data from the eeprom which can
        help vendor debug the queue info for the UART stats in particular
        currently relevant to the MCU
        using this API the vendor could check how many txns are currently waiting to be processed,proceessed
        in the queue etc for debugging purposes
        Args:
             None
        Returns:
            a Dictionary:
                 with all the relevant key-value pairs for all the meaningful fields
                 for the queue inside the MCU firmware
                 which would help diagnose the cable for proper functioning
        """

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    result = {}
                    for option in range(2):
                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_QUEUE_INFO
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = option
                        status = self.send_vsc(vsc_req_form)
                        if status != YCable.MCU_EC_NO_ERROR:
                            self.log_error('Dump Uart statstics error (error code:0x%04X)' % (status))
                            return result

                        data = self.read_mmap(YCable.MIS_PAGE_FC, 128, 48)

                        queue = {}

                        offset = 0
                        cnt = {}
                        cnt['r_ptr']       = struct.unpack_from('<H', data[offset +  0: offset +  2])[0]
                        cnt['w_ptr']       = struct.unpack_from('<H', data[offset +  2: offset +  4])[0]
                        cnt['total_count'] = struct.unpack_from('<H', data[offset +  4: offset +  6])[0]
                        cnt['free_count']  = struct.unpack_from('<H', data[offset +  6: offset +  8])[0]
                        cnt['buff_addr']   = struct.unpack_from('<I', data[offset +  8: offset + 12])[0]
                        cnt['node_size']   = struct.unpack_from('<I', data[offset + 12: offset + 16])[0]
                        queue['VSC'] = cnt

                        offset = 16
                        cnt = {}
                        cnt['r_ptr']       = struct.unpack_from('<H', data[offset +  0: offset +  2])[0]
                        cnt['w_ptr']       = struct.unpack_from('<H', data[offset +  2: offset +  4])[0]
                        cnt['total_count'] = struct.unpack_from('<H', data[offset +  4: offset +  6])[0]
                        cnt['free_count']  = struct.unpack_from('<H', data[offset +  6: offset +  8])[0]
                        cnt['buff_addr']   = struct.unpack_from('<I', data[offset +  8: offset + 12])[0]
                        cnt['node_size']   = struct.unpack_from('<I', data[offset + 12: offset + 16])[0]
                        queue['UART1'] = cnt

                        offset = 32
                        cnt = {}
                        cnt['r_ptr']       = struct.unpack_from('<H', data[offset +  0: offset +  2])[0]
                        cnt['w_ptr']       = struct.unpack_from('<H', data[offset +  2: offset +  4])[0]
                        cnt['total_count'] = struct.unpack_from('<H', data[offset +  4: offset +  6])[0]
                        cnt['free_count']  = struct.unpack_from('<H', data[offset +  6: offset +  8])[0]
                        cnt['buff_addr']   = struct.unpack_from('<I', data[offset +  8: offset + 12])[0]
                        cnt['node_size']   = struct.unpack_from('<I', data[offset + 12: offset + 16])[0]
                        queue['UART2'] = cnt

                        if option == 0: result['Local']  = queue
                        else:           result['Remote'] = queue
                else:
                    self.log_error('acquire lock timeout, failed to get queue info')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get queue info")

        return result

    def reset_cause(self):
        """
        This API should return the reset cause for the NIC MCU.
        This should help ascertain whether a reset was caused by soft reboot or
        cable poweroff
        Args:
             None
        Returns:
            a string:
                 the string should be self explnatory as to what was the cause of reset
        """

        curr_offset = YCable.OFFSET_RESET_CAUSE

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            result = struct.unpack("<B", result)[0]
        else:
            self.log_error("platform_chassis is not loaded, failed to get operation time")
            return YCable.EEPROM_ERROR

        return result

    def operation_time(self):
        """
        This API should return the time since the cable is powered on from NIC MCU side
        This should be helpful in debugging purposes as to if/when the cable has been powered on
        Args:
             None
        Returns:
            a float:
                 the float should represent how much time the mux cable is alive/powered on
        """

        curr_offset = YCable.OFFSET_OPERATION_TIME

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 4)
            result = struct.unpack("<I", result)[0]
        else:
            self.log_error("platform_chassis is not loaded, failed to get operation time")
            return YCable.EEPROM_ERROR

        return result

    def mem_read(self, target, addr, length):
        """
        This API should return the memory contents of the cable which would be useful in debug for the
        y-cable
        Args:
             None
        Returns:
            a Dictionary:
                 with all the relevant key-value pairs for all the meaningful fields
                 for the memory inside the MCU firmware
                 which would help diagnose the cable for proper functioning
        """

        data = bytearray()

        if self.platform_chassis is not None:
            curr = 0
            while curr < length:
                if target == 0:
                    if (length - curr) > 512: size = 512
                    else:                     size = length - curr
                else:
                    size = 4

                with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                    if lock_status:
                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_MEM_READ
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = target
                        vsc_req_form[130] = (addr >>  0) & 0xFF
                        vsc_req_form[131] = (addr >>  8) & 0xFF
                        vsc_req_form[132] = (addr >> 16) & 0xFF
                        vsc_req_form[133] = (addr >> 24) & 0xFF
                        vsc_req_form[134] = (size >>  0) & 0xFF
                        vsc_req_form[135] = (size >>  8) & 0xFF
                        vsc_req_form[136] = (size >> 16) & 0xFF
                        vsc_req_form[137] = (size >> 24) & 0xFF
                        status = self.send_vsc(vsc_req_form)
                        if status != YCable.MCU_EC_NO_ERROR:
                            self.log_error('read MCU internal memory error error (error code:0x%04X)' % (status))
                            return YCable.EEPROM_ERROR

                        idx = 0
                        while idx < size:
                            if (size - idx) > 128:
                                data.extend(self.read_mmap(YCable.MIS_PAGE_FC + idx // 128, 128 + idx % 128, 128))
                                idx += 128
                            else:
                                data.extend(self.read_mmap(YCable.MIS_PAGE_FC + idx // 128, 128 + idx % 128, size - idx))
                                idx = size
                    else:
                        self.log_error('acquire lock timeout, failed to read memory')
                        return YCable.EEPROM_ERROR
            
                curr += size
                addr += size
        else:
            self.log_error("platform_chassis is not loaded, failed to read memory")

        return data

    def health_check(self):
        """
        This API checks the health of the cable, where it is healthy/unhealythy for RMA purposes/diagnostics.
        The port on which this API is called for can be referred using self.port.

        Args:
        Returns:
            a Boolean, True if the cable is healthy and False if it is not healthy.
        """

        if self.platform_chassis is not None:
            api_ver = self.platform_chassis.get_sfp(self.port).read_eeprom(YCable.OFFSET_API_VERSION, 1)[0]

            vendor = self.get_vendor()
            if vendor !=  "Credo           ":
                self.log_error("check cable health fail: unable to get correct vendor name:%s" % (vendor))
                return YCable.CABLE_UNHEALTHY

            uart_stat = self.get_uart_stat()
            if api_ver >= 0x18:
                if uart_stat['Local']['UART2']['RxErrorCnt'] > 100:
                    self.log_error("check cable health fail: uart rx error count overlimit:%d" % (uart_stat['local']['UART2']['RxErrorCnt']))
                    return YCable.CABLE_UNHEALTHY

            if ((uart_stat['Local']['UART1']['TxRetryCnt'] > 10000 and uart_stat['Local']['UART1']['TxAbortCnt'] > 5000) or 
                (uart_stat['Local']['UART2']['TxRetryCnt'] > 10000 and uart_stat['Local']['UART2']['TxAbortCnt'] > 5000) or 
                (uart_stat['Remote']['UART1']['TxRetryCnt'] > 10000 and uart_stat['Remote']['UART1']['TxAbortCnt'] > 5000) or 
                (uart_stat['Remote']['UART2']['TxRetryCnt'] > 10000 and uart_stat['Remote']['UART2']['TxAbortCnt'] > 5000)):

                self.log_error("check cable health fail: uart tx retry and abort count overlimit: LU1:%d %d LU2:%d %d RU1:%d %d RU2:%d %d" % 
                                            (uart_stat['Local']['UART1']['TxRetryCnt'],  uart_stat['Local']['UART1']['TxAbortCnt'],
                                             uart_stat['Local']['UART2']['TxRetryCnt'],  uart_stat['Local']['UART1']['TxAbortCnt'],
                                             uart_stat['Remote']['UART1']['TxRetryCnt'], uart_stat['Local']['UART1']['TxAbortCnt'],
                                             uart_stat['Remote']['UART2']['TxRetryCnt'], uart_stat['Local']['UART1']['TxAbortCnt']))

                return YCable.CABLE_UNHEALTHY
            
            if api_ver >= 0x19:
                status = self.get_fw_crc_status()
                if status[0] or status[1]:
                    self.log_error("check fw crc status error:%d %d" % (status[0], status[1]))
                    return YCable.CABLE_UNHEALTHY

            serdes_fw_tag = self.reg_read_atomic(0xB71A)
            if serdes_fw_tag != 0x6A6A:
                self.log_error("check cable health fail: serdes fw is not loaded correctly:%04X" % (serdes_fw_tag))
                return YCable.CABLE_UNHEALTHY
        else:
            self.log_error("platform_chassis is not loaded, failed to check cable health")
            return YCable.EEPROM_ERROR

        return YCable.CABLE_HEALTHY

    def get_dsp_link_detect(self):
        """
        This API returns rdy/sd of DSP.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
           a dictionary:
               a detailed format agreed upon by vendors
        """

        if self.platform_chassis is not None:
            result = {}
            curr_offset = YCable.OFFSET_NIC_SIGNAL_DETECTION
            result['sdNic']   = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 0, 1)[0]
            result['rdyNic']  = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 1, 1)[0]
            result['sdTorA']  = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 2, 1)[0]
            result['rdyTorA'] = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 3, 1)[0]
            result['sdTorB']  = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 4, 1)[0]
            result['rdyTorB'] = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 5, 1)[0]
        else:
            self.log_error("platform_chassis is not loaded, failed to get init. status of DSP firmware")

        return result

    def get_dsp_fw_init_stat(self):
        """
        This API returns init. status of DSP FW.
        The port on which this API is called for can be referred using self.port.

        Returns:
           a dictionary:
               a detailed format agreed upon by vendors
        """

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    result = {}

                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_DSP_LOADFW_STAT
                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('Get DSP firmware init status error (error code:0x%04X)' % (status))
                        return result

                    result['err_code'] = self.read_mmap(YCable.MIS_PAGE_VSC, 134)
                    result['err_stat'] = self.read_mmap(YCable.MIS_PAGE_VSC, 135)
                else:
                    self.log_error('acquire lock timeout, failed to get init status')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get init status")

        return result

    def get_uart_stat(self):
        """
        This API returns Uart statstics.
        The port on which this API is called for can be referred using self.port.

        Returns:
           a dictionary:
               a detailed format agreed upon by vendors
        """

        if self.platform_chassis is not None:
            result = {}

            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    for option in range(2):
                        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_UART_STAT
                        vsc_req_form[YCable.VSC_BYTE_OPTION] = option
                        status = self.send_vsc(vsc_req_form)
                        if status != YCable.MCU_EC_NO_ERROR:
                            self.log_error('Dump Uart statstics error (error code:0x%04X)' % (status))
                            return result

                        data = self.read_mmap(YCable.MIS_PAGE_FC, 128, 64)
                        ver  = self.read_mmap(YCable.MIS_PAGE_VSC, 130, 1)

                        uartPort = {}
                        cnt = {}
                        cnt['TxPktCnt']   = struct.unpack_from('<I', data[  0 :  4])[0] 
                        cnt['RxPktCnt']   = struct.unpack_from('<I', data[  4 :  8])[0] 
                        cnt['AckCnt']     = struct.unpack_from('<I', data[  8 : 12])[0] 
                        cnt['NackCnt']    = struct.unpack_from('<I', data[ 12 : 16])[0] 
                        cnt['TxRetryCnt'] = struct.unpack_from('<I', data[ 16 : 20])[0] 
                        cnt['TxAbortCnt'] = struct.unpack_from('<I', data[ 20 : 24])[0]

                        if ver == 1:
                            cnt['RxErrorCnt'] = struct.unpack_from('<I', data[ 48 : 52])[0]

                        uartPort['UART1'] = cnt

                        cnt = {}
                        cnt['TxPktCnt']   = struct.unpack_from('<I', data[ 24 : 28])[0] 
                        cnt['RxPktCnt']   = struct.unpack_from('<I', data[ 28 : 32])[0] 
                        cnt['AckCnt']     = struct.unpack_from('<I', data[ 32 : 36])[0] 
                        cnt['NackCnt']    = struct.unpack_from('<I', data[ 36 : 40])[0] 
                        cnt['TxRetryCnt'] = struct.unpack_from('<I', data[ 40 : 44])[0] 
                        cnt['TxAbortCnt'] = struct.unpack_from('<I', data[ 44 : 48])[0] 

                        if ver == 1:
                            cnt['RxErrorCnt'] = struct.unpack_from('<I', data[ 52 : 56])[0]

                        uartPort['UART2'] = cnt

                        if option == 0: result['Local']  = uartPort
                        else:           result['Remote'] = uartPort
                else:
                    self.log_error('acquire lock timeout, failed to get uart statistics')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get uart statistics")

        return result

    def get_serdes_params(self, lane):
        """
        This API returns Serdes parameters.
        The port on which this API is called for can be referred using self.port.

        Args:
            lane:
                id of lane

        Returns:
           a bytearray:
               raw data of serdes information
        """
        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:
                    ln = lane

                    result = {}
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_SERDES_INFO
                    vsc_req_form[YCable.VSC_BYTE_OPTION] = 0
                    vsc_req_form[YCable.VSC_BYTE_ADDR0]  = ln & 0xFF
                    vsc_req_form[YCable.VSC_BYTE_DATA0]  = 1
                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('Dump Serdes Info error (error code:0x%04X)' % (status))
                        return result

                    result = self.read_mmap(YCable.MIS_PAGE_FC, 128, 128)
                else:
                    self.log_error('acquire lock timeout, failed to get serdes param')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get serdes params")

        return result
    
    def get_fw_crc_status(self):
        """
        This API verifies all fw images's crc and return the result.
        The port on which this API is called for can be referred using self.port.

        Returns:
           a integer: return 0 if succeed, otherwise return non-zero value
        """

        result = {}

        if self.platform_chassis is not None:
            with self.rlock.acquire_timeout(RLocker.ACQUIRE_LOCK_TIMEOUT) as lock_status:
                if lock_status:                    
                    vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                    vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
                    vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_VERIFY_CRC
                    status = self.send_vsc(vsc_req_form)
                    if status != YCable.MCU_EC_NO_ERROR:
                        self.log_error('Get fw crc status error (error code:0x%04X)' % (status))
                        return status
                    
                    for idx in range(2):
                        base_addr = 128 + idx * 5
                        ret = self.read_mmap(YCable.MIS_PAGE_FC, base_addr, 5) 
                        result[idx] = ret[0]
                else:
                    self.log_error('acquire lock timeout, failed to get fw crc status')
                    return YCable.EEPROM_ERROR
        else:
            self.log_error("platform_chassis is not loaded, failed to get fw crc status")
            return YCable.EEPROM_ERROR

        return result
             

        