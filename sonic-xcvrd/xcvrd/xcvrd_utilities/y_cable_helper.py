"""
    y_cable_helper.py
    helper utlities configuring y_cable for xcvrd daemon
"""

import threading
import time

from sonic_py_common import daemon_base, logger
from sonic_py_common import multi_asic
from sonic_y_cable import y_cable
from swsscommon import swsscommon


SELECT_TIMEOUT = 1000

y_cable_platform_sfputil = None
y_cable_platform_chassis = None

SYSLOG_IDENTIFIER = "y_cable_helper"

helper_logger = logger.Logger(SYSLOG_IDENTIFIER)


# SFP status definition, shall be aligned with the definition in get_change_event() of ChassisBase
SFP_STATUS_REMOVED = '0'
SFP_STATUS_INSERTED = '1'

# SFP error codes, stored as strings. Can add more as needed.
SFP_STATUS_ERR_I2C_STUCK = '2'
SFP_STATUS_ERR_BAD_EEPROM = '3'
SFP_STATUS_ERR_UNSUPPORTED_CABLE = '4'
SFP_STATUS_ERR_HIGH_TEMP = '5'
SFP_STATUS_ERR_BAD_CABLE = '6'

# Store the error codes in a set for convenience
errors_block_eeprom_reading = {
    SFP_STATUS_ERR_I2C_STUCK,
    SFP_STATUS_ERR_BAD_EEPROM,
    SFP_STATUS_ERR_UNSUPPORTED_CABLE,
    SFP_STATUS_ERR_HIGH_TEMP,
    SFP_STATUS_ERR_BAD_CABLE
}

Y_CABLE_STATUS_NO_TOR_ACTIVE = 0
Y_CABLE_STATUS_TORA_ACTIVE = 1
Y_CABLE_STATUS_TORB_ACTIVE = 2

y_cable_switch_state_values = {
    Y_CABLE_STATUS_NO_TOR_ACTIVE,
    Y_CABLE_STATUS_TORA_ACTIVE,
    Y_CABLE_STATUS_TORB_ACTIVE
}

MUX_CABLE_STATIC_INFO_TABLE = "MUX_CABLE_STATIC_INFO"
MUX_CABLE_INFO_TABLE = "MUX_CABLE_INFO"

# Find out the underneath physical port list by logical name


def logical_port_name_to_physical_port_list(port_name):
    if port_name.startswith("Ethernet"):
        if y_cable_platform_sfputil.is_logical_port(port_name):
            return y_cable_platform_sfputil.get_logical_to_physical(port_name)
        else:
            helper_logger.log_error("Invalid port '%s'" % port_name)
            return None
    else:
        return [int(port_name)]


def _wrapper_get_presence(physical_port):
    if y_cable_platform_chassis is not None:
        try:
            return y_cable_platform_chassis.get_sfp(physical_port).get_presence()
        except NotImplementedError:
            pass
    return y_cable_platform_sfputil.get_presence(physical_port)


# Delete port from Y cable status table
def delete_port_from_y_cable_table(logical_port_name, y_cable_tbl):
    if y_cable_tbl is not None:
        y_cable_tbl._del(logical_port_name)


def update_table_mux_status_for_response_tbl(table_name, status, logical_port_name):
    fvs = swsscommon.FieldValuePairs([('response', status)])
    table_name.set(logical_port_name, fvs)


def update_table_mux_status_for_statedb_port_tbl(table_name, status, read_side, active_side, logical_port_name):
    fvs = swsscommon.FieldValuePairs([('state', status),
                                      ('read_side', str(read_side)),
                                      ('active_side', str(active_side))])
    table_name.set(logical_port_name, fvs)


def y_cable_toggle_mux_torA(physical_port):
    update_status = y_cable.toggle_mux_to_torA(physical_port)
    if update_status is True:
        return 1
    else:
        helper_logger.log_warning(
            "Error: Could not toggle the mux for port {} to torA write eeprom failed".format(physical_port))
        return -1


def y_cable_toggle_mux_torB(physical_port):
    update_status = y_cable.toggle_mux_to_torB(physical_port)
    if update_status is True:
        return 2
    else:
        helper_logger.log_warning(
            "Error: Could not toggle the mux for port {} to torB write eeprom failed".format(physical_port))
        return -1


def update_tor_active_side(read_side, state, logical_port_name):
    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if _wrapper_get_presence(physical_port):
            if int(read_side) == 1:
                if state == "active":
                    return y_cable_toggle_mux_torA(physical_port)
                elif state == "standby":
                    return y_cable_toggle_mux_torB(physical_port)
            elif int(read_side) == 2:
                if state == "active":
                    return y_cable_toggle_mux_torB(physical_port)
                elif state == "standby":
                    return y_cable_toggle_mux_torA(physical_port)

            # TODO: Should we confirm that the mux was indeed toggled?

        else:
            helper_logger.log_warning(
                "Error: Could not establish presence for  Y cable port {} while trying to toggle the mux".format(logical_port_name))
            return -1

    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable table port {} while trying to toggle the mux".format(logical_port_name))
        return -1


def update_appdb_port_mux_cable_response_table(logical_port_name, asic_index, appl_db, read_side):

    status = None
    y_cable_response_tbl = {}

    y_cable_response_tbl[asic_index] = swsscommon.Table(
        appl_db[asic_index], "MUX_CABLE_RESPONSE_TABLE")
    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if _wrapper_get_presence(physical_port):

            if read_side is None:

                status = 'unknown'
                update_table_mux_status_for_response_tbl(y_cable_response_tbl[asic_index], status, logical_port_name)
                helper_logger.log_warning(
                    "Error: Could not get read side for mux cable port probe command logical port {} and physical port {}".format(logical_port_name, physical_port))
                return

            active_side = y_cable.check_mux_direction(physical_port)

            if active_side is None:

                status = 'unknown'
                update_table_mux_status_for_response_tbl(y_cable_response_tbl[asic_index], status, logical_port_name)
                helper_logger.log_warning(
                    "Error: Could not get active side for mux cable port probe command logical port {} and physical port {}".format(logical_port_name, physical_port))
                return

            if read_side == active_side and (active_side == 1 or active_side == 2):
                status = 'active'
            elif read_side != active_side and (active_side == 1 or active_side == 2):
                status = 'standby'
            else:
                status = 'unknown'
                helper_logger.log_warning(
                    "Error: Could not get state for mux cable port probe command logical port {} and physical port {}".format(logical_port_name, physical_port))

            update_table_mux_status_for_response_tbl(y_cable_response_tbl[asic_index], status, logical_port_name)

        else:

            status = 'unknown'
            update_table_mux_status_for_response_tbl(y_cable_response_tbl[asic_index], status, logical_port_name)
            helper_logger.log_warning(
                "Error: Could not establish presence for Y cable port {} while responding to command probe".format(logical_port_name))
    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen

        status = 'unknown'
        update_table_mux_status_for_response_tbl(y_cable_response_tbl[asic_index], status, logical_port_name)
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable port {} while responding to command probe".format(logical_port_name))


