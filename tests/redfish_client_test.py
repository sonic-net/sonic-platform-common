"""
    redfish_client_test.py

    Unit tests for RedfishClient, against a fake BMC at the HTTP transport
"""

import itertools
import json
import logging
import os
import re
import subprocess
import sys
from collections import namedtuple
from unittest import mock
from urllib.parse import urlparse

import pytest
import requests
from requests_toolbelt.multipart.decoder import MultipartDecoder
from urllib3.exceptions import MaxRetryError, NewConnectionError, ProtocolError

try:
    from sonic_py_common import logger
except ImportError:
    sys.modules['sonic_py_common'] = mock.MagicMock()
    sys.modules['sonic_py_common.logger'] = mock.MagicMock()

from sonic_platform_base.redfish_client import RedfishClient


test_path = os.path.dirname(os.path.abspath(__file__))

BMC_IP = '169.254.0.1'
USER = 'testuser'
PASSWORD = 'TestPass123!'

SESSIONS = '/redfish/v1/SessionService/Sessions'
FW_INVENTORY = '/redfish/v1/UpdateService/FirmwareInventory'
UPDATE_MULTIPART = '/redfish/v1/UpdateService/update-multipart'
TASKS = '/redfish/v1/TaskService/Tasks'
CHASSIS = '/redfish/v1/Chassis'
ACCOUNT_SERVICE = '/redfish/v1/AccountService'
ACCOUNTS = '/redfish/v1/AccountService/Accounts'
BMC_RESET = '/redfish/v1/Managers/BMC_0/Actions/Manager.Reset'
DUMP_COLLECT = '/redfish/v1/Managers/BMC_0/LogServices/Dump/Actions/LogService.CollectDiagnosticData'

OK = RedfishClient.ERR_CODE_OK


def http(status, body=None, headers=None):
    """A requests.Response as the BMC would send it."""
    resp = requests.Response()
    resp.status_code = status
    if isinstance(body, (dict, list)):
        body = json.dumps(body)
    resp._content = body.encode() if isinstance(body, str) else (body or b'')
    resp.headers.update(headers or {})
    return resp


def dropped():
    """The error on a kept-alive connection the BMC has dropped, for example by rebooting."""
    return requests.exceptions.ConnectionError(
        ProtocolError('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer')))


def refused():
    """The error when no connection to the BMC can be opened."""
    return requests.exceptions.ConnectionError(
        MaxRetryError(None, '/', NewConnectionError(None, 'Connection refused')))


def truncated(status=204):
    """A reply whose body breaks off, which requests raises only after the adapter has returned."""
    resp = requests.Response()
    resp.status_code = status
    resp.raw = mock.Mock(spec=['stream'], **{'stream.side_effect': ProtocolError('Connection broken: IncompleteRead')})
    return resp


def login_ok(token='token1', session_id='session1'):
    return http(201, {'Id': session_id},
                {'X-Auth-Token': token, 'Location': f'{SESSIONS}/{session_id}'})


def redfish_error(message_id, message, status=400):
    """A single-message Redfish error body, shaped as bmcweb sends it."""
    return http(status, {'error': {
        'code': message_id,
        'message': message,
        '@Message.ExtendedInfo': [{'MessageId': message_id, 'Message': message}]}})


def load_json(fname):
    with open(os.path.join(test_path, 'mock_data', fname)) as f:
        return json.load(f)


Call = namedtuple('Call', ['method', 'scheme', 'path', 'headers', 'body', 'timeout', 'verify'])


class FakeBmc:
    """Replays per-(method, path) replies in order, repeating the last; an exception is raised."""

    def __init__(self):
        self.routes = {('GET', '/redfish/v1/'): [http(200, {})],
                       ('POST', SESSIONS): [login_ok()]}
        self.calls = []

    def on(self, method, path, *responses):
        self.routes[(method, path)] = list(responses)

    def send(self, adapter, request, **kwargs):
        parsed = urlparse(request.url)
        self.calls.append(Call(request.method, parsed.scheme, parsed.path,
                               dict(request.headers), request.body, kwargs.get('timeout'), kwargs.get('verify')))
        queue = self.routes.get((request.method, parsed.path))
        item = (queue.pop(0) if len(queue) > 1 else queue[0]) if queue else http(404)
        if isinstance(item, Exception):
            raise item
        item.request, item.url = request, request.url
        return item

    def sent(self, method, path):
        return [c for c in self.calls if c.method == method and c.path == path]


def json_body(call):
    return json.loads(call.body)


def multipart_fields(call):
    """{part name: (filename, content type, content)} of a multipart request."""
    decoder = MultipartDecoder(call.body, call.headers['Content-Type'])
    fields = {}
    for part in decoder.parts:
        disposition = part.headers[b'Content-Disposition'].decode()
        name = re.search(r'name="([^"]+)"', disposition).group(1)
        filename = re.search(r'filename="([^"]+)"', disposition)
        fields[name] = (filename.group(1) if filename else None,
                        part.headers.get(b'Content-Type', b'').decode(),
                        part.content)
    return fields


@pytest.fixture
def bmc():
    fake = FakeBmc()
    with mock.patch.object(requests.adapters.HTTPAdapter, 'send', autospec=True, side_effect=fake.send), \
         mock.patch('redfish.rest.v1.time.sleep'), \
         mock.patch('sonic_platform_base.redfish_client.time.sleep'):
        yield fake


@pytest.fixture
def client(bmc):
    return RedfishClient(BMC_IP, lambda: USER, lambda: PASSWORD)


@pytest.fixture
def logged_in(client):
    assert client.login() == OK
    return client


@pytest.fixture
def fw_image(tmp_path):
    path = tmp_path / 'bmc.fwpkg'
    path.write_bytes(b'\x00FW-IMAGE\xff')
    return str(path)


def test_importing_the_package_does_not_load_the_library():
    code = (
        "import sys, types\n"
        "from unittest import mock\n"
        "m = types.ModuleType('sonic_py_common'); m.__path__ = []\n"
        "sys.modules['sonic_py_common'] = m\n"
        "for sub in ('logger', 'syslogger', 'device_info', 'general', 'multi_asic', 'daemon_base'):\n"
        "    sys.modules['sonic_py_common.' + sub] = mock.MagicMock()\n"
        "import sonic_platform_base.redfish_client, sonic_platform_base.bmc_base\n"
        "print(sorted(n for n in ('redfish', 'requests', 'urllib3') if n in sys.modules))\n")
    out = subprocess.run([sys.executable, '-c', code], cwd=os.path.join(test_path, '..'),
                         capture_output=True, text=True, check=True).stdout
    assert out.strip() == '[]'


