import json
import os

from sonic_py_common import device_info, logger
from xcvrd import xcvrd

g_optics_si_dict = {}

SYSLOG_IDENTIFIER = "xcvrd"
helper_logger = logger.Logger(SYSLOG_IDENTIFIER)

def get_optics_si_settings_value(physical_port, lane_speed, key, vendor_name_str):
    GLOBAL_MEDIA_SETTINGS_KEY = 'GLOBAL_MEDIA_SETTINGS'
    PORT_MEDIA_SETTINGS_KEY = 'PORT_MEDIA_SETTINGS'
    DEFAULT_KEY = 'Default'
    SPEED_KEY = str(lane_speed) + 'G_SPEED'
    RANGE_SEPARATOR = '-'
    COMMA_SEPARATOR = ','
    default_dict = {}
    optics_si_dict = {}

    # Keys under global media settings can be a list or range or list of ranges
    # of physical port numbers. Below are some examples
    # 1-32
    # 1,2,3,4,5
    # 1-4,9-12

    if GLOBAL_MEDIA_SETTINGS_KEY in g_optics_si_dict:
        for keys in g_optics_si_dict[GLOBAL_MEDIA_SETTINGS_KEY]:
            if COMMA_SEPARATOR in keys:
                port_list = keys.split(COMMA_SEPARATOR)
                for port in port_list:
                    if RANGE_SEPARATOR in port:
                        if xcvrd.check_port_in_range(port, physical_port):
                            optics_si_dict = g_optics_si_dict[GLOBAL_MEDIA_SETTINGS_KEY][keys]
                            break
                    elif str(physical_port) == port:
                        optics_si_dict = g_optics_si_dict[GLOBAL_MEDIA_SETTINGS_KEY][keys]
                        break

            elif RANGE_SEPARATOR in keys:
                if xcvrd.check_port_in_range(keys, physical_port):
                    optics_si_dict = g_optics_si_dict[GLOBAL_MEDIA_SETTINGS_KEY][keys]

            key_dict = {}
            if SPEED_KEY in optics_si_dict:
                if key in optics_si_dict[SPEED_KEY]:
                    key_dict = optics_si_dict[SPEED_KEY]
                    return  key_dict[key]
                elif vendor_name_str in optics_si_dict[SPEED_KEY]:
                    key_dict = optics_si_dict[SPEED_KEY]
                    return  key_dict[vendor_name_str]
                elif DEFAULT_KEY in optics_si_dict[SPEED_KEY]:
                    key_dict = optics_si_dict[SPEED_KEY]
                    default_dict = key_dict[DEFAULT_KEY]

    optics_si_dict = {}

    if PORT_MEDIA_SETTINGS_KEY in g_optics_si_dict:
        for keys in g_optics_si_dict[PORT_MEDIA_SETTINGS_KEY]:
            if int(keys) == physical_port:
                optics_si_dict = g_optics_si_dict[PORT_MEDIA_SETTINGS_KEY][keys]
                break
        if len(optics_si_dict) == 0:
            if len(default_dict) != 0:
                return default_dict
            else:
                helper_logger.log_error("Error: No values for physical port '{}'".format(physical_port))
            return {}

        key_dict = {}
        if SPEED_KEY in optics_si_dict:
            if key in optics_si_dict[SPEED_KEY]:
                key_dict = optics_si_dict[SPEED_KEY]
                return  key_dict[key]
            elif vendor_name_str in optics_si_dict[SPEED_KEY]:
                key_dict = optics_si_dict[SPEED_KEY]
                return  key_dict[vendor_name_str]
            elif DEFAULT_KEY in optics_si_dict[SPEED_KEY]:
                key_dict = optics_si_dict[SPEED_KEY]
                default_dict = key_dict[DEFAULT_KEY]
            elif len(default_dict) != 0:
                return default_dict

    return default_dict

def get_module_vendor_key(physical_port, sfp):
    api = sfp.get_xcvr_api()
    if api is None:
        helper_logger.log_info("Module {} xcvrd api not found".format(physical_port))
        return None

    vendor_name = api.get_manufacturer()
    if vendor_name is None:
        helper_logger.log_info("Module {} vendor name not found".format(physical_port))
        return None

    vendor_pn = api.get_model()
    if vendor_pn is None:
        helper_logger.log_info("Module {} vendor part number not found".format(physical_port))
        return None

    return vendor_name.upper().strip() + '-' + vendor_pn.upper().strip(), vendor_name.upper().strip()

def fetch_optics_si_setting(physical_port, lane_speed, sfp):
    if not g_optics_si_dict:
        return

    optics_si = {}

    if not xcvrd._wrapper_get_presence(physical_port):
        helper_logger.log_info("Module {} presence not detected during notify".format(physical_port))
        return optics_si
    vendor_key, vendor_name = get_module_vendor_key(physical_port, sfp)
    if vendor_key is None or vendor_name is None:
        helper_logger.log_error("Error: No Vendor Key found for port '{}'".format(logical_port_name))
        return optics_si
    optics_si = get_optics_si_settings_value(physical_port, lane_speed, vendor_key, vendor_name)
    return optics_si

def load_optics_si_settings():
    global g_optics_si_dict
    (platform_path, _) = device_info.get_paths_to_platform_and_hwsku_dirs()

    optics_si_settings_file_path = os.path.join(platform_path, "optics_si_settings.json")
    if not os.path.isfile(optics_si_settings_file_path):
        helper_logger.log_info("No optics SI file exists")
        return {}

    with open(optics_si_settings_file_path, "r") as optics_si_file:
        g_optics_si_dict = json.load(optics_si_file)

def optics_si_present():
    if g_optics_si_dict:
        return True
    return False

