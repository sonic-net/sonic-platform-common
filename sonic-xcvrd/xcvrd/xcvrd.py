#!/usr/bin/env python3

"""
    xcvrd
    Transceiver information update daemon for SONiC
"""

try:
    import ast
    import copy
    import json
    import os
    import signal
    import sys
    import threading
    import time
    import datetime
    import subprocess
    import argparse
    import re
    import traceback
    import ctypes

    from natsort import natsorted
    from sonic_py_common import daemon_base, device_info, logger
    from sonic_py_common import multi_asic
    from swsscommon import swsscommon

    from .xcvrd_utilities import sfp_status_helper
    from .sff_mgr import SffManagerTask
    from .xcvrd_utilities.xcvr_table_helper import XcvrTableHelper
    from .xcvrd_utilities import port_event_helper
    from .xcvrd_utilities.port_event_helper import PortChangeObserver
    from .xcvrd_utilities import media_settings_parser
    from .xcvrd_utilities import optics_si_parser
    
    from sonic_platform_base.sonic_xcvr.api.public.c_cmis import CmisApi

except ImportError as e:
    raise ImportError(str(e) + " - required module not found")

#
# Constants ====================================================================
#

SYSLOG_IDENTIFIER = "xcvrd"

PLATFORM_SPECIFIC_MODULE_NAME = "sfputil"
PLATFORM_SPECIFIC_CLASS_NAME = "SfpUtil"

TRANSCEIVER_STATUS_TABLE_SW_FIELDS = ["status", "error", "cmis_state"]

CMIS_STATE_UNKNOWN   = 'UNKNOWN'
CMIS_STATE_INSERTED  = 'INSERTED'
CMIS_STATE_DP_DEINIT = 'DP_DEINIT'
CMIS_STATE_AP_CONF   = 'AP_CONFIGURED'
CMIS_STATE_DP_ACTIVATE = 'DP_ACTIVATION'
CMIS_STATE_DP_INIT   = 'DP_INIT'
CMIS_STATE_DP_TXON   = 'DP_TXON'
CMIS_STATE_READY     = 'READY'
CMIS_STATE_REMOVED   = 'REMOVED'
CMIS_STATE_FAILED    = 'FAILED'

CMIS_TERMINAL_STATES = {
                        CMIS_STATE_FAILED,
                        CMIS_STATE_READY,
                        CMIS_STATE_REMOVED
                        }

# Mgminit time required as per CMIS spec
MGMT_INIT_TIME_DELAY_SECS = 2

# SFP insert event poll duration
SFP_INSERT_EVENT_POLL_PERIOD_MSECS = 1000

DOM_INFO_UPDATE_PERIOD_SECS = 60
STATE_MACHINE_UPDATE_PERIOD_MSECS = 60000
TIME_FOR_SFP_READY_SECS = 1

EVENT_ON_ALL_SFP = '-1'
# events definition
SYSTEM_NOT_READY = 'system_not_ready'
SYSTEM_BECOME_READY = 'system_become_ready'
SYSTEM_FAIL = 'system_fail'
NORMAL_EVENT = 'normal'
# states definition
STATE_INIT = 0
STATE_NORMAL = 1
STATE_EXIT = 2

PHYSICAL_PORT_NOT_EXIST = -1
SFP_EEPROM_NOT_READY = -2

SFPUTIL_LOAD_ERROR = 1
PORT_CONFIG_LOAD_ERROR = 2
NOT_IMPLEMENTED_ERROR = 3
SFP_SYSTEM_ERROR = 4

RETRY_TIMES_FOR_SYSTEM_READY = 24
RETRY_PERIOD_FOR_SYSTEM_READY_MSECS = 5000

RETRY_TIMES_FOR_SYSTEM_FAIL = 24
RETRY_PERIOD_FOR_SYSTEM_FAIL_MSECS = 5000

TEMP_UNIT = 'C'
VOLT_UNIT = 'Volts'
POWER_UNIT = 'dBm'
BIAS_UNIT = 'mA'

g_dict = {}
# Global platform specific sfputil class instance
platform_sfputil = None
# Global chassis object based on new platform api
platform_chassis = None

# Global logger instance for helper functions and classes
# TODO: Refactor so that we only need the logger inherited
# by DaemonXcvrd
helper_logger = logger.Logger(SYSLOG_IDENTIFIER)

#
# Helper functions =============================================================
#
def log_exception_traceback():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    msg = traceback.format_exception(exc_type, exc_value, exc_traceback)
    for tb_line in msg:
        for tb_line_split in tb_line.splitlines():
            helper_logger.log_error(tb_line_split)

def is_cmis_api(api):
   return isinstance(api, CmisApi)


def get_cmis_application_desired(api, host_lane_count, speed):
    """
    Get the CMIS application code that matches the specified host side configurations

    Args:
        api:
            XcvrApi object
        host_lane_count:
            Number of lanes on the host side
        speed:
            Integer, the port speed of the host interface

    Returns:
        Integer, the transceiver-specific application code
    """

    if speed == 0 or host_lane_count == 0:
        return None

    if not is_cmis_api(api):
        return None

    appl_dict = api.get_application_advertisement()
    for index, app_info in appl_dict.items():
        if (app_info.get('host_lane_count') == host_lane_count and
        get_interface_speed(app_info.get('host_electrical_interface_id')) == speed):
            return (index & 0xf)

    return None


def get_interface_speed(ifname):
    """
    Get the port speed from the host interface name

    Args:
        ifname: String, interface name

    Returns:
        Integer, the port speed if success otherwise 0
    """
    # see HOST_ELECTRICAL_INTERFACE of sff8024.py
    speed = 0
    if '800G' in ifname:
        speed = 800000
    elif '400G' in ifname:
        speed = 400000
    elif '200G' in ifname:
        speed = 200000
    elif '100G' in ifname or 'CAUI-4' in ifname:
        speed = 100000
    elif '50G' in ifname or 'LAUI-2' in ifname:
        speed = 50000
    elif '40G' in ifname or 'XLAUI' in ifname or 'XLPPI' in ifname:
        speed = 40000
    elif '25G' in ifname:
        speed = 25000
    elif '10G' in ifname or 'SFI' in ifname or 'XFI' in ifname:
        speed = 10000
    elif '1000BASE' in ifname:
        speed = 1000
    else:
        helper_logger.log_error("No interface speed found for: '{}'".format(ifname))
    return speed


# Get physical port name


def get_physical_port_name(logical_port, physical_port, ganged):
    if ganged:
        return logical_port + ":{} (ganged)".format(physical_port)
    else:
        return logical_port

# Get physical port name dict (port_idx to port_name)


def get_physical_port_name_dict(logical_port_name, port_mapping):
    ganged_port = False
    ganged_member_num = 1

    physical_port_list = port_mapping.logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("No physical ports found for logical port '{}'".format(logical_port_name))
        return {}

    if len(physical_port_list) > 1:
        ganged_port = True

    port_name_dict = {}
    for physical_port in physical_port_list:
        port_name = get_physical_port_name(logical_port_name, ganged_member_num, ganged_port)
        ganged_member_num += 1
        port_name_dict[physical_port] = port_name

    return port_name_dict

# Strip units and beautify


def strip_unit_and_beautify(value, unit):
    # Strip unit from raw data
    if type(value) is str:
        width = len(unit)
        if value[-width:] == unit:
            value = value[:-width]
        return value
    else:
        return str(value)


def _wrapper_get_presence(physical_port):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_sfp(physical_port).get_presence()
        except NotImplementedError:
            pass
    return platform_sfputil.get_presence(physical_port)


def _wrapper_is_replaceable(physical_port):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_sfp(physical_port).is_replaceable()
        except NotImplementedError:
            pass
    return False


def _wrapper_get_transceiver_info(physical_port):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_sfp(physical_port).get_transceiver_info()
        except NotImplementedError:
            pass
    return platform_sfputil.get_transceiver_info_dict(physical_port)

def _wrapper_get_transceiver_firmware_info(physical_port):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_sfp(physical_port).get_transceiver_info_firmware_versions()
        except NotImplementedError:
            pass
    return {}

def _wrapper_get_transceiver_dom_info(physical_port):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_sfp(physical_port).get_transceiver_bulk_status()
        except NotImplementedError:
            pass
    return platform_sfputil.get_transceiver_dom_info_dict(physical_port)


def _wrapper_get_transceiver_dom_threshold_info(physical_port):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_sfp(physical_port).get_transceiver_threshold_info()
        except NotImplementedError:
            pass
    return platform_sfputil.get_transceiver_dom_threshold_info_dict(physical_port)


def _wrapper_get_transceiver_status(physical_port):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_sfp(physical_port).get_transceiver_status()
        except NotImplementedError:
            pass
    return {}


def _wrapper_get_transceiver_pm(physical_port):
    if platform_chassis is not None:
        try:
            return platform_chassis.get_sfp(physical_port).get_transceiver_pm()
        except NotImplementedError:
            pass
    return {}

def _wrapper_is_flat_memory(physical_port):
    if platform_chassis is not None:
        try:
            sfp = platform_chassis.get_sfp(physical_port)
            api = sfp.get_xcvr_api()
            return api.is_flat_memory()
        except NotImplementedError:
            pass
    return None

# Soak SFP insert event until management init completes
def _wrapper_soak_sfp_insert_event(sfp_insert_events, port_dict):
    for key, value in list(port_dict.items()):
        if value == sfp_status_helper.SFP_STATUS_INSERTED:
            sfp_insert_events[key] = time.time()
            del port_dict[key]
        elif value == sfp_status_helper.SFP_STATUS_REMOVED:
            if key in sfp_insert_events:
                del sfp_insert_events[key]

    for key, itime in list(sfp_insert_events.items()):
        if time.time() - itime >= MGMT_INIT_TIME_DELAY_SECS:
            port_dict[key] = sfp_status_helper.SFP_STATUS_INSERTED
            del sfp_insert_events[key]

def _wrapper_get_transceiver_change_event(timeout):
    if platform_chassis is not None:
        try:
            status, events = platform_chassis.get_change_event(timeout)
            sfp_events = events.get('sfp')
            sfp_errors = events.get('sfp_error')
            return status, sfp_events, sfp_errors
        except NotImplementedError:
            pass
    status, events = platform_sfputil.get_transceiver_change_event(timeout)
    return status, events, None


def _wrapper_get_sfp_type(physical_port):
    if platform_chassis:
        try:
            sfp = platform_chassis.get_sfp(physical_port)
        except (NotImplementedError, AttributeError):
            return None
        try:
            return sfp.sfp_type
        except (NotImplementedError, AttributeError):
            pass
    return None


def _wrapper_get_sfp_error_description(physical_port):
    if platform_chassis:
        try:
            return platform_chassis.get_sfp(physical_port).get_error_description()
        except NotImplementedError:
            pass
    return None

# Remove unnecessary unit from the raw data

def beautify_dom_info_dict(dom_info_dict, physical_port):
    for k, v in dom_info_dict.items():
        if k == 'temperature':
            dom_info_dict[k] = strip_unit_and_beautify(v, TEMP_UNIT)
        elif k == 'voltage':
            dom_info_dict[k] = strip_unit_and_beautify(v, VOLT_UNIT)
        elif re.match('^(tx|rx)[1-8]power$', k):
            dom_info_dict[k] = strip_unit_and_beautify(v, POWER_UNIT)
        elif re.match('^(tx|rx)[1-8]bias$', k):
            dom_info_dict[k] = strip_unit_and_beautify(v, BIAS_UNIT)
        elif type(v) is not str:
            # For all the other keys:
            dom_info_dict[k] = str(v)


def beautify_dom_threshold_info_dict(dom_info_dict):
    for k, v in dom_info_dict.items():
        if re.search('temp', k) is not None:
            dom_info_dict[k] = strip_unit_and_beautify(v, TEMP_UNIT)
        elif re.search('vcc', k) is not None:
            dom_info_dict[k] = strip_unit_and_beautify(v, VOLT_UNIT)
        elif re.search('power', k) is not None:
            dom_info_dict[k] = strip_unit_and_beautify(v, POWER_UNIT)
        elif re.search('txbias', k) is not None:
            dom_info_dict[k] = strip_unit_and_beautify(v, BIAS_UNIT)
        elif type(v) is not str:
            # For all the other keys:
            dom_info_dict[k] = str(v)


def beautify_transceiver_status_dict(transceiver_status_dict, physical_port):
    for k, v in transceiver_status_dict.items():
        if type(v) is str:
            continue
        transceiver_status_dict[k] = str(v)


def beautify_pm_info_dict(pm_info_dict, physical_port):
    for k, v in pm_info_dict.items():
        if type(v) is str:
            continue
        pm_info_dict[k] = str(v)

# Update port sfp info in db