class TestLogin:

    def test_login_opens_a_session_with_the_callback_credentials(self, bmc, client):
        assert client.login() == OK
        assert client.has_login()
        assert client.get_login_token() == 'token1'
        assert client.get_session_id() == 'session1'
        assert json_body(bmc.sent('POST', SESSIONS)[0]) == {'UserName': USER, 'Password': PASSWORD}

    def test_login_does_not_keep_the_password(self, bmc, client):
        client.login()
        assert client._RedfishClient__rf.get_password() is None

    def test_login_when_logged_in_reuses_the_session(self, bmc, logged_in):
        assert logged_in.login() == OK
        assert len(bmc.sent('POST', SESSIONS)) == 1

    @pytest.mark.parametrize('response, expected', [
        (http(401), RedfishClient.ERR_CODE_AUTH_FAILURE),
        (requests.exceptions.ConnectionError('refused'), RedfishClient.ERR_CODE_SERVER_UNREACHABLE),
        (requests.exceptions.ReadTimeout('slow'), RedfishClient.ERR_CODE_TIMEOUT),
        (http(201, {}), RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE),
        (http(201, {}, {'Location': f'{SESSIONS}/session1'}), RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE),
    ], ids=['rejected', 'unreachable', 'timeout', 'no-token-no-location', 'no-token'])
    def test_login_failure(self, bmc, client, response, expected):
        bmc.on('POST', SESSIONS, response)
        assert client.login() == expected
        assert not client.has_login()

    def test_login_needing_a_password_change_fails_and_closes_its_session(self, bmc, client):
        bmc.on('POST', SESSIONS, http(201, {'@Message.ExtendedInfo': [
            {'MessageId': 'Base.1.19.PasswordChangeRequired', 'MessageArgs': [f'{ACCOUNTS}/{USER}']}]},
            {'X-Auth-Token': 'token1', 'Location': f'{SESSIONS}/session1'}))
        bmc.on('DELETE', f'{SESSIONS}/session1', http(204))
        assert client.login() == RedfishClient.ERR_CODE_AUTH_FAILURE
        assert not client.has_login()
        assert len(bmc.sent('DELETE', f'{SESSIONS}/session1')) == 1

    def test_login_is_resent_after_the_bmc_dropped_the_connection(self, bmc, client):
        bmc.on('POST', SESSIONS, dropped(), login_ok())
        assert client.login() == OK
        assert len(bmc.sent('POST', SESSIONS)) == 2

    def test_login_is_resent_once_after_a_dropped_connection(self, bmc, client):
        bmc.on('POST', SESSIONS, dropped())
        assert client.login() == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        assert len(bmc.sent('POST', SESSIONS)) == 2
        assert not client.has_login()

    def test_login_to_an_unreachable_bmc_is_not_resent(self, bmc, client):
        bmc.on('POST', SESSIONS, refused())
        assert client.login() == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        assert len(bmc.sent('POST', SESSIONS)) == 1

    def test_login_to_an_unreachable_bmc_does_not_wait(self, bmc, client):
        bmc.on('GET', '/redfish/v1/', refused())
        with mock.patch('redfish.rest.v1.time.sleep') as sleep:
            assert client.login() == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        sleep.assert_not_called()
        assert len(bmc.sent('GET', '/redfish/v1/')) == 1

    def test_login_while_service_root_is_unavailable(self, bmc, client):
        bmc.on('GET', '/redfish/v1/', http(503))
        assert client.login() == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        assert not bmc.sent('POST', SESSIONS)

    @pytest.mark.parametrize('log_errors, expected_log', [(False, 'log_notice'), (True, 'log_error')])
    def test_login_failure_log_level(self, bmc, client, log_errors, expected_log):
        bmc.on('POST', SESSIONS, http(401))
        with mock.patch('sonic_platform_base.redfish_client.logger') as log:
            assert client.login(log_errors=log_errors) == RedfishClient.ERR_CODE_AUTH_FAILURE
        assert getattr(log, expected_log).called
        if not log_errors:
            log.log_error.assert_not_called()

    def test_login_without_password(self, bmc):
        def no_password():
            raise RuntimeError('TPM not ready')
        client = RedfishClient(BMC_IP, lambda: USER, no_password)
        assert client.login() == RedfishClient.ERR_CODE_PASSWORD_UNAVAILABLE
        assert bmc.calls == []

    def test_requests_carry_the_session_token(self, bmc, logged_in):
        bmc.on('GET', f'{FW_INVENTORY}/BMC_FW_0', http(200, {'Version': '1.0'}))
        logged_in.redfish_api_get_firmware_version('BMC_FW_0')
        assert bmc.sent('GET', f'{FW_INVENTORY}/BMC_FW_0')[0].headers['X-Auth-Token'] == 'token1'

    def test_library_records_do_not_reach_application_logs(self, bmc, client):
        records = []
        handler = logging.Handler()
        handler.emit = records.append
        root, level = logging.getLogger(), logging.getLogger().level
        root.addHandler(handler)
        root.setLevel(logging.DEBUG)
        try:
            client.login()
            client.redfish_api_get_firmware_version('BMC_FW_0')
        finally:
            root.removeHandler(handler)
            root.setLevel(level)
        assert not [r for r in records if r.name.startswith('redfish')]

    def test_api_call_before_login(self, bmc, client):
        assert client.redfish_api_get_firmware_version('BMC_FW_0') == (RedfishClient.ERR_CODE_NOT_LOGIN, 'N/A')
        assert bmc.calls == []


class TestExpiredSession:

    URI = f'{FW_INVENTORY}/BMC_FW_0'

    def test_relogin_returns_the_rerun_result(self, bmc, logged_in):
        bmc.on('POST', SESSIONS, login_ok('token2', 'session2'))
        bmc.on('GET', self.URI, http(401), http(200, {'Version': '88.0060.2408'}))
        assert logged_in.redfish_api_get_firmware_version('BMC_FW_0') == (OK, '88.0060.2408')
        assert [c.headers['X-Auth-Token'] for c in bmc.sent('GET', self.URI)] == ['token1', 'token2']
        assert logged_in.get_session_id() == 'session2'

    def test_failed_relogin(self, bmc, logged_in):
        bmc.on('POST', SESSIONS, http(401))
        bmc.on('GET', self.URI, http(401))
        assert logged_in.redfish_api_get_firmware_version('BMC_FW_0') == \
            (RedfishClient.ERR_CODE_AUTH_FAILURE, 'N/A')
        assert not logged_in.has_login()

    def test_rerun_rejected_again(self, bmc, logged_in):
        bmc.on('POST', SESSIONS, login_ok('token2', 'session2'))
        bmc.on('GET', self.URI, http(401))
        assert logged_in.redfish_api_get_firmware_version('BMC_FW_0') == \
            (RedfishClient.ERR_CODE_AUTH_FAILURE, 'N/A')
        assert len(bmc.sent('GET', self.URI)) == 2
        assert not logged_in.has_login()


