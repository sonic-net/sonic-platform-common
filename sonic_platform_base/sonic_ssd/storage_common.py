#
# storage_common.py
#
# Class for common implementation functions,
# i.e. functions that are storage device type agnostic.
#

try:
    import os
    import sys
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
        self.MOUNTS_FILE = "/proc/mounts"
        self.diskdev = os.path.basename(diskdev)
        self.partition = self.__set_host_partition(self.diskdev)

    def __set_host_partition(self, diskdev):
        """
        internal function to fetch SONiC partition
        
        Returns:
            The partition containing '/host' mount, or 'N/A' if not found
        Args:
            N/A
        """
        if 'psutil' in sys.modules:
            for p in psutil.disk_partitions():
                if p.mountpoint == "/host":
                    return os.path.basename(p.device)
            return None

        else:
            mounts = ""
            with open(self.MOUNTS_FILE) as f:
                mounts = f.readlines()

            for mt in mounts:
                if '/host' in mt and diskdev in mt:
                    return os.path.basename(mt.split()[0])
            return None

    def get_fs_io_reads(self):
        """
        Function to get the total number of reads on the 'SONiC' partition by parsing the /proc/diskstats file

        Returns:
            The total number of FS reads OR disk reads if storage device does not host the SONiC OS
        
        Args:
            N/A
        """

        searchterm = self.partition
        if searchterm == None: searchterm = self.diskdev

        if 'psutil' in sys.modules:
            return psutil.disk_io_counters(perdisk=True, nowrap=True)[searchterm].read_count
        else:
            with open(self.DISKSTATS_FILE) as f:
                statsfile = f.readlines()
                for line in statsfile:
                    if searchterm in line:
                        return line.split()[3]
                return 'N/A'

    def get_fs_io_writes(self):
        """
        Function to get the total number of writes on the 'SONiC' partition by parsing the /proc/diskstats file

        Returns:
            The total number of FS writes OR disk writes if storage device does not host the SONiC OS
        
        Args:
            N/A
        """

        searchterm = self.partition
        if searchterm == None: searchterm = self.diskdev

        if 'psutil' in sys.modules:
            return psutil.disk_io_counters(perdisk=True, nowrap=True)[searchterm].write_count
        else:
            with open(self.DISKSTATS_FILE) as f:
                statsfile = f.readlines()
                for line in statsfile:
                    if searchterm in line:
                        return line.split()[7]
                return 'N/A'