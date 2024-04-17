from sonic_py_common import daemon_base
from sonic_py_common import multi_asic
from swsscommon import swsscommon

SELECT_TIMEOUT_MSECS = 1000
DEFAULT_PORT_TBL_MAP = [
    {'CONFIG_DB': swsscommon.CFG_PORT_TABLE_NAME},
    {'STATE_DB': 'TRANSCEIVER_INFO'},
    {'STATE_DB': 'PORT_TABLE', 'FILTER': ['host_tx_ready']},
]

class PortChangeEvent:
    PORT_ADD = 0
    PORT_REMOVE = 1
    PORT_SET = 2
    PORT_DEL = 3

    def __init__(self, port_name, port_index, asic_id, event_type, port_dict=None,
                 db_name=None, table_name=None):
        # Logical port name, e.g. Ethernet0
        self.port_name = port_name
        # Physical port index, equals to "index" field of PORT table in CONFIG_DB
        self.port_index = int(port_index)
        # ASIC ID, for multi ASIC
        self.asic_id = asic_id
        # Port change event type
        self.event_type = event_type
        # Port config dict
        self.port_dict = port_dict
        self.db_name = db_name
        self.table_name = table_name

    def __str__(self):
        return '{} - name={} index={} asic_id={}'.format('Add' if self.event_type == self.PORT_ADD else 'Remove',
                                                         self.port_name,
                                                         self.port_index,
                                                         self.asic_id)

