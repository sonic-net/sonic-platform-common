"""
    SFF task manager
    Deterministic link bring-up task manager for SFF compliant modules, running
    as a thread inside xcvrd
"""

try:
    import copy
    import sys
    import threading
    import traceback

    from swsscommon import swsscommon

    from .xcvrd_utilities.port_event_helper import PortChangeObserver
    from .xcvrd_utilities.xcvr_table_helper import XcvrTableHelper
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


class SffLoggerForPortUpdateEvent:
    SFF_LOGGER_PREFIX = "SFF-PORT-UPDATE: "

    def __init__(self, logger):
        self.logger = logger

    def log_notice(self, message):
        self.logger.log_notice("{}{}".format(self.SFF_LOGGER_PREFIX, message))

    def log_warning(self, message):
        self.logger.log_warning("{}{}".format(self.SFF_LOGGER_PREFIX, message))

    def log_error(self, message):
        self.logger.log_error("{}{}".format(self.SFF_LOGGER_PREFIX, message))

# Thread wrapper class for SFF compliant transceiver management
class SffManagerTask(threading.Thread):

    # CONFIG_DB port table fields:

    ADMIN_STATUS = 'admin_status'
    # This is the subport index for this logical port, starting from 1, 0 means
    # all lanes are taken.
    SUBPORT = 'subport'
    # This is a comma separated list of lane numbers
    LANES_LIST = 'lanes'


    # STATE_DB TRANSCEIVER_INFO table fields:

    # This filed can used to determine insertion/removal event. Since
    # TRANSCEIVER_INFO has the same life cycle as a transceiver, if transceiver
    # is inserted/removed, TRANSCEIVER_INFO is also created/deleted.
    XCVR_TYPE = 'type'


    # STATE_DB PORT_TABLE fields:

    HOST_TX_READY = 'host_tx_ready'

    # Default number of lanes per physical port for QSFP28/QSFP+ transceiver
    DEFAULT_NUM_LANES_PER_PPORT = 4

    # Subscribe to below tables in Redis DB
    PORT_TBL_MAP = [
        {
            'CONFIG_DB': swsscommon.CFG_PORT_TABLE_NAME
        },
        {
            'STATE_DB': 'TRANSCEIVER_INFO',
            'FILTER': [XCVR_TYPE]
        },
        {
            'STATE_DB': 'PORT_TABLE',
            'FILTER': [HOST_TX_READY] # This also filters out unwanted 'admin_status' from STATE_DB.
        },
    ]

    SFF_LOGGER_PREFIX = "SFF-MAIN: "

    def __init__(self, namespaces, main_thread_stop_event, platform_chassis, helper_logger):
        threading.Thread.__init__(self)
        self.name = "SffManagerTask"
        self.exc = None
        self.task_stopping_event = threading.Event()
        self.main_thread_stop_event = main_thread_stop_event
        self.helper_logger = helper_logger
        self.logger_for_port_update_event = SffLoggerForPortUpdateEvent(helper_logger)
        self.platform_chassis = platform_chassis
        # port_dict holds data obtained from on_port_update_event per port entry
        # with logical_port_name as key.
        # Its port entry will get deleted upon CONFIG_DB PORT_TABLE DEL.
        self.port_dict = {}
        # port_dict snapshot captured in the previous event update loop
        self.port_dict_prev = {}
        self.xcvr_table_helper = XcvrTableHelper(namespaces)
        self.namespaces = namespaces

    def log_notice(self, message):
        self.helper_logger.log_notice("{}{}".format(self.SFF_LOGGER_PREFIX, message))

    def log_warning(self, message):
        self.helper_logger.log_warning("{}{}".format(self.SFF_LOGGER_PREFIX, message))

    def log_error(self, message):
        self.helper_logger.log_error("{}{}".format(self.SFF_LOGGER_PREFIX, message))

    def get_active_lanes_for_lport(self, lport, subport_idx, num_lanes_per_lport, num_lanes_per_pport):
        """
        Get the active lanes for a logical port based on the subport index.

        Args:
            lport (str): Logical port name.
            subport_idx (int): Subport index, starting from 1. 0 means all lanes are taken.
            num_lanes_per_lport (int): Number of lanes per logical port.
            num_lanes_per_pport (int): Number of lanes per physical port.

        Returns:
            list: A list of boolean values, where True means the corresponding
                  lane belongs to this logical port. For example, [True, True,
                  False, False] means the first two lanes on this physical port
                  belong to this logical port.
        """
        if subport_idx < 0 or subport_idx > num_lanes_per_pport // num_lanes_per_lport:
            self.log_error(
                "{}: Invalid subport_idx {} "
                "for num_lanes_per_lport={}, "
                "num_lanes_per_pport={}".format(lport,
                                                subport_idx,
                                                num_lanes_per_lport,
                                                num_lanes_per_pport)
            )
            return None

        if subport_idx == 0:
            lanes = [True] * num_lanes_per_pport
        else:
            lanes = [False] * num_lanes_per_pport
            start = (subport_idx - 1) * num_lanes_per_lport
            end = subport_idx * num_lanes_per_lport
            lanes[start:end] = [True] * (end - start)

        return lanes

    def on_port_update_event(self, port_change_event):
        if (port_change_event.event_type
                not in [port_change_event.PORT_SET, port_change_event.PORT_DEL]):
            return

        lport = port_change_event.port_name
        pport = port_change_event.port_index
        asic_id = port_change_event.asic_id

        # Skip if it's not a physical port
        if not lport.startswith('Ethernet'):
            return

        # Skip if the physical index is not available
        if pport is None:
            return

        if port_change_event.port_dict is None:
            return

        if port_change_event.event_type == port_change_event.PORT_SET:
            if lport not in self.port_dict:
                self.port_dict[lport] = {}
            if pport >= 0:
                self.port_dict[lport]['index'] = pport

            if self.SUBPORT in port_change_event.port_dict:
                self.port_dict[lport][self.SUBPORT] = port_change_event.port_dict[self.SUBPORT]

            if self.LANES_LIST in port_change_event.port_dict:
                self.port_dict[lport][self.LANES_LIST] = \
                    port_change_event.port_dict[self.LANES_LIST].split(',')

            if self.HOST_TX_READY in port_change_event.port_dict:
                self.port_dict[lport][self.HOST_TX_READY] = \
                        port_change_event.port_dict[self.HOST_TX_READY]

            if self.ADMIN_STATUS in port_change_event.port_dict:
                self.port_dict[lport][self.ADMIN_STATUS] = \
                        port_change_event.port_dict[self.ADMIN_STATUS]

            if self.XCVR_TYPE in port_change_event.port_dict:
                self.port_dict[lport][self.XCVR_TYPE] = port_change_event.port_dict[self.XCVR_TYPE]
            self.port_dict[lport]['asic_id'] = asic_id
        # CONFIG_DB PORT_TABLE DEL case:
        elif port_change_event.db_name and \
                port_change_event.db_name == 'CONFIG_DB':
            # Only when port is removed from CONFIG, we consider this entry as deleted.
            if lport in self.port_dict:
                del self.port_dict[lport]
        # STATE_DB TRANSCEIVER_INFO DEL case:
        elif port_change_event.table_name and \
                port_change_event.table_name == 'TRANSCEIVER_INFO':
            # TRANSCEIVER_INFO DEL corresponds to transceiver removal (not
            # port/interface removal), in this case, remove XCVR_TYPE field from
            # self.port_dict
            if lport in self.port_dict and self.XCVR_TYPE in self.port_dict[lport]:
                del self.port_dict[lport][self.XCVR_TYPE]

    def get_host_tx_status(self, lport, asic_index):
        host_tx_ready = 'false'

        state_port_tbl = self.xcvr_table_helper.get_state_port_tbl(asic_index)

        found, value = state_port_tbl.hget(lport, self.HOST_TX_READY)
        if found:
            host_tx_ready = value
        return host_tx_ready

    def get_admin_status(self, lport, asic_index):
        admin_status = 'down'

        cfg_port_tbl = self.xcvr_table_helper.get_cfg_port_tbl(asic_index)

        found, value = cfg_port_tbl.hget(lport, self.ADMIN_STATUS)
        if found:
            admin_status = value
        return admin_status

    def run(self):
        if self.platform_chassis is None:
            self.log_error("Platform chassis is not available, stopping...")
            return

        try:
            self.task_worker()
        except Exception as e:
            self.helper_logger.log_error("Exception occured at {} thread due to {}".format(
                threading.current_thread().getName(), repr(e)))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            msg = traceback.format_exception(exc_type, exc_value, exc_traceback)
            for tb_line in msg:
                for tb_line_split in tb_line.splitlines():
                    self.helper_logger.log_error(tb_line_split)
            self.exc = e
            self.main_thread_stop_event.set()

    def join(self):
        self.task_stopping_event.set()
        threading.Thread.join(self)
        if self.exc:
            raise self.exc

    def calculate_tx_disable_delta_array(self, cur_tx_disable_array, tx_disable_flag, active_lanes):
        """
        Calculate the delta array between current tx_disable array and the target tx_disable flag.

        Args:
            cur_tx_disable_array (list): An array of boolean values, where True means the
                                         corresponding lane is disabled.
            tx_disable_flag (bool): The target tx_disable flag.
            active_lanes (list): An array of boolean values, where True means the
                                 corresponding lane is active for this logical port.

        Returns:
            list: A list of boolean values, where True means the corresponding
                  lane needs to be changed.
        """
        delta_array = []
        for active, cur_flag in zip(active_lanes, cur_tx_disable_array):
            is_different = (tx_disable_flag != cur_flag) if active else False
            delta_array.append(is_different)
        return delta_array

    def convert_bool_array_to_bit_mask(self, bool_array):
        """
        Convert a boolean array into a bitmask. If a value in the boolean array
        is True, the corresponding bit in the bitmask is set to 1, otherwise
        it's set to 0. The function starts from the least significant bit for
        the first item in the boolean array.

        Args:
            bool_array (list): An array of boolean values.

        Returns:
            int: A bitmask corresponding to the input boolean array.
        """
        mask = 0
        for i, flag in enumerate(bool_array):
            mask += (1 << i if flag else 0)
        return mask

    def task_worker(self):
        '''
        The main goal of sff_mgr is to make sure SFF compliant modules are
        brought up in a deterministc way, meaning TX is enabled only after
        host_tx_ready becomes True, and TX will be disabled when host_tx_ready
        becomes False. This will help eliminate link stability issue and
        potential interface flap, also turning off TX reduces the power
        consumption and avoid any lab hazard for admin shut interface.

        Platform can decide whether to enable sff_mgr. By default, it's disabled.

        Pre-requisite for platform to enable sff_mgr:
        platform needs to keep TX in disabled state after module coming
        out-of-reset, in either module insertion or bootup cases. This is to
        make sure the module is not transmitting with TX enabled before
        host_tx_ready is True.
        '''

        # CONFIG updates, and STATE_DB for insertion/removal, and host_tx_ready change
        port_change_observer = PortChangeObserver(self.namespaces,
                                                  self.logger_for_port_update_event,
                                                  self.task_stopping_event,
                                                  self.on_port_update_event,
                                                  self.PORT_TBL_MAP)

        # This thread doesn't need to expilictly wait on PortInitDone and
        # PortConfigDone events, as xcvrd main thread waits on them before
        # spawrning this thread.
        while not self.task_stopping_event.is_set():
            # Internally, handle_port_update_event will block for up to
            # SELECT_TIMEOUT_MSECS until a message is received(in select
            # function). A message is received when there is a Redis SET/DEL
            # operation in the DB tables. Upon process restart, messages will be
            # replayed for all fields, no need to explictly query the DB tables
            # here.
            if not port_change_observer.handle_port_update_event():
                # In the case of no real update, go back to the beginning of the loop
                continue

            for lport in self.port_dict:
                if self.task_stopping_event.is_set():
                    break
                data = self.port_dict[lport]
                pport = int(data.get('index', '-1'))
                subport_idx = int(data.get(self.SUBPORT, '0'))
                lanes_list = data.get(self.LANES_LIST, None)
                # active_lanes is a list of boolean values, where True means the
                # corresponding lane belongs to this logical port.
                active_lanes = data.get('active_lanes', None)
                xcvr_type = data.get(self.XCVR_TYPE, None)
                xcvr_inserted = False
                host_tx_ready_changed = False
                admin_status_changed = False
                if pport < 0 or lanes_list is None:
                    continue

                if xcvr_type is None:
                    # TRANSCEIVER_INFO table's XCVR_TYPE is not ready, meaning xcvr is not present
                    continue

                # Procced only for QSFP28/QSFP+ transceiver
                if not (xcvr_type.startswith('QSFP28') or xcvr_type.startswith('QSFP+')):
                    continue

                # Handle the case that host_tx_ready value in the local cache hasn't
                # been updated via PortChangeEvent:
                if self.HOST_TX_READY not in data:
                    # Fetch host_tx_ready status from STATE_DB (if not present
                    # in DB, treat it as false), and update self.port_dict
                    data[self.HOST_TX_READY] = self.get_host_tx_status(lport, data['asic_id'])
                    self.log_notice("{}: fetched DB and updated host_tx_ready={} locally".format(
                        lport, data[self.HOST_TX_READY]))
                # Handle the case that admin_status value in the local cache hasn't
                # been updated via PortChangeEvent:
                if self.ADMIN_STATUS not in data:
                    # Fetch admin_status from CONFIG_DB (if not present in DB,
                    # treat it as false), and update self.port_dict
                    data[self.ADMIN_STATUS] = self.get_admin_status(lport, data['asic_id'])
                    self.log_notice("{}: fetched DB and updated admin_status={} locally".format(
                        lport, data[self.ADMIN_STATUS]))

                # Check if there's a diff between current and previous XCVR_TYPE
                # It's a xcvr insertion case if TRANSCEIVER_INFO XCVR_TYPE doesn't exist
                # in previous port_dict snapshot
                if lport not in self.port_dict_prev or self.XCVR_TYPE not in self.port_dict_prev[lport]:
                    xcvr_inserted = True
                # Check if there's a diff between current and previous host_tx_ready
                if (lport not in self.port_dict_prev or
                        self.HOST_TX_READY not in self.port_dict_prev[lport] or
                        self.port_dict_prev[lport][self.HOST_TX_READY] != data[self.HOST_TX_READY]):
                    host_tx_ready_changed = True
                # Check if there's a diff between current and previous admin_status
                if (lport not in self.port_dict_prev or
                    self.ADMIN_STATUS not in self.port_dict_prev[lport] or
                    self.port_dict_prev[lport][self.ADMIN_STATUS] != data[self.ADMIN_STATUS]):
                    admin_status_changed = True
                # Skip if neither of below cases happens:
                # 1) xcvr insertion
                # 2) host_tx_ready getting changed
                # 3) admin_status getting changed
                # In addition to handle_port_update_event()'s internal filter,
                # this check serves as additional filter to ignore irrelevant
                # event, such as CONFIG_DB change other than admin_status field.
                if ((not xcvr_inserted) and
                    (not host_tx_ready_changed) and
                    (not admin_status_changed)):
                    continue
                self.log_notice(("{}: xcvr=present(inserted={}), "
                                 "host_tx_ready={}(changed={}), "
                                 "admin_status={}(changed={})").format(
                    lport,
                    xcvr_inserted,
                    data[self.HOST_TX_READY], host_tx_ready_changed,
                    data[self.ADMIN_STATUS], admin_status_changed))

                # double-check the HW presence before moving forward
                sfp = self.platform_chassis.get_sfp(pport)
                if not sfp.get_presence():
                    self.log_error("{}: module not present!".format(lport))
                    del self.port_dict[lport][self.XCVR_TYPE]
                    continue
                try:
                    # Skip if XcvrApi is not supported
                    api = sfp.get_xcvr_api()
                    if api is None:
                        self.log_error(
                            "{}: skipping sff_mgr since no xcvr api!".format(lport))
                        continue

                    # Skip if it's not a paged memory device
                    if api.is_flat_memory():
                        self.log_notice(
                            "{}: skipping sff_mgr for flat memory xcvr".format(lport))
                        continue

                    # Skip if it's a copper cable
                    if api.is_copper():
                        self.log_notice(
                            "{}: skipping sff_mgr for copper cable".format(lport))
                        continue

                    # Skip if tx_disable action is not supported for this xcvr
                    if not api.get_tx_disable_support():
                        self.log_notice(
                            "{}: skipping sff_mgr due to tx_disable not supported".format(
                                lport))
                        continue
                except (AttributeError, NotImplementedError):
                    # Skip if these essential routines are not available
                    continue

                if active_lanes is None:
                    active_lanes = self.get_active_lanes_for_lport(lport, subport_idx,
                                                               len(lanes_list),
                                                               self.DEFAULT_NUM_LANES_PER_PPORT)
                    if active_lanes is None:
                        self.log_error("{}: skipping sff_mgr due to "
                                       "failing to get active lanes".format(lport))
                        continue
                    # Save active_lanes in self.port_dict
                    self.port_dict[lport]['active_lanes'] = active_lanes

                # Only turn on TX if both host_tx_ready is true and admin_status is up
                target_tx_disable_flag = not (data[self.HOST_TX_READY] == 'true'
                                              and data[self.ADMIN_STATUS] == 'up')
                # get_tx_disable API returns an array of bool, with tx_disable flag on each lane.
                # True means tx disabled; False means tx enabled.
                cur_tx_disable_array = api.get_tx_disable()
                if cur_tx_disable_array is None:
                    self.log_error("{}: Failed to get current tx_disable value".format(lport))
                    # If reading current tx_disable/enable value failed (could be due to
                    # read error), then set this variable to the opposite value of
                    # target_tx_disable_flag, to let detla array to be True on
                    # all the interested lanes, to try best-effort TX disable/enable.
                    cur_tx_disable_array = [not target_tx_disable_flag] * self.DEFAULT_NUM_LANES_PER_PPORT
                # Get an array of bool, where it's True only on the lanes that need change.
                delta_array = self.calculate_tx_disable_delta_array(cur_tx_disable_array,
                                                                    target_tx_disable_flag, active_lanes)
                mask = self.convert_bool_array_to_bit_mask(delta_array)
                if mask == 0:
                    self.log_notice("{}: No change is needed for tx_disable value".format(lport))
                    continue
                if api.tx_disable_channel(mask, target_tx_disable_flag):
                    self.log_notice("{}: TX was {} with lanes mask: {}".format(
                        lport, "disabled" if target_tx_disable_flag else "enabled", bin(mask)))
                else:
                    self.log_error("{}: Failed to {} TX with lanes mask: {}".format(
                        lport, "disable" if target_tx_disable_flag else "enable", bin(mask)))

            # Take a snapshot for port_dict, this will be used to calculate diff
            # later in the while loop to determine if there's really a value
            # change on the fields related to the events we care about.
            self.port_dict_prev = copy.deepcopy(self.port_dict)
