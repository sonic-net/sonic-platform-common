"""
This parser is responsible for parsing the ASIC side SerDes custom SI settings.
"""

import json
import os
import ast
import re
from natsort import natsorted

from sonic_py_common import device_info, logger
from swsscommon import swsscommon
from xcvrd import xcvrd
from .xcvr_table_helper import *

g_dict = {}

LANE_SPEED_KEY_PREFIX = "speed:"
VENDOR_KEY = 'vendor_key'
MEDIA_KEY = 'media_key'
LANE_SPEED_KEY = 'lane_speed_key'
DEFAULT_KEY = 'Default'
# This is useful if default value is desired when no match is found for lane speed key
LANE_SPEED_DEFAULT_KEY = LANE_SPEED_KEY_PREFIX + DEFAULT_KEY
SYSLOG_IDENTIFIER = "xcvrd"
helper_logger = logger.Logger(SYSLOG_IDENTIFIER)

PHYSICAL_PORT_NOT_EXIST = -1

def load_media_settings():
    global g_dict
    (platform_path, hwsku_path) = device_info.get_paths_to_platform_and_hwsku_dirs()

    # Support to fetch media_settings.json both from platform folder and HWSKU folder
    media_settings_file_path_platform = os.path.join(platform_path, "media_settings.json")
    media_settings_file_path_hwsku = os.path.join(hwsku_path, "media_settings.json")

    if os.path.isfile(media_settings_file_path_hwsku):
        media_settings_file_path = media_settings_file_path_hwsku
    elif os.path.isfile(media_settings_file_path_platform):
        media_settings_file_path = media_settings_file_path_platform
    else:
        helper_logger.log_info("xcvrd: No media file exists")
        return {}

    with open(media_settings_file_path, "r") as media_file:
        g_dict = json.load(media_file)


def media_settings_present():
    if g_dict:
        return True
    return False


