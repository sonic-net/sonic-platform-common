"""
    xcvr_api_factory.py

    Factory class responsible for instantiating the appropriate XcvrApi
    implementation for a xcvr module in SONiC
"""

from .xcvr_eeprom import XcvrEeprom
# TODO: remove the following imports
from .codes.public.sff8024 import Sff8024
from .api.public.cmis import CmisApi
from .mem_maps.public.cmis import CmisMemMap

class XcvrApiFactory(object):
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    def _get_id(self):
        # TODO: read ID from eeprom
        pass

    def create_xcvr_api(self):
        # TODO: load correct classes from id_mapping file
        codes = Sff8024
        mem_map = CmisMemMap(codes)
        xcvr_eeprom = XcvrEeprom(self.reader, self.writer, mem_map)
        return CmisApi(xcvr_eeprom)
