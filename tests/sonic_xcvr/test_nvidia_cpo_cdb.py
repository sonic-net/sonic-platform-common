"""Tests for the NVIDIA CPO CDB target selection and CDB lock."""
import contextlib
import fcntl
import os
import threading
from unittest.mock import MagicMock, patch

import pytest

from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_cdb import (
    CDB_TARGET_ELS,
    CDB_TARGET_OE,
    CDB_TARGET_SELECT_OFFSET,
    CdbLock,
    CdbTargetHandler,
    get_module_cdb_lock,
)
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_els import NvidiaCpoElsCmisApi
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_oe import NvidiaCpoOeCmisApi
from sonic_platform_base.sonic_xcvr.cdb.cdb import CdbCmdHandler


class FakeEeprom(object):
    """A byte-addressed EEPROM that records the accesses to the target select byte."""

    def __init__(self, control):
        self.control = control
        self.accesses = []
        self.fail = False

    def reader(self, offset, num_bytes):
        assert (offset, num_bytes) == (CDB_TARGET_SELECT_OFFSET, 1)
        self.accesses.append('read')
        return None if self.fail else bytearray([self.control])

    def writer(self, offset, num_bytes, write_buffer):
        assert (offset, num_bytes) == (CDB_TARGET_SELECT_OFFSET, 1)
        self.accesses.append(('write', write_buffer[0]))
        if self.fail:
            return False
        self.control = write_buffer[0]
        return True


def make_api(api_class, control):
    api = api_class.__new__(api_class)
    eeprom = FakeEeprom(control)
    api.xcvr_eeprom = MagicMock(reader=eeprom.reader, writer=eeprom.writer)
    return api, eeprom


API_TARGETS = [(NvidiaCpoOeCmisApi, CDB_TARGET_OE), (NvidiaCpoElsCmisApi, CDB_TARGET_ELS)]


class TestSelectCdbTarget(object):
    @pytest.mark.parametrize("api_class, target", API_TARGETS)
    def test_selects_target_and_keeps_other_controls(self, api_class, target):
        # Bit 4 stands for the other Module Global Controls.
        api, eeprom = make_api(api_class, 0x10 | (1 - target))

        assert api._select_cdb_target() is True

        assert eeprom.accesses == ['read', ('write', 0x10 | target)]

    @pytest.mark.parametrize("api_class, target", API_TARGETS)
    def test_selected_target_is_not_rewritten(self, api_class, target):
        api, eeprom = make_api(api_class, 0x10 | target)

        assert api._select_cdb_target() is True

        assert eeprom.accesses == ['read']

    @pytest.mark.parametrize("api_class, target", API_TARGETS)
    def test_read_failure(self, api_class, target):
        api, eeprom = make_api(api_class, 1 - target)
        eeprom.fail = True

        assert api._select_cdb_target() is False
        assert eeprom.accesses == ['read']

    @pytest.mark.parametrize("api_class, target", API_TARGETS)
    def test_write_failure(self, api_class, target):
        api, eeprom = make_api(api_class, 1 - target)
        eeprom.reader = MagicMock(return_value=bytearray([1 - target]))
        api.xcvr_eeprom.reader = eeprom.reader
        eeprom.fail = True

        assert api._select_cdb_target() is False


class TestCdbTargetHandler(object):
    def test_selects_target_before_each_method(self):
        order = MagicMock()
        order.select.return_value = True
        order.send_cmd.return_value = True
        handler = CdbTargetHandler(order, order.select)

        assert handler.send_cmd(0x9018, payload={'a': 1}) is True
        handler.read_reply(0x9018)

        assert order.mock_calls == [
            ('select', (), {}),
            ('send_cmd', (0x9018,), {'payload': {'a': 1}}),
            ('select', (), {}),
            ('read_reply', (0x9018,), {}),
        ]

    def test_cached_method_still_selects_target(self):
        select = MagicMock(return_value=True)
        handler = CdbTargetHandler(MagicMock(), select)

        handler.send_cmd(0x9018)
        handler.send_cmd(0x9018)

        assert select.call_count == 2

    def test_method_fails_when_target_cannot_be_selected(self):
        inner = MagicMock()
        handler = CdbTargetHandler(inner, lambda: False)

        with pytest.raises(RuntimeError, match='Failed to select the CDB target'):
            handler.send_cmd(0x9018)
        inner.send_cmd.assert_not_called()

    def test_attributes_pass_through(self):
        inner = MagicMock(start_LPL_size=112)
        select = MagicMock()
        handler = CdbTargetHandler(inner, select)

        assert handler.start_LPL_size == 112
        select.assert_not_called()

    def test_internal_calls_select_once(self):
        select = MagicMock(return_value=True)
        inner = CdbCmdHandler(MagicMock(), MagicMock(), MagicMock())
        inner.send_cmd = MagicMock(return_value=True)

        CdbTargetHandler(inner, select).write_lpl_block(0, b'\x00')

        select.assert_called_once_with()
        inner.send_cmd.assert_called_once()


