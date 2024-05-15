#
# storage_common.py
#
# Class for common implementation functions,
# i.e. functions that are storage device type agnostic.
#

try:
    import os
    import sys
    import json
    import psutil
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")


class StorageCommon(object):
    def __init__(self, diskdev):
        """
        Constructor

        Args:
            Block device path for which we need to get information
        """
        self.DISKSTATS_FILE = "/proc/diskstats"
        self.storage_disk = os.path.basename(diskdev)
        self.fsstats_reads = 0
        self.fsstats_writes = 0

    def get_fs_io_reads(self):
        """
        Function to get the latest reads on the disk by parsing the /proc/diskstats file

        Returns:
            The total number of procfs reads

        Args:
            N/A
        """

        self.fsstats_reads = int(psutil.disk_io_counters(perdisk=True, nowrap=True)[self.storage_disk].read_count)

        return self.fsstats_reads

    def get_fs_io_writes(self):
        """
        Function to get the latest disk writes by parsing the /proc/diskstats file

        Returns:
            The total number of procfs writes

        Args:
            N/A
        """

        self.fsstats_writes = psutil.disk_io_counters(perdisk=True, nowrap=True)[self.storage_disk].write_count

        return self.fsstats_writes
