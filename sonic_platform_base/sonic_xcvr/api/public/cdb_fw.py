"""
    cdb_fw.py

    All CDB firmware related APIs are here, separated from the core CMIS transceiver API.
"""

from ...fields import consts
from ...fields import cdb_consts
from ...cdb.cdb_fw import CdbFwHandler as CdbFw
import time
from sonic_py_common.syslogger import SysLogger

SYSLOG_IDENTIFIER = "CdbFwApi"
log = SysLogger(SYSLOG_IDENTIFIER)
log.logger.propagate = False


class CmisCdbFw:
    """
    CDB firmware upgrade operations for CMIS modules.
    """

    @property
    def cdb_fw_hdlr(self):
        if not self._init_cdb_fw_handler:
            return None

        if self._cdb_fw_hdlr is None:
            self._cdb_fw_hdlr = self._create_cdb_fw_handler()
        return self._cdb_fw_hdlr

    def _create_cdb_fw_handler(self):
        if not self.is_cdb_supported():
            self._init_cdb_fw_handler = False
            return None

        try:
            return CdbFw(self.xcvr_eeprom.reader, self.xcvr_eeprom.writer, self._cdb_mem_map)
        except AssertionError as err:
            log.log_error("Failed to initialize CDB firmware handler due to assertion: {}".format(err))
        except Exception as err:
            log.log_error("Failed to initialize CDB firmware handler: {}".format(err))

        self._init_cdb_fw_handler = False
        return None

    def get_module_fw_mgmt_feature(self, verbose = False):
        """
        This function obtains CDB features supported by the module from CDB command 0041h,
        such as start header size, maximum block size, whether extended payload messaging
        (page 0xA0 - 0xAF) or only local payload is supported. These features are important because
        the following upgrade with depend on these parameters.
        """
        txt = ''
        if self.cdb_fw_hdlr is None:
            return {'status': False, 'info': "CDB Not supported", 'feature': None}

        # get fw upgrade features (CMD 0041h)
        starttime = time.time()
        autopaging = self.xcvr_eeprom.read(consts.AUTO_PAGING_SUPPORT)
        autopaging_flag = bool(autopaging)
        writelength_raw = self.xcvr_eeprom.read(consts.CDB_SEQ_WRITE_LENGTH_EXT)
        if writelength_raw is None:
            return {'status': False, 'info': "Failed to read write length", 'feature': None}
        writelength = (writelength_raw + 1) * 8
        txt += 'Auto page support: %s\n' %autopaging_flag
        txt += 'Max write length: %d\n' %writelength

        fw_features = self.cdb_fw_hdlr.get_fw_mgmt_features()
        if fw_features is None:
            txt += 'Failed to get firmware management features\n'
            log.log_error(txt)
            return {'status': False, 'info': txt, 'feature': None}

        startLPLsize, maxblocksize, lplonly_flag = fw_features
        txt += 'Start payload size %d\n' % startLPLsize
        txt += 'Max block size %d\n' % maxblocksize
        if lplonly_flag:
            txt += 'Write to LPL supported\n'
        else:
            txt += 'Write to LPL/EPL supported\n'

        elapsedtime = time.time()-starttime
        log.log_info('Get module FW upgrade features time: {:.2f} s\n'.format(elapsedtime))
        log.log_notice(txt)
        return {'status': True, 'info': txt, 'feature': (startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength)}

    def get_module_fw_info(self):
        """
        This function returns firmware Image A and B version, running version, committed version
        and whether both firmware images are valid.
        Operational Status: 1 = running, 0 = not running
        Administrative Status: 1=committed, 0=uncommitted
        Validity Status: 1 = invalid, 0 = valid
        """
        txt = ''

        if self.cdb_fw_hdlr is None:
            return {'status': False, 'info': "CDB Not supported", 'result': None}

        fw_info = self.cdb_fw_hdlr.get_firmware_info()

        # password issue
        if fw_info is False or fw_info is None:
            if self.get_status_code() == cdb_consts.CDB_PASSWORD_ERROR_STATUS:
                log.log_notice('Get module FW info: Need to enter password')
                self.cdb_fw_hdlr.enter_password()
                fw_info = self.cdb_fw_hdlr.get_firmware_info()

        if fw_info is False or fw_info is None:
            # Return 0 distinguishes busy/command failure and interface fail from unsupported CDB
            return {'status': False, 'info': "Failed to get firmware info", 'result': 0}

        fw_status = fw_info.get(cdb_consts.CDB1_FIRMWARE_STATUS, {})
        ImageARunning = int(fw_status.get(cdb_consts.CDB1_BANKA_OPER_STATUS, False))
        ImageACommitted = int(fw_status.get(cdb_consts.CDB1_BANKA_ADMIN_STATUS, False))
        ImageAValid = int(fw_status.get(cdb_consts.CDB1_BANKA_VALID_STATUS, True))
        ImageBRunning = int(fw_status.get(cdb_consts.CDB1_BANKB_OPER_STATUS, False))
        ImageBCommitted = int(fw_status.get(cdb_consts.CDB1_BANKB_ADMIN_STATUS, False))
        ImageBValid = int(fw_status.get(cdb_consts.CDB1_BANKB_VALID_STATUS, True))

        if ImageAValid == 0:
            ImageA = '{}.{}.{}'.format(
                fw_info.get(cdb_consts.CDB1_BANKA_MAJOR_VERSION, 0),
                fw_info.get(cdb_consts.CDB1_BANKA_MINOR_VERSION, 0),
                fw_info.get(cdb_consts.CDB1_BANKA_BUILD_VERSION, 0)
            )
        else:
            ImageA = "N/A"
        txt += 'Image A Version: {}\n'.format(ImageA)

        if ImageBValid == 0:
            ImageB = '{}.{}.{}'.format(
                fw_info.get(cdb_consts.CDB1_BANKB_MAJOR_VERSION, 0),
                fw_info.get(cdb_consts.CDB1_BANKB_MINOR_VERSION, 0),
                fw_info.get(cdb_consts.CDB1_BANKB_BUILD_VERSION, 0)
            )
        else:
            ImageB = "N/A"
        txt += 'Image B Version: {}\n'.format(ImageB)

        FactoryImage = '{}.{}.{}'.format(
            fw_info.get(cdb_consts.CDB1_FACTORY_MAJOR_VERSION, 0),
            fw_info.get(cdb_consts.CDB1_FACTORY_MINOR_VERSION, 0),
            fw_info.get(cdb_consts.CDB1_FACTORY_BUILD_VERSION, 0)
        )
        txt += 'Factory Image Version: {}\n'.format(FactoryImage)

        ActiveFirmware = 'N/A'
        InactiveFirmware = 'N/A'
        if ImageARunning == 1:
            RunningImage = 'A'
            ActiveFirmware = ImageA
            InactiveFirmware = ImageB
        elif ImageBRunning == 1:
            RunningImage = 'B'
            ActiveFirmware = ImageB
            InactiveFirmware = ImageA
        else:
            RunningImage = 'N/A'
        if ImageACommitted == 1:
            CommittedImage = 'A'
        elif ImageBCommitted == 1:
            CommittedImage = 'B'
        else:
            CommittedImage = 'N/A'

        txt += 'Running Image: {}\n'.format(RunningImage)
        txt += 'Committed Image: {}\n'.format(CommittedImage)
        txt += 'Active Firmware: {}\n'.format(ActiveFirmware)
        txt += 'Inactive Firmware: {}\n'.format(InactiveFirmware)
        return {'status': True, 'info': txt, 'result': (ImageA, ImageARunning, ImageACommitted, ImageAValid, ImageB, ImageBRunning, ImageBCommitted, ImageBValid, ActiveFirmware, InactiveFirmware)}

    # Returns raw CDB status byte: 1=success, 0x40|code=failed, 0x80|code=busy, 0=no handler
    def get_status_code(self):
        """
        Get raw status byte from last CDB command.
        """
        status = self.cdb_fw_hdlr.get_cmd_status_code()
        if status is None:
            return 0
        status_code = status[cdb_consts.CDB1_STATUS]
        if status[cdb_consts.CDB1_IS_BUSY]:
            return 0x80 | status_code
        if status[cdb_consts.CDB1_HAS_FAILED]:
            return 0x40 | status_code
        return status_code

    def cdb_run_firmware(self, mode = 0x01):
        # run module FW (CMD 0109h)
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.run_fw_image(mode) is True:
            log.log_notice('Run firmware status: Success')
            return 1
        status = self.get_status_code()
        log.log_notice('Run firmware status: Fail- {}'.format(self.cdb_fw_hdlr.get_last_cmd_status()))
        return status

    def cdb_commit_firmware(self):
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.commit_fw_image() is True:
            log.log_notice('Commit firmware status: Success')
            return 1
        status = self.get_status_code()
        log.log_notice('Commit firmware status: Fail- {}'.format(self.cdb_fw_hdlr.get_last_cmd_status()))
        return status

    def module_fw_run(self, mode = 0x01):
        """
        This command is used to start and run a selected image.
        This command transfers control from the currently
        running firmware to a selected firmware that is started. It
        can be used to switch between firmware versions, or to
        perform a restart of the currently running firmware.
        mode:
        00h = Traffic affecting Reset to Inactive Image.
        01h = Attempt Hitless Reset to Inactive Image
        02h = Traffic affecting Reset to Running Image.
        03h = Attempt Hitless Reset to Running Image

        This function returns True if firmware run successfully completes.
        Otherwise it will return False.
        """
        # run module FW (CMD 0109h)
        txt = ''
        if self.cdb_fw_hdlr is None:
            return False, "CDB NOT supported on this module"
        starttime = time.time()
        result = self.cdb_fw_hdlr.run_fw_image(mode)
        if result is True:
            txt += 'Module FW run: Success\n'
        else:
            fw_run_status = self.get_status_code()
            # password issue
            if fw_run_status == cdb_consts.CDB_PASSWORD_ERROR_STATUS:
                string = 'Module FW run: Need to enter password\n'
                log.log_notice(string)
                self.cdb_fw_hdlr.enter_password()
                result = self.cdb_fw_hdlr.run_fw_image(mode)
                if result is not True:
                    txt += 'Module FW run: Fail after password retry\n'
                    txt += 'FW_run_status %d\n' % self.get_status_code()
                    return False, txt
                txt += 'Module FW run: Success after password retry\n'
            else:
                txt += 'Module FW run: Fail\n'
                txt += 'FW_run_status %d\n' % fw_run_status
                return False, txt
        elapsedtime = time.time()-starttime
        log.log_info('Module FW run time: {:.2f} s\n'.format(elapsedtime))
        log.log_notice(txt)
        return True, txt

    def module_fw_commit(self):
        """
        The host uses this command to commit the running image
        so that the module will boot from it on future boots.

        This function returns True if firmware commit successfully completes.
        Otherwise it will return False.
        """
        txt = ''
        if self.cdb_fw_hdlr is None:
            return False, "CDB NOT supported on this module"
        # commit module FW (CMD 010Ah)
        starttime = time.time()
        result = self.cdb_fw_hdlr.commit_fw_image()
        if result is True:
            txt += 'Module FW commit: Success\n'
        else:
            fw_commit_status = self.get_status_code()
            # password issue
            if fw_commit_status == cdb_consts.CDB_PASSWORD_ERROR_STATUS:
                string = 'Module FW commit: Need to enter password\n'
                log.log_notice(string)
                self.cdb_fw_hdlr.enter_password()
                result = self.cdb_fw_hdlr.commit_fw_image()
                if result is not True:
                    txt += 'Module FW commit: Fail after password retry\n'
                    txt += 'FW_commit_status %d\n' % self.get_status_code()
                    return False, txt
                txt += 'Module FW commit: Success after password retry\n'
            else:
                txt += 'Module FW commit: Fail\n'
                txt += 'FW_commit_status %d\n' % fw_commit_status
                return False, txt
        elapsedtime = time.time()-starttime
        log.log_info('Module FW commit time: {:.2f} s\n'.format(elapsedtime))
        log.log_notice(txt)
        return True, txt

    def cdb_firmware_download_complete(self):
        # complete FW download (CMD 0107h)
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.complete_fw_download() is True:
            log.log_notice('Firmware download complete status: Success')
            return 1
        status = self.get_status_code()
        log.log_notice('Firmware download complete status: Fail- {}'.format(self.cdb_fw_hdlr.get_last_cmd_status()))
        return status

    def cdb_start_firmware_download(self, filepath):
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.start_fw_download(filepath) is True:
            log.log_notice('Start firmware download status: Success')
            return 1
        status = self.get_status_code()
        log.log_notice('Start firmware download status: Fail- {}'.format(self.cdb_fw_hdlr.get_last_cmd_status()))
        return status

    def cdb_lpl_block_write(self, address, data):
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.write_lpl_block(address, data) is True:
            return 1
        status = self.get_status_code()
        log.log_notice('LPL firmware download status: Fail- {}'.format(self.cdb_fw_hdlr.get_last_cmd_status()))
        return status

    def cdb_epl_block_write(self, address, data):
        if self.cdb_fw_hdlr is None:
            return 0
        try:
            self.cdb_fw_hdlr.write_epl_pages(data)
        except AssertionError as err:
            log.log_error('EPL write_epl_pages failed: {}'.format(err))
            return 0
        if self.cdb_fw_hdlr.write_epl_block(address, data) is True:
            return 1
        status = self.get_status_code()
        log.log_notice('EPL firmware download status: Fail- {}'.format(self.cdb_fw_hdlr.get_last_cmd_status()))
        return status

    def cdb_enter_host_password(self, password):
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.enter_password(password) is True:
            log.log_notice('CDB host auth status: Success')
            return 1
        status = self.get_status_code()
        log.log_notice('CDB host auth status: Fail- {}'.format(self.cdb_fw_hdlr.get_last_cmd_status()))
        return status

    def module_fw_start_download(self, imagepath):
        """
        Start firmware download with CDB command 0101h.
        Handles password retry if the module requires authentication.

        This function returns True on success.
        Otherwise it will return False.
        """
        if self.cdb_fw_hdlr is None:
            return False, "CDB NOT supported on this module"

        log.log_notice('\nStart FW downloading')
        try:
            result = self.cdb_fw_hdlr.start_fw_download(imagepath)
        except FileNotFoundError:
            txt = 'Image path %s is incorrect.\n' % imagepath
            log.log_notice(txt)
            return False, txt

        if result is True:
            log.log_notice('Start module FW download: Success\n')
            return True, ''

        fw_start_status = self.get_status_code()
        # password error - retry with default password
        if fw_start_status == cdb_consts.CDB_PASSWORD_ERROR_STATUS:
            log.log_notice('Start module FW download: Need to enter password\n')
            self.cdb_fw_hdlr.enter_password()
            if self.cdb_fw_hdlr.start_fw_download(imagepath) is True:
                return True, ''
            txt = 'Start module FW download: Fail after password retry\n'
            self.cdb_fw_hdlr.abort_fw_download()
            log.log_notice(txt)
            return False, txt

        txt = 'Start module FW download: Fail\n'
        self.cdb_fw_hdlr.abort_fw_download()
        txt += 'FW_start_status %d\n' % fw_start_status
        log.log_notice(txt)
        return False, txt

    def module_fw_write_blocks(self, imagepath, startLPLsize, maxblocksize, lplonly_flag):
        """
        Write firmware blocks using CDB command 0103h (LPL) or 0104h (EPL).
        Aborts the download if any block write fails.

        This function returns True on success.
        Otherwise it will return False.
        """
        starttime = time.time()
        BLOCK_SIZE = cdb_consts.LPL_MAX_PAYLOAD_SIZE if lplonly_flag else maxblocksize

        with open(imagepath, 'rb') as f:
            f.seek(0, 2)
            imagesize = f.tell()
            f.seek(startLPLsize, 0)

            address = 0
            remaining = imagesize - startLPLsize
            log.log_info("\nTotal size: {} start bytes: {} remaining: {}".format(imagesize, startLPLsize, remaining))
            while remaining > 0:
                count = min(remaining, BLOCK_SIZE)
                data = f.read(count)
                if lplonly_flag:
                    result = self.cdb_fw_hdlr.write_lpl_block(address, data)
                else:
                    try:
                        self.cdb_fw_hdlr.write_epl_pages(data)
                    except AssertionError as err:
                        self.cdb_fw_hdlr.abort_fw_download()
                        txt = 'CDB download failed: {}'.format(err)
                        log.log_error(txt)
                        return False, txt
                    result = self.cdb_fw_hdlr.write_epl_block(address, data)
                if result is not True:
                    self.cdb_fw_hdlr.abort_fw_download()
                    fw_download_status = self.get_status_code()
                    txt = 'CDB download failed. CDB Status: %d\n' % fw_download_status
                    log.log_notice(txt)
                    return False, txt
                address += count
                remaining -= count
                progress = (imagesize - remaining) * 100.0 / imagesize
                elapsedtime = time.time() - starttime
                log.log_info('Address: {:#08x}; Count: {}; Remain: {:#08x}; Progress: {:.2f}%; Time: {:.2f}s'.format(
                    address, count, remaining, progress, elapsedtime))

        log.log_info('Total module FW download time: {:.2f} s'.format(time.time() - starttime))
        return True, ''

    def module_fw_complete_download(self):
        """
        Complete firmware download with CDB command 0107h.

        This function returns True on success.
        Otherwise it will return False.
        """
        result = self.cdb_fw_hdlr.complete_fw_download()
        if result is True:
            txt = 'Module FW download complete: Success\n'
            log.log_notice(txt)
            return True, txt

        fw_complete_status = self.get_status_code()
        txt = 'Module FW download complete: Fail\n'
        txt += 'FW_complete_status %d\n' % fw_complete_status
        log.log_notice(txt)
        return False, txt

    def module_fw_download(self, startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength, imagepath):
        """
        This function performs the full firmware download sequence:
        1. Start download with password retry
        2. Write firmware blocks
        3. Complete download

        This function returns True on success.
        Otherwise it will return False.
        """
        success, txt = self.module_fw_start_download(imagepath)
        if not success:
            return False, txt

        success, msg = self.module_fw_write_blocks(imagepath, startLPLsize, maxblocksize, lplonly_flag)
        txt += msg
        if not success:
            return False, txt

        success, msg = self.module_fw_complete_download()
        txt += msg
        if not success:
            return False, txt

        return True, txt

    def module_fw_upgrade(self, imagepath, timeout=5):
        """
        This function performs a full firmware upgrade:
        1.  Get current firmware info
        2.  Check module advertised FW management features
        3.  Download firmware image
        4.  Run the downloaded firmware
        5.  Commit the running firmware

        imagepath specifies where firmware image file is located.
        timeout specifies the wait time in seconds after run before commit (default: 5).

        This function returns True if upgrade successfully completes.
        Otherwise it will return False.
        """
        result = self.get_module_fw_info()
        try:
            _, _, _, _, _, _, _, _, _, _ = result['result']
        except (ValueError, TypeError):
            return result['status'], result['info']
        result = self.get_module_fw_mgmt_feature()
        try:
            startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength = result['feature']
        except (ValueError, TypeError):
            return result['status'], result['info']

        download_status, txt = self.module_fw_download(startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength, imagepath)
        if not download_status:
            return False, txt

        success, info = self.module_fw_run(mode=0x01)
        if not success:
            txt += 'Module FW run failed\n' + info
            return False, txt
        time.sleep(timeout)

        success, info = self.module_fw_commit()
        if not success:
            txt += 'Module FW commit failed\n' + info
            return False, txt

        log.log_notice('Module firmware upgrade successful')
        return True, txt
