#!/usr/bin/env python2

"""
    xcvrd
    Transceiver information update daemon for SONiC
"""

try:
    import ast
    import json
    import multiprocessing
    import os
    import signal
    import sys
    import threading
    import time

    from sonic_py_common import daemon_base, device_info, logger
    from sonic_py_common import multi_asic
    from swsscommon import swsscommon

    from .xcvrd_utilities import sfp_status_helper
    from .xcvrd_utilities import y_cable_helper
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")

#
# Constants ====================================================================
#

SYSLOG_IDENTIFIER = "xcvrd"

PLATFORM_SPECIFIC_MODULE_NAME = "sfputil"
PLATFORM_SPECIFIC_CLASS_NAME = "SfpUtil"

TRANSCEIVER_INFO_TABLE = 'TRANSCEIVER_INFO'
TRANSCEIVER_DOM_SENSOR_TABLE = 'TRANSCEIVER_DOM_SENSOR'
TRANSCEIVER_STATUS_TABLE = 'TRANSCEIVER_STATUS'

SELECT_TIMEOUT_MSECS = 1000

# Mgminit time required as per CMIS spec
MGMT_INIT_TIME_DELAY_SECS = 2

# SFP insert event poll duration
SFP_INSERT_EVENT_POLL_PERIOD_MSECS = 1000

DOM_INFO_UPDATE_PERIOD_SECS = 60
TIME_FOR_SFP_READY_SECS = 1
XCVRD_MAIN_THREAD_SLEEP_SECS = 60

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

media_settings = ''
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

# Find out the underneath physical port list by logical name


def logical_port_name_to_physical_port_list(port_name):
    try:
        return [int(port_name)]
    except ValueError:
        if platform_sfputil.is_logical_port(port_name):
            return platform_sfputil.get_logical_to_physical(port_name)
        else:
            helper_logger.log_error("Invalid port '{}'".format(port_name))
            return None

# Get physical port name


def get_physical_port_name(logical_port, physical_port, ganged):
    if logical_port == physical_port:
        return logical_port
    elif ganged:
        return logical_port + ":{} (ganged)".format(physical_port)
    else:
        return logical_port

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
            return platform_chassis.get_sfp(physical_port).sfp_type
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
    dom_info_dict['temperature'] = strip_unit_and_beautify(dom_info_dict['temperature'], TEMP_UNIT)
    dom_info_dict['voltage'] = strip_unit_and_beautify(dom_info_dict['voltage'], VOLT_UNIT)
    dom_info_dict['rx1power'] = strip_unit_and_beautify(dom_info_dict['rx1power'], POWER_UNIT)
    dom_info_dict['rx2power'] = strip_unit_and_beautify(dom_info_dict['rx2power'], POWER_UNIT)
    dom_info_dict['rx3power'] = strip_unit_and_beautify(dom_info_dict['rx3power'], POWER_UNIT)
    dom_info_dict['rx4power'] = strip_unit_and_beautify(dom_info_dict['rx4power'], POWER_UNIT)
    dom_info_dict['tx1bias'] = strip_unit_and_beautify(dom_info_dict['tx1bias'], BIAS_UNIT)
    dom_info_dict['tx2bias'] = strip_unit_and_beautify(dom_info_dict['tx2bias'], BIAS_UNIT)
    dom_info_dict['tx3bias'] = strip_unit_and_beautify(dom_info_dict['tx3bias'], BIAS_UNIT)
    dom_info_dict['tx4bias'] = strip_unit_and_beautify(dom_info_dict['tx4bias'], BIAS_UNIT)
    dom_info_dict['tx1power'] = strip_unit_and_beautify(dom_info_dict['tx1power'], POWER_UNIT)
    dom_info_dict['tx2power'] = strip_unit_and_beautify(dom_info_dict['tx2power'], POWER_UNIT)
    dom_info_dict['tx3power'] = strip_unit_and_beautify(dom_info_dict['tx3power'], POWER_UNIT)
    dom_info_dict['tx4power'] = strip_unit_and_beautify(dom_info_dict['tx4power'], POWER_UNIT)
    if _wrapper_get_sfp_type(physical_port) == 'QSFP_DD':
        dom_info_dict['rx5power'] = strip_unit_and_beautify(dom_info_dict['rx5power'], POWER_UNIT)
        dom_info_dict['rx6power'] = strip_unit_and_beautify(dom_info_dict['rx6power'], POWER_UNIT)
        dom_info_dict['rx7power'] = strip_unit_and_beautify(dom_info_dict['rx7power'], POWER_UNIT)
        dom_info_dict['rx8power'] = strip_unit_and_beautify(dom_info_dict['rx8power'], POWER_UNIT)
        dom_info_dict['tx5bias'] = strip_unit_and_beautify(dom_info_dict['tx5bias'], BIAS_UNIT)
        dom_info_dict['tx6bias'] = strip_unit_and_beautify(dom_info_dict['tx6bias'], BIAS_UNIT)
        dom_info_dict['tx7bias'] = strip_unit_and_beautify(dom_info_dict['tx7bias'], BIAS_UNIT)
        dom_info_dict['tx8bias'] = strip_unit_and_beautify(dom_info_dict['tx8bias'], BIAS_UNIT)
        dom_info_dict['tx5power'] = strip_unit_and_beautify(dom_info_dict['tx5power'], POWER_UNIT)
        dom_info_dict['tx6power'] = strip_unit_and_beautify(dom_info_dict['tx6power'], POWER_UNIT)
        dom_info_dict['tx7power'] = strip_unit_and_beautify(dom_info_dict['tx7power'], POWER_UNIT)
        dom_info_dict['tx8power'] = strip_unit_and_beautify(dom_info_dict['tx8power'], POWER_UNIT)


