"""
    Custom API for Amphenol 800G Backplane Cartridge
"""
import copy
from ...fields import consts
from ..public.cmis import CmisApi

AMPH_BACKPLANE_INFO_DICT = {
        "type": "N/A",
        "type_abbrv_name": "N/A",
        "hardware_rev": "N/A",
        "serial": "N/A",
        "cable_length": "N/A",
        "manufacturer": "N/A", # Vendor Name
        "model": "N/A", # Vendor Part Number
        "vendor_date": "N/A",
        "vendor_oui": "N/A",
        "vendor_rev": "N/A",
        "application_advertisement": "N/A",
        "host_electrical_interface": "N/A",
        "host_lane_count": "N/A",
        "cable_type": "N/A",
        "cmis_rev": "N/A",
        "specification_compliance": "N/A",
        "slot_id": "unknown"
        }

class AmphBackplaneImpl(CmisApi):
    """
    Custom API for Amphenol 800G Backplane Catridge
    """
    def __init__(self, xcvr_eeprom):
        super(AmphBackplaneImpl, self).__init__(xcvr_eeprom)

    def get_slot_id(self):
        """
        Get the slot id
        """
        slot = self.xcvr_eeprom.read(consts.CARTRDIGE_SLOT_ID)
        if slot is None:
            return "N/A"
        return slot

    def get_transceiver_info(self):
        admin_info = self.xcvr_eeprom.read(consts.ADMIN_INFO_FIELD)
        if admin_info is None:
            return None

        xcvr_info = copy.deepcopy(AMPH_BACKPLANE_INFO_DICT)
        xcvr_info.update({
            "type": admin_info[consts.ID_FIELD],
            "type_abbrv_name": admin_info[consts.ID_ABBRV_FIELD],
            "hardware_rev": self.get_module_hardware_revision(),
            "cable_length": float(admin_info[consts.LENGTH_ASSEMBLY_FIELD]),
            "application_advertisement": str(self.get_application_advertisement()) \
                        if len(self.get_application_advertisement()) > 0 else 'N/A',
            "host_electrical_interface": self.get_host_electrical_interface(),
            "host_lane_count": self.get_host_lane_count(),
            "host_lane_assignment_option": self.get_host_lane_assignment_option(),
            "cable_type": self.get_cable_length_type(),
            "cmis_rev": self.get_cmis_rev(),
            "specification_compliance": self.get_module_media_type(),
            "vdm_supported": self.is_transceiver_vdm_supported()
        })

        appl_adv = self.get_application_advertisement()
        if len(appl_adv) > 0:
            xcvr_info["application_advertisement"] = str(appl_adv)

        # Vendor specific fields
        xcvr_info.update({
            "serial": admin_info[consts.VENDOR_SERIAL_NO_FIELD],
            "manufacturer": admin_info[consts.VENDOR_NAME_FIELD],
            "model": admin_info[consts.VENDOR_PART_NO_FIELD],
            "vendor_date": admin_info[consts.VENDOR_DATE_FIELD],
            "vendor_oui": admin_info[consts.VENDOR_OUI_FIELD],
            "vendor_rev": self.get_vendor_rev(),
            "slot_id": self.get_slot_id(),
        })
        return xcvr_info

