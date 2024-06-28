#--------------------------------------------------------------------------
#
# Copyright 2012 Cumulus Networks, inc  all rights reserved
#
#--------------------------------------------------------------------------

from __future__ import print_function

try:
    import struct
    from .sff8024 import type_of_transceiver    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import type_abbrv_name    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sffbase import sffbase    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

#------------------------------------------------------------------------------

class sff8472InterfaceId(sffbase):
    """Parser and interpreter for Two wire Interface ID Data fields
    - Address A0h

    Base types:
    XXX - Complete documentation

    outtype - can be used to dictate the type of output you get
    Mainly used with bitmap type.
    if outtype == 'allbits':
        parse gives all bitnames with values
    if outtype == 'onbits':
        parse gives all onbits with value = None
    """

    version = '1.0'

    transceiver_codes = {   '10GEthernetComplianceCode':
                {'offset':3,
                 'size':1,
                 'type' : 'bitmap',
                 'decode' : {'10G Base-ER':
                        {'offset': 3,
                         'bit': 7},
                         '10G Base-LRM':
                        {'offset': 3,
                         'bit': 6},
                         '10G Base-LR':
                        {'offset': 3,
                         'bit': 5},
                         '10G Base-SR':
                        {'offset': 3,
                         'bit': 4}}},
                'InfinibandComplianceCode':
                {'offset':3,
                 'size':1,
                 'type' : 'bitmap',
                 'decode' : {'1X SX':
                        {'offset': 3,
                         'bit': 3},
                         '1X LX':
                        {'offset': 3,
                         'bit': 2},
                         '1X Copper Active':
                        {'offset': 3,
                         'bit': 1},
                         '1X Copper Passive':
                        {'offset': 3,
                         'bit': 0}}},
                'ESCONComplianceCodes':
                {'offset':4,
                 'size':1,
                 'type' : 'bitmap',
                 'decode' : {'ESCON MMF, 1310nm LED':
                        {'offset': 4,
                        'bit': 7},
                         'ESCON SMF, 1310nm Laser':
                        {'offset': 4,
                        'bit': 6}}},
                'SONETComplianceCodes':
                {'offset': 4,
                 'size':2,
                 'type' : 'bitmap',
                 'decode' : {   'OC-192, short reach':
                            {'offset': 4,
                            'bit': 5},
                        'SONET reach specifier bit 1':
                            {'offset': 4,
                             'bit': 4},
                        'SONET reach specifier bit 2':
                            {'offset': 4,
                            'bit': 3},
                        'OC-48, long reach':
                            {'offset': 4,
                            'bit': 2},
                        'OC-48, intermediate reach':
                            {'offset': 4,
                             'bit': 1},
                        'OC-48, short reach':
                            {'offset': 4,
                             'bit': 0},
                        'OC-12, single mode, long reach':
                            {'offset': 5,
                             'bit': 6},
                        'OC-12, single mode, inter reach':
                            {'offset': 5,
                             'bit': 5},
                        'OC-12, short reach':
                            {'offset': 5,
                             'bit': 4},
                        'OC-3, single mode, long reach':
                            {'offset': 5,
                             'bit': 2},
                        'OC-3, single mode, inter reach':
                            {'offset': 5,
                             'bit': 1},
                        'OC-3, short reach':
                            {'offset': 5,
                             'bit': 0}}},
                'EthernetComplianceCodes':
                    {'offset': 6,
                     'size':2,
                     'type' : 'bitmap',
                     'decode' : {
                        'BASE-PX':
                            {'offset': 6,
                             'bit': 7},
                        'BASE-BX10':
                            {'offset': 6,
                            'bit': 6},
                        '100BASE-FX':
                            {'offset': 6,
                            'bit': 5},
                        '100BASE-LX/LX10':
                            {'offset': 6,
                            'bit': 4},
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
                'FibreChannelLinkLength':
                    {'offset': 7,
                     'size':2,
                     'type' : 'bitmap',
                     'decode' :
                        {'very long distance (V)':
                            {'offset': 7,
                            'bit': 7},
                        'short distance (S)':
                            {'offset': 7,
                            'bit': 6},
                        'Intermediate distance (I)':
                            {'offset': 7,
                            'bit': 5},
                        'Long distance (L)':
                            {'offset': 7,
                            'bit': 4},
                        'medium distance (M)':
                            {'offset': 7,
                            'bit': 3}}},
                    'FibreChannelTechnology':
                    {'offset': 7,
                     'size':2,
                     'type' : 'bitmap',
                     'decode' :
                        {'Shortwave laser, linear Rx (SA)':
                            {'offset': 7,
                             'bit': 2},
                        'Longwave Laser (LC)':
                            {'offset': 7,
                            'bit': 1},
                        'Electrical inter-enclosure (EL)':
                            {'offset': 7,
                             'bit': 0},
                        'Electrical intra-enclosure (EL)':
                            {'offset': 8,
                            'bit': 7},
                        'Shortwave laser w/o OFC (SN)':
                            {'offset': 8,
                            'bit': 6},
                        'Shortwave laser with OFC (SL)':
                            {'offset': 8,
                            'bit': 5},
                        'Longwave laser (LL)':
                            {'offset': 8,
                            'bit': 4}}},
                'SFP+CableTechnology':
                    {'offset': 7,
                     'size':2,
                     'type' : 'bitmap',
                     'decode' :
                        {'Active Cable':
                            {'offset': 8,
                            'bit': 3},
                        'Passive Cable':
                            {'offset': 8,
                             'bit': 2}}},
                    'FibreChannelTransmissionMedia':
                    {'offset': 7,
                     'size':2,
                     'type' : 'bitmap',
                     'decode' :
                        {'Twin Axial Pair (TW)':
                            {'offset': 9,
                             'bit': 7},
                         'Twisted Pair (TP)':
                            {'offset': 9,
                            'bit': 6},
                        'Miniature Coax (MI)':
                            {'offset': 9,
                            'bit': 5},
                        'Video Coax (TV)':
                            {'offset': 9,
                            'bit': 4},
                        'Multimode, 62.5um (M6)':
                            {'offset': 9,
                            'bit': 3},
                        'Multimode, 50um (M5, M5E)':
                            {'offset': 9,
                            'bit': 2},
                        'Single Mode (SM)':
                            {'offset': 9,
                            'bit': 0}}},
                'FibreChannelSpeed':
                    {'offset': 7,
                     'size':2,
                     'type': 'bitmap',
                     'decode' :
                        {'1200 MBytes/sec':
                            {'offset': 10,
                            'bit': 7},
                        '800 MBytes/sec':
                            {'offset': 10,
                            'bit': 6},
                        '1600 MBytes/sec':
                            {'offset': 10,
                            'bit': 5},
                        '400 MBytes/sec':
                            {'offset': 10,
                            'bit': 4},
                        '200 MBytes/sec':
                            {'offset': 10,
                            'bit': 2},
                        '100 MBytes/sec':
                            {'offset': 10,
                            'bit': 0}}}}

    exttypeoftransceiver = {'00': 'GBIC def not specified',
                '01':'GBIC is compliant with MOD_DEF 1',
                '02':'GBIC is compliant with MOD_DEF 2',
                '03':'GBIC is compliant with MOD_DEF 3',
                '04':'GBIC/SFP defined by twowire interface ID',
                '05':'GBIC is compliant with MOD_DEF 5',
                '06':'GBIC is compliant with MOD_DEF 6',
                '07':'GBIC is compliant with MOD_DEF 7'}

    connector = {'00': 'Unknown',
             '01': 'SC',
             '02': 'Fibre Channel Style 1 copper connector',
             '03': 'Fibre Channel Style 2 copper connector',
             '04': 'BNC/TNC',
             '05': 'Fibre Channel coaxial headers',
             '06': 'FibreJack',
             '07': 'LC',
             '08': 'MT-RJ',
             '09': 'MU',
             '0a': 'SG',
             '0b': 'Optical pigtail',
             '0c': 'MPO Parallel Optic',
             '20': 'HSSDCII',
             '21': 'CopperPigtail',
             '22': 'RJ45'}

    encoding_codes = {'00':'Unspecified',
              '01':'8B/10B',
              '02':'4B/5B',
              '03':'NRZ',
              '04':'Manchester',
              '05': 'SONET Scrambled',
              '06':'64B/66B'}

    rate_identifier = {'00':'Unspecified',
               '01':'Defined for SFF-8079 (4/2/1G Rate_Select & AS0/AS1)',
               '02': 'Defined for SFF-8431 (8/4/2G Rx Rate_Select only)',
               '03':'Unspecified',
               '04': 'Defined for SFF-8431 (8/4/2G Tx Rate_Select only)',
               '05':'Unspecified',
               '06':'Defined for SFF-8431 (8/4/2G Independent Rx & Tx Rate_select)',
               '07':'Unspecified',
               '08': 'Defined for FC-PI-5 (16/8/4G Rx Rate_select only) High=16G only, Low=8G/4G',
               '09': 'Unspecified',
               '0a': 'Defined for FC-PI-5 (16/8/4G Independent Rx, Tx Rate_select) High=16G only, Low=8G/4G'}


    interface_id = {'TypeOfTransceiver':
                {'offset':0,
                 'size':1,
                 'type' : 'enum',
                 'decode' : type_of_transceiver},
             'ExtIdentOfTypeOfTransceiver':
                {'offset':1,
                 'size':1,
                 'type' : 'enum',
                 'outlevel' : 2,
                 'decode': exttypeoftransceiver},
             'Connector':
                {'offset':2,
                 'size':1,
                 'type' : 'enum',
                 'decode': connector},
            'EncodingCodes':
                {'offset':11,
                 'size':1,
                 'type' : 'enum',
                 'decode' : encoding_codes},
            'VendorName':
                {'offset' : 20,
                 'size' : 16,
                 'type' : 'str'},
            'VendorOUI':
                {'offset':37,
                 'size':3,
                 'type' : 'hex'},
            'VendorPN':
                {'offset':40,
                 'size':16,
                 'type' : 'str'},
            'VendorSN':
                {'offset':68,
                 'size':16,
                 'type' : 'str'},
            'VendorRev':
                {'offset':56,
                 'size':4,
                 'type' : 'str'},
            'CalibrationType':
                {'offset':92,
                 'size':1,
                 'type' : 'bitmap',
                 'short_name' : 'calType',
                 'decode' : {'Internally Calibrated':
                        {'offset': 92,
                         'bit':5},
                         'Externally Calibrated':
                        {'offset': 92,
                         'bit':4},
                             }},
            'ReceivedPowerMeasurementType':
                {'offset':92,
                 'size':1,
                 'type' : 'bitmap',
                 'decode' : {'Avg power':
                        {'offset': 92,
                         'bit':3},
                         'OMA':
                        {'offset': 92,
                         'bit':3,
                             'value':0}}},
            'RateIdentifier':
                {'offset':13,
                 'size':1,
                 'type' : 'enum',
                 'decode' : rate_identifier},
            'TransceiverCodes':
                {'offset' : 3,
                 'type' : 'nested',
                 'decode' : transceiver_codes},
            'NominalSignallingRate(UnitsOf100Mbd)':
                {'offset': 12,
                 'size':1,
                 'type':'int'},
            'LengthSMFkm-UnitsOfKm':
                {'offset':14,
                 'size':1,
                 'type':'int'},
            'LengthSMF(UnitsOf100m)':
                {'offset':15,
                 'size':1,
                 'type':'int'},
            'Length50um(UnitsOf10m)':
                {'offset':16,
                'size':1,
                 'type':'int'},
            'Length62.5um(UnitsOfm)':
                {'offset':17,
                'size':1,
                 'type':'int'},
            'LengthCable(UnitsOfm)':
                {'offset':18,
                'size':1,
                 'type':'int'},
            'LengthOM3(UnitsOf10m)':
                {'offset':19,
                 'size':1,
                 'type':'int'},
            'VendorDataCode(YYYY-MM-DD Lot)':
                {'offset':84,
                'size':8,
                'type': 'date'}}

# Parser for specific values that interested by SNMP

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
                 'decode': exttypeoftransceiver},
             'Connector':
                {'offset':2,
                 'size':1,
                 'type' : 'enum',
                 'decode': connector},
            'Specification compliance':
                {'offset' : 3,
                 'type' : 'nested',
                 'decode' : transceiver_codes},
            'EncodingCodes':
                {'offset':11,
                 'size':1,
                 'type' : 'enum',
                 'decode' : encoding_codes},
            'NominalSignallingRate(UnitsOf100Mbd)':
                {'offset': 12,
                 'size':1,
                 'type':'int'},
            'RateIdentifier':
                {'offset':13,
                 'size':1,
                 'type' : 'enum',
                 'decode' : rate_identifier},
            'LengthSMFkm-UnitsOfKm':
                {'offset':14,
                 'size':1,
                 'type':'int'},
            'LengthSMF(UnitsOf100m)':
                {'offset':15,
                 'size':1,
                 'type':'int'},
            'Length50um(UnitsOf10m)':
                {'offset':16,
                'size':1,
                 'type':'int'},
            'Length62.5um(UnitsOfm)':
                {'offset':17,
                'size':1,
                 'type':'int'},
            'LengthCable(UnitsOfm)':
                {'offset':18,
                'size':1,
                 'type':'int'},
            'LengthOM3(UnitsOf10m)':
                {'offset':19,
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
             'size': 4,
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

    sfp_dom_capability = {
        'sff8472_dom_support':
            {'offset': 0,
             'bit': 6,
             'type': 'bitvalue'}
        }

    # Returns calibration type
    def _get_calibration_type(self, eeprom_data):
        try:
            data = int(eeprom_data[92], 16)
            if self.test_bit(data, 5) != 0:
                return 1  # internally calibrated
            elif self.test_bit(data, 4) != 0:
                return 2  # externally calibrated
            else:
                return 0  # Could not find calibration type
        except Exception:
            return 0

    def __init__(self, eeprom_raw_data=None):
        self.interface_data = None
        start_pos = 0

        if eeprom_raw_data != None:
            self.interface_data = sffbase.parse(self,
                            self.interface_id,
                            eeprom_raw_data, start_pos)
            self.calibration_type = self._get_calibration_type(
                            eeprom_raw_data)

    def parse(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.interface_id, eeprom_raw_data, start_pos)

#new parser functions for specific values that interested by SNMP
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

    def parse_dom_capability(self, dom_type_raw_data, start_pos):
        return sffbase.parse(self, self.sfp_dom_capability, dom_type_raw_data, start_pos)

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

class sff8472Dom(sffbase):
    """Parser and interpretor for Diagnostics data fields at address A2h"""

    version = '1.0'

    dom_ext_calibration_constants = {'RX_PWR_4':
                        {'offset':56,
                         'size':4},
                    'RX_PWR_3':
                        {'offset':60,
                        'size':4},
                        'RX_PWR_2':
                        {'offset':64,
                         'size':4},
                        'RX_PWR_1':
                        {'offset':68,
                         'size':4},
                        'RX_PWR_0':
                        {'offset':72,
                         'size':4},
                        'TX_I_Slope':
                        {'offset':76,
                         'size':2},
                    'TX_I_Offset':
                        {'offset':78,
                         'size':2},
                    'TX_PWR_Slope':
                        {'offset':80,
                         'size':2},
                    'TX_PWR_Offset':
                        {'offset':82,
                         'size':2},
                    'T_Slope':
                        {'offset':84,
                         'size':2},
                    'T_Offset':
                        {'offset':86,
                         'size':2},
                    'V_Slope':
                        {'offset':88,
                         'size':2},
                    'V_Offset':
                        {'offset':90,
                         'size':2}}


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

                # SFF-8472 Rev 12.4 section 9.3 5)
                # Rx_PWR (uW) = Rx_PWR(4) * Rx_PWR_ADe4 (16 bit unsigned integer) +
                #               Rx_PWR(3) * Rx_PWR_ADe3 (16 bit unsigned integer) +
                #               Rx_PWR(2) * Rx_PWR_ADe2 (16 bit unsigned integer) +
                #               Rx_PWR(1) * Rx_PWR_AD (16 bit unsigned integer) +
                #               Rx_PWR(0)
                rx_pwr_ad = result
                result = 0
                for i in range(0, 5):
                    field_name = f'RX_PWR_{i}'
                    rx_pwr = self.dom_ext_calibration_constants[field_name]
                    off = rx_pwr['offset']
                    size = rx_pwr['size']
                    coeff = self.float_from_bytes(eeprom_data[off:off+size])
                    result += coeff * rx_pwr_ad ** i

                result = result * 0.0001 # uW to mW
                #print(indent, name, " : ", power_in_dbm_str(result))
                retval = self.power_in_dbm_str(result)
            else:
                retval = 'Unknown'
        except Exception as err:
            retval = str(err)

        return retval


    dom_aw_thresholds = {   'TempHighAlarm':
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
                'VoltageHighAlarm':
                    {'offset':8,
                    'size':2,
                    'type': 'func',
                    'decode': { 'func':calc_voltage}},
                'VoltageLowAlarm':
                    {'offset':10,
                     'size':2,
                     'type': 'func',
                    'decode': { 'func':calc_voltage}},
                'VoltageHighWarning':
                    {'offset':12,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_voltage}},
                'VoltageLowWarning':
                    {'offset':14,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_voltage}},
                'BiasHighAlarm':
                    {'offset':16,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_bias}},
                'BiasLowAlarm':
                    {'offset':18,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_bias}},
                'BiasHighWarning':
                    {'offset':20,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_bias}},
                'BiasLowWarning':
                    {'offset':22,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_bias}},
                'TXPowerHighAlarm':
                    {'offset':24,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_tx_power}},
                'TXPowerLowAlarm':
                    {'offset':26,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_tx_power}},
                'TXPowerHighWarning':
                    {'offset':28,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_tx_power}},
                'TXPowerLowWarning':
                    {'offset':30,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_tx_power}},
                'RXPowerHighAlarm':
                    {'offset':32,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_rx_power}},
                'RXPowerLowAlarm':
                    {'offset':34,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_rx_power}},
                'RXPowerHighWarning':
                    {'offset':36,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_rx_power}},
                'RXPowerLowWarning':
                    {'offset':38,
                     'size':2,
                     'type': 'func',
                     'decode': { 'func':calc_rx_power}}}

    dom_monitor = {'Temperature':
                {'offset':96,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_temperature}},
                 'Vcc':
                {'offset':98,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_voltage}},
                 'TXBias':
                {'offset':100,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_bias}},
                 'TXPower':
                {'offset':102,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_tx_power}},
                 'RXPower':
                {'offset':104,
                 'size':2,
                 'type': 'func',
                 'decode': { 'func':calc_rx_power}}}

    dom_status_control = {  'TXDisableState':
                    {'offset': 110,
                     'bit': 7,
                     'type': 'bitvalue'},
                'SoftTXDisableSelect':
                    {'offset': 110,
                     'bit': 6,
                     'type': 'bitvalue'},
                'RS1State':
                    {'offset': 110,
                     'bit': 5,
                     'type': 'bitvalue'},
                'RateSelectState':
                    {'offset': 110,
                     'bit': 4,
                     'type': 'bitvalue'},
                'SoftRateSelect':
                    {'offset': 110,
                     'bit': 3,
                     'type': 'bitvalue'},
                'TXFaultState':
                    {'offset': 110,
                     'bit': 2,
                     'type': 'bitvalue'},
                'RXLOSState':
                    {'offset': 110,
                     'bit': 1,
                     'type': 'bitvalue'},
                'DataReadyBarState':
                    {'offset': 110,
                     'bit': 0,
                    'type': 'bitvalue'}}

    dom_alarm_flags = {'TempHighAlarm':
                {'offset':112,
                 'bit':7,
                'type': 'bitvalue'},
               'TempLowAlarm':
                {'offset':112,
                 'bit':6,
                'type': 'bitvalue'},
               'VccHighAlarm':
                {'offset':112,
                 'bit':5,
                'type': 'bitvalue'},
               'VccLowAlarm':
                {'offset':112,
                 'bit':4,
                'type': 'bitvalue'},
               'TXBiasHighAlarm':
                {'offset':112,
                 'bit':3,
                'type': 'bitvalue'},
               'TXBiasLowAlarm':
                {'offset':112,
                 'bit':2,
                 'type': 'bitvalue'},
               'TXPowerHighAlarm':
                {'offset':112,
                 'bit':1,
                'type': 'bitvalue'},
               'TXPowerLowAlarm':
                {'offset':112,
                 'bit':0,
                'type': 'bitvalue'},
               'RXPowerHighAlarm':
                {'offset':113,
                 'bit':7,
                'type': 'bitvalue'},
               'RXPowerLowAlarm':
                {'offset':113,
                 'bit':6,
                'type': 'bitvalue'}}

    dom_warning_flags = {   'TempHighWarning':
                    {'offset':116,
                     'bit':7,
                     'type': 'bitvalue'},
                'TempLowWarning':
                    {'offset':116,
                     'bit':6,
                     'type': 'bitvalue'},
                    'VccHighWarning':
                    {'offset':116,
                     'bit':5,
                     'type': 'bitvalue'},
                    'VccLowWarning':
                    {'offset':116,
                     'bit':4,
                     'type': 'bitvalue'},
                    'TXBiasHighWarning':
                    {'offset':116,
                     'bit':3,
                     'type': 'bitvalue'},
                    'TXBiasLowWarning':
                    {'offset':116,
                     'bit':2,
                    'type': 'bitvalue'},
                'TXPowerHighWarning':
                    {'offset':116,
                    'bit':1,
                    'type': 'bitvalue'},
                'TXPowerLowWarning':
                    {'offset':116,
                    'bit':0,
                    'type': 'bitvalue'},
                'RXPowerHighWarning':
                    {'offset':117,
                     'bit':7,
                    'type': 'bitvalue'},
                'RXPowerLowWarning':
                    {'offset':117,
                    'bit':6,
                    'type': 'bitvalue'}}

    dom_map = {'AwThresholds':
            {'offset' : 0,
             'size' : 40,
             'type' : 'nested',
             'decode' : dom_aw_thresholds},
            'MonitorData':
            {'offset':96,
             'size':10,
             'type' : 'nested',
             'decode': dom_monitor},
           'StatusControl':
            {'offset':110,
             'size':1,
             'type' : 'nested',
             'decode':dom_status_control},
           'AlarmFlagStatus':
            {'offset':112,
             'size':2,
             'type' : 'nested',
             'decode':dom_alarm_flags},
           'WarningFlagStatus':
            {'offset':112,
             'size':2,
             'type' : 'nested',
             'decode':dom_warning_flags}}