def beautify_dom_threshold_info_dict(dom_info_dict):
    dom_info_dict['temphighalarm'] = strip_unit_and_beautify(dom_info_dict['temphighalarm'], TEMP_UNIT)
    dom_info_dict['temphighwarning'] = strip_unit_and_beautify(dom_info_dict['temphighwarning'], TEMP_UNIT)
    dom_info_dict['templowalarm'] = strip_unit_and_beautify(dom_info_dict['templowalarm'], TEMP_UNIT)
    dom_info_dict['templowwarning'] = strip_unit_and_beautify(dom_info_dict['templowwarning'], TEMP_UNIT)

    dom_info_dict['vcchighalarm'] = strip_unit_and_beautify(dom_info_dict['vcchighalarm'], VOLT_UNIT)
    dom_info_dict['vcchighwarning'] = strip_unit_and_beautify(dom_info_dict['vcchighwarning'], VOLT_UNIT)
    dom_info_dict['vcclowalarm'] = strip_unit_and_beautify(dom_info_dict['vcclowalarm'], VOLT_UNIT)
    dom_info_dict['vcclowwarning'] = strip_unit_and_beautify(dom_info_dict['vcclowwarning'], VOLT_UNIT)

    dom_info_dict['txpowerhighalarm'] = strip_unit_and_beautify(dom_info_dict['txpowerhighalarm'], POWER_UNIT)
    dom_info_dict['txpowerlowalarm'] = strip_unit_and_beautify(dom_info_dict['txpowerlowalarm'], POWER_UNIT)
    dom_info_dict['txpowerhighwarning'] = strip_unit_and_beautify(dom_info_dict['txpowerhighwarning'], POWER_UNIT)
    dom_info_dict['txpowerlowwarning'] = strip_unit_and_beautify(dom_info_dict['txpowerlowwarning'], POWER_UNIT)

    dom_info_dict['rxpowerhighalarm'] = strip_unit_and_beautify(dom_info_dict['rxpowerhighalarm'], POWER_UNIT)
    dom_info_dict['rxpowerlowalarm'] = strip_unit_and_beautify(dom_info_dict['rxpowerlowalarm'], POWER_UNIT)
    dom_info_dict['rxpowerhighwarning'] = strip_unit_and_beautify(dom_info_dict['rxpowerhighwarning'], POWER_UNIT)
    dom_info_dict['rxpowerlowwarning'] = strip_unit_and_beautify(dom_info_dict['rxpowerlowwarning'], POWER_UNIT)

    dom_info_dict['txbiashighalarm'] = strip_unit_and_beautify(dom_info_dict['txbiashighalarm'], BIAS_UNIT)
    dom_info_dict['txbiaslowalarm'] = strip_unit_and_beautify(dom_info_dict['txbiaslowalarm'], BIAS_UNIT)
    dom_info_dict['txbiashighwarning'] = strip_unit_and_beautify(dom_info_dict['txbiashighwarning'], BIAS_UNIT)
    dom_info_dict['txbiaslowwarning'] = strip_unit_and_beautify(dom_info_dict['txbiaslowwarning'], BIAS_UNIT)

# Update port sfp info in db

def post_port_sfp_info_to_db(logical_port_name, table, transceiver_dict,
                             stop_event=threading.Event()):
    ganged_port = False
    ganged_member_num = 1

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
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
                fvs = swsscommon.FieldValuePairs(
                    [('type', port_info_dict['type']),
                     ('hardware_rev', port_info_dict['hardware_rev']),
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
                     ])
                table.set(port_name, fvs)
            else:
                return SFP_EEPROM_NOT_READY

        except NotImplementedError:
            helper_logger.log_error("This functionality is currently not implemented for this platform")
            sys.exit(NOT_IMPLEMENTED_ERROR)

# Update port dom threshold info in db


