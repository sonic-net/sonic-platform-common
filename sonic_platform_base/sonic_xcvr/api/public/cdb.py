"""
    cdb.py

    All CDB-related APIs are consolidated here, separated from the core CMIS transceiver API.
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
    Must be used with a class that has xcvr_eeprom and is_flat_memory() (e.g., CmisApi).
    """

    def _init_cdb(self, xcvr_eeprom, init_cdb_fw_handler=False):
        """Initialize CDB-related attributes. Call from __init__."""
        self._init_cdb_fw_handler = init_cdb_fw_handler
        self._cdb_fw_hdlr = None

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
        cdb_mem_map = CdbMemMap(CdbCodes)
        return CdbFw(self.xcvr_eeprom.reader, self.xcvr_eeprom.writer, cdb_mem_map)

    def is_cdb_supported(self):
        '''
        This function returns whether CDB is supported
        '''
        if self.is_flat_memory():
            return False

        cdb_inst = self.xcvr_eeprom.read(consts.CDB_SUPPORT)
        if cdb_inst is None:
            return False

        if cdb_inst == 1 or cdb_inst == 2:
            return True

        return False

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
            return None
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
            status = self.cdb_fw_hdlr.get_cmd_status_code()
            if status and status[cdb_consts.CDB1_HAS_FAILED] and status[cdb_consts.CDB1_STATUS] == cdb_consts.CDB_PASSWORD_ERROR_CODE:
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
            return None
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

