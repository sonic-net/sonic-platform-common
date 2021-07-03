"""
    y_cable_base.py

    Base class for implementing Y-Cable specific functionality in SONiC.
    This is the base class of sonic_y_cable implentation. A vendor-specific
    implementation of a 'YCable' class needs to inherit from this class.
    Classes derived from this class provide the ability to interact
    with a vendor-specific Y-Cable
"""

#
# YCableBase ===================================================================
#

class YCableBase():

    # definitions of targets for getting the various fields/cursor
    # equalization parameters from the register spec.
    # the name of the target denotes which side MCU
    # values will be retrieved from or written to
    # on the Y-Cable

    TARGET_UNKNOWN = -1
    TARGET_NIC = 0
    TARGET_TOR_A = 1
    TARGET_TOR_B = 2

    # definitions of targets for getting the EYE/BER
    # and initiating PRBS/Loopback on the Y cable
    # the name of the target denotes which side values
    # will be retreived/initiated

    EYE_PRBS_LOOPBACK_TARGET_NIC = 0
    EYE_PRBS_LOOPBACK_TARGET_TOR_A = 1
    EYE_PRBS_LOOPBACK_TARGET_TOR_B = 2
    EYE_PRBS_LOOPBACK_TARGET_LOCAL = 3

    # definitions of switch counter types
    # to be entered by the user in get_switch_count api
    # for retreiving the counter values

    SWITCH_COUNT_MANUAL = "manual"
    SWITCH_COUNT_AUTO = "auto"

    # switching modes inside Y-Cable
    SWITCHING_MODE_MANUAL = 0
    SWITCHING_MODE_AUTO = 1

    # definitions of the FEC mode to be configured
    # on a port/cable
    FEC_MODE_NONE = 0
    FEC_MODE_RS = 1
    FEC_MODE_FC = 2

    # definitions of the modes to be run for loopback mode
    # on the port/cable
    LOOPBACK_MODE_NEAR_END = 0
    LOOPBACK_MODE_FAR_END = 1

    # Valid return codes for upgrade firmware routine steps
    FIRMWARE_DOWNLOAD_SUCCESS = 0
    FIRMWARE_DOWNLOAD_FAILURE = 1
    FIRMWARE_ACTIVATE_SUCCESS = 0
    FIRMWARE_ACTIVATE_FAILURE = 1
    FIRMWARE_ROLLBACK_SUCCESS = 0
    FIRMWARE_ROLLBACK_FAILURE = 1

    # definitions of PRBS run modes
    PRBS_DIRECTION_BOTH = 0
    PRBS_DIRECTION_GENERATOR = 1
    PRBS_DIRECTION_CHECKER = 2

    def __init__(self, port, logger):
        """
        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
            logger:
                 a logging instance object, must be an instance of the Logger class from sonic_py_common instantiated
                 by the program which is instantiating this class.

        """
        self.port = port
        self._logger = logger

    def log_warning(self, msg):
        self._logger.log_warning("y_cable_port {}: {}".format(self.port, msg))

    def log_error(self, msg):
        self._logger.log_error("y_cable_port {}: {}".format(self.port, msg))

    def log_info(self, msg):
        self._logger.log_info("y_cable_port {}: {}".format(self.port, msg))

    def log_notice(self, msg):
        self._logger.log_notice("y_cable_port {}: {}".format(self.port, msg))

    def log_debug(self, msg):
        self._logger.log_debug("y_cable_port {}: {}".format(self.port, msg))

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

        raise NotImplementedError

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
        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError


    def get_vendor(self):
        """
        This API returns the vendor name of the Y cable for a specfic port.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a string, with vendor name
        """

        raise NotImplementedError

    def get_part_number(self):
        """
        This API returns the part number of the Y cable for a specfic port.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a string, with part number
        """

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

    def get_nic_temperature(self):
        """
        This API returns nic temperature of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            an Integer, the temperature of the NIC MCU
        """

        raise NotImplementedError

    def get_local_temperature(self):
        """
        This API returns local ToR temperature of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            an Integer, the temperature of the local MCU
        """

        raise NotImplementedError

    def get_nic_voltage(self):
        """
        This API returns nic voltage of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a float, the voltage of the NIC MCU
        """

        raise NotImplementedError

    def get_local_voltage(self):
        """
        This API returns local ToR voltage of the physical port for which this API is called.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a float, the voltage of the local MCU
        """

        raise NotImplementedError

    def get_alive_status(self):
        """
        This API checks if cable is connected to all the ports and is healthy.
        The port on which this API is called for can be referred using self.port.

        Args:

        Returns:
            a boolean, True if the cable is alive
                     , False if the cable is not alive
        """

        raise NotImplementedError

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

        raise NotImplementedError

    def create_port(self, speed, fec_mode_tor_a=FEC_MODE_NONE, fec_mode_tor_b=FEC_MODE_NONE,
                    fec_mode_nic=FEC_MODE_NONE, anlt_tor_a=False, anlt_tor_b= False, anlt_nic=False):
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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError

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
                 for example 3 -> 0b'0011, means running on lane0 and lane1

        Returns:
            a boolean, True if the enable is successful
                     , False if the enable failed
        """

        raise NotImplementedError

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

        raise NotImplementedError

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

        raise NotImplementedError


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
