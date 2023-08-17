"""
    y_cable_helper.py
    helper utlities configuring y_cable for xcvrd daemon
"""

import asyncio
import datetime
import ipaddress
import json
import os
import re
import sys
import threading
import time
import traceback

from importlib import import_module


import grpc
from proto_out import linkmgr_grpc_driver_pb2_grpc
from proto_out import linkmgr_grpc_driver_pb2
from sonic_py_common import daemon_base, logger
from sonic_py_common import multi_asic
from sonic_y_cable import y_cable_vendor_mapping
from swsscommon import swsscommon


from . import y_cable_table_helper

if sys.version_info.major == 3:
    UNICODE_TYPE = str
else:
    UNICODE_TYPE = unicode

SELECT_TIMEOUT = 1000

#gRPC timeouts for RPC
QUERY_ADMIN_FORWARDING_TIMEOUT = 0.5
SET_ADMIN_FORWARDING_TIMEOUT = 0.5

y_cable_platform_sfputil = None
y_cable_platform_chassis = None
y_cable_is_platform_vs = None

# Global port channels for gRPC RPC's
grpc_port_channels = {}
# Global port channel stubs for gRPC RPC's
grpc_port_stubs = {}
# Global port channel connectivity for gRPC RPC's
grpc_port_connectivity = {}
# Global port statistics for gRPC RPC's
grpc_port_stats = {}

GRPC_PORT = 50075

read_side = -1

DEFAULT_NAMESPACE = ""

LOOPBACK_INTERFACE_T0 = "10.212.64.1/32"
LOOPBACK_INTERFACE_LT0 = "10.212.64.2/32"
LOOPBACK_INTERFACE_T0_NIC = "10.1.0.38/32"
LOOPBACK_INTERFACE_LT0_NIC = "10.1.0.39/32"
# rename and put in right place
# port id 0 -> maps to  T0
# port id 1 -> maps to  LT0

GRPC_CLIENT_OPTIONS = [
    ('grpc.keepalive_timeout_ms', 8000),
    ('grpc.keepalive_time_ms', 4000),
    ('grpc.keepalive_permit_without_calls', True),
    ('grpc.http2.max_pings_without_data', 0)
]

CONFIG_MUX_STATES = ["active", "standby", "auto", "manual", "detach"]

DEFAULT_PORT_IDS = [0, 1]

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

y_cable_port_instances = {}
y_cable_port_locks = {}

disable_telemetry = False

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

PHYSICAL_PORT_MAPPING_ERROR = -1
PORT_INSTANCE_ERROR = -1

port_mapping_error_values = {
  PHYSICAL_PORT_MAPPING_ERROR,
  PORT_INSTANCE_ERROR
}

SECRETS_PATH = "/etc/sonic/grpc_secrets.json"

def format_mapping_identifier(string):
    """
    Takes an arbitrary string and creates a valid entity for port mapping file.
    The input could contain trailing and leading spaces, upper cases etc.
    Convert them to what is defined in the y_cable vendor_mapping file.

    """

    if not isinstance(string, str):
        helper_logger.log_warning(
            "Error: mapping identifier is not a string {}".format(string))
        return


    # create a working copy (and make it lowercase, while we're at it)
    s = string.lower()

    # remove leading and trailing whitespace
    s = s.strip()

    # Replace whitespace with underscores
    # Make spaces into underscores
    s = re.sub(r'\s+', '_', s)

    return s

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


def y_cable_wrapper_get_presence(physical_port):
    if y_cable_platform_chassis is not None:
        try:
            return y_cable_platform_chassis.get_sfp(physical_port).get_presence()
        except NotImplementedError:
            pass
    if y_cable_is_platform_vs is True:
        return True
    return y_cable_platform_sfputil.get_presence(physical_port)



def hook_y_cable_simulated(target):
    """
    Decorator to add hook for using the simulated y_cable driver.
    This decorator checks existence of the configuration file required by the simulated y_cable driver. If the
    configuration file is found, then override the "manufacturer" and "model" fields with value "microsoft" and
    "simulated" in the collected transceiver info dict. Consequently, instance of the simulated y_cable driver
    class will be initialized.
    When the configuration file is not found on system, then just return the original transceiver info to initialize
    instance of y_cable driver class of whatever actually plugged physical y_cable.
    For test systems using simulated y_cable, we can just inject the simulated y_cable driver config file then
    restart the pmon service before testing starts.

    Args:
        target (function): The function collecting transceiver info.
    """

    MUX_SIMULATOR_CONFIG_FILE = "/etc/sonic/mux_simulator.json"
    VENDOR = "microsoft"
    MODEL = "simulated"

    def wrapper(*args, **kwargs):
        res = target(*args, **kwargs)
        if os.path.exists(MUX_SIMULATOR_CONFIG_FILE):
            res["manufacturer"] = VENDOR
            res["model"] = MODEL
        return res

    wrapper.__name__ = target.__name__

    return wrapper

@hook_y_cable_simulated
def y_cable_wrapper_get_transceiver_info(physical_port):
    if y_cable_platform_chassis is not None:
        try:
            return y_cable_platform_chassis.get_sfp(physical_port).get_transceiver_info()
        except NotImplementedError:
            pass
    if y_cable_is_platform_vs is True:
        return {}
    return y_cable_platform_sfputil.get_transceiver_info_dict(physical_port)

def get_ycable_physical_port_from_logical_port(logical_port_name):

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if y_cable_wrapper_get_presence(physical_port):

            return physical_port
        else:
            helper_logger.log_warning(
                "Error: Could not establish presence for  Y cable port {} while retreiving physical port mapping".format(logical_port_name))
            return -1

    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable table port {} while retreiving physical port mapping".format(logical_port_name))
        return -1

def get_ycable_port_instance_from_logical_port(logical_port_name):

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if y_cable_wrapper_get_presence(physical_port):

            port_instance = y_cable_port_instances.get(physical_port)
            if port_instance is None:
                helper_logger.log_error(
                    "Error: Could not get port instance from the dict for Y cable port {}".format(logical_port_name))
                return PORT_INSTANCE_ERROR
            return port_instance
        else:
            helper_logger.log_warning(
                "Error: Could not establish presence for  Y cable port {} while trying to toggle the mux".format(logical_port_name))
            return PORT_INSTANCE_ERROR

    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable table port {} while trying to toggle the mux".format(logical_port_name))
        return -1

def set_show_firmware_fields(port, mux_info_dict, xcvrd_show_fw_rsp_tbl):
    fvs = swsscommon.FieldValuePairs(
        [('version_self_active', str(mux_info_dict["version_self_active"])),
         ('version_self_inactive', str(mux_info_dict["version_self_inactive"])),
         ('version_self_next', str(mux_info_dict["version_self_next"])),
         ('version_peer_active', str(mux_info_dict["version_peer_active"])),
         ('version_peer_inactive', str(mux_info_dict["version_peer_inactive"])),
         ('version_peer_next', str(mux_info_dict["version_peer_next"])),
         ('version_nic_active', str(mux_info_dict["version_nic_active"])),
         ('version_nic_inactive', str(mux_info_dict["version_nic_inactive"])),
         ('version_nic_next', str(mux_info_dict["version_nic_next"]))
        ])
    xcvrd_show_fw_rsp_tbl.set(port, fvs)

    return 0



def check_mux_cable_port_type(logical_port_name, port_tbl, asic_index):

    (status, fvs) = port_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_debug(
            "Could not retreive fieldvalue pairs for {}, inside config_db table {}".format(logical_port_name, port_tbl[asic_index].getTableName()))
        return (False, None)

    else:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "state" in mux_table_dict:

            val = mux_table_dict.get("state", None)
            cable_type = mux_table_dict.get("cable_type", None)

            if val in CONFIG_MUX_STATES:
                if cable_type == "active-active":
                    helper_logger.log_debug("Y_CABLE_DEBUG:check_mux_cable_port_type returning True active-active port {}".format(logical_port_name))
                    return (True , "active-active")
                else:
                    helper_logger.log_debug("Y_CABLE_DEBUG:check_mux_cable_port_type returning True active-standby port {}".format(logical_port_name))
                    return (True, "active-standby")
        else:
            helper_logger.log_debug("Y_CABLE_DEBUG:check_mux_cable_port_type returning False None port {}".format(logical_port_name))
            return (False, None)


def hook_grpc_nic_simulated(target, soc_ip):
    """
    Args:
        target (function): The function collecting transceiver info.
    """

    #NIC_SIMULATOR_CONFIG_FILE = "/etc/sonic/nic_simulator.json"

    def wrapper(*args, **kwargs):
        #res = target(*args, **kwargs)
        if os.path.exists(MUX_SIMULATOR_CONFIG_FILE):
            """setup channels for all downlinks
            NIC simulator will run on same port number
            Todo put a task for secure channel"""
            channel = grpc.insecure_channel("server_ip:GRPC_PORT".format(host))
            stub = None
            #metadata_interceptor = MetadataInterceptor(("grpc_server", soc_ipv4))
            #intercept_channel = grpc.intercept_channel(channel, metadata_interceptor)
            #stub = linkmgr_grpc_driver_pb2_grpc.DualToRActiveStub(intercept_channel)
            # TODO hook the interceptor appropriately
        return channel, stub

    wrapper.__name__ = target.__name__

    return wrapper

def retry_setup_grpc_channel_for_port(port, asic_index, port_tbl, grpc_client, fwd_state_response_tbl):

    global grpc_port_stubs
    global grpc_port_channels

    (status, fvs) = port_tbl[asic_index].get(port)
    if status is False:
        helper_logger.log_debug(
            "Could not retreive fieldvalue pairs for {}, inside config_db table {}".format(port, port_tbl[asic_index].getTableName()))
        return False

    else:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "state" in mux_table_dict and "soc_ipv4" in mux_table_dict:

            soc_ipv4_full = mux_table_dict.get("soc_ipv4", None)
            if soc_ipv4_full is not None:
                soc_ipv4 = soc_ipv4_full.split('/')[0]

            channel, stub = setup_grpc_channel_for_port(port, soc_ipv4, asic_index, grpc_client, fwd_state_response_tbl, False)
            if channel is None or stub is None:
                helper_logger.log_notice(
                    "stub is None, while reattempt setting up channels did not work {}".format(port))
                return False
            else:
                grpc_port_channels[port] = channel
                grpc_port_stubs[port] = stub
                return True

def apply_grpc_secrets_configuration(SECRETS_PATH, grpc_config):


    f = open(SECRETS_PATH, 'rb')
    parsed_data = json.load(f)

    asic_index = multi_asic.get_asic_index_from_namespace(DEFAULT_NAMESPACE)
    grpc_client_config = parsed_data.get("GRPCCLIENT", None)
    if grpc_client_config is not None:
        config = grpc_client_config.get("config", None)
        if config is not None:
            type_chan = config.get("type",None)
            auth_level = config.get("auth_level",None)
            log_level = config.get("log_level", None)
            fvs_updated = swsscommon.FieldValuePairs([('type', type_chan),
                                                      ('auth_level',auth_level ),
                                                      ('log_level',log_level)])
            grpc_config[asic_index].set('config', fvs_updated)
        certs = grpc_client_config.get("certs", None)
        if certs is not None:
            client_crt = certs.get("client_crt", None)
            client_key = certs.get("client_key", None)
            ca_crt = certs.get("ca_crt", None)
            grpc_ssl_credential = certs.get("grpc_ssl_credential",None)
            fvs_updated = swsscommon.FieldValuePairs([('client_crt', client_crt),
                                                      ('client_key', client_key),
                                                      ('grpc_ssl_credential', grpc_ssl_credential),
                                                      ('ca_crt',ca_crt)])
            grpc_config[asic_index].set('certs', fvs_updated)
    

def get_grpc_credentials(type_chan, kvp):

    root_file = kvp.get("ca_crt", None)
    if root_file is not None and os.path.isfile(root_file): 
        root_cert = open(root_file, 'rb').read()
    else:
        helper_logger.log_error("grpc credential channel setup no root file in config_db")
        return None

    if type_chan == "mutual":
        cert_file = kvp.get("client_crt", None)
        if cert_file is not None and os.path.isfile(cert_file): 
            cert_chain = open(cert_file, 'rb').read()
        else:
            helper_logger.log_error("grpc credential channel setup no cert file for mutual authentication in config_db")
            return None

        key_file = kvp.get("client_key", None)
        if key_file is not None and os.path.isfile(key_file): 
            key = open(key_file, 'rb').read()
        else:
            helper_logger.log_error("grpc credential channel setup no key file for mutual authentication in config_db")
            return None

        credential = grpc.ssl_channel_credentials(
                root_certificates=root_cert,
                private_key=key,
                certificate_chain=cert_chain)
    elif type_chan == "server":
        credential = grpc.ssl_channel_credentials(
                root_certificates=root_cert)
    else:
        #should not happen
        helper_logger.log_error("grpc credential channel setup no type specified for authentication in config_db")
        return None

    return credential

def connect_channel(channel, stub, port):

    channel_ready = grpc.channel_ready_future(channel)
    retries = 3

    for _ in range(retries):
        try:
            channel_ready.result(timeout=2)
        except grpc.FutureTimeoutError:
            helper_logger.log_warning("gRPC port {} state changed to SHUTDOWN".format(port))
        else:
            break

def create_channel(type_chan, level, kvp, soc_ip, port, asic_index, fwd_state_response_tbl, is_async):

    # Helper callback to get an channel connectivity state
    def wait_for_state_change(channel_connectivity):
        if channel_connectivity == grpc.ChannelConnectivity.TRANSIENT_FAILURE:
            helper_logger.log_notice("gRPC port {} state changed to TRANSIENT_FAILURE".format(port))
            # for connectivity state to FAILURE/IDLE report a failure
            fvs_updated = swsscommon.FieldValuePairs([('response', 'failure')])
            fwd_state_response_tbl[asic_index].set(port, fvs_updated)
            grpc_port_connectivity[port] = "TRANSIENT_FAILURE"

        if channel_connectivity == grpc.ChannelConnectivity.CONNECTING:
            helper_logger.log_notice("gRPC port {} state changed to CONNECTING".format(port))
            grpc_port_connectivity[port] = "CONNECTING"
        if channel_connectivity == grpc.ChannelConnectivity.READY:
            helper_logger.log_notice("gRPC port {} state changed to READY".format(port))
            grpc_port_connectivity[port] = "READY"
        if channel_connectivity == grpc.ChannelConnectivity.IDLE:
            helper_logger.log_notice("gRPC port {} state changed to IDLE".format(port))
            # for connectivity state to FAILURE/IDLE report a failure
            fvs_updated = swsscommon.FieldValuePairs([('response', 'failure')])
            fwd_state_response_tbl[asic_index].set(port, fvs_updated) 
            grpc_port_connectivity[port] = "IDLE"

        if channel_connectivity == grpc.ChannelConnectivity.SHUTDOWN:
            helper_logger.log_notice("gRPC port {} state changed to SHUTDOWN".format(port))
            grpc_port_connectivity[port] = "SHUTDOWN"


    if type_chan == "secure":
        credential = get_grpc_credentials(level, kvp)
        target_name = kvp.get("grpc_ssl_credential", None)
        if credential is None or target_name is None:
            return (None, None)


        if is_async:
            ASYNC_GRPC_CLIENT_OPTIONS = []
            ASYNC_GRPC_CLIENT_OPTIONS.append(('grpc.ssl_target_name_override', '{}'.format(target_name)))
            channel = grpc.aio.secure_channel("{}:{}".format(soc_ip, GRPC_PORT), credential, options=ASYNC_GRPC_CLIENT_OPTIONS)
            stub = linkmgr_grpc_driver_pb2_grpc.DualToRActiveStub(channel)
        else:
            GRPC_CLIENT_OPTIONS.append(('grpc.ssl_target_name_override', '{}'.format(target_name)))
            channel = grpc.secure_channel("{}:{}".format(soc_ip, GRPC_PORT), credential, options=GRPC_CLIENT_OPTIONS)
            stub = linkmgr_grpc_driver_pb2_grpc.DualToRActiveStub(channel)


    else:
        if is_async:
            channel = grpc.aio.insecure_channel("{}:{}".format(soc_ip, GRPC_PORT))
            stub = linkmgr_grpc_driver_pb2_grpc.DualToRActiveStub(channel)
        else:
            channel = grpc.insecure_channel("{}:{}".format(soc_ip, GRPC_PORT), options=GRPC_CLIENT_OPTIONS)
            stub = linkmgr_grpc_driver_pb2_grpc.DualToRActiveStub(channel)




    if not is_async and channel is not None:
        channel.subscribe(wait_for_state_change)

    #connect_channel(channel, stub, port)
    """
    Comment the connect channel call for now, since it is not required for normal gRPC I/O
    and all use cases work without it.
    TODO: check if this subroutine call can be ommitted for all use cases in future enhancements
    """

    return channel, stub

def setup_grpc_channel_for_port(port, soc_ip, asic_index, grpc_config, fwd_state_response_tbl, is_async):

    """
    Dummy values for lab for now
    TODO remove these once done
    root_cert = open('/home/admin/proto_out1/proto_out/ca-chain-bundle.cert.pem', 'rb').read()
    key = open('/home/admin/proto_out1/proto_out/client.key.pem', 'rb').read()
    cert_chain = open('/home/admin/proto_out1/proto_out/client.cert.pem', 'rb').read()
    """
    """credential = grpc.ssl_channel_credentials(
            root_certificates=root_cert,
            private_key=key,
            certificate_chain=cert_chain)
    """
    helper_logger.log_notice("Setting up gRPC channel for RPC's {} {}".format(port,soc_ip))


    #if no config from config DB, treat channel to be as insecure
    type_chan = "insecure"
    level = "server"

    (status, fvs) = grpc_config[asic_index].get("config")
    if status is False:
        helper_logger.log_debug(
            "Could not retreive fieldvalue pairs for {}, inside config_db table kvp config for {} for setting up channel type".format(port, grpc_config[asic_index].getTableName()))
    else:
        grpc_config_dict = dict(fvs)
        type_chan = grpc_config_dict.get("type", None)
        level = grpc_config_dict.get("auth_level", None)
    
   
    kvp = {}
    if type_chan == "secure":
        (status, fvs) = grpc_config[asic_index].get("certs")
        if status is False:
            helper_logger.log_debug(
                "Could not retreive fieldvalue pairs for {}, inside config_db table kvp certs for {} for setting up channel type".format(port, grpc_config[asic_index].getTableName()))
            #if type is secure, must have certs defined
            return (None, None)
        kvp = dict(fvs)


    channel, stub = create_channel(type_chan, level, kvp, soc_ip, port, asic_index, fwd_state_response_tbl, is_async)

    if stub is None:
        helper_logger.log_warning("stub was not setup for gRPC soc ip {} port {}, no gRPC soc server running ?".format(soc_ip, port))
    if channel is None:
        helper_logger.log_warning("channel was not setup for gRPC soc ip {} port {}, no gRPC soc server running ?".format(soc_ip, port))

    return channel, stub

def put_init_values_for_grpc_states(port, read_side, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index):


    stub = grpc_port_stubs.get(port, None)
    request = linkmgr_grpc_driver_pb2.AdminRequest(portid=DEFAULT_PORT_IDS, state=[0, 0])
    if stub is None:
        helper_logger.log_notice("stub is None for getting admin port forwarding state RPC port {}".format(port))
        fvs_updated = swsscommon.FieldValuePairs([('state', 'unknown'),
                                                  ('read_side', str(read_side)),
                                                  ('active_side', 'unknown')])
        hw_mux_cable_tbl[asic_index].set(port, fvs_updated)
        hw_mux_cable_tbl_peer[asic_index].set(port, fvs_updated)
        return

    ret, response = try_grpc(stub.QueryAdminForwardingPortState, QUERY_ADMIN_FORWARDING_TIMEOUT, request)
    (self_state, peer_state) = parse_grpc_response_forwarding_state(ret, response, read_side, port)
    if response is not None:
        # Debug only, remove this section once Server side is Finalized
        fwd_response_port_ids = response.portid
        fwd_response_port_ids_state = response.state
        helper_logger.log_notice(
            "forwarding state RPC received response port ids = {} port {}".format(fwd_response_port_ids, port))
        helper_logger.log_notice(
            "forwarding state RPC received response state values = {} port {}".format(fwd_response_port_ids_state, port))
    else:
        helper_logger.log_warning("response was none while doing init config state for gRPC HW_MUX_CABLE_TABLE {} ".format(port))

    fvs_updated = swsscommon.FieldValuePairs([('state', self_state),
                                              ('read_side', str(read_side)),
                                              ('active_side', self_state)])
    hw_mux_cable_tbl[asic_index].set(port, fvs_updated)
    fvs_updated = swsscommon.FieldValuePairs([('state', peer_state),
                                              ('read_side', str(read_side)),
                                              ('active_side', peer_state)])
    hw_mux_cable_tbl_peer[asic_index].set(port, fvs_updated)

