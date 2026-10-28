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

"""Tests for the NVIDIA CPO Optical Engine (OE) memmaps and API."""
import struct
from unittest.mock import MagicMock, patch

from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.cdb.nvidia.cpo_oe_codes import NvidiaCpoOeCdbCodes
from sonic_platform_base.sonic_xcvr.fields import cdb_consts
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_oe import NvidiaCpoOeMemMap
from sonic_platform_base.sonic_xcvr.cdb.nvidia.cpo_oe_memmap import (
    CDB_READ_OE_TELEMETRY_CMD,
    CDB_READ_OE_TELEMETRY_EPL_LEN,
    NUM_LANES,
    NVIDIA_CPO_OE_TELEMETRY_EXT_MASKS,
    NVIDIA_CPO_OE_TELEMETRY_REPLY,
    NVIDIA_CPO_OE_TLM_CAPABILITY,
    NVIDIA_CPO_OE_TLM_CAPABILITY_EXT,
    NVIDIA_CPO_OE_TLM_OE_SN,
    NVIDIA_CPO_OE_TLM_VALID_EXT,
    OE_SN_LEN,
    OE_TELEMETRY_REQUEST_BITS,
    NVIDIA_CPO_OE_TLM_LANE_BANK_ECHO,
    NVIDIA_CPO_OE_TLM_LAST_REASON_OPCODE,
    NVIDIA_CPO_OE_TLM_RX_HS_DATA_RATE,
    NVIDIA_CPO_OE_TLM_RX_PS_LANE_STATE,
    NVIDIA_CPO_OE_TLM_RX_PS_LANE_SUB_STATE,
    NVIDIA_CPO_OE_TLM_TX_HS_DATA_RATE,
    NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE,
    NVIDIA_CPO_OE_TLM_TX_PS_LANE_SUB_STATE,
    NVIDIA_CPO_OE_TLM_VALID,
    NVIDIA_CPO_OE_TLM_VER_MAJOR,
    NVIDIA_CPO_OE_TLM_VER_MINOR,
    NVIDIA_CPO_OE_TLM_VER_RC,
    OE_TELEMETRY_REQUEST_MASK_ALL,
    CdbReadOeTelemetry,
    NvidiaCpoOeCdbMemMap,
)
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_oe import (
    OE_TELEMETRY_FIRMWARE_REQUEST_MASK,
    OE_TELEMETRY_INFO_REQUEST_MASK,
    OE_TELEMETRY_STATUS_REQUEST_MASK,
    NvidiaCpoOeCmisApi,
)

OE_SN_REQUEST_BIT = OE_TELEMETRY_REQUEST_BITS[NVIDIA_CPO_OE_TLM_OE_SN]
from sonic_platform_base.sonic_xcvr.cpo.cmis import CpoCmisApi


def _epl_addr(byte_in_reply):
    return cdb_consts.EPL_PAGE * 128 + 128 + byte_in_reply


def _make_blank_reply():
    return bytearray(CDB_READ_OE_TELEMETRY_EPL_LEN)


def _new_oe_api_stub(cdb_handler=None, mem_map_bank=0):
    """Bypass NvidiaCpoOeCmisApi.__init__ and stick MagicMocks in place of EEPROM/CDB."""
    api = NvidiaCpoOeCmisApi.__new__(NvidiaCpoOeCmisApi)
    eeprom = MagicMock()
    eeprom.mem_map = MagicMock(bank=mem_map_bank)
    api.xcvr_eeprom = eeprom
    api._vendor_cdb_mem_map = MagicMock() if cdb_handler is not None else None
    api._vendor_cdb_handler = cdb_handler
    return api


class TestNvidiaCpoOeMemMap:
    def test_instantiates_with_default_bank(self):
        mm = NvidiaCpoOeMemMap(CmisCodes)
        assert mm.bank == 0

    def test_instantiates_with_explicit_bank(self):
        mm = NvidiaCpoOeMemMap(CmisCodes, bank=2)
        assert mm.bank == 2

    def test_inherits_standard_cmis_fields(self):
        mm = NvidiaCpoOeMemMap(CmisCodes)
        from sonic_platform_base.sonic_xcvr.fields import consts
        field = mm.get_field(consts.ADMIN_INFO_FIELD)
        assert field is not None


