"""
    y_cable_base.py

    Base class for implementing Y-Cable specific functionality in SONiC.
    This is the base class of sonic_y_cable implentation. A vendor specific 
    implementation of YCable needs to inherit from this class.
    Classes derived from this class provide the ability to interact
    with a vendor specific Y-Cable
"""


class YCableBase(object):

    # definitions of targets for getting the various fields/cursor
    # equalization parameters from the register spec
    # the name of the target denotes which side MCU
    # values will be retreived on the Y-Cable

    TARGET_UNKNOWN = -1
    TARGET_NIC = 0
    TARGET_TOR_A = 1
    TARGET_TOR_B = 2

    # definitions of targets for getting the EYE/BER
    # and initiating PRBS/Loopback on the Y cable
    # the name of the target denotes which side values
    # will be retreived/initiated

    EYE_PRBS_TARGET_LOCAL = 0
    EYE_PRBS_TARGET_TOR_A = 1
    EYE_PRBS_TARGET_TOR_B = 2
    EYE_PRBS_TARGET_NIC = 3

    # definitions of switch counter types
    # to be entered by the user in get_switch_count api
    # for retreiving the counter values

    SWITCH_COUNT_MANUAL = "manual"
    SWITCH_COUNT_AUTO = "auto"

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

    def __init__(self, port):
        self.port = port

    def toggle_mux_to_torA(self, port):
        """
        This API specifically does a hard switch toggle of the Y cable's MUX regardless of link state to
        TOR A. This means if the Y cable is actively sending traffic, the "check_active_linked_tor_side"
        API will now return Tor A. It also implies that if the link is actively sending traffic on this port,
        Y cable MUX will start forwarding packets from TOR A to NIC, and drop packets from TOR B to NIC
        regardless of previous forwarding state.

        Args:
            port:
            an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

        Returns:
            a Boolean, True if the toggle succeeded and False if it did not succeed.
        """

        raise NotImplementedError

    def toggle_mux_to_torB(self, port):
        """
        This API specifically does a hard switch toggle of the Y cable's MUX regardless of link state to
        TOR B. This means if the Y cable is actively sending traffic, the "check_active_linked_tor_side"
        API will now return Tor B. It also implies that if the link is actively sending traffic on this port,
        Y cable. MUX will start forwarding packets from TOR B to NIC, and drop packets from TOR A to NIC
        regardless of previous forwarding state.

        Args:
            port:
                an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

        Returns:
            a Boolean, True if the toggle succeeded and False if it did not succeed.
        """
        raise NotImplementedError

    def check_read_side(self, port):
        """
        This API specifically checks which side of the Y cable the reads are actually getting performed
        from, either TOR A or TOR B or NIC and returns the value.

        Args:
            port:
                an Integer, the actual physical port connected to Y end of a Y cable which can which side reading the MUX from

        Returns:
            One of the following predefined constants:
                TARGET_TOR_A, if reading the Y cable from TOR A side.
                TARGET_TOR_B, if reading the Y cable from TOR B side.
                TARGET_NIC, if reading the Y cable from NIC side.
                TARGET_UNKNOWN, if reading the Y cable API fails.
        """

        raise NotImplementedError

    def check_mux_direction(self, port):
        """
        This API specifically checks which side of the Y cable mux is currently point to
        and returns either TOR A or TOR B. Note that this API should return mux-direction
        regardless of whether the link is active and sending traffic or not.

        Args:
            port:
                an Integer, the actual physical port connected to a Y cable

        Returns:
            One of the following predefined constants:
                TARGET_TOR_A, if mux is pointing to TOR A side.
                TARGET_TOR_B, if mux is pointing to TOR B side.
                TARGET_UNKNOWN, if mux direction API fails.
        """

        raise NotImplementedError

    def check_active_linked_tor_side(self, port):
        """
        This API specifically checks which side of the Y cable is actively linked and sending traffic
        and returns either TOR A or TOR B.

        Args:
            port:
                an Integer, the actual physical port connected to a Y cable

        Returns:
            One of the following predefined constants:
                TARGET_TOR_A, if TOR A is actively linked and sending traffic.
                TARGET_TOR_B, if TOR B is actively linked and sending traffic.
                TARGET_UNKNOWN, if checking which side is linked and sending traffic API fails.
        """

        raise NotImplementedError

    def check_if_link_is_active_for_NIC(self, port):
        """
        This API specifically checks if NIC side of the Y cable's link is active

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable

        Returns:
            a boolean, True if the link is active
                     , False if the link is not active
        """

        raise NotImplementedError

    def check_if_link_is_active_for_torA(self, port):
        """
        This API specifically checks if tor A side of the Y cable's link is active

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable

        Returns:
            a boolean, True if the link is active
                     , False if the link is not active
        """

        raise NotImplementedError

    def check_if_link_is_active_for_torB(self, port):
        """
        This API specifically checks if tor B side of the Y cable's link is active

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable

        Returns:
            a boolean, True if the link is active
                     , False if the link is not active
        """

        raise NotImplementedError

    def get_eye_info(self, port):
        """
        This API specifically returns the EYE height value for a specfic port.
        The target could be local side, TOR_A, TOR_B, NIC etc.

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
            target:
                 One of the following predefined constants, the target on which to get the eye:
                     EYE_PRBS_TARGET_LOCAL -> local side,
                     EYE_PRBS_TARGET_TOR_A -> TOR A
                     EYE_PRBS_TARGET_TOR_B -> TOR B
                     EYE_PRBS_TARGET_NIC -> NIC
        Returns:
            a list, with EYE values of lane 0 lane 1 lane 2 lane 3 with corresponding index
        """

        raise NotImplementedError

    def get_ber_info(self, port):
        """
        This API specifically returns the BER (Bit error rate) value for a specfic port.
        The target could be local side, TOR_A, TOR_B, NIC etc.

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
            target:
                 One of the following predefined constants, the target on which to get the BER:
                     EYE_PRBS_TARGET_LOCAL -> local side,
                     EYE_PRBS_TARGET_TOR_A -> TOR A
                     EYE_PRBS_TARGET_TOR_B -> TOR B
                     EYE_PRBS_TARGET_NIC -> NIC
        Returns:
            a list, with BER values of lane 0 lane 1 lane 2 lane 3 with corresponding index
        """

        raise NotImplementedError

    def get_vendor(self, port):
        """
        This API specifically returns the vendor name of the Y cable for a specfic port.

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
        Returns:
            a string, with vendor name
        """

        raise NotImplementedError

    def get_part_number(self, port):
        """
        This API specifically returns the part number of the Y cable for a specfic port.

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
        Returns:
            a string, with part number
        """

        raise NotImplementedError

    def get_switch_count(self, port, count_type):
        """
        This API specifically returns the switch count to change the Active TOR which has
        been done manually by the user.

        Args:
            port:
                an Integer, the actual physical port connected to a Y cable
            count_type:
                One of the following predefined constants, for getting the count type:
                    SWITCH_COUNT_MANUAL -> manual switch count
                    SWITCH_COUNT_AUTO -> automatic switch count
            Returns:
                an integer, the number of times manually the Y-cable has been switched
        """

        raise NotImplementedError

    def get_target_cursor_values(self, port, lane, target):
        """
        This API specifically returns the cursor equalization parameters for a target(NIC, TOR_A, TOR_B).
        This includes pre one, pre two , main, post one, post two cursor values

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
            lane:
                 an Integer, the lane on which to collect the cursor values
                             1 -> lane 1,
                             2 -> lane 2
                             3 -> lane 3
                             4 -> lane 4
            target:
                One of the following predefined constants, the actual target to get the cursor values on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A-> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
            a list, with  pre one, pre two , main, post one, post two cursor values in the order
        """

        raise NotImplementedError

    def get_firmware_version(self, port, target):
        """
        This routine should return the active, inactive and next (committed)
        firmware running on the target. Each of the version values in this context
        could be a string with a major and minor number and a build value.

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
            target:
                One of the following predefined constants, the actual target to get the firmware version on:
                     TARGET_NIC -> NIC,
                     TARGET_TOR_A-> TORA,
                     TARGET_TOR_B -> TORB
        Returns:
            a Dictionary:
                 with version_active, version_inactive and version_next keys
                 and their corresponding values

        """

        raise NotImplementedError

    def download_firmware(self, port, fwfile):
        """
        This routine should download and store the firmware on all the
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
            port:
                 an Integer, the actual physical port connected to a Y cable
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

    def activate_firmware(self, port, fwfile=None):
        """
        This routine should activate the downloaded firmware on all the
        components of the Y cable of the port specified.
        This API is meant to be used in conjunction with download_firmware API, and
        should be called once download_firmware API is succesful.
        This means that the firmware which has been downloaded should be
        activated (start being utilized by the cable) once this API is
        successfully executed.

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
            fwfile:
                 a string, a path to the file which contains the firmware image.
                 Note that the firmware file can be in the format of the vendor's
                 choosing (binary, archive, etc.). But note that it should be one file
                 which contains firmware for all components of the Y-cable. In case the
                 vendor chooses to pass this file in activate_firmware, the API should
                 have the logic to retreive the firmware version from this file
                 which has to be activated on the componenets of the Y-Cable
                 this API has been called for.
        Returns:
            One of the following predefined constants:
                FIRMWARE_ACTIVATE_SUCCESS
                FIRMWARE_ACTIVATE_FAILURE
        """

        raise NotImplementedError

    def rollback_firmware(self, port):
        """
        This routine should rollback the firmware to the previous version
        which was being used by the cable. This API is intended to be called when the
        user either witnesses an activate_firmware API failure or sees issues with
        newer firmware in regards to stable cable functioning.

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
        Returns:
            One of the following predefined constants:
                FIRMWARE_ROLLBACK_SUCCESS
                FIRMWARE_ROLLBACK_FAILURE
        """

        raise NotImplementedError

    def set_switching_mode(self, port, mode):
        """
        This API specifically enables the auto switching or manual switching feature on the muxcable,
        depending upon the mode entered by the user.
        Autoswitch feature if enabled actually does an automatic toggle of the mux in case the active
        side link goes down and basically points the mux to the other side.

        Args:
             port:
                 an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX
             mode:
                 One of the following predefined constants:
                 SWITCHING_MODE_AUTO
                 SWITCHING_MODE_MANUAL

                 specifies which type of switching mode we set the muxcable to
                 either SWITCHING_MODE_AUTO or SWITCHING_MODE_MANUAL

        Returns:
            a Boolean, True if the switch succeeded and False if it did not succeed.
        """

        raise NotImplementedError

    def get_switching_mode(self, port):
        """
        This API specifically returns which type of switching mode the cable is set to auto/manual

        Args:
             port:
                 an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

        Returns:
            One of the following predefined constants:
               SWITCHING_MODE_AUTO if auto switch is enabled.
               SWITCHING_MODE_MANUAL if manual switch is enabled.
        """

        raise NotImplementedError

    def get_nic_temperature(self, port):
        """
        This API specifically returns nic temperature of the physical port specified

        Args:
             port:
                 an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

        Returns:
            an Integer, the temperature of the NIC MCU
        """

        raise NotImplementedError

    def get_local_temperature(self, port):
        """
        This API specifically returns local ToR temperature of the physical port specified

        Args:
             port:
                 an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

        Returns:
            an Integer, the temperature of the local MCU
        """

        raise NotImplementedError

    def get_nic_voltage(self, port):
        """
        This API specifically returns nic voltage of the physical port specified

        Args:
             port:
                 an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

        Returns:
            a float, the voltage of the NIC MCU
        """

        raise NotImplementedError

    def get_local_voltage(self, port):
        """
        This API specifically returns local ToR voltage of the physical port specified

        Args:
             port:
                 an Integer, the actual physical port connected to Y end of a Y cable which can toggle the MUX

        Returns:
            a float, the voltage of the local MCU
        """

        raise NotImplementedError

    def enable_prbs_mode(self, port, target, mode_value, lane_map):
        """
        This API specifically configures and enables the PRBS mode/type depending upon the mode_value the user provides.
        The mode_value configures the PRBS Type for generation and BER sensing on a per side basis.
        Target is an integer for selecting which end of the Y cable we want to run PRBS on.
        LaneMap specifies the lane configuration to run the PRBS on.
        Note that this is a diagnostic mode command and must not run during normal traffic/switch operation

        Args:
            port:
                an Integer, the actual physical port connected to a Y cable
            target:
                One of the following predefined constants, the target on which to enable the PRBS:
                    EYE_PRBS_TARGET_LOCAL -> local side,
                    EYE_PRBS_TARGET_TOR_A -> TOR A
                    EYE_PRBS_TARGET_TOR_B -> TOR B
                    EYE_PRBS_TARGET_NIC -> NIC
            mode_value:
                 an Integer, the mode/type for configuring the PRBS mode.

            lane_map:
                 an Integer, representing the lane_map to be run PRBS on
                 0bit for lane 0, 1bit for lane1 and so on.
                 for example 3 -> 0b'0011 , means running on lane0 and lane1

        Returns:
            a boolean, True if the enable is successful
                     , False if the enable failed

        """

        raise NotImplementedError

    def disable_prbs_mode(self, port, target):
        """
        This API specifically disables the PRBS mode on the physical port.

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
            target:
                One of the following predefined constants, the target on which to disable the PRBS:
                    EYE_PRBS_TARGET_LOCAL -> local side,
                    EYE_PRBS_TARGET_TOR_A -> TOR A
                    EYE_PRBS_TARGET_TOR_B -> TOR B
                    EYE_PRBS_TARGET_NIC -> NIC

        Returns:
            a boolean, True if the disable is successful
                     , False if the disable failed
        """

        raise NotImplementedError

    def enable_loopback_mode(self, port, target, lane_map):
        """
        This API specifically configures and enables the Loopback mode on the port user provides.
        Target is an integer for selecting which end of the Y cable we want to run loopback on.
        LaneMap specifies the lane configuration to run the loopback on.
        Note that this is a diagnostic mode command and must not run during normal traffic/switch operation

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
            target:
                One of the following predefined constants, the target on which to enable the loopback:
                    EYE_PRBS_TARGET_LOCAL -> local side,
                    EYE_PRBS_TARGET_TOR_A -> TOR A
                    EYE_PRBS_TARGET_TOR_B -> TOR B
                    EYE_PRBS_TARGET_NIC -> NIC
            lane_map:
                 an Integer, representing the lane_map to be run PRBS on
                 0bit for lane 0, 1bit for lane1 and so on.
                 for example 3 -> 0b'0011 , means running on lane0 and lane1

        Returns:
            a boolean, True if the enable is successful
                     , False if the enable failed
        """

        raise NotImplementedError

    def disable_loopback_mode(self, port, target):
        """
        This API specifically disables the Loopback mode on the port user provides.
        Target is an integer for selecting which end of the Y cable we want to run loopback on.

        Args:
            port:
                 an Integer, the actual physical port connected to a Y cable
            target:
                One of the following predefined constants, the target on which to disable the loopback:
                    EYE_PRBS_TARGET_LOCAL -> local side,
                    EYE_PRBS_TARGET_TOR_A -> TOR A
                    EYE_PRBS_TARGET_TOR_B -> TOR B
                    EYE_PRBS_TARGET_NIC -> NIC

        Returns:
            a boolean, True if the disable is successful
                     , False if the disable failed
        """

        raise NotImplementedError
