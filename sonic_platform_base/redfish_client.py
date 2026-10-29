"""
    redfish_client.py

    RedfishClient class provides BMC access via Redfish APIs, built on the DMTF redfish library.

"""


import json
import logging
import os
import re
import time
from datetime import datetime

from sonic_py_common.logger import Logger


logger = Logger('redfish_client')

# The library logs request headers, incl. the session token, at DEBUG: keep its records out of all logs
logging.getLogger('redfish').addHandler(logging.NullHandler())
logging.getLogger('redfish').propagate = False


class RedfishClient:

    '''
    Redfish client of the BMC
    '''

    DEFAULT_TIMEOUT = 3
    DEFAULT_LOGIN_TIMEOUT = 4
    ACTION_TIMEOUT = 120
    # Retries of a GET on timeout; other requests are never resent
    MAX_RETRY = 2

    SCHEME_HTTPS = 'https'
    SCHEME_HTTP = 'http'
    DEFAULT_SCHEME = SCHEME_HTTPS

    REDFISH_URI_FW_INVENTORY = '/redfish/v1/UpdateService/FirmwareInventory'
    REDFISH_URI_CHASSIS_INVENTORY = '/redfish/v1/Chassis'
    REDFISH_URI_TASKS = '/redfish/v1/TaskService/Tasks'
    REDFISH_URI_UPDATE_SERVICE_UPDATE_MULTIPART = '/redfish/v1/UpdateService/update-multipart'
    REDFISH_URI_UPDATE_SERVICE = '/redfish/v1/UpdateService'
    REDFISH_URI_ACCOUNTS = '/redfish/v1/AccountService/Accounts'
    REDFISH_URI_ACCOUNT_SERVICE = '/redfish/v1/AccountService'
    REDFISH_URI_SESSION_SERVICE = '/redfish/v1/SessionService/Sessions'
    REDFISH_BMC_LOG_DUMP = '/redfish/v1/Managers/BMC_0/LogServices/Dump/Actions'
    REDFISH_REQUEST_SYSTEM_RESET = '/redfish/v1/Systems/System_0/Actions/ComputerSystem.Reset'
    REDFISH_REQUEST_BMC_RESET = '/redfish/v1/Managers/BMC_0/Actions/Manager.Reset'

    ERR_CODE_OK = 0
    ERR_CODE_AUTH_FAILURE = -1
    ERR_CODE_INVALID_JSON_FORMAT = -2
    ERR_CODE_UNEXPECTED_RESPONSE = -3
    ERR_CODE_CURL_FAILURE = -4  # transport failure; name kept for API compatibility
    ERR_CODE_NOT_LOGIN = -5
    ERR_CODE_TIMEOUT = -6
    ERR_CODE_LOWER_VERSION = -7
    ERR_CODE_PASSWORD_UNAVAILABLE = -8
    ERR_CODE_URI_NOT_FOUND = -9
    ERR_CODE_SERVER_UNREACHABLE = -10
    ERR_CODE_UNSUPPORTED_PARAMETER = -11
    ERR_CODE_GENERIC_ERROR = -12
    ERR_CODE_IDENTICAL_VERSION = -13

    # Readiness-poll defaults for wait_until_redfish_ready() (after a BMC restart).
    READY_POLL_TIMEOUT = 300     # seconds, hard upper bound on the readiness wait
    READY_POLL_INTERVAL = 10     # seconds between readiness probes

    # Checked before the HTTP status: a BMC may answer a missing resource with 400
    REDFISH_REASON_TO_ERR_CODE = {
        'ResourceNotFound':       ERR_CODE_URI_NOT_FOUND,
        'ResourceMissingAtURI':   ERR_CODE_URI_NOT_FOUND,
        'ActionParameterUnknown': ERR_CODE_UNSUPPORTED_PARAMETER,
    }

    HTTP_STATUS_TO_ERR_CODE = {
        401: ERR_CODE_AUTH_FAILURE,
        404: ERR_CODE_URI_NOT_FOUND,
    }

    REDFISH_BMC_GRACEFUL_RESTART = 'GracefulRestart'
    REDFISH_BMC_FORCE_RESTART = 'ForceRestart'

    '''
    Constructor
    Callbacks are provided because:
    1. Each BMC instance may have its own BMC users management mechanism.
    2. Password is not allowed to be saved for security concern.
    3. If token expires or becomes invalid for some reason (for example, being revoked from BMC web interface),
    RedfishClient will do login retry in which password is required anyway. It will get password from an external password provider,
    for example class BMC which holds the responsibility of generating password from TPM.

    Args:
        ip_addr: A string, IP address of the BMC
        user_callback: A callback function which returns the user name string
        password_callback: A callback function which returns the password string
        scheme_callback: A callback function which returns the URI scheme, 'https' (default) or 'http'
        cafile: A string, CA file to verify the BMC certificate with. If None, it is not verified.
    '''
    def __init__(self, ip_addr, user_callback, password_callback, scheme_callback=None, cafile=None):
        self.__svr_ip = ip_addr
        self.__user_callback = user_callback
        self.__password_callback = password_callback
        self.__scheme_callback = scheme_callback
        # Imported here, not at module level: every pmon daemon imports this module, BMC or not
        import redfish
        # max_retry=0: the library's own retry resends any request, even an action; __send resends only GETs
        self.__rf = redfish.redfish_client(base_url=f'{RedfishClient.DEFAULT_SCHEME}://{ip_addr}',
                                           timeout=RedfishClient.DEFAULT_LOGIN_TIMEOUT,
                                           max_retry=0,
                                           cafile=cafile,
                                           check_connectivity=False)
        self.__task_status_event_handlers = {}
        self.__register_task_status_event_handlers()
        logger.log_notice(f'RedfishClient instance (to {self.__svr_ip}) is created\n')

    '''
    Build the base URL of all Redfish requests; an unsupported scheme falls back to DEFAULT_SCHEME

    Returns:
        A string, '<scheme>://<BMC IP address>'
    '''
    def __base_url(self):
        scheme = self.__scheme_callback() if self.__scheme_callback \
                 else RedfishClient.DEFAULT_SCHEME
        if scheme not in (RedfishClient.SCHEME_HTTPS, RedfishClient.SCHEME_HTTP):
            logger.log_error(f'Unsupported Redfish URI scheme "{scheme}", '
                             f'falling back to {RedfishClient.DEFAULT_SCHEME}\n')
            scheme = RedfishClient.DEFAULT_SCHEME
        return f'{scheme}://{self.__svr_ip}'

    '''
    Get the redfish library client for a new request, pointed at the current base URL

    Returns:
        The redfish library client
    '''
    def __connection(self):
        self.__rf.set_base_url(self.__base_url())
        return self.__rf

    '''
    Get the error under a RetriesExhaustedError of the redfish library

    Args:
        exc: An exception raised by the redfish library

    Returns:
        The exception that caused exc if exc is a RetriesExhaustedError, exc otherwise
    '''
    def __unwrap_retries(self, exc):
        from redfish.rest.v1 import RetriesExhaustedError
        if isinstance(exc, RetriesExhaustedError) and exc.__cause__:
            return exc.__cause__
        return exc

    '''
    Translate an exception raised on the way to the BMC to RedfishClient error code

    Args:
        exc: An exception raised by the redfish library

    Returns:
        An integer, RedfishClient error code
    '''
    def __exception_to_err_code(self, exc):
        import requests
        from redfish.rest.v1 import InvalidCredentialsError, RedfishPasswordChangeRequiredError, \
            ServerDownOrUnreachableError, SessionCreationError
        exc = self.__unwrap_retries(exc)
        if isinstance(exc, requests.exceptions.Timeout):
            return RedfishClient.ERR_CODE_TIMEOUT
        if isinstance(exc, (requests.exceptions.ConnectionError, ServerDownOrUnreachableError)):
            return RedfishClient.ERR_CODE_SERVER_UNREACHABLE
        if isinstance(exc, (InvalidCredentialsError, RedfishPasswordChangeRequiredError)):
            return RedfishClient.ERR_CODE_AUTH_FAILURE
        if isinstance(exc, SessionCreationError):
            return RedfishClient.ERR_CODE_GENERIC_ERROR
        if isinstance(exc, requests.exceptions.RequestException):
            return RedfishClient.ERR_CODE_CURL_FAILURE
        return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE

    '''
    Tell whether an exception means that the BMC dropped an open connection, for example
    a kept-alive one from before a BMC reboot, as opposed to a connection that could not be opened

    Args:
        exc: An exception raised by the redfish library

    Returns:
        A boolean
    '''
    def __is_dropped_connection(self, exc):
        import requests
        from urllib3.exceptions import ProtocolError
        exc = self.__unwrap_retries(exc)
        return isinstance(exc, requests.exceptions.ConnectionError) and \
            bool(exc.args) and isinstance(exc.args[0], ProtocolError)

    '''
    Classify a Redfish response by its Redfish message reason first, then by its HTTP status

    Args:
        response: A RestResponse of the redfish library

    Returns:
        A tuple of (ret, json_response, err_msg)
    '''
    def __classify_response(self, response):
        from redfish.rest.v1 import JsonDecodingError
        try:
            json_response = response.dict
        except JsonDecodingError:
            if response.status < 400:
                return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, None, 'Invalid JSON format')
            json_response = {}

        error = json_response.get('error') if isinstance(json_response, dict) else None
        if response.status < 400 and error is None:
            return (RedfishClient.ERR_CODE_OK, json_response, '')

        error = error or {}
        messages = error.get('@Message.ExtendedInfo') or \
                   [{'MessageId': error.get('code', ''), 'Message': error.get('message', '')}]
        reasons = [msg.get('MessageId', '').rsplit('.', 1)[-1] for msg in messages]
        ret = next((RedfishClient.REDFISH_REASON_TO_ERR_CODE[reason] for reason in reasons
                    if reason in RedfishClient.REDFISH_REASON_TO_ERR_CODE),
                   RedfishClient.HTTP_STATUS_TO_ERR_CODE.get(response.status, RedfishClient.ERR_CODE_GENERIC_ERROR))
        err_msg = next((msg['Message'] for msg in messages if msg.get('Message')),
                       f'HTTP status code {response.status}')
        return (ret, json_response, err_msg)

    '''
    Send a Redfish request; a GET is resent after a timeout or a dropped connection, up to MAX_RETRY times

    Args:
        method: A string, the HTTP method
        uri: A string, the Redfish URI
        quiet: A boolean, whether to skip logging a successful exchange
        timeout: An integer, the socket timeout in seconds; DEFAULT_TIMEOUT for a GET, ACTION_TIMEOUT otherwise if None
        kwargs: body/headers of the request

    Returns:
        A tuple of (ret, response, err_msg)
    '''
    def __send(self, method, uri, quiet=False, timeout=None, **kwargs):
        is_get = (method == 'GET')
        if timeout is None:
            timeout = RedfishClient.DEFAULT_TIMEOUT if is_get else RedfishClient.ACTION_TIMEOUT
        log_uri = re.sub(r'/(Sessions|Accounts)/[^/]+', r'/\1/******', uri)

        for _ in range(1 + RedfishClient.MAX_RETRY if is_get else 1):
            # The library rewrites the headers it is given; a callable body is rebuilt for every send
            send_kwargs = dict(kwargs)
            if 'headers' in kwargs:
                send_kwargs['headers'] = dict(kwargs['headers'])
            if callable(kwargs.get('body')):
                send_kwargs['body'] = kwargs['body']()
            try:
                send = getattr(self.__connection(), method.lower())
                response = send(uri, timeout=timeout, **send_kwargs)
            except Exception as e:
                ret, err_msg = self.__exception_to_err_code(e), str(e.__cause__ or e)
                logger.log_notice(f'Redfish {method} {log_uri} failed: {err_msg}')
                if ret == RedfishClient.ERR_CODE_TIMEOUT or self.__is_dropped_connection(e):
                    continue
                return (ret, None, err_msg)

            if not quiet or response.status >= 400:
                logger.log_notice(f'Redfish {method} {log_uri}: HTTP {response.status}')
            return (RedfishClient.ERR_CODE_OK, response, '')
        return (ret, None, err_msg)

    '''
    Send a Redfish request in the current session. On HTTP 401, re-login and resend it once.

    Args:
        method: A string, the HTTP method
        uri: A string, the Redfish URI
        login_again: A boolean, whether to re-login on HTTP 401
        raw: A boolean, return the response itself instead of its JSON body on success
        quiet: A boolean, whether to skip logging a successful exchange
        kwargs: body/headers of the request

    Returns:
        A tuple of (ret, json_response or response, err_msg)
    '''
    def __request(self, method, uri, login_again=True, raw=False, quiet=False, **kwargs):
        if not self.has_login():
            logger.log_error('Need to login first before executing Redfish request')
            return (RedfishClient.ERR_CODE_NOT_LOGIN, None, 'Not login')

        ret, response, err_msg = self.__send(method, uri, quiet, **kwargs)
        if response is not None and response.status == 401 and login_again:
            # Token may become invalid, for example, remote side may clear the session table or change password.
            logger.log_notice('Re-login and retry last request...')
            self.invalidate_session()
            ret = self.login()
            if ret != RedfishClient.ERR_CODE_OK:
                return (ret, None, 'Authentication failure')
            ret, response, err_msg = self.__send(method, uri, quiet, **kwargs)

        if response is None:
            return (ret, None, err_msg)
        if response.status == 401:
            self.invalidate_session()
        if raw and response.status < 400:
            return (RedfishClient.ERR_CODE_OK, response, '')
        ret, json_response, err_msg = self.__classify_response(response)
        if ret != RedfishClient.ERR_CODE_OK:
            logger.log_notice(f'Redfish {method} request failed with error {ret}: {err_msg}')
        return (ret, json_response, err_msg)

    '''
    Extract URI from the job response

    Args:
        json_response: A dictionary, the task status response

    Returns:
        A tuple of (ret, err_msg, uri)
    '''
    def __get_uri_from_response(self, json_response):
        if "Payload" not in json_response:
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, "Error: Missing 'Payload' field", None)

        payload = json_response["Payload"]
        if "HttpHeaders" not in payload:
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, "Error: Missing 'HttpHeaders' field", None)

        uri = None
        for header in payload["HttpHeaders"]:
            if "Location" in header:
                uri = header.split()[-1]

        if not uri:
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, "Error: Missing 'Location' field", None)

        return (RedfishClient.ERR_CODE_OK, "", uri)

    '''
    Get the ID of the task started by a Redfish request

    Args:
        json_response: A dictionary, the response of the request

    Returns:
        A tuple of (ret, task_id, err_msg)
    '''
    def __get_task_id(self, json_response):
        if 'TaskStatus' not in json_response:
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, None, "Error: Missing 'TaskStatus' field in response")
        status = json_response['TaskStatus']
        if status != 'OK':
            return (RedfishClient.ERR_CODE_GENERIC_ERROR, None, f'Error: Return status is {status}')
        return (RedfishClient.ERR_CODE_OK, json_response.get('Id', ''), '')

    '''
    Wait for given task to complete

    Args:
        task_id: A string, the task ID to be monitored
        timeout: An integer, overall timeout in seconds
        progress_callback: A callback function to report progress
        sleep_timeout: An integer, sleep time between polling in seconds

    Returns:
        A dictionary with the following fields:
            ret_code: return code
            ret_msg:  return message
            response: JSON response of the last polling
    '''
    def __wait_task_completion(self, task_id, timeout = 1800, progress_callback = None, sleep_timeout = 2):
        uri = f'{RedfishClient.REDFISH_URI_TASKS}/{task_id}'
        prev_status = None
        prev_percent = None
        start_tm = time.time()
        timeout_cnt = 0

        while True:
            # Dictionary which may vary with messages received.
            # At least it will have the following 3 fields.
            result = {
                'ret_code': RedfishClient.ERR_CODE_OK,
                'ret_msg': '',
                'response': None
            }
            timestamp = datetime.now().strftime("%H:%M:%S.%f")

            ret, json_response, err_msg = self.__request('GET', uri, quiet=True)
            result['response'] = json_response

            # If timeout occurred, check if we exceeded the overall timeout counter, otherwise continue polling
            if (ret == RedfishClient.ERR_CODE_TIMEOUT and (timeout_cnt < 10)):
                timeout_cnt += 1
                logger.log_notice(f'Timeout on checking task {task_id} status, retry count {timeout_cnt}')
                time.sleep(sleep_timeout)
                continue
            timeout_cnt = 0

            if (ret != RedfishClient.ERR_CODE_OK):
                result['ret_code'] = ret
                result['ret_msg'] = f"Error: {err_msg}"
                return result

            # Format validation
            attrs = ['PercentComplete', 'TaskStatus', 'Messages']
            for attr in attrs:
                if attr not in json_response:
                    result['ret_code'] = RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
                    result['ret_msg'] = f"Error: Missing '{attr}' field in task status response"
                    return result

            # Go through all the messages in the response
            for msg in json_response['Messages']:
                ret, ret_msg = self.__dispatch_event(msg, result)

            status = json_response["TaskStatus"]
            percent = json_response['PercentComplete']

            # Log the task status only if status or percent changed
            if (prev_status != status or prev_percent != percent):
                logger.log_notice(f'Task {task_id} status at {timestamp}:')
                self.log_multi_line_str(json.dumps(json_response, indent=2))

                prev_status = status
                prev_percent = percent

            # Progress reporting
            if progress_callback and percent:
                progress_data = {
                    # Put here more data if needed
                    'percent': percent
                }
                progress_callback(progress_data)

            # If status is not OK, return immediately
            if (status != 'OK'):
                error_detected = result.get('err_detected', False)
                aborted = result.get('aborted', False)
                result['ret_code'] = RedfishClient.ERR_CODE_GENERIC_ERROR
                if not error_detected:
                    if aborted:
                        result['ret_msg'] += 'Error: The task has been aborted\n'
                    else:
                        result['ret_msg'] = f'Error: Fail to execute the task - Taskstatus={status}'
                result['ret_msg'] = result['ret_msg'].strip()
                return result

            if percent is None:
                continue

            # Return if task is completed
            if (percent == 100):
                return result

            # Check if we have timeout
            if (time.time() - start_tm > timeout):
                result['ret_code'] = RedfishClient.ERR_CODE_TIMEOUT
                result['ret_msg'] += 'Error: Wait task completion timeout\n'
                logger.log_notice(f'Task {task_id} status polling timeout after {timeout} seconds')
                return result

            time.sleep(sleep_timeout)

    '''
    Register task status event handlers
    '''
    def __register_task_status_event_handlers(self):
        self.__task_status_event_handlers = {
            'UpdateSuccessful': self.__update_successful_handler,
            'ResourceErrorsDetected': self.__resource_errors_detected_handler,
            'ComponentUpdateSkipped': self.__component_update_skipped_handler,
            'TaskAborted': self.__task_aborted_handler
        }

    '''
    Validate message arguments for some task status event handlers

    Args:
        event_msg: A dictionary, the event message to be validated

    Returns:
        A tuple of (is_valid, err_msg)
    '''
    def __validate_message_args(self, event_msg):
        msg_id = event_msg['MessageId']
        if 'MessageArgs' not in event_msg:
            err_msg = f"Error: Missing 'MessageArgs' field for {msg_id}"
            return (False, err_msg)
        if len(event_msg['MessageArgs']) < 2:
            err_msg = f"Error: 'MessageArgs' field for {msg_id} has less than 2 elements"
            return (False, err_msg)
        return (True, '')

    '''
    Handler of ResourceEvent.1.0.UpdateSuccessful

    Args:
        event_msg: A dictionary, the event message to be handled
        context: A dictionary, context to be updated

    Returns:
        A tuple of (ret, err_msg)
    '''
    def __update_successful_handler(self, event_msg, context):
        valid, err_msg = self.__validate_message_args(event_msg)
        if not valid:
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, err_msg)
        comp_id = event_msg['MessageArgs'][0]
        if 'updated_components' in context:
            context['updated_components'].append(comp_id)
        else:
            context['updated_components'] = [comp_id]
        return (RedfishClient.ERR_CODE_OK, '')

    '''
    Handler of ResourceEvent.1.0.ComponentUpdateSkipped

    Args:
        event_msg: A dictionary, the event message to be handled
        context: A dictionary, context to be updated

    Returns:
        A tuple of (ret, err_msg)
    '''
    def __component_update_skipped_handler(self, event_msg, context):
        valid, err_msg = self.__validate_message_args(event_msg)
        if not valid:
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, err_msg)
        context['identical_version'] = True
        return (RedfishClient.ERR_CODE_OK, '')

    '''
    Handler of ResourceEvent.1.0.ResourceErrorsDetected

    Args:
        event_msg: A dictionary, the event message to be handled
        context: A dictionary, context to be updated

    Returns:
        A tuple of (ret, err_msg)
    '''
    def __resource_errors_detected_handler(self, event_msg, context):
        valid, err_msg = self.__validate_message_args(event_msg)
        if not valid:
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, err_msg)

        LOWER_VER_STR = 'lower than the firmware component comparison stamp'
        IDENTICAL_VER_STR = 'Component image is identical'

        # args: comp_id, err_str
        args = event_msg['MessageArgs']
        err_str = args[1]
        err_msg = f'Error: {err_str}'

        # Identical version detected
        if IDENTICAL_VER_STR in err_str:
            context['identical_version'] = True
            return (RedfishClient.ERR_CODE_OK, '')

        # Version downgrade detected
        if LOWER_VER_STR in err_str:
            context['lower_version'] = True
            err_msg = 'Error: The target image has lower version\n'

        if 'ret_msg' not in context:
            context['ret_msg'] = err_msg
        else:
            if err_msg not in context['ret_msg']:
                context['ret_msg'] = context['ret_msg'] + err_msg + '\n'

        context['err_detected'] = True
        return (RedfishClient.ERR_CODE_OK, '')

    '''
    Handler of ResourceEvent.1.0.TaskAborted

    Args:
        event_msg: A dictionary, the event message to be handled
        context: A dictionary, context to be updated

    Returns:
        A tuple of (ret, err_msg)
    '''
    def __task_aborted_handler(self, event_msg, context):
        context['aborted'] = True
        return (RedfishClient.ERR_CODE_OK, '')

    '''
    Dispatch task status event to the corresponding handler

    Args:
        event_msg: A dictionary, the event message to be dispatched
        context: A dictionary, context to be updated

    Returns:
        A tuple of (ret, err_msg)
    '''
    def __dispatch_event(self, event_msg, context):
        if 'MessageId' not in event_msg:
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, f"Error: Missing 'MessageId' field")
        msg_id = event_msg['MessageId']
        event_name = msg_id.split('.')[-1]
        handler = self.__task_status_event_handlers.get(event_name)
        if not handler:
            return (RedfishClient.ERR_CODE_OK, '')
        return handler(event_msg, context)

    '''
    Log multi-line string line by line

    Args:
        msg: A string, the multi-line string to be logged
    '''
    def log_multi_line_str(self, msg):
        if msg is None:
            return
        lines = msg.splitlines()
        for line in lines:
            logger.log_notice(f'{line}')

    '''
    Get current login token

    Returns:
        A string, the current bearer token
    '''
    def get_login_token(self):
        return self.__rf.get_session_key()

    '''
    Get current session ID

    Returns:
        A string, the current session ID
    '''
    def get_session_id(self):
        location = self.__rf.get_session_location()
        return location.rstrip('/').split('/')[-1] if location else None

    '''
    Invalidate current token and session ID
    '''
    def invalidate_session(self):
        logger.log_notice(f'Invalidate login token and session')
        self.__rf.set_session_key(None)
        self.__rf.set_session_location(None)

    '''
    Open a new session by logging in and return the session ID and token

    Returns:
        A tuple of (ret, (msg, (session_id, token)))
    '''
    def open_session(self):
        self.login()
        if not self.has_login():
            return RedfishClient.ERR_CODE_NOT_LOGIN, ('Failed to open session', None)
        return RedfishClient.ERR_CODE_OK, ('Login successful', (self.get_session_id(), self.get_login_token()))

    '''
    Close the given session by session ID

    Args:
        session_id: A string, the session ID to be closed

    Returns:
        A tuple of (ret, msg)
    '''
    def close_session(self, session_id):
        try:
            if not self.has_login():
                return RedfishClient.ERR_CODE_NOT_LOGIN, 'Not logged in'

            ret, json_response, error = self.__request('GET', RedfishClient.REDFISH_URI_SESSION_SERVICE)
            if ret != RedfishClient.ERR_CODE_OK:
                msg = f'Failed to get session list: {error}'
                logger.log_error(msg)
                return ret, msg

            members = json_response.get('Members', [])
            session_exists = False
            for member in members:
                member_odata_id = member.get('@odata.id', '')
                if member_odata_id.endswith(f'/{session_id}'):
                    session_exists = True
                    break
            if not session_exists:
                logger.log_notice(f'Session {session_id} does not exist, no logout needed')
                return RedfishClient.ERR_CODE_OK, 'Session does not exist'

            res = self.logout(session_id)
            if res != RedfishClient.ERR_CODE_OK:
                msg = f'Failed to close session: {res}'
                logger.log_error(msg)
                return res, msg
            return RedfishClient.ERR_CODE_OK, 'Session closed successfully'

        except Exception as e:
            msg = f'Failed to close session: {str(e)}'
            logger.log_error(msg)
            return RedfishClient.ERR_CODE_GENERIC_ERROR, msg

    '''
    Check if already logged in

    Returns:
        A boolean, True if already logged in; False otherwise
    '''
    def has_login(self):
        return self.__rf.get_session_key() is not None and self.__rf.get_session_location() is not None

    '''
    Login Redfish server and get bearer token

    Args:
        log_errors: When False, log failures at notice not error (readiness poll).

    Returns:
        An integer, return code
    '''
    def login(self, *, log_errors=True):
        if self.has_login():
            return RedfishClient.ERR_CODE_OK

        log_fn = logger.log_error if log_errors else logger.log_notice

        try:
            password = self.__password_callback()
        except Exception as e:
            log_fn(f'{str(e)}')
            return RedfishClient.ERR_CODE_PASSWORD_UNAVAILABLE

        from redfish.rest.v1 import AuthMethod, RedfishPasswordChangeRequiredError
        # Resent once if the BMC dropped the connection, as it does to a kept-alive one when it reboots
        for resend in (False, True):
            rf = self.__connection()
            try:
                rf.login(username=self.__user_callback(), password=password, auth=AuthMethod.SESSION)
                break
            except Exception as e:
                if not resend and self.__is_dropped_connection(e):
                    logger.log_notice(f'Login failed on a dropped connection, resending: {e.__cause__ or e}')
                    continue
                # The BMC opened a session that can only change the password; close it there too
                if isinstance(e, RedfishPasswordChangeRequiredError):
                    self.logout()
                self.invalidate_session()
                ret = self.__exception_to_err_code(e)
                log_fn(f'Login failure: code {ret}, {e.__cause__ or e}')
                return ret
            finally:
                rf.set_password(None)  # nosemgrep: python.django.security.audit.unvalidated-password.unvalidated-password

        if not self.has_login():
            log_fn('Login failure: no session token or location in the response')
            self.invalidate_session()
            return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE

        logger.log_notice('Redfish login successfully with session token and session ID updated')
        return RedfishClient.ERR_CODE_OK

    '''
    Logout Redfish server

    Args:
        session_id: A string, the session to close; the current one if None

    Returns:
        An integer, return code
    '''
    def logout(self, session_id=None):
        if session_id:
            logger.log_notice(f'Close the following session {session_id}')
        else:
            logger.log_notice('Close the current session')

        # If session_id=None so we want to close the current session
        if not session_id and not self.has_login():
            return RedfishClient.ERR_CODE_OK

        logger.log_notice('Logout redfish session')
        uri = f'{RedfishClient.REDFISH_URI_SESSION_SERVICE}/{session_id or self.get_session_id()}'
        ret, _, err_msg = self.__request('DELETE', uri, login_again=False)
        # Invalidate token and session ID anyway (if session_id=None)
        if not session_id:
            self.invalidate_session()

        if ret != RedfishClient.ERR_CODE_OK:
            logger.log_notice(f'Logout failure: {err_msg}')
        else:
            logger.log_notice('Redfish logout successful')
        return ret

    '''
    Poll a quiet login() until the Redfish service accepts it or the timeout
    elapses. Used after a BMC restart; a successful login is a stronger "ready"
    signal than ping / L3.

    Args:
        timeout: Hard upper bound in seconds on the total wait.
        interval: Seconds to sleep between probes.

    Returns:
        ERR_CODE_OK (0) when ready, else the last non-OK code seen (timeout or a
        non-transient failure).
    '''
    def wait_until_redfish_ready(self, timeout=READY_POLL_TIMEOUT,
                                 interval=READY_POLL_INTERVAL):
        # Drop any cached session first, or login() short-circuits to OK on the
        # cached token and falsely reports "ready". invalidate_session() is
        # local-only, so (unlike a logout DELETE) it can't log an ERROR.
        self.invalidate_session()

        deadline = time.time() + timeout
        last_code = None
        while True:
            last_code = self.login(log_errors=False)
            if last_code == RedfishClient.ERR_CODE_OK:
                self.logout()
                logger.log_notice('BMC Redfish service is ready')
                return RedfishClient.ERR_CODE_OK

            # Fail fast only on a local permanent error. AUTH_FAILURE (401) is
            # transient here: on boot the web server precedes the auth backend.
            if last_code == RedfishClient.ERR_CODE_PASSWORD_UNAVAILABLE:
                return last_code

            remaining = deadline - time.time()
            if remaining <= 0:
                return last_code
            logger.log_notice('Waiting for BMC Redfish service to become ready...')
            time.sleep(min(interval, remaining))

    '''
    Get firmware inventory

    Returns:
        A tuple of (ret, fw_list)
    '''
    def redfish_api_get_firmware_list(self):
        ret, json_response, error = self.__request('GET', RedfishClient.REDFISH_URI_FW_INVENTORY)
        if (ret != RedfishClient.ERR_CODE_OK):
            logger.log_error(f'Fail to get firmware list: {error}')
            return (ret, [])
        if 'Members' not in json_response:
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, [])
        fw_list = []
        for item in json_response['Members']:
            fw_id = item["@odata.id"].split('/')[-1]
            ret, version = self.redfish_api_get_firmware_version(fw_id)
            fw_list.append((fw_id, version))
        return (RedfishClient.ERR_CODE_OK, fw_list)

    '''
    Get firmware version by given ID

    Args:
        fw_id: A string, the firmware ID

    Returns:
        A tuple of (ret, version)
    '''
    def redfish_api_get_firmware_version(self, fw_id):
        uri = f'{RedfishClient.REDFISH_URI_FW_INVENTORY}/{fw_id}'
        ret, json_response, error_msg = self.__request('GET', uri)
        if ret == RedfishClient.ERR_CODE_OK and 'Version' not in json_response:
            ret, error_msg = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, 'Version not found in Redfish response'
        if ret != RedfishClient.ERR_CODE_OK:
            # Callers probe candidate firmware IDs, so a missing member is not an error
            log_fn = logger.log_notice if ret == RedfishClient.ERR_CODE_URI_NOT_FOUND else logger.log_error
            log_fn(f'Got error {ret} on querying {fw_id} version: {error_msg}')
            return (ret, 'N/A')
        return (ret, json_response['Version'])

    '''
    Update firmware

    Args:
        fw_image: A string, the firmware image file path
        fw_ids: A list of strings, the firmware IDs to be updated. If None, BMC will infer the IDs from the image.
        force_update: A boolean, whether to force update even if the version is lower or identical
        timeout: An integer, overall timeout in seconds; the image upload alone may wait this long for the BMC's reply
        progress_callback: A callback function to report progress

    Returns:
        A tuple of (ret, error_msg, updated_components)
    '''
    def redfish_api_update_firmware(self, fw_image, fw_ids = None, \
            force_update=True, timeout=1800, progress_callback=None):

        update_parameters = {'ForceUpdate': force_update}
        if fw_ids:
            update_parameters['Targets'] = [f'{RedfishClient.REDFISH_URI_FW_INVENTORY}/{fw_id}' for fw_id in fw_ids]
        try:
            image = open(fw_image, 'rb')
        except OSError as e:
            return (RedfishClient.ERR_CODE_GENERIC_ERROR, f'Error: {e}', [])

        def body():
            image.seek(0)
            return {
                'UpdateParameters': (None, json.dumps(update_parameters), 'application/json'),
                'UpdateFile': (os.path.basename(fw_image), image, 'application/octet-stream')
            }

        # Trigger FW upgrade
        with image:
            # The BMC may check the image before it replies, so wait as long as the whole update may take
            ret, json_response, error_msg = self.__request('POST', RedfishClient.REDFISH_URI_UPDATE_SERVICE_UPDATE_MULTIPART,
                                                           body=body, headers={'Content-Type': 'multipart/form-data'},
                                                           timeout=timeout)
        if (ret != RedfishClient.ERR_CODE_OK):
            return (ret, f'Error: {error_msg}', [])

        ret, task_id, error_msg = self.__get_task_id(json_response)
        if (ret != RedfishClient.ERR_CODE_OK):
            return (ret, error_msg, [])

        # Wait for completion
        result = self.__wait_task_completion(task_id, timeout, progress_callback)
        lower_version = result.get('lower_version', False)
        identical_version = result.get('identical_version', False)
        err_detected = result.get('err_detected', False)
        updated_components = result.get('updated_components', [])
        if lower_version:
           result['ret_code'] = RedfishClient.ERR_CODE_LOWER_VERSION
        elif identical_version and not err_detected:
           result['ret_code'] = RedfishClient.ERR_CODE_IDENTICAL_VERSION
           # identical version comes with an 'aborted' message. Clear it.
           result['ret_msg'] = ''

        ret = result['ret_code']
        error_msg = result['ret_msg']

        return (ret, error_msg, updated_components)

    '''
    Trigger BMC debug log dump file

    Returns:
        A tuple of (ret, (task_id, error_msg))
    '''
    def redfish_api_trigger_bmc_debug_log_dump(self):
        task_id = '-1'
        uri = f'{RedfishClient.REDFISH_BMC_LOG_DUMP}/LogService.CollectDiagnosticData'
        ret, json_response, error_msg = self.__request('POST', uri, body={'DiagnosticDataType': 'Manager'})
        if (ret != RedfishClient.ERR_CODE_OK):
            return (ret, (task_id, f'Error: {error_msg}'))

        ret, new_task_id, error_msg = self.__get_task_id(json_response)
        if (ret != RedfishClient.ERR_CODE_OK):
            return (ret, (task_id, error_msg))
        return (RedfishClient.ERR_CODE_OK, (new_task_id, None))

    '''
    Get BMC debug log dump file

    Args:
        task_id: A string, the task ID returned from redfish_api_trigger_bmc_debug_log_dump
        filename: A string, the output file name
        file_path: A string, the output file path
        timeout: An integer, overall timeout in seconds

    Returns:
        A tuple of (ret, error_msg)
    '''
    def redfish_api_get_bmc_debug_log_dump(self, task_id, filename, file_path, timeout = 120):
        result = self.__wait_task_completion(task_id, timeout)
        ret = result['ret_code']
        error_msg = result['ret_msg']

        if ret != RedfishClient.ERR_CODE_OK:
            return (ret, error_msg)

        ret, error_msg, uri = self.__get_uri_from_response(result['response'])
        if ret != RedfishClient.ERR_CODE_OK:
            return (ret, error_msg)

        ret, response, error_msg = self.__request('GET', f'{uri}/attachment', raw=True)
        if ret != RedfishClient.ERR_CODE_OK:
            return (ret, error_msg)

        with open(f'{file_path}/{filename}', 'wb') as f:
            f.write(response.read)
        return (RedfishClient.ERR_CODE_OK, '')

    '''
    Reads all the eeproms of the bmc

    Returns:
        A tuple of (ret, eeprom_list)
    '''
    def redfish_api_get_eeprom_list(self):
        ret, json_response, error = self.__request('GET', RedfishClient.REDFISH_URI_CHASSIS_INVENTORY)
        if (ret != RedfishClient.ERR_CODE_OK):
            logger.log_error(f'Fail to get eeprom list: {error}')
            return (ret, [])
        if 'Members' not in json_response:
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, [])

        eeprom_list = []
        for item in json_response['Members']:
            component_url = item.get("@odata.id")
            if not component_url:
                continue
            component_name = component_url.split('/')[-1]
            if 'eeprom' not in component_name:
                continue
            ret, eeprom_values = self.redfish_api_get_eeprom_info(component_name)
            eeprom_list.append((component_name, eeprom_values))

        return (RedfishClient.ERR_CODE_OK, eeprom_list)

    '''
    Get eeprom values for a given component

    Args:
        component_name: A string, the component name

    Returns:
        A tuple of (ret, eeprom_info)
    '''
    def redfish_api_get_eeprom_info(self, component_name):
        uri = f'{RedfishClient.REDFISH_URI_CHASSIS_INVENTORY}/{component_name}'
        ret, json_response, err_msg = self.__request('GET', uri)
        if (ret != RedfishClient.ERR_CODE_OK):
            logger.log_error(f'Fail to get eeprom info for {component_name}: {err_msg}')
            return (ret, {'State': 'Fail'})

        eeprom_info = {}
        for key,value in json_response.items():
            # Remove information that is not the eeprom content itself but part of the redfish protocol
            if '@odata' in str(value) or '@odata' in str(key):
                continue
            # Don't add the status, we will parse it and add it later
            if key == 'Status':
                continue
            eeprom_info[str(key)] = str(value)

        status = json_response.get('Status',{})
        eeprom_info['State'] = status.get('State', 'Ok')
        eeprom_info['Health'] = status.get('Health', 'Ok')
        eeprom_info['HealthRollup'] = status.get('HealthRollup', 'Ok')

        return (RedfishClient.ERR_CODE_OK, eeprom_info)

    '''
    Change login password

    Args:
        new_password: A string, the new password
        user: A string, the user name. If None, change password of itself

    Returns:
        A tuple of (ret, error_msg)
    '''
    def redfish_api_change_login_password(self, new_password, user=None):
        logger.log_notice('Changing BMC password\n')
        if user is None:
            user = self.__user_callback()
        uri = f'{RedfishClient.REDFISH_URI_ACCOUNTS}/{user}'
        ret, json_response, error_msg = self.__request('PATCH', uri, body={'Password': new_password})
        if ret == RedfishClient.ERR_CODE_OK:
            for info in json_response.get('Password@Message.ExtendedInfo', []):
                if info.get('MessageId', '').endswith('Error'):
                    ret, error_msg = RedfishClient.ERR_CODE_GENERIC_ERROR, info.get('Message', '')
                    logger.log_error(f'Resolution: {info.get("Resolution")}')
                    break

        if ret != RedfishClient.ERR_CODE_OK:
            logger.log_error(f'Fail to change login password: {error_msg}')
            return (ret, error_msg)
        logger.log_notice('Password changed successfully')
        return (RedfishClient.ERR_CODE_OK, '')

    '''
    Set minimum password length for BMC accounts

    Args:
        min_length: minimum password length value (integer)

    Returns:
        A tuple of (ret, error_msg)
    '''
    def redfish_api_set_min_password_length(self, min_length):
        logger.log_notice(f'Setting BMC minimum password length to {min_length}')
        ret, _, error_msg = self.__request('PATCH', RedfishClient.REDFISH_URI_ACCOUNT_SERVICE,
                                           body={'MinPasswordLength': min_length})
        if ret != RedfishClient.ERR_CODE_OK:
            logger.log_error(f'Fail to set minimum password length: {error_msg}')
            return (ret, error_msg)
        logger.log_notice(f'Minimum password length set to {min_length} successfully')
        return (RedfishClient.ERR_CODE_OK, '')

    '''
    Get minimum password length for BMC accounts

    Returns:
        A tuple of (ret_code, min_length or error_msg)
        ret_code    return code
        min_length  minimum password length value (integer) on success,
                    or error message string on failure
    '''
    def redfish_api_get_min_password_length(self):
        ret, json_response, error_msg = self.__request('GET', RedfishClient.REDFISH_URI_ACCOUNT_SERVICE)
        if (ret != RedfishClient.ERR_CODE_OK):
            logger.log_error(f'Fail to get minimum password length: {error_msg}')
            return (ret, error_msg)
        min_length = json_response.get('MinPasswordLength')
        if min_length is None:
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE,
                    'Error: MinPasswordLength not found in response')
        return (RedfishClient.ERR_CODE_OK, min_length)

    '''
    Request BMC to reset itself

    Args:
        bmc_reset_type: A string, the reset type. Valid values are: GracefulRestart and ForceRestart

    Returns:
        A tuple of (ret, error_msg)
    '''
    def redfish_api_request_bmc_reset(self, bmc_reset_type=REDFISH_BMC_GRACEFUL_RESTART):
        ret, _, error_msg = self.__request('POST', RedfishClient.REDFISH_REQUEST_BMC_RESET,
                                           body={'ResetType': bmc_reset_type})
        if ret != RedfishClient.ERR_CODE_OK:
            logger.log_notice(f'Reset BMC returned error {ret}: {error_msg}')
        return (ret, error_msg)