class TestTransport:

    URI = f'{FW_INVENTORY}/BMC_FW_0'

    def test_get_is_retried_after_a_timeout(self, bmc, logged_in):
        bmc.on('GET', self.URI, requests.exceptions.ReadTimeout('slow'), http(200, {'Version': '1.0'}))
        assert logged_in.redfish_api_get_firmware_version('BMC_FW_0') == (OK, '1.0')

    def test_get_gives_up_after_two_retries(self, bmc, logged_in):
        bmc.on('GET', self.URI, requests.exceptions.ReadTimeout('slow'))
        assert logged_in.redfish_api_get_firmware_version('BMC_FW_0') == (RedfishClient.ERR_CODE_TIMEOUT, 'N/A')
        assert len(bmc.sent('GET', self.URI)) == 3

    def test_action_is_not_resent_after_a_timeout(self, bmc, logged_in):
        bmc.on('POST', BMC_RESET, requests.exceptions.ReadTimeout('slow'))
        assert logged_in.redfish_api_request_bmc_reset()[0] == RedfishClient.ERR_CODE_TIMEOUT
        assert len(bmc.sent('POST', BMC_RESET)) == 1

    def test_action_is_sent_once_when_a_resend_would_succeed(self, bmc, logged_in):
        bmc.on('PATCH', ACCOUNT_SERVICE, requests.exceptions.ConnectionError('reset'), http(204))
        assert logged_in.redfish_api_set_min_password_length(8)[0] == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        assert len(bmc.sent('PATCH', ACCOUNT_SERVICE)) == 1

    def test_get_is_resent_after_the_bmc_dropped_the_connection(self, bmc, logged_in):
        bmc.on('GET', self.URI, dropped(), http(200, {'Version': '1.0'}))
        assert logged_in.redfish_api_get_firmware_version('BMC_FW_0') == (OK, '1.0')

    def test_action_is_not_resent_after_the_bmc_dropped_the_connection(self, bmc, logged_in):
        bmc.on('POST', BMC_RESET, dropped(), http(204))
        assert logged_in.redfish_api_request_bmc_reset()[0] == RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        assert len(bmc.sent('POST', BMC_RESET)) == 1

    def test_get_to_an_unreachable_bmc_is_not_resent(self, bmc, logged_in):
        bmc.on('GET', self.URI, refused())
        assert logged_in.redfish_api_get_firmware_version('BMC_FW_0') == \
            (RedfishClient.ERR_CODE_SERVER_UNREACHABLE, 'N/A')
        assert len(bmc.sent('GET', self.URI)) == 1

    @pytest.mark.parametrize('failure', [refused(), dropped(), requests.exceptions.ReadTimeout('slow')],
                             ids=['refused', 'dropped', 'timeout'])
    def test_a_failed_send_does_not_wait(self, bmc, logged_in, failure):
        bmc.on('GET', self.URI, failure)
        with mock.patch('redfish.rest.v1.time.sleep') as sleep:
            logged_in.redfish_api_get_firmware_version('BMC_FW_0')
        sleep.assert_not_called()

    def test_action_is_not_resent_when_its_reply_breaks_off(self, bmc, logged_in):
        bmc.on('POST', BMC_RESET, truncated())
        assert logged_in.redfish_api_request_bmc_reset()[0] == RedfishClient.ERR_CODE_CURL_FAILURE
        assert len(bmc.sent('POST', BMC_RESET)) == 1

    def test_get_uses_the_short_timeout_and_actions_the_long_one(self, bmc, logged_in):
        bmc.on('GET', self.URI, http(200, {'Version': '1.0'}))
        bmc.on('POST', BMC_RESET, http(204))
        logged_in.redfish_api_get_firmware_version('BMC_FW_0')
        logged_in.redfish_api_request_bmc_reset()
        assert bmc.sent('GET', self.URI)[0].timeout == RedfishClient.DEFAULT_TIMEOUT
        assert bmc.sent('POST', BMC_RESET)[0].timeout == RedfishClient.ACTION_TIMEOUT

    def test_unreachable_bmc(self, bmc, logged_in):
        bmc.on('GET', self.URI, requests.exceptions.ConnectionError('refused'))
        assert logged_in.redfish_api_get_firmware_version('BMC_FW_0') == \
            (RedfishClient.ERR_CODE_SERVER_UNREACHABLE, 'N/A')

    def test_other_transport_failure(self, bmc, logged_in):
        bmc.on('GET', self.URI, requests.exceptions.ChunkedEncodingError('broken'))
        assert logged_in.redfish_api_get_firmware_version('BMC_FW_0') == (RedfishClient.ERR_CODE_CURL_FAILURE, 'N/A')

    @pytest.mark.parametrize('status, expected', [(404, RedfishClient.ERR_CODE_URI_NOT_FOUND),
                                                  (502, RedfishClient.ERR_CODE_GENERIC_ERROR)])
    def test_error_body_that_is_not_json(self, bmc, logged_in, status, expected):
        bmc.on('GET', ACCOUNT_SERVICE, http(status, '<html>error</html>'))
        assert logged_in.redfish_api_get_min_password_length() == (expected, f'HTTP status code {status}')

    def test_https_by_default(self, bmc, client):
        client.login()
        assert {c.scheme for c in bmc.calls} == {'https'}

    def test_scheme_callback_is_read_per_request(self, bmc):
        scheme = {'value': RedfishClient.SCHEME_HTTPS}
        client = RedfishClient(BMC_IP, lambda: USER, lambda: PASSWORD, lambda: scheme['value'])
        scheme['value'] = RedfishClient.SCHEME_HTTP
        client.login()
        assert {c.scheme for c in bmc.calls} == {'http'}

    def test_certificate_is_not_verified_by_default(self, bmc, client):
        client.login()
        assert {c.verify for c in bmc.calls} == {False}

    def test_cafile_verifies_the_certificate(self, bmc):
        client = RedfishClient(BMC_IP, lambda: USER, lambda: PASSWORD, cafile='/etc/ssl/certs/bmc-ca.pem')
        client.login()
        assert {c.verify for c in bmc.calls} == {'/etc/ssl/certs/bmc-ca.pem'}

    def test_unsupported_scheme_falls_back_to_https(self, bmc):
        client = RedfishClient(BMC_IP, lambda: USER, lambda: PASSWORD, lambda: 'ftp')
        client.login()
        assert {c.scheme for c in bmc.calls} == {'https'}


class TestLogout:

    def test_logout_deletes_the_current_session(self, bmc, logged_in):
        bmc.on('DELETE', f'{SESSIONS}/session1', http(200, load_json('mock_bmc_logout_response')))
        assert logged_in.logout() == OK
        assert len(bmc.sent('DELETE', f'{SESSIONS}/session1')) == 1
        assert not logged_in.has_login()

    def test_failed_logout_still_drops_the_session(self, bmc, logged_in):
        bmc.on('DELETE', f'{SESSIONS}/session1', http(500))
        assert logged_in.logout() == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert not logged_in.has_login()

    def test_logout_with_an_expired_token_does_not_relogin(self, bmc, logged_in):
        bmc.on('DELETE', f'{SESSIONS}/session1', http(401))
        assert logged_in.logout() == RedfishClient.ERR_CODE_AUTH_FAILURE
        assert len(bmc.sent('POST', SESSIONS)) == 1

    def test_logout_of_another_session_keeps_the_current_one(self, bmc, logged_in):
        bmc.on('DELETE', f'{SESSIONS}/other', http(204))
        assert logged_in.logout('other') == OK
        assert logged_in.has_login()

    def test_logout_without_a_session(self, bmc, client):
        assert client.logout() == OK
        assert bmc.calls == []


