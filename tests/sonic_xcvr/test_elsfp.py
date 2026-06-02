import pytest
import struct

from sonic_platform_base.sonic_xcvr.codes.public.elsfp import ElsfpCodes
from sonic_platform_base.sonic_xcvr.fields import consts, elsfp_consts
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.elsfp import ElsfpMemMap


from sonic_platform_base.sonic_xcvr.api.public.elsfp import ElsfpApi
from sonic_platform_base.sonic_xcvr.fields.elsfp_consts import SaveRestoreCommand, SaveRestoreConfirmationCode
from .eeprom_utils import InMemoryEeprom


class TestElsfpMemMap:
    mem_map = ElsfpMemMap(ElsfpCodes)

    def test_inherits_cmis_flat_pages(self):
        # CmisFlatMemMap adds page 00h lower + upper; ElsfpMemMap adds 6 more.
        assert len(self.mem_map.pages) == 8

    @pytest.mark.parametrize("page", [0x01, 0x02, 0x1A, 0x1B, 0x2F, 0x9F])
    def test_expected_pages_present(self, page):
        assert any(p.page == page for p in self.mem_map.pages)

    @pytest.mark.parametrize("page", [0x10, 0x11, 0x12, 0x13])
    def test_lane_datapath_pages_excluded(self, page):
        assert not any(p.page == page for p in self.mem_map.pages)

    @pytest.mark.parametrize("field", [
        consts.MODULE_FUNCTION_TYPE,
        consts.ADVERTISING_FIELD,
        consts.THRESHOLDS_FIELD,
        elsfp_consts.ELSFP_MODULE_ADVERTISEMENTS_FIELD,
        elsfp_consts.ELSFP_LANE_FAULTS_WARNINGS_FIELD,
        elsfp_consts.ELSFP_LASER_SAVE_RESTORE_FIELD,
        elsfp_consts.ELSFP_ALARMS_WARNINGS_MASKS_FIELD,
        elsfp_consts.ELSFP_LANE_CONTROLS_FIELD,
        elsfp_consts.ELSFP_OUTPUT_FIBER_CHECKED_FIELD,
        elsfp_consts.ELSFP_LANE_MAPPING_FREQ_POWER_FIELD,
        elsfp_consts.ELSFP_SETPOINTS_FIELD,
        elsfp_consts.ELSFP_MONITORS_FIELD,
    ])
    def test_field_resolvable(self, field):
        assert self.mem_map.get_field(field) is not None


class TestElsfpCodes:
    def test_inherits_cmis_codes(self):
        # ElsfpCodes extends CmisCodes; the parent VDM_TYPE table is inherited.
        assert 1 in ElsfpCodes.VDM_TYPE  # CMIS Laser Age entry
        assert 84 in ElsfpCodes.VDM_TYPE  # CMIS 5.3 ELS Input Power entry

    def test_elsfp_specific_codes_present(self):
        assert ElsfpCodes.CONTROL_MODE[0] == 'ACC'
        assert ElsfpCodes.CONTROL_MODE[1] == 'APC'
        assert 0 in ElsfpCodes.LANE_FAULT_CODE
        assert 0 in ElsfpCodes.LANE_WARNING_CODE
        assert ElsfpCodes.LANE_STATE[2] == 'Lane Output on'


# Linear base address for page 1Ah fields (bank 0): page * 128 = 0x1A * 128
PAGE_1A_BASE = 0x1A * 128


@pytest.fixture
def mem_eeprom():
    return InMemoryEeprom(ElsfpMemMap(ElsfpCodes))


@pytest.fixture
def api(mem_eeprom):
    return ElsfpApi(mem_eeprom.eeprom)


def _bitmask_from_lane_list(lanes: list[int]) -> int:
    """Reconstruct an 8-bit bitmask from a per-lane list (index 0 → lane 1 → bit 0)."""
    return sum(v << i for i, v in enumerate(lanes))


