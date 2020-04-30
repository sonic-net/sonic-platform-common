#
# fan_drawer_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a fan drawer module in SONiC
#

from . import device_base


class FanDrawerBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a fan drawer
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "fan_drawer"

    def __init__(self):
        self._fan_list = []

    def get_num_fans(self):
        """
        Retrieves the number of fans available on this fan drawer

        Returns:
            An integer, the number of fan modules available on this fan drawer
        """
        return len(self._fan_list)

    def get_all_fans(self):
        """
        Retrieves all fan modules available on this fan drawer

        Returns:
            A list of objects derived from FanBase representing all fan
            modules available on this fan drawer
        """
        return self._fan_list

    def set_status_led(self, color):
        """
        Sets the state of the fan drawer status LED

        Args:
            color: A string representing the color with which to set the
                   fan drawer status LED

        Returns:
            bool: True if status LED state is set successfully, False if not
        """
        raise NotImplementedError

    def get_status_led(self, color):
        """
        Gets the state of the fan drawer LED

        Returns:
            A string, one of the predefined STATUS_LED_COLOR_* strings above
        """
        raise NotImplementedError
