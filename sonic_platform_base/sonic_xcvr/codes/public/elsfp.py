"""
    elsfp.py

    Code definitions for ELSFP (External Laser Source Function Plug),
    per OIF-ELSFP-CMIS-01.0.
"""

from .cmis import CmisCodes


class ElsfpCodes(CmisCodes):
    CONTROL_MODE = {
        0: 'ACC',  # Automatic Current Control
        1: 'APC',  # Automatic Power Control
    }

    LANE_FAULT_CODE = {
        0: 'No alarm detected',
        1: 'Automatic Power Control (APC) control loop failure',
        2: 'Automatic Current Control (ACC) control loop failure',
        3: 'Reserved',
        4: 'Reserved',
        5: 'Reserved',
        6: 'Reserved',
        7: 'Reserved',
        8: 'Reserved',
        9: 'Vendor specific fault',
        10: 'Vendor specific fault',
        11: 'Vendor specific fault',
        12: 'Vendor specific fault',
        13: 'Vendor specific fault',
        14: 'Vendor specific fault',
        15: 'Vendor specific fault',
    }

    LANE_WARNING_CODE = {
        0: 'No warning detected',
        1: 'Automatic Power Control (APC) control loop warning',
        2: 'Automatic Current Control (ACC) control loop warning',
        3: 'Reserved',
        4: 'Reserved',
        5: 'Reserved',
        6: 'Reserved',
        7: 'Reserved',
        8: 'Reserved',
        9: 'Vendor specific warning',
        10: 'Vendor specific warning',
        11: 'Vendor specific warning',
        12: 'Vendor specific warning',
        13: 'Vendor specific warning',
        14: 'Vendor specific warning',
        15: 'Vendor specific warning',
    }

    LANE_STATE = {
        0: 'Lane Output off',
        1: 'Lane Output ramping',
        2: 'Lane Output on',
        3: 'Reserved',
    }