def process_loopback_interface_and_get_read_side(loopback_keys):

    asic_index = multi_asic.get_asic_index_from_namespace(DEFAULT_NAMESPACE)

    for key in loopback_keys[asic_index]:
        helper_logger.log_debug("Y_CABLE_DEBUG:Loopback key = {} ".format(key))
        if key.startswith("Loopback3|") and "/" in key and "::" not in key:
            helper_logger.log_debug("Y_CABLE_DEBUG:Loopback split  1 {} ".format(key))
            temp_list = key.split('|')
            addr = temp_list[1].split('/')[0]
            helper_logger.log_debug("Y_CABLE_DEBUG:Loopback split 2  {} ".format(addr))
            loopback_prefix = ipaddress.ip_network(UNICODE_TYPE(addr))
            loopback_address = str(loopback_prefix)
            helper_logger.log_debug("Y_CABLE_DEBUG:Loopback address parsed = {} ".format(loopback_address))
            if loopback_address == LOOPBACK_INTERFACE_LT0 or loopback_address == LOOPBACK_INTERFACE_LT0_NIC:
                return 0
            elif loopback_address == LOOPBACK_INTERFACE_T0 or loopback_address == LOOPBACK_INTERFACE_T0_NIC:
                return 1
            else:
                # Loopback3 should be present, if not present log a warning
                helper_logger.log_warning("Could not get any address associated with Loopback3")
                return -1

    return -1


def check_identifier_presence_and_setup_channel(logical_port_name, port_tbl, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index, read_side, mux_tbl, y_cable_presence, grpc_client, fwd_state_response_tbl):
    global grpc_port_stubs
    global grpc_port_channels

    (status, fvs) = port_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_debug(
            "Could not retreive fieldvalue pairs for {}, inside config_db table {}".format(logical_port_name, port_tbl[asic_index].getTableName()))
        return

    else:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "state" in mux_table_dict and "soc_ipv4" in mux_table_dict:

            val = mux_table_dict.get("state", None)
            soc_ipv4_full = mux_table_dict.get("soc_ipv4", None)
            if soc_ipv4_full is not None:
                soc_ipv4 = soc_ipv4_full.split('/')[0]
            cable_type = mux_table_dict.get("cable_type", None)

            if val in CONFIG_MUX_STATES and cable_type == "active-active":

                # import the module and load the port instance
                y_cable_presence[:] = [True]
                physical_port_list = logical_port_name_to_physical_port_list(
                    logical_port_name)

                if len(physical_port_list) == 1:

                    physical_port = physical_port_list[0]
                    if y_cable_wrapper_get_presence(physical_port):
                        prev_stub = grpc_port_stubs.get(logical_port_name, None)
                        prev_channel = grpc_port_channels.get(logical_port_name, None)
                        if prev_channel is not None and prev_stub is not None:
                            return

                        channel, stub = setup_grpc_channel_for_port(logical_port_name, soc_ipv4, asic_index, grpc_client, fwd_state_response_tbl, False)
                        post_port_mux_info_to_db(logical_port_name,  mux_tbl, asic_index, hw_mux_cable_tbl, 'pseudo-cable')
                        if channel is not None:
                            grpc_port_channels[logical_port_name] = channel
                            helper_logger.log_notice(
                                "channel is not None, Cable-Insert or daemon init, daemon able to set up channel for gRPC SOC IP {}, port {}".format(soc_ipv4, logical_port_name))
                        if stub is not None:
                            grpc_port_stubs[logical_port_name] = stub
                            helper_logger.log_notice(
                                "stub is not None, Cable-Insert or daemon init, daemon able to set up channel for gRPC SOC IP {}, port {}".format(soc_ipv4, logical_port_name))

                    else:
                        helper_logger.log_warning(
                            "DAC cable not present while Channel setup Port {} for gRPC channel initiation".format(logical_port_name))

                    put_init_values_for_grpc_states(logical_port_name, read_side, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index)

                else:
                    helper_logger.log_warning(
                        "DAC cable logical to physical port mapping returned more than one physical ports while Channel setup Port {}".format(logical_port_name))
            else:
                helper_logger.log_warning(
                    "DAC cable logical to physical port mapping returned more than one physical ports while Channel setup Port {}".format(logical_port_name))


def setup_grpc_channels(stop_event, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, port_tbl, loopback_tbl, port_table_keys, grpc_client, fwd_state_response_tbl):

    global read_side
    helper_logger.log_debug("Y_CABLE_DEBUG:setting up channels for active-active")
    config_db, state_db, port_tbl, loopback_tbl, port_table_keys = {}, {}, {}, {}, {}
    loopback_keys = {}
    hw_mux_cable_tbl = {}
    hw_mux_cable_tbl_peer = {}
    mux_tbl = {}

    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        config_db[asic_id] = daemon_base.db_connect("CONFIG_DB", namespace)
        port_tbl[asic_id] = swsscommon.Table(config_db[asic_id], "MUX_CABLE")
        loopback_tbl[asic_id] = swsscommon.Table(
            config_db[asic_id], "LOOPBACK_INTERFACE")
        loopback_keys[asic_id] = loopback_tbl[asic_id].getKeys()
        port_table_keys[asic_id] = port_tbl[asic_id].getKeys()
        state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
        hw_mux_cable_tbl[asic_id] = swsscommon.Table(
            state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
        hw_mux_cable_tbl_peer[asic_id] = swsscommon.Table(
            state_db[asic_id], "HW_MUX_CABLE_TABLE_PEER")
        mux_tbl[asic_id] = swsscommon.Table(
                state_db[asic_id], "MUX_CABLE_INFO")

    if read_side == -1:
        read_side = process_loopback_interface_and_get_read_side(loopback_keys)
        if os.path.isfile(SECRETS_PATH):
            apply_grpc_secrets_configuration(SECRETS_PATH, grpc_client)

    helper_logger.log_debug("Y_CABLE_DEBUG:while setting up grpc channels read side = {}".format(read_side))

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
            check_identifier_presence_and_setup_channel(
                logical_port_name, port_tbl, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index, read_side, mux_tbl, y_cable_presence, grpc_client, fwd_state_response_tbl)
        else:
            # This port does not exist in Port table of config but is present inside
            # logical_ports after loading the port_mappings from port_config_file
            # This should not happen
            helper_logger.log_warning(
                "Could not retreive port inside config_db PORT table {} for gRPC channel initiation".format(logical_port_name))


def try_grpc(callback, rpc_timeout, *args, **kwargs):
    """
    Handy function to invoke the callback and catch NotImplementedError
    :param callback: Callback to be invoked
    :param rpc_timeout: timeout for RPC in seconds
    :param args: Arguments to be passed to callback
    :param kwargs: Default return value if exception occur
    :return: Default return value if exception occur else return value of the callback
    """

    return_val = True
    try:
        if rpc_timeout is not None:
            resp = callback(*args, timeout=rpc_timeout)
        else:
            resp = callback(*args)

        if resp is None:
            return_val = False
    except grpc.RpcError as e:
        #err_msg = 'Grpc error code '+str(e.code())
        if e.code() == grpc.StatusCode.CANCELLED:
            helper_logger.log_notice("rpc cancelled for port= {}".format(str(e.code())))
        elif e.code() == grpc.StatusCode.UNAVAILABLE:
            helper_logger.log_notice("rpc unavailable for port= {}".format(str(e.code())))
        elif e.code() == grpc.StatusCode.INVALID_ARGUMENT:
            helper_logger.log_notice("rpc invalid arguement for port= {}".format(str(e.code())))
        elif e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            helper_logger.log_notice("rpc timeout exceeded for port= {} timeout = {}".format(str(e.code()), rpc_timeout))
        else:
            helper_logger.log_notice("rpc exception error for port= {}".format(str(e.code())))
        resp = None
        return_val = False

    return return_val, resp


def close(channel):
    "Close the channel"
    channel.close()

def set_result_and_delete_port(result, actual_result, command_table, response_table, port):
    fvs = swsscommon.FieldValuePairs([(result, str(actual_result))])
    response_table.set(port, fvs)
    command_table._del(port)

# Delete port from Y cable status table
def delete_port_from_y_cable_table(logical_port_name, y_cable_tbl):
    if y_cable_tbl is not None:
        y_cable_tbl._del(logical_port_name)


def update_table_mux_status_for_response_tbl(table_name, status, logical_port_name):
    fvs = swsscommon.FieldValuePairs([('response', status)])
    table_name.set(logical_port_name, fvs)

    helper_logger.log_debug("Y_CABLE_DEBUG: Successful in returning probe port status {}".format(logical_port_name))


def update_table_mux_status_for_statedb_port_tbl(table_name, status, read_side, active_side, logical_port_name):
    fvs = swsscommon.FieldValuePairs([('state', status),
                                      ('read_side', str(read_side)),
                                      ('active_side', str(active_side))])
    table_name.set(logical_port_name, fvs)


def y_cable_toggle_mux_torA(physical_port):
    port_instance = y_cable_port_instances.get(physical_port)
    if port_instance is None:
        helper_logger.log_error(
            "Error: Could not get port instance for read side for  Y cable port {} {}".format(physical_port, threading.currentThread().getName()))
        return -1

    try:
        update_status = port_instance.toggle_mux_to_tor_a()
    except Exception as e:
        update_status = -1
        helper_logger.log_warning("Failed to execute the toggle mux ToR A API for port {} due to {} {}".format(physical_port, repr(e) , threading.currentThread().getName()))

    helper_logger.log_debug("Y_CABLE_DEBUG: Status of toggling mux to ToR A for port {} status {} {}".format(physical_port, update_status, threading.currentThread().getName()))
    if update_status is True:
        return 1
    else:
        helper_logger.log_warning(
            "Error: Could not toggle the mux for port {} to torA write eeprom failed".format(physical_port))
        return -1


def y_cable_toggle_mux_torB(physical_port):
    port_instance = y_cable_port_instances.get(physical_port)
    if port_instance is None:
        helper_logger.log_error("Error: Could not get port instance for read side for  Y cable port {} {}".format(physical_port, threading.currentThread().getName()))
        return -1

    try:
        update_status = port_instance.toggle_mux_to_tor_b()
    except Exception as e:
        update_status = -1
        helper_logger.log_warning("Failed to execute the toggle mux ToR B API for port {} due to {} {}".format(physical_port,repr(e), threading.currentThread().getName()))

    helper_logger.log_debug("Y_CABLE_DEBUG: Status of toggling mux to ToR B for port {} {} {}".format(physical_port, update_status, threading.currentThread().getName()))
    if update_status is True:
        return 2
    else:
        helper_logger.log_warning(
            "Error: Could not toggle the mux for port {} to torB write eeprom failed".format(physical_port))
        return -1


def toggle_mux_direction(physical_port, read_side, state):

    if int(read_side) == 1:
        if state == "active":
            return (y_cable_toggle_mux_torA(physical_port), read_side)
        elif state == "standby":
            return (y_cable_toggle_mux_torB(physical_port), read_side)
    elif int(read_side) == 2:
        if state == "active":
            return (y_cable_toggle_mux_torB(physical_port), read_side)
        elif state == "standby":
            return (y_cable_toggle_mux_torA(physical_port), read_side)

def toggle_mux_tor_direction_and_update_read_side(state, logical_port_name, physical_port):

    port_instance = y_cable_port_instances.get(physical_port)
    if port_instance is None:
        helper_logger.log_error("Error: Could not get port instance for read side for while processing a toggle Y cable port {} {}".format(physical_port, threading.currentThread().getName()))
        return (-1, -1)

    try:
        read_side = port_instance.get_read_side()
    except Exception as e:
        read_side = None
        helper_logger.log_warning("Failed to execute the get_read_side API for port {} due to {} from update_read_side".format(logical_port_name,repr(e)))

    if read_side is None or read_side is port_instance.EEPROM_ERROR or read_side < 0:
        helper_logger.log_error(
            "Error: Could not get read side for toggle command from orchagent Y cable port {}".format(logical_port_name))
        return (-1, -1)
    if int(read_side) == 1 or int(read_side) == 2:
        (active_side, read_side) = toggle_mux_direction(physical_port, read_side, state)
        return (active_side, read_side)
    else:
        #should not happen
        return (-1,-1)

"""
def poll_active_side_after_toggle(logical_port_name, read_side, requested_state, time_switchover_start):
    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)
        

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if physical_port != 1:
            return
        port_instance = y_cable_port_instances.get(physical_port)

        required_side = 0
        if read_side == '1':
            if requested_state == "active":
                required_side = 1
            if requested_state == "standby":
                required_side = 2
        elif read_side == '2':
            if requested_state == "active":
                required_side = 2
            if requested_state == "standby":
                required_side = 1
        else:
            return

        time_start = time.time()
        count = 0
        while True:
            count = count + 1
            curr_active_side = port_instance.get_mux_direction()
            time_now = time.time()
            time_diff = time_now - time_start
            if curr_active_side == required_side:
                break
            elif time_diff >= TOGGLE_TIMEOUT:
                helper_logger.log_warning(
                    "Error: Could not toggle the mux for port {} {} to torA write eeprom timeout time taken {}, count: {}".format(physical_port, logical_port_name, time_now-time_switchover_start, count))
                return -1

            time.sleep(0.001)

        time_taken = time.time() - time_switchover_start
        helper_logger.log_warning(
            "Sucessfully toggled the mux after polling port to required side {} {} {} {}, count: {}".format(physical_port, required_side, logical_port_name, time_taken, count))
        return 1
    else:
        error_time = time.time() - time_switchover_start
        helper_logger.log_warning(
            "Error: Could not toggle the mux for port {} to torA write eeprom failed time taken {}".format(physical_port, error_time))
"""


def update_tor_active_side(read_side, state, logical_port_name):
    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if y_cable_wrapper_get_presence(physical_port):
            if int(read_side) == 1 or int(read_side) == 2:
                (active_side, read_side) = toggle_mux_direction(physical_port, read_side, state)
                return (active_side, read_side)
            else:
                # not a valid read side
                (active_side, read_side) = toggle_mux_tor_direction_and_update_read_side(state, logical_port_name, physical_port)
                return (active_side, read_side)

            # TODO: Should we confirm that the mux was indeed toggled?

        else:
            helper_logger.log_warning(
                "Error: Could not establish presence for  Y cable port {} while trying to toggle the mux".format(logical_port_name))
            return (-1, -1)

    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable table port {} while trying to toggle the mux".format(logical_port_name))
        return (-1, -1)


def update_appdb_port_mux_cable_response_table(logical_port_name, asic_index, appl_db, read_side, y_cable_response_tbl):

    status = None
    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)

    if len(physical_port_list) == 1:

        physical_port = physical_port_list[0]
        if y_cable_wrapper_get_presence(physical_port):

            port_instance = y_cable_port_instances.get(physical_port)
            if port_instance is None or port_instance == -1:
                status = 'unknown'
                update_table_mux_status_for_response_tbl(y_cable_response_tbl[asic_index], status, logical_port_name)
                helper_logger.log_error(
                    "Error: Could not get port instance to perform update appdb for read side for Y cable port {}".format(logical_port_name))
                return

            if read_side is None:

                status = 'unknown'
                update_table_mux_status_for_response_tbl(y_cable_response_tbl[asic_index], status, logical_port_name)
                helper_logger.log_warning(
                    "Error: Could not get read side to perform update appdb for mux cable port probe command logical port {} and physical port {}".format(logical_port_name, physical_port))
                return

            active_side = None
            try:
                active_side = port_instance.get_mux_direction()
            except Exception as e:
                active_side = -1
                helper_logger.log_warning("Failed to execute the get_mux_direction for port {} due to {}".format(physical_port,repr(e)))

            if active_side is None or active_side == port_instance.EEPROM_ERROR or active_side < 0 :

                status = 'unknown'
                update_table_mux_status_for_response_tbl(y_cable_response_tbl[asic_index], status, logical_port_name)
                helper_logger.log_warning(
                    "Error: Could not get active side to perform update appdb for mux cable port probe command logical port {} and physical port {}".format(logical_port_name, physical_port))
                return

            if read_side == active_side and (active_side == 1 or active_side == 2):
                status = 'active'
            elif read_side != active_side and (active_side == 1 or active_side == 2):
                status = 'standby'
            else:
                status = 'unknown'
                helper_logger.log_warning(
                    "Error: Could not get state to perform update appdb for mux cable port probe command logical port {} and physical port {}".format(logical_port_name, physical_port))

            helper_logger.log_debug("Y_CABLE_DEBUG: notifying a probe for port status {} {}".format(logical_port_name, status))

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
        if y_cable_wrapper_get_presence(physical_port):

            port_instance = y_cable_port_instances.get(physical_port)
            if port_instance is None or port_instance == -1:
                read_side = active_side = -1
                update_table_mux_status_for_statedb_port_tbl(
                    mux_config_tbl, "unknown", read_side, active_side, logical_port_name)
                helper_logger.log_error(
                    "Error: Could not get port instance to perform read_y_cable update state db for read side for  Y cable port {}".format(logical_port_name))
                return

            with y_cable_port_locks[physical_port]:
                try:
                    read_side = port_instance.get_read_side()
                except Exception as e:
                    read_side = None
                    helper_logger.log_warning("Failed to execute the get_read_side for port {} due to {}".format(physical_port,repr(e)))

            if read_side is None or read_side < 0 or read_side == port_instance.EEPROM_ERROR:
                read_side = active_side = -1
                update_table_mux_status_for_statedb_port_tbl(
                    mux_config_tbl, "unknown", read_side, active_side, logical_port_name)
                helper_logger.log_error(
                    "Error: Could not establish the read side for Y cable port {} to perform read_y_cable update state db".format(logical_port_name))
                return

            with y_cable_port_locks[physical_port]:
                try:
                    active_side = port_instance.get_mux_direction()
                except Exception as e:
                    active_side = None
                    helper_logger.log_warning("Failed to execute the get_mux_direction for port {} due to {}".format(physical_port,repr(e)))

            if active_side is None or active_side not in y_cable_switch_state_values:
                active_side = -1
                update_table_mux_status_for_statedb_port_tbl(
                    mux_config_tbl, "unknown", read_side, active_side, logical_port_name)
                helper_logger.log_error(
                    "Error: Could not establish the active side for Y cable port {} to perform read_y_cable update state db".format(logical_port_name))
                return

            if read_side == active_side and (active_side == 1 or active_side == 2):
                status = 'active'
            elif read_side != active_side and (active_side == 1 or active_side == 2):
                status = 'standby'
            else:
                status = 'unknown'
                helper_logger.log_warning(
                    "Error: Could not establish the active status for Y cable port {} to perform read_y_cable update state db".format(logical_port_name))

            update_table_mux_status_for_statedb_port_tbl(
                mux_config_tbl, status, read_side, active_side, logical_port_name)
            return

        else:
            read_side = active_side = -1
            update_table_mux_status_for_statedb_port_tbl(
                mux_config_tbl, "unknown", read_side, active_side, logical_port_name)
            helper_logger.log_warning(
                "Error: Could not establish presence for  Y cable port {} to perform read_y_cable update state db".format(logical_port_name))
    else:
        # Y cable ports should always have
        # one to one mapping of physical-to-logical
        # This should not happen
        read_side = active_side = -1
        update_table_mux_status_for_statedb_port_tbl(
            mux_config_tbl, "unknown", read_side, active_side, logical_port_name)
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable port {} to perform read_y_cable update state db".format(logical_port_name))

def create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name):

    # fill the newly found entry
    read_y_cable_and_update_statedb_port_tbl(
        logical_port_name, y_cable_tbl[asic_index])
    post_port_mux_static_info_to_db(
        logical_port_name, static_tbl[asic_index], y_cable_tbl)

