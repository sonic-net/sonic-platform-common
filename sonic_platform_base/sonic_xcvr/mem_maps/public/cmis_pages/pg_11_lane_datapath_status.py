"""
    pg_11_lane_datapath_status.py

    CMIS Page 11h - Lane Datapath Status Page
"""

from .base import CmisPage
from .cmis_page_consts import LANE_DATAPATH_STATUS_PAGE
from ....fields.xcvr_field import (
    CodeRegField,
    NumberRegField,
    RegBitField,
    RegGroupField,
)
from ....fields import consts


class CmisLaneDatapathStatusPage(CmisPage):
    def __init__(self, codes, bank=0, page=LANE_DATAPATH_STATUS_PAGE):
        super().__init__(codes, page=page, bank=bank)

        # TX_POWER_ALARM_FLAGS_FIELD
        self.fields[consts.TX_POWER_ALARM_FLAGS_FIELD] = [
            RegGroupField(consts.TX_POWER_HIGH_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_POWER_HIGH_ALARM_FLAG, lane), self.getaddr(139),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_LOW_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_POWER_LOW_ALARM_FLAG, lane), self.getaddr(140),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_HIGH_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_POWER_HIGH_WARN_FLAG, lane), self.getaddr(141),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_LOW_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_POWER_LOW_WARN_FLAG, lane), self.getaddr(142),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            )
        ]

        # TX_BIAS_ALARM_FLAGS_FIELD
        self.fields[consts.TX_BIAS_ALARM_FLAGS_FIELD] = [
            RegGroupField(consts.TX_BIAS_HIGH_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_BIAS_HIGH_ALARM_FLAG, lane), self.getaddr(143),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_LOW_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_BIAS_LOW_ALARM_FLAG, lane), self.getaddr(144),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_HIGH_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_BIAS_HIGH_WARN_FLAG, lane), self.getaddr(145),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_LOW_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_BIAS_LOW_WARN_FLAG, lane), self.getaddr(146),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            )
        ]

        # RX_POWER_ALARM_FLAGS_FIELD
        self.fields[consts.RX_POWER_ALARM_FLAGS_FIELD] = [
            RegGroupField(consts.RX_POWER_HIGH_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.RX_POWER_HIGH_ALARM_FLAG, lane), self.getaddr(149),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_LOW_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.RX_POWER_LOW_ALARM_FLAG, lane), self.getaddr(150),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_HIGH_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.RX_POWER_HIGH_WARN_FLAG, lane), self.getaddr(151),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_LOW_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.RX_POWER_LOW_WARN_FLAG, lane), self.getaddr(152),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                ) for lane in range(1, 9))
            )
        ]

        # LANE_DATAPATH_STATUS_FIELD - This is a large field, will be added next
        self.fields[consts.LANE_DATAPATH_STATUS_FIELD] = [
            RegGroupField(consts.TX_FAULT_FIELD,
                *(NumberRegField("%s%d" % (consts.TX_FAULT_FIELD, lane), self.getaddr(135),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_LOS_FIELD,
                *(NumberRegField("%s%d" % (consts.RX_LOS_FIELD, lane), self.getaddr(147),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),

            RegGroupField(consts.TX_POWER_FIELD,
                *(NumberRegField("OpticalPowerTx%dField" % channel, self.getaddr(offset), size=2, format=">H", scale=10000.0)
                for channel, offset in zip(range(1, 9), range(154, 170, 2)))
            ),
            RegGroupField(consts.TX_BIAS_FIELD,
                *(NumberRegField("LaserBiasTx%dField" % channel, self.getaddr(offset), size=2, format=">H", scale=500.0)
                for channel, offset in zip(range(1, 9), range(170, 186, 2)))
            ),
            RegGroupField(consts.RX_POWER_FIELD,
                *(NumberRegField("OpticalPowerRx%dField" % channel, self.getaddr(offset), size=2, format=">H", scale=10000.0)
                for channel, offset in zip(range(1, 9), range(186, 202, 2)))
            ),

            RegGroupField(consts.DATA_PATH_STATE,
                *(CodeRegField("DP%dState" % (lane) , self.getaddr(128 + int((lane-1)/2)), codes.DATAPATH_STATE,
                    *(RegBitField("Bit%d" % bit, bit) for bit in [range(4, 8), range(0, 4)][lane%2]))
                 for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_OUTPUT_STATUS,
                *(NumberRegField("%s%d" % (consts.RX_OUTPUT_STATUS, lane), self.getaddr(132),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_OUTPUT_STATUS,
                *(NumberRegField("%s%d" % (consts.TX_OUTPUT_STATUS, lane), self.getaddr(133),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_LOS_FIELD,
                *(NumberRegField("%s%d" % (consts.TX_LOS_FIELD, lane), self.getaddr(136),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_CDR_LOL,
                *(NumberRegField("%s%d" % (consts.TX_CDR_LOL, lane), self.getaddr(137),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_ADAPTIVE_INPUT_EQ_FAIL_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_ADAPTIVE_INPUT_EQ_FAIL_FLAG, lane), self.getaddr(138),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_HIGH_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_POWER_HIGH_ALARM_FLAG, lane), self.getaddr(139),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_LOW_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_POWER_LOW_ALARM_FLAG, lane), self.getaddr(140),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_HIGH_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_POWER_HIGH_WARN_FLAG, lane), self.getaddr(141),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_LOW_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_POWER_LOW_WARN_FLAG, lane), self.getaddr(142),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_HIGH_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_BIAS_HIGH_ALARM_FLAG, lane), self.getaddr(143),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_LOW_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_BIAS_LOW_ALARM_FLAG, lane), self.getaddr(144),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_HIGH_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_BIAS_HIGH_WARN_FLAG, lane), self.getaddr(145),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_LOW_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.TX_BIAS_LOW_WARN_FLAG, lane), self.getaddr(146),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_CDR_LOL,
                *(NumberRegField("%s%d" % (consts.RX_CDR_LOL, lane), self.getaddr(148),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_HIGH_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.RX_POWER_HIGH_ALARM_FLAG, lane), self.getaddr(149),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_LOW_ALARM_FLAG,
                *(NumberRegField("%s%d" % (consts.RX_POWER_LOW_ALARM_FLAG, lane), self.getaddr(150),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_HIGH_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.RX_POWER_HIGH_WARN_FLAG, lane), self.getaddr(151),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_LOW_WARN_FLAG,
                *(NumberRegField("%s%d" % (consts.RX_POWER_LOW_WARN_FLAG, lane), self.getaddr(152),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
            RegGroupField(consts.CONFIG_LANE_STATUS,
                *(CodeRegField("%s%d" % (consts.CONFIG_LANE_STATUS, lane) , self.getaddr(202 + int((lane-1)/2)), codes.CONFIG_STATUS,
                    *(RegBitField("Bit%d" % bit, bit) for bit in [range(4, 8), range(0, 4)][lane%2]))
                 for lane in range(1, 9))
            ),
            RegGroupField(consts.DPINIT_PENDING,
                *(NumberRegField("%s%d" % (consts.DPINIT_PENDING, lane), self.getaddr(235),
                    RegBitField("Bit%d" % (lane-1), (lane-1))
                )
                for lane in range(1, 9))
            ),
        ]

        # ADVERTISING_FIELD (partial - ACTIVE_APSEL_CODE from page 11h)
        self.fields[consts.ADVERTISING_FIELD] = [
            RegGroupField(consts.ACTIVE_APSEL_CODE,
                *(NumberRegField("%s%d" % (consts.ACTIVE_APSEL_HOSTLANE, lane) , self.getaddr(offset),
                    *(RegBitField("Bit%d" % bit, bit) for bit in range(4, 8)))
                 for lane, offset in zip(range(1, 9), range(206, 214)))
            ),
        ]