def read_y_cable_and_update_statedb_port_tbl(logical_port_name, mux_config_tbl):
    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)

    read_side = None
    active_side = None
    status = None
    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if _wrapper_get_presence(physical_port):
            read_side = y_cable.check_read_side(physical_port)
            if read_side is None:
                read_side = active_side = -1
                update_table_mux_status_for_statedb_port_tbl(
                    mux_config_tbl, "unknown", read_side, active_side, logical_port_name)
                helper_logger.log_error(
                    "Error: Could not establish the read side for  Y cable port {}".format(logical_port_name))
                return

            active_side = y_cable.check_mux_direction(physical_port)
            if active_side is None or active_side not in y_cable_switch_state_values:
                read_side = active_side = -1
                update_table_mux_status_for_statedb_port_tbl(
                    mux_config_tbl, "unknown", read_side, active_side, logical_port_name)
                helper_logger.log_error(
                    "Error: Could not establish the active side for  Y cable port {}".format(logical_port_name))
                return

            if read_side == active_side and (active_side == 1 or active_side == 2):
                status = 'active'
            elif read_side != active_side and (active_side == 1 or active_side == 2):
                status = 'standby'
            else:
                status = 'unknown'
                helper_logger.log_warning(
                    "Error: Could not establish the active status for  Y cable port {}".format(logical_port_name))

            update_table_mux_status_for_statedb_port_tbl(
                mux_config_tbl, status, read_side, active_side, logical_port_name)
            return

        else:
            read_side = active_side = -1
            update_table_mux_status_for_statedb_port_tbl(
                mux_config_tbl, "unknown", read_side, active_side, logical_port_name)
            helper_logger.log_warning(
                "Error: Could not establish presence for  Y cable port {}".format(logical_port_name))
    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen
        read_side = active_side = -1
        update_table_mux_status_for_statedb_port_tbl(
            mux_config_tbl, "unknown", read_side, active_side, logical_port_name)
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable port {}".format(logical_port_name))


def check_identifier_presence_and_update_mux_table_entry(state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence):

    (status, fvs) = port_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_warning(
            "Could not retreive fieldvalue pairs for {}, inside config_db".format(logical_port_name))
        return

    else:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "mux_cable" in mux_table_dict:
            val = mux_table_dict.get("mux_cable", None)
            if val == "true":

                y_cable_asic_table = y_cable_tbl.get(asic_index, None)
                mux_asic_table = mux_tbl.get(asic_index, None)
                static_mux_asic_table = static_tbl.get(asic_index, None)
                if y_cable_presence[0] is True and y_cable_asic_table is not None and mux_asic_table is not None and static_mux_asic_table is not None:
                    # fill in the newly found entry
                    read_y_cable_and_update_statedb_port_tbl(
                        logical_port_name, y_cable_tbl[asic_index])
                    post_port_mux_info_to_db(logical_port_name,  mux_tbl[asic_index])
                    post_port_mux_static_info_to_db(logical_port_name,  static_tbl[asic_index])

                else:
                    # first create the state db y cable table and then fill in the entry
                    y_cable_presence[:] = [True]
                    namespaces = multi_asic.get_front_end_namespaces()
                    for namespace in namespaces:
                        asic_id = multi_asic.get_asic_index_from_namespace(
                            namespace)
                        state_db[asic_id] = daemon_base.db_connect(
                            "STATE_DB", namespace)
                        y_cable_tbl[asic_id] = swsscommon.Table(
                            state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
                        static_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_STATIC_INFO_TABLE)
                        mux_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_INFO_TABLE)
                    # fill the newly found entry
                    read_y_cable_and_update_statedb_port_tbl(
                        logical_port_name, y_cable_tbl[asic_index])
                    post_port_mux_info_to_db(logical_port_name,  mux_tbl[asic_index])
                    post_port_mux_static_info_to_db(logical_port_name,  static_tbl[asic_index])


def check_identifier_presence_and_delete_mux_table_entry(state_db, port_tbl, asic_index, logical_port_name, y_cable_presence, delete_change_event):

    y_cable_tbl = {}
    static_tbl, mux_tbl = {}, {}

    # if there is No Y cable do not do anything here
    if y_cable_presence[0] is False:
        return

    (status, fvs) = port_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_warning(
            "Could not retreive fieldvalue pairs for {}, inside config_db".format(logical_port_name))
        return

    else:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "mux_cable" in mux_table_dict:
            if y_cable_presence[0] is True:
                # delete this entry in the y cable table found and update the delete event
                namespaces = multi_asic.get_front_end_namespaces()
                for namespace in namespaces:
                    asic_id = multi_asic.get_asic_index_from_namespace(
                        namespace)
                    state_db[asic_id] = daemon_base.db_connect(
                        "STATE_DB", namespace)
                    y_cable_tbl[asic_id] = swsscommon.Table(
                        state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
                    static_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_STATIC_INFO_TABLE)
                    mux_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_INFO_TABLE)
                # fill the newly found entry
                delete_port_from_y_cable_table(
                    logical_port_name, y_cable_tbl[asic_index])
                delete_port_from_y_cable_table(
                    logical_port_name, static_tbl[asic_index])
                delete_port_from_y_cable_table(
                    logical_port_name, mux_tbl[asic_index])
                delete_change_event[:] = [True]


