"""
    pg_10_lane_datapath_config.py

    CMIS Page 10h - Lane Datapath Configuration Page
"""

from .base import CmisPage
from .cmis_page_consts import LANE_DATAPATH_CONFIG_PAGE
from ....fields.xcvr_field import (
    NumberRegField,
    RegBitField,
    RegBitsField,
)
from ....fields import consts


class CmisLaneDatapathConfigPage(CmisPage):
    def __init__(self, codes, bank=0):
        super().__init__(codes, page=LANE_DATAPATH_CONFIG_PAGE, bank=bank)

        # LANE_DATAPATH_CTRL_FIELD
        self.fields[consts.LANE_DATAPATH_CTRL_FIELD] = [
            NumberRegField(consts.DATAPATH_DEINIT_FIELD, self.getaddr(128), ro=False),
            NumberRegField(consts.TX_DISABLE_FIELD, self.getaddr(130), ro=False),
            NumberRegField(consts.RX_DISABLE_FIELD, self.getaddr(138), ro=False,
                *(RegBitField("%s_%d" % (consts.RX_DISABLE_FIELD, channel), bitpos, ro=False)
                  for channel, bitpos in zip(range(1, 9), range(0, 8)))  # 8 channels
            )
        ]
        # STAGED_CTRL_FIELD (STAGED_CTRL0)
        self.fields["%s_%d" % (consts.STAGED_CTRL_FIELD, 0)] = [
            NumberRegField("%s_%d" % (consts.STAGED_CTRL_APPLY_DPINIT_FIELD, 0),
                self.getaddr(143), ro=False),
            NumberRegField("%s_%d" % (consts.STAGED_CTRL_APPLY_IMMEDIATE_FIELD, 0),
                self.getaddr(144), ro=False),
            *(NumberRegField("%s_%d_%d" % (consts.STAGED_CTRL_APSEL_FIELD, 0, lane),
                self.getaddr(144 + lane), ro=False)
                for lane in range(1, 9))
        ]

        # STAGED_CTRL0_TX_RX_CTRL_FIELD
        self.fields[consts.STAGED_CTRL0_TX_RX_CTRL_FIELD] = [
            NumberRegField(consts.ADAPTIVE_INPUT_EQ_ENABLE_TX, self.getaddr(153),
                *(RegBitsField(consts.ADAPTIVE_INPUT_EQ_ENABLE_TX + str(lane), bitpos=(lane-1), ro=False, size=1)
                for lane in range(1, 9))
            ),
            NumberRegField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX1_4, self.getaddr(154),
                RegBitsField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX1, bitpos=0, ro=False, size=2),
                RegBitsField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX2, bitpos=2, ro=False, size=2),
                RegBitsField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX3, bitpos=4, ro=False, size=2),
                RegBitsField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX4, bitpos=6, ro=False, size=2),
            ),
            NumberRegField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX5_8, self.getaddr(155),
                RegBitsField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX5, bitpos=0, ro=False, size=2),
                RegBitsField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX6, bitpos=2, ro=False, size=2),
                RegBitsField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX7, bitpos=4, ro=False, size=2),
                RegBitsField(consts.ADAPTIVE_INPUT_EQ_RECALLED_TX8, bitpos=6, ro=False, size=2),
            ),
            NumberRegField(consts.FIXED_INPUT_EQ_TARGET_TX1_2, self.getaddr(156),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX1, bitpos=0, ro=False, size=4),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX2, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.FIXED_INPUT_EQ_TARGET_TX3_4, self.getaddr(157),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX3, bitpos=0, ro=False, size=4),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX4, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.FIXED_INPUT_EQ_TARGET_TX5_6, self.getaddr(158),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX5, bitpos=0, ro=False, size=4),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX6, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.FIXED_INPUT_EQ_TARGET_TX7_8, self.getaddr(159),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX7, bitpos=0, ro=False, size=4),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX8, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.CDR_ENABLE_TX, self.getaddr(160),
                *(RegBitsField(consts.CDR_ENABLE_TX + str(lane), bitpos=(lane-1), ro=False, size=1)
                for lane in range(1, 9))
            ),
            NumberRegField(consts.CDR_ENABLE_RX, self.getaddr(161),
                *(RegBitsField(consts.CDR_ENABLE_RX + str(lane), bitpos=(lane-1), ro=False, size=1)
                for lane in range(1, 9))
            ),
            NumberRegField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX1_2, self.getaddr(162),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX1, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX2, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX3_4, self.getaddr(163),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX3, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX4, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX5_6, self.getaddr(164),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX5, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX6, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX7_8, self.getaddr(165),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX7, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX8, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX1_2, self.getaddr(166),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX1, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX2, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX3_4, self.getaddr(167),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX3, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX4, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX5_6, self.getaddr(168),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX5, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX6, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX7_8, self.getaddr(169),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX7, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX8, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_AMPLITUDE_TARGET_RX1_2, self.getaddr(170),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX1, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX2, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_AMPLITUDE_TARGET_RX3_4, self.getaddr(171),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX3, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX4, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_AMPLITUDE_TARGET_RX5_6, self.getaddr(172),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX5, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX6, bitpos=4, ro=False, size=4)
            ),
            NumberRegField(consts.OUTPUT_AMPLITUDE_TARGET_RX7_8, self.getaddr(173),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX7, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX8, bitpos=4, ro=False, size=4)
            ),
        ]

