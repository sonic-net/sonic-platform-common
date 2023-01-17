"""
    Mock implementation of sonic_platform package for unit testing
"""

import sys
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

from sonic_platform_base.chassis_base import ChassisBase


class Chassis(ChassisBase):
    def __init__(self):
        ChassisBase.__init__(self)
        self.eeprom = mock.MagicMock()

    def get_eeprom(self):
        return self.eeprom

    def get_my_slot(self):
        return 1

    def get_supervisor_slot(self):
        return 1