class TestModuleAdvertisements:
    """Table 4 (bytes 128-164)"""

    @pytest.mark.parametrize("method, byte_offset, raw_value, expected", [
        # Optical power fields use scale=100.0 (10 uW steps → mW): decoded = raw / 100.0
        ("get_max_optical_power",        128, 1000, 10.0),
        ("get_min_optical_power",        130,  500,  5.0),
        # Laser bias fields use scale=10000.0 (100 uA steps → A): decoded = raw / 10000.0
        ("get_max_laser_bias",           132, 1000, 0.1),
        ("get_min_laser_bias",           134,  500, 0.05),
        ("get_laser_bias_high_alarm",    141, 1000, 0.1),
        ("get_laser_bias_low_alarm",     143,  500, 0.05),
        ("get_laser_bias_high_warn",     145, 1000, 0.1),
        ("get_laser_bias_low_warn",      147,  500, 0.05),
        ("get_optical_power_high_alarm", 149, 1000, 10.0),
        ("get_optical_power_low_alarm",  151,  500,  5.0),
        ("get_optical_power_high_warn",  153, 1000, 10.0),
        ("get_optical_power_low_warn",   155,  500,  5.0),
    ])
    def test_read_only_fields(self, mem_eeprom, api, method, byte_offset, raw_value, expected):
        offset = PAGE_1A_BASE + byte_offset
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", raw_value)
        assert getattr(api, method)() == pytest.approx(expected)

    def test_get_control_mode_acc(self, mem_eeprom, api):
        mem_eeprom.memory[PAGE_1A_BASE + 140] = 0x00  # bit 0 = 0 → ACC
        assert api.get_control_mode() == 'ACC'

    def test_get_control_mode_apc(self, mem_eeprom, api):
        mem_eeprom.memory[PAGE_1A_BASE + 140] = 0x01  # bit 0 = 1 → APC
        assert api.get_control_mode() == 'APC'

    def test_get_lane_count(self, mem_eeprom, api):
        #   bit 7   bit 6   bit 5   bit 4   bit 3   bit 2   bit 1   bit 0
        #  [                NUMBER_OF_LANES (7 bits)              ] [APC]
        # NUMBER_OF_LANES occupies bits 7-1. 8 lanes -> raw = 8 << 1 = 0x10.
        mem_eeprom.memory[PAGE_1A_BASE + 140] = 0x10
        assert api.get_lane_count() == 8


class TestLaneFaultsWarnings:
    """Table 5 (bytes 165-181): read-only fault and warning flags."""

    def test_lane_summary_fault_set(self, mem_eeprom, api):
        mem_eeprom.memory[PAGE_1A_BASE + 165] = 0x04  # bit 2
        assert api.get_lane_summary_fault() == True

    def test_lane_summary_fault_clear(self, mem_eeprom, api):
        mem_eeprom.memory[PAGE_1A_BASE + 165] = 0x00
        assert api.get_lane_summary_fault() == False

    def test_lane_summary_warning_set(self, mem_eeprom, api):
        mem_eeprom.memory[PAGE_1A_BASE + 165] = 0x08  # bit 3
        assert api.get_lane_summary_warning() == True

    def test_lane_summary_warning_clear(self, mem_eeprom, api):
        mem_eeprom.memory[PAGE_1A_BASE + 165] = 0x00
        assert api.get_lane_summary_warning() == False

    def test_per_lane_fault_flags(self, mem_eeprom, api):
        # Lanes 1-8 are packed into byte 166, one bit per lane.
        mem_eeprom.memory[PAGE_1A_BASE + 166] = 0b00000101  # lanes 1 and 3
        result = api.get_per_lane_fault_flags()
        assert result["FaultFlagLane1"] == 1
        assert result["FaultFlagLane2"] == 0
        assert result["FaultFlagLane3"] == 1

    def test_per_lane_warn_flags(self, mem_eeprom, api):
        # Lanes 1-8 are packed into byte 174, one bit per lane.
        mem_eeprom.memory[PAGE_1A_BASE + 174] = 0b00000110  # lanes 2 and 3
        result = api.get_per_lane_warn_flags()
        assert result["WarnFlagLane1"] == 0
        assert result["WarnFlagLane2"] == 1
        assert result["WarnFlagLane3"] == 1


