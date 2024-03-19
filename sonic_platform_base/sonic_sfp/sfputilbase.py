# sfputilbase.py
#
# Base class for creating platform-specific SFP transceiver interfaces for SONiC
#

from __future__ import print_function

try:
    import abc
    import os
    import re
    import sys
    from collections import OrderedDict

    from natsort import natsorted
    from portconfig import get_port_config
    from sonic_py_common import device_info, multi_asic

    from sonic_eeprom import eeprom_dts
    from .sff8472 import sff8472InterfaceId  # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8472 import sff8472Dom    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8436 import sff8436InterfaceId  # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8436 import sff8436Dom    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .inf8628 import inf8628InterfaceId    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

# Global Variable
PLATFORM_JSON = 'platform.json'
PORT_CONFIG_INI = 'port_config.ini'

# definitions of the offset and width for values in XCVR info eeprom
XCVR_INTFACE_BULK_OFFSET = 0
XCVR_INTFACE_BULK_WIDTH_QSFP = 20
XCVR_INTFACE_BULK_WIDTH_SFP = 21
XCVR_TYPE_OFFSET = 0
XCVR_TYPE_WIDTH = 1
XCVR_EXT_TYPE_OFFSET = 1
XCVR_EXT_TYPE_WIDTH = 1
XCVR_CONNECTOR_OFFSET = 2
XCVR_CONNECTOR_WIDTH = 1
XCVR_COMPLIANCE_CODE_OFFSET = 3
XCVR_COMPLIANCE_CODE_WIDTH = 8
XCVR_ENCODING_OFFSET = 11
XCVR_ENCODING_WIDTH = 1
XCVR_NBR_OFFSET = 12
XCVR_NBR_WIDTH = 1
XCVR_EXT_RATE_SEL_OFFSET = 13
XCVR_EXT_RATE_SEL_WIDTH = 1
XCVR_CABLE_LENGTH_OFFSET = 14
XCVR_CABLE_LENGTH_WIDTH_QSFP = 5
XCVR_CABLE_LENGTH_WIDTH_SFP = 6
XCVR_VENDOR_NAME_OFFSET = 20
XCVR_VENDOR_NAME_WIDTH = 16
XCVR_VENDOR_OUI_OFFSET = 37
XCVR_VENDOR_OUI_WIDTH = 3
XCVR_VENDOR_PN_OFFSET = 40
XCVR_VENDOR_PN_WIDTH = 16
XCVR_HW_REV_OFFSET = 56
XCVR_HW_REV_WIDTH_OSFP = 2
XCVR_HW_REV_WIDTH_QSFP = 2
XCVR_HW_REV_WIDTH_SFP = 4
XCVR_VENDOR_SN_OFFSET = 68
XCVR_VENDOR_SN_WIDTH = 16
XCVR_VENDOR_DATE_OFFSET = 84
XCVR_VENDOR_DATE_WIDTH = 8
XCVR_DOM_CAPABILITY_OFFSET = 92
XCVR_DOM_CAPABILITY_WIDTH = 1

# definitions of the offset for values in OSFP info eeprom
OSFP_TYPE_OFFSET = 0
OSFP_VENDOR_NAME_OFFSET = 129
OSFP_VENDOR_PN_OFFSET = 148
OSFP_HW_REV_OFFSET = 164
OSFP_VENDOR_SN_OFFSET = 166

#definitions of the offset and width for values in DOM info eeprom
QSFP_DOM_REV_OFFSET = 1
QSFP_DOM_REV_WIDTH = 1
QSFP_TEMPE_OFFSET = 22
QSFP_TEMPE_WIDTH = 2
QSFP_VOLT_OFFSET = 26
QSFP_VOLT_WIDTH = 2
QSFP_CHANNL_MON_OFFSET = 34
QSFP_CHANNL_MON_WIDTH = 16
QSFP_CHANNL_MON_WITH_TX_POWER_WIDTH = 24
QSFP_MODULE_THRESHOLD_OFFSET = 128
QSFP_MODULE_THRESHOLD_WIDTH = 24
QSFP_CHANNL_THRESHOLD_OFFSET = 176
QSFP_CHANNL_THRESHOLD_WIDTH = 24
QSFP_CHANNL_MON_MASK_OFFSET = 242
QSFP_CHANNL_MON_MASK_WIDTH = 4

SFP_TEMPE_OFFSET = 96
SFP_TEMPE_WIDTH = 2
SFP_VOLT_OFFSET = 98
SFP_VOLT_WIDTH = 2
SFP_CHANNL_MON_OFFSET = 100
SFP_CHANNL_MON_WIDTH = 6
SFP_MODULE_THRESHOLD_OFFSET = 112
SFP_MODULE_THRESHOLD_WIDTH = 5
SFP_CHANNL_THRESHOLD_OFFSET = 112
SFP_CHANNL_THRESHOLD_WIDTH = 6

qsfp_cable_length_tup = ('Length(km)', 'Length OM3(2m)',
                         'Length OM2(m)', 'Length OM1(m)',
                         'Length Cable Assembly(m)')

sfp_cable_length_tup = ('LengthSMFkm-UnitsOfKm', 'LengthSMF(UnitsOf100m)',
                        'Length50um(UnitsOf10m)', 'Length62.5um(UnitsOfm)',
                        'LengthCable(UnitsOfm)', 'LengthOM3(UnitsOf10m)')

sfp_compliance_code_tup = ('10GEthernetComplianceCode', 'InfinibandComplianceCode',
                            'ESCONComplianceCodes', 'SONETComplianceCodes',
                            'EthernetComplianceCodes','FibreChannelLinkLength',
                            'FibreChannelTechnology', 'SFP+CableTechnology',
                            'FibreChannelTransmissionMedia','FibreChannelSpeed')

qsfp_compliance_code_tup = ('10/40G Ethernet Compliance Code', 'SONET Compliance codes',
                            'SAS/SATA compliance codes', 'Gigabit Ethernet Compliant codes',
                            'Fibre Channel link length/Transmitter Technology',
                            'Fibre Channel transmission media', 'Fibre Channel Speed')

qsfp_dom_capability_tup = ('Tx_power_support', 'Rx_power_support',
                           'Voltage_support', 'Temp_support')

# Add an EOL to prevent this being viewed as string instead of list
sfp_dom_capability_tup = ('sff8472_dom_support', 'EOL')

class SfpUtilError(Exception):
    """Base class for exceptions in this module."""
    pass


