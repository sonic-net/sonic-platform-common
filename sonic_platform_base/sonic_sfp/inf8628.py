#----------------------------------------------------------------------------
# QSFP-DD 8X Transceiver (QSFP Double Density)
#----------------------------------------------------------------------------

from __future__ import print_function

try:
    from .sff8024 import type_of_transceiver    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import type_abbrv_name    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import type_of_media_interface
    from .sff8024 import power_class_of_transceiver
    from .sffbase import sffbase    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .qsfp_dd import qsfp_dd_InterfaceId
    from .qsfp_dd import qsfp_dd_Dom
except ImportError as e:
    raise ImportError ("%s - required module not found" % e)

class inf8628InterfaceId(sffbase):

    def decode_application_advertisement(self, eeprom_data, offset, size):
        ret = {}
        tbl = self.qsfp_dd.parse_media_type(eeprom_data, offset)
        if tbl is None:
            return
        app = 1
        hid = int(eeprom_data[1 + offset], 16)
        while (app <= 8) and (hid != 0) and (hid != 0xff):
            (ht, mt) = self.qsfp_dd.parse_application(tbl, eeprom_data[1 + offset], eeprom_data[2 + offset])
            ret[app] = { 'host_if': ht, 'media_if': mt }
            app += 1
            offset += 4
            hid = int(eeprom_data[1 + offset], 16)
        return str(ret)

    def decode_cable_assembly_length(self, eeprom_data, offset, size):
        len = 0
        val = int(eeprom_data[offset], 16)
        if val == 0:
            return '0'
        if val == 0xff:
            return '6300+'

        base = val & 0x3f
        mult = (val >> 6) & 0x03
        if mult == 0:
            len = base / 10
        elif mult == 1:
            len = base
        elif mult == 2:
            len = base * 10
        else:
            len = base * 100
        return '{0}'.format(len)

    def decode_implemented_memory_pages(self, eeprom_data, offset, size):
        ret = []
        val = int(eeprom_data[offset], 16)
        if (val & 0x40) > 0:
            ret.append('Versatile Diagnostic Monitoring')
        if (val & 0x20) > 0:
            ret.append('Diagnostic Pages Implemented')
        if (val & 0x04) > 0:
            ret.append('Page 03h Implemented')
        bank = val & 0x03
        if (bank == 0):
            ret.append('Bank 0 Implemented')
        elif (bank == 1):
            ret.append('Bank 0,1 Implemented')
        elif (bank == 2):
            ret.append('Bank 0,1,2,3 Implemented')
        return str(ret)

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
                {'offset': 128,
                 'size': 1,
                 'type': 'enum',
                 'decode': type_of_transceiver},
            'type_abbrv_name':
                {'offset': 128,
                 'size':1,
                 'type' : 'enum',
                 'decode' : type_abbrv_name},
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
            'Media Type':
                {'offset': 85,
                 'size': 1,
                 'type': 'enum',
                 'decode': type_of_media_interface},
            'Application Advertisement':
                {'offset': 85,
                 'type': 'func',
                 'decode': {'func': decode_application_advertisement}},
            'Vendor Name':
                {'offset': 129,
                 'size': 16,
                 'type': 'str'},
            'Vendor OUI':
                {'offset': 145,
                 'size'  : 3,
                 'type'  : 'hex'},
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
            'Vendor Date Code(YYYY-MM-DD Lot)':
                {'offset': 182,
                 'size'  : 8,
                 'type'  : 'date'},
            'Power Class':
                {'offset': 200,
                 'size': 1,
                 'type': 'enum',
                 'decode': power_class_of_transceiver},
            'Length Cable Assembly(m)':
                {'offset': 202,
                 'type': 'func',
                 'decode': {'func': decode_cable_assembly_length}},
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

    impl_mem_pages = {
        'Implemented Memory Pages':
            {'offset': 0,
             'type': 'func',
             'decode': {'func': decode_implemented_memory_pages}},
        }

    module_state = {
        'Module State':
            {'offset': 0,
             'type': 'func',
             'decode': {'func': decode_module_state}},
        }

    def __init__(self, eeprom_raw_data=None):
        self.qsfp_dd = qsfp_dd_InterfaceId()
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

    def parse_implemented_memory_pages(self, raw_data, start_pos):
        return sffbase.parse(self, self.impl_mem_pages, raw_data, start_pos)

    def parse_module_state(self, sn_raw_data, start_pos):
        return sffbase.parse(self, self.module_state, sn_raw_data, start_pos)

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

class inf8628Dom(sffbase):

    version = '1.0'

    def calc_temperature(self, eeprom_data, offset, size):
        return self.qsfp_dd.calc_temperature(eeprom_data, offset, size)

    def calc_voltage(self, eeprom_data, offset, size):
        return self.qsfp_dd.calc_voltage(eeprom_data, offset, size)

    def calc_bias(self, eeprom_data, offset, size):
        return self.qsfp_dd.calc_bias(eeprom_data, offset, size)

    def calc_power(self, eeprom_data, offset, size):
        return self.qsfp_dd.calc_rx_power(eeprom_data, offset, size)

    dom_id = {
            'Temperature':
                {'offset': 14,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_temperature}},
            'Vcc':
                {'offset': 16,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_voltage}},
            'TX1Power':
                {'offset': (154 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'TX2Power':
                {'offset': (156 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'TX3Power':
                {'offset': (158 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'TX4Power':
                {'offset': (160 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'TX5Power':
                {'offset': (162 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'TX6Power':
                {'offset': (164 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'TX7Power':
                {'offset': (166 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'TX8Power':
                {'offset': (168 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'TX1Bias':
                {'offset': (170 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_bias}},
            'TX2Bias':
                {'offset': (172 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_bias}},
            'TX3Bias':
                {'offset': (174 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_bias}},
            'TX4Bias':
                {'offset': (176 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_bias}},
            'TX5Bias':
                {'offset': (178 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_bias}},
            'TX6Bias':
                {'offset': (180 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_bias}},
            'TX7Bias':
                {'offset': (182 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_bias}},
            'TX8Bias':
                {'offset': (184 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_bias}},
            'RX1Power':
                {'offset': (186 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'RX2Power':
                {'offset': (188 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'RX3Power':
                {'offset': (190 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'RX4Power':
                {'offset': (192 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'RX5Power':
                {'offset': (194 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'RX6Power':
                {'offset': (196 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'RX7Power':
                {'offset': (198 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
            'RX8Power':
                {'offset': (200 & 0x7f) + 0x900,
                 'size': 2,
                 'type': 'func',
                 'decode': {'func': calc_power}},
    }

    def __init__(self, eeprom_raw_data=None):
        self.qsfp_dd = qsfp_dd_Dom()
        if eeprom_raw_data is not None:
            self.dom_data = sffbase.parse(self,
                                          self.dom_id,
                                          eeprom_raw_data,
                                          0)

    def get_data_pretty(self):
        return sffbase.get_data_pretty(self, self.dom_data)
