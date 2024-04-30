"""
    fr_800g.py

    Implementation of Innolight FR module specific in addition to the CMIS specification.
"""

from ...fields import consts
from ..public.cmis import CmisApi

class CmisFr800gApi(CmisApi):
    def get_transceiver_info_firmware_versions(self):
        return_dict = {"active_firmware" : "N/A", "inactive_firmware" : "N/A"}
        
        InactiveFirmware = self.get_module_inactive_firmware()
        ActiveFirmware = self.get_module_active_firmware()

        return_dict["active_firmware"] = ActiveFirmware + ".0"
        return_dict["inactive_firmware"] = InactiveFirmware + ".0"
        return return_dict
