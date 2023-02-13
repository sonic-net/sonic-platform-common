#
# ssd_generic.py
#
# Generic implementation of the SSD health API
# SSD models supported:
#  - InnoDisk
#  - StorFly
#  - Virtium

try:
    import re
    import subprocess
    from .ssd_base import SsdBase
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

SMARTCTL = "smartctl {} -a"
INNODISK = "iSmart -d {}"
VIRTIUM  = "SmartCmd -m {}"

NOT_AVAILABLE = "N/A"

# Set Vendor Specific IDs
INNODISK_HEALTH_ID = 169
INNODISK_TEMPERATURE_ID = 194

class SsdUtil(SsdBase):
    """
    Generic implementation of the SSD health API
    """
    model = NOT_AVAILABLE
    serial = NOT_AVAILABLE
    firmware = NOT_AVAILABLE
    temperature = NOT_AVAILABLE
    health = NOT_AVAILABLE
    ssd_info = NOT_AVAILABLE
    vendor_ssd_info = NOT_AVAILABLE

    def __init__(self, diskdev):
        self.vendor_ssd_utility = {
            "Generic"  : { "utility" : SMARTCTL, "parser" : self.parse_generic_ssd_info },
            "InnoDisk" : { "utility" : INNODISK, "parser" : self.parse_innodisk_info },
            "M.2"      : { "utility" : INNODISK, "parser" : self.parse_innodisk_info },
            "StorFly"  : { "utility" : VIRTIUM,  "parser" : self.parse_virtium_info },
            "Virtium"  : { "utility" : VIRTIUM,  "parser" : self.parse_virtium_info }
        }

        self.dev = diskdev
        # Generic part
        self.fetch_generic_ssd_info(diskdev)
        self.parse_generic_ssd_info()

        # Known vendor part
        if self.model:
            vendor = self._parse_vendor()
            if vendor:
                self.fetch_vendor_ssd_info(diskdev, vendor)
                self.parse_vendor_ssd_info(vendor)
            else:
                # No handler registered for this disk model
                pass
        else:
            # Failed to get disk model
            self.model = "Unknown"

    def _execute_shell(self, cmd):
        process = subprocess.Popen(cmd.split(), universal_newlines=True, stdout=subprocess.PIPE)
        output, error = process.communicate()
        return output

    def _parse_re(self, pattern, buffer):
        res_list = re.findall(pattern, buffer)
        return res_list[0] if res_list else NOT_AVAILABLE

    def _parse_vendor(self):
        model_short = self.model.split()[0]
        if model_short in self.vendor_ssd_utility:
            return model_short
        elif self.model.startswith('VSF'):
            return 'Virtium'
        else:
            return None

    def fetch_generic_ssd_info(self, diskdev):
        self.ssd_info = self._execute_shell(self.vendor_ssd_utility["Generic"]["utility"].format(diskdev))

    # Health and temperature values may be overwritten with vendor specific data
    def parse_generic_ssd_info(self):
        if "nvme" in self.dev:
            self.model = self._parse_re('Model Number:\s*(.+?)\n', self.ssd_info)

            health_raw = self._parse_re('Percentage Used\s*(.+?)\n', self.ssd_info)
            if health_raw == NOT_AVAILABLE:
                self.health = NOT_AVAILABLE
            else:
                health_raw = health_raw.split()[-1]
                self.health = 100 - float(health_raw.strip('%'))

            temp_raw = self._parse_re('Temperature\s*(.+?)\n', self.ssd_info)
            if temp_raw == NOT_AVAILABLE:
                self.temperature = NOT_AVAILABLE
            else:
                temp_raw = temp_raw.split()[-2]
                self.temperature = float(temp_raw)
        else:
            self.model = self._parse_re('Device Model:\s*(.+?)\n', self.ssd_info)

            health_raw = self._parse_re('Remaining_Lifetime_Perc\s*(.+?)\n', self.ssd_info)
            if health_raw == NOT_AVAILABLE:
                self.health = NOT_AVAILABLE
            else:
                self.health = health_raw.split()[-1]

            temp_raw = self._parse_re('Temperature_Celsius\s*(.+?)\n', self.ssd_info)
            if temp_raw == NOT_AVAILABLE:
                self.temperature = NOT_AVAILABLE
            else:
                self.temperature = temp_raw.split()[-6]

        self.serial = self._parse_re('Serial Number:\s*(.+?)\n', self.ssd_info)
        self.firmware = self._parse_re('Firmware Version:\s*(.+?)\n', self.ssd_info)

    def parse_innodisk_info(self):
        if self.vendor_ssd_info:
            self.health = self._parse_re('Health:\s*(.+?)%', self.vendor_ssd_info)
            self.temperature = self._parse_re('Temperature\s*\[\s*(.+?)\]', self.vendor_ssd_info)
        else:
            if self.health == NOT_AVAILABLE:
                health_raw = self.parse_id_number(INNODISK_HEALTH_ID)
                self.health = health_raw.split()[-1]
            if self.temperature == NOT_AVAILABLE:
                temp_raw = self.parse_id_number(INNODISK_TEMPERATURE_ID)
                self.temperature = temp_raw.split()[-6]

    def parse_virtium_info(self):
        if self.vendor_ssd_info:
            self.temperature = self._parse_re('Temperature_Celsius\s*\d*\s*(\d+?)\s+', self.vendor_ssd_info)
            nand_endurance = self._parse_re('NAND_Endurance\s*\d*\s*(\d+?)\s+', self.vendor_ssd_info)
            avg_erase_count = self._parse_re('Average_Erase_Count\s*\d*\s*(\d+?)\s+', self.vendor_ssd_info)
            if nand_endurance != NOT_AVAILABLE and avg_erase_count != NOT_AVAILABLE:
                try:
                    self.health = 100 - (float(avg_erase_count) * 100 / float(nand_endurance))
                except (ValueError, ZeroDivisionError):
                    pass
            else:
                try:
                    self.health = float(self._parse_re('Remaining_Life_Left\s*\d*\s*(\d+?)\s+', self.vendor_ssd_info))
                except ValueError:
                    pass
        
    def fetch_vendor_ssd_info(self, diskdev, model):
        self.vendor_ssd_info = self._execute_shell(self.vendor_ssd_utility[model]["utility"].format(diskdev))

    def parse_vendor_ssd_info(self, model):
        self.vendor_ssd_utility[model]["parser"]()

    def get_health(self):
        """
        Retrieves current disk health in percentages

        Returns:
            A float number of current ssd health
            e.g. 83.5
        """
        return self.health

    def get_temperature(self):
        """
        Retrieves current disk temperature in Celsius

        Returns:
            A float number of current temperature in Celsius
            e.g. 40.1
        """
        return self.temperature

    def get_model(self):
        """
        Retrieves model for the given disk device

        Returns:
            A string holding disk model as provided by the manufacturer
        """
        return self.model

    def get_firmware(self):
        """
        Retrieves firmware version for the given disk device

        Returns:
            A string holding disk firmware version as provided by the manufacturer
        """
        return self.firmware

    def get_serial(self):
        """
        Retrieves serial number for the given disk device

        Returns:
            A string holding disk serial number as provided by the manufacturer
        """
        return self.serial

    def get_vendor_output(self):
        """
        Retrieves vendor specific data for the given disk device

        Returns:
            A string holding some vendor specific disk information
        """
        return self.vendor_ssd_info

    def parse_id_number(self, id):
        return self._parse_re('{}\s*(.+?)\n'.format(id), self.ssd_info)
