"""
    c-cmis.py

    Implementation of XcvrApi that corresponds to C-CMIS
"""
from ...fields import consts
from ..xcvr_api import XcvrApi
import time
BYTELENGTH = 8
class CCmisApi(XcvrApi):
    NUM_CHANNELS = 8

    def __init__(self, xcvr_eeprom):
        super(CCmisApi, self).__init__(xcvr_eeprom)

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
        return self.xcvr_eeprom.read(consts.VENDOR_REV)

    def get_vendor_serial(self):
        '''
        This function returns the serial number of the module
        '''
        return self.xcvr_eeprom.read(consts.VENDOR_SERIAL_NO)

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
        return self.xcvr_eeprom.read(consts.VENDOR_DATE)

    def get_connector_type(self):
        '''
        This function returns module connector. Table 4-3 in SFF-8024 Rev4.6
        '''
        return self.xcvr_eeprom.read(consts.CONNECTOR_TYPE)

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
        case_temp_dict = dict()
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
        voltage_dict = dict()
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
        tx_power_dict = dict()
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
        rx_power_dict = dict()
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
        tx_bias_current_dict = dict()
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

    def get_freq_grid(self):
        '''
        This function returns the configured frequency grid. Unit in GHz
        '''
        freq_grid = self.xcvr_eeprom.read(consts.GRID_SPACING) >> 4
        if freq_grid == 7:
            return 75
        elif freq_grid == 6:
            return 33
        elif freq_grid == 5:
            return 100
        elif freq_grid == 4:
            return 50
        elif freq_grid == 3:
            return 25
        elif freq_grid == 2:
            return 12.5
        elif freq_grid == 1:
            return 6.25
        elif freq_grid == 0:
            return 3.125

    def get_laser_config_freq(self):
        '''
        This function returns the configured laser frequency. Unit in MHz
        '''
        freq_grid = self.get_freq_grid()
        channel = self.xcvr_eeprom.read(consts.LASER_CONFIG_CHANNEL)
        if freq_grid == 75:
            config_freq = 193100000 + channel * freq_grid/3*1000 
        else:
            config_freq = 193100000 + channel * freq_grid
        return config_freq

    def get_current_laser_freq(self):
        '''
        This function returns the monitored laser frequency. Unit in MHz
        '''
        return self.xcvr_eeprom.read(consts.LASER_CURRENT_FREQ)

    def get_TX_config_power(self):
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
        laser_temp_dict = dict()
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
        laser_tec_current_dict = dict()
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


    def get_PM(self):
        '''
        This function returns the PMs reported in Page 34h and 35h in OIF C-CMIS document
        CD:     unit in ps/nm
        DGD:    unit in ps
        SOPMD:  unit in ps^2
        PDL:    unit in dB
        OSNR:   unit in dB
        ESNR:   unit in dB
        CFO:    unit in MHz
        TXpower:unit in dBm
        RXpower:unit in dBm
        RX sig power:   unit in dBm
        SOPROC: unit in krad/s
        MER:    unit in dB
        '''
        self.xcvr_eeprom.write(consts.VDM_CONTROL, 128)
        time.sleep(5)
        self.xcvr_eeprom.write(consts.VDM_CONTROL, 0)
        PM_dict = dict()

        rx_bits_pm = self.xcvr_eeprom.read(consts.RX_BITS_PM)
        rx_bits_subint_pm = self.xcvr_eeprom.read(consts.RX_BITS_SUB_INTERVAL_PM)
        rx_corr_bits_pm = self.xcvr_eeprom.read(consts.RX_CORR_BITS_PM)
        rx_min_corr_bits_subint_pm = self.xcvr_eeprom.read(consts.RX_MIN_CORR_BITS_SUB_INTERVAL_PM)
        rx_max_corr_bits_subint_pm = self.xcvr_eeprom.read(consts.RX_MAX_CORR_BITS_SUB_INTERVAL_PM)

        if (rx_bits_subint_pm != 0) and (rx_bits_pm != 0):
            PM_dict['preFEC_BER_cur'] = rx_corr_bits_pm*1.0/rx_bits_pm
            PM_dict['preFEC_BER_min'] = rx_min_corr_bits_subint_pm*1.0/rx_bits_subint_pm
            PM_dict['preFEC_BER_max'] = rx_max_corr_bits_subint_pm*1.0/rx_bits_subint_pm

        rx_frames_pm = self.xcvr_eeprom.read(consts.RX_FRAMES_PM)
        rx_frames_subint_pm = self.xcvr_eeprom.read(consts.RX_FRAMES_SUB_INTERVAL_PM)
        rx_frames_uncorr_err_pm = self.xcvr_eeprom.read(consts.RX_FRAMES_UNCORR_ERR_PM)
        rx_min_frames_uncorr_err_subint_pm = self.xcvr_eeprom.read(consts.RX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM)
        rx_max_frames_uncorr_err_subint_pm = self.xcvr_eeprom.read(consts.RX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM)

        if (rx_frames_subint_pm != 0) and (rx_frames_pm != 0):
            PM_dict['preFEC_uncorr_frame_ratio_cur'] = rx_frames_uncorr_err_pm*1.0/rx_frames_subint_pm
            PM_dict['preFEC_uncorr_frame_ratio_min'] = rx_min_frames_uncorr_err_subint_pm*1.0/rx_frames_subint_pm
            PM_dict['preFEC_uncorr_frame_ratio_max'] = rx_max_frames_uncorr_err_subint_pm*1.0/rx_frames_subint_pm        

        PM_dict['rx_cd_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_CD_PM)
        PM_dict['rx_cd_min'] = self.xcvr_eeprom.read(consts.RX_MIN_CD_PM)
        PM_dict['rx_cd_max'] = self.xcvr_eeprom.read(consts.RX_MAX_CD_PM)

        PM_dict['rx_dgd_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_DGD_PM)
        PM_dict['rx_dgd_min'] = self.xcvr_eeprom.read(consts.RX_MIN_DGD_PM)
        PM_dict['rx_dgd_max'] = self.xcvr_eeprom.read(consts.RX_MAX_DGD_PM)

        PM_dict['rx_sopmd_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_SOPMD_PM)
        PM_dict['rx_sopmd_min'] = self.xcvr_eeprom.read(consts.RX_MIN_SOPMD_PM)
        PM_dict['rx_sopmd_max'] = self.xcvr_eeprom.read(consts.RX_MAX_SOPMD_PM)

        PM_dict['rx_pdl_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_PDL_PM)
        PM_dict['rx_pdl_min'] = self.xcvr_eeprom.read(consts.RX_MIN_PDL_PM)
        PM_dict['rx_pdl_max'] = self.xcvr_eeprom.read(consts.RX_MAX_PDL_PM)

        PM_dict['rx_osnr_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_OSNR_PM)
        PM_dict['rx_osnr_min'] = self.xcvr_eeprom.read(consts.RX_MIN_OSNR_PM)
        PM_dict['rx_osnr_max'] = self.xcvr_eeprom.read(consts.RX_MAX_OSNR_PM)

        PM_dict['rx_esnr_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_ESNR_PM)
        PM_dict['rx_esnr_min'] = self.xcvr_eeprom.read(consts.RX_MIN_ESNR_PM)
        PM_dict['rx_esnr_max'] = self.xcvr_eeprom.read(consts.RX_MAX_ESNR_PM)

        PM_dict['rx_cfo_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_CFO_PM)
        PM_dict['rx_cfo_min'] = self.xcvr_eeprom.read(consts.RX_MIN_CFO_PM)
        PM_dict['rx_cfo_max'] = self.xcvr_eeprom.read(consts.RX_MAX_CFO_PM)

        PM_dict['rx_evm_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_EVM_PM)
        PM_dict['rx_evm_min'] = self.xcvr_eeprom.read(consts.RX_MIN_EVM_PM)
        PM_dict['rx_evm_max'] = self.xcvr_eeprom.read(consts.RX_MAX_EVM_PM)

        PM_dict['tx_power_avg'] = self.xcvr_eeprom.read(consts.TX_AVG_POWER_PM)
        PM_dict['tx_power_min'] = self.xcvr_eeprom.read(consts.TX_MIN_POWER_PM)
        PM_dict['tx_power_max'] = self.xcvr_eeprom.read(consts.TX_MAX_POWER_PM)

        PM_dict['rx_power_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_POWER_PM)
        PM_dict['rx_power_min'] = self.xcvr_eeprom.read(consts.RX_MIN_POWER_PM)
        PM_dict['rx_power_max'] = self.xcvr_eeprom.read(consts.RX_MAX_POWER_PM)

        PM_dict['rx_sigpwr_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_SIG_POWER_PM)
        PM_dict['rx_sigpwr_min'] = self.xcvr_eeprom.read(consts.RX_MIN_SIG_POWER_PM)
        PM_dict['rx_sigpwr_max'] = self.xcvr_eeprom.read(consts.RX_MAX_SIG_POWER_PM)

        PM_dict['rx_soproc_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_SOPROC_PM)
        PM_dict['rx_soproc_min'] = self.xcvr_eeprom.read(consts.RX_MIN_SOPROC_PM)
        PM_dict['rx_soproc_max'] = self.xcvr_eeprom.read(consts.RX_MAX_SOPROC_PM)

        PM_dict['rx_mer_avg'] = self.xcvr_eeprom.read(consts.RX_AVG_MER_PM)
        PM_dict['rx_mer_min'] = self.xcvr_eeprom.read(consts.RX_MIN_MER_PM)
        PM_dict['rx_mer_max'] = self.xcvr_eeprom.read(consts.RX_MAX_MER_PM)
        return PM_dict


    # Transceiver status
    def get_module_state(self):
        '''
        This function returns the module state
        '''
        result = self.xcvr_eeprom.read(consts.MODULE_STATE) >> 1
        DICT = self.xcvr_eeprom.mem_map.codes['cmis_code'].MODULE_STATE
        return DICT.get(result, "Unknown")

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
        DICT = self.xcvr_eeprom.mem_map.codes['cmis_code'].DATAPATH_STATE
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
        This function returns whether TX output signals are valid
        '''
        result = self.xcvr_eeprom.read(consts.TX_OUTPUT_STATUS)
        tx_output_status_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_output_status_dict['TX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return tx_output_status_dict

    def get_rx_output_status(self):
        '''
        This function returns whether RX output signals are valid
        '''
        result = self.xcvr_eeprom.read(consts.RX_OUTPUT_STATUS)
        rx_output_status_dict = dict()
        for bitpos in range(BYTELENGTH):
            rx_output_status_dict['RX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return rx_output_status_dict

    def get_tx_fault(self):
        '''
        This function returns TX failure flag 
        '''
        result = self.xcvr_eeprom.read(consts.TX_FAULT_FLAG)
        tx_fault_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_fault_dict['TX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return tx_fault_dict

    def get_tx_los(self):
        '''
        This function returns TX LOS flag 
        '''
        result = self.xcvr_eeprom.read(consts.TX_LOS_FLAG)
        tx_los_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_los_dict['TX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return tx_los_dict

    def get_tx_cdr_lol(self):
        '''
        This function returns TX CDR LOL flag
        '''
        result = self.xcvr_eeprom.read(consts.TX_CDR_LOL)
        tx_lol_dict = dict()
        for bitpos in range(BYTELENGTH):
            tx_lol_dict['TX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return tx_lol_dict

    def get_tx_power_flag(self):
        '''
        This function returns TX power out of range flag
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
        This function returns TX bias out of range flag
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
        This function returns RX power out of range flag
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
        This function returns RX LOS flag 
        '''
        result = self.xcvr_eeprom.read(consts.RX_LOS_FLAG)
        rx_los_dict = dict()
        for bitpos in range(BYTELENGTH):
            rx_los_dict['RX_lane%d' %(bitpos+1)] = bool((result >> bitpos) & 0x1)
        return rx_los_dict        

    def get_rx_cdr_lol(self):
        '''
        This function returns RX CDR LOL flag
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
        config_status_raw = [config_status_lane1, config_status_lane2, config_status_lane3, config_status_lane4,
                             config_status_lane5, config_status_lane6, config_status_lane7, config_status_lane8]
        DICT = self.xcvr_eeprom.mem_map.codes['cmis_code'].CONFIG_STATUS
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

    def get_tuning_in_progress(self):
        '''
        This function returns tunning in progress status.
        0 means tuning not in progress
        1 means tuning in progress
        '''
        return bool(self.xcvr_eeprom.read(consts.TUNING_IN_PROGRESS))

    def get_wavelength_unlocked(self):
        '''
        This function returns wavelength unlocked status.
        0 means wavelength locked
        1 means wavelength unlocked
        '''
        return bool(self.xcvr_eeprom.read(consts.WAVELENGTH_UNLOCKED))

    def get_laser_tuning_summary(self):
        '''
        This function returns laser tuning status summary
        '''
        result = self.xcvr_eeprom.read(consts.LASER_TUNING_DETAIL)
        laser_tuning_summary = []
        if (result >> 5) & 0x1:
            laser_tuning_summary.append("TargetOutputPowerOOR")
        if (result >> 4) & 0x1:
            laser_tuning_summary.append("FineTuningOutOfRange")
        if (result >> 3) & 0x1:
            laser_tuning_summary.append("TuningNotAccepted")
        if (result >> 2) & 0x1:
            laser_tuning_summary.append("InvalidChannel")
        if (result >> 1) & 0x1:
            laser_tuning_summary.append("WavelengthUnlocked")
        if (result >> 0) & 0x1:
            laser_tuning_summary.append("TuningComplete")
        return laser_tuning_summary

    def set_low_power(self, AssertLowPower):
        '''
        This function sets the module to low power state. 
        AssertLowPower being 0 means "set to high power"
        AssertLowPower being 1 means "set to low power"
        '''
        low_power_control = AssertLowPower << 6
        self.xcvr_eeprom.write(consts.MODULE_LEVEL_CONTROL, low_power_control)

    def set_laser_freq(self, freq):
        '''
        This function sets the laser frequency. Unit in THz
        ZR application will not support fine tuning of the laser
        '''
        GridSupported = self.xcvr_eeprom.read(consts.SUPPORT_GRID)
        GridSupported_75GHz = (GridSupported >> 7) & 0x1
        assert GridSupported_75GHz
        freq_grid = 0x70
        self.xcvr_eeprom.write(consts.GRID_SPACING, freq_grid)
        channel_number = int(round((freq - 193.1)/0.025))
        assert channel_number % 3 == 0
        low_ch_num = self.xcvr_eeprom.read(consts.LOW_CHANNEL)
        hi_ch_num = self.xcvr_eeprom.read(consts.HIGH_CHANNEL)
        if channel_number > hi_ch_num or channel_number < low_ch_num:
            raise ValueError('Provisioned frequency out of range. Max Freq: 196.1; Min Freq: 191.3 THz.')
        self.set_low_power(True)
        time.sleep(5)
        self.xcvr_eeprom.write(consts.LASER_CONFIG_CHANNEL, channel_number)
        time.sleep(1)
        self.set_low_power(False)
        time.sleep(1)
    
    def set_TX_power(self, TX_power):
        '''
        This function sets the TX output power. Unit in dBm
        '''
        min_prog_tx_output_power = self.xcvr_eeprom.read(consts.MIN_PROG_OUTPUT_POWER)
        max_prog_tx_output_power = self.xcvr_eeprom.read(consts.MAX_PROG_OUTPUT_POWER)
        if TX_power > max_prog_tx_output_power or TX_power < min_prog_tx_output_power:
            raise ValueError('Provisioned TX power out of range. Max: %.1f; Min: %.1f dBm.' 
                             %(max_prog_tx_output_power, min_prog_tx_output_power))
        self.xcvr_eeprom.write(consts.TX_CONFIG_POWER, TX_power)
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
            self.xcvr_eeprom.write(consts.MEDIA_INPUT_LOOPBACK, 0x1)
        elif loopback_mode == 'media-side-output':
            assert loopback_capability['media_side_output_loopback_supported']
            self.xcvr_eeprom.write(consts.MEDIA_OUTPUT_LOOPBACK, 0x1)