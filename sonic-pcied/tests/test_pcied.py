import os
import sys
from imp import load_source  # Replace with importlib once we no longer need to support Python 2

import pytest

# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info >= (3, 3):
    from unittest.mock import MagicMock, patch, mock_open
else:
    from mock import MagicMock, patch, mock_open

from .mock_platform import MockPcieUtil

tests_path = os.path.dirname(os.path.abspath(__file__))

# Add mocked_libs path so that the file under test can load mocked modules from there
mocked_libs_path = os.path.join(tests_path, "mocked_libs")
sys.path.insert(0, mocked_libs_path)
from sonic_py_common import daemon_base, device_info

# Add path to the file under test so that we can load it
modules_path = os.path.dirname(tests_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)
load_source('pcied', os.path.join(scripts_path, 'pcied'))
import pcied


daemon_base.db_connect = MagicMock()

SYSLOG_IDENTIFIER = 'pcied_test'
NOT_AVAILABLE = 'N/A'


@patch('pcied.load_platform_pcieutil', MagicMock())
@patch('pcied.DaemonPcied.run')
def test_main(mock_run):
    mock_run.return_value = False

    pcied.main()
    assert mock_run.call_count == 1


@patch('pcied.os.path.exists', MagicMock(return_value=True))
def test_read_id_file():

    device_name = "test"

    with patch('builtins.open', new_callable=mock_open, read_data='15') as mock_fd:
        rc = pcied.read_id_file(device_name)
        assert rc == "15"

@patch('pcied.device_info.get_paths_to_platform_and_hwsku_dirs', MagicMock(return_value=('/tmp', None)))
def test_load_platform_pcieutil():
    from sonic_platform_base.sonic_pcie.pcie_common import PcieUtil
    rc = pcied.load_platform_pcieutil()

    assert isinstance(rc, PcieUtil)