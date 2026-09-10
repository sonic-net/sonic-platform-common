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
    NVIDIA_CPO_OE_TELEMETRY_REPLY,
    NVIDIA_CPO_OE_TLM_CAPABILITY,
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
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_oe import NvidiaCpoOeCmisApi


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
    api._cdb_mem_map = MagicMock() if cdb_handler is not None else None
    api._cdb_handler = cdb_handler
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
        assert cmd.epl == CDB_READ_OE_TELEMETRY_EPL_LEN
        assert cmd.lpl == 5
        assert cmd.rpl_field == NVIDIA_CPO_OE_TELEMETRY_REPLY

    def test_encode_packs_payload_dict_into_5_byte_lpl(self):
        cmd = CdbReadOeTelemetry()
        encoded = cmd.encode({"bank_id": 0x02, "request_mask": 0x000003F0})

        # CDBCommand.encode prepends an 8-byte header (id|epl|lpl|cksum|rpl).
        assert encoded[:2] == b"\x90\x30"
        assert struct.unpack(">H", encoded[2:4])[0] == CDB_READ_OE_TELEMETRY_EPL_LEN
        assert encoded[4] == 5             # lpl byte
        # LPL payload starts at byte 8.
        assert encoded[8] == 0x02                                 # bank_id
        assert struct.unpack(">I", encoded[9:13])[0] == 0x000003F0  # request_mask

    def test_encode_defaults_request_mask_to_all(self):
        cmd = CdbReadOeTelemetry()
        encoded = cmd.encode({"bank_id": 1})
        assert encoded[8] == 1
        assert struct.unpack(">I", encoded[9:13])[0] == OE_TELEMETRY_REQUEST_MASK_ALL

    def test_encode_defaults_bank_id_to_zero(self):
        cmd = CdbReadOeTelemetry()
        encoded = cmd.encode({"request_mask": 0x12345678})
        assert encoded[8] == 0
        assert struct.unpack(">I", encoded[9:13])[0] == 0x12345678

    def test_request_mask_all_covers_all_advertised_caps(self):
        for bit in (4, 5, 6, 7, 8, 9, 18, 19, 20, 21):
            assert OE_TELEMETRY_REQUEST_MASK_ALL & (1 << bit), \
                "cap bit %d should be in OE_TELEMETRY_REQUEST_MASK_ALL" % bit


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


class TestGetOeTelemetry:
    def _raw_reply_marker(self):
        return {"sentinel": True}

    def test_returns_none_when_no_cdb_handler(self):
        api = _new_oe_api_stub(cdb_handler=None)
        assert api.get_oe_telemetry() is None

    def test_returns_none_when_send_returns_false(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = False
        api = _new_oe_api_stub(cdb_handler=cdb)
        assert api.get_oe_telemetry() is None
        assert not cdb.read_reply.called

    def test_returns_none_when_send_raises(self):
        cdb = MagicMock()
        cdb.send_cmd.side_effect = RuntimeError("boom")
        api = _new_oe_api_stub(cdb_handler=cdb)
        assert api.get_oe_telemetry() is None

    def test_returns_none_when_read_reply_raises(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.side_effect = RuntimeError("bad reply")
        api = _new_oe_api_stub(cdb_handler=cdb)
        assert api.get_oe_telemetry() is None

    def test_returns_none_when_read_reply_is_none(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = None
        api = _new_oe_api_stub(cdb_handler=cdb)
        assert api.get_oe_telemetry() is None

    def test_returns_raw_decoded_reply_unchanged(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        sentinel = self._raw_reply_marker()
        cdb.read_reply.return_value = sentinel
        api = _new_oe_api_stub(cdb_handler=cdb)
        assert api.get_oe_telemetry() is sentinel

    def test_send_cmd_invoked_with_payload_dict(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = self._raw_reply_marker()
        api = _new_oe_api_stub(cdb_handler=cdb, mem_map_bank=2)
        api.get_oe_telemetry()

        args, kwargs = cdb.send_cmd.call_args
        assert args[0] == CDB_READ_OE_TELEMETRY_CMD
        payload = kwargs["payload"]
        assert payload == {"bank_id": 2, "request_mask": OE_TELEMETRY_REQUEST_MASK_ALL}

    def test_caller_can_override_request_mask(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = self._raw_reply_marker()
        api = _new_oe_api_stub(cdb_handler=cdb, mem_map_bank=1)
        api.get_oe_telemetry(request_mask=0x000000F0)

        payload = cdb.send_cmd.call_args[1]["payload"]
        assert payload == {"bank_id": 1, "request_mask": 0x000000F0}

    def test_read_reply_invoked_with_cmd_id(self):
        cdb = MagicMock()
        cdb.send_cmd.return_value = True
        cdb.read_reply.return_value = self._raw_reply_marker()
        api = _new_oe_api_stub(cdb_handler=cdb)
        api.get_oe_telemetry()
        assert cdb.read_reply.call_args[0][0] == CDB_READ_OE_TELEMETRY_CMD


class TestGetTransceiverVdmRealValue:

    def _stub_get_oe_telemetry(self, api, value):
        api.get_oe_telemetry = MagicMock(return_value=value)

    def test_merges_super_vdm_with_oe_telemetry(self):
        api = _new_oe_api_stub()
        self._stub_get_oe_telemetry(api, {"NvidiaCpoOeTlmVerMajor": 1,
                                          "NvidiaCpoOeTlmVerMinor": 2})
        with patch.object(CmisApi, "get_transceiver_vdm_real_value",
                          return_value={"Laser Temperature [C]": 45.5}):
            out = api.get_transceiver_vdm_real_value()
        assert out == {
            "Laser Temperature [C]": 45.5,
            "NvidiaCpoOeTlmVerMajor": 1,
            "NvidiaCpoOeTlmVerMinor": 2,
        }

    def test_oe_telemetry_takes_precedence_on_key_collision(self):
        api = _new_oe_api_stub()
        self._stub_get_oe_telemetry(api, {"shared_key": "from_oe"})
        with patch.object(CmisApi, "get_transceiver_vdm_real_value",
                          return_value={"shared_key": "from_super"}):
            out = api.get_transceiver_vdm_real_value()
        assert out["shared_key"] == "from_oe"

    def test_returns_super_only_when_oe_telemetry_none(self):
        api = _new_oe_api_stub()
        self._stub_get_oe_telemetry(api, None)
        with patch.object(CmisApi, "get_transceiver_vdm_real_value",
                          return_value={"x": 1}):
            assert api.get_transceiver_vdm_real_value() == {"x": 1}

    def test_returns_oe_telemetry_only_when_super_none(self):
        api = _new_oe_api_stub()
        self._stub_get_oe_telemetry(api, {"NvidiaCpoOeTlmVerMajor": 7})
        with patch.object(CmisApi, "get_transceiver_vdm_real_value",
                          return_value=None):
            assert api.get_transceiver_vdm_real_value() == {
                "NvidiaCpoOeTlmVerMajor": 7,
            }

    def test_returns_none_when_both_sources_empty(self):
        api = _new_oe_api_stub()
        self._stub_get_oe_telemetry(api, None)
        with patch.object(CmisApi, "get_transceiver_vdm_real_value",
                          return_value=None):
            assert api.get_transceiver_vdm_real_value() is None


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
