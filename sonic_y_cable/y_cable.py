#
# y_cable.py
#
#  definitions for implementing Y cable access and configurations
#   API's for Y cable functionality in SONiC

try:
    import math
    import time
    import struct
    from ctypes import c_int8

    from sonic_py_common import logger
    import sonic_platform.platform
except ImportError as e:
    # When build python3 xcvrd, it tries to do basic check which will import this file. However,
    # not all platform supports python3 API now, so it could cause an issue when importing
    # sonic_platform.platform. We skip the ImportError here. This is safe because:
    #   1. If any python package is not available, there will be exception when use it
    #   2. Vendors know their platform API version, they are responsible to use correct python
    #   version when importing this file.
    pass

# definitions of the offset with width accommodated for values
# of MUX register specs of upper page 0x04 starting at 640
# info eeprom for Y Cable
OFFSET_IDENTFIER_LOWER_PAGE = 0
OFFSET_IDENTFIER_UPPER_PAGE = 128
OFFSET_DETERMINE_CABLE_READ_SIDE = 640
OFFSET_CHECK_LINK_ACTIVE = 641
OFFSET_SWITCH_MUX_DIRECTION = 642
OFFSET_MUX_DIRECTION = 644
OFFSET_ACTIVE_TOR_INDICATOR = 645
OFFSET_CONFIGURE_PRBS_TYPE = 768
OFFSET_ENABLE_PRBS = 769
OFFSET_INITIATE_BER_MEASUREMENT = 770
OFFSET_TARGET = 794
OFFSET_ENABLE_LOOPBACK = 793
OFFSET_LANE_1_BER_RESULT = 771
OFFSET_MAX_LANES = 2
OFFSET_INITIATE_EYE_MEASUREMENT = 784
OFFSET_LANE_1_EYE_RESULT = 785
OFFSET_PART_NUMBER = 168
OFFSET_VENDOR_NAME = 148
OFFSET_MANUAL_SWITCH_COUNT = 653
OFFSET_AUTO_SWITCH_COUNT = 657
OFFSET_NIC_CURSOR_VALUES = 661
OFFSET_TOR1_CURSOR_VALUES = 681
OFFSET_TOR2_CURSOR_VALUES = 701
OFFSET_NIC_LANE_ACTIVE = 721
OFFSET_INTERNAL_TEMPERATURE = 22
OFFSET_INTERNAL_VOLTAGE = 26
OFFSET_NIC_TEMPERATURE = 727
OFFSET_NIC_VOLTAGE = 729
OFFSET_ENABLE_AUTO_SWITCH = 651

# definitions of targets for getting the cursor
# equalization parameters from the register spec
# the name of the target denotes which side cursor
# values will be retreived

TARGET_NIC = 0
TARGET_TOR1 = 1
TARGET_TOR2 = 2

# definitions of targets for getting the EYE/BER
# and initiating PRBS/Loopback on the Y cable
# the name of the target denotes which side values
# will be retreived/initiated

EYE_PRBS_TARGET_LOCAL = 0
EYE_PRBS_TARGET_TOR1 = 1
EYE_PRBS_TARGET_TOR2 = 2
EYE_PRBS_TARGET_NIC = 3

# definitions of switch counter types
# to be entered by the user in get_switch_count api
# for retreiving the counter values

SWITCH_COUNT_MANUAL = "manual"
SWITCH_COUNT_AUTO = "auto"

FIRMWARE_INFO_PAYLOAD_SIZE = 48
NUM_MCU_SIDE = 3

EEPROM_READ_DATA_INVALID = -1
EEPROM_ERROR = -1
EEPROM_TIMEOUT_ERROR = -1

BER_TIMEOUT_SECS = 1
EYE_TIMEOUT_SECS = 1

MAX_NUM_LANES = 4

# switching modes inside muxcable
SWITCHING_MODE_MANUAL = 0
SWITCHING_MODE_AUTO = 1

# Valid return codes for upgrade firmware routine steps
FIRMWARE_DOWNLOAD_SUCCESS = 0
FIRMWARE_DOWNLOAD_FAILURE = 1
FIRMWARE_ACTIVATE_SUCCESS = 0
FIRMWARE_ACTIVATE_FAILURE = 1
FIRMWARE_ROLLBACK_SUCCESS = 0
FIRMWARE_ROLLBACK_FAILURE = 1

SYSLOG_IDENTIFIER = "sonic_y_cable"

# Global logger instance for helper functions and classes to log
helper_logger = logger.Logger(SYSLOG_IDENTIFIER)

# Global platform_chassis instance to call get_sfp required for read/write eeprom
platform_chassis = None

try:
    platform_chassis = sonic_platform.platform.Platform().get_chassis()
    helper_logger.log_info("chassis loaded {}".format(platform_chassis))
except Exception as e:
    helper_logger.log_warning("Failed to load chassis due to {}".format(repr(e)))


def y_cable_validate_read_data(result, size, physical_port, message):

    if result is not None:
        if isinstance(result, bytearray):
            if len(result) != size:
                LOG_MESSAGE_TEMPLATE = "Error: for checking mux_cable {}, eeprom read returned a size {} not equal to 1 for port {}"
                helper_logger.log_error(LOG_MESSAGE_TEMPLATE.format(message, len(result), physical_port))
                return EEPROM_READ_DATA_INVALID
        else:
            LOG_MESSAGE_TEMPLATE = "Error: for checking mux_cable {}, eeprom read returned an instance value of type {} which is not a bytearray for port {}"
            helper_logger.log_error(LOG_MESSAGE_TEMPLATE.format(message, type(result), physical_port))
            return EEPROM_READ_DATA_INVALID
    else:
        LOG_MESSAGE_TEMPLATE = "Error: for checking mux_cable {}, eeprom read returned a None value for port {} which is not expected"
        helper_logger.log_error(LOG_MESSAGE_TEMPLATE.format(message, physical_port))
        return EEPROM_READ_DATA_INVALID


