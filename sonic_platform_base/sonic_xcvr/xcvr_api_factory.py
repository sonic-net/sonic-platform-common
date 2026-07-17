"""
    xcvr_api_factory.py

    Factory class responsible for instantiating the appropriate XcvrApi
    implementation for a xcvr module in SONiC
"""

import logging
import re
from .xcvr_eeprom import XcvrEeprom
from .eeprom_rw import ModuleEepromLowerMemoryInfo

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
# TODO: remove the following imports
from .codes.public.cmis import CmisCodes
from .api.public.cmis import CmisApi
from .api.public.c_cmis import CCmisApi
from .mem_maps.public.cmis import CmisMemMap
from .mem_maps.public.cmis.c_cmis import CCmisMemMap

from .codes.credo.aec_800g import CredoAec800gCodes
from .api.credo.aec_800g import CredoAec800gApi
from .mem_maps.credo.aec_800g import CredoAec800gMemMap

from .api.innolight.fr_800g import CmisFr800gApi
from .api.hisense.aoc_2x100g import CmisAocSingleBankApi

from .api.amphenol.backplane import AmphBackplaneImpl
from .mem_maps.amphenol.backplane import AmphBackplaneMemMap
from .codes.amphenol.backplane import AmphBackplaneCodes

from .mem_maps.public.elsfp_cmis import ElsfpCmisMemMap
from .api.public.elsfp_cmis import ElsfpCmisApi
from .codes.nvidia.cpo_oe import NvidiaCpoOeCodes
from .mem_maps.nvidia.cpo_oe import NvidiaCpoOeMemMap
from .api.nvidia.cpo_oe import NvidiaCpoOeCmisApi
from .cdb.nvidia.cpo_oe_codes import NvidiaCpoOeCdbCodes
from .cdb.nvidia.cpo_oe_memmap import NvidiaCpoOeCdbMemMap

from .codes.nvidia.cpo_els import NvidiaCpoElsCodes
from .mem_maps.nvidia.cpo_els import (
    NvidiaCpoElsCmisMemMap, 
    NVIDIA_ELS_IDENTITY_PAGE as NVIDIA_ELS_ADMIN_UPPER_PAGE,
)
from .api.nvidia.cpo_els import NvidiaCpoElsCmisApi
from .cdb.nvidia.cpo_els_codes import NvidiaCpoElsCdbCodes
from .cdb.nvidia.cpo_els_memmap import NvidiaCpoElsCdbMemMap

from .api.public.cpo import CpoApi

from .codes.public.sff8436 import Sff8436Codes
from .api.public.sff8436 import Sff8436Api
from .mem_maps.public.sff8436 import Sff8436MemMap

from .codes.public.sff8636 import Sff8636Codes
from .api.public.sff8636 import Sff8636Api
from .mem_maps.public.sff8636 import Sff8636MemMap

from .codes.public.sff8472 import Sff8472Codes
from .api.public.sff8472 import Sff8472Api
from .mem_maps.public.sff8472 import Sff8472MemMap

CREDO_800G_AEC_VENDOR_PN_LIST = ["CAC81X321M2MC1MS", "CAC815321M2MC1MS", "CAC82X321M2MC1MS"]
INL_800G_VENDOR_PN_LIST = ["T-DL8CNT-NCI", "T-DH8CNT-NCI", "T-DH8CNT-N00", "T-DP4CNH-NCI", "T-DP8CNT-NNO",
                           "T-DP8CNH-NNO", "T-DC8CNT-NNO", "T-DP8CNL-NNO", "T-OL8CNT-N00", "T-OH8CNH-N00",
                           "T-OH8CNH-NNO", "T-OL8CNT-NNO"]
EOP_800G_VENDOR_PN_LIST = ["EOLD-168HG-02-41", "EOLD-138HG-02-41"]
HISENSE_2X100G_VENDOR_PN = r"DEF8504-2C\d{2}-MB3$"
NVIDIA_VENDOR_NAME = "NVIDIA"

def _is_nvidia_vendor(vendor):
    return vendor is not None and vendor.upper() == NVIDIA_VENDOR_NAME

