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

"""CDB memory map for the NVIDIA CPO Optical Engine (OE).

Adds command 0x9030 (CdbReadOeTelemetry) on top of the standard CdbMemMap.
The first 168 bytes of the EPL reply (from page 0xA0 byte 128) are decoded into
the NVIDIA_CPO_OE_TELEMETRY_REPLY RegGroupField defined below. The OE serial
number and the extended capability/valid masks sit further into the reply and
are separate fields, read only when the OE serial number is requested.
"""
import struct

from ...fields import cdb_consts
from ...fields.xcvr_field import (
    NumberRegField,
    RegBitsField,
    RegGroupField,
    StringRegField,
)
from ...mem_maps.public.cmis.cdb import CDBCommand, CdbMemMap


CDB_READ_OE_TELEMETRY_CMD = 0x9030
CDB_READ_OE_TELEMETRY_EPL_LEN = 168
OE_TELEMETRY_REQUEST_MASK_LEN = 5

NVIDIA_CPO_OE_TELEMETRY_REPLY = "NvidiaCpoOeTelemetryReply"

NVIDIA_CPO_OE_TLM_CAPABILITY     = "NvidiaCpoOeTlmCapability"
NVIDIA_CPO_OE_TLM_VALID          = "NvidiaCpoOeTlmValid"
NVIDIA_CPO_OE_TLM_LANE_BANK_ECHO = "NvidiaCpoOeTlmLaneBankEcho"
NVIDIA_CPO_OE_TLM_VER_MAJOR      = "NvidiaCpoOeTlmVerMajor"
NVIDIA_CPO_OE_TLM_VER_MINOR      = "NvidiaCpoOeTlmVerMinor"
NVIDIA_CPO_OE_TLM_VER_RC         = "NvidiaCpoOeTlmVerRc"
NVIDIA_CPO_OE_TLM_OE_SN          = "NvidiaCpoOeTlmOeSn"

NVIDIA_CPO_OE_TELEMETRY_EXT_MASKS = "NvidiaCpoOeTelemetryExtMasks"
NVIDIA_CPO_OE_TLM_CAPABILITY_EXT  = "NvidiaCpoOeTlmCapabilityExt"
NVIDIA_CPO_OE_TLM_VALID_EXT       = "NvidiaCpoOeTlmValidExt"

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
_OFF_OE_SN                 = 168
_OFF_CAPABILITY_EXT        = 318
_OFF_VALID_EXT             = 320

OE_SN_LEN = 28

NUM_LANES = 8

# The request bit of each 0x9030 field (per-lane fields by name prefix). The OE
# flags a field as supported and valid with the same bit of the capability and
# valid masks; for bits 32 and up, with bit (bit - 32) of the extended masks.
# The spec's capability and valid lists omit bits 18-21; firmware 0.8.0 sets
# 19-21 and clears 18 in both.
OE_TELEMETRY_REQUEST_BITS = {
    NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE:     4,
    NVIDIA_CPO_OE_TLM_TX_PS_LANE_SUB_STATE: 5,
    NVIDIA_CPO_OE_TLM_RX_PS_LANE_STATE:     6,
    NVIDIA_CPO_OE_TLM_RX_PS_LANE_SUB_STATE: 7,
    NVIDIA_CPO_OE_TLM_TX_HS_DATA_RATE:      8,
    NVIDIA_CPO_OE_TLM_RX_HS_DATA_RATE:      9,
    NVIDIA_CPO_OE_TLM_LAST_REASON_OPCODE:   18,
    NVIDIA_CPO_OE_TLM_VER_MAJOR:            19,
    NVIDIA_CPO_OE_TLM_VER_MINOR:            20,
    NVIDIA_CPO_OE_TLM_VER_RC:               21,
    NVIDIA_CPO_OE_TLM_OE_SN:                35,
}
OE_TELEMETRY_EXT_MASK_FIRST_BIT = 32


def oe_telemetry_request_mask(fields):
    """The 0x9030 request mask for the given field names (or name prefixes)."""
    mask = 0
    for field in fields:
        mask |= 1 << OE_TELEMETRY_REQUEST_BITS[field]
    return mask


OE_TELEMETRY_REQUEST_MASK_ALL = oe_telemetry_request_mask(OE_TELEMETRY_REQUEST_BITS)


def _lane_name(prefix, lane):
    return "%s_%d" % (prefix, lane)


def _cdb_addr(page, offset, page_size=128):
    """Flat EEPROM address of `offset` within CDB `page`. CDB pages are never banked."""
    return page * page_size + offset


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
                "%s_byte%d" % (prefix, byte_idx),
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

    LPL request payload (6 bytes): [lane_bank_u8] + [request_params_bitmask, 5 bytes BE].
    Payload contract: ``send_cmd(cmd_id, payload={"bank_id": int, "request_mask": int})``;
    request_mask defaults to ``OE_TELEMETRY_REQUEST_MASK_ALL`` when omitted.
    """
    def __init__(self,
                 cmd_id=CDB_READ_OE_TELEMETRY_CMD,
                 reply_field=NVIDIA_CPO_OE_TELEMETRY_REPLY):
        # The request carries no EPL data; CDB_READ_OE_TELEMETRY_EPL_LEN is the
        # size of the module's EPL reply, not of anything the host sends.
        super(CdbReadOeTelemetry, self).__init__(
            cmd_id,
            epl=0,
            lpl=1 + OE_TELEMETRY_REQUEST_MASK_LEN,
            rpl_field=reply_field,
        )

    def encode(self, payload):
        bank_id = payload.get("bank_id", 0) & 0xFF
        request_mask = payload.get("request_mask", OE_TELEMETRY_REQUEST_MASK_ALL)
        lpl_data = struct.pack("B", bank_id) + request_mask.to_bytes(OE_TELEMETRY_REQUEST_MASK_LEN, "big")
        return super(CdbReadOeTelemetry, self).encode(payload=lpl_data)


class NvidiaCpoOeCdbMemMap(CdbMemMap):
    def __init__(self, codes):
        super(NvidiaCpoOeCdbMemMap, self).__init__(codes)

        getaddr = _cdb_addr

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

        self.nvidia_cpo_oe_telemetry_oe_sn = StringRegField(
            NVIDIA_CPO_OE_TLM_OE_SN,
            getaddr(cdb_consts.EPL_PAGE, 128 + _OFF_OE_SN),
            size=OE_SN_LEN)

        self.nvidia_cpo_oe_telemetry_ext_masks = RegGroupField(
            NVIDIA_CPO_OE_TELEMETRY_EXT_MASKS,
            NumberRegField(NVIDIA_CPO_OE_TLM_CAPABILITY_EXT,
                           getaddr(cdb_consts.EPL_PAGE, 128 + _OFF_CAPABILITY_EXT),
                           size=2, format=">H"),
            NumberRegField(NVIDIA_CPO_OE_TLM_VALID_EXT,
                           getaddr(cdb_consts.EPL_PAGE, 128 + _OFF_VALID_EXT),
                           size=2, format=">H"))

        self.nvidia_cpo_oe_read_telemetry_cmd = CdbReadOeTelemetry()