def hook_y_cable_simulator(target):
    """Decorator to add hook for calling y_cable_simulator_client.

    This decorator updates the y_cable driver functions to call hook functions defined in the y_cable_simulator_client
    module if importing the module is successful. If importing the y_cable_simulator_client module failed, just call
    the original y_cable driver functions defined in this module.

    Args:
        target (function): The y_cable driver function to be updated.
    """
    def wrapper(*args, **kwargs):
        try:
            import y_cable_simulator_client
            y_cable_func = getattr(y_cable_simulator_client, target.__name__, None)
            if y_cable_func and callable(y_cable_func):
                return y_cable_func(*args, **kwargs)
            else:
                return target(*args, **kwargs)
        except ImportError:
            return target(*args, **kwargs)
    wrapper.__name__ = target.__name__
    return wrapper


@hook_y_cable_simulator
def toggle_mux_to_torA(physical_port):
    """
    This API specifically does a hard switch toggle of the Y cable's MUX regardless of link state to
    TOR A. This means if the Y cable is actively routing, the "check_active_linked_tor_side(physical_port)"
    API will now return Tor A. It also implies that if the link is actively routing on this port, Y cable
    MUX will start forwarding packets from TOR A to NIC, and drop packets from TOR B to NIC
    regardless of previous forwarding state. This API basically writes to upper page 4 offset 130 the
    value of 0x2 and expects the MUX to toggle to TOR A. Bit 0 value 0 means TOR A.

    Register Specification at offset 130 is documented below

    Byte offset   bits     Name                    Description
    130           7-2      Reserved                Reserved
                  1        Hard vs. soft switch    0b0 - Switch only if a valid TOR link on target; 0b1 Switch to new target regardless of link status
                  0        Switch Target           Switch Target - 0b0 - TOR#1, 0b1 - TOR#2; default is TOR #1

    Args:
         physical_port:
             an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

    Returns:
        a Boolean, true if the toggle succeeded and false if it did not succeed.
    """

    buffer = bytearray([2])
    curr_offset = OFFSET_SWITCH_MUX_DIRECTION

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to toggle mux to TOR A")
        return False

    return result


@hook_y_cable_simulator
def toggle_mux_to_torB(physical_port):
    """
    This API specifically does a hard switch toggle of the Y cable's MUX regardless of link state to
    TOR B. This means if the Y cable is actively routing, the "check_active_linked_tor_side(physical_port)"
    API will now return Tor B. It also implies that if the link is actively routing on this port, Y cable
    MUX will start forwarding packets from TOR B to NIC, and drop packets from TOR A to NIC
    regardless of previous forwarding state. API basically writes to upper page 4 offset 130 the value
    of 0x3 and expects the MUX to toggle to TOR B. Bit 0 value 1 means TOR B

    Register Specification at offset 130 is documented below

    Byte offset   bits      Name                   Description
    130           7-2       Reserved               Reserved
                  1         Hard vs. soft switch   0b0 - Switch only if a valid TOR link on target; 0b1 Switch to new target regardless of link status
                  0         Switch Target          Switch Target - 0b0 - TOR#1, 0b1 - TOR#2; default is TOR #1

    Args:
         physical_port:
             an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

    Returns:
        a Boolean, true if the toggle succeeded and false if it did not succeed.
    """

    buffer = bytearray([3])
    curr_offset = OFFSET_SWITCH_MUX_DIRECTION

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to toggle mux to TOR B")
        return False

    return result


