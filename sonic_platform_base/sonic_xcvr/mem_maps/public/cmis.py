"""
    cmis.py

    Implementation of XcvrMemMap for CMIS Rev 5.0
"""

from ..xcvr_mem_map import XcvrMemMap
from ...fields.xcvr_field import (
    RegGroupField,
)
from ...fields import consts
from ...fields.consts import *
from .cmis_pages.base import CMIS_NUM_NON_BANKED_PAGES, CMIS_ARCH_PAGES, get_field_from_pages

# Import page classes
from .cmis_pages import (
    CmisAdministrativeLowerPage,
    CmisAdministrativeUpperPage,
    CmisAdvertisingPage,
    CmisThresholdsPage,
    CmisLaneDatapathConfigPage,
    CmisLaneDatapathStatusPage,
    CmisTunableLaserCtrlStatusPage,
    CmisModulePerfDiagCtrlPage,
    CmisVdmAdvertisingCtrlPage,
    CmisCdbMessagePage,
)

class CmisFlatMemMap(XcvrMemMap):
    """
    Memory map for CMIS flat memory (Lower page and Upper page 0h ONLY)
    """
    def __init__(self, codes, bank=0):
        self._bank = bank
        super(CmisFlatMemMap, self).__init__(codes)

        self.MGMT_CHARACTERISTICS = RegGroupField(consts.MGMT_CHAR_FIELD,
            NumberRegField(consts.MGMT_CHAR_MISC_FIELD, self.getaddr(0x0, 2),
                RegBitField(consts.FLAT_MEM_FIELD, 7)
            )
        )

        # This memmap should contain ONLY Lower page 00h and upper page 00h fields
        self.ADMIN_INFO = RegGroupField(consts.ADMIN_INFO_FIELD,
            CodeRegField(consts.ID_FIELD, self.getaddr(0x0, 0), self.codes.XCVR_IDENTIFIERS),
            CodeRegField(consts.ID_ABBRV_FIELD, self.getaddr(0x0, 128), self.codes.XCVR_IDENTIFIER_ABBRV),
            StringRegField(consts.VENDOR_NAME_FIELD, self.getaddr(0x0, 129), size=16),
            HexRegField(consts.VENDOR_OUI_FIELD, self.getaddr(0x0, 145), size=3),
            StringRegField(consts.VENDOR_PART_NO_FIELD, self.getaddr(0x0, 148), size=16),
            StringRegField(consts.VENDOR_REV_FIELD, self.getaddr(0x0, 164), size=2),
            StringRegField(consts.VENDOR_SERIAL_NO_FIELD, self.getaddr(0x0, 166), size=16),
            DateField(consts.VENDOR_DATE_FIELD, self.getaddr(0x0, 182), size=8),
            RegGroupField(consts.EXT_ID_FIELD,
                CodeRegField(consts.POWER_CLASS_FIELD, self.getaddr(0x0, 200), self.codes.POWER_CLASSES,
                    *(RegBitField("%s_%d" % (consts.POWER_CLASS_FIELD, bit), bit) for bit in range(5, 8))
                ),
                NumberRegField(consts.MAX_POWER_FIELD, self.getaddr(0x0, 201), scale=4.0),
            ),
            NumberRegField(consts.LEN_MULT_FIELD, self.getaddr(0x0, 202),
                *(RegBitField("%s_%d" % (consts.LEN_MULT_FIELD, bit), bit) for bit in range (6, 8))
            ),
            CableLenField(consts.LENGTH_ASSEMBLY_FIELD, self.getaddr(0x0, 202),
                *(RegBitField("%s_%d" % (consts.LENGTH_ASSEMBLY_FIELD, bit), bit) for bit in range(0, 6))
            ),

            CodeRegField(consts.CONNECTOR_FIELD, self.getaddr(0x0, 203), self.codes.CONNECTORS),

            RegGroupField(consts.APPLS_ADVT_FIELD,
                *(CodeRegField("%s_%d" % (consts.HOST_ELECTRICAL_INTERFACE, app), self.getaddr(0x0, 86 + 4 * (app - 1)),
                    self.codes.HOST_ELECTRICAL_INTERFACE) for app in range(1, 9)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_850NM, app), self.getaddr(0x0, 87 + 4 * (app- 1)),
                    self.codes.NM_850_MEDIA_INTERFACE) for app in range(1, 9)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_SM, app), self.getaddr(0x0, 87 + 4 * (app - 1)),
                    self.codes.SM_MEDIA_INTERFACE) for app in range(1, 9)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER, app), self.getaddr(0x0, 87 + 4 * (app - 1)),
                    self.codes.PASSIVE_COPPER_MEDIA_INTERFACE) for app in range(1, 9)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE, app), self.getaddr(0x0, 87 + 4 * (app - 1)),
                    self.codes.ACTIVE_CABLE_MEDIA_INTERFACE) for app in range(1, 9)),

                *(CodeRegField("%s_%d" % (consts.MODULE_MEDIA_INTERFACE_BASE_T, app), self.getaddr(0x0, 87 + 4 * (app - 1)),
                    self.codes.BASE_T_MEDIA_INTERFACE) for app in range(1, 9)),

                *(NumberRegField("%s_%d" % (consts.MEDIA_LANE_COUNT, lane), self.getaddr(0x0, 88 + 4 * (lane - 1)),
                    *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
                    ) for lane in range(1, 9)),

                *(NumberRegField("%s_%d" % (consts.HOST_LANE_COUNT, lane), self.getaddr(0x0, 88 + 4 * (lane - 1)),
                    *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
                    ) for lane in range(1, 9)),

                *(NumberRegField("%s_%d" % (consts.HOST_LANE_ASSIGNMENT_OPTION, lane), self.getaddr(0x0, 89 + 4 * (lane - 1)),
                    format="B", size=1) for lane in range(1, 9)),
            ),

            CodeRegField(consts.HOST_ELECTRICAL_INTERFACE, self.getaddr(0x0, 86), self.codes.HOST_ELECTRICAL_INTERFACE),
            CodeRegField(consts.MEDIA_TYPE_FIELD, self.getaddr(0x0, 85), self.codes.MODULE_MEDIA_TYPE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_850NM, self.getaddr(0x0, 87), self.codes.NM_850_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_SM, self.getaddr(0x0, 87), self.codes.SM_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER, self.getaddr(0x0, 87), self.codes.PASSIVE_COPPER_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE, self.getaddr(0x0, 87), self.codes.ACTIVE_CABLE_MEDIA_INTERFACE),
            CodeRegField(consts.MODULE_MEDIA_INTERFACE_BASE_T, self.getaddr(0x0, 87), self.codes.BASE_T_MEDIA_INTERFACE),
            NumberRegField(consts.MEDIA_LANE_COUNT, self.getaddr(0x0, 88),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
            ),
            NumberRegField(consts.HOST_LANE_COUNT, self.getaddr(0x0, 88),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
            ),
            NumberRegField(consts.HOST_LANE_ASSIGNMENT_OPTION, self.getaddr(0x0, 89), format="B", size=1),
            CodeRegField(consts.MEDIA_INTERFACE_TECH, self.getaddr(0x0, 212), self.codes.MEDIA_INTERFACE_TECH),
            NumberRegField(consts.CMIS_MAJOR_REVISION, self.getaddr(0x0, 1),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (4, 8))
            ),
            NumberRegField(consts.CMIS_MINOR_REVISION, self.getaddr(0x0, 1),
                *(RegBitField("Bit%d" % (bit), bit) for bit in range (0, 4))
            ),
            NumberRegField(consts.ACTIVE_FW_MAJOR_REV, self.getaddr(0x0, 39), format="B", size=1),
            NumberRegField(consts.ACTIVE_FW_MINOR_REV, self.getaddr(0x0, 40), format="B", size=1),
        )

        self.PAGE0_MODULE_LEVEL_MONITORS = RegGroupField(consts.MODULE_MONITORS_PAGE0_FIELD,
            NumberRegField(consts.TEMPERATURE_FIELD, self.getaddr(0x0, 14), size=2, format=">h", scale=256.0),
            NumberRegField(consts.VOLTAGE_FIELD, self.getaddr(0x0, 16), size=2, format=">H", scale=10000.0),
            NumberRegField(consts.AUX1_MON, self.getaddr(0x0, 18), format=">h", size=2),
            NumberRegField(consts.AUX2_MON, self.getaddr(0x0, 20), format=">h", size=2),
            NumberRegField(consts.AUX3_MON, self.getaddr(0x0, 22), format=">h", size=2),
            NumberRegField(consts.CUSTOM_MON, self.getaddr(0x0, 24), format=">H", size=2),
        )

        self.TRANS_MODULE_STATUS = RegGroupField(consts.TRANS_MODULE_STATUS_FIELD,
            CodeRegField(consts.MODULE_STATE, self.getaddr(0x0, 3), self.codes.MODULE_STATE,
                 *(RegBitField("Bit%d" % (bit), bit) for bit in range (1, 4))
            ),
            NumberRegField(consts.MODULE_FIRMWARE_FAULT_INFO, self.getaddr(0x0, 8), size=1),
            NumberRegField(consts.MODULE_FLAG_BYTE1, self.getaddr(0x0, 9), size=1),
            NumberRegField(consts.MODULE_FLAG_BYTE2, self.getaddr(0x0, 10), size=1),
            NumberRegField(consts.MODULE_FLAG_BYTE3, self.getaddr(0x0, 11), size=1),
            NumberRegField(consts.CDB1_STATUS, self.getaddr(0x0, 37), size=1),
            CodeRegField(consts.MODULE_FAULT_CAUSE, self.getaddr(0x0, 41), self.codes.MODULE_FAULT_CAUSE),
        )

        self.TRANS_CONFIG = RegGroupField(consts.TRANS_CONFIG_FIELD,
            NumberRegField(consts.MODULE_LEVEL_CONTROL, self.getaddr(0x0, 26), size=1, ro=False),
        )

    @property
    def bank(self):
        """Returns the bank number (read-only)."""
        return self._bank

    def getaddr(self, page, offset, page_size=128):
        """
        Calculate linear offset for CMIS memory map using instance's bank.

        For lower memory (page 0, offset < 128):
            linear_offset = offset

        For non-banked pages (00h-0Fh):
            bank is clamped to 0 because writing the BankSelect register is
            not necessary for these pages per CMIS 5.x.

        For paged memory:
            offset_in_paged_area = (page * page_size + offset) - 128
            bytes_per_bank = CMIS_ARCH_PAGES * page_size  (256 * 128 = 32KB)
            linear_offset = 128 + (bank * bytes_per_bank) + offset_in_paged_area

        Simplified:
            linear_offset = (bank * CMIS_ARCH_PAGES + page) * page_size + offset

        Note: Each bank is treated as a full 256-page (32KB) architectural block,
        even though only pages 10h-FFh (240 pages) are actually banked. This ensures
        proper alignment and matches the kernel driver behavior.
        """
        if page == 0 and offset < 128:
            # Lower memory - not affected by banking or paging.
            return offset

        # If we are accessing a non-banked page, there is no reason to set the bank
        # to a non-zero value. 
        bank = 0 if page < CMIS_NUM_NON_BANKED_PAGES else self.bank
        # Note: we consider CDB pages as non-banked here, though it
        # is possible to have multiple CDB instances exposed for a module where
        # each instance is accessible via bank selection.
        # This can be deleted once support for multiple CDB instances is added.
        bank = 0 if 0x9F <= page <= 0xAF else bank
        # For all paged memory (including bank 0), use the unified formula
        # that treats each bank as a 256-page (32KB) block
        return (bank * CMIS_ARCH_PAGES + page) * page_size + offset

