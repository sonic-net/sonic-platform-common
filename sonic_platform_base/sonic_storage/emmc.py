#
# emmc.py
#
# Implementation of SSD Utility API for eMMC.
# It reads eMMC health, model, firmware, and serial from /sys/block/*.
#

try:
    import os
    from .storage_common import StorageCommon
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")


class EmmcUtil(StorageCommon):
    def __init__(self, diskdev):
        self.diskdev = diskdev
        self.path = os.path.join('/sys/block', os.path.basename(diskdev))
        StorageCommon.__init__(self, diskdev)

    def _read_device_entry(self, entry, default=None):
        path = os.path.join(self.path, 'device', entry)
        try:
            with open(path) as f:
                return f.read().rstrip()
        except OSError:
            return default

    def _is_slc(self):
        return bool(self._read_device_entry('enhanced_area_offset'))

    def get_health(self):
        data = self._read_device_entry('life_time')
        if data is None:
            raise NotImplementedError
        value = int(data.split()[0 if self._is_slc() else 1], 0)
        return float(100 - (10 * (value - 1)))

    def get_temperature(self):
        return 'N/A'

    def get_model(self):
        return self._read_device_entry('name')

    def get_firmware(self):
        return self._read_device_entry('fwrev')

    def get_serial(self):
        return self._read_device_entry('serial')

    def get_vendor_output(self):
        return ''

    def get_disk_io_reads(self):
        return 'N/A'

    def get_disk_io_writes(self):
        return 'N/A'

    def get_reserved_blocks(self):
        return 'N/A'

    def fetch_parse_info(self, diskdev=None):
        return