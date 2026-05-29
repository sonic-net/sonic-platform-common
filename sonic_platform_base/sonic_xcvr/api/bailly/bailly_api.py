"""
    bailly_api.py

    Implementation of Micas Bailly CPO specific in addition to the CMIS specification.
"""
from ..public.cmis import CmisApi
from ...fields.bailly import bailly_consts

class BaillyApi(CmisApi):
    def __init__(self, xcvr_eeprom):
        super(BaillyApi, self).__init__(xcvr_eeprom)
    
    def get_dpinit_pending(self):
        '''
        Bailly not supported, return fake value.
        '''
        dpinit_pending_dict = {}
        for lane in range(self.NUM_CHANNELS):
            key = "DPInitPending{}".format(lane + 1)
            dpinit_pending_dict[key] = True
        return dpinit_pending_dict
    
    def get_active_apsel_hostlane(self):
        '''
        Bailly not supported Deinit, if it is deinit return fake value.
        '''
        has_zero  = False
        current_map = {}
        for lane in range(self.NUM_CHANNELS):
            lane_key = 'ActiveAppSelLane{}'.format(lane + 1)
            app_lane = self.get_application(lane)
            current_map[lane_key] = app_lane
            if app_lane == 0:
                has_zero = True
        
        if has_zero:
            return current_map
        else:
            normal =  super().get_active_apsel_hostlane()
            return normal
    def _format_revision(self, revision):
        if revision is None:
            return None
        return "{}.{}".format((revision >> 4) & 0xf, revision & 0xf)

    def get_transceiver_info(self):
        info = super().get_transceiver_info()
        if info is None:
            return None

        els_info = self.get_els_info()
        cpo_info = els_info.get("cpo_info")
        vendor_info = els_info.get("vendor_info")
        laser_power_mode = els_info.get("laser_power_mode")
        if cpo_info is None and vendor_info is None and laser_power_mode is None:
            return info

        if cpo_info is not None:
            info.update({
                "els_identifier": cpo_info.get(bailly_consts.CPO_IDENTIFIER),
                "els_revision": self._format_revision(cpo_info.get(bailly_consts.CPO_REVISION)),
                "els_laser_grid_and_count": cpo_info.get(bailly_consts.LASER_GRID_AND_COUNT),
                "els_laser_wavelength_grid": cpo_info.get(bailly_consts.LASER_WAVELENGTH_GRID),
                "els_laser_count": cpo_info.get(bailly_consts.LASER_COUNT),
            })

        if vendor_info is not None:
            info.update({
                "els_vendor_name": self._strip_str(
                    vendor_info.get(bailly_consts.VENDOR_NAME_ASCII_FIELD)
                ),
                "els_vendor_oui": vendor_info.get(bailly_consts.VENDOR_OUI_HEX_FIELD),
                "els_vendor_pn": self._strip_str(
                    vendor_info.get(bailly_consts.VENDOR_PART_NUMBER_ASCII_FIELD)
                ),
                "els_vendor_rev": self._strip_str(
                    vendor_info.get(bailly_consts.VENDOR_REVISION_ASCII_FIELD)
                ),
                "els_vendor_sn": self._strip_str(
                    vendor_info.get(bailly_consts.VENDOR_SERIAL_NUMBER_ASCII_FIELD)
                ),
                "els_date_code": self._strip_str(
                    vendor_info.get(bailly_consts.DATE_CODE_FIELD)
                ),
                "els_max_power": vendor_info.get(bailly_consts.MAX_POWER_CONSUMPTION_FIELD),
            })

        if laser_power_mode is not None:
            info.update({
                "els_laser_power_mode_control": laser_power_mode.get(
                    bailly_consts.LASER_POWER_MODE_CONTROL_BITS_FIELD
                ),
            })

        return info

    def get_els_vendor_info(self):
        return self.xcvr_eeprom.read(bailly_consts.CPO_VENDOR_INFO_FIELD)

    def get_els_info(self):
        return {
            "cpo_info": self.xcvr_eeprom.read(bailly_consts.CPO_INFO_FIELD),
            "vendor_info": self.get_els_vendor_info(),
            "laser_power_mode": self.xcvr_eeprom.read(bailly_consts.LASER_POWER_MODE_CONTROL_FIELD),
        }
