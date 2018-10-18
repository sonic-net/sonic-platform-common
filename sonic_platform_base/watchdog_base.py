#
# watchdog_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a hardware watchdog module in SONiC
#

try:
    import abc
    from . import device_base
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


# NOTE: This class inherits the metaclass 'abc.ABCMeta' from DeviceBase
class WatchdogBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a hardware watchdog module
    """

    # Possible fan directions
    FAN_DIRECTION_INTAKE = "intake"
    FAN_DIRECTION_EXHAUST = "exhaust"

    @abc.abstractmethod
    def arm(self, seconds):
        """
        Arm the hardware watchdog with a timeout of <seconds> seconds

        Returns:
            A boolean, True if watchdog is armed successfully, False if not
        """
        return None

    @abc.abstractmethod
    def disarm(self):
        """
        Disarm the hardware watchdog

        Returns:
            A boolean, True if watchdog is disarmed successfully, False if not
        """
        return 0

    @abc.abstractmethod
    def is_armed(self):
        """
        Retrieves the armed state of the hardware watchdog and if armed, the
        number of seconds remaining on the watchdog timer

        Returns:
            A tuple of the form (bool, int). If the watchdog is armed, the
            first value will be 'true' and the second value will be the
            number of seconds remaining on the watchdog timer. If the watchdog
            is disarmed, the first value will be 'false' and the integer
            returned as the second value should be ignored.
        """
        return (false, 0)