class TestCdbReadOeTelemetry:
    def test_init_defaults(self):
        cmd = CdbReadOeTelemetry()
        assert cmd.cmd_id == CDB_READ_OE_TELEMETRY_CMD
        assert cmd.epl == 0
        assert cmd.lpl == 6
        assert cmd.rpl_field == NVIDIA_CPO_OE_TELEMETRY_REPLY

    def test_encode_packs_payload_dict_into_6_byte_lpl(self):
        cmd = CdbReadOeTelemetry()
        encoded = cmd.encode({"bank_id": 0x02, "request_mask": 0x000003F0})

        # CDBCommand.encode prepends an 8-byte header (id|epl|lpl|cksum|rpl).
        assert encoded[:2] == b"\x90\x30"
        assert struct.unpack(">H", encoded[2:4])[0] == 0   # request sends no EPL data
        assert encoded[4] == 6             # lpl byte
        # LPL payload starts at byte 8: lane bank, then the 5-byte request mask.
        assert encoded[8] == 0x02
        assert encoded[9:14] == bytes.fromhex("00000003f0")
        assert len(encoded) == 14

    def test_encode_matches_the_request_the_firmware_accepts(self):
        # Bytes 128-141 of page 9Fh for the request firmware answered with
        # status 0x01 on hardware (bank 0, all advertised caps).
        cmd = CdbReadOeTelemetry()
        encoded = cmd.encode({"bank_id": 0, "request_mask": 0x00003C03F0})
        assert encoded.hex() == "90300000060a0000" + "00" + "00003c03f0"

    def test_encode_default_request_adds_oe_sn_to_the_accepted_request(self):
        cmd = CdbReadOeTelemetry()
        encoded = cmd.encode({"bank_id": 0})
        assert encoded[9:14] == bytes.fromhex("08003c03f0")

    def test_encode_defaults_request_mask_to_all(self):
        cmd = CdbReadOeTelemetry()
        encoded = cmd.encode({"bank_id": 1})
        assert encoded[8] == 1
        assert int.from_bytes(encoded[9:14], "big") == OE_TELEMETRY_REQUEST_MASK_ALL

    def test_encode_defaults_bank_id_to_zero(self):
        cmd = CdbReadOeTelemetry()
        encoded = cmd.encode({"request_mask": 0x12345678})
        assert encoded[8] == 0
        assert int.from_bytes(encoded[9:14], "big") == 0x12345678

    def test_request_mask_all_covers_all_advertised_caps(self):
        for bit in (4, 5, 6, 7, 8, 9, 18, 19, 20, 21):
            assert OE_TELEMETRY_REQUEST_MASK_ALL & (1 << bit), \
                "cap bit %d should be in OE_TELEMETRY_REQUEST_MASK_ALL" % bit

    def test_request_mask_all_requests_oe_sn(self):
        assert OE_TELEMETRY_REQUEST_MASK_ALL & (1 << OE_SN_REQUEST_BIT)

    def test_encode_places_oe_sn_request_bit_in_the_5_byte_mask(self):
        cmd = CdbReadOeTelemetry()
        encoded = cmd.encode({"bank_id": 0, "request_mask": 1 << OE_SN_REQUEST_BIT})
        assert encoded[9:14] == bytes.fromhex("0800000000")


