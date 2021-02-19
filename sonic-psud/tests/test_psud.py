import os
import sys
from imp import load_source

import pytest

# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock
from sonic_py_common import daemon_base

from . import mock_swsscommon
from .mock_platform import MockChassis, MockPsu, MockFanDrawer, MockModule

SYSLOG_IDENTIFIER = 'psud_test'
NOT_AVAILABLE = 'N/A'

daemon_base.db_connect = mock.MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)

os.environ["PSUD_UNIT_TESTING"] = "1"
load_source('psud', scripts_path + '/psud')
import psud

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


@mock.patch('psud._wrapper_get_psu_presence', mock.MagicMock())
@mock.patch('psud._wrapper_get_psu_status', mock.MagicMock())
def test_psu_db_update():
    psu_tbl = mock.MagicMock()

    psud._wrapper_get_psu_presence.return_value = True
    psud._wrapper_get_psu_status.return_value = True
    expected_fvp = psud.swsscommon.FieldValuePairs(
        [(psud.PSU_INFO_PRESENCE_FIELD, 'true'),
         (psud.PSU_INFO_STATUS_FIELD, 'true'),
         ])
    psud.psu_db_update(psu_tbl, 1)
    assert psu_tbl.set.call_count == 1
    psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(1), expected_fvp)

    psu_tbl.set.reset_mock()

    psud._wrapper_get_psu_presence.return_value = False
    psud._wrapper_get_psu_status.return_value = True
    expected_fvp = psud.swsscommon.FieldValuePairs(
        [(psud.PSU_INFO_PRESENCE_FIELD, 'false'),
         (psud.PSU_INFO_STATUS_FIELD, 'true'),
         ])
    psud.psu_db_update(psu_tbl, 1)
    assert psu_tbl.set.call_count == 1
    psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(1), expected_fvp)

    psu_tbl.set.reset_mock()

    psud._wrapper_get_psu_presence.return_value = True
    psud._wrapper_get_psu_status.return_value = False
    expected_fvp = psud.swsscommon.FieldValuePairs(
        [(psud.PSU_INFO_PRESENCE_FIELD, 'true'),
         (psud.PSU_INFO_STATUS_FIELD, 'false'),
         ])
    psud.psu_db_update(psu_tbl, 1)
    assert psu_tbl.set.call_count == 1
    psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(1), expected_fvp)

    psu_tbl.set.reset_mock()

    psud._wrapper_get_psu_presence.return_value = False
    psud._wrapper_get_psu_status.return_value = False
    expected_fvp = psud.swsscommon.FieldValuePairs(
        [(psud.PSU_INFO_PRESENCE_FIELD, 'false'),
         (psud.PSU_INFO_STATUS_FIELD, 'false'),
         ])
    psud.psu_db_update(psu_tbl, 1)
    assert psu_tbl.set.call_count == 1
    psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(1), expected_fvp)

    psu_tbl.set.reset_mock()

    psud._wrapper_get_psu_presence.return_value = True
    psud._wrapper_get_psu_status.return_value = True
    expected_fvp = psud.swsscommon.FieldValuePairs(
        [(psud.PSU_INFO_PRESENCE_FIELD, 'true'),
         (psud.PSU_INFO_STATUS_FIELD, 'true'),
         ])
    psud.psu_db_update(psu_tbl, 32)
    assert psu_tbl.set.call_count == 32
    psu_tbl.set.assert_called_with(psud.PSU_INFO_KEY_TEMPLATE.format(32), expected_fvp)


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
