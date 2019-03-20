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
    from . import bcmshell			# Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from sonic_eeprom import eeprom_dts
    from .sff8472 import sff8472InterfaceId	# Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8472 import sff8472Dom		# Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8436 import sff8436InterfaceId	# Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8436 import sff8436Dom		# Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from inf8628 import inf8628InterfaceId
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

# definitions of the offset and width for values in XCVR info eeprom
XCVR_TYPE_OFFSET = 0
XCVR_TYPE_WIDTH = 1
XCVR_VENDOR_NAME_OFFSET = 20
XCVR_VENDOR_NAME_WIDTH = 16
XCVR_VENDOR_PN_OFFSET = 40
XCVR_VENDOR_PN_WIDTH = 16
XCVR_HW_REV_OFFSET = 56
XCVR_HW_REV_WIDTH_OSFP = 2
XCVR_HW_REV_WIDTH_QSFP = 2
XCVR_HW_REV_WIDTH_SFP = 4
XCVR_VENDOR_SN_OFFSET = 68
XCVR_VENDOR_SN_WIDTH = 16
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
QSFP_VLOT_OFFSET = 26
QSFP_VOLT_WIDTH = 2
QSFP_CHANNL_MON_OFFSET = 34
QSFP_CHANNL_MON_WIDTH = 16
QSFP_CHANNL_MON_WITH_TX_POWER_WIDTH = 24

SFP_TEMPE_OFFSET = 96
SFP_TEMPE_WIDTH = 2
SFP_VLOT_OFFSET = 98
SFP_VOLT_WIDTH = 2
SFP_CHANNL_MON_OFFSET = 100
SFP_CHANNL_MON_WIDTH = 6

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
            except:
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
            print("Error: reading sysfs file %s" % sysfs_sfp_i2c_client_eeprom_path)
            return None

        try:
            for n in range(0, num_bytes):
                eeprom_raw[n] = hex(ord(raw[n]))[2:].zfill(2)
        except:
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
        except:
            return None

        return eeprom_raw

    def _is_valid_port(self, port_num):
        if port_num >= self.port_start and port_num <= self.port_end:
            return True

        return False

    def read_porttab_mappings(self, porttabfile):
        logical = []
        logical_to_bcm = {}
        logical_to_physical = {}
        physical_to_logical = {}
        last_fp_port_index = 0
        last_portname = ""
        first = 1
        port_pos_in_file = 0
        parse_fmt_port_config_ini = False

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

            logical_to_bcm[portname] = "xe" + bcm_port
            logical_to_physical[portname] = [fp_port_index]
            if physical_to_logical.get(fp_port_index) is None:
                physical_to_logical[fp_port_index] = [portname]
            else:
                physical_to_logical[fp_port_index].append(
                    portname)

            if (fp_port_index - last_fp_port_index) > 1:
                # last port was a gang port
                for p in range(last_fp_port_index+1, fp_port_index):
                    logical_to_physical[last_portname].append(p)
                    if physical_to_logical.get(p) is None:
                        physical_to_logical[p] = [last_portname]
                    else:
                        physical_to_logical[p].append(last_portname)

            last_fp_port_index = fp_port_index
            last_portname = portname

            port_pos_in_file += 1

        self.logical = logical
        self.logical_to_bcm = logical_to_bcm
        self.logical_to_physical = logical_to_physical
        self.physical_to_logical = physical_to_logical

        """
        print("logical: " + self.logical)
        print("logical to bcm: " + self.logical_to_bcm)
        print("logical to physical: " + self.logical_to_physical)
        print("physical to logical: " + self.physical_to_logical)
        """

    def read_phytab_mappings(self, phytabfile):
        logical = []
        phytab_mappings = {}
        physical_to_logical = {}
        physical_to_phyaddrs = {}

        try:
            f = open(phytabfile)
        except:
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

        return self.physical_to_logical[port_num]

    def get_logical_to_physical(self, logical_port):
        """Returns list of physical ports for the given logical port"""

        return self.logical_to_physical[logical_port]

    def is_logical_port(self, port):
        if port in self.logical:
            return 1
        else:
            return 0

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
        for sfp_sysfs_path, attrs in sorted(self.eep_dict.iteritems()):
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

        if port_num in self.osfp_ports:
            offset = 0
            vendor_rev_width = XCVR_HW_REV_WIDTH_OSFP
        if port_num in self.qsfp_ports:
            offset = 128
            vendor_rev_width = XCVR_HW_REV_WIDTH_QSFP
        else:
            offset = 0
            vendor_rev_width = XCVR_HW_REV_WIDTH_SFP

        file_path = self._get_port_eeprom_path(port_num, self.IDENTITY_EEPROM_ADDR)
        if not self._sfp_eeprom_present(file_path, 0):
            print("Error, file not exist %s" % file_path)
            return None

        try:
            sysfsfile_eeprom = open(file_path, mode="rb", buffering=0)
        except IOError:
            print("Error: reading sysfs file %s" % file_path)
            return None

        if port_num in self.osfp_ports:
            sfpi_obj = inf8628InterfaceId()
        elif port_num in self.qsfp_ports:
            sfpi_obj = sff8436InterfaceId()
        else:
            sfpi_obj = sff8472InterfaceId()

        if sfpi_obj is None:
            print("Error: sfp_object open failed")
            return None

        if port_num in self.osfp_ports:
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
        else:
            sfp_type_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + XCVR_TYPE_OFFSET), XCVR_TYPE_WIDTH)
            if sfp_type_raw is not None:
                sfp_type_data = sfpi_obj.parse_sfp_type(sfp_type_raw, 0)
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

        try:
            sysfsfile_eeprom.close()
        except IOError:
            print("Error: closing sysfs file %s" % file_path)
            return None

        transceiver_info_dict['type'] = sfp_type_data['data']['type']['value']
        transceiver_info_dict['manufacturename'] = sfp_vendor_name_data['data']['Vendor Name']['value']
        transceiver_info_dict['modelname'] = sfp_vendor_pn_data['data']['Vendor PN']['value']
        transceiver_info_dict['hardwarerev'] = sfp_vendor_rev_data['data']['Vendor Rev']['value']
        transceiver_info_dict['serialnum'] = sfp_vendor_sn_data['data']['Vendor SN']['value']

        return transceiver_info_dict

    def get_transceiver_dom_info_dict(self, port_num):
        transceiver_dom_info_dict = {}

        if port_num in self.osfp_ports:
            pass
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
                qspf_dom_capability_data = sfpi_obj.parse_qsfp_dom_capability(qsfp_dom_capability_raw, 0)
            else:
                return None

            dom_temperature_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + QSFP_TEMPE_OFFSET), QSFP_TEMPE_WIDTH)
            if dom_temperature_raw is not None:
                dom_temperature_data = sfpd_obj.parse_temperature(dom_temperature_raw, 0)
            else:
                return None

            dom_voltage_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + QSFP_VLOT_OFFSET), QSFP_VOLT_WIDTH)
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

            dom_voltage_raw = self._read_eeprom_specific_bytes(sysfsfile_eeprom, (offset + SFP_VLOT_OFFSET), SFP_VOLT_WIDTH)
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
        :status: Boolean, True if call successful, False if not;
        :events: dictionary for pysical port index and the SFP status,
        status='1' represent plug in, '0' represent plug out like {'0': '1', '31':'0'}
        """
        return
