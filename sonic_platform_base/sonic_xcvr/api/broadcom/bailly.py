"""
    bailly.py

    Implementation of Micas Bailly CPO specific in addition to the CMIS specification.
"""
import time

from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_py_common import syslogger

from ..public.cmis import CmisApi
from ...fields.broadcom import bailly

SYSLOG_IDENTIFIER = "bailly_api"
# Global logger instance
helper_logger = syslogger.SysLogger(SYSLOG_IDENTIFIER, enable_runtime_config=True)
def log_debug(message):
    helper_logger.log_debug(message)

def log_notice(message):
    helper_logger.log_notice(message)

def log_error(message):
    helper_logger.log_error(message)

def _to_hex(data):
    """
    Format a raw register buffer as a space separated hex string for logging.

    Args:
        data:
            bytes/bytearray/tuple/list of integers, or None

    Returns:
        String, e.g. "00 01 0f"; "None" if data is None
    """
    if data is None:
        return "None"
    return " ".join("{:02x}".format(byte) for byte in bytearray(data))

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

    # Bailly CPO Staged Control Set (Page 10h) programming.
    # StagedCtrlApSel holds one byte per host lane with this layout:
    #   bit 7-4: application code
    #   bit 3  : lane group selector (see _appl_sel_lane_group)
    #   bit 0  : EC (Explicit Control)
    APPL_SEL_CODE_SHIFT = 4
    APPL_SEL_LANE_GROUP_SHIFT = 1
    APPL_SEL_CODE_MAX = 0xf
    # Number of host lanes per lane group (lane0-3 / lane4-7)
    LANES_PER_LANE_GROUP = 4
    # Application code of the 800G application, where the lane group bit stays 0
    APPL_CODE_800G = 6
    # Policy of the ApSel block read-back verification
    APPLY_VERIFY_MAX_RETRY = 3
    APPLY_VERIFY_RETRY_DELAY_SEC = 0.1
    # Settle time after applying DataPathInit
    DPINIT_SETTLE_DELAY_SEC = 0.01

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

    def _get_appl_sel_field(self, lane_id):
        """
        Get the STAGED_CTRL_APSEL field object of one host lane.

        Args:
            lane_id:
                Integer, one-based host lane id (1 .. NUM_CHANNELS)

        Returns:
            Field object, or None if it is not present in the memory map
        """
        field_name = "{}_{}_{}".format(consts.STAGED_CTRL_APSEL_FIELD, 0, lane_id)
        return self.xcvr_eeprom.mem_map.get_field(field_name)

    def _get_appl_sel_block(self):
        """
        Locate the whole STAGED_CTRL_APSEL block (one byte per host lane).

        Returns:
            Tuple (start_offset, size) on success, (None, None) on failure
        """
        first_field = self._get_appl_sel_field(1)
        last_field = self._get_appl_sel_field(self.NUM_CHANNELS)
        if first_field is None or last_field is None:
            log_error("_get_appl_sel_block: '{}' field not found in memory map".format(
                consts.STAGED_CTRL_APSEL_FIELD))
            return None, None

        start_offset = first_field.get_offset()
        size = last_field.get_offset() + last_field.get_size() - start_offset
        if size != self.NUM_CHANNELS:
            log_error("_get_appl_sel_block: unexpected block size {} (expect {}) at offset {}".format(
                size, self.NUM_CHANNELS, start_offset))
            return None, None

        return start_offset, size

    def _get_all_application_raw(self):
        """
        Read all lanes STAGED_CTRL_APSEL register block once via read_raw.

        Returns:
            bytearray: raw register bytes for all lanes, None on failure
        """
        if self.is_flat_memory():
            log_error("_get_all_application_raw: flat memory, no lane datapath page")
            return None

        start_offset, size = self._get_appl_sel_block()
        if start_offset is None:
            return None

        try:
            raw_buf = self.xcvr_eeprom.read_raw(start_offset, size)
        except Exception as error:
            log_error("_get_all_application_raw: read_raw({}, {}) failed: {}".format(
                start_offset, size, repr(error)))
            return None

        if raw_buf is None:
            log_error("_get_all_application_raw: read_raw({}, {}) returned None".format(
                start_offset, size))
            return None

        raw_buf = bytearray(raw_buf)
        log_debug("_get_all_application_raw: start_addr {}, raw_buf: {}".format(
            start_offset, _to_hex(raw_buf)))
        return raw_buf

    def _appl_sel_lane_group(self, lane, appl_code):
        """
        Compute the lane group bit of one host lane.

        The host lanes are split into groups of LANES_PER_LANE_GROUP lanes
        (lane0-3 / lane4-7); the second group sets the lane group bit, except
        for the 800G application where the bit stays 0 on every lane.

        Args:
            lane:
                Integer, zero-based host lane id
            appl_code:
                Integer, the application code being programmed

        Returns:
            Integer, 0 or LANES_PER_LANE_GROUP
        """
        if lane < self.LANES_PER_LANE_GROUP or appl_code == self.APPL_CODE_800G:
            return 0
        return self.LANES_PER_LANE_GROUP

    def _build_appl_sel_buffer(self, appl_code, ec):
        """
        Build the whole STAGED_CTRL_APSEL block content for one application.

        Args:
            appl_code:
                Integer, the application code
            ec:
                Integer, EC (Explicit Control) bit value

        Returns:
            bytearray, one byte per host lane
        """
        return bytearray(
            (appl_code << self.APPL_SEL_CODE_SHIFT)
            | (self._appl_sel_lane_group(lane, appl_code) << self.APPL_SEL_LANE_GROUP_SHIFT)
            | ec
            for lane in range(self.NUM_CHANNELS)
        )

    def set_application(self, channel, appl_code, ec=0):
        """
        Update the selected application code to the specified lanes on the host side

        Bailly programs the StagedCtrlApSel block as a whole (one byte per host
        lane), so every lane is written with the same appl_code instead of only
        the lanes selected in channel. channel is therefore used to validate the
        request only; the CPO caller (cmis_manager_task) passes the full lane
        mask of the module.

        Args:
            channel:
                Integer, a bitmask of the lanes on the host side
                e.g. 0x5 for lane 0 and lane 2.
            appl_code:
                Integer, the desired application code
            ec:
                Integer, EC bit value

        Returns:
            Boolean, true if success otherwise false
        """
        log_debug("set_application channel {:#x}, appl_code {}, ec {}".format(channel, appl_code, ec))

        if (channel & ((1 << self.NUM_CHANNELS) - 1)) == 0:
            log_error("set_application: no host lane selected for channel {:#x}, appl_code {}".format(
                channel, appl_code))
            return False

        if not 0 <= appl_code <= self.APPL_SEL_CODE_MAX:
            log_error("set_application: invalid appl_code {} for channel {:#x}".format(
                appl_code, channel))
            return False

        start_offset, size = self._get_appl_sel_block()
        if start_offset is None:
            return False

        # Read the whole block first: it validates that page 10h is reachable
        # and logs the state before the update.
        if self._get_all_application_raw() is None:
            log_error("set_application: unable to read ApSel block for channel {:#x}, appl_code {}".format(
                channel, appl_code))
            return False

        write_buf = self._build_appl_sel_buffer(appl_code, ec)
        log_notice("set_application start_offset {}, channel {:#x}, appl_code {}, ec {}, write_buffer: {}".format(
            start_offset, channel, appl_code, ec, _to_hex(write_buf)))

        try:
            if not self.xcvr_eeprom.write_raw(start_offset, size, write_buf):
                log_error("set_application: write_raw failed for channel {:#x}, appl_code {}".format(
                    channel, appl_code))
                return False

            # retry read-back to verify write result
            new_data = None
            for retry_cnt in range(self.APPLY_VERIFY_MAX_RETRY):
                new_data = self._get_all_application_raw()
                if new_data is None:
                    log_error("set_application: verify read failed, retry {}, channel {:#x}, appl_code {}".format(
                        retry_cnt, channel, appl_code))
                    time.sleep(self.APPLY_VERIFY_RETRY_DELAY_SEC)
                    continue

                if new_data == write_buf:
                    log_debug("set_application: verify ok at retry {}, channel {:#x}, appl_code {}".format(
                        retry_cnt, channel, appl_code))
                    return True

                log_debug("set_application: verify retry {}, start_offset {}, raw_buf: {}".format(
                    retry_cnt, start_offset, _to_hex(new_data)))
                time.sleep(self.APPLY_VERIFY_RETRY_DELAY_SEC)

            log_error("set_application: verify failed for channel {:#x}, appl_code {}, expect: {}, actual: {}".format(
                channel, appl_code, _to_hex(write_buf), _to_hex(new_data)))
            return False
        except Exception as error:
            log_error("set_application: unexpected error for channel {:#x}, appl_code {}, {}".format(
                channel, appl_code, repr(error)))
            return False

    def scs_apply_datapath_init(self, channel):
        """
        Apply DataPathInit via the Page 10h staged control set.

        Bailly applies DataPathInit to the whole bank: as soon as any lane is
        selected in channel the full lane mask is written, and 0 is written when
        channel is 0.

        Note:
            The applied bit is a trigger, it is not read back for verification
            because the hardware may self-clear it.

        Args:
            channel:
                Integer, a bitmask of the lanes on the host side

        Returns:
            Boolean, true if the register write succeeded otherwise false
        """
        data = 0 if channel == 0 else (1 << self.NUM_CHANNELS) - 1
        field_name = "%s_%d" % (consts.STAGED_CTRL_APPLY_DPINIT_FIELD, 0)

        try:
            ret = self.xcvr_eeprom.write(field_name, data)
        except Exception as error:
            log_error("scs_apply_datapath_init: write {} failed: {}".format(field_name, repr(error)))
            return False

        if not ret:
            log_error("scs_apply_datapath_init: write {} = {:#x} failed, channel {:#x}".format(
                field_name, data, channel))
            return False

        log_notice("scs_apply_datapath_init: {} set to {:#x}, channel {:#x}".format(
            field_name, data, channel))
        time.sleep(self.DPINIT_SETTLE_DELAY_SEC)
        return True
