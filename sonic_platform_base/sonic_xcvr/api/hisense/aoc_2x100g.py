"""
    aoc_2x100g.py

    Firmware management for modules that use single-bank firmware architecture.
"""
from ..public.cmis import CmisApi
from ...fields import cdb_consts

class CmisAocSingleBankApi(CmisApi):
    def __init__(self, xcvr_eeprom):
        super().__init__(xcvr_eeprom, init_cdb_fw_handler=True)

    def get_module_fw_info(self):
        """
        Override for single-bank firmware modules. These modules only have one firmware bank (Image A), 
        so Image B is always reported as N/A. The inactive firmware version is read from 
        EEPROM instead of CDB.

        This function returns firmware Image A and B version, running version, committed version
        and whether both firmware images are valid.
        Operational Status: 1 = running, 0 = not running
        Administrative Status: 1=committed, 0=uncommitted
        Validity Status: 1 = invalid, 0 = valid
        """
        txt = ''
        if self.cdb is None:
            return {'status': False, 'info': "CDB Not supported", 'result': None}

        fw_hdlr = self.cdb_fw_hdlr
        if fw_hdlr is None:
            return {'status': False, 'info': "CDB FW handler init failed", 'result': None}

        fw_info = fw_hdlr.get_firmware_info()
        if fw_info is False or fw_info is None:
            return {'status': False, 'info': "Failed to get firmware info", 'result': None}

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
            # Single-bank module: only Image A is present; inactive FW read from EEPROM
            InactiveFirmware = self.get_module_inactive_firmware() + ".0"
        else:
            RunningImage = 'N/A'
        if ImageACommitted == 1:
            CommittedImage = 'A'
        else:
            CommittedImage = 'N/A'

        txt += 'Running Image: {}\n'.format(RunningImage)
        txt += 'Committed Image: {}\n'.format(CommittedImage)
        txt += 'Active Firmware: {}\n'.format(ActiveFirmware)
        txt += 'Inactive Firmware: {}\n'.format(InactiveFirmware)
        return {'status': True, 'info': txt, 'result': (ImageA, ImageARunning, ImageACommitted, ImageAValid, ImageB, ImageBRunning, ImageBCommitted, ImageBValid, ActiveFirmware, InactiveFirmware)}
