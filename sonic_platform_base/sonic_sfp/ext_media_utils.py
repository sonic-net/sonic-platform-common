########################################################################
# DellEMC
#
# Module contains common classes and utilities for other components
# of the extended media functionality
#
########################################################################

DEFAULT_NO_DATA_VALUE = 'N/A'

# Connector codes are common to all form-factors
connector_code_to_name_map = {
                0x00: DEFAULT_NO_DATA_VALUE,
                0x01: 'SC',
                0x02: 'FC Style 1 copper',
                0x03: 'FC Style 2 copper',
                0x04: 'BNC/TNC',
                0x05: 'FC coax headers',
                0x06: 'Fiberjack',
                0x07: 'LC',
                0x08: 'MT-RJ',
                0x09: 'MU',
                0x0A: 'SG',
                0x0B: 'Optical Pigtail',
                0x0C: 'MPOx12',
                0x0D: 'MPOx16',
                # 0x0E-0x1F are reserved
                0x20: 'HSSDC II',
                0x21: 'Copper pigtail',
                0x22: 'RJ45',
                0x23: 'No separable connector',
                0x24: 'MXC 2x16',
                0x25: 'CS',
                0x26: 'SN (Mini CS)',
                0x27: 'MPO 2x12',
                0x28: 'MPO 1x16'
                # > 0x29 Reserved or Custom
}
def get_connector_name(conn_code):
    return connector_code_to_name_map.get(conn_code, DEFAULT_NO_DATA_VALUE)

A0 = 0
class media_eeprom_address:
    """
    Addressing for media eeprom.
    """
    eeprom_bank_default = 0
    eeprom_device_default = A0
    eeprom_page_default = 0
    eeprom_offset_default = 0
    eeprom_size = 256
    def __init__(self, device=eeprom_device_default, bank=eeprom_bank_default, page=eeprom_page_default, offset=eeprom_offset_default):
        self.device = device
        self.bank = bank #Banks not yet supported 
        self.page = page
        self.offset = offset

def set_bits(bits, val=0):
    """
    Takesa list of bit indices in list bits and sets them in value
    Returns val with the bits set.
    """
    for pos in bits:
        val |= (1 << pos)
    return val
def read_eeprom_byte(eeprom, addr):
    # Simple for now. Expect cached 
    return eeprom[addr.offset]

def read_eeprom_multi_byte(eeprom, addr_start, addr_end):
    # Simple for now. Expect cached 
    return eeprom[addr_start.offset:addr_end.offset]

def vendor_char_arr_to_ascii_str(char_arr):
    return (''.join(chr(ch) for ch in char_arr)).strip()

def extract_string_from_eeprom(eeprom, addr_start, length):
    addr_end = media_eeprom_address(offset=addr_start.offset+length)
    return vendor_char_arr_to_ascii_str(read_eeprom_multi_byte(eeprom, addr_start, addr_end))

def parse_date_code(date_code):
    # Input format: YYMMDDAB as ASCII
    # YY: year, starting from 0 to mean 2000, and increasing
    # MM: month, 01 to 12, for Jan to Dec
    # DD: day, 01 to 31. Linear map
    # AB: lot code, may be empty

    # Output: YYYY-MM-DD:AB
    try:
        date = '20{}-{}-{}'.format(date_code[0:2], date_code[2:4], date_code[4:6])
        if len(date_code) > 6:
            lot_code = date_code[6:]
            if lot_code not in ['', ' ', '  ']:
                date = date + ':' + lot_code
    except:
        return DEFAULT_NO_DATA_VALUE 
    return date

class media_summary:
    """
    Class with attrs summarizing basic media info.
    """
    def __init__(self, form_factor= '',speed=None, interface=None, lane_count=None, cable_class=None, breakout=None, cable_length=0.0, special_fields=dict()):
        self.speed = speed
        self.interface = interface
        self.lane_count = lane_count
        self.cable_class = cable_class
        self.breakout = breakout
        self.cable_length = cable_length
        self.form_factor = form_factor
        self.special_fields = special_fields

def is_separable(media_summ):
    """
    Is connector separable?
    Hence is the cable/fiber removable?
    """
    return media_summ.cable_class not in ['DAC', 'AOC', 'ACC']

# Build conformant display name from media summary
def build_media_display_name(media_summ):

    """
    See github doc for naming rules 
    """
    if media_summ.form_factor is None:
        return DEFAULT_NO_DATA_VALUE

    form_factor_part = media_summ.form_factor
    media_interface_part = media_summ.interface

    # breakout is formatted as 1x# where # is the far end count, a number of 1,2,4,8,16
    num_far_ends = media_summ.breakout.split("x")[1]

    lane_count_per_far_end = str(media_summ.lane_count / (int(num_far_ends)))
 
    # Format 1dp and add unit of Meters
    length_part = "-{:.1f}".format(media_summ.cable_length) + 'M'

    speed = str(media_summ.speed/1000/int(num_far_ends)) + 'G'

    straight_form = ''
    # Cleanup 
    if lane_count_per_far_end is '1':
        lane_count_per_far_end = ''
    if media_summ.speed <= 1000:
        speed = str(media_summ.speed)
    if is_separable(media_summ) or media_summ.cable_length == 0.0:
        # No length shown for seperable media or zero len (due to eeprom error)
        length_part = ''
    else:
        straight_form = '-'+str(media_summ.cable_class)
    straight_form = speed + 'BASE-'+ media_interface_part + lane_count_per_far_end + straight_form

    breakout_form = straight_form
    # Breakout case, add parens
    if num_far_ends is not '1':
        breakout_form = num_far_ends + 'x('+straight_form+')'

    display_name = form_factor_part + ' '+ breakout_form + length_part
    return display_name

def get_cmis_version(eeprom):
    CMIS_VER_ADDR = media_eeprom_address(offset=1)
    return read_eeprom_byte(eeprom, CMIS_VER_ADDR)