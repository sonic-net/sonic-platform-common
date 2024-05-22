import os
import sys
import types
from mock import MagicMock, patch
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

