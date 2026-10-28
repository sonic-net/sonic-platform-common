import contextlib
#
# SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
# Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

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
    NVIDIA_ELS_MODULE_STATE_FIELD,
    NVIDIA_ELS_MODULE_STATUS_PAGE,
    NVIDIA_ELS_THRESHOLDS_PAGE,
    NVIDIA_ELS_VOLTAGE_FIELD,
    NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD,
    NvidiaCpoElsCmisMemMap,
    NvidiaCpoElsCustomMonThresholdsPage,
    NvidiaCpoElsCustomMonValuePage,
    NvidiaCpoElsModuleStatePage,
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

from .eeprom_utils import InMemoryEeprom


_LPL_REPLY_BASE = (cdb_consts.LPL_PAGE * 128) + cdb_consts.RPL_DATA_START_OFFSET


def _new_els_api_stub(cdb_handler=None, bank_id=0):
    """Bypass NvidiaCpoElsCmisApi.__init__ and stick MagicMocks in place of EEPROM/CDB."""
    api = NvidiaCpoElsCmisApi.__new__(NvidiaCpoElsCmisApi)
    api.xcvr_eeprom = MagicMock()
    api._vendor_cdb_mem_map = MagicMock() if cdb_handler is not None else None
    api._vendor_cdb_handler = cdb_handler
    api.xcvr_eeprom.mem_map.bank = bank_id
    return api


