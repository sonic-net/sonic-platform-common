# =============================================================================
# TEMPORARY: scaffold derived from upstream PRs
#   nexthop-ai/sonic-platform-common#1 (Refactor CMIS memory map into pages)
#   nexthop-ai/sonic-platform-common#2 (ELSFP pages and Memory Map)
#
# Re-export surface for the page-class composition pattern. Upstream keeps
# each page in its own pg_NN_*.py file; downstream we collapse the standard
# CMIS pages into cmis_pages.py and the ELSFP pages into elsfp_pages.py
# (one file per logical memory map). When upstream merges, replace the two
# consolidated files with the upstream pg_NN_*.py files and update the
# imports below accordingly.
# =============================================================================
from .base import CmisPage
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
from .elsfp_pages import (
    ElsfpAdvertisementsFlagsCtrlPage,
    ElsfpSetpointsMonitorsPage,
)

__all__ = [
    "CmisPage",
    # Standard CMIS pages
    "CmisAdministrativeLowerPage",
    "CmisAdministrativeUpperPage",
    "CmisAdvertisingPage",
    "CmisThresholdsPage",
    "CmisLaneDatapathConfigPage",
    "CmisLaneDatapathStatusPage",
    "CmisTunableLaserCtrlStatusPage",
    "CmisModulePerfDiagCtrlPage",
    "CmisVdmAdvertisingCtrlPage",
    "CmisCdbMessagePage",
    # ELSFP pages
    "ElsfpAdvertisementsFlagsCtrlPage",
    "ElsfpSetpointsMonitorsPage",
]
