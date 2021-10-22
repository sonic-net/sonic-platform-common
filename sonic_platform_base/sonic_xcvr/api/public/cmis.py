"""
    cmis.py

    Implementation of XcvrApi that corresponds to CMIS
"""
import logging
from ...fields import consts
from ..xcvr_api import XcvrApi
from .cmisCDB import CmisCdbApi
from .cmisVDM import CmisVdmApi
import time

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

BYTELENGTH = 8
class CmisApi(XcvrApi):
    NUM_CHANNELS = 8

    def __init__(self, xcvr_eeprom):
        super(CmisApi, self).__init__(xcvr_eeprom)

    # Transceiver Information
    def get_model(self):
        '''
        This function returns the part number of the module
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_PART_NO_FIELD)

    def get_vendor_rev(self):
        '''
        This function returns the revision level for part number provided by vendor 
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_REV_FIELD)

    def get_vendor_serial(self):
        '''
        This function returns the serial number of the module
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_SERIAL_NO_FIELD)

    def get_vendor_name(self):
        '''
        This function returns the vendor name of the module
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_NAME_FIELD)

    def get_module_type(self):
        '''
        This function returns the SFF8024Identifier (module type / form-factor). Table 4-1 in SFF-8024 Rev4.6
        '''
        return self.xcvr_eeprom.read(consts.ID_FIELD)

    def get_vendor_OUI(self):
        '''
        This function returns the vendor IEEE company ID
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_OUI_FIELD)

    def get_vendor_date(self):
        '''
        This function returns the module manufacture date. It returns YYMMDDXX. XX is the lot code.
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_DATE_FIELD)

    def get_connector_type(self):
        '''
        This function returns module connector. Table 4-3 in SFF-8024 Rev4.6
        '''
        return self.xcvr_eeprom.read(consts.CONNECTOR_FIELD)

    def get_module_media_type(self):
        '''
        This function returns module media type: MMF, SMF, Passive Copper Cable, Active Cable Assembly or Base-T.
        '''
        return self.xcvr_eeprom.read(consts.MODULE_MEDIA_TYPE)

    def get_host_electrical_interface(self):
        '''
        This function returns module host electrical interface. Table 4-5 in SFF-8024 Rev4.6
        '''
        return self.xcvr_eeprom.read(consts.HOST_ELECTRICAL_INTERFACE)

    def get_module_media_interface(self):
        '''
        This function returns module media electrical interface. Table 4-6 ~ 4-10 in SFF-8024 Rev4.6
        '''       
        media_type = self.get_module_media_type()
        if media_type == 'Multimode Fiber (MMF)':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_850NM)
        elif media_type == 'Single Mode Fiber (SMF)':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_SM)
        elif media_type == 'Passive Copper Cable':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_PASSIVE_COPPER)
        elif media_type == 'Active Cable Assembly':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_ACTIVE_CABLE)
        elif media_type == 'BASE-T':
            return self.xcvr_eeprom.read(consts.MODULE_MEDIA_INTERFACE_BASE_T)
        else: 
            return 'Unknown media interface'
    
    def get_host_lane_count(self):
        '''
        This function returns number of host lanes
        '''
        lane_count = self.xcvr_eeprom.read(consts.LANE_COUNT)
        return (lane_count >> 4) & 0xf

    def get_media_lane_count(self):
        '''
        This function returns number of media lanes
        '''        
        lane_count = self.xcvr_eeprom.read(consts.LANE_COUNT)
        return (lane_count) & 0xf

    def get_host_lane_assignment_option(self):
        '''
        This function returns the host lane that the application begins on
        '''
        return self.xcvr_eeprom.read(consts.HOST_LANE_ASSIGNMENT_OPTION)

    def get_media_lane_assignment_option(self):
        '''
        This function returns the media lane that the application is allowed to begin on
        '''
        return self.xcvr_eeprom.read(consts.MEDIA_LANE_ASSIGNMENT_OPTION)

    def get_active_apsel_hostlane(self):
        '''
        This function returns the application select code that each host lane has
        '''
        apsel_dict = dict()
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_1)
        apsel_dict['hostlane1'] = (result >> 4) & 0xf
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_2)
        apsel_dict['hostlane2'] = (result >> 4) & 0xf
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_3)
        apsel_dict['hostlane3'] = (result >> 4) & 0xf
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_4)
        apsel_dict['hostlane4'] = (result >> 4) & 0xf
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_5)
        apsel_dict['hostlane5'] = (result >> 4) & 0xf
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_6)
        apsel_dict['hostlane6'] = (result >> 4) & 0xf
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_7)
        apsel_dict['hostlane7'] = (result >> 4) & 0xf
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_8)
        apsel_dict['hostlane8'] = (result >> 4) & 0xf
        return apsel_dict

    def get_media_interface_technology(self):
        '''
        This function returns the media lane technology
        '''
        return self.xcvr_eeprom.read(consts.MEDIA_INTERFACE_TECH)

    def get_module_hardware_revision(self):
        '''
        This function returns the module hardware revision
        '''
        hw_major_rev = self.xcvr_eeprom.read(consts.HW_MAJOR_REV)
        hw_minor_rev = self.xcvr_eeprom.read(consts.HW_MAJOR_REV)
        hw_rev = [str(num) for num in [hw_major_rev, hw_minor_rev]]
        return '.'.join(hw_rev)
    
    def get_cmis_rev(self):
        '''
        This function returns the CMIS version the module complies to
        '''
        cmis = self.xcvr_eeprom.read(consts.CMIS_REVISION)
        cmis_major = (cmis >> 4) & 0xf
        cmis_minor = (cmis) & 0xf
        cmis_rev = [str(num) for num in [cmis_major, cmis_minor]]
        return '.'.join(cmis_rev)
    
    def get_module_active_firmware(self):
        '''
        This function returns the active firmware version
        '''
        active_fw_major = self.xcvr_eeprom.read(consts.ACTIVE_FW_MAJOR_REV)
        active_fw_minor = self.xcvr_eeprom.read(consts.ACTIVE_FW_MINOR_REV)
        active_fw = [str(num) for num in [active_fw_major, active_fw_minor]]
        return '.'.join(active_fw)

    def get_module_inactive_firmware(self):
        '''
        This function returns the inactive firmware version
        '''
        inactive_fw_major = self.xcvr_eeprom.read(consts.INACTIVE_FW_MAJOR_REV)
        inactive_fw_minor = self.xcvr_eeprom.read(consts.INACTIVE_FW_MINOR_REV)
        inactive_fw = [str(num) for num in [inactive_fw_major, inactive_fw_minor]]
        return '.'.join(inactive_fw)

    # Transceiver DOM
    def get_module_temperature(self):
        '''
        This function returns the module case temperature and its thresholds. Unit in deg C
        '''
        case_temp = self.xcvr_eeprom.read(consts.CASE_TEMP)
        case_temp_high_alarm = self.xcvr_eeprom.read(consts.CASE_TEMP_HIGH_ALARM)
        case_temp_low_alarm = self.xcvr_eeprom.read(consts.CASE_TEMP_LOW_ALARM)
        case_temp_high_warn = self.xcvr_eeprom.read(consts.CASE_TEMP_HIGH_WARN)
        case_temp_low_warn = self.xcvr_eeprom.read(consts.CASE_TEMP_LOW_WARN)
        case_temp_dict = {'monitor value': case_temp,
                          'high alarm': case_temp_high_alarm,
                          'low alarm': case_temp_low_alarm,
                          'high warn': case_temp_high_warn,
                          'low warn': case_temp_low_warn}
        return case_temp_dict
    
    def get_module_voltage(self):
        '''
        This function returns the monitored value of the 3.3-V supply voltage and its thresholds.
        Unit in V
        '''
        voltage = self.xcvr_eeprom.read(consts.VOLTAGE)
        voltage_high_alarm = self.xcvr_eeprom.read(consts.VOLTAGE_HIGH_ALARM)
        voltage_low_alarm = self.xcvr_eeprom.read(consts.VOLTAGE_LOW_ALARM)
        voltage_high_warn = self.xcvr_eeprom.read(consts.VOLTAGE_HIGH_WARN)
        voltage_low_warn = self.xcvr_eeprom.read(consts.VOLTAGE_LOW_WARN)
        voltage_dict = {'monitor value': voltage,
                        'high alarm': voltage_high_alarm,
                        'low alarm': voltage_low_alarm,
                        'high warn': voltage_high_warn,
                        'low warn': voltage_low_warn}
        return voltage_dict

    def get_txpower(self):
        '''
        This function returns the TX output power. Unit in mW
        '''
        tx_power = self.xcvr_eeprom.read(consts.TX_POW)
        tx_power_high_alarm = self.xcvr_eeprom.read(consts.TX_POWER_HIGH_ALARM)
        tx_power_low_alarm = self.xcvr_eeprom.read(consts.TX_POWER_LOW_ALARM)
        tx_power_high_warn = self.xcvr_eeprom.read(consts.TX_POWER_HIGH_WARN)
        tx_power_low_warn = self.xcvr_eeprom.read(consts.TX_POWER_LOW_WARN)
        tx_power_dict = {'monitor value lane1': tx_power,
                        'high alarm': tx_power_high_alarm,
                        'low alarm': tx_power_low_alarm,
                        'high warn': tx_power_high_warn,
                        'low warn': tx_power_low_warn}        
        return tx_power_dict

    def get_rxpower(self):
        '''
        This function returns the RX input power. Unit in mW
        '''
        rx_power = self.xcvr_eeprom.read(consts.RX_POW)
        rx_power_high_alarm = self.xcvr_eeprom.read(consts.RX_POWER_HIGH_ALARM)
        rx_power_low_alarm = self.xcvr_eeprom.read(consts.RX_POWER_LOW_ALARM)
        rx_power_high_warn = self.xcvr_eeprom.read(consts.RX_POWER_HIGH_WARN)
        rx_power_low_warn = self.xcvr_eeprom.read(consts.RX_POWER_LOW_WARN)
        rx_power_dict = {'monitor value lane1': rx_power,
                        'high alarm': rx_power_high_alarm,
                        'low alarm': rx_power_low_alarm,
                        'high warn': rx_power_high_warn,
                        'low warn': rx_power_low_warn}      
        return rx_power_dict

    def get_txbias(self):
        '''
        This function returns the TX laser bias current. Unit in mA
        '''
        tx_bias_current = self.xcvr_eeprom.read(consts.TX_BIAS)
        tx_bias_current_high_alarm = self.xcvr_eeprom.read(consts.TX_BIAS_CURR_HIGH_ALARM)
        tx_bias_current_low_alarm = self.xcvr_eeprom.read(consts.TX_BIAS_CURR_LOW_ALARM)
        tx_bias_current_high_warn = self.xcvr_eeprom.read(consts.TX_BIAS_CURR_HIGH_WARN)
        tx_bias_current_low_warn = self.xcvr_eeprom.read(consts.TX_BIAS_CURR_LOW_WARN)
        tx_bias_current_dict = {'monitor value lane1': tx_bias_current,
                        'high alarm': tx_bias_current_high_alarm,
                        'low alarm': tx_bias_current_low_alarm,
                        'high warn': tx_bias_current_high_warn,
                        'low warn': tx_bias_current_low_warn} 
        return tx_bias_current_dict

    def get_tx_config_power(self):
        '''
        This function returns the configured TX output power. Unit in dBm
        '''
        return self.xcvr_eeprom.read(consts.TX_CONFIG_POWER)

    def get_media_output_loopback(self):
        '''
        This function returns the media output loopback status
        '''
        result = self.xcvr_eeprom.read(consts.MEDIA_OUTPUT_LOOPBACK)
        return result == 1

    def get_media_input_loopback(self):
        '''
        This function returns the media input loopback status
        '''
        result = self.xcvr_eeprom.read(consts.MEDIA_INPUT_LOOPBACK)
        return result == 1

    def get_host_output_loopback(self):
        '''
        This function returns the host output loopback status
        '''
        result = self.xcvr_eeprom.read(consts.HOST_OUTPUT_LOOPBACK)
        loopback_status = []
        for bitpos in range(BYTELENGTH):
            loopback_status.append(bool((result >> bitpos) & 0x1))
        return loopback_status

    def get_host_input_loopback(self):
        '''
        This function returns the host input loopback status
        '''
        result = self.xcvr_eeprom.read(consts.HOST_INPUT_LOOPBACK)        
        loopback_status = []
        for bitpos in range(BYTELENGTH):
            loopback_status.append(bool((result >> bitpos) & 0x1))
        return loopback_status

    def get_aux_mon_type(self):
        '''
        This function returns the aux monitor types
        '''
        result = self.xcvr_eeprom.read(consts.AUX_MON_TYPE)    
        aux1_mon_type = result & 0x1
        aux2_mon_type = (result >> 1) & 0x1
        aux3_mon_type = (result >> 2) & 0x1
        return aux1_mon_type, aux2_mon_type, aux3_mon_type

    def get_laser_temperature(self):
        '''
        This function returns the laser temperature monitor value
        '''
        aux1_mon_type, aux2_mon_type, aux3_mon_type = self.get_aux_mon_type()
        LASER_TEMP_SCALE = 256.0
        if aux2_mon_type == 0:
            laser_temp = self.xcvr_eeprom.read(consts.AUX2_MON)/LASER_TEMP_SCALE
            laser_temp_high_alarm = self.xcvr_eeprom.read(consts.AUX2_HIGH_ALARM)/LASER_TEMP_SCALE
            laser_temp_low_alarm = self.xcvr_eeprom.read(consts.AUX2_LOW_ALARM)/LASER_TEMP_SCALE
            laser_temp_high_warn = self.xcvr_eeprom.read(consts.AUX2_HIGH_WARN)/LASER_TEMP_SCALE
            laser_temp_low_warn = self.xcvr_eeprom.read(consts.AUX2_LOW_WARN)/LASER_TEMP_SCALE
        elif aux2_mon_type == 1 and aux3_mon_type == 0:
            laser_temp = self.xcvr_eeprom.read(consts.AUX3_MON)/LASER_TEMP_SCALE
            laser_temp_high_alarm = self.xcvr_eeprom.read(consts.AUX3_HIGH_ALARM)/LASER_TEMP_SCALE
            laser_temp_low_alarm = self.xcvr_eeprom.read(consts.AUX3_LOW_ALARM)/LASER_TEMP_SCALE
            laser_temp_high_warn = self.xcvr_eeprom.read(consts.AUX3_HIGH_WARN)/LASER_TEMP_SCALE
            laser_temp_low_warn = self.xcvr_eeprom.read(consts.AUX3_LOW_WARN)/LASER_TEMP_SCALE
        else:
            return None
        laser_temp_dict = {'monitor value': laser_temp,
                           'high alarm': laser_temp_high_alarm,
                           'low alarm': laser_temp_low_alarm,
                           'high warn': laser_temp_high_warn,
                           'low warn': laser_temp_low_warn}  
        return laser_temp_dict
    
    def get_laser_TEC_current(self):
        '''
        This function returns the laser TEC current monitor value
        '''
        aux1_mon_type, aux2_mon_type, aux3_mon_type = self.get_aux_mon_type()
        LASER_TEC_CURRENT_SCALE = 32767.0
        if aux1_mon_type == 1:
            laser_tec_current = self.xcvr_eeprom.read(consts.AUX1_MON)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_high_alarm = self.xcvr_eeprom.read(consts.AUX1_HIGH_ALARM)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_low_alarm = self.xcvr_eeprom.read(consts.AUX1_LOW_ALARM)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_high_warn = self.xcvr_eeprom.read(consts.AUX1_HIGH_WARN)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_low_warn = self.xcvr_eeprom.read(consts.AUX1_LOW_WARN)/LASER_TEC_CURRENT_SCALE
        elif aux1_mon_type == 0 and aux2_mon_type == 1:
            laser_tec_current = self.xcvr_eeprom.read(consts.AUX2_MON)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_high_alarm = self.xcvr_eeprom.read(consts.AUX2_HIGH_ALARM)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_low_alarm = self.xcvr_eeprom.read(consts.AUX2_LOW_ALARM)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_high_warn = self.xcvr_eeprom.read(consts.AUX2_HIGH_WARN)/LASER_TEC_CURRENT_SCALE
            laser_tec_current_low_warn = self.xcvr_eeprom.read(consts.AUX2_LOW_WARN)/LASER_TEC_CURRENT_SCALE
        else:
            return None
        laser_tec_current_dict = {'monitor value': laser_tec_current,
                                  'high alarm': laser_tec_current_high_alarm,
                                  'low alarm': laser_tec_current_low_alarm,
                                  'high warn': laser_tec_current_high_warn,
                                  'low warn': laser_tec_current_low_warn}              
        return laser_tec_current_dict

    def get_custom_field(self, signed = False, scale = 1.0):
        '''
        This function returns the custom monitor field
        '''
        result = self.xcvr_eeprom.read(consts.CUSTOM_MON)
        if signed:
            result -= 2**15
        result /= scale
        return result


    def get_vdm_api(self):
        self.vdm = CmisVdmApi(self.xcvr_eeprom)
        return self.vdm

    def get_vdm(self):
        '''
        This function returns all the VDM items, including real time monitor value, threholds and flags
        '''
        try: 
            self.vdm
        except AttributeError:
            self.get_vdm_api()
        vdm = self.vdm.get_vdm_allpage()
        return vdm

    # Transceiver status
    def get_module_state(self):
        '''
        This function returns the module state
        '''
        result = self.xcvr_eeprom.read(consts.MODULE_STATE) >> 1
        DICT = self.xcvr_eeprom.mem_map.codes.MODULE_STATE
        return DICT.get(result, "Unknown")

    def get_module_fault_cause(self):
        '''
        This function returns the module fault cause
        '''
        return self.xcvr_eeprom.read(consts.MODULE_FAULT_CAUSE)

    def get_module_firmware_fault_state_changed(self):
        '''
        This function returns datapath firmware fault state, module firmware fault state 
        and whether module state changed
        '''
        result = self.xcvr_eeprom.read(consts.MODULE_FIRMWARE_FAULT_INFO)
        datapath_firmware_fault = bool((result >> 2) & 0x1)
        module_firmware_fault = bool((result >> 1) & 0x1)
        module_state_changed = bool(result & 0x1)
        return datapath_firmware_fault, module_firmware_fault, module_state_changed

    def get_module_level_flag(self):
        '''
        This function returns teh module level flags, including
        - 3.3 V voltage supply flags
        - Case temperature flags
        - Aux 1 flags
        - Aux 2 flags
        - Aux 3 flags
        - Custom field flags
        '''
        module_flag_byte1 = self.xcvr_eeprom.read(consts.MODULE_FLAG_BYTE1)
        module_flag_byte2 = self.xcvr_eeprom.read(consts.MODULE_FLAG_BYTE2)
        module_flag_byte3 = self.xcvr_eeprom.read(consts.MODULE_FLAG_BYTE3)

        voltage_high_alarm_flag = bool((module_flag_byte1 >> 4) & 0x1)
        voltage_low_alarm_flag = bool((module_flag_byte1 >> 5) & 0x1)
        voltage_high_warn_flag = bool((module_flag_byte1 >> 6) & 0x1)
        voltage_low_warn_flag = bool((module_flag_byte1 >> 7) & 0x1)
        voltage_flags = {'voltage_high_alarm_flag': voltage_high_alarm_flag,
                         'voltage_low_alarm_flag': voltage_low_alarm_flag,
                         'voltage_high_warn_flag': voltage_high_warn_flag,
                         'voltage_low_warn_flag': voltage_low_warn_flag}

        case_temp_high_alarm_flag = bool((module_flag_byte1 >> 0) & 0x1)
        case_temp_low_alarm_flag = bool((module_flag_byte1 >> 1) & 0x1)
        case_temp_high_warn_flag = bool((module_flag_byte1 >> 2) & 0x1)
        case_temp_low_warn_flag = bool((module_flag_byte1 >> 3) & 0x1)
        case_temp_flags = {'case_temp_high_alarm_flag': case_temp_high_alarm_flag,
                           'case_temp_low_alarm_flag': case_temp_low_alarm_flag,
                           'case_temp_high_warn_flag': case_temp_high_warn_flag,
                           'case_temp_low_warn_flag': case_temp_low_warn_flag}

        aux2_high_alarm_flag = bool((module_flag_byte2 >> 4) & 0x1)
        aux2_low_alarm_flag = bool((module_flag_byte2 >> 5) & 0x1)
        aux2_high_warn_flag = bool((module_flag_byte2 >> 6) & 0x1)
        aux2_low_warn_flag = bool((module_flag_byte2 >> 7) & 0x1)
        aux2_flags = {'aux2_high_alarm_flag': aux2_high_alarm_flag,
                      'aux2_low_alarm_flag': aux2_low_alarm_flag,
                      'aux2_high_warn_flag': aux2_high_warn_flag,
                      'aux2_low_warn_flag': aux2_low_warn_flag}

        aux1_high_alarm_flag = bool((module_flag_byte2 >> 0) & 0x1)
        aux1_low_alarm_flag = bool((module_flag_byte2 >> 1) & 0x1)
        aux1_high_warn_flag = bool((module_flag_byte2 >> 2) & 0x1)
        aux1_low_warn_flag = bool((module_flag_byte2 >> 3) & 0x1)
        aux1_flags = {'aux1_high_alarm_flag': aux1_high_alarm_flag,
                      'aux1_low_alarm_flag': aux1_low_alarm_flag,
                      'aux1_high_warn_flag': aux1_high_warn_flag,
                      'aux1_low_warn_flag': aux1_low_warn_flag}

        custom_mon_high_alarm_flag = bool((module_flag_byte3 >> 4) & 0x1)
        custom_mon_low_alarm_flag = bool((module_flag_byte3 >> 5) & 0x1)
        custom_mon_high_warn_flag = bool((module_flag_byte3 >> 6) & 0x1)
        custom_mon_low_warn_flag = bool((module_flag_byte3 >> 7) & 0x1)
        custom_mon_flags = {'custom_mon_high_alarm_flag': custom_mon_high_alarm_flag,
                            'custom_mon_low_alarm_flag': custom_mon_low_alarm_flag,
                            'custom_mon_high_warn_flag': custom_mon_high_warn_flag,
                            'custom_mon_low_warn_flag': custom_mon_low_warn_flag}

        aux3_high_alarm_flag = bool((module_flag_byte3 >> 0) & 0x1)
        aux3_low_alarm_flag = bool((module_flag_byte3 >> 1) & 0x1)
        aux3_high_warn_flag = bool((module_flag_byte3 >> 2) & 0x1)
        aux3_low_warn_flag = bool((module_flag_byte3 >> 3) & 0x1)
        aux3_flags = {'aux3_high_alarm_flag': aux3_high_alarm_flag,
                      'aux3_low_alarm_flag': aux3_low_alarm_flag,
                      'aux3_high_warn_flag': aux3_high_warn_flag,
                      'aux3_low_warn_flag': aux3_low_warn_flag}

        module_flag = {'voltage_flags': voltage_flags,
                       'case_temp_flags': case_temp_flags,
                       'aux1_flags': aux1_flags,
                       'aux2_flags': aux2_flags,
                       'aux3_flags': aux3_flags,
                       'custom_mon_flags': custom_mon_flags}
        return module_flag

    def get_datapath_state(self):
        '''
        This function returns the eight datapath states
        '''
        result = self.xcvr_eeprom.read(consts.DATAPATH_STATE)
        dp_lane7 = (result >> 0) & 0xf
        dp_lane8 = (result >> 4) & 0xf
        dp_lane5 = (result >> 8) & 0xf
        dp_lane6 = (result >> 12) & 0xf
        dp_lane3 = (result >> 16) & 0xf
        dp_lane4 = (result >> 20) & 0xf
        dp_lane1 = (result >> 24) & 0xf
        dp_lane2 = (result >> 28) & 0xf
        DICT = self.xcvr_eeprom.mem_map.codes.DATAPATH_STATE
        dp_state_dict = {'dp_lane1': DICT.get(dp_lane1, "Unknown"),
                         'dp_lane2': DICT.get(dp_lane2, "Unknown"),
                         'dp_lane3': DICT.get(dp_lane3, "Unknown"),
                         'dp_lane4': DICT.get(dp_lane4, "Unknown"),
                         'dp_lane5': DICT.get(dp_lane5, "Unknown"),
                         'dp_lane6': DICT.get(dp_lane6, "Unknown"),
                         'dp_lane7': DICT.get(dp_lane7, "Unknown"),
                         'dp_lane8': DICT.get(dp_lane8, "Unknown")
                        }
        return dp_state_dict

    def get_tx_output_status(self):
        '''
        This function returns whether TX output signals are valid on TX media lane
        '''
        result = self.xcvr_eeprom.read(consts.TX_OUTPUT_STATUS)
        tx_output_status_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_output_status_dict['TX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return tx_output_status_dict

    def get_rx_output_status(self):
        '''
        This function returns whether RX output signals are valid on RX host lane
        '''
        result = self.xcvr_eeprom.read(consts.RX_OUTPUT_STATUS)
        rx_output_status_dict = dict()
        for bitpos in range(BYTELENGTH):
            rx_output_status_dict['RX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return rx_output_status_dict

    def get_tx_fault(self):
        '''
        This function returns TX failure flag on TX media lane
        '''
        result = self.xcvr_eeprom.read(consts.TX_FAULT_FLAG)
        tx_fault_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_fault_dict['TX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return tx_fault_dict

    def get_tx_los(self):
        '''
        This function returns TX LOS flag on TX host lane
        '''
        result = self.xcvr_eeprom.read(consts.TX_LOS_FLAG)
        tx_los_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_los_dict['TX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return tx_los_dict

    def get_tx_cdr_lol(self):
        '''
        This function returns TX CDR LOL flag on TX host lane
        '''
        result = self.xcvr_eeprom.read(consts.TX_CDR_LOL)
        tx_lol_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_lol_dict['TX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return tx_lol_dict

    def get_tx_power_flag(self):
        '''
        This function returns TX power out of range flag on TX media lane
        '''
        tx_power_high_alarm = self.xcvr_eeprom.read(consts.TX_POWER_HIGH_ALARM_FLAG)
        tx_power_low_alarm = self.xcvr_eeprom.read(consts.TX_POWER_LOW_ALARM_FLAG)
        tx_power_high_warn = self.xcvr_eeprom.read(consts.TX_POWER_HIGH_WARN_FLAG)
        tx_power_low_warn = self.xcvr_eeprom.read(consts.TX_POWER_LOW_WARN_FLAG)
        tx_power_high_alarm_dict = dict()
        tx_power_low_alarm_dict = dict()
        tx_power_high_warn_dict = dict()
        tx_power_low_warn_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_power_high_alarm_dict['TX_lane%d' %(bitpos+1)] = bool((tx_power_high_alarm >> bitpos) & 0x1)
            tx_power_low_alarm_dict['TX_lane%d' %(bitpos+1)] = bool((tx_power_low_alarm >> bitpos) & 0x1)
            tx_power_high_warn_dict['TX_lane%d' %(bitpos+1)] = bool((tx_power_high_warn >> bitpos) & 0x1)
            tx_power_low_warn_dict['TX_lane%d' %(bitpos+1)] = bool((tx_power_low_warn >> bitpos) & 0x1)

        tx_power_flag_dict = {'tx_power_high_alarm': tx_power_high_alarm_dict,
                              'tx_power_low_alarm': tx_power_low_alarm_dict,
                              'tx_power_high_warn': tx_power_high_warn_dict,
                              'tx_power_low_warn': tx_power_low_warn_dict,}
        return tx_power_flag_dict

    def get_tx_bias_flag(self):
        '''
        This function returns TX bias out of range flag on TX media lane
        '''
        tx_bias_high_alarm = self.xcvr_eeprom.read(consts.TX_BIAS_HIGH_ALARM_FLAG)
        tx_bias_low_alarm = self.xcvr_eeprom.read(consts.TX_BIAS_LOW_ALARM_FLAG)
        tx_bias_high_warn = self.xcvr_eeprom.read(consts.TX_BIAS_HIGH_WARN_FLAG)
        tx_bias_low_warn = self.xcvr_eeprom.read(consts.TX_BIAS_LOW_WARN_FLAG)
        tx_bias_high_alarm_dict = dict()
        tx_bias_low_alarm_dict = dict()
        tx_bias_high_warn_dict = dict()
        tx_bias_low_warn_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_bias_high_alarm_dict['TX_lane%d' %(bitpos+1)] = bool((tx_bias_high_alarm >> bitpos) & 0x1)
            tx_bias_low_alarm_dict['TX_lane%d' %(bitpos+1)] = bool((tx_bias_low_alarm >> bitpos) & 0x1)
            tx_bias_high_warn_dict['TX_lane%d' %(bitpos+1)] = bool((tx_bias_high_warn >> bitpos) & 0x1)
            tx_bias_low_warn_dict['TX_lane%d' %(bitpos+1)] = bool((tx_bias_low_warn >> bitpos) & 0x1)

        tx_bias_flag_dict = {'tx_bias_high_alarm': tx_bias_high_alarm_dict,
                              'tx_bias_low_alarm': tx_bias_low_alarm_dict,
                              'tx_bias_high_warn': tx_bias_high_warn_dict,
                              'tx_bias_low_warn': tx_bias_low_warn_dict,}
        return tx_bias_flag_dict

    def get_rx_power_flag(self):
        '''
        This function returns RX power out of range flag on RX media lane
        '''
        rx_power_high_alarm = self.xcvr_eeprom.read(consts.RX_POWER_HIGH_ALARM_FLAG)
        rx_power_low_alarm = self.xcvr_eeprom.read(consts.RX_POWER_LOW_ALARM_FLAG)
        rx_power_high_warn = self.xcvr_eeprom.read(consts.RX_POWER_HIGH_WARN_FLAG)
        rx_power_low_warn = self.xcvr_eeprom.read(consts.RX_POWER_LOW_WARN_FLAG)
        rx_power_high_alarm_dict = dict()
        rx_power_low_alarm_dict = dict()
        rx_power_high_warn_dict = dict()
        rx_power_low_warn_dict = dict()
        for bitpos in range(BYTELENGTH):
            rx_power_high_alarm_dict['RX_lane%d' %(bitpos+1)] = bool((rx_power_high_alarm >> bitpos) & 0x1)
            rx_power_low_alarm_dict['RX_lane%d' %(bitpos+1)] = bool((rx_power_low_alarm >> bitpos) & 0x1)
            rx_power_high_warn_dict['RX_lane%d' %(bitpos+1)] = bool((rx_power_high_warn >> bitpos) & 0x1)
            rx_power_low_warn_dict['RX_lane%d' %(bitpos+1)] = bool((rx_power_low_warn >> bitpos) & 0x1)

        rx_power_flag_dict = {'rx_power_high_alarm': rx_power_high_alarm_dict,
                              'rx_power_low_alarm': rx_power_low_alarm_dict,
                              'rx_power_high_warn': rx_power_high_warn_dict,
                              'rx_power_low_warn': rx_power_low_warn_dict,}
        return rx_power_flag_dict

    def get_rx_los(self):
        '''
        This function returns RX LOS flag on RX media lane
        '''
        result = self.xcvr_eeprom.read(consts.RX_LOS_FLAG)
        rx_los_dict = dict()
        for bitpos in range(BYTELENGTH):
            rx_los_dict['RX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return rx_los_dict        

    def get_rx_cdr_lol(self):
        '''
        This function returns RX CDR LOL flag on RX media lane
        '''
        result = self.xcvr_eeprom.read(consts.RX_CDR_LOL)
        rx_lol_dict = dict()
        for bitpos in range(BYTELENGTH):
            rx_lol_dict['RX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return rx_lol_dict

    def get_config_datapath_hostlane_status(self):
        '''
        This function returns configuration command execution 
        / result status for the datapath of each host lane
        '''       
        result = self.xcvr_eeprom.read(consts.CONFIG_LANE_STATUS)
        config_status_lane7 = (result >> 0) & 0xf
        config_status_lane8 = (result >> 4) & 0xf
        config_status_lane5 = (result >> 8) & 0xf
        config_status_lane6 = (result >> 12) & 0xf
        config_status_lane3 = (result >> 16) & 0xf
        config_status_lane4 = (result >> 20) & 0xf
        config_status_lane1 = (result >> 24) & 0xf
        config_status_lane2 = (result >> 28) & 0xf
        DICT = self.xcvr_eeprom.mem_map.codes.CONFIG_STATUS
        config_status_dict = {'config_DP_status_hostlane1': DICT.get(config_status_lane1, "Unknown"),
                              'config_DP_status_hostlane2': DICT.get(config_status_lane2, "Unknown"),
                              'config_DP_status_hostlane3': DICT.get(config_status_lane3, "Unknown"),
                              'config_DP_status_hostlane4': DICT.get(config_status_lane4, "Unknown"),
                              'config_DP_status_hostlane5': DICT.get(config_status_lane5, "Unknown"),
                              'config_DP_status_hostlane6': DICT.get(config_status_lane6, "Unknown"),
                              'config_DP_status_hostlane7': DICT.get(config_status_lane7, "Unknown"),
                              'config_DP_status_hostlane8': DICT.get(config_status_lane8, "Unknown")
                             }
        return config_status_dict

    def get_dpinit_pending(self):
        '''
        This function returns datapath init pending status.
        0 means datapath init not pending.
        1 means datapath init pending. DPInit not yet executed after successful ApplyDPInit.
        Hence the active control set content may deviate from the actual hardware config
        '''
        result = self.xcvr_eeprom.read(consts.DPINIT_PENDING)
        dpinit_pending_dict = dict()
        for bitpos in range(BYTELENGTH):
            dpinit_pending_dict['hostlane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return dpinit_pending_dict

    def get_supported_power_config(self):
        '''
        This function returns the supported TX power range
        '''
        min_prog_tx_output_power = self.xcvr_eeprom.read(consts.MIN_PROG_OUTPUT_POWER)
        max_prog_tx_output_power = self.xcvr_eeprom.read(consts.MAX_PROG_OUTPUT_POWER)
        return min_prog_tx_output_power, max_prog_tx_output_power

    def reset_module(self, reset = False):
        '''
        This function resets the module
        '''
        if reset:
            reset_control = reset << 3
            self.xcvr_eeprom.write(consts.MODULE_LEVEL_CONTROL, reset_control)

    def set_low_power(self, AssertLowPower):
        '''
        This function sets the module to low power state. 
        AssertLowPower being 0 means "set to high power"
        AssertLowPower being 1 means "set to low power"
        '''
        low_power_control = AssertLowPower << 6
        self.xcvr_eeprom.write(consts.MODULE_LEVEL_CONTROL, low_power_control)
    
    def set_tx_power(self, tx_power):
        '''
        This function sets the TX output power. Unit in dBm
        '''
        min_prog_tx_output_power, max_prog_tx_output_power = self.get_supported_power_config()
        if tx_power > max_prog_tx_output_power or tx_power < min_prog_tx_output_power:
            raise ValueError('Provisioned TX power out of range. Max: %.1f; Min: %.1f dBm.' 
                             %(max_prog_tx_output_power, min_prog_tx_output_power))
        self.xcvr_eeprom.write(consts.TX_CONFIG_POWER, tx_power)
        time.sleep(1)

    def get_loopback_capability(self):
        '''
        This function returns the module loopback capability as advertised
        '''
        allowed_loopback_result = self.xcvr_eeprom.read(consts.LOOPBACK_CAPABILITY)
        loopback_capability = dict()
        loopback_capability['simultaneous_host_media_loopback_supported'] = bool((allowed_loopback_result >> 6) & 0x1)
        loopback_capability['per_lane_media_loopback_supported'] = bool((allowed_loopback_result >> 5) & 0x1)
        loopback_capability['per_lane_host_loopback_supported'] = bool((allowed_loopback_result >> 4) & 0x1)
        loopback_capability['host_side_input_loopback_supported'] = bool((allowed_loopback_result >> 3) & 0x1)
        loopback_capability['host_side_output_loopback_supported'] = bool((allowed_loopback_result >> 2) & 0x1)
        loopback_capability['media_side_input_loopback_supported'] = bool((allowed_loopback_result >> 1) & 0x1)
        loopback_capability['media_side_output_loopback_supported'] = bool((allowed_loopback_result >> 0) & 0x1)
        return loopback_capability

    def set_loopback_mode(self, loopback_mode):
        '''
        This function sets the module loopback mode.
        Loopback mode has to be one of the five:
        1. "none" (default)
        2. "host-side-input"
        3. "host-side-output"
        4. "media-side-input"
        5. "media-side-output"
        The function will look at 13h:128 to check advertized loopback capabilities.
        '''
        loopback_capability = self.get_loopback_capability()
        if loopback_mode == 'none':
            self.xcvr_eeprom.write(consts.HOST_INPUT_LOOPBACK, 0)
            self.xcvr_eeprom.write(consts.HOST_OUTPUT_LOOPBACK, 0)
            self.xcvr_eeprom.write(consts.MEDIA_INPUT_LOOPBACK, 0)
            self.xcvr_eeprom.write(consts.MEDIA_OUTPUT_LOOPBACK, 0)
        elif loopback_mode == 'host-side-input':
            assert loopback_capability['host_side_input_loopback_supported']
            self.xcvr_eeprom.write(consts.HOST_INPUT_LOOPBACK, 0xff)
        elif loopback_mode == 'host-side-output':
            assert loopback_capability['host_side_output_loopback_supported']
            self.xcvr_eeprom.write(consts.HOST_OUTPUT_LOOPBACK, 0xff)
        elif loopback_mode == 'media-side-input':
            assert loopback_capability['media_side_input_loopback_supported']
            self.xcvr_eeprom.write(consts.MEDIA_INPUT_LOOPBACK, 0xff)
        elif loopback_mode == 'media-side-output':
            assert loopback_capability['media_side_output_loopback_supported']
            self.xcvr_eeprom.write(consts.MEDIA_OUTPUT_LOOPBACK, 0xff)


    def get_cdb_api(self):
        self.cdb = CmisCdbApi(self.xcvr_eeprom)
        return self.cdb
    
    def get_module_fw_upgrade_feature(self, verbose = False):
        """
        This function obtains CDB features supported by the module from CDB command 0041h,
        such as start header size, maximum block size, whether extended payload messaging
        (page 0xA0 - 0xAF) or only local payload is supported. These features are important because
        the following upgrade with depend on these parameters.
        """
        try:
            self.cdb
        except AttributeError:
            self.get_cdb_api()
        # get fw upgrade features (CMD 0041h)
        starttime = time.time()
        autopaging_flag = bool((self.xcvr_eeprom.read(consts.CDB_SUPPORT) >> 4) & 0x1)
        writelength = (self.xcvr_eeprom.read(consts.CDB_SEQ_WRITE_LENGTH_EXT) + 1) * 8
        logger.info('Auto page support: %s' %autopaging_flag)
        logger.info('Max write length: %d' %writelength)
        rpllen, rpl_chkcode, rpl = self.cdb.cmd0041h()
        if self.cdb.cdb_chkcode(rpl) == rpl_chkcode:
            password_type = {
                0x00 : 'vendorPassword',
                0x01 : 'vendorPasswordSeq',
                0x80 : 'msaPassword'
            }
            self.cdb.password_type = password_type[rpl[0]]
            logger.info('Download password type: %s' %self.cdb.password_type)

            startLPLsize = rpl[2]
            logger.info('Start payload size %d' % startLPLsize)
            maxblocksize = (rpl[4] + 1) * 8
            logger.info('Max block size %d' % maxblocksize)
            lplEplSupport = {0x00 : 'No write to LPL/EPL supported',
                            0x01 : 'Write to LPL supported',
                            0x10 : 'Write to EPL supported',
                            0x11 : 'Write to LPL/EPL supported'}
            logger.info('{}'.format(lplEplSupport[rpl[5]]))
            if rpl[5] == 1:
                lplonly_flag = True
            else:
                lplonly_flag = False
            logger.info('Abort CMD102h supported %s' %bool(rpl[1] & 0x01))
            if verbose:
                logger.info('Copy CMD108h supported %s' %bool((rpl[1] >> 1) & 0x01))
                logger.info('Skipping erased blocks supported %s' %bool((rpl[1] >> 2) & 0x01))
                logger.info('Full image readback supported %s' %bool((rpl[1] >> 7) & 0x01))
                logger.info('Default erase byte {:#x}'.format(rpl[3]))
                logger.info('Read to LPL/EPL {:#x}'.format(rpl[6]))

        else:
            raise ValueError('Reply payload check code error')
        elapsedtime = time.time()-starttime
        logger.info('Get module FW upgrade features time: %.2f s' %elapsedtime)
        return startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength

    def get_module_fw_info(self):
        """
        This function returns firmware Image A and B version, running version, committed version
        and whether both firmware images are valid.
        Operational Status: 1 = running, 0 = not running
        Administrative Status: 1=committed, 0=uncommitted
        Validity Status: 1 = invalid, 0 = valid
        """
        try:
            self.cdb
        except AttributeError:
            self.get_cdb_api()
        # get fw info (CMD 0100h)
        starttime = time.time()
        logger.info('\nGet module FW info')
        rpllen, rpl_chkcode, rpl = self.cdb.cmd0100h()
        if self.cdb.cdb_chkcode(rpl) == rpl_chkcode:
            # Regiter 9Fh:136
            fwStatus = rpl[0]
            # Registers 9Fh:138,139; 140,141
            ImageA = '%d.%d.%d' %(rpl[2], rpl[3], ((rpl[4]<< 8) | rpl[5]))
            logger.info('Image A Version: %s' %ImageA)
            # Registers 9Fh:174,175; 176.177
            ImageB = '%d.%d.%d' %(rpl[38], rpl[39], ((rpl[40]<< 8) | rpl[41]))
            logger.info('Image B Version: %s' %ImageB)

            ImageARunning = (fwStatus & 0x01) # bit 0 - image A is running
            ImageACommitted = ((fwStatus >> 1) & 0x01) # bit 1 - image A is committed
            ImageAValid = ((fwStatus >> 2) & 0x01) # bit 2 - image A is valid
            ImageBRunning = ((fwStatus >> 4) & 0x01) # bit 4 - image B is running
            ImageBCommitted = ((fwStatus >> 5) & 0x01)  # bit 5 - image B is committed
            ImageBValid = ((fwStatus >> 6) & 0x01) # bit 6 - image B is valid

            if ImageARunning == 1: 
                RunningImage = 'A'
            elif ImageBRunning == 1:
                RunningImage = 'B'
            if ImageACommitted == 1:
                CommittedImage = 'A'
            elif ImageBCommitted == 1:
                CommittedImage = 'B'
            logger.info('Running Image: %s; Committed Image: %s' %(RunningImage, CommittedImage))
        else:
            raise ValueError('Reply payload check code error')
        elapsedtime = time.time()-starttime
        logger.info('Get module FW info time: %.2f s' %elapsedtime)
        return ImageA, ImageARunning, ImageACommitted, ImageAValid, ImageB, ImageBRunning, ImageBCommitted, ImageBValid

    def module_fw_run(self, mode = 0x01):
        """
        This command is used to start and run a selected image. 
        This command transfers control from the currently 
        running firmware to a selected firmware that is started. It 
        can be used to switch between firmware versions, or to 
        perform a restart of the currently running firmware.
        mode:
        00h = Traffic affecting Reset to Inactive Image.
        01h = Attempt Hitless Reset to Inactive Image
        02h = Traffic affecting Reset to Running Image.
        03h = Attempt Hitless Reset to Running Image
        """
        try:
            self.cdb
        except AttributeError:
            self.get_cdb_api()
        # run module FW (CMD 0109h)
        starttime = time.time()
        fw_run_status = self.cdb.cmd0109h(mode)
        if fw_run_status == 1:
            logger.info('Module FW run: Success')
        else:
            self.cdb.cmd0102h()
            logger.info('Module FW run: Fail')
        elapsedtime = time.time()-starttime
        logger.info('Module FW run time: %.2f s\n' %elapsedtime)

    def module_fw_commit(self):
        """
        The host uses this command to commit the running image 
        so that the module will boot from it on future boots.
        """
        try:
            self.cdb
        except AttributeError:
            self.get_cdb_api()
        # commit module FW (CMD 010Ah)
        starttime = time.time()
        fw_commit_status= self.cdb.cmd010Ah()
        if fw_commit_status == 1:
            logger.info('Module FW commit: Success')
        else:
            self.cdb.cmd0102h()
            logger.info('Module FW commit: Fail')
        elapsedtime = time.time()-starttime
        logger.info('Module FW commit time: %.2f s\n' %elapsedtime)

    def module_fw_download(self, startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength, imagepath):
        """
        This function performs the download of a firmware image to module eeprom
        It starts CDB download by writing the header of start header size
        from the designated firmware file to the local payload page 0x9F, with CDB command 0101h.

        Then it repeatedly reads from the given firmware file and write to the payload
        space advertised from the first step. We use CDB command 0103h to write to the local payload;
        we use CDB command 0104h to write to the extended paylaod. This step repeats until it reaches
        end of the firmware file, or the CDB status failed.

        The last step is to complete the firmware upgrade with CDB command 0107h.

        Note that if the download process fails anywhere in the middle, we need to run CDB command 0102h
        to abort the upgrade before we restart another upgrade process.
        """
        try:
            self.cdb
        except AttributeError:
            self.get_cdb_api()
        # start fw download (CMD 0101h)
        starttime = time.time()
        f = open(imagepath, 'rb')
        f.seek(0, 2)
        imagesize = f.tell()
        f.seek(0, 0)
        startdata = f.read(startLPLsize)
        if self.cdb.password_type == 'msaPassword':
            self.xcvr_eeprom.write_raw(122, 4, b'\x00\x00\x10\x11')
        logger.info('\nStart FW downloading')
        logger.info("startLPLsize is %d" %startLPLsize)
        fw_start_status = self.cdb.cmd0101h(startLPLsize, bytearray(startdata), imagesize)
        if fw_start_status == 1:
            logger.info('Start module FW download: Success')
        else:
            logger.info('Start module FW download: Fail')
            self.cdb.cmd0102h()
            raise ValueError('FW_start_status %d' %fw_start_status)
        elapsedtime = time.time()-starttime
        logger.info('Start module FW download time: %.2f s' %elapsedtime)

        # start periodically writing (CMD 0103h or 0104h)
        assert maxblocksize == 2048 or lplonly_flag
        if lplonly_flag:
            BLOCK_SIZE = 116
        else:
            BLOCK_SIZE = maxblocksize
        address = 0
        remaining = imagesize - startLPLsize
        logger.info("\nTotal size: {} start bytes: {} remaining: {}".format(imagesize, startLPLsize, remaining))
        while remaining > 0:
            if remaining < BLOCK_SIZE:
                count = remaining
            else:
                count = BLOCK_SIZE
            data = f.read(count)
            progress = (imagesize - remaining) * 100.0 / imagesize
            if lplonly_flag:
                fw_download_status = self.cdb.cmd0103h(address, data)
            else:
                fw_download_status = self.cdb.cmd0104h(address, data, autopaging_flag, writelength)
            if fw_download_status != 1:
                logger.info('CDB download failed. CDB Status: %d' %fw_download_status)
                exit(1)
            elapsedtime = time.time()-starttime
            logger.info('Address: {:#08x}; Count: {}; Progress: {:.2f}%; Time: {:.2f}s'.format(address, count, progress, elapsedtime))
            address += count
            remaining -= count
        elapsedtime = time.time()-starttime
        logger.info('Total module FW download time: %.2f s' %elapsedtime)

        time.sleep(2)
        # complete FW download (CMD 0107h)
        fw_complete_status = self.cdb.cmd0107h()
        if fw_complete_status == 1:
            logger.info('Module FW download complete: Success')
        else:
            logger.info('Module FW download complete: Fail')
        elapsedtime = time.time()-elapsedtime-starttime
        logger.info('Complete module FW download time: %.2f s\n' %elapsedtime)

    def module_fw_upgrade(self, imagepath):
        """
        This function performs firmware upgrade. 
        1.  show FW version in the beginning 
        2.  check module advertised FW download capability
        3.  configure download
        4.  show download progress
        5.  configure run downloaded firmware
        6.  configure commit downloaded firmware
        7.  show FW version in the end
        """
        self.get_module_fw_info()
        startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength = self.get_module_fw_upgrade_feature()
        self.module_fw_download(startLPLsize, maxblocksize, lplonly_flag, autopaging_flag, writelength, imagepath)
        self.module_fw_run(mode = 0x01)
        time.sleep(60)
        self.module_fw_commit()
        self.get_module_fw_info()

    def module_fw_switch(self):
        """
        This function switch the active/inactive module firmware in the current module memory
        """
        _, _, _, ImageAValid, _, _, _, ImageBValid = self.get_module_fw_info()
        if ImageAValid == 0 and ImageBValid == 0:
            self.module_fw_run(mode = 0x01)
            time.sleep(60)
            self.module_fw_commit()
            self.get_module_fw_info()
        else:
            logger.info('Not both images are valid.')
    # TODO: other XcvrApi methods


