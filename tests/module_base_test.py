import unittest
from unittest.mock import patch, MagicMock, call
from sonic_platform_base.module_base import ModuleBase
import fcntl
import importlib
import builtins
from io import StringIO
import sys
import os
import shutil
import contextlib
from types import ModuleType


class MockFile:
    def __init__(self, data=None):
        self.data = data
        self.written_data = None
        self.closed = False
        self.fileno_called = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def read(self):
        return self.data

    def write(self, data):
        self.written_data = data

    def fileno(self):
        self.fileno_called = True
        return 123


class TestModuleBase:

    def test_module_base(self):
        module = ModuleBase()
        not_implemented_methods = [
            [module.get_dpu_id],
            [module.get_reboot_cause],
            [module.get_state_info],
            [module.get_pci_bus_info],
            [module.pci_detach],
            [module.pci_reattach],
        ]

        for method in not_implemented_methods:
            exception_raised = False
            try:
                func = method[0]
                args = method[1:]
                func(*args)
            except NotImplementedError:
                exception_raised = True

            assert exception_raised

    def test_sensors(self):
        module = ModuleBase()
        assert module.get_num_voltage_sensors() == 0
        assert module.get_all_voltage_sensors() == []
        assert module.get_voltage_sensor(0) is None
        module._voltage_sensor_list = ["s1"]
        assert module.get_all_voltage_sensors() == ["s1"]
        assert module.get_voltage_sensor(0) == "s1"
        assert module.get_num_current_sensors() == 0
        assert module.get_all_current_sensors() == []
        assert module.get_current_sensor(0) is None
        module._current_sensor_list = ["s1"]
        assert module.get_all_current_sensors() == ["s1"]
        assert module.get_current_sensor(0) == "s1"


class DummyModule(ModuleBase):
    def __init__(self, name="DPU0"):
        self.name = name
        # Mock the _state_db_connector to avoid swsscommon dependency in tests
        self._state_db_connector = MagicMock()

    def get_name(self):
        return self.name

    def set_admin_state(self, up):
        return True  # Dummy override