class TestManualSessions:

    def test_open_session_returns_the_credentials(self, bmc, client):
        assert client.open_session() == (OK, ('Login successful', ('session1', 'token1')))

    def test_open_session_failure(self, bmc, client):
        bmc.on('POST', SESSIONS, http(401))
        assert client.open_session() == (RedfishClient.ERR_CODE_NOT_LOGIN, ('Failed to open session', None))

    def test_close_session_deletes_an_existing_session(self, bmc, logged_in):
        bmc.on('GET', SESSIONS, http(200, {'Members': [{'@odata.id': f'{SESSIONS}/other'}]}))
        bmc.on('DELETE', f'{SESSIONS}/other', http(204))
        assert logged_in.close_session('other') == (OK, 'Session closed successfully')
        assert len(bmc.sent('DELETE', f'{SESSIONS}/other')) == 1

    def test_close_session_of_an_unknown_session(self, bmc, logged_in):
        bmc.on('GET', SESSIONS, http(200, {'Members': [{'@odata.id': f'{SESSIONS}/session1'}]}))
        assert logged_in.close_session('other') == (OK, 'Session does not exist')
        assert not bmc.sent('DELETE', f'{SESSIONS}/other')

    def test_close_session_when_the_session_list_is_refused(self, bmc, logged_in):
        bmc.on('GET', SESSIONS, redfish_error('Base.1.19.InsufficientPrivilege',
                                              'There are insufficient privileges for the account.', 403))
        ret, _ = logged_in.close_session('other')
        assert ret == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert not bmc.sent('DELETE', f'{SESSIONS}/other')

    def test_close_session_when_the_delete_fails(self, bmc, logged_in):
        bmc.on('GET', SESSIONS, http(200, {'Members': [{'@odata.id': f'{SESSIONS}/other'}]}))
        bmc.on('DELETE', f'{SESSIONS}/other', http(500))
        assert logged_in.close_session('other') == \
            (RedfishClient.ERR_CODE_GENERIC_ERROR, f'Failed to close session: {RedfishClient.ERR_CODE_GENERIC_ERROR}')

    def test_close_session_with_a_malformed_session_list(self, bmc, logged_in):
        bmc.on('GET', SESSIONS, http(200, ['not', 'a', 'collection']))
        ret, msg = logged_in.close_session('other')
        assert ret == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert msg.startswith('Failed to close session:')

    def test_close_session_without_login(self, bmc, client):
        assert client.close_session('other') == (RedfishClient.ERR_CODE_NOT_LOGIN, 'Not logged in')


class TestWaitUntilRedfishReady:

    def test_ready_on_the_first_login(self, bmc, client):
        assert client.wait_until_redfish_ready(timeout=30, interval=1) == OK
        assert len(bmc.sent('DELETE', f'{SESSIONS}/session1')) == 1

    def test_cached_session_is_not_taken_as_ready(self, bmc, logged_in):
        bmc.on('POST', SESSIONS, http(503))
        assert logged_in.wait_until_redfish_ready(timeout=0, interval=1) != OK

    def test_keeps_polling_past_an_auth_failure(self, bmc, client):
        bmc.on('POST', SESSIONS, http(401), login_ok())
        assert client.wait_until_redfish_ready(timeout=30, interval=1) == OK
        assert len(bmc.sent('POST', SESSIONS)) == 2

    def test_missing_password_fails_fast(self, bmc):
        def no_password():
            raise RuntimeError('TPM not ready')
        client = RedfishClient(BMC_IP, lambda: USER, no_password)
        assert client.wait_until_redfish_ready(timeout=30, interval=1) == \
            RedfishClient.ERR_CODE_PASSWORD_UNAVAILABLE

    def test_sleep_is_capped_to_the_remaining_time(self, bmc, client):
        with mock.patch.object(client, 'login', side_effect=[RedfishClient.ERR_CODE_SERVER_UNREACHABLE, OK]), \
             mock.patch.object(client, 'logout'), \
             mock.patch('sonic_platform_base.redfish_client.time') as mock_time:
            # deadline = 1000 + 300; the check at 1297 leaves 3 s, less than the interval
            mock_time.time.side_effect = [1000.0, 1297.0]
            assert client.wait_until_redfish_ready(timeout=300, interval=10) == OK
        mock_time.sleep.assert_called_once_with(3.0)

    def test_timeout_returns_the_last_failure(self, bmc, client):
        bmc.on('GET', '/redfish/v1/', http(503))
        assert client.wait_until_redfish_ready(timeout=0, interval=1) == \
            RedfishClient.ERR_CODE_SERVER_UNREACHABLE


