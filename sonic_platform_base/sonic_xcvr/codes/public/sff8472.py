"""
    sff8472.py

    SFF-8472 Rev 12.3
"""

from .sff8024 import Sff8024

class Sff8472Codes(Sff8024):
    ENCODINGS = {
        0: "Unspecified",
        1: "8B/10B",
        2: "4B/5B",
        3: "NRZ",
        4: "Manchester",
        5: "SONET Scrambled",
        6: "64B/66B",
        7: "256B/257B (transcoded FEC-enabled data)",
        8: "PAM4",
    }

    EXT_IDENTIFIERS = {
        0: "GBIC definition is not specified",
        1: "GBIC is compliant with MOD_DEF 1",
        2: "GBIC is compliant with MOD_DEF 2",
        3: "GBIC is compliant with MOD_DEF 3",
        4: "GBIC/SFP defined by two-wire interface ID",
        5: "GBIC is compliant with MOD_DEF 5",
        6: "GBIC is compliant with MOD_DEF 6",
        7: "GBIC is compliant with MOD_DEF 7"
    }

    POWER_CLASSES = {
        0: "Power Class 1 Module (1.5W max.)",
        64: "Power Class 2 Module (2.0W max.)",
        128: "Power Class 3 Module (2.5W max.)",
        192: "Power Class 4 Module (3.5W max.)",
        193: "Power Class 5 Module (4.0W max.)",
        194: "Power Class 6 Module (4.5W max.)",
        195: "Power Class 7 Module (5.0W max.)",
        32: "Power Class 8 Module",
    }

    ETHERNET_10G_COMPLIANCE = {
        1: "10GBASE-SR",
        2: "10GBASE-LR",
        4: "10GBASE-LRM",
        8: "10GBASE-ER",
    }

    INFINIBAND_COMPLIANCE = {
        1: "1X Copper Passive",
        2: "1X Copper Active",
        4: "1X LX",
        8: "1X SX"
    }

    ESCON_COMPLIANCE = {
        2: "ESCON MMF, 1310nm LED",
        1: "ESCON SMF, 1310nm Laser"
    }

    SONET_COMPLIANCE = {
        1: "OC 3 short reach",
        2: "OC 3, single mode, intermediate reach",
        4: "OC 3, single mode, long reach",
        16: "OC 12, short reach",
        32: "OC 12, single mode, intermediate reach",
        64: "OC 12, single mode, long reach",
        256: "OC 48, short reach",
        512: "OC 48, intermediate reach",
        1024: "OC 48, long reach",
        2048: "SONET reach specifier bit 2",
        4096: "SONET reach specifier bit 1",
        8192: "OC 192, short reach"
    }

    ETHERNET_COMPLIANCE = {
        1: "1000BASE-SX",
        2: "1000BASE-LX",
        4: "1000BASE-CX",
        8: "1000BASE-T",
        16: "100BASE-LX/LX10",
        32: "100BASE-FX",
        64: "BASE-BX10",
        128: "BASE-PX"
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
        8: "Electrical intra-enclosure (EL)",
        16: "Electrical inter-enclosure (EL)",
        32: "Longwave laser (LC)",
        64: "Shortwave laser, linear RX (SA)"
    }

    SFP_CABLE_TECH = {
        4: "Passive Cable",
        8: "Active Cable"
    }

    FIBRE_CHANNEL_TRANSMISSION_MEDIA = {
        1: "Single Mode (SM)",
        4: "Multi-mode 50m (M5, M5E)",
        8: "Multi-mode 62.5m (M6)",
        16: "Video Coax (TV)",
        32: "Miniature Coax (MI)",
        64: "Twisted Pair (TP",
        128: "Twin Axial Pair (TW)"
    }

    FIBRE_CHANNEL_SPEED = {
        1: "100 MBytes/sec",
        2: "Extended",
        4: "200 MBytes/sec",
        8: "3200 MBytes/sec",
        16: "400 MBytes/sec",
        32: "1600 MBytes/sec",
        64: "800 MBytes/sec",
        128: "1200 MBytes/sec"
    }

    RATE_IDENTIFIERS = {
        1: "SFF-8079 (4/2/1G Rate_Select & AS0/AS1)",
        2: "SFF-8431 (8/4/2G Rx Rate_Select only)",
        4: "SFF-8431 (8/4/2G Tx Rate_Select only)",
        6: "SFF-8431 (8/4/2G Independent Rx & Tx Rate_select)",
        8: "FC-PI-5 (16/8/4G Rx Rate_select only) High=16G only, Low=8G/4G",
        10: "FC-PI-5 (16/8/4G Independent Rx, Tx Rate_select) High=16G only, Low=8G/4G",
        12: "FC-PI-6 (32/16/8 Independent Rx, Tx Rate_select) High=32G only, Low=16G/8G",
        14: "10/8G Rx and Tx Rate_Select controlling the operation or locking modes of the internal signal conditioner, retimer or CDR",
        16: "FC-PI-7 (64/32/16 Independent Rx, Tx Rate_select) High=32GFC and 64GFC, Low=16GFC",
    }
