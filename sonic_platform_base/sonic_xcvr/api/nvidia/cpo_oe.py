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