class TestModuleStateComesFromPage00:
    """Page B0 is a static snapshot. The live state is page 0x00 byte 3."""

    def test_a_page00_read_returns_the_decoded_state(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = {consts.MODULE_STATE: "ModuleReady"}

        assert api.get_module_state() == "ModuleReady"
        api.xcvr_eeprom.read.assert_called_once_with(NVIDIA_ELS_MODULE_STATE_FIELD)

    def test_a_failed_page00_read_is_none(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = None

        assert api.get_module_state() is None

    def test_the_status_carries_the_state_but_not_the_fault_cause(self):
        """The fault cause exists only on the static B0 snapshot."""
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.side_effect = lambda field: {
            NVIDIA_ELS_MODULE_STATE_FIELD: {consts.MODULE_STATE: "ModuleFault"},
            consts.MODULE_FAULT_CAUSE: "No Fault detected",
        }[field]

        assert api.get_non_banked_elsfp_status() == {"module_state": "ModuleFault"}

    def test_a_failed_state_read_leaves_no_status(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read.return_value = None

        assert api.get_non_banked_elsfp_status() is None


class TestLaserMonitoringLeavesTheCdbTargetAlone:
    """The vModule routes CDB 0x9018 to the laser source by itself."""

    def test_the_command_is_sent_without_selecting_a_target(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = {'reply': 1}
        api = _new_els_api_stub(cdb_handler=cdb)

        assert api.get_els_laser_monitoring() == {'reply': 1}
        cdb.send_cmd.assert_called_once()
        api.xcvr_eeprom.write_raw.assert_not_called()
        api.xcvr_eeprom.read_raw.assert_not_called()
        api.xcvr_eeprom.writer.assert_not_called()
        api.xcvr_eeprom.reader.assert_not_called()


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
            "B3":   upper(NVIDIA_ELS_THRESHOLDS_PAGE),
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

    def test_the_bare_voltage_threshold_name_is_the_b3_mirrors(self):
        """The ELS's own voltage thresholds are read as the
        NvidiaElsVoltageThresholds group, never by the bare field name."""
        field = self.mm.get_field(consts.VOLTAGE_HIGH_ALARM_FIELD)
        assert field.get_offset() == NVIDIA_ELS_THRESHOLDS_PAGE * 128 + 136

    def test_module_state_resolves_to_page0_byte3_not_the_b0_mirror(self):
        live = self.mm.get_field(NVIDIA_ELS_MODULE_STATE_FIELD)
        snapshot = self.mm.get_field(consts.MODULE_STATE)
        assert live is not snapshot
        assert live.get_offset() == 3
        assert [f.name for f in live.fields] == [consts.MODULE_STATE]
        assert live.get_size() == 1
        # The bare name stays on the B0 mirror: offset 3 shifted up by 128.
        assert snapshot.get_offset() == NVIDIA_ELS_MODULE_STATUS_PAGE * 128 + 131

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


    def test_the_standard_thresholds_resolve_to_the_b3_mirror(self):
        rg = self.mm.get_field(consts.THRESHOLDS_FIELD)
        assert rg.get_offset() == NVIDIA_ELS_THRESHOLDS_PAGE * 128 + 128
        names = {f.name for f in rg.fields}
        assert {consts.VOLTAGE_HIGH_ALARM_FIELD, consts.VOLTAGE_LOW_ALARM_FIELD,
                consts.VOLTAGE_HIGH_WARNING_FIELD, consts.VOLTAGE_LOW_WARNING_FIELD} <= names

    def test_custom_mon_value_is_standalone_not_merged_with_mirrors(self):
        """The NVIDIA custom-mon value is published under its own key
        (NvidiaElsCustomMonValue), deliberately targeting the page-0 standard
        slot without reusing the standard MODULE_MONITORS_PAGE0_FIELD name.

        That keeps it a small standalone group at page 0 byte 24, so the ELS
        read path (get_module_temperature) issues a 2-byte read rather than being
        merged with the B0 monitors mirror into a multi-KB RegGroupField span.
        The standard MODULE_MONITORS_PAGE0_FIELD group is intentionally unused
        on this memmap; only the NVIDIA-keyed groups are read.
        """
        custom_mon_value = self.mm.get_field(NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD)
        module_monitors = self.mm.get_field(consts.MODULE_MONITORS_PAGE0_FIELD)
        # Distinct group objects at distinct offsets - not the same merged group.
        assert custom_mon_value is not module_monitors
        assert custom_mon_value.get_offset() == 24
        # Standalone: only its own single leaf, so the read span stays 2 bytes.
        assert [f.name for f in custom_mon_value.fields] == [consts.CUSTOM_MON]


class TestExtensionPageStandalone:

    def test_module_state_page_addresses(self):
        page = NvidiaCpoElsModuleStatePage(NvidiaCpoElsCodes)
        assert page.page == 0
        fields = page.fields[NVIDIA_ELS_MODULE_STATE_FIELD]
        assert len(fields) == 1
        assert fields[0].name == consts.MODULE_STATE
        assert fields[0].get_offset() == 3

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


def recording_lock(events):
    """A CDB lock that records when it is taken and released."""
    @contextlib.contextmanager
    def lock():
        events.append('lock')
        try:
            yield
        finally:
            events.append('unlock')
    return lock


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

    def test_returns_empty_when_no_cdb_handler(self):
        api = _new_els_api_stub(cdb_handler=None)
        assert api.get_els_laser_monitoring() == {}

    def test_returns_none_when_send_returns_false(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = False
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_monitoring() is None
        assert not cdb.read_reply.called

    def test_returns_none_when_send_raises(self):
        cdb = MagicMock()
        cdb.send_cmd.side_effect = RuntimeError("boom")
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_monitoring() is None

    def test_command_and_reply_hold_the_cdb_lock(self):
        events = []
        cdb = MagicMock()
        cdb.send_cmd.side_effect = lambda *args, **kwargs: events.append('send') or True
        cdb.read_reply.side_effect = lambda *args: events.append('reply') or self._decoded_reply()
        api = _new_els_api_stub(cdb_handler=cdb)
        api.cdb_lock = recording_lock(events)

        assert api.get_els_laser_monitoring() == self._decoded_reply()

        assert events == ['lock', 'send', 'reply', 'unlock']

    def test_returns_none_when_read_reply_raises(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.side_effect = RuntimeError("bad reply")
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_monitoring() is None

    def test_returns_none_when_read_reply_is_none(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = None
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_monitoring() is None

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
    """The CDB 0x9018 reply, as DOM readings of this bank's lasers."""

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

    def _api_with_raw(self, raw, bank_id=0):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = raw
        return _new_els_api_stub(cdb_handler=cdb, bank_id=bank_id)

    def test_returns_none_when_the_cdb_read_fails(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = False
        api = _new_els_api_stub(cdb_handler=cdb)
        assert api.get_els_laser_dom_sensors() is None

    def test_returns_empty_when_raw_empty(self):
        api = self._api_with_raw({})
        assert api.get_els_laser_dom_sensors() == {}

    def test_returns_empty_when_no_cdb_handler(self):
        api = _new_els_api_stub(cdb_handler=None)
        assert api.get_els_laser_dom_sensors() == {}

    @pytest.mark.parametrize("bank_id, first_lane", [(0, 1), (1, 9), (3, 25)])
    def test_each_laser_is_published_under_its_absolute_lane(self, bank_id, first_lane):
        api = self._api_with_raw(self._decoded_reply(), bank_id=bank_id)
        out = api.get_els_laser_dom_sensors()

        assert out["power_consumption"] == 30.5
        for laser in range(NUM_LASERS):
            lane = first_lane + laser
            assert out["laser_mpd_lane%d" % lane] == (1500 + laser) / 1000.0
            assert out["tec_voltage_lane%d" % lane] == 2500 + laser
            assert out["health_value_lane%d" % lane] == (100 + laser) * 5.0
            assert out["tec_health_value_lane%d" % lane] == (50 + laser) * 5.0

    def test_strips_cdb_framing_bytes(self):
        """cap/bank/mask are CDB transport metadata and must not reach STATE_DB."""
        api = self._api_with_raw(self._decoded_reply())
        out = api.get_els_laser_dom_sensors()
        for framing in (NVIDIA_CPO_ELS_LASER_MON_CAP,
                        NVIDIA_CPO_ELS_LASER_MON_BANK,
                        NVIDIA_CPO_ELS_LASER_MON_MASK):
            assert framing not in out

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
            "power_consumption":   12.0,
            "tec_voltage_lane1":   2500,
            "health_value_lane4":  250.0,
        }

    def test_the_readings_join_the_banked_dom_half(self):
        api = self._api_with_raw(self._decoded_reply())
        api.get_per_lane_bias_current_monitor = MagicMock(return_value={})
        api.get_per_lane_opt_power_monitor = MagicMock(return_value={})
        api.get_per_lane_voltage_monitor = MagicMock(return_value={})
        api.get_icc_monitor = MagicMock(return_value=0.1)

        dom = api.get_banked_elsfp_dom_real_value()
        assert dom["icc"] == 0.1
        assert dom["power_consumption"] == 30.5
        assert dom["laser_mpd_lane1"] == 1.5

    def test_the_banked_dom_half_fails_when_the_cdb_read_fails(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = False
        api = _new_els_api_stub(cdb_handler=cdb)
        api.get_per_lane_bias_current_monitor = MagicMock(return_value={})
        api.get_per_lane_opt_power_monitor = MagicMock(return_value={})
        api.get_per_lane_voltage_monitor = MagicMock(return_value={})
        api.get_icc_monitor = MagicMock(return_value=0.1)

        # A partial dict would hide the missing laser readings (#5357091).
        assert api.get_banked_elsfp_dom_real_value() is None

    def test_the_setpoints_join_the_banked_dom_half(self):
        api = self._api_with_raw({})
        api.get_per_lane_bias_current_monitor = MagicMock(return_value={})
        api.get_per_lane_opt_power_monitor = MagicMock(return_value={})
        api.get_per_lane_voltage_monitor = MagicMock(return_value={})
        api.get_icc_monitor = MagicMock(return_value=0.1)
        api.get_els_setpoint_values = MagicMock(return_value={
            "bias_current_setpoint_lane1": 20.0,
            "optical_power_setpoint_lane1": 21.761,
        })

        dom = api.get_banked_elsfp_dom_real_value()
        assert dom["bias_current_setpoint_lane1"] == 20.0
        assert dom["optical_power_setpoint_lane1"] == 21.761


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
    assert api._get_first_lane_for_bank() == 9


BANK_STRIDE = 256 * 128

# Pages 10h-2Fh are selected per bank, so what they hold answers for one bank's
# lanes. The laser source keeps its lane data on 1Ah and 1Bh, inside that range.
BANKED_PAGES = frozenset(range(0x10, 0x30))
CDB_PAGES = frozenset(range(0x9F, 0xB0))


def _page_of(offset):
    """The CMIS page a linear EEPROM offset falls on, for whichever bank."""
    offset %= BANK_STRIDE
    if offset < 128:
        return 0x00
    return offset // 128 - 1


class TestTheBankedSplitReadsTheRightPages:
    """Which pages each half of a split table actually reaches.

    A non-banked half is read once and its answer handed to every port of the
    laser source, so it may only read what reads the same from every bank.
    Should one of them reach a banked page, all four ports are quietly given
    whichever bank was selected when the read happened - a wrong reading rather
    than a slow one, and one no reading of the field names would show up.

    So these tests go by the addresses. Two are taken: the page each read lands
    on, and whether the same read moves when the memory map is built for the
    next bank, which is what banked addressing means here.
    """

    FAMILIES = ('status', 'dom_real_value', 'dom_flags', 'status_flags')

    # The halves xcvrd reads once per laser source and shares across its
    # ports. The status flags are read per port: their non-banked half holds
    # the lane summary, which ElsfpApi reads off page 1Ah.
    SHARED_FAMILIES = ('status', 'dom_real_value', 'dom_flags')

    def _recording_api(self, bank=0):
        """An api over an in-memory laser source, and the reads it makes."""
        mem_map = NvidiaCpoElsCmisMemMap(NvidiaCpoElsCodes, bank=bank)
        eeprom = InMemoryEeprom(mem_map, num_banks=4)

        reads = []
        reader = eeprom.eeprom.reader

        def recording_reader(offset, size):
            reads.append((offset, size))
            return reader(offset, size)

        eeprom.eeprom.reader = recording_reader
        return NvidiaCpoElsCmisApi(eeprom.eeprom, init_cdb_fw_handler=False), reads

    def _pages(self, reads):
        return {_page_of(byte) for offset, size in reads
                for byte in range(offset, offset + size)}

    @pytest.mark.parametrize('family', SHARED_FAMILIES)
    def test_the_non_banked_half_stays_off_the_banked_pages(self, family):
        api, reads = self._recording_api()

        getattr(api, 'get_non_banked_elsfp_%s' % family)()

        pages = self._pages(reads)
        assert not pages & BANKED_PAGES, sorted(hex(page) for page in pages & BANKED_PAGES)
        assert not pages & CDB_PAGES, sorted(hex(page) for page in pages & CDB_PAGES)

    @pytest.mark.parametrize('family', SHARED_FAMILIES)
    def test_the_non_banked_half_reads_the_same_bytes_whatever_the_bank(self, family):
        """The page numbers above are the rule of thumb; this is the property
        they stand for. A vendor page outside 10h-2Fh that was nonetheless
        addressed with the bank would pass the test above and fail this one."""
        api0, reads0 = self._recording_api(bank=0)
        api1, reads1 = self._recording_api(bank=1)

        getattr(api0, 'get_non_banked_elsfp_%s' % family)()
        getattr(api1, 'get_non_banked_elsfp_%s' % family)()

        assert reads0 == reads1

    @pytest.mark.parametrize('family', FAMILIES)
    def test_the_banked_half_follows_the_bank(self, family):
        """The other direction: a half reading nothing banked holds fields that
        are the same for the whole laser source, and paying for them once per
        port is the cost the split exists to avoid."""
        api0, reads0 = self._recording_api(bank=0)
        api1, reads1 = self._recording_api(bank=1)

        getattr(api0, 'get_banked_elsfp_%s' % family)()
        getattr(api1, 'get_banked_elsfp_%s' % family)()

        assert reads0 and self._pages(reads0) <= BANKED_PAGES
        assert reads0 != reads1

    @pytest.mark.parametrize('family', SHARED_FAMILIES)
    def test_the_banked_pages_move_by_a_whole_bank(self, family):
        api0, reads0 = self._recording_api(bank=0)
        api1, reads1 = self._recording_api(bank=1)

        getattr(api0, 'get_banked_elsfp_%s' % family)()
        getattr(api1, 'get_banked_elsfp_%s' % family)()

        assert [(offset + BANK_STRIDE, size) for offset, size in reads0] == reads1

    def test_the_lane_flags_are_one_byte_per_bank(self):
        """The fault and warning flag bytes are laid out linearly, one per bank,
        and clear on read, so each bank reads its own byte - the next one along,
        under the next bank's addressing - and leaves the others' flags latched."""
        api0, reads0 = self._recording_api(bank=0)
        api1, reads1 = self._recording_api(bank=1)

        api0.get_banked_elsfp_status_flags()
        api1.get_banked_elsfp_status_flags()

        assert all(size == 1 for _, size in reads0 + reads1)
        assert [(offset + BANK_STRIDE + 1, size) for offset, size in reads0] == reads1

    @pytest.mark.parametrize('family', FAMILIES)
    def test_the_two_halves_hold_every_field_the_whole_table_does(self, family):
        """A field landing in neither half would leave the laser source
        publishing less than it used to, with nothing to say so."""
        api, _ = self._recording_api()

        halves = {**getattr(api, 'get_non_banked_elsfp_%s' % family)(),
                  **getattr(api, 'get_banked_elsfp_%s' % family)()}
        whole = getattr(api, 'get_elsfp_%s' % family)()

        assert whole and set(whole) == set(halves)

    @pytest.mark.parametrize('family', FAMILIES)
    def test_neither_half_is_empty(self, family):
        """Both halves carry fields on this platform, so an empty one means a
        table went whole into the other and lost its scope."""
        api, _ = self._recording_api()

        assert getattr(api, 'get_non_banked_elsfp_%s' % family)()
        assert getattr(api, 'get_banked_elsfp_%s' % family)()


class TestIsCdbSupported:
    """The generic answer is the CMIS advertisement, as it is for a transceiver.

    NVIDIA's laser source is the exception and says so in its own class: it
    reports CDB_SUPPORT as 0 while answering the standard firmware commands.
    """

    @staticmethod
    def _generic_api(advertised):
        from sonic_platform_base.sonic_xcvr.api.public.elsfp import ElsfpApi

        api = ElsfpApi.__new__(ElsfpApi)
        api.xcvr_eeprom = MagicMock()
        api.xcvr_eeprom.read = MagicMock(return_value=advertised)
        return api

    @pytest.mark.parametrize("advertised, expected",
                             [(0, False), (1, True), (2, True), (3, False)])
    def test_the_advertisement_decides(self, advertised, expected):
        assert self._generic_api(advertised).is_cdb_supported() is expected

    def test_it_reads_the_cmis_advertisement_field(self):
        api = self._generic_api(1)
        api.is_cdb_supported()
        api.xcvr_eeprom.read.assert_called_once_with(consts.CDB_SUPPORT)

    def test_a_failed_read_is_not_a_no(self):
        """None rather than False, so the cache re-reads instead of pinning a
        refusal that was only a read failure."""
        assert self._generic_api(None).is_cdb_supported() is None

    def test_the_answer_is_cached(self):
        api = self._generic_api(1)
        assert api.is_cdb_supported() is True
        assert api.is_cdb_supported() is True
        assert api.xcvr_eeprom.read.call_count == 1

    def test_a_failed_read_is_not_cached(self):
        api = self._generic_api(None)
        api.is_cdb_supported()
        api.is_cdb_supported()
        assert api.xcvr_eeprom.read.call_count == 2

    def test_the_nvidia_laser_source_overrides_its_own_advertisement(self):
        api = _new_els_api_stub()
        api.xcvr_eeprom.read = MagicMock(return_value=0)

        assert api.is_cdb_supported() is True
        api.xcvr_eeprom.read.assert_not_called()


def _patterned_api(bank=0):
    """An api over a laser source whose every byte holds its own offset."""
    from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom

    mem_map = NvidiaCpoElsCmisMemMap(NvidiaCpoElsCodes, bank=bank)
    eeprom = XcvrEeprom(lambda offset, size: bytes((offset + i) & 0xFF for i in range(size)),
                        lambda offset, size, data: True, mem_map)
    return NvidiaCpoElsCmisApi(eeprom, init_cdb_fw_handler=False)


def _patterned_word(offset, signed):
    """The 16-bit value _patterned_api answers at offset."""
    return int.from_bytes(bytes([offset & 0xFF, (offset + 1) & 0xFF]), "big", signed=signed)


def _f3(value):
    return float("{:.3f}".format(value))


TEMPERATURE_FLAG_KEYS = ("temperature_alarm_high", "temperature_alarm_low",
                         "temperature_warn_high", "temperature_warn_low")


class TestTheTemperatureComesFromTheCustomMonitor:
    """NVIDIA's laser source keeps its temperature in the Custom Monitor slot:
    the value at page 00h byte 24, the thresholds at page 02h bytes 168-175 and
    the flags in the high nibble of byte 11. Its voltage thresholds are the
    page 02h ones too; the rest of the standard thresholds come from the B3
    mirror. Everything else in each table is ElsfpApi's."""

    def test_the_dom_temperature_is_the_custom_monitor_value(self):
        dom = _patterned_api().get_elsfp_dom_real_value()
        assert dom["temperature"] == _f3(_patterned_word(24, signed=True) / 256)

    def test_the_dom_voltage_stays_the_standard_one(self):
        dom = _patterned_api().get_elsfp_dom_real_value()
        assert dom["voltage"] == _f3(_patterned_word(16, signed=False) / 10000)

    @pytest.mark.parametrize("key, offset", [
        ("temperature_alarm_high", 168), ("temperature_alarm_low", 170),
        ("temperature_warn_high", 172), ("temperature_warn_low", 174)])
    def test_the_temperature_thresholds_are_the_custom_monitor_ones(self, key, offset):
        thresholds = _patterned_api().get_elsfp_threshold_info()
        assert thresholds[key] == _f3(_patterned_word(0x02 * 128 + offset, signed=True) / 256)

    @pytest.mark.parametrize("key, offset", [
        ("voltage_alarm_high", 136), ("voltage_alarm_low", 138),
        ("voltage_warn_high", 140), ("voltage_warn_low", 142)])
    def test_the_voltage_thresholds_are_the_page2_ones(self, key, offset):
        thresholds = _patterned_api().get_elsfp_threshold_info()
        assert thresholds[key] == _f3(_patterned_word(0x02 * 128 + offset, signed=False) / 10000)

    def test_the_standard_power_and_bias_thresholds_are_not_published(self):
        """The laser source leaves the standard rx/tx power and tx bias slots
        unset, which read as -inf dBm and 0 mA; its own are the page 1Ah ones."""
        thresholds = _patterned_api().get_elsfp_threshold_info()
        assert not [key for key in thresholds
                    if key.startswith(("rxpower", "txpower", "txbias"))]
        for key in ("optical_power_alarm_high", "optical_power_alarm_low",
                    "optical_power_warn_high", "optical_power_warn_low",
                    "laser_bias_alarm_high", "laser_bias_alarm_low",
                    "laser_bias_warn_high", "laser_bias_warn_low"):
            assert key in thresholds

    def test_page2_is_read_only_for_the_voltage_and_custom_monitor(self):
        """The rest of the standard thresholds come from the B3 mirror; page 02h
        is not the laser source's apart from those two groups."""
        api = _patterned_api()
        reads = []
        reader = api.xcvr_eeprom.reader
        api.xcvr_eeprom.reader = lambda offset, size: reads.append((offset, size)) or reader(offset, size)

        api.get_elsfp_threshold_info()

        def touched(page):
            return {o for offset, size in reads for o in range(offset, offset + size)
                    if page * 128 + 128 <= o < page * 128 + 256}
        assert touched(0x02) == {0x02 * 128 + b for b in list(range(136, 144)) + list(range(168, 176))}
        assert touched(NVIDIA_ELS_THRESHOLDS_PAGE)

    @pytest.mark.parametrize("bit, key", list(zip(range(4, 8), TEMPERATURE_FLAG_KEYS)))
    def test_each_custom_monitor_flag_is_its_own_bit(self, bit, key):
        api = _patterned_api()
        read = api.xcvr_eeprom.read
        api.xcvr_eeprom.read = lambda field: {consts.MODULE_FLAG_BYTE1: 0,
                                              consts.MODULE_FLAG_BYTE3: 1 << bit}.get(field, read(field))

        flags = api.get_non_banked_elsfp_dom_flags()
        assert [name for name in TEMPERATURE_FLAG_KEYS if flags[name]] == [key]
        assert not any(value for name, value in flags.items() if name.startswith("voltage"))

    @pytest.mark.parametrize("field, getter", [
        (consts.MODULE_FLAG_BYTE3, "get_non_banked_elsfp_dom_flags"),
        (NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD, "get_elsfp_threshold_info"),
        (NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD, "get_elsfp_threshold_info")])
    def test_a_failed_custom_monitor_read_is_none(self, field, getter):
        """None rather than a table with the standard slot's temperature left in
        it, so the caller retries."""
        api = _patterned_api()
        read = api.xcvr_eeprom.read
        api.xcvr_eeprom.read = lambda f: None if f == field else read(f)

        assert getattr(api, getter)() is None


class TestTheFirmwareVersionsComeFromTheMirrors:
    """The laser source's own firmware revisions sit in its B0 and B2 mirrors of
    lower memory and page 01h, so they are read there and CDB is not involved."""

    def _api(self):
        from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom

        reads, writes = [], []

        def reader(offset, size):
            reads.append(offset)
            return bytes((offset + i) & 0xFF for i in range(size))

        def writer(offset, size, data):
            writes.append(offset)
            return True

        mem_map = NvidiaCpoElsCmisMemMap(NvidiaCpoElsCodes)
        api = NvidiaCpoElsCmisApi(XcvrEeprom(reader, writer, mem_map), init_cdb_fw_handler=False)
        api.get_module_fw_info = MagicMock()
        return api, reads, writes

    def test_the_versions_are_read_off_b0_and_b2(self):
        api, reads, _ = self._api()

        # Every byte of the patterned EEPROM holds its own offset.
        assert api.get_elsfp_info_firmware_versions() == {
            "active_firmware": "167.168", "inactive_firmware": "128.129"}
        assert {_page_of(offset) for offset in reads} == {
            NVIDIA_ELS_MODULE_STATUS_PAGE, NVIDIA_ELS_ADVERTISING_PAGE}

    def test_the_cdb_target_is_left_alone(self):
        api, _, writes = self._api()

        api.get_elsfp_info_firmware_versions()
        assert writes == []
        api.get_module_fw_info.assert_not_called()