class TestLaserSaveRestore:
    """Table 6 (bytes 182-185): save/restore command and confirmation."""

    @pytest.mark.parametrize("command", [
        SaveRestoreCommand.SAVE_SET1_LANE_CONTROLS,
        SaveRestoreCommand.SAVE_SET2_LANE_CONTROLS,
        SaveRestoreCommand.RESTORE_FACTORY_SETTINGS_FOR_LANE_CONTROLS,
        SaveRestoreCommand.RESTORE_SET1_LANE_CONTROLS,
        SaveRestoreCommand.RESTORE_SET2_LANE_CONTROLS,
        SaveRestoreCommand.SAVE_SET1_ALARM_WARNING_MASKS,
        SaveRestoreCommand.SAVE_SET2_ALARM_WARNING_MASKS,
        SaveRestoreCommand.RESTORE_FACTORY_SETTINGS_FOR_FLAGS_AND_WARNINGS,
        SaveRestoreCommand.RESTORE_SET1_ALARM_WARNING_MASKS,
        SaveRestoreCommand.RESTORE_SET2_ALARM_WARNING_MASKS,
    ])
    def test_write_save_restore_command(self, mem_eeprom, api, command):
        api.write_save_restore_command(command)
        assert mem_eeprom.memory[PAGE_1A_BASE + 184] == command.value

    @pytest.mark.parametrize("raw_value, expected_code", [
        (0x01, SaveRestoreConfirmationCode.SUCCESS),
        (0x02, SaveRestoreConfirmationCode.IN_PROGRESS),
        (0x03, SaveRestoreConfirmationCode.INVALID_COMMAND),
        (0x04, SaveRestoreConfirmationCode.NO_RELEVANT_SAVED_CONTENT),
        (0x08, SaveRestoreConfirmationCode.FAILED),
    ])
    def test_get_save_restore_confirmation(self, mem_eeprom, api, raw_value, expected_code):
        mem_eeprom.memory[PAGE_1A_BASE + 185] = raw_value
        assert api.get_save_restore_confirmation() == expected_code


