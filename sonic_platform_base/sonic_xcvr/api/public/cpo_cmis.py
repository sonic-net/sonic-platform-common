"""
    cpo-cmis.py

    Implementation of XcvrApi that corresponds to CPO-CMIS
"""
from ...fields import consts
from .cmis import CmisApi, CMIS_VDM_KEY_TO_DB_PREFIX_KEY_MAP, CMIS_XCVR_INFO_DEFAULT_DICT
import time
import copy

class ElsfpCmisApi(CmisApi): 
    def __init__(self, xcvr_eeprom, cdb_fw_hdlr=None):
        super(ElsfpCmisApi, self).__init__(xcvr_eeprom)
    def elsfp_set_output_fiber_checked_flag(self):
        return NotImplementedError
    def elsfp_tx_enable(self):
        return NotImplementedError
    def elsfp_is_tx_enabled(self):
        return NotImplementedError
    def elsfp_is_tx_on(self):
        return NotImplementedError
    def elsfp_get_opt_power_monitor(self):
        return NotImplementedError
    def elsfp_get_min_optical_power(self):
        return NotImplementedError
    def elsfp_get_max_optical_power(self):
        return NotImplementedError

class CpoCmisApi(CmisApi):   # new
    def __init__(self, oe_xcvr_eeprom, els_xcvr_eeprom, cdb_fw_hdlr=None):
        super(CpoCmisApi, self).__init__(oe_xcvr_eeprom)
        self._els_api = ElsfpCmisApi(els_xcvr_eeprom, cdb_fw_hdlr) if els_xcvr_eeprom else None
    
    # The CmisApi already has functions, while the elsfp needs to modify the interface name
    def get_elsfp_manufacturer(self):
        return self._els_api.get_manufacturer() if self._els_api else None
    def get_elsfp_serial(self):
        return self._els_api.get_serial() if self._els_api else None
    def get_elsfp_transceiver_info(self):
        return self._els_api.get_transceiver_info() if self._els_api else None

    # New functions of elsfp
    def elsfp_set_output_fiber_checked_flag(self):
        return self._els_api.elsfp_set_output_fiber_checked_flag() if self._els_api else None
    def elsfp_tx_enable(self):
        return self._els_api.elsfp_tx_enable() if self._els_api else None
    def elsfp_is_tx_enabled(self):
        return self._els_api.elsfp_is_tx_enabled() if self._els_api else None
    def elsfp_is_tx_on(self):
        return self._els_api.elsfp_is_tx_on() if self._els_api else None
    def elsfp_get_opt_power_monitor(self):
        return self._els_api.elsfp_get_opt_power_monitor() if self._els_api else None
    def elsfp_get_min_optical_power(self):
        return self._els_api.elsfp_get_min_optical_power() if self._els_api else None
    def elsfp_get_max_optical_power(self):
        return self._els_api.elsfp_get_max_optical_power() if self._els_api else None