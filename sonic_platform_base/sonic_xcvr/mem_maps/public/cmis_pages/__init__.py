"""
    cmis_pages package

    CMIS page-specific memory map classes
"""

from .base import CmisPage
from .cmis_page_consts import (
    CMIS_NUM_BANKED_PAGES,
    CMIS_NUM_NON_BANKED_PAGES,
    CMIS_EEPROM_PAGE_SIZE,
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
from .pg_00_administrative_lower import CmisAdministrativeLowerPage
from .pg_00_administrative_upper import CmisAdministrativeUpperPage
from .pg_01_advertising import CmisAdvertisingPage
from .pg_02_thresholds import CmisThresholdsPage
from .pg_10_lane_datapath_config import CmisLaneDatapathConfigPage
from .pg_11_lane_datapath_status import CmisLaneDatapathStatusPage
from .pg_12_tunable_laser_ctrl_status import CmisTunableLaserCtrlStatusPage
from .pg_13_module_perf_diag_ctrl import CmisModulePerfDiagCtrlPage
from .pg_2f_vdm_advertising_ctrl import CmisVdmAdvertisingCtrlPage
from .pg_9f_cdb_message import CmisCdbMessagePage

__all__ = [
    'CmisPage',
    'CMIS_NUM_BANKED_PAGES',
    'CMIS_NUM_NON_BANKED_PAGES',
    'CMIS_EEPROM_PAGE_SIZE',
    'ADMINISTRATIVE_PAGE',
    'ADVERTISING_PAGE',
    'THRESHOLDS_PAGE',
    'LANE_DATAPATH_CONFIG_PAGE',
    'LANE_DATAPATH_STATUS_PAGE',
    'TUNABLE_LASER_CTRL_STATUS_PAGE',
    'MODULE_PERF_DIAG_CTRL_PAGE',
    'VDM_ADVERTISING_CTRL_PAGE',
    'CDB_MESSAGE_PAGE',
    'CmisAdministrativeLowerPage',
    'CmisAdministrativeUpperPage',
    'CmisAdvertisingPage',
    'CmisThresholdsPage',
    'CmisLaneDatapathConfigPage',
    'CmisLaneDatapathStatusPage',
    'CmisTunableLaserCtrlStatusPage',
    'CmisModulePerfDiagCtrlPage',
    'CmisVdmAdvertisingCtrlPage',
    'CmisCdbMessagePage',
]

