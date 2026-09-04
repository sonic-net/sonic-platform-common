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


import logging

from ..public.cmis import CmisApi
from ...cdb.nvidia.cpo_oe_memmap import (
    CDB_READ_OE_TELEMETRY_CMD,
    OE_TELEMETRY_REQUEST_MASK_ALL,
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class NvidiaCpoOeCmisApi(CmisApi):

    def _get_bank_id(self):
        return getattr(self.xcvr_eeprom.mem_map, 'bank', 0)

    def get_oe_telemetry(self, request_mask=OE_TELEMETRY_REQUEST_MASK_ALL):
        """CDB 0x9030: read NVIDIA OE telemetry block.

        Returns the raw decoded reply dict (per-lane fields are suffixed
        ``_0``..``_7``). Cap/valid-bit interpretation is the consumer's job.
        Returns ``None`` if CDB is unavailable or the command fails.
        """
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
            return self.cdb_handler.read_reply(CDB_READ_OE_TELEMETRY_CMD)
        except Exception:
            logger.exception("CDB 0x%04x read_reply failed", CDB_READ_OE_TELEMETRY_CMD)
            return None

    def get_transceiver_vdm_real_value(self):
        """Standard CMIS VDM real values overlaid with the NVIDIA OE telemetry block."""
        result = super().get_transceiver_vdm_real_value() or {}
        oe = self.get_oe_telemetry()
        if oe:
            result.update(oe)
        return result or None
