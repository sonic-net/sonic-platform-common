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

Reserved for NVIDIA-specific overrides on top of CmisApi. The engine is a plain
CMIS module whose four banks are its four logical ports, so nothing is
overridden yet; the CDB-driven OE telemetry getter lands here.

CmisApi is the base rather than CpoCmisApi because CpoCmisApi overrides the
aggregate getters to read banked and non-banked halves separately. Adopting
that is a change in what a DOM pass reads, not a rename, so it belongs with the
work that needs the split rather than here.
"""
from ..public.cmis import CmisApi


class NvidiaCpoOeCmisApi(CmisApi):
    pass
