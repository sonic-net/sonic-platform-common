try:
    from sonic_py_common import daemon_base, logger
    from sonic_py_common import multi_asic
    from swsscommon import swsscommon
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")

SYSLOG_IDENTIFIER = "xcvrd"
helper_logger = logger.Logger(SYSLOG_IDENTIFIER)

TRANSCEIVER_INFO_TABLE = 'TRANSCEIVER_INFO'
TRANSCEIVER_FIRMWARE_INFO_TABLE = 'TRANSCEIVER_FIRMWARE_INFO'
TRANSCEIVER_DOM_SENSOR_TABLE = 'TRANSCEIVER_DOM_SENSOR'
TRANSCEIVER_DOM_THRESHOLD_TABLE = 'TRANSCEIVER_DOM_THRESHOLD'
TRANSCEIVER_STATUS_TABLE = 'TRANSCEIVER_STATUS'
TRANSCEIVER_PM_TABLE = 'TRANSCEIVER_PM'

NPU_SI_SETTINGS_SYNC_STATUS_KEY = 'NPU_SI_SETTINGS_SYNC_STATUS'
NPU_SI_SETTINGS_DEFAULT_VALUE = 'NPU_SI_SETTINGS_DEFAULT'
NPU_SI_SETTINGS_NOTIFIED_VALUE = 'NPU_SI_SETTINGS_NOTIFIED'

class XcvrTableHelper:
    def __init__(self, namespaces):
        self.int_tbl, self.dom_tbl, self.dom_threshold_tbl, self.status_tbl, self.app_port_tbl, \
		self.cfg_port_tbl, self.state_port_tbl, self.pm_tbl, self.firmware_info_tbl = {}, {}, {}, {}, {}, {}, {}, {}, {}
        self.state_db = {}
        self.cfg_db = {}
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            self.state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            self.int_tbl[asic_id] = swsscommon.Table(self.state_db[asic_id], TRANSCEIVER_INFO_TABLE)
            self.dom_tbl[asic_id] = swsscommon.Table(self.state_db[asic_id], TRANSCEIVER_DOM_SENSOR_TABLE)
            self.dom_threshold_tbl[asic_id] = swsscommon.Table(self.state_db[asic_id], TRANSCEIVER_DOM_THRESHOLD_TABLE)
            self.status_tbl[asic_id] = swsscommon.Table(self.state_db[asic_id], TRANSCEIVER_STATUS_TABLE)
            self.pm_tbl[asic_id] = swsscommon.Table(self.state_db[asic_id], TRANSCEIVER_PM_TABLE)
            self.firmware_info_tbl[asic_id] = swsscommon.Table(self.state_db[asic_id], TRANSCEIVER_FIRMWARE_INFO_TABLE)
            self.state_port_tbl[asic_id] = swsscommon.Table(self.state_db[asic_id], swsscommon.STATE_PORT_TABLE_NAME)
            appl_db = daemon_base.db_connect("APPL_DB", namespace)
            self.app_port_tbl[asic_id] = swsscommon.ProducerStateTable(appl_db, swsscommon.APP_PORT_TABLE_NAME)
            self.cfg_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
            self.cfg_port_tbl[asic_id] = swsscommon.Table(self.cfg_db[asic_id], swsscommon.CFG_PORT_TABLE_NAME)

    def get_intf_tbl(self, asic_id):
        return self.int_tbl[asic_id]

    def get_dom_tbl(self, asic_id):
        return self.dom_tbl[asic_id]

    def get_dom_threshold_tbl(self, asic_id):
        return self.dom_threshold_tbl[asic_id]

    def get_status_tbl(self, asic_id):
        return self.status_tbl[asic_id]

    def get_pm_tbl(self, asic_id):
        return self.pm_tbl[asic_id]

    def get_firmware_info_tbl(self, asic_id):
        return self.firmware_info_tbl[asic_id]

    def get_app_port_tbl(self, asic_id):
        return self.app_port_tbl[asic_id]

    def get_state_db(self, asic_id):
        return self.state_db[asic_id]

    def get_cfg_port_tbl(self, asic_id):
        return self.cfg_port_tbl[asic_id]

    def get_state_port_tbl(self, asic_id):
        return self.state_port_tbl[asic_id]

    def get_state_db_port_table_val_by_key(self, lport, port_mapping, key):
        """
        Retrieves the value of a key from STATE_DB PORT_TABLE|<lport> for the given logical port
        Args:
            lport:
                logical port name
            port_mapping:
                A PortMapping object
            key:
                key for the corresponding value to be retrieved
        Returns:
            The value of the key if the key is found in STATE_DB PORT_TABLE|<lport>
            None otherwise
        """

        if port_mapping is None:
            helper_logger.log_error("Get value by key from STATE_DB: port_mapping is None "
                                    "for lport {}".format(lport))
            return None

        asic_index = port_mapping.get_asic_id_for_logical_port(lport)
        state_port_table = self.get_state_port_tbl(asic_index)
        if state_port_table is None:
            helper_logger.log_error("Get value by key from STATE_DB: state_db is None with asic_index {} "
                                    "for lport {}".format(asic_index, lport))
            return None

        found, state_port_table_fvs = state_port_table.get(lport)
        if not found:
            helper_logger.log_error("Get value by key from STATE_DB: Unable to find lport {}".format(lport))
            return None

        state_port_table_fvs_dict = dict(state_port_table_fvs)
        if key not in state_port_table_fvs_dict:
            helper_logger.log_error("Get value by key from STATE_DB: Unable to find key {} "
                                    "state_port_table_fvs_dict {} for lport {}".format(key, state_port_table_fvs_dict, lport))
            return None

        return state_port_table_fvs_dict[key]

    def is_npu_si_settings_update_required(self, lport, port_mapping):
        """
        Checks if NPU SI settings update is required for a module
        Args:
            lport:
                logical port name
            port_mapping:
                A PortMapping object
        Returns:
            True if NPU_SI_SETTINGS_SYNC_STATUS_KEY is
                - not present/accessible from STATE_DB or
                - set to NPU_SI_SETTINGS_DEFAULT_VALUE
            False otherwise
        """
        npu_si_settings_sync_val = self.get_state_db_port_table_val_by_key(lport,
                                                                            port_mapping, NPU_SI_SETTINGS_SYNC_STATUS_KEY)

        # If npu_si_settings_sync_val is None, it can also mean that the key is not present in the table
        return npu_si_settings_sync_val is None or npu_si_settings_sync_val == NPU_SI_SETTINGS_DEFAULT_VALUE
