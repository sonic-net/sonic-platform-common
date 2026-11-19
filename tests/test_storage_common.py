import os
import sys
import types
from mock import MagicMock, mock_open, patch
#import psutil

from sonic_platform_base.sonic_storage.storage_common import StorageCommon

class DiskIOCounters():
    def __init__(self, perdisk=True, nowrap=True):

        self.read_count =  18038
        self.write_count = 95836

class TestStorageCommon:
    
    @patch('psutil.disk_io_counters', MagicMock(return_value={'sda': DiskIOCounters()}))
    def test_get_reads_writes(self):

        common_object = StorageCommon('/dev/sda')

        reads = common_object.get_fs_io_reads()
        writes = common_object.get_fs_io_writes()

        assert (reads == 18038)
        assert (writes == 95836)

    
    def test_init(self):
        common_object = StorageCommon('/dev/sda')

        assert common_object.storage_disk == 'sda'


    def test_get_reads_writes_bad_disk(self):
        common_object = StorageCommon('/dev/glorp')

        with patch('psutil.disk_io_counters', MagicMock()) as mock_psutil_output:

            class DiskIOCounters():
                def __init__(self, perdisk=True, nowrap=True):
                    pass

            mock_psutil_output.return_value = {'glorp': DiskIOCounters()}
            reads = common_object.get_fs_io_reads()
            writes = common_object.get_fs_io_writes()

            assert (reads == 0)
            assert (writes == 0)

    def test_unmount(self):
        mounts = '/dev/sda1 /host ext4 rw 0 0\n/dev/sda /host/deep ext4 rw 0 0\n'
        common_object = StorageCommon('/dev/sda')
        libc = MagicMock()
        libc.umount2.return_value = 0

        with patch('builtins.open', mock_open(read_data=mounts)), patch(
                'os.listdir', return_value=['sda', 'sda1']
        ), patch('os.path.realpath', side_effect=lambda path: {
            '/sys/class/block/sda': '/sys/devices/block/sda',
            '/sys/class/block/sda1': '/sys/devices/block/sda/sda1',
        }.get(path, path)), patch('os.sync') as sync, patch(
                'sonic_platform_base.sonic_storage.storage_common.ctypes.CDLL',
                return_value=libc):
            assert common_object._unmount() is True

        sync.assert_called_once_with()
        assert libc.umount2.call_count == 2
        assert libc.umount2.call_args_list[0].args[0].value == b'/host/deep'
        assert libc.umount2.call_args_list[1].args[0].value == b'/host'

    def test_zero_write(self):
        common_object = StorageCommon('/dev/sda')
        with patch(
            'sonic_platform_base.sonic_storage.storage_common.subprocess.check_call'
        ) as check_call:
            common_object._zero_write()

        check_call.assert_called_once_with([
            'dd', 'if=/dev/zero', 'of=/dev/sda', 'bs=1M', 'status=progress'
        ])

    def test_verify_zeroed(self):
        common_object = StorageCommon('/dev/nvme0n1')
        with patch(
            'sonic_platform_base.sonic_storage.storage_common.subprocess.check_output',
            return_value='4096\n'
        ), patch(
            'sonic_platform_base.sonic_storage.storage_common.subprocess.check_call'
        ) as check_call:
            assert common_object._verify_zeroed() is True

        check_call.assert_called_once_with([
            'cmp', '-n', '4096', '/dev/zero', '/dev/nvme0n1'
        ])

