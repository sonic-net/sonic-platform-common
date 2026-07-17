#
# SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
# Copyright (c) 2019-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# Apache-2.0
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
#############################################################################
# Mellanox
#############################################################################

import struct

from ...fields import cdb_consts
from ...fields.xcvr_field import (
    NumberRegField,
    RegBitsField,
    RegGroupField,
)
from ...mem_maps.public.cdb import CDBCommand, CdbMemMap


CDB_READ_OE_TELEMETRY_CMD = 0x9030
CDB_READ_OE_TELEMETRY_EPL_LEN = 168

NVIDIA_CPO_OE_TELEMETRY_REPLY = "NvidiaCpoOeTelemetryReply"

NVIDIA_CPO_OE_TLM_CAPABILITY     = "NvidiaCpoOeTlmCapability"
NVIDIA_CPO_OE_TLM_VALID          = "NvidiaCpoOeTlmValid"
NVIDIA_CPO_OE_TLM_LANE_BANK_ECHO = "NvidiaCpoOeTlmLaneBankEcho"
NVIDIA_CPO_OE_TLM_VER_MAJOR      = "NvidiaCpoOeTlmVerMajor"
NVIDIA_CPO_OE_TLM_VER_MINOR      = "NvidiaCpoOeTlmVerMinor"
NVIDIA_CPO_OE_TLM_VER_RC         = "NvidiaCpoOeTlmVerRc"

NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE       = "NvidiaCpoOeTlmTxPsLaneState"
NVIDIA_CPO_OE_TLM_RX_PS_LANE_STATE       = "NvidiaCpoOeTlmRxPsLaneState"
NVIDIA_CPO_OE_TLM_TX_PS_LANE_SUB_STATE   = "NvidiaCpoOeTlmTxPsLaneSubState"
NVIDIA_CPO_OE_TLM_RX_PS_LANE_SUB_STATE   = "NvidiaCpoOeTlmRxPsLaneSubState"
NVIDIA_CPO_OE_TLM_TX_HS_DATA_RATE        = "NvidiaCpoOeTlmTxHsDataRate"
NVIDIA_CPO_OE_TLM_RX_HS_DATA_RATE        = "NvidiaCpoOeTlmRxHsDataRate"
NVIDIA_CPO_OE_TLM_LAST_REASON_OPCODE     = "NvidiaCpoOeTlmLastReasonOpcode"

# EPL absolute offsets (from EPL byte 0 = page 0xA0 byte 128) of each block.
_OFF_CAPABILITY            = 0
_OFF_VALID                 = 4
_OFF_LANE_BANK_ECHO        = 8
_OFF_TX_PS_LANE_STATE      = 43
_OFF_RX_PS_LANE_STATE      = 47
_OFF_TX_PS_LANE_SUB_STATE  = 51
_OFF_RX_PS_LANE_SUB_STATE  = 67
_OFF_TX_HS_DATA_RATE       = 83
_OFF_RX_HS_DATA_RATE       = 87
_OFF_LAST_REASON_OPCODE    = 154
_OFF_VER_MAJOR             = 162
_OFF_VER_MINOR             = 164
_OFF_VER_RC                = 166

NUM_LANES = 8

# Per-field cap-bit metadata gating each field. Cap-bit interpretation of the
# decoded reply is the consumer's job (cap & valid -> use value).
# Bits >= 18 are firmware-version slots that the MCU populates unconditionally.
_OE_TELEMETRY_CAP_BITS = (4, 5, 6, 7, 8, 9, 18, 19, 20, 21)

OE_TELEMETRY_REQUEST_MASK_ALL = 0
for _bit in _OE_TELEMETRY_CAP_BITS:
    OE_TELEMETRY_REQUEST_MASK_ALL |= (1 << _bit)


def _lane_name(prefix, lane):
    return f"{prefix}_{lane}"


