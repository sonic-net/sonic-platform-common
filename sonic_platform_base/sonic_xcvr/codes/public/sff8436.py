from .sff8024 import Sff8024

class Sff8436Codes(Sff8024):
    ENCODINGS = {
        0: "Unspecified",
        1: "8B/10B",
        2: "4B/5B",
        3: "NRZ",
        4: "SONET Scrambled",
        5: "64B/66B",
        6: "Manchester",
        7: "256B/257B (transcoded FEC-enabled data)",
        8: "PAM4",
    }

    POWER_CLASSES = {
        0: "Power Class 1 Module (1.5W max. Power consumption)",
        1: "Power Class 2 Module (2.0W max. Power consumption)",
        2: "Power Class 3 Module (2.5W max. Power consumption)",
        3: "Power Class 4 Module (3.5W max. Power consumption)",
    }

    CLEI_CODE = {
        0: "No CLEI code present in Page 02h",
        1: "CLEI code present in Page 02h"
    }

    CDR_TX = {
        0: "No CDR in TX",
        1: "CDR present in TX"
    }

    CDR_RX = {
        0: "No CDR in RX",
        1: "CDR present in RX"
    }

    ETHERNET_10_40G_COMPLIANCE = {
        1: "40G Active Cable (XLPPI)",
        2: "40GBASE-LR4",
        4: "40GBASE-SR4",
        8: "40GBASE-CR4",
        16: "10GBASE-SR",
        32: "10GBASE-LR",
        64: "10GBASE-LRM"
    }

    SONET_COMPLIANCE = {
        1: "OC 48 short reach",
        2: "OC 48, intermediate reach",
        4: "OC 48, long reach",
        16: "40G OTN (OTU3B/OTU3C)"
    }

    SAS_SATA_COMPLIANCE = {
        8: "SAS 3.0G",
        16: "SAS 6.0G",
    }

    GIGABIT_ETHERNET_COMPLIANCE = {
        1: "1000BASE-SX",
        2: "1000BASE-LX",
        4: "1000BASE-CX",
        8: "1000BASE-T"
    }

    FIBRE_CHANNEL_LINK_LENGTH = {
        1: "Medium (M)",
        2: "Long distance (L)",
        4: "Intermediate distance (I)",
        8: "Short distance (S)",
        16: "Very long distance (V)"
    }

    FIBRE_CHANNEL_TRANSMITTER_TECH = {
        1: "Longwave Laser (LL)",
        2: "Shortwave laser w OFC (SL)",
        4: "Shortwave laser w/o OFC (SN)",
        8: "Electrical intra-enclosure",
        16: "Electrical inter-enclosure (EN)",
        32: "Longwave laser (LC)"
    }

    FIBRE_CHANNEL_TRANSMISSION_MEDIA = {
        1: "Single Mode (SM)",
        2: "Multi-mode 50 um (OM3)",
        4: "Multi-mode 50m (M5)",
        8: "Multi-mode 62.5m (M6)",
        16: "Video Coax (TV)",
        32: "Miniature Coax (MI)",
        64: "Shielded Twisted Pair (TP",
        128: "Twin Axial Pair (TW)"
    }

    FIBRE_CHANNEL_SPEED = {
        1: "100 Mbytes/Sec",
        4: "200 Mbytes/Sec",
        16: "400 Mbytes/Sec",
        32: "1600 Mbytes/Sec",
        64: "800 Mbytes/Sec",
        128: "1200 Mbytes/Sec"
    }

    EXT_RATESELECT_COMPLIANCE = {
        0: "QSFP+ Rate Select Version 1"
    }
