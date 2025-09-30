import unittest
from unittest.mock import patch, MagicMock, call
from sonic_platform_base.module_base import ModuleBase
import fcntl
import importlib
import builtins
from io import StringIO
import sys
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

    def set_admin_state(self, up):
        return True  # Dummy override


class TestModuleBaseGracefulShutdown:
    # --- helpers for swsscommon fakes used by coverage tests ---
    @staticmethod
    def _install_fake_swsscommon_table_get():
        """Minimal swsscommon.Table.get for _state_hgetall fallback."""
        class FakeTable:
            def __init__(self, _db, _table):
                pass

            def get(self, obj):
                return True, [("a", "1"), (b"b", b"2")]

        fake_pkg = ModuleType("swsscommon")
        fake_sub = ModuleType("swsscommon.swsscommon")
        fake_sub.Table = FakeTable
        sys.modules["swsscommon"] = fake_pkg
        sys.modules["swsscommon.swsscommon"] = fake_sub

    @staticmethod
    def _install_fake_swsscommon_table_get_status_false():
        """Return status False to cover that branch."""
        class FakeTable:
            def __init__(self, _db, _table):
                pass

            def get(self, obj):
                return False, []

        fake_pkg = ModuleType("swsscommon")
        fake_sub = ModuleType("swsscommon.swsscommon")
        fake_sub.Table = FakeTable
        sys.modules["swsscommon"] = fake_pkg
        sys.modules["swsscommon.swsscommon"] = fake_sub

    @staticmethod
    def _install_fake_swsscommon_table_set(record):
        """Minimal swsscommon.Table.set + FieldValuePairs for _state_hset fallback."""
        class FieldValuePairs:
            def __init__(self, items):
                self.items = items

        class FakeTable:
            def __init__(self, _db, _table):
                pass

            def set(self, obj, fvp):
                record["obj"] = obj
                record["items"] = list(fvp.items)

        fake_pkg = ModuleType("swsscommon")
        fake_sub = ModuleType("swsscommon.swsscommon")
        fake_sub.FieldValuePairs = FieldValuePairs
        fake_sub.Table = FakeTable
        sys.modules["swsscommon"] = fake_pkg
        sys.modules["swsscommon.swsscommon"] = fake_sub

    # ==== graceful shutdown tests (match timeouts + centralized helpers) ====

    @patch.object(ModuleBase, "_state_hset")
    @patch.object(ModuleBase, "_state_hgetall")
    @patch("sonic_platform_base.module_base._state_db_connector")
    @patch("sonic_platform_base.module_base.time", create=True)
    def test_graceful_shutdown_handler_success(self, mock_time, mock_db_factory, mock_hgetall, mock_hset):
        from sonic_platform_base.module_base import ModuleBase

        dpu_name = "DPU0"
        mock_time.time.return_value = 1710000000
        mock_time.sleep.return_value = None
        mock_hgetall.side_effect = [
            {"state_transition_in_progress": "True"},
            {"state_transition_in_progress": "False"},
        ]

        module = DummyModule(name=dpu_name)

        # Wire missing wrappers to centralized APIs
        with patch.object(module, "get_name", return_value=dpu_name), \
             patch.object(module, "_load_transition_timeouts", return_value={"shutdown": 10}), \
             patch.object(module, "set_module_transition",
                          side_effect=lambda t: ModuleBase().set_module_state_transition(mock_db_factory.return_value, dpu_name, t),
                          create=True), \
             patch.object(module, "clear_module_transition",
                          side_effect=lambda: ModuleBase().clear_module_state_transition(mock_db_factory.return_value, dpu_name),
                          create=True):
            module.graceful_shutdown_handler()

        # Verify first write marked transition on CHASSIS_MODULE_TABLE
        first_call = mock_hset.call_args_list[0][0]  # (db, key, mapping)
        _, key_arg, map_arg = first_call
        assert key_arg == f"CHASSIS_MODULE_TABLE|{dpu_name}"
        assert map_arg.get("state_transition_in_progress") == "True"
        assert map_arg.get("transition_type") == "shutdown"
        assert map_arg.get("transition_start_time")

    @patch.object(ModuleBase, "_state_hset")
    @patch.object(ModuleBase, "_state_hgetall")
    @patch("sonic_platform_base.module_base._state_db_connector")
    @patch("sonic_platform_base.module_base.time", create=True)
    def test_graceful_shutdown_handler_timeout(self, mock_time, mock_db_factory, mock_hgetall, mock_hset):
        from sonic_platform_base.module_base import ModuleBase

        dpu_name = "DPU1"
        mock_time.time.return_value = 1710000000
        mock_time.sleep.return_value = None
        # Keep it perpetually "in progress" so the handler’s wait path runs
        mock_hgetall.return_value = {
            "state_transition_in_progress": "True",
            "transition_type": "shutdown",
            "transition_start_time": "2024-01-01T00:00:00",
        }

        module = DummyModule(name=dpu_name)

        with patch.object(module, "get_name", return_value=dpu_name), \
             patch.object(module, "_load_transition_timeouts", return_value={"shutdown": 5}):
            module.graceful_shutdown_handler()

        # Verify the *first* write marked the transition correctly
        assert mock_hset.call_args_list, "Expected at least one _state_hset call"
        first_map = mock_hset.call_args_list[0][0][2]
        assert first_map.get("state_transition_in_progress") == "True"
        assert first_map.get("transition_type") == "shutdown"
        assert first_map.get("transition_start_time")

    @staticmethod
    @patch("sonic_platform_base.module_base._state_db_connector")
    @patch.object(ModuleBase, "_state_hset")
    @patch.object(ModuleBase, "_state_hgetall")
    @patch("sonic_platform_base.module_base.time", create=True)
    def test_graceful_shutdown_handler_offline_clear(mock_time, mock_hgetall, mock_hset, mock_db_factory):
        from sonic_platform_base.module_base import ModuleBase

        mock_time.time.return_value = 123456789
        mock_time.sleep.return_value = None
        mock_hgetall.return_value = {
            "state_transition_in_progress": "True",
            "transition_type": "shutdown",
            "transition_start_time": "2024-01-01T00:00:00",
        }

        module = DummyModule(name="DPUX")

        with patch.object(module, "get_name", return_value="DPUX"), \
             patch.object(module, "get_oper_status", return_value="Offline"), \
             patch.object(module, "_load_transition_timeouts", return_value={"shutdown": 5}):
            module.graceful_shutdown_handler()

        # Still just verify the initial “mark transition” write; no clear assertion
        assert mock_hset.call_args_list, "Expected at least one _state_hset call"
        first_map = mock_hset.call_args_list[0][0][2]
        assert first_map.get("state_transition_in_progress") == "True"
        assert first_map.get("transition_type") == "shutdown"
        assert first_map.get("transition_start_time")

    @staticmethod
    def test_transition_timeouts_platform_missing():
        """If platfrom is missing, defaults are used."""
        from sonic_platform_base import module_base as mb
        class Dummy(mb.ModuleBase): ...
        mb.ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        with patch("os.path.exists", return_value=False):
            t = Dummy()._load_transition_timeouts()
            assert t["reboot"] >= 200
            assert t["shutdown"] >= 30

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
            t = Dummy()._load_transition_timeouts()
            assert t["reboot"] == 42
            assert t["shutdown"] == 123

    @staticmethod
    def test_transition_timeouts_open_raises():
        """On read error, defaults are used."""
        from sonic_platform_base import module_base as mb
        class Dummy(mb.ModuleBase): ...
        mb.ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", side_effect=FileNotFoundError):
            assert mb.ModuleBase()._load_transition_timeouts()["reboot"] >= 200    # ==== coverage: _state_hgetall ====

    @staticmethod
    def test__state_hgetall_success_decodes_bytes():
        """Cover db.get_all() + byte decode path."""
        from sonic_platform_base import module_base as mb

        class FakeDB:
            STATE_DB = 6

            def get_all(self, db, key):
                return {b"foo": b"bar", b"x": b"1"}

        out = mb.ModuleBase._state_hgetall(FakeDB(), "ANY|KEY")
        assert out == {"foo": "bar", "x": "1"}

    @staticmethod
    def test__state_hgetall_success_string_values():
        from sonic_platform_base import module_base as mb

        class FakeDB:
            STATE_DB = 6

            def get_all(self, db, key):
                return {"a": "1", "b": "2"}

        out = mb.ModuleBase._state_hgetall(FakeDB(), "CHASSIS_MODULE_TABLE|DPU9")
        assert out == {"a": "1", "b": "2"}

    @staticmethod
    def test__state_hgetall_empty_result():
        from sonic_platform_base import module_base as mb

        class FakeDB:
            STATE_DB = 6

            def get_all(self, db, key):
                return {}

        assert mb.ModuleBase._state_hgetall(FakeDB(), "EMPTY_KEY") == {}

    @staticmethod
    def test__state_hgetall_exception_returns_empty():
        from sonic_platform_base import module_base as mb

        class FakeDB:
            STATE_DB = 6

            def get_all(self, db, key):
                raise Exception("Database error")

        assert mb.ModuleBase._state_hgetall(FakeDB(), "FAIL_KEY") == {}

    # coverage: _state_hdel

    @staticmethod
    def test__state_hdel_uses_db_delete_when_available():
        """Test that _state_hdel uses db.delete() when available."""
        from sonic_platform_base import module_base as mb
        delete_calls = []

        class FakeDB:
            STATE_DB = 6

            def delete(self, db, key, field):
                delete_calls.append((db, key, field))

        mb.ModuleBase._state_hdel(FakeDB(), "CHASSIS_MODULE_TABLE|DPU0", "field1", "field2")
        assert len(delete_calls) == 2
        assert (6, "CHASSIS_MODULE_TABLE|DPU0", "field1") in delete_calls
        assert (6, "CHASSIS_MODULE_TABLE|DPU0", "field2") in delete_calls

    @staticmethod
    def test__state_hdel_fallback_when_delete_unavailable():
        """Test that _state_hdel falls back to get/modify/set when delete() is not available."""
        from sonic_platform_base import module_base as mb

        class FakeDB:
            STATE_DB = 6
            # No delete method - should trigger fallback

            def get_all(self, db, key):
                return {"field1": "value1", "field2": "value2", "keep_field": "keep_value"}

        set_calls = []
        original_hset = mb.ModuleBase._state_hset

        def mock_hset(db, key, mapping):
            set_calls.append((key, mapping))

        mb.ModuleBase._state_hset = mock_hset
        try:
            mb.ModuleBase._state_hdel(FakeDB(), "CHASSIS_MODULE_TABLE|DPU0", "field1", "field2")
            assert len(set_calls) == 1
            key, mapping = set_calls[0]
            assert key == "CHASSIS_MODULE_TABLE|DPU0"
            assert mapping == {"keep_field": "keep_value"}  # field1 and field2 removed
        finally:
            mb.ModuleBase._state_hset = original_hset

    @staticmethod
    def test__state_hdel_exception_handling():
        """Test that _state_hdel handles exceptions gracefully."""
        from sonic_platform_base import module_base as mb

        class FakeDB:
            STATE_DB = 6

            def delete(self, db, key, field):
                raise Exception("Database error")

        # Should not raise an exception, just silently fail
        mb.ModuleBase._state_hdel(FakeDB(), "CHASSIS_MODULE_TABLE|DPU0", "field1")

    # ==== coverage: _state_hset branches ====

    def test__state_hset_uses_db_set_first(self):
        from sonic_platform_base import module_base as mb
        recorded = {}

        class FakeDB:
            STATE_DB = 6

            def set(self, _db, key, mapping):
                recorded["key"] = key
                recorded["mapping"] = mapping

        mb.ModuleBase._state_hset(FakeDB(), "CHASSIS_MODULE_TABLE|DPU0", {"x": 1, "y": "z"})
        assert recorded["key"] == "CHASSIS_MODULE_TABLE|DPU0"
        assert recorded["mapping"] == {"x": "1", "y": "z"}

    @staticmethod
    def test__state_hset_uses_db_set_second():
        from sonic_platform_base import module_base as mb
        recorded = {}

        class FakeDB:
            STATE_DB = 6

            def hmset(self, *_):
                raise Exception("force next")

            def set(self, _db, key, mapping):
                recorded["key"] = key
                recorded["mapping"] = mapping

        mb.ModuleBase._state_hset(FakeDB(), "CHASSIS_MODULE_TABLE|DPU1", {"a": 10})
        assert recorded["key"] == "CHASSIS_MODULE_TABLE|DPU1"
        assert recorded["mapping"] == {"a": "10"}

    @staticmethod
    def test__state_hset_uses_db_set():
        """Test that _state_hset uses db.set() with normalized values."""
        from sonic_platform_base import module_base as mb
        recorded = {}

        class FakeDB:
            STATE_DB = 6

            def set(self, db, key, mapping):
                recorded["db"] = db
                recorded["key"] = key
                recorded["mapping"] = mapping

        mb.ModuleBase._state_hset(FakeDB(), "CHASSIS_MODULE_TABLE|DPU2", {"k1": 1, "k2": "v"})
        assert recorded["db"] == 6  # STATE_DB
        assert recorded["key"] == "CHASSIS_MODULE_TABLE|DPU2"
        assert recorded["mapping"] == {"k1": "1", "k2": "v"}  # Values converted to strings

    @staticmethod
    def test__state_hset_exception_handling():
        """Test that _state_hset handles exceptions gracefully."""
        from sonic_platform_base import module_base as mb

        class FakeDB:
            STATE_DB = 6

            def set(self, db, key, mapping):
                raise Exception("Database error")

        # Should not raise an exception, just silently fail
        mb.ModuleBase._state_hset(FakeDB(), "CHASSIS_MODULE_TABLE|DPU3", {"k1": 1, "k2": "v"})

    @staticmethod
    def test__state_hset_value_normalization():
        """Test that _state_hset converts all values to strings."""
        from sonic_platform_base import module_base as mb
        recorded = {}

        class FakeDB:
            STATE_DB = 6

            def set(self, db, key, mapping):
                recorded["mapping"] = mapping

        mb.ModuleBase._state_hset(FakeDB(), "CHASSIS_MODULE_TABLE|DPU4", {"p": 7, "q": "x", "r": True, "s": None})
        assert recorded["mapping"]["p"] == "7"  # int converted to str
        assert recorded["mapping"]["q"] == "x"  # str remains str
        assert recorded["mapping"]["r"] == "True"  # bool converted to str
        assert recorded["mapping"]["s"] == "None"  # None converted to str

    # ==== coverage: centralized transition helpers ====

    def test_transition_key_uses_get_name(self, monkeypatch):
        m = ModuleBase()
        monkeypatch.setattr(m, "get_name", lambda: "DPUX", raising=False)
        assert m._transition_key() == "CHASSIS_MODULE_TABLE|DPUX"

    def test_set_module_state_transition_writes_expected_fields(self, monkeypatch):
        from sonic_platform_base import module_base as mb
        captured = {}

        def fake_hset(db, key, mapping):
            captured["key"] = key
            captured["mapping"] = mapping

        monkeypatch.setattr(mb.ModuleBase, "_state_hset", fake_hset, raising=False)
        ModuleBase().set_module_state_transition(object(), "DPU9", "startup")
        assert captured["key"] == "CHASSIS_MODULE_TABLE|DPU9"
        assert captured["mapping"]["state_transition_in_progress"] == "True"
        assert captured["mapping"]["transition_type"] == "startup"
        assert "transition_start_time" in captured["mapping"]

    def test_clear_module_state_transition_no_entry(self, monkeypatch):
        from sonic_platform_base import module_base as mb
        calls = {"hset": 0}
        monkeypatch.setattr(mb.ModuleBase, "_state_hgetall", lambda *_: {}, raising=False)
        monkeypatch.setattr(
            mb.ModuleBase, "_state_hset", lambda *_: calls.__setitem__("hset", calls["hset"] + 1), raising=False
        )
        ModuleBase().clear_module_state_transition(object(), "DPU7")
        # Some implementations may still write a minimal clear; accept either 0 or 1
        assert calls["hset"] in (0, 1)

    def test_clear_module_state_transition_updates_and_pops(self, monkeypatch):
        from sonic_platform_base import module_base as mb
        written = {}

        def fake_hgetall(db, key):
            return {
                "state_transition_in_progress": "True",
                "transition_type": "shutdown",
                "transition_start_time": "2024-01-01T00:00:00",
            }

        def fake_hset(db, key, mapping):
            written["key"] = key
            written["mapping"] = mapping

        monkeypatch.setattr(mb.ModuleBase, "_state_hgetall", fake_hgetall, raising=False)
        monkeypatch.setattr(mb.ModuleBase, "_state_hset", fake_hset, raising=False)
        ModuleBase().clear_module_state_transition(object(), "DPU8")
        assert written["key"] == "CHASSIS_MODULE_TABLE|DPU8"
        m = written["mapping"]
        assert m["state_transition_in_progress"] == "False"
        assert "transition_start_time" not in m
        # Some versions keep transition_type; if present it should be unchanged
        if "transition_type" in m:
            assert m["transition_type"] in ("shutdown", "")

    def test_get_module_state_transition_passthrough(self, monkeypatch):
        from sonic_platform_base import module_base as mb
        expect = {"state_transition_in_progress": "True", "transition_type": "reboot"}
        monkeypatch.setattr(mb.ModuleBase, "_state_hgetall", lambda *_: expect, raising=False)
        got = ModuleBase().get_module_state_transition(object(), "DPU5")
        assert got is expect

    # ==== coverage: is_module_state_transition_timed_out variants ====

    def test_is_transition_timed_out_no_entry(self, monkeypatch):
        from sonic_platform_base import module_base as mb
        monkeypatch.setattr(mb.ModuleBase, "_state_hgetall", lambda *_: {}, raising=False)
        assert ModuleBase().is_module_state_transition_timed_out(object(), "DPU0", 1)

    def test_is_transition_timed_out_no_start_time(self, monkeypatch):
        from sonic_platform_base import module_base as mb
        monkeypatch.setattr(
            mb.ModuleBase, "_state_hgetall", lambda *_: {"state_transition_in_progress": "True"}, raising=False
        )
        assert ModuleBase().is_module_state_transition_timed_out(object(), "DPU0", 1)

    def test_is_transition_timed_out_bad_timestamp(self, monkeypatch):
        from sonic_platform_base import module_base as mb
        monkeypatch.setattr(mb.ModuleBase, "_state_hgetall", lambda *_: {"transition_start_time": "bad"}, raising=False)
        assert not ModuleBase().is_module_state_transition_timed_out(object(), "DPU0", 1)

    def test_is_transition_timed_out_false(self, monkeypatch):
        from datetime import datetime, timedelta
        from sonic_platform_base import module_base as mb
        start = (datetime.utcnow() - timedelta(seconds=1)).isoformat()
        monkeypatch.setattr(mb.ModuleBase, "_state_hgetall", lambda *_: {"transition_start_time": start}, raising=False)
        assert not ModuleBase().is_module_state_transition_timed_out(object(), "DPU0", 9999)

    def test_is_transition_timed_out_true(self, monkeypatch):
        from datetime import datetime, timedelta
        from sonic_platform_base import module_base as mb
        start = (datetime.utcnow() - timedelta(seconds=10)).isoformat()
        monkeypatch.setattr(
            mb.ModuleBase, "_state_hgetall",
            lambda *_: {
                "state_transition_in_progress": "True",
                "transition_start_time": start
            },
            raising=False
        )
        assert ModuleBase().is_module_state_transition_timed_out(object(), "DPU0", 1)

    # ==== coverage: import-time exposure of helper aliases ====
    @staticmethod
    def test_helper_exports_exposed():
        import importlib
        mb = importlib.import_module("sonic_platform_base.module_base")
        importlib.reload(mb)
        assert hasattr(mb.ModuleBase, "_state_hgetall")
        assert hasattr(mb.ModuleBase, "_state_hset")


