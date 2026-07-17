'''
Test BMCWatchdog module
'''

import json
import socket
import sys
from unittest import mock

import pytest

try:
    from sonic_py_common import logger
except ImportError:
    sys.modules['sonic_py_common'] = mock.MagicMock()
    sys.modules['sonic_py_common.logger'] = mock.MagicMock()

from sonic_platform_base.bmc_watchdog import BMCWatchdog


def make_sock_mock(response):
    '''
    Build a mock socket whose recv() returns the JSON-encoded `response`.
    Returns (sock_mock, sent) where `sent` collects sendall() payloads.
    '''
    sock = mock.MagicMock()
    sent = []
    sock.sendall.side_effect = lambda data: sent.append(data)
    if response is None:
        sock.recv.return_value = b""
    else:
        sock.recv.return_value = (json.dumps(response) + "\n").encode()
    return sock, sent


class TestBMCWatchdog:
    def test_init_defaults(self):
        wd = BMCWatchdog()
        assert wd.socket_path == "/run/hw-watchdog-mgrd.sock"
        assert wd.sysfs_path == "/sys/class/watchdog/watchdog0/"

    def test_init_custom_paths(self):
        wd = BMCWatchdog(socket_path="/tmp/wd.sock", sysfs_path="/tmp/wd/")
        assert wd.socket_path == "/tmp/wd.sock"
        assert wd.sysfs_path == "/tmp/wd/"

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_request_sends_command(self, mock_socket):
        sock, sent = make_sock_mock({"result": True})
        mock_socket.return_value = sock
        wd = BMCWatchdog(socket_path="/tmp/wd.sock")

        resp = wd._request("arm", seconds=30)

        assert resp == {"result": True}
        sock.connect.assert_called_once_with("/tmp/wd.sock")
        assert json.loads(sent[0].decode().strip()) == {"cmd": "arm", "seconds": 30}

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_request_connection_error_returns_none(self, mock_socket):
        sock = mock.MagicMock()
        sock.connect.side_effect = OSError("no daemon")
        mock_socket.return_value = sock
        wd = BMCWatchdog()
        assert wd._request("is_armed") is None

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_request_invalid_json_returns_none(self, mock_socket):
        sock = mock.MagicMock()
        sock.recv.return_value = b"not-json\n"
        mock_socket.return_value = sock
        wd = BMCWatchdog()
        assert wd._request("is_armed") is None

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_arm(self, mock_socket):
        sock, _ = make_sock_mock({"result": 30})
        mock_socket.return_value = sock
        assert BMCWatchdog().arm(30) == 30

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_arm_failure_returns_minus_one(self, mock_socket):
        sock, _ = make_sock_mock({"error": "bad"})
        mock_socket.return_value = sock
        assert BMCWatchdog().arm(30) == -1

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_arm_daemon_unreachable_returns_minus_one(self, mock_socket):
        sock = mock.MagicMock()
        sock.connect.side_effect = OSError("no daemon")
        mock_socket.return_value = sock
        assert BMCWatchdog().arm(30) == -1

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_disarm(self, mock_socket):
        sock, _ = make_sock_mock({"result": True})
        mock_socket.return_value = sock
        assert BMCWatchdog().disarm() is True

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_disarm_daemon_unreachable_returns_false(self, mock_socket):
        sock = mock.MagicMock()
        sock.connect.side_effect = OSError("no daemon")
        mock_socket.return_value = sock
        assert BMCWatchdog().disarm() is False

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_is_armed(self, mock_socket):
        sock, _ = make_sock_mock({"result": True})
        mock_socket.return_value = sock
        assert BMCWatchdog().is_armed() is True

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_get_remaining_time(self, mock_socket):
        sock, _ = make_sock_mock({"result": 42})
        mock_socket.return_value = sock
        assert BMCWatchdog().get_remaining_time() == 42

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_get_remaining_time_daemon_unreachable(self, mock_socket):
        sock = mock.MagicMock()
        sock.connect.side_effect = OSError("no daemon")
        mock_socket.return_value = sock
        assert BMCWatchdog().get_remaining_time() == -1

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_is_armed_falls_back_to_sysfs_active(self, mock_socket):
        sock = mock.MagicMock()
        sock.connect.side_effect = OSError("no daemon")
        mock_socket.return_value = sock
        wd = BMCWatchdog()
        with mock.patch("builtins.open", mock.mock_open(read_data="active\n")):
            assert wd.is_armed() is True

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_is_armed_falls_back_to_sysfs_inactive(self, mock_socket):
        sock = mock.MagicMock()
        sock.connect.side_effect = OSError("no daemon")
        mock_socket.return_value = sock
        wd = BMCWatchdog()
        with mock.patch("builtins.open", mock.mock_open(read_data="inactive\n")):
            assert wd.is_armed() is False

    @mock.patch("sonic_platform_base.bmc_watchdog.socket.socket")
    def test_is_armed_sysfs_missing_returns_false(self, mock_socket):
        sock = mock.MagicMock()
        sock.connect.side_effect = OSError("no daemon")
        mock_socket.return_value = sock
        wd = BMCWatchdog()
        with mock.patch("builtins.open", side_effect=OSError("missing")):
            assert wd.is_armed() is False
