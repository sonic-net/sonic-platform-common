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
        api = self.get_xcvr_api()
        return api.get_model() if api is not None else None

    def get_serial(self):
        api = self.get_xcvr_api()
        return api.get_serial() if api is not None else None

    def get_transceiver_info(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_info() if api is not None else None

    def get_transceiver_bulk_status(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_bulk_status() if api is not None else None

    def get_transceiver_threshold_info(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_threshold_info() if api is not None else None

    def get_rx_los(self):
        api = self.get_xcvr_api()
        if api is not None:
            rx_los = api.get_rx_los()
            # TODO Current expected behaviour is to return list of Boolean but
            # xcvr_api can return list of N/A. Return list of Boolean here for now.
            if isinstance(rx_los, list) and "N/A" in rx_los:
                return [False for _ in rx_los]
            return rx_los
        return None

    def get_tx_fault(self):
        api = self.get_xcvr_api()
        if api is not None:
            tx_fault = api.get_tx_fault()
            # TODO Current expected behaviour is to return list of Boolean but
            # xcvr_api can return list of N/A. Return list of Boolean here for now.
            if isinstance(tx_fault, list) and "N/A" in tx_fault:
                return [False for _ in tx_fault]
            return tx_fault
        return None

    def get_tx_disable(self):
        api = self.get_xcvr_api()
        return api.get_tx_disable() if api is not None else None

    def get_tx_disable_channel(self):
        api = self.get_xcvr_api()
        return api.get_tx_disable_channel() if api is not None else None

    def get_temperature(self):
        api = self.get_xcvr_api()
        if api is not None:
            temp = api.get_module_temperature()
            # TODO Current expected behaviour is to only return float but
            # xcvr_api can return N/A. Return float here for now.
            if temp == "N/A":
                return 0.0
            return temp
        return None

    def get_voltage(self):
        api = self.get_xcvr_api()
        if api is not None:
            voltage = api.get_voltage()
            # TODO Current expected behaviour is to only return float but
            # xcvr_api can return N/A. Return float here for now.
            if voltage == "N/A":
                return 0.0
            return voltage
        return None

    def get_tx_bias(self):
        api = self.get_xcvr_api()
        if api is not None:
            tx_bias = api.get_tx_bias()
            # TODO Current expected behaviour is to return list of float but
            # xcvr_api can return list of N/A. Return list of float here for now.
            if isinstance(tx_bias, list) and "N/A" in tx_bias:
                return [0.0 for _ in tx_bias]
            return tx_bias
        return None

    def get_rx_power(self):
        api = self.get_xcvr_api()
        if api is not None:
            rx_power = api.get_rx_power()
            # TODO Current expected behaviour is to return list of float but
            # xcvr_api can return list of N/A. Return list of float here for now.
            if isinstance(rx_power, list) and "N/A" in rx_power:
                return [0.0 for _ in rx_power]
            return rx_power
        return None

    def get_tx_power(self):
        api = self.get_xcvr_api()
        return api.get_tx_power() if api is not None else None

    def tx_disable(self, tx_disable):
        api = self.get_xcvr_api()
        return api.tx_disable(tx_disable) if api is not None else None

    def tx_disable_channel(self, channel, disable):
        api = self.get_xcvr_api()
        return api.tx_disable_channel(channel, disable) if api is not None else None

    def get_power_override(self):
        api = self.get_xcvr_api()
        return api.get_power_override() if api is not None else None

    def set_power_override(self, power_override, power_set):
        api = self.get_xcvr_api()
        return api.set_power_override(power_override, power_set) if api is not None else None

    def get_eeprom_path(self):
        raise NotImplementedError

    def get_lpmode(self):
        api = self.get_xcvr_api()
        return api.get_lpmode() if api is not None else None

    def set_lpmode(self, lpmode):
        api = self.get_xcvr_api()
        return api.set_lp_mode(lpmode) if api is not None else None

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