def post_port_sfp_info_to_db(logical_port_name, port_mapping, table, transceiver_dict,
                             stop_event=threading.Event()):
    ganged_port = False
    ganged_member_num = 1

    physical_port_list = port_mapping.logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("No physical ports found for logical port '{}'".format(logical_port_name))
        return PHYSICAL_PORT_NOT_EXIST

    if len(physical_port_list) > 1:
        ganged_port = True

    for physical_port in physical_port_list:
        if stop_event.is_set():
            break

        if not _wrapper_get_presence(physical_port):
            continue

        port_name = get_physical_port_name(logical_port_name, ganged_member_num, ganged_port)
        ganged_member_num += 1

        try:
            port_info_dict = _wrapper_get_transceiver_info(physical_port)
            if port_info_dict is not None:
                is_replaceable = _wrapper_is_replaceable(physical_port)
                transceiver_dict[physical_port] = port_info_dict
                # if cmis is supported by the module
                if 'cmis_rev' in port_info_dict:
                    fvs = swsscommon.FieldValuePairs(
                        [('type', port_info_dict['type']),
                        ('vendor_rev', port_info_dict['vendor_rev']),
                        ('serial', port_info_dict['serial']),
                        ('manufacturer', port_info_dict['manufacturer']),
                        ('model', port_info_dict['model']),
                        ('vendor_oui', port_info_dict['vendor_oui']),
                        ('vendor_date', port_info_dict['vendor_date']),
                        ('connector', port_info_dict['connector']),
                        ('encoding', port_info_dict['encoding']),
                        ('ext_identifier', port_info_dict['ext_identifier']),
                        ('ext_rateselect_compliance', port_info_dict['ext_rateselect_compliance']),
                        ('cable_type', port_info_dict['cable_type']),
                        ('cable_length', str(port_info_dict['cable_length'])),
                        ('specification_compliance', port_info_dict['specification_compliance']),
                        ('nominal_bit_rate', str(port_info_dict['nominal_bit_rate'])),
                        ('application_advertisement', port_info_dict['application_advertisement']
                        if 'application_advertisement' in port_info_dict else 'N/A'),
                        ('is_replaceable', str(is_replaceable)),
                        ('dom_capability', port_info_dict['dom_capability']
                        if 'dom_capability' in port_info_dict else 'N/A'),
                        ('cmis_rev', port_info_dict['cmis_rev'] if 'cmis_rev' in port_info_dict else 'N/A'),
                        ('hardware_rev', port_info_dict['hardware_rev']
                        if 'hardware_rev' in port_info_dict else 'N/A'),
                        ('media_interface_code', port_info_dict['media_interface_code']
                        if 'media_interface_code' in port_info_dict else 'N/A'),
                        ('host_electrical_interface', port_info_dict['host_electrical_interface']
                        if 'host_electrical_interface' in port_info_dict else 'N/A'),
                        ('host_lane_count', str(port_info_dict['host_lane_count'])
                        if 'host_lane_count' in port_info_dict else 'N/A'),
                        ('media_lane_count', str(port_info_dict['media_lane_count'])
                        if 'media_lane_count' in port_info_dict else 'N/A'),
                        ('host_lane_assignment_option', str(port_info_dict['host_lane_assignment_option'])
                        if 'host_lane_assignment_option' in port_info_dict else 'N/A'),
                        ('media_lane_assignment_option', str(port_info_dict['media_lane_assignment_option'])
                        if 'media_lane_assignment_option' in port_info_dict else 'N/A'),
                        ('active_apsel_hostlane1', str(port_info_dict['active_apsel_hostlane1'])
                        if 'active_apsel_hostlane1' in port_info_dict else 'N/A'),
                        ('active_apsel_hostlane2', str(port_info_dict['active_apsel_hostlane2'])
                        if 'active_apsel_hostlane2' in port_info_dict else 'N/A'),
                        ('active_apsel_hostlane3', str(port_info_dict['active_apsel_hostlane3'])
                        if 'active_apsel_hostlane3' in port_info_dict else 'N/A'),
                        ('active_apsel_hostlane4', str(port_info_dict['active_apsel_hostlane4'])
                        if 'active_apsel_hostlane4' in port_info_dict else 'N/A'),
                        ('active_apsel_hostlane5', str(port_info_dict['active_apsel_hostlane5'])
                        if 'active_apsel_hostlane5' in port_info_dict else 'N/A'),
                        ('active_apsel_hostlane6', str(port_info_dict['active_apsel_hostlane6'])
                        if 'active_apsel_hostlane6' in port_info_dict else 'N/A'),
                        ('active_apsel_hostlane7', str(port_info_dict['active_apsel_hostlane7'])
                        if 'active_apsel_hostlane7' in port_info_dict else 'N/A'),
                        ('active_apsel_hostlane8', str(port_info_dict['active_apsel_hostlane8'])
                        if 'active_apsel_hostlane8' in port_info_dict else 'N/A'),
                        ('media_interface_technology', port_info_dict['media_interface_technology']
                        if 'media_interface_technology' in port_info_dict else 'N/A'),
                        ('supported_max_tx_power', str(port_info_dict['supported_max_tx_power'])
                        if 'supported_max_tx_power' in port_info_dict else 'N/A'),
                        ('supported_min_tx_power', str(port_info_dict['supported_min_tx_power'])
                        if 'supported_min_tx_power' in port_info_dict else 'N/A'),
                        ('supported_max_laser_freq', str(port_info_dict['supported_max_laser_freq'])
                        if 'supported_max_laser_freq' in port_info_dict else 'N/A'),
                        ('supported_min_laser_freq', str(port_info_dict['supported_min_laser_freq'])
                        if 'supported_min_laser_freq' in port_info_dict else 'N/A')
                    ])
                # else cmis is not supported by the module
                else:
                    fvs = swsscommon.FieldValuePairs([
                        ('type', port_info_dict['type']),
                        ('vendor_rev', port_info_dict['vendor_rev']),
                        ('serial', port_info_dict['serial']),
                        ('manufacturer', port_info_dict['manufacturer']),
                        ('model', port_info_dict['model']),
                        ('vendor_oui', port_info_dict['vendor_oui']),
                        ('vendor_date', port_info_dict['vendor_date']),
                        ('connector', port_info_dict['connector']),
                        ('encoding', port_info_dict['encoding']),
                        ('ext_identifier', port_info_dict['ext_identifier']),
                        ('ext_rateselect_compliance', port_info_dict['ext_rateselect_compliance']),
                        ('cable_type', port_info_dict['cable_type']),
                        ('cable_length', str(port_info_dict['cable_length'])),
                        ('specification_compliance', port_info_dict['specification_compliance']),
                        ('nominal_bit_rate', str(port_info_dict['nominal_bit_rate'])),
                        ('application_advertisement', port_info_dict['application_advertisement']
                        if 'application_advertisement' in port_info_dict else 'N/A'),
                        ('is_replaceable', str(is_replaceable)),
                        ('dom_capability', port_info_dict['dom_capability']
                        if 'dom_capability' in port_info_dict else 'N/A')
                    ])
                table.set(port_name, fvs)
            else:
                return SFP_EEPROM_NOT_READY

        except NotImplementedError:
            helper_logger.log_error("This functionality is currently not implemented for this platform")
            sys.exit(NOT_IMPLEMENTED_ERROR)

# Update port sfp firmware info in db

def post_port_sfp_firmware_info_to_db(logical_port_name, port_mapping, table,
                             stop_event=threading.Event(), firmware_info_cache=None):
    for physical_port, physical_port_name in get_physical_port_name_dict(logical_port_name, port_mapping).items():
        if stop_event.is_set():
            break

        if not _wrapper_get_presence(physical_port):
            continue

        try:
            if firmware_info_cache is not None and physical_port in firmware_info_cache:
                # If cache is enabled and firmware information is in cache, just read from cache, no need read from EEPROM
                transceiver_firmware_info_dict = firmware_info_cache[physical_port]
            else:
                transceiver_firmware_info_dict = _wrapper_get_transceiver_firmware_info(physical_port)
                if firmware_info_cache is not None:
                    # If cache is enabled, put firmware information to cache
                    firmware_info_cache[physical_port] = transceiver_firmware_info_dict
            if transceiver_firmware_info_dict:
                fvs = swsscommon.FieldValuePairs([(k, v) for k, v in transceiver_firmware_info_dict.items()])
                table.set(physical_port_name, fvs)
            else:
                return SFP_EEPROM_NOT_READY

        except NotImplementedError:
            helper_logger.log_error("Transceiver firmware info functionality is currently not implemented for this platform")
            sys.exit(NOT_IMPLEMENTED_ERROR)

# Update port dom threshold info in db


def post_port_dom_threshold_info_to_db(logical_port_name, port_mapping, table,
                                       stop=threading.Event(), dom_th_info_cache=None):
    ganged_port = False
    ganged_member_num = 1

    physical_port_list = port_mapping.logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("No physical ports found for logical port '{}'".format(logical_port_name))
        return PHYSICAL_PORT_NOT_EXIST

    if len(physical_port_list) > 1:
        ganged_port = True

    for physical_port in physical_port_list:
        if stop.is_set():
            break

        if not _wrapper_get_presence(physical_port):
            continue

        if _wrapper_is_flat_memory(physical_port) == True:
            continue

        port_name = get_physical_port_name(logical_port_name,
                                           ganged_member_num, ganged_port)
        ganged_member_num += 1

        try:
            if dom_th_info_cache is not None and physical_port in dom_th_info_cache:
                # If cache is enabled and there is a cache, no need read from EEPROM, just read from cache
                dom_info_dict = dom_th_info_cache[physical_port]
            else:
                dom_info_dict = _wrapper_get_transceiver_dom_threshold_info(physical_port)
                if dom_th_info_cache is not None:
                    # If cache is enabled, put dom threshold infomation to cache
                    dom_th_info_cache[physical_port] = dom_info_dict
            if dom_info_dict is not None:
                beautify_dom_threshold_info_dict(dom_info_dict)
                fvs = swsscommon.FieldValuePairs([(k, v) for k, v in dom_info_dict.items()])
                table.set(port_name, fvs)
            else:
                return SFP_EEPROM_NOT_READY

        except NotImplementedError:
            helper_logger.log_error("This functionality is currently not implemented for this platform")
            sys.exit(NOT_IMPLEMENTED_ERROR)

# Update port dom sensor info in db


def post_port_dom_info_to_db(logical_port_name, port_mapping, table, stop_event=threading.Event(), dom_info_cache=None):
    for physical_port, physical_port_name in get_physical_port_name_dict(logical_port_name, port_mapping).items():
        if stop_event.is_set():
            break

        if not _wrapper_get_presence(physical_port):
            continue

        if _wrapper_is_flat_memory(physical_port) == True:
            continue

        try:
            if dom_info_cache is not None and physical_port in dom_info_cache:
                # If cache is enabled and dom information is in cache, just read from cache, no need read from EEPROM
                dom_info_dict = dom_info_cache[physical_port]
            else:
                dom_info_dict = _wrapper_get_transceiver_dom_info(physical_port)
                if dom_info_cache is not None:
                    # If cache is enabled, put dom information to cache
                    dom_info_cache[physical_port] = dom_info_dict
            if dom_info_dict is not None:
                beautify_dom_info_dict(dom_info_dict, physical_port)
                fvs = swsscommon.FieldValuePairs([(k, v) for k, v in dom_info_dict.items()])
                table.set(physical_port_name, fvs)
            else:
                return SFP_EEPROM_NOT_READY

        except NotImplementedError:
            helper_logger.log_error("This functionality is currently not implemented for this platform")
            sys.exit(NOT_IMPLEMENTED_ERROR)

# Update port pm info in db


def post_port_pm_info_to_db(logical_port_name, port_mapping, table, stop_event=threading.Event(), pm_info_cache=None):
    for physical_port, physical_port_name in get_physical_port_name_dict(logical_port_name, port_mapping).items():
        if stop_event.is_set():
            break

        if not _wrapper_get_presence(physical_port):
            continue

        if _wrapper_is_flat_memory(physical_port) == True:
            continue

        if pm_info_cache is not None and physical_port in pm_info_cache:
            # If cache is enabled and pm info is in cache, just read from cache, no need read from EEPROM
            pm_info_dict = pm_info_cache[physical_port]
        else:
            pm_info_dict = _wrapper_get_transceiver_pm(physical_port)
            if pm_info_cache is not None:
                # If cache is enabled, put dom information to cache
                pm_info_cache[physical_port] = pm_info_dict
        if pm_info_dict is not None:
            # Skip if empty (i.e. get_transceiver_pm API is not applicable for this xcvr)
            if not pm_info_dict:
                continue
            beautify_pm_info_dict(pm_info_dict, physical_port)
            fvs = swsscommon.FieldValuePairs([(k, v) for k, v in pm_info_dict.items()])
            table.set(physical_port_name, fvs)
        else:
            return SFP_EEPROM_NOT_READY

# Delete port dom/sfp info from db


def del_port_sfp_dom_info_from_db(logical_port_name, port_mapping, int_tbl, dom_tbl, dom_threshold_tbl, pm_tbl, firmware_info_tbl):
    for physical_port_name in get_physical_port_name_dict(logical_port_name, port_mapping).values():
        try:
            if int_tbl:
                int_tbl._del(physical_port_name)
            if dom_tbl:
                dom_tbl._del(physical_port_name)
            if dom_threshold_tbl:
                dom_threshold_tbl._del(physical_port_name)
            if pm_tbl:
                pm_tbl._del(physical_port_name)
            if firmware_info_tbl:
                firmware_info_tbl._del(physical_port_name)

        except NotImplementedError:
            helper_logger.log_error("This functionality is currently not implemented for this platform")
            sys.exit(NOT_IMPLEMENTED_ERROR)


def check_port_in_range(range_str, physical_port):
    RANGE_SEPARATOR = '-'

    range_list = range_str.split(RANGE_SEPARATOR)
    start_num = int(range_list[0].strip())
    end_num = int(range_list[1].strip())
    if start_num <= physical_port <= end_num:
        return True
    return False


def waiting_time_compensation_with_sleep(time_start, time_to_wait):
    time_now = time.time()
    time_diff = time_now - time_start
    if time_diff < time_to_wait:
        time.sleep(time_to_wait - time_diff)

# Update port SFP status table for SW fields on receiving SFP change event


def update_port_transceiver_status_table_sw(logical_port_name, status_tbl, status, error_descriptions='N/A'):
    fvs = swsscommon.FieldValuePairs([('status', status), ('error', error_descriptions)])
    status_tbl.set(logical_port_name, fvs)

