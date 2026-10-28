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

"""XcvrApi for the NVIDIA CPO Optical Engine (OE).

Inherits CpoCmisApi, which is CmisApi with its aggregate getters split into
banked and non-banked halves so a caller can read the engine-wide half once per
engine rather than once per port; adds the OE telemetry (CDB 0x9030) to the
transceiver info, firmware info and status and drops the legacy laser
temperature, tx bias and per-lane status fields the OE does not support.
"""

import logging

from ..cdb_capable_mixin import CdbCapableMixin
from ...cpo.cmis import CpoCmisApi
from .cpo_cdb import CDB_TARGET_OE, NvidiaCpoCdbTargetMixin
from ...cdb.nvidia.cpo_oe_memmap import (
    CDB_READ_OE_TELEMETRY_CMD,
    NUM_LANES,
    NVIDIA_CPO_OE_TELEMETRY_EXT_MASKS,
    NVIDIA_CPO_OE_TLM_CAPABILITY,
    NVIDIA_CPO_OE_TLM_CAPABILITY_EXT,
    NVIDIA_CPO_OE_TLM_LAST_REASON_OPCODE,
    NVIDIA_CPO_OE_TLM_OE_SN,
    NVIDIA_CPO_OE_TLM_RX_HS_DATA_RATE,
    NVIDIA_CPO_OE_TLM_RX_PS_LANE_STATE,
    NVIDIA_CPO_OE_TLM_RX_PS_LANE_SUB_STATE,
    NVIDIA_CPO_OE_TLM_TX_HS_DATA_RATE,
    NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE,
    NVIDIA_CPO_OE_TLM_TX_PS_LANE_SUB_STATE,
    NVIDIA_CPO_OE_TLM_VALID,
    NVIDIA_CPO_OE_TLM_VALID_EXT,
    NVIDIA_CPO_OE_TLM_VER_MAJOR,
    NVIDIA_CPO_OE_TLM_VER_MINOR,
    NVIDIA_CPO_OE_TLM_VER_RC,
    OE_TELEMETRY_EXT_MASK_FIRST_BIT,
    OE_TELEMETRY_REQUEST_BITS,
    OE_TELEMETRY_REQUEST_MASK_ALL,
    oe_telemetry_request_mask,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Maps each per-lane 0x9030 reply field-name prefix (0-indexed _<lane> suffix)
# to its 0x9030 spec name with an oe_ prefix, published in the transceiver
# status as "<name>_lane<N>" with N the lane within the bank (0-7), as the spec
# numbers them.
_OE_TELEMETRY_STATUS_LANE_FIELDS = (
    (NVIDIA_CPO_OE_TLM_TX_PS_LANE_STATE,     'oe_tx_ps_state'),
    (NVIDIA_CPO_OE_TLM_RX_PS_LANE_STATE,     'oe_rx_ps_state'),
    (NVIDIA_CPO_OE_TLM_TX_PS_LANE_SUB_STATE, 'oe_tx_ps_sub'),
    (NVIDIA_CPO_OE_TLM_RX_PS_LANE_SUB_STATE, 'oe_rx_ps_sub'),
    (NVIDIA_CPO_OE_TLM_TX_HS_DATA_RATE,      'oe_tx_hs_data'),
    (NVIDIA_CPO_OE_TLM_RX_HS_DATA_RATE,      'oe_rx_hs_data'),
    (NVIDIA_CPO_OE_TLM_LAST_REASON_OPCODE,   'oe_last_reason_opcode'),
)

# Map the module-wide 0x9030 reply fields to their 0x9030 spec names with an
# oe_ prefix, published in the transceiver firmware info and info.
_OE_TELEMETRY_FIRMWARE_FIELDS = (
    (NVIDIA_CPO_OE_TLM_VER_MAJOR, 'oe_ver_major'),
    (NVIDIA_CPO_OE_TLM_VER_MINOR, 'oe_ver_minor'),
    (NVIDIA_CPO_OE_TLM_VER_RC,    'oe_ver_rc'),
)
_OE_TELEMETRY_INFO_FIELDS = (
    (NVIDIA_CPO_OE_TLM_OE_SN, 'oe_sn'),
)

# Each table is read with a 0x9030 request for only its own fields.
OE_TELEMETRY_STATUS_REQUEST_MASK = oe_telemetry_request_mask(
    src for src, _ in _OE_TELEMETRY_STATUS_LANE_FIELDS)
OE_TELEMETRY_FIRMWARE_REQUEST_MASK = oe_telemetry_request_mask(
    src for src, _ in _OE_TELEMETRY_FIRMWARE_FIELDS)
OE_TELEMETRY_INFO_REQUEST_MASK = oe_telemetry_request_mask(
    src for src, _ in _OE_TELEMETRY_INFO_FIELDS)

# Legacy DOM fields the OE does not support: it has no laser of its own (laser
# temperature comes from the ELS TEC via VDM) and reports no tx bias.
UNSUPPORTED_THRESHOLD_KEYS = (
    'lasertemphighalarm', 'lasertemplowalarm', 'lasertemphighwarning', 'lasertemplowwarning',
    'txbiashighalarm', 'txbiaslowalarm', 'txbiashighwarning', 'txbiaslowwarning',
)
UNSUPPORTED_NON_BANKED_FLAG_KEYS = (
    'lasertempHAlarm', 'lasertempLAlarm', 'lasertempHWarn', 'lasertempLWarn',
)
TX_BIAS_FLAG_KEY_TEMPLATES = (
    'tx%dbiasHAlarm', 'tx%dbiasLAlarm', 'tx%dbiasHWarn', 'tx%dbiasLWarn',
)
UNSUPPORTED_STATUS_KEY_TEMPLATES = (
    'rx%dOutputStatusHostlane',
)
UNSUPPORTED_STATUS_FLAG_KEY_TEMPLATES = (
    'tx%dcdrlol_hostlane', 'tx%d_eq_fault', 'rx%dcdrlol',
)


class NvidiaCpoOeCmisApi(NvidiaCpoCdbTargetMixin, CpoCmisApi, CdbCapableMixin):
    CDB_TARGET = CDB_TARGET_OE

    def __init__(self, xcvr_eeprom, cdb_mem_map=None, **kwargs):
        super(NvidiaCpoOeCmisApi, self).__init__(xcvr_eeprom, **kwargs)
        self._init_vendor_cdb_mem_map(cdb_mem_map)

    def _get_bank_id(self):
        return getattr(self.xcvr_eeprom.mem_map, 'bank', 0)

    def get_laser_temperature(self):
        return dict.fromkeys(('monitor value', 'high alarm', 'low alarm', 'high warn', 'low warn'), 'N/A')

    def get_non_banked_transceiver_dom_real_value(self):
        bulk_status = super().get_non_banked_transceiver_dom_real_value()
        if bulk_status:
            bulk_status.pop('laser_temperature', None)
        return bulk_status

    def get_tx_bias_support(self):
        return False

    def get_banked_transceiver_dom_real_value(self):
        bulk_status = super().get_banked_transceiver_dom_real_value()
        if bulk_status:
            for lane in range(1, self.NUM_CHANNELS + 1):
                bulk_status.pop('tx%dbias' % lane, None)
        return bulk_status

    def get_non_banked_transceiver_dom_flags(self):
        dom_flag_dict = super().get_non_banked_transceiver_dom_flags()
        for key in UNSUPPORTED_NON_BANKED_FLAG_KEYS:
            dom_flag_dict.pop(key, None)
        return dom_flag_dict

    def get_banked_transceiver_dom_flags(self):
        dom_flag_dict = super().get_banked_transceiver_dom_flags()
        for lane in range(1, self.NUM_CHANNELS + 1):
            for template in TX_BIAS_FLAG_KEY_TEMPLATES:
                dom_flag_dict.pop(template % lane, None)
        return dom_flag_dict

    def get_transceiver_info(self):
        xcvr_info = super().get_transceiver_info()
        if xcvr_info is not None:
            xcvr_info.update(self.get_oe_telemetry_info())
        return xcvr_info

    def get_transceiver_info_firmware_versions(self):
        firmware_info = super().get_transceiver_info_firmware_versions()
        firmware_info.update(self.get_oe_telemetry_firmware_versions())
        return firmware_info

    def get_banked_transceiver_status(self):
        trans_status = super().get_banked_transceiver_status()
        for lane in range(1, self.NUM_CHANNELS + 1):
            for template in UNSUPPORTED_STATUS_KEY_TEMPLATES:
                trans_status.pop(template % lane, None)
        trans_status.update(self.get_oe_telemetry_status())
        return trans_status

    def get_banked_transceiver_status_flags(self):
        status_flags_dict = super().get_banked_transceiver_status_flags()
        for lane in range(1, self.NUM_CHANNELS + 1):
            for template in UNSUPPORTED_STATUS_FLAG_KEY_TEMPLATES:
                status_flags_dict.pop(template % lane, None)
        return status_flags_dict

    def get_transceiver_threshold_info(self):
        threshold_info = super().get_transceiver_threshold_info()
        if threshold_info:
            for key in UNSUPPORTED_THRESHOLD_KEYS:
                threshold_info.pop(key, None)
        return threshold_info

    def get_oe_telemetry(self, request_mask=OE_TELEMETRY_REQUEST_MASK_ALL):
        """CDB 0x9030: the requested NVIDIA OE telemetry fields.

        Returns a dict holding only the requested fields, per-lane ones
        suffixed ``_0``..``_7``. A field is ``'N/A'`` unless the OE flags it
        as both supported and valid, or if reading it fails. Returns ``None``
        if CDB is unavailable or the command fails.
        """
        # The reply, with the extended masks and the serial number read after
        # it, stays in the CDB pages only until the next command.
        with self.cdb_lock():
            return self._read_oe_telemetry(request_mask)

    def _read_oe_telemetry(self, request_mask):
        if self.cdb_handler is None:
            return None

        payload = {"bank_id": self._get_bank_id(), "request_mask": request_mask}

        try:
            ok = self.cdb_handler.send_cmd(CDB_READ_OE_TELEMETRY_CMD, payload=payload)
        except Exception:
            logger.exception("CDB 0x%04x send failed", CDB_READ_OE_TELEMETRY_CMD)
            return None
        if ok is not True:
            logger.warning("CDB 0x%04x returned non-success: %r",
                           CDB_READ_OE_TELEMETRY_CMD, ok)
            return None

        try:
            reply = self.cdb_handler.read_reply(CDB_READ_OE_TELEMETRY_CMD)
        except Exception:
            logger.exception("CDB 0x%04x read_reply failed", CDB_READ_OE_TELEMETRY_CMD)
            return None
        if reply is None:
            return None

        # The nibble-packed per-lane fields decode as one dict per byte.
        flat = {}
        for key, value in reply.items():
            if isinstance(value, dict):
                flat.update(value)
            else:
                flat[key] = value

        supported = flat.get(NVIDIA_CPO_OE_TLM_CAPABILITY, 0) & flat.get(NVIDIA_CPO_OE_TLM_VALID, 0)
        if request_mask >> OE_TELEMETRY_EXT_MASK_FIRST_BIT:
            supported |= self._read_oe_telemetry_ext_support() << OE_TELEMETRY_EXT_MASK_FIRST_BIT

        result = {}
        for field, bit in OE_TELEMETRY_REQUEST_BITS.items():
            if not request_mask & (1 << bit):
                continue
            lane_names = ["%s_%d" % (field, lane) for lane in range(NUM_LANES)]
            for name in lane_names if lane_names[0] in flat else [field]:
                result[name] = self._read_oe_telemetry_value(name, flat) \
                    if supported & (1 << bit) else 'N/A'
        return result

    def _read_oe_telemetry_ext_support(self):
        """The extended capability & valid masks of the last 0x9030 reply, 0 if
        the read fails."""
        try:
            ext_masks = self.cdb_handler.read(NVIDIA_CPO_OE_TELEMETRY_EXT_MASKS)
        except Exception:
            logger.exception("CDB 0x%04x extended masks read failed", CDB_READ_OE_TELEMETRY_CMD)
            return 0
        if not ext_masks:
            return 0
        return ext_masks[NVIDIA_CPO_OE_TLM_CAPABILITY_EXT] & ext_masks[NVIDIA_CPO_OE_TLM_VALID_EXT]

    def _read_oe_telemetry_value(self, name, reply):
        """A field of the last 0x9030 reply, read on its own if it lies outside
        the reply group; ``'N/A'`` if the read fails or a string is blank."""
        if name in reply:
            value = reply[name]
        else:
            try:
                value = self.cdb_handler.read(name)
            except Exception:
                logger.exception("CDB 0x%04x %s read failed", CDB_READ_OE_TELEMETRY_CMD, name)
                return 'N/A'
        if isinstance(value, str):
            value = value.rstrip('\x00 ')
        return 'N/A' if value is None or value == '' else value

    def _get_oe_telemetry_fields(self, request_mask, fields):
        """The module-wide 0x9030 fields, each under its 0x9030 spec name and
        ``'N/A'`` if the OE does not answer."""
        telemetry = self.get_oe_telemetry(request_mask) or {}
        return {name: telemetry.get(src, 'N/A') for src, name in fields}

    def get_oe_telemetry_info(self):
        """The 0x9030 OE serial number."""
        return self._get_oe_telemetry_fields(OE_TELEMETRY_INFO_REQUEST_MASK,
                                             _OE_TELEMETRY_INFO_FIELDS)

    def get_oe_telemetry_firmware_versions(self):
        """The 0x9030 OE firmware version (major, minor, release candidate)."""
        return self._get_oe_telemetry_fields(OE_TELEMETRY_FIRMWARE_REQUEST_MASK,
                                             _OE_TELEMETRY_FIRMWARE_FIELDS)

    def get_oe_telemetry_status(self):
        """The per-lane 0x9030 fields of this port's lane bank.

        Each field is under its 0x9030 spec name as "<name>_lane<N>", with N
        the lane within the bank (0-7), and is ``'N/A'`` if the OE does not
        answer.
        """
        telemetry = self.get_oe_telemetry(OE_TELEMETRY_STATUS_REQUEST_MASK) or {}
        return {"%s_lane%d" % (name, lane): telemetry.get("%s_%d" % (src, lane), 'N/A')
                for src, name in _OE_TELEMETRY_STATUS_LANE_FIELDS
                for lane in range(NUM_LANES)}
