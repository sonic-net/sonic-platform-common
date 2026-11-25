"""
    led_base.py

    Abstract base class for implementing a platform-specific class with which
    to interact with a LED in SONiC
"""

try:
    from enum import Enum
except ImportError as e:
    raise ImportError(str(e) + " - required module not found") from e

class LedColor(Enum):
    """
    Enumeration of LED colors

    These are the standard colors used by LEDs.
    """
    OFF = "off"
    GREEN = "green"
    AMBER = "amber"
    YELLOW = "amber"  # YELLOW is an alias for AMBER
    RED = "red"
    BLUE = "blue"

class LedBase:
    """
    Abstract base class for interfacing with an LED

    This class represents a single physical LED that can be controlled.
    """

    def __init__(self):
        pass

    def get_name(self):
        """
        Retrieves the name of the LED

        Returns:
            A string representing the name of the LED. This is a platform-specific
            identifier that can be used for debugging purposes.

        Example:
            "port1_led1", "osfp1_led2"
        """
        raise NotImplementedError

    def get_color_capabilities(self):
        """
        Retrieves the color capabilities of the LED

        Returns:
            A list of LedColor enum values representing the colors this LED
            can display. Platforms should include OFF in the capability list
            for clarity and completeness.

        Example:
            [LedColor.OFF, LedColor.GREEN, LedColor.AMBER]
            [LedColor.OFF, LedColor.GREEN, LedColor.RED, LedColor.BLUE]
        """
        raise NotImplementedError

    def set_color(self, color):
        """
        Sets the color of the LED

        Args:
            color: A LedColor enum value representing the desired color.
                   The color must be one of the values returned by
                   get_color_capabilities()

        Returns:
            A boolean, True if the color was set successfully, False if not

        Raises:
            ValueError: if the color is not supported by this LED

        Example:
            led.set_color(LedColor.GREEN)  # Set LED to green
            led.set_color(LedColor.AMBER)  # Set LED to amber
            led.set_color(LedColor.OFF)    # Turn LED off
        """
        raise NotImplementedError

    def get_color(self):
        """
        Retrieves the current color of the LED (optional method)

        Returns:
            A LedColor enum value representing the current color of the LED
        """
        raise NotImplementedError
