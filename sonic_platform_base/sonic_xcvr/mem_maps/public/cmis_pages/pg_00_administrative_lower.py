"""
    pg_00_administrative_lower.py

    Implementation of CmisAdministrativeLowerPage for CMIS page 0x00 lower memory (offsets 0-127)
"""

from .base import CmisPage
from .cmis_page_consts import ADMINISTRATIVE_PAGE
from ....fields.xcvr_field import (
    CodeRegField,
    NumberRegField,
    RegBitField,
)
from ....fields import consts


class CmisAdministrativeLowerPage(CmisPage):
    def __init__(self, codes, page=ADMINISTRATIVE_PAGE):
        super().__init__(codes, page=page, bank=0)

        # MGMT_CHAR_FIELD
        self.fields[consts.MGMT_CHAR_FIELD] = [
            NumberRegField(consts.MGMT_CHAR_MISC_FIELD, self.getaddr(2),
                RegBitField(consts.FLAT_MEM_FIELD, 7)
            )
        ]

        # ADMIN_INFO_FIELD - includes individual media interface fields
        self.fields[consts.ADMIN_INFO_FIELD] = [
            CodeRegField(consts.ID_FIELD, self.getaddr(0), codes.XCVR_IDENTIFIERS),
            CodeRegField(consts.MEDIA_TYPE_FIELD, self.getaddr(85), codes.MODULE_MEDIA_TYPE),
            CodeRegField(consts.HOST_ELECTRICAL_INTERFACE, self.getaddr(86), codes.HOST_ELECTRICAL_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_850NM, self.getaddr(87), codes.NM_850_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_SM, self.getaddr(87), codes.SM_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER, self.getaddr(87), codes.PASSIVE_COPPER_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE, self.getaddr(87), codes.ACTIVE_CABLE_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_BASE_T, self.getaddr(87), codes.BASE_T_MEDIA_INTERFACE),
            NumberRegField(consts.MEDIA_LANE_COUNT, self.getaddr(88),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
            ),
            NumberRegField(consts.HOST_LANE_COUNT, self.getaddr(88),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
            ),
            NumberRegField(consts.HOST_LANE_ASSIGNMENT_OPTION, self.getaddr(89), format="B", size=1),
            NumberRegField(consts.CMIS_MAJOR_REVISION, self.getaddr(1),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
            ),
            NumberRegField(consts.CMIS_MINOR_REVISION, self.getaddr(1),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
            ),
            NumberRegField(consts.ACTIVE_FW_MAJOR_REV, self.getaddr(39), format="B", size=1),
            NumberRegField(consts.ACTIVE_FW_MINOR_REV, self.getaddr(40), format="B", size=1),
        ]

        # APPLS_ADVT_FIELD - application advertisements from lower page
        self.fields[consts.APPLS_ADVT_FIELD] = [
            *(CodeRegField("%s_%d" % (consts.HOST_ELECTRICAL_INTERFACE, app), self.getaddr(86 + 4 * (app - 1)),
                codes.HOST_ELECTRICAL_INTERFACE) for app in range(1, 9)),

            *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_850NM, app), self.getaddr(87 + 4 * (app- 1)),
                codes.NM_850_MEDIA_INTERFACE) for app in range(1, 9)),

            *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_SM, app), self.getaddr(87 + 4 * (app - 1)),
                codes.SM_MEDIA_INTERFACE) for app in range(1, 9)),

            *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER, app), self.getaddr(87 + 4 * (app - 1)),
                codes.PASSIVE_COPPER_MEDIA_INTERFACE) for app in range(1, 9)),

            *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE, app), self.getaddr(87 + 4 * (app - 1)),
                codes.ACTIVE_CABLE_MEDIA_INTERFACE) for app in range(1, 9)),

            *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_BASE_T, app), self.getaddr(87 + 4 * (app - 1)),
                codes.BASE_T_MEDIA_INTERFACE) for app in range(1, 9)),

            *(NumberRegField("%s_%d" % (consts.MEDIA_LANE_COUNT, lane), self.getaddr(88 + 4 * (lane - 1)),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
                ) for lane in range(1, 9)),

            *(NumberRegField("%s_%d" % (consts.HOST_LANE_COUNT, lane), self.getaddr(88 + 4 * (lane - 1)),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
                ) for lane in range(1, 9)),

            *(NumberRegField("%s_%d" % (consts.HOST_LANE_ASSIGNMENT_OPTION, lane), self.getaddr(89 + 4 * (lane - 1)),
                format="B", size=1) for lane in range(1, 9)),
        ]

        # MODULE_MONITORS_PAGE0_FIELD
        self.fields[consts.MODULE_MONITORS_PAGE0_FIELD] = [
            NumberRegField(consts.TEMPERATURE_FIELD, self.getaddr(14), size=2, format=">h", scale=256.0),
            NumberRegField(consts.VOLTAGE_FIELD, self.getaddr(16), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.AUX1_MON, self.getaddr(18), format=">h", size=2),
            NumberRegField(consts.AUX2_MON, self.getaddr(20), format=">h", size=2),
            NumberRegField(consts.AUX3_MON, self.getaddr(22), format=">h", size=2),
            NumberRegField(consts.CUSTOM_MON, self.getaddr(24), format=">H", size=2),
        ]

        # TRANS_MODULE_STATUS_FIELD
        self.fields[consts.TRANS_MODULE_STATUS_FIELD] = [
            CodeRegField(consts.MODULE_STATE, self.getaddr(3), codes.MODULE_STATE,
                 *(RegBitField("Bit%d" % (bit), bit) for bit in range (1, 4))
            ),
            NumberRegField(consts.MODULE_FIRMWARE_FAULT_INFO, self.getaddr(8), size=1),
            NumberRegField(consts.MODULE_FLAG_BYTE1, self.getaddr(9), size=1),
            NumberRegField(consts.MODULE_FLAG_BYTE2, self.getaddr(10), size=1),
            NumberRegField(consts.MODULE_FLAG_BYTE3, self.getaddr(11), size=1),
            NumberRegField(consts.CDB1_STATUS, self.getaddr(37), size=1),
            CodeRegField(consts.MODULE_FAULT_CAUSE, self.getaddr(41), codes.MODULE_FAULT_CAUSE),
        ]

        # TRANS_CONFIG_FIELD
        self.fields[consts.TRANS_CONFIG_FIELD] = [
            NumberRegField(consts.MODULE_LEVEL_CONTROL, self.getaddr(26), size=1, ro=False),
        ]