class TestBankedAlarmsWarningsMasks:
    """Table 7 (bytes 186-219): alarm/warning indexed flags, masks, and codes."""

    # Alarm/warning indexed fields return a list[int] (one entry per lane, index 0 = lane 1).
    # Reconstruct the bitmask to compare against the raw byte written into memory.
    @pytest.mark.parametrize("method, byte_offset, raw_byte", [
        ("get_per_lane_high_bias_alarms",    186, 0b00000101),
        ("get_per_lane_low_bias_alarms",     187, 0b00001010),
        ("get_per_lane_high_bias_warnings",  188, 0b00000011),
        ("get_per_lane_low_bias_warnings",   189, 0b11111111),
        ("get_per_lane_high_power_alarms",   190, 0b00000101),
        ("get_per_lane_low_power_alarms",    191, 0b00001010),
        ("get_per_lane_high_power_warnings", 192, 0b00000011),
        ("get_per_lane_low_power_warnings",  193, 0b11111111),
    ])
    def test_alarm_indexed_field(self, mem_eeprom, api, method, byte_offset, raw_byte):
        mem_eeprom.memory[PAGE_1A_BASE + byte_offset] = raw_byte
        result = getattr(api, method)()
        assert _bitmask_from_lane_list(result) == raw_byte

    # Mask fields are read/write. Each is a single byte with one bit per lane.
    @pytest.mark.parametrize("set_method, get_method", [
        ("set_per_lane_high_bias_alarm_mask",    "get_per_lane_high_bias_alarm_mask"),
        ("set_per_lane_low_bias_alarm_mask",     "get_per_lane_low_bias_alarm_mask"),
        ("set_per_lane_high_bias_warning_mask",  "get_per_lane_high_bias_warning_mask"),
        ("set_per_lane_low_bias_warning_mask",   "get_per_lane_low_bias_warning_mask"),
        ("set_per_lane_high_power_alarm_mask",   "get_per_lane_high_power_alarm_mask"),
        ("set_per_lane_low_power_alarm_mask",    "get_per_lane_low_power_alarm_mask"),
        ("set_per_lane_high_power_warning_mask", "get_per_lane_high_power_warning_mask"),
        ("set_per_lane_low_power_warning_mask",  "get_per_lane_low_power_warning_mask"),
        ("set_per_lane_global_alarm_mask",       "get_per_lane_global_alarm_mask"),
        ("set_per_lane_global_warn_mask",        "get_per_lane_global_warn_mask"),
    ])
    def test_mask_set(self, api, set_method, get_method):
        getattr(api, set_method)(0b00000101, True)  # lanes 1 and 3
        result = getattr(api, get_method)()
        assert _bitmask_from_lane_list(result) == 0b00000101

    @pytest.mark.parametrize("set_method, get_method", [
        ("set_per_lane_high_bias_alarm_mask",    "get_per_lane_high_bias_alarm_mask"),
        ("set_per_lane_low_bias_alarm_mask",     "get_per_lane_low_bias_alarm_mask"),
        ("set_per_lane_high_bias_warning_mask",  "get_per_lane_high_bias_warning_mask"),
        ("set_per_lane_low_bias_warning_mask",   "get_per_lane_low_bias_warning_mask"),
        ("set_per_lane_high_power_alarm_mask",   "get_per_lane_high_power_alarm_mask"),
        ("set_per_lane_low_power_alarm_mask",    "get_per_lane_low_power_alarm_mask"),
        ("set_per_lane_high_power_warning_mask", "get_per_lane_high_power_warning_mask"),
        ("set_per_lane_low_power_warning_mask",  "get_per_lane_low_power_warning_mask"),
        ("set_per_lane_global_alarm_mask",       "get_per_lane_global_alarm_mask"),
        ("set_per_lane_global_warn_mask",        "get_per_lane_global_warn_mask"),
    ])
    def test_mask_clear(self, api, set_method, get_method):
        # Set lanes 1 and 3, then clear lane 1 — only lane 3 should remain.
        getattr(api, set_method)(0b00000101, True)   # lanes 1 and 3
        getattr(api, set_method)(0b00000001, False)  # lane 1 only
        result = getattr(api, get_method)()
        assert _bitmask_from_lane_list(result) == 0b00000100

    def test_per_lane_fault_code(self, mem_eeprom, api):
        # Fault code occupies bits 3-0 of each byte in 212-219.
        # Write 0x05 to byte 212 -> FaultCode1 raw = 5 -> decoded = LANE_FAULT_CODE[5] = 'Reserved'.
        mem_eeprom.memory[PAGE_1A_BASE + 212] = 0x05
        result = api.get_per_lane_fault_code()
        assert result["FaultCode1"] == 'Reserved'

    def test_per_lane_warning_code(self, mem_eeprom, api):
        # Warning code occupies bits 7-4 of each byte in 212-219.
        # Write 0x50 to byte 212 -> WarningCode1 raw = 5 -> decoded = LANE_WARNING_CODE[5] = 'Reserved'.
        mem_eeprom.memory[PAGE_1A_BASE + 212] = 0x50
        result = api.get_per_lane_warning_code()
        assert result["WarningCode1"] == 'Reserved'


