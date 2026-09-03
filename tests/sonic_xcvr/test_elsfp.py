import pytest
from mock import MagicMock, patch
import struct

from sonic_platform_base.sonic_xcvr.api.broadcom.davisson_elsfp import DavissonTh6ElsfpApi
from sonic_platform_base.sonic_xcvr.codes.public.elsfp import ElsfpCodes
from sonic_platform_base.sonic_xcvr.fields import consts, elsfp_consts
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.davisson_elsfp import DavissonTh6ElsfpMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.elsfp import ElsfpMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.elsfp.pages.consts import (
    ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE,
    ELSFP_SETPOINTS_MON_PAGE,
)
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.page import CmisPage
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoHardwareInfo, OeId
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpApiFactory
from sonic_platform_base.sonic_xcvr.eeprom_rw import ModuleEepromLowerMemoryInfo
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.consts import (
    ADVERTISING_PAGE,
    CMIS_LANES_PER_BANK,
    THRESHOLDS_PAGE,
)


class TestElsfpApiFactory(object):
    def test_create_api_davisson(self):
        elsfp = MagicMock()
        elsfp.bank = 1
        elsfp.hardware_id = CpoHardwareInfo(
            oe_id=OeId.BROADCOM_DAVISSON,
            elsfp_id=None,
            elsfp_low_mem_offset=CmisPage.linear_offset(0xB0, 0, 0),
        )
        factory = ElsfpApiFactory(elsfp)

        # The factory probes vendor name/part number from the EEPROM before
        # dispatching; stub out the lower-memory reads.
        with patch.object(ModuleEepromLowerMemoryInfo, 'get_vendor_name', return_value='BROADCOM'), \
             patch.object(ModuleEepromLowerMemoryInfo, 'get_vendor_part_num', return_value='DAVISSON-TH6'):
            api = factory.create_api()

        assert isinstance(api, DavissonTh6ElsfpApi)
        assert isinstance(api.xcvr_eeprom.mem_map, DavissonTh6ElsfpMemMap)
        # The device's bank and EEPROM accessors must be threaded through.
        assert api.xcvr_eeprom.mem_map.bank == 1
        assert api.xcvr_eeprom.reader is elsfp.read_eeprom
        assert api.xcvr_eeprom.writer is elsfp.write_eeprom


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
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        offset = base + byte_offset
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", raw_value)
        assert getattr(api, method)() == pytest.approx(expected)

    def test_get_control_mode_acc(self, mem_eeprom, api):
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 140] = 0x00  # bit 0 = 0 → ACC
        assert api.get_control_mode() == 'ACC'

    def test_get_control_mode_apc(self, mem_eeprom, api):
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 140] = 0x01  # bit 0 = 1 → APC
        assert api.get_control_mode() == 'APC'

    def test_get_lane_count(self, mem_eeprom, api):
        #   bit 7   bit 6   bit 5   bit 4   bit 3   bit 2   bit 1   bit 0
        #  [                NUMBER_OF_LANES (7 bits)              ] [APC]
        # NUMBER_OF_LANES occupies bits 7-1. 8 lanes -> raw = 8 << 1 = 0x10.
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 140] = 0x10
        assert api.get_lane_count() == 8


