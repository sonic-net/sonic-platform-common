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

short_type_name = {
    '00': 'Unknown',
    '01': 'GBIC',
    '02': 'Soldered',
    '03': 'SFP',
    '04': 'XBI300',
    '05': 'XENPAK',
    '06': 'XFP',
    '07': 'XFF',
    '08': 'XFP-E',
    '09': 'XPAK',
    '0a': 'X2',
    '0b': 'DWDM-SFP',
    '0c': 'QSFP',
    '0d': 'QSFP+',
    '0e': 'CXP',
    '0f': 'HD4X',
    '10': 'HD8X',
    '11': 'QSFP28',
    '12': 'CXP2',
    '13': 'CDFP-1/2',
    '14': 'HD4X-Fanout',
    '15': 'HD8X-Fanout',
    '16': 'CDFP-3',
    '17': 'microQSFP',
    '18': 'QSFP-DD',
    '19': 'OSFP-8X',
    '1a': 'SFP-DD'
}
