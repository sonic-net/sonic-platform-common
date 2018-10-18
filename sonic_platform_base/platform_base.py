#
# platform_base.py
#
# Abstract base class for implementing platform-specific functionality in
# SONiC. This is the root class of sonic_platform_base hierarchy. A platform
# may contain one or more chassis. Classes derived from this class provide
# the ability to interact with all available chassis on the platform.
#

from __future__ import print_function

try:
    import sys
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


class PlatformBase(object):

    # List of ChassisBase-derived objects representing all chassis available
    # on the platform
    chassis_list = []

    def get_num_chassis(self):
        """
        Retrieves the number of chassis available on the platform

        Returns:
            An integer, the number of chassis available on the platform
        """
        return len(self.chassis_list)

    def get_all_chassis(self):
        """
        Retrieves all chassis available on the platform

        Returns:
            A list of objects derived from ChassisBase, one for each chassis
            available on the platform
        """
        return self.chassis_list

    def get_chassis(self, index):
        """
        Retrieves a chassis by its 1-based index

        Args:
            index: An integer, the index (1-based) of the chassis to retrieve

        Returns:
            An object derived from ChassisBase containing the chassis
            specified by <index>
        """
        chassis = None

        try:
            chassis = self.chassis_list[index]
        except IndexError:
            sys.stderr.write("Chassis index {} out of range (0-{})\n".format(
                             index, len(self.chassis_list)-1))

        return chassis
