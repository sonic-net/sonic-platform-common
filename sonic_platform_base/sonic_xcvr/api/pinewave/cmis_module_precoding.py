"""
    cmis_module_precoding.py

    API for Pinewave CMIS modules with module-wide TP1/TP4 precoding control
"""

import logging

from ..public.cmis import CmisApi
from ...fields import pinewave_consts as pw

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

_BIT_MAP = {
    pw.MODULE_PRECODING_TP1: 3,
    pw.MODULE_PRECODING_TP4: 2,
}


class PinewaveCmisApi(CmisApi):
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
        bits are changed.

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
            if key not in _BIT_MAP or isinstance(enable, str) or enable not in (0, 1):
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
        return self.xcvr_eeprom.write(pw.MODULE_PRECODING_CONTROL, new_val)

    def stage_custom_si_settings(self, host_lanes_mask, optics_si_dict):
        if not super().stage_custom_si_settings(host_lanes_mask, optics_si_dict):
            return False
        if pw.MODULE_PRECODING in optics_si_dict:
            return self.set_module_precoding(optics_si_dict[pw.MODULE_PRECODING])
        return True
