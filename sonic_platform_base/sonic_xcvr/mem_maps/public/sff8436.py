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

class Sff8436MemMap(XcvrMemMap):
    def __init__(self, codes):
        super(Sff8436MemMap, self).__init__(codes)

        self.STATUS = RegGroupField(consts.STATUS_FIELD,
            NumberRegField(consts.STATUS_IND_BITS_FIELD, self.get_addr(0, 2), 
                RegBitField(consts.FLAT_MEM_FIELD, 2)
            )
        )

        self.SERIAL_ID = RegGroupField(consts.SERIAL_ID_FIELD,
            CodeRegField(consts.ID_FIELD, self.get_addr(0, 128), self.codes.XCVR_IDENTIFIERS),
            CodeRegField(consts.ID_ABBRV_FIELD, self.get_addr(0, 128), self.codes.XCVR_IDENTIFIER_ABBRV),
            RegGroupField(consts.EXT_ID_FIELD, 
                CodeRegField(consts.POWER_CLASS_FIELD, self.get_addr(0, 129), self.codes.POWER_CLASSES,
                    RegBitField("%s_6" % consts.POWER_CLASS_FIELD, 6),
                    RegBitField("%s_7" % consts.POWER_CLASS_FIELD, 7)
                ),
                CodeRegField(consts.CLEI_CODE_FIELD, self.get_addr(0, 129), self.codes.CLEI_CODE,
                    RegBitField("%s_4" % consts.CLEI_CODE_FIELD, 4)
                ),
                CodeRegField(consts.CDR_TX_FIELD, self.get_addr(0, 129), self.codes.CDR_TX,
                    RegBitField("%s_3" % consts.CDR_TX_FIELD, 3)
                ),
                CodeRegField(consts.CDR_RX_FIELD, self.get_addr(0, 129), self.codes.CDR_RX,
                    RegBitField("%s_2" % consts.CDR_RX_FIELD, 2)
                ),
            ),
            CodeRegField(consts.CONNECTOR_FIELD, self.get_addr(0, 130), self.codes.CONNECTORS),
            RegGroupField(consts.SPEC_COMPLIANCE_FIELD, 
                CodeRegField(consts.ETHERNET_10_40G_COMPLIANCE_FIELD, self.get_addr(0, 131), self.codes.ETHERNET_10_40G_COMPLIANCE),
                CodeRegField(consts.SONET_COMPLIANCE_FIELD, self.get_addr(0, 132), self.codes.SONET_COMPLIANCE),
                CodeRegField(consts.SAS_SATA_COMPLIANCE_FIELD, self.get_addr(0, 133), self.codes.SAS_SATA_COMPLIANCE),
                CodeRegField(consts.GIGABIT_ETHERNET_COMPLIANCE_FIELD, self.get_addr(0, 134), self.codes.GIGABIT_ETHERNET_COMPLIANCE),
                CodeRegField(consts.FIBRE_CHANNEL_LINK_LENGTH_FIELD, self.get_addr(0, 135), self.codes.FIBRE_CHANNEL_LINK_LENGTH,
                    *(RegBitField("%s_%d" % (consts.FIBRE_CHANNEL_LINK_LENGTH_FIELD, bit), bit) for bit in range(3, 8))
                ),
                CodeRegField(consts.FIBRE_CHANNEL_TRANSMITTER_TECH_FIELD, self.get_addr(0, 135), self.codes.FIBRE_CHANNEL_TRANSMITTER_TECH,
                    *(RegBitField("%s_%d" % (consts.FIBRE_CHANNEL_TRANSMITTER_TECH_FIELD, bit), bit) for bit in range(4, 11)),
                    size=2, format=">H"
                ),
                CodeRegField(consts.FIBRE_CHANNEL_TRANSMISSION_MEDIA_FIELD, self.get_addr(0, 137), self.codes.FIBRE_CHANNEL_TRANSMISSION_MEDIA),
                CodeRegField(consts.FIBRE_CHANNEL_SPEED_FIELD, self.get_addr(0, 138), self.codes.FIBRE_CHANNEL_SPEED),
            ),
            CodeRegField(consts.ENCODING_FIELD, self.get_addr(0, 139), self.codes.ENCODINGS),
            NumberRegField(consts.NOMINAL_BR_FIELD, self.get_addr(0, 140)),
            CodeRegField(consts.EXT_RATE_SELECT_COMPLIANCE_FIELD, self.get_addr(0, 141), self.codes.EXT_RATESELECT_COMPLIANCE),
            NumberRegField(consts.LENGTH_SMF_KM_FIELD, self.get_addr(0, 142)),
            NumberRegField(consts.LENGTH_OM3_FIELD, self.get_addr(0, 143)),
            NumberRegField(consts.LENGTH_OM2_FIELD, self.get_addr(0, 144)),
            NumberRegField(consts.LENGTH_OM1_FIELD, self.get_addr(0, 145)),
            NumberRegField(consts.LENGTH_ASSEMBLY_FIELD, self.get_addr(0, 146)),
            StringRegField(consts.VENDOR_NAME_FIELD, self.get_addr(0, 148), size=16),
            HexRegField(consts.VENDOR_OUI_FIELD, self.get_addr(0, 165), size=3),
            StringRegField(consts.VENDOR_PART_NO_FIELD, self.get_addr(0, 168), size=16),
            StringRegField(consts.VENDOR_REV_FIELD, self.get_addr(0, 184), size=2),
            NumberRegField(consts.OPTIONS_FIELD, self.get_addr(0, 192),
                RegBitField(consts.TX_FAULT_SUPPORT_FIELD, 27),
                RegBitField(consts.TX_DISABLE_SUPPORT_FIELD, 28),
            size=4, format="<I"),
            StringRegField(consts.VENDOR_SERIAL_NO_FIELD, self.get_addr(0, 196), size=16),
            DateField(consts.VENDOR_DATE_FIELD, self.get_addr(0, 212), size=8)
        )

        self.RX_LOS = NumberRegField(consts.RX_LOS_FIELD, self.get_addr(0, 3),
            *(RegBitField("Rx%dLOS" % channel, bitpos)
              for channel, bitpos in zip(range(1, 5), range(0, 4)))
        )

        self.TX_FAULT = NumberRegField(consts.TX_FAULT_FIELD, self.get_addr(0, 4),
            *(RegBitField("Tx%dFault" % channel, bitpos)
              for channel, bitpos in zip(range(1, 5), range(0, 4)))
        )

        self.TX_DISABLE = NumberRegField(consts.TX_DISABLE_FIELD, self.get_addr(0, 86),
            *(RegBitField("Tx%dDisable" % channel, bitpos, ro=False)
              for channel, bitpos in zip(range(1, 5), range(0, 4))),
            ro=False
        )

        self.RX_POWER = RegGroupField(consts.RX_POWER_FIELD,
            *(NumberRegField("Rx%dPowerField" % channel, self.get_addr(0, offset), size=2, format=">H", scale=10000)
              for channel, offset in zip(range(1, 5), range(34, 41, 2)))
        )

        self.TX_BIAS = RegGroupField(consts.TX_BIAS_FIELD,
            *(NumberRegField("Tx%dBiasField" % channel, self.get_addr(0, offset), size=2, format=">H", scale=500)
              for channel, offset in zip(range(1, 5), range(42, 49, 2)))
        )

        self.TEMP = NumberRegField(consts.TEMPERATURE_FIELD, self.get_addr(0, 22), size=2, format=">h", scale=256)
        
        self.VOLTAGE = NumberRegField(consts.VOLTAGE_FIELD, self.get_addr(0, 26), size=2, format=">H", scale=10000)

        self.POWER_CTRL = NumberRegField(consts.POWER_CTRL_FIELD, self.get_addr(0, 93),
            RegBitField(consts.POWER_OVERRIDE_FIELD, 0, ro=False),
            RegBitField(consts.POWER_SET_FIELD, 1, ro=False),
            ro=False
        )

        self.TEMP_THRESHOLDS = RegGroupField(consts.TEMP_THRESHOLDS_FIELD,
            NumberRegField(consts.TEMP_HIGH_ALARM_FIELD, self.get_addr(3, 128), size=2, format=">h", scale=256),
            NumberRegField(consts.TEMP_LOW_ALARM_FIELD, self.get_addr(3, 130), size=2, format=">h", scale=256),
            NumberRegField(consts.TEMP_HIGH_WARNING_FIELD, self.get_addr(3, 132), size=2, format=">h", scale=256),
            NumberRegField(consts.TEMP_LOW_WARNING_FIELD, self.get_addr(3, 134), size=2, format=">h", scale=256),
        )

        self.VOLTAGE_THRESHOLDS = RegGroupField(consts.VOLTAGE_THRESHOLDS_FIELD,
            NumberRegField(consts.VOLTAGE_HIGH_ALARM_FIELD, self.get_addr(3, 144), size=2, format=">H", scale=10000),
            NumberRegField(consts.VOLTAGE_LOW_ALARM_FIELD, self.get_addr(3, 146), size=2, format=">H", scale=10000),
            NumberRegField(consts.VOLTAGE_HIGH_WARNING_FIELD, self.get_addr(3, 148), size=2, format=">H", scale=10000),
            NumberRegField(consts.VOLTAGE_LOW_WARNING_FIELD, self.get_addr(3, 150), size=2, format=">H", scale=10000),
        )

        self.RX_POWER_THRESHOLDS = RegGroupField(consts.RX_POWER_THRESHOLDS_FIELD,
            NumberRegField(consts.RX_POWER_HIGH_ALARM_FIELD, self.get_addr(3, 176), size=2, format=">H", scale=10000),
            NumberRegField(consts.RX_POWER_LOW_ALARM_FIELD, self.get_addr(3, 178), size=2, format=">H", scale=10000),
            NumberRegField(consts.RX_POWER_HIGH_WARNING_FIELD, self.get_addr(3, 180), size=2, format=">H", scale=10000),
            NumberRegField(consts.RX_POWER_LOW_WARNING_FIELD, self.get_addr(3, 182), size=2, format=">H", scale=10000),
        )

        self.TX_BIAS_THRESHOLDS = RegGroupField(consts.TX_BIAS_THRESHOLDS_FIELD,
            NumberRegField(consts.TX_BIAS_HIGH_ALARM_FIELD, self.get_addr(3, 184), size=2, format=">H", scale=500),
            NumberRegField(consts.TX_BIAS_LOW_ALARM_FIELD, self.get_addr(3, 186), size=2, format=">H", scale=500),
            NumberRegField(consts.TX_BIAS_HIGH_WARNING_FIELD, self.get_addr(3, 188), size=2, format=">H", scale=500),
            NumberRegField(consts.TX_BIAS_LOW_WARNING_FIELD, self.get_addr(3, 190), size=2, format=">H", scale=500),
        )

    def get_addr(self, page, offset, page_size=128):
        return page * page_size + offset
