"""cmis_pages.py

CmisPage subclasses for the standard CMIS Rev 5.0 memory map. Each class
populates self.fields with const-string keys; CmisPage.register_fields then
composes them onto a CmisMemMap (or any XcvrMemMap subclass) with cross-page
group merging handled by the base class.
"""

from .base import CmisPage
from .cmis_page_consts import (
    ADMINISTRATIVE_PAGE,
    ADVERTISING_PAGE,
    THRESHOLDS_PAGE,
    LANE_DATAPATH_CONFIG_PAGE,
    LANE_DATAPATH_STATUS_PAGE,
    TUNABLE_LASER_CTRL_STATUS_PAGE,
    MODULE_PERF_DIAG_CTRL_PAGE,
    VDM_ADVERTISING_CTRL_PAGE,
    CDB_MESSAGE_PAGE,
)
from ....fields.xcvr_field import (
    CodeRegField,
    DateField,
    HexRegField,
    NumberRegField,
    RegBitField,
    RegBitsField,
    RegGroupField,
    StringRegField,
)
from ....fields import consts
from ....fields.public.cmis import CableLenField


# ---------------------------------------------------------------------------
# Page 0x00 -- Administrative (lower memory, offsets 0-127)
# ---------------------------------------------------------------------------
class CmisAdministrativeLowerPage(CmisPage):
    def __init__(self, codes, page=ADMINISTRATIVE_PAGE, bank=0):
        super(CmisAdministrativeLowerPage, self).__init__(
            codes, page=page, bank=bank)

        self.fields[consts.MGMT_CHAR_FIELD] = [
            NumberRegField(consts.MGMT_CHAR_MISC_FIELD, self.getaddr(2),
                RegBitField(consts.FLAT_MEM_FIELD, 7)
            ),
        ]

        self.fields[consts.ADMIN_INFO_FIELD] = [
            CodeRegField(consts.ID_FIELD, self.getaddr(0), self.codes.XCVR_IDENTIFIERS),
            NumberRegField(consts.CMIS_MAJOR_REVISION, self.getaddr(1),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8))
            ),
            NumberRegField(consts.CMIS_MINOR_REVISION, self.getaddr(1),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 4))
            ),
            NumberRegField(consts.ACTIVE_FW_MAJOR_REV, self.getaddr(39), format="B", size=1),
            NumberRegField(consts.ACTIVE_FW_MINOR_REV, self.getaddr(40), format="B", size=1),
            CodeRegField(consts.MEDIA_TYPE_FIELD, self.getaddr(85), self.codes.MODULE_MEDIA_TYPE),
            CodeRegField(consts.HOST_ELECTRICAL_INTERFACE, self.getaddr(86), self.codes.HOST_ELECTRICAL_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_850NM, self.getaddr(87), self.codes.NM_850_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_SM, self.getaddr(87), self.codes.SM_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER, self.getaddr(87), self.codes.PASSIVE_COPPER_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE, self.getaddr(87), self.codes.ACTIVE_CABLE_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_BASE_T, self.getaddr(87), self.codes.BASE_T_MEDIA_INTERFACE),
            NumberRegField(consts.MEDIA_LANE_COUNT, self.getaddr(88),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 4))
            ),
            NumberRegField(consts.HOST_LANE_COUNT, self.getaddr(88),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8))
            ),
            NumberRegField(consts.HOST_LANE_ASSIGNMENT_OPTION, self.getaddr(89), format="B", size=1),
        ]

        self.fields[consts.APPLS_ADVT_FIELD] = [
            *(CodeRegField(f"{consts.HOST_ELECTRICAL_INTERFACE}_{app}", self.getaddr(86 + 4 * (app - 1)),
                self.codes.HOST_ELECTRICAL_INTERFACE) for app in range(1, 9)),

            *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_850NM}_{app}", self.getaddr(87 + 4 * (app - 1)),
                self.codes.NM_850_MEDIA_INTERFACE) for app in range(1, 9)),

            *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_SM}_{app}", self.getaddr(87 + 4 * (app - 1)),
                self.codes.SM_MEDIA_INTERFACE) for app in range(1, 9)),

            *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER}_{app}", self.getaddr(87 + 4 * (app - 1)),
                self.codes.PASSIVE_COPPER_MEDIA_INTERFACE) for app in range(1, 9)),

            *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE}_{app}", self.getaddr(87 + 4 * (app - 1)),
                self.codes.ACTIVE_CABLE_MEDIA_INTERFACE) for app in range(1, 9)),

            *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_BASE_T}_{app}", self.getaddr(87 + 4 * (app - 1)),
                self.codes.BASE_T_MEDIA_INTERFACE) for app in range(1, 9)),

            *(NumberRegField(f"{consts.MEDIA_LANE_COUNT}_{lane}", self.getaddr(88 + 4 * (lane - 1)),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 4))
            ) for lane in range(1, 9)),

            *(NumberRegField(f"{consts.HOST_LANE_COUNT}_{lane}", self.getaddr(88 + 4 * (lane - 1)),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8))
            ) for lane in range(1, 9)),

            *(NumberRegField(f"{consts.HOST_LANE_ASSIGNMENT_OPTION}_{lane}", self.getaddr(89 + 4 * (lane - 1)),
                format="B", size=1) for lane in range(1, 9)),
        ]

        self.fields[consts.MODULE_MONITORS_PAGE0_FIELD] = [
            NumberRegField(consts.TEMPERATURE_FIELD, self.getaddr(14), size=2, format=">h", scale=256.0),
            NumberRegField(consts.VOLTAGE_FIELD, self.getaddr(16), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.AUX1_MON, self.getaddr(18), format=">h", size=2),
            NumberRegField(consts.AUX2_MON, self.getaddr(20), format=">h", size=2),
            NumberRegField(consts.AUX3_MON, self.getaddr(22), format=">h", size=2),
            NumberRegField(consts.CUSTOM_MON, self.getaddr(24), size=2, format=">h", scale=256.0),
        ]

        self.fields[consts.TRANS_MODULE_STATUS_FIELD] = [
            CodeRegField(consts.MODULE_STATE, self.getaddr(3), self.codes.MODULE_STATE,
                *(RegBitField(f"Bit{bit}", bit) for bit in range(1, 4))
            ),
            NumberRegField(consts.MODULE_FIRMWARE_FAULT_INFO, self.getaddr(8), size=1),
            NumberRegField(consts.MODULE_FLAG_BYTE1, self.getaddr(9), size=1),
            NumberRegField(consts.MODULE_FLAG_BYTE2, self.getaddr(10), size=1),
            NumberRegField(consts.MODULE_FLAG_BYTE3, self.getaddr(11), size=1),
            NumberRegField(consts.CDB1_STATUS, self.getaddr(37), size=1),
            CodeRegField(consts.MODULE_FAULT_CAUSE, self.getaddr(41), self.codes.MODULE_FAULT_CAUSE),
        ]

        self.fields[consts.TRANS_CONFIG_FIELD] = [
            NumberRegField(consts.MODULE_LEVEL_CONTROL, self.getaddr(26), size=1, ro=False),
        ]

    def getaddr(self, offset, page_size=128):
        if self._page != ADMINISTRATIVE_PAGE and offset < 128:
            offset += 128
        return super(CmisAdministrativeLowerPage, self).getaddr(offset, page_size)