class TestFirmwareInventory:

    def test_get_firmware_version(self, bmc, logged_in):
        bmc.on('GET', f'{FW_INVENTORY}/MGX_FW_BMC_0', http(200, {'Id': 'MGX_FW_BMC_0', 'Version': '88.0060.2408'}))
        assert logged_in.redfish_api_get_firmware_version('MGX_FW_BMC_0') == (OK, '88.0060.2408')

    @pytest.mark.parametrize('response, expected', [
        (redfish_error('Base.1.19.ResourceMissingAtURI',
                       "The resource at the URI '/redfish/v1/UpdateService/FirmwareInventory/FW_BMC_0' was not found."),
         RedfishClient.ERR_CODE_URI_NOT_FOUND),
        (http(400, {'error': {
            'code': 'Base.1.19.GeneralError',
            'message': 'A general error has occurred. See Resolution for information on how to resolve the error.',
            '@Message.ExtendedInfo': [
                {'MessageId': 'Base.1.19.ResourceMissingAtURI', 'Message': 'not found'},
                {'MessageId': 'Base.1.19.InternalError', 'Message': 'internal'}]}}),
         RedfishClient.ERR_CODE_URI_NOT_FOUND),
        (redfish_error('Base.1.19.ResourceNotFound', 'The requested resource was not found.', 404),
         RedfishClient.ERR_CODE_URI_NOT_FOUND),
        (http(404), RedfishClient.ERR_CODE_URI_NOT_FOUND),
        (redfish_error('Base.1.19.InternalError', 'The request failed due to an internal service error.', 500),
         RedfishClient.ERR_CODE_GENERIC_ERROR),
        (http(500), RedfishClient.ERR_CODE_GENERIC_ERROR),
        (http(200, {'Id': 'FW_BMC_0'}), RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE),
        (http(200, 'not json'), RedfishClient.ERR_CODE_INVALID_JSON_FORMAT),
    ], ids=['400-missing-at-uri', '400-general-error', '404-not-found', '404-no-body',
            '500-internal', '500-no-body', '200-no-version', '200-not-json'])
    def test_get_firmware_version_failure(self, bmc, logged_in, response, expected):
        bmc.on('GET', f'{FW_INVENTORY}/FW_BMC_0', response)
        assert logged_in.redfish_api_get_firmware_version('FW_BMC_0') == (expected, 'N/A')

    def test_missing_member_is_not_logged_as_an_error(self, bmc, logged_in):
        bmc.on('GET', f'{FW_INVENTORY}/FW_BMC_0', redfish_error('Base.1.19.ResourceMissingAtURI', 'not found'))
        with mock.patch('sonic_platform_base.redfish_client.logger') as log:
            logged_in.redfish_api_get_firmware_version('FW_BMC_0')
        log.log_error.assert_not_called()

    def test_get_firmware_list(self, bmc, logged_in):
        bmc.on('GET', FW_INVENTORY, http(200, load_json('mock_get_firmware_list_response')))
        bmc.on('GET', f'{FW_INVENTORY}/BMC_FW_0', http(200, {'Version': '1.0'}))
        bmc.on('GET', f'{FW_INVENTORY}/BIOS_FW_0', redfish_error('Base.1.19.ResourceMissingAtURI', 'not found'))
        assert logged_in.redfish_api_get_firmware_list() == (OK, [('BMC_FW_0', '1.0'), ('BIOS_FW_0', 'N/A')])

    def test_get_firmware_list_without_members(self, bmc, logged_in):
        bmc.on('GET', FW_INVENTORY, http(200, {'Name': 'Software Inventory Collection'}))
        assert logged_in.redfish_api_get_firmware_list() == (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, [])

    def test_get_firmware_list_failure(self, bmc, logged_in):
        bmc.on('GET', FW_INVENTORY, http(500))
        assert logged_in.redfish_api_get_firmware_list() == (RedfishClient.ERR_CODE_GENERIC_ERROR, [])


class TestFirmwareUpdate:

    TASK = f'{TASKS}/1234'

    @staticmethod
    def task(percent, status='OK', messages=()):
        return http(200, {'Id': '1234', 'PercentComplete': percent, 'TaskStatus': status,
                          'Messages': list(messages)})

    def test_update_uploads_the_image_and_waits_for_the_task(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, http(200, load_json('mock_firmware_update_task_complete')))
        assert logged_in.redfish_api_update_firmware(fw_image, fw_ids=['MGX_FW_BMC_0'], force_update=False) == \
            (OK, '', ['BMC_FW_0'])
        fields = multipart_fields(bmc.sent('POST', UPDATE_MULTIPART)[0])
        filename, content_type, params = fields['UpdateParameters']
        assert (filename, content_type) == (None, 'application/json')
        assert json.loads(params) == {'ForceUpdate': False,
                                      'Targets': ['/redfish/v1/UpdateService/FirmwareInventory/MGX_FW_BMC_0']}
        assert fields['UpdateFile'] == ('bmc.fwpkg', 'application/octet-stream', b'\x00FW-IMAGE\xff')

    def test_upload_waits_for_its_reply_as_long_as_the_whole_update(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, http(200, load_json('mock_firmware_update_task_complete')))
        logged_in.redfish_api_update_firmware(fw_image)
        logged_in.redfish_api_update_firmware(fw_image, timeout=600)
        assert [c.timeout for c in bmc.sent('POST', UPDATE_MULTIPART)] == [1800, 600]

    def test_update_without_targets_lets_the_bmc_choose(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, http(200, load_json('mock_firmware_update_task_complete')))
        logged_in.redfish_api_update_firmware(fw_image)
        _, _, params = multipart_fields(bmc.sent('POST', UPDATE_MULTIPART)[0])['UpdateParameters']
        assert json.loads(params) == {'ForceUpdate': True}

    def test_update_reports_progress(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, self.task(40), http(200, load_json('mock_firmware_update_task_complete')))
        progress = []
        logged_in.redfish_api_update_firmware(fw_image, progress_callback=lambda d: progress.append(d['percent']))
        assert progress == [40, 100]

    def test_update_task_status_is_logged_only_when_it_changes(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, self.task(40), self.task(40), http(200, load_json('mock_firmware_update_task_complete')))
        with mock.patch('sonic_platform_base.redfish_client.logger') as log:
            assert logged_in.redfish_api_update_firmware(fw_image)[0] == OK
        status_logs = [c for c in log.log_notice.call_args_list if c.args[0].startswith('Task 1234 status at')]
        assert len(bmc.sent('GET', self.TASK)) == 3
        assert len(status_logs) == 2

    def test_update_rejected_by_the_bmc(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, redfish_error('Base.1.19.InvalidObject', "The object at 'Targets' is invalid."))
        assert logged_in.redfish_api_update_firmware(fw_image, fw_ids=['FW_BMC_0']) == \
            (RedfishClient.ERR_CODE_GENERIC_ERROR, "Error: The object at 'Targets' is invalid.", [])
        assert not bmc.sent('GET', self.TASK)

    def test_update_with_a_lower_version(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, self.task(100, 'Critical', [{
            'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected',
            'MessageArgs': ['BMC_FW_0', 'Version is lower than the firmware component comparison stamp']}]))
        ret, msg, _ = logged_in.redfish_api_update_firmware(fw_image)
        assert (ret, msg) == (RedfishClient.ERR_CODE_LOWER_VERSION, 'Error: The target image has lower version')

    def test_update_with_an_identical_version(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, self.task(100, 'Warning', [
            {'MessageId': 'ResourceEvent.1.0.ComponentUpdateSkipped', 'MessageArgs': ['BMC_FW_0', 'identical']},
            {'MessageId': 'TaskEvent.1.0.TaskAborted', 'MessageArgs': ['1234']}]))
        assert logged_in.redfish_api_update_firmware(fw_image) == (RedfishClient.ERR_CODE_IDENTICAL_VERSION, '', [])

    def test_update_task_that_disappeared(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, redfish_error('Base.1.19.ResourceNotFound', 'The requested resource was not found.', 404))
        ret, _, _ = logged_in.redfish_api_update_firmware(fw_image)
        assert ret == RedfishClient.ERR_CODE_URI_NOT_FOUND

    def test_update_task_failed_without_an_error_message(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, self.task(50, 'Failed'))
        ret, msg, ids = logged_in.redfish_api_update_firmware(fw_image)
        assert (ret, ids) == (RedfishClient.ERR_CODE_GENERIC_ERROR, [])
        # Kept from the cURL client, with the property name in lowercase
        assert msg == 'Error: Fail to execute the task - ' + 'TaskStatus'.capitalize() + '=Failed'

    def test_update_task_aborted(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, self.task(30, 'Aborted', [{'MessageId': 'TaskEvent.1.0.TaskAborted'}]))
        assert logged_in.redfish_api_update_firmware(fw_image) == \
            (RedfishClient.ERR_CODE_GENERIC_ERROR, 'Error: The task has been aborted', [])

    def test_update_task_overall_timeout(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, self.task(50))
        clock = itertools.count(100, 3)
        with mock.patch('sonic_platform_base.redfish_client.time.time', side_effect=lambda: next(clock)):
            ret, msg, _ = logged_in.redfish_api_update_firmware(fw_image, timeout=5)
        assert (ret, msg) == (RedfishClient.ERR_CODE_TIMEOUT, 'Error: Wait task completion timeout\n')

    def test_update_task_poll_keeps_going_after_timeouts(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, *([requests.exceptions.ReadTimeout('slow')] * 3),
               http(200, load_json('mock_firmware_update_task_complete')))
        assert logged_in.redfish_api_update_firmware(fw_image) == (OK, '', ['BMC_FW_0'])

    @pytest.mark.parametrize('response, expected', [
        (http(200, 'not json'), (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, 'Error: Invalid JSON format')),
        (http(200, {'TaskStatus': 'OK', 'Messages': []}),
         (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, "Error: Missing 'PercentComplete' field in task status response")),
    ], ids=['not-json', 'missing-field'])
    def test_update_task_with_a_malformed_status(self, bmc, logged_in, fw_image, response, expected):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, response)
        ret, msg, _ = logged_in.redfish_api_update_firmware(fw_image)
        assert (ret, msg) == expected

    def test_update_task_started_with_a_bad_status(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, {'Id': '1234', 'TaskStatus': 'Critical'}))
        assert logged_in.redfish_api_update_firmware(fw_image) == \
            (RedfishClient.ERR_CODE_GENERIC_ERROR, 'Error: Return status is Critical', [])
        assert not bmc.sent('GET', self.TASK)

    def test_update_task_without_progress_yet(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, self.task(None), http(200, load_json('mock_firmware_update_task_complete')))
        assert logged_in.redfish_api_update_firmware(fw_image) == (OK, '', ['BMC_FW_0'])
        assert len(bmc.sent('GET', self.TASK)) == 2

    def test_update_reply_without_a_task(self, bmc, logged_in, fw_image):
        bmc.on('POST', UPDATE_MULTIPART, http(202, {'Id': '1234'}))
        assert logged_in.redfish_api_update_firmware(fw_image) == \
            (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, "Error: Missing 'TaskStatus' field in response", [])

    def test_update_after_an_expired_token_resends_the_whole_image(self, bmc, logged_in, fw_image):
        bmc.on('POST', SESSIONS, login_ok('token2', 'session2'))
        bmc.on('POST', UPDATE_MULTIPART, http(401), http(202, load_json('mock_firmware_update_response')))
        bmc.on('GET', self.TASK, http(200, load_json('mock_firmware_update_task_complete')))
        assert logged_in.redfish_api_update_firmware(fw_image)[0] == OK
        resent = bmc.sent('POST', UPDATE_MULTIPART)[1]
        assert multipart_fields(resent)['UpdateFile'][2] == b'\x00FW-IMAGE\xff'

    def test_update_with_a_missing_image(self, bmc, logged_in, tmp_path):
        ret, _, _ = logged_in.redfish_api_update_firmware(str(tmp_path / 'absent.fwpkg'))
        assert ret == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert not bmc.sent('POST', UPDATE_MULTIPART)