@hook_y_cable_simulator
def check_read_side(physical_port):
    """
    This API specifically checks which side of the Y cable the reads are actually getting performed
    from, either TOR A or TOR B or NIC and returns the value. API basically reads 1 byte at upper
    page 4 offset 128 and checks which side of the Y cable the read is being performed from.

    Register Specification of upper page 0x4 at offset 128 is documented below

    Byte offset   bits     Name                    Description
                  7-3      Reserved                Determine which side of the cable you are reading from - specifically to differentiate TOR #1 and TOR #2:
                                                   0b1 : Reading from indicated side, 0b0 not reading from that side.
                  2        TOR #1 Side
                  1        TOR #2 Side
                  0        NIC Side
    Args:
         physical_port:
             an Integer, the actual physical port connected to Y end of a Y cable which can which side reading the MUX from

    Returns:
        an Integer, 1 if reading the Y cable from TOR A side(TOR 1).
                  , 2 if reading the Y cable from TOR B side(TOR 2).
                  , 0 if reading the Y cable from NIC side.
                  , -1 if reading the Y cable API fails.
    """

    curr_offset = OFFSET_DETERMINE_CABLE_READ_SIDE

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to check read side")
        return -1

    if result is not None:
        if isinstance(result, bytearray):
            if len(result) != 1:
                helper_logger.log_error("Error: for checking mux_cable read side, eeprom read returned a size {} not equal to 1 for port {}".format(
                    len(result), physical_port))
                return -1
        else:
            helper_logger.log_error("Error: for checking mux_cable read_side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                type(result), physical_port))
            return -1
    else:
        helper_logger.log_error(
            "Error: for checking mux_cable read_side, eeprom read returned a None value for port {} which is not expected".format(physical_port))
        return -1

    regval_read = struct.unpack(">B", result)

    if ((regval_read[0] >> 2) & 0x01):
        helper_logger.log_info("Reading from TOR A")
        return 1
    elif ((regval_read[0] >> 1) & 0x01):
        helper_logger.log_info("Reading from TOR B")
        return 2
    elif (regval_read[0] & 0x01):
        helper_logger.log_info("Reading from NIC side")
        return 0
    else:
        helper_logger.log_error(
            "Error: unknown status for checking which side regval = {} ".format(result))

    return -1


@hook_y_cable_simulator
def check_mux_direction(physical_port):
    """
    This API specifically checks which side of the Y cable mux is currently point to
    and returns either TOR A or TOR B. API basically reads 1 byte at upper page 4 offset 132
    and checks which side the mux is pointing to


    Register Specification of upper page 0x4 at offset 133 is documented below

    Byte offset   bits     Name                           Description
    132           7-0      MUX Switch Status Register     0x00 : MUX pointing at TOR#2, 0x01 MUX pointing at TOR#1 regardless of connection status

    Args:
         physical_port:
             an Integer, the actual physical port connected to a Y cable

    Returns:
        an Integer, 1 if the mux is pointing to TOR A .
                  , 2 if the mux is pointing to TOR B.
                  , -1 if checking which side mux is pointing to API fails.
    """

    curr_offset = OFFSET_MUX_DIRECTION

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to check Active Linked and routing TOR side")
        return -1

    if result is not None:
        if isinstance(result, bytearray):
            if len(result) != 1:
                helper_logger.log_error("Error: for checking mux_cable mux pointing side, eeprom read returned a size {} not equal to 1 for port {}".format(
                    len(result), physical_port))
                return -1
        else:
            helper_logger.log_error("Error: for checking mux_cable mux pointing side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                type(result), physical_port))
            return -1
    else:
        helper_logger.log_error(
            "Error: for checking mux_cable mux pointing side, eeprom read returned a None value from eeprom read for port {} which is not expected".format(physical_port))
        return -1

    regval_read = struct.unpack(">B", result)

    if ((regval_read[0]) & 0x01):
        helper_logger.log_info("mux pointing to TOR A")
        return 1
    elif regval_read[0] == 0:
        helper_logger.log_info("mux pointing to TOR B")
        return 2
    else:
        helper_logger.log_error(
            "Error: unknown status for mux direction regval = {} ".format(result))
        return -1

    return -1


@hook_y_cable_simulator
def check_active_linked_tor_side(physical_port):
    """
    This API specifically checks which side of the Y cable is actively linked and routing
    and returns either TOR A or TOR B. API basically reads 1 byte at upper page 4 offset 133
    and checks which side is actively linked and routing.


    Register Specification of upper page 0x4 at offset 133 is documented below

    Byte offset   bits     Name                     Description
    133           7-0      TOR Active Indicator     0x00, no sides linked and routing frames, 0x01 TOR #1 linked and routing, 0x02, TOR #2 linked and routing

    Args:
         physical_port:
             an Integer, the actual physical port connected to a Y cable

    Returns:
        an Integer, 1 if TOR A is actively linked and routing(TOR 1).
                  , 2 if TOR B is actively linked and routing(TOR 2).
                  , 0 if nothing linked and actively routing
                  , -1 if checking which side linked for routing API fails.
    """

    curr_offset = OFFSET_ACTIVE_TOR_INDICATOR

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to check Active Linked and routing TOR side")
        return -1

    if result is not None:
        if isinstance(result, bytearray):
            if len(result) != 1:
                helper_logger.log_error("Error: for checking mux_cable active linked side, eeprom read returned a size {} not equal to 1 for port {}".format(
                    len(result), physical_port))
                return -1
        else:
            helper_logger.log_error("Error: for checking mux_cable active linked side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                type(result), physical_port))
            return -1
    else:
        helper_logger.log_error(
            "Error: for checking mux_cable active linked side, eeprom read returned a None value from eeprom read for port {} which is not expected".format(physical_port))
        return -1

    regval_read = struct.unpack(">B", result)

    if ((regval_read[0] >> 1) & 0x01):
        helper_logger.log_info("TOR B active linked and actively routing")
        return 2
    elif ((regval_read[0]) & 0x01):
        helper_logger.log_info("TOR A standby linked and actively routing")
        return 1
    elif regval_read[0] == 0:
        helper_logger.log_info("Nothing linked for routing")
        return 0
    else:
        helper_logger.log_error(
            "Error: unknown status for active TOR regval = {} ".format(result))
        return -1

    return -1


@hook_y_cable_simulator
def check_if_link_is_active_for_NIC(physical_port):
    """
    This API specifically checks if NIC side of the Y cable's link is active
    API basically reads 1 byte at upper page 4 offset 129 and checks if the link is active on NIC side

    Register Specification of upper page 0x4 at offset 129 is documented below

    Byte offset   bits     Name                   Description
    129           7-3      Reserved               Cable link status is for each end.  0b1 : Link up, 0b0 link not up.
                  2        TOR #1 Side
                  1        TOR #2 Side
                  0        NIC Side

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable

    Returns:
        a boolean, true if the link is active
                 , false if the link is not active
    """
    curr_offset = OFFSET_CHECK_LINK_ACTIVE

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to check if link is Active on NIC side")
        return -1

    if result is not None:
        if isinstance(result, bytearray):
            if len(result) != 1:
                helper_logger.log_error("Error: for checking mux_cable link is active on NIC side, eeprom read returned a size {} not equal to 1 for port {}".format(
                    len(result), physical_port))
                return -1
        else:
            helper_logger.log_error("Error: for checking mux_cable link is active on NIC side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                type(result), physical_port))
            return -1
    else:
        helper_logger.log_error(
            "Error: for checking mux_cable link is active on NIC side, eeprom read returned a None value from eeprom read for port {} which is not expected".format(physical_port))
        return -1

    regval_read = struct.unpack(">B", result)

    if (regval_read[0] & 0x01):
        helper_logger.log_info("NIC link is up")
        return True
    else:
        return False


@hook_y_cable_simulator
def check_if_link_is_active_for_torA(physical_port):
    """
    This API specifically checks if TOR A side of the Y cable's link is active
    API basically reads 1 byte at upper page 4 offset 129 and checks if the link is active on NIC side

    Register Specification of upper page 0x4 at offset 129 is documented below

    Byte offset   bits     Name                    Description
    129           7-3      Reserved                Cable link status is for each end.  0b1 : Link up, 0b0 link not up.
                  2        TOR #1 Side
                  1        TOR #2 Side
                  0        NIC Side

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable

    Returns:
        a boolean, true if the link is active
                 , false if the link is not active
    """

    curr_offset = OFFSET_CHECK_LINK_ACTIVE

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to check if link is Active on TOR A side")
        return -1

    if result is not None:
        if isinstance(result, bytearray):
            if len(result) != 1:
                helper_logger.log_error("Error: for checking mux_cable link is active on TOR A side, eeprom read returned a size {} not equal to 1 for port {}".format(
                    len(result), physical_port))
                return -1
        else:
            helper_logger.log_error("Error: for checking mux_cable link is active on TOR A side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                type(result), physical_port))
            return -1
    else:
        helper_logger.log_error(
            "Error: for checking mux_cable link is active on TOR A side, eeprom read returned a None value from eeprom read for port {} which is not expected".format(physical_port))
        return -1

    regval_read = struct.unpack(">B", result)

    if ((regval_read[0] >> 2) & 0x01):
        helper_logger.log_info("TOR A link is up")
        return True
    else:
        return False


@hook_y_cable_simulator
def check_if_link_is_active_for_torB(physical_port):
    """
    This API specifically checks if TOR B side of the Y cable's link is active
    API basically reads 1 byte at upper page 4 offset 129 and checks if the link is active on NIC side

    Register Specification of upper page 0x4 at offset 129 is documented below

    Byte offset   bits    Name                  Description
    129           7-3     Reserved              Cable link status is for each end.  0b1 : Link up, 0b0 link not up.
                  2       TOR #1 Side
                  1       TOR #2 Side
                  0       NIC Side

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable

    Returns:
        a boolean, true if the link is active
                 , false if the link is not active
    """

    curr_offset = OFFSET_CHECK_LINK_ACTIVE

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to check if link is Active on TOR B side")
        return -1

    if result is not None:
        if isinstance(result, bytearray):
            if len(result) != 1:
                helper_logger.log_error("Error: for checking mux_cable link is active on TOR B side, eeprom read returned a size {} not equal to 1 for port {}".format(
                    len(result), physical_port))
                return -1
        else:
            helper_logger.log_error("Error: for checking mux_cable link is active on TOR B side, eeprom read returned an instance value of type {} which is not a bytearray for port {}".format(
                type(result), physical_port))
            return -1
    else:
        helper_logger.log_error(
            "Error: for checking mux_cable link is active on TOR B side, eeprom read returned a None value from eeprom read for port {} which is not expected".format(physical_port))
        return -1

    regval_read = struct.unpack(">B", result)

    if ((regval_read[0] >> 1) & 0x01):
        helper_logger.log_info("TOR B link is up")
        return True
    else:
        return False


@hook_y_cable_simulator
def enable_prbs_mode(physical_port, target, mode_value, lane_map):
    """
    This API specifically configures and enables the PRBS mode/type depending upon the mode_value the user provides.
    The mode_value configures the PRBS Type for generation and BER sensing on a per side basis.
    Each side can only R/W its own value.  0x00 = PRBS 9, 0x01 = PRBS 15, 0x02 = PRBS 23, 0x03 = PRBS 31, 0x04-0xFF reserved.
    Target is an integer for selecting which end of the Y cable we want to run PRBS on.
    LaneMap specifies the lane configuration to run the PRBS on.


    Register Specification of upper page 0x5 at offset 128, 129 is documented below

    Byte offset   bits    Name                  Description
    128           7-0     Reserved              PRBS Type for generation and BER sensing on a per side basis.
                                                Each side can only R/W its own value.
                                                0x00 = PRBS 9, 0x01 = PRBS 15, 0x02 = PRBS 23, 0x03 = PRBS 31, 0x04-0xFF reserved

    129           7-4     Reserved
                  3       Lane 4 enable         "Enable PRBS generation on target lane 0b1 :
                                                 Enable, 0b0 disable If any lanes are enabled,
                                                 then that side of cable is removed fro mission mode and no longer passing valid traffic."
                  2       Lane 3 enable
                  1       Lane 2 enable
                  0       Lane 1 enable

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
        target:
             an Integer, the target on which to enable the PRBS
                         EYE_PRBS_TARGET_LOCAL -> local side,
                         EYE_PRBS_TARGET_TOR1 -> TOR 1
                         EYE_PRBS_TARGET_TOR2 -> TOR 2
                         EYE_PRBS_TARGET_NIC -> NIC
        mode_value:
             an Integer, the mode/type for configuring the PRBS mode.
             0x00 = PRBS 9, 0x01 = PRBS 15, 0x02 = PRBS 23, 0x03 = PRBS 31
        lane_map:
             an Integer, representing the lane_map to be run PRBS on
             0bit for lane 0, 1bit for lane1 and so on.
             for example 3 -> 0b'0011 , means running on lane0 and lane1

    Returns:
        a boolean, true if the enable is successful
                 , false if the enable failed
    """

    buffer = bytearray([target])
    curr_offset = OFFSET_TARGET

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
        if result is False:
            return result
        buffer = bytearray([mode_value])
        curr_offset = OFFSET_CONFIGURE_PRBS_TYPE
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
        if result is False:
            return result
        buffer = bytearray([lane_map])
        curr_offset = OFFSET_ENABLE_PRBS
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)

    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to configure the PRBS type")
        return -1

    return result


@hook_y_cable_simulator
def disable_prbs_mode(physical_port, target):
    """
    This API specifically disables the PRBS mode on the physcial port.

    Register Specification of upper page 0x5 at offset 129 is documented below

    Byte offset   bits    Name                  Description
    129           7-4     Reserved
                  3       Lane 4 enable         "Enable PRBS generation on target lane 0b1 :
                                                 Enable, 0b0 disable If any lanes are enabled,
                                                 then that side of cable is removed fro mission mode and no longer passing valid traffic."
                  2       Lane 3 enable
                  1       Lane 2 enable
                  0       Lane 1 enable

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
        target:
             an Integer, the target on which to enable the PRBS
                         EYE_PRBS_TARGET_LOCAL -> local side,
                         EYE_PRBS_TARGET_TOR1 -> TOR 1
                         EYE_PRBS_TARGET_TOR2 -> TOR 2
                         EYE_PRBS_TARGET_NIC -> NIC

    Returns:
        a boolean, true if the disable is successful
                 , false if the disable failed
    """

    buffer = bytearray([target])
    curr_offset = OFFSET_TARGET

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
        if result is False:
            return result
        buffer = bytearray([0])
        curr_offset = OFFSET_ENABLE_PRBS
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)

    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to configure the PRBS type")
        return -1

    return result


@hook_y_cable_simulator
def enable_loopback_mode(physical_port, target, lane_map):
    """
    This API specifically configures and enables the Loopback mode on the port user provides.
    Target is an integer for selecting which end of the Y cable we want to run loopback on.
    LaneMap specifies the lane configuration to run the loopback on.


    Register Specification of upper page 0x5 at offset 153 is documented below

    Byte offset   bits    Name                  Description
    153           7-4                           Reserved
                  3     Lane 4 enable           "Enable loopback generation on target lane 0b1 :
                                                 Enable, 0b0 disable.The cable supports 3 modes of operation : mission mode; PRBS mode or loopback mode.
                                                 Enabling loopback on any lane of any sides puts cable in loopback mode and disables PRBS.
                  2     Lane 3 enable
                  1     Lane 2 enable
                  0     Lane 1 enable

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
        target:
             an Integer, the target on which to enable the PRBS
                         EYE_PRBS_TARGET_LOCAL -> local side,
                         EYE_PRBS_TARGET_TOR1 -> TOR 1
                         EYE_PRBS_TARGET_TOR2 -> TOR 2
                         EYE_PRBS_TARGET_NIC -> NIC
        lane_map:
             an Integer, representing the lane_map to be run PRBS on
             0bit for lane 0, 1bit for lane1 and so on.
             for example 3 -> 0b'0011 , means running on lane0 and lane1

    Returns:
        a boolean, true if the enable is successful
                 , false if the enable failed
    """

    buffer = bytearray([target])
    curr_offset = OFFSET_TARGET

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
        if result is False:
            return result
        buffer = bytearray([lane_map])
        curr_offset = OFFSET_ENABLE_LOOPBACK
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)

    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to configure the PRBS type")
        return -1

    return result


@hook_y_cable_simulator
def disable_loopback_mode(physical_port, target):
    """
    This API specifically disables the Loopback mode on the port user provides.
    Target is an integer for selecting which end of the Y cable we want to run loopback on.


    Register Specification of upper page 0x5 at offset 153 is documented below

    Byte offset   bits    Name                  Description
    153           7-4                           Reserved
                  3     Lane 4 enable           "Enable loopback generation on target lane 0b1 :
                                                 Enable, 0b0 disable.The cable supports 3 modes of operation :
                                                 mission mode; PRBS mode or loopback mode.
                                                 Enabling loopback on any lane of any sides puts cable in loopback mode and disables PRBS.
                  2     Lane 3 enable
                  1     Lane 2 enable
                  0     Lane 1 enable

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
        target:
             an Integer, the target on which to enable the PRBS
                         EYE_PRBS_TARGET_LOCAL -> local side,
                         EYE_PRBS_TARGET_TOR1 -> TOR 1
                         EYE_PRBS_TARGET_TOR2 -> TOR 2
                         EYE_PRBS_TARGET_NIC -> NIC

    Returns:
        a boolean, true if the disable is successful
                 , false if the disable failed
    """

    buffer = bytearray([target])
    curr_offset = OFFSET_TARGET

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
        if result is False:
            return result
        buffer = bytearray([0])
        curr_offset = OFFSET_ENABLE_LOOPBACK
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)

    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to configure the PRBS type")
        return -1

    return result


@hook_y_cable_simulator
def get_ber_info(physical_port, target):
    """
    This API specifically returns the BER (Bit error rate) value for a specfic port.
    The target could be local side, TOR1, TOR2, NIC etc.


    Register Specification of upper page 0x5 at offset 130 is documented below

    Byte offset   bits    Name                     Description
    130           1-0     Initiate BER Measurement "Write 0x00 - initiate gated BER measurement on target side with PRBS traffic
                                                    Write 0x01-0xFF - reserved
                                                    Read 0x00 - BER Gate in process
                                                    Read 0x01 - BER Gate complete, valid values in Lane BER registers
                                                    NB this command is only valid when PRBS has been enabled on at least one lane
                                                    The cable supports 3 modes of operation : mission mode; PRBS mode or loopback mode.
                                                    Enabling PRBS on any lane of any sides puts cable in PRBS mode and disables loopback and mission mode."

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
        target:
             an Integer, the target on which to enable the PRBS
                         EYE_PRBS_TARGET_LOCAL -> local side,
                         EYE_PRBS_TARGET_TOR1 -> TOR 1
                         EYE_PRBS_TARGET_TOR2 -> TOR 2
                         EYE_PRBS_TARGET_NIC -> NIC
    Returns:
        a list, with BER values of lane 0 and lane 1 with corresponding index
    """

    buffer = bytearray([target])
    curr_offset = OFFSET_TARGET

    ber_result = []

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
        if result is False:
            return result
        buffer = bytearray([0])
        curr_offset = OFFSET_INITIATE_BER_MEASUREMENT
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
        if result is False:
            return result
        time_start = time.time()
        while(True):
            done = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
            if y_cable_validate_read_data(done, 1, physical_port, "BER data ready to read") == EEPROM_READ_DATA_INVALID:
                return EEPROM_ERROR
            time_now = time.time()
            time_diff = time_now - time_start
            if done[0] == 1:
                break
            elif time_diff >= BER_TIMEOUT_SECS:
                return EEPROM_TIMEOUT_ERROR

        idx = 0
        curr_offset = OFFSET_LANE_1_BER_RESULT
        for lane in range(MAX_NUM_LANES):
            msb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset+idx, 1)
            if y_cable_validate_read_data(msb_result, 1, physical_port, "BER data msb result") == EEPROM_READ_DATA_INVALID:
                return EEPROM_ERROR
            lsb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset+1+idx, 1)
            if y_cable_validate_read_data(lsb_result, 1, physical_port, "BER data lsb result") == EEPROM_READ_DATA_INVALID:
                return EEPROM_ERROR
            lane_result = msb_result[0] * math.pow(10, (lsb_result[0]-24))
            ber_result.append(lane_result)
            idx += 2

    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to configure the PRBS type")
        return -1

    return ber_result