class TestLaneFaultsWarnings:
    """Table 5 (bytes 165-181): read-only fault and warning flags."""

    def test_lane_summary_fault_set(self, mem_eeprom, api):
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 165] = 0x04  # bit 2
        assert api.get_lane_summary_fault() == True

    def test_lane_summary_fault_clear(self, mem_eeprom, api):
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 165] = 0x00
        assert api.get_lane_summary_fault() == False

    def test_lane_summary_warning_set(self, mem_eeprom, api):
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 165] = 0x08  # bit 3
        assert api.get_lane_summary_warning() == True

    def test_lane_summary_warning_clear(self, mem_eeprom, api):
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 165] = 0x00
        assert api.get_lane_summary_warning() == False

    def test_per_lane_fault_flags(self, mem_eeprom, api):
        # Bank 0's 8 lanes are packed into byte 166, one bit per lane.
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 166] = 0b10000101  # lanes 1, 3 and 8
        result = api.get_per_lane_fault_flags()
        assert result == {
            "FaultFlagLane1": True,
            "FaultFlagLane2": False,
            "FaultFlagLane3": True,
            "FaultFlagLane4": False,
            "FaultFlagLane5": False,
            "FaultFlagLane6": False,
            "FaultFlagLane7": False,
            "FaultFlagLane8": True,
        }

    def test_per_lane_fault_flags_ignores_other_banks(self, mem_eeprom, api):
        # 167-169 hold lanes 9-32 (banks 1-3) and must not leak into bank 0.
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 166] = 0x00
        for offset in range(167, 170):
            mem_eeprom.memory[base + offset] = 0xFF
        result = api.get_per_lane_fault_flags()
        assert set(result.values()) == {False}

    def test_per_lane_warn_flags(self, mem_eeprom, api):
        # Bank 0's 8 lanes are packed into byte 174, one bit per lane.
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 174] = 0b10000110  # lanes 2, 3 and 8
        result = api.get_per_lane_warn_flags()
        assert result == {
            "WarnFlagLane1": False,
            "WarnFlagLane2": True,
            "WarnFlagLane3": True,
            "WarnFlagLane4": False,
            "WarnFlagLane5": False,
            "WarnFlagLane6": False,
            "WarnFlagLane7": False,
            "WarnFlagLane8": True,
        }

    def test_per_lane_warn_flags_ignores_other_banks(self, mem_eeprom, api):
        # 175-177 hold lanes 9-32 (banks 1-3) and must not leak into bank 0.
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 174] = 0x00
        for offset in range(175, 178):
            mem_eeprom.memory[base + offset] = 0xFF
        result = api.get_per_lane_warn_flags()
        assert set(result.values()) == {False}

    @pytest.mark.parametrize("bank", [0, 1, 2, 3])
    @pytest.mark.parametrize("method, base_offset, key_prefix", [
        ("get_per_lane_fault_flags", 166, "FaultFlagLane"),
        ("get_per_lane_warn_flags",  174, "WarnFlagLane"),
    ])
    def test_flags_report_only_selected_bank(self, bank, method, base_offset, key_prefix):
        """Bank N reports the byte holding lanes 8N+1..8N+8, keyed by absolute lane."""
        eeprom = InMemoryEeprom(ElsfpMemMap(ElsfpCodes, bank=bank), num_banks=4)
        api = ElsfpApi(eeprom.eeprom)

        # The 4-byte block lives in this bank's page image. Give each byte a
        # distinct single-bit pattern so reading the wrong one is detectable.
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, bank, 0)
        patterns = [0b00000001, 0b00000010, 0b00000100, 0b00001000]
        for i, pattern in enumerate(patterns):
            eeprom.memory[base + base_offset + i] = pattern

        result = getattr(api, method)()

        # Keys cover this bank's absolute lane range, e.g. bank 1 -> lanes 9-16.
        first_lane = CMIS_LANES_PER_BANK * bank
        assert set(result) == {
            "%s%d" % (key_prefix, first_lane + lane)
            for lane in range(1, CMIS_LANES_PER_BANK + 1)
        }

        # The byte for bank N sets bit N, i.e. lane N+1 of that bank.
        expected_lane = first_lane + bank + 1
        assert result["%s%d" % (key_prefix, expected_lane)] is True
        assert sum(result.values()) == 1


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
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        api.write_save_restore_command(command)
        assert mem_eeprom.memory[base + 184] == command.value

    @pytest.mark.parametrize("raw_value, expected_code", [
        (0x01, SaveRestoreConfirmationCode.SUCCESS),
        (0x02, SaveRestoreConfirmationCode.IN_PROGRESS),
        (0x03, SaveRestoreConfirmationCode.INVALID_COMMAND),
        (0x04, SaveRestoreConfirmationCode.NO_RELEVANT_SAVED_CONTENT),
        (0x08, SaveRestoreConfirmationCode.FAILED),
    ])
    def test_get_save_restore_confirmation(self, mem_eeprom, api, raw_value, expected_code):
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 185] = raw_value
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
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + byte_offset] = raw_byte
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
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 212] = 0x05
        result = api.get_per_lane_fault_code()
        assert result["FaultCode1"] == 'Reserved'

    def test_per_lane_warning_code(self, mem_eeprom, api):
        # Warning code occupies bits 7-4 of each byte in 212-219.
        # Write 0x50 to byte 212 -> WarningCode1 raw = 5 -> decoded = LANE_WARNING_CODE[5] = 'Reserved'.
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 212] = 0x50
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
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 221] = 0b00000110
        # Byte 222 holds lanes 5-8, 2 bits per lane.
        # 0b00001100: lane 5 = bits 1-0 = 0b00 = 0 → 'Lane Output off'
        #             lane 6 = bits 3-2 = 0b11 = 3 → 'Reserved'
        mem_eeprom.memory[base + 222] = 0b00001100
        result = api.get_per_lane_state()
        assert result["LaneState1"] == 'Lane Output on'
        assert result["LaneState2"] == 'Lane Output ramping'
        assert result["LaneState5"] == 'Lane Output off'
        assert result["LaneState6"] == 'Reserved'


