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
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

try:
    import psutil
except ImportError as e:
    pass


class StorageCommon(object):
    def __init__(self, diskdev):
        """
        Constructor

        Args:
            Block device path for which we need to get information
        """
        self.DISKSTATS_FILE = "/proc/diskstats"
        self.diskdev = os.path.basename(diskdev)
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

        if 'psutil' in sys.modules:
            self.fsstats_reads = int(psutil.disk_io_counters(perdisk=True, nowrap=True)[self.diskdev].read_count)
        else:
            with open(self.DISKSTATS_FILE) as f:
                statsfile = f.readlines()
                for line in statsfile:
                    if self.diskdev == line.split()[2]:
                        self.fsstats_reads = int(line.split()[3])
                        break

        return self.fsstats_reads

    def get_fs_io_writes(self):
        """
        Function to get the latest disk writes by parsing the /proc/diskstats file

        Returns:
            The total number of procfs writes

        Args:
            N/A
        """

        if 'psutil' in sys.modules:
            self.fsstats_writes = psutil.disk_io_counters(perdisk=True, nowrap=True)[self.diskdev].write_count
        else:
            with open(self.DISKSTATS_FILE) as f:
                statsfile = f.readlines()
                for line in statsfile:
                    if self.diskdev == line.split()[2]:
                        self.fsstats_writes = int(line.split()[7])
                        break

        return self.fsstats_writes
