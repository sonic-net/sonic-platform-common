#----------------------------------------------------------------------------
# QSFP-DD 8X Transceiver (QSFP Double Density)
#----------------------------------------------------------------------------

from __future__ import print_function

try:
    from .sff8024 import type_of_transceiver    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import type_abbrv_name    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sffbase import sffbase    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
except ImportError as e:
    raise ImportError ("%s - required module not found" % e)

class inf8628InterfaceId(sffbase):

    def decode_revision_compliance(self, eeprom_data, offset, size):
        return '%c.%c' % (eeprom_data[offset][0], eeprom_data[offset][1])

    def decode_module_state(self, eeprom_data, offset, size):
        module_state_byte = eeprom_data[offset]
        module_state = int(module_state_byte, 16) & 14
        if module_state == 2:
            return 'Low Power State'
        elif module_state == 4:
            return 'Power Up State'
        elif module_state == 6:
            return 'Ready State'
        elif module_state == 8:
            return 'Power Down State'
        elif module_state == 10:
            return 'Fault State'
        return 'Unknown State %s' % module_state

    version = '1.0'

    interface_id = {
            'Identifier':
                {'offset': 0,
                 'size': 1,
                 'type': 'enum',
                 'decode': type_of_transceiver},
            'Revision Compliance':
                {'offset': 1,
                 'type': 'func',
                 'decode': {'func': decode_revision_compliance}},
            'Module State':
                {'offset': 3,
                 'type': 'func',
                 'decode': {'func': decode_module_state}},
            'Interrupt Asserted':
                {'offset': 3,
                 'bit': 0,
                 'type': 'bitvalue'},
            'Vendor Name':
                {'offset': 129,
                 'size': 16,
                 'type': 'str'},
            'Vendor Part Number':
                {'offset': 148,
                 'size': 16,
                 'type': 'str'},
            'Vendor Revision':
                {'offset': 164,
                 'size': 2,
                 'type': 'str'},
            'Vendor Serial Number':
                {'offset': 166,
                 'size': 16,
                 'type': 'str'},
            }

    sfp_type = {
        'type':
            {'offset': 0,
             'size': 1,
             'type': 'enum',
             'decode': type_of_transceiver}
        }

    sfp_type_abbrv_name = {
        'type_abbrv_name':
            {'offset': 0,
             'size': 1,
             'type': 'enum',
             'decode': type_abbrv_name}
        }

    vendor_name = {
        'Vendor Name':
            {'offset': 0,
             'size': 16,
             'type': 'str'}
        }

    vendor_pn = {
        'Vendor PN':
            {'offset': 0,
             'size': 16,
             'type': 'str'}
        }

    vendor_rev = {
        'Vendor Rev':
            {'offset': 0,
             'size': 2,
             'type': 'str'}
        }

    vendor_sn = {
        'Vendor SN':
            {'offset': 0,
             'size': 16,
             'type': 'str'}
        }

    def __init__(self, eeprom_raw_data=None):
        self.interface_data = None
        start_pos = 0

        if eeprom_raw_data is not None:
            self.interface_data = sffbase.parse(self,
                            self.interface_id,
                            eeprom_raw_data,
                            start_pos)

    def parse(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.interface_id, eeprom_raw_data, start_pos)

    def parse_sfp_type(self, type_raw_data, start_pos):
        return sffbase.parse(self, self.sfp_type, type_raw_data, start_pos)

    def parse_sfp_type_abbrv_name(self, type_raw_data, start_pos):
        return sffbase.parse(self, self.sfp_type_abbrv_name, type_raw_data, start_pos)

    def parse_vendor_name(self, name_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_name, name_raw_data, start_pos)

    def parse_vendor_rev(self, rev_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_rev, rev_raw_data, start_pos)

    def parse_vendor_pn(self, pn_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_pn, pn_raw_data, start_pos)

    def parse_vendor_sn(self, sn_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_sn, sn_raw_data, start_pos)

    def dump_pretty(self):
        if self.interface_data is None:
            print('Object not initialized, nothing to print')
            return
        sffbase.dump_pretty(self, self.interface_data)

    def get_calibration_type(self):
        return self.calibration_type

    def get_data(self):
        return self.interface_data

    def get_data_pretty(self):
        return sffbase.get_data_pretty(self, self.interface_data)
