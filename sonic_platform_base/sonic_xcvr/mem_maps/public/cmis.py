"""
    cmis.py

    Implementation of XcvrMemMap for CMIS Rev 5.0

    The actual field definitions live in mem_maps/public/cmis_pages/cmis_pages.py
    as CmisPage subclasses (see nexthop-ai/sonic-platform-common#1, imported as
    a temporary scaffold). This file is now a thin composer that wires the page
    classes onto CmisFlatMemMap / CmisMemMap via CmisPage.register_fields, with
    cross-page RegGroupField merges (ADMIN_INFO, ADVERTISING, MODULE_MONITORS,
    LANE_DATAPATH_STATUS, TRANS_CDB) handled automatically.

    The legacy 2-arg getaddr(page, offset) is preserved on this class so
    downstream subclasses that still add fields directly here (CCmisMemMap,
    CmisTargetFWUpgradeMemMap, AmphBackplaneMemMap, NvidiaCpoOeMemMap)
    continue to work unchanged. New code should define fields inside
    CmisPage subclasses and use page.getaddr(offset) instead.
"""

from ..xcvr_mem_map import XcvrMemMap
from ...fields import consts  # noqa: F401  -- preserved for downstream `cmis.consts` access
from ...fields.consts import *  # noqa: F401,F403  -- preserved re-export of CMIS field constants
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
    """Memory map for CMIS flat memory (Lower page and Upper page 0h ONLY)."""

    def __init__(self, codes, bank=0):
        super(CmisFlatMemMap, self).__init__(codes)
        self.bank = bank
        for page in self._build_pages(codes):
            page.register_fields(self)

    def _build_pages(self, codes):
        """Return the list of CmisPage instances composed onto this memmap.
        Subclasses extend this list to layer additional pages on top.
        """
        return [
            CmisAdministrativeLowerPage(codes),
            CmisAdministrativeUpperPage(codes),
        ]

    def getaddr(self, page, offset, page_size=128):
        return page * page_size + offset


class CmisMemMap(CmisFlatMemMap):
    """Full CMIS memory map (lower + all standard upper pages)."""

    def _build_pages(self, codes):
        return super(CmisMemMap, self)._build_pages(codes) + [
            CmisAdvertisingPage(codes),                 # 0x01
            CmisThresholdsPage(codes),                  # 0x02
            CmisLaneDatapathConfigPage(codes),          # 0x10
            CmisLaneDatapathStatusPage(codes),          # 0x11
            CmisTunableLaserCtrlStatusPage(codes),      # 0x12
            CmisModulePerfDiagCtrlPage(codes),          # 0x13
            CmisVdmAdvertisingCtrlPage(codes),          # 0x2F
            CmisCdbMessagePage(codes),                  # 0x9F
        ]