def post_port_dom_threshold_info_to_db(logical_port_name, table,
                                       stop=threading.Event()):
    ganged_port = False
    ganged_member_num = 1

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
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

        port_name = get_physical_port_name(logical_port_name,
                                           ganged_member_num, ganged_port)
        ganged_member_num += 1

        try:
            dom_info_dict = _wrapper_get_transceiver_dom_threshold_info(physical_port)
            if dom_info_dict is not None:
                beautify_dom_threshold_info_dict(dom_info_dict)
                fvs = swsscommon.FieldValuePairs(
                    [('temphighalarm', dom_info_dict['temphighalarm']),
                     ('temphighwarning', dom_info_dict['temphighwarning']),
                     ('templowalarm', dom_info_dict['templowalarm']),
                     ('templowwarning', dom_info_dict['templowwarning']),
                     ('vcchighalarm', dom_info_dict['vcchighalarm']),
                     ('vcchighwarning', dom_info_dict['vcchighwarning']),
                     ('vcclowalarm', dom_info_dict['vcclowalarm']),
                     ('vcclowwarning', dom_info_dict['vcclowwarning']),
                     ('txpowerhighalarm', dom_info_dict['txpowerhighalarm']),
                     ('txpowerlowalarm', dom_info_dict['txpowerlowalarm']),
                     ('txpowerhighwarning', dom_info_dict['txpowerhighwarning']),
                     ('txpowerlowwarning', dom_info_dict['txpowerlowwarning']),
                     ('rxpowerhighalarm', dom_info_dict['rxpowerhighalarm']),
                     ('rxpowerlowalarm', dom_info_dict['rxpowerlowalarm']),
                     ('rxpowerhighwarning', dom_info_dict['rxpowerhighwarning']),
                     ('rxpowerlowwarning', dom_info_dict['rxpowerlowwarning']),
                     ('txbiashighalarm', dom_info_dict['txbiashighalarm']),
                     ('txbiaslowalarm', dom_info_dict['txbiaslowalarm']),
                     ('txbiashighwarning', dom_info_dict['txbiashighwarning']),
                     ('txbiaslowwarning', dom_info_dict['txbiaslowwarning'])
                     ])
                table.set(port_name, fvs)
            else:
                return SFP_EEPROM_NOT_READY

        except NotImplementedError:
            helper_logger.log_error("This functionality is currently not implemented for this platform")
            sys.exit(NOT_IMPLEMENTED_ERROR)

# Update port dom sensor info in db


def post_port_dom_info_to_db(logical_port_name, table, stop_event=threading.Event()):
    ganged_port = False
    ganged_member_num = 1

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
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
            dom_info_dict = _wrapper_get_transceiver_dom_info(physical_port)
            if dom_info_dict is not None:
                beautify_dom_info_dict(dom_info_dict, physical_port)
                if _wrapper_get_sfp_type(physical_port) == 'QSFP_DD':
                    fvs = swsscommon.FieldValuePairs(
                        [('temperature', dom_info_dict['temperature']),
                         ('voltage', dom_info_dict['voltage']),
                         ('rx1power', dom_info_dict['rx1power']),
                         ('rx2power', dom_info_dict['rx2power']),
                         ('rx3power', dom_info_dict['rx3power']),
                         ('rx4power', dom_info_dict['rx4power']),
                         ('rx5power', dom_info_dict['rx5power']),
                         ('rx6power', dom_info_dict['rx6power']),
                         ('rx7power', dom_info_dict['rx7power']),
                         ('rx8power', dom_info_dict['rx8power']),
                         ('tx1bias', dom_info_dict['tx1bias']),
                         ('tx2bias', dom_info_dict['tx2bias']),
                         ('tx3bias', dom_info_dict['tx3bias']),
                         ('tx4bias', dom_info_dict['tx4bias']),
                         ('tx5bias', dom_info_dict['tx5bias']),
                         ('tx6bias', dom_info_dict['tx6bias']),
                         ('tx7bias', dom_info_dict['tx7bias']),
                         ('tx8bias', dom_info_dict['tx8bias']),
                         ('tx1power', dom_info_dict['tx1power']),
                         ('tx2power', dom_info_dict['tx2power']),
                         ('tx3power', dom_info_dict['tx3power']),
                         ('tx4power', dom_info_dict['tx4power']),
                         ('tx5power', dom_info_dict['tx5power']),
                         ('tx6power', dom_info_dict['tx6power']),
                         ('tx7power', dom_info_dict['tx7power']),
                         ('tx8power', dom_info_dict['tx8power'])
                         ])
                else:
                    fvs = swsscommon.FieldValuePairs(
                        [('temperature', dom_info_dict['temperature']),
                         ('voltage', dom_info_dict['voltage']),
                         ('rx1power', dom_info_dict['rx1power']),
                         ('rx2power', dom_info_dict['rx2power']),
                         ('rx3power', dom_info_dict['rx3power']),
                         ('rx4power', dom_info_dict['rx4power']),
                         ('tx1bias', dom_info_dict['tx1bias']),
                         ('tx2bias', dom_info_dict['tx2bias']),
                         ('tx3bias', dom_info_dict['tx3bias']),
                         ('tx4bias', dom_info_dict['tx4bias']),
                         ('tx1power', dom_info_dict['tx1power']),
                         ('tx2power', dom_info_dict['tx2power']),
                         ('tx3power', dom_info_dict['tx3power']),
                         ('tx4power', dom_info_dict['tx4power'])
                         ])

                table.set(port_name, fvs)

            else:
                return SFP_EEPROM_NOT_READY

        except NotImplementedError:
            helper_logger.log_error("This functionality is currently not implemented for this platform")
            sys.exit(NOT_IMPLEMENTED_ERROR)

