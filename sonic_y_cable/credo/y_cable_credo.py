"""
    y_cable_credo.py

    Implementation of Credo Y-Cable
"""

import math
import time
import struct
from ctypes import c_int8
from sonic_y_cable.y_cable_base import YCableBase

try:
    import sonic_platform.platform
except ImportError as e:
    pass


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
    OFFSET_CONFIGURE_PRBS_TYPE       = 768
    OFFSET_ENABLE_PRBS               = 769
    OFFSET_INITIATE_BER_MEASUREMENT  = 770
    OFFSET_LANE_1_BER_RESULT         = 771
    OFFSET_INITIATE_EYE_MEASUREMENT  = 784
    OFFSET_LANE_1_EYE_RESULT         = 785
    OFFSET_TARGET                    = 794
    OFFSET_ENABLE_LOOPBACK           = 793

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
    VSC_OPCODE_FWUPD      = 0x80
    VSC_OPCODE_EVENTLOG   = 0x81
    VSC_OPCODE_TCM_READ   = 0x82
    VSC_OPCODE_TCM_WRITE  = 0x83
    VSC_OPCODE_FW_CMD     = 0x84
    VSC_OPCODE_FW_CMD_EXT = 0x85
    VSC_OPCODE_REG_READ   = 0x86
    VSC_OPCODE_REG_WRITE  = 0x87

    BER_TIMEOUT_SECS = 1
    EYE_TIMEOUT_SECS = 1
    EXTEND_SWITCH_CNT_TIMEOUT_SECS = 1

    # error code of EEPROM
    EEPROM_READ_DATA_INVALID = -1
    EEPROM_ERROR = -1
    EEPROM_TIMEOUT_ERROR = -1

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

        try:
            self.platform_chassis = sonic_platform.platform.Platform().get_chassis()
            self.log_info("chassis loaded {}".format(self.platform_chassis))
        except Exception as e:
            self.log_warning("Failed to load chassis due to {}".format(repr(e)))

    def read_mmap(self, page, byte, len=1):
        """
        This API converts memory map page and offset to linar address, then returns eeprom values
        by calling read_eeprom()

        Args:
             page:
                 an Integer, page number of memorymap

             byte:
                 an Integer, byte address of the page

             len:
                 an Integer, length of the reading

        Returns:
            an Integer or bytearray, returns the value of the specified eeprom addres, returns 0xFF if it did not succeed
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
        This API converts memory map page and offset to linar address for calling write_eeprom()

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
            return False

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
            return False

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
            return YCableBase.TARGET_UNKNOWN

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
            self.log_error("Error: unknown status for checking which side regval = {} ".format(result))

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
                "platform_chassis is not loaded, failed to check Active Linked and routing TOR side")
            return YCableBase.TARGET_UNKNOWN

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

        self.log_error("Error: unknown status for mux direction regval = {} ".format(result))
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
            return YCableBase.TARGET_UNKNOWN

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

        self.log_error("Error: unknown status for active TOR regval = {} ".format(result))
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
            return YCableBase.TARGET_UNKNOWN

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
            return YCableBase.TARGET_UNKNOWN

        regval_read = struct.unpack(">B", result)

        if (regval_read[0] & 0x01):
            self.log_info("NIC link is up")
            return True
        elif ((regval_read[0] >> 2) & 0x01):
            self.log_info("TOR A link is up")
            return True
        elif ((regval_read[0] >> 1) & 0x01):
            self.log_info("TOR B link is up")
            return True
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
            self.log_error("platform_chassis is not loaded, failed to configure the PRBS type")
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
            return -1

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
            return -1

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
            self.log_error("platform_chassis is not loaded, failed to get part number")
            return -1

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

        if switch_count_type == YCableBase.SWITCH_COUNT_MANUAL:
            count = self.get_switch_count_tor_a(clear_on_read) + self.get_switch_count_tor_b(clear_on_read)
        elif switch_count_type == YCableBase.SWITCH_COUNT_AUTO:
            curr_offset = YCable.OFFSET_AUTO_SWITCH_COUNT

            if self.platform_chassis is not None:
                msb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                msb_result_1 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 1, 1)
                msb_result_2 = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + 2, 1)
                lsb_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset+3, 1)
                count = (msb_result[0] << 24 | msb_result_1[0] << 16 | msb_result_2[0] << 8 | lsb_result[0])
            else:
                self.log_error("platform_chassis is not loaded, failed to get manual switch count")
                return -1
        else:
            self.log_error("not a valid switch_count_type, failed to get switch count")
            return -1

        if clear_on_read:
            if switch_count_type == YCableBase.SWITCH_COUNT_AUTO:
                curr_offset = YCable.OFFSET_AUTO_SWITCH_COUNT
                buffer = bytearray([6])
                result = self.platform_chassis.get_sfp(
                    self.port).write_eeprom(curr_offset, 1, buffer)
                if result is False:
                    return result

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
        else:
            self.log_error("platform_chassis is not loaded, failed to get manual switch count")
            return -1

        if clear_on_read:
            buffer = bytearray([4])
            curr_offset = YCable.OFFSET_CLEAR_SWITCH_COUNT
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result

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
        else:
            self.log_error("platform_chassis is not loaded, failed to get manual switch count")
            return -1

        if clear_on_read:
            buffer = bytearray([5])
            curr_offset = YCable.OFFSET_CLEAR_SWITCH_COUNT
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result

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
                return -1
        elif switch_count_type == YCableBase.SWITCH_COUNT_AUTO:
            if target == YCableBase.TARGET_TOR_A:
                buffer = bytearray([2])
            elif target == YCableBase.TARGET_TOR_B:
                buffer = bytearray([3])
            else:
                self.log_error("not a valid target")
                return -1
        else:
            self.log_error("not a valid switch_count_type, failed to get switch count")
            return -1

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
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
                result = self.platform_chassis.get_sfp(
                    self.port).write_eeprom(curr_offset, 1, buffer)
                if result is False:
                    return result
        else:
            self.log_error("platform_chassis is not loaded, failed to get switch count target")
            return -1

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
            return -1

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
            return -1

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
        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_GET_INFO
        self.send_vsc(vsc_req_form)

        data = bytearray(YCable.FIRMWARE_INFO_PAYLOAD_SIZE)

        if self.platform_chassis is not None:
            for byte_idx in range(0, YCable.FIRMWARE_INFO_PAYLOAD_SIZE):
                curr_offset = 0xfc * 128 + 128 + byte_idx
                read_out = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                data[byte_idx] = read_out[0]
        else:
            self.log_error("platform_chassis is not loaded, failed to get NIC lanes active")
            return -1

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

        inFile = open(fwfile, 'rb')
        fwImage = bytearray(inFile.read())
        inFile.close()

        '''
        Firmware update start
        '''
        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_START
        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error(YCable.MCU_ERROR_CODE_STRING[status])
            return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

        '''
        Transfer firmwre image to local side MCU
        '''
        total_chunk = len(fwImage) // YCable.VSC_BUFF_SIZE
        chunk_idx = 0
        retry_count = 0
        while chunk_idx < total_chunk:
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
                    return YCableBase.FIRMWARE_DOWNLOAD_FAILURE
                retry_count += 1

        '''
        Complete the local side firmware transferring
        '''
        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_LOCAL_XFER_COMPLETE
        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error('Veriyf firmware binary error (error code:0x%04X)' % (status))
            return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

        '''
        transfer firmware image from local side MCU to the other two via UART
        '''
        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_UART_XFER
        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error('Firmware binary UART transfer error (error code:0x%04X)' % (status))
            return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

        vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
        vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
        vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_UART_XFER_STATUS
        status = self.send_vsc(vsc_req_form)
        if status != YCable.MCU_EC_NO_ERROR:
            self.log_error(
                'Get firmware binary UART transfer status error (error code:0x%04X)' % (status))
            return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

        busy = self.read_mmap(YCable.MIS_PAGE_FC, 128)
        self.read_mmap(YCable.MIS_PAGE_FC, 129)
        self.read_mmap(YCable.MIS_PAGE_FC, 130)
        self.read_mmap(YCable.MIS_PAGE_FC, 131)

        while busy != 0:
            vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
            vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
            vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_UART_XFER_STATUS
            status = self.send_vsc(vsc_req_form)
            if status != YCable.MCU_EC_NO_ERROR:
                self.log_error(
                    'Get firmware binary UART transfer status error (error code:0x%04X)' % (status))
                return YCableBase.FIRMWARE_DOWNLOAD_FAILURE

            time.sleep(0.2)
            busy = self.read_mmap(YCable.MIS_PAGE_FC, 128)
            self.read_mmap(YCable.MIS_PAGE_FC, 129)
            self.read_mmap(YCable.MIS_PAGE_FC, 130)
            self.read_mmap(YCable.MIS_PAGE_FC, 131)

        return YCableBase.FIRMWARE_DOWNLOAD_SUCCESS

    def activate_firmware(self, fwfile=None, hitless=False):
        """
        This routine should activate the downloaded firmware on all the
        components of the Y cable of the port for which this API is called..
        This API is meant to be used in conjunction with download_firmware API, and
        should be called once download_firmware API is succesful.
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
                 have the logic to retreive the firmware version from this file
                 which has to be activated on the components of the Y-Cable
                 this API has been called for.
                 If None is passed for fwfile, the cable should activate whatever
                 firmware is marked to be activated next.
                 If provided, it should retreive the firmware version(s) from this file, ensure
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
            side = 0x7

            vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
            vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_COMMIT
            vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
            vsc_req_form[YCable.VSC_BYTE_ADDR0] = side
            status = self.send_vsc(vsc_req_form)
            if status != YCable.MCU_EC_NO_ERROR:
                self.log_error(YCable.MCU_ERROR_CODE_STRING[status])
                return YCableBase.FIRMWARE_ACTIVATE_FAILURE

            vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
            vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_RUN
            vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
            vsc_req_form[YCable.VSC_BYTE_ADDR0] = side
            vsc_req_form[YCable.VSC_BYTE_ADDR1] = hitless
            status = self.send_vsc(vsc_req_form)
            time.sleep(5)
            if status != YCable.MCU_EC_NO_ERROR:
                self.log_error(YCable.MCU_ERROR_CODE_STRING[status])
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
                 have the logic to retreive the firmware version from this file
                 which should not be activated on the components of the Y-Cable
                 this API has been called for.
                 If None is passed for fwfile, the cable should rollback whatever
                 firmware is marked to be rollback next.
                 If provided, it should retreive the firmware version(s) from this file, ensure
                 that the firmware is rollbacked to a version which does not match to retreived version(s).
                 This is exactly the opposite behavior of this param to activate_firmware
        Returns:
            One of the following predefined constants:
                FIRMWARE_ROLLBACK_SUCCESS
                FIRMWARE_ROLLBACK_FAILURE
        """

        if self.platform_chassis is not None:
            if self.activate_firmware() == YCableBase.FIRMWARE_ACTIVATE_FAILURE:
                return YCableBase.FIRMWARE_ROLLBACK_FAILURE
        else:
            self.log_error("platform_chassis is not loaded, failed to activate firmware")
            return YCableBase.FIRMWARE_ROLLBACK_FAILURE

        return YCableBase.FIRMWARE_ROLLBACK_SUCCESS

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
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)
        else:
            self.log_error("platform_chassis is not loaded, failed to do a switch target")
            return False

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
            result = self.platform_chassis.get_sfp(
                self.port).read_eeprom(curr_offset, 1)
        else:
            self.log_error("platform_chassis is not loaded, failed to get the switch mode")
            return -1

        if result[0] == 1:
            return YCableBase.SWITCHING_MODE_AUTO
        else:
            return YCableBase.SWITCHING_MODE_MANUAL

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
            return -1

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
            return -1

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
            self.log_error("platform_chassis is not loaded, failed to get anlt")
            return False

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

            vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
            vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.FWUPD_OPTION_RUN
            vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_FWUPD
            vsc_req_form[YCable.VSC_BYTE_ADDR0] = (1 << target)
            vsc_req_form[YCable.VSC_BYTE_ADDR1] = 0
            status = self.send_vsc(vsc_req_form)

            if target  == YCableBase.TARGET_NIC:
                time.sleep(4)
            else:
                time.sleep(2)

            if status != YCable.MCU_EC_NO_ERROR:
                self.log_error("unable to reset the module")
                return False
        else:
            self.log_error("platform_chassis is not loaded, failed to reset")
            return False

        return True

    def create_port(self, speed, fec_mode_tor_a=YCableBase.FEC_MODE_NONE, fec_mode_tor_b=YCableBase.FEC_MODE_NONE,
                    fec_mode_nic=YCableBase.FEC_MODE_NONE, anlt_tor_a=False, anlt_tor_b=False, anlt_nic=False):
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

            fec_mode_tor_a:
                One of the following predefined constants, the actual FEC mode for the ToR A to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC

            fec_mode_tor_b:
                One of the following predefined constants, the actual FEC mode for the ToR B to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC

            fec_mode_nic:
                One of the following predefined constants, the actual FEC mode for the nic to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC

            anlt_tor_a:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled on ToR A
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled on ToR A

            anlt_tor_b:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled on ToR B
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled on ToR B

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
            mode |= (1 << 1) if anlt_tor_a else (0 << 1)
            mode |= (1 << 3) if fec_mode_nic == YCableBase.FEC_MODE_RS else (0 << 3)
            mode |= (1 << 4) if fec_mode_tor_a == YCableBase.FEC_MODE_RS else (0 << 4)

            curr_offset = YCable.OFFSET_NIC_MODE_CONFIGURATION
            buffer = bytearray([mode])
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
        else:
            self.log_error("platform_chassis is not loaded, failed to create port")
            return False

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
            return -1

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
            return False

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
            return -1

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
            return False

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
            return -1

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
                vsc_req_form = [None] * (YCable.VSC_CMD_ATTRIBUTE_LENGTH)
                vsc_req_form[YCable.VSC_BYTE_OPCODE] = YCable.VSC_OPCODE_EVENTLOG
                vsc_req_form[YCable.VSC_BYTE_OPTION] = YCable.EVENTLOG_OPTION_CLEAR
                self.send_vsc(vsc_req_form)

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

            while (True):
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
                    return None

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
        else:
            self.log_error("platform_chassis is not loaded, failed to get pcs statisics")
            return result

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
            self.log_error("platform_chassis is not loaded, failed to get pcs statisics")
            return pcs_stats

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

        raise NotImplementedError

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
            return -1

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
            return -1

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
            self.log_error("platform_chassis is not loaded, failed to restart anlt")
            return -1

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
            self.log_error("platform_chassis is not loaded, failed to get anlt stats")

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
            return -1

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
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
            buffer = bytearray([0])
            curr_offset = YCable.OFFSET_ENABLE_PRBS
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)

        else:
            self.log_error("platform_chassis is not loaded, failed to disable the PRBS mode")
            return -1

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
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
            buffer = bytearray([lane_mask])
            curr_offset = YCable.OFFSET_ENABLE_LOOPBACK
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)

        else:
            self.log_error("platform_chassis is not loaded, failed to enable the loopback mode")
            return -1

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
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)
            if result is False:
                return result
            buffer = bytearray([0])
            curr_offset = YCable.OFFSET_ENABLE_LOOPBACK
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)

        else:
            self.log_error("platform_chassis is not loaded, failed to disable the loopback mode")
            return -1

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
                    LOOPBACK_MODE_NEAR_END
                    LOOPBACK_MODE_FAR_END
        """

        raise NotImplementedError

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
            result = self.platform_chassis.get_sfp(
                self.port).write_eeprom(curr_offset, 1, buffer)
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
            return -1

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

        raise NotImplementedError
