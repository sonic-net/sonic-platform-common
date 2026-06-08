"""
    cpo_optoe_base.py

    Platform-independent class with which to interact with a cpo module
    in SONiC
"""
import abc
import os
import json
from .sfp_optoe_base import SfpOptoeBase
from sonic_py_common.device_info import  get_platform,  get_path_to_platform_dir

CPO_JSON_FILE = "cpo.json"
def get_cpo_json_data():
    """
    Retrieve the data from cpo.json file

    Returns:
        A dictionary containing the key/value pairs as found in the cpo.json file
    """
    platform = get_platform()
    if not platform:
        return None

    platform_path = get_path_to_platform_dir()
    if not platform_path:
        return None

    platform_json = os.path.join(platform_path, CPO_JSON_FILE)
    if not os.path.isfile(platform_json):
        return None

    try:
        with open(platform_json, 'r') as f:
            cpo_data = json.loads(f.read())
            return cpo_data
    except (json.JSONDecodeError, IOError, TypeError, ValueError):
        return None
        
class CpoOptoeBase(SfpOptoeBase):
    def __init__(self):
        super().__init__()
        self._port_id = -1
        self._oe_bank_id = -1
        self._oe_id = -1
        self._els_id = -1
        self._els_bank_id = -1

    def get_oe_eeprom_path(self):
        oes_cfg = self.get_oes_config() or {}
        cpo_bus = oes_cfg.get("oe_cmis_path")
        return (cpo_bus + "eeprom") if cpo_bus else None

    def get_eeprom_path(self):
        return self.get_oe_eeprom_path()

    def get_oes_config(self):
        key = f"oe{self._oe_id}"
        cpo_data = get_cpo_json_data() or {}
        return (cpo_data.get("oes") or {}).get(key)

    def get_elss_config(self):
        key = f"els{self._els_id}"
        cpo_data = get_cpo_json_data() or {}
        return (cpo_data.get("elss") or {}).get(key)

    def read_eeprom(self, offset, num_bytes):
        sys_path = self.get_eeprom_path()
        if not sys_path:
            return None
        try:
            with open(sys_path, mode='rb', buffering=0) as f:
                f.seek(offset)
                return bytearray(f.read(num_bytes))
        except (OSError, IOError, TypeError):
            return None

    def write_eeprom(self, offset, num_bytes, write_buffer):
        sys_path = self.get_eeprom_path()
        if not sys_path:
            return False
        try:
            with open(sys_path, mode='r+b', buffering=0) as f:
                f.seek(offset)
                f.write(write_buffer[0:num_bytes])
        except (OSError, IOError, TypeError):
            return False
        return True

    def get_els_presence(self):
        try:
            elss_cfg = self.get_elss_config() or {}
            els_presence = elss_cfg.get("els_presence") or {}

            els_presence_file = els_presence.get("presence_file")
            presence_offset = int(els_presence.get("presence_offset", "0"), 16)
            presence_len = int(els_presence.get("presence_len", 0))
            presence_bit = int(els_presence.get("presence_bit", 0))
            presence_value = int(els_presence.get("presence_value", 1))

            if not els_presence_file or presence_len <= 0:
                return False

            with open(els_presence_file, mode='rb', buffering=0) as f:
                f.seek(presence_offset)
                raw = bytearray(f.read(presence_len))
                int_value = int.from_bytes(raw, byteorder='little')
                return ((int_value >> presence_bit) & 1) == presence_value
        except (OSError, IOError, TypeError, ValueError, AttributeError):
            return False
        
    def get_presence(self):
        return self.get_els_presence()

    def get_els_base_page(self):
        elss_cfg = self.get_elss_config() or {}
        return int(elss_cfg.get("base_page", 0))

    def get_oe_bank_id(self):
        return self._oe_bank_id
    def get_oe_id(self):
        return self._oe_id
    def get_els_bank_id(self):
        return self._els_bank_id
    def get_els_id(self):
        return self._els_id

    @abc.abstractmethod
    def check_fiber_dirty(self):
        """
        Check whether the fiber is dirty. True:check ok; False: check failed
        """
        raise NotImplementedError

    @abc.abstractmethod
    def check_calibration(self):
        """
        Check whether the calibration such as oe power sufficient. True:check ok; False: check failed
        """
        raise NotImplementedError
    
    @abc.abstractmethod
    def is_els_power_sufficient(self):
        """
        Check whether els power sufficient.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_calibration_checked(self):
        """
        Check whether the calibration such as oe power sufficient detection​ has been completed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_fiber_checked(self):
        """
        Check whether the fiber detection​ has been completed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_els_tx_on(self):
        """
        Check the ELS TX​ status to see if it is emitting light normally.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def is_els_tx_enabled(self):
        """
        Check whether the ELS TX enable​ has been set.
        """
        raise NotImplementedError

