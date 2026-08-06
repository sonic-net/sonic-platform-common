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

from ..public.cmis_pages.base import CmisPage
from ..public.cmis_pages.cmis_pages import (
    CmisAdministrativeLowerPage,
    CmisAdministrativeUpperPage,
    CmisAdvertisingPage,
)
from ..public.elsfp_cmis import ElsfpCmisMemMap
from ...fields import consts
from ...fields.scale_consts import (
    SCALE_100UV_TO_V,
    SCALE_1_OVER_256C_TO_C,
)
from ...fields.xcvr_field import NumberRegField

NVIDIA_ELS_MODULE_STATUS_PAGE = 0xB0
NVIDIA_ELS_IDENTITY_PAGE = 0xB1
NVIDIA_ELS_ADVERTISING_PAGE = 0xB2
NVIDIA_ELS_THRESHOLDS_PAGE = 0xB3

NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD = "NvidiaElsCustomMonValue"
NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD = "NvidiaElsCustomMonThresholds"
NVIDIA_ELS_VOLTAGE_FIELD = "NvidiaElsVoltage"
NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD = "NvidiaElsVoltageThresholds"


class NvidiaCpoElsCustomMonValuePage(CmisPage):
    """ELS Custom Monitor value at page 0x00 byte 24 (int16, 1/256 deg C per LSB)."""

    def __init__(self, codes, bank=0):
        super(NvidiaCpoElsCustomMonValuePage, self).__init__(codes, page=0, bank=bank)
        self.fields[NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD] = [
            NumberRegField(consts.CUSTOM_MON, self.getaddr(24),
                           size=2, format=">h", scale=SCALE_1_OVER_256C_TO_C),
        ]


class NvidiaCpoElsCustomMonThresholdsPage(CmisPage):
    """ELS Custom Monitor thresholds at page 0x02 bytes 168-175 (int16, 1/256 deg C per LSB)."""

    def __init__(self, codes, bank=0):
        super(NvidiaCpoElsCustomMonThresholdsPage, self).__init__(codes, page=0x02, bank=bank)
        self.fields[NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD] = [
            NumberRegField(consts.CUSTOM_MON_HIGH_ALARM, self.getaddr(168), size=2, format=">h", scale=SCALE_1_OVER_256C_TO_C),
            NumberRegField(consts.CUSTOM_MON_LOW_ALARM,  self.getaddr(170), size=2, format=">h", scale=SCALE_1_OVER_256C_TO_C),
            NumberRegField(consts.CUSTOM_MON_HIGH_WARN,  self.getaddr(172), size=2, format=">h", scale=SCALE_1_OVER_256C_TO_C),
            NumberRegField(consts.CUSTOM_MON_LOW_WARN,   self.getaddr(174), size=2, format=">h", scale=SCALE_1_OVER_256C_TO_C),
        ]


class NvidiaCpoElsVoltagePage(CmisPage):
    """ELS Voltage at page 0x00 byte 16 (u16, scale 10000 -> Volts)."""

    def __init__(self, codes, bank=0):
        super(NvidiaCpoElsVoltagePage, self).__init__(codes, page=0, bank=bank)
        self.fields[NVIDIA_ELS_VOLTAGE_FIELD] = [
            NumberRegField(consts.VOLTAGE_FIELD, self.getaddr(16),
                           size=2, format=">H", scale=SCALE_100UV_TO_V),
        ]


class NvidiaCpoElsVoltageThresholdsPage(CmisPage):
    """ELS Voltage thresholds at page 0x02 bytes 136-143 (u16, scale 10000 -> Volts)."""

    def __init__(self, codes, bank=0):
        super(NvidiaCpoElsVoltageThresholdsPage, self).__init__(codes, page=0x02, bank=bank)
        self.fields[NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD] = [
            NumberRegField(consts.VOLTAGE_HIGH_ALARM_FIELD,   self.getaddr(136), size=2, format=">H", scale=SCALE_100UV_TO_V),
            NumberRegField(consts.VOLTAGE_LOW_ALARM_FIELD,    self.getaddr(138), size=2, format=">H", scale=SCALE_100UV_TO_V),
            NumberRegField(consts.VOLTAGE_HIGH_WARNING_FIELD, self.getaddr(140), size=2, format=">H", scale=SCALE_100UV_TO_V),
            NumberRegField(consts.VOLTAGE_LOW_WARNING_FIELD,  self.getaddr(142), size=2, format=">H", scale=SCALE_100UV_TO_V),
        ]


class NvidiaCpoElsCmisMemMap(ElsfpCmisMemMap):
    def _build_pages(self, codes):
        pages = super(NvidiaCpoElsCmisMemMap, self)._build_pages(codes)
        pages.extend([
            CmisAdministrativeLowerPage(codes, page=NVIDIA_ELS_MODULE_STATUS_PAGE, bank=self.bank),
            CmisAdministrativeUpperPage(codes, page=NVIDIA_ELS_IDENTITY_PAGE,      bank=self.bank),
            CmisAdvertisingPage(codes,         page=NVIDIA_ELS_ADVERTISING_PAGE,   bank=self.bank),
            # B3 thresholds-mirror intentionally NOT registered (see module docstring).
            NvidiaCpoElsCustomMonValuePage(codes,                                  bank=self.bank),
            NvidiaCpoElsCustomMonThresholdsPage(codes,                             bank=self.bank),
            NvidiaCpoElsVoltagePage(codes,                                         bank=self.bank),
            NvidiaCpoElsVoltageThresholdsPage(codes,                               bank=self.bank),
        ])
        return pages
