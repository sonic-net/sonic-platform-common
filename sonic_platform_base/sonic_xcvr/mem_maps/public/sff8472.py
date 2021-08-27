"""
    sff8472.py

    Implementation of XcvrMemMap for SFF-8472 Rev 12.3
"""

from ..xcvr_mem_map import XcvrMemMap
from ...fields.xcvr_field import (
    CodeRegField,
    DateField,
    HexRegField,
    NumberRegField,
    RegBitField,
    RegGroupField,
    StringRegField,
)
from ...fields import consts
from ...fields.public.sff8472 import (
    RxPowerField,
    TempField,
    TxBiasField,
    TxPowerField,
    VoltageField,
)

class Sff8472MemMap(XcvrMemMap):
    def __init__(self, codes):
        super(Sff8472MemMap, self).__init__(codes)

        self.SERIAL_ID = RegGroupField(consts.SERIAL_ID_FIELD,
            CodeRegField(consts.ID_FIELD, self.get_addr(0xA0, None, 0), self.codes.XCVR_IDENTIFIERS),
            CodeRegField(consts.ID_ABBRV_FIELD, self.get_addr(0xA0, None, 0), self.codes.XCVR_IDENTIFIER_ABBRV),
            CodeRegField(consts.EXT_ID_FIELD, self.get_addr(0xA0, None, 1), self.codes.EXT_IDENTIFIERS),
            CodeRegField(consts.CONNECTOR_FIELD, self.get_addr(0xA0, None, 2), self.codes.CONNECTORS),
            RegGroupField(consts.SPEC_COMPLIANCE_FIELD, 
                CodeRegField(consts.ETHERNET_10G_COMPLIANCE_FIELD, self.get_addr(0xA0, None, 3), self.codes.ETHERNET_10G_COMPLIANCE,
                    *(RegBitField("%s_%d" % (consts.ETHERNET_10G_COMPLIANCE_FIELD, bit), bit) for bit in range(4, 8))
                ),
                CodeRegField(consts.INFINIBAND_COMPLIANCE_FIELD, self.get_addr(0xA0, None, 3), self.codes.INFINIBAND_COMPLIANCE,
                    *(RegBitField("%s_%d" % (consts.INFINIBAND_COMPLIANCE_FIELD, bit), bit) for bit in range(0, 4))
                ),
                CodeRegField(consts.ESCON_COMPLIANCE_FIELD, self.get_addr(0xA0, None, 4), self.codes.ESCON_COMPLIANCE,
                    *(RegBitField("%s_%d" % (consts.ESCON_COMPLIANCE_FIELD, bit), bit) for bit in range(6, 8))
                ),
                CodeRegField(consts.SONET_COMPLIANCE_FIELD, self.get_addr(0xA0, None, 4), self.codes.SONET_COMPLIANCE,
                    *(RegBitField("%s_%d" % (consts.SONET_COMPLIANCE_FIELD, bit), bit) for bit in range(0, 14)),
                    size=2, format=">H"
                ),
                CodeRegField(consts.ETHERNET_COMPLIANCE_FIELD, self.get_addr(0xA0, None, 6), self.codes.ETHERNET_COMPLIANCE),
                CodeRegField(consts.FIBRE_CHANNEL_LINK_LENGTH_FIELD, self.get_addr(0xA0, None, 7), self.codes.FIBRE_CHANNEL_LINK_LENGTH,
                    *(RegBitField("%s_%d" % (consts.FIBRE_CHANNEL_LINK_LENGTH_FIELD, bit), bit) for bit in range(3, 8))
                ),
                CodeRegField(consts.FIBRE_CHANNEL_TRANSMITTER_TECH_FIELD, self.get_addr(0xA0, None, 7), self.codes.FIBRE_CHANNEL_TRANSMITTER_TECH,
                    *(RegBitField("%s_%d" % (consts.FIBRE_CHANNEL_TRANSMITTER_TECH_FIELD, bit), bit) for bit in range(4, 11)),
                    size=2, format=">H"
                ),
                CodeRegField(consts.SFP_CABLE_TECH_FIELD, self.get_addr(0xA0, None, 8), self.codes.SFP_CABLE_TECH,
                    *(RegBitField("%s_%d" % (consts.SFP_CABLE_TECH_FIELD, bit), bit) for bit in range(0, 4))
                ),
                CodeRegField(consts.FIBRE_CHANNEL_TRANSMISSION_MEDIA_FIELD, self.get_addr(0xA0, None, 9), self.codes.FIBRE_CHANNEL_TRANSMISSION_MEDIA),
                CodeRegField(consts.FIBRE_CHANNEL_SPEED_FIELD, self.get_addr(0xA0, None, 10), self.codes.FIBRE_CHANNEL_SPEED),
            ),
            CodeRegField(consts.ENCODING_FIELD, self.get_addr(0xA0, None, 11), self.codes.ENCODINGS),
            NumberRegField(consts.NOMINAL_BR_FIELD, self.get_addr(0xA0, None, 12)),
            CodeRegField(consts.RATE_ID_FIELD, self.get_addr(0xA0, None, 13), self.codes.RATE_IDENTIFIERS),
            NumberRegField(consts.LENGTH_SMF_KM_FIELD, self.get_addr(0xA0, None, 14)),
            NumberRegField(consts.LENGTH_SMF_M_FIELD, self.get_addr(0xA0, None, 15)),
            NumberRegField(consts.LENGTH_OM2_FIELD, self.get_addr(0xA0, None, 16)),
            NumberRegField(consts.LENGTH_OM1_FIELD, self.get_addr(0xA0, None, 17)),
            NumberRegField(consts.LENGTH_OM4_FIELD, self.get_addr(0xA0, None, 18)),
            NumberRegField(consts.LENGTH_OM3_FIELD, self.get_addr(0xA0, None, 19)),
            StringRegField(consts.VENDOR_NAME_FIELD, self.get_addr(0xA0, None, 20), size=16),
            HexRegField(consts.VENDOR_OUI_FIELD, self.get_addr(0xA0, None, 37), size=3),
            StringRegField(consts.VENDOR_PART_NO_FIELD, self.get_addr(0xA0, None, 40), size=16),
            StringRegField(consts.VENDOR_REV_FIELD, self.get_addr(0xA0, None, 56), size=4),
            NumberRegField(consts.OPTIONS_FIELD, self.get_addr(0xA0, None, 64),
                RegBitField(consts.PAGING_SUPPORT_FIELD, 4),
            size=2, format="<H"),
            StringRegField(consts.VENDOR_SERIAL_NO_FIELD, self.get_addr(0xA0, None, 68), size=16),
            DateField(consts.VENDOR_DATE_FIELD, self.get_addr(0xA0, None, 84), size=8),
            NumberRegField(consts.DIAG_MON_TYPE_FIELD, self.get_addr(0xA0, None, 92),
                RegBitField(consts.DDM_SUPPORT_FIELD, 6),
                RegBitField(consts.INT_CAL_FIELD, 5),
                RegBitField(consts.EXT_CAL_FIELD, 4),
            ),
            NumberRegField(consts.ENHANCED_OPTIONS_FIELD, self.get_addr(0xA0, None, 3),
                RegBitField(consts.TX_DISABLE_SUPPORT_FIELD, 6),
                RegBitField(consts.TX_FAULT_SUPPORT_FIELD, 5),
                RegBitField(consts.RX_LOS_SUPPORT_FIELD, 4),
            ),
        )

        self.STATUS_CTRL = NumberRegField(consts.STATUS_CTRL_FIELD, self.get_addr(0xA2, 0, 110), 
            RegBitField(consts.TX_DISABLE_FIELD, 7),
            RegBitField(consts.TX_DISABLE_SELECT_FIELD, 6, ro=False),
            RegBitField(consts.TX_FAULT_FIELD, 2),
            RegBitField(consts.RX_LOS_FIELD, 1),
        )

        ext_cal_deps = [consts.INT_CAL_FIELD,
                        consts.EXT_CAL_FIELD,
                        consts.RX_PWR_4_FIELD, 
                        consts.RX_PWR_3_FIELD,
                        consts.RX_PWR_2_FIELD, 
                        consts.RX_PWR_1_FIELD, 
                        consts.RX_PWR_0_FIELD, 
                        consts.TX_I_SLOPE_FIELD, 
                        consts.TX_I_OFFSET_FIELD,
                        consts.TX_PWR_SLOPE_FIELD,
                        consts.TX_PWR_OFFSET_FIELD,
                        consts.T_SLOPE_FIELD,
                        consts.T_OFFSET_FIELD,
                        consts.V_SLOPE_FIELD,
                        consts.V_OFFSET_FIELD
                       ]

        self.DOM = RegGroupField(consts.DOM_FIELD,
            TempField(consts.TEMPERATURE_FIELD, self.get_addr(0xA2, 0, 96), size=2, format=">h", scale=256),
            VoltageField(consts.VOLTAGE_FIELD, self.get_addr(0xA2, 0, 98), size=2, format=">H", scale=10000),
            TxBiasField(consts.TX_BIAS_FIELD, self.get_addr(0xA2, 0, 100), size=2, format=">H", scale=500),
            TxPowerField(consts.TX_POWER_FIELD, self.get_addr(0xA2, 0, 102), size=2, format=">H", scale=1000),
            RxPowerField(consts.RX_POWER_FIELD, self.get_addr(0xA2, 0, 104), size=2, format=">H", scale=1000),
            deps=ext_cal_deps
        )

        self.THRESHOLDS = RegGroupField(consts.THRESHOLDS_FIELD,
            TempField(consts.TEMP_HIGH_ALARM_FIELD, self.get_addr(0xA2, 0, 0), size=2, format=">h", scale=256),
            TempField(consts.TEMP_LOW_ALARM_FIELD, self.get_addr(0xA2, 0, 2), size=2, format=">h", scale=256),
            TempField(consts.TEMP_HIGH_WARNING_FIELD, self.get_addr(0xA2, 0, 4), size=2, format=">h", scale=256),
            TempField(consts.TEMP_LOW_WARNING_FIELD, self.get_addr(0xA2, 0, 6), size=2, format=">h", scale=256),
            VoltageField(consts.VOLTAGE_HIGH_ALARM_FIELD, self.get_addr(0xA2, 0, 8), size=2, format=">H", scale=10000),
            VoltageField(consts.VOLTAGE_LOW_ALARM_FIELD, self.get_addr(0xA2, 0, 10), size=2, format=">H", scale=10000),
            VoltageField(consts.VOLTAGE_HIGH_WARNING_FIELD, self.get_addr(0xA2, 0, 12), size=2, format=">H", scale=10000),
            VoltageField(consts.VOLTAGE_LOW_WARNING_FIELD, self.get_addr(0xA2, 0, 14), size=2, format=">H", scale=10000),
            TxBiasField(consts.TX_BIAS_HIGH_ALARM_FIELD, self.get_addr(0xA2, 0, 16), size=2, format=">H", scale=500),
            TxBiasField(consts.TX_BIAS_LOW_ALARM_FIELD, self.get_addr(0xA2, 0, 18), size=2, format=">H", scale=500),
            TxBiasField(consts.TX_BIAS_HIGH_WARNING_FIELD, self.get_addr(0xA2, 0, 20), size=2, format=">H", scale=500),
            TxBiasField(consts.TX_BIAS_LOW_WARNING_FIELD, self.get_addr(0xA2, 0, 22), size=2, format=">H", scale=500),
            TxPowerField(consts.TX_POWER_HIGH_ALARM_FIELD, self.get_addr(0xA2, 0, 24), size=2, format=">H", scale=1000),
            TxPowerField(consts.TX_POWER_LOW_ALARM_FIELD, self.get_addr(0xA2, 0, 26), size=2, format=">H", scale=1000),
            TxPowerField(consts.TX_POWER_HIGH_WARNING_FIELD, self.get_addr(0xA2, 0, 28), size=2, format=">H", scale=1000),
            TxPowerField(consts.TX_POWER_LOW_WARNING_FIELD, self.get_addr(0xA2, 0, 30), size=2, format=">H", scale=1000),
            RxPowerField(consts.RX_POWER_HIGH_ALARM_FIELD, self.get_addr(0xA2, 0, 32), size=2, format=">H", scale=1000),
            RxPowerField(consts.RX_POWER_LOW_ALARM_FIELD, self.get_addr(0xA2, 0, 34), size=2, format=">H", scale=1000),
            RxPowerField(consts.RX_POWER_HIGH_WARNING_FIELD, self.get_addr(0xA2, 0, 36), size=2, format=">H", scale=1000),
            RxPowerField(consts.RX_POWER_LOW_WARNING_FIELD, self.get_addr(0xA2, 0, 38), size=2, format=">H", scale=1000),
            deps=ext_cal_deps
        )

        self.DOM_EXT_CAL_CONST = RegGroupField(consts.DOM_EXT_CAL_CONST_FIELD,
            NumberRegField(consts.RX_PWR_4_FIELD, self.get_addr(0xA2, 0, 56), size=4, format=">f"),
            NumberRegField(consts.RX_PWR_3_FIELD, self.get_addr(0xA2, 0, 60), size=4, format=">f"),
            NumberRegField(consts.RX_PWR_2_FIELD, self.get_addr(0xA2, 0, 64), size=4, format=">f"),
            NumberRegField(consts.RX_PWR_1_FIELD, self.get_addr(0xA2, 0, 68), size=4, format=">f"),
            NumberRegField(consts.RX_PWR_0_FIELD, self.get_addr(0xA2, 0, 72), size=4, format=">f"),
            NumberRegField(consts.TX_I_SLOPE_FIELD, self.get_addr(0xA2, 0, 76), size=2, format=">H"),
            NumberRegField(consts.TX_I_OFFSET_FIELD, self.get_addr(0xA2, 0, 78), size=2, format=">h"),
            NumberRegField(consts.TX_PWR_SLOPE_FIELD, self.get_addr(0xA2, 0, 80), size=2, format=">H"),
            NumberRegField(consts.TX_PWR_OFFSET_FIELD, self.get_addr(0xA2, 0, 82), size=2, format=">h"),
            NumberRegField(consts.T_SLOPE_FIELD, self.get_addr(0xA2, 0, 84), size=2, format=">H"),
            NumberRegField(consts.T_OFFSET_FIELD, self.get_addr(0xA2, 0, 86), size=2, format=">H"),
            NumberRegField(consts.V_SLOPE_FIELD, self.get_addr(0xA2, 0, 88), size=2, format=">H"),
            NumberRegField(consts.V_OFFSET_FIELD, self.get_addr(0xA2, 0, 90), size=2, format=">h") 
        )

    def get_addr(self, wire_addr, page, offset, page_size=128):
        assert wire_addr == 0xA0 or wire_addr == 0xA2
        if wire_addr == 0xA0:
            return offset

        return page * page_size + offset + 256
