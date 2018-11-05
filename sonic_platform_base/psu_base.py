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

    # Possible fan directions
    FAN_DIRECTION_INTAKE = "intake"
    FAN_DIRECTION_EXHAUST = "exhaust"

    # Possible fan status LED colors
    STATUS_LED_COLOR_GREEN = "green"
    STATUS_LED_COLOR_RED = "red"
    STATUS_LED_COLOR_OFF = "off"

    # FanBase-derived object representing fan module available on the PSU
    _fan = None

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
