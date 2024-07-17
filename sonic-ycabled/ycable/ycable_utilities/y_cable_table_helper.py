"""
    y_cable_table_helper.py
    helper utlities configuring y_cable tables for ycabled daemon
"""

import threading
from sonic_py_common import daemon_base, logger
from sonic_py_common import multi_asic
from swsscommon import swsscommon


SYSLOG_IDENTIFIER = "y_cable_table_helper"

helper_logger = logger.Logger(SYSLOG_IDENTIFIER)

MUX_CABLE_STATIC_INFO_TABLE = "MUX_CABLE_STATIC_INFO"
MUX_CABLE_INFO_TABLE = "MUX_CABLE_INFO"
TRANSCEIVER_INFO_TABLE = 'TRANSCEIVER_INFO'

class YcableInfoUpdateTableHelper(object):
    def __init__(self):

        self.state_db = {}
        self.config_db = {}
        self.port_tbl = {}
        self.status_tbl = {}
        self.y_cable_tbl = {} 
        self.mux_tbl = {}

        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            self.state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            self.config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
            self.port_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "MUX_CABLE")
            self.status_tbl[asic_id] = swsscommon.Table(self.state_db[asic_id], TRANSCEIVER_INFO_TABLE)
            self.y_cable_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            self.mux_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], MUX_CABLE_INFO_TABLE)

    def get_state_db(self):
        return self.state_db

    def get_config_db(self):
        return self.config_db

    def get_port_tbl(self):
        return self.port_tbl

    def get_status_tbl(self):
        return self.status_tbl

    def get_y_cable_tbl(self):
        return self.y_cable_tbl

    def get_mux_tbl(self):
        return self.mux_tbl


class YcableStateUpdateTableHelper(object):
    def __init__(self):

        self.state_db = {}
        self.appl_db = {}
        self.sub_status_tbl = {}
        self.config_db = {}
        self.port_tbl = {}
        self.y_cable_tbl = {}
        self.static_tbl = {}
        self.mux_tbl = {}
        self.port_table_keys = {}
        self.loopback_tbl= {}
        self.loopback_keys = {}
        self.hw_mux_cable_tbl = {}
        self.hw_mux_cable_tbl_peer = {}
        self.grpc_config_tbl = {}
        self.fwd_state_response_tbl = {}

        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            self.state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            self.appl_db[asic_id] = daemon_base.db_connect("APPL_DB", namespace)
            self.sub_status_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.state_db[asic_id], TRANSCEIVER_INFO_TABLE)
            self.config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
            self.port_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "MUX_CABLE")
            self.port_table_keys[asic_id] = self.port_tbl[asic_id].getKeys()
            self.loopback_tbl[asic_id] = swsscommon.Table(
                self.config_db[asic_id], "LOOPBACK_INTERFACE")
            self.loopback_keys[asic_id] = self.loopback_tbl[asic_id].getKeys()
            self.state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            self.hw_mux_cable_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            self.hw_mux_cable_tbl_peer[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "HW_MUX_CABLE_TABLE_PEER")
            self.y_cable_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            self.static_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], MUX_CABLE_STATIC_INFO_TABLE)
            self.mux_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], MUX_CABLE_INFO_TABLE)
            self.grpc_config_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "GRPCCLIENT")
            self.fwd_state_response_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "FORWARDING_STATE_RESPONSE")
            self.static_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], MUX_CABLE_STATIC_INFO_TABLE)

    def get_sub_status_tbl(self):
        return self.sub_status_tbl

    def get_state_db(self):
        return self.state_db

    def get_config_db(self):
        return self.config_db

    def get_appl_db(self):
        return self.appl_db

    def get_port_tbl(self):
        return self.port_tbl

    def get_mux_tbl(self):
        return self.mux_tbl

    def get_loopback_tbl(self):
        return self.loopback_tbl

    def get_hw_mux_cable_tbl(self):
        return self.hw_mux_cable_tbl

    def get_hw_mux_cable_tbl_peer(self):
        return self.hw_mux_cable_tbl_peer

    def get_grpc_config_tbl(self):
        return self.grpc_config_tbl

    def get_y_cable_tbl(self):
        return self.y_cable_tbl

    def get_static_tbl(self):
        return self.static_tbl

    def get_fwd_state_response_tbl(self):
        return self.fwd_state_response_tbl



