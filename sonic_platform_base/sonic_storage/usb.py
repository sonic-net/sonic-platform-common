#
# usb.py
#
# Implementation of SSD Utility API for eUSB.
# It reads eUSB health, model, firmware, and serial from /sys/block/*.
#

try:
    import os
    from .storage_common import StorageCommon
    from sonic_py_common import syslogger
    from blkinfo import BlkDiskInfo
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")


NOT_AVAILABLE = "N/A"

class UsbUtil(StorageCommon):

    model = NOT_AVAILABLE
    serial = NOT_AVAILABLE
    firmware = NOT_AVAILABLE
    temperature = NOT_AVAILABLE
    health = NOT_AVAILABLE
    vendor = NOT_AVAILABLE
    disk_io_reads = NOT_AVAILABLE
    disk_io_writes = NOT_AVAILABLE
    reserved_blocks = NOT_AVAILABLE
    blkd = {}


    def __init__(self, diskdev):

        self.diskdev = diskdev
        self.path = os.path.join('/sys/block', os.path.basename(diskdev))
        StorageCommon.__init__(self, diskdev)

        self.log_identifier = "UsbUtil"
        self.log = syslogger.SysLogger(self.log_identifier)

        self.fetch_parse_info()

    def fetch_parse_info(self, diskdev=None):
        self.fetch_blkinfo()
        self.parse_blkinfo()

    def fetch_blkinfo(self):
        filters = {}
        filters['name'] = '{}'.format(os.path.basename(self.diskdev))
        self.blkd = BlkDiskInfo().get_disks(filters)[0]

    def parse_blkinfo(self):
        if 'dict' in str(type(self.blkd)) and self.blkd:
            self.model = self.blkd["model"]
            self.serial = self.blkd["serial"]
            self.vendor = self.blkd["vendor"]

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
        return self.vendor