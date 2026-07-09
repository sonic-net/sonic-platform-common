"""
    page34.py

    C-CMIS Page 34h - Media Lane FEC Performance Monitors.
"""

from .page import CmisPage
from .....fields.xcvr_field import NumberRegField
from .....fields import consts


class CCmisMediaLaneFecPmPage(CmisPage):
    """C-CMIS Page 34h: media-lane FEC performance-monitor counters."""

    def __init__(self, codes, bank=0, page=0x34):
        super().__init__(codes, page=page, bank=bank)

        self.fields[consts.MEDIA_LANE_FEC_PM] = [
            NumberRegField(consts.RX_BITS_PM, self.getaddr(128), format=">Q", size=8),
            NumberRegField(consts.RX_BITS_SUB_INTERVAL_PM, self.getaddr(136), format=">Q", size=8),
            NumberRegField(consts.RX_CORR_BITS_PM, self.getaddr(144), format=">Q", size=8),
            NumberRegField(consts.RX_MIN_CORR_BITS_SUB_INTERVAL_PM, self.getaddr(152), format=">Q", size=8),
            NumberRegField(consts.RX_MAX_CORR_BITS_SUB_INTERVAL_PM, self.getaddr(160), format=">Q", size=8),
            NumberRegField(consts.RX_FRAMES_PM, self.getaddr(168), format=">I", size=4),
            NumberRegField(consts.RX_FRAMES_SUB_INTERVAL_PM, self.getaddr(172), format=">I", size=4),
            NumberRegField(consts.RX_FRAMES_UNCORR_ERR_PM, self.getaddr(176), format=">I", size=4),
            NumberRegField(consts.RX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM, self.getaddr(180), format=">I", size=4),
            NumberRegField(consts.RX_MAX_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM, self.getaddr(184), format=">I", size=4),
        ]