def init_ports_status_for_y_cable(platform_sfp, platform_chassis, y_cable_presence, stop_event=threading.Event()):
    global y_cable_platform_sfputil
    global y_cable_platform_chassis
    # Connect to CONFIG_DB and create port status table inside state_db
    config_db, state_db, port_tbl, y_cable_tbl = {}, {}, {}, {}
    static_tbl, mux_tbl = {}, {}
    port_table_keys = {}

    y_cable_platform_sfputil = platform_sfp
    y_cable_platform_chassis = platform_chassis

    # Get the namespaces in the platform
    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
        port_tbl[asic_id] = swsscommon.Table(config_db[asic_id], "PORT")
        port_table_keys[asic_id] = port_tbl[asic_id].getKeys()

    # Init PORT_STATUS table if ports are on Y cable
    logical_port_list = y_cable_platform_sfputil.logical
    for logical_port_name in logical_port_list:
        if stop_event.is_set():
            break

        # Get the asic to which this port belongs
        asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(
            logical_port_name)
        if asic_index is None:
            helper_logger.log_warning(
                "Got invalid asic index for {}, ignored".format(logical_port_name))
            continue

        if logical_port_name in port_table_keys[asic_index]:
            check_identifier_presence_and_update_mux_table_entry(
                state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
        else:
            # This port does not exist in Port table of config but is present inside
            # logical_ports after loading the port_mappings from port_config_file
            # This should not happen
            helper_logger.log_warning(
                "Could not retreive port inside config_db PORT table ".format(logical_port_name))


def change_ports_status_for_y_cable_change_event(port_dict, y_cable_presence, stop_event=threading.Event()):
    # Connect to CONFIG_DB and create port status table inside state_db
    config_db, state_db, port_tbl, y_cable_tbl = {}, {}, {}, {}
    static_tbl, mux_tbl = {}, {}
    port_table_keys = {}
    delete_change_event = [False]

    # Get the namespaces in the platform
    namespaces = multi_asic.get_front_end_namespaces()
    # Get the keys from PORT table inside config db to prepare check for mux_cable identifier
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
        port_tbl[asic_id] = swsscommon.Table(config_db[asic_id], "PORT")
        port_table_keys[asic_id] = port_tbl[asic_id].getKeys()

    # Init PORT_STATUS table if ports are on Y cable and an event is received
    for key, value in port_dict.items():
        if stop_event.is_set():
            break
        logical_port_list = y_cable_platform_sfputil.get_physical_to_logical(int(key))
        if logical_port_list is None:
            helper_logger.log_warning("Got unknown FP port index {}, ignored".format(key))
            continue
        for logical_port_name in logical_port_list:

            # Get the asic to which this port belongs
            asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(logical_port_name)
            if asic_index is None:
                helper_logger.log_warning(
                    "Got invalid asic index for {}, ignored".format(logical_port_name))
                continue

            if logical_port_name in port_table_keys[asic_index]:
                if value == SFP_STATUS_INSERTED:
                    helper_logger.log_info("Got SFP inserted event")
                    check_identifier_presence_and_update_mux_table_entry(
                        state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
                elif value == SFP_STATUS_REMOVED or value in errors_block_eeprom_reading:
                    check_identifier_presence_and_delete_mux_table_entry(
                        state_db, port_tbl, asic_index, logical_port_name, y_cable_presence, delete_change_event)

                else:
                    # SFP return unkown event, just ignore for now.
                    helper_logger.log_warning("Got unknown event {}, ignored".format(value))
                    continue

    # If there was a delete event and y_cable_presence was true, reaccess the y_cable presence
    if y_cable_presence[0] is True and delete_change_event[0] is True:

        y_cable_presence[:] = [False]
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(
                namespace)
            y_cable_tbl[asic_id] = swsscommon.Table(
                state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            y_cable_table_size = len(y_cable_tbl[asic_id].getKeys())
            if y_cable_table_size > 0:
                y_cable_presence[:] = [True]
                break


def delete_ports_status_for_y_cable():

    state_db, port_tbl, y_cable_tbl = {}, {}, {}
    y_cable_tbl_keys = {}
    static_tbl, mux_tbl = {}, {}
    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
        y_cable_tbl[asic_id] = swsscommon.Table(
            state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        y_cable_tbl_keys[asic_id] = y_cable_tbl[asic_id].getKeys()
        static_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_STATIC_INFO_TABLE)
        mux_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_INFO_TABLE)

    # delete PORTS on Y cable table if ports on Y cable
    logical_port_list = y_cable_platform_sfputil.logical
    for logical_port_name in logical_port_list:

        # Get the asic to which this port belongs
        asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(
            logical_port_name)
        if asic_index is None:
            logger.log_warning(
                "Got invalid asic index for {}, ignored".format(logical_port_name))

        if logical_port_name in y_cable_tbl_keys[asic_index]:
            delete_port_from_y_cable_table(
                logical_port_name, y_cable_tbl[asic_index])
            delete_port_from_y_cable_table(
                logical_port_name, static_tbl[asic_index])
            delete_port_from_y_cable_table(
                logical_port_name, mux_tbl[asic_index])


def check_identifier_presence_and_update_mux_info_entry(state_db, mux_tbl, asic_index, logical_port_name):

    # Get the namespaces in the platform
    config_db, port_tbl = {}, {}
    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
        port_tbl[asic_id] = swsscommon.Table(config_db[asic_id], "PORT")

    (status, fvs) = port_tbl[asic_index].get(logical_port_name)

    if status is False:
        helper_logger.log_warning(
            "Could not retreive fieldvalue pairs for {}, inside config_db".format(logical_port_name))
        return

    else:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "mux_cable" in mux_table_dict:
            val = mux_table_dict.get("mux_cable", None)
            if val == "true":

                if mux_tbl.get(asic_index, None) is not None:
                    # fill in the newly found entry
                    post_port_mux_info_to_db(logical_port_name,  mux_tbl[asic_index])

                else:
                    # first create the state db y cable table and then fill in the entry
                    namespaces = multi_asic.get_front_end_namespaces()
                    for namespace in namespaces:
                        asic_id = multi_asic.get_asic_index_from_namespace(
                            namespace)
                        mux_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_INFO_TABLE)
                    # fill the newly found entry
                    post_port_mux_info_to_db(logical_port_name,  mux_tbl[asic_index])


def get_firmware_dict(physical_port, target, side, mux_info_dict):

    result = y_cable.get_firmware_version(physical_port, target)

    if result is not None and isinstance(result, dict):
        mux_info_dict[("build_slot1_{}".format(side))] = result.get("build_slot1", None)
        mux_info_dict[("version_slot1_{}".format(side))] = result.get("version_slot1", None)
        mux_info_dict[("build_slot2_{}".format(side))] = result.get("build_slot2", None)
        mux_info_dict[("version_slot2_{}".format(side))] = result.get("version_slot2", None)
        mux_info_dict[("run_slot1_{}".format(side))] = result.get("run_slot1", None)
        mux_info_dict[("run_slot2_{}".format(side))] = result.get("run_slot2", None)
        mux_info_dict[("commit_slot1_{}".format(side))] = result.get("commit_slot1", None)
        mux_info_dict[("commit_slot2_{}".format(side))] = result.get("commit_slot2", None)
        mux_info_dict[("empty_slot1_{}".format(side))] = result.get("empty_slot1", None)
        mux_info_dict[("empty_slot2_{}".format(side))] = result.get("empty_slot2", None)
    else:
        mux_info_dict[("build_slot1_{}".format(side))] = "N/A"
        mux_info_dict[("version_slot1_{}".format(side))] = "N/A"
        mux_info_dict[("build_slot2_{}".format(side))] = "N/A"
        mux_info_dict[("version_slot2_{}".format(side))] = "N/A"
        mux_info_dict[("run_slot1_{}".format(side))] = "N/A"
        mux_info_dict[("run_slot2_{}".format(side))] = "N/A"
        mux_info_dict[("commit_slot1_{}".format(side))] = "N/A"
        mux_info_dict[("commit_slot2_{}".format(side))] = "N/A"
        mux_info_dict[("empty_slot1_{}".format(side))] = "N/A"
        mux_info_dict[("empty_slot2_{}".format(side))] = "N/A"


def get_muxcable_info(physical_port, logical_port_name):

    mux_info_dict = {}
    y_cable_tbl, state_db = {}, {}

    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
        y_cable_tbl[asic_id] = swsscommon.Table(
            state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)

    asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(
        logical_port_name)
    if asic_index is None:
        helper_logger.log_warning(
            "Got invalid asic index for {}, ignored".format(logical_port_name))
        return -1

    (status, fvs) = y_cable_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_warning("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
            logical_port_name, y_cable_tbl[asic_index]))
        return -1

    mux_port_dict = dict(fvs)
    read_side = int(mux_port_dict.get("read_side"))

    active_side = y_cable.check_active_linked_tor_side(physical_port)

    if active_side is None or active_side == y_cable.EEPROM_ERROR:
        tor_active = 'unknown'
    elif read_side == active_side and (active_side == 1 or active_side == 2):
        tor_active = 'active'
    elif read_side != active_side and (active_side == 1 or active_side == 2):
        tor_active = 'standby'
    else:
        tor_active = 'unknown'

    mux_info_dict["tor_active"] = tor_active

    mux_dir_val = y_cable.check_mux_direction(physical_port)
    if mux_dir_val is None or mux_dir_val == y_cable.EEPROM_ERROR:
        mux_direction = 'unknown'
    elif read_side == mux_dir_val and (active_side == 1 or active_side == 2):
        mux_direction = 'self'
    elif read_side != mux_dir_val and (active_side == 1 or active_side == 2):
        mux_direction = 'peer'
    else:
        mux_direction = 'unknown'

    mux_info_dict["mux_direction"] = mux_direction

    manual_switch_cnt = y_cable.get_switch_count(physical_port, y_cable.SWITCH_COUNT_MANUAL)
    auto_switch_cnt = y_cable.get_switch_count(physical_port, y_cable.SWITCH_COUNT_AUTO)

    if manual_switch_cnt is not y_cable.EEPROM_ERROR:
        mux_info_dict["manual_switch_count"] = manual_switch_cnt
    else:
        mux_info_dict["manual_switch_count"] = "N/A"

    if auto_switch_cnt is not y_cable.EEPROM_ERROR:
        mux_info_dict["auto_switch_count"] = auto_switch_cnt
    else:
        mux_info_dict["auto_switch_count"] = "N/A"

    lane_active = y_cable.check_if_nic_lanes_active(physical_port)

    if lane_active is not y_cable.EEPROM_ERROR:
        if (lane_active & 0x1):
            mux_info_dict["nic_lane1_active"] = "True"
        else:
            mux_info_dict["nic_lane1_active"] = "False"

        if ((lane_active >> 1) & 0x1):
            mux_info_dict["nic_lane2_active"] = "True"
        else:
            mux_info_dict["nic_lane2_active"] = "False"

        if ((lane_active >> 2) & 0x1):
            mux_info_dict["nic_lane3_active"] = "True"
        else:
            mux_info_dict["nic_lane3_active"] = "False"

        if ((lane_active >> 3) & 0x1):
            mux_info_dict["nic_lane4_active"] = "True"
        else:
            mux_info_dict["nic_lane4_active"] = "False"
    else:
        mux_info_dict["nic_lane1_active"] = "N/A"
        mux_info_dict["nic_lane2_active"] = "N/A"
        mux_info_dict["nic_lane3_active"] = "N/A"
        mux_info_dict["nic_lane4_active"] = "N/A"

    if read_side == 1:
        eye_result_self = y_cable.get_eye_info(physical_port, 1)
        eye_result_peer = y_cable.get_eye_info(physical_port, 2)
    else:
        eye_result_self = y_cable.get_eye_info(physical_port, 2)
        eye_result_peer = y_cable.get_eye_info(physical_port, 1)

    eye_result_nic = y_cable.get_eye_info(physical_port, 3)

    if eye_result_self is not None and eye_result_self is not y_cable.EEPROM_ERROR and isinstance(eye_result_self, list):
        mux_info_dict["self_eye_height_lane1"] = eye_result_self[0]
        mux_info_dict["self_eye_height_lane2"] = eye_result_self[1]
    else:
        mux_info_dict["self_eye_height_lane1"] = "N/A"
        mux_info_dict["self_eye_height_lane2"] = "N/A"

    if eye_result_peer is not None and eye_result_peer is not y_cable.EEPROM_ERROR and isinstance(eye_result_peer, list):
        mux_info_dict["peer_eye_height_lane1"] = eye_result_peer[0]
        mux_info_dict["peer_eye_height_lane2"] = eye_result_peer[1]
    else:
        mux_info_dict["peer_eye_height_lane1"] = "N/A"
        mux_info_dict["peer_eye_height_lane2"] = "N/A"

    if eye_result_nic is not None and eye_result_nic is not y_cable.EEPROM_ERROR and isinstance(eye_result_nic, list):
        mux_info_dict["nic_eye_height_lane1"] = eye_result_nic[0]
        mux_info_dict["nic_eye_height_lane2"] = eye_result_nic[1]
    else:
        mux_info_dict["nic_eye_height_lane1"] = "N/A"
        mux_info_dict["nic_eye_height_lane2"] = "N/A"

    if read_side == 1:
        if y_cable.check_if_link_is_active_for_torA(physical_port):
            mux_info_dict["link_status_self"] = "up"
        else:
            mux_info_dict["link_status_self"] = "down"
        if y_cable.check_if_link_is_active_for_torB(physical_port):
            mux_info_dict["link_status_peer"] = "up"
        else:
            mux_info_dict["link_status_peer"] = "down"
    else:
        if y_cable.check_if_link_is_active_for_torB(physical_port):
            mux_info_dict["link_status_self"] = "up"
        else:
            mux_info_dict["link_status_self"] = "down"
        if y_cable.check_if_link_is_active_for_torA(physical_port):
            mux_info_dict["link_status_peer"] = "up"
        else:
            mux_info_dict["link_status_peer"] = "down"

    if y_cable.check_if_link_is_active_for_NIC(physical_port):
        mux_info_dict["link_status_nic"] = "up"
    else:
        mux_info_dict["link_status_nic"] = "down"

    get_firmware_dict(physical_port, 0, "nic", mux_info_dict)
    get_firmware_dict(physical_port, 1, "tor1", mux_info_dict)
    get_firmware_dict(physical_port, 2, "tor2", mux_info_dict)

    res = y_cable.get_internal_voltage_temp(physical_port)

    if res is not y_cable.EEPROM_ERROR and isinstance(res, tuple):
        mux_info_dict["internal_temperature"] = res[0]
        mux_info_dict["internal_voltage"] = res[1]
    else:
        mux_info_dict["internal_temperature"] = "N/A"
        mux_info_dict["internal_voltage"] = "N/A"

    res = y_cable.get_nic_voltage_temp(physical_port)

    if res is not y_cable.EEPROM_ERROR and isinstance(res, tuple):
        mux_info_dict["nic_temperature"] = res[0]
        mux_info_dict["nic_voltage"] = res[1]
    else:
        mux_info_dict["nic_temperature"] = "N/A"
        mux_info_dict["nic_voltage"] = "N/A"

    return mux_info_dict


