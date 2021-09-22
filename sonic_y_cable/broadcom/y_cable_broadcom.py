#
# bcm_cable_api.py
#
# property
#   $Copyright: (c) 2021 Broadcom.
#   Broadcom Proprietary and Confidential. All rights reserved.
#
#   definitions for implementing Y cable access and configurations
#   API's for Y cable functionality in SONiC
#
#from y_cable_base import YCableBase
from sonic_y_cable.y_cable_base import YCableBase

try:
    import time
    import struct
    import array
    import math
    import os
    import threading
    from ctypes import c_int16
    from datetime import datetime
    from contextlib import contextmanager
    #import chassis

    #from chassis import chassis
    import sonic_platform.platform
    #from sonic_py_common import logger
except ImportError as e:
    print("{}".format(e))
    # When build python3 xcvrd, it tries to do basic check which will import this file. However,
    # not all platform supports python3 API now, so it could cause an issue when importing
    # sonic_platform.platform. We skip the ImportError here. This is safe because:
    #   1. If any python package is not available, there will be exception when use it
    #   2. Vendors know their platform API version, they are responsible to use correct python
    #   version when importing this file.
    # pass

# strut definitions used in fw related functions


class cable_image_version_s(object):

    def __init__(self):
        self.image_version_minor = 0
        self.image_version_major = 0


class cable_image_info_s(object):

    def __init__(self):
        self.image_fw_version = cable_image_version_s()
        self.image_api_version = cable_image_version_s()
        self.image_crc32 = 0
        self.image_ptr = array.array('H', [])
        self.image_size = 0


class cable_bank_info_s(object):

    def __init__(self):
        self.image_fw_version = cable_image_version_s()
        self.image_api_version = cable_image_version_s()
        self.image_crc32 = 0


class cable_status_info_s():

    def __init__(self):
        self.current_bank = 0
        self.next_bank = 0
        self.bank1_info = cable_bank_info_s()
        self.bank2_info = cable_bank_info_s()


class cable_upgrade_info_s(object):

    def __init__(self):
        self.image_info = cable_image_info_s()
        self.status_info = cable_status_info_s()
        self.destination = 0
        self.bank = 0


class cable_upgrade_head_s():

    def __init__(self):
        self.compression = 0
        self.compressed_size = 0
        self.compressed_crc32 = 0
        self.add_size = 0
        self.add_crc32 = 0
        self.header_crc32 = 0
        self.cable_up_info = cable_upgrade_info_s()


class cmd_handle_s(object):

    def __init__(self):
        self.cmd_wr = 0
        self.read_info = 0
        self.cmd_rd = 0
        self.info_len = 0
        self.data_read = bytearray(30)


class valid_port_option_table_s:

    def __init__(self, speed, fec_tor, fec_nic, anlt_tor, anlt_nic, mode):
        self.speed = speed
        self.fec_tor = fec_tor
        self.fec_nic = fec_nic
        self.anlt_tor = anlt_tor
        self.anlt_nic = anlt_nic
        self.mode = mode


class context_state_frame_s(object):
    def __init__(self):
        self.r0 = 0
        self.r1 = 0
        self.r2 = 0
        self.r3 = 0
        self.r12 = 0
        self.lr = 0
        self.return_address = 0
        self.xpsr = 0


class ram2_exp_hdr_s(object):
    def __init__(self):
        self.crash = 0
        self.crash_len = 0
        self.cfsr_reg = 0
        self.ufsr_reg = 0
        self.bfsr_reg = 0
        self.mmfsr_reg = 0
        self.val = context_state_frame_s()
        self.exp_sp_depth = 0


class ram2_exp_s(object):
    def __init__(self):
        self.hdr_val = ram2_exp_hdr_s()
        self.exp_stack = array.array('I', [])


ENABLE_DBG_PRINT = False


def enable_debug_print(flag):
    global ENABLE_DBG_PRINT
    ENABLE_DBG_PRINT = flag


def debug_print(log_msg):
    if ENABLE_DBG_PRINT:
        curr_timestamp = datetime.utcnow()
        cur_tstr = curr_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print("({}) {} : {}".format(threading.currentThread().getName(), cur_tstr, log_msg))
    return None

#
# Lock for port access for thread safe
#


class PortLock(object):
    def __init__(self, port_nbr):
        self.port_nbr = port_nbr
        self.lock = threading.RLock()

    # def __del__(self):
    #   print("PortLock {} destroyed".format(self.port_nbr))

    def __enter__(self):
        self.lock.acquire()
        debug_print("(with) acquired lock for port {}".format(self.port_nbr))

    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()
        debug_print("(with) released lock for port {}".format(self.port_nbr))

    @contextmanager
    def acquire_timeout(self, timeout):
        result = self.lock.acquire(timeout=timeout)
        debug_print("(with timeout) acquired lock for port {}".format(self.port_nbr))
        yield result
        if result:
            self.lock.release()
            debug_print("(with timeout) released lock for port {}".format(self.port_nbr))

    def get_port_nbr(self):
        return self.port_nbr

    def acquire(self):
        self.lock.acquire()
        debug_print("explicitly acquired lock for port {}".format(self.port_nbr))

    def release(self):
        self.lock.release()
        debug_print("explicitly released lock for port {}".format(self.port_nbr))

#
# BCM Y Cable implementation derived from y_cable_base
#


class YCable(YCableBase):

    WARMBOOT = 0
    COLDBOOT = 1

    # definitions of the modes to be run for loopback mode
    # on the port/cable
    LOOPBACK_MODE_NEAR_END = 1

    # definitions of PRBS run modes
    PRBS_DIRECTION_BOTH = 0
    PRBS_DIRECTION_GENERATOR = 1
    PRBS_DIRECTION_CHECKER = 2

    BCM_API_VERSION = "1.2"
    CONSOLE_PRINT = False

    # Log levels
    LOG_INFO = 1
    LOG_WARN = 2
    LOG_DEBUG = 3
    LOG_ERROR = 4

    CABLE_MODE_100G_FEC = 0
    CABLE_MODE_100G_PCS = 1
    CABLE_MODE_50G_FEC = 2
    CABLE_MODE_50G_PCS = 3

    PORT_SPEED_50 = 0
    PORT_SPEED_100 = 1

    FEC_MODE_NONE = 0
    FEC_MODE_RS = 1
    PORT_FEC_FC = 2

    ANLT_DISABLED = 1
    ANLT_ENABLED = 2
    ANLT_DONT_CARE = 3
    #ANLT_DONT_CARE = True

    CABLE_MODE_50G = 50000
    CABLE_MODE_100G = 100000

    PORT_LOCK_TIMEOUT = 30  # in seconds

    # Register absolute addresses
    QSFP28_LP_3_TX_RX_LOSS = 0x00000003
    QSFP28_LP_5_TX_RX_CDR_LOL = 0x00000005
    QSFP28_LOS_LOL_SEC = 0x0000004A
    QSFP28_LINK_DOWN = 0x0000004B
    QSFP28_LINK_FAULT = 0x0000004C
    QSFP28_MESC_FAULT = 0x0000004D
    QSFP28_BIP_CW_ERR_FAULT = 0x00000050
    QSFP28_LP_22_TEMP_MSB = 0x00000016
    QSFP_SQL_STATUS = 0x0000004E
    QSFP_LP_31_VENDOR = 0x0000004F           # CHANGED to 79 -- Not used. Check!
    QSFP_LINK_FAULT_MASK = 0x00007F61
    QSFP_MESC_MASK = 0x00007F62
    QSFP28_LP_100_TX_RX_LOS_MASK = 0x00000064
    QSFP28_LP_102_TX_RX_CDR_LOL_MASK = 0x00000066
    QSFP28_LOS_LOL_SEC_MASK = 0x00007F63
    QSFP28_UP_DOWN_MASK = 0x00007F64
    QSFP28_BIP_UNCORR_MASK = 0x00007F65
    QSFP28_UP0_148_VENDOR_NAME_0 = 0x00000094
    QSFP28_UP0_168_PN_1 = 0x000000a8
    QSFP28_UP0_224_SPECIFIC_1_RSV = 0x000000e0
    QSFP_BRCM_CABLE_CMD = 0x00000013
    QSFP_BRCM_CABLE_CTRL_CMD_STS = 0x00000014
    QSFP_VEN_FE_130_BRCM_DATA_LENGHT_LSB = 0x00007f82
    QSFP28_VENFD_129_DIE_TEMP_MSB = 0x00007f01
    QSFP28_VENFD_130_DIE_VOLTAGE_LSB = 0x00007f02
    QSFP28_VENFD_184_NIC_TORB_TORA_RESET = 0x00007f38
    QSFP28_VENFD_216_LINK_STATUS = 0x00007f58
    QSFP28_RESET_SELF_OFFSET = 0x0000005D

    # temperature and voltage register offsets
    QSFP28_VENFD_128_DIE_TEMP_LSB = 0x00007f00
    QSFP28_VENFD_131_DIE_VOLTAGE_MSB = 0x00007f03
    QSFP28_VENFD_134_TORA_TEMP_MSB = 0x00007f06
    QSFP28_VENFD_135_TORA_TEMP_LSB = 0x00007f07
    QSFP28_VENFD_138_TORB_TEMP_MSB = 0x00007f0a
    QSFP28_VENFD_139_TORB_TEMP_LSB = 0x00007f0b
    QSFP28_VENFD_142_NIC_TEMP_MSB = 0x00007f0e
    QSFP28_VENFD_143_NIC_TEMP_LSB = 0x00007f0f

    QSFP28_LP_QSFP28_LP_2_STATUS_CR = 0x00000002
    QSFP_BRCM_FW_UPGRADE_COMP_SET = 0x00000094

    # User defined
    CMD_REQ_PARAM_START_OFFSET = 0x7F87
    CMD_RSP_PARAM_START_OFFSET = 0x7FB8

    MAX_REQ_PARAM_LEN = 0x30
    MAX_RSP_PARAM_LEN = 0x77

    # command IDs
    CABLE_CMD_ID_PRBS_SET = 0x01
    CABLE_CMD_ID_PRBS_CHK = 0x03
    CABLE_CMD_ID_SET_LOOPBACK = 0x04
    CABLE_CMD_ID_GET_LOOPBACK = 0x05
    CABLE_CMD_ID_SET_TXFIR = 0x06
    CABLE_CMD_ID_GET_TXFIR = 0x07
    CABLE_CMD_ID_SET_ANLT = 0x08
    CABLE_CMD_ID_GET_ANLT = 0x09
    CABLE_CMD_ID_GET_ANLT_RESTART = 0x0A
    CABLE_CMD_ID_GET_ANLT_GET_STATUS = 0x0B
    CABLE_CMD_ID_SET_POLARITY = 0x0C
    CABLE_CMD_ID_GET_POLARITY = 0x0D
    CABLE_CMD_ID_SET_MODE = 0x0E
    CABLE_CMD_ID_GET_MODE = 0x0F
    CABLE_CMD_ID_GET_SQUELCH = 0x10
    CABLE_CMD_ID_SET_SQUELCH = 0x11
    CABLE_CMD_ID_GET_HMUX_CONFIG = 0x12
    CABLE_CMD_ID_SET_HMUX_CONFIG = 0x13
    CABLE_CMD_ID_GET_HMUX_CONTEXT = 0x14
    CABLE_CMD_ID_SET_HMUX_CONTEXT = 0x15
    CABLE_CMD_ID_GET_HMUX_STATS = 0x16
    CABLE_CMD_ID_READ_REG = 0x17
    CABLE_CMD_ID_WRITE_REG = 0x18
    CABLE_CMD_ID_ENABLE_PHY_CHIP = 0x19
    CABLE_CMD_ID_DISABLE_PHY_CHIP = 0x1A
    CABLE_CMD_ID_DUMP_PAGE = 0x1B
    CABLE_CMD_ID_GET_EYE_MARGIN = 0x1F
    CABLE_CMD_ID_GET_SNR = 0x20
    CABLE_CMD_ID_SET_HMUX_CONTEXT_PRI = 0x21
    CABLE_CMD_ID_SET_HMUX_CONTEXT_SEC = 0x22
    CABLE_CMD_ID_GET_TOT_MAN_SWT_CNT = 0x23
    CABLE_CMD_ID_GET_TOT_MAN_SWT_CNT_CLR = 0x24
    CABLE_CMD_ID_GET_TO_TORA_MAN_SWT_CNT = 0x25
    CABLE_CMD_ID_GET_TO_TORA_MAN_SWT_CNT_CLR = 0x26
    CABLE_CMD_ID_GET_TO_TORB_MAN_SWT_CNT = 0x27
    CABLE_CMD_ID_GET_TO_TORB_MAN_SWT_CNT_CLR = 0x28
    CABLE_CMD_ID_GET_FM_TORA_MAN_SWT_CNT = 0x29
    CABLE_CMD_ID_GET_FM_TORA_MAN_SWT_CNT_CLR = 0x2A
    CABLE_CMD_ID_GET_FM_TORB_MAN_SWT_CNT = 0x2B
    CABLE_CMD_ID_GET_FM_TORB_MAN_SWT_CNT_CLR = 0x2C
    CABLE_CMD_ID_GET_TOT_AUT_SWT_CNT = 0x2D
    CABLE_CMD_ID_GET_TOT_AUT_SWT_CNT_CLR = 0x2E
    CABLE_CMD_ID_GET_TO_TORA_AUT_SWT_CNT = 0x2F
    CABLE_CMD_ID_GET_TO_TORA_AUT_SWT_CNT_CLR = 0x30
    CABLE_CMD_ID_GET_TO_TORB_AUT_SWT_CNT = 0x31
    CABLE_CMD_ID_GET_TO_TORB_AUT_SWT_CNT_CLR = 0x32
    CABLE_CMD_ID_READ_MCU_RAM = 0x33
    CABLE_CMD_ID_CLEAR_CRASH = 0x34

    # Download commands
    FW_CMD_START = 1
    FW_CMD_TRANSFER = 2
    FW_CMD_COMPLETE = 3
    FW_CMD_SWAP = 4
    FW_CMD_ABORT = 5
    FW_CMD_INFO = 6
    FW_CMD_RESET = 7

    FW_UP_SUCCESS = 1
    FW_UP_IN_PROGRESS = 2

    FW_CMD_WARM_BOOT = 13
    FW_CMD_BOOT_STATUS = 14

    # destination values
    TOR_MCU = 0x01
    TOR_MCU_SELF = 0x01
    NIC_MCU = 0x02
    MUX_CHIP = 0x03
    TOR_MCU_PEER = 0x04

    # FW image address
    MCU_FW_IMG_INFO_ADDR = 0x3E7F0
    MCU_FW_IMG_SIZE = 0x3E800
    MUX_FW_IMG_INFO_ADDR = 0x3FFE0
    MUX_FW_IMG_SIZE = 0x40000
    FW_IMG_INFO_SIZE = 12
    FW_UP_PACKET_SIZE = 128

    QSFP_BRCM_FW_UPGRADE_DATA_PAGE_1 = 0x81
    QSFP_BRCM_FW_UPGRADE_DATA_PAGE_2 = 0x82
    QSFP_BRCM_FW_UPGRADE_DATA_START = 0x80
    QSFP_BRCM_DIAGNOSTIC_PAGE = 0x04
    QSFP_BRCM_DIAGNOSTIC_STATUS = 0x81

    QSFP_BRCM_FW_UPGRADE_PACKET_SIZE = 0x92
    QSFP_BRCM_FW_UPGRADE_CURRENT_BANK = 0x80

    QSFP_BRCM_FW_UPGRADE_CTRL_CMD = 0x80
    QSFP_BRCM_FW_UPGRADE_CMD_STS = 0x81
    QSFP_BRCM_FW_UPGRADE_CTRL_STS = 0x81

    QSFP_BRCM_FW_UPGRADE_PAGE = 0x80
    QSFP_BRCM_FW_UPGRADE_HEADER_0_7 = 0x82
    QSFP_BRCM_FW_UPGRADE_HEADER_24_31 = 0x85
    QSFP_BRCM_FW_UPGRADE_BOOT_STATUS = 0x9A

    # muxchip return codes
    RR_ERROR = -1  # -255      # Error Category
    RR_ERROR_SYSTEM_UNAVAILABLE = -1  # -250      # System Unavailable Error
    RR_SUCCESS = 0         # Success

    # PRBS polynomials
    CABLE_PRBS7 = 0  # PRBS poly 7
    CABLE_PRBS9 = 1  # PRBS poly 9
    CABLE_PRBS11 = 2  # PRBS poly 11
    CABLE_PRBS15 = 3  # PRBS poly 15
    CABLE_PRBS23 = 4  # PRBS poly 23
    CABLE_PRBS31 = 5  # PRBS poly 31
    CABLE_PRBS58 = 6  # PRBS poly 58
    CABLE_PRBS49 = 7  # PRBS poly 49
    CABLE_PRBS13 = 8  # PRBS poly 13

    # Loopback modes
    CABLE_NIC_GLOOPBACK_MODE = 0  # Global NIC loopback mode, line/NIC side deep or G-Loop
    CABLE_NIC_RLOOPBACK_MODE = 1  # Remote NIC loopback mode, line/NIC side R-LOOP
    CABLE_TOR_GLOOPBACK_MODE = 2  # Global TOR loopback mode, TOR side deep or G-Loop
    CABLE_TOR_RLOOPBACK_MODE = 3  # Remote TOR loopback mode, side R-LOOP

    # core ip's
    CORE_IP_ALL = 0  # Core IP ALL
    CORE_IP_LW = 2  # Core IP Line Wrapper
    CORE_IP_CLIENT = 3  # Core IP SerDes
    CORE_IP_NIC = 1
    CORE_IP_TOR = 2
    CORE_IP_CENTRAL = 3

    # Error codes returned from y_cable functions
    ERROR_PLATFORM_NOT_LOADED = -1  # -1
    ERROR_CMD_STS_CHECK_FAILED = -1  # -2
    ERROR_WRITE_EEPROM_FAILED = -1  # -3
    ERROR_CMD_PROCESSING_FAILED = -1  # -4
    ERROR_MCU_NOT_RELEASED = -1  # -5
    ERROR_MCU_BUSY = -1  # -6
    ERROR_INVALID_PRBS_MODE = -1  # -8
    ERROR_INVALID_TARGET = -1  # -9
    ERROR_INVALID_DIRECTION = -1  # -10
    ERROR_INVALID_POLARITY = -1  # -11
    ERROR_CMD_EXEC_FAILED = -1  # -12
    ERROR_PORT_LOCK_TIMEOUT = -1  # -13
    ERROR_INVALID_INPUT = -1  # -14
    ERROR_WR_EEPROM_FAILED = -1

    ERROR_FW_GET_STATUS_FAILED = -1  # -15
    ERROR_NO_MATCHING_FW = -1  # -16
    ERROR_RESET_FAILED = -1  # -17
    ERROR_TOGGLE_FAILED = -1  # -18
    # ERROR_FW_ACTIVATE_FAILURE     = -1 #-19
    # ERROR_FW_ROLLBACK_FAILURE     = -1 #-20
    ERROR_GET_FEC_MODE_FAILED = -1  # -21
    ERROR_READ_SIDE_FAILED = -1  # -22

    WARNING_FW_ALREADY_ACTIVE = -50
    WARNING_FW_ALREADY_ROLLEDBACK = -51

    EEPROM_READ_DATA_INVALID = -1  # -100
    EEPROM_ERROR = -1  # -101
    API_FAIL = -1  # -102

    ERROR_RW_NIC_FAILED = -1  # -30     #Unable to communicate with NIC MCU
    ERROR_RW_TOR_FAILED = -1  # -31     #Unable to communicate with TOR MCU
    ERROR_GET_VERSION_FAILED = -1  # -32	    #Unable to get firmware version from MCU
    ERROR_FLASH_SIZE_INVALID = -1  # -33	    #Firmware image size is greater than flash bank size
    ERROR_FLASH_ERASE_FAILED = -1  # -34	    #Flash erase failed
    ERROR_FLASH_WRITE_FAILED = -1  # -35	    #Flash write failed
    ERROR_FLASH_READ_FAILED = -1  # -36	    #Flash read failed
    ERROR_CRC32_FAILED = -1  # -37	    #Flash CRC validation failed
    ERROR_CMD_TIMEOUT = -1  # -38	    #No response after command sent
    ERROR_SYSTEM_BUSY = -1  # -39	    #System is busy

    def __init__(self, port, logger1):

        self.port = port
        self.platform_chassis = None
        self.sfp = None
        self.lock = PortLock(port)
        self.fp_lock = PortLock(port)
        self.dl_lock = PortLock(port)
        self.logger = logger1
        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_NOT_INITIATED_OR_FINISHED
        super(YCable, self).__init__(port, logger1)
        try:
            #self.platform_chassis = chassis()
            self.platform_chassis = sonic_platform.platform.Platform().get_chassis()
            self.sfp = self.platform_chassis.get_sfp(self.port)

            logger1.log_info("chassis loaded {}".format(self.platform_chassis))
        except Exception as e:
            logger1.log_warning("Failed to load chassis due to {}".format(repr(e)))

