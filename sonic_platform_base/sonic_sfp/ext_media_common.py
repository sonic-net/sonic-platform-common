########################################################################
# DellEMC
#
# Module contains common classes and functions for other components
# of the extended media functionality
#
########################################################################

from ext_media_utils import read_eeprom_byte, media_eeprom_address, set_bits, get_cmis_version
import ext_media_handler_sfp as ext_media_handler_sfp
import ext_media_handler_sfp_plus as ext_media_handler_sfp_plus
import ext_media_handler_sfp28 as ext_media_handler_sfp28
import ext_media_handler_sfp56_dd as ext_media_handler_sfp56_dd
import ext_media_handler_qsfp_plus as ext_media_handler_qsfp_plus
import ext_media_handler_qsfp28 as ext_media_handler_qsfp28
import ext_media_handler_qsfp28_dd as ext_media_handler_qsfp28_dd
import ext_media_handler_qsfp56_dd as ext_media_handler_qsfp56_dd

# Read the first length bytes for use in field determination
# So far that's all needed. This improves performance
def populate_eeprom_cache(path, offset=0, length=256):
    eeprom = list()
    try:
        ee = open(path, 'rb')
        ee.seek(offset)
        if length == 1:
            eeprom.append(ord(ee.read(1)))
        else:
            tmp = ee.read(length)
            eeprom = [ord(j) for j in tmp]
        ee.close()
    except Exception as e:
        # print("EEPROM read of {} failed with exception {}".format(path, e))
        pass
    return eeprom


"""
The following functions are used to determine the form-factor 
This is needed so we can know which driver module to proceed with
"""

def get_fc_speeds(fc_code):
    # For SFPx, read byte 10

    fc_speed_list = list()
    xcvr_fc_info = fc_code
    # Each bit in 0-7 matches a certain speed supported
    bit_to_fc_speed = [100*8, 0, 200*8, 3200*8, 400*8, 1600*8, 800*8, 1200*8]
    # If bit 1 is set, fields are invalid 
    if xcvr_fc_info & (1 << 1):
        return fc_speed_list
    for i in range(0, 8):
        if i == 1:
            continue
        if xcvr_fc_info & (1<<i):
            fc_speed_list.append(bit_to_fc_speed[i])

    if len(fc_speed_list) == 0:
        return [0]
    return fc_speed_list

def get_max_fc_speed(fc_code):
    return max(get_fc_speeds(fc_code))

def is_sfp(eeprom):
    # Conditions:
    # Byte 0: bits 0-7: Identifier     = 0x03, 0x0B              -> Still ambiguous
    # Byte 3: bits 4-7: 10G Compliance = 0                 -> Still ambiguous
    # Max FC Speed <= 1200mbps                             -> Still ambiguous
    # Byte 6: 1G Eth Compliance  != 0

    if read_eeprom_byte(eeprom, media_eeprom_address(offset=0)) != 0x03:
        return False

    if read_eeprom_byte(eeprom, media_eeprom_address(offset=3)) & set_bits([4,5,6,7]):
        return False
    
    if get_max_fc_speed(read_eeprom_byte(eeprom, media_eeprom_address(offset=10))) > 1200:
        return False

    if read_eeprom_byte(eeprom, media_eeprom_address(offset=6)) == 0:
        return False

    return True

def is_sfp28(eeprom):
    # Byte 0: bits 0-7: Identifier     = 0x03              -> Still ambiguous
    # Byte 36: bits 0-7: Extended Spec Compliance has to be in set (0x01, 0x02, 0x03,0x04, 0x08, 0x0B, 0x0C,0x0D,0x18, 0x19)

    if read_eeprom_byte(eeprom, media_eeprom_address(offset=0)) != 0x03:
        return False
    if read_eeprom_byte(eeprom, media_eeprom_address(offset=36)) not in [0x01, 0x02, 0x03,0x04, 0x08, 0x0B, 0x0C,0x0D,0x18, 0x19]:
        return False
    if read_eeprom_byte(eeprom, media_eeprom_address(offset=2)) == 0x22:
        return False
    return True

def is_sfp_plus(eeprom):
    # Determine by exclusion.
    # Byte 0 = 0x03 can be SFP, SFP+, SFP28
    if read_eeprom_byte(eeprom, media_eeprom_address(offset=0)) != 0x03:
        return False

    # If rj45, can only be sfp or sfp+
    if read_eeprom_byte(eeprom, media_eeprom_address(offset=2)) == 0x22:
        return not is_sfp(eeprom)
    return not is_sfp(eeprom) and not is_sfp28(eeprom)

def is_qsfp_plus(eeprom):
    if read_eeprom_byte(eeprom, media_eeprom_address(offset=0)) not in [0x0C, 0x0D, 0x1E]:
        return False
    return True

def is_qsfp28(eeprom):
    if read_eeprom_byte(eeprom, media_eeprom_address(offset=0)) != 0x11:
        return False
    return True

def is_qsfp28_dd(eeprom):
    if read_eeprom_byte(eeprom, media_eeprom_address(offset=0)) != 0x18:
        return False

    # Ideally 200G should not be coded with ver 3.0
    if get_cmis_version(eeprom) >= 0x30:
        return False
    return True
def is_qsfp56_dd(eeprom):
    if read_eeprom_byte(eeprom, media_eeprom_address(offset=0)) != 0x18:
        return False
    return not is_qsfp28_dd(eeprom)

def is_sfp56_dd(eeprom):
    if read_eeprom_byte(eeprom, media_eeprom_address(offset=0)) != 0x1A:
        return False
    return True

"""
Maps the handler to the name, and form factor driver module
"""
form_factor_handler_to_ff_info = {is_sfp:   ('SFP', ext_media_handler_sfp),
                            is_sfp_plus:    ('SFP+', ext_media_handler_sfp_plus),
                            is_sfp28:       ('SFP28', ext_media_handler_sfp28),
                            is_sfp56_dd:    ('SFP56-DD', ext_media_handler_sfp56_dd),
                            is_qsfp_plus:   ('QSFP+', ext_media_handler_qsfp_plus),
                            is_qsfp28:      ('QSFP28', ext_media_handler_qsfp28),
                            is_qsfp28_dd:   ('QSFP28-DD', ext_media_handler_qsfp28_dd),
                            is_qsfp56_dd:   ('QSFP56-DD', ext_media_handler_qsfp56_dd)
                            }

"""
Returns the form factor name and handler functions
"""
def get_form_factor_info(eeprom_bytes):
    for func in form_factor_handler_to_ff_info:
        if func(eeprom_bytes):
            return form_factor_handler_to_ff_info[func]
    return (None, None)