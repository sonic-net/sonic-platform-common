"""
    aec_800g.py

    Implementation of Vendor specific in addition to the CMIS specification.
"""

from ...fields import consts
import logging
from ..public.cmis import CmisApi
import time

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class CmisAec800gApi(CmisApi):
    def set_firmware_download_target_end(self, target):
        return self.xcvr_eeprom.write(consts.TARGET_MODE, target)
