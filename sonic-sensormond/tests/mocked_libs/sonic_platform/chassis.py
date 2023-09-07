"""
    Mock implementation of sonic_platform package for unit testing
"""

import sys
from unittest import mock
from sonic_platform_base.chassis_base import ChassisBase


class Chassis(ChassisBase):
    def __init__(self):
        ChassisBase.__init__(self)
        self._eeprom = mock.MagicMock()

    def get_eeprom(self):
        return self._eeprom
