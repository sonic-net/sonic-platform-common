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
    from portconfig import get_port_config
    from collections import OrderedDict
    from natsort import natsorted
    from sonic_daemon_base.daemon_base import DaemonBase
    import sys
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

# Global Variable
PLATFORM_JSON = 'platform.json'
PORT_CONFIG_INI = 'portconfig.ini'

class SfpUtilHelper(object):
    # List to specify filter for sfp_ports
    # Needed by platforms like dni-6448 which
    # have only a subset of ports that support sfp
    sfp_ports = []

    # List of logical port names available on a system
    """ ["swp1", "swp5", "swp6", "swp7", "swp8" ...] """
    logical = []

    # dicts for easier conversions between logical, physical and bcm ports
    logical_to_physical = {}

    physical_to_logical = {}
    physical_to_phyaddrs = {}

    def __init__(self):
        pass

    def read_porttab_mappings(self, porttabfile):
        logical = []
        logical_to_physical = {}
        physical_to_logical = {}
        last_fp_port_index = 0
        last_portname = ""
        first = 1
        port_pos_in_file = 0
        parse_fmt_port_config_ini = False
        parse_fmt_platform_json = False

        parse_fmt_port_config_ini = (os.path.basename(porttabfile) == PORT_CONFIG_INI)
        parse_fmt_platform_json = (os.path.basename(porttabfile) == PLATFORM_JSON)

        (platform, hwsku) =  DaemonBase().get_platform_and_hwsku()
        if(parse_fmt_platform_json):
            ports, _ = get_port_config(hwsku, platform)
            if not ports:
                print('Failed to get port config', file=sys.stderr)
                sys.exit(1)
            else:
                logical_list = []
                for intf in ports.keys():
                    logical_list.append(intf)

                logical = natsorted(logical_list, key=lambda y: y.lower())
                logical_to_physical, physical_to_logical = OrderedDict(),  OrderedDict()

                for intf_name in logical:
                    bcm_port = str(port_pos_in_file)

                    if 'index' in ports[intf_name].keys():
                        fp_port_index = ports[intf_name]['index']
                        logical_to_physical[intf_name] = [fp_port_index]

                    if physical_to_logical.get(fp_port_index) is None:
                        physical_to_logical[fp_port_index] = [intf_name]
                    else:
                        physical_to_logical[fp_port_index].append(intf_name)

                    port_pos_in_file +=1

                self.logical = logical
                self.logical_to_physical = logical_to_physical
                self.physical_to_logical = physical_to_logical

                """
                print("logical: {}".format(self.logical))
                print("logical to physical: {}".format(self.logical_to_physical))
                print("physical to logical: {}".format( self.physical_to_logical))
                """
                return None


        try:
            f = open(porttabfile)
        except:
            raise

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

                bcm_port = str(port_pos_in_file)

                if "index" in title:
                    fp_port_index = int(line.split()[title.index("index")])
                # Leave the old code for backward compatibility
                elif len(line.split()) >= 4:
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

            logical_to_physical[portname] = [fp_port_index]
            if physical_to_logical.get(fp_port_index) is None:
                physical_to_logical[fp_port_index] = [portname]
            else:
                physical_to_logical[fp_port_index].append(portname)

            last_fp_port_index = fp_port_index
            last_portname = portname

            port_pos_in_file += 1

        self.logical = logical
        self.logical_to_physical = logical_to_physical
        self.physical_to_logical = physical_to_logical

        """
        print("logical: " + self.logical)
        print("logical to physical: " + self.logical_to_physical)
        print("physical to logical: " + self.physical_to_logical)
        """
    def get_physical_to_logical(self, port_num):
        """Returns list of logical ports for the given physical port"""

        return self.physical_to_logical[port_num]

    def get_logical_to_physical(self, logical_port):
        """Returns list of physical ports for the given logical port"""

        return self.logical_to_physical[logical_port]

    def is_logical_port(self, port):
        if port in self.logical:
            return 1
        else:
            return 0
