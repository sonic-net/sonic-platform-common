"""XcvrApi for the ELSFP (External Laser Source) device, per OIF-CMIS-ELSFP.

Strict ELSFP-only: inherits XcvrApi (not CmisApi). Vendor subclasses chain super()
on each aggregator and overlay vendor-specific extensions. All getters return dicts
with ``els_*``-prefixed keys so a joint-mode merge with an OE-side CmisApi is a
disjoint union.
"""

import logging

from ...fields import elsfp_consts as ec
from ..cdb_capable_mixin import CdbCapableMixin
from ..xcvr_api import XcvrApi

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

NUM_ELSFP_LANES = 8


class ElsfpCmisApi(XcvrApi, CdbCapableMixin):
    NUM_CHANNELS = NUM_ELSFP_LANES

    def __init__(self, xcvr_eeprom, bank_id=0, cdb_mem_map=None):
        super(ElsfpCmisApi, self).__init__(xcvr_eeprom)
        self._init_cdb_mem_map(cdb_mem_map)
        self.bank_id = bank_id

    @staticmethod
    def _nested_get(decoded, group_key, leaf_key, default='N/A'):
        """Fetch a per-lane leaf from a decoded RegGroupField.

        The ELSFP pages compose several groups as a RegGroupField whose members
        are themselves RegGroupFields, so RegGroupField.decode returns a nested
        dict (``decoded[group_key][leaf_key]``) rather than a flat one. This
        helper resolves the leaf through the nested sub-dict, falling back to a
        flat ``decoded[leaf_key]`` so callers stay correct regardless of whether
        the leaf is nested or surfaced directly.
        """
        sub = decoded.get(group_key)
        if isinstance(sub, dict):
            return sub.get(leaf_key, decoded.get(leaf_key, default))
        return decoded.get(leaf_key, default)

    def get_elsfp_lane_monitors(self):
        """ELSFP 0x1B per-lane monitors for TRANSCEIVER_DOM_SENSOR."""
        monitors = self.xcvr_eeprom.read(ec.ELSFP_MONITORS_FIELD)
        if monitors is None:
            return None
        result = {}
        for lane in range(1, self.NUM_CHANNELS + 1):
            mon_bias = f"{ec.BIAS_CURRENT_MONITOR_FIELD}{lane}"
            mon_power = f"{ec.OPT_POWER_MONITOR_FIELD}{lane}"
            mon_voltage = f"{ec.VOLTAGE_MONITOR_FIELD}{lane}"
            result[f"els_bias_current_monitor{lane}"] = self._nested_get(
                monitors, ec.BIAS_CURRENT_MONITOR_FIELD, mon_bias)
            result[f"els_opt_power_monitor{lane}"] = self._nested_get(
                monitors, ec.OPT_POWER_MONITOR_FIELD, mon_power)
            result[f"els_voltage_monitor{lane}"] = self._nested_get(
                monitors, ec.VOLTAGE_MONITOR_FIELD, mon_voltage)
        result['els_icc'] = monitors.get(ec.ICC_MONITOR, 'N/A')
        return result

    def get_elsfp_lane_thresholds(self):
        """ELSFP 0x1A bias/power thresholds (Table 4)."""
        adv = self.xcvr_eeprom.read(ec.ELSFP_MODULE_ADVERTISEMENTS_FIELD)
        if adv is None:
            return None
        result = {}
        fields = [
            ['els_bias', ec.BIAS_HIGH_ALARM, ec.BIAS_LOW_ALARM, ec.BIAS_HIGH_WARN, ec.BIAS_LOW_WARN, False],
            ['els_optpower', ec.OPT_POWER_HIGH_ALARM, ec.OPT_POWER_LOW_ALARM, ec.OPT_POWER_HIGH_WARN, ec.OPT_POWER_LOW_WARN, True],
        ]

        for item in fields:
            prefix, const_ha, const_la, const_hw, const_lw, convert_dbm = item
            ha = adv.get(const_ha, 'N/A')
            la = adv.get(const_la, 'N/A')
            hw = adv.get(const_hw, 'N/A')
            lw = adv.get(const_lw, 'N/A')
            if convert_dbm:
                suffix_val_list = [
                    ('highalarm', ha),
                    ('lowalarm', la),
                    ('highwarning', hw),
                    ('lowwarning', lw)
                ]
                for suffix, val in suffix_val_list:
                    if val != 'N/A' and val is not None:
                        result[f'{prefix}{suffix}'] = float("{:.3f}".format(self.mw_to_dbm(val)))
                    else:
                        result[f'{prefix}{suffix}'] = 'N/A'
            else:
                result[f'{prefix}highalarm'] = ha
                result[f'{prefix}lowalarm'] = la
                result[f'{prefix}highwarning'] = hw
                result[f'{prefix}lowwarning'] = lw

        return result

    def get_elsfp_lane_flags(self):
        """ELSFP 0x1A per-lane indexed alarm/warning flags (Table 7)."""
        masks = self.xcvr_eeprom.read(ec.ELSFP_ALARMS_WARNINGS_MASKS_FIELD)
        if masks is None:
            return None
        result = {}
        flag_map = [
            (ec.HIGH_BIAS_ALARM_INDEXED_FIELD,  f'els_HighBiasAlarm'),
            (ec.LOW_BIAS_ALARM_INDEXED_FIELD,   f'els_LowBiasAlarm'),
            (ec.HIGH_BIAS_WARN_INDEXED_FIELD,   f'els_HighBiasWarn'),
            (ec.LOW_BIAS_WARN_INDEXED_FIELD,    f'els_LowBiasWarn'),
            (ec.HIGH_POWER_ALARM_INDEXED_FIELD, f'els_HighPowerAlarm'),
            (ec.LOW_POWER_ALARM_INDEXED_FIELD,  f'els_LowPowerAlarm'),
            (ec.HIGH_POWER_WARN_INDEXED_FIELD,  f'els_HighPowerWarn'),
            (ec.LOW_POWER_WARN_INDEXED_FIELD,   f'els_LowPowerWarn'),
        ]
        for field_const, key_template in flag_map:
            byte_val = masks.get(field_const, 0)
            for lane in range(1, self.NUM_CHANNELS + 1):
                result[f"{key_template}{lane}"] = bool((byte_val >> (lane - 1)) & 0x1)
        return result

    def get_elsfp_lane_state(self):
        """ELSFP 0x1A per-lane enable + state (Table 8) for TRANSCEIVER_STATUS."""
        ctrl = self.xcvr_eeprom.read(ec.ELSFP_LANE_CONTROLS_FIELD)
        if ctrl is None:
            return None
        result = {}
        enable_byte = ctrl.get(ec.LANE_ENABLE_FIELD, 0)
        for lane in range(1, self.NUM_CHANNELS + 1):
            result[f'els_lane_enable{lane}'] = (enable_byte >> (lane - 1)) & 1
            result[f'els_lane_state{lane}'] = self._nested_get(
                ctrl, ec.LANE_STATE_FIELD, f"{ec.LANE_STATE_FIELD}{lane}")
        return result

    def get_elsfp_output_fiber_checked(self):
        """ELSFP 0x1A output-fiber-checked per-laser flags (byte 223)."""
        fiber = self.xcvr_eeprom.read(ec.ELSFP_OUTPUT_FIBER_CHECKED_FIELD)
        if fiber is None:
            return None
        fiber_byte = fiber.get(ec.OUTPUT_FIBER_CHECKED_FLAG_LANE_FIELD, 0)
        return {
            f'els_output_fiber_checked_flag_lane{lane}':
                (fiber_byte >> (lane - 1)) & 1
            for lane in range(1, self.NUM_CHANNELS + 1)
        }

    def get_elsfp_fault_warning_codes(self):
        """ELSFP 0x1A per-lane 4-bit fault/warning codes (Table 7)."""
        masks = self.xcvr_eeprom.read(ec.ELSFP_ALARMS_WARNINGS_MASKS_FIELD)
        if masks is None:
            return None
        result = {}
        for lane in range(1, self.NUM_CHANNELS + 1):
            result[f'els_fault_code{lane}'] = self._nested_get(
                masks, ec.FAULT_CODE_FIELD, f"{ec.FAULT_CODE_FIELD}{lane}")
            result[f'els_warning_code{lane}'] = self._nested_get(
                masks, ec.WARNING_CODE_FIELD, f"{ec.WARNING_CODE_FIELD}{lane}")
        return result

    def get_elsfp_lane_setpoints(self):
        """ELSFP 0x1B per-lane bias-current / opt-power setpoints for TRANSCEIVER_DOM_THRESHOLD_INFO."""
        sp = self.xcvr_eeprom.read(ec.ELSFP_SETPOINTS_FIELD)
        if sp is None:
            return None
        result = {}
        for lane in range(1, self.NUM_CHANNELS + 1):
            result[f'els_bias_current_setpoint{lane}'] = self._nested_get(
                sp, ec.BIAS_CURRENT_SETPOINT_FIELD,
                f"{ec.BIAS_CURRENT_SETPOINT_FIELD}{lane}")
            result[f'els_opt_power_setpoint{lane}'] = self._nested_get(
                sp, ec.OPT_POWER_SETPOINT_FIELD,
                f"{ec.OPT_POWER_SETPOINT_FIELD}{lane}")
        return result

    def get_elsfp_control_mode(self):
        """ELSFP 0x1A APC/ACC control mode for TRANSCEIVER_STATUS."""
        adv = self.xcvr_eeprom.read(ec.ELSFP_MODULE_ADVERTISEMENTS_FIELD)
        if not adv:
            return {
                'els_control_mode_APCACC': 'N/A'
            }
        return {
            'els_control_mode_APCACC': self._nested_get(
                adv, ec.CONTROL_MODE_AND_LANE_COUNT, ec.CONTROL_MODE_APC_ACC),
        }

    def get_elsfp_status_flags(self):
        """ELSFP 0x1A non-banked summary fault/warn flag bytes for this bank.

        Bytes 166-169 hold per-lane fault flags for absolute lanes 1-32; bytes
        174-177 the matching warning flags. The relevant 8 lanes are selected
        by self.bank_id and remapped to relative lanes 1-8 in the result.
        """
        faults = self.xcvr_eeprom.read(ec.ELSFP_LANE_FAULTS_WARNINGS_FIELD)
        if faults is None:
            return None
        result = {}
        lane_start = self.bank_id * 8 + 1
        lane_end = lane_start + 8
        for abs_lane in range(lane_start, lane_end):
            rel_lane = abs_lane - lane_start + 1
            fault_key = f"FaultFlagLane{abs_lane}"
            warn_key = f"WarnFlagLane{abs_lane}"
            result[f'els_fault_flag_lane{rel_lane}'] = self._nested_get(
                faults, ec.FAULT_FLAG_LANE_FIELD, fault_key)
            result[f'els_warn_flag_lane{rel_lane}'] = self._nested_get(
                faults, ec.WARN_FLAG_LANE_FIELD, warn_key)
        return result

    def get_transceiver_info(self):
        return {}

    def get_transceiver_dom_real_value(self):
        result = self.get_elsfp_lane_monitors() or {}
        return result

    def get_transceiver_threshold_info(self):
        result = self.get_elsfp_lane_thresholds() or {}
        result.update(self.get_elsfp_lane_setpoints() or {})
        return result

    def get_transceiver_dom_flags(self):
        result = self.get_elsfp_lane_flags() or {}
        return result

    def get_transceiver_status(self):
        result = self.get_elsfp_lane_state() or {}
        result.update(self.get_elsfp_control_mode() or {})
        result.update(self.get_elsfp_fault_warning_codes() or {})
        return result

    def get_transceiver_status_flags(self):
        result = self.get_elsfp_status_flags() or {}
        result.update(self.get_elsfp_output_fiber_checked() or {})
        return result