def _build_nibble_packed_lane_fields(getaddr, prefix, base_offset, bit_width):
    """4 NumberRegField parents (1 byte each) holding 2 RegBitsField lanes per byte.

    Even lanes occupy bits 0..bit_width-1; odd lanes bits 4..4+bit_width-1.
    """
    fields = []
    for byte_idx in range(NUM_LANES // 2):
        even_lane = byte_idx * 2
        odd_lane = byte_idx * 2 + 1
        fields.append(
            NumberRegField(
                f"{prefix}_byte{byte_idx}",
                getaddr(cdb_consts.EPL_PAGE, 128 + base_offset + byte_idx),
                RegBitsField(_lane_name(prefix, even_lane), bitpos=0, size=bit_width),
                RegBitsField(_lane_name(prefix, odd_lane),  bitpos=4, size=bit_width),
                bitdecode=True,
            )
        )
    return fields


def _build_u16_per_lane_fields(getaddr, prefix, base_offset):
    return [
        NumberRegField(
            _lane_name(prefix, lane),
            getaddr(cdb_consts.EPL_PAGE, 128 + base_offset + lane * 2),
            size=2, format=">H",
        )
        for lane in range(NUM_LANES)
    ]


def _build_u8_per_lane_fields(getaddr, prefix, base_offset):
    return [
        NumberRegField(
            _lane_name(prefix, lane),
            getaddr(cdb_consts.EPL_PAGE, 128 + base_offset + lane),
            size=1, format="B",
        )
        for lane in range(NUM_LANES)
    ]


class CdbReadOeTelemetry(CDBCommand):
    """CDB 0x9030 -- read OE telemetry block (EPL reply).

    LPL request payload (5 bytes): [bank_id_u8] + [request_mask_u32_be].
    Payload contract: ``send_cmd(cmd_id, payload={"bank_id": int, "request_mask": int})``;
    request_mask defaults to ``OE_TELEMETRY_REQUEST_MASK_ALL`` when omitted.
    """
    def __init__(self,
                 cmd_id=CDB_READ_OE_TELEMETRY_CMD,
                 reply_field=NVIDIA_CPO_OE_TELEMETRY_REPLY):
        super(CdbReadOeTelemetry, self).__init__(
            cmd_id,
            epl=CDB_READ_OE_TELEMETRY_EPL_LEN,
            lpl=5,
            rpl_field=reply_field,
        )

    def encode(self, payload):
        bank_id = payload.get("bank_id", 0) & 0xFF
        request_mask = payload.get("request_mask", OE_TELEMETRY_REQUEST_MASK_ALL) & 0xFFFFFFFF
        lpl_data = struct.pack("B", bank_id) + struct.pack(">I", request_mask)
        return super(CdbReadOeTelemetry, self).encode(payload=lpl_data)


class NvidiaCpoOeCdbMemMap(CdbMemMap):
    def __init__(self, codes):
        super(NvidiaCpoOeCdbMemMap, self).__init__(codes)

        getaddr = self.getaddr

        reply_fields = [
            NumberRegField(NVIDIA_CPO_OE_TLM_CAPABILITY,
                           getaddr(cdb_consts.EPL_PAGE, 128 + _OFF_CAPABILITY),
                           size=4, format=">I"),
            NumberRegField(NVIDIA_CPO_OE_TLM_VALID,
                           getaddr(cdb_consts.EPL_PAGE, 128 + _OFF_VALID),
                           size=4, format=">I"),
            NumberRegField(NVIDIA_CPO_OE_TLM_LANE_BANK_ECHO,
                           getaddr(cdb_consts.EPL_PAGE, 128 + _OFF_LANE_BANK_ECHO),
                           size=1, format="B"),
        ]
        reply_fields += _build_nibble_packed_lane_fields(
            getaddr, NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE,
            _OFF_TX_PS_LANE_STATE, bit_width=4)
        reply_fields += _build_nibble_packed_lane_fields(
            getaddr, NVIDIA_CPO_OE_TLM_RX_PS_LANE_STATE,
            _OFF_RX_PS_LANE_STATE, bit_width=4)
        reply_fields += _build_u16_per_lane_fields(
            getaddr, NVIDIA_CPO_OE_TLM_TX_PS_LANE_SUB_STATE,
            _OFF_TX_PS_LANE_SUB_STATE)
        reply_fields += _build_u16_per_lane_fields(
            getaddr, NVIDIA_CPO_OE_TLM_RX_PS_LANE_SUB_STATE,
            _OFF_RX_PS_LANE_SUB_STATE)
        reply_fields += _build_nibble_packed_lane_fields(
            getaddr, NVIDIA_CPO_OE_TLM_TX_HS_DATA_RATE,
            _OFF_TX_HS_DATA_RATE, bit_width=3)
        reply_fields += _build_nibble_packed_lane_fields(
            getaddr, NVIDIA_CPO_OE_TLM_RX_HS_DATA_RATE,
            _OFF_RX_HS_DATA_RATE, bit_width=3)
        reply_fields += _build_u8_per_lane_fields(
            getaddr, NVIDIA_CPO_OE_TLM_LAST_REASON_OPCODE,
            _OFF_LAST_REASON_OPCODE)
        reply_fields += [
            NumberRegField(NVIDIA_CPO_OE_TLM_VER_MAJOR,
                           getaddr(cdb_consts.EPL_PAGE, 128 + _OFF_VER_MAJOR),
                           size=2, format=">H"),
            NumberRegField(NVIDIA_CPO_OE_TLM_VER_MINOR,
                           getaddr(cdb_consts.EPL_PAGE, 128 + _OFF_VER_MINOR),
                           size=2, format=">H"),
            NumberRegField(NVIDIA_CPO_OE_TLM_VER_RC,
                           getaddr(cdb_consts.EPL_PAGE, 128 + _OFF_VER_RC),
                           size=2, format=">H"),
        ]

        self.nvidia_cpo_oe_telemetry_reply = RegGroupField(
            NVIDIA_CPO_OE_TELEMETRY_REPLY, *reply_fields)

        self.nvidia_cpo_oe_read_telemetry_cmd = CdbReadOeTelemetry()
