from unittest.mock import MagicMock, call, patch

import pytest

from sonic_platform_base.sonic_xcvr.api.public.cdb_fw import CmisCdbFw
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_els import NvidiaCpoElsCmisApi
from sonic_platform_base.sonic_xcvr import cdb_firmware
from sonic_platform_base.sonic_xcvr.cdb_firmware import (
    CdbFirmwareMixin, FW_RUN_DELAY)
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoHardwareInfo, OeId
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpBase
from sonic_platform_base.sonic_xcvr.cpo.oe import OeBase
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom

FEATURE = (112, 2048, True, True)


class FakeDevice(CdbFirmwareMixin):
    def __init__(self, api):
        self.api = api
        self.refresh_api = MagicMock()

    def get_api(self):
        return self.api


@pytest.fixture(autouse=True)
def no_sleep():
    with patch.object(cdb_firmware.time, 'sleep') as sleep:
        yield sleep


@pytest.fixture
def api():
    api = MagicMock()
    api.cdb_fw_hdlr.get_fw_mgmt_features.return_value = FEATURE
    api.module_fw_start_download.return_value = (True, '')
    api.module_fw_write_blocks_iter.return_value = iter([2048, 2048, 100])
    api.module_fw_complete_download.return_value = (True, 'Module FW download complete: Success\n')
    api.module_fw_run.return_value = (True, 'Module FW run: Success\n')
    api.module_fw_commit.return_value = (True, 'Module FW commit: Success\n')
    api.get_module_fw_info.return_value = {'status': True, 'info': '', 'result': ()}
    api.xcvr_eeprom.read.side_effect = KeyError
    return api


