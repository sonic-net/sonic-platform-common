#
# device_base.py
#
# Abstract base class for interfacing with a generic type of platform
# peripheral device in SONiC
#

try:
    import abc
    import six
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


# NOTE: Using 'six' module here to ensure consistent abc metaclass behavior
# with both Python 2.x and Python 3.x
@six.add_metaclass(abc.ABCMeta)
class DeviceBase(object):
    """
    Abstract base class for interfacing with a generic type of platform
    peripheral device
    """

    @abc.abstractmethod
    def get_presence(self):
        """
        Retrieves the presence of the device

        Returns:
            bool: True if device is present, False if not
        """
        return False

    @abc.abstractmethod
    def get_model(self):
        """
        Retrieves the model number (or part number) of the device

        Returns:
            string: Model/part number of device
        """
        return None

    @abc.abstractmethod
    def get_serial(self):
        """
        Retrieves the serial number of the device

        Returns:
            string: Serial number of device
        """
        return None

    @abc.abstractmethod
    def get_status(self):
        """
        Retrieves the operational status of the device

        Returns:
            A boolean value, True if device is operating properly, False if not
        """
        return False

    @abc.abstractmethod
    def get_change_event(self, timeout=0):
        """
        Returns a dictionary containing all devices which have experienced a
        change

        Args:
            timeout: Timeout in milliseconds (optional). If timeout == 0,
                this method will block until a change is detected.

        Returns:
            (bool, dict):
                - True if call successful, False if not;
                - Dict where key is device ID and value is device event,
                  status='1' represents device inserted,
                  status='0' represents device removed. Ex. {'0': '1', '1': '0'}
        """
        return (False, None)
