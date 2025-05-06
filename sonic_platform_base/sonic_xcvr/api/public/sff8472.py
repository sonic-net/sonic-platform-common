"""
    sff8472.py

    Implementation of XcvrApi that corresponds to the SFF-8472 specification for
    SFP+ pluggable transceivers.
"""
from ...fields import consts
from ..xcvr_api import XcvrApi

class Sff8472Api(XcvrApi):
    NUM_CHANNELS = 1

    def __init__(self, xcvr_eeprom):
        super(Sff8472Api, self).__init__(xcvr_eeprom)

    def get_model(self):
        return self.xcvr_eeprom.read(consts.VENDOR_PART_NO_FIELD)

    def get_serial(self):
        return self.xcvr_eeprom.read(consts.VENDOR_SERIAL_NO_FIELD)

    def get_transceiver_info(self):
        serial_id = self.xcvr_eeprom.read(consts.SERIAL_ID_FIELD)
        if serial_id is None:
            return None
        smf_km_len = serial_id[consts.LENGTH_SMF_KM_FIELD]
        smf_m_len = serial_id[consts.LENGTH_SMF_M_FIELD]
        om4_len = serial_id[consts.LENGTH_OM4_FIELD]
        om3_len = serial_id[consts.LENGTH_OM3_FIELD]
        om2_len = serial_id[consts.LENGTH_OM2_FIELD]
        om1_len = serial_id[consts.LENGTH_OM1_FIELD]

        len_types = ["Length SMF (km)", "Length SMF (100m)", "Length OM2 (10m)", "Length OM1(10m)", "Length OM4(10m)", "Length OM3(10m)"]
        cable_len = 0
        cable_type = None
        for len, type in zip([smf_km_len, smf_m_len, om2_len, om1_len, om4_len, om3_len], len_types):
            if len > 0:
                cable_len = len
                cable_type = type

        xcvr_info = {
            "type": serial_id[consts.ID_FIELD],
            "type_abbrv_name": serial_id[consts.ID_ABBRV_FIELD],
            "vendor_rev": serial_id[consts.VENDOR_REV_FIELD],
            "serial": serial_id[consts.VENDOR_SERIAL_NO_FIELD],
            "manufacturer": serial_id[consts.VENDOR_NAME_FIELD],
            "model": serial_id[consts.VENDOR_PART_NO_FIELD],
            "connector": serial_id[consts.CONNECTOR_FIELD],
            "encoding": serial_id[consts.ENCODING_FIELD],
            "ext_identifier": serial_id[consts.EXT_ID_FIELD],
            "ext_rateselect_compliance": serial_id[consts.RATE_ID_FIELD],
            "cable_type": cable_type,
            "cable_length": float(cable_len),
            "nominal_bit_rate": serial_id[consts.NOMINAL_BR_FIELD],
            "specification_compliance": str(serial_id[consts.SPEC_COMPLIANCE_FIELD]),
            "vendor_date": serial_id[consts.VENDOR_DATE_FIELD],
            "vendor_oui": serial_id[consts.VENDOR_OUI_FIELD],
            "application_advertisement": "N/A",
        }

        return xcvr_info

    def get_transceiver_status(self):
        """
        Retrieves the current status of the transceiver module.

        Accesses non-latched registers to gather information about the TX statuses.

        Returns:
            dict: A dictionary containing boolean values for various status fields, as defined in
                the TRANSCEIVER_STATUS table in STATE_DB.
        """
        tx_disable = self.get_tx_disable()
        tx_disabled_channel = self.get_tx_disable_channel()
        read_failed = tx_disable is None or \
                      tx_disabled_channel is None
        if read_failed:
            return None

        trans_status = dict()
        for lane in range(1, len(tx_disable) + 1):
            trans_status['tx%ddisable' % lane] = tx_disable[lane - 1]
        trans_status['tx_disabled_channel'] = tx_disabled_channel

        return trans_status

    def get_transceiver_status_flags(self):
        """
        Retrieves the current flag status of the transceiver module.

        Accesses non-latched registers to gather TX and RX-related flags. Unlike other
        module types, SFF-8472 does not support latched registers for these flags.

        Returns:
            dict: A dictionary containing boolean values for various flags, as defined in
                the TRANSCEIVER_STATUS_FLAGS table in STATE_DB.
        """
        rx_los = self.get_rx_los()
        tx_fault = self.get_tx_fault()
        read_failed = rx_los is None or \
                      tx_fault is None
        if read_failed:
            return None

        trans_status_flags = dict()
        for lane in range(1, len(rx_los) + 1):
            trans_status_flags['rx%dlos' % lane] = rx_los[lane - 1]
        for lane in range(1, len(tx_fault) + 1):
            trans_status_flags['tx%dfault' % lane] = tx_fault[lane - 1]

        return trans_status_flags

    def get_transceiver_dom_real_value(self):
        """
        Retrieves DOM sensor values for this transceiver

        The returned dictionary contains floating-point values corresponding to various
        DOM sensor readings, as defined in the TRANSCEIVER_DOM_SENSOR table in STATE_DB.

        Returns:
            Dictionary
        """
        temp = self.get_module_temperature()
        voltage = self.get_voltage()
        tx_bias = self.get_tx_bias()
        rx_power = self.get_rx_power()
        tx_power = self.get_tx_power()
        read_failed = temp is None or \
                      voltage is None or \
                      tx_bias is None or \
                      rx_power is None or \
                      tx_power is None
        if read_failed:
            return None

        bulk_status = {
            "temperature": temp,
            "voltage": voltage
        }

        for i in range(1, self.NUM_CHANNELS + 1):
            bulk_status["tx%dbias" % i] = tx_bias[i - 1]
            bulk_status["rx%dpower" % i] = self.mw_to_dbm(rx_power[i - 1]) if rx_power[i - 1] != 'N/A' else 'N/A'
            bulk_status["tx%dpower" % i] = self.mw_to_dbm(tx_power[i - 1]) if tx_power[i - 1] != 'N/A' else 'N/A'

        # Added to avoid failing xcvrd. Ideally xcvrd should be fixed so that this is not necessary
        for i in range(2, 5):
            bulk_status["tx%dbias" % i] = 'N/A'
            bulk_status["rx%dpower" % i] = 'N/A'
            bulk_status["tx%dpower" % i] = 'N/A'

        return bulk_status

    def get_transceiver_threshold_info(self):
        """
        Retrieves threshold info for this xcvr

        The returned dictionary contains floating-point values corresponding to various
        DOM sensor threshold readings, as defined in the TRANSCEIVER_DOM_THRESHOLD table in STATE_DB.

        Returns:
            Dictionary
        """
        threshold_info_keys = ['temphighalarm',    'temphighwarning',
                               'templowalarm',     'templowwarning',
                               'vcchighalarm',     'vcchighwarning',
                               'vcclowalarm',      'vcclowwarning',
                               'rxpowerhighalarm', 'rxpowerhighwarning',
                               'rxpowerlowalarm',  'rxpowerlowwarning',
                               'txpowerhighalarm', 'txpowerhighwarning',
                               'txpowerlowalarm',  'txpowerlowwarning',
                               'txbiashighalarm',  'txbiashighwarning',
                               'txbiaslowalarm',   'txbiaslowwarning'
                              ]
        threshold_info_dict = dict.fromkeys(threshold_info_keys, 'N/A')
        thresh_support = self.get_transceiver_thresholds_support()
        if thresh_support is None:
            return None
        if not thresh_support:
            return threshold_info_dict
        thresholds = self.xcvr_eeprom.read(consts.THRESHOLDS_FIELD)
        if thresholds is None:
            return threshold_info_dict

        return {
            "temphighalarm": float("{:.3f}".format(thresholds[consts.TEMP_HIGH_ALARM_FIELD])),
            "templowalarm": float("{:.3f}".format(thresholds[consts.TEMP_LOW_ALARM_FIELD])),
            "temphighwarning": float("{:.3f}".format(thresholds[consts.TEMP_HIGH_WARNING_FIELD])),
            "templowwarning": float("{:.3f}".format(thresholds[consts.TEMP_LOW_WARNING_FIELD])),
            "vcchighalarm": float("{:.3f}".format(thresholds[consts.VOLTAGE_HIGH_ALARM_FIELD])),
            "vcclowalarm": float("{:.3f}".format(thresholds[consts.VOLTAGE_LOW_ALARM_FIELD])),
            "vcchighwarning": float("{:.3f}".format(thresholds[consts.VOLTAGE_HIGH_WARNING_FIELD])),
            "vcclowwarning": float("{:.3f}".format(thresholds[consts.VOLTAGE_LOW_WARNING_FIELD])),
            "rxpowerhighalarm": float("{:.3f}".format(self.mw_to_dbm(thresholds[consts.RX_POWER_HIGH_ALARM_FIELD]))),
            "rxpowerlowalarm": float("{:.3f}".format(self.mw_to_dbm(thresholds[consts.RX_POWER_LOW_ALARM_FIELD]))),
            "rxpowerhighwarning": float("{:.3f}".format(self.mw_to_dbm(thresholds[consts.RX_POWER_HIGH_WARNING_FIELD]))),
            "rxpowerlowwarning": float("{:.3f}".format(self.mw_to_dbm(thresholds[consts.RX_POWER_LOW_WARNING_FIELD]))),
            "txpowerhighalarm": float("{:.3f}".format(self.mw_to_dbm(thresholds[consts.TX_POWER_HIGH_ALARM_FIELD]))),
            "txpowerlowalarm": float("{:.3f}".format(self.mw_to_dbm(thresholds[consts.TX_POWER_LOW_ALARM_FIELD]))),
            "txpowerhighwarning": float("{:.3f}".format(self.mw_to_dbm(thresholds[consts.TX_POWER_HIGH_WARNING_FIELD]))),
            "txpowerlowwarning": float("{:.3f}".format(self.mw_to_dbm(thresholds[consts.TX_POWER_LOW_WARNING_FIELD]))),
            "txbiashighalarm": float("{:.3f}".format(thresholds[consts.TX_BIAS_HIGH_ALARM_FIELD])),
            "txbiaslowalarm": float("{:.3f}".format(thresholds[consts.TX_BIAS_LOW_ALARM_FIELD])),
            "txbiashighwarning": float("{:.3f}".format(thresholds[consts.TX_BIAS_HIGH_WARNING_FIELD])),
            "txbiaslowwarning": float("{:.3f}".format(thresholds[consts.TX_BIAS_LOW_WARNING_FIELD]))
        }

    def get_rx_los(self):
        rx_los_support = self.get_rx_los_support()
        if rx_los_support is None:
            return None
        if not rx_los_support:
            return ["N/A"]
        rx_los = self.xcvr_eeprom.read(consts.RX_LOS_FIELD)
        if rx_los is None:
            return None
        return [rx_los]

    def get_tx_fault(self):
        tx_fault_support = self.get_tx_fault_support()
        if tx_fault_support is None:
            return None
        if not tx_fault_support:
            return ["N/A"]
        tx_fault = self.xcvr_eeprom.read(consts.TX_FAULT_FIELD)
        if tx_fault is None:
            return None
        return [tx_fault]

    def get_tx_disable(self):
        tx_disable_support = self.get_tx_disable_support()
        if tx_disable_support is None:
            return None
        if not tx_disable_support:
            return ["N/A"]
        tx_disable = self.xcvr_eeprom.read(consts.TX_DISABLE_FIELD)
        tx_disable_select = self.xcvr_eeprom.read(consts.TX_DISABLE_SELECT_FIELD)
        if tx_disable is None or tx_disable_select is None:
            return None
        return [tx_disable or tx_disable_select]

    def get_tx_disable_channel(self):
        tx_disable_list = self.get_tx_disable()
        if tx_disable_list is None:
            return None
        if tx_disable_list[0] == "N/A":
            return "N/A"
        return int(tx_disable_list[0])

    def get_module_temperature(self):
        if not self.get_temperature_support():
            return 'N/A'
        temp = self.xcvr_eeprom.read(consts.TEMPERATURE_FIELD)
        if temp is None:
            return None
        return float("{:.3f}".format(temp))

    def get_voltage(self):
        voltage_support = self.get_voltage_support()
        if voltage_support is None:
            return None
        if not voltage_support:
            return 'N/A'
        voltage = self.xcvr_eeprom.read(consts.VOLTAGE_FIELD)
        if voltage is None:
            return None
        return float("{:.3f}".format(voltage))

    def get_tx_bias(self):
        tx_bias_support = self.get_tx_bias_support()
        if tx_bias_support is None:
            return None
        if not tx_bias_support:
            return ["N/A"]
        tx_bias = self.xcvr_eeprom.read(consts.TX_BIAS_FIELD)
        if tx_bias is None:
            return None
        return [float("{:.3f}".format(tx_bias))]

    def get_rx_power(self):
        rx_power_support = self.get_rx_power_support()
        if rx_power_support is None:
            return None
        if not rx_power_support:
            return ["N/A"]
        rx_power = self.xcvr_eeprom.read(consts.RX_POWER_FIELD)
        if rx_power is None:
            return None
        return [float("{:.3f}".format(rx_power))]

    def get_tx_power(self):
        tx_power_support = self.get_tx_power_support()
        if tx_power_support is None:
            return None
        if not tx_power_support:
            return ["N/A"]
        tx_power = self.xcvr_eeprom.read(consts.TX_POWER_FIELD)
        if tx_power is None:
            return None
        return [float("{:.3f}".format(tx_power))]

    def tx_disable(self, tx_disable):
        return self.xcvr_eeprom.write(consts.TX_DISABLE_SELECT_FIELD, tx_disable)

    def tx_disable_channel(self, channel, disable):
        return self.tx_disable(disable) if channel != 0 else True

    def is_flat_memory(self):
        return not self.xcvr_eeprom.read(consts.PAGING_SUPPORT_FIELD) is not False

    def get_temperature_support(self):
        return self.xcvr_eeprom.read(consts.DDM_SUPPORT_FIELD)

    def get_voltage_support(self):
        return self.xcvr_eeprom.read(consts.DDM_SUPPORT_FIELD)

    def get_tx_power_support(self):
        return self.xcvr_eeprom.read(consts.DDM_SUPPORT_FIELD)

    def get_rx_power_support(self):
        return self.xcvr_eeprom.read(consts.DDM_SUPPORT_FIELD)

    def get_rx_los_support(self):
        return self.xcvr_eeprom.read(consts.RX_LOS_SUPPORT_FIELD)

    def get_tx_bias_support(self):
        return self.xcvr_eeprom.read(consts.DDM_SUPPORT_FIELD)

    def get_tx_fault_support(self):
        return self.xcvr_eeprom.read(consts.TX_FAULT_SUPPORT_FIELD)

    def get_tx_disable_support(self):
        return self.xcvr_eeprom.read(consts.TX_DISABLE_SUPPORT_FIELD)

    def get_transceiver_thresholds_support(self):
        return self.xcvr_eeprom.read(consts.DDM_SUPPORT_FIELD)

    def get_lpmode_support(self):
        return False

    def get_power_override_support(self):
        return False

    def get_lpmode(self):
        '''
        Retrieves low power mode status

        Returns:
            bool: True if module in low power else returns False.
        '''
        return False

    def set_lpmode(self, lpmode):
        '''
        This function sets LPMode for the module.

        Args:
            lpmode (bool): False means LPMode Off, True means LPMode On

        Returns:
            bool: True if the provision succeeds, False if it fails
        '''
        return False

    def is_copper(self):
        return self.xcvr_eeprom.read(consts.SFP_CABLE_TECH_FIELD) == 'Passive Cable'