class TestBmcDebugLogDump:

    ATTACHMENT = '/redfish/v1/Managers/BMC_0/LogServices/Dump/Entries/113/attachment'

    def test_trigger_dump(self, bmc, logged_in):
        bmc.on('POST', DUMP_COLLECT, http(202, load_json('mock_bmc_debug_log_dump_response')))
        assert logged_in.redfish_api_trigger_bmc_debug_log_dump() == (OK, ('0', None))
        assert json_body(bmc.sent('POST', DUMP_COLLECT)[0]) == {'DiagnosticDataType': 'Manager'}

    def test_trigger_dump_rejected(self, bmc, logged_in):
        bmc.on('POST', DUMP_COLLECT, redfish_error('Base.1.19.ServiceTemporarilyUnavailable',
                                                   'The service is temporarily unavailable.', 503))
        assert logged_in.redfish_api_trigger_bmc_debug_log_dump() == \
            (RedfishClient.ERR_CODE_GENERIC_ERROR, ('-1', 'Error: The service is temporarily unavailable.'))

    def test_trigger_dump_without_a_task(self, bmc, logged_in):
        bmc.on('POST', DUMP_COLLECT, http(202, {}))
        assert logged_in.redfish_api_trigger_bmc_debug_log_dump() == \
            (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, ('-1', "Error: Missing 'TaskStatus' field in response"))

    def test_get_dump_when_the_task_is_gone(self, bmc, logged_in, tmp_path):
        bmc.on('GET', f'{TASKS}/0', redfish_error('Base.1.19.ResourceNotFound', 'The requested resource was not found.', 404))
        assert logged_in.redfish_api_get_bmc_debug_log_dump('0', 'bmc.tar.xz', str(tmp_path)) == \
            (RedfishClient.ERR_CODE_URI_NOT_FOUND, 'Error: The requested resource was not found.')
        assert not (tmp_path / 'bmc.tar.xz').exists()

    def test_get_dump_writes_the_attachment(self, bmc, logged_in, tmp_path):
        bmc.on('GET', f'{TASKS}/0', http(200, load_json('mock_bmc_task_query_valid_debug_log_dump')))
        bmc.on('GET', self.ATTACHMENT, http(200, b'\xfd7zXZ\x00dump'))
        assert logged_in.redfish_api_get_bmc_debug_log_dump('0', 'bmc.tar.xz', str(tmp_path)) == (OK, '')
        assert (tmp_path / 'bmc.tar.xz').read_bytes() == b'\xfd7zXZ\x00dump'

    def test_get_dump_with_a_missing_attachment(self, bmc, logged_in, tmp_path):
        bmc.on('GET', f'{TASKS}/0', http(200, load_json('mock_bmc_task_query_valid_debug_log_dump')))
        bmc.on('GET', self.ATTACHMENT, redfish_error('Base.1.19.ResourceNotFound', 'The requested resource was not found.', 404))
        ret, _ = logged_in.redfish_api_get_bmc_debug_log_dump('0', 'bmc.tar.xz', str(tmp_path))
        assert ret == RedfishClient.ERR_CODE_URI_NOT_FOUND
        assert not (tmp_path / 'bmc.tar.xz').exists()

    @pytest.mark.parametrize('drop, expected', [
        ('Payload', "Error: Missing 'Payload' field"),
        ('HttpHeaders', "Error: Missing 'HttpHeaders' field"),
    ])
    def test_get_dump_with_an_incomplete_task(self, bmc, logged_in, tmp_path, drop, expected):
        task = load_json('mock_bmc_task_query_valid_debug_log_dump')
        if drop == 'Payload':
            del task['Payload']
        else:
            del task['Payload']['HttpHeaders']
        bmc.on('GET', f'{TASKS}/0', http(200, task))
        assert logged_in.redfish_api_get_bmc_debug_log_dump('0', 'bmc.tar.xz', str(tmp_path)) == \
            (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, expected)

    def test_get_dump_without_a_location(self, bmc, logged_in, tmp_path):
        task = load_json('mock_bmc_task_query_valid_debug_log_dump')
        task['Payload']['HttpHeaders'] = ['Host: 10.0.1.1']
        bmc.on('GET', f'{TASKS}/0', http(200, task))
        assert logged_in.redfish_api_get_bmc_debug_log_dump('0', 'bmc.tar.xz', str(tmp_path)) == \
            (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, "Error: Missing 'Location' field")


