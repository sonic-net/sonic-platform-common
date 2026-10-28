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

"""XcvrApi for the NVIDIA CPO External Laser Source (ELS).

Inherits ElsfpApi and its aggregates, overriding only where the NVIDIA laser
source departs from the standard: it reports its temperature in the Custom
Monitor slot (page 0x00 byte 24, thresholds at page 0x02 bytes 168-175, flags
in the high nibble of lower-memory byte 11) rather than the module temperature
slot, it reads the module state from live page 0x00 byte 3 rather than the
static page B0 snapshot, and it adds the CDB 0x9018 laser monitoring block to
the DOM readings.
Its CDB is the optical engine's. The vModule routes the CDB 0x9018 command to
the laser source by itself, so it is sent without selecting a CDB target.
"""

import logging

from ..public.elsfp import ElsfpApi
from .cpo_cdb import CDB_TARGET_ELS, NvidiaCpoCdbTargetMixin
from ...fields import consts
from ...fields import elsfp_consts
from ...mem_maps.nvidia.cpo_els import (
    NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD,
    NVIDIA_ELS_MODULE_STATE_FIELD,
    NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD,
)
from ...cdb.nvidia.cpo_els_memmap import (
    CDB_READ_ELS_LASER_MONITORING_CMD,
    ELS_LASER_MONITORING_CAP_MASK_ALL,
    NUM_LASERS,
    NVIDIA_CPO_ELS_LASER_HEALTH,
    NVIDIA_CPO_ELS_LASER_MPD,
    NVIDIA_CPO_ELS_MODULE_POWER,
    NVIDIA_CPO_ELS_TEC_HEALTH,
    NVIDIA_CPO_ELS_TEC_VOLTAGE,
)

# Maps each per-laser CDB 0x9018 reply field-name prefix (0-indexed _<lane> suffix)
# to the name it is published under, as "<name>_lane<N>" with N the absolute lane.
_ELS_LASER_DOM_SENSOR_RENAMES = (
    (NVIDIA_CPO_ELS_LASER_MPD,    'laser_mpd'),
    (NVIDIA_CPO_ELS_TEC_VOLTAGE,  'tec_voltage'),
    (NVIDIA_CPO_ELS_LASER_HEALTH, 'health_value'),
    (NVIDIA_CPO_ELS_TEC_HEALTH,   'tec_health_value'),
)

