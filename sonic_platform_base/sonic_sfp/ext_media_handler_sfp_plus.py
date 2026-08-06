########################################################################
# DellEMC
#
# Module contains the ext media drivers for SFP+ modules
#
########################################################################

from ext_media_utils import *
from ext_media_handler_base import media_static_info

SFP_PLUS_LENGTH_ADDR = media_eeprom_address(offset=18)
SFP_PLUS_10G_COMPLIANCE_ADDR = media_eeprom_address(offset=3)
SFP_PLUS_CABLE_TECH_ADDR = media_eeprom_address(offset=8)
SFP_PLUS_CONNECTOR_ADDR = media_eeprom_address(offset=2)
SFP_PLUS_EXT_SPEC_COMPLIANCE_ADDR =  media_eeprom_address(offset=36)
SFP_PLUS_VENDOR_NAME_ADDR = media_eeprom_address(offset=20)
SFP_PLUS_VENDOR_PART_NUM_ADDR = media_eeprom_address(offset=40)
SFP_PLUS_VENDOR_REVISION_ADDR = media_eeprom_address(offset=56)
SFP_PLUS_VENDOR_SERIAL_NUM_ADDR = media_eeprom_address(offset=68)
SFP_PLUS_VENDOR_OUI_ADDR = media_eeprom_address(offset=37)
SFP_PLUS_VENDOR_DATE_CODE_ADDR = media_eeprom_address(offset=84)

class sfp_plus(media_static_info):
    # Uses SFP implementation
    def get_cable_length_detailed(self, eeprom):
        return float(read_eeprom_byte(eeprom, SFP_PLUS_LENGTH_ADDR))
    # Get a summary of the media info
    def _get_media_summary(self, eeprom):
        ms = media_summary()

        # Default 
        ms.form_factor = self.get_form_factor(eeprom)
        ms.cable_length = self.get_cable_length_detailed(eeprom)
        ms.speed = 10000
        ms.lane_count = self.get_lane_count(eeprom)
        ms.breakout = self.get_cable_breakout(eeprom)
        ms.cable_class = 'FIBER'

        xcvr_compliance_10g = read_eeprom_byte(eeprom, SFP_PLUS_10G_COMPLIANCE_ADDR) & set_bits([4,5,6,7])

        if xcvr_compliance_10g > 0:
            import math
            # Get leftmost set bit
            msb = int(math.log(xcvr_compliance_10g,2)) - 4
            ms.interface = ['SR', 'LR', 'LRM', 'ER'][msb]
            return ms

        # Check the cable tech:
        cable_tech = read_eeprom_byte(eeprom, SFP_PLUS_CABLE_TECH_ADDR)
        if cable_tech & set_bits([3]):
            ms.interface = 'SR'
            ms.cable_class = 'AOC'
        if cable_tech & set_bits([2]):
            ms.interface = 'CR'
            ms.cable_class = 'DAC'
        if ms.interface is None:
            ext_spec_compliance = read_eeprom_byte(eeprom, SFP_PLUS_EXT_SPEC_COMPLIANCE_ADDR)
            if ext_spec_compliance in [0x16, 0x1C]:
                ms.cable_class = 'RJ45'
                ms.interface = 'T'
            else:
                connector_type = read_eeprom_byte(eeprom, SFP_PLUS_CONNECTOR_ADDR)
                if connector_type == 0x22:
                    ms.cable_class = 'RJ45'
                    ms.interface = 'T'
                elif connector_type == '0x21':
                    ms.cable_class = 'DAC'
                    ms.interface = 'CR'
                else:
                    return None
        return ms

    def get_media_interface(self, eeprom):
        if self.media_summary.interface is None:
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.interface
    def get_cable_class(self, eeprom):
        if self.media_summary.cable_class is None:
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.cable_class
    def get_lane_count(self, eeprom):
        return 1
    def get_cable_breakout(self, eeprom):
        return '1x1'
    def get_display_name(self, eeprom):
        display_name = build_media_display_name(self.media_summary)

        # All known 10G conventions are conformant
        return display_name
    def get_connector_type(self, eeprom):
        connector_code = read_eeprom_byte(eeprom, SFP_PLUS_CONNECTOR_ADDR)
        return get_connector_name(connector_code)
    def get_power_rating_max(self, eeprom):
        # Constant upper limit for most SFP+
        return 2.0
    def get_form_factor(self, eeprom):
        return 'SFP+'
    def get_vendor_name(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, SFP_PLUS_VENDOR_NAME_ADDR, 16)

    def get_vendor_part_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, SFP_PLUS_VENDOR_PART_NUM_ADDR, 16)

    def get_vendor_serial_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, SFP_PLUS_VENDOR_SERIAL_NUM_ADDR, 16)

    def get_vendor_oui(self, eeprom):
        # 3 bytes, raw
        oui_bytes = read_eeprom_multi_byte(eeprom, SFP_PLUS_VENDOR_OUI_ADDR, media_eeprom_address(offset=SFP_PLUS_VENDOR_OUI_ADDR.offset+3))
        # Print OUI as hyphen seperated hex formatted bytes
        return '-'.join('{:02X}'.format(n) for n in oui_bytes)

    def get_vendor_revision(self, eeprom):
        # 4 bytes
        return extract_string_from_eeprom(eeprom, SFP_PLUS_VENDOR_REVISION_ADDR, 4)

    def get_vendor_date_code(self, eeprom):
        # 8 bytes, strict formatting
        date_code = extract_string_from_eeprom(eeprom, SFP_PLUS_VENDOR_DATE_CODE_ADDR, 8)
        return parse_date_code(date_code)
    def __init__(self, eeprom):
        self.media_summary = self._get_media_summary(eeprom)
