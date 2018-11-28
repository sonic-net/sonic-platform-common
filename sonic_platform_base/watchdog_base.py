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
            A boolean, True if watchdog was armed successfully, False if not
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
        Retrieves the armed state of the hardware watchdog.

        Returns:
            A boolean, True if watchdog is armed, False if not
        """
        raise NotImplementedError

    def get_remaining_time(self):
        """
        If the watchdog is armed, retrieve the number of seconds remaining on
        the watchdog timer

        Returns:
            An integer specifying the number of seconds remaining on thei
            watchdog timer. If the watchdog is not armed, returns -1.
        """
        raise NotImplementedError
