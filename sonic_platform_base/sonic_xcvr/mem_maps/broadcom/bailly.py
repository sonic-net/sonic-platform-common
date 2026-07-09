"""
    bailly.py

    Implementation of XcvrMemMap for Bailly extending CMIS
"""

from ..public.cmis import CmisMemMap
from ..public.cmis.pages.page import CmisPage
from ...fields.xcvr_field import (
    CodeRegField,
    DateField,
    HexRegField,
    NumberRegField,
    RegBitField,
    RegBitsField,
    RegGroupField,
    StringRegField,
)
from ...fields.consts import *
from ...fields.broadcom import bailly


class _BaillyRlmControlPage(CmisPage):
    """Bailly-specific fields on CMIS Page 0xB0h"""

    def __init__(self, codes, page=0xB0, bank=0):
        super().__init__(codes, page=page, bank=bank)

        self.fields[bailly.CPO_INFO_FIELD] = [
            RegGroupField(bailly.CPO_INFO_FIELD,
                CodeRegField(bailly.CPO_IDENTIFIER, self.getaddr(128), codes.XCVR_IDENTIFIERS),
                NumberRegField(bailly.CPO_REVISION, self.getaddr(129), format="B", size=1),
                NumberRegField(bailly.LASER_GRID_AND_COUNT, self.getaddr(130), size=1, format="B"),
                CodeRegField(bailly.LASER_WAVELENGTH_GRID, self.getaddr(130),
                    codes.LASER_WAVELENGTH_GRID,
                    RegBitField(bailly.BIT4_FIELD, bitpos=4, ro=True)
                ),
                CodeRegField(bailly.LASER_COUNT, self.getaddr(130),
                    codes.LASER_COUNT,
                    RegBitsField(bailly.BITS0_3_FIELD, bitpos=0, size=4, ro=True)
                ),
            )
        ]

        self.fields[bailly.LASER_CONTROL_FIELD] = [
            RegGroupField(bailly.LASER_CONTROL_FIELD,
                CodeRegField(bailly.MODULE_LOW_POWER_CONTROL, self.getaddr(132),
                    codes.POWER_MODE,
                    RegBitField(bailly.BIT0_FIELD, bitpos=0, ro=False)
                ),
                NumberRegField(bailly.LASER_DISABLE_CONTROL_7_0, self.getaddr(133), format="B", size=1, ro=False),
                NumberRegField(bailly.LASER_DISABLE_CONTROL_15_8, self.getaddr(134), format="B", size=1, ro=False),
                RegGroupField(bailly.LASER_DISABLE_CONTROL_FIELD,
                    *(CodeRegField(bailly.LASER_DISABLE_CONTROL.format(laser),
                        self.getaddr(133 + laser // 8),
                        codes.LASER_DISABLE_CONTROL,
                        RegBitField(bailly.BIT_FIELD.format(laser % 8), bitpos=laser % 8, ro=False),
                    )
                    for laser in range(0, 16))
                ),
            )
        ]

        self.fields[bailly.LASER_STATUS_FIELD] = [
            RegGroupField(bailly.LASER_STATUS_FIELD,
                NumberRegField(bailly.MODULE_STATE_AND_INTERRUPT, self.getaddr(131), size=1, format="B"),
                CodeRegField(bailly.MODULE_LOW_POWER_STATE, self.getaddr(131),
                    codes.POWER_MODE,
                    RegBitField(bailly.BIT1_FIELD, bitpos=1)
                ),
                CodeRegField(bailly.INTL_INTERRUPT_STATUS, self.getaddr(131),
                    codes.INTERRUPT_STATUS,
                    RegBitField(bailly.BIT0_FIELD, bitpos=0)
                ),
                NumberRegField(bailly.LASER_ACTIVE_STATUS_7_0, self.getaddr(135), format="B", size=1),
                NumberRegField(bailly.LASER_ACTIVE_STATUS_15_8, self.getaddr(136), format="B", size=1),
                RegGroupField(bailly.LASER_ACTIVE_STATUS_FIELD,
                    *(CodeRegField(bailly.LASER_ACTIVE_STATUS.format(laser),
                        self.getaddr(135 + laser // 8),
                        codes.LASER_ACTIVE_STATUS,
                        RegBitField(bailly.BIT_FIELD.format(laser % 8), bitpos=laser % 8),
                        size=1)
                    for laser in range(0, 16))
                ),
            )
        ]

        self.fields[bailly.MODULE_ALARMS_FIELD] = [
            RegGroupField(bailly.MODULE_ALARMS_FIELD,
                NumberRegField(bailly.VCC_3V3_TEMPERATURE_WARNING_ALARM, self.getaddr(137), format="B", size=1),
                RegBitField(bailly.TEMP_HIGH_ALARM_FLAG, offset=self.getaddr(137), bitpos=0),
                RegBitField(bailly.TEMP_LOW_ALARM_FLAG, offset=self.getaddr(137), bitpos=1),
                RegBitField(bailly.TEMP_HIGH_WARN_FLAG, offset=self.getaddr(137), bitpos=2),
                RegBitField(bailly.TEMP_LOW_WARN_FLAG, offset=self.getaddr(137), bitpos=3),
                RegBitField(bailly.VOLTAGE_HIGH_ALARM_FLAG, offset=self.getaddr(137), bitpos=4),
                RegBitField(bailly.VOLTAGE_LOW_ALARM_FLAG, offset=self.getaddr(137), bitpos=5),
                RegBitField(bailly.VOLTAGE_HIGH_WARN_FLAG, offset=self.getaddr(137), bitpos=6),
                RegBitField(bailly.VOLTAGE_LOW_WARN_FLAG, offset=self.getaddr(137), bitpos=7),
                NumberRegField(bailly.LASER_BIAS_WARNING_7_0, self.getaddr(138), format="B", size=1),
                NumberRegField(bailly.LASER_BIAS_WARNING_15_8, self.getaddr(139), format="B", size=1),
                RegGroupField(bailly.LASER_BIAS_WARNING_FIELD,
                    *(NumberRegField(bailly.LASER_BIAS_WARNING.format(laser),
                        self.getaddr(138 + laser // 8),
                        RegBitField(bailly.BIT_FIELD.format(laser % 8), bitpos=laser % 8),
                        size=1)
                    for laser in range(0, 16))
                ),
                NumberRegField(bailly.LASER_BIAS_ALARM_7_0, self.getaddr(140), format="B", size=1),
                NumberRegField(bailly.LASER_BIAS_ALARM_15_8, self.getaddr(141), format="B", size=1),
                RegGroupField(bailly.LASER_BIAS_ALARM_FIELD,
                    *(NumberRegField(bailly.LASER_BIAS_ALARM.format(laser),
                        self.getaddr(140 + laser // 8),
                        RegBitField(bailly.BIT_FIELD.format(laser % 8), bitpos=laser % 8),
                        size=1)
                    for laser in range(0, 16))
                ),
            )
        ]

        self.fields[bailly.CPO_MODULE_MONITORS_FIELD] = [
            RegGroupField(bailly.CPO_MODULE_MONITORS_FIELD,
                NumberRegField(bailly.MODULE_TEMPERATURE_MONITOR, self.getaddr(150), size=2, format=">h", scale=256.0),
                NumberRegField(bailly.MODULE_SUPPLY_VOLTAGE_MONITOR, self.getaddr(152), size=2, format=">H", scale=10000.0),
                RegGroupField(bailly.LASER_CURRENT_MONITOR_FIELD,
                    *(NumberRegField(bailly.LASER_CURRENT_MONITOR.format(laser),
                        self.getaddr(154 + 2 * laser), size=2, format=">H", scale=100.0)
                    for laser in range(0, 16))
                ),
                RegGroupField(bailly.LASER_VOLTAGE_MONITOR_FIELD,
                    *(NumberRegField(bailly.LASER_VOLTAGE_MONITOR.format(laser),
                        self.getaddr(186 + laser), size=1, format="B", scale=100.0)
                    for laser in range(0, 16))
                ),
                RegGroupField(bailly.LASER_OPTICAL_POWER_MONITOR_FIELD,
                    *(NumberRegField(bailly.LASER_OPTICAL_POWER_MONITOR.format(laser),
                        self.getaddr(203 + 2 * laser), size=2, format=">H", scale=100.0)
                    for laser in range(0, 16))
                ),
                NumberRegField(bailly.TEC_CURRENT_MONITOR, self.getaddr(250), size=2, format=">h", scale=327.67),
            )
        ]


class _BaillyRlmInfoPage(CmisPage):
    """Bailly-specific fields on CMIS Page 0xB1h"""

    def __init__(self, codes, page=0xB1, bank=0):
        super().__init__(codes, page=page, bank=bank)

        self.fields[bailly.CPO_VENDOR_INFO_FIELD] = [
            RegGroupField(bailly.CPO_VENDOR_INFO_FIELD,
                StringRegField(bailly.VENDOR_NAME_ASCII_FIELD, self.getaddr(129), size=16),
                HexRegField(bailly.VENDOR_OUI_HEX_FIELD, self.getaddr(145), size=3),
                StringRegField(bailly.VENDOR_PART_NUMBER_ASCII_FIELD, self.getaddr(148), size=16),
                StringRegField(bailly.VENDOR_REVISION_ASCII_FIELD, self.getaddr(164), size=2),
                StringRegField(bailly.VENDOR_SERIAL_NUMBER_ASCII_FIELD, self.getaddr(166), size=16),
                StringRegField(bailly.DATE_CODE_YY_FIELD, self.getaddr(182), size=2),
                StringRegField(bailly.DATE_CODE_MM_FIELD, self.getaddr(184), size=2),
                StringRegField(bailly.DATE_CODE_DD_FIELD, self.getaddr(186), size=2),
                StringRegField(bailly.DATE_CODE_LOT_FIELD, self.getaddr(188), size=2),
                DateField(bailly.DATE_CODE_FIELD, self.getaddr(182), size=8),
                StringRegField(bailly.CLEI_CODE_FIELD, self.getaddr(190), size=10),
                NumberRegField(bailly.MAX_POWER_CONSUMPTION_FIELD, self.getaddr(200), format="B", size=1, scale=4.0),
                NumberRegField(bailly.CHECKSUM_FIELD, self.getaddr(251), format="B", size=1),
            )
        ]


class _BaillyRlmThresholdPage(CmisPage):
    """Bailly-specific fields on CMIS Page 0xB2h"""

    def __init__(self, codes, page=0xB2, bank=0):
        super().__init__(codes, page=page, bank=bank)

        self.fields[bailly.LASER_POWER_MODE_CONTROL_FIELD] = [
            RegGroupField(bailly.LASER_POWER_MODE_CONTROL_FIELD,
                NumberRegField(bailly.LASER_POWER_MODE_CONTROL_BITS_FIELD, self.getaddr(128), format="B", size=1, ro=False,
                    *(RegBitField(bailly.CHANNEL_LASER_POWER_MODE_ENABLE.format(channel), bitpos=channel, ro=False)
                    for channel in range(0, 8))
                ),
                RegGroupField(bailly.LASER_POWER_MODE_CONTROL_CHANNELS_FIELD,
                    *(CodeRegField(bailly.CHANNEL_LASER_POWER_MODE_ENABLE.format(channel),
                        self.getaddr(128),
                        codes.LASER_POWER_MODE_ENABLE,
                        RegBitField(bailly.BIT_FIELD.format(channel), bitpos=channel, ro=False),
                    )
                    for channel in range(0, 8))
                ),
                RegGroupField(bailly.THRESHOLD_VALUES_FIELD,
                    NumberRegField(bailly.RLM_TEMP_HIGH_ALARM_FIELD, self.getaddr(162), size=2, format=">h", scale=256.0),
                    NumberRegField(bailly.RLM_TEMP_LOW_ALARM_FIELD, self.getaddr(164), size=2, format=">h", scale=256.0),
                    NumberRegField(bailly.RLM_TEMP_HIGH_WARNING_FIELD, self.getaddr(166), size=2, format=">h", scale=256.0),
                    NumberRegField(bailly.RLM_TEMP_LOW_WARNING_FIELD, self.getaddr(168), size=2, format=">h", scale=256.0),
                    NumberRegField(bailly.RLM_VCC_HIGH_ALARM_FIELD, self.getaddr(170), size=2, format=">H", scale=10000.0),
                    NumberRegField(bailly.RLM_VCC_LOW_ALARM_FIELD, self.getaddr(172), size=2, format=">H", scale=10000.0),
                    NumberRegField(bailly.RLM_VCC_HIGH_WARNING_FIELD, self.getaddr(174), size=2, format=">H", scale=10000.0),
                    NumberRegField(bailly.RLM_VCC_LOW_WARNING_FIELD, self.getaddr(176), size=2, format=">H", scale=10000.0),
                    NumberRegField(bailly.RLM_TX_POWER_HIGH_ALARM_FIELD, self.getaddr(178), size=2, format=">H", scale=100.0),
                    NumberRegField(bailly.RLM_TX_POWER_LOW_ALARM_FIELD, self.getaddr(180), size=2, format=">H", scale=100.0),
                    NumberRegField(bailly.RLM_TX_POWER_HIGH_WARNING_FIELD, self.getaddr(182), size=2, format=">H", scale=100.0),
                    NumberRegField(bailly.RLM_TX_POWER_LOW_WARNING_FIELD, self.getaddr(184), size=2, format=">H", scale=100.0),
                    NumberRegField(bailly.RLM_TX_BIAS_HIGH_ALARM_FIELD, self.getaddr(186), size=2, format=">H", scale=100.0),
                    NumberRegField(bailly.RLM_TX_BIAS_HIGH_WARNING_FIELD, self.getaddr(188), size=2, format=">H", scale=100.0),
                ),
                NumberRegField(bailly.CHECKSUM_FIELD, self.getaddr(255), format="B", size=1),
            )
        ]


class BaillyMemMap(CmisMemMap):
    def __init__(self, codes, bank=0, base_page=0):
        self._bank = bank
        self._base_page = base_page
        super().__init__(codes, bank)

        RLM_CONTROL_PAGE = 0xB0
        RLM_INFO_PAGE = 0xB1
        RLM_THRESHOLD_PAGE = 0xB2

        self.add_pages(
            _BaillyRlmControlPage(codes, RLM_CONTROL_PAGE + base_page),
            _BaillyRlmInfoPage(codes, RLM_INFO_PAGE + base_page),
            _BaillyRlmThresholdPage(codes, RLM_THRESHOLD_PAGE + base_page),
        )