class TestBankedLaneControls:
    """Table 8 (bytes 220-222): per-lane enable and state."""

    def test_lane_enable_set(self, api):
        api.set_per_lane_enable(0b00000101, True)  # lanes 1 and 3
        result = api.get_per_lane_enable()
        assert _bitmask_from_lane_list(result) == 0b00000101

    def test_lane_enable_clear(self, api):
        api.set_per_lane_enable(0b00000101, True)   # lanes 1 and 3
        api.set_per_lane_enable(0b00000100, False)  # lane 3 only
        result = api.get_per_lane_enable()
        assert _bitmask_from_lane_list(result) == 0b00000001

    def test_lane_mask_out_of_range_raises(self, api):
        # Per-lane fields are single-byte (8 lanes), so a bit above bit 7
        # would overflow the 'B' pack format; the API must reject it up front.
        with pytest.raises(ValueError):
            api.set_per_lane_enable(0x100, True)

    def test_per_lane_state(self, mem_eeprom, api):
        # Byte 221 holds lanes 1-4, 2 bits per lane.
        # 0b00000110: lane 1 = bits 1-0 = 0b10 = 2 → 'Lane Output on'
        #             lane 2 = bits 3-2 = 0b01 = 1 → 'Lane Output ramping'
        mem_eeprom.memory[PAGE_1A_BASE + 221] = 0b00000110
        # Byte 222 holds lanes 5-8, 2 bits per lane.
        # 0b00001100: lane 5 = bits 1-0 = 0b00 = 0 → 'Lane Output off'
        #             lane 6 = bits 3-2 = 0b11 = 3 → 'Reserved'
        mem_eeprom.memory[PAGE_1A_BASE + 222] = 0b00001100
        result = api.get_per_lane_state()
        assert result["LaneState1"] == 'Lane Output on'
        assert result["LaneState2"] == 'Lane Output ramping'
        assert result["LaneState5"] == 'Lane Output off'
        assert result["LaneState6"] == 'Reserved'


class TestOutputFiberChecked:
    """Table 9 (byte 223): output fiber link checked flag."""

    def test_get_per_lane_output_fiber_checked(self, mem_eeprom, api):
        # Field returns list[int], one entry per lane (index 0 = lane 1).
        mem_eeprom.memory[PAGE_1A_BASE + 223] = 0b00000101  # lanes 1 and 3
        result = api.get_per_lane_output_fiber_checked()
        assert result[0] == 1  # lane 1
        assert result[1] == 0  # lane 2
        assert result[2] == 1  # lane 3

    def test_set_per_lane_output_fiber_checked(self, api):
        api.set_lane_output_fiber_checked(0b00000101, True)   # lanes 1 and 3
        result = api.get_per_lane_output_fiber_checked()
        assert _bitmask_from_lane_list(result) == 0b00000101
        api.set_lane_output_fiber_checked(0b00000001, False)  # lane 1 only
        result = api.get_per_lane_output_fiber_checked()
        assert _bitmask_from_lane_list(result) == 0b00000100


class TestLaneMappingFreqPower:
    """Table 10 (bytes 224-255): lane-to-fiber mapping, frequency, and power setpoint."""

    def test_lane_to_fiber_mapping(self, mem_eeprom, api):
        # NumberRegField with scale=1, format="B": decoded = raw byte as int.
        mem_eeprom.memory[PAGE_1A_BASE + 224] = 0x0F
        result = api.get_lane_to_fiber_mapping()
        assert result["LaneToFiberMapping1"] == 15

    def test_per_lane_freq(self, mem_eeprom, api):
        # LaneFreq1 is a 2-byte big-endian U16 at byte 232, scale=0.2.
        # raw=100 -> decoded = 100 / 0.2 = 500.0 GHz.
        offset = PAGE_1A_BASE + 232
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", 100)
        result = api.get_per_lane_freq()
        assert result["LaneFreq1"] == 500.0

    def test_opt_check_power_setpoint(self, mem_eeprom, api):
        # Single byte, scale=1.0. raw=5 -> decoded = 5 / 1.0 = 5.0 mW.
        mem_eeprom.memory[PAGE_1A_BASE + 248] = 5
        assert api.get_opt_check_power_setpoint() == 5.0


# Page 1Bh base address (bank 0): page * 128 = 0x1B * 128
PAGE_1B_BASE = 0x1B * 128


