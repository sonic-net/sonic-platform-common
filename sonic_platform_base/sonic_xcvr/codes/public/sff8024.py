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

    # TODO: Add other codes