class TestOutputFiberChecked:
    """Table 9 (byte 223): output fiber link checked flag."""

    def test_get_per_lane_output_fiber_checked(self, mem_eeprom, api):
        # Field returns list[int], one entry per lane (index 0 = lane 1).
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 223] = 0b00000101  # lanes 1 and 3
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
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 224] = 0x0F
        result = api.get_lane_to_fiber_mapping()
        assert result["LaneToFiberMapping1"] == 15

    def test_per_lane_freq(self, mem_eeprom, api):
        # LaneFreq1 is a 2-byte big-endian U16 at byte 232, scale=0.2.
        # raw=100 -> decoded = 100 / 0.2 = 500.0 GHz.
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        offset = base + 232
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", 100)
        result = api.get_per_lane_freq()
        assert result["LaneFreq1"] == 500.0

    def test_opt_check_power_setpoint(self, mem_eeprom, api):
        # Single byte, scale=1.0. raw=5 -> decoded = 5 / 1.0 = 5.0 mW.
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        mem_eeprom.memory[base + 248] = 5
        assert api.get_opt_check_power_setpoint() == 5.0


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
        base = CmisPage.linear_offset(ELSFP_SETPOINTS_MON_PAGE, 0, 0)
        offset = base + 186
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", 2000)
        result = api.get_per_lane_bias_current_monitor()
        assert result["BiasCurrentMonitor2"] == 0.2

    def test_opt_power_monitor(self, mem_eeprom, api):
        # Verify lane 2 is read from the correct address (bytes 202-203).
        # raw=2000 -> decoded = 2000 / 100 = 20.0 mW.
        base = CmisPage.linear_offset(ELSFP_SETPOINTS_MON_PAGE, 0, 0)
        offset = base + 202
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", 2000)
        result = api.get_per_lane_opt_power_monitor()
        assert result["OptPowerMonitor2"] == 20.0

    def test_voltage_monitor(self, mem_eeprom, api):
        # raw=255 -> decoded = 255 / (1000/15) = 255 * 0.015 = 3.825 V.
        base = CmisPage.linear_offset(ELSFP_SETPOINTS_MON_PAGE, 0, 0)
        mem_eeprom.memory[base + 233] = 255
        result = api.get_per_lane_voltage_monitor()
        assert result["VoltageMonitor2"] == pytest.approx(3.825)

    def test_icc_monitor(self, mem_eeprom, api):
        # raw=1000 -> decoded = 1000 / 5000 = 0.2 A.
        base = CmisPage.linear_offset(ELSFP_SETPOINTS_MON_PAGE, 0, 0)
        offset = base + 240
        mem_eeprom.memory[offset:offset + 2] = struct.pack(">H", 1000)
        assert api.get_icc_monitor() == 0.2


class TestElsfpDomRealValue:
    """get_elsfp_dom_real_value() and the banked / non-banked halves it is composed of."""

    EXPECTED_NON_BANKED_DOM = {
        "temperature": 40.0,
        "voltage": 3.3,
    }

    EXPECTED_BANKED_DOM = {
        "per_lane_laser_bias_current": {
            "BiasCurrentMonitor%d" % lane: 0.01 * lane
            for lane in range(1, CMIS_LANES_PER_BANK + 1)
        },
        "per_lane_optical_power": {
            "OptPowerMonitor%d" % lane: 2.0 * lane
            for lane in range(1, CMIS_LANES_PER_BANK + 1)
        },
        "per_lane_voltage": {
            "VoltageMonitor%d" % lane: pytest.approx(0.15 * lane)
            for lane in range(1, CMIS_LANES_PER_BANK + 1)
        },
        "icc": 0.2,
    }

    def _populate_non_banked_dom(self, mem_eeprom):
        """Fill page 00h lower memory with the module level monitors."""
        mem = mem_eeprom.memory
        # Temperature: bytes 14-15, scale=256.0 -> deg C.
        mem[14:16] = struct.pack(">h", 40 * 256)
        # Voltage: bytes 16-17, scale=10000.0 -> V.
        mem[16:18] = struct.pack(">H", 33000)

    def _populate_banked_dom(self, mem_eeprom):
        """Fill page 1Bh (bank 0) with the per-lane monitors."""
        base = CmisPage.linear_offset(ELSFP_SETPOINTS_MON_PAGE, 0, 0)
        mem = mem_eeprom.memory
        for lane in range(1, CMIS_LANES_PER_BANK + 1):
            # Bias current monitor: 2 bytes per lane from 184, scale=10000.0 -> A.
            bias_offset = base + 184 + 2 * (lane - 1)
            mem[bias_offset:bias_offset + 2] = struct.pack(">H", 100 * lane)
            # Optical power monitor: 2 bytes per lane from 200, scale=100.0 -> mW.
            power_offset = base + 200 + 2 * (lane - 1)
            mem[power_offset:power_offset + 2] = struct.pack(">H", 200 * lane)
            # Voltage monitor: 1 byte per lane from 232, 15 mV steps -> V.
            mem[base + 232 + (lane - 1)] = 10 * lane
        # ICC monitor: bytes 240-241, scale=5000.0 -> A.
        mem[base + 240:base + 242] = struct.pack(">H", 1000)

    def test_get_non_banked_elsfp_dom_real_value(self, mem_eeprom, api):
        self._populate_non_banked_dom(mem_eeprom)
        assert api.get_non_banked_elsfp_dom_real_value() == self.EXPECTED_NON_BANKED_DOM

    def test_get_banked_elsfp_dom_real_value(self, mem_eeprom, api):
        self._populate_banked_dom(mem_eeprom)
        assert api.get_banked_elsfp_dom_real_value() == self.EXPECTED_BANKED_DOM

    def test_get_elsfp_dom_real_value_is_union_of_halves(self, mem_eeprom, api):
        self._populate_non_banked_dom(mem_eeprom)
        self._populate_banked_dom(mem_eeprom)
        non_banked_dom = api.get_non_banked_elsfp_dom_real_value()
        banked_dom = api.get_banked_elsfp_dom_real_value()
        # The halves must not overlap, otherwise "union" would be ambiguous.
        assert not set(non_banked_dom) & set(banked_dom)
        assert api.get_elsfp_dom_real_value() == {**non_banked_dom, **banked_dom}


class TestElsfpDomFlags:
    """get_elsfp_dom_flags() and the banked / non-banked halves it is composed of."""

    PER_LANE_FLAG_NAMES = (
        "laser_bias_alarm_high",
        "laser_bias_alarm_low",
        "laser_bias_warn_high",
        "laser_bias_warn_low",
        "optical_power_alarm_high",
        "optical_power_alarm_low",
        "optical_power_warn_high",
        "optical_power_warn_low",
    )

    def _populate_flags(self, mem_eeprom, bank=0):
        """Raise one flag of every kind the aggregate reports.

        Page 1Ah gets a high laser bias alarm on the bank's first lane and a
        low optical power warning on its second lane. Page 00h lower memory gets
        a case temperature high alarm and a supply voltage high warning.
        """
        # Page 1Ah bytes 186-193 hold one bitmask byte per per-lane flag, bit 0
        # being the first lane of the bank.
        high_bias_alarm_byte = 186
        low_optical_power_warn_byte = 193
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, bank, 0)
        mem_eeprom.memory[base + high_bias_alarm_byte] = 0b0000_0001
        mem_eeprom.memory[base + low_optical_power_warn_byte] = 0b0000_0010
        # Byte 9: case temperature flags in the low nibble, supply voltage flags
        # in the high nibble, each ordered high alarm, low alarm, high warn, low warn.
        mem_eeprom.memory[9] = 0b0100_0001

    def test_per_lane_flags(self, mem_eeprom, api):
        self._populate_flags(mem_eeprom)
        flags = api.get_banked_elsfp_dom_flags()

        assert flags["laser_bias_alarm_high_lane1"] is True
        assert flags["optical_power_warn_low_lane2"] is True
        # Every other per-lane flag is clear.
        assert flags["laser_bias_alarm_high_lane2"] is False
        assert flags["optical_power_warn_low_lane1"] is False

        # Lanes with nothing set report no flag at all.
        assert not any(flags["%s_lane3" % name] for name in self.PER_LANE_FLAG_NAMES)

    def test_banked_flags_cover_every_lane_of_the_bank(self, mem_eeprom, api):
        self._populate_flags(mem_eeprom)
        flags = api.get_banked_elsfp_dom_flags()
        expected_keys = {
            "%s_lane%d" % (name, lane)
            for name in self.PER_LANE_FLAG_NAMES
            for lane in range(1, CMIS_LANES_PER_BANK + 1)
        }
        assert set(flags) == expected_keys

    @pytest.mark.parametrize("bank", [0, 1, 2, 3])
    def test_banked_flags_use_absolute_lane_numbers(self, bank):
        """Bank N keys its flags by absolute lane, e.g. bank 1 -> lanes 9-16."""
        mem_eeprom = InMemoryEeprom(ElsfpMemMap(ElsfpCodes, bank=bank), num_banks=4)
        api = ElsfpApi(mem_eeprom.eeprom)
        self._populate_flags(mem_eeprom, bank)

        flags = api.get_banked_elsfp_dom_flags()

        first_lane = CMIS_LANES_PER_BANK * bank + 1
        assert flags["laser_bias_alarm_high_lane%d" % first_lane] is True
        assert flags["optical_power_warn_low_lane%d" % (first_lane + 1)] is True

    def test_module_level_flags(self, mem_eeprom, api):
        self._populate_flags(mem_eeprom)
        assert api.get_non_banked_elsfp_dom_flags() == {
            "temperature_alarm_high": True,
            "temperature_alarm_low": False,
            "temperature_warn_high": False,
            "temperature_warn_low": False,
            "voltage_alarm_high": False,
            "voltage_alarm_low": False,
            "voltage_warn_high": True,
            "voltage_warn_low": False,
        }

    def test_get_elsfp_dom_flags_is_union_of_halves(self, mem_eeprom, api):
        self._populate_flags(mem_eeprom)
        non_banked_flags = api.get_non_banked_elsfp_dom_flags()
        banked_flags = api.get_banked_elsfp_dom_flags()
        # The halves must not overlap, otherwise "union" would be ambiguous.
        assert not set(non_banked_flags) & set(banked_flags)
        assert api.get_elsfp_dom_flags() == {**non_banked_flags, **banked_flags}