class TestCdbFirmwareMixin(object):
    def test_download_yields_header_and_blocks(self, api):
        device = FakeDevice(api)

        assert list(device.download_firmware('/tmp/fw.bin')) == [112, 2048, 2048, 100]

        api.enable_cdb_fw_handler.assert_called_once_with()
        api.module_fw_start_download.assert_called_once_with('/tmp/fw.bin')
        api.module_fw_write_blocks_iter.assert_called_once_with('/tmp/fw.bin', 112, 2048, True)
        api.module_fw_complete_download.assert_called_once_with()
        api.module_fw_run.assert_not_called()
        api.module_fw_commit.assert_not_called()

    def test_download_without_header(self, api):
        api.cdb_fw_hdlr.get_fw_mgmt_features.return_value = (0, 2048, False, True)

        assert list(FakeDevice(api).download_firmware('/tmp/fw.bin')) == [2048, 2048, 100]
        api.module_fw_write_blocks_iter.assert_called_once_with('/tmp/fw.bin', 0, 2048, False)

    def test_download_is_lazy(self, api):
        device = FakeDevice(api)
        device.get_api = MagicMock(return_value=api)

        device.download_firmware('/tmp/fw.bin')

        device.get_api.assert_not_called()
        api.module_fw_start_download.assert_not_called()

    def test_download_feature_failure(self, api):
        api.cdb_fw_hdlr.get_fw_mgmt_features.return_value = None
        with pytest.raises(RuntimeError, match='firmware management features'):
            list(FakeDevice(api).download_firmware('/tmp/fw.bin'))
        api.module_fw_start_download.assert_not_called()

    def test_download_start_failure(self, api):
        api.module_fw_start_download.return_value = (False, 'Start module FW download: Fail\n')
        with pytest.raises(RuntimeError, match='Failed to start firmware download: Start module FW download: Fail'):
            list(FakeDevice(api).download_firmware('/tmp/fw.bin'))
        api.module_fw_write_blocks_iter.assert_not_called()

    def test_download_block_failure(self, api):
        def blocks(*args):
            yield 2048
            raise RuntimeError('CDB download failed. CDB Status: 69')

        api.module_fw_write_blocks_iter.side_effect = blocks
        written = []
        with pytest.raises(RuntimeError, match='CDB Status: 69'):
            for count in FakeDevice(api).download_firmware('/tmp/fw.bin'):
                written.append(count)
        assert written == [112, 2048]
        api.module_fw_complete_download.assert_not_called()
        # module_fw_write_blocks_iter() aborts a failed download itself.
        api.cdb_fw_hdlr.abort_fw_download.assert_not_called()

    @pytest.mark.parametrize("stop_after", [1, 2])
    def test_stopped_download_is_aborted(self, api, stop_after):
        blocks = FakeDevice(api).download_firmware('/tmp/fw.bin')
        for _ in range(stop_after):
            next(blocks)

        blocks.close()

        api.cdb_fw_hdlr.abort_fw_download.assert_called_once_with()
        api.module_fw_complete_download.assert_not_called()

    def test_interrupted_download_is_aborted(self, api):
        def blocks(*args):
            yield 2048
            raise KeyboardInterrupt

        api.module_fw_write_blocks_iter.side_effect = blocks
        with pytest.raises(KeyboardInterrupt):
            list(FakeDevice(api).download_firmware('/tmp/fw.bin'))
        api.cdb_fw_hdlr.abort_fw_download.assert_called_once_with()

    def test_abort_waits_for_the_pending_command(self, api):
        order = MagicMock()
        api.cdb_fw_hdlr.wait_for_cdb_status.side_effect = order.wait
        order.abort.return_value = True
        api.cdb_fw_hdlr.abort_fw_download.side_effect = order.abort
        blocks = FakeDevice(api).download_firmware('/tmp/fw.bin')
        next(blocks)

        blocks.close()

        assert order.mock_calls == [call.wait(), call.abort()]

    def test_no_abort_when_not_supported(self, api):
        api.cdb_fw_hdlr.get_fw_mgmt_features.return_value = (112, 2048, True, False)
        blocks = FakeDevice(api).download_firmware('/tmp/fw.bin')
        next(blocks)

        blocks.close()

        api.cdb_fw_hdlr.wait_for_cdb_status.assert_not_called()
        api.cdb_fw_hdlr.abort_fw_download.assert_not_called()

    def test_download_aborted_when_reading_the_image_fails(self, api):
        def blocks(*args):
            yield 2048
            raise OSError('read error')

        api.module_fw_write_blocks_iter.side_effect = blocks
        with pytest.raises(OSError, match='read error'):
            list(FakeDevice(api).download_firmware('/tmp/fw.bin'))
        api.cdb_fw_hdlr.abort_fw_download.assert_called_once_with()

    def test_rejected_abort_is_logged(self, api):
        api.cdb_fw_hdlr.abort_fw_download.return_value = None
        blocks = FakeDevice(api).download_firmware('/tmp/fw.bin')
        next(blocks)

        with patch.object(cdb_firmware, 'log') as log:
            blocks.close()
        log.log_error.assert_called_once_with('Failed to abort firmware download')

    def test_abort_failure_does_not_hide_the_interruption(self, api):
        api.cdb_fw_hdlr.abort_fw_download.side_effect = OSError('I2C error')
        blocks = FakeDevice(api).download_firmware('/tmp/fw.bin')
        next(blocks)

        with patch.object(cdb_firmware, 'log') as log:
            blocks.close()
        log.log_error.assert_called_once_with('Failed to abort firmware download: I2C error')

    def test_download_complete_failure(self, api):
        api.module_fw_complete_download.return_value = (False, 'Module FW download complete: Fail\n')
        with pytest.raises(RuntimeError, match='Failed to complete firmware download'):
            list(FakeDevice(api).download_firmware('/tmp/fw.bin'))

    @pytest.mark.parametrize("method, args, api_method, api_args", [
        ('run_firmware', (), 'module_fw_run', (0x01,)),
        ('run_firmware', (0x00,), 'module_fw_run', (0x00,)),
        ('commit_firmware', (), 'module_fw_commit', ()),
    ])
    def test_run_and_commit(self, api, method, args, api_method, api_args):
        assert getattr(FakeDevice(api), method)(*args) is True
        api.enable_cdb_fw_handler.assert_called_once_with()
        getattr(api, api_method).assert_called_once_with(*api_args)

    @pytest.mark.parametrize("method, api_method, message", [
        ('run_firmware', 'module_fw_run', 'Failed to run firmware: Module FW run: Fail'),
        ('commit_firmware', 'module_fw_commit', 'Failed to commit firmware: Module FW commit: Fail'),
    ])
    def test_run_and_commit_failure(self, api, method, api_method, message):
        getattr(api, api_method).return_value = (False, message.split(': ', 1)[1] + '\n')
        with pytest.raises(RuntimeError, match=message):
            getattr(FakeDevice(api), method)()

    def test_upgrade_downloads_runs_and_commits(self, no_sleep, api):
        order = MagicMock()
        order.complete.return_value = (True, '')
        order.run.return_value = (True, '')
        order.commit.return_value = (True, '')
        api.module_fw_complete_download.side_effect = order.complete
        api.module_fw_run.side_effect = order.run
        no_sleep.side_effect = order.sleep
        api.module_fw_commit.side_effect = order.commit

        assert list(FakeDevice(api).upgrade_firmware('/tmp/fw.bin')) == [112, 2048, 2048, 100]
        assert order.mock_calls == [call.complete(), call.run(0x01), call.sleep(FW_RUN_DELAY), call.commit()]

    def test_upgrade_stops_when_run_fails(self, no_sleep, api):
        api.module_fw_run.return_value = (False, 'Module FW run: Fail\n')
        with pytest.raises(RuntimeError, match='Failed to run firmware'):
            list(FakeDevice(api).upgrade_firmware('/tmp/fw.bin'))
        api.module_fw_commit.assert_not_called()
        no_sleep.assert_not_called()

    @pytest.mark.parametrize("operation", [
        lambda device: list(device.download_firmware('/tmp/fw.bin')),
        lambda device: list(device.upgrade_firmware('/tmp/fw.bin')),
        lambda device: device.run_firmware(),
        lambda device: device.commit_firmware(),
    ])
    def test_api_without_cdb_firmware_support(self, operation):
        with pytest.raises(NotImplementedError, match='device API does not support'):
            operation(FakeDevice(object()))

    @pytest.mark.parametrize("operation", [
        lambda device: list(device.download_firmware('/tmp/fw.bin')),
        lambda device: device.run_firmware(),
        lambda device: device.commit_firmware(),
    ])
    def test_device_without_cdb_support(self, api, operation):
        api.cdb_fw_hdlr = None
        with pytest.raises(NotImplementedError, match='device does not support'):
            operation(FakeDevice(api))
        api.module_fw_start_download.assert_not_called()
        api.module_fw_run.assert_not_called()
        api.module_fw_commit.assert_not_called()

    @pytest.mark.parametrize("device_class", [OeBase, ElsfpBase])
    def test_cpo_devices_use_their_own_api(self, api, device_class):
        device = device_class(CpoHardwareInfo(oe_id=OeId.BROADCOM_DAVISSON, elsfp_id=None))
        device.get_api = MagicMock(return_value=api)
        device.refresh_api = MagicMock()

        assert list(device.download_firmware('/tmp/fw.bin')) == [112, 2048, 2048, 100]
        assert device.run_firmware() is True
        assert device.commit_firmware() is True
        assert api.enable_cdb_fw_handler.call_count == 3

    def test_upgrade_commits_through_the_refreshed_api(self, no_sleep, api):
        new_api = MagicMock()
        new_api.module_fw_commit.return_value = (True, '')
        device = FakeDevice(api)
        device.get_api = MagicMock(side_effect=[api, new_api])

        list(device.upgrade_firmware('/tmp/fw.bin'))

        api.module_fw_commit.assert_not_called()
        new_api.module_fw_commit.assert_called_once_with()


