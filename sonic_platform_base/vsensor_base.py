"""
    vsensor_base.py

    Abstract base class for implementing a platform-specific class with which
    to interact with a voltage sensor module in SONiC
"""

from . import device_base


class VsensorBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a voltage sensor module
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "vsensor"

    def get_voltage(self):
        """
        Retrieves current voltage reading from voltage sensor

        Returns:
            Current voltage in Millivolts.
        """
        raise NotImplementedError


    def get_high_threshold(self):
        """
        Retrieves the high threshold voltage of voltage sensor

        Returns:
            High voltage threshold in Millivolts.
        """
        raise NotImplementedError

    def get_low_threshold(self):
        """
        Retrieves the low threshold voltage of voltage sensor

        Returns:
            Low voltage threshold in Millivolts
        """
        raise NotImplementedError

    def set_high_threshold(self, voltage):
        """
        Sets the high threshold voltage of voltage sensor

        Args :
            voltage: Value in Millivolts

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def set_low_threshold(self, voltage):
        """
        Sets the low threshold voltage of voltage sensor

        Args :
            voltage: Value in Millivolts

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def get_high_critical_threshold(self):
        """
        Retrieves the high critical threshold voltage of voltage sensor

        Returns:
            The high critical threshold voltage of sensor in Millivolts
        """
        raise NotImplementedError

    def get_low_critical_threshold(self):
        """
        Retrieves the low critical threshold voltage of voltage sensor

        Returns:
            The low critical threshold voltage of voltage sensor in Millivolts
        """
        raise NotImplementedError

    def set_high_critical_threshold(self, voltage):
        """
        Sets the critical high threshold voltage of voltage sensor

        Args :
            voltage: Value in Millivolts

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def set_low_critical_threshold(self, voltage):
        """
        Sets the critical low threshold voltage of voltage sensor

        Args :
            voltage: Value in Millivolts

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def get_minimum_recorded(self):
        """
        Retrieves the minimum recorded voltage of voltage sensor

        Returns:
            The minimum recorded voltage of voltage sensor in Millivolts
        """
        raise NotImplementedError

    def get_maximum_recorded(self):
        """
        Retrieves the maximum recorded voltage of voltage sensor

        Returns:
            The maximum recorded voltage of voltage sensor in Millivolts
        """
        raise NotImplementedError
