import os
import sys
from imp import load_source

import pytest
# TODO: Clean this up once we no longer need to support Python 2
if sys.version_info.major == 3:
    from unittest.mock import Mock, MagicMock, patch
else:
    from mock import Mock, MagicMock, patch
from sonic_py_common import daemon_base

SYSLOG_IDENTIFIER = 'ledd_test'
NOT_AVAILABLE = 'N/A'

daemon_base.db_connect = MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)

os.environ["LEDD_UNIT_TESTING"] = "1"
load_source('ledd', scripts_path + '/ledd')
import ledd


def test_help_args(capsys):
    for flag in ['-h', '--help']:
        with patch.object(sys, 'argv', ['ledd', flag]):
            with pytest.raises(SystemExit) as pytest_wrapped_e:
                ledd.main()
            assert pytest_wrapped_e.type == SystemExit
            assert pytest_wrapped_e.value.code == 0
            out, err = capsys.readouterr()
            assert out.rstrip() == ledd.USAGE_HELP.rstrip()


def test_version_args(capsys):
    for flag in ['-v', '--version']:
        with patch.object(sys, 'argv', ['ledd', flag]):
            with pytest.raises(SystemExit) as pytest_wrapped_e:
                ledd.main()
            assert pytest_wrapped_e.type == SystemExit
            assert pytest_wrapped_e.value.code == 0
            out, err = capsys.readouterr()
            assert out.rstrip() == 'ledd version {}'.format(ledd.VERSION)


def test_bad_args(capsys):
    for flag in ['-n', '--nonexistent']:
        with patch.object(sys, 'argv', ['ledd', flag]):
            with pytest.raises(SystemExit) as pytest_wrapped_e:
                ledd.main()
            assert pytest_wrapped_e.type == SystemExit
            assert pytest_wrapped_e.value.code == 1
            out, err = capsys.readouterr()
            assert out.rstrip().endswith(ledd.USAGE_HELP.rstrip())


class TestDaemonLedd(object):
    """
    Test cases to cover functionality in DaemonLedd class
    """

    def test_run(self):
        daemon_ledd = ledd.DaemonLedd(SYSLOG_IDENTIFIER)
        # TODO: Add more coverage
