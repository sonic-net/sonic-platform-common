"""XcvrMemMap for the ELSFP (External Laser Source) device, per OIF-CMIS-ELSFP.

ELSFP is a resource module without datapath pages, so this does NOT inherit CmisMemMap.
Vendor-specific page additions belong on a vendor subclass.
"""

from .cmis import CmisFlatMemMap
from .cmis_pages import (
    ElsfpAdvertisementsFlagsCtrlPage,
    ElsfpSetpointsMonitorsPage,
)


class ElsfpCmisMemMap(CmisFlatMemMap):
    def _build_pages(self, codes):
        return [
            ElsfpAdvertisementsFlagsCtrlPage(codes, bank=self.bank),  # 0x1A
            ElsfpSetpointsMonitorsPage(codes, bank=self.bank),        # 0x1B
        ]