class TestBankedSetpoints:
    """Table 11 (bytes 128-159): per-lane bias current and optical power setpoints."""

    def test_bias_current_setpoint_roundtrip(self, api):
        # set_lane_bias_current_setpoint encodes in Amps (scale=10000.0).
        # 0.5 A -> raw = int(0.5 * 10000) = 5000 -> decoded = 5000 / 10000 = 0.5 A.
        api.set_lane_bias_current_setpoint(1, 0.5)
        result = api.get_per_lane_bias_current_setpoint()
        assert result["BiasCurrentSetpoint1"] == 0.5

    def test_bias_current_setpoint_two_lanes_independent(self, api):
        # Verify that setting lane 2 is stored independently from lane 1.
        api.set_lane_bias_current_setpoint(1, 0.1)
        api.set_lane_bias_current_setpoint(2, 0.2)
        result = api.get_per_lane_bias_current_setpoint()
        assert result["BiasCurrentSetpoint1"] == 0.1
        assert result["BiasCurrentSetpoint2"] == 0.2

    def test_opt_power_setpoint_roundtrip(self, api):
        # set_lane_opt_power_setpoint encodes in mW (scale=100.0).
        # 100.0 mW -> raw = int(100.0 * 100) = 10000 -> decoded = 10000 / 100 = 100.0 mW.
        api.set_lane_opt_power_setpoint(1, 100.0)
        result = api.get_per_lane_opt_power_setpoint()
        assert result["OptPowerSetpoint1"] == 100.0

    def test_opt_power_setpoint_two_lanes_independent(self, api):
        # Verify that setting lane 2 is stored independently from lane 1.
        api.set_lane_opt_power_setpoint(1, 100.0)
        api.set_lane_opt_power_setpoint(2, 200.0)
        result = api.get_per_lane_opt_power_setpoint()
        assert result["OptPowerSetpoint1"] == 100.0
        assert result["OptPowerSetpoint2"] == 200.0


class TestBankedMonitors:
    """Table 12 (bytes 184-241): per-lane bias, optical power, voltage monitors and ICC."""

    def test_bias_current_monitor(self, mem_eeprom, api):
        # Verify lane 2 is read from the correct address (bytes 186-187).
        offset = PAGE_1B_BASE + 186
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", 2000)
        result = api.get_per_lane_bias_current_monitor()
        assert result["BiasCurrentMonitor2"] == 0.2

    def test_opt_power_monitor(self, mem_eeprom, api):
        # Verify lane 2 is read from the correct address (bytes 202-203).
        # raw=2000 -> decoded = 2000 / 100 = 20.0 mW.
        offset = PAGE_1B_BASE + 202
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", 2000)
        result = api.get_per_lane_opt_power_monitor()
        assert result["OptPowerMonitor2"] == 20.0

    def test_voltage_monitor(self, mem_eeprom, api):
        # raw=255 -> decoded = 255 / (1000/15) = 255 * 0.015 = 3.825 V.
        mem_eeprom.memory[PAGE_1B_BASE + 233] = 255
        result = api.get_per_lane_voltage_monitor()
        assert result["VoltageMonitor2"] == pytest.approx(3.825)

    def test_icc_monitor(self, mem_eeprom, api):
        # raw=1000 -> decoded = 1000 / 5000 = 0.2 A.
        offset = PAGE_1B_BASE + 240
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", 1000)
        assert api.get_icc_monitor() == 0.2


class TestModuleFunctionType:
    """Lower memory byte 57: ModuleFunctionType."""

    def test_transmission_module(self, mem_eeprom, api):
        mem_eeprom.memory[57] = 0
        assert api.get_module_function_type() == "Transmission Module"

    def test_resource_module(self, mem_eeprom, api):
        mem_eeprom.memory[57] = 1
        assert api.get_module_function_type() == "Resource Module"

    def test_reserved_value(self, mem_eeprom, api):
        mem_eeprom.memory[57] = 5
        assert api.get_module_function_type() == "Unknown"

    def test_resource_module_skips_apsel_read(self, mem_eeprom, api):
        # Byte 2 bit 7 = 0 → paged memory (not flat), so the flat-memory guard
        # won't fire. Byte 57 = 1 → Resource Module, so the resource module
        # guard should return N/A without touching page 11h (ACTIVE_APSEL_CODE).
        mem_eeprom.memory[2] = 0x00   # paged memory
        mem_eeprom.memory[57] = 1     # Resource Module
        result = api.get_active_apsel_hostlane()
        for lane in range(1, 9):
            assert result["active_apsel_hostlane%d" % lane] == "N/A"
