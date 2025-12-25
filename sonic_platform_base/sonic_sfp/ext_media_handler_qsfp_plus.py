########################################################################
# DellEMC
#
# Module contains the ext media drivers for QSFP+ modules
#
########################################################################

from ext_media_utils import *
from ext_media_handler_base import media_static_info

QSFP_PLUS_LENGTH_ADDR = media_eeprom_address(offset=146)
QSFP_PLUS_FAR_END_IMPL_ADDR = media_eeprom_address(offset=113)
QSFP_PLUS_CONNECTOR_ADDR = media_eeprom_address(offset=130)
QSFP_PLUS_EXT_SPEC_COMPL_ADDR = media_eeprom_address(offset=192)
QSFP_PLUS_40G_COMPL_ADDR = media_eeprom_address(offset=131)
QSFP_PLUS_DEVICE_TECH_ADDR = media_eeprom_address(offset=147)
QSFP_PLUS_MAX_POWER_CLASS_ADDR = media_eeprom_address(offset=129)
QSFP_PLUS_MAX_POWER_RAW_ADDR = media_eeprom_address(offset=107)
QSFP_PLUS_VENDOR_NAME_ADDR = media_eeprom_address(offset=148)
QSFP_PLUS_VENDOR_PART_NUM_ADDR = media_eeprom_address(offset=168)
QSFP_PLUS_VENDOR_REVISION_ADDR = media_eeprom_address(offset=184)
QSFP_PLUS_VENDOR_SERIAL_NUM_ADDR = media_eeprom_address(offset=196)
QSFP_PLUS_VENDOR_OUI_ADDR = media_eeprom_address(offset=165)
QSFP_PLUS_VENDOR_DATE_CODE_ADDR = media_eeprom_address(offset=212)



