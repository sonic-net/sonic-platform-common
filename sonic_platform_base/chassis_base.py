#
# chassis_base.py
#
# Base class for implementing a platform-specific class with which
# to interact with a chassis device in SONiC.
#

import sys
from . import device_base


class ChassisBase(device_base.DeviceBase):
    """
    Base class for interfacing with a platform chassis
    """

    # Possible reboot causes
    REBOOT_CAUSE_POWER_LOSS = "power_loss"
    REBOOT_CAUSE_THERMAL_OVERLOAD_CPU = "thermal_overload_cpu"
    REBOOT_CAUSE_THERMAL_OVERLOAD_ASIC = "thermal_overload_asic"
    REBOOT_CAUSE_THERMAL_OVERLOAD_OTHER = "thermal_overload_other"
    REBOOT_CAUSE_INSUFFICIENT_FAN = "insufficient_fan"
    REBOOT_CAUSE_WATCHDOG = "watchdog"
    REBOOT_CAUSE_SOFTWARE = "software"

    # List of ModuleBase-derived objects representing all modules
    # available on the chassis (for use with modular chassis)
    _module_list = []

    # List of FanBase-derived objects representing all fans
    # available on the chassis
    _fan_list = []

    # List of PsuBase-derived objects representing all power supply units
    # available on the chassis
    _psu_list = []

    # Object derived from WatchdogBase for interacting with hardware watchdog
    _watchdog = None

    def get_base_mac(self):
        """
        Retrieves the base MAC address for the chassis

        Returns:
            A string containing the MAC address in the format
            'XX:XX:XX:XX:XX:XX'
        """
        raise NotImplementedError

    def get_reboot_cause(self):
        """
        Retrieves the cause of the previous reboot

        Returns:
            A string containing the cause of the previous reboot. This string
            must be one of the predefined strings in this class.
        """
        raise NotImplementedError

    def get_component_versions(self):
        """
        Retrieves platform-specific hardware/firmware versions for chassis
        componenets such as BIOS, CPLD, FPGA, etc.

        Returns:
            A string containing platform-specific component versions
        """
        raise NotImplementedError

    ##############################################
    # Module methods
    ##############################################

    def get_num_modules(self):
        """
        Retrieves the number of modules available on this chassis

        Returns:
            An integer, the number of modules available on this chassis
        """
        return len(self._module_list)

    def get_all_modules(self):
        """
        Retrieves all modules available on this chassis

        Returns:
            A list of objects derived from ModuleBase representing all
            modules available on this chassis
        """
        return self._module_list

    def get_module(self, index):
        """
        Retrieves module represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the module to
            retrieve

        Returns:
            An object dervied from ModuleBase representing the specified
            module
        """
        module = None

        try:
            module = self._module_list[index]
        except IndexError:
            sys.stderr.write("Module index {} out of range (0-{})\n".format(
                             index, len(self._module_list)-1))

        return module

    ##############################################
    # Fan methods
    ##############################################

    def get_num_fans(self):
        """
        Retrieves the number of fans available on this chassis

        Returns:
            An integer, the number of fan modules available on this chassis
        """
        return len(self._fan_list)

    def get_all_fans(self):
        """
        Retrieves all fan modules available on this chassis

        Returns:
            A list of objects derived from FanBase representing all fan
            modules available on this chassis
        """
        return self._fan_list

    def get_fan(self, index):
        """
        Retrieves fan module represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the fan module to
            retrieve

        Returns:
            An object dervied from FanBase representing the specified fan
            module
        """
        fan = None

        try:
            fan = self._fan_list[index]
        except IndexError:
            sys.stderr.write("Fan index {} out of range (0-{})\n".format(
                             index, len(self._fan_list)-1))

        return fan

    ##############################################
    # PSU methods
    ##############################################

    def get_num_psus(self):
        """
        Retrieves the number of power supply units available on this chassis

        Returns:
            An integer, the number of power supply units available on this
            chassis
        """
        return len(self._psu_list)

    def get_all_psus(self):
        """
        Retrieves all power supply units available on this chassis

        Returns:
            A list of objects derived from PsuBase representing all power
            supply units available on this chassis
        """
        return self._psu_list

    def get_psu(self, index):
        """
        Retrieves power supply unit represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the power supply unit to
            retrieve

        Returns:
            An object dervied from PsuBase representing the specified power
            supply unit
        """
        psu = None

        try:
            psu = self._psu_list[index]
        except IndexError:
            sys.stderr.write("PSU index {} out of range (0-{})\n".format(
                             index, len(self._psu_list)-1))

        return psu

    ##############################################
    # Other methods
    ##############################################

    def get_watchdog(self):
        """
        Retreives hardware watchdog device on this chassis

        Returns:
            An object derived from WatchdogBase representing the hardware
            watchdog device
        """
        return _watchdog
