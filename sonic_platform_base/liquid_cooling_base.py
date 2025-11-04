"""
    liquid_cooling_base.py

    Abstract base class for implementing a platform-specific class with which
    to interact with a liquid cooling module in SONiC
"""

from . import device_base
from .sensor_base import SensorBase
import sys

class LeakageSensorBase(SensorBase):
    def __init__(self, name):
        self.name = name
        self.leaking = False

    def get_name(self):
        """
        Retrieves the name of the leakage sensor

        Returns:
            tring: the name of the leakage sensor
        """        
        return self.name

    def is_leak(self):
        """
        Retrieves the leak status of the sensor

        Returns:
            bool: True if leak is detected, False if not
        """        
        return self.leaking

class LiquidCoolingBase(device_base.DeviceBase):
    """
    Base class for implementing liquid cooling system
    """

    def __init__(self, leakage_sensors_num = 0, leakage_sensors_list = None):
        self.leakage_sensors_num = leakage_sensors_num
        self.leakage_sensors = leakage_sensors_list if leakage_sensors_list else []

    def get_num_leak_sensors(self):
        """
        Retrieves the number of leakage sensors
 
        Returns:
            int: The number of leakage sensors
        """
        return self.leakage_sensors_num
    
    def get_leak_sensor(self, index):
        """
        Retrieves the leakage sensor by index
        """
        sensor = None

        try:
            sensor = self.leakage_sensors[index]
        except IndexError:
            sys.stderr.write("Leakage sensor index {} out of range (0-{})\n".format(
                             index, len(self.leakage_sensors)-1))

        return sensor
 
    def get_all_leak_sensors(self):
        """
        Retrieves the list of leakage sensors
 
        Returns:
            list: A list of leakage sensor names
        """
        return self.leakage_sensors

    def get_leak_sensor_status(self):
        """
        Retrieves the leak status of the sensors

        Returns:
            list: A list of leakage sensor names that are leaking, empty list if no leakage
        """
        leaking_sensors = []
        for sensor in self.leakage_sensors:
            if sensor.is_leak():
                leaking_sensors.append(sensor)
        return leaking_sensors

