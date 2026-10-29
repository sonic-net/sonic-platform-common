"""Legacy combined Bailly memory map and compatible endpoint-map imports."""
from ..public.cmis import CmisMemMap
from .bailly_oe import BaillyOeMemMap
from .bailly_elsfp import (
    BaillyElsfpMemMap,
    _BaillyRlmControlPage,
    _BaillyRlmInfoPage,
    _BaillyRlmThresholdPage,
)

__all__ = ["BaillyMemMap", "BaillyOeMemMap", "BaillyElsfpMemMap"]


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
