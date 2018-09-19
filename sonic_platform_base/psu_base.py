#
# psu_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a power supply unit (PSU) in SONiC
#

try:
    import abc
    from . import device_base
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


class PsuBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a power supply unit
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
    def get_fan_direction(self):
        """
        Retrieves the direction of PSU fan

        Returns:
            A string, either 'intake' or 'exhaust', depending on fan direction
        """
        return None

    @abc.abstractmethod
    def get_fan_speed(self):
        """
        Retrieves the speed of PSU fan as a percentage of full speed

        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
            to 100 (full speed)
        """
        return 0

    @abc.abstractmethod
    def get_fan_target_speed(self):
        """
        Retrieves the target (expected) speed of the PSU fan

        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
            to 100 (full speed)
        """
        return 0

    @abc.abstractmethod
    def get_fan_speed_tolerance(self):
        """
        Retrieves the speed tolerance of the PSU fan

        Returns:
            An integer, the percentage of variance from target speed which is
            considered tolerable
        """
        return 0

    @abc.abstractmethod
    def set_fan_speed(self, speed):
        """
        Sets the fan speed

        Args:
            speed: An integer, the percentage of full fan speed to set fan to,
                   in the range 0 (off) to 100 (full speed)

        Returns:
            A boolean, True if fan speed is set successfully, False if not
        """
        return False

    @abc.abstractmethod
    def set_status_led(self, color):
        """
        Sets the state of the PSU status LED

        Args:
            color: A string representing the color with which to set the
                   PSU status LED

        Returns:
            bool: True if status LED state is set successfully, False if not
        """
        return False
