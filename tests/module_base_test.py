import unittest
from unittest.mock import patch, MagicMock, call
from sonic_platform_base.module_base import ModuleBase
import pytest
import json
import os
import fcntl
import importlib
import builtins
from io import StringIO
import shutil
from click.testing import CliRunner
import sys
from types import ModuleType

try:
    import config.chassis_modules  # noqa: F401
    _HAS_SONIC_UTILS = True
except Exception:
    _HAS_SONIC_UTILS = False


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

    # 1) Shutdown sets flags and admin_status=down (sonic-utilities CLI)
    @unittest.skipUnless(_HAS_SONIC_UTILS, "sonic-utilities (config.chassis_modules) not available")
    def test_shutdown_triggers_transition_tracking(self):
        with patch("config.chassis_modules.is_smartswitch", return_value=True, create=True), \
             patch("config.chassis_modules.get_config_module_state", return_value="up", create=True):

            from utilities_common.db import Db
            import config

            runner = CliRunner()
            db = Db()

            result = runner.invoke(
                config.config.commands["chassis"].commands["modules"].commands["shutdown"],
                ["DPU0"],
                obj=db
            )
            assert result.exit_code == 0

            # CONFIG_DB admin down
            cfg_fvs = db.cfgdb.get_entry("CHASSIS_MODULE", "DPU0")
            assert cfg_fvs.get("admin_status") == "down"

            # STATE_DB transition flags (centralized API)
            state_fvs = db.db.get_all("STATE_DB", "CHASSIS_MODULE_TABLE|DPU0")
            assert state_fvs is not None
            assert state_fvs.get("state_transition_in_progress") == "True"
            assert state_fvs.get("transition_type") == "shutdown"
            assert state_fvs.get("transition_start_time")

    # 2) Shutdown when transition already in progress
    @unittest.skipUnless(_HAS_SONIC_UTILS, "sonic-utilities (config.chassis_modules) not available")
    def test_shutdown_triggers_transition_in_progress(self):
        with patch("config.chassis_modules.is_smartswitch", return_value=True, create=True), \
             patch("config.chassis_modules.get_config_module_state", return_value="up", create=True), \
             patch("config.chassis_modules.get_state_transition_in_progress", return_value="True", create=True), \
             patch("config.chassis_modules.is_transition_timed_out", return_value=False, create=True):

            from utilities_common.db import Db
            import config

            runner = CliRunner()
            db = Db()

            result = runner.invoke(
                config.config.commands["chassis"].commands["modules"].commands["shutdown"],
                ["DPU0"],
                obj=db
            )
            assert result.exit_code == 0

            fvs = db.db.get_all("STATE_DB", "CHASSIS_MODULE_TABLE|DPU0")
            assert fvs is not None
            assert fvs.get("state_transition_in_progress") == "True"
            assert fvs.get("transition_start_time")

    # 3) Transition timeout path
    @unittest.skipUnless(_HAS_SONIC_UTILS, "sonic-utilities (config.chassis_modules) not available")
    def test_shutdown_triggers_transition_timeout(self):
        with patch("config.chassis_modules.is_smartswitch", return_value=True, create=True), \
             patch("config.chassis_modules.get_config_module_state", return_value="up", create=True), \
             patch("config.chassis_modules.get_state_transition_in_progress", return_value="True", create=True), \
             patch("config.chassis_modules.is_transition_timed_out", return_value=True, create=True):

            from utilities_common.db import Db
            import config

            runner = CliRunner()
            db = Db()

            result = runner.invoke(
                config.config.commands["chassis"].commands["modules"].commands["shutdown"],
                ["DPU0"],
                obj=db
            )
            assert result.exit_code == 0

            fvs = db.db.get_all("STATE_DB", "CHASSIS_MODULE_TABLE|DPU0")
            assert fvs is not None
            assert "state_transition_in_progress" in fvs

    # Helpers to fake per-instance transition methods (module under test expects these)

    @staticmethod
    def _install_fake_transition_methods(module, mb):
        """
        Attach set_module_transition / clear_module_transition to the module instance.
        These write to CHASSIS_MODULE_TABLE via the patched _state_hset mock.
        """
        def _fake_set(transition_type):
            # Remember last type for clear()
            setattr(module, "_last_transition_type", transition_type)
            key = f"CHASSIS_MODULE_TABLE|{module.get_name()}"
            mb._state_hset(object(), key, {
                "state_transition_in_progress": "True",
                "transition_type": transition_type,
                "transition_start_time": "2024-01-01T00:00:00"
            })

        def _fake_clear():
            key = f"CHASSIS_MODULE_TABLE|{module.get_name()}"
            ttype = getattr(module, "_last_transition_type", "shutdown")
            mb._state_hset(object(), key, {
                "state_transition_in_progress": "False",
                "transition_type": ttype
            })

        # Patch them onto the *instance* to match how the code calls `self.*`
        patch.object(module, "set_module_transition", new=_fake_set, create=True).start()
        patch.object(module, "clear_module_transition", new=_fake_clear, create=True).start()

    # 4) Graceful shutdown handler – success (cleared by other agent)
    @patch("sonic_platform_base.module_base._state_hset", create=True)
    @patch("sonic_platform_base.module_base._state_hgetall", create=True)
    @patch("sonic_platform_base.module_base.SonicV2Connector")
    @patch("sonic_platform_base.module_base.time", create=True)
    def test_graceful_shutdown_handler_success(self, mock_time, mock_db, mock_hgetall, mock_hset):
        dpu_name = "DPU0"
        mock_time.time.return_value = 1710000000
        mock_time.sleep.return_value = None

        # First poll: in-progress; Second poll: cleared
        mock_hgetall.side_effect = [
            {"state_transition_in_progress": "True"},
            {"state_transition_in_progress": "False"},
        ]

        from sonic_platform_base import module_base as mb
        module = DummyModule(name=dpu_name)

        with patch.object(module, "get_name", return_value=dpu_name), \
             patch.object(module, "_load_transition_timeouts", return_value={"shutdown": 10}):
            self._install_fake_transition_methods(module, mb)
            module.graceful_shutdown_handler()

        # Verify first write marked transition
        first_call = mock_hset.call_args_list[0][0]  # (db, key, mapping)
        _, key_arg, map_arg = first_call
        assert key_arg == f"CHASSIS_MODULE_TABLE|{dpu_name}"
        assert map_arg.get("state_transition_in_progress") == "True"
        assert map_arg.get("transition_type") == "shutdown"
        assert "transition_start_time" in map_arg and map_arg["transition_start_time"]

    # 5) Graceful shutdown handler – timeout then self-clear
    @patch("sonic_platform_base.module_base._state_hset", create=True)
    @patch("sonic_platform_base.module_base._state_hgetall", create=True)
    @patch("sonic_platform_base.module_base.SonicV2Connector")
    @patch("sonic_platform_base.module_base.time", create=True)
    def test_graceful_shutdown_handler_timeout(self, mock_time, mock_db, mock_hgetall, mock_hset):
        dpu_name = "DPU1"
        mock_time.time.return_value = 1710000000
        mock_time.sleep.return_value = None

        # Always in-progress; handler will time out and clear itself
        mock_hgetall.return_value = {"state_transition_in_progress": "True"}

        from sonic_platform_base import module_base as mb
        module = DummyModule(name=dpu_name)

        with patch.object(module, "get_name", return_value=dpu_name), \
             patch.object(module, "_load_transition_timeouts", return_value={"shutdown": 5}):
            self._install_fake_transition_methods(module, mb)
            module.graceful_shutdown_handler()

        # First write: mark transition
        first_map = mock_hset.call_args_list[0][0][2]
        assert first_map.get("state_transition_in_progress") == "True"
        assert first_map.get("transition_type") == "shutdown"
        assert "transition_start_time" in first_map and first_map["transition_start_time"]

        # Last write: timeout clear
        last_map = mock_hset.call_args_list[-1][0][2]
        assert last_map.get("state_transition_in_progress") == "False"
        assert last_map.get("transition_type") == "shutdown"

    # 6) If oper_status becomes Offline, handler clears in_progress
    @staticmethod
    @patch("sonic_platform_base.module_base.SonicV2Connector")
    @patch("sonic_platform_base.module_base._state_hset", create=True)
    @patch("sonic_platform_base.module_base._state_hgetall", create=True)
    @patch("sonic_platform_base.module_base.time", create=True)
    def test_graceful_shutdown_handler_offline_clear(mock_time, mock_hgetall, mock_hset, mock_db):
        mock_time.time.return_value = 123456789
        mock_time.sleep.return_value = None
        mock_hgetall.return_value = {"state_transition_in_progress": "True"}

        from sonic_platform_base import module_base as mb
        module = DummyModule(name="DPUX")

        with patch.object(module, "get_name", return_value="DPUX"), \
             patch.object(module, "get_oper_status", return_value="Offline"), \
             patch.object(module, "_load_transition_timeouts", return_value={"shutdown": 5}):
            # Install fake transition methods so handler can call them
            TestModuleBaseGracefulShutdown._install_fake_transition_methods(module, mb)
            module.graceful_shutdown_handler()

        last_map = mock_hset.call_args_list[-1][0][2]
        assert last_map.get("state_transition_in_progress") == "False"
        assert last_map.get("transition_type") == "shutdown"

    # ----------------------------
    # PCI / sensor helpers (unchanged)
    # ----------------------------

    def test_pci_entry_state_db(self):
        module = ModuleBase()
        mock_connector = MagicMock()
        module.state_db_connector = mock_connector

        module.pci_entry_state_db("0000:00:00.0", "detaching")
        mock_connector.hset.assert_has_calls([
            call("PCIE_DETACH_INFO|0000:00:00.0", "bus_info", "0000:00:00.0"),
            call("PCIE_DETACH_INFO|0000:00:00.0", "dpu_state", "detaching")
        ])

        module.pci_entry_state_db("0000:00:00.0", "attaching")
        mock_connector.delete.assert_called_with("PCIE_DETACH_INFO|0000:00:00.0")

        mock_connector.hset.side_effect = Exception("DB Error")
        module.pci_entry_state_db("0000:00:00.0", "detaching")

    def test_pci_operation_lock(self):
        module = ModuleBase()
        mock_file = MockFile()

        with patch('builtins.open', return_value=mock_file), \
             patch('fcntl.flock') as mock_flock, \
             patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.makedirs'):
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
             patch('os.system') as mock_system:
            assert module.handle_sensor_removal() is True
            mock_copy.assert_called_once_with(
                "/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf",
                "/etc/sensors.d/ignore_sensors_DPU0.conf"
            )
            mock_system.assert_called_once_with("service sensord restart")

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=False), \
             patch('shutil.copy2') as mock_copy, \
             patch('os.system') as mock_system:
            assert module.handle_sensor_removal() is True
            mock_copy.assert_not_called()
            mock_system.assert_not_called()

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=True), \
             patch('shutil.copy2', side_effect=Exception("Copy failed")):
            assert module.handle_sensor_removal() is False

    def test_handle_sensor_addition(self):
        module = ModuleBase()

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove, \
             patch('os.system') as mock_system:
            assert module.handle_sensor_addition() is True
            mock_remove.assert_called_once_with("/etc/sensors.d/ignore_sensors_DPU0.conf")
            mock_system.assert_called_once_with("service sensord restart")

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=False), \
             patch('os.remove') as mock_remove, \
             patch('os.system') as mock_system:
            assert module.handle_sensor_addition() is True
            mock_remove.assert_not_called()
            mock_system.assert_not_called()

        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove', side_effect=Exception("Remove failed")):
            assert module.handle_sensor_addition() is False

    def test_module_pre_shutdown(self):
        module = ModuleBase()

        # Success
        with patch.object(module, 'handle_pci_removal', return_value=True), \
             patch.object(module, 'handle_sensor_removal', return_value=True):
            assert module.module_pre_shutdown() is True

        # PCI removal failure
        with patch.object(module, 'handle_pci_removal', return_value=False), \
             patch.object(module, 'handle_sensor_removal', return_value=True):
            assert module.module_pre_shutdown() is False

        # Sensor removal failure
        with patch.object(module, 'handle_pci_removal', return_value=True), \
             patch.object(module, 'handle_sensor_removal', return_value=False):
            assert module.module_pre_shutdown() is False

    def test_module_post_startup(self):
        module = ModuleBase()

        # Success
        with patch.object(module, 'handle_pci_rescan', return_value=True), \
             patch.object(module, 'handle_sensor_addition', return_value=True):
            assert module.module_post_startup() is True

        # PCI rescan failure
        with patch.object(module, 'handle_pci_rescan', return_value=False), \
             patch.object(module, 'handle_sensor_addition', return_value=True):
            assert module.module_post_startup() is False

        # Sensor addition failure
        with patch.object(module, 'handle_pci_rescan', return_value=True), \
             patch.object(module, 'handle_sensor_addition', return_value=False):
            assert module.module_post_startup() is False

    # ----------------------------
    # Import / helpers coverage
    # ----------------------------

    @staticmethod
    def test_import_fallback_to_swsscommon():
        """Cover swsssdk -> swsscommon fallback by reloading module_base."""
        orig_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "swsssdk":
                raise ImportError("simulate missing swsssdk")
            return orig_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            mb = importlib.import_module("sonic_platform_base.module_base")
            importlib.reload(mb)
            assert hasattr(mb, "SonicV2Connector")

    @staticmethod
    def test__state_hgetall_fallback_decodes_bytes():
        """Cover module-level _state_hgetall client fallback + byte decode."""
        from sonic_platform_base import module_base as mb

        class FakeClient:
            def hgetall(self, key):
                return {b"foo": b"bar", b"x": b"1"}

        class FakeDB:
            STATE_DB = 6

            def get_all(self, *_):
                raise Exception("force client fallback")

            def get_redis_client(self, *_):
                return FakeClient()

        out = mb._state_hgetall(FakeDB(), "ANY|KEY")
        assert out == {"foo": "bar", "x": "1"}

    @staticmethod
    def test__state_hset_fallback_to_client_hset():
        """Cover module-level _state_hset branch when db.set raises -> client.hset."""
        from sonic_platform_base import module_base as mb
        recorded = {}

        class FakeClient:
            def hset(self, key, mapping=None, **_):
                recorded["key"] = key
                recorded["mapping"] = mapping

        class FakeDB:
            STATE_DB = 6

            def set(self, *_):
                raise Exception("force client.hset")

            def get_redis_client(self, *_):
                return FakeClient()

        mb._state_hset(FakeDB(), "CHASSIS_MODULE_TABLE|DPU0", {"a": 1, "b": "x"})
        assert recorded["key"] == "CHASSIS_MODULE_TABLE|DPU0"
        assert recorded["mapping"] == {"a": "1", "b": "x"}  # coerced to str

    @staticmethod
    def test__cfg_get_entry_initializes_v2_and_decodes():
        """Cover _cfg_get_entry with _v2 initialization and byte decoding."""
        from sonic_platform_base import module_base as mb

        class FakeV2:
            CONFIG_DB = object()

            def __init__(self, *args, **kwargs):
                pass  # must accept use_unix_socket_path=True

            def connect(self, *_):
                pass

            def get_all(self, *_):
                return {b"platform": b"x86_64-foo", b"other": b"bar"}

        # Provide a fake package layout: swsscommon + swsscommon.swsscommon
        pkg = ModuleType("swsscommon")
        sub = ModuleType("swsscommon.swsscommon")
        sub.SonicV2Connector = FakeV2
        sys.modules["swsscommon"] = pkg
        sys.modules["swsscommon.swsscommon"] = sub

        # Force fresh init path
        mb._v2 = None

        if not hasattr(mb, "_cfg_get_entry"):
            pytest.skip("_cfg_get_entry is not exposed in this build")

        out = mb._cfg_get_entry("DEVICE_METADATA", "localhost")
        assert out == {"platform": "x86_64-foo", "other": "bar"}

    # ----------------------------
    # Timeouts (replaces old get_reboot_timeout tests)
    # ----------------------------

    @staticmethod
    def test_load_transition_timeouts_platform_missing():
        """When platform is missing, fall back to class defaults."""
        from sonic_platform_base import module_base as mb
        class Dummy(mb.ModuleBase): ...
        with patch("sonic_platform_base.module_base._cfg_get_entry", return_value={}, create=True):
            t = Dummy()._load_transition_timeouts()
            assert t["startup"] == mb.ModuleBase._TRANSITION_TIMEOUT_DEFAULTS["startup"]
            assert t["shutdown"] == mb.ModuleBase._TRANSITION_TIMEOUT_DEFAULTS["shutdown"]
            assert t["reboot"] == mb.ModuleBase._TRANSITION_TIMEOUT_DEFAULTS["reboot"]

    @staticmethod
    def test_load_transition_timeouts_reads_values():
        """Read values from platform.json: dpu_*_timeout keys."""
        from sonic_platform_base import module_base as mb
        from unittest import mock
        class Dummy(mb.ModuleBase): ...
        with patch("sonic_platform_base.module_base._cfg_get_entry", return_value={"platform": "plat"}, create=True), \
             patch("builtins.open", new_callable=mock.mock_open,
                   read_data=json.dumps({
                       "dpu_startup_timeout": 11,
                       "dpu_shutdown_timeout": 22,
                       "dpu_reboot_timeout": 33
                   })):
            t = Dummy()._load_transition_timeouts()
            assert t["startup"] == 11
            assert t["shutdown"] == 22
            assert t["reboot"] == 33

    @staticmethod
    def test_load_transition_timeouts_open_raises():
        """On file read error, stick with defaults."""
        from sonic_platform_base import module_base as mb
        class Dummy(mb.ModuleBase): ...
        with patch("sonic_platform_base.module_base._cfg_get_entry", return_value={"platform": "plat"}, create=True), \
             patch("builtins.open", side_effect=FileNotFoundError):
            t = Dummy()._load_transition_timeouts()
            assert t == mb.ModuleBase._TRANSITION_TIMEOUT_DEFAULTS
