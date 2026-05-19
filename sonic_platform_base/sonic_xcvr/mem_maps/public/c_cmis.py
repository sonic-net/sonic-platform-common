"""
    c_cmis.py

    Implementation of XcvrMemMap for C-CMIS Rev 1.1
"""

from .cmis import CmisMemMap
from .cmis.pages import (
    CCmisModuleConfigSupportPage,
    CCmisMediaLaneFecPmPage,
    CCmisMediaLaneLinkPmPage,
)


class CCmisMemMap(CmisMemMap):
    def __init__(self, codes, bank=0):
        super(CCmisMemMap, self).__init__(codes, bank=bank)

        # C-CMIS-specific pages on top of the base CMIS memory map.
        self.add_pages(
            CCmisModuleConfigSupportPage(codes, bank=bank),  # 0x04
            CCmisMediaLaneFecPmPage(codes, bank=bank),       # 0x34
            CCmisMediaLaneLinkPmPage(codes, bank=bank),      # 0x35
        )
