"""
    isensor_base.py

    Abstract base class for implementing a platform-specific class with which
    to interact with a isensor module in SONiC
"""

from . import device_base


class IsensorBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a isensor module
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "isensor"

    def get_current(self):
        """
        Retrieves current current reading from isensor

        Returns:
            Current current in Milliamps.
        """
        raise NotImplementedError


    def get_high_threshold(self):
        """
        Retrieves the high threshold current of isensor

        Returns:
            High current threshold in Milliamps.
        """
        raise NotImplementedError

    def get_low_threshold(self):
        """
        Retrieves the low threshold current of isensor

        Returns:
            Low current threshold in Milliamps
        """
        raise NotImplementedError

    def set_high_threshold(self, current):
        """
        Sets the high threshold current of isensor

        Args :
            current: Value in Milliamps

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def set_low_threshold(self, current):
        """
        Sets the low threshold current of isensor

        Args :
            current: Value in Milliamps

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def get_high_critical_threshold(self):
        """
        Retrieves the high critical threshold current of isensor

        Returns:
            The high critical threshold current of sensor in Milliamps
        """
        raise NotImplementedError

    def get_low_critical_threshold(self):
        """
        Retrieves the low critical threshold current of isensor

        Returns:
            The low critical threshold current of isensor in Milliamps
        """
        raise NotImplementedError

    def set_high_critical_threshold(self, current):
        """
        Sets the critical high threshold current of isensor

        Args :
            current: Value in Milliamps

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def set_low_critical_threshold(self, current):
        """
        Sets the critical low threshold current of isensor

        Args :
            current: Value in Milliamps

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def get_minimum_recorded(self):
        """
        Retrieves the minimum recorded current of isensor

        Returns:
            The minimum recorded current of isensor in Milliamps
        """
        raise NotImplementedError

    def get_maximum_recorded(self):
        """
        Retrieves the maximum recorded current of isensor

        Returns:
            The maximum recorded current of isensor in Milliamps
        """
        raise NotImplementedError
