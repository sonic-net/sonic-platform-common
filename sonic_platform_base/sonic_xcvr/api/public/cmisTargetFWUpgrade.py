"""
    cmisTargetFWUpgrade.py

    Implementation of XcvrApi for CMIS based modules supporting firmware
    upgrade of remote target from the local target itself.
"""

import struct
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

AEC_E1_FIRMWARE_INFO_MAP = {
    'active_firmware': 'e1_active_firmware',
    'inactive_firmware': 'e1_inactive_firmware',
    'server_firmware': 'e1_server_firmware'
}

AEC_E2_FIRMWARE_INFO_MAP = {
    'active_firmware': 'e2_active_firmware',
    'inactive_firmware': 'e2_inactive_firmware',
    'server_firmware': 'e2_server_firmware'
}

REMOTE_TARGET_FIRMWARE_INFO_MAP = {
    TARGET_E1_VALUE: AEC_E1_FIRMWARE_INFO_MAP,
    TARGET_E2_VALUE: AEC_E2_FIRMWARE_INFO_MAP,
}

class CmisTargetFWUpgradeAPI(CmisApi):
    def set_firmware_download_target_end(self, target):
        return self.xcvr_eeprom.write(consts.TARGET_MODE, target)

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
                    logging.error("Target mode change failed. Target: {}".format(target))
                    continue

                # Any register apart from the TARGET_MODE register will have the value 0xff
                # if the remote target is not accessible from the local target.
                module_type = self.get_module_type()
                if 'Unknown' in module_type:
                    logging.info("Remote target {} not accessible. Skipping.".format(target))
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
                logging.error("Exception occurred while handling target {} firmware version: {}".format(target, repr(e)))
                exc_type, exc_value, exc_traceback = sys.exc_info()
                msg = traceback.format_exception(exc_type, exc_value, exc_traceback)
                for tb_line in msg:
                    for tb_line_split in tb_line.splitlines():
                        logging.error(tb_line_split)
                continue

        self.set_firmware_download_target_end(TARGET_E0_VALUE)
        return return_dict

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
            server_fw_version_byte_array = self.xcvr_eeprom.read(consts.SERVER_FW_VERSION)

            calculated_checksum = 0
            for byte in server_fw_version_byte_array:
                calculated_checksum += byte

            if calculated_checksum & 0xFF == checksum:
                server_fw_version_str = ''
                for i in range(0, SERVER_FW_VERSION_SIZE, SERVER_FW_VERSION_NUMBER_SIZE):
                    server_fw_version_number = bytes(server_fw_version_byte_array[i:i+SERVER_FW_VERSION_NUMBER_SIZE])
                    # Each number of the server firmware version is 4 bytes and is stored in big endian format.
                    # Convert the 4 bytes to a number and then convert the number to a string.
                    server_fw_version_str += str(struct.unpack('>I', server_fw_version_number)[0]) + '.'
                server_fw_version_str = server_fw_version_str[:-1]
                return_dict['server_firmware'] = server_fw_version_str

        return return_dict