class PortChangeObserver:
    """
    PortChangeObserver is a class to monitor port change events in DBs, and
    notify callback function
    """

    def __init__(self, namespaces, logger,
                 stop_event,
                 port_change_event_handler,
                 port_tbl_map=DEFAULT_PORT_TBL_MAP):
        """
        Args:
            namespaces (list): List of namespaces to monitor
            logger (Logger): Logger object
            stop_event (threading.Event): Stop event to stop the observer
            port_change_event_handler (function): Callback function to handle port change event
            port_tbl_map (list): List of dictionaries, each dictionary contains
            the DB name and table name to monitor
        """
        # To avoid duplicate event processing, this dict stores the latest port
        # change event for each key which is a tuple of
        # (port_name, port_tbl.db_name, port_tbl.table_name)
        self.port_event_cache = {}
        self.namespaces = namespaces
        self.logger = logger
        self.stop_event = stop_event
        self.port_change_event_handler = port_change_event_handler
        self.port_tbl_map = port_tbl_map
        self.port_role_map = {}
        self.refresh_role_map()
        self.subscribe_port_update_event()

    def apply_filter_to_fvp(self, filter, fvp):
        if filter is not None:
            for key in fvp.copy().keys():
                if key not in (set(filter) | set({'index', 'port_name', 'asic_id', 'op'})):
                    del fvp[key]

    def refresh_role_map(self):
        for ns in self.namespaces:
            cfg_db = daemon_base.db_connect("CONFIG_DB", namespace=ns)
            port_table = swsscommon.Table(cfg_db, swsscommon.CFG_PORT_TABLE_NAME)
            for key in port_table.getKeys():
                _, port_config = port_table.get(key)
                port_config_dict = dict(port_config)
                if port_config_dict.get(multi_asic.PORT_ROLE, None):
                    self.port_role_map[key] =  port_config_dict[multi_asic.PORT_ROLE]

    def subscribe_port_update_event(self):
        """
           Subscribe to a particular DB's table and listen to only interested fields
           Format :
              { <DB name> : <Table name> , <field1>, <field2>, .. } where only field<n> update will be received
        """
        sel = swsscommon.Select()
        asic_context = {}
        for d in self.port_tbl_map:
            for namespace in self.namespaces:
                db = daemon_base.db_connect(list(d.keys())[0], namespace=namespace)
                asic_id = multi_asic.get_asic_index_from_namespace(namespace)
                port_tbl = swsscommon.SubscriberStateTable(db, list(d.values())[0])
                port_tbl.db_name = list(d.keys())[0]
                port_tbl.table_name = list(d.values())[0]
                port_tbl.filter = d['FILTER'] if 'FILTER' in d else None
                asic_context[port_tbl] = asic_id
                sel.addSelectable(port_tbl)
                self.logger.log_warning("subscribing to port_tbl {} - {} DB of namespace {} ".format(
                                            port_tbl, list(d.values())[0], namespace))
        self.sel, self.asic_context = sel, asic_context

    def handle_port_update_event(self):
        """
        Select PORT update events, notify the observers upon a port update in CONFIG_DB
        or a XCVR insertion/removal in STATE_DB

        Returns:
            bool: True if there's at least one update event; False if there's no update event.
        """
        has_event = False
        if not self.stop_event.is_set():
            (state, _) = self.sel.select(SELECT_TIMEOUT_MSECS)
            if state == swsscommon.Select.TIMEOUT:
                return has_event
            if state != swsscommon.Select.OBJECT:
                self.logger.log_warning('sel.select() did not return swsscommon.Select.OBJECT')
                return has_event

            port_event_cache = {}
            for port_tbl in self.asic_context.keys():
                while True:
                    (port_name, op, fvp) = port_tbl.pop()
                    if not port_name:
                        break
 
                    fvp = dict(fvp) if fvp is not None else {}
                    role = fvp.get(multi_asic.PORT_ROLE, None)
                    if role:
                        # If an internal port is broken out on the fly using DPB,
                        # the assumption here is that we would recieve CONFIG_DB or APPL_DB notification before STATE_DB
                        self.port_role_map[port_name] = role
                    else:
                        # role attribute might not be present for state DB
                        # notifs and thus need to maintain a cache
                        role = self.port_role_map.get(port_name, None)

                    if not multi_asic.is_front_panel_port(port_name, role):
                        continue

                    self.logger.log_warning("$$$ {} handle_port_update_event() : op={} DB:{} Table:{} fvp {}".format(
                                                            port_name, op, port_tbl.db_name, port_tbl.table_name, fvp))
                    if 'index' not in fvp:
                       fvp['index'] = '-1'
                    fvp['port_name'] = port_name
                    fvp['asic_id'] = self.asic_context[port_tbl]
                    fvp['op'] = op
                    fvp['FILTER'] = port_tbl.filter
                    # Soak duplicate events and consider only the last event
                    port_event_cache[(port_name, port_tbl.db_name, port_tbl.table_name)] = fvp

            # Now apply filter over soaked events
            for key, fvp in port_event_cache.items():
                db_name = key[1]
                table_name = key[2]
                port_index = int(fvp['index'])
                port_change_event = None
                filter = fvp['FILTER']
                del fvp['FILTER']
                self.apply_filter_to_fvp(filter, fvp)

                if key in self.port_event_cache:
                    # Compare current event with last event on this key, to see if
                    # there's really a need to update.
                    diff = set(fvp.items()) - set(self.port_event_cache[key].items())
                    # Ignore duplicate events
                    if not diff:
                       self.port_event_cache[key] = fvp
                       continue
                # Update the latest event to the cache
                self.port_event_cache[key] = fvp

                if fvp['op'] == swsscommon.SET_COMMAND:
                   port_change_event = PortChangeEvent(fvp['port_name'],
                                                            port_index,
                                                            fvp['asic_id'],
                                                            PortChangeEvent.PORT_SET,
                                                            fvp,
                                                            db_name,
                                                            table_name)
                elif fvp['op'] == swsscommon.DEL_COMMAND:
                   port_change_event = PortChangeEvent(fvp['port_name'],
                                                            port_index,
                                                            fvp['asic_id'],
                                                            PortChangeEvent.PORT_DEL,
                                                            fvp,
                                                            db_name,
                                                            table_name)
                # This is the final event considered for processing
                self.logger.log_warning("*** {} handle_port_update_event() fvp {}".format(
                    key, fvp))
                if port_change_event is not None:
                    has_event = True
                    self.port_change_event_handler(port_change_event)

        return has_event


class PortMapping:
    def __init__(self):
        # A list of logical port name, e.g. ["Ethernet0", "Ethernet4" ...]
        self.logical_port_list = []
        # Logical port name to physical port index mapping
        self.logical_to_physical = {}
        # Physical port index to logical port name mapping
        self.physical_to_logical = {}
        # Logical port name to ASIC ID mapping
        self.logical_to_asic = {}

    def handle_port_change_event(self, port_change_event):
        if port_change_event.event_type == PortChangeEvent.PORT_ADD:
            self._handle_port_add(port_change_event)
        elif port_change_event.event_type == PortChangeEvent.PORT_REMOVE:
            self._handle_port_remove(port_change_event)

    def _handle_port_add(self, port_change_event):
        port_name = port_change_event.port_name
        self.logical_port_list.append(port_name)
        self.logical_to_physical[port_name] = port_change_event.port_index
        if port_change_event.port_index not in self.physical_to_logical:
            self.physical_to_logical[port_change_event.port_index] = [port_name]
        else:
            self.physical_to_logical[port_change_event.port_index].append(port_name)
        self.logical_to_asic[port_name] = port_change_event.asic_id

    def _handle_port_remove(self, port_change_event):
        port_name = port_change_event.port_name
        self.logical_port_list.remove(port_name)
        self.logical_to_physical.pop(port_name)
        self.physical_to_logical[port_change_event.port_index].remove(port_name)
        if not self.physical_to_logical[port_change_event.port_index]:
            self.physical_to_logical.pop(port_change_event.port_index)
        self.logical_to_asic.pop(port_name)

    def get_asic_id_for_logical_port(self, port_name):
        return self.logical_to_asic.get(port_name)

    def is_logical_port(self, port_name):
        return port_name in self.logical_to_physical

    def get_logical_to_physical(self, port_name):
        port_index = self.logical_to_physical.get(port_name)
        return None if port_index is None else [port_index]

    def get_physical_to_logical(self, physical_port: int):
        assert isinstance(physical_port, int), "{} is NOT integer".format(physical_port)
        return self.physical_to_logical.get(physical_port)

    def logical_port_name_to_physical_port_list(self, port_name):
        try:
            return [int(port_name)]
        except ValueError:
            if self.is_logical_port(port_name):
                return self.get_logical_to_physical(port_name)
            else:
                return None