def get_cmis_state_from_state_db(lport, status_tbl):
    found, transceiver_status_dict = status_tbl.get(lport)
    if found and 'cmis_state' in dict(transceiver_status_dict):
        return dict(transceiver_status_dict)['cmis_state']
    else:
        return CMIS_STATE_UNKNOWN


# Update port SFP status table for HW fields


def update_port_transceiver_status_table_hw(logical_port_name, port_mapping,
                                            table, stop_event=threading.Event(), transceiver_status_cache=None):
    for physical_port, physical_port_name in get_physical_port_name_dict(logical_port_name, port_mapping).items():
        if stop_event.is_set():
            break

        if not _wrapper_get_presence(physical_port):
            continue

        if transceiver_status_cache is not None and physical_port in transceiver_status_cache:
            # If cache is enabled and status info is in cache, just read from cache, no need read from EEPROM
            transceiver_status_dict = transceiver_status_cache[physical_port]
        else:
            transceiver_status_dict = _wrapper_get_transceiver_status(physical_port)
            if transceiver_status_cache is not None:
                # If cache is enabled, put status info to cache
                transceiver_status_cache[physical_port] = transceiver_status_dict
        if transceiver_status_dict is not None:
            # Skip if empty (i.e. get_transceiver_status API is not applicable for this xcvr)
            if not transceiver_status_dict:
                continue
            beautify_transceiver_status_dict(transceiver_status_dict, physical_port)
            fvs = swsscommon.FieldValuePairs([(k, v) for k, v in transceiver_status_dict.items()])
            table.set(physical_port_name, fvs)
        else:
            return SFP_EEPROM_NOT_READY

# Delete port from SFP status table


def delete_port_from_status_table_sw(logical_port_name, status_tbl):
    for f in TRANSCEIVER_STATUS_TABLE_SW_FIELDS:
        status_tbl.hdel(logical_port_name, f)

# Delete port from SFP status table for HW fields which are fetched from EEPROM


def delete_port_from_status_table_hw(logical_port_name, port_mapping, status_tbl):
    for physical_port_name in get_physical_port_name_dict(logical_port_name, port_mapping).values():
        found, fvs = status_tbl.get(physical_port_name)
        if not found:
            return
        status_dict = dict(fvs)
        for f in status_dict.keys():
            if f in TRANSCEIVER_STATUS_TABLE_SW_FIELDS:
                continue
            status_tbl.hdel(physical_port_name, f)

def is_fast_reboot_enabled():
    fastboot_enabled = subprocess.check_output('sonic-db-cli STATE_DB hget "FAST_RESTART_ENABLE_TABLE|system" enable', shell=True, universal_newlines=True)
    return "true" in fastboot_enabled


def is_warm_reboot_enabled():
    warmstart = swsscommon.WarmStart()
    warmstart.initialize("xcvrd", "pmon")
    warmstart.checkWarmStart("xcvrd", "pmon", False)
    is_warm_start = warmstart.isWarmStart()
    return is_warm_start

#
# Helper classes ===============================================================
#

# Thread wrapper class for CMIS transceiver management

