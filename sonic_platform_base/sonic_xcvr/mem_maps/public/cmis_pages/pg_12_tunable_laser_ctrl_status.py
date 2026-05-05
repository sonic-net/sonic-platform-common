"""
    pg_12_tunable_laser_ctrl_status.py

    CMIS Page 12h - Tunable Laser Control and Status Page
"""

from .base import CmisPage
from .cmis_page_consts import TUNABLE_LASER_CTRL_STATUS_PAGE
from ....fields.xcvr_field import (
    NumberRegField,
    RegBitField,
)
from ....fields import consts


class CmisTunableLaserCtrlStatusPage(CmisPage):
    def __init__(self, codes, bank=0, page=TUNABLE_LASER_CTRL_STATUS_PAGE):
        super().__init__(codes, page=page, bank=bank)

        # MODULE_MONITORS_FIELD
        self.fields[consts.MODULE_MONITORS_FIELD] = [
            NumberRegField(consts.GRID_SPACING, self.getaddr(128),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8)), ro = False
            ),
            NumberRegField(consts.LASER_CONFIG_CHANNEL, self.getaddr(136), format=">h", size=2, ro=False),
            NumberRegField(consts.LASER_CURRENT_FREQ, self.getaddr(168), format=">L", size=4, scale = 1000.0),
            NumberRegField(consts.TX_CONFIG_POWER, self.getaddr(200), format=">h", size=2, scale=100.0, ro=False),
        ]

        # LANE_DATAPATH_STATUS_FIELD (partial - laser tuning fields from page 12h)
        self.fields[consts.LANE_DATAPATH_STATUS_FIELD] = [
            RegBitField(consts.TUNING_IN_PROGRESS, offset=self.getaddr(222), bitpos=1),
            RegBitField(consts.WAVELENGTH_UNLOCKED, offset=self.getaddr(222), bitpos=0),
            NumberRegField(consts.LASER_TUNING_DETAIL, self.getaddr(231), size=1),
        ]
