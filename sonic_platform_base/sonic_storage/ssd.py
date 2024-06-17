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

    from .storage_common import StorageCommon
    from sonic_py_common import syslogger
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")


SMARTCTL = "smartctl {} -a"
INNODISK = "iSmart -d {}"
VIRTIUM  = "SmartCmd -m {}"
TRANSCEND = "scopepro -all {}"

NOT_AVAILABLE = "N/A"

# Generic IDs

GENERIC_HEALTH_ID = 169
GENERIC_IO_READS_ID = 242
GENERIC_IO_WRITES_ID = 241
GENERIC_RESERVED_BLOCKS_ID = [170, 232]

# Set Vendor Specific IDs
INNODISK_HEALTH_ID = 169
INNODISK_TEMPERATURE_ID = 194
INNODISK_IO_WRITES_ID = 241
INNODISK_IO_READS_ID = 242
INNODISK_RESERVED_BLOCKS_ID = 232

SWISSBIT_HEALTH_ID = 248
SWISSBIT_TEMPERATURE_ID = 194

VIRTIUM_HEALTH_ID = 231
VIRTIUM_RESERVED_BLOCKS_ID = 232
VIRTIUM_IO_WRITES_ID = 241
VIRTIUM_IO_READS_ID = 242

MICRON_RESERVED_BLOCKS_ID = [170, 180]
MICRON_IO_WRITES_ID = 246
MICRON_ERASE_FAIL_COUNT_ID = 172
MICRON_AVG_ERASE_COUNT_ID = 173
MICRON_PERC_LIFETIME_REMAIN_ID = 202

INTEL_MEDIA_WEAROUT_INDICATOR_ID = 233
TRANSCEND_HEALTH_ID = 169
TRANSCEND_TEMPERATURE_ID = 194

