from .sff8024 import Sff8024

class CmisCodes(Sff8024):
    POWER_CLASSES = {
        0: "Power Class 1",
        1: "Power Class 2",
        2: "Power Class 3",
        3: "Power Class 4",
        4: "Power Class 5",
        5: "Power Class 6",
        6: "Power Class 7",
        7: "Power Class 8"
    }

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

    MODULE_FAULT_CAUSE = {
        0: 'No Fault detected',
        1: 'TEC runawawy',
        2: 'Data memory corrupted',
        3: 'Program memory corrupted',
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

    VDM_TYPE = {
        # VDM_ID: [VDM_NAME, DATA_TYPE, SCALE]
        1: ['Laser Age [%]', 'U16', 1],
        2: ['TEC Current [%]', 'S16', 100.0/32767],
        3: ['Laser Frequency Error [MHz]', 'S16', 10],
        4: ['Laser Temperature [C]', 'S16', 1.0/256],
        5: ['eSNR Media Input [dB]', 'U16', 1.0/256],
        6: ['eSNR Host Input [dB]', 'U16', 1.0/256],
        7: ['PAM4 Level Transition Parameter Media Input [dB]', 'U16', 1.0/256],
        8: ['PAM4 Level Transition Parameter Host Input [dB]', 'U16', 1.0/256],
        9: ['Pre-FEC BER Minimum Media Input', 'F16', 1],
        10: ['Pre-FEC BER Minimum Host Input', 'F16', 1],
        11: ['Pre-FEC BER Maximum Media Input', 'F16', 1],
        12: ['Pre-FEC BER Maximum Host Input', 'F16', 1],
        13: ['Pre-FEC BER Average Media Input', 'F16', 1],
        14: ['Pre-FEC BER Average Host Input', 'F16', 1],
        15: ['Pre-FEC BER Current Value Media Input', 'F16', 1],
        16: ['Pre-FEC BER Current Value Host Input', 'F16', 1],
        17: ['Errored Frames Minimum Media Input', 'F16', 1],
        18: ['Errored Frames Minimum Host Input', 'F16', 1],
        19: ['Errored Frames Maximum Media Input', 'F16', 1],
        20: ['Errored Frames Maximum Host Input', 'F16', 1],
        21: ['Errored Frames Average Media Input', 'F16', 1],
        22: ['Errored Frames Average Host Input', 'F16', 1],
        23: ['Errored Frames Current Value Media Input', 'F16', 1],
        24: ['Errored Frames Current Value Host Input', 'F16', 1],
        128: ['Modulator Bias X/I [%]', 'U16', 100.0/65535],
        129: ['Modulator Bias X/Q [%]', 'U16', 100.0/65535],
        130: ['Modulator Bias Y/I [%]', 'U16', 100.0/65535],
        131: ['Modulator Bias Y/Q [%]', 'U16', 100.0/65535],
        132: ['Modulator Bias X_Phase [%]', 'U16', 100.0/65535],
        133: ['Modulator Bias Y_Phase [%]', 'U16', 100.0/65535],
        134: ['CD high granularity, short link [ps/nm]', 'S16', 1],
        135: ['CD low granularity, long link [ps/nm]', 'S16', 20],
        136: ['DGD [ps]', 'U16', 0.01],
        137: ['SOPMD [ps^2]', 'U16', 0.01],
        138: ['PDL [dB]', 'U16', 0.1],
        139: ['OSNR [dB]', 'U16', 0.1],
        140: ['eSNR [dB]', 'U16', 0.1],
        141: ['CFO [MHz]', 'S16', 1],
        142: ['EVM_modem [%]', 'U16', 100.0/65535],
        143: ['Tx Power [dBm]', 'S16', 0.01],
        144: ['Rx Total Power [dBm]', 'S16', 0.01],
        145: ['Rx Signal Power [dBm]', 'S16', 0.01],
        146: ['SOP ROC [krad/s]', 'U16', 1],
        147: ['MER [dB]', 'U16', 0.1]
    }

    CDB_FAIL_STATUS = {
        0: 'reserved',
        1: 'CMDID unknown',
        2: 'Parameter range error or parameter not supported',
        3: 'Previous CMD was not properly ABORTED',
        4: 'Command checking time out',
        5: 'CdbChkCode Error',
        6: 'Password related error',
        7: 'Command not compatible with operating status'
    }

    DP_PATH_TIMINGS = {
        0: '1',
        1: '5',
        2: '10',
        3: '50',
        4: '100',
        5: '500',
        6: '1000',
        7: '5000',
        8: '10000',
        9: '60000',
        10: '300000',
        11: '600000',
        12: '3000000',
        13: '6000000',
        14: '0',
        15: '0'
    }

    # TODO: Add other codes