class TestElsfpFirmwareVersions:
    """get_elsfp_info_firmware_versions()"""

    def test_get_elsfp_info_firmware_versions(self, mem_eeprom, api):
        mem = mem_eeprom.memory
        # Page 00h lower memory: active firmware major/minor.
        mem[39] = 1
        mem[40] = 2
        # Page 01h: inactive firmware major/minor.
        page_01_base = CmisPage.linear_offset(ADVERTISING_PAGE, 0, 0)
        mem[page_01_base + 128] = 3
        mem[page_01_base + 129] = 4
        assert api.get_elsfp_info_firmware_versions() == {
            "active_firmware": "1.2",
            "inactive_firmware": "3.4",
        }

    def test_get_elsfp_info_firmware_versions_read_failure(self, api):
        # A failed EEPROM read must surface as None so the caller retries
        # instead of caching a partial result.
        with patch.object(api.xcvr_eeprom, "read", return_value=None):
            assert api.get_elsfp_info_firmware_versions() is None


class TestElsfpInfo:
    """get_elsfp_info()"""

    EXPECTED_INFO = {
        "type": "OIF-ELSP",
        "type_abbrv_name": "OIF-ELSP",
        "hardware_rev": "1.2",
        "serial": "SN0123456789",
        "manufacturer": "BROADCOM",
        "model": "DAVISSON-TH6",
        "connector": "LC",
        "encoding": "N/A",
        "ext_identifier": "Power Class 8 (20.0W Max)",
        "ext_rateselect_compliance": "N/A",
        "cable_length": 3.0,
        "nominal_bit_rate": "N/A",
        "vendor_date": "2026-08-21",
        "vendor_oui": "00-17-6a",
        "cable_type": "Length Cable Assembly(m)",
        "media_interface_technology": "1310 nm DFB",
        "vendor_rev": "A1",
        "cmis_rev": "1.0",
        "specification_compliance": "sm_media_interface",
        "vdm_supported": True,
        "cdb_supported": True,
        "lane_count": CMIS_LANES_PER_BANK,
        "control_mode": "APC",
        "max_optical_power": 10.0,
        "min_optical_power": 5.0,
        "max_laser_bias": 0.1,
        "min_laser_bias": 0.05,
        "lane_to_fiber_mapping": {
            "LaneToFiberMapping%d" % lane: lane
            for lane in range(1, CMIS_LANES_PER_BANK + 1)
        },
        "lane_frequency": {
            "LaneFreq%d" % lane: 500.0 * lane
            for lane in range(1, CMIS_LANES_PER_BANK + 1)
        },
    }

    def _populate_info(self, mem_eeprom):
        """Fill pages 00h, 01h and 1Ah with the fields get_elsfp_info() reads."""
        mem = mem_eeprom.memory
        # Page 00h lower memory (linear address == byte offset).
        mem[0] = 0x22                               # identifier
        mem[1] = 0x10                               # CMIS rev: major bits 7-4, minor bits 3-0
        mem[85] = 2                                 # module media type -> sm_media_interface
        # Page 00h upper memory.
        mem[128] = 0x22                             # identifier abbreviation
        mem[129:145] = b"BROADCOM        "          # vendor name (16 bytes, space padded)
        mem[145:148] = bytes((0x00, 0x17, 0x6A))    # vendor OUI
        mem[148:164] = b"DAVISSON-TH6    "          # vendor part number (16 bytes)
        mem[164:166] = b"A1"                        # vendor revision (2 bytes)
        mem[166:182] = b"SN0123456789    "          # vendor serial number (16 bytes)
        mem[182:190] = b"260821  "                  # date code YYMMDD + 2 byte lot code
        mem[200] = 7 << 5                           # power class (bits 7-5) -> Power Class 8
        mem[201] = 80                               # max power, scale=4.0 -> 20.0 W
        mem[202] = (1 << 6) | 3                     # length multiplier 1 (x1), base length 3
        mem[203] = 7                                # connector -> LC
        mem[212] = 4                                # media interface tech -> 1310 nm DFB
        # Page 01h.
        page_01_base = CmisPage.linear_offset(ADVERTISING_PAGE, 0, 0)
        mem[page_01_base + 130] = 1                 # hardware revision major
        mem[page_01_base + 131] = 2                 # hardware revision minor
        mem[page_01_base + 142] = 1 << 6            # PageSupportAdvertisement: VdmSupported
        mem[page_01_base + 163] = 1 << 6            # CdbSupport: one CDB instance
        # Page 1Ah (bank 0).
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        # Max/min optical power, scale=100.0 (10 uW steps -> mW).
        mem[base + 128:base + 130] = struct.pack(">H", 1000)
        mem[base + 130:base + 132] = struct.pack(">H", 500)
        # Max/min laser bias, scale=10000.0 (100 uA steps -> A).
        mem[base + 132:base + 134] = struct.pack(">H", 1000)
        mem[base + 134:base + 136] = struct.pack(">H", 500)
        # Byte 140: lane count in bits 7-1, control mode in bit 0 (1 -> APC).
        mem[base + 140] = (CMIS_LANES_PER_BANK << 1) | 1
        for lane in range(1, CMIS_LANES_PER_BANK + 1):
            # Lane-to-fiber mapping: 1 byte per lane starting at 224.
            mem[base + 224 + (lane - 1)] = lane
            # Lane frequency: 2 bytes per lane starting at 232, scale=0.2 -> GHz.
            freq_offset = base + 232 + 2 * (lane - 1)
            mem[freq_offset:freq_offset + 2] = struct.pack(">H", 100 * lane)

    def test_get_elsfp_info(self, mem_eeprom, api):
        self._populate_info(mem_eeprom)
        assert api.get_elsfp_info() == self.EXPECTED_INFO

    @pytest.mark.parametrize("cdb_inst, expected", [
        (0, False),   # CDB not supported
        (1, True),    # one CDB instance
        (2, True),    # two CDB instances
        (3, False),   # reserved encoding
    ])
    def test_is_cdb_supported(self, mem_eeprom, api, cdb_inst, expected):
        page_01_base = CmisPage.linear_offset(ADVERTISING_PAGE, 0, 0)
        mem_eeprom.memory[page_01_base + 163] = cdb_inst << 6
        assert api.is_cdb_supported() is expected