class CmisMemMap(CmisFlatMemMap):
    def __init__(self, codes, bank=0):
        super(CmisMemMap, self).__init__(codes, bank=bank)

        # Initialize page instances
        self.advertising_page = CmisAdvertisingPage(codes, bank=bank)  # 0x01
        self.thresholds_page = CmisThresholdsPage(codes, bank=bank)  # 0x02
        self.datapath_control_page = CmisLaneDatapathConfigPage(codes, bank=bank)  # 0x10
        self.datapath_status_page = CmisLaneDatapathStatusPage(codes, bank=bank)  # 0x11
        self.tunable_module_monitors_page = CmisTunableLaserCtrlStatusPage(codes, bank=bank)  # 0x12
        self.loopback_page = CmisModulePerfDiagCtrlPage(codes, bank=bank)  # 0x13
        self.performance_monitoring_page = CmisVdmAdvertisingCtrlPage(codes, bank=bank)  # 0x2F
        self.cdb_message_page = CmisCdbMessagePage(codes, bank=bank)  # 0x9F

        # This memmap should contain ONLY upper page >= 01h fields
        self.ADVERTISING = RegGroupField(consts.ADVERTISING_FIELD,
            *get_field_from_pages(consts.ADVERTISING_FIELD, self.advertising_page, self.datapath_status_page)
        )

        self.MODULE_LEVEL_MONITORS = RegGroupField(consts.MODULE_MONITORS_FIELD,
            *get_field_from_pages(consts.MODULE_MONITORS_FIELD, self.tunable_module_monitors_page, self.advertising_page)
        )

        self.MODULE_CHAR_ADVT = RegGroupField(consts.MODULE_CHAR_ADVT_FIELD,
            *get_field_from_pages(consts.MODULE_CHAR_ADVT_FIELD, self.advertising_page)
        )

        self.THRESHOLDS = RegGroupField(consts.THRESHOLDS_FIELD,
            *get_field_from_pages(consts.THRESHOLDS_FIELD, self.thresholds_page)
        )

        self.LANE_DATAPATH_CTRL = RegGroupField(consts.LANE_DATAPATH_CTRL_FIELD,
            *get_field_from_pages(consts.LANE_DATAPATH_CTRL_FIELD, self.datapath_control_page)
        )

        self.TX_POWER_ALARM_FLAGS = RegGroupField(consts.TX_POWER_ALARM_FLAGS_FIELD,
            *get_field_from_pages(consts.TX_POWER_ALARM_FLAGS_FIELD, self.datapath_status_page)
        )

        self.TX_BIAS_ALARM_FLAGS = RegGroupField(consts.TX_BIAS_ALARM_FLAGS_FIELD,
            *get_field_from_pages(consts.TX_BIAS_ALARM_FLAGS_FIELD, self.datapath_status_page)
        )

        self.RX_POWER_ALARM_FLAGS = RegGroupField(consts.RX_POWER_ALARM_FLAGS_FIELD,
            *get_field_from_pages(consts.RX_POWER_ALARM_FLAGS_FIELD, self.datapath_status_page)
        )

        self.LANE_DATAPATH_STATUS = RegGroupField(consts.LANE_DATAPATH_STATUS_FIELD,
            *get_field_from_pages(consts.LANE_DATAPATH_STATUS_FIELD, self.datapath_status_page, self.tunable_module_monitors_page)
        )

        self.TRANS_LOOPBACK = RegGroupField(consts.TRANS_LOOPBACK_FIELD,
            *get_field_from_pages(consts.TRANS_LOOPBACK_FIELD, self.loopback_page)
        )

        self.TRANS_PM = RegGroupField(consts.TRANS_PM_FIELD,
            *get_field_from_pages(consts.TRANS_PM_FIELD, self.performance_monitoring_page)
        )

        self.TRANS_CDB = RegGroupField(consts.TRANS_CDB_FIELD,
            *get_field_from_pages(consts.TRANS_CDB_FIELD, self.advertising_page, self.cdb_message_page)
        )

        self.STAGED_CTRL0 = RegGroupField("%s_%d" % (consts.STAGED_CTRL_FIELD, 0),
            *get_field_from_pages("%s_%d" % (consts.STAGED_CTRL_FIELD, 0), self.datapath_control_page)
        )

        self.SIGNAL_INTEGRITY_CTRL_ADVT = RegGroupField(consts.SIGNAL_INTEGRITY_CTRL_ADVT_FIELD,
            *get_field_from_pages(consts.SIGNAL_INTEGRITY_CTRL_ADVT_FIELD, self.advertising_page)
        )

        self.STAGED_CTRL0_TX_RX_CTRL = RegGroupField(consts.STAGED_CTRL0_TX_RX_CTRL_FIELD,
            *get_field_from_pages(consts.STAGED_CTRL0_TX_RX_CTRL_FIELD, self.datapath_control_page)
        )
        # TODO: add remaining fields
