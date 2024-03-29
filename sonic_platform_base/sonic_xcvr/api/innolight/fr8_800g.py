"""
    fr8_800g.py

    Implementation of Innolight FR8 module specific in addition to the CMIS specification.
"""

from ...fields import consts
from ..public.cmis import CmisApi

class CmisFr8800gApi(CmisApi):
    def get_transceiver_info_firmware_versions(self):
        InactiveFirmware = self.get_module_inactive_firmware() + ".0"
        ActiveFirmware = self.get_module_active_firmware() + ".0"

        return [ActiveFirmware, InactiveFirmware]
