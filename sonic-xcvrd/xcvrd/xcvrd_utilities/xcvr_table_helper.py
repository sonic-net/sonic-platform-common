try:
    from sonic_py_common import daemon_base
    from sonic_py_common import multi_asic
    from swsscommon import swsscommon
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")

TRANSCEIVER_INFO_TABLE = 'TRANSCEIVER_INFO'
TRANSCEIVER_FIRMWARE_INFO_TABLE = 'TRANSCEIVER_FIRMWARE_INFO'
TRANSCEIVER_DOM_SENSOR_TABLE = 'TRANSCEIVER_DOM_SENSOR'
TRANSCEIVER_DOM_THRESHOLD_TABLE = 'TRANSCEIVER_DOM_THRESHOLD'
TRANSCEIVER_STATUS_TABLE = 'TRANSCEIVER_STATUS'
TRANSCEIVER_PM_TABLE = 'TRANSCEIVER_PM'

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
