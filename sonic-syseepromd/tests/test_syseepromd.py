import os
import sys
from imp import load_source  # Replace with importlib once we no longer need to support Python 2

import pytest

# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock
from sonic_py_common import daemon_base

SYSLOG_IDENTIFIER = 'syseepromd_test'
NOT_AVAILABLE = 'N/A'

daemon_base.db_connect = mock.MagicMock()

tests_path = os.path.dirname(os.path.abspath(__file__))

# Add mocked_libs path so that the file under test can load mocked modules from there
mocked_libs_path = os.path.join(tests_path, 'mocked_libs')
sys.path.insert(0, mocked_libs_path)

# Add path to the file under test so that we can load it
modules_path = os.path.dirname(tests_path)
scripts_path = os.path.join(modules_path, 'scripts')
sys.path.insert(0, modules_path)

load_source('syseepromd', os.path.join(scripts_path, 'syseepromd'))
import syseepromd


def test_post_eeprom_to_db_eeprom_read_fail():
    daemon_syseepromd = syseepromd.DaemonSyseeprom()
    daemon_syseepromd.eeprom.read_eeprom = mock.MagicMock(return_value=None)
    daemon_syseepromd.eeprom_tbl = mock.MagicMock()
    daemon_syseepromd.log_error = mock.MagicMock()

    ret = daemon_syseepromd.post_eeprom_to_db()
    assert ret == syseepromd.ERR_FAILED_EEPROM
    assert daemon_syseepromd.log_error.call_count == 1
    daemon_syseepromd.log_error.assert_called_with('Failed to read EEPROM')
    assert daemon_syseepromd.eeprom_tbl.getKeys.call_count == 0


def test_post_eeprom_to_db_update_fail():
    daemon_syseepromd = syseepromd.DaemonSyseeprom()
    daemon_syseepromd.eeprom.update_eeprom_db = mock.MagicMock(return_value=1)
    daemon_syseepromd.eeprom_tbl = mock.MagicMock()
    daemon_syseepromd.log_error = mock.MagicMock()

    ret = daemon_syseepromd.post_eeprom_to_db()
    assert ret == syseepromd.ERR_FAILED_UPDATE_DB
    assert daemon_syseepromd.log_error.call_count == 1
    daemon_syseepromd.log_error.assert_called_with('Failed to update EEPROM info in database')
    assert daemon_syseepromd.eeprom_tbl.getKeys.call_count == 0


def test_post_eeprom_to_db_ok():
    daemon_syseepromd = syseepromd.DaemonSyseeprom()
    daemon_syseepromd.eeprom.update_eeprom_db = mock.MagicMock(return_value=0)
    daemon_syseepromd.eeprom_tbl = mock.MagicMock()
    daemon_syseepromd.log_error = mock.MagicMock()

    ret = daemon_syseepromd.post_eeprom_to_db()
    assert ret == syseepromd.ERR_NONE
    assert daemon_syseepromd.log_error.call_count == 0
    assert daemon_syseepromd.eeprom_tbl.getKeys.call_count == 1


def test_clear_db():
    daemon_syseepromd = syseepromd.DaemonSyseeprom()
    daemon_syseepromd.eeprom_tbl.getKeys = mock.MagicMock(return_value=['key1', 'key2'])
    daemon_syseepromd.eeprom_tbl._del = mock.MagicMock()

    daemon_syseepromd.clear_db()
    assert daemon_syseepromd.eeprom_tbl.getKeys.call_count == 1
    assert daemon_syseepromd.eeprom_tbl._del.call_count == 2


def test_detect_eeprom_table_integrity():
    daemon_syseepromd = syseepromd.DaemonSyseeprom()

    # Test entries as expected
    daemon_syseepromd.eeprom_tbl.getKeys = mock.MagicMock(return_value=['key1', 'key2'])
    daemon_syseepromd.eepromtbl_keys = ['key1', 'key2']
    ret = daemon_syseepromd.detect_eeprom_table_integrity()
    assert ret == True

    # Test differing amounts of entries
    daemon_syseepromd.eeprom_tbl.getKeys = mock.MagicMock(return_value=['key1', 'key2'])
    daemon_syseepromd.eepromtbl_keys = ['key1']
    ret = daemon_syseepromd.detect_eeprom_table_integrity()
    assert ret == False

    # Test same amount of entries, but with different keys
    daemon_syseepromd.eeprom_tbl.getKeys = mock.MagicMock(return_value=['key1', 'key2'])
    daemon_syseepromd.eepromtbl_keys = ['key1', 'key3']
    ret = daemon_syseepromd.detect_eeprom_table_integrity()
    assert ret == False


