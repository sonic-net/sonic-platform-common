"""
    page35.py

    C-CMIS Page 35h - Media Lane Link Performance Monitors.
    Contains all the coherent PMs in C-CMIS spec.
"""

from .page import CmisPage
from .....fields.xcvr_field import NumberRegField
from .....fields import consts


class CCmisMediaLaneLinkPmPage(CmisPage):
    """C-CMIS Page 35h: coherent performance-monitor counters."""

    def __init__(self, codes, bank=0, page=0x35):
        super().__init__(codes, page=page, bank=bank)

        self.fields[consts.MEDIA_LANE_LINK_PM] = [
            NumberRegField(consts.RX_AVG_CD_PM, self.getaddr(128), format=">i", size=4),
            NumberRegField(consts.RX_MIN_CD_PM, self.getaddr(132), format=">i", size=4),
            NumberRegField(consts.RX_MAX_CD_PM, self.getaddr(136), format=">i", size=4),
            NumberRegField(consts.RX_AVG_DGD_PM, self.getaddr(140), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_MIN_DGD_PM, self.getaddr(142), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_MAX_DGD_PM, self.getaddr(144), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_SOPMD_PM, self.getaddr(146), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_MIN_SOPMD_PM, self.getaddr(148), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_MAX_SOPMD_PM, self.getaddr(150), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_PDL_PM, self.getaddr(152), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MIN_PDL_PM, self.getaddr(154), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MAX_PDL_PM, self.getaddr(156), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_AVG_OSNR_PM, self.getaddr(158), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MIN_OSNR_PM, self.getaddr(160), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MAX_OSNR_PM, self.getaddr(162), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_AVG_ESNR_PM, self.getaddr(164), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MIN_ESNR_PM, self.getaddr(166), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MAX_ESNR_PM, self.getaddr(168), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_AVG_CFO_PM, self.getaddr(170), format=">h", size=2),
            NumberRegField(consts.RX_MIN_CFO_PM, self.getaddr(172), format=">h", size=2),
            NumberRegField(consts.RX_MAX_CFO_PM, self.getaddr(174), format=">h", size=2),
            NumberRegField(consts.RX_AVG_EVM_PM, self.getaddr(176), format=">H", size=2, scale=655.35),
            NumberRegField(consts.RX_MIN_EVM_PM, self.getaddr(178), format=">H", size=2, scale=655.35),
            NumberRegField(consts.RX_MAX_EVM_PM, self.getaddr(180), format=">H", size=2, scale=655.35),
            NumberRegField(consts.TX_AVG_POWER_PM, self.getaddr(182), format=">h", size=2, scale=100.0),
            NumberRegField(consts.TX_MIN_POWER_PM, self.getaddr(184), format=">h", size=2, scale=100.0),
            NumberRegField(consts.TX_MAX_POWER_PM, self.getaddr(186), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_POWER_PM, self.getaddr(188), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_MIN_POWER_PM, self.getaddr(190), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_MAX_POWER_PM, self.getaddr(192), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_SIG_POWER_PM, self.getaddr(194), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_MIN_SIG_POWER_PM, self.getaddr(196), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_MAX_SIG_POWER_PM, self.getaddr(198), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_SOPROC_PM, self.getaddr(200), format=">H", size=2),
            NumberRegField(consts.RX_MIN_SOPROC_PM, self.getaddr(202), format=">H", size=2),
            NumberRegField(consts.RX_MAX_SOPROC_PM, self.getaddr(204), format=">H", size=2),
            NumberRegField(consts.RX_AVG_MER_PM, self.getaddr(206), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MIN_MER_PM, self.getaddr(208), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MAX_MER_PM, self.getaddr(210), format=">H", size=2, scale=10.0),
        ]
