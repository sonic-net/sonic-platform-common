########################################################################
# DellEMC
#
# Module contains the ext media drivers for QSFP56-DD modules
#
########################################################################

from ext_media_utils import *
from ext_media_handler_base import media_static_info

QSFP56_DD_CMIS_1_LENGTH_ADDR = media_eeprom_address(offset=146)
QSFP56_DD_CMIS_3_LENGTH_ADDR = media_eeprom_address(offset=202)

QSFP56_DD_CMIS_3_MEDIA_TYPE_ENCODING_ADDR =  media_eeprom_address(offset=85)
QSFP56_DD_CMIS_3_DEFAULT_MODULE_MEDIA_INTERFACE_ADDR =  media_eeprom_address(offset=87)
QSFP56_DD_CMIS_3_DEFAULT_LANE_COUNT_ADDR =  media_eeprom_address(offset=88)
QSFP56_DD_CMIS_3_MEDIA_INTERFACE_TECH_ADDR =  media_eeprom_address(offset=212)
QSFP56_DD_CMIS_3_FAR_END_COUNT_ADDR =  media_eeprom_address(offset=211)
QSFP56_DD_CMIS_3_CONNECTOR_ADDR = media_eeprom_address(offset=203)
QSFP56_DD_CMIS_3_MAX_POWER_CLASS_ADDR = media_eeprom_address(offset=200)
QSFP56_DD_CMIS_3_MAX_POWER_RAW_ADDR = media_eeprom_address(offset=201)

QSFP56_DD_CMIS_3_VENDOR_NAME_ADDR = media_eeprom_address(offset=129)
QSFP56_DD_CMIS_3_VENDOR_PART_NUM_ADDR = media_eeprom_address(offset=148)
QSFP56_DD_CMIS_3_VENDOR_REVISION_ADDR = media_eeprom_address(offset=164)
QSFP56_DD_CMIS_3_VENDOR_SERIAL_NUM_ADDR = media_eeprom_address(offset=166)
QSFP56_DD_CMIS_3_VENDOR_OUI_ADDR = media_eeprom_address(offset=145)
QSFP56_DD_CMIS_3_VENDOR_DATE_CODE_ADDR = media_eeprom_address(offset=182)


QSFP56_DD_CMIS_3_OPTICAL_MMF_TABLE = {
                                        0x0F: ('SR', 'FIBER', 16, None),
                                        0x10: ('SR', 'FIBER', 8, None),
                                        0x11: ('SR', 'FIBER', 4, None),
                                        0x1A: ('BIDI', 'FIBER', 8, None) # Special. Has name override to SR4.2 
}
QSFP56_DD_CMIS_3_OPTICAL_SMF_TABLE = {
                                        0x1A: ('FR', 'FIBER', 8, None),
                                        0x1B: ('LR', 'FIBER', 8, None),
                                        0x42: ('ER', 'FIBER', 8, None),
                                        0x1C: ('DR', 'FIBER', 4, None),
                                        0x1D: ('FR', 'FIBER', 4, None),
                                        0x43: ('LR', 'FIBER', 4, None),
                                        0x1E: ('LR', 'FIBER', 4, None)
}
QSFP56_DD_CMIS_3_PASSIVE_CU_TABLE = {
                                        0x01: ('CR', 'DAC', 8, None),
                                        0xBF: ('CR', 'E-LPBK', 8, None) # Effectively a DAC
}
# Active cable may be AOC or ACC. Need to check byte 212 (media interface technology)
QSFP56_DD_CMIS_3_ACTIVE_CABLE_TABLE = {
                                        0x01: ('SR', 'AOC', 8, 'BER:1e-12'),
                                        0x02: ('SR', 'AOC', 8, 'BER:5e-5'),
                                        0x03: ('SR', 'AOC', 8, 'BER:2.6e-4'),
                                        0x04: ('SR', 'AOC', 8, 'BER:1e-6'),
                                        0xBF: ('CR', 'E-LPBK', 8, None),
}

