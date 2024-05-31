import datetime
import os
import sys
from imp import load_source

# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info.major == 3:
    from unittest.mock import patch, MagicMock, mock_open
else:
    from mock import patch, MagicMock, mock_open

# Add mocked_libs path so that the file under test can load mocked modules from there
tests_path = os.path.dirname(os.path.abspath(__file__))
mocked_libs_path = os.path.join(tests_path, "mocked_libs")
sys.path.insert(0, mocked_libs_path)

from .mocked_libs.swsscommon import swsscommon
from sonic_py_common import daemon_base

# Add path to the file under test so that we can load it
modules_path = os.path.dirname(tests_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)
load_source('stormond', os.path.join(scripts_path, 'stormond'))

import stormond
import pytest


log_identifier = 'storage_daemon_test'


#daemon_base.db_connect = MagicMock()

config_intvls = '''
daemon_polling_interval,
60,
fsstats_sync_interval,
300
'''

fsio_dict = {"total_fsio_reads": "", "total_fsio_writes": "", "latest_fsio_reads": "1000", "latest_fsio_writes": "2000"}
fsio_json_dict = { 'sda' : {"total_fsio_reads": "10500", "total_fsio_writes": "21000", "latest_fsio_reads": "1000", "latest_fsio_writes": "2000"}}
bad_fsio_json_dict = { 'sda' : {"total_fsio_reads": None, "total_fsio_writes": "21000", "latest_fsio_reads": "1000", "latest_fsio_writes": "2000"}}
fsio_statedb_dict = { 'sda' : {"total_fsio_reads": "10500", "total_fsio_writes": "21000", "latest_fsio_reads": "200", "latest_fsio_writes": "400"}}

dynamic_dict = {'firmware': 'ILLBBK', 'health': '40', 'temperature': '5000', 'latest_fsio_reads': '150', 'latest_fsio_writes': '270', 'disk_io_reads': '1000', 'disk_io_writes': '2000', 'reserved_blocks': '3'}