class TestEeprom:

    def test_get_eeprom_info(self, bmc, logged_in):
        bmc.on('GET', f'{CHASSIS}/BMC_eeprom', http(200, load_json('mock_get_bmc_eeprom_response')))
        assert logged_in.redfish_api_get_eeprom_info('BMC_eeprom') == (OK, load_json('mock_parsed_bmc_eeprom_dict'))

    def test_get_eeprom_info_of_a_missing_eeprom(self, bmc, logged_in):
        bmc.on('GET', f'{CHASSIS}/BMC_eeprom', redfish_error('Base.1.19.ResourceNotFound', 'not found', 404))
        assert logged_in.redfish_api_get_eeprom_info('BMC_eeprom') == \
            (RedfishClient.ERR_CODE_URI_NOT_FOUND, {'State': 'Fail'})

    def test_get_eeprom_list(self, bmc, logged_in):
        bmc.on('GET', CHASSIS, http(200, load_json('mock_get_eeprom_list_response')))
        bmc.on('GET', f'{CHASSIS}/BMC_eeprom', http(200, {'Model': 'BMC1000'}))
        bmc.on('GET', f'{CHASSIS}/system_eeprom', http(500))
        ret, eeproms = logged_in.redfish_api_get_eeprom_list()
        assert ret == OK
        assert eeproms == [
            ('BMC_eeprom', {'Model': 'BMC1000', 'State': 'Ok', 'Health': 'Ok', 'HealthRollup': 'Ok'}),
            ('system_eeprom', {'State': 'Fail'})]

    def test_get_eeprom_list_skips_other_members(self, bmc, logged_in):
        bmc.on('GET', CHASSIS, http(200, {'Members': [{}, {'@odata.id': f'{CHASSIS}/Board_0'},
                                                      {'@odata.id': f'{CHASSIS}/BMC_eeprom'}]}))
        bmc.on('GET', f'{CHASSIS}/BMC_eeprom', http(200, {'Model': 'BMC1000'}))
        assert logged_in.redfish_api_get_eeprom_list() == \
            (OK, [('BMC_eeprom', {'Model': 'BMC1000', 'State': 'Ok', 'Health': 'Ok', 'HealthRollup': 'Ok'})])
        assert not bmc.sent('GET', f'{CHASSIS}/Board_0')

    def test_get_eeprom_list_without_members(self, bmc, logged_in):
        bmc.on('GET', CHASSIS, http(200, {'Name': 'Chassis Collection'}))
        assert logged_in.redfish_api_get_eeprom_list() == (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, [])

    def test_get_eeprom_list_failure(self, bmc, logged_in):
        bmc.on('GET', CHASSIS, http(500))
        assert logged_in.redfish_api_get_eeprom_list() == (RedfishClient.ERR_CODE_GENERIC_ERROR, [])


class TestAccounts:

    def test_change_own_password(self, bmc, logged_in):
        bmc.on('PATCH', f'{ACCOUNTS}/{USER}', http(204))
        assert logged_in.redfish_api_change_login_password('NewPass456!') == (OK, '')
        assert json_body(bmc.sent('PATCH', f'{ACCOUNTS}/{USER}')[0]) == {'Password': 'NewPass456!'}

    def test_change_password_of_another_user(self, bmc, logged_in):
        bmc.on('PATCH', f'{ACCOUNTS}/root', http(200, load_json('mock_change_bmc_login_password_success_response')))
        assert logged_in.redfish_api_change_login_password('NewPass456!', 'root') == (OK, '')

    def test_change_password_rejected(self, bmc, logged_in):
        bmc.on('PATCH', f'{ACCOUNTS}/{USER}', redfish_error(
            'Base.1.19.PropertyValueFormatError', "The value '******' for the property Password is not a format that the property can accept."))
        assert logged_in.redfish_api_change_login_password('weak') == \
            (RedfishClient.ERR_CODE_GENERIC_ERROR,
             "The value '******' for the property Password is not a format that the property can accept.")

    def test_change_password_with_a_property_error_in_a_success_response(self, bmc, logged_in):
        bmc.on('PATCH', f'{ACCOUNTS}/{USER}', http(200, {'Password@Message.ExtendedInfo': [{
            'MessageId': 'Base.1.19.PropertyValueFormatError', 'Message': 'Password is too short.',
            'Resolution': 'Use a longer password.'}]}))
        assert logged_in.redfish_api_change_login_password('weak') == \
            (RedfishClient.ERR_CODE_GENERIC_ERROR, 'Password is too short.')

    def test_change_password_ignores_a_property_success_message(self, bmc, logged_in):
        bmc.on('PATCH', f'{ACCOUNTS}/{USER}', http(200, {'Password@Message.ExtendedInfo': [{
            'MessageId': 'Base.1.19.PropertyValueModified', 'Message': 'The property Password was modified.'}]}))
        assert logged_in.redfish_api_change_login_password('NewPass456!') == (OK, '')

    def test_set_min_password_length(self, bmc, logged_in):
        bmc.on('PATCH', ACCOUNT_SERVICE, http(204))
        assert logged_in.redfish_api_set_min_password_length(8) == (OK, '')
        assert json_body(bmc.sent('PATCH', ACCOUNT_SERVICE)[0]) == {'MinPasswordLength': 8}

    def test_set_min_password_length_with_an_error_in_a_success_response(self, bmc, logged_in):
        bmc.on('PATCH', ACCOUNT_SERVICE, http(200, load_json('mock_bmc_set_min_password_length_failure_response')))
        ret, msg = logged_in.redfish_api_set_min_password_length(5)
        assert ret == RedfishClient.ERR_CODE_GENERIC_ERROR
        assert msg.startswith("The property 'MinPasswordLength' with the requested value of '5'")

    def test_get_min_password_length(self, bmc, logged_in):
        bmc.on('GET', ACCOUNT_SERVICE, http(200, load_json('mock_bmc_get_account_service_response')))
        assert logged_in.redfish_api_get_min_password_length() == (OK, 13)

    def test_get_min_password_length_failure(self, bmc, logged_in):
        bmc.on('GET', ACCOUNT_SERVICE, redfish_error('Base.1.19.InternalError', 'The request failed due to an internal service error.', 500))
        assert logged_in.redfish_api_get_min_password_length() == \
            (RedfishClient.ERR_CODE_GENERIC_ERROR, 'The request failed due to an internal service error.')

    def test_get_min_password_length_missing(self, bmc, logged_in):
        bmc.on('GET', ACCOUNT_SERVICE, http(200, {'Id': 'AccountService'}))
        assert logged_in.redfish_api_get_min_password_length() == \
            (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, 'Error: MinPasswordLength not found in response')


