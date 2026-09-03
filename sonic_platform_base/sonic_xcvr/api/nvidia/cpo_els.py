"""XcvrApi for the NVIDIA CPO External Laser Source (ELS).

Reserved for NVIDIA-specific overrides on top of ElsfpApi. The laser source is
described by the generic ELSFP tables as they stand, so nothing is overridden
yet; the vendor pages and the CDB laser monitoring projection land here.
"""
from ..public.elsfp import ElsfpApi


class NvidiaCpoElsCmisApi(ElsfpApi):
    pass