# ---------------------------------------------------------------------------
# Page 0x00 -- Administrative (upper memory, offsets 128-255)
# ---------------------------------------------------------------------------
class CmisAdministrativeUpperPage(CmisPage):
    def __init__(self, codes, page=ADMINISTRATIVE_PAGE, bank=0):
        super(CmisAdministrativeUpperPage, self).__init__(
            codes, page=page, bank=bank)

        self.fields[consts.ADMIN_INFO_FIELD] = [
            CodeRegField(consts.ID_ABBRV_FIELD, self.getaddr(128), self.codes.XCVR_IDENTIFIER_ABBRV),
            StringRegField(consts.VENDOR_NAME_FIELD, self.getaddr(129), size=16),
            HexRegField(consts.VENDOR_OUI_FIELD, self.getaddr(145), size=3),
            StringRegField(consts.VENDOR_PART_NO_FIELD, self.getaddr(148), size=16),
            StringRegField(consts.VENDOR_REV_FIELD, self.getaddr(164), size=2),
            StringRegField(consts.VENDOR_SERIAL_NO_FIELD, self.getaddr(166), size=16),
            DateField(consts.VENDOR_DATE_FIELD, self.getaddr(182), size=8),
            RegGroupField(consts.EXT_ID_FIELD,
                CodeRegField(consts.POWER_CLASS_FIELD, self.getaddr(200), self.codes.POWER_CLASSES,
                    *(RegBitField(f"{consts.POWER_CLASS_FIELD}_{bit}", bit) for bit in range(5, 8))
                ),
                NumberRegField(consts.MAX_POWER_FIELD, self.getaddr(201), scale=4.0),
            ),
            NumberRegField(consts.LEN_MULT_FIELD, self.getaddr(202),
                *(RegBitField(f"{consts.LEN_MULT_FIELD}_{bit}", bit) for bit in range(6, 8))
            ),
            CableLenField(consts.LENGTH_ASSEMBLY_FIELD, self.getaddr(202),
                *(RegBitField(f"{consts.LENGTH_ASSEMBLY_FIELD}_{bit}", bit) for bit in range(0, 6))
            ),
            CodeRegField(consts.CONNECTOR_FIELD, self.getaddr(203), self.codes.CONNECTORS),
            CodeRegField(consts.MEDIA_INTERFACE_TECH, self.getaddr(212), self.codes.MEDIA_INTERFACE_TECH),
        ]


