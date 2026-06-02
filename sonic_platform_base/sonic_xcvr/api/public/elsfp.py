import typing

from .cmis import CmisApi
import sonic_platform_base.sonic_xcvr.fields.elsfp_consts as elsfp_consts

class ElsfpApi(CmisApi):

    def _unpack_lane_bits(self, field: str, num_lanes: int = 8) -> list[int]:
        """Read a per-lane bitmask field and unpack it into a per-lane list.

        Args:
            field:     EEPROM field name to read (returns a raw integer bitmask).
            num_lanes: Number of lanes to unpack. Defaults to 8.

        Returns:
            List of num_lanes integers (0 or 1), where index 0 corresponds to
            lane 1 (bit 0 of the raw value), index 1 to lane 2, etc.
        """
        raw = self.xcvr_eeprom.read(field)
        if raw is None:
            return None
        return [(raw >> lane) & 1 for lane in range(num_lanes)]

    def _set_lane_bits(self, field: str, lane_mask: int, value: bool) -> bool:
        """
        Set or clear lane bits in a per-lane EEPROM field.

        Args:
            field:     The EEPROM field name to read from and write to.
            lane_mask: Bitmask of lanes to update (bit 0 = lane 1, bit 1 = lane 2, etc.).
            value:     True to set the bits, False to clear them.

        Returns:
            True if the write succeeded, False otherwise.
        """
        current = self.xcvr_eeprom.read(field)
        if value:
            current |= lane_mask
        else:
            current &= ~lane_mask
        return self.xcvr_eeprom.write(field, current)

    #############################################################
    #              Module Advertisements (Page 1Ah)             #
    #############################################################

    def get_max_optical_power(self) -> float:
        # Returns maximum optical output power per lane in mW (raw register in 10 uW steps, scaled by 1/100)
        return self.xcvr_eeprom.read(elsfp_consts.MAX_OPTICAL_POWER)

    def get_min_optical_power(self) -> float:
        # Returns minimum optical output power per lane in mW (raw register in 10 uW steps, scaled by 1/100)
        return self.xcvr_eeprom.read(elsfp_consts.MIN_OPTICAL_POWER)

    def get_max_laser_bias(self) -> float:
        # Returns maximum laser bias current per lane in A (raw register in 100 uA steps, scaled by 1/10000)
        return self.xcvr_eeprom.read(elsfp_consts.MAX_LASER_BIAS)

    def get_min_laser_bias(self) -> float:
        # Returns minimum laser bias current per lane in A (raw register in 100 uA steps, scaled by 1/10000)
        return self.xcvr_eeprom.read(elsfp_consts.MIN_LASER_BIAS)

    def get_control_mode(self) -> str:
        return self.xcvr_eeprom.read(elsfp_consts.CONTROL_MODE_APC_ACC)

    def get_lane_count(self) -> int:
        return self.xcvr_eeprom.read(elsfp_consts.NUMBER_OF_LANES)

    def get_laser_bias_high_alarm(self) -> float:
        # Returns laser bias high alarm threshold in A (raw register in 100 uA steps, scaled by 1/10000)
        return self.xcvr_eeprom.read(elsfp_consts.BIAS_HIGH_ALARM)

    def get_laser_bias_low_alarm(self) -> float:
        # Returns laser bias low alarm threshold in A (raw register in 100 uA steps, scaled by 1/10000)
        return self.xcvr_eeprom.read(elsfp_consts.BIAS_LOW_ALARM)

    def get_laser_bias_high_warn(self) -> float:
        # Returns laser bias high warning threshold in A (raw register in 100 uA steps, scaled by 1/10000)
        return self.xcvr_eeprom.read(elsfp_consts.BIAS_HIGH_WARN)

    def get_laser_bias_low_warn(self) -> float:
        # Returns laser bias low warning threshold in A (raw register in 100 uA steps, scaled by 1/10000)
        return self.xcvr_eeprom.read(elsfp_consts.BIAS_LOW_WARN)

    def get_optical_power_high_alarm(self) -> float:
        # Returns optical power high alarm threshold in mW (raw register in 10 uW steps, scaled by 1/100)
        return self.xcvr_eeprom.read(elsfp_consts.OPT_POWER_HIGH_ALARM)

    def get_optical_power_low_alarm(self) -> float:
        # Returns optical power low alarm threshold in mW (raw register in 10 uW steps, scaled by 1/100)
        return self.xcvr_eeprom.read(elsfp_consts.OPT_POWER_LOW_ALARM)

    def get_optical_power_high_warn(self) -> float:
        # Returns optical power high warning threshold in mW (raw register in 10 uW steps, scaled by 1/100)
        return self.xcvr_eeprom.read(elsfp_consts.OPT_POWER_HIGH_WARN)

    def get_optical_power_low_warn(self) -> float:
        # Returns optical power low warning threshold in mW (raw register in 10 uW steps, scaled by 1/100)
        return self.xcvr_eeprom.read(elsfp_consts.OPT_POWER_LOW_WARN)

    ###############################################################
    #              Lane fault and warnings (Page 1Ah)             #
    ###############################################################

    def get_lane_summary_fault(self) -> bool:
        return self.xcvr_eeprom.read(elsfp_consts.LANE_SUMMARY_FAULT)

    def get_lane_summary_warning(self) -> bool:
        return self.xcvr_eeprom.read(elsfp_consts.LANE_SUMMARY_WARNING)

    def get_per_lane_fault_flags(self) -> dict[str, int]:
        """
        This function will return a dictionary mapping lanes to an integer representing
        whether the lane has had a fault or not (0 == no fault, 1 == fault)

        Example:
          {
              "FaultFlagLane1": 0,
              "FaultFlagLane2": 1,
              "FaultFlagLane3": 0,
              # ... etc ...
              "FaultFlagLane32": 1,
          }
        """
        return self.xcvr_eeprom.read(elsfp_consts.FAULT_FLAG_LANE_FIELD)

    def get_per_lane_warn_flags(self) -> dict[str, int]:
        """
        This function will return a dictionary mapping lanes to an integer representing
        whether the lane has had a warning or not (0 == no warning, 1 == warning)

        Example:
          {
              "WarnFlagLane1": 0,
              "WarnFlagLane2": 1,
              "WarnFlagLane3": 0,
              # ... etc ...
              "WarnFlagLane32": 1,
          }
        """
        return self.xcvr_eeprom.read(elsfp_consts.WARN_FLAG_LANE_FIELD)

    ###############################################################
    #              Lane setting and saving and restoring          #
    #              factory/customer settings (Page 1Ah)           #
    ###############################################################

    def write_save_restore_command(self, command: elsfp_consts.SaveRestoreCommand) -> bool:
        return self.xcvr_eeprom.write(elsfp_consts.SAVE_RESTORE_COMMAND, command.value)

    def get_save_restore_confirmation(self) -> elsfp_consts.SaveRestoreConfirmationCode:
        value = self.xcvr_eeprom.read(elsfp_consts.SAVE_RESTORE_CONFIRM)
        return elsfp_consts.SaveRestoreConfirmationCode(value)

    ###############################################################
    #         Alarms/warnings values, alarm/warning codes         #
    #           and masks for set lane bank (Page 1Ah)            #
    ###############################################################

    def get_per_lane_high_bias_alarms(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.HIGH_BIAS_ALARM_INDEXED_FIELD)

    def get_per_lane_low_bias_alarms(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.LOW_BIAS_ALARM_INDEXED_FIELD)

    def get_per_lane_high_bias_warnings(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.HIGH_BIAS_WARN_INDEXED_FIELD)

    def get_per_lane_low_bias_warnings(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.LOW_BIAS_WARN_INDEXED_FIELD)

    def get_per_lane_high_power_alarms(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.HIGH_POWER_ALARM_INDEXED_FIELD)

    def get_per_lane_low_power_alarms(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.LOW_POWER_ALARM_INDEXED_FIELD)

    def get_per_lane_high_power_warnings(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.HIGH_POWER_WARN_INDEXED_FIELD)

    def get_per_lane_low_power_warnings(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.LOW_POWER_WARN_INDEXED_FIELD)

    def get_per_lane_high_bias_alarm_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.HIGH_BIAS_ALARM_MASK_FIELD)

    def set_per_lane_high_bias_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.HIGH_BIAS_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_low_bias_alarm_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.LOW_BIAS_ALARM_MASK_FIELD)

    def set_per_lane_low_bias_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LOW_BIAS_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_high_bias_warning_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.HIGH_BIAS_WARN_MASK_FIELD)

    def set_per_lane_high_bias_warning_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.HIGH_BIAS_WARN_MASK_FIELD, lane_mask, masked)

    def get_per_lane_low_bias_warning_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.LOW_BIAS_WARN_MASK_FIELD)

    def set_per_lane_low_bias_warning_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LOW_BIAS_WARN_MASK_FIELD, lane_mask, masked)

    def get_per_lane_high_power_alarm_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.HIGH_POWER_ALARM_MASK_FIELD)

    def set_per_lane_high_power_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.HIGH_POWER_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_low_power_alarm_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.LOW_POWER_ALARM_MASK_FIELD)

    def set_per_lane_low_power_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LOW_POWER_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_high_power_warning_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.HIGH_POWER_WARN_MASK_FIELD)

    def set_per_lane_high_power_warning_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.HIGH_POWER_WARN_MASK_FIELD, lane_mask, masked)

    def get_per_lane_low_power_warning_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.LOW_POWER_WARN_MASK_FIELD)

    def set_per_lane_low_power_warning_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LOW_POWER_WARN_MASK_FIELD, lane_mask, masked)

    # Global alarm and warning masks

    def get_per_lane_global_alarm_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.GLOBAL_ALARM_MASK_FIELD)

    def set_per_lane_global_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.GLOBAL_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_global_warn_mask(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.GLOBAL_WARN_MASK_FIELD)

    def set_per_lane_global_warn_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.GLOBAL_WARN_MASK_FIELD, lane_mask, masked)

    def get_per_lane_fault_code(self) -> dict[str, str]:
        return self.xcvr_eeprom.read(elsfp_consts.FAULT_CODE_FIELD)

    def get_per_lane_warning_code(self) -> dict[str, str]:
        return self.xcvr_eeprom.read(elsfp_consts.WARNING_CODE_FIELD)

    ###############################################################
    #          Per lane enable/disable control and lane           #
    #             state for set lane bank (Page 1Ah)              #
    ###############################################################

    def get_per_lane_enable(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.LANE_ENABLE_FIELD)

    def set_per_lane_enable(self, lane_mask: int, enabled: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LANE_ENABLE_FIELD, lane_mask, enabled)

    def get_per_lane_state(self) -> dict[str, str]:
        return self.xcvr_eeprom.read(elsfp_consts.LANE_STATE_FIELD)

    ###############################################################
    #    Per lane output fiber link checked flag for selected     #
    #                  lane bank (Page 1Ah)                       #
    ###############################################################

    def get_per_lane_output_fiber_checked(self) -> list[int]:
        return self._unpack_lane_bits(elsfp_consts.OUTPUT_FIBER_CHECKED_FLAG_LANE_FIELD)

    def set_lane_output_fiber_checked(self, lane_mask: int, checked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.OUTPUT_FIBER_CHECKED_FLAG_LANE_FIELD, lane_mask, checked)

    ###############################################################
    #       Additional per lane information such as lane to       #
    #      fiber mapping and reference frequency for 8 lanes      #
    #                for set lane bank (Page 1Ah)                 #
    ###############################################################

    def get_lane_to_fiber_mapping(self) -> dict[str, int]:
        return self.xcvr_eeprom.read(elsfp_consts.LANE_TO_FIBER_MAPPING_FIELD)

    def get_per_lane_freq(self) -> dict[str, float]:
        # Returns per-lane frequency in GHz (raw register in 5 GHz steps, scaled by 1/0.2)
        return self.xcvr_eeprom.read(elsfp_consts.LANE_FREQ_FIELD)

    def get_opt_check_power_setpoint(self) -> int:
        # Returns optical power setpoint for fiber check in mW (raw register in 1 mW steps)
        return self.xcvr_eeprom.read(elsfp_consts.OPT_CHECK_POWER_SETPOINT)

    ###############################################################
    #             Current Optical power setpoints, if             #
    #           supported for selected bank. (Page 1Bh)           #
    ###############################################################

    def get_per_lane_bias_current_setpoint(self) -> dict[str, float]:
        # Returns per-lane bias current setpoint in A (raw register in 100 uA steps, scaled by 1/10000)
        return self.xcvr_eeprom.read(elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD)

    def set_lane_bias_current_setpoint(self, lane: int, current: float) -> bool:
        # current is in A (raw register in 100 uA steps, scaled by 1/10000)
        field_name = f"{elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD}{lane}"
        return self.xcvr_eeprom.write(field_name, current)

    def get_per_lane_opt_power_setpoint(self) -> dict[str, float]:
        # Returns per-lane optical power setpoint in mW (raw register in 10 uW steps, scaled by 1/100)
        return self.xcvr_eeprom.read(elsfp_consts.OPT_POWER_SETPOINT_FIELD)

    def set_lane_opt_power_setpoint(self, lane: int, power: float) -> bool:
        # power is in mW (raw register in 10 uW steps, scaled by 1/100)
        field_name = f"{elsfp_consts.OPT_POWER_SETPOINT_FIELD}{lane}"
        return self.xcvr_eeprom.write(field_name, power)

    ###############################################################
    #            Current/optical/voltage monitors for             #
    #                  selected bank. (Page 1Bh)                  #
    ###############################################################

    def get_per_lane_bias_current_monitor(self) -> dict[str, float]:
        # Returns per-lane bias current monitor in A (raw register in 100 uA steps, scaled by 1/10000)
        return self.xcvr_eeprom.read(elsfp_consts.BIAS_CURRENT_MONITOR_FIELD)

    def get_per_lane_opt_power_monitor(self) -> dict[str, float]:
        # Returns per-lane optical power monitor in mW (raw register in 10 uW steps, scaled by 1/100)
        return self.xcvr_eeprom.read(elsfp_consts.OPT_POWER_MONITOR_FIELD)

    def get_per_lane_voltage_monitor(self) -> dict[str, float]:
        # Returns per-lane voltage monitor in V (raw register in 15 mV steps, scaled by 15/1000)
        return self.xcvr_eeprom.read(elsfp_consts.VOLTAGE_MONITOR_FIELD)

    def get_icc_monitor(self) -> float:
        # Returns VCC current monitor in A (raw register in 200 uA steps, scaled by 1/5000)
        return self.xcvr_eeprom.read(elsfp_consts.ICC_MONITOR)

    #############################################################
    #   CmisApi methods not supported by ELSFP                  #
    #                                                           #
    #   ELSFP supports: lower memory, pages 00h, 01h, 02h,      #
    #   03h, 9Fh, A0h-AFh, 1Ah, 1Bh.                            #
    #                                                           #
    #   Pages 10h, 11h, 12h, 13h, 2Fh are not present in the    #
    #   ELSFP memory map and the methods below reflect that.    #
    #   Note: we leave the VDM methods available for use,       #
    #   since a vendor could conceivably implement VDM          #
    #   observables for an ELSFP despite VDM not being          #
    #   mentioned in the spec.                                  #
    #############################################################

    # Page 10h — Lane Datapath Config

    def tx_disable(self, tx_disable):
        raise NotImplementedError

    def rx_disable(self, rx_disable):
        raise NotImplementedError

    def get_tx_config_power(self):
        raise NotImplementedError

    def get_application(self, lane):
        raise NotImplementedError

    def set_application(self, channel, appl_code, ec=0):
        raise NotImplementedError

    def set_datapath_init(self, channel):
        raise NotImplementedError

    def set_datapath_deinit(self, channel):
        raise NotImplementedError

    def get_datapath_deinit(self):
        raise NotImplementedError

    def scs_apply_datapath_init(self, channel):
        raise NotImplementedError

    def decommission_all_datapaths(self):
        raise NotImplementedError

    def scs_lane_write(self, si_param, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_output_eq_pre_cursor_target_rx(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_output_eq_post_cursor_target_rx(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_output_amp_target_rx(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_fixed_input_target_tx(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_adaptive_input_eq_recall_tx(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_adaptive_input_eq_enable_tx(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_cdr_tx(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_cdr_rx(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_rx_si_settings(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_tx_si_settings(self, host_lanes_mask, si_settings_dict):
        raise NotImplementedError

    def stage_custom_si_settings(self, host_lanes_mask, optics_si_dict):
        raise NotImplementedError

    # Page 11h — Lane Datapath Status

    def get_tx_output_status(self):
        raise NotImplementedError

    def get_rx_output_status(self):
        raise NotImplementedError

    def get_config_datapath_hostlane_status(self):
        raise NotImplementedError

    def get_datapath_state(self):
        raise NotImplementedError

    def get_dpinit_pending(self):
        raise NotImplementedError

    def get_alarm_flags(self, alarm_flag):
        raise NotImplementedError

    def get_tx_power_flag(self):
        raise NotImplementedError

    def get_tx_bias_flag(self):
        raise NotImplementedError

    def get_rx_power_flag(self):
        raise NotImplementedError

    # Page 12h — Tunable Laser Ctrl/Status

    def get_laser_tuning_summary(self):
        raise NotImplementedError

    # Page 13h — Module Perf Diag Ctrl

    def get_loopback_capability(self):
        raise NotImplementedError

    def get_media_output_loopback(self):
        raise NotImplementedError

    def get_media_input_loopback(self):
        raise NotImplementedError

    def get_host_output_loopback(self):
        raise NotImplementedError

    def get_host_input_loopback(self):
        raise NotImplementedError

    def set_host_input_loopback(self, lane_mask, enable):
        raise NotImplementedError

    def set_host_output_loopback(self, lane_mask, enable):
        raise NotImplementedError

    def set_media_input_loopback(self, lane_mask, enable):
        raise NotImplementedError

    def set_media_output_loopback(self, lane_mask, enable):
        raise NotImplementedError

    def set_loopback_mode(self, loopback_mode, lane_mask=0xff, enable=False):
        raise NotImplementedError

    # C-CMIS

    def get_supported_power_config(self):
        raise NotImplementedError

    # Aggregate methods that access unsupported pages

    def get_transceiver_dom_flags(self):
        raise NotImplementedError

    def get_transceiver_status(self):
        raise NotImplementedError

    def get_transceiver_loopback(self):
        raise NotImplementedError

    def get_error_description(self):
        raise NotImplementedError