class TestNvidiaCpoOeCdbMemMap:
    def setup_method(self):
        self.mm = NvidiaCpoOeCdbMemMap(NvidiaCpoOeCdbCodes)

    def test_inherits_standard_cdb_commands(self):
        from sonic_platform_base.sonic_xcvr.fields import cdb_consts as cc
        assert self.mm.get_cdb_cmd(cc.CDB_QUERY_STATUS_CMD) is not None
        assert self.mm.get_cdb_cmd(cc.CDB_GET_FIRMWARE_INFO_CMD) is not None

    def test_registers_oe_telemetry_command(self):
        cmd = self.mm.get_cdb_cmd(CDB_READ_OE_TELEMETRY_CMD)
        assert cmd is not None
        assert isinstance(cmd, CdbReadOeTelemetry)
        assert cmd.get_reply_field() == NVIDIA_CPO_OE_TELEMETRY_REPLY

    def test_telemetry_reply_field_is_registered(self):
        rg = self.mm.get_field(NVIDIA_CPO_OE_TELEMETRY_REPLY)
        assert rg is not None
        assert rg.get_offset() == _epl_addr(0)
        # Last field is VER_RC (2 bytes at offset 166).
        assert rg.get_size() == 168

    def test_telemetry_reply_decode_full(self):
        reply = _make_blank_reply()

        struct.pack_into(">I", reply, 0,  0xFFFFFFFF)
        struct.pack_into(">I", reply, 4,  0xFFFFFFFF)
        reply[8] = 0x07

        # Per-lane state nibbles (4 bits per lane): even lane in bits 0..3,
        # odd lane in bits 4..7. Lanes 0..7 carry values 1..8.
        # Pack [1,2,3,4,5,6,7,8] -> bytes [0x21, 0x43, 0x65, 0x87].
        reply[43:47] = bytes([0x21, 0x43, 0x65, 0x87])  # tx_ps_lane_state
        reply[47:51] = bytes([0x21, 0x43, 0x65, 0x87])  # rx_ps_lane_state

        for lane in range(NUM_LANES):
            struct.pack_into(">H", reply, 51 + lane * 2, 0x0100 + lane)
            struct.pack_into(">H", reply, 67 + lane * 2, 0x0200 + lane)

        # 3-bit RegBitsField: lanes 0..7 carry values 0..7 -> [0x10, 0x32, 0x54, 0x76].
        reply[83:87] = bytes([0x10, 0x32, 0x54, 0x76])
        reply[87:91] = bytes([0x10, 0x32, 0x54, 0x76])

        reply[154:162] = bytes(range(8))

        struct.pack_into(">H", reply, 162, 0x0102)
        struct.pack_into(">H", reply, 164, 0x0304)
        struct.pack_into(">H", reply, 166, 0x0506)

        rg = self.mm.get_field(NVIDIA_CPO_OE_TELEMETRY_REPLY)
        decoded = rg.decode(bytes(reply))

        assert decoded[NVIDIA_CPO_OE_TLM_CAPABILITY] == 0xFFFFFFFF
        assert decoded[NVIDIA_CPO_OE_TLM_VALID] == 0xFFFFFFFF
        assert decoded[NVIDIA_CPO_OE_TLM_LANE_BANK_ECHO] == 0x07

        for lane in range(NUM_LANES):
            byte_idx = lane // 2
            for prefix, expected in (
                (NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE, lane + 1),
                (NVIDIA_CPO_OE_TLM_RX_PS_LANE_STATE, lane + 1),
                (NVIDIA_CPO_OE_TLM_TX_HS_DATA_RATE, lane),
                (NVIDIA_CPO_OE_TLM_RX_HS_DATA_RATE, lane),
            ):
                parent_key = "%s_byte%d" % (prefix, byte_idx)
                lane_key = "%s_%d" % (prefix, lane)
                assert decoded[parent_key][lane_key] == expected, \
                    "%s lane %d: expected %d, got %r" % (
                        prefix, lane, expected, decoded[parent_key][lane_key])

            assert decoded["%s_%d" % (NVIDIA_CPO_OE_TLM_TX_PS_LANE_SUB_STATE, lane)] == 0x0100 + lane
            assert decoded["%s_%d" % (NVIDIA_CPO_OE_TLM_RX_PS_LANE_SUB_STATE, lane)] == 0x0200 + lane
            assert decoded["%s_%d" % (NVIDIA_CPO_OE_TLM_LAST_REASON_OPCODE, lane)] == lane

        assert decoded[NVIDIA_CPO_OE_TLM_VER_MAJOR] == 0x0102
        assert decoded[NVIDIA_CPO_OE_TLM_VER_MINOR] == 0x0304
        assert decoded[NVIDIA_CPO_OE_TLM_VER_RC] == 0x0506

    def test_telemetry_reply_excludes_oe_sn_and_ext_masks(self):
        rg = self.mm.get_field(NVIDIA_CPO_OE_TELEMETRY_REPLY)
        names = set(rg.get_fields())
        for name in (NVIDIA_CPO_OE_TLM_OE_SN, NVIDIA_CPO_OE_TLM_CAPABILITY_EXT,
                     NVIDIA_CPO_OE_TLM_VALID_EXT):
            assert name not in names

    def test_oe_sn_field_is_at_page_a1_byte_168(self):
        field = self.mm.get_field(NVIDIA_CPO_OE_TLM_OE_SN)
        assert field.get_offset() == (cdb_consts.EPL_PAGE + 1) * 128 + 168
        assert field.get_size() == OE_SN_LEN
        serial = b"MT2420XZ0ABC-OE01".ljust(OE_SN_LEN, b"\x00")
        assert field.decode(serial) == serial.decode("ascii")

    def test_ext_masks_are_at_page_a2_bytes_190_to_193(self):
        rg = self.mm.get_field(NVIDIA_CPO_OE_TELEMETRY_EXT_MASKS)
        assert rg.get_offset() == (cdb_consts.EPL_PAGE + 2) * 128 + 190
        assert rg.get_size() == 4
        decoded = rg.decode(bytes([0x00, 0x08, 0x00, 0x18]))
        assert decoded == {NVIDIA_CPO_OE_TLM_CAPABILITY_EXT: 0x0008,
                           NVIDIA_CPO_OE_TLM_VALID_EXT: 0x0018}



def _decoded_reply(capability=0xFFFFFFFF, valid=0xFFFFFFFF):
    """A 0x9030 reply decoded through the real memmap: lanes 0..7 carry
    1..8 power states, 0x0100+lane/0x0200+lane sub-states, data rate and
    last reason opcode lane; firmware version 0.8.0."""
    reply = _make_blank_reply()
    struct.pack_into(">I", reply, 0, capability)
    struct.pack_into(">I", reply, 4, valid)
    reply[43:47] = bytes([0x21, 0x43, 0x65, 0x87])
    reply[47:51] = bytes([0x21, 0x43, 0x65, 0x87])
    for lane in range(NUM_LANES):
        struct.pack_into(">H", reply, 51 + lane * 2, 0x0100 + lane)
        struct.pack_into(">H", reply, 67 + lane * 2, 0x0200 + lane)
    reply[83:87] = bytes([0x10, 0x32, 0x54, 0x76])
    reply[87:91] = bytes([0x10, 0x32, 0x54, 0x76])
    reply[154:162] = bytes(range(8))
    struct.pack_into(">HHH", reply, 162, 0, 8, 0)
    rg = NvidiaCpoOeCdbMemMap(NvidiaCpoOeCdbCodes).get_field(NVIDIA_CPO_OE_TELEMETRY_REPLY)
    return rg.decode(bytes(reply))