class SsdUtil(StorageCommon):
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
    fs_io_reads = NOT_AVAILABLE
    fs_io_writes = NOT_AVAILABLE
    disk_io_reads = NOT_AVAILABLE
    disk_io_writes = NOT_AVAILABLE
    reserved_blocks = NOT_AVAILABLE

    def __init__(self, diskdev):

        self.log_identifier = "SsdUtil"
        self.log = syslogger.SysLogger(self.log_identifier)

        self.vendor_ssd_utility = {
            "Generic"  : { "utility" : SMARTCTL, "parser" : self.parse_generic_ssd_info },
            "InnoDisk" : { "utility" : INNODISK, "parser" : self.parse_innodisk_info },
            "M.2"      : { "utility" : INNODISK, "parser" : self.parse_innodisk_info },
            "StorFly"  : { "utility" : VIRTIUM,  "parser" : self.parse_virtium_info },
            "Virtium"  : { "utility" : VIRTIUM,  "parser" : self.parse_virtium_info },
            "Swissbit" : { "utility" : SMARTCTL, "parser" : self.parse_swissbit_info },
            "Micron"   : { "utility" : SMARTCTL, "parser" : self.parse_micron_info },
            "Intel"    : { "utility" : SMARTCTL, "parser" : self.parse_intel_info },
            "Transcend" : { "utility" : TRANSCEND, "parser" : self.parse_transcend_info },
        }

        self.dev = diskdev
        self.fetch_parse_info(diskdev)

        StorageCommon.__init__(self, diskdev)

    def fetch_parse_info(self, diskdev):

        # Generic part
        self.fetch_generic_ssd_info(diskdev)
        self.parse_generic_ssd_info()

        # Known vendor part
        if self.model:
            vendor = self._parse_vendor()
            if vendor:

                self.fetch_vendor_ssd_info(diskdev, vendor)
                try:
                    self.parse_vendor_ssd_info(vendor)
                except Exception as ex:
                    self.log.log_error("{}".format(str(ex)))

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
        elif self.model.startswith('SFS'):
            return 'Swissbit'
        elif re.search(r'\bmicron\b', self.model.split('_')[0], re.I):
            return 'Micron'
        elif re.search(r'\bintel\b', self.model, re.I):
            return 'Intel'
        elif self.model.startswith('TS'):
            return 'Transcend'
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
                health_raw = self.parse_id_number(GENERIC_HEALTH_ID, self.ssd_info)
                if health_raw == NOT_AVAILABLE:
                    self.health = NOT_AVAILABLE
                else: self.health = health_raw.split()[-1]
            else:
                self.health = health_raw.split()[-1]

            temp_raw = self._parse_re('Temperature_Celsius\s*(.+?)\n', self.ssd_info)
            if temp_raw == NOT_AVAILABLE:
                self.temperature = NOT_AVAILABLE
            else:
                self.temperature = temp_raw.split()[7].split()[0]

        self.serial = self._parse_re('Serial Number:\s*(.+?)\n', self.ssd_info)
        self.firmware = self._parse_re('Firmware Version:\s*(.+?)\n', self.ssd_info)

        io_reads_raw = self.parse_id_number(GENERIC_IO_READS_ID, self.ssd_info)
        self.disk_io_reads = NOT_AVAILABLE if io_reads_raw == NOT_AVAILABLE else io_reads_raw.split()[-1]

        io_writes_raw = self.parse_id_number(GENERIC_IO_WRITES_ID, self.ssd_info)
        self.disk_io_writes = NOT_AVAILABLE if io_writes_raw == NOT_AVAILABLE else io_writes_raw.split()[-1]

        for ID in GENERIC_RESERVED_BLOCKS_ID:
            rbc_raw = self.parse_id_number(ID, self.ssd_info)
            if rbc_raw == NOT_AVAILABLE: self.reserved_blocks = NOT_AVAILABLE
            else:
                self.reserved_blocks = rbc_raw.split()[-1]
                break

    def parse_innodisk_info(self):
        if self.vendor_ssd_info:
            if self.health == NOT_AVAILABLE: self.health = self._parse_re('Health:\s*(.+?)%', self.vendor_ssd_info)
            if self.temperature == NOT_AVAILABLE: self.temperature = self._parse_re('Temperature\s*\[\s*(.+?)\]', self.vendor_ssd_info)
            if self.firmware == NOT_AVAILABLE: self.firmware = (self._parse_re('.*FW.*', self.vendor_ssd_info)).split()[-1]
            if self.serial == NOT_AVAILABLE: self.serial = (self._parse_re('.*Serial.*', self.vendor_ssd_info)).split()[-1]

        if self.health == NOT_AVAILABLE:
            health_raw = self.parse_id_number("[{}]".format(hex(INNODISK_HEALTH_ID)[2:]).upper(), self.vendor_ssd_info)
            if health_raw == NOT_AVAILABLE:
                self.health = NOT_AVAILABLE
            else:
                self.health = health_raw.split()[-2].strip("[]")
        if self.temperature == NOT_AVAILABLE:
            temp_raw = self.parse_id_number("[{}]".format(hex(INNODISK_TEMPERATURE_ID)[2:]).upper(), self.vendor_ssd_info)
            if temp_raw == NOT_AVAILABLE:
                self.temperature = NOT_AVAILABLE
            else:
                self.temperature = temp_raw.split()[-6]
        if self.disk_io_reads == NOT_AVAILABLE:
            io_reads_raw = self.parse_id_number("[{}]".format(hex(INNODISK_IO_READS_ID)[2:]).upper(), self.vendor_ssd_info)
            if io_reads_raw == NOT_AVAILABLE:
                self.disk_io_reads == NOT_AVAILABLE
            else:
                self.disk_io_reads = io_reads_raw.split()[-2].strip("[]")
        if self.disk_io_writes == NOT_AVAILABLE:
            io_writes_raw = self.parse_id_number("[{}]".format(hex(INNODISK_IO_WRITES_ID)[2:]).upper(), self.vendor_ssd_info)
            if io_writes_raw == NOT_AVAILABLE:
                self.disk_io_writes == NOT_AVAILABLE
            else:
                self.disk_io_writes = io_writes_raw.split()[-2].strip("[]")
        if self.reserved_blocks == NOT_AVAILABLE:
            rbc_raw = self.parse_id_number("[{}]".format(hex(INNODISK_RESERVED_BLOCKS_ID)[2:]).upper(), self.vendor_ssd_info)
            if rbc_raw == NOT_AVAILABLE:
                self.reserved_blocks == NOT_AVAILABLE
            else:
                self.reserved_blocks = rbc_raw.split()[-2].strip("[]")

    def parse_virtium_info(self):
        if self.vendor_ssd_info:
            vendor_temp = self._parse_re('Temperature_Celsius\s*\d*\s*(\d+?)\s+', self.vendor_ssd_info)
            if vendor_temp != NOT_AVAILABLE:
                self.temperature = vendor_temp
            nand_endurance = self._parse_re('NAND_Endurance\s*\d*\s*(\d+?)\s+', self.vendor_ssd_info)
            avg_erase_count = self._parse_re('Average_Erase_Count\s*\d*\s*(\d+?)\s+', self.vendor_ssd_info)
            if nand_endurance != NOT_AVAILABLE and avg_erase_count != NOT_AVAILABLE:
                try:
                    self.health = 100 - (float(avg_erase_count) * 100 / float(nand_endurance))
                except (ValueError, ZeroDivisionError) as ex:
                    self.log.log_info("SsdUtil parse_virtium_info exception: {}".format(ex))
                    pass
            else:
                health_raw = NOT_AVAILABLE
                try:
                    if self.model == 'VSFDM8XC240G-V11-T':
                        # The ID of "Remaining Life Left" attribute on 'VSFDM8XC240G-V11-T' device is 231
                        # However, it is not recognized by SmartCmd nor smartctl so far
                        # We need to parse it using the ID number
                        health_raw = self.parse_id_number(VIRTIUM_HEALTH_ID, self.vendor_ssd_info)
                        self.health = float(health_raw.split()[2]) if health_raw != NOT_AVAILABLE else NOT_AVAILABLE
                    else:
                        pattern = 'Remaining_Life_Left\s*\d*\s*(\d+?)\s+'
                        health_raw = self._parse_re(pattern, self.vendor_ssd_info)
                        self.health = float(health_raw.split()[-1]) if health_raw != NOT_AVAILABLE else NOT_AVAILABLE
                except ValueError as ex:
                    self.log.log_info("SsdUtil parse_virtium_info exception: {}".format(ex))
                    pass

            if self.disk_io_reads == NOT_AVAILABLE:
                io_reads_raw = self.parse_id_number(VIRTIUM_IO_READS_ID, self.vendor_ssd_info)
                if io_reads_raw == NOT_AVAILABLE:
                    self.disk_io_reads == NOT_AVAILABLE
                else:
                    self.disk_io_reads = io_reads_raw.split()[-1]

            if self.disk_io_writes == NOT_AVAILABLE:
                io_writes_raw = self.parse_id_number(VIRTIUM_IO_WRITES_ID, self.vendor_ssd_info)
                if io_writes_raw == NOT_AVAILABLE:
                    self.disk_io_writes == NOT_AVAILABLE
                else:
                    self.disk_io_writes = io_writes_raw.split()[-1]

            if self.reserved_blocks == NOT_AVAILABLE:
                rbc_raw = self.parse_id_number(VIRTIUM_RESERVED_BLOCKS_ID, self.vendor_ssd_info)
                if rbc_raw == NOT_AVAILABLE:
                    self.reserved_blocks == NOT_AVAILABLE
                else:
                    self.reserved_blocks = rbc_raw.split()[-1]

    def parse_swissbit_info(self):
        if self.ssd_info:
            health_raw = self.parse_id_number(SWISSBIT_HEALTH_ID, self.ssd_info)
            if health_raw == NOT_AVAILABLE:
                self.health = NOT_AVAILABLE
            else:
                self.health = health_raw.split()[-1]
            temp_raw = self.parse_id_number(SWISSBIT_TEMPERATURE_ID, self.ssd_info)
            if temp_raw == NOT_AVAILABLE:
                self.temperature = NOT_AVAILABLE
            else:
                self.temperature = temp_raw.split()[8]

    def parse_micron_info(self):
        if self.vendor_ssd_info:
            health_raw = self._parse_re('{}\s*(.+?)\n'.format('Percent_Lifetime_Used'), self.vendor_ssd_info)
            if health_raw == NOT_AVAILABLE:
                health_raw = self._parse_re('{}\s*(.+?)\n'.format('Percent_Lifetime_Remain'), self.vendor_ssd_info)
                self.health = health_raw.split()[-1]
            else:
                self.health = str(100 - int(health_raw.split()[-1]))

            if health_raw == NOT_AVAILABLE:
                average_erase_count = self.parse_id_number(MICRON_AVG_ERASE_COUNT_ID, self.vendor_ssd_info)
                erase_fail_count = self.parse_id_number(MICRON_ERASE_FAIL_COUNT_ID, self.vendor_ssd_info)

                if average_erase_count != NOT_AVAILABLE and erase_fail_count != NOT_AVAILABLE:
                    try:
                        self.health = 100 - (float(average_erase_count) * 100 / float(nand_endurance))
                    except (ValueError, ZeroDivisionError) as ex:
                        self.log.log_info("SsdUtil parse_micron_info exception: {}".format(ex))
                        pass

            io_writes_raw = self.parse_id_number(MICRON_IO_WRITES_ID, self.vendor_ssd_info)
            self.disk_io_writes = NOT_AVAILABLE if io_writes_raw == NOT_AVAILABLE else io_writes_raw.split()[-1]

            for ID in MICRON_RESERVED_BLOCKS_ID:
                rbc_raw = self.parse_id_number(ID, self.vendor_ssd_info)

                if rbc_raw == NOT_AVAILABLE: self.reserved_blocks = NOT_AVAILABLE
                else: 
                    self.reserved_blocks = rbc_raw.split()[-1]
                    break

    def parse_intel_info(self):
        if self.vendor_ssd_info:
            health_raw = self.parse_id_number(INTEL_MEDIA_WEAROUT_INDICATOR_ID, self.vendor_ssd_info)
            self.health = NOT_AVAILABLE if health_raw == NOT_AVAILABLE else str(100 - float(health_raw.split()[-1]))

    def parse_transcend_info(self):
        if self.vendor_ssd_info:
            self.model = self._parse_re('Model\s*:(.+?)\s*\n', self.vendor_ssd_info)
            self.serial = self._parse_re('Serial No\s*:(.+?)\s*\n', self.vendor_ssd_info)
            self.firmware = self._parse_re('FW Version\s*:(.+?)\s*\n', self.vendor_ssd_info)
            health_raw = self._parse_re('{}\s*(.+?)\n'.format(hex(TRANSCEND_HEALTH_ID).upper()[2:]), self.vendor_ssd_info) #169 -> A9
            if health_raw == NOT_AVAILABLE:
                self.health = NOT_AVAILABLE
            else:
                self.health = health_raw.split()[-1]
            temp_raw = self._parse_re('{}\s*(.+?)\n'.format(hex(TRANSCEND_TEMPERATURE_ID).upper()[2:]), self.vendor_ssd_info) #194 -> C2
            if temp_raw == NOT_AVAILABLE:
                self.temperature = NOT_AVAILABLE
            else:
                self.temperature = temp_raw.split()[-1]

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

    def get_disk_io_reads(self):
        """
        Retrieves the total number of Input/Output (I/O) reads done on an SSD

        Returns:
            An integer value of the total number of I/O reads
        """
        return self.disk_io_reads

    def get_disk_io_writes(self):
        """
        Retrieves the total number of Input/Output (I/O) writes done on an SSD

        Returns:
            An integer value of the total number of I/O writes
        """
        return self.disk_io_writes

    def get_reserved_blocks(self):
        """
        Retrieves the total number of reserved blocks in an SSD

        Returns:
            An integer value of the total number of reserved blocks
        """
        return self.reserved_blocks

    def get_vendor_output(self):
        """
        Retrieves vendor specific data for the given disk device

        Returns:
            A string holding some vendor specific disk information
        """
        return self.vendor_ssd_info

    def parse_id_number(self, id, buffer):
        if buffer:
            buffer_lines = buffer.split('\n')
            for line in buffer_lines:
                if line.strip().startswith(str(id)):
                    return line[len(str(id)):]

        return NOT_AVAILABLE