def get_muxcable_static_info(physical_port, logical_port_name):

    mux_static_info_dict = {}
    y_cable_tbl, state_db = {}, {}

    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
        y_cable_tbl[asic_id] = swsscommon.Table(
            state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)

    asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(
        logical_port_name)
    if asic_index is None:
        helper_logger.log_warning(
            "Got invalid asic index for {}, ignored".format(logical_port_name))
        return -1

    (status, fvs) = y_cable_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_warning("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
            logical_port_name, y_cable_tbl[asic_index]))
        return -1
    mux_port_dict = dict(fvs)
    read_side = int(mux_port_dict.get("read_side"))

    if read_side == 1:
        mux_static_info_dict["read_side"] = "tor1"
    else:
        mux_static_info_dict["read_side"] = "tor2"

    dummy_list = ["N/A", "N/A", "N/A", "N/A", "N/A"]
    cursor_nic_values = []
    cursor_tor1_values = []
    cursor_tor2_values = []
    for i in range(1, 3):
        cursor_values_nic = y_cable.get_target_cursor_values(physical_port, i, y_cable.TARGET_NIC)
        if cursor_values_nic is not None and cursor_values_nic is not y_cable.EEPROM_ERROR and isinstance(cursor_values_nic, list):
            cursor_nic_values.append(cursor_values_nic)
        else:
            cursor_nic_values.append(dummy_list)
        cursor_values_tor1 = y_cable.get_target_cursor_values(physical_port, i, y_cable.TARGET_TOR1)
        if cursor_values_tor1 is not None and cursor_values_tor1 is not y_cable.EEPROM_ERROR and isinstance(cursor_values_tor1, list):
            cursor_tor1_values.append(cursor_values_tor1)
        else:
            cursor_tor1_values.append(dummy_list)

        cursor_values_tor2 = y_cable.get_target_cursor_values(physical_port, i, y_cable.TARGET_TOR2)
        if cursor_values_tor2 is not None and cursor_values_tor2 is not y_cable.EEPROM_ERROR and isinstance(cursor_values_tor2, list):
            cursor_tor2_values.append(cursor_values_tor2)
        else:
            cursor_tor2_values.append(dummy_list)

    for i in range(1, 3):
        mux_static_info_dict[("nic_lane{}_precursor1".format(i))] = cursor_nic_values[i-1][0]
        mux_static_info_dict[("nic_lane{}_precursor2".format(i))] = cursor_nic_values[i-1][1]
        mux_static_info_dict[("nic_lane{}_maincursor".format(i))] = cursor_nic_values[i-1][2]
        mux_static_info_dict[("nic_lane{}_postcursor1".format(i))] = cursor_nic_values[i-1][3]
        mux_static_info_dict[("nic_lane{}_postcursor2".format(i))] = cursor_nic_values[i-1][4]

    if read_side == 1:
        for i in range(1, 3):
            mux_static_info_dict[("tor_self_lane{}_precursor1".format(i))] = cursor_tor1_values[i-1][0]
            mux_static_info_dict[("tor_self_lane{}_precursor2".format(i))] = cursor_tor1_values[i-1][1]
            mux_static_info_dict[("tor_self_lane{}_maincursor".format(i))] = cursor_tor1_values[i-1][2]
            mux_static_info_dict[("tor_self_lane{}_postcursor1".format(i))] = cursor_tor1_values[i-1][3]
            mux_static_info_dict[("tor_self_lane{}_postcursor2".format(i))] = cursor_tor1_values[i-1][4]

        for i in range(1, 3):
            mux_static_info_dict[("tor_peer_lane{}_precursor1".format(i))] = cursor_tor2_values[i-1][0]
            mux_static_info_dict[("tor_peer_lane{}_precursor2".format(i))] = cursor_tor2_values[i-1][1]
            mux_static_info_dict[("tor_peer_lane{}_maincursor".format(i))] = cursor_tor2_values[i-1][2]
            mux_static_info_dict[("tor_peer_lane{}_postcursor1".format(i))] = cursor_tor2_values[i-1][3]
            mux_static_info_dict[("tor_peer_lane{}_postcursor2".format(i))] = cursor_tor2_values[i-1][4]
    else:
        for i in range(1, 3):
            mux_static_info_dict[("tor_self_lane{}_precursor1".format(i))] = cursor_tor2_values[i-1][0]
            mux_static_info_dict[("tor_self_lane{}_precursor2".format(i))] = cursor_tor2_values[i-1][1]
            mux_static_info_dict[("tor_self_lane{}_maincursor".format(i))] = cursor_tor2_values[i-1][2]
            mux_static_info_dict[("tor_self_lane{}_postcursor1".format(i))] = cursor_tor2_values[i-1][3]
            mux_static_info_dict[("tor_self_lane{}_postcursor2".format(i))] = cursor_tor2_values[i-1][4]

        for i in range(1, 3):
            mux_static_info_dict[("tor_peer_lane{}_precursor1".format(i))] = cursor_tor1_values[i-1][0]
            mux_static_info_dict[("tor_peer_lane{}_precursor2".format(i))] = cursor_tor1_values[i-1][1]
            mux_static_info_dict[("tor_peer_lane{}_maincursor".format(i))] = cursor_tor1_values[i-1][2]
            mux_static_info_dict[("tor_peer_lane{}_postcursor1".format(i))] = cursor_tor1_values[i-1][3]
            mux_static_info_dict[("tor_peer_lane{}_postcursor2".format(i))] = cursor_tor1_values[i-1][4]

    return mux_static_info_dict


