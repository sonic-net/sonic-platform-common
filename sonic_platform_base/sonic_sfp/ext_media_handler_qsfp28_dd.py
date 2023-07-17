########################################################################
# DellEMC
#
# Module contains the ext media drivers for QSFP28 modules
#
########################################################################

from ext_media_utils import *
from ext_media_handler_base import media_static_info
# Mostly not implemented

QSFP28_DD_CMIS_3_LENGTH_ADDR = media_eeprom_address(offset=202)
QSFP28_DD_CMIS_1_LENGTH_ADDR = media_eeprom_address(offset=146)


class qsfp28_dd(media_static_info):
    def get_cable_length_detailed(self, eeprom):
        # CMIS Rev 2.x and below use QSFPx style
        if get_cmis_version(eeprom) < 0x30:
            return float(read_eeprom_byte(eeprom, QSFP28_DD_CMIS_1_LENGTH_ADDR))

        length_code = read_eeprom_byte(eeprom, QSFP28_DD_CMIS_3_LENGTH_ADDR)

        # Upper 2 bits is multiplier in powers of 10, starting from 0.1
        multiplier = float( (length_code & set_bits([6,7])) >> 6)
        multiplier = 0.1 * (10**multiplier)

        # Lower 6 bits is an integer scaling factor
        scale = length_code & set_bits([q for q in range(0,6)])

        return float(multiplier) * float(scale)
    def get_form_factor(self, eeprom):
        return 'QSFP28-DD'
    def __init__(self, eeprom=None):
        # Support pending
        return