SN_EXT_BIT = 1 << (OE_SN_REQUEST_BIT - 32)


def _api_with_reply(capability=0xFFFFFFFF, valid=0xFFFFFFFF, cap_ext=SN_EXT_BIT,
                    valid_ext=SN_EXT_BIT, oe_sn="MT2420XZ0ABC\x00\x00  ", ext_masks_missing=False,
                    mem_map_bank=0):
    """An OE API whose CDB answers 0x9030 with _decoded_reply() and serves the
    extended masks and the serial number on their own reads."""
    cdb = MagicMock()
    cdb.send_cmd.return_value = True
    cdb.read_reply.return_value = _decoded_reply(capability, valid)
    fields = {
        NVIDIA_CPO_OE_TELEMETRY_EXT_MASKS: None if ext_masks_missing else {
            NVIDIA_CPO_OE_TLM_CAPABILITY_EXT: cap_ext,
            NVIDIA_CPO_OE_TLM_VALID_EXT: valid_ext,
        },
        NVIDIA_CPO_OE_TLM_OE_SN: oe_sn,
    }
    cdb.read.side_effect = fields.get
    return _new_oe_api_stub(cdb_handler=cdb, mem_map_bank=mem_map_bank), cdb


def _lane_keys(*prefixes):
    return {"%s_%d" % (prefix, lane) for prefix in prefixes for lane in range(NUM_LANES)}


STATUS_PREFIXES = (
    NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE, NVIDIA_CPO_OE_TLM_RX_PS_LANE_STATE,
    NVIDIA_CPO_OE_TLM_TX_PS_LANE_SUB_STATE, NVIDIA_CPO_OE_TLM_RX_PS_LANE_SUB_STATE,
    NVIDIA_CPO_OE_TLM_TX_HS_DATA_RATE, NVIDIA_CPO_OE_TLM_RX_HS_DATA_RATE,
    NVIDIA_CPO_OE_TLM_LAST_REASON_OPCODE,
)

# Capability and valid masks reported by OE firmware 0.8.0 on sws-cham6s-20.
HW_CAPABILITY = 0xFFFBFFFD
HW_VALID = 0x003803F0


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


