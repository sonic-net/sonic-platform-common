# pcie_common.py
# Common PCIE check interfaces for SONIC
#

import os
import yaml
import subprocess
import re
import sys
from copy import deepcopy
try:
    from .pcie_base import PcieBase
    import binascii
    from sonic_py_common import logger
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

# Enable logging by classes and helper functions
SYSLOG_IDENTIFIER = "PcieUtil"
log = logger.Logger(SYSLOG_IDENTIFIER)

class PcieUtil(PcieBase):
    """Platform-specific PCIEutil class"""
    # got the config file path
    def __init__(self, path):
        self.config_path = path
        self._conf_rev = None
        self.procfs_path = "/proc/bus/pci/"

    # load the config file
    def load_config_file(self):
        conf_rev = "_{}".format(self._conf_rev) if self._conf_rev else ""
        config_file = "{}/pcie{}.yaml".format(self.config_path, conf_rev)
        try:
            with open(config_file) as conf_file:
                self.confInfo = yaml.safe_load(conf_file)
        except IOError as e:
            log.log_error("Error: {}".format(str(e)))
            log.log_error("Not found config file, please add a config file manually, or generate it by running [pcieutil pcie_generate]")
            sys.exit()

    # load current PCIe device
    def get_pcie_device(self):
        pciDict = {}
        pciList = []
        p1 = "^(\w+):(\w+)\.(\w)\s(.*)\s*\(*.*\)*"
        p2 = "^.*:.*:.*:(\w+)\s*\(*.*\)*"
        command1 = ["sudo", "lspci"]
        command2 = ["sudo", "lspci", "-n"]
        # run command 1
        proc1 = subprocess.Popen(command1, universal_newlines=True, stdout=subprocess.PIPE)
        output1 = proc1.stdout.readlines()
        (out, err) = proc1.communicate()
        # run command 2
        proc2 = subprocess.Popen(command2, universal_newlines=True, stdout=subprocess.PIPE)
        output2 = proc2.stdout.readlines()
        (out, err) = proc2.communicate()

        if proc1.returncode > 0:
            for line1 in output1:
                print(line1.strip())
            return
        elif proc2.returncode > 0:
            for line2 in output2:
                print(line2.strip())
            return
        else:
            for (line1, line2) in zip(output1, output2):
                pciDict.clear()
                match1 = re.search(p1, line1.strip())
                match2 = re.search(p2, line2.strip())
                if match1 and match2:
                    Bus = match1.group(1)
                    Dev = match1.group(2)
                    Fn = match1.group(3)
                    Name = match1.group(4)
                    Id = match2.group(1)
                    pciDict["name"] = Name
                    pciDict["bus"] = Bus
                    pciDict["dev"] = Dev
                    pciDict["fn"] = Fn
                    pciDict["id"] = Id
                    pciList.append(pciDict)
                    pciDict = deepcopy(pciDict)
                else:
                    log.log_warning("CAN NOT MATCH PCIe DEVICE")
        return pciList

    # Check device ID from procfs file check for each PCI device
    def check_pcie_deviceid(self, bus="", device="", fn="", id=""):
        current_file = os.path.join(self.procfs_path, bus, "{}.{}".format(device, fn))
        pcie_device = ("{}:{}.{}".format(bus, device, fn))
        transaction_check = ['setpci', '-s', pcie_device, '2.w']
        try:
            with open(current_file, 'rb') as f:
                f.seek(2)
                data = f.read(2)
                hexstring = binascii.hexlify(data).decode('ascii')
                procfs_id = str(hexstring[-2:] + hexstring[:2])
                if id != procfs_id:
                    log.log_notice("PCIe YAML file device ID mismatch for {}:{}.{} - expected {}, got {}".format(bus, device, fn, id, procfs_id))

                output = subprocess.check_output(transaction_check)
                transaction_check_result = output.decode('utf8').strip()

                if procfs_id == transaction_check_result:
                    return True
                else:
                    log.log_warning("PCIe transaction check device ID mismatch for {}:{}.{} - expected {}, got {}".format(bus, device, fn, procfs_id, transaction_check_result))

                return False
        except OSError as osex:
            log.log_warning("Ecountered {} while trying to open {}".format(str(osex), current_file))
            return False



    # check the sysfs tree for each PCIe device
    def check_pcie_sysfs(self, domain=0, bus=0, device=0, func=0):
        dev_path = os.path.join('/sys/bus/pci/devices', '%04x:%02x:%02x.%d' % (domain, bus, device, func))
        if os.path.exists(dev_path):
            return True
        return False

    # check the current PCIe device with config file and return the result
    def get_pcie_check(self):
        self.load_config_file()
        for item_conf in self.confInfo:
            bus_conf = item_conf["bus"]
            dev_conf = item_conf["dev"]
            fn_conf  = item_conf["fn"]
            id_conf  = item_conf["id"]

            sysfs_check = self.check_pcie_sysfs(bus=int(bus_conf, base=16), device=int(dev_conf, base=16), func=int(fn_conf, base=16))
            deviceid_check = self.check_pcie_deviceid(bus_conf, dev_conf, fn_conf, id_conf)

            if sysfs_check and deviceid_check:
                item_conf["result"] = "Passed"
            else:
                item_conf["result"] = "Failed"
        return self.confInfo

    # return AER stats of PCIe device
    def get_pcie_aer_stats(self, domain=0, bus=0, dev=0, func=0):
        aer_stats = {'correctable': {}, 'fatal': {}, 'non_fatal': {}}
        dev_path = os.path.join('/sys/bus/pci/devices', '%04x:%02x:%02x.%d' % (domain, bus, dev, func))

        # construct AER sysfs filepath
        correctable_path = os.path.join(dev_path, "aer_dev_correctable")
        fatal_path = os.path.join(dev_path, "aer_dev_fatal")
        non_fatal_path = os.path.join(dev_path, "aer_dev_nonfatal")

        # update AER-correctable fields
        if os.path.isfile(correctable_path):
            with open(correctable_path, 'r') as fh:
                lines = fh.readlines()
            for line in lines:
                correctable_field, value = line.split()
                aer_stats['correctable'][correctable_field] = value

        # update AER-Fatal fields
        if os.path.isfile(fatal_path):
            with open(fatal_path, 'r') as fh:
                lines = fh.readlines()
            for line in lines:
                fatal_field, value = line.split()
                aer_stats['fatal'][fatal_field] = value

        # update AER-Non Fatal fields
        if os.path.isfile(non_fatal_path):
            with open(non_fatal_path, 'r') as fh:
                lines = fh.readlines()
            for line in lines:
                non_fatal_field, value = line.split()
                aer_stats['non_fatal'][non_fatal_field] = value

        return aer_stats

    # generate the config file with current pci device
    def dump_conf_yaml(self):
        curInfo = self.get_pcie_device()
        conf_rev = "_{}".format(self._conf_rev) if self._conf_rev else ""
        config_file = "{}/pcie{}.yaml".format(self.config_path, conf_rev)
        with open(config_file, "w") as conf_file:
            yaml.dump(curInfo, conf_file, default_flow_style=False)
        return
