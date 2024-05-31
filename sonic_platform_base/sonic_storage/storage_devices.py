#
# storage_devices.py
#
# Composition class for the instantiation of objects of various storage device classes,
# i.e. SsdUtil, EmmcUtil
#


try:
    import os
    import sys
    from sonic_py_common import syslogger
    from sonic_platform_base.sonic_storage.ssd import SsdUtil
    from sonic_platform_base.sonic_storage.emmc import EmmcUtil
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

# Not currently supported
try:
    from sonic_platform_base.sonic_storage.usb import UsbUtil
except ImportError as e:
    pass

BASE_PATH = "/sys/block"
BLKDEV_BASE_PATH = "/dev"

class StorageDevices:
    def __init__(self):
        self.log_identifier = "StorageDevices"
        self.log = syslogger.SysLogger(self.log_identifier)
        self.devices = {}

        # Populate the self.devices dictionary with as many key-values pairs as storage disks,
        # where key is the name of the storage disk and temporary value is None.
        self._get_storage_devices()

    def _get_storage_devices(self):
        """
        Function to get a list of storage disks in the switch by populating the self.devices dictionary with storage disk identifiers found in the /sys/block directory.

        Args: N/A

        Returns: N/A

        """
        fdlist = os.listdir(BASE_PATH)
        for fd in fdlist:
            if 'boot' in fd or 'loop' in fd:
                continue
            else:
                # Populate value for each key in dictionary with corresponding storage class object
                self.devices[fd] = self._storage_device_object_factory(fd)

    def _storage_device_object_factory(self, key):
        """
        A function that returns instances of storage device utility classes
        based on the disk identifiers obtained in the _get_storage_devices

        Args: N/A

        Returns: N/A

        """

        blkdev = os.path.join(BLKDEV_BASE_PATH, key)
        diskdev = os.path.join(BASE_PATH, key)

        if key.startswith('sd'):
            path = os.path.join(diskdev, "device")
            if "ata" in os.path.realpath(path):
                try:
                    return SsdUtil(blkdev)
                except Exception as e:
                    self.log.log_warning("Failed to instantiate SsdUtil object. Error: {}".format(str(e)), True)

            elif "usb" in os.path.realpath(path):
                try:
                    return UsbUtil(blkdev)
                except Exception as e:
                    self.log.log_warning("Failed to instantiate UsbUtil object. Error: {}".format(str(e)), True)

        elif "mmcblk" in key:
            try:
                return EmmcUtil(key)
            except Exception as e:
                self.log.log_warning("Failed to instantiate EmmcUtil object. Error: {}".format(str(e)), True)

        return None
