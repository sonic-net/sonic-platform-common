########################################################################
# DellEMC
#
# Module contains the ext media drivers for QSFP28 modules
#
########################################################################

from ext_media_utils import *
from ext_media_handler_base import media_static_info

QSFP28_LENGTH_ADDR = media_eeprom_address(offset=146)
QSFP28_FAR_END_IMPL_ADDR = media_eeprom_address(offset=113)
QSFP28_CONNECTOR_ADDR = media_eeprom_address(offset=130)
QSFP28_EXT_SPEC_COMPL_ADDR = media_eeprom_address(offset=192)
QSFP28_DEVICE_TECH_ADDR = media_eeprom_address(offset=147)
QSFP28_MAX_POWER_CLASS_ADDR = media_eeprom_address(offset=129)
QSFP28_MAX_POWER_RAW_ADDR = media_eeprom_address(offset=107)
QSFP28_VENDOR_NAME_ADDR = media_eeprom_address(offset=148)
QSFP28_VENDOR_PART_NUM_ADDR = media_eeprom_address(offset=168)
QSFP28_VENDOR_REVISION_ADDR = media_eeprom_address(offset=184)
QSFP28_VENDOR_SERIAL_NUM_ADDR = media_eeprom_address(offset=196)
QSFP28_VENDOR_OUI_ADDR = media_eeprom_address(offset=165)
QSFP28_VENDOR_DATE_CODE_ADDR = media_eeprom_address(offset=212)


class qsfp28(media_static_info):
    # Uses QSFP+ implementation
    def get_cable_length_detailed(self, eeprom):
        return float(read_eeprom_byte(eeprom, QSFP28_LENGTH_ADDR))
    # Get a summary of the media info
    def _get_media_summary(self, eeprom):
        ms = media_summary()

        # Default 
        ms.form_factor = self.get_form_factor(eeprom)
        ms.cable_length = self.get_cable_length_detailed(eeprom)
        ms.speed = 100*1000
        ms.lane_count = 4
        ms.breakout = self.get_cable_breakout(eeprom)
        ms.cable_class = 'FIBER'

        ext_spec_compliance = read_eeprom_byte(eeprom, QSFP28_EXT_SPEC_COMPL_ADDR)
        comp_code_to_attrs = {0x01: ('SR', 'AOC', 4, 'BER:5e-5'),
                            0x02: ('SR', 'FIBER', 4, None),
                            0x03: ('LR', 'FIBER', 4, None),
                            0x04: ('ER', 'FIBER', 4, None),
                            0x05: ('SR', 'FIBER', 10, None),
                            0x06: ('CWDM', 'FIBER', 4, None),
                            0x07: ('PSM', 'FIBER', 4,None),
                            0x08: ('SR', 'ACC', 4,'BER:5e-5'),
                            0x0B: ('CR', 'DAC', 4,'CA-25G-L'),
                            0x0C: ('CR', 'DAC', 4,'CA-25G-S'),
                            0x0D: ('CR', 'DAC', 4,'CA-25G-N'),
                            0x18: ('CLR', 'FIBER', 4, None),
                            0x18: ('SR', 'AOC', 4, 'BER:5e-12'),
                            0x19: ('SR', 'ACC', 4, 'BER:5e-12'),
                            0x1A: ('DWDM', 'FIBER', 2, 'NO-FEC'),
                            0x1A: ('WDM', 'FIBER', 4, None),
                            0x20: ('SWDM', 'FIBER', 4, None),
                            0x21: ('BIDI', 'FIBER', 1, None),
                            0x22: ('CWDM', 'FIBER', 4, None),
                            0x23: ('LR', 'FIBER', 4, None), # 20km
                            0x24: ('LR', 'FIBER', 4, None), # 40km
                            0x25: ('DR', 'FIBER', 1, None),
                            0x26: ('FR', 'FIBER', 1, None),
                            0x27: ('LR', 'FIBER', 1, None)}

        if ext_spec_compliance in comp_code_to_attrs:
            ms.interface = comp_code_to_attrs[ext_spec_compliance][0]
            ms.cable_class = comp_code_to_attrs[ext_spec_compliance][1]
            ms.lane_count = comp_code_to_attrs[ext_spec_compliance][2]
            if comp_code_to_attrs[ext_spec_compliance][2] is not None:
                ms.special_fields['fec_hint'] = comp_code_to_attrs[ext_spec_compliance][3]
        else:
            # Try device tech
            dev_tech = read_eeprom_byte(eeprom, QSFP28_DEVICE_TECH_ADDR) & set_bits([4,5,6,7])
            if dev_tech > ((1 << 7) | (1 << 4)):
                ms.cable_class = 'DAC'
                ms.interface = 'CR'

        if ms.cable_class in ['DAC', 'ACC', 'AOC']:
            # Can potentially be breakout
            ms.breakout = self.get_cable_breakout(eeprom)

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
        if self.media_summary is None:
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.lane_count

    def get_cable_breakout(self, eeprom):
        # Try to build based on far-end count
        far_end = read_eeprom_byte(eeprom, QSFP28_FAR_END_IMPL_ADDR) & set_bits([4,5,6])
        if far_end > 0:
            far_end = far_end >> 4            
            return ['1x1', '1x1', '1x1', '1x1', '1x4', '2x2', '1x2'][far_end]
        # Default is 1x1
        return '1x1'
    def get_display_name(self, eeprom):
        display_name = build_media_display_name(self.media_summary)

        return display_name
    def get_connector_type(self, eeprom):
        connector_code = read_eeprom_byte(eeprom, QSFP28_CONNECTOR_ADDR)
        return get_connector_name(connector_code)
    def get_power_rating_max(self, eeprom):
        power_max_code = read_eeprom_byte(eeprom, QSFP28_MAX_POWER_CLASS_ADDR) 

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
        return float(read_eeprom_byte(eeprom, QSFP28_MAX_POWER_RAW_ADDR)) * 0.1 
    def get_form_factor(self, eeprom):
        return 'QSFP28'

    def get_vendor_name(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, QSFP28_VENDOR_NAME_ADDR, 16)

    def get_vendor_part_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, QSFP28_VENDOR_PART_NUM_ADDR, 16)

    def get_vendor_serial_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, QSFP28_VENDOR_SERIAL_NUM_ADDR, 16)

    def get_vendor_oui(self, eeprom):
        # 3 bytes, raw
        oui_bytes = read_eeprom_multi_byte(eeprom, QSFP28_VENDOR_OUI_ADDR, media_eeprom_address(offset=QSFP28_VENDOR_OUI_ADDR.offset+3))
        # Print OUI as hyphen seperated hex formatted bytes
        return '-'.join('{:02X}'.format(n) for n in oui_bytes)

    def get_vendor_revision(self, eeprom):
        # 2 bytes
        return extract_string_from_eeprom(eeprom, QSFP28_VENDOR_REVISION_ADDR, 2)

    def get_vendor_date_code(self, eeprom):
        # 8 bytes, strict formatting
        date_code = extract_string_from_eeprom(eeprom, QSFP28_VENDOR_DATE_CODE_ADDR, 8)
        return parse_date_code(date_code)
    def __init__(self, eeprom):
        self.media_summary = self._get_media_summary(eeprom)