class CmisManagerTask(threading.Thread):

    CMIS_MAX_RETRIES     = 3
    CMIS_DEF_EXPIRED     = 60 # seconds, default expiration time
    CMIS_MODULE_TYPES    = ['QSFP-DD', 'QSFP_DD', 'OSFP', 'OSFP-8X', 'QSFP+C']
    CMIS_MAX_HOST_LANES    = 8

    def __init__(self, namespaces, port_mapping, main_thread_stop_event, skip_cmis_mgr=False):
        threading.Thread.__init__(self)
        self.name = "CmisManagerTask"
        self.exc = None
        self.task_stopping_event = threading.Event()
        self.main_thread_stop_event = main_thread_stop_event
        self.port_dict = {}
        self.port_mapping = copy.deepcopy(port_mapping)
        self.xcvr_table_helper = XcvrTableHelper(namespaces)
        self.isPortInitDone = False
        self.isPortConfigDone = False
        self.skip_cmis_mgr = skip_cmis_mgr
        self.namespaces = namespaces

    def log_debug(self, message):
        helper_logger.log_debug("CMIS: {}".format(message))

    def log_notice(self, message):
        helper_logger.log_notice("CMIS: {}".format(message))

    def log_error(self, message):
        helper_logger.log_error("CMIS: {}".format(message))

    def update_port_transceiver_status_table_sw_cmis_state(self, lport, cmis_state_to_set):
        asic_index = self.port_mapping.get_asic_id_for_logical_port(lport)
        status_table = self.xcvr_table_helper.get_status_tbl(asic_index)
        if status_table is None:
            helper_logger.log_error("status_table is None while updating "
                                    "sw CMIS state for lport {}".format(lport))
            return

        fvs = swsscommon.FieldValuePairs([('cmis_state', cmis_state_to_set)])
        status_table.set(lport, fvs)

    def on_port_update_event(self, port_change_event):
        if port_change_event.event_type not in [port_change_event.PORT_SET, port_change_event.PORT_DEL]:
            return

        lport = port_change_event.port_name
        pport = port_change_event.port_index

        if lport in ['PortInitDone']:
            self.isPortInitDone = True
            return

        if lport in ['PortConfigDone']:
            self.isPortConfigDone = True
            return

        # Skip if it's not a physical port
        if not lport.startswith('Ethernet'):
            return

        # Skip if the physical index is not available
        if pport is None:
            return

        # Skip if the port/cage type is not a CMIS
        # 'index' can be -1 if STATE_DB|PORT_TABLE
        if lport not in self.port_dict:
            self.port_dict[lport] = {}

        if port_change_event.port_dict is None:
            return

        if port_change_event.event_type == port_change_event.PORT_SET:
            if pport >= 0:
                self.port_dict[lport]['index'] = pport
            if 'speed' in port_change_event.port_dict and port_change_event.port_dict['speed'] != 'N/A':
                self.port_dict[lport]['speed'] = port_change_event.port_dict['speed']
            if 'lanes' in port_change_event.port_dict:
                self.port_dict[lport]['lanes'] = port_change_event.port_dict['lanes']
            if 'host_tx_ready' in port_change_event.port_dict:
                self.port_dict[lport]['host_tx_ready'] = port_change_event.port_dict['host_tx_ready']
            if 'admin_status' in port_change_event.port_dict:
                self.port_dict[lport]['admin_status'] = port_change_event.port_dict['admin_status']
            if 'laser_freq' in port_change_event.port_dict:
                self.port_dict[lport]['laser_freq'] = int(port_change_event.port_dict['laser_freq'])
            if 'tx_power' in port_change_event.port_dict:
                self.port_dict[lport]['tx_power'] = float(port_change_event.port_dict['tx_power'])
            if 'subport' in port_change_event.port_dict:
                self.port_dict[lport]['subport'] = int(port_change_event.port_dict['subport'])

            self.force_cmis_reinit(lport, 0)
        else:
            self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_REMOVED)

    def get_cmis_dp_init_duration_secs(self, api):
        return api.get_datapath_init_duration()/1000

    def get_cmis_dp_deinit_duration_secs(self, api):
        return api.get_datapath_deinit_duration()/1000

    def get_cmis_module_power_up_duration_secs(self, api):
        return api.get_module_pwr_up_duration()/1000

    def get_cmis_module_power_down_duration_secs(self, api):
        return api.get_module_pwr_down_duration()/1000

    def get_cmis_host_lanes_mask(self, api, appl, host_lane_count, subport):
        """
        Retrieves mask of active host lanes based on appl, host lane count and subport

        Args:
            api:
                XcvrApi object
            appl:
                Integer, the transceiver-specific application code
            host_lane_count:
                Integer, number of lanes on the host side
            subport:
                Integer, 1-based logical port number of the physical port after breakout
                         0 means port is a non-breakout port

        Returns:
            Integer, a mask of the active lanes on the host side
            e.g. 0x3 for lane 0 and lane 1.
        """
        host_lanes_mask = 0

        if appl is None or host_lane_count <= 0 or subport < 0:
            self.log_error("Invalid input to get host lane mask - appl {} host_lane_count {} "
                            "subport {}!".format(appl, host_lane_count, subport))
            return host_lanes_mask

        host_lane_assignment_option = api.get_host_lane_assignment_option(appl)
        host_lane_start_bit = (host_lane_count * (0 if subport == 0 else subport - 1))
        if host_lane_assignment_option & (1 << host_lane_start_bit):
            host_lanes_mask = ((1 << host_lane_count) - 1) << host_lane_start_bit
        else:
            self.log_error("Unable to find starting host lane - host_lane_assignment_option {}"
                            " host_lane_start_bit {} host_lane_count {} subport {} appl {}!".format(
                            host_lane_assignment_option, host_lane_start_bit, host_lane_count,
                            subport, appl))

        return host_lanes_mask

    def get_cmis_media_lanes_mask(self, api, appl, lport, subport):
        """
        Retrieves mask of active media lanes based on appl, lport and subport

        Args:
            api:
                XcvrApi object
            appl:
                Integer, the transceiver-specific application code
            lport:
                String, logical port name
            subport:
                Integer, 1-based logical port number of the physical port after breakout
                         0 means port is a non-breakout port

        Returns:
            Integer, a mask of the active lanes on the media side
            e.g. 0xf for lane 0, lane 1, lane 2 and lane 3.
        """
        media_lanes_mask = 0
        media_lane_count = self.port_dict[lport]['media_lane_count']
        media_lane_assignment_option = self.port_dict[lport]['media_lane_assignment_options']

        if appl < 1 or media_lane_count <= 0 or subport < 0:
            self.log_error("Invalid input to get media lane mask - appl {} media_lane_count {} "
                            "lport {} subport {}!".format(appl, media_lane_count, lport, subport))
            return media_lanes_mask
	
        media_lane_start_bit = (media_lane_count * (0 if subport == 0 else subport - 1))
        if media_lane_assignment_option & (1 << media_lane_start_bit):
            media_lanes_mask = ((1 << media_lane_count) - 1) << media_lane_start_bit
        else:
            self.log_error("Unable to find starting media lane - media_lane_assignment_option {}"
                            " media_lane_start_bit {} media_lane_count {} lport {} subport {} appl {}!".format(
                            media_lane_assignment_option, media_lane_start_bit, media_lane_count,
                            lport, subport, appl))

        return media_lanes_mask

    def is_appl_reconfigure_required(self, api, app_new):
        """
	   Reset app code if non default app code needs to configured 
        """
        for lane in range(self.CMIS_MAX_HOST_LANES):
            app_cur = api.get_application(lane)
            if app_cur != 0 and app_cur != app_new:
                return True
        return False

    def is_cmis_application_update_required(self, api, app_new, host_lanes_mask):
        """
        Check if the CMIS application update is required

        Args:
            api:
                XcvrApi object
            app_new:
                Integer, the transceiver-specific application code for the new application
            host_lanes_mask:
                Integer, a bitmask of the lanes on the host side
                e.g. 0x5 for lane 0 and lane 2.

        Returns:
            Boolean, true if application update is required otherwise false
        """
        if api.is_flat_memory() or app_new <= 0 or host_lanes_mask <= 0:
            self.log_error("Invalid input while checking CMIS update required - is_flat_memory {}"
                            "app_new {} host_lanes_mask {}!".format(
                            api.is_flat_memory(), app_new, host_lanes_mask))
            return False

        app_old = 0
        for lane in range(self.CMIS_MAX_HOST_LANES):
            if ((1 << lane) & host_lanes_mask) == 0:
                continue
            if app_old == 0:
                app_old = api.get_application(lane)
            elif app_old != api.get_application(lane):
                self.log_notice("Not all the lanes are in the same application mode "
                                "app_old {} current app {} lane {} host_lanes_mask {}".format(
                                app_old, api.get_application(lane), lane, host_lanes_mask))
                self.log_notice("Forcing application update...")
                return True

        if app_old == app_new:
            skip = True
            dp_state = api.get_datapath_state()
            conf_state = api.get_config_datapath_hostlane_status()
            for lane in range(self.CMIS_MAX_HOST_LANES):
                if ((1 << lane) & host_lanes_mask) == 0:
                    continue
                name = "DP{}State".format(lane + 1)
                if dp_state[name] != 'DataPathActivated':
                    skip = False
                    break
                name = "ConfigStatusLane{}".format(lane + 1)
                if conf_state[name] != 'ConfigSuccess':
                    skip = False
                    break
            return (not skip)
        return True

    def force_cmis_reinit(self, lport, retries=0):
        """
        Try to force the restart of CMIS state machine
        """
        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_INSERTED)
        self.port_dict[lport]['cmis_retries'] = retries
        self.port_dict[lport]['cmis_expired'] = None # No expiration

    def check_module_state(self, api, states):
        """
        Check if the CMIS module is in the specified state

        Args:
            api:
                XcvrApi object
            states:
                List, a string list of states

        Returns:
            Boolean, true if it's in the specified state, otherwise false
        """
        return api.get_module_state() in states

    def check_config_error(self, api, host_lanes_mask, states):
        """
        Check if the CMIS configuration states are in the specified state

        Args:
            api:
                XcvrApi object
            host_lanes_mask:
                Integer, a bitmask of the lanes on the host side
                e.g. 0x5 for lane 0 and lane 2.
            states:
                List, a string list of states

        Returns:
            Boolean, true if all lanes are in the specified state, otherwise false
        """
        done = True
        cerr = api.get_config_datapath_hostlane_status()
        for lane in range(self.CMIS_MAX_HOST_LANES):
            if ((1 << lane) & host_lanes_mask) == 0:
                continue
            key = "ConfigStatusLane{}".format(lane + 1)
            if cerr[key] not in states:
                done = False
                break

        return done

    def check_datapath_init_pending(self, api, host_lanes_mask):
        """
        Check if the CMIS datapath init is pending

        Args:
            api:
                XcvrApi object
            host_lanes_mask:
                Integer, a bitmask of the lanes on the host side
                e.g. 0x5 for lane 0 and lane 2.

        Returns:
            Boolean, true if all lanes are pending datapath init, otherwise false
        """
        pending = True
        dpinit_pending_dict = api.get_dpinit_pending()
        for lane in range(self.CMIS_MAX_HOST_LANES):
            if ((1 << lane) & host_lanes_mask) == 0:
                continue
            key = "DPInitPending{}".format(lane + 1)
            if not dpinit_pending_dict[key]:
                pending = False
                break

        return pending

    def check_datapath_state(self, api, host_lanes_mask, states):
        """
        Check if the CMIS datapath states are in the specified state

        Args:
            api:
                XcvrApi object
            host_lanes_mask:
                Integer, a bitmask of the lanes on the host side
                e.g. 0x5 for lane 0 and lane 2.
            states:
                List, a string list of states

        Returns:
            Boolean, true if all lanes are in the specified state, otherwise false
        """
        done = True
        dpstate = api.get_datapath_state()
        for lane in range(self.CMIS_MAX_HOST_LANES):
            if ((1 << lane) & host_lanes_mask) == 0:
                continue
            key = "DP{}State".format(lane + 1)
            if dpstate[key] not in states:
                done = False
                break

        return done

    def get_configured_laser_freq_from_db(self, lport):
        """
           Return the Tx power configured by user in CONFIG_DB's PORT table
        """
        freq = 0
        asic_index = self.port_mapping.get_asic_id_for_logical_port(lport)
        port_tbl = self.xcvr_table_helper.get_cfg_port_tbl(asic_index)

        found, port_info = port_tbl.get(lport)
        if found and 'laser_freq' in dict(port_info):
            freq = dict(port_info)['laser_freq']
        return int(freq)

    def get_configured_tx_power_from_db(self, lport):
        """
           Return the Tx power configured by user in CONFIG_DB's PORT table
        """
        power = 0
        asic_index = self.port_mapping.get_asic_id_for_logical_port(lport)
        port_tbl = self.xcvr_table_helper.get_cfg_port_tbl(asic_index)

        found, port_info = port_tbl.get(lport)
        if found and 'tx_power' in dict(port_info):
            power = dict(port_info)['tx_power']
        return float(power)

    def get_host_tx_status(self, lport):
        host_tx_ready = 'false'

        asic_index = self.port_mapping.get_asic_id_for_logical_port(lport)
        state_port_tbl = self.xcvr_table_helper.get_state_port_tbl(asic_index)

        found, port_info = state_port_tbl.get(lport)
        if found and 'host_tx_ready' in dict(port_info):
            host_tx_ready = dict(port_info)['host_tx_ready']
        return host_tx_ready

    def get_port_admin_status(self, lport):
        admin_status = 'down'

        asic_index = self.port_mapping.get_asic_id_for_logical_port(lport)
        cfg_port_tbl = self.xcvr_table_helper.get_cfg_port_tbl(asic_index)

        found, port_info = cfg_port_tbl.get(lport)
        if found:
            # Check admin_status too ...just in case
            admin_status = dict(port_info).get('admin_status', 'down')
        return admin_status

    def configure_tx_output_power(self, api, lport, tx_power):
        min_p, max_p = api.get_supported_power_config()
        if tx_power < min_p:
           self.log_error("{} configured tx power {} < minimum power {} supported".format(lport, tx_power, min_p))
        if tx_power > max_p:
           self.log_error("{} configured tx power {} > maximum power {} supported".format(lport, tx_power, max_p))
        return api.set_tx_power(tx_power)

    def validate_frequency_and_grid(self, api, lport, freq, grid=75):
        supported_grid, _,  _, lowf, highf = api.get_supported_freq_config()
        if freq < lowf:
            self.log_error("{} configured freq:{} GHz is lower than the supported freq:{} GHz".format(lport, freq, lowf))
            return False
        if freq > highf:
            self.log_error("{} configured freq:{} GHz is higher than the supported freq:{} GHz".format(lport, freq, highf))
            return False
        if grid == 75:
            if (supported_grid >> 7) & 0x1 != 1:
                self.log_error("{} configured freq:{}GHz supported grid:{} 75GHz is not supported".format(lport, freq, supported_grid))
                return False
            chan = int(round((freq - 193100)/25))
            if chan % 3 != 0:
                self.log_error("{} configured freq:{}GHz is NOT in 75GHz grid".format(lport, freq))
                return False
        elif grid == 100:
            if (supported_grid >> 5) & 0x1 != 1:
                self.log_error("{} configured freq:{}GHz 100GHz is not supported".format(lport, freq))
                return False
        else:
            self.log_error("{} configured freq:{}GHz {}GHz is not supported".format(lport, freq, grid))
            return False
        return True

    def configure_laser_frequency(self, api, lport, freq, grid=75):
        if api.get_tuning_in_progress():
            self.log_error("{} Tuning in progress, subport selection may fail!".format(lport))
        return api.set_laser_freq(freq, grid)

    def post_port_active_apsel_to_db(self, api, lport, host_lanes_mask):
        try:
            act_apsel = api.get_active_apsel_hostlane()
            appl_advt = api.get_application_advertisement()
        except NotImplementedError:
            helper_logger.log_error("Required feature is not implemented")
            return

        tuple_list = []
        for lane in range(self.CMIS_MAX_HOST_LANES):
            if ((1 << lane) & host_lanes_mask) == 0:
                continue
            act_apsel_lane = act_apsel.get('ActiveAppSelLane{}'.format(lane + 1), 'N/A')
            tuple_list.append(('active_apsel_hostlane{}'.format(lane + 1),
                               str(act_apsel_lane)))

        # also update host_lane_count and media_lane_count
        if len(tuple_list) > 0:
            appl_advt_act = appl_advt.get(act_apsel_lane)
            host_lane_count = appl_advt_act.get('host_lane_count', 'N/A') if appl_advt_act else 'N/A'
            tuple_list.append(('host_lane_count', str(host_lane_count)))
            media_lane_count = appl_advt_act.get('media_lane_count', 'N/A') if appl_advt_act else 'N/A'
            tuple_list.append(('media_lane_count', str(media_lane_count)))

        asic_index = self.port_mapping.get_asic_id_for_logical_port(lport)
        intf_tbl = self.xcvr_table_helper.get_intf_tbl(asic_index)
        fvs = swsscommon.FieldValuePairs(tuple_list)
        intf_tbl.set(lport, fvs)
        self.log_notice("{}: updated TRANSCEIVER_INFO_TABLE {}".format(lport, tuple_list))

    def wait_for_port_config_done(self, namespace):
        # Connect to APPL_DB and subscribe to PORT table notifications
        appl_db = daemon_base.db_connect("APPL_DB", namespace=namespace)

        sel = swsscommon.Select()
        port_tbl = swsscommon.SubscriberStateTable(appl_db, swsscommon.APP_PORT_TABLE_NAME)
        sel.addSelectable(port_tbl)

        # Make sure this daemon started after all port configured
        while not self.task_stopping_event.is_set():
            (state, c) = sel.select(port_event_helper.SELECT_TIMEOUT_MSECS)
            if state == swsscommon.Select.TIMEOUT:
                continue
            if state != swsscommon.Select.OBJECT:
                self.log_warning("sel.select() did not return swsscommon.Select.OBJECT")
                continue

            (key, op, fvp) = port_tbl.pop()
            if key in ["PortConfigDone", "PortInitDone"]:
                break

    def task_worker(self):
        self.xcvr_table_helper = XcvrTableHelper(self.namespaces)

        self.log_notice("Waiting for PortConfigDone...")
        for namespace in self.namespaces:
            self.wait_for_port_config_done(namespace)

        logical_port_list = self.port_mapping.logical_port_list
        for lport in logical_port_list:
            self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_UNKNOWN)

        # APPL_DB for CONFIG updates, and STATE_DB for insertion/removal
        port_change_observer = PortChangeObserver(self.namespaces, helper_logger,
                                                  self.task_stopping_event,
                                                  self.on_port_update_event)

        while not self.task_stopping_event.is_set():
            # Handle port change event from main thread
            port_change_observer.handle_port_update_event()

            for lport, info in self.port_dict.items():
                if self.task_stopping_event.is_set():
                    break

                if lport not in self.port_dict:
                    continue

                state = get_cmis_state_from_state_db(lport, self.xcvr_table_helper.get_status_tbl(self.port_mapping.get_asic_id_for_logical_port(lport)))
                if state in CMIS_TERMINAL_STATES or state == CMIS_STATE_UNKNOWN:
                    if state != CMIS_STATE_READY:
                        self.port_dict[lport]['appl'] = 0
                        self.port_dict[lport]['host_lanes_mask'] = 0
                    continue

                # Handle the case when Xcvrd was NOT running when 'host_tx_ready' or 'admin_status'
                # was updated or this is the first run so reconcile the above two attributes
                if 'host_tx_ready' not in self.port_dict[lport]:
                   self.port_dict[lport]['host_tx_ready'] = self.get_host_tx_status(lport)

                if 'admin_status' not in self.port_dict[lport]:
                   self.port_dict[lport]['admin_status'] = self.get_port_admin_status(lport)

                pport = int(info.get('index', "-1"))
                speed = int(info.get('speed', "0"))
                lanes = info.get('lanes', "").strip()
                subport = info.get('subport', 0)
                if pport < 0 or speed == 0 or len(lanes) < 1 or subport < 0:
                    continue

                # Desired port speed on the host side
                host_speed = speed
                host_lane_count = len(lanes.split(','))

                # double-check the HW presence before moving forward
                sfp = platform_chassis.get_sfp(pport)
                if not sfp.get_presence():
                    self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_REMOVED)
                    continue

                try:
                    # Skip if XcvrApi is not supported
                    api = sfp.get_xcvr_api()
                    if api is None:
                        self.log_error("{}: skipping CMIS state machine since no xcvr api!!!".format(lport))
                        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_READY)
                        continue

                    # Skip if it's not a paged memory device
                    if api.is_flat_memory():
                        self.log_notice("{}: skipping CMIS state machine for flat memory xcvr".format(lport))
                        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_READY)
                        continue

                    # Skip if it's not a CMIS module
                    type = api.get_module_type_abbreviation()
                    if (type is None) or (type not in self.CMIS_MODULE_TYPES):
                        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_READY)
                        continue

                    if api.is_coherent_module():
                       if 'tx_power' not in self.port_dict[lport]:
                           self.port_dict[lport]['tx_power'] = self.get_configured_tx_power_from_db(lport)
                       if 'laser_freq' not in self.port_dict[lport]:
                           self.port_dict[lport]['laser_freq'] = self.get_configured_laser_freq_from_db(lport)
                except AttributeError:
                    # Skip if these essential routines are not available
                    self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_READY)
                    continue
                except Exception as e:
                    self.log_error("{}: Exception in xcvr api: {}".format(lport, e))
                    log_exception_traceback()
                    self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_FAILED)
                    continue

                # CMIS expiration and retries
                #
                # A retry should always start over at INSETRTED state, while the
                # expiration will reset the state to INSETRTED and advance the
                # retry counter
                now = datetime.datetime.now()
                expired = self.port_dict[lport].get('cmis_expired')
                retries = self.port_dict[lport].get('cmis_retries', 0)
                host_lanes_mask = self.port_dict[lport].get('host_lanes_mask', 0)
                appl = self.port_dict[lport].get('appl', 0)
                if state != CMIS_STATE_INSERTED and (host_lanes_mask <= 0 or appl < 1):
                    self.log_error("{}: Unexpected value for host_lanes_mask {} or appl {} in "
                                    "{} state".format(lport, host_lanes_mask, appl, state))
                    self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_FAILED)
                    continue

                self.log_notice("{}: {}G, lanemask=0x{:x}, state={}, appl {} host_lane_count {} "
                                "retries={}".format(lport, int(speed/1000), host_lanes_mask,
                                state, appl, host_lane_count, retries))
                if retries > self.CMIS_MAX_RETRIES:
                    self.log_error("{}: FAILED".format(lport))
                    self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_FAILED)
                    continue

                try:
                    # CMIS state transitions
                    if state == CMIS_STATE_INSERTED:
                        self.port_dict[lport]['appl'] = get_cmis_application_desired(api, host_lane_count, host_speed)
                        if self.port_dict[lport]['appl'] is None:
                            self.log_error("{}: no suitable app for the port appl {} host_lane_count {} "
                                            "host_speed {}".format(lport, appl, host_lane_count, host_speed))
                            self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_FAILED)
                            continue
                        appl = self.port_dict[lport]['appl']
                        self.log_notice("{}: Setting appl={}".format(lport, appl))

                        self.port_dict[lport]['host_lanes_mask'] = self.get_cmis_host_lanes_mask(api,
                                                                        appl, host_lane_count, subport)
                        if self.port_dict[lport]['host_lanes_mask'] <= 0:
                            self.log_error("{}: Invalid lane mask received - host_lane_count {} subport {} "
                                            "appl {}!".format(lport, host_lane_count, subport, appl))
                            self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_FAILED)
                            continue
                        host_lanes_mask = self.port_dict[lport]['host_lanes_mask']
                        self.log_notice("{}: Setting host_lanemask=0x{:x}".format(lport, host_lanes_mask))
			
                        self.port_dict[lport]['media_lane_count'] = int(api.get_media_lane_count(appl))
                        self.port_dict[lport]['media_lane_assignment_options'] = int(api.get_media_lane_assignment_option(appl))
                        media_lane_count = self.port_dict[lport]['media_lane_count']
                        media_lane_assignment_options = self.port_dict[lport]['media_lane_assignment_options']
                        self.port_dict[lport]['media_lanes_mask'] = self.get_cmis_media_lanes_mask(api,
                                                                        appl, lport, subport)
                        if self.port_dict[lport]['media_lanes_mask'] <= 0:
                            self.log_error("{}: Invalid media lane mask received - media_lane_count {} "
                                            "media_lane_assignment_options {} subport {}"
                                            " appl {}!".format(lport, media_lane_count, media_lane_assignment_options, subport, appl))
                            self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_FAILED)
                            continue
                        media_lanes_mask = self.port_dict[lport]['media_lanes_mask']
                        self.log_notice("{}: Setting media_lanemask=0x{:x}".format(lport, media_lanes_mask))

                        if self.port_dict[lport]['host_tx_ready'] != 'true' or \
                                self.port_dict[lport]['admin_status'] != 'up':
                           self.log_notice("{} Forcing Tx laser OFF".format(lport))
                           # Force DataPath re-init
                           api.tx_disable_channel(media_lanes_mask, True)
                           self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_READY)
                           continue
                    # Configure the target output power if ZR module
                        if api.is_coherent_module():
                           tx_power = self.port_dict[lport]['tx_power']
                           # Prevent configuring same tx power multiple times
                           if 0 != tx_power and tx_power != api.get_tx_config_power():
                              if 1 != self.configure_tx_output_power(api, lport, tx_power):
                                 self.log_error("{} failed to configure Tx power = {}".format(lport, tx_power))
                              else:
                                 self.log_notice("{} Successfully configured Tx power = {}".format(lport, tx_power))

                        # Set all the DP lanes AppSel to unused(0) when non default app code needs to be configured
                        if True == self.is_appl_reconfigure_required(api, appl):
                            self.log_notice("{}: Decommissioning all lanes/datapaths to default AppSel=0".format(lport))
                            if True != api.decommission_all_datapaths():
                                self.log_notice("{}: Failed to default to AppSel=0".format(lport))
                                self.force_cmis_reinit(lport, retries + 1)
                                continue

                        need_update = self.is_cmis_application_update_required(api, appl, host_lanes_mask)

                        # For ZR module, Datapath needes to be re-initlialized on new channel selection
                        if api.is_coherent_module():
                            freq = self.port_dict[lport]['laser_freq']
                            # If user requested frequency is NOT the same as configured on the module
                            # force datapath re-initialization
                            if 0 != freq and freq != api.get_laser_config_freq():
                                if self.validate_frequency_and_grid(api, lport, freq) == True:
                                    need_update = True
                                else:
                                    # clear setting of invalid frequency config
                                    self.port_dict[lport]['laser_freq'] = 0

                        if not need_update:
                            # No application updates
                            self.log_notice("{}: no CMIS application update required...READY".format(lport))
                            self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_READY)
                            continue
                        self.log_notice("{}: force Datapath reinit".format(lport))
                        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_DP_DEINIT)
                    elif state == CMIS_STATE_DP_DEINIT:
                        # D.2.2 Software Deinitialization
                        api.set_datapath_deinit(host_lanes_mask)

                        # D.1.3 Software Configuration and Initialization
                        media_lanes_mask = self.port_dict[lport]['media_lanes_mask']
                        if not api.tx_disable_channel(media_lanes_mask, True):
                            self.log_notice("{}: unable to turn off tx power with host_lanes_mask {}".format(lport, host_lanes_mask))
                            self.port_dict[lport]['cmis_retries'] = retries + 1
                            continue

                        #Sets module to high power mode and doesn't impact datapath if module is already in high power mode
                        api.set_lpmode(False)
                        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_AP_CONF)
                        dpDeinitDuration = self.get_cmis_dp_deinit_duration_secs(api)
                        modulePwrUpDuration = self.get_cmis_module_power_up_duration_secs(api)
                        self.log_notice("{}: DpDeinit duration {} secs, modulePwrUp duration {} secs".format(lport, dpDeinitDuration, modulePwrUpDuration))
                        self.port_dict[lport]['cmis_expired'] = now + datetime.timedelta(seconds = max(modulePwrUpDuration, dpDeinitDuration))

                    elif state == CMIS_STATE_AP_CONF:
                        # Explicit control bit to apply custom Host SI settings. 
                        # It will be set to 1 and applied via set_application if 
                        # custom SI settings is applicable
                        ec = 0

                        # TODO: Use fine grained time when the CMIS memory map is available
                        if not self.check_module_state(api, ['ModuleReady']):
                            if (expired is not None) and (expired <= now):
                                self.log_notice("{}: timeout for 'ModuleReady'".format(lport))
                                self.force_cmis_reinit(lport, retries + 1)
                            continue

                        if not self.check_datapath_state(api, host_lanes_mask, ['DataPathDeactivated']):
                            if (expired is not None) and (expired <= now):
                                self.log_notice("{}: timeout for 'DataPathDeactivated state'".format(lport))
                                self.force_cmis_reinit(lport, retries + 1)
                            continue

                        if api.is_coherent_module():
                        # For ZR module, configure the laser frequency when Datapath is in Deactivated state
                           freq = self.port_dict[lport]['laser_freq']
                           if 0 != freq:
                                if 1 != self.configure_laser_frequency(api, lport, freq):
                                   self.log_error("{} failed to configure laser frequency {} GHz".format(lport, freq))
                                else:
                                   self.log_notice("{} configured laser frequency {} GHz".format(lport, freq))

                        # Stage custom SI settings
                        if optics_si_parser.optics_si_present():
                            optics_si_dict = {}
                            # Apply module SI settings if applicable
                            lane_speed = int(speed/1000)//host_lane_count
                            optics_si_dict = optics_si_parser.fetch_optics_si_setting(pport, lane_speed, sfp)
                            
                            self.log_debug("Read SI parameters for port {} from optics_si_settings.json vendor file:".format(lport))
                            for key, sub_dict in optics_si_dict.items():
                                self.log_debug("{}".format(key))
                                for sub_key, value in sub_dict.items():
                                    self.log_debug("{}: {}".format(sub_key, str(value)))
                            
                            if optics_si_dict:
                                self.log_notice("{}: Apply Optics SI found for Vendor: {}  PN: {} lane speed: {}G".
                                                 format(lport, api.get_manufacturer(), api.get_model(), lane_speed))
                                if not api.stage_custom_si_settings(host_lanes_mask, optics_si_dict):
                                    self.log_notice("{}: unable to stage custom SI settings ".format(lport))
                                    self.force_cmis_reinit(lport, retries + 1)
                                    continue

                                # Set Explicit control bit to apply Custom Host SI settings
                                ec = 1

                        # D.1.3 Software Configuration and Initialization
                        api.set_application(host_lanes_mask, appl, ec)
                        if not api.scs_apply_datapath_init(host_lanes_mask):
                            self.log_notice("{}: unable to set application and stage DP init".format(lport))
                            self.force_cmis_reinit(lport, retries + 1)
                            continue

                        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_DP_INIT)
                    elif state == CMIS_STATE_DP_INIT:
                        if not self.check_config_error(api, host_lanes_mask, ['ConfigSuccess']):
                            if (expired is not None) and (expired <= now):
                                self.log_notice("{}: timeout for 'ConfigSuccess'".format(lport))
                                self.force_cmis_reinit(lport, retries + 1)
                            continue

                        if hasattr(api, 'get_cmis_rev'):
                            # Check datapath init pending on module that supports CMIS 5.x
                            majorRev = int(api.get_cmis_rev().split('.')[0])
                            if majorRev >= 5 and not self.check_datapath_init_pending(api, host_lanes_mask):
                                self.log_notice("{}: datapath init not pending".format(lport))
                                self.force_cmis_reinit(lport, retries + 1)
                                continue

                        # Ensure the Datapath is NOT Activated unless the host Tx siganl is good.
                        # NOTE: Some CMIS compliant modules may have 'auto-squelch' feature where
                        # the module won't take datapaths to Activated state if host tries to enable
                        # the datapaths while there is no good Tx signal from the host-side.
                        if self.port_dict[lport]['admin_status'] != 'up' or \
                                self.port_dict[lport]['host_tx_ready'] != 'true':
                            self.log_notice("{} waiting for host tx ready...".format(lport))
                            continue

                        # D.1.3 Software Configuration and Initialization
                        api.set_datapath_init(host_lanes_mask)
                        dpInitDuration = self.get_cmis_dp_init_duration_secs(api)
                        self.log_notice("{}: DpInit duration {} secs".format(lport, dpInitDuration))
                        self.port_dict[lport]['cmis_expired'] = now + datetime.timedelta(seconds=dpInitDuration)
                        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_DP_TXON)
                    elif state == CMIS_STATE_DP_TXON:
                        if not self.check_datapath_state(api, host_lanes_mask, ['DataPathInitialized']):
                            if (expired is not None) and (expired <= now):
                                self.log_notice("{}: timeout for 'DataPathInitialized'".format(lport))
                                self.force_cmis_reinit(lport, retries + 1)
                            continue

                        # Turn ON the laser
                        media_lanes_mask = self.port_dict[lport]['media_lanes_mask']
                        api.tx_disable_channel(media_lanes_mask, False)
                        self.log_notice("{}: Turning ON tx power".format(lport))
                        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_DP_ACTIVATE)
                    elif state == CMIS_STATE_DP_ACTIVATE:
                        if not self.check_datapath_state(api, host_lanes_mask, ['DataPathActivated']):
                            if (expired is not None) and (expired <= now):
                                self.log_notice("{}: timeout for 'DataPathActivated'".format(lport))
                                self.force_cmis_reinit(lport, retries + 1)
                            continue

                        self.log_notice("{}: READY".format(lport))
                        self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_READY)
                        self.post_port_active_apsel_to_db(api, lport, host_lanes_mask)

                except Exception as e:
                    self.log_error("{}: internal errors due to {}".format(lport, e))
                    log_exception_traceback()
                    self.update_port_transceiver_status_table_sw_cmis_state(lport, CMIS_STATE_FAILED)

        self.log_notice("Stopped")

    def run(self):
        if platform_chassis is None:
            self.log_notice("Platform chassis is not available, stopping...")
            return

        if self.skip_cmis_mgr:
            self.log_notice("Skipping CMIS Task Manager")
            return

        try:
            self.task_worker()
        except Exception as e:
            helper_logger.log_error("Exception occured at {} thread due to {}".format(threading.current_thread().getName(), repr(e)))
            log_exception_traceback()
            self.exc = e
            self.main_thread_stop_event.set()

    def join(self):
        self.task_stopping_event.set()
        if not self.skip_cmis_mgr:
            threading.Thread.join(self)
            if self.exc:
                raise self.exc

