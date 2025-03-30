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
        **{f"active_apsel_hostlane{i}": "N/A" for i in range(1, 9)},
        "application_advertisement": "N/A",
        "host_electrical_interface": "N/A",
        "media_interface_code": "N/A",
        "host_lane_count": "N/A",
        "media_lane_count": "N/A",
        "host_lane_assignment_option": "N/A",
        "media_lane_assignment_option": "N/A",
        "cable_type": "N/A",
        "media_interface_technology": "N/A",
        "cmis_rev": "N/A",
        "specification_compliance": "N/A",
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

        xcvr_info = copy.deepcopy(self._get_xcvr_info_default_dict())
        xcvr_info.update({
            "type": admin_info[consts.ID_FIELD],
            "type_abbrv_name": admin_info[consts.ID_ABBRV_FIELD],
            "hardware_rev": self.get_module_hardware_revision(),
            "cable_length": float(admin_info[consts.LENGTH_ASSEMBLY_FIELD]),
            "application_advertisement": str(self.get_application_advertisement()) \
                        if len(self.get_application_advertisement()) > 0 else 'N/A',
            "host_electrical_interface": self.get_host_electrical_interface(),
            "media_interface_code": self.get_module_media_interface(),
            "host_lane_count": self.get_host_lane_count(),
            "media_lane_count": self.get_media_lane_count(),
            "host_lane_assignment_option": self.get_host_lane_assignment_option(),
            "media_lane_assignment_option": self.get_media_lane_assignment_option(),
            "cable_type": self.get_cable_length_type(),
            "media_interface_technology": self.get_media_interface_technology(),
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

