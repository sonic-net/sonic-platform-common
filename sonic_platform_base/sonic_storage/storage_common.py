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
        self.FSSTATS_FILE_PREFIX = "/host/storagemon/fs-stats"
        self.diskdev = os.path.basename(diskdev)
        self.fs_reads = 0
        self.fs_writes = 0
        self._parse_fsstats_file()

    def _parse_fsstats_file(self):
        """
        Function to parse a file containing the previous latest FS IO Reads/Writes values from the corresponding disk's file and saves it to member variables

        Args: None

        Returns: None

        """
        filename = self.FSSTATS_FILE_PREFIX + "-" + self.diskdev

        if not os.path.isfile(filename):
            with open(filename, 'w') as f:
                f.write("{} {}".format(self.fs_reads, self.fs_writes))
                return
        else:
            try:
                with open(filename) as f:
                    fsstats = f.readline().strip()
                    self.fs_reads = fsstats.split()[0]
                    self.fs_writes = fsstats.split()[1]
            except Exception as e:
                os.remove(filename)
                pass


    def _update_fsstats_file(self, value, attr):
        """
        Function to update the latest FS IO Reads/Writes (fs_reads/writes + crresponding value parsed from /proc/diskstats) to the disk's fsstats file

        Args: value, 'R' or 'W' to indicate which field to update in the file

        Returns:
            N/A
        """
        filename = self.FSSTATS_FILE_PREFIX + "-" + self.diskdev
        fsstats = ""

        if not os.path.isfile(filename):
            if attr == 'R':
                fsstats = ("{} {}".format(value, self.fs_writes))
            elif attr == 'W':
                fsstats = ("{} {}".format(self.fs_reads, value))
        else:
            with open(filename) as f:
                fsstats = f.readline().strip()

            if attr == 'R':
                fsstats = "{} {}".format(value, fsstats.split()[1])
            elif attr == 'W':
                fsstats = "{} {}".format(fsstats.split()[0], value)

        with open(filename, 'w') as f:
            f.write(fsstats)

    def get_fs_io_reads(self):
        """
        Function to get the total number of reads on the disk by parsing the /proc/diskstats file

        Returns:
            The total number of disk reads

        Args:
            N/A
        """

        reads = 0

        if 'psutil' in sys.modules:
            reads = int(psutil.disk_io_counters(perdisk=True, nowrap=True)[self.diskdev].read_count)
        else:
            with open(self.DISKSTATS_FILE) as f:
                statsfile = f.readlines()
                for line in statsfile:
                    if self.diskdev == line.split()[2]:
                        reads = int(line.split()[3])
                        break

        total_reads = int(self.fs_reads) + reads
        self._update_fsstats_file(total_reads, 'R')

        return total_reads


    def get_fs_io_writes(self):
        """
        Function to get the total number of disk writes by parsing the /proc/diskstats file

        Returns:
            The total number of disk writes

        Args:
            N/A
        """

        writes = 0

        if 'psutil' in sys.modules:
            writes = psutil.disk_io_counters(perdisk=True, nowrap=True)[self.diskdev].write_count
        else:
            with open(self.DISKSTATS_FILE) as f:
                statsfile = f.readlines()
                for line in statsfile:
                    if self.diskdev == line.split()[2]:
                        writes = int(line.split()[7])
                        break

        total_writes = int(self.fs_writes) + writes
        self._update_fsstats_file(total_writes, 'W')

        return total_writes
