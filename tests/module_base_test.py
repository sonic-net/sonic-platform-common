# Unit tests for sonic_platform_base.module_base.ModuleBase
import json
import time
from unittest.mock import MagicMock, patch, call
import pytest
import subprocess

from sonic_platform_base.module_base import ModuleBase


class MockFile:
    """Minimal file-like object with a stable fileno() for flock tests."""
    def __init__(self, data=""):
        self._data = data
        self._closed = False
        self.fileno_called = False

    def __enter__(self): return self
    def __exit__(self, *a): self._closed = True
    def read(self): return self._data
    def write(self, d): self._data = d
    def fileno(self):
        self.fileno_called = True
        return 123


class TestModuleBase:
    # ------------------------------------------------------------------ Setup --
    def setup_method(self):
        # Prevent real DB connection during ModuleBase __init__
        self._db_patcher = patch("sonic_py_common.daemon_base.db_connect", lambda *a, **k: None)
        self._db_patcher.start()
        self.module = ModuleBase()

    def teardown_method(self):
        self._db_patcher.stop()

    # ------------------------------------------------------ Not Implemented API --
    @pytest.mark.parametrize(
        "method_name",
        ["get_dpu_id", "get_reboot_cause", "get_state_info", "get_pci_bus_info", "pci_detach", "pci_reattach"],
    )
    def test_not_implemented_methods_raise(self, method_name):
        with pytest.raises(NotImplementedError):
            getattr(self.module, method_name)()

    def test_is_host_detection(self):
        # Test when /.dockerenv does not exist (host environment)
        with patch("os.path.exists", return_value=False):
            module_on_host = ModuleBase()
            assert module_on_host.is_host is True

        # Test when /.dockerenv exists (container environment)
        with patch("os.path.exists", return_value=True):
            module_in_container = ModuleBase()
            assert module_in_container.is_host is False

    # -------------------------------------------------------------- Sensors API --
    def test_sensors_api(self):
        assert self.module.get_num_voltage_sensors() == 0
        assert self.module.get_all_voltage_sensors() == []
        assert self.module.get_voltage_sensor(0) is None
        assert self.module.get_num_current_sensors() == 0
        assert self.module.get_all_current_sensors() == []
        assert self.module.get_current_sensor(0) is None

        self.module._voltage_sensor_list = ["s1"]
        self.module._current_sensor_list = ["s1"]
        assert self.module.get_all_voltage_sensors() == ["s1"]
        assert self.module.get_voltage_sensor(0) == "s1"
        assert self.module.get_all_current_sensors() == ["s1"]
        assert self.module.get_current_sensor(0) == "s1"

    # --------------------------------------------------------- PCI state in DB --
    def test_pci_entry_state_db(self):
        db = MagicMock()
        self.module.state_db = db

        self.module.pci_entry_state_db("0000:00:00.0", "detaching")
        db.hset.assert_has_calls([
            call("PCIE_DETACH_INFO|0000:00:00.0", "bus_info", "0000:00:00.0"),
            call("PCIE_DETACH_INFO|0000:00:00.0", "dpu_state", "detaching"),
        ])

        self.module.pci_entry_state_db("0000:00:00.0", "attaching")
        db.delete.assert_called_with("PCIE_DETACH_INFO|0000:00:00.0")

        db.hset.side_effect = Exception("DB Error")
        self.module.pci_entry_state_db("0000:00:00.0", "detaching")  # should not raise

    # -------------------------------------------------------------- File locks --
    @pytest.mark.parametrize(
        "lock_method_name, extra",
        [
            ("_file_operation_lock", {"lock_path": "/var/lock/test.lock"}),
            ("_pci_operation_lock", {}),
            ("_sensord_operation_lock", {}),
            ("_transition_operation_lock", {}),
        ],
    )
    def test_lock_contexts(self, lock_method_name, extra):
        mf = MockFile()
        with patch("builtins.open", return_value=mf), \
             patch("fcntl.flock") as pflock, \
             patch("os.makedirs"), \
             patch.object(self.module, "get_name", return_value="DPU0"):
            lock_ctx = getattr(self.module, lock_method_name)
            if "lock_path" in extra:
                with lock_ctx(extra["lock_path"]):
                    pass
            else:
                with lock_ctx():
                    pass

        import fcntl
        pflock.assert_has_calls([call(123, fcntl.LOCK_EX), call(123, fcntl.LOCK_UN)])
        assert mf.fileno_called

    # ---------------------------------------------------------- PCI operations --
    def test_handle_pci_removal_success(self):
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "get_pci_bus_info", return_value=["0000:00:00.0"]), \
             patch.object(self.module, "pci_entry_state_db") as mdb, \
             patch.object(self.module, "pci_detach", return_value=True), \
             patch.object(self.module, "_pci_operation_lock"):
            assert self.module.handle_pci_removal() is True
            mdb.assert_called_with("0000:00:00.0", "detaching")

    def test_handle_pci_removal_error(self):
        with patch.object(self.module, "get_pci_bus_info", side_effect=Exception("boom")):
            assert self.module.handle_pci_removal() is False

    def test_handle_pci_rescan_success(self):
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "get_pci_bus_info", return_value=["0000:00:00.0"]), \
             patch.object(self.module, "pci_entry_state_db") as mdb, \
             patch.object(self.module, "pci_reattach", return_value=True), \
             patch.object(self.module, "_pci_operation_lock"):
            assert self.module.handle_pci_rescan() is True
            mdb.assert_called_with("0000:00:00.0", "attaching")

    def test_handle_pci_rescan_error(self):
        with patch.object(self.module, "get_pci_bus_info", side_effect=Exception("boom")):
            assert self.module.handle_pci_rescan() is False

    # ---------------------------------------------------------- Sensor actions --
    def test_handle_sensor_removal(self):
        # Test successful case on host - commands run via docker exec pmon to access container
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(self.module, "_sensord_operation_lock") as mock_lock:
            self.module.is_host = True
            # First call to test -f (fake file exists) returns 0, second call is cp, third is service restart
            mock_call.side_effect = [0, 0, 0]
            assert self.module.handle_sensor_removal() is True
            assert mock_call.call_count == 3
            # When running on host, should call docker exec commands to run inside container
            mock_call.assert_any_call(["docker", "exec", "pmon", "test", "-f",
                                       "/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf"],
                                       stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(["docker", "exec", "pmon", "cp",
                                       "/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf",
                                       "/etc/sensors.d/ignore_sensors_DPU0.conf"],
                                       stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(["docker", "exec", "pmon", "service", "sensord", "restart"],
                                       stdout=subprocess.DEVNULL)
            mock_lock.assert_called_once()

        # Test successful case inside container - commands run directly without docker exec
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(self.module, "_sensord_operation_lock") as mock_lock:
            self.module.is_host = False
            # First call to test -f (fake file exists) returns 0, second call is cp, third is service restart
            mock_call.side_effect = [0, 0, 0]
            assert self.module.handle_sensor_removal() is True
            assert mock_call.call_count == 3
            # When running inside container, should call commands directly without docker exec prefix
            mock_call.assert_any_call(
                ["test", "-f",
                 "/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf"],
                stdout=subprocess.DEVNULL
            )
            mock_call.assert_any_call(
                ["cp", "/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf",
                 "/etc/sensors.d/ignore_sensors_DPU0.conf"],
                stdout=subprocess.DEVNULL
            )
            mock_call.assert_any_call(
                ["service", "sensord", "restart"],
                stdout=subprocess.DEVNULL
            )
            mock_lock.assert_called_once()

        # Test file does not exist - should return True but not call copy or restart
        with patch.object(self.module, "get_name", return_value="DPU0"), \
                patch("subprocess.call") as mock_call, \
                patch.object(self.module, "_sensord_operation_lock") as mock_lock:
            self.module.is_host = True
            # Return 1 to indicate file does not exist
            mock_call.return_value = 1
            assert self.module.handle_sensor_removal() is True
            # Only the file existence check should be called (with docker exec when on host)
            mock_call.assert_called_once_with(
                ['docker', 'exec', 'pmon', 'test', '-f',
                 '/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf'],
                 stdout=subprocess.DEVNULL
                )

        # Test exception handling
        with patch.object(self.module, "get_name", return_value="DPU0"), \
                patch('subprocess.call', side_effect=Exception("copy failed")):
            self.module.is_host = True
            assert self.module.handle_sensor_removal() is False

    def test_handle_sensor_addition(self):
        # Test successful case on host - commands run via docker exec pmon to access container
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(self.module, "_sensord_operation_lock") as mock_lock:
            self.module.is_host = True
            # First call is file check (returns 0=exists), second is rm, third is restart
            mock_call.side_effect = [0, 0, 0]
            assert self.module.handle_sensor_addition() is True
            assert mock_call.call_count == 3
            # When on host, commands are prefixed with docker exec pmon to run inside container
            mock_call.assert_any_call(
                ["docker", "exec", "pmon", "test", "-f",
                 "/etc/sensors.d/ignore_sensors_DPU0.conf"],
                stdout=subprocess.DEVNULL
            )
            mock_call.assert_any_call(
                ["docker", "exec", "pmon", "rm",
                 "/etc/sensors.d/ignore_sensors_DPU0.conf"],
                stdout=subprocess.DEVNULL
            )
            mock_call.assert_any_call(
                ["docker", "exec", "pmon", "service", "sensord", "restart"],
                stdout=subprocess.DEVNULL
            )
            mock_lock.assert_called_once()

        # Test successful case inside container - commands run directly without docker exec
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(self.module, "_sensord_operation_lock") as mock_lock:
            self.module.is_host = False
            # First call to test -f (file exists) returns 0, second call is rm, third is service restart
            mock_call.side_effect = [0, 0, 0]
            assert self.module.handle_sensor_addition() is True
            assert mock_call.call_count == 3
            # When inside container, commands are run directly without docker exec prefix
            mock_call.assert_any_call(
                ["test", "-f", "/etc/sensors.d/ignore_sensors_DPU0.conf"],
                stdout=subprocess.DEVNULL
            )
            mock_call.assert_any_call(
                ["rm", "/etc/sensors.d/ignore_sensors_DPU0.conf"],
                stdout=subprocess.DEVNULL
            )
            mock_call.assert_any_call(
                ["service", "sensord", "restart"],
                stdout=subprocess.DEVNULL
            )
            mock_lock.assert_called_once()

        # Test file does not exist - should return True but not call rm or restart
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch("subprocess.call") as mock_call, \
             patch.object(self.module, "_sensord_operation_lock") as mock_lock:
            self.module.is_host = True
            # Return 1 to indicate file does not exist
            mock_call.side_effect = [1]
            assert self.module.handle_sensor_addition() is True
            # Only the file existence check should be called (with docker exec when on host)
            mock_call.assert_called_once_with(
                ["docker", "exec", "pmon", "test", "-f", "/etc/sensors.d/ignore_sensors_DPU0.conf"],
                stdout=subprocess.DEVNULL
            )
            mock_lock.assert_not_called()

        # Test exception handling
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch('subprocess.call', side_effect=Exception("Remove failed")):
            self.module.is_host = True
            assert self.module.handle_sensor_addition() is False

    # ------------------------------------------------ Pre-shutdown/Post-startup --
    @pytest.mark.parametrize(
        "pci_ok,sensor_ok,expected",
        [(True, True, True), (False, True, False), (True, False, False)],
    )
    def test_module_pre_shutdown(self, pci_ok, sensor_ok, expected):
        with patch.object(self.module, "handle_sensor_removal", return_value=sensor_ok), \
             patch.object(self.module, "handle_pci_removal", return_value=pci_ok):
            assert self.module.module_pre_shutdown() is expected
            # Verify sensor removal is called before PCI removal
            sensor_call = call()
            pci_call = call()
            assert list(self.module.handle_sensor_removal.call_args_list + \
                        self.module.handle_pci_removal.call_args_list) == [sensor_call, pci_call]

        # Test sensor removal failure
        with patch.object(self.module, "handle_sensor_removal", return_value=False), \
             patch.object(self.module, "handle_pci_removal", return_value=pci_ok):
            assert self.module.module_pre_shutdown() is False

        # Test PCI removal failure
        with patch.object(self.module, "handle_sensor_removal", return_value=sensor_ok), \
             patch.object(self.module, "handle_pci_removal", return_value=False):
            assert self.module.module_pre_shutdown() is False

    @pytest.mark.parametrize(
        "pci_ok,sensor_ok,expected",
        [(True, True, True), (False, True, False), (True, False, False)],
    )
    def test_module_post_startup(self, pci_ok, sensor_ok, expected):
        with patch.object(self.module, "handle_pci_rescan", return_value=pci_ok), \
             patch.object(self.module, "handle_sensor_addition", return_value=sensor_ok):
            assert self.module.module_post_startup() is expected

    # -------------------------------------- set_admin_state_gracefully paths --
    @pytest.mark.parametrize("admin_up", [True, False])
    def test_set_admin_state_gracefully_success(self, admin_up):
        db = MagicMock()
        self.module.state_db = db
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=True), \
             patch.object(self.module, "clear_module_state_transition", return_value=True), \
             patch.object(self.module, "set_admin_state", return_value=True) as mset:
            if admin_up:
                with patch.object(self.module, "module_post_startup", return_value=True):
                    assert self.module.set_admin_state_gracefully(True) is True
                    mset.assert_called_once_with(True)
            else:
                with patch.object(self.module, "module_pre_shutdown", return_value=True), \
                     patch.object(self.module, "_graceful_shutdown_handler", return_value=True):
                    assert self.module.set_admin_state_gracefully(False) is True
                    mset.assert_called_once_with(False)

    def test_set_admin_state_gracefully_transition_fail(self, capsys):
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=False):
            assert self.module.set_admin_state_gracefully(True) is False
        assert "Failed to set module state transition for admin state UP" in capsys.readouterr().err

    def test_set_admin_state_gracefully_post_startup_warn(self, capsys):
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=True), \
             patch.object(self.module, "clear_module_state_transition", return_value=True), \
             patch.object(self.module, "set_admin_state", return_value=True), \
             patch.object(self.module, "module_post_startup", return_value=False):
            assert self.module.set_admin_state_gracefully(True) is True
        assert "module_post_startup() failed" in capsys.readouterr().err

    def test_set_admin_state_gracefully_pre_shutdown_warn(self, capsys):
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=True), \
             patch.object(self.module, "clear_module_state_transition", return_value=True), \
             patch.object(self.module, "set_admin_state", return_value=True), \
             patch.object(self.module, "module_pre_shutdown", return_value=False), \
             patch.object(self.module, "_graceful_shutdown_handler", return_value=True):
            assert self.module.set_admin_state_gracefully(False) is True
        assert "module_pre_shutdown() failed" in capsys.readouterr().err

    def test_set_admin_state_gracefully_clear_transition_fail_up(self, capsys):
        """Test clear_module_state_transition failure for admin UP path (lines 442-443)"""
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=True), \
             patch.object(self.module, "clear_module_state_transition", return_value=False), \
             patch.object(self.module, "set_admin_state", return_value=True), \
             patch.object(self.module, "module_post_startup", return_value=True):
            assert self.module.set_admin_state_gracefully(True) is True
        assert "Failed to clear module state transition for admin state UP" in capsys.readouterr().err

    def test_set_admin_state_gracefully_clear_transition_fail_down(self, capsys):
        """Test clear_module_state_transition failure for admin DOWN path (lines 463-464)"""
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=True), \
             patch.object(self.module, "clear_module_state_transition", return_value=False), \
             patch.object(self.module, "set_admin_state", return_value=True), \
             patch.object(self.module, "module_pre_shutdown", return_value=True), \
             patch.object(self.module, "_graceful_shutdown_handler", return_value=True):
            assert self.module.set_admin_state_gracefully(False) is True
        assert "Failed to clear module state transition for admin state DOWN" in capsys.readouterr().err

    def test_set_admin_state_gracefully_set_transition_fail_down(self, capsys):
        """Test set_module_state_transition failure for admin DOWN path (lines 448-450)"""
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=False):
            assert self.module.set_admin_state_gracefully(False) is False
        assert "Failed to set module state transition for admin state DOWN" in capsys.readouterr().err

    def test_set_admin_state_gracefully_graceful_shutdown_fail(self, capsys):
        """Test graceful shutdown handler failure/timeout (lines 456-458)"""
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=True), \
             patch.object(self.module, "clear_module_state_transition", return_value=True), \
             patch.object(self.module, "set_admin_state", return_value=True), \
             patch.object(self.module, "module_pre_shutdown", return_value=True), \
             patch.object(self.module, "_graceful_shutdown_handler", return_value=False):
            assert self.module.set_admin_state_gracefully(False) is True
        assert "Graceful shutdown handler failed or timed out for module: DPU0" in capsys.readouterr().err

    def test_set_admin_state_gracefully_all_failures_up_path(self, capsys):
        """Test multiple failure scenarios in the UP path for maximum coverage"""
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=True), \
             patch.object(self.module, "clear_module_state_transition", return_value=False), \
             patch.object(self.module, "set_admin_state", return_value=True), \
             patch.object(self.module, "module_post_startup", return_value=False):
            result = self.module.set_admin_state_gracefully(True)
            assert result is True  # Method continues despite failures

        captured = capsys.readouterr().err
        assert "module_post_startup() failed" in captured
        assert "Failed to clear module state transition for admin state UP" in captured

    def test_set_admin_state_gracefully_all_failures_down_path(self, capsys):
        """Test multiple failure scenarios in the DOWN path for maximum coverage"""
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "set_module_state_transition", return_value=True), \
             patch.object(self.module, "clear_module_state_transition", return_value=False), \
             patch.object(self.module, "set_admin_state", return_value=True), \
             patch.object(self.module, "module_pre_shutdown", return_value=False), \
             patch.object(self.module, "_graceful_shutdown_handler", return_value=False):
            result = self.module.set_admin_state_gracefully(False)
            assert result is True  # Method continues despite failures

        captured = capsys.readouterr().err
        assert "module_pre_shutdown() failed" in captured
        assert "Graceful shutdown handler failed or timed out for module: DPU0" in captured
        assert "Failed to clear module state transition for admin state DOWN" in captured

    # ----------------------------------------------------- Timeouts loading ----
    def test_load_transition_timeouts_defaults(self):
        ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        with patch("os.path.exists", return_value=False):
            assert self.module._load_transition_timeouts() == {
                "startup": 300,
                "shutdown": 180,
                "reboot": 240,
                "halt_services": 60
            }

    def test_load_transition_timeouts_custom(self):
        ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        data = {
            "dpu_startup_timeout": 600,
            "dpu_shutdown_timeout": 360,
            "dpu_reboot_timeout": 480,
            "dpu_halt_services_timeout": 120
        }
        mf = MockFile(json.dumps(data))
        with patch("os.path.exists", return_value=True), patch("builtins.open", return_value=mf):
            assert self.module._load_transition_timeouts() == {
                "startup": 600,
                "shutdown": 360,
                "reboot": 480,
                "halt_services": 120
            }

    def test_load_transition_timeouts_partial(self):
        ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        mf = MockFile(json.dumps({"dpu_startup_timeout": 500}))
        with patch("os.path.exists", return_value=True), patch("builtins.open", return_value=mf):
            assert self.module._load_transition_timeouts() == {
                "startup": 500,
                "shutdown": 180,
                "reboot": 240,
                "halt_services": 60
            }

    def test_load_transition_timeouts_error(self):
        ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        with patch("os.path.exists", return_value=True), \
             patch("builtins.open", side_effect=Exception("read error")):
            assert self.module._load_transition_timeouts() == {
                "startup": 300,
                "shutdown": 180,
                "reboot": 240,
                "halt_services": 60
            }

    def test_load_transition_timeouts_cache(self):
        ModuleBase._TRANSITION_TIMEOUTS_CACHE = None
        with patch("os.path.exists", return_value=False) as pexists:
            t1 = self.module._load_transition_timeouts()
            t2 = self.module._load_transition_timeouts()
            assert t1 == t2
            pexists.assert_called_once()
        ModuleBase._TRANSITION_TIMEOUTS_CACHE = None

    # -------------------------------------- Graceful shutdown wait-loop --------
    def test_graceful_shutdown_handler_external_completion(self):
        """Test graceful shutdown when external process clears gnoi_halt_in_progress flag"""
        db = MagicMock()
        self.module.state_db = db
        # First call: flag is set, second call: flag is cleared
        db.hget.side_effect = ["True", None]

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_load_transition_timeouts", return_value={"halt_services": 60}), \
             patch("time.sleep") as ms, \
             patch("time.time", side_effect=[1000, 1000, 1005, 1005]):
            assert self.module._graceful_shutdown_handler() is True
            ms.assert_called_once_with(5)
            # Verify we checked the flag twice
            assert db.hget.call_count == 2

    def test_graceful_shutdown_handler_timeout(self, capsys):
        """Test graceful shutdown when timeout is reached"""
        db = MagicMock()
        self.module.state_db = db
        # Flag remains set throughout
        db.hget.return_value = "True"

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_load_transition_timeouts", return_value={"halt_services": 10}), \
             patch("time.sleep") as ms, \
             patch("time.time", side_effect=[1000, 1000, 1005, 1005, 1010, 1010, 1015]):
            assert self.module._graceful_shutdown_handler() is True
            # Verify sleep was called
            ms.assert_called_with(5)
            # Verify flag was cleared after timeout
            db.hdel.assert_called_once_with("CHASSIS_MODULE_TABLE|DPU0", "gnoi_halt_in_progress")

        assert "Shutdown timeout reached for module: DPU0. Proceeding with shutdown." in capsys.readouterr().err

    def test_graceful_shutdown_handler_immediate_past_end(self):
        """Test when current time is already past end time"""
        db = MagicMock()
        self.module.state_db = db
        db.hget.return_value = "True"

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_load_transition_timeouts", return_value={"halt_services": 10}), \
             patch("time.sleep") as ms, \
             patch("time.time", side_effect=[1000, 1020, 1020]):
            # Loop condition fails immediately, returns False
            assert self.module._graceful_shutdown_handler() is False
            ms.assert_not_called()

    def test_graceful_shutdown_handler_custom_timeout(self):
        """Test graceful shutdown with custom halt_services timeout"""
        db = MagicMock()
        self.module.state_db = db
        db.hget.side_effect = ["True", None]

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_load_transition_timeouts", return_value={"halt_services": 120}), \
             patch("time.sleep"), \
             patch("time.time", side_effect=[1000, 1000, 1005, 1005]):
            assert self.module._graceful_shutdown_handler() is True

    # ---------------------------------- GNOI halt flag operations --------------
    def test_get_module_gnoi_halt_in_progress_true(self):
        """Test getting gnoi_halt_in_progress flag when it's set to True"""
        db = MagicMock()
        self.module.state_db = db
        db.hget.return_value = "True"

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module._get_module_gnoi_halt_in_progress() is True
            db.hget.assert_called_once_with("CHASSIS_MODULE_TABLE|DPU0", "gnoi_halt_in_progress")

    def test_get_module_gnoi_halt_in_progress_false(self):
        """Test getting gnoi_halt_in_progress flag when it's not set or False"""
        db = MagicMock()
        self.module.state_db = db

        for value in [None, "False", "false", "", "0"]:
            db.hget.return_value = value
            with patch.object(self.module, "get_name", return_value="DPU0"), \
                 patch.object(self.module, "_transition_operation_lock"):
                assert self.module._get_module_gnoi_halt_in_progress() is False

    def test_get_module_gnoi_halt_in_progress_db_error(self):
        """Test getting gnoi_halt_in_progress flag when database error occurs"""
        db = MagicMock()
        self.module.state_db = db
        db.hget.side_effect = Exception("DB Error")

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module._get_module_gnoi_halt_in_progress() is False

    def test_clear_module_gnoi_halt_in_progress_success(self):
        """Test clearing gnoi_halt_in_progress flag successfully"""
        db = MagicMock()
        self.module.state_db = db

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module._clear_module_gnoi_halt_in_progress() is True
            db.hdel.assert_called_once_with("CHASSIS_MODULE_TABLE|DPU0", "gnoi_halt_in_progress")

    def test_clear_module_gnoi_halt_in_progress_db_error(self):
        """Test clearing gnoi_halt_in_progress flag when database error occurs"""
        db = MagicMock()
        self.module.state_db = db
        db.hdel.side_effect = Exception("DB Error")

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module._clear_module_gnoi_halt_in_progress() is False

    @pytest.mark.parametrize("module_name", ["DPU0", "DPU1", "LINE-CARD0", "SUPERVISOR0"])
    def test_get_module_gnoi_halt_in_progress_various_modules(self, module_name):
        """Test getting gnoi_halt_in_progress flag for various module types"""
        db = MagicMock()
        self.module.state_db = db
        db.hget.return_value = "True"

        with patch.object(self.module, "get_name", return_value=module_name), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module._get_module_gnoi_halt_in_progress() is True
            db.hget.assert_called_with(f"CHASSIS_MODULE_TABLE|{module_name}", "gnoi_halt_in_progress")

    @pytest.mark.parametrize("module_name", ["DPU0", "DPU1", "LINE-CARD0", "SUPERVISOR0"])
    def test_clear_module_gnoi_halt_in_progress_various_modules(self, module_name):
        """Test clearing gnoi_halt_in_progress flag for various module types"""
        db = MagicMock()
        self.module.state_db = db

        with patch.object(self.module, "get_name", return_value=module_name), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module._clear_module_gnoi_halt_in_progress() is True
            db.hdel.assert_called_with(f"CHASSIS_MODULE_TABLE|{module_name}", "gnoi_halt_in_progress")

    def test_set_module_gnoi_halt_in_progress_success(self):
        """Test setting gnoi_halt_in_progress flag successfully"""
        db = MagicMock()
        self.module.state_db = db

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module._set_module_gnoi_halt_in_progress() is True
            db.hset.assert_called_once_with("CHASSIS_MODULE_TABLE|DPU0", "gnoi_halt_in_progress", "True")

    def test_set_module_gnoi_halt_in_progress_db_error(self):
        """Test setting gnoi_halt_in_progress flag when database error occurs"""
        db = MagicMock()
        self.module.state_db = db
        db.hset.side_effect = Exception("DB Error")

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module._set_module_gnoi_halt_in_progress() is False

    @pytest.mark.parametrize("module_name", ["DPU0", "DPU1", "LINE-CARD0", "SUPERVISOR0"])
    def test_set_module_gnoi_halt_in_progress_various_modules(self, module_name):
        """Test setting gnoi_halt_in_progress flag for various module types"""
        db = MagicMock()
        self.module.state_db = db

        with patch.object(self.module, "get_name", return_value=module_name), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module._set_module_gnoi_halt_in_progress() is True
            db.hset.assert_called_with(f"CHASSIS_MODULE_TABLE|{module_name}", "gnoi_halt_in_progress", "True")

    def test_set_module_gnoi_halt_in_progress_uses_lock(self):
        """Test that _set_module_gnoi_halt_in_progress uses transition lock"""
        db = MagicMock()
        self.module.state_db = db
        
        mock_lock = MagicMock()
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock", return_value=mock_lock):
            self.module._set_module_gnoi_halt_in_progress()
            mock_lock.__enter__.assert_called_once()
            mock_lock.__exit__.assert_called_once()

    def test_graceful_shutdown_handler_multiple_checks_before_clear(self):
        """Test graceful shutdown checks flag multiple times before clearing on timeout"""
        db = MagicMock()
        self.module.state_db = db
        # Flag remains set for 3 checks, then timeout
        db.hget.return_value = "True"

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_load_transition_timeouts", return_value={"halt_services": 15}), \
             patch("time.sleep"), \
             patch("time.time", side_effect=[1000, 1000, 1005, 1005, 1010, 1010, 1015, 1015, 1020]):
            assert self.module._graceful_shutdown_handler() is True
            # Should check flag at least 3 times before timeout
            assert db.hget.call_count >= 3
            db.hdel.assert_called_once()

    def test_graceful_shutdown_handler_flag_cleared_mid_loop(self):
        """Test graceful shutdown when flag is cleared after several iterations"""
        db = MagicMock()
        self.module.state_db = db
        # Flag set for first 2 checks, then cleared
        db.hget.side_effect = ["True", "True", None]

        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_load_transition_timeouts", return_value={"halt_services": 60}), \
             patch("time.sleep") as ms, \
             patch("time.time", side_effect=[1000, 1000, 1005, 1005, 1010, 1010, 1015]):
            assert self.module._graceful_shutdown_handler() is True
            # Should have slept twice before flag was cleared
            assert ms.call_count == 2
            # Should not clear flag when external process cleared it
            db.hdel.assert_not_called()

    # -------------------------------- set/get/clear transition flags -----------
    def _key(self, mod="DPU0"):
        return f"CHASSIS_MODULE_TABLE|{mod}"

    def test_set_module_state_transition_happy(self):
        db = MagicMock()
        self.module.state_db = db
        db.hget.return_value = None
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"), \
             patch("time.time", return_value=1000):
            assert self.module.set_module_state_transition("dpu0", "startup") is True
        db.hset.assert_has_calls([
            call(self._key("DPU0"), "transition_in_progress", "True"),
            call(self._key("DPU0"), "transition_type", "startup"),
            call(self._key("DPU0"), "transition_start_time", "1000"),
        ])

    def test_set_module_state_transition_within_timeout(self, capsys):
        db = MagicMock()
        self.module.state_db = db
        db.hget.side_effect = ["True", "950"]
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"), \
             patch.object(self.module, "_load_transition_timeouts", return_value={"startup": 300}), \
             patch("time.time", return_value=1000):
            assert self.module.set_module_state_transition("dpu0", "startup") is False
        assert "Transition already in progress" in capsys.readouterr().err
        db.hset.assert_not_called()

    @pytest.mark.parametrize("elapsed,timeout,expected", [(400, 300, True), (150, 300, False)])
    def test_set_module_state_transition_timeout_behavior(self, elapsed, timeout, expected):
        db = MagicMock()
        self.module.state_db = db
        db.hget.side_effect = ["True", str(1000 - elapsed)]
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"), \
             patch.object(self.module, "_load_transition_timeouts", return_value={"startup": timeout}), \
             patch("time.time", return_value=1000):
            assert self.module.set_module_state_transition("dpu0", "startup") is expected

    def test_set_module_state_transition_input_validation(self, capsys):
        db = MagicMock()
        self.module.state_db = db
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module.set_module_state_transition("dpu0", "invalid") is False
        assert "Invalid transition type: invalid" in capsys.readouterr().err

    def test_set_module_state_transition_missing_start_time(self, capsys):
        db = MagicMock()
        self.module.state_db = db
        db.hget.side_effect = ["True", None]
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module.set_module_state_transition("dpu0", "startup") is False
        assert "Missing start time" in capsys.readouterr().err

    def test_set_module_state_transition_db_errors(self, capsys):
        db = MagicMock()
        self.module.state_db = db

        db.hget.side_effect = Exception("DB Error")
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"):
            assert self.module.set_module_state_transition("dpu0", "startup") is False
        assert "Error setting transition flag for module DPU0: DB Error" in capsys.readouterr().err

        db.hget.side_effect = None
        db.hget.return_value = None
        db.hset.side_effect = Exception("DB Error")
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"), \
             patch("time.time", return_value=1000):
            assert self.module.set_module_state_transition("dpu0", "startup") is False

    @pytest.mark.parametrize("tt", ["startup", "shutdown", "reboot"])
    def test_set_module_state_transition_types(self, tt):
        db = MagicMock()
        self.module.state_db = db
        db.hget.return_value = None
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"), \
             patch("time.time", return_value=1000):
            assert self.module.set_module_state_transition("dpu0", tt) is True
        db.hset.assert_any_call(self._key("DPU0"), "transition_type", tt)

    # ---------------------------------------------------------- clear / get ----
    def test_clear_module_state_transition(self):
        db = MagicMock()
        self.module.state_db = db
        with patch.object(self.module, "_transition_operation_lock"), \
             patch.object(self.module, "get_name", return_value="DPU0"):
            assert self.module.clear_module_state_transition("dpu0") is True
        db.hdel.assert_has_calls([
            call(self._key("DPU0"), "transition_in_progress"),
            call(self._key("DPU0"), "transition_type"),
            call(self._key("DPU0"), "transition_start_time"),
        ])

    def test_clear_module_state_transition_db_error(self, capsys):
        db = MagicMock()
        self.module.state_db = db
        db.hdel.side_effect = Exception("DB Error")
        with patch.object(self.module, "_transition_operation_lock"), \
             patch.object(self.module, "get_name", return_value="DPU0"):
            assert self.module.clear_module_state_transition("dpu0") is False
        assert "Error clearing transition flag for module DPU0: DB Error" in capsys.readouterr().err

    @pytest.mark.parametrize("mod", ["DPU0", "LINE-CARD1", "SUPERVISOR0", "FABRIC-CARD0"])
    def test_clear_module_state_transition_various_modules(self, mod):
        db = MagicMock()
        self.module.state_db = db
        with patch.object(self.module, "_transition_operation_lock"), \
             patch.object(self.module, "get_name", return_value="DPU0"):
            assert self.module.clear_module_state_transition(mod.lower()) is True
        db.hdel.assert_any_call(self._key(mod), "transition_in_progress")

    @pytest.mark.parametrize("ret,expected", [("True", True), (None, False), ("False", False), ("weird", False)])
    def test_get_module_state_transition(self, ret, expected):
        db = MagicMock()
        self.module.state_db = db
        db.hget.return_value = ret
        with patch.object(self.module, "get_name", return_value="DPU0"):
            assert self.module.get_module_state_transition("dpu0") is expected
        db.hget.assert_called_with(self._key("DPU0"), "transition_in_progress")

    def test_get_module_state_transition_db_error(self, capsys):
        db = MagicMock()
        self.module.state_db = db
        db.hget.side_effect = Exception("DB Error")
        with patch.object(self.module, "get_name", return_value="DPU0"):
            assert self.module.get_module_state_transition("dpu0") is False

    @pytest.mark.parametrize("mod", ["DPU0", "LINE-CARD1", "SUPERVISOR0", "FABRIC-CARD0"])
    def test_get_module_state_transition_various_modules(self, mod):
        db = MagicMock()
        self.module.state_db = db
        db.hget.return_value = "True"
        with patch.object(self.module, "get_name", return_value=mod):
            assert self.module.get_module_state_transition(mod.lower()) is True
        db.hget.assert_called_with(self._key(mod), "transition_in_progress")

    # ---------------------------------- Edge timeout semantics coverage --------
    @pytest.mark.parametrize(
        "timeouts,hget_vals,now,expected",
        [
            ({"startup": 0, "shutdown": 0, "reboot": 0}, ["True", str(int(time.time()))], time.time() + 1, True),
            ({"startup": 999999999, "shutdown": 999999999, "reboot": 999999999}, ["True", "1"], 1_000_000, False),
            ({"startup": -1, "shutdown": -1, "reboot": -1}, ["True", str(int(time.time()))], time.time() + 1, True),
        ],
    )
    def test_transition_timeout_edge_cases(self, timeouts, hget_vals, now, expected):
        db = MagicMock()
        self.module.state_db = db
        db.hget.side_effect = hget_vals
        with patch.object(self.module, "get_name", return_value="DPU0"), \
             patch.object(self.module, "_transition_operation_lock"), \
             patch.object(self.module, "_load_transition_timeouts", return_value=timeouts), \
             patch("time.time", return_value=now):
            assert self.module.set_module_state_transition("dpu0", "startup") is expected