def post_port_mux_info_to_db(logical_port_name, table):

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("No physical ports found for logical port '{}'".format(logical_port_name))
        return -1

    if len(physical_port_list) > 1:
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable port {}".format(logical_port_name))
        return -1

    for physical_port in physical_port_list:

        if not _wrapper_get_presence(physical_port):
            helper_logger.log_warning(
                "Error: trying to post mux info without presence of port {}".format(logical_port_name))
            continue

        mux_info_dict = get_muxcable_info(physical_port, logical_port_name)
        if mux_info_dict is not None and mux_info_dict is not -1:
            #transceiver_dict[physical_port] = port_info_dict
            fvs = swsscommon.FieldValuePairs(
                [('tor_active',  mux_info_dict["tor_active"]),
                 ('mux_direction',  str(mux_info_dict["mux_direction"])),
                 ('manual_switch_count', str(mux_info_dict["manual_switch_count"])),
                 ('auto_switch_count', str(mux_info_dict["auto_switch_count"])),
                 ('link_status_self', mux_info_dict["link_status_self"]),
                 ('link_status_peer', mux_info_dict["link_status_peer"]),
                 ('link_status_nic', mux_info_dict["link_status_nic"]),
                 ('nic_lane1_active', mux_info_dict["nic_lane1_active"]),
                 ('nic_lane2_active', mux_info_dict["nic_lane2_active"]),
                 ('nic_lane3_active', mux_info_dict["nic_lane3_active"]),
                 ('nic_lane4_active', mux_info_dict["nic_lane4_active"]),
                 ('self_eye_height_lane1', str(mux_info_dict["self_eye_height_lane1"])),
                 ('self_eye_height_lane2', str(mux_info_dict["self_eye_height_lane2"])),
                 ('peer_eye_height_lane1', str(mux_info_dict["peer_eye_height_lane1"])),
                 ('peer_eye_height_lane2', str(mux_info_dict["peer_eye_height_lane1"])),
                 ('nic_eye_height_lane1', str(mux_info_dict["nic_eye_height_lane1"])),
                 ('nic_eye_height_lane2', str(mux_info_dict["nic_eye_height_lane2"])),
                 ('internal_temperature', str(mux_info_dict["internal_temperature"])),
                 ('internal_voltage', str(mux_info_dict["internal_voltage"])),
                 ('nic_temperature', str(mux_info_dict["nic_temperature"])),
                 ('nic_voltage', str(mux_info_dict["nic_voltage"])),
                 ('build_slot1_nic', str(mux_info_dict["build_slot1_nic"])),
                 ('build_slot2_nic', str(mux_info_dict["build_slot2_nic"])),
                 ('version_slot1_nic', str(mux_info_dict["version_slot1_nic"])),
                 ('version_slot2_nic', str(mux_info_dict["version_slot2_nic"])),
                 ('run_slot1_nic', str(mux_info_dict["run_slot1_nic"])),
                 ('run_slot2_nic', str(mux_info_dict["run_slot2_nic"])),
                 ('commit_slot1_nic', str(mux_info_dict["commit_slot1_nic"])),
                 ('commit_slot2_nic', str(mux_info_dict["commit_slot2_nic"])),
                 ('empty_slot1_nic', str(mux_info_dict["empty_slot1_nic"])),
                 ('empty_slot2_nic', str(mux_info_dict["empty_slot2_nic"])),
                 ('build_slot1_tor1', str(mux_info_dict["build_slot1_tor1"])),
                 ('build_slot2_tor1', str(mux_info_dict["build_slot2_tor1"])),
                 ('version_slot1_tor1', str(mux_info_dict["version_slot1_tor1"])),
                 ('version_slot2_tor1', str(mux_info_dict["version_slot2_tor1"])),
                 ('run_slot1_tor1', str(mux_info_dict["run_slot1_tor1"])),
                 ('run_slot2_tor1', str(mux_info_dict["run_slot2_tor1"])),
                 ('commit_slot1_tor1', str(mux_info_dict["commit_slot1_tor1"])),
                 ('commit_slot2_tor1', str(mux_info_dict["commit_slot2_tor1"])),
                 ('empty_slot1_tor1', str(mux_info_dict["empty_slot1_tor1"])),
                 ('empty_slot2_tor1', str(mux_info_dict["empty_slot2_tor1"])),
                 ('build_slot1_tor2', str(mux_info_dict["build_slot1_tor2"])),
                 ('build_slot2_tor2', str(mux_info_dict["build_slot2_tor2"])),
                 ('version_slot1_tor2', str(mux_info_dict["version_slot1_tor2"])),
                 ('version_slot2_tor2', str(mux_info_dict["version_slot2_tor2"])),
                 ('run_slot1_tor2', str(mux_info_dict["run_slot1_tor2"])),
                 ('run_slot2_tor2', str(mux_info_dict["run_slot2_tor2"])),
                 ('commit_slot1_tor2', str(mux_info_dict["commit_slot1_tor2"])),
                 ('commit_slot2_tor2', str(mux_info_dict["commit_slot2_tor2"])),
                 ('empty_slot1_tor2', str(mux_info_dict["empty_slot1_tor2"])),
                 ('empty_slot2_tor2', str(mux_info_dict["empty_slot2_tor2"]))
                 ])
            table.set(logical_port_name, fvs)
        else:
            return -1


