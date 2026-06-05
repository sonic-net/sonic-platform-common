"""
    bailly_mem_map.py

    Implementation of XcvrMemMap for Bailly extending CMIS Rev 5.0
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
from ...fields.bailly import bailly_consts

class _BaillyElsControlPage(CmisPage):
    """Bailly-specific fields on CMIS Page 0xB0h"""
    def __init__(self, codes, page=0xB0, bank=0):
        super().__init__(codes, page=page, bank=bank)

        self.fields[bailly_consts.CPO_INFO_FIELD] = [
            RegGroupField(bailly_consts.CPO_INFO_FIELD,
                CodeRegField(bailly_consts.CPO_IDENTIFIER, self.getaddr(128), codes.XCVR_IDENTIFIERS),
                NumberRegField(bailly_consts.CPO_REVISION, self.getaddr(129), format="B", size=1),
                NumberRegField(bailly_consts.LASER_GRID_AND_COUNT, self.getaddr(130), size=1, format="B"),
                CodeRegField(bailly_consts.LASER_WAVELENGTH_GRID, self.getaddr(130),
                    codes.LASER_WAVELENGTH_GRID,
                    RegBitField(bailly_consts.BIT4_FIELD, bitpos=4, ro=True)
                ),
                CodeRegField(bailly_consts.LASER_COUNT, self.getaddr(130),
                    codes.LASER_COUNT,
                    RegBitsField(bailly_consts.BITS0_3_FIELD, bitpos=0, size=4, ro=True)
                ),
            )
        ]

        self.fields[bailly_consts.LASER_CONTROL_FIELD] = [
            RegGroupField(bailly_consts.LASER_CONTROL_FIELD,
                NumberRegField(bailly_consts.MODULE_LOW_POWER_CONTROL, self.getaddr(132),
                    RegBitField(bailly_consts.BIT0_FIELD, bitpos=0, ro=False), size=1, ro=False
                ),
                NumberRegField(bailly_consts.LASER_DISABLE_CONTROL_7_0, self.getaddr(133), format="B", size=1, ro=False),
                NumberRegField(bailly_consts.LASER_DISABLE_CONTROL_15_8, self.getaddr(134), format="B", size=1, ro=False),
                RegGroupField(bailly_consts.LASER_DISABLE_CONTROL_FIELD,
                    *(NumberRegField(bailly_consts.LASER_DISABLE_CONTROL.format(laser),
                        self.getaddr(133 + laser // 8),
                        RegBitField(bailly_consts.BIT_FIELD.format(laser % 8), bitpos=laser % 8, ro=False),
                        size=1, ro=False)
                    for laser in range(0, 16))
                ),
            )
        ]

        self.fields[bailly_consts.LASER_STATUS_FIELD] = [
            RegGroupField(bailly_consts.LASER_STATUS_FIELD,
                NumberRegField(bailly_consts.MODULE_STATE_AND_INTERRUPT, self.getaddr(131), size=1, format="B"),
                CodeRegField(bailly_consts.MODULE_LOW_POWER_STATE, self.getaddr(131),
                    codes.POWER_MODE,
                    RegBitField(bailly_consts.BIT1_FIELD, bitpos=1)
                ),
                CodeRegField(bailly_consts.INTL_INTERRUPT_STATUS, self.getaddr(131),
                    codes.INTERRUPT_STATUS,
                    RegBitField(bailly_consts.BIT0_FIELD, bitpos=0)
                ),
                NumberRegField(bailly_consts.LASER_ACTIVE_STATUS_7_0, self.getaddr(135), format="B", size=1),
                NumberRegField(bailly_consts.LASER_ACTIVE_STATUS_15_8, self.getaddr(136), format="B", size=1),
                RegGroupField(bailly_consts.LASER_ACTIVE_STATUS_FIELD,
                    *(CodeRegField(bailly_consts.LASER_ACTIVE_STATUS.format(laser),
                        self.getaddr(135 + laser // 8),
                        codes.LASER_ACTIVE_STATUS,
                        RegBitField(bailly_consts.BIT_FIELD.format(laser % 8), bitpos=laser % 8),
                        size=1)
                    for laser in range(0, 16))
                ),
            )
        ]

        self.fields[bailly_consts.MODULE_ALARMS_FIELD] = [
            RegGroupField(bailly_consts.MODULE_ALARMS_FIELD,
                NumberRegField(bailly_consts.VCC_3V3_TEMPERATURE_WARNING_ALARM, self.getaddr(137), format="B", size=1),
                RegBitField(bailly_consts.TEMP_HIGH_ALARM_FLAG, offset=self.getaddr(137), bitpos=0),
                RegBitField(bailly_consts.TEMP_LOW_ALARM_FLAG, offset=self.getaddr(137), bitpos=1),
                RegBitField(bailly_consts.TEMP_HIGH_WARN_FLAG, offset=self.getaddr(137), bitpos=2),
                RegBitField(bailly_consts.TEMP_LOW_WARN_FLAG, offset=self.getaddr(137), bitpos=3),
                RegBitField(bailly_consts.VOLTAGE_HIGH_ALARM_FLAG, offset=self.getaddr(137), bitpos=4),
                RegBitField(bailly_consts.VOLTAGE_LOW_ALARM_FLAG, offset=self.getaddr(137), bitpos=5),
                RegBitField(bailly_consts.VOLTAGE_HIGH_WARN_FLAG, offset=self.getaddr(137), bitpos=6),
                RegBitField(bailly_consts.VOLTAGE_LOW_WARN_FLAG, offset=self.getaddr(137), bitpos=7),
                NumberRegField(bailly_consts.LASER_BIAS_WARNING_7_0, self.getaddr(138), format="B", size=1),
                NumberRegField(bailly_consts.LASER_BIAS_WARNING_15_8, self.getaddr(139), format="B", size=1),
                RegGroupField(bailly_consts.LASER_BIAS_WARNING_FIELD,
                    *(NumberRegField(bailly_consts.LASER_BIAS_WARNING.format(laser),
                        self.getaddr(138 + laser // 8),
                        RegBitField(bailly_consts.BIT_FIELD.format(laser % 8), bitpos=laser % 8),
                        size=1)
                    for laser in range(0, 16))
                ),
                NumberRegField(bailly_consts.LASER_BIAS_ALARM_7_0, self.getaddr(140), format="B", size=1),
                NumberRegField(bailly_consts.LASER_BIAS_ALARM_15_8, self.getaddr(141), format="B", size=1),
                RegGroupField(bailly_consts.LASER_BIAS_ALARM_FIELD,
                    *(NumberRegField(bailly_consts.LASER_BIAS_ALARM.format(laser),
                        self.getaddr(140 + laser // 8),
                        RegBitField(bailly_consts.BIT_FIELD.format(laser % 8), bitpos=laser % 8),
                        size=1)
                    for laser in range(0, 16))
                ),
            )
        ]

        self.fields[bailly_consts.CPO_MODULE_MONITORS_FIELD] = [
            RegGroupField(bailly_consts.CPO_MODULE_MONITORS_FIELD,
                NumberRegField(bailly_consts.MODULE_TEMPERATURE_MONITOR_MSB, self.getaddr(150), format="B", size=1),
                NumberRegField(bailly_consts.MODULE_TEMPERATURE_MONITOR_LSB, self.getaddr(151), format="B", size=1),
                NumberRegField(bailly_consts.MODULE_TEMPERATURE_MONITOR, self.getaddr(150), size=2, format=">h", scale=256.0),
                NumberRegField(bailly_consts.MODULE_SUPPLY_VOLTAGE_MONITOR_MSB, self.getaddr(152), format="B", size=1),
                NumberRegField(bailly_consts.MODULE_SUPPLY_VOLTAGE_MONITOR_LSB, self.getaddr(153), format="B", size=1),
                NumberRegField(bailly_consts.MODULE_SUPPLY_VOLTAGE_MONITOR, self.getaddr(152), size=2, format=">H", scale=10000.0),
                RegGroupField(bailly_consts.LASER_CURRENT_MONITOR_FIELD,
                    *(RegGroupField(bailly_consts.LASER_CURRENT_MONITOR.format(laser),
                        NumberRegField(bailly_consts.LASER_CURRENT_MONITOR_MSB.format(laser), self.getaddr(154 + 2 * laser), format="B", size=1),
                        NumberRegField(bailly_consts.LASER_CURRENT_MONITOR_LSB.format(laser), self.getaddr(155 + 2 * laser), format="B", size=1),
                        NumberRegField(bailly_consts.LASER_CURRENT_MONITOR.format(laser), self.getaddr(154 + 2 * laser), size=2, format=">H", scale=10.0),
                    ) for laser in range(0, 16))
                ),
                RegGroupField(bailly_consts.LASER_VOLTAGE_MONITOR_FIELD,
                    *(NumberRegField(bailly_consts.LASER_VOLTAGE_MONITOR.format(laser),
                        self.getaddr(186 + laser), size=1, format="B", scale=100.0)
                    for laser in range(0, 16))
                ),
                RegGroupField(bailly_consts.LASER_OPTICAL_POWER_MONITOR_FIELD,
                    *(RegGroupField(bailly_consts.LASER_OPTICAL_POWER_MONITOR.format(laser),
                        NumberRegField(bailly_consts.LASER_OPTICAL_POWER_MONITOR_MSB.format(laser), self.getaddr(203 + 2 * laser), format="B", size=1),
                        NumberRegField(bailly_consts.LASER_OPTICAL_POWER_MONITOR_LSB.format(laser), self.getaddr(204 + 2 * laser), format="B", size=1),
                        NumberRegField(bailly_consts.LASER_OPTICAL_POWER_MONITOR.format(laser), self.getaddr(203 + 2 * laser), size=2, format=">H", scale=100.0),
                    ) for laser in range(0, 16))
                ),
                NumberRegField(bailly_consts.TEC_CURRENT_MONITOR_MSB, self.getaddr(250), format="B", size=1),
                NumberRegField(bailly_consts.TEC_CURRENT_MONITOR_LSB, self.getaddr(251), format="B", size=1),
                NumberRegField(bailly_consts.TEC_CURRENT_MONITOR, self.getaddr(250), size=2, format=">h", scale=327.67),
            )
        ]

class _BaillyElsInfoPage(CmisPage):
    """Bailly-specific fields on CMIS Page 0xB1h"""
    def __init__(self, codes, page=0xB1, bank=0):
        super().__init__(codes, page=page, bank=bank)

        self.fields[bailly_consts.CPO_VENDOR_INFO_FIELD] = [
            RegGroupField(bailly_consts.CPO_VENDOR_INFO_FIELD,
                StringRegField(bailly_consts.VENDOR_NAME_ASCII_FIELD, self.getaddr(129), size=16),
                HexRegField(bailly_consts.VENDOR_OUI_HEX_FIELD, self.getaddr(145), size=3),
                StringRegField(bailly_consts.VENDOR_PART_NUMBER_ASCII_FIELD, self.getaddr(148), size=16),
                StringRegField(bailly_consts.VENDOR_REVISION_ASCII_FIELD, self.getaddr(164), size=2),
                StringRegField(bailly_consts.VENDOR_SERIAL_NUMBER_ASCII_FIELD, self.getaddr(166), size=16),
                StringRegField(bailly_consts.DATE_CODE_YY_FIELD, self.getaddr(182), size=2),
                StringRegField(bailly_consts.DATE_CODE_MM_FIELD, self.getaddr(184), size=2),
                StringRegField(bailly_consts.DATE_CODE_DD_FIELD, self.getaddr(186), size=2),
                StringRegField(bailly_consts.DATE_CODE_LOT_FIELD, self.getaddr(188), size=2),
                DateField(bailly_consts.DATE_CODE_FIELD, self.getaddr(182), size=8),
                StringRegField(bailly_consts.CLEI_CODE_FIELD, self.getaddr(190), size=10),
                NumberRegField(bailly_consts.MAX_POWER_CONSUMPTION_FIELD, self.getaddr(200), format="B", size=1, scale=4.0),
                NumberRegField(bailly_consts.CHECKSUM_FIELD, self.getaddr(251), format="B", size=1),
            )
        ]

class _BaillyElsThresholdPage(CmisPage):
    """Bailly-specific fields on CMIS Page 0xB2h"""
    def __init__(self, codes, page=0xB2, bank=0):
        super().__init__(codes, page=page, bank=bank)

        self.fields[bailly_consts.LASER_POWER_MODE_CONTROL_FIELD] = [
            RegGroupField(bailly_consts.LASER_POWER_MODE_CONTROL_FIELD,
                NumberRegField(bailly_consts.LASER_POWER_MODE_CONTROL_BITS_FIELD, self.getaddr(128), format="B", size=1, ro=False,
                    *(RegBitField(bailly_consts.CHANNEL_LASER_POWER_MODE_ENABLE.format(channel), bitpos=channel, ro=False)
                    for channel in range(0, 8))
                ),
                RegGroupField(bailly_consts.LASER_POWER_MODE_CONTROL_CHANNELS_FIELD,
                    *(NumberRegField(bailly_consts.CHANNEL_LASER_POWER_MODE_ENABLE.format(channel),
                        self.getaddr(128),
                        RegBitField(bailly_consts.BIT_FIELD.format(channel), bitpos=channel, ro=False),
                        size=1, ro=False)
                    for channel in range(0, 8))
                ),
                RegGroupField(bailly_consts.THRESHOLD_VALUES_FIELD,
                    NumberRegField(bailly_consts.TEMP_HIGH_ALARM_MSB_FIELD, self.getaddr(162), format="B", size=1),
                    NumberRegField(bailly_consts.TEMP_HIGH_ALARM_LSB_FIELD, self.getaddr(163), format="B", size=1),
                    NumberRegField(bailly_consts.TEMP_LOW_ALARM_MSB_FIELD, self.getaddr(164), format="B", size=1),
                    NumberRegField(bailly_consts.TEMP_LOW_ALARM_LSB_FIELD, self.getaddr(165), format="B", size=1),
                    NumberRegField(bailly_consts.TEMP_HIGH_WARNING_MSB_FIELD, self.getaddr(166), format="B", size=1),
                    NumberRegField(bailly_consts.TEMP_HIGH_WARNING_LSB_FIELD, self.getaddr(167), format="B", size=1),
                    NumberRegField(bailly_consts.TEMP_LOW_WARNING_MSB_FIELD, self.getaddr(168), format="B", size=1),
                    NumberRegField(bailly_consts.TEMP_LOW_WARNING_LSB_FIELD, self.getaddr(169), format="B", size=1),
                    NumberRegField(bailly_consts.VCC_HIGH_ALARM_MSB_FIELD, self.getaddr(170), format="B", size=1),
                    NumberRegField(bailly_consts.VCC_HIGH_ALARM_LSB_FIELD, self.getaddr(171), format="B", size=1),
                    NumberRegField(bailly_consts.VCC_LOW_ALARM_MSB_FIELD, self.getaddr(172), format="B", size=1),
                    NumberRegField(bailly_consts.VCC_LOW_ALARM_LSB_FIELD, self.getaddr(173), format="B", size=1),
                    NumberRegField(bailly_consts.VCC_HIGH_WARNING_MSB_FIELD, self.getaddr(174), format="B", size=1),
                    NumberRegField(bailly_consts.VCC_HIGH_WARNING_LSB_FIELD, self.getaddr(175), format="B", size=1),
                    NumberRegField(bailly_consts.VCC_LOW_WARNING_MSB_FIELD, self.getaddr(176), format="B", size=1),
                    NumberRegField(bailly_consts.VCC_LOW_WARNING_LSB_FIELD, self.getaddr(177), format="B", size=1),
                    NumberRegField(bailly_consts.TX_POWER_HIGH_ALARM_MSB_FIELD, self.getaddr(178), format="B", size=1),
                    NumberRegField(bailly_consts.TX_POWER_HIGH_ALARM_LSB_FIELD, self.getaddr(179), format="B", size=1),
                    NumberRegField(bailly_consts.TX_POWER_LOW_ALARM_MSB_FIELD, self.getaddr(180), format="B", size=1),
                    NumberRegField(bailly_consts.TX_POWER_LOW_ALARM_LSB_FIELD, self.getaddr(181), format="B", size=1),
                    NumberRegField(bailly_consts.TX_POWER_HIGH_WARNING_MSB_FIELD, self.getaddr(182), format="B", size=1),
                    NumberRegField(bailly_consts.TX_POWER_HIGH_WARNING_LSB_FIELD, self.getaddr(183), format="B", size=1),
                    NumberRegField(bailly_consts.TX_POWER_LOW_WARNING_MSB_FIELD, self.getaddr(184), format="B", size=1),
                    NumberRegField(bailly_consts.TX_POWER_LOW_WARNING_LSB_FIELD, self.getaddr(185), format="B", size=1),
                    NumberRegField(bailly_consts.TX_BIAS_HIGH_ALARM_MSB_FIELD, self.getaddr(186), format="B", size=1),
                    NumberRegField(bailly_consts.TX_BIAS_HIGH_ALARM_LSB_FIELD, self.getaddr(187), format="B", size=1),
                    NumberRegField(bailly_consts.TX_BIAS_HIGH_WARNING_MSB_FIELD, self.getaddr(188), format="B", size=1),
                    NumberRegField(bailly_consts.TX_BIAS_HIGH_WARNING_LSB_FIELD, self.getaddr(189), format="B", size=1),
                ),
                NumberRegField(bailly_consts.CHECKSUM_FIELD, self.getaddr(255), format="B", size=1),
            )
        ]

# -------------------------- Bailly Main Memory Map Class --------------------------
class BaillyMemMap(CmisMemMap):
    def __init__(self, codes, bank=0, base_page=0):
        self._bank = bank
        self._base_page = base_page
        super().__init__(codes, bank)

        ELS_CONTROL_PAGE = 0xB0
        ELS_INFO_PAGE = 0xB1
        ELS_THRESHOLD_PAGE = 0xB2
    
        self.add_pages(
            _BaillyElsControlPage(codes, ELS_CONTROL_PAGE + base_page),
            _BaillyElsInfoPage(codes, ELS_INFO_PAGE + base_page),
            _BaillyElsThresholdPage(codes, ELS_THRESHOLD_PAGE + base_page),
        )