class TestElsfpThresholdInfo:
    """get_elsfp_threshold_info()"""

    EXPECTED_THRESHOLD_INFO = {
        # Page 1Ah: one module-wide register per threshold, applying to every
        # laser. Bytes 141-148 are raw 100 uA steps -> mA.
        "bias_alarm_high": 100.0,
        "bias_alarm_low": 10.0,
        "bias_warn_high": 90.0,
        "bias_warn_low": 20.0,
        # Page 1Ah bytes 149-156, raw 10 uW steps -> dBm.
        "optical_power_alarm_high": 10.0,
        "optical_power_alarm_low": -10.0,
        "optical_power_warn_high": 9.542,
        "optical_power_warn_low": -6.99,
        # Page 02h: the standard CMIS module thresholds.
        "temphighalarm": 75.0,
        "templowalarm": -5.0,
        "temphighwarning": 70.0,
        "templowwarning": 0.0,
        "vcchighalarm": 3.6,
        "vcclowalarm": 3.0,
        "vcchighwarning": 3.5,
        "vcclowwarning": 3.1,
        "rxpowerhighalarm": 3.01,
        "rxpowerlowalarm": -10.0,
        "rxpowerhighwarning": 0.0,
        "rxpowerlowwarning": -6.99,
        "txpowerhighalarm": 3.01,
        "txpowerlowalarm": -10.0,
        "txpowerhighwarning": 0.0,
        "txpowerlowwarning": -6.99,
        # Raw 1/500 A steps -> mA, doubled by a TX bias scaling exponent of 1.
        "txbiashighalarm": 20.0,
        "txbiaslowalarm": 2.0,
        "txbiashighwarning": 18.0,
        "txbiaslowwarning": 4.0,
    }

    def _populate_thresholds(self, mem_eeprom):
        mem = mem_eeprom.memory

        # Page 1Ah: module-wide bias thresholds (bytes 141-148, 100 uA steps)
        # and optical power thresholds (bytes 149-156, 10 uW steps).
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, 0, 0)
        for offset, raw in ((141, 1000), (143, 100), (145, 900), (147, 200),
                            (149, 1000), (151, 10), (153, 900), (155, 20)):
            mem[base + offset:base + offset + 2] = struct.pack(">H", raw)

        # Page 02h: the standard CMIS module thresholds.
        page_02_base = CmisPage.linear_offset(THRESHOLDS_PAGE, 0, 0)
        for offset, fmt, raw in (
            (128, ">h", 75 * 256), (130, ">h", -5 * 256),      # temperature alarms
            (132, ">h", 70 * 256), (134, ">h", 0),             # temperature warnings
            (136, ">H", 36000), (138, ">H", 30000),            # voltage alarms
            (140, ">H", 35000), (142, ">H", 31000),            # voltage warnings
            (176, ">H", 20000), (178, ">H", 1000),             # tx power alarms
            (180, ">H", 10000), (182, ">H", 2000),             # tx power warnings
            (184, ">H", 5000), (186, ">H", 500),               # tx bias alarms
            (188, ">H", 4500), (190, ">H", 1000),              # tx bias warnings
            (192, ">H", 20000), (194, ">H", 1000),             # rx power alarms
            (196, ">H", 10000), (198, ">H", 2000),             # rx power warnings
        ):
            mem[page_02_base + offset:page_02_base + offset + 2] = struct.pack(fmt, raw)

        # Page 01h: TX bias scaling exponent (byte 160, bits 4-3).
        page_01_base = CmisPage.linear_offset(ADVERTISING_PAGE, 0, 0)
        mem[page_01_base + 160] = 1 << 3

    def test_get_elsfp_threshold_info(self, mem_eeprom, api):
        self._populate_thresholds(mem_eeprom)
        assert api.get_elsfp_threshold_info() == self.EXPECTED_THRESHOLD_INFO


