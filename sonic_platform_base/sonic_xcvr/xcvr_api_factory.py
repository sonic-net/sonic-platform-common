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
INL_800G_VENDOR_PN_LIST = ["T-DL8CNT-NCI", "T-DH8CNT-NCI", "T-DH8CNT-N00", "T-DP4CNH-NCI"]
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
        
    def create_xcvr_api(self):
        # TODO: load correct classes from id_mapping file
        id = self._get_id()
        # QSFP-DD or OSFP
        if id == 0x18 or id == 0x19 or id == 0x1e:
            vendor_name = self._get_vendor_name()
            vendor_pn = self._get_vendor_part_num()
            if vendor_name == 'Credo' and vendor_pn in CREDO_800G_AEC_VENDOR_PN_LIST:
                codes = CmisAec800gCodes
                mem_map = CmisAec800gMemMap(CmisAec800gCodes)
                xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
                api = CmisAec800gApi(xcvr_eeprom)
            elif ('INNOLIGHT' in vendor_name and vendor_pn in INL_800G_VENDOR_PN_LIST) or \
                 ('EOPTOLINK' in vendor_name and vendor_pn in EOP_800G_VENDOR_PN_LIST):
                codes = CmisCodes
                mem_map = CmisMemMap(codes)
                xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
                api = CmisFr800gApi(xcvr_eeprom)
            else:
                codes = CmisCodes
                mem_map = CmisMemMap(codes)
                xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
                api = CmisApi(xcvr_eeprom)

            if api.is_coherent_module():
                mem_map = CCmisMemMap(codes)
                xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
                api = CCmisApi(xcvr_eeprom)

        # QSFP28
        elif id == 0x11:
            codes = Sff8636Codes
            mem_map = Sff8636MemMap(codes)
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
            api = Sff8636Api(xcvr_eeprom)
        # QSFP+
        elif id == 0x0D:
            revision_compliance = self._get_revision_compliance()
            if revision_compliance >= 3:
                codes = Sff8636Codes
                mem_map = Sff8636MemMap(codes)
                xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
                api = Sff8636Api(xcvr_eeprom)
            else:
                codes = Sff8436Codes
                mem_map = Sff8436MemMap(codes)
                xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
                api = Sff8436Api(xcvr_eeprom)
        elif id == 0x03:
            codes = Sff8472Codes
            mem_map = Sff8472MemMap(codes)
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
            api = Sff8472Api(xcvr_eeprom)
        else:
            api = None
        return api