def recording_lock(events):
    """A CDB lock that records when it is taken and released."""
    @contextlib.contextmanager
    def lock():
        events.append('lock')
        try:
            yield
        finally:
            events.append('unlock')
    return lock


class FakeDevice(object):
    """The platform device whose read_eeprom the API reads through."""

    def __init__(self, lock_dir, sdk_index):
        self.CDB_LOCK_DIR = lock_dir
        self.sdk_index = sdk_index

    def read_eeprom(self, offset, num_bytes):
        return bytearray(num_bytes)

    def write_eeprom(self, offset, num_bytes, write_buffer):
        return True


def api_on_device(api_class, lock_dir, sdk_index):
    api = api_class.__new__(api_class)
    device = FakeDevice(lock_dir, sdk_index)
    api.xcvr_eeprom = MagicMock(reader=device.read_eeprom, writer=device.write_eeprom)
    return api


def is_free(path):
    """Whether another process could take the lock file now."""
    fd = os.open(path, os.O_RDWR | os.O_CREAT)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False
    finally:
        os.close(fd)


class TestCdbLock(object):
    def test_the_oe_and_the_els_of_a_module_share_its_lock(self, tmp_path):
        oe = api_on_device(NvidiaCpoOeCmisApi, str(tmp_path), 4)
        els = api_on_device(NvidiaCpoElsCmisApi, str(tmp_path), 4)
        other = api_on_device(NvidiaCpoElsCmisApi, str(tmp_path), 5)

        assert oe.cdb_lock() is els.cdb_lock()
        assert other.cdb_lock() is not oe.cdb_lock()

    def test_the_lock_is_reentrant_and_held_against_other_processes(self, tmp_path):
        oe = api_on_device(NvidiaCpoOeCmisApi, str(tmp_path), 4)
        els = api_on_device(NvidiaCpoElsCmisApi, str(tmp_path), 4)
        path = str(tmp_path / 'cdb4.lock')

        with oe.cdb_lock():
            with els.cdb_lock():
                assert not is_free(path)
            assert not is_free(path)
            assert is_free(str(tmp_path / 'cdb5.lock'))
        assert is_free(path)

    def test_the_lock_waits_for_another_process(self, tmp_path):
        els = api_on_device(NvidiaCpoElsCmisApi, str(tmp_path), 6)
        fd = os.open(str(tmp_path / 'cdb6.lock'), os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        taken = threading.Event()

        def take():
            with els.cdb_lock():
                taken.set()

        thread = threading.Thread(target=take)
        thread.start()
        try:
            assert not taken.wait(0.2)
        finally:
            os.close(fd)
        thread.join(5)
        assert taken.is_set()

    def test_the_lock_waits_for_another_thread(self, tmp_path):
        els = api_on_device(NvidiaCpoElsCmisApi, str(tmp_path), 7)
        taken = threading.Event()

        def take():
            with els.cdb_lock():
                taken.set()

        with els.cdb_lock():
            thread = threading.Thread(target=take)
            thread.start()
            assert not taken.wait(0.2)
        thread.join(5)
        assert taken.is_set()

    def test_the_lock_is_released_on_error(self, tmp_path):
        els = api_on_device(NvidiaCpoElsCmisApi, str(tmp_path), 8)

        with pytest.raises(OSError):
            with els.cdb_lock():
                raise OSError

        assert is_free(str(tmp_path / 'cdb8.lock'))

    @pytest.mark.parametrize("lock_dir, sdk_index", [(None, 0), ('/tmp', None)])
    def test_no_lock_without_a_lock_dir_and_a_module(self, lock_dir, sdk_index):
        lock = get_module_cdb_lock(FakeDevice(lock_dir, sdk_index))
        assert not isinstance(lock, CdbLock)
        assert not isinstance(api_on_device(NvidiaCpoElsCmisApi, lock_dir, sdk_index).cdb_lock(), CdbLock)
        with lock:
            with lock.hold(0):
                pass

    def test_the_device_and_its_api_get_the_same_lock(self, tmp_path):
        device = FakeDevice(str(tmp_path), 4)
        api = api_on_device(NvidiaCpoElsCmisApi, str(tmp_path), 4)

        assert get_module_cdb_lock(device) is api.cdb_lock()

    def test_no_lock_on_a_reader_of_no_device(self):
        api, _ = make_api(NvidiaCpoElsCmisApi, 0)
        assert not isinstance(api.cdb_lock(), CdbLock)

    def test_hold_fails_after_the_timeout_while_another_process_holds_it(self, tmp_path):
        lock = get_module_cdb_lock(FakeDevice(str(tmp_path), 10))
        fd = os.open(str(tmp_path / 'cdb10.lock'), os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            with pytest.raises(RuntimeError, match='another firmware operation is in progress'):
                with lock.hold(0.2):
                    pass
        finally:
            os.close(fd)
        # A failed hold leaves the lock usable by this process.
        with lock.hold(0):
            assert not is_free(str(tmp_path / 'cdb10.lock'))
        assert is_free(str(tmp_path / 'cdb10.lock'))

    def test_hold_fails_after_the_timeout_while_another_thread_holds_it(self, tmp_path):
        lock = get_module_cdb_lock(FakeDevice(str(tmp_path), 11))
        taken, release = threading.Event(), threading.Event()

        def hold_it():
            with lock:
                taken.set()
                release.wait(5)

        thread = threading.Thread(target=hold_it)
        thread.start()
        taken.wait(5)
        try:
            with pytest.raises(RuntimeError):
                with lock.hold(0.2):
                    pass
        finally:
            release.set()
            thread.join(5)

    def test_hold_waits_for_a_single_command_of_another_process(self, tmp_path):
        lock = get_module_cdb_lock(FakeDevice(str(tmp_path), 12))
        fd = os.open(str(tmp_path / 'cdb12.lock'), os.O_RDWR | os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        timer = threading.Timer(0.2, os.close, (fd,))
        timer.start()
        with lock.hold(5):
            assert not is_free(str(tmp_path / 'cdb12.lock'))
        timer.join()

    def test_commands_reenter_a_held_lock(self, tmp_path):
        device = FakeDevice(str(tmp_path), 13)
        api = api_on_device(NvidiaCpoElsCmisApi, str(tmp_path), 13)
        with get_module_cdb_lock(device).hold(0):
            with api.cdb_lock():
                with get_module_cdb_lock(device).hold(0):
                    pass
            assert not is_free(str(tmp_path / 'cdb13.lock'))
        assert is_free(str(tmp_path / 'cdb13.lock'))

    def test_target_and_method_hold_the_lock_together(self):
        events = []
        inner = MagicMock()
        inner.send_cmd.side_effect = lambda *args: events.append('send') or True
        handler = CdbTargetHandler(inner, lambda: events.append('select') or True, recording_lock(events))

        assert handler.send_cmd(0x9018) is True

        assert events == ['lock', 'select', 'send', 'unlock']

    @pytest.mark.parametrize("api_class, target", API_TARGETS)
    def test_vendor_cdb_handler_holds_the_lock(self, api_class, target):
        api, eeprom = make_api(api_class, 1 - target)
        api.cdb_lock = recording_lock(eeprom.accesses)
        api._init_vendor_cdb_mem_map(MagicMock())
        with patch('sonic_platform_base.sonic_xcvr.api.cdb_capable_mixin.CdbCmdHandler') as mock_handler:
            mock_handler.return_value.send_cmd.side_effect = lambda *args: eeprom.accesses.append('send')
            api.cdb_handler.send_cmd(0x9030)

        assert eeprom.accesses == ['lock', 'read', ('write', target), 'send', 'unlock']

    @pytest.mark.parametrize("api_class, target", API_TARGETS)
    @patch('sonic_platform_base.sonic_xcvr.api.public.cdb_fw.CdbFw')
    def test_firmware_handler_is_created_under_the_lock(self, mock_cdb_fw, api_class, target):
        api, eeprom = make_api(api_class, 1 - target)
        api.cdb_lock = recording_lock(eeprom.accesses)
        api.is_cdb_supported = MagicMock(return_value=True)
        api.enable_cdb_fw_handler()
        mock_cdb_fw.side_effect = lambda *args: eeprom.accesses.append('create') or MagicMock()

        handler = api.cdb_fw_hdlr
        assert eeprom.accesses == ['lock', 'read', ('write', target), 'create', 'unlock']

        # The firmware commands hold it too.
        del eeprom.accesses[:]
        handler.run_fw_image(0x01)
        assert eeprom.accesses == ['lock', 'read', 'unlock']


class TestApiHandlers(object):
    @pytest.mark.parametrize("api_class, target", API_TARGETS)
    def test_vendor_cdb_handler_selects_target(self, api_class, target):
        api, eeprom = make_api(api_class, 1 - target)
        api._init_vendor_cdb_mem_map(MagicMock())
        with patch('sonic_platform_base.sonic_xcvr.api.cdb_capable_mixin.CdbCmdHandler') as mock_handler:
            handler = api.cdb_handler
            assert eeprom.accesses == []
            handler.send_cmd(0x9018)

        assert eeprom.accesses == ['read', ('write', target)]
        mock_handler.return_value.send_cmd.assert_called_once_with(0x9018)

    @pytest.mark.parametrize("api_class", [NvidiaCpoOeCmisApi, NvidiaCpoElsCmisApi])
    def test_no_vendor_cdb_handler(self, api_class):
        api, _ = make_api(api_class, 0)
        api._init_vendor_cdb_mem_map(None)

        assert api.cdb_handler is None

    @pytest.mark.parametrize("api_class, target", API_TARGETS)
    @patch('sonic_platform_base.sonic_xcvr.api.public.cdb_fw.CdbFw')
    def test_firmware_handler_selects_target(self, mock_cdb_fw, api_class, target):
        api, eeprom = make_api(api_class, 1 - target)
        api.is_cdb_supported = MagicMock(return_value=True)
        api.enable_cdb_fw_handler()

        # Creating the handler sends CDB commands, so the target is selected first.
        mock_cdb_fw.side_effect = lambda *args: eeprom.accesses.append('create') or MagicMock()
        handler = api.cdb_fw_hdlr
        assert eeprom.accesses == ['read', ('write', target), 'create']

        eeprom.control = 1 - target
        handler.run_fw_image(0x01)
        assert eeprom.accesses[3:] == ['read', ('write', target)]
        assert api.cdb_fw_hdlr is handler

    @pytest.mark.parametrize("api_class, target", API_TARGETS)
    @patch('sonic_platform_base.sonic_xcvr.api.public.cdb_fw.CdbFw')
    def test_firmware_handler_not_created_without_target(self, mock_cdb_fw, api_class, target):
        api, eeprom = make_api(api_class, 1 - target)
        api.is_cdb_supported = MagicMock(return_value=True)
        api.enable_cdb_fw_handler()
        eeprom.fail = True

        assert api.cdb_fw_hdlr is None
        mock_cdb_fw.assert_not_called()

        # The failure is not permanent: the handler is created once the target is selected.
        eeprom.fail = False
        assert isinstance(api.cdb_fw_hdlr, CdbTargetHandler)

    @pytest.mark.parametrize("api_class", [NvidiaCpoOeCmisApi, NvidiaCpoElsCmisApi])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cdb_fw.CdbFw')
    def test_no_firmware_handler_without_cdb_support(self, mock_cdb_fw, api_class):
        api, _ = make_api(api_class, 0)
        api.is_cdb_supported = MagicMock(return_value=False)
        api.enable_cdb_fw_handler()

        assert api.cdb_fw_hdlr is None
        mock_cdb_fw.assert_not_called()