class TestElsfpStatusFlags:
    """get_elsfp_status_flags()"""

    def _populate_status_flags(self, mem_eeprom, bank=0):
        """Raise a fault on two lanes and a warning on one, plus the module flags.

        Byte 166 + bank gets a fault on the bank's first and third lanes and
        byte 174 + bank a warning on its second lane. Byte 165 summarises those:
        the module raises the summary bit whenever ANY lane has a fault or a
        warning, so with both kinds present both bits are set.
        """
        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, bank, 0)
        mem_eeprom.memory[base + 165] = 0x0C  # bit 2: summary fault, bit 3: summary warning
        mem_eeprom.memory[base + 166 + bank] = 0b0000_0101
        mem_eeprom.memory[base + 174 + bank] = 0b0000_0010
        # Page 00h lower byte 8: bit 2 datapath firmware fault, bit 1 module
        # firmware fault, bit 0 module state changed.
        mem_eeprom.memory[8] = 0b0000_0011

    def test_get_elsfp_status_flags(self, mem_eeprom, api):
        self._populate_status_flags(mem_eeprom)
        assert api.get_elsfp_status_flags() == {
            "lane_summary_fault": True,
            "lane_summary_warning": True,
            "datapath_firmware_fault": False,
            "module_firmware_fault": True,
            "module_state_changed": True,
            "FaultFlagLane1": True,
            "FaultFlagLane2": False,
            "FaultFlagLane3": True,
            "FaultFlagLane4": False,
            "FaultFlagLane5": False,
            "FaultFlagLane6": False,
            "FaultFlagLane7": False,
            "FaultFlagLane8": False,
            "WarnFlagLane1": False,
            "WarnFlagLane2": True,
            "WarnFlagLane3": False,
            "WarnFlagLane4": False,
            "WarnFlagLane5": False,
            "WarnFlagLane6": False,
            "WarnFlagLane7": False,
            "WarnFlagLane8": False,
        }


