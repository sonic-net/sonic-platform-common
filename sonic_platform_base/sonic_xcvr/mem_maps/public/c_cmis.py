"""
    c_cmis.py

    Implementation of XcvrMemMap for C-CMIS Rev 1.1
"""

from ...fields.xcvr_field import (
    NumberRegField,
    RegGroupField
)
from ...fields import consts
from .cmis import CmisMemMap

class CCmisMemMap(CmisMemMap):
    def __init__(self, codes):
        super(CCmisMemMap, self).__init__(codes)

        self.MODULE_CONFIG_SUPPORT = RegGroupField(consts.MODULE_CONFIG_SUPPORT_FIELD,
            NumberRegField(consts.SUPPORT_GRID, self.getaddr(0x4, 128)),
            NumberRegField(consts.LOW_CHANNEL, self.getaddr(0x4, 158), format=">h", size=2),
            NumberRegField(consts.HIGH_CHANNEL, self.getaddr(0x4, 160), format=">h", size=2),
            NumberRegField(consts.MIN_PROG_OUTPUT_POWER, self.getaddr(0x4, 198), format=">h", size=2, scale = 100.0),
            NumberRegField(consts.MAX_PROG_OUTPUT_POWER, self.getaddr(0x4, 200), format=">h", size=2, scale = 100.0)
        )

        self.MEDIA_LANE_FEC_PM = RegGroupField(consts.MEDIA_LANE_FEC_PM,
            NumberRegField(consts.RX_BITS_PM, self.getaddr(0x34, 128), format=">Q", size=8),
            NumberRegField(consts.RX_BITS_SUB_INTERVAL_PM, self.getaddr(0x34, 136), format=">Q", size=8),
            NumberRegField(consts.RX_CORR_BITS_PM, self.getaddr(0x34, 144), format=">Q", size=8),
            NumberRegField(consts.RX_MIN_CORR_BITS_SUB_INTERVAL_PM, self.getaddr(0x34, 152), format=">Q", size=8),
            NumberRegField(consts.RX_MAX_CORR_BITS_SUB_INTERVAL_PM, self.getaddr(0x34, 160), format=">Q", size=8),
            NumberRegField(consts.RX_FRAMES_PM, self.getaddr(0x34, 168), format=">I", size=4),
            NumberRegField(consts.RX_FRAMES_SUB_INTERVAL_PM, self.getaddr(0x34, 172), format=">I", size=4),
            NumberRegField(consts.RX_FRAMES_UNCORR_ERR_PM, self.getaddr(0x34, 176), format=">I", size=4),
            NumberRegField(consts.RX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM, self.getaddr(0x34, 180), format=">I", size=4),
            NumberRegField(consts.RX_MAX_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM, self.getaddr(0x34, 184), format=">I", size=4),
        )

        # MEDIA_LANE_LINK_PM block corresponds to all the coherent PMs in C-CMIS spec reported in Page 35h.
        self.MEDIA_LANE_LINK_PM = RegGroupField(consts.MEDIA_LANE_LINK_PM,
            NumberRegField(consts.RX_AVG_CD_PM, self.getaddr(0x35, 128), format=">i", size=4),
            NumberRegField(consts.RX_MIN_CD_PM, self.getaddr(0x35, 132), format=">i", size=4),
            NumberRegField(consts.RX_MAX_CD_PM, self.getaddr(0x35, 136), format=">i", size=4),
            NumberRegField(consts.RX_AVG_DGD_PM, self.getaddr(0x35, 140), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_MIN_DGD_PM, self.getaddr(0x35, 142), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_MAX_DGD_PM, self.getaddr(0x35, 144), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_SOPMD_PM, self.getaddr(0x35, 146), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_MIN_SOPMD_PM, self.getaddr(0x35, 148), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_MAX_SOPMD_PM, self.getaddr(0x35, 150), format=">H", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_PDL_PM, self.getaddr(0x35, 152), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MIN_PDL_PM, self.getaddr(0x35, 154), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MAX_PDL_PM, self.getaddr(0x35, 156), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_AVG_OSNR_PM, self.getaddr(0x35, 158), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MIN_OSNR_PM, self.getaddr(0x35, 160), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MAX_OSNR_PM, self.getaddr(0x35, 162), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_AVG_ESNR_PM, self.getaddr(0x35, 164), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MIN_ESNR_PM, self.getaddr(0x35, 166), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MAX_ESNR_PM, self.getaddr(0x35, 168), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_AVG_CFO_PM, self.getaddr(0x35, 170), format=">h", size=2),
            NumberRegField(consts.RX_MIN_CFO_PM, self.getaddr(0x35, 172), format=">h", size=2),
            NumberRegField(consts.RX_MAX_CFO_PM, self.getaddr(0x35, 174), format=">h", size=2),
            NumberRegField(consts.RX_AVG_EVM_PM, self.getaddr(0x35, 176), format=">H", size=2, scale=655.35),
            NumberRegField(consts.RX_MIN_EVM_PM, self.getaddr(0x35, 178), format=">H", size=2, scale=655.35),
            NumberRegField(consts.RX_MAX_EVM_PM, self.getaddr(0x35, 180), format=">H", size=2, scale=655.35),
            NumberRegField(consts.TX_AVG_POWER_PM, self.getaddr(0x35,182), format=">h", size=2, scale=100.0),
            NumberRegField(consts.TX_MIN_POWER_PM, self.getaddr(0x35,184), format=">h", size=2, scale=100.0),
            NumberRegField(consts.TX_MAX_POWER_PM, self.getaddr(0x35,186), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_POWER_PM, self.getaddr(0x35,188), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_MIN_POWER_PM, self.getaddr(0x35,190), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_MAX_POWER_PM, self.getaddr(0x35,192), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_SIG_POWER_PM, self.getaddr(0x35,194), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_MIN_SIG_POWER_PM, self.getaddr(0x35,196), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_MAX_SIG_POWER_PM, self.getaddr(0x35,198), format=">h", size=2, scale=100.0),
            NumberRegField(consts.RX_AVG_SOPROC_PM, self.getaddr(0x35,200), format=">H", size=2),
            NumberRegField(consts.RX_MIN_SOPROC_PM, self.getaddr(0x35,202), format=">H", size=2),
            NumberRegField(consts.RX_MAX_SOPROC_PM, self.getaddr(0x35,204), format=">H", size=2),
            NumberRegField(consts.RX_AVG_MER_PM, self.getaddr(0x35,206), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MIN_MER_PM, self.getaddr(0x35,208), format=">H", size=2, scale=10.0),
            NumberRegField(consts.RX_MAX_MER_PM, self.getaddr(0x35,210), format=">H", size=2, scale=10.0),
            # TODO: add others PMs...
        )
