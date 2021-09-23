"""
    cmis_code.py

    Implementation of dictionaries used in CMIS
"""
from ..xcvr_codes import XcvrCodes

class CmisCode(XcvrCodes):
    MEDIA_INTERFACE_TECH = {
    0: '850 nm VCSEL',
    1: '1310 nm VCSEL',
    2: '1550 nm VCSEL',
    3: '1310 nm FP',
    4: '1310 nm DFB',
    5: '1550 nm DFB',
    6: '1310 nm EML',
    7: '1550 nm EML',
    8: 'Others',
    9: '1490 nm DFB',
    10: 'Copper cable unequalized',
    11: 'Copper cable passive equalized',
    12: 'Copper cable, near and far end limiting active equalizers',
    13: 'Copper cable, far end limiting active equalizers',
    14: 'Copper cable, near end limiting active equalizers',
    15: 'Copper cable, linear active equalizers',
    16: 'C-band tunable laser',
    17: 'L-band tunable laser',       
    }

    MODULE_STATE = {
    1: 'ModuleLowPwr',
    2: 'ModulePwrUp',
    3: 'ModuleReady',
    4: 'ModulePwrDn',
    5: 'ModuleFault',
    }

    DATAPATH_STATE = {
    1: 'DataPathDeactivated',
    2: 'DataPathInit',
    3: 'DataPathDeinit',
    4: 'DataPathActivated',
    5: 'DataPathTxTurnOn', 
    6: 'DataPathTxTurnOff', 
    7: 'DataPathInitialized', 
    }

    CONFIG_STATUS = {
    0: 'ConfigUndefined',
    1: 'ConfigSuccess',
    2: 'ConfigRejected',
    3: 'ConfigRejectedInvalidAppSel',
    4: 'ConfigRejectedInvalidDataPath',
    5: 'ConfigRejectedInvalidSI',
    6: 'ConfigRejectedLaneInUse',
    7: 'ConfigRejectedPartialDataPath',
    12: 'ConfigInProgress',
    }

    # TODO: Add other codes