"""
    cmis.py

    Implementation of XcvrMemMap for CMIS Rev 5.0
"""

from ..xcvr_mem_map import XcvrMemMap
from ...fields.xcvr_field import (
    CodeRegField,
    DateField,
    HexRegField,
    NumberRegField,
    RegBitField,
    RegGroupField,
    StringRegField,
)
from ...fields.public.cmis import CableLenField
from ...fields import consts
from ...fields.consts import *
from .cmis_pages.base import CMIS_NUM_NON_BANKED_PAGES, CMIS_ARCH_PAGES

# Import page classes
from .cmis_pages import (
    CmisAdministrativeLowerPage,
    CmisAdministrativeUpperPage,
    CmisAdvertisingPage,
    CmisThresholdsPage,
    CmisLaneDatapathConfigPage,
    CmisLaneDatapathStatusPage,
    CmisTunableLaserCtrlStatusPage,
    CmisModulePerfDiagCtrlPage,
    CmisVdmAdvertisingCtrlPage,
    CmisCdbMessagePage,
)

class CmisFlatMemMap(XcvrMemMap):
    """
    Memory map for CMIS flat memory (Lower page and Upper page 0h ONLY)
    """
    def __init__(self, codes, bank=0):
        self._bank = bank
        super(CmisFlatMemMap, self).__init__(codes)
        self.pages = []

        # Page 0x00 is split into a lower-half page (offsets 0-127) and an
        # upper-half page (offsets 128-255). Each page class owns its half;
        # register_fields merges shared field groups (e.g. ADMIN_INFO_FIELD).
        self.add_pages(
            CmisAdministrativeLowerPage(codes),
            CmisAdministrativeUpperPage(codes),
        )

    def add_pages(self, *pages):
        """Append pages to self.pages and register their fields onto self."""
        self.pages.extend(pages)
        for page in pages:
            page.register_fields(self)

    @property
    def bank(self):
        """Returns the bank number (read-only)."""
        return self._bank

    def getaddr(self, page, offset, page_size=128):
        """
        Calculate linear offset for CMIS memory map using instance's bank.

        For lower memory (page 0, offset < 128):
            linear_offset = offset

        For non-banked pages (00h-0Fh):
            bank is clamped to 0 because writing the BankSelect register is
            not necessary for these pages per CMIS 5.x.

        For paged memory:
            offset_in_paged_area = (page * page_size + offset) - 128
            bytes_per_bank = CMIS_ARCH_PAGES * page_size  (256 * 128 = 32KB)
            linear_offset = 128 + (bank * bytes_per_bank) + offset_in_paged_area

        Simplified:
            linear_offset = (bank * CMIS_ARCH_PAGES + page) * page_size + offset

        Note: Each bank is treated as a full 256-page (32KB) architectural block,
        even though only pages 10h-FFh (240 pages) are actually banked. This ensures
        proper alignment and matches the kernel driver behavior.
        """
        if page == 0 and offset < 128:
            # Lower memory - not affected by banking or paging.
            return offset

        # If we are accessing a non-banked page, there is no reason to set the bank
        # to a non-zero value. 
        bank = 0 if page < CMIS_NUM_NON_BANKED_PAGES else self.bank
        # Note: we consider CDB pages as non-banked here, though it
        # is possible to have multiple CDB instances exposed for a module where
        # each instance is accessible via bank selection.
        # This can be deleted once support for multiple CDB instances is added.
        bank = 0 if 0x9F <= page <= 0xAF else bank
        # For all paged memory (including bank 0), use the unified formula
        # that treats each bank as a 256-page (32KB) block
        return (bank * CMIS_ARCH_PAGES + page) * page_size + offset

class CmisMemMap(CmisFlatMemMap):
    def __init__(self, codes, bank=0):
        super(CmisMemMap, self).__init__(codes, bank=bank)

        # Add CMIS upper pages (0x01 and beyond). Cross-page field groups
        # (e.g., ADVERTISING_FIELD spans pg_01 + pg_11) are merged automatically
        # by CmisPage.register_fields.
        self.add_pages(
            CmisAdvertisingPage(codes),                           # 0x01
            CmisThresholdsPage(codes),                            # 0x02
            CmisLaneDatapathConfigPage(codes, bank=bank),         # 0x10
            CmisLaneDatapathStatusPage(codes, bank=bank),         # 0x11
            CmisTunableLaserCtrlStatusPage(codes, bank=bank),     # 0x12
            CmisModulePerfDiagCtrlPage(codes, bank=bank),         # 0x13
            CmisVdmAdvertisingCtrlPage(codes, bank=bank),         # 0x2F
            CmisCdbMessagePage(codes, bank=bank),                 # 0x9F
        )
