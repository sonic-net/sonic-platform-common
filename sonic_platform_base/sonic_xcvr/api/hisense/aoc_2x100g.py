"""
    aoc_2x100g.py

    Firmware management for modules that use single-bank firmware architecture.
"""
import logging
from ..public.cmis import CmisApi

logger = logging.getLogger(__name__)

class CmisAocSingleBankApi(CmisApi):
    def get_module_fw_info(self):
        """
        This function returns firmware Image A and B version, running version, committed version
        and whether both firmware images are valid.
        Operational Status: 1 = running, 0 = not running
        Administrative Status: 1=committed, 0=uncommitted
        Validity Status: 1 = invalid, 0 = valid
        """
        txt = ''

        if self.cdb is None:
            return {'status': False, 'info': "CDB Not supported", 'result': None}

        # get fw info (CMD 0100h)
        result = self.cdb.get_fw_info()
        status = result['status']
        rpllen, rpl_chkcode, rpl = result['rpl']

        # Interface NACK or timeout
        if (rpllen is None) or (rpl_chkcode is None):
            return {'status': False, 'info': "Interface fail", 'result': 0} # Return result 0 for distinguishing CDB is maybe in busy or failure.

        # password issue
        if status == 0x46:
            string = 'Get module FW info: Need to enter password\n'
            logger.info(string)
            # Reset password for module using CMIS 4.0
            self.cdb.module_enter_password(0)
            result = self.cdb.get_fw_info()
            status = result['status']
            rpllen, rpl_chkcode, rpl = result['rpl']

        if status == 1 and self.cdb.cdb_chkcode(rpl) == rpl_chkcode:
            # Register 9Fh:136
            fwStatus = rpl[0]
            ImageARunning = (fwStatus & 0x01) # bit 0 - image A is running
            ImageACommitted = ((fwStatus >> 1) & 0x01) # bit 1 - image A is committed
            ImageAValid = ((fwStatus >> 2) & 0x01) # bit 2 - image A is valid
            ImageBRunning = ((fwStatus >> 4) & 0x01) # bit 4 - image B is running
            ImageBCommitted = ((fwStatus >> 5) & 0x01)  # bit 5 - image B is committed
            ImageBValid = ((fwStatus >> 6) & 0x01) # bit 6 - image B is valid

            if ImageAValid == 0:
                # Registers 9Fh:138,139; 140,141
                ImageA = '%d.%d.%d' %(rpl[2], rpl[3], ((rpl[4]<< 8) | rpl[5]))
            else:
                ImageA = "N/A"
            txt += 'Image A Version: %s\n' %ImageA

            ImageB = "N/A"
            txt += 'Image B Version: %s\n' %ImageB

            if rpllen > 77:
                factory_image = '%d.%d.%d' % (rpl[74], rpl[75], ((rpl[76] << 8) | rpl[77]))
                txt += 'Factory Image Version: %s\n' %factory_image

            ActiveFirmware = 'N/A'
            InactiveFirmware = 'N/A'
            if ImageARunning == 1:
                RunningImage = 'A'
                ActiveFirmware = ImageA
                # In case of single bank module, inactive firmware version can be read from EEPROM
                InactiveFirmware = self.get_module_inactive_firmware() + ".0"
            else:
                RunningImage = 'N/A'
            if ImageACommitted == 1:
                CommittedImage = 'A'
            else:
                CommittedImage = 'N/A'
            txt += 'Running Image: %s\n' % (RunningImage)
            txt += 'Committed Image: %s\n' % (CommittedImage)
            txt += 'Active Firmware: {}\n'.format(ActiveFirmware)
            txt += 'Inactive Firmware: {}\n'.format(InactiveFirmware)
        else:
            txt += 'Reply payload check code error\n'
            return {'status': False, 'info': txt, 'result': None}
        return {'status': True, 'info': txt, 'result': (ImageA, ImageARunning, ImageACommitted, ImageAValid, ImageB, ImageBRunning, ImageBCommitted, ImageBValid, ActiveFirmware, InactiveFirmware)}
