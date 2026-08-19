"""
CMIS API for CPO hardware.

In CPO hardware, a single optical engine may be shared by multiple physical ports.
As a result, a daemon like xcvrd might want to only read non-banked information
once per device instead of once per port in order to avoid wasting i2c read bandwidth.
Banked information can be read once per port, since each port will typically have its
own bank.

This subclass splits aggregate methods into two constituents:
    - a function that reads banked information
    - a function that reads non-banked information.

This allows xcvrd to selectively read banked and non-banked information separately
when required for CPO hardware.
"""

import copy

from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.fields import consts

# Transceiver info fields that reside on banked pages and therefore vary by bank.
CPO_XCVR_INFO_BANKED_DEFAULT_DICT = {
        **{f"active_apsel_hostlane{i}": "N/A" for i in range(1, 9)}
        }

# Transceiver info fields that reside on non-banked pages and do not vary by bank.
CPO_XCVR_INFO_NON_BANKED_DEFAULT_DICT = {
        "type": "N/A",
        "type_abbrv_name": "N/A",
        "hardware_rev": "N/A",
        "serial": "N/A",
        "manufacturer": "N/A",
        "model": "N/A",
        "connector": "N/A",
        "encoding": "N/A",
        "ext_identifier": "N/A",
        "ext_rateselect_compliance": "N/A",
        "cable_length": "N/A",
        "nominal_bit_rate": "N/A",
        "vendor_date": "N/A",
        "vendor_oui": "N/A",
        "application_advertisement": "N/A",
        "host_lane_count": "N/A",
        "media_lane_count": "N/A",
        "cable_type": "N/A",
        "media_interface_technology": "N/A",
        "vendor_rev": "N/A",
        "cmis_rev": "N/A",
        "specification_compliance": "N/A",
        "vdm_supported": "N/A"
        }