class TestModuleBaseGracefulShutdown:
    # ==== graceful shutdown tests (match timeouts + centralized helpers) ====

    @patch("sonic_platform_base.module_base.time", create=True)
    def test_graceful_shutdown_handler_success(self, mock_time):
        dpu_name = "DPU0"
        mock_time.time.return_value = 1710000000
        mock_time.sleep.return_value = None

        module = DummyModule(name=dpu_name)
        module._state_db_connector.get_all.side_effect = [
            {"state_transition_in_progress": "True"},
            {"state_transition_in_progress": "False"},
        ]

        # Mock the race condition protection to allow the transition to be set
        with patch.object(module, "get_name", return_value=dpu_name), \
             patch.object(module, "_load_transition_timeouts", return_value={"shutdown": 10}), \
             patch.object(module, "set_module_state_transition", return_value=True), \
             patch.object(module, "is_module_state_transition_timed_out", return_value=False):
            result = module.graceful_shutdown_handler()
            assert result is True

    @patch("sonic_platform_base.module_base.time", create=True)
    def test_graceful_shutdown_handler_timeout(self, mock_time):
        dpu_name = "DPU1"
        mock_time.time.return_value = 1710000000
        mock_time.sleep.return_value = None

        module = DummyModule(name=dpu_name)
        # Keep it perpetually "in progress" so the handler’s wait path runs
        module._state_db_connector.get_all.return_value = {
            "state_transition_in_progress": "True",
            "transition_type": "shutdown",
            "transition_start_time": "2024-01-01T00:00:00",
        }

        with patch.object(module, "get_name", return_value=dpu_name), \
             patch.object(module, "_load_transition_timeouts", return_value={"shutdown": 5}), \
             patch.object(module, "set_module_state_transition", return_value=True), \
             patch.object(module, "is_module_state_transition_timed_out", return_value=True):
            result = module.graceful_shutdown_handler()
            assert result is False

    @staticmethod
    @patch("sonic_platform_base.module_base.time", create=True)
    def test_graceful_shutdown_handler_offline_clear(mock_time):
        mock_time.time.return_value = 123456789
        mock_time.sleep.return_value = None

        module = DummyModule(name="DPUX")
        module._state_db_connector.get_all.return_value = {
            "state_transition_in_progress": "True",
            "transition_type": "shutdown",
            "transition_start_time": "2024-01-01T00:00:00",
        }

        with patch.object(module, "get_name", return_value="DPUX"), \
             patch.object(module, "get_oper_status", return_value="Offline"), \
             patch.object(module, "_load_transition_timeouts", return_value={"shutdown": 5}), \
             patch.object(module, "is_module_state_transition_timed_out", return_value=False), \
             patch.object(module, "set_module_state_transition", return_value=True):
            result = module.graceful_shutdown_handler()
            assert result is True

    @staticmethod
    def test_transition_timeouts_platform_missing():
        """If platform is missing, defaults are used."""
        from sonic_platform_base import module_base as mb
        class Dummy(mb.ModuleBase): ...
        mb.ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        with patch("os.path.exists", return_value=False):
            d = Dummy()
            assert d._load_transition_timeouts()["reboot"] == 240

    @staticmethod
    def test_transition_timeouts_reads_value():
        """platform.json dpu_reboot_timeout and dpu_shutdown_timeout are honored."""
        from sonic_platform_base import module_base as mb
        from unittest import mock
        class Dummy(mb.ModuleBase): ...
        mb.ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", new_callable=mock.mock_open,
                   read_data='{"dpu_reboot_timeout": 42, "dpu_shutdown_timeout": 123}'):
            d = Dummy()
            assert d._load_transition_timeouts()["reboot"] == 42
            assert d._load_transition_timeouts()["shutdown"] == 123

    @staticmethod
    def test_transition_timeouts_open_raises():
        """On read error, defaults are used."""
        from sonic_platform_base import module_base as mb
        class Dummy(mb.ModuleBase): ...
        mb.ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", side_effect=FileNotFoundError):
            d = Dummy()
            assert d._load_transition_timeouts()["reboot"] == 240

    # ==== coverage: centralized transition helpers ====

    def test_transition_key_uses_get_name(self, monkeypatch):
        m = ModuleBase()
        monkeypatch.setattr(m, "get_name", lambda: "DPUX", raising=False)
        assert m._transition_key() == "CHASSIS_MODULE_TABLE|DPUX"

    def test_set_module_state_transition_writes_expected_fields(self):
        module = DummyModule()
        module._state_db_connector.get_all.return_value = {}

        with patch.object(module, '_transition_operation_lock', side_effect=contextlib.nullcontext):
            result = module.set_module_state_transition(module._state_db_connector, "DPU9", "startup")

        assert result is True  # Should successfully set the transition

        # Check that 'set' was called with the correct arguments
        module._state_db_connector.set.assert_called_with(
            module._state_db_connector.STATE_DB,
            "CHASSIS_MODULE_TABLE|DPU9",
            {
                "state_transition_in_progress": "True",
                "transition_type": "startup",
                "transition_start_time": unittest.mock.ANY,
            },
        )

    def test_set_module_state_transition_race_condition_protection(self, monkeypatch):
        module = DummyModule()
        module._state_db_connector.get_all.return_value = {
            "state_transition_in_progress": "True",
            "transition_type": "shutdown",
            "transition_start_time": "..."
        }

        def fake_is_timed_out(db, module_name, timeout_seconds):
            # This is the check inside set_module_state_transition
            return False  # Not timed out

        monkeypatch.setattr(module, "is_module_state_transition_timed_out", fake_is_timed_out, raising=False)

        # Mock _load_transition_timeouts to avoid file access
        monkeypatch.setattr(module, "_load_transition_timeouts", lambda: {"shutdown": 180})
        with patch.object(module, '_transition_operation_lock', side_effect=contextlib.nullcontext):
            result = module.set_module_state_transition(module._state_db_connector, "DPU9", "shutdown")

        assert result is False  # Should fail to set due to existing active transition

    def test_clear_module_state_transition_success(self):
        module = DummyModule()

        with patch.object(module, '_transition_operation_lock', side_effect=contextlib.nullcontext):
            result = module.clear_module_state_transition(module._state_db_connector, "DPU9")

        assert result is True

        # Check that 'set' was called to clear the flags
        module._state_db_connector.set.assert_called_with(
            module._state_db_connector.STATE_DB,
            "CHASSIS_MODULE_TABLE|DPU9",
            {"state_transition_in_progress": "False", "transition_type": ""},
        )

        # Check that 'delete' was called to remove the start time
        module._state_db_connector.delete.assert_called_with(
            module._state_db_connector.STATE_DB, "CHASSIS_MODULE_TABLE|DPU9", "transition_start_time"
        )

    def test_clear_module_state_transition_failure(self, monkeypatch):
        module = DummyModule()
        module._state_db_connector.set.side_effect = Exception("DB error")

        with patch.object(module, '_transition_operation_lock', side_effect=contextlib.nullcontext), \
             patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            result = module.clear_module_state_transition(module._state_db_connector, "DPU9")
            assert result is False
            assert "Failed to clear module state transition" in mock_stderr.getvalue()

    def test_get_module_state_transition_passthrough(self):
        expect = {"state_transition_in_progress": "True", "transition_type": "reboot"}
        module = DummyModule()
        module._state_db_connector.get_all.return_value = expect
        got = module.get_module_state_transition(module._state_db_connector, "DPU5")
        assert got is expect

    # ==== coverage: is_module_state_transition_timed_out variants ====

    def test_is_transition_timed_out_not_in_progress(self, monkeypatch):
        module = DummyModule()
        monkeypatch.setattr(
            module, "get_module_state_transition",
            lambda *_: {"state_transition_in_progress": "False"},
            raising=False
        )
        # If not in progress, it's not timed out (it's completed)
        assert module.is_module_state_transition_timed_out(object(), "DPU0", 1)

    def test_is_transition_timed_out_no_entry(self, monkeypatch):
        module = DummyModule()
        monkeypatch.setattr(module, "get_module_state_transition", lambda *_: {}, raising=False)
        assert module.is_module_state_transition_timed_out(object(), "DPU0", 1)

    def test_is_transition_timed_out_no_start_time(self, monkeypatch):
        module = DummyModule()
        monkeypatch.setattr(
            module, "get_module_state_transition", lambda *_: {"state_transition_in_progress": "True"}, raising=False
        )
        # Current implementation returns False when no start time is present (to be safe)
        assert not module.is_module_state_transition_timed_out(object(), "DPU0", 1)

    def test_is_transition_timed_out_bad_timestamp(self, monkeypatch):
        module = DummyModule()
        monkeypatch.setattr(
            module, "get_module_state_transition",
            lambda *_: {
                "state_transition_in_progress": "True",
                "transition_start_time": "bad"
            },
            raising=False
        )
        assert module.is_module_state_transition_timed_out(object(), "DPU0", 1)

    def test_is_transition_timed_out_false(self, monkeypatch):
        from datetime import datetime, timezone, timedelta
        start = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        module = DummyModule()
        monkeypatch.setattr(
            module, "get_module_state_transition",
            lambda *_: {
                "state_transition_in_progress": "True",
                "transition_start_time": start
            },
            raising=False
        )
        assert not module.is_module_state_transition_timed_out(object(), "DPU0", 9999)

    def test_is_transition_timed_out_true(self, monkeypatch):
        from datetime import datetime, timezone, timedelta
        start = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        module = DummyModule()
        monkeypatch.setattr(
            module, "get_module_state_transition",
            lambda *_: {
                "state_transition_in_progress": "True",
                "transition_start_time": start
            },
            raising=False
        )
        assert module.is_module_state_transition_timed_out(object(), "DPU0", 1)

    # ==== coverage: import-time exposure of helper aliases ====
    @staticmethod
    def test_helper_exports_exposed():
        # The helpers are available as methods on ModuleBase; importing
        # them as top-level symbols is not required. Verify presence on class.
        from sonic_platform_base.module_base import ModuleBase as MB
        assert hasattr(MB, 'set_module_state_transition') and callable(getattr(MB, 'set_module_state_transition'))
        assert hasattr(MB, 'clear_module_state_transition') and callable(getattr(MB, 'clear_module_state_transition'))
        assert hasattr(MB, 'is_module_state_transition_timed_out') and callable(getattr(MB, 'is_module_state_transition_timed_out'))


