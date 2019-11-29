#
# device_base.py
#
# Abstract base class for interfacing with a generic type of platform
# peripheral device in SONiC
#

class DeviceBase(object):
    """
    Abstract base class for interfacing with a generic type of platform
    peripheral device
    """

    def get_name(self):
        """
        Retrieves the name of the device

        Returns:
            string: The name of the device
        """
        raise NotImplementedError


    def get_presence(self):
        """
        Retrieves the presence of the device

        Returns:
            bool: True if device is present, False if not
        """
        raise NotImplementedError

    def get_model(self):
        """
        Retrieves the model number (or part number) of the device

        Returns:
            string: Model/part number of device
        """
        raise NotImplementedError

    def get_serial(self):
        """
        Retrieves the serial number of the device

        Returns:
            string: Serial number of device
        """
        raise NotImplementedError

    def get_status(self):
        """
        Retrieves the operational status of the device

        Returns:
            A boolean value, True if device is operating properly, False if not
        """
        raise NotImplementedError
