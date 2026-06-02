"""
eeprom_utils.py

In-memory EEPROM for use in unit tests. Provides a real reader/writer backed
by a bytearray so that encode/decode logic is exercised end-to-end without
requiring physical hardware.
"""

from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.consts import (
    CMIS_EEPROM_PAGE_SIZE,
    CMIS_ARCH_PAGES,
)


class InMemoryEeprom:
    """
    XcvrEeprom backed by an in-memory bytearray.

    Exposes the raw `memory` buffer so tests can directly pre-populate
    read-only fields before exercising API decode logic.

    Args:
        mem_map:   an XcvrMemMap instance to use for field lookup.
        num_banks: number of banks to allocate space for. Each bank is a full
                   256-page architectural block (matching the linear addressing
                   in CmisPage.linear_offset), so the buffer grows by
                   CMIS_ARCH_PAGES * CMIS_EEPROM_PAGE_SIZE per bank. Defaults to 1.
    """

    def __init__(self, mem_map, num_banks=1):
        size = num_banks * CMIS_ARCH_PAGES * CMIS_EEPROM_PAGE_SIZE
        self.memory = bytearray(size)
        self.eeprom = XcvrEeprom(self._reader, self._writer, mem_map)

    def _reader(self, offset, size):
        return bytes(self.memory[offset:offset + size])

    def _writer(self, offset, size, data):
        self.memory[offset:offset + size] = data
        return True
