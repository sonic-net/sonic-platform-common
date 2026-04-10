"""
    pg_02_thresholds.py

    CMIS Page 02h - Thresholds Page
"""

from .base import CmisPage
from .cmis_page_consts import THRESHOLDS_PAGE
from ....fields.xcvr_field import NumberRegField
from ....fields import consts


class CmisThresholdsPage(CmisPage):
    def __init__(self, codes, bank=0):
        super().__init__(codes, page=THRESHOLDS_PAGE, bank=bank)

        # THRESHOLDS_FIELD
        self.fields[consts.THRESHOLDS_FIELD] = [
            NumberRegField(consts.TEMP_HIGH_ALARM_FIELD, self.getaddr(128), size=2, format=">h", scale=256.0),
            NumberRegField(consts.TEMP_LOW_ALARM_FIELD, self.getaddr(130), size=2, format=">h", scale=256.0),
            NumberRegField(consts.TEMP_HIGH_WARNING_FIELD, self.getaddr(132), size=2, format=">h", scale=256.0),
            NumberRegField(consts.TEMP_LOW_WARNING_FIELD, self.getaddr(134), size=2, format=">h", scale=256.0),
            NumberRegField(consts.VOLTAGE_HIGH_ALARM_FIELD, self.getaddr(136), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.VOLTAGE_LOW_ALARM_FIELD, self.getaddr(138), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.VOLTAGE_HIGH_WARNING_FIELD, self.getaddr(140), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.VOLTAGE_LOW_WARNING_FIELD, self.getaddr(142), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.TX_POWER_HIGH_ALARM_FIELD, self.getaddr(176), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.TX_POWER_LOW_ALARM_FIELD, self.getaddr(178), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.TX_POWER_HIGH_WARNING_FIELD, self.getaddr(180), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.TX_POWER_LOW_WARNING_FIELD, self.getaddr(182), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.TX_BIAS_HIGH_ALARM_FIELD, self.getaddr(184), size=2, format=">H", scale=500.0),
            NumberRegField(consts.TX_BIAS_LOW_ALARM_FIELD, self.getaddr(186), size=2, format=">H", scale=500.0),
            NumberRegField(consts.TX_BIAS_HIGH_WARNING_FIELD, self.getaddr(188), size=2, format=">H", scale=500.0),
            NumberRegField(consts.TX_BIAS_LOW_WARNING_FIELD, self.getaddr(190), size=2, format=">H", scale=500.0),
            NumberRegField(consts.RX_POWER_HIGH_ALARM_FIELD, self.getaddr(192), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.RX_POWER_LOW_ALARM_FIELD, self.getaddr(194), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.RX_POWER_HIGH_WARNING_FIELD, self.getaddr(196), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.RX_POWER_LOW_WARNING_FIELD, self.getaddr(198), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.AUX1_HIGH_ALARM, self.getaddr(144), format=">h", size=2),
            NumberRegField(consts.AUX1_LOW_ALARM, self.getaddr(146), format=">h", size=2),
            NumberRegField(consts.AUX1_HIGH_WARN, self.getaddr(148), format=">h", size=2),
            NumberRegField(consts.AUX1_LOW_WARN, self.getaddr(150), format=">h", size=2),
            NumberRegField(consts.AUX2_HIGH_ALARM, self.getaddr(152), format=">h", size=2),
            NumberRegField(consts.AUX2_LOW_ALARM, self.getaddr(154), format=">h", size=2),
            NumberRegField(consts.AUX2_HIGH_WARN, self.getaddr(156), format=">h", size=2),
            NumberRegField(consts.AUX2_LOW_WARN, self.getaddr(158), format=">h", size=2),
            NumberRegField(consts.AUX3_HIGH_ALARM, self.getaddr(160), format=">h", size=2),
            NumberRegField(consts.AUX3_LOW_ALARM, self.getaddr(162), format=">h", size=2),
            NumberRegField(consts.AUX3_HIGH_WARN, self.getaddr(164), format=">h", size=2),
            NumberRegField(consts.AUX3_LOW_WARN, self.getaddr(166), format=">h", size=2),
        ]
