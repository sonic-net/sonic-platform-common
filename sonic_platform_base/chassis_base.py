#
# chassis_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a chassis device in SONiC.
#

try:
    import abc
    import sys
    from . import device_base
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


class ChassisBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a platform chassis
    """

    __metaclass__ = abc.ABCMeta

    # Possible reboot causes
    REBOOT_CAUSE_POWER_LOSS = "power_loss" 
    REBOOT_CAUSE_THERMAL_OVERLOAD = "thermal_overload"
    REBOOT_CAUSE_SOFTWARE = "software"

    # List of all fans available on the chassis
    fan_list = []

    @abc.abstractmethod
    def get_base_mac(self):
        """
        Retrieves the base MAC address for the chassis

        Returns:
            A string containing the MAC address in the format
            'XX:XX:XX:XX:XX:XX'
        """
        return None 

    @abc.abstractmethod
    def get_reboot_cause(self):
        """
        Retrieves the cause of the previous reboot

        Returns:
            An integer, the number of power supply units available on this
            chassis
        """
        return REBOOT_CAUSE_SOFTWARE

    def get_num_fans(self):
        """
        Retrieves the number of fan modules available on this chassis

        Returns:
            An integer, the number of fan modules available on this chassis
        """
        return len(self.fan_list)

    def get_all_fans(self):
        """
        Retrieves all fan modules available on this chassis

        Returns:
            A list of objects derived from FanBase representing all fan
            modules available on this chassis
        """
        return self.fan_list

    def get_fan(self, index):
        """
        Retrieves fan module represented by (1-based) index <index>

        Args:
            index: An integer, the index (1-based) of the fan module to
            retrieve

        Returns:
            An object dervied from FanBase representing the specified fan
            module
        """
        fan = None

        try:
            fan = self.fan_list[index]
        except IndexError:
            sys.stderr.write("Fan index {} out of range (0-{})\n".format(
                             index, len(self.fan_list)-1))

        return fan
