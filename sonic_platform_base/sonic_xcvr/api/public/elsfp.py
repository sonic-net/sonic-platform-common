import copy
import typing

from ..xcvr_api import XcvrApi
from ...fields import consts
from ...mem_maps.public.cmis.pages.consts import CMIS_LANES_PER_BANK
import sonic_platform_base.sonic_xcvr.fields.elsfp_consts as elsfp_consts

ELSFP_INFO_DEFAULT_DICT = {
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
        "cable_type": "N/A",
        "media_interface_technology": "N/A",
        "vendor_rev": "N/A",
        "cmis_rev": "N/A",
        "specification_compliance": "N/A",
        "vdm_supported": "N/A",
        "cdb_supported": "N/A",
        "lane_count": "N/A",
        "control_mode": "N/A",
        "max_optical_power": "N/A",
        "min_optical_power": "N/A",
        "max_laser_bias": "N/A",
        "min_laser_bias": "N/A"
        }


ELSFP_NON_BANKED_DOM_REAL_VALUE_DEFAULT_DICT = {
        "temperature": "N/A",
        "voltage": "N/A"
        }

ELSFP_BANKED_DOM_REAL_VALUE_DEFAULT_DICT = {
        "icc": "N/A"
        }

ELSFP_DOM_REAL_VALUE_DEFAULT_DICT = {
        **ELSFP_NON_BANKED_DOM_REAL_VALUE_DEFAULT_DICT,
        **ELSFP_BANKED_DOM_REAL_VALUE_DEFAULT_DICT
        }

