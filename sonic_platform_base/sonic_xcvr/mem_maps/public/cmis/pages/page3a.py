"""
    page3a.py

    C-CMIS Page 3Ah - Data Path Host Interface Performance Monitors.
"""

from .page import CmisPage
from .....fields.xcvr_field import NumberRegField
from .....fields import consts


class CCmisDataPathHostIfPmPage(CmisPage):
    """C-CMIS Page 3Ah: data path host-interface performance-monitor counters."""

    def __init__(self, codes, bank=0, page=0x3A):
        super().__init__(codes, page=page, bank=bank)

        self.fields[consts.DATA_PATH_HOST_IF_PM] = [
            NumberRegField(consts.TX_BITS_PM, self.getaddr(128), format=">Q", size=8),
            NumberRegField(consts.TX_BITS_SUB_INTERVAL_PM, self.getaddr(136), format=">Q", size=8),
            NumberRegField(consts.TX_CORR_BITS_PM, self.getaddr(144), format=">Q", size=8),
            NumberRegField(consts.TX_MIN_CORR_BITS_SUB_INTERVAL_PM, self.getaddr(152), format=">Q", size=8),
            NumberRegField(consts.TX_MAX_CORR_BITS_SUB_INTERVAL_PM, self.getaddr(160), format=">Q", size=8),
            NumberRegField(consts.TX_FRAMES_PM, self.getaddr(168), format=">I", size=4),
            NumberRegField(consts.TX_FRAMES_SUB_INTERVAL_PM, self.getaddr(172), format=">I", size=4),
            NumberRegField(consts.TX_FRAMES_UNCORR_ERR_PM, self.getaddr(176), format=">I", size=4),
            NumberRegField(consts.TX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM, self.getaddr(180), format=">I", size=4),
            NumberRegField(consts.TX_MAX_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM, self.getaddr(184), format=">I", size=4),
            NumberRegField(consts.TX_CORRECTED_FRAMES_PM, self.getaddr(188), format=">I", size=4),
            NumberRegField(consts.TX_CORRECTED_FRAMES_SUB_INTERVAL_PM, self.getaddr(192), format=">I", size=4),
        ]
