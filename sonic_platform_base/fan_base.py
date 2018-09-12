#
# fan_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a fan module in SONiC
#

try:
    import abc
    from . import device_base
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


class FanBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a fan module
    """
    __metaclass__ = abc.ABCMeta
    
    # Possible fan directions
    FAN_DIRECTION_INTAKE = "intake"
    FAN_DIRECTION_EXHAUST = "exhaust"

    # Possible fan status LED colors
    STATUS_LED_COLOR_GREEN = "green"
    STATUS_LED_COLOR_RED = "red"
    STATUS_LED_COLOR_OFF = "off"

    @abc.abstractmethod
    def get_direction(self):
        """
        Retrieves the direction of fan

        Returns:
            A string, either FAN_DIRECTION_INTAKE or FAN_DIRECTION_EXHAUST
            depending on fan direction
        """
        return None

    @abc.abstractmethod
    def get_speed(self):
        """
        Retrieves the speed of fan as a percentage of full speed

        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
                 to 100 (full speed)
        """
        return 0

    @abc.abstractmethod
    def get_expected_speed(self):
        """
        Retrieves the expected speed of the fan

        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
                 to 100 (full speed)
        """
        return 0

    @abc.abstractmethod
    def get_speed_tolerance(self):
        """
        Retrieves the speed tolerance of the fan

        Returns:
            An integer, the percentage of variance from expected speed which is
                 considered tolerable
        """
        return 0

    @abc.abstractmethod
    def set_speed(self, speed):
        """
        Sets the fan speed

        Args:
            speed: An integer, the percentage of full fan speed to set fan to,
                   in the range 0 (off) to 100 (full speed)

        Returns:
            A boolean, True if speed is set successfully, False if not
        """
        return False

    @abc.abstractmethod
    def set_status_led(self, color):
        """
        Sets the state of the fan module status LED

        Args:
            color: A string representing the color with which to set the
                   fan module status LED

        Returns:
            bool: True if status LED state is set successfully, False if not
        """
        return False