def get_lane_speed_key(physical_port, port_speed, lane_count):
    """
    Get lane speed key for the given port

    Args:
        physical_port: physical port number for this logical port
        port_speed: logical port speed in Mbps
        lane_count: number of lanes for this logical port

    Returns:
        the lane speed key string, in either host electrical interface format (e.g: 'speed:200GAUI-8')
        or regular format (e.g: 'speed:25G')
        Refer to Table 4-5 of SFF-8024 for different kinds of host electrical interfaces.
    """
    sfp = xcvrd.platform_chassis.get_sfp(physical_port)
    api = sfp.get_xcvr_api()
    
    lane_speed_key = None
    if xcvrd.is_cmis_api(api):
        appl_adv_dict = api.get_application_advertisement()
        app_id = xcvrd.get_cmis_application_desired(api, lane_count, port_speed)
        if app_id and app_id in appl_adv_dict:
            host_electrical_interface_id = appl_adv_dict[app_id].get('host_electrical_interface_id')
            if host_electrical_interface_id:
                lane_speed_key = LANE_SPEED_KEY_PREFIX + host_electrical_interface_id.split()[0]
        if not lane_speed_key:
            helper_logger.log_error("No host_electrical_interface_id found for CMIS module on physical port {}"
                                    ", failed to construct lane_speed_key".format(physical_port))
    else:
        # Directly calculate lane speed and use it as key, this is especially useful for
        # non-CMIS transceivers which typically have no host_electrical_interface_id
        lane_speed_key = '{}{}G'.format(LANE_SPEED_KEY_PREFIX, port_speed // lane_count // 1000)
    return lane_speed_key


def get_media_settings_key(physical_port, transceiver_dict, port_speed, lane_count):
    sup_compliance_str = '10/40G Ethernet Compliance Code'
    sup_len_str = 'Length Cable Assembly(m)'
    sup_compliance_extended_values = ['Extended', 'Unknown']
    extended_spec_compliance_str = 'Extended Specification Compliance'
    vendor_name_str = transceiver_dict[physical_port]['manufacturer']
    vendor_pn_str = transceiver_dict[physical_port]['model']
    vendor_key = vendor_name_str.upper() + '-' + vendor_pn_str

    media_len = ''
    if transceiver_dict[physical_port]['cable_type'] == sup_len_str:
        media_len = transceiver_dict[physical_port]['cable_length']

    media_compliance_dict_str = transceiver_dict[physical_port]['specification_compliance']
    media_compliance_code = ''
    media_type = ''
    media_key = ''
    media_compliance_dict = {}

    try:
        sfp = xcvrd.platform_chassis.get_sfp(physical_port)
        api = sfp.get_xcvr_api()
        if xcvrd.is_cmis_api(api):
            media_compliance_code = media_compliance_dict_str
        else:
            media_compliance_dict = ast.literal_eval(media_compliance_dict_str)
            if sup_compliance_str in media_compliance_dict:
                media_compliance_code = media_compliance_dict[sup_compliance_str]
                # For 100G transceivers, it's usually in extended specification compliance
                if media_compliance_code in sup_compliance_extended_values and \
                        extended_spec_compliance_str in media_compliance_dict:
                    media_compliance_code = media_compliance_dict[extended_spec_compliance_str]
    except ValueError as e:
        helper_logger.log_error("Invalid value for port {} 'specification_compliance': {}".format(physical_port, media_compliance_dict_str))

    media_type = transceiver_dict[physical_port]['type_abbrv_name']

    if len(media_type) != 0:
        media_key += media_type
    if len(media_compliance_code) != 0:
        media_key += '-' + media_compliance_code
        sfp = xcvrd.platform_chassis.get_sfp(physical_port)
        api = sfp.get_xcvr_api()
        if xcvrd.is_cmis_api(api):
            if media_compliance_code == "passive_copper_media_interface":
                if media_len != 0:
                    media_key += '-' + str(media_len) + 'M'
        else:
            if media_len != 0:
                media_key += '-' + str(media_len) + 'M'
    else:
        media_key += '-' + '*'

    lane_speed_key = get_lane_speed_key(physical_port, port_speed, lane_count)
    # return (vendor_key, media_key, lane_speed_key)
    return {
        VENDOR_KEY: vendor_key,
        MEDIA_KEY: media_key,
        LANE_SPEED_KEY: lane_speed_key
    }


def is_si_per_speed_supported(media_dict):
    return LANE_SPEED_KEY_PREFIX in list(media_dict.keys())[0]


def get_serdes_si_setting_val_str(val_dict, lane_count, subport_num=0):
    """
    Get ASIC side SerDes SI settings for the given logical port (subport)

    Args:
        val_dict: dictionary containing SerDes settings for all lanes of the port
                  e.g. {'lane0': '0x1f', 'lane1': '0x1f', 'lane2': '0x1f', 'lane3': '0x1f'}
        lane_count: number of lanes for this subport
        subport_num: subport number (1-based), 0 for non-breakout case

    Returns:
        string containing SerDes settings for the given subport, separated by comma
        e.g. '0x1f,0x1f,0x1f,0x1f'
    """
    start_lane_idx = (subport_num - 1) * lane_count if subport_num else 0
    if start_lane_idx + lane_count > len(val_dict):
        helper_logger.log_notice(
            "start_lane_idx + lane_count ({}) is beyond length of {}, "
            "default start_lane_idx to 0 as a best effort".format(start_lane_idx + lane_count, val_dict)
        )
        start_lane_idx = 0
    val_list = [val_dict[lane_key] for lane_key in natsorted(val_dict)]
    # If subport_num ('subport') is not specified in config_db, return values for first lane_count number of lanes
    return ','.join(val_list[start_lane_idx:start_lane_idx + lane_count])


def get_media_settings_for_speed(settings_dict, lane_speed_key):
    """
    Get settings for the given lane speed key

    Args:
        settings_dict: dictionary used to look up the settings for the given lane speed key,
                       its key can also be regular expression pattern string.
                        e.g. {'speed:400GAUI-8': {'idriver': {'lane0': '0x1f', ...}}, ...}
                            or {'idriver': {'lane0': '0x1f', ...}, ...}
                            or {'speed:200GAUI-8|100GAUI-4|25G': {'idriver': {'lane0': '0x1f', ...}}, ...}
        lane_speed_key: the lane speed key either in host electrical interface format (e.g: 'speed:200GAUI-8')
                        or regular format (e.g: 'speed:25G')

    Returns:
        dictionary containing the settings for the given lane speed key if matched, return {} if no match
        If no lane speed key defined in input dictionary, return the input dictionary as is
    """
    if not is_si_per_speed_supported(settings_dict):
        return settings_dict
    if not lane_speed_key:
        return {}
    # Check if lane_speed_key matches any key defined in the input dictionary
    lane_speed_str = lane_speed_key[len(LANE_SPEED_KEY_PREFIX):]
    for candidate_lane_speed_key, value_dict in settings_dict.items():
        lane_speed_pattern = candidate_lane_speed_key[len(LANE_SPEED_KEY_PREFIX):]
        if re.fullmatch(lane_speed_pattern, lane_speed_str):
            return value_dict
    # If no match found, return default settings if present (defined as LANE_SPEED_DEFAULT_KEY)
    return settings_dict.get(LANE_SPEED_DEFAULT_KEY, {})


def get_media_settings_value(physical_port, key):
    GLOBAL_MEDIA_SETTINGS_KEY = 'GLOBAL_MEDIA_SETTINGS'
    PORT_MEDIA_SETTINGS_KEY = 'PORT_MEDIA_SETTINGS'
    RANGE_SEPARATOR = '-'
    COMMA_SEPARATOR = ','
    media_dict = {}
    default_dict = {}
    lane_speed_key = key[LANE_SPEED_KEY]

    def get_media_settings(key, media_dict):
        for dict_key in media_dict.keys():
            if (re.match(dict_key, key[VENDOR_KEY]) or \
                re.match(dict_key, key[VENDOR_KEY].split('-')[0]) # e.g: 'AMPHENOL-1234'
                or re.match(dict_key, key[MEDIA_KEY]) ): # e.g: 'QSFP28-40GBASE-CR4-1M'
                return get_media_settings_for_speed(media_dict[dict_key], key[LANE_SPEED_KEY])
        return None

    # Keys under global media settings can be a list or range or list of ranges
    # of physical port numbers. Below are some examples
    # 1-32
    # 1,2,3,4,5
    # 1-4,9-12

    if GLOBAL_MEDIA_SETTINGS_KEY in g_dict:
        for keys in g_dict[GLOBAL_MEDIA_SETTINGS_KEY]:
            if COMMA_SEPARATOR in keys:
                port_list = keys.split(COMMA_SEPARATOR)
                for port in port_list:
                    if RANGE_SEPARATOR in port:
                        if xcvrd.check_port_in_range(port, physical_port):
                            media_dict = g_dict[GLOBAL_MEDIA_SETTINGS_KEY][keys]
                            break
                    elif str(physical_port) == port:
                        media_dict = g_dict[GLOBAL_MEDIA_SETTINGS_KEY][keys]
                        break

            elif RANGE_SEPARATOR in keys:
                if xcvrd.check_port_in_range(keys, physical_port):
                    media_dict = g_dict[GLOBAL_MEDIA_SETTINGS_KEY][keys]

            # If there is a match in the global profile for a media type,
            # fetch those values
            media_settings = get_media_settings(key, media_dict)
            if media_settings is not None:
                return media_settings
            # Try to match 'default' key if it does not match any keys
            elif DEFAULT_KEY in media_dict:
                default_dict = get_media_settings_for_speed(media_dict[DEFAULT_KEY], lane_speed_key)

    media_dict = {}

    if PORT_MEDIA_SETTINGS_KEY in g_dict:
        for keys in g_dict[PORT_MEDIA_SETTINGS_KEY]:
            if int(keys) == physical_port:
                media_dict = g_dict[PORT_MEDIA_SETTINGS_KEY][keys]
                break

        if len(media_dict) == 0:
            if len(default_dict) != 0:
                return default_dict
            else:
                helper_logger.log_notice("No values for physical port '{}'".format(physical_port))
            return {}

        media_settings = get_media_settings(key, media_dict)
        if media_settings is not None:
            return media_settings
        # Try to match 'default' key if it does not match any keys
        elif DEFAULT_KEY in media_dict:
            return get_media_settings_for_speed(media_dict[DEFAULT_KEY], lane_speed_key)
        elif len(default_dict) != 0:
            return default_dict
    else:
        if len(default_dict) != 0:
            return default_dict

    return {}


def get_speed_lane_count_and_subport(port, cfg_port_tbl):
    port_speed, lane_count, subport_num = 0, 0, 0
    found, port_info = cfg_port_tbl.get(port)
    port_info_dict = dict(port_info)
    if found and 'speed' in port_info_dict and 'lanes' in port_info_dict:
        port_speed = int(port_info_dict['speed'])
        lanes = port_info_dict['lanes']
        lane_count = len(lanes.split(','))
        subport_num = int(port_info_dict.get('subport', subport_num))
    else:
        helper_logger.log_error("No info found for port {} in cfg_port_tbl".format(port))
    return port_speed, lane_count, subport_num


def notify_media_setting(logical_port_name, transceiver_dict,
                         xcvr_table_helper, port_mapping):

    if not media_settings_present():
        return

    if not xcvr_table_helper:
        helper_logger.log_error("Notify media setting: xcvr_table_helper "
                                "not initialized for lport {}".format(logical_port_name))
        return

    if not xcvr_table_helper.is_npu_si_settings_update_required(logical_port_name, port_mapping):
        helper_logger.log_notice("Notify media setting: Media settings already "
                                 "notified for lport {}".format(logical_port_name))
        return

    asic_index = port_mapping.get_asic_id_for_logical_port(logical_port_name)

    port_speed, lane_count, subport_num = get_speed_lane_count_and_subport(logical_port_name, xcvr_table_helper.get_cfg_port_tbl(asic_index))

    ganged_port = False
    ganged_member_num = 1

    physical_port_list = port_mapping.logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("Error: No physical ports found for logical port '{}'".format(logical_port_name))
        return PHYSICAL_PORT_NOT_EXIST

    if len(physical_port_list) > 1:
        ganged_port = True

    for physical_port in physical_port_list:
        if not xcvrd._wrapper_get_presence(physical_port):
            helper_logger.log_info("Media {} presence not detected during notify".format(physical_port))
            continue
        if physical_port not in transceiver_dict:
            helper_logger.log_error("Media {} eeprom not populated in transceiver dict".format(physical_port))
            continue

        port_name = xcvrd.get_physical_port_name(logical_port_name,
                                           ganged_member_num, ganged_port)
        
        ganged_member_num += 1
        key = get_media_settings_key(physical_port, transceiver_dict, port_speed, lane_count)
        helper_logger.log_notice("Retrieving media settings for port {} speed {} num_lanes {}, using key {}".format(logical_port_name, port_speed, lane_count, key))
        media_dict = get_media_settings_value(physical_port, key)

        if len(media_dict) == 0:
            helper_logger.log_info("Error in obtaining media setting for {}".format(logical_port_name))
            return

        fvs = swsscommon.FieldValuePairs(len(media_dict))

        index = 0
        helper_logger.log_notice("Publishing ASIC-side SI setting for port {} in APP_DB:".format(logical_port_name))
        for media_key in media_dict:
            if type(media_dict[media_key]) is dict:
                val_str = get_serdes_si_setting_val_str(media_dict[media_key], lane_count, subport_num)
            else:
                val_str = media_dict[media_key]
            helper_logger.log_notice("{}:({},{}) ".format(index, str(media_key), str(val_str)))
            fvs[index] = (str(media_key), str(val_str))
            index += 1

        xcvr_table_helper.get_app_port_tbl(asic_index).set(port_name, fvs)
        xcvr_table_helper.get_state_port_tbl(asic_index).set(logical_port_name, [(NPU_SI_SETTINGS_SYNC_STATUS_KEY, NPU_SI_SETTINGS_NOTIFIED_VALUE)])
        helper_logger.log_notice("Notify media setting: Published ASIC-side SI setting "
                                 "for lport {} in APP_DB".format(logical_port_name))
