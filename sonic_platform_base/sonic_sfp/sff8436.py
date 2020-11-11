#----------------------------------------------------------------------------
# SFF-8436 QSFP+ 10 Gbs 4X PLUGGABLE TRANSCEIVER
#----------------------------------------------------------------------------

from __future__ import print_function

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
    from .sff8024 import type_of_transceiver    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import type_abbrv_name    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import ext_specification_compliance    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sffbase import sffbase    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

class sff8436InterfaceId(sffbase):

    version = '1.0'

    specification_compliance = {'10/40G Ethernet Compliance Code':
                {'offset':3,
                 'size':1,
                 'type' : 'bitmap',
                 'decode' : {
                         '10GBase-LRM':
                        {'offset': 3,
                         'bit': 6},
                         '10GBase-LR':
                        {'offset': 3,
                         'bit': 5},
                         '10GBase-SR':
                        {'offset': 3,
                         'bit': 4},
                         '40GBASE-CR4':
                        {'offset': 3,
                         'bit': 3},
                         '40GBASE-SR4':
                        {'offset': 3,
                         'bit': 2},
                         '40GBASE-LR4':
                        {'offset': 3,
                         'bit': 1},
                         '40G Active Cable (XLPPI)':
                        {'offset': 3,
                         'bit': 0}}},
                 'SONET Compliance codes':
                {'offset':4,
                 'size':1,
                 'type' : 'bitmap',
                 'decode' : {
                         '40G OTN (OTU3B/OTU3C)':
                        {'offset': 4,
                         'bit': 3},
                         'OC 48, long reach':
                        {'offset': 4,
                         'bit': 2},
                         'OC 48, intermediate reach':
                        {'offset': 4,
                         'bit': 1},
                         'OC 48 short reach':
                        {'offset': 4,
                         'bit': 0}}},
                 'SAS/SATA compliance codes':
                {'offset': 5,
                 'size'  : 1,
                 'type'  : 'bitmap',
                 'decode': {
                         'SAS 6.0G':
                        {'offset': 5,
                         'bit': 5},
                         'SAS 3.0G':
                        {'offset': 5,
                         'bit': 4}}},
                 'Gigabit Ethernet Compliant codes':
                {'offset': 6,
                 'size'  : 1,
                 'type'  : 'bitmap',
                 'decode': {
                         '1000BASE-T':
                        {'offset': 6,
                         'bit': 3},
                         '1000BASE-CX':
                        {'offset': 6,
                         'bit': 2},
                         '1000BASE-LX':
                        {'offset': 6,
                         'bit': 1},
                         '1000BASE-SX':
                        {'offset': 6,
                         'bit': 0}}},
                 'Fibre Channel link length/Transmitter Technology':
                {'offset': 7,
                 'size'  : 2,
                 'type'  : 'bitmap',
                 'decode': {
                         'Very long distance (V)':
                        {'offset': 7,
                         'bit': 7},
                         'Short distance (S)':
                        {'offset': 7,
                         'bit': 6},
                         'Intermediate distance (I)':
                        {'offset': 7,
                         'bit': 5},
                         'Long distance (L)':
                        {'offset': 7,
                         'bit': 4},
                         'Medium (M)':
                        {'offset': 7,
                         'bit': 3},
                         'Longwave laser (LC)':
                        {'offset': 7,
                         'bit': 1},
                         'Electrical inter-enclosure (EL)':
                        {'offset': 7,
                         'bit': 0},
                         'Electrical intra-enclosure':
                        {'offset': 8,
                         'bit': 7},
                         'Shortwave laser w/o OFC (SN)':
                        {'offset': 8,
                         'bit': 6},
                         'Shortwave laser w OFC (SL)':
                        {'offset': 8,
                         'bit': 5},
                         'Longwave Laser (LL)':
                        {'offset': 8,
                         'bit': 4}}},
                 'Fibre Channel transmission media':
                {'offset': 8,
                 'size'  : 1,
                 'type'  : 'bitmap',
                 'decode': {
                         'Twin Axial Pair (TW)':
                        {'offset': 8,
                         'bit': 7},
                         'Shielded Twisted Pair (TP)':
                        {'offset': 8,
                         'bit': 6},
                         'Miniature Coax (MI)':
                        {'offset': 8,
                         'bit': 5},
                         'Video Coax (TV)':
                        {'offset': 8,
                         'bit': 4},
                         'Multi-mode 62.5m (M6)':
                        {'offset': 8,
                         'bit': 3},
                         'Multi-mode 50m (M5)':
                        {'offset': 8,
                         'bit': 2},
                         'Multi-mode 50um (OM3)':
                        {'offset': 8,
                         'bit': 1},
                         'Single Mode (SM)':
                        {'offset': 8,
                         'bit': 0}}},
                 'Fibre Channel Speed':
                {'offset': 9,
                 'size'  : 1,
                 'type'  : 'bitmap',
                 'decode': {
                         '1200 Mbytes/Sec':
                        {'offset': 9,
                         'bit': 7},
                         '800 Mbytes/Sec':
                        {'offset': 9,
                         'bit': 6},
                         '1600 Mbytes/Sec':
                        {'offset': 9,
                         'bit': 5},
                         '400 Mbytes/Sec':
                        {'offset': 9,
                         'bit': 4},
                         '200 Mbytes/Sec':
                        {'offset': 9,
                         'bit': 2},
                         '100 Mbytes/Sec':
                        {'offset': 9,
                         'bit': 0}}}}

    ext_type_of_transceiver = {
            '00': 'Power Class 1(1.5W max)',
            '04': 'Power Class 1(1.5W max), CDR present in Tx',
            '08': 'Power Class 1(1.5W max), CDR present in Rx',
            '0c': 'Power Class 1(1.5W max), CDR present in Rx Tx',
            '10': 'Power Class 1(1.5W max), CLEI present',
            '14': 'Power Class 1(1.5W max), CLEI present, CDR present in Tx',
            '18': 'Power Class 1(1.5W max), CLEI present, CDR present in Rx',
            '1c': 'Power Class 1(1.5W max), CLEI present, CDR present in Rx Tx',

            '40': 'Power Class 2(2.0W max)',
            '44': 'Power Class 2(2.0W max), CDR present in Rx',
            '48': 'Power Class 2(2.0W max), CDR present in Tx',
            '4c': 'Power Class 2(2.0W max), CDR present in Rx Tx',
            '50': 'Power Class 2(2.0W max), CLEI present',
            '54': 'Power Class 2(2.0W max), CLEI present, CDR present in Rx',
            '58': 'Power Class 2(2.0W max), CLEI present, CDR present in Tx',
            '5c': 'Power Class 2(2.0W max), CLEI present, CDR present in Rx Tx',

            '80': 'Power Class 3(2.5W max)',
            '84': 'Power Class 3(2.5W max), CDR present in Rx',
            '88': 'Power Class 3(2.5W max), CDR present in Tx',
            '8c': 'Power Class 3(2.5W max), CDR present in Rx Tx',
            '90': 'Power Class 3(2.5W max), CLEI present',
            '94': 'Power Class 3(2.5W max), CLEI present, CDR present in Rx',
            '98': 'Power Class 3(2.5W max), CLEI present, CDR present in Tx',
            '9c': 'Power Class 3(2.5W max), CLEI present, CDR present in Rx Tx',

            'c0': 'Power Class 4(3.5W max)',
            'c4': 'Power Class 4(3.5W max), CDR present in Rx',
            'c8': 'Power Class 4(3.5W max), CDR present in Tx',
            'cc': 'Power Class 4(3.5W max), CDR present in Rx Tx',
            'd0': 'Power Class 4(3.5W max), CLEI present',
            'd4': 'Power Class 4(3.5W max), CLEI present, CDR present in Rx',
            'd8': 'Power Class 4(3.5W max), CLEI present, CDR present in Tx',
            'dc': 'Power Class 4(3.5W max), CLEI present, CDR present in Rx Tx'
            }

    connector = {
            '00': 'Unknown or unspecified',
            '01': 'SC',
            '02': 'FC Style 1 copper connector',
            '03': 'FC Style 2 copper connector',
            '04': 'BNC/TNC',
            '05': 'FC coax headers',
            '06': 'Fiberjack',
            '07': 'LC',
            '08': 'MT-RJ',
            '09': 'MU',
            '0a': 'SG',
            '0b': 'Optical Pigtail',
            '0c': 'MPOx12',
            '0d': 'MPOx16',
            '20': 'HSSDC II',
            '21': 'Copper pigtail',
            '22': 'RJ45',
            '23': 'No separable connector'
            }

    encoding_codes = {
            '00':'Unspecified',
            '01': '8B10B',
            '02': '4B5B',
            '03': 'NRZ',
            '04': 'SONET Scrambled',
            '05': '64B66B',
            '06': 'Manchester',
            '07': '256B257B'
            }

    rate_identifier = {'00':'QSFP+ Rate Select Version 1'}

    interface_id = {'Identifier':
                {'offset':0,
                 'size':1,
                 'type' : 'enum',
                 'decode' : type_of_transceiver},
             'Extended Identifier':
                {'offset':1,
                 'size':1,
                 'type' : 'enum',
                 'decode': ext_type_of_transceiver},
             'Connector':
                {'offset':2,
                 'size':1,
                 'type' : 'enum',
                 'decode': connector},
            'Specification compliance':
                {'offset' : 3,
                 'type' : 'nested',
                 'decode' : specification_compliance},
            'Encoding':
                {'offset':11,
                 'size':1,
                 'type' : 'enum',
                 'decode' : encoding_codes},
            'Nominal Bit Rate(100Mbs)':
                {'offset': 12,
                 'size':1,
                 'type':'int'},
            'Extended RateSelect Compliance':
                {'offset':13,
                 'size':1,
                 'type' : 'enum',
                 'decode' : rate_identifier},
            'Length(km)':
                {'offset':14,
                 'size':1,
                 'type':'int'},
            'Length OM3(2m)':
                {'offset':15,
                 'size':1,
                 'type':'int'},
            'Length OM2(m)':
                {'offset':16,
                'size':1,
                 'type':'int'},
            'Length OM1(m)':
                {'offset':17,
                'size':1,
                 'type':'int'},
            'Length Cable Assembly(m)':
                {'offset':18,
                'size':1,
                 'type':'int'},
            # Device Tech
            'Vendor Name':
                {'offset' : 20,
                 'size': 16,
                 'type': 'str'},
            'Vendor OUI':
                {'offset': 37,
                 'size'  : 3,
                 'type'  : 'hex'},
            'Vendor PN':
                {'offset': 40,
                 'size'  : 16,
                 'type'  : 'str'},
            'Vendor Rev':
                {'offset': 56,
                 'size'  : 2,
                 'type'  : 'str'},
            'Vendor SN':
                {'offset': 68,
                 'size'  : 16,
                 'type'  : 'str'},
            'Vendor Date Code(YYYY-MM-DD Lot)':
                {'offset': 84,
                 'size'  : 8,
                 'type'  : 'date'},
            'Diagnostic Monitoring Type':
                {'offset': 92,
                 'size'  : 1,
                 'type'  : 'bitmap',
                 'decode': {}},
            'Enhanced Options':
                {'offset': 93,
                 'size'  : 1,
                 'type'  : 'bitmap',
                 'decode': {}}}
    
    sfp_info_bulk = {'type':
                {'offset':0,
                 'size':1,
                 'type' : 'enum',
                 'decode' : type_of_transceiver},
             'type_abbrv_name':
                {'offset':0,
                 'size':1,
                 'type' : 'enum',
                 'decode' : type_abbrv_name},
             'Extended Identifier':
                {'offset':1,
                 'size':1,
                 'type' : 'enum',
                 'decode': ext_type_of_transceiver},
             'Connector':
                {'offset':2,
                 'size':1,
                 'type' : 'enum',
                 'decode': connector},
            'Specification compliance':
                {'offset' : 3,
                 'type' : 'nested',
                 'decode' : specification_compliance},
            'EncodingCodes':
                {'offset':11,
                 'size':1,
                 'type' : 'enum',
                 'decode' : encoding_codes},
            'Nominal Bit Rate(100Mbs)':
                {'offset': 12,
                 'size':1,
                 'type':'int'},
            'RateIdentifier':
                {'offset':13,
                 'size':1,
                 'type' : 'enum',
                 'decode' : rate_identifier},
            'Length(km)':
                {'offset':14,
                 'size':1,
                 'type':'int'},
            'Length OM3(2m)':
                {'offset':15,
                 'size':1,
                 'type':'int'},
            'Length OM2(m)':
                {'offset':16,
                'size':1,
                 'type':'int'},
            'Length OM1(m)':
                {'offset':17,
                'size':1,
                 'type':'int'},
            'Length Cable Assembly(m)':
                {'offset':18,
                'size':1,
                 'type':'int'}
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

    vendor_oui = {
        'Vendor OUI':
                {'offset':0,
                 'size':3,
                 'type' : 'hex'}
        }
    
    vendor_date = {
        'VendorDataCode(YYYY-MM-DD Lot)':
                {'offset':0,
                'size':8,
                'type': 'date'}
        }

    sfp_ext_specification_compliance = {
        'Extended Specification compliance':
            {'offset' : 0,
             'size':1,
             'type' : 'enum',
             'decode' : ext_specification_compliance}
        }

    qsfp_dom_capability = {
        'Tx_power_support':
            {'offset': 0,
             'bit': 2,
             'type': 'bitvalue'},
        'Rx_power_support':
            {'offset': 0,
             'bit': 3,
             'type': 'bitvalue'},
        'Voltage_support':
            {'offset': 0,
             'bit': 4,
             'type': 'bitvalue'},
        'Temp_support':
            {'offset': 0,
             'bit': 5,
             'type': 'bitvalue'}
        }

    def __init__(self, eeprom_raw_data=None):
        self.interface_data = None
        start_pos = 128

        if eeprom_raw_data != None:
            self.interface_data = sffbase.parse(self,
                            self.interface_id,
                            eeprom_raw_data,
                            start_pos)

    def parse(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.interface_id, eeprom_raw_data, start_pos)

    def parse_sfp_info_bulk(self, type_raw_data, start_pos):
        return sffbase.parse(self, self.sfp_info_bulk, type_raw_data, start_pos)

    def parse_vendor_name(self, name_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_name, name_raw_data, start_pos)

    def parse_vendor_rev(self, rev_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_rev, rev_raw_data, start_pos)

    def parse_vendor_pn(self, pn_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_pn, pn_raw_data, start_pos)

    def parse_vendor_sn(self, sn_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_sn, sn_raw_data, start_pos)

    def parse_vendor_date(self, sn_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_date, sn_raw_data, start_pos)
    
    def parse_vendor_oui(self, sn_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_oui, sn_raw_data, start_pos)

    def parse_ext_specification_compliance(self, sn_raw_data, start_pos):
        return sffbase.parse(self, self.sfp_ext_specification_compliance, sn_raw_data, start_pos)

    def parse_qsfp_dom_capability(self, sn_raw_data, start_pos):
        return sffbase.parse(self, self.qsfp_dom_capability, sn_raw_data, start_pos)

    def dump_pretty(self):
        if self.interface_data == None:
            print('Object not initialized, nothing to print')
            return
        sffbase.dump_pretty(self, self.interface_data)

    def get_calibration_type(self):
        return self.calibration_type

    def get_data(self):
        return self.interface_data

    def get_data_pretty(self):
        return sffbase.get_data_pretty(self, self.interface_data)


class sff8436Dom(sffbase):

    version = '1.0'

    def get_calibration_type(self):
        return self._calibration_type

    def calc_temperature(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)

            result = (msb << 8) | (lsb & 0xff)
            result = self.twos_comp(result, 16)

            if cal_type == 1:

                # Internal calibration

                result = float(result / 256.0)
                retval = '%.4f' %result + 'C'
            elif cal_type == 2:

                # External calibration

                # T(C) = T_Slope * T_AD + T_Offset
                off = self.dom_ext_calibration_constants['T_Slope']['offset']
                msb_t = int(eeprom_data[off], 16)
                lsb_t = int(eeprom_data[off + 1], 16)
                t_slope = (msb_t << 8) | (lsb_t & 0xff)

                off = self.dom_ext_calibration_constants['T_Offset']['offset']
                msb_t = int(eeprom_data[off], 16)
                lsb_t = int(eeprom_data[off + 1], 16)
                t_offset = (msb_t << 8) | (lsb_t & 0xff)
                t_offset = self.twos_comp(t_offset, 16)

                result = t_slope * result + t_offset
                result = float(result / 256.0)
                retval = '%.4f' %result + 'C'
            else:
                retval = 'Unknown'
        except Exception as err:
            retval = str(err)

        return retval


    def calc_voltage(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            if cal_type == 1:

                # Internal Calibration

                result = float(result * 0.0001)
                #print(indent, name, ' : %.4f' %result, 'Volts')
                retval = '%.4f' %result + 'Volts'
            elif cal_type == 2:

                # External Calibration

                # V(uV) = V_Slope * VAD + V_Offset
                off = self.dom_ext_calibration_constants['V_Slope']['offset']
                msb_v = int(eeprom_data[off], 16)
                lsb_v = int(eeprom_data[off + 1], 16)
                v_slope = (msb_v << 8) | (lsb_v & 0xff)

                off = self.dom_ext_calibration_constants['V_Offset']['offset']
                msb_v = int(eeprom_data[off], 16)
                lsb_v = int(eeprom_data[off + 1], 16)
                v_offset = (msb_v << 8) | (lsb_v & 0xff)
                v_offset = self.twos_comp(v_offset, 16)

                result = v_slope * result + v_offset
                result = float(result * 0.0001)
                #print(indent, name, ' : %.4f' %result, 'Volts')
                retval = '%.4f' %result + 'Volts'
            else:
                #print(indent, name, ' : Unknown')
                retval = 'Unknown'
        except Exception as err:
            retval = str(err)

        return retval


    def calc_bias(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            if cal_type == 1:
                # Internal Calibration

                result = float(result * 0.002)
                #print(indent, name, ' : %.4f' %result, 'mA')
                retval = '%.4f' %result + 'mA'

            elif cal_type == 2:
                # External Calibration

                # I(uA) = I_Slope * I_AD + I_Offset
                off = self.dom_ext_calibration_constants['I_Slope']['offset']
                msb_i = int(eeprom_data[off], 16)
                lsb_i = int(eeprom_data[off + 1], 16)
                i_slope = (msb_i << 8) | (lsb_i & 0xff)

                off = self.dom_ext_calibration_constants['I_Offset']['offset']
                msb_i = int(eeprom_data[off], 16)
                lsb_i = int(eeprom_data[off + 1], 16)
                i_offset = (msb_i << 8) | (lsb_i & 0xff)
                i_offset = self.twos_comp(i_offset, 16)

                result = i_slope * result + i_offset
                result = float(result * 0.002)
                #print(indent, name, ' : %.4f' %result, 'mA')
                retval = '%.4f' %result + 'mA'
            else:
                retval = 'Unknown'
        except Exception as err:
            retval = str(err)

        return retval


    def calc_tx_power(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            if cal_type == 1:

                result = float(result * 0.0001)
                #print(indent, name, ' : ', power_in_dbm_str(result))
                retval = self.power_in_dbm_str(result)

            elif cal_type == 2:

                # TX_PWR(uW) = TX_PWR_Slope * TX_PWR_AD + TX_PWR_Offset
                off = self.dom_ext_calibration_constants['TX_PWR_Slope']['offset']
                msb_tx_pwr = int(eeprom_data[off], 16)
                lsb_tx_pwr = int(eeprom_data[off + 1], 16)
                tx_pwr_slope = (msb_tx_pwr << 8) | (lsb_tx_pwr & 0xff)

                off = self.dom_ext_calibration_constants['TX_PWR_Offset']['offset']
                msb_tx_pwr = int(eeprom_data[off], 16)
                lsb_tx_pwr = int(eeprom_data[off + 1], 16)
                tx_pwr_offset = (msb_tx_pwr << 8) | (lsb_tx_pwr & 0xff)
                tx_pwr_offset = self.twos_comp(tx_pwr_offset, 16)

                result = tx_pwr_slope * result + tx_pwr_offset
                result = float(result * 0.0001)
                retval = self.power_in_dbm_str(result)
            else:
                retval = 'Unknown'
        except Exception as err:
                retval = str(err)

        return retval


    def calc_rx_power(self, eeprom_data, offset, size):
        try:
            cal_type = self.get_calibration_type()

            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            if cal_type == 1:

                # Internal Calibration
                result = float(result * 0.0001)
                #print(indent, name, " : ", power_in_dbm_str(result))
                retval = self.power_in_dbm_str(result)

            elif cal_type == 2:

                # External Calibration

                # RX_PWR(uW) = RX_PWR_4 * RX_PWR_AD +
                #          RX_PWR_3 * RX_PWR_AD +
                #          RX_PWR_2 * RX_PWR_AD +
                #          RX_PWR_1 * RX_PWR_AD +
                #          RX_PWR(0)
                off = self.dom_ext_calibration_constants['RX_PWR_4']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_4 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                off = self.dom_ext_calibration_constants['RX_PWR_3']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_3 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                off = self.dom_ext_calibration_constants['RX_PWR_2']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_2 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                off = self.dom_ext_calibration_constants['RX_PWR_1']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_1 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                off = self.dom_ext_calibration_constants['RX_PWR_0']['offset']
                rx_pwr_byte3 = int(eeprom_data[off], 16)
                rx_pwr_byte2 = int(eeprom_data[off + 1], 16)
                rx_pwr_byte1 = int(eeprom_data[off + 2], 16)
                rx_pwr_byte0 = int(eeprom_data[off + 3], 16)
                rx_pwr_0 = (rx_pwr_byte3 << 24) | (rx_pwr_byte2 << 16) | (rx_pwr_byte1 << 8) | (rx_pwr_byte0 & 0xff)

                rx_pwr = (rx_pwr_4 * result) + (rx_pwr_3 * result) + (rx_pwr_2 * result) + (rx_pwr_1 * result) + rx_pwr_0

                result = float(result * 0.0001)
                #print(indent, name, " : ", power_in_dbm_str(result))
                retval = self.power_in_dbm_str(result)
            else:
                retval = 'Unknown'
        except Exception as err:
            retval = str(err)

        return retval

    dom_status_indicator = {
            'DataNotReady':
                {'offset': 0,
                 'bit': 0,
                 'type': 'bitvalue'},
            'IntL':
                {'offset': 0,
                 'bit': 1,
                 'type': 'bitvalue'},
            'FlatMem':
                {'offset': 0,
                 'bit': 2,
                 'type': 'bitvalue'}}

    dom_channel_status = {
            'Tx4LOS':
                {'offset': 3,
                 'bit': 7,
                 'type': 'bitvalue'},
            'Tx3LOS':
                {'offset': 3,
                 'bit': 6,
                 'type': 'bitvalue'},
            'Tx2LOS':
                {'offset': 3,
                 'bit': 5,
                 'type': 'bitvalue'},
            'Tx1LOS':
                {'offset': 3,
                 'bit': 4,
                 'type': 'bitvalue'},
            'Rx4LOS':
                {'offset': 3,
                 'bit': 3,
                 'type': 'bitvalue'},
            'Rx3LOS':
                {'offset': 3,
                 'bit': 2,
                 'type': 'bitvalue'},
            'Rx2LOS':
                {'offset': 3,
                 'bit': 1,
                 'type': 'bitvalue'},
            'Rx1LOS':
                {'offset': 3,
                 'bit': 0,
                 'type': 'bitvalue'},
            'Tx4Fault':
                {'offset': 4,
                 'bit': 3,
                 'type': 'bitvalue'},
            'Tx3Fault':
                {'offset': 4,
                 'bit': 2,
                 'type': 'bitvalue'},
            'Tx2Fault':
                {'offset': 4,
                 'bit': 1,
                 'type': 'bitvalue'},
            'Tx1Fault':
                {'offset': 4,
                 'bit': 0,
                 'type': 'bitvalue'}}

    dom_tx_rx_los = {'Tx4LOS':
                {'offset': 0,
                 'bit': 7,
                 'type': 'bitvalue'},
                  'Tx3LOS':
                {'offset': 0,
                 'bit': 6,
                 'type': 'bitvalue'},
                  'Tx2LOS':
                {'offset': 0,
                 'bit': 5,
                 'type': 'bitvalue'},
                  'Tx1LOS':
                {'offset': 0,
                 'bit': 4,
                 'type': 'bitvalue'},
                  'Rx4LOS':
                {'offset': 0,
                 'bit': 3,
                 'type': 'bitvalue'},
                  'Rx3LOS':
                {'offset': 0,
                 'bit': 2,
                 'type': 'bitvalue'},
                  'Rx2LOS':
                {'offset': 0,
                 'bit': 1,
                 'type': 'bitvalue'},
                  'Rx1LOS':
                {'offset': 0,
                 'bit': 0,
                 'type': 'bitvalue'}}

    dom_tx_fault = {'Tx4Fault':
                {'offset': 0,
                 'bit': 3,
                 'type': 'bitvalue'},
                  'Tx3Fault':
                {'offset': 0,
                 'bit': 2,
                 'type': 'bitvalue'},
                  'Tx2Fault':
                {'offset': 0,
                 'bit': 1,
                 'type': 'bitvalue'},
                  'Tx1Fault':
                {'offset': 0,
                 'bit': 0,
                 'type': 'bitvalue'}}

    dom_module_monitor = {
            'TempHighAlarm':
                {'offset': 6,
                 'bit': 7,
                 'type': 'bitvalue'},
            'TempLowAlarm':
                {'offset': 6,
                 'bit': 6,
                 'type': 'bitvalue'},
            'TempHighWarning':
                {'offset': 6,
                 'bit': 5,
                 'type': 'bitvalue'},
            'TempLowWarning':
                {'offset': 6,
                 'bit': 4,
                 'type': 'bitvalue'},
            'InitCompleteFlag':
                {'offset': 6,
                 'bit': 0,
                 'type': 'bitvalue'},
            'VccHighAlarm':
                {'offset': 7,
                 'bit': 7,
                 'type': 'bitvalue'},
            'VccLowAlarm':
                {'offset': 7,
                 'bit': 6,
                 'type': 'bitvalue'},
            'VccHighWarning':
                {'offset': 7,
                 'bit': 5,
                 'type': 'bitvalue'},
            'VccLowWarning':
                {'offset': 7,
                 'bit': 4,
                 'type': 'bitvalue'}}

    dom_channel_monitor = {
            'Rx1PowerHighAlarm':
                {'offset': 9,
                 'bit': 7,
                 'type': 'bitvalue'},
            'Rx1PowerLowAlarm':
                {'offset': 9,
                 'bit': 6,
                 'type': 'bitvalue'},
            'Rx1PowerHighWarning':
                {'offset': 9,
                 'bit': 5,
                 'type': 'bitvalue'},
            'Rx1PowerLowWarning':
                {'offset': 9,
                 'bit': 4,
                 'type': 'bitvalue'},
            'Rx2PowerHighAlarm':
                {'offset': 9,
                 'bit': 3,
                 'type': 'bitvalue'},
            'Rx2PowerLowAlarm':
                {'offset': 9,
                 'bit': 2,
                 'type': 'bitvalue'},
            'Rx2PowerHighWarning':
                {'offset': 9,
                 'bit': 1,
                 'type': 'bitvalue'},
            'Rx2PowerLowWarning':
                {'offset': 9,
                 'bit': 0,
                 'type': 'bitvalue'},
            'Rx3PowerHighAlarm':
                {'offset': 10,
                 'bit': 7,
                 'type': 'bitvalue'},
            'Rx3PowerLowAlarm':
                {'offset': 10,
                 'bit': 6,
                 'type': 'bitvalue'},
            'Rx3PowerHighWarning':
                {'offset': 10,
                 'bit': 5,
                 'type': 'bitvalue'},
            'Rx3PowerLowWarning':
                {'offset': 10,
                 'bit': 4,
                 'type': 'bitvalue'},
            'Rx4PowerHighAlarm':
                {'offset': 10,
                 'bit': 3,
                 'type': 'bitvalue'},
            'Rx4PowerLowAlarm':
                {'offset': 10,
                 'bit': 2,
                 'type': 'bitvalue'},
            'Rx4PowerHighWarning':
                {'offset': 10,
                 'bit': 1,
                 'type': 'bitvalue'},
            'Rx4PowerLowWarning':
                {'offset': 10,
                 'bit': 0,
                 'type': 'bitvalue'},
            'Tx1BiasHighAlarm':
                {'offset': 11,
                 'bit': 7,
                 'type': 'bitvalue'},
            'Tx1BiasLowAlarm':
                {'offset': 11,
                 'bit': 6,
                 'type': 'bitvalue'},
            'Tx1BiasHighWarning':
                {'offset': 11,
                 'bit': 5,
                 'type': 'bitvalue'},
            'Tx1BiasLowWarning':
                {'offset': 11,
                 'bit': 4,
                 'type': 'bitvalue'},
            'Tx2BiasHighAlarm':
                {'offset': 11,
                 'bit': 3,
                 'type': 'bitvalue'},
            'Tx2BiasLowAlarm':
                {'offset': 11,
                 'bit': 2,
                 'type': 'bitvalue'},
            'Tx2BiasHighWarning':
                {'offset': 11,
                 'bit': 1,
                 'type': 'bitvalue'},
            'Tx2BiasLowWarning':
                {'offset': 11,
                 'bit': 0,
                 'type': 'bitvalue'},
            'Tx3BiasHighAlarm':
                {'offset': 12,
                 'bit': 7,
                 'type': 'bitvalue'},
            'Tx3BiasLowAlarm':
                {'offset': 12,
                 'bit': 6,
                 'type': 'bitvalue'},
            'Tx3BiasHighWarning':
                {'offset': 12,
                 'bit': 5,
                 'type': 'bitvalue'},
            'Tx3BiasLowWarning':
                {'offset': 12,
                 'bit': 4,
                 'type': 'bitvalue'},
            'Tx4BiasHighAlarm':
                {'offset': 12,
                 'bit': 3,
                 'type': 'bitvalue'},
            'Tx4BiasLowAlarm':
                {'offset': 12,
                 'bit': 2,
                 'type': 'bitvalue'},
            'Tx4BiasHighWarning':
                {'offset': 12,
                 'bit': 1,
                 'type': 'bitvalue'},
            'Tx4BiasLowWarning':
                {'offset': 12,
                 'bit': 0,
                 'type': 'bitvalue'}}

    dom_module_monitor_values = {
            'Temperature':
                {'offset':22,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_temperature}},
            'Vcc':   
                {'offset':26,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_voltage}}}

    dom_channel_monitor_values = {
            'RX1Power':
                {'offset':34,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_rx_power}},
            'RX2Power':
                {'offset':36,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_rx_power}},
            'RX3Power':
                {'offset':38,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_rx_power}},
            'RX4Power':
                {'offset':40,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_rx_power}},
            'TX1Bias':
                {'offset':42,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_bias}},
            'TX2Bias':
                {'offset':44,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_bias}},
            'TX3Bias':
                {'offset':46,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_bias}},
            'TX4Bias':
                {'offset':48,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_bias}}}

    dom_map = {
           'ModuleMonitorValues':
            {'offset': 7,
             'size': 2,
             'type': 'nested',
             'decode': dom_module_monitor_values},
           'ChannelMonitorValues':
            {'offset': 10,
             'size': 2,
             'type': 'nested',
             'decode': dom_channel_monitor_values}}

