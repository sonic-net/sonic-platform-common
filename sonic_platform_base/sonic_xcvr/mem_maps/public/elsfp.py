"""
    elsfp.py

    Implementation of XcvrMemMap for ELSFP
    Extends CMIS Rev 5.0 with ELSFP-specific pages 1Ah and 1Bh
"""

from .cmis import CmisFlatMemMap
from ...fields.xcvr_field import RegGroupField
from ...fields import consts
from ...fields import elsfp_consts

# Import CMIS page classes (excluding pages 10h, 11h, 12h, 13h)
from .cmis.pages import (
    CmisAdvertisingPage,
    CmisThresholdsPage,
    CmisVdmAdvertisingCtrlPage,
    CmisCdbMessagePage,
    ElsfpAdvertisementsFlagsCtrlPage,
    ElsfpSetpointsMonitorsPage,
)


def get_field_from_pages(field_name, *pages):
    fields = []
    for page in pages:
        if hasattr(page, 'fields') and field_name in page.fields:
            fields.extend(page.fields[field_name])
    return fields


class ElsfpMemMap(CmisFlatMemMap):
    """
    Memory map for ELSFP.

    Inherits CmisFlatMemMap (Page 00h) and adds:
    - Page 01h: CMIS Advertising
    - Page 02h: CMIS Thresholds
    - Page 1Ah: ELSFP Advertisements, Flags, and Controls
    - Page 1Bh: ELSFP Setpoints and Monitors
    - Page 2Fh: CMIS VDM Advertising/Control
    - Page 9Fh: CMIS CDB Message

    Excludes CMIS pages 10h, 11h, 12h, 13h (lane datapath and module control pages).
    """

    def __init__(self, codes, bank=0):
        # Initialize base CmisFlatMemMap (Page 00h lower and upper)
        super(ElsfpMemMap, self).__init__(codes, bank=bank)

        # ------------------------------------------------------------------
        # Initialize CMIS page instances relevant to ELSFP
        # ------------------------------------------------------------------
        self.advertising_page = CmisAdvertisingPage(codes, bank=bank)  # 0x01
        self.thresholds_page = CmisThresholdsPage(codes, bank=bank)  # 0x02
        self.performance_monitoring_page = CmisVdmAdvertisingCtrlPage(codes, bank=bank)  # 0x2F
        self.cdb_message_page = CmisCdbMessagePage(codes, bank=bank)  # 0x9F

        # ------------------------------------------------------------------
        # Initialize ELSFP-specific page instances
        # ------------------------------------------------------------------
        self.elsfp_advert_flags_ctrl_page = ElsfpAdvertisementsFlagsCtrlPage(codes, bank=bank)  # 0x1A
        self.elsfp_setpoints_mon_page = ElsfpSetpointsMonitorsPage(codes, bank=bank)  # 0x1B

        # ------------------------------------------------------------------
        # CMIS Field Groups (from pages 01h, 02h, 2Fh, 9Fh)
        # ------------------------------------------------------------------

        # Page 01h: Advertising
        self.ADVERTISING = RegGroupField(
            consts.ADVERTISING_FIELD,
            *get_field_from_pages(consts.ADVERTISING_FIELD, self.advertising_page)
        )

        self.MODULE_CHAR_ADVT = RegGroupField(
            consts.MODULE_CHAR_ADVT_FIELD,
            *get_field_from_pages(consts.MODULE_CHAR_ADVT_FIELD, self.advertising_page)
        )

        self.SIGNAL_INTEGRITY_CTRL_ADVT = RegGroupField(
            consts.SIGNAL_INTEGRITY_CTRL_ADVT_FIELD,
            *get_field_from_pages(consts.SIGNAL_INTEGRITY_CTRL_ADVT_FIELD, self.advertising_page)
        )

        # Page 02h: Thresholds
        self.THRESHOLDS = RegGroupField(
            consts.THRESHOLDS_FIELD,
            *get_field_from_pages(consts.THRESHOLDS_FIELD, self.thresholds_page)
        )

        # Page 2Fh: VDM Performance Monitoring
        self.TRANS_PM = RegGroupField(
            consts.TRANS_PM_FIELD,
            *get_field_from_pages(consts.TRANS_PM_FIELD, self.performance_monitoring_page)
        )

        # Page 9Fh: CDB Message (combined with page 01h fields)
        self.TRANS_CDB = RegGroupField(
            consts.TRANS_CDB_FIELD,
            *get_field_from_pages(consts.TRANS_CDB_FIELD, self.advertising_page, self.cdb_message_page)
        )

        # ------------------------------------------------------------------
        # ELSFP Page 1Ah Field Groups
        # ------------------------------------------------------------------

        # Module Advertisements (Bytes 128-164, Table 4)
        self.ELSFP_MODULE_ADVERTISEMENTS = RegGroupField(
            elsfp_consts.ELSFP_MODULE_ADVERTISEMENTS_FIELD,
            *get_field_from_pages(
                elsfp_consts.ELSFP_MODULE_ADVERTISEMENTS_FIELD,
                self.elsfp_advert_flags_ctrl_page
            )
        )

        # Lane Faults and Warnings (Bytes 165-181, Table 5)
        self.ELSFP_LANE_FAULTS_WARNINGS = RegGroupField(
            elsfp_consts.ELSFP_LANE_FAULTS_WARNINGS_FIELD,
            *get_field_from_pages(
                elsfp_consts.ELSFP_LANE_FAULTS_WARNINGS_FIELD,
                self.elsfp_advert_flags_ctrl_page
            )
        )

        # Laser Save/Restore (Bytes 182-185, Table 6)
        self.ELSFP_LASER_SAVE_RESTORE = RegGroupField(
            elsfp_consts.ELSFP_LASER_SAVE_RESTORE_FIELD,
            *get_field_from_pages(
                elsfp_consts.ELSFP_LASER_SAVE_RESTORE_FIELD,
                self.elsfp_advert_flags_ctrl_page
            )
        )

        # Alarms, Warnings, and Masks (Bytes 186-219, Table 7)
        self.ELSFP_ALARMS_WARNINGS_MASKS = RegGroupField(
            elsfp_consts.ELSFP_ALARMS_WARNINGS_MASKS_FIELD,
            *get_field_from_pages(
                elsfp_consts.ELSFP_ALARMS_WARNINGS_MASKS_FIELD,
                self.elsfp_advert_flags_ctrl_page
            )
        )

        # Lane Controls (Bytes 220-222, Table 8)
        self.ELSFP_LANE_CONTROLS = RegGroupField(
            elsfp_consts.ELSFP_LANE_CONTROLS_FIELD,
            *get_field_from_pages(
                elsfp_consts.ELSFP_LANE_CONTROLS_FIELD,
                self.elsfp_advert_flags_ctrl_page
            )
        )

        # Output Fiber Checked (Byte 223, Table 9)
        self.ELSFP_OUTPUT_FIBER_CHECKED = RegGroupField(
            elsfp_consts.ELSFP_OUTPUT_FIBER_CHECKED_FIELD,
            *get_field_from_pages(
                elsfp_consts.ELSFP_OUTPUT_FIBER_CHECKED_FIELD,
                self.elsfp_advert_flags_ctrl_page
            )
        )

        # Lane Mapping, Frequency, and Power (Bytes 224-255, Table 10)
        self.ELSFP_LANE_MAPPING_FREQ_POWER = RegGroupField(
            elsfp_consts.ELSFP_LANE_MAPPING_FREQ_POWER_FIELD,
            *get_field_from_pages(
                elsfp_consts.ELSFP_LANE_MAPPING_FREQ_POWER_FIELD,
                self.elsfp_advert_flags_ctrl_page
            )
        )

        # ------------------------------------------------------------------
        # ELSFP Page 1Bh Field Groups
        # ------------------------------------------------------------------

        # Setpoints (Bytes 128-183, Table 11)
        self.ELSFP_SETPOINTS = RegGroupField(
            elsfp_consts.ELSFP_SETPOINTS_FIELD,
            *get_field_from_pages(
                elsfp_consts.ELSFP_SETPOINTS_FIELD,
                self.elsfp_setpoints_mon_page
            )
        )

        # Monitors (Bytes 184-255, Table 12)
        self.ELSFP_MONITORS = RegGroupField(
            elsfp_consts.ELSFP_MONITORS_FIELD,
            *get_field_from_pages(
                elsfp_consts.ELSFP_MONITORS_FIELD,
                self.elsfp_setpoints_mon_page
            )
        )

