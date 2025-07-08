"""
    redfish_client.py

    RedfishClient class provides functionality for BMC access via CURL requests of Redfish APIs.

"""


import subprocess
import json
import time
import re
import shlex
from datetime import datetime
from sonic_py_common.logger import Logger


logger = Logger('redfish_client')


class RedfishClient:
    
    '''
    cURL wrapper for Redfish commands
    '''

    DEFAULT_TIMEOUT = 3
    DEFAULT_LOGIN_TIMEOUT = 4

    REDFISH_URI_FW_INVENTORY = '/redfish/v1/UpdateService/FirmwareInventory'
    REDFISH_URI_CHASSIS_INVENTORY = '/redfish/v1/Chassis'
    REDFISH_URI_TASKS = '/redfish/v1/TaskService/Tasks'
    REDFISH_URI_UPDATE_SERVICE_UPDATE_MULTIPART = '/redfish/v1/UpdateService/update-multipart'
    REDFISH_URI_UPDATE_SERVICE = '/redfish/v1/UpdateService'
    REDFISH_URI_ACCOUNTS = '/redfish/v1/AccountService/Accounts'
    REDFISH_URI_SESSION_SERVICE = '/redfish/v1/SessionService/Sessions'
    REDFISH_BMC_LOG_DUMP = '/redfish/v1/Managers/BMC_0/LogServices/Dump/Actions'
    REDFISH_REQUEST_SYSTEM_RESET = '/redfish/v1/Systems/System_0/Actions/ComputerSystem.Reset'
    REDFISH_REQUEST_BMC_RESET = '/redfish/v1/Managers/BMC_0/Actions/Manager.Reset'

    ERR_CODE_OK = 0
    ERR_CODE_AUTH_FAILURE = -1
    ERR_CODE_INVALID_JSON_FORMAT = -2
    ERR_CODE_UNEXPECTED_RESPONSE = -3
    ERR_CODE_CURL_FAILURE = -4
    ERR_CODE_NOT_LOGIN = -5
    ERR_CODE_TIMEOUT = -6
    ERR_CODE_LOWER_VERSION = -7
    ERR_CODE_PASSWORD_UNAVAILABLE = -8
    ERR_CODE_URI_NOT_FOUND = -9
    ERR_CODE_SERVER_UNREACHABLE = -10
    ERR_CODE_UNSUPPORTED_PARAMETER = -11
    ERR_CODE_GENERIC_ERROR = -12
    ERR_CODE_IDENTICAL_VERSION = -13

    CURL_ERR_OK = 0
    CURL_ERR_OPERATION_TIMEDOUT = 28
    CURL_ERR_COULDNT_RESOLVE_HOST = 6
    CURL_ERR_FAILED_CONNECT_TO_HOST = 7
    CURL_ERR_SSL_CONNECT_ERROR = 35

    CURL_TO_REDFISH_ERROR_MAP = \
    {
        CURL_ERR_COULDNT_RESOLVE_HOST :   ERR_CODE_SERVER_UNREACHABLE,
        CURL_ERR_FAILED_CONNECT_TO_HOST : ERR_CODE_SERVER_UNREACHABLE,
        CURL_ERR_SSL_CONNECT_ERROR :      ERR_CODE_SERVER_UNREACHABLE,
        CURL_ERR_OPERATION_TIMEDOUT :     ERR_CODE_TIMEOUT,
        CURL_ERR_OK :                     ERR_CODE_OK
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
        curl_path: A string, path to cURL binary
        ip_addr: A string, IP address of the BMC
        user_callback: A callback function which returns the user name string
        password_callback: A callback function which returns the password string
    '''
    def __init__(self, curl_path, ip_addr, user_callback, password_callback):
        self.__curl_path = curl_path
        self.__svr_ip = ip_addr
        self.__user_callback = user_callback
        self.__password_callback = password_callback
        self.__token = None
        self.__session_id = None
        self.__task_status_event_handlers = {}
        self.__register_task_status_event_handlers()
        logger.log_notice(f'RedfishClient instance (to {self.__svr_ip}) is created\n')

    '''
    Build the POST command to login and get bearer token
    Uses -D - to dump headers to stdout for parsing

    Args:
        password: A string, password for the user
    
    Returns:
        A string, the cURL command to be executed
    '''
    def __build_login_cmd(self, password):
        user = self.__user_callback()
        cmd = f'{self.__curl_path} -m {RedfishClient.DEFAULT_LOGIN_TIMEOUT} -k -D - ' \
              f'-H "Content-Type: application/json" ' \
              f'-X POST https://{self.__svr_ip}{RedfishClient.REDFISH_URI_SESSION_SERVICE} ' \
              f'-d \'{{"UserName" : "{user}", "Password" : "{password}"}}\''
        return cmd

    '''
    Build the DELETE command to logout and release the session

    Returns:
        A string, the cURL command to be executed
    '''
    def __build_logout_cmd(self):
        cmd = f'{self.__curl_path} -k -H "X-Auth-Token: {self.__token}" ' \
              f'-X DELETE https://{self.__svr_ip}{RedfishClient.REDFISH_URI_SESSION_SERVICE}/{self.__session_id}'
        return cmd

    '''
    Build the POST command to do firmware update-multipart

    Args:
        fw_image: A string, path to the firmware image file
        fw_ids: A list of strings, firmware IDs to be updated. If None or empty, the BMC will infer the targets from the image.
        force_update: A boolean, whether to force update even if the same or lower version is detected.

    Returns:
        A string, the cURL command to be executed
    '''
    def __build_fw_update_multipart_cmd(self, fw_image, fw_ids = None, force_update=False):
        if fw_ids:
            targets = [f'"{RedfishClient.REDFISH_URI_FW_INVENTORY}/{fw_id}"' for fw_id in fw_ids]
            targets_str = ', '.join(targets)
            targets_str =  f', "Targets":[{targets_str}]'
        else:
            targets_str = ''
        force_update_str = 'true' if force_update else 'false'
        cmd = f'{self.__curl_path} -k -H "X-Auth-Token: {self.__token}" ' \
              f'https://{self.__svr_ip}' \
              f'{RedfishClient.REDFISH_URI_UPDATE_SERVICE_UPDATE_MULTIPART} ' \
              f"--form 'UpdateParameters={{\"ForceUpdate\":{force_update_str}" \
              f"{targets_str}}};type=application/json' " \
              f'--form "UpdateFile=@{fw_image};type=application/octet-stream"'
        return cmd

    '''
    Build the POST command to request BMC reset

    Args:
        bmc_reset_type: A string, type of BMC reset. Valid values are GracefulRestart and ForceRestart.

    Returns:
        A string, the cURL command to be executed
    '''
    def __build_request_bmc_reset_cmd(self, bmc_reset_type=REDFISH_BMC_GRACEFUL_RESTART):
        cmd = f'{self.__curl_path} -k -H "X-Auth-Token: {self.__token}" ' \
              f'-H "Content-Type: application/json" ' \
              f'-X POST https://{self.__svr_ip}' \
              f'{RedfishClient.REDFISH_REQUEST_BMC_RESET} ' \
              f'-d \'{{"ResetType": "{bmc_reset_type}"}}\''
        return cmd

    '''
    Build the PATCH command to change login password

    Args:
        new_password: A string, the new password to be applied
        user: A string, the user name whose password is to be changed. If None, use the user from user_callback.
    
    Returns:
        A string, the cURL command to be executed
    '''
    def __build_change_password_cmd(self, new_password, user):
        if user is None:
            user = self.__user_callback()
        cmd = f'{self.__curl_path} -k -H "X-Auth-Token: {self.__token}" ' \
              f'-H "Content-Type: application/json" -X PATCH ' \
              f'https://{self.__svr_ip}' \
              f'{RedfishClient.REDFISH_URI_ACCOUNTS}/{user} ' \
              f'-d \'{{"Password" : "{new_password}"}}\''
        return cmd

    '''
    Build the POST command to start BMC debug dump request Redfish Task

    Returns:
        A string, the cURL command to be executed
    '''
    def __build_bmc_debug_log_dump_cmd(self):
        cmd = f'{self.__curl_path} -k -H "X-Auth-Token: {self.__token}" ' \
              f'-H "Content-Type: application/json" ' \
              f'-X POST https://{self.__svr_ip}' \
              f'{RedfishClient.REDFISH_BMC_LOG_DUMP}/LogService.CollectDiagnosticData ' \
              '-d \'{"DiagnosticDataType":"Manager"}\''
        return cmd
    
    '''
    Build the GET command

    Args:
        uri: A string, the Redfish URI to be accessed
        output_file: A string, path to the output file
    
    Returns:
        A string, the cURL command to be executed
    '''
    def __build_get_cmd(self, uri, output_file = None):
        output_str = '' if not output_file else f'--output {output_file}'
        cmd = f'{self.__curl_path} -m {RedfishClient.DEFAULT_TIMEOUT} -k ' \
              f'-H "X-Auth-Token: {self.__token}" --request GET ' \
              f'--location https://{self.__svr_ip}{uri} ' \
              f'{output_str}'
        return cmd
    
    '''
    Obfuscate sensitive authentication data in login response

    Args:
        response: A string, the cURL output to be obfuscated
    
    Returns:
        A string, the obfuscated cURL output
    '''
    def __obfuscate_login_response(self, response):
        # Obfuscate X-Auth-Token in headers
        pattern = r'X-Auth-Token: [^\r\n]+'
        replacement = 'X-Auth-Token: ******'
        obfuscated = re.sub(pattern, replacement, response)
        
        # Obfuscate session ID in Location header
        pattern = r'(Location: [^\r\n]*SessionService/Sessions/)[^\r\n\s]+'
        replacement = r'\1******'
        obfuscated = re.sub(pattern, replacement, obfuscated)
        
        # Obfuscate session ID in @odata.id field
        pattern = r'("@odata\.id": "[^"]*SessionService/Sessions/)[^"]*(")'
        replacement = r'\1******\2'
        obfuscated = re.sub(pattern, replacement, obfuscated)
        
        # Obfuscate session ID in Id field
        pattern = r'("Id": ")[^"]*(")'
        replacement = r'\1******\2'
        obfuscated = re.sub(pattern, replacement, obfuscated)
        
        # Obfuscate UserName field
        pattern = r'("UserName": ")[^"]*(")'
        replacement = r'\1******\2'
        obfuscated = re.sub(pattern, replacement, obfuscated)
        
        # Also obfuscate any token in response body
        pattern = r'"token": "[^"]*"'
        replacement = '"token": "******"'
        obfuscated = re.sub(pattern, replacement, obfuscated)
        
        return obfuscated

    '''
    Obfuscate username and session IDs in logout response

    Args:
        response: A string, the cURL output to be obfuscated
    
    Returns:
        A string, the obfuscated cURL output
    '''
    def __obfuscate_logout_response(self, response):
        # Obfuscate username in the response
        pattern = r"User '[^']+'"
        replacement = "User '******'"
        obfuscation_response = re.sub(pattern, replacement, response)
        
        # Obfuscate username in the response
        pattern = r'("data": "User \')[^\']+(\' logged out")'
        replacement = r'\1******\2'
        obfuscation_response = re.sub(pattern, replacement, obfuscation_response)
        
        # Obfuscate session ID in the response
        pattern = r'(SessionService/Sessions/)[^\s"}\r\n]+'
        replacement = r'\1******'
        obfuscation_response = re.sub(pattern, replacement, obfuscation_response)
        
        return obfuscation_response

    '''
    Obfuscate username and password while asking for bearer token

    Args:
        cmd: A string, the cURL command to be obfuscated
    
    Returns:
        A string, the obfuscated cURL command
    '''
    def __obfuscate_user_password(self, cmd):
        # Obfuscate 'UserName' and 'Password' in the payload
        pattern = r'"UserName" : "[^"]*", "Password" : "[^"]*"'
        replacement = '"UserName" : "******", "Password" : "******"'
        obfuscation_cmd = re.sub(pattern, replacement, cmd)

        # Obfuscate username and password in the command line parameter
        pattern =  r'-u [!-~]+:[!-~]+'
        replacement = '-u ******:******'
        obfuscation_cmd = re.sub(pattern, replacement, obfuscation_cmd)
        return obfuscation_cmd

    '''
    Obfuscate bearer token passed to cURL

    Args:
        cmd: A string, the cURL command to be obfuscated
    
    Returns:
        A string, the obfuscated cURL command
    '''
    def __obfuscate_auth_token(self, cmd):
        pattern = r'X-Auth-Token: [^"]+'
        replacement = 'X-Auth-Token: ******'
        obfuscation_cmd = re.sub(pattern, replacement, cmd)
        return obfuscation_cmd

    '''
    Obfuscate password while asking for password change

    Args:
        cmd: A string, the cURL command to be obfuscated
    
    Returns:
        A string, the obfuscated cURL command
    '''
    def __obfuscate_password(self, cmd):
        pattern = r'"Password" : "[^"]*"'
        replacement = '"Password" : "******"'
        obfuscation_cmd = re.sub(pattern, replacement, cmd)
        return obfuscation_cmd

    '''
    Obfuscate username while asking for password change

    Args:
        cmd: A string, the cURL command to be obfuscated
    
    Returns:
        A string, the obfuscated cURL command
    '''
    def __obfuscate_username_in_url(self, cmd):
        pattern = r'/AccountService/Accounts/[^/\s]+'
        replacement = '/AccountService/Accounts/******'
        obfuscation_cmd = re.sub(pattern, replacement, cmd)
        return obfuscation_cmd

    '''
    Obfuscate session ID in URLs

    Args:
        cmd: A string, the cURL command to be obfuscated
    
    Returns:
        A string, the obfuscated cURL command
    '''
    def __obfuscate_session_id_in_url(self, cmd):
        pattern = r'/SessionService/Sessions/[^/\s]+'
        replacement = '/SessionService/Sessions/******'
        obfuscation_cmd = re.sub(pattern, replacement, cmd)
        return obfuscation_cmd

    '''
    Parse cURL output to extract response and HTTP status code

    Args:
        curl_output: A string, the cURL output to be parsed
    
    Returns:
        A tuple of response string and HTTP status code string
    '''
    def __parse_curl_output(self, curl_output):
        response_str = None
        http_status_code = None
        pattern = r'([\s\S]*?)(?:\n)?HTTP Status Code: (\d+)$'
        match = re.search(pattern, curl_output, re.MULTILINE)
        if match:
            response_str = match.group(1)
            http_status_code = match.group(2)
        return (response_str, http_status_code)
    
    '''
    Parse cURL output with headers from -D - flag
    Used only for login to extract headers and body from stdout

    Args:
        curl_output: A string, the cURL output to be parsed
    
    Returns: A tuple of headers dictionary and body string
    '''
    def __get_headers_and_body_from_curl_output(self, curl_output):
        # Parse curl -D - output - headers and body separated by double newline
        headers = {}
        body = curl_output
        # Split headers and body on double newline (handles both \r\n\r\n and \n\n)
        parts = re.split(r'\r?\n\r?\n', curl_output, 1)
        if len(parts) == 2:
            headers_section, body = parts
            for line in headers_section.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
        return headers, body
    
    '''
    Translate cURL error code to RedfishClient error code

    Args:
        curl_error: An integer, cURL error code
    
    Returns:
        An integer, RedfishClient error code
    '''
    def __curl_errors_to_redfish_errors_translation(self, curl_error):
        return self.CURL_TO_REDFISH_ERROR_MAP.get(
                    curl_error, RedfishClient.ERR_CODE_CURL_FAILURE)

    '''
    Update token in the command.

    Args:
        cmd: A string, the cURL command to be updated
    
    Returns:
        A string, the updated cURL command
    '''
    def __update_token_in_command(self, cmd):
        pattern = r'X-Auth-Token:\s*[^\s\"\']+'
        new_cmd = re.sub(pattern, 'X-Auth-Token: ' + self.__token, cmd)
        return new_cmd

    '''
    Execute cURL command and return the output and error messages

    Args:
        cmd: A string, the cURL command to be executed
    
    Returns:
        A tuple of (ret, http_status_code, output_str, error_str)
    '''
    def __exec_curl_cmd_internal(self, cmd):
        task_mon = (RedfishClient.REDFISH_URI_TASKS in cmd)
        login_cmd = (RedfishClient.REDFISH_URI_SESSION_SERVICE in cmd and 'POST' in cmd)
        logout_cmd = (RedfishClient.REDFISH_URI_SESSION_SERVICE in cmd and 'DELETE' in cmd)
        password_change = (RedfishClient.REDFISH_URI_ACCOUNTS in cmd and 'PATCH' in cmd)
        obfuscation_cmd = self.__obfuscate_user_password(cmd)
        obfuscation_cmd = self.__obfuscate_auth_token(obfuscation_cmd)
        if password_change:
            obfuscation_cmd = self.__obfuscate_username_in_url(obfuscation_cmd)
            obfuscation_cmd = self.__obfuscate_password(obfuscation_cmd)
        if logout_cmd:
            obfuscation_cmd = self.__obfuscate_session_id_in_url(obfuscation_cmd)
        cmd_str = obfuscation_cmd
        exec_cmd_msg = f'Execute cURL command: {cmd_str}'

        if not task_mon:
            logger.log_notice(f'{exec_cmd_msg}')

        # Instruct cURL to append HTTP status code after JSON response
        cmd += ' -w "\nHTTP Status Code: %{http_code}"'
        process = subprocess.Popen(shlex.split(cmd),
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        output, error = process.communicate()
        output_str, http_status_code = self.__parse_curl_output(output.decode('utf-8'))
        error_str = error.decode('utf-8')
        ret = process.returncode

        if (ret == RedfishClient.CURL_ERR_OK):
            # cURL will print r/x statistics on stderr, ignore it
            error_str = ''
            ret = RedfishClient.ERR_CODE_OK

            # For login/logout command, obfuscate the response (and headers from -D -)
            if login_cmd:
                obfuscation_output_str = self.__obfuscate_login_response(output_str)
            elif logout_cmd:
                obfuscation_output_str = self.__obfuscate_logout_response(output_str)
            else:
                obfuscation_output_str = output_str

            # No HTTP status code found, return immediately. This is unlikely to happen.
            if http_status_code is None:
                logger.log_error(f'HTTP status code not found')
                logger.log_notice(f'cURL output:')
                self.log_multi_line_str(obfuscation_output_str)
                return (RedfishClient.ERR_CODE_CURL_FAILURE, http_status_code, output_str, 'Unexpected curl output')

            if not task_mon:
                logger.log_notice(f'HTTP status code: {http_status_code}')
                logger.log_notice(f'cURL output:')
                self.log_multi_line_str(obfuscation_output_str)
        else:
            logger.log_notice(f'cURL error:')
            self.log_multi_line_str(error_str)
            ret = self.__curl_errors_to_redfish_errors_translation(ret)

        return (ret, http_status_code, output_str, error_str)

    '''
    Extract URI from the job response

    Args:
        response: A string, the cURL output to be parsed
    
    Returns:
        A tuple of (ret, err_msg, uri)
    '''
    def __get_uri_from_response(self, response):
        try:
            json_response = json.loads(response)
        except Exception as e:
            msg = 'Error: Invalid JSON format'
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, msg, None)

        if "Payload" not in json_response:
            ret = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
            err_msg = "Error: Missing 'Payload' field"
            return (ret, err_msg, None)

        payload = json_response["Payload"]
        if "HttpHeaders" not in payload:
            ret = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
            err_msg = "Error: Missing 'HttpHeaders' field"
            return (ret, err_msg, None)

        http_headers = payload["HttpHeaders"]
        uri = None
        for header in http_headers:
            if "Location" in header:
                uri = header.split()[-1]

        if not uri:
            ret = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
            err_msg = "Error: Missing 'Location' field"
            return (ret, err_msg, None)

        return (RedfishClient.ERR_CODE_OK, "", uri)
    
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
            response: cURL output from the last polling
    '''
    def __wait_task_completion(self, task_id, timeout = 1800, progress_callback = None, sleep_timeout = 2):
        # Construct the command to poll task status by given task id
        uri = f'{RedfishClient.REDFISH_URI_TASKS}/{task_id}'
        cmd = self.__build_get_cmd(uri)
        obfuscation_cmd = self.__obfuscate_auth_token(cmd)
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
                'response': ''
            }
            now = datetime.now()
            timestamp = now.strftime("%H:%M:%S.%f")

            ret, http_status_code, response, err_msg = self.exec_curl_cmd(cmd)
            result['response'] = response

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

            # Parse JSON response
            try:
                json_response = json.loads(response)
            except Exception as e:
                result['ret_code'] = RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
                result['ret_msg'] = 'Error: Invalid JSON format'
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

            # Log cURL command and response only if status or percent changed
            if (prev_status != status or prev_percent != percent):
                logger.log_notice(f'Execute cURL command at {timestamp}: {obfuscation_cmd}')
                logger.log_notice(f'HTTP status code: {http_status_code}')
                logger.log_notice('cURL output:')
                self.log_multi_line_str(response)

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
    Wrapper function to execute the given cURL command which can deal with invalid bearer token case.

    Args:
        cmd: A string, the cURL command to be executed
        max_retries: An integer, maximum retries on timeout
    
    Returns:
        A tuple of (ret, http_status_code, output_str, error_str)
    '''
    def exec_curl_cmd(self, cmd, max_retries=2):
        is_login_cmd = (RedfishClient.REDFISH_URI_SESSION_SERVICE in cmd and 'POST' in cmd)

        # Not login, return
        if (not self.has_login()) and (not is_login_cmd):
            logger.log_error('Need to login first before executing cURL command')
            return (RedfishClient.ERR_CODE_NOT_LOGIN, None, 'Not login', 'Not login')

        ret, http_status_code, output_str, error_str = self.__exec_curl_cmd_internal(cmd)

        # cURL execution timeout, try again
        i = 0
        while (i < max_retries) and (ret == RedfishClient.ERR_CODE_TIMEOUT):
            # Increase timeout temporarily
            timeout = None
            match = re.search(r'-m\s*(\d+)', cmd)
            if match:
                timeout = int(match.group(1))
                timeout += 2
                cmd = re.sub(r'-m\s*\d+', f'-m {timeout}', cmd)
            ret, http_status_code, output_str, error_str \
                = self.__exec_curl_cmd_internal(cmd)
            i += 1

        if not http_status_code == '401':
            return (ret, http_status_code, output_str, error_str)

        # Authentication failure might happen in case of:
        #   - Incorrect password.
        #   - Token may become invalid, for example, remote side may clear the session table or change password.
        if is_login_cmd:
            return (RedfishClient.ERR_CODE_AUTH_FAILURE, http_status_code, 'Authentication failure', 'Authentication failed')

        # Authentication failure for other commands.
        # Re-login, retry the command and expect to recover.
        logger.log_notice('Re-login and retry last command...')
        self.invalidate_session()
        ret = self.login()
        if ret == RedfishClient.ERR_CODE_OK:
            logger.log_notice('Login successfully. Rerun last command\n')
            cmd = self.__update_token_in_command(cmd)
            ret, http_status_code, output_str, error_str = self.__exec_curl_cmd_internal(cmd)
            if ret != RedfishClient.ERR_CODE_OK:
                logger.log_notice(f'Command rerun returns error {ret}\n')
            elif http_status_code == '401':
                logger.log_notice('Command rerun fails as authentication failure\n')
                self.invalidate_session()
            return (RedfishClient.ERR_CODE_AUTH_FAILURE, http_status_code, 'Authentication failure', 'Authentication failure')
        elif ret == RedfishClient.ERR_CODE_AUTH_FAILURE:
            logger.log_notice('Failed to login. Return as authentication failure\n')
            self.invalidate_session()
            return (ret, http_status_code, 'Authentication failure', 'Authentication failure')
        else:
            logger.log_notice(f'Failed to login, error : {ret}\n')
            self.invalidate_session()
            return (ret, http_status_code, 'Login failure', 'Login failure')

    '''
    Get current login token

    Returns:
        A string, the current bearer token
    '''
    def get_login_token(self):
        return self.__token
    
    '''
    Get current session ID

    Returns:
        A string, the current session ID
    '''
    def get_session_id(self):
        return self.__session_id

    '''
    Invalidate current token and session ID
    '''
    def invalidate_session(self):
        logger.log_notice(f'Invalidate login token and session')
        self.__token = None
        self.__session_id = None

    '''
    Check if already logged in

    Returns:
        A boolean, True if already logged in; False otherwise
    '''
    def has_login(self):
        return self.__token is not None and self.__session_id is not None

    '''
    Login Redfish server and get bearer token

    Returns:
        An integer, return code
    '''
    def login(self):
        if self.has_login():
            return RedfishClient.ERR_CODE_OK

        try:
            password = self.__password_callback()
        except Exception as e:
            logger.log_error(f'{str(e)}')
            return RedfishClient.ERR_CODE_PASSWORD_UNAVAILABLE

        cmd = self.__build_login_cmd(password)
        ret, _, response, error = self.exec_curl_cmd(cmd)

        if (ret != 0):
            logger.log_error(f'Login failure: code {ret}, {error}')
            return ret

        if response is None or len(response) == 0:
            logger.log_error('Got empty Redfish login response')
            return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE

        try:
            # Parse headers and body from -D - output
            headers, body = self.__get_headers_and_body_from_curl_output(response)
            if body:
                try:
                    json_response = json.loads(body)
                    if 'error' in json_response:
                        error_msg = json_response['error']['message']
                        logger.log_error(f'Login failure: {error_msg}')
                        self.log_multi_line_str(response)
                        return RedfishClient.ERR_CODE_GENERIC_ERROR
                except Exception as e:
                    logger.log_error(f'Login failure: Exception during parsing body: {str(e)}')
                    self.log_multi_line_str(response)

            # Extract both token and session ID from headers
            token = headers.get('X-Auth-Token')
            if not token:
                logger.log_error('Login failure: no "X-Auth-Token" header found')
                self.log_multi_line_str(response)
                return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
            
            location = headers.get('Location')
            if not location:
                logger.log_error('Login failure: no "Location" header found')
                self.log_multi_line_str(response)
                return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
            
            session_id = location.split('/')[-1]
            if not session_id:
                logger.log_error('Login failure: could not extract session ID from Location header')
                self.log_multi_line_str(response)
                return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
                
            self.__token = token
            self.__session_id = session_id
            logger.log_notice('Redfish login successfully with session token and session ID updated')
            return RedfishClient.ERR_CODE_OK
            
        except Exception as e:
            logger.log_error(f'Login failure: exception {str(e)}')
            self.log_multi_line_str(response)
            return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE

    '''
    Logout Redfish server

    Returns:
        An integer, return code
    '''
    def logout(self):
        if not self.has_login():
            return RedfishClient.ERR_CODE_OK

        logger.log_notice('Logout redfish session')
        cmd = self.__build_logout_cmd()
        ret, _, response, _ = self.exec_curl_cmd(cmd)
        # Invalidate token and session ID anyway
        self.invalidate_session()

        if (ret != 0):
            msg = 'Logout failure: curl command returns error\n'
            logger.log_notice(f'{msg}')
            return ret

        # Logout returns JSON with success message
        if response and len(response) > 0:
            try:
                json_response = json.loads(response)
                if 'error' in json_response:
                    error_msg = json_response['error']['message']
                    logger.log_error(f'Logout failed: {error_msg}')
                    self.log_multi_line_str(response)
                    return RedfishClient.ERR_CODE_GENERIC_ERROR
                
                if '@Message.ExtendedInfo' in json_response:
                    for info in json_response['@Message.ExtendedInfo']:
                        message_id = info.get('MessageId', '')
                        if 'Success' in message_id:
                            logger.log_notice('Redfish logout successful')
                            return RedfishClient.ERR_CODE_OK
                    logger.log_error('Logout failed: No success message in response')
                    self.log_multi_line_str(response)
                    return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
                else:
                    logger.log_error('Logout failed: No Message.ExtendedInfo in response')
                    self.log_multi_line_str(response)
                    return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
            except Exception as e:
                logger.log_error(f'Logout failed: exception {str(e)}')
                self.log_multi_line_str(response)
                return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
        else:
            logger.log_error('Logout failed: Empty response')
            return RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
    
    '''
    Get firmware inventory

    Returns:
        A tuple of (ret, fw_list)
    '''
    def redfish_api_get_firmware_list(self):
        cmd = self.__build_get_cmd(RedfishClient.REDFISH_URI_FW_INVENTORY)
        ret, _, response, error = self.exec_curl_cmd(cmd)
        if (ret != RedfishClient.ERR_CODE_OK):
            logger.log_error(f'Fail to get firmware list: {error}')
            return (ret, [])
        try:
            json_response = json.loads(response)
            item_list = json_response["Members"]
        except json.JSONDecodeError as e:
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, [])
        except Exception as e:
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, [])
        fw_list = []
        for item in item_list:
            fw_id = item["@odata.id"].split('/')[-1]
            ret, version = self.redfish_api_get_firmware_version(fw_id)
            if (ret != RedfishClient.ERR_CODE_OK):
                version = "N/A"
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
        version = 'N/A'
        uri = f'{RedfishClient.REDFISH_URI_FW_INVENTORY}/{fw_id}'
        cmd = self.__build_get_cmd(uri)
        ret, _, response, error_msg = self.exec_curl_cmd(cmd)
        if (ret == RedfishClient.ERR_CODE_OK):
            try:
                json_response = json.loads(response)
                if 'Version' in json_response:
                    version = json_response['Version']
                else:
                    msg = 'Error: Version not found in Redfish response'
                    logger.log_error(f'{msg}')
            except json.JSONDecodeError as e:
                msg = f'Error: Invalid Redfish response JSON format on querying {fw_id} version'
                logger.log_notice(f'{msg}')
                ret = RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
            except Exception as e:
                msg = f'Error: Exception {str(e)} caught on querying {fw_id} version'
                logger.log_notice(f'{msg}')
                ret = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
        else:
            msg = f'Got error {ret} on querying {fw_id} version: {error_msg}'
            logger.log_error(f'{msg}')
        return (ret, version)

    '''
    Update firmware

    Args:
        fw_image: A string, the firmware image file path
        fw_ids: A list of strings, the firmware IDs to be updated. If None, BMC will infer the IDs from the image.
        force_update: A boolean, whether to force update even if the version is lower or identical
        timeout: An integer, overall timeout in seconds
        progress_callback: A callback function to report progress

    Returns:
        A tuple of (ret, error_msg)
    '''
    def redfish_api_update_firmware(self, fw_image, fw_ids = None, \
            force_update=True, timeout=1800, progress_callback=None):

        # Trigger FW upgrade
        cmd = self.__build_fw_update_multipart_cmd(fw_image,
                                                   fw_ids=fw_ids,
                                                   force_update=force_update)
        ret, _, response, error_msg = self.exec_curl_cmd(cmd)
        if (ret != RedfishClient.ERR_CODE_OK):
            return (ret, f'Error: {error_msg}')

        try:
            json_response = json.loads(response)
        except Exception as e:
            msg = 'Error: Invalid JSON format'
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, msg)

        # Retrieve task id from response
        task_id = ''
        if 'error' in json_response: # Error found
            err = json_response['error']
            if 'message' in err:
                err_msg = err['message']
                ret = RedfishClient.ERR_CODE_GENERIC_ERROR
            else:
                ret = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
                err_msg = "Missing 'message' field"
            return (ret, f'Error: {err_msg}')
        elif 'TaskStatus' in json_response:
            status = json_response['TaskStatus']
            if status == 'OK':
                task_id = json_response['Id']
            else:
                ret = RedfishClient.ERR_CODE_GENERIC_ERROR
                return (ret, f'Error: Return status is {status}')

        # Wait for completion
        result = self.__wait_task_completion(task_id, timeout, progress_callback)
        lower_version = result.get('lower_version', False)
        identical_version = result.get('identical_version', False)
        err_detected = result.get('err_detected', False)

        if lower_version:
           result['ret_code'] = RedfishClient.ERR_CODE_LOWER_VERSION
        elif identical_version and not err_detected:
           result['ret_code'] = RedfishClient.ERR_CODE_IDENTICAL_VERSION
           # identical version comes with an 'aborted' message. Clear it.
           result['ret_msg'] = ''

        ret = result['ret_code']
        error_msg = result['ret_msg']

        return (ret, error_msg)

    '''
    Trigger BMC debug log dump file

    Returns:
        A tuple of (ret, (task_id, error_msg))
    '''
    def redfish_api_trigger_bmc_debug_log_dump(self):
        task_id = '-1'
        cmd = self.__build_bmc_debug_log_dump_cmd()
        ret, _, response, error_msg = self.exec_curl_cmd(cmd)
        if (ret != RedfishClient.ERR_CODE_OK):
            return (ret, (task_id, f'Error: {error_msg}'))

        try:
            json_response = json.loads(response)
        except Exception as e:
            msg = 'Error: Invalid JSON format'
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, (task_id, msg))

        # Retrieve task id from response
        if 'error' in json_response:
            err = json_response['error']
            if 'message' in err:
                err_msg = err['message']
                ret = RedfishClient.ERR_CODE_GENERIC_ERROR
            else:
                ret = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
                err_msg = "Missing 'message' field"
            return (ret, (task_id, f'Error: {err_msg}'))
        elif 'TaskStatus' in json_response:
            status = json_response['TaskStatus']
            if status == 'OK':
                task_id = json_response.get('Id', '')
                ret = RedfishClient.ERR_CODE_OK
                return (ret, (task_id, None))
            else:
                ret = RedfishClient.ERR_CODE_GENERIC_ERROR
                return (ret, (task_id, f'Error: Return status is {status}'))
        else:
            ret = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
            err_msg = "Missing 'error' or 'TaskStatus' field in response"
            return (ret, (task_id, f'Error: {err_msg}'))

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
        response = result['response']

        if ret != RedfishClient.ERR_CODE_OK:
            return (ret, error_msg)

        ret, error_msg, uri = self.__get_uri_from_response(response)
        if ret != RedfishClient.ERR_CODE_OK:
            return (ret, error_msg)

        if not uri:
            ret = RedfishClient.ERR_CODE_GENERIC_ERROR
            return (ret, error_msg)

        output_file = f'{file_path}/{filename}'
        uri += '/attachment'
        cmd = self.__build_get_cmd(uri, output_file=output_file)
        ret, _, response, error_msg = self.exec_curl_cmd(cmd)

        return (ret, error_msg)

    '''
    Reads all the eeproms of the bmc

    Returns:
        A tuple of (ret, eeprom_list)
    '''
    def redfish_api_get_eeprom_list(self):
        cmd = self.__build_get_cmd(RedfishClient.REDFISH_URI_CHASSIS_INVENTORY)
        ret, _, response, error = self.exec_curl_cmd(cmd)

        if (ret != RedfishClient.ERR_CODE_OK):
            logger.log_error(f'Fail to get eeprom list: {error}')
            return (ret, [])

        try:
            json_response = json.loads(response)
            item_list = json_response["Members"]
        except json.JSONDecodeError as e:
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, [])
        except Exception as e:
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, [])

        eeprom_list = []
        for item in item_list:
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
        cmd = self.__build_get_cmd(uri)
        ret, _, response, err_msg = self.exec_curl_cmd(cmd)

        bad_eeprom_info = {'State': 'Fail'}
        if (ret != RedfishClient.ERR_CODE_OK):
            logger.log_error(f'Fail to get eeprom info for {component_name}: {err_msg}')
            return (ret, bad_eeprom_info)

        try:
            json_response = json.loads(response)
        except json.JSONDecodeError as e:
            ret = RedfishClient.ERR_CODE_INVALID_JSON_FORMAT
            return (ret, bad_eeprom_info)
        except Exception as e:
            ret = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
            return (ret, bad_eeprom_info)

        if 'error' in json_response:
            err = json_response['error']
            if ('code' in err) and ('ResourceNotFound' in err['code']):
                ret = RedfishClient.ERR_CODE_URI_NOT_FOUND
            else:
                ret = RedfishClient.ERR_CODE_GENERIC_ERROR
            logger.log_error(f'Got redfish error response for {component_name} query')
            return (ret, bad_eeprom_info)

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
        cmd = self.__build_change_password_cmd(new_password, user)
        ret, _, response, error = self.exec_curl_cmd(cmd)

        if (ret != RedfishClient.ERR_CODE_OK):
            logger.log_error(f'Fail to change login password: {error}')
            return (ret, f'Error: {error}')
        else:
            try:
                json_response = json.loads(response)
                if 'error' in json_response:
                    msg = json_response['error']['message']
                    logger.log_error(f'Fail to change login password: {msg}')
                    ret = RedfishClient.ERR_CODE_GENERIC_ERROR
                    return (ret, msg)

                if 'Password@Message.ExtendedInfo' in json_response:
                    for info in json_response['Password@Message.ExtendedInfo']:
                        if info['MessageId'].endswith('Error'):
                            msg = info['Message']
                            logger.log_error(f'Fail to change login password: {msg}')
                            resolution = info['Resolution']
                            logger.log_error(f'Resolution: {resolution}')
                            ret = RedfishClient.ERR_CODE_GENERIC_ERROR
                            return (ret, msg)

                if '@Message.ExtendedInfo' in json_response:
                    for info in json_response['@Message.ExtendedInfo']:
                        if info['MessageId'].endswith('Success'):
                            logger.log_notice('Password changed successfully')
                            return (RedfishClient.ERR_CODE_OK, '')

                msg = 'Error: Unexpected response format'
                logger.log_error(f'Fail to change login password. {msg}')
                return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, msg)
            except json.JSONDecodeError as e:
                return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, 'Error: Invalid JSON format')
            except Exception as e:
                return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, 'Error: Unexpected response format')

    '''
    Request BMC to reset itself

    Args:
        bmc_reset_type: A string, the reset type. Valid values are: GracefulRestart and ForceRestart

    Returns:
        A tuple of (ret, error_msg)
    '''
    def redfish_api_request_bmc_reset(self, bmc_reset_type=REDFISH_BMC_GRACEFUL_RESTART):
        cmd = self.__build_request_bmc_reset_cmd(bmc_reset_type)
        ret, _, response, err_msg = self.exec_curl_cmd(cmd)
        json_response = None

        if (ret != RedfishClient.ERR_CODE_OK):
            logger.log_notice(f'Reset BMC return not OK, ret {ret}, response {response}, err msg {err_msg}')
            return (ret, err_msg)

        if response is None or len(response) == 0:
            logger.log_notice(f'Reset BMC return OK, ret {ret}, err msg {err_msg}')
            return (RedfishClient.ERR_CODE_OK, '')

        logger.log_notice(f"After requesting BMC {bmc_reset_type}, got response {response} and error {err_msg}")

        try:
            json_response = json.loads(response)
        except json.JSONDecodeError as e:
            msg = 'Error: Invalid JSON format'
            return (RedfishClient.ERR_CODE_INVALID_JSON_FORMAT, msg)
        except Exception as e:
            msg = 'Error: unexpected response'
            return (RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE, msg)

        if 'error' in json_response:
            err = json_response['error']
            if 'message' in err:
                err_msg = err['message']
                ret = RedfishClient.ERR_CODE_GENERIC_ERROR
                if 'ActionParameterUnknown' in err.get('code', ''):
                    ret = RedfishClient.ERR_CODE_UNSUPPORTED_PARAMETER
            else:
                ret = RedfishClient.ERR_CODE_UNEXPECTED_RESPONSE
                err_msg = "Missing 'message' field"

        return (ret, err_msg)