class TestDaemonStorage(object):
    """
    Test cases to cover functionality in DaemonStorage class
    """

    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_default_configdb_intervals_no_config(self):

        stormon_daemon = stormond.DaemonStorage(log_identifier)

        assert (stormon_daemon.timeout) == 3600
        assert (stormon_daemon.fsstats_sync_interval) == 86400

    
    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_storage_devices(self):

        def new_mock_factory(self, key):
            return MagicMock()

        with patch('sonic_platform_base.sonic_storage.storage_devices.StorageDevices._storage_device_object_factory', new=new_mock_factory):

            stormon_daemon = stormond.DaemonStorage(log_identifier)

            assert(list(stormon_daemon.storage.devices.keys()) == ['sda'])

    @patch('os.path.exists', MagicMock(return_value=True))
    @patch('json.load', MagicMock(return_value=bad_fsio_json_dict))
    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_load_fsio_rw_json_false(self):

        with patch('builtins.open', new_callable=mock_open, read_data='{}') as mock_fd:
            stormon_daemon = stormond.DaemonStorage(log_identifier)

            assert stormon_daemon.fsio_json_file_loaded == False
    
    @patch('os.path.exists', MagicMock(return_value=True))
    @patch('json.load', MagicMock(return_value=fsio_json_dict))
    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_load_fsio_rw_json_true(self):

        with patch('builtins.open', new_callable=mock_open, read_data='{}') as mock_fd:
            stormon_daemon = stormond.DaemonStorage(log_identifier)

            assert stormon_daemon.fsio_json_file_loaded == True


    @patch('os.path.exists', MagicMock(return_value=True))
    @patch('json.load', MagicMock(side_effect=Exception))
    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_load_fsio_rw_json_exception(self):

        with patch('builtins.open', new_callable=mock_open, read_data='{}') as mock_fd:
            stormon_daemon = stormond.DaemonStorage(log_identifier)

            assert stormon_daemon.fsio_json_file_loaded == False
    
    @patch('sonic_py_common.daemon_base.db_connect')
    def testget_configdb_intervals(self, mock_daemon_base):

        mock_daemon_base = MagicMock()

        stormon_daemon = stormond.DaemonStorage(log_identifier)
        stormon_daemon.get_configdb_intervals()

        assert mock_daemon_base.call_count == 0

            
    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    @patch('json.dump', MagicMock())
    def test_sync_fsio_rw_json_exception(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)

        with patch('builtins.open', new_callable=mock_open, read_data='{}') as mock_fd:
            stormon_daemon.sync_fsio_rw_json()

            assert stormon_daemon.state_db.call_count == 0

    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    @patch('json.dump', MagicMock())
    @patch('time.time', MagicMock(return_value=1000))
    def test_sync_fsio_rw_json_happy(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)

        with patch('builtins.open', new_callable=mock_open, read_data='{}') as mock_fd:
            stormon_daemon.sync_fsio_rw_json()

            assert stormon_daemon.state_db.call_count == 0

    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_reconcile_fsio_rw_values_init(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)
        stormon_daemon.use_statedb_baseline = False
        stormon_daemon.use_fsio_json_baseline = False

        (reads, writes) = stormon_daemon._reconcile_fsio_rw_values(fsio_dict, MagicMock())

        assert reads == '1000'
        assert writes == '2000'


    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_reconcile_fsio_rw_values_reboot(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)
        
        stormon_daemon.use_statedb_baseline = False
        stormon_daemon.use_fsio_json_baseline = True
        stormon_daemon.fsio_rw_json = fsio_json_dict

        (reads, writes) = stormon_daemon._reconcile_fsio_rw_values(fsio_dict, 'sda')

        assert reads == '11500'
        assert writes == '23000'


    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_reconcile_fsio_rw_values_daemon_crash(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)
        
        stormon_daemon.use_statedb_baseline = True
        stormon_daemon.use_fsio_json_baseline = True
        stormon_daemon.fsio_rw_statedb = fsio_statedb_dict

        (reads, writes) = stormon_daemon._reconcile_fsio_rw_values(fsio_dict, 'sda')

        assert reads == '11300'
        assert writes == '22600'
    
    
    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_update_storage_info_status_db(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)

        stormon_daemon.update_storage_info_status_db('sda', fsio_json_dict['sda'])

        assert stormon_daemon.device_table.getKeys() == ['sda']
    

    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_get_static_fields(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)

        mock_storage_device_object = MagicMock()
        mock_storage_device_object.get_model.return_value = "Skynet"
        mock_storage_device_object.get_serial.return_value = "T1000"

        stormon_daemon.storage.devices = {'sda' : mock_storage_device_object}
        stormon_daemon.get_static_fields_update_state_db()

        assert stormon_daemon.device_table.getKeys() == ['sda']
        assert stormon_daemon.device_table.get('sda') == {'device_model': 'Skynet', 'serial': 'T1000'}


    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_get_dynamic_fields(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)

        mock_storage_device_object = MagicMock()
        mock_storage_device_object.get_firmware.return_value = "ILLBBK"
        mock_storage_device_object.get_health.return_value = "40"
        mock_storage_device_object.get_temperature.return_value = "5000"
        mock_storage_device_object.get_fs_io_reads.return_value = "150"
        mock_storage_device_object.get_fs_io_writes.return_value = "270"
        mock_storage_device_object.get_disk_io_reads.return_value = "1000"
        mock_storage_device_object.get_disk_io_writes.return_value = "2000"
        mock_storage_device_object.get_reserved_blocks.return_value = "3"

        stormon_daemon.storage.devices = {'sda' : mock_storage_device_object}
        stormon_daemon.get_dynamic_fields_update_state_db()

        assert stormon_daemon.device_table.getKeys() == ['sda']
        for field, value in dynamic_dict.items():
            assert stormon_daemon.device_table.get('sda')[field] == value
    
    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    @patch('json.dump', MagicMock())
    @patch('time.time', MagicMock(return_value=1000))
    def test_write_sync_time_statedb(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)
        stormon_daemon.sync_fsio_rw_json = MagicMock(return_value=True)

        stormon_daemon.write_sync_time_statedb()
        assert stormon_daemon.state_db.call_count == 0


    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_signal_handler(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)
        stormon_daemon.sync_fsio_rw_json = MagicMock()

        stormon_daemon.stop_event.set = MagicMock()
        stormon_daemon.log_info = MagicMock()
        stormon_daemon.log_warning = MagicMock()

        # Test SIGHUP
        stormon_daemon.signal_handler(stormond.signal.SIGHUP, None)
        assert stormon_daemon.log_info.call_count == 1
        stormon_daemon.log_info.assert_called_with("Caught signal 'SIGHUP' - ignoring...")
        assert stormon_daemon.log_warning.call_count == 0
        assert stormon_daemon.stop_event.set.call_count == 0
        assert stormond.exit_code == 0

        # Reset
        stormon_daemon.log_info.reset_mock()
        stormon_daemon.log_warning.reset_mock()
        stormon_daemon.stop_event.set.reset_mock()

        # Test SIGINT
        test_signal = stormond.signal.SIGINT
        stormon_daemon.signal_handler(test_signal, None)
        assert stormon_daemon.log_info.call_count == 2
        stormon_daemon.log_info.assert_called_with("Exiting with SIGINT")
        assert stormon_daemon.log_warning.call_count == 0
        assert stormon_daemon.stop_event.set.call_count == 1
        assert stormond.exit_code == (128 + test_signal)

        # Reset
        stormon_daemon.log_info.reset_mock()
        stormon_daemon.log_warning.reset_mock()
        stormon_daemon.stop_event.set.reset_mock()

        # Test SIGTERM
        test_signal = stormond.signal.SIGTERM
        stormon_daemon.signal_handler(test_signal, None)
        assert stormon_daemon.log_info.call_count == 2
        stormon_daemon.log_info.assert_called_with("Exiting with SIGTERM")
        assert stormon_daemon.log_warning.call_count == 0
        assert stormon_daemon.stop_event.set.call_count == 1
        assert stormond.exit_code == (128 + test_signal)

        # Reset
        stormon_daemon.log_info.reset_mock()
        stormon_daemon.log_warning.reset_mock()
        stormon_daemon.stop_event.set.reset_mock()
        stormond.exit_code = 0

        # Test an unhandled signal
        stormon_daemon.signal_handler(stormond.signal.SIGUSR1, None)
        assert stormon_daemon.log_warning.call_count == 1
        stormon_daemon.log_warning.assert_called_with("Caught unhandled signal 'SIGUSR1' - ignoring...")
        assert stormon_daemon.log_info.call_count == 0
        assert stormon_daemon.stop_event.set.call_count == 0
        assert stormond.exit_code == 0


    @patch('sonic_py_common.daemon_base.db_connect', MagicMock())
    def test_run(self):
        stormon_daemon = stormond.DaemonStorage(log_identifier)
        stormon_daemon.get_dynamic_fields_update_state_db = MagicMock()

        def mock_intervals():
            stormon_daemon.timeout = 10
            stormon_daemon.fsstats_sync_interval = 30

        with patch.object(stormon_daemon, 'get_configdb_intervals', new=mock_intervals):
            stormon_daemon.run()

            assert stormon_daemon.get_dynamic_fields_update_state_db.call_count == 1