# Update port dom/sfp info in db


def post_port_sfp_dom_info_to_db(is_warm_start, stop_event=threading.Event()):
    # Connect to STATE_DB and create transceiver dom/sfp info tables
    transceiver_dict, state_db, appl_db, int_tbl, dom_tbl, app_port_tbl = {}, {}, {}, {}, {}, {}

    # Get the namespaces in the platform
    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
        appl_db[asic_id] = daemon_base.db_connect("APPL_DB", namespace)
        int_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_INFO_TABLE)
        dom_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_DOM_SENSOR_TABLE)
        app_port_tbl[asic_id] = swsscommon.ProducerStateTable(appl_db[asic_id], swsscommon.APP_PORT_TABLE_NAME)

    # Post all the current interface dom/sfp info to STATE_DB
    logical_port_list = platform_sfputil.logical
    for logical_port_name in logical_port_list:
        if stop_event.is_set():
            break

        # Get the asic to which this port belongs
        asic_index = platform_sfputil.get_asic_id_for_logical_port(logical_port_name)
        if asic_index is None:
            logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
            continue
        post_port_sfp_info_to_db(logical_port_name, int_tbl[asic_index], transceiver_dict, stop_event)
        post_port_dom_info_to_db(logical_port_name, dom_tbl[asic_index], stop_event)
        post_port_dom_threshold_info_to_db(logical_port_name, dom_tbl[asic_index], stop_event)

        # Do not notify media settings during warm reboot to avoid dataplane traffic impact
        if is_warm_start == False:
            notify_media_setting(logical_port_name, transceiver_dict, app_port_tbl[asic_index])
            transceiver_dict.clear()

# Delete port dom/sfp info from db


def del_port_sfp_dom_info_from_db(logical_port_name, int_tbl, dom_tbl):
    ganged_port = False
    ganged_member_num = 1

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("No physical ports found for logical port '{}'".format(logical_port_name))
        return PHYSICAL_PORT_NOT_EXIST

    if len(physical_port_list) > 1:
        ganged_port = True

    for physical_port in physical_port_list:
        port_name = get_physical_port_name(logical_port_name, ganged_member_num, ganged_port)
        ganged_member_num += 1

        try:
            if int_tbl != None:
                int_tbl._del(port_name)
            if dom_tbl != None:
                dom_tbl._del(port_name)

        except NotImplementedError:
            helper_logger.log_error("This functionality is currently not implemented for this platform")
            sys.exit(NOT_IMPLEMENTED_ERROR)

# recover missing sfp table entries if any


def recover_missing_sfp_table_entries(sfp_util, int_tbl, status_tbl, stop_event):
    transceiver_dict = {}

    logical_port_list = sfp_util.logical
    for logical_port_name in logical_port_list:
        if stop_event.is_set():
            break

        # Get the asic to which this port belongs
        asic_index = sfp_util.get_asic_id_for_logical_port(logical_port_name)
        if asic_index is None:
            logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
            continue

        keys = int_tbl[asic_index].getKeys()
        if logical_port_name not in keys and not sfp_status_helper.detect_port_in_error_status(logical_port_name, status_tbl[asic_index]):
            post_port_sfp_info_to_db(logical_port_name, int_tbl[asic_index], transceiver_dict, stop_event)


def check_port_in_range(range_str, physical_port):
    RANGE_SEPARATOR = '-'

    range_list = range_str.split(RANGE_SEPARATOR)
    start_num = int(range_list[0].strip())
    end_num = int(range_list[1].strip())
    if start_num <= physical_port <= end_num:
        return True
    return False


def get_media_settings_value(physical_port, key):
    GLOBAL_MEDIA_SETTINGS_KEY = 'GLOBAL_MEDIA_SETTINGS'
    PORT_MEDIA_SETTINGS_KEY = 'PORT_MEDIA_SETTINGS'
    DEFAULT_KEY = 'Default'
    RANGE_SEPARATOR = '-'
    COMMA_SEPARATOR = ','
    media_dict = {}
    default_dict = {}

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
                        if check_port_in_range(port, physical_port):
                            media_dict = g_dict[GLOBAL_MEDIA_SETTINGS_KEY][keys]
                            break
                    elif str(physical_port) == port:
                        media_dict = g_dict[GLOBAL_MEDIA_SETTINGS_KEY][keys]
                        break

            elif RANGE_SEPARATOR in keys:
                if check_port_in_range(keys, physical_port):
                    media_dict = g_dict[GLOBAL_MEDIA_SETTINGS_KEY][keys]

            # If there is a match in the global profile for a media type,
            # fetch those values
            if key[0] in media_dict:
                return media_dict[key[0]]
            elif key[1] in media_dict:
                return media_dict[key[1]]
            elif DEFAULT_KEY in media_dict:
                default_dict = media_dict[DEFAULT_KEY]

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
                helper_logger.log_error("Error: No values for physical port '{}'".format(physical_port))
            return {}

        if key[0] in media_dict:
            return media_dict[key[0]]
        elif key[1] in media_dict:
            return media_dict[key[1]]
        elif DEFAULT_KEY in media_dict:
            return media_dict[DEFAULT_KEY]
        elif len(default_dict) != 0:
            return default_dict
    else:
        if len(default_dict) != 0:
            return default_dict

    return {}


