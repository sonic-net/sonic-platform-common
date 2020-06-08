#!/usr/bin/env python
#
# fan_base.py
#
# Base class for implementing platform-specific
#  FAN control functionality for SONiC
#

try:
    import abc
except ImportError as e:
    raise ImportError (str(e) + " - required module not found")

class FanBase(object):
    __metaclass__ = abc.ABCMeta

    # Possible fan directions (relative to port-side of device)
    FAN_DIRECTION_INTAKE = "intake"
    FAN_DIRECTION_EXHAUST = "exhaust"
    FAN_DIRECTION_NOT_APPLICABLE = "N/A"

    def get_num_fans(self):
        """
        Retrieves the number of FANs supported on the device

        :return: An integer, the number of FANs supported on the device
        """
        return 0

    def get_status(self, index):
        """
        Retrieves the operational status of FAN defined
                by index 1-based <index>

        :param index: An integer, 1-based index of the PSU of which to query status
        :return: Boolean,
            - True if FAN is running with some speed 
            - False if FAN has stopped running
        """
        return False

    def get_presence(self, index):
        """
        Retrieves the presence status of a FAN defined
                by 1-based index <index>

        :param index: An integer, 1-based index of the FAN of which to query status
        :return: Boolean, True if FAN is plugged, False if not
        """
        return False
    
    def get_direction(self, index):
        """
        Retrieves the airflow direction of a FAN defined
                by 1-based index <index>

        :param index: An integer, 1-based index of the FAN of which to query status
        :return: string, denoting FAN airflow direction
        """
        return ""
    
    def get_speed(self, index):
        """
        Retrieves the speed of a Front FAN in the tray in revolutions per minute defined
                by 1-based index <index>

        :param index: An integer, 1-based index of the FAN of which to query speed
        :return: integer, denoting front FAN speed
        """
        return 0

    def get_speed_rear(self, index):
        """
        Retrieves the speed of a rear FAN in the tray (applicable only for 2-fan tray) 
                in revolutions per minute defined by 1-based index <index>

        :param index: An integer, 1-based index of the FAN of which to query speed
        :return: integer, denoting rear FAN speed
        """
        return 0
    
    def set_speed(self, val):
        """
        Sets the speed of all the FANs to a value denoted by the duty-cycle percentage val

        :param val: An integer, <0-100> denoting FAN duty cycle percentage 
        :return: Boolean, True if operation is successful, False if not
        """
        return False