BANKED_MEM_MAPS = [CmisMemMap, CCmisMemMap, ElsfpCmisMemMap]
class XcvrApiFactory(object):
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    def _get_id(self):
        id_byte_raw = self.reader(0, 1)
        if id_byte_raw is None:
            return None
        return id_byte_raw[0]

    def _get_revision_compliance(self):
        id_byte_raw = self.reader(1, 1)
        if id_byte_raw is None:
            return None
        return id_byte_raw[0]

    def _get_vendor_name(self, offset=VENDOR_NAME_OFFSET, length=VENDOR_NAME_LENGTH):
       name_data = self.reader(offset, length)
       if name_data is None:
           return None
       vendor_name = name_data.decode('utf-8', errors='ignore')
       return vendor_name.strip()

    def _get_vendor_part_num(self):
       part_num = self.reader(VENDOR_PART_NUM_OFFSET, VENDOR_PART_NUM_LENGTH)
       if part_num is None:
           return None
       vendor_pn = part_num.decode('utf-8', errors='ignore')
       return vendor_pn.strip()

    def _create_cmis_api(self):
        api = None
        vendor_name = self.lower_memory_info.get_vendor_name()
        vendor_pn = self.lower_memory_info.get_vendor_part_num()

        if vendor_name == 'Credo' and vendor_pn in CREDO_800G_AEC_VENDOR_PN_LIST:
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CredoAec800gMemMap(CredoAec800gCodes, bank=bank))
            api = CredoAec800gApi(xcvr_eeprom, init_cdb_fw_handler=True)
        elif ('INNOLIGHT' in vendor_name and vendor_pn in INL_800G_VENDOR_PN_LIST) or \
             ('EOPTOLINK' in vendor_name and vendor_pn in EOP_800G_VENDOR_PN_LIST):
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CmisMemMap(CmisCodes, bank=bank))
            api = CmisFr800gApi(xcvr_eeprom, init_cdb_fw_handler=True)
        elif vendor_name == 'Hisense' and vendor_pn is not None and re.match(HISENSE_2X100G_VENDOR_PN, vendor_pn):
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CmisMemMap(CmisCodes, bank=bank))
            api = CmisAocSingleBankApi(xcvr_eeprom, init_cdb_fw_handler=True)
        else:
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CmisMemMap(CmisCodes, bank=bank))
            api = CmisApi(xcvr_eeprom, init_cdb_fw_handler=True)
            if api.is_coherent_module():
                xcvr_eeprom = XcvrEeprom(self.reader, self.writer, CCmisMemMap(CmisCodes, bank=bank))
                api = CCmisApi(xcvr_eeprom, init_cdb_fw_handler=True)
        return api

    def _create_cmis_cpo_api(self, bank_id):
        oe_api, els_admin_upper_page = self._build_cpo_oe_api(bank_id)
        els_api = self._build_cpo_els_api(els_admin_upper_page, bank_id)
        return CpoApi(oe_api, els_api)

    def _build_cpo_oe_api(self, bank_id):
        """Returns ``(oe_api, els_admin_upper_page)``; the page id is the ELSFP
        CmisAdministrativeUpperPage where the ELS vendor name lives, or None for
        unknown OEs."""
        oe_vendor = self._get_vendor_name()
        if _is_nvidia_vendor(oe_vendor):
            oe_api = self._create_api(NvidiaCpoOeCodes, NvidiaCpoOeMemMap,
                                      NvidiaCpoOeCmisApi, bank=bank_id,
                                      cdb_mem_map=NvidiaCpoOeCdbMemMap(NvidiaCpoOeCdbCodes))
            return oe_api, NVIDIA_ELS_ADMIN_UPPER_PAGE
        oe_api = self._create_api(CmisCodes, CmisMemMap, CmisApi, bank=bank_id)
        return oe_api, None

    def _build_cpo_els_api(self, els_admin_upper_page, bank_id):
        """Falls back to the generic ElsfpCmisApi when the page is None or vendor unknown.

        Also propagates ``bank_id`` onto the returned API instance: ElsfpCmisApi
        reads ``self.bank_id`` for CDB payload framing and lane indexing, but
        ``_create_api`` only wires ``bank`` into the mem_map, not into the API
        constructor.
        """
        els_vendor = self._get_vendor_els_name(els_admin_upper_page)
        if _is_nvidia_vendor(els_vendor):
            api = self._create_api(NvidiaCpoElsCodes, NvidiaCpoElsCmisMemMap,
                                   NvidiaCpoElsCmisApi, bank=bank_id,
                                   cdb_mem_map=NvidiaCpoElsCdbMemMap(NvidiaCpoElsCdbCodes))
        else:
            api = self._create_api(CmisCodes, ElsfpCmisMemMap,
                                   ElsfpCmisApi, bank=bank_id)
        api.bank_id = bank_id
        return api

    def _get_vendor_els_name(self, els_admin_upper_page):
        if els_admin_upper_page is None:
            return None
        addr = els_admin_upper_page * 128 + VENDOR_NAME_OFFSET
        try:
            els_vendor = self._get_vendor_name(addr, VENDOR_NAME_LENGTH)
        except Exception as e:
            logger.warning("ELS vendor probe at 0x%X failed: %s", addr, e)
            return None
        return els_vendor

    def _create_qsfp_api(self):
        """
        QSFP/QSFP+ API implementation
        """
        revision_compliance = self.lower_memory_info.get_revision_compliance()
        if revision_compliance >= 3:
            return self._create_api(Sff8636Codes, Sff8636MemMap, Sff8636Api)
        else:
            return self._create_api(Sff8436Codes, Sff8436MemMap, Sff8436Api)

    def _create_api(self, codes_class, mem_map_class, api_class, bank=0, cdb_mem_map=None):
        codes = codes_class
        if any(issubclass(mem_map_class, m) for m in BANKED_MEM_MAPS):
            mem_map = mem_map_class(codes, bank=bank)
        else:
            mem_map = mem_map_class(codes)
        xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
        if cdb_mem_map is not None:
            return api_class(xcvr_eeprom, cdb_mem_map=cdb_mem_map)
        return api_class(xcvr_eeprom)

    def create_xcvr_api(self, bank_id=0):
        id = self._get_id()

        # Instantiate various Optics implementation based upon their respective ID as per SFF8024
        id_mapping = {
            0x03: (self._create_api, (Sff8472Codes, Sff8472MemMap, Sff8472Api)),
            0x0D: (self._create_qsfp_api, ()),
            0x11: (self._create_api, (Sff8636Codes, Sff8636MemMap, Sff8636Api)),
            0x18: (self._create_cmis_api, ()),
            0x19: (self._create_cmis_api, ()),
            0x1b: (self._create_cmis_api, ()),
            0x1e: (self._create_cmis_api, ()),
            0x80: (self._create_cmis_cpo_api, (bank_id,)),
            0x7e: (self._create_api, (AmphBackplaneCodes,
                                     AmphBackplaneMemMap, AmphBackplaneImpl)),
        }

        # Check if the ID exists in the mapping
        if id in id_mapping:
            func, args = id_mapping[id]
            if isinstance(args, tuple):
                try:
                    return func(*args)
                except Exception as e:
                    print(f"Error creating API: {e}")
                    return None
        return None
