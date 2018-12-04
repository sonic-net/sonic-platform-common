#
# platform_base.py
#
# Base class for implementing platform-specific functionality in SONiC.
# This is the root class of sonic_platform_base hierarchy. A platform
# may contain one or more chassis. Classes derived from this class provide
# the ability to interact with all available chassis on the platform.
#

from __future__ import print_function

import sys


class PlatformBase(object):

    # ChassisBase-derived object representing the platform's chassis
    _chassis = None

    def get_chassis(self):
        """
        Retrieves the chassis for this platform

        Returns:
            An object derived from ChassisBase representing the platform's
            chassis
        """
        return self._chassis
