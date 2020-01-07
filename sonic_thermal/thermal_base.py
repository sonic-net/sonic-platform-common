#!/usr/bin/env python
#
# thermal_base.py
#
# Base class for implementing platform-specific
#  Thermal functionality for SONiC

try:
    import abc
except ImportError as e:
    raise ImportError (str(e) + " - required module not found")

class ThermalBase(object):
    __metaclass__ = abc.ABCMeta

    def get_num_thermals(self):
        """
        Retrieves the number of thermal sensors supported on the device

        :return: An integer, the number of thermal sensors supported on the device
        """
        return 0

    def get_name(self, index):
        """
        Retrieves the human-readable name of a thermal sensor by 1-based index

        Returns:
        :param index: An integer, 1-based index of the thermal sensor of which to query status
        :return: String,
            A string representing the name of the thermal sensor. 
        """
        return ""

    def get_temperature(self, index):
        """
        Retrieves current temperature reading from thermal sensor by 1-based index

        :param index: An integer, 1-based index of the thermal sensor of which to query status
        :return: Float,
            A float number of current temperature in Celsius up to nearest thousandth
            of one degree Celsius, e.g. 30.125 
        """
        return 0.0

    def get_low_threshold(self, index):
        """
        Retrieves the low threshold temperature of thermal sensor by 1-based index
        Actions should be taken if the temperature becomes lower than the low threshold.

        :param index: An integer, 1-based index of the thermal sensor of which to query status
        :return: A float number, the low threshold temperature of thermal in Celsius
                 up to nearest thousandth of one degree Celsius, e.g. 30.125
        """
        return 0.0

    def get_low_critical_threshold(self, index):
        """
        Retrieves the low critical threshold temperature of thermal by 1-based index
        Actions should be taken immediately if the temperature becomes lower than the low critical
        threshold otherwise the device will be damaged.

        :param index: An integer, 1-based index of the thermal sensor of which to query status
        :return: A float number, the low critical threshold temperature of thermal in Celsius
                 up to nearest thousandth of one degree Celsius, e.g. 30.125
        """
        return 0.0

    def get_high_threshold(self, index):
        """
        Retrieves the high threshold temperature of thermal by 1-based index
        Actions should be taken if the temperature becomes higher than the threshold.

        :param index: An integer, 1-based index of the thermal sensor of which to query status
        :return: A float number, the high threshold temperature of thermal in Celsius
                 up to nearest thousandth of one degree Celsius, e.g. 30.125
        """
        return 0.0

    def get_high_critical_threshold(self, index):
        """
        Retrieves the high critical threshold temperature of thermal by 1-based index
        Actions should be taken immediately if the temperature becomes higher than the high critical
        threshold otherwise the device will be damaged.

        :param index: An integer, 1-based index of the thermal sensor of which to query status
        :return: A float number, the high critical threshold temperature of thermal in Celsius
                 up to nearest thousandth of one degree Celsius, e.g. 30.125
        """
        return 0.0
