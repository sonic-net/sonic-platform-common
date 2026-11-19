#
# storage_common.py
#
# Class for common implementation functions,
# i.e. functions that are storage device type agnostic.
#

try:
    import ctypes
    import os
    import subprocess
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
        self.device_name = (
            diskdev if os.path.isabs(diskdev)
            else os.path.join("/dev", self.storage_disk)
        )

    def _unmount(self):
        """Unmount this device and all of its mounted partitions."""
        try:
            sysfs_device = os.path.realpath(
                os.path.join("/sys/class/block", self.storage_disk)
            )
            device_paths = {self.device_name}
            for block_device in os.listdir("/sys/class/block"):
                sysfs_candidate = os.path.realpath(
                    os.path.join("/sys/class/block", block_device)
                )
                if (sysfs_candidate == sysfs_device or
                        sysfs_candidate.startswith(sysfs_device + os.sep)):
                    device_paths.add(os.path.join("/dev", block_device))
            real_device_paths = set(os.path.realpath(path) for path in device_paths)
            mountpoints = []
            with open("/proc/self/mounts") as mounts:
                for line in mounts:
                    fields = line.split()
                    if len(fields) < 2:
                        continue
                    source = fields[0].replace("\\040", " ")
                    target = fields[1].replace("\\040", " ")
                    if source in device_paths or os.path.realpath(source) in real_device_paths:
                        mountpoints.append(target)

            os.sync()
            libc = ctypes.CDLL(None, use_errno=True)
            for mountpoint in sorted(
                    set(mountpoints), key=lambda path: path.count("/"), reverse=True):
                result = libc.umount2(
                    ctypes.c_char_p(os.fsencode(mountpoint)),
                    ctypes.c_int(0),
                )
                if result != 0:
                    error_number = ctypes.get_errno()
                    raise OSError(
                        error_number, os.strerror(error_number), mountpoint
                    )
            return True
        except (OSError, subprocess.CalledProcessError) as error:
            self.log.log_warning(
                "Failed to unmount {}: {}".format(self.device_name, error)
            )
            return False

    def _zero_write(self):
        """Write zeroes over the complete block device."""
        subprocess.check_call([
            "dd",
            "if=/dev/zero",
            "of={}".format(self.device_name),
            "bs=1M",
            "status=progress",
        ])

    def _verify_zeroed(self):
        """Return True only when every byte on the device is zero."""
        try:
            size = subprocess.check_output(
                ["blockdev", "--getsize64", self.device_name],
                universal_newlines=True
            ).strip()
            if not size or int(size) < 0:
                return False
            subprocess.check_call([
                "cmp", "-n", size, "/dev/zero", self.device_name
            ])
            return True
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            self.log.log_warning(
                "Failed to verify {}: {}".format(self.device_name, error)
            )
            return False

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