def post_port_mux_static_info_to_db(logical_port_name, static_table):

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("No physical ports found for logical port '{}'".format(logical_port_name))
        return -1

    if len(physical_port_list) > 1:
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable port {}".format(logical_port_name))
        return -1

    for physical_port in physical_port_list:

        if not _wrapper_get_presence(physical_port):
            continue

        mux_static_info_dict = get_muxcable_static_info(physical_port, logical_port_name)

        if mux_static_info_dict is not None and mux_static_info_dict is not -1:
            #transceiver_dict[physical_port] = port_info_dict
            fvs = swsscommon.FieldValuePairs(
                [('read_side',  mux_static_info_dict["read_side"]),
                 ('nic_lane1_precursor1', str(mux_static_info_dict["nic_lane1_precursor1"])),
                 ('nic_lane1_precursor2', str(mux_static_info_dict["nic_lane1_precursor2"])),
                 ('nic_lane1_maincursor', str(mux_static_info_dict["nic_lane1_maincursor"])),
                 ('nic_lane1_postcursor1', str(mux_static_info_dict["nic_lane1_postcursor1"])),
                 ('nic_lane1_postcursor2', str(mux_static_info_dict["nic_lane1_postcursor2"])),
                 ('nic_lane2_precursor1', str(mux_static_info_dict["nic_lane2_precursor1"])),
                 ('nic_lane2_precursor2', str(mux_static_info_dict["nic_lane2_precursor2"])),
                 ('nic_lane2_maincursor', str(mux_static_info_dict["nic_lane2_maincursor"])),
                 ('nic_lane2_postcursor1', str(mux_static_info_dict["nic_lane2_postcursor1"])),
                 ('nic_lane2_postcursor2', str(mux_static_info_dict["nic_lane2_postcursor2"])),
                 ('tor_self_lane1_precursor1', str(mux_static_info_dict["tor_self_lane1_precursor1"])),
                 ('tor_self_lane1_precursor2', str(mux_static_info_dict["tor_self_lane1_precursor2"])),
                 ('tor_self_lane1_maincursor', str(mux_static_info_dict["tor_self_lane1_maincursor"])),
                 ('tor_self_lane1_postcursor1', str(mux_static_info_dict["tor_self_lane1_postcursor1"])),
                 ('tor_self_lane1_postcursor2', str(mux_static_info_dict["tor_self_lane1_postcursor2"])),
                 ('tor_self_lane2_precursor1', str(mux_static_info_dict["tor_self_lane2_precursor1"])),
                 ('tor_self_lane2_precursor2', str(mux_static_info_dict["tor_self_lane2_precursor2"])),
                 ('tor_self_lane2_maincursor', str(mux_static_info_dict["tor_self_lane2_maincursor"])),
                 ('tor_self_lane2_postcursor1', str(mux_static_info_dict["tor_self_lane2_postcursor1"])),
                 ('tor_self_lane2_postcursor2', str(mux_static_info_dict["tor_self_lane2_postcursor2"])),
                 ('tor_peer_lane1_precursor1', str(mux_static_info_dict["tor_peer_lane1_precursor1"])),
                 ('tor_peer_lane1_precursor2', str(mux_static_info_dict["tor_peer_lane1_precursor2"])),
                 ('tor_peer_lane1_maincursor', str(mux_static_info_dict["tor_peer_lane1_maincursor"])),
                 ('tor_peer_lane1_postcursor1', str(mux_static_info_dict["tor_peer_lane1_postcursor1"])),
                 ('tor_peer_lane1_postcursor2', str(mux_static_info_dict["tor_peer_lane1_postcursor2"])),
                 ('tor_peer_lane2_precursor1', str(mux_static_info_dict["tor_peer_lane2_precursor1"])),
                 ('tor_peer_lane2_precursor2', str(mux_static_info_dict["tor_peer_lane2_precursor2"])),
                 ('tor_peer_lane2_maincursor', str(mux_static_info_dict["tor_peer_lane2_maincursor"])),
                 ('tor_peer_lane2_postcursor1', str(mux_static_info_dict["tor_peer_lane2_postcursor1"])),
                 ('tor_peer_lane2_postcursor2', str(mux_static_info_dict["tor_peer_lane2_postcursor2"]))
                 ])
            static_table.set(logical_port_name, fvs)
        else:
            return -1


