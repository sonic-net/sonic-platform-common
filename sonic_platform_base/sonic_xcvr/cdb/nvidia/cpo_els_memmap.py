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
from ...fields.scale_consts import (
    SCALE_0P1W_TO_W,
    SCALE_5MV_TO_MV,
    SCALE_UA_TO_MA,
)
from ...fields.xcvr_field import (
    NumberRegField,
    RegGroupField,
)
from ...mem_maps.public.cdb import CDBCommand, CdbMemMap


CDB_READ_ELS_LASER_MONITORING_CMD = 0x9018

NVIDIA_CPO_ELS_LASER_MONITORING_REPLY = "NvidiaCpoElsLaserMonitoringReply"

NVIDIA_CPO_ELS_LASER_MON_CAP    = "NvidiaCpoElsLaserMonCap"
NVIDIA_CPO_ELS_LASER_MON_BANK   = "NvidiaCpoElsLaserMonBank"
NVIDIA_CPO_ELS_LASER_MON_MASK   = "NvidiaCpoElsLaserMonMask"
NVIDIA_CPO_ELS_MODULE_POWER     = "NvidiaCpoElsModulePower"

NVIDIA_CPO_ELS_LASER_MPD        = "NvidiaCpoElsLaserMpd"
NVIDIA_CPO_ELS_TEC_VOLTAGE      = "NvidiaCpoElsTecVoltage"
NVIDIA_CPO_ELS_LASER_HEALTH     = "NvidiaCpoElsLaserHealth"
NVIDIA_CPO_ELS_TEC_HEALTH       = "NvidiaCpoElsTecHealth"

# LPL reply offsets relative to RPL_DATA_START_OFFSET (page 0x9F byte 136).
_OFF_MON_CAP        = 0
_OFF_MON_BANK       = 1
_OFF_MON_MASK       = 2
# offset 3: reserved
_OFF_LASER_MPD      = 4
_OFF_TEC_VOLTAGE    = 20
_OFF_LASER_HEALTH   = 36
_OFF_TEC_HEALTH     = 44
_OFF_MODULE_POWER   = 52

NUM_LASERS = 8

ELS_LASER_MON_CAP_BIT_LASER_MPD     = 0x01
ELS_LASER_MON_CAP_BIT_TEC_VOLTAGE   = 0x02
ELS_LASER_MON_CAP_BIT_LASER_HEALTH  = 0x04
ELS_LASER_MON_CAP_BIT_TEC_HEALTH    = 0x08
ELS_LASER_MON_CAP_BIT_MODULE_POWER  = 0x10

ELS_LASER_MONITORING_CAP_MASK_ALL = (
    ELS_LASER_MON_CAP_BIT_LASER_MPD
    | ELS_LASER_MON_CAP_BIT_TEC_VOLTAGE
    | ELS_LASER_MON_CAP_BIT_LASER_HEALTH
    | ELS_LASER_MON_CAP_BIT_TEC_HEALTH
    | ELS_LASER_MON_CAP_BIT_MODULE_POWER
)

# Scale factors are named constants in fields.scale_consts.
# CDB 0x9018 reply layout:
#   laser MPD    -> SCALE_UA_TO_MA    (1 uA/LSB, decoded in mA)
#   TEC voltage  -> no scale (raw u16; unit under review)
#   laser health -> SCALE_5MV_TO_MV   (5 mV/LSB, decoded in mV)
#   TEC health   -> SCALE_5MV_TO_MV   (5 mV/LSB, decoded in mV)
#   module power -> SCALE_0P1W_TO_W   (0.1 W/LSB, decoded in W)


def _lane_name(prefix, lane):
    return f"{prefix}_{lane}"


def _lpl_addr(getaddr, byte_offset):
    return getaddr(cdb_consts.LPL_PAGE,
                   cdb_consts.RPL_DATA_START_OFFSET + byte_offset)


