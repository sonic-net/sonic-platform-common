"""
    aec_800g.py

    Implementation of Credo AEC cable specific XcvrMemMap for CMIS Rev 5.0
    Includes CMIS target firmware upgrade memory map for modules supporting
    firmware upgrade of a remote target from the local target itself.
"""

from ..public.cmis import CmisMemMap
from ...fields.xcvr_field import (
    NumberRegField,
    RegGroupField,
    ServerFWVersionRegField,
)
from ...fields import consts

class CredoAec800gMemMap(CmisMemMap):
    def __init__(self, codes, bank=0):
        super().__init__(codes, bank=bank)

        self.CMIS_TARGET_SERVER_INFO = RegGroupField(consts.CMIS_TARGET_SERVER_INFO,
            NumberRegField(consts.PAGE_SELECT_BYTE, self.getaddr(0, 127), format="B", size=1, ro=False),
            NumberRegField(consts.SERVER_FW_MAGIC_BYTE, self.getaddr(0x3, 128), format="B", size=1),
            NumberRegField(consts.SERVER_FW_CHECKSUM, self.getaddr(0x3, 129), format="B", size=1),
            ServerFWVersionRegField(consts.SERVER_FW_VERSION, self.getaddr(0x3, 130), size=16))

        self.VENDOR_CUSTOM = RegGroupField(consts.VENDOR_CUSTOM,
            NumberRegField(consts.TARGET_MODE, self.getaddr(0x0, 64), ro=False)
        )
