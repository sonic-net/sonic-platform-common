"""
    cmis_module_precoding.py

    Memory map for Pinewave CMIS modules with module-wide TP1/TP4 precoding control
"""

from ..public.cmis import CmisMemMap
from ..public.cmis.pages.page import CmisPage
from ...fields.xcvr_field import NumberRegField
from ...fields import pinewave_consts as pw


class _PinewaveLowerPage(CmisPage):
    """Lower memory byte 29 (Custom in CMIS): module TP1/TP4 precoding control."""

    def __init__(self, codes):
        super().__init__(codes, page=0x00, bank=0)
        self.fields[pw.MODULE_PRECODING_FIELD] = [
            NumberRegField(pw.MODULE_PRECODING_CONTROL, self.getaddr(29), size=1, ro=False),
        ]


class PinewaveCmisMemMap(CmisMemMap):
    def __init__(self, codes, bank=0):
        super().__init__(codes, bank=bank)
        self.add_pages(_PinewaveLowerPage(codes))
