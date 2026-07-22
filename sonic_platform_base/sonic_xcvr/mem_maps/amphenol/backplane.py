"""
    Custom memory map for Amphenol 800G Backplane connector
"""

from ..public.cmis import CmisFlatMemMap
from ..public.cmis.pages.page import CmisPage
from ...fields.xcvr_field import CodeRegField
from ...fields import consts


class _AmphSlotIdPage(CmisPage):
    """Page 00h extension: Amphenol Cartridge Slot ID byte (offset 203)."""

    def __init__(self, codes):
        super().__init__(codes, page=0x00, bank=0)
        self.fields[consts.CARTRDIGE_SLOT_ID] = [
            CodeRegField(consts.CARTRDIGE_SLOT_ID, self.getaddr(203), codes.CARTRDIGE_SLOT_ID),
        ]


class AmphBackplaneMemMap(CmisFlatMemMap):
    def __init__(self, codes):
        super().__init__(codes)
        self.add_pages(_AmphSlotIdPage(codes))
