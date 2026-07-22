"""
    cmis.elsfp package

    Re-exports ElsfpMemMap so existing imports of the form
    `from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.elsfp import X`
    keep resolving after the elsfp.py module became the elsfp/ package.
"""

from .elsfp import ElsfpMemMap