def get_media_settings_key(physical_port, transceiver_dict):
    sup_compliance_str = '10/40G Ethernet Compliance Code'
    sup_len_str = 'Length Cable Assembly(m)'
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
        if _wrapper_get_sfp_type(physical_port) == 'QSFP_DD':
            media_compliance_code = media_compliance_dict_str
        else:
            media_compliance_dict = ast.literal_eval(media_compliance_dict_str)
            if sup_compliance_str in media_compliance_dict:
                media_compliance_code = media_compliance_dict[sup_compliance_str]
    except ValueError as e:
        helper_logger.log_error("Invalid value for port {} 'specification_compliance': {}".format(physical_port, media_compliance_dict_str))

    media_type = transceiver_dict[physical_port]['type_abbrv_name']

    if len(media_type) != 0:
        media_key += media_type
    if len(media_compliance_code) != 0:
        media_key += '-' + media_compliance_code
        if _wrapper_get_sfp_type(physical_port) == 'QSFP_DD':
            if media_compliance_code == "passive_copper_media_interface":
                if len(media_len) != 0:
                    media_key += '-' + media_len + 'M'
        else:
            if len(media_len) != 0:
                media_key += '-' + media_len + 'M'
    else:
        media_key += '-' + '*'

    return [vendor_key, media_key]


def get_media_val_str_from_dict(media_dict):
    LANE_STR = 'lane'
    LANE_SEPARATOR = ','

    media_str = ''
    tmp_dict = {}

    for keys in media_dict:
        lane_num = int(keys.strip()[len(LANE_STR):])
        tmp_dict[lane_num] = media_dict[keys]

    for key in range(0, len(tmp_dict)):
        media_str += tmp_dict[key]
        if key != list(tmp_dict.keys())[-1]:
            media_str += LANE_SEPARATOR
    return media_str


def get_media_val_str(num_logical_ports, lane_dict, logical_idx):
    LANE_STR = 'lane'

    logical_media_dict = {}
    num_lanes_on_port = len(lane_dict)

    # The physical ports has more than one logical port meaning it is
    # in breakout mode. So fetch the corresponding lanes from the file
    media_val_str = ''
    if (num_logical_ports > 1) and \
       (num_lanes_on_port >= num_logical_ports):
        num_lanes_per_logical_port = num_lanes_on_port//num_logical_ports
        start_lane = logical_idx * num_lanes_per_logical_port

        for lane_idx in range(start_lane, start_lane +
                              num_lanes_per_logical_port):
            lane_idx_str = LANE_STR + str(lane_idx)
            logical_lane_idx_str = LANE_STR + str(lane_idx - start_lane)
            logical_media_dict[logical_lane_idx_str] = lane_dict[lane_idx_str]

        media_val_str = get_media_val_str_from_dict(logical_media_dict)
    else:
        media_val_str = get_media_val_str_from_dict(lane_dict)
    return media_val_str


def notify_media_setting(logical_port_name, transceiver_dict,
                         app_port_tbl):
    if len(media_settings) == 0:
        return

    ganged_port = False
    ganged_member_num = 1

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("Error: No physical ports found for logical port '{}'".format(logical_port_name))
        return PHYSICAL_PORT_NOT_EXIST

    if len(physical_port_list) > 1:
        ganged_port = True

    for physical_port in physical_port_list:
        logical_port_list = platform_sfputil.get_physical_to_logical(physical_port)
        num_logical_ports = len(logical_port_list)
        logical_idx = logical_port_list.index(logical_port_name)
        if not _wrapper_get_presence(physical_port):
            helper_logger.log_info("Media {} presence not detected during notify".format(physical_port))
            continue
        if physical_port not in transceiver_dict:
            helper_logger.log_error("Media {} eeprom not populated in transceiver dict".format(physical_port))
            continue

        port_name = get_physical_port_name(logical_port_name,
                                           ganged_member_num, ganged_port)
        ganged_member_num += 1
        key = get_media_settings_key(physical_port, transceiver_dict)
        media_dict = get_media_settings_value(physical_port, key)

        if len(media_dict) == 0:
            helper_logger.log_error("Error in obtaining media setting for {}".format(logical_port_name))
            return

        fvs = swsscommon.FieldValuePairs(len(media_dict))

        index = 0
        for media_key in media_dict:
            if type(media_dict[media_key]) is dict:
                media_val_str = get_media_val_str(num_logical_ports,
                                                  media_dict[media_key],
                                                  logical_idx)
            else:
                media_val_str = media_dict[media_key]
            fvs[index] = (str(media_key), str(media_val_str))
            index += 1

        app_port_tbl.set(port_name, fvs)


