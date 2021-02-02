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

daemon_base.db_connect = mock.MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)

load_source('ledd', scripts_path + '/ledd')
import ledd


def test_help_args(capsys):
    for flag in ['-h', '--help']:
        with mock.patch.object(sys, 'argv', ['ledd', flag]):
            with pytest.raises(SystemExit) as pytest_wrapped_e:
                ledd.main()
            assert pytest_wrapped_e.type == SystemExit
            assert pytest_wrapped_e.value.code == 0
            out, err = capsys.readouterr()
            assert out.rstrip() == ledd.USAGE_HELP.rstrip()


def test_version_args(capsys):
    for flag in ['-v', '--version']:
        with mock.patch.object(sys, 'argv', ['ledd', flag]):
            with pytest.raises(SystemExit) as pytest_wrapped_e:
                ledd.main()
            assert pytest_wrapped_e.type == SystemExit
            assert pytest_wrapped_e.value.code == 0
            out, err = capsys.readouterr()
            assert out.rstrip() == 'ledd version {}'.format(ledd.VERSION)


def test_bad_args(capsys):
    for flag in ['-n', '--nonexistent']:
        with mock.patch.object(sys, 'argv', ['ledd', flag]):
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

    def test_run_fail_load_platform_util(self):
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            ledd.DaemonLedd()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == ledd.LEDUTIL_LOAD_ERROR

    @mock.patch("ledd.DaemonLedd.load_platform_util")
    @mock.patch("ledd.swsscommon.SubscriberStateTable")
    @mock.patch("ledd.swsscommon.Select")
    def test_run_select_timeout(self, mock_select, mock_sst, mock_load_plat_util):
        select_instance = mock_select.return_value
        select_instance.select.return_value = (ledd.swsscommon.Select.TIMEOUT, None)

        daemon_ledd = ledd.DaemonLedd()
        ret = daemon_ledd.run()
        assert ret == 1

    @mock.patch("ledd.DaemonLedd.load_platform_util")
    @mock.patch("ledd.swsscommon.SubscriberStateTable")
    @mock.patch("ledd.swsscommon.Select")
    def test_run_bad_select_return(self, mock_select, mock_sst, mock_load_plat_util):
        select_instance = mock_select.return_value
        select_instance.select.return_value = (ledd.swsscommon.Select.ERROR, mock.MagicMock())

        daemon_ledd = ledd.DaemonLedd()
        ret = daemon_ledd.run()
        assert ret == 2

    @mock.patch("ledd.DaemonLedd.load_platform_util")
    @mock.patch("ledd.swsscommon.CastSelectableToRedisSelectObj")
    @mock.patch("ledd.swsscommon.SubscriberStateTable")
    @mock.patch("ledd.swsscommon.Select")
    def test_run_ignore_keys(self, mock_select, mock_sst, mock_cstrso, mock_load_plat_util):
        select_instance = mock_select.return_value
        select_instance.select.return_value = (ledd.swsscommon.Select.OBJECT, mock.MagicMock())

        mock_cstrso.return_value.getDbConnector.return_value.getNamespace.return_value = ledd.multi_asic.DEFAULT_NAMESPACE

        sst_instance = mock_sst.return_value

        for key in ['PortConfigDone', 'PortInitDone']:
            sst_instance.pop.return_value = ('PortConfigDone', 'SET', {'not': 'applicable'})

            daemon_ledd = ledd.DaemonLedd()
            ret = daemon_ledd.run()
            assert ret == 3

    @mock.patch("ledd.DaemonLedd.load_platform_util")
    @mock.patch("ledd.swsscommon.CastSelectableToRedisSelectObj")
    @mock.patch("ledd.swsscommon.SubscriberStateTable")
    @mock.patch("ledd.swsscommon.Select")
    def test_run_bad_fvp(self, mock_select, mock_sst, mock_cstrso, mock_load_plat_util):
        select_instance = mock_select.return_value
        select_instance.select.return_value = (ledd.swsscommon.Select.OBJECT, mock.MagicMock())

        mock_cstrso.return_value.getDbConnector.return_value.getNamespace.return_value = ledd.multi_asic.DEFAULT_NAMESPACE

        sst_instance = mock_sst.return_value

        for fvp in [None, {}]:
            sst_instance.pop.return_value = ('Ethernet0', 'SET', fvp)

            daemon_ledd = ledd.DaemonLedd()
            ret = daemon_ledd.run()
            assert ret == 4

    @mock.patch("ledd.DaemonLedd.load_platform_util")
    @mock.patch("ledd.swsscommon.CastSelectableToRedisSelectObj")
    @mock.patch("ledd.swsscommon.SubscriberStateTable")
    @mock.patch("ledd.swsscommon.Select")
    def test_run_good(self, mock_select, mock_sst, mock_cstrso, mock_led_control):
        select_instance = mock_select.return_value
        select_instance.select.return_value = (ledd.swsscommon.Select.OBJECT, mock.MagicMock())

        mock_cstrso.return_value.getDbConnector.return_value.getNamespace.return_value = ledd.multi_asic.DEFAULT_NAMESPACE

        sst_instance = mock_sst.return_value

        led_control_instance = mock_led_control.return_value

        for port in ['Ethernet0', 'Ethernet4']:
            for link_state in ['up', 'down']:
                sst_instance.pop.return_value = (port, 'SET', {'oper_status': link_state})

                daemon_ledd = ledd.DaemonLedd()
                ret = daemon_ledd.run()
                assert ret == 0
                assert led_control_instance.port_link_state_change.call_count == 1
                led_control_instance.port_link_state_change.assert_called_with(port, link_state)
                led_control_instance.port_link_state_change.reset_mock()
