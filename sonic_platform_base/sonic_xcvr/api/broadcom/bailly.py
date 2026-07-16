"""
    bailly.py

    Implementation of Micas Bailly CPO specific in addition to the CMIS specification.
"""
from ..public.cmis import CmisApi
from ...fields.broadcom import bailly

class BaillyApi(CmisApi):
    RLM_THRESHOLD_FIELDS = {
        "els_temphighalarm": bailly.RLM_TEMP_HIGH_ALARM_FIELD,
        "els_templowalarm": bailly.RLM_TEMP_LOW_ALARM_FIELD,
        "els_temphighwarning": bailly.RLM_TEMP_HIGH_WARNING_FIELD,
        "els_templowwarning": bailly.RLM_TEMP_LOW_WARNING_FIELD,
        "els_vcchighalarm": bailly.RLM_VCC_HIGH_ALARM_FIELD,
        "els_vcclowalarm": bailly.RLM_VCC_LOW_ALARM_FIELD,
        "els_vcchighwarning": bailly.RLM_VCC_HIGH_WARNING_FIELD,
        "els_vcclowwarning": bailly.RLM_VCC_LOW_WARNING_FIELD,
        "els_txpowerhighalarm": bailly.RLM_TX_POWER_HIGH_ALARM_FIELD,
        "els_txpowerlowalarm": bailly.RLM_TX_POWER_LOW_ALARM_FIELD,
        "els_txpowerhighwarning": bailly.RLM_TX_POWER_HIGH_WARNING_FIELD,
        "els_txpowerlowwarning": bailly.RLM_TX_POWER_LOW_WARNING_FIELD,
        "els_txbiashighalarm": bailly.RLM_TX_BIAS_HIGH_ALARM_FIELD,
        "els_txbiashighwarning": bailly.RLM_TX_BIAS_HIGH_WARNING_FIELD,
    }

    # CMIS compatibility overrides.

    def __init__(self, xcvr_eeprom):
        super(BaillyApi, self).__init__(xcvr_eeprom)

    def get_dpinit_pending(self):
        '''
        Bailly not supported, return fake value, always return True
        '''
        dpinit_pending_dict = {}
        for lane in range(self.NUM_CHANNELS):
            key = "DPInitPending{}".format(lane + 1)
            dpinit_pending_dict[key] = True
        return dpinit_pending_dict

    def get_active_apsel_hostlane(self):
        '''
        Bailly not supported 0 appl.When the API detects that Page 0x10 is set to 0, return the value from Page 0x10 instead.
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

    # Helper methods.

    def _format_revision(self, revision):
        '''
        Format RLM revision byte as major.minor string.
        '''
        if revision is None:
            return None
        return "{}.{}".format((revision >> 4) & 0xf, revision & 0xf)

    def _format_float(self, value):
        '''
        Format RLM numeric value to three decimal places.
        '''
        if value is None:
            return None
        if isinstance(value, dict):
            return None
        return float("{:.3f}".format(value))

    # RLM single-read APIs.

    def get_rlm_temperature(self):
        '''
        This function returns RLM module temperature.
        '''
        monitors = self.xcvr_eeprom.read(bailly.CPO_MODULE_MONITORS_FIELD)
        if monitors is None:
            return None
        temperature = monitors.get(bailly.MODULE_TEMPERATURE_MONITOR)
        return self._format_float(temperature)

    def get_rlm_vendor_info(self):
        '''
        This function returns RLM vendor information.
        '''
        return self.xcvr_eeprom.read(bailly.CPO_VENDOR_INFO_FIELD)

    def get_rlm_laser_current(self):
        '''
        This function returns RLM laser current monitor values.
        '''
        return self.xcvr_eeprom.read(bailly.LASER_CURRENT_MONITOR_FIELD)

    def get_rlm_laser_voltage(self):
        '''
        This function returns RLM laser voltage monitor values.
        '''
        return self.xcvr_eeprom.read(bailly.LASER_VOLTAGE_MONITOR_FIELD)

    def get_rlm_laser_power(self):
        '''
        This function returns RLM laser optical power monitor values.
        '''
        return self.xcvr_eeprom.read(bailly.LASER_OPTICAL_POWER_MONITOR_FIELD)

    # RLM aggregate-read APIs.

    def get_rlm_monitor_values(self):
        """
        Retrieves RLM DOM sensor values for the RLM laser module
        
        The returned dictionary contains floating-point values corresponding to
        RLM temperature, voltage and TEC current readings, as defined in the
        TRANSCEIVER_DOM_SENSOR table in STATE_DB.
        
        Returns:
            Dictionary
        """
        monitors = self.xcvr_eeprom.read(bailly.CPO_MODULE_MONITORS_FIELD)
        if monitors is None:
            return None

        monitor_values = {
            "els_temperature": self._format_float(monitors.get(bailly.MODULE_TEMPERATURE_MONITOR)),
            "els_voltage": self._format_float(monitors.get(bailly.MODULE_SUPPLY_VOLTAGE_MONITOR)),
            "rlm_tec_current": self._format_float(monitors.get(bailly.TEC_CURRENT_MONITOR)),
        }

        return monitor_values

    def get_rlm_thresholds(self):
        """
        Retrieves RLM threshold values for the RLM laser module
        
        The returned dictionary contains floating-point values corresponding to
        RLM DOM sensor threshold readings, as defined in the
        TRANSCEIVER_DOM_THRESHOLD table in STATE_DB.
        
        Returns:
            Dictionary
        """
        laser_power_mode = self.xcvr_eeprom.read(bailly.LASER_POWER_MODE_CONTROL_FIELD)
        if laser_power_mode is None:
            return None

        thresholds = laser_power_mode.get(bailly.THRESHOLD_VALUES_FIELD)
        if thresholds is None:
            return None

        return {
            key: self._format_float(thresholds.get(field))
            for key, field in self.RLM_THRESHOLD_FIELDS.items()
        }

    def get_rlm_flags(self):
        '''
        This function returns RLM alarm and warning flags.
        '''
        module_alarms = self.xcvr_eeprom.read(bailly.MODULE_ALARMS_FIELD)
        if module_alarms is None:
            return None

        flags = {
            "els_tempHAlarm": module_alarms.get(bailly.TEMP_HIGH_ALARM_FLAG),
            "els_tempLAlarm": module_alarms.get(bailly.TEMP_LOW_ALARM_FLAG),
            "els_tempHWarn": module_alarms.get(bailly.TEMP_HIGH_WARN_FLAG),
            "els_tempLWarn": module_alarms.get(bailly.TEMP_LOW_WARN_FLAG),
            "els_vccHAlarm": module_alarms.get(bailly.VOLTAGE_HIGH_ALARM_FLAG),
            "els_vccLAlarm": module_alarms.get(bailly.VOLTAGE_LOW_ALARM_FLAG),
            "els_vccHWarn": module_alarms.get(bailly.VOLTAGE_HIGH_WARN_FLAG),
            "els_vccLWarn": module_alarms.get(bailly.VOLTAGE_LOW_WARN_FLAG),
        }

        return flags

    def get_rlm_status(self):
        '''
        This function returns RLM module status flags.
        '''
        status = self.xcvr_eeprom.read(bailly.LASER_STATUS_FIELD)
        if status is None:
            return None

        return {
            "els_module_low_power_state": status.get(bailly.MODULE_LOW_POWER_STATE),
            "els_interrupt_status": status.get(bailly.INTL_INTERRUPT_STATUS),
        }

    def get_rlm_info(self):
        '''
        This function returns RLM CPO, vendor and laser power mode information.
        '''
        return {
            "cpo_info": self.xcvr_eeprom.read(bailly.CPO_INFO_FIELD),
            "rlm_vendor_info": self.get_rlm_vendor_info(),
            "laser_power_mode": self.xcvr_eeprom.read(bailly.LASER_POWER_MODE_CONTROL_FIELD),
        }

    # RLM subset APIs.

    def get_transceiver_dom_real_value(self):
        """
        Retrieves DOM sensor values for the RLM laser module
        
        The returned dictionary extends the parent CMIS DOM sensor values with
        RLM sensor readings, as defined in the TRANSCEIVER_DOM_SENSOR table in
        STATE_DB.
        
        Returns:
            Dictionary
        """
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

    def get_transceiver_threshold_info(self):
        """
        Retrieves threshold info for the RLM laser module
        
        The returned dictionary extends the parent CMIS threshold values with RLM
        DOM sensor threshold readings, as defined in the TRANSCEIVER_DOM_THRESHOLD
        table in STATE_DB.
        
        Returns:
            Dictionary
        """
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

    def get_transceiver_dom_flags(self):
        """
        Retrieves DOM flag values for the RLM laser module
        
        The returned dictionary extends the parent CMIS DOM flag values with RLM
        alarm and warning flags, as defined in the TRANSCEIVER_DOM_FLAG table in
        STATE_DB.
        
        Returns:
            Dictionary
        """
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
        """
        Retrieves status flag values for the RLM laser module
        
        The returned dictionary extends the parent CMIS status flag values with
        RLM alarm, warning and module status flags, as defined in status tables
        in STATE_DB.
        
        Returns:
            Dictionary
        """
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

    def get_transceiver_info(self):
        """
        Retrieves module information with RLM laser module fields
        
        The returned dictionary extends the parent CMIS module information
        with RLM vendor, identifier, revision and laser capability fields.
        
        Returns:
            Dictionary
        """
        info = super().get_transceiver_info()
        if info is None:
            return None

        rlm_info = self.get_rlm_info()
        cpo_info = rlm_info.get("cpo_info")
        rlm_vendor_info = rlm_info.get("rlm_vendor_info")
        laser_power_mode = rlm_info.get("laser_power_mode")
        if cpo_info is None and rlm_vendor_info is None and laser_power_mode is None:
            return info

        if cpo_info is not None:
            info.update({
                "els_identifier": cpo_info.get(bailly.CPO_IDENTIFIER),
                "els_revision": self._format_revision(cpo_info.get(bailly.CPO_REVISION)),
                "els_laser_count": cpo_info.get(bailly.LASER_COUNT),
                "rlm_laser_wavelength_grid": cpo_info.get(bailly.LASER_WAVELENGTH_GRID),
            })

        if rlm_vendor_info is not None:
            info.update({
                "els_vendor_name": self._strip_str(
                    rlm_vendor_info.get(bailly.VENDOR_NAME_ASCII_FIELD)
                ),
                "els_vendor_oui": rlm_vendor_info.get(bailly.VENDOR_OUI_HEX_FIELD),
                "els_vendor_pn": self._strip_str(
                    rlm_vendor_info.get(bailly.VENDOR_PART_NUMBER_ASCII_FIELD)
                ),
                "els_vendor_rev": self._strip_str(
                    rlm_vendor_info.get(bailly.VENDOR_REVISION_ASCII_FIELD)
                ),
                "els_vendor_sn": self._strip_str(
                    rlm_vendor_info.get(bailly.VENDOR_SERIAL_NUMBER_ASCII_FIELD)
                ),
                "els_date_code": self._strip_str(
                    rlm_vendor_info.get(bailly.DATE_CODE_FIELD)
                ),
                "els_max_power": rlm_vendor_info.get(bailly.MAX_POWER_CONSUMPTION_FIELD),
            })

        if laser_power_mode is not None:
            info.update({
                "rlm_laser_lpmode_control": laser_power_mode.get(
                    bailly.LASER_POWER_MODE_CONTROL_BITS_FIELD
                ),
            })

        return info

    def get_laser_temperature(self):
        """
        Bailly has no laser temperature acquisition register, return none.
        """
        return None