# Thread wrapper class to update dom info periodically


class DomInfoUpdateTask(threading.Thread):
    def __init__(self, namespaces, port_mapping, main_thread_stop_event, skip_cmis_mgr):
        threading.Thread.__init__(self)
        self.name = "DomInfoUpdateTask"
        self.exc = None
        self.task_stopping_event = threading.Event()
        self.main_thread_stop_event = main_thread_stop_event
        self.port_mapping = copy.deepcopy(port_mapping)
        self.namespaces = namespaces
        self.skip_cmis_mgr = skip_cmis_mgr

    def get_dom_polling_from_config_db(self, lport):
        """
            Returns the value of dom_polling field from PORT table in CONFIG_DB
            For non-breakout ports, this function will get dom_polling field from PORT table of lport (subport = 0)
            For breakout ports, this function will get dom_polling field from PORT table of the first subport
            of lport's correpsonding breakout group (subport = 1)

            Returns:
                'disabled' if dom_polling is set to 'disabled', otherwise 'enabled'
        """
        dom_polling = 'enabled'

        pport_list = self.port_mapping.get_logical_to_physical(lport)
        if not pport_list:
            helper_logger.log_warning("Get dom disabled: Got unknown physical port list {} for lport {}".format(pport_list, lport))
            return dom_polling
        pport = pport_list[0]

        logical_port_list = self.port_mapping.get_physical_to_logical(pport)
        if logical_port_list is None:
            helper_logger.log_warning("Get dom disabled: Got unknown FP port index {}".format(pport))
            return dom_polling

        # Sort the logical port list to make sure we always get the first subport
        logical_port_list = natsorted(logical_port_list, key=lambda y: y.lower())
        first_logical_port = logical_port_list[0]

        asic_index = self.port_mapping.get_asic_id_for_logical_port(first_logical_port)
        port_tbl = self.xcvr_table_helper.get_cfg_port_tbl(asic_index)

        found, port_info = port_tbl.get(first_logical_port)
        if found and 'dom_polling' in dict(port_info):
            dom_polling = dict(port_info)['dom_polling']

        return dom_polling

    """
    Checks if the port is going through CMIS initialization process
    This API assumes CMIS_STATE_UNKNOWN as a transitional state since it is the
    first state after starting CMIS state machine.
    This assumption allows the DomInfoUpdateTask thread to skip polling on the port
    to allow CMIS initialization to complete if needed.
    Returns:
        True if the port is in CMIS initialization process,
        otherwise False
    """
    def is_port_in_cmis_initialization_process(self, logical_port_name):
        # If CMIS manager is not available for the platform, return False
        if self.skip_cmis_mgr:
            return False

        asic_index = self.port_mapping.get_asic_id_for_logical_port(logical_port_name)
        if asic_index is None:
            helper_logger.log_warning("Got invalid asic index for {} while checking cmis init status".format(logical_port_name))
            return False

        cmis_state = get_cmis_state_from_state_db(logical_port_name, self.xcvr_table_helper.get_status_tbl(asic_index))
        if cmis_state not in CMIS_TERMINAL_STATES:
            return True
        else:
            return False

    def is_port_dom_monitoring_disabled(self, logical_port_name):
        return self.get_dom_polling_from_config_db(logical_port_name) == 'disabled' or \
                self.is_port_in_cmis_initialization_process(logical_port_name)

    def task_worker(self):
        self.xcvr_table_helper = XcvrTableHelper(self.namespaces)
        helper_logger.log_info("Start DOM monitoring loop")
        firmware_info_cache = {}
        dom_info_cache = {}
        transceiver_status_cache = {}
        pm_info_cache = {}
        sel, asic_context = port_event_helper.subscribe_port_config_change(self.namespaces)

        # Start loop to update dom info in DB periodically
        while not self.task_stopping_event.wait(DOM_INFO_UPDATE_PERIOD_SECS):
            # Clear the cache at the begin of the loop to make sure it will be clear each time
            firmware_info_cache.clear()
            dom_info_cache.clear()
            transceiver_status_cache.clear()
            pm_info_cache.clear()

            # Handle port change event from main thread
            port_event_helper.handle_port_config_change(sel, asic_context, self.task_stopping_event, self.port_mapping, helper_logger, self.on_port_config_change)
            logical_port_list = self.port_mapping.logical_port_list
            for logical_port_name in logical_port_list:
                if self.is_port_dom_monitoring_disabled(logical_port_name):
                    continue

                # Get the asic to which this port belongs
                asic_index = self.port_mapping.get_asic_id_for_logical_port(logical_port_name)
                if asic_index is None:
                    helper_logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
                    continue

                if not sfp_status_helper.detect_port_in_error_status(logical_port_name, self.xcvr_table_helper.get_status_tbl(asic_index)):
                    try:
                        post_port_sfp_firmware_info_to_db(logical_port_name, self.port_mapping, self.xcvr_table_helper.get_firmware_info_tbl(asic_index), self.task_stopping_event, firmware_info_cache=firmware_info_cache)
                    except (KeyError, TypeError) as e:
                        #continue to process next port since execption could be raised due to port reset, transceiver removal
                        helper_logger.log_warning("Got exception {} while processing firmware info for port {}, ignored".format(repr(e), logical_port_name))
                        continue
                    try:
                        post_port_dom_info_to_db(logical_port_name, self.port_mapping, self.xcvr_table_helper.get_dom_tbl(asic_index), self.task_stopping_event, dom_info_cache=dom_info_cache)
                    except (KeyError, TypeError) as e:
                        #continue to process next port since execption could be raised due to port reset, transceiver removal
                        helper_logger.log_warning("Got exception {} while processing dom info for port {}, ignored".format(repr(e), logical_port_name))
                        continue
                    try:
                        update_port_transceiver_status_table_hw(logical_port_name,
                                                                self.port_mapping,
                                                                self.xcvr_table_helper.get_status_tbl(asic_index),
                                                                self.task_stopping_event,
                                                                transceiver_status_cache=transceiver_status_cache)
                    except (KeyError, TypeError) as e:
                        #continue to process next port since execption could be raised due to port reset, transceiver removal
                        helper_logger.log_warning("Got exception {} while processing transceiver status hw for port {}, ignored".format(repr(e), logical_port_name))
                        continue
                    try:
                        post_port_pm_info_to_db(logical_port_name, self.port_mapping, self.xcvr_table_helper.get_pm_tbl(asic_index), self.task_stopping_event, pm_info_cache=pm_info_cache)
                    except (KeyError, TypeError) as e:
                        #continue to process next port since execption could be raised due to port reset, transceiver removal
                        helper_logger.log_warning("Got exception {} while processing pm info for port {}, ignored".format(repr(e), logical_port_name))
                        continue

        helper_logger.log_info("Stop DOM monitoring loop")

    def run(self):
        if self.task_stopping_event.is_set():
            return
        try:
            self.task_worker()
        except Exception as e:
            helper_logger.log_error("Exception occured at {} thread due to {}".format(threading.current_thread().getName(), repr(e)))
            log_exception_traceback()
            self.exc = e
            self.main_thread_stop_event.set()

    def join(self):
        self.task_stopping_event.set()
        threading.Thread.join(self)
        if self.exc:
            raise self.exc

    def on_port_config_change(self, port_change_event):
        if port_change_event.event_type == port_event_helper.PortChangeEvent.PORT_REMOVE:
            self.on_remove_logical_port(port_change_event)
        self.port_mapping.handle_port_change_event(port_change_event)

    def on_remove_logical_port(self, port_change_event):
        """Called when a logical port is removed from CONFIG_DB

        Args:
            port_change_event (object): port change event
        """
        # To avoid race condition, remove the entry TRANSCEIVER_FIRMWARE_INFO, TRANSCEIVER_DOM_SENSOR, TRANSCEIVER_PM and HW section of TRANSCEIVER_STATUS table.
        # This thread only updates TRANSCEIVER_FIRMWARE_INFO, TRANSCEIVER_DOM_SENSOR, TRANSCEIVER_PM and HW section of TRANSCEIVER_STATUS table,
        # so we don't have to remove entries from TRANSCEIVER_INFO and TRANSCEIVER_DOM_THRESHOLD
        del_port_sfp_dom_info_from_db(port_change_event.port_name,
                                      self.port_mapping,
                                      None,
                                      self.xcvr_table_helper.get_dom_tbl(port_change_event.asic_id),
                                      None,
                                      self.xcvr_table_helper.get_pm_tbl(port_change_event.asic_id),
                                      self.xcvr_table_helper.get_firmware_info_tbl(port_change_event.asic_id))
        delete_port_from_status_table_hw(port_change_event.port_name,
                                      self.port_mapping,
                                      self.xcvr_table_helper.get_status_tbl(port_change_event.asic_id))