class TestRunDelay(object):
    def test_run_waits_for_the_device_and_refreshes_the_api(self, api, no_sleep):
        order = MagicMock()
        order.run.return_value = (True, '')
        api.module_fw_run.side_effect = order.run
        no_sleep.side_effect = order.sleep
        device = FakeDevice(api)
        device.refresh_api.side_effect = order.refresh

        assert device.run_firmware() is True

        assert order.mock_calls == [call.run(0x01), call.sleep(FW_RUN_DELAY), call.refresh()]

    def test_no_wait_when_run_fails(self, api, no_sleep):
        api.module_fw_run.return_value = (False, 'Module FW run: Fail\n')
        device = FakeDevice(api)

        with pytest.raises(RuntimeError, match='Failed to run firmware'):
            device.run_firmware()
        no_sleep.assert_not_called()
        device.refresh_api.assert_not_called()


FW_INFO_TEXT = (
    'Image A Version: 1.2.0\n'
    'Image B Version: N/A\n'
    'Factory Image Version: 1.0.0\n'
    'Running Image: A\n'
    'Committed Image: A\n'
    'Active Firmware: 1.2.0\n'
    'Inactive Firmware: N/A\n'
)


class TestFirmwareInfo(object):
    def test_cdb_firmware_info(self, api):
        api.get_module_fw_info.return_value = {'status': True, 'info': FW_INFO_TEXT, 'result': ()}

        info = FakeDevice(api).get_firmware_info()

        assert list(info.items()) == [
            ('Image A Version', '1.2.0'),
            ('Image B Version', 'N/A'),
            ('Factory Image Version', '1.0.0'),
            ('Running Image', 'A'),
            ('Committed Image', 'A'),
            ('Active Firmware', '1.2.0'),
            ('Inactive Firmware', 'N/A'),
        ]
        api.enable_cdb_fw_handler.assert_called_once_with()

    def test_cdb_failure(self, api):
        api.get_module_fw_info.return_value = {'status': False, 'info': 'Failed to get firmware info', 'result': 0}
        with pytest.raises(RuntimeError, match='^Failed to get firmware info$'):
            FakeDevice(api).get_firmware_info()

    def test_eeprom_firmware_info_without_cdb(self, api):
        api.cdb_fw_hdlr = None
        versions = {
            consts.ACTIVE_FW_MAJOR_REV: 1, consts.ACTIVE_FW_MINOR_REV: 2,
            consts.INACTIVE_FW_MAJOR_REV: 1, consts.INACTIVE_FW_MINOR_REV: 1,
        }
        api.xcvr_eeprom.read.side_effect = versions.get

        assert FakeDevice(api).get_firmware_info() == {'Active Firmware': '1.2', 'Inactive Firmware': '1.1'}
        api.get_module_fw_info.assert_not_called()

    def test_eeprom_firmware_info_not_reported(self, api):
        api.cdb_fw_hdlr = None

        assert FakeDevice(api).get_firmware_info() == {'Active Firmware': 'N/A', 'Inactive Firmware': 'N/A'}

    def test_eeprom_firmware_info_on_api_without_cdb_firmware(self):
        api = MagicMock(spec=['xcvr_eeprom'])
        api.xcvr_eeprom.read.return_value = 3

        assert FakeDevice(api).get_firmware_info() == {'Active Firmware': '3.3', 'Inactive Firmware': '3.3'}

    def test_no_device_api(self):
        with pytest.raises(RuntimeError, match='The device API is not available'):
            FakeDevice(None).get_firmware_info()


