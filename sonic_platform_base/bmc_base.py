"""
    bmc_base.py

    Base class for implementing BMC APIs using Redfish commands.
    The vendor-specific BMC class should inherit this class and:
    1. Implement the pure virtual functions.
    2. Override other methods if necessary.
    3. Extend the class if necessary.

"""


try:
    import subprocess
    from functools import wraps
    from . import device_base
    from .redfish_client import RedfishClient
    from sonic_py_common.logger import Logger
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")


logger = Logger('bmc_base')


"""
Wrapper to manage a session with login/logout for each API call.
"""
def with_session_management(api_func):
    @wraps(api_func)
    def wrapper(self, *args, **kwargs):
        try:
            if self.rf_client is None:
                raise Exception('RedfishClient instance is None')
            
            self._login()
            ret, data = api_func(self, *args, **kwargs)

            if ret != RedfishClient.ERR_CODE_OK:
                logger.log_notice(f'Failed to execute {api_func.__name__}: {ret}')
            
            self._logout()
            return (ret, data)
        except Exception as e:
            logger.log_error(f'Exception in {api_func.__name__}: {str(e)}')
            self._logout()
            logger.log_notice(f'Logged out from BMC in exception handler of {api_func.__name__}')
            return (RedfishClient.ERR_CODE_GENERIC_ERROR, str(e))
    return wrapper


