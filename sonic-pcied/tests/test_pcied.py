import os
import sys
from imp import load_source  # Replace with importlib once we no longer need to support Python 2

import pytest

# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock
from sonic_py_common import daemon_base, device_info

from .mock_platform import MockPcieUtil

tests_path = os.path.dirname(os.path.abspath(__file__))

# Add mocked_libs path so that the file under test can load mocked modules from there
mocked_libs_path = os.path.join(tests_path, "mocked_libs")
sys.path.insert(0, mocked_libs_path)

# Add path to the file under test so that we can load it
modules_path = os.path.dirname(tests_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)
load_source('pcied', os.path.join(scripts_path, 'pcied'))
import pcied


daemon_base.db_connect = mock.MagicMock()


SYSLOG_IDENTIFIER = 'pcied_test'
NOT_AVAILABLE = 'N/A'


@mock.patch('pcied.load_platform_pcieutil', mock.MagicMock())
@mock.patch('pcied.DaemonPcied.run')
def test_main(mock_run):
    mock_run.return_value = False

    pcied.main()
    assert mock_run.call_count == 1
