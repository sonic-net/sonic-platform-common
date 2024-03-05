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

from .mock_platform import MockPsu, MockChassis

tests_path = os.path.dirname(os.path.abspath(__file__))

# Add mocked_libs path so that the file under test can load mocked modules from there
mocked_libs_path = os.path.join(tests_path, "mocked_libs")
sys.path.insert(0, mocked_libs_path)

# Add path to the file under test so that we can load it
modules_path = os.path.dirname(tests_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)
load_source('psud', os.path.join(scripts_path, 'psud'))
import psud


daemon_base.db_connect = mock.MagicMock()


SYSLOG_IDENTIFIER = 'psud_test'
NOT_AVAILABLE = 'N/A'


@mock.patch('psud.platform_chassis', mock.MagicMock())
@mock.patch('psud.platform_psuutil', mock.MagicMock())
def test_wrapper_get_num_psus():
    # Test new platform API is available and implemented
    psud._wrapper_get_num_psus()
    assert psud.platform_chassis.get_num_psus.call_count == 1
    assert psud.platform_psuutil.get_num_psus.call_count == 0

    # Test new platform API is available but not implemented
    psud.platform_chassis.get_num_psus.side_effect = NotImplementedError
    psud._wrapper_get_num_psus()
    assert psud.platform_chassis.get_num_psus.call_count == 2
    assert psud.platform_psuutil.get_num_psus.call_count == 1

    # Test new platform API not available
    psud.platform_chassis = None
    psud._wrapper_get_num_psus()
    assert psud.platform_psuutil.get_num_psus.call_count == 2


@mock.patch('psud.platform_chassis', mock.MagicMock())
@mock.patch('psud.platform_psuutil', mock.MagicMock())
def test_wrapper_get_psu_presence():
    # Test new platform API is available
    psud._wrapper_get_psu_presence(1)
    assert psud.platform_chassis.get_psu(0).get_presence.call_count == 1
    assert psud.platform_psuutil.get_psu_presence.call_count == 0

    # Test new platform API is available but not implemented
    psud.platform_chassis.get_psu(0).get_presence.side_effect = NotImplementedError
    psud._wrapper_get_psu_presence(1)
    assert psud.platform_chassis.get_psu(0).get_presence.call_count == 2
    assert psud.platform_psuutil.get_psu_presence.call_count == 1

    # Test new platform API not available
    psud.platform_chassis = None
    psud._wrapper_get_psu_presence(1)
    assert psud.platform_psuutil.get_psu_presence.call_count == 2
    psud.platform_psuutil.get_psu_presence.assert_called_with(1)


@mock.patch('psud.platform_chassis', mock.MagicMock())
@mock.patch('psud.platform_psuutil', mock.MagicMock())
def test_wrapper_get_psu_status():
    # Test new platform API is available
    psud._wrapper_get_psu_status(1)
    assert psud.platform_chassis.get_psu(0).get_powergood_status.call_count == 1
    assert psud.platform_psuutil.get_psu_status.call_count == 0

    # Test new platform API is available but not implemented
    psud.platform_chassis.get_psu(0).get_powergood_status.side_effect = NotImplementedError
    psud._wrapper_get_psu_status(1)
    assert psud.platform_chassis.get_psu(0).get_powergood_status.call_count == 2
    assert psud.platform_psuutil.get_psu_status.call_count == 1

    # Test new platform API not available
    psud.platform_chassis = None
    psud._wrapper_get_psu_status(1)
    assert psud.platform_psuutil.get_psu_status.call_count == 2
    psud.platform_psuutil.get_psu_status.assert_called_with(1)


def test_log_on_status_changed():
    normal_log = "Normal log message"
    abnormal_log = "Abnormal log message"

    mock_logger = mock.MagicMock()

    psud.log_on_status_changed(mock_logger, True, normal_log, abnormal_log)
    assert mock_logger.log_notice.call_count == 1
    assert mock_logger.log_warning.call_count == 0
    mock_logger.log_notice.assert_called_with(normal_log)

    mock_logger.log_notice.reset_mock()

    psud.log_on_status_changed(mock_logger, False, normal_log, abnormal_log)
    assert mock_logger.log_notice.call_count == 0
    assert mock_logger.log_warning.call_count == 1
    mock_logger.log_warning.assert_called_with(abnormal_log)


@mock.patch('psud.platform_chassis', mock.MagicMock())
@mock.patch('psud.DaemonPsud.run')
def test_main(mock_run):
    mock_run.return_value = False

    psud.main()
    assert mock_run.call_count == 1