class TestElsfpStatus:
    """get_elsfp_status() and the banked / non-banked halves it is composed of."""

    EXPECTED_NON_BANKED_STATUS = {
        "module_state": "ModuleFault",
        "module_fault_cause": "Transmitter fault",
    }

    EXPECTED_BANKED_STATUS = {
        "enable_lane1": True,
        "enable_lane2": False,
        "enable_lane3": True,
        "enable_lane4": False,
        "enable_lane5": False,
        "enable_lane6": False,
        "enable_lane7": False,
        "enable_lane8": True,
        "state_lane1": "Lane Output on",
        "state_lane2": "Lane Output ramping",
        "state_lane3": "Lane Output off",
        "state_lane4": "Lane Output off",
        "state_lane5": "Lane Output off",
        "state_lane6": "Reserved",
        "state_lane7": "Lane Output off",
        "state_lane8": "Lane Output off",
        "output_fiber_checked_lane1": True,
        "output_fiber_checked_lane2": True,
        "output_fiber_checked_lane3": False,
        "output_fiber_checked_lane4": False,
        "output_fiber_checked_lane5": False,
        "output_fiber_checked_lane6": False,
        "output_fiber_checked_lane7": False,
        "output_fiber_checked_lane8": False,
        "fault_code_lane1": "Automatic Power Control (APC) control loop failure",
        "fault_code_lane2": "Automatic Current Control (ACC) control loop failure",
        "fault_code_lane3": "No alarm detected",
        "fault_code_lane4": "No alarm detected",
        "fault_code_lane5": "No alarm detected",
        "fault_code_lane6": "No alarm detected",
        "fault_code_lane7": "No alarm detected",
        "fault_code_lane8": "No alarm detected",
        "warning_code_lane1": "Automatic Current Control (ACC) control loop warning",
        "warning_code_lane2": "No warning detected",
        "warning_code_lane3": "No warning detected",
        "warning_code_lane4": "No warning detected",
        "warning_code_lane5": "No warning detected",
        "warning_code_lane6": "No warning detected",
        "warning_code_lane7": "No warning detected",
        "warning_code_lane8": "No warning detected",
    }

    def _populate_status(self, mem_eeprom, bank=0):
        """Put the module into ModuleFault with a mix of per-lane state.

        Page 00h lower carries the module state and fault cause. Page 1Ah
        carries the per-lane enable bits, lane states, output fiber checked
        bits, and the packed fault and warning codes.
        """
        # Byte 3 bits 3-1: module state, byte 41: fault cause.
        mem_eeprom.memory[3] = 5 << 1  # ModuleFault
        mem_eeprom.memory[41] = 4      # Transmitter fault

        base = CmisPage.linear_offset(ELSFP_ADVERTISEMENTS_FLAGS_CTRL_PAGE, bank, 0)
        # Byte 220: one enable bit per lane, bit 0 being the bank's first lane.
        mem_eeprom.memory[base + 220] = 0b1000_0101  # lanes 1, 3 and 8
        # Bytes 221-222: 2 bits of state per lane, 4 lanes to a byte.
        # Byte 221 holds lanes 1-4: lane 1 = 0b10 (on), lane 2 = 0b01 (ramping).
        mem_eeprom.memory[base + 221] = 0b0000_0110
        # Byte 222 holds lanes 5-8: lane 6 = 0b11 (reserved).
        mem_eeprom.memory[base + 222] = 0b0000_1100
        # Byte 223: one output fiber checked bit per lane.
        mem_eeprom.memory[base + 223] = 0b0000_0011  # lanes 1 and 2
        # Bytes 212-219: one byte per lane, low nibble the fault code and high
        # nibble the warning code.
        mem_eeprom.memory[base + 212] = 0x21  # lane 1: APC fault, ACC warning
        mem_eeprom.memory[base + 213] = 0x02  # lane 2: ACC fault, no warning

    def test_get_non_banked_elsfp_status(self, mem_eeprom, api):
        self._populate_status(mem_eeprom)
        assert api.get_non_banked_elsfp_status() == self.EXPECTED_NON_BANKED_STATUS

    def test_get_banked_elsfp_status(self, mem_eeprom, api):
        self._populate_status(mem_eeprom)
        assert api.get_banked_elsfp_status() == self.EXPECTED_BANKED_STATUS

    def test_get_elsfp_status(self, mem_eeprom, api):
        self._populate_status(mem_eeprom)
        assert api.get_elsfp_status() == {
            **self.EXPECTED_NON_BANKED_STATUS,
            **self.EXPECTED_BANKED_STATUS,
        }
