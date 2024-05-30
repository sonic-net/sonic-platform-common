#
# storage_common.py
#
# Class for common implementation functions,
# i.e. functions that are storage device type agnostic.
#

try:
    import os
    import sys
    import psutil
    from sonic_py_common import syslogger
    from .storage_base import StorageBase
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

class StorageCommon(StorageBase, object):
    def __init__(self, diskdev):
        """
        Constructor

        Args:
            Block device path for which we need to get information
        """
        self.log_identifier = "StorageCommon"
        self.log = syslogger.SysLogger(self.log_identifier)

        self.storage_disk = os.path.basename(diskdev)

    def get_fs_io_reads(self):
        """
        Function to get the latest reads on the disk by parsing the /proc/diskstats file

        Returns:
            The total number of procfs reads

        Args:
            N/A
        """

        fsstats_reads = 0
        try:
            fsstats_reads = int(psutil.disk_io_counters(perdisk=True, nowrap=True)[self.storage_disk].read_count)
        except Exception as ex:
            self.log.log_warning("get_fs_io_reads exception: {}".format(ex))
            pass

        return fsstats_reads

    def get_fs_io_writes(self):
        """
        Function to get the latest disk writes by parsing the /proc/diskstats file

        Returns:
            The total number of procfs writes

        Args:
            N/A
        """

        fsstats_writes = 0
        try:
            fsstats_writes = psutil.disk_io_counters(perdisk=True, nowrap=True)[self.storage_disk].write_count
        except Exception as ex:
            self.log.log_warning("get_fs_io_writes exception: {}".format(ex))
            pass

        return fsstats_writes
