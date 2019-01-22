#
# psu_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a power supply unit (PSU) in SONiC
#

from . import device_base


class PsuBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a power supply unit
    """

    # Possible fan status LED colors
    STATUS_LED_COLOR_GREEN = "green"
    STATUS_LED_COLOR_RED = "red"
    STATUS_LED_COLOR_OFF = "off"

    def get_voltage(self):
        """
        Retrieves current PSU voltage output

        Returns:
            A float number, the output voltage in volts, 
            e.g. 12.1 
        """
        raise NotImplementedError

    def get_ampere(self):
        """
        Retrieves present electric current supplied by PSU

        Returns:
            A float number, the electric current in amperes, e.g 15.4
        """
        raise NotImplementedError

    def get_watt(self):
        """
        Retrieves current energy supplied by PSU

        Returns:
            A float number, the power in watts, e.g. 302.6
        """
        raise NotImplementedError

    def get_powergood_status(self):
        """
        Retrieves the powergood status of PSU

        Returns:
            A boolean, True if PSU has stablized its output voltages and passed all
            its internal self-tests, False if not.
        """
        raise NotImplementedError

    def set_status_led(self, color):
        """
        Sets the state of the PSU status LED

        Args:
            color: A string representing the color with which to set the
                   PSU status LED

        Returns:
            bool: True if status LED state is set successfully, False if not
        """
        raise NotImplementedError

    def get_status_led(self, color):
        """
        Gets the state of the PSU status LED

        Args:
            color: A string representing the color of PSU status LED

        Returns:
            bool: True if get LED state returned successfully, False if not
        """
        raise NotImplementedError
