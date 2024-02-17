#
# storage_devices.py
#
# Composition class for the instantiation of objects of various storage device classes,
# i.e. SsdUtil, EmmcUtil
#


try:
    import os
    import sys
    from sonic_py_common import logger
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

class StorageDevices():
    def __init__(self, log_identifier):
        self.devices = {}
        self.BASE_PATH = "/sys/block"
        self.BLKDEV_BASE_PATH = "/dev"
        self._get_storage_devices()
        self._get_storage_device_object()

    def _get_storage_devices(self):
        """
        Function to get a list of storage disks in the switch by populating the self.devices dictionary with storage disk identifiers found in the /sys/block directory.

        Args: N/A

        Returns: N/A

        """
        fdlist = os.listdir(self.BASE_PATH)
        for fd in fdlist:
            if 'boot' in fd or 'loop' in fd:
                continue
            else:
                self.devices[fd] = None

    def _get_storage_device_object(self):
        """
        A function that creates instances of storage device utility classes based on the disk identifiers obtained in the _get_storage_devices

        Args: N/A

        Returns: N/A

        """
        for key in self.devices:
            blkdev = os.path.join(self.BLKDEV_BASE_PATH, key)
            diskdev = os.path.join(self.BASE_PATH, key)
            if key.startswith('sd'):
                path = os.path.join(diskdev, "device")
                if "ata" in os.path.realpath(path):
                    try:
                        from sonic_platform_base.sonic_storage.ssd import SsdUtil
                        self.devices[key] = SsdUtil(blkdev)
                    except ImportError as e:
                        log.log_warning("Failed to import default SsdUtil. Error: {}".format(str(e)), True)
                elif "usb" in os.path.realpath(path):
                    try:
                        from sonic_platform_base.sonic_storage.usb import UsbUtil
                        self.devices[key] = UsbUtil(blkdev)
                    except ImportError as e:
                        log.log_warning("Failed to import default UsbUtil. Error: {}".format(str(e)), True)
            elif "mmcblk" in key:
                try:
                    from sonic_platform_base.sonic_storage.emmc import EmmcUtil
                    self.devices[key] = EmmcUtil(key)
                except ImportError as e:
                    log.log_warning("Failed to import default EmmcUtil. Error: {}".format(str(e)), True)