class DaemonYcableTableHelper(object):
    def __init__(self):

        self.state_db = {}
        self.appl_db = {}
        self.config_db = {}
        self.port_tbl = {}
        self.y_cable_tbl = {} 
        self.metadata_tbl = {}
        self.static_tbl, self.mux_tbl = {}, {}
        self.port_table_keys = {}
        self.xcvrd_log_tbl = {}
        self.loopback_tbl= {}
        self.loopback_keys = {}
        self.hw_mux_cable_tbl = {}
        self.hw_mux_cable_tbl_peer = {}
        self.grpc_config_tbl = {}
        self.fwd_state_response_tbl = {}

        # Get the namespaces in the platform
        fvs_updated = swsscommon.FieldValuePairs([('log_verbosity', 'notice')])
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            self.appl_db[asic_id] = daemon_base.db_connect("APPL_DB", namespace)
            self.state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            self.config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
            self.port_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "MUX_CABLE")
            self.y_cable_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            self.mux_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], MUX_CABLE_INFO_TABLE)
            self.metadata_tbl[asic_id] = swsscommon.Table(
                self.config_db[asic_id], "DEVICE_METADATA")
            self.port_table_keys[asic_id] = self.port_tbl[asic_id].getKeys()
            self.xcvrd_log_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "XCVRD_LOG")
            self.xcvrd_log_tbl[asic_id].set("Y_CABLE", fvs_updated)
            self.loopback_tbl[asic_id] = swsscommon.Table(
                self.config_db[asic_id], "LOOPBACK_INTERFACE")
            self.loopback_keys[asic_id] = self.loopback_tbl[asic_id].getKeys()
            self.hw_mux_cable_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            self.hw_mux_cable_tbl_peer[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "HW_MUX_CABLE_TABLE_PEER")
            self.static_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], MUX_CABLE_STATIC_INFO_TABLE)
            self.grpc_config_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "GRPCCLIENT")
            self.fwd_state_response_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "FORWARDING_STATE_RESPONSE")


    def get_state_db(self):
        return self.state_db

    def get_config_db(self):
        return self.config_db

    def get_port_tbl(self):
        return self.port_tbl

    def get_y_cable_tbl(self):
        return self.y_cable_tbl

    def get_mux_tbl(self):
        return self.mux_tbl

    def get_metadata_tbl(self):
        return self.metadata_tbl

    def get_xcvrd_log_tbl(self):
        return self.xcvrd_log_tbl

    def get_loopback_tbl(self):
        return self.loopback_tbl

    def get_hw_mux_cable_tbl(self):
        return self.hw_mux_cable_tbl

    def get_hw_mux_cable_tbl_peer(self):
        return self.hw_mux_cable_tbl_peer

    def get_static_tbl(self):
        return self.static_tbl

    def get_grpc_config_tbl(self):
        return self.grpc_config_tbl

    def get_fwd_state_response_tbl(self):
        return self.fwd_state_response_tbl

