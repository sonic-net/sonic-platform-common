import sys
from unittest import mock
from pytest import raises

from sonic_platform_base.sonic_storage.storage_devices import StorageDevices

log_identifier = "test_storage_devices"

mocked_basepath = ['loop1', 'mmcblk0', 'loop6', 'mmcblk0boot0', 'loop4', 'loop2', 'loop0', 'loop7', 'mmcblk0boot1', 'sda', 'loop5', 'loop3']
mocked_devices = { 'mmcblk0' : None, 'sda' : None}


class TestStorageDevices:

    @mock.patch('os.listdir', mock.MagicMock(return_value=mocked_basepath))
    def test_get_storage_devices_none(self):
        
        def mock_factory(self, dummy_key):
            return None
        
        with mock.patch.object(StorageDevices, '_storage_device_object_factory', new=mock_factory):
            storage = StorageDevices(log_identifier)
            assert storage.devices == mocked_devices


    @mock.patch('os.listdir', mock.MagicMock(return_value=mocked_basepath))
    @mock.patch('sonic_platform_base.sonic_storage.emmc')
    @mock.patch('sonic_platform_base.sonic_storage.ssd')
    def test_get_storage_devices_mockobjs(self, mock_emmc, mock_ssd):
        
        mock_emmc = mock.MagicMock()
        mock_ssd = mock.MagicMock()
        
        def mock_factory(self, dummy_key):
            if dummy_key == "mmcblk0": return mock_emmc
            else: return mock_ssd
        
        with mock.patch.object(StorageDevices, '_storage_device_object_factory', new=mock_factory):
            storage = StorageDevices(log_identifier)

            assert (list(storage.devices.keys()) == ['mmcblk0', 'sda'])
            assert isinstance(storage.devices['mmcblk0'], mock.MagicMock)
            assert isinstance(storage.devices['sda'], mock.MagicMock)
            assert (storage.devices['mmcblk0'] == mock_emmc)
            assert (storage.devices['sda'] == mock_ssd)

