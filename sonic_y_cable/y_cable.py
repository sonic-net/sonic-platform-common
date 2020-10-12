#!/usr/bin/env python
#
# y_cable.py
#
#  class for implementing Y cable access and configurations
#   API's for Y cable functionality in SONiC

try:
    import binascii
    import sys

    import sonic_platform.platform
    from sonic_py_common import logger

except ImportError as e:
    raise ImportError(str(e) + " - required module not found")

# Global logger instance for helper functions and classes
helper_logger = logger.Logger(SYSLOG_IDENTIFIER)

# Global platform_chassis instance to call get_sfp required for read/write eeprom
platform_chassis = sonic_platform.platform.Platform().get_chassis()

# definitions of the offset with width accomodated for values
# of MUX register specs of upper page 0x04 starting at 640
# info eeprom
Y_CABLE_IDENTFIER_LOWER_PAGE = 0
Y_CABLE_IDENTFIER_UPPER_PAGE = 128
Y_CABLE_DETERMINE_CABLE_READ_SIDE = 640
Y_CABLE_CHECK_LINK_ACTIVE = 641
Y_CABLE_SWITCH_MUX_DIRECTION = 642
Y_CABLE_ACTIVE_TOR_INDICATOR = 645
Y_CABLE_ACTIVE_TOR_INDICATOR = 0


def toggle_mux_to_torA(physical_port):

    buffer = bytearray([2])
    curr_offset = Y_CABLE_SWITCH_MUX_DIRECTION

    result = platform_chassis.get_sfp(
        physical_port).write_eeprom(curr_offset, 1, buffer)

    return result


def toggle_mux_to_torB(physical_port):

    buffer = bytearray([3])
    curr_offset = Y_CABLE_SWITCH_MUX_DIRECTION

    result = platform_chassis.get_sfp(
        physical_port).write_eeprom(curr_offset, 1, buffer)

    return result


def check_read_side(physical_port):

    curr_offset = Y_CABLE_DETERMINE_CABLE_READ_SIDE

    result = platform_chassis.get_sfp(
        physical_port).read_eeprom(curr_offset, 1)

    regval_read = struct.unpack(">i", result)

    if ((regval_read >> 2) & 0x01):
        helper_logger.log_info("Reading from TOR A")
        return 1
    elif ((regval_read >> 1) & 0x01):
        helper_logger.log_info("Reading from TOR B")
        return 2
    elif (regval_read & 0x01):
        helper_logger.log_info("Reading from NIC side")
        return 0
    else:
        helper_logger.log_error(
            "Error: unknown status for checking which side regval = {} ".format(result))
        return -1

    return -1


def check_active_linked_tor_side(physical_port):

    curr_offset = Y_CABLE_ACTIVE_TOR_INDICATOR

    result = platform_chassis.get_sfp(
        physical_port).read_eeprom(curr_offset, 1)

    regval_read = struct.unpack(">i", result)

    if ((regval_read >> 1) & 0x01):
        helper_logger.log_info("TOR B active linked and actively routing")
        return 2
    elif ((regval_read) & 0x01):
        helper_logger.log_info("TOR A standby linked and actively routing")
        return 1
    elif regval_read == 0:
        helper_logger.log_info("Nothing linked for routing")
        return 0
    else:
        helper_logger.log_error(
            "Error: unknown status for active TOR regval = {} ".format(result))
        return -1

    return -1


def check_if_link_is_active_for_NIC(physical_port):

    curr_offset = Y_CABLE_CHECK_LINK_ACTIVE

    result = platform_chassis.get_sfp(
        physical_port).read_eeprom(curr_offset, 1)

    regval_read = struct.unpack(">i", result)

    if (regval_read & 0x01):
        helper_logger.log_info("NIC link is up")
        return True
    else:
        return False


def check_if_link_is_active_for_torA(physical_port):

    curr_offset = Y_CABLE_CHECK_LINK_ACTIVE

    result = platform_chassis.get_sfp(
        physical_port).read_eeprom(curr_offset, 1)

    regval_read = struct.unpack(">i", result)

    if ((regval_read >> 2) & 0x01):
        helper_logger.log_info("TOR A link is up")
        return True
    else:
        return False


def check_if_link_is_active_for_torB(physical_port):

    curr_offset = Y_CABLE_CHECK_LINK_ACTIVE

    result = platform_chassis.get_sfp(
        physical_port).read_eeprom(curr_offset, 1)

    regval_read = struct.unpack(">i", result)

    if ((regval_read >> 1) & 0x01):
        helper_logger.log_info("TOR B link is up")
        return True
    else:
        return False
