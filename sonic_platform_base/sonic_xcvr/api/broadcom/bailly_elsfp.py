"""
    bailly_elsfp.py

    Public ELSFP API for the Bailly external laser source (RLM). The RLM
    registers are exposed on pages 0xB0-0xB2 of the optical engine's EEPROM,
    offset by the ELS base page; see BaillyElsfpMemMap.

    Only the public ELSFP methods backed by RLM registers are implemented.
    Bailly does not provide a reset control, so reset() keeps the
    NotImplementedError behavior of ElsfpApi.
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

    def _format_float(self, value):
        if value is None:
            return None
        return float("{:.3f}".format(value))

    def _read_laser_bits(self, low_field, high_field):
        """Return a 16-bit per-laser register value, bit N for laser N."""
        low = self.xcvr_eeprom.read(low_field)
        high = self.xcvr_eeprom.read(high_field)
        if low is None or high is None:
            return None
        return (high << 8) | low

    def _per_laser_values(self, group_field, laser_field, public_field, convert):
        """
        Read a per-laser RLM monitor group and return it keyed by public ELSFP
        field names, numbered from 1 like the public ELSFP API.
        """
        count = self.get_lane_count()
        values = self.xcvr_eeprom.read(group_field)
        if count is None or values is None:
            return None

        result = {}
        for laser in range(count):
            value = values.get(laser_field.format(laser))
            if value is None:
                return None
            result["%s%d" % (public_field, laser + 1)] = convert(value)
        return result

    ###############################################################
    #               Module information (Pages B0h-B1h)            #
    ###############################################################

    def get_lane_count(self) -> int:
        cpo_info = self.xcvr_eeprom.read(bailly.CPO_INFO_FIELD)
        if cpo_info is None:
            return None
        count = cpo_info.get(bailly.LASER_COUNT)
        if not isinstance(count, int) or not 0 < count <= BAILLY_MAX_LASERS:
            return None
        return count

    def get_elsfp_info(self) -> dict:
        cpo_info = self.xcvr_eeprom.read(bailly.CPO_INFO_FIELD)
        vendor_info = self.xcvr_eeprom.read(bailly.CPO_VENDOR_INFO_FIELD)
        lane_count = self.get_lane_count()
        if cpo_info is None or vendor_info is None or lane_count is None:
            return None

        revision = cpo_info[bailly.CPO_REVISION]
        info = copy.deepcopy(ELSFP_INFO_DEFAULT_DICT)
        info.update({
            "type": cpo_info[bailly.CPO_IDENTIFIER],
            "hardware_rev": "%d.%d" % ((revision >> 4) & 0xf, revision & 0xf),
            "serial": vendor_info[bailly.VENDOR_SERIAL_NUMBER_ASCII_FIELD].rstrip(),
            "manufacturer": vendor_info[bailly.VENDOR_NAME_ASCII_FIELD].rstrip(),
            "model": vendor_info[bailly.VENDOR_PART_NUMBER_ASCII_FIELD].rstrip(),
            "ext_identifier": "%sW Max" % vendor_info[bailly.MAX_POWER_CONSUMPTION_FIELD],
            "vendor_date": vendor_info[bailly.DATE_CODE_FIELD].rstrip(),
            "vendor_oui": vendor_info[bailly.VENDOR_OUI_HEX_FIELD],
            "vendor_rev": vendor_info[bailly.VENDOR_REVISION_ASCII_FIELD].rstrip(),
            "lane_count": lane_count,
        })
        return info

    ###############################################################
    #                 Module monitors (Page B0h)                  #
    ###############################################################

    def get_module_temperature(self) -> float:
        monitors = self.xcvr_eeprom.read(bailly.CPO_MODULE_MONITORS_FIELD)
        if monitors is None:
            return None
        return self._format_float(monitors.get(bailly.MODULE_TEMPERATURE_MONITOR))

    def get_module_voltage(self) -> float:
        monitors = self.xcvr_eeprom.read(bailly.CPO_MODULE_MONITORS_FIELD)
        if monitors is None:
            return None
        return self._format_float(monitors.get(bailly.MODULE_SUPPLY_VOLTAGE_MONITOR))

    def get_icc_monitor(self) -> float:
        raise NotImplementedError("Bailly ELS does not report a supply current monitor")

    def get_per_lane_bias_current_monitor(self) -> dict:
        # RLM laser current is reported in mA; the public API reports amperes.
        return self._per_laser_values(bailly.LASER_CURRENT_MONITOR_FIELD,
                                      bailly.LASER_CURRENT_MONITOR,
                                      elsfp_consts.BIAS_CURRENT_MONITOR_FIELD,
                                      lambda ma: ma / 1000.0)

    def get_per_lane_opt_power_monitor(self) -> dict:
        # RLM laser optical power is reported in mW, as in the public API.
        return self._per_laser_values(bailly.LASER_OPTICAL_POWER_MONITOR_FIELD,
                                      bailly.LASER_OPTICAL_POWER_MONITOR,
                                      elsfp_consts.OPT_POWER_MONITOR_FIELD,
                                      lambda mw: mw)

    def get_per_lane_voltage_monitor(self) -> dict:
        return self._per_laser_values(bailly.LASER_VOLTAGE_MONITOR_FIELD,
                                      bailly.LASER_VOLTAGE_MONITOR,
                                      elsfp_consts.VOLTAGE_MONITOR_FIELD,
                                      lambda volts: volts)

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

    ###############################################################
    #                    Thresholds (Page B2h)                    #
    ###############################################################

    def get_elsfp_threshold_info(self) -> dict:
        power_mode_control = self.xcvr_eeprom.read(bailly.LASER_POWER_MODE_CONTROL_FIELD)
        if power_mode_control is None:
            return None
        thresholds = power_mode_control.get(bailly.THRESHOLD_VALUES_FIELD)
        if thresholds is None:
            return None

        threshold_info = {}
        for name, field in (
                ("temperature_alarm_high", bailly.RLM_TEMP_HIGH_ALARM_FIELD),
                ("temperature_alarm_low", bailly.RLM_TEMP_LOW_ALARM_FIELD),
                ("temperature_warn_high", bailly.RLM_TEMP_HIGH_WARNING_FIELD),
                ("temperature_warn_low", bailly.RLM_TEMP_LOW_WARNING_FIELD),
                ("voltage_alarm_high", bailly.RLM_VCC_HIGH_ALARM_FIELD),
                ("voltage_alarm_low", bailly.RLM_VCC_LOW_ALARM_FIELD),
                ("voltage_warn_high", bailly.RLM_VCC_HIGH_WARNING_FIELD),
                ("voltage_warn_low", bailly.RLM_VCC_LOW_WARNING_FIELD),
                # RLM bias thresholds are in mA, as reported by the public API.
                # Bailly provides no low bias thresholds.
                ("laser_bias_alarm_high", bailly.RLM_TX_BIAS_HIGH_ALARM_FIELD),
                ("laser_bias_warn_high", bailly.RLM_TX_BIAS_HIGH_WARNING_FIELD)):
            threshold_info[name] = self._format_float(thresholds[field])

        # RLM optical power thresholds are in mW; the public API reports dBm.
        for name, field in (
                ("optical_power_alarm_high", bailly.RLM_TX_POWER_HIGH_ALARM_FIELD),
                ("optical_power_alarm_low", bailly.RLM_TX_POWER_LOW_ALARM_FIELD),
                ("optical_power_warn_high", bailly.RLM_TX_POWER_HIGH_WARNING_FIELD),
                ("optical_power_warn_low", bailly.RLM_TX_POWER_LOW_WARNING_FIELD)):
            threshold_info[name] = self._format_float(self.mw_to_dbm(thresholds[field]))

        if None in threshold_info.values():
            return None
        return threshold_info

    ###############################################################
    #              Module state and controls (Page B0h)           #
    ###############################################################

    def get_module_state(self) -> str:
        # Bailly reports only its power mode; full power is reported as ready.
        status = self.xcvr_eeprom.read(bailly.LASER_STATUS_FIELD)
        if status is None:
            return None
        power_mode = status.get(bailly.MODULE_LOW_POWER_STATE)
        codes = self.xcvr_eeprom.mem_map.codes
        if power_mode == codes.POWER_MODE[1]:
            return MODULE_STATE_LOW_POWER
        if power_mode == codes.POWER_MODE[0]:
            return MODULE_STATE_READY
        return "Unknown"

    def set_lpmode(self, low_power: bool) -> bool:
        field = self.xcvr_eeprom.mem_map.get_field(bailly.MODULE_LOW_POWER_CONTROL)
        offset = field.get_offset()
        current = self.xcvr_eeprom.read_raw(offset, 1)
        if current is None:
            return False
        mask = field.get_bitmask()
        value = current | mask if low_power else current & ~mask
        return self.xcvr_eeprom.write_raw(offset, 1, bytearray([value & 0xFF]))

    def get_per_lane_enable(self) -> list:
        count = self.get_lane_count()
        disabled = self._read_laser_bits(bailly.LASER_DISABLE_CONTROL_7_0,
                                         bailly.LASER_DISABLE_CONTROL_15_8)
        if count is None or disabled is None:
            return None
        return [0 if (disabled >> laser) & 1 else 1 for laser in range(count)]

    def set_per_lane_enable(self, lane_mask: int, enabled: bool) -> bool:
        """
        Enable or disable RLM lasers.

        Args:
            lane_mask: Bitmask of lasers to update (bit 0 = laser 0).
            enabled:   True to enable the lasers, False to disable them.

        Raises:
            ValueError: If lane_mask selects a laser beyond the laser count.
        """
        count = self.get_lane_count()
        if count is None:
            return False
        if lane_mask & ~((1 << count) - 1):
            raise ValueError("lane_mask 0x%X selects lasers outside the %d-laser range" % (lane_mask, count))

        disabled = self._read_laser_bits(bailly.LASER_DISABLE_CONTROL_7_0,
                                         bailly.LASER_DISABLE_CONTROL_15_8)
        if disabled is None:
            return False
        if enabled:
            disabled &= ~lane_mask
        else:
            disabled |= lane_mask

        for field, shift in ((bailly.LASER_DISABLE_CONTROL_7_0, 0),
                             (bailly.LASER_DISABLE_CONTROL_15_8, 8)):
            if (lane_mask >> shift) & 0xFF:
                if not self.xcvr_eeprom.write(field, (disabled >> shift) & 0xFF):
                    return False
        return True

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

    def get_non_banked_elsfp_status(self) -> dict:
        module_state = self.get_module_state()
        if module_state is None:
            return None
        return {"module_state": module_state}

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