#############################################################################################
###                     Broadcom internal/debug/utility functions                         ###
#############################################################################################

    def enable_all_log(self, enable):
        if enable:
            self.CONSOLE_PRINT = True
            if self.logger is not None:
                self.logger.set_min_log_priority(9)
            print("Logging enabled...")
        else:
            self.CONSOLE_PRINT = False
            if self.logger is not None:
                self.logger.set_min_log_priority(7)
            print("Logging disabled...")

    def __get_pid_str(self):
        pid_str = "[{},{}] Port-{} : ".format(os.getpid(), threading.currentThread().getName(), self.port)
        return pid_str

    def log_timestamp(self, last_timestamp, log_msg):
        curr_timestamp = datetime.utcnow()
        cur_tstr = curr_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        difftime = curr_timestamp - last_timestamp

        tstr = "({}s {}ms)".format(difftime.seconds, difftime.microseconds//1000)
        ret_str = cur_tstr + tstr
        self.log(self.LOG_DEBUG, "{} : {}".format(ret_str, log_msg))

        return curr_timestamp

    def log(self, level, msg, also_print_to_console=False):

        msg = self.__get_pid_str() + msg
        also_print_to_console = True if self.CONSOLE_PRINT else also_print_to_console

        if level == self.LOG_INFO:
            self.logger.log_info(msg)
        elif level == self.LOG_WARN:
            self.logger.log_warning(msg)
        elif level == self.LOG_DEBUG:
            self.logger.log_debug(msg)
        elif level == self.LOG_ERROR:
            self.logger.log_error(msg)

        if self.CONSOLE_PRINT or also_print_to_console:
            curr_timestamp = datetime.utcnow()
            cur_tstr = curr_timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            msg = cur_tstr + " " + msg
            print(msg)

    def __util_convert_to_phyinfo_details(self, target, lane_map):
        """

        This util API is internally used to simplify the calculation of core_ip, lane_mask

        """

        if target == self.TARGET_NIC or target == self.EYE_PRBS_LOOPBACK_TARGET_NIC:
            core_ip = self.CORE_IP_NIC
        else:
            core_ip = self.CORE_IP_TOR

        read_side = self.get_read_side()
        is_torA = False

        if read_side == 1:
            is_torA = True

        if (target == self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            target = read_side

        # if check is on TOR-B, make is_torA False
        if (target == self.TARGET_TOR_B or target == self.EYE_PRBS_LOOPBACK_TARGET_TOR_B) and read_side == self.TARGET_TOR_A:
            is_torA = False
        # if check is on TOR-A and read side is TOR-B, make is_torA False
        elif (target == self.TARGET_TOR_A or target == self.EYE_PRBS_LOOPBACK_TARGET_TOR_A) and read_side == self.TARGET_TOR_B:
            is_torA = True

        #lane_mask = lane_map

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

    def __util_convert_to_loopback_phyinfo(self, target, lane_map, lb_mode):
        """

        This util API is internally used to simplify the calculation of core_ip, lane_mask

        """

        if target == self.TARGET_NIC or target == self.EYE_PRBS_LOOPBACK_TARGET_NIC:
            core_ip = self.CORE_IP_NIC
        else:
            core_ip = self.CORE_IP_TOR

        read_side = self.get_read_side()
        is_torA = False

        if read_side == self.TARGET_TOR_A:
            is_torA = True

        if (target == self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            target = read_side

        # if target is TOR-B, but read_side is TOR-A, make is_torA False
        if (target == self.TARGET_TOR_B or target == self.EYE_PRBS_LOOPBACK_TARGET_TOR_B) and read_side == self.TARGET_TOR_A:
            is_torA = False
        # if target is TOR-A but read_side is TOR-B, make is_torA True
        elif (target == self.TARGET_TOR_A or target == self.EYE_PRBS_LOOPBACK_TARGET_TOR_A) and read_side == self.TARGET_TOR_B:
            is_torA = True

        #lane_mask = lane_map

        if core_ip == self.CORE_IP_NIC:
            lane_mask = lane_map
            if lb_mode == self.LOOPBACK_MODE_FAR_END:
                mode = self.CABLE_NIC_GLOOPBACK_MODE
            elif lb_mode == self.LOOPBACK_MODE_NEAR_END:
                mode = self.CABLE_NIC_RLOOPBACK_MODE
            else:
                self.log(self.LOG_ERROR, "Incorrect mode value")

        else:
            if is_torA is False:
                lane_mask = ((lane_map << 4) & 0xF0) | ((lane_map >> 4) & 0x0F)
                if lb_mode == self.LOOPBACK_MODE_FAR_END:
                    mode = self.CABLE_TOR_GLOOPBACK_MODE
                elif lb_mode == self.LOOPBACK_MODE_NEAR_END:
                    mode = self.CABLE_TOR_RLOOPBACK_MODE
                else:
                    self.log(self.LOG_ERROR, "Incorrect mode value")
            else:
                lane_mask = lane_map
                if lb_mode == self.LOOPBACK_MODE_FAR_END:
                    mode = self.CABLE_TOR_GLOOPBACK_MODE
                elif lb_mode == self.LOOPBACK_MODE_NEAR_END:
                    mode = self.CABLE_TOR_RLOOPBACK_MODE
                else:
                    self.log(self.LOG_ERROR, "Incorrect mode value")

        if core_ip == self.CORE_IP_TOR:
            core_ip = self.CORE_IP_CLIENT
        elif core_ip == self.CORE_IP_NIC:
            core_ip = self.CORE_IP_LW
        else:
            core_ip = self.CORE_IP_ALL

        return core_ip, lane_mask, mode

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

        start_ts = datetime.utcnow()
        ts = datetime.utcnow()
        curr_offset = None
        cmd_rsp_body = None
        ret_val = 0

        if self.platform_chassis is not None:

            debug_print("Trying for the lock")
            with self.lock.acquire_timeout(self.PORT_LOCK_TIMEOUT) as result:
                if result:
                    ts = self.log_timestamp(ts, "lock acquired")
                    # read cable command and status offsets
                    curr_offset = self.QSFP_BRCM_CABLE_CMD
                    result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 2)
                    if result is None:
                        self.log(self.LOG_ERROR, "read eeprom failed")
                        return self.EEPROM_ERROR, None

                    cmd_req = result[0]
                    cmd_sts = result[1]
                    ts = self.log_timestamp(ts, "read cmd/sts done")

                    # if command request and status both are 1,
                    #    write 0 to cmd req and
                    #    wait for status to go 0
                    if ((cmd_req & 0x01) == 1) and ((cmd_sts & 0x01) == 1):
                        cmd_req = 0
                        curr_offset = self.QSFP_BRCM_CABLE_CMD
                        buffer1 = bytearray([cmd_req])
                        result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1)
                        if result is False:
                            return self.ERROR_WR_EEPROM_FAILED, None

                        # poll command status for 100ms
                        start = time.monotonic_ns()
                        ms_elapsed = 0
                        while (ms_elapsed < 100):
                            sta = 0
                            curr_offset = self.QSFP_BRCM_CABLE_CTRL_CMD_STS
                            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                            if result is None:
                                return self.EEPROM_ERROR, None
                            sta = result[0]

                            if (sta & 0x01) == 0x0:
                                break
                            ms_elapsed = (time.monotonic_ns()//1000000) - (start//1000000)
                        else:
                            self.log(self.LOG_ERROR, "CMD_REQ/STS both are stuck at 1")
                            return self.ERROR_CMD_STS_CHECK_FAILED, None
                        ts = self.log_timestamp(ts, "resetting cmd to 0 done (error logic)")

                    # check if any command is currently being executed
                    if ((cmd_req & 0x01) == 0) and ((cmd_sts & 0x01) == 0):
                        #
                        #    Combine the write of the cable command header
                        #    - write the request parameter len
                        #    - write the response parameter len
                        #    - write the BH lane mask (Client)
                        #    - write the LW lane mask (Line)
                        #    - write the core ip value
                        #

                        # skip sending cmd_hdr for SET_HMUX_CONTEXT_PRI and SET_HMUX_CONTEXT_SEC
                        if ((command_id < self.CABLE_CMD_ID_SET_HMUX_CONTEXT_PRI) or
                            (command_id == self.CABLE_CMD_ID_READ_MCU_RAM) or
                                (command_id == self.CABLE_CMD_ID_CLEAR_CRASH)):
                            curr_offset = self.QSFP_VEN_FE_130_BRCM_DATA_LENGHT_LSB
                            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 5, cmd_hdr)
                            if result is False:
                                self.log(self.LOG_ERROR, "write_eeprom() failed")
                                return self.ERROR_WRITE_EEPROM_FAILED, None
                            ts = self.log_timestamp(ts, "writing of cmd_hdr 5 bytes done")
                        else:
                            curr_offset = self.QSFP_VEN_FE_130_BRCM_DATA_LENGHT_LSB + 1
                            cmd_rsp_len = cmd_hdr[1]
                            buffer1 = bytearray([cmd_rsp_len])
                            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1)
                            if result is False:
                                self.log(self.LOG_ERROR, "write_eeprom() failed")
                                return self.ERROR_WRITE_EEPROM_FAILED, None
                            ts = self.log_timestamp(ts, "writing of cmd_hdr (only rsp_len) 1 byte done")

                        # write request data
                        wr_len = cmd_hdr[0]
                        if wr_len > 0:
                            curr_offset = self.CMD_REQ_PARAM_START_OFFSET
                            result = self.platform_chassis.get_sfp(
                                self.port).write_eeprom(curr_offset, wr_len, cmd_req_body)
                            if result is False:
                                return self.ERROR_WR_EEPROM_FAILED, None
                        ts = self.log_timestamp(ts, "write request data done - bytes {}".format(wr_len))

                        # write the command request byte now
                        cmd_req = 1
                        cmd_req = (cmd_req | (command_id << 1))
                        curr_offset = self.QSFP_BRCM_CABLE_CMD
                        buffer1 = bytearray([cmd_req])
                        result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1)
                        if result is False:
                            return self.ERROR_WR_EEPROM_FAILED, None
                        rd = False
                        ts = self.log_timestamp(ts, "write command request to 1 done")

                        error = 0
                        start = time.monotonic_ns()
                        ms_elapsed = 0
                        while (ms_elapsed < 500):
                            sta = 0
                            curr_offset = self.QSFP_BRCM_CABLE_CTRL_CMD_STS
                            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                            if result is None:
                                return self.EEPROM_ERROR, None
                            sta = result[0]

                            if (sta & 0x7F) == 0x11:
                                rd = True
                                break

                            if (sta & 0x7F) == 0x31:
                                #rd = True
                                error = 1
                                self.log(self.LOG_ERROR, "ERROR: NIC command failed")
                                break

                            ms_elapsed = (time.monotonic_ns()//1000000) - (start//1000000)
                        else:
                            self.log(self.LOG_ERROR, "CMD_STS never read as 0x11 or 0x31. reg_value: {}".format(hex(sta)))
                            ret_val = self.ERROR_CMD_PROCESSING_FAILED
                        ts = self.log_timestamp(ts, "polling for status done")

                        # read response data
                        if rd is True:
                            rd_len = cmd_hdr[1]
                            if rd_len > 0:
                                curr_offset = self.CMD_RSP_PARAM_START_OFFSET
                                cmd_rsp_body = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, rd_len)
                                if cmd_rsp_body is None:
                                    return self.EEPROM_ERROR, None
                            ts = self.log_timestamp(ts, "read cmd response bytes {} done".format(rd_len))

                        # set the command request to idle state
                        cmd_req = 0
                        curr_offset = self.QSFP_BRCM_CABLE_CMD
                        buffer1 = bytearray([cmd_req])
                        result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1)
                        if result is False:
                            self.log(self.LOG_ERROR, "write eeprom failed for CMD_req")
                            return self.ERROR_WRITE_EEPROM_FAILED, None
                        ts = self.log_timestamp(ts, "write command request to 0 done")

                        # wait  for MCU response to be pulled down
                        start = time.monotonic_ns()
                        ms_elapsed = 0
                        while (ms_elapsed < 2000):
                            sta = 0
                            curr_offset = self.QSFP_BRCM_CABLE_CTRL_CMD_STS
                            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                            if result is None:
                                return self.EEPROM_ERROR, None
                            sta = result[0]

                            if (sta & 0x01) == 0x0:
                                break
                            ms_elapsed = (time.monotonic_ns()//1000000) - (start//1000000)
                        else:
                            ret_val = self.ERROR_MCU_NOT_RELEASED
                        self.log_timestamp(ts, "poll for MCU response to be puled down - done")

                        if error:
                            return -1, None

                    else:
                        ret_val = self.ERROR_MCU_BUSY
                else:
                    self.log(self.LOG_ERROR, "Port lock timed-out!")
                    return self.ERROR_PORT_LOCK_TIMEOUT, None

        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to check if link is Active on TOR B side")
            return self.ERROR_PLATFORM_NOT_LOADED, None

        self.log_timestamp(start_ts, "__cable_cmd_execute() completed")
        return ret_val, cmd_rsp_body

    def __validate_read_data(self, result, size, message):
        '''
        This API specifically used to validate the register read value
        '''

        if result is not None:
            if isinstance(result, bytearray):
                if len(result) != size:
                    LOG_MESSAGE_TEMPLATE = "Error: for checking mux_cable {}, eeprom read returned a size {} not equal to {} for port {}"
                    self.log(self.LOG_ERROR, LOG_MESSAGE_TEMPLATE.format(message, len(result), size, self.port))
                    return self.EEPROM_READ_DATA_INVALID
            else:
                LOG_MESSAGE_TEMPLATE = "Error: for checking mux_cable {}, eeprom read returned an instance value of type {} which is not a bytearray for port {}"
                self.log(self.LOG_ERROR, LOG_MESSAGE_TEMPLATE.format(message, type(result), self.port))
                return self.EEPROM_READ_DATA_INVALID
        else:
            LOG_MESSAGE_TEMPLATE = "Error: for checking mux_cable {}, eeprom read returned a None value for port {} which is not expected"
            self.log(self.LOG_ERROR, LOG_MESSAGE_TEMPLATE.format(message, self.port))
            return self.EEPROM_READ_DATA_INVALID


##############################################################################
#
# Public APIs
#
##############################################################################

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
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to get vendor name and pn_number")
            return self.ERROR_PLATFORM_NOT_LOADED

        if self.__validate_read_data(part_result, 15, "get  part_number") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR

        part_number = str(part_result.decode())
        self.log(self.LOG_DEBUG, "Part number = {}".format(part_number))

        return part_number

    def get_vendor(self):
        """
        This API returns the vendor name of the Y cable for a specfic port.
        The port on which this API is called for can be referred using self.port.

        Args:
            None
        Returns:
            a string, with vendor name
        """

        if self.platform_chassis is not None:
            curr_offset = self.QSFP28_UP0_148_VENDOR_NAME_0
            vendor_result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 15)
        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to get vendor name ")
            return self.ERROR_PLATFORM_NOT_LOADED

        if self.__validate_read_data(vendor_result, 15, "Vendor_name") == -1:
            return self.EEPROM_ERROR

        vendor_name = str(vendor_result.decode())
        self.log(self.LOG_DEBUG, "vendor name = {}".format(vendor_name))

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

        start_ts = datetime.utcnow()
        ts = self.log_timestamp(start_ts, " get_read_side() start")

        if self.platform_chassis is not None:
            curr_offset = self.QSFP28_UP0_224_SPECIFIC_1_RSV
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to check read side")
            return self.ERROR_PLATFORM_NOT_LOADED

        if self.__validate_read_data(result, 1, "read side") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR
        read_side = struct.unpack("<B", result)
        self.log_timestamp(ts, " get_read_side() completed")
        if read_side[0] & 0x1:
            self.log(self.LOG_DEBUG, "Reading the Y cable from TOR A side")
            ret = self.TARGET_TOR_A
        elif read_side[0] & 0x2:
            self.log(self.LOG_DEBUG, "Reading the Y cable from TOR B side")
            ret = self.TARGET_TOR_B
        elif read_side[0] & 0x4:
            self.log(self.LOG_DEBUG, "Reading the Y cable from NIC side")
            ret = self.TARGET_NIC
        else:
            self.log(self.LOG_WARN, "Target unknown")
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

        start_ts = datetime.utcnow()
        ts = self.log_timestamp(start_ts, "get_mux_direction() start")

        fast_command = bytearray(30)
        with self.fp_lock.acquire_timeout(self.PORT_LOCK_TIMEOUT) as result:
            if result:
                fast_command[0] = 0x1
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(32, 1, fast_command)
                if result is False:
                    self.log(self.LOG_ERROR, "get_mux_direction write eeprom failed")
                    return self.EEPROM_ERROR

                for _ in range(0, 3000):
                    status = self.platform_chassis.get_sfp(self.port).read_eeprom(32, 2)
                    if status is None:
                        self.log(self.LOG_ERROR, "get mux direction read eeprom failed")
                        return self.EEPROM_ERROR

                    if status[0] & 0x1 == 0:
                        break
            else:
                self.log(self.LOG_ERROR, "FP Port lock timed-out!")
                return self.ERROR_PORT_LOCK_TIMEOUT

        self.log_timestamp(ts, "get_mux_direction() completed")

        if status[0] & 0x1 != 0:
            self.log(self.LOG_ERROR, "Polling timed-out. Failed to get the mux_direction!")
            return self.TARGET_UNKNOWN

        if status[1] == 1:
            self.log(self.LOG_INFO, "Mux is pointing to TOR B")
            return self.TARGET_TOR_B
        elif status[1] == 0:
            self.log(self.LOG_INFO, "Mux is pointing to TOR A")
            return self.TARGET_TOR_A
        else:
            self.log(self.LOG_INFO, "Nothing linked for routing")
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

        start_ts = datetime.utcnow()
        ts = self.log_timestamp(start_ts, "toggle_mux_to_tor_a() start")

        fast_command = bytearray(30)
        with self.fp_lock.acquire_timeout(self.PORT_LOCK_TIMEOUT) as result:
            if result:
                fast_command[0] = 0x2
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(32, 1, fast_command)
                if result is False:
                    self.log(self.LOG_ERROR, "toggle_mux_to_tor_a write eeprom failed")
                    return self.EEPROM_ERROR

                cmd_ok = False
                for _ in range(0, 30):
                    # read 32 and 33
                    status = self.platform_chassis.get_sfp(self.port).read_eeprom(32, 2)
                    if status is None:
                        self.log(self.LOG_ERROR, "toggle_mux_to_tor_a read eeprom failed")
                        return self.EEPROM_ERROR

                    if status[0] & 0x2 == 0:
                        if status[1] == 0xFF:
                            self.log(self.LOG_ERROR, "ERROR: NIC not available")
                        else:
                            cmd_ok = True
                        break
            else:
                self.log(self.LOG_ERROR, "FP Port lock timed-out!")
                return self.ERROR_PORT_LOCK_TIMEOUT

        self.log_timestamp(ts, "toggle_mux_to_tor_a() completed")

        if cmd_ok == True:
            self.log(self.LOG_INFO, "Toggle mux to torA succeeded")
        else:
            self.log(self.LOG_ERROR, "ERROR: polling timed-out. Cmd_ok not received!")

        return cmd_ok

    def toggle_mux_to_tor_b(self):
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

        start_ts = datetime.utcnow()
        ts = self.log_timestamp(start_ts, "toggle_mux_to_tor_b() start")

        fast_command = bytearray(30)
        with self.fp_lock.acquire_timeout(self.PORT_LOCK_TIMEOUT) as result:
            if result:
                fast_command[0] = 0x4
                result = self.platform_chassis.get_sfp(self.port).write_eeprom(32, 1, fast_command)
                if result is False:
                    self.log(self.LOG_ERROR, "toggle_mux_to_tor_b write eeprom failed")
                    return self.EEPROM_ERROR

                cmd_ok = False
                for _ in range(0, 30):
                    # read 32 and 33
                    status = self.platform_chassis.get_sfp(self.port).read_eeprom(32, 2)
                    if status is None:
                        self.log(self.LOG_ERROR, "toggle_mux_to_tor_b read eeprom failed")
                        return self.EEPROM_ERROR

                    if status[0] & 0x4 == 0:
                        if status[1] == 0xFF:
                            self.log(self.LOG_ERROR, "ERROR: NIC not available")
                        else:
                            cmd_ok = True
                        break
            else:
                self.log(self.LOG_ERROR, "FP Port lock timed-out!")
                return self.ERROR_PORT_LOCK_TIMEOUT

        self.log_timestamp(ts, "toggle_mux_to_tor_b() completed")

        if cmd_ok == True:
            self.log(self.LOG_INFO, "Toggle mux to torB succeeded")

        return cmd_ok

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

        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET

        if self.platform_chassis is not None:
            curr_offset = self.QSFP28_VENFD_216_LINK_STATUS
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to check link is active for TOR A side")
            return self.ERROR_PLATFORM_NOT_LOADED

        if self.__validate_read_data(result, 1, "link is active for TOR A side") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR

        regval_read = struct.unpack("<B", result)

        if target == self.TARGET_TOR_A:
            if regval_read[0] & 0x1:
                self.log(self.LOG_INFO, "TOR A link is up")
                return True
            else:
                self.log(self.LOG_INFO, "TOR A link is down")
                return False

        elif target == self.TARGET_TOR_B:
            if regval_read[0] & 0x2:
                self.log(self.LOG_INFO, "TOR B link is up")
                return True
            else:
                self.log(self.LOG_INFO, "TOR B link is down")
                return False

        elif target == self.TARGET_NIC:
            if regval_read[0] & 0x4:
                self.log(self.LOG_INFO, "NIC link is up")
                return True
            else:
                self.log(self.LOG_INFO, "NIC link is down")
                return False
        else:
            self.log(self.LOG_WARN, "target is unkown")
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
                self.log(self.LOG_INFO, "TOR A standby linked and actively routing")
                ret_val = self.TARGET_TOR_A
            else:
                self.log(self.LOG_INFO, "Nothing linked for routing")
                ret_val = self.TARGET_UNKNOWN

        elif ret_val == self.TARGET_TOR_B:
            if self.is_link_active(self.TARGET_TOR_B) == True:
                self.log(self.LOG_INFO, "TOR B standby linked and actively routing")
                ret_val = self.TARGET_TOR_B
            else:
                self.log(self.LOG_INFO, "Nothing linked for routing")
                ret_val = self.TARGET_UNKNOWN

        return ret_val

    def util_get_switch_count(self, cmd_id):
        """
        utility function returns all switchover counters in a list

        """

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        count_value = None

        cmd_hdr[0] = 0
        cmd_hdr[1] = 4
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(cmd_id, cmd_hdr, cmd_req_body)
        if ret_val == 0 and cmd_rsp_body is not None:
            count_value = struct.unpack("<I", cmd_rsp_body)[0]
        else:
            self.log(self.LOG_ERROR, "Get switch count is failed ")

        return count_value

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

        if switch_count_type == self.SWITCH_COUNT_AUTO:
            cmd_id = self.CABLE_CMD_ID_GET_TOT_AUT_SWT_CNT_CLR if (
                clear_on_read) else self.CABLE_CMD_ID_GET_TOT_AUT_SWT_CNT
        elif switch_count_type == self.SWITCH_COUNT_MANUAL:
            cmd_id = self.CABLE_CMD_ID_GET_TOT_MAN_SWT_CNT_CLR if (
                clear_on_read) else self.CABLE_CMD_ID_GET_TOT_MAN_SWT_CNT
        else:
            self.log(self.LOG_ERROR, "Invalid switch_count_type {}".format(switch_count_type))
            return self.ERROR_INVALID_INPUT

        count_value = self.util_get_switch_count(cmd_id)
        self.log(self.LOG_INFO, "get_switch_count_total value = {} ".format(count_value))

        return count_value

    def get_switch_count_tor_a(self, clear_on_read=False):
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

        cmd_id = self.CABLE_CMD_ID_GET_FM_TORA_MAN_SWT_CNT_CLR if (
            clear_on_read) else self.CABLE_CMD_ID_GET_FM_TORA_MAN_SWT_CNT

        count_value = self.util_get_switch_count(cmd_id)
        self.log(self.LOG_INFO, "get_switch_count_tor_a value = {} ".format(count_value))

        return count_value

    def get_switch_count_tor_b(self, clear_on_read=False):
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

        cmd_id = self.CABLE_CMD_ID_GET_FM_TORB_MAN_SWT_CNT_CLR if (
            clear_on_read) else self.CABLE_CMD_ID_GET_FM_TORB_MAN_SWT_CNT

        count_value = self.util_get_switch_count(cmd_id)
        self.log(self.LOG_INFO, "get_switch_count_tor_b value = {} ".format(count_value))

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

        if (target == self.TARGET_TOR_A):
            if switch_count_type == self.SWITCH_COUNT_AUTO:
                cmd_id = self.CABLE_CMD_ID_GET_TO_TORA_AUT_SWT_CNT_CLR if (
                    clear_on_read) else self.CABLE_CMD_ID_GET_TO_TORA_AUT_SWT_CNT
            elif switch_count_type == self.SWITCH_COUNT_MANUAL:
                cmd_id = self.CABLE_CMD_ID_GET_TO_TORA_MAN_SWT_CNT_CLR if (
                    clear_on_read) else self.CABLE_CMD_ID_GET_TO_TORA_MAN_SWT_CNT
            else:
                self.log(self.LOG_ERROR, "Invalid switch_count_type {}".format(switch_count_type))
                return self.ERROR_INVALID_INPUT

        elif (target == self.TARGET_TOR_B):
            if switch_count_type == self.SWITCH_COUNT_AUTO:
                cmd_id = self.CABLE_CMD_ID_GET_TO_TORB_AUT_SWT_CNT_CLR if (
                    clear_on_read) else self.CABLE_CMD_ID_GET_TO_TORB_AUT_SWT_CNT
            elif switch_count_type == self.SWITCH_COUNT_MANUAL:
                cmd_id = self.CABLE_CMD_ID_GET_TO_TORB_MAN_SWT_CNT_CLR if (
                    clear_on_read) else self.CABLE_CMD_ID_GET_TO_TORB_MAN_SWT_CNT
            else:
                self.log(self.LOG_ERROR, "Invalid switch_count_type {}".format(switch_count_type))
                return self.ERROR_INVALID_INPUT

        else:
            self.log(self.LOG_ERROR, "Invalid target")
            return self.ERROR_INVALID_TARGET

        count_value = self.util_get_switch_count(cmd_id)
        self.log(self.LOG_INFO, "get_switch_count_target {} count_value = {} ".format(
            ("TOR_A" if target == self.TARGET_TOR_A else "TOR_B"), count_value))

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
        self.log(self.LOG_ERROR, "ERROR : {}, Sending abort".format(error))
        self.__cable_fw_mcu_abort(upgrade_info)
        time.sleep(0.001)

    def __handle_error(self, error):
        """
        Internal API to handle error in FW related APIs
        """
        dat = bytearray(30)
        status = 0

        self.log(self.LOG_ERROR, "ERROR : {} FAILED".format(error))

        if self.platform_chassis is not None:

            # set the command request to idle state
            dat[0] = 0x00
            curr_offset = (self.QSFP_BRCM_FW_UPGRADE_PAGE * 128) + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD
            result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat)
            if result is False:
                return self.ERROR_WRITE_EEPROM_FAILED

            # wait for mcu response to be pulled down
            for _ in range(30):
                curr_offset = (self.QSFP_BRCM_FW_UPGRADE_PAGE * 128) + self.QSFP_BRCM_FW_UPGRADE_CMD_STS
                status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                if status is None:
                    self.log(self.LOG_ERROR, "__handle_error read eeprom failed")
                    return self.EEPROM_ERROR

                if (status[0] & 0x01) == 0:
                    return
                time.sleep(0.001)

        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to handle_error")
            return self.ERROR_PLATFORM_NOT_LOADED

    def __cable_fw_mcu_abort(self, upgrade_info):
        """
        Internal API used to abort the execution of FW related function in case of error

        Args:
            upgrade_info : MCU details
        """
        ret_val = self.RR_ERROR
        dat = bytearray(30)
        status = 0
        req_status = False

        read_side = self.get_read_side()

        if read_side == 0x02:
            self.log(self.LOG_DEBUG, "Current side: TOR B")
        elif read_side == 0x01:
            self.log(self.LOG_DEBUG, "Current side TOR A")
        elif read_side == 0x04:
            self.log(self.LOG_DEBUG, "Current side NIC")
        else:
            self.log(self.LOG_ERROR, "Current side UNKNOWN")
            return self.ERROR_READ_SIDE_FAILED

        # Make sure TOR to NIC MCU communication is alive
        self.log(self.LOG_DEBUG, "Make sure TOR to NIC MCU communication is alive ")
        if (upgrade_info.destination == self.NIC_MCU) and ((read_side == 0x02) or (read_side == 0x01)):
            # Since we are running from TOR side, make sure no flush is on going
            for _ in range(3000):
                curr_offset = ((self.QSFP_BRCM_DIAGNOSTIC_PAGE * 128) + self.QSFP_BRCM_DIAGNOSTIC_STATUS)
                status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                if status is None:
                    self.log(self.LOG_ERROR, "__cable_fw_mcu_abort read eeprom failed")
                    return self.EEPROM_ERROR

                if status[0] == 0:
                    break

                time.sleep(0.001)

            if status[0]:
                self.log(self.LOG_ERROR, "Unable to communicate with NIC MCU")
                return self.ERROR_RW_NIC_FAILED

        # Make sure to clear command first else can have unforseen consequences
        curr_offset = (self.QSFP_BRCM_FW_UPGRADE_PAGE*128)
        dat[0] = 0x00
        if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
            return self.ERROR_WR_EEPROM_FAILED

        # Send destination
        dat[0] = upgrade_info.destination
        if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset + self.QSFP_BRCM_FW_UPGRADE_HEADER_24_31, 1, dat) is False:
            return self.ERROR_WR_EEPROM_FAILED

        # Send Abort request
        dat[0] = (self.FW_CMD_ABORT << 1) | 1
        if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
            return self.ERROR_WR_EEPROM_FAILED

        time.sleep(0.3)

        # Check response status
        for _ in range(100):
            status = self.platform_chassis.get_sfp(self.port).read_eeprom(
                curr_offset + self.QSFP_BRCM_FW_UPGRADE_CMD_STS, 1)
            if status is None:
                return self.EEPROM_ERROR

            if (status[0] & 0x01) == 0:
                req_status = True
                ret_val = self.RR_SUCCESS

                # Set the command request to idle state
                dat[0] = 0x00
                if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                    return self.ERROR_WR_EEPROM_FAILED
                break
            time.sleep(0.001)

        if not req_status:
            # Pull down anyway
            dat[0] = 0x00
            curr_offset = ((self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD)
            if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat) is False:
                return self.ERROR_WR_EEPROM_FAILED

        if not req_status:
            self.log(self.LOG_ERROR, "Abort timeout. No response from MCU")
            self.__handle_error(17)
            return self.ERROR_CMD_TIMEOUT

        return ret_val

    def cable_fw_get_status(self, upgrade_info):
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
            RR_SUCCESS                    : Success
            RR_ERROR                      : Failed
            ERROR_RW_NIC_FAILED           : Unable to communicate with nic MCU
            EEPROM_READ_DATA_INVALID      : Read invalid data
            RR_ERROR_SYSTEM_UNAVAILABLE   : System unavaiable
            ERROR_PLATFORM_NOT_LOADED     : Platform not loaded
            ERROR_PORT_LOCK_TIMEOUT       : Port lock timeout

        """
        ret_val = self.RR_ERROR
        cmd_handle = cmd_handle_s()

        if self.platform_chassis is not None:
            # SEE which MCU it is: Assuming constant pages have been set for each MCU

            if(self.__pre_cmd_check(upgrade_info) == self.RR_SUCCESS):

                cmd_handle.cmd_wr = self.FW_CMD_INFO
                cmd_handle.read_info = 1
                cmd_handle.cmd_rd = self.QSFP_BRCM_FW_UPGRADE_CURRENT_BANK
                cmd_handle.info_len = 26
                ret_val = self.__handle_cmd(upgrade_info, cmd_handle)
                if((ret_val != self.RR_SUCCESS) and (ret_val != self.RR_ERROR_SYSTEM_UNAVAILABLE)):
                    return ret_val

                # Current bank
                upgrade_info.status_info.current_bank = cmd_handle.data_read[0]
                upgrade_info.status_info.next_bank = cmd_handle.data_read[25]

                # Bank 1 minor fw version
                upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor = (
                    cmd_handle.data_read[2] << 8) | cmd_handle.data_read[1]

                # Bank 1 major fw version
                upgrade_info.status_info.bank1_info.image_fw_version.image_version_major = (
                    cmd_handle.data_read[4] << 8) | cmd_handle.data_read[3]

                # Bank 1 minor API version
                upgrade_info.status_info.bank1_info.image_api_version.image_version_minor = (
                    cmd_handle.data_read[6] << 8) | cmd_handle.data_read[5]

                # Bank 1 major API version
                upgrade_info.status_info.bank1_info.image_api_version.image_version_major = (
                    cmd_handle.data_read[8] << 8) | cmd_handle.data_read[7]

                # Bank 1 CRC32
                upgrade_info.status_info.bank1_info.image_crc32 = (cmd_handle.data_read[12] << 24) | (
                    cmd_handle.data_read[11] << 16) | (cmd_handle.data_read[10] << 8) | cmd_handle.data_read[9]
                # Bank 2 minor fw version
                upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor = (
                    cmd_handle.data_read[14] << 8) | cmd_handle.data_read[13]

                # Bank 2 major fw version
                upgrade_info.status_info.bank2_info.image_fw_version.image_version_major = (
                    cmd_handle.data_read[16] << 8) | cmd_handle.data_read[15]

                # Bank 2 minor API version
                upgrade_info.status_info.bank2_info.image_api_version.image_version_minor = (
                    cmd_handle.data_read[18] << 8) | cmd_handle.data_read[17]

                # Bank 2 major API version
                upgrade_info.status_info.bank2_info.image_api_version.image_version_major = (
                    cmd_handle.data_read[20] << 8) | cmd_handle.data_read[19]

                # Bank2 CRC32
                upgrade_info.status_info.bank2_info.image_crc32 = (cmd_handle.data_read[24] << 24) | (
                    cmd_handle.data_read[23] << 16) | (cmd_handle.data_read[22] << 8) | cmd_handle.data_read[21]

            else:
                self.log(self.LOG_ERROR, "MCU not in the right state")

        return ret_val

    def cable_fw_toggle_bcomp(self, upgrade_info):
        """ 
        This API is internally used by activate firmware. Used to activate old FW only.

        Args:
            upgrade_info: MCU details
        """

        ret_val = self.RR_ERROR
        cmd_handle = cmd_handle_s()

        if self.platform_chassis is not None:

            if(self.__pre_cmd_check(upgrade_info) == self.RR_SUCCESS):
                cmd_handle.cmd_wr = self.FW_CMD_SWAP
                ret_val = self.__handle_cmd(upgrade_info, cmd_handle)
                if (ret_val != self.RR_SUCCESS):
                    return ret_val

                # Do reset
                time.sleep(0.3)

                ret_val = self.__cable_fw_mcu_reset(upgrade_info)
                if(ret_val != self.RR_SUCCESS):
                    self.log(self.LOG_ERROR, "cable_fw_mcu_reset failed. ret_val {}".format(ret_val))
                    return self.ERROR_RESET_FAILED

                time.sleep(0.3)
                ret_val = self.RR_SUCCESS

            else:
                self.log(self.LOG_ERROR, "MCU not in the right state")

        return ret_val

    def cable_fw_bank_toggle(self, upgrade_info):
        '''
        This API is internally used by activate firmware

        Args:
            upgrade_info: MCU details
        '''
        ret_val = self.RR_ERROR
        status = 0
        cmd_handle = cmd_handle_s()

        if self.platform_chassis is not None:

            if(self.__pre_cmd_check(upgrade_info) == self.RR_SUCCESS):
                cmd_handle.cmd_wr = self.FW_CMD_SWAP
                ret_val = self.__handle_cmd(upgrade_info, cmd_handle)
                if (ret_val != self.RR_SUCCESS):
                    return ret_val

                # Do reset
                time.sleep(0.3)

                ret_val = self.__cable_fw_mcu_reset(upgrade_info)
                if(ret_val != self.RR_SUCCESS):
                    self.log(self.LOG_ERROR, "cable_fw_mcu_reset failed. ret_val {}".format(ret_val))
                    return self.ERROR_RESET_FAILED

                time.sleep(0.3)

                cmd_handle.cmd_wr = self.FW_CMD_BOOT_STATUS
                cmd_handle.read_info = 1
                cmd_handle.cmd_rd = self.QSFP_BRCM_FW_UPGRADE_BOOT_STATUS
                cmd_handle.info_len = 1
                ret_val = self.__handle_cmd(upgrade_info, cmd_handle)
                if(ret_val != self.RR_SUCCESS):
                    self.log(self.LOG_ERROR, "handle_cmd failed. ret_val {}".format(ret_val))
                    return ret_val

                if upgrade_info.destination == self.NIC_MCU:
                    if cmd_handle.data_read[0] == 0:
                        # Reset went through. Check mux chip status
                        for _ in range(0, 3000):
                            curr_offset = ((self.QSFP_BRCM_DIAGNOSTIC_PAGE*128) + self.QSFP_BRCM_DIAGNOSTIC_STATUS)
                            status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 2)
                            if status is None:
                                return self.EEPROM_ERROR
                            if status[0] == 0:
                                break
                            time.sleep(0.001)

                        if status[0]:
                            self.log(self.LOG_ERROR, "Unable to communicate with MUX chip")
                            return self.RR_ERROR

                        ret_val = self.RR_SUCCESS
                        return ret_val

                    elif cmd_handle.data_read[0] == 1:
                        # RESET ERROR
                        self.log(self.LOG_ERROR, "COLD BOOT reset succeeded but MUX chip failed")
                        ret_val = self.RR_ERROR
                        return ret_val
                    else:
                        # RESET ERROR
                        self.log(self.LOG_ERROR, "COLD BOOT reset failed")
                        ret_val = self.RR_ERROR
                        return ret_val
                else:
                    if cmd_handle.data_read[0] == 0:
                        ret_val = self.RR_SUCCESS
                        return ret_val
                    else:
                        # RESET ERROR
                        self.log(self.LOG_ERROR, "COLD BOOT reset failed")
                        ret_val = self.RR_ERROR
                        return ret_val
            else:
                self.log(self.LOG_ERROR, "MCU not in the right state")

        return ret_val

    def __cable_fw_warm_boot(self, upgrade_info):

        ret_val = self.RR_ERROR
        status = 0
        cmd_handle = cmd_handle_s()

        if self.__pre_cmd_check(upgrade_info) == self.RR_SUCCESS:
            cmd_handle.cmd_wr = self.FW_CMD_WARM_BOOT

            ret_val = self.__handle_cmd(upgrade_info, cmd_handle)
            if ret_val != self.RR_SUCCESS:
                return ret_val
            time.sleep(2)

            cmd_handle.cmd_wr = self.FW_CMD_BOOT_STATUS
            cmd_handle.read_info = 1
            cmd_handle.cmd_rd = self.QSFP_BRCM_FW_UPGRADE_BOOT_STATUS
            cmd_handle.info_len = 1
            ret_val = self.__handle_cmd(upgrade_info, cmd_handle)
            if(ret_val != self.RR_SUCCESS):
                return ret_val

            if cmd_handle.data_read[0] == 0:
                # Reset went through. Check mux chip status
                for _ in range(0, 3000):
                    curr_offset = ((self.QSFP_BRCM_DIAGNOSTIC_PAGE*128) + self.QSFP_BRCM_DIAGNOSTIC_STATUS)
                    status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                    if status is None:
                        self.log(self.LOG_ERROR, "__cmd_handle read eeprom failed")
                        return self.EEPROM_ERROR

                    if status[0] == 0:
                        break
                    time.sleep(0.001)

                if status[0]:
                    self.log(self.LOG_ERROR, "Unable to communicate with MUX chip")
                    return self.RR_ERROR

                ret_val = self.RR_SUCCESS
                return ret_val

            elif cmd_handle.data_read[0] == 1:
                # RESET ERROR
                self.log(self.LOG_ERROR, "WARM BOOT reset succeeded but MUX chip failed")
                ret_val = self.RR_ERROR
                return ret_val
            else:
                # RESET ERROR
                self.log(self.LOG_ERROR, "WARM BOOT reset failed")
                ret_val = self.RR_ERROR
                return ret_val
        else:
            self.log(self.LOG_ERROR, "MCU not in the right state")

        return ret_val

    def __handle_cmd(self, upgrade_info, cmd_handle):

        ret_val = self.RR_ERROR
        req_status = False
        dat = bytearray(100)
        info_stat = 0
        status = 0
        QSFP_PAGE_OFFSET = self.QSFP_BRCM_FW_UPGRADE_PAGE * 128

        dat[0] = 0x00
        curr_offset = ((self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD)
        result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat)
        if result is False:
            return self.ERROR_WRITE_EEPROM_FAILED

        # Send destination
        dat[0] = upgrade_info.destination
        curr_offset = ((self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_HEADER_24_31)
        result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat)
        if result is False:
            return self.ERROR_WRITE_EEPROM_FAILED

        # Send command request
        dat[0] = (cmd_handle.cmd_wr << 1) | 1
        curr_offset = ((self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD)
        result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat)
        if result is False:
            return self.ERROR_WRITE_EEPROM_FAILED

        # Delay reading status as this can block during swap
        time.sleep(0.1)
        # time.sleep(1)

        # First check if any errors
        for _ in range(0, 100):
            curr_offset = ((self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_CMD_STS)
            status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            if status is None:
                self.log(self.LOG_ERROR, "__cmd_handle read eeprom failed")
                return self.EEPROM_ERROR
            if status[0] & 0x01:
                if (((status[0] & 0xFC) == (self.FW_UP_SUCCESS << 2)) or ((status[0] & 0xFC) == (self.FW_UP_IN_PROGRESS << 2))):
                    if((status[0] & 0xFC) == (self.FW_UP_IN_PROGRESS << 2)):
                        info_stat = 1

                    if cmd_handle.read_info == 1:
                        curr_offset = (self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_1*128) + cmd_handle.cmd_rd
                        cmd_handle.data_read = self.platform_chassis.get_sfp(
                            self.port).read_eeprom(curr_offset, cmd_handle.info_len)
                        if cmd_handle.data_read is None:
                            self.log(self.LOG_ERROR, "__cmd_handle read eeprom failed")
                            return self.EEPROM_ERROR
                    req_status = True
                    break
                else:
                    self.log(self.LOG_ERROR, "CMD {} failed".format(cmd_handle.cmd_wr))
                    self.__handle_error_abort(upgrade_info, status[0])
                    return ret_val
            time.sleep(0.001)

        if req_status:
            req_status = False
            # set the command request to idle state
            self.log(self.LOG_DEBUG, "set the command request to idle state ")
            dat[0] = 0x00
            if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                return self.ERROR_WR_EEPROM_FAILED

            time.sleep(0.3)

            # wait for mcu response to be pulled down
            self.log(self.LOG_DEBUG, "wait for mcu response to be pulled down ")
            for _ in range(100):
                status = self.__util_read_eeprom(
                    (QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "__handle_cmd")
                if status is None:
                    self.log(self.LOG_ERROR, "__handle_cmd: read_eeprom failed")
                    return self.EEPROM_ERROR

                if (status[0] & 0x01) == 0:
                    req_status = True
                    break

                time.sleep(0.001)

            if not req_status:
                # Timeout, no response to pull down
                self.log(self.LOG_ERROR, "Timeout waiting pull down")
                self.__handle_error_abort(upgrade_info, 1)
                return ret_val

            elif info_stat == 1:
                ret_val = self.RR_ERROR_SYSTEM_UNAVAILABLE
                return ret_val
            else:
                ret_val = self.RR_SUCCESS
                return ret_val
        else:
            # Timeout, no response to pull down
            self.log(self.LOG_ERROR, "Timeout waiting for cmd {} status".format(cmd_handle.cmd_wr))
            self.__handle_error_abort(upgrade_info, 1)
            return ret_val

    def parse_image(self, upgrade_head, destination, fwfile):

        File_seek = 0
        image_compressed = 0
        image_offset = 0
        fw_up_buff = array.array('I', [])

        for i in range(self.MUX_FW_IMG_SIZE):
            fw_up_buff.append(0)

        file1 = open(fwfile, 'rb')
        if file1 is None:
            self.log(self.LOG_ERROR, "File {} failed to open".format(fwfile))
            return self.RR_ERROR

        if (destination == self.TOR_MCU_SELF) or (destination == self.TOR_MCU_PEER):
            # Check TOR current bank to find which TOR image to download
            upgrade_head.cable_up_info.destination = destination
            if (self.cable_fw_get_status(upgrade_head.cable_up_info) != self.RR_SUCCESS):
                file1.close()
                return self.RR_ERROR
            if upgrade_head.cable_up_info.status_info.current_bank == 1:
                # Select TOR bank 2 image
                # First read TOR bank 1 image header to find header location of TOR bank2 image header
                file1.seek(image_offset + 0x10)
                image_compressed = struct.unpack('I', file1.read(4))[0]
                if image_compressed:
                    # Read compressed image size
                    File_seek = struct.unpack('I', file1.read(4))[0]
                    file1.seek(image_offset)
                else:
                    # Read image size
                    file1.seek(image_offset)
                    File_seek = struct.unpack('I', file1.read(4))[0]
                # Next set TOR bank2 image header location
                File_seek += (image_offset + 0x28)
            else:
                File_seek = image_offset
            # Parse TOR image now
            file1.seek(File_seek)
            upgrade_head.cable_up_info.image_info.image_size = struct.unpack('I', file1.read(4))[0]

            fw_version_array = array.array('I', [])
            for i in range(self.FW_IMG_INFO_SIZE):
                if i < 4:
                    byte_val = file1.read(2)
                    fw_version_array.append(0)
                    fw_version_array[i] = struct.unpack('H', byte_val)[0]
                else:
                    byte_val = file1.read(4)
                    fw_version_array.append(0)
                    fw_version_array[i] = struct.unpack('I', byte_val)[0]
                    break

            upgrade_head.compression = struct.unpack('I', file1.read(4))[0]
            upgrade_head.compressed_size = struct.unpack('I', file1.read(4))[0]
            upgrade_head.compressed_crc32 = struct.unpack('I', file1.read(4))[0]
            upgrade_head.add_size = struct.unpack('I', file1.read(4))[0]
            upgrade_head.add_crc32 = struct.unpack('I', file1.read(4))[0]
            upgrade_head.header_crc32 = struct.unpack('I', file1.read(4))[0]

            for i in range(upgrade_head.cable_up_info.image_info.image_size):
                byte_val = file1.read(4)
                if len(byte_val) == 4:
                    fw_up_buff[i] = struct.unpack('I', byte_val)[0]

            upgrade_head.cable_up_info.image_info.image_fw_version.image_version_major = fw_version_array[1]
            upgrade_head.cable_up_info.image_info.image_fw_version.image_version_minor = fw_version_array[0]
            upgrade_head.cable_up_info.image_info.image_api_version.image_version_minor = fw_version_array[2]
            upgrade_head.cable_up_info.image_info.image_api_version.image_version_major = fw_version_array[3]
            upgrade_head.cable_up_info.image_info.image_crc32 = fw_version_array[4]
            upgrade_head.cable_up_info.image_info.image_ptr = fw_up_buff

            if destination == self.TOR_MCU_SELF:
                upgrade_head.cable_up_info.destination = self.TOR_MCU_SELF
            else:
                upgrade_head.cable_up_info.destination = self.TOR_MCU_PEER

        elif destination == self.NIC_MCU:
            # Parse NIC image
            # Seek to location of NIC bank1 image
            file1.seek(0x10)
            image_compressed = struct.unpack('I', file1.read(4))[0]
            if image_compressed:
                # Read compressed image size
                image_offset = struct.unpack('I', file1.read(4))[0]
                file1.seek(0)
            else:
                # Read image size
                file1.seek(0)
                image_offset = struct.unpack('I', file1.read(4))[0]

            image_offset += 0x28
            # Seek to TOR bank2 image
            file1.seek(image_offset)
            # Read TOR bank 2 image header to find header location of NIC bank1 image header
            file1.seek((image_offset + 0x10))
            image_compressed = struct.unpack('I', file1.read(4))[0]
            if image_compressed:
                # Read compressed image size
                File_seek = struct.unpack('I', file1.read(4))[0]
                file1.seek(image_offset)
            else:
                # Read image size
                file1.seek(image_offset)
                File_seek = struct.unpack('I', file1.read(4))[0]

            # Seek to NIC bank1 image
            File_seek += (image_offset + 0x28)
            file1.seek(File_seek)
            image_offset = File_seek

            # Check NIC current bank to find which NIC image to download
            upgrade_head.cable_up_info.destination = destination
            if (self.cable_fw_get_status(upgrade_head.cable_up_info) != self.RR_SUCCESS):
                file1.close()
                return self.RR_ERROR

            if upgrade_head.cable_up_info.status_info.current_bank == 1:
                # Select NIC bank 2 image
                # First read NIC bank 1 image header to find header location of NIC bank2 image header
                file1.seek((image_offset + 0x10))
                image_compressed = struct.unpack('I', file1.read(4))[0]

                if image_compressed:
                    # Read compressed image size
                    File_seek = struct.unpack('I', file1.read(4))[0]
                    file1.seek(image_offset)
                else:
                    # Read image size
                    file1.seek(image_offset)
                    File_seek = struct.unpack('I', file1.read(4))[0]

                # Next set NIC bank2 image header location
                File_seek += (image_offset + 0x28)
            else:
                File_seek = image_offset

            file1.seek(File_seek)
            upgrade_head.cable_up_info.image_info.image_size = struct.unpack('I', file1.read(4))[0]

            fw_version_array = array.array('I', [])
            for i in range(self.FW_IMG_INFO_SIZE):
                if i < 4:
                    byte_val = file1.read(2)
                    fw_version_array.append(0)
                    fw_version_array[i] = struct.unpack('H', byte_val)[0]
                else:
                    byte_val = file1.read(4)
                    fw_version_array.append(0)
                    fw_version_array[i] = struct.unpack('I', byte_val)[0]
                    break

            upgrade_head.compression = struct.unpack('I', file1.read(4))[0]
            upgrade_head.compressed_size = struct.unpack('I', file1.read(4))[0]
            upgrade_head.compressed_crc32 = struct.unpack('I', file1.read(4))[0]
            upgrade_head.add_size = struct.unpack('I', file1.read(4))[0]
            upgrade_head.add_crc32 = struct.unpack('I', file1.read(4))[0]
            upgrade_head.header_crc32 = struct.unpack('I', file1.read(4))[0]

            upgrade_head.cable_up_info.destination = self.NIC_MCU

            for i in range(upgrade_head.cable_up_info.image_info.image_size):
                byte_val = file1.read(4)
                if len(byte_val) == 4:
                    fw_up_buff[i] = struct.unpack('I', byte_val)[0]

            upgrade_head.cable_up_info.image_info.image_fw_version.image_version_major = fw_version_array[1]
            upgrade_head.cable_up_info.image_info.image_fw_version.image_version_minor = fw_version_array[0]
            upgrade_head.cable_up_info.image_info.image_api_version.image_version_minor = fw_version_array[2]
            upgrade_head.cable_up_info.image_info.image_api_version.image_version_major = fw_version_array[3]
            upgrade_head.cable_up_info.image_info.image_crc32 = fw_version_array[4]
            upgrade_head.cable_up_info.image_info.image_ptr = fw_up_buff
            upgrade_head.cable_up_info.destination = self.NIC_MCU

        elif destination == self.MUX_CHIP:
            # Parse MUX CHIP image
            # Seek to location of NIC bank1 image
            file1.seek(0x10)
            image_compressed = struct.unpack('I', file1.read(4))[0]
            if image_compressed:
                # Read compressed image size
                image_offset = struct.unpack('I', file1.read(4))[0]
                file1.seek(0)
            else:
                # Read image size
                file1.seek(0)
                image_offset = struct.unpack('I', file1.read(4))[0]

            image_offset += 0x28
            # Seek to TOR bank2 image
            file1.seek(image_offset)

            # Read TOR bank 2 image header to find header location of NIC bank1 image header
            file1.seek(image_offset + 0x10)
            image_compressed = struct.unpack('I', file1.read(4))[0]

            if image_compressed:
                # Read compressed image size
                File_seek = struct.unpack('I', file1.read(4))[0]
                file1.seek(image_offset)
            else:
                # Read image size
                file1.seek(image_offset)
                File_seek = struct.unpack('I', file1.read(4))[0]

            # Seek to NIC bank1 image
            File_seek += (image_offset + 0x28)
            file1.seek(File_seek)
            image_offset = File_seek

            # Read NIC bank 1 image header to find header location of N
            file1.seek(image_offset + 0x10)
            image_compressed = struct.unpack('I', file1.read(4))[0]
            if image_compressed:
                # Read compressed image size
                File_seek = struct.unpack('I', file1.read(4))[0]
                file1.seek(image_offset)
            else:
                # Read image size
                file1.seek(image_offset)
                File_seek = struct.unpack('I', file1.read(4))[0]

            # Next set NIC bank2 image header location
            File_seek += (image_offset + 0x28)
            image_offset = File_seek

            file1.seek(File_seek + 0x10)
            image_compressed = struct.unpack('I', file1.read(4))[0]

            if image_compressed:
                # Read compressed image size
                File_seek = struct.unpack('I', file1.read(4))[0]
                file1.seek(image_offset)
            else:
                # Read image size
                file1.seek(image_offset)
                File_seek = struct.unpack('I', file1.read(4))[0]

            File_seek += (image_offset + 0x28)
            file1.seek(File_seek)
            image_offset = File_seek

            upgrade_head.cable_up_info.image_info.image_size = struct.unpack('I', file1.read(4))[0]

            fw_version_array = array.array('I', [])
            for i in range(self.FW_IMG_INFO_SIZE):
                if i < 4:
                    byte_val = file1.read(2)
                    fw_version_array.append(0)
                    fw_version_array[i] = struct.unpack('H', byte_val)[0]
                else:
                    byte_val = file1.read(4)
                    fw_version_array.append(0)
                    fw_version_array[i] = struct.unpack('I', byte_val)[0]
                    break

            upgrade_head.compression = struct.unpack('I', file1.read(4))[0]
            upgrade_head.compressed_size = struct.unpack('I', file1.read(4))[0]
            upgrade_head.compressed_crc32 = struct.unpack('I', file1.read(4))[0]
            upgrade_head.add_size = struct.unpack('I', file1.read(4))[0]
            upgrade_head.add_crc32 = struct.unpack('I', file1.read(4))[0]
            upgrade_head.header_crc32 = struct.unpack('I', file1.read(4))[0]

            upgrade_head.cable_up_info.destination = self.MUX_CHIP

            for i in range(upgrade_head.cable_up_info.image_info.image_size):
                byte_val = file1.read(4)
                if len(byte_val) == 4:
                    fw_up_buff[i] = struct.unpack('I', byte_val)[0]

            upgrade_head.cable_up_info.image_info.image_fw_version.image_version_major = fw_version_array[1]
            upgrade_head.cable_up_info.image_info.image_fw_version.image_version_minor = fw_version_array[0]
            upgrade_head.cable_up_info.image_info.image_api_version.image_version_minor = fw_version_array[2]
            upgrade_head.cable_up_info.image_info.image_api_version.image_version_major = fw_version_array[3]
            upgrade_head.cable_up_info.image_info.image_crc32 = fw_version_array[4]
            upgrade_head.cable_up_info.image_info.image_ptr = fw_up_buff

        else:
            file1.close()
            return self.RR_ERROR

        file1.close()
        return self.RR_SUCCESS

    def __cable_fw_mcu_reset(self, upgrade_info):

        ret_val = self.RR_ERROR
        dat = bytearray(30)
        status = 0
        req_status = False

        if (self.__pre_cmd_check(upgrade_info) == self.RR_SUCCESS):
            # If TOR MCU, reset self
            if(upgrade_info.destination == self.TOR_MCU_SELF):
                curr_offset = ((0x00*128) + 0x5D)
                dat = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                if dat is None:
                    return self.EEPROM_ERROR
                dat[0] |= 0x80
                curr_offset = ((0x00*128) + 0x5D)
                if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat) is False:
                    return self.ERROR_WR_EEPROM_FAILED

                time.sleep(1)

                # Check response status
                for _ in range(0, 2000):
                    curr_offset = ((0x00*128) + 0x5D)
                    status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                    if status is None:
                        return self.EEPROM_ERROR

                    if (status[0] & 0x80) == 0:
                        ret_val = self.RR_SUCCESS
                        return ret_val
                    time.sleep(0.001)

            elif((upgrade_info.destination == self.TOR_MCU_PEER) or (upgrade_info.destination == self.NIC_MCU)):
                if(upgrade_info.destination == self.TOR_MCU_PEER):
                    read_side = self.get_read_side()
                    if (read_side == self.TARGET_UNKNOWN):
                        self.log(self.LOG_ERROR, "ERROR: get_read_side Failed!")
                        return None
                    dat[0] = 0x02 if read_side == 0x01 else 0x01
                else:
                    dat[0] = 0x04
                curr_offset = ((0xFD*128) + 0xB8)
                if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat) is False:
                    return self.ERROR_WR_EEPROM_FAILED

                if(upgrade_info.destination == self.NIC_MCU):
                    # MUST WAIT FOR mux CHIP TO BOOT
                    time.sleep(7.5)

                # Check response status
                for _ in range(0, 2000):
                    curr_offset = ((0xFD*128) + 0xB8)
                    status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                    if status is None:
                        return self.EEPROM_ERROR

                    if ((status[0] & 0x01) == 0):
                        ret_val = self.RR_SUCCESS
                        return ret_val
                    time.sleep(0.001)

            # Should not be here unless no response
            if not req_status:
                # ERROR
                return ret_val

        else:
            self.log(self.LOG_ERROR, "MCU not in the right state")

        return ret_val

    def __pre_cmd_check(self, upgrade_info):

        dat = bytearray(30)
        QSFP_PAGE_OFFSET = self.QSFP_BRCM_FW_UPGRADE_PAGE * 128

        read_side = self.get_read_side()
        if read_side == self.TARGET_UNKNOWN:
            self.log(self.LOG_ERROR, "ERROR: get_read_side Failed!")
            return self.RR_ERROR

        #ts = datetime.utcnow()
        # Make sure TOR to NIC MCU communication is alive
        if upgrade_info.destination == self.NIC_MCU and ((read_side == 0x02) or (read_side == 0x01)):
            # Since we are running from TOR side, make sure no flush is on going
            for _ in range(0, 3000):
                curr_offset = ((self.QSFP_BRCM_DIAGNOSTIC_PAGE*128) + self.QSFP_BRCM_DIAGNOSTIC_STATUS)
                status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                if status is None:
                    self.log(self.LOG_ERROR, "__pre_cmd_check read eeprom failed")
                    return self.EEPROM_ERROR
                if status[0] == 0:
                    break
                time.sleep(0.001)

            if status[0]:
                self.log(self.LOG_ERROR, "Unable to communicate with NIC MCU")
                return self.ERROR_RW_NIC_FAILED
            #ts = self.log_timestamp(ts,"TOR to NIC MCU communication is alive")

        # read cable command and status offsets
        self.log(self.LOG_DEBUG, "read cable command and status offsets")
        result = self.__util_read_eeprom((QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD), 2, "pre_cmd_check")
        if result is None:
            return self.EEPROM_ERROR
        if result != self.EEPROM_READ_DATA_INVALID:
            dat[0] = result[0]
            dat[1] = result[1]

        if ((dat[0] & 0x01) != 0) or ((dat[1] & 0x01) != 0):
            self.log(self.LOG_DEBUG, "MCU not in the right state. Sending abort")
            ret_val = self.__cable_fw_mcu_abort(upgrade_info)
            if ret_val != self.RR_SUCCESS:
                self.log(self.LOG_ERROR, "MCU abort failed")
                return ret_val

            time.sleep(0.001)
            result = self.__util_read_eeprom(
                (QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD), 2, "pre_cmd_check")
            if result is None:
                return self.EEPROM_ERROR

        result = self.__util_read_eeprom((QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD), 2, "pre_cmd_check")
        if result is None:
            return self.EEPROM_ERROR
        if result != self.EEPROM_READ_DATA_INVALID:
            dat[0] = result[0]
            dat[1] = result[1]
        if ((dat[0] & 0x01) == 0) and ((dat[1] & 0x01) == 0):
            ret_val = self.RR_SUCCESS
        else:
            ret_val = self.RR_ERROR

        return ret_val

    def __cable_fw_upgrade(self, upgrade_head):
        """
        This function used internally to upgrade the firmware of TOR, NIC and MUX
        physical_port:
            an Integer, the actual physical port connected to a Y cable

        upgrade_info:
            an object of type cable_upgrade_info_s, The destination, versions
            and image_buffer must be set

        Returns
            RR_SUCCESS             Success
            RR_ERROR               Failures
            ERROR_RW_NIC_FAILED    Unable to comminicate NIC MCU
            ERROR_INVALID_TARGET   Wrong destination
            ERROR_CMD_TIMEOUT      Command Time out
        """
        ret_val = self.RR_ERROR
        dat = bytearray(128)
        status = 0
        req_status = False
        i = 0
        tmp_cnt = 0
        tmp_print = 0
        QSFP_PAGE_OFFSET = self.QSFP_BRCM_FW_UPGRADE_PAGE * 128
        start_tstamp = datetime.utcnow()

        if(self.__pre_cmd_check(upgrade_head.cable_up_info) == self.RR_SUCCESS):
            # START CMD ============================================
            # Debug prints
            self.log(self.LOG_DEBUG, "Starting firmware upgrade to {}".format("TOR MCU SELF"
                                                                              if upgrade_head.cable_up_info.destination == self.TOR_MCU_SELF
                                                                              else "TOR MCU PEER" if upgrade_head.cable_up_info.destination == self.TOR_MCU_PEER
                                                                              else "NIC MCU" if upgrade_head.cable_up_info.destination == self.NIC_MCU else "MUX_CHIP"))

            self.log(self.LOG_DEBUG, "FW Version minor: {}".format(
                hex(upgrade_head.cable_up_info.image_info.image_fw_version.image_version_minor)))
            self.log(self.LOG_DEBUG, "FW Version major: {}".format(
                hex(upgrade_head.cable_up_info.image_info.image_fw_version.image_version_major)))
            if (upgrade_head.cable_up_info.destination == self.TOR_MCU_SELF or upgrade_head.cable_up_info.destination == self.TOR_MCU_PEER):
                self.log(self.LOG_DEBUG, "API version minor: {}".format(
                    hex(upgrade_head.cable_up_info.image_info.image_api_version.image_version_minor)))
                self.log(self.LOG_DEBUG, "API version major: {}".format(
                    hex(upgrade_head.cable_up_info.image_info.image_api_version.image_version_major)))
            self.log(self.LOG_DEBUG, "CRC32 : {}".format(hex(upgrade_head.cable_up_info.image_info.image_crc32)))
            self.log(self.LOG_DEBUG, "Image size : {}".format(hex(upgrade_head.cable_up_info.image_info.image_size)))

            ts = datetime.utcnow()
            # Send image header
            self.log(self.LOG_INFO, "send image header")
            dat[0] = upgrade_head.cable_up_info.image_info.image_size & 0xff
            dat[1] = (upgrade_head.cable_up_info.image_info.image_size >> 8) & 0xFF
            dat[2] = (upgrade_head.cable_up_info.image_info.image_size >> 16) & 0xFF
            dat[3] = upgrade_head.cable_up_info.destination
            dat[4] = upgrade_head.cable_up_info.image_info.image_fw_version.image_version_minor & 0xFF
            dat[5] = (upgrade_head.cable_up_info.image_info.image_fw_version.image_version_minor >> 8) & 0xFF
            dat[6] = upgrade_head.cable_up_info.image_info.image_fw_version.image_version_major & 0xFF
            dat[7] = (upgrade_head.cable_up_info.image_info.image_fw_version.image_version_major >> 8) & 0xFF
            dat[8] = upgrade_head.cable_up_info.image_info.image_api_version.image_version_minor & 0xFF
            dat[9] = (upgrade_head.cable_up_info.image_info.image_api_version.image_version_minor >> 8) & 0xFF
            dat[10] = upgrade_head.cable_up_info.image_info.image_api_version.image_version_major & 0xFF
            dat[11] = (upgrade_head.cable_up_info.image_info.image_api_version.image_version_major >> 8) & 0xFF
            dat[12] = upgrade_head.cable_up_info.image_info.image_crc32 & 0xFF
            dat[13] = (upgrade_head.cable_up_info.image_info.image_crc32 >> 8) & 0xFF
            dat[14] = (upgrade_head.cable_up_info.image_info.image_crc32 >> 16) & 0xFF
            dat[15] = (upgrade_head.cable_up_info.image_info.image_crc32 >> 24) & 0xFF
            dat[16] = self.FW_UP_PACKET_SIZE
            dat[17] = self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_1

            if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_HEADER_0_7, 18, dat) is False:
                return self.ERROR_WR_EEPROM_FAILED

            ts = self.log_timestamp(ts, "Image header sent")

            # Write compression header
            dat[0] = (upgrade_head.compression & 0xFF)
            dat[1] = (upgrade_head.compressed_size & 0xFF)
            dat[2] = ((upgrade_head.compressed_size >> 8) & 0xFF)
            dat[3] = ((upgrade_head.compressed_size >> 16) & 0xFF)
            dat[4] = ((upgrade_head.compressed_size >> 24) & 0xFF)
            dat[5] = (upgrade_head.compressed_crc32 & 0xFF)
            dat[6] = ((upgrade_head.compressed_crc32 >> 8) & 0xFF)
            dat[7] = ((upgrade_head.compressed_crc32 >> 16) & 0xFF)
            dat[8] = ((upgrade_head.compressed_crc32 >> 24) & 0xFF)
            dat[9] = (upgrade_head.add_size & 0xFF)
            dat[10] = ((upgrade_head.add_size >> 8) & 0xFF)
            dat[11] = ((upgrade_head.add_size >> 16) & 0xFF)
            dat[12] = ((upgrade_head.add_size >> 24) & 0xFF)
            dat[13] = (upgrade_head.add_crc32 & 0xFF)
            dat[14] = ((upgrade_head.add_crc32 >> 8) & 0xFF)
            dat[15] = ((upgrade_head.add_crc32 >> 16) & 0xFF)
            dat[16] = ((upgrade_head.add_crc32 >> 24) & 0xFF)

            # Header CRC
            dat[17] = (upgrade_head.header_crc32 & 0xFF)
            dat[18] = ((upgrade_head.header_crc32 >> 8) & 0xFF)
            dat[19] = ((upgrade_head.header_crc32 >> 16) & 0xFF)
            dat[20] = ((upgrade_head.header_crc32 >> 24) & 0xFF)

            curr_offset = ((self.QSFP_BRCM_FW_UPGRADE_PAGE*128) + self.QSFP_BRCM_FW_UPGRADE_COMP_SET)
            if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 21, dat) is False:
                return self.ERROR_WR_EEPROM_FAILED
            ts = self.log_timestamp(ts, "compression  header sent")

            # Send request firmware upgrad to START
            self.log(self.LOG_INFO, "START ERASING")

            dat[0] = (self.FW_CMD_START << 1) | 1
            if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                return self.ERROR_WR_EEPROM_FAILED

            time.sleep(3.5)
            ts = self.log_timestamp(ts, "Erase command sent")

            # Check response status
            self.log(self.LOG_DEBUG, "check MCU ready status")
            for i in range(3000):
                status = self.__util_read_eeprom(
                    (self.QSFP_BRCM_FW_UPGRADE_PAGE * 128 + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                if status is None:
                    return self.EEPROM_ERROR
                if status[0] & 0x01:
                    if (status[0] & 0xFC) == (self.FW_UP_SUCCESS << 2):
                        self.log(self.LOG_DEBUG, "MCU is Ready")
                        req_status = True
                        break
                    else:
                        if (status[0] & 0xFC) == (self.FW_UP_IN_PROGRESS << 2):
                            ret_val = self.RR_ERROR_SYSTEM_UNAVAILABLE
                            self.log(self.LOG_WARN, "System Unavailable/busy...")
                            #self.__handle_error_abort(upgrade_head.cable_up_info, 1)
                            return ret_val

                time.sleep(0.001)

            ts = self.log_timestamp(ts, "MCU ready check done")

            # if MCU is ready
            if req_status:
                req_status = False
                # set the command request to idle state
                self.log(self.LOG_DEBUG, "set the command request to idle state ")
                dat[0] = 0x00
                if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                    return self.ERROR_WR_EEPROM_FAILED

                # wait for mcu response to be pulled down
                self.log(self.LOG_DEBUG, "wait for mcu response to be pulled down ")
                for _ in range(100):
                    status = self.__util_read_eeprom(
                        (QSFP_PAGE_OFFSET + self. QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                    if status is None:
                        return self.EEPROM_ERROR
                    if (status[0] & 0x01) == 0:
                        req_status = True
                        break

                    time.sleep(0.001)

                if not req_status:
                    self.log(self.LOG_ERROR, "Timeout ")
                    self.__handle_error_abort(upgrade_head.cable_up_info, 2)
                    return ret_val
                ts = self.log_timestamp(ts, "MCU response pulled down")

            else:
                self.log(self.LOG_ERROR, "ERROR MCU is not ready ")
                self.__handle_error_abort(upgrade_head.cable_up_info, 17)
                return ret_val

            # if MCU response pulled down
            if req_status:
                # TRANSFER command
                self.log(self.LOG_INFO, "FW image transfer start ")
                tmp_image_ptr = upgrade_head.cable_up_info.image_info.image_ptr
                remain_page_size = 0
                image_to_page_size = 0
                count = 0
                page_loc = self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_1
                if((upgrade_head.compression & 0xFF)):
                    tmp_image_size = upgrade_head.compressed_size
                else:
                    tmp_image_size = upgrade_head.cable_up_info.image_info.image_size

                remain_page_size = tmp_image_size % self.FW_UP_PACKET_SIZE
                image_to_page_size = tmp_image_size - remain_page_size

                # MCU is now ready for firmware upgrade, Start the loop to transfre the data
                self.log(self.LOG_DEBUG, "MCU is now ready for firmware upgrade, Start the loop to transfer the data")
                dat[0] = self.FW_UP_PACKET_SIZE
                dat[1] = page_loc
                if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_PACKET_SIZE, 2, dat) is False:
                    return self.ERROR_WR_EEPROM_FAILED
                self.log(self.LOG_DEBUG, "Writing packet to page_loc {} fw_up_packet_size : {}".format(
                    page_loc, self.FW_UP_PACKET_SIZE))

                for i in range(0, self.FW_UP_PACKET_SIZE, 4):
                    dat[0 + i] = tmp_image_ptr[count] & 0xFF
                    dat[1 + i] = (tmp_image_ptr[count] >> 8) & 0xFF
                    dat[2 + i] = (tmp_image_ptr[count] >> 16) & 0xFF
                    dat[3 + i] = (tmp_image_ptr[count] >> 24) & 0xFF
                    count += 1

                if self.platform_chassis.get_sfp(self.port).write_eeprom((page_loc*128) + self.QSFP_BRCM_FW_UPGRADE_DATA_START, self.FW_UP_PACKET_SIZE, dat) is False:
                    return self.ERROR_WR_EEPROM_FAILED
                ts = self.log_timestamp(ts, "First packet written")

                self.log(self.LOG_INFO, "TRANSFERING remaining packets..")

                dat[0] = (self.FW_CMD_TRANSFER << 1) | 1
                if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                    return self.ERROR_WR_EEPROM_FAILED

                # prepare and send remaining packets
                for _ in range(self.FW_UP_PACKET_SIZE, image_to_page_size, self.FW_UP_PACKET_SIZE):
                    req_status = False

                    # Toggle data page_loc
                    page_loc = self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_1 if(
                        page_loc == self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_2) else self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_2

                    # prepare packet data
                    for i in range(0, self.FW_UP_PACKET_SIZE, 4):
                        dat[0 + i] = tmp_image_ptr[count] & 0xFF
                        dat[1 + i] = (tmp_image_ptr[count] >> 8) & 0xFF
                        dat[2 + i] = (tmp_image_ptr[count] >> 16) & 0xFF
                        dat[3 + i] = (tmp_image_ptr[count] >> 24) & 0xFF
                        count += 1

                    # write packet
                    if self.platform_chassis.get_sfp(self.port).write_eeprom((page_loc*128) + self.QSFP_BRCM_FW_UPGRADE_DATA_START, self.FW_UP_PACKET_SIZE, dat) is False:
                        return self.ERROR_WR_EEPROM_FAILED

                    # Check response status for previous packet
                    for i in range(500):
                        status = self.__util_read_eeprom(
                            (QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                        if status is None:
                            return self.EEPROM_ERROR
                        if status[0] & 0x01:
                            if(status[0] & 0xFC) == (self.FW_UP_SUCCESS << 2):
                                req_status = True
                                tmp_cnt += self.FW_UP_PACKET_SIZE
                                if tmp_cnt >= (tmp_image_size / 100):
                                    tmp_cnt = 0
                                    tmp_print += 1
                                    #_logger.log_info("  {}%".format(tmp_print),CONSOLE_PRINT)
                                    print("  {}% (tmp_cnt {})".format(tmp_print, tmp_cnt))
                                break
                            else:
                                # ERROR
                                self.log(self.LOG_ERROR, "ERROR: TRANSFER error {}".format((status[0] & 0xFC) >> 2))
                                self.__handle_error_abort(upgrade_head.cable_up_info, 3)
                                return ret_val

                        time.sleep(0.001)

                    # if previous packet sent successfully
                    if req_status:
                        req_status = False

                        # Set the command request to idle state
                        dat[0] = 0x00
                        if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                            return self.ERROR_WR_EEPROM_FAILED

                        # wait for mcu response to be pulled down
                        for i in range(1000):
                            status = self.__util_read_eeprom(
                                (QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                            if status is None:
                                return self.EEPROM_ERROR
                            if(status[0] & 0x01) == 0:
                                # Previous packet is OK
                                # Set MCU write the next packet
                                dat[0] = self.FW_UP_PACKET_SIZE
                                dat[1] = page_loc
                                if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_PACKET_SIZE, 2, dat) is False:
                                    return self.ERROR_WR_EEPROM_FAILED

                                dat[0] = (self.FW_CMD_TRANSFER << 1) | 1
                                if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                                    return self.ERROR_WR_EEPROM_FAILED
                                req_status = True
                                break
                            time.sleep(0.001)

                        if not req_status:
                            # Time out how to handle
                            self.log(self.LOG_ERROR, "cable_fw_upgrade : handle erro abort1")
                            self.__handle_error_abort(upgrade_head.cable_up_info, 4)
                            return ret_val

                    else:
                        # Check if error status or timeout
                        if not req_status:
                            self.log(self.LOG_ERROR, "ERROR: TRANSFER timed out")

                        self.__handle_error_abort(upgrade_head.cable_up_info, 5)
                        return ret_val
                ts = self.log_timestamp(ts, "All packets written... Check response for last page")

                # Transfer remaining bytes if less than a page
                if remain_page_size:
                    req_status = False

                    # Toggle data page_loc
                    page_loc = self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_1 if(
                        page_loc == self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_2) else self.QSFP_BRCM_FW_UPGRADE_DATA_PAGE_2
                    j = 0
                    for i in range(remain_page_size):
                        dat[i] = ((tmp_image_ptr[count] >> (8 * j)) & 0xFF)
                        j += 1
                        if j >= 4:
                            count += 1
                            j = 0
                    # write packet
                    if self.platform_chassis.get_sfp(self.port).write_eeprom(((page_loc*128) + self.QSFP_BRCM_FW_UPGRADE_DATA_START), remain_page_size, dat) is False:
                        return self.ERROR_WR_EEPROM_FAILED

                    # Check response status for previous packet
                    for i in range(500):
                        status = self.__util_read_eeprom(
                            (QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                        if status is None:
                            return self.EEPROM_ERROR
                        if status[0] & 0x01:
                            if(status[0] & 0xFC) == (self.FW_UP_SUCCESS << 2):
                                req_status = True
                                tmp_cnt += self.FW_UP_PACKET_SIZE
                                if tmp_cnt >= (upgrade_head.cable_up_info.image_info.image_size / 100):
                                    tmp_cnt = 0
                                    tmp_print += 1
                                    #_logger.log_info("  {}%".format(tmp_print),CONSOLE_PRINT)
                                    print("  {}% (tmp_cnt: {})".format(tmp_print, tmp_cnt))
                                break
                            else:
                                # ERROR
                                self.log(self.LOG_ERROR, "ERROR: TRANSFER error {}".format((status[0] & 0xFC) >> 2))
                                self.__handle_error_abort(upgrade_head.cable_up_info, 3)
                                return ret_val

                        time.sleep(0.001)

                    # if previous packet sent successfully
                    if req_status:

                        req_status = False
                        # Set the command request to idle state
                        dat[0] = 0x00
                        if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                            return self.ERROR_WR_EEPROM_FAILED,

                        # Wait for mcu response to be pulled down
                        for i in range(1000):
                            status = self.__util_read_eeprom(
                                (QSFP_PAGE_OFFSET + self. QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                            if status is None:
                                return self.EEPROM_ERROR
                            if (status[0] & 0x01) == 0:
                                # Previous packet is OK
                                # Set MCU to write the next packet
                                dat[0] = remain_page_size
                                dat[1] = page_loc
                                curr_offset = ((self.QSFP_BRCM_FW_UPGRADE_PAGE*128) +
                                               self.QSFP_BRCM_FW_UPGRADE_PACKET_SIZE)
                                if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 2, dat) is False:
                                    return self.ERROR_WR_EEPROM_FAILED

                                dat[0] = (self.FW_CMD_TRANSFER << 1) | 1
                                curr_offset = ((self.QSFP_BRCM_FW_UPGRADE_PAGE*128) +
                                               self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD)
                                if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, dat) is False:
                                    return self.ERROR_WR_EEPROM_FAILED
                                req_status = True
                                break
                            time.sleep(0.001)
                        if not req_status:
                            self.__handle_error_abort(upgrade_head.cable_up_info, 4)
                            # return ret_val
                            return self.ERROR_CMD_TIMEOUT
                    else:
                        if not req_status:
                            # Timeout
                            self.log(self.LOG_ERROR, "Transfer timeout")
                            self.__handle_error_abort(upgrade_head.cable_up_info, 5)
                            # return ret_val
                            return self.ERROR_CMD_TIMEOUT

                # Check response status for last page
                for i in range(100):
                    status = self.__util_read_eeprom(
                        (QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                    if status is None:
                        return self.EEPROM_ERROR

                    if status[0] & 0x01:
                        if (status[0] & 0xFC) == (self.FW_UP_SUCCESS << 2):
                            req_status = True
                            self.log(self.LOG_DEBUG, "   100% ")
                            break
                        else:
                            # ERROR
                            self.log(self.LOG_ERROR, "ERROR: TRANSFER error{}".format((status[0] & 0xFC) >> 2))
                            self.__handle_error_abort(upgrade_head.cable_up_info, 3)
                            return ret_val

                    time.sleep(0.001)
                ts = self.log_timestamp(ts, "Check response for last page done")

                if req_status:
                    req_status = False

                    # Set the command request to idle state
                    dat[0] = 0x00
                    if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                        return self.ERROR_WR_EEPROM_FAILED

                    # Wait for mcu response to be pulled down
                    for i in range(100):
                        status = self.__util_read_eeprom(
                            (QSFP_PAGE_OFFSET + self. QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                        if status is None:
                            return self.EEPROM_ERROR
                        if (status[0] & 0x01) == 0:
                            # Last packet is OK
                            req_status = True
                            break
                        time.sleep(0.001)
                    if not req_status:
                        # Timeout, how to handle?
                        self.__handle_error_abort(upgrade_head.cable_up_info, 4)
                        # return ret_val
                        return self.ERROR_CMD_TIMEOUT
                    ts = self.log_timestamp(ts, "Wait for mcu response to be pulled down2")

                else:
                    if not req_status:
                        self.log(self.LOG_ERROR, "ERROR: TRANSFER timed out")
                    self.__handle_error_abort(upgrade_head.cable_up_info, 5)
                    return ret_val

                # COMPLETE command
                # Send firmware upgrade complete
                req_status = False
                self.log(self.LOG_INFO, "TRANSFER COMPLETE")
                ts = self.log_timestamp(ts, "TRANSFER complete")

                dat[0] = (self.FW_CMD_COMPLETE << 1) | 1
                if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                    return self.ERROR_WR_EEPROM_FAILED

                # Check response status
                for i in range(100):
                    status = self.__util_read_eeprom(
                        (QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                    if status is None:
                        return self.EEPROM_ERROR

                    # Check response status
                    if status[0] & 0x01:
                        if (status[0] & 0xFC) == (self.FW_UP_SUCCESS << 2):
                            # MCU SUCCEEDED
                            req_status = True
                            break
                        else:
                            # ERROR
                            self.__handle_error_abort(upgrade_head.cable_up_info, 6)
                            return ret_val
                    time.sleep(0.001)

                ts = self.log_timestamp(ts, "MCU check response state good")
                if req_status:
                    req_status = False
                    # Set the command request to idle state
                    dat[0] = 0x00
                    if self.platform_chassis.get_sfp(self.port).write_eeprom(QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CTRL_CMD, 1, dat) is False:
                        return self.ERROR_WR_EEPROM_FAILED

                    # wait for mcu response to be pulled down
                    for i in range(100):
                        status = self.__util_read_eeprom(
                            (QSFP_PAGE_OFFSET + self.QSFP_BRCM_FW_UPGRADE_CMD_STS), 1, "cable_fw_upgrade")
                        if status is None:
                            return self.EEPROM_ERROR
                        if (status[0] & 0x01) == 0:
                            # MCU is Ready
                            req_status = True
                            ret_val = self.RR_SUCCESS
                            break
                        time.sleep(0.001)

                    if not req_status:
                        # Timeout
                        self.log(self.LOG_ERROR, "Timed out - MCU pull down polling")
                        self.__handle_error_abort(upgrade_head.cable_up_info, 7)
                        # return ret_val
                        return self.ERROR_CMD_TIMEOUT
                    self.log_timestamp(ts, "wait for mcu response to be pulled down3")

                else:
                    # ERROR
                    self.log(self.LOG_ERROR, "ERROR")
                    self.__handle_error_abort(upgrade_head.cable_up_info, 8)
                    return ret_val
        else:
            self.log(self.LOG_WARN, "MCU not in the right state")

        self.log_timestamp(start_tstamp, "FW upgrade complete")
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

        dat = []
        dat1 = []
        i = 0
        fw_ver_dict = {}
        upgrade_info = cable_upgrade_info_s()

        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET

        if self.platform_chassis is not None:

            read_side = self.get_read_side()
            if (read_side == self.TARGET_UNKNOWN):
                self.log(self.LOG_ERROR, "ERROR: get_read_side Failed!")
                return None

            if (target == self.TARGET_TOR_A):
                target = self.TOR_MCU_SELF if (read_side == 1) else self.TOR_MCU_PEER
            elif (target == self.TARGET_TOR_B):
                target = self.TOR_MCU_SELF if (read_side == 2) else self.TOR_MCU_PEER
            else:
                target = self.NIC_MCU

            # 1s timeout
            with self.dl_lock.acquire_timeout(1) as result:

                if result:
                    upgrade_info.destination = target

                    self.log(self.LOG_DEBUG, "read_side {} target {}".format(read_side, target))

                    ret_val = self.cable_fw_get_status(upgrade_info)
                    if ret_val != self.RR_ERROR:
                        if upgrade_info.status_info.current_bank == 1:
                            # Active version
                            dat.append(format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major, 'X') +
                                       "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                            # Inactive version
                            dat.append(format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major, 'X') +
                                       "." + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                        else:
                            dat.append(format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major, 'X') +
                                       "." + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                            dat.append(format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major, 'X') +
                                       "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))

                        if upgrade_info.status_info.next_bank == 1:
                            dat.append(format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major, 'X') +
                                       "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                        else:
                            dat.append(format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major, 'X') +
                                       "." + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))

                    else:
                        self.log(self.LOG_ERROR, "Error getting version for {}".format("TOR MCU SELF" if target ==
                                                                                       self.TOR_MCU_SELF else "TOR MCU PEER" if target == self.TOR_MCU_PEER else "NIC MCU"))
                        # return self.RR_ERROR
                        return self.ERROR_GET_VERSION_FAILED

                    if target == self.NIC_MCU:
                        upgrade_info.destination = self.MUX_CHIP
                        ret_val = self.cable_fw_get_status(upgrade_info)
                        if ret_val != self.RR_ERROR:
                            if upgrade_info.status_info.current_bank == 1:
                                # Active version
                                # Active version
                                dat1.append('.' + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major,
                                                         'X') + "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                                dat1.append('.' + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major,
                                                         'X') + "." + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                                # Inactive version
                            else:
                                dat1.append('.' + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major,
                                                         'X') + "." + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                                dat1.append('.' + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major,
                                                         'X') + "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                            if upgrade_info.status_info.next_bank == 1:
                                # Active version
                                dat1.append('.' + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_major,
                                                         'X') + "." + format(upgrade_info.status_info.bank1_info.image_fw_version.image_version_minor, 'X'))
                            else:
                                dat1.append('.' + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_major,
                                                         'X') + "." + format(upgrade_info.status_info.bank2_info.image_fw_version.image_version_minor, 'X'))
                        else:
                            self.log(self.LOG_ERROR, "Error getting version for MUX CHIP")
                            # return self.RR_ERROR
                            return self.ERROR_GET_VERSION_FAILED

                        for i in range(0, 3):
                            dat[i] = dat[i] + dat1[i]

                    if target == self.TOR_MCU_SELF:
                        fw_ver_dict["version_active"] = dat[0]
                        fw_ver_dict["version_inactive"] = dat[1]
                        fw_ver_dict["version_next"] = dat[2]
                    elif target == self.TOR_MCU_PEER:
                        fw_ver_dict["version_active"] = dat[0]
                        fw_ver_dict["version_inactive"] = dat[1]
                        fw_ver_dict["version_next"] = dat[2]
                    elif target == self.NIC_MCU:
                        fw_ver_dict["version_active"] = dat[0]
                        fw_ver_dict["version_inactive"] = dat[1]
                        fw_ver_dict["version_next"] = dat[2]

                    return fw_ver_dict

                else:
                    self.log(self.LOG_ERROR, "DL Port lock timed-out!")
                    #ret_val = self.ERROR_PORT_LOCK_TIMEOUT

        return None

    def get_local_temperature(self):
        """
        This API returns local ToR temperature of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:
            None

        Returns:
            an Integer, the temperature of the local MCU
        """
        read_side = self.get_read_side()

        if read_side == self.TARGET_TOR_A:
            curr_offset = 0xFD * 128 + 0x86
        elif read_side == self.TARGET_TOR_B:
            curr_offset = 0xFD * 128 + 0x8a
        elif read_side == self.TARGET_NIC:
            curr_offset = 0xFD * 128 + 0x8e
        else:
            self.log(self.LOG_ERROR, "get_local_temperature: unknown read_side")
            return -1

        if self.platform_chassis is not None:
            #curr_offset = self.QSFP28_VENFD_129_DIE_TEMP_MSB
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            if result is None:
                self.log(self.LOG_ERROR, "get local temperature  read  eeprom failed")
                return self.EEPROM_ERROR
            else:
                temperature = result[0]
        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to check read side")
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

        read_side = self.get_read_side()

        if read_side == self.TARGET_TOR_A:
            curr_offset = 0xFD * 128 + 0x88
        elif read_side == self.TARGET_TOR_B:
            curr_offset = 0xFD * 128 + 0x8c
        elif read_side == self.TARGET_NIC:
            return None
        else:
            self.log(self.LOG_ERROR, "get_local_voltage: unknown read_side")
            return -1

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 2)
            if result is None:
                self.log(self.LOG_ERROR, "get local temperature  read  eeprom failed")
                return self.EEPROM_ERROR
            else:
                temperature = result[0] << 8 | result[1]
        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to check read side")
            temperature = None

        return temperature

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

        read_side = self.get_read_side()

        if read_side == self.TARGET_TOR_A:
            curr_offset = 0xFD * 128 + 0x8e
        elif read_side == self.TARGET_TOR_B:
            curr_offset = 0xFD * 128 + 0x8e
        elif read_side == self.TARGET_NIC:
            curr_offset = 0xFD * 128 + 0x81
        else:
            self.log(self.LOG_ERROR, "get_nic_temperature: unknown read_side")
            return -1

        if self.platform_chassis is not None:
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            if result is None:
                self.log(self.LOG_ERROR, "get local temperature  read  eeprom failed")
                return self.EEPROM_ERROR
            else:
                temperature = result[0]
        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to check read side")
            temperature = None

        return temperature

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
        if target == self.EYE_PRBS_LOOPBACK_TARGET_NIC or target == self.TARGET_NIC:
            self.log(self.LOG_WARN, "Get eye heights not supported for NIC target ")
            return None
        elif (target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_A) and (target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_B) and \
             (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET

        core_ip, lane_mask = self.__util_convert_to_phyinfo_details(target, 0X0F)

        cmd_hdr = bytearray(10)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 0x40
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = 0
        #cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = self.CORE_IP_CLIENT

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_EYE_MARGIN, cmd_hdr, cmd_req_body)

        if ret_val == 0:
            eye_heights = [[] for i in range(4)]
            values = []
            lrud_list = []
            ind = 0
            for i in range(0, 32):
                #values.append(struct.unpack("h", cmd_rsp_body[ind:ind+2]))
                byte_list = []
                for j in range(0, 2):
                    byte_list.append(cmd_rsp_body[ind + j])
                byte_array = bytearray(byte_list)
                values.append(struct.unpack("h", byte_array)[0])

                ind += 2

            if lane_mask == 0x0F:
                j = 0
                l = 0
                for i in range(0, 4):
                    for k in range(0, 4):
                        eye_heights[j].append(values[l])
                        l += 1
                    j += 1
                for i in range(0, 4):
                    #lrud_val = (format(eye_heights[i][0]) + " " + format(eye_heights[i][1]) + " " + format(eye_heights[i][2]) + " " + format(eye_heights[i][3]))
                    lrud_val = eye_heights[i][2] + eye_heights[i][3]
                    lrud_list.append(lrud_val)

            if lane_mask == 0xF0:
                j = 0
                l = 16
                for i in range(0, 4):
                    for k in range(0, 4):
                        eye_heights[j].append(values[l])
                        l += 1
                    j += 1
                k = 0
                for i in range(4, 8):
                    #lrud_val = (format(eye_heights[k][0]) + " " + format(eye_heights[k][1]) + " " + format(eye_heights[k][2]) + " " + format(eye_heights[k][3]))
                    lrud_val = eye_heights[k][2] + eye_heights[k][3]
                    lrud_list.append(lrud_val)

                    k += 1

            return lrud_list
        else:
            self.log(self.LOG_ERROR, "Command execute failed ret_val: {}".format(ret_val))
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

        if (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL and target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_A and
                target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_B and target != self.EYE_PRBS_LOOPBACK_TARGET_NIC):
            self.log(self.LOG_ERROR, "Invalid Traget : {}".format(target))
            return self.ERROR_INVALID_TARGET

        mode_value = 0xff
        lane = 0x0f
        ber_result = []
        ret_val, lock_sts, err_cnt_list = self.cable_check_prbs(target, mode_value, lane)
        if ret_val != 0:
            return False

        time.sleep(1)

        ret_val, lock_sts, err_cnt_list = self.cable_check_prbs(target, mode_value, lane)
        if ret_val != 0:
            return False

        for i in range(0, 8):
            prbs_error_per_lane = err_cnt_list[i]
            self.log(self.LOG_DEBUG, "prbs_error_per_lane : {}".format(hex(prbs_error_per_lane)))
            ber_result.append(prbs_error_per_lane/(25.78125*(math.pow(10, 9))))

        return ber_result

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
            self.log(self.LOG_ERROR, "Invalid lane = {} valid lane is 1 to 4".format(lane))
            return self.ERROR_INVALID_INPUT

        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET

        lane -= 1  # internally lane starts from 0
        lane_mask = 1 << lane
        ret_val = self.__util_convert_to_phyinfo_details(target, lane_mask)

        core_ip = ret_val[0]
        lane_mask = ret_val[1]
        self.log(self.LOG_DEBUG, "lane_mask = {} core_ip {} target {}".format(hex(lane_mask), core_ip, target))

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 14
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_TXFIR, cmd_hdr, cmd_req_body)

        if ret_val == 0:
            txfir = []
            ind = 0
            for i in range(0, 7):
                txfir.append(struct.unpack("h", cmd_rsp_body[ind:ind+2])[0])
                ind += 2

            self.log(self.LOG_DEBUG, "lane {} : pre1  = {}".format(lane, txfir[0]))
            self.log(self.LOG_DEBUG, "lane {} : pre2  = {}".format(lane, txfir[1]))
            self.log(self.LOG_DEBUG, "lane {} : main  = {}".format(lane, txfir[2]))
            self.log(self.LOG_DEBUG, "lane {} : post1 = {}".format(lane, txfir[3]))
            self.log(self.LOG_DEBUG, "lane {} : post2 = {}".format(lane, txfir[4]))
            self.log(self.LOG_DEBUG, "lane {} : post3 = {}".format(lane, txfir[5]))
            self.log(self.LOG_DEBUG, "lane {} : taps  = {}".format(lane, txfir[6]))
            return txfir
        else:
            self.log(self.LOG_ERROR, "command execution failed ret_val: {}".format(ret_val))

        return None

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

        if lane < 1 or lane > 4:
            self.log(self.LOG_ERROR, "Invalid lane = {} valid lane is 1 to 4".format(lane))
            return self.ERROR_INVALID_INPUT

        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET

        lane -= 1  # internally lane starts from 0
        lane_mask = 1 << lane
        ret_val = self.__util_convert_to_phyinfo_details(target, lane_mask)
        core_ip = ret_val[0]
        lane_mask = ret_val[1]
        self.log(self.LOG_DEBUG, "lane_mask = {} core_ip {} target {}".format(hex(lane_mask), core_ip, target))
        cmd_hdr = bytearray(5)
        #cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)
        cmd_req_body1 = bytearray()
        cmd_hdr[0] = 14
        cmd_hdr[1] = 40
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        for i in range(len(cursor_values)):
            cmd_req_body1 += struct.pack("<h", cursor_values[i])
        cmd_req_body = cmd_req_body1
        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_TXFIR, cmd_hdr, cmd_req_body)
        if ret_val == 0:
            return True
        else:
            if cmd_rsp_body is None:
                self.log(self.LOG_DEBUG, "Command response body not received")
            self.log(self.LOG_ERROR, "Command execution failed ret_val : {}".format(ret_val))
            return False

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
                RR_SUCCESS               : Success
                RR_ERROR                 : Failed
                ERROR_GET_VERSION_FAILED : Failed to get fw version from MCU
        """

        self.log(self.LOG_DEBUG, "download_firmware() start...")
        read_side = self.get_read_side()
        if read_side == self.TARGET_NIC:
            self.log(self.LOG_ERROR, "Connot perform download from NIC side")
            return False
        elif read_side == self.TARGET_UNKNOWN:
            self.log(self.LOG_ERROR, "Target self unknown. Can't upgrade")
            return False

        upgrade_head = []
        upgrade_head.append(cable_upgrade_head_s())
        upgrade_head.append(cable_upgrade_head_s())
        upgrade_head.append(cable_upgrade_head_s())
        upgrade_head.append(cable_upgrade_head_s())

        upgrade_info = []
        upgrade_info.append(cable_upgrade_info_s())
        upgrade_info.append(cable_upgrade_info_s())
        upgrade_info.append(cable_upgrade_info_s())
        upgrade_info.append(cable_upgrade_info_s())

        with self.dl_lock.acquire_timeout(self.PORT_LOCK_TIMEOUT) as result:

            if result:

                # parse image for FW versions
                for i in range(0, 4):
                    ret = self.parse_image(upgrade_head[i], i+1, fwfile)
                    if ret != self.RR_SUCCESS:
                        self.log(self.LOG_ERROR, "Parse image failed")
                        return self.RR_ERROR

                # Check MUX firmware version
                self.log(self.LOG_DEBUG, "Check MUX firmware version")

                self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS
                self.log(self.LOG_INFO, "Firmware download status inprogress")

                upgrade_info[self.MUX_CHIP - 1].destination = self.MUX_CHIP

                ret_val = self.cable_fw_get_status(upgrade_info[self.MUX_CHIP - 1])

                if ret_val != self.RR_SUCCESS:
                    self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                    self.log(self.LOG_ERROR, "MUX CHIP Firmware download status failed")
                    return self.ERROR_GET_VERSION_FAILED
                else:
                    # If version in inactive bank is different or bank is empty, then upgrade else skip
                    self.log(self.LOG_DEBUG, "If version in inactive bank is different or bank is empty, then upgrade else skip")
                    if(
                        ((upgrade_info[self.MUX_CHIP - 1].status_info.current_bank == 1)
                         and (((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major != upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major)
                               or (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor != upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))
                        or ((upgrade_info[self.MUX_CHIP - 1].status_info.current_bank == 2)
                            and (((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major != upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major)
                                  or (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor != upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))
                    ):

                        #upgrade_info[self.MUX_CHIP - 1].destination = self.MUX_CHIP
                        # Do an upgrade
                        self.log(self.LOG_DEBUG, "MUX chip new firmware available: Downloading")
                        ret_val = self.__cable_fw_upgrade(upgrade_head[self.MUX_CHIP - 1])
                        if ret_val != self.RR_SUCCESS:
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            self.log(self.LOG_ERROR, "MUX CHIP Firmware upgrade failed")
                            return self.RR_ERROR
                    else:
                        self.log(self.LOG_INFO, "MUX chip: Firmware is up to date")

                # Check NIC current bank to find which NIC image to download
                # Check if NIC MCU needs fw upgrade
                upgrade_info[self.NIC_MCU - 1].destination = self.NIC_MCU

                # Check NIC firmware version
                self.log(self.LOG_DEBUG, "Check NIC fw version")
                ret_val = self.cable_fw_get_status(upgrade_info[self.NIC_MCU - 1])
                if ret_val != self.RR_SUCCESS:
                    self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                    self.log(self.LOG_ERROR, "NIC MCU Firmware download status failed")
                    return self.ERROR_GET_VERSION_FAILED

                # If version in inactive bank is old or bank is empty, then upgrade else skip
                if(
                    ((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 1)
                     and (((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major != upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major)
                           or (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor != upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))
                    or ((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 2)
                        and (((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major != upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major)
                              or (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor != upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))
                ):
                    # Do an upgrade
                    self.log(self.LOG_INFO, "NIC MCU new firmware available: Downloading")
                    ret_val = self.__cable_fw_upgrade(upgrade_head[self.NIC_MCU - 1])
                    if ret_val != self.RR_SUCCESS:
                        self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                        self.log(self.LOG_ERROR, "NIC MCU Firmware upgrade failed")
                        return self.RR_ERROR
                else:
                    self.log(self.LOG_INFO, "NIC MCU: Firmware is up to date")

                # Check TOR firmware version
                self.log(self.LOG_DEBUG, "Check TOR firmware version")
                upgrade_info[self.TOR_MCU_SELF - 1].destination = self.TOR_MCU_SELF

                ret_val = self.cable_fw_get_status(upgrade_info[self.TOR_MCU_SELF - 1])

                if ret_val != self.RR_SUCCESS:
                    self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                    self.log(self.LOG_ERROR, "TOR SELF Firmware download status failed")
                    return self.ERROR_GET_VERSION_FAILED
                else:

                    # If version in inactive bank is old or bank is empty, then upgrade else skip
                    if(
                        ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 1)
                         and (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major != upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major)
                               or (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor != upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))
                            or (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_api_version.image_version_major != upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_api_version.image_version_major)
                                 or (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_api_version.image_version_minor != upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_api_version.image_version_minor))))
                        or ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 2)
                            and (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major != upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major)
                                  or (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor != upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))
                            or (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_api_version.image_version_major != upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_api_version.image_version_major)
                                 or (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_api_version.image_version_minor != upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_api_version.image_version_minor))))
                    ):
                        # Do an upgrade
                        self.log(self.LOG_INFO, "TOR SELF new firmware available: Downloading")
                        ret_val = self.__cable_fw_upgrade(upgrade_head[self.TOR_MCU_SELF - 1])
                        if ret_val != self.RR_SUCCESS:
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            self.log(self.LOG_ERROR, "TOR MCU Firmware upgrade failed")
                            return self.RR_ERROR

                    else:
                        self.log(self.LOG_INFO, "TOR SELF: Firmware is up to date")

                # Check TOR firmware version
                self.log(self.LOG_DEBUG, "Check TOR firmware version")
                upgrade_info[self.TOR_MCU_PEER - 1].destination = self.TOR_MCU_PEER
                ret_val = self.cable_fw_get_status(upgrade_info[self.TOR_MCU_PEER - 1])
                if ret_val != self.RR_SUCCESS:
                    self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                    self.log(self.LOG_ERROR, "TOR PEER Firmware download status failed")
                    return self.ERROR_GET_VERSION_FAILED
                else:
                    # If version in inactive bank is old or bank is empty, then upgrade else skip
                    if(
                        ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 1)
                         and (((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major != upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major)
                               or (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor != upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))
                            or (((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_api_version.image_version_major != upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_api_version.image_version_major)
                                 or (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_api_version.image_version_minor != upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_api_version.image_version_minor))))
                        or ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 2)
                            and (((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major != upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major)
                                  or (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor != upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))
                            or (((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_api_version.image_version_major != upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_api_version.image_version_major)
                                 or (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_api_version.image_version_minor != upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_api_version.image_version_minor))))
                    ):
                        # Do an upgrade
                        self.log(self.LOG_INFO, "TOR PEER new firmware available: Downloading")
                        ret_val = self.__cable_fw_upgrade(upgrade_head[self.TOR_MCU_PEER - 1])
                        if ret_val != self.RR_SUCCESS:
                            self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_FAILED
                            self.log(self.LOG_ERROR, "TOR PEER Firmware upgrade failed")
                            return self.RR_ERROR
                    else:
                        self.log(self.LOG_INFO, "TOR PEER : Firmware is up to date")

                self.download_firmware_status = self.FIRMWARE_DOWNLOAD_STATUS_NOT_INITIATED_OR_FINISHED
                self.log(self.LOG_INFO, "Firmware download finished")

            else:
                self.log(self.LOG_ERROR, "DL Port lock timed-out!")
                ret_val = self.ERROR_PORT_LOCK_TIMEOUT

        return ret_val

    def activate_firmware(self, fwfile=None, hitless=False):
        """
        This routine should activate the downloaded firmware on all the
        components of the Y cable of the port for which this API is called..
        This API is meant to be used in conjCnction with download_firmware API, and
        should be called once download_firmware API is succesful.
        This means that the firmware which has been downloaded should be
        activated (start being utilized by the cable) once this API is
        successfully executed.
        The port on which this API is called for can be referred using self.port.
        Args:
            boot_type:
                an Integer, one of the follwing predefine constants defines the boot type
                    WARMBOOT = 0 
                    COLDBOOT = 1

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
                RR_SUCCESS                 : Success
                ERROR_FW_GET_STATUS_FAILED : Failed to get firmware status from MCU
                ERROR_NO_MATCHING_FW       : No matching firmware version  found for each end of the cable
                WARNING_FW_ALREADY_ACTIVE  : Version alredy active
                ERROR_TOGGLE_FAILED        : Toggle failed
                ERROR_RESET_FAILED         : Reset Failed
                ERROR_FW_ACTIVATE_FAILURE  : Activate firmware failed
                RR_ERROR                   : Cannot activate due to fw version mismatch
        """

        #ret_val = self.ERROR_FW_ACTIVATE_FAILURE
        nic_ret_val = self.RR_SUCCESS
        self_ret_val = self.RR_SUCCESS
        peer_ret_val = self.RR_SUCCESS

        if hitless == True:
            boot_type = self.WARMBOOT
        else:
            boot_type = self.COLDBOOT

        upgrade_head = []
        upgrade_head.append(cable_upgrade_head_s())
        upgrade_head.append(cable_upgrade_head_s())
        upgrade_head.append(cable_upgrade_head_s())
        upgrade_head.append(cable_upgrade_head_s())

        upgrade_info = []
        upgrade_info.append(cable_upgrade_info_s())
        upgrade_info.append(cable_upgrade_info_s())
        upgrade_info.append(cable_upgrade_info_s())
        upgrade_info.append(cable_upgrade_info_s())

        with self.dl_lock.acquire_timeout(self.PORT_LOCK_TIMEOUT) as result:
            if result:
                upgrade_info[self.NIC_MCU - 1].destination = self.NIC_MCU
                upgrade_info[self.MUX_CHIP - 1].destination = self.MUX_CHIP
                upgrade_info[self.TOR_MCU_SELF - 1].destination = self.TOR_MCU_SELF
                upgrade_info[self.TOR_MCU_PEER - 1].destination = self.TOR_MCU_PEER

                if boot_type == self.WARMBOOT:
                    if(self.cable_fw_get_status(upgrade_info[self.MUX_CHIP - 1]) == self.RR_SUCCESS):
                        if ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major) !=
                            (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major) or
                            (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor) !=
                                (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor)):
                            self.log(self.LOG_ERROR, "Can not perform Warm Boot, MUX CHIP banks have diffrent versions")
                            return self.RR_ERROR
                    else:
                        self.log(self.LOG_ERROR, "MUX CHIP get firmware status failed")
                        return self.RR_ERROR

                for i in range(0, 4):
                    if fwfile is not None:
                        ret = self.parse_image(upgrade_head[i], i+1, fwfile)
                        if ret != self.RR_SUCCESS:
                            self.log(self.LOG_ERROR, "Parse image failed")
                            return self.RR_ERROR

                    upgrade_info[i].destination = i+1
                    if(self. cable_fw_get_status(upgrade_info[i]) != self.RR_SUCCESS):
                        return self.RR_ERROR

                # First make sure there was a successful download_firmware prior to activate
                # Check that all the ends of the cable have at least one bank matching the firmware version in fwfile
                if fwfile is not None:
                    if not ((
                        (((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                           upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                         ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                           upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                        (((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                           upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                         ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                           upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))) and
                        (
                        (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                           upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                        (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                           upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))) and
                        ((((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                            upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                           (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                            upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                         (((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                            upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                           (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                            upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))):

                        self.log(self.LOG_ERROR, "Error: Could not find for each end of the cable at least one bank matching the firmware version in the file. Please make sure to download the firmware in the file for each end")
                        return self.ERROR_NO_MATCHING_FW

                else:
                    # if anyone of the MCU's inactive bank has 0xDEADBEEF, return error
                    # check the inactive bank and validate the image_version_major
                    if upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 1:
                        if ((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "NIC MCU Inactive bank (bank2) has Inavlid firmware image")
                            return -1
                    else:
                        if ((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "NIC MCU Inactive bank (bank1) has Inavlid firmware image")
                            return -1

                    if (upgrade_info[self.MUX_CHIP - 1].status_info.current_bank == 1):
                        if ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "MUX_CHIP Inactive bank (bank2) has Inavlid firmware image")
                            return -1
                    else:
                        if ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "MUX_CHIP Inactive bank (bank1) has Inavlid firmware image")
                            return -1

                    if (upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 1):
                        if ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "TOR_MCU_SELF Inactive bank (bank2) has Inavlid firmware image")
                            return -1
                    else:
                        if ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "TOR_MCU_SELF Inactive bank (bank1) has Inavlid firmware image")
                            return -1

                    if upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 1:
                        if((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "TOR_MCU_PEER Inactive bank (bank2) has Inavlid firmware image")
                            return -1

                    else:
                        if ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "TOR_MCU_PEER Inactive bank (bank1) has Inavlid firmware image")
                            return -1

                # Check if TOR PEER MCU needs activation
                self.log(self.LOG_INFO, "TOR PEER activation:")

                # if fwfile is not provided OR
                # If version in active bank is different and version in inactive bank matches, then activate else skip
                if((fwfile is None) or
                   (((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 1) and
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                      (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                      (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                    ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 2) and
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                      (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                      (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))):

                    if boot_type == self.WARMBOOT:
                        self.log(self.LOG_INFO, "Toggle TOR-PEER MCU - warm boot")
                        ret_val = self.__cable_fw_warm_boot(upgrade_info[self.TOR_MCU_PEER - 1])
                    else:
                        self.log(self.LOG_INFO, "Toggle TOR-PEER MCU - cold boot")
                        ret_val = self.cable_fw_bank_toggle(upgrade_info[self.TOR_MCU_PEER - 1])

                    if ret_val == self.RR_SUCCESS:
                        self.log(self.LOG_INFO, "In activate fw TOR-PEER toggle success")
                    else:
                        self.log(self.LOG_ERROR, "ERROR: while activating TOR-PEER firwmware")
                        return self.ERROR_TOGGLE_FAILED

                elif(((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 1) and
                      ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                        upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 2) and
                      ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                        upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))):

                    self.log(self.LOG_INFO, "TOR-PEER MCU FW Version already active")
                    peer_ret_val = self.WARNING_FW_ALREADY_ACTIVE

                else:
                    self.log(self.LOG_ERROR, "ERROR: cannot activate due to fw version mismatch")
                    peer_ret_val = self.RR_ERROR

                # Check if NIC MCU and MUX chip needs activation
                self.log(self.LOG_INFO, "NIC MCU activation:")

                # if fwfile is not provided OR
                # If version in active bank is different and version in inactive bank matches, then activate else skip
                if((fwfile is None) or
                   (((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 1) and
                     (((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) or
                      ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) and
                     (((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                      ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))) or
                    ((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 2) and
                     (((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) or
                      ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) and
                     (((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                      ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))))):

                    if boot_type == self.WARMBOOT:
                        self.log(self.LOG_INFO, "Toggle NIC MCU - warm boot")
                        ret_val = self.__cable_fw_warm_boot(upgrade_info[self.NIC_MCU - 1])
                    else:
                        self.log(self.LOG_INFO, "Toggle NIC MCU - cold boot")
                        ret_val = self.cable_fw_bank_toggle(upgrade_info[self.NIC_MCU - 1])

                    if ret_val == self.RR_SUCCESS:
                        self.log(self.LOG_INFO, "In activate fw NIC toggle success")
                    else:
                        self.log(self.LOG_ERROR, "ERROR: while activating NIC firwmware")
                        return self.ERROR_TOGGLE_FAILED

                elif (((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 1) and
                       (((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                          upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                         (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                          upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                        ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                          upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                           (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                            upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))) or
                      ((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 2) and
                       (((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                          upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                         (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                          upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                          ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                            upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                           (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                            upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))):

                    self.log(self.LOG_INFO, "NIC MCU FW Version already active")
                    nic_ret_val = self.WARNING_FW_ALREADY_ACTIVE

                else:
                    self.log(self.LOG_ERROR, "ERROR: cannot activate due to fw version mismatch")
                    nic_ret_val = self.RR_ERROR

                # Check if TOR SELF MCU needs activation
                self.log(self.LOG_INFO, "TOR SELF activation:")

                # if fwfile is not provided OR
                # If version in active bank is different and version in inactive bank matches, then activate else skip
                if((fwfile is None) or
                   (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 1) and
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                      (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                      (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                    ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 2) and
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                      (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                      (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))):

                    if boot_type == self.WARMBOOT:
                        self.log(self.LOG_INFO, "Toggle TOR-SELF MCU - warm boot")
                        ret_val = self.__cable_fw_warm_boot(upgrade_info[self.TOR_MCU_SELF - 1])
                    else:
                        self.log(self.LOG_INFO, "Toggle TOR-SELF MCU - cold boot")
                        ret_val = self.cable_fw_bank_toggle(upgrade_info[self.TOR_MCU_SELF - 1])

                    if ret_val == self.RR_SUCCESS:
                        self.log(self.LOG_INFO, "In activate fw TOR-SELF toggle success")
                    else:
                        self.log(self.LOG_ERROR, "ERROR: while activating TOR-SELF firwmware")
                        return self.ERROR_TOGGLE_FAILED

                elif(((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 1) and
                      ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                        upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 2) and
                      ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                        upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))):

                    self.log(self.LOG_INFO, "TOR-SELF MCU FW Version already active")
                    self_ret_val = self.WARNING_FW_ALREADY_ACTIVE

                else:
                    self.log(self.LOG_ERROR, "ERROR: cannot activate due to fw version mismatch")
                    self_ret_val = self.RR_ERROR
            else:
                self.log(self.LOG_ERROR, "DL Port lock timed-out!")
                ret_val = self.ERROR_PORT_LOCK_TIMEOUT

        if peer_ret_val == self.RR_ERROR or self_ret_val == self.RR_ERROR or nic_ret_val == self.RR_ERROR:
            return self.RR_ERROR
        elif peer_ret_val == self.WARNING_FW_ALREADY_ACTIVE and self_ret_val == self.WARNING_FW_ALREADY_ACTIVE and nic_ret_val == self.WARNING_FW_ALREADY_ACTIVE:
            return self.WARNING_FW_ALREADY_ACTIVE
        else:
            return self.RR_SUCCESS

    def rollback_firmware(self, fwfile=None):
        """
        This routine should rollback the firmware to the previous version
        which was being used by the cable. This API is intended to be called when the
        user either witnesses an activate_firmware API failure or sees issues with
        newer firmware in regards to stable cable functioning.
        The port on which this API is called for can be referred using self.port.
        Args:
            boot_type:
                an Integer, one of the follwing predefine constants defines the boot type
                    WARMBOOT 
                    COLDBOOT
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
                 RR_SUCCESS                    : Success
                 ERROR_FW_GET_STATUS_FAILED    : Failed to get firmware status from MCU
                 ERROR_NO_MATCHING_FW          : No matching firmware version  found for each end of the cable
                 WARNING_FW_ALREADY_ROLLEDBACK : Version alredy active
                 ERROR_TOGGLE_FAILED           : Toggle failed
                 ERROR_RESET_FAILED            : Reset Failed
                 ERROR_FW_ROLLBACK_FAILURE     : Activate firmware failed
                 RR_ERROR                      : cannot activate due to fw version mismatch

        """

        #ret_val = self.ERROR_FW_ROLLBACK_FAILURE
        nic_ret_val = self.RR_SUCCESS
        self_ret_val = self.RR_SUCCESS
        peer_ret_val = self.RR_SUCCESS

        boot_type = self.COLDBOOT

        upgrade_head = []
        upgrade_head.append(cable_upgrade_head_s())
        upgrade_head.append(cable_upgrade_head_s())
        upgrade_head.append(cable_upgrade_head_s())
        upgrade_head.append(cable_upgrade_head_s())

        upgrade_info = []
        upgrade_info.append(cable_upgrade_info_s())
        upgrade_info.append(cable_upgrade_info_s())
        upgrade_info.append(cable_upgrade_info_s())
        upgrade_info.append(cable_upgrade_info_s())

        with self.dl_lock.acquire_timeout(self.PORT_LOCK_TIMEOUT) as result:
            if result:
                upgrade_info[self.NIC_MCU - 1].destination = self.NIC_MCU
                upgrade_info[self.MUX_CHIP - 1].destination = self.MUX_CHIP
                upgrade_info[self.TOR_MCU_SELF - 1].destination = self.TOR_MCU_SELF
                upgrade_info[self.TOR_MCU_PEER - 1].destination = self.TOR_MCU_PEER

                if boot_type == self.WARMBOOT:
                    if(self.cable_fw_get_status(upgrade_info[self.MUX_CHIP - 1]) == self.RR_SUCCESS):
                        if ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major) !=
                            (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major) or
                            (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor) !=
                                (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor)):
                            self.log(self.LOG_ERROR, "Can not perform Warm Boot, MUX CHIP banks have diffrent versions")
                            return self.RR_ERROR
                    else:
                        self.log(self.LOG_ERROR, "MUX CHIP get firmware status failed")
                        return self.RR_ERROR

                for i in range(0, 4):
                    if fwfile is not None:
                        ret = self.parse_image(upgrade_head[i], i+1, fwfile)
                        if ret != self.RR_SUCCESS:
                            self.log(self.LOG_ERROR, "Parse image failed")
                            return self.RR_ERROR

                    upgrade_info[i].destination = i+1
                    if(self. cable_fw_get_status(upgrade_info[i]) != self.RR_SUCCESS):
                        return self.RR_ERROR

                    # First make sure there was a successful download_firmware prior to activate
                    # Check that all the ends of the cable have at least one bank matching the firmware version in fwfile
                if fwfile is not None:
                    if not ((
                        (((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                           upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                         ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                           upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                        (((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                           upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                         ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                           upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))) and
                        (
                        (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                           upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                        (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                           upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                          (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                           upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))) and
                        ((((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                            upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                           (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                            upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                         (((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                            upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                           (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                            upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))):
                        self.log(self.LOG_ERROR, "Error: Could not find for each end of the cable at least one bank matching the firmware version in the file. Please make sure to download the firmware in the file for each end")
                        return self.ERROR_NO_MATCHING_FW

                else:
                    # if anyone of the MCU's inactive bank has 0xDEADBEEF, return error
                    # check the inactive bank and validate the image_version_major
                    if upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 1:
                        if ((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "NIC MCU Inactive bank (bank2) has Inavlid firmware image")
                            return -1
                    else:
                        if ((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "NIC MCU Inactive bank (bank1) has Inavlid firmware image")
                            return -1

                    if (upgrade_info[self.MUX_CHIP - 1].status_info.current_bank == 1):
                        if ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "MUX_CHIP Inactive bank (bank2) has Inavlid firmware image")
                            return -1
                    else:
                        if ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "MUX_CHIP Inactive bank (bank1) has Inavlid firmware image")
                            return -1

                    if (upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 1):
                        if ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "TOR_MCU_SELF Inactive bank (bank2) has Inavlid firmware image")
                            return -1
                    else:
                        if ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "TOR_MCU_SELF Inactive bank (bank1) has Inavlid firmware image")
                            return -1

                    if upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 1:
                        if((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "TOR_MCU_PEER Inactive bank (bank2) has Inavlid firmware image")
                            return -1

                    else:
                        if ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor == 0xBEEF) or
                            (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major == 0xDEAD) or
                                (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_crc32 == 0xDEADBEEF)):
                            self.log(self.LOG_ERROR, "TOR_MCU_PEER Inactive bank (bank1) has Inavlid firmware image")
                            return -1

                # Check NIC MCU needs rollback
                self.log(self.LOG_INFO, "NIC MCU rollback:")

                # If version in active bank is same and version in inactive bank different, then rollback
                if((fwfile is None) or
                   (((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 1) and
                     (((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) or
                      ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))
                     and
                     (((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) or
                      ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))
                    or
                    ((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 2) and
                     (((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) or
                      ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                       (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))
                     and
                     (((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) or
                      ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))))):

                    if boot_type == self.WARMBOOT:
                        self.log(self.LOG_INFO, "Rollback NIC MCU - warm boot")
                        ret_val = self.__cable_fw_warm_boot(upgrade_info[self.NIC_MCU - 1])
                    else:
                        self.log(self.LOG_INFO, "Rollback NIC MCU - cold boot")
                        ret_val = self.cable_fw_bank_toggle(upgrade_info[self.NIC_MCU - 1])

                    if ret_val == self.RR_SUCCESS:
                        self.log(self.LOG_INFO, "In rollback fw NIC MCU toggle success")
                    else:
                        self.log(self.LOG_ERROR, "ERROR: while rollback NIC MCU firwmware")
                        return self.ERROR_TOGGLE_FAILED

                elif(((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 1) and
                      (((upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                         upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                        (upgrade_info[self.NIC_MCU - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                         upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                       ((upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                         upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                        (upgrade_info[self.MUX_CHIP - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                         upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))
                     or
                     ((upgrade_info[self.NIC_MCU - 1].status_info.current_bank == 2) and
                      (((upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                         upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                        (upgrade_info[self.NIC_MCU - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                         upgrade_head[self.NIC_MCU - 1].cable_up_info.image_info.image_fw_version.image_version_minor))and
                       ((upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                         upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                        (upgrade_info[self.MUX_CHIP - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                         upgrade_head[self.MUX_CHIP - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))):

                    self.log(self.LOG_INFO, "NIC/MUX Previous version already rolled back")
                    nic_ret_val = self.WARNING_FW_ALREADY_ROLLEDBACK

                else:
                    self.log(self.LOG_ERROR, "ERROR: NIC/MUX cannot rollback: no previous version found to rollback")
                    nic_ret_val = self.RR_ERROR

                # Check TOR SELF MCU needs rollback
                self.log(self.LOG_INFO, "TOR SELF MCU rollback:")

                # If version in active bank is same and version in inactive bank different, then rollback else skip
                if((fwfile is None) or
                   (((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 1) and
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                      (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                      (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                    ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 2) and
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                      (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                      (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                       upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))):

                    if boot_type == self.WARMBOOT:
                        self.log(self.LOG_INFO, "Rollback TOR-SELF MCU - warm boot")
                        ret_val = self.__cable_fw_warm_boot(upgrade_info[self.TOR_MCU_SELF - 1])
                    else:
                        self.log(self.LOG_INFO, "Rollback TOR-SELF MCU - cold boot")
                        ret_val = self.cable_fw_bank_toggle(upgrade_info[self.TOR_MCU_SELF - 1])

                    if ret_val == self.RR_SUCCESS:
                        self.log(self.LOG_INFO, "In rollback fw TOR-SELF toggle success")
                    else:
                        self.log(self.LOG_ERROR, "ERROR: while rollback TOR-SELF firwmware")
                        return self.ERROR_TOGGLE_FAILED

                elif(((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 1) and
                      ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                        upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                     ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.current_bank == 2) and
                      ((upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                        upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.TOR_MCU_SELF - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.TOR_MCU_SELF - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))):

                    self.log(self.LOG_INFO, "TOR-SELF Previous version already rolled back")
                    if ret_val != self.WARNING_FW_ALREADY_ROLLEDBACK:
                        self_ret_val = self.WARNING_FW_ALREADY_ROLLEDBACK

                else:
                    self.log(self.LOG_ERROR, "ERROR: TOR-SELF cannot rollback: no previous version found to rollback")
                    if ret_val != self.RR_ERROR:
                        self_ret_val = self.RR_ERROR

                # Check TOR PEER MCU needs rollback
                self.log(self.LOG_INFO, "TOR PEER MCU rollback:")

                # If version in active bank is same and version in inactive bank different, then rollback else skip
                if((fwfile is None) or
                   (((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 1) and
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major ==
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                      (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor ==
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                      (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                    ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 2) and
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major ==
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) and
                      (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor ==
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor)) and
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                      (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                       upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))))):

                    if boot_type == self.WARMBOOT:
                        self.log(self.LOG_INFO, "Toggle TOR-PEER MCU - warm boot")
                        ret_val = self.__cable_fw_warm_boot(upgrade_info[self.TOR_MCU_PEER - 1])
                    else:
                        self.log(self.LOG_INFO, "Toggle TOR-PEER MCU - cold boot")
                        ret_val = self.cable_fw_bank_toggle(upgrade_info[self.TOR_MCU_PEER - 1])

                    if ret_val == self.RR_SUCCESS:
                        self.log(self.LOG_INFO, "In rollback fw TOR-PEER toggle success")
                    else:
                        self.log(self.LOG_ERROR, "ERROR: while rollback TOR-PEER firwmware")
                        return self.ERROR_TOGGLE_FAILED

                elif(((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 1) and
                      ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_major !=
                        upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank1_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor))) or
                     ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.current_bank == 2) and
                      ((upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_major !=
                        upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_major) or
                       (upgrade_info[self.TOR_MCU_PEER - 1].status_info.bank2_info.image_fw_version.image_version_minor !=
                        upgrade_head[self.TOR_MCU_PEER - 1].cable_up_info.image_info.image_fw_version.image_version_minor)))):

                    self.log(self.LOG_INFO, "TOR-PEER Previous version already rolled back")
                    if ret_val != self.WARNING_FW_ALREADY_ROLLEDBACK:
                        peer_ret_val = self.WARNING_FW_ALREADY_ROLLEDBACK

                else:
                    self.log(self.LOG_ERROR, "ERROR: TOR-PEER cannot rollback: no previous version found to rollback")
                    if ret_val != self.RR_ERROR:
                        peer_ret_val = self.RR_ERROR
            else:
                self.log(self.LOG_ERROR, "DL Port lock timed-out!")
                ret_val = self.ERROR_PORT_LOCK_TIMEOUT

        if peer_ret_val == self.RR_ERROR or self_ret_val == self.RR_ERROR or nic_ret_val == self.RR_ERROR:
            return self.RR_ERROR
        elif peer_ret_val == self.WARNING_FW_ALREADY_ROLLEDBACK and self_ret_val == self.WARNING_FW_ALREADY_ROLLEDBACK and nic_ret_val == self.WARNING_FW_ALREADY_ROLLEDBACK:
            return self.WARNING_FW_ALREADY_ROLLEDBACK
        else:
            return self.RR_SUCCESS

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

        if mode == self.SWITCHING_MODE_AUTO:
            mode_val = 1
        elif mode == self.SWITCHING_MODE_MANUAL:
            mode_val = 0
        else:
            self.log(self.LOG_ERROR, "Invalid mode {}".format(mode))
            return self.ERROR_INVALID_INPUT

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 4
        cmd_hdr[1] = 0
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL
        cmd_req_body[0] = mode_val

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_HMUX_CONFIG, cmd_hdr, cmd_req_body)

        if ret_val == 0 and cmd_rsp_body is None:
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

        cmd_hdr[0] = 0
        cmd_hdr[1] = 4
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_HMUX_CONFIG, cmd_hdr, cmd_req_body)
        if ret_val == 0:
            if cmd_rsp_body[0] & 0x1:
                self.log(self.LOG_INFO, "Auto switch enabled")
                return self.SWITCHING_MODE_AUTO
            else:
                self.log(self.LOG_INFO, "Manual switch enabled")
                return self.SWITCHING_MODE_MANUAL
        else:
            self.log(self.LOG_ERROR, "Command execution failed. ret_val: {}".format(ret_val))
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
            if result is None:
                return self.EEPROM_ERROR
        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to check active link status")
            return self.ERROR_PLATFORM_NOT_LOADED

        if self.__validate_read_data(result, 1, "get_alive_status") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR

        regval_read = struct.unpack("<B", result)

        self.log(self.LOG_DEBUG, "TOR-A active link is {}".format("up" if (regval_read[0] & 0x1 == 0) else "down"))
        self.log(self.LOG_DEBUG, "TOR-B active link is {}".format("up" if (regval_read[0] & 0x2 == 0) else "down"))
        self.log(self.LOG_DEBUG, "NIC   active link is {}".format("up" if (regval_read[0] & 0x4 == 0) else "down"))
        self.log(self.LOG_DEBUG, "PHY chip status   is {}".format("up" if (regval_read[0] & 0x8 == 0) else "down"))

        if regval_read[0] & 0x7 == 0:
            return True

        return False

    def reset_nic(self):
        """
        Resets the NIC  MCU  and this make bank swap of NIC MCU and MUX chip in effect
        Args:
            None
        Returns:
            an boolean, True - on success
                        False - on Failure
        """
        ret_code = self.reset(self.TARGET_NIC)
        if ret_code == True:
            return True
        else:
            self.log(self.LOG_ERROR, "reset_nic failed. ret_val: {}".format(ret_code))
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

        self.log(self.LOG_INFO, "reset self...")
        status = bytearray(self.MAX_REQ_PARAM_LEN)

        rval = 0
        if self.platform_chassis is not None:

            debug_print("Trying for the lock")
            with self.dl_lock.acquire_timeout(self.PORT_LOCK_TIMEOUT) as result:
                if result:

                    curr_offset = self.QSFP28_RESET_SELF_OFFSET
                    result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                    if result is None:
                        self.log(self.LOG_ERROR, "reset_self read eeprom failed")
                        return self.EEPROM_ERROR

                    rval = result[0]
                    rval |= 0x80

                    status[0] = rval
                    result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, status)
                    if result is False:
                        self.log(self.LOG_ERROR, "write to QSFP28_VENFD_184_NIC_TORB_TORA_RESET failed.")
                        return False
                    time.sleep(3)
                    # for next one second, keep checking the register to see if it becomes 0
                    for _ in range(30):
                        result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                        if result is None:
                            return self.EEPROM_ERROR
                        rval = result[0]
                        if (rval & 0x80) == 0x00:
                            ret_code = True
                            break

                        time.sleep(0.1)  # 100ms
                    else:
                        self.log(self.LOG_ERROR, "TORB_TORA_RESET never become zero.  rval: {} ".format(rval))
                        ret_code = False
                else:
                    self.log(self.LOG_ERROR, "Port lock timed-out!")
                    return self.ERROR_PORT_LOCK_TIMEOUT

        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to check read side")
            ret_code = False

        return ret_code

    def reset_peer(self):
        """
        Resets the Remote TOR MCU  and this make bank swap in effect
        Args:
            None

        Returns:
            a boolean, True  - on success
                       False - on Failure
        """

        read_side = self.get_read_side()

        if read_side == self.TARGET_TOR_A:
            if self.reset(self.TARGET_TOR_B) == True:
                return True
            else:
                return False
        elif read_side == self.TARGET_TOR_B:
            if self.reset(self.TARGET_TOR_A) == True:
                return True
            else:
                return False
        elif read_side == self.TARGET_NIC:
            self.log(self.LOG_WARN, "Cannot apply reset peer from NIC")
            return False
        else:
            self.log(self.LOG_ERROR, "reset_peer: get_read_side failed")
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
            self.log(self.LOG_ERROR, "Invalid target")
            return self.ERROR_INVALID_TARGET

        # if read side is matching target, invoke reset_self()
        read_side = self.get_read_side()
        if read_side == target:
            return self.reset_self()

        if self.platform_chassis is not None:

            debug_print("Trying for the lock")
            with self.dl_lock.acquire_timeout(self.PORT_LOCK_TIMEOUT) as result:
                if result:

                    curr_offset = self.QSFP28_VENFD_184_NIC_TORB_TORA_RESET
                    result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, status)
                    if result is False:
                        self.log(self.LOG_ERROR, "write to QSFP28_VENFD_184_NIC_TORB_TORA_RESET failed.")
                        return False

                    time.sleep(3)

                    self.log(self.LOG_DEBUG, "reset value to write.  rval: {} ".format(status[0]))
                    # for next one second, keep checking the register to see if it becomes 0
                    for _ in range(30):
                        rval = 0
                        result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
                        if result is None:
                            return self.EEPROM_ERROR
                        rval = result[0]

                        if (rval & status[0]) == 0x00:
                            ret_code = True
                            break

                        time.sleep(0.1)  # 100ms
                    else:
                        self.log(self.LOG_ERROR, "TORB_TORA_RESET never become zero.  rval: {} ".format(rval))
                        ret_code = False
                else:
                    self.log(self.LOG_ERROR, "Port lock timed-out!")
                    return self.ERROR_PORT_LOCK_TIMEOUT

        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded, failed to check read side")
            ret_code = False

        return ret_code

    def create_port(self, speed, fec_mode_tor=FEC_MODE_NONE, fec_mode_nic=FEC_MODE_NONE, anlt_tor=False, anlt_nic=False):
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
            fec_mode_tor:
                One of the following predefined constants, the actual fec mode for the tor A to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC
            fec_mode_nic:
                One of the following predefined constants, the actual fec mode for the nic to be configured:
                     FEC_MODE_NONE,
                     FEC_MODE_RS,
                     FEC_MODE_FC
            anlt_tor:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled on tor A
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled on tor A
            anlt_nic:
                a boolean, True if auto-negotiation + link training (AN/LT) is to be enabled on nic
                         , False if auto-negotiation + link training (AN/LT) is not to be enabled on nic
        Returns:
            a boolean, True if the port is configured
                     , False if the port is not configured
        """
        port_option_table = []
        ret_code = True

        port_option_table.append(valid_port_option_table_s(self.PORT_SPEED_50, self.FEC_MODE_NONE,
                                                           self.FEC_MODE_NONE, self.ANLT_DONT_CARE, self.ANLT_DONT_CARE, self.CABLE_MODE_50G_PCS))

        port_option_table.append(valid_port_option_table_s(self.PORT_SPEED_50, self.FEC_MODE_RS,
                                                           self.FEC_MODE_RS, self.ANLT_DONT_CARE, self.ANLT_DONT_CARE, self.CABLE_MODE_50G_FEC))

        port_option_table.append(valid_port_option_table_s(self.PORT_SPEED_100, self.FEC_MODE_NONE,
                                                           self.FEC_MODE_NONE, self.ANLT_DONT_CARE, self.ANLT_DONT_CARE, self.CABLE_MODE_100G_PCS))

        port_option_table.append(valid_port_option_table_s(self.PORT_SPEED_100, self.FEC_MODE_RS,
                                                           self.FEC_MODE_RS, self.ANLT_DONT_CARE, self.ANLT_DONT_CARE, self.CABLE_MODE_100G_FEC))

        matched_entry = valid_port_option_table_s
        for i in range(len(port_option_table)):
            if ((speed == port_option_table[i].speed) and (fec_mode_tor == port_option_table[i].fec_tor) and
                (fec_mode_nic == port_option_table[i].fec_nic) and
                ((0x2 if anlt_tor == True else 0x1) & port_option_table[i].anlt_tor) and
                    ((0x2 if anlt_nic == True else 0x1) & port_option_table[i].anlt_nic)):
                matched_entry.speed = port_option_table[i].speed
                matched_entry.fec_tor = port_option_table[i].fec_tor
                matched_entry.fec_nic = port_option_table[i].fec_nic
                matched_entry.anlt_tor = port_option_table[i].anlt_tor
                matched_entry.anlt_nic = port_option_table[i].anlt_nic
                matched_entry.mode = port_option_table[i].mode
                break
            else:
                if i == (len(port_option_table) - 1):
                    self.log(self.LOG_ERROR, "Not supported input parameter")
                    return False

        # Disable ANLT irrespective, For 100G need to disable AN, mcu wouldn't do it
        # Disable AN on the NIC side
        if self.set_anlt(0, self.TARGET_NIC) == False:
            self.log(self.LOG_ERROR, "disable AN/LT on TARGET_NIC failed")
            ret_code = False
        # Disable AN on the TORA side
        if self.set_anlt(0, self.TARGET_TOR_A) == False:
            self.log(self.LOG_ERROR, "disable AN/LT on TARGET_TOR-A failed")
            ret_code = False
        # Disable AN on the TORB side
        if self.set_anlt(0, self.TARGET_TOR_B) == False:
            self.log(self.LOG_ERROR, "disable AN/LT on TARGET_TOR-A failed")
            ret_code = False

        # configure mode
        if self.cable_set_mode(matched_entry.mode) == False:
            self.log(self.LOG_ERROR, "set mode failed")
            ret_code = False

        # configure AN/LT
        if anlt_nic:
            if self.set_anlt(1, self.TARGET_NIC) == False:
                self.log(self.LOG_ERROR, "Enable AN/LT on TARGET_NIC failed")
                ret_code = False
        else:
            if self.set_anlt(0, self.TARGET_NIC) == False:
                self.log(self.LOG_ERROR, "Disable AN/LT on TARGET_NIC failed")
                ret_code = False

        if anlt_tor:
            if self.set_anlt(1, self.TARGET_TOR_A) == False:
                self.log(self.LOG_ERROR, "Enable AN/LT on TARGET_TORA failed")
                ret_code = False
            if self.set_anlt(1, self.TARGET_TOR_B) == False:
                self.log(self.LOG_ERROR, "Enable AN/LT on TARGET_TORB failed")
                ret_code == False
        else:
            if self.set_anlt(0, self.TARGET_TOR_A) == False:
                self.log(self.LOG_ERROR, "Enable AN/LT on TARGET_TORA failed")
                ret_code = False
            if self.set_anlt(0, self.TARGET_TOR_B) == False:
                self.log(self.LOG_ERROR, "Enable AN/LT on TARGET_TORB failed")
                ret_code == False
        return ret_code

    def get_speed(self):
        """
        This API gets the mode of the cable for corresponding lane configuration.
        The port on which this API is called for can be referred using self.port.

        Args:
            None
        Returns:
            speed:
                an Integer, the value for the link speed is configured (in megabytes).
                examples:
                50000 -> 50G
                100000 -> 100G
        """
        mode = self.cable_get_mode()
        if mode == self.CABLE_MODE_100G_FEC or mode == self.CABLE_MODE_100G_PCS:
            return self.CABLE_MODE_100G
        elif mode == self.CABLE_MODE_50G_FEC or mode == self.CABLE_MODE_50G_PCS:
            return self.CABLE_MODE_50G
        else:
            self.log(self.LOG_ERROR, "No mode configured")
            return None

    def set_fec_mode(self, fec_mode, target=None):
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

        entry_to_match = valid_port_option_table_s

        mode_select = self.cable_get_mode()
        if (mode_select < 0):
            self.log(self.LOG_ERROR, "get_mode failed ret_code: {}".format(mode_select))
            return False

        entry_to_match.mode = mode_select
        curr_fec_mode = self.FEC_MODE_NONE if (
            mode_select == self.CABLE_MODE_50G_PCS or mode_select == self.CABLE_MODE_100G_PCS) else self.FEC_MODE_RS

        if fec_mode == curr_fec_mode:
            self.log(self.LOG_INFO, "Current mode already configured to {}".format(
                " PCS " if fec_mode == self.FEC_MODE_NONE else "FEC"))
            return True

        if fec_mode == self.FEC_MODE_NONE:
            entry_to_match.fec_nic = self.FEC_MODE_NONE
            entry_to_match.fec_tor = self.FEC_MODE_NONE
        elif fec_mode == self.FEC_MODE_RS:
            entry_to_match.fec_nic = self.FEC_MODE_RS
            entry_to_match.fec_tor = self.FEC_MODE_RS
        else:
            self.log(self.LOG_ERROR, "Invalid Input/NotSupported mode: {}".format(fec_mode))
            return False

        entry_to_match.speed = self.PORT_SPEED_50 if (
            mode_select == self.CABLE_MODE_50G_PCS or mode_select == self.CABLE_MODE_50G_FEC) else self.PORT_SPEED_100

        anlt_enable = self.get_anlt(self.TARGET_NIC)
        entry_to_match.anlt_nic = 1 if anlt_enable == True else 0

        anlt_enable = self.get_anlt(self.TARGET_TOR_A)
        entry_to_match.anlt_tor = 1 if anlt_enable == True else 0

        anlt_enable = self.get_anlt(self.TARGET_TOR_B)
        entry_to_match.anlt_tor = 1 if anlt_enable == True else 0

        ret_code = self.create_port(entry_to_match.speed, entry_to_match.fec_tor,
                                    entry_to_match.fec_nic, (1 if entry_to_match.anlt_tor == True else 0),
                                    (1 if entry_to_match.anlt_nic == True else 0))

        if ret_code == True:
            self.log(self.LOG_INFO, "Set {} fec mode success".format(fec_mode))
            return True
        else:
            self.log(self.LOG_ERROR, "Set fec mode failed")
            return False

    def get_fec_mode(self, target=None):
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
        mode_select = self.cable_get_mode()
        if (mode_select < 0):
            self.log(self.LOG_ERROR, "get_mode failed ret_code: {}".format(mode_select))
            return self.ERROR_GET_FEC_MODE_FAILED

        return self.FEC_MODE_NONE if (mode_select == self.CABLE_MODE_50G_PCS or mode_select == self.CABLE_MODE_100G_PCS) else self.FEC_MODE_RS

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
        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_INPUT

        values = self.__util_convert_to_phyinfo_details(target, 0x0F)
        core_ip = values[0]
        lane_mask = values[1]
        self.log(self.LOG_DEBUG, "core_ip {} lane_mask {}".format(core_ip, hex(lane_mask)))

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0x1
        cmd_hdr[1] = 0
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        cmd_req_body[0] = enable

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_ANLT, cmd_hdr, cmd_req_body)
        if ret_val == 0 and cmd_rsp_body is None:
            self.log(self.LOG_INFO, "{} AN/LT Successful".format("Enable" if (enable) else "Disable"))
            return True
        else:
            self.log(self.LOG_ERROR, "Enable/Disable AN LT mode is failed")
            return False

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
        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_INPUT

        values = self.__util_convert_to_phyinfo_details(target, 0x0F)
        core_ip = values[0]
        lane_mask = values[1]
        self.log(self.LOG_DEBUG, "core_ip {} lane_mask {} target {}".format(core_ip, hex(lane_mask), target))

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 1
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_ANLT, cmd_hdr, cmd_req_body)

        if self.__validate_read_data(cmd_rsp_body, 1, "cable anlt get") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR

        if ret_val == 0:
            if cmd_rsp_body[0] & 1:
                self.log(self.LOG_INFO, "AN/LT mode enabled")
                return True
            else:
                self.log(self.LOG_INFO, "AN/LT mode disabled")
                return False
        else:
            self.log(self.LOG_ERROR, "Get AN/LT get mode command execution failed")
            return False

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

    def set_autoswitch_hysteresis_timer(self, time1):
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

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 4
        cmd_hdr[1] = 0
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL

        cmd_req_body[0] = ((0x01 | (time1 << 1)) | 1 << 7)
        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_HMUX_CONFIG, cmd_hdr, cmd_req_body)
        if ret_val == 0 and cmd_rsp_body is None:
            return True
        else:
            self.log(self.LOG_ERROR, "Command execution failed. ret_val: {}".format(ret_val))
            return False

    def get_autoswitch_hysteresis_timer(self):
        """
        This API gets the hysteresis timer of the cable. This is basically the time in auto-switch mode
        which the mux has to wait after toggling it once, before again toggling the mux to a different ToR
        The port on which this API is called for can be referred using self.port.

        Args:
            None
        Returns:
            time:
                an Integer, the time value for hysteresis is configured in milliseconds
        """
        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 4
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL
        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_HMUX_CONFIG, cmd_hdr, cmd_req_body)
        if ret_val == 0:
            timer = (cmd_rsp_body[0] >> 1)
            self.log(self.LOG_DEBUG, "Timer  = {}".format(timer))

            return timer
        else:
            self.log(self.LOG_ERROR, "Get Timer value command execution failed")
            return False

    def restart_anlt(self, target):
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
        """

        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET

        values = self.__util_convert_to_phyinfo_details(target, 0x0F)
        core_ip = values[0]
        lane_mask = values[1]
        self.log(self.LOG_DEBUG, "core_ip {} lane_mask {}".format(core_ip, hex(lane_mask)))

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 0
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_ANLT_RESTART, cmd_hdr, cmd_req_body)

        if ret_val == 0 and cmd_rsp_body is None:
            self.log(self.LOG_INFO, "AN LT Restart successful")
            return True
        else:
            self.log(self.LOG_ERROR, "AN LT Restart failed")
            return False

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
        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET, None

        values = self.__util_convert_to_phyinfo_details(target, 0x0F)
        core_ip = values[0]
        lane_mask = values[1]

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 9
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_ANLT_GET_STATUS, cmd_hdr, cmd_req_body)

        if self.__validate_read_data(cmd_rsp_body, 9, "anlt get status") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR, None

        ret_array = [0 for _ in range(5)]
        if ret_val == 0 and len(cmd_rsp_body) == 9:
            ret_array[0] = an_state = cmd_rsp_body[0]
            ret_array[1] = lp_ability1 = struct.unpack('H', cmd_rsp_body[1:3])[0]
            ret_array[2] = lp_ability2 = struct.unpack('H', cmd_rsp_body[3:5])[0]
            ret_array[3] = lp_ability3 = struct.unpack('H', cmd_rsp_body[5:7])[0]
            ret_array[4] = lp_fec_ability = struct.unpack('H', cmd_rsp_body[7:9])[0]

            self.log(self.LOG_DEBUG, "Get AN LT AN State = {}".format(an_state))
            self.log(self.LOG_DEBUG, "Get AN LT LP ability1 = {}".format(lp_ability1))
            self.log(self.LOG_DEBUG, "Get AN LT LP ability2 = {}".format(lp_ability2))
            self.log(self.LOG_DEBUG, "Get AN LT LP ability3 = {}".format(lp_ability3))
            self.log(self.LOG_DEBUG, "Get AN LT LP FEC ability = {}".format(lp_fec_ability))

        else:
            self.log(self.LOG_ERROR, "Get AN LT status is failed")
            return self.EEPROM_ERROR

        return ret_val, ret_array


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
        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return False

        if lane_mask & 0xF == 0:
            self.log(self.LOG_ERROR, "Invalid lane_mask : {}".format(hex(lane_mask)))
            return False

        core_ip, lane_mask = self.__util_convert_to_phyinfo_details(target, lane_mask)

        if mode_value == 0:
            prbs_type = self.CABLE_PRBS7
        elif mode_value == 1:
            prbs_type = self.CABLE_PRBS9
        elif mode_value == 2:
            prbs_type = self.CABLE_PRBS11
        elif mode_value == 3:
            prbs_type = self.CABLE_PRBS15
        elif mode_value == 4:
            prbs_type = self.CABLE_PRBS23
        elif mode_value == 5:
            prbs_type = self.CABLE_PRBS31
        elif mode_value == 6:
            prbs_type = self.CABLE_PRBS58
        elif mode_value == 7:
            prbs_type = self.CABLE_PRBS49
        elif mode_value == 8:
            prbs_type = self.CABLE_PRBS13
        else:
            self.log(self.LOG_ERROR, "Error: for checking mux_cable enable PRBS mode, the mode_value is wrong")
            return self.ERROR_INVALID_PRBS_MODE

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0x2
        cmd_hdr[1] = 0
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        cmd_req_body[0] = 1  # enable
        cmd_req_body[1] = prbs_type

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_PRBS_SET, cmd_hdr, cmd_req_body)

        if ret_val == 0 and cmd_rsp_body is None:
            self.log(self.LOG_INFO, "Enable PRBS mode is successful")
            return True
        else:
            self.log(self.LOG_ERROR, "Enable PRBS mode is failed")
            return False

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

        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET

        core_ip, lane_mask = self.__util_convert_to_phyinfo_details(target, 0xF)

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0x2
        cmd_hdr[1] = 0
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        cmd_req_body[0] = 0  # disable
        cmd_req_body[1] = 0

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_PRBS_SET, cmd_hdr, cmd_req_body)

        if ret_val == 0 and cmd_rsp_body is None:
            self.log(self.LOG_INFO, "Disable PRBS mode is successful")
            return True
        else:
            self.log(self.LOG_ERROR, "Disable PRBS mode command execution failed")
            return False

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
        if (target != self.EYE_PRBS_LOOPBACK_TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_A) and \
           (target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_B) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return False

        if lane_mask & 0xF == 0:
            self.log(self.LOG_ERROR, "Invalid lane mask {}".format(hex(lane_mask)))
            return False

        ret_val = self.__util_convert_to_loopback_phyinfo(target, lane_mask, mode)
        core_ip = ret_val[0]
        lane_mask = ret_val[1]
        mode = ret_val[2]

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0x2
        cmd_hdr[1] = 0
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        cmd_req_body[0] = mode
        cmd_req_body[1] = 1  # enable

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_LOOPBACK, cmd_hdr, cmd_req_body)

        if ret_val == 0 and cmd_rsp_body is None:
            self.log(self.LOG_INFO, "Enable looback mode is successful")
            return True
        else:
            self.log(self.LOG_ERROR, "Enable loopback mode is failed")
            return False

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

        if (target != self.EYE_PRBS_LOOPBACK_TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_A) and \
           (target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_B) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return False

        ret_val = self.__util_convert_to_loopback_phyinfo(target, 0xF, self.LOOPBACK_MODE_NEAR_END)
        core_ip = ret_val[0]
        lane_mask = ret_val[1]
        mode = ret_val[2]

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0x2
        cmd_hdr[1] = 0
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        # disable LOOPBACK_MODE_NEAR_END first
        cmd_req_body[0] = mode
        cmd_req_body[1] = 0  # disable

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_LOOPBACK, cmd_hdr, cmd_req_body)

        if ret_val != 0:
            self.log(self.LOG_ERROR, "Disable loopback mode is failed")
            return False

        # disable LOOPBACK_MODE_FAR_END next
        ret_val = self.__util_convert_to_loopback_phyinfo(target, 0xF, self.LOOPBACK_MODE_FAR_END)
        mode = ret_val[2]

        cmd_req_body[0] = mode
        cmd_req_body[1] = 0  # disable

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_LOOPBACK, cmd_hdr, cmd_req_body)

        if ret_val == 0 and cmd_rsp_body is None:
            self.log(self.LOG_INFO, "Disable looback mode is successful")
            return True
        else:
            self.log(self.LOG_ERROR, "Disable loopback mode is failed")
            return False

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
        if (target != self.EYE_PRBS_LOOPBACK_TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_A) and \
           (target != self.EYE_PRBS_LOOPBACK_TARGET_TOR_B) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET

        ret_val = self.__util_convert_to_loopback_phyinfo(target, 0xF, self.LOOPBACK_MODE_FAR_END)
        core_ip = ret_val[0]
        lane_mask = ret_val[1]
        mode = ret_val[2]

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0x1
        cmd_hdr[1] = 0x1
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        cmd_req_body[0] = mode

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_LOOPBACK, cmd_hdr, cmd_req_body)
        if self.__validate_read_data(cmd_rsp_body, 1, "get loopback") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR
        if ret_val == 0:
            if cmd_rsp_body[0] == 1:
                self.log(self.LOG_INFO, "The Far-End loopback mode is set ON")
                return self.LOOPBACK_MODE_FAR_END
        else:
            self.log(self.LOG_ERROR, "Error getting the loopback mode ON/OFF")
            return self.LOOPBACK_MODE_NONE

        # check NEAR_END loopback
        ret_val = self.__util_convert_to_loopback_phyinfo(target, 0xF, self.LOOPBACK_MODE_NEAR_END)
        mode = ret_val[2]

        cmd_req_body[0] = mode

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_LOOPBACK, cmd_hdr, cmd_req_body)
        if self.__validate_read_data(cmd_rsp_body, 1, "get loopback") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR

        if ret_val == 0:
            if cmd_rsp_body[0] == 1:
                self.log(self.LOG_INFO, "The Near-End loopback mode is set ON")
                return self.LOOPBACK_MODE_NEAR_END
        else:
            self.log(self.LOG_ERROR, "Error getting the loopback mode ON/OFF")
            return self.LOOPBACK_MODE_NONE

        return self.LOOPBACK_MODE_NONE

    def debug_dump_registers(self):
        """
        This API should dump all registers with meaningful values
        for the cable to be diagnosed for proper functioning.
        This means that for all the fields on relevant vendor-specific pages
        this API should dump the appropriate fields with parsed values
        which would help debug the Y-Cable

        Args:
            None
        Returns:
            a Dictionary:
                 with all the relevant key-value pairs for all the meaningful fields
                 which would help diagnose the cable for proper functioning
        """

        output_str = "PHY CHIP DEBUG info dump\n"
        ret_code, reg_val = self.rd_reg_ex(0x5200C820, 0x0)
        if ret_code == -1:
            self.log(self.LOG_ERROR, "debug dump register read eeprom failed")
            return self.EEPROM_ERROR

        output_str += "active port status = {}\n".format(hex(reg_val))

        ret_code, reg_val = self.rd_reg_ex(0x5200C894, 0x0)
        output_str += "standby port status = {}\n".format(hex(reg_val))

        ret_code = self.wr_reg_ex(0x5200C81C, 0xFFFF, 0x0)
        if ret_code is False:
            print("ERROR: Writing to 0x5200C81C Failed!")

        ret_code = self.wr_reg_ex(0x5200C81C, 0x0, 0x0)
        if ret_code is False:
            print("ERROR: Writing to 0x5200C81C Failed!")

        ret_code, reg_val = self.rd_reg_ex(0x5200C8B4, 0x0)
        output_str += "GP_REG_45_int register = {} (cmd_ret: {})\n".format(hex(reg_val), ret_code)

        output_str += "\nCW=>LW IPC registers:\n"
        for i in range(0, 4):
            reg_addr = 0x5200CC20 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            output_str += "Lane {} = {} (cmd_ret: {})\n".format(i, hex(reg_val), ret_code)

        output_str += "\nLW=>CW IPC registers\n"
        for i in range(0, 4):
            reg_addr = 0x5200CC40 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            output_str += "Lane {} = {} (cmd_ret: {})\n".format(i, hex(reg_val), ret_code)

        output_str += "\nCW=>BH IPC registers\n"
        for i in range(0, 8):
            reg_addr = 0x5200CC60 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            output_str += "{} Lane {} = {} (cmd_ret: {})\n".format("TORB" if i >
                                                                   3 else "TORA", i, hex(reg_val), ret_code)

        output_str += "\nBH=>CW IPC registers\n"
        for i in range(0, 8):
            reg_addr = 0x5200CCA0 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            output_str += "{} Lane {} = {} (cmd_ret: {})\n".format("TORB" if i >
                                                                   3 else "TORA", i, hex(reg_val), ret_code)

        mode = self.cable_get_mode()
        output_str += "\npcs receive irq status registers\n"
        output_str += "lanes 0 to 3\n"
        for i in range(0, 3):
            reg_addr = 0x52007E80 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            if ret_code == -1:
                print("ERROR: rd_reg_ex {} Failed!".format(hex(reg_addr)))
            ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
            if ret_code is False:
                print("ERROR: wr_reg_ex to {} Failed!".format(hex(reg_addr)))
            if(i == 0):
                output_str += "{} {} = {}\n".format("DESK_ALIGN_LOSS:", hex(reg_addr), hex(reg_val))
            elif i == 1:
                output_str += "{} {} = {}\n".format("DSKW0:", hex(reg_addr), hex(reg_val))
            elif i == 2:
                output_str += "{} {} = {}\n".format("DSKW1:", hex(reg_addr), hex(reg_val))

        for i in range(0, 4):
            reg_addr = 0x52007E8C + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            if ret_code == -1:
                print("ERROR: rd_reg_ex {} Failed!".format(hex(reg_addr)))
            reg_val = reg_val & 0x7FFF  # dont clear bit 15
            ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
            if ret_code is False:
                print("ERROR: wr_reg_ex to {} Failed!".format(hex(reg_addr)))
            output_str += "Lane {} {} = {}\n".format(i, hex(reg_addr), hex(reg_val))
        if(mode == 0 or mode == 2):  # for fec modes
            output_str += "FEC irq status\n"
            for i in range(0, 4):
                reg_addr = 0x52007ED0 + i * 4
                ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
                if ret_code == -1:
                    print("ERROR: rd_reg_ex {} Failed!".format(hex(reg_addr)))
                ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
                if ret_code is False:
                    print("ERROR: wr_reg_ex to {} Failed!".format(hex(reg_addr)))
                if(i == 0):
                    output_str += "{} {} = {}\n".format("DEC_AM_LOCK_UNLOCK:", hex(reg_addr), hex(reg_val))
                elif i == 1:
                    output_str += "{} {} = {}\n".format("DEC_DGBOX:", hex(reg_addr), hex(reg_val))
                elif i == 2:
                    output_str += "{} {} = {}\n".format("DEC_IGBOX:", hex(reg_addr), hex(reg_val))
                elif i == 3:
                    output_str += "{} {} = {}\n".format("XDEC_ERR:", hex(reg_addr), hex(reg_val))
            for i in range(0, 2):
                reg_addr = 0x52007E60 + i * 4
                ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
                if ret_code == -1:
                    print("ERROR: rd_reg_ex {} Failed!".format(hex(reg_addr)))
                ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
                if ret_code is False:
                    print("ERROR: wr_reg_ex to {} Failed!".format(hex(reg_addr)))
                if(i == 0):
                    output_str += "{} {} = {}\n".format("ENC_GBOX:", hex(reg_addr), hex(reg_val))
                elif i == 1:
                    output_str += "{} {} = {}".format("ENC_PFIFO:", hex(reg_addr), hex(reg_val))
        output_str += "lanes 4 to 7\n"
        for i in range(0, 3):
            reg_addr = 0x52017E80 + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            if ret_code == -1:
                print("ERROR: rd_reg_ex {} Failed!".format(hex(reg_addr)))
            ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
            if ret_code is False:
                print("ERROR: wr_reg_ex to {} Failed!".format(hex(reg_addr)))
            if(i == 0):
                output_str += "{} {} = {}\n".format("DESK_ALIGN_LOSS:", hex(reg_addr), hex(reg_val))
            elif i == 1:
                output_str += "{} {} = {}\n".format("DSKW0:", hex(reg_addr), hex(reg_val))
            elif i == 2:
                output_str += "{} {} = {}\n".format("DSKW1:", hex(reg_addr), hex(reg_val))

        for i in range(0, 4):
            reg_addr = 0x52017E8C + i * 4
            ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
            if ret_code == -1:
                print("ERROR: rd_reg_ex {} Failed!".format(hex(reg_addr)))
            reg_val = reg_val & 0x7FFF  # dont clear bit 15
            ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
            if ret_code is False:
                print("ERROR: wr_reg_ex to {} Failed!".format(hex(reg_addr)))
            output_str += "Lane {} {} = {}\n".format(i, hex(reg_addr), hex(reg_val))
        if(mode == 0 or mode == 2):  # for fec modes
            output_str += "FEC irq status\n"
            for i in range(0, 4):
                reg_addr = 0x52017ED0 + i * 4
                ret_code, reg_val = self.rd_reg_ex(reg_addr, 0x0)
                if ret_code == -1:
                    print("ERROR: rd_reg_ex {} Failed!".format(hex(reg_addr)))
                ret_code = self.wr_reg_ex(reg_addr, reg_val, 0x0)
                if ret_code is False:
                    print("ERROR: wr_reg_ex to {} Failed!".format(hex(reg_addr)))
                if(i == 0):
                    output_str += "{} {} = {}\n".format("DEC_AM_LOCK_UNLOCK:", hex(reg_addr), hex(reg_val))
                elif i == 1:
                    output_str += "{} {} = {}\n".format("DEC_DGBOX:", hex(reg_addr), hex(reg_val))
                elif i == 2:
                    output_str += "{} {} = {}\n".format("DEC_IGBOX:", hex(reg_addr), hex(reg_val))
                elif i == 3:
                    output_str += "{} {} = {}\n".format("XDEC_ERR:", hex(reg_addr), hex(reg_val))
        print("\n")

        return output_str

##############################################################################
#
# Broadcom internal/debug functions
#
##############################################################################

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
        cmd_req_body[3] = ((reg_addr >> 16) & 0xFF)
        cmd_req_body[4] = ((reg_addr >> 24) & 0xFF)

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_READ_REG, cmd_hdr, cmd_req_body)
        if ret_val == 0:
            out = struct.unpack('I', cmd_rsp_body)[0]
        else:
            out = None

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
        cmd_req_body[3] = ((reg_addr >> 16) & 0xFF)
        cmd_req_body[4] = ((reg_addr >> 24) & 0xFF)
        cmd_req_body[5] = (reg_value & 0xFF)
        cmd_req_body[6] = ((reg_value >> 8) & 0xFF)
        cmd_req_body[7] = ((reg_value >> 16) & 0xFF)
        cmd_req_body[8] = ((reg_value >> 24) & 0xFF)

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_WRITE_REG, cmd_hdr, cmd_req_body)

        if cmd_rsp_body is not None:
            self.log(self.LOG_ERROR, "ERROR: response not expected")

        return ret_val

    def util_print_ctx_debug(self):
        """
        Utility api to print context debug info
        """
        ret_code, cnt_val = self.rd_reg_ex(0x5200CCE0, 0x0)
        if ret_code != 0:
            return self.EEPROM_ERROR
        ret_code, tmp_start_ppm = self.rd_reg_ex(0x5200CCE4, 0x0)
        if ret_code != 0:
            return self.EEPROM_ERROR
        ret_code, tmp_stop_ppm = self.rd_reg_ex(0x5200CCE8, 0x0)
        if ret_code != 0:
            return self.EEPROM_ERROR
        ret_code, tmp_bh_ppm = self.rd_reg_ex(0x5200CCEC, 0x0)
        if ret_code != 0:
            return self.EEPROM_ERROR

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
        if ret_code != 0:
            return self.EEPROM_ERROR

        print("cnt_val     = {}".format(cnt_val))
        print("start_ppm   = {}".format(start_ppm))
        print("stop_ppm    = {}".format(stop_ppm))
        print("bh_ppm      = {}".format(bh_ppm))
        print("switch_time = {}".format(switch_time))

        return ret_code

    def __qsfp_is_valid_page(self, page):

        if ((page == 5 or page == 6 or page == 7 or page == 8 or page == 9 or page == 10 or page == 11 or page == 12) or
            (page == 0 or page == 1 or page == 2 or page == 4 or page == 3 or page == 0x80 or page == 0x81 or
             page == 0x82 or page == 0xB1 or page == 0xFF or page == 0xFE or page == 0xFD)):
            return True

        return False

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

        if interface != self.TARGET_NIC and interface != self.TARGET_TOR_A and interface != self.TARGET_TOR_B:
            self.log(self.LOG_ERROR, "Invalid target {}".format(interface))
            return False

        if self.__qsfp_is_valid_page(page_no) == False:
            self.log(self.LOG_ERROR, "Error: invalid page no {}".format(hex(page_no)))
            return False

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

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
                print('0x{0:0{1}x}'.format((i*16), 2), end=" ")
                for j in range(0, 16):
                    print('0x{0:0{1}x}'.format(cmd_rsp_body[j], 2), end=" ")
                print("\n")

            else:
                self.log(self.LOG_ERROR, "QSFP_DUMP_PAGE failed! interface {} page {}".format(interface, page_no))
                return False

        return True

    def cable_set_mode(self, cable_mode):
        """
        This API specifically set the cable mode on the port user provides.

        Args:
             physical_port:
                 an Integer, the actual physical port connected to a Y cable

             cable_mode:
                 an Integer, specifies the cable_mode
                             CABLE_MODE_100G_FEC -> 0
                             CABLE_MODE_100G_PCS -> 1
                             CABLE_MODE_50G_FEC ->  2
                             CABLE_MODE_50G_PCS ->  3
        Returns:
            a boolean, true if the cable mode is set
                     , false if the cable mode set failed
        """
        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 1
        cmd_hdr[1] = 0
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = 0

        if cable_mode == 0:
            mode = "CABLE_MODE_100G_FEC"
        elif cable_mode == 1:
            mode = "CABLE_MODE_100G_PCS"
        elif cable_mode == 2:
            mode = "CABLE_MODE_50G_FEC"
        elif cable_mode == 3:
            mode = "CABLE_MODE_50G_PCS"
        else:
            self.log(self.LOG_ERROR, "CABLE MODE input is wrong")
            return False

        cmd_req_body[0] = cable_mode

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_MODE, cmd_hdr, cmd_req_body)
        if ret_val == -1:
            self.log(self.LOG_ERROR, "set mode read eeprom failed")
            return self.EEPROM_ERROR

        if ret_val == 0:
            self.log(self.LOG_INFO, "CABLE MODE SET {} SUCCESSFUL".format(mode))
            return True
        else:
            if cmd_rsp_body is not None:
                self.log(self.LOG_ERROR, "ERROR: Responce unexpected")

            self.log(self.LOG_ERROR, "CABLE MODE SET {} NOT SUCCESSFUL".format(mode))
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
                self.log(self.LOG_DEBUG, "CABLE_MODE_100G_FEC")
                ret_mode = 0
            elif regval_read[0] == 1:
                self.log(self.LOG_DEBUG, "CABLE_MODE_100G_PCS")
                ret_mode = 1
            elif regval_read[0] == 2:
                self.log(self.LOG_DEBUG, "CABLE_MODE_50G_FEC")
                ret_mode = 2
            elif regval_read[0] == 3:
                self.log(self.LOG_DEBUG, "CABLE_MODE_50G_PCS")
                ret_mode = 3
            else:
                self.log(self.LOG_ERROR, "Cable mode not set")
                ret_mode = -1
        else:
            ret_mode = -1

        return ret_mode

    def cable_check_prbs(self, target, mode_value, lane_mask):
        """
        This API specifically provides PRBS lock status and error count for the
        given prbs_type, lane_mask and target side

        Args:
            physical_port:
                 an Integer, the actual physical port connected to a Y cable
            target:
                 an Integer, the target on which to enable the PRBS
                             0 - PRBS_TARGET_LOCAL -> local side,
                             1 - PRBS_TARGET_TOR1 -> TOR 1
                             2 - PRBS_TARGET_TOR2 -> TOR 2
                             3 - PRBS_TARGET_NIC -> NIC
            mode_value:
                 an Integer, the mode/type for configuring the PRBS mode.
                 0x00 = PRBS 9, 0x01 = PRBS 15, 0x02 = PRBS 23, 0x03 = PRBS 31
            lane_map:
                 an Integer, representing the lane_map to be run PRBS on
                 0bit for lane 0, 1bit for lane1 and so on.
                 for example 3 -> 0b'0011 , means running on lane0 and lane1
        Returns:
            a boolean, true if the PRBS lock is successful
                     , false if the PRBS lock is failed

            lock_status, lock status - each bit represents a lane PRBS lock stats

            list,      error count list contains error count for each lane
        """

        if lane_mask & 0xF == 0:
            self.log(self.LOG_ERROR, "Lane mask not Valid ")
            return self.ERROR_INVALID_INPUT

        core_ip, lane_mask = self.__util_convert_to_phyinfo_details(target, lane_mask)
        if mode_value == 0:
            prbs_type = self.CABLE_PRBS7
        elif mode_value == 1:
            prbs_type = self.CABLE_PRBS9
        elif mode_value == 2:
            prbs_type = self.CABLE_PRBS11
        elif mode_value == 3:
            prbs_type = self.CABLE_PRBS15
        elif mode_value == 4:
            prbs_type = self.CABLE_PRBS23
        elif mode_value == 5:
            prbs_type = self.CABLE_PRBS31
        elif mode_value == 6:
            prbs_type = self.CABLE_PRBS58
        elif mode_value == 7:
            prbs_type = self.CABLE_PRBS49
        elif mode_value == 8:
            prbs_type = self.CABLE_PRBS13
        elif mode_value == 0xff:
            prbs_type = 0xff
        else:
            self.log(self.LOG_ERROR, "Error: for checking mux_cable check PRBS mode, the mode_value is wrong")
            return self.ERROR_INVALID_PRBS_MODE

        self.log(self.LOG_DEBUG, "Check PRBS for core_ip {} lane_mask {} prbs_type {}".format(
            core_ip, hex(lane_mask), prbs_type))

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0x2
        cmd_hdr[1] = 0x21
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        cmd_req_body[0] = 1  # enable
        cmd_req_body[1] = prbs_type

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_PRBS_CHK, cmd_hdr, cmd_req_body)

        if self.__validate_read_data(cmd_rsp_body, 0x21, "PRBS Check") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR, None, None

        lock_sts = int(cmd_rsp_body[0])
        self.log(self.LOG_DEBUG, "ret_val {} lock_status {}".format(ret_val, hex(lock_sts)))
        err_cnt_list = []

        if ret_val == 0:
            if cmd_rsp_body is not None:
                for i in range(0, 8):
                    if lane_mask & (1 << i):
                        if lock_sts & (1 << i):
                            self.log(self.LOG_DEBUG, "Lane {} PRBS_LOCKED".format(i))
                        else:
                            self.log(self.LOG_DEBUG, "Lane {} PRBS_NOT_LOCKED".format(i))

                    err_cnt = struct.unpack_from('I', cmd_rsp_body, 1 + i*4)[0]
                    err_cnt_list.append(err_cnt)
                    self.log(self.LOG_DEBUG, "Error count[{}] : {} ".format(i, hex(err_cnt_list[i])))
            else:
                self.log(self.LOG_WARN, "The check PRBS returned none")
                return self.EEPROM_ERROR, None, None
        else:
            self.log(self.LOG_ERROR, "Check PRBS mode is failed")
            return self.EEPROM_ERROR, None, None

        return ret_val, lock_sts, err_cnt_list

    def cable_get_intr_status(self):
        """
        This API spcifically gets the Lane interupt status,Chip interupt status
        and Port interupt status on torA, torB and NIC.

        bits        Name        Description
        3-0         TORA        torA cdr loss of lock
        7-4         NIC         nic cdr loss of lock

        3-0         TORB        torB cdr loss of lock
        7-4         TORB        torB loss

        3-0         TORA        torA loss
        7-4         NIC         nic loss

        0-2                     phy watchdog,fw ser,fw ded status respectively
        7-3                     reserved

          0                     active tor to nic fault
          1                     nic to torA link fault
          2                     nic to torB link fault
        7-3                     reserved

          0                     torA to nic pcs fec_link
          1                     torB to nic pcs fec link
        7-2                     reserved

        Args:

            physical_port:
                 an Integer, the actual physical port connected to a Y cable
        Returns:
            a bytearray, with Nic and torA loss of lock intr status,torB cdr loss of lock
                              and torB loss intr status,torA loss and Nic loss intr status,
                              CHIP interupt status ,PORT interupt status1,
                              PORT interupt status2.

        """

        intr_status = bytearray(7)
        curr_offset = [self.QSFP28_LP_5_TX_RX_CDR_LOL,
                       self.QSFP28_LOS_LOL_SEC,
                       self.QSFP28_LP_3_TX_RX_LOSS,
                       self.QSFP28_MESC_FAULT,
                       self.QSFP28_LINK_FAULT,
                       self.QSFP28_LINK_DOWN,
                       self.QSFP28_BIP_CW_ERR_FAULT]

        for ind in range(0, len(curr_offset)):
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset[ind], 1)
            if result is None:
                self.log(self.LOG_ERROR, "intr_status read_eeprom failed")
                return self.EEPROM_ERROR
            else:
                self.log(self.LOG_DEBUG, "intr_result[{}] value : {}".format(ind, hex(result[0])))

            if curr_offset[ind] == self.QSFP28_LP_5_TX_RX_CDR_LOL:
                self.log(self.LOG_DEBUG, "LANE Interupt status")
                status = struct.unpack("<B", result)
                intr_status[0] = status[0]
                self.log(self.LOG_DEBUG, "nic_cdr_loss_of_lock_ln0 = {}" .format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "nic_cdr_loss_of_lock_ln1 = {}" .format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "nic_cdr_loss_of_lock_ln2 = {}" .format(1 if((status[0] & (1 << 2))) else 0))
                self.log(self.LOG_DEBUG, "nic_cdr_loss_of_lock_ln3 = {}" .format(1 if((status[0] & (1 << 3))) else 0))
                self.log(self.LOG_DEBUG, "torA_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 4))) else 0))
                self.log(self.LOG_DEBUG, "torA_cdr_loss_of_lock_ln1 = {}".format(1 if((status[0] & (1 << 5))) else 0))
                self.log(self.LOG_DEBUG, "torA_cdr_loss_of_lock_ln2 = {}".format(1 if((status[0] & (1 << 6))) else 0))
                self.log(self.LOG_DEBUG, "torA_cdr_loss_of_lock_ln3 = {}".format(1 if((status[0] & (1 << 7))) else 0))

            if curr_offset[ind] == self.QSFP28_LOS_LOL_SEC:
                status = struct.unpack("<B", result)
                intr_status[1] = status[0]
                self.log(self.LOG_DEBUG, "torB_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "torB_cdr_loss_of_lock_ln1 = {}".format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "torB_cdr_loss_of_lock_ln2 = {}".format(1 if((status[0] & (1 << 2))) else 0))
                self.log(self.LOG_DEBUG, "torB_cdr_loss_of_lock_ln3 = {}".format(1 if((status[0] & (1 << 3))) else 0))
                self.log(self.LOG_DEBUG, "torB_los_ln0 = {}".format(1 if((status[0] & (1 << 4))) else 0))
                self.log(self.LOG_DEBUG, "torB_los_ln1 = {}".format(1 if((status[0] & (1 << 5))) else 0))
                self.log(self.LOG_DEBUG, "torB_los_ln2 = {}".format(1 if((status[0] & (1 << 6))) else 0))
                self.log(self.LOG_DEBUG, "torB_los_ln3 = {}".format(1 if((status[0] & (1 << 7))) else 0))

            if curr_offset[ind] == self.QSFP28_LP_3_TX_RX_LOSS:
                status = struct.unpack("<B", result)
                intr_status[2] = status[0]
                self.log(self.LOG_DEBUG, "nic_los_ln0  = {}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "nic_los_ln1  = {}".format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "nic_los_ln2  = {}".format(1 if((status[0] & (1 << 2))) else 0))
                self.log(self.LOG_DEBUG, "nic_los_ln3  = {}".format(1 if((status[0] & (1 << 3))) else 0))
                self.log(self.LOG_DEBUG, "torA_los_ln0 = {}".format(1 if((status[0] & (1 << 4))) else 0))
                self.log(self.LOG_DEBUG, "torA_los_ln1 = {}".format(1 if((status[0] & (1 << 5))) else 0))
                self.log(self.LOG_DEBUG, "torA_los_ln2 = {}".format(1 if((status[0] & (1 << 6))) else 0))
                self.log(self.LOG_DEBUG, "torA_los_ln3 = {}".format(1 if((status[0] & (1 << 7))) else 0))

            if curr_offset[ind] == self.QSFP28_MESC_FAULT:
                self.log(self.LOG_DEBUG, "CHIP  Intrerupt Status")
                status = struct.unpack("<B", result)
                intr_status[3] = status[0]
                self.log(self.LOG_DEBUG, "phy_watchdog      = {}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "phy_fw_ser        = {}".format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "phy_fw_ded        = {}".format(1 if((status[0] & (1 << 2))) else 0))
                self.log(self.LOG_DEBUG, "torA_mcu_wd_expiry = {}".format(1 if((status[0] & (1 << 3))) else 0))
                self.log(self.LOG_DEBUG, "torB_mcu_wd_expiry= {}".format(1 if((status[0] & (1 << 4))) else 0))
                self.log(self.LOG_DEBUG, "nic_mcu_wd_expiry= {}".format(1 if((status[0] & (1 << 5))) else 0))
                self.log(self.LOG_DEBUG, "avs_failure       = {}".format(1 if((status[0] & (1 << 6))) else 0))
                self.log(self.LOG_DEBUG, "mux_switch        = {}".format(1 if((status[0] & (1 << 7))) else 0))

            if curr_offset[ind] == self.QSFP28_LINK_FAULT:
                self.log(self.LOG_DEBUG, "PORT  Intrerupt Status")
                status = struct.unpack("<B", result)
                intr_status[4] = status[0]
                self.log(self.LOG_DEBUG, "active_tor_to_nic_fault = {}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "nic_to_torA_link_fault  = {}".format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "nic_to_torB_link_fault  = {}".format(1 if((status[0] & (1 << 2))) else 0))

            if curr_offset[ind] == self.QSFP28_LINK_DOWN:
                status = struct.unpack("<B", result)
                intr_status[5] = status[0]
                self.log(self.LOG_DEBUG, "torA_to_nic_pcs_fec_link_down = {}".format(
                    1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "torB_to_nic_pcs_fec_link_down = {}".format(
                    1 if((status[0] & (1 << 1))) else 0))

            if curr_offset[ind] == self.QSFP28_BIP_CW_ERR_FAULT:
                status = struct.unpack("<B", result)
                intr_status[6] = status[0]
                self.log(self.LOG_DEBUG, "torA BIP or CW Uncorrected error = {}".format(
                    1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "torB BIP or CW Uncorrected error = {}".format(
                    1 if((status[0] & (1 << 1))) else 0))

        return intr_status

    def cable_set_squelch(self, target, lane_map, enable, direction):
        """
        This API specifically returns get the Rx squelch and Tx squelch status on TOR and NIC

        Register Specification at offset < > is documented below

        Byte offset   bits    Name        Description
        <  >          0       squelch      0x01 enable squelch
                                           0x00 enable un-squelch
                      0       direction    0x02 direction Egress(Tx)
                                           0x00 direction Ingress(Rx)
        Args:
            physical_port:
                 an Integer, the actual physical port connected to a Y cable
            target:
                 an Integer, the actual target to get the cursor values on
                             TARGET_NIC -> NIC,
                             TARGET_TOR1-> TOR1,
                             TARGET_TOR2 -> TOR2
            lane_map:
                 an Integer, representing the lane_map to be set squelch on
                 0bit for lane 0, 1bit for lane1 and so on.
                 for example 3 -> 0b'0011 , means running on lane0 and lane1
            enable:
                 an Integer,specifies SQUELCH or UNSQUELCH 
                            SQUELCh   -> 1
                            UNSQUELCH -> 0
            direction:
                an Integer, specifies INGRESS, EGRESS or BOTH
                            INGRESS -> 0
                            EGRESS  -> 1
        Returns:
            a Boolean, True on sucess
                       False on api fail
        """

        if (target != self.TARGET_TOR_A) and (target != self.TARGET_TOR_B) and (target != self.TARGET_NIC) and (target != self.EYE_PRBS_LOOPBACK_TARGET_LOCAL):
            self.log(self.LOG_ERROR, "Invalid target : {}".format(target))
            return self.ERROR_INVALID_TARGET
        elif lane_map & 0xF == 0:
            self.log(self.LOG_ERROR, "Invalid Lane map {}".format(lane_map))
            return self.ERROR_INVALID_INPUT

        ret_val = self.__util_convert_to_phyinfo_details(target, lane_map)
        core_ip = ret_val[0]
        lane_mask = ret_val[1]

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 4
        cmd_hdr[1] = 0
        cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = core_ip

        cmd_req_body[0] = enable
        cmd_req_body[1] = direction

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_SET_SQUELCH, cmd_hdr, cmd_req_body)
        if ret_val == 0 and cmd_rsp_body is None:
            return True
        else:
            self.log(self.LOG_ERROR, "Command execution failed. ret_val: {}".format(ret_val))
            return False

    def cable_get_squelch(self):
        """
        This API specifically returns the Rx squelch and Tx squelch status on TOR and NIC

        Args:
            physical_port:
                 an Integer, the actual physical port connected to a Y cable
        Returns:
            an integer, 0 and cmd_rsp_body contains squelch status on success
                        -1 on api fail
         """

        if self.platform_chassis is not None:
            curr_offset = self.QSFP_SQL_STATUS
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            if result is None:
                self.log(self.LOG_ERROR, "get_squelch read eeprom failed")
                return self.EEPROM_ERROR
        else:
            self.log(self.LOG_ERROR, "platform_chassis is not loaded")
            return self.ERROR_PLATFORM_NOT_LOADED

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 4
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_ALL

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_SQUELCH, cmd_hdr, cmd_req_body)

        if ret_val == 0:
            lane = 0
            for _ in range(0, 8):
                if cmd_rsp_body[0] & (1 << lane):
                    self.log(self.LOG_DEBUG, "client side rx lane {} is squelch".format(lane))
                    lane += 1
                else:
                    self.log(self.LOG_DEBUG, "client side rx lane {} is un-squelch".format(lane))
                    lane += 1
            lane = 0
            for _ in range(0, 8):
                if cmd_rsp_body[1] & (1 << lane):
                    self.log(self.LOG_DEBUG, "client side tx lane {} is squelch".format(lane))
                    lane += 1
                else:
                    self.log(self.LOG_DEBUG, "client side tx lane {} is un-squelch".format(lane))
                    lane += 1

            lane = 0
            for _ in range(0, 8):
                if cmd_rsp_body[2] & (1 << lane):
                    self.log(self.LOG_DEBUG, "line side rx lane {} is squelch".format(lane))
                    lane += 1
                else:
                    self.log(self.LOG_DEBUG, "line side rx lane {} is un-squelch".format(lane))
                    lane += 1
            lane = 0
            for _ in range(0, 8):
                if cmd_rsp_body[3] & (1 << lane):
                    self.log(self.LOG_DEBUG, "line side tx lane {} is squelch".format(lane))
                    lane += 1
                else:
                    self.log(self.LOG_DEBUG, "line side tx lane {} is un-squelch".format(lane))
                    lane += 1
        else:
            self.log(self.LOG_ERROR, "Command execution failed. ret_val: {}".format(ret_val))
            return None

        return cmd_rsp_body

    def cable_get_snr(self):
        """
        cable get snr
        """

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 0x10
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0x0F
        #cmd_hdr[2] = lane_mask if (core_ip == self.CORE_IP_CLIENT) else 0
        #cmd_hdr[3] = lane_mask if (core_ip == self.CORE_IP_LW) else 0
        cmd_hdr[4] = self.CORE_IP_LW

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_GET_SNR, cmd_hdr, cmd_req_body)
        if ret_val == 0:
            values = []
            values.append(struct.unpack('<f', cmd_rsp_body[0:4]))
            values.append(struct.unpack('<f', cmd_rsp_body[4:8]))
            values.append(struct.unpack('<f', cmd_rsp_body[8:12]))
            values.append(struct.unpack('<f', cmd_rsp_body[12:16]))
            for i in range(len(values)):
                self.log(self.LOG_DEBUG, "lane {} = (snr) = {}".format(i, values[i]))

            return values
        else:
            return None

    def cable_get_intr_mask(self):
        """
        This API spcifically gets the Lane interupt mask,Chip interupt mask and
        Port interupt mask on torA, torB and NIC.

          bits      Name        Description
          3-0       TORA        torA cdr loss of lock
          7-4       NIC         nic cdr loss of lock

          3-0       TORB        torB cdr loss of lock
          7-4       TORB        torB loss

          3-0       TORA        torA loss
          7-4       NIC         nic loss

          0-2                   phy watchdog,fw ser,fw ded status respectively.
          7-3                   reserved

            0                   active tor to nic fault
            1                   nic to torA link fault
            2                   nic to torB link fault
          7-3                   reserved

            0                   torA to nic pcs fec_link
            1                   torB to nic pcs fec link
          7-2                   reserved
        Args:
            physical_port:
                 an Integer, the actual physical port connected to a Y cable
        Returns:
            a bytearray, with Nic and torA loss of lock intr mask,torB cdr loss of lock and
                              torB loss intr mask, torA loss and Nic loss intr mask,
                              CHIP interupt status intr mask,PORT link fault int mask,
                              PORT up down intr mask.
        """

        curr_offset = [self.QSFP28_LP_102_TX_RX_CDR_LOL_MASK,
                       self.QSFP28_LOS_LOL_SEC_MASK,
                       self.QSFP28_LP_100_TX_RX_LOS_MASK,
                       self.QSFP_MESC_MASK,
                       self.QSFP28_UP_DOWN_MASK,
                       self.QSFP_LINK_FAULT_MASK,
                       self.QSFP28_BIP_UNCORR_MASK]

        intr_mask = bytearray(7)

        for ind in range(0, len(curr_offset)):
            result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset[ind], 1)
            if result is None:
                self.log(self.LOG_ERROR, "cable_get_intr_mask read eeprom failed")
                return self.EEPROM_ERROR

            self.log(self.LOG_DEBUG, "intr_result[{}] value : {}".format(ind, hex(result[0])))

            if curr_offset[ind] == self.QSFP28_LP_102_TX_RX_CDR_LOL_MASK:
                self.log(self.LOG_DEBUG, "LANE Interupt status")
                status = struct.unpack("<B", result)
                intr_mask[0] = status[0]
                self.log(self.LOG_DEBUG, "nic_cdr_loss_of_lock_ln0 = {}" .format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "nic_cdr_loss_of_lock_ln0 = {}" .format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "nic_cdr_loss_of_lock_ln0 = {}" .format(1 if((status[0] & (1 << 2))) else 0))
                self.log(self.LOG_DEBUG, "nic_cdr_loss_of_lock_ln0 = {}" .format(1 if((status[0] & (1 << 3))) else 0))
                self.log(self.LOG_DEBUG, "torA_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 4))) else 0))
                self.log(self.LOG_DEBUG, "torA_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 5))) else 0))
                self.log(self.LOG_DEBUG, "torA_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 6))) else 0))
                self.log(self.LOG_DEBUG, "torA_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 7))) else 0))

            if curr_offset[ind] == self.QSFP28_LOS_LOL_SEC_MASK:
                status = struct.unpack("<B", result)
                intr_mask[1] = status[0]
                self.log(self.LOG_DEBUG, "torB_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "torB_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "torB_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 2))) else 0))
                self.log(self.LOG_DEBUG, "torB_cdr_loss_of_lock_ln0 = {}".format(1 if((status[0] & (1 << 3))) else 0))
                self.log(self.LOG_DEBUG, "torB_los_ln0= {}".format(1 if((status[0] & (1 << 4))) else 0))
                self.log(self.LOG_DEBUG, "torB_los_ln0= {}".format(1 if((status[0] & (1 << 5))) else 0))
                self.log(self.LOG_DEBUG, "torB_los_ln0= {}".format(1 if((status[0] & (1 << 6))) else 0))
                self.log(self.LOG_DEBUG, "torB_los_ln0= {}".format(1 if((status[0] & (1 << 7))) else 0))

            if curr_offset[ind] == self.QSFP28_LP_100_TX_RX_LOS_MASK:
                status = struct.unpack("<B", result)
                intr_mask[2] = status[0]
                self.log(self.LOG_DEBUG, "torA_los_ln0 ={}".format(1 if((status[0] & (1 << 4))) else 0))
                self.log(self.LOG_DEBUG, "torA_los_ln0 ={}".format(1 if((status[0] & (1 << 5))) else 0))
                self.log(self.LOG_DEBUG, "torA_los_ln0 ={}".format(1 if((status[0] & (1 << 6))) else 0))
                self.log(self.LOG_DEBUG, "torA_los_ln0 ={}".format(1 if((status[0] & (1 << 7))) else 0))
                self.log(self.LOG_DEBUG, "nic_los_ln0 ={}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "nic_los_ln0 ={}".format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "nic_los_ln0 ={}".format(1 if((status[0] & (1 << 2))) else 0))
                self.log(self.LOG_DEBUG, "nic_los_ln0 ={}".format(1 if((status[0] & (1 << 3))) else 0))

            if curr_offset[ind] == self.QSFP_MESC_MASK:
                self.log(self.LOG_DEBUG, "CHIP  Intrerupt Status")
                status = struct.unpack("<B", result)
                intr_mask[3] = status[0]
                self.log(self.LOG_DEBUG, "phy_watchdog={}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "phy_fw_ser= {}".format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "phy_fw_ded= {}".format(1 if((status[0] & (1 << 2))) else 0))
                self.log(self.LOG_DEBUG, "avs_failure={}".format(1 if((status[0] & (1 << 6))) else 0))

            if curr_offset[ind] == self.QSFP_LINK_FAULT_MASK:
                self.log(self.LOG_DEBUG, "PORT  Intrerupt Status")
                status = struct.unpack("<B", result)
                intr_mask[4] = status[0]
                self.log(self.LOG_DEBUG, "active_tor_to_nic_fault= {}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "nic_to_torA_link_fault={}".format(1 if((status[0] & (1 << 1))) else 0))
                self.log(self.LOG_DEBUG, "nic_to_torB_link_fault= {}".format(1 if((status[0] & (1 << 2))) else 0))

            if curr_offset[ind] == self.QSFP28_UP_DOWN_MASK:
                status = struct.unpack("<B", result)
                intr_mask[5] = status[0]
                self.log(self.LOG_DEBUG, "torA_to_nic_pcs_fec_link_down={}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG, "torB_to_nic_pcs_fec_link_down= {}".format(
                    1 if((status[0] & (1 << 1))) else 0))

            if curr_offset[ind] == self.QSFP28_BIP_UNCORR_MASK:
                status = struct.unpack("<B", result)
                intr_mask[6] = status[0]
                self.log(self.LOG_DEBUG,
                         "tora bip error/fec un correctable error = {}".format(1 if((status[0] & (1 << 0))) else 0))
                self.log(self.LOG_DEBUG,
                         "torb bip error/fec un correctable error = {}".format(1 if((status[0] & (1 << 1))) else 0))

        return intr_mask

    def cable_set_intr_mask(self, intr_mask):
        """
        This API spcifically gets the Lane interupt mask,Chip interupt mask and
        Port interupt mask on torA, torB and NIC.
          bits      Name        Description
          3-0       TORA        torA cdr loss of lock
          7-4       NIC         nic cdr loss of lock
          3-0       TORB        torB cdr loss of lock
          7-4       TORB        torB loss
          3-0       TORA        torA loss
          7-4       NIC         nic loss
          0-2                   phy watchdog,fw ser,fw ded status respectively.
          7-3                   reserved
            0                   active tor to nic fault
            1                   nic to torA link fault
            2                   nic to torB link fault
          7-3                   reserved
            0                   torA to nic pcs fec_link
            1                   torB to nic pcs fec link
          7-2                   reserved
        Args:
            list of intr mask in the below order : 
                    nic_torA_loss_lock_intr_mask
                    torB_cdr_loss_lock_torB_loss_intr_mask
                    torA_loss_nic_loss_intr_mask
                    chip_intr_mask
                    port_link_fault_intr_mask
                    port_up_down_intr_mas
        Returns:
            a Boolean,True on Success
                      False on failure
        """
        if self.platform_chassis is not None:
            buffer1 = bytearray(self.MAX_REQ_PARAM_LEN)
            curr_offset = self.QSFP28_LP_102_TX_RX_CDR_LOL_MASK
            buffer1[0] = intr_mask[0]
            if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1) is False:
                return self.ERROR_WR_EEPROM_FAILED
            curr_offset = self.QSFP28_LOS_LOL_SEC_MASK
            buffer1[0] = intr_mask[1]
            if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1) is False:
                return self.ERROR_WR_EEPROM_FAILED
            curr_offset = self.QSFP28_LP_100_TX_RX_LOS_MASK
            buffer1[0] = intr_mask[2]
            if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1) is False:
                return self.ERROR_WR_EEPROM_FAILED
            curr_offset = self.QSFP_MESC_MASK
            buffer1[0] = intr_mask[3]
            if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1) is False:
                return self.ERROR_WR_EEPROM_FAILED
            curr_offset = self.QSFP_LINK_FAULT_MASK
            buffer1[0] = intr_mask[4]
            if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1) is False:
                return self.ERROR_WR_EEPROM_FAILED
            curr_offset = self.QSFP28_UP_DOWN_MASK
            buffer1[0] = intr_mask[5]
            if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1) is False:
                return self.ERROR_WR_EEPROM_FAILED
            curr_offset = self.QSFP28_BIP_UNCORR_MASK
            buffer1[0] = intr_mask[6]
            if self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buffer1) is False:
                return self.ERROR_WR_EEPROM_FAILED
        else:
            self.log(self.LOG_WARN, "platform_chassis is not loaded, failed to set intr mask ")
            return -1

        return True

    def cable_check_intr_active_status(self):

        curr_offset = self.QSFP28_LP_QSFP28_LP_2_STATUS_CR
        result = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        if self.__validate_read_data(result, 1, "get check_active_status") == self.EEPROM_READ_DATA_INVALID:
            return self.EEPROM_ERROR
        else:
            self.log(self.LOG_DEBUG, "intr value : {}".format(hex(result[0])))
            return result[0]

    def cable_read_nic_mcu_ram(self, address):
        """
        utility function reads RAM address and returns value

        """

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 5
        cmd_hdr[1] = 4
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL

        cmd_req_body[0] = address & 0xFF
        cmd_req_body[1] = (address >> 8) & 0xFF
        cmd_req_body[2] = (address >> 16) & 0xFF
        cmd_req_body[3] = (address >> 24) & 0xFF
        cmd_req_body[4] = 4

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_READ_MCU_RAM, cmd_hdr, cmd_req_body)
        if ret_val == 0 and cmd_rsp_body is not None:
            return cmd_rsp_body
        else:
            self.log(self.LOG_ERROR, "cable_read_nic_mcu_ram failed ")

        return None

    def cable_clear_nic_mcu_dump(self):
        """
        utility function reads RAM address and returns value

        """

        cmd_hdr = bytearray(5)
        cmd_req_body = bytearray(self.MAX_REQ_PARAM_LEN)

        cmd_hdr[0] = 0
        cmd_hdr[1] = 0
        cmd_hdr[2] = 0
        cmd_hdr[3] = 0
        cmd_hdr[4] = self.CORE_IP_CENTRAL

        ret_val, cmd_rsp_body = self.__cable_cmd_execute(self.CABLE_CMD_ID_CLEAR_CRASH, cmd_hdr, cmd_req_body)
        if ret_val == 0:
            self.log(self.LOG_ERROR, "nic_mcu_crash cleared ")
            if cmd_rsp_body is not None:
                self.log(self.LOG_DEBUG, "CABLE_CMD_ID_CLEAR_CRASH returned value?")
        else:
            self.log(self.LOG_ERROR, "cable_clear_nic_mcu_crash failed ")

        return None

    def read_tor_ram(self, address):
        """
        Utility function to read SRAM address
        """
        addr_array = bytearray(4)
        buf = bytearray(4)

        addr_array[0] = address & 0xFF
        addr_array[1] = (address >> 8) & 0xFF
        addr_array[2] = (address >> 16) & 0xFF
        addr_array[3] = (address >> 24) & 0xFF

        # write the ram address to read
        curr_offset = (0xFD * 128) + 0xF8
        result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 4, addr_array)
        if result is False:
            return self.ERROR_WR_EEPROM_FAILED

        # write count
        curr_offset = (0xFD * 128) + 0xF6
        buf[0] = 4
        result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buf)
        if result is False:
            return self.ERROR_WR_EEPROM_FAILED

        curr_offset = (0xFD * 128) + 0xF6
        for _ in range(0, 3000):
            status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            if status is None:
                self.log(self.LOG_ERROR, "read_tor_ram: read_eeprom failed")
                return self.EEPROM_ERROR

            if status[0] == 0:
                break

        curr_offset = (0xFD * 128) + 0xF7
        status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
        if status is None:
            self.log(self.LOG_ERROR, "read_tor_ram: read_eeprom failed")
            return self.EEPROM_ERROR

        if status[0] == 0:
            curr_offset = (0xFD * 128) + 0xFC
            val_arr = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 4)
            if val_arr is None:
                return self.EEPROM_ERROR
        else:
            return -1

        return val_arr

    def cable_clear_tor_mcu_dump(self):
        """
        Utility function to cear TOR crash info
        """
        # clear TOR crash
        buf = bytearray(1)
        buf[0] = 1
        curr_offset = ((0xFD * 128) + 0xF2)
        result = self.platform_chassis.get_sfp(self.port).write_eeprom(curr_offset, 1, buf)
        if result is False:
            return self.ERROR_WR_EEPROM_FAILED

        curr_offset = ((0xFD * 128) + 0xF2)
        for _ in range(0, 3000):
            status = self.platform_chassis.get_sfp(self.port).read_eeprom(curr_offset, 1)
            if status is None:
                self.log(self.LOG_ERROR, "clear_tor_crash_info: read_eeprom failed")
                return self.EEPROM_ERROR
            if status[0] == 0:
                break

    def cable_print_nic_mcu_dump(self):
        """
        Dump NIC crash info
        """
        buff = bytearray()
        itr_count = 2048
        address = 0x20030000
        no_crash = 1
        exp_val = ram2_exp_s()

        self.log(self.LOG_DEBUG, "Reading NIC dump data...")
        for i in range(0, itr_count):
            tval = self.cable_read_nic_mcu_ram(address)
            # if tval is None or tval == -1:
            if (tval is None) or (tval == self.EEPROM_ERROR):
                self.log(self.LOG_ERROR, "cable_print_nic_mcu_dump: read_tor_ram failed")
                break

            if i == 0:
                value = struct.unpack("<I", tval)[0]
                if value != 0xDEADBEEF:
                    self.log(self.LOG_WARN, "No new crash on NIC")
                    break
            elif i == 1:
                value = struct.unpack("<I", tval)[0]

            no_crash = 0
            buff += tval
            address = address + 4

        # print the crash info
        if no_crash == 0:
            exp_val.hdr_val.crash = struct.unpack('I', buff[0:4])[0]
            exp_val.hdr_val.crash_len = struct.unpack('I', buff[4:8])[0]
            exp_val.hdr_val.cfsr_reg = struct.unpack('I', buff[8:12])[0]
            exp_val.hdr_val.ufsr_reg = struct.unpack('H', buff[12:14])[0]
            exp_val.hdr_val.bfsr_reg = struct.unpack('B', buff[14:15])[0]
            exp_val.hdr_val.mmfsr_reg = struct.unpack('B', buff[15:16])[0]
            exp_val.hdr_val.val.r0 = struct.unpack('I', buff[16:20])[0]
            exp_val.hdr_val.val.r1 = struct.unpack('I', buff[20:24])[0]
            exp_val.hdr_val.val.r2 = struct.unpack('I', buff[24:28])[0]
            exp_val.hdr_val.val.r3 = struct.unpack('I', buff[28:32])[0]
            exp_val.hdr_val.val.r12 = struct.unpack('I', buff[32:36])[0]
            exp_val.hdr_val.val.lr = struct.unpack('I', buff[36:40])[0]
            exp_val.hdr_val.val.return_address = struct.unpack('I', buff[40:44])[0]
            exp_val.hdr_val.val.xpsr = struct.unpack('I', buff[44:48])[0]
            exp_val.hdr_val.exp_sp_depth = struct.unpack('I', buff[48:52])[0]
            stack_depth = exp_val.hdr_val.exp_sp_depth

            sidx = 52
            for i in range(stack_depth):
                exp_val.exp_stack.append(0)

            for i in range(stack_depth):
                exp_val.exp_stack[i] = struct.unpack('I', buff[sidx:sidx+4])[0]
                sidx += 4

            output_str = "Exception status register values:\n"
            output_str += "csfr=>>>>>>> = {}\n".format(hex(exp_val.hdr_val.cfsr_reg))
            output_str += "ufsr_reg=>>> = {}\n".format(hex(exp_val.hdr_val.ufsr_reg))
            output_str += "bfsr_reg=>>> = {}\n".format(hex(exp_val.hdr_val.bfsr_reg))
            output_str += "mmfsr_reg=>> = {}\n".format(hex(exp_val.hdr_val.mmfsr_reg))
            output_str += "-------------------------------------------------\n"
            output_str += "Exception context Frame\n"
            output_str += "R0=>>>>> {}\n".format(hex(exp_val.hdr_val.val.r0))
            output_str += "R1=>>>>> {}\n".format(hex(exp_val.hdr_val.val.r1))
            output_str += "R2=>>>>> {}\n".format(hex(exp_val.hdr_val.val.r2))
            output_str += "R3=>>>>> {}\n".format(hex(exp_val.hdr_val.val.r3))
            output_str += "R12=>>>> {}\n".format(hex(exp_val.hdr_val.val.r12))
            output_str += "LR=>>>>> {}\n".format(hex(exp_val.hdr_val.val.lr))
            output_str += "Return Address=>>>>> {}\n".format(hex(exp_val.hdr_val.val.return_address))
            output_str += "XPSR=>>>>> {}\n".format(hex(exp_val.hdr_val.val.xpsr))
            output_str += "-------------------------------------------------\n"
            i = stack_depth - 1

            for j in range(i, -1, -1):
                output_str += "stack value at {}  >>>>>> {}\n".format(j, hex(exp_val.exp_stack[j]))

            return output_str

        return None

    def cable_print_tor_mcu_dump(self):
        """
        Dump TOR crash info
        """
        buff = bytearray()
        itr_count = 2048
        address = 0x20030000
        no_crash = 1
        exp_val = ram2_exp_s()

        self.log(self.LOG_DEBUG, "Reading TOR dump data...")
        for i in range(0, itr_count):
            tval = self.read_tor_ram(address)
            if (tval is None) or (tval == self.EEPROM_ERROR):
                self.log(self.LOG_ERROR, "cable_print_tor_mcu_dump: read_tor_ram failed")
                break

            if i == 0:
                value = struct.unpack("<I", tval)[0]
                if value != 0xDEADBEEF:
                    self.log(self.LOG_DEBUG, "No new crash on TOR")
                    break
            elif i == 1:
                value = struct.unpack("<I", tval)[0]

            no_crash = 0
            buff += tval

            address = address + 4

        if no_crash == 0:

            exp_val.hdr_val.crash = struct.unpack('I', buff[0:4])[0]
            exp_val.hdr_val.crash_len = struct.unpack('I', buff[4:8])[0]
            exp_val.hdr_val.cfsr_reg = struct.unpack('I', buff[8:12])[0]
            exp_val.hdr_val.ufsr_reg = struct.unpack('H', buff[12:14])[0]
            exp_val.hdr_val.bfsr_reg = struct.unpack('B', buff[14:15])[0]
            exp_val.hdr_val.mmfsr_reg = struct.unpack('B', buff[15:16])[0]
            exp_val.hdr_val.val.r0 = struct.unpack('I', buff[16:20])[0]
            exp_val.hdr_val.val.r1 = struct.unpack('I', buff[20:24])[0]
            exp_val.hdr_val.val.r2 = struct.unpack('I', buff[24:28])[0]
            exp_val.hdr_val.val.r3 = struct.unpack('I', buff[28:32])[0]
            exp_val.hdr_val.val.r12 = struct.unpack('I', buff[32:36])[0]
            exp_val.hdr_val.val.lr = struct.unpack('I', buff[36:40])[0]
            exp_val.hdr_val.val.return_address = struct.unpack('I', buff[40:44])[0]
            exp_val.hdr_val.val.xpsr = struct.unpack('I', buff[44:48])[0]
            exp_val.hdr_val.exp_sp_depth = struct.unpack('I', buff[48:52])[0]
            stack_depth = exp_val.hdr_val.exp_sp_depth

            sidx = 52
            for i in range(stack_depth):
                exp_val.exp_stack.append(0)

            for i in range(stack_depth):
                exp_val.exp_stack[i] = struct.unpack('I', buff[sidx:sidx+4])[0]
                sidx += 4

            output_str = "Exception status register values:\n"
            output_str += "csfr=>>>>>>> = {}\n".format(hex(exp_val.hdr_val.cfsr_reg))
            output_str += "ufsr_reg=>>> = {}\n".format(hex(exp_val.hdr_val.ufsr_reg))
            output_str += "bfsr_reg=>>> = {}\n".format(hex(exp_val.hdr_val.bfsr_reg))
            output_str += "mmfsr_reg=>> = {}\n".format(hex(exp_val.hdr_val.mmfsr_reg))
            output_str += "-------------------------------------------------\n"
            output_str += "Exception context Frame\n"
            output_str += "R0=>>>>> {}\n".format(hex(exp_val.hdr_val.val.r0))
            output_str += "R1=>>>>> {}\n".format(hex(exp_val.hdr_val.val.r1))
            output_str += "R2=>>>>> {}\n".format(hex(exp_val.hdr_val.val.r2))
            output_str += "R3=>>>>> {}\n".format(hex(exp_val.hdr_val.val.r3))
            output_str += "R12=>>>> {}\n".format(hex(exp_val.hdr_val.val.r12))
            output_str += "LR=>>>>> {}\n".format(hex(exp_val.hdr_val.val.lr))
            output_str += "Return Address=>>>>> {}\n".format(hex(exp_val.hdr_val.val.return_address))
            output_str += "XPSR=>>>>> {}\n".format(hex(exp_val.hdr_val.val.xpsr))
            output_str += "-------------------------------------------------\n"
            i = stack_depth - 1

            for j in range(i, -1, -1):
                output_str += "stack value at {}  >>>>>> {}\n".format(j, hex(exp_val.exp_stack[j]))

            return output_str

        return None
