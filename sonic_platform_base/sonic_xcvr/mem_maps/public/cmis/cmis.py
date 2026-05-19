"""
    cmis.py

    Implementation of XcvrMemMap for CMIS Rev 5.0
"""

from ...xcvr_mem_map import XcvrMemMap
from .pages import (
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
