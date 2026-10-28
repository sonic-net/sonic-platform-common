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

"""XcvrMemMap for the NVIDIA CPO External Laser Source (ELS).

Registers the ELSFP pages 0x1A/0x1B, the NVIDIA vendor pages B0 (module status
mirror), B1 (identity mirror), B2 (advertising mirror) and B3 (thresholds
mirror), plus five NVIDIA-named groups that target *standard* CMIS slots on
pages 0x00 / 0x02 (ELS temperature/voltage value and thresholds, and the live
module state at page 0x00 byte 3). The NVIDIA group names keep the standard
slots from being merged with the B0/B3 mirrors into a multi-KB RegGroupField
span.

The default CMIS page 00h pages are deliberately not registered, following
DavissonTh6ElsfpMemMap: CMIS lower/upper memory is reached through the B0/B1
mirrors, so registering page 00h too would merge each mirror with its
standard counterpart.

B3 holds the standard CMIS thresholds page layout, so the standard thresholds
group resolves there rather than to page 0x02. Of page 0x02 itself, only the
temperature (Custom Monitor) and voltage thresholds are the ELS's.
"""

from ..public.cmis.pages import (
    ADMINISTRATIVE_PAGE,
    CmisPage,
    CmisAdministrativeLowerPage,
    CmisAdministrativeUpperPage,
    CmisAdvertisingPage,
    CmisThresholdsPage,
)
from ..public.cmis import CmisFlatMemMap
from ..public.cmis.elsfp.pages import (
    ElsfpAdvertisementsFlagsCtrlPage,
    ElsfpSetpointsMonitorsPage,
)
from ...fields import consts
from ...fields.scale_consts import (
    SCALE_100UV_TO_V,
    SCALE_1_OVER_256C_TO_C,
)
from ...fields.xcvr_field import CodeRegField, NumberRegField, RegBitField

NVIDIA_ELS_MODULE_STATUS_PAGE = 0xB0
NVIDIA_ELS_IDENTITY_PAGE = 0xB1
NVIDIA_ELS_ADVERTISING_PAGE = 0xB2
NVIDIA_ELS_THRESHOLDS_PAGE = 0xB3

NVIDIA_ELS_CUSTOM_MON_VALUE_FIELD = "NvidiaElsCustomMonValue"
NVIDIA_ELS_CUSTOM_MON_THRESHOLDS_FIELD = "NvidiaElsCustomMonThresholds"
NVIDIA_ELS_MODULE_STATE_FIELD = "NvidiaElsModuleState"
NVIDIA_ELS_VOLTAGE_FIELD = "NvidiaElsVoltage"
NVIDIA_ELS_VOLTAGE_THRESHOLDS_FIELD = "NvidiaElsVoltageThresholds"

class NvidiaCpoElsB0MirrorPage(CmisAdministrativeLowerPage):
    """CMIS lower-memory fields mirrored into the upper half of a vendor page.

    The B0 mirror reproduces the standard lower-memory layout (offsets 0-127)
    at offsets 128-255 of the vendor page, so shift sub-128 offsets up before
    delegating to the standard addressing. Standard usage at
    ``ADMINISTRATIVE_PAGE`` is unaffected.
    """

    def getaddr(self, offset, page_size=128):
        if self._page != ADMINISTRATIVE_PAGE and offset < 128:
            offset += 128
        return super(NvidiaCpoElsB0MirrorPage, self).getaddr(offset, page_size)


class NvidiaCpoElsModuleStatePage(CmisPage):
    """Live CMIS module state at page 0x00 byte 3, bits 1-3.

    The B0 copy of this byte is a static snapshot of the els state and does not follow
    the actual live module state of the vModule, so this reads the page 0x00 byte 3 instead.
    """

    def __init__(self, codes, bank=0):
        super(NvidiaCpoElsModuleStatePage, self).__init__(codes, page=0, bank=bank)
        self.fields[NVIDIA_ELS_MODULE_STATE_FIELD] = [
            CodeRegField(consts.MODULE_STATE, self.getaddr(3), codes.MODULE_STATE,
                         *(RegBitField("Bit%d" % bit, bit) for bit in range(1, 4))),
        ]


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


class NvidiaCpoElsCmisMemMap(CmisFlatMemMap):
    def __init__(self, codes, bank=0):
        # Bypass CmisFlatMemMap.__init__ so we don't register the default CMIS
        # flat memory pages — the ELS reaches CMIS lower/upper memory through
        # its B0/B1 mirrors, and registering page 00h as well would merge each
        # mirror with its standard counterpart into a multi-KB RegGroupField.
        self._bank = bank
        super(CmisFlatMemMap, self).__init__(codes)
        self.pages = []

        self.add_pages(
            NvidiaCpoElsB0MirrorPage(codes, page=NVIDIA_ELS_MODULE_STATUS_PAGE),
            CmisAdministrativeUpperPage(codes, page=NVIDIA_ELS_IDENTITY_PAGE),
            CmisAdvertisingPage(codes,         page=NVIDIA_ELS_ADVERTISING_PAGE),
            CmisThresholdsPage(codes,          page=NVIDIA_ELS_THRESHOLDS_PAGE),
            ElsfpAdvertisementsFlagsCtrlPage(codes, bank=bank),  # 0x1A
            ElsfpSetpointsMonitorsPage(codes, bank=bank),        # 0x1B
            NvidiaCpoElsModuleStatePage(codes),
            NvidiaCpoElsCustomMonValuePage(codes),
            NvidiaCpoElsCustomMonThresholdsPage(codes),
            NvidiaCpoElsVoltagePage(codes),
            NvidiaCpoElsVoltageThresholdsPage(codes)
        )
