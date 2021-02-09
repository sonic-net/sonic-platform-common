# sfputilbase.py
#
# Base class for creating platform-specific SFP transceiver interfaces for SONiC
#

from __future__ import print_function

try:
    import abc
    import binascii
    import os
    import re
    import ast
    import json
    from sonic_py_common.interface import backplane_prefix
    from swsssdk import ConfigDBConnector
    from sonic_py_common import logger
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

SYSLOG_IDENTIFIER = "sfputilhelper"
helper_logger = logger.Logger(SYSLOG_IDENTIFIER)

class SfpUtilHelper(object):
    # List to specify filter for sfp_ports
    # Needed by platforms like dni-6448 which
    # have only a subset of ports that support sfp
    sfp_ports = []

    # List of logical port names available on a system
    """ ["swp1", "swp5", "swp6", "swp7", "swp8" ...] """
    logical = []

    # Mapping of logical port names available on a system to ASIC num
    logical_to_asic = {}

    # dicts for easier conversions between logical, physical and bcm ports
    logical_to_physical = {}

    physical_to_logical = {}
    physical_to_phyaddrs = {}

    def __init__(self):
        pass

    def read_porttab_mappings(self, porttabfile, asic_inst=0, get_ports_from_db=False):
        logical = []
        logical_to_physical = {}
        physical_to_logical = {}
        last_fp_port_index = 0
        last_portname = ""
        first = 1
        port_pos_in_file = 0
        parse_fmt_port_config_ini = False

        if get_ports_from_db:
            config_db = ConfigDBConnector()
            config_db.connect()
            ports_table = config_db.get_table("PORT")
            ports = ast.literal_eval(json.dumps(ports_table))
            if not ports:
                helper_logger.log_error("failed to get ports data from config DB")
                return

            for port_alias in ports.keys():
                self.logical.append(port_alias)

                if 'index' in ports[port_alias].keys():
                    port_idx = int(ports[port_alias]['index'])
                    self.logical_to_physical[port_alias] = [port_idx]

                    if self.physical_to_logical.get(port_idx) is None:
                        self.physical_to_logical[port_idx] = [port_alias]
                    else:
                        self.physical_to_logical[port_idx].append(port_alias)

                    self.logical_to_asic[port_alias] = asic_inst
                else:
                    helper_logger.log_error("failed to parse port {} data, port index is missing".format(port_alias))
            return

        try:
            f = open(porttabfile)
        except:
            raise

        parse_fmt_port_config_ini = (os.path.basename(porttabfile) == "port_config.ini")

        # Read the porttab file and generate dicts
        # with mapping for future reference.
        #
        # TODO: Refactor this to use the portconfig.py module that now
        # exists as part of the sonic-config-engine package.
        title = []
        for line in f:
            line.strip()
            if re.search("^#", line) is not None:
                # The current format is: # name lanes alias index speed
                # Where the ordering of the columns can vary
                title = line.split()[1:]
                continue

            # Parsing logic for 'port_config.ini' file
            if (parse_fmt_port_config_ini):
                # bcm_port is not explicitly listed in port_config.ini format
                # Currently we assume ports are listed in numerical order according to bcm_port
                # so we use the port's position in the file (zero-based) as bcm_port
                portname = line.split()[0]

                # Ignore if this is an internal backplane interface
                if portname.startswith(backplane_prefix()):
                    continue

                bcm_port = str(port_pos_in_file)

                if "index" in title:
                    fp_port_index = int(line.split()[title.index("index")])
                # Leave the old code for backward compatibility
                elif "asic_port_name" not in title and len(line.split()) >= 4:
                    fp_port_index = int(line.split()[3])
                else:
                    fp_port_index = portname.split("Ethernet").pop()
                    fp_port_index = int(fp_port_index.split("s").pop(0))/4
            else:  # Parsing logic for older 'portmap.ini' file
                (portname, bcm_port) = line.split("=")[1].split(",")[:2]

                fp_port_index = portname.split("Ethernet").pop()
                fp_port_index = int(fp_port_index.split("s").pop(0))/4

            if ((len(self.sfp_ports) > 0) and (fp_port_index not in self.sfp_ports)):
                continue

            if first == 1:
                # Initialize last_[physical|logical]_port
                # to the first valid port
                last_fp_port_index = fp_port_index
                last_portname = portname
                first = 0

            logical.append(portname)

            # Mapping of logical port names available on a system to ASIC instance
            self.logical_to_asic[portname] = asic_inst

            logical_to_physical[portname] = [fp_port_index]
            if physical_to_logical.get(fp_port_index) is None:
                physical_to_logical[fp_port_index] = [portname]
            else:
                physical_to_logical[fp_port_index].append(
                    portname)

            last_fp_port_index = fp_port_index
            last_portname = portname

            port_pos_in_file += 1

        self.logical.extend(logical)
        self.logical_to_physical.update(logical_to_physical)
        self.physical_to_logical.update(physical_to_logical)

        """
        print("logical: " + self.logical)
        print("logical to physical: " + self.logical_to_physical)
        print("physical to logical: " + self.physical_to_logical)
        """

    def read_all_porttab_mappings(self, platform_dir, num_asic_inst):
        # In multi asic scenario, get all the port_config files for different asics
         for inst in range(num_asic_inst):
             port_map_dir = os.path.join(platform_dir, str(inst))
             port_map_file = os.path.join(port_map_dir, "port_config.ini")
             if os.path.exists(port_map_file):
                 self.read_porttab_mappings(port_map_file, inst)

    def get_physical_to_logical(self, port_num):
        """Returns list of logical ports for the given physical port"""

        return self.physical_to_logical.get(port_num)

    def get_logical_to_physical(self, logical_port):
        """Returns list of physical ports for the given logical port"""

        return self.logical_to_physical[logical_port]

    def is_logical_port(self, port):
        if port in self.logical:
            return 1
        else:
            return 0

    def get_asic_id_for_logical_port(self, logical_port):
        """Returns the asic_id list of physical ports for the given logical port"""
        return self.logical_to_asic.get(logical_port)