def waiting_time_compensation_with_sleep(time_start, time_to_wait):
    time_now = time.time()
    time_diff = time_now - time_start
    if time_diff < time_to_wait:
        time.sleep(time_to_wait - time_diff)

# Update port SFP status table on receiving SFP change event


def update_port_transceiver_status_table(logical_port_name, status_tbl, status, error_descriptions='N/A'):
    fvs = swsscommon.FieldValuePairs([('status', status), ('error', error_descriptions)])
    status_tbl.set(logical_port_name, fvs)


# Delete port from SFP status table


def delete_port_from_status_table(logical_port_name, status_tbl):
    status_tbl._del(logical_port_name)

# Init TRANSCEIVER_STATUS table


def init_port_sfp_status_tbl(stop_event=threading.Event()):
    # Connect to STATE_DB and create transceiver status table
    state_db, status_tbl = {}, {}

    # Get the namespaces in the platform
    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
        status_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_STATUS_TABLE)

    # Init TRANSCEIVER_STATUS table
    logical_port_list = platform_sfputil.logical
    for logical_port_name in logical_port_list:
        if stop_event.is_set():
            break

        # Get the asic to which this port belongs
        asic_index = platform_sfputil.get_asic_id_for_logical_port(logical_port_name)
        if asic_index is None:
            logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
            continue

        physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
        if physical_port_list is None:
            helper_logger.log_error("No physical ports found for logical port '{}'".format(logical_port_name))
            update_port_transceiver_status_table(logical_port_name, status_tbl[asic_index], sfp_status_helper.SFP_STATUS_REMOVED)

        for physical_port in physical_port_list:
            if stop_event.is_set():
                break

            if not _wrapper_get_presence(physical_port):
                update_port_transceiver_status_table(logical_port_name, status_tbl[asic_index], sfp_status_helper.SFP_STATUS_REMOVED)
            else:
                update_port_transceiver_status_table(logical_port_name, status_tbl[asic_index], sfp_status_helper.SFP_STATUS_INSERTED)

#
# Helper classes ===============================================================
#

# Thread wrapper class to update dom info periodically


class DomInfoUpdateTask(object):
    def __init__(self):
        self.task_thread = None
        self.task_stopping_event = threading.Event()

    def task_worker(self, y_cable_presence):
        helper_logger.log_info("Start DOM monitoring loop")

        # Connect to STATE_DB and create transceiver dom info table
        state_db, dom_tbl, status_tbl = {}, {}, {}
        mux_tbl = {}

        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            dom_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_DOM_SENSOR_TABLE)
            status_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_STATUS_TABLE)

        # Start loop to update dom info in DB periodically
        while not self.task_stopping_event.wait(DOM_INFO_UPDATE_PERIOD_SECS):
            logical_port_list = platform_sfputil.logical
            for logical_port_name in logical_port_list:
                # Get the asic to which this port belongs
                asic_index = platform_sfputil.get_asic_id_for_logical_port(logical_port_name)
                if asic_index is None:
                    logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
                    continue

                if not sfp_status_helper.detect_port_in_error_status(logical_port_name, status_tbl[asic_index]):
                    post_port_dom_info_to_db(logical_port_name, dom_tbl[asic_index], self.task_stopping_event)
                    post_port_dom_threshold_info_to_db(logical_port_name, dom_tbl[asic_index], self.task_stopping_event)
                    if y_cable_presence[0] is True:
                        y_cable_helper.check_identifier_presence_and_update_mux_info_entry(state_db, mux_tbl, asic_index, logical_port_name)

        helper_logger.log_info("Stop DOM monitoring loop")

    def task_run(self, y_cable_presence):
        if self.task_stopping_event.is_set():
            return

        self.task_thread = threading.Thread(target=self.task_worker, args=(y_cable_presence,))
        self.task_thread.start()

    def task_stop(self):
        self.task_stopping_event.set()
        self.task_thread.join()

# Process wrapper class to update sfp state info periodically


