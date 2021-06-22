from sonic_platform_base.sfp_base import SfpBase

# SFP status definition, shall be aligned with the definition in get_change_event() of ChassisBase
SFP_STATUS_REMOVED = '0'
SFP_STATUS_INSERTED = '1'

# SFP error code dictinary, new elements can be added if new errors need to be supported.
SFP_ERRORS_BLOCKING_MASK = 0x02
SFP_ERRORS_GENERIC_MASK = 0x0000FFFE
SFP_ERRORS_VENDOR_SPECIFIC_MASK = 0xFFFF0000

def is_error_block_eeprom_reading(error_bits):
    return 0 != (error_bits & SFP_ERRORS_BLOCKING_MASK)


def has_vendor_specific_error(error_bits):
    return 0 != (error_bits & SFP_ERRORS_VENDOR_SPECIFIC_MASK)


def fetch_generic_error_description(error_bits):
    generic_error_bits = (error_bits & SFP_ERRORS_GENERIC_MASK)
    error_descriptions = []
    if generic_error_bits:
        for error_bit, error_description in SfpBase.SFP_ERROR_BIT_TO_DESCRIPTION_DICT.items():
            if error_bit & generic_error_bits:
                error_descriptions.append(error_description)
    return error_descriptions


def detect_port_in_error_status(logical_port_name, status_tbl):
    rec, fvp = status_tbl.get(logical_port_name)
    if rec:
        status_dict = dict(fvp)
        error = status_dict.get('error')
        return SfpBase.SFP_ERROR_DESCRIPTION_BLOCKING in error
    return False