class qsfp_plus(media_static_info):
    def get_cable_length_detailed(self, eeprom):
        return float(read_eeprom_byte(eeprom, QSFP_PLUS_LENGTH_ADDR))

    def _get_media_summary(self, eeprom):
        ms = media_summary()

        # Default 
        ms.form_factor = self.get_form_factor(eeprom)
        ms.cable_length = self.get_cable_length_detailed(eeprom)
        ms.speed = 40000
        ms.lane_count = self.get_lane_count(eeprom)
        ms.breakout = self.get_cable_breakout(eeprom)
        ms.cable_class = 'FIBER'

        xcvr_compl = read_eeprom_byte(eeprom, QSFP_PLUS_40G_COMPL_ADDR)
        if xcvr_compl & set_bits([3]):
            ms.interface = 'CR'
            ms.cable_class = 'DAC'
            ms.breakout = self.get_cable_breakout(eeprom)
        elif xcvr_compl & set_bits([2]):
            ms.interface = 'SR'
        elif xcvr_compl & set_bits([1]):
            ms.interface = 'LR'
        elif xcvr_compl & set_bits([0]):
            ms.interface = 'SR'
            ms.cable_class = 'AOC'
            ms.breakout = self.get_cable_breakout(eeprom)

        if ms.interface is None:
            # Try extended compliance checks 
            ext_compl = read_eeprom_byte(eeprom, QSFP_PLUS_EXT_SPEC_COMPL_ADDR)
            ext_compl_map = {0x10: 'ER', 0x11: 'SR', 0x12: 'PSM', 0x1F: 'SWDM'}
            if ext_compl in ext_compl_map:
                ms.interface = ext_compl_map[ext_compl]
            else:
                # Try connector type
                connector_type = read_eeprom_byte(eeprom, QSFP_PLUS_CONNECTOR_ADDR)
                if connector_type == 0x23:
                    # Either DAC, AOC, ACC
                    # Check device tech
                    device_tech = (read_eeprom_byte(eeprom, QSFP_PLUS_DEVICE_TECH_ADDR) >> 4) & 0x0F
                    if device_tech < 0x0A:
                        ms.interface = 'SR'
                        ms.cable_class = 'AOC'
                    else:
                        ms.interface = 'CR'
                        ms.cable_class = 'DAC'
                elif connector_type == 0x21:
                    ms.interface = 'CR'
                    ms.cable_class = 'DAC'
                elif connector_type in [0x07, 0x0C, 0x0D]:
                    ms.interface = 'SR'
                else:
                    return None
        return ms
    def get_media_interface(self, eeprom):
        if self.media_summary is None:
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.interface
    def get_cable_class(self, eeprom):
        if self.media_summary is None:
            # Summary builder could not find it
            # Try to use connector type:
            connector_type = read_eeprom_byte(eeprom, QSFP_PLUS_CONNECTOR_ADDR)
            if connector_type == 0x21:
                return 'DAC'
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.cable_class
    
    def get_lane_count(self, eeprom):
        return 4
    def get_cable_breakout(self, eeprom):
        # Try to build based on far-end count
        far_end = read_eeprom_byte(eeprom, QSFP_PLUS_FAR_END_IMPL_ADDR) & set_bits([4,5,6])
        if far_end > 0:
            far_end = far_end >> 4            
            return ['1x1', '1x1', '1x1', '1x1', '1x4', '2x2', '1x2'][far_end]
        # Default is 1x1
        return '1x1'
    def get_display_name(self, eeprom):
        display_name = build_media_display_name(self.media_summary)

        # All known 40G conventions are conformant. No need to augment standard name
        return display_name
    def get_connector_type(self, eeprom):
        connector_code = read_eeprom_byte(eeprom, QSFP_PLUS_CONNECTOR_ADDR)
        return get_connector_name(connector_code)
    def get_power_rating_max(self, eeprom):
        power_max_code = read_eeprom_byte(eeprom, QSFP_PLUS_MAX_POWER_CLASS_ADDR) 

        # Determine which power checking method
        if (power_max_code & 0x03) == 0:
            # Old method
            # Check upper 2 bits 6, 7
            return [1.5, 2.0, 2.5, 3.5][((power_max_code >> 6) & 0x03)]
        elif (power_max_code & (1<<5)) == 0:
            # New method
            # Check bits 0,1
            return [0.0, 4.0, 4.5, 5.0][power_max_code & 0x03]
        # Newest method
        # Byte 107, as unsigned int in units of 0.1W
        return float(read_eeprom_byte(eeprom, QSFP_PLUS_MAX_POWER_RAW_ADDR)) * 0.1 


    def get_form_factor(self, eeprom):
        return 'QSFP+'

    def get_vendor_name(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, QSFP_PLUS_VENDOR_NAME_ADDR, 16)

    def get_vendor_part_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, QSFP_PLUS_VENDOR_PART_NUM_ADDR, 16)

    def get_vendor_serial_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, QSFP_PLUS_VENDOR_SERIAL_NUM_ADDR, 16)

    def get_vendor_oui(self, eeprom):
        # 3 bytes, raw
        oui_bytes = read_eeprom_multi_byte(eeprom, QSFP_PLUS_VENDOR_OUI_ADDR, media_eeprom_address(offset=QSFP_PLUS_VENDOR_OUI_ADDR.offset+3))
        # Print OUI as hyphen seperated hex formatted bytes
        return '-'.join('{:02X}'.format(n) for n in oui_bytes)

    def get_vendor_revision(self, eeprom):
        # 2 bytes
        return extract_string_from_eeprom(eeprom, QSFP_PLUS_VENDOR_REVISION_ADDR, 2)

    def get_vendor_date_code(self, eeprom):
        # 8 bytes, strict formatting
        date_code = extract_string_from_eeprom(eeprom, QSFP_PLUS_VENDOR_DATE_CODE_ADDR, 8)
        return parse_date_code(date_code)
    def __init__(self, eeprom):
        self.media_summary = self._get_media_summary(eeprom)