def post_mux_static_info_to_db(is_warm_start, stop_event=threading.Event()):
    # Connect to STATE_DB and create transceiver mux/static info tables
    state_db, static_tbl = {}, {}

    # Get the namespaces in the platform
    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
        static_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_STATIC_INFO_TABLE)

    # Post all the current interface dom/sfp info to STATE_DB
    logical_port_list = y_cable_platform_sfputil.logical
    for logical_port_name in logical_port_list:
        if stop_event.is_set():
            break

        # Get the asic to which this port belongs
        asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(logical_port_name)
        if asic_index is None:
            logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
            continue
        post_port_mux_static_info_to_db(logical_port_name, mux_tbl[asic_index])


def post_mux_info_to_db(is_warm_start, stop_event=threading.Event()):
    # Connect to STATE_DB and create transceiver mux/static info tables
    state_db, mux_tbl, static_tbl = {}, {}, {}

    # Get the namespaces in the platform
    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
        mux_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_INFO_TABLE)

    # Post all the current interface dom/sfp info to STATE_DB
    logical_port_list = y_cable_platform_sfputil.logical
    for logical_port_name in logical_port_list:
        if stop_event.is_set():
            break

        # Get the asic to which this port belongs
        asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(logical_port_name)
        if asic_index is None:
            logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
            continue
        post_port_mux_info_to_db(logical_port_name,  mux_tbl[asic_index])


