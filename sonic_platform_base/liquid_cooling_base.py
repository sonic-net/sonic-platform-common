"""
    liquid_cooling_base.py

    Abstract base class for implementing a platform-specific class with which
    to interact with a liquid cooling module in SONiC
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List

from . import device_base
from .sensor_base import SensorBase
import sys


class LeakSeverity(Enum):
    MINOR    = "MINOR"
    CRITICAL = "CRITICAL"


class LeakageSensorBase(SensorBase):
    # Keep string aliases for backwards compatibility
    LEAK_SEVERITY_CRITICAL = LeakSeverity.CRITICAL
    LEAK_SEVERITY_MINOR    = LeakSeverity.MINOR

    def __init__(self,
                 name: str, *,
                 type: str|None = None,
                 location: str|None = None,
                 severity: LeakSeverity = LeakSeverity.CRITICAL):
        self.name: str = name
        self.leaking: bool = False
        self.leak_sensor_ok: bool = True
        self.leak_type: str|None = type
        self.leak_location = location
        self.leak_severity = severity

    def get_name(self) -> str:
        """
        Retrieves the name of the leakage sensor

        Returns:
            string: the name of the leakage sensor
        """
        return self.name

    def is_leak(self) -> bool:
        """
        Retrieves the leak status of the sensor.
        The platform should apply debounce logic before reporting/clearing leak.

        Returns:
            bool: True if leak is detected, False if not
        """
        return self.leaking

    def is_leak_sensor_ok(self) -> bool:
        """
        Retrieves the state of leak sensor whether it is ok or faulty

        Returns:
            bool: True if leak sensor is ok, False if it is faulty
        """
        return self.leak_sensor_ok

    def get_leak_sensor_type(self) -> str|None:
        """
        Retrieves the leak sensor type

        Returns:
            string: the type of the leakage sensor
        """
        return self.leak_type

    def get_leak_sensor_location(self) -> str|None:
        """
        Retrieves the location of leak sensor

        Returns:
            string: the location of the leakage sensor
        """
        return self.leak_location

    def get_leak_severity(self) -> LeakSeverity:
        """
        Retrieves the severity of leak

        Returns:
            LeakSeverity: LeakSeverity.CRITICAL or LeakSeverity.MINOR, or None if no leak
        """
        return self.leak_severity

    def get_leak_profile(self):
        """
        Returns the leak sensor profile associated with this sensor.
        """
        raise NotImplementedError

class LeakSensorProfileBase(ABC):
    """
    Platform-specific leak sensor profile, which defines APIs pre leaksensor type
    """

    @abstractmethod
    def get_type(self) -> str:
        """
        Retrieves the type of sensor that this profile is describing.

        Returns:
            str: the type being described
        """
        pass

    @abstractmethod
    def get_leak_max_minor_duration_sec(self) -> int:
        """
        Maximum time before a minor leak is marked critical.

        Returns:
            int: time in seconds
        """
        pass


class LiquidCoolingBase(device_base.DeviceBase):
    """
    Base class for implementing liquid cooling system
    """

    def __init__(self,
                 leakage_sensors_num: int = 0,
                 leakage_sensors_list: List[LeakageSensorBase] = [],
                 *,
                 profiles: List[LeakSensorProfileBase] = []):
        self.leakage_sensors: List[LeakageSensorBase] = leakage_sensors_list
        self.profiles: Dict[str, LeakSensorProfileBase] = {
            p.get_type(): p for p in profiles
        }

    def get_num_leak_sensors(self) -> int:
        """
        Retrieves the number of leakage sensors
 
        Returns:
            int: The number of leakage sensors
        """
        return len(self.leakage_sensors)
    
    def get_leak_sensor(self, index: int) -> LeakageSensorBase|None:
        """
        Retrieves the leakage sensor by index
        """
        sensor = self.leakage_sensors[index] \
            if index < len(self.leakage_sensors) else None

        if sensor is None:
            sys.stderr.write("Leakage sensor index {} out of range (0-{})\n".format(
                             index, len(self.leakage_sensors)-1))

        return sensor

    def get_all_leak_sensors(self) -> List[LeakageSensorBase]:
        """
        Retrieves the list of leakage sensors
 
        Returns:
            List[LeakageSensorBase]: A list of leakage sensor names
        """
        return self.leakage_sensors

    def get_leak_sensor_status(self) -> List[LeakageSensorBase]:
        """
        Retrieves the leak status of the sensors

        Returns:
            List[str]: A list of leakage sensors that are leaking, empty list if no leakage
        """
        leaking_sensors = []
        for sensor in self.leakage_sensors:
            if sensor.is_leak():
                leaking_sensors.append(sensor)
        return leaking_sensors

    def get_all_profiles(self) -> List[LeakSensorProfileBase]:
        """
        Retrieves the list of leak sensor profiles.

        Returns:
            List[LeakSensorProfile]: A list of all leak sensor profiles
        """
        return list(self.profiles.values())

    def get_profile(self, type: str) -> LeakSensorProfileBase|None:
        """
        Retrives the profile with the given name.
        """
        profile = getattr(self.profiles, type, None)

        if profile is None:
            sys.stderr.write(f"Leakage sensor profile {type} doesn't exist")

        return profile
