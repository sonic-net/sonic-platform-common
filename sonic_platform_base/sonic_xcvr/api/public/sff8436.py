from ...fields import consts
from ..xcvr_api import XcvrApi

class Sff8436Api(XcvrApi):
    NUM_CHANNELS = 4

    def __init__(self, xcvr_eeprom):
        super(Sff8436Api, self).__init__(xcvr_eeprom)

    def get_model(self):
        return self.xcvr_eeprom.read(consts.VENDOR_PART_NO_FIELD)

    def get_serial(self):
        return self.xcvr_eeprom.read(consts.VENDOR_SERIAL_NO_FIELD)

    def get_transceiver_info(self):
        serial_id = self.xcvr_eeprom.read(consts.SERIAL_ID_FIELD)
        if serial_id is None:
            return None

        ext_id = serial_id[consts.EXT_ID_FIELD]
        power_class = ext_id[consts.POWER_CLASS_FIELD]
        clei_code = ext_id[consts.CLEI_CODE_FIELD]
        cdr_tx = ext_id[consts.CDR_TX_FIELD]
        cdr_rx = ext_id[consts.CDR_RX_FIELD]

        smf_len = serial_id[consts.LENGTH_SMF_KM_FIELD]
        om3_len = serial_id[consts.LENGTH_OM3_FIELD]
        om2_len = serial_id[consts.LENGTH_OM2_FIELD]
        om1_len = serial_id[consts.LENGTH_OM1_FIELD]
        cable_assembly_len = serial_id[consts.LENGTH_ASSEMBLY_FIELD]

        len_types = ['Length(km)', 'Length OM3(2m)', 'Length OM2(m)', 'Length OM1(m)', 'Length Cable Assembly(m)']
        cable_len = 0
        cable_type = "Unknown"
        for len, type in zip([smf_len, om3_len, om2_len, om1_len, cable_assembly_len], len_types):
            if len > 0:
                cable_len = len        
                cable_type = type

        xcvr_info = {
            "type": serial_id[consts.ID_FIELD],
            "type_abbrv_name": serial_id[consts.ID_ABBRV_FIELD],
            "hardware_rev": serial_id[consts.VENDOR_REV_FIELD],
            "serial": serial_id[consts.VENDOR_SERIAL_NO_FIELD],
            "manufacturer": serial_id[consts.VENDOR_NAME_FIELD],
            "model": serial_id[consts.VENDOR_PART_NO_FIELD],
            "connector": serial_id[consts.CONNECTOR_FIELD],
            "encoding": serial_id[consts.ENCODING_FIELD],
            "ext_identifier": ", ".join([power_class, clei_code, cdr_tx, cdr_rx]),
            "ext_rateselect_compliance": serial_id[consts.EXT_RATE_SELECT_COMPLIANCE_FIELD],
            "cable_type": cable_type,
            "cable_length": cable_len,
            "nominal_bit_rate": serial_id[consts.NOMINAL_BR_FIELD],
            "specification_compliance": str(serial_id[consts.SPEC_COMPLIANCE_FIELD]),
            "vendor_date": serial_id[consts.VENDOR_DATE_FIELD],
            "vendor_oui": serial_id[consts.VENDOR_OUI_FIELD],
            "application_advertisement": "N/A",
        }

        return xcvr_info

    def get_transceiver_bulk_status(self):
        rx_los = self.get_rx_los()
        tx_fault = self.get_tx_fault()
        tx_disable = self.get_tx_disable()
        tx_disabled_channel = self.get_tx_disable_channel()
        temp = self.get_module_temperature()
        voltage = self.get_voltage()
        tx_bias = self.get_tx_bias()
        rx_power = self.get_rx_power()
        tx_power = self.get_tx_power()
        read_failed = rx_los is None or \
                      tx_fault is None or \
                      tx_disable is None or \
                      tx_disabled_channel is None or \
                      temp is None or \
                      voltage is None or \
                      tx_bias is None or \
                      rx_power is None or \
                      tx_power is None
        if read_failed:
            return None

        bulk_status = {
            "rx_los": all(rx_los) if self.get_rx_los_support() else 'N/A',
            "tx_fault": all(tx_fault) if self.get_tx_fault_support() else 'N/A',
            "tx_disable": all(tx_disable),
            "tx_disabled_channel": tx_disabled_channel,
            "temperature": temp,
            "voltage": voltage
        }

        for i in range(1, self.NUM_CHANNELS + 1):
            bulk_status["tx%dbias" % i] = tx_bias[i - 1]
            bulk_status["rx%dpower" % i] = rx_power[i - 1]
            bulk_status["tx%dpower" % i] = tx_power[i - 1]

        return bulk_status

    def get_transceiver_threshold_info(self):
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

        temp_thresholds = self.xcvr_eeprom.read(consts.TEMP_THRESHOLDS_FIELD)
        voltage_thresholds = self.xcvr_eeprom.read(consts.VOLTAGE_THRESHOLDS_FIELD)
        rx_power_thresholds = self.xcvr_eeprom.read(consts.RX_POWER_THRESHOLDS_FIELD)
        tx_bias_thresholds = self.xcvr_eeprom.read(consts.TX_BIAS_THRESHOLDS_FIELD)
        read_failed = temp_thresholds is None or \
                      voltage_thresholds is None or \
                      rx_power_thresholds is None or \
                      tx_bias_thresholds is None
        if read_failed:
            return None

        for thresh in rx_power_thresholds:
            rx_power_thresholds[thresh] = self.mw_to_dbm(rx_power_thresholds[thresh])

        return {
            "temphighalarm": float("{:.3f}".format(temp_thresholds[consts.TEMP_HIGH_ALARM_FIELD])),
            "templowalarm": float("{:.3f}".format(temp_thresholds[consts.TEMP_LOW_ALARM_FIELD])),
            "temphighwarning": float("{:.3f}".format(temp_thresholds[consts.TEMP_HIGH_WARNING_FIELD])),
            "templowwarning": float("{:.3f}".format(temp_thresholds[consts.TEMP_LOW_WARNING_FIELD])),
            "vcchighalarm": float("{:.3f}".format(voltage_thresholds[consts.VOLTAGE_HIGH_ALARM_FIELD])),
            "vcclowalarm": float("{:.3f}".format(voltage_thresholds[consts.VOLTAGE_LOW_ALARM_FIELD])),
            "vcchighwarning": float("{:.3f}".format(voltage_thresholds[consts.VOLTAGE_HIGH_WARNING_FIELD])),
            "vcclowwarning": float("{:.3f}".format(voltage_thresholds[consts.VOLTAGE_LOW_WARNING_FIELD])),
            "rxpowerhighalarm": float("{:.3f}".format(rx_power_thresholds[consts.RX_POWER_HIGH_ALARM_FIELD])),
            "rxpowerlowalarm": float("{:.3f}".format(rx_power_thresholds[consts.RX_POWER_LOW_ALARM_FIELD])),
            "rxpowerhighwarning": float("{:.3f}".format(rx_power_thresholds[consts.RX_POWER_HIGH_WARNING_FIELD])),
            "rxpowerlowwarning": float("{:.3f}".format(rx_power_thresholds[consts.RX_POWER_LOW_WARNING_FIELD])),
            "txpowerhighalarm": "N/A",
            "txpowerlowalarm": "N/A",
            "txpowerhighwarning": "N/A",
            "txpowerlowwarning": "N/A",
            "txbiashighalarm": float("{:.3f}".format(tx_bias_thresholds[consts.TX_BIAS_HIGH_ALARM_FIELD])),
            "txbiaslowalarm": float("{:.3f}".format(tx_bias_thresholds[consts.TX_BIAS_LOW_ALARM_FIELD])),
            "txbiashighwarning": float("{:.3f}".format(tx_bias_thresholds[consts.TX_BIAS_HIGH_WARNING_FIELD])),
            "txbiaslowwarning": float("{:.3f}".format(tx_bias_thresholds[consts.TX_BIAS_LOW_WARNING_FIELD]))
        }

    def get_rx_los(self):
        rx_los = self.xcvr_eeprom.read(consts.RX_LOS_FIELD)
        if rx_los is None:
            return None
        return [bool(rx_los & (1 << i)) for i in range(self.NUM_CHANNELS)]

    def get_tx_fault(self):
        tx_fault_support = self.get_tx_fault_support()
        if tx_fault_support is None:
            return None
        if not tx_fault_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        tx_fault = self.xcvr_eeprom.read(consts.TX_FAULT_FIELD)
        if tx_fault is None:
            return None
        return [bool(tx_fault & (1 << i)) for i in range(self.NUM_CHANNELS)]

    def get_tx_disable(self):
        tx_disable_support = self.get_tx_disable_support()
        if tx_disable_support is None:
            return None
        if not tx_disable_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        tx_disable = self.xcvr_eeprom.read(consts.TX_DISABLE_FIELD)
        if tx_disable is None:
            return None
        return [bool(tx_disable & (1 << i)) for i in range(self.NUM_CHANNELS)]

    def get_tx_disable_channel(self):
        tx_disable_support = self.get_tx_disable_support()
        if tx_disable_support is None:
            return None
        if not tx_disable_support:
            return 'N/A'
        return self.xcvr_eeprom.read(consts.TX_DISABLE_FIELD)

    def get_module_temperature(self):
        temp = self.xcvr_eeprom.read(consts.TEMPERATURE_FIELD)
        if temp is None:
            return None
        return float("{:.3f}".format(temp))

    def get_voltage(self):
        voltage = self.xcvr_eeprom.read(consts.VOLTAGE_FIELD)
        if voltage is None:
            return None
        return float("{:.3f}".format(voltage))

    def get_tx_bias(self):
        tx_bias = self.xcvr_eeprom.read(consts.TX_BIAS_FIELD)
        if tx_bias is None:
            return None
        return [channel_bias for channel_bias in tx_bias.values()]

    def get_rx_power(self):
        rx_power = self.xcvr_eeprom.read(consts.RX_POWER_FIELD)
        if rx_power is None:
            return None
        return [float("{:.3f}".format(channel_power)) for channel_power in rx_power.values()]

    def get_tx_power(self):
        return ["N/A" for _ in range(self.NUM_CHANNELS)]

    def tx_disable(self, tx_disable):
        val = 0xF if tx_disable else 0x0
        return self.xcvr_eeprom.write(consts.TX_DISABLE_FIELD, val)

    def tx_disable_channel(self, channel, disable):
        channel_state = self.get_tx_disable_channel()
        if channel_state is None or channel_state == "N/A":
            return False

        for i in range(self.NUM_CHANNELS):
            mask = (1 << i)
            if not (channel & mask):
                continue
            if disable:
                channel_state |= mask
            else:
                channel_state &= ~mask

        return self.xcvr_eeprom.write(consts.TX_DISABLE_FIELD, channel_state)

    def get_power_override(self):
        return self.xcvr_eeprom.read(consts.POWER_OVERRIDE_FIELD)

    def get_power_set(self):
        return self.xcvr_eeprom.read(consts.POWER_SET_FIELD)

    def set_power_override(self, power_override, power_set):
        ret = self.xcvr_eeprom.write(consts.POWER_OVERRIDE_FIELD, power_override)
        if power_override:
            ret &= self.xcvr_eeprom.write(consts.POWER_SET_FIELD, power_set)
        return ret
    
    def is_flat_memory(self):
        return self.xcvr_eeprom.read(consts.FLAT_MEM_FIELD)

    def get_tx_power_support(self):
        return False

    def get_rx_power_support(self):
        return True

    def is_copper(self):
        eth_compliance = self.xcvr_eeprom.read(consts.ETHERNET_10_40G_COMPLIANCE_FIELD)
        if eth_compliance is None:
            return None
        return eth_compliance == "40GBASE-CR4"

    def get_temperature_support(self):
        return True

    def get_voltage_support(self):
        return True

    def get_rx_los_support(self):
        return True

    def get_tx_bias_support(self):
        return True

    def get_tx_fault_support(self):
        return self.xcvr_eeprom.read(consts.TX_FAULT_SUPPORT_FIELD)

    def get_tx_disable_support(self):
        return self.xcvr_eeprom.read(consts.TX_DISABLE_SUPPORT_FIELD)

    def get_transceiver_thresholds_support(self):
        return not self.is_flat_memory()

    def get_lpmode_support(self):
        power_class = self.xcvr_eeprom.read(consts.POWER_CLASS_FIELD)
        if power_class is None:
            return False
        return "Power Class 1" not in power_class

    def get_power_override_support(self):
        return not self.is_copper()
