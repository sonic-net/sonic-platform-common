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
        cpo_bus = self.get_oes_config().get("oe_cmis_path", None)
        return cpo_bus + "eeprom" if cpo_bus is not None else None

    def get_oes_config(self):
        key = f"oe{self._oe_id}"
        config = get_cpo_json_data().get("oes", None)
        return config.get(key)

    def get_elss_config(self):
        key = f"els{self._els_id}"
        config = get_cpo_json_data().get("elss", None)
        return config.get(key)

    def read_eeprom(self, offset, num_bytes):
        try:
            with open(self.get_eeprom_path(), mode='rb', buffering=0) as f:
                f.seek(offset)
                ret = bytearray(f.read(num_bytes))
                return ret
        except (OSError, IOError):
            return None

    def write_eeprom(self, offset, num_bytes, write_buffer):
        try:
            with open(self.get_eeprom_path(), mode='r+b', buffering=0) as f:
                f.seek(offset)
                f.write(write_buffer[0:num_bytes])
        except (OSError, IOError):
            return False
        return True

    def get_els_presence(self):
        try:
            els_presence = self.get_elss_config().get("els_presence", None)
            els_presence_file = els_presence.get("presence_file", None)
            presence_offset = int(els_presence.get("presence_offset", None), 16)
            presence_len = int(els_presence.get("presence_len", None))
            presence_bit = int(els_presence.get("presence_bit", None))
            presence_value = int(els_presence.get("presence_value", None))
            with open(els_presence_file, mode='rb', buffering=0) as f:
                f.seek(presence_offset)
                byte_value = f.read(presence_len)
                raw = bytearray(byte_value)
                int_value = int.from_bytes(raw, byteorder='little')
                is_bit_presence = ((int_value >> presence_bit) & 1) == presence_value
                return is_bit_presence
        except (OSError, IOError):
            return False
        
    def get_presence(self):
        return self.get_els_presence()

    def get_els_base_page(self):
        return int(self.get_elss_config().get("base_page", 0))

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
