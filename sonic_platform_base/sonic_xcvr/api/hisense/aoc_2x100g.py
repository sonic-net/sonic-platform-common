"""
    aoc_2x100g.py

    Firmware management for modules that use single-bank firmware architecture.
"""
from ..public.cmis import CmisApi
from ...cdb.cdb_fw import CdbFwHandler
from ...codes.public.cdb import CdbCodes
from ...mem_maps.public.cdb import CdbMemMap

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
        try:
            fw_hdlr = CdbFwHandler(
                self.xcvr_eeprom.reader,
                self.xcvr_eeprom.writer,
                CdbMemMap(CdbCodes)
            )
        except Exception:
            return {'status': False, 'info': "CDB FW handler init failed", 'result': None}
        
        fw_info = fw_hdlr.get_firmware_info()
        if not fw_info:
            return {'status': False, 'info': "Failed to get firmware info", 'result': None}
        
        fw_status = fw_info.get('Cdb1FirmwareStatus', {})
        ImageARunning = int(fw_status.get('CdbBankAOperStatus', False))
        ImageACommitted = int(fw_status.get('CdbBankAAdminStatus', False))
        ImageAValid = int(fw_status.get('CdbBankAValidStatus', True))
        ImageBRunning = int(fw_status.get('CdbBankBOperStatus', False))
        ImageBCommitted = int(fw_status.get('CdbBankBAdminStatus', False))
        ImageBValid = int(fw_status.get('CdbBankBValidStatus', True))

        if ImageAValid == 0:
            ImageA = '{}.{}.{}'.format(
                fw_info.get('CdbBankAMajorVersion', 0),
                fw_info.get('CdbBankAMinorVersion', 0),
                fw_info.get('CdbBankABuildVersion', 0)
            )
        else:
            ImageA = "N/A"
        txt += 'Image A Version: {}\n'.format(ImageA)
        ImageB = "N/A"
        txt += 'Image B Version: {}\n'.format(ImageB)
        
        FactoryImage = '{}.{}.{}'.format(
            fw_info.get('CdbFactoryMajorVersion', 0),
            fw_info.get('CdbFactoryMinorVersion', 0),
            fw_info.get('CdbFactoryBuildVersion', 0)
        )
        txt += 'Factory Image Version: {}\n'.format(FactoryImage)

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

        txt += 'Running Image: {}\n'.format(RunningImage)
        txt += 'Committed Image: {}\n'.format(CommittedImage)
        txt += 'Active Firmware: {}\n'.format(ActiveFirmware)
        txt += 'Inactive Firmware: {}\n'.format(InactiveFirmware)
        return {'status': True, 'info': txt, 'result': (ImageA, ImageARunning, ImageACommitted, ImageAValid, ImageB, ImageBRunning, ImageBCommitted, ImageBValid, ActiveFirmware, InactiveFirmware)}