# Thread wrapper class to update y_cable status periodically
class YCableTableUpdateTask(object):
    def __init__(self):
        self.task_thread = None

        if multi_asic.is_multi_asic():
            # Load the namespace details first from the database_global.json file.
            swsscommon.SonicDBConfig.initializeGlobalConfig()

    def task_worker(self):

        # Connect to STATE_DB and APPL_DB and get both the HW_MUX_STATUS_TABLE info
        appl_db, state_db, status_tbl, y_cable_tbl = {}, {}, {}, {}
        y_cable_tbl_keys = {}
        mux_cable_command_tbl, y_cable_command_tbl = {}, {}

        sel = swsscommon.Select()

        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            # Open a handle to the Application database, in all namespaces
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            appl_db[asic_id] = daemon_base.db_connect("APPL_DB", namespace)
            status_tbl[asic_id] = swsscommon.SubscriberStateTable(
                appl_db[asic_id], swsscommon.APP_HW_MUX_CABLE_TABLE_NAME)
            mux_cable_command_tbl[asic_id] = swsscommon.SubscriberStateTable(
                appl_db[asic_id], swsscommon.APP_MUX_CABLE_COMMAND_TABLE_NAME)
            y_cable_command_tbl[asic_id] = swsscommon.Table(
                appl_db[asic_id], swsscommon.APP_MUX_CABLE_COMMAND_TABLE_NAME)
            state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            y_cable_tbl[asic_id] = swsscommon.Table(
                state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            y_cable_tbl_keys[asic_id] = y_cable_tbl[asic_id].getKeys()
            sel.addSelectable(status_tbl[asic_id])
            sel.addSelectable(mux_cable_command_tbl[asic_id])

        # Listen indefinitely for changes to the HW_MUX_CABLE_TABLE in the Application DB's
        while True:
            # Use timeout to prevent ignoring the signals we want to handle
            # in signal_handler() (e.g. SIGTERM for graceful shutdown)

            # A brief sleep appears necessary in this loop or any spawned
            # update threads will get stuck. Appears to be due to the sel.select() call.
            # TODO: Eliminate the need for this sleep.
            time.sleep(0.1)

            (state, selectableObj) = sel.select(SELECT_TIMEOUT)

            if state == swsscommon.Select.TIMEOUT:
                # Do not flood log when select times out
                continue
            if state != swsscommon.Select.OBJECT:
                helper_logger.log_warning(
                    "sel.select() did not  return swsscommon.Select.OBJECT for sonic_y_cable updates")
                continue

            # Get the redisselect object  from selectable object
            redisSelectObj = swsscommon.CastSelectableToRedisSelectObj(
                selectableObj)
            # Get the corresponding namespace from redisselect db connector object
            namespace = redisSelectObj.getDbConnector().getNamespace()
            asic_index = multi_asic.get_asic_index_from_namespace(namespace)

            (port, op, fvp) = status_tbl[asic_index].pop()
            if fvp:
                # This check might be redundant, to check, the presence of this Port in keys
                # in logical_port_list but keep for now for coherency
                # also skip checking in logical_port_list inside sfp_util
                if port not in y_cable_tbl_keys[asic_index]:
                    continue

                fvp_dict = dict(fvp)

                if "state" in fvp_dict:
                    # got a state change
                    new_status = fvp_dict["state"]
                    (status, fvs) = y_cable_tbl[asic_index].get(port)
                    if status is False:
                        helper_logger.log_warning("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
                            port, y_cable_tbl[asic_index]))
                        continue
                    mux_port_dict = dict(fvs)
                    old_status = mux_port_dict.get("state")
                    read_side = mux_port_dict.get("read_side")
                    prev_active_side = mux_port_dict.get("active_side")
                    # Now if the old_status does not match new_status toggle the mux appropriately
                    if old_status != new_status:
                        active_side = update_tor_active_side(
                            read_side, new_status, port)
                        if active_side == -1:
                            new_status = 'unknown'

                        fvs_updated = swsscommon.FieldValuePairs([('state', new_status),
                                                                  ('read_side',
                                                                   read_side),
                                                                  ('active_side', str(active_side))])
                        y_cable_tbl[asic_index].set(port, fvs_updated)
                    else:
                        # nothing to do since no status change
                        active_side = prev_active_side
                        fvs_updated = swsscommon.FieldValuePairs([('state', new_status),
                                                                  ('read_side',
                                                                   read_side),
                                                                  ('active_side', str(active_side))])
                        y_cable_tbl[asic_index].set(port, fvs_updated)
                        helper_logger.log_warning("Got a change event on that does not toggle the TOR active side for port  {} status {} active linked side = {} ".format(
                            port, old_status, prev_active_side))
                else:
                    helper_logger.log_info("Got a change event on port {} of table {} that does not contain status ".format(
                        port, swsscommon.APP_HW_MUX_CABLE_TABLE_NAME))

            (port_m, op_m, fvp_m) = mux_cable_command_tbl[asic_index].pop()
            if fvp_m:

                if port_m not in y_cable_tbl_keys[asic_index]:
                    continue

                fvp_dict = dict(fvp_m)

                if "command" in fvp_dict:
                    # check if xcvrd got a probe command
                    probe_identifier = fvp_dict["command"]

                    if probe_identifier == "probe":
                        (status, fv) = y_cable_tbl[asic_index].get(port_m)
                        if status is False:
                            helper_logger.log_warning("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
                                port_m, y_cable_tbl[asic_index]))
                            continue
                        mux_port_dict = dict(fv)
                        read_side = mux_port_dict.get("read_side")
                        update_appdb_port_mux_cable_response_table(port_m, asic_index, appl_db, int(read_side))

    def task_run(self):
        self.task_thread = threading.Thread(target=self.task_worker)
        self.task_thread.start()

    def task_stop(self):
        self.task_thread.join()
