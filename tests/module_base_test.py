import unittest
from unittest.mock import patch, MagicMock
from sonic_platform_base.module_base import ModuleBase
import pytest
import json
import os
import fcntl
from unittest.mock import patch, MagicMock, call
from io import StringIO
import shutil

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
        assert(module.get_num_voltage_sensors() == 0)
        assert(module.get_all_voltage_sensors() == [])
        assert(module.get_voltage_sensor(0) == None)
        module._voltage_sensor_list = ["s1"]
        assert(module.get_all_voltage_sensors() == ["s1"])
        assert(module.get_voltage_sensor(0) == "s1")
        assert(module.get_num_current_sensors() == 0)
        assert(module.get_all_current_sensors() == [])
        assert(module.get_current_sensor(0) == None)
        module._current_sensor_list = ["s1"]
        assert(module.get_all_current_sensors() == ["s1"])
        assert(module.get_current_sensor(0) == "s1")


class DummyModule(ModuleBase):
    def __init__(self, name="DPU0"):
        self.name = name

    def set_admin_state(self, up):
        return True  # Dummy override


class TestModuleBaseGracefulShutdown:

    @patch("sonic_platform_base.module_base.SonicV2Connector")
    def test_get_reboot_timeout_default(self, mock_db):
        mock_instance = mock_db.return_value
        mock_instance.get_entry.return_value = {'platform': 'x86_64-foo'}
        with patch("builtins.open", unittest.mock.mock_open(read_data='{}')):
            module = DummyModule()
            timeout = module.get_reboot_timeout()
            assert timeout == 60

    @patch("sonic_platform_base.module_base.SonicV2Connector")
    def test_graceful_shutdown_handler_success(self, mock_db):
        dpu_name = "DPU0"
        mock_instance = mock_db.return_value
        mock_instance.get_all.side_effect = [
            {},  # First poll
            {"start": "true", "status": "success", "message": "OK"}  # Second poll
        ]

        module = DummyModule(name=dpu_name)

        with patch.object(module, "get_reboot_timeout", return_value=10), \
             patch("time.sleep"):
            module.graceful_shutdown_handler()
            mock_instance.set_entry.assert_any_call("GNOI_REBOOT_RESULT", dpu_name, {"start": "false"})

    @patch("sonic_platform_base.module_base.SonicV2Connector")
    def test_graceful_shutdown_handler_timeout(self, mock_db):
        dpu_name = "DPU1"
        mock_instance = mock_db.return_value
        mock_instance.get_all.return_value = {}

        module = DummyModule(name=dpu_name)

        with patch.object(module, "get_reboot_timeout", return_value=5), \
             patch("time.sleep"):
            try:
                module.graceful_shutdown_handler()
            except TimeoutError as e:
                assert "timeout" in str(e).lower()

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
             patch('os.system') as mock_system:
            assert module.handle_sensor_removal() is True
            mock_copy.assert_called_once_with("/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf",
                                             "/etc/sensors.d/ignore_sensors_DPU0.conf")
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