class TestGetOeTelemetry:
    def test_returns_none_when_no_cdb_handler(self):
        api = _new_oe_api_stub(cdb_handler=None)
        assert api.get_oe_telemetry() is None

    def test_returns_none_when_send_returns_false(self):
        api, cdb = _api_with_reply()
        cdb.send_cmd.return_value = False
        assert api.get_oe_telemetry() is None
        assert not cdb.read_reply.called

    def test_returns_none_when_send_raises(self):
        api, cdb = _api_with_reply()
        cdb.send_cmd.side_effect = RuntimeError("boom")
        assert api.get_oe_telemetry() is None

    def test_command_and_reply_hold_the_cdb_lock(self):
        api, cdb = _api_with_reply()
        events = []
        api.cdb_lock = recording_lock(events)
        reply = cdb.read_reply.return_value
        read = cdb.read.side_effect
        cdb.send_cmd.side_effect = lambda *args, **kwargs: events.append('send') or True
        cdb.read_reply.side_effect = lambda *args: events.append('reply') or reply
        cdb.read.side_effect = lambda name: events.append('read') or read(name)

        assert api.get_oe_telemetry() is not None

        # The extended masks and the serial number are read from the reply
        # pages after the reply, so the lock is not released in between: it is
        # held from the command to the last read. Each handler call also takes
        # the (reentrant) lock again to select the CDB target.
        assert events[:7] == ['lock', 'lock', 'send', 'unlock', 'lock', 'reply', 'unlock']
        assert 'read' in events
        depth = 0
        for index, event in enumerate(events):
            depth += {'lock': 1, 'unlock': -1}.get(event, 0)
            assert depth > 0 or index == len(events) - 1, events
        assert depth == 0

    def test_returns_none_when_read_reply_raises(self):
        api, cdb = _api_with_reply()
        cdb.read_reply.side_effect = RuntimeError("bad reply")
        assert api.get_oe_telemetry() is None

    def test_returns_none_when_read_reply_is_none(self):
        api, cdb = _api_with_reply()
        cdb.read_reply.return_value = None
        assert api.get_oe_telemetry() is None

    def test_send_cmd_invoked_with_payload_dict(self):
        api, cdb = _api_with_reply(mem_map_bank=2)
        api.get_oe_telemetry()
        args, kwargs = cdb.send_cmd.call_args
        assert args[0] == CDB_READ_OE_TELEMETRY_CMD
        assert kwargs["payload"] == {"bank_id": 2, "request_mask": OE_TELEMETRY_REQUEST_MASK_ALL}

    def test_caller_can_override_request_mask(self):
        api, cdb = _api_with_reply(mem_map_bank=1)
        api.get_oe_telemetry(request_mask=0x000000F0)
        assert cdb.send_cmd.call_args[1]["payload"] == {"bank_id": 1, "request_mask": 0x000000F0}

    def test_read_reply_invoked_with_cmd_id(self):
        api, cdb = _api_with_reply()
        api.get_oe_telemetry()
        assert cdb.read_reply.call_args[0][0] == CDB_READ_OE_TELEMETRY_CMD

    def test_returns_all_fields_flat_without_framing(self):
        api, _ = _api_with_reply()
        out = api.get_oe_telemetry()
        assert set(out) == _lane_keys(*STATUS_PREFIXES) | {
            NVIDIA_CPO_OE_TLM_VER_MAJOR, NVIDIA_CPO_OE_TLM_VER_MINOR, NVIDIA_CPO_OE_TLM_VER_RC,
            NVIDIA_CPO_OE_TLM_OE_SN}
        assert out["%s_3" % NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE] == 4
        assert out["%s_3" % NVIDIA_CPO_OE_TLM_RX_HS_DATA_RATE] == 3
        assert out[NVIDIA_CPO_OE_TLM_VER_MINOR] == 8

    def test_returns_only_requested_fields(self):
        api, _ = _api_with_reply()
        out = api.get_oe_telemetry(request_mask=OE_TELEMETRY_FIRMWARE_REQUEST_MASK)
        assert out == {NVIDIA_CPO_OE_TLM_VER_MAJOR: 0, NVIDIA_CPO_OE_TLM_VER_MINOR: 8,
                       NVIDIA_CPO_OE_TLM_VER_RC: 0}

    def test_field_na_unless_supported_and_valid(self):
        # Firmware 0.8.0 flags bits 4-9 and 19-21 but not bit 18.
        api, _ = _api_with_reply(capability=HW_CAPABILITY, valid=HW_VALID)
        out = api.get_oe_telemetry()
        for lane in range(NUM_LANES):
            assert out["%s_%d" % (NVIDIA_CPO_OE_TLM_LAST_REASON_OPCODE, lane)] == "N/A"
            assert out["%s_%d" % (NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE, lane)] == lane + 1
        assert out[NVIDIA_CPO_OE_TLM_VER_MINOR] == 8

    def test_field_na_when_supported_but_not_valid(self):
        api, _ = _api_with_reply(valid=0xFFFFFFFF & ~(1 << 4))
        out = api.get_oe_telemetry()
        assert out["%s_0" % NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE] == "N/A"
        assert out["%s_0" % NVIDIA_CPO_OE_TLM_RX_PS_LANE_STATE] == 1

    def test_field_na_when_valid_but_not_supported(self):
        api, _ = _api_with_reply(capability=0xFFFFFFFF & ~(1 << 19))
        assert api.get_oe_telemetry()[NVIDIA_CPO_OE_TLM_VER_MAJOR] == "N/A"

    def test_ext_masks_not_read_without_a_request_bit_above_31(self):
        api, cdb = _api_with_reply()
        api.get_oe_telemetry(request_mask=OE_TELEMETRY_STATUS_REQUEST_MASK)
        assert not cdb.read.called


class TestGetOeTelemetryOeSn:
    def test_not_read_unless_requested(self):
        api, cdb = _api_with_reply()
        out = api.get_oe_telemetry(request_mask=OE_TELEMETRY_REQUEST_MASK_ALL & ~OE_TELEMETRY_INFO_REQUEST_MASK)
        assert NVIDIA_CPO_OE_TLM_OE_SN not in out
        assert not cdb.read.called

    def test_stripped_when_supported_and_valid(self):
        api, _ = _api_with_reply()
        assert api.get_oe_telemetry()[NVIDIA_CPO_OE_TLM_OE_SN] == "MT2420XZ0ABC"

    def test_gated_on_the_extended_masks(self):
        # Bit 3 of the main masks is a different field (RX_CAL_VOAY_PMIR).
        api, _ = _api_with_reply(cap_ext=0, valid_ext=0)
        assert api.get_oe_telemetry()[NVIDIA_CPO_OE_TLM_OE_SN] == "N/A"

    def test_na_when_not_supported(self):
        api, cdb = _api_with_reply(cap_ext=0)
        assert api.get_oe_telemetry()[NVIDIA_CPO_OE_TLM_OE_SN] == "N/A"
        assert NVIDIA_CPO_OE_TLM_OE_SN not in [c[0][0] for c in cdb.read.call_args_list]

    def test_na_when_not_valid(self):
        api, _ = _api_with_reply(valid_ext=0)
        assert api.get_oe_telemetry()[NVIDIA_CPO_OE_TLM_OE_SN] == "N/A"

    def test_na_when_ext_masks_read_fails(self):
        api, _ = _api_with_reply(ext_masks_missing=True)
        assert api.get_oe_telemetry()[NVIDIA_CPO_OE_TLM_OE_SN] == "N/A"

    def test_na_when_reads_raise(self):
        api, cdb = _api_with_reply()
        cdb.read.side_effect = RuntimeError("i2c")
        out = api.get_oe_telemetry()
        assert out[NVIDIA_CPO_OE_TLM_OE_SN] == "N/A"
        assert out[NVIDIA_CPO_OE_TLM_VER_MINOR] == 8

    def test_na_when_serial_read_raises(self):
        api, cdb = _api_with_reply()
        ext_masks = {NVIDIA_CPO_OE_TLM_CAPABILITY_EXT: SN_EXT_BIT, NVIDIA_CPO_OE_TLM_VALID_EXT: SN_EXT_BIT}

        def read(name):
            if name == NVIDIA_CPO_OE_TLM_OE_SN:
                raise RuntimeError("i2c")
            return ext_masks
        cdb.read.side_effect = read
        assert api.get_oe_telemetry()[NVIDIA_CPO_OE_TLM_OE_SN] == "N/A"

    def test_na_when_serial_is_all_padding(self):
        api, _ = _api_with_reply(oe_sn="\x00" * OE_SN_LEN)
        assert api.get_oe_telemetry()[NVIDIA_CPO_OE_TLM_OE_SN] == "N/A"


