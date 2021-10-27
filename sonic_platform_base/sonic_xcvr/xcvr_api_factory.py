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
from .api.public.c_cmis import CCmisApi
from .mem_maps.public.cmis import CmisMemMap

from .codes.public.sff8436 import Sff8436Codes
from .api.public.sff8436 import Sff8436Api
from .mem_maps.public.sff8436 import Sff8436MemMap

from .codes.public.sff8636 import Sff8636Codes
from .api.public.sff8636 import Sff8636Api
from .mem_maps.public.sff8636 import Sff8636MemMap

ZR_MEDIA_INTERFACE_CODE = [62, 63, 70, 71, 72, 73]

class XcvrApiFactory(object):
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    def _get_id(self):
        id_byte_raw = self.reader(0, 1)
        if id_byte_raw is None:
            return None
        return id_byte_raw[0]
    
    def _get_module_type(self):
        module_type = self.reader(85, 1)
        if module_type is None:
            return None
        return module_type[0]
    
    def _get_module_media_interface(self):
        module_media_interface = self.reader(87, 1)
        if module_media_interface is None:
            return None
        return module_media_interface[0]

    def create_xcvr_api(self):
        # TODO: load correct classes from id_mapping file
        id = self._get_id()
        # QSFP-DD or OSFP
        if id == 0x18 or id == 0x19:
            codes = CmisCode
            mem_map = CmisMemMap(codes)
            xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)

            module_type = self._get_module_type()
            module_media_interface = self._get_module_media_interface()
            if (module_type == 2) and (module_media_interface in ZR_MEDIA_INTERFACE_CODE):
                api = CCmisApi(xcvr_eeprom)
            else:
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