class SfpStateUpdateTask(object):
    def __init__(self):
        self.task_process = None
        self.task_stopping_event = multiprocessing.Event()
        self.sfp_insert_events = {}

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

    def task_worker(self, stopping_event, sfp_error_event, y_cable_presence):
        helper_logger.log_info("Start SFP monitoring loop")

        transceiver_dict = {}
        # Connect to STATE_DB and create transceiver dom/sfp info tables
        state_db, appl_db, int_tbl, dom_tbl, status_tbl, app_port_tbl = {}, {}, {}, {}, {}, {}

        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            int_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_INFO_TABLE)
            dom_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_DOM_SENSOR_TABLE)
            status_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_STATUS_TABLE)

            # Connect to APPL_DB to notify Media notifications
            appl_db[asic_id] = daemon_base.db_connect("APPL_DB", namespace)
            app_port_tbl[asic_id] = swsscommon.ProducerStateTable(appl_db[asic_id], swsscommon.APP_PORT_TABLE_NAME)

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
        while not stopping_event.is_set():
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
                    for key, value in port_dict.items():
                        logical_port_list = platform_sfputil.get_physical_to_logical(int(key))
                        if logical_port_list is None:
                            helper_logger.log_warning("Got unknown FP port index {}, ignored".format(key))
                            continue
                        for logical_port in logical_port_list:

                            # Get the asic to which this port belongs
                            asic_index = platform_sfputil.get_asic_id_for_logical_port(logical_port)
                            if asic_index is None:
                                logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port))
                                continue

                            if value == sfp_status_helper.SFP_STATUS_INSERTED:
                                helper_logger.log_info("Got SFP inserted event")
                                # A plugin event will clear the error state.
                                update_port_transceiver_status_table(
                                    logical_port, status_tbl[asic_index], sfp_status_helper.SFP_STATUS_INSERTED)
                                helper_logger.log_info("receive plug in and update port sfp status table.")
                                rc = post_port_sfp_info_to_db(logical_port, int_tbl[asic_index], transceiver_dict)
                                # If we didn't get the sfp info, assuming the eeprom is not ready, give a try again.
                                if rc == SFP_EEPROM_NOT_READY:
                                    helper_logger.log_warning("SFP EEPROM is not ready. One more try...")
                                    time.sleep(TIME_FOR_SFP_READY_SECS)
                                    post_port_sfp_info_to_db(logical_port, int_tbl[asic_index], transceiver_dict)
                                post_port_dom_info_to_db(logical_port, dom_tbl[asic_index])
                                post_port_dom_threshold_info_to_db(logical_port, dom_tbl[asic_index])
                                notify_media_setting(logical_port, transceiver_dict, app_port_tbl[asic_index])
                                transceiver_dict.clear()
                            elif value == sfp_status_helper.SFP_STATUS_REMOVED:
                                helper_logger.log_info("Got SFP removed event")
                                update_port_transceiver_status_table(
                                    logical_port, status_tbl[asic_index], sfp_status_helper.SFP_STATUS_REMOVED)
                                helper_logger.log_info("receive plug out and update port sfp status table.")
                                del_port_sfp_dom_info_from_db(logical_port, int_tbl[asic_index], dom_tbl[asic_index])
                            else:
                                try:
                                    error_bits = int(value)
                                    helper_logger.log_info("Got SFP error event {}".format(value))

                                    error_descriptions = sfp_status_helper.fetch_generic_error_description(error_bits)

                                    if sfp_status_helper.has_vendor_specific_error(error_bits):
                                        if error_dict:
                                            vendor_specific_error_description = error_dict.get(key)
                                        else:
                                            vendor_specific_error_description = _wrapper_get_sfp_error_description(key)
                                        error_descriptions.append(vendor_specific_error_description)

                                    # Add error info to database
                                    # Any existing error will be replaced by the new one.
                                    update_port_transceiver_status_table(logical_port, status_tbl[asic_index], value, '|'.join(error_descriptions))
                                    helper_logger.log_info("Receive error update port sfp status table.")
                                    # In this case EEPROM is not accessible. The DOM info will be removed since it can be out-of-date.
                                    # The interface info remains in the DB since it is static.
                                    if sfp_status_helper.is_error_block_eeprom_reading(error_bits):
                                        del_port_sfp_dom_info_from_db(logical_port, None, dom_tbl[asic_index])
                                except (TypeError, ValueError) as e:
                                    logger.log_error("Got unrecognized event {}, ignored".format(value))

                    # Since ports could be connected to a mux cable, if there is a change event process the change for being on a Y cable Port
                    y_cable_helper.change_ports_status_for_y_cable_change_event(
                        port_dict, y_cable_presence, stopping_event)
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
                timeout = 0

        helper_logger.log_info("Stop SFP monitoring loop")

    def task_run(self, sfp_error_event, y_cable_presence):
        if self.task_stopping_event.is_set():
            return

        self.task_process = multiprocessing.Process(target=self.task_worker, args=(
            self.task_stopping_event, sfp_error_event, y_cable_presence))
        self.task_process.start()

    def task_stop(self):
        self.task_stopping_event.set()
        os.kill(self.task_process.pid, signal.SIGKILL)

#
# Daemon =======================================================================
#


