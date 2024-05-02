"""
    cmisTargetFWUpgrade.py

    Implementation of XcvrApi for CMIS based modules supporting firmware
    upgrade of remote target from the local target itself.
"""

import sys
import traceback
from ...fields import consts
from .cmis import CmisApi

import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

TARGET_E0_VALUE = 0
TARGET_E1_VALUE = 1
TARGET_E2_VALUE = 2

SERVER_FW_VERSION_SIZE = 16
SERVER_FW_VERSION_NUMBER_SIZE = 4

TARGET_LIST = [TARGET_E0_VALUE, TARGET_E1_VALUE, TARGET_E2_VALUE]

CABLE_E1_FIRMWARE_INFO_MAP = {
    'active_firmware': 'e1_active_firmware',
    'inactive_firmware': 'e1_inactive_firmware',
    'server_firmware': 'e1_server_firmware'
}

CABLE_E2_FIRMWARE_INFO_MAP = {
    'active_firmware': 'e2_active_firmware',
    'inactive_firmware': 'e2_inactive_firmware',
    'server_firmware': 'e2_server_firmware'
}

REMOTE_TARGET_FIRMWARE_INFO_MAP = {
    TARGET_E1_VALUE: CABLE_E1_FIRMWARE_INFO_MAP,
    TARGET_E2_VALUE: CABLE_E2_FIRMWARE_INFO_MAP,
}

class CmisTargetFWUpgradeAPI(CmisApi):
    def set_firmware_download_target_end(self, target):
        """
        Sets the target mode to the specified target.
        If the target mode is set to a remote target, then the page select byte is set to 0.
        Also, the remote target is then checked to ensure that its accessible.
        In case of any error, the target mode is restored to E0.
        Returns:
            True if the target mode is set successfully, False otherwise.
        """
        try:
            if not self.xcvr_eeprom.write(consts.TARGET_MODE, target):
                logger.error("Failed to set target mode to {}".format(target))
                return self._restore_target_to_E0()
            if target != TARGET_E0_VALUE:
                if not self.xcvr_eeprom.write(consts.PAGE_SELECT_BYTE, 0):
                    logger.error("Failed to set page select byte to {}".format(target))
                    return self._restore_target_to_E0()
                if not self._is_remote_target_accessible():
                    logger.error("Remote target {} not accessible.".format(target))
                    return self._restore_target_to_E0()
        except Exception as e:
            logger.error("Exception occurred while setting target mode to {}: {}".format(target, repr(e)))
            return self._restore_target_to_E0()

        return True

    def get_current_target_end(self):
        """
        Reads the target mode and returns the target mode.
        Returns:
            The target mode.
        """
        return self.xcvr_eeprom.read(consts.TARGET_MODE)

    """
    Reads the active, inactive and server firmware version from all targets
    and returns a dictionary of the firmware versions.
    Returns:
        A dictionary of the firmware versions for all targets.
    """
    def get_transceiver_info_firmware_versions(self):
        return_dict = {
            'active_firmware': 'N/A',
            'inactive_firmware': 'N/A',
            'e1_active_firmware': 'N/A',
            'e1_inactive_firmware': 'N/A',
            'e2_active_firmware': 'N/A',
            'e2_inactive_firmware': 'N/A',
            'e1_server_firmware': 'N/A',
            'e2_server_firmware': 'N/A'
        }

        for target in TARGET_LIST:
            try:
                if not self.set_firmware_download_target_end(target):
                    logger.error("Target mode change failed. Target: {}".format(target))
                    continue

                firmware_versions = super().get_transceiver_info_firmware_versions()
                if target in REMOTE_TARGET_FIRMWARE_INFO_MAP:
                    # Add server firmware version to the firmware_versions dictionary
                    firmware_versions.update(self._get_server_firmware_version())
                    return_dict.update(self._convert_firmware_info_to_target_firmware_info(
                                                                    firmware_versions, REMOTE_TARGET_FIRMWARE_INFO_MAP[target]))
                else:
                    return_dict.update(firmware_versions)
            except Exception as e:
                logger.error("Exception occurred while handling target {} firmware version: {}".format(target, repr(e)))
                exc_type, exc_value, exc_traceback = sys.exc_info()
                msg = traceback.format_exception(exc_type, exc_value, exc_traceback)
                for tb_line in msg:
                    for tb_line_split in tb_line.splitlines():
                        logger.error(tb_line_split)
                continue

        self.set_firmware_download_target_end(TARGET_E0_VALUE)
        return return_dict

    def _is_remote_target_accessible(self):
        """
        Once the target is changed to remote, any register apart from the TARGET_MODE register
        will have the value 0xff if the remote target is powered down.
        Assumption:
            The target mode has already been set to the desired remote target.
        Returns:
            True if the remote target is accessible from the local target, False otherwise.
        """
        module_type = self.get_module_type()
        if 'Unknown' in module_type:
            return False

        return True

    def _restore_target_to_E0(self):
        """
        Logs the error message and restores the target mode to E0.
        Returns:
            False always.
        """
        self.xcvr_eeprom.write(consts.TARGET_MODE, TARGET_E0_VALUE)
        return False

    def _convert_firmware_info_to_target_firmware_info(self, firmware_info, firmware_info_map):
        return_dict = {}
        for key, value in firmware_info_map.items():
            if key in firmware_info:
                return_dict[value] = firmware_info[key]
        return return_dict

    """
    Reads the server firmware version and return a dictionary of the server firmware version.
    The server firmware version is of the format "A.B.C.D" where A, B, C and D are 4 bytes each representing a number.
    Following are the steps to read the server firmware version:
        1. Read the magic byte at page 3h, offset 128. If this has the value 0x0, then the server
        firmware version is not available and hence, return without proceeding to step 2.
        2. Calculate the checksum of the server firmware version. If the checksum is not valid, then the server
        firmware version is not available. If the checksum is valid, then proceed to step 3.
        3. Read the server firmware version from page 3h, offset 130-145.
    Returns:
        A dictionary of the server firmware version.
    """
    def _get_server_firmware_version(self):
        return_dict = {
            'server_firmware': 'N/A'
        }

        magic_byte = self.xcvr_eeprom.read(consts.SERVER_FW_MAGIC_BYTE)
        if magic_byte != 0:
            checksum = self.xcvr_eeprom.read(consts.SERVER_FW_CHECKSUM)
            server_fw_version_byte_array, server_fw_version_str = self.xcvr_eeprom.read(consts.SERVER_FW_VERSION)

            calculated_checksum = 0
            for byte in server_fw_version_byte_array:
                calculated_checksum += byte

            if calculated_checksum & 0xFF == checksum:
                return_dict['server_firmware'] = server_fw_version_str

        return return_dict