@hook_y_cable_simulator
def get_eye_info(physical_port, target):
    """
    This API specifically returns the EYE height value for a specfic port.
    The target could be local side, TOR1, TOR2, NIC etc.


    Register Specification of upper page 0x5 at offset 144 is documented below

    Byte offset   bits    Name                     Description
    144           1-0     Initiate EYE Measurement "Write 0x00 - initiate gated eye height measurement on target side with any traffic (PRBS or mission mode)
                                                    Write 0x01-0xFF - reserved
                                                    Read 0x00 - Eye Height Measurement in process
                                                    Read 0x01 - Eye Height Gate complete, valid values in Eye Height Registers
                                                    NB this command can be issued whenever the side is linked, this does not interrupt mission mode traffic"	R/W

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
        target:
             an Integer, the target on which to enable the PRBS
                         EYE_PRBS_TARGET_LOCAL -> local side,
                         EYE_PRBS_TARGET_TOR1 -> TOR 1
                         EYE_PRBS_TARGET_TOR2 -> TOR 2
                         EYE_PRBS_TARGET_NIC -> NIC
    Returns:
        a list, with EYE values of lane 0 and lane 1 with corresponding index
    """

    buffer = bytearray([target])
    curr_offset = OFFSET_TARGET

    eye_result = []

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
        if result is False:
            return result
        buffer = bytearray([0])
        curr_offset = OFFSET_INITIATE_EYE_MEASUREMENT
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
        if result is False:
            return result

        time_start = time.time()
        while(True):
            done = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
            if y_cable_validate_read_data(done, 1, physical_port, "EYE data ready to read") == EEPROM_READ_DATA_INVALID:
                return EEPROM_ERROR
            time_now = time.time()
            time_diff = time_now - time_start
            if done[0] == 1:
                break
            elif time_diff >= EYE_TIMEOUT_SECS:
                return EEPROM_TIMEOUT_ERROR

        idx = 0
        for lane in range(MAX_NUM_LANES):
            curr_offset = OFFSET_LANE_1_EYE_RESULT
            msb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset+idx, 1)
            if y_cable_validate_read_data(msb_result, 1, physical_port, "EYE data msb result") == EEPROM_READ_DATA_INVALID:
                return EEPROM_ERROR
            lsb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset+1+idx, 1)
            if y_cable_validate_read_data(lsb_result, 1, physical_port, "EYE data lsb result") == EEPROM_READ_DATA_INVALID:
                return EEPROM_ERROR
            lane_result = (msb_result[0] << 8 | lsb_result[0])
            eye_result.append(lane_result)
            idx += 2

    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to configure the PRBS type")
        return -1

    return eye_result


