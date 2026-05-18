"""
    page.py

    Abstract class for CMIS pages
"""

from typing import Dict
from ....xcvr_mem_map import XcvrMemMap
from .....fields.xcvr_field import RegField, RegGroupField
from .consts import CMIS_ARCH_PAGES, CMIS_NUM_NON_BANKED_PAGES


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

    @staticmethod
    def linear_offset(page, bank, offset, page_size=128):
        """Compute the linear EEPROM offset for a CMIS (page, bank, offset) triple.

        Lower memory (page 0, offset < 128) is unaffected by paging or banking.

        Bank is clamped to 0 for:
          - non-banked pages (00h-0Fh): writing BankSelect is not required per CMIS 5.x
          - CDB pages (9Fh-AFh): treated as non-banked here, though the spec permits
            multiple CDB instances reachable via bank selection. Revisit if support
            for multiple CDB instances is added.

        Each bank is a full 256-page (32KB) architectural block, matching the kernel
        driver layout, even though only pages 10h-FFh (240 pages) are actually banked.
        """
        if page == 0 and offset < 128:
            return offset
        if page < CMIS_NUM_NON_BANKED_PAGES or 0x9F <= page <= 0xAF:
            bank = 0
        return (bank * CMIS_ARCH_PAGES + page) * page_size + offset

    @staticmethod
    def get_field_from_pages(field_name, *pages):
        fields = []
        for page in pages:
            if hasattr(page, 'fields') and field_name in page.fields:
                fields.extend(page.fields[field_name])
        return fields

    def getaddr(self, offset, page_size=128):
        """Linear EEPROM offset for this page's `(page, bank)` at `offset`.

        See CmisPage.linear_offset for the full addressing rules (including bank
        clamping for non-banked and CDB pages).
        """
        return CmisPage.linear_offset(self._page, self._bank, offset, page_size)

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
