#----------------------------------------------------------------------------
# sffbase class for sff8436 and sff8472
#----------------------------------------------------------------------------



try:
    import fcntl
    import struct
    import sys
    import time
    import binascii
    import os
    import getopt
    import types
    from math import log10
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

class sffbase(object):
    """Class to parse and interpret sff8436 and sff8472 spec for
    diagnostically monitoring interfaces of optical transceivers"""

    _indent = '\t'

    def inc_indent(self):
        self._indent += '\t'

    def dec_indent(self):
        self._indent = self._indent[:-1]

    # Convert Hex to String
    def convert_hex_to_string(self, arr, start, end):
        try:
            ret_str = ''
            for n in range(start, end):
                ret_str += arr[n]
            return binascii.unhexlify(ret_str).decode("utf-8", "ignore").strip()
        except Exception as err:
            return str(err)

    # Convert Date to String
    def convert_date_to_string(self, eeprom_data, offset, size):
        try:
            year_offset  = 0
            month_offset = 2
            day_offset   = 4
            lot_offset   = 6

            date = self.convert_hex_to_string(eeprom_data, offset, offset + size)
            retval = "20"+ date[year_offset:month_offset] + "-" + \
                    date[month_offset:day_offset] + "-" + \
                    date[day_offset:lot_offset] + " " + \
                    date[lot_offset:size]
        except Exception as err:
            retval = str(err)
        return retval

    def test_bit(self, n, bitpos):
        try:
            mask = 1 << bitpos
            if (n & mask) == 0:
                return 0
            else:
                return 1
        except Exception:
            return -1

    def twos_comp(self, num, bits):
        try:
            if ((num & (1 << (bits - 1))) != 0):
                num = num - (1 << bits)
            return num
        except Exception:
            return 0

    def float_from_bytes(b):
        """Convert IEEE 754 single precision float from bytes."""
        return struct.unpack('!f', b)[0]

    def mw_to_dbm(self, mW):
        if mW == 0:
            return float("-inf")
        elif mW < 0:
            return float("NaN")
        return 10. * log10(mW)


    def power_in_dbm_str(self, mW):
        return "%.4f%s" % (self.mw_to_dbm(mW), "dBm")

    # Parse sff base elements
    def parse_sff_element(self, eeprom_data, eeprom_ele, start_pos):
        value  = None
        offset = eeprom_ele.get('offset') + start_pos
        size   = eeprom_ele.get('size')
        type   = eeprom_ele.get('type')
        decode = eeprom_ele.get('decode');

        if type == 'enum':
            # Get the matched value
            value = decode.get(str(eeprom_data[offset]), 'Unknown')

        elif type == 'bitmap':
            # Get the 'on' bitname
            bitvalue_dict = {}
            for bitname, bitinfo in sorted(decode.items()):
                bitinfo_offset = bitinfo.get('offset') + start_pos
                bitinfo_pos = bitinfo.get('bit')
                bitinfo_value = bitinfo.get('value')
                data = int(eeprom_data[bitinfo_offset], 16)
                bit_value = self.test_bit(data, bitinfo_pos)
                if bitinfo_value != None:
                    if bit_value == bitinfo_value:
                        value = bitname
                        break
                elif bit_value == 1:
                    value = bitname
                    break

        elif type == 'bitvalue':
            # Get the value of the bit
            bitpos = eeprom_ele.get('bit')
            data = int(eeprom_data[offset], 16)
            bitval = self.test_bit(data, bitpos)
            value = ['Off', 'On'][bitval]

        elif type == 'func':
            # Call the decode func to get the value
            value = decode['func'](self, eeprom_data,
                         offset, size)

        elif type == 'str':
            value = self.convert_hex_to_string(eeprom_data, offset,
                              offset + size)

        elif type == 'int':
            value = int(eeprom_data[offset], 16)

        elif type == 'date':
            value = self.convert_date_to_string(eeprom_data, offset,
                              size)

        elif type == 'hex':
            value = '-'.join(eeprom_data[offset:offset+size])

        return value

    # Recursively parses sff data into dictionary
    def parse_sff(self, eeprom_map, eeprom_data, start_pos):
        outdict = {}
        for name, meta_data in sorted(eeprom_map.items()):
            type = meta_data.get('type')

            # Initialize output value
            value_dict = {}
            value_dict['outtype'] = meta_data.get('outtype')
            value_dict['short_name'] = meta_data.get('short_name')

            if type != 'nested':
                data = self.parse_sff_element(eeprom_data,
                                  meta_data, start_pos)
            else:
                nested_map = meta_data.get('decode')
                data = self.parse_sff(nested_map,
                             eeprom_data, start_pos)

            if data != None:
                value_dict['value'] = data
                outdict[name] = value_dict

        return outdict


    # Main sff parser function
    def parse(self, eeprom_map, eeprom_data, start_pos):
        """ Example Return format:
        {'version': '1.0', 'data': {'Length50um(UnitsOf10m)':
        {'outtype': None, 'value': 8, 'short_name': None},
        'TransceiverCodes': {'outtype': None, 'value':
        {'10GEthernetComplianceCode': {'outtype': None, 'value':
        '10G Base-SR', 'short_name': None}}, 'short_name': None},
        'ExtIdentOfTypeOfTransceiver': {'outtype': None, 'value':
        'GBIC/SFP func defined by two-wire interface ID', 'short_name':
         None}, 'Length62.5um(UnitsOfm)': {'outtype': None,"""

        outdict = {}
        return_dict = {}

        outdict = self.parse_sff(eeprom_map, eeprom_data, start_pos)

        return_dict['version'] = self.version
        return_dict['data'] = outdict

        return return_dict


    # Returns sff parsed data in a pretty dictionary format
    def get_data_pretty_dict(self, indict):
        outdict = {}

        for elem, elem_val in sorted(indict.items()):
            value = elem_val.get('value')
            if type(value) == dict:
                outdict[elem] = sffbase.get_data_pretty_dict(
                                self, value)
            else:
                outdict[elem] = value

        return outdict

    def get_data_pretty(self, indata):
        """Example Return format:
        {'version': '1.0', 'data': {'Length50um(UnitsOf10m)': 8,
        'TransceiverCodes': {'10GEthernetComplianceCode':
        '10G Base-SR'}, 'ExtIdentOfTypeOfTransceiver': 'GBIC/SFP func
        defined by two-wire interface ID', 'Length62.5um(UnitsOfm)': 3,
         'VendorPN': 'FTLX8571D3BNL', 'RateIdentifier': 'Unspecified',
         'NominalSignallingRate(UnitsOf100Mbd)': 103, 'VendorOUI': ..}}
        {'version': '1.0', 'data': {'AwThresholds':
        {'TXPowerLowWarning': '-5.0004 dBm', 'TempHighWarning':
        '88.0000C', 'RXPowerHighAlarm': '0.0000 dBm',
        'TXPowerHighAlarm': '-0.7998 dBm', 'RXPowerLowAlarm':
        '-20.0000 dBm', 'RXPowerHighWarning': '-1.0002 dBm',
        'VoltageLowAlarm': '2.9000Volts'"""

        return_dict = {}

        return_dict['version'] = indata.get('version')
        return_dict['data'] = self.get_data_pretty_dict(indata.get(
                                'data'))
        return return_dict

    # Dumps dict in pretty format
    def dump_pretty(self, indict):
        for elem, elem_val in sorted(indict.items()):
            if type(elem_val) == dict:
                print(self._indent, elem, ': ')
                self.inc_indent()
                sff8472.dump_pretty(self, elem_val)
                self.dec_indent()
            elif type(elem_val) == list:
                if len(elem_val) == 1:
                    print(self._indent, elem, ': ', elem_val.pop())
                else:
                    print(self._indent, elem, ': ')
                    self.inc_indent()
                    for e in elem_val:
                        print(self._indent, e)
                    self.dec_indent()
            else:
                print(self._indent, elem, ': ', elem_val)