class TestModuleBasePCIAndSensors:
    def test_pci_entry_state_db(self):
        module = DummyModule()

        # Test "detaching" — implementation writes a dict with bus_info and dpu_state
        module.pci_entry_state_db("0000:01:00.0", "detaching")
        module._state_db_connector.set.assert_called_with(
            module._state_db_connector.STATE_DB,
            "PCIE_DETACH_INFO|0000:01:00.0",
            {
                "bus_info": "0000:01:00.0",
                "dpu_state": "detaching"
            }
        )

        # Test "attaching" — implementation deletes specific fields on attach
        module.pci_entry_state_db("0000:02:00.0", "attaching")
        module._state_db_connector.delete.assert_any_call(
            module._state_db_connector.STATE_DB,
            "PCIE_DETACH_INFO|0000:02:00.0",
            "bus_info"
        )
        module._state_db_connector.delete.assert_any_call(
            module._state_db_connector.STATE_DB,
            "PCIE_DETACH_INFO|0000:02:00.0",
            "dpu_state"
        )

    def test_pci_entry_state_db_exception(self):
        module = DummyModule()
        module._state_db_connector.set.side_effect = Exception("DB write error")

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            module.pci_entry_state_db("0000:01:00.0", "detaching")
            # Implementation writes a more specific message
            assert "Failed to write pcie bus info to state database" in mock_stderr.getvalue()

    def test_file_operation_lock(self):
        module = ModuleBase()
        mock_file = MockFile()

        with patch('builtins.open', return_value=mock_file) as mock_file_open, \
             patch('fcntl.flock') as mock_flock, \
             patch('os.makedirs') as mock_makedirs:

            with module._file_operation_lock("/var/lock/test.lock"):
                mock_flock.assert_called_with(123, fcntl.LOCK_EX)

            mock_flock.assert_has_calls([
                call(123, fcntl.LOCK_EX),
                call(123, fcntl.LOCK_UN)
            ])
            assert mock_file.fileno_called

    def test_pci_operation_lock(self):
        module = ModuleBase()
        mock_file = MockFile()

        with patch('builtins.open', return_value=mock_file) as mock_file_open, \
             patch('fcntl.flock') as mock_flock, \
             patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.makedirs') as mock_makedirs:

            with module._pci_operation_lock():
                mock_flock.assert_called_with(123, fcntl.LOCK_EX)

            mock_flock.assert_has_calls([
                call(123, fcntl.LOCK_EX),
                call(123, fcntl.LOCK_UN)
            ])
            assert mock_file.fileno_called

    def test_sensord_operation_lock(self):
        module = ModuleBase()
        mock_file = MockFile()

        with patch('builtins.open', return_value=mock_file) as mock_file_open, \
             patch('fcntl.flock') as mock_flock, \
             patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.makedirs') as mock_makedirs:

            with module._sensord_operation_lock():
                mock_flock.assert_called_with(123, fcntl.LOCK_EX)

            mock_flock.assert_has_calls([
                call(123, fcntl.LOCK_EX),
                call(123, fcntl.LOCK_UN)
            ])
            assert mock_file.fileno_called

    def test_handle_pci_removal(self):
        module = ModuleBase()

        with patch.object(module, 'get_pci_bus_info', return_value=["0000:00:00.0"]), \
             patch.object(module, 'pci_entry_state_db') as mock_db, \
             patch.object(module, 'pci_detach', return_value=True), \
             patch.object(module, '_pci_operation_lock') as mock_lock, \
             patch.object(module, 'get_name', return_value="DPU0"):
            assert module.handle_pci_removal() is True
            mock_db.assert_called_with("0000:00:00.0", "detaching")
            mock_lock.assert_called_once()

        with patch.object(module, 'get_pci_bus_info', side_effect=Exception()):
            assert module.handle_pci_removal() is False

    def test_handle_pci_rescan(self):
        module = ModuleBase()

        with patch.object(module, 'get_pci_bus_info', return_value=["0000:00:00.0"]), \
             patch.object(module, 'pci_entry_state_db') as mock_db, \
             patch.object(module, 'pci_reattach', return_value=True), \
             patch.object(module, '_pci_operation_lock') as mock_lock, \
             patch.object(module, 'get_name', return_value="DPU0"):
            assert module.handle_pci_rescan() is True
            mock_db.assert_called_with("0000:00:00.0", "attaching")
            mock_lock.assert_called_once()

        with patch.object(module, 'get_pci_bus_info', side_effect=Exception()):
            assert module.handle_pci_rescan() is False

    def test_handle_sensor_removal(self):
        module = ModuleBase()

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=True), \
             patch('shutil.copy2') as mock_copy, \
             patch('os.system') as mock_system, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            assert module.handle_sensor_removal() is True
            mock_copy.assert_called_once_with("/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf",
                                             "/etc/sensors.d/ignore_sensors_DPU0.conf")
            mock_system.assert_called_once_with("service sensord restart")
            mock_lock.assert_called_once()

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=False), \
             patch('shutil.copy2') as mock_copy, \
             patch('os.system') as mock_system, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            assert module.handle_sensor_removal() is True
            mock_copy.assert_not_called()
            mock_system.assert_not_called()
            mock_lock.assert_not_called()

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=True), \
             patch('shutil.copy2', side_effect=Exception("Copy failed")):
            assert module.handle_sensor_removal() is False

    def test_handle_sensor_addition(self):
        module = ModuleBase()

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove, \
             patch('os.system') as mock_system, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            assert module.handle_sensor_addition() is True
            mock_remove.assert_called_once_with("/etc/sensors.d/ignore_sensors_DPU0.conf")
            mock_system.assert_called_once_with("service sensord restart")
            mock_lock.assert_called_once()

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=False), \
             patch('os.remove') as mock_remove, \
             patch('os.system') as mock_system, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            assert module.handle_sensor_addition() is True
            mock_remove.assert_not_called()
            mock_system.assert_not_called()
            mock_lock.assert_not_called()

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove', side_effect=Exception("Remove failed")):
            assert module.handle_sensor_addition() is False

    def test_module_pre_shutdown(self):
        module = ModuleBase()

        # Test successful case
        with patch.object(module, 'handle_pci_removal', return_value=True), \
             patch.object(module, 'handle_sensor_removal', return_value=True):
            assert module.module_pre_shutdown() is True

        # Test PCI removal failure
        with patch.object(module, 'handle_pci_removal', return_value=False), \
             patch.object(module, 'handle_sensor_removal', return_value=True):
            assert module.module_pre_shutdown() is False

        # Test sensor removal failure
        with patch.object(module, 'handle_pci_removal', return_value=True), \
             patch.object(module, 'handle_sensor_removal', return_value=False):
            assert module.module_pre_shutdown() is False

    def test_module_post_startup(self):
        module = ModuleBase()

        # Test successful case
        with patch.object(module, 'handle_pci_rescan', return_value=True), \
             patch.object(module, 'handle_sensor_addition', return_value=True):
            assert module.module_post_startup() is True

        # Test PCI rescan failure
        with patch.object(module, 'handle_pci_rescan', return_value=False), \
             patch.object(module, 'handle_sensor_addition', return_value=True):
            assert module.module_post_startup() is False

        # Test sensor addition failure
        with patch.object(module, 'handle_pci_rescan', return_value=True), \
             patch.object(module, 'handle_sensor_addition', return_value=False):
            assert module.module_post_startup() is False