def check_identifier_presence_and_update_mux_table_entry(state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence):

    global y_cable_port_instances
    global y_cable_port_locks
    (status, fvs) = port_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_debug(
            "Could not retreive fieldvalue pairs for {}, inside config_db table {}".format(logical_port_name, port_tbl[asic_index].getTableName()))
        return

    else:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "state" in mux_table_dict:

            val = mux_table_dict.get("state", None)

            if val in CONFIG_MUX_STATES:

                # import the module and load the port instance
                physical_port_list = logical_port_name_to_physical_port_list(
                    logical_port_name)

                if len(physical_port_list) == 1:

                    physical_port = physical_port_list[0]
                    if y_cable_wrapper_get_presence(physical_port):
                        port_info_dict = y_cable_wrapper_get_transceiver_info(
                            physical_port)
                        if port_info_dict is not None:
                            vendor = port_info_dict.get('manufacturer')

                            if vendor is None:
                                helper_logger.log_warning(
                                    "Error: Unable to find Vendor name for Transceiver for Y-Cable initiation {}".format(logical_port_name))
                                create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)
                                return

                            model = port_info_dict.get('model')

                            if model is None:
                                helper_logger.log_warning(
                                    "Error: Unable to find model name for Transceiver for Y-Cable initiation {}".format(logical_port_name))
                                create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)
                                return

                            vendor = format_mapping_identifier(vendor)
                            model = format_mapping_identifier(model)
                            module_dir = y_cable_vendor_mapping.mapping.get(vendor)

                            if module_dir is None:
                                helper_logger.log_warning(
                                    "Error: Unable to find module dir name from vendor for Y-Cable initiation {}".format(logical_port_name))
                                create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)
                                return

                            module = module_dir.get(model)
                            if module is None:
                                helper_logger.log_warning(
                                    "Error: Unable to find module name from model for Y-Cable initiation {}".format(logical_port_name))
                                create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)
                                return

                            attr_name = 'sonic_y_cable.' + module
                            try:
                                y_cable_attribute = getattr(import_module(attr_name), 'YCable')
                            except Exception as e:
                                helper_logger.log_warning("Failed to load the attr due to {}".format(repr(e)))
                                create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)
                                return
                            if y_cable_attribute is None:
                                helper_logger.log_warning(
                                    "Error: Unable to import attr name for Y-Cable initiation {}".format(logical_port_name))
                                create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)
                                return

                            y_cable_port_instances[physical_port] = y_cable_attribute(physical_port, helper_logger)
                            y_cable_port_locks[physical_port] = threading.Lock()
                            with y_cable_port_locks[physical_port]:
                                try:
                                    vendor_name_api = y_cable_port_instances.get(physical_port).get_vendor()
                                except Exception as e:
                                    helper_logger.log_warning("Failed to call the get_vendor API for port {} due to {}".format(physical_port,repr(e)))
                                    create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)
                                    return

                            if format_mapping_identifier(vendor_name_api) != vendor:
                                y_cable_port_instances.pop(physical_port)
                                y_cable_port_locks.pop(physical_port)
                                create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)
                                helper_logger.log_warning("Error: Y Cable api does not work for {}, {} actual vendor name {}".format(
                                    logical_port_name, vendor_name_api, vendor))
                                return

                            y_cable_asic_table = y_cable_tbl.get(
                                asic_index, None)
                            mux_asic_table = mux_tbl.get(asic_index, None)
                            static_mux_asic_table = static_tbl.get(
                                asic_index, None)
                            if y_cable_presence[0] is True and y_cable_asic_table is not None and mux_asic_table is not None and static_mux_asic_table is not None:
                                # fill in the newly found entry
                                read_y_cable_and_update_statedb_port_tbl(
                                    logical_port_name, y_cable_tbl[asic_index])
                                post_port_mux_static_info_to_db(
                                    logical_port_name, static_tbl[asic_index], y_cable_tbl)

                            else:
                                # first create the state db y cable table and then fill in the entry
                                y_cable_presence[:] = [True]
                                # fill the newly found entry
                                read_y_cable_and_update_statedb_port_tbl(
                                    logical_port_name, y_cable_tbl[asic_index])
                                post_port_mux_info_to_db(
                                    logical_port_name,  mux_tbl, asic_index, y_cable_tbl, 'active-standby')
                                post_port_mux_static_info_to_db(
                                    logical_port_name, static_tbl[asic_index], y_cable_tbl)
                        else:
                            helper_logger.log_warning(
                                "Error: Could not get transceiver info dict Y cable port {} while inserting entries".format(logical_port_name))
                            create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)

                    else:
                        helper_logger.log_warning(
                            "Error: Could not establish transceiver presence for a Y cable port {} while inserting entries".format(logical_port_name))
                        create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)

                else:
                    helper_logger.log_warning(
                        "Error: Retreived multiple ports for a Y cable port {} while inserting entries".format(logical_port_name))
                    create_tables_and_insert_mux_unknown_entries(state_db, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name)

            else:
                helper_logger.log_warning(
                    "Could not retreive active or auto value for state kvp for {}, inside MUX_CABLE table".format(logical_port_name))

        else:
            helper_logger.log_warning(
                "Could not retreive state value inside mux_info_dict for {}, inside MUX_CABLE table".format(logical_port_name))


def check_identifier_presence_and_delete_mux_table_entry(state_db, port_tbl, asic_index, logical_port_name, y_cable_presence, delete_change_event, y_cable_tbl, static_tbl, mux_tbl):

    # if there is No Y cable do not do anything here
    if y_cable_presence[0] is False:
        return

    (status, fvs) = port_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_debug(
            "Could not retreive fieldvalue pairs for {}, inside config_db table {}".format(logical_port_name, port_tbl[asic_index].getTableName()))
        return

    else:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "state" in mux_table_dict:
            if y_cable_presence[0] is True:
                # delete this entry in the y cable table found and update the delete event
                #We dont delete the values here, rather just update the values in state DB
                (status, fvs) = y_cable_tbl[asic_index].get(logical_port_name)
                if status is False:
                    helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table {} while deleting mux entry".format(
                        logical_port_name, y_cable_tbl[asic_index].getTableName()))
                mux_port_dict = dict(fvs)
                read_side = mux_port_dict.get("read_side", None)
                active_side = -1
                update_table_mux_status_for_statedb_port_tbl(
                    y_cable_tbl[asic_index], "unknown", read_side, active_side, logical_port_name)
                #delete_port_from_y_cable_table(logical_port_name, static_tbl[asic_index])
                #delete_port_from_y_cable_table(logical_port_name, mux_tbl[asic_index])
                delete_change_event[:] = [True]
                # delete the y_cable instance
                physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)

                if len(physical_port_list) == 1:

                    physical_port = physical_port_list[0]
                    if y_cable_port_instances.get(physical_port) is not None:
                        y_cable_port_instances.pop(physical_port)
                    if y_cable_port_instances.get(physical_port) is not None:
                        y_cable_port_locks.pop(physical_port)
                else:
                    helper_logger.log_warning(
                        "Error: Retreived multiple ports for a Y cable port {} while delete entries".format(logical_port_name))


def init_ports_status_for_y_cable(platform_sfp, platform_chassis, y_cable_presence, state_db ,port_tbl, y_cable_tbl, static_tbl, mux_tbl, port_table_keys,  loopback_keys , hw_mux_cable_tbl, hw_mux_cable_tbl_peer, grpc_client, fwd_state_response_tbl, stop_event=threading.Event(), is_vs=False):
    global y_cable_platform_sfputil
    global y_cable_platform_chassis
    global y_cable_port_instances
    global y_cable_is_platform_vs
    global read_side
    # Connect to CONFIG_DB and create port status table inside state_db

    y_cable_platform_sfputil = platform_sfp
    y_cable_platform_chassis = platform_chassis
    y_cable_is_platform_vs = is_vs


    if read_side == -1:
        read_side = process_loopback_interface_and_get_read_side(loopback_keys)
        if os.path.isfile(SECRETS_PATH):
            apply_grpc_secrets_configuration(SECRETS_PATH, grpc_client)

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
            (status, cable_type) = check_mux_cable_port_type(logical_port_name, port_tbl, asic_index)
            if status and cable_type == "active-standby":
                check_identifier_presence_and_update_mux_table_entry(
                    state_db, port_tbl, hw_mux_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
            if status and cable_type == "active-active":
                grpc_port_stats[logical_port_name] = {}
                check_identifier_presence_and_setup_channel(
                    logical_port_name, port_tbl, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index, read_side, mux_tbl, y_cable_presence, grpc_client, fwd_state_response_tbl)
        else:
            # This port does not exist in Port table of config but is present inside
            # logical_ports after loading the port_mappings from port_config_file
            # This should not happen
            helper_logger.log_warning(
                "Could not retreive port inside config_db PORT table {} for Y-Cable initiation".format(logical_port_name))


def change_ports_status_for_y_cable_change_event(port_dict, y_cable_presence, port_tbl, port_table_keys, loopback_tbl, loopback_keys, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, y_cable_tbl, static_tbl, mux_tbl, grpc_client, fwd_state_response_tbl, state_db, stop_event=threading.Event()):

    global read_side
    delete_change_event = [False]


    if read_side == -1:
        read_side = process_loopback_interface_and_get_read_side(loopback_keys)
        if os.path.isfile(SECRETS_PATH):
            apply_grpc_secrets_configuration(SECRETS_PATH, grpc_client)


    # Init PORT_STATUS table if ports are on Y cable and an event is received
    for logical_port_name, value in port_dict.items():
        if stop_event.is_set():
            break

        # Get the asic to which this port belongs
        asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(logical_port_name)
        if asic_index is None:
            helper_logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
            continue

        if logical_port_name in port_table_keys[asic_index]:
            if value == SFP_STATUS_INSERTED:
                helper_logger.log_info("Got SFP inserted ycable event")
                (status, cable_type) = check_mux_cable_port_type(logical_port_name, port_tbl, asic_index)
                if status and cable_type == "active-standby":
                    check_identifier_presence_and_update_mux_table_entry(
                        state_db, port_tbl, y_cable_tbl, static_tbl, mux_tbl, asic_index, logical_port_name, y_cable_presence)
                if status and cable_type == "active-active":
                    check_identifier_presence_and_setup_channel(
                        logical_port_name, port_tbl, hw_mux_cable_tbl, hw_mux_cable_tbl_peer, asic_index, read_side, mux_tbl,  y_cable_presence, grpc_client, fwd_state_response_tbl)
            elif value == SFP_STATUS_REMOVED:
                helper_logger.log_info("Got SFP deleted ycable event")
                check_identifier_presence_and_delete_mux_table_entry(
                    state_db, port_tbl, asic_index, logical_port_name, y_cable_presence, delete_change_event, y_cable_tbl, static_tbl, mux_tbl)
            else:
                try:
                    # Now that the value is in bitmap format, let's convert it to number
                    event_bits = int(value)
                    if event_bits in errors_block_eeprom_reading:
                        check_identifier_presence_and_delete_mux_table_entry(
                            state_db, port_tbl, asic_index, logical_port_name, y_cable_presence, delete_change_event, y_cable_tbl, static_tbl, mux_tbl)
                except (TypeError, ValueError) as e:
                    helper_logger.log_error("Got unrecognized event {}, ignored".format(value))

                # SFP return unkown event, just ignore for now.
                helper_logger.log_warning("Got unknown event {}, ignored".format(value))
                continue

    # If there was a delete event and y_cable_presence was true, reaccess the y_cable presence
    if y_cable_presence[0] is True and delete_change_event[0] is True:

        y_cable_presence[:] = [False]
        state_db = {}
        yc_hw_mux_cable_table = {}
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            asic_id = multi_asic.get_asic_index_from_namespace(
                namespace)
            state_db[asic_id] = daemon_base.db_connect("STATE_DB", namespace)
            yc_hw_mux_cable_table[asic_id] = swsscommon.Table(
                state_db[asic_id], swsscommon.STATE_HW_MUX_CABLE_TABLE_NAME)
            y_cable_table_size = len(yc_hw_mux_cable_table[asic_id].getKeys())
            if y_cable_table_size > 0:
                y_cable_presence[:] = [True]
                break


def delete_ports_status_for_y_cable(y_cable_tbl, static_tbl, mux_tbl, port_tbl, grpc_config):

    y_cable_tbl_keys = {}

    namespaces = multi_asic.get_front_end_namespaces()
    for namespace in namespaces:
        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
        y_cable_tbl_keys[asic_id] = y_cable_tbl[asic_id].getKeys()

    if read_side != -1:
        asic_index = multi_asic.get_asic_index_from_namespace(DEFAULT_NAMESPACE)
        if os.path.isfile(SECRETS_PATH):
            grpc_config[asic_index]._del("config")
            grpc_config[asic_index]._del("certs")

    # delete PORTS on Y cable table if ports on Y cable
    logical_port_list = y_cable_platform_sfputil.logical
    for logical_port_name in logical_port_list:

        # Get the asic to which this port belongs
        asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(
            logical_port_name)
        if asic_index is None:
            helper_logger.log_warning(
                "Got invalid asic index for {}, ignored".format(logical_port_name))

        if logical_port_name in y_cable_tbl_keys[asic_index]:
            delete_port_from_y_cable_table(logical_port_name, y_cable_tbl[asic_index])
            delete_port_from_y_cable_table(logical_port_name, static_tbl[asic_index])
            delete_port_from_y_cable_table(logical_port_name, mux_tbl[asic_index])
            # delete the y_cable port instance
            physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)

            if len(physical_port_list) == 1:

                physical_port = physical_port_list[0]
                if y_cable_port_instances.get(physical_port) is not None:
                    y_cable_port_instances.pop(physical_port)
                if y_cable_port_locks.get(physical_port) is not None:
                    y_cable_port_locks.pop(physical_port)
            else:
                helper_logger.log_warning(
                    "Error: Retreived multiple ports for a Y cable port {} while deleting entries".format(logical_port_name))


def check_identifier_presence_and_update_mux_info_entry(state_db, mux_tbl, asic_index, logical_port_name, y_cable_tbl, port_tbl):

    global disable_telemetry

    if disable_telemetry == True:
       return


    (status, fvs) = port_tbl[asic_index].get(logical_port_name)
    (cable_status, cable_type) = check_mux_cable_port_type(logical_port_name, port_tbl, asic_index)

    if status is False:
        helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside config_db table {}".format(logical_port_name, port_tbl[asic_index].getTableName()))
        return

    elif cable_status is True:
        # Convert list of tuples to a dictionary
        mux_table_dict = dict(fvs)
        if "state" in mux_table_dict:
            val = mux_table_dict.get("state", None)
            if val in CONFIG_MUX_STATES:

                if mux_tbl.get(asic_index, None) is not None:
                    # fill in the newly found entry
                    post_port_mux_info_to_db(logical_port_name,  mux_tbl, asic_index, y_cable_tbl, cable_type)

                else:
                    # first create the state db y cable table and then fill in the entry
                    namespaces = multi_asic.get_front_end_namespaces()
                    for namespace in namespaces:
                        asic_id = multi_asic.get_asic_index_from_namespace(namespace)
                        mux_tbl[asic_id] = swsscommon.Table(state_db[asic_id], MUX_CABLE_INFO_TABLE)
                    # fill the newly found entry
                    post_port_mux_info_to_db(logical_port_name,  mux_tbl, asic_index, y_cable_tbl, cable_type)
            else:
                helper_logger.log_warning(
                    "Could not retreive active or auto value for state kvp for {}, inside MUX_CABLE table".format(logical_port_name))


def get_firmware_dict(physical_port, port_instance, target, side, mux_info_dict, logical_port_name, mux_tbl):

    result = {}
    if port_instance.download_firmware_status == port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS:

        # if there is a firmware download in progress, retreive the last known firmware
        mux_firmware_dict = {}

        asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(
            logical_port_name)

        (status, fvs) = mux_tbl[asic_index].get(logical_port_name)
        if status is False:
            helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(logical_port_name, mux_tbl[asic_index].getTableName()))
            mux_info_dict[("version_{}_active".format(side))] = "N/A"
            mux_info_dict[("version_{}_inactive".format(side))] = "N/A"
            mux_info_dict[("version_{}_next".format(side))] = "N/A"
            return

        mux_firmware_dict = dict(fvs)

        mux_info_dict[("version_{}_active".format(side))] = mux_firmware_dict.get(("version_{}_active".format(side)), None)
        mux_info_dict[("version_{}_inactive".format(side))] = mux_firmware_dict.get(("version_{}_inactive".format(side)), None)
        mux_info_dict[("version_{}_next".format(side))] = mux_firmware_dict.get(("version_{}_next".format(side)), None)

        helper_logger.log_warning(
            "trying to get/post firmware info while download/toggle in progress returning with last known firmware without execute {}".format(physical_port))
        return

    elif port_instance.download_firmware_status == port_instance.FIRMWARE_DOWNLOAD_STATUS_FAILED:
        # if there is a firmware download failed, retreive the current MCU's firmware with a log message
        helper_logger.log_error(
            "Firmware Download API failed in the previous run, firmware download status was set to failed;retry required {}".format(physical_port))

    with y_cable_port_locks[physical_port]:
        try:
            result = port_instance.get_firmware_version(target)
        except Exception as e:
            result = None
            helper_logger.log_warning("Failed to execute the get_firmware_version API for port {} side {} due to {}".format(physical_port,side,repr(e)))

    if result is not None and isinstance(result, dict):
        mux_info_dict[("version_{}_active".format(side))] = result.get("version_active", None)
        mux_info_dict[("version_{}_inactive".format(side))] = result.get("version_inactive", None)
        mux_info_dict[("version_{}_next".format(side))] = result.get("version_next", None)

    else:
        mux_info_dict[("version_{}_active".format(side))] = "N/A"
        mux_info_dict[("version_{}_inactive".format(side))] = "N/A"
        mux_info_dict[("version_{}_next".format(side))] = "N/A"

def get_muxcable_static_info_without_presence():
    mux_info_static_dict = {}
    mux_info_static_dict['read_side']= '-1'
    mux_info_static_dict['nic_lane1_precursor1'] = 'N/A'
    mux_info_static_dict['nic_lane1_precursor2'] = 'N/A'
    mux_info_static_dict['nic_lane1_maincursor'] = 'N/A'
    mux_info_static_dict['nic_lane1_postcursor1'] = 'N/A'
    mux_info_static_dict['nic_lane1_postcursor2'] = 'N/A'
    mux_info_static_dict['nic_lane2_precursor1'] = 'N/A'
    mux_info_static_dict['nic_lane2_precursor2'] = 'N/A'
    mux_info_static_dict['nic_lane2_maincursor'] = 'N/A'
    mux_info_static_dict['nic_lane2_postcursor1'] = 'N/A'
    mux_info_static_dict['nic_lane2_postcursor2'] = 'N/A'
    mux_info_static_dict['tor_self_lane1_precursor1'] = 'N/A'
    mux_info_static_dict['tor_self_lane1_precursor2'] = 'N/A'
    mux_info_static_dict['tor_self_lane1_maincursor'] = 'N/A'
    mux_info_static_dict['tor_self_lane1_postcursor1'] = 'N/A'
    mux_info_static_dict['tor_self_lane1_postcursor2'] = 'N/A'
    mux_info_static_dict['tor_self_lane2_precursor1'] = 'N/A'
    mux_info_static_dict['tor_self_lane2_precursor2'] = 'N/A'
    mux_info_static_dict['tor_self_lane2_maincursor'] = 'N/A'
    mux_info_static_dict['tor_self_lane2_postcursor1'] = 'N/A'
    mux_info_static_dict['tor_self_lane2_postcursor2'] = 'N/A'
    mux_info_static_dict['tor_peer_lane1_precursor1'] = 'N/A'
    mux_info_static_dict['tor_peer_lane1_precursor2'] = 'N/A'
    mux_info_static_dict['tor_peer_lane1_maincursor'] = 'N/A'
    mux_info_static_dict['tor_peer_lane1_postcursor1'] = 'N/A'
    mux_info_static_dict['tor_peer_lane1_postcursor2'] = 'N/A'
    mux_info_static_dict['tor_peer_lane2_precursor1'] = 'N/A'
    mux_info_static_dict['tor_peer_lane2_precursor2'] = 'N/A' 
    mux_info_static_dict['tor_peer_lane2_maincursor'] = 'N/A'
    mux_info_static_dict['tor_peer_lane2_postcursor1'] = 'N/A'
    mux_info_static_dict['tor_peer_lane2_postcursor2'] = 'N/A'

    return mux_info_static_dict

def parse_grpc_response_link_and_oper_state(ret, response, read_side, query_type, port):
    self_state = peer_state = 'unknown'

    if ret is True and response is not None:
        if len(response.portid) == 2 and len(response.state) == 2:
            if int(read_side) == 0:
                if response.state[0] == True:
                    self_state = 'up'
                elif response.state[0] == False:
                    self_state = 'down'
                # No other values expected, should we raise exception/msg
                # TODO handle other responses
                if response.state[1] == True:
                    peer_state = 'up'
                elif response.state[1] == False:
                    peer_state = 'down'

            elif int(read_side) == 1:
                if response.state[1] == True:
                    self_state = 'up'
                elif response.state[1] == False:
                    self_state = 'down'
                if response.state[0] == True:
                    peer_state = 'up'
                elif response.state[0] == False:
                    peer_state = 'down'

        else:
            helper_logger.log_warning("recieved an error port list while parsing response {} port state list size 0 {} {}".format(query_type, len(response.portid), len(response.state)))
            self_state = 'unknown'
            peer_state = 'unknown'
    else:
        self_state = 'unknown'
        peer_state = 'unknown'

    stat = grpc_port_stats.get(port,None)
    if stat is not None:

        if query_type == "link_state":
            grpc_port_stats[port]["link_state_probe_count"] = str(int(stat.get("link_state_probe_count", 0)) + 1 )
            grpc_port_stats[port]["peer_link_state_probe_count"] = str(int(stat.get("peer_link_state_probe_count", 0)) + 1 )
        elif query_type == "oper_state":
            grpc_port_stats[port]["operation_state_probe_count"] = str(int(stat.get("operation_state_probe_count", 0)) + 1 )
            grpc_port_stats[port]["peer_operation_state_probe_count"] = str(int(stat.get("peer_operation_state_probe_count", 0)) + 1 )
    else:
        grpc_port_stats[port] = {}
        if query_type == "link_state":
            grpc_port_stats[port]["link_state_probe_count"] = 0
            grpc_port_stats[port]["peer_link_state_probe_count"] = 0
        elif query_type == "oper_state":
            grpc_port_stats[port]["operation_state_probe_count"] = 0
            grpc_port_stats[port]["peer_operation_state_probe_count"] = 0


    return (self_state, peer_state)



