########################################################################
# DellEMC
#
# Module contains the ext media drivers for SFP modules
#
########################################################################

from ext_media_utils import *
from ext_media_handler_base import media_static_info

SFP_LENGTH_ADDR = media_eeprom_address(offset=18)
SFP_INFINIBAND_COMPLIANCE_ADDR = media_eeprom_address(offset=3)
SFP_ETH_COMPLIANCE_ADDR = media_eeprom_address(offset=6)
SFP_CONNECTOR_ADDR = media_eeprom_address(offset=2)
SFP_VENDOR_NAME_ADDR = media_eeprom_address(offset=20)
SFP_VENDOR_PART_NUM_ADDR = media_eeprom_address(offset=40)
SFP_VENDOR_REVISION_ADDR = media_eeprom_address(offset=56)
SFP_VENDOR_SERIAL_NUM_ADDR = media_eeprom_address(offset=68)
SFP_VENDOR_OUI_ADDR = media_eeprom_address(offset=37)
SFP_VENDOR_DATE_CODE_ADDR = media_eeprom_address(offset=84)

class sfp(media_static_info):
    def get_cable_length_detailed(self, eeprom):
        return float(read_eeprom_byte(eeprom, SFP_LENGTH_ADDR))

    # Get a summary of the media info
    def _get_media_summary(self, eeprom):
        ms = media_summary()
        # To be enhanced. 1G is low prio now

        ms.form_factor = self.get_form_factor(eeprom)
        ms.cable_length = self.get_cable_length_detailed(eeprom)
        ms.speed = 1000
        ms.lane_count = self.get_lane_count(eeprom)
        ms.breakout = self.get_cable_breakout(eeprom)
        ms.cable_class = 'FIBER'
        # Lots of condensed media info can be found in bytes 3-10
        # Byte 3, first 4 bits has 1G infiniband compliance 
        xcvr_compliance_1g = read_eeprom_byte(eeprom, SFP_INFINIBAND_COMPLIANCE_ADDR) & set_bits([0,1,2,3])

        if xcvr_compliance_1g > 0:
            # Multiple can be set. Pick the most significant bit
            if xcvr_compliance_1g & set_bits([3]):
                ms.interface = 'SX'
            elif xcvr_compliance_1g & set_bits([2]):
                ms.interface = 'LX'
            elif xcvr_compliance_1g & set_bits([1]):
                ms.interface = 'SR'
                ms.cable_class = 'ACC'
            elif xcvr_compliance_1g & set_bits([0]):
                ms.interface = 'CR'
                ms.cable_class = 'DAC'
        eth_compliance = read_eeprom_byte(eeprom, SFP_ETH_COMPLIANCE_ADDR)
        
        if eth_compliance > 0:
            if eth_compliance & set_bits([7]):
                ms.interface = 'PX'
            elif eth_compliance & set_bits([6]):
                ms.interface = 'BX'
            elif eth_compliance & set_bits([5]):
                ms.interface = 'FX'
                ms.speed = 100
            elif eth_compliance & set_bits([4]):
                ms.interface = 'LX'
                ms.speed = 100
            elif eth_compliance & set_bits([3]):
                ms.interface = 'T'
                ms.cable_class = 'RJ45'
            elif eth_compliance & set_bits([2]):
                ms.interface = 'CX'
            elif eth_compliance & set_bits([1]):
                ms.interface = 'LX'
            elif eth_compliance & set_bits([0]):
                ms.interface = 'SX'

        if ms.interface is None:
            # Finally use cable type to estimate 
            connector_type = read_eeprom_byte(eeprom, SFP_CONNECTOR_ADDR)
            if connector_type == 0x22:
                ms.interface = 'T'
                ms.cable_class = 'RJ45'
            elif connector_type in [0x23, 0x21]:
                ms.interface = 'CR'
                ms.cable_class = 'DAC'

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
        connector_code = read_eeprom_byte(eeprom, SFP_CONNECTOR_ADDR)
        return get_connector_name(connector_code)
    def get_power_rating_max(self, eeprom):
        # Constant upper limit for SFP
        return 1.5
    def get_form_factor(self, eeprom):
        return 'SFP'

    def get_vendor_name(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, SFP_VENDOR_NAME_ADDR, 16)

    def get_vendor_part_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, SFP_VENDOR_PART_NUM_ADDR, 16)

    def get_vendor_serial_number(self, eeprom):
        # 16 bytes
        return extract_string_from_eeprom(eeprom, SFP_VENDOR_SERIAL_NUM_ADDR, 16)

    def get_vendor_oui(self, eeprom):
        # 3 bytes, raw
        oui_bytes = read_eeprom_multi_byte(eeprom, SFP_VENDOR_OUI_ADDR, media_eeprom_address(offset=SFP_VENDOR_OUI_ADDR.offset+3))
        # Print OUI as hyphen seperated hex formatted bytes
        return '-'.join('{:02X}'.format(n) for n in oui_bytes)

    def get_vendor_revision(self, eeprom):
        # 4 bytes
        return extract_string_from_eeprom(eeprom, SFP_VENDOR_REVISION_ADDR, 4)

    def get_vendor_date_code(self, eeprom):
        # 8 bytes, strict formatting
        date_code = extract_string_from_eeprom(eeprom, SFP_VENDOR_DATE_CODE_ADDR, 8)
        return parse_date_code(date_code)
    def __init__(self, eeprom):
        self.media_summary = self._get_media_summary(eeprom)
