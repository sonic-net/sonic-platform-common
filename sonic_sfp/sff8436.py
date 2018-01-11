#! /usr/bin/env python
#----------------------------------------------------------------------------
# SFF-8436 QSFP+ 10 Gbs 4X PLUGGABLE TRANSCEIVER
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
    from sffbase import sffbase
except ImportError, e:
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

    type_of_transceiver = {
            '00':'Unknown or unspecified',
            '01':'GBIC',
            '02': 'Module/connector soldered to motherboard',
            '03': 'SFP',
            '04': '300 pin XBI',
            '05': 'XENPAK',
            '06': 'XFP',
            '07': 'XFF',
            '08': 'XFP-E',
            '09': 'XPAK',
            '0a': 'X2',
            '0b': 'DWDM-SFP',
            '0c': 'QSFP',
            '0d': 'QSFP+'
            }

    ext_type_of_transceiver = {}

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
            '0C': 'MPO',
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
            '06': 'Manchester'
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

    def dump_pretty(self):
        if self.interface_data == None:
            print 'Object not initialized, nothing to print'
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
        except Exception, err:
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
                #print indent, name, ' : %.4f' %result, 'Volts'
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
                #print indent, name, ' : %.4f' %result, 'Volts'
                retval = '%.4f' %result + 'Volts'
            else:
                #print indent, name, ' : Unknown'
                retval = 'Unknown'
        except Exception, err:
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
                #print indent, name, ' : %.4f' %result, 'mA'
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
                #print indent, name, ' : %.4f' %result, 'mA'
                retval = '%.4f' %result + 'mA'
            else:
                retval = 'Unknown'
        except Exception, err:
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
                #print indent, name, ' : ', power_in_dbm_str(result)
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
        except Exception, err:
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
                #print indent, name, " : ", power_in_dbm_str(result)
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
                #print indent, name, " : ", power_in_dbm_str(result)
                retval = self.power_in_dbm_str(result)
            else:
                retval = 'Unknown'
        except Exception, err:
            retval = str(err)

        return retval


    dom_status_indicator = {'DataNotReady':
                {'offset': 2,
                 'bit': 0,
                 'type': 'bitvalue'}}

    dom_channel_status = {'Tx4LOS':
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

    dom_module_monitor = {'TempHighAlarm':
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

    dom_channel_monitor = {'Rx1PowerHighAlarm':
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


    dom_module_monitor_values = {'Temperature':
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


    def __init__(self, eeprom_raw_data=None, calibration_type=1):
        self._calibration_type = calibration_type
        start_pos = 0

        if eeprom_raw_data != None:
            self.dom_data = sffbase.parse(self, self.dom_map,
                          eeprom_raw_data, start_pos)

    def parse(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_map, eeprom_raw_data,
                    start_pos)

    def dump_pretty(self):
        if self.dom_data == None:
            print 'Object not initialized, nothing to print'
            return
        sffbase.dump_pretty(self, self.dom_data)

    def get_data(self):
        return self.dom_data

    def get_data_pretty(self):
        return sffbase.get_data_pretty(self, self.dom_data)
