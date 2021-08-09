"""
    cmis.py

    Implementation of XcvrApi that corresponds to CMIS
"""

from ...fields import consts
from ..xcvr_api import XcvrApi
from ..coh_optic_api import CoherentOpticApi

class CmisApi(XcvrApi):
    NUM_CHANNELS = 8

    def __init__(self, xcvr_eeprom):
        super(CmisApi, self).__init__(xcvr_eeprom)

    def get_model(self):
        return self.xcvr_eeprom.read(consts.VENDOR_PART_NO_FIELD)

    # TODO: other XcvrApi methods