# ---------------------------------------------------------------------------
# Page 0x01 -- Advertising
# ---------------------------------------------------------------------------
class CmisAdvertisingPage(CmisPage):
    def __init__(self, codes, page=ADVERTISING_PAGE, bank=0):
        super(CmisAdvertisingPage, self).__init__(
            codes, page=page, bank=bank)

        self.fields[consts.ADVERTISING_FIELD] = [
            NumberRegField(consts.INACTIVE_FW_MAJOR_REV, self.getaddr(128), format="B", size=1),
            NumberRegField(consts.INACTIVE_FW_MINOR_REV, self.getaddr(129), format="B", size=1),
            NumberRegField(consts.HW_MAJOR_REV, self.getaddr(130), size=1),
            NumberRegField(consts.HW_MINOR_REV, self.getaddr(131), size=1),
            CodeRegField(consts.DP_PATH_INIT_DURATION, self.getaddr(144), self.codes.DP_PATH_TIMINGS,
                *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 4))
            ),
            CodeRegField(consts.DP_PATH_DEINIT_DURATION, self.getaddr(144), self.codes.DP_PATH_TIMINGS,
                *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8))
            ),
            CodeRegField(consts.MODULE_PWRUP_DURATION, self.getaddr(167), self.codes.DP_PATH_TIMINGS,
                *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 4))
            ),
            CodeRegField(consts.MODULE_PWRDN_DURATION, self.getaddr(167), self.codes.DP_PATH_TIMINGS,
                *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8))
            ),
            CodeRegField(consts.DP_TX_TURNON_DURATION, self.getaddr(168), self.codes.DP_PATH_TIMINGS,
                *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 4))
            ),
            CodeRegField(consts.DP_TX_TURNOFF_DURATION, self.getaddr(168), self.codes.DP_PATH_TIMINGS,
                *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8))
            ),
            NumberRegField(consts.MEDIA_LANE_ASSIGNMENT_OPTION, self.getaddr(176), format="B", size=1),

            RegGroupField(consts.APPLS_ADVT_FIELD_PAGE01,
                *(NumberRegField(f"{consts.MEDIA_LANE_ASSIGNMENT_OPTION}_{app}", self.getaddr(176 + (app - 1)),
                    format="B", size=1) for app in range(1, 16)),

                *(CodeRegField(f"{consts.HOST_ELECTRICAL_INTERFACE}_{app}", self.getaddr(223 + 4 * (app - 9)),
                    self.codes.HOST_ELECTRICAL_INTERFACE) for app in range(9, 16)),

                *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_850NM}_{app}", self.getaddr(224 + 4 * (app - 9)),
                    self.codes.NM_850_MEDIA_INTERFACE) for app in range(9, 16)),

                *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_SM}_{app}", self.getaddr(224 + 4 * (app - 9)),
                    self.codes.SM_MEDIA_INTERFACE) for app in range(9, 16)),

                *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER}_{app}", self.getaddr(224 + 4 * (app - 9)),
                    self.codes.PASSIVE_COPPER_MEDIA_INTERFACE) for app in range(9, 16)),

                *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE}_{app}", self.getaddr(224 + 4 * (app - 9)),
                    self.codes.ACTIVE_CABLE_MEDIA_INTERFACE) for app in range(9, 16)),

                *(CodeRegField(f"{consts.MODULE_MEDIA_INTERFACE_BASE_T}_{app}", self.getaddr(224 + 4 * (app - 9)),
                    self.codes.BASE_T_MEDIA_INTERFACE) for app in range(9, 16)),

                *(NumberRegField(f"{consts.MEDIA_LANE_COUNT}_{lane}", self.getaddr(225 + 4 * (lane - 9)),
                    *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 4))
                ) for lane in range(9, 16)),

                *(NumberRegField(f"{consts.HOST_LANE_COUNT}_{lane}", self.getaddr(225 + 4 * (lane - 9)),
                    *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8))
                ) for lane in range(9, 16)),

                *(NumberRegField(f"{consts.HOST_LANE_ASSIGNMENT_OPTION}_{app}", self.getaddr(226 + 4 * (app - 9)),
                    format="B", size=1) for app in range(9, 16)),
            ),
        ]

        self.fields[consts.MODULE_MONITORS_FIELD] = [
            NumberRegField(consts.AUX_MON_TYPE, self.getaddr(145), size=1),
        ]

        self.fields[consts.MODULE_CHAR_ADVT_FIELD] = [
            NumberRegField(consts.PAGE_SUPPORT_ADVT_FIELD, self.getaddr(142),
                RegBitField(consts.VDM_SUPPORTED, 6),
                RegBitField(consts.DIAG_PAGE_SUPPORT_ADVT_FIELD, 5),
            ),
            NumberRegField(consts.TX_INPUT_EQ_MAX, self.getaddr(153),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 4))
            ),
            NumberRegField(consts.RX_OUTPUT_LEVEL_SUPPORT, self.getaddr(153),
                RegBitField(consts.RX_OUTPUT_LEVEL_0_SUPPORTED, 4),
                RegBitField(consts.RX_OUTPUT_LEVEL_1_SUPPORTED, 5),
                RegBitField(consts.RX_OUTPUT_LEVEL_2_SUPPORTED, 6),
                RegBitField(consts.RX_OUTPUT_LEVEL_3_SUPPORTED, 7),
            ),
            NumberRegField(consts.RX_OUTPUT_EQ_PRE_CURSOR_MAX, self.getaddr(154),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 4))
            ),
            NumberRegField(consts.RX_OUTPUT_EQ_POST_CURSOR_MAX, self.getaddr(154),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8))
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
                *(RegBitField(f"Bit{bit}", bit) for bit in range(3, 5))
            ),
        ]

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
                *(RegBitField(f"Bit{bit}", bit) for bit in range(5, 7))
            ),

            NumberRegField(consts.RX_SI_CTRL_ADVT, self.getaddr(162),
                RegBitField(consts.RX_CDR_SUPPORT_FIELD, 0),
                RegBitField(consts.RX_CDR_BYPASS_CTRL_FIELD, 1),
                RegBitField(consts.RX_OUTPUT_AMP_CTRL_SUPPORT_FIELD, 2),
                RegBitField(consts.RX_OUTPUT_EQ_PRE_CTRL_SUPPORT_FIELD, 3),
                RegBitField(consts.RX_OUTPUT_EQ_POST_CTRL_SUPPORT_FIELD, 4),
            ),
            NumberRegField(consts.RX_OUTPUT_EQ_CTRL_SUPPORT_FIELD, self.getaddr(162),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(3, 5))
            ),
        ]

        self.fields[consts.TRANS_CDB_FIELD] = [
            NumberRegField(consts.CDB_SUPPORT, self.getaddr(163),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(6, 8))
            ),
            NumberRegField(consts.AUTO_PAGING_SUPPORT, self.getaddr(163),
                (RegBitField("Bit4", 4))
            ),
            NumberRegField(consts.CDB_SEQ_WRITE_LENGTH_EXT, self.getaddr(164), size=1),
        ]


