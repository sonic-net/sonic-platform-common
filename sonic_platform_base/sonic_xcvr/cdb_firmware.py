"""
    cdb_firmware.py

    Firmware management of a transceiver device through the CMIS CDB firmware
    flow, for platform objects that expose the device API with get_api() and
    rebuild it with refresh_api().
"""

import time
from collections.abc import Iterator

from sonic_py_common.syslogger import SysLogger

from .fields import consts

SYSLOG_IDENTIFIER = "CdbFirmware"
log = SysLogger(SYSLOG_IDENTIFIER)
log.logger.propagate = False

# CMIS CDB Run Firmware Image (0109h) mode: attempt a hitless reset to the
# inactive image.
FW_RUN_MODE_HITLESS_INACTIVE = 0x01

# Seconds to wait after running a new image, for the device to reset and be
# manageable again: the reset delay of the Run Firmware Image command plus
# tMgmtInit (2 s in CMIS), with margin.
FW_RUN_DELAY = 5


class CdbFirmwareMixin(object):
    """
    Download, run, commit and upgrade firmware through the CMIS CDB firmware
    flow of the device API returned by get_api(). The platform object also
    provides refresh_api(), called after a firmware run resets the device.

    The device API must provide the CmisCdbFw operations. A platform whose
    device needs additional steps overrides these methods and calls them
    through super().

    The operations take no lock. A platform whose device can be reached by
    another process or thread at the same time, such as the platform daemons,
    serializes them in its overrides.
    """

    def _get_cdb_fw_api(self):
        """Return the device API with its CDB firmware handler enabled."""
        api = self.get_api()
        enable = getattr(api, 'enable_cdb_fw_handler', None)
        if not callable(enable):
            raise NotImplementedError('The device API does not support CDB firmware management')
        enable()
        if api.cdb_fw_hdlr is None:
            raise NotImplementedError('The device does not support CDB firmware management')
        return api

    @staticmethod
    def _read_fw_version(api, major_field, minor_field):
        """Return a firmware version from the EEPROM, or None if the EEPROM does not report it."""
        try:
            major = api.xcvr_eeprom.read(major_field)
            minor = api.xcvr_eeprom.read(minor_field)
        except KeyError:
            # The memory map has no such field.
            return None
        if major is None or minor is None:
            return None
        return f'{major}.{minor}'

    @staticmethod
    def _parse_fw_info(text):
        """
        Return the 'name: value' lines of a CDB firmware info text as a dict.

        The text is the 'info' that CmisCdbFw.get_module_fw_info() returns.
        """
        info = {}
        for line in text.splitlines():
            name, separator, value = line.partition(':')
            if separator:
                info[name.strip()] = value.strip()
        return info

    @staticmethod
    def _abort_download(api, abort_supported):
        if not abort_supported:
            return
        try:
            # The module rejects a new command while the last one is executing.
            api.cdb_fw_hdlr.wait_for_cdb_status()
            if api.cdb_fw_hdlr.abort_fw_download() is not True:
                log.log_error('Failed to abort firmware download')
        except Exception as err:
            log.log_error(f'Failed to abort firmware download: {err}')

    def _download(self, api, file_path):
        features = api.cdb_fw_hdlr.get_fw_mgmt_features()
        if features is None:
            raise RuntimeError('Failed to get firmware management features')
        start_lpl_size, max_block_size, lpl_only, abort_supported = features

        success, info = api.module_fw_start_download(file_path)
        if not success:
            raise RuntimeError(f'Failed to start firmware download: {info.strip()}')
        try:
            # The start command carries the image header.
            if start_lpl_size:
                yield start_lpl_size
            yield from api.module_fw_write_blocks_iter(file_path, start_lpl_size, max_block_size, lpl_only)
        except RuntimeError:
            # A failed block write has already aborted the download.
            raise
        except BaseException:
            # The download stopped early, for example closed by the caller:
            # leave the device out of download mode.
            self._abort_download(api, abort_supported)
            raise

        success, info = api.module_fw_complete_download()
        if not success:
            raise RuntimeError(f'Failed to complete firmware download: {info.strip()}')

    def _run(self, api, mode):
        success, info = api.module_fw_run(mode)
        if not success:
            raise RuntimeError(f'Failed to run firmware: {info.strip()}')
        time.sleep(FW_RUN_DELAY)
        self.refresh_api()

    @staticmethod
    def _commit(api):
        success, info = api.module_fw_commit()
        if not success:
            raise RuntimeError(f'Failed to commit firmware: {info.strip()}')

    def download_firmware(self, file_path: str) -> Iterator[int]:
        """
        Downloads a firmware image to the inactive bank of the device

        Args:
            file_path: A string, the path of the firmware image

        Returns:
            An iterator that yields the number of bytes written for each
            block of the image. Closing it before the end aborts the download.

        Raises:
            NotImplementedError: The device does not support CDB firmware
                management
            RuntimeError: A CDB firmware command failed
        """
        yield from self._download(self._get_cdb_fw_api(), file_path)

    def run_firmware(self, mode: int = FW_RUN_MODE_HITLESS_INACTIVE) -> bool:
        """
        Runs a firmware image of the device, then waits FW_RUN_DELAY seconds
        for the device to reset and be manageable again.

        Args:
            mode: An integer, the CMIS CDB Run Firmware Image mode; by default,
                attempt a hitless reset to the inactive image

        Returns:
            A boolean, True if successful

        Raises:
            NotImplementedError: The device does not support CDB firmware
                management
            RuntimeError: The CDB command failed
        """
        self._run(self._get_cdb_fw_api(), mode)
        return True

    def commit_firmware(self) -> bool:
        """
        Commits the running firmware image of the device so that the device
        boots from it

        Returns:
            A boolean, True if successful

        Raises:
            NotImplementedError: The device does not support CDB firmware
                management
            RuntimeError: The CDB command failed
        """
        self._commit(self._get_cdb_fw_api())
        return True

    def upgrade_firmware(self, file_path: str) -> Iterator[int]:
        """
        Upgrades the firmware of the device: downloads the image to the
        inactive bank, runs it and commits it

        Args:
            file_path: A string, the path of the firmware image

        Returns:
            An iterator that yields the number of bytes written for each
            block of the image. Closing it before the end aborts the download.
            After the download, the run waits FW_RUN_DELAY seconds for the
            device to reset.

        Raises:
            NotImplementedError: The device does not support CDB firmware
                management
            RuntimeError: A CDB firmware command failed
        """
        api = self._get_cdb_fw_api()
        yield from self._download(api, file_path)
        self._run(api, FW_RUN_MODE_HITLESS_INACTIVE)
        # Running the image refreshed the device API.
        self._commit(self._get_cdb_fw_api())

    def get_firmware_info(self) -> dict:
        """
        Retrieves the firmware information of the device

        The information comes from the CDB Get Firmware Info command when the
        device supports CDB firmware management. Otherwise, only the active
        and inactive firmware versions are read from the EEPROM.

        Returns:
            A dict of the firmware information, in display order, such as
            {'Image A Version': '1.2.0', ..., 'Active Firmware': '1.2.0',
            'Inactive Firmware': '1.1.0'}. A version that the EEPROM does
            not report is 'N/A'.

        Raises:
            RuntimeError: The CDB command failed, or the device API is not
                available
        """
        try:
            result = self._get_cdb_fw_api().get_module_fw_info()
        except NotImplementedError:
            return self._read_eeprom_firmware_info()

        if not result.get('status'):
            raise RuntimeError(str(result.get('info') or '').strip() or 'Failed to get firmware info')
        return self._parse_fw_info(result['info'])

    def _read_eeprom_firmware_info(self):
        api = self.get_api()
        if api is None:
            raise RuntimeError('The device API is not available')
        active = self._read_fw_version(api, consts.ACTIVE_FW_MAJOR_REV, consts.ACTIVE_FW_MINOR_REV)
        inactive = self._read_fw_version(api, consts.INACTIVE_FW_MAJOR_REV, consts.INACTIVE_FW_MINOR_REV)
        return {
            'Active Firmware': active or 'N/A',
            'Inactive Firmware': inactive or 'N/A',
        }
