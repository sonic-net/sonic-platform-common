"""
    cmisTargetFWUpgrade.py

    Implementation of XcvrApi for CMIS based modules supporting firmware
    upgrade of remote target from the local target itself.
"""

from ...fields import consts
from .cmis import CmisApi

class CmisTargetFWUpgradeAPI(CmisApi):
    def set_firmware_download_target_end(self, target):
        return self.xcvr_eeprom.write(consts.TARGET_MODE, target)