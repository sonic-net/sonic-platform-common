#
# bcm_y_cable.py
#
# property
#   $Copyright: (c) 2021 Broadcom.
#   Broadcom Proprietary and Confidential. All rights reserved.
#
#   definitions for implementing Y cable access and configurations
#   API's for Y cable functionality in SONiC
#
from sonic_y_cable.y_cable_base import YCableBase

try:
    import time
    import struct
    import array
    import os
    import threading

    import sonic_platform.platform
    from ctypes import c_int16
    from datetime import datetime

    #from chassis import chassis
    import sonic_platform.platform
    from sonic_y_cable.y_cable_base import YCableBase
except ImportError as e:
    print("{}".format(e))
    # When build python3 xcvrd, it tries to do basic check which will import this file. However,
    # not all platform supports python3 API now, so it could cause an issue when importing
    # sonic_platform.platform. We skip the ImportError here. This is safe because:
    #   1. If any python package is not available, there will be exception when use it
    #   2. Vendors know their platform API version, they are responsible to use correct python
    #   version when importing this file.
    #pass

# strut definitions used in fw related functions
class cable_image_version_s(object):

    def __init__(self):
        self.image_version_minor = 0
        self.image_version_major = 0

class cable_image_info_s(object):

    def __init__(self):
        self.image_fw_version    = cable_image_version_s()
        self.image_api_version   = cable_image_version_s()
        self.image_crc32         = 0
        self.image_ptr           = array.array('H', [])
        self.image_size          = 0

class cable_bank_info_s(object):

    def __init__(self):
        self.image_fw_version    = cable_image_version_s()
        self.image_api_version   = cable_image_version_s()
        self.image_crc32         = 0

class cable_status_info_s():

    def __init__(self):
        self.current_bank = 0
        self.next_bank = 0
        self.bank1_info   = cable_bank_info_s()
        self.bank2_info   = cable_bank_info_s()

class cable_upgrade_info_s():

    def __init__(self):
        self.image_info  = cable_image_info_s()
        self.status_info = cable_status_info_s()
        self.destination = 0
        self.bank        = 0


class YCable(YCableBase):


    # TODO: findout how to use base class definitions
    FEC_MODE_NONE = 0
    PRBS_DIRECTION_BOTH = 0
    LOOPBACK_MODE_NEAR_END = 0


    SYSLOG_IDENTIFIER = "bcm_y_cable"
    BCM_API_VERSION = "0.1"
    CONSOLE_PRINT = False
    LOG_PID = False

    # Register absolute addresses
    QSFP28_LP_3_TX_RX_LOSS                        = 0x00000003		 
    QSFP28_LP_5_TX_RX_CDR_LOL                     = 0x00000005		 
    QSFP28_LP_8_LOS_LOL_SEC                       = 0x00000008		 
    QSFP28_LP_19_LINK_DOWN                        = 0x00000013		 
    QSFP28_LP_20_LINK_FAULT                       = 0x00000014		 
    QSFP28_LP_21_MESC_FAULT                       = 0x00000015		 
    QSFP28_LP_22_TEMP_MSB                         = 0x00000016
    QSFP_LP_30_VENDOR                             = 0x0000001e		 
    QSFP_LP_31_VENDOR                             = 0x0000001f
    QSFP_LP_32_LINK_FAULT_MASK                    = 0x00000020		 
    QSFP_LP_33_MESC_MASK                          = 0x00000021		 
    QSFP28_LP_100_TX_RX_LOS_MASK                  = 0x00000064		 
    QSFP28_LP_102_TX_RX_CDR_LOL_MASK              = 0x00000066		 
    QSFP28_LP_105_LOS_LOL_SEC_MASK                = 0x00000069		 
    QSFP28_LP_106_UP_DOWN_MASK                    = 0x0000006a		 
    QSFP28_UP0_148_VENDOR_NAME_0                  = 0x00000094		 
    QSFP28_UP0_168_PN_1                           = 0x000000a8		 
    QSFP28_UP0_224_SPECIFIC_1_RSV                 = 0x000000e0
    QSFP_VEN_FE_128_BRCM_CABLE_CMD                = 0x00007f80		 
    QSFP_VEN_FE_129_BRCM_CABLE_CTRL_CMD_STS       = 0x00007f81		 
    QSFP_VEN_FE_130_BRCM_DATA_LENGHT_LSB          = 0x00007f82		 
    QSFP28_VENFD_129_DIE_TEMP_MSB                 = 0x00007f01
    QSFP28_VENFD_130_DIE_VOLTAGE_LSB              = 0x00007f02
    QSFP28_VENFD_184_NIC_TORB_TORA_RESET          = 0x00007f38
    QSFP28_VENFD_216_LINK_STATUS                  = 0x00007f58
    QSFP28_RESET_SELF_OFFSET                      = 0x0000005D

    # temperature and voltage register offsets
    QSFP28_VENFD_128_DIE_TEMP_LSB                 = 0x00007f00
    QSFP28_VENFD_131_DIE_VOLTAGE_MSB              = 0x00007f03
    QSFP28_VENFD_134_TORA_TEMP_MSB                = 0x00007f06
    QSFP28_VENFD_135_TORA_TEMP_LSB                = 0x00007f07
    QSFP28_VENFD_138_TORB_TEMP_MSB                = 0x00007f0a
    QSFP28_VENFD_139_TORB_TEMP_LSB                = 0x00007f0b
    QSFP28_VENFD_142_NIC_TEMP_MSB                 = 0x00007f0e
    QSFP28_VENFD_143_NIC_TEMP_LSB                 = 0x00007f0f

    # User defined
    CMD_REQ_PARAM_START_OFFSET = 0x7F87
    CMD_RSP_PARAM_START_OFFSET = 0x7FB8
    
    MAX_REQ_PARAM_LEN = 0x30
    MAX_RSP_PARAM_LEN = 0x77
    
    # command IDs 
    CABLE_CMD_ID_PRBS_SET            = 0x01
    CABLE_CMD_ID_PRBS_CHK            = 0x03
    CABLE_CMD_ID_SET_LOOPBACK        = 0x04
    CABLE_CMD_ID_GET_LOOPBACK        = 0x05
    CABLE_CMD_ID_SET_TXFIR           = 0x06
    CABLE_CMD_ID_GET_TXFIR           = 0x07
    CABLE_CMD_ID_SET_ANLT            = 0x08
    CABLE_CMD_ID_GET_ANLT            = 0x09
    CABLE_CMD_ID_GET_ANLT_RESTART    = 0x0A
    CABLE_CMD_ID_GET_ANLT_GET_STATUS = 0x0B
    CABLE_CMD_ID_SET_POLARITY        = 0x0C
    CABLE_CMD_ID_GET_POLARITY        = 0x0D
    CABLE_CMD_ID_SET_MODE            = 0x0E
    CABLE_CMD_ID_GET_MODE            = 0x0F
    CABLE_CMD_ID_GET_SQUELCH         = 0x10
    CABLE_CMD_ID_SET_SQUELCH         = 0x11
    CABLE_CMD_ID_GET_HMUX_CONFIG     = 0x12
    CABLE_CMD_ID_SET_HMUX_CONFIG     = 0x13
    CABLE_CMD_ID_GET_HMUX_CONTEXT    = 0x14
    CABLE_CMD_ID_SET_HMUX_CONTEXT    = 0x15
    CABLE_CMD_ID_GET_HMUX_STATS      = 0x16
    CABLE_CMD_ID_READ_REG            = 0x17
    CABLE_CMD_ID_WRITE_REG           = 0x18
    CABLE_CMD_ID_ENABLE_PHY_CHIP     = 0x19
    CABLE_CMD_ID_DISABLE_PHY_CHIP    = 0x1A
    CABLE_CMD_ID_DUMP_PAGE           = 0x1B

    # Download commands
    FW_CMD_START        = 1
    FW_CMD_TRANSFER     = 2
    FW_CMD_COMPLETE     = 3
    FW_CMD_SWAP         = 4
    FW_CMD_ABORT        = 5
    FW_CMD_INFO         = 6
    FW_CMD_RESET        = 7
    
    FW_UP_SUCCESS       = 1
    FW_UP_IN_PROGRESS   = 2
    
    # destination values
    TOR_MCU             = 0x01
    TOR_MCU_SELF        = 0x01
    NIC_MCU	        = 0x02
    MUX_CHIP            = 0x03
    TOR_MCU_PEER        = 0x04

    # FW image address
    MCU_FW_IMG_INFO_ADDR    = 0x3E7F0
    MCU_FW_IMG_SIZE         = 0x3E800
    MUX_FW_IMG_INFO_ADDR    = 0x3FFE0
    MUX_FW_IMG_SIZE         = 0x40000
    FW_IMG_INFO_SIZE        = 12
    FW_UP_PACKET_SIZE       = 128

    QSFP_BRCM_FW_UPGRADE_DATA_PAGE_1    = 0x81
    QSFP_BRCM_FW_UPGRADE_DATA_PAGE_2    = 0x82
    QSFP_BRCM_FW_UPGRADE_DATA_START     = 0x80
    QSFP_BRCM_DIAGNOSTIC_PAGE           = 0x04
    QSFP_BRCM_DIAGNOSTIC_STATUS         = 0x81
    
    QSFP_BRCM_FW_UPGRADE_PACKET_SIZE    = 0x92
    QSFP_BRCM_FW_UPGRADE_CURRENT_BANK   = 0x80
    
    QSFP_BRCM_FW_UPGRADE_CTRL_CMD       = 0x80
    QSFP_BRCM_FW_UPGRADE_CMD_STS        = 0x81
    QSFP_BRCM_FW_UPGRADE_CTRL_STS       = 0x81
    
    QSFP_BRCM_FW_UPGRADE_PAGE           = 0x80
    QSFP_BRCM_FW_UPGRADE_HEADER_0_7     = 0x82
    QSFP_BRCM_FW_UPGRADE_HEADER_24_31   = 0x85

    # muxchip return codes
    RR_ERROR                        = -255      # Error Category
    RR_ERROR_SYSTEM_UNAVAILABLE     = -250      # System Unavailable Error    
    RR_SUCCESS                      = 0         # Success                     

    # PRBS polynomials
    CABLE_PRBS7  = 0 #  PRBS poly 7 
    CABLE_PRBS9  = 1 #  PRBS poly 9 
    CABLE_PRBS11 = 2 #  PRBS poly 11 
    CABLE_PRBS15 = 3 #  PRBS poly 15 
    CABLE_PRBS23 = 4 #  PRBS poly 23 
    CABLE_PRBS31 = 5 #  PRBS poly 31 
    CABLE_PRBS58 = 6 #  PRBS poly 58 

    # core ip's
    CORE_IP_ALL     = 0     #Core IP ALL
    CORE_IP_LW      = 2     #Core IP Line Wrapper 
    CORE_IP_CLIENT  = 3     #Core IP SerDes 
    CORE_IP_NIC     = 1
    CORE_IP_TOR     = 2
    CORE_IP_CENTRAL = 3
    
    # Error codes returned from y_cable functions
    ERROR_INVALID_INPUT           = -1
    ERROR_CMD_STS_CHECK_FAILED    = -2
    ERROR_WRITE_EEPROM_FAILED     = -3
    ERROR_CMD_PROCESSING_FAILED   = -4
    ERROR_MCU_NOT_RELEASED        = -5
    ERROR_MCU_BUSY                = -6
    ERROR_PLATFORM_NOT_LOADED     = -7
    ERROR_INVALID_PRBS_MODE       = -8
    ERROR_INVALID_TARGET          = -9
    ERROR_INVALID_DIRECTION       = -10
    ERROR_INVALID_POLARITY        = -11
    ERROR_CMD_EXEC_FAILED         = -12
    
    ERROR_FW_GET_STATUS_FAILED    = -15
    ERROR_NO_MATCHING_FW          = -16
    ERROR_RESET_FAILED            = -17
    ERROR_TOGGLE_FAILED           = -18
    ERROR_FW_ACTIVATE_FAILURE     = -19
    ERROR_FW_ROLLBACK_FAILURE     = -20
    
    WARNING_FW_ALREADY_ACTIVE     = -50
    WARNING_FW_ALREADY_ROLLEDBACK = -51
    
    EEPROM_READ_DATA_INVALID      = -100
    EEPROM_ERROR                  = -101
    API_FAIL                      = -102
    ERROR_PLATFORM_NOT_LOADED     = -1

    def __init__(self, port, logger):
        super(YCable, self).__init__(port, logger)

        # Global logger instance for helper functions and classes to log
        #self.helper_logger = logger.Logger(self.SYSLOG_IDENTIFIER)

        self.platform_chassis = None
        self.sfp              = None
        try:
            #self.platform_chassis = chassis()
            self.platform_chassis = sonic_platform.platform.Platform().get_chassis()
            self.sfp = self.platform_chassis.get_sfp(self.port)
        
            self.log_info("chassis loaded {}".format(self.platform_chassis))
            print("chassis loaded {}".format(self.platform_chassis))
        except Exception as e:
            self.log_warning("Failed to load chassis due to {}".format(repr(e)))

