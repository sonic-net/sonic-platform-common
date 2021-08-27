"""
    cmis.py

    Implementation of XcvrMemMap for CMIS Rev 5.0
"""

from ..xcvr_mem_map import XcvrMemMap
from ...fields.xcvr_field import (
    CodeRegField,
    HexRegField,
    NumberRegField,
    RegBitField,
    RegGroupField,
    StringRegField,
)
from ...fields import consts
from ...fields.public.cmis import CableLenField

class CmisMemMap(XcvrMemMap):
    def __init__(self, codes):
        super(CmisMemMap, self).__init__(codes)

        self.MGMT_CHARACTERISTICS = RegGroupField(consts.MGMT_CHAR_FIELD,
            NumberRegField(consts.MGMT_CHAR_MISC_FIELD, self.get_addr(0x0, 2),
                RegBitField(consts.FLAT_MEM_FIELD, 7)
            )
        )

        self.MEDIA_TYPE = CodeRegField(consts.MEDIA_TYPE_FIELD, self.get_addr(0x0, 85), self.codes.MEDIA_TYPES)

        self.ADMIN_INFO = RegGroupField(consts.ADMIN_INFO_FIELD,
            CodeRegField(consts.ID_FIELD, self.get_addr(0x0, 128), self.codes.XCVR_IDENTIFIERS),
            CodeRegField(consts.ID_ABBRV_FIELD, self.get_addr(0x0, 128), self.codes.XCVR_IDENTIFIER_ABBRV),
            StringRegField(consts.VENDOR_NAME_FIELD, self.get_addr(0x0, 129), size=16),
            HexRegField(consts.VENDOR_OUI_FIELD, self.get_addr(0x0, 145), size=3),
            StringRegField(consts.VENDOR_PART_NO_FIELD, self.get_addr(0x0, 148), size=16),
            StringRegField(consts.VENDOR_REV_FIELD, self.get_addr(0x0, 164), size=2),
            StringRegField(consts.VENDOR_SERIAL_NO_FIELD, self.get_addr(0x0, 166), size=16),
            StringRegField(consts.VENDOR_DATE_FIELD, self.get_addr(0x0, 182), size=8),
            RegGroupField(consts.EXT_ID_FIELD,
                CodeRegField(consts.POWER_CLASS_FIELD, self.get_addr(0x0, 200), self.codes.POWER_CLASSES,
                    *(RegBitField("%s_%d" % (consts.POWER_CLASS_FIELD, bit), bit) for bit in range(5, 8))
                ),
                NumberRegField(consts.MAX_POWER_FIELD, self.get_addr(0x0, 201), scale=4),
            ),
            NumberRegField(consts.LEN_MULT_FIELD, self.get_addr(0x0, 202),
                *(RegBitField("%s_%d" % (consts.LEN_MULT_FIELD, bit), bit) for bit in range (6, 8))
            ),
            CableLenField(consts.LENGTH_ASSEMBLY_FIELD, self.get_addr(0x0, 202), deps=[consts.LEN_MULT_FIELD]),
            CodeRegField(consts.CONNECTOR_FIELD, self.get_addr(0x0, 203), self.codes.CONNECTORS),
        )

        self.MODULE_LEVEL_MONITORS = RegGroupField(consts.MODULE_MONITORS_FIELD,
            NumberRegField(consts.TEMPERATURE_FIELD, self.get_addr(0x0, 14), size=2, format=">h", scale=256),
            NumberRegField(consts.VOLTAGE_FIELD, self.get_addr(0x0, 16), size=2, format=">H", scale=1000),
        )

        self.MODULE_CHAR_ADVT = RegGroupField(consts.MODULE_CHAR_ADVT_FIELD,
            NumberRegField(consts.CTRLS_ADVT_FIELD, self.get_addr(0x1, 155),
                RegBitField(consts.TX_DISABLE_SUPPORT_FIELD, 1),
                size=2, format="<H"
            ),
            NumberRegField(consts.FLAGS_ADVT_FIELD, self.get_addr(0x1, 157),
                RegBitField(consts.TX_FAULT_SUPPORT_FIELD, 0),
                size=2, format="<H"
            )
        )

        self.THRESHOLDS = RegGroupField(consts.THRESHOLDS_FIELD,
            NumberRegField(consts.TEMP_HIGH_ALARM_FIELD, self.get_addr(0x2, 128), size=2, format=">h", scale=256),
            NumberRegField(consts.TEMP_LOW_ALARM_FIELD, self.get_addr(0x2, 130), size=2, format=">h", scale=256),
            NumberRegField(consts.TEMP_HIGH_WARNING_FIELD, self.get_addr(0x2, 132), size=2, format=">h", scale=256),
            NumberRegField(consts.TEMP_LOW_WARNING_FIELD, self.get_addr(0x2, 134), size=2, format=">h", scale=256),
            NumberRegField(consts.VOLTAGE_HIGH_ALARM_FIELD, self.get_addr(0x2, 136), size=2, format=">H", scale=1000),
            NumberRegField(consts.VOLTAGE_LOW_ALARM_FIELD, self.get_addr(0x2, 138), size=2, format=">H", scale=1000),
            NumberRegField(consts.VOLTAGE_HIGH_WARNING_FIELD, self.get_addr(0x2, 140), size=2, format=">H", scale=1000),
            NumberRegField(consts.VOLTAGE_LOW_WARNING_FIELD, self.get_addr(0x2, 142), size=2, format=">H", scale=1000),
            NumberRegField(consts.TX_POWER_HIGH_ALARM_FIELD, self.get_addr(0x2, 176), size=2, format=">H", scale=1000),
            NumberRegField(consts.TX_POWER_LOW_ALARM_FIELD, self.get_addr(0x2, 178), size=2, format=">H", scale=1000),
            NumberRegField(consts.TX_POWER_HIGH_WARNING_FIELD, self.get_addr(0x2, 180), size=2, format=">H", scale=1000),
            NumberRegField(consts.TX_POWER_LOW_WARNING_FIELD, self.get_addr(0x2, 182), size=2, format=">H", scale=1000),
            NumberRegField(consts.TX_BIAS_HIGH_ALARM_FIELD, self.get_addr(0x2, 184), size=2, format=">H", scale=500),
            NumberRegField(consts.TX_BIAS_LOW_ALARM_FIELD, self.get_addr(0x2, 186), size=2, format=">H", scale=500),
            NumberRegField(consts.TX_BIAS_HIGH_WARNING_FIELD, self.get_addr(0x2, 188), size=2, format=">H", scale=500),
            NumberRegField(consts.TX_BIAS_LOW_WARNING_FIELD, self.get_addr(0x2, 190), size=2, format=">H", scale=500),
            NumberRegField(consts.RX_POWER_HIGH_ALARM_FIELD, self.get_addr(0x2, 192), size=2, format=">H", scale=1000),
            NumberRegField(consts.RX_POWER_LOW_ALARM_FIELD, self.get_addr(0x2, 194), size=2, format=">H", scale=1000),
            NumberRegField(consts.RX_POWER_HIGH_WARNING_FIELD, self.get_addr(0x2, 196), size=2, format=">H", scale=1000),
            NumberRegField(consts.RX_POWER_LOW_WARNING_FIELD, self.get_addr(0x2, 198), size=2, format=">H", scale=1000),
        )

        self.LANE_DATAPATH_CTRL = RegGroupField(consts.LANE_DATAPATH_CTRL_FIELD,
            NumberRegField(consts.TX_DISABLE_FIELD, self.get_addr(0x10, 130), ro=False)
        )

        self.LANE_DATAPATH_STATUS = RegGroupField(consts.LANE_DATAPATH_STATUS_FIELD,
            NumberRegField(consts.TX_FAULT_FIELD, self.get_addr(0x11, 135)),
            NumberRegField(consts.RX_LOS_FIELD, self.get_addr(0x11, 147)),
            RegGroupField(consts.TX_POWER_FIELD,
                *(NumberRegField("OpticalPowerTx%dField" % channel, self.get_addr(0x11, offset), size=2, format=">H", scale=1000)
                for channel, offset in zip(range(1, 9), range(154, 170, 2)))
            ),
            RegGroupField(consts.TX_BIAS_FIELD,
                *(NumberRegField("LaserBiasTx%dField" % channel, self.get_addr(0x11, offset), size=2, format=">H", scale=500)
                for channel, offset in zip(range(1, 9), range(170, 186, 2)))
            ),
            RegGroupField(consts.RX_POWER_FIELD,
                *(NumberRegField("OpticalPowerRx%dField" % channel, self.get_addr(0x11, offset), size=2, format=">H", scale=1000)
                for channel, offset in zip(range(1, 9), range(186, 202, 2)))
            ),
        )

        self.MEDIA_LANE_FEC_PM = RegGroupField(consts.MEDIA_LANE_FEC_PM_FIELD,
            NumberRegField(consts.RX_BITS_PM_FIELD, self.get_addr(0x34, 128), format=">Q", size=8),
            NumberRegField(consts.RX_BITS_SUB_INT_PM_FIELD, self.get_addr(0x34, 136), format=">Q", size=8),
            # TODO: add other PMs...
        )

        self.MEDIA_LANE_LINK_PM = RegGroupField(consts.MEDIA_LANE_LINK_PM_FIELD,
            NumberRegField(consts.RX_AVG_CD_PM_FIELD, self.get_addr(0x35, 128), format=">i", size=4),
            NumberRegField(consts.RX_MIN_CD_PM_FIELD, self.get_addr(0x35, 132), format=">i", size=4),
            NumberRegField(consts.RX_MAX_CD_PM_FIELD, self.get_addr(0x35, 136), format=">i", size=4),
            NumberRegField(consts.RX_AVG_DGD_PM_FIELD, self.get_addr(0x35, 140), format=">H", size=2, scale=100)
            # TODO: add others PMs...
        )

    def get_addr(self, page, offset, page_size=128):
        return page * page_size + offset
