"""
    cmis package

    Re-exports the public API of cmis.py so existing imports of the form
    `from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import X`
    keep resolving after the cmis.py module became the cmis/ package.
"""

from .cmis import (
    CmisFlatMemMap,
    CmisMemMap,
    CMIS_EEPROM_PAGE_SIZE,
    CMIS_NUM_NON_BANKED_PAGES,
    CMIS_ARCH_PAGES,
)