class YcableTableUpdateTableHelper(object):
    def __init__(self):

        self.appl_db, self.state_db, self.config_db, self.status_tbl, self.status_tbl_peer = {}, {}, {}, {}, {}
        self.hw_mux_cable_tbl, self.hw_mux_cable_tbl_peer = {}, {}
        self.hw_mux_cable_tbl_keys = {}
        self.port_tbl, self.port_table_keys = {}, {}
        self.fwd_state_command_tbl, self.fwd_state_response_tbl, self.mux_cable_command_tbl = {}, {}, {}
        self.mux_metrics_tbl = {}
        self.grpc_config_tbl = {}
        self.y_cable_response_tbl = {}


        if multi_asic.is_multi_asic():
            # Load the namespace details first from the database_global.json file.
            swsscommon.SonicDBConfig.initializeGlobalConfig()

        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            # Open a handle to the Application database, in all namespaces
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            self.appl_db[asic_id] = daemon_base.db_connect("APPL_DB", namespace)
            self.config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
            self.state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            self.status_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], swsscommon.APP_HW_MUX_CABLE_TABLE_NAME)
            self.mux_cable_command_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], swsscommon.APP_MUX_CABLE_COMMAND_TABLE_NAME)
            self.mux_metrics_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], swsscommon.STATE_MUX_METRICS_TABLE_NAME)
            self.hw_mux_cable_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            # TODO add definition inside app DB
            self.status_tbl_peer[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "HW_FORWARDING_STATE_PEER")
            self.fwd_state_command_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "FORWARDING_STATE_COMMAND")
            self.fwd_state_response_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "FORWARDING_STATE_RESPONSE")
            self.hw_mux_cable_tbl_peer[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "HW_MUX_CABLE_TABLE_PEER")
            self.y_cable_response_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "MUX_CABLE_RESPONSE_TABLE")
            self.port_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "MUX_CABLE")
            self.port_table_keys[asic_id] = self.port_tbl[asic_id].getKeys()
            self.grpc_config_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "GRPCCLIENT")

    def get_state_db(self):
        return self.state_db

    def get_config_db(self):
        return self.config_db

    def get_appl_db(self):
        return self.appl_db

    def get_status_tbl(self):
        return self.status_tbl

    def get_status_tbl_peer(self):
        return self.status_tbl_peer

    def get_mux_cable_command_tbl(self):
        return self.mux_cable_command_tbl

    def get_mux_metrics_tbl(self):
        return self.mux_metrics_tbl

    def get_hw_mux_cable_tbl(self):
        return self.hw_mux_cable_tbl

    def get_hw_mux_cable_tbl_peer(self):
        return self.hw_mux_cable_tbl_peer

    def get_fwd_state_command_tbl(self):
        return self.fwd_state_command_tbl

    def get_fwd_state_response_tbl(self):
        return self.fwd_state_response_tbl

    def get_y_cable_response_tbl(self):
        return self.y_cable_response_tbl

    def get_port_tbl(self):
        return self.port_tbl

    def get_grpc_config_tbl(self):
        return self.grpc_config_tbl

