#! /usr/bin/env python
#----------------------------------------------------------------------------
# SFF-8024 Rev 4.5
#----------------------------------------------------------------------------

from __future__ import print_function

type_of_transceiver = {
    '00': 'Unknown or unspecified',
    '01': 'GBIC',
    '02': 'Module/connector soldered to motherboard',
    '03': 'SFP/SFP+/SFP28',
    '04': '300 pin XBI',
    '05': 'XENPAK',
    '06': 'XFP',
    '07': 'XFF',
    '08': 'XFP-E',
    '09': 'XPAK',
    '0a': 'X2',
    '0b': 'DWDM-SFP/SFP+',
    '0c': 'QSFP',
    '0d': 'QSFP+ or later',
    '0e': 'CXP or later',
    '0f': 'Shielded Mini Multilane HD 4X',
    '10': 'Shielded Mini Multilane HD 8X',
    '11': 'QSFP28 or later',
    '12': 'CXP2 (aka CXP28) or later',
    '13': 'CDFP (Style 1/Style2)',
    '14': 'Shielded Mini Multilane HD 4X Fanout Cable',
    '15': 'Shielded Mini Multilane HD 8X Fanout Cable',
    '16': 'CDFP (Style 3)',
    '17': 'microQSFP',
    '18': 'QSFP-DD Double Density 8X Pluggable Transceiver',
    '19': 'OSFP 8X Pluggable Transceiver',
    '1a': 'SFP-DD Double Density 2X Pluggable Transceiver'
}
