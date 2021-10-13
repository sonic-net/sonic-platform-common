"""
    xcvr_api_factory.py

    Factory class responsible for instantiating the appropriate XcvrApi
    implementation for a xcvr module in SONiC
"""

from .xcvr_eeprom import XcvrEeprom
# TODO: remove the following imports
from .codes.public.sff8024 import Sff8024
from .codes.public.cmis_code import CmisCode
from .api.public.cmis import CmisApi
from .mem_maps.public.cmis import CmisMemMap

from .codes.public.sff8436 import Sff8436Codes
from .api.public.sff8436 import Sff8436Api
from .mem_maps.public.sff8436 import Sff8436MemMap

from .codes.public.sff8636 import Sff8636Codes
from .api.public.sff8636 import Sff8636Api
from .mem_maps.public.sff8636 import Sff8636MemMap

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
        if id == 0x18 or id == 0x19:
            codes = {'sff8024':Sff8024, 'cmis_code':CmisCode}
            mem_map = CmisMemMap(codes)
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
            api = CmisApi(xcvr_eeprom)
        # QSFP28
        elif id == 0x11:
            codes = Sff8636Codes
            mem_map = Sff8636MemMap(codes)
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
            api = Sff8636Api(xcvr_eeprom)
        # QSFP+
        elif id == 0x0D:
            codes = Sff8436Codes
            mem_map = Sff8436MemMap(codes)
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
            api = Sff8436Api(xcvr_eeprom)
        else:
            api = None
        return api        
