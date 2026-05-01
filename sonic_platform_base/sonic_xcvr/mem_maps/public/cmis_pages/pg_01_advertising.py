"""
    pg_01_advertising.py

    CMIS Page 01h - Advertising Page
"""

from .base import CmisPage
from .cmis_page_consts import ADVERTISING_PAGE
from ....fields.xcvr_field import (
    CodeRegField,
    NumberRegField,
    RegBitField,
    RegGroupField,
)
from ....fields import consts


class CmisAdvertisingPage(CmisPage):
    def __init__(self, codes):
        super().__init__(codes, page=ADVERTISING_PAGE, bank=0)

        # ADVERTISING_FIELD
        self.fields[consts.ADVERTISING_FIELD] = [
            NumberRegField(consts.INACTIVE_FW_MAJOR_REV, self.getaddr(128), format="B", size=1),
            NumberRegField(consts.INACTIVE_FW_MINOR_REV, self.getaddr(129), format="B", size=1),
            NumberRegField(consts.HW_MAJOR_REV, self.getaddr(130), size=1),
            NumberRegField(consts.HW_MINOR_REV, self.getaddr(131), size=1),
            CodeRegField(consts.DP_PATH_INIT_DURATION, self.getaddr(144), codes.DP_PATH_TIMINGS,
                 *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
            ),
            CodeRegField(consts.DP_PATH_DEINIT_DURATION, self.getaddr(144), codes.DP_PATH_TIMINGS,
                 *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
            ),
            CodeRegField(consts.MODULE_PWRUP_DURATION, self.getaddr(167), codes.DP_PATH_TIMINGS,
                 *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
            ),
            CodeRegField(consts.MODULE_PWRDN_DURATION, self.getaddr(167), codes.DP_PATH_TIMINGS,
                 *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
            ),
            CodeRegField(consts.DP_TX_TURNON_DURATION, self.getaddr(168), codes.DP_PATH_TIMINGS,
                 *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
            ),
            CodeRegField(consts.DP_TX_TURNOFF_DURATION, self.getaddr(168), codes.DP_PATH_TIMINGS,
                 *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
            ),
            NumberRegField(consts.MEDIA_LANE_ASSIGNMENT_OPTION, self.getaddr(176), format="B", size=1),

            RegGroupField(consts.APPLS_ADVT_FIELD_PAGE01,
                *(NumberRegField("%s_%d" % (consts.MEDIA_LANE_ASSIGNMENT_OPTION, app), self.getaddr(176 + (app - 1)),
                    format="B", size=1) for app in range(1, 16)),

                *(CodeRegField("%s_%d" % (consts.HOST_ELECTRICAL_INTERFACE, app), self.getaddr(223 + 4 * (app - 9)),
                    codes.HOST_ELECTRICAL_INTERFACE) for app in range(9, 16)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_850NM, app), self.getaddr(224 + 4 * (app - 9)),
                    codes.NM_850_MEDIA_INTERFACE) for app in range(9, 16)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_SM, app), self.getaddr(224 + 4 * (app - 9)),
                    codes.SM_MEDIA_INTERFACE) for app in range(9, 16)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER, app), self.getaddr(224 + 4 * (app - 9)),
                    codes.PASSIVE_COPPER_MEDIA_INTERFACE) for app in range(9, 16)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE, app), self.getaddr(224 + 4 * (app - 9)),
                    codes.ACTIVE_CABLE_MEDIA_INTERFACE) for app in range(9, 16)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_BASE_T, app), self.getaddr(224 + 4 * (app - 9)),
                    codes.BASE_T_MEDIA_INTERFACE) for app in range(9, 16)),

                *(NumberRegField("%s_%d" % (consts.MEDIA_LANE_COUNT, lane), self.getaddr(225 + 4 * (lane - 9)),
                    *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
                    ) for lane in range(9, 16)),

                *(NumberRegField("%s_%d" % (consts.HOST_LANE_COUNT, lane), self.getaddr(225 + 4 * (lane - 9)),
                    *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
                    ) for lane in range(9, 16)),

                *(NumberRegField("%s_%d" % (consts.HOST_LANE_ASSIGNMENT_OPTION, app), self.getaddr(226 + 4 * (app - 9)),
                    format="B", size=1) for app in range(9, 16))
            )
        ]

        # MODULE_CHAR_ADVT_FIELD
        self.fields[consts.MODULE_CHAR_ADVT_FIELD] = [
            NumberRegField(consts.PAGE_SUPPORT_ADVT_FIELD, self.getaddr(142),
                RegBitField(consts.VDM_SUPPORTED, 6),
                RegBitField(consts.DIAG_PAGE_SUPPORT_ADVT_FIELD, 5),
            ),
            NumberRegField(consts.BANKS_SUPPORTED_FIELD, self.getaddr(142),
                *(RegBitField("Bit%d" % bit, bit) for bit in range(0, 2))
            ),
            NumberRegField(consts.TX_INPUT_EQ_MAX, self.getaddr(153),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (0 , 4))
            ),
            NumberRegField(consts.RX_OUTPUT_LEVEL_SUPPORT, self.getaddr(153),
                RegBitField(consts.RX_OUTPUT_LEVEL_0_SUPPORTED, 4),
                RegBitField(consts.RX_OUTPUT_LEVEL_1_SUPPORTED, 5),
                RegBitField(consts.RX_OUTPUT_LEVEL_2_SUPPORTED, 6),
                RegBitField(consts.RX_OUTPUT_LEVEL_3_SUPPORTED, 7),
            ),
            NumberRegField(consts.RX_OUTPUT_EQ_PRE_CURSOR_MAX, self.getaddr(154),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (0 , 4))
            ),
            NumberRegField(consts.RX_OUTPUT_EQ_POST_CURSOR_MAX, self.getaddr(154),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (4 , 8))
            ),
            NumberRegField(consts.CTRLS_ADVT_FIELD, self.getaddr(155),
                RegBitField(consts.TX_DISABLE_SUPPORT_FIELD, 1),
                size=2, format="<H"
            ),
            NumberRegField(consts.CTRLS_ADVT_FIELD, self.getaddr(156),
                RegBitField(consts.RX_DISABLE_SUPPORT_FIELD, 1),
                size=2, format="<H"
            ),
            NumberRegField(consts.TX_FLAGS_ADVT_FIELD, self.getaddr(157),
                RegBitField(consts.TX_FAULT_SUPPORT_FIELD, 0),
                RegBitField(consts.TX_LOS_SUPPORT_FIELD, 1),
                RegBitField(consts.TX_CDR_LOL_SUPPORT_FIELD, 2),
                RegBitField(consts.TX_ADAPTIVE_INPUT_EQ_FAIL_FLAG_SUPPORTED, 3),
            ),
            NumberRegField(consts.RX_FLAGS_ADVT_FIELD, self.getaddr(158),
                RegBitField(consts.RX_LOS_SUPPORT, 1),
                RegBitField(consts.RX_CDR_LOL_SUPPORT_FIELD, 2),
            ),
            NumberRegField(consts.LANE_MON_ADVT_FIELD, self.getaddr(160),
                RegBitField(consts.RX_POWER_SUPPORT_FIELD, 2),
                RegBitField(consts.TX_POWER_SUPPORT_FIELD, 1),
                RegBitField(consts.TX_BIAS_SUPPORT_FIELD, 0),
            ),
            NumberRegField(consts.TX_BIAS_SCALE, self.getaddr(160),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (3, 5))
            ),
        ]

        # MODULE_MONITORS_FIELD (partial - AUX_MON_TYPE from page 01h)
        self.fields[consts.MODULE_MONITORS_FIELD] = [
            NumberRegField(consts.AUX_MON_TYPE, self.getaddr(145), size=1),
        ]

        # SIGNAL_INTEGRITY_CTRL_ADVT_FIELD
        self.fields[consts.SIGNAL_INTEGRITY_CTRL_ADVT_FIELD] = [
            NumberRegField(consts.TX_SI_CTRL_ADVT, self.getaddr(161),
                RegBitField(consts.TX_CDR_SUPPORT_FIELD, 0),
                RegBitField(consts.TX_CDR_BYPASS_CTRL_FIELD, 1),
                RegBitField(consts.TX_INPUT_EQ_FIXED_MANUAL_CTRL_SUPPORT_FIELD, 2),
                RegBitField(consts.TX_INPUT_ADAPTIVE_EQ_SUPPORT_FIELD, 3),
                RegBitField(consts.TX_INPUT_EQ_FREEZE_SUPPORT_FIELD, 4),
                RegBitField(consts.TX_INPUT_EQ_RECALL_BUF1_SUPPORT_FIELD, 5),
                RegBitField(consts.TX_INPUT_EQ_RECALL_BUF2_SUPPORT_FIELD, 6),
            ),
            NumberRegField(consts.TX_INPUT_EQ_RECALL_BUF_SUPPORT_FIELD, self.getaddr(161),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (5 , 7))
            ),

            NumberRegField(consts.RX_SI_CTRL_ADVT, self.getaddr(162),
                RegBitField(consts.RX_CDR_SUPPORT_FIELD, 0),
                RegBitField(consts.RX_CDR_BYPASS_CTRL_FIELD, 1),
                RegBitField(consts.RX_OUTPUT_AMP_CTRL_SUPPORT_FIELD, 2),
                RegBitField(consts.RX_OUTPUT_EQ_PRE_CTRL_SUPPORT_FIELD, 3),
                RegBitField(consts.RX_OUTPUT_EQ_POST_CTRL_SUPPORT_FIELD, 4),
            ),
            NumberRegField(consts.RX_OUTPUT_EQ_CTRL_SUPPORT_FIELD, self.getaddr(162),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (3 , 5))
            ),
        ]

        # TRANS_CDB_FIELD (partial - page 01 fields only)
        self.fields[consts.TRANS_CDB_FIELD] = [
            NumberRegField(consts.CDB_SUPPORT, self.getaddr(163),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (6, 8))
            ),
            NumberRegField(consts.AUTO_PAGING_SUPPORT, self.getaddr(163),
                (RegBitField("Bit4", 4))
            ),
            NumberRegField(consts.CDB_SEQ_WRITE_LENGTH_EXT, self.getaddr(164), size=1),
        ]