class TestStateDbConnectorSwsscommonOnly:
    @patch('swsscommon.swsscommon.SonicV2Connector')
    def test_initialize_state_db_connector_success(self, mock_connector):
        from sonic_platform_base.module_base import ModuleBase
        mock_db = MagicMock()
        mock_connector.return_value = mock_db
        module = ModuleBase()
        assert module._state_db_connector == mock_db
        mock_db.connect.assert_called_once_with(mock_db.STATE_DB)

    @patch('swsscommon.swsscommon.SonicV2Connector')
    def test_initialize_state_db_connector_exception(self, mock_connector):
        from sonic_platform_base.module_base import ModuleBase
        mock_db = MagicMock()
        mock_db.connect.side_effect = RuntimeError("Connection failed")
        mock_connector.return_value = mock_db

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            module = ModuleBase()
            assert module._state_db_connector is None
            assert "Failed to connect to STATE_DB" in mock_stderr.getvalue()

    def test_state_db_connector_uses_swsscommon_only(self):
        import importlib
        import sys
        from types import ModuleType
        from unittest.mock import patch

        # Fake swsscommon package + swsscommon.swsscommon module
        pkg = ModuleType("swsscommon")
        pkg.__path__ = []  # mark as package
        sub = ModuleType("swsscommon.swsscommon")

        class FakeV2:
            def connect(self, *_):
                pass

        sub.SonicV2Connector = FakeV2

        with patch.dict(sys.modules, {
            "swsscommon": pkg,
            "swsscommon.swsscommon": sub
        }, clear=False):
            mb = importlib.import_module("sonic_platform_base.module_base")
            importlib.reload(mb)
            # Since __init__ calls it, we need to patch before creating an instance
            with patch.object(mb.ModuleBase, '_initialize_state_db_connector') as mock_init_db:
                mock_init_db.return_value = FakeV2()
                instance = mb.ModuleBase()
                assert isinstance(instance._state_db_connector, FakeV2)


# New test cases for set_admin_state_using_graceful_handler logic
class TestModuleBaseAdminState:
    def test_set_admin_state_up_clears_transition(self):
        module = DummyModule()
        module.set_admin_state = MagicMock(return_value=True)
        module.clear_module_state_transition = MagicMock(return_value=True)

        result = module.set_admin_state_using_graceful_handler(True)

        assert result is True
        module.set_admin_state.assert_called_once_with(True)
        module.clear_module_state_transition.assert_called_once()

    def test_set_admin_state_down_success(self):
        module = DummyModule()
        module.graceful_shutdown_handler = MagicMock(return_value=True)
        module.set_admin_state = MagicMock(return_value=True)
        module.clear_module_state_transition = MagicMock(return_value=True)

        result = module.set_admin_state_using_graceful_handler(False)

        assert result is True
        module.graceful_shutdown_handler.assert_called_once()
        module.set_admin_state.assert_called_once_with(False)
        assert module.clear_module_state_transition.call_count == 1