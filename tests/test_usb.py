import os
import sys
from mock import patch, MagicMock

tests_path = os.path.dirname(os.path.abspath(__file__))
# Add mocked_libs path so that the file under test
# can load mocked modules from there
mocked_libs_path = os.path.join(tests_path, "mocked_libs")  # noqa: E402,F401
sys.path.insert(0, mocked_libs_path)

from .mocked_libs.blkinfo import BlkDiskInfo  # noqa: E402,F401
from sonic_platform_base.sonic_storage import usb

class TestUsb:

    def test_eusb_disk(self):

        usb_disk = usb.UsbUtil("sdx")

        assert usb_disk.get_model() == "SMART EUSB"
        assert usb_disk.get_serial() == "SPG200807J1"
        assert usb_disk.get_vendor_output() == "SMART EUSB"
        assert usb_disk.get_firmware() == "N/A"
        assert usb_disk.get_temperature() == "N/A"
        assert usb_disk.get_health() == "N/A"
        assert usb_disk.get_disk_io_reads() == "N/A"
        assert usb_disk.get_disk_io_writes() == "N/A"
        assert usb_disk.get_reserved_blocks() == "N/A"

