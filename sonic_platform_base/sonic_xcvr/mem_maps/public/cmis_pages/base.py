"""
    base.py

    Abstract class for CMIS pages
"""

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
        """Return a linear address for this page that encodes the bank.

        Page 0 is non-banked (CMIS spec) so bank is dropped. Upper pages encode
        bank as a 32KB-per-bank stride: ``(bank * CMIS_ARCH_PAGES + page) * 128 + offset``.
        Platform readers extract the bank from the upper bits of this address.
        """
        if self._page == 0:
            return offset
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
