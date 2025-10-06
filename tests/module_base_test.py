from sonic_platform_base.module_base import ModuleBase
import pytest
import json
import os
import fcntl
from unittest.mock import patch, MagicMock, call
from io import StringIO
import subprocess

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

    def test_is_host_detection(self):
        # Test when /.dockerenv does not exist - running on host
        with patch('os.path.exists', return_value=False):
            module = ModuleBase()
            assert module.is_host is True

        # Test when /.dockerenv exists - running in container (inside pmon)
        with patch('os.path.exists', return_value=True):
            module = ModuleBase()
            assert module.is_host is False

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

        # Test successful case on host - commands run via docker exec pmon to access container
        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            module.is_host = True
            # First call to test -f (file exists) returns 0, second call is cp, third is service restart
            mock_call.side_effect = [0, 0, 0]
            assert module.handle_sensor_removal() is True
            assert mock_call.call_count == 3
            # When on host, commands are prefixed with docker exec pmon to run inside container
            mock_call.assert_any_call(['docker', 'exec', 'pmon', 'test', '-f', '/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf'],
                                      stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(['docker', 'exec', 'pmon', 'cp', '/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf',
                                      '/etc/sensors.d/ignore_sensors_DPU0.conf'], 
                                      stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(['docker', 'exec', 'pmon', 'service', 'sensord', 'restart'],
                                      stdout=subprocess.DEVNULL)
            mock_lock.assert_called_once()

        # Test successful case inside container - commands run directly without docker exec
        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            module.is_host = False
            # First call to test -f (file exists) returns 0, second call is cp, third is service restart
            mock_call.side_effect = [0, 0, 0]
            assert module.handle_sensor_removal() is True
            assert mock_call.call_count == 3
            # When inside container, commands run directly without docker exec prefix
            mock_call.assert_any_call(['test', '-f', '/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf'],
                                      stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(['cp', '/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf',
                                      '/etc/sensors.d/ignore_sensors_DPU0.conf'], 
                                      stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(['service', 'sensord', 'restart'],
                                      stdout=subprocess.DEVNULL)
            mock_lock.assert_called_once()

        # Test file does not exist - should return True but not call copy or restart
        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            module.is_host = True
            # Return 1 to indicate file doesn't exist
            mock_call.return_value = 1
            assert module.handle_sensor_removal() is True
            # Only the file existence check should be called (with docker exec when on host)
            mock_call.assert_called_once_with(['docker', 'exec', 'pmon', 'test', '-f', '/usr/share/sonic/platform/module_sensors_ignore_conf/ignore_sensors_DPU0.conf'],
                                             stdout=subprocess.DEVNULL)
            mock_lock.assert_not_called()

        # Test exception handling
        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('subprocess.call', side_effect=Exception("Copy failed")):
            module.is_host = True
            assert module.handle_sensor_removal() is False

    def test_handle_sensor_addition(self):
        module = ModuleBase()

        # Test successful case on host - commands run via docker exec pmon to access container
        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            module.is_host = True
            # First call to test -f (file exists) returns 0, second call is rm, third is service restart
            mock_call.side_effect = [0, 0, 0]
            assert module.handle_sensor_addition() is True
            assert mock_call.call_count == 3
            # When on host, commands are prefixed with docker exec pmon to run inside container
            mock_call.assert_any_call(['docker', 'exec', 'pmon', 'test', '-f', '/etc/sensors.d/ignore_sensors_DPU0.conf'],
                                      stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(['docker', 'exec', 'pmon', 'rm', '/etc/sensors.d/ignore_sensors_DPU0.conf'],
                                      stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(['docker', 'exec', 'pmon', 'service', 'sensord', 'restart'],
                                      stdout=subprocess.DEVNULL)
            mock_lock.assert_called_once()

        # Test successful case inside container - commands run directly without docker exec
        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            module.is_host = False
            # First call to test -f (file exists) returns 0, second call is rm, third is service restart
            mock_call.side_effect = [0, 0, 0]
            assert module.handle_sensor_addition() is True
            assert mock_call.call_count == 3
            # When inside container, commands run directly without docker exec prefix
            mock_call.assert_any_call(['test', '-f', '/etc/sensors.d/ignore_sensors_DPU0.conf'],
                                      stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(['rm', '/etc/sensors.d/ignore_sensors_DPU0.conf'],
                                      stdout=subprocess.DEVNULL)
            mock_call.assert_any_call(['service', 'sensord', 'restart'],
                                      stdout=subprocess.DEVNULL)
            mock_lock.assert_called_once()

        # Test file does not exist - should return True but not call remove or restart
        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('subprocess.call') as mock_call, \
             patch.object(module, '_sensord_operation_lock') as mock_lock:
            module.is_host = True
            # Return 1 to indicate file doesn't exist
            mock_call.return_value = 1
            assert module.handle_sensor_addition() is True
            # Only the file existence check should be called (with docker exec when on host)
            mock_call.assert_called_once_with(['docker', 'exec', 'pmon', 'test', '-f', '/etc/sensors.d/ignore_sensors_DPU0.conf'],
                                             stdout=subprocess.DEVNULL)
            mock_lock.assert_not_called()

        # Test exception handling
        with patch.object(module, 'get_name', return_value="DPU0"), \
             patch('subprocess.call', side_effect=Exception("Remove failed")):
            module.is_host = True
            assert module.handle_sensor_addition() is False

    def test_module_pre_shutdown(self):
        module = ModuleBase()

        # Test successful case
        with patch.object(module, 'handle_sensor_removal', return_value=True) as mock_sensor, \
             patch.object(module, 'handle_pci_removal', return_value=True) as mock_pci:
            assert module.module_pre_shutdown() is True
            # Verify sensor removal is called before PCI removal
            mock_sensor.assert_called_once()
            mock_pci.assert_called_once()

        # Test sensor removal failure
        with patch.object(module, 'handle_sensor_removal', return_value=False), \
             patch.object(module, 'handle_pci_removal', return_value=True):
            assert module.module_pre_shutdown() is False

        # Test PCI removal failure
        with patch.object(module, 'handle_sensor_removal', return_value=True), \
             patch.object(module, 'handle_pci_removal', return_value=False):
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