class TestOeTelemetryRequestMasks:
    MASKS = (OE_TELEMETRY_INFO_REQUEST_MASK, OE_TELEMETRY_FIRMWARE_REQUEST_MASK,
             OE_TELEMETRY_STATUS_REQUEST_MASK)

    def test_info_mask_requests_oe_sn_only(self):
        assert OE_TELEMETRY_INFO_REQUEST_MASK.to_bytes(5, "big") == bytes.fromhex("0800000000")

    def test_firmware_mask_requests_version_only(self):
        assert OE_TELEMETRY_FIRMWARE_REQUEST_MASK.to_bytes(5, "big") == bytes.fromhex("0000380000")

    def test_status_mask_requests_lane_fields_only(self):
        assert OE_TELEMETRY_STATUS_REQUEST_MASK.to_bytes(5, "big") == bytes.fromhex("00000403f0")

    def test_masks_split_the_full_request(self):
        for i, mask in enumerate(self.MASKS):
            for other in self.MASKS[i + 1:]:
                assert mask & other == 0
        assert self.MASKS[0] | self.MASKS[1] | self.MASKS[2] == OE_TELEMETRY_REQUEST_MASK_ALL


class TestOeTelemetryInfoFirmwareAndStatus:
    """The 0x9030 fields split into info, firmware info and per-lane status."""

    def test_info_requests_oe_sn(self):
        api, cdb = _api_with_reply()
        api.get_oe_telemetry_info()
        assert cdb.send_cmd.call_args[1]["payload"]["request_mask"] == OE_TELEMETRY_INFO_REQUEST_MASK

    def test_info_holds_oe_sn_only(self):
        api, _ = _api_with_reply()
        assert api.get_oe_telemetry_info() == {"oe_sn": "MT2420XZ0ABC"}

    def test_info_na_when_telemetry_unavailable(self):
        api, cdb = _api_with_reply()
        cdb.send_cmd.return_value = False
        assert api.get_oe_telemetry_info() == {"oe_sn": "N/A"}

    def test_firmware_versions_request_the_version(self):
        api, cdb = _api_with_reply()
        api.get_oe_telemetry_firmware_versions()
        assert cdb.send_cmd.call_args[1]["payload"]["request_mask"] == OE_TELEMETRY_FIRMWARE_REQUEST_MASK

    def test_firmware_versions_hold_the_version_only(self):
        api, _ = _api_with_reply()
        assert api.get_oe_telemetry_firmware_versions() == {
            "oe_ver_major": 0, "oe_ver_minor": 8, "oe_ver_rc": 0}

    def test_firmware_versions_na_when_telemetry_unavailable(self):
        api, cdb = _api_with_reply()
        cdb.send_cmd.return_value = False
        assert api.get_oe_telemetry_firmware_versions() == dict.fromkeys(
            ("oe_ver_major", "oe_ver_minor", "oe_ver_rc"), "N/A")

    def test_status_requests_the_lane_fields(self):
        api, cdb = _api_with_reply()
        api.get_oe_telemetry_status()
        assert cdb.send_cmd.call_args[1]["payload"]["request_mask"] == OE_TELEMETRY_STATUS_REQUEST_MASK

    def test_status_uses_spec_names_with_bank_relative_lanes(self):
        api, _ = _api_with_reply()
        out = api.get_oe_telemetry_status()
        for lane in range(NUM_LANES):
            assert out["oe_tx_ps_state_lane%d" % lane] == lane + 1
            assert out["oe_rx_ps_state_lane%d" % lane] == lane + 1
            assert out["oe_tx_ps_sub_lane%d" % lane] == 0x0100 + lane
            assert out["oe_rx_ps_sub_lane%d" % lane] == 0x0200 + lane
            assert out["oe_tx_hs_data_lane%d" % lane] == lane
            assert out["oe_rx_hs_data_lane%d" % lane] == lane
            assert out["oe_last_reason_opcode_lane%d" % lane] == lane
        assert len(out) == 7 * NUM_LANES

    def test_status_na_for_fields_the_oe_does_not_flag(self):
        api, _ = _api_with_reply(capability=HW_CAPABILITY, valid=HW_VALID)
        out = api.get_oe_telemetry_status()
        assert out["oe_last_reason_opcode_lane0"] == "N/A"
        assert out["oe_tx_ps_state_lane0"] == 1

    def test_status_na_when_telemetry_unavailable(self):
        api, cdb = _api_with_reply()
        cdb.send_cmd.return_value = False
        out = api.get_oe_telemetry_status()
        assert len(out) == 7 * NUM_LANES
        assert set(out.values()) == {"N/A"}


