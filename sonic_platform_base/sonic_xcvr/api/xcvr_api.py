"""
    xcvr_api.py

    Abstract base class for platform-independent APIs used to interact with
    xcvrs in SONiC
"""
from math import log10
class XcvrApi(object):
    def __init__(self, xcvr_eeprom):
        self.xcvr_eeprom = xcvr_eeprom

    @staticmethod
    def mw_to_dbm(mW):
        if mW == 0:
            return float("-inf")
        elif mW < 0:
            return float("NaN")
        return round(10. * log10(mW), 3)

    def get_model(self):
        """
        Retrieves the model (part number) of the xcvr

        Returns:
            A string, the model/part number of the xcvr

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_rx_disable(self):
        """
        Retrieves the rx_disable status of this xcvr.

        Returns:
            A list of boolean values, representing the RX disable status
            of each available channel. The value is True if the xcvr channel
            is RX disabled, False if not.

            E.g., for a transceiver with four channels: [False, False, True, False]

            If RX disable status is unsupported on the xcvr, each list element should be "N/A" instead.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_rx_disable_channel(self):
        """
        Retrieves the RX disabled channels in this xcvr.

        Returns:
            A hex of 4 bits (bit 0 to bit 3 as channel 0 to channel 3) to represent
            RX channels which have been disabled in this xcvr.
            As an example, a returned value of 0x5 indicates that channel 0
            and channel 2 have been disabled.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError


    def get_serial(self):
        """
        Retrieves the serial number of the xcvr

        Returns:
            A string, the serial number of the xcvr

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_transceiver_info(self):
        """
        Retrieves general info about this xcvr

        Returns:
            A dict containing the following keys/values :
        ================================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        type                       |string         |type of xcvr
        type_abbrv_name            |string         |type of SFP, abbreviated
        hardware_rev               |string         |hardware version of xcvr
        serial                     |string         |serial number of the xcvr
        manufacturer               |string         |xcvr vendor name
        model                      |string         |xcvr model name
        connector                  |string         |connector information
        encoding                   |string         |encoding information
        ext_identifier             |string         |extend identifier
        ext_rateselect_compliance  |string         |extended rateSelect compliance
        cable_length               |float          |cable length in m
        nominal_bit_rate           |int            |nominal bit rate by 100Mbs
        specification_compliance   |string         |specification compliance
        vendor_date                |string         |vendor date
        vendor_oui                 |string         |vendor OUI
        application_advertisement  |string         |supported applications advertisement
        ================================================================================

        If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_transceiver_info_firmware_versions(self):
        """
        Retrieves active and inactive firmware versions of the xcvr

        Returns:
            A dictionary containing the active and inactive firmware versions of the transceiver
            {'active_firmware' : 'A.B.C', 'inactive_firmware' : 'X.Y.Z'}
        """
        raise NotImplementedError

    def get_transceiver_dom_real_value(self):
        """
        Retrieves DOM sensor values for this transceiver

        The returned dictionary contains floating-point values corresponding to various
        DOM sensor readings, as defined in the TRANSCEIVER_DOM_SENSOR table in STATE_DB.

        Returns:
            A dict containing the following keys/values :
        ========================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        temperature                |float          |module temperature in Celsius
        voltage                    |float          |supply voltage in mV
        tx<n>bias                  |float          |TX Bias Current in mA, n is the channel number,
                                   |               |for example, tx2bias stands for tx bias of channel 2.
        rx<n>power                 |float          |received optical power in mW, n is the channel number,
                                   |               |for example, rx2power stands for rx power of channel 2.
        tx<n>power                 |float          |TX output power in mW, n is the channel number,
                                   |               |for example, tx2power stands for tx power of channel 2.
        ========================================================================

        If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_transceiver_dom_flags(self):
        """
        Retrieves the DOM flags for this xcvr

        The returned dictionary contains boolean values representing various DOM flags.
        All registers accessed by this function are latched and correspond to the
        TRANSCEIVER_DOM_FLAG table in the STATE_DB.

        Returns:
            Dictionary
        """
        raise NotImplementedError

    def get_transceiver_threshold_info(self):
        """
        Retrieves threshold info for this xcvr

        The returned dictionary contains floating-point values corresponding to various
        DOM sensor threshold readings, as defined in the TRANSCEIVER_DOM_THRESHOLD table in STATE_DB.

        Returns:
            A dict containing the following keys/values :
        ========================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        temphighalarm              |FLOAT          |High Alarm Threshold value of temperature in Celsius.
        templowalarm               |FLOAT          |Low Alarm Threshold value of temperature in Celsius.
        temphighwarning            |FLOAT          |High Warning Threshold value of temperature in Celsius.
        templowwarning             |FLOAT          |Low Warning Threshold value of temperature in Celsius.
        vcchighalarm               |FLOAT          |High Alarm Threshold value of supply voltage in mV.
        vcclowalarm                |FLOAT          |Low Alarm Threshold value of supply voltage in mV.
        vcchighwarning             |FLOAT          |High Warning Threshold value of supply voltage in mV.
        vcclowwarning              |FLOAT          |Low Warning Threshold value of supply voltage in mV.
        rxpowerhighalarm           |FLOAT          |High Alarm Threshold value of received power in dBm.
        rxpowerlowalarm            |FLOAT          |Low Alarm Threshold value of received power in dBm.
        rxpowerhighwarning         |FLOAT          |High Warning Threshold value of received power in dBm.
        rxpowerlowwarning          |FLOAT          |Low Warning Threshold value of received power in dBm.
        txpowerhighalarm           |FLOAT          |High Alarm Threshold value of transmit power in dBm.
        txpowerlowalarm            |FLOAT          |Low Alarm Threshold value of transmit power in dBm.
        txpowerhighwarning         |FLOAT          |High Warning Threshold value of transmit power in dBm.
        txpowerlowwarning          |FLOAT          |Low Warning Threshold value of transmit power in dBm.
        txbiashighalarm            |FLOAT          |High Alarm Threshold value of tx Bias Current in mA.
        txbiaslowalarm             |FLOAT          |Low Alarm Threshold value of tx Bias Current in mA.
        txbiashighwarning          |FLOAT          |High Warning Threshold value of tx Bias Current in mA.
        txbiaslowwarning           |FLOAT          |Low Warning Threshold value of tx Bias Current in mA.
        ========================================================================

        If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_transceiver_status(self):
        """
        Retrieves the current status of the transceiver module.

        Accesses non-latched registers to gather information about the module's state,
        fault causes, and datapath-level statuses, including TX and RX statuses.

        Returns:
            dict: A dictionary containing boolean values for various status fields, as defined in
                the TRANSCEIVER_STATUS table in STATE_DB.
        If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_transceiver_status_flags(self):
        """
        Retrieves the current flag status of the transceiver module.

        Accesses latched registers to gather information about both
        module-level and datapath-level states (including TX/RX related flags).

        Returns:
            dict: A dictionary containing boolean values for various flags, as defined in
                the TRANSCEIVER_STATUS_FLAGS table in STATE_DB.
        """
        raise NotImplementedError

    def is_transceiver_vdm_supported(self):
        """
        Retrieves VDM support status for this xcvr (applicable for CMIS and C-CMIS)
        """
        raise NotImplementedError

    def get_transceiver_vdm_real_value(self):
        """
        Retrieves VDM real (sample) values for this xcvr (applicable for CMIS and C-CMIS)
        Specifically, it retrieves sample data from pages 24h to 27h
        """
        raise NotImplementedError

    def get_transceiver_vdm_thresholds(self):
        """
        Retrieves VDM thresholds for this xcvr (applicable for CMIS and C-CMIS)
        """
        raise NotImplementedError

    def get_transceiver_vdm_flags(self):
        """
        Retrieves VDM flags for this xcvr (applicable for CMIS and C-CMIS)
        """
        raise NotImplementedError

    def get_transceiver_pm(self):
        """
        Retrieves PM (Performance Monitoring) info for this xcvr (applicable for C-CMIS)

        Returns:
            A dict containing the following keys/values :
        ========================================================================
        key                          = TRANSCEIVER_PM|ifname            ; information of PM on port
        ; field                      = value
        prefec_ber_avg               = FLOAT                            ; prefec ber avg
        prefec_ber_min               = FLOAT                            ; prefec ber min
        prefec_ber_max               = FLOAT                            ; prefec ber max
        uncorr_frames_avg            = FLOAT                            ; uncorrected frames ratio avg
        uncorr_frames_min            = FLOAT                            ; uncorrected frames ratio min
        uncorr_frames_max            = FLOAT                            ; uncorrected frames ratio max
        cd_avg                       = FLOAT                            ; chromatic dispersion avg
        cd_min                       = FLOAT                            ; chromatic dispersion min
        cd_max                       = FLOAT                            ; chromatic dispersion max
        dgd_avg                      = FLOAT                            ; differential group delay avg
        dgd_min                      = FLOAT                            ; differential group delay min
        dgd_max                      = FLOAT                            ; differential group delay max
        sopmd_avg                    = FLOAT                            ; second order polarization mode dispersion avg
        sopmd_min                    = FLOAT                            ; second order polarization mode dispersion min
        sopmd_max                    = FLOAT                            ; second order polarization mode dispersion max
        pdl_avg                      = FLOAT                            ; polarization dependent loss avg
        pdl_min                      = FLOAT                            ; polarization dependent loss min
        pdl_max                      = FLOAT                            ; polarization dependent loss max
        osnr_avg                     = FLOAT                            ; optical signal to noise ratio avg
        osnr_min                     = FLOAT                            ; optical signal to noise ratio min
        osnr_max                     = FLOAT                            ; optical signal to noise ratio max
        esnr_avg                     = FLOAT                            ; electrical signal to noise ratio avg
        esnr_min                     = FLOAT                            ; electrical signal to noise ratio min
        esnr_max                     = FLOAT                            ; electrical signal to noise ratio max
        cfo_avg                      = FLOAT                            ; carrier frequency offset avg
        cfo_min                      = FLOAT                            ; carrier frequency offset min
        cfo_max                      = FLOAT                            ; carrier frequency offset max
        soproc_avg                   = FLOAT                            ; state of polarization rate of change avg
        soproc_min                   = FLOAT                            ; state of polarization rate of change min
        soproc_max                   = FLOAT                            ; state of polarization rate of change max
        tx_power_avg                 = FLOAT                            ; tx output power avg
        tx_power_min                 = FLOAT                            ; tx output power min
        tx_power_max                 = FLOAT                            ; tx output power max
        rx_tot_power_avg             = FLOAT                            ; rx total power avg
        rx_tot_power_min             = FLOAT                            ; rx total power min
        rx_tot_power_max             = FLOAT                            ; rx total power max
        rx_sig_power_avg             = FLOAT                            ; rx signal power avg
        rx_sig_power_min             = FLOAT                            ; rx signal power min
        rx_sig_power_max             = FLOAT                            ; rx signal power max

        If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_rx_los(self):
        """
        Retrieves the RX LOS (loss-of-signal) status of this xcvr

        Returns:
            A list of boolean values, representing the RX LOS status
            of each available channel, value is True if xcvr channel
            has RX LOS, False if not.
            E.g., for a tranceiver with four channels: [False, False, True, False]

            If Rx LOS status is unsupported on the xcvr, each list element should be "N/A" instead.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_tx_fault(self):
        """
        Retrieves the TX fault status of this xcvr

        Returns:
            A list of boolean values, representing the TX fault status
            of each available channel, value is True if xcvr channel
            has TX fault, False if not.
            E.g., for a tranceiver with four channels: [False, False, True, False]

            If TX fault status is unsupported on the xcvr, each list element should be "N/A" instead.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_tx_disable(self):
        """
        Retrieves the tx_disable status of this xcvr

        Returns:
            A list of boolean values, representing the TX disable status
            of each available channel, value is True if xcvr channel
            is TX disabled, False if not.
            E.g., for a tranceiver with four channels: [False, False, True, False]

            If TX disable status is unsupported on the xcvr, each list element should be "N/A" instead.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_tx_disable_channel(self):
        """
        Retrieves the TX disabled channels in this xcvr

        Returns:
            A hex of 4 bits (bit 0 to bit 3 as channel 0 to channel 3) to represent
            TX channels which have been disabled in this xcvr.
            As an example, a returned value of 0x5 indicates that channel 0
            and channel 2 have been disabled.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def rx_disable(self, rx_disable):
        """
        Disable xcvr RX for all channels

        Args:
            rx_disable : A Boolean, True to enable rx_disable mode, False to disable
                         rx_disable mode.

        Returns:
            A boolean, True if rx_disable is set successfully, False if not
        """
        raise NotImplementedError

    def rx_disable_channel(self, channel, disable):
        """
        Sets the rx_disable for specified xcvr channels

        Args:
            channel : A hex of 4 bits (bit 0 to bit 3) which represent channel 0 to 3,
                      e.g. 0x5 for channel 0 and channel 2.
            disable : A boolean, True to disable RX channels specified in channel,
                      False to enable

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError

    def get_module_temperature(self):
        """
        Retrieves the temperature of this xcvr

        Returns:
            A float representing the current temperature in Celsius, or "N/A" if temperature
            measurements are unsupported on the xcvr.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_voltage(self):
        """
        Retrieves the supply voltage of this xcvr

        Returns:
            A float representing the supply voltage in mV, or "N/A" if voltage measurements are
            unsupported on the xcvr.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_tx_bias(self):
        """
        Retrieves the TX bias current of all xcvr channels

        Returns:
            A list of floats, representing TX bias in mA
            for each available channel
            E.g., for a tranceiver with four channels: ['110.09', '111.12', '108.21', '112.09']

            If TX bias is unsupported on the xcvr, each list element should be "N/A" instead.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_rx_power(self):
        """
        Retrieves the received optical power of all xcvr channels

        Returns:
            A list of floats, representing received optical
            power in mW for each available channel
            E.g., for a tranceiver with four channels: ['1.77', '1.71', '1.68', '1.70']

            If RX power is unsupported on the xcvr, each list element should be "N/A" instead.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_tx_power(self):
        """
        Retrieves the TX power of all xcvr channels

        Returns:
            A list of floats, representing TX power in mW
            for each available channel
            E.g., for a tranceiver with four channels: ['1.86', '1.86', '1.86', '1.86']

            If TX power is unsupported on the xcvr, each list element should be "N/A" instead.

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def tx_disable(self, tx_disable):
        """
        Disable xcvr TX for all channels

        Args:
            tx_disable : A Boolean, True to enable tx_disable mode, False to disable
                         tx_disable mode.

        Returns:
            A boolean, True if tx_disable is set successfully, False if not
        """
        raise NotImplementedError

    def tx_disable_channel(self, channel, disable):
        """
        Sets the tx_disable for specified xcvr channels

        Args:
            channel : A hex of 4 bits (bit 0 to bit 3) which represent channel 0 to 3,
                      e.g. 0x5 for channel 0 and channel 2.
            disable : A boolean, True to disable TX channels specified in channel,
                      False to enable

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError

    def get_power_override(self):
        """
        Retrieves the power-override status of this xcvr

        Returns:
            A boolean, True if power-override is enabled, False if disabled

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def set_power_override(self, power_override, power_set):
        """
        Sets xcvr power level using power_override and power_set

        Args:
            power_override :
                    A Boolean, True to override set_lpmode and use power_set
                    to control xcvr power, False to disable xcvr power control
                    through power_override/power_set and use set_lpmode
                    to control xcvr power.
            power_set :
                    Only valid when power_override is True.
                    A Boolean, True to set xcvr to low power mode, False to set
                    xcvr to high power mode.

        Returns:
            A boolean, True if power-override and power_set are set successfully,
            False if not
        """
        raise NotImplementedError

    def is_flat_memory(self):
        """
        Determines whether the xcvr's memory map is flat or paged

        Returns:
            A Boolean, True if flat memory, False if paging is implemented

            If there is an issue with reading the xcvr, True should be returned.
        """
        raise NotImplementedError

    def get_tx_power_support(self):
        """
        Retrieves the tx power measurement capability of this xcvr

        Returns:
            A Boolean, True if tx power measurement is supported, False otherwise

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_rx_power_support(self):
        """
        Retrieves the tx power measurement capability of this xcvr

        Returns:
            A Boolean, True if tx power measurement is supported, False otherwise
        """
        raise NotImplementedError

    def is_copper(self):
        """
        Returns:
            A Boolean, True if xcvr is copper, False if optical

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_temperature_support(self):
        """
        Retrieves the temperature measurement capability of this xcvr

        Returns:
            A Boolean, True if module temperature is supported, False otherwise

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_voltage_support(self):
        """
        Retrieves the temperature measurement capability of this xcvr

        Returns:
            A Boolean, True if module voltage measurement is supported, False otherwise

            If there is an issue with reading the xcvr, None should be returned.
        """
        raise NotImplementedError

    def get_rx_los_support(self):
        """
        Retrieves the RX LOS status reporting capability of this xcvr

        Returns:
            A Boolean, True if xcvr reports RX LOS status, False otherwise
        """
        raise NotImplementedError

    def get_tx_bias_support(self):
        """
        Retrieves the TX bias measurement capability of this xcvr

        Returns:
            A Boolean, True if TX bias is supported, False otherwise
        """
        raise NotImplementedError

    def get_tx_fault_support(self):
        """
        Retrieves the TX fault status reporting capability of this xcvr

        Returns:
            A Boolean, True if xcvr reports TX fault, False otherwise
        """
        raise NotImplementedError

    def get_tx_disable_support(self):
        """
        Retrieves the TX disable capability of this xcvr

        Returns:
            A Boolean, True if Tx can be disabled, False otherwise
        """
        raise NotImplementedError

    def get_transceiver_thresholds_support(self):
        """
        Retrieves the thresholds reporting capability by this xcvr

        Returns:
            A Boolean, True if thresholds are supported, False otherwise
        """
        raise NotImplementedError

    def get_lpmode_support(self):
        """
        Retrieves the lpmode support of this xcvr

        Returns:
            A Boolean, True if lpmode is supported, False otherwise
        """
        raise NotImplementedError

    def get_power_override_support(self):
        """
        Retrieves the power override support of this xcvr

        Returns:
            A Boolean, True if power override is supported, False otherwise
        """
        raise NotImplementedError

    def get_module_fw_info(self):
        """
        Retrieves the firmware information of this xcvr.

        Returns:
            A dict containing the following keys/values:
        ================================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        status                     |bool           |status of operation
        info                       |string         |human readable representation of firmware information
        result                     |tuple          |firmware information
        """
        raise NotImplementedError

    def get_error_description(self):
        """
        Retrives the error descriptions of the SFP module

        Returns:
            String that represents the current error descriptions of vendor specific errors
            In case there are multiple errors, they should be joined by '|',
            like: "Bad EEPROM|Unsupported cable"
        """
        raise NotImplementedError

    def get_power_class(self):
        """
        Retrieves the power class of the module

        Returns:
            int: Power class of the module, None if it fails
        """
        raise NotImplementedError

    def set_high_power_class(self, power_class, enable):
        """
        This function sets high power class for the module.

        Args:
            power_class (int): Power class to enable/disable
            enable (bool): True to enable high power class, False to disable

        Returns:
            bool: True if the provision succeeds, False if it fails
        """
        raise NotImplementedError

    def is_lpo(self):
        """
        Check if the module is Linear Pluggable Optics (LPO)

        Returns:
            A Boolean, True if the module is LPO, False otherwise
        """
        raise NotImplementedError
