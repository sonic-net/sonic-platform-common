"""
    cdb_fw.py

    All CDB firmware related APIs are here, separated from the core CMIS transceiver API.
"""

from ...fields import consts
from ...fields import cdb_consts
from ...codes.public.cdb import CdbCodes
from ...mem_maps.public.cdb import CdbMemMap
from ...cdb.cdb_fw import CdbFwHandler as CdbFw
import time
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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
            cdb_mem_map = CdbMemMap(CdbCodes)
            return CdbFw(self.xcvr_eeprom.reader, self.xcvr_eeprom.writer, cdb_mem_map)
        except AssertionError as err:
            logger.error("Failed to initialize CDB firmware handler due to assertion: %s", err)
        except Exception as err:
            logger.error("Failed to initialize CDB firmware handler: %s", err)

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
            logger.error(txt)
            return {'status': False, 'info': txt, 'feature': None}

        startLPLsize, maxblocksize, lplonly_flag = fw_features
        txt += 'Start payload size %d\n' % startLPLsize
        txt += 'Max block size %d\n' % maxblocksize
        if lplonly_flag:
            txt += 'Write to LPL supported\n'
        else:
            txt += 'Write to LPL/EPL supported\n'

        elapsedtime = time.time()-starttime
        logger.info('Get module FW upgrade features time: %.2f s\n' %elapsedtime)
        logger.info(txt)
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
            if self.get_status_code() == 70:
                logger.info('Get module FW info: Need to enter password')
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
            logger.info('Run firmware status: Success')
            return 1
        status = self.get_status_code()
        logger.info('Run firmware status: Fail- %s', self.cdb_fw_hdlr.get_last_cmd_status())
        return status

    def cdb_commit_firmware(self):
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.commit_fw_image() is True:
            logger.info('Commit firmware status: Success')
            return 1
        status = self.get_status_code()
        logger.info('Commit firmware status: Fail- %s', self.cdb_fw_hdlr.get_last_cmd_status())
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
            if fw_run_status == 70:
                string = 'Module FW run: Need to enter password\n'
                logger.info(string)
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
        logger.info('Module FW run time: %.2f s\n' %elapsedtime)
        logger.info(txt)
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
            if fw_commit_status == 70:
                string = 'Module FW commit: Need to enter password\n'
                logger.info(string)
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
        logger.info('Module FW commit time: %.2f s\n' %elapsedtime)
        logger.info(txt)
        return True, txt

    def cdb_firmware_download_complete(self):
        # complete FW download (CMD 0107h)
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.complete_fw_download() is True:
            logger.info('Firmware download complete status: Success')
            return 1
        status = self.get_status_code()
        logger.info('Firmware download complete status: Fail- %s', self.cdb_fw_hdlr.get_last_cmd_status())
        return status

    def cdb_start_firmware_download(self, filepath):
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.start_fw_download(filepath) is True:
            logger.info('Start firmware download status: Success')
            return 1
        status = self.get_status_code()
        logger.info('Start firmware download status: Fail- %s', self.cdb_fw_hdlr.get_last_cmd_status())
        return status

    def cdb_lpl_block_write(self, address, data):
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.write_lpl_block(address, data) is True:
            return 1
        status = self.get_status_code()
        logger.info('LPL firmware download status: Fail- %s', self.cdb_fw_hdlr.get_last_cmd_status())
        return status

    def cdb_epl_block_write(self, address, data):
        if self.cdb_fw_hdlr is None:
            return 0
        self.cdb_fw_hdlr.write_epl_pages(data)
        if self.cdb_fw_hdlr.write_epl_block(address, data) is True:
            return 1
        status = self.get_status_code()
        logger.info('EPL firmware download status: Fail- %s', self.cdb_fw_hdlr.get_last_cmd_status())
        return status

    def cdb_enter_host_password(self, password):
        if self.cdb_fw_hdlr is None:
            return 0
        if self.cdb_fw_hdlr.enter_password(password) is True:
            logger.info('CDB host auth status: Success')
            return 1
        status = self.get_status_code()
        logger.info('CDB host auth status: Fail- %s', self.cdb_fw_hdlr.get_last_cmd_status())
        return status

    def module_fw_download(self, startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength, imagepath):
        """
        This function performs the download of a firmware image to module eeprom
        It starts CDB download by writing the header of start header size
        from the designated firmware file to the local payload page 0x9F, with CDB command 0101h.

        Then it repeatedly reads from the given firmware file and write to the payload
        space advertised from the first step. We use CDB command 0103h to write to the local payload;
        we use CDB command 0104h to write to the extended paylaod. This step repeats until it reaches
        end of the firmware file, or the CDB status failed.

        The last step is to complete the firmware upgrade with CDB command 0107h.

        Note that if the download process fails anywhere in the middle, we need to run CDB command 0102h
        to abort the upgrade before we restart another upgrade process.

        This function returns True if download successfully completes. Otherwise it will return False where it fails.
        """
        txt = ''
        if self.cdb_fw_hdlr is None:
            return False, "CDB NOT supported on this module"

        # start fw download (CMD 0101h)
        starttime = time.time()
        logger.info('\nStart FW downloading')
        logger.info("startLPLsize is %d" %startLPLsize)
        try:
            result = self.cdb_fw_hdlr.start_fw_download(imagepath)
        except FileNotFoundError:
            txt += 'Image path  %s is incorrect.\n' % imagepath
            logger.info(txt)
            return False, txt

        if result is True:
            string = 'Start module FW download: Success\n'
            logger.info(string)
        else:
            fw_start_status = self.get_status_code()
            # password error
            if fw_start_status == 70:
                string = 'Start module FW download: Need to enter password\n'
                logger.info(string)
                self.cdb_fw_hdlr.enter_password()
                if self.cdb_fw_hdlr.start_fw_download(imagepath) is not True:
                    txt += 'Start module FW download: Fail after password retry\n'
                    self.cdb_fw_hdlr.abort_fw_download()
                    logger.info(txt)
                    return False, txt
            else:
                string = 'Start module FW download: Fail\n'
                txt += string
                self.cdb_fw_hdlr.abort_fw_download()
                txt += 'FW_start_status %d\n' %fw_start_status
                logger.info(txt)
                return False, txt
        elapsedtime = time.time()-starttime
        logger.info('Start module FW download time: %.2f s' %elapsedtime)

        # start periodically writing (CMD 0103h or 0104h)
        if lplonly_flag:
            BLOCK_SIZE = cdb_consts.LPL_MAX_PAYLOAD_SIZE
        else:
            BLOCK_SIZE = maxblocksize

        with open(imagepath, 'rb') as f:
            f.seek(0, 2)
            imagesize = f.tell()
            f.seek(startLPLsize, 0)

            address = 0
            remaining = imagesize - startLPLsize
            logger.info("\nTotal size: {} start bytes: {} remaining: {}".format(imagesize, startLPLsize, remaining))
            while remaining > 0:
                count = min(remaining, BLOCK_SIZE)
                data = f.read(count)
                if lplonly_flag:
                    result = self.cdb_fw_hdlr.write_lpl_block(address, data)
                else:
                    self.cdb_fw_hdlr.write_epl_pages(data)
                    result = self.cdb_fw_hdlr.write_epl_block(address, data)
                if result is not True:
                    self.cdb_fw_hdlr.abort_fw_download()
                    fw_download_status = self.get_status_code()
                    txt += 'CDB download failed. CDB Status: %d\n' %fw_download_status
                    logger.info(txt)
                    return False, txt
                elapsedtime = time.time()-starttime
                address += count
                remaining -= count
                progress = (imagesize - remaining) * 100.0 / imagesize
                logger.info('Address: {:#08x}; Count: {}; Remain: {:#08x}; Progress: {:.2f}%; Time: {:.2f}s'.format(address, count, remaining, progress, elapsedtime))

        elapsedtime = time.time()-starttime
        logger.info('Total module FW download time: %.2f s' %elapsedtime)

        time.sleep(2)
        # complete FW download (CMD 0107h)
        result = self.cdb_fw_hdlr.complete_fw_download()
        if result is True:
            string = 'Module FW download complete: Success'
            logger.info(string)
            txt += string
        else:
            fw_complete_status = self.get_status_code()
            txt += 'Module FW download complete: Fail\n'
            txt += 'FW_complete_status %d\n' %fw_complete_status
            logger.info(txt)
            return False, txt
        elapsedtime = time.time()-elapsedtime-starttime
        string = 'Complete module FW download time: %.2f s\n' %elapsedtime
        logger.info(string)
        txt += string
        return True, txt

    def module_fw_upgrade(self, imagepath):
        """
        This function performs firmware upgrade.
        1.  show FW version in the beginning
        2.  check module advertised FW download capability
        3.  configure download
        4.  show download progress
        5.  configure run downloaded firmware
        6.  configure commit downloaded firmware
        7.  show FW version in the end

        imagepath specifies where firmware image file is located.
        target_firmware is a string that specifies the firmware version to upgrade to

        This function returns True if download successfully completes.
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
        switch_status, switch_txt = self.module_fw_switch()
        status = download_status and switch_status
        txt += switch_txt
        return status, txt

    def module_fw_switch(self):
        """
        This function switch the active/inactive module firmware in the current module memory
        This function returns True if firmware switch successfully completes.
        Otherwise it will return False.
        If not both images are valid, it will stop firmware switch and return False
        """
        txt = ''
        result = self.get_module_fw_info()
        try:
            (ImageA_init, ImageARunning_init, ImageACommitted_init, ImageAValid_init,
             ImageB_init, ImageBRunning_init, ImageBCommitted_init, ImageBValid_init, _, _) = result['result']
        except (ValueError, TypeError):
            return result['status'], result['info']
        if ImageAValid_init == 0 and ImageBValid_init == 0:
            self.module_fw_run(mode = 0x01)
            time.sleep(60)
            self.module_fw_commit()
            result = self.get_module_fw_info()
            try:
                (ImageA, ImageARunning, ImageACommitted, ImageAValid,
                 ImageB, ImageBRunning, ImageBCommitted, ImageBValid, _, _) = result['result']
            except (ValueError, TypeError):
                return result['status'], result['info']
            # detect if image switch happened
            txt += 'Before switch Image A: %s; Run: %d Commit: %d, Valid: %d\n' %(
                ImageA_init, ImageARunning_init, ImageACommitted_init, ImageAValid_init
            )
            txt += 'Before switch Image B: %s; Run: %d Commit: %d, Valid: %d\n' %(
                ImageB_init, ImageBRunning_init, ImageBCommitted_init, ImageBValid_init
            )
            txt += 'After switch Image A: %s; Run: %d Commit: %d, Valid: %d\n' %(ImageA, ImageARunning, ImageACommitted, ImageAValid)
            txt += 'After switch Image B: %s; Run: %d Commit: %d, Valid: %d\n' %(ImageB, ImageBRunning, ImageBCommitted, ImageBValid)
            if (ImageARunning_init == 1 and ImageARunning == 1) or (ImageBRunning_init == 1 and ImageBRunning == 1):
                txt += 'Switch did not happen.\n'
                logger.info(txt)
                return False, txt
            else:
                logger.info(txt)
                return True, txt
        else:
            txt += 'Not both images are valid.'
            logger.info(txt)
            return False, txt