class DeviceTreeError(SfpUtilError):
    """Exception raised when unable to find SFP device attributes in the device tree."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SfpUtilBase(object):
    """ Abstract base class for SFP utility. This class
    provides base EEPROM read attributes and methods common
    to most platforms."""

    __metaclass__ = abc.ABCMeta

    IDENTITY_EEPROM_ADDR = 0x50
    DOM_EEPROM_ADDR = 0x51
    SFP_DEVICE_TYPE = "24c02"

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
    logical_to_bcm = {}
    logical_to_physical = {}

    """
    phytab_mappings stores mapping between logical, physical and bcm ports
    from /var/lib/cumulus/phytab
    For a normal non-ganged port:
    "swp8": {"bcmport": "xe4", "physicalport": [8], "phyid": ["0xb"]}

    For a ganged 40G/4 port:
    "swp1": {"bcmport": "xe0", "physicalport": [1, 2, 3, 4], "phyid": ["0x4", "0x5", "0x6", "0x7"]}

    For ganged 4x10G port:
    "swp52s0": {"bcmport": "xe51", "physicalport": [52], "phyid": ["0x48"]},
    "swp52s1": {"bcmport": "xe52", "physicalport": [52], "phyid": ["0x49"]},
    "swp52s2": {"bcmport": "xe53", "physicalport": [52], "phyid": ["0x4a"]},
    "swp52s3": {"bcmport": "xe54", "physicalport": [52], "phyid": ["0x4b"]},
    """
    phytab_mappings = {}

    physical_to_logical = {}
    physical_to_phyaddrs = {}

    port_to_i2cbus_mapping = None

    @abc.abstractproperty
    def port_start(self):
        """ Starting index of physical port range """
        pass

    @abc.abstractproperty
    def port_end(self):
        """ Ending index of physical port range """
        pass

    @abc.abstractproperty
    def qsfp_ports(self):
        """ QSFP Ports """
        pass

    @property
    def osfp_ports(self):
        """ OSFP/QSFP-DD Ports """
        return []

    @abc.abstractproperty
    def port_to_eeprom_mapping(self):
        """ Dictionary where key = physical port index (integer),
            value = path to SFP EEPROM device file (string) """
        pass

    def __init__(self):
        pass

    def _get_bcm_port(self, port_num):
        bcm_port = None

        logical_port = self.physical_to_logical.get(port_num)
        if logical_port is not None and len(logical_port) > 0:
            bcm_port = self.logical_to_bcm.get(logical_port[0])

        if bcm_port is None:
            bcm_port = "xe%d" % (port_num - 1)

        return bcm_port

    def _get_port_i2c_adapter_id(self, port_num):
        if len(self.port_to_i2cbus_mapping) == 0:
            return -1

        return self.port_to_i2cbus_mapping.get(port_num, -1)

    # Adds new sfp device on i2c adapter/bus via i2c bus new_device
    # sysfs attribute
    def _add_new_sfp_device(self, sysfs_sfp_i2c_adapter_path, devaddr):
        try:
            sysfs_nd_path = "%s/new_device" % sysfs_sfp_i2c_adapter_path

            # Write device address to new_device file
            nd_file = open(sysfs_nd_path, "w")
            nd_str = "%s %s" % (self.SFP_DEVICE_TYPE, hex(devaddr))
            nd_file.write(nd_str)
            nd_file.close()

        except Exception as err:
            print("Error writing to new device file: %s" % str(err))
            return 1
        else:
            return 0

    # Deletes sfp device on i2c adapter/bus via i2c bus delete_device
    # sysfs attribute
    def _delete_sfp_device(self, sysfs_sfp_i2c_adapter_path, devaddr):
        try:
            sysfs_nd_path = "%s/delete_device" % sysfs_sfp_i2c_adapter_path

            # Write device address to delete_device file
            nd_file = open(sysfs_nd_path, "w")
            nd_file.write(devaddr)
            nd_file.close()
        except Exception as err:
            print("Error writing to new device file: %s" % str(err))
            return 1
        else:
            return 0

    # Returns 1 if SFP EEPROM found. Returns 0 otherwise
    def _sfp_eeprom_present(self, sysfs_sfp_i2c_client_eeprompath, offset):
        """Tries to read the eeprom file to determine if the
        device/sfp is present or not. If sfp present, the read returns
        valid bytes. If not, read returns error 'Connection timed out"""

        if not os.path.exists(sysfs_sfp_i2c_client_eeprompath):
            return False
        else:
            try:
                with open(sysfs_sfp_i2c_client_eeprompath, mode="rb", buffering=0) as sysfsfile:
                    sysfsfile.seek(offset)
                    sysfsfile.read(1)
            except IOError:
                return False
            except Exception:
                return False
            else:
                return True

    def _get_port_eeprom_path(self, port_num, devid):
        sysfs_i2c_adapter_base_path = "/sys/class/i2c-adapter"

        if port_num in self.port_to_eeprom_mapping.keys():
            sysfs_sfp_i2c_client_eeprom_path = self.port_to_eeprom_mapping[port_num]
        else:
            sysfs_i2c_adapter_base_path = "/sys/class/i2c-adapter"

            i2c_adapter_id = self._get_port_i2c_adapter_id(port_num)
            if i2c_adapter_id is None:
                print("Error getting i2c bus num")
                return None

            # Get i2c virtual bus path for the sfp
            sysfs_sfp_i2c_adapter_path = "%s/i2c-%s" % (sysfs_i2c_adapter_base_path,
                                                        str(i2c_adapter_id))

            # If i2c bus for port does not exist
            if not os.path.exists(sysfs_sfp_i2c_adapter_path):
                print("Could not find i2c bus %s. Driver not loaded?" % sysfs_sfp_i2c_adapter_path)
                return None

            sysfs_sfp_i2c_client_path = "%s/%s-00%s" % (sysfs_sfp_i2c_adapter_path,
                                                        str(i2c_adapter_id),
                                                        hex(devid)[-2:])

            # If sfp device is not present on bus, Add it
            if not os.path.exists(sysfs_sfp_i2c_client_path):
                ret = self._add_new_sfp_device(
                        sysfs_sfp_i2c_adapter_path, devid)
                if ret != 0:
                    print("Error adding sfp device")
                    return None

            sysfs_sfp_i2c_client_eeprom_path = "%s/eeprom" % sysfs_sfp_i2c_client_path

        return sysfs_sfp_i2c_client_eeprom_path

    # Read out any bytes from any offset
    def _read_eeprom_specific_bytes(self, sysfsfile_eeprom, offset, num_bytes):
        eeprom_raw = []
        for i in range(0, num_bytes):
            eeprom_raw.append("0x00")

        try:
            sysfsfile_eeprom.seek(offset)
            raw = sysfsfile_eeprom.read(num_bytes)
        except IOError:
            print("Error: reading EEPROM sysfs file")
            return None

        try:
            # raw is changed to bytearray to support both python 2 and 3.
            raw = bytearray(raw)
            for n in range(0, num_bytes):
                eeprom_raw[n] = hex(raw[n])[2:].zfill(2)
        except Exception:
            return None

        return eeprom_raw

    # Read eeprom
    def _read_eeprom_devid(self, port_num, devid, offset, num_bytes = 256):
        sysfs_sfp_i2c_client_eeprom_path = self._get_port_eeprom_path(port_num, devid)

        if not self._sfp_eeprom_present(sysfs_sfp_i2c_client_eeprom_path, offset):
            return None

        try:
            sysfsfile_eeprom = open(sysfs_sfp_i2c_client_eeprom_path, mode="rb", buffering=0)
        except IOError:
            print("Error: reading sysfs file %s" % sysfs_sfp_i2c_client_eeprom_path)
            return None

        eeprom_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, offset, num_bytes)

        try:
            sysfsfile_eeprom.close()
        except Exception:
            return None

        return eeprom_raw

    def _write_eeprom_specific_bytes(self, sysfsfile_eeprom, offset, num_bytes, write_buffer):
        try:
            sysfsfile_eeprom.seek(offset)
            sysfsfile_eeprom.write(write_buffer)
        except IOError:
            print("Error: writing EEPROM sysfs file")
            return False

        return True

    def _write_eeprom_devid(self, port_num, devid, offset, num_bytes, write_buffer):
        sysfs_sfp_i2c_client_eeprom_path = self._get_port_eeprom_path(port_num, devid)

        if not self._sfp_eeprom_present(sysfs_sfp_i2c_client_eeprom_path, offset):
            return False

        try:
            sysfsfile_eeprom = open(sysfs_sfp_i2c_client_eeprom_path, mode="wb", buffering=0)
        except IOError:
            print("Error: trying to open sysfs file for writing %s" % sysfs_sfp_i2c_client_eeprom_path)
            return False

        result = self._write_eeprom_specific_bytes(sysfsfile_eeprom, offset, num_bytes, write_buffer)

        try:
            sysfsfile_eeprom.close()
        except Exception:
            return False

        return True

    def _is_valid_port(self, port_num):
        if port_num >= self.port_start and port_num <= self.port_end:
            return True

        return False

    def read_porttab_mappings(self, porttabfile, asic_inst=0):
        logical = []
        logical_to_bcm = {}
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

        (platform, hwsku) = device_info.get_platform_and_hwsku()
        if(parse_fmt_platform_json):
            ports, _, _ = get_port_config(hwsku, platform)
            if not ports:
                print('Failed to get port config', file=sys.stderr)
                sys.exit(1)
            else:
                for intf in ports.keys():
                    # Ignore if this is a non front panel interface
                    if multi_asic.is_front_panel_port(intf, ports[intf].get(multi_asic.PORT_ROLE, None)):
                        logical.append(intf)

                logical = natsorted(logical, key=lambda y: y.lower())
                logical_to_bcm, logical_to_physical, physical_to_logical = OrderedDict(),  OrderedDict(),  OrderedDict()

                for intf_name in logical:
                    bcm_port = str(port_pos_in_file)
                    logical_to_bcm[intf_name] = "xe"+ bcm_port

                    if 'index' in ports[intf_name].keys():
                        fp_port_index = int(ports[intf_name]['index'])
                        logical_to_physical[intf_name] = [fp_port_index]

                    if physical_to_logical.get(fp_port_index) is None:
                        physical_to_logical[fp_port_index] = [intf_name]
                    else:
                        physical_to_logical[fp_port_index].append(intf_name)

                    # Mapping of logical port names available on a system to ASIC instance
                    self.logical_to_asic[intf_name] = asic_inst
                    port_pos_in_file +=1

                self.logical = logical
                self.logical_to_bcm = logical_to_bcm
                self.logical_to_physical = logical_to_physical
                self.physical_to_logical = physical_to_logical

                """
                print("logical: {}".format(self.logical))
                print("logical to bcm: {}".format(self.logical_to_bcm))
                print("logical to physical: {}".format(self.logical_to_physical))
                print("physical to logical: {}".format( self.physical_to_logical))
                """
                return None


        try:
            f = open(porttabfile)
        except Exception:
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

                # Ignore if this is an internal backplane interface and Inband interface
                if not multi_asic.is_front_panel_port(portname):
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

            logical_to_bcm[portname] = "xe" + bcm_port
            logical_to_physical[portname] = [fp_port_index]
            if physical_to_logical.get(fp_port_index) is None:
                physical_to_logical[fp_port_index] = [portname]
            else:
                physical_to_logical[fp_port_index].append(portname)

            last_fp_port_index = fp_port_index
            last_portname = portname

            port_pos_in_file += 1

        self.logical.extend(logical)
        self.logical_to_bcm.update(logical_to_bcm)
        self.logical_to_physical.update(logical_to_physical)
        self.physical_to_logical.update(physical_to_logical)

        """
        print("logical: " + self.logical)
        print("logical to bcm: " + self.logical_to_bcm)
        print("logical to physical: " + self.logical_to_physical)
        print("physical to logical: " + self.physical_to_logical)
        """

    def read_all_porttab_mappings(self, platform_dir, num_asic_inst):
        # In multi asic scenario, get all the port_config files for different asics
         for inst in range(num_asic_inst):
             port_map_dir = os.path.join(platform_dir, str(inst))
             port_map_file = os.path.join(port_map_dir, PORT_CONFIG_INI)
             if os.path.exists(port_map_file):
                 self.read_porttab_mappings(port_map_file, inst)
             else:
                 port_json_file = os.path.join(port_map_dir, PLATFORM_JSON)
                 if os.path.exists(port_json_file):
                     self.read_porttab_mappings(port_json_file, inst)

    def read_phytab_mappings(self, phytabfile):
        logical = []
        phytab_mappings = {}
        physical_to_logical = {}
        physical_to_phyaddrs = {}

        try:
            f = open(phytabfile)
        except Exception:
            raise

        # Read the phytab file and generate dicts
        # with mapping for future reference.
        # XXX: move the phytabfile
        # parsing stuff to a separate module, or reuse
        # if something already exists
        for line in f:
            line = line.strip()
            line = re.sub(r"\s+", " ", line)
            if len(line) < 4:
                continue
            if re.search("^#", line) is not None:
                continue
            (phy_addr, logical_port, bcm_port, type) = line.split(" ", 3)

            if re.match("xe", bcm_port) is None:
                continue

            lport = re.findall("swp(\d+)s*(\d*)", logical_port)
            if lport is not None:
                lport_tuple = lport.pop()
                physical_port = int(lport_tuple[0])
            else:
                physical_port = logical_port.split("swp").pop()
                physical_port = int(physical_port.split("s").pop(0))

            # Some platforms have a list of physical sfp ports
            # defined. If such a list exists, check to see if this
            # port is blacklisted
            if ((len(self.sfp_ports) > 0) and (physical_port not in self.sfp_ports)):
                continue

            if logical_port not in logical:
                logical.append(logical_port)

            if phytab_mappings.get(logical_port) is None:
                phytab_mappings[logical_port] = {}
                phytab_mappings[logical_port]['physicalport'] = []
                phytab_mappings[logical_port]['phyid'] = []
                phytab_mappings[logical_port]['type'] = type

            # If the port is 40G/4 ganged, there will be multiple
            # physical ports corresponding to the logical port.
            # Generate the next physical port number in the series
            # and append it to the list
            tmp_physical_port_list = phytab_mappings[logical_port]['physicalport']
            if (type == "40G/4" and physical_port in tmp_physical_port_list):
                # Aha!...ganged port
                new_physical_port = tmp_physical_port_list[-1] + 1
            else:
                new_physical_port = physical_port

            if (new_physical_port not in phytab_mappings[logical_port]['physicalport']):
                phytab_mappings[logical_port]['physicalport'].append(new_physical_port)
            phytab_mappings[logical_port]['phyid'].append(phy_addr)
            phytab_mappings[logical_port]['bcmport'] = bcm_port

            # Store in physical_to_logical dict
            if physical_to_logical.get(new_physical_port) is None:
                physical_to_logical[new_physical_port] = []
            physical_to_logical[new_physical_port].append(logical_port)

            # Store in physical_to_phyaddrs dict
            if physical_to_phyaddrs.get(new_physical_port) is None:
                physical_to_phyaddrs[new_physical_port] = []
            physical_to_phyaddrs[new_physical_port].append(phy_addr)

        self.logical = logical
        self.phytab_mappings = phytab_mappings
        self.physical_to_logical = physical_to_logical
        self.physical_to_phyaddrs = physical_to_phyaddrs

        """
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self.phytab_mappings)

        print("logical: " +  self.logical)
        print("logical to bcm: " +  self.logical_to_bcm)
        print("phytab mappings: " + self.phytab_mappings)
        print("physical to logical: " + self.physical_to_logical)
        print("physical to phyaddrs: " + self.physical_to_phyaddrs)
        """

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

    def is_logical_port_ganged_40_by_4(self, logical_port):
        physical_port_list = self.logical_to_physical[logical_port]
        if len(physical_port_list) > 1:
            return 1
        else:
            return 0

    def is_physical_port_ganged_40_by_4(self, port_num):
        logical_port = self.get_physical_to_logical(port_num)
        if logical_port is not None:
            return self.is_logical_port_ganged_40_by_4(logical_port[0])

        return 0

    def get_physical_port_phyid(self, physical_port):
        """Returns list of phyids for a physical port"""

        return self.physical_to_phyaddrs[physical_port]

    def get_40_by_4_gangport_phyid(self, logical_port):
        """ Return the first ports phyid. One use case for
            this is to address the gang port in single mode """

        phyid_list = self.phytab_mappings[logical_port]['phyid']
        if phyid_list is not None:
            return phyid_list[0]

    def is_valid_sfputil_port(self, port):
        if port.startswith(""):
            if self.is_logical_port(port):
                return 1
            else:
                return 0
        else:
            return 0

    def read_port_mappings(self):
        if self.port_to_eeprom_mapping is None or self.port_to_i2cbus_mapping is None:
            self.read_port_to_eeprom_mapping()
            self.read_port_to_i2cbus_mapping()

    def read_port_to_eeprom_mapping(self):
        eeprom_dev = "/sys/class/eeprom_dev"
        self.port_to_eeprom_mapping = {}
        for eeprom_path in [os.path.join(eeprom_dev, x) for x in os.listdir(eeprom_dev)]:
            eeprom_label = open(os.path.join(eeprom_path, "label"), "r").read().strip()
            if eeprom_label.startswith("port"):
                port = int(eeprom_label[4:])
                self.port_to_eeprom_mapping[port] = os.path.join(eeprom_path, "device", "eeprom")

    def read_port_to_i2cbus_mapping(self):
        if self.port_to_i2cbus_mapping is not None and len(self.port_to_i2cbus_mapping) > 0:
            return

        self.eep_dict = eeprom_dts.get_dev_attr_from_dtb(['sfp'])
        if len(self.eep_dict) == 0:
            return

        # XXX: there should be a cleaner way to do this.
        i2cbus_list = []
        self.port_to_i2cbus_mapping = {}
        s = self.port_start
        for sfp_sysfs_path, attrs in sorted(self.eep_dict.items()):
            i2cbus = attrs.get("dev-id")
            if i2cbus is None:
                raise DeviceTreeError("No 'dev-id' attribute found in attr: %s" % repr(attrs))
            if i2cbus in i2cbus_list:
                continue
            i2cbus_list.append(i2cbus)
            self.port_to_i2cbus_mapping[s] = i2cbus
            s += 1
            if s > self.port_end:
                break

    def get_eeprom_raw(self, port_num, num_bytes=256):
        # Read interface id EEPROM at addr 0x50
        return self._read_eeprom_devid(port_num, self.IDENTITY_EEPROM_ADDR, 0, num_bytes)

    def get_eeprom_dom_raw(self, port_num):
        if port_num in self.osfp_ports:
            return None
        if port_num in self.qsfp_ports:
            # QSFP DOM EEPROM is also at addr 0x50 and thus also stored in eeprom_ifraw
            return None
        else:
            # Read dom eeprom at addr 0x51
            return self._read_eeprom_devid(port_num, self.DOM_EEPROM_ADDR, 0)

    def get_eeprom_dict(self, port_num):
        """Returns dictionary of interface and dom data.
        format: {<port_num> : {'interface': {'version' : '1.0', 'data' : {...}},
                               'dom' : {'version' : '1.0', 'data' : {...}}}}
        """

        sfp_data = {}

        eeprom_ifraw = self.get_eeprom_raw(port_num)
        eeprom_domraw = self.get_eeprom_dom_raw(port_num)

        if eeprom_ifraw is None:
            return None

        if port_num in self.osfp_ports:
            sfpi_obj = inf8628InterfaceId(eeprom_ifraw)
            if sfpi_obj is not None:
                sfp_data['interface'] = sfpi_obj.get_data_pretty()
            return sfp_data
        elif port_num in self.qsfp_ports:
            sfpi_obj = sff8436InterfaceId(eeprom_ifraw)
            if sfpi_obj is not None:
                sfp_data['interface'] = sfpi_obj.get_data_pretty()
            # For Qsfp's the dom data is part of eeprom_if_raw
            # The first 128 bytes

            sfpd_obj = sff8436Dom(eeprom_ifraw)
            if sfpd_obj is not None:
                sfp_data['dom'] = sfpd_obj.get_data_pretty()

            return sfp_data
        else:
            sfpi_obj = sff8472InterfaceId(eeprom_ifraw)
            if sfpi_obj is not None:
                sfp_data['interface'] = sfpi_obj.get_data_pretty()
                cal_type = sfpi_obj.get_calibration_type()

            if eeprom_domraw is not None:
                sfpd_obj = sff8472Dom(eeprom_domraw, cal_type)
                if sfpd_obj is not None:
                    sfp_data['dom'] = sfpd_obj.get_data_pretty()

            return sfp_data

    # Read out SFP type, vendor name, PN, REV, SN from eeprom.
    def get_transceiver_info_dict(self, port_num):
        transceiver_info_dict = {}
        compliance_code_dict = {}
        dom_capability_dict = {}

        # ToDo: OSFP tranceiver info parsing not fully supported.
        # in inf8628.py lack of some memory map definition
        # will be implemented when the inf8628 memory map ready
        if port_num in self.osfp_ports:
            offset = 0
            vendor_rev_width = XCVR_HW_REV_WIDTH_OSFP

            sfpi_obj = inf8628InterfaceId()
            if sfpi_obj is None:
                print("Error: sfp_object open failed")
                return None

            file_path = self._get_port_eeprom_path(port_num, self.IDENTITY_EEPROM_ADDR)
            if not self._sfp_eeprom_present(file_path, 0):
                print("Error, file not exist %s" % file_path)
                return None

            try:
                sysfsfile_eeprom = open(file_path, mode="rb", buffering=0)
            except IOError:
                print("Error: reading sysfs file %s" % file_path)
                return None

            sfp_type_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + OSFP_TYPE_OFFSET), XCVR_TYPE_WIDTH)
            if sfp_type_raw is not None:
                sfp_type_data = sfpi_obj.parse_sfp_type(sfp_type_raw, 0)
            else:
                return None

            sfp_vendor_name_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + OSFP_VENDOR_NAME_OFFSET), XCVR_VENDOR_NAME_WIDTH)
            if sfp_vendor_name_raw is not None:
                sfp_vendor_name_data = sfpi_obj.parse_vendor_name(sfp_vendor_name_raw, 0)
            else:
                return None

            sfp_vendor_pn_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + OSFP_VENDOR_PN_OFFSET), XCVR_VENDOR_PN_WIDTH)
            if sfp_vendor_pn_raw is not None:
                sfp_vendor_pn_data = sfpi_obj.parse_vendor_pn(sfp_vendor_pn_raw, 0)
            else:
                return None

            sfp_vendor_rev_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + OSFP_HW_REV_OFFSET), vendor_rev_width)
            if sfp_vendor_rev_raw is not None:
                sfp_vendor_rev_data = sfpi_obj.parse_vendor_rev(sfp_vendor_rev_raw, 0)
            else:
                return None

            sfp_vendor_sn_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + OSFP_VENDOR_SN_OFFSET), XCVR_VENDOR_SN_WIDTH)
            if sfp_vendor_sn_raw is not None:
                sfp_vendor_sn_data = sfpi_obj.parse_vendor_sn(sfp_vendor_sn_raw, 0)
            else:
                return None

            sfp_type_abbrv_name_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + OSFP_TYPE_OFFSET), XCVR_TYPE_WIDTH)
            if sfp_type_abbrv_name_raw is not None:
                sfp_type_abbrv_name = sfpi_obj.parse_sfp_type_abbrv_name(sfp_type_abbrv_name_raw, 0)
            else:
                return None

            try:
                sysfsfile_eeprom.close()
            except IOError:
                print("Error: closing sysfs file %s" % file_path)
                return None

            transceiver_info_dict['type'] = sfp_type_data['data']['type']['value']
            transceiver_info_dict['type_abbrv_name'] = sfp_type_abbrv_name['data']['type_abbrv_name']['value']
            transceiver_info_dict['manufacturer'] = sfp_vendor_name_data['data']['Vendor Name']['value']
            transceiver_info_dict['model'] = sfp_vendor_pn_data['data']['Vendor PN']['value']
            transceiver_info_dict['hardware_rev'] = sfp_vendor_rev_data['data']['Vendor Rev']['value']
            transceiver_info_dict['serial'] = sfp_vendor_sn_data['data']['Vendor SN']['value']
            # Below part is added to avoid fail the xcvrd, shall be implemented later
            transceiver_info_dict['vendor_oui'] = 'N/A'
            transceiver_info_dict['vendor_date'] = 'N/A'
            transceiver_info_dict['connector'] = 'N/A'
            transceiver_info_dict['encoding'] = 'N/A'
            transceiver_info_dict['ext_identifier'] = 'N/A'
            transceiver_info_dict['ext_rateselect_compliance'] = 'N/A'
            transceiver_info_dict['cable_type'] = 'N/A'
            transceiver_info_dict['cable_length'] = 'N/A'
            transceiver_info_dict['specification_compliance'] = '{}'
            transceiver_info_dict['nominal_bit_rate'] = 'N/A'
            transceiver_info_dict['application_advertisement'] = 'N/A'
            transceiver_info_dict['dom_capability'] = '{}'

        else:
            file_path = self._get_port_eeprom_path(port_num, self.IDENTITY_EEPROM_ADDR)
            if not self._sfp_eeprom_present(file_path, 0):
                print("Error, file not exist %s" % file_path)
                return None

            try:
                sysfsfile_eeprom = open(file_path, mode="rb", buffering=0)
            except IOError:
                print("Error: reading sysfs file %s" % file_path)
                return None

            if port_num in self.qsfp_ports:
                # Check for QSA adapter
                byte0 = self._read_eeprom_specific_bytes(sysfsfile_eeprom, 0, 1)[0]
                is_qsfp = (byte0 != '03' and byte0 != '0b')
            else:
                is_qsfp = False

            if is_qsfp:
                offset = 128
                vendor_rev_width = XCVR_HW_REV_WIDTH_QSFP
                cable_length_width = XCVR_CABLE_LENGTH_WIDTH_QSFP
                interface_info_bulk_width = XCVR_INTFACE_BULK_WIDTH_QSFP
                sfp_type = 'QSFP'

                sfpi_obj = sff8436InterfaceId()
                if sfpi_obj is None:
                    print("Error: sfp_object open failed")
                    return None

            else:
                offset = 0
                vendor_rev_width = XCVR_HW_REV_WIDTH_SFP
                cable_length_width = XCVR_CABLE_LENGTH_WIDTH_SFP
                interface_info_bulk_width = XCVR_INTFACE_BULK_WIDTH_SFP
                sfp_type = 'SFP'

                sfpi_obj = sff8472InterfaceId()
                if sfpi_obj is None:
                    print("Error: sfp_object open failed")
                    return None

            sfp_interface_bulk_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + XCVR_INTFACE_BULK_OFFSET), interface_info_bulk_width)
            if sfp_interface_bulk_raw is not None:
                sfp_interface_bulk_data = sfpi_obj.parse_sfp_info_bulk(sfp_interface_bulk_raw, 0)
            else:
                return None

            sfp_vendor_name_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + XCVR_VENDOR_NAME_OFFSET), XCVR_VENDOR_NAME_WIDTH)
            if sfp_vendor_name_raw is not None:
                sfp_vendor_name_data = sfpi_obj.parse_vendor_name(sfp_vendor_name_raw, 0)
            else:
                return None

            sfp_vendor_pn_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + XCVR_VENDOR_PN_OFFSET), XCVR_VENDOR_PN_WIDTH)
            if sfp_vendor_pn_raw is not None:
                sfp_vendor_pn_data = sfpi_obj.parse_vendor_pn(sfp_vendor_pn_raw, 0)
            else:
                return None

            sfp_vendor_rev_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + XCVR_HW_REV_OFFSET), vendor_rev_width)
            if sfp_vendor_rev_raw is not None:
                sfp_vendor_rev_data = sfpi_obj.parse_vendor_rev(sfp_vendor_rev_raw, 0)
            else:
                return None

            sfp_vendor_sn_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + XCVR_VENDOR_SN_OFFSET), XCVR_VENDOR_SN_WIDTH)
            if sfp_vendor_sn_raw is not None:
                sfp_vendor_sn_data = sfpi_obj.parse_vendor_sn(sfp_vendor_sn_raw, 0)
            else:
                return None

            sfp_vendor_oui_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + XCVR_VENDOR_OUI_OFFSET), XCVR_VENDOR_OUI_WIDTH)
            if sfp_vendor_oui_raw is not None:
                sfp_vendor_oui_data = sfpi_obj.parse_vendor_oui(sfp_vendor_oui_raw, 0)
            else:
                return None

            sfp_vendor_date_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + XCVR_VENDOR_DATE_OFFSET), XCVR_VENDOR_DATE_WIDTH)
            if sfp_vendor_date_raw is not None:
                sfp_vendor_date_data = sfpi_obj.parse_vendor_date(sfp_vendor_date_raw, 0)
            else:
                return None

            sfp_dom_capability_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + XCVR_DOM_CAPABILITY_OFFSET), XCVR_DOM_CAPABILITY_WIDTH)
            if sfp_dom_capability_raw is not None:
                sfp_dom_capability_data = sfpi_obj.parse_dom_capability(sfp_dom_capability_raw, 0)
            else:
                return None

            try:
                sysfsfile_eeprom.close()
            except IOError:
                print("Error: closing sysfs file %s" % file_path)
                return None

            transceiver_info_dict['type'] = sfp_interface_bulk_data['data']['type']['value']
            transceiver_info_dict['type_abbrv_name'] = sfp_interface_bulk_data['data']['type_abbrv_name']['value']
            transceiver_info_dict['manufacturer'] = sfp_vendor_name_data['data']['Vendor Name']['value']
            transceiver_info_dict['model'] = sfp_vendor_pn_data['data']['Vendor PN']['value']
            transceiver_info_dict['hardware_rev'] = sfp_vendor_rev_data['data']['Vendor Rev']['value']
            transceiver_info_dict['serial'] = sfp_vendor_sn_data['data']['Vendor SN']['value']
            transceiver_info_dict['vendor_oui'] = sfp_vendor_oui_data['data']['Vendor OUI']['value']
            transceiver_info_dict['vendor_date'] = sfp_vendor_date_data['data']['VendorDataCode(YYYY-MM-DD Lot)']['value']
            transceiver_info_dict['connector'] = sfp_interface_bulk_data['data']['Connector']['value']
            transceiver_info_dict['encoding'] = sfp_interface_bulk_data['data']['EncodingCodes']['value']
            transceiver_info_dict['ext_identifier'] = sfp_interface_bulk_data['data']['Extended Identifier']['value']
            transceiver_info_dict['ext_rateselect_compliance'] = sfp_interface_bulk_data['data']['RateIdentifier']['value']
            transceiver_info_dict['cable_type'] = "Unknown"
            transceiver_info_dict['cable_length'] = "Unknown"
            transceiver_info_dict['application_advertisement'] = 'N/A'

            if sfp_type == 'QSFP':
                for key in qsfp_cable_length_tup:
                    if key in sfp_interface_bulk_data['data']:
                        transceiver_info_dict['cable_type'] = key
                        transceiver_info_dict['cable_length'] = str(sfp_interface_bulk_data['data'][key]['value'])

                for key in qsfp_compliance_code_tup:
                    if key in sfp_interface_bulk_data['data']['Specification compliance']['value']:
                        compliance_code_dict[key] = sfp_interface_bulk_data['data']['Specification compliance']['value'][key]['value']
                transceiver_info_dict['specification_compliance'] = str(compliance_code_dict)

                for key in qsfp_dom_capability_tup:
                    if key in sfp_dom_capability_data['data']:
                        dom_capability_dict[key] = "yes" if sfp_dom_capability_data['data'][key]['value'] == 'on' else "no"
                transceiver_info_dict['dom_capability'] = str(dom_capability_dict)

                transceiver_info_dict['nominal_bit_rate'] = str(sfp_interface_bulk_data['data']['Nominal Bit Rate(100Mbs)']['value'])
            else:
                for key in sfp_cable_length_tup:
                    if key in sfp_interface_bulk_data['data']:
                        transceiver_info_dict['cable_type'] = key
                        transceiver_info_dict['cable_length'] = str(sfp_interface_bulk_data['data'][key]['value'])

                for key in sfp_compliance_code_tup:
                    if key in sfp_interface_bulk_data['data']['Specification compliance']['value']:
                        compliance_code_dict[key] = sfp_interface_bulk_data['data']['Specification compliance']['value'][key]['value']
                transceiver_info_dict['specification_compliance'] = str(compliance_code_dict)

                for key in sfp_dom_capability_tup:
                    if key in sfp_dom_capability_data['data']:
                        dom_capability_dict[key] = "yes" if sfp_dom_capability_data['data'][key]['value'] == 'on' else "no"
                transceiver_info_dict['dom_capability'] = str(dom_capability_dict)

                transceiver_info_dict['nominal_bit_rate'] = str(sfp_interface_bulk_data['data']['NominalSignallingRate(UnitsOf100Mbd)']['value'])

        return transceiver_info_dict

    def get_transceiver_dom_info_dict(self, port_num):
        transceiver_dom_info_dict = {}

        dom_info_dict_keys = ['temperature', 'voltage',  'rx1power',
                              'rx2power',    'rx3power', 'rx4power',
                              'tx1bias',     'tx2bias',  'tx3bias',
                              'tx4bias',     'tx1power', 'tx2power',
                              'tx3power',    'tx4power',
                             ]
        transceiver_dom_info_dict = dict.fromkeys(dom_info_dict_keys, 'N/A')

        if port_num in self.osfp_ports:
            # Below part is added to avoid fail xcvrd, shall be implemented later
            transceiver_dom_info_dict['temperature'] = 'N/A'
            transceiver_dom_info_dict['voltage'] = 'N/A'
            transceiver_dom_info_dict['rx1power'] = 'N/A'
            transceiver_dom_info_dict['rx2power'] = 'N/A'
            transceiver_dom_info_dict['rx3power'] = 'N/A'
            transceiver_dom_info_dict['rx4power'] = 'N/A'
            transceiver_dom_info_dict['tx1bias'] = 'N/A'
            transceiver_dom_info_dict['tx2bias'] = 'N/A'
            transceiver_dom_info_dict['tx3bias'] = 'N/A'
            transceiver_dom_info_dict['tx4bias'] = 'N/A'
            transceiver_dom_info_dict['tx1power'] = 'N/A'
            transceiver_dom_info_dict['tx2power'] = 'N/A'
            transceiver_dom_info_dict['tx3power'] = 'N/A'
            transceiver_dom_info_dict['tx4power'] = 'N/A'

        elif port_num in self.qsfp_ports:
            offset = 0
            offset_xcvr = 128
            file_path = self._get_port_eeprom_path(port_num, self.IDENTITY_EEPROM_ADDR)
            if not self._sfp_eeprom_present(file_path, 0):
                return None

            try:
                sysfsfile_eeprom = open(file_path, mode="rb", buffering=0)
            except IOError:
                print("Error: reading sysfs file %s" % file_path)
                return None

            sfpd_obj = sff8436Dom()
            if sfpd_obj is None:
                return None

            sfpi_obj = sff8436InterfaceId()
            if sfpi_obj is None:
                return None

            # QSFP capability byte parse, through this byte can know whether it support tx_power or not.
            # TODO: in the future when decided to migrate to support SFF-8636 instead of SFF-8436,
            # need to add more code for determining the capability and version compliance
            # in SFF-8636 dom capability definitions evolving with the versions.
            qsfp_dom_capability_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset_xcvr + XCVR_DOM_CAPABILITY_OFFSET), XCVR_DOM_CAPABILITY_WIDTH)
            if qsfp_dom_capability_raw is not None:
                qspf_dom_capability_data = sfpi_obj.parse_dom_capability(qsfp_dom_capability_raw, 0)
            else:
                return None

            dom_temperature_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + QSFP_TEMPE_OFFSET), QSFP_TEMPE_WIDTH)
            if dom_temperature_raw is not None:
                dom_temperature_data = sfpd_obj.parse_temperature(dom_temperature_raw, 0)
            else:
                return None

            dom_voltage_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + QSFP_VOLT_OFFSET), QSFP_VOLT_WIDTH)
            if dom_voltage_raw is not None:
                dom_voltage_data = sfpd_obj.parse_voltage(dom_voltage_raw, 0)
            else:
                return None

            qsfp_dom_rev_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + QSFP_DOM_REV_OFFSET), QSFP_DOM_REV_WIDTH)
            if qsfp_dom_rev_raw is not None:
                qsfp_dom_rev_data = sfpd_obj.parse_sfp_dom_rev(qsfp_dom_rev_raw, 0)
            else:
                return None

            transceiver_dom_info_dict['temperature'] = dom_temperature_data['data']['Temperature']['value']
            transceiver_dom_info_dict['voltage'] = dom_voltage_data['data']['Vcc']['value']

            # The tx_power monitoring is only available on QSFP which compliant with SFF-8636
            # and claimed that it support tx_power with one indicator bit.
            dom_channel_monitor_data = {}
            qsfp_dom_rev = qsfp_dom_rev_data['data']['dom_rev']['value']
            qsfp_tx_power_support = qspf_dom_capability_data['data']['Tx_power_support']['value']
            if (qsfp_dom_rev[0:8] != 'SFF-8636' or (qsfp_dom_rev[0:8] == 'SFF-8636' and qsfp_tx_power_support != 'on')):
                dom_channel_monitor_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + QSFP_CHANNL_MON_OFFSET), QSFP_CHANNL_MON_WIDTH)
                if dom_channel_monitor_raw is not None:
                    dom_channel_monitor_data = sfpd_obj.parse_channel_monitor_params(dom_channel_monitor_raw, 0)
                else:
                    return None

                transceiver_dom_info_dict['tx1power'] = 'N/A'
                transceiver_dom_info_dict['tx2power'] = 'N/A'
                transceiver_dom_info_dict['tx3power'] = 'N/A'
                transceiver_dom_info_dict['tx4power'] = 'N/A'
            else:
                dom_channel_monitor_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + QSFP_CHANNL_MON_OFFSET), QSFP_CHANNL_MON_WITH_TX_POWER_WIDTH)
                if dom_channel_monitor_raw is not None:
                    dom_channel_monitor_data = sfpd_obj.parse_channel_monitor_params_with_tx_power(dom_channel_monitor_raw, 0)
                else:
                    return None

                transceiver_dom_info_dict['tx1power'] = dom_channel_monitor_data['data']['TX1Power']['value']
                transceiver_dom_info_dict['tx2power'] = dom_channel_monitor_data['data']['TX2Power']['value']
                transceiver_dom_info_dict['tx3power'] = dom_channel_monitor_data['data']['TX3Power']['value']
                transceiver_dom_info_dict['tx4power'] = dom_channel_monitor_data['data']['TX4Power']['value']

            try:
                sysfsfile_eeprom.close()
            except IOError:
                print("Error: closing sysfs file %s" % file_path)
                return None

            transceiver_dom_info_dict['temperature'] = dom_temperature_data['data']['Temperature']['value']
            transceiver_dom_info_dict['voltage'] = dom_voltage_data['data']['Vcc']['value']
            transceiver_dom_info_dict['rx1power'] = dom_channel_monitor_data['data']['RX1Power']['value']
            transceiver_dom_info_dict['rx2power'] = dom_channel_monitor_data['data']['RX2Power']['value']
            transceiver_dom_info_dict['rx3power'] = dom_channel_monitor_data['data']['RX3Power']['value']
            transceiver_dom_info_dict['rx4power'] = dom_channel_monitor_data['data']['RX4Power']['value']
            transceiver_dom_info_dict['tx1bias'] = dom_channel_monitor_data['data']['TX1Bias']['value']
            transceiver_dom_info_dict['tx2bias'] = dom_channel_monitor_data['data']['TX2Bias']['value']
            transceiver_dom_info_dict['tx3bias'] = dom_channel_monitor_data['data']['TX3Bias']['value']
            transceiver_dom_info_dict['tx4bias'] = dom_channel_monitor_data['data']['TX4Bias']['value']

        else:
            offset = 256
            file_path = self._get_port_eeprom_path(port_num, self.DOM_EEPROM_ADDR)
            if not self._sfp_eeprom_present(file_path, 0):
                return None

            try:
                sysfsfile_eeprom = open(file_path, mode="rb", buffering=0)
            except IOError:
                print("Error: reading sysfs file %s" % file_path)
                return None

            sfpd_obj = sff8472Dom()
            if sfpd_obj is None:
                return None
            dom_temperature_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + SFP_TEMPE_OFFSET), SFP_TEMPE_WIDTH)
            if dom_temperature_raw is not None:
                dom_temperature_data = sfpd_obj.parse_temperature(dom_temperature_raw, 0)
            else:
                return None

            dom_voltage_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + SFP_VOLT_OFFSET), SFP_VOLT_WIDTH)
            if dom_voltage_raw is not None:
                dom_voltage_data = sfpd_obj.parse_voltage(dom_voltage_raw, 0)
            else:
                return None

            dom_channel_monitor_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + SFP_CHANNL_MON_OFFSET), SFP_CHANNL_MON_WIDTH)
            if dom_channel_monitor_raw is not None:
                dom_channel_monitor_data = sfpd_obj.parse_channel_monitor_params(dom_channel_monitor_raw, 0)
            else:
                return None

            try:
                sysfsfile_eeprom.close()
            except IOError:
                print("Error: closing sysfs file %s" % file_path)
                return None

            transceiver_dom_info_dict['temperature'] = dom_temperature_data['data']['Temperature']['value']
            transceiver_dom_info_dict['voltage'] = dom_voltage_data['data']['Vcc']['value']
            transceiver_dom_info_dict['rx1power'] = dom_channel_monitor_data['data']['RXPower']['value']
            transceiver_dom_info_dict['rx2power'] = 'N/A'
            transceiver_dom_info_dict['rx3power'] = 'N/A'
            transceiver_dom_info_dict['rx4power'] = 'N/A'
            transceiver_dom_info_dict['tx1bias'] = dom_channel_monitor_data['data']['TXBias']['value']
            transceiver_dom_info_dict['tx2bias'] = 'N/A'
            transceiver_dom_info_dict['tx3bias'] = 'N/A'
            transceiver_dom_info_dict['tx4bias'] = 'N/A'
            transceiver_dom_info_dict['tx1power'] = dom_channel_monitor_data['data']['TXPower']['value']
            transceiver_dom_info_dict['tx2power'] = 'N/A'
            transceiver_dom_info_dict['tx3power'] = 'N/A'
            transceiver_dom_info_dict['tx4power'] = 'N/A'

        return transceiver_dom_info_dict
    def get_transceiver_dom_threshold_info_dict(self, port_num):
        transceiver_dom_threshold_info_dict = {}

        dom_info_dict_keys = ['temphighalarm',    'temphighwarning',
                              'templowalarm',     'templowwarning',
                              'vcchighalarm',     'vcchighwarning',
                              'vcclowalarm',      'vcclowwarning',
                              'rxpowerhighalarm', 'rxpowerhighwarning',
                              'rxpowerlowalarm',  'rxpowerlowwarning',
                              'txpowerhighalarm', 'txpowerhighwarning',
                              'txpowerlowalarm',  'txpowerlowwarning',
                              'txbiashighalarm',  'txbiashighwarning',
                              'txbiaslowalarm',   'txbiaslowwarning'
                             ]
        transceiver_dom_threshold_info_dict = dict.fromkeys(dom_info_dict_keys, 'N/A')

        if port_num in self.osfp_ports:
            # Below part is added to avoid fail xcvrd, shall be implemented later
            return transceiver_dom_threshold_info_dict

        elif port_num in self.qsfp_ports:
            file_path = self._get_port_eeprom_path(port_num, self.IDENTITY_EEPROM_ADDR)
            if not self._sfp_eeprom_present(file_path, 0):
                return None

            try:
                sysfsfile_eeprom = open(file_path, mode="rb", buffering=0)
            except IOError:
                print("Error: reading sysfs file %s" % file_path)
                return None

            sfpd_obj = sff8436Dom()
            if sfpd_obj is None:
                return None

            # Dom Threshold data starts from offset 384
            # Revert offset back to 0 once data is retrieved
            offset = 384
            dom_module_threshold_raw = self._read_eeprom_specific_bytes(
                                     sysfsfile_eeprom,
                                     (offset + QSFP_MODULE_THRESHOLD_OFFSET),
                                     QSFP_MODULE_THRESHOLD_WIDTH)
            if dom_module_threshold_raw is not None:
                dom_module_threshold_data = sfpd_obj.parse_module_threshold_values(dom_module_threshold_raw, 0)
            else:
                return None

            dom_channel_threshold_raw = self._read_eeprom_specific_bytes(
                                      sysfsfile_eeprom,
                                      (offset + QSFP_CHANNL_THRESHOLD_OFFSET),
                                      QSFP_CHANNL_THRESHOLD_WIDTH)
            if dom_channel_threshold_raw is not None:
                dom_channel_threshold_data = sfpd_obj.parse_channel_threshold_values(dom_channel_threshold_raw, 0)
            else:
                return None

            try:
                sysfsfile_eeprom.close()
            except IOError:
                print("Error: closing sysfs file %s" % file_path)
                return None

            # Threshold Data
            transceiver_dom_threshold_info_dict['temphighalarm'] = dom_module_threshold_data['data']['TempHighAlarm']['value']
            transceiver_dom_threshold_info_dict['temphighwarning'] = dom_module_threshold_data['data']['TempHighWarning']['value']
            transceiver_dom_threshold_info_dict['templowalarm'] = dom_module_threshold_data['data']['TempLowAlarm']['value']
            transceiver_dom_threshold_info_dict['templowwarning'] = dom_module_threshold_data['data']['TempLowWarning']['value']
            transceiver_dom_threshold_info_dict['vcchighalarm'] = dom_module_threshold_data['data']['VccHighAlarm']['value']
            transceiver_dom_threshold_info_dict['vcchighwarning'] = dom_module_threshold_data['data']['VccHighWarning']['value']
            transceiver_dom_threshold_info_dict['vcclowalarm'] = dom_module_threshold_data['data']['VccLowAlarm']['value']
            transceiver_dom_threshold_info_dict['vcclowwarning'] = dom_module_threshold_data['data']['VccLowWarning']['value']
            transceiver_dom_threshold_info_dict['rxpowerhighalarm'] = dom_channel_threshold_data['data']['RxPowerHighAlarm']['value']
            transceiver_dom_threshold_info_dict['rxpowerhighwarning'] = dom_channel_threshold_data['data']['RxPowerHighWarning']['value']
            transceiver_dom_threshold_info_dict['rxpowerlowalarm'] = dom_channel_threshold_data['data']['RxPowerLowAlarm']['value']
            transceiver_dom_threshold_info_dict['rxpowerlowwarning'] = dom_channel_threshold_data['data']['RxPowerLowWarning']['value']
            transceiver_dom_threshold_info_dict['txbiashighalarm'] = dom_channel_threshold_data['data']['TxBiasHighAlarm']['value']
            transceiver_dom_threshold_info_dict['txbiashighwarning'] = dom_channel_threshold_data['data']['TxBiasHighWarning']['value']
            transceiver_dom_threshold_info_dict['txbiaslowalarm'] = dom_channel_threshold_data['data']['TxBiasLowAlarm']['value']
            transceiver_dom_threshold_info_dict['txbiaslowwarning'] = dom_channel_threshold_data['data']['TxBiasLowWarning']['value']

        else:
            offset = 256
            file_path = self._get_port_eeprom_path(port_num, self.DOM_EEPROM_ADDR)
            if not self._sfp_eeprom_present(file_path, 0):
                return None

            try:
                sysfsfile_eeprom = open(file_path, mode="rb", buffering=0)
            except IOError:
                print("Error: reading sysfs file %s" % file_path)
                return None

            sfpd_obj = sff8472Dom()
            if sfpd_obj is None:
                return None

            dom_module_threshold_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom,
                                         (offset + SFP_MODULE_THRESHOLD_OFFSET),
                                         SFP_MODULE_THRESHOLD_WIDTH)
            if dom_module_threshold_raw is not None:
                dom_module_threshold_data = sfpd_obj.parse_module_monitor_params(dom_module_threshold_raw, 0)
            else:
                return None

            dom_channel_threshold_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom,
                                         (offset + SFP_CHANNL_THRESHOLD_OFFSET),
                                         SFP_CHANNL_THRESHOLD_WIDTH)
            if dom_channel_threshold_raw is not None:
                dom_channel_threshold_data = sfpd_obj.parse_channel_thresh_monitor_params(dom_channel_threshold_raw, 0)
            else:
                return None

            try:
                sysfsfile_eeprom.close()
            except IOError:
                print("Error: closing sysfs file %s" % file_path)
                return None

            # Threshold Data
            transceiver_dom_threshold_info_dict['temphighalarm'] = dom_module_threshold_data['data']['TempHighAlarm']['value']
            transceiver_dom_threshold_info_dict['templowalarm'] = dom_module_threshold_data['data']['TempLowAlarm']['value']
            transceiver_dom_threshold_info_dict['temphighwarning'] = dom_module_threshold_data['data']['TempHighWarning']['value']
            transceiver_dom_threshold_info_dict['templowwarning'] = dom_module_threshold_data['data']['TempLowWarning']['value']
            transceiver_dom_threshold_info_dict['vcchighalarm'] = dom_module_threshold_data['data']['VccHighAlarm']['value']
            transceiver_dom_threshold_info_dict['vcclowalarm'] = dom_module_threshold_data['data']['VccLowAlarm']['value']
            transceiver_dom_threshold_info_dict['vcchighwarning'] = dom_module_threshold_data['data']['VccHighWarning']['value']
            transceiver_dom_threshold_info_dict['vcclowwarning'] = dom_module_threshold_data['data']['VccLowWarning']['value']
            transceiver_dom_threshold_info_dict['txbiashighalarm'] = dom_channel_threshold_data['data']['BiasHighAlarm']['value']
            transceiver_dom_threshold_info_dict['txbiaslowalarm'] = dom_channel_threshold_data['data']['BiasLowAlarm']['value']
            transceiver_dom_threshold_info_dict['txbiashighwarning'] = dom_channel_threshold_data['data']['BiasHighWarning']['value']
            transceiver_dom_threshold_info_dict['txbiaslowwarning'] = dom_channel_threshold_data['data']['BiasLowWarning']['value']
            transceiver_dom_threshold_info_dict['txpowerhighalarm'] = dom_channel_threshold_data['data']['TxPowerHighAlarm']['value']
            transceiver_dom_threshold_info_dict['txpowerlowalarm'] = dom_channel_threshold_data['data']['TxPowerLowAlarm']['value']
            transceiver_dom_threshold_info_dict['txpowerhighwarning'] = dom_channel_threshold_data['data']['TxPowerHighWarning']['value']
            transceiver_dom_threshold_info_dict['txpowerlowwarning'] = dom_channel_threshold_data['data']['TxPowerLowWarning']['value']
            transceiver_dom_threshold_info_dict['rxpowerhighalarm'] = dom_channel_threshold_data['data']['RxPowerHighAlarm']['value']
            transceiver_dom_threshold_info_dict['rxpowerlowalarm'] = dom_channel_threshold_data['data']['RxPowerLowAlarm']['value']
            transceiver_dom_threshold_info_dict['rxpowerhighwarning'] = dom_channel_threshold_data['data']['RxPowerHighWarning']['value']
            transceiver_dom_threshold_info_dict['rxpowerlowwarning'] = dom_channel_threshold_data['data']['RxPowerLowWarning']['value']

        return transceiver_dom_threshold_info_dict

    @abc.abstractmethod
    def get_presence(self, port_num):
        """
        :param port_num: Integer, index of physical port
        :returns: Boolean, True if tranceiver is present, False if not
        """
        return

    @abc.abstractmethod
    def get_low_power_mode(self, port_num):
        """
        :param port_num: Integer, index of physical port
        :returns: Boolean, True if low-power mode enabled, False if disabled
        """
        return

    @abc.abstractmethod
    def set_low_power_mode(self, port_num, lpmode):
        """
        :param port_num: Integer, index of physical port
        :param lpmode: Boolean, True to enable low-power mode, False to disable it
        :returns: Boolean, True if low-power mode set successfully, False if not
        """
        return

    @abc.abstractmethod
    def reset(self, port_num):
        """
        :param port_num: Integer, index of physical port
        :returns: Boolean, True if reset successful, False if not
        """
        return

    @abc.abstractmethod
    def get_transceiver_change_event(self, timeout=0):
        """
        :param timeout in milliseconds. The method is a blocking call. When timeout is
         zero, it only returns when there is change event, i.e., transceiver plug-in/out
         event. When timeout is non-zero, the function can also return when the timer expires.
         When timer expires, the return status is True and events is empty.
        :returns: (status, events)
        :status: Boolean, True if call successful and no system level event/error occurred,
         False if call not success or system level event/error occurred.
        :events: dictionary for physical port index and the SFP status,
         status='1' represent plug in, '0' represent plug out like {'0': '1', '31':'0'}
         when it comes to system level event/error, the index will be '-1',
         and status can be 'system_not_ready', 'system_become_ready', 'system_fail',
         like {'-1':'system_not_ready'}.
        """
        return

