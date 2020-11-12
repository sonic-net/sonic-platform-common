"""
    y_cable_helper.py
    helper utlities configuring y_cable for xcvrd daemon
"""

try:
    import threading

    from sonic_py_common import daemon_base, logger
    from sonic_py_common import multi_asic
    from sonic_y_cable import y_cable
    from swsscommon import swsscommon
except ImportError, e:
    raise ImportError(str(e) + " - required module not found")


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
    y_cable_tbl._del(logical_port_name)


def update_tor_active_side(read_side, status, logical_port_name):
    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if int(read_side) == 1:
            if status == "active":
                y_cable.toggle_mux_to_torA(physical_port)
                return 1
            elif status == "standby":
                y_cable.toggle_mux_to_torB(physical_port)
                return 2
        elif int(read_side) == 2:
            if status == "active":
                y_cable.toggle_mux_to_torB(physical_port)
                return 2
            elif status == "standby":
                y_cable.toggle_mux_to_torA(physical_port)
                return 1

        # TODO: Should we confirm that the mux was indeed toggled?
    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable table".format(logical_port_name))
        return -1


def update_appdb_port_mux_cable_response_table(logical_port_name, asic_index, appl_db):
    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if _wrapper_get_presence(physical_port):
            status = None
            y_cable_response_tbl = {}
            read_side = y_cable.check_read_side(physical_port)
            y_cable_response_tbl[asic_index] = swsscommon.Table(
                appl_db[asic_index], swsscommon.APP_MUX_CABLE_RESPONSE_TABLE_NAME)

            if not read_side:
                status = 'failure'

                fvs = swsscommon.FieldValuePairs([('status', status)])
                y_cable_response_tbl[asic_index].set(logical_port_name, fvs)

                helper_logger.log_warning(
                    "Error: Could not get read side for mux cable port probe failed {}".format(logical_port_name))
                return

            active_side = y_cable.check_active_linked_tor_side(physical_port)
            if not active_side:
                status = 'failure'

                fvs = swsscommon.FieldValuePairs([('status', status)])
                y_cable_response_tbl[asic_index].set(logical_port_name, fvs)

                helper_logger.log_warning(
                    "Error: Could not get active side for mux cable port probe failed {}".format(logical_port_name))
                return

            if read_side == active_side and (active_side == 1 or active_side == 2):
                status = 'active'
            elif read_side != active_side and (active_side == 1 or active_side == 2):
                status = 'standby'
            else:
                status = 'inactive'


            fvs = swsscommon.FieldValuePairs([('status', status)])

            y_cable_response_tbl[asic_index].set(logical_port_name, fvs)
        else:
            helper_logger.log_warning(
                "Error: Could not establish presence for  Y cable port {}".format(logical_port_name))
    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable port {}".format(logical_port_name))

def update_statedb_port_mux_status_table(logical_port_name, mux_config_tbl):
    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if _wrapper_get_presence(physical_port):
            read_side = y_cable.check_read_side(physical_port)
            active_side = y_cable.check_active_linked_tor_side(physical_port)
            if read_side == active_side:
                status = 'active'
            elif active_side == 0:
                status = 'inactive'
            else:
                status = 'standby'

            fvs = swsscommon.FieldValuePairs([('status', status),
                                              ('read_side', str(read_side)),
                                              ('active_side', str(active_side))])
            mux_config_tbl.set(logical_port_name, fvs)
        else:
            helper_logger.log_warning(
                "Error: Could not establish presence for  Y cable port {}".format(logical_port_name))
    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable port {}".format(logical_port_name))


def check_identifier_presence_and_update_mux_table_entry(state_db, port_tbl, y_cable_tbl, asic_index, logical_port_name, y_cable_presence):

    (status, fvs) = port_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_warning(
            "Could not retreive fieldvalue pairs for {}, inside config_db".format(logical_port_name))
        return

    else:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "mux_cable" in mux_table_dict:
            y_cable_asic_table = y_cable_tbl.get(asic_index, None)
            if y_cable_presence[0] is True and y_cable_asic_table is not None:
                # fill in the newly found entry
                update_statedb_port_mux_status_table(
                    logical_port_name, y_cable_tbl[asic_index])

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
                # fill the newly found entry
                update_statedb_port_mux_status_table(
                    logical_port_name, y_cable_tbl[asic_index])