class BMCBase(device_base.DeviceBase):

    """
    BMCBase encapsulates base BMC device functionality.
    It also acts as base class of RedfishClient wrapper.
    """

    CURL_PATH = '/usr/bin/curl'
    BMC_NAME = 'BMC'
    ROOT_ACCOUNT = 'root'
    
    def __init__(self, addr):
        """
        Initialize BMC base class.
        The vendor-specific BMC class should have get_instance() static method.

        Args:
            addr: A string of the BMC IP address
        """
        self.addr = addr
        self.rf_client = RedfishClient(BMCBase.CURL_PATH,
                                        addr,
                                        self._get_login_user_callback,
                                        self._get_login_password_callback)
    
    def _get_login_user_callback(self):
        """
        Get BMC username/account for login before Redfish commands from NOS.
        Should be implemented by vendor-specific BMC class.
        
        Returns:
            A string containing the BMC login user name
        """
        raise NotImplementedError
    
    def _get_login_password_callback(self):
        """
        Get BMC password of the account for login before Redfish commands from NOS.
        Should be implemented by vendor-specific BMC class.

        Returns:
            A string containing the BMC login password
        """
        raise NotImplementedError
    
    def _get_default_root_password(self):
        """
        Get the default root password for BMC. Will be used in reset_root_password().
        Should be implemented by vendor-specific BMC class.

        Returns:
            A string containing the default root password
        """
        raise NotImplementedError
    
    def _get_firmware_id(self):
        """
        Get the BMC firmware ID.
        Should be implemented by vendor-specific BMC class.

        Returns:
            A string containing the BMC firmware ID
        """
        raise NotImplementedError
    
    def _get_eeprom_id(self):
        """
        Get the BMC EEPROM ID.
        Should be implemented by vendor-specific BMC class.

        Returns:
            A string containing the BMC EEPROM ID
        """
        raise NotImplementedError

    def _get_ip_addr(self):
        """
        Get BMC IP address

        Returns:
            A string containing the BMC IP address
        """
        return self.addr
    
    def _login(self):
        """
        Generic BMC login, should be called before any Redfish command.
        Vendor-specific BMC class may override this method for custom login behavior.

        Returns:
            An integer RedfishClient return code indicating success (0) or failure
        """
        if self.rf_client.has_login():
            return RedfishClient.ERR_CODE_OK
        return self.rf_client.login()
    
    def _logout(self):
        """
        Generic BMC logout, should be called after any Redfish command.

        Returns:
            An integer RedfishClient return code indicating success (0) or failure
        """
        if self.rf_client.has_login():
            return self.rf_client.logout()
        return RedfishClient.ERR_CODE_OK
    
    @with_session_management
    def _change_login_password(self, password, user=None):
        """
        Generic login password change.
        If user is None, change password for the default user returned by _get_login_user_callback().

        Args:
            password: A string containing the new password
            user: A string containing the user name whose password is to be changed

        Returns:
            A tuple (ret, msg) where:
                ret: An integer return code indicating success (0) or failure
                msg: A string containing success message or error description
        """
        return self.rf_client.redfish_api_change_login_password(password, user)
    
    @with_session_management
    def _get_firmware_version(self, fw_id):
        """
        Generic get firmware version

        Args:
            fw_id: A string containing the firmware ID
        
        Returns:
            A tuple (ret, version) where:
                ret: An integer return code indicating success (0) or failure
                version: A string containing the firmware version, or 'N/A' if not available
        """
        return self.rf_client.redfish_api_get_firmware_version(fw_id)

    @with_session_management
    def _get_eeprom_info(self, eeprom_id):
        """
        Generic get EEPROM information

        Args:
            eeprom_id: A string containing the EEPROM ID
        
        Returns:
            A tuple (ret, eeprom_info) where:
                ret: An integer return code indicating success (0) or failure
                eeprom_info: A dictionary containing the EEPROM information
        """
        return self.rf_client.redfish_api_get_eeprom_info(eeprom_id)
    
    def _is_bmc_eeprom_content_valid(self, eeprom_info):
        """
        Check if the BMC EEPROM content is valid
        Args:
            eeprom_info: A dictionary containing the EEPROM information
        
        Returns:
            A boolean indicating whether the EEPROM content is valid
        """
        if None == eeprom_info or 0 == len(eeprom_info):
            return False
        got_error = eeprom_info.get('error')
        if got_error:
            logger.log_error(f'Got error when querying eeprom: {got_error}')
            return False
        return True

    def get_name(self):
        """
        Get the name of the BMC device

        Returns:
            A string containing the name of the BMC device
        """
        return BMCBase.BMC_NAME
    
    def get_presence(self):
        """
        Check if the BMC device is present

        Returns:
            A boolean indicating whether the BMC device is present
        """
        from sonic_py_common import device_info
        bmc_data = device_info.get_bmc_data()
        if bmc_data and bmc_data.get('bmc_addr'):
            return True
        return False
    
    def get_model(self):
        """
        Get the model of the BMC device
        
        Returns:
            A string containing the model of the BMC device
        """
        eeprom_info = self.get_eeprom()
        if not self._is_bmc_eeprom_content_valid(eeprom_info):
            return None
        return eeprom_info.get('Model')
    
    def get_serial(self):
        """
        Get the serial number of the BMC device
        
        Returns:
            A string containing the serial number of the BMC device
        """
        eeprom_info = self.get_eeprom()
        if not self._is_bmc_eeprom_content_valid(eeprom_info):
            return None
        return eeprom_info.get('SerialNumber')

    def get_revision(self):
        """
        Get the revision of the BMC device

        Returns:
            A string containing the revision of the BMC device
        """
        return 'N/A'
    
    def get_status(self):
        """
        Get the status of the BMC device

        Returns:
            A boolean indicating whether the BMC device is operational
        """
        if not self.get_presence():
            return False
        try:
            command = ['/usr/bin/ping', '-c', '1', '-W', '1', self._get_ip_addr()]
            subprocess.check_output(command, stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def is_replaceable(self):
        """
        Check if the BMC device is field replaceable

        Returns:
            A boolean indicating whether the BMC device is replaceable
        """
        return False
    
    def get_eeprom(self):
        """
        Retrieves the BMC EEPROM information

        Returns:
            A dictionary containing the BMC EEPROM information.
            Returns an empty dictionary {} if EEPROM information cannot be retrieved
        """
        try:
            ret, eeprom_info = self._get_eeprom_info(self._get_eeprom_id())
            if not self._is_bmc_eeprom_content_valid(eeprom_info) or ret != RedfishClient.ERR_CODE_OK:
                logger.log_error(f'Failed to get BMC EEPROM info: {ret}')
                return {}
            return eeprom_info
        except Exception as e:
            logger.log_error(f'Failed to get BMC EEPROM info: {str(e)}')
            return {}

    def get_version(self):
        """
        Retrieves the BMC firmware version

        Returns:
            A string containing the BMC firmware version.
            Returns 'N/A' if the BMC firmware version cannot be retrieved
        """
        ret = 0
        try:
            ret, version = self._get_firmware_version(self._get_firmware_id())
            if ret != RedfishClient.ERR_CODE_OK:
                logger.log_error(f'Failed to get BMC firmware version: {ret}')
                return 'N/A'
            return version
        except Exception as e:
            logger.log_error(f'Failed to get BMC firmware version: {str(e)}')  
            return 'N/A'

    @with_session_management
    def trigger_bmc_debug_log_dump(self):
        """
        Triggers a BMC debug log dump operation

        Returns:
            A tuple (ret, (task_id, err_msg)) where:
                ret: An integer return code indicating success (0) or failure
                task_id: A string containing the Redfish task ID for monitoring
                         the debug log dump operation. Returns '-1' on failure.
                err_msg: A string containing error message if operation failed,
                        None if successful
        """
        return self.rf_client.redfish_api_trigger_bmc_debug_log_dump()
    
    @with_session_management
    def get_bmc_debug_log_dump(self, task_id, filename, path, timeout = 120):
        """
        Retrieves the BMC debug log dump for a given task ID and saves it to
        the specified file path

        Args:
            task_id: A string containing the task ID from trigger_bmc_debug_log_dump
            filename: A string containing the filename to save the debug log
            path: A string containing the directory path where to save the debug log
            timeout: An integer, timeout in seconds for the operation (default: 120)

        Returns:
            A tuple (ret, err_msg) where:
                ret: An integer return code indicating success (0) or failure
                err_msg: A string containing error message if operation failed
        """
        return self.rf_client.redfish_api_get_bmc_debug_log_dump(task_id, filename, path, timeout)

    @with_session_management
    def update_firmware(self, fw_image):
        """
        Updates the BMC firmware with the provided firmware image

        Args:
            fw_image: A string containing the path to the firmware image file

        Returns:
            A tuple (ret, msg) where:
                ret: An integer return code indicating success (0) or failure
                msg: A string containing status message about the firmware update
        """
        logger.log_notice(f'Installing BMC firmware image {fw_image}')
        ret, msg = self.rf_client.redfish_api_update_firmware(fw_image, fw_ids=[self._get_firmware_id()])
        logger.log_notice(f'Firmware update result: {ret}')
        if msg:
            logger.log_notice(f'{msg}')
        return (ret, msg)
    
    @with_session_management
    def request_bmc_reset(self, graceful=True):
        """
        Generic BMC reset request

        Args:
            graceful: A boolean indicating whether to perform a graceful reset (True) or forceful reset (False)

        Returns:
            A tuple (ret, msg) where:
                ret: An integer return code indicating success (0) or failure
                msg: A string containing success message or error description
        """
        bmc_reset_type = RedfishClient.REDFISH_BMC_GRACEFUL_RESTART if graceful else RedfishClient.REDFISH_BMC_FORCE_RESTART
        return self.rf_client.redfish_api_request_bmc_reset(bmc_reset_type)

    def reset_root_password(self):
        """
        Resets the BMC root password to default

        Returns:
            A tuple (ret, msg) where:
                ret: An integer return code indicating success (0) or failure
                msg: A string containing success message or error description
        """
        return self._change_login_password(self._get_default_root_password(), BMCBase.ROOT_ACCOUNT)
