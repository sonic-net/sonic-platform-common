"""
    cmisTargetFWUpgrade.py

    Implementation of memory map for CMIS based modules supporting firmware
    upgrade of remote target from the local target itself.
"""

from .cmis import CmisMemMap
from ...fields.xcvr_field import (
    NumberRegField,
    RegGroupField,
    ServerFWVersionRegField
)
from ...fields import consts

class CmisTargetFWUpgradeMemMap(CmisMemMap):
    # Vendor agnostic implementation to be added here
    def __init__(self, codes):
        super().__init__(codes)

        self.CMIS_TARGET_SERVER_INFO = RegGroupField(consts.CMIS_TARGET_SERVER_INFO,
            NumberRegField(consts.PAGE_SELECT_BYTE, self.getaddr(0, 127), format="B", size=1, ro=False),
            NumberRegField(consts.SERVER_FW_MAGIC_BYTE, self.getaddr(0x3, 128), format="B", size=1),
            NumberRegField(consts.SERVER_FW_CHECKSUM, self.getaddr(0x3, 129), format="B", size=1),
            ServerFWVersionRegField(consts.SERVER_FW_VERSION, self.getaddr(0x3, 130), size=16))
