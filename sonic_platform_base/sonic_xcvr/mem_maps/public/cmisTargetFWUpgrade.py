"""
    cmisTargetFWUpgrade.py

    Implementation of memory map for CMIS based modules supporting firmware
    upgrade of remote target from the local target itself.
"""

from .cmis import CmisMemMap

class CmisTargetFWUpgradeMemMap(CmisMemMap):
    # Vendor agnostic implementation to be added here
    pass