class TestOeTelemetryPublishing:

    def test_transceiver_info_adds_oe_sn(self):
        api = _new_oe_api_stub()
        api.get_oe_telemetry_info = MagicMock(return_value={"oe_sn": "N/A"})
        with patch.object(CmisApi, "get_transceiver_info", return_value={"serial": "SN1"}):
            assert api.get_transceiver_info() == {"serial": "SN1", "oe_sn": "N/A"}

    def test_firmware_info_adds_oe_version(self):
        api = _new_oe_api_stub()
        api.get_oe_telemetry_firmware_versions = MagicMock(
            return_value={"oe_ver_major": 0, "oe_ver_minor": 8, "oe_ver_rc": 0})
        with patch.object(CmisApi, "get_transceiver_info_firmware_versions",
                          return_value={"active_firmware": "1.2.3", "inactive_firmware": "N/A"}):
            assert api.get_transceiver_info_firmware_versions() == {
                "active_firmware": "1.2.3", "inactive_firmware": "N/A",
                "oe_ver_major": 0, "oe_ver_minor": 8, "oe_ver_rc": 0,
            }

    def test_transceiver_info_none_when_eeprom_not_ready(self):
        api = _new_oe_api_stub()
        api.get_oe_telemetry_info = MagicMock()
        with patch.object(CmisApi, "get_transceiver_info", return_value=None):
            assert api.get_transceiver_info() is None
        api.get_oe_telemetry_info.assert_not_called()

    def test_banked_status_adds_dynamic_oe_telemetry(self):
        api = _new_oe_api_stub()
        api.get_oe_telemetry_status = MagicMock(return_value={"oe_tx_ps_state_lane0": 5})
        with patch.object(CpoCmisApi, "get_banked_transceiver_status",
                          return_value={"DP1State": "DataPathActivated"}):
            assert api.get_banked_transceiver_status() == {
                "DP1State": "DataPathActivated", "oe_tx_ps_state_lane0": 5,
            }

    def test_vdm_real_values_carry_no_oe_telemetry(self):
        api = _new_oe_api_stub()
        api.get_oe_telemetry = MagicMock()
        with patch.object(CmisApi, "get_transceiver_vdm_real_value_basic",
                          return_value={"Laser Temperature [C]": 45.5}):
            assert api.get_transceiver_vdm_real_value_basic() == {"Laser Temperature [C]": 45.5}
        api.get_oe_telemetry.assert_not_called()