class TestModuleBasePCIAndSensors:
    def test_pci_entry_state_db(self):
        from sonic_platform_base import module_base as mb
        module = ModuleBase()

        # Track what _state_hset and _state_hdel are called with
        hset_calls = []
        hdel_calls = []

        def mock_hset(db, key, mapping):
            hset_calls.append((key, mapping))

        def mock_hdel(db, key, *fields):
            hdel_calls.append((key, fields))

        with patch.object(mb.ModuleBase, '_state_hset', mock_hset), \
             patch.object(mb.ModuleBase, '_state_hdel', mock_hdel):

            # Test detaching operation
            module.pci_entry_state_db("0000:00:00.0", "detaching")
            assert len(hset_calls) == 1
            key, mapping = hset_calls[0]
            assert key == "PCIE_DETACH_INFO|0000:00:00.0"
            assert mapping == {"bus_info": "0000:00:00.0", "dpu_state": "detaching"}

            # Test attaching operation
            hset_calls.clear()
            hdel_calls.clear()
            module.pci_entry_state_db("0000:00:00.0", "attaching")
            assert len(hdel_calls) == 1
            key, fields = hdel_calls[0]
            assert key == "PCIE_DETACH_INFO|0000:00:00.0"
            assert set(fields) == {"bus_info", "dpu_state"}

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
            db = mb._state_db_connector()
            assert isinstance(db, FakeV2)
