"""
    cmisTargetFWUpgrade.py

    Implementation of memory map for CMIS based modules supporting firmware
    upgrade of remote target from the local target itself.
"""

from .cmis import CmisMemMap
from ...fields.xcvr_field import (
    NumberRegField,
    RegGroupField,
)
from ...fields import consts

class CmisTargetFWUpgradeMemMap(CmisMemMap):
    def __init__(self, codes):
        super().__init__(codes)

        self.VENDOR_CUSTOM = RegGroupField(consts.VENDOR_CUSTOM,
            NumberRegField(consts.TARGET_MODE, self.getaddr(0x0, 64), ro=False)
        )

    def getaddr(self, page, offset, page_size=128):
        return page * page_size + offset
