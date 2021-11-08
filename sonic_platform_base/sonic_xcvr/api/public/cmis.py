"""
    cmis.py

    Implementation of XcvrApi that corresponds to the CMIS specification.
"""

from ...fields import consts
from ..xcvr_api import XcvrApi

class CmisApi(XcvrApi):
    NUM_CHANNELS = 8

    def __init__(self, xcvr_eeprom):
        super(CmisApi, self).__init__(xcvr_eeprom)

    def get_model(self):
        return self.xcvr_eeprom.read(consts.VENDOR_PART_NO_FIELD)

    def get_serial(self):
        return self.xcvr_eeprom.read(consts.VENDOR_SERIAL_NO_FIELD)

    def get_transceiver_info(self):
        admin_info = self.xcvr_eeprom.read(consts.ADMIN_INFO_FIELD)
        media_type = self.xcvr_eeprom.read(consts.MEDIA_TYPE_FIELD)
        if admin_info is None or media_type is None:
            return None

        ext_id = admin_info[consts.EXT_ID_FIELD]
        power_class = ext_id[consts.POWER_CLASS_FIELD]
        max_power = ext_id[consts.MAX_POWER_FIELD]

        xcvr_info = {
            "type": admin_info[consts.ID_FIELD],
            "type_abbrv_name": admin_info[consts.ID_ABBRV_FIELD],
            "hardware_rev": admin_info[consts.VENDOR_REV_FIELD],
            "serial": admin_info[consts.VENDOR_SERIAL_NO_FIELD],
            "manufacturer": admin_info[consts.VENDOR_NAME_FIELD],
            "model": admin_info[consts.VENDOR_PART_NO_FIELD],
            "connector": admin_info[consts.CONNECTOR_FIELD],
            "encoding": "N/A", # Not supported
            "ext_identifier": "%s (%sW Max)" % (power_class, max_power),
            "ext_rateselect_compliance": "N/A", # Not supported
            "cable_type": "Length cable Assembly(m)",
            "cable_length": float(admin_info[consts.LENGTH_ASSEMBLY_FIELD]),
            "nominal_bit_rate": 0, # Not supported
            "specification_compliance": media_type,
            "vendor_date": admin_info[consts.VENDOR_DATE_FIELD],
            "vendor_oui": admin_info[consts.VENDOR_OUI_FIELD],
            # TODO
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
        thresh = self.xcvr_eeprom.read(consts.THRESHOLDS_FIELD)
        if thresh is None:
            return None

        return {
            "temphighalarm": float("{:.3f}".format(thresh[consts.TEMP_HIGH_ALARM_FIELD])),
            "templowalarm": float("{:.3f}".format(thresh[consts.TEMP_LOW_ALARM_FIELD])),
            "temphighwarning": float("{:.3f}".format(thresh[consts.TEMP_HIGH_WARNING_FIELD])),
            "templowwarning": float("{:.3f}".format(thresh[consts.TEMP_LOW_WARNING_FIELD])),
            "vcchighalarm": float("{:.3f}".format(thresh[consts.VOLTAGE_HIGH_ALARM_FIELD])),
            "vcclowalarm": float("{:.3f}".format(thresh[consts.VOLTAGE_LOW_ALARM_FIELD])),
            "vcchighwarning": float("{:.3f}".format(thresh[consts.VOLTAGE_HIGH_WARNING_FIELD])),
            "vcclowwarning": float("{:.3f}".format(thresh[consts.VOLTAGE_LOW_WARNING_FIELD])),
            "rxpowerhighalarm": float("{:.3f}".format(thresh[consts.RX_POWER_HIGH_ALARM_FIELD])),
            "rxpowerlowalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_LOW_ALARM_FIELD]))),
            "rxpowerhighwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_HIGH_WARNING_FIELD]))),
            "rxpowerlowwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_LOW_WARNING_FIELD]))),
            "txpowerhighalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_HIGH_ALARM_FIELD]))),
            "txpowerlowalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_LOW_ALARM_FIELD]))),
            "txpowerhighwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_HIGH_WARNING_FIELD]))),
            "txpowerlowwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_LOW_WARNING_FIELD]))),
            "txbiashighalarm": float("{:.3f}".format(thresh[consts.TX_BIAS_HIGH_ALARM_FIELD])),
            "txbiaslowalarm": float("{:.3f}".format(thresh[consts.TX_BIAS_LOW_ALARM_FIELD])),
            "txbiashighwarning": float("{:.3f}".format(thresh[consts.TX_BIAS_HIGH_WARNING_FIELD])),
            "txbiaslowwarning": float("{:.3f}".format(thresh[consts.TX_BIAS_LOW_WARNING_FIELD]))
        }

    def get_module_temperature(self):
        if not self.get_temperature_support():
            return 'N/A'
        temp = self.xcvr_eeprom.read(consts.TEMPERATURE_FIELD)
        if temp is None:
            return None
        return float("{:.3f}".format(temp))
 
    def get_voltage(self):
        if not self.get_voltage_support():
            return 'N/A'
        voltage = self.xcvr_eeprom.read(consts.VOLTAGE_FIELD)
        if voltage is None:
            return None
        return float("{:.3f}".format(voltage))

    def is_flat_memory(self):
        return self.xcvr_eeprom.read(consts.FLAT_MEM_FIELD)
 
    def get_temperature_support(self):
        return not self.is_flat_memory()

    def get_voltage_support(self):
        return not self.is_flat_memory()

    def get_rx_los_support(self):
        return not self.is_flat_memory()

    def get_rx_los(self):
        rx_los_support = self.get_rx_los_support()
        if rx_los_support is None:
            return None
        if not rx_los_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        rx_los = self.xcvr_eeprom.read(consts.RX_LOS_FIELD)
        if rx_los is None:
            return None
        return [bool(rx_los & (1 << i)) for i in range(self.NUM_CHANNELS)]

    def get_tx_bias_support(self):
        return not self.is_flat_memory()

    def get_tx_bias(self):
        tx_bias_support = self.get_tx_bias_support()
        if tx_bias_support is None:
            return None
        if not tx_bias_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        tx_bias = self.xcvr_eeprom.read(consts.TX_BIAS_FIELD)
        if tx_bias is None:
            return None
        return [channel_bias for channel_bias in tx_bias.values()]
    
    def get_tx_power(self):
        tx_power_support = self.get_tx_power_support()
        if tx_power_support is None:
            return None
        if not tx_power_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        tx_power = self.xcvr_eeprom.read(consts.TX_POWER_FIELD)
        if tx_power is None:
            return None
        return [float("{:.3f}".format(channel_power)) for channel_power in tx_power.values()]

    def get_tx_power_support(self):
        return not self.is_flat_memory()

    def get_rx_power(self):
        rx_power_support = self.get_rx_power_support()
        if rx_power_support is None:
            return None
        if not rx_power_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        rx_power = self.xcvr_eeprom.read(consts.RX_POWER_FIELD)
        if rx_power is None:
            return None
        return [float("{:.3f}".format(channel_power)) for channel_power in rx_power.values()]

    def get_rx_power_support(self):
        return not self.is_flat_memory()

    def get_tx_fault_support(self):
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.TX_FAULT_SUPPORT_FIELD)

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

    def get_tx_disable_support(self):
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.TX_DISABLE_SUPPORT_FIELD)

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

    def tx_disable(self, tx_disable):
        val = 0xFF if tx_disable else 0x0
        return self.xcvr_eeprom.write(consts.TX_DISABLE_FIELD, val)

    def get_tx_disable_channel(self):
        tx_disable_support = self.get_tx_disable_support()
        if tx_disable_support is None:
            return None
        if not tx_disable_support:
            return 'N/A'
        return self.xcvr_eeprom.read(consts.TX_DISABLE_FIELD)

    def tx_disable_channel(self, channel, disable):
        channel_state = self.get_tx_disable_channel()
        if channel_state is None or channel_state == 'N/A':
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

    def get_transceiver_thresholds_support(self):
        return not self.is_flat_memory()

    def get_lpmode_support(self):
        power_class = self.xcvr_eeprom.read(consts.POWER_CLASS_FIELD)
        if power_class is None:
            return False
        return "Power Class 1" not in power_class

    def get_lpmode(self):
        if self.is_flat_memory() or not self.get_lpmode_support():
            return False
        lpmode = self.xcvr_eeprom.read(consts.MODULE_STATE_FIELD)
        if lpmode is not None:
            if lpmode >> 1 == 1:
                return True
        return False

    def set_lpmode(self, lpmode):
        if self.is_flat_memory() or not self.get_lpmode_support():
            return False

        if lpmode is True:
            lpmode_val = 0x10
        else:
            lpmode_val = 0x0

        return self.xcvr_eeprom.write(consts.SET_LP_MODE_FIELD, lpmode_val)

    def get_power_override_support(self):
        return False
