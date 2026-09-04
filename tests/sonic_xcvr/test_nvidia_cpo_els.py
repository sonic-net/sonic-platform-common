"""Tests for the NVIDIA CPO External Laser Source (ELS) memmaps and API."""
from unittest.mock import MagicMock, call

import pytest

from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.codes.nvidia.cpo_els import NvidiaCpoElsCodes
from sonic_platform_base.sonic_xcvr.cdb.nvidia.cpo_els_codes import NvidiaCpoElsCdbCodes
from sonic_platform_base.sonic_xcvr.fields import cdb_consts, consts
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_els import (
    NVIDIA_ELS_ADVERTISING_PAGE,
    NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD,
    NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD,
    NVIDIA_ELS_IDENTITY_PAGE,
    NVIDIA_ELS_MODULE_STATUS_PAGE,
    NVIDIA_ELS_THRESHOLDS_PAGE,
    NVIDIA_ELS_VOLTAGE_FIELD,
    NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD,
    NvidiaCpoElsCmisMemMap,
    NvidiaCpoElsCustomMonThresholdsPage,
    NvidiaCpoElsCustomMonValuePage,
    NvidiaCpoElsVoltagePage,
    NvidiaCpoElsVoltageThresholdsPage,
)
from sonic_platform_base.sonic_xcvr.cdb.nvidia.cpo_els_memmap import (
    CDB_READ_ELS_LASER_MONITORING_CMD,
    ELS_LASER_MONITORING_CAP_MASK_ALL,
    NUM_LASERS,
    NVIDIA_CPO_ELS_LASER_HEALTH,
    NVIDIA_CPO_ELS_LASER_MON_BANK,
    NVIDIA_CPO_ELS_LASER_MON_CAP,
    NVIDIA_CPO_ELS_LASER_MON_MASK,
    NVIDIA_CPO_ELS_LASER_MONITORING_REPLY,
    NVIDIA_CPO_ELS_LASER_MPD,
    NVIDIA_CPO_ELS_MODULE_POWER,
    NVIDIA_CPO_ELS_TEC_HEALTH,
    NVIDIA_CPO_ELS_TEC_VOLTAGE,
    CdbReadElsLaserMonitoring,
    NvidiaCpoElsCdbMemMap,
)
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_els import NvidiaCpoElsCmisApi


_LPL_REPLY_BASE = (cdb_consts.LPL_PAGE * 128) + cdb_consts.RPL_DATA_START_OFFSET


def _new_els_api_stub(cdb_handler=None, bank_id=0):
    """Bypass NvidiaCpoElsCmisApi.__init__ and stick MagicMocks in place of EEPROM/CDB."""
    api = NvidiaCpoElsCmisApi.__new__(NvidiaCpoElsCmisApi)
    api.xcvr_eeprom = MagicMock()
    api._cdb_mem_map = MagicMock() if cdb_handler is not None else None
    api._cdb_handler = cdb_handler
    api.bank_id = bank_id
    return api


class TestNvidiaCpoElsCmisMemMap:

    def setup_method(self):
        self.mm = NvidiaCpoElsCmisMemMap(NvidiaCpoElsCodes)

    def test_pages_present(self):
        leaf_offsets = []
        for field in self.mm._get_all_fields().values():
            offset = field.get_offset()
            if offset is None:
                continue
            leaf_offsets.append(offset)

        def upper(page):
            return range(page * 128 + 128, page * 128 + 256)
        expected_ranges = {
            "0x1A": upper(0x1A),
            "0x1B": upper(0x1B),
            "B0":   upper(NVIDIA_ELS_MODULE_STATUS_PAGE),
            "B1":   upper(NVIDIA_ELS_IDENTITY_PAGE),
            "B2":   upper(NVIDIA_ELS_ADVERTISING_PAGE),
            "0x00": range(0, 128),
            "0x02": upper(0x02),
        }
        for label, byte_range in expected_ranges.items():
            assert any(o in byte_range for o in leaf_offsets), (
                "page %s missing: no field offsets found in [%d, %d)"
                % (label, byte_range.start, byte_range.stop)
            )

    def test_b0_mirror_temperature_address(self):
        # B0 mirror applies a +128 shift to <128 offsets, so Temperature@14 -> 0xB0:142.
        field = self.mm.get_field(consts.TEMPERATURE_FIELD)
        assert field.get_offset() == NVIDIA_ELS_MODULE_STATUS_PAGE * 128 + 142

    def test_voltage_high_alarm_resolves_to_standard_page2_byte136(self):
        field = self.mm.get_field(consts.VOLTAGE_HIGH_ALARM_FIELD)
        assert field.get_offset() == 0x02 * 128 + 136

    def test_custom_mon_value_resolves_to_standard_page0_byte24(self):
        rg = self.mm.get_field(NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD)
        assert rg.get_offset() == 24
        assert any(f.name == consts.CUSTOM_MON for f in rg.fields)

    def test_custom_mon_thresholds_resolve_to_standard_page2(self):
        rg = self.mm.get_field(NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD)
        assert rg.get_offset() == 0x02 * 128 + 168
        names = {f.name for f in rg.fields}
        assert names == {
            consts.CUSTOM_MON_HIGH_ALARM,
            consts.CUSTOM_MON_LOW_ALARM,
            consts.CUSTOM_MON_HIGH_WARN,
            consts.CUSTOM_MON_LOW_WARN,
        }

    def test_voltage_resolves_to_standard_page0_byte16(self):
        rg = self.mm.get_field(NVIDIA_ELS_VOLTAGE_FIELD)
        assert rg.get_offset() == 16
        assert any(f.name == consts.VOLTAGE_FIELD for f in rg.fields)

    def test_voltage_thresholds_resolve_to_standard_page2_bytes_136_to_143(self):
        rg = self.mm.get_field(NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD)
        assert rg.get_offset() == 0x02 * 128 + 136
        names = {f.name for f in rg.fields}
        assert names == {
            consts.VOLTAGE_HIGH_ALARM_FIELD,
            consts.VOLTAGE_LOW_ALARM_FIELD,
            consts.VOLTAGE_HIGH_WARNING_FIELD,
            consts.VOLTAGE_LOW_WARNING_FIELD,
        }

    def test_extension_pages_are_distinct_groups_from_b0_b3(self):
        """Verifies the Custom-Mon extension is not merged with the B0/B3 mirrors
        (otherwise the RegGroupField would span kilobytes and break reads)."""
        custom_mon_value = self.mm.get_field(NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD)
        b0_mirror_monitors = self.mm.get_field(consts.MODULE_MONITORS_PAGE0_FIELD)
        assert custom_mon_value.get_offset() != b0_mirror_monitors.get_offset()
        b0_field_names = {f.name for f in b0_mirror_monitors.fields}
        assert consts.CUSTOM_MON not in b0_field_names \
            or b0_mirror_monitors.get_offset() >= NVIDIA_ELS_MODULE_STATUS_PAGE * 128