# Standard CMIS power and bias thresholds the laser source leaves unset: it has
# no receiver, and its output power and bias thresholds are the page 1Ah ones.
_UNSET_STANDARD_THRESHOLD_PREFIXES = ("rxpower", "txpower", "txbias")

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class NvidiaCpoElsCmisApi(NvidiaCpoCdbTargetMixin, ElsfpApi):
    CDB_TARGET = CDB_TARGET_ELS

    def is_cdb_supported(self):
        """This laser source supports CDB despite what it advertises.

        It reports CDB_SUPPORT as 0 while answering the standard firmware
        commands - reading the version off one returns 42.40.15 where the
        optical engine beside it returns 95.10.742 - so honouring the
        advertisement would refuse a path that demonstrably works.

        Remove this override once the laser source firmware sets the field.
        """
        return True

    @property
    def _untargeted_cdb_handler(self):
        """The vendor CDB handler, without NvidiaCpoCdbTargetMixin's target selection.

        The vModule routes CDB 0x9018 to the laser source by itself; only the
        firmware commands need the CDB target selected.
        """
        return super(NvidiaCpoCdbTargetMixin, self).cdb_handler

    def get_module_state(self) -> str:
        """Return the live CMIS module state from page 0x00 byte 3.

        The B0 copy of this byte is a static snapshot of the els status,
        so this reads the page 0x00 byte 3 to show the vModule status instead.
        In joint mode, the els status is identical to the vModule status.
        The value is one of ModuleLowPwr, ModulePwrUp, ModuleReady,
        ModulePwrDn, or ModuleFault.
        """
        state = self.xcvr_eeprom.read(NVIDIA_ELS_MODULE_STATE_FIELD)
        if not isinstance(state, dict):
            return None
        return state.get(consts.MODULE_STATE)

    def get_non_banked_elsfp_status(self):
        """The standard status without the module fault cause.

        The fault cause is reachable only through the static page B0 snapshot,
        so it would not follow the live module state read from page 0x00.
        """
        status = super().get_non_banked_elsfp_status()
        if status is None:
            return None
        status.pop("module_fault_cause", None)
        return status

    def get_module_temperature(self):
        """The laser source temperature, from the Custom Monitor slot."""
        temperature = self.xcvr_eeprom.read(consts.CUSTOM_MON)
        if temperature is None:
            return None
        return float("{:.3f}".format(temperature))

    def get_non_banked_elsfp_dom_flags(self):
        flags = super().get_non_banked_elsfp_dom_flags()
        module_flag_byte3 = self.xcvr_eeprom.read(consts.MODULE_FLAG_BYTE3)
        if flags is None or module_flag_byte3 is None:
            return None

        # The Custom Monitor flags sit in the high nibble of byte 11, ordered
        # high alarm, low alarm, high warning, low warning like the others.
        nibble = (module_flag_byte3 >> 4) & 0xF
        flags.update({
            "temperature_alarm_high": bool(nibble & 0x1),
            "temperature_alarm_low": bool((nibble >> 1) & 0x1),
            "temperature_warn_high": bool((nibble >> 2) & 0x1),
            "temperature_warn_low": bool((nibble >> 3) & 0x1)
        })
        return flags

    def get_elsfp_threshold_info(self):
        threshold_info = super().get_elsfp_threshold_info()
        temperature = self.xcvr_eeprom.read(NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD)
        voltage = self.xcvr_eeprom.read(NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD)
        if threshold_info is None or temperature is None or voltage is None:
            return None

        threshold_info = {key: value for key, value in threshold_info.items()
                          if not key.startswith(_UNSET_STANDARD_THRESHOLD_PREFIXES)}
        threshold_info.update({
            "temperature_alarm_high": float("{:.3f}".format(temperature[consts.CUSTOM_MON_HIGH_ALARM])),
            "temperature_alarm_low": float("{:.3f}".format(temperature[consts.CUSTOM_MON_LOW_ALARM])),
            "temperature_warn_high": float("{:.3f}".format(temperature[consts.CUSTOM_MON_HIGH_WARN])),
            "temperature_warn_low": float("{:.3f}".format(temperature[consts.CUSTOM_MON_LOW_WARN])),
            "voltage_alarm_high": float("{:.3f}".format(voltage[consts.VOLTAGE_HIGH_ALARM_FIELD])),
            "voltage_alarm_low": float("{:.3f}".format(voltage[consts.VOLTAGE_LOW_ALARM_FIELD])),
            "voltage_warn_high": float("{:.3f}".format(voltage[consts.VOLTAGE_HIGH_WARNING_FIELD])),
            "voltage_warn_low": float("{:.3f}".format(voltage[consts.VOLTAGE_LOW_WARNING_FIELD]))
        })
        return threshold_info

    def get_banked_elsfp_dom_real_value(self):
        dom = super().get_banked_elsfp_dom_real_value()
        if dom is None:
            return None
        dom.update(self.get_els_setpoint_values())
        laser_dom = self.get_els_laser_dom_sensors()
        if laser_dom is None:
            # Without the laser monitoring the readings are not complete.
            return None
        dom.update(laser_dom)
        return dom

    def get_els_setpoint_values(self):
        """Page 1Bh per-lane bias current and optical power setpoints."""
        result = {}
        first_lane = self._get_first_lane_for_bank()
        for name, field, values, convert in (
                ("bias_current_setpoint", elsfp_consts.BIAS_CURRENT_SETPOINT_FIELD,
                 self.get_per_lane_bias_current_setpoint(), self.amps_to_ma),
                ("optical_power_setpoint", elsfp_consts.OPT_POWER_SETPOINT_FIELD,
                 self.get_per_lane_opt_power_setpoint(), self.mw_to_dbm)):
            if not values:
                continue
            for index in range(len(values)):
                value = values.get("%s%d" % (field, index + 1))
                if value is None:
                    continue
                result["%s_lane%d" % (name, first_lane + index)] = float("{:.3f}".format(convert(value)))
        return result

    def get_els_laser_monitoring(self, cap_mask=ELS_LASER_MONITORING_CAP_MASK_ALL,
                                 laser_mask=0x00):
        """CDB 0x9018: read NVIDIA ELS laser monitoring block (raw decoded reply).

        Returns {} if the module has no CDB, and None if the command or the
        reading of its reply fails.
        """
        cdb_handler = self._untargeted_cdb_handler
        if cdb_handler is None:
            return {}

        payload = {
            "cap_mask":   cap_mask,
            "bank_id":    self.xcvr_eeprom.mem_map.bank,
            "laser_mask": laser_mask,
        }

        # The command needs no target, but the CDB is shared, and the reply
        # is in the CDB pages until the next command.
        with self.cdb_lock():
            try:
                ok = cdb_handler.send_cmd(CDB_READ_ELS_LASER_MONITORING_CMD,
                                          payload=payload)
            except Exception:
                logger.exception("CDB 0x%04x send failed",
                                 CDB_READ_ELS_LASER_MONITORING_CMD)
                return None
            if ok is not True:
                logger.warning("CDB 0x%04x returned non-success: %r",
                               CDB_READ_ELS_LASER_MONITORING_CMD, ok)
                return None

            try:
                return cdb_handler.read_reply(CDB_READ_ELS_LASER_MONITORING_CMD)
            except Exception:
                logger.exception("CDB 0x%04x read_reply failed",
                                 CDB_READ_ELS_LASER_MONITORING_CMD)
                return None

    def get_els_laser_dom_sensors(self):
        """The CDB 0x9018 reply as DOM readings of this bank's lasers.

        Each per-laser field is published as "<name>_lane<N>" with N the
        absolute lane, like the readings ElsfpApi publishes, and the module
        power as ``power_consumption``. Cap/bank/mask framing bytes are dropped.
        Returns None if the CDB read fails.
        """
        raw = self.get_els_laser_monitoring()
        if raw is None:
            return None
        if not raw:
            return {}
        result = {}
        first_lane = self._get_first_lane_for_bank()
        for src_prefix, dst_prefix in _ELS_LASER_DOM_SENSOR_RENAMES:
            for lane in range(NUM_LASERS):
                src_key = "%s_%d" % (src_prefix, lane)
                if src_key in raw:
                    result["%s_lane%d" % (dst_prefix, first_lane + lane)] = raw[src_key]
        if NVIDIA_CPO_ELS_MODULE_POWER in raw:
            result['power_consumption'] = raw[NVIDIA_CPO_ELS_MODULE_POWER]
        return result