# Thread wrapper class to update sfp state info periodically


class SfpStateUpdateTask(threading.Thread):
    RETRY_EEPROM_READING_INTERVAL = 60
    def __init__(self, namespaces, port_mapping, main_thread_stop_event, sfp_error_event):
        threading.Thread.__init__(self)
        self.name = "SfpStateUpdateTask"
        self.exc = None
        self.task_stopping_event = threading.Event()
        self.main_thread_stop_event = main_thread_stop_event
        self.sfp_error_event = sfp_error_event
        self.port_mapping = copy.deepcopy(port_mapping)
        # A set to hold those logical port name who fail to read EEPROM
        self.retry_eeprom_set = set()
        # To avoid retry EEPROM read too fast, record the last EEPROM read timestamp in this member
        self.last_retry_eeprom_time = 0
        # A dict to hold SFP error event, for SFP insert/remove event, it is not necessary to cache them
        # because _wrapper_get_presence returns the SFP presence status
        self.sfp_error_dict = {}
        self.sfp_insert_events = {}
        self.namespaces = namespaces

    def _mapping_event_from_change_event(self, status, port_dict):
        """
        mapping from what get_transceiver_change_event returns to event defined in the state machine
        the logic is pretty straightforword
        """
        if status:
            if bool(port_dict):
                event = NORMAL_EVENT
            else:
                event = SYSTEM_BECOME_READY
                # here, a simple timeout event whose port_dict is empty is mapped
                # into a SYSTEM_BECOME_READY event so that it can be handled
                port_dict[EVENT_ON_ALL_SFP] = SYSTEM_BECOME_READY
        else:
            if EVENT_ON_ALL_SFP in port_dict.keys():
                event = port_dict[EVENT_ON_ALL_SFP]
            else:
                # this should not happen. just for protection
                event = SYSTEM_FAIL
                port_dict[EVENT_ON_ALL_SFP] = SYSTEM_FAIL

        helper_logger.log_debug("mapping from {} {} to {}".format(status, port_dict, event))
        return event

    # Update port sfp info and dom threshold in db during xcvrd bootup
    def _post_port_sfp_info_and_dom_thr_to_db_once(self, port_mapping, xcvr_table_helper, stop_event=threading.Event()):
        # Connect to STATE_DB and create transceiver dom/sfp info tables
        transceiver_dict = {}
        retry_eeprom_set = set()

        is_warm_start = is_warm_reboot_enabled()
        # Post all the current interface sfp/dom threshold info to STATE_DB
        logical_port_list = port_mapping.logical_port_list
        for logical_port_name in logical_port_list:
            if stop_event.is_set():
                break

            # Get the asic to which this port belongs
            asic_index = port_mapping.get_asic_id_for_logical_port(logical_port_name)
            if asic_index is None:
                helper_logger.log_warning("Got invalid asic index for {}, ignored while posting SFP info during boot-up".format(logical_port_name))
                continue
            rc = post_port_sfp_info_to_db(logical_port_name, port_mapping, xcvr_table_helper.get_intf_tbl(asic_index), transceiver_dict, stop_event)
            if rc != SFP_EEPROM_NOT_READY:
                post_port_dom_threshold_info_to_db(logical_port_name, port_mapping, xcvr_table_helper.get_dom_threshold_tbl(asic_index), stop_event)

                # Do not notify media settings during warm reboot to avoid dataplane traffic impact
                if is_warm_start == False:
                    media_settings_parser.notify_media_setting(logical_port_name, transceiver_dict, xcvr_table_helper.get_app_port_tbl(asic_index), xcvr_table_helper.get_cfg_port_tbl(asic_index), port_mapping)
                    transceiver_dict.clear()
            else:
                retry_eeprom_set.add(logical_port_name)

        return retry_eeprom_set

    # Init TRANSCEIVER_STATUS table
    def _init_port_sfp_status_tbl(self, port_mapping, xcvr_table_helper, stop_event=threading.Event()):
        # Init TRANSCEIVER_STATUS table
        logical_port_list = port_mapping.logical_port_list
        for logical_port_name in logical_port_list:
            if stop_event.is_set():
                break

            # Get the asic to which this port belongs
            asic_index = port_mapping.get_asic_id_for_logical_port(logical_port_name)
            if asic_index is None:
                helper_logger.log_warning("Got invalid asic index for {}, ignored during sfp status table init".format(logical_port_name))
                continue

            physical_port_list = port_mapping.logical_port_name_to_physical_port_list(logical_port_name)
            if physical_port_list is None:
                helper_logger.log_error("No physical ports found for logical port '{}' during sfp status table init".format(logical_port_name))
                update_port_transceiver_status_table_sw(logical_port_name, xcvr_table_helper.get_status_tbl(asic_index), sfp_status_helper.SFP_STATUS_REMOVED)

            for physical_port in physical_port_list:
                if stop_event.is_set():
                    break

                if not _wrapper_get_presence(physical_port):
                    update_port_transceiver_status_table_sw(logical_port_name, xcvr_table_helper.get_status_tbl(asic_index), sfp_status_helper.SFP_STATUS_REMOVED)
                else:
                    update_port_transceiver_status_table_sw(logical_port_name, xcvr_table_helper.get_status_tbl(asic_index), sfp_status_helper.SFP_STATUS_INSERTED)

    def init(self):
        port_mapping_data = port_event_helper.get_port_mapping(self.namespaces)

        # Post all the current interface sfp/dom threshold info to STATE_DB
        self.retry_eeprom_set = self._post_port_sfp_info_and_dom_thr_to_db_once(port_mapping_data, self.xcvr_table_helper, self.main_thread_stop_event)
        helper_logger.log_notice("SfpStateUpdateTask: Posted all port DOM/SFP info to DB")

        # Init port sfp status table
        self._init_port_sfp_status_tbl(port_mapping_data, self.xcvr_table_helper, self.main_thread_stop_event)
        helper_logger.log_notice("SfpStateUpdateTask: Initialized port sfp status table")

    def task_worker(self, stopping_event, sfp_error_event):
        self.xcvr_table_helper = XcvrTableHelper(self.namespaces)

        helper_logger.log_info("Start SFP monitoring loop")

        transceiver_dict = {}
        # Start main loop to listen to the SFP change event.
        # The state migrating sequence:
        # 1. When the system starts, it is in "INIT" state, calling get_transceiver_change_event
        #    with RETRY_PERIOD_FOR_SYSTEM_READY_MSECS as timeout for before reach RETRY_TIMES_FOR_SYSTEM_READY
        #    times, otherwise it will transition to "EXIT" state
        # 2. Once 'system_become_ready' returned, the system enters "SYSTEM_READY" state and starts to monitor
        #    the insertion/removal event of all the SFP modules.
        #    In this state, receiving any system level event will be treated as an error and cause transition to
        #    "INIT" state
        # 3. When system back to "INIT" state, it will continue to handle system fail event, and retry until reach
        #    RETRY_TIMES_FOR_SYSTEM_READY times, otherwise it will transition to "EXIT" state

        # states definition
        # - Initial state: INIT, before received system ready or a normal event
        # - Final state: EXIT
        # - other state: NORMAL, after has received system-ready or a normal event

        # events definition
        # - SYSTEM_NOT_READY
        # - SYSTEM_BECOME_READY
        #   -
        # - NORMAL_EVENT
        #   - sfp insertion/removal
        #   - timeout returned by sfputil.get_change_event with status = true
        # - SYSTEM_FAIL

        # State transition:
        # 1. SYSTEM_NOT_READY
        #     - INIT
        #       - retry < RETRY_TIMES_FOR_SYSTEM_READY
        #             retry ++
        #       - else
        #             max retry reached, treat as fatal, transition to EXIT
        #     - NORMAL
        #         Treat as an error, transition to INIT
        # 2. SYSTEM_BECOME_READY
        #     - INIT
        #         transition to NORMAL
        #     - NORMAL
        #         log the event
        #         nop
        # 3. NORMAL_EVENT
        #     - INIT (for the vendors who don't implement SYSTEM_BECOME_READY)
        #         transition to NORMAL
        #         handle the event normally
        #     - NORMAL
        #         handle the event normally
        # 4. SYSTEM_FAIL
        #     - INIT
        #       - retry < RETRY_TIMES_FOR_SYSTEM_READY
        #             retry ++
        #       - else
        #             max retry reached, treat as fatal, transition to EXIT
        #     - NORMAL
        #         Treat as an error, transition to INIT

        # State           event               next state
        # INIT            SYSTEM NOT READY    INIT / EXIT
        # INIT            SYSTEM FAIL         INIT / EXIT
        # INIT            SYSTEM BECOME READY NORMAL
        # NORMAL          SYSTEM BECOME READY NORMAL
        # NORMAL          SYSTEM FAIL         INIT
        # INIT/NORMAL     NORMAL EVENT        NORMAL
        # NORMAL          SYSTEM NOT READY    INIT
        # EXIT            -

        retry = 0
        timeout = RETRY_PERIOD_FOR_SYSTEM_READY_MSECS
        state = STATE_INIT
        self.init()

        sel, asic_context = port_event_helper.subscribe_port_config_change(self.namespaces)
        while not stopping_event.is_set():
            port_event_helper.handle_port_config_change(sel, asic_context, stopping_event, self.port_mapping, helper_logger, self.on_port_config_change)

            # Retry those logical ports whose EEPROM reading failed or timeout when the SFP is inserted
            self.retry_eeprom_reading()
            next_state = state
            time_start = time.time()
            # Ensure not to block for any event if sfp insert event is pending
            if self.sfp_insert_events:
                timeout = SFP_INSERT_EVENT_POLL_PERIOD_MSECS
            status, port_dict, error_dict = _wrapper_get_transceiver_change_event(timeout)
            if status:
                # Soak SFP insert events across various ports (updates port_dict)
                _wrapper_soak_sfp_insert_event(self.sfp_insert_events, port_dict)
            if not port_dict:
                continue
            helper_logger.log_debug("Got event {} {} in state {}".format(status, port_dict, state))
            event = self._mapping_event_from_change_event(status, port_dict)
            if event == SYSTEM_NOT_READY:
                if state == STATE_INIT:
                    # system not ready, wait and retry
                    if retry >= RETRY_TIMES_FOR_SYSTEM_READY:
                        helper_logger.log_error("System failed to get ready in {} secs or received system error. Exiting...".format(
                            (RETRY_PERIOD_FOR_SYSTEM_READY_MSECS/1000)*RETRY_TIMES_FOR_SYSTEM_READY))
                        next_state = STATE_EXIT
                        sfp_error_event.set()
                    else:
                        retry = retry + 1

                        # get_transceiver_change_event may return immediately,
                        # we want the retry expired in expected time period,
                        # So need to calc the time diff,
                        # if time diff less that the pre-defined waiting time,
                        # use sleep() to complete the time.
                        time_now = time.time()
                        time_diff = time_now - time_start
                        if time_diff < RETRY_PERIOD_FOR_SYSTEM_READY_MSECS/1000:
                            time.sleep(RETRY_PERIOD_FOR_SYSTEM_READY_MSECS/1000 - time_diff)
                elif state == STATE_NORMAL:
                    helper_logger.log_error("Got system_not_ready in normal state, treat as fatal. Exiting...")
                    next_state = STATE_EXIT
                else:
                    next_state = STATE_EXIT
            elif event == SYSTEM_BECOME_READY:
                if state == STATE_INIT:
                    next_state = STATE_NORMAL
                    helper_logger.log_info("Got system_become_ready in init state, transition to normal state")
                elif state == STATE_NORMAL:
                    helper_logger.log_info("Got system_become_ready in normal state, ignored")
                else:
                    next_state = STATE_EXIT
            elif event == NORMAL_EVENT:
                if state == STATE_NORMAL or state == STATE_INIT:
                    if state == STATE_INIT:
                        next_state = STATE_NORMAL
                    # this is the originally logic that handled the transceiver change event
                    # this can be reached in two cases:
                    #   1. the state has been normal before got the event
                    #   2. the state was init and transition to normal after got the event.
                    #      this is for the vendors who don't implement "system_not_ready/system_becom_ready" logic
                    logical_port_dict = {}
                    for key, value in port_dict.items():
                        # SFP error event should be cached because: when a logical port is created, there is no way to
                        # detect the SFP error by platform API.
                        if value != sfp_status_helper.SFP_STATUS_INSERTED and value != sfp_status_helper.SFP_STATUS_REMOVED:
                            self.sfp_error_dict[key] = (value, error_dict)
                        else:
                            self.sfp_error_dict.pop(key, None)
                        logical_port_list = self.port_mapping.get_physical_to_logical(int(key))
                        if logical_port_list is None:
                            helper_logger.log_warning("Got unknown FP port index {}, ignored".format(key))
                            continue
                        for logical_port in logical_port_list:
                            logical_port_dict[logical_port] = value
                            # Get the asic to which this port belongs
                            asic_index = self.port_mapping.get_asic_id_for_logical_port(logical_port)
                            if asic_index is None:
                                helper_logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port))
                                continue

                            if value == sfp_status_helper.SFP_STATUS_INSERTED:
                                helper_logger.log_notice("{}: Got SFP inserted event".format(logical_port))
                                # A plugin event will clear the error state.
                                update_port_transceiver_status_table_sw(
                                    logical_port, self.xcvr_table_helper.get_status_tbl(asic_index), sfp_status_helper.SFP_STATUS_INSERTED)
                                helper_logger.log_notice("{}: received plug in and update port sfp status table.".format(logical_port))
                                rc = post_port_sfp_info_to_db(logical_port, self.port_mapping, self.xcvr_table_helper.get_intf_tbl(asic_index), transceiver_dict)
                                # If we didn't get the sfp info, assuming the eeprom is not ready, give a try again.
                                if rc == SFP_EEPROM_NOT_READY:
                                    helper_logger.log_warning("{}: SFP EEPROM is not ready. One more try...".format(logical_port))
                                    time.sleep(TIME_FOR_SFP_READY_SECS)
                                    rc = post_port_sfp_info_to_db(logical_port, self.port_mapping, self.xcvr_table_helper.get_intf_tbl(asic_index), transceiver_dict)
                                    if rc == SFP_EEPROM_NOT_READY:
                                        # If still failed to read EEPROM, put it to retry set
                                        self.retry_eeprom_set.add(logical_port)

                                if rc != SFP_EEPROM_NOT_READY:
                                    post_port_dom_threshold_info_to_db(logical_port, self.port_mapping, self.xcvr_table_helper.get_dom_threshold_tbl(asic_index))
                                    media_settings_parser.notify_media_setting(logical_port, transceiver_dict, self.xcvr_table_helper.get_app_port_tbl(asic_index), self.xcvr_table_helper.get_cfg_port_tbl(asic_index), self.port_mapping)
                                    transceiver_dict.clear()
                            elif value == sfp_status_helper.SFP_STATUS_REMOVED:
                                helper_logger.log_notice("{}: Got SFP removed event".format(logical_port))
                                update_port_transceiver_status_table_sw(
                                    logical_port, self.xcvr_table_helper.get_status_tbl(asic_index), sfp_status_helper.SFP_STATUS_REMOVED)
                                helper_logger.log_notice("{}: received plug out and update port sfp status table.".format(logical_port))
                                del_port_sfp_dom_info_from_db(logical_port, self.port_mapping,
                                                              self.xcvr_table_helper.get_intf_tbl(asic_index),
                                                              self.xcvr_table_helper.get_dom_tbl(asic_index),
                                                              self.xcvr_table_helper.get_dom_threshold_tbl(asic_index),
                                                              self.xcvr_table_helper.get_pm_tbl(asic_index),
                                                              self.xcvr_table_helper.get_firmware_info_tbl(asic_index))
                                delete_port_from_status_table_hw(logical_port, self.port_mapping, self.xcvr_table_helper.get_status_tbl(asic_index))
                            else:
                                try:
                                    error_bits = int(value)
                                    helper_logger.log_error("{}: Got SFP error event {}".format(logical_port, value))

                                    error_descriptions = sfp_status_helper.fetch_generic_error_description(error_bits)

                                    if sfp_status_helper.has_vendor_specific_error(error_bits):
                                        if error_dict:
                                            vendor_specific_error_description = error_dict.get(key)
                                        else:
                                            vendor_specific_error_description = _wrapper_get_sfp_error_description(key)
                                        error_descriptions.append(vendor_specific_error_description)

                                    # Add error info to database
                                    # Any existing error will be replaced by the new one.
                                    update_port_transceiver_status_table_sw(logical_port, self.xcvr_table_helper.get_status_tbl(asic_index), value, '|'.join(error_descriptions))
                                    helper_logger.log_notice("{}: Receive error update port sfp status table.".format(logical_port))
                                    # In this case EEPROM is not accessible. The DOM info will be removed since it can be out-of-date.
                                    # The interface info remains in the DB since it is static.
                                    if sfp_status_helper.is_error_block_eeprom_reading(error_bits):
                                        del_port_sfp_dom_info_from_db(logical_port,
                                                                      self.port_mapping,
                                                                      None,
                                                                      self.xcvr_table_helper.get_dom_tbl(asic_index),
                                                                      self.xcvr_table_helper.get_dom_threshold_tbl(asic_index),
                                                                      self.xcvr_table_helper.get_pm_tbl(asic_index),
                                                                      self.xcvr_table_helper.get_firmware_info_tbl(asic_index))
                                        delete_port_from_status_table_hw(logical_port, self.port_mapping, self.xcvr_table_helper.get_status_tbl(asic_index))
                                except (TypeError, ValueError) as e:
                                    helper_logger.log_error("{}: Got unrecognized event {}, ignored".format(logical_port, value))

                else:
                    next_state = STATE_EXIT
            elif event == SYSTEM_FAIL:
                if state == STATE_INIT:
                    # To overcome a case that system is only temporarily not available,
                    # when get system fail event will wait and retry for a certain period,
                    # if system recovered in this period xcvrd will transit to INIT state
                    # and continue run, if can not recover then exit.
                    if retry >= RETRY_TIMES_FOR_SYSTEM_FAIL:
                        helper_logger.log_error("System failed to recover in {} secs. Exiting...".format(
                            (RETRY_PERIOD_FOR_SYSTEM_FAIL_MSECS/1000)*RETRY_TIMES_FOR_SYSTEM_FAIL))
                        next_state = STATE_EXIT
                        sfp_error_event.set()
                    else:
                        retry = retry + 1
                        waiting_time_compensation_with_sleep(time_start, RETRY_PERIOD_FOR_SYSTEM_FAIL_MSECS/1000)
                elif state == STATE_NORMAL:
                    helper_logger.log_error("Got system_fail in normal state, treat as error, transition to INIT...")
                    next_state = STATE_INIT
                    timeout = RETRY_PERIOD_FOR_SYSTEM_FAIL_MSECS
                    retry = 0
                else:
                    next_state = STATE_EXIT
            else:
                helper_logger.log_warning("Got unknown event {} on state {}.".format(event, state))

            if next_state != state:
                helper_logger.log_debug("State transition from {} to {}".format(state, next_state))
                state = next_state

            if next_state == STATE_EXIT:
                os.kill(os.getppid(), signal.SIGTERM)
                break
            elif next_state == STATE_NORMAL:
                timeout = STATE_MACHINE_UPDATE_PERIOD_MSECS

        helper_logger.log_info("Stop SFP monitoring loop")

    def run(self):
        self.thread_id = threading.current_thread().ident
        if self.task_stopping_event.is_set():
            return
        try:
            self.task_worker(self.task_stopping_event, self.sfp_error_event)
        except Exception as e:
            helper_logger.log_error("Exception occured at {} thread due to {}".format(threading.current_thread().getName(), repr(e)))
            log_exception_traceback()
            self.exc = e
            self.main_thread_stop_event.set()

    # SfpStateUpdateTask thread has a call to an API which could potentially sleep in the order of seconds and hence,
    # could block the xcvrd daemon graceful shutdown process for a prolonged time. Raising an exception will allow us to
    # interrupt the SfpStateUpdateTask thread while sleeping and will allow graceful shutdown of the thread
    def raise_exception(self):
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(self.thread_id),
              ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(self.thread_id), 0)
            helper_logger.log_error('Exception raise failure for SfpStateUpdateTask')

    def join(self):
        self.task_stopping_event.set()
        threading.Thread.join(self)
        if self.exc:
            raise self.exc

    def on_port_config_change(self , port_change_event):
        if port_change_event.event_type == port_event_helper.PortChangeEvent.PORT_REMOVE:
            self.on_remove_logical_port(port_change_event)
            self.port_mapping.handle_port_change_event(port_change_event)
        elif port_change_event.event_type == port_event_helper.PortChangeEvent.PORT_ADD:
            self.port_mapping.handle_port_change_event(port_change_event)
            self.on_add_logical_port(port_change_event)

    def on_remove_logical_port(self, port_change_event):
        """Called when a logical port is removed from CONFIG_DB.

        Args:
            port_change_event (object): port change event
        """
        # To avoid race condition, remove the entry TRANSCEIVER_DOM_INFO, TRANSCEIVER_STATUS_INFO and TRANSCEIVER_INFO table.
        # The operation to remove entry from TRANSCEIVER_DOM_INFO is duplicate with DomInfoUpdateTask.on_remove_logical_port,
        # but it is necessary because TRANSCEIVER_DOM_INFO is also updated in this thread when a new SFP is inserted.
        del_port_sfp_dom_info_from_db(port_change_event.port_name,
                                      self.port_mapping,
                                      self.xcvr_table_helper.get_intf_tbl(port_change_event.asic_id),
                                      self.xcvr_table_helper.get_dom_tbl(port_change_event.asic_id),
                                      self.xcvr_table_helper.get_dom_threshold_tbl(port_change_event.asic_id),
                                      self.xcvr_table_helper.get_pm_tbl(port_change_event.asic_id),
                                      self.xcvr_table_helper.get_firmware_info_tbl(port_change_event.asic_id))
        delete_port_from_status_table_sw(port_change_event.port_name, self.xcvr_table_helper.get_status_tbl(port_change_event.asic_id))
        delete_port_from_status_table_hw(port_change_event.port_name,
                                         self.port_mapping,
                                         self.xcvr_table_helper.get_status_tbl(port_change_event.asic_id))

        # The logical port has been removed, no need retry EEPROM reading
        if port_change_event.port_name in self.retry_eeprom_set:
            self.retry_eeprom_set.remove(port_change_event.port_name)

    def on_add_logical_port(self, port_change_event):
        """Called when a logical port is added

        Args:
            port_change_event (object): port change event

        Returns:
            dict: key is logical port name, value is SFP status
        """
        # A logical port is created. There could be 3 cases:
        #  1. SFP is present with no SFP error. Need query the SFP status by platform API and
        #     insert the data to DB.
        #  2. SFP is present with SFP error. If the SFP error does not block EEPROM reading,
        #     just query transceiver information and DOM sensor information via platform API and update the data to DB; otherwise,
        #     just update TRANSCEIVER_STATUS table with the error.
        #  3. SFP is not present. Only update TRANSCEIVER_STATUS_INFO table.
        status_tbl = self.xcvr_table_helper.get_status_tbl(port_change_event.asic_id)
        int_tbl = self.xcvr_table_helper.get_intf_tbl(port_change_event.asic_id)
        dom_threshold_tbl = self.xcvr_table_helper.get_dom_threshold_tbl(port_change_event.asic_id)

        error_description = 'N/A'
        status = None
        read_eeprom = True
        if port_change_event.port_index in self.sfp_error_dict:
            value, error_dict = self.sfp_error_dict[port_change_event.port_index]
            status = value
            error_bits = int(value)
            helper_logger.log_info("Got SFP error event {}".format(value))

            error_descriptions = sfp_status_helper.fetch_generic_error_description(error_bits)

            if sfp_status_helper.has_vendor_specific_error(error_bits):
                if error_dict:
                    vendor_specific_error_description = error_dict.get(port_change_event.port_index)
                else:
                    vendor_specific_error_description = _wrapper_get_sfp_error_description(port_change_event.port_index)
                error_descriptions.append(vendor_specific_error_description)

            error_description = '|'.join(error_descriptions)
            helper_logger.log_info("Receive error update port sfp status table.")
            if sfp_status_helper.is_error_block_eeprom_reading(error_bits):
                read_eeprom = False

        # SFP information not in DB
        if _wrapper_get_presence(port_change_event.port_index) and read_eeprom:
            transceiver_dict = {}
            status = sfp_status_helper.SFP_STATUS_INSERTED if not status else status
            rc = post_port_sfp_info_to_db(port_change_event.port_name, self.port_mapping, int_tbl, transceiver_dict)
            if rc == SFP_EEPROM_NOT_READY:
                # Failed to read EEPROM, put it to retry set
                self.retry_eeprom_set.add(port_change_event.port_name)
            else:
                post_port_dom_threshold_info_to_db(port_change_event.port_name, self.port_mapping, dom_threshold_tbl)
                media_settings_parser.notify_media_setting(port_change_event.port_name, transceiver_dict, self.xcvr_table_helper.get_app_port_tbl(port_change_event.asic_id), self.xcvr_table_helper.get_cfg_port_tbl(port_change_event.asic_id), self.port_mapping)
        else:
            status = sfp_status_helper.SFP_STATUS_REMOVED if not status else status
        update_port_transceiver_status_table_sw(port_change_event.port_name, status_tbl, status, error_description)

    def retry_eeprom_reading(self):
        """Retry EEPROM reading, if retry succeed, remove the logical port from the retry set
        """
        if not self.retry_eeprom_set:
            return

        # Retry eeprom with an interval RETRY_EEPROM_READING_INTERVAL. No need to put sleep here
        # because _wrapper_get_transceiver_change_event has a timeout argument.
        now = time.time()
        if now - self.last_retry_eeprom_time < self.RETRY_EEPROM_READING_INTERVAL:
            return

        self.last_retry_eeprom_time = now

        transceiver_dict = {}
        retry_success_set = set()
        for logical_port in self.retry_eeprom_set:
            asic_index = self.port_mapping.get_asic_id_for_logical_port(logical_port)
            rc = post_port_sfp_info_to_db(logical_port, self.port_mapping, self.xcvr_table_helper.get_intf_tbl(asic_index), transceiver_dict)
            if rc != SFP_EEPROM_NOT_READY:
                post_port_dom_threshold_info_to_db(logical_port, self.port_mapping, self.xcvr_table_helper.get_dom_threshold_tbl(asic_index))
                media_settings_parser.notify_media_setting(logical_port, transceiver_dict, self.xcvr_table_helper.get_app_port_tbl(asic_index), self.xcvr_table_helper.get_cfg_port_tbl(asic_index), self.port_mapping)
                transceiver_dict.clear()
                retry_success_set.add(logical_port)
        # Update retry EEPROM set
        self.retry_eeprom_set -= retry_success_set