@hook_y_cable_simulator
def get_part_number(physical_port):
    """
    This API specifically returns the part number of the Y cable for a specfic port.

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
    Returns:
        a string, with part number
    """

    curr_offset = OFFSET_PART_NUMBER

    if platform_chassis is not None:
        part_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 16)
        if y_cable_validate_read_data(part_result, 16, physical_port, "Part number") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get part number")
        return -1

    part_number = str(part_result.decode())

    return part_number


@hook_y_cable_simulator
def get_vendor(physical_port):
    """
    This API specifically returns the vendor name of the Y cable for a specfic port.

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
    Returns:
        a string, with vendor name
    """

    curr_offset = OFFSET_VENDOR_NAME

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 16)
        if y_cable_validate_read_data(result, 16, physical_port, "Vendor name") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get Vendor name")
        return -1

    vendor_name = str(result.decode())

    return vendor_name


@hook_y_cable_simulator
def get_switch_count(physical_port, count_type):
    """
    This API specifically returns the switch count to change the Active TOR which has
    been done manually by the user.

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
        count_type:
             a string, for getting the count type
                      "manual" -> manual switch count
                      "auto" -> automatic switch count
    Returns:
        an integer, the number of times manually the Y-cable has been switched
    """

    if count_type == SWITCH_COUNT_MANUAL:
        curr_offset = OFFSET_MANUAL_SWITCH_COUNT
    elif count_type == SWITCH_COUNT_AUTO:
        curr_offset = OFFSET_AUTO_SWITCH_COUNT
    else:
        helper_logger.log_error("not a valid count_type, failed to get switch count")
        return -1

    count = 0

    if platform_chassis is not None:
        msb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(msb_result, 1, physical_port, "{} switch count msb result".format(count_type)) == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        msb_result_1 = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset + 1, 1)
        if y_cable_validate_read_data(msb_result_1, 1, physical_port, "{} switch count msb result 1".format(count_type)) == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        msb_result_2 = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset + 2, 1)
        if y_cable_validate_read_data(msb_result_2, 1, physical_port, "{} switch count msb result 2".format(count_type)) == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        lsb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset+3, 1)
        if y_cable_validate_read_data(lsb_result, 1, physical_port, "{} switch count lsb result".format(count_type)) == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        count = (msb_result[0] << 24 | msb_result_1[0] << 16 | msb_result_2[0] << 8 | lsb_result[0])

    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get manual switch count")
        return -1

    return count


