"""
    cpo_cmis.py

    Implementation of XcvrMemMap for C-CMIS Rev 5.3 
"""

from ...fields.xcvr_field import (
    NumberRegField,
    RegGroupField
)
from ...fields import consts
from .cmis import CmisMemMap

PAGES_PER_BANK  = 240

# only needed by separate mode
class ElsfpCmisMemMap(CmisMemMap): 
    def __init__(self, codes, bank):
        return NotImplementedError
    def getaddr(self, page, offset, page_size=128):
        if 0 <= page <= 0xf:
            bank_id = 0
        else:
            bank_id = self._bank
        return (bank_id * PAGES_PER_BANK + page) * page_size + offset;


class BankedCmisMemMap(CmisMemMap):   
    def __init__(self, codes, bank):
        super().__init__(codes)
        self._bank = bank

    def getaddr(self, page, offset, page_size=128):
        if 0 <= page <= 0xf:
            bank_id = 0
        else:
            bank_id = self._bank
        return (bank_id * PAGES_PER_BANK + page) * page_size + offset