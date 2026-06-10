"""
    bailly_rlm.py

    Implementation of Micas Bailly CPO specific in addition to the CMIS specification.
"""
from ..public.cmis import CmisApi
from ...fields.broadcom import bailly_rlm


RLM_XCVR_INFO_DEFAULT_DICT = {
    "rlm_identifier": "N/A",
    "rlm_revision": "N/A",
    "rlm_laser_wavelength_grid": "N/A",
    "rlm_laser_count": "N/A",
    "rlm_vendor_name": "N/A",
    "rlm_vendor_oui": "N/A",
    "rlm_vendor_pn": "N/A",
    "rlm_vendor_rev": "N/A",
    "rlm_vendor_sn": "N/A",
    "rlm_date_code": "N/A",
    "rlm_max_power": "N/A",
    "rlm_laser_power_mode_control": "N/A",
}


class BaillyApi(CmisApi):
    RLM_THRESHOLD_FIELDS = {
        "RLM_temphighalarm": bailly_rlm.RLM_TEMP_HIGH_ALARM_FIELD,
        "RLM_templowalarm": bailly_rlm.RLM_TEMP_LOW_ALARM_FIELD,
        "RLM_temphighwarning": bailly_rlm.RLM_TEMP_HIGH_WARNING_FIELD,
        "RLM_templowwarning": bailly_rlm.RLM_TEMP_LOW_WARNING_FIELD,
        "RLM_vcchighalarm": bailly_rlm.RLM_VCC_HIGH_ALARM_FIELD,
        "RLM_vcclowalarm": bailly_rlm.RLM_VCC_LOW_ALARM_FIELD,
        "RLM_vcchighwarning": bailly_rlm.RLM_VCC_HIGH_WARNING_FIELD,
        "RLM_vcclowwarning": bailly_rlm.RLM_VCC_LOW_WARNING_FIELD,
        "RLM_txpowerhighalarm": bailly_rlm.RLM_TX_POWER_HIGH_ALARM_FIELD,
        "RLM_txpowerlowalarm": bailly_rlm.RLM_TX_POWER_LOW_ALARM_FIELD,
        "RLM_txpowerhighwarning": bailly_rlm.RLM_TX_POWER_HIGH_WARNING_FIELD,
        "RLM_txpowerlowwarning": bailly_rlm.RLM_TX_POWER_LOW_WARNING_FIELD,
        "RLM_txbiashighalarm": bailly_rlm.RLM_TX_BIAS_HIGH_ALARM_FIELD,
        "RLM_txbiashighwarning": bailly_rlm.RLM_TX_BIAS_HIGH_WARNING_FIELD,
    }
    def __init__(self, xcvr_eeprom):
        super(BaillyApi, self).__init__(xcvr_eeprom)

    def get_dpinit_pending(self):
        '''
        Bailly not supported, return fake value.
        '''
        dpinit_pending_dict = {}
        for lane in range(self.NUM_CHANNELS):
            key = "DPInitPending{}".format(lane + 1)
            dpinit_pending_dict[key] = True
        return dpinit_pending_dict

    def get_active_apsel_hostlane(self):
        '''
        Bailly not supported Deinit, if it is deinit return fake value.
        '''
        has_zero  = False
        current_map = {}
        for lane in range(self.NUM_CHANNELS):
            lane_key = 'ActiveAppSelLane{}'.format(lane + 1)
            app_lane = self.get_application(lane)
            current_map[lane_key] = app_lane
            if app_lane == 0:
                has_zero = True

        if has_zero:
            return current_map
        else:
            normal =  super().get_active_apsel_hostlane()
            return normal

    def _format_revision(self, revision):
        if revision is None:
            return None
        return "{}.{}".format((revision >> 4) & 0xf, revision & 0xf)

    def _format_float(self, value):
        if value is None:
            return None
        if isinstance(value, dict):
            return None
        return float("{:.3f}".format(value))

    def get_rlm_temperature(self):
        monitors = self.xcvr_eeprom.read(bailly_rlm.CPO_MODULE_MONITORS_FIELD)
        if monitors is None:
            return None
        temperature = monitors.get(bailly_rlm.MODULE_TEMPERATURE_MONITOR)
        return self._format_float(temperature)

    def _get_nested_monitor_value(self, monitors, group_field, value_field):
        group = monitors.get(group_field)
        if group is None:
            return None

        value = group.get(value_field)
        if isinstance(value, dict):
            value = value.get(value_field)
        return value

    def get_rlm_monitor_values(self):
        monitors = self.xcvr_eeprom.read(bailly_rlm.CPO_MODULE_MONITORS_FIELD)
        if monitors is None:
            return None

        monitor_values = {
            "RLM_temperature": self._format_float(monitors.get(bailly_rlm.MODULE_TEMPERATURE_MONITOR)),
            "RLM_voltage": self._format_float(monitors.get(bailly_rlm.MODULE_SUPPLY_VOLTAGE_MONITOR)),
            "RLM_tec_current": self._format_float(monitors.get(bailly_rlm.TEC_CURRENT_MONITOR)),
        }

        return monitor_values

    def get_rlm_thresholds(self):
        laser_power_mode = self.xcvr_eeprom.read(bailly_rlm.LASER_POWER_MODE_CONTROL_FIELD)
        if laser_power_mode is None:
            return None

        thresholds = laser_power_mode.get(bailly_rlm.THRESHOLD_VALUES_FIELD)
        if thresholds is None:
            return None

        return {
            key: self._format_float(thresholds.get(field))
            for key, field in self.RLM_THRESHOLD_FIELDS.items()
        }

    def get_rlm_temperature_thresholds(self):
        thresholds = self.get_rlm_thresholds()
        if thresholds is None:
            return None

        return {
            "temphighalarm": thresholds.get("RLM_temphighalarm"),
            "templowalarm": thresholds.get("RLM_templowalarm"),
            "temphighwarning": thresholds.get("RLM_temphighwarning"),
            "templowwarning": thresholds.get("RLM_templowwarning"),
        }

    def get_rlm_flags(self):
        module_alarms = self.xcvr_eeprom.read(bailly_rlm.MODULE_ALARMS_FIELD)
        if module_alarms is None:
            return None

        flags = {
            "RLM_tempHAlarm": module_alarms.get(bailly_rlm.TEMP_HIGH_ALARM_FLAG),
            "RLM_tempLAlarm": module_alarms.get(bailly_rlm.TEMP_LOW_ALARM_FLAG),
            "RLM_tempHWarn": module_alarms.get(bailly_rlm.TEMP_HIGH_WARN_FLAG),
            "RLM_tempLWarn": module_alarms.get(bailly_rlm.TEMP_LOW_WARN_FLAG),
            "RLM_vccHAlarm": module_alarms.get(bailly_rlm.VOLTAGE_HIGH_ALARM_FLAG),
            "RLM_vccLAlarm": module_alarms.get(bailly_rlm.VOLTAGE_LOW_ALARM_FLAG),
            "RLM_vccHWarn": module_alarms.get(bailly_rlm.VOLTAGE_HIGH_WARN_FLAG),
            "RLM_vccLWarn": module_alarms.get(bailly_rlm.VOLTAGE_LOW_WARN_FLAG),
        }

        return flags

    def get_rlm_status(self):
        status = self.xcvr_eeprom.read(bailly_rlm.LASER_STATUS_FIELD)
        if status is None:
            return None

        return {
            "RLM_module_low_power_state": status.get(bailly_rlm.MODULE_LOW_POWER_STATE),
            "RLM_interrupt_status": status.get(bailly_rlm.INTL_INTERRUPT_STATUS),
        }
    def get_rlm_temperature_flags(self):
        flags = self.get_rlm_flags()
        if flags is None:
            return None

        return {
            "tempHAlarm": flags.get("RLM_tempHAlarm"),
            "tempLAlarm": flags.get("RLM_tempLAlarm"),
            "tempHWarn": flags.get("RLM_tempHWarn"),
            "tempLWarn": flags.get("RLM_tempLWarn"),
        }

    def get_transceiver_dom_real_value(self):
        dom_info = super().get_transceiver_dom_real_value()
        if dom_info is None:
            dom_info = {}

        rlm_monitors = self.get_rlm_monitor_values()
        if rlm_monitors is not None:
            dom_info.update({
                key: value for key, value in rlm_monitors.items()
                if value is not None
            })

        return dom_info

    def get_transceiver_dom_flags(self):
        dom_flags = super().get_transceiver_dom_flags()
        if dom_flags is None:
            dom_flags = {}

        rlm_flags = self.get_rlm_flags()
        if rlm_flags is not None:
            dom_flags.update({
                key: value for key, value in rlm_flags.items()
                if value is not None
            })

        return dom_flags

    def get_transceiver_status_flags(self):
        status_flags = super().get_transceiver_status_flags()
        if status_flags is None:
            status_flags = {}

        rlm_flags = self.get_rlm_flags()
        if rlm_flags is not None:
            status_flags.update({
                key: value for key, value in rlm_flags.items()
                if value is not None
            })

        rlm_status = self.get_rlm_status()
        if rlm_status is not None:
            status_flags.update({
                key: value for key, value in rlm_status.items()
                if value is not None
            })

        return status_flags

    def get_transceiver_threshold_info(self):
        threshold_info = super().get_transceiver_threshold_info()
        if threshold_info is None:
            threshold_info = {}

        rlm_thresholds = self.get_rlm_thresholds()
        if rlm_thresholds is not None:
            threshold_info.update({
                key: value for key, value in rlm_thresholds.items()
                if value is not None
            })

        return threshold_info

    def get_transceiver_info(self):
        info = super().get_transceiver_info()
        if info is None:
            return None
        info.update(RLM_XCVR_INFO_DEFAULT_DICT)

        rlm_info = self.get_rlm_info()
        cpo_info = rlm_info.get("cpo_info")
        rlm_vendor_info = rlm_info.get("rlm_vendor_info")
        laser_power_mode = rlm_info.get("laser_power_mode")
        if cpo_info is None and rlm_vendor_info is None and laser_power_mode is None:
            return info

        if cpo_info is not None:
            info.update({
                "rlm_identifier": cpo_info.get(bailly_rlm.CPO_IDENTIFIER),
                "rlm_revision": self._format_revision(cpo_info.get(bailly_rlm.CPO_REVISION)),
                "rlm_laser_wavelength_grid": cpo_info.get(bailly_rlm.LASER_WAVELENGTH_GRID),
                "rlm_laser_count": cpo_info.get(bailly_rlm.LASER_COUNT),
            })

        if rlm_vendor_info is not None:
            info.update({
                "rlm_vendor_name": self._strip_str(
                    rlm_vendor_info.get(bailly_rlm.VENDOR_NAME_ASCII_FIELD)
                ),
                "rlm_vendor_oui": rlm_vendor_info.get(bailly_rlm.VENDOR_OUI_HEX_FIELD),
                "rlm_vendor_pn": self._strip_str(
                    rlm_vendor_info.get(bailly_rlm.VENDOR_PART_NUMBER_ASCII_FIELD)
                ),
                "rlm_vendor_rev": self._strip_str(
                    rlm_vendor_info.get(bailly_rlm.VENDOR_REVISION_ASCII_FIELD)
                ),
                "rlm_vendor_sn": self._strip_str(
                    rlm_vendor_info.get(bailly_rlm.VENDOR_SERIAL_NUMBER_ASCII_FIELD)
                ),
                "rlm_date_code": self._strip_str(
                    rlm_vendor_info.get(bailly_rlm.DATE_CODE_FIELD)
                ),
                "rlm_max_power": rlm_vendor_info.get(bailly_rlm.MAX_POWER_CONSUMPTION_FIELD),
            })

        if laser_power_mode is not None:
            info.update({
                "rlm_laser_power_mode_control": laser_power_mode.get(
                    bailly_rlm.LASER_POWER_MODE_CONTROL_BITS_FIELD
                ),
            })

        return info

    def get_rlm_vendor_info(self):
        return self.xcvr_eeprom.read(bailly_rlm.CPO_VENDOR_INFO_FIELD)

    def get_rlm_info(self):
        return {
            "cpo_info": self.xcvr_eeprom.read(bailly_rlm.CPO_INFO_FIELD),
            "rlm_vendor_info": self.get_rlm_vendor_info(),
            "laser_power_mode": self.xcvr_eeprom.read(bailly_rlm.LASER_POWER_MODE_CONTROL_FIELD),
        }

    def get_rlm_laser_current(self):
        return self.xcvr_eeprom.read(bailly_rlm.LASER_CURRENT_MONITOR_FIELD)

    def get_rlm_laser_voltage(self):
        return self.xcvr_eeprom.read(bailly_rlm.LASER_VOLTAGE_MONITOR_FIELD)

    def get_rlm_laser_power(self):
        return self.xcvr_eeprom.read(bailly_rlm.LASER_OPTICAL_POWER_MONITOR_FIELD)
