"""
    platform_base.py

    Base class for implementing platform-specific functionality in SONiC.
    This is the root class of sonic_platform_base hierarchy. A platform
    may contain one or more chassis. Classes derived from this class provide
    the ability to interact with all available chassis on the platform.
"""

class PlatformBase(object):

    def __init__(self):
        # ChassisBase-derived object representing the platform's chassis
        self._chassis = None

    def get_chassis(self):
        """
        Retrieves the chassis for this platform

        Returns:
            An object derived from ChassisBase representing the platform's
            chassis
        """
        return self._chassis
