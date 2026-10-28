"""
    bailly_elsfp.py

    Public ELSFP API for the Bailly external laser source (RLM). The RLM
    registers are exposed on pages 0xB0-0xB2 of the optical engine's EEPROM,
    offset by the ELS base page; see BaillyElsfpMemMap.

    Only the public ELSFP methods backed by RLM registers are implemented.
    The ELS controls (reset, low-power mode and laser enable) raise
    NotImplementedError: Bailly has no reset register, and its low-power and
    laser disable registers do not act on host writes.
"""
import copy

from ..public.elsfp import (
    ElsfpApi,
    ELSFP_BANKED_DOM_REAL_VALUE_DEFAULT_DICT,
    ELSFP_INFO_DEFAULT_DICT,
)
from ...fields import elsfp_consts
from ...fields.broadcom import bailly

BAILLY_MAX_LASERS = 16

MODULE_STATE_LOW_POWER = "ModuleLowPwr"
MODULE_STATE_READY = "ModuleReady"


class BaillyElsfpApi(ElsfpApi):
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

    # Legacy RLM readers: retained from BaillyApi without decoding changes.

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

    # Public ELSFP adapters. These do not redefine RLM register decoding.

    @staticmethod
    def _lane_count_from_info(cpo_info):
        if cpo_info is None:
            return None
        count = cpo_info.get(bailly.LASER_COUNT)
        if not isinstance(count, int) or not 0 < count <= BAILLY_MAX_LASERS:
            return None
        return count

    def get_lane_count(self) -> int:
        # No legacy count-only reader exists. Avoid get_rlm_info(), which also
        # reads the vendor and power-mode groups when only the count is needed.
        return self._lane_count_from_info(self.xcvr_eeprom.read(bailly.CPO_INFO_FIELD))

    def get_elsfp_info(self) -> dict:
        raw = self.get_rlm_info()
        cpo_info = raw.get("cpo_info")
        vendor_info = raw.get("rlm_vendor_info")
        power_mode = raw.get("laser_power_mode")
        lane_count = self._lane_count_from_info(cpo_info)
        if cpo_info is None or vendor_info is None or lane_count is None:
            return None
        revision = self._format_revision(cpo_info.get(bailly.CPO_REVISION))
        required = (bailly.VENDOR_SERIAL_NUMBER_ASCII_FIELD, bailly.VENDOR_NAME_ASCII_FIELD,
                    bailly.VENDOR_PART_NUMBER_ASCII_FIELD, bailly.MAX_POWER_CONSUMPTION_FIELD,
                    bailly.DATE_CODE_FIELD, bailly.VENDOR_OUI_HEX_FIELD, bailly.VENDOR_REVISION_ASCII_FIELD)
        if revision is None or cpo_info.get(bailly.CPO_IDENTIFIER) is None:
            return None
        if any(vendor_info.get(field) is None for field in required):
            return None

        info = copy.deepcopy(ELSFP_INFO_DEFAULT_DICT)
        info.update({
            "type": cpo_info[bailly.CPO_IDENTIFIER],
            "hardware_rev": revision,
            "serial": vendor_info[bailly.VENDOR_SERIAL_NUMBER_ASCII_FIELD].rstrip(),
            "manufacturer": vendor_info[bailly.VENDOR_NAME_ASCII_FIELD].rstrip(),
            "model": vendor_info[bailly.VENDOR_PART_NUMBER_ASCII_FIELD].rstrip(),
            "ext_identifier": "%sW Max" % vendor_info[bailly.MAX_POWER_CONSUMPTION_FIELD],
            "vendor_date": vendor_info[bailly.DATE_CODE_FIELD].rstrip(),
            "vendor_oui": vendor_info[bailly.VENDOR_OUI_HEX_FIELD],
            "vendor_rev": vendor_info[bailly.VENDOR_REVISION_ASCII_FIELD].rstrip(),
            "lane_count": lane_count,
            "laser_wavelength_grid": cpo_info.get(bailly.LASER_WAVELENGTH_GRID),
        })
        # Preserve the old decoded control readback as an ELS extension. It is
        # not a promise that the hardware accepts writes to that control.
        if power_mode is not None:
            info["rlm_laser_lpmode_control"] = power_mode.get(bailly.LASER_POWER_MODE_CONTROL_BITS_FIELD)
        return info

    def get_module_temperature(self) -> float:
        return self.get_rlm_temperature()

    def get_module_voltage(self) -> float:
        values = self.get_rlm_monitor_values()
        return values.get("els_voltage") if values is not None else None

    def get_icc_monitor(self) -> float:
        raise NotImplementedError("Bailly ELS does not report a supply current monitor")

    def _per_laser_values(self, values, laser_field, public_field, convert):
        if values is None:
            return None
        count = self.get_lane_count()
        if count is None:
            return None
        result = {}
        for laser in range(count):
            value = values.get(laser_field.format(laser))
            if value is None or isinstance(value, dict):
                return None
            result["%s%d" % (public_field, laser + 1)] = convert(value)
        return result

    def get_per_lane_bias_current_monitor(self) -> dict:
        # Legacy mA -> public monitor A; DOM/display converts A to mA.
        return self._per_laser_values(self.get_rlm_laser_current(), bailly.LASER_CURRENT_MONITOR,
                                      elsfp_consts.BIAS_CURRENT_MONITOR_FIELD, lambda ma: ma / 1000.0)

    def get_per_lane_opt_power_monitor(self) -> dict:
        # Both legacy and public single-monitor values are mW.
        return self._per_laser_values(self.get_rlm_laser_power(), bailly.LASER_OPTICAL_POWER_MONITOR,
                                      elsfp_consts.OPT_POWER_MONITOR_FIELD, lambda mw: mw)

    def get_per_lane_voltage_monitor(self) -> dict:
        return self._per_laser_values(self.get_rlm_laser_voltage(), bailly.LASER_VOLTAGE_MONITOR,
                                      elsfp_consts.VOLTAGE_MONITOR_FIELD, lambda volts: volts)

    def get_non_banked_elsfp_dom_real_value(self) -> dict:
        values = self.get_rlm_monitor_values()
        if values is None or values.get("els_temperature") is None or values.get("els_voltage") is None:
            return None
        return {"temperature": values["els_temperature"], "voltage": values["els_voltage"],
                "tec_current": values.get("rlm_tec_current")}

    def get_banked_elsfp_dom_real_value(self) -> dict:
        bias_current = self.get_per_lane_bias_current_monitor()
        optical_power = self.get_per_lane_opt_power_monitor()
        voltage = self.get_per_lane_voltage_monitor()
        if None in (bias_current, optical_power, voltage):
            return None

        # Bailly has no supply current monitor, so "icc" keeps its default.
        dom = copy.deepcopy(ELSFP_BANKED_DOM_REAL_VALUE_DEFAULT_DICT)
        first_lane = self._get_first_lane_for_bank()
        for name, field, values, convert in (
                ("laser_bias_current", elsfp_consts.BIAS_CURRENT_MONITOR_FIELD, bias_current, self.amps_to_ma),
                ("optical_power", elsfp_consts.OPT_POWER_MONITOR_FIELD, optical_power, self.mw_to_dbm),
                ("voltage", elsfp_consts.VOLTAGE_MONITOR_FIELD, voltage, lambda volts: volts)):
            for index in range(len(values)):
                value = convert(values["%s%d" % (field, index + 1)])
                dom["%s_lane%d" % (name, first_lane + index)] = float("{:.3f}".format(value))
        return dom

    def _get_rlm_threshold(self, name):
        values = self.get_rlm_thresholds()
        return values.get(name) if values is not None else None

    def get_laser_bias_high_alarm(self) -> float:
        # The public threshold API returns A; legacy RLM thresholds use mA.
        value = self._get_rlm_threshold("els_txbiashighalarm")
        return value / 1000.0 if value is not None else None

    def get_laser_bias_high_warn(self) -> float:
        value = self._get_rlm_threshold("els_txbiashighwarning")
        return value / 1000.0 if value is not None else None

    def get_laser_bias_low_alarm(self) -> float:
        raise NotImplementedError("Bailly RLM does not report a low bias alarm threshold")

    def get_laser_bias_low_warn(self) -> float:
        raise NotImplementedError("Bailly RLM does not report a low bias warning threshold")

    def get_optical_power_high_alarm(self) -> float:
        return self._get_rlm_threshold("els_txpowerhighalarm")

    def get_optical_power_low_alarm(self) -> float:
        return self._get_rlm_threshold("els_txpowerlowalarm")

    def get_optical_power_high_warn(self) -> float:
        return self._get_rlm_threshold("els_txpowerhighwarning")

    def get_optical_power_low_warn(self) -> float:
        return self._get_rlm_threshold("els_txpowerlowwarning")

    def get_elsfp_threshold_info(self) -> dict:
        values = self.get_rlm_thresholds()
        if values is None:
            return None
        names = {
            "temperature_alarm_high": "els_temphighalarm",
            "temperature_alarm_low": "els_templowalarm",
            "temperature_warn_high": "els_temphighwarning",
            "temperature_warn_low": "els_templowwarning",
            "voltage_alarm_high": "els_vcchighalarm",
            "voltage_alarm_low": "els_vcclowalarm",
            "voltage_warn_high": "els_vcchighwarning",
            "voltage_warn_low": "els_vcclowwarning",
            "laser_bias_alarm_high": "els_txbiashighalarm",
            "laser_bias_warn_high": "els_txbiashighwarning",
            "optical_power_alarm_high": "els_txpowerhighalarm",
            "optical_power_alarm_low": "els_txpowerlowalarm",
            "optical_power_warn_high": "els_txpowerhighwarning",
            "optical_power_warn_low": "els_txpowerlowwarning",
        }
        if any(values.get(name) is None for name in names.values()):
            return None
        # Bias thresholds remain mA. Only optical-power thresholds become dBm.
        return {name: self._format_float(self.mw_to_dbm(values[raw])) if name.startswith("optical_power_")
                else values[raw] for name, raw in names.items()}

    def get_non_banked_elsfp_dom_flags(self) -> dict:
        values = self.get_rlm_flags()
        if values is None:
            return None
        names = {
            "temperature_alarm_high": "els_tempHAlarm", "temperature_alarm_low": "els_tempLAlarm",
            "temperature_warn_high": "els_tempHWarn", "temperature_warn_low": "els_tempLWarn",
            "voltage_alarm_high": "els_vccHAlarm", "voltage_alarm_low": "els_vccLAlarm",
            "voltage_warn_high": "els_vccHWarn", "voltage_warn_low": "els_vccLWarn",
        }
        if any(values.get(name) is None for name in names.values()):
            return None
        return {name: bool(values[raw]) for name, raw in names.items()}

    def get_banked_elsfp_dom_flags(self) -> dict:
        # Expose only the existing module-level alarms. Per-laser alarm
        # reporting requires hardware capability/bit-semantics verification.
        return {}

    def _module_state_from_status(self, status):
        if status is None:
            return None
        power_mode = status.get("els_module_low_power_state")
        codes = self.xcvr_eeprom.mem_map.codes
        if power_mode == codes.POWER_MODE[1]:
            return MODULE_STATE_LOW_POWER
        if power_mode == codes.POWER_MODE[0]:
            return MODULE_STATE_READY
        return "Unknown"

    def get_module_fault_cause(self) -> str:
        raise NotImplementedError("Bailly RLM does not report an ELS module fault cause")

    def get_module_state(self) -> str:
        # This adapts power-mode readback, not a complete ELS state machine.
        return self._module_state_from_status(self.get_rlm_status())

    def get_non_banked_elsfp_status(self) -> dict:
        values = self.get_rlm_status()
        state = self._module_state_from_status(values)
        if state is None:
            return None
        return {"module_state": state, "interrupt_status": values.get("els_interrupt_status")}

    def get_non_banked_elsfp_status_flags(self) -> dict:
        flags = self.get_non_banked_elsfp_dom_flags()
        status = self.get_rlm_status()
        if flags is None or status is None:
            return None
        flags["interrupt_status"] = status.get("els_interrupt_status")
        return flags

    # Existing per-laser state/enable readers and unsupported controls.

    def _read_laser_bits(self, low_field, high_field):
        """Return a 16-bit per-laser register value, bit N for laser N."""
        low = self.xcvr_eeprom.read(low_field)
        high = self.xcvr_eeprom.read(high_field)
        if low is None or high is None:
            return None
        return (high << 8) | low

    def get_per_lane_enable(self) -> list:
        count = self.get_lane_count()
        disabled = self._read_laser_bits(bailly.LASER_DISABLE_CONTROL_7_0,
                                         bailly.LASER_DISABLE_CONTROL_15_8)
        if count is None or disabled is None:
            return None
        return [0 if (disabled >> laser) & 1 else 1 for laser in range(count)]

    def get_per_lane_state(self) -> dict:
        count = self.get_lane_count()
        active = self._read_laser_bits(bailly.LASER_ACTIVE_STATUS_7_0,
                                       bailly.LASER_ACTIVE_STATUS_15_8)
        if count is None or active is None:
            return None
        codes = self.xcvr_eeprom.mem_map.codes
        return {
            "%s%d" % (elsfp_consts.LANE_STATE_FIELD, laser + 1):
                codes.LASER_ACTIVE_STATUS[(active >> laser) & 1]
            for laser in range(count)
        }

    def get_banked_elsfp_status(self) -> dict:
        lane_enable = self.get_per_lane_enable()
        lane_state = self.get_per_lane_state()
        if lane_enable is None or lane_state is None:
            return None

        status = {}
        first_lane = self._get_first_lane_for_bank()
        for index, enabled in enumerate(lane_enable):
            status["enable_lane%d" % (first_lane + index)] = bool(enabled)
        for index in range(len(lane_state)):
            status["state_lane%d" % (first_lane + index)] = \
                lane_state["%s%d" % (elsfp_consts.LANE_STATE_FIELD, index + 1)]
        return status

    def get_banked_elsfp_status_flags(self) -> dict:
        return self.get_banked_elsfp_dom_flags()

    # The shared lower memory belongs to the OE. Never use generic ELSFP
    # byte-26 controls here; the existing RLM controls remain unavailable.

    def set_lpmode(self, low_power: bool) -> bool:
        raise NotImplementedError("Bailly ELS low-power control is not available through the RLM registers")

    def reset(self) -> bool:
        raise NotImplementedError("Bailly ELS reset is not available: the RLM has no reset register")

    def set_per_lane_enable(self, lane_mask: int, enabled: bool) -> bool:
        raise NotImplementedError("Bailly ELS laser enable control is not available through the RLM registers")