class CpoCmisApi(CmisApi):
    def get_non_banked_transceiver_info(self):
        admin_info = self.xcvr_eeprom.read(consts.ADMIN_INFO_FIELD)
        if admin_info is None:
            return None

        ext_id = admin_info[consts.EXT_ID_FIELD]
        power_class = ext_id[consts.POWER_CLASS_FIELD]
        max_power = ext_id[consts.MAX_POWER_FIELD]
        xcvr_info = copy.deepcopy(CPO_XCVR_INFO_NON_BANKED_DEFAULT_DICT)
        xcvr_info.update({
            "type": admin_info[consts.ID_FIELD],
            "type_abbrv_name": admin_info[consts.ID_ABBRV_FIELD],
            "hardware_rev": self.get_module_hardware_revision(),
            "serial": self._strip_str(admin_info[consts.VENDOR_SERIAL_NO_FIELD]),
            "manufacturer": self._strip_str(admin_info[consts.VENDOR_NAME_FIELD]),
            "model": self._strip_str(admin_info[consts.VENDOR_PART_NO_FIELD]),
            "connector": admin_info[consts.CONNECTOR_FIELD],
            "ext_identifier": "%s (%sW Max)" % (power_class, max_power),
            "cable_length": float(admin_info[consts.LENGTH_ASSEMBLY_FIELD]),
            "vendor_date": self._strip_str(admin_info[consts.VENDOR_DATE_FIELD]),
            "vendor_oui": admin_info[consts.VENDOR_OUI_FIELD],
            "application_advertisement": str(self.get_application_advertisement()) if len(self.get_application_advertisement()) > 0 else 'N/A',
            "host_lane_count": self.get_host_lane_count(),
            "media_lane_count": self.get_media_lane_count(),
            "cable_type": self.get_cable_length_type(),
            "media_interface_technology": self.get_media_interface_technology(),
            "vendor_rev": self._strip_str(self.get_vendor_rev()),
            "cmis_rev": self.get_cmis_rev(),
            "specification_compliance": self.get_module_media_type(),
            "vdm_supported": self.is_transceiver_vdm_supported()
        })

        # In normal case will get a valid value for each of the fields. If get a 'None' value
        # means there was a failure while reading the EEPROM, either because the EEPROM was
        # not ready yet or experiencing some other issues. It shouldn't return a dict with a
        # wrong field value, instead should return a 'None' to indicate to XCVRD that retry is
        # needed.
        if None in xcvr_info.values():
            return None
        else:
            return xcvr_info

    def get_banked_transceiver_info(self):
        xcvr_info = copy.deepcopy(CPO_XCVR_INFO_BANKED_DEFAULT_DICT)
        apsel_dict = self.get_active_apsel_hostlane()
        for lane in range(1, self.NUM_CHANNELS + 1):
            xcvr_info["%s%d" % ("active_apsel_hostlane", lane)] = \
            apsel_dict["%s%d" % (consts.ACTIVE_APSEL_HOSTLANE, lane)]

        if None in xcvr_info.values():
            return None
        else:
            return xcvr_info

    def get_transceiver_info(self):
        xcvr_info = self.get_non_banked_transceiver_info()
        if xcvr_info is None:
            return None

        banked_xcvr_info = self.get_banked_transceiver_info()
        if banked_xcvr_info is None:
            return None

        xcvr_info.update(banked_xcvr_info)
        return xcvr_info

    def get_non_banked_transceiver_dom_real_value(self):
        temp = self.get_module_temperature()
        voltage = self.get_voltage()
        if temp is None or voltage is None:
            return None

        bulk_status = {
            "temperature": temp,
            "voltage": voltage
        }

        laser_temp_dict = self.get_laser_temperature()
        try:
            bulk_status['laser_temperature'] = laser_temp_dict['monitor value']
        except (KeyError, TypeError):
            pass

        return bulk_status

    def get_banked_transceiver_dom_real_value(self):
        tx_bias = self.get_tx_bias()
        rx_power = self.get_rx_power()
        tx_power = self.get_tx_power()
        if tx_bias is None or rx_power is None or tx_power is None:
            return None

        bulk_status = dict()
        for i in range(1, self.NUM_CHANNELS + 1):
            bulk_status["tx%dbias" % i] = tx_bias[i - 1]
            bulk_status["rx%dpower" % i] = float("{:.3f}".format(self.mw_to_dbm(rx_power[i - 1]))) if rx_power[i - 1] != 'N/A' else 'N/A'
            bulk_status["tx%dpower" % i] = float("{:.3f}".format(self.mw_to_dbm(tx_power[i - 1]))) if tx_power[i - 1] != 'N/A' else 'N/A'

        return bulk_status

    def get_transceiver_dom_real_value(self):
        bulk_status = self.get_non_banked_transceiver_dom_real_value()
        if bulk_status is None:
            return None

        banked_bulk_status = self.get_banked_transceiver_dom_real_value()
        if banked_bulk_status is None:
            return None

        bulk_status.update(banked_bulk_status)
        return bulk_status

    def get_non_banked_transceiver_dom_flags(self):
        dom_flag_dict = dict()
        module_flag = self.get_module_level_flag()

        try:
            case_temp_flags = module_flag['case_temp_flags']
            voltage_flags = module_flag['voltage_flags']
            dom_flag_dict.update({
                'tempHAlarm': case_temp_flags['case_temp_high_alarm_flag'],
                'tempLAlarm': case_temp_flags['case_temp_low_alarm_flag'],
                'tempHWarn': case_temp_flags['case_temp_high_warn_flag'],
                'tempLWarn': case_temp_flags['case_temp_low_warn_flag'],
                'vccHAlarm': voltage_flags['voltage_high_alarm_flag'],
                'vccLAlarm': voltage_flags['voltage_low_alarm_flag'],
                'vccHWarn': voltage_flags['voltage_high_warn_flag'],
                'vccLWarn': voltage_flags['voltage_low_warn_flag']
            })
        except TypeError:
            pass
        try:
            _, aux2_mon_type, aux3_mon_type = self.get_aux_mon_type()
            if aux2_mon_type == 0:
                dom_flag_dict['lasertempHAlarm'] = module_flag['aux2_flags']['aux2_high_alarm_flag']
                dom_flag_dict['lasertempLAlarm'] = module_flag['aux2_flags']['aux2_low_alarm_flag']
                dom_flag_dict['lasertempHWarn'] = module_flag['aux2_flags']['aux2_high_warn_flag']
                dom_flag_dict['lasertempLWarn'] = module_flag['aux2_flags']['aux2_low_warn_flag']
            elif aux2_mon_type == 1 and aux3_mon_type == 0:
                dom_flag_dict['lasertempHAlarm'] = module_flag['aux3_flags']['aux3_high_alarm_flag']
                dom_flag_dict['lasertempLAlarm'] = module_flag['aux3_flags']['aux3_low_alarm_flag']
                dom_flag_dict['lasertempHWarn'] = module_flag['aux3_flags']['aux3_high_warn_flag']
                dom_flag_dict['lasertempLWarn'] = module_flag['aux3_flags']['aux3_low_warn_flag']
        except TypeError:
            pass

        return dom_flag_dict

    def get_banked_transceiver_dom_flags(self):
        dom_flag_dict = dict()
        if not self.is_flat_memory():
            tx_power_flag_dict = self.get_tx_power_flag()
            if tx_power_flag_dict:
                for lane in range(1, self.NUM_CHANNELS+1):
                    dom_flag_dict['tx%dpowerHAlarm' % lane] = tx_power_flag_dict['tx_power_high_alarm']['TxPowerHighAlarmFlag%d' % lane]
                    dom_flag_dict['tx%dpowerLAlarm' % lane] = tx_power_flag_dict['tx_power_low_alarm']['TxPowerLowAlarmFlag%d' % lane]
                    dom_flag_dict['tx%dpowerHWarn' % lane] = tx_power_flag_dict['tx_power_high_warn']['TxPowerHighWarnFlag%d' % lane]
                    dom_flag_dict['tx%dpowerLWarn' % lane] = tx_power_flag_dict['tx_power_low_warn']['TxPowerLowWarnFlag%d' % lane]
            rx_power_flag_dict = self.get_rx_power_flag()
            if rx_power_flag_dict:
                for lane in range(1, self.NUM_CHANNELS+1):
                    dom_flag_dict['rx%dpowerHAlarm' % lane] = rx_power_flag_dict['rx_power_high_alarm']['RxPowerHighAlarmFlag%d' % lane]
                    dom_flag_dict['rx%dpowerLAlarm' % lane] = rx_power_flag_dict['rx_power_low_alarm']['RxPowerLowAlarmFlag%d' % lane]
                    dom_flag_dict['rx%dpowerHWarn' % lane] = rx_power_flag_dict['rx_power_high_warn']['RxPowerHighWarnFlag%d' % lane]
                    dom_flag_dict['rx%dpowerLWarn' % lane] = rx_power_flag_dict['rx_power_low_warn']['RxPowerLowWarnFlag%d' % lane]
            tx_bias_flag_dict = self.get_tx_bias_flag()
            if tx_bias_flag_dict:
                for lane in range(1, self.NUM_CHANNELS+1):
                    dom_flag_dict['tx%dbiasHAlarm' % lane] = tx_bias_flag_dict['tx_bias_high_alarm']['TxBiasHighAlarmFlag%d' % lane]
                    dom_flag_dict['tx%dbiasLAlarm' % lane] = tx_bias_flag_dict['tx_bias_low_alarm']['TxBiasLowAlarmFlag%d' % lane]
                    dom_flag_dict['tx%dbiasHWarn' % lane] = tx_bias_flag_dict['tx_bias_high_warn']['TxBiasHighWarnFlag%d' % lane]
                    dom_flag_dict['tx%dbiasLWarn' % lane] = tx_bias_flag_dict['tx_bias_low_warn']['TxBiasLowWarnFlag%d' % lane]

        return dom_flag_dict

    def get_transceiver_dom_flags(self):
        dom_flag_dict = self.get_non_banked_transceiver_dom_flags()
        dom_flag_dict.update(self.get_banked_transceiver_dom_flags())
        return dom_flag_dict

    def get_non_banked_transceiver_status(self):
        trans_status = dict()
        trans_status['module_state'] = self.get_module_state()
        trans_status['module_fault_cause'] = self.get_module_fault_cause()
        return trans_status

    def get_banked_transceiver_status(self):
        trans_status = dict()
        if not self.is_flat_memory():
            dp_state_dict = self.get_datapath_state()
            if dp_state_dict:
                for lane in range(1, self.NUM_CHANNELS+1):
                    trans_status['DP%dState' % lane] = dp_state_dict.get('DP%dState' % lane)
            tx_output_status_dict = self.get_tx_output_status()
            if tx_output_status_dict:
                for lane in range(1, self.NUM_CHANNELS+1):
                    trans_status['tx%dOutputStatus' % lane] = tx_output_status_dict.get('TxOutputStatus%d' % lane)
            rx_output_status_dict = self.get_rx_output_status()
            if rx_output_status_dict:
                for lane in range(1, self.NUM_CHANNELS+1):
                    trans_status['rx%dOutputStatusHostlane' % lane] = rx_output_status_dict.get('RxOutputStatus%d' % lane)
            tx_disabled_channel = self.get_tx_disable_channel()
            if tx_disabled_channel is not None:
                trans_status['tx_disabled_channel'] = tx_disabled_channel
            tx_disable = self.get_tx_disable()
            if tx_disable is not None:
                for lane in range(1, self.NUM_CHANNELS+1):
                    trans_status['tx%ddisable' % lane] = tx_disable[lane - 1]
            config_status_dict = self.get_config_datapath_hostlane_status()
            if config_status_dict:
                for lane in range(1, self.NUM_CHANNELS+1):
                    trans_status['config_state_hostlane%d' % lane] = config_status_dict.get('ConfigStatusLane%d' % lane)
            dedeint_hostlane = self.get_datapath_deinit()
            if dedeint_hostlane is not None:
                for lane in range(1, self.NUM_CHANNELS+1):
                    trans_status['dpdeinit_hostlane%d' % lane] = dedeint_hostlane[lane - 1]
            dpinit_pending_dict = self.get_dpinit_pending()
            if dpinit_pending_dict:
                for lane in range(1, self.NUM_CHANNELS+1):
                    trans_status['dpinit_pending_hostlane%d' % lane] = dpinit_pending_dict.get('DPInitPending%d' % lane)
        return trans_status

    def get_transceiver_status(self):
        trans_status = self.get_non_banked_transceiver_status()
        trans_status.update(self.get_banked_transceiver_status())
        return trans_status

    def get_non_banked_transceiver_status_flags(self):
        status_flags_dict = dict()
        try:
            dp_fw_fault, module_fw_fault, module_state_changed = self.get_module_firmware_fault_state_changed()
            status_flags_dict.update({
                'datapath_firmware_fault': dp_fw_fault,
                'module_firmware_fault': module_fw_fault,
                'module_state_changed': module_state_changed
            })
        except TypeError:
            pass

        return status_flags_dict

    def get_banked_transceiver_status_flags(self):
        status_flags_dict = dict()
        if not self.is_flat_memory():
            fault_types = {
                'tx{lane_num}fault': self.get_tx_fault(),
                'rx{lane_num}los': self.get_rx_los(),
                'tx{lane_num}los_hostlane': self.get_tx_los(),
                'tx{lane_num}cdrlol_hostlane': self.get_tx_cdr_lol(),
                'tx{lane_num}_eq_fault': self.get_tx_adaptive_eq_fail_flag(),
                'rx{lane_num}cdrlol': self.get_rx_cdr_lol()
            }

            for fault_type_template, fault_values in fault_types.items():
                for lane in range(1, self.NUM_CHANNELS + 1):
                    key = fault_type_template.format(lane_num=lane)
                    status_flags_dict[key] = fault_values[lane - 1] if fault_values else "N/A"

        return status_flags_dict

    def get_transceiver_status_flags(self):
        status_flags_dict = self.get_non_banked_transceiver_status_flags()
        status_flags_dict.update(self.get_banked_transceiver_status_flags())
        return status_flags_dict