class TestNoLock(object):
    def test_operations_take_no_lock(self, api):
        """The platform serializes the operations, if it needs to."""
        assert not hasattr(CdbFirmwareMixin, '_firmware_lock')
        assert not hasattr(CdbFirmwareMixin, 'FIRMWARE_LOCK_DIR')
        assert FakeDevice(api).commit_firmware() is True


class TestCdbFwHandlerEnable(object):
    @staticmethod
    def eeprom(cdb_support):
        reader = MagicMock(return_value=None)
        eeprom = XcvrEeprom(reader, MagicMock(), CmisMemMap(CmisCodes))
        eeprom.read = MagicMock(side_effect=lambda field: cdb_support if field == consts.CDB_SUPPORT else None)
        return eeprom

    @patch('sonic_platform_base.sonic_xcvr.api.public.cdb_fw.CdbFw')
    def test_enable_on_api_built_without_handler(self, mock_cdb_fw):
        api = CmisApi(self.eeprom(1), init_cdb_fw_handler=False)
        api.is_flat_memory = MagicMock(return_value=False)
        assert api.cdb_fw_hdlr is None

        api.enable_cdb_fw_handler()

        assert api.cdb_fw_hdlr is mock_cdb_fw.return_value
        mock_cdb_fw.assert_called_once_with(api.xcvr_eeprom.reader, api.xcvr_eeprom.writer, api._cdb_mem_map)

    @patch('sonic_platform_base.sonic_xcvr.api.public.cdb_fw.CdbFw')
    def test_enable_keeps_the_handler_off_without_cdb_support(self, mock_cdb_fw):
        api = CmisApi(self.eeprom(0))
        api.is_flat_memory = MagicMock(return_value=False)

        api.enable_cdb_fw_handler()

        assert api.cdb_fw_hdlr is None
        mock_cdb_fw.assert_not_called()

    @pytest.mark.parametrize("cdb_support", [0, 1, 2])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cdb_fw.CdbFw')
    def test_els_api_supports_cdb_firmware(self, mock_cdb_fw, cdb_support):
        api = NvidiaCpoElsCmisApi(self.eeprom(cdb_support))
        api._select_cdb_target = MagicMock(return_value=True)
        assert isinstance(api, CmisCdbFw)

        api.enable_cdb_fw_handler()

        # The ELSFP is driven over CDB whatever it advertises (is_cdb_supported).
        assert api.cdb_fw_hdlr._handler is mock_cdb_fw.return_value
