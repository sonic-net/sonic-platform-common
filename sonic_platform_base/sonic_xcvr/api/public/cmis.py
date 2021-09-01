"""
    cmis.py

    Implementation of XcvrApi that corresponds to CMIS
"""

from ...fields import consts
from ..xcvr_api import XcvrApi
import time
BYTELENGTH = 8
class CmisApi(XcvrApi):
    NUM_CHANNELS = 8

    def __init__(self, xcvr_eeprom):
        super(CmisApi, self).__init__(xcvr_eeprom)

    # Transceiver Information
    def get_model(self):
        return self.xcvr_eeprom.read(consts.VENDOR_PART_NO_FIELD)

    def get_vendor_rev(self):
        return self.xcvr_eeprom.read(consts.VENDOR_REV)

    def get_vendor_serial(self):
        return self.xcvr_eeprom.read(consts.VENDOR_SERIAL_NO)

    def get_vendor_name(self):
        return self.xcvr_eeprom.read(consts.VENDOR_NAME_FIELD)

    def get_module_type(self):
        return self.xcvr_eeprom.read(consts.ID_FIELD)

    def get_vendor_OUI(self):
        return self.xcvr_eeprom.read(consts.VENDOR_OUI_FIELD)

    def get_vendor_date(self):
        return self.xcvr_eeprom.read(consts.VENDOR_DATE)

    def get_connector_type(self):
        return self.xcvr_eeprom.read(consts.CONNECTOR_TYPE)

    def get_module_media_type(self):
        return self.xcvr_eeprom.read(consts.MODULE_MEDIA_TYPE)

    def get_host_electrical_interface(self):
        return self.xcvr_eeprom.read(consts.HOST_ELECTRICAL_INTERFACE)

    def get_module_media_interface(self):
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
        lane_count = self.xcvr_eeprom.read(consts.LANE_COUNT)
        return (lane_count >> 4) & 0xf

    def get_media_lane_count(self):
        lane_count = self.xcvr_eeprom.read(consts.LANE_COUNT)
        return (lane_count) & 0xf

    def get_host_lane_assignment_option(self):
        return self.xcvr_eeprom.read(consts.HOST_LANE_ASSIGNMENT_OPTION)

    def get_media_lane_assignment_option(self):
        return self.xcvr_eeprom.read(consts.MEDIA_LANE_ASSIGNMENT_OPTION)

    def get_active_apsel_hostlane1(self):
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_1)
        return (result >> 4) & 0xf

    def get_active_apsel_hostlane2(self):
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_2)
        return (result >> 4) & 0xf

    def get_active_apsel_hostlane3(self):
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_3)
        return (result >> 4) & 0xf

    def get_active_apsel_hostlane4(self):
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_4)
        return (result >> 4) & 0xf

    def get_active_apsel_hostlane5(self):
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_5)
        return (result >> 4) & 0xf

    def get_active_apsel_hostlane6(self):
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_6)
        return (result >> 4) & 0xf

    def get_active_apsel_hostlane7(self):
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_7)
        return (result >> 4) & 0xf

    def get_active_apsel_hostlane8(self):
        result = self.xcvr_eeprom.read(consts.ACTIVE_APSEL_HOSTLANE_8)
        return (result >> 4) & 0xf  

    def get_media_interface_technology(self):
        return self.xcvr_eeprom.read(consts.MEDIA_INTERFACE_TECH)

    def get_module_hardware_revision(self):
        hw_major_rev = self.xcvr_eeprom.read(consts.HW_MAJOR_REV)
        hw_minor_rev = self.xcvr_eeprom.read(consts.HW_MAJOR_REV)
        hw_rev = [str(num) for num in [hw_major_rev, hw_minor_rev]]
        return '.'.join(hw_rev)
    
    def get_cmis_rev(self):
        cmis = self.xcvr_eeprom.read(consts.CMIS_REVISION)
        cmis_major = (cmis >> 4) & 0xf
        cmis_minor = (cmis) & 0xf
        cmis_rev = [str(num) for num in [cmis_major, cmis_minor]]
        return '.'.join(cmis_rev)
    
    def get_module_active_firmware(self):
        active_fw_major = self.xcvr_eeprom.read(consts.ACTIVE_FW_MAJOR_REV)
        active_fw_minor = self.xcvr_eeprom.read(consts.ACTIVE_FW_MINOR_REV)
        active_fw = [str(num) for num in [active_fw_major, active_fw_minor]]
        return '.'.join(active_fw)

    def get_module_inactive_firmware(self):
        inactive_fw_major = self.xcvr_eeprom.read(consts.INACTIVE_FW_MAJOR_REV)
        inactive_fw_minor = self.xcvr_eeprom.read(consts.INACTIVE_FW_MINOR_REV)
        inactive_fw = [str(num) for num in [inactive_fw_major, inactive_fw_minor]]
        return '.'.join(inactive_fw)

    # Transceiver DOM
    def get_module_temperature(self):
        return self.xcvr_eeprom.read(consts.CASE_TEMP)
    
    def get_module_voltage(self):
        return self.xcvr_eeprom.read(consts.VOLTAGE)

    def get_rxpower1(self):
        return self.xcvr_eeprom.read(consts.RX_POW1)

    def get_rxpower2(self):
        return self.xcvr_eeprom.read(consts.RX_POW2)

    def get_rxpower3(self):
        return self.xcvr_eeprom.read(consts.RX_POW3)

    def get_rxpower4(self):
        return self.xcvr_eeprom.read(consts.RX_POW4)     

    def get_txbias1(self):
        return self.xcvr_eeprom.read(consts.TX_BIAS1)

    def get_txbias2(self):
        return self.xcvr_eeprom.read(consts.TX_BIAS2)

    def get_txbias3(self):
        return self.xcvr_eeprom.read(consts.TX_BIAS3)

    def get_txbias4(self):
        return self.xcvr_eeprom.read(consts.TX_BIAS4)

    def get_freq_grid(self):
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
        freq_grid = self.get_freq_grid()
        channel = self.xcvr_eeprom.read(consts.LASER_CONFIG_CHANNEL)
        if freq_grid == 75:
            config_freq = 193100000 + channel * freq_grid/3*1000 
        else:
            config_freq = 193100000 + channel * freq_grid
        return config_freq

    def get_current_laser_freq(self):
        return self.xcvr_eeprom.read(consts.LASER_CURRENT_FREQ)

    def get_TX_config_power(self):
        return self.xcvr_eeprom.read(consts.TX_CONFIG_POWER)

    def get_media_output_loopback(self):
        result = self.xcvr_eeprom.read(consts.MEDIA_OUTPUT_LOOPBACK)
        return result == 1

    def get_media_input_loopback(self):
        result = self.xcvr_eeprom.read(consts.MEDIA_INPUT_LOOPBACK)
        return result == 1

    def get_host_output_loopback(self):
        result = self.xcvr_eeprom.read(consts.HOST_OUTPUT_LOOPBACK)
        loopback_status = []
        for bitpos in range(BYTELENGTH):
            loopback_status.append(bool((result >> bitpos) & 0x1))
        return loopback_status

    def get_host_input_loopback(self):
        result = self.xcvr_eeprom.read(consts.HOST_INPUT_LOOPBACK)        
        loopback_status = []
        for bitpos in range(BYTELENGTH):
            loopback_status.append(bool((result >> bitpos) & 0x1))
        return loopback_status

    def get_aux_mon_type(self):
        result = self.xcvr_eeprom.read(consts.AUX_MON_TYPE)    
        aux1_mon_type = result & 0x1
        aux2_mon_type = (result >> 1) & 0x1
        aux3_mon_type = (result >> 2) & 0x1
        return aux1_mon_type, aux2_mon_type, aux3_mon_type

    def get_laser_temp(self):
        aux1_mon_type, aux2_mon_type, aux3_mon_type = self.get_aux_mon_type()
        LASER_TEMP_SCALE = 256.0
        if aux2_mon_type == 0:
            laser_temp = self.xcvr_eeprom.read(consts.AUX2_MON)/LASER_TEMP_SCALE
        elif aux2_mon_type == 1 and aux3_mon_type == 0:
            laser_temp = self.xcvr_eeprom.read(consts.AUX3_MON)/LASER_TEMP_SCALE
        else:
            return None
        return laser_temp

    def get_PM(self):
        self.xcvr_eeprom.write(consts.FREEZE_REQUEST, 128)
        time.sleep(5)
        self.xcvr_eeprom.write(consts.FREEZE_REQUEST, 0)
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

    def get_module_state(self):
        result = self.xcvr_eeprom.read(consts.MODULE_STATE) >> 1
        DICT = self.xcvr_eeprom.mem_map.codes.MODULE_STATE
        return DICT.get(result, "Unknown")

    def get_module_firmware_fault_state_changed(self):
        result = self.xcvr_eeprom.read(consts.MODULE_FIRMWARE_FAULT_INFO)
        datapath_firmware_fault = bool((result >> 2) & 0x1)
        module_firmware_fault = bool((result >> 1) & 0x1)
        module_state_changed = bool(result & 0x1)
        return datapath_firmware_fault, module_firmware_fault, module_state_changed

    def get_datapath_state(self):
        result = self.xcvr_eeprom.read(consts.DATAPATH_STATE)
        dp_lane7 = (result >> 0) & 0xf
        dp_lane8 = (result >> 4) & 0xf
        dp_lane5 = (result >> 8) & 0xf
        dp_lane6 = (result >> 12) & 0xf
        dp_lane3 = (result >> 16) & 0xf
        dp_lane4 = (result >> 20) & 0xf
        dp_lane1 = (result >> 24) & 0xf
        dp_lane2 = (result >> 28) & 0xf
        dp_state_raw = [dp_lane1, dp_lane2, dp_lane3, dp_lane4, dp_lane5, dp_lane6, dp_lane7, dp_lane8]
        DICT = self.xcvr_eeprom.mem_map.codes.DATAPATH_STATE
        dp_state = [DICT.get(dp_lane, "Unknown") for dp_lane in dp_state_raw]
        return dp_state

    def get_tx_output_status(self):
        result = self.xcvr_eeprom.read(consts.TX_OUTPUT_STATUS)
        tx_output_status = []
        for bitpos in range(BYTELENGTH):
            tx_output_status.append(bool((result >> bitpos) & 0x1))
        return tx_output_status

    def get_rx_output_status(self):
        result = self.xcvr_eeprom.read(consts.RX_OUTPUT_STATUS)
        rx_output_status = []
        for bitpos in range(BYTELENGTH):
            rx_output_status.append(bool((result >> bitpos) & 0x1))
        return rx_output_status

    def get_tx_fault(self):
        result = self.xcvr_eeprom.read(consts.TX_FAULT_FLAG)
        tx_fault = []
        for bitpos in range(BYTELENGTH):
            tx_fault.append(bool((result >> bitpos) & 0x1))
        return tx_fault

    def get_tx_los(self):
        result = self.xcvr_eeprom.read(consts.TX_LOS_FLAG)
        tx_los = []
        for bitpos in range(BYTELENGTH):
            tx_los.append(bool((result >> bitpos) & 0x1))
        return tx_los        

    def get_tx_cdr_lol(self):
        result = self.xcvr_eeprom.read(consts.TX_CDR_LOL)
        tx_lol = []
        for bitpos in range(BYTELENGTH):
            tx_lol.append(bool((result >> bitpos) & 0x1))
        return tx_lol

    def get_rx_los(self):
        result = self.xcvr_eeprom.read(consts.RX_LOS_FLAG)
        rx_los = []
        for bitpos in range(BYTELENGTH):
            rx_los.append(bool((result >> bitpos) & 0x1))
        return rx_los        

    def get_rx_cdr_lol(self):
        result = self.xcvr_eeprom.read(consts.RX_CDR_LOL)
        rx_lol = []
        for bitpos in range(BYTELENGTH):
            rx_lol.append(bool((result >> bitpos) & 0x1))
        return rx_lol

    def get_config_lane_status(self):
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
        DICT = self.xcvr_eeprom.mem_map.codes.CONFIG_STATUS
        config_status = [DICT.get(config_lane, "Unknown") for config_lane in config_status_raw]
        return config_status

    def get_dpinit_pending(self):
        result = self.xcvr_eeprom.read(consts.DPINIT_PENDING)
        dpinit_pending = []
        for bitpos in range(BYTELENGTH):
            dpinit_pending.append(bool((result >> bitpos) & 0x1))
        return dpinit_pending

    def get_tuning_in_progress(self):
        return bool(self.xcvr_eeprom.read(consts.TUNING_IN_PROGRESS))

    def get_wavelength_unlocked(self):
        return bool(self.xcvr_eeprom.read(consts.WAVELENGTH_UNLOCKED))

    def get_laser_tuning_summary(self):
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
        low_power_control = AssertLowPower << 6
        self.xcvr_eeprom.write(consts.MODULE_LEVEL_CONTROL, low_power_control)

    def set_laser_freq(self, freq):
        freq_grid = 0x70
        self.xcvr_eeprom.write(consts.GRID_SPACING, freq_grid)
        channel_number = int(round((freq - 193.1)/0.025))
        assert channel_number % 3 == 0
        self.set_low_power(True)
        time.sleep(5)
        self.xcvr_eeprom.write(consts.LASER_CONFIG_CHANNEL, channel_number)
        time.sleep(1)
        self.set_low_power(False)
        time.sleep(1)
    
    def set_TX_power(self, TX_power):
        self.xcvr_eeprom.write(consts.TX_CONFIG_POWER, TX_power)
        time.sleep(1)

    def get_loopback_capability(self):
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


    # TODO: other XcvrApi methods


