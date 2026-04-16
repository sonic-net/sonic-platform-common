"""
    cpo_xcvr_api_factory.py

    Factory class responsible for instantiating the appropriate XcvrApi
    implementation for a cpo module in SONiC
"""

from .xcvr_eeprom import XcvrEeprom
from .codes.public.cmis import CmisCodes
from .api.public.cmis import CmisApi
from .api.public.cpo_cmis import CpoCmisApi
from .mem_maps.public.cmis import CmisMemMap
from .mem_maps.public.cpo_cmis import BankedCmisMemMap
from .mem_maps.public.elsfp_cmis import ElsfpCmisMemMap
from xcvr_api_factory import XcvrApiFactory

class CpoXcvrApiFactory(XcvrApiFactory):
    def __init__(self, oe_reader, oe_writer, els_reader, els_writer, oe_bank=0, els_bank=0, cpo_eeprom_mode="joint"):
        self._oe_reader = oe_reader
        self._oe_writer = oe_writer
        self._oe_bank = oe_bank
        self._els_reader = els_reader
        self._els_writer = els_writer
        self._els_bank = els_bank
        self._cpo_eeprom_mode = cpo_eeprom_mode

    def _create_cpo_cmis_api(self):  # new
        els_xcvr_eeprom = None
        oe_xcvr_eeprom = XcvrEeprom(self._oe_reader, self._oe_writer, BankedCmisMemMap(CmisCodes, self._oe_bank)) # BankedCmisMemMap == jointCmisMemMap/OeCmisMemMap
        if self._cpo_eeprom_mode == "separate":
            els_xcvr_eeprom = XcvrEeprom(self._els_reader, self._els_writer, ElsfpCmisMemMap(CmisCodes, self._els_bank))
        api = CpoCmisApi(oe_xcvr_eeprom, els_xcvr_eeprom)
        return api
    def create_xcvr_api(self):
        return self._create_cpo_cmis_api()