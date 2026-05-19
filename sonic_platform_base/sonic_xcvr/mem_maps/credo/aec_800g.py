"""
    aec_800g.py

    Implementation of Credo AEC cable specific XcvrMemMap for CMIS Rev 5.0
    Includes CMIS target firmware upgrade memory map for modules supporting
    firmware upgrade of a remote target from the local target itself.
"""

from ..public.cmis import CmisMemMap
from ..public.cmis.pages.page import CmisPage
from ...fields.xcvr_field import NumberRegField, ServerFWVersionRegField
from ...fields import consts


class _CredoAec800gPage00(CmisPage):
    """Credo vendor extensions on CMIS Page 00h: page-select byte and target-mode register."""

    def __init__(self, codes):
        super().__init__(codes, page=0x00, bank=0)
        self.fields[consts.CMIS_TARGET_SERVER_INFO] = [
            NumberRegField(consts.PAGE_SELECT_BYTE, self.getaddr(127), format="B", size=1, ro=False),
        ]
        self.fields[consts.VENDOR_CUSTOM] = [
            NumberRegField(consts.TARGET_MODE, self.getaddr(64), ro=False),
        ]


class _CredoAec800gPage03(CmisPage):
    """Credo server-firmware fields on CMIS Page 03h."""

    def __init__(self, codes):
        # Page 0x03 < 0x10: linear_offset clamps bank to 0 regardless.
        super().__init__(codes, page=0x03, bank=0)
        self.fields[consts.CMIS_TARGET_SERVER_INFO] = [
            NumberRegField(consts.SERVER_FW_MAGIC_BYTE, self.getaddr(128), format="B", size=1),
            NumberRegField(consts.SERVER_FW_CHECKSUM, self.getaddr(129), format="B", size=1),
            ServerFWVersionRegField(consts.SERVER_FW_VERSION, self.getaddr(130), size=16),
        ]


class CredoAec800gMemMap(CmisMemMap):
    def __init__(self, codes, bank=0):
        super().__init__(codes, bank=bank)
        # Vendor extensions: contributions to CMIS_TARGET_SERVER_INFO from pages 00h
        # and 03h are merged automatically by CmisPage.register_fields.
        self.add_pages(
            _CredoAec800gPage00(codes),
            _CredoAec800gPage03(codes),
        )
