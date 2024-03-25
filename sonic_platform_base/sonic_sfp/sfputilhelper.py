# sfputilbase.py
#
# Base class for creating platform-specific SFP transceiver interfaces for SONiC
#

from __future__ import print_function

try:
    import os
    import re
    import sys
    from collections import OrderedDict

    from natsort import natsorted
    from portconfig import get_port_config
    from sonic_py_common import device_info, multi_asic

except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

# Global Variable
PLATFORM_JSON = 'platform.json'
PORT_CONFIG_INI = 'port_config.ini'
ASIC_NAME_PREFIX = 'asic'

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

    def read_porttab_mappings(self, porttabfile, asic_inst=0):
        logical = []
        logical_to_physical = {}
        physical_to_logical = {}
        fp_port_index = 1

        (platform, hwsku) = device_info.get_platform_and_hwsku()

        asic_name = None
        if multi_asic.is_multi_asic():
            asic_name = ASIC_NAME_PREFIX + str(asic_inst)

        ports, _, _ = get_port_config(hwsku, platform, asic_name=asic_name)

        if not ports:
            ports, _, _ = get_port_config(hwsku, platform, porttabfile)
            if not ports:
                print('Failed to get port config', file=sys.stderr)
                sys.exit(1)

        for intf in ports.keys():
            # Ignore if this is a non front panel interface
            if multi_asic.is_front_panel_port(intf, ports[intf].get(multi_asic.PORT_ROLE, None)):
                logical.append(intf)

        logical = natsorted(logical, key=lambda y: y.lower())
        logical_to_physical, physical_to_logical = OrderedDict(),  OrderedDict()

        for intf_name in logical:
            if 'index' in ports[intf_name].keys():
                fp_port_index = int(ports[intf_name]['index'])
                logical_to_physical[intf_name] = [fp_port_index]

            if physical_to_logical.get(fp_port_index) is None:
                physical_to_logical[fp_port_index] = [intf_name]
            else:
                physical_to_logical[fp_port_index].append(intf_name)

            # Mapping of logical port names available on a system to ASIC instance
            self.logical_to_asic[intf_name] = asic_inst

        self.logical.extend(logical)
        self.logical = list(OrderedDict.fromkeys(self.logical).keys())
        self.logical_to_physical.update(logical_to_physical)
        self.physical_to_logical.update(physical_to_logical)

        return None


    def read_all_porttab_mappings(self, platform_dir, num_asic_inst):
        # In multi asic scenario, get all the port_config files for different asic
        for inst in range(num_asic_inst):
            port_map_dir = os.path.join(platform_dir, str(inst))
            port_map_file = os.path.join(port_map_dir, PORT_CONFIG_INI)
            if os.path.exists(port_map_file):
                self.read_porttab_mappings(port_map_file, inst)
            else:
                port_json_file = os.path.join(platform_dir, PLATFORM_JSON)
                if os.path.exists(port_json_file):
                    self.read_porttab_mappings(port_json_file, inst)

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
