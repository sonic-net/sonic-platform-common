"""
    aec_800g.py

    Implementation of Credo AEC cable specific XcvrMemMap for CMIS Rev 5.0
"""

from ..public.cmis import CmisMemMap
from ...fields.xcvr_field import (
    CodeRegField,
    DateField,
    HexRegField,
    NumberRegField,
    RegBitField,
    RegGroupField,
    StringRegField,
)
from ...fields import consts

class CmisAec800gMemMap(CmisMemMap):
    def __init__(self, codes):
        super(CmisAec800gMemMap, self).__init__(codes)

        self.VENDOR_CUSTOM = RegGroupField(consts.VENDOR_CUSTOM,
            NumberRegField(consts.TARGET_MODE, self.getaddr(0x0, 64), ro=False)
        )

    def getaddr(self, page, offset, page_size=128):
        return page * page_size + offset
