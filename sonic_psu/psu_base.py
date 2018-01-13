#!/usr/bin/env python
#
# psu_base.py
#
# Abstract base class for implementing platform-specific
#  PSU control functionality for SONiC
#

try:
    import abc
except ImportError as e:
    raise ImportError (str(e) + " - required module not found")

class PsuBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_num_psus(self):
        """
        Retrieves the number of PSUs supported on the device

        :return: An integer, the number of PSUs supported on the device
        """
        return 0

    @abc.abstractmethod
    def get_psu_status(self, index):
        """
        Retrieves the operational status of power supply unit (PSU) defined
                by index 1-based <index>

        :param index: An integer, 1-based index of the PSU of which to query status
        :return: Boolean,
            - True if PSU is operating properly: PSU is inserted and powered in the device
            - False if PSU is faulty: PSU is inserted in the device but not powered
        """
        return False

    @abc.abstractmethod
    def get_psu_presence(self, index):
        """
        Retrieves the presence status of power supply unit (PSU) defined
                by 1-based index <index>

        :param index: An integer, 1-based index of the PSU of which to query status
        :return: Boolean, True if PSU is plugged, False if not
        """
        return False

