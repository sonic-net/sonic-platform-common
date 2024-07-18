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

    def get_transceiver_info_firmware_versions(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_info_firmware_versions() if api is not None else None

    def get_transceiver_bulk_status(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_bulk_status() if api is not None else None

    def get_transceiver_threshold_info(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_threshold_info() if api is not None else None

    def get_transceiver_status(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_status() if api is not None else None

    def get_transceiver_loopback(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_loopback() if api is not None else None

    def is_coherent_module(self):
        api = self.get_xcvr_api()
        return api.is_coherent_module() if api is not None else None

    def get_transceiver_pm(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_pm() if api is not None else None

    def freeze_vdm_stats(self):
        '''
        This function freeze all the vdm statistics reporting registers.
        When raised by the host, causes the module to freeze and hold all 
        reported statistics reporting registers (minimum, maximum and 
        average values)in Pages 24h-27h.

        Returns True if the provision succeeds and False incase of failure.
        '''
        api = self.get_xcvr_api()
        try:
            return api.freeze_vdm_stats() if api is not None else False
        except (NotImplementedError, AttributeError):
            return False

    def unfreeze_vdm_stats(self):
        '''
        This function unfreeze all the vdm statistics reporting registers.
        When freeze is ceased by the host, releases the freeze request, allowing the 
        reported minimum, maximum and average values to update again.

        Returns True if the provision succeeds and False incase of failure.
        '''
        api = self.get_xcvr_api()
        try:
            return api.unfreeze_vdm_stats() if api is not None else False
        except (NotImplementedError, AttributeError):
            return False


    def get_vdm_freeze_status(self):
        '''
        This function reads and returns the vdm Freeze done status.

        Returns True if the vdm stats freeze is successful and False if not freeze.
        '''
        api = self.get_xcvr_api()
        try:
            return api.get_vdm_freeze_status() if api is not None else False
        except (NotImplementedError, AttributeError):
            return False

    def get_vdm_unfreeze_status(self):
        '''
        This function reads and returns the vdm unfreeze status.

        Returns True if the vdm stats unfreeze is successful and False if not unfreeze.
        '''
        api = self.get_xcvr_api()
        try:
            return api.get_vdm_unfreeze_status() if api is not None else False
        except (NotImplementedError, AttributeError):
            return False


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
        """
        This common API is applicable only for CMIS as Low Power mode can be verified
        using EEPROM registers.For other media types like QSFP28/QSFP+ etc., platform
        vendors has to implement accordingly.
        """
        api = self.get_xcvr_api()
        return api.get_lpmode() if api is not None else None

    def set_lpmode(self, lpmode):
        """
        This common API is applicable only for CMIS as Low Power mode can be controlled
        via EEPROM registers.For other media types like QSFP28/QSFP+ etc., platform
        vendors has to implement accordingly.
        """
        api = self.get_xcvr_api()
        return api.set_lpmode(lpmode) if api is not None else None

    def set_power(self, mode):
        raise NotImplementedError

    def set_optoe_write_max(self, write_max):
        sys_path = self.get_eeprom_path()
        sys_path = sys_path.replace("eeprom", "write_max")
        try:
            with open(sys_path, mode='w') as f:
                f.write(str(write_max))
        except (OSError, IOError):
            pass

    def set_optoe_write_timeout(self, write_timeout):
        sys_path = self.get_eeprom_path()
        sys_path = sys_path.replace("eeprom", "write_timeout")
        try:
            with open(sys_path, mode='w') as f:
                f.write(str(write_timeout))
        except (OSError, IOError):
            pass

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

    def reset(self):
        """
        Reset SFP and return all user module settings to their default state.

        Returns:
            A boolean, True if successful, False if not
        """
        api = self.get_xcvr_api()
        return api.reset() if api is not None else False

    def get_error_description(self):
        """
        Retrives the error descriptions of the SFP module

        Returns:
            String that represents the current error descriptions of vendor specific errors
            In case there are multiple errors, they should be joined by '|',
            like: "Bad EEPROM|Unsupported cable"
        """
        api = self.get_xcvr_api()
        return api.get_error_description() if api is not None else None