def subscribe_port_config_change(namespaces):
    sel = swsscommon.Select()
    asic_context = {}
    for namespace in namespaces:
        config_db = daemon_base.db_connect("CONFIG_DB", namespace=namespace)
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        port_tbl = swsscommon.SubscriberStateTable(config_db, swsscommon.CFG_PORT_TABLE_NAME)
        asic_context[port_tbl] = asic_id
        sel.addSelectable(port_tbl)
    return sel, asic_context

def handle_port_config_change(sel, asic_context, stop_event, port_mapping, logger, port_change_event_handler):
    """Select CONFIG_DB PORT table changes, once there is a port configuration add/remove, notify observers
    """
    if not stop_event.is_set():
        (state, _) = sel.select(SELECT_TIMEOUT_MSECS)
        if state == swsscommon.Select.TIMEOUT:
            return
        if state != swsscommon.Select.OBJECT:
            logger.log_warning('sel.select() did not return swsscommon.Select.OBJECT')
            return

        read_port_config_change(asic_context, port_mapping, logger, port_change_event_handler)

def read_port_config_change(asic_context, port_mapping, logger, port_change_event_handler):
    for port_tbl in asic_context.keys():
        while True:
            (key, op, fvp) = port_tbl.pop()
            if not key:
                break
            fvp = dict(fvp)
            if not multi_asic.is_front_panel_port(key, fvp.get(multi_asic.PORT_ROLE, None)):
                continue
            if op == swsscommon.SET_COMMAND:
                if 'index' not in fvp:
                    continue

                new_physical_index = int(fvp['index'])
                if not port_mapping.is_logical_port(key):
                    # New logical port created
                    port_change_event = PortChangeEvent(key, new_physical_index, asic_context[port_tbl], PortChangeEvent.PORT_ADD)
                    port_change_event_handler(port_change_event)
                else:
                    current_physical_index = port_mapping.get_logical_to_physical(key)[0]
                    if current_physical_index != new_physical_index:
                        port_change_event = PortChangeEvent(key,
                                                            current_physical_index,
                                                            asic_context[port_tbl],
                                                            PortChangeEvent.PORT_REMOVE)
                        port_change_event_handler(port_change_event)

                        port_change_event = PortChangeEvent(key, new_physical_index, asic_context[port_tbl], PortChangeEvent.PORT_ADD)
                        port_change_event_handler(port_change_event)
            elif op == swsscommon.DEL_COMMAND:
                if port_mapping.is_logical_port(key):
                    port_change_event = PortChangeEvent(key,
                                                        port_mapping.get_logical_to_physical(key)[0],
                                                        asic_context[port_tbl],
                                                        PortChangeEvent.PORT_REMOVE)
                    port_change_event_handler(port_change_event)
            else:
                logger.log_warning('Invalid DB operation: {}'.format(op))

def get_port_mapping(namespaces):
    """Get port mapping from CONFIG_DB
    """
    port_mapping = PortMapping()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        config_db = daemon_base.db_connect("CONFIG_DB", namespace=namespace)
        port_table = swsscommon.Table(config_db, swsscommon.CFG_PORT_TABLE_NAME)
        for key in port_table.getKeys():
            _, port_config = port_table.get(key)
            port_config_dict = dict(port_config)
            if not multi_asic.is_front_panel_port(key, port_config_dict.get(multi_asic.PORT_ROLE, None)):
                continue
            port_change_event = PortChangeEvent(key, port_config_dict['index'], asic_id, PortChangeEvent.PORT_ADD)
            port_mapping.handle_port_change_event(port_change_event)
    return port_mapping
