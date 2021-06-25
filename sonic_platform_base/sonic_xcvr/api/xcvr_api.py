"""
    xcvr_api.py

    Abstract base class for platform-independent APIs used to interact with
    xcvrs in SONiC
"""

class XcvrApi(object):
    def __init__(self, xcvr_eeprom):
        self.xcvr_eeprom = xcvr_eeprom

    def get_model(self):
        raise NotImplementedError

    def get_serial(self):
        raise NotImplementedError

    def get_transceiver_info(self):
        raise NotImplementedError

    def get_transceiver_bulk_status(self):
        raise NotImplementedError

    def get_transceiver_threshold_info(self):
        raise NotImplementedError

    def get_rx_los(self):
        raise NotImplementedError

    def get_tx_fault(self):
        raise NotImplementedError

    def get_tx_disable(self):
        raise NotImplementedError

    def get_tx_disable_channel(self):
        raise NotImplementedError

    def get_temperature(self):
        raise NotImplementedError

    def get_voltage(self):
        raise NotImplementedError

    def get_tx_bias(self):
        raise NotImplementedError

    def get_rx_power(self):
        raise NotImplementedError

    def get_tx_power(self):
        raise NotImplementedError

    def tx_disable(self, tx_disable):
        raise NotImplementedError

    def tx_disable_channel(self, channel, disable):
        raise NotImplementedError

    def get_power_override(self):
        raise NotImplementedError

    def set_power_override(self, power_override, power_set):
        raise NotImplementedError

    def get_coherent_optic_api(self):
        raise NotImplementedError
