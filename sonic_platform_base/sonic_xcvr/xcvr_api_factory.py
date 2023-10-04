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

from .codes.public.sff8436 import Sff8436Codes
from .api.public.sff8436 import Sff8436Api
from .mem_maps.public.sff8436 import Sff8436MemMap

from .codes.public.sff8636 import Sff8636Codes
from .api.public.sff8636 import Sff8636Api
from .mem_maps.public.sff8636 import Sff8636MemMap

from .codes.public.sff8472 import Sff8472Codes
from .api.public.sff8472 import Sff8472Api
from .mem_maps.public.sff8472 import Sff8472MemMap

class XcvrApiFactory(object):
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    def _get_id(self):
        id_byte_raw = self.reader(0, 1)
        if id_byte_raw is None:
            return None
        return id_byte_raw[0]

    def create_xcvr_api(self):
        # TODO: load correct classes from id_mapping file
        id = self._get_id()
        # QSFP-DD or OSFP
        if id == 0x18 or id == 0x19 or id == 0x1e:
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
        # QSFP+ or QSFP
        elif id == 0x0D or id == 0x0C:
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
