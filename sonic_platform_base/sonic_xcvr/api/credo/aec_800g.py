"""
    aec_800g.py

    Implementation of Credo AEC cable specific in addition to the CMIS specification.
"""

from ...fields import consts
from ..public.cmis import CmisApi

class CmisAec800gApi(CmisApi):
    def set_firmware_download_target_end(self, target):
        return self.xcvr_eeprom.write(consts.TARGET_MODE, target)
