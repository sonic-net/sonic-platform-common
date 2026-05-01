"""
    elsfp.py

    Implementation of XcvrMemMap for ELSFP
    Extends CMIS Rev 5.0 with ELSFP-specific pages 1Ah and 1Bh
"""

from .cmis import CmisFlatMemMap

# Import CMIS page classes (excluding pages 10h, 11h, 12h, 13h)
from .cmis.pages import (
    CmisAdvertisingPage,
    CmisThresholdsPage,
    ElsfpAdvertisementsFlagsCtrlPage,
    ElsfpSetpointsMonitorsPage,
)


class ElsfpMemMap(CmisFlatMemMap):
    """
    Memory map for ELSFP.

    Inherits CmisFlatMemMap (Page 00h) and adds:
    - Page 01h: CMIS Advertising
    - Page 02h: CMIS Thresholds
    - Page 1Ah: ELSFP Advertisements, Flags, and Controls
    - Page 1Bh: ELSFP Setpoints and Monitors

    Excludes CMIS pages 10h, 11h, 12h, 13h (lane datapath and module control pages).
    """

    def __init__(self, codes, bank=0):
        # Initialize base CmisFlatMemMap (Page 00h lower and upper)
        super(ElsfpMemMap, self).__init__(codes, bank=bank)

        self.add_pages(
            CmisAdvertisingPage(codes),                # 0x01
            CmisThresholdsPage(codes),                 # 0x02
            ElsfpAdvertisementsFlagsCtrlPage(codes, bank=bank),   # 0x1A
            ElsfpSetpointsMonitorsPage(codes, bank=bank),         # 0x1B
        )