def check_identifier_presence_and_delete_mux_table_entry(state_db, port_tbl, asic_index, logical_port_name, y_cable_presence, delete_change_event):

    y_cable_tbl = {}

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
                # fill the newly found entry
                delete_port_from_y_cable_table(
                    logical_port_name, y_cable_tbl[asic_index])
                delete_change_event[:] = [True]


def init_ports_status_for_y_cable(platform_sfp, platform_chassis, y_cable_presence, stop_event=threading.Event()):
    global y_cable_platform_sfputil
    global y_cable_platform_chassis
    # Connect to CONFIG_DB and create port status table inside state_db
    config_db, state_db, port_tbl, y_cable_tbl = {}, {}, {}, {}
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
                state_db, port_tbl, y_cable_tbl, asic_index, logical_port_name, y_cable_presence)
        else:
            # This port does not exist in Port table of config but is present inside
            # logical_ports after loading the port_mappings from port_config_file
            # This should not happen
            helper_logger.log_warning(
                "Could not retreive port inside config_db PORT table ".format(logical_port_name))


def change_ports_status_for_y_cable_change_event(port_dict, y_cable_presence, stop_event=threading.Event()):
    # Connect to CONFIG_DB and create port status table inside state_db
    config_db, state_db, port_tbl, y_cable_tbl = {}, {}, {}, {}
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
    for key, value in port_dict.iteritems():
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
                        state_db, port_tbl, y_cable_tbl, asic_index, logical_port_name, y_cable_presence)
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
    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
        y_cable_tbl[asic_id] = swsscommon.Table(
            state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        y_cable_tbl_keys[asic_id] = y_cable_tbl[asic_id].getKeys()

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


# Thread wrapper class to update y_cable status periodically
class YCableTableUpdateTask(object):
    def __init__(self):
        self.task_thread = None

        # Load the namespace details first from the database_global.json file.
        swsscommon.SonicDBConfig.initializeGlobalConfig()

    def task_worker(self):

        # Connect to STATE_DB and APPL_DB and get both the HW_MUX_STATUS_TABLE info
        appl_db, state_db, status_tbl, y_cable_tbl = {}, {}, {}, {}
        y_cable_tbl_keys = {}
        mux_cable_command_tbl = {}

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

                if "status" in fvp_dict:
                    # got a status change
                    new_status = fvp_dict["status"]
                    (status, fvs) = y_cable_tbl[asic_index].get(port)
                    if status is False:
                        helper_logger.log_warning("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
                            port, y_cable_tbl[asic_index]))
                        continue
                    mux_port_dict = dict(fvs)
                    old_status = mux_port_dict.get("status")
                    read_side = mux_port_dict.get("read_side")
                    prev_active_side = mux_port_dict.get("active_side")
                    # Now if the old_status does not match new_status toggle the mux appropriately
                    if old_status != new_status:
                        active_side = update_tor_active_side(
                            read_side, new_status, port)
                        fvs_updated = swsscommon.FieldValuePairs([('status', new_status),
                                                                  ('read_side',
                                                                   read_side),
                                                                  ('active_side', str(active_side))])
                        y_cable_tbl[asic_index].set(port, fvs_updated)
                        # nothing to do since no status change
                    else:
                        helper_logger.log_warning("Got a change event on that does not toggle the TOR active side for port  {} status {} active linked side = {} ".format(
                            port, old_status, prev_active_side))
                else:
                    helper_logger.log_info("Got a change event on port {} of table {} that does not contain status ".format(
                        port, swsscommon.APP_HW_MUX_CABLE_TABLE_NAME))

            (port_m, op_m, fvp_m) = mux_cable_command_tbl[asic_index].pop()
            if fvp_m:

                fvp_dict = dict(fvp_m)

                if "command" in fvp_dict:
                    #check if xcvrd got a probe command
                    probe_identifier = fvp_dict["command"]

                    if probe_identifier == "probe":
                        update_appdb_port_mux_cable_response_table(port_m, asic_index, appl_db)

    def task_run(self):
        self.task_thread = threading.Thread(target=self.task_worker)
        self.task_thread.start()

    def task_stop(self):
        self.task_thread.join()