class TestExtensionPageStandalone:

    def test_value_page_addresses(self):
        page = NvidiaCpoElsCustomMonValuePage(NvidiaCpoElsCodes)
        assert page.page == 0
        fields = page.fields[NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD]
        assert len(fields) == 1
        assert fields[0].name == consts.CUSTOM_MON
        assert fields[0].get_offset() == 24

    def test_thresholds_page_addresses(self):
        page = NvidiaCpoElsCustomMonThresholdsPage(NvidiaCpoElsCodes)
        assert page.page == 0x02
        fields = page.fields[NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD]
        assert [f.name for f in fields] == [
            consts.CUSTOM_MON_HIGH_ALARM,
            consts.CUSTOM_MON_LOW_ALARM,
            consts.CUSTOM_MON_HIGH_WARN,
            consts.CUSTOM_MON_LOW_WARN,
        ]
        for i, f in enumerate(fields):
            assert f.get_offset() == 0x02 * 128 + 168 + i * 2

    def test_voltage_page_addresses(self):
        page = NvidiaCpoElsVoltagePage(NvidiaCpoElsCodes)
        assert page.page == 0
        fields = page.fields[NVIDIA_ELS_VOLTAGE_FIELD]
        assert len(fields) == 1
        assert fields[0].name == consts.VOLTAGE_FIELD
        assert fields[0].get_offset() == 16

    def test_voltage_thresholds_page_addresses(self):
        page = NvidiaCpoElsVoltageThresholdsPage(NvidiaCpoElsCodes)
        assert page.page == 0x02
        fields = page.fields[NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD]
        assert [f.name for f in fields] == [
            consts.VOLTAGE_HIGH_ALARM_FIELD,
            consts.VOLTAGE_LOW_ALARM_FIELD,
            consts.VOLTAGE_HIGH_WARNING_FIELD,
            consts.VOLTAGE_LOW_WARNING_FIELD,
        ]
        for i, f in enumerate(fields):
            assert f.get_offset() == 0x02 * 128 + 136 + i * 2


class TestCdbReadElsLaserMonitoring:

    def test_init_defaults(self):
        cmd = CdbReadElsLaserMonitoring()
        assert cmd.cmd_id == CDB_READ_ELS_LASER_MONITORING_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 3
        assert cmd.rpl_field == NVIDIA_CPO_ELS_LASER_MONITORING_REPLY

    def test_encode_packs_payload_dict_into_3_byte_lpl(self):
        cmd = CdbReadElsLaserMonitoring()
        encoded = cmd.encode({"cap_mask": 0x1F, "bank_id": 2, "laser_mask": 0xAA})

        # CDBCommand.encode prepends an 8-byte header (id|epl|lpl|cksum|rpl).
        assert encoded[:2] == b"\x90\x18"
        assert encoded[4] == 3
        assert encoded[8]  == 0x1F
        assert encoded[9]  == 0x02
        assert encoded[10] == 0xAA

    def test_encode_defaults_cap_mask_to_all(self):
        cmd = CdbReadElsLaserMonitoring()
        encoded = cmd.encode({"bank_id": 1})
        assert encoded[8]  == ELS_LASER_MONITORING_CAP_MASK_ALL
        assert encoded[9]  == 1
        assert encoded[10] == 0

    def test_encode_defaults_bank_id_to_zero(self):
        cmd = CdbReadElsLaserMonitoring()
        encoded = cmd.encode({"cap_mask": 0x05})
        assert encoded[8]  == 0x05
        assert encoded[9]  == 0
        assert encoded[10] == 0

    def test_encode_truncates_oversize_values_to_one_byte(self):
        cmd = CdbReadElsLaserMonitoring()
        encoded = cmd.encode({"cap_mask": 0x1FF, "bank_id": 0x100, "laser_mask": 0xABCD})
        assert encoded[8]  == 0xFF
        assert encoded[9]  == 0x00
        assert encoded[10] == 0xCD


