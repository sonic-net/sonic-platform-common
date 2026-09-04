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

from ..public.elsfp_cmis import ElsfpCmisApi
from ...fields import consts
from ...mem_maps.nvidia.cpo_els import (
    NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD,
    NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD,
    NVIDIA_ELS_VOLTAGE_FIELD,
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
# to the spec's els_* DOM_SENSOR prefix (1-indexed lane suffix, no underscore).
_ELS_LASER_DOM_SENSOR_RENAMES = (
    (NVIDIA_CPO_ELS_LASER_MPD,    'els_laser_mpd'),
    (NVIDIA_CPO_ELS_TEC_VOLTAGE,  'els_tec_voltage_laser'),
    (NVIDIA_CPO_ELS_LASER_HEALTH, 'els_health_value_laser'),
    (NVIDIA_CPO_ELS_TEC_HEALTH,   'els_tec_health_value_laser'),
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class NvidiaCpoElsCmisApi(ElsfpCmisApi):

    def get_els_status(self):
        """ELS module state, fault cause, and VCC for TRANSCEIVER_STATUS.

        Sources: NVIDIA B0 mirror (state / fault cause / VCC at 0xB0:144).
        """
        result = {}

        status = self.xcvr_eeprom.read(consts.TRANS_MODULE_STATUS_FIELD)
        if status:
            result['els_module_state'] = status.get(consts.MODULE_STATE, 'N/A')
            result['els_module_fault_cause'] = status.get(consts.MODULE_FAULT_CAUSE, 'N/A')
        else:
            result['els_module_state'] = 'Unknown'
            result['els_module_fault_cause'] = 'Unknown'

        vcc = self.xcvr_eeprom.read(consts.VOLTAGE_FIELD)
        result['els_vcc'] = vcc if vcc is not None else 'N/A'

        return result

    def get_els_dom_sensors(self):
        """ELS temperature + voltage from the standard CMIS slots (page 0x00).

        The B0 mirror is for the get_els_status / els_vcc path; these come
        from the actual standard slots (CUSTOM_MON @ 24 and VOLTAGE @ 16).
        """
        result = {}

        mons = self.xcvr_eeprom.read(NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD)
        if mons:
            result['els_temperature'] = mons.get(consts.CUSTOM_MON, 'N/A')

        volts = self.xcvr_eeprom.read(NVIDIA_ELS_VOLTAGE_FIELD)
        if volts:
            result['els_voltage'] = volts.get(consts.VOLTAGE_FIELD, 'N/A')

        return result

    def get_els_cmon_temp_thresholds(self):
        """ELS temperature thresholds from the standard Custom Monitor slot (0x02:168-175)."""
        thresholds = self.xcvr_eeprom.read(NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD)
        if not thresholds:
            return {
                'els_temphighalarm':   'N/A',
                'els_templowalarm':    'N/A',
                'els_temphighwarning': 'N/A',
                'els_templowwarning':  'N/A',
            }

        return {
            'els_temphighalarm':   thresholds.get(consts.CUSTOM_MON_HIGH_ALARM, 'N/A'),
            'els_templowalarm':    thresholds.get(consts.CUSTOM_MON_LOW_ALARM,  'N/A'),
            'els_temphighwarning': thresholds.get(consts.CUSTOM_MON_HIGH_WARN,  'N/A'),
            'els_templowwarning':  thresholds.get(consts.CUSTOM_MON_LOW_WARN,   'N/A'),
        }

    def get_els_dom_flags(self):
        """ELS custom-monitor alarm/warning flag bits (B0:139, MODULE_FLAG_BYTE3)."""
        flag_byte = self.xcvr_eeprom.read(consts.MODULE_FLAG_BYTE3)
        if flag_byte is None:
            return {}
        return {
            'els_custom_mon_high_alarm':   bool((flag_byte >> 4) & 1),
            'els_custom_mon_low_alarm':    bool((flag_byte >> 5) & 1),
            'els_custom_mon_high_warning': bool((flag_byte >> 6) & 1),
            'els_custom_mon_low_warning':  bool((flag_byte >> 7) & 1),
        }

    def get_els_info(self):
        """ELS identity (B1), type info (B0/B1), and HW rev (B2)."""
        result = {}

        admin = self.xcvr_eeprom.read(consts.ADMIN_INFO_FIELD)
        if admin:
            result['els_manufacturer'] = admin.get(consts.VENDOR_NAME_FIELD, 'N/A')
            result['els_vendor_oui']   = admin.get(consts.VENDOR_OUI_FIELD, 'N/A')
            result['els_model']        = admin.get(consts.VENDOR_PART_NO_FIELD, 'N/A')
            result['els_vendor_rev']   = admin.get(consts.VENDOR_REV_FIELD, 'N/A')
            result['els_serial']       = admin.get(consts.VENDOR_SERIAL_NO_FIELD, 'N/A')
            result['els_vendor_date']  = admin.get(consts.VENDOR_DATE_FIELD, 'N/A')
            result['els_connector']    = admin.get(consts.CONNECTOR_FIELD, 'N/A')
            result['els_type']         = admin.get(consts.ID_FIELD, 'N/A')
            result['els_type_abbrv_name'] = admin.get(consts.ID_ABBRV_FIELD, 'N/A')
            major = admin.get(consts.CMIS_MAJOR_REVISION)
            minor = admin.get(consts.CMIS_MINOR_REVISION)
            result['els_cmis_rev'] = (
                f"{major}.{minor}" if major is not None and minor is not None else 'N/A')


            ext_id = admin.get(consts.EXT_ID_FIELD)
            if isinstance(ext_id, dict):
                result['els_ext_identifier'] = ext_id.get(consts.POWER_CLASS_FIELD, 'N/A')
            else:
                result['els_ext_identifier'] = 'N/A'

            # cable_type has no standard CMIS counterpart and is not on the B1 mirror.
            result['els_cable_type'] = 'N/A'
        else:
            result['els_manufacturer'] = 'Unknown'
            result['els_vendor_oui'] = 'Unknown'
            result['els_model'] = 'Unknown'
            result['els_vendor_rev'] = 'Unknown'
            result['els_serial'] = 'Unknown'
            result['els_vendor_date'] = 'Unknown'
            result['els_connector'] = 'Unknown'
            result['els_type'] = 'Unknown'
            result['els_type_abbrv_name'] = 'Unknown'
            result['els_cmis_rev'] = 'Unknown'
            result['els_ext_identifier'] = 'Unknown'
            result['els_cable_type'] = 'Unknown'
            result['els_hardware_rev'] = 'Unknown'

        adv = self.xcvr_eeprom.read(consts.ADVERTISING_FIELD)
        if adv:
            major = adv.get(consts.HW_MAJOR_REV, 0)
            minor = adv.get(consts.HW_MINOR_REV, 0)
            result['els_hardware_rev'] = f"{major}.{minor}"
        else:
            result['els_hardware_rev'] = 'Unknown'

        return result

    def get_els_thresholds(self):
        """ELS supply-voltage thresholds from the standard CMIS slot (0x02:136-143)."""
        data = self.xcvr_eeprom.read(NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD)
        if not data:
            return {
                'els_vcchighalarm':   'N/A',
                'els_vcclowalarm':    'N/A',
                'els_vcchighwarning': 'N/A',
                'els_vcclowwarning':  'N/A',
            }
        return {
            'els_vcchighalarm':   data.get(consts.VOLTAGE_HIGH_ALARM_FIELD,   'N/A'),
            'els_vcclowalarm':    data.get(consts.VOLTAGE_LOW_ALARM_FIELD,    'N/A'),
            'els_vcchighwarning': data.get(consts.VOLTAGE_HIGH_WARNING_FIELD, 'N/A'),
            'els_vcclowwarning':  data.get(consts.VOLTAGE_LOW_WARNING_FIELD,  'N/A'),
        }

    def get_els_laser_monitoring(self, cap_mask=ELS_LASER_MONITORING_CAP_MASK_ALL,
                                 laser_mask=0x00):
        """CDB 0x9018: read NVIDIA ELS laser monitoring block (raw decoded reply)."""
        if self.cdb_handler is None:
            return {}

        payload = {
            "cap_mask":   cap_mask,
            "bank_id":    self.bank_id,
            "laser_mask": laser_mask,
        }

        try:
            ok = self.cdb_handler.send_cmd(CDB_READ_ELS_LASER_MONITORING_CMD,
                                           payload=payload)
        except Exception:
            logger.exception("CDB 0x%04x send failed",
                             CDB_READ_ELS_LASER_MONITORING_CMD)
            return {}
        if ok is not True:
            logger.warning("CDB 0x%04x returned non-success: %r",
                           CDB_READ_ELS_LASER_MONITORING_CMD, ok)
            return {}

        try:
            return self.cdb_handler.read_reply(CDB_READ_ELS_LASER_MONITORING_CMD) or {}
        except Exception:
            logger.exception("CDB 0x%04x read_reply failed",
                             CDB_READ_ELS_LASER_MONITORING_CMD)
            return {}

    def get_els_laser_dom_sensors(self):
        """Spec-aligned DOM_SENSOR projection of the CDB 0x9018 reply.

        Renames per-laser CDB field-name prefixes to els_* spec prefixes
        (lane index 1-indexed, no underscore) and surfaces module power
        as ``els_power_consumption``. Cap/bank/mask framing bytes are dropped.
        """
        raw = self.get_els_laser_monitoring()
        if not raw:
            return {}
        result = {}
        for src_prefix, dst_prefix in _ELS_LASER_DOM_SENSOR_RENAMES:
            for lane in range(NUM_LASERS):
                src_key = f"{src_prefix}_{lane}"
                if src_key in raw:
                    result[f"{dst_prefix}{lane + 1}"] = raw[src_key]
        if NVIDIA_CPO_ELS_MODULE_POWER in raw:
            result['els_power_consumption'] = raw[NVIDIA_CPO_ELS_MODULE_POWER]
        return result

    def get_transceiver_info(self):
        result = super().get_transceiver_info()
        result.update(self.get_els_info())
        return result

    def get_transceiver_dom_real_value(self):
        result = super().get_transceiver_dom_real_value()
        result.update(self.get_els_dom_sensors())
        result.update(self.get_els_laser_dom_sensors())
        return result

    def get_transceiver_threshold_info(self):
        result = super().get_transceiver_threshold_info()
        result.update(self.get_els_thresholds())
        result.update(self.get_els_cmon_temp_thresholds())
        return result

    def get_transceiver_dom_flags(self):
        result = super().get_transceiver_dom_flags()
        result.update(self.get_els_dom_flags())
        return result

    def get_transceiver_status(self):
        result = super().get_transceiver_status()
        result.update(self.get_els_status())
        return result
