import sys
from mock import patch, MagicMock
from pytest import raises

from sonic_platform_base.sonic_storage.storage_devices import StorageDevices

log_identifier = "test_storage_devices"

mocked_basepath = ['loop1', 'mmcblk0', 'loop6', 'mmcblk0boot0', 'loop4', 'loop2', 'loop0', 'loop7', 'mmcblk0boot1', 'sda', 'loop5', 'loop3']
mocked_devices = { 'mmcblk0' : None, 'sda' : None}
mock_realpath = "/sys/devices/pci0000:00/0000:00:18.0/ata5/host4/target4:0:0/4:0:0:0"


class TestStorageDevices:

    @patch('os.listdir', MagicMock(return_value=['mmcblk0']))
    @patch('sonic_platform_base.sonic_storage.emmc.EmmcUtil')
    def test_get_storage_devices_emmc_obj(self, mock_emmc):

        with patch('sonic_platform_base.sonic_storage.emmc.EmmcUtil') as mock_emmc:
            mock_emmc_obj = MagicMock()
            mock_emmc.return_value = mock_emmc_obj

            storage = StorageDevices(log_identifier)

            assert (list(storage.devices.keys()) == ['mmcblk0'])
            assert (storage.devices['mmcblk0'] != None)



    @patch('os.listdir', MagicMock(return_value=mocked_basepath))
    def test_get_storage_devices_none(self):
        
        def mock_factory(self, dummy_key):
            return None
        
        with patch.object(StorageDevices, '_storage_device_object_factory', new=mock_factory):
            storage = StorageDevices(log_identifier)
            assert storage.devices == mocked_devices