class YcableCliUpdateTableHelper(object):
    def __init__(self):

        self.appl_db, self.state_db, self.config_db = {}, {}, {}
        self.hw_mux_cable_tbl = {}
        self.xcvrd_log_tbl = {}
        self.port_tbl = {}
        self.mux_tbl = {}
        self.xcvrd_down_fw_cmd_tbl, self.xcvrd_down_fw_rsp_tbl, self.xcvrd_down_fw_cmd_sts_tbl = {}, {}, {}
        self.xcvrd_down_fw_status_cmd_tbl, self.xcvrd_down_fw_status_rsp_tbl, self.xcvrd_down_fw_status_cmd_sts_tbl = {}, {}, {}
        self.xcvrd_acti_fw_cmd_tbl, self.xcvrd_acti_fw_cmd_arg_tbl, self.xcvrd_acti_fw_rsp_tbl, self.xcvrd_acti_fw_cmd_sts_tbl = {}, {}, {}, {}
        self.xcvrd_roll_fw_cmd_tbl, self.xcvrd_roll_fw_rsp_tbl, self.xcvrd_roll_fw_cmd_sts_tbl = {}, {}, {}
        self.xcvrd_show_fw_cmd_tbl, self.xcvrd_show_fw_rsp_tbl, self.xcvrd_show_fw_cmd_sts_tbl, self.xcvrd_show_fw_res_tbl = {}, {}, {}, {}
        self.xcvrd_show_hwmode_dir_cmd_tbl, self.xcvrd_show_hwmode_dir_rsp_tbl, self.xcvrd_show_hwmode_dir_res_tbl, self.xcvrd_show_hwmode_dir_cmd_sts_tbl = {}, {}, {}, {}
        self.xcvrd_show_hwmode_swmode_cmd_tbl, self.xcvrd_show_hwmode_swmode_rsp_tbl, self.xcvrd_show_hwmode_swmode_cmd_sts_tbl = {}, {}, {}
        self.xcvrd_config_hwmode_state_cmd_tbl, self.xcvrd_config_hwmode_state_rsp_tbl , self.xcvrd_config_hwmode_state_cmd_sts_tbl= {}, {}, {}
        self.xcvrd_config_hwmode_swmode_cmd_tbl, self.xcvrd_config_hwmode_swmode_rsp_tbl , self.xcvrd_config_hwmode_swmode_cmd_sts_tbl= {}, {}, {}
        self.xcvrd_config_prbs_cmd_tbl, self.xcvrd_config_prbs_cmd_arg_tbl, self.xcvrd_config_prbs_rsp_tbl , self.xcvrd_config_prbs_cmd_sts_tbl= {}, {}, {}, {}
        self.xcvrd_config_loop_cmd_tbl, self.xcvrd_config_loop_cmd_arg_tbl, self.xcvrd_config_loop_rsp_tbl , self.xcvrd_config_loop_cmd_sts_tbl= {}, {}, {}, {}
        self.xcvrd_show_event_cmd_tbl, self.xcvrd_show_event_rsp_tbl , self.xcvrd_show_event_cmd_sts_tbl, self.xcvrd_show_event_res_tbl= {}, {}, {}, {}
        self.xcvrd_show_fec_cmd_tbl, self.xcvrd_show_fec_rsp_tbl , self.xcvrd_show_fec_cmd_sts_tbl, self.xcvrd_show_fec_res_tbl= {}, {}, {}, {}
        self.xcvrd_show_ber_cmd_tbl, self.xcvrd_show_ber_cmd_arg_tbl, self.xcvrd_show_ber_rsp_tbl , self.xcvrd_show_ber_cmd_sts_tbl, self.xcvrd_show_ber_res_tbl= {}, {}, {}, {}, {}


        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            # Open a handle to the Application database, in all namespaces
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            self.appl_db[asic_id] = daemon_base.db_connect("APPL_DB", namespace)
            self.config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
            self.state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)

            self.xcvrd_log_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.config_db[asic_id], "XCVRD_LOG")
            self.xcvrd_show_fw_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_SHOW_FW_CMD")
            self.xcvrd_show_fw_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_SHOW_FW_CMD")
            self.xcvrd_show_fw_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_SHOW_FW_RSP")
            self.xcvrd_show_fw_res_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_SHOW_FW_RES")
            self.xcvrd_down_fw_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_DOWN_FW_CMD")
            self.xcvrd_down_fw_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_DOWN_FW_CMD")
            self.xcvrd_down_fw_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_DOWN_FW_RSP")
            self.xcvrd_down_fw_status_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_DOWN_FW_STATUS_CMD")
            self.xcvrd_down_fw_status_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_DOWN_FW_STATUS_RSP")
            self.xcvrd_acti_fw_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_ACTI_FW_CMD")
            self.xcvrd_acti_fw_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_ACTI_FW_CMD")
            self.xcvrd_acti_fw_cmd_arg_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_ACTI_FW_CMD_ARG")
            self.xcvrd_acti_fw_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_ACTI_FW_RSP")
            self.xcvrd_roll_fw_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_ROLL_FW_CMD")
            self.xcvrd_roll_fw_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_ROLL_FW_CMD")
            self.xcvrd_roll_fw_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_ROLL_FW_RSP")
            self.xcvrd_show_hwmode_dir_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_SHOW_HWMODE_DIR_CMD")
            self.xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_SHOW_HWMODE_DIR_CMD")
            self.xcvrd_show_hwmode_dir_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_SHOW_HWMODE_DIR_RSP")
            self.xcvrd_show_hwmode_dir_res_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_SHOW_HWMODE_DIR_RES")
            self.xcvrd_config_hwmode_state_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_CONFIG_HWMODE_DIR_CMD")
            self.xcvrd_config_hwmode_state_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_CONFIG_HWMODE_DIR_CMD")
            self.xcvrd_config_hwmode_state_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_CONFIG_HWMODE_DIR_RSP")
            self.xcvrd_config_hwmode_swmode_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_CONFIG_HWMODE_SWMODE_CMD")
            self.xcvrd_config_hwmode_swmode_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_CONFIG_HWMODE_SWMODE_CMD")
            self.xcvrd_config_hwmode_swmode_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_CONFIG_HWMODE_SWMODE_RSP")
            self.xcvrd_show_hwmode_swmode_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_SHOW_HWMODE_SWMODE_CMD")
            self.xcvrd_show_hwmode_swmode_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_SHOW_HWMODE_SWMODE_CMD")
            self.xcvrd_show_hwmode_swmode_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_SHOW_HWMODE_SWMODE_RSP")
            self.xcvrd_config_prbs_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_CONFIG_PRBS_CMD")
            self.xcvrd_config_prbs_cmd_arg_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_CONFIG_PRBS_CMD_ARG")
            self.xcvrd_config_prbs_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_CONFIG_PRBS_CMD")
            self.xcvrd_config_prbs_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_CONFIG_PRBS_RSP")
            self.xcvrd_config_loop_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_CONFIG_LOOP_CMD")
            self.xcvrd_config_loop_cmd_arg_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_CONFIG_LOOP_CMD_ARG")
            self.xcvrd_config_loop_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_CONFIG_LOOP_CMD")
            self.xcvrd_config_loop_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_CONFIG_LOOP_RSP")
            self.xcvrd_show_event_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_EVENT_LOG_CMD")
            self.xcvrd_show_event_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_EVENT_LOG_CMD")
            self.xcvrd_show_event_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_EVENT_LOG_RSP")
            self.xcvrd_show_event_res_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_EVENT_LOG_RES")
            self.xcvrd_show_fec_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_GET_FEC_CMD")
            self.xcvrd_show_fec_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_GET_FEC_CMD")
            self.xcvrd_show_fec_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_GET_FEC_RSP")
            self.xcvrd_show_fec_res_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_GET_FEC_RES")
            self.xcvrd_show_ber_cmd_tbl[asic_id] = swsscommon.SubscriberStateTable(
                self.appl_db[asic_id], "XCVRD_GET_BER_CMD")
            self.xcvrd_show_ber_cmd_arg_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_GET_BER_CMD_ARG")
            self.xcvrd_show_ber_cmd_sts_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "XCVRD_GET_BER_CMD")
            self.xcvrd_show_ber_rsp_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_GET_BER_RSP")
            self.xcvrd_show_ber_res_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], "XCVRD_GET_BER_RES")
            self.port_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "MUX_CABLE")
            self.mux_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], MUX_CABLE_INFO_TABLE)
            self.hw_mux_cable_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)

    def get_state_db(self):
        return self.state_db

    def get_config_db(self):
        return self.config_db

    def get_appl_db(self):
        return self.appl_db


