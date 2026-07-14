"""
    c_cmis.py

    Implementation of XcvrMemMap for C-CMIS Rev 1.1
"""

from .cmis import CmisMemMap
from .pages import (
    CCmisModuleConfigSupportPage,
    CCmisMediaLaneFecPmPage,
    CCmisMediaLaneLinkPmPage,
<<<<<<< HEAD
=======
    CCmisDataPathHostIfPmPage,
    CCmisPmAdvertisementPage,
>>>>>>> bec9ff8 (NOS-11204: Add C-CMIS PM API logic and advertising (#147))
)


class CCmisMemMap(CmisMemMap):
    def __init__(self, codes, bank=0):
        super(CCmisMemMap, self).__init__(codes, bank=bank)

        # C-CMIS-specific pages on top of the base CMIS memory map.
        self.add_pages(
            CCmisModuleConfigSupportPage(codes, bank=bank),  # 0x04
            CCmisMediaLaneFecPmPage(codes, bank=bank),       # 0x34
            CCmisMediaLaneLinkPmPage(codes, bank=bank),      # 0x35
<<<<<<< HEAD
=======
            CCmisDataPathHostIfPmPage(codes, bank=bank),     # 0x3A
            CCmisPmAdvertisementPage(codes, bank=bank),      # 0x42
>>>>>>> bec9ff8 (NOS-11204: Add C-CMIS PM API logic and advertising (#147))
        )
