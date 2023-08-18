"""
    sensor_base.py

    Abstract base class for implementing a platform-specific class with which
    to interact with a sensor module in SONiC
"""

from . import device_base

class SensorBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a sensor module
    """

    @classmethod
    def get_type(cls):
        """
        Specifies the type of the sensor such as current/voltage etc.

        Returns:
            Sensor type
        """
        raise NotImplementedError

    def get_value(self):
        """
        Retrieves measurement reported by sensor

        Returns:
            Sensor measurement
        """
        raise NotImplementedError

    @classmethod
    def get_unit(cls):
        """
        Retrieves unit of measurement reported by sensor

        Returns:
            Sensor measurement unit
        """
        raise NotImplementedError

    def get_high_threshold(self):
        """
        Retrieves the high threshold of sensor

        Returns:
            High threshold 
        """
        raise NotImplementedError

    def get_low_threshold(self):
        """
        Retrieves the low threshold 

        Returns:
            Low threshold 
        """
        raise NotImplementedError

    def set_high_threshold(self, value):
        """
        Sets the high threshold value of sensor

        Args:
            value: High threshold value to set

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def set_low_threshold(self, value):
        """
        Sets the low threshold value of sensor

        Args:
            value: Value 

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def get_high_critical_threshold(self):
        """
        Retrieves the high critical threshold value of sensor

        Returns:
            The high critical threshold value of sensor 
        """
        raise NotImplementedError

    def get_low_critical_threshold(self):
        """
        Retrieves the low critical threshold value of sensor

        Returns:
            The low critical threshold value of sensor 
        """
        raise NotImplementedError

    def set_high_critical_threshold(self, value):
        """
        Sets the critical high threshold value of sensor

        Args:
            value: Critical high threshold Value 

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def set_low_critical_threshold(self, value):
        """
        Sets the critical low threshold value of sensor

        Args:
            value: Critial low threshold Value 

        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        raise NotImplementedError

    def get_minimum_recorded(self):
        """
        Retrieves the minimum recorded value of sensor

        Returns:
            The minimum recorded value of sensor 
        """
        raise NotImplementedError

    def get_maximum_recorded(self):
        """
        Retrieves the maximum recorded value of sensor

        Returns:
            The maximum recorded value of sensor 
        """
        raise NotImplementedError



class VoltageSensorBase(SensorBase):
    """
    Abstract base class for interfacing with a voltage sensor module
    """

    @classmethod
    def get_type(cls):
        return "SENSOR_TYPE_VOLTAGE"

    @classmethod
    def get_unit(cls):
        return "mV"


class CurrentSensorBase(SensorBase):
    """
    Abstract base class for interfacing with a current sensor module
    """

    @classmethod
    def get_type(cls):
        return "SENSOR_TYPE_CURRENT"

    @classmethod
    def get_unit(cls):
        return "mA"
