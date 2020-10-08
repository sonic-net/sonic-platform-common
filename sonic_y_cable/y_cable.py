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
    import sonic_platform_base.sonic_sfp.sfputilhelper

    from sonic_py_common import logger

except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


PLATFORM_SPECIFIC_MODULE_NAME = "sfputil"
PLATFORM_SPECIFIC_CLASS_NAME = "SfpUtil"

# definitions of the offset and width for values of MUX register specs of upper page 0x04 info eeprom

Y_CABLE_DETERMINE_CABLE_READ_SIDE = 640
Y_CABLE_CHECK_LINK_ACTIVE = 641
Y_CABLE_SWITCH_MUX_DIRECTION = 642
Y_CABLE_ACTIVE_TOR_INDICATOR = 645


class Y_cable(object):
    ports_read_side_dict = dict()
    active_ports_dict = dict()
    platform_chassis = sonic_platform.platform.Platform().get_chassis()
    platform_sfputil = sonic_platform_base.sonic_sfp.sfputilhelper.SfpUtilHelper()
    logical_port_list = platform_sfputil.logical

    """ TODO: This information about which ports are active , read side etc will
              be part of xcvrd but for now putting all this 
              information within Y cable object itself
    """

    def __init__(self):
        logical_port_list = platform_sfputil.logical
        if logical_port_list is None:
            logger.log_info("could not get the logical port list for Y cable")
            sys.exit(1)

        for logical_port in logical_port_list:
            physical_port = self.logical_port_name_to_physical_port(
                logical_port)
            read_side = self.check_read_side(physical_port_name)
            ports_read_side_dict[logical_port] = read_side
            is_tor_active = self.check_active_linked_side(physical_port_name)
            active_ports_dict[logical_port] = is_tor_active

    def logical_port_name_to_physical_port(port_name):
        if port_name.startswith("Ethernet"):
            if self.platform_sfputil.is_logical_port(port_name):
                return self.platform_sfputil.get_logical_to_physical(port_name)
            else:
                logger.log_error("Invalid port '%s'" % port_name)
                return None
        else:
            return [int(port_name)]

    def toggle_mux_to_active_tor(self, physcal_port):

        regval = 0x2
        buffer = create_string_buffer(1)
        buffer[0] = chr(regval)
        curr_offset = Y_CABLE_SWITCH_MUX_DIRECTION

        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)

        return result

    def toggle_mux_to_standby(self, physcal_port):

        regval = 0x3
        buffer = create_string_buffer(1)
        buffer[0] = chr(regval)
        curr_offset = Y_CABLE_SWITCH_MUX_DIRECTION

        result = platform_chassis.get_sfp(
            physical_port).write_eeprom(curr_offset, 1, buffer)

        return result

    def check_read_side(self, physcal_port):

        curr_offset = Y_CABLE_DETERMINE_CABLE_READ_SIDE

        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)

        if ((int(result[0]) >> 2) & 0x01):
            logger.log_info("Reading from TOR Active")
            return 1
        elif ((int(result[0]) >> 1) & 0x01):
            logger.log_info("Reading from TOR standby")
            return 2
        elif (int(result[0]) & 0x01):
            logger.log_info("Reading from NIC side")
            return 0
        else:
            logger.log_info(
                "Error: unknown status for checking which side regval = {} ".format(result))
            return -1

        return -1

    def check_active_linked_tor_side(self, physcal_port):

        curr_offset = 645

        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)

        if ((int(result[0]) >> 1) & 0x01):
            logger.log_info("TOR active linked and actively routing")
            return 1
        elif (int(result[0]) & 0x01):
            logger.log_info("TOR  standby linked and actively routing")
            return 2
        elif (int(result[0]) == 0):
            logger.log_info("Nothing linked for routing")
            return 0
        else:
            logger.log_info(
                "Error: unknown status for active TOR regval = {} ".format(result))
            return -1

        return -1

    def check_if_link_is_active(self, physical_port):

        curr_offset = Y_CABLE_CHECK_LINK_ACTIVE

        result = platform_chassis.get_sfp(
            physical_port).read_eeprom(curr_offset, 1)

        if ((int(result[0]) >> 1) & 0x01):
            logger.log_info("TOR  linked and actively routing")
            return True
        elif (int(result[0]) & 0x01):
            logger.log_info("TOR  linked and actively routing")
            return True
        elif (int(result[0] << 1) & 0x01):
            logger.log_info("TOR  linked and actively routing")
            return True
