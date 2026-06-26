from ..public.cmis import CmisFlatMemMap
from ..public.cmis.pages import (
    CmisAdministrativeLowerPage,
    CmisAdministrativeUpperPage,
    CmisAdvertisingPage,
    CmisThresholdsPage,
)
from ..public.cmis.elsfp.pages import (
    ElsfpAdvertisementsFlagsCtrlPage,
    ElsfpSetpointsMonitorsPage,
)


class DavissonTh6ElsfpMemMap(CmisFlatMemMap):
    def __init__(self, codes, bank=0):
        # Bypass CmisFlatMemMap.__init__ so we don't register the default
        # CMIS flat memory pages — TH6 ELSFP relocates the CMIS pages onto
        # a contiguous 0xB0..0xB5 range.
        self._bank = bank
        super(CmisFlatMemMap, self).__init__(codes)
        self.pages = []

        self.add_pages(
            CmisAdministrativeLowerPage(codes, page=0xB0),
            CmisAdministrativeUpperPage(codes, page=0xB1),
            CmisAdvertisingPage(codes, page=0xB2),
            CmisThresholdsPage(codes, page=0xB3),
            ElsfpAdvertisementsFlagsCtrlPage(codes, bank=bank, page=0xB4),
            ElsfpSetpointsMonitorsPage(codes, bank=bank, page=0xB5),
        )