# parsers for specific values that interested by SNMP
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
             'decode': {'func':calc_voltage}}
        }

    dom_channel_monitor_params = {
        'TXBias':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TXPower':
            {'offset': 2,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'RXPower':
            {'offset': 4,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}}
        }
    dom_module_monitor = {
        'TempHighAlarm':
            {'offset':0,
            'bit':7,
            'type': 'bitvalue'},
        'TempLowAlarm':
             {'offset':0,
             'bit':6,
             'type': 'bitvalue'},
        'TempHighWarning':
             {'offset': 4,
             'bit': 7,
             'type': 'bitvalue'},
        'TempLowWarning':
             {'offset': 4,
             'bit': 6,
             'type': 'bitvalue'},
        'VccHighAlarm':
             {'offset': 0,
             'bit': 5,
             'type': 'bitvalue'},
        'VccLowAlarm':
              {'offset': 0,
              'bit': 4,
              'type': 'bitvalue'},
        'VccHighWarning':
             {'offset': 4,
             'bit': 5,
             'type': 'bitvalue'},
        'VccLowWarning':
             {'offset': 4,
             'bit': 4,
             'type': 'bitvalue'}}

    dom_channel_thresh_monitor_params = {
          'BiasHighAlarm':
              {'offset':0,
              'bit':3,
              'type': 'bitvalue'},
          'BiasLowAlarm':
              {'offset':0,
              'bit':2,
              'type': 'bitvalue'},
          'BiasHighWarning':
               {'offset':4,
               'bit':3,
               'type': 'bitvalue'},
          'BiasLowWarning':
                {'offset':4,
                'bit':2,
                'type': 'bitvalue'},
          'TxPowerHighAlarm':
                 {'offset':0,
                 'bit':1,
                 'type': 'bitvalue'},
          'TxPowerLowAlarm':
                 {'offset':0,
                 'bit':0,
                 'type': 'bitvalue'},
          'TxPowerHighWarning':
                  {'offset':4,
                  'bit':1,
                  'type': 'bitvalue'},
          'TxPowerLowWarning':
                  {'offset':4,
                  'bit':0,
                  'type': 'bitvalue'},
          'RxPowerHighAlarm':
                  {'offset':1,
                  'bit':7,
                  'type': 'bitvalue'},
          'RxPowerLowAlarm':
                  {'offset':1,
                  'bit':6,
                  'type': 'bitvalue'},
          'RxPowerHighWarning':
                 {'offset':5,
                 'bit':7,
                 'type': 'bitvalue'},
          'RxPowerLowWarning':
                 {'offset':5,
                 'bit':6,
                  'type': 'bitvalue'}
    }

    def __init__(self, eeprom_raw_data=None, calibration_type=0):
        self._calibration_type = calibration_type
        start_pos = 0

        if eeprom_raw_data != None:
            self.dom_data = sffbase.parse(self, self.dom_map,
                              eeprom_raw_data, start_pos)

    def parse(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_map, eeprom_raw_data, start_pos)

# parser functions for specific values interested by SNMP
    def parse_temperature(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_temperature, eeprom_raw_data,
                    start_pos)

    def parse_voltage(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_voltage, eeprom_raw_data,
                    start_pos)

    def parse_channel_monitor_params(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_channel_monitor_params, eeprom_raw_data,
                    start_pos)

    def parse_module_monitor_params(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_monitor, eeprom_raw_data,
                    start_pos)

    def parse_channel_thresh_monitor_params(self, eeprom_raw_data, start_pos):
         return sffbase.parse(self, self.dom_channel_thresh_monitor_params, eeprom_raw_data,
                     start_pos)

    def parse_alarm_warning_threshold(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_aw_thresholds, eeprom_raw_data,
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