class DaemonXcvrd(daemon_base.DaemonBase):
    def __init__(self, log_identifier):
        super(DaemonXcvrd, self).__init__(log_identifier)

        self.timeout = XCVRD_MAIN_THREAD_SLEEP_SECS
        self.num_asics = multi_asic.get_num_asics()
        self.stop_event = threading.Event()
        self.sfp_error_event = multiprocessing.Event()
        self.y_cable_presence = [False]

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
        sst = swsscommon.SubscriberStateTable(appl_db, swsscommon.APP_PORT_TABLE_NAME)
        sel.addSelectable(sst)

        # Make sure this daemon started after all port configured
        while not self.stop_event.is_set():
            (state, c) = sel.select(SELECT_TIMEOUT_MSECS)
            if state == swsscommon.Select.TIMEOUT:
                continue
            if state != swsscommon.Select.OBJECT:
                self.log_warning("sel.select() did not return swsscommon.Select.OBJECT")
                continue

            (key, op, fvp) = sst.pop()
            if key in ["PortConfigDone", "PortInitDone"]:
                break

    def load_media_settings(self):
        global media_settings
        global g_dict
        (platform_path, hwsku_path) = device_info.get_paths_to_platform_and_hwsku_dirs()

        media_settings_file_path = os.path.join(platform_path, "media_settings.json")
        if not os.path.isfile(media_settings_file_path):
            self.log_info("xcvrd: No media file exists")
            return {}

        media_file = open(media_settings_file_path, "r")
        media_settings = media_file.read()
        g_dict = json.loads(media_settings)

    # Initialize daemon
    def init(self):
        global platform_sfputil
        global platform_chassis

        self.log_info("Start daemon init...")

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

        # Load port info
        try:
            if multi_asic.is_multi_asic():
                # For multi ASIC platforms we pass DIR of port_config_file_path and the number of asics
                (platform_path, hwsku_path) = device_info.get_paths_to_platform_and_hwsku_dirs()
                platform_sfputil.read_all_porttab_mappings(hwsku_path, self.num_asics)
            else:
                # For single ASIC platforms we pass port_config_file_path and the asic_inst as 0
                port_config_file_path = device_info.get_path_to_port_config_file()
                platform_sfputil.read_porttab_mappings(port_config_file_path, 0)
        except Exception as e:
            self.log_error("Failed to read port info: {}".format(str(e)), True)
            sys.exit(PORT_CONFIG_LOAD_ERROR)

        # Connect to STATE_DB and create transceiver dom/sfp info tables
        state_db, self.int_tbl, self.dom_tbl, self.status_tbl = {}, {}, {}, {}

        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            self.int_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_INFO_TABLE)
            self.dom_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_DOM_SENSOR_TABLE)
            self.status_tbl[asic_id] = swsscommon.Table(state_db[asic_id], TRANSCEIVER_STATUS_TABLE)

        self.load_media_settings()
        warmstart = swsscommon.WarmStart()
        warmstart.initialize("xcvrd", "pmon")
        warmstart.checkWarmStart("xcvrd", "pmon", False)
        is_warm_start = warmstart.isWarmStart()

        # Make sure this daemon started after all port configured
        self.log_info("Wait for port config is done")
        for namespace in namespaces:
            self.wait_for_port_config_done(namespace)

        # Post all the current interface dom/sfp info to STATE_DB
        self.log_info("Post all port DOM/SFP info to DB")
        post_port_sfp_dom_info_to_db(is_warm_start, self.stop_event)

        # Init port sfp status table
        self.log_info("Init port sfp status table")
        init_port_sfp_status_tbl(self.stop_event)

        # Init port y_cable status table
        y_cable_helper.init_ports_status_for_y_cable(
            platform_sfputil, platform_chassis, self.y_cable_presence, self.stop_event)

    # Deinitialize daemon
    def deinit(self):
        self.log_info("Start daemon deinit...")

        # Delete all the information from DB and then exit
        logical_port_list = platform_sfputil.logical
        for logical_port_name in logical_port_list:
            # Get the asic to which this port belongs
            asic_index = platform_sfputil.get_asic_id_for_logical_port(logical_port_name)
            if asic_index is None:
                logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
                continue

            del_port_sfp_dom_info_from_db(logical_port_name, self.int_tbl[asic_index], self.dom_tbl[asic_index])
            delete_port_from_status_table(logical_port_name, self.status_tbl[asic_index])

        if self.y_cable_presence[0] is True:
            y_cable_helper.delete_ports_status_for_y_cable()

        del globals()['platform_chassis']

    # Run daemon

    def run(self):
        self.log_info("Starting up...")

        # Start daemon initialization sequence
        self.init()

        # Start the dom sensor info update thread
        dom_info_update = DomInfoUpdateTask()
        dom_info_update.task_run(self.y_cable_presence)

        # Start the sfp state info update process
        sfp_state_update = SfpStateUpdateTask()
        sfp_state_update.task_run(self.sfp_error_event, self.y_cable_presence)

        # Start the Y-cable state info update process if Y cable presence established
        y_cable_state_update = None
        if self.y_cable_presence[0] is True:
            y_cable_state_update = y_cable_helper.YCableTableUpdateTask()
            y_cable_state_update.task_run()

        # Start main loop
        self.log_info("Start daemon main loop")

        while not self.stop_event.wait(self.timeout):
            # Check the integrity of the sfp info table and recover the missing entries if any
            recover_missing_sfp_table_entries(platform_sfputil, self.int_tbl, self.status_tbl, self.stop_event)

        self.log_info("Stop daemon main loop")

        # Stop the dom sensor info update thread
        dom_info_update.task_stop()

        # Stop the sfp state info update process
        sfp_state_update.task_stop()

        # Stop the Y-cable state info update process
        if self.y_cable_presence[0] is True:
            y_cable_state_update.task_stop()

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
    xcvrd = DaemonXcvrd(SYSLOG_IDENTIFIER)
    xcvrd.run()


if __name__ == '__main__':
    main()
