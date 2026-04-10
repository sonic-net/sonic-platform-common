"""
    base.py

    Abstract class for CMIS pages
"""

from typing import Dict
from ...xcvr_mem_map import XcvrMemMap
from ....fields.xcvr_field import RegField
from .cmis_page_consts import CMIS_NUM_BANKED_PAGES, CMIS_ARCH_PAGES

def get_field_from_pages(field_name, *pages):
        fields = []
        for page in pages:
            if hasattr(page, 'fields') and field_name in page.fields:
                fields.extend(page.fields[field_name])
        return fields

class CmisPage(XcvrMemMap):
    fields: Dict[str, list[RegField]]  # This is a Dictionary of list of fields

    def __init__(self, codes, page, bank):
        super(CmisPage, self).__init__(codes)
        self._page = page
        self._bank = bank
        self.fields = {}

    @property
    def page(self):
        """Returns the page number (read-only)."""
        return self._page

    @property
    def bank(self):
        """Returns the bank number (read-only)."""
        return self._bank

    def getaddr(self, offset, page_size=128):
        """
        Calculate linear offset for CMIS memory map using instance's bank.

        For lower memory (page 0, offset < 128):
            linear_offset = offset

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
        if self._page == 0 and offset < 128:
            # Lower memory - not affected by banking
            return offset

        # For all paged memory (including bank 0), use the unified formula
        # that treats each bank as a 256-page (32KB) block
        return (self._bank * CMIS_ARCH_PAGES + self._page) * page_size + offset

    def get_field_values(self, field: str):
        return self.fields[field]
