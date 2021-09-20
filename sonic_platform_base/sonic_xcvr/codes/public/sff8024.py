"""
    sff8024.py

    Implementation of SFF-8024 Rev 4.8a
"""

from ..xcvr_codes import XcvrCodes

class Sff8024(XcvrCodes):
    XCVR_IDENTIFIERS = {
        0: 'Unknown or unspecified',
        1: 'GBIC',
        2: 'Module/connector soldered to motherboard',
        3: 'SFP/SFP+/SFP28',
        4: '300 pin XBI',
        5: 'XENPAK',
        6: 'XFP',
        7: 'XFF',
        8: 'XFP-E',
        9: 'XPAK',
        10: 'X2',
        11: 'DWDM-SFP/SFP+',
        12: 'QSFP',
        13: 'QSFP+ or later with SFF-8636 or SFF-8436',
        14: 'CXP or later',
        15: 'Shielded Mini Multilane HD 4X',
        16: 'Shielded Mini Multilane HD 8X',
        17: 'QSFP28 or later',
        18: 'CXP2 (aka CXP28) or later',
        19: 'CDFP (Style 1/Style2)',
        20: 'Shielded Mini Multilane HD 4X Fanout Cable',
        21: 'Shielded Mini Multilane HD 8X Fanout Cable',
        22: 'CDFP (Style 3)',
        23: 'microQSFP',
        24: 'QSFP-DD Double Density 8X Pluggable Transceiver',
        25: 'OSFP 8X Pluggable Transceiver',
        26: 'SFP-DD Double Density 2X Pluggable Transceiver',
        27: 'DSFP Dual Small Form Factor Pluggable Transceiver',
        28: 'x4 MiniLink/OcuLink',
        29: 'x8 MiniLink',
        30: 'QSFP+ or later with CMIS'
    }

    XCVR_IDENTIFIER_ABBRV = {
        0: 'Unknown',
        1: 'GBIC',
        2: 'Soldered',
        3: 'SFP',
        4: 'XBI300',
        5: 'XENPAK',
        6: 'XFP',
        7: 'XFF',
        8: 'XFP-E',
        9: 'XPAK',
        10: 'X2',
        11: 'DWDM-SFP',
        12: 'QSFP',
        13: 'QSFP+',
        14: 'CXP',
        15: 'HD4X',
        16: 'HD8X',
        17: 'QSFP28',
        18: 'CXP2',
        19: 'CDFP-1/2',
        20: 'HD4X-Fanout',
        21: 'HD8X-Fanout',
        22: 'CDFP-3',
        23: 'MicroQSFP',
        24: 'QSFP-DD',
        25: 'OSFP-8X',
        26: 'SFP-DD',
        27: 'DSFP',
        28: 'Link-x4',
        29: 'Link-x8',
        30: 'QSFP+',
    }

    CONNECTORS = {
        0: 'Unknown or unspecified',
        1: 'SC',
        2: 'FC Style 1 copper connector',
        3: 'FC Style 2 copper connector',
        4: 'BNC/TNC',
        5: 'FC coax headers',
        6: 'Fiberjack',
        7: 'LC',
        8: 'MT-RJ',
        9: 'MU',
        10: 'SG',
        11: 'Optical Pigtail',
        12: 'MPO 1x12',
        13: 'MPO 2x16',
        32: 'HSSDC II',
        33: 'Copper pigtail',
        34: 'RJ45',
        35: 'No separable connector',
        36: 'MXC 2x16',
        37: 'CS optical connector',
        38: 'SN optical connector',
        39: 'MPO 2x12',
        40: 'MPO 1x16',
    }

    ENCODINGS = {
        0: "Unspecified",
        1: "8B/10B",
        2: "4B/5B",
        3: "NRZ",
        # 4-6 differ between 8472 and 8436/8636
        7: "256B/257B (transcoded FEC-enabled data)",
        8: "PAM4",
    }


    # TODO: Add other codes
