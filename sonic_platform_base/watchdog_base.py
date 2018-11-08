#
# watchdog_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a hardware watchdog module in SONiC
#


class WatchdogBase:
    """
    Abstract base class for interfacing with a hardware watchdog module
    """

    def arm(self, seconds):
        """
        Arm the hardware watchdog with a timeout of <seconds> seconds.
        If the watchdog is currently armed, calling this function will
        simply reset the timer to the provided value.

        Returns:
            A boolean, True if watchdog is armed successfully, False if not
        """
        raise NotImplementedError

    def disarm(self):
        """
        Disarm the hardware watchdog

        Returns:
            A boolean, True if watchdog is disarmed successfully, False if not
        """
        raise NotImplementedError

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
        raise NotImplementedError