def _build_u16_per_lane_fields(getaddr, prefix, base_offset, scale=None):
    return [
        NumberRegField(
            _lane_name(prefix, lane),
            _lpl_addr(getaddr, base_offset + lane * 2),
            size=2, format=">H",
            scale=scale,
        )
        for lane in range(NUM_LASERS)
    ]


def _build_u8_per_lane_fields(getaddr, prefix, base_offset, scale=None):
    return [
        NumberRegField(
            _lane_name(prefix, lane),
            _lpl_addr(getaddr, base_offset + lane),
            size=1, format="B",
            scale=scale,
        )
        for lane in range(NUM_LASERS)
    ]


class CdbReadElsLaserMonitoring(CDBCommand):
    """CDB 0x9018 -- read ELS laser monitoring (LPL reply only).

    Payload contract: ``send_cmd(cmd_id, payload={"cap_mask": int, "bank_id": int, "laser_mask": int})``.
    Per-lane reply keys use the internal ``_<lane>`` (0-indexed) suffix.
    """
    def __init__(self,
                 cmd_id=CDB_READ_ELS_LASER_MONITORING_CMD,
                 reply_field=NVIDIA_CPO_ELS_LASER_MONITORING_REPLY):
        super(CdbReadElsLaserMonitoring, self).__init__(
            cmd_id,
            epl=0,
            lpl=3,
            rpl_field=reply_field,
        )

    def encode(self, payload):
        cap_mask   = payload.get("cap_mask",   ELS_LASER_MONITORING_CAP_MASK_ALL) & 0xFF
        bank_id    = payload.get("bank_id",    0) & 0xFF
        laser_mask = payload.get("laser_mask", 0) & 0xFF
        lpl_data = struct.pack("BBB", cap_mask, bank_id, laser_mask)
        return super(CdbReadElsLaserMonitoring, self).encode(payload=lpl_data)


class NvidiaCpoElsCdbMemMap(CdbMemMap):
    def __init__(self, codes):
        super(NvidiaCpoElsCdbMemMap, self).__init__(codes)

        getaddr = self.getaddr

        reply_fields = [
            NumberRegField(NVIDIA_CPO_ELS_LASER_MON_CAP,
                           _lpl_addr(getaddr, _OFF_MON_CAP),
                           size=1, format="B"),
            NumberRegField(NVIDIA_CPO_ELS_LASER_MON_BANK,
                           _lpl_addr(getaddr, _OFF_MON_BANK),
                           size=1, format="B"),
            NumberRegField(NVIDIA_CPO_ELS_LASER_MON_MASK,
                           _lpl_addr(getaddr, _OFF_MON_MASK),
                           size=1, format="B"),
        ]
        reply_fields += _build_u16_per_lane_fields(
            getaddr, NVIDIA_CPO_ELS_LASER_MPD, _OFF_LASER_MPD,
            scale=SCALE_UA_TO_MA)
        reply_fields += _build_u16_per_lane_fields(
            getaddr, NVIDIA_CPO_ELS_TEC_VOLTAGE, _OFF_TEC_VOLTAGE)
        reply_fields += _build_u8_per_lane_fields(
            getaddr, NVIDIA_CPO_ELS_LASER_HEALTH, _OFF_LASER_HEALTH,
            scale=SCALE_5MV_TO_MV)
        reply_fields += _build_u8_per_lane_fields(
            getaddr, NVIDIA_CPO_ELS_TEC_HEALTH, _OFF_TEC_HEALTH,
            scale=SCALE_5MV_TO_MV)
        reply_fields += [
            NumberRegField(NVIDIA_CPO_ELS_MODULE_POWER,
                           _lpl_addr(getaddr, _OFF_MODULE_POWER),
                           size=2, format=">H",
                           scale=SCALE_0P1W_TO_W),
        ]

        self.nvidia_cpo_els_laser_monitoring_reply = RegGroupField(
            NVIDIA_CPO_ELS_LASER_MONITORING_REPLY, *reply_fields)

        self.nvidia_cpo_els_read_laser_monitoring_cmd = CdbReadElsLaserMonitoring()