class ElsfpApi(XcvrApi):

    def _read_lane_bits(self, field: str, num_lanes: int = 8) -> list[int]:
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

        Raises:
            ValueError: If lane_mask has bits set outside the 8-lane range (0x00-0xFF).
        """
        if lane_mask & ~0xFF:
            raise ValueError("lane_mask 0x%X has bits set outside the 8-lane range (0x00-0xFF)" % lane_mask)
        current = self.xcvr_eeprom.read(field)
        if current is None:
            return False
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

    def get_per_lane_fault_flags(self) -> dict[str, bool]:
        """
        This function will return a dictionary mapping lanes to a boolean representing
        whether the lane has had a fault or not

        These flags are latched and cleared on read. Only the 8 lanes of the
        currently selected bank are read and reported; the other banks' flags are
        left latched for a read at that bank. Lanes are numbered absolutely, so
        bank 0 reports lanes 1-8, bank 1 reports lanes 9-16, and so on.

        Example (bank 1):
          {
              "FaultFlagLane9": False,
              "FaultFlagLane10": True,
              "FaultFlagLane11": False,
              # ... etc ...
              "FaultFlagLane16": True,
          }
        """
        flags = self.xcvr_eeprom.read(elsfp_consts.FAULT_FLAG_LANE_FIELDS[self.xcvr_eeprom.mem_map.bank])
        if flags is None:
            return None
        return {field: bool(value) for field, value in flags.items()}

    def get_per_lane_warn_flags(self) -> dict[str, bool]:
        """
        This function will return a dictionary mapping lanes to a boolean representing
        whether the lane has had a warning or not

        These flags are latched and cleared on read. Only the 8 lanes of the
        currently selected bank are read and reported; the other banks' flags are
        left latched for a read at that bank. Lanes are numbered absolutely, so
        bank 0 reports lanes 1-8, bank 1 reports lanes 9-16, and so on.

        Example (bank 1):
          {
              "WarnFlagLane9": False,
              "WarnFlagLane10": True,
              "WarnFlagLane11": False,
              # ... etc ...
              "WarnFlagLane16": True,
          }
        """
        flags = self.xcvr_eeprom.read(elsfp_consts.WARN_FLAG_LANE_FIELDS[self.xcvr_eeprom.mem_map.bank])
        if flags is None:
            return None
        return {field: bool(value) for field, value in flags.items()}

    ###############################################################
    #              Lane setting and saving and restoring          #
    #              factory/customer settings (Page 1Ah)           #
    ###############################################################

    def write_save_restore_command(self, command: elsfp_consts.SaveRestoreCommand) -> bool:
        return self.xcvr_eeprom.write(elsfp_consts.SAVE_RESTORE_COMMAND, command.value)

    def get_save_restore_confirmation(self) -> elsfp_consts.SaveRestoreConfirmationCode:
        value = self.xcvr_eeprom.read(elsfp_consts.SAVE_RESTORE_CONFIRM)
        try:
            return elsfp_consts.SaveRestoreConfirmationCode(value)
        except ValueError:
            return elsfp_consts.SaveRestoreConfirmationCode.UNKNOWN

    ###############################################################
    #         Alarms/warnings values, alarm/warning codes         #
    #           and masks for set lane bank (Page 1Ah)            #
    ###############################################################

    def get_per_lane_high_bias_alarms(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.HIGH_BIAS_ALARM_INDEXED_FIELD)

    def get_per_lane_low_bias_alarms(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.LOW_BIAS_ALARM_INDEXED_FIELD)

    def get_per_lane_high_bias_warnings(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.HIGH_BIAS_WARN_INDEXED_FIELD)

    def get_per_lane_low_bias_warnings(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.LOW_BIAS_WARN_INDEXED_FIELD)

    def get_per_lane_high_power_alarms(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.HIGH_POWER_ALARM_INDEXED_FIELD)

    def get_per_lane_low_power_alarms(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.LOW_POWER_ALARM_INDEXED_FIELD)

    def get_per_lane_high_power_warnings(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.HIGH_POWER_WARN_INDEXED_FIELD)

    def get_per_lane_low_power_warnings(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.LOW_POWER_WARN_INDEXED_FIELD)

    def get_per_lane_high_bias_alarm_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.HIGH_BIAS_ALARM_MASK_FIELD)

    def set_per_lane_high_bias_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.HIGH_BIAS_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_low_bias_alarm_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.LOW_BIAS_ALARM_MASK_FIELD)

    def set_per_lane_low_bias_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LOW_BIAS_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_high_bias_warning_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.HIGH_BIAS_WARN_MASK_FIELD)

    def set_per_lane_high_bias_warning_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.HIGH_BIAS_WARN_MASK_FIELD, lane_mask, masked)

    def get_per_lane_low_bias_warning_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.LOW_BIAS_WARN_MASK_FIELD)

    def set_per_lane_low_bias_warning_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LOW_BIAS_WARN_MASK_FIELD, lane_mask, masked)

    def get_per_lane_high_power_alarm_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.HIGH_POWER_ALARM_MASK_FIELD)

    def set_per_lane_high_power_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.HIGH_POWER_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_low_power_alarm_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.LOW_POWER_ALARM_MASK_FIELD)

    def set_per_lane_low_power_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LOW_POWER_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_high_power_warning_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.HIGH_POWER_WARN_MASK_FIELD)

    def set_per_lane_high_power_warning_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.HIGH_POWER_WARN_MASK_FIELD, lane_mask, masked)

    def get_per_lane_low_power_warning_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.LOW_POWER_WARN_MASK_FIELD)

    def set_per_lane_low_power_warning_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LOW_POWER_WARN_MASK_FIELD, lane_mask, masked)

    # Global alarm and warning masks

    def get_per_lane_global_alarm_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.GLOBAL_ALARM_MASK_FIELD)

    def set_per_lane_global_alarm_mask(self, lane_mask: int, masked: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.GLOBAL_ALARM_MASK_FIELD, lane_mask, masked)

    def get_per_lane_global_warn_mask(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.GLOBAL_WARN_MASK_FIELD)

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
        return self._read_lane_bits(elsfp_consts.LANE_ENABLE_FIELD)

    def set_per_lane_enable(self, lane_mask: int, enabled: bool) -> bool:
        return self._set_lane_bits(elsfp_consts.LANE_ENABLE_FIELD, lane_mask, enabled)

    def get_per_lane_state(self) -> dict[str, str]:
        return self.xcvr_eeprom.read(elsfp_consts.LANE_STATE_FIELD)

    ###############################################################
    #    Per lane output fiber link checked flag for selected     #
    #                  lane bank (Page 1Ah)                       #
    ###############################################################

    def get_per_lane_output_fiber_checked(self) -> list[int]:
        return self._read_lane_bits(elsfp_consts.OUTPUT_FIBER_CHECKED_FLAG_LANE_FIELD)

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

    def get_opt_check_power_setpoint(self) -> float:
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

    ###############################################################
    #           Module monitors (Page 00h lower memory)           #
    ###############################################################

    def get_module_temperature(self) -> float:
        # Returns module case temperature in deg C
        temperature = self.xcvr_eeprom.read(consts.TEMPERATURE_FIELD)
        if temperature is None:
            return None
        return float("{:.3f}".format(temperature))

    def get_module_voltage(self) -> float:
        # Returns the monitored value of the 3.3 V supply voltage in V
        voltage = self.xcvr_eeprom.read(consts.VOLTAGE_FIELD)
        if voltage is None:
            return None
        return float("{:.3f}".format(voltage))

    def get_module_state(self) -> str:
        # Returns the CMIS module state, e.g. "ModuleReady"
        return self.xcvr_eeprom.read(consts.MODULE_STATE)

    def get_module_fault_cause(self) -> str:
        # Returns the fault cause reported when the module state is ModuleFault
        return self.xcvr_eeprom.read(consts.MODULE_FAULT_CAUSE)

    def get_module_firmware_fault_info(self) -> dict[str, bool]:
        """
        This function returns the firmware fault and module state change flags
        packed into the low 3 bits of byte 8.

        Returns:
          {
              "datapath_firmware_fault": False,
              "module_firmware_fault": True,
              "module_state_changed": True,
          }
        """
        firmware_fault_info = self.xcvr_eeprom.read(consts.MODULE_FIRMWARE_FAULT_INFO)
        if firmware_fault_info is None:
            return None
        return {
            "datapath_firmware_fault": bool((firmware_fault_info >> 2) & 0x1),
            "module_firmware_fault": bool((firmware_fault_info >> 1) & 0x1),
            "module_state_changed": bool(firmware_fault_info & 0x1)
        }

    def is_cdb_supported(self) -> bool:
        """
        Returns whether the module advertises CDB support
        """
        cdb_inst = self.xcvr_eeprom.read(consts.CDB_SUPPORT)
        if cdb_inst is None:
            return None
        return cdb_inst == 1 or cdb_inst == 2

    ###############################################################
    #      Aggregate APIs consumed directly by the xcvrd daemon   #
    ###############################################################

    def get_elsfp_info(self) -> dict:
        admin_info = self.xcvr_eeprom.read(consts.ADMIN_INFO_FIELD)
        if admin_info is None:
            return None

        ext_id = admin_info[consts.EXT_ID_FIELD]
        power_class = ext_id[consts.POWER_CLASS_FIELD]
        max_power = ext_id[consts.MAX_POWER_FIELD]

        hw_major_rev = self.xcvr_eeprom.read(consts.HW_MAJOR_REV)
        hw_minor_rev = self.xcvr_eeprom.read(consts.HW_MINOR_REV)
        hardware_rev = None if hw_major_rev is None or hw_minor_rev is None \
            else "%s.%s" % (hw_major_rev, hw_minor_rev)

        lane_to_fiber_mapping = self.get_lane_to_fiber_mapping()
        lane_frequency = self.get_per_lane_freq()
        max_optical_power = self.get_max_optical_power()
        min_optical_power = self.get_min_optical_power()
        max_laser_bias = self.get_max_laser_bias()
        min_laser_bias = self.get_min_laser_bias()
        if None in (lane_to_fiber_mapping, lane_frequency, max_optical_power, min_optical_power,
                    max_laser_bias, min_laser_bias):
            return None

        info = copy.deepcopy(ELSFP_INFO_DEFAULT_DICT)
        info.update({
            "type": admin_info[consts.ID_FIELD],
            "type_abbrv_name": admin_info[consts.ID_ABBRV_FIELD],
            "hardware_rev": hardware_rev,
            "serial": admin_info[consts.VENDOR_SERIAL_NO_FIELD].rstrip(),
            "manufacturer": admin_info[consts.VENDOR_NAME_FIELD].rstrip(),
            "model": admin_info[consts.VENDOR_PART_NO_FIELD].rstrip(),
            "connector": admin_info[consts.CONNECTOR_FIELD],
            "ext_identifier": "%s (%sW Max)" % (power_class, max_power),
            "cable_length": float(admin_info[consts.LENGTH_ASSEMBLY_FIELD]),
            "vendor_date": admin_info[consts.VENDOR_DATE_FIELD].rstrip(),
            "vendor_oui": admin_info[consts.VENDOR_OUI_FIELD],
            "cable_type": "Length Cable Assembly(m)",
            "media_interface_technology": admin_info[consts.MEDIA_INTERFACE_TECH],
            "vendor_rev": admin_info[consts.VENDOR_REV_FIELD].rstrip(),
            "cmis_rev": "%s.%s" % (admin_info[consts.CMIS_MAJOR_REVISION],
                                   admin_info[consts.CMIS_MINOR_REVISION]),
            "specification_compliance": admin_info[consts.MEDIA_TYPE_FIELD],
            "vdm_supported": self.xcvr_eeprom.read(consts.VDM_SUPPORTED),
            "cdb_supported": self.is_cdb_supported(),
            "lane_count": self.get_lane_count(),
            "control_mode": self.get_control_mode(),
            "max_optical_power": float("{:.3f}".format(self.mw_to_dbm(max_optical_power))),
            "min_optical_power": float("{:.3f}".format(self.mw_to_dbm(min_optical_power))),
            "max_laser_bias": float("{:.3f}".format(self.amps_to_ma(max_laser_bias))),
            "min_laser_bias": float("{:.3f}".format(self.amps_to_ma(min_laser_bias)))
        })

        # Per-lane fields are flattened to "<name>_lane<N>" scalars, with N the
        # absolute lane number for the selected bank.
        first_lane = self.xcvr_eeprom.mem_map.bank * CMIS_LANES_PER_BANK + 1
        for name, field, values in (("fiber_mapping", elsfp_consts.LANE_TO_FIBER_MAPPING_FIELD,
                                     lane_to_fiber_mapping),
                                    ("frequency", elsfp_consts.LANE_FREQ_FIELD, lane_frequency)):
            for index in range(len(values)):
                info["%s_lane%d" % (name, first_lane + index)] = values["%s%d" % (field, index + 1)]

        # A 'None' means an EEPROM read failed, so return 'None' to tell the
        # caller to retry rather than handing back a partial dict.
        if None in info.values():
            return None
        return info

    def get_elsfp_info_firmware_versions(self) -> dict:
        # TODO: Currently this function just reads the firmware version
        # information from lower memory. Once CDB support is added to ElsfpApi, we
        # should only read from lower memory if CDB support is not advertised by the
        # module.
        active_fw_major = self.xcvr_eeprom.read(consts.ACTIVE_FW_MAJOR_REV)
        active_fw_minor = self.xcvr_eeprom.read(consts.ACTIVE_FW_MINOR_REV)
        inactive_fw_major = self.xcvr_eeprom.read(consts.INACTIVE_FW_MAJOR_REV)
        inactive_fw_minor = self.xcvr_eeprom.read(consts.INACTIVE_FW_MINOR_REV)
        if None in (active_fw_major, active_fw_minor, inactive_fw_major, inactive_fw_minor):
            return None

        return {
            "active_firmware": "%s.%s" % (active_fw_major, active_fw_minor),
            "inactive_firmware": "%s.%s" % (inactive_fw_major, inactive_fw_minor)
        }

    def get_non_banked_elsfp_dom_real_value(self) -> dict:
        dom = copy.deepcopy(ELSFP_NON_BANKED_DOM_REAL_VALUE_DEFAULT_DICT)
        dom.update({
            "temperature": self.get_module_temperature(),
            "voltage": self.get_module_voltage()
        })

        if None in dom.values():
            return None
        return dom

    def get_banked_elsfp_dom_real_value(self) -> dict:
        bias_current = self.get_per_lane_bias_current_monitor()
        optical_power = self.get_per_lane_opt_power_monitor()
        voltage = self.get_per_lane_voltage_monitor()
        icc = self.get_icc_monitor()
        if None in (bias_current, optical_power, voltage, icc):
            return None

        dom = copy.deepcopy(ELSFP_BANKED_DOM_REAL_VALUE_DEFAULT_DICT)
        dom["icc"] = icc

        # Per-lane monitors are flattened to "<name>_lane<N>" scalars, with N the
        # absolute lane number for the selected bank. Units are normalized to
        # match the units that their associated thresholds are reported in.
        first_lane = self.xcvr_eeprom.mem_map.bank * CMIS_LANES_PER_BANK + 1
        for name, field, values, convert in (
                ("laser_bias_current", elsfp_consts.BIAS_CURRENT_MONITOR_FIELD, bias_current, self.amps_to_ma),
                ("optical_power", elsfp_consts.OPT_POWER_MONITOR_FIELD, optical_power, self.mw_to_dbm),
                ("voltage", elsfp_consts.VOLTAGE_MONITOR_FIELD, voltage, lambda volts: volts)):
            for index in range(len(values)):
                value = convert(values["%s%d" % (field, index + 1)])
                dom["%s_lane%d" % (name, first_lane + index)] = float("{:.3f}".format(value))
        return dom

    def get_elsfp_dom_real_value(self) -> dict:
        # A 'None' from either half means an EEPROM read failed, so return 'None'
        # to tell the caller to retry rather than handing back a partial dict.
        non_banked_dom = self.get_non_banked_elsfp_dom_real_value()
        banked_dom = self.get_banked_elsfp_dom_real_value()
        if non_banked_dom is None or banked_dom is None:
            return None
        return {**non_banked_dom, **banked_dom}

    def get_non_banked_elsfp_dom_flags(self) -> dict:
        module_flag_byte1 = self.xcvr_eeprom.read(consts.MODULE_FLAG_BYTE1)
        if module_flag_byte1 is None:
            return None

        # Byte 9 packs the case temperature flags into its low nibble and the
        # supply voltage flags into its high nibble, each ordered high alarm,
        # low alarm, high warning, low warning.
        flags = {}
        for monitor, nibble in (("temperature", module_flag_byte1 & 0xF),
                                ("voltage", (module_flag_byte1 >> 4) & 0xF)):
            flags.update({
                "%s_alarm_high" % monitor: bool(nibble & 0x1),
                "%s_alarm_low" % monitor: bool((nibble >> 1) & 0x1),
                "%s_warn_high" % monitor: bool((nibble >> 2) & 0x1),
                "%s_warn_low" % monitor: bool((nibble >> 3) & 0x1)
            })
        return flags

    def get_banked_elsfp_dom_flags(self) -> dict:
        alarms = {
            "laser_bias_alarm_high": self.get_per_lane_high_bias_alarms(),
            "laser_bias_alarm_low": self.get_per_lane_low_bias_alarms(),
            "optical_power_alarm_high": self.get_per_lane_high_power_alarms(),
            "optical_power_alarm_low": self.get_per_lane_low_power_alarms()
        }
        warnings = {
            "laser_bias_warn_high": self.get_per_lane_high_bias_warnings(),
            "laser_bias_warn_low": self.get_per_lane_low_bias_warnings(),
            "optical_power_warn_high": self.get_per_lane_high_power_warnings(),
            "optical_power_warn_low": self.get_per_lane_low_power_warnings()
        }
        if None in alarms.values() or None in warnings.values():
            return None

        flags = {}
        first_lane = self.xcvr_eeprom.mem_map.bank * CMIS_LANES_PER_BANK + 1
        for index in range(CMIS_LANES_PER_BANK):
            lane = first_lane + index
            for name, lane_bits in {**alarms, **warnings}.items():
                flags["%s_lane%d" % (name, lane)] = bool(lane_bits[index])
        return flags

    def get_elsfp_dom_flags(self) -> dict:
        # A 'None' from either half means an EEPROM read failed, so return 'None'
        # to tell the caller to retry rather than handing back a partial dict.
        non_banked_flags = self.get_non_banked_elsfp_dom_flags()
        banked_flags = self.get_banked_elsfp_dom_flags()
        if non_banked_flags is None or banked_flags is None:
            return None
        return {**non_banked_flags, **banked_flags}

    def get_elsfp_threshold_info(self) -> dict:
        # ELSFP specific thresholds (Page 1Ah)
        bias_thresholds = {
            "laser_bias_alarm_high": self.get_laser_bias_high_alarm(),
            "laser_bias_alarm_low": self.get_laser_bias_low_alarm(),
            "laser_bias_warn_high": self.get_laser_bias_high_warn(),
            "laser_bias_warn_low": self.get_laser_bias_low_warn()
        }
        optical_power_thresholds = {
            "optical_power_alarm_high": self.get_optical_power_high_alarm(),
            "optical_power_alarm_low": self.get_optical_power_low_alarm(),
            "optical_power_warn_high": self.get_optical_power_high_warn(),
            "optical_power_warn_low": self.get_optical_power_low_warn()
        }
        if None in bias_thresholds.values() or None in optical_power_thresholds.values():
            return None

        threshold_info = {
            **{name: float("{:.3f}".format(self.amps_to_ma(amps))) for name, amps in bias_thresholds.items()},
            **{name: float("{:.3f}".format(self.mw_to_dbm(mw)))
               for name, mw in optical_power_thresholds.items()}
        }

        # Standard CMIS module thresholds (Page 02h).
        thresh = self.xcvr_eeprom.read(consts.THRESHOLDS_FIELD)
        tx_bias_scale_raw = self.xcvr_eeprom.read(consts.TX_BIAS_SCALE)
        if thresh is None or tx_bias_scale_raw is None:
            return None
        tx_bias_scale = 2**tx_bias_scale_raw if tx_bias_scale_raw < 3 else 1

        threshold_info.update({
            "temperature_alarm_high": float("{:.3f}".format(thresh[consts.TEMP_HIGH_ALARM_FIELD])),
            "temperature_alarm_low": float("{:.3f}".format(thresh[consts.TEMP_LOW_ALARM_FIELD])),
            "temperature_warn_high": float("{:.3f}".format(thresh[consts.TEMP_HIGH_WARNING_FIELD])),
            "temperature_warn_low": float("{:.3f}".format(thresh[consts.TEMP_LOW_WARNING_FIELD])),
            "voltage_alarm_high": float("{:.3f}".format(thresh[consts.VOLTAGE_HIGH_ALARM_FIELD])),
            "voltage_alarm_low": float("{:.3f}".format(thresh[consts.VOLTAGE_LOW_ALARM_FIELD])),
            "voltage_warn_high": float("{:.3f}".format(thresh[consts.VOLTAGE_HIGH_WARNING_FIELD])),
            "voltage_warn_low": float("{:.3f}".format(thresh[consts.VOLTAGE_LOW_WARNING_FIELD])),
            "rxpowerhighalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_HIGH_ALARM_FIELD]))),
            "rxpowerlowalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_LOW_ALARM_FIELD]))),
            "rxpowerhighwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_HIGH_WARNING_FIELD]))),
            "rxpowerlowwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.RX_POWER_LOW_WARNING_FIELD]))),
            "txpowerhighalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_HIGH_ALARM_FIELD]))),
            "txpowerlowalarm": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_LOW_ALARM_FIELD]))),
            "txpowerhighwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_HIGH_WARNING_FIELD]))),
            "txpowerlowwarning": float("{:.3f}".format(self.mw_to_dbm(thresh[consts.TX_POWER_LOW_WARNING_FIELD]))),
            "txbiashighalarm": float("{:.3f}".format(thresh[consts.TX_BIAS_HIGH_ALARM_FIELD] * tx_bias_scale)),
            "txbiaslowalarm": float("{:.3f}".format(thresh[consts.TX_BIAS_LOW_ALARM_FIELD] * tx_bias_scale)),
            "txbiashighwarning": float("{:.3f}".format(thresh[consts.TX_BIAS_HIGH_WARNING_FIELD] * tx_bias_scale)),
            "txbiaslowwarning": float("{:.3f}".format(thresh[consts.TX_BIAS_LOW_WARNING_FIELD] * tx_bias_scale))
        })

        return threshold_info

    def get_non_banked_elsfp_status(self) -> dict:
        status = {
            "module_state": self.get_module_state(),
            "module_fault_cause": self.get_module_fault_cause()
        }
        if None in status.values():
            return None
        return status

    def get_banked_elsfp_status(self) -> dict:
        lane_enable = self.get_per_lane_enable()
        lane_state = self.get_per_lane_state()
        output_fiber_checked = self.get_per_lane_output_fiber_checked()
        fault_code = self.get_per_lane_fault_code()
        warning_code = self.get_per_lane_warning_code()
        if lane_enable is None or lane_state is None or output_fiber_checked is None \
                or fault_code is None or warning_code is None:
            return None

        status = {}
        first_lane = self.xcvr_eeprom.mem_map.bank * CMIS_LANES_PER_BANK + 1
        for index, enabled in enumerate(lane_enable):
            status["enable_lane%d" % (first_lane + index)] = bool(enabled)

        for index in range(len(lane_state)):
            status["state_lane%d" % (first_lane + index)] = \
                lane_state["%s%d" % (elsfp_consts.LANE_STATE_FIELD, index + 1)]

        for index, checked in enumerate(output_fiber_checked):
            status["output_fiber_checked_lane%d" % (first_lane + index)] = bool(checked)

        for name, field, codes in (("fault_code", elsfp_consts.FAULT_CODE_FIELD, fault_code),
                                   ("warning_code", elsfp_consts.WARNING_CODE_FIELD, warning_code)):
            for index in range(len(codes)):
                status["%s_lane%d" % (name, first_lane + index)] = \
                    codes["%s%d" % (field, index + 1)]
        return status

    def get_elsfp_status(self) -> dict:
        non_banked_status = self.get_non_banked_elsfp_status()
        banked_status = self.get_banked_elsfp_status()
        if non_banked_status is None or banked_status is None:
            return None
        return {**non_banked_status, **banked_status}

    def get_non_banked_elsfp_status_flags(self) -> dict:
        status_flags = {
            "lane_summary_fault": self.get_lane_summary_fault(),
            "lane_summary_warning": self.get_lane_summary_warning()
        }
        firmware_fault_info = self.get_module_firmware_fault_info()
        if None in status_flags.values() or firmware_fault_info is None:
            return None

        status_flags.update(firmware_fault_info)
        return status_flags

    def get_banked_elsfp_status_flags(self) -> dict:
        # The per-lane fault and warning flags (page 1Ah bytes 166-169 and
        # 174-177) are laid out linearly in the memory map and not banked in
        # the traditional sense (requiring a write to the BankSelect register).
        # Instead, the API only reads the byte associated with our bank, so
        # we still consider this data bank dependent.
        fault_flags = self.get_per_lane_fault_flags()
        warn_flags = self.get_per_lane_warn_flags()
        if fault_flags is None or warn_flags is None:
            return None

        # Flatten and convert the mem-map names ("FaultFlagLane9") in these dictionaries
        # to the snake case "<name>_lane<N>".
        status_flags = {}
        first_lane = self.xcvr_eeprom.mem_map.bank * CMIS_LANES_PER_BANK + 1
        for name, prefix, flags in (("fault_flag", elsfp_consts.FAULT_FLAG_LANE_PREFIX, fault_flags),
                                    ("warning_flag", elsfp_consts.WARN_FLAG_LANE_PREFIX, warn_flags)):
            for index in range(len(flags)):
                lane = first_lane + index
                status_flags["%s_lane%d" % (name, lane)] = flags["%s%d" % (prefix, lane)]
        return status_flags

    def get_elsfp_status_flags(self) -> dict:
        # A 'None' from either half means an EEPROM read failed, so return 'None'
        # to tell the caller to retry rather than handing back a partial dict.
        non_banked_flags = self.get_non_banked_elsfp_status_flags()
        banked_flags = self.get_banked_elsfp_status_flags()
        if non_banked_flags is None or banked_flags is None:
            return None
        return {**non_banked_flags, **banked_flags}