def get_muxcable_info_for_active_active(physical_port, port, mux_tbl, asic_index, y_cable_tbl):
    mux_info_dict = {}

    time_post = datetime.datetime.utcnow().strftime("%Y-%b-%d %H:%M:%S.%f")
    mux_info_dict["time_post"] = str(time_post)

    (status, fvs) = y_cable_tbl[asic_index].get(port)
    if status is False:
        helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(logical_port_name, y_cable_tbl[asic_index].getTableName()))
        return -1

    mux_port_dict = dict(fvs)
    read_side = int(mux_port_dict.get("read_side"))

    stat = grpc_port_stats.get(port, None)
    if stat is not None:
        mux_info_dict['mux_direction_probe_count'] = grpc_port_stats[port].get("mux_direction_probe_count", "unknown")
        mux_info_dict['peer_mux_direction_probe_count'] = grpc_port_stats[port].get("peer_mux_direction_probe_count", "unknown")
        mux_info_dict['link_state_probe_count'] = grpc_port_stats[port].get("link_state_probe_count", "unknown")
        mux_info_dict['peer_link_state_probe_count'] = grpc_port_stats[port].get("peer_link_state_probe_count", "unknown")
        mux_info_dict['operation_state_probe_count'] = grpc_port_stats[port].get("operation_state_probe_count", "unknown")
        mux_info_dict['peer_operation_state_probe_count'] = grpc_port_stats[port].get("peer_operation_state_probe_count", "unknown")
    else:
        mux_info_dict['mux_direction_probe_count'] = "unknown"
        mux_info_dict['peer_mux_direction_probe_count'] = "unknown"
        mux_info_dict['link_state_probe_count'] = "unknown"
        mux_info_dict['peer_link_state_probe_count'] = "unknown"
        mux_info_dict['operation_state_probe_count'] = "unknown"
        mux_info_dict['peer_operation_state_probe_count'] = "unknown"



    stub = grpc_port_stubs.get(port, None)
    if stub is None:
        #Can't make any RPC gRPC for this port, fill everything as unknown except cached values
        mux_info_dict['self_link_state'] = "unknown"
        mux_info_dict['peer_link_state'] = "unknown"
        mux_info_dict['self_oper_state'] = "unknown"
        mux_info_dict['peer_oper_state'] = "unknown"
        mux_info_dict['server_version'] = "N/A"
        mux_info_dict['self_mux_direction'] = "unknown"
        mux_info_dict['peer_mux_direction'] = "unknown"
        mux_info_dict['grpc_connection_status'] = "unknown"
        return mux_info_dict


    request = linkmgr_grpc_driver_pb2.LinkStateRequest(portid=DEFAULT_PORT_IDS)

    ret, response = try_grpc(stub.QueryLinkState, QUERY_ADMIN_FORWARDING_TIMEOUT , request)

    (self_link_state, peer_link_state) = parse_grpc_response_link_and_oper_state(ret, response, read_side, "link_state", port)

    mux_info_dict['self_link_state'] = self_link_state
    mux_info_dict['peer_link_state'] = peer_link_state

    request = linkmgr_grpc_driver_pb2.OperationRequest(portid=DEFAULT_PORT_IDS)

    ret, response = try_grpc(stub.QueryOperationPortState, QUERY_ADMIN_FORWARDING_TIMEOUT , request)

    (self_oper_state, peer_oper_state) = parse_grpc_response_link_and_oper_state(ret, response, read_side, "oper_state", port)

    mux_info_dict['self_oper_state'] = self_oper_state
    mux_info_dict['peer_oper_state'] = peer_oper_state

    request = linkmgr_grpc_driver_pb2.AdminRequest(portid=DEFAULT_PORT_IDS, state=[0, 0])

    ret, response = try_grpc(stub.QueryAdminForwardingPortState, QUERY_ADMIN_FORWARDING_TIMEOUT , request)

    (self_state, peer_state) = parse_grpc_response_forwarding_state(ret, response, read_side, port)

    mux_info_dict['self_mux_direction'] = self_state
    mux_info_dict['peer_mux_direction'] = peer_state

    request = linkmgr_grpc_driver_pb2.ServerVersionRequest(version="1.0")

    ret, response = try_grpc(stub.QueryServerVersion, QUERY_ADMIN_FORWARDING_TIMEOUT , request)

    if ret is True:
        version = response.version
    else:
        version = "N/A"

    mux_info_dict['server_version'] = version

    grpc_connection_status = grpc_port_connectivity.get(port, "unknown")

    mux_info_dict['grpc_connection_status'] = grpc_connection_status

    return mux_info_dict

def get_muxcable_info_without_presence():
    mux_info_dict = {}

    time_post = datetime.datetime.utcnow().strftime("%Y-%b-%d %H:%M:%S.%f")
    mux_info_dict["time_post"] = str(time_post)
    mux_info_dict['tor_active'] = 'unknown'
    mux_info_dict['mux_direction'] = 'unknown'
    mux_info_dict['manual_switch_count'] = 'N/A'
    mux_info_dict['auto_switch_count'] = 'N/A'
    mux_info_dict['link_status_self'] = 'unknown'
    mux_info_dict['link_status_peer'] = 'unknown'
    mux_info_dict['link_status_nic'] = 'unknown'
    mux_info_dict['self_eye_height_lane1'] = 'N/A'
    mux_info_dict['self_eye_height_lane2'] = 'N/A'
    mux_info_dict['peer_eye_height_lane1'] = 'N/A'
    mux_info_dict['peer_eye_height_lane2'] = 'N/A'
    mux_info_dict['nic_eye_height_lane1'] = 'N/A'
    mux_info_dict['nic_eye_height_lane2'] = 'N/A'
    mux_info_dict['internal_temperature'] = 'N/A'
    mux_info_dict['internal_voltage'] = 'N/A'
    mux_info_dict['nic_temperature'] = 'N/A'
    mux_info_dict['nic_voltage'] = 'N/A'
    mux_info_dict['version_self_active'] = 'N/A'
    mux_info_dict['version_self_inactive'] = 'N/A'
    mux_info_dict['version_self_next'] = 'N/A'
    mux_info_dict['version_peer_active'] = 'N/A'
    mux_info_dict['version_peer_inactive'] = 'N/A'
    mux_info_dict['version_peer_next'] = 'N/A'
    mux_info_dict['version_nic_active'] = 'N/A'
    mux_info_dict['version_nic_inactive'] = 'N/A'
    mux_info_dict['version_nic_next'] = 'N/A'

    return mux_info_dict

def get_muxcable_info(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl):

    mux_info_dict = {}

    port_instance = y_cable_port_instances.get(physical_port)
    if port_instance is None:
        helper_logger.log_error("Error: Could not get port instance for muxcable info for Y cable port {}".format(logical_port_name))
        return -1

    if port_instance.download_firmware_status == port_instance.FIRMWARE_DOWNLOAD_STATUS_INPROGRESS:
        helper_logger.log_warning("Warning: posting mux cable info while a download firmware in progress {}".format(logical_port_name))


    if asic_index is None:
        helper_logger.log_warning("Got invalid asic index for {}, ignored".format(logical_port_name))
        return -1

    (status, fvs) = y_cable_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(logical_port_name, y_cable_tbl[asic_index].getTableName()))
        return -1

    mux_port_dict = dict(fvs)
    read_side = int(mux_port_dict.get("read_side"))

    active_side = None

    with y_cable_port_locks[physical_port]:
        try:
            active_side = port_instance.get_active_linked_tor_side()
        except Exception as e:
            helper_logger.log_warning("Failed to execute the get_active_side API for port {} due to {}".format(physical_port,repr(e)))

    if active_side is None or active_side == port_instance.EEPROM_ERROR or active_side < 0:
        tor_active = 'unknown'
    elif read_side == active_side and (active_side == 1 or active_side == 2):
        tor_active = 'active'
    elif read_side != active_side and (active_side == 1 or active_side == 2):
        tor_active = 'standby'
    else:
        tor_active = 'unknown'

    mux_info_dict["tor_active"] = tor_active

    time_post = datetime.datetime.utcnow().strftime("%Y-%b-%d %H:%M:%S.%f")
    mux_info_dict["time_post"] = str(time_post)

    mux_dir_val = None
    with y_cable_port_locks[physical_port]:
        try:
            mux_dir_val = port_instance.get_mux_direction()
        except Exception as e:
            helper_logger.log_warning("Failed to execute the get_mux_direction API for port {} due to {}".format(physical_port,repr(e)))

    if mux_dir_val is None or mux_dir_val == port_instance.EEPROM_ERROR or mux_dir_val < 0 or read_side == -1:
        mux_direction = 'unknown'
    else:
        if read_side == mux_dir_val:
            mux_direction = 'self'
        else:
            mux_direction = 'peer'

    mux_info_dict["mux_direction"] = mux_direction

    with y_cable_port_locks[physical_port]:
        try:
            manual_switch_cnt = port_instance.get_switch_count_total(port_instance.SWITCH_COUNT_MANUAL)
            auto_switch_cnt = port_instance.get_switch_count_total(port_instance.SWITCH_COUNT_AUTO)
        except Exception as e:
            manual_switch_cnt = None
            auto_switch_cnt = None
            helper_logger.log_warning("Failed to execute the get_switch_cnt API for port {} due to {}".format(physical_port,repr(e)))

    if manual_switch_cnt is None or manual_switch_cnt == port_instance.EEPROM_ERROR or manual_switch_cnt < 0:
        mux_info_dict["manual_switch_count"] = "N/A"
    else:
        mux_info_dict["manual_switch_count"] = manual_switch_cnt

    if auto_switch_cnt is None or auto_switch_cnt == port_instance.EEPROM_ERROR or auto_switch_cnt < 0:
        mux_info_dict["auto_switch_count"] = "N/A"
    else:
        mux_info_dict["auto_switch_count"] = auto_switch_cnt


    if read_side == 1:
        with y_cable_port_locks[physical_port]:
            try:
                eye_result_self = port_instance.get_eye_heights(port_instance.TARGET_TOR_A)
                eye_result_peer = port_instance.get_eye_heights(port_instance.TARGET_TOR_B)
            except Exception as e:
                eye_result_self = None
                eye_result_peer = None
                helper_logger.log_warning("Failed to execute the get_eye_heights API for port {} due to {}".format(physical_port,repr(e)))
    else:
        with y_cable_port_locks[physical_port]:
            try:
                eye_result_self = port_instance.get_eye_heights(port_instance.TARGET_TOR_B)
                eye_result_peer = port_instance.get_eye_heights(port_instance.TARGET_TOR_A)
            except Exception as e:
                eye_result_self = None
                eye_result_peer = None
                helper_logger.log_warning("Failed to execute the get_eye_heights API for port {} due to {}".format(physical_port,repr(e)))

    with y_cable_port_locks[physical_port]:
        try:
            eye_result_nic = port_instance.get_eye_heights(port_instance.TARGET_NIC)
        except Exception as e:
            eye_result_nic = None
            helper_logger.log_warning("Failed to execute the get_eye_heights nic side API for port {} due to {}".format(physical_port,repr(e)))

    if eye_result_self is not None and eye_result_self is not port_instance.EEPROM_ERROR and isinstance(eye_result_self, list):
        mux_info_dict["self_eye_height_lane1"] = eye_result_self[0]
        mux_info_dict["self_eye_height_lane2"] = eye_result_self[1]
    else:
        mux_info_dict["self_eye_height_lane1"] = "N/A"
        mux_info_dict["self_eye_height_lane2"] = "N/A"

    if eye_result_peer is not None and eye_result_peer is not port_instance.EEPROM_ERROR and isinstance(eye_result_peer, list):
        mux_info_dict["peer_eye_height_lane1"] = eye_result_peer[0]
        mux_info_dict["peer_eye_height_lane2"] = eye_result_peer[1]
    else:
        mux_info_dict["peer_eye_height_lane1"] = "N/A"
        mux_info_dict["peer_eye_height_lane2"] = "N/A"

    if eye_result_nic is not None and eye_result_nic is not port_instance.EEPROM_ERROR and isinstance(eye_result_nic, list):
        mux_info_dict["nic_eye_height_lane1"] = eye_result_nic[0]
        mux_info_dict["nic_eye_height_lane2"] = eye_result_nic[1]
    else:
        mux_info_dict["nic_eye_height_lane1"] = "N/A"
        mux_info_dict["nic_eye_height_lane2"] = "N/A"

    if read_side == 1:
        with y_cable_port_locks[physical_port]:
            try:
                link_state_tor_a = port_instance.is_link_active(port_instance.TARGET_TOR_A)
            except Exception as e:
                link_state_tor_a = False
                helper_logger.log_warning("Failed to execute the is_link_active TOR A side API for port {} due to {}".format(physical_port,repr(e)))

            if link_state_tor_a:
                mux_info_dict["link_status_self"] = "up"
            else:
                mux_info_dict["link_status_self"] = "down"
        with y_cable_port_locks[physical_port]:
            try:
                link_state_tor_b = port_instance.is_link_active(port_instance.TARGET_TOR_B)
            except Exception as e:
                link_state_tor_b = False
                helper_logger.log_warning("Failed to execute the is_link_active TOR B side API for port {} due to {}".format(physical_port,repr(e)))
            if link_state_tor_b:
                mux_info_dict["link_status_peer"] = "up"
            else:
                mux_info_dict["link_status_peer"] = "down"
    else:
        with y_cable_port_locks[physical_port]:
            try:
                link_state_tor_b = port_instance.is_link_active(port_instance.TARGET_TOR_B)
            except Exception as e:
                link_state_tor_b = False
                helper_logger.log_warning("Failed to execute the is_link_active TOR B side API for port {} due to {}".format(physical_port,repr(e)))

            if link_state_tor_b:
                mux_info_dict["link_status_self"] = "up"
            else:
                mux_info_dict["link_status_self"] = "down"

        with y_cable_port_locks[physical_port]:
            try:
                link_state_tor_a = port_instance.is_link_active(port_instance.TARGET_TOR_A)
            except Exception as e:
                link_state_tor_a = False
                helper_logger.log_warning("Failed to execute the is_link_active TOR A side API for port {} due to {}".format(physical_port,repr(e)))

            if link_state_tor_a:
                mux_info_dict["link_status_peer"] = "up"
            else:
                mux_info_dict["link_status_peer"] = "down"

    with y_cable_port_locks[physical_port]:
        try:
            link_state_tor_nic = port_instance.is_link_active(port_instance.TARGET_NIC)
        except Exception as e:
            link_state_tor_nic = False
            helper_logger.log_warning("Failed to execute the is_link_active NIC side API for port {} due to {}".format(physical_port,repr(e)))

        if link_state_tor_nic:
            mux_info_dict["link_status_nic"] = "up"
        else:
            mux_info_dict["link_status_nic"] = "down"

    get_firmware_dict(physical_port, port_instance, port_instance.TARGET_NIC, "nic", mux_info_dict, logical_port_name, mux_tbl)
    if read_side == 1:
        get_firmware_dict(physical_port, port_instance, port_instance.TARGET_TOR_A, "self", mux_info_dict, logical_port_name, mux_tbl)
        get_firmware_dict(physical_port, port_instance, port_instance.TARGET_TOR_B, "peer", mux_info_dict, logical_port_name, mux_tbl)
    else:
        get_firmware_dict(physical_port, port_instance, port_instance.TARGET_TOR_A, "peer", mux_info_dict, logical_port_name, mux_tbl)
        get_firmware_dict(physical_port, port_instance, port_instance.TARGET_TOR_B, "self", mux_info_dict, logical_port_name, mux_tbl)

    with y_cable_port_locks[physical_port]:
        try:
            res = port_instance.get_local_temperature()
        except Exception as e:
            res = None
            helper_logger.log_warning("Failed to execute the get_local_temperature for port {} due to {}".format(physical_port,repr(e)))

    if res is not None and res is not port_instance.EEPROM_ERROR and isinstance(res, int) and res >= 0:
        mux_info_dict["internal_temperature"] = res
    else:
        mux_info_dict["internal_temperature"] = "N/A"

    with y_cable_port_locks[physical_port]:
        try:
            res = port_instance.get_local_voltage()
        except Exception as e:
            res = None
            helper_logger.log_warning("Failed to execute the get_local_voltage for port {} due to {}".format(physical_port,repr(e)))

    if res is not None and res is not port_instance.EEPROM_ERROR and isinstance(res, float):
        mux_info_dict["internal_voltage"] = res
    else:
        mux_info_dict["internal_voltage"] = "N/A"

    with y_cable_port_locks[physical_port]:
        try:
            res = port_instance.get_nic_voltage()
        except Exception as e:
            res = None
            helper_logger.log_warning("Failed to execute the get_nic_voltage for port {} due to {}".format(physical_port,repr(e)))

    if res is not None and res is not port_instance.EEPROM_ERROR and isinstance(res, float):
        mux_info_dict["nic_voltage"] = res
    else:
        mux_info_dict["nic_voltage"] = "N/A"

    with y_cable_port_locks[physical_port]:
        try:
            res = port_instance.get_nic_temperature()
        except Exception as e:
            res = None
            helper_logger.log_warning("Failed to execute the get_nic_temperature for port {} due to {}".format(physical_port,repr(e)))

    if res is not None and res is not port_instance.EEPROM_ERROR and isinstance(res, int) and res >= 0:
        mux_info_dict["nic_temperature"] = res
    else:
        mux_info_dict["nic_temperature"] = "N/A"

    return mux_info_dict


def get_muxcable_static_info(physical_port, logical_port_name, y_cable_tbl):

    mux_static_info_dict = {}

    port_instance = y_cable_port_instances.get(physical_port)
    if port_instance is None:
        helper_logger.log_error("Error: Could not get port instance for muxcable info for Y cable port {}".format(logical_port_name))
        return -1

    asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(
        logical_port_name)
    if asic_index is None:
        helper_logger.log_warning(
            "Got invalid asic index for {}, ignored".format(logical_port_name))
        return -1

    (status, fvs) = y_cable_tbl[asic_index].get(logical_port_name)
    if status is False:
        helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
            logical_port_name, y_cable_tbl[asic_index].getTableName()))
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
        try:
            cursor_values_nic = port_instance.get_target_cursor_values(i, port_instance.TARGET_NIC)
        except Exception as e:
            cursor_values_nic = None
            helper_logger.log_warning("Failed to execute the get_target_cursor_value NIC for port {} due to {}".format(physical_port,repr(e)))

        if cursor_values_nic is not None and cursor_values_nic is not port_instance.EEPROM_ERROR and isinstance(cursor_values_nic, list):
            cursor_nic_values.append(cursor_values_nic)
        else:
            cursor_nic_values.append(dummy_list)

        try:
            cursor_values_tor1 = port_instance.get_target_cursor_values(i, port_instance.TARGET_TOR_A)
        except Exception as e:
            cursor_values_tor1 = None
            helper_logger.log_warning("Failed to execute the get_target_cursor_value ToR 1 for port {} due to {}".format(physical_port,repr(e)))

        if cursor_values_tor1 is not None and cursor_values_tor1 is not port_instance.EEPROM_ERROR and isinstance(cursor_values_tor1, list):
            cursor_tor1_values.append(cursor_values_tor1)
        else:
            cursor_tor1_values.append(dummy_list)

        try:
            cursor_values_tor2 = port_instance.get_target_cursor_values(i, port_instance.TARGET_TOR_B)
        except Exception as e:
            cursor_values_tor2 = None
            helper_logger.log_warning("Failed to execute the get_target_cursor_value ToR 2 for port {} due to {}".format(physical_port,repr(e)))

        if cursor_values_tor2 is not None and cursor_values_tor2 is not port_instance.EEPROM_ERROR and isinstance(cursor_values_tor2, list):
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