# ---------------------------------------------------------------------------
# Page 0x02 -- Module-level thresholds
# ---------------------------------------------------------------------------
class CmisThresholdsPage(CmisPage):
    def __init__(self, codes, page=THRESHOLDS_PAGE, bank=0):
        super(CmisThresholdsPage, self).__init__(
            codes, page=page, bank=bank)

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


# ---------------------------------------------------------------------------
# Page 0x10 -- Lane datapath configuration / staged controls
# ---------------------------------------------------------------------------
class CmisLaneDatapathConfigPage(CmisPage):
    def __init__(self, codes):
        super(CmisLaneDatapathConfigPage, self).__init__(
            codes, page=LANE_DATAPATH_CONFIG_PAGE, bank=0)

        self.fields[consts.LANE_DATAPATH_CTRL_FIELD] = [
            NumberRegField(consts.DATAPATH_DEINIT_FIELD, self.getaddr(128), ro=False),
            NumberRegField(consts.TX_DISABLE_FIELD, self.getaddr(130), ro=False),
            NumberRegField(consts.RX_DISABLE_FIELD, self.getaddr(138), ro=False,
                *(RegBitField(f"{consts.RX_DISABLE_FIELD}_{channel}", bitpos, ro=False)
                  for channel, bitpos in zip(range(1, 9), range(0, 8)))
            ),
        ]

        # Preserve the original RegGroupField .name f"{consts.STAGED_CTRL_FIELD}_0"
        self.fields[f"{consts.STAGED_CTRL_FIELD}_0"] = [
            NumberRegField(f"{consts.STAGED_CTRL_APPLY_DPINIT_FIELD}_0",
                self.getaddr(143), ro=False),
            NumberRegField(f"{consts.STAGED_CTRL_APPLY_IMMEDIATE_FIELD}_0",
                self.getaddr(144), ro=False),
            *(NumberRegField(f"{consts.STAGED_CTRL_APSEL_FIELD}_0_{lane}",
                self.getaddr(144 + lane), ro=False) for lane in range(1, 9)),
        ]

        self.fields[consts.STAGED_CTRL0_TX_RX_CTRL_FIELD] = [
            NumberRegField(consts.ADAPTIVE_INPUT_EQ_ENABLE_TX, self.getaddr(153),
                *(RegBitsField(consts.ADAPTIVE_INPUT_EQ_ENABLE_TX + str(lane), bitpos=(lane - 1), ro=False, size=1)
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
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX2, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.FIXED_INPUT_EQ_TARGET_TX3_4, self.getaddr(157),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX3, bitpos=0, ro=False, size=4),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX4, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.FIXED_INPUT_EQ_TARGET_TX5_6, self.getaddr(158),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX5, bitpos=0, ro=False, size=4),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX6, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.FIXED_INPUT_EQ_TARGET_TX7_8, self.getaddr(159),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX7, bitpos=0, ro=False, size=4),
                RegBitsField(consts.FIXED_INPUT_EQ_TARGET_TX8, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.CDR_ENABLE_TX, self.getaddr(160),
                *(RegBitsField(consts.CDR_ENABLE_TX + str(lane), bitpos=(lane - 1), ro=False, size=1)
                  for lane in range(1, 9))
            ),
            NumberRegField(consts.CDR_ENABLE_RX, self.getaddr(161),
                *(RegBitsField(consts.CDR_ENABLE_RX + str(lane), bitpos=(lane - 1), ro=False, size=1)
                  for lane in range(1, 9))
            ),
            NumberRegField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX1_2, self.getaddr(162),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX1, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX2, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX3_4, self.getaddr(163),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX3, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX4, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX5_6, self.getaddr(164),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX5, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX6, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX7_8, self.getaddr(165),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX7, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_PRE_CURSOR_TARGET_RX8, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX1_2, self.getaddr(166),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX1, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX2, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX3_4, self.getaddr(167),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX3, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX4, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX5_6, self.getaddr(168),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX5, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX6, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX7_8, self.getaddr(169),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX7, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_EQ_POST_CURSOR_TARGET_RX8, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_AMPLITUDE_TARGET_RX1_2, self.getaddr(170),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX1, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX2, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_AMPLITUDE_TARGET_RX3_4, self.getaddr(171),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX3, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX4, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_AMPLITUDE_TARGET_RX5_6, self.getaddr(172),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX5, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX6, bitpos=4, ro=False, size=4),
            ),
            NumberRegField(consts.OUTPUT_AMPLITUDE_TARGET_RX7_8, self.getaddr(173),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX7, bitpos=0, ro=False, size=4),
                RegBitsField(consts.OUTPUT_AMPLITUDE_TARGET_RX8, bitpos=4, ro=False, size=4),
            ),
        ]


