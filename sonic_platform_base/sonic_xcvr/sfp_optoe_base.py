"""
    sfp_optoe_base.py

    Platform-independent class with which to interact with a SFP module
    in SONiC
"""

from ..sfp_base import SfpBase

SFP_OPTOE_PAGE_SELECT_OFFSET = 127
SFP_OPTOE_UPPER_PAGE0_OFFSET = 128
SFP_OPTOE_PAGE_SIZE = 128

CMIS_MODULE_IDS = (0x18, 0x19, 0x1b, 0x1e)
# Lower-memory byte 2 bit 7: 1 = flat memory (lower + upper page 00h only), 0 = paged.
CMIS_FLAT_MEM_FILE_OFFSET = 2
CMIS_FLAT_MEM_BIT_MASK = 0x80
# Page 01h byte 142 in the optoe linear EEPROM file at bank-0 stride.
CMIS_BANKS_SUPPORTED_FILE_OFFSET = 270
# CMIS AdvBnkSupport (page 01h byte 142, bits 0-1): 00b->1, 01b->2, 10b->4 banks.
CMIS_BANKS_SUPPORTED_TO_MAX_BANK_SIZE = {0: 0, 1: 2, 2: 4}

class SfpOptoeBase(SfpBase):
    def __init__(self, bank=0):
        SfpBase.__init__(self, bank=bank)

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

    def get_transceiver_dom_real_value(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_dom_real_value() if api is not None else None

    def get_transceiver_dom_flags(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_dom_flags() if api is not None else None

    def get_transceiver_threshold_info(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_threshold_info() if api is not None else None

    def get_transceiver_status(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_status() if api is not None else None

    def get_transceiver_status_flags(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_status_flags() if api is not None else None

    def get_transceiver_loopback(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_loopback() if api is not None else None

    def is_coherent_module(self):
        api = self.get_xcvr_api()
        return api.is_coherent_module() if api is not None else None

    def is_transceiver_vdm_supported(self):
        api = self.get_xcvr_api()
        return api.is_transceiver_vdm_supported() if api is not None else None

    def is_vdm_statistic_supported(self):
        """
        Returns whether the optic advertises any VDM statistic observable types
        """
        api = self.get_xcvr_api()
        return api.is_vdm_statistic_supported() if api is not None else None

    def get_transceiver_vdm_real_value(self):
        """
        Retrieves all VDM real (sample) values for this xcvr (applicable for CMIS and C-CMIS)
        Specifically, it retrieves sample data from pages 24h to 27h
        """
        api = self.get_xcvr_api()
        return api.get_transceiver_vdm_real_value() if api is not None else None

    def get_transceiver_vdm_real_value_basic(self):
        """
        Retrieves basic (instantaneous) VDM real values for this xcvr
        """
        api = self.get_xcvr_api()
        return api.get_transceiver_vdm_real_value_basic() if api is not None else None

    def get_transceiver_vdm_real_value_statistic(self):
        """
        Retrieves statistic (min/max/avg) VDM real values for this xcvr
        """
        api = self.get_xcvr_api()
        return api.get_transceiver_vdm_real_value_statistic() if api is not None else None

    def get_transceiver_vdm_thresholds(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_vdm_thresholds() if api is not None else None

    def get_transceiver_vdm_flags(self):
        api = self.get_xcvr_api()
        return api.get_transceiver_vdm_flags() if api is not None else None

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

    def get_rx_disable(self):
        api = self.get_xcvr_api()
        return api.get_rx_disable() if api is not None else None

    def get_rx_disable_channel(self):
        api = self.get_xcvr_api()
        return api.get_rx_disable_channel() if api is not None else None

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

    def rx_disable(self, rx_disable):
        api = self.get_xcvr_api()
        return api.rx_disable(rx_disable) if api is not None else None

    def rx_disable_channel(self, channel, disable):
        api = self.get_xcvr_api()
        return api.rx_disable_channel(channel, disable) if api is not None else None


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

    def set_optoe_max_bank_size(self, max_bank_size):
        """Write max_bank_size to the optoe sysfs entry. Reads the current value first and skips the write if it already matches, since the driver tears down and recreates the eeprom bin file on every write regardless of whether the value changed. Exceptions propagate: a failure here means banked EEPROM offsets won't be accessible, and a loud failure now is preferable to a confusing read-past-EOF later."""
        sys_path = self.get_eeprom_path().replace("eeprom", "max_bank_size")
        with open(sys_path) as f:
            if int(f.read().strip()) == max_bank_size:
                return
        with open(sys_path, mode='w') as f:
            f.write(str(max_bank_size))

    def _read_optoe_max_bank_size(self):
        """Determine optoe max_bank_size from the module's CMIS BanksSupported advertisement, or None if non-CMIS, flat-memory, or unreadable."""
        id_byte = self.read_eeprom(0, 1)
        if id_byte is None or id_byte[0] not in CMIS_MODULE_IDS:
            return None
        flat_mem = self.read_eeprom(CMIS_FLAT_MEM_FILE_OFFSET, 1)
        if flat_mem is None or flat_mem[0] & CMIS_FLAT_MEM_BIT_MASK:
            return None
        raw = self.read_eeprom(CMIS_BANKS_SUPPORTED_FILE_OFFSET, 1)
        if raw is None:
            return None
        return CMIS_BANKS_SUPPORTED_TO_MAX_BANK_SIZE.get(raw[0] & 0x03)

    def refresh_xcvr_api(self):
        """Sync optoe max_bank_size to the module's BanksSupported before building the XcvrApi, so subsequent banked reads don't land past EOF. Only runs when self.bank is non-zero so we don't enable banking based on a module that may erroneously advertise it."""
        if self.bank != 0:
            max_bank_size = self._read_optoe_max_bank_size()
            if max_bank_size is not None:
                self.set_optoe_max_bank_size(max_bank_size)
        super().refresh_xcvr_api()

    def get_optoe_current_page(self):
        return self.read_eeprom(SFP_OPTOE_PAGE_SELECT_OFFSET, 1)[0]

    def set_page0(self):
        self.write_eeprom(SFP_OPTOE_PAGE_SELECT_OFFSET, 1, bytearray([0x00]))

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
                if offset >= SFP_OPTOE_UPPER_PAGE0_OFFSET  and \
                    offset < (SFP_OPTOE_UPPER_PAGE0_OFFSET+SFP_OPTOE_PAGE_SIZE) and \
                        self.get_optoe_current_page() != 0:
                    # Restoring the page to 0 helps in cases where the optoe driver failed to restore
                    # the page when say the module was busy with CDB command processing
                   self.set_page0()
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

    def get_power_class(self):
        """
        Get the power class of the module

        Returns:
            Integer that represents the power class of the module, None if it fails
        """
        api = self.get_xcvr_api()
        return api.get_power_class() if api is not None else None

    def set_high_power_class(self, power_class, enable):
        """
        Set the high power class of the module

        Args:
            power_class: Integer that represents the power class to enable or disable
            enable: Boolean that represents whether to enable or disable the high power class

        Returns:
            Boolean, True if successful, False if not
        """
        api = self.get_xcvr_api()
        return api.set_high_power_class(power_class, enable) if api is not None else False