QSFP56_DD_CMIS_3_MEDIA_TYPE_TO_MODULE_TYPE_TABLE = {
                                        0x01: QSFP56_DD_CMIS_3_OPTICAL_MMF_TABLE,
                                        0x02: QSFP56_DD_CMIS_3_OPTICAL_SMF_TABLE,
                                        0x03: QSFP56_DD_CMIS_3_PASSIVE_CU_TABLE,
                                        0x04: QSFP56_DD_CMIS_3_ACTIVE_CABLE_TABLE
}

class qsfp56_dd(media_static_info):
    def cmis_ver_check(fn):
        def gn(self, eeprom):
            if get_cmis_version(eeprom) < 0x30:
                # Cannot proceed. Not supported
                return None
            return fn(self, eeprom)
        return gn

    def get_cable_length_detailed(self, eeprom):
        # CMIS Rev 2.x and below use QSFPx style
        if get_cmis_version(eeprom) < 0x30:
            return float(read_eeprom_byte(eeprom, QSFP56_DD_CMIS_1_LENGTH_ADDR))

        length_code = read_eeprom_byte(eeprom, QSFP56_DD_CMIS_3_LENGTH_ADDR)

        # Upper 2 bits is multiplier in powers of 10, starting from 0.1
        multiplier = float( (length_code & set_bits([6,7])) >> 6)
        multiplier = 0.1 * (10**multiplier)

        # Lower 6 bits is an integer scaling factor
        scale = length_code & set_bits([q for q in range(0,6)])

        return float(multiplier) * float(scale)

    # Get a summary of the media info
    @cmis_ver_check
    def _get_media_summary(self, eeprom):
        ms = media_summary()

        # Default 
        ms.form_factor = self.get_form_factor(eeprom)
        ms.cable_length = self.get_cable_length_detailed(eeprom)
        ms.speed = 400*1000
        ms.lane_count = 8
        ms.breakout = '1x1'
        ms.cable_class = 'FIBER'

        module_type_encoding = read_eeprom_byte(eeprom, QSFP56_DD_CMIS_3_MEDIA_TYPE_ENCODING_ADDR)
        if module_type_encoding not in QSFP56_DD_CMIS_3_MEDIA_TYPE_TO_MODULE_TYPE_TABLE:
            return None
        
        module_type_table = QSFP56_DD_CMIS_3_MEDIA_TYPE_TO_MODULE_TYPE_TABLE[module_type_encoding]
        
        module_media_interface = read_eeprom_byte(eeprom, QSFP56_DD_CMIS_3_DEFAULT_MODULE_MEDIA_INTERFACE_ADDR)

        if module_media_interface not in module_type_table:
            return None
        ms.interface = module_type_table[module_media_interface][0]
        ms.cable_class = module_type_table[module_media_interface][1]
        ms.lane_count = module_type_table[module_media_interface][2] # Can be overriden
        if module_type_table[module_media_interface][3] is not None:
            ms.special_fields['fec_hint'] = module_type_table[module_media_interface][3]

        # Active cables can either be ACC or AOC. Need to check media interface tech
        if ms.cable_class is 'AOC':
            media_interface_tech = read_eeprom_byte(eeprom, QSFP56_DD_CMIS_3_MEDIA_INTERFACE_TECH_ADDR)
            if media_interface_tech in [0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F]:
                ms.cable_class = 'ACC'
                ms.interface = 'SR'

        # Check if standard field overrides
        lane_count = self._get_lane_count(eeprom)
        if lane_count is not None:
            ms.lane_count = lane_count
    
        ms.breakout = self.get_cable_breakout(eeprom)

        # If no interface, discard defaults
        if ms.interface is None:
            return None
        return ms
    def get_media_interface(self, eeprom):
        if self.media_summary is None:
            # Summary builder could not find it 
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.interface
    def get_cable_class(self, eeprom):
        if self.media_summary is None:
            # Summary builder could not find it 
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.cable_class

    # Standard way, unless overridden by application code
    def _get_lane_count(self, eeprom):
        lane_count = read_eeprom_byte(eeprom, QSFP56_DD_CMIS_3_DEFAULT_LANE_COUNT_ADDR)
        # Only care about media lane count (lower 4 bits)
        lane_count = lane_count & 0x0F
        if lane_count > 0 and lane_count <= 8:
            return lane_count
        return None
    def get_lane_count(self, eeprom):
        if self.media_summary is None:
            return DEFAULT_NO_DATA_VALUE
        return self.media_summary.lane_count

    def get_cable_breakout(self, eeprom):
        # Check for far-end (breakout)
        far_end_count = read_eeprom_byte(eeprom, QSFP56_DD_CMIS_3_FAR_END_COUNT_ADDR)
        # Lower 4 bits
        far_end_count = far_end_count & 0x1F
        # There are 26 different ways. Only care about 1x1, 1x2, 1x4, 1x8
        far_end_count_map = {0x00: '1x1',
                                0x01: '1x8',
                                0x02: '1x1',
                                0x03: '1x2',
                                0x0C: '1x4'}

        if far_end_count in far_end_count_map:
            return far_end_count_map[far_end_count]
        # Default
        return '1x1'
    def get_display_name(self, eeprom):
        display_name = build_media_display_name(self.media_summary)
        if display_name is not None:
            # Weird naming convention exception due to proprietary stuff
            display_name = display_name.replace('BIDI8', 'SR4.2')
        return display_name
    def get_connector_type(self, eeprom):
        connector_code = read_eeprom_byte(eeprom, QSFP56_DD_CMIS_3_CONNECTOR_ADDR)
        return get_connector_name(connector_code)

    def get_power_rating_max(self, eeprom):
        power_max_code = (read_eeprom_byte(eeprom, QSFP56_DD_CMIS_3_MAX_POWER_CLASS_ADDR) >> 5) & 0x07
        power_old_method = 0.0
        if power_max_code < 0x07:
            # Hard-coded power values
            power_old_method = [1.5, 2.0, 2.5, 3.5, 4.0, 4.5, 5.0][power_max_code]
        # Alternatively, power is encoded as unsigned int in units of 0.25W
        return max(power_old_method, float(read_eeprom_byte(eeprom, QSFP56_DD_CMIS_3_MAX_POWER_RAW_ADDR)) * 0.25)

    def get_form_factor(self, eeprom):
        return 'QSFP56-DD'

    def get_vendor_name(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, QSFP56_DD_CMIS_3_VENDOR_NAME_ADDR, 16)

    def get_vendor_part_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, QSFP56_DD_CMIS_3_VENDOR_PART_NUM_ADDR, 16)

    def get_vendor_serial_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, QSFP56_DD_CMIS_3_VENDOR_SERIAL_NUM_ADDR, 16)

    def get_vendor_oui(self, eeprom):
        # 3 bytes, raw
        oui_bytes = read_eeprom_multi_byte(eeprom, QSFP56_DD_CMIS_3_VENDOR_OUI_ADDR, media_eeprom_address(offset=QSFP56_DD_CMIS_3_VENDOR_OUI_ADDR.offset+3))
        # Print OUI as hyphen seperated hex formatted bytes
        return '-'.join('{:02X}'.format(n) for n in oui_bytes)

    def get_vendor_revision(self, eeprom):
        # 2 bytes
        return extract_string_from_eeprom(eeprom, QSFP56_DD_CMIS_3_VENDOR_REVISION_ADDR, 2)

    def get_vendor_date_code(self, eeprom):
        # 8 bytes, strict formatting
        date_code = extract_string_from_eeprom(eeprom, QSFP56_DD_CMIS_3_VENDOR_DATE_CODE_ADDR, 8)
        return parse_date_code(date_code)
    def __init__(self, eeprom):
        self.media_summary = self._get_media_summary(eeprom)
