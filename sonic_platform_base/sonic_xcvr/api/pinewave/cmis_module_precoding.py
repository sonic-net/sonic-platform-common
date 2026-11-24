"""
    cmis_module_precoding.py

    API for Pinewave CMIS modules with module-wide TP1/TP4 precoding control
    in lower memory byte 29 (Custom in CMIS).
"""

import logging

from ..public.cmis import CmisApi
from ...fields import consts
from ...fields import pinewave_consts as pw

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

_BIT_MAP = {
    consts.MODULE_PRECODING_TP1: 3,
    consts.MODULE_PRECODING_TP4: 2,
}


class PinewaveCmisApi(CmisApi):
    def is_module_precoding_supported(self):
        '''
        This function returns True: modules selected for this API support the
        module-wide TP1/TP4 precoding control in byte 29
        '''
        return True

    def get_module_precoding(self):
        '''
        This function returns the module TP1/TP4 precoding settings as
        {'TP1': bool, 'TP4': bool}, or None if unreadable
        '''
        val = self.xcvr_eeprom.read(pw.MODULE_PRECODING_CONTROL)
        if val is None:
            return None
        return {key: bool(val & (1 << bit)) for key, bit in _BIT_MAP.items()}

    def set_module_precoding(self, precoding_dict):
        '''
        Sets the module-wide TP1/TP4 precoding controls. Only the requested
        controls are changed, and the value is read back after the write.

        Args:
            precoding_dict: dict with optional keys 'TP1' and/or 'TP4', each
                            set to True/1 (ON) or False/0 (OFF)

        Returns:
            True if successful or nothing to change, False otherwise
        '''
        if not isinstance(precoding_dict, dict):
            logger.error('Invalid module precoding settings: %r', precoding_dict)
            return False
        for key, enable in precoding_dict.items():
            if key not in _BIT_MAP or not isinstance(enable, (bool, int)) or enable not in (0, 1):
                logger.error('Invalid module precoding setting %r: %r', key, enable)
                return False
        if not precoding_dict:
            return True

        val = self.xcvr_eeprom.read(pw.MODULE_PRECODING_CONTROL)
        if val is None:
            return False
        new_val = val
        for key, enable in precoding_dict.items():
            mask = 1 << _BIT_MAP[key]
            new_val = (new_val | mask) if enable else (new_val & ~mask)
        if new_val == val:
            return True
        if not self.xcvr_eeprom.write(pw.MODULE_PRECODING_CONTROL, new_val):
            return False
        readback = self.xcvr_eeprom.read(pw.MODULE_PRECODING_CONTROL)
        if readback != new_val:
            logger.error('Module precoding read back %r after writing %r', readback, new_val)
            return False
        return True
