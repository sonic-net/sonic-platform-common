from unittest.mock import patch
from mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.api.innolight.fr_800g import CmisFr800gApi

class TestCmisFr800gApi(object):
    codes = CmisCodes
    mem_map = CmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = CmisFr800gApi(eeprom)

    def test_get_transceiver_info_firmware_versions(self):
        self.api.get_module_inactive_firmware = MagicMock()
        self.api.get_module_inactive_firmware.return_value = "1.0"
        self.api.get_module_active_firmware = MagicMock()
        self.api.get_module_active_firmware.return_value = "1.1"
        expected_result = {"active_firmware" : "1.1.0", "inactive_firmware" : "1.0.0"}
        result = self.api.get_transceiver_info_firmware_versions()
        assert result == expected_result
