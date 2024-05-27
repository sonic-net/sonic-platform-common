import sys
import mock

from sonic_platform_base.sonic_storage.emmc import EmmcUtil

mocked_files = {
    '/sys/block/emmctest/device/enhanced_area_offset': '0',
    '/sys/block/emmctest/device/life_time': '0x02 0x02',
    '/sys/block/emmctest/device/name': 'Test eMMC device',
    '/sys/block/emmctest/device/fwrev': '0xAA00000000000000',
    '/sys/block/emmctest/device/serial': '0xabcdefef',
    '/proc/mounts' : '/dev/emmctestp1 /host ext4 rw,relatime 0 0'
}


def build_mocked_sys_fs_open(files):
    mocks = dict([(fname, mock.mock_open(read_data=cnt).return_value)
                 for fname, cnt in files.items()])

    def mopen(fname):
        if fname in mocks:
            return mocks[fname]
        else:
            raise FileNotFoundError(fname)
    return mopen


class TestEMMC:

    @mock.patch('builtins.open', new=build_mocked_sys_fs_open(mocked_files))

    def test_check(self, *args):
        util = EmmcUtil('emmctest')

        assert (util.get_health() == 90.0)
        assert (util.get_temperature() == 'N/A')
        assert (util.get_model() == 'Test eMMC device')
        assert (util.get_firmware() == '0xAA00000000000000')
        assert (util.get_serial() == '0xabcdefef')
        assert (util.get_disk_io_reads() == 'N/A')
        assert (util.get_disk_io_writes() == 'N/A')
        assert (util.get_reserved_blocks() == 'N/A')
        assert (util.fetch_parse_info() == None)

