########################################################################
# DellEMC
#
# Module contains the ext media drivers for SFP28 modules
#
########################################################################

from ext_media_utils import *
from ext_media_handler_base import media_static_info

SFP28_EXT_SPEC_COMPLIANCE_ADDR =  media_eeprom_address(offset=36)
SFP28_LENGTH_ADDR = media_eeprom_address(offset=18)
SFP28_CONNECTOR_ADDR = media_eeprom_address(offset=2)
SFP28_VENDOR_NAME_ADDR = media_eeprom_address(offset=20)
SFP28_VENDOR_PART_NUM_ADDR = media_eeprom_address(offset=40)
SFP28_VENDOR_REVISION_ADDR = media_eeprom_address(offset=56)
SFP28_VENDOR_SERIAL_NUM_ADDR = media_eeprom_address(offset=68)
SFP28_VENDOR_OUI_ADDR = media_eeprom_address(offset=37)
SFP28_VENDOR_DATE_CODE_ADDR = media_eeprom_address(offset=84)

class sfp28(media_static_info):
    # Uses SFP implementation
    def get_cable_length_detailed(self, eeprom):
        return float(read_eeprom_byte(eeprom, SFP28_LENGTH_ADDR))

    # Get a summary of the media info
    def _get_media_summary(self, eeprom):
        ms = media_summary()

        # Default
        ms.form_factor = self.get_form_factor(eeprom)
        ms.cable_length = self.get_cable_length_detailed(eeprom)
        ms.speed = 25000
        ms.lane_count = self.get_lane_count(eeprom)
        ms.breakout = self.get_cable_breakout(eeprom)
        ms.cable_class = 'FIBER'

        ext_spec_compliance = read_eeprom_byte(eeprom, SFP28_EXT_SPEC_COMPLIANCE_ADDR)
        comp_code_to_attrs = {0x01: ('SR', 'AOC', 'BER:5e-5'),
                            0x02: ('SR', 'FIBER', None),
                            0x03: ('LR', 'FIBER', None),
                            0x04: ('ER', 'FIBER', None),
                            0x08: ('SR', 'ACC', 'BER:5e-5'),
                            0x0B: ('CR', 'DAC', 'CA-25G-L'),
                            0x0C: ('CR', 'DAC', 'CA-25G-S'),
                            0x0D: ('CR', 'DAC', 'CA-25G-N'),
                            0x18: ('SR', 'AOC', 'BER:5e-12'),
                            0x19: ('SR', 'ACC', 'BER:5e-12')}

        if ext_spec_compliance in comp_code_to_attrs:
            ms.interface = comp_code_to_attrs[ext_spec_compliance][0]
            ms.cable_class = comp_code_to_attrs[ext_spec_compliance][1]
            if comp_code_to_attrs[ext_spec_compliance][2] is not None:
                ms.special_fields['fec_hint'] = comp_code_to_attrs[ext_spec_compliance][2]

        # If no interface, discard defaults
        if ms.interface is None:
            return None
        return ms

    def get_media_interface(self, eeprom):
        if self.media_summary is None:
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.interface

    def get_cable_class(self, eeprom):
        if self.media_summary is None:
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.cable_class
    
    def get_lane_count(self, eeprom):
        return 1
    def get_cable_breakout(self, eeprom):
        return '1x1'
    def get_display_name(self, eeprom):
        display_name = build_media_display_name(self.media_summary)
        return display_name
    def get_connector_type(self, eeprom):
        connector_code = read_eeprom_byte(eeprom, SFP28_CONNECTOR_ADDR)
        return get_connector_name(connector_code)
    def get_power_rating_max(self, eeprom):
        # Constant upper limit for SFP28
        return 2.5
    def get_form_factor(self, eeprom):
        return 'SFP28'
    def get_vendor_name(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, SFP28_VENDOR_NAME_ADDR, 16)

    def get_vendor_part_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, SFP28_VENDOR_PART_NUM_ADDR, 16)

    def get_vendor_serial_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, SFP28_VENDOR_SERIAL_NUM_ADDR, 16)

    def get_vendor_oui(self, eeprom):
        # 3 bytes, raw
        oui_bytes = read_eeprom_multi_byte(eeprom, SFP28_VENDOR_OUI_ADDR, media_eeprom_address(offset=SFP28_VENDOR_OUI_ADDR.offset+3))
        # Print OUI as hyphen seperated hex formatted bytes
        return '-'.join('{:02X}'.format(n) for n in oui_bytes)

    def get_vendor_revision(self, eeprom):
        # 4 bytes
        return extract_string_from_eeprom(eeprom, SFP28_VENDOR_REVISION_ADDR, 4)

    def get_vendor_date_code(self, eeprom):
        # 8 bytes, strict formatting
        date_code = extract_string_from_eeprom(eeprom, SFP28_VENDOR_DATE_CODE_ADDR, 8)
        return parse_date_code(date_code)
    def __init__(self, eeprom):
        self.media_summary = self._get_media_summary(eeprom)
