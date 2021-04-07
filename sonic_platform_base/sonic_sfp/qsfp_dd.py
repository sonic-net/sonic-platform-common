#----------------------------------------------------------------------------
# QSFP-DD 8X Transceiver (QSFP Double Density)
#----------------------------------------------------------------------------

from __future__ import print_function

try:
    from .sff8024 import type_of_transceiver    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import type_abbrv_name    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import connector_dict    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import ext_type_of_transceiver    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import type_of_media_interface    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import host_electrical_interface    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import nm_850_media_interface    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import sm_media_interface    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import passive_copper_media_interface    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import active_cable_media_interface    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from .sff8024 import base_t_media_interface    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
    from sonic_platform_base.sonic_sfp.sffbase import sffbase    # Dot module supports both Python 2 and Python 3 using explicit relative import methods
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

#------------------------------------------------------------------------------

class qsfp_dd_InterfaceId(sffbase):

    def decode_revision_compliance(self, eeprom_data, offset, size):
        # first nibble and second nibble represent the version
        return '%c.%c' % (str((eeprom_data[offset][0] >> 4) & 0x0f), str((eeprom_data[offset][0] & 0x0f)))

    def decode_module_state(self, eeprom_data, offset, size):
        module_state_byte = eeprom_data[offset]
        # bits 1-3
        module_state = (int(module_state_byte, 16) >> 1) & 3
        if module_state == 1:
            return 'Low Power state (Flat memory passive cable assemblies)'
        elif module_state == 2:
            return 'Power Up State'
        elif module_state == 3:
            return 'Ready State'
        elif module_state == 4:
            return 'Power Down State'
        elif module_state == 5:
            return 'Fault State'
        return 'Unknown State %s' % module_state

    def decode_connector(self, eeprom_data, offset, size):
        connector_id = eeprom_data[offset]
        return connector_dict[connector_id]

    def decode_ext_id(self, eeprom_data, offset, size):
        # bits 5-7 represent Module Card Power Class
        ext_id_power_class_byte = eeprom_data[offset]
        ext_id_power_class_code = (int(ext_id_power_class_byte, 16) >> 5) & 3
        # Max power is in multiply of 0.25W
        ext_id_max_power_byte = eeprom_data[offset + 1]
        ext_id_max_power_value = int(ext_id_max_power_byte, 16)
        return ext_type_of_transceiver[str(ext_id_power_class_code)] + "({}W Max)".format(ext_id_max_power_value * 0.25)

    def decode_cable_len(self, eeprom_data, offset, size):
        cable_byte = eeprom_data[offset]
        # base length im meters 0-5 bits
        base_len = int(cable_byte, 16) & 0x3f
        # mult_code 6-7 bits
        mult_code = (int(cable_byte, 16) >> 6) & 0x03
        if mult_code == 0:
            mult = 0.1
        elif mult_code == 1:
            mult = 1
        elif mult_code == 2:
            mult = 10
        else:
            mult = 100

        return base_len * mult

    def decode_media_type(self, eeprom_data, offset, size):
        media_type_code = eeprom_data[offset]
        dict_name = type_of_media_interface[media_type_code]
        if dict_name == "nm_850_media_interface":
            return nm_850_media_interface
        elif dict_name == "sm_media_interface":
            return sm_media_interface
        elif dict_name == "passive_copper_media_interface":
            return passive_copper_media_interface
        elif dict_name == "active_cable_media_interface":
            return active_cable_media_interface
        elif dict_name == "base_t_media_interface":
            return base_t_media_interface
        else:
             return None

    def parse_application(self, sfp_media_type_dict, host_interface, media_interface):
        host_result = host_electrical_interface[host_interface]
        media_result = sfp_media_type_dict[media_interface]
        return host_result, media_result

    version = '1.0'

    connector = {
        'Connector':
            {'offset':0,
             'type' : 'func',
             'decode': {'func': decode_connector}}
    }

    sfp_type = {
        'type':
            {'offset': 0,
             'size': 1,
             'type': 'enum',
             'decode': type_of_transceiver}
        }

    ext_iden = {
        'Extended Identifier':
            {'offset': 0,
             'type': 'func',
             'decode': {'func': decode_ext_id}}
    }

    cable_len = {
        'Length Cable Assembly(m)':
            {'offset': 0,
             'type': 'func',
             'decode': {'func': decode_cable_len}}
    }

    rev_comp = {
        'Revision Compliance':
            {'offset': 0,
             'type': 'func',
             'decode': {'func': decode_revision_compliance}}
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

    vendor_oui = {
        'Vendor OUI':
                {'offset':0,
                 'size':3,
                 'type' : 'hex'}
        }

    qsfp_dd_dom_capability = {
        'Flat_MEM':
            {'offset': 0,
                'bit': 7,
                'type': 'bitvalue'}
        }

    vendor_date = {
        'VendorDataCode(YYYY-MM-DD Lot)':
                {'offset':0,
                'size':8,
                'type': 'date'}
        }

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

    def parse_vendor_date(self, date_raw_data, start_pos):
        return sffbase.parse(self, self.vendor_date, date_raw_data, start_pos)
    
    def parse_vendor_oui(self, vendor_oui_data, start_pos):
        return sffbase.parse(self, self.vendor_oui, vendor_oui_data, start_pos)

    def parse_connector(self, connector_data, start_pos):
        return sffbase.parse(self, self.connector, connector_data, start_pos)

    def parse_ext_iden(self, ext_iden_data, start_pos):
        return sffbase.parse(self, self.ext_iden, ext_iden_data, start_pos)

    def parse_cable_len(self, cable_len_data, start_pos):
        return sffbase.parse(self, self.cable_len, cable_len_data, start_pos)

    def parse_dom_capability(self, dom_capability_raw_data, start_pos):
        return sffbase.parse(self, self.qsfp_dd_dom_capability, dom_capability_raw_data, start_pos)

    def parse_media_type(self, qsfp_media_type_raw_data, start_pos):
        return self.decode_media_type(qsfp_media_type_raw_data, start_pos, 1)

class qsfp_dd_Dom(sffbase):

    version = '1.0'

    def calc_temperature(self, eeprom_data, offset, size):
        try:
            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)

            result = (msb << 8) | (lsb & 0xff)
            result = self.twos_comp(result, 16)

            result = float(result / 256.0)
            retval = '%.4f' %result + 'C'

        except Exception as err:
            retval = str(err)

        return retval


    def calc_voltage(self, eeprom_data, offset, size):
        try:
            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            result = float(result * 0.0001)
            retval = '%.4f' %result + 'Volts'

        except Exception as err:
            retval = str(err)

        return retval


    def calc_bias(self, eeprom_data, offset, size):
        try:
            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            result = float(result * 0.002)
            retval = '%.4f' %result + 'mA'

        except Exception as err:
            retval = str(err)

        return retval


    def calc_tx_power(self, eeprom_data, offset, size):
        try:
            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            result = float(result * 0.0001)
            retval = self.power_in_dbm_str(result)

        except Exception as err:
                retval = str(err)

        return retval


    def calc_rx_power(self, eeprom_data, offset, size):
        try:
            msb = int(eeprom_data[offset], 16)
            lsb = int(eeprom_data[offset + 1], 16)
            result = (msb << 8) | (lsb & 0xff)

            result = float(result * 0.0001)
            retval = self.power_in_dbm_str(result)

        except Exception as err:
            retval = str(err)

        return retval

    dom_channel_status = {
            'Status':
                {'offset': 0,
                 'bit': 3,
                 'type': 'bitvalue'}}

    dom_channel_monitor_params = {
        'TX8Bias':
            {'offset': 30,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX7Bias':
            {'offset': 28,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX6Bias':
            {'offset': 26,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX5Bias':
            {'offset': 24,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX4Bias':
            {'offset': 22,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX3Bias':
            {'offset': 20,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX2Bias':
            {'offset': 18,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX1Bias':
            {'offset': 16,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'RX8Power':
            {'offset': 46,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX7Power':
            {'offset': 44,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX6Power':
            {'offset': 42,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX5Power':
            {'offset': 40,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX4Power':
            {'offset': 38,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX3Power':
            {'offset': 36,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX2Power':
            {'offset': 34,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX1Power':
            {'offset': 32,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'TX8Power':
            {'offset': 14,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX7Power':
            {'offset': 12,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX6Power':
            {'offset': 10,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX5Power':
            {'offset': 8,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX4Power':
            {'offset': 6,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX3Power':
            {'offset': 4,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX2Power':
            {'offset': 2,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX1Power':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}}
    }

    dom_tx_bias = {
        'TX8Bias':
            {'offset': 14,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX7Bias':
            {'offset': 12,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX6Bias':
            {'offset': 10,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX5Bias':
            {'offset': 8,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX4Bias':
            {'offset': 6,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX3Bias':
            {'offset': 4,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX2Bias':
            {'offset': 2,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}},
        'TX1Bias':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_bias}}
    }

    dom_rx_power = {
        'RX8Power':
            {'offset': 14,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX7Power':
            {'offset': 12,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX6Power':
            {'offset': 10,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX5Power':
            {'offset': 8,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX4Power':
            {'offset': 6,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX3Power':
            {'offset': 4,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX2Power':
            {'offset': 2,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}},
        'RX1Power':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_rx_power}}
    }

    dom_tx_power = {
        'TX8Power':
            {'offset': 14,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX7Power':
            {'offset': 12,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX6Power':
            {'offset': 10,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX5Power':
            {'offset': 8,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX4Power':
            {'offset': 6,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX3Power':
            {'offset': 4,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX2Power':
            {'offset': 2,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}},
        'TX1Power':
            {'offset': 0,
             'size': 2,
             'type': 'func',
             'decode': {'func': calc_tx_power}}
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
             {'offset':8,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_voltage}},
        'VccLowAlarm':
             {'offset':10,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_voltage}},
        'VccHighWarning':
             {'offset':12,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_voltage}},
        'VccLowWarning':
             {'offset':14,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_voltage}},
        'RxPowerHighAlarm':
             {'offset':64,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'RxPowerLowAlarm':
             {'offset':66,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'RxPowerHighWarning':
             {'offset':68,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'RxPowerLowWarning':
             {'offset':70,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_rx_power}},
        'TxBiasHighAlarm':
             {'offset':56,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_bias}},
        'TxBiasLowAlarm':
             {'offset':58,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_bias}},
        'TxBiasHighWarning':
             {'offset':60,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_bias}},
        'TxBiasLowWarning':
             {'offset':62,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_bias}},
        'TxPowerHighAlarm':
             {'offset':48,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_tx_power}},
        'TxPowerLowAlarm':
             {'offset':50,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_tx_power}},
        'TxPowerHighWarning':
             {'offset':52,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_tx_power}},
        'TxPowerLowWarning':
             {'offset':54,
              'size':2,
              'type': 'func',
              'decode': { 'func':calc_tx_power}}
              }

    def parse_temperature(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_temperature, eeprom_raw_data,
                    start_pos)

    def parse_voltage(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_voltage, eeprom_raw_data,
                    start_pos)

    def parse_channel_monitor_params(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_channel_monitor_params, eeprom_raw_data,
                    start_pos)
    
    def parse_dom_tx_bias(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_tx_bias, eeprom_raw_data,
                    start_pos)

    def parse_dom_rx_power(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_rx_power, eeprom_raw_data,
                    start_pos)

    def parse_dom_tx_power(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_tx_power, eeprom_raw_data,
                    start_pos)

    def parse_module_threshold_values(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_module_threshold_values, eeprom_raw_data,
                    start_pos)

    def parse_dom_channel_status(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_channel_status, eeprom_raw_data,
                start_pos)

    def parse_dom_tx_fault(self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_tx_fault, eeprom_raw_data,
                start_pos)

    def parse_dom_tx_disable (self, eeprom_raw_data, start_pos):
        return sffbase.parse(self, self.dom_tx_disable, eeprom_raw_data,
                start_pos)

