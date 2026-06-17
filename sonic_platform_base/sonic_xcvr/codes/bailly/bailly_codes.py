from ..public.cmis import CmisCodes

class BaillyCodes(CmisCodes):
    # Vendor specific implementation to be added here
    XCVR_IDENTIFIERS = {
        **CmisCodes.XCVR_IDENTIFIERS,
        128: 'CPO Bailly',
    }

    XCVR_IDENTIFIER_ABBRV = {
        **CmisCodes.XCVR_IDENTIFIER_ABBRV,
        128: 'QSFP-DD',
    }

    HOST_ELECTRICAL_INTERFACE = {
        **CmisCodes.HOST_ELECTRICAL_INTERFACE,
        253: 'Bailly-Reserved-1',
        254: 'Bailly-Reserved-2',
    }

    SM_MEDIA_INTERFACE = {
        **CmisCodes.SM_MEDIA_INTERFACE,
        193: 'Bailly-800G-2xFR4',
        253: 'Bailly-Reserved-LC-1',
        254: 'Bailly-Reserved-LC-2',
    }

    LASER_WAVELENGTH_GRID = {
        0: "CWDM4",
        1: "DR4",
    }

    LASER_COUNT = {
        code: code + 1 for code in range(16)
    }

    POWER_MODE = {
        0: "High power mode",
        1: "Low power mode",
    }

    INTERRUPT_STATUS = {
        0: "Interrupt event occurred",
        1: "Interrupt event cleared",
    }

    LASER_DISABLE_CONTROL = {
        0: "Enable",
        1: "Disable",
    }

    LASER_ACTIVE_STATUS = {
        0: "Inactive",
        1: "Active",
    }

    LASER_POWER_MODE_ENABLE = {
        0: "Disable",
        1: "Enable",
    }

    MAX_BANKS_SUPPORTED = {
        **CmisCodes.MAX_BANKS_SUPPORTED,
        3: 8,
    }

