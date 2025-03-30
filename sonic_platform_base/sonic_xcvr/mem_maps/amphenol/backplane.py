"""
    Custom memory map for Amphenol 800G Backplane connector
"""

from ...mem_maps.public.cmis import CmisFlatMemMap
from ...fields.xcvr_field import (
    NumberRegField,
    RegGroupField,
    CodeRegField
)
from ...fields import consts

class AmphBackplaneMemMap(CmisFlatMemMap):
    def __init__(self, codes):
        super(AmphBackplaneMemMap, self).__init__(codes)

        self.SLOT_ID = CodeRegField(consts.CARTRDIGE_SLOT_ID, self.getaddr(0x0, 203),
                                                self.codes.CARTRDIGE_SLOT_ID)