class TestUnsupportedLegacyDomFields:

    def test_laser_temperature_is_unsupported(self):
        api = _new_oe_api_stub()
        assert api.get_laser_temperature() == {
            'monitor value': 'N/A', 'high alarm': 'N/A', 'low alarm': 'N/A',
            'high warn': 'N/A', 'low warn': 'N/A',
        }
        api.xcvr_eeprom.read.assert_not_called()

    def test_non_banked_dom_real_value_has_no_laser_temperature(self):
        api = _new_oe_api_stub()
        api.get_module_temperature = MagicMock(return_value=45.0)
        api.get_voltage = MagicMock(return_value=3.3)
        assert api.get_non_banked_transceiver_dom_real_value() == {
            "temperature": 45.0,
            "voltage": 3.3,
        }

    def test_non_banked_dom_real_value_none_when_temp_unreadable(self):
        api = _new_oe_api_stub()
        api.get_module_temperature = MagicMock(return_value=None)
        api.get_voltage = MagicMock(return_value=3.3)
        assert api.get_non_banked_transceiver_dom_real_value() is None

    def test_tx_bias_is_unsupported(self):
        api = _new_oe_api_stub()
        assert api.get_tx_bias_support() is False
        assert api.get_tx_bias() == ['N/A'] * api.NUM_CHANNELS
        api.xcvr_eeprom.read.assert_not_called()

    def test_banked_dom_real_value_has_power_and_no_tx_bias(self):
        api = _new_oe_api_stub()
        api.get_rx_power = MagicMock(return_value=[1.0] * api.NUM_CHANNELS)
        api.get_tx_power = MagicMock(return_value=['N/A'] * api.NUM_CHANNELS)
        out = api.get_banked_transceiver_dom_real_value()
        api.xcvr_eeprom.read.assert_not_called()
        assert set(out) == {"%s%dpower" % (d, i) for d in ("rx", "tx")
                            for i in range(1, api.NUM_CHANNELS + 1)}
        assert out["rx1power"] == 0.0
        assert out["tx1power"] == 'N/A'

    def test_banked_dom_real_value_none_when_power_unreadable(self):
        api = _new_oe_api_stub()
        api.get_rx_power = MagicMock(return_value=None)
        api.get_tx_power = MagicMock(return_value=[1.0] * api.NUM_CHANNELS)
        assert api.get_banked_transceiver_dom_real_value() is None

    def test_non_banked_dom_flags_drop_laser_temperature(self):
        api = _new_oe_api_stub()
        with patch.object(CpoCmisApi, "get_non_banked_transceiver_dom_flags",
                          return_value={"tempHAlarm": False, "lasertempHAlarm": False,
                                        "lasertempLAlarm": False, "lasertempHWarn": False,
                                        "lasertempLWarn": False}):
            assert api.get_non_banked_transceiver_dom_flags() == {"tempHAlarm": False}

    def test_banked_dom_flags_drop_tx_bias(self):
        api = _new_oe_api_stub()
        flags = {}
        for lane in range(1, api.NUM_CHANNELS + 1):
            for kind in ("HAlarm", "LAlarm", "HWarn", "LWarn"):
                flags["tx%dbias%s" % (lane, kind)] = False
                flags["tx%dpower%s" % (lane, kind)] = False
                flags["rx%dpower%s" % (lane, kind)] = False
        with patch.object(CpoCmisApi, "get_banked_transceiver_dom_flags", return_value=flags):
            out = api.get_banked_transceiver_dom_flags()
        assert out
        assert not any("bias" in key for key in out)
        assert len(out) == 2 * 4 * api.NUM_CHANNELS

    def test_threshold_info_drops_laser_temperature_and_tx_bias(self):
        api = _new_oe_api_stub()
        thresholds = {
            "temphighalarm": 80.0, "rxpowerhighalarm": 3.0,
            "lasertemphighalarm": 0.0, "lasertemplowalarm": 0.0,
            "lasertemphighwarning": 0.0, "lasertemplowwarning": 0.0,
            "txbiashighalarm": 0.0, "txbiaslowalarm": 0.0,
            "txbiashighwarning": 0.0, "txbiaslowwarning": 0.0,
        }
        with patch.object(CmisApi, "get_transceiver_threshold_info", return_value=thresholds):
            assert api.get_transceiver_threshold_info() == {
                "temphighalarm": 80.0, "rxpowerhighalarm": 3.0,
            }

    def test_banked_status_drops_rx_output_status(self):
        api = _new_oe_api_stub()
        api.get_oe_telemetry_status = MagicMock(return_value={})
        status = {"DP1State": "DataPathActivated", "tx1OutputStatus": True}
        for lane in range(1, api.NUM_CHANNELS + 1):
            status["rx%dOutputStatusHostlane" % lane] = False
        with patch.object(CpoCmisApi, "get_banked_transceiver_status", return_value=status):
            assert api.get_banked_transceiver_status() == {
                "DP1State": "DataPathActivated", "tx1OutputStatus": True,
            }

    def test_banked_status_flags_drop_cdr_lol_and_eq_fault(self):
        api = _new_oe_api_stub()
        flags = {}
        for lane in range(1, api.NUM_CHANNELS + 1):
            flags.update({
                "tx%dfault" % lane: False, "rx%dlos" % lane: False, "tx%dlos_hostlane" % lane: False,
                "tx%dcdrlol_hostlane" % lane: "N/A", "tx%d_eq_fault" % lane: "N/A", "rx%dcdrlol" % lane: "N/A",
            })
        with patch.object(CpoCmisApi, "get_banked_transceiver_status_flags", return_value=flags):
            out = api.get_banked_transceiver_status_flags()
        assert len(out) == 3 * api.NUM_CHANNELS
        assert not any("cdrlol" in key or "eq_fault" in key for key in out)

    def test_threshold_info_passes_through_none(self):
        api = _new_oe_api_stub()
        with patch.object(CmisApi, "get_transceiver_threshold_info", return_value=None):
            assert api.get_transceiver_threshold_info() is None


def test_factory_style_instantiation():
    """End-to-end: build the OE memmap + CDB memmap + API the same way the factory does."""
    from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom

    reader = MagicMock(return_value=b"\x00")
    writer = MagicMock(return_value=True)

    mm = NvidiaCpoOeMemMap(CmisCodes, bank=1)
    eeprom = XcvrEeprom(reader, writer, mm)
    cdb_mm = NvidiaCpoOeCdbMemMap(NvidiaCpoOeCdbCodes)
    api = NvidiaCpoOeCmisApi(eeprom, cdb_mem_map=cdb_mm)

    assert api.cdb_handler is not None
    assert api.cdb_handler.mem_map is cdb_mm
    assert api._get_bank_id() == 1
