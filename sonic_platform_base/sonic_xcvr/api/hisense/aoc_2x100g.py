"""
    aoc_2x100g.py

    Firmware management for modules that use single-bank firmware architecture.
"""
from ..public.cmis import CmisApi

class CmisAocSingleBankApi(CmisApi):
    def get_module_fw_info(self):
        """
        Override for single-bank firmware modules. These modules only have one
        firmware bank (Image A), so Image B is always reported as N/A. The
        inactive firmware version is read from EEPROM instead of CDB.
        """
        result = super().get_module_fw_info()
        if not result['status'] or result['result'] is None:
            return result

        (ImageA, ImageARunning, ImageACommitted, ImageAValid,
         ImageB, ImageBRunning, ImageBCommitted, ImageBValid,
         ActiveFirmware, InactiveFirmware) = result['result']

        # Single-bank: inactive firmware from EEPROM instead of CDB
        if ImageARunning == 1 and ImageBValid != 0:
            inactive_fw = self.get_module_inactive_firmware()
            if inactive_fw is not None and inactive_fw != 'N/A':
                InactiveFirmware = '{}.0'.format(inactive_fw)

        txt = result['info']
        txt = txt.replace('Inactive Firmware: {}'.format(result['result'][9]), 'Inactive Firmware: {}'.format(InactiveFirmware))
        return {'status': True, 'info': txt, 'result': (ImageA, ImageARunning, ImageACommitted, ImageAValid, ImageB, ImageBRunning, ImageBCommitted, ImageBValid, ActiveFirmware, InactiveFirmware)}