class TestBmcReset:

    @pytest.mark.parametrize('reset_type', [RedfishClient.REDFISH_BMC_GRACEFUL_RESTART,
                                            RedfishClient.REDFISH_BMC_FORCE_RESTART])
    def test_request_bmc_reset(self, bmc, logged_in, reset_type):
        bmc.on('POST', BMC_RESET, http(204))
        assert logged_in.redfish_api_request_bmc_reset(reset_type) == (OK, '')
        assert json_body(bmc.sent('POST', BMC_RESET)[0]) == {'ResetType': reset_type}

    def test_request_bmc_reset_with_an_unsupported_type(self, bmc, logged_in):
        bmc.on('POST', BMC_RESET, redfish_error(
            'Base.1.19.ActionParameterUnknown',
            "The action Manager.Reset was submitted with the invalid parameter ResetType."))
        assert logged_in.redfish_api_request_bmc_reset('ForceRestart') == \
            (RedfishClient.ERR_CODE_UNSUPPORTED_PARAMETER,
             "The action Manager.Reset was submitted with the invalid parameter ResetType.")


class TestTaskEventHandlers:

    @pytest.mark.parametrize('event_msg, expected', [
        ({'MessageId': 'ResourceEvent.1.0.UpdateSuccessful', 'MessageArgs': ['arg1', 'arg2']}, (True, '')),
        ({'MessageId': 'ResourceEvent.1.0.UpdateSuccessful'},
         (False, "Error: Missing 'MessageArgs' field for ResourceEvent.1.0.UpdateSuccessful")),
        ({'MessageId': 'ResourceEvent.1.0.UpdateSuccessful', 'MessageArgs': ['arg1']},
         (False, "Error: 'MessageArgs' field for ResourceEvent.1.0.UpdateSuccessful has less than 2 elements")),
    ], ids=['valid', 'missing-args', 'one-arg'])
    def test_validate_message_args(self, client, event_msg, expected):
        assert client._RedfishClient__validate_message_args(event_msg) == expected

    def test_update_successful(self, client):
        context = {}
        msg = {'MessageId': 'ResourceEvent.1.0.UpdateSuccessful', 'MessageArgs': ['BMC_FW_0', 'Success']}
        assert client._RedfishClient__update_successful_handler(msg, context) == (OK, '')
        assert client._RedfishClient__update_successful_handler(dict(msg, MessageArgs=['BIOS_FW_0', 'x']), context) == (OK, '')
        assert context['updated_components'] == ['BMC_FW_0', 'BIOS_FW_0']

    def test_component_update_skipped(self, client):
        context = {}
        msg = {'MessageId': 'ResourceEvent.1.0.ComponentUpdateSkipped', 'MessageArgs': ['BMC_FW_0', 'Identical version']}
        assert client._RedfishClient__component_update_skipped_handler(msg, context) == (OK, '')
        assert context.get('identical_version') is True

    def test_resource_errors_lower_version(self, client):
        context = {}
        msg = {'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected',
               'MessageArgs': ['BMC_FW_0', 'Version is lower than the firmware component comparison stamp']}
        assert client._RedfishClient__resource_errors_detected_handler(msg, context) == (OK, '')
        assert context.get('lower_version') is True
        assert context.get('err_detected') is True

    def test_resource_errors_identical_version(self, client):
        context = {}
        msg = {'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected',
               'MessageArgs': ['BMC_FW_0', 'Component image is identical to the current version']}
        assert client._RedfishClient__resource_errors_detected_handler(msg, context) == (OK, '')
        assert context.get('identical_version') is True
        assert not context.get('err_detected', False)

    def test_resource_errors_generic_error(self, client):
        context = {}
        msg = {'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected', 'MessageArgs': ['BMC_FW_0', 'Some generic error message']}
        assert client._RedfishClient__resource_errors_detected_handler(msg, context) == (OK, '')
        assert context.get('err_detected') is True
        assert context['ret_msg'] == 'Error: Some generic error message'

    def test_resource_errors_are_not_duplicated(self, client):
        context = {'ret_msg': 'Error: Duplicate error\n'}
        msg = {'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected', 'MessageArgs': ['BMC_FW_0', 'Duplicate error']}
        assert client._RedfishClient__resource_errors_detected_handler(msg, context) == (OK, '')
        assert context['ret_msg'].count('Duplicate error') == 1

    @pytest.mark.parametrize('handler, event_msg, expected_err', [
        ('__update_successful_handler', {'MessageId': 'ResourceEvent.1.0.UpdateSuccessful'}, 'Missing'),
        ('__component_update_skipped_handler',
         {'MessageId': 'ResourceEvent.1.0.ComponentUpdateSkipped', 'MessageArgs': ['only_one']}, 'less than 2'),
        ('__resource_errors_detected_handler', {'MessageId': 'ResourceEvent.1.0.ResourceErrorsDetected'}, 'Missing'),
    ], ids=['update-successful', 'update-skipped', 'resource-errors'])
    def test_handler_with_invalid_message_args(self, client, handler, event_msg, expected_err):
        context = {}
        ret, err_msg = getattr(client, '_RedfishClient' + handler)(event_msg, context)
        assert ret == RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
        assert expected_err in err_msg
        assert context == {}

    def test_task_aborted(self, client):
        context = {}
        assert client._RedfishClient__task_aborted_handler({'MessageId': 'TaskEvent.1.0.TaskAborted'}, context) == (OK, '')
        assert context.get('aborted') is True

    def test_dispatch_event_without_a_message_id(self, client):
        assert client._RedfishClient__dispatch_event({}, {}) == \
            (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, "Error: Missing 'MessageId' field")

    def test_dispatch_event_ignores_unknown_events(self, client):
        context = {}
        assert client._RedfishClient__dispatch_event({'MessageId': 'TaskEvent.1.0.TaskStarted'}, context) == (OK, '')
        assert context == {}

    def test_log_multi_line_str_with_none(self, client):
        with mock.patch('sonic_platform_base.redfish_client.logger') as log:
            client.log_multi_line_str(None)
        log.log_notice.assert_not_called()