@hook_y_cable_simulator
def get_target_cursor_values(physical_port, lane, target):
    """
    This API specifically returns the cursor equalization parameters for a target(NIC, TOR1, TOR2).
    This includes pre one, pre two , main, post one, post two cursor values

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
        lane:
             an Integer, the lane on which to collect the cursor values
                         1 -> lane 1,
                         2 -> lane 2
                         3 -> lane 3
                         4 -> lane 4
        target:
             an Integer, the actual target to get the cursor values on
                         TARGET_NIC -> NIC,
                         TARGET_TOR1-> TOR1,
                         TARGET_TOR2 -> TOR2
    Returns:
        an list, with  pre one, pre two , main, post one, post two cursor values in the order
    """

    curr_offset = OFFSET_NIC_CURSOR_VALUES

    result = []

    if platform_chassis is not None:
        pre1 = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5, 1)
        if y_cable_validate_read_data(pre1, 1, physical_port, "target cursor result") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        result.append(c_int8(pre1[0]).value)
        pre2 = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5 + 1, 1)
        if y_cable_validate_read_data(pre2, 1, physical_port, "target cursor result") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        result.append(c_int8(pre2[0]).value)
        main = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5 + 2, 1)
        if y_cable_validate_read_data(main, 1, physical_port, "target cursor result") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        result.append(c_int8(main[0]).value)
        post1 = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5 + 3, 1)
        if y_cable_validate_read_data(post1, 1, physical_port, "target cursor result") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        result.append(c_int8(post1[0]).value)
        post2 = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset + (target)*20 + (lane-1)*5 + 4, 1)
        if y_cable_validate_read_data(post2, 1, physical_port, "target cursor result") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        result.append(c_int8(post2[0]).value)

    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get target cursor values")
        return -1

    return result


