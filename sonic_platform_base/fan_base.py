"""
    fan_base.py

    Abstract base class for implementing a platform-specific class with which
    to interact with a fan module in SONiC
"""

from . import device_base


class FanBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a fan module
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "fan"

    # Possible fan directions (relative to port-side of device)
    FAN_DIRECTION_INTAKE = "intake"
    FAN_DIRECTION_EXHAUST = "exhaust"
    FAN_DIRECTION_NOT_APPLICABLE = "N/A"

    # Possible fan status LED colors
    STATUS_LED_COLOR_GREEN = "green"
    STATUS_LED_COLOR_AMBER = "amber"
    STATUS_LED_COLOR_RED = "red"
    STATUS_LED_COLOR_OFF = "off"

    def get_direction(self):
        """
        Retrieves the direction of fan

        Returns:
            A string, either FAN_DIRECTION_INTAKE or FAN_DIRECTION_EXHAUST
            depending on fan direction
        """
        raise NotImplementedError

    def get_speed(self):
        """
        Retrieves the speed of fan as a percentage of full speed

        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
                 to 100 (full speed)
        """
        raise NotImplementedError

    def get_target_speed(self):
        """
        Retrieves the target (expected) speed of the fan

        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
                 to 100 (full speed)
        """
        raise NotImplementedError

    def get_speed_tolerance(self):
        """
        Retrieves the speed tolerance of the fan

        Returns:
            An integer, the percentage of variance from target speed which is
                 considered tolerable
        """
        raise NotImplementedError

    def is_under_speed(self):
        """
        Calculates if the fan speed is under the tolerated low speed threshold

        Returns:
            A boolean, True if fan speed is under the low threshold, False if not
        """
        speed = self.get_speed()
        target_speed = self.get_target_speed()
        tolerance = self.get_speed_tolerance()

        for param, value in (('speed', speed), ('target speed', target_speed), ('speed tolerance', tolerance)):
            if not isinstance(value, int):
                raise TypeError('Fan {0} is not an integer value: {0}={1}'.format(param, value))
            if value < 0 or value > 100:
                raise ValueError('Fan {0} is not a valid percentage value: {0}={1}'.format(param, value))

        return speed < target_speed * (1 - float(tolerance) / 100)

    def is_over_speed(self):
        """
        Calculates if the fan speed is over the tolerated high speed threshold

        Returns:
            A boolean, True if fan speed is over the high threshold, False if not
        """
        speed = self.get_speed()
        target_speed = self.get_target_speed()
        tolerance = self.get_speed_tolerance()

        for param, value in (('speed', speed), ('target speed', target_speed), ('speed tolerance', tolerance)):
            if not isinstance(value, int):
                raise TypeError('Fan {0} is not an integer value: {0}={1}'.format(param, value))
            if value < 0 or value > 100:
                raise ValueError('Fan {0} is not a valid percentage value: {0}={1}'.format(param, value))

        return speed > target_speed * (1 + float(tolerance) / 100)

    def set_speed(self, speed):
        """
        Sets the fan speed

        Args:
            speed: An integer, the percentage of full fan speed to set fan to,
                   in the range 0 (off) to 100 (full speed)

        Returns:
            A boolean, True if speed is set successfully, False if not
        """
        raise NotImplementedError

    def set_status_led(self, color):
        """
        Sets the state of the fan module status LED

        Args:
            color: A string representing the color with which to set the
                   fan module status LED

        Returns:
            bool: True if status LED state is set successfully, False if not
        """
        raise NotImplementedError

    def get_status_led(self):
        """
        Gets the state of the fan status LED

        Returns:
            A string, one of the predefined STATUS_LED_COLOR_* strings above
        """
        raise NotImplementedError
