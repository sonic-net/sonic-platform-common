
"""
    cmis.py

    Implementation of XcvrApi that corresponds to the CMIS specification.
"""

from ...fields import consts
from ..xcvr_api import XcvrApi

import logging
from ...codes.public.cmis import CmisCodes
from ...codes.public.sff8024 import Sff8024
from ...fields import consts
from ..xcvr_api import XcvrApi
from .cmisCDB import CmisCdbApi
from .cmisVDM import CmisVdmApi
import time

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class CmisApi(XcvrApi):
    NUM_CHANNELS = 8
    LowPwrRequestSW = 4
    LowPwrAllowRequestHW = 6

    def __init__(self, xcvr_eeprom):
        super(CmisApi, self).__init__(xcvr_eeprom)
        self.vdm = CmisVdmApi(xcvr_eeprom) if not self.is_flat_memory() else None
        self.cdb = CmisCdbApi(xcvr_eeprom) if not self.is_flat_memory() else None

    def get_model(self):
        '''
        This function returns the part number of the module
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_PART_NO_FIELD)

    def get_vendor_rev(self):
        '''
        This function returns the revision level for part number provided by vendor
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_REV_FIELD)

    def get_serial(self):
        '''
        This function returns the serial number of the module
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_SERIAL_NO_FIELD)

    def get_module_type(self):
        '''
        This function returns the SFF8024Identifier (module type / form-factor). Table 4-1 in SFF-8024 Rev4.6
        '''
        return self.xcvr_eeprom.read(consts.ID_FIELD)

    def get_module_type_abbreviation(self):
        '''
        This function returns the SFF8024Identifier (module type / form-factor). Table 4-1 in SFF-8024 Rev4.6
        '''
        return self.xcvr_eeprom.read(consts.ID_ABBRV_FIELD)

    def get_connector_type(self):
        '''
        This function returns module connector. Table 4-3 in SFF-8024 Rev4.6
        '''
        return self.xcvr_eeprom.read(consts.CONNECTOR_FIELD)

    def get_module_hardware_revision(self):
        '''
        This function returns the module hardware revision
        '''
        if self.is_flat_memory():
            return '0.0'
        hw_major_rev = self.xcvr_eeprom.read(consts.HW_MAJOR_REV)
        hw_minor_rev = self.xcvr_eeprom.read(consts.HW_MAJOR_REV)
        hw_rev = [str(num) for num in [hw_major_rev, hw_minor_rev]]
        return '.'.join(hw_rev)

    def get_cmis_rev(self):
        '''
        This function returns the CMIS version the module complies to
        '''
        cmis_major = self.xcvr_eeprom.read(consts.CMIS_MAJOR_REVISION)
        cmis_minor = self.xcvr_eeprom.read(consts.CMIS_MINOR_REVISION)
        cmis_rev = [str(num) for num in [cmis_major, cmis_minor]]
        return '.'.join(cmis_rev)

    # Transceiver status
    def get_module_state(self):
        '''
        This function returns the module state
        '''
        return self.xcvr_eeprom.read(consts.MODULE_STATE)

    def get_module_fault_cause(self):
        '''
        This function returns the module fault cause
        '''
        return self.xcvr_eeprom.read(consts.MODULE_FAULT_CAUSE)

    def get_module_active_firmware(self):
        '''
        This function returns the active firmware version
        '''
        active_fw_major = self.xcvr_eeprom.read(consts.ACTIVE_FW_MAJOR_REV)
        active_fw_minor = self.xcvr_eeprom.read(consts.ACTIVE_FW_MINOR_REV)
        active_fw = [str(num) for num in [active_fw_major, active_fw_minor]]
        return '.'.join(active_fw)

    def get_module_inactive_firmware(self):
        '''
        This function returns the inactive firmware version
        '''
        if self.is_flat_memory():
            return 'N/A'
        inactive_fw_major = self.xcvr_eeprom.read(consts.INACTIVE_FW_MAJOR_REV)
        inactive_fw_minor = self.xcvr_eeprom.read(consts.INACTIVE_FW_MINOR_REV)
        inactive_fw = [str(num) for num in [inactive_fw_major, inactive_fw_minor]]
        return '.'.join(inactive_fw)

    def get_transceiver_info(self):
        admin_info = self.xcvr_eeprom.read(consts.ADMIN_INFO_FIELD)
        if admin_info is None:
            return None

        ext_id = admin_info[consts.EXT_ID_FIELD]
        power_class = ext_id[consts.POWER_CLASS_FIELD]
        max_power = ext_id[consts.MAX_POWER_FIELD]

        xcvr_info = {
            "type": admin_info[consts.ID_FIELD],
            "type_abbrv_name": admin_info[consts.ID_ABBRV_FIELD],
            "hardware_rev": self.get_module_hardware_revision(),
            "serial": admin_info[consts.VENDOR_SERIAL_NO_FIELD],
            "manufacturer": admin_info[consts.VENDOR_NAME_FIELD],
            "model": admin_info[consts.VENDOR_PART_NO_FIELD],
            "connector": admin_info[consts.CONNECTOR_FIELD],
            "encoding": "N/A", # Not supported
            "ext_identifier": "%s (%sW Max)" % (power_class, max_power),
            "ext_rateselect_compliance": "N/A", # Not supported
            "cable_type": "Length Cable Assembly(m)",
            "cable_length": float(admin_info[consts.LENGTH_ASSEMBLY_FIELD]),
            "nominal_bit_rate": 0, # Not supported
            "vendor_date": admin_info[consts.VENDOR_DATE_FIELD],
            "vendor_oui": admin_info[consts.VENDOR_OUI_FIELD]
        }
        appl_advt = self.get_application_advertisement()
        xcvr_info['application_advertisement'] = str(appl_advt) if len(appl_advt) > 0 else 'N/A'
        xcvr_info['host_electrical_interface'] = self.get_host_electrical_interface()
        xcvr_info['media_interface_code'] = self.get_module_media_interface()
        xcvr_info['host_lane_count'] = self.get_host_lane_count()
        xcvr_info['media_lane_count'] = self.get_media_lane_count()
        xcvr_info['host_lane_assignment_option'] = self.get_host_lane_assignment_option()
        xcvr_info['media_lane_assignment_option'] = self.get_media_lane_assignment_option()
        apsel_dict = self.get_active_apsel_hostlane()
        for lane in range(1, self.NUM_CHANNELS+1):
            xcvr_info["%s%d" % ("active_apsel_hostlane", lane)] = \
                    apsel_dict["%s%d" % (consts.ACTIVE_APSEL_HOSTLANE, lane)]
        xcvr_info['media_interface_technology'] = self.get_media_interface_technology()
        xcvr_info['vendor_rev'] = self.get_vendor_rev()
        xcvr_info['cmis_rev'] = self.get_cmis_rev()
        xcvr_info['active_firmware'] = self.get_module_active_firmware()
        xcvr_info['inactive_firmware'] = self.get_module_inactive_firmware()
        xcvr_info['specification_compliance'] = self.get_module_media_type()

        # In normal case will get a valid value for each of the fields. If get a 'None' value
        # means there was a failure while reading the EEPROM, either because the EEPROM was
        # not ready yet or experincing some other issues. It shouldn't return a dict with a
        # wrong field value, instead should return a 'None' to indicate to XCVRD that retry is
        # needed.
        if None in xcvr_info.values():
            return None
        else:
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
            "tx_disabled_channel": tx_disabled_channel,
            "temperature": temp,
            "voltage": voltage
        }

        for i in range(1, self.NUM_CHANNELS + 1):
            bulk_status["tx%ddisable" % i] = tx_disable[i-1] if self.get_tx_disable_support() else 'N/A'
            bulk_status["tx%dbias" % i] = tx_bias[i - 1]
            bulk_status["rx%dpower" % i] = float("{:.3f}".format(self.mw_to_dbm(rx_power[i - 1]))) if rx_power[i - 1] != 'N/A' else 'N/A'
            bulk_status["tx%dpower" % i] = float("{:.3f}".format(self.mw_to_dbm(tx_power[i - 1]))) if tx_power[i - 1] != 'N/A' else 'N/A'

        laser_temp_dict = self.get_laser_temperature()
        self.vdm_dict = self.get_vdm()
        try:
            bulk_status['laser_temperature'] = laser_temp_dict['monitor value']
            bulk_status['prefec_ber'] = self.vdm_dict['Pre-FEC BER Average Media Input'][1][0]
            bulk_status['postfec_ber_min'] = self.vdm_dict['Errored Frames Minimum Media Input'][1][0]
            bulk_status['postfec_ber_max'] = self.vdm_dict['Errored Frames Maximum Media Input'][1][0]
            bulk_status['postfec_ber_avg'] = self.vdm_dict['Errored Frames Average Media Input'][1][0]
            bulk_status['postfec_curr_val'] = self.vdm_dict['Errored Frames Current Value Media Input'][1][0]
        except (KeyError, TypeError):
            pass
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
        tx_bias_scale_raw = self.xcvr_eeprom.read(consts.TX_BIAS_SCALE)
        tx_bias_scale = 2**tx_bias_scale_raw if tx_bias_scale_raw < 3 else 1
        threshold_info_dict =  {
            "temphighalarm": float("{:.3f}".format(thresh[consts.TEMP_HIGH_ALARM_FIELD])),
            "templowalarm": float("{:.3f}".format(thresh[consts.TEMP_LOW_ALARM_FIELD])),
            "temphighwarning": float("{:.3f}".format(thresh[consts.TEMP_HIGH_WARNING_FIELD])),
            "templowwarning": float("{:.3f}".format(thresh[consts.TEMP_LOW_WARNING_FIELD])),
            "vcchighalarm": float("{:.3f}".format(thresh[consts.VOLTAGE_HIGH_ALARM_FIELD])),
            "vcclowalarm": float("{:.3f}".format(thresh[consts.VOLTAGE_LOW_ALARM_FIELD])),
            "vcchighwarning": float("{:.3f}".format(thresh[consts.VOLTAGE_HIGH_WARNING_FIELD])),
            "vcclowwarning": float("{:.3f}".format(thresh[consts.VOLTAGE_LOW_WARNING_FIELD])),
            "rxpowerhighalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_HIGH_ALARM_FIELD]))),
            "rxpowerlowalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_LOW_ALARM_FIELD]))),
            "rxpowerhighwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_HIGH_WARNING_FIELD]))),
            "rxpowerlowwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_LOW_WARNING_FIELD]))),
            "txpowerhighalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_HIGH_ALARM_FIELD]))),
            "txpowerlowalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_LOW_ALARM_FIELD]))),
            "txpowerhighwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_HIGH_WARNING_FIELD]))),
            "txpowerlowwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_LOW_WARNING_FIELD]))),
            "txbiashighalarm": float("{:.3f}".format(thresh[consts.TX_BIAS_HIGH_ALARM_FIELD]*tx_bias_scale)),
            "txbiaslowalarm": float("{:.3f}".format(thresh[consts.TX_BIAS_LOW_ALARM_FIELD]*tx_bias_scale)),
            "txbiashighwarning": float("{:.3f}".format(thresh[consts.TX_BIAS_HIGH_WARNING_FIELD]*tx_bias_scale)),
            "txbiaslowwarning": float("{:.3f}".format(thresh[consts.TX_BIAS_LOW_WARNING_FIELD]*tx_bias_scale))
        }
        laser_temp_dict = self.get_laser_temperature()
        threshold_info_dict['lasertemphighalarm'] = laser_temp_dict['high alarm']
        threshold_info_dict['lasertemplowalarm'] = laser_temp_dict['low alarm']
        threshold_info_dict['lasertemphighwarning'] = laser_temp_dict['high warn']
        threshold_info_dict['lasertemplowwarning'] = laser_temp_dict['low warn']
        self.vdm_dict = self.get_vdm()
        try:
            threshold_info_dict['prefecberhighalarm'] = self.vdm_dict['Pre-FEC BER Average Media Input'][1][1]
            threshold_info_dict['prefecberlowalarm'] = self.vdm_dict['Pre-FEC BER Average Media Input'][1][2]
            threshold_info_dict['prefecberhighwarning'] = self.vdm_dict['Pre-FEC BER Average Media Input'][1][3]
            threshold_info_dict['prefecberlowwarning'] = self.vdm_dict['Pre-FEC BER Average Media Input'][1][4]
            threshold_info_dict['postfecberhighalarm'] = self.vdm_dict['Errored Frames Average Media Input'][1][1]
            threshold_info_dict['postfecberlowalarm'] = self.vdm_dict['Errored Frames Average Media Input'][1][2]
            threshold_info_dict['postfecberhighwarning'] = self.vdm_dict['Errored Frames Average Media Input'][1][3]
            threshold_info_dict['postfecberlowwarning'] = self.vdm_dict['Errored Frames Average Media Input'][1][4]
        except (KeyError, TypeError):
            pass
        return threshold_info_dict

    def get_module_temperature(self):
        '''
        This function returns the module case temperature and its thresholds. Unit in deg C
        '''
        if not self.get_temperature_support():
            return 'N/A'
        temp = self.xcvr_eeprom.read(consts.TEMPERATURE_FIELD)
        if temp is None:
            return None
        return float("{:.3f}".format(temp))

    def get_voltage(self):
        '''
        This function returns the monitored value of the 3.3-V supply voltage and its thresholds.
        Unit in V
        '''
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
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.RX_LOS_SUPPORT)

    def get_tx_cdr_lol_support(self):
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.TX_CDR_LOL_SUPPORT_FIELD)

    def get_tx_cdr_lol(self):
        '''
        This function returns TX CDR LOL flag on TX host lane
        '''
        tx_cdr_lol_support = self.get_tx_cdr_lol_support()
        if tx_cdr_lol_support is None:
            return None
        if not tx_cdr_lol_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        tx_cdr_lol = self.xcvr_eeprom.read(consts.TX_CDR_LOL)
        if tx_cdr_lol is None:
            return None
        keys = sorted(tx_cdr_lol.keys())
        tx_cdr_lol_final = []
        for key in keys:
            tx_cdr_lol_final.append(bool(tx_cdr_lol[key]))
        return tx_cdr_lol_final

    def get_rx_los(self):
        '''
        This function returns RX LOS flag on RX media lane
        '''
        rx_los_support = self.get_rx_los_support()
        if rx_los_support is None:
            return None
        if not rx_los_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        rx_los = self.xcvr_eeprom.read(consts.RX_LOS_FIELD)
        if rx_los is None:
            return None
        keys = sorted(rx_los.keys())
        rx_los_final = []
        for key in keys:
            rx_los_final.append(bool(rx_los[key]))
        return rx_los_final

    def get_rx_cdr_lol_support(self):
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.RX_CDR_LOL_SUPPORT_FIELD)

    def get_rx_cdr_lol(self):
        '''
        This function returns RX CDR LOL flag on RX media lane
        '''
        rx_cdr_lol_support = self.get_rx_cdr_lol_support()
        if rx_cdr_lol_support is None:
            return None
        if not rx_cdr_lol_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        rx_cdr_lol = self.xcvr_eeprom.read(consts.RX_CDR_LOL)
        if rx_cdr_lol is None:
            return None
        keys = sorted(rx_cdr_lol.keys())
        rx_cdr_lol_final = []
        for key in keys:
            rx_cdr_lol_final.append(bool(rx_cdr_lol[key]))
        return rx_cdr_lol_final

    def get_tx_power_flag(self):
        '''
        This function returns TX power out of range flag on TX media lane
        '''
        tx_power_high_alarm_dict = self.xcvr_eeprom.read(consts.TX_POWER_HIGH_ALARM_FLAG)
        tx_power_low_alarm_dict = self.xcvr_eeprom.read(consts.TX_POWER_LOW_ALARM_FLAG)
        tx_power_high_warn_dict = self.xcvr_eeprom.read(consts.TX_POWER_HIGH_WARN_FLAG)
        tx_power_low_warn_dict = self.xcvr_eeprom.read(consts.TX_POWER_LOW_WARN_FLAG)
        if tx_power_high_alarm_dict is None or tx_power_low_alarm_dict is None or tx_power_high_warn_dict is None or tx_power_low_warn_dict is None:
            return None
        for key, value in tx_power_high_alarm_dict.items():
            tx_power_high_alarm_dict[key] = bool(value)
        for key, value in tx_power_low_alarm_dict.items():
            tx_power_low_alarm_dict[key] = bool(value)
        for key, value in tx_power_high_warn_dict.items():
            tx_power_high_warn_dict[key] = bool(value)
        for key, value in tx_power_low_warn_dict.items():
            tx_power_low_warn_dict[key] = bool(value)
        tx_power_flag_dict = {'tx_power_high_alarm': tx_power_high_alarm_dict,
                              'tx_power_low_alarm': tx_power_low_alarm_dict,
                              'tx_power_high_warn': tx_power_high_warn_dict,
                              'tx_power_low_warn': tx_power_low_warn_dict,}
        return tx_power_flag_dict

    def get_tx_bias_flag(self):
        '''
        This function returns TX bias out of range flag on TX media lane
        '''
        tx_bias_high_alarm_dict = self.xcvr_eeprom.read(consts.TX_BIAS_HIGH_ALARM_FLAG)
        tx_bias_low_alarm_dict = self.xcvr_eeprom.read(consts.TX_BIAS_LOW_ALARM_FLAG)
        tx_bias_high_warn_dict = self.xcvr_eeprom.read(consts.TX_BIAS_HIGH_WARN_FLAG)
        tx_bias_low_warn_dict = self.xcvr_eeprom.read(consts.TX_BIAS_LOW_WARN_FLAG)
        if tx_bias_high_alarm_dict is None or tx_bias_low_alarm_dict is None or tx_bias_high_warn_dict is None or tx_bias_low_warn_dict is None:
            return None
        for key, value in tx_bias_high_alarm_dict.items():
            tx_bias_high_alarm_dict[key] = bool(value)
        for key, value in tx_bias_low_alarm_dict.items():
            tx_bias_low_alarm_dict[key] = bool(value)
        for key, value in tx_bias_high_warn_dict.items():
            tx_bias_high_warn_dict[key] = bool(value)
        for key, value in tx_bias_low_warn_dict.items():
            tx_bias_low_warn_dict[key] = bool(value)
        tx_bias_flag_dict = {'tx_bias_high_alarm': tx_bias_high_alarm_dict,
                              'tx_bias_low_alarm': tx_bias_low_alarm_dict,
                              'tx_bias_high_warn': tx_bias_high_warn_dict,
                              'tx_bias_low_warn': tx_bias_low_warn_dict,}
        return tx_bias_flag_dict

    def get_rx_power_flag(self):
        '''
        This function returns RX power out of range flag on RX media lane
        '''
        rx_power_high_alarm_dict = self.xcvr_eeprom.read(consts.RX_POWER_HIGH_ALARM_FLAG)
        rx_power_low_alarm_dict = self.xcvr_eeprom.read(consts.RX_POWER_LOW_ALARM_FLAG)
        rx_power_high_warn_dict = self.xcvr_eeprom.read(consts.RX_POWER_HIGH_WARN_FLAG)
        rx_power_low_warn_dict = self.xcvr_eeprom.read(consts.RX_POWER_LOW_WARN_FLAG)
        if rx_power_high_alarm_dict is None or rx_power_low_alarm_dict is None or rx_power_high_warn_dict is None or rx_power_low_warn_dict is None:
            return None
        for key, value in rx_power_high_alarm_dict.items():
            rx_power_high_alarm_dict[key] = bool(value)
        for key, value in rx_power_low_alarm_dict.items():
            rx_power_low_alarm_dict[key] = bool(value)
        for key, value in rx_power_high_warn_dict.items():
            rx_power_high_warn_dict[key] = bool(value)
        for key, value in rx_power_low_warn_dict.items():
            rx_power_low_warn_dict[key] = bool(value)
        rx_power_flag_dict = {'rx_power_high_alarm': rx_power_high_alarm_dict,
                              'rx_power_low_alarm': rx_power_low_alarm_dict,
                              'rx_power_high_warn': rx_power_high_warn_dict,
                              'rx_power_low_warn': rx_power_low_warn_dict,}
        return rx_power_flag_dict

    def get_tx_output_status(self):
        '''
        This function returns whether TX output signals are valid on TX media lane
        '''
        tx_output_status_dict = self.xcvr_eeprom.read(consts.TX_OUTPUT_STATUS)
        if tx_output_status_dict is None:
            return None
        for key, value in tx_output_status_dict.items():
            tx_output_status_dict[key] = bool(value)
        return tx_output_status_dict

    def get_rx_output_status(self):
        '''
        This function returns whether RX output signals are valid on RX host lane
        '''
        rx_output_status_dict = self.xcvr_eeprom.read(consts.RX_OUTPUT_STATUS)
        if rx_output_status_dict is None:
            return None
        for key, value in rx_output_status_dict.items():
            rx_output_status_dict[key] = bool(value)
        return rx_output_status_dict

    def get_tx_bias_support(self):
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.TX_BIAS_SUPPORT_FIELD)

    def get_tx_bias(self):
        '''
        This function returns TX bias current on each media lane
        '''
        tx_bias_support = self.get_tx_bias_support()
        if tx_bias_support is None:
            return None
        if not tx_bias_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        scale_raw = self.xcvr_eeprom.read(consts.TX_BIAS_SCALE)
        scale = 2**scale_raw if scale_raw < 3 else 1
        tx_bias = self.xcvr_eeprom.read(consts.TX_BIAS_FIELD)
        for key, value in tx_bias.items():
            tx_bias[key] *= scale
        return [tx_bias['LaserBiasTx%dField' % i] for i in range(1, self.NUM_CHANNELS + 1)]

    def get_tx_power(self):
        '''
        This function returns TX output power in mW on each media lane
        '''
        tx_power = ["N/A" for _ in range(self.NUM_CHANNELS)]

        tx_power_support = self.get_tx_power_support()
        if not tx_power_support:
            return tx_power

        if tx_power_support:
            tx_power = self.xcvr_eeprom.read(consts.TX_POWER_FIELD)
            if tx_power is not None:
                tx_power =  [tx_power['OpticalPowerTx%dField' %i] for i in range(1, self.NUM_CHANNELS+1)]

        return tx_power

    def get_tx_power_support(self):
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.TX_POWER_SUPPORT_FIELD)

    def get_rx_power(self):
        '''
        This function returns RX input power in mW on each media lane
        '''
        rx_power = ["N/A" for _ in range(self.NUM_CHANNELS)]

        rx_power_support = self.get_rx_power_support()
        if not rx_power_support:
            return rx_power

        if rx_power_support:
            rx_power = self.xcvr_eeprom.read(consts.RX_POWER_FIELD)
            if rx_power is not None:
                rx_power = [rx_power['OpticalPowerRx%dField' %i] for i in range(1, self.NUM_CHANNELS+1)]

        return rx_power

    def get_rx_power_support(self):
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.RX_POWER_SUPPORT_FIELD)

    def get_tx_fault_support(self):
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.TX_FAULT_SUPPORT_FIELD)

    def get_tx_fault(self):
        '''
        This function returns TX fault flag on TX media lane
        '''
        tx_fault_support = self.get_tx_fault_support()
        if tx_fault_support is None:
            return None
        if not tx_fault_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        tx_fault = self.xcvr_eeprom.read(consts.TX_FAULT_FIELD)
        if tx_fault is None:
            return None
        keys = sorted(tx_fault.keys())
        tx_fault_final = []
        for key in keys:
            tx_fault_final.append(bool(tx_fault[key]))
        return tx_fault_final

    def get_tx_los_support(self):
        return not self.is_flat_memory() and self.xcvr_eeprom.read(consts.TX_LOS_SUPPORT_FIELD)

    def get_tx_los(self):
        '''
        This function returns TX LOS flag on TX host lane
        '''
        tx_los_support = self.get_tx_los_support()
        if tx_los_support is None:
            return None
        if not tx_los_support:
            return ["N/A" for _ in range(self.NUM_CHANNELS)]
        tx_los = self.xcvr_eeprom.read(consts.TX_LOS_FIELD)
        if tx_los is None:
            return None
        keys = sorted(tx_los.keys())
        tx_los_final = []
        for key in keys:
            tx_los_final.append(bool(tx_los[key]))
        return tx_los_final

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

    def get_power_override(self):
        return None

    def set_power_override(self, power_override, power_set):
        return True

    def get_transceiver_thresholds_support(self):
        return not self.is_flat_memory()

    def get_lpmode_support(self):
        power_class = self.xcvr_eeprom.read(consts.POWER_CLASS_FIELD)
        if power_class is None:
            return False
        return "Power Class 1" not in power_class

    def get_power_override_support(self):
        return False

    def get_module_media_type(self):
        '''
        This function returns module media type: MMF, SMF, Passive Copper Cable, Active Cable Assembly or Base-T.
        '''
        return self.xcvr_eeprom.read(consts.MEDIA_TYPE_FIELD)

    def get_host_electrical_interface(self):
        '''
        This function returns module host electrical interface. Table 4-5 in SFF-8024 Rev4.6
        '''
        if self.is_flat_memory():
            return 'N/A'
        return self.xcvr_eeprom.read(consts.HOST_ELECTRICAL_INTERFACE)

    def get_module_media_interface(self):
        '''
        This function returns module media electrical interface. Table 4-6 ~ 4-10 in SFF-8024 Rev4.6
        '''
        media_type = self.get_module_media_type()
        if media_type == 'nm_850_media_interface':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_850NM)
        elif media_type == 'sm_media_interface':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_SM)
        elif media_type == 'passive_copper_media_interface':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER)
        elif media_type == 'active_cable_media_interface':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE)
        elif media_type == 'base_t_media_interface':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_BASE_T)
        else:
            return 'Unknown media interface'

    def is_coherent_module(self):
        '''
        Returns True if the module follow C-CMIS spec, False otherwise
        '''
        mintf = self.get_module_media_interface()
        return False if 'ZR' not in mintf else True

    def get_datapath_init_duration(self):
        '''
        This function returns the duration of datapath init
        '''
        if self.is_flat_memory():
            return 0
        duration = self.xcvr_eeprom.read(consts.DP_PATH_INIT_DURATION)
        return float(duration) if duration is not None else 0

    def get_datapath_deinit_duration(self):
        '''
        This function returns the duration of datapath deinit
        '''
        if self.is_flat_memory():
            return 0
        duration = self.xcvr_eeprom.read(consts.DP_PATH_DEINIT_DURATION)
        return float(duration) if duration is not None else 0

    def get_host_lane_count(self):
        '''
        This function returns number of host lanes for default application
        '''
        return self.xcvr_eeprom.read(consts.HOST_LANE_COUNT)

    def get_media_lane_count(self):
        '''
        This function returns number of media lanes for default application
        '''
        if self.is_flat_memory():
            return 0
        return self.xcvr_eeprom.read(consts.MEDIA_LANE_COUNT)

    def get_media_interface_technology(self):
        '''
        This function returns the media lane technology
        '''
        return self.xcvr_eeprom.read(consts.MEDIA_INTERFACE_TECH)

    def get_host_lane_assignment_option(self, appl=1):
        '''
        This function returns the host lane that the application begins on
        Args:
            app:
                Integer, desired application for which host_lane_assignment_options are requested
        '''
        if (appl <= 0):
            return 0

        appl_advt = self.get_application_advertisement()
        return appl_advt[appl]['host_lane_assignment_options'] if len(appl_advt) >= appl else 0

    def get_media_lane_assignment_option(self):
        '''
        This function returns the media lane that the application is allowed to begin on
        '''
        if self.is_flat_memory():
            return 'N/A'
        return self.xcvr_eeprom.read(consts.MEDIA_LANE_ASSIGNMENT_OPTION)

    def get_active_apsel_hostlane(self):
        '''
        This function returns the application select code that each host lane has
        '''
        if (self.is_flat_memory()):
            return {'{}{}'.format(consts.ACTIVE_APSEL_HOSTLANE, i) : 'N/A' for i in range(1, self.NUM_CHANNELS+1)}
        return self.xcvr_eeprom.read(consts.ACTIVE_APSEL_CODE)

    def get_tx_config_power(self):
        '''
        This function returns the configured TX output power. Unit in dBm
        '''
        return self.xcvr_eeprom.read(consts.TX_CONFIG_POWER)

    def get_media_output_loopback(self):
        '''
        This function returns the media output loopback status
        '''
        result = self.xcvr_eeprom.read(consts.MEDIA_OUTPUT_LOOPBACK)
        if result is None:
            return None
        return result == 1

    def get_media_input_loopback(self):
        '''
        This function returns the media input loopback status
        '''
        result = self.xcvr_eeprom.read(consts.MEDIA_INPUT_LOOPBACK)
        if result is None:
            return None
        return result == 1

    def get_host_output_loopback(self):
        '''
        This function returns the host output loopback status
        '''
        result = self.xcvr_eeprom.read(consts.HOST_OUTPUT_LOOPBACK)
        if result is None:
            return None
        loopback_status = []
        for bitpos in range(self.NUM_CHANNELS):
            loopback_status.append(bool((result >> bitpos) & 0x1))
        return loopback_status

    def get_host_input_loopback(self):
        '''
        This function returns the host input loopback status
        '''
        result = self.xcvr_eeprom.read(consts.HOST_INPUT_LOOPBACK)
        if result is None:
            return None
        loopback_status = []
        for bitpos in range(self.NUM_CHANNELS):
            loopback_status.append(bool((result >> bitpos) & 0x1))
        return loopback_status

    def get_aux_mon_type(self):
        '''
        This function returns the aux monitor types
        '''
        result = self.xcvr_eeprom.read(consts.AUX_MON_TYPE) if not self.is_flat_memory() else None
        if result is None:
            return None
        aux1_mon_type = result & 0x1
        aux2_mon_type = (result >> 1) & 0x1
        aux3_mon_type = (result >> 2) & 0x1
        return aux1_mon_type, aux2_mon_type, aux3_mon_type

    def get_laser_temperature(self):
        '''
        This function returns the laser temperature monitor value
        '''
        laser_temp_dict = {
            'monitor value' : 'N/A',
            'high alarm' : 'N/A',
            'low alarm' : 'N/A',
            'high warn' : 'N/A',
            'low warn' : 'N/A'
        }

        if self.is_flat_memory():
            return laser_temp_dict

        try:
            aux1_mon_type, aux2_mon_type, aux3_mon_type = self.get_aux_mon_type()
        except TypeError:
            return None
        LASER_TEMP_SCALE = 256.0
        if aux2_mon_type == 0:
            laser_temp = self.xcvr_eeprom.read(consts.AUX2_MON)/LASER_TEMP_SCALE
            laser_temp_high_alarm = self.xcvr_eeprom.read(consts.AUX2_HIGH_ALARM)/LASER_TEMP_SCALE
            laser_temp_low_alarm = self.xcvr_eeprom.read(consts.AUX2_LOW_ALARM)/LASER_TEMP_SCALE
            laser_temp_high_warn = self.xcvr_eeprom.read(consts.AUX2_HIGH_WARN)/LASER_TEMP_SCALE
            laser_temp_low_warn = self.xcvr_eeprom.read(consts.AUX2_LOW_WARN)/LASER_TEMP_SCALE
        elif aux2_mon_type == 1 and aux3_mon_type == 0:
            laser_temp = self.xcvr_eeprom.read(consts.AUX3_MON)/LASER_TEMP_SCALE
            laser_temp_high_alarm = self.xcvr_eeprom.read(consts.AUX3_HIGH_ALARM)/LASER_TEMP_SCALE
            laser_temp_low_alarm = self.xcvr_eeprom.read(consts.AUX3_LOW_ALARM)/LASER_TEMP_SCALE
            laser_temp_high_warn = self.xcvr_eeprom.read(consts.AUX3_HIGH_WARN)/LASER_TEMP_SCALE
            laser_temp_low_warn = self.xcvr_eeprom.read(consts.AUX3_LOW_WARN)/LASER_TEMP_SCALE
        else:
            return laser_temp_dict
        laser_temp_dict = {'monitor value': laser_temp,
                           'high alarm': laser_temp_high_alarm,
                           'low alarm': laser_temp_low_alarm,
                           'high warn': laser_temp_high_warn,
                           'low warn': laser_temp_low_warn}
        return laser_temp_dict

    def get_laser_TEC_current(self):
        '''
        This function returns the laser TEC current monitor value
        '''
        try:
            aux1_mon_type, aux2_mon_type, aux3_mon_type = self.get_aux_mon_type()
        except TypeError:
            return None
        LASER_TEC_CURRENT_SCALE = 32767.0
        if aux1_mon_type == 1:
            laser_tec_current = self.xcvr_eeprom.read(consts.AUX1_MON)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_high_alarm = self.xcvr_eeprom.read(consts.AUX1_HIGH_ALARM)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_low_alarm = self.xcvr_eeprom.read(consts.AUX1_LOW_ALARM)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_high_warn = self.xcvr_eeprom.read(consts.AUX1_HIGH_WARN)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_low_warn = self.xcvr_eeprom.read(consts.AUX1_LOW_WARN)/LASER_TEC_CURRENT_SCALE
        elif aux1_mon_type == 0 and aux2_mon_type == 1:
            laser_tec_current = self.xcvr_eeprom.read(consts.AUX2_MON)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_high_alarm = self.xcvr_eeprom.read(consts.AUX2_HIGH_ALARM)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_low_alarm = self.xcvr_eeprom.read(consts.AUX2_LOW_ALARM)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_high_warn = self.xcvr_eeprom.read(consts.AUX2_HIGH_WARN)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_low_warn = self.xcvr_eeprom.read(consts.AUX2_LOW_WARN)/LASER_TEC_CURRENT_SCALE
        else:
            return None
        laser_tec_current_dict = {'monitor value': laser_tec_current,
                                  'high alarm': laser_tec_current_high_alarm,
                                  'low alarm': laser_tec_current_low_alarm,
                                  'high warn': laser_tec_current_high_warn,
                                  'low warn': laser_tec_current_low_warn}
        return laser_tec_current_dict

    def get_config_datapath_hostlane_status(self):
        '''
        This function returns configuration command execution
        / result status for the datapath of each host lane
        '''
        return self.xcvr_eeprom.read(consts.CONFIG_LANE_STATUS)

    def get_datapath_state(self):
        '''
        This function returns the eight datapath states
        '''
        return self.xcvr_eeprom.read(consts.DATA_PATH_STATE)

    def get_dpinit_pending(self):
        '''
        This function returns datapath init pending status.
        0 means datapath init not pending.
        1 means datapath init pending. DPInit not yet executed after successful ApplyDPInit.
        Hence the active control set content may deviate from the actual hardware config
        '''
        dpinit_pending_dict = self.xcvr_eeprom.read(consts.DPINIT_PENDING)
        if dpinit_pending_dict is None:
            return None
        for key, value in dpinit_pending_dict.items():
            dpinit_pending_dict[key] = bool(value)
        return dpinit_pending_dict

    def get_supported_power_config(self):
        '''
        This function returns the supported TX power range
        '''
        min_prog_tx_output_power = self.xcvr_eeprom.read(consts.MIN_PROG_OUTPUT_POWER)
        max_prog_tx_output_power = self.xcvr_eeprom.read(consts.MAX_PROG_OUTPUT_POWER)
        return min_prog_tx_output_power, max_prog_tx_output_power

    def reset_module(self, reset = False):
        '''
        This function resets the module
        Return True if the provision succeeds, False if it fails
        Return True if no action.
        '''
        if reset:
            reset_control = reset << 3
            return self.xcvr_eeprom.write(consts.MODULE_LEVEL_CONTROL, reset_control)
        else:
            return True

    def reset(self):
        """
        Reset SFP and return all user module settings to their default state.

        Returns:
            A boolean, True if successful, False if not
        """
        if self.reset_module(True):
            # minimum waiting time for the TWI to be functional again
            time.sleep(2)
            # buffer time
            for retries in range(5):
                state = self.get_module_state()
                if state in ['ModuleReady', 'ModuleLowPwr']:
                    return True
                time.sleep(1)
        return False

    def get_lpmode(self):
        '''
        Retrieves Low power module status
        Returns True if module in low power else returns False.
        '''
        if self.is_flat_memory() or not self.get_lpmode_support():
            return False

        lpmode = self.xcvr_eeprom.read(consts.TRANS_MODULE_STATUS_FIELD)
        if lpmode is not None:
            if lpmode.get('ModuleState') == 'ModuleLowPwr':
                return True
        return False

    def set_lpmode(self, lpmode):
        '''
        This function sets the module to low power state.
        lpmode being False means "set to high power"
        lpmode being True means "set to low power"
        Return True if the provision succeeds, False if it fails
        '''

        if self.is_flat_memory() or not self.get_lpmode_support():
            return False

        lpmode_val = self.xcvr_eeprom.read(consts.MODULE_LEVEL_CONTROL)
        if lpmode_val is not None:
            if lpmode is True:
                # Force module transition to LowPwr under SW control
                lpmode_val = lpmode_val | (1 << CmisApi.LowPwrRequestSW)
                self.xcvr_eeprom.write(consts.MODULE_LEVEL_CONTROL, lpmode_val)
                time.sleep(0.1)
                return self.get_lpmode()
            else:
                # Force transition from LowPwr to HighPower state under SW control.
                # This will transition LowPwrS signal to False. (see Table 6-12 CMIS v5.0)
                lpmode_val = lpmode_val & ~(1 << CmisApi.LowPwrRequestSW)
                lpmode_val = lpmode_val & ~(1 << CmisApi.LowPwrAllowRequestHW)
                self.xcvr_eeprom.write(consts.MODULE_LEVEL_CONTROL, lpmode_val)
                time.sleep(1)
                mstate = self.get_module_state()
                return True if mstate == 'ModuleReady' else False
        return False

    def get_loopback_capability(self):
        '''
        This function returns the module loopback capability as advertised
        '''
        if self.is_flat_memory():
            return None
        allowed_loopback_result = self.xcvr_eeprom.read(consts.LOOPBACK_CAPABILITY)
        if allowed_loopback_result is None:
            return None
        loopback_capability = dict()
        loopback_capability['simultaneous_host_media_loopback_supported'] = bool((allowed_loopback_result >> 6) & 0x1)
        loopback_capability['per_lane_media_loopback_supported'] = bool((allowed_loopback_result >> 5) & 0x1)
        loopback_capability['per_lane_host_loopback_supported'] = bool((allowed_loopback_result >> 4) & 0x1)
        loopback_capability['host_side_input_loopback_supported'] = bool((allowed_loopback_result >> 3) & 0x1)
        loopback_capability['host_side_output_loopback_supported'] = bool((allowed_loopback_result >> 2) & 0x1)
        loopback_capability['media_side_input_loopback_supported'] = bool((allowed_loopback_result >> 1) & 0x1)
        loopback_capability['media_side_output_loopback_supported'] = bool((allowed_loopback_result >> 0) & 0x1)
        return loopback_capability

    def set_loopback_mode(self, loopback_mode):
        '''
        This function sets the module loopback mode.
        Loopback mode has to be one of the five:
        1. "none" (default)
        2. "host-side-input"
        3. "host-side-output"
        4. "media-side-input"
        5. "media-side-output"
        The function will look at 13h:128 to check advertized loopback capabilities.
        Return True if the provision succeeds, False if it fails
        '''
        loopback_capability = self.get_loopback_capability()
        if loopback_capability is None:
            return False
        if loopback_mode == 'none':
            status_host_input = self.xcvr_eeprom.write(consts.HOST_INPUT_LOOPBACK, 0)
            status_host_output = self.xcvr_eeprom.write(consts.HOST_OUTPUT_LOOPBACK, 0)
            status_media_input = self.xcvr_eeprom.write(consts.MEDIA_INPUT_LOOPBACK, 0)
            status_media_output = self.xcvr_eeprom.write(consts.MEDIA_OUTPUT_LOOPBACK, 0)
            return all([status_host_input, status_host_output, status_media_input, status_media_output])
        elif loopback_mode == 'host-side-input':
            if loopback_capability['host_side_input_loopback_supported']:
                return self.xcvr_eeprom.write(consts.HOST_INPUT_LOOPBACK, 0xff)
            else:
                return False
        elif loopback_mode == 'host-side-output':
            if loopback_capability['host_side_output_loopback_supported']:
                return self.xcvr_eeprom.write(consts.HOST_OUTPUT_LOOPBACK, 0xff)
            else:
                return False
        elif loopback_mode == 'media-side-input':
            if loopback_capability['media_side_input_loopback_supported']:
                return self.xcvr_eeprom.write(consts.MEDIA_INPUT_LOOPBACK, 0xff)
            else:
                return False
        elif loopback_mode == 'media-side-output':
            if loopback_capability['media_side_output_loopback_supported']:
                return self.xcvr_eeprom.write(consts.MEDIA_OUTPUT_LOOPBACK, 0xff)
            else:
                return False
        else:
            return False

    def get_vdm(self):
        '''
        This function returns all the VDM items, including real time monitor value, threholds and flags
        '''
        vdm = self.vdm.get_vdm_allpage() if self.vdm is not None else {}
        return vdm

    def get_module_firmware_fault_state_changed(self):
        '''
        This function returns datapath firmware fault state, module firmware fault state
        and whether module state changed
        '''
        result = self.xcvr_eeprom.read(consts.MODULE_FIRMWARE_FAULT_INFO)
        if result is None:
            return None
        datapath_firmware_fault = bool((result >> 2) & 0x1)
        module_firmware_fault = bool((result >> 1) & 0x1)
        module_state_changed = bool(result & 0x1)
        return datapath_firmware_fault, module_firmware_fault, module_state_changed

    def get_module_level_flag(self):
        '''
        This function returns teh module level flags, including
        - 3.3 V voltage supply flags
        - Case temperature flags
        - Aux 1 flags
        - Aux 2 flags
        - Aux 3 flags
        - Custom field flags
        '''
        module_flag_byte1 = self.xcvr_eeprom.read(consts.MODULE_FLAG_BYTE1)
        module_flag_byte2 = self.xcvr_eeprom.read(consts.MODULE_FLAG_BYTE2)
        module_flag_byte3 = self.xcvr_eeprom.read(consts.MODULE_FLAG_BYTE3)
        if module_flag_byte1 is None or module_flag_byte2 is None or module_flag_byte3 is None:
            return None
        voltage_high_alarm_flag = bool((module_flag_byte1 >> 4) & 0x1)
        voltage_low_alarm_flag = bool((module_flag_byte1 >> 5) & 0x1)
        voltage_high_warn_flag = bool((module_flag_byte1 >> 6) & 0x1)
        voltage_low_warn_flag = bool((module_flag_byte1 >> 7) & 0x1)
        voltage_flags = {'voltage_high_alarm_flag': voltage_high_alarm_flag,
                         'voltage_low_alarm_flag': voltage_low_alarm_flag,
                         'voltage_high_warn_flag': voltage_high_warn_flag,
                         'voltage_low_warn_flag': voltage_low_warn_flag}

        case_temp_high_alarm_flag = bool((module_flag_byte1 >> 0) & 0x1)
        case_temp_low_alarm_flag = bool((module_flag_byte1 >> 1) & 0x1)
        case_temp_high_warn_flag = bool((module_flag_byte1 >> 2) & 0x1)
        case_temp_low_warn_flag = bool((module_flag_byte1 >> 3) & 0x1)
        case_temp_flags = {'case_temp_high_alarm_flag': case_temp_high_alarm_flag,
                           'case_temp_low_alarm_flag': case_temp_low_alarm_flag,
                           'case_temp_high_warn_flag': case_temp_high_warn_flag,
                           'case_temp_low_warn_flag': case_temp_low_warn_flag}

        aux2_high_alarm_flag = bool((module_flag_byte2 >> 4) & 0x1)
        aux2_low_alarm_flag = bool((module_flag_byte2 >> 5) & 0x1)
        aux2_high_warn_flag = bool((module_flag_byte2 >> 6) & 0x1)
        aux2_low_warn_flag = bool((module_flag_byte2 >> 7) & 0x1)
        aux2_flags = {'aux2_high_alarm_flag': aux2_high_alarm_flag,
                      'aux2_low_alarm_flag': aux2_low_alarm_flag,
                      'aux2_high_warn_flag': aux2_high_warn_flag,
                      'aux2_low_warn_flag': aux2_low_warn_flag}

        aux1_high_alarm_flag = bool((module_flag_byte2 >> 0) & 0x1)
        aux1_low_alarm_flag = bool((module_flag_byte2 >> 1) & 0x1)
        aux1_high_warn_flag = bool((module_flag_byte2 >> 2) & 0x1)
        aux1_low_warn_flag = bool((module_flag_byte2 >> 3) & 0x1)
        aux1_flags = {'aux1_high_alarm_flag': aux1_high_alarm_flag,
                      'aux1_low_alarm_flag': aux1_low_alarm_flag,
                      'aux1_high_warn_flag': aux1_high_warn_flag,
                      'aux1_low_warn_flag': aux1_low_warn_flag}

        custom_mon_high_alarm_flag = bool((module_flag_byte3 >> 4) & 0x1)
        custom_mon_low_alarm_flag = bool((module_flag_byte3 >> 5) & 0x1)
        custom_mon_high_warn_flag = bool((module_flag_byte3 >> 6) & 0x1)
        custom_mon_low_warn_flag = bool((module_flag_byte3 >> 7) & 0x1)
        custom_mon_flags = {'custom_mon_high_alarm_flag': custom_mon_high_alarm_flag,
                            'custom_mon_low_alarm_flag': custom_mon_low_alarm_flag,
                            'custom_mon_high_warn_flag': custom_mon_high_warn_flag,
                            'custom_mon_low_warn_flag': custom_mon_low_warn_flag}

        aux3_high_alarm_flag = bool((module_flag_byte3 >> 0) & 0x1)
        aux3_low_alarm_flag = bool((module_flag_byte3 >> 1) & 0x1)
        aux3_high_warn_flag = bool((module_flag_byte3 >> 2) & 0x1)
        aux3_low_warn_flag = bool((module_flag_byte3 >> 3) & 0x1)
        aux3_flags = {'aux3_high_alarm_flag': aux3_high_alarm_flag,
                      'aux3_low_alarm_flag': aux3_low_alarm_flag,
                      'aux3_high_warn_flag': aux3_high_warn_flag,
                      'aux3_low_warn_flag': aux3_low_warn_flag}

        module_flag = {'voltage_flags': voltage_flags,
                       'case_temp_flags': case_temp_flags,
                       'aux1_flags': aux1_flags,
                       'aux2_flags': aux2_flags,
                       'aux3_flags': aux3_flags,
                       'custom_mon_flags': custom_mon_flags}
        return module_flag

    def get_module_fw_mgmt_feature(self, verbose = False):
        """
        This function obtains CDB features supported by the module from CDB command 0041h,
        such as start header size, maximum block size, whether extended payload messaging
        (page 0xA0 - 0xAF) or only local payload is supported. These features are important because
        the following upgrade with depend on these parameters.
        """
        txt = ''
        if self.cdb is None:
            return {'status': False, 'info': "CDB Not supported", 'result': None}

        # get fw upgrade features (CMD 0041h)
        starttime = time.time()
        autopaging = self.xcvr_eeprom.read(consts.AUTO_PAGING_SUPPORT)
        autopaging_flag = bool(autopaging)
        writelength_raw = self.xcvr_eeprom.read(consts.CDB_SEQ_WRITE_LENGTH_EXT)
        if writelength_raw is None:
            return None
        writelength = (writelength_raw + 1) * 8
        txt += 'Auto page support: %s\n' %autopaging_flag
        txt += 'Max write length: %d\n' %writelength
        rpllen, rpl_chkcode, rpl = self.cdb.get_fw_management_features()
        if self.cdb.cdb_chkcode(rpl) == rpl_chkcode:
            startLPLsize = rpl[2]
            txt += 'Start payload size %d\n' % startLPLsize
            maxblocksize = (rpl[4] + 1) * 8
            txt += 'Max block size %d\n' % maxblocksize
            lplEplSupport = {0x00 : 'No write to LPL/EPL supported',
                            0x01 : 'Write to LPL supported',
                            0x10 : 'Write to EPL supported',
                            0x11 : 'Write to LPL/EPL supported'}
            txt += '{}\n'.format(lplEplSupport[rpl[5]])
            if rpl[5] == 1:
                lplonly_flag = True
            else:
                lplonly_flag = False
            txt += 'Abort CMD102h supported %s\n' %bool(rpl[1] & 0x01)
            if verbose:
                txt += 'Copy CMD108h supported %s\n' %bool((rpl[1] >> 1) & 0x01)
                txt += 'Skipping erased blocks supported %s\n' %bool((rpl[1] >> 2) & 0x01)
                txt += 'Full image readback supported %s\n' %bool((rpl[1] >> 7) & 0x01)
                txt += 'Default erase byte {:#x}\n'.format(rpl[3])
                txt += 'Read to LPL/EPL {:#x}\n'.format(rpl[6])

        else:
            txt += 'Reply payload check code error\n'
            return {'status': False, 'info': txt, 'result': None}
        elapsedtime = time.time()-starttime
        logger.info('Get module FW upgrade features time: %.2f s\n' %elapsedtime)
        logger.info(txt)
        return {'status': True, 'info': txt, 'feature': (startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength)}

    def get_module_fw_info(self):
        """
        This function returns firmware Image A and B version, running version, committed version
        and whether both firmware images are valid.
        Operational Status: 1 = running, 0 = not running
        Administrative Status: 1=committed, 0=uncommitted
        Validity Status: 1 = invalid, 0 = valid
        """
        txt = ''

        if self.cdb is None:
            return {'status': False, 'info': "CDB Not supported", 'result': None}

        # get fw info (CMD 0100h)
        rpllen, rpl_chkcode, rpl = self.cdb.get_fw_info()
        # Interface NACK or timeout
        if (rpllen is None) or (rpl_chkcode is None):
            return {'status': False, 'info': "Interface fail", 'result': 0} # Return result 0 for distinguishing CDB is maybe in busy or failure.

        # password issue
        if self.cdb.cdb_chkcode(rpl) != rpl_chkcode:
            string = 'Get module FW info: Need to enter password\n'
            logger.info(string)
            # Reset password for module using CMIS 4.0
            self.cdb.module_enter_password(0)
            rpllen, rpl_chkcode, rpl = self.cdb.get_fw_info()

        if self.cdb.cdb_chkcode(rpl) == rpl_chkcode:
            # Regiter 9Fh:136
            fwStatus = rpl[0]
            ImageARunning = (fwStatus & 0x01) # bit 0 - image A is running
            ImageACommitted = ((fwStatus >> 1) & 0x01) # bit 1 - image A is committed
            ImageAValid = ((fwStatus >> 2) & 0x01) # bit 2 - image A is valid
            ImageBRunning = ((fwStatus >> 4) & 0x01) # bit 4 - image B is running
            ImageBCommitted = ((fwStatus >> 5) & 0x01)  # bit 5 - image B is committed
            ImageBValid = ((fwStatus >> 6) & 0x01) # bit 6 - image B is valid

            if ImageAValid == 0:
                # Registers 9Fh:138,139; 140,141
                ImageA = '%d.%d.%d' %(rpl[2], rpl[3], ((rpl[4]<< 8) | rpl[5]))
            else:
                ImageA = "N/A"
            txt += 'Image A Version: %s\n' %ImageA

            if ImageBValid == 0:
                # Registers 9Fh:174,175; 176.177
                ImageB = '%d.%d.%d' %(rpl[38], rpl[39], ((rpl[40]<< 8) | rpl[41]))
            else:
                ImageB = "N/A"
            txt += 'Image B Version: %s\n' %ImageB

            if rpllen > 77:
                factory_image = '%d.%d.%d' % (rpl[74], rpl[75], ((rpl[76] << 8) | rpl[77]))
                txt += 'Factory Image Version: %s\n' %factory_image

            if ImageARunning == 1:
                RunningImage = 'A'
            elif ImageBRunning == 1:
                RunningImage = 'B'
            else:
                RunningImage = 'N/A'
            if ImageACommitted == 1:
                CommittedImage = 'A'
            elif ImageBCommitted == 1:
                CommittedImage = 'B'
            else:
                CommittedImage = 'N/A'
            txt += 'Running Image: %s\n' % (RunningImage)
            txt += 'Committed Image: %s\n' % (CommittedImage)
            txt += 'Active Firmware: {}\n'.format(self.get_module_active_firmware())
            txt += 'Inactive Firmware: {}\n'.format(self.get_module_inactive_firmware())
        else:
            txt += 'Reply payload check code error\n'
            return {'status': False, 'info': txt, 'result': None}
        return {'status': True, 'info': txt, 'result': (ImageA, ImageARunning, ImageACommitted, ImageAValid, ImageB, ImageBRunning, ImageBCommitted, ImageBValid)}

    def cdb_run_firmware(self, mode = 0x01):
        # run module FW (CMD 0109h)
        return self.cdb.run_fw_image(mode)

    def cdb_commit_firmware(self):
        return self.cdb.commit_fw_image()

    def module_fw_run(self, mode = 0x01):
        """
        This command is used to start and run a selected image.
        This command transfers control from the currently
        running firmware to a selected firmware that is started. It
        can be used to switch between firmware versions, or to
        perform a restart of the currently running firmware.
        mode:
        00h = Traffic affecting Reset to Inactive Image.
        01h = Attempt Hitless Reset to Inactive Image
        02h = Traffic affecting Reset to Running Image.
        03h = Attempt Hitless Reset to Running Image

        This function returns True if firmware run successfully completes.
        Otherwise it will return False.
        """
        # run module FW (CMD 0109h)
        txt = ''
        if self.cdb is None:
            return False, "CDB NOT supported on this module"
        starttime = time.time()
        fw_run_status = self.cdb.run_fw_image(mode)
        if fw_run_status == 1:
            txt += 'Module FW run: Success\n'
        # password issue
        elif fw_run_status == 70:
            string = 'Module FW run: Need to enter password\n'
            logger.info(string)
            self.cdb.module_enter_password()
            fw_run_status = self.cdb.run_fw_image(mode)
            txt += 'FW_run_status %d\n' %fw_run_status
        else:
            # self.cdb.abort_fw_download()
            txt += 'Module FW run: Fail\n'
            txt += 'FW_run_status %d\n' %fw_run_status
            return False, txt
        elapsedtime = time.time()-starttime
        logger.info('Module FW run time: %.2f s\n' %elapsedtime)
        logger.info(txt)
        return True, txt

    def module_fw_commit(self):
        """
        The host uses this command to commit the running image
        so that the module will boot from it on future boots.

        This function returns True if firmware commit successfully completes.
        Otherwise it will return False.
        """
        txt = ''
        if self.cdb is None:
            return False, "CDB NOT supported on this module"
        # commit module FW (CMD 010Ah)
        starttime = time.time()
        fw_commit_status= self.cdb.commit_fw_image()
        if fw_commit_status == 1:
            txt += 'Module FW commit: Success\n'
        # password issue
        elif fw_commit_status == 70:
            string = 'Module FW commit: Need to enter password\n'
            logger.info(string)
            self.cdb.module_enter_password()
            fw_commit_status = self.cdb.commit_fw_image()
            txt += 'FW_commit_status %d\n' %fw_commit_status
        else:
            # self.cdb.abort_fw_download()
            txt += 'Module FW commit: Fail\n'
            txt += 'FW_commit_status %d\n' %fw_commit_status
            return False, txt
        elapsedtime = time.time()-starttime
        logger.info('Module FW commit time: %.2f s\n' %elapsedtime)
        logger.info(txt)
        return True, txt

    def cdb_firmware_download_complete(self):
        # complete FW download (CMD 0107h)
        return self.cdb.validate_fw_image()

    def cdb_start_firmware_download(self, startLPLsize, startdata, imagesize):
        return self.cdb.start_fw_download(startLPLsize, bytearray(startdata), imagesize)

    def cdb_lpl_block_write(self, address, data):
        return self.cdb.block_write_lpl(address, data)

    def cdb_epl_block_write(self, address, data, autopaging_flag, writelength):
        return self.cdb.block_write_epl(address, data, autopaging_flag, writelength)

    def cdb_enter_host_password(self, password):
        return self.cdb.module_enter_password(password)

    def module_fw_download(self, startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength, imagepath):
        """
        This function performs the download of a firmware image to module eeprom
        It starts CDB download by writing the header of start header size
        from the designated firmware file to the local payload page 0x9F, with CDB command 0101h.

        Then it repeatedly reads from the given firmware file and write to the payload
        space advertised from the first step. We use CDB command 0103h to write to the local payload;
        we use CDB command 0104h to write to the extended paylaod. This step repeats until it reaches
        end of the firmware file, or the CDB status failed.

        The last step is to complete the firmware upgrade with CDB command 0107h.

        Note that if the download process fails anywhere in the middle, we need to run CDB command 0102h
        to abort the upgrade before we restart another upgrade process.

        This function returns True if download successfully completes. Otherwise it will return False where it fails.
        """
        txt = ''
        if self.cdb is None:
            return False, "CDB NOT supported on this module"

        # start fw download (CMD 0101h)
        starttime = time.time()
        try:
            f = open(imagepath, 'rb')
        except FileNotFoundError:
            txt += 'Image path  %s is incorrect.\n' % imagepath
            logger.info(txt)
            return False, txt

        f.seek(0, 2)
        imagesize = f.tell()
        f.seek(0, 0)
        startdata = f.read(startLPLsize)
        logger.info('\nStart FW downloading')
        logger.info("startLPLsize is %d" %startLPLsize)
        fw_start_status = self.cdb.start_fw_download(startLPLsize, bytearray(startdata), imagesize)
        if fw_start_status == 1:
            string = 'Start module FW download: Success\n'
            logger.info(string)
        # password error
        elif fw_start_status == 70:
            string = 'Start module FW download: Need to enter password\n'
            logger.info(string)
            self.cdb.module_enter_password()
            self.cdb.start_fw_download(startLPLsize, bytearray(startdata), imagesize)
        else:
            string = 'Start module FW download: Fail\n'
            txt += string
            self.cdb.abort_fw_download()
            txt += 'FW_start_status %d\n' %fw_start_status
            logger.info(txt)
            return False, txt
        elapsedtime = time.time()-starttime
        logger.info('Start module FW download time: %.2f s' %elapsedtime)

        # start periodically writing (CMD 0103h or 0104h)
        # assert maxblocksize == 2048 or lplonly_flag
        if lplonly_flag:
            BLOCK_SIZE = 116
        else:
            BLOCK_SIZE = maxblocksize
        address = 0
        remaining = imagesize - startLPLsize
        logger.info("\nTotal size: {} start bytes: {} remaining: {}".format(imagesize, startLPLsize, remaining))
        while remaining > 0:
            if remaining < BLOCK_SIZE:
                count = remaining
            else:
                count = BLOCK_SIZE
            data = f.read(count)
            if lplonly_flag:
                fw_download_status = self.cdb.block_write_lpl(address, data)
            else:
                fw_download_status = self.cdb.block_write_epl(address, data, autopaging_flag, writelength)
            if fw_download_status != 1:
                self.cdb.abort_fw_download()
                txt += 'CDB download failed. CDB Status: %d\n' %fw_download_status
                txt += 'FW_download_status %d\n' %fw_download_status
                logger.info(txt)
                return False, txt
            elapsedtime = time.time()-starttime
            address += count
            remaining -= count
            progress = (imagesize - remaining) * 100.0 / imagesize
            logger.info('Address: {:#08x}; Count: {}; Remain: {:#08x}; Progress: {:.2f}%; Time: {:.2f}s'.format(address, count, remaining, progress, elapsedtime))

        elapsedtime = time.time()-starttime
        logger.info('Total module FW download time: %.2f s' %elapsedtime)

        time.sleep(2)
        # complete FW download (CMD 0107h)
        fw_complete_status = self.cdb.validate_fw_image()
        if fw_complete_status == 1:
            string = 'Module FW download complete: Success'
            logger.info(string)
            txt += string
        else:
            txt += 'Module FW download complete: Fail\n'
            txt += 'FW_complete_status %d\n' %fw_complete_status
            logger.info(txt)
            return False, txt
        elapsedtime = time.time()-elapsedtime-starttime
        string = 'Complete module FW download time: %.2f s\n' %elapsedtime
        logger.info(string)
        txt += string
        return True, txt

    def module_fw_upgrade(self, imagepath):
        """
        This function performs firmware upgrade.
        1.  show FW version in the beginning
        2.  check module advertised FW download capability
        3.  configure download
        4.  show download progress
        5.  configure run downloaded firmware
        6.  configure commit downloaded firmware
        7.  show FW version in the end

        imagepath specifies where firmware image file is located.
        target_firmware is a string that specifies the firmware version to upgrade to

        This function returns True if download successfully completes.
        Otherwise it will return False.
        """
        result = self.get_module_fw_info()
        try:
            _, _, _, _, _, _, _, _ = result['result']
        except (ValueError, TypeError):
            return result['status'], result['info']
        result = self.get_module_fw_mgmt_feature()
        try:
            startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength = result['result']
        except (ValueError, TypeError):
            return result['status'], result['info']
        download_status, txt = self.module_fw_download(startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength, imagepath)
        if not download_status:
            return False, txt
        switch_status, switch_txt = self.module_fw_switch()
        status = download_status and switch_status
        txt += switch_txt
        return status, txt

    def module_fw_switch(self):
        """
        This function switch the active/inactive module firmware in the current module memory
        This function returns True if firmware switch successfully completes.
        Otherwise it will return False.
        If not both images are valid, it will stop firmware switch and return False
        """
        txt = ''
        result = self.get_module_fw_info()
        try:
            (ImageA_init, ImageARunning_init, ImageACommitted_init, ImageAValid_init,
             ImageB_init, ImageBRunning_init, ImageBCommitted_init, ImageBValid_init) = result['result']
        except (ValueError, TypeError):
            return result['status'], result['info']
        if ImageAValid_init == 0 and ImageBValid_init == 0:
            self.module_fw_run(mode = 0x01)
            time.sleep(60)
            self.module_fw_commit()
            (ImageA, ImageARunning, ImageACommitted, ImageAValid,
             ImageB, ImageBRunning, ImageBCommitted, ImageBValid) = self.get_module_fw_info()['result']
            # detect if image switch happened
            txt += 'Before switch Image A: %s; Run: %d Commit: %d, Valid: %d\n' %(
                ImageA_init, ImageARunning_init, ImageACommitted_init, ImageAValid_init
            )
            txt += 'Before switch Image B: %s; Run: %d Commit: %d, Valid: %d\n' %(
                ImageB_init, ImageBRunning_init, ImageBCommitted_init, ImageBValid_init
            )
            txt += 'After switch Image A: %s; Run: %d Commit: %d, Valid: %d\n' %(ImageA, ImageARunning, ImageACommitted, ImageAValid)
            txt += 'After switch Image B: %s; Run: %d Commit: %d, Valid: %d\n' %(ImageB, ImageBRunning, ImageBCommitted, ImageBValid)
            if (ImageARunning_init == 1 and ImageARunning == 1) or (ImageBRunning_init == 1 and ImageBRunning == 1):
                txt += 'Switch did not happen.\n'
                logger.info(txt)
                return False, txt
            else:
                logger.info(txt)
                return True, txt
        else:
            txt += 'Not both images are valid.'
            logger.info(txt)
            return False, txt

    def get_transceiver_status(self):
        """
        Retrieves transceiver status of this SFP

        Returns:
            A dict which contains following keys/values :
        ================================================================================
        key                          = TRANSCEIVER_STATUS|ifname        ; Error information for module on port
        ; field                      = value
        module_state                 = 1*255VCHAR                       ; current module state (ModuleLowPwr, ModulePwrUp, ModuleReady, ModulePwrDn, Fault)
        module_fault_cause           = 1*255VCHAR                       ; reason of entering the module fault state
        datapath_firmware_fault      = BOOLEAN                          ; datapath (DSP) firmware fault
        module_firmware_fault        = BOOLEAN                          ; module firmware fault
        module_state_changed         = BOOLEAN                          ; module state changed
        datapath_hostlane1           = 1*255VCHAR                       ; data path state indicator on host lane 1
        datapath_hostlane2           = 1*255VCHAR                       ; data path state indicator on host lane 2
        datapath_hostlane3           = 1*255VCHAR                       ; data path state indicator on host lane 3
        datapath_hostlane4           = 1*255VCHAR                       ; data path state indicator on host lane 4
        datapath_hostlane5           = 1*255VCHAR                       ; data path state indicator on host lane 5
        datapath_hostlane6           = 1*255VCHAR                       ; data path state indicator on host lane 6
        datapath_hostlane7           = 1*255VCHAR                       ; data path state indicator on host lane 7
        datapath_hostlane8           = 1*255VCHAR                       ; data path state indicator on host lane 8
        txoutput_status              = BOOLEAN                          ; tx output status on media lane
        rxoutput_status_hostlane1    = BOOLEAN                          ; rx output status on host lane 1
        rxoutput_status_hostlane2    = BOOLEAN                          ; rx output status on host lane 2
        rxoutput_status_hostlane3    = BOOLEAN                          ; rx output status on host lane 3
        rxoutput_status_hostlane4    = BOOLEAN                          ; rx output status on host lane 4
        rxoutput_status_hostlane5    = BOOLEAN                          ; rx output status on host lane 5
        rxoutput_status_hostlane6    = BOOLEAN                          ; rx output status on host lane 6
        rxoutput_status_hostlane7    = BOOLEAN                          ; rx output status on host lane 7
        rxoutput_status_hostlane8    = BOOLEAN                          ; rx output status on host lane 8
        txfault                      = BOOLEAN                          ; tx fault flag on media lane
        txlos_hostlane1              = BOOLEAN                          ; tx loss of signal flag on host lane 1
        txlos_hostlane2              = BOOLEAN                          ; tx loss of signal flag on host lane 2
        txlos_hostlane3              = BOOLEAN                          ; tx loss of signal flag on host lane 3
        txlos_hostlane4              = BOOLEAN                          ; tx loss of signal flag on host lane 4
        txlos_hostlane5              = BOOLEAN                          ; tx loss of signal flag on host lane 5
        txlos_hostlane6              = BOOLEAN                          ; tx loss of signal flag on host lane 6
        txlos_hostlane7              = BOOLEAN                          ; tx loss of signal flag on host lane 7
        txlos_hostlane8              = BOOLEAN                          ; tx loss of signal flag on host lane 8
        txcdrlol_hostlane1           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 1
        txcdrlol_hostlane2           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 2
        txcdrlol_hostlane3           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 3
        txcdrlol_hostlane4           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 4
        txcdrlol_hostlane5           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 5
        txcdrlol_hostlane6           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 6
        txcdrlol_hostlane7           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 7
        txcdrlol_hostlane8           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 8
        rxlos                        = BOOLEAN                          ; rx loss of signal flag on media lane
        rxcdrlol                     = BOOLEAN                          ; rx clock and data recovery loss of lock on media lane
        config_state_hostlane1       = 1*255VCHAR                       ; configuration status for the data path of host line 1
        config_state_hostlane2       = 1*255VCHAR                       ; configuration status for the data path of host line 2
        config_state_hostlane3       = 1*255VCHAR                       ; configuration status for the data path of host line 3
        config_state_hostlane4       = 1*255VCHAR                       ; configuration status for the data path of host line 4
        config_state_hostlane5       = 1*255VCHAR                       ; configuration status for the data path of host line 5
        config_state_hostlane6       = 1*255VCHAR                       ; configuration status for the data path of host line 6
        config_state_hostlane7       = 1*255VCHAR                       ; configuration status for the data path of host line 7
        config_state_hostlane8       = 1*255VCHAR                       ; configuration status for the data path of host line 8
        dpinit_pending_hostlane1     = BOOLEAN                          ; data path configuration updated on host lane 1
        dpinit_pending_hostlane2     = BOOLEAN                          ; data path configuration updated on host lane 2
        dpinit_pending_hostlane3     = BOOLEAN                          ; data path configuration updated on host lane 3
        dpinit_pending_hostlane4     = BOOLEAN                          ; data path configuration updated on host lane 4
        dpinit_pending_hostlane5     = BOOLEAN                          ; data path configuration updated on host lane 5
        dpinit_pending_hostlane6     = BOOLEAN                          ; data path configuration updated on host lane 6
        dpinit_pending_hostlane7     = BOOLEAN                          ; data path configuration updated on host lane 7
        dpinit_pending_hostlane8     = BOOLEAN                          ; data path configuration updated on host lane 8
        temphighalarm_flag           = BOOLEAN                          ; temperature high alarm flag
        temphighwarning_flag         = BOOLEAN                          ; temperature high warning flag
        templowalarm_flag            = BOOLEAN                          ; temperature low alarm flag
        templowwarning_flag          = BOOLEAN                          ; temperature low warning flag
        vcchighalarm_flag            = BOOLEAN                          ; vcc high alarm flag
        vcchighwarning_flag          = BOOLEAN                          ; vcc high warning flag
        vcclowalarm_flag             = BOOLEAN                          ; vcc low alarm flag
        vcclowwarning_flag           = BOOLEAN                          ; vcc low warning flag
        txpowerhighalarm_flag        = BOOLEAN                          ; tx power high alarm flag
        txpowerlowalarm_flag         = BOOLEAN                          ; tx power low alarm flag
        txpowerhighwarning_flag      = BOOLEAN                          ; tx power high warning flag
        txpowerlowwarning_flag       = BOOLEAN                          ; tx power low alarm flag
        rxpowerhighalarm_flag        = BOOLEAN                          ; rx power high alarm flag
        rxpowerlowalarm_flag         = BOOLEAN                          ; rx power low alarm flag
        rxpowerhighwarning_flag      = BOOLEAN                          ; rx power high warning flag
        rxpowerlowwarning_flag       = BOOLEAN                          ; rx power low warning flag
        txbiashighalarm_flag         = BOOLEAN                          ; tx bias high alarm flag
        txbiaslowalarm_flag          = BOOLEAN                          ; tx bias low alarm flag
        txbiashighwarning_flag       = BOOLEAN                          ; tx bias high warning flag
        txbiaslowwarning_flag        = BOOLEAN                          ; tx bias low warning flag
        lasertemphighalarm_flag      = BOOLEAN                          ; laser temperature high alarm flag
        lasertemplowalarm_flag       = BOOLEAN                          ; laser temperature low alarm flag
        lasertemphighwarning_flag    = BOOLEAN                          ; laser temperature high warning flag
        lasertemplowwarning_flag     = BOOLEAN                          ; laser temperature low warning flag
        prefecberhighalarm_flag      = BOOLEAN                          ; prefec ber high alarm flag
        prefecberlowalarm_flag       = BOOLEAN                          ; prefec ber low alarm flag
        prefecberhighwarning_flag    = BOOLEAN                          ; prefec ber high warning flag
        prefecberlowwarning_flag     = BOOLEAN                          ; prefec ber low warning flag
        postfecberhighalarm_flag     = BOOLEAN                          ; postfec ber high alarm flag
        postfecberlowalarm_flag      = BOOLEAN                          ; postfec ber low alarm flag
        postfecberhighwarning_flag   = BOOLEAN                          ; postfec ber high warning flag
        postfecberlowwarning_flag    = BOOLEAN                          ; postfec ber low warning flag
        ================================================================================
        """
        trans_status = dict()
        trans_status['module_state'] = self.get_module_state()
        trans_status['module_fault_cause'] = self.get_module_fault_cause()
        try:
            dp_fw_fault, module_fw_fault, module_state_changed = self.get_module_firmware_fault_state_changed()
            trans_status['datapath_firmware_fault'] = dp_fw_fault
            trans_status['module_firmware_fault'] = module_fw_fault
            trans_status['module_state_changed'] = module_state_changed
        except TypeError:
            pass
        module_flag = self.get_module_level_flag()
        trans_status['temphighalarm_flag'] = module_flag['case_temp_flags']['case_temp_high_alarm_flag']
        trans_status['templowalarm_flag'] = module_flag['case_temp_flags']['case_temp_low_alarm_flag']
        trans_status['temphighwarning_flag'] = module_flag['case_temp_flags']['case_temp_high_warn_flag']
        trans_status['templowwarning_flag'] = module_flag['case_temp_flags']['case_temp_low_warn_flag']
        trans_status['vcchighalarm_flag'] = module_flag['voltage_flags']['voltage_high_alarm_flag']
        trans_status['vcclowalarm_flag'] = module_flag['voltage_flags']['voltage_low_alarm_flag']
        trans_status['vcchighwarning_flag'] = module_flag['voltage_flags']['voltage_high_warn_flag']
        trans_status['vcclowwarning_flag'] = module_flag['voltage_flags']['voltage_low_warn_flag']
        try:
            aux1_mon_type, aux2_mon_type, aux3_mon_type = self.get_aux_mon_type()
            if aux2_mon_type == 0:
                trans_status['lasertemphighalarm_flag'] = module_flag['aux2_flags']['aux2_high_alarm_flag']
                trans_status['lasertemplowalarm_flag'] = module_flag['aux2_flags']['aux2_low_alarm_flag']
                trans_status['lasertemphighwarning_flag'] = module_flag['aux2_flags']['aux2_high_warn_flag']
                trans_status['lasertemplowwarning_flag'] = module_flag['aux2_flags']['aux2_low_warn_flag']
            elif aux2_mon_type == 1 and aux3_mon_type == 0:
                trans_status['lasertemphighalarm_flag'] = module_flag['aux3_flags']['aux3_high_alarm_flag']
                trans_status['lasertemplowalarm_flag'] = module_flag['aux3_flags']['aux3_low_alarm_flag']
                trans_status['lasertemphighwarning_flag'] = module_flag['aux3_flags']['aux3_high_warn_flag']
                trans_status['lasertemplowwarning_flag'] = module_flag['aux3_flags']['aux3_low_warn_flag']
        except TypeError:
            pass
        if not self.is_flat_memory():
            dp_state_dict = self.get_datapath_state()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['DP%dState' % lane] = dp_state_dict['DP%dState' % lane]
            tx_output_status_dict = self.get_tx_output_status()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['txoutput_status%d' % lane] = tx_output_status_dict['TxOutputStatus%d' % lane]
            rx_output_status_dict = self.get_rx_output_status()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['rxoutput_status_hostlane%d' % lane] = rx_output_status_dict['RxOutputStatus%d' % lane]
            tx_fault = self.get_tx_fault()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['txfault%d' % lane] = tx_fault[lane - 1]
            tx_los = self.get_tx_los()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['txlos_hostlane%d' % lane] = tx_los[lane - 1]
            tx_lol = self.get_tx_cdr_lol()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['txcdrlol_hostlane%d' % lane] = tx_lol[lane - 1]
            rx_los = self.get_rx_los()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['rxlos%d' % lane] = rx_los[lane - 1]
            rx_lol = self.get_rx_cdr_lol()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['rxcdrlol%d' % lane] = rx_lol[lane - 1]
            config_status_dict = self.get_config_datapath_hostlane_status()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['config_state_hostlane%d' % lane] = config_status_dict['ConfigStatusLane%d' % lane]
            dpinit_pending_dict = self.get_dpinit_pending()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['dpinit_pending_hostlane%d' % lane] = dpinit_pending_dict['DPInitPending%d' % lane]
            tx_power_flag_dict = self.get_tx_power_flag()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['txpowerhighalarm_flag%d' % lane] = tx_power_flag_dict['tx_power_high_alarm']['TxPowerHighAlarmFlag%d' % lane]
                trans_status['txpowerlowalarm_flag%d' % lane] = tx_power_flag_dict['tx_power_low_alarm']['TxPowerLowAlarmFlag%d' % lane]
                trans_status['txpowerhighwarning_flag%d' % lane] = tx_power_flag_dict['tx_power_high_warn']['TxPowerHighWarnFlag%d' % lane]
                trans_status['txpowerlowwarning_flag%d' % lane] = tx_power_flag_dict['tx_power_low_warn']['TxPowerLowWarnFlag%d' % lane]
            rx_power_flag_dict = self.get_rx_power_flag()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['rxpowerhighalarm_flag%d' % lane] = rx_power_flag_dict['rx_power_high_alarm']['RxPowerHighAlarmFlag%d' % lane]
                trans_status['rxpowerlowalarm_flag%d' % lane] = rx_power_flag_dict['rx_power_low_alarm']['RxPowerLowAlarmFlag%d' % lane]
                trans_status['rxpowerhighwarning_flag%d' % lane] = rx_power_flag_dict['rx_power_high_warn']['RxPowerHighWarnFlag%d' % lane]
                trans_status['rxpowerlowwarning_flag%d' % lane] = rx_power_flag_dict['rx_power_low_warn']['RxPowerLowWarnFlag%d' % lane]
            tx_bias_flag_dict = self.get_tx_bias_flag()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_status['txbiashighalarm_flag%d' % lane] = tx_bias_flag_dict['tx_bias_high_alarm']['TxBiasHighAlarmFlag%d' % lane]
                trans_status['txbiaslowalarm_flag%d' % lane] = tx_bias_flag_dict['tx_bias_low_alarm']['TxBiasLowAlarmFlag%d' % lane]
                trans_status['txbiashighwarning_flag%d' % lane] = tx_bias_flag_dict['tx_bias_high_warn']['TxBiasHighWarnFlag%d' % lane]
                trans_status['txbiaslowwarning_flag%d' % lane] = tx_bias_flag_dict['tx_bias_low_warn']['TxBiasLowWarnFlag%d' % lane]
            self.vdm_dict = self.get_vdm()
            try:
                trans_status['prefecberhighalarm_flag'] = self.vdm_dict['Pre-FEC BER Average Media Input'][1][5]
                trans_status['prefecberlowalarm_flag'] = self.vdm_dict['Pre-FEC BER Average Media Input'][1][6]
                trans_status['prefecberhighwarning_flag'] = self.vdm_dict['Pre-FEC BER Average Media Input'][1][7]
                trans_status['prefecberlowwarning_flag'] = self.vdm_dict['Pre-FEC BER Average Media Input'][1][8]
                trans_status['postfecberhighalarm_flag'] = self.vdm_dict['Errored Frames Average Media Input'][1][5]
                trans_status['postfecberlowalarm_flag'] = self.vdm_dict['Errored Frames Average Media Input'][1][6]
                trans_status['postfecberhighwarning_flag'] = self.vdm_dict['Errored Frames Average Media Input'][1][7]
                trans_status['postfecberlowwarning_flag'] = self.vdm_dict['Errored Frames Average Media Input'][1][8]
            except (KeyError, TypeError):
                pass
        return trans_status

    def get_transceiver_loopback(self):
        """
        Retrieves loopback mode for this xcvr

        Returns:
            A dict containing the following keys/values :
        ========================================================================
        key                          = TRANSCEIVER_PM|ifname            ; information of loopback on port
        ; field                      = value
        media_output_loopback        = BOOLEAN                          ; media side output loopback enable
        media_input_loopback         = BOOLEAN                          ; media side input loopback enable
        host_output_loopback_lane1   = BOOLEAN                          ; host side output loopback enable lane1
        host_output_loopback_lane2   = BOOLEAN                          ; host side output loopback enable lane2
        host_output_loopback_lane3   = BOOLEAN                          ; host side output loopback enable lane3
        host_output_loopback_lane4   = BOOLEAN                          ; host side output loopback enable lane4
        host_output_loopback_lane5   = BOOLEAN                          ; host side output loopback enable lane5
        host_output_loopback_lane6   = BOOLEAN                          ; host side output loopback enable lane6
        host_output_loopback_lane7   = BOOLEAN                          ; host side output loopback enable lane7
        host_output_loopback_lane8   = BOOLEAN                          ; host side output loopback enable lane8
        host_input_loopback_lane1   = BOOLEAN                          ; host side input loopback enable lane1
        host_input_loopback_lane2   = BOOLEAN                          ; host side input loopback enable lane2
        host_input_loopback_lane3   = BOOLEAN                          ; host side input loopback enable lane3
        host_input_loopback_lane4   = BOOLEAN                          ; host side input loopback enable lane4
        host_input_loopback_lane5   = BOOLEAN                          ; host side input loopback enable lane5
        host_input_loopback_lane6   = BOOLEAN                          ; host side input loopback enable lane6
        host_input_loopback_lane7   = BOOLEAN                          ; host side input loopback enable lane7
        host_input_loopback_lane8   = BOOLEAN                          ; host side input loopback enable lane8
        ========================================================================
        """
        trans_loopback = dict()
        loopback_capability = self.get_loopback_capability()
        if loopback_capability is None:
            trans_loopback['simultaneous_host_media_loopback_supported'] = 'N/A'
            trans_loopback['per_lane_media_loopback_supported'] = 'N/A'
            trans_loopback['per_lane_host_loopback_supported'] = 'N/A'
            trans_loopback['host_side_input_loopback_supported'] = 'N/A'
            trans_loopback['host_side_output_loopback_supported'] = 'N/A'
            trans_loopback['media_side_input_loopback_supported'] = 'N/A'
            trans_loopback['media_side_output_loopback_supported'] = 'N/A'
            trans_loopback['media_output_loopback'] = 'N/A'
            trans_loopback['media_input_loopback'] = 'N/A'
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_loopback['host_output_loopback_lane%d' % lane] = 'N/A'
                trans_loopback['host_input_loopback_lane%d' % lane] = 'N/A'
            return trans_loopback
        else:
            trans_loopback['simultaneous_host_media_loopback_supported'] = loopback_capability['simultaneous_host_media_loopback_supported']
            trans_loopback['per_lane_media_loopback_supported'] = loopback_capability['per_lane_media_loopback_supported']
            trans_loopback['per_lane_host_loopback_supported'] = loopback_capability['per_lane_host_loopback_supported']
            trans_loopback['host_side_input_loopback_supported'] = loopback_capability['host_side_input_loopback_supported']
            trans_loopback['host_side_output_loopback_supported'] = loopback_capability['host_side_output_loopback_supported']
            trans_loopback['media_side_input_loopback_supported'] = loopback_capability['media_side_input_loopback_supported']
            trans_loopback['media_side_output_loopback_supported'] = loopback_capability['media_side_output_loopback_supported']
        if loopback_capability['media_side_output_loopback_supported']:
            trans_loopback['media_output_loopback'] = self.get_media_output_loopback()
        else:
            trans_loopback['media_output_loopback'] = 'N/A'
        if loopback_capability['media_side_input_loopback_supported']:
            trans_loopback['media_input_loopback'] = self.get_media_input_loopback()
        else:
            trans_loopback['media_input_loopback'] = 'N/A'
        if loopback_capability['host_side_output_loopback_supported']:
            host_output_loopback_status = self.get_host_output_loopback()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_loopback['host_output_loopback_lane%d' % lane] = host_output_loopback_status[lane - 1]
        else:
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_loopback['host_output_loopback_lane%d' % lane] = 'N/A'
        if loopback_capability['host_side_input_loopback_supported']:
            host_input_loopback_status = self.get_host_input_loopback()
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_loopback['host_input_loopback_lane%d' % lane] = host_input_loopback_status[lane - 1]
        else:
            for lane in range(1, self.NUM_CHANNELS+1):
                trans_loopback['host_input_loopback_lane%d' % lane] = 'N/A'
        return trans_loopback

    def set_datapath_init(self, channel):
        """
        Put the CMIS datapath into the initialized state

        Args:
            channel:
                Integer, a bitmask of the lanes on the host side
                e.g. 0x5 for lane 0 and lane 2.

        Returns:
            Boolean, true if success otherwise false
        """
        cmis_major = self.xcvr_eeprom.read(consts.CMIS_MAJOR_REVISION)
        data = self.xcvr_eeprom.read(consts.DATAPATH_DEINIT_FIELD)
        for lane in range(self.NUM_CHANNELS):
            if ((1 << lane) & channel) == 0:
                continue
            if cmis_major >= 4: # CMIS v4 onwards
                data &= ~(1 << lane)
            else:               # CMIS v3
                data |= (1 << lane)
        self.xcvr_eeprom.write(consts.DATAPATH_DEINIT_FIELD, data)

    def set_datapath_deinit(self, channel):
        """
        Put the CMIS datapath into the de-initialized state

        Args:
            channel:
                Integer, a bitmask of the lanes on the host side
                e.g. 0x5 for lane 0 and lane 2.

        Returns:
            Boolean, true if success otherwise false
        """
        cmis_major = self.xcvr_eeprom.read(consts.CMIS_MAJOR_REVISION)
        data = self.xcvr_eeprom.read(consts.DATAPATH_DEINIT_FIELD)
        for lane in range(self.NUM_CHANNELS):
            if ((1 << lane) & channel) == 0:
                continue
            if cmis_major >= 4: # CMIS v4 onwards
                data |= (1 << lane)
            else:               # CMIS v3
                data &= ~(1 << lane)
        self.xcvr_eeprom.write(consts.DATAPATH_DEINIT_FIELD, data)

    def get_application_advertisement(self):
        """
        Get the application advertisement of the CMIS transceiver

        Returns:
            Dictionary, the application advertisement
        """
        map = {
            Sff8024.MODULE_MEDIA_TYPE[1]: consts.MODULE_MEDIA_INTERFACE_850NM,
            Sff8024.MODULE_MEDIA_TYPE[2]: consts.MODULE_MEDIA_INTERFACE_SM,
            Sff8024.MODULE_MEDIA_TYPE[3]: consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER,
            Sff8024.MODULE_MEDIA_TYPE[4]: consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE,
            Sff8024.MODULE_MEDIA_TYPE[5]: consts.MODULE_MEDIA_INTERFACE_BASE_T
        }

        ret = {}
        # Read the application advertisment in lower memory
        dic = self.xcvr_eeprom.read(consts.APPLS_ADVT_FIELD)

        if not self.is_flat_memory():
            # Read the application advertisement in page01
            try:
                dic.update(self.xcvr_eeprom.read(consts.APPLS_ADVT_FIELD_PAGE01))
            except (TypeError, AttributeError) as e:
                logger.error('Failed to read APPLS_ADVT_FIELD_PAGE01: ' + str(e))
                return ret

        for app in range(1, 16):
            buf = {}

            key = "{}_{}".format(consts.HOST_ELECTRICAL_INTERFACE, app)
            val = dic.get(key)
            if val in [None, 'Unknown', 'Undefined']:
                break
            buf['host_electrical_interface_id'] = val

            prefix = map.get(self.xcvr_eeprom.read(consts.MEDIA_TYPE_FIELD))
            if prefix is None:
                break
            key = "{}_{}".format(prefix, app)
            val = dic.get(key)
            if val in [None, 'Unknown', 'Undefined']:
                break
            buf['module_media_interface_id'] = val

            key = "{}_{}".format(consts.MEDIA_LANE_COUNT, app)
            val = dic.get(key)
            if val is None:
                break
            buf['media_lane_count'] = val

            key = "{}_{}".format(consts.HOST_LANE_COUNT, app)
            val = dic.get(key)
            if val is None:
                break
            buf['host_lane_count'] = val

            key = "{}_{}".format(consts.HOST_LANE_ASSIGNMENT_OPTION, app)
            val = dic.get(key)
            if val is None:
                break
            buf['host_lane_assignment_options'] = val

            key = "{}_{}".format(consts.MEDIA_LANE_ASSIGNMENT_OPTION, app)
            val = dic.get(key)
            if val is not None:
                buf['media_lane_assignment_options'] = val

            ret[app] = buf
        return ret

    def get_application(self, lane):
        """
        Get the CMIS selected application code of a host lane

        Args:
            lane:
                Integer, the zero-based lane id on the host side

        Returns:
            Integer, the transceiver-specific application code
        """
        appl = 0
        if lane in range(self.NUM_CHANNELS) and not self.is_flat_memory():
            name = "{}_{}_{}".format(consts.STAGED_CTRL_APSEL_FIELD, 0, lane + 1)
            appl = self.xcvr_eeprom.read(name) >> 4

        return (appl & 0xf)

    def set_application(self, channel, appl_code):
        """
        Update the selected application code to the specified lanes on the host side

        Args:
            channel:
                Integer, a bitmask of the lanes on the host side
                e.g. 0x5 for lane 0 and lane 2.
            appl_code:
                Integer, the desired application code

        Returns:
            Boolean, true if success otherwise false
        """
        # Update the application selection
        lane_first = -1
        for lane in range(self.NUM_CHANNELS):
            if ((1 << lane) & channel) == 0:
                continue
            if lane_first < 0:
                lane_first = lane
            addr = "{}_{}_{}".format(consts.STAGED_CTRL_APSEL_FIELD, 0, lane + 1)
            data = (appl_code << 4) | (lane_first << 1)
            self.xcvr_eeprom.write(addr, data)

        # Apply DataPathInit
        return self.xcvr_eeprom.write("%s_%d" % (consts.STAGED_CTRL_APPLY_DPINIT_FIELD, 0), channel)

    def get_error_description(self):
        dp_state = self.get_datapath_state()
        conf_state = self.get_config_datapath_hostlane_status()
        for lane in range(self.NUM_CHANNELS):
            name = "{}_{}_{}".format(consts.STAGED_CTRL_APSEL_FIELD, 0, lane + 1)
            appl = self.xcvr_eeprom.read(name)
            if (appl is None) or ((appl >> 4) == 0):
                continue

            name = "DP{}State".format(lane + 1)
            if dp_state[name] != CmisCodes.DATAPATH_STATE[4]:
                return dp_state[name]

            name = "ConfigStatusLane{}".format(lane + 1)
            if conf_state[name] != CmisCodes.CONFIG_STATUS[1]:
                return conf_state[name]

        state = self.get_module_state()
        if state != CmisCodes.MODULE_STATE[3]:
            return state

        return None

    # TODO: other XcvrApi methods
