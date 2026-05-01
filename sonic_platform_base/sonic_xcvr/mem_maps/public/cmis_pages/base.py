"""
    base.py

    Abstract class for CMIS pages
"""

from typing import Dict
from ...xcvr_mem_map import XcvrMemMap
from ....fields.xcvr_field import RegField, RegGroupField
from .cmis_page_consts import CMIS_NUM_BANKED_PAGES, CMIS_ARCH_PAGES

def get_field_from_pages(field_name, *pages):
        fields = []
        for page in pages:
            if hasattr(page, 'fields') and field_name in page.fields:
                fields.extend(page.fields[field_name])
        return fields

class CmisPage(XcvrMemMap):
    fields: Dict[str, list[RegField]]  # This is a Dictionary of list of fields

    def __init__(self, codes, page, bank=0):
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

    def register_fields(self, memmap):
        """Compose this page's fields onto the memory map.

        Each key in self.fields becomes both the setattr name on memmap and the
        RegGroupField.name. If memmap already carries a RegGroupField under the
        same key (from a previously-registered page), this page's contributions
        are merged in and the field list is re-sorted by offset to preserve the
        RegGroupField invariant (first member must have the smallest offset).
        """
        for key, contribs in self.fields.items():
            if not contribs:
                continue
            existing = getattr(memmap, key, None)
            field_key = key
            field_values = contribs
            if isinstance(existing, RegGroupField):
                field_key = existing.name
                field_values = sorted(
                    list(existing.fields) + list(contribs),
                    key=lambda f: f.get_offset(),
                )
            setattr(memmap, key, RegGroupField(field_key, *field_values))