class TestNvidiaCpoElsCdbMemMap:

    def setup_method(self):
        self.mm = NvidiaCpoElsCdbMemMap(NvidiaCpoElsCdbCodes)

    def test_inherits_standard_cdb_commands(self):
        from sonic_platform_base.sonic_xcvr.fields import cdb_consts as cc
        assert self.mm.get_cdb_cmd(cc.CDB_QUERY_STATUS_CMD) is not None

    def test_registers_laser_monitoring_command(self):
        cmd = self.mm.get_cdb_cmd(CDB_READ_ELS_LASER_MONITORING_CMD)
        assert cmd is not None
        assert isinstance(cmd, CdbReadElsLaserMonitoring)

    def test_reply_field_is_registered_at_lpl_offset(self):
        rg = self.mm.get_field(NVIDIA_CPO_ELS_LASER_MONITORING_REPLY)
        assert rg is not None
        assert rg.get_offset() == _LPL_REPLY_BASE + 0
        # Last field is u16 module-power at offset 52.
        assert rg.get_size() == 54

    def test_reply_decode_full(self):
        reply = bytearray(54)
        reply[0] = 0x1F                # cap mask
        reply[1] = 0x05                # bank echo
        reply[2] = 0xAA                # laser mask echo
        # offset 3 reserved
        for laser in range(NUM_LASERS):
            # u16 BE: laser_mpd (offset 4), tec_voltage (offset 20)
            reply[4 + laser * 2:4 + laser * 2 + 2] = (1000 + laser).to_bytes(2, "big")
            reply[20 + laser * 2:20 + laser * 2 + 2] = (2000 + laser).to_bytes(2, "big")
            # u8: laser_health (offset 36), tec_health (offset 44)
            reply[36 + laser] = 100 + laser
            reply[44 + laser] = 200 + laser
        # u16 BE module power at offset 52.
        reply[52:54] = (3050).to_bytes(2, "big")

        rg = self.mm.get_field(NVIDIA_CPO_ELS_LASER_MONITORING_REPLY)
        decoded = rg.decode(bytes(reply))

        assert decoded[NVIDIA_CPO_ELS_LASER_MON_CAP] == 0x1F
        assert decoded[NVIDIA_CPO_ELS_LASER_MON_BANK] == 0x05
        assert decoded[NVIDIA_CPO_ELS_LASER_MON_MASK] == 0xAA
        assert decoded[NVIDIA_CPO_ELS_MODULE_POWER] == 305.0

        for laser in range(NUM_LASERS):
            assert decoded["%s_%d" % (NVIDIA_CPO_ELS_LASER_MPD, laser)] == \
                (1000 + laser) / 1000.0
            assert decoded["%s_%d" % (NVIDIA_CPO_ELS_TEC_VOLTAGE, laser)] == \
                2000 + laser
            assert decoded["%s_%d" % (NVIDIA_CPO_ELS_LASER_HEALTH, laser)] == \
                (100 + laser) * 5.0
            assert decoded["%s_%d" % (NVIDIA_CPO_ELS_TEC_HEALTH, laser)] == \
                (200 + laser) * 5.0


