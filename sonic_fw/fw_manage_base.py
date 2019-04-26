#!/usr/bin/env python
#
# fw_manage_base.py
#
# Abstract base class for implementing platform-specific
#  Firmware management functionality for SONiC
#

try:
    import abc
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


class FwBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def get_module_list(self):
        """
        Retrieves the list of module that available on the device

        :return: A list : the list of module that available on the device
        """
        return []

    @abc.abstractmethod
    def get_fw_version(self, module_name):
        """
        Retrieves the firmware version of module

        :param module_name: A string, module name
        :return: A Dict, firmware version object
            - Example of return object of module that doesn't have sub modules
            {
                "module_name": "BIOS",
                "fw_version": "1.0.0"
                "has_submodule" = False
            }
            - Example of return object of module that have sub modules
            {
                "module_name": "CPLD",
                "fw_version": {
                    "CPLD1" : "1.0.0",
                    "CPLD2" : "1.1.0"
                }
                "has_submodule" = True
            }            
        """
        return {}

    @abc.abstractmethod
    def install(self, module_name, image_path):
        """
        Install firmware to module

        :param module_name: A string, name of module that need to install new firmware
        :param image_path: A string, path to firmware image 
        :return: Boolean,
            - True if install process is finished without error
            - False if install process is failed
        """
        return False
