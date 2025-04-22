"""
    xcvr_api_factory.py

    Factory class responsible for instantiating the appropriate XcvrApi
    implementation for a xcvr module in SONiC
"""

from .xcvr_eeprom import XcvrEeprom
# TODO: remove the following imports
from .codes.public.cmis import CmisCodes
from .api.public.cmis import CmisApi
from .api.public.c_cmis import CCmisApi
from .mem_maps.public.cmis import CmisMemMap
from .mem_maps.public.c_cmis import CCmisMemMap

from .codes.credo.aec_800g import CmisAec800gCodes
from .api.credo.aec_800g import CmisAec800gApi
from .mem_maps.credo.aec_800g import CmisAec800gMemMap

from .api.innolight.fr_800g import CmisFr800gApi

from .api.amphenol.backplane import AmphBackplaneImpl
from .mem_maps.amphenol.backplane import AmphBackplaneMemMap
from .codes.amphenol.backplane import AmphBackplaneCodes

from .codes.public.sff8436 import Sff8436Codes
from .api.public.sff8436 import Sff8436Api
from .mem_maps.public.sff8436 import Sff8436MemMap

from .codes.public.sff8636 import Sff8636Codes
from .api.public.sff8636 import Sff8636Api
from .mem_maps.public.sff8636 import Sff8636MemMap

from .codes.public.sff8472 import Sff8472Codes
from .api.public.sff8472 import Sff8472Api
from .mem_maps.public.sff8472 import Sff8472MemMap

VENDOR_NAME_OFFSET = 129
VENDOR_PART_NUM_OFFSET = 148
VENDOR_NAME_LENGTH = 16
VENDOR_PART_NUM_LENGTH = 16

CREDO_800G_AEC_VENDOR_PN_LIST = ["CAC81X321M2MC1MS", "CAC815321M2MC1MS", "CAC82X321M2MC1MS"]
INL_800G_VENDOR_PN_LIST = ["T-DL8CNT-NCI", "T-DH8CNT-NCI", "T-DH8CNT-N00", "T-DP4CNH-NCI", "T-DP8CNT-NNO", "T-DP8CNH-NNO", "T-DC8CNT-NNO", "T-DP8CNL-NNO", "T-OL8CNT-N00", "T-OH8CNH-N00"]
EOP_800G_VENDOR_PN_LIST = ["EOLD-168HG-02-41", "EOLD-138HG-02-41"]

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

    def _get_vendor_name(self):
       name_data = self.reader(VENDOR_NAME_OFFSET, VENDOR_NAME_LENGTH)
       if name_data is None:
           return None
       vendor_name = name_data.decode()
       return vendor_name.strip()

    def _get_vendor_part_num(self):
       part_num = self.reader(VENDOR_PART_NUM_OFFSET, VENDOR_PART_NUM_LENGTH)
       if part_num is None:
           return None
       vendor_pn = part_num.decode()
       return vendor_pn.strip()

    def _create_cmis_api(self):
        api = None
        vendor_name = self._get_vendor_name()
        vendor_pn = self._get_vendor_part_num()

        if vendor_name == 'Credo' and vendor_pn in CREDO_800G_AEC_VENDOR_PN_LIST:
            api = self._create_api(CmisAec800gCodes, CmisAec800gMemMap, CmisAec800gApi)
        elif ('INNOLIGHT' in vendor_name and vendor_pn in INL_800G_VENDOR_PN_LIST) or \
             ('EOPTOLINK' in vendor_name and vendor_pn in EOP_800G_VENDOR_PN_LIST):
            api = self._create_api(CmisCodes, CmisMemMap, CmisFr800gApi)

        else:
            api = self._create_api(CmisCodes, CmisMemMap, CmisApi)
            if api.is_coherent_module():
                api = self._create_api(CmisCodes, CCmisMemMap, CCmisApi)
        return api

    def _create_qsfp_api(self):
        """
        QSFP/QSFP+ API implementation
        """
        revision_compliance = self._get_revision_compliance()
        if revision_compliance >= 3:
            return self._create_api(Sff8636Codes, Sff8636MemMap, Sff8636Api)
        else:
            return self._create_api(Sff8436Codes, Sff8436MemMap, Sff8436Api)

    def _create_api(self, codes_class, mem_map_class, api_class):
        codes = codes_class
        mem_map = mem_map_class(codes)
        xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
        return api_class(xcvr_eeprom) 

    def create_xcvr_api(self):
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
            0x7e: (self._create_api, (AmphBackplaneCodes,
                                     AmphBackplaneMemMap, AmphBackplaneImpl)),
        }

        # Check if the ID exists in the mapping
        if id in id_mapping:
            func, args = id_mapping[id]
            if isinstance(args, tuple):
                return func(*args)
        return None