class TestGetElsStatus:
    def test_full_status(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.side_effect = lambda f: {
            consts.TRANS_MODULE_STATUS_FIELD: {
                consts.MODULE_STATE: "ModuleReady",
                consts.MODULE_FAULT_CAUSE: "NoFault",
            },
            consts.VOLTAGE_FIELD: 3.31,
        }.get(f)
        out = api.get_els_status()
        assert out == {
            "els_module_state": "ModuleReady",
            "els_module_fault_cause": "NoFault",
            "els_vcc": 3.31,
        }

    def test_status_partial_when_status_read_fails(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.side_effect = lambda f: 3.4 if f == consts.VOLTAGE_FIELD else None
        out = api.get_els_status()
        # Status group failed -> 'Unknown'; vcc succeeded independently.
        assert out["els_module_state"] == "Unknown"
        assert out["els_module_fault_cause"] == "Unknown"
        assert out["els_vcc"] == 3.4

    def test_status_all_unknown_when_both_reads_fail(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = None
        assert api.get_els_status() == {
            "els_module_state": "Unknown",
            "els_module_fault_cause": "Unknown",
            "els_vcc": "N/A",
        }


class TestGetElsDomSensors:
    @staticmethod
    def _read_side_effect(per_field):
        def fake(field):
            return per_field.get(field)
        return fake

    def test_returns_temperature_and_voltage(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.side_effect = self._read_side_effect({
            NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD: {consts.CUSTOM_MON:    47.5},
            NVIDIA_ELS_VOLTAGE_FIELD:          {consts.VOLTAGE_FIELD:  3.4},
        })
        out = api.get_els_dom_sensors()
        assert out == {"els_temperature": 47.5, "els_voltage": 3.4}

    def test_reads_only_from_nvidia_extension_groups(self):
        """Verifies dispatch via NVIDIA-named groups, not via the B0 mirror."""
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = None
        api.get_els_dom_sensors()
        assert api.xcvr_eeprom.read.call_args_list == [
            call(NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD),
            call(NVIDIA_ELS_VOLTAGE_FIELD),
        ]

    def test_omits_voltage_when_only_temperature_succeeds(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.side_effect = self._read_side_effect({
            NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD: {consts.CUSTOM_MON: 30.0},
        })
        assert api.get_els_dom_sensors() == {"els_temperature": 30.0}

    def test_omits_temperature_when_only_voltage_succeeds(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.side_effect = self._read_side_effect({
            NVIDIA_ELS_VOLTAGE_FIELD: {consts.VOLTAGE_FIELD: 3.3},
        })
        assert api.get_els_dom_sensors() == {"els_voltage": 3.3}

    def test_returns_empty_when_both_reads_fail(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = None
        assert api.get_els_dom_sensors() == {}


class TestGetElsCmonTempThresholds:

    def test_full_decode(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = {
            consts.CUSTOM_MON_HIGH_ALARM: 80.0,
            consts.CUSTOM_MON_LOW_ALARM: -5.0,
            consts.CUSTOM_MON_HIGH_WARN: 70.0,
            consts.CUSTOM_MON_LOW_WARN: 0.0,
        }
        out = api.get_els_cmon_temp_thresholds()
        assert out == {
            "els_temphighalarm": 80.0,
            "els_templowalarm": -5.0,
            "els_temphighwarning": 70.0,
            "els_templowwarning": 0.0,
        }

    def test_reads_from_nvidia_extension_group(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = {}
        api.get_els_cmon_temp_thresholds()
        api.xcvr_eeprom.read.assert_called_once_with(NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD)

    def test_all_na_on_read_failure(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = None
        assert api.get_els_cmon_temp_thresholds() == {
            "els_temphighalarm":   "N/A",
            "els_templowalarm":    "N/A",
            "els_temphighwarning": "N/A",
            "els_templowwarning":  "N/A",
        }


class TestGetElsDomFlags:
    def test_decode_all_flags_set(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = 0xF0  # bits 4..7 all set
        out = api.get_els_dom_flags()
        assert out == {
            "els_custom_mon_high_alarm": True,
            "els_custom_mon_low_alarm": True,
            "els_custom_mon_high_warning": True,
            "els_custom_mon_low_warning": True,
        }

    def test_decode_individual_bits(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = 1 << 6  # high warning only
        out = api.get_els_dom_flags()
        assert out["els_custom_mon_high_warning"] is True
        assert out["els_custom_mon_high_alarm"] is False
        assert out["els_custom_mon_low_alarm"] is False
        assert out["els_custom_mon_low_warning"] is False

    def test_returns_none_when_byte_unreadable(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = None
        assert api.get_els_dom_flags() == {}


class TestGetElsInfo:
    def _admin_dict(self):
        return {
            consts.VENDOR_NAME_FIELD: "Nvidia",
            consts.VENDOR_OUI_FIELD: "00-1c-23",
            consts.VENDOR_PART_NO_FIELD: "ELSPN-001",
            consts.VENDOR_REV_FIELD: "A1",
            consts.VENDOR_SERIAL_NO_FIELD: "SN0001",
            consts.VENDOR_DATE_FIELD: "2026-04-01",
            consts.CONNECTOR_FIELD: "MPO",
            consts.ID_FIELD: "CPO ELS",
            consts.ID_ABBRV_FIELD: "ELS",
            consts.CMIS_MAJOR_REVISION: 5,
            consts.CMIS_MINOR_REVISION: 0,
            consts.EXT_ID_FIELD: {
                consts.POWER_CLASS_FIELD: "Power Class 5",
                consts.MAX_POWER_FIELD: 12.5,
            },
        }

    def test_full_info(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.side_effect = lambda f: {
            consts.ADMIN_INFO_FIELD: self._admin_dict(),
            consts.ADVERTISING_FIELD: {
                consts.HW_MAJOR_REV: 1, consts.HW_MINOR_REV: 2,
            },
        }.get(f)

        out = api.get_els_info()
        assert out["els_manufacturer"] == "Nvidia"
        assert out["els_model"] == "ELSPN-001"
        assert out["els_serial"] == "SN0001"
        assert out["els_cmis_rev"] == "5.0"
        assert out["els_ext_identifier"] == "Power Class 5"
        assert out["els_hardware_rev"] == "1.2"
        # No CMIS analog for cable_type yet.
        assert out["els_cable_type"] == "N/A"

    def test_missing_advertising_uses_admin_only(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.side_effect = lambda f: (
            self._admin_dict() if f == consts.ADMIN_INFO_FIELD else None)
        out = api.get_els_info()
        # Admin group succeeded; advertising failed -> hardware_rev='Unknown'.
        assert out["els_hardware_rev"] == "Unknown"
        assert out["els_manufacturer"] == "Nvidia"

    def test_missing_ext_id_falls_back_to_na(self):
        api = _new_els_api_stub()
        admin = self._admin_dict()
        admin[consts.EXT_ID_FIELD] = None
        api.xcvr_eeprom.read.side_effect = lambda f: (
            admin if f == consts.ADMIN_INFO_FIELD else None)
        out = api.get_els_info()
        assert out["els_ext_identifier"] == "N/A"

    def test_missing_cmis_rev_falls_back_to_na(self):
        api = _new_els_api_stub()
        admin = self._admin_dict()
        admin[consts.CMIS_MAJOR_REVISION] = None
        admin[consts.CMIS_MINOR_REVISION] = None
        api.xcvr_eeprom.read.side_effect = lambda f: (
            admin if f == consts.ADMIN_INFO_FIELD else None)
        out = api.get_els_info()
        assert out["els_cmis_rev"] == "N/A"

    def test_all_unknown_when_both_reads_fail(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = None
        # Both admin + advertising groups failed -> every els_* key is 'Unknown'.
        assert api.get_els_info() == {
            "els_manufacturer":     "Unknown",
            "els_vendor_oui":       "Unknown",
            "els_model":            "Unknown",
            "els_vendor_rev":       "Unknown",
            "els_serial":           "Unknown",
            "els_vendor_date":      "Unknown",
            "els_connector":        "Unknown",
            "els_type":             "Unknown",
            "els_type_abbrv_name":  "Unknown",
            "els_cmis_rev":         "Unknown",
            "els_ext_identifier":   "Unknown",
            "els_cable_type":       "Unknown",
            "els_hardware_rev":     "Unknown",
        }


class TestGetElsThresholds:
    """Verifies the els_vcc* contribution from the standard CMIS Voltage thresholds slot."""

    def test_full_decode(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = {
            consts.VOLTAGE_HIGH_ALARM_FIELD:   3.6,
            consts.VOLTAGE_LOW_ALARM_FIELD:    3.0,
            consts.VOLTAGE_HIGH_WARNING_FIELD: 3.5,
            consts.VOLTAGE_LOW_WARNING_FIELD:  3.1,
        }
        out = api.get_els_thresholds()
        assert out == {
            "els_vcchighalarm":   3.6,
            "els_vcclowalarm":    3.0,
            "els_vcchighwarning": 3.5,
            "els_vcclowwarning":  3.1,
        }

    def test_reads_from_nvidia_extension_group(self):
        """Verifies dispatch via the NVIDIA-named voltage-thresholds group, not the B3 mirror."""
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = {}
        api.get_els_thresholds()
        api.xcvr_eeprom.read.assert_called_once_with(NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD)

    def test_all_na_on_read_failure(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = None
        assert api.get_els_thresholds() == {
            "els_vcchighalarm":   "N/A",
            "els_vcclowalarm":    "N/A",
            "els_vcchighwarning": "N/A",
            "els_vcclowwarning":  "N/A",
        }

    def test_missing_subfields_become_na(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = {
            consts.VOLTAGE_HIGH_ALARM_FIELD: 3.6,
        }
        out = api.get_els_thresholds()
        assert out["els_vcchighalarm"] == 3.6
        assert out["els_vcclowwarning"] == "N/A"

    def test_does_not_emit_temp_or_power_or_bias_or_rx_keys(self):
        """Spec-alignment guard: temp / power / bias come from sibling getters."""
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = {
            consts.VOLTAGE_HIGH_ALARM_FIELD: 3.6,
        }
        out = api.get_els_thresholds()
        forbidden_substrings = ("temp", "txpower", "txbias", "rxpower", "optpower", "bias")
        for k in out:
            assert not any(sub in k for sub in forbidden_substrings), \
                "get_els_thresholds leaked non-vcc key: %s" % k


class TestGetElsLaserMonitoring:
    def _decoded_reply(self, cap=0x1F):
        raw = {
            NVIDIA_CPO_ELS_LASER_MON_CAP: cap,
            NVIDIA_CPO_ELS_LASER_MON_BANK: 0,
            NVIDIA_CPO_ELS_LASER_MON_MASK: 0,
            NVIDIA_CPO_ELS_MODULE_POWER: 30.5,
        }
        for laser in range(NUM_LASERS):
            raw["%s_%d" % (NVIDIA_CPO_ELS_LASER_MPD, laser)]    = (1500 + laser) / 1000.0
            raw["%s_%d" % (NVIDIA_CPO_ELS_TEC_VOLTAGE, laser)]  = 2500 + laser
            raw["%s_%d" % (NVIDIA_CPO_ELS_LASER_HEALTH, laser)] = (100 + laser) * 5.0
            raw["%s_%d" % (NVIDIA_CPO_ELS_TEC_HEALTH, laser)]   = (50 + laser) * 5.0
        return raw

    def test_returns_none_when_no_cdb_handler(self):
        api = _new_els_api_stub(cdb_handler=None)
        assert api.get_els_laser_monitoring() == {}

    def test_returns_none_when_send_returns_false(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = False
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_monitoring() == {}
        assert not cdb.read_reply.called

    def test_returns_none_when_send_raises(self):
        cdb = MagicMock()
        cdb.send_cmd.side_effect = RuntimeError("boom")
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_monitoring() == {}

    def test_returns_none_when_read_reply_raises(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.side_effect = RuntimeError("bad reply")
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_monitoring() == {}

    def test_returns_none_when_read_reply_is_none(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = None
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_monitoring() == {}

    def test_payload_is_dict_with_full_cap_mask_and_bank(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = self._decoded_reply()
        api = _new_els_api_stub(cdb_handler=cdb, bank_id=2)
        api.get_els_laser_monitoring()

        cmd_id = cdb.send_cmd.call_args[0][0]
        payload = cdb.send_cmd.call_args[1]["payload"]
        assert cmd_id == CDB_READ_ELS_LASER_MONITORING_CMD
        assert payload == {
            "cap_mask":   ELS_LASER_MONITORING_CAP_MASK_ALL,
            "bank_id":    2,
            "laser_mask": 0x00,
        }

    def test_payload_propagates_caller_overrides(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = self._decoded_reply()
        api = _new_els_api_stub(cdb_handler=cdb, bank_id=1)
        api.get_els_laser_monitoring(cap_mask=0x05, laser_mask=0xAA)
        payload = cdb.send_cmd.call_args[1]["payload"]
        assert payload == {"cap_mask": 0x05, "bank_id": 1, "laser_mask": 0xAA}

    def test_returns_raw_decoded_dict_unchanged(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        decoded = self._decoded_reply()
        cdb.read_reply.return_value = decoded
        api = _new_els_api_stub(cdb_handler=cdb)

        out = api.get_els_laser_monitoring()
        assert out is decoded
        assert out[NVIDIA_CPO_ELS_LASER_MON_CAP] == 0x1F
        assert out[NVIDIA_CPO_ELS_MODULE_POWER] == 30.5
        for laser in range(NUM_LASERS):
            assert out["%s_%d" % (NVIDIA_CPO_ELS_LASER_MPD, laser)] == \
                (1500 + laser) / 1000.0


class TestGetElsLaserDomSensors:
    """Verifies the spec-aligned projection of CDB 0x9018 onto els_* DOM_SENSOR keys."""

    def _decoded_reply(self, cap=0x1F):
        raw = {
            NVIDIA_CPO_ELS_LASER_MON_CAP: cap,
            NVIDIA_CPO_ELS_LASER_MON_BANK: 0,
            NVIDIA_CPO_ELS_LASER_MON_MASK: 0,
            NVIDIA_CPO_ELS_MODULE_POWER: 30.5,
        }
        for laser in range(NUM_LASERS):
            raw["%s_%d" % (NVIDIA_CPO_ELS_LASER_MPD, laser)]    = (1500 + laser) / 1000.0
            raw["%s_%d" % (NVIDIA_CPO_ELS_TEC_VOLTAGE, laser)]  = 2500 + laser
            raw["%s_%d" % (NVIDIA_CPO_ELS_LASER_HEALTH, laser)] = (100 + laser) * 5.0
            raw["%s_%d" % (NVIDIA_CPO_ELS_TEC_HEALTH, laser)]   = (50 + laser) * 5.0
        return raw

    def _api_with_raw(self, raw):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = raw
        return _new_els_api_stub(cdb_handler=cdb)

    def test_returns_empty_when_raw_empty(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = False
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_dom_sensors() == {}

    def test_returns_empty_when_no_cdb_handler(self):
        api = _new_els_api_stub(cdb_handler=None)
        assert api.get_els_laser_dom_sensors() == {}

    def test_full_decode_renames_to_spec_keys(self):
        api = self._api_with_raw(self._decoded_reply())
        out = api.get_els_laser_dom_sensors()

        assert out["els_power_consumption"] == 30.5

        # 0-indexed CDB suffix _0 -> 1-indexed spec suffix concatenated to the prefix.
        for laser in range(NUM_LASERS):
            n = laser + 1
            assert out["els_laser_mpd%d"              % n] == (1500 + laser) / 1000.0
            assert out["els_tec_voltage_laser%d"      % n] == 2500 + laser
            assert out["els_health_value_laser%d"     % n] == (100 + laser) * 5.0
            assert out["els_tec_health_value_laser%d" % n] == (50 + laser) * 5.0

    def test_strips_cdb_framing_bytes(self):
        """cap/bank/mask are CDB transport metadata and must not reach STATE_DB."""
        api = self._api_with_raw(self._decoded_reply())
        out = api.get_els_laser_dom_sensors()
        for framing in (NVIDIA_CPO_ELS_LASER_MON_CAP,
                        NVIDIA_CPO_ELS_LASER_MON_BANK,
                        NVIDIA_CPO_ELS_LASER_MON_MASK):
            assert framing not in out

    def test_emits_only_els_prefixed_keys(self):
        """Spec-alignment guard: every emitted key must start with 'els_'."""
        api = self._api_with_raw(self._decoded_reply())
        out = api.get_els_laser_dom_sensors()
        assert out, "expected non-empty projection from the full raw dict"
        for k in out:
            assert k.startswith("els_"), \
                "non-spec key leaked from get_els_laser_dom_sensors: %s" % k
            assert not k.startswith("NvidiaCpoEls"), \
                "raw CDB key leaked from get_els_laser_dom_sensors: %s" % k

    def test_partial_reply_only_emits_present_fields(self):
        """A partial raw reply emits only the keys present (no 'N/A' fillers)."""
        raw = {
            NVIDIA_CPO_ELS_MODULE_POWER: 12.0,
            "%s_0" % NVIDIA_CPO_ELS_TEC_VOLTAGE: 2500,
            "%s_3" % NVIDIA_CPO_ELS_LASER_HEALTH: 250.0,
        }
        api = self._api_with_raw(raw)
        out = api.get_els_laser_dom_sensors()
        assert out == {
            "els_power_consumption":    12.0,
            "els_tec_voltage_laser1":   2500,
            "els_health_value_laser4":  250.0,
        }


class TestAggregatorOverrides:

    def _api_with_stubbed_children(self, **child_returns):
        api = _new_els_api_stub()
        for name, value in child_returns.items():
            setattr(api, name, MagicMock(return_value=value))
        return api

    def test_info_returns_els_info_only(self):
        api = self._api_with_stubbed_children(
            get_els_info={
                "els_manufacturer": "Nvidia",
                "els_model": "ELSPN-001",
                "els_hardware_rev": "1.2",
            },
        )
        out = api.get_transceiver_info()
        assert out == {
            "els_manufacturer": "Nvidia",
            "els_model": "ELSPN-001",
            "els_hardware_rev": "1.2",
        }

    def test_info_returns_empty_when_els_info_empty(self):
        api = self._api_with_stubbed_children(get_els_info={})
        assert api.get_transceiver_info() == {}

    def test_dom_real_value_merges_lane_temp_and_laser_monitoring(self):
        """Unions ELSFP lane monitors, ELS dom sensors, and the CDB 0x9018 projection."""
        api = self._api_with_stubbed_children(
            get_elsfp_lane_monitors={"els_bias_current_monitor1": 10},
            get_els_dom_sensors={"els_temperature": 50.0},
            get_els_laser_dom_sensors={
                "els_laser_mpd1":         1.5,
                "els_power_consumption":  30.5,
            },
        )
        out = api.get_transceiver_dom_real_value()
        assert out == {
            "els_bias_current_monitor1": 10,
            "els_temperature":           50.0,
            "els_laser_mpd1":            1.5,
            "els_power_consumption":     30.5,
        }

    def test_dom_real_value_returns_empty_when_all_children_empty(self):
        api = self._api_with_stubbed_children(
            get_elsfp_lane_monitors=None,
            get_els_dom_sensors={},
            get_els_laser_dom_sensors={},
        )
        assert api.get_transceiver_dom_real_value() == {}

    def test_threshold_info_merges_elsfp_thresholds_setpoints_vcc_and_temp(self):
        """Unions ELSFP bias/opt thresholds + per-lane setpoints, ELS vcc and temp thresholds."""
        api = self._api_with_stubbed_children(
            get_elsfp_lane_thresholds={"els_biashighalarm": 1.0},
            get_elsfp_lane_setpoints={
                "els_bias_current_setpoint1": 20,
                "els_opt_power_setpoint1":    1500,
            },
            get_els_thresholds={"els_vcchighalarm": 3.6},
            get_els_cmon_temp_thresholds={"els_temphighalarm": 70.0},
        )
        out = api.get_transceiver_threshold_info()
        assert out == {
            "els_biashighalarm":           1.0,
            "els_bias_current_setpoint1":  20,
            "els_opt_power_setpoint1":     1500,
            "els_vcchighalarm":            3.6,
            "els_temphighalarm":           70.0,
        }

    def test_dom_flags_merges_lane_flags_and_cmon(self):
        """Unions ELSFP per-lane indexed flags and the NVIDIA Custom Monitor flag quartet."""
        api = self._api_with_stubbed_children(
            get_elsfp_lane_flags={"els_HighBiasAlarm1": True},
            get_els_dom_flags={"els_custom_mon_high_alarm": False},
        )
        out = api.get_transceiver_dom_flags()
        assert out == {
            "els_HighBiasAlarm1":          True,
            "els_custom_mon_high_alarm":   False,
        }

    def test_dom_flags_does_not_emit_setpoints(self):
        """Spec-alignment guard: setpoints belong in DOM_THRESHOLD_INFO, not DOM_FLAG."""
        api = self._api_with_stubbed_children(
            get_elsfp_lane_flags={"els_HighBiasAlarm1": True},
            get_elsfp_lane_setpoints={
                "els_bias_current_setpoint1": 20,
                "els_opt_power_setpoint1":    1500,
            },
            get_els_dom_flags={"els_custom_mon_high_alarm": False},
        )
        out = api.get_transceiver_dom_flags()
        for k in out:
            assert "setpoint" not in k, \
                "lane setpoint leaked into get_transceiver_dom_flags: %s" % k

    def test_status_merges_lane_state_control_mode_codes_and_status(self):
        """Unions ELSFP lane state + control mode + fault/warning codes and ELS module status."""
        api = self._api_with_stubbed_children(
            get_elsfp_lane_state={
                "els_lane_enable1": 1,
                "els_lane_state1":  2,
            },
            get_elsfp_control_mode={"els_control_mode_APCACC": 0},
            get_elsfp_fault_warning_codes={
                "els_fault_code1":   0,
                "els_warning_code1": 2,
            },
            get_els_status={"els_module_state": "ModuleReady"},
        )
        out = api.get_transceiver_status()
        assert out == {
            "els_lane_enable1":         1,
            "els_lane_state1":          2,
            "els_control_mode_APCACC":  0,
            "els_fault_code1":          0,
            "els_warning_code1":        2,
            "els_module_state":         "ModuleReady",
        }

    def test_status_does_not_emit_setpoint_or_output_fiber_keys(self):
        """Spec-alignment guard: setpoints belong in DOM_THRESHOLD_INFO, output-fiber in STATUS_FLAGS."""
        api = self._api_with_stubbed_children(
            get_elsfp_lane_state={"els_lane_enable1": 1},
            get_elsfp_control_mode={"els_control_mode_APCACC": 0},
            get_elsfp_lane_setpoints={"els_bias_current_setpoint1": 20},
            get_elsfp_output_fiber_checked={
                "els_output_fiber_checked_flag_lane1": 1,
            },
            get_els_status={"els_module_state": "ModuleReady"},
        )
        out = api.get_transceiver_status()
        for k in out:
            assert "setpoint" not in k, \
                "lane setpoint leaked into get_transceiver_status: %s" % k
            assert "output_fiber_checked" not in k, \
                "output-fiber-checked leaked into get_transceiver_status: %s" % k

    def test_status_flags_merges_per_lane_flags_and_output_fiber(self):
        """Unions ELSFP per-lane fault/warn flag bytes and output-fiber-checked bits."""
        api = self._api_with_stubbed_children(
            get_elsfp_status_flags={"els_fault_flag_lane1": True},
            get_elsfp_output_fiber_checked={
                "els_output_fiber_checked_flag_lane1": 1,
                "els_output_fiber_checked_flag_lane2": 0,
            },
        )
        out = api.get_transceiver_status_flags()
        assert out == {
            "els_fault_flag_lane1":               True,
            "els_output_fiber_checked_flag_lane1": 1,
            "els_output_fiber_checked_flag_lane2": 0,
        }

    def test_status_flags_does_not_emit_codes_or_laser_monitoring_keys(self):
        """Spec-alignment guard: 4-bit codes are STATUS, laser monitoring is DOM_SENSOR."""
        api = self._api_with_stubbed_children(
            get_elsfp_status_flags={"els_fault_flag_lane1": True},
            get_elsfp_output_fiber_checked={
                "els_output_fiber_checked_flag_lane1": 1,
            },
            get_elsfp_fault_warning_codes={
                "els_fault_code1":   0,
                "els_warning_code1": 2,
            },
            get_els_laser_dom_sensors={
                "els_laser_mpd1":         1.5,
                "els_power_consumption":  30.5,
            },
        )
        out = api.get_transceiver_status_flags()
        for k in out:
            assert not k.endswith("_code1"), \
                "fault/warning code leaked into STATUS_FLAGS: %s" % k
            assert "laser_mpd"     not in k
            assert "tec_voltage"   not in k
            assert "tec_health"    not in k
            assert "health_value"  not in k
            assert "power_consump" not in k

    def test_status_flags_returns_empty_when_all_children_empty(self):
        api = self._api_with_stubbed_children(
            get_elsfp_status_flags=None,
            get_elsfp_output_fiber_checked=None,
        )
        assert api.get_transceiver_status_flags() == {}


def test_factory_style_instantiation():
    """End-to-end: compose memmap + CDB memmap + API exactly as the factory does."""
    from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom

    reader = MagicMock(return_value=b"\x00")
    writer = MagicMock(return_value=True)

    mm = NvidiaCpoElsCmisMemMap(NvidiaCpoElsCodes, bank=1)
    eeprom = XcvrEeprom(reader, writer, mm)
    cdb_mm = NvidiaCpoElsCdbMemMap(NvidiaCpoElsCdbCodes)
    api = NvidiaCpoElsCmisApi(eeprom, cdb_mem_map=cdb_mm)

    assert api.cdb_handler is not None
    assert api.cdb_handler.mem_map is cdb_mm
    assert api.bank_id == 0


class TestElsfpNestedGroupDecode:
    """End-to-end regression for the nested RegGroupField decode.

    Several ELSFP 0x1A/0x1B groups are composed as a RegGroupField whose members
    are themselves RegGroupFields, so RegGroupField.decode yields a nested dict.
    The per-lane getters must resolve through that extra level; otherwise every
    per-lane value comes back 'N/A' even when the EEPROM holds real data. These
    tests run the real XcvrEeprom decode path with deterministic non-zero bytes
    (the rest of the suite stubs the getters, which is why this slipped through).
    """

    @staticmethod
    def _api_with_nonzero_eeprom(fill=0x12, bank_id=0):
        from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
        from sonic_platform_base.sonic_xcvr.api.public.elsfp_cmis import ElsfpCmisApi

        mm = NvidiaCpoElsCmisMemMap(NvidiaCpoElsCodes)
        eeprom = XcvrEeprom(lambda off, size: bytes([fill] * size),
                            lambda off, size, data: True, mm)
        api = ElsfpCmisApi.__new__(ElsfpCmisApi)
        api.xcvr_eeprom = eeprom
        api.bank_id = bank_id
        return api

    def _assert_no_na(self, getter_name, expected_len):
        api = self._api_with_nonzero_eeprom()
        out = getattr(api, getter_name)()
        assert out is not None and len(out) == expected_len, \
            "%s returned %r" % (getter_name, out)
        na = [k for k, v in out.items() if v == 'N/A']
        assert not na, "%s left these fields 'N/A': %s" % (getter_name, na)

    def test_lane_monitors_populated(self):
        # 8 lanes x (bias, opt, voltage) + els_icc = 25
        self._assert_no_na("get_elsfp_lane_monitors", 25)

    def test_lane_setpoints_populated(self):
        self._assert_no_na("get_elsfp_lane_setpoints", 16)

    def test_control_mode_populated(self):
        self._assert_no_na("get_elsfp_control_mode", 1)

    def test_fault_warning_codes_populated(self):
        self._assert_no_na("get_elsfp_fault_warning_codes", 16)

    def test_lane_state_populated(self):
        # lane_enable is flat and already worked; lane_state was nested.
        api = self._api_with_nonzero_eeprom()
        out = api.get_elsfp_lane_state()
        state_na = [k for k in out if k.startswith('els_lane_state') and out[k] == 'N/A']
        assert not state_na, "lane_state still 'N/A': %s" % state_na

    def test_status_flags_populated(self):
        self._assert_no_na("get_elsfp_status_flags", 16)

    def test_icc_monitor_still_flat(self):
        # els_icc comes from a flat member; guard against regressing it.
        api = self._api_with_nonzero_eeprom()
        assert api.get_elsfp_lane_monitors()['els_icc'] != 'N/A'