# new added parser for some specific values interested by SNMP
# TO DO: find a way to reuse the definitions in above code, need refactor
    revision_compliance = {
        '00': 'Revision not specified',
        '01': 'SFF-8436 Rev 4.8',
        '02': 'SFF-8436 Rev 4.8 with extra bytes support',
        '03': 'SFF-8636 Rev 1.3',
        '04': 'SFF-8636 Rev 1.4',
        '05': 'SFF-8636 Rev 1.5',
        '06': 'SFF-8636 Rev 2.0',
        '07': 'SFF-8636 Rev 2.5'
        }

    sfp_dom_rev = {
        'dom_rev':
            {'offset': 0,
             'size': 1,
             'type': 'enum',
             'decode': revision_compliance}
        }

    dom_module_temperature = {
        'Temperature':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_temperature}}
        }

    dom_module_voltage = {
        'Vcc':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_voltage}}
        }

    dom_channel_monitor_params = {
        'RX1Power':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX2Power':
            {'offset': 2,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX3Power':
            {'offset': 4,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX4Power':
            {'offset': 6,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'TX1Bias':
            {'offset': 8,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX2Bias':
            {'offset': 10,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX3Bias':
            {'offset': 12,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX4Bias':
            {'offset': 14,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}}
        }

    dom_channel_monitor_params_with_tx_power = {
        'RX1Power':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX2Power':
            {'offset': 2,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX3Power':
            {'offset': 4,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX4Power':
            {'offset': 6,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'TX1Bias':
            {'offset': 8,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX2Bias':
            {'offset': 10,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX3Bias':
            {'offset': 12,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX4Bias':
            {'offset': 14,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX1Power':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX2Power':
            {'offset': 2,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX3Power':
            {'offset': 4,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX4Power':
            {'offset': 6,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}}
        }

    dom_module_threshold_values = {
        'TempHighAlarm':
             {'offset':0,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_temperature}},
        'TempLowAlarm':
             {'offset':2,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_temperature}},
        'TempHighWarning':
              {'offset':4,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_temperature}},
        'TempLowWarning':
             {'offset':6,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_temperature}},
        'VccHighAlarm':
             {'offset':16,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_voltage}},
        'VccLowAlarm':
             {'offset':18,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_voltage}},
        'VccHighWarning':
             {'offset':20,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_voltage}},
        'VccLowWarning':
             {'offset':22,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_voltage}}}

    dom_channel_threshold_values = {
        'RxPowerHighAlarm':
             {'offset':0,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'RxPowerLowAlarm':
             {'offset':2,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'RxPowerHighWarning':
             {'offset':4,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'RxPowerLowWarning':
             {'offset':6,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'TxBiasHighAlarm':
             {'offset':8,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_bias}},
        'TxBiasLowAlarm':
             {'offset':10,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_bias}},
        'TxBiasHighWarning':
             {'offset':12,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_bias}},
        'TxBiasLowWarning':
             {'offset':14,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_bias}},
        'TxPowerHighAlarm':
             {'offset':16,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'TxPowerLowAlarm':
             {'offset':18,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'TxPowerHighWarning':
             {'offset':20,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'TxPowerLowWarning':
             {'offset':22,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}}}

    dom_channel_monitor_masks = {
        'Rx1PowerHighAlarm':
             {'offset':0,
              'bit': 7,
              'type': 'bitvalue'},
        'Rx1PowerLowAlarm':
             {'offset':0,
              'bit': 6,
              'type': 'bitvalue'},
        'Rx1PowerHighWarning':
             {'offset':0,
              'bit': 5,
              'type': 'bitvalue'},
        'Rx1PowerLowWarning':
             {'offset':0,
              'bit': 4,
              'type': 'bitvalue'},
        'Rx2PowerHighAlarm':
             {'offset':0,
              'bit': 3,
              'type': 'bitvalue'},
        'Rx2PowerLowAlarm':
             {'offset':0,
              'bit': 2,
              'type': 'bitvalue'},
        'Rx2PowerHighWarning':
             {'offset':0,
              'bit': 1,
              'type': 'bitvalue'},
        'Rx2PowerLowWarning':
             {'offset':0,
              'bit': 0,
              'type': 'bitvalue'},
        'Rx3PowerHighAlarm':
             {'offset':1,
              'bit': 7,
              'type': 'bitvalue'},
        'Rx3PowerLowAlarm':
             {'offset':1,
              'bit': 6,
              'type': 'bitvalue'},
        'Rx3PowerHighWarning':
             {'offset':1,
              'bit': 5,
              'type': 'bitvalue'},
        'Rx3PowerLowWarning':
             {'offset':1,
              'bit': 4,
              'type': 'bitvalue'},
        'Rx4PowerHighAlarm':
             {'offset':1,
              'bit': 3,
              'type': 'bitvalue'},
        'Rx4PowerLowAlarm':
             {'offset':1,
              'bit': 2,
              'type': 'bitvalue'},
        'Rx4PowerHighWarning':
             {'offset':1,
              'bit': 1,
              'type': 'bitvalue'},
        'Rx4PowerLowWarning':
             {'offset':1,
              'bit': 0,
              'type': 'bitvalue'},
        'Tx1BiasHighAlarm':
             {'offset':2,
              'bit': 7,
              'type': 'bitvalue'},
        'Tx1BiasLowAlarm':
             {'offset':2,
              'bit': 6,
              'type': 'bitvalue'},
        'Tx1BiasHighWarning':
             {'offset':2,
              'bit': 5,
              'type': 'bitvalue'},
        'Tx1BiasLowWarning':
             {'offset':2,
              'bit': 4,
              'type': 'bitvalue'},
        'Tx2BiasHighAlarm':
             {'offset':2,
              'bit': 3,
              'type': 'bitvalue'},
        'Tx2BiasLowAlarm':
             {'offset':2,
              'bit': 2,
              'type': 'bitvalue'},
        'Tx2BiasHighWarning':
             {'offset':2,
              'bit': 1,
              'type': 'bitvalue'},
        'Tx2BiasLowWarning':
             {'offset':2,
              'bit': 0,
              'type': 'bitvalue'},
        'Tx3BiasHighAlarm':
             {'offset':3,
              'bit': 7,
              'type': 'bitvalue'},
        'Tx3BiasLowAlarm':
             {'offset':3,
              'bit': 6,
              'type': 'bitvalue'},
        'Tx3BiasHighWarning':
             {'offset': 3,
              'bit': 5,
              'type': 'bitvalue'},
        'Tx3BiasLowWarning':
             {'offset': 3,
              'bit': 4,
              'type': 'bitvalue'},
        'Tx4BiasHighAlarm':
             {'offset': 3,
              'bit': 3,
              'type': 'bitvalue'},
        'Tx4BiasLowAlarm':
             {'offset': 3,
              'bit': 2,
              'type': 'bitvalue'},
        'Tx4BiasHighWarning':
             {'offset': 3,
              'bit': 1,
              'type': 'bitvalue'},
        'Tx4BiasLowWarning':
             {'offset': 3,
              'bit': 0,
              'type': 'bitvalue'}}

    dom_tx_disable = {
        'Tx4Disable':
             {'offset':0,
              'bit': 3,
              'type': 'bitvalue'},
        'Tx3Disable':
             {'offset':0,
              'bit': 2,
              'type': 'bitvalue'},
        'Tx2Disable':
             {'offset':0,
              'bit': 1,
              'type': 'bitvalue'},
        'Tx1Disable':
             {'offset':0,
              'bit': 0,
              'type': 'bitvalue'}}

    dom_power_control = {
        'PowerSet':
             {'offset': 0,
              'bit': 1,
              'type': 'bitvalue'},
        'PowerOverRide':
             {'offset': 0,
              'bit': 0,
              'type': 'bitvalue'}}

    dom_threshold_map = {
        'ChannelThresholdValues':
             {'offset': 11,
              'size': 2,
              'type': 'nested',
              'decode': dom_channel_threshold_values},
        'ChannelMonitorMasks':
             {'offset': 12,
              'size': 2,
              'type': 'nested',
              'decode': dom_channel_monitor_masks},
        'ModuleThresholdValues':
             {'offset': 13,
              'size': 2,
              'type': 'nested',
              'decode': dom_module_threshold_values}}

    dom_control_bytes_masks = {
        'TX4Disable':
            {'offset': 0,
             'bit': 3,
             'type': 'bitvalue'},
        'TX3Disable':
            {'offset': 0,
             'bit': 2,
             'type': 'bitvalue'},
        'TX2Disable':
            {'offset': 0,
             'bit': 1,
             'type': 'bitvalue'},
        'TX1Disable':
            {'offset': 0,
             'bit': 0,
             'type': 'bitvalue'},
        # RxXRateSelect & Tx4RateSelect are not supported yet.
        'Rx4AppSelect':
            {'offset': 3,
             'size': 1,
             'type': 'int'},
        'Rx3AppSelect':
            {'offset': 4,
             'size': 1,
             'type': 'int'},
        'Rx2AppSelect':
            {'offset': 5,
             'size': 1,
             'type': 'int'},
        'Rx1AppSelect':
            {'offset': 6,
             'size': 1,
             'type': 'int'},
        'PowerSet':
            {'offset': 7,
             'bit': 1,
             'type': 'bitvalue'},
        'PowerOverride':
            {'offset': 7,
             'bit': 0,
             'type': 'bitvalue'},
    }

    #SFF8436 Table 39, Option Values (Address 192-195) (Page 00)
    #each field indicates whether that feature is supported on this module
    dom_option_value_masks = {
        'RXOutputAmplitudeProgramming':
            {'offset': 1,
             'bit': 0,
             'type': 'bitvalue'},
        'RxSquelchDisable':
            {'offset': 2,
             'bit': 3,
             'type': 'bitvalue'},
        'RxOutputDisableCapable':
            {'offset': 2,
             'bit': 2,
             'type': 'bitvalue'},
        'TxSquelchDisable':
            {'offset': 2,
             'bit': 1,
             'type': 'bitvalue'},
        'TxSquelch':
            {'offset': 2,
             'bit': 0,
             'type': 'bitvalue'},
        'MemoryPage02Provided':
            {'offset': 3,
             'bit': 7,
             'type': 'bitvalue'},
        'MemoryPage01Provided':
            {'offset': 3,
             'bit': 6,
             'type': 'bitvalue'},
        'RATE_SELECT':
            {'offset': 3,
             'bit': 5,
             'type': 'bitvalue'},
        'TxDisable':
            {'offset': 3,
             'bit': 4,
             'type': 'bitvalue'},
        'TxFault':
            {'offset': 3,
             'bit': 3,
             'type': 'bitvalue'},
        'TxSquelch_OMA_or_ReducePave':
            {'offset': 3,
             'bit': 2,
             'type': 'bitvalue'},
        'TxLOS':
            {'offset': 3,
             'bit': 1,
             'type': 'bitvalue'},
    }


    def __init__(self, eeprom_raw_data=None, calibration_type=1):
        self._calibration_type = calibration_type
        start_pos = 0

        if eeprom_raw_data != None:
            self.dom_data = sffbase.parse(self, self.dom_map,
                          eeprom_raw_data, start_pos)

    def parse(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_map, eeprom_raw_data,
                    start_pos)

# Parser functions for specific values interested by SNMP
    def parse_sfp_dom_rev(self, type_raw_data, start_pos):
        return sffbase.parse(self, self.sfp_dom_rev, type_raw_data, start_pos)

    def parse_temperature(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_temperature, eeprom_raw_data,
                    start_pos)

    def parse_voltage(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_voltage, eeprom_raw_data,
                    start_pos)

    def parse_channel_monitor_params(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_channel_monitor_params, eeprom_raw_data,
                    start_pos)

    def parse_channel_monitor_params_with_tx_power(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_channel_monitor_params_with_tx_power, eeprom_raw_data,
                    start_pos)

    def parse_module_threshold_values(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_threshold_values, eeprom_raw_data,
                    start_pos)

    def parse_channel_threshold_values(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_channel_threshold_values, eeprom_raw_data,
                    start_pos)

    def parse_channel_monitor_mask(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_channel_monitor_masks, eeprom_raw_data,
                    start_pos)

    def parse_control_bytes(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_control_bytes_masks, eeprom_raw_data, start_pos)

    def parse_module_monitor_params(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_monitor, eeprom_raw_data,
                    start_pos)

    def parse_option_params(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_option_value_masks, eeprom_raw_data,
                    start_pos)

    def parse_dom_status_indicator(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_status_indicator, eeprom_raw_data,
                start_pos)

    def parse_dom_channel_status(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_channel_status, eeprom_raw_data,
                start_pos)

    def parse_dom_tx_rx_los(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_tx_rx_los, eeprom_raw_data,
                start_pos)

    def parse_dom_tx_fault(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_tx_fault, eeprom_raw_data,
                start_pos)

    def parse_dom_tx_disable (self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_tx_disable, eeprom_raw_data,
                start_pos)

    def parse_dom_power_control(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_power_control, eeprom_raw_data,
                start_pos)

    def dump_pretty(self):
        if self.dom_data == None:
            print('Object not initialized, nothing to print')
            return
        sffbase.dump_pretty(self, self.dom_data)

    def get_data(self):
        return self.dom_data

    def get_data_pretty(self):
        return sffbase.get_data_pretty(self, self.dom_data)