def post_port_mux_info_to_db(logical_port_name, mux_tbl, asic_index, y_cable_tbl, cable_type):

    physical_port_list = logical_port_name_to_physical_port_list(logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("No physical ports found for logical port '{}'".format(logical_port_name))
        return -1

    if len(physical_port_list) > 1:
        helper_logger.log_warning("Error: Retreived multiple ports for a Y cable port {}".format(logical_port_name))
        return -1

    for physical_port in physical_port_list:

        if not y_cable_wrapper_get_presence(physical_port) or cable_type == 'pseudo-cable':
            mux_info_dict = get_muxcable_info_without_presence()
        elif cable_type == 'active-active':
            helper_logger.log_debug("Error: trying to post mux info without presence of port {}".format(logical_port_name))
            mux_info_dict = get_muxcable_info_for_active_active(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)
            if mux_info_dict is not None and mux_info_dict !=  -1:
                fvs = swsscommon.FieldValuePairs(
                    [('self_link_state',  mux_info_dict["self_link_state"]),
                     ('peer_link_state',  str(mux_info_dict["peer_link_state"])),
                     ('self_oper_state', str(mux_info_dict["self_oper_state"])),
                     ('peer_oper_state', str(mux_info_dict["peer_oper_state"])),
                     ('server_version', str(mux_info_dict["server_version"])),
                     ('time_post',  str(mux_info_dict["time_post"])),
                     ('self_mux_direction',  str(mux_info_dict["self_mux_direction"])),
                     ('peer_mux_direction',  str(mux_info_dict["peer_mux_direction"])),
                     ('peer_mux_direction_probe_count',  str(mux_info_dict["peer_mux_direction_probe_count"])),
                     ('mux_direction_probe_count',  str(mux_info_dict["mux_direction_probe_count"])),
                     ('link_state_probe_count',  str(mux_info_dict["link_state_probe_count"])),
                     ('peer_link_state_probe_count',  str(mux_info_dict["peer_link_state_probe_count"])),
                     ('operation_state_probe_count',  str(mux_info_dict["operation_state_probe_count"])),
                     ('peer_operation_state_probe_count',  str(mux_info_dict["peer_operation_state_probe_count"])),
                     ('grpc_connection_status',  str(mux_info_dict["grpc_connection_status"]))
                     ])
                mux_tbl[asic_index].set(logical_port_name, fvs)
                return
            else:
                return -1
        else:
            mux_info_dict = get_muxcable_info(physical_port, logical_port_name, mux_tbl, asic_index, y_cable_tbl)

        if mux_info_dict is not None and mux_info_dict !=  -1:
            #transceiver_dict[physical_port] = port_info_dict
            fvs = swsscommon.FieldValuePairs(
                [('tor_active',  mux_info_dict["tor_active"]),
                 ('time_post',  str(mux_info_dict["time_post"])),
                 ('mux_direction',  str(mux_info_dict["mux_direction"])),
                 ('manual_switch_count', str(mux_info_dict["manual_switch_count"])),
                 ('auto_switch_count', str(mux_info_dict["auto_switch_count"])),
                 ('link_status_self', mux_info_dict["link_status_self"]),
                 ('link_status_peer', mux_info_dict["link_status_peer"]),
                 ('link_status_nic', mux_info_dict["link_status_nic"]),
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
                 ('version_self_active', str(mux_info_dict["version_self_active"])),
                 ('version_self_inactive', str(mux_info_dict["version_self_inactive"])),
                 ('version_self_next', str(mux_info_dict["version_self_next"])),
                 ('version_peer_active', str(mux_info_dict["version_peer_active"])),
                 ('version_peer_inactive', str(mux_info_dict["version_peer_inactive"])),
                 ('version_peer_next', str(mux_info_dict["version_peer_next"])),
                 ('version_nic_active', str(mux_info_dict["version_nic_active"])),
                 ('version_nic_inactive', str(mux_info_dict["version_nic_inactive"])),
                 ('version_nic_next', str(mux_info_dict["version_nic_next"]))
                 ])
            mux_tbl[asic_index].set(logical_port_name, fvs)
        else:
            return -1


def post_port_mux_static_info_to_db(logical_port_name, static_table, y_cable_tbl):

    physical_port_list = logical_port_name_to_physical_port_list(
        logical_port_name)
    if physical_port_list is None:
        helper_logger.log_error("No physical ports found for logical port '{}'".format(logical_port_name))
        return -1

    if len(physical_port_list) > 1:
        helper_logger.log_warning(
            "Error: Retreived multiple ports for a Y cable port {}".format(logical_port_name))
        return -1

    for physical_port in physical_port_list:

        if not y_cable_wrapper_get_presence(physical_port):
            helper_logger.log_warning("Error: trying to post mux static info without presence of port {}".format(logical_port_name))
            mux_static_info_dict = get_muxcable_static_info_without_presence()
        else:
            mux_static_info_dict = get_muxcable_static_info(physical_port, logical_port_name, y_cable_tbl)


        if mux_static_info_dict is not None and mux_static_info_dict != -1:
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

def put_all_values_from_list_to_db(res, xcvrd_show_ber_res_tbl, port):
    index = 0
    for val in res:
        fvs_log = swsscommon.FieldValuePairs(
            [(str(index), str(val))])
        index = index + 1
        xcvrd_show_ber_res_tbl.set(port, fvs_log)


def put_all_values_from_dict_to_db(res, xcvrd_show_ber_res_tbl, port):

    for key, val in res.items():
        fvs_log = swsscommon.FieldValuePairs(
            [(str(key), str(val))])
        xcvrd_show_ber_res_tbl.set(port, fvs_log)

def gather_arg_from_db_and_check_for_type(arg_tbl, port, key, fvp_dict, arg):

    mode = fvp_dict.get(key, None)

    (arg_status, fvp_s) = arg_tbl.get(port)

    res_dir = dict(fvp_s)

    target = res_dir.get(arg, None)
    if target is not None:
        return (target, mode, res_dir)

    return (None, mode, res_dir)

"""def check_physical_port_correctness(physical_port, status_val, status, sts_tbl, rsp_tbl, port, str_val):
    if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
        # error scenario update table accordingly
        helper_logger.log_warning("{} {}".format(str_val, port))
        set_result_and_delete_port(status_val, status, sts_tbl, rsp_tbl, port)
        return False

    return True
"""

def task_download_firmware_worker(port, physical_port, port_instance, file_full_path, xcvrd_down_fw_rsp_tbl, xcvrd_down_fw_cmd_sts_tbl, rc):
    helper_logger.log_debug("Y_CABLE_DEBUG:worker thread launched for downloading physical port {} path {}".format(physical_port, file_full_path))
    try:
        status = port_instance.download_firmware(file_full_path)
        time.sleep(5)
    except Exception as e:
        status = -1
        helper_logger.log_warning("Failed to execute the download firmware API for port {} due to {}".format(physical_port,repr(e)))

    set_result_and_delete_port('status', status, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, port)
    helper_logger.log_debug("Y_CABLE_DEBUG:downloading complete {} {} {}".format(physical_port, file_full_path, status))
    rc[0] = status
    helper_logger.log_debug("Y_CABLE_DEBUG:download thread finished port {} physical_port {}".format(port, physical_port))

def handle_config_prbs_cmd_arg_tbl_notification(fvp, xcvrd_config_prbs_cmd_arg_tbl, xcvrd_config_prbs_cmd_sts_tbl, xcvrd_config_prbs_rsp_tbl, asic_index, port):

    fvp_dict = dict(fvp)
    status = 'False'

    if "config_prbs" in fvp_dict:

        (target,config_prbs_mode, res_dir) = gather_arg_from_db_and_check_for_type(xcvrd_config_prbs_cmd_arg_tbl[asic_index], port, "config_prbs", fvp_dict, "target")

        if target is not None:
            target = int(target)

        physical_port = get_ycable_physical_port_from_logical_port(port)
        if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR or target is None:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get physical port or correct args for cli cmd enable/disable prbs anlt/reset port {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_config_prbs_cmd_sts_tbl[asic_index], xcvrd_config_prbs_rsp_tbl[asic_index], port)
            return -1

        port_instance = get_ycable_port_instance_from_logical_port(port)
        if port_instance is None or port_instance in port_mapping_error_values:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get port instance for cli cmd enable/disable prbs anlt/reset port {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_config_prbs_cmd_sts_tbl[asic_index], xcvrd_config_prbs_rsp_tbl[asic_index], port)
            return -1

        if config_prbs_mode == "enable":
            mode_value = res_dir.get("mode_value", None)
            if mode_value is not None:
                mode_value = int(mode_value)

            lane_mask = res_dir.get("lane_mask", None)
            if lane_mask is not None:
                lane_mask = int(lane_mask)

            direction = res_dir.get("direction", None)
            if direction is None:
                direction = port_instance.PRBS_DIRECTION_BOTH
            else:
                direction = int(direction)

            if lane_mask is None or mode_value is None:
                helper_logger.log_warning("Error: Could not get correct args lan_mask/mode_value for cli cmd enable prbs port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_config_prbs_cmd_sts_tbl[asic_index], xcvrd_config_prbs_rsp_tbl[asic_index], port)
                return -1
            with y_cable_port_locks[physical_port]:
                try:
                    status = port_instance.enable_prbs_mode(target, mode_value, lane_mask, direction)
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the enable prbs API for port {} due to {}".format(physical_port,repr(e)))
        elif config_prbs_mode == "disable":
            direction = res_dir.get("direction", None)
            if direction is None:
                direction = port_instance.PRBS_DIRECTION_BOTH
            else:
                direction = int(direction)

            with y_cable_port_locks[physical_port]:
                try:
                    status = port_instance.disable_prbs_mode(target, direction)
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the disable prbs API for port {} due to {}".format(physical_port,repr(e)))
        elif config_prbs_mode == "reset":

            port_instance.download_firmware_status == port_instance.FIRMWARE_DOWNLOAD_STATUS_NOT_INITIATED_OR_FINISHED
            with y_cable_port_locks[physical_port]:
                try:
                    status = port_instance.reset(target)
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the reset API for port {} due to {}".format(physical_port,repr(e)))
        elif config_prbs_mode == "anlt":
            enable = res_dir.get("mode", None)
            if enable is None:
                helper_logger.log_warning("Error: Could not get correct args (enable) for cli cmd set anlt port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_config_prbs_cmd_sts_tbl[asic_index], xcvrd_config_prbs_rsp_tbl[asic_index], port)
                return -1
            enable = int(enable)
            with y_cable_port_locks[physical_port]:
                try:
                    status = port_instance.set_anlt(enable, target)
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the set_anlt API for port {} due to {}".format(physical_port,repr(e)))
        elif config_prbs_mode == "fec":
            mode = res_dir.get("mode", None)
            if mode is None:
                helper_logger.log_warning("Error: Could not get correct args (enable) for cli cmd set fec port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_config_prbs_cmd_sts_tbl[asic_index], xcvrd_config_prbs_rsp_tbl[asic_index], port)
                return -1
            mode = int(mode)
            with y_cable_port_locks[physical_port]:
                try:
                    status = port_instance.set_fec_mode(mode, target)
                except Exception as e:
                    status = -1
        set_result_and_delete_port('status', status, xcvrd_config_prbs_cmd_sts_tbl[asic_index], xcvrd_config_prbs_rsp_tbl[asic_index], port)
    else:
        helper_logger.log_error("Wrong param for cli cmd enable/disable prbs anlt/reset API port {}".format(port))
        set_result_and_delete_port('status', status, xcvrd_config_prbs_cmd_sts_tbl[asic_index], xcvrd_config_prbs_rsp_tbl[asic_index], port)

def handle_config_loop_cmd_arg_tbl_notification(fvp, xcvrd_config_loop_cmd_arg_tbl, xcvrd_config_loop_cmd_sts_tbl, xcvrd_config_loop_rsp_tbl, asic_index, port):

    fvp_dict = dict(fvp)
    status = 'False'

    if "config_loop" in fvp_dict:


        (target, config_loop_mode, res_dir) = gather_arg_from_db_and_check_for_type(xcvrd_config_loop_cmd_arg_tbl[asic_index], port, "config_loop", fvp_dict, "target")

        if target is not None:
            target = int(target)

        physical_port = get_ycable_physical_port_from_logical_port(port)
        if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR or target is None:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get physical port or correct args for cli cmd enable enable/disable loopback {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_config_loop_cmd_sts_tbl[asic_index], xcvrd_config_loop_rsp_tbl[asic_index], port)
            return -1

        port_instance = get_ycable_port_instance_from_logical_port(port)
        if port_instance is None or port_instance in port_mapping_error_values:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get port instance for cli cmd enable/disable loopback mode port {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_config_loop_cmd_sts_tbl[asic_index], xcvrd_config_loop_rsp_tbl[asic_index], port)
            return -1

        if config_loop_mode == "enable":
            mode_value = res_dir.get("mode_value", None)
            if mode_value is None:
                mode_value = port_instance.LOOPBACK_MODE_NEAR_END
            else:
                mode_value = int(mode_value)

            lane_mask = res_dir.get("lane_mask", None)

            if lane_mask is None:
                helper_logger.log_warning("Error: Could not get physical port or correct args for cli cmd enable loopback port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_config_loop_cmd_sts_tbl[asic_index], xcvrd_config_loop_rsp_tbl[asic_index], port)
                return -1
            else:
                lane_mask = int(lane_mask)

            with y_cable_port_locks[physical_port]:
                try:
                    status = port_instance.enable_loopback_mode(target, mode_value, lane_mask)
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the enable/disable loopback API for port {} due to {}".format(physical_port,repr(e)))
        elif config_loop_mode == "disable":
            with y_cable_port_locks[physical_port]:
                try:
                    status = port_instance.disable_loopback_mode(target)
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the enable/disable loopback API for port {} due to {}".format(physical_port,repr(e)))
        set_result_and_delete_port('status', status, xcvrd_config_loop_cmd_sts_tbl[asic_index], xcvrd_config_loop_rsp_tbl[asic_index], port)
    else:
        helper_logger.log_error("Wrong param for cli cmd enable/disable loopback port {}".format(port))
        set_result_and_delete_port('status', status, xcvrd_config_loop_cmd_sts_tbl[asic_index], xcvrd_config_loop_rsp_tbl[asic_index], port)

def handle_show_event_cmd_arg_tbl_notification(fvp, xcvrd_show_event_cmd_sts_tbl, xcvrd_show_event_rsp_tbl, xcvrd_show_event_res_tbl, asic_index, port):
    status = 'False'
    fvp_dict = dict(fvp)

    if "show_event" in fvp_dict:

        physical_port = get_ycable_physical_port_from_logical_port(port)
        if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get physical port or correct args for cli cmd event log port {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_show_event_cmd_sts_tbl[asic_index], xcvrd_show_event_rsp_tbl[asic_index], port)
            return -1

        port_instance = get_ycable_port_instance_from_logical_port(port)
        if port_instance is None or port_instance in port_mapping_error_values:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get port instance for cli cmd event log port {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_show_event_cmd_sts_tbl[asic_index], xcvrd_show_event_rsp_tbl[asic_index], port)
            return -1

        with y_cable_port_locks[physical_port]:
            try:
                res_list = port_instance.get_event_log()
                index = 0
                status = True
                if isinstance(res_list, list):
                    for log in res_list:
                        fvs_log = swsscommon.FieldValuePairs([(str(index), str(log))])
                        helper_logger.log_notice("event log for cable {} port {}".format(log, port))
                        index = index +1
                        xcvrd_show_event_res_tbl[asic_index].set(port, fvs_log)
            except Exception as e:
                status = -1
                helper_logger.log_warning("Failed to execute the event log API for port {} due to {}".format(physical_port,repr(e)))
        set_result_and_delete_port('status', status, xcvrd_show_event_cmd_sts_tbl[asic_index], xcvrd_show_event_rsp_tbl[asic_index], port)
    else:
        helper_logger.log_error("Wrong param for cli cmd event log API port {}".format(port))
        set_result_and_delete_port('status', status, xcvrd_show_event_cmd_sts_tbl[asic_index], xcvrd_show_event_rsp_tbl[asic_index], port)

def handle_get_fec_cmd_arg_tbl_notification(fvp,xcvrd_show_fec_rsp_tbl, xcvrd_show_fec_cmd_sts_tbl, xcvrd_show_fec_res_tbl, asic_index, port):

    fvp_dict = dict(fvp)
    status = 'False'

    if "get_fec" in fvp_dict:

        physical_port = get_ycable_physical_port_from_logical_port(port)
        if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get physical port or correct args for cli cmd get_fec_eye_anlt port {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_show_fec_cmd_sts_tbl[asic_index], xcvrd_show_fec_rsp_tbl[asic_index], port)
            return -1

        port_instance = get_ycable_port_instance_from_logical_port(port)
        if port_instance is None or port_instance in port_mapping_error_values:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get port instance for cli cmd get_fec_eye_anlt port {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_show_fec_cmd_sts_tbl[asic_index], xcvrd_show_fec_rsp_tbl[asic_index], port)
            return -1

        with y_cable_port_locks[physical_port]:
            try:
                fec_res_nic = port_instance.get_fec_mode(port_instance.TARGET_NIC)
                fec_res_a = port_instance.get_fec_mode(port_instance.TARGET_TOR_A)
                fec_res_b = port_instance.get_fec_mode(port_instance.TARGET_TOR_B)
                speed_res_nic = port_instance.get_speed()
                an_res_nic = port_instance.get_anlt(port_instance.TARGET_NIC)
                an_res_a = port_instance.get_anlt(port_instance.TARGET_TOR_A)
                an_res_b = port_instance.get_anlt(port_instance.TARGET_TOR_B)
                fvs_log = swsscommon.FieldValuePairs(
                    [("fec_nic", str(fec_res_nic)),
                     ("fec_tor_a", str(fec_res_a)),
                     ("fec_tor_b", str(fec_res_b)),
                     ("speed", str(speed_res_nic)),
                     ("anlt_nic", str(an_res_nic)),
                     ("anlt_tor_a", str(an_res_a)),
                     ("anlt_tor_b", str(an_res_b))])
                xcvrd_show_fec_res_tbl[asic_index].set(port, fvs_log)
                status = True
            except Exception as e:
                status = -1
                helper_logger.log_warning("Failed to execute the get_fec_eye_anlt API for port {} due to {}".format(physical_port,repr(e)))
        set_result_and_delete_port('status', status, xcvrd_show_fec_cmd_sts_tbl[asic_index], xcvrd_show_fec_rsp_tbl[asic_index], port)
    else:
        helper_logger.log_error("Wrong param for cli cmd get_fec_eye_anlt port {}".format(port))
        set_result_and_delete_port('status', status, xcvrd_show_fec_cmd_sts_tbl[asic_index], xcvrd_show_fec_rsp_tbl[asic_index], port)

def handle_config_firmware_roll_cmd_arg_tbl_notification(fvp, xcvrd_roll_fw_cmd_sts_tbl, xcvrd_roll_fw_rsp_tbl, asic_index, port):

        fvp_dict = dict(fvp)


        if "rollback_firmware" in fvp_dict:
            file_name = fvp_dict["rollback_firmware"]
            status = 'False'

            if file_name == 'null':
                file_full_path = None
            else:
                file_full_path = '/usr/share/sonic/firmware/{}'.format(file_name)
                if not os.path.isfile(file_full_path):
                    helper_logger.log_error("Error: cli cmd mux rollback firmware file does not exist port {} file {}".format(port, file_name))
                    set_result_and_delete_port('status', status, xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)
                    return -1



            physical_port = get_ycable_physical_port_from_logical_port(port)
            if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
                # error scenario update table accordingly
                helper_logger.log_warning("Error: Could not get physical port for cli cmd mux rollback firmware port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)
                return -1

            port_instance = get_ycable_port_instance_from_logical_port(port)
            if port_instance is None or port_instance in port_mapping_error_values:
                # error scenario update table accordingly
                helper_logger.log_warning("Error: Could not get port instance for cli cmd mux rollback firmware port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)

            with y_cable_port_locks[physical_port]:
                try:
                    status = port_instance.rollback_firmware(file_full_path)
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the rollback_firmware API for port {} due to {}".format(physical_port,repr(e)))
            set_result_and_delete_port('status', status, xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)
        else:
            helper_logger.log_error("Wrong param for cli cmd mux rollback firmware port {}".format(port))
            set_result_and_delete_port('status', 'False', xcvrd_roll_fw_cmd_sts_tbl[asic_index], xcvrd_roll_fw_rsp_tbl[asic_index], port)

def handle_config_firmware_down_cmd_arg_tbl_notification(fvp, xcvrd_down_fw_cmd_sts_tbl, xcvrd_down_fw_rsp_tbl, asic_index, port, task_download_firmware_thread):

        # This check might be redundant, to check, the presence of this Port in keys
        # in logical_port_list but keep for now for coherency
        # also skip checking in logical_port_list inside sfp_util

        fvp_dict = dict(fvp)

        if "download_firmware" in fvp_dict:

            file_name = fvp_dict["download_firmware"]
            file_full_path = '/usr/share/sonic/firmware/{}'.format(file_name)

            status = -1

            if not os.path.isfile(file_full_path):
                helper_logger.log_error("Error: cli cmd download firmware file does not exist port {} file {}".format(port, file_name))
                set_result_and_delete_port('status', status, xcvrd_down_fw_cmd_sts_tbl[asic_index], xcvrd_down_fw_rsp_tbl[asic_index], port)
                return -1

            physical_port = get_ycable_physical_port_from_logical_port(port)
            if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
                # error scenario update table accordingly
                helper_logger.log_error(
                    "Error: Could not get physical port for cli cmd download firmware cli Y cable port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_down_fw_cmd_sts_tbl[asic_index], xcvrd_down_fw_rsp_tbl[asic_index], port)
                return -1

            port_instance = get_ycable_port_instance_from_logical_port(port)
            if port_instance is None or port_instance in port_mapping_error_values:
                # error scenario update table accordingly
                helper_logger.log_error(
                    "Error: Could not get port instance for cli cmd download firmware Y cable port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_down_fw_cmd_sts_tbl[asic_index], xcvrd_down_fw_rsp_tbl[asic_index], port)
                return -1

            rc = {}
            task_download_firmware_thread[physical_port] = threading.Thread(target=task_download_firmware_worker, args=(port, physical_port, port_instance, file_full_path, xcvrd_down_fw_rsp_tbl[asic_index], xcvrd_down_fw_cmd_sts_tbl[asic_index], rc,))
            task_download_firmware_thread[physical_port].start()
        else:
            helper_logger.log_error(
                "Error: Wrong input parameter get for cli cmd download firmware Y cable port {}".format(port))
            set_result_and_delete_port('status', '-1', xcvrd_down_fw_cmd_sts_tbl[asic_index], xcvrd_down_fw_rsp_tbl[asic_index], port)

def handle_show_ber_cmd_arg_tbl_notification(fvp, xcvrd_show_ber_cmd_arg_tbl, xcvrd_show_ber_rsp_tbl, xcvrd_show_ber_cmd_sts_tbl, xcvrd_show_ber_res_tbl, asic_index, port):
    fvp_dict = dict(fvp)
    status = 'False'
    res = None

    if "get_ber" in fvp_dict:

        (target, mode, res_dir) = gather_arg_from_db_and_check_for_type(xcvrd_show_ber_cmd_arg_tbl[asic_index], port, "get_ber", fvp_dict, "target")

        if target is not None:
            target = int(target)

        physical_port = get_ycable_physical_port_from_logical_port(port)
        if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get physical port or correct args for cli cmd fec port {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_show_ber_cmd_sts_tbl[asic_index], xcvrd_show_ber_rsp_tbl[asic_index], port)
            return -1

        port_instance = get_ycable_port_instance_from_logical_port(port)
        if port_instance is None or port_instance in port_mapping_error_values:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get port instance for cli cmd debug_dump/cli_event/fec_stats {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_show_ber_cmd_sts_tbl[asic_index], xcvrd_show_ber_rsp_tbl[asic_index], port)
            return -1

        if mode == "ber":
            if target is None:
                helper_logger.log_warning("Error: Could not get physical port or correct args for cli cmd get_ber_info port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_show_ber_cmd_sts_tbl[asic_index], xcvrd_show_ber_rsp_tbl[asic_index], port)
                return -1
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.get_ber_info(target)
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the get_ber_info API for port {} due to {}".format(physical_port,repr(e)))
            if res is not None and isinstance(res, list):
                put_all_values_from_list_to_db(res, xcvrd_show_ber_res_tbl[asic_index], port)

        elif mode == "eye":
            if target is None:
                helper_logger.log_warning("Error: Could not get physical port or correct args for cli cmd get_eye_info port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_show_ber_cmd_sts_tbl[asic_index], xcvrd_show_ber_rsp_tbl[asic_index], port)
                return -1
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.get_eye_heights(target)
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the eye_heights API for port {} due to {}".format(physical_port,repr(e)))
            if res is not None and isinstance(res, list):
                put_all_values_from_list_to_db(res, xcvrd_show_ber_res_tbl[asic_index], port)

        elif mode == "fec_stats":
            if target is None:
                helper_logger.log_warning("Error: Could not get physical port or correct args for cli cmd fec_stats port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_show_ber_cmd_sts_tbl[asic_index], xcvrd_show_ber_rsp_tbl[asic_index], port)
                return -1
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.get_fec_stats(target)
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute the get_fec_stats API for port {} due to {}".format(physical_port,repr(e)))
            if res is not None and isinstance(res, dict):
                put_all_values_from_dict_to_db(res, xcvrd_show_ber_res_tbl[asic_index], port)

        elif mode == "pcs_stats":
            if target is None:
                helper_logger.log_warning("Error: Could not get target or correct args for cli cmd pcs_stats port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_show_ber_cmd_sts_tbl[asic_index], xcvrd_show_ber_rsp_tbl[asic_index], port)
                return -1
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.get_pcs_stats(target)
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute cli cmd API get_pcs_stats for port {} due to {}".format(physical_port,repr(e)))
            if res is not None and isinstance(res, dict):
                put_all_values_from_dict_to_db(res, xcvrd_show_ber_res_tbl[asic_index], port)

        elif mode == "cable_alive":
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.get_alive_status()
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute cli cmd get_alive_status API for port {} due to {}".format(physical_port,repr(e)))
            if res is not None:
                fvs_log = swsscommon.FieldValuePairs(
                    [("cable_alive", str(res))])
                xcvrd_show_ber_res_tbl[asic_index].set(port, fvs_log)
        elif mode == "health_check":
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.health_check()
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute cli cmd get_health API for port {} due to {}".format(physical_port,repr(e)))
            if res is not None:
                fvs_log = swsscommon.FieldValuePairs(
                    [("health_check", str(res))])
                xcvrd_show_ber_res_tbl[asic_index].set(port, fvs_log)
        elif mode == "reset_cause":
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.reset_cause()
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute reset cause cmd API for port {} due to {}".format(physical_port,repr(e)))
            if res is not None:
                fvs_log = swsscommon.FieldValuePairs(
                    [("reset_cause", str(res))])
                xcvrd_show_ber_res_tbl[asic_index].set(port, fvs_log)
        elif mode == "operation_time":
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.operation_time()
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute operation time cmd API for port {} due to {}".format(physical_port,repr(e)))
            if res is not None:
                fvs_log = swsscommon.FieldValuePairs(
                    [("operation_time", str(res))])
                xcvrd_show_ber_res_tbl[asic_index].set(port, fvs_log)
        elif mode == "debug_dump":
            option = res_dir.get("option", None)
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.debug_dump_registers(option)
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute cli cmd debug_dump API for port {} due to {}".format(physical_port,repr(e)))
            if res is not None and isinstance(res, dict):
                put_all_values_from_dict_to_db(res, xcvrd_show_ber_res_tbl[asic_index], port)
        elif mode == "queue_info":
            with y_cable_port_locks[physical_port]:
                try:
                    res = port_instance.queue_info()
                    status = True
                except Exception as e:
                    status = -1
                    helper_logger.log_warning("Failed to execute cli cmd queue_info API for port {} due to {}".format(physical_port,repr(e)))
            if res is not None and isinstance(res, dict):
                put_all_values_from_dict_to_db(res, xcvrd_show_ber_res_tbl[asic_index], port)


        set_result_and_delete_port('status', status, xcvrd_show_ber_cmd_sts_tbl[asic_index], xcvrd_show_ber_rsp_tbl[asic_index], port)
    else:
        helper_logger.log_error("Wrong param for cli cmd debug_dump/cli_event/fec_stats API port {}".format(port))
        set_result_and_delete_port('status', status, xcvrd_show_ber_cmd_sts_tbl[asic_index], xcvrd_show_ber_rsp_tbl[asic_index], port)

def handle_config_mux_switchmode_arg_tbl_notification(fvp, xcvrd_config_hwmode_swmode_cmd_sts_tbl, xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port):
        fvp_dict = dict(fvp)

        if "config" in fvp_dict:
            config_mode = str(fvp_dict["config"])

            status = 'False'
            physical_port = get_ycable_physical_port_from_logical_port(port)
            if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
                # error scenario update table accordingly
                helper_logger.log_error(
                    "Error: Could not get physical port for cli cmd config mux hwmode setswitchmode Y cable port {}".format(port))
                set_result_and_delete_port('result', status, xcvrd_config_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_swmode_rsp_tbl[asic_index], port)
                return -1

            port_instance = get_ycable_port_instance_from_logical_port(port)
            if port_instance is None or port_instance in port_mapping_error_values:
                # error scenario update table accordingly
                helper_logger.log_error(
                    "Error: Could not get port instance for cli cmd config mux hwmode setswitchmode Y cable port {}".format(port))
                set_result_and_delete_port('result', status, xcvrd_config_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_swmode_rsp_tbl[asic_index], port)
                return -1

            if config_mode == "auto":
                with y_cable_port_locks[physical_port]:
                    try:
                        result = port_instance.set_switching_mode(port_instance.SWITCHING_MODE_AUTO)
                    except Exception as e:
                        result = None
                        helper_logger.log_warning("Failed to execute the set_switching_mode auto for port {} due to {}".format(physical_port,repr(e)))

                if result is None or result == port_instance.EEPROM_ERROR or result < 0:

                    status = 'False'
                    helper_logger.log_error(
                        "Error: Could not get read side for cli cmd config mux hwmode setswitchmode logical port {} and physical port {}".format(port, physical_port))
                    set_result_and_delete_port('result', status, xcvrd_config_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_swmode_rsp_tbl[asic_index], port)
                    return -1

            elif config_mode == "manual":
                with y_cable_port_locks[physical_port]:
                    try:
                        result = port_instance.set_switching_mode(port_instance.SWITCHING_MODE_MANUAL)
                    except Exception as e:
                        result = None
                        helper_logger.log_warning("Failed to execute the set_switching_mode manual for port {} due to {}".format(physical_port,repr(e)))
                if result is None or result is port_instance.EEPROM_ERROR or result < 0:

                    status = 'False'
                    helper_logger.log_error(
                        "Error: Could not get read side for cli cmd config mux hwmode setswitchmode logical port {} and physical port {}".format(port, physical_port))
                    set_result_and_delete_port('result', status, xcvrd_config_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_swmode_rsp_tbl[asic_index], port)
                    return -1
            else:
                helper_logger.log_error(
                    "Error: Incorrect Config state for cli cmd config mux hwmode setswitchmode logical port {} and physical port {}".format(port, physical_port))
                set_result_and_delete_port('result', status, xcvrd_config_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_swmode_rsp_tbl[asic_index], port)
                return -1


            set_result_and_delete_port('result', result, xcvrd_config_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_swmode_rsp_tbl[asic_index], port)

        else:
            helper_logger.log_error("Error: Incorrect input param for cli cmd config mux hwmode setswitchmode logical port {}".format(port))
            set_result_and_delete_port('result', 'False', xcvrd_config_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_swmode_rsp_tbl[asic_index], port)

def handle_show_firmware_show_cmd_arg_tbl_notification(fvp, xcvrd_show_fw_cmd_sts_tbl, xcvrd_show_fw_rsp_tbl, xcvrd_show_fw_res_tbl, asic_index, port, mux_tbl):
        fvp_dict = dict(fvp)

        mux_info_dict = {}
        mux_info_dict['version_self_active'] = 'N/A'
        mux_info_dict['version_self_inactive'] = 'N/A'
        mux_info_dict['version_self_next'] = 'N/A'
        mux_info_dict['version_peer_active'] = 'N/A'
        mux_info_dict['version_peer_inactive'] = 'N/A'
        mux_info_dict['version_peer_next'] = 'N/A'
        mux_info_dict['version_nic_active'] = 'N/A'
        mux_info_dict['version_nic_inactive'] = 'N/A'
        mux_info_dict['version_nic_next'] = 'N/A'

        if "firmware_version" in fvp_dict:


            status = 'False'
            physical_port = get_ycable_physical_port_from_logical_port(port)
            if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
                # error scenario update table accordingly
                helper_logger.log_warning("Error: Could not get physical port for cli cmd show firmware port {}".format(port))
                set_result_and_delete_port('status', status, xcvrd_show_fw_cmd_sts_tbl[asic_index], xcvrd_show_fw_rsp_tbl[asic_index], port)
                set_show_firmware_fields(port, mux_info_dict, xcvrd_show_fw_res_tbl[asic_index])
                return -1

            port_instance = get_ycable_port_instance_from_logical_port(port)
            if port_instance is None or port_instance in port_mapping_error_values:
                # error scenario update table accordingly
                helper_logger.log_warning("Error: Could not get port instance for cli cmd show firmware command port {}".format(port))
                set_show_firmware_fields(port, mux_info_dict, xcvrd_show_fw_res_tbl[asic_index])
                set_result_and_delete_port('status', status, xcvrd_show_fw_cmd_sts_tbl[asic_index], xcvrd_show_fw_rsp_tbl[asic_index], port)
                return -1

            with y_cable_port_locks[physical_port]:
                try:
                    read_side = port_instance.get_read_side()
                except Exception as e:
                    read_side = None
                    helper_logger.log_warning("Failed to execute the get_read_side API for port {} due to {}".format(physical_port,repr(e)))
            if read_side is None or read_side is port_instance.EEPROM_ERROR or read_side < 0:

                status = 'False'
                helper_logger.log_warning("Error: Could not get read side for cli cmd show firmware port {}".format(port))
                set_show_firmware_fields(port, mux_info_dict, xcvrd_show_fw_res_tbl[asic_index])
                set_result_and_delete_port('status', status, xcvrd_show_fw_cmd_sts_tbl[asic_index], xcvrd_show_fw_rsp_tbl[asic_index], port)
                return -1


            get_firmware_dict(physical_port, port_instance, port_instance.TARGET_NIC, "nic", mux_info_dict, port, mux_tbl)
            if read_side == port_instance.TARGET_TOR_A:
                get_firmware_dict(physical_port, port_instance, port_instance.TARGET_TOR_A, "self", mux_info_dict, port, mux_tbl)
                get_firmware_dict(physical_port, port_instance, port_instance.TARGET_TOR_B, "peer", mux_info_dict, port, mux_tbl)
            else:
                get_firmware_dict(physical_port, port_instance, port_instance.TARGET_TOR_A, "peer", mux_info_dict, port, mux_tbl)
                get_firmware_dict(physical_port, port_instance, port_instance.TARGET_TOR_B, "self", mux_info_dict, port, mux_tbl)

            status = 'True'
            set_show_firmware_fields(port, mux_info_dict, xcvrd_show_fw_res_tbl[asic_index])
            set_result_and_delete_port('status', status, xcvrd_show_fw_cmd_sts_tbl[asic_index], xcvrd_show_fw_rsp_tbl[asic_index], port)
        else:
            helper_logger.log_error("Wrong param for cli cmd show firmware port {}".format(port))
            set_show_firmware_fields(port, mux_info_dict, xcvrd_show_fw_res_tbl[asic_index])
            set_result_and_delete_port('status', 'False', xcvrd_show_fw_cmd_sts_tbl[asic_index], xcvrd_show_fw_rsp_tbl[asic_index], port)

def handle_config_firmware_acti_cmd_arg_tbl_notification(fvp, xcvrd_acti_fw_cmd_sts_tbl, xcvrd_acti_fw_rsp_tbl, xcvrd_acti_fw_cmd_arg_tbl, asic_index, port):

    fvp_dict = dict(fvp)
    status = 'False'

    if "activate_firmware" in fvp_dict:
        file_name = fvp_dict["activate_firmware"]

        (hitless, mode, res_dir) = gather_arg_from_db_and_check_for_type(xcvrd_acti_fw_cmd_arg_tbl[asic_index], port, "activate_firmware", fvp_dict, "hitless")


        if hitless is not None:
            hitless = False
        else:
            hitless = True

        if file_name == 'null':
            file_full_path = None
        else:
            file_full_path = '/usr/share/sonic/firmware/{}'.format(file_name)
            if not os.path.isfile(file_full_path):
                helper_logger.log_error("ERROR: cli cmd mux activate firmware file does not exist port {} file {}".format(port, file_name))
                set_result_and_delete_port('status', status, xcvrd_acti_fw_cmd_sts_tbl[asic_index], xcvrd_acti_fw_rsp_tbl[asic_index], port)
                return -1


        physical_port = get_ycable_physical_port_from_logical_port(port)
        if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
            # error scenario update table accordingly
            helper_logger.log_warning("Error: Could not get physical port for cli cmd mux activate firmware port {}".format(port))
            set_result_and_delete_port('status', status, xcvrd_acti_fw_cmd_sts_tbl[asic_index], xcvrd_acti_fw_rsp_tbl[asic_index], port)
            return -1

        port_instance = get_ycable_port_instance_from_logical_port(port)
        if port_instance is None or port_instance in port_mapping_error_values:
            helper_logger.log_warning("Error: Could not get port instance for cli cmd mux activate firmware port {}".format(port))
            # error scenario update table accordingly
            set_result_and_delete_port('status', status, xcvrd_acti_fw_cmd_sts_tbl[asic_index], xcvrd_acti_fw_rsp_tbl[asic_index], port)
            return -1


        with y_cable_port_locks[physical_port]:
            try:
                status = port_instance.activate_firmware(file_full_path, hitless)
                time.sleep(5)
            except Exception as e:
                status = -1
                helper_logger.log_warning("Failed to execute the activate_firmware API for port {} due to {}".format(physical_port,repr(e)))

        set_result_and_delete_port('status', status, xcvrd_acti_fw_cmd_sts_tbl[asic_index], xcvrd_acti_fw_rsp_tbl[asic_index], port)
    else:
        helper_logger.log_error("Wrong param for cli cmd mux activate firmware port {}".format(port))
        set_result_and_delete_port('status', 'False', xcvrd_acti_fw_cmd_sts_tbl[asic_index], xcvrd_acti_fw_rsp_tbl[asic_index], port)


def handle_show_hwmode_swmode_cmd_arg_tbl_notification(fvp, xcvrd_show_hwmode_swmode_cmd_sts_tbl,  xcvrd_show_hwmode_swmode_rsp_tbl, asic_index, port):

    fvp_dict = dict(fvp)

    if "state" in fvp_dict:

        state = 'unknown'
        physical_port = get_ycable_physical_port_from_logical_port(port)
        if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
            # error scenario update table accordingly
            helper_logger.log_error(
                "Error: Could not get physical port for cli cmd show mux hwmode switchmode Y cable port {}".format(port))
            state = 'cable not present'
            set_result_and_delete_port('state', state, xcvrd_show_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_swmode_rsp_tbl[asic_index], port)
            return -1

        port_instance = get_ycable_port_instance_from_logical_port(port)
        if port_instance is None or port_instance in port_mapping_error_values:
            # error scenario update table accordingly
            helper_logger.log_error(
                "Error: Could not get port instance for cli cmd show mux hwmode switchmode Y cable port {}".format(port))
            state = 'not Y-Cable port'
            set_result_and_delete_port('state', state, xcvrd_show_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_swmode_rsp_tbl[asic_index], port)
            return -1

        with y_cable_port_locks[physical_port]:
            try:
                result = port_instance.get_switching_mode()
            except Exception as e:
                result = None
                helper_logger.log_warning("Failed to execute the get_switching_mode for port {} due to {}".format(physical_port,repr(e)))

            if result is None or result == port_instance.EEPROM_ERROR or result < 0:

                helper_logger.log_error(
                    "Error: Could not get read side for cli cmd show mux hwmode switchmode logical port {} and physical port {}".format(port, physical_port))
                set_result_and_delete_port('state', state, xcvrd_show_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_swmode_rsp_tbl[asic_index], port)
                return -1

        if result == port_instance.SWITCHING_MODE_AUTO:
            state = "auto"
        elif result == port_instance.SWITCHING_MODE_MANUAL:
            state = "manual"
        else:
            state = "unknown"
        set_result_and_delete_port('state', state, xcvrd_show_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_swmode_rsp_tbl[asic_index], port)

    else:
        helper_logger.log_error("Error: Incorrect input param for cli cmd show mux hwmode switchmode logical port {}".format(port))
        set_result_and_delete_port('state', 'unknown', xcvrd_show_hwmode_swmode_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_swmode_rsp_tbl[asic_index], port)

def handle_config_hwmode_state_cmd_arg_tbl_notification(fvp, xcvrd_config_hwmode_state_cmd_sts_tbl,  xcvrd_config_hwmode_state_rsp_tbl, hw_mux_cable_tbl, asic_index, port):

    fvp_dict = dict(fvp)

    if "config" in fvp_dict:
        config_state = str(fvp_dict["config"])

        status = 'False'
        physical_port = get_ycable_physical_port_from_logical_port(port)
        if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
            # error scenario update table accordingly
            helper_logger.log_error(
                "Error: Could not get physical port for cli command config mux hwmode state active/standby Y cable port {}".format(port))
            set_result_and_delete_port('result', status, xcvrd_config_hwmode_state_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_state_rsp_tbl[asic_index], port)
            return -1

        port_instance = get_ycable_port_instance_from_logical_port(port)
        if port_instance is None or port_instance in port_mapping_error_values:
            # error scenario update table accordingly
            helper_logger.log_error(
                "Error: Could not get port instance for cli command config mux hwmode state active/standby Y cable port {}".format(port))
            set_result_and_delete_port('result', status, xcvrd_config_hwmode_state_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_state_rsp_tbl[asic_index], port)
            return -1

        with y_cable_port_locks[physical_port]:
            try:
                read_side = port_instance.get_read_side()
            except Exception as e:
                read_side = None
                helper_logger.log_warning("Failed to execute the get_read_side API for port {} due to {}".format(physical_port,repr(e)))

        if read_side is None or read_side is port_instance.EEPROM_ERROR or read_side < 0:

            status = 'False'
            helper_logger.log_error(
                "Error: Could not get read side for cli command config mux hwmode state active/standby Y cable port {}".format(port))
            set_result_and_delete_port('result', status, xcvrd_config_hwmode_state_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_state_rsp_tbl[asic_index], port)
            return -1

        if read_side is port_instance.TARGET_TOR_A:
            if config_state == "active":
                with y_cable_port_locks[physical_port]:
                    try:
                        status = port_instance.toggle_mux_to_tor_a()
                    except Exception as e:
                        status = -1
                        helper_logger.log_warning("Failed to execute the toggle mux ToR A API for port {} due to {}".format(physical_port,repr(e)))
            elif config_state == "standby":
                with y_cable_port_locks[physical_port]:
                    try:
                        status = port_instance.toggle_mux_to_tor_b()
                    except Exception as e:
                        status = -1
                        helper_logger.log_warning("Failed to execute the toggle mux ToR B API for port {} due to {}".format(physical_port,repr(e)))
        elif read_side is port_instance.TARGET_TOR_B:
            if config_state == 'active':
                with y_cable_port_locks[physical_port]:
                    try:
                        status = port_instance.toggle_mux_to_tor_b()
                    except Exception as e:
                        status = -1
                        helper_logger.log_warning("Failed to execute the toggle mux ToR B API for port {} due to {}".format(physical_port,repr(e)))
            elif config_state == "standby":
                with y_cable_port_locks[physical_port]:
                    try:
                        status = port_instance.toggle_mux_to_tor_a()
                    except Exception as e:
                        status = -1
                        helper_logger.log_warning("Failed to execute the toggle mux ToR A API for port {} due to {}".format(physical_port,repr(e)))
        else:
            set_result_and_delete_port('result', status, xcvrd_config_hwmode_state_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_state_rsp_tbl[asic_index], port)
            helper_logger.log_error(
                "Error: Could not get valid config read side for cli command config mux hwmode state active/standby Y cable port {}".format(port))
            return -1

        set_result_and_delete_port('result', status, xcvrd_config_hwmode_state_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_state_rsp_tbl[asic_index], port)
    else:
        helper_logger.log_error("Error: Wrong input param for cli command config mux hwmode state active/standby logical port {}".format(port))
        set_result_and_delete_port('result', 'False', xcvrd_config_hwmode_state_cmd_sts_tbl[asic_index], xcvrd_config_hwmode_state_rsp_tbl[asic_index], port)

def handle_show_hwmode_state_cmd_arg_tbl_notification(fvp, port_tbl, xcvrd_show_hwmode_dir_cmd_sts_tbl,  xcvrd_show_hwmode_dir_rsp_tbl, xcvrd_show_hwmode_dir_res_tbl, hw_mux_cable_tbl, asic_index, port):
    state_db = {}

    fvp_dict = dict(fvp)

    if "state" in fvp_dict:

        presence = "False"

        physical_port = get_ycable_physical_port_from_logical_port(port)
        if physical_port is not None and y_cable_wrapper_get_presence(physical_port):
            presence = "True"

        fvs_log = swsscommon.FieldValuePairs([(str("presence"), str(presence))])
        xcvrd_show_hwmode_dir_res_tbl[asic_index].set(port, fvs_log)

        if physical_port is None or physical_port == PHYSICAL_PORT_MAPPING_ERROR:
            state = 'unknown'
            # error scenario update table accordingly
            helper_logger.log_error(
                "Error: Could not get physical port for cli command show mux hwmode muxdirection Y cable port {}".format(port))
            set_result_and_delete_port('state', state, xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)
            return -1

        (cable_status, cable_type) = check_mux_cable_port_type(port, port_tbl, asic_index)

        if cable_status and cable_type == "active-standby":

            port_instance = get_ycable_port_instance_from_logical_port(port)
            if port_instance is None or port_instance in port_mapping_error_values:
                # error scenario update table accordingly
                state = 'not Y-Cable port'
                helper_logger.log_error(
                    "Error: Could not get port instance for cli command show mux hwmode muxdirection Y cable port {}".format(port))
                set_result_and_delete_port('state', state, xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)
                return -1

            with y_cable_port_locks[physical_port]:
                try:
                    read_side = port_instance.get_read_side()
                except Exception as e:
                    read_side = None
                    helper_logger.log_warning("Failed to execute the get_read_side API for port {} due to {}".format(physical_port,repr(e)))

            if read_side is None or read_side == port_instance.EEPROM_ERROR or read_side < 0:

                state = 'unknown'
                helper_logger.log_warning(
                    "Error: Could not get read side for cli command show mux hwmode muxdirection logical port {} and physical port {}".format(port, physical_port))
                set_result_and_delete_port('state', state, xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)
                return -1

            with y_cable_port_locks[physical_port]:
                try:
                    active_side = port_instance.get_mux_direction()
                except Exception as e:
                    active_side = None
                    helper_logger.log_warning("Failed to execute the get_mux_direction API for port {} due to {}".format(physical_port,repr(e)))

            if active_side is None or active_side == port_instance.EEPROM_ERROR or active_side < 0:

                state = 'unknown'
                helper_logger.log_warning("Error: Could not get active side for cli command show mux hwmode muxdirection logical port {} and physical port {}".format(port, physical_port))

                set_result_and_delete_port('state', state, xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)
                return -1

            if read_side == active_side and (active_side == 1 or active_side == 2):
                state = 'active'
            elif read_side != active_side and (active_side == 1 or active_side == 2):
                state = 'standby'
            else:
                state = 'unknown'
                helper_logger.log_warning("Error: Could not get valid state for cli command show mux hwmode muxdirection logical port {} and physical port {}".format(port, physical_port))
                set_result_and_delete_port('state', state, xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)
                return -1

            set_result_and_delete_port('state', state, xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)

        elif cable_status and cable_type == "active-active":



            (status, fv) = hw_mux_cable_tbl[asic_index].get(port)

            if status is False:
                helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table while responding to cli cmd show mux status {}".format(
                    port, hw_mux_cable_tbl[asic_index].getTableName()))
                set_result_and_delete_port('state', 'unknown', xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)
                return -1

            mux_port_dict = dict(fv)
            read_side = mux_port_dict.get("read_side", None)
            state = mux_port_dict.get("state", None)
            if state is not None:
                set_result_and_delete_port('state', state, xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)
                return

            helper_logger.log_debug("Y_CABLE_DEBUG:before invoking RPC fwd_state read_side = {}".format(read_side))
            # TODO state only for dummy value in this request MSG remove this
            request = linkmgr_grpc_driver_pb2.AdminRequest(portid=DEFAULT_PORT_IDS, state=[0, 0])
            helper_logger.log_debug(
                "Y_CABLE_DEBUG:calling RPC for getting cli forwarding state read_side portid = {} Ethernet port {}".format(read_side, port))

            stub = grpc_port_stubs.get(port, None)
            if stub is None:
                # no need to retry setup channels for mux cli hw mode command
                helper_logger.log_warning("stub is None for getting forwarding state RPC port for cli query {}".format(port))
                set_result_and_delete_port('state', 'unknown', xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)
                return

            ret, response = try_grpc(stub.QueryAdminForwardingPortState, QUERY_ADMIN_FORWARDING_TIMEOUT , request)

            (self_state, peer_state) = parse_grpc_response_forwarding_state(ret, response, read_side, port)
            state = self_state
            set_result_and_delete_port('state', state, xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)
            if response is not None:
                # Debug only, remove this section once Server side is Finalized
                fwd_response_port_ids = response.portid
                fwd_response_port_ids_state = response.state
                helper_logger.log_notice(
                    "forwarding state RPC received response port ids = {} port {}".format(fwd_response_port_ids, port))
                helper_logger.log_notice(
                    "forwarding state RPC received response state values = {} port {}".format(fwd_response_port_ids_state, port))
            else:
                helper_logger.log_notice("response was none cli handle_fwd_state_command_grpc_notification {} ".format(port))

        else:
            helper_logger.log_warning("Error: Wrong input param for cli command show mux hwmode muxdirection logical port {}".format(port))
            set_result_and_delete_port('state', 'unknown', xcvrd_show_hwmode_dir_cmd_sts_tbl[asic_index], xcvrd_show_hwmode_dir_rsp_tbl[asic_index], port)

def parse_grpc_response_hw_mux_cable_change_state(ret, response, portid, port):
    state = 'unknown'
    "return a list of states"
    if ret is True:
        if len(response.portid) > 0 and len(response.state) > 0:
            if response.portid[0] == portid:
                if response.state[0] == True:
                    state = 'active'
                # No other values expected
                elif response.state[0] == False:
                    state = 'standby'
                else:
                    helper_logger.log_warning("recieved an error state while parsing response hw mux no response state for port".format(port))
            else:
                helper_logger.log_warning("recieved an error portid while parsing response hw mux port list size 0 for port".format(port))
        else:
            helper_logger.log_warning("recieved an error portid while parsing response hw mux no portid for port".format(port))

    else:
        helper_logger.log_warning("recieved an error state while parsing response hw mux for port".format(port))
        state = 'unknown'

    return state


def parse_grpc_response_forwarding_state(ret, response, read_side, port):
    self_state = peer_state = 'unknown'

    if ret is True and response is not None:
        if len(response.portid) == 2 and len(response.state) == 2:
            if int(read_side) == 0:
                if response.state[0] == True:
                    self_state = 'active'
                elif response.state[0] == False:
                    self_state = 'standby'
                # No other values expected, should we raise exception/msg
                # TODO handle other responses
                if response.state[1] == True:
                    peer_state = 'active'
                elif response.state[1] == False:
                    peer_state = 'standby'

            elif int(read_side) == 1:
                if response.state[1] == True:
                    self_state = 'active'
                elif response.state[1] == False:
                    self_state = 'standby'
                if response.state[0] == True:
                    peer_state = 'active'
                elif response.state[0] == False:
                    peer_state = 'standby'

        else:
            helper_logger.log_warning("recieved an error port list while parsing response forwarding port state list size 0 {} {}".format(len(response.portid), len(response.state)))
            self_state = 'unknown'
            peer_state = 'unknown'
    else:
        self_state = 'unknown'
        peer_state = 'unknown'

    stat = grpc_port_stats.get(port,None)
    if stat is not None:
        grpc_port_stats[port]["mux_direction_probe_count"] = str(int(stat.get("mux_direction_probe_count", 0)) + 1 )
        grpc_port_stats[port]["peer_mux_direction_probe_count"] = str(int(stat.get("peer_mux_direction_probe_count", 0)) + 1 )
    else:
        grpc_port_stats[port] = {}
        grpc_port_stats[port]["mux_direction_probe_count"] = 0
        grpc_port_stats[port]["peer_mux_direction_probe_count"] = 0

    

    return (self_state, peer_state)


def handle_fwd_state_command_grpc_notification(fvp_m, hw_mux_cable_tbl, fwd_state_response_tbl, asic_index, port, appl_db, port_tbl, grpc_client):

    helper_logger.log_debug("Y_CABLE_DEBUG:recevied the notification fwd state port {}".format(port))
    fvp_dict = dict(fvp_m)

    if "command" in fvp_dict:
        # check if xcvrd got a probe command
        probe_identifier = fvp_dict["command"]

        if probe_identifier == "probe":
            helper_logger.log_debug("Y_CABLE_DEBUG:processing the notification fwd_state port {}".format(port))
            (status, fv) = hw_mux_cable_tbl[asic_index].get(port)
            if status is False:
                helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
                    port, hw_mux_cable_tbl[asic_index].getTableName()))
                return False
            mux_port_dict = dict(fv)
            read_side = mux_port_dict.get("read_side")
            helper_logger.log_debug("Y_CABLE_DEBUG:before invoking RPC fwd_state read_side = {}".format(read_side))
            # TODO state only for dummy value in this request MSG remove this
            request = linkmgr_grpc_driver_pb2.AdminRequest(portid=DEFAULT_PORT_IDS, state=[0, 0])
            helper_logger.log_notice(
                "calling RPC for getting forwarding state port = {} portid {} peer portid {} read_side {}".format(port, read_side, 1 - int(read_side), read_side))

            self_state = "unknown"
            peer_state = "unknown"
            stub = grpc_port_stubs.get(port, None)
            if stub is None:
                helper_logger.log_notice("stub is None for getting admin port forwarding state RPC port {}".format(port))
                retry_setup_grpc_channel_for_port(port, asic_index, port_tbl, grpc_client, fwd_state_response_tbl)
                stub = grpc_port_stubs.get(port, None)
                if stub is None:
                    helper_logger.log_warning(
                        "stub was None for performing fwd mux RPC port {}, setting it up again did not work".format(port))
                    fvs_updated = swsscommon.FieldValuePairs([('response', str(self_state)),
                                                              ('response_peer', str(peer_state))])
                    fwd_state_response_tbl[asic_index].set(port, fvs_updated)
                    return

            ret, response = try_grpc(stub.QueryAdminForwardingPortState, QUERY_ADMIN_FORWARDING_TIMEOUT, request)

            (self_state, peer_state) = parse_grpc_response_forwarding_state(ret, response, read_side, port)
            if response is not None:
                # Debug only, remove this section once Server side is Finalized
                fwd_response_port_ids = response.portid
                fwd_response_port_ids_state = response.state
                helper_logger.log_notice(
                    "forwarding state RPC received response port = {} portids {} read_side {}".format(port, fwd_response_port_ids,read_side))
                helper_logger.log_notice(
                    "forwarding state RPC received response port = {} state values = {} read_side {}".format(port, fwd_response_port_ids_state, read_side))
            else:
                helper_logger.log_notice("response was none handle_fwd_state_command_grpc_notification {} ".format(port))

            fvs_updated = swsscommon.FieldValuePairs([('response', str(self_state)),
                                                      ('response_peer', str(peer_state))])
            fwd_state_response_tbl[asic_index].set(port, fvs_updated)
            helper_logger.log_debug("Y_CABLE_DEBUG:processed the notification fwd state cleanly")
            return True
        else:
            helper_logger.log_warning("probe val not present in the notification fwd state handling port {}".format(port))
    else:
        helper_logger.log_warning("command key not present in the notification fwd state handling port {}".format(port))


def handle_hw_mux_cable_table_grpc_notification(fvp, hw_mux_cable_tbl, asic_index, grpc_metrics_tbl, peer, port, port_tbl, grpc_client, fwd_state_response_tbl):

    # entering this section signifies a gRPC start for state
    # change request from swss so initiate recording in mux_metrics table
    time_start = datetime.datetime.utcnow().strftime("%Y-%b-%d %H:%M:%S.%f")
    # This check might be redundant, to check, the presence of this Port in keys
    # in logical_port_list but keep for now for coherency
    # also skip checking in logical_port_list inside sfp_util

    helper_logger.log_debug("Y_CABLE_DEBUG:recevied the notification mux hw state")
    fvp_dict = dict(fvp)
    toggle_side = "self"

    if "state" in fvp_dict:
        # got a state change
        new_state = fvp_dict["state"]
        requested_status = new_state
        if requested_status in ["active", "standby"]:

            (status, fvs) = hw_mux_cable_tbl[asic_index].get(port)
            if status is False:
                helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
                    port, hw_mux_cable_tbl[asic_index].getTableName()))
                return
            helper_logger.log_debug("Y_CABLE_DEBUG processing the notification mux hw state port {}".format(port))
            mux_port_dict = dict(fvs)
            old_state = mux_port_dict.get("state", None)
            read_side = mux_port_dict.get("read_side", None)
            curr_read_side = int(read_side)
            # Now whatever is the state requested, call gRPC to update the soc state appropriately
            if peer == True:
                curr_read_side = 1-int(read_side)
                toggle_side = "peer"

            if new_state == "active":
                state_req = 1
            elif new_state == "standby":
                state_req = 0

            helper_logger.log_notice(
                "calling RPC for hw mux_cable set state ispeer = {} port {} portid {} read_side {} state requested {}".format(peer, port, curr_read_side, read_side, new_state))

            request = linkmgr_grpc_driver_pb2.AdminRequest(portid=[curr_read_side], state=[state_req])

            stub = grpc_port_stubs.get(port, None)
            if stub is None:
                helper_logger.log_debug("Y_CABLE_DEBUG:stub is None for performing hw mux RPC port {}".format(port))
                retry_setup_grpc_channel_for_port(port, asic_index, port_tbl, grpc_client, fwd_state_response_tbl)
                stub = grpc_port_stubs.get(port, None)
                if stub is None:
                    helper_logger.log_warning(
                            "gRPC channel was initially not setup for performing hw mux set state RPC port {}, trying to set gRPC channel again also did not work, posting unknown state for stateDB:HW_MUX_CABLE_TABLE".format(port))
                    active_side = new_state = 'unknown'
                    time_end = datetime.datetime.utcnow().strftime("%Y-%b-%d %H:%M:%S.%f")
                    fvs_metrics = swsscommon.FieldValuePairs([('xcvrd_switch_{}_{}_start'.format(toggle_side, new_state), str(time_start)),
                                                              ('xcvrd_switch_{}_{}_end'.format(toggle_side, new_state), str(time_end))])
                    grpc_metrics_tbl[asic_index].set(port, fvs_metrics)

                    fvs_updated = swsscommon.FieldValuePairs([('state', new_state),
                                                              ('read_side', read_side),
                                                              ('active_side', str(active_side))])
                    hw_mux_cable_tbl[asic_index].set(port, fvs_updated)
                    return

            ret, response = try_grpc(stub.SetAdminForwardingPortState, SET_ADMIN_FORWARDING_TIMEOUT, request)

            if response is not None:
                # Debug only, remove this section once Server side is Finalized
                hw_response_port_ids = response.portid
                hw_response_port_ids_state = response.state
                helper_logger.log_notice(
                    "Set admin state RPC received response port {} port ids = {} curr_read_side {} read_side {}".format(port, hw_response_port_ids, curr_read_side, read_side))
                helper_logger.log_notice(
                    "Set admin state RPC received response port {} state values = {} curr_read_side {} read_side {}".format(port, hw_response_port_ids_state, curr_read_side, read_side))
            else:
                helper_logger.log_notice("response was none hw_mux_cable_table_grpc_notification {} ".format(port))

            active_side = parse_grpc_response_hw_mux_cable_change_state(ret, response, curr_read_side, port)

            if active_side == "unknown":
                helper_logger.log_warning(
                    "ERR: Got a change event for updating gRPC but could not toggle the mux-direction for port {} state from {} to {}, writing unknown".format(port, old_state, new_state))
                new_state = 'unknown'

            time_end = datetime.datetime.utcnow().strftime("%Y-%b-%d %H:%M:%S.%f")
            fvs_metrics = swsscommon.FieldValuePairs([('xcvrd_switch_{}_{}_start'.format(toggle_side, new_state), str(time_start)),
                                                      ('xcvrd_switch_{}_{}_end'.format(toggle_side, new_state), str(time_end))])
            grpc_metrics_tbl[asic_index].set(port, fvs_metrics)

            fvs_updated = swsscommon.FieldValuePairs([('state', new_state),
                                                      ('read_side', read_side),
                                                      ('active_side', str(active_side))])
            hw_mux_cable_tbl[asic_index].set(port, fvs_updated)
            helper_logger.log_debug("Y_CABLE_DEBUG: processed the notification hw mux state cleanly {}".format(port))
        else:
            helper_logger.log_info("Got a change event on port {} of table {} that does not contain state".format(
                port, swsscommon.APP_HW_MUX_CABLE_TABLE_NAME))


def handle_ycable_active_standby_probe_notification(cable_type, fvp_dict, appl_db, hw_mux_cable_tbl, port_m, asic_index,  y_cable_response_tbl):

    if cable_type == 'active-standby' and "command" in fvp_dict:

        # check if xcvrd got a probe command
        probe_identifier = fvp_dict["command"]

        if probe_identifier == "probe":

            (status, fv) = hw_mux_cable_tbl[asic_index].get(port_m)

            if status is False:
                helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
                    port_m, hw_mux_cable_tbl[asic_index].getTableName()))
                return False

            mux_port_dict = dict(fv)
            read_side = mux_port_dict.get("read_side")
            update_appdb_port_mux_cable_response_table(port_m, asic_index, appl_db, int(read_side), y_cable_response_tbl)

            return True

def handle_ycable_enable_disable_tel_notification(fvp_m, key):

    global disable_telemetry

    if fvp_m:

        if key != "Y_CABLE":
            return

        fvp_dict = dict(fvp_m)
        if "log_verbosity" in fvp_dict:
            # check if xcvrd got a probe command
            probe_identifier = fvp_dict["log_verbosity"]

            if probe_identifier == "debug":
                helper_logger.set_min_log_priority_debug()

            elif probe_identifier == "notice":
                helper_logger.set_min_log_priority_notice()
        if "disable_telemetry" in fvp_dict:
            # check if xcvrd got a probe command
            enable = fvp_dict["disable_telemetry"]

            helper_logger.log_notice("Y_CABLE_DEBUG: trying to enable/disable telemetry flag to {}".format(enable))
            if enable == "True":
                disable_telemetry = True

            elif enable == "False":
                disable_telemetry = False

# Thread wrapper class to update y_cable status periodically
class YCableTableUpdateTask(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.exc = None
        self.task_stopping_event = threading.Event()
        self.hw_mux_cable_tbl_keys = {}

        self.table_helper =  y_cable_table_helper.YcableTableUpdateTableHelper()
       
    def task_worker(self):

        # Connect to STATE_DB and APPL_DB and get both the HW_MUX_STATUS_TABLE info

        sel = swsscommon.Select()

        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            # Open a handle to the Application database, in all namespaces
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            self.hw_mux_cable_tbl_keys[asic_id] = self.table_helper.get_hw_mux_cable_tbl()[asic_id].getKeys()
            sel.addSelectable(self.table_helper.get_status_tbl()[asic_id])
            sel.addSelectable(self.table_helper.get_status_tbl_peer()[asic_id])
            sel.addSelectable(self.table_helper.get_fwd_state_command_tbl()[asic_id])
            sel.addSelectable(self.table_helper.get_mux_cable_command_tbl()[asic_id])


        # Listen indefinitely for changes to the HW_MUX_CABLE_TABLE in the Application DB's
        while True:
            # Use timeout to prevent ignoring the signals we want to handle
            # in signal_handler() (e.g. SIGTERM for graceful shutdown)

            if self.task_stopping_event.is_set():
                break

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

            while True:
                (port, op, fvp) = self.table_helper.get_status_tbl()[asic_index].pop()
                if not port:
                    break

                helper_logger.log_debug("Y_CABLE_DEBUG: received an event for port transition {} {}".format(port, threading.currentThread().getName()))

                # entering this section signifies a start for xcvrd state
                # change request from swss so initiate recording in mux_metrics table
                time_start = datetime.datetime.utcnow().strftime("%Y-%b-%d %H:%M:%S.%f")
                if fvp:
                    # This check might be redundant, to check, the presence of this Port in keys
                    # in logical_port_list but keep for now for coherency
                    # also skip checking in logical_port_list inside sfp_util
                    if port not in self.hw_mux_cable_tbl_keys[asic_index]:
                        continue

                    (status, cable_type) = check_mux_cable_port_type(port, self.table_helper.get_port_tbl(), asic_index)

                    if status:

                        if cable_type == 'active-standby':
                            fvp_dict = dict(fvp)

                            if "state" in fvp_dict:
                                # got a state change
                                new_status = fvp_dict["state"]
                                requested_status = new_status
                                (status, fvs) = self.table_helper.get_hw_mux_cable_tbl()[asic_index].get(port)
                                if status is False:
                                    helper_logger.log_debug("Could not retreive fieldvalue pairs for {}, inside state_db table {}".format(
                                        port, self.table_helper.get_hw_mux_cable_tbl()[asic_index].getTableName()))
                                    continue
                                mux_port_dict = dict(fvs)
                                old_status = mux_port_dict.get("state", None)
                                read_side = mux_port_dict.get("read_side", None)
                                # Now whatever is the state requested, toggle the mux appropriately
                                helper_logger.log_debug("Y_CABLE_DEBUG: xcvrd trying to transition port {} from {} to {} read side {}".format(port, old_status, new_status, read_side))
                                (active_side, read_side) = update_tor_active_side(read_side, new_status, port)
                                if active_side == -1:
                                    helper_logger.log_warning("ERR: Got a change event for toggle but could not toggle the mux-direction for port {} state from {} to {}, writing unknown".format(
                                        port, old_status, new_status))
                                    new_status = 'unknown'

                                helper_logger.log_debug("Y_CABLE_DEBUG: xcvrd successful to transition port {} from {} to {} and write back to the DB {}".format(port, old_status, new_status, threading.currentThread().getName()))
                                helper_logger.log_notice("Got a change event for toggle the mux-direction active side for port {} state requested {} from old state {} to new state {} read_side  {} thread id {}".format(port, requested_status, old_status, new_status, read_side, threading.currentThread().getName()))
                                time_end = datetime.datetime.utcnow().strftime("%Y-%b-%d %H:%M:%S.%f")
                                fvs_metrics = swsscommon.FieldValuePairs([('xcvrd_switch_{}_start'.format(new_status), str(time_start)),
                                                                          ('xcvrd_switch_{}_end'.format(new_status), str(time_end))])
                                self.table_helper.get_mux_metrics_tbl()[asic_index].set(port, fvs_metrics)

                                fvs_updated = swsscommon.FieldValuePairs([('state', new_status),
                                                                          ('read_side', str(read_side)),
                                                                          ('active_side', str(active_side))])
                                self.table_helper.get_hw_mux_cable_tbl()[asic_index].set(port, fvs_updated)
                            else:
                                helper_logger.log_info("Got a change event on port {} of table {} that does not contain state".format(
                                    port, swsscommon.APP_HW_MUX_CABLE_TABLE_NAME))

                        elif cable_type == "active-active":

                            if fvp:
                                handle_hw_mux_cable_table_grpc_notification(
                                    fvp, self.table_helper.get_hw_mux_cable_tbl(), asic_index, self.table_helper.get_mux_metrics_tbl(), False, port, self.table_helper.get_port_tbl(), self.table_helper.get_grpc_config_tbl(), self.table_helper.get_fwd_state_response_tbl())


            while True:
                (port_m, op_m, fvp_m) = self.table_helper.get_mux_cable_command_tbl()[asic_index].pop()

                if not port_m:
                    break
                helper_logger.log_debug("Y_CABLE_DEBUG: received a probe for port status {} {}".format(port_m, threading.currentThread().getName()))

                if fvp_m:

                    if port_m not in self.hw_mux_cable_tbl_keys[asic_index]:
                        continue

                    fvp_dict = dict(fvp_m)

                    (status, cable_type) = check_mux_cable_port_type(port_m, self.table_helper.get_port_tbl(), asic_index)

                    if status:
                        handle_ycable_active_standby_probe_notification(cable_type, fvp_dict, self.table_helper.get_appl_db(), self.table_helper.get_hw_mux_cable_tbl(), port_m, asic_index, self.table_helper.get_y_cable_response_tbl())


            while True:
                (port_m, op_m, fvp_m) = self.table_helper.get_fwd_state_command_tbl()[asic_index].pop()

                if not port_m:
                    break

                helper_logger.log_debug("Y_CABLE_DEBUG: received a probe for Forwarding state using gRPC port status {} {}".format(port_m, threading.currentThread().getName()))
                (status, cable_type) = check_mux_cable_port_type(port_m, self.table_helper.get_port_tbl(), asic_index)

                if status is False or cable_type != "active-active":
                    break

                if fvp_m:
                    handle_fwd_state_command_grpc_notification(
                        fvp_m, self.table_helper.get_hw_mux_cable_tbl(), self.table_helper.get_fwd_state_response_tbl(), asic_index, port_m, self.table_helper.get_appl_db(), self.table_helper.get_port_tbl(), self.table_helper.get_grpc_config_tbl())

            while True:
                (port_n, op_n, fvp_n) = self.table_helper.get_status_tbl_peer()[asic_index].pop()
                if not port_n:
                    break

                (status, cable_type) = check_mux_cable_port_type(port_n, self.table_helper.get_port_tbl(), asic_index)

                if status is False or cable_type != "active-active":
                    break

                if fvp_n:
                    handle_hw_mux_cable_table_grpc_notification(
                        fvp_n, self.table_helper.get_hw_mux_cable_tbl_peer(), asic_index, self.table_helper.get_mux_metrics_tbl(), True, port_n, self.table_helper.get_port_tbl(), self.table_helper.get_grpc_config_tbl(), self.table_helper.get_fwd_state_response_tbl())

    def run(self):
        if self.task_stopping_event.is_set():
            return

        try:
            self.task_worker()
        except Exception as e:
            helper_logger.log_error("Exception occured at child thread YCableTableUpdateTask due to {} {}".format(repr(e), traceback.format_exc()))
            self.exc = e


    def join(self):
        threading.Thread.join(self)

        if self.exc:
            raise self.exc

class YCableCliUpdateTask(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.exc = None
        self.task_download_firmware_thread = {}
        self.task_stopping_event = threading.Event()
        self.cli_table_helper =  y_cable_table_helper.YcableCliUpdateTableHelper()
        self.name = "YCableCliUpdateTask"


    def task_cli_worker(self):


        sel = swsscommon.Select()


        # Get the namespaces in the platform
        namespaces = multi_asic.get_front_end_namespaces()
        for namespace in namespaces:
            # Open a handle to the Application database, in all namespaces
            asic_id = multi_asic.get_asic_index_from_namespace(namespace)
            sel.addSelectable(self.cli_table_helper.xcvrd_log_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_down_fw_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_down_fw_status_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_acti_fw_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_roll_fw_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_show_fw_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_show_hwmode_dir_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_config_hwmode_state_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_show_hwmode_swmode_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_config_hwmode_swmode_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_config_prbs_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_config_loop_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_show_event_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_show_fec_cmd_tbl[asic_id])
            sel.addSelectable(self.cli_table_helper.xcvrd_show_ber_cmd_tbl[asic_id])

        # Listen indefinitely for changes to the XCVRD_CMD_TABLE in the Application DB's
        while True:
            # Use timeout to prevent ignoring the signals we want to handle
            # in signal_handler() (e.g. SIGTERM for graceful shutdown)

            if self.task_stopping_event.is_set():
                break

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


            while True:
                (key, op_m, fvp_m) = self.cli_table_helper.xcvrd_log_tbl[asic_index].pop()

                if not key:
                    break

                if fvp_m:
                    helper_logger.log_notice("Y_CABLE_DEBUG: trying to enable/disable debug logs")
                    handle_ycable_enable_disable_tel_notification(fvp_m, 'Y_CABLE')
                    break

            while True:
                # show muxcable hwmode state <port>
                (port, op, fvp) = self.cli_table_helper.xcvrd_show_hwmode_dir_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_show_hwmode_state_cmd_arg_tbl_notification(fvp, self.cli_table_helper.port_tbl, self.cli_table_helper.xcvrd_show_hwmode_dir_cmd_sts_tbl, self.cli_table_helper.xcvrd_show_hwmode_dir_rsp_tbl, self.cli_table_helper.xcvrd_show_hwmode_dir_res_tbl, self.cli_table_helper.hw_mux_cable_tbl, asic_index, port)
                    break

            while True:
                # Config muxcable hwmode state <active/standby> <port>
                (port, op, fvp) = self.cli_table_helper.xcvrd_config_hwmode_state_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_config_hwmode_state_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_config_hwmode_state_cmd_sts_tbl,  self.cli_table_helper.xcvrd_config_hwmode_state_rsp_tbl, self.cli_table_helper.hw_mux_cable_tbl, asic_index, port)
                    break


            while True:
                # Config muxcable hwmode setswitchmode <auto/manual> <port>
                (port, op, fvp) = self.cli_table_helper.xcvrd_show_hwmode_swmode_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_show_hwmode_swmode_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_show_hwmode_swmode_cmd_sts_tbl, self.cli_table_helper.xcvrd_show_hwmode_swmode_rsp_tbl, asic_index, port)
                    break

            while True:
                # Config muxcable hwmode setswitchmode <auto/manual> <port>
                (port, op, fvp) = self.cli_table_helper.xcvrd_config_hwmode_swmode_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                   handle_config_mux_switchmode_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_config_hwmode_swmode_cmd_sts_tbl, self.cli_table_helper.xcvrd_config_hwmode_swmode_rsp_tbl, asic_index, port)
                   break

            while True:
                (port, op, fvp) = self.cli_table_helper.xcvrd_down_fw_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_config_firmware_down_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_down_fw_cmd_sts_tbl, self.cli_table_helper.xcvrd_down_fw_rsp_tbl, asic_index, port, self.task_download_firmware_thread)
                    break

            while True:
                (port, op, fvp) = self.cli_table_helper.xcvrd_show_fw_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_show_firmware_show_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_show_fw_cmd_sts_tbl, self.cli_table_helper.xcvrd_show_fw_rsp_tbl, self.cli_table_helper.xcvrd_show_fw_res_tbl, asic_index, port, self.cli_table_helper.mux_tbl)
                    break

            while True:
                (port, op, fvp) = self.cli_table_helper.xcvrd_acti_fw_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_config_firmware_acti_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_acti_fw_cmd_sts_tbl, self.cli_table_helper.xcvrd_acti_fw_rsp_tbl, self.cli_table_helper.xcvrd_acti_fw_cmd_arg_tbl, asic_index, port)
                    break


            while True:
                (port, op, fvp) = self.cli_table_helper.xcvrd_roll_fw_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_config_firmware_roll_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_roll_fw_cmd_sts_tbl, self.cli_table_helper.xcvrd_roll_fw_rsp_tbl, asic_index, port)
                    break

            while True:
                (port, op, fvp) = self.cli_table_helper.xcvrd_config_prbs_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_config_prbs_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_config_prbs_cmd_arg_tbl, self.cli_table_helper.xcvrd_config_prbs_cmd_sts_tbl, self.cli_table_helper.xcvrd_config_prbs_rsp_tbl, asic_index, port)
                    break

            while True:
                (port, op, fvp) = self.cli_table_helper.xcvrd_config_loop_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_config_loop_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_config_loop_cmd_arg_tbl, self.cli_table_helper.xcvrd_config_loop_cmd_sts_tbl, self.cli_table_helper.xcvrd_config_loop_rsp_tbl, asic_index, port)
                    break

            while True:
                (port, op, fvp) = self.cli_table_helper.xcvrd_show_event_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:

                    handle_show_event_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_show_event_cmd_sts_tbl, self.cli_table_helper.xcvrd_show_event_rsp_tbl, self.cli_table_helper.xcvrd_show_event_res_tbl, asic_index, port)
                    break

            while True:
                (port, op, fvp) = self.cli_table_helper.xcvrd_show_fec_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:

                    handle_get_fec_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_show_fec_rsp_tbl, self.cli_table_helper.xcvrd_show_fec_cmd_sts_tbl, self.cli_table_helper.xcvrd_show_fec_res_tbl, asic_index, port)
                    break

            while True:
                (port, op, fvp) = self.cli_table_helper.xcvrd_show_ber_cmd_tbl[asic_index].pop()

                if not port:
                    break

                if fvp:
                    handle_show_ber_cmd_arg_tbl_notification(fvp, self.cli_table_helper.xcvrd_show_ber_cmd_arg_tbl, self.cli_table_helper.xcvrd_show_ber_rsp_tbl, self.cli_table_helper.xcvrd_show_ber_cmd_sts_tbl, self.cli_table_helper.xcvrd_show_ber_res_tbl, asic_index, port)

                    break

    def run(self):
        if self.task_stopping_event.is_set():
            return

        try:
            self.task_cli_worker()
        except Exception as e:
            helper_logger.log_error("Exception occured at child thread YcableCliUpdateTask due to {} {}".format(repr(e), traceback.format_exc()))
            self.exc = e
 
    def join(self):
 
        threading.Thread.join(self)
 
        for key, value in self.task_download_firmware_thread.items():
            self.task_download_firmware_thread[key].join()
        helper_logger.log_info("stopped all thread")
        if self.exc is not None:
 
            raise self.exc

