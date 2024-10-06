import os
import sys
from mock import patch, MagicMock
import pytest

mocked_basepath = ['loop1', 'mmcblk0', 'loop6', 'mmcblk0boot0', 'loop4', 'loop2', 'loop0', 'loop7', 'mmcblk0boot1', 'sda', 'loop5', 'loop3']
mocked_devices = { 'mmcblk0' : None, 'sda' : None}
mock_realpath = "/sys/devices/pci0000:00/0000:00:18.0/ata5/host4/target4:0:0/4:0:0:0"

tests_path = os.path.dirname(os.path.abspath(__file__))
# Add mocked_libs path so that the file under test
# can load mocked modules from there
mocked_libs_path = os.path.join(tests_path, "mocked_libs")  # noqa: E402,F401
sys.path.insert(0, mocked_libs_path)

from .mocked_libs.blkinfo import BlkDiskInfo  # noqa: E402,F401

from sonic_platform_base.sonic_storage.storage_devices import StorageDevices


class TestStorageDevices:

    @patch('os.listdir', MagicMock(return_value=['sdi']))
    @patch('os.path.realpath', MagicMock(return_value=mock_realpath))
    @patch('sonic_platform_base.sonic_storage.ssd.SsdUtil')
    def test_get_storage_devices_sda_obj(self, mock_ssdutil):

        mock_ssdutil = MagicMock()
        mock_ssdutil.return_value = MagicMock()

        storage = StorageDevices()

        assert (list(storage.devices.keys()) == ['sdi'])


    @patch('os.listdir', MagicMock(return_value=['sdj']))
    @patch('os.path.realpath', MagicMock(return_value="usb"))
    @patch('sonic_platform_base.sonic_storage.usb.UsbUtil', MagicMock())
    def test_get_storage_devices_usb_obj(self):

        storage = StorageDevices()

        assert (list(storage.devices.keys()) == ['sdj'])
        assert ("UsbUtil" in str(type(storage.devices['sdj'])))


    @patch('os.listdir', MagicMock(return_value=['mmcblk0']))
    @patch('sonic_platform_base.sonic_storage.emmc.EmmcUtil')
    def test_get_storage_devices_emmc_obj(self, mock_emmcutil):

        mock_emmcutil = MagicMock()
        mock_emmcutil.return_value = MagicMock()

        storage = StorageDevices()

        assert (list(storage.devices.keys()) == ['mmcblk0'])
        assert storage.devices['mmcblk0'] != None



    @patch('os.listdir', MagicMock(return_value=mocked_basepath))
    def test_get_storage_devices_none(self):
        
        def mock_factory(self, dummy_key):
            return None
        
        with patch.object(StorageDevices, '_storage_device_object_factory', new=mock_factory):
            storage = StorageDevices()
            assert storage.devices == mocked_devices