class YcableAsyncNotificationTableHelper(object):
    def __init__(self):

        self.state_db = {}
        self.config_db = {}
        self.appl_db = {}
        self.port_tbl = {}
        self.status_tbl = {}
        self.y_cable_tbl = {} 
        self.mux_tbl = {}
        self.grpc_config_tbl = {}
        self.fwd_state_response_tbl = {}
        self.loopback_tbl= {}
        self.loopback_keys = {}

        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            self.state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            self.appl_db[asic_id] = daemon_base.db_connect("APPL_DB", namespace)
            self.config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
            self.port_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "MUX_CABLE")
            self.status_tbl[asic_id] = swsscommon.Table(self.state_db[asic_id], TRANSCEIVER_INFO_TABLE)
            self.y_cable_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            self.mux_tbl[asic_id] = swsscommon.Table(
                self.state_db[asic_id], MUX_CABLE_INFO_TABLE)
            self.grpc_config_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "GRPCCLIENT")
            self.fwd_state_response_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "FORWARDING_STATE_RESPONSE")
            self.loopback_tbl[asic_id] = swsscommon.Table(
                self.config_db[asic_id], "LOOPBACK_INTERFACE")
            self.loopback_keys[asic_id] = self.loopback_tbl[asic_id].getKeys()

    def get_state_db(self):
        return self.state_db

    def get_config_db(self):
        return self.config_db

    def get_port_tbl(self):
        return self.port_tbl

    def get_status_tbl(self):
        return self.status_tbl

    def get_y_cable_tbl(self):
        return self.y_cable_tbl

    def get_mux_tbl(self):
        return self.mux_tbl

    def get_grpc_config_tbl(self):
        return self.grpc_config_tbl

    def get_fwd_state_response_tbl(self):
        return self.fwd_state_response_tbl

class YcableChannelStateTableHelper(object):
    def __init__(self):

        self.appl_db = {}
        self.fwd_state_response_tbl = {}

        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            self.appl_db[asic_id] = daemon_base.db_connect("APPL_DB", namespace)
            self.fwd_state_response_tbl[asic_id] = swsscommon.Table(
                self.appl_db[asic_id], "FORWARDING_STATE_RESPONSE")
        helper_logger.log_notice('created table instance from tid {}'.format(threading.currentThread().getName()))

    def get_fwd_state_response_tbl(self):
        return self.fwd_state_response_tbl