class GracefulRestartClient:
    def __init__(self, port, channel: grpc.aio.secure_channel, read_side):
        self.port = port
        self.stub = linkmgr_grpc_driver_pb2_grpc.GracefulRestartStub(channel)
        self.request_queue = asyncio.Queue()
        self.response_queue = asyncio.Queue()
        self.read_side = read_side

    async def send_request_and_get_response(self):
        while True:
            tor = await self.request_queue.get()
            request = linkmgr_grpc_driver_pb2.GracefulAdminRequest(tor=tor)
            response = None 
            try:
                response_stream = self.stub.NotifyGracefulRestartStart(request)
                index = 0
                async for response in response_stream:
                    helper_logger.log_notice("Async client received from direct read period port = {}: period = {} index = {} guid = {} notifytype {} msgtype = {}".format(self.port, response.period, index, response.guid, response.notifytype, response.msgtype))
                    helper_logger.log_debug("Async Debug only :{} {}".format(dir(response_stream), dir(response)))
                    index = index+1
                    if response == grpc.aio.EOF:
                        break
                helper_logger.log_notice("Async client finished loop from direct read period port:{} ".format(self.port))
                index = index+1
            except grpc.RpcError as e:
                helper_logger.log_notice("Async client port = {} exception occured because of {} ".format(self.port, e.code()))

            await self.response_queue.put(response)

    async def process_response(self):
        while True:
            response = await self.response_queue.get()
            helper_logger.log_debug("Async recieved a response from {} {}".format(self.port, response))
            # do something with response
            if response is not None:
                await asyncio.sleep(response.period)
            else:
                await asyncio.sleep(20)

            if self.read_side == 0:
                tor_side = linkmgr_grpc_driver_pb2.ToRSide.UPPER_TOR
            else:
                tor_side = linkmgr_grpc_driver_pb2.ToRSide.LOWER_TOR
            await self.request_queue.put(tor_side)

    async def notify_graceful_restart_start(self, tor: linkmgr_grpc_driver_pb2.ToRSide):
        await self.request_queue.put(tor)


