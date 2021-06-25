"""
    sfp_optoe_base.py

    Platform-independent class with which to interact with a SFP module
    in SONiC
"""

from ..sfp_base import SfpBase

class SfpOptoeBase(SfpBase):
    def __init__(self):
        SfpBase.__init__(self)

    def get_model(self):
        return self.xcvr_api.get_model()

    def get_serial(self):
        return self.xcvr_api.get_serial()

    def get_transceiver_info(self):
        return self.xcvr_api.get_transceiver_info()

    def get_transceiver_bulk_status(self):
        return self.xcvr_api.get_transceiver_bulk_status()

    def get_transceiver_threshold_info(self):
        return self.xcvr_api.get_transceiver_threshold_info()

    def get_rx_los(self):
        return self.xcvr_api.get_rx_los()

    def get_tx_fault(self):
        return self.xcvr_api.get_tx_fault()

    def get_tx_disable(self):
        return self.xcvr_api.get_tx_disable()

    def get_tx_disable_channel(self):
        return self.xcvr_api.get_tx_disable_channel()

    def get_temperature(self):
        return self.xcvr_api.get_temperature()

    def get_voltage(self):
        return self.xcvr_api.get_voltage()

    def get_tx_bias(self):
        return self.xcvr_api.get_tx_bias()

    def get_rx_power(self):
        return self.xcvr_api.get_rx_power()

    def get_tx_power(self):
        return self.xcvr_api.get_tx_power()

    def tx_disable(self, tx_disable):
        return self.xcvr_api.tx_disable(tx_disable)

    def tx_disable_channel(self, channel, disable):
        return self.xcvr_api.tx_disable_channel(channel, disable)

    def get_power_override(self):
        return self.xcvr_api.get_power_override()

    def set_power_override(self, power_override, power_set):
        return self.xcvr_api.set_power_override(power_override, power_set)

    def get_eeprom_path(self):
        raise NotImplementedError

    def read_eeprom(self, offset, num_bytes):
        try:
            with open(self.get_eeprom_path(), mode='rb', buffering=0) as f:
                f.seek(offset)
                return bytearray(f.read(num_bytes))
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
