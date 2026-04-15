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
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")


class PcieUtil(PcieBase):
    """Platform-specific PCIEutil class"""
    # got the config file path
    def __init__(self, path):
        self.config_path = path
        self._conf_rev = None

    # load the config file
    def load_config_file(self):
        conf_rev = "_{}".format(self._conf_rev) if self._conf_rev else ""
        config_file = "{}/pcie{}.yaml".format(self.config_path, conf_rev)
        try:
            with open(config_file) as conf_file:
                self.confInfo = yaml.safe_load(conf_file)
        except IOError as e:
            print("Error: {}".format(str(e)))
            print("Not found config file, please add a config file manually, or generate it by running [pcieutil pcie_generate]")
            sys.exit()

    # load current PCIe device
    def get_pcie_device(self):
        pciList = []
        seen = set()

        # Domain-aware output:
        #   0002:01:00.0 Ethernet controller: ...
        p1 = r"^([0-9a-fA-F]{4}):([0-9a-fA-F]{2}):([0-9a-fA-F]{2})\.([0-7])\s+(.*)$"
        # Numeric output:
        #   0002:01:00.0 0200: 177d:a065 ...
        p2 = r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]\s+[0-9a-fA-F]{4}:\s*([0-9a-fA-F]{4}):([0-9a-fA-F]{4}).*$"

        command1 = ["sudo", "lspci", "-D"]
        command2 = ["sudo", "lspci", "-D", "-n"]

        proc1 = subprocess.Popen(command1, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output1, err1 = proc1.communicate()

        proc2 = subprocess.Popen(command2, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output2, err2 = proc2.communicate()

        if proc1.returncode != 0:
            print(output1)
            print(err1)
            return []
        if proc2.returncode != 0:
            print(output2)
            print(err2)
            return []

        lines1 = output1.splitlines()
        lines2 = output2.splitlines()

        for line1, line2 in zip(lines1, lines2):
            match1 = re.search(p1, line1.strip())
            match2 = re.search(p2, line2.strip())
            if not (match1 and match2):
                print("CAN NOT MATCH PCIe DEVICE")
                print("lspci   :", line1.strip())
                print("lspci -n:", line2.strip())
                continue

            domain = match1.group(1).lower()
            bus = match1.group(2).lower()
            dev = match1.group(3).lower()
            fn = match1.group(4).lower()
            name = match1.group(5).strip()
            vendor = match2.group(1).lower()
            device = match2.group(2).lower()

            key = (domain, bus, dev, fn)
            if key in seen:
                continue
            seen.add(key)

            pciDict = {
                "name": name,
                "domain": domain,
                "bus": bus,
                "dev": dev,
                "fn": fn,
                "id": device,
                "vendor": vendor
            }
            pciList.append(deepcopy(pciDict))

        return pciList

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
            domain_conf = item_conf.get("domain", "0000")
            bus_conf = item_conf["bus"]
            dev_conf = item_conf["dev"]
            fn_conf = item_conf["fn"]

            if self.check_pcie_sysfs(
                domain=int(domain_conf, base=16),
                bus=int(bus_conf, base=16),
                device=int(dev_conf, base=16),
                func=int(fn_conf, base=16)
            ):
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
            yaml.dump(curInfo, conf_file, default_flow_style=False, sort_keys=False)
        return
        