@hook_y_cable_simulator
def check_if_nic_lanes_active(physical_port):
    """
    This API specifically returns the byte value which denotes which nic lanes
    are detected and active

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
    Returns:
        an integer, with  lower 4 bits representing which lanes are active from 1, 2, 3, 4
             in that order.
    """

    curr_offset = OFFSET_NIC_LANE_ACTIVE

    result = None

    if platform_chassis is not None:
        res = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(res, 1, physical_port, "nic lanes active") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        result = res[0]

    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get NIC lanes active")
        return -1

    return result


@hook_y_cable_simulator
def get_firmware_version(physical_port, target):

    data = bytearray(FIRMWARE_INFO_PAYLOAD_SIZE)

    if platform_chassis is not None:
        for byte_idx in range(0, FIRMWARE_INFO_PAYLOAD_SIZE):
            curr_offset = 0xfc * 128 + 128 + byte_idx
            read_out = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
            if y_cable_validate_read_data(read_out, 1, physical_port, "firmware info") == EEPROM_READ_DATA_INVALID:
                return EEPROM_ERROR
            data[byte_idx] = read_out[0]
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get NIC lanes active")
        return -1

    result = {}
    NUM_MCU_SIDE = 3

    base_addr = int(target * (FIRMWARE_INFO_PAYLOAD_SIZE / NUM_MCU_SIDE))
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

        '''TODO: the fields with slot number as suffix are redundant and must
        be removed eventually since they are covered by the fields which
        have version as prefix. '''

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


@hook_y_cable_simulator
def get_internal_voltage_temp(physical_port):

    curr_offset = OFFSET_INTERNAL_TEMPERATURE
    if platform_chassis is not None:
        result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(result, 1, physical_port, "internal voltage") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        curr_offset = OFFSET_INTERNAL_VOLTAGE
        msb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(msb_result, 1, physical_port, "internal temperature msb") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        lsb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset+1, 1)
        if y_cable_validate_read_data(lsb_result, 1, physical_port, "internal temperature lsb") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR

        temp = result[0]
        voltage = (((msb_result[0] << 8) | lsb_result[0]) * 0.0001)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get internal voltage and temp")
        return -1

    return temp, voltage


@hook_y_cable_simulator
def get_nic_voltage_temp(physical_port):

    curr_offset = OFFSET_NIC_TEMPERATURE
    if platform_chassis is not None:
        result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(result, 1, physical_port, "internal voltage") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        curr_offset = OFFSET_NIC_VOLTAGE
        msb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(msb_result, 1, physical_port, "internal temperature msb") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        lsb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset+1, 1)
        if y_cable_validate_read_data(lsb_result, 1, physical_port, "internal temperature lsb") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR

        temp = result[0]
        voltage = (((msb_result[0] << 8) | lsb_result[0]) * 0.0001)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get NIC voltage and temp")
        return -1

    return temp, voltage


@hook_y_cable_simulator
def get_local_temperature(physical_port):

    curr_offset = OFFSET_INTERNAL_TEMPERATURE
    if platform_chassis is not None:
        result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(result, 1, physical_port, "local temperature") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        temp = result[0]
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get local temp")
        return -1

    return temp


@hook_y_cable_simulator
def get_local_voltage(physical_port):

    if platform_chassis is not None:
        curr_offset = OFFSET_INTERNAL_VOLTAGE
        msb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(msb_result, 1, physical_port, "local voltage MSB") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        lsb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset+1, 1)
        if y_cable_validate_read_data(lsb_result, 1, physical_port, "local voltage LSB") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR

        voltage = (((msb_result[0] << 8) | lsb_result[0]) * 0.0001)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get local voltage")
        return -1

    return voltage