# ---------------------------------------------------------------------------
# Page 0x11 -- Lane datapath status, alarm/warning flags
# ---------------------------------------------------------------------------
class CmisLaneDatapathStatusPage(CmisPage):
    def __init__(self, codes):
        super(CmisLaneDatapathStatusPage, self).__init__(
            codes, page=LANE_DATAPATH_STATUS_PAGE, bank=0)

        self.fields[consts.ADVERTISING_FIELD] = [
            RegGroupField(consts.ACTIVE_APSEL_CODE,
                *(NumberRegField(f"{consts.ACTIVE_APSEL_HOSTLANE}{lane}", self.getaddr(offset),
                    *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8)))
                  for lane, offset in zip(range(1, 9), range(206, 214)))
            ),
        ]

        self.fields[consts.TX_POWER_ALARM_FLAGS_FIELD] = [
            RegGroupField(consts.TX_POWER_HIGH_ALARM_FLAG,
                *(NumberRegField(f"{consts.TX_POWER_HIGH_ALARM_FLAG}{lane}", self.getaddr(139),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_LOW_ALARM_FLAG,
                *(NumberRegField(f"{consts.TX_POWER_LOW_ALARM_FLAG}{lane}", self.getaddr(140),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_HIGH_WARN_FLAG,
                *(NumberRegField(f"{consts.TX_POWER_HIGH_WARN_FLAG}{lane}", self.getaddr(141),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_LOW_WARN_FLAG,
                *(NumberRegField(f"{consts.TX_POWER_LOW_WARN_FLAG}{lane}", self.getaddr(142),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
        ]

        self.fields[consts.TX_BIAS_ALARM_FLAGS_FIELD] = [
            RegGroupField(consts.TX_BIAS_HIGH_ALARM_FLAG,
                *(NumberRegField(f"{consts.TX_BIAS_HIGH_ALARM_FLAG}{lane}", self.getaddr(143),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_LOW_ALARM_FLAG,
                *(NumberRegField(f"{consts.TX_BIAS_LOW_ALARM_FLAG}{lane}", self.getaddr(144),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_HIGH_WARN_FLAG,
                *(NumberRegField(f"{consts.TX_BIAS_HIGH_WARN_FLAG}{lane}", self.getaddr(145),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_LOW_WARN_FLAG,
                *(NumberRegField(f"{consts.TX_BIAS_LOW_WARN_FLAG}{lane}", self.getaddr(146),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
        ]

        self.fields[consts.RX_POWER_ALARM_FLAGS_FIELD] = [
            RegGroupField(consts.RX_POWER_HIGH_ALARM_FLAG,
                *(NumberRegField(f"{consts.RX_POWER_HIGH_ALARM_FLAG}{lane}", self.getaddr(149),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_LOW_ALARM_FLAG,
                *(NumberRegField(f"{consts.RX_POWER_LOW_ALARM_FLAG}{lane}", self.getaddr(150),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_HIGH_WARN_FLAG,
                *(NumberRegField(f"{consts.RX_POWER_HIGH_WARN_FLAG}{lane}", self.getaddr(151),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_LOW_WARN_FLAG,
                *(NumberRegField(f"{consts.RX_POWER_LOW_WARN_FLAG}{lane}", self.getaddr(152),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
        ]

        self.fields[consts.LANE_DATAPATH_STATUS_FIELD] = [
            RegGroupField(consts.DATA_PATH_STATE,
                *(CodeRegField(f"DP{lane}State", self.getaddr(128 + int((lane - 1) / 2)), self.codes.DATAPATH_STATE,
                    *(RegBitField(f"Bit{bit}", bit) for bit in [range(4, 8), range(0, 4)][lane % 2]))
                  for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_OUTPUT_STATUS,
                *(NumberRegField(f"{consts.RX_OUTPUT_STATUS}{lane}", self.getaddr(132),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_OUTPUT_STATUS,
                *(NumberRegField(f"{consts.TX_OUTPUT_STATUS}{lane}", self.getaddr(133),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_FAULT_FIELD,
                *(NumberRegField(f"{consts.TX_FAULT_FIELD}{lane}", self.getaddr(135),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_LOS_FIELD,
                *(NumberRegField(f"{consts.TX_LOS_FIELD}{lane}", self.getaddr(136),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_CDR_LOL,
                *(NumberRegField(f"{consts.TX_CDR_LOL}{lane}", self.getaddr(137),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_ADAPTIVE_INPUT_EQ_FAIL_FLAG,
                *(NumberRegField(f"{consts.TX_ADAPTIVE_INPUT_EQ_FAIL_FLAG}{lane}", self.getaddr(138),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_HIGH_ALARM_FLAG,
                *(NumberRegField(f"{consts.TX_POWER_HIGH_ALARM_FLAG}{lane}", self.getaddr(139),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_LOW_ALARM_FLAG,
                *(NumberRegField(f"{consts.TX_POWER_LOW_ALARM_FLAG}{lane}", self.getaddr(140),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_HIGH_WARN_FLAG,
                *(NumberRegField(f"{consts.TX_POWER_HIGH_WARN_FLAG}{lane}", self.getaddr(141),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_LOW_WARN_FLAG,
                *(NumberRegField(f"{consts.TX_POWER_LOW_WARN_FLAG}{lane}", self.getaddr(142),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_HIGH_ALARM_FLAG,
                *(NumberRegField(f"{consts.TX_BIAS_HIGH_ALARM_FLAG}{lane}", self.getaddr(143),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_LOW_ALARM_FLAG,
                *(NumberRegField(f"{consts.TX_BIAS_LOW_ALARM_FLAG}{lane}", self.getaddr(144),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_HIGH_WARN_FLAG,
                *(NumberRegField(f"{consts.TX_BIAS_HIGH_WARN_FLAG}{lane}", self.getaddr(145),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_BIAS_LOW_WARN_FLAG,
                *(NumberRegField(f"{consts.TX_BIAS_LOW_WARN_FLAG}{lane}", self.getaddr(146),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_LOS_FIELD,
                *(NumberRegField(f"{consts.RX_LOS_FIELD}{lane}", self.getaddr(147),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_CDR_LOL,
                *(NumberRegField(f"{consts.RX_CDR_LOL}{lane}", self.getaddr(148),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_HIGH_ALARM_FLAG,
                *(NumberRegField(f"{consts.RX_POWER_HIGH_ALARM_FLAG}{lane}", self.getaddr(149),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_LOW_ALARM_FLAG,
                *(NumberRegField(f"{consts.RX_POWER_LOW_ALARM_FLAG}{lane}", self.getaddr(150),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_HIGH_WARN_FLAG,
                *(NumberRegField(f"{consts.RX_POWER_HIGH_WARN_FLAG}{lane}", self.getaddr(151),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.RX_POWER_LOW_WARN_FLAG,
                *(NumberRegField(f"{consts.RX_POWER_LOW_WARN_FLAG}{lane}", self.getaddr(152),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
            RegGroupField(consts.TX_POWER_FIELD,
                *(NumberRegField(f"OpticalPowerTx{channel}Field", self.getaddr(offset), size=2, format=">H", scale=10000.0)
                  for channel, offset in zip(range(1, 9), range(154, 170, 2)))
            ),
            RegGroupField(consts.TX_BIAS_FIELD,
                *(NumberRegField(f"LaserBiasTx{channel}Field", self.getaddr(offset), size=2, format=">H", scale=500.0)
                  for channel, offset in zip(range(1, 9), range(170, 186, 2)))
            ),
            RegGroupField(consts.RX_POWER_FIELD,
                *(NumberRegField(f"OpticalPowerRx{channel}Field", self.getaddr(offset), size=2, format=">H", scale=10000.0)
                  for channel, offset in zip(range(1, 9), range(186, 202, 2)))
            ),
            RegGroupField(consts.CONFIG_LANE_STATUS,
                *(CodeRegField(f"{consts.CONFIG_LANE_STATUS}{lane}", self.getaddr(202 + int((lane - 1) / 2)), self.codes.CONFIG_STATUS,
                    *(RegBitField(f"Bit{bit}", bit) for bit in [range(4, 8), range(0, 4)][lane % 2]))
                  for lane in range(1, 9))
            ),
            RegGroupField(consts.DPINIT_PENDING,
                *(NumberRegField(f"{consts.DPINIT_PENDING}{lane}", self.getaddr(235),
                    RegBitField(f"Bit{lane - 1}", (lane - 1))
                ) for lane in range(1, 9))
            ),
        ]


# ---------------------------------------------------------------------------
# Page 0x12 -- Tunable laser control / module-level monitors
# ---------------------------------------------------------------------------
class CmisTunableLaserCtrlStatusPage(CmisPage):
    def __init__(self, codes):
        super(CmisTunableLaserCtrlStatusPage, self).__init__(
            codes, page=TUNABLE_LASER_CTRL_STATUS_PAGE, bank=0)

        self.fields[consts.MODULE_MONITORS_FIELD] = [
            NumberRegField(consts.GRID_SPACING, self.getaddr(128),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(4, 8)), ro=False
            ),
            NumberRegField(consts.LASER_CONFIG_CHANNEL, self.getaddr(136), format=">h", size=2, ro=False),
            NumberRegField(consts.LASER_CURRENT_FREQ, self.getaddr(168), format=">L", size=4, scale=1000.0),
            NumberRegField(consts.TX_CONFIG_POWER, self.getaddr(200), format=">h", size=2, scale=100.0, ro=False),
        ]

        self.fields[consts.LANE_DATAPATH_STATUS_FIELD] = [
            RegBitField(consts.TUNING_IN_PROGRESS, offset=self.getaddr(222), bitpos=1),
            RegBitField(consts.WAVELENGTH_UNLOCKED, offset=self.getaddr(222), bitpos=0),
            NumberRegField(consts.LASER_TUNING_DETAIL, self.getaddr(231), size=1),
        ]


# ---------------------------------------------------------------------------
# Page 0x13 -- Module-level loopback / performance diagnostics
# ---------------------------------------------------------------------------
class CmisModulePerfDiagCtrlPage(CmisPage):
    def __init__(self, codes):
        super(CmisModulePerfDiagCtrlPage, self).__init__(
            codes, page=MODULE_PERF_DIAG_CTRL_PAGE, bank=0)

        self.fields[consts.TRANS_LOOPBACK_FIELD] = [
            NumberRegField(consts.LOOPBACK_CAPABILITY, self.getaddr(128), size=1),
            NumberRegField(consts.MEDIA_OUTPUT_LOOPBACK, offset=self.getaddr(180), size=1, ro=False),
            NumberRegField(consts.MEDIA_INPUT_LOOPBACK, offset=self.getaddr(181), size=1, ro=False),
            NumberRegField(consts.HOST_OUTPUT_LOOPBACK, self.getaddr(182), size=1, ro=False),
            NumberRegField(consts.HOST_INPUT_LOOPBACK, self.getaddr(183), size=1, ro=False),
        ]


# ---------------------------------------------------------------------------
# Page 0x2F -- VDM advertising / control
# ---------------------------------------------------------------------------
class CmisVdmAdvertisingCtrlPage(CmisPage):
    def __init__(self, codes):
        super(CmisVdmAdvertisingCtrlPage, self).__init__(
            codes, page=VDM_ADVERTISING_CTRL_PAGE, bank=0)

        self.fields[consts.TRANS_PM_FIELD] = [
            NumberRegField(consts.VDM_SUPPORTED_PAGE, self.getaddr(128),
                *(RegBitField(f"Bit{bit}", bit) for bit in range(0, 2))
            ),
            NumberRegField(consts.VDM_CONTROL, self.getaddr(144), size=1, ro=False),
            NumberRegField(consts.VDM_STATUS, self.getaddr(145),
                RegBitField(consts.VDM_UNFREEZE_DONE, 6),
                RegBitField(consts.VDM_FREEZE_DONE, 7),
            ),
        ]


# ---------------------------------------------------------------------------
# Page 0x9F -- CDB message page
# ---------------------------------------------------------------------------
class CmisCdbMessagePage(CmisPage):
    def __init__(self, codes):
        super(CmisCdbMessagePage, self).__init__(
            codes, page=CDB_MESSAGE_PAGE, bank=0)

        self.fields[consts.TRANS_CDB_FIELD] = [
            NumberRegField(consts.CDB_RPL_LENGTH, self.getaddr(134), size=1, ro=False),
            NumberRegField(consts.CDB_RPL_CHKCODE, self.getaddr(135), size=1, ro=False),
        ]