def test_signal_handler():
    daemon_syseepromd = syseepromd.DaemonSyseeprom()
    daemon_syseepromd.stop_event.set = mock.MagicMock()
    daemon_syseepromd.log_info = mock.MagicMock()
    daemon_syseepromd.log_warning = mock.MagicMock()

    # Test SIGHUP
    daemon_syseepromd.signal_handler(syseepromd.signal.SIGHUP, None)
    assert daemon_syseepromd.log_info.call_count == 1
    daemon_syseepromd.log_info.assert_called_with("Caught signal 'SIGHUP' - ignoring...")
    assert daemon_syseepromd.log_warning.call_count == 0
    assert daemon_syseepromd.stop_event.set.call_count == 0
    assert syseepromd.exit_code == 0

    # Reset
    daemon_syseepromd.log_info.reset_mock()
    daemon_syseepromd.log_warning.reset_mock()
    daemon_syseepromd.stop_event.set.reset_mock()

    # Test SIGINT
    test_signal = syseepromd.signal.SIGINT
    daemon_syseepromd.signal_handler(test_signal, None)
    assert daemon_syseepromd.log_info.call_count == 1
    daemon_syseepromd.log_info.assert_called_with("Caught signal 'SIGINT' - exiting...")
    assert daemon_syseepromd.log_warning.call_count == 0
    assert daemon_syseepromd.stop_event.set.call_count == 1
    assert syseepromd.exit_code == (128 + test_signal)

    # Reset
    daemon_syseepromd.log_info.reset_mock()
    daemon_syseepromd.log_warning.reset_mock()
    daemon_syseepromd.stop_event.set.reset_mock()

    # Test SIGTERM
    test_signal = syseepromd.signal.SIGTERM
    daemon_syseepromd.signal_handler(test_signal, None)
    assert daemon_syseepromd.log_info.call_count == 1
    daemon_syseepromd.log_info.assert_called_with("Caught signal 'SIGTERM' - exiting...")
    assert daemon_syseepromd.log_warning.call_count == 0
    assert daemon_syseepromd.stop_event.set.call_count == 1
    assert syseepromd.exit_code == (128 + test_signal)

    # Reset
    daemon_syseepromd.log_info.reset_mock()
    daemon_syseepromd.log_warning.reset_mock()
    daemon_syseepromd.stop_event.set.reset_mock()
    syseepromd.exit_code = 0

    # Test an unhandled signal
    daemon_syseepromd.signal_handler(syseepromd.signal.SIGUSR1, None)
    assert daemon_syseepromd.log_warning.call_count == 1
    daemon_syseepromd.log_warning.assert_called_with("Caught unhandled signal 'SIGUSR1' - ignoring...")
    assert daemon_syseepromd.log_info.call_count == 0
    assert daemon_syseepromd.stop_event.set.call_count == 0
    assert syseepromd.exit_code == 0


@mock.patch('syseepromd.EEPROM_INFO_UPDATE_PERIOD_SECS', 1)
def test_run():
    daemon_syseepromd = syseepromd.DaemonSyseeprom()
    daemon_syseepromd.clear_db = mock.MagicMock()
    daemon_syseepromd.log_info = mock.MagicMock()
    daemon_syseepromd.log_error = mock.MagicMock()
    daemon_syseepromd.post_eeprom_to_db = mock.MagicMock(return_value=syseepromd.ERR_NONE)

    # Test no change to EEPROM data
    daemon_syseepromd.detect_eeprom_table_integrity = mock.MagicMock(return_value=True)

    ret = daemon_syseepromd.run()
    assert ret == True
    assert daemon_syseepromd.detect_eeprom_table_integrity.call_count == 1
    assert daemon_syseepromd.log_info.call_count == 0
    assert daemon_syseepromd.log_error.call_count == 0
    assert daemon_syseepromd.clear_db.call_count == 0
    assert daemon_syseepromd.post_eeprom_to_db.call_count == 0

    # Reset mocks
    daemon_syseepromd.detect_eeprom_table_integrity.reset_mock()

    # Test EEPROM data has changed, update succeeds
    daemon_syseepromd.detect_eeprom_table_integrity = mock.MagicMock(return_value=False)

    ret = daemon_syseepromd.run()
    assert ret == True
    assert daemon_syseepromd.detect_eeprom_table_integrity.call_count == 1
    assert daemon_syseepromd.log_info.call_count == 1
    daemon_syseepromd.log_info.assert_called_with('System EEPROM table was changed, needs update')
    assert daemon_syseepromd.clear_db.call_count == 1
    assert daemon_syseepromd.post_eeprom_to_db.call_count == 1
    assert daemon_syseepromd.log_error.call_count == 0

    # Reset mocks
    daemon_syseepromd.detect_eeprom_table_integrity.reset_mock()
    daemon_syseepromd.log_info.reset_mock()
    daemon_syseepromd.clear_db.reset_mock()
    daemon_syseepromd.post_eeprom_to_db.reset_mock()

    # Test EEPROM data has changed, update fails
    daemon_syseepromd.detect_eeprom_table_integrity = mock.MagicMock(return_value=False)
    daemon_syseepromd.post_eeprom_to_db = mock.MagicMock(return_value=syseepromd.ERR_FAILED_UPDATE_DB)

    ret = daemon_syseepromd.run()
    assert ret == True
    assert daemon_syseepromd.detect_eeprom_table_integrity.call_count == 1
    assert daemon_syseepromd.log_info.call_count == 1
    daemon_syseepromd.log_info.assert_called_with('System EEPROM table was changed, needs update')
    assert daemon_syseepromd.clear_db.call_count == 1
    assert daemon_syseepromd.post_eeprom_to_db.call_count == 1
    assert daemon_syseepromd.log_error.call_count == 1
    daemon_syseepromd.log_error.assert_called_with('Failed to post EEPROM to database')


@mock.patch('syseepromd.DaemonSyseeprom.run')
def test_main(mock_run):
    mock_run.return_value = False

    syseepromd.main()
    assert mock_run.call_count == 1
