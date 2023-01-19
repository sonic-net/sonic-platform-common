from sonic_py_common import daemon_base
from sonic_py_common import multi_asic
from sonic_py_common.interface import backplane_prefix, inband_prefix, recirc_prefix
from swsscommon import swsscommon

SELECT_TIMEOUT_MSECS = 1000


class PortChangeEvent:
    PORT_ADD = 0
    PORT_REMOVE = 1
    PORT_SET = 2
    PORT_DEL = 3
    PORT_EVENT = {}

    def __init__(self, port_name, port_index, asic_id, event_type, port_dict=None):
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

    def __str__(self):
        return '{} - name={} index={} asic_id={}'.format('Add' if self.event_type == self.PORT_ADD else 'Remove',
                                                         self.port_name,
                                                         self.port_index,
                                                         self.asic_id)


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

def validate_port(port):
    if port.startswith((backplane_prefix(), inband_prefix(), recirc_prefix())):
        return False
    return True

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

def subscribe_port_update_event(namespaces, logger):
    """
       Subscribe to a particular DB's table and listen to only interested fields
       Format :
          { <DB name> : <Table name> , <field1>, <field2>, .. } where only field<n> update will be received
    """
    port_tbl_map = [
        {'CONFIG_DB': swsscommon.CFG_PORT_TABLE_NAME},
        {'STATE_DB': 'TRANSCEIVER_INFO'},
        {'STATE_DB': 'PORT_TABLE', 'FILTER': ['host_tx_ready']},
    ]

    sel = swsscommon.Select()
    asic_context = {}
    for d in port_tbl_map:
        for namespace in namespaces:
            db = daemon_base.db_connect(list(d.keys())[0], namespace=namespace)
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            port_tbl = swsscommon.SubscriberStateTable(db, list(d.values())[0])
            port_tbl.db_name = list(d.keys())[0]
            port_tbl.table_name = list(d.values())[0]
            port_tbl.filter = d['FILTER'] if 'FILTER' in d else None
            asic_context[port_tbl] = asic_id
            sel.addSelectable(port_tbl)
            logger.log_warning("subscribing to port_tbl {} - {} DB of namespace {} ".format(
                                        port_tbl, list(d.values())[0], namespace))
    return sel, asic_context

def apply_filter_to_fvp(filter, fvp):
    if filter is not None:
        for key in fvp.copy().keys():
            if key not in (set(filter) | set({'index', 'key', 'asic_id', 'op'})):
                del fvp[key]

def handle_port_update_event(sel, asic_context, stop_event, logger, port_change_event_handler):
    """
    Select PORT update events, notify the observers upon a port update in CONFIG_DB
    or a XCVR insertion/removal in STATE_DB
    """
    if not stop_event.is_set():
        (state, _) = sel.select(SELECT_TIMEOUT_MSECS)
        if state == swsscommon.Select.TIMEOUT:
            return
        if state != swsscommon.Select.OBJECT:
            logger.log_warning('sel.select() did not return swsscommon.Select.OBJECT')
            return

        port_event_cache = {}
        for port_tbl in asic_context.keys():
            while True:
                (key, op, fvp) = port_tbl.pop()
                if not key:
                    break
                if not validate_port(key):
                    continue
                fvp = dict(fvp) if fvp is not None else {}
                logger.log_warning("$$$ {} handle_port_update_event() : op={} DB:{} Table:{} fvp {}".format(
                                                        key, op, port_tbl.db_name, port_tbl.table_name, fvp))

                if 'index' not in fvp:
                   fvp['index'] = '-1'
                fvp['key'] = key
                fvp['asic_id'] = asic_context[port_tbl]
                fvp['op'] = op
                fvp['FILTER'] = port_tbl.filter
                # Soak duplicate events and consider only the last event
                port_event_cache[key+port_tbl.db_name+port_tbl.table_name] = fvp

        # Now apply filter over soaked events
        for key, fvp in port_event_cache.items():
            port_index = int(fvp['index'])
            port_change_event = None
            diff = {}
            filter = fvp['FILTER']
            del fvp['FILTER']
            apply_filter_to_fvp(filter, fvp)

            if key in PortChangeEvent.PORT_EVENT:
               diff = dict(set(fvp.items()) - set(PortChangeEvent.PORT_EVENT[key].items()))
               # Ignore duplicate events
               if not diff:
                  PortChangeEvent.PORT_EVENT[key] = fvp
                  continue
            PortChangeEvent.PORT_EVENT[key] = fvp

            if fvp['op'] == swsscommon.SET_COMMAND:
               port_change_event = PortChangeEvent(fvp['key'],
                                                        port_index,
                                                        fvp['asic_id'],
                                                        PortChangeEvent.PORT_SET,
                                                        fvp)
            elif fvp['op'] == swsscommon.DEL_COMMAND:
               port_change_event = PortChangeEvent(fvp['key'],
                                                        port_index,
                                                        fvp['asic_id'],
                                                        PortChangeEvent.PORT_DEL,
                                                        fvp)
            # This is the final event considered for processing
            logger.log_warning("*** {} handle_port_update_event() fvp {}".format(
                key, fvp))
            if port_change_event is not None:
               port_change_event_handler(port_change_event)


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
            if not validate_port(key):
                continue
            if op == swsscommon.SET_COMMAND:
                fvp = dict(fvp)
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
            if not validate_port(key):
                continue
            _, port_config = port_table.get(key)
            port_config_dict = dict(port_config)
            port_change_event = PortChangeEvent(key, port_config_dict['index'], asic_id, PortChangeEvent.PORT_ADD)
            port_mapping.handle_port_change_event(port_change_event)
    return port_mapping