#############################################################################################
###                     Broadcom internal/debug/utility functions                         ###
#############################################################################################

    def enable_all_log(self, enable):
        if enable:
            self.CONSOLE_PRINT = True
            if self._logger is not None:
                self._logger.set_min_log_priority(9)
            print("Logging enabled...")
        else:
            self.CONSOLE_PRINT = False
            if self._logger is not None:
                self._logger.set_min_log_priority(7)
            print("Logging disabled...")
    
    def __get_pid_str(self):
        pid_str = "[{},{}] ".format(os.getpid(), threading.get_ident())
        return pid_str

    """def log_error(self, msg, also_print_to_console=False):
        if self.LOG_PID:
            msg = self.__get_pid_str() + msg
        also_print_to_console = True if self.CONSOLE_PRINT else also_print_to_console

        if self.helper_logger is not None:
            self.log_error(msg, also_print_to_console)
        else:
            if self.CONSOLE_PRINT:
                print(msg)

    def log_warning(self, msg, also_print_to_console=False):
        msg = self.__get_pid_str() + msg
        also_print_to_console = True if self.CONSOLE_PRINT else also_print_to_console

        if self.helper_logger is not None:
            self.log_warning(msg, also_print_to_console)
        else:
            if self.CONSOLE_PRINT:
                print(msg)

    def log_notice(self, msg, also_print_to_console=False):
        msg = self.__get_pid_str() + msg
        also_print_to_console = True if self.CONSOLE_PRINT else also_print_to_console

        if self.helper_logger is not None:
            self.log_notice(msg, also_print_to_console)
        else:
            if self.CONSOLE_PRINT:
                print(msg)

    def log_info(self, msg, also_print_to_console=False):
        if self.LOG_PID:
            msg = self.__get_pid_str() + msg
        also_print_to_console = True if self.CONSOLE_PRINT else also_print_to_console

        if self.helper_logger is not None:
            self.log_info(msg, also_print_to_console)
        else:
            if self.CONSOLE_PRINT:
                print(msg)

    def log_debug(self, msg, also_print_to_console=False):
        msg = self.__get_pid_str() + msg
        also_print_to_console = True if self.CONSOLE_PRINT else also_print_to_console

        if self.helper_logger is not None:
            self.log_debug(msg, also_print_to_console)
        else:
            if self.CONSOLE_PRINT:
                print(msg)
    """

    def __util_convert_to_phyinfo_details(self, target, lane_map):
        """
    
        This util API is internally used to simplify the calculation of core_ip, lane_mask
    
        """
    
        if target == self.TARGET_NIC:
            core_ip = self.CORE_IP_NIC
        else:
            core_ip = self.CORE_IP_TOR
    
        read_side = self.get_read_side()
        is_torA = False
    
        if read_side == 1:
            is_torA = True
    
        # if check is on TOR-B, make is_torA False
        if target == 2 and read_side == 1:
            is_torA = False
        # if check is on TOR-A and read side is TOR-B, make is_torA False
        elif target == 1 and read_side == 2:
            is_torA = True
    
        lane_mask = lane_map
    
        if core_ip == self.CORE_IP_NIC:
            lane_mask = lane_map
        else:
            if is_torA is False:
                lane_mask = ((lane_map << 4) & 0xF0) | ((lane_map >> 4) & 0x0F)
            else:
                lane_mask = lane_map
    
        if core_ip == self.CORE_IP_TOR:
            core_ip = self.CORE_IP_CLIENT
        elif core_ip == self.CORE_IP_NIC:
            core_ip = self.CORE_IP_LW
        else:
            core_ip = self.CORE_IP_ALL
    
        return core_ip, lane_mask
    
    def __cable_cmd_execute(self, command_id, cmd_hdr, cmd_req_body):
        """
            Internal function, sends command request to MCU and returns the response from MCU

            Args:
                command_id:
                    Command ID
                cmd_hdr
                    command header containing details of the command
                cmd_req_body
                    command request payload, to be sent to MCU

            Returns:
                an integer,  0 if transaction is successful
                          , -N for failure
                byte array, cmd_rsp_body containing command response
        """

        curr_offset = None
        cmd_rsp_body = None
        ret_val = 0

        if self.platform_chassis is not None:

            # read cable command and status offsets
            curr_offset = self.QSFP_VEN_FE_128_BRCM_CABLE_CMD
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 2)
            cmd_req = result[0]
            cmd_sts = result[1]

            # if command request and status both are 1,
            #    write 0 to cmd req and
            #    wait for status to go 0
            if ((cmd_req & 0x01) == 1) and ((cmd_sts & 0x01) == 1):
                cmd_req = 0
                curr_offset = self.QSFP_VEN_FE_128_BRCM_CABLE_CMD
                buffer1 = bytearray([cmd_req])
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1)
                if result is False:
                    return self.ERROR_WR_EEPROM_FAILED, None

                # poll command status for 100ms
                start = time.monotonic_ns()
                ms_elapsed = 0
                while (ms_elapsed < 100):
                    sta = 0
                    curr_offset = self.QSFP_VEN_FE_129_BRCM_CABLE_CTRL_CMD_STS
                    result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                    sta = result[0]

                    if (sta & 0x01) == 0x0:
                        break
                    ms_elapsed = (time.monotonic_ns()//1000000) - (start//1000000)
                else:
                    self.log_error("CMD_REQ/STS both are stuck at 1")
                    return self.ERROR_CMD_STS_CHECK_FAILED, None

            # check if any command is currently being executed
            if ((cmd_req & 0x01) == 0) and ((cmd_sts & 0x01) == 0):
                """
                    Combine the write of the cable command header
                    - write the request parameter len
                    - write the response parameter len
                    - write the BH lane mask (Client)
                    - write the LW lane mask (Line)
                    - write the core ip value
                """
                curr_offset = self.QSFP_VEN_FE_130_BRCM_DATA_LENGHT_LSB
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 5, cmd_hdr)
                if result is False:
                    self.log_error("write_eeprom() failed")
                    return self.ERROR_WRITE_EEPROM_FAILED, None

                # write request data
                wr_len = cmd_hdr[0]
                if wr_len > 0:
                    curr_offset = self.CMD_REQ_PARAM_START_OFFSET
                    result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, wr_len, cmd_req_body)
                    if result is False:
                        return self.ERROR_WRITE_EEPROM_FAILED, None

                # write the command request byte now
                cmd_req = 1
                cmd_req = (cmd_req | (command_id << 1))
                curr_offset = self.QSFP_VEN_FE_128_BRCM_CABLE_CMD
                buffer1 = bytearray([cmd_req])
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1)
                if result is False:
                    return self.ERROR_WRITE_EEPROM_FAILED, None
                rd = False

                start = time.monotonic_ns()
                ms_elapsed = 0
                while (ms_elapsed < 100):
                    sta = 0
                    curr_offset = self.QSFP_VEN_FE_129_BRCM_CABLE_CTRL_CMD_STS
                    result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                    sta = result[0]

                    if (sta & 0x7F) == 0x11 or (sta & 0x7F) == 0x31:
                        rd = True
                        break
                    ms_elapsed = (time.monotonic_ns()//1000000) - (start//1000000)
                else:
                    self.log_error("CMD_STS never read as 0x11 or 0x31")
                    ret_val = self.ERROR_CMD_PROCESSING_FAILED

                # read response data
                if rd is True:
                    rd_len = cmd_hdr[1]
                    if rd_len > 0:
                        curr_offset = self.CMD_RSP_PARAM_START_OFFSET
                        cmd_rsp_body = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, rd_len)

                # set the command request to idle state
                cmd_req = 0
                curr_offset = self.QSFP_VEN_FE_128_BRCM_CABLE_CMD
                buffer1 = bytearray([cmd_req])
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1)
                if result is False:
                    self.log_error("write eeprom failed for CMD_req")
                    return self.ERROR_WRITE_EEPROM_FAILED, None

                # wait  for MCU response to be pulled down
                start = time.monotonic_ns()
                ms_elapsed = 0
                while (ms_elapsed < 2000):
                    sta = 0
                    curr_offset = self.QSFP_VEN_FE_129_BRCM_CABLE_CTRL_CMD_STS
                    result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                    sta = result[0]

                    if (sta & 0x01) == 0x0:
                        break
                    ms_elapsed = (time.monotonic_ns()//1000000) - (start//1000000)
                else:
                    ret_val = self.ERROR_MCU_NOT_RELEASED

            else:
                ret_val = self.ERROR_MCU_BUSY

        else:
            self.log_error("platform_chassis is not loaded, failed to check if link is Active on TOR B side")
            return self.ERROR_PLATFORM_NOT_LOADED, None

        return ret_val, cmd_rsp_body


    def __validate_read_data(self, result, size, message):
        '''
        This API specifically used to validate the register read value
        '''
    
        if result is not None:
            if isinstance(result, bytearray):
                if len(result) != size:
                    LOG_MESSAGE_TEMPLATE = "Error: for checking mux_cable {}, eeprom read returned a size {} not equal to {} for port {}"
                    self.log_error(LOG_MESSAGE_TEMPLATE.format(message, len(result), size, self.port))
                    return self.EEPROM_READ_DATA_INVALID
            else:
                LOG_MESSAGE_TEMPLATE = "Error: for checking mux_cable {}, eeprom read returned an instance value of type {} which is not a bytearray for port {}"
                self.log_error(LOG_MESSAGE_TEMPLATE.format(message, type(result), self.port))
                return self.EEPROM_READ_DATA_INVALID
        else:
            LOG_MESSAGE_TEMPLATE = "Error: for checking mux_cable {}, eeprom read returned a None value for port {} which is not expected"
            self.log_error(LOG_MESSAGE_TEMPLATE.format(message, self.port))
            return self.EEPROM_READ_DATA_INVALID

    def rd_reg_ex(self, reg_addr, lane_map):
        """
        This API specifically used to read the register values
    
        Args:
            reg_addr:
                an hexadecomal,the register address which we intrested to read
            lane_map:
                register belong to lane_map to be read
    
        Returns:
        	an integer, on sucess returns the register values
                unsigned integer, register value
    
        """
        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)
    
        cmd_hdr[0] = 5
        cmd_hdr[1] = 4
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = 0
    
        if lane_map == 0 or lane_map is None:
            cmd_req_body[0] = 0
        else:
            # if lane_mask is for 4..7 lanes, then set port_id to 1. Else, port_id to 0
            if (lane_map & 0xF0):
                cmd_req_body[0] = 1
            else:
                cmd_req_body[0] = 0
    
        cmd_req_body[1] = (reg_addr & 0xFF)
        cmd_req_body[2] = ((reg_addr >> 8) & 0xFF)
        cmd_req_body[3] = ((reg_addr >>16) & 0xFF)
        cmd_req_body[4] = ((reg_addr >>24) & 0xFF)
    
        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_READ_REG, cmd_hdr, cmd_req_body)
        out = struct.unpack('I', cmd_rsp_body)[0]
    
        return ret_val, out
    
    def wr_reg_ex(self, reg_addr, reg_value, lane_map):
        """
        This API specifically used to write the register values
    
        Args:
            reg_addr:
                an hexadecomal,the register address where we want to write value
            reg_value:
                an hexadecomal,the register value which we want to write
            lane_map:
                Write register to be performed to given lane_map block
    
        Returns:
       	    a Boolean, true if the write register succeeded and false if it did not succeed.
    
        """
    
        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)
    
        cmd_hdr[0] = 9
        cmd_hdr[1] = 0
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = 0
    
        if lane_map == 0 or lane_map is None:
            cmd_req_body[0] = 0
        else:
            # if lane_mask is for 4..7 lanes, then set port_id to 1. Else, port_id to 0
            if (lane_map & 0xF0):
                cmd_req_body[0] = 1
            else:
                cmd_req_body[0] = 0
    
        cmd_req_body[1] = (reg_addr & 0xFF)
        cmd_req_body[2] = ((reg_addr >> 8) & 0xFF)
        cmd_req_body[3] = ((reg_addr >>16) & 0xFF)
        cmd_req_body[4] = ((reg_addr >>24) & 0xFF)
        cmd_req_body[5] = (reg_value & 0xFF)
        cmd_req_body[6] = ((reg_value >> 8) & 0xFF)
        cmd_req_body[7] = ((reg_value >>16) & 0xFF)
        cmd_req_body[8] = ((reg_value >>24) & 0xFF)
    
        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_WRITE_REG, cmd_hdr, cmd_req_body)
    
        return ret_val

    def util_print_ctx_debug(self):
        """
        Utility api to print context debug info
        """
        ret_code, cnt_val = self.rd_reg_ex(0x5200CCE0, 0x0)
        ret_code, tmp_start_ppm = self.rd_reg_ex(0x5200CCE4, 0x0)
        ret_code, tmp_stop_ppm = self.rd_reg_ex(0x5200CCE8, 0x0)
        ret_code, tmp_bh_ppm = self.rd_reg_ex(0x5200CCEC, 0x0)
    
        start_ppm = c_int16(tmp_start_ppm).value
        stop_ppm = c_int16(tmp_stop_ppm).value
        bh_ppm = c_int16(tmp_bh_ppm).value
        #print("cnt_val {} start_ppm {} stop_ppm {} bh_ppm {}".format(cnt_val, start_ppm, stop_ppm, bh_ppm))
    
        if (start_ppm & 0x1000):
            start_ppm = start_ppm | 0xFFFF0000
    
        if (bh_ppm & 0x1000):
            bh_ppm = bh_ppm | 0xFFFF0000
    
        if (stop_ppm & 0x1000):
            stop_ppm = stop_ppm | 0xFFFF0000
    
        start_ppm = (start_ppm * 10)/105
        stop_ppm = (stop_ppm * 10)/105
        bh_ppm = (bh_ppm * 10)/105
    
        ret_code, switch_time = self.rd_reg_ex(0x5200C7D4, 0x0)
    
        print("cnt_val     = {}".format(cnt_val))
        print("start_ppm   = {}".format(start_ppm))
        print("stop_ppm    = {}".format(stop_ppm))
        print("bh_ppm      = {}".format(bh_ppm))
        print("switch_time = {}".format(switch_time))
    
        return ret_code

    def cable_print_qsfp_page(self, interface, page_no):
        """
        This API prints QSFP registers for give interface/side and page number
    
        Args:
            interface:
                0 - TORA
                1 - TORB
                2 - NIC
            page_no:
                an Integer, indicates the page number
    
        Returns:
            an bool, True on success
                     False on failure
        """
    
        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)
    
        cmd_hdr[0] = 4
        cmd_hdr[1] = 16
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = 0
    
        cmd_req_body[0] = interface
        cmd_req_body[1] = page_no
    
        if (page_no):
            itr = 8
        else:
            itr = 16
    
        for i in range(0, itr):
            if (page_no):
                start_off = 0x80 + i*16
            else:
                start_off = i*16
    
            cmd_req_body[2] = start_off
            cmd_req_body[3] = 16
            ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_DUMP_PAGE, cmd_hdr, cmd_req_body)
    
            if ret_val == 0:
                print('0x{0:0{1}x}'.format((i*16), 2), end = " ")
                for j in range(0, 16):
                    print('0x{0:0{1}x}'.format(cmd_rsp_body[j], 2), end = " ")
                print("\n")
    
            else:
                self.log_error("QSFP_DUMP_PAGE failed! interface {} page {}".format(interface, page_no))
                return False
    
        return False

    def cable_get_mode(self):
        """
        This API specifically set the cable mode on the port user provides.
    
        Args:
            None
    
        Returns:
            integer , specifies one of the cable_mode (0 - CABLE_MODE_100G_FEC,
                      1 - CABLE_MODE_100G_PCS, 2 - CABLE_MODE_50G_FEC, 3 - CABLE_MODE_50G_PCS)
                      -1 if api fails
        """
        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)
    
        cmd_hdr[0] = 0
        cmd_hdr[1] = 1
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = 0
    
        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_MODE, cmd_hdr, cmd_req_body)
    
        if self.__validate_read_data(cmd_rsp_body, 1, "get cable mode") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR
    
        if ret_val == 0:
            regval_read = struct.unpack("<B", cmd_rsp_body)
            if regval_read[0] == 0:
                self.log_info("CABLE_MODE_100G_FEC")
                ret_mode = 0
            elif regval_read[0] == 1:
                self.log_info("CABLE_MODE_100G_PCS")
                ret_mode = 1
            elif regval_read[0] == 2:
                self.log_info("CABLE_MODE_50G_FEC")
                ret_mode = 2
            elif regval_read[0] == 3:
                self.log_info("CABLE_MODE_50G_PCS")
                ret_mode = 3
            else:
                self.log_info("Cable mode not set")
                ret_mode = -1
        else:
            ret_mode = -1
    
        return ret_mode

    ### Public APIs
    def get_api_version(self):
        """
        Returns Broadcom y_cable api version
        """
        return self.BCM_API_VERSION

    def get_part_number(self):
        """
        This API specifically returns the part number of the Y cable for a specfic port.
        Args:
            None

        Returns:
            a string, with part number
        """
    
        if self.sfp is not None:
            curr_offset = self.QSFP28_UP0_168_PN_1
            part_result = self.sfp.read_eeprom(curr_offset, 15)
        else:
            self.log_error("platform_chassis is not loaded, failed to get vendor name and pn_number")
            return ERROR_PLATFORM_NOT_LOADED
    
        if self.__validate_read_data(part_result, 15, "get  part_number") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR
    
        part_number = str(part_result.decode())
        self.log_info("Part number = {}".format(part_number))
    
        return part_number

    
    def get_vendor(self):
        """
        This API returns the vendor name of the Y cable for a specfic port.
        The port on which this API is called for can be referred using self.port.
        Args:
        Returns:
            a string, with vendor name
        """


        if self.platform_chassis is not None:
            curr_offset = self.QSFP28_UP0_148_VENDOR_NAME_0
            vendor_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 15)
        else:
            self.log_error("platform_chassis is not loaded, failed to get vendor name ")
            return -1

        if self.__validate_read_data(vendor_result, 15, "Vendor_name") == -1:
            return EEPROM_ERROR

        vendor_name = str(vendor_result.decode())
        self.log_info("vendor name = {}".format(vendor_name))

        return vendor_name


    def get_read_side(self):
        """
        This API checks which side of the Y cable the reads are actually getting performed
        from, either TOR A or TOR B or NIC and returns the value.
        The port on which this API is called for can be referred using self.port.

        Args:
            None

        Returns:
            One of the following predefined constants:
                TARGET_TOR_A, if reading the Y cable from TOR A side.
                TARGET_TOR_B, if reading the Y cable from TOR B side.
                TARGET_NIC, if reading the Y cable from NIC side.
                TARGET_UNKNOWN, if reading the Y cable API fails.
        """
    
        if self.platform_chassis is not None:
            curr_offset = self.QSFP28_UP0_224_SPECIFIC_1_RSV
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log_error("platform_chassis is not loaded, failed to check read side")
            return self.ERROR_PLATFORM_NOT_LOADED
    
        if self.__validate_read_data(result, 1, "read side") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR
    
        read_side = struct.unpack("<B", result)
    
        if read_side[0] & 0x1:
            self.log_info("Reading the Y cable from TOR A side")
            ret = self.TARGET_TOR_A
        elif read_side[0] & 0x2:
            self.log_info("Reading the Y cable from TOR B side")
            ret = self.TARGET_TOR_B
        elif read_side[0] & 0x4:
            self.log_info("Reading the Y cable from NIC side")
            ret = self.TARGET_NIC
        else:
            self.log_info("Target unknown")
            return self.TARGET_UNKNOWN

        return ret


    def get_mux_direction(self):
        """
        This API checks which side of the Y cable mux is currently point to
        and returns either TOR A or TOR B. Note that this API should return mux-direction
        regardless of whether the link is active and sending traffic or not.
        The port on which this API is called for can be referred using self.port.

        Args:
            None

        Returns:
            One of the following predefined constants:
                TARGET_TOR_A, if mux is pointing to TOR A side.
                TARGET_TOR_B, if mux is pointing to TOR B side.
                TARGET_UNKNOWN, if mux direction API fails.
        """

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 1
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = 0

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_HMUX_CONTEXT, cmd_hdr, cmd_req_body)

        if self.__validate_read_data(cmd_rsp_body, 1, "mux pointing side") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR

        if ret_val == 0:
            regval_read = struct.unpack("<B", cmd_rsp_body)
            if regval_read[0] == 1:
                self.log_info("Mux is pointing to TOR B")
                return self.TARGET_TOR_B
            else:
                self.log_info("Mux is pointing to TOR A")
                return self.TARGET_TOR_A
        else:
            self.log_info("Nothing linked for routing")
            return self.TARGET_UNKNOWN


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
            None

        Returns:
            a Boolean, True if the toggle succeeded and False if it did not succeed.
        """

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)

        cmd_hdr[0] = 1
        cmd_hdr[1] = 0
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = 0

        cmd_req_body[0] = 0

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_HMUX_CONTEXT, cmd_hdr, cmd_req_body)

        if ret_val == 0:
            self.log_info("Toggle mux to torA succeeded")
            ret = True
        else:
            self.log_info("Toggle mux to torA failed")
            ret = False

        return ret


    def toggle_mux_to_tor_b(self):
        """
        This API does a hard switch toggle of the Y cable's MUX regardless of link state to
        TOR B. This means if the Y cable is actively sending traffic, the "get_active_linked_tor_side"
        API will now return Tor B. It also implies that if the link is actively sending traffic on this port,
        Y cable. MUX will start forwarding packets from TOR B to NIC, and drop packets from TOR A to NIC
        regardless of previous forwarding state.
        The port on which this API is called for can be referred using self.port.

        Args:
            None

        Returns:
            a Boolean, True if the toggle succeeded and False if it did not succeed.
        """

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)

        cmd_hdr[0] = 1
        cmd_hdr[1] = 0
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = 0

        cmd_req_body[0] = 1

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_HMUX_CONTEXT, cmd_hdr, cmd_req_body)

        if ret_val == 0:
            self.log_info("Toggle mux to torB succeeded")
            ret = True
        else:
            self.log_info("Toggle mux to torB failed")
            ret = False

        return ret


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

        if self.platform_chassis is not None:
            curr_offset = self.QSFP28_VENFD_216_LINK_STATUS
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log_error("platform_chassis is not loaded, failed to check link is active for TOR A side")
            return self.ERROR_PLATFORM_NOT_LOADED

        if self.__validate_read_data(result, 1, "link is active for TOR A side") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR

        regval_read = struct.unpack("<B", result)
        
        if target == self.TARGET_TOR_A: 
            if regval_read[0] & 0x1:
                self.log_info("TOR A link is up")
                return True
            else:
                self.log_info("TOR A link is down")
                return False
        
        elif target == self.TARGET_TOR_B: 
            if regval_read[0] & 0x2:
                self.log_info("TOR B link is up")
                return True
            else:
                self.log_info("TOR B link is down")
                return False

        elif target == self.TARGET_NIC: 
            if regval_read[0] & 0x4:
                self.log_info("NIC link is up")
                return True
            else:
                self.log_info("NIC link is down")
                return False
        else:
            self.log_info("target is unkown")
            return self.TARGET_UNKNOWN


    def get_active_linked_tor_side(self):
        """
        This API checks which side of the Y cable is actively linked and sending traffic
        and returns either TOR A or TOR B.
        The port on which this API is called for can be referred using self.port.
        This is different from get_mux_direction in a sense it also implies the link on the side
        where mux is pointing to must be active and sending traffic, whereas get_mux_direction
        just tells where the mux is pointing to.

        Args:
            None

        Returns:
            One of the following predefined constants:
                TARGET_TOR_A, if TOR A is actively linked and sending traffic.
                TARGET_TOR_B, if TOR B is actively linked and sending traffic.
                TARGET_UNKNOWN, if checking which side is linked and sending traffic API fails.
        """

        ret_val = self.get_mux_direction()
        if ret_val == self.TARGET_TOR_A:
            if self.is_link_active(self.TARGET_TOR_A) == True:
                self.log_info("TOR A standby linked and actively routing")
                ret_val = self.TARGET_TOR_A
            else:
                self.log_info("Nothing linked for routing")
                ret_val = self.TARGET_UNKNOWN
           
        elif ret_val == self.TARGET_TOR_B :
            if self.is_link_active(self.TARGET_TOR_B) == True:
                self.log_info("TOR B standby linked and actively routing")
                ret_val = self.TARGET_TOR_B
            else:
                self.log_info("Nothing linked for routing")
                ret_val = self.TARGET_UNKNOWN

        return ret_val
    
    def util_get_switch_count(self, clear_on_read):
        """
        utility function returns all switchover counters in a list

        """

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)

        byte_list = []

        cmd_hdr[0] = 1
        cmd_hdr[1] = 12
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL

        cmd_req_body[0] = clear_on_read

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_HMUX_STATS, cmd_hdr, cmd_req_body)
        if ret_val == 0:
            count_list = []
            ind = 0
            for i in range(0, 6):
                byte_list = []
                for j in range(0, 2):
                    byte_list.append(cmd_rsp_body[ind + j])
                byte_array = bytearray(byte_list)
                count_list.append(struct.unpack("<H", byte_array)[0])
                ind += 2

            self.log_info("\nDebug: counter tables")
            self.log_info("to_tora_from_readside_tora_manual_cnt = {} ".format(count_list[0]))
            self.log_info("to_torb_from_readside_tora_manual_cnt = {} ".format(count_list[1]))
            self.log_info("to_tora_from_readside_torb_manual_cnt = {} ".format(count_list[2]))
            self.log_info("to_torb_from_readside_torb_manual_cnt = {} ".format(count_list[3]))
            self.log_info("to_tora_as_cnt                        = {} ".format(count_list[4]))
            self.log_info("to_torb_as_cnt                        = {} ".format(count_list[5]))
            self.log_info("\n")

            return count_list

        else:
            return None
 

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
        count_value = None
        count_list = self.util_get_switch_count(clear_on_read)
        if count_list is None:
            self.log_error("Get switch count is failed ")
            return None
        else:
            to_tora_from_tora_manual_cnt = count_list[0]
            to_torb_from_tora_manual_cnt = count_list[1]
            to_tora_from_torb_manual_cnt = count_list[2]
            to_torb_from_torb_manual_cnt = count_list[3]
            to_tora_as_cnt = count_list[4]
            to_torb_as_cnt = count_list[5]

            if (switch_count_type == self.SWITCH_COUNT_MANUAL):
                count_value = to_tora_from_tora_manual_cnt + to_torb_from_tora_manual_cnt + \
                              to_tora_from_torb_manual_cnt + to_torb_from_torb_manual_cnt
                self.log_info("Total manual count is : {}".format(count_value))
            elif (switch_count_type == self.SWITCH_COUNT_AUTO):
                count_value = to_tora_as_cnt + to_torb_as_cnt
                self.log_info("Total auto count is : {}".format(count_value))

            return count_value


    def get_switch_count_tor_a(self, clear_on_read):
        """
        This API returns the switch count to change the Active TOR which has
        been done manually by the user initiated from ToR A
        This is essentially all the successful switches initiated from ToR A. Toggles which were
        initiated to toggle from ToR A and did not succed do not count.
        The port on which this API is called for can be referred using self.port.

        Args:
            clear_on_read:
                a boolean, True if the count has to be reset after read to zero
                         , False if the count is not to be reset after read

        Returns:
            an integer, the number of times the Y-cable has been switched from ToR A
        """

        count_value = None
        count_list = self.util_get_switch_count(clear_on_read)
        if count_list is None:
            self.log_error("Get switch count is failed ")
        else:
            to_tora_from_tora_manual_cnt = count_list[0]
            to_torb_from_tora_manual_cnt = count_list[1]
            count_value = to_tora_from_tora_manual_cnt + to_torb_from_tora_manual_cnt

        return count_value

    
    def get_switch_count_tor_b(self, clear_on_read):
        """
        This API returns the switch count to change the Active TOR which has
        been done manually by the user initiated from ToR B
        This is essentially all the successful switches initiated from ToR B. Toggles which were
        initiated to toggle from ToR B and did not succed do not count.
        The port on which this API is called for can be referred using self.port.

        Args:
            clear_on_read:
                a boolean, True if the count has to be reset after read to zero
                         , False if the count is not to be reset after read

        Returns:
            an integer, the number of times the Y-cable has been switched from ToR B
        """

        count_value = None
        count_list = self.util_get_switch_count(clear_on_read)
        if count_list is None:
            self.log_error("Get switch count is failed ")
        else:
            to_tora_from_torb_manual_cnt = count_list[2]
            to_torb_from_torb_manual_cnt = count_list[3]

            count_value = to_tora_from_torb_manual_cnt + to_torb_from_torb_manual_cnt

        return count_value


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
        
        count_value = None
        count_list = self.util_get_switch_count( clear_on_read)
        if count_list is None:
            self.log_error("Get switch count is failed ")
        else:
            to_tora_from_tora_manual_cnt = count_list[0]
            to_torb_from_tora_manual_cnt = count_list[1]
            to_tora_from_torb_manual_cnt = count_list[2]
            to_torb_from_torb_manual_cnt = count_list[3]
            to_tora_as_cnt = count_list[4]
            to_torb_as_cnt = count_list[5]

            if target == self.TARGET_TOR_A:
                if (switch_count_type == self.SWITCH_COUNT_MANUAL):
                    count_value = to_tora_from_tora_manual_cnt + to_tora_from_torb_manual_cnt
                elif (switch_count_type == self.SWITCH_COUNT_AUTO):
                    count_value = to_tora_as_cnt
                else:
                    count_value = None

            if target == self.TARGET_TOR_B:
                if (switch_count_type == self.SWITCH_COUNT_MANUAL):
                    count_value = to_torb_from_tora_manual_cnt + to_torb_from_torb_manual_cnt
                elif (switch_count_type == self.SWITCH_COUNT_AUTO):
                    count_value = to_torb_as_cnt
                else:
                    count_value = None

        return count_value


    def __util_read_eeprom(self, curr_offset, rd_len, message):
        """
        This API is internally used for read and validate
        """
        result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, rd_len)

        if self.__validate_read_data(result, rd_len, message) == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR

        return result

    def __handle_error_abort(self, upgrade_info, error):
        """
        Internal API used to abort in case of error in FW related functions
        """
        self.log_error("ERROR : {}, Sending abort".format(error))
        self.__cable_fw_mcu_abort(self.port, upgrade_info)
        time.sleep(0.001)

    def __handle_error(self, error):
        """
        Internal API to handle error in FW related APIs
        """
        dat = bytearray(30)
        status = 0

        self.log_error("ERROR : {} FAILED".format(error))

        if self.platform_chassis is not None:
            # set the command request to idle state
            dat[0] = 0x00
            curr_offset = (self.QSFP_BRCM_FW_UPGRADE_PAGE * 128) + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat)
            if result is False:
                return self.ERROR_WRITE_EEPROM_FAILED

            # wait for mcu response to be pulled down
            for i in range(30):
                curr_offset = (self.QSFP_BRCM_FW_UPGRADE_PAGE * 128) + self.QSFP_BRCM_FW_UPGRADE_CMD_STS
                status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                if (status[0] & 0x01) == 0:
                    return
                time.sleep(0.001)

        else:
            self.log_error("platform_chassis is not loaded, failed to handle_error")
            return self.ERROR_PLATFORM_NOT_LOADED


    def __cable_fw_mcu_abort(self, upgrade_info):
        """
        Internal API used to abort the execution of FW related function in case of error
        """
        ret_val = self.RR_ERROR
        dat = bytearray(30)
        status = 0
        req_status = False
        i = 0

        # SEE which MCU it is: Assuming constant pages have been set for each MCU
        curr_offset = (0 * 128) + 0xE0
        result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        dat[0] = result[0]

        if dat[0] == 0x02:
            self.log_info("Current side: TOR B")
        elif dat[0] == 0x01:
            self.log_info("Current side TOR A")
        elif dat[0] == 0x04:
            self.log_info("Current side NIC")
        else:
            self.log_info("Current side UNKNOWN")

        # Make sure TOR to NIC MCU communication is alive
        self.log_info("Make sure TOR to NIC MCU communication is alive ")
        if (upgrade_info.destination == self.NIC_MCU) and ((dat[0] == 0x02) or (dat[0] == 0x01)):
            # Since we are running from TOR side, make sure no flush is on going
            for i in range(3000):
                curr_offset = (self.QSFP_BRCM_DIAGNOSTIC_PAGE * 128) + self.QSFP_BRCM_DIAGNOSTIC_STATUS
                status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                if status[0] == 0:
                    break
                time.sleep(0.001)
            if status[0]:
                self.log_error("Unable to communicate with NIC MCU")
                return self.RR_ERROR


        # Make sure to clear command first else can have unforseen consequences
        curr_offset = (self.QSFP_BRCM_FW_UPGRADE_PAGE*128)
        dat[0] = 0x00
        self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat)

        # Send destination
        dat[0] = upgrade_info.destination
        self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset + self.QSFP_BRCM_FW_UPGRADE_HEADER_24_31, 1, dat)

        # Send Abort request
        dat[0] = (self.FW_CMD_ABORT << 1) | 1
        self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat)

        # Check response status
        for i in range(100):
            status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset + self.QSFP_BRCM_FW_UPGRADE_CMD_STS, 1)

            if (status[0] & 0x01) == 0:
                req_status = True
                ret_val = self.RR_SUCCESS

                # Set the command request to idle state
                dat[0] = 0x00
                self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat)
                break
            time.sleep(0.001)

        if not req_status:
            self.log_error("Abort timeout. No response from MCU")
            self.__handle_error(17)
            return ret_val

        return ret_val



    def __cable_fw_get_status(self, upgrade_info):
        """
        This function used internally to get the status information of existing firmware.
        The status information has the following details,
            1. current bank
            2. bank1 firmware image version minor
            3. bank1 firmware image version major
            4. bank1 API image version minor
            5. bank1 API image version major
            6. bank1 image crc32
            7. bank2 firmware image version minor
            8. bank2 firmware image version major
            9. bank2 API image version minor
            10. bank2 API image version major
            11. bank2 image crc32

        upgrade_info:
            an object of type cable_upgrade_type_s, must have upgrade_info.destination
            set to MUX_CHIP or NIC_MCU or TOR_MCU

        Returns:
            upgrade_info with firmware versions and crc
            Integer, -1 if api failes

        """
        ret_val = self.RR_ERROR
        dat = bytearray(30)
        status = 0
        info_stat = 0
        req_status = False
        i = 0

        if self.platform_chassis is not None:
            # SEE which MCU it is: Assuming constant pages have been set for each MCU
            curr_offset = (0*128) + 0xE0
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            dat[0] = result[0]

            if dat[0] == 0x02:
                 self.log_info("Current side: TOR B")
            elif dat[0] == 0x01:
                self.log_info("Current side TOR A")
            elif dat[0] == 0x04:
                self.log_info("Current side NIC")
            else:
                self.log_info("Current side UNKNOWN")

            # Make sure TOR to NIC MCU communication is alive
            self.log_info("cable_fw_get_status : .................................................... ")
            self.log_info("Make sure TOR to NIC MCU communication is alive ")
            if (upgrade_info.destination == self.NIC_MCU) and ((dat[0] == 0x02) or (dat[0] == 0x01)):

                for i in range(3000):
                    curr_offset = (self.QSFP_BRCM_DIAGNOSTIC_PAGE * 128) + self.QSFP_BRCM_DIAGNOSTIC_STATUS
                    status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                    if status[0] == 0:
                        break
                    time.sleep(0.001)

                if status[0]:
                    self.log_error("Unable to communicate with NIC MCU")
                    return self.RR_ERROR

            # read cable command and status offsets
            self.log_info("read cable command and status offsets ")
            result = self.__util_read_eeprom(((self.QSFP_BRCM_FW_UPGRADE_PAGE * 128) + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD), 2, "cable_fw_get_status")
            if result != self.EEPROM_READ_DATA_INVALID:
                dat[0] = result[0]
                dat[1] = result[1]

            if ((dat[0] & 0x01) != 0) or ((dat[1] & 0x01) != 0):
                self.log_info("MCU not in the right state. Sending abort")
                self.__cable_fw_mcu_abort(upgrade_info)
                time.sleep(0.001)
                result = self.__util_read_eeprom(((self.QSFP_BRCM_FW_UPGRADE_PAGE * 128) + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD), 2, "cable_fw_upgrade")
                dat[0] = result[0]
                dat[1] = result[1]

            # check if any command is currently being executed
            self.log_info("check if any command is currently being executed ")
            if ((dat[0] & 0x01) == 0) and ((dat[1] & 0x01) == 0):
                # Send destination
                self.log_info("send destination ")
                dat[0] = upgrade_info.destination
                current_offset = (self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_HEADER_24_31
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(current_offset, 1, dat)
                if result is False:
                    return self.ERROR_WRITE_EEPROM_FAILED

                # Send command status request
                self.log_info("send command status request ")
                dat[0] = (self.FW_CMD_INFO << 1) | 1
                current_offset = (self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(current_offset, 1, dat)
                if result is False:
                    return self.ERROR_WRITE_EEPROM_FAILED

                #Delay reading status as this can block during swap
                #time.sleep(0.2)
                req_status = False
                for i in range(0, 100):
                    status = self.__util_read_eeprom(((self.QSFP_BRCM_FW_UPGRADE_PAGE * 128) + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_get_status")
                    if status[0] & 0x01:
                        if ((status[0] & 0xFC) == (self.FW_UP_SUCCESS << 2)) or ((status[0] & 0xFC) == (self.FW_UP_IN_PROGRESS << 2)):

                            # SUCCESS, read the status info
                            dat = self.__util_read_eeprom(((self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_1 * 128) + self.QSFP_BRCM_FW_UPGRADE_CURRENT_BANK), 26, "cable_fw_get_status")

                            # Current bank
                            upgrade_info.status_info.current_bank = dat[0]
                            upgrade_info.status_info.next_bank = dat[25]

                            # Bank 1 minor fw version
                            upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor = (dat[2] << 8) | dat[1]

                            # Bank 1 major fw version
                            upgrade_info.status_info.bank1_info.image_fw_version.image_version_major = (dat[4] << 8) | dat[3]

                            # Bank 1 minor API version
                            upgrade_info.status_info.bank1_info.image_api_version.image_version_minor = (dat[6] << 8) | dat[5]

                            # Bank 1 major API version
                            upgrade_info.status_info.bank1_info.image_api_version.image_version_major = (dat[8] << 8) | dat[7]

                            # Bank 1 CRC32
                            upgrade_info.status_info.bank1_info.image_crc32 = (dat[12] << 24) | (dat[11] << 16) | (dat[10] << 8) | dat[9]
                            # Bank 2 minor fw version
                            upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor = (dat[14] << 8) | dat[13]

                            # Bank 2 major fw version
                            upgrade_info.status_info.bank2_info.image_fw_version.image_version_major = (dat[16] << 8) | dat[15]

                            # Bank 2 minor API version
                            upgrade_info.status_info.bank2_info.image_api_version.image_version_minor = (dat[18] << 8) | dat[17]

                            # Bank 2 major API version
                            upgrade_info.status_info.bank2_info.image_api_version.image_version_major = (dat[20] << 8) | dat[19]

                            # Bank2 CRC32
                            upgrade_info.status_info.bank2_info.image_crc32 = (dat[24] << 24) | (dat[23] << 16) | (dat[22] << 8) | dat[21]

                            req_status = True

                            if (status[0] & 0xFC) == (self.FW_UP_IN_PROGRESS << 2):
                                info_stat = 1

                            break
                        else:
                            self.__handle_error_abort(self.port, upgrade_info, 1)
                            return ret_val
                    time.sleep(0.01)

                if req_status:
                    req_status = False
                    # set the command request to idle state
                    self.log_info("set the command request to idle state ")
                    dat[0] = 0x00
                    curr_offset = (self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD
                    result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat)
                    if result is False:
                        return self.ERROR_WRITE_EEPROM_FAILED

                    # Delay reading status as this can block during swap
                    #time.sleep(0.3)

                    # wait for mcu response to be pulled down
                    self.log_info("wait for mcu response to be pulled down  ")
                    for i in range(100):
                        status = self.platform_chassis.get_sfp(self.port).read_eeprom(((self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1)
                        if (status[0] & 0x01) == 0:
                            req_status = True
                            ret_val = self.RR_SUCCESS
                            break

                        time.sleep(0.001)

                    if not req_status:
                        # Timeout, how to handle?
                        self.log_info("timeout handle error abort  ")
                        self.__handle_error_abort(self.port, upgrade_info, 2)
                        return ret_val
                else:
                    # Error
                    self.log_info("Error handle error abort  ")
                    self.__handle_error_abort(self.port, upgrade_info, 17)
                    return ret_val
            else:
                self.log_error("MCU not in the right state")

            if info_stat:
                ret_val = self.RR_ERROR_SYSTEM_UNAVAILABLE
                return ret_val

        else:
            self.log_error("platform_chassis is not loaded, failed to read " + "fw_get_status")
            return self.ERROR_PLATFORM_NOT_LOADED

        return ret_val


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

        #dat = bytearray(30)
        dat = [1000]
        dat1 = [1000]
        i = 0
        result = {}
        upgrade_info = cable_upgrade_info_s()

        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC):
            return self.RR_ERROR

        if self.platform_chassis is not None:

            read_side = self.get_read_side()
            if (target == self.TARGET_TOR_A):
                target = self.TOR_MCU_SELF if (read_side == 1) else self.TOR_MCU_PEER
            elif (target == self.TARGET_TOR_B):
                target = self.TOR_MCU_SELF if (read_side == 2) else self.TOR_MCU_PEER
            else:
                target = self.NIC_MCU
            
            upgrade_info.destination = target

            self.log_info("read_side {} target {}".format(read_side, target))

            ret_val = self.__cable_fw_get_status(upgrade_info)
            if ret_val != self.RR_ERROR:
                if upgrade_info.status_info.current_bank == 1:
                    # Active version
                    dat.append(format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major, 'X') + "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                    # Inactive version
                    dat.append(format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major, 'X') + "." +  format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                else:
                    dat.append(format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major, 'X') + "." +  format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                    dat.append(format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major, 'X') + "." +  format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))

                if upgrade_info.status_info.next_bank == 1:
                    dat.append(format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major, 'X') + "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                else:
                    dat.append(format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major, 'X') + "." +  format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))

            else:
                self.log_error("Error getting version for {}".format("TOR MCU SELF" if target == TOR_MCU_SELF else "TOR MCU PEER" if target == TOR_MCU_PEER else "NIC MCU"))
                return self.RR_ERROR

            if target == self.NIC_MCU:
                upgrade_info.destination = self.MUX_CHIP
                ret_val = self.__cable_fw_get_status(upgrade_info)
                if ret_val != self.RR_ERROR:
                    if upgrade_info.status_info.current_bank == 1:
                        # Active version
                        # Active version
                        dat1.append('.' + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major, 'X') + "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                        dat1.append('.' + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major, 'X') + "." + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                        # Inactive version
                    else:
                        dat1.append('.' + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major, 'X') + "." + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                        dat1.append('.' + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major, 'X') + "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                    if upgrade_info.status_info.next_bank == 1:
                        # Active version
                        dat1.append('.' + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major, 'X') + "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                    else:
                        dat1.append('.' + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major, 'X') + "." + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                else:
                    self.log.error("Error getting version for MUX CHIP")
                    return self.RR_ERROR

                for i in range(0, 4):
                    dat[i] = dat[i] + dat1[i]
            
            if target == self.TOR_MCU_SELF:
                result["version self active   : "] = dat[1]
                result["version self inactive : "] = dat[2]
                result["version self next     : "] = dat[3]
            elif target == self.TOR_MCU_PEER:
                result["version peer active   : "] = dat[1]
                result["version peer inactive : "] = dat[2]
                result["version peer next     : "] = dat[3]
            elif target == self.NIC_MCU:
                result["version nic active    : "] = dat[1]
                result["version nic inactive  : "] = dat[2]
                result["version nic next      : "] = dat[3]
            
            return result

    def get_local_temperature(self):
        """
        This API returns local ToR temperature of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:
            None

        Returns:
            an Integer, the temperature of the local MCU
        """

        if self.platform_chassis is not None:
            curr_offset = self.QSFP28_VENFD_129_DIE_TEMP_MSB
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            temperature = result[0]
        else:
            self.log_error("platform_chassis is not loaded, failed to check read side")
            temperature = None

        return temperature

    def get_local_voltage(self):
        """
        This API returns local ToR voltage of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:
            None

        Returns:
            a float, the voltage of the local MCU
        """

        if self.platform_chassis is not None:
            curr_offset = self.QSFP28_VENFD_130_DIE_VOLTAGE_LSB
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 2)
            voltage = struct.unpack("h", result)[0]
        else:
            self.log_error("platform_chassis is not loaded, failed to check read side")
            voltage = None

        return voltage


    def get_nic_voltage(self):
        """
        This API returns nic voltage of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.
        Args:
        Returns:
            a float, the voltage of the NIC MCU
        """

        return None

    def get_nic_temperature(self):
        """
        This API returns nic temperature of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.
        Args:
        Returns:
            an Integer, the temperature of the NIC MCU
        """

        return None


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

        return None
    
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

        return None


    def get_target_cursor_values(self, lane, target):
        """
        This API returns the cursor equalization parameters for a target(NIC, TOR_A, TOR_B).
        This includes pre one, pre two , main, post one, post two , post three cursor values
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
            a list, with  pre one, pre two , main, post one, post two , post three cursor values in the order
        """

        # validate lane number
        if lane < 1 or lane > 4:
            self.log_error("Invalid lane = {} valid lane is 1 to 4".format(lane))
            return self.ERROR_INVALID_INPUT, None

        lane -= 1 # internally lane starts from 0 
        lane_mask = 1 << lane
        ret_val = self.__util_convert_to_phyinfo_details(target, lane_mask)
        print(ret_val)
        core_ip = ret_val[0]
        lane_mask = ret_val[1]
        self.log_info("lane_mask = {} core_ip {} target {}".format(hex(lane_mask), core_ip, target))

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 14
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        #cmd_rsp_body = []
        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_TXFIR, cmd_hdr, cmd_req_body)

        if ret_val == 0:
            txfir = []
            ind = 0
            for i in range(0, 7):
                byte_list = []
                for j in range(0, 2):
                    byte_list.append(cmd_rsp_body[ind + j])
                byte_array = bytearray(byte_list)
                txfir.append(struct.unpack("h", byte_array)[0])
                ind += 2

        self.log_info("lane {} : pre1  = {}".format(lane,txfir[0]))
        self.log_info("lane {} : pre2  = {}".format(lane,txfir[1]))
        self.log_info("lane {} : main  = {}".format(lane,txfir[2]))
        self.log_info("lane {} : post1 = {}".format(lane,txfir[3]))
        self.log_info("lane {} : post2 = {}".format(lane,txfir[4]))
        self.log_info("lane {} : post3 = {}".format(lane,txfir[5]))
        self.log_info("lane {} : taps  = {}".format(lane,txfir[6]))

        return ret_val, txfir

    def set_target_cursor_values(self, lane, cursor_values, target):
        """
        This API sets the cursor equalization parameters for a target(NIC, TOR_A, TOR_B).
        This includes pre one, pre two , main, post one, post two etc. cursor values
        The port on which this API is called for can be referred using self.port.
        Args:
            lane:
                 an Integer, the lane on which to collect the cursor values
                             1 -> lane 1,
                             2 -> lane 2
                             3 -> lane 3
                             4 -> lane 4
            cursor_values:
                a list, with  pre one, pre two , main, post one, post two cursor, post three etc. values in the order
            target:
                One of the following predefined constants, the actual target to get the cursor values on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
            Returns:
            a boolean, True if cursor values setting is successful
                     , False if cursor values setting is not successful
        """

        return None


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

        return None

    def activate_firmware(self, fwfile=None):
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
        Returns:
            One of the following predefined constants:
                FIRMWARE_ACTIVATE_SUCCESS
                FIRMWARE_ACTIVATE_FAILURE
        """

        return  None

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

        return None


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

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)

        cmd_hdr[0] = 4
        cmd_hdr[1] = 0
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL
        cmd_req_body[0] = mode
        '''
        if mode == 0:
            cmd_req_body[0] = self.SWITCHING_MODE_MANUAL
        if mode == 1:
            cmd_req_body[0] = self.SWITCHING_MODE_AUTO
        '''
        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_HMUX_CONFIG, cmd_hdr, cmd_req_body)

        if ret_val == 0:
            return True
        else:
            return False



    def get_switching_mode(self):
        """
        This API returns which type of switching mode the cable is set to auto/manual
        The port on which this API is called for can be referred using self.port.

        Args:
            None
        Returns:
            One of the following predefined constants:
               SWITCHING_MODE_AUTO if auto switch is enabled.
               SWITCHING_MODE_MANUAL if manual switch is enabled.
        """

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        #cmd_rsp_body = bytearray(self.MAX_RSP_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 4
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_HMUX_CONFIG, cmd_hdr, cmd_req_body)
        if ret_val == 0:
            if cmd_rsp_body[0] & 1:
                self.log_info("Auto switch enabled")
                return self.SWITCHING_MODE_AUTO
            else:
                self.log_info("Manual switch enabled")
                return self.SWITCHING_MODE_MANUAL
        else:
            return None

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
            curr_offset = (0xFD * 128) + 217
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log_error("platform_chassis is not loaded, failed to check active link status")
            return self.ERROR_PLATFORM_NOT_LOADED

        if self.__validate_read_data(result, 1, "get_alive_status") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR

        regval_read = struct.unpack("<B", result)

        self.log_info("TOR-A active link is {}".format("up" if (regval_read[0] & 0x1 == 0) else "down"))
        self.log_info("TOR-B active link is {}".format("up" if (regval_read[0] & 0x2 == 0) else "down"))
        self.log_info("NIC   active link is {}".format("up" if (regval_read[0] & 0x4 == 0) else "down"))
        
        if regval_read[0] & 0x7 == 0:
            return True

        return False

    def reset_self(self):
        """
        Resets the Local TOR MCU  and this make bank swap in effect
        Args:
            None
        Returns:
            an integer, True - on success
                        False - on Failure
        """
    
        self.log_info("reset self...")
        status = bytearray(self.MAX_REQ_PARAM_LEN)
    
        rval = 0
        if self.platform_chassis is not None:
            curr_offset = self.QSFP28_RESET_SELF_OFFSET
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            rval = result[0]
            rval |= 0x80
    
            status[0] = rval
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, status)
            if result is False:
                self.log_error("write to QSFP28_VENFD_184_NIC_TORB_TORA_RESET failed.")
                return False
            time.sleep(3)
    
            # for next one second, keep checking the register to see if it becomes 0
            for i in range(30):
                result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                rval = result[0]
    
                if (rval & 0x80) == 0x00:
                    ret_code = True
                    break
    
                time.sleep(0.1) #100ms
            else:
                self.log_error("TORB_TORA_RESET never become zero.  rval: {} ".format(rval))
                ret_code = False
    
        else:
            self.log_error("platform_chassis is not loaded, failed to check read side")
            ret_code = False
    
        return ret_code

    def reset_peer(self):
        """
        Resets the Remote TOR MCU  and this make bank swap in effect
        Args:
            None

        Returns:
            an integer,0 - on success
                       -1 - on Failure
        """

        read_side = self.get_read_side()

        if read_side == self.TARGET_TOR_A:
            return self.reset(self.TARGET_TOR_B)
        elif read_side == self.TARGET_TOR_B:
            return self.reset(self.TARGET_TOR_A)
        else:
            self.log_error("get_read_side failed")
            return False 

    
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

        status = bytearray(self.MAX_REQ_PARAM_LEN)

        if target == self.TARGET_TOR_A:
            status[0] = 0x1
        elif target == self.TARGET_TOR_B:
            status[0] = 0x2
        elif target == self.TARGET_NIC:
            status[0] = 0x4
        else:
            self.log_error("Invalid target")
            return False

        # if read side is matching target, invoke reset_self()
        read_side = self.get_read_side()
        if read_side == target:
            return self.reset_self()

        if self.platform_chassis is not None:

            curr_offset = self.QSFP28_VENFD_184_NIC_TORB_TORA_RESET
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, status)
            if result is False:
                self.log_error("write to QSFP28_VENFD_184_NIC_TORB_TORA_RESET failed.")
                return False
            time.sleep(3)

            self.log_info("reset value to write.  rval: {} ".format(status[0]))
            # for next one second, keep checking the register to see if it becomes 0
            for i in range(30):
                rval = 0
                result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                rval = result[0]

                if (rval & status[0]) == 0x00:
                    ret_code = True
                    break

                time.sleep(0.1) #100ms
            else:
                self.log_error("TORB_TORA_RESET never become zero.  rval: {} ".format(rval))
                ret_code = False

        else:
            self.log_error("platform_chassis is not loaded, failed to check read side")
            ret_code = False

        return ret_code


    def create_port(self, speed, fec_mode_tor_a=FEC_MODE_NONE, fec_mode_tor_b=FEC_MODE_NONE ,fec_mode_nic=FEC_MODE_NONE, anlt_tor_a=False, anlt_tor_b= False, anlt_nic=False):
        """
        This API sets the mode of the cable/port for corresponding lane/fec etc. configuration as specified.
        The speed specifies which mode is supposed to be set 50G, 100G etc
        the anlt specifies if auto-negotiation + link training (AN/LT) has to be enabled
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
                One of the following predefined constants, the actual fec mode for the tor A to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC
            fec_mode_tor_b:
                One of the following predefined constants, the actual fec mode for the tor B to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC
            fec_mode_nic:
                One of the following predefined constants, the actual fec mode for the nic to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC
            anlt_tor_a:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled on tor A
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled on tor A
            anlt_tor_b:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled on tor B
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled on tor B
            anlt_nic:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled on nic
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled on nic
        Returns:
            a boolean, True if the port is configured
                     , False if the port is not configured
        """

        return None


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
        return None

    def set_fec_mode(self, fec_mode, target):
        """
        This API gets the fec mode of the cable for which it is set to.
        The port on which this API is called for can be referred using self.port.
        Args:
            fec_mode:
                One of the following predefined constants, the actual fec mode for the port to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC
            target:
                One of the following predefined constants, the actual target to set the fec mode on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
            a boolean, True if the fec mode is configured
                     , False if the fec mode is not configured
        """

        return None

    def get_fec_mode(self, target):
        """
        This API gets the fec mode of the cable which it is set to.
        The port on which this API is called for can be referred using self.port.
        Args:
            target:
                One of the following predefined constants, the actual target to fec mode on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
            fec_mode:
                One of the following predefined constants, the actual fec mode for the port to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC
        """

        return None

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

        return None

    def get_anlt(self, target):
        """
        This API gets the mode of the cable for corresponding lane configuration.
        The port on which this API is called for can be referred using self.port.
        Args:
            target:
                One of the following predefined constants, the actual target to get the anlt on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
            a boolean, True if auto-negotiation + link training (AN/LT) is enabled
                     , False if auto-negotiation + link training (AN/LT) is not enabled
        """

        return None

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

        return None
    
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

        return None

    def get_fec_stats(self, target):
        """
        This API returns the fec statistics of the cable
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

        return None
    
    
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

        return None

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

        return None


    def restart_anlt(self):
        """
        This API restarts auto-negotiation + link training (AN/LT) mode
        The port on which this API is called for can be referred using self.port.
        Args:
            target:
                One of the following predefined constants, the actual target to restart anlt on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
            a boolean, True if restart is successful
                     , False if the restart is not successful
        """

        return None

    def get_anlt_stats(self, target):
        """
        This API returns auto-negotiation + link training (AN/LT) mode statistics
        The port on which this API is called for can be referred using self.port.
        Args:
            target:
                One of the following predefined constants, the actual target to get anlt stats on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A -> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
           a dictionary:
               a detailed format agreed upon by vendors
        """

        return None

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

        return None

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

        return None
    
    
    def enable_prbs_mode(self, target, mode_value, lane_mask, direction=PRBS_DIRECTION_BOTH):
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
                 for example 3 -> 0b'0011 , means running on lane0 and lane1
            direction:
                One of the following predefined constants, the direction to run the PRBS:
                    PRBS_DIRECTION_BOTH
                    PRBS_DIRECTION_GENERATOR
                    PRBS_DIRECTION_CHECKER
        Returns:
            a boolean, True if the enable is successful
                     , False if the enable failed
        """

        return None

    def disable_prbs_mode(self, target, direction=PRBS_DIRECTION_BOTH):
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

        return None


    #def enable_loopback_mode(self, target, mode=NEAR_END_LOOPBACK, lane_mask):
    def enable_loopback_mode(self, target, lane_mask, mode=LOOPBACK_MODE_NEAR_END):
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
            mode_value:
                One of the following predefined constants, the mode to be run for loopback:
                    LOOPBACK_MODE_NEAR_END
                    LOOPBACK_MODE_FAR_END
            lane_mask:
                 an Integer, representing the lane_mask to be run loopback on
                 0bit for lane 0, 1bit for lane1 and so on.
                 for example 3 -> 0b'0011 , means running on lane0 and lane1
        Returns:
            a boolean, True if the enable is successful
                     , False if the enable failed
        """

        return None


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

        return None

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

        return None


    def debug_dump_registers(self):
        """
        This API should dump all registers with meaningful values
        for the cable to be diagnosed for proper functioning.
        This means that for all the fields on relevant vendor-specific pages
        this API should dump the appropriate fields with parsed values
        which would help debug the Y-Cable
        Args:
        Returns:
            a Dictionary:
                 with all the relevant key-value pairs for all the meaningful fields
                 which would help diagnose the cable for proper functioning
        """

        print("\nPHY CHIP DEBUG info dump")
        # print out the port FSM of the active context
        ret_code, reg_val = self.rd_reg_ex(0x5200C820, 0x0)
        print("active port status = {}".format(hex(reg_val)))
        
        # print out the port FSM of the inactive context
        ret_code, reg_val = self.rd_reg_ex(0x5200C894, 0x0)
        print("standby port status = {}".format(hex(reg_val)))
        
        # clear the stickies
        ret_code = self.wr_reg_ex(0x5200C81C, 0xFFFF, 0x0)
        if ret_code is False:
            print("ERROR: Writing to 0x5200C81C Failed!")
        
        ret_code = self.wr_reg_ex(0x5200C81C, 0x0, 0x0)
        if ret_code is False:
            print("ERROR: Writing to 0x5200C81C Failed!")
        
        # print out the interrupt register
        ret_code, reg_val = self.rd_reg_ex(0x5200C8B4, 0x0)
        print("GP_REG_45_int register = {}".format(hex(reg_val)))
        
        # print out the ipc registers CW=>LW
        print("CW=>LW IPC registers:")
        for i in range(0,4):
            reg_addr = 0x5200CC20 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            print("Lane {} = {} (cmd ret_code: {})".format(i, hex(reg_val), ret_code))
        
        # print out the ipc registers LW=>CW 
        print("LW=>CW IPC registers")
        for i in range(0,4):
            reg_addr = 0x5200CC40 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            print("Lane {} = {} (cmd ret_code: {})".format(i, hex(reg_val), ret_code))
        
        # print out the ipc registers CW=>BH
        print("CW=>BH IPC registers")
        for i in range(0,8):
            reg_addr = 0x5200CC60 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            print("{} Lane {} = {} (cmd ret_code: {})".format( "TORB" if i> 3 else "TORA", i, hex(reg_val), ret_code))
        
        # print out the ipc registers BH=>CW
        print("BH=>CW IPC registers")
        for i in range(0,8):
            reg_addr = 0x5200CCA0 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            print("{} Lane {} = {} (cmd ret_code: {})".format( "TORB" if i> 3 else "TORA", i, hex(reg_val), ret_code))
        
        # print out the PCS receive irq registers 
        mode = self.cable_get_mode()
        print("pcs receive irq status registers")
        print("lanes 0 to 3")
        for i in range(0,3):
            reg_addr = 0x52007E80 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            if ret_code is False:
                print("\n")

            ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
            if ret_code is False:
                print("ERROR: wr_reg_ex failed for {}".format(hex(reg_addr)))

            if(i==0):
                print("{} {} = {}".format( "DESK_ALIGN_LOSS:", hex(reg_addr), hex(reg_val)))
            elif i==1:
                print("{} {} = {}".format(  "DSKW0:", hex(reg_addr), hex(reg_val)))
            elif i==2:
                print("{} {} = {}".format( "DSKW1:", hex(reg_addr), hex(reg_val)))
        
        for i in range(0,4):
            reg_addr = 0x52007E8C + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            if ret_code is False:
                print("\n")

            reg_val = reg_val & 0x7FFF#dont clear bit 15
            ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
            if ret_code is False:
                print("ERROR: wr_reg_ex failed for {}".format(hex(reg_addr)))

            print("Lane {} {} = {}".format( i, hex(reg_addr), hex(reg_val)))
        if(mode == 0 or mode == 2):#for fec modes
            print("FEC irq status")
            for i in range(0,4):
                reg_addr = 0x52007ED0 + i * 4
                ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
                if ret_code is False:
                    print("\n")

                ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
                if ret_code is False:
                    print("ERROR: wr_reg_ex failed for {}".format(hex(reg_addr)))

                if(i==0):
                    print("{} {} = {}".format( "DEC_AM_LOCK_UNLOCK:", hex(reg_addr), hex(reg_val)))
                elif i==1:
                    print("{} {} = {}".format( "DEC_DGBOX:", hex(reg_addr), hex(reg_val)))
                elif i==2:
                    print("{} {} = {}".format( "DEC_IGBOX:", hex(reg_addr), hex(reg_val)))
                elif i==3:
                    print("{} {} = {}".format( "XDEC_ERR:", hex(reg_addr), hex(reg_val)))
            for i in range(0,2):
                reg_addr = 0x52007E60 + i * 4
                ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
                if ret_code is False:
                    print("\n")

                ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
                if ret_code is False:
                    print("ERROR: wr_reg_ex failed for {}".format(hex(reg_addr)))

                if(i==0):
                    print("{} {} = {}".format( "ENC_GBOX:", hex(reg_addr), hex(reg_val)))
                elif i==1:
                    print("{} {} = {}".format( "ENC_PFIFO:", hex(reg_addr), hex(reg_val)))
        print("lanes 4 to 7")
        for i in range(0,3):
            reg_addr = 0x52017E80 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            if ret_code is False:
                print("\n")

            ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
            if ret_code is False:
                print("ERROR: wr_reg_ex failed for {}".format(hex(reg_addr)))

            if(i==0):
                print("{} {} = {}".format( "DESK_ALIGN_LOSS:", hex(reg_addr), hex(reg_val)))
            elif i==1:
                print("{} {} = {}".format(  "DSKW0:", hex(reg_addr), hex(reg_val)))
            elif i==2:
                print("{} {} = {}".format( "DSKW1:", hex(reg_addr), hex(reg_val)))
        
        for i in range(0,4):
            reg_addr = 0x52017E8C + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            if ret_code is False:
                print("\n")

            reg_val = reg_val & 0x7FFF#dont clear bit 15
            ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
            if ret_code is False:
                print("ERROR: wr_reg_ex failed for {}".format(hex(reg_addr)))

            print("Lane {} {} = {}".format( i, hex(reg_addr), hex(reg_val)))
        if(mode == 0 or mode == 2):#for fec modes
            print("FEC irq status")
            for i in range(0,4):
                reg_addr = 0x52017ED0 + i * 4
                ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
                if ret_code is False:
                    print("\n")

                ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
                if ret_code is False:
                    print("ERROR: wr_reg_ex failed for {}".format(hex(reg_addr)))

                if(i==0):
                    print("{} {} = {}".format( "DEC_AM_LOCK_UNLOCK:", hex(reg_addr), hex(reg_val)))
                elif i==1:
                    print("{} {} = {}".format( "DEC_DGBOX:", hex(reg_addr), hex(reg_val)))
                elif i==2:
                    print("{} {} = {}".format( "DEC_IGBOX:", hex(reg_addr), hex(reg_val)))
                elif i==3:
                    print("{} {} = {}".format( "XDEC_ERR:", hex(reg_addr), hex(reg_val)))
        print("\n")
        
        return True