@hook_y_cable_simulator
def get_nic_temperature(physical_port):

    curr_offset = OFFSET_NIC_TEMPERATURE
    if platform_chassis is not None:
        result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(result, 1, physical_port, "NIC temperature") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        temp = result[0]
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get NIC temp")
        return -1

    return temp


@hook_y_cable_simulator
def get_nic_voltage(physical_port):

    curr_offset = OFFSET_NIC_VOLTAGE
    if platform_chassis is not None:
        msb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(msb_result, 1, physical_port, "NIC voltage MSB") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
        lsb_result = platform_chassis.get_sfp(physical_port).read_eeprom(curr_offset+1, 1)
        if y_cable_validate_read_data(lsb_result, 1, physical_port, "NIC voltage LSB") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR

        voltage = (((msb_result[0] << 8) | lsb_result[0]) * 0.0001)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get NIC voltage")
        return -1

    return voltage


@hook_y_cable_simulator
def download_firmware(physical_port, fwfile):
    """ This routine should download and store the firmware on all the
    components of the Y cable of the port specified.
    This should include any internal transfers, checksum validation etc.
    from TOR to TOR or TOR to NIC side of the firmware specified by the fwfile.
    This basically means that the firmware which is being downloaded should be
    available to be activated (start being utilized by the cable) once this API is
    successfully executed.
    Note that this API should ideally not require any rollback even if it fails
    as this should not interfere with the existing cable functionality because
    this has not been activated yet.

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
        fwfile:
             a string, a path to the file which contains the firmware image.
             Note that the firmware file can be in the format of the vendor's
             choosing (binary, archive, etc.). But note that it should be one file
             which contains firmware for all components of the Y-cable
    Returns:
        an Integer:
             a predefined code stating whether the firmware download was successful
             or an error code as to what was the cause of firmware download failure
    """

    return FIRMWARE_DOWNLOAD_SUCCESS


@hook_y_cable_simulator
def activate_firmware(physical_port):
    """ This routine should activate the downloaded firmware on all the
    components of the Y cable of the port specified.
    This API is meant to be used in conjunction with download_firmware API, and
    should be called once download_firmware API is succesful.
    This means that the firmware which has been downloaded should be
    activated (start being utilized by the cable) once this API is
    successfully executed.

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
    Returns:
        an Integer:
             a predefined code stating whether the firmware activate was successful
             or an error code as to what was the cause of firmware activate failure
    """

    return FIRMWARE_ACTIVATE_SUCCESS


@hook_y_cable_simulator
def rollback_firmware(physical_port):
    """ This routine should rollback the firmware to the previous version
    which was being used by the cable. This API is intended to be called when the
    user either witnesses an activate_firmware API failure or sees issues with
    newer firmware in regards to stable cable functioning.

    Args:
        physical_port:
             an Integer, the actual physical port connected to a Y cable
    Returns:
        an Integer:
             a predefined code stating whether the firmware rollback was successful
             or an error code as to what was the cause of firmware rollback failure
    """

    return FIRMWARE_ROLLBACK_SUCCESS


@hook_y_cable_simulator
def set_switching_mode(physical_port, mode):
    """
    This API specifically enables the auto switching or manual switching feature on the muxcable,
    depending upon the mode entered by the user.
    Autoswitch feature if enabled actually does an automatic toggle of the mux in case the active
    side link goes down and basically points the mux to the other side.

    Register Specification at offset 139 is documented below

    Byte offset   bits      Name                   Description
    139           0         Switch Target          "0x01 - enable auto switchover; if both TOR#1 and TOR#2 are linked and the active link fails,
                                                    the cable will automatically switchover to the inactive link.
                                                    0x00 - disable auto switchover.  Default is disabled."


    Args:
         physical_port:
             an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX
         mode:
             an Integer, specifies which type of switching mode we set the muxcable to
             either SWITCHING_MODE_AUTO or SWITCHING_MODE_MANUAL

    Returns:
        a Boolean, true if the switch succeeded and false if it did not succeed.
    """

    if mode == SWITCHING_MODE_AUTO:
        buffer = bytearray([1])
    elif mode == SWITCHING_MODE_MANUAL:
        buffer = bytearray([0])
    else:
        helper_logger.log_error(
            "ERR: invalid mode provided for autoswitch feature, failed to do a switch")
        return False

    curr_offset = OFFSET_ENABLE_AUTO_SWITCH

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to do a switch target")
        return False

    return result


@hook_y_cable_simulator
def get_switching_mode(physical_port):
    """
    This API specifically returns which type of switching mode the cable is set to auto/manual

    Register Specification at offset 139 is documented below

    Byte offset   bits      Name                   Description
    139           0         Switch Target          "0x01 - enable auto switchover; if both TOR#1 and TOR#2 are linked and the active link fails,
                                                    the cable will automatically switchover to the inactive link.
                                                    0x00 - disable auto switchover.  Default is disabled."


    Args:
         physical_port:
             an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

    Returns:
        an Integer, SWITCHING_MODE_AUTO if auto switch is enabled.
                    SWITCHING_MODE_MANUAL if manual switch is enabled.
    """

    curr_offset = OFFSET_ENABLE_AUTO_SWITCH

    if platform_chassis is not None:
        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)
        if y_cable_validate_read_data(result, 1, physical_port, "check if autoswitch is enabled") == EEPROM_READ_DATA_INVALID:
            return EEPROM_ERROR
    else:
        helper_logger.log_error("platform_chassis is not loaded, failed to get the switch mode")
        return -1

    if result[0] == 1:
        return SWITCHING_MODE_AUTO
    else:
        return SWITCHING_MODE_MANUAL