class YCableAsyncNotificationTask(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

        self.exc = None
        self.task_stopping_event = threading.Event()
        self.table_helper =  y_cable_table_helper.YcableAsyncNotificationTableHelper()
        self.read_side = process_loopback_interface_and_get_read_side(self.table_helper.loopback_keys)
        self.name = "YCableAsyncNotificationTask"

    async def task_worker(self):

        # Create tasks for all ports  
        logical_port_list = y_cable_platform_sfputil.logical
        tasks = []
        for logical_port_name in logical_port_list:
            if self.task_stopping_event.is_set():
                break

            # Get the asic to which this port belongs
            asic_index = y_cable_platform_sfputil.get_asic_id_for_logical_port(logical_port_name)
            (status, fvs) = self.table_helper.get_port_tbl()[asic_index].get(logical_port_name)
            if status is False:
                helper_logger.log_debug(
                    "Could not retreive fieldvalue pairs for {}, inside config_db table {}".format(logical_port_name, self.table_helper.get_port_tbl()[asic_index].getTableName()))
                continue

            else:
                # Convert list of tuples to a dictionary
                mux_table_dict = dict(fvs)
                if "state" in mux_table_dict and "soc_ipv4" in mux_table_dict:

                    soc_ipv4_full = mux_table_dict.get("soc_ipv4", None)
                    if soc_ipv4_full is not None:
                        soc_ipv4 = soc_ipv4_full.split('/')[0]

                        channel, stub = setup_grpc_channel_for_port(logical_port_name, soc_ipv4, asic_index, self.table_helper.get_grpc_config_tbl(), self.table_helper.get_fwd_state_response_tbl(), True)

                        client = GracefulRestartClient(logical_port_name, channel, read_side)
                        tasks.append(asyncio.create_task(client.send_request_and_get_response()))
                        tasks.append(asyncio.create_task(client.process_response()))

                        if self.read_side == 0:
                            tor_side = linkmgr_grpc_driver_pb2.ToRSide.UPPER_TOR
                        else:
                            tor_side = linkmgr_grpc_driver_pb2.ToRSide.LOWER_TOR

                        tasks.append(asyncio.create_task(client.notify_graceful_restart_start(tor_side)))

        await asyncio.gather(*tasks) 

    def run(self):
        if self.task_stopping_event.is_set():
            return

        try:
            asyncio.run(self.task_worker())
        except Exception as e:
            helper_logger.log_error("Exception occured at child thread YcableCliUpdateTask due to {} {}".format(repr(e), traceback.format_exc()))
            self.exc = e
 
    def join(self):
 
        threading.Thread.join(self)
 
        helper_logger.log_info("stopped all thread")
        if self.exc is not None:
 
            raise self.exc