#
# Daemon =======================================================================
#


class DaemonXcvrd(daemon_base.DaemonBase):
    def __init__(self, log_identifier, skip_cmis_mgr=False, enable_sff_mgr=False):
        super(DaemonXcvrd, self).__init__(log_identifier)
        self.stop_event = threading.Event()
        self.sfp_error_event = threading.Event()
        self.skip_cmis_mgr = skip_cmis_mgr
        self.enable_sff_mgr = enable_sff_mgr
        self.namespaces = ['']
        self.threads = []

    # Signal handler
    def signal_handler(self, sig, frame):
        if sig == signal.SIGHUP:
            self.log_info("Caught SIGHUP - ignoring...")
        elif sig == signal.SIGINT:
            self.log_info("Caught SIGINT - exiting...")
            self.stop_event.set()
        elif sig == signal.SIGTERM:
            self.log_info("Caught SIGTERM - exiting...")
            self.stop_event.set()
        else:
            self.log_warning("Caught unhandled signal '" + sig + "'")

    # Wait for port config is done
    def wait_for_port_config_done(self, namespace):
        # Connect to APPL_DB and subscribe to PORT table notifications
        appl_db = daemon_base.db_connect("APPL_DB", namespace=namespace)

        sel = swsscommon.Select()
        port_tbl = swsscommon.SubscriberStateTable(appl_db, swsscommon.APP_PORT_TABLE_NAME)
        sel.addSelectable(port_tbl)

        # Make sure this daemon started after all port configured
        while not self.stop_event.is_set():
            (state, c) = sel.select(port_event_helper.SELECT_TIMEOUT_MSECS)
            if state == swsscommon.Select.TIMEOUT:
                continue
            if state != swsscommon.Select.OBJECT:
                self.log_warning("sel.select() did not return swsscommon.Select.OBJECT")
                continue

            (key, op, fvp) = port_tbl.pop()
            if key in ["PortConfigDone", "PortInitDone"]:
                break


    # Initialize daemon
    def init(self):
        global platform_sfputil
        global platform_chassis

        self.log_notice("XCVRD INIT: Start daemon init...")

        # Load new platform api class
        try:
            import sonic_platform.platform
            import sonic_platform_base.sonic_sfp.sfputilhelper
            platform_chassis = sonic_platform.platform.Platform().get_chassis()
            self.log_info("chassis loaded {}".format(platform_chassis))
            # we have to make use of sfputil for some features
            # even though when new platform api is used for all vendors.
            # in this sense, we treat it as a part of new platform api.
            # we have already moved sfputil to sonic_platform_base
            # which is the root of new platform api.
            platform_sfputil = sonic_platform_base.sonic_sfp.sfputilhelper.SfpUtilHelper()
        except Exception as e:
            self.log_warning("Failed to load chassis due to {}".format(repr(e)))

        # Load platform specific sfputil class
        if platform_chassis is None or platform_sfputil is None:
            try:
                platform_sfputil = self.load_platform_util(PLATFORM_SPECIFIC_MODULE_NAME, PLATFORM_SPECIFIC_CLASS_NAME)
            except Exception as e:
                self.log_error("Failed to load sfputil: {}".format(str(e)), True)
                sys.exit(SFPUTIL_LOAD_ERROR)

        if multi_asic.is_multi_asic():
            # Load the namespace details first from the database_global.json file.
            swsscommon.SonicDBConfig.initializeGlobalConfig()
        # To prevent race condition in get_all_namespaces() we cache the namespaces before
        # creating any worker threads
        self.namespaces = multi_asic.get_front_end_namespaces()

        # Initialize xcvr table helper
        self.xcvr_table_helper = XcvrTableHelper(self.namespaces)

        if is_fast_reboot_enabled():
            self.log_info("Skip loading media_settings.json and optics_si_settings.json in case of fast-reboot")
        else:
            media_settings_parser.load_media_settings()
            optics_si_parser.load_optics_si_settings()

        # Make sure this daemon started after all port configured
        self.log_notice("XCVRD INIT: Wait for port config is done")
        for namespace in self.namespaces:
            self.wait_for_port_config_done(namespace)

        self.log_notice("XCVRD INIT: After port config is done")
        return port_event_helper.get_port_mapping(self.namespaces)

    # Deinitialize daemon
    def deinit(self):
        self.log_info("Start daemon deinit...")

        is_warm_fast_reboot = is_warm_reboot_enabled() or is_fast_reboot_enabled()

        # Delete all the information from DB and then exit
        port_mapping_data = port_event_helper.get_port_mapping(self.namespaces)
        logical_port_list = port_mapping_data.logical_port_list
        for logical_port_name in logical_port_list:
            # Get the asic to which this port belongs
            asic_index = port_mapping_data.get_asic_id_for_logical_port(logical_port_name)
            if asic_index is None:
                helper_logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
                continue

            intf_tbl = self.xcvr_table_helper.get_intf_tbl(asic_index) if not is_warm_fast_reboot else None

            del_port_sfp_dom_info_from_db(logical_port_name, port_mapping_data,
                                          intf_tbl,
                                          self.xcvr_table_helper.get_dom_tbl(asic_index),
                                          self.xcvr_table_helper.get_dom_threshold_tbl(asic_index),
                                          self.xcvr_table_helper.get_pm_tbl(asic_index),
                                          self.xcvr_table_helper.get_firmware_info_tbl(asic_index))

            if not is_warm_fast_reboot:
                delete_port_from_status_table_sw(logical_port_name, self.xcvr_table_helper.get_status_tbl(asic_index))
                delete_port_from_status_table_hw(logical_port_name, port_mapping_data, self.xcvr_table_helper.get_status_tbl(asic_index))

        del globals()['platform_chassis']

    # Run daemon

    def run(self):
        self.log_notice("Starting up...")

        # Start daemon initialization sequence
        port_mapping_data = self.init()

        # Start the SFF manager
        sff_manager = None
        if self.enable_sff_mgr:
            sff_manager = SffManagerTask(self.namespaces, self.stop_event, platform_chassis, helper_logger)
            sff_manager.start()
            self.threads.append(sff_manager)
        else:
            self.log_notice("Skipping SFF Task Manager")

        # Start the CMIS manager
        cmis_manager = None
        if not self.skip_cmis_mgr:
            cmis_manager = CmisManagerTask(self.namespaces, port_mapping_data, self.stop_event, self.skip_cmis_mgr)
            cmis_manager.start()
            self.threads.append(cmis_manager)

        # Start the dom sensor info update thread
        dom_info_update = DomInfoUpdateTask(self.namespaces, port_mapping_data, self.stop_event, self.skip_cmis_mgr)
        dom_info_update.start()
        self.threads.append(dom_info_update)

        # Start the sfp state info update thread
        sfp_state_update = SfpStateUpdateTask(self.namespaces, port_mapping_data, self.stop_event, self.sfp_error_event)
        sfp_state_update.start()
        self.threads.append(sfp_state_update)

        # Start main loop
        self.log_notice("Start daemon main loop with thread count {}".format(len(self.threads)))
        for thread in self.threads:
            self.log_notice("Started thread {}".format(thread.getName()))

        self.stop_event.wait()

        self.log_info("Stop daemon main loop")

        generate_sigkill = False
        # check all threads are alive
        for thread in self.threads:
            if thread.is_alive() is False:
                try:
                    thread.join()
                except Exception as e:
                    self.log_error("Xcvrd: exception found at child thread {} due to {}".format(thread.getName(), repr(e)))
                    generate_sigkill = True

        if generate_sigkill is True:
            self.log_error("Exiting main loop as child thread raised exception!")
            os.kill(os.getpid(), signal.SIGKILL)

        # Stop the SFF manager
        if sff_manager is not None:
            if sff_manager.is_alive():
                sff_manager.join()

        # Stop the CMIS manager
        if cmis_manager is not None:
            if cmis_manager.is_alive():
                cmis_manager.join()

        # Stop the dom sensor info update thread
        if dom_info_update.is_alive():
            dom_info_update.join()

        # Stop the sfp state info update thread
        if sfp_state_update.is_alive():
            sfp_state_update.raise_exception()
            sfp_state_update.join()

        # Start daemon deinitialization sequence
        self.deinit()

        self.log_info("Shutting down...")

        if self.sfp_error_event.is_set():
            sys.exit(SFP_SYSTEM_ERROR)


#
# Main =========================================================================
#

# This is our main entry point for xcvrd script


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip_cmis_mgr', action='store_true')
    parser.add_argument('--enable_sff_mgr', action='store_true')

    args = parser.parse_args()
    xcvrd = DaemonXcvrd(SYSLOG_IDENTIFIER, args.skip_cmis_mgr, args.enable_sff_mgr)
    xcvrd.run()


if __name__ == '__main__':
    main()
