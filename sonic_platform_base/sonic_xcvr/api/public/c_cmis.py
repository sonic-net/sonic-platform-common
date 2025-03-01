"""
    c-cmis.py

    Implementation of XcvrApi that corresponds to C-CMIS
"""
from sonic_py_common import logger
from ...fields import consts
from .cmis import CmisApi, CMIS_VDM_KEY_TO_DB_PREFIX_KEY_MAP, CMIS_XCVR_INFO_DEFAULT_DICT
import time
import copy
BYTELENGTH = 8
SYSLOG_IDENTIFIER = "CCmisApi"

C_CMIS_DELTA_VDM_KEY_TO_DB_PREFIX_KEY_MAP = {
    'Modulator Bias X/I [%]' : 'biasxi',
    'Modulator Bias X/Q [%]' : 'biasxq',
    'Modulator Bias X_Phase [%]' : 'biasxp',
    'Modulator Bias Y/I [%]' : 'biasyi',
    'Modulator Bias Y/Q [%]' : 'biasyq',
    'Modulator Bias Y_Phase [%]' : 'biasyp',
    'CD high granularity, short link [ps/nm]' : 'cdshort',
    'CD low granularity, long link [ps/nm]' : 'cdlong',
    'DGD [ps]' : 'dgd',
    'SOPMD [ps^2]' : 'sopmd',
    'SOP ROC [krad/s]' : 'soproc',
    'PDL [dB]' : 'pdl',
    'OSNR [dB]' : 'osnr',
    'eSNR [dB]' : 'esnr',
    'CFO [MHz]' : 'cfo',
    'Tx Power [dBm]' : 'txcurrpower',
    'Rx Total Power [dBm]' : 'rxtotpower',
    'Rx Signal Power [dBm]' : 'rxsigpower'
}

VDM_SUBTYPE_IDX_MAP= {
    1: 'highalarm',
    2: 'lowalarm',
    3: 'highwarning',
    4: 'lowwarning',
    5: 'highalarm_flag',
    6: 'lowalarm_flag',
    7: 'highwarning_flag',
    8: 'lowwarning_flag'
}


helper_logger = logger.Logger(SYSLOG_IDENTIFIER)

C_CMIS_XCVR_INFO_DEFAULT_DICT = copy.deepcopy(CMIS_XCVR_INFO_DEFAULT_DICT)
C_CMIS_XCVR_INFO_DEFAULT_DICT.update({
    "supported_max_tx_power": "N/A",
    "supported_min_tx_power": "N/A",
    "supported_max_laser_freq": "N/A",
    "supported_min_laser_freq": "N/A"
})

class CCmisApi(CmisApi):
    def __init__(self, xcvr_eeprom):
        super(CCmisApi, self).__init__(xcvr_eeprom)

    def _get_vdm_key_to_db_prefix_map(self):
        combined_map = {**CMIS_VDM_KEY_TO_DB_PREFIX_KEY_MAP, **C_CMIS_DELTA_VDM_KEY_TO_DB_PREFIX_KEY_MAP}
        return combined_map

    def _update_dict_if_vdm_key_exists(self, dict_to_be_updated, new_key, vdm_dict_key, vdm_subtype_index, lane=1):
        '''
        This function updates the dictionary with the VDM value if the vdm_dict_key exists.
        @param dict_to_be_updated: the dictionary to be updated.
        @param new_key: the key to be added in dict_to_be_updated.
        @param vdm_dict_key: lookup key in the VDM dictionary.
        @param vdm_subtype_index: the index of the VDM subtype in the VDM page.
            0 refers to the real time value
            1 refers to the high alarm threshold
            2 refers to the low alarm threshold
            3 refers to the high warning threshold
            4 refers to the low warning threshold
            5 refers to the high alarm flag
            6 refers to the low alarm flag
            7 refers to the high warning flag
            8 refers to the low warning flag
        @param lane: the lane number. Default is 1.

        @return: True if the key exists in the VDM dictionary, False if not.
        '''
        try:
            dict_to_be_updated[new_key] = self.vdm_dict[vdm_dict_key][lane][vdm_subtype_index]
        except KeyError:
            dict_to_be_updated[new_key] = 'N/A'
            helper_logger.log_debug('key {} not present in VDM'.format(new_key))
            return False

        return True

    def get_freq_grid(self):
        '''
        This function returns the configured frequency grid. Unit in GHz
        '''
        freq_grid = self.xcvr_eeprom.read(consts.GRID_SPACING)
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
        else:
            return None

    def get_laser_config_freq(self):
        '''
        This function returns the configured laser frequency. Unit in GHz
        '''
        freq_grid = self.get_freq_grid()
        channel = self.xcvr_eeprom.read(consts.LASER_CONFIG_CHANNEL)
        if freq_grid == 75:
            config_freq = 193100 + channel * freq_grid/3
        else:
            config_freq = 193100 + channel * freq_grid
        return config_freq

    def get_current_laser_freq(self):
        '''
        This function returns the monitored laser frequency. Unit in GHz
        '''
        return self.xcvr_eeprom.read(consts.LASER_CURRENT_FREQ)

    def get_tuning_in_progress(self):
        '''
        This function returns tuning in progress status on media lane
        False means tuning not in progress
        True means tuning in progress
        '''
        return bool(self.xcvr_eeprom.read(consts.TUNING_IN_PROGRESS))

    def get_wavelength_unlocked(self):
        '''
        This function returns wavelength unlocked status on media lane
        False means wavelength locked
        True means wavelength unlocked
        '''
        return bool(self.xcvr_eeprom.read(consts.WAVELENGTH_UNLOCKED))

    def get_laser_tuning_summary(self):
        '''
        This function returns laser tuning status summary on media lane
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

    def get_supported_freq_config(self):
        '''
        This function returns the supported freq grid, low and high supported channel in 75/100GHz grid,
        and low and high frequency supported in GHz.
        allowed channel number bound in 75/100 GHz grid
        allowed frequency bound in 75/100 GHz grid
        '''
        grid_supported = self.xcvr_eeprom.read(consts.SUPPORT_GRID)
        low_ch_num = self.xcvr_eeprom.read(consts.LOW_CHANNEL)
        hi_ch_num = self.xcvr_eeprom.read(consts.HIGH_CHANNEL)
        low_freq_supported = 193100 + low_ch_num * 25
        high_freq_supported = 193100 + hi_ch_num * 25
        return grid_supported, low_ch_num, hi_ch_num, low_freq_supported, high_freq_supported

    def set_laser_freq(self, freq, grid):
        '''
        This function sets the laser frequency. Unit in GHz
        ZR application will not support fine tuning of the laser
        SONiC will only support 75 GHz and 100GHz frequency grids
        Return True if the provision succeeds, False if it fails
        '''
        grid_supported, low_ch_num, hi_ch_num, _, _ = self.get_supported_freq_config()
        grid_supported_75GHz = (grid_supported >> 7) & 0x1
        grid_supported_100GHz = (grid_supported >> 5) & 0x1
        if grid == 75:
            assert grid_supported_75GHz
            freq_grid = 0x70
            channel_number = int(round((freq - 193100)/25))
            assert channel_number % 3 == 0
        elif grid == 100:
            assert grid_supported_100GHz
            freq_grid = 0x50
            channel_number = int(round((freq - 193100)/100))
        else:
            return False
        self.xcvr_eeprom.write(consts.GRID_SPACING, freq_grid)
        if channel_number > hi_ch_num or channel_number < low_ch_num:
            raise ValueError('Provisioned frequency out of range. Max Freq: 196100; Min Freq: 191300 GHz.')
        status = self.xcvr_eeprom.write(consts.LASER_CONFIG_CHANNEL, channel_number)
        return status

    def set_tx_power(self, tx_power):
        '''
        This function sets the TX output power. Unit in dBm
        Return True if the provision succeeds, False if it fails
        '''
        min_prog_tx_output_power, max_prog_tx_output_power = self.get_supported_power_config()
        status = self.xcvr_eeprom.write(consts.TX_CONFIG_POWER, tx_power)
        time.sleep(1)
        return status

    def get_pm_all(self):
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
        PM_dict = dict()

        rx_bits_pm = self.xcvr_eeprom.read(consts.RX_BITS_PM)
        rx_bits_subint_pm = self.xcvr_eeprom.read(consts.RX_BITS_SUB_INTERVAL_PM)
        rx_corr_bits_pm = self.xcvr_eeprom.read(consts.RX_CORR_BITS_PM)
        rx_min_corr_bits_subint_pm = self.xcvr_eeprom.read(consts.RX_MIN_CORR_BITS_SUB_INTERVAL_PM)
        rx_max_corr_bits_subint_pm = self.xcvr_eeprom.read(consts.RX_MAX_CORR_BITS_SUB_INTERVAL_PM)

        if (rx_bits_subint_pm != 0) and (rx_bits_pm != 0):
            PM_dict['preFEC_BER_avg'] = rx_corr_bits_pm*1.0/rx_bits_pm
            PM_dict['preFEC_BER_min'] = rx_min_corr_bits_subint_pm*1.0/rx_bits_subint_pm
            PM_dict['preFEC_BER_max'] = rx_max_corr_bits_subint_pm*1.0/rx_bits_subint_pm
        # when module is low power, still need these values to show 1.0
        else:
            PM_dict['preFEC_BER_avg'] = 1.0
            PM_dict['preFEC_BER_min'] = 1.0
            PM_dict['preFEC_BER_max'] = 1.0
        rx_frames_pm = self.xcvr_eeprom.read(consts.RX_FRAMES_PM)
        rx_frames_subint_pm = self.xcvr_eeprom.read(consts.RX_FRAMES_SUB_INTERVAL_PM)
        rx_frames_uncorr_err_pm = self.xcvr_eeprom.read(consts.RX_FRAMES_UNCORR_ERR_PM)
        rx_min_frames_uncorr_err_subint_pm = self.xcvr_eeprom.read(consts.RX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM)
        rx_max_frames_uncorr_err_subint_pm = self.xcvr_eeprom.read(consts.RX_MAX_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM)

        if (rx_frames_subint_pm != 0) and (rx_frames_pm != 0):
            PM_dict['preFEC_uncorr_frame_ratio_avg'] = rx_frames_uncorr_err_pm*1.0/rx_frames_subint_pm
            PM_dict['preFEC_uncorr_frame_ratio_min'] = rx_min_frames_uncorr_err_subint_pm*1.0/rx_frames_subint_pm
            PM_dict['preFEC_uncorr_frame_ratio_max'] = rx_max_frames_uncorr_err_subint_pm*1.0/rx_frames_subint_pm
        # when module is low power, still need these values
        else:
            PM_dict['preFEC_uncorr_frame_ratio_avg'] = 0
            PM_dict['preFEC_uncorr_frame_ratio_min'] = 0
            PM_dict['preFEC_uncorr_frame_ratio_max'] = 0
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

    def _get_xcvr_info_default_dict(self):
        return C_CMIS_XCVR_INFO_DEFAULT_DICT

    def get_transceiver_info(self):
        """
        Retrieves transceiver info of this SFP

        Returns:
            A dict which contains following keys/values :
        ================================================================================
        key                          = TRANSCEIVER_INFO|ifname  ; information for module on port
        ; field                      = value
        module_media_type            = 1*255VCHAR               ; module media interface ID
        host_electrical_interface    = 1*255VCHAR               ; host electrical interface ID
        media_interface_code         = 1*255VCHAR               ; media interface code
        host_lane_count              = INTEGER                  ; host lane count
        media_lane_count             = INTEGER                  ; media lane count
        host_lane_assignment_option  = INTEGER                  ; permissible first host lane number for application
        media_lane_assignment_option = INTEGER                  ; permissible first media lane number for application
        active_apsel_hostlane1       = INTEGER                  ; active application selected code assigned to host lane 1
        active_apsel_hostlane2       = INTEGER                  ; active application selected code assigned to host lane 2
        active_apsel_hostlane3       = INTEGER                  ; active application selected code assigned to host lane 3
        active_apsel_hostlane4       = INTEGER                  ; active application selected code assigned to host lane 4
        active_apsel_hostlane5       = INTEGER                  ; active application selected code assigned to host lane 5
        active_apsel_hostlane6       = INTEGER                  ; active application selected code assigned to host lane 6
        active_apsel_hostlane7       = INTEGER                  ; active application selected code assigned to host lane 7
        active_apsel_hostlane8       = INTEGER                  ; active application selected code assigned to host lane 8
        media_interface_technology   = 1*255VCHAR               ; media interface technology
        hardwarerev                  = 1*255VCHAR               ; module hardware revision 
        serialnum                    = 1*255VCHAR               ; module serial number 
        manufacturename              = 1*255VCHAR               ; module venndor name
        modelname                    = 1*255VCHAR               ; module model name
        vendor_rev                   = 1*255VCHAR               ; module vendor revision
        vendor_oui                   = 1*255VCHAR               ; vendor organizationally unique identifier
        vendor_date                  = 1*255VCHAR               ; module manufacture date
        connector_type               = 1*255VCHAR               ; connector type
        specification_compliance     = 1*255VCHAR               ; electronic or optical interfaces that supported
        active_firmware              = 1*255VCHAR               ; active firmware
        inactive_firmware            = 1*255VCHAR               ; inactive firmware
        supported_max_tx_power       = FLOAT                    ; support maximum tx power
        supported_min_tx_power       = FLOAT                    ; support minimum tx power
        supported_max_laser_freq     = FLOAT                    ; support maximum laser frequency
        supported_min_laser_freq     = FLOAT                    ; support minimum laser frequency
        ================================================================================
        """
        xcvr_info = super(CCmisApi, self).get_transceiver_info()

        # Return None if CmisApi class returns None, this indicates to XCVRD that retry is
        # needed.
        if xcvr_info is None:
            return None

        min_power, max_power = self.get_supported_power_config()
        _, _, _, low_freq_supported, high_freq_supported = self.get_supported_freq_config()
        xcvr_info.update({
            'supported_max_tx_power': max_power,
            'supported_min_tx_power': min_power,
            'supported_max_laser_freq': high_freq_supported,
            'supported_min_laser_freq': low_freq_supported
        })
        return xcvr_info

    def get_transceiver_bulk_status(self):
        """
        Retrieves bulk status info for this xcvr

        Returns:
            A dict containing the following keys/values :
        ========================================================================
        key                          = TRANSCEIVER_DOM_SENSOR|ifname    ; information module DOM sensors on port
        ; field                      = value
        temperature                  = FLOAT                            ; temperature value in Celsius
        voltage                      = FLOAT                            ; voltage value
        txpower                      = FLOAT                            ; tx power in mW
        rxpower                      = FLOAT                            ; rx power in mW
        txbias                       = FLOAT                            ; tx bias in mA
        laser_temperature	         = FLOAT                            ; laser temperature value in Celsius
        prefec_ber                   = FLOAT                            ; prefec ber
        postfec_ber                  = FLOAT                            ; postfec ber
        cd_shortlink                 = FLOAT                            ; chromatic dispersion, high granularity, short link in ps/nm
        cd_longlink                  = FLOAT                            ; chromatic dispersion, low granularity, long link in ps/nm
        dgd                          = FLOAT                            ; differential group delay in ps
        sopmd                        = FLOAT                            ; second order polarization mode dispersion in ps^2
        pdl                          = FLOAT                            ; polarization dependent loss in db
        osnr                         = FLOAT                            ; optical signal to noise ratio in db
        esnr                         = FLOAT                            ; electrical signal to noise ratio in db
        cfo                          = FLOAT                            ; carrier frequency offset in MHz
        soproc                       = FLOAT                            ; state of polarization rate of change in krad/s
        laser_config_freq            = FLOAT                            ; laser configured frequency in MHz
        laser_curr_freq              = FLOAT                            ; laser current frequency in MHz
        tx_config_power              = FLOAT                            ; configured tx output power in dbm
        tx_curr_power                = FLOAT                            ; tx current output power in dbm
        rx_tot_power                 = FLOAT                            ; rx total power in  dbm
        rx_sig_power                 = FLOAT                            ; rx signal power in dbm
        bias_xi                      = FLOAT                            ; modulator bias xi
        bias_xq                      = FLOAT                            ; modulator bias xq
        bias_xp                      = FLOAT                            ; modulator bias xp
        bias_yi                      = FLOAT                            ; modulator bias yi
        bias_yq                      = FLOAT                            ; modulator bias yq
        bias_yp                      = FLOAT                            ; modulator bias yp
        ========================================================================
        """
        trans_dom = super(CCmisApi,self).get_transceiver_bulk_status()

        for vdm_key, trans_dom_key in C_CMIS_DELTA_VDM_KEY_TO_DB_PREFIX_KEY_MAP.items():
            self._update_dict_if_vdm_key_exists(trans_dom, trans_dom_key, vdm_key, 0)

        trans_dom['laser_config_freq'] = self.get_laser_config_freq()
        trans_dom['laser_curr_freq'] = self.get_current_laser_freq()
        trans_dom['tx_config_power'] = self.get_tx_config_power()
        return trans_dom

    def get_transceiver_threshold_info(self):
        """
        Retrieves threshold info for this xcvr

        Returns:
            A dict containing the following keys/values :
        ========================================================================
        key                          = TRANSCEIVER_STATUS|ifname        ; DOM threshold information for module on port
        ; field                      = value
        temphighalarm                = FLOAT                            ; temperature high alarm threshold in Celsius
        temphighwarning              = FLOAT                            ; temperature high warning threshold in Celsius
        templowalarm                 = FLOAT                            ; temperature low alarm threshold in Celsius
        templowwarning               = FLOAT                            ; temperature low warning threshold in Celsius
        vcchighalarm                 = FLOAT                            ; vcc high alarm threshold in V
        vcchighwarning               = FLOAT                            ; vcc high warning threshold in V
        vcclowalarm                  = FLOAT                            ; vcc low alarm threshold in V
        vcclowwarning                = FLOAT                            ; vcc low warning threshold in V
        txpowerhighalarm             = FLOAT                            ; tx power high alarm threshold in mW
        txpowerlowalarm              = FLOAT                            ; tx power low alarm threshold in mW
        txpowerhighwarning           = FLOAT                            ; tx power high warning threshold in mW
        txpowerlowwarning            = FLOAT                            ; tx power low alarm threshold in mW
        rxpowerhighalarm             = FLOAT                            ; rx power high alarm threshold in mW
        rxpowerlowalarm              = FLOAT                            ; rx power low alarm threshold in mW
        rxpowerhighwarning           = FLOAT                            ; rx power high warning threshold in mW
        rxpowerlowwarning            = FLOAT                            ; rx power low warning threshold in mW
        txbiashighalarm              = FLOAT                            ; tx bias high alarm threshold in mA
        txbiaslowalarm               = FLOAT                            ; tx bias low alarm threshold in mA
        txbiashighwarning            = FLOAT                            ; tx bias high warning threshold in mA
        txbiaslowwarning             = FLOAT                            ; tx bias low warning threshold in mA
        lasertemphighalarm           = FLOAT                            ; laser temperature high alarm threshold in Celsius
        lasertemplowalarm            = FLOAT                            ; laser temperature low alarm threshold in Celsius
        lasertemphighwarning         = FLOAT                            ; laser temperature high warning threshold in Celsius
        lasertemplowwarning          = FLOAT                            ; laser temperature low warning threshold in Celsius
        prefecberhighalarm           = FLOAT                            ; prefec ber high alarm threshold
        prefecberlowalarm            = FLOAT                            ; prefec ber low alarm threshold
        prefecberhighwarning         = FLOAT                            ; prefec ber high warning threshold
        prefecberlowwarning          = FLOAT                            ; prefec ber low warning threshold
        postfecberhighalarm          = FLOAT                            ; postfec ber high alarm threshold
        postfecberlowalarm           = FLOAT                            ; postfec ber low alarm threshold
        postfecberhighwarning        = FLOAT                            ; postfec ber high warning threshold
        postfecberlowwarning         = FLOAT                            ; postfec ber low warning threshold
        biasxihighalarm              = FLOAT                            ; bias xi high alarm threshold in percent
        biasxilowalarm               = FLOAT                            ; bias xi low alarm threshold in percent
        biasxihighwarning            = FLOAT                            ; bias xi high warning threshold in percent
        biasxilowwarning             = FLOAT                            ; bias xi low warning threshold in percent
        biasxqhighalarm              = FLOAT                            ; bias xq high alarm threshold in percent
        biasxqlowalarm               = FLOAT                            ; bias xq low alarm threshold in percent
        biasxqhighwarning            = FLOAT                            ; bias xq high warning threshold in percent
        biasxqlowwarning             = FLOAT                            ; bias xq low warning threshold in percent
        biasxphighalarm              = FLOAT                            ; bias xp high alarm threshold in percent
        biasxplowalarm               = FLOAT                            ; bias xp low alarm threshold in percent
        biasxphighwarning            = FLOAT                            ; bias xp high warning threshold in percent
        biasxplowwarning             = FLOAT                            ; bias xp low warning threshold in percent
        biasyihighalarm              = FLOAT                            ; bias yi high alarm threshold in percent
        biasyilowalarm               = FLOAT                            ; bias yi low alarm threshold in percent
        biasyihighwarning            = FLOAT                            ; bias yi high warning threshold in percent
        biasyilowwarning             = FLOAT                            ; bias yi low warning threshold in percent
        biasyqhighalarm              = FLOAT                            ; bias yq high alarm threshold in percent
        biasyqlowalarm               = FLOAT                            ; bias yq low alarm threshold in percent
        biasyqhighwarning            = FLOAT                            ; bias yq high warning threshold in percent
        biasyqlowwarning             = FLOAT                            ; bias yq low warning threshold in percent
        biasyphighalarm              = FLOAT                            ; bias yp high alarm threshold in percent
        biasyplowalarm               = FLOAT                            ; bias yp low alarm threshold in percent
        biasyphighwarning            = FLOAT                            ; bias yp high warning threshold in percent
        biasyplowwarning             = FLOAT                            ; bias yp low warning threshold in percent
        cdshorthighalarm             = FLOAT                            ; cd short high alarm threshold in ps/nm
        cdshortlowalarm              = FLOAT                            ; cd short low alarm threshold in ps/nm
        cdshorthighwarning           = FLOAT                            ; cd short high warning threshold in ps/nm
        cdshortlowwarning            = FLOAT                            ; cd short low warning threshold in ps/nm
        cdlonghighalarm              = FLOAT                            ; cd long high alarm threshold in ps/nm
        cdlonglowalarm               = FLOAT                            ; cd long low alarm threshold in ps/nm
        cdlonghighwarning            = FLOAT                            ; cd long high warning threshold in ps/nm
        cdlonglowwarning             = FLOAT                            ; cd long low warning threshold in ps/nm
        dgdhighalarm                 = FLOAT                            ; dgd high alarm threshold in ps
        dgdlowalarm                  = FLOAT                            ; dgd low alarm threshold in ps
        dgdhighwarning               = FLOAT                            ; dgd high warning threshold in ps
        dgdlowwarning                = FLOAT                            ; dgd low warning threshold in ps
        sopmdhighalarm               = FLOAT                            ; sopmd high alarm threshold in ps^2
        sopmdlowalarm                = FLOAT                            ; sopmd low alarm threshold in ps^2
        sopmdhighwarning             = FLOAT                            ; sopmd high warning threshold in ps^2
        sopmdlowwarning              = FLOAT                            ; sopmd low warning threshold in ps^2
        pdlhighalarm                 = FLOAT                            ; pdl high alarm threshold in db
        pdllowalarm                  = FLOAT                            ; pdl low alarm threshold in db
        pdlhighwarning               = FLOAT                            ; pdl high warning threshold in db
        pdllowwarning                = FLOAT                            ; pdl low warning threshold in db
        osnrhighalarm                = FLOAT                            ; osnr high alarm threshold in db
        osnrlowalarm                 = FLOAT                            ; osnr low alarm threshold in db
        osnrhighwarning              = FLOAT                            ; osnr high warning threshold in db
        osnrlowwarning               = FLOAT                            ; osnr low warning threshold in db
        esnrhighalarm                = FLOAT                            ; esnr high alarm threshold in db
        esnrlowalarm                 = FLOAT                            ; esnr low alarm threshold in db
        esnrhighwarning              = FLOAT                            ; esnr high warning threshold in db
        esnrlowwarning               = FLOAT                            ; esnr low warning threshold in db
        cfohighalarm                 = FLOAT                            ; cfo high alarm threshold in MHz
        cfolowalarm                  = FLOAT                            ; cfo low alarm threshold in MHz
        cfohighwarning               = FLOAT                            ; cfo high warning threshold in MHz
        cfolowwarning                = FLOAT                            ; cfo low warning threshold in MHz
        txcurrpowerhighalarm         = FLOAT                            ; txcurrpower high alarm threshold in dbm
        txcurrpowerlowalarm          = FLOAT                            ; txcurrpower low alarm threshold in dbm
        txcurrpowerhighwarning       = FLOAT                            ; txcurrpower high warning threshold in dbm
        txcurrpowerlowwarning        = FLOAT                            ; txcurrpower low warning threshold in dbm
        rxtotpowerhighalarm          = FLOAT                            ; rxtotpower high alarm threshold in dbm
        rxtotpowerlowalarm           = FLOAT                            ; rxtotpower low alarm threshold in dbm
        rxtotpowerhighwarning        = FLOAT                            ; rxtotpower high warning threshold in dbm
        rxtotpowerlowwarning         = FLOAT                            ; rxtotpower low warning threshold in dbm
        rxsigpowerhighalarm          = FLOAT                            ; rxsigpower high alarm threshold in dbm
        rxsigpowerlowalarm           = FLOAT                            ; rxsigpower low alarm threshold in dbm
        rxsigpowerhighwarning        = FLOAT                            ; rxsigpower high warning threshold in dbm
        rxsigpowerlowwarning         = FLOAT                            ; rxsigpower low warning threshold in dbm
        ========================================================================
        """
        trans_dom_th = super(CCmisApi,self).get_transceiver_threshold_info()

        for vdm_key, trans_dom_th_key_prefix in C_CMIS_DELTA_VDM_KEY_TO_DB_PREFIX_KEY_MAP.items():
            for i in range(1, 5):
                trans_dom_th_key = trans_dom_th_key_prefix + VDM_SUBTYPE_IDX_MAP[i]
                self._update_dict_if_vdm_key_exists(trans_dom_th, trans_dom_th_key, vdm_key, i)

        return trans_dom_th

    def get_transceiver_status(self):
        """
        Retrieves transceiver status of this SFP

        Returns:
            A dict which contains following keys/values :
        ================================================================================
        key                          = TRANSCEIVER_STATUS|ifname        ; Error information for module on port
        ; field                      = value
        module_state                 = 1*255VCHAR                       ; current module state (ModuleLowPwr, ModulePwrUp, ModuleReady, ModulePwrDn, Fault)
        module_fault_cause           = 1*255VCHAR                       ; reason of entering the module fault state
        datapath_firmware_fault      = BOOLEAN                          ; datapath (DSP) firmware fault
        module_firmware_fault        = BOOLEAN                          ; module firmware fault
        module_state_changed         = BOOLEAN                          ; module state changed
        datapath_hostlane1           = 1*255VCHAR                       ; data path state indicator on host lane 1
        datapath_hostlane2           = 1*255VCHAR                       ; data path state indicator on host lane 2
        datapath_hostlane3           = 1*255VCHAR                       ; data path state indicator on host lane 3
        datapath_hostlane4           = 1*255VCHAR                       ; data path state indicator on host lane 4
        datapath_hostlane5           = 1*255VCHAR                       ; data path state indicator on host lane 5
        datapath_hostlane6           = 1*255VCHAR                       ; data path state indicator on host lane 6
        datapath_hostlane7           = 1*255VCHAR                       ; data path state indicator on host lane 7
        datapath_hostlane8           = 1*255VCHAR                       ; data path state indicator on host lane 8
        txoutput_status              = BOOLEAN                          ; tx output status on media lane
        rxoutput_status_hostlane1    = BOOLEAN                          ; rx output status on host lane 1
        rxoutput_status_hostlane2    = BOOLEAN                          ; rx output status on host lane 2
        rxoutput_status_hostlane3    = BOOLEAN                          ; rx output status on host lane 3
        rxoutput_status_hostlane4    = BOOLEAN                          ; rx output status on host lane 4
        rxoutput_status_hostlane5    = BOOLEAN                          ; rx output status on host lane 5
        rxoutput_status_hostlane6    = BOOLEAN                          ; rx output status on host lane 6
        rxoutput_status_hostlane7    = BOOLEAN                          ; rx output status on host lane 7
        rxoutput_status_hostlane8    = BOOLEAN                          ; rx output status on host lane 8
        txfault                      = BOOLEAN                          ; tx fault flag on media lane
        txlos_hostlane1              = BOOLEAN                          ; tx loss of signal flag on host lane 1
        txlos_hostlane2              = BOOLEAN                          ; tx loss of signal flag on host lane 2
        txlos_hostlane3              = BOOLEAN                          ; tx loss of signal flag on host lane 3
        txlos_hostlane4              = BOOLEAN                          ; tx loss of signal flag on host lane 4
        txlos_hostlane5              = BOOLEAN                          ; tx loss of signal flag on host lane 5
        txlos_hostlane6              = BOOLEAN                          ; tx loss of signal flag on host lane 6
        txlos_hostlane7              = BOOLEAN                          ; tx loss of signal flag on host lane 7
        txlos_hostlane8              = BOOLEAN                          ; tx loss of signal flag on host lane 8
        txcdrlol_hostlane1           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 1
        txcdrlol_hostlane2           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 2
        txcdrlol_hostlane3           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 3
        txcdrlol_hostlane4           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 4
        txcdrlol_hostlane5           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 5
        txcdrlol_hostlane6           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 6
        txcdrlol_hostlane7           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 7
        txcdrlol_hostlane8           = BOOLEAN                          ; tx clock and data recovery loss of lock on host lane 8
        rxlos                        = BOOLEAN                          ; rx loss of signal flag on media lane
        rxcdrlol                     = BOOLEAN                          ; rx clock and data recovery loss of lock on media lane
        config_state_hostlane1       = 1*255VCHAR                       ; configuration status for the data path of host line 1
        config_state_hostlane2       = 1*255VCHAR                       ; configuration status for the data path of host line 2
        config_state_hostlane3       = 1*255VCHAR                       ; configuration status for the data path of host line 3
        config_state_hostlane4       = 1*255VCHAR                       ; configuration status for the data path of host line 4
        config_state_hostlane5       = 1*255VCHAR                       ; configuration status for the data path of host line 5
        config_state_hostlane6       = 1*255VCHAR                       ; configuration status for the data path of host line 6
        config_state_hostlane7       = 1*255VCHAR                       ; configuration status for the data path of host line 7
        config_state_hostlane8       = 1*255VCHAR                       ; configuration status for the data path of host line 8
        dpinit_pending_hostlane1     = BOOLEAN                          ; data path configuration updated on host lane 1 
        dpinit_pending_hostlane2     = BOOLEAN                          ; data path configuration updated on host lane 2
        dpinit_pending_hostlane3     = BOOLEAN                          ; data path configuration updated on host lane 3
        dpinit_pending_hostlane4     = BOOLEAN                          ; data path configuration updated on host lane 4
        dpinit_pending_hostlane5     = BOOLEAN                          ; data path configuration updated on host lane 5
        dpinit_pending_hostlane6     = BOOLEAN                          ; data path configuration updated on host lane 6
        dpinit_pending_hostlane7     = BOOLEAN                          ; data path configuration updated on host lane 7
        dpinit_pending_hostlane8     = BOOLEAN                          ; data path configuration updated on host lane 8
        tuning_in_progress           = BOOLEAN                          ; tuning in progress status
        wavelength_unlock_status     = BOOLEAN                          ; laser unlocked status
        target_output_power_oor      = BOOLEAN                          ; target output power out of range flag
        fine_tuning_oor              = BOOLEAN                          ; fine tuning out of range flag
        tuning_not_accepted          = BOOLEAN                          ; tuning not accepted flag
        invalid_channel_num          = BOOLEAN                          ; invalid channel number flag
        tuning_complete              = BOOLEAN                          ; tuning complete flag
        temphighalarm_flag           = BOOLEAN                          ; temperature high alarm flag 
        temphighwarning_flag         = BOOLEAN                          ; temperature high warning flag
        templowalarm_flag            = BOOLEAN                          ; temperature low alarm flag
        templowwarning_flag          = BOOLEAN                          ; temperature low warning flag
        vcchighalarm_flag            = BOOLEAN                          ; vcc high alarm flag
        vcchighwarning_flag          = BOOLEAN                          ; vcc high warning flag
        vcclowalarm_flag             = BOOLEAN                          ; vcc low alarm flag
        vcclowwarning_flag           = BOOLEAN                          ; vcc low warning flag
        txpowerhighalarm_flag        = BOOLEAN                          ; tx power high alarm flag
        txpowerlowalarm_flag         = BOOLEAN                          ; tx power low alarm flag
        txpowerhighwarning_flag      = BOOLEAN                          ; tx power high warning flag
        txpowerlowwarning_flag       = BOOLEAN                          ; tx power low alarm flag
        rxpowerhighalarm_flag        = BOOLEAN                          ; rx power high alarm flag
        rxpowerlowalarm_flag         = BOOLEAN                          ; rx power low alarm flag
        rxpowerhighwarning_flag      = BOOLEAN                          ; rx power high warning flag
        rxpowerlowwarning_flag       = BOOLEAN                          ; rx power low warning flag
        txbiashighalarm_flag         = BOOLEAN                          ; tx bias high alarm flag
        txbiaslowalarm_flag          = BOOLEAN                          ; tx bias low alarm flag
        txbiashighwarning_flag       = BOOLEAN                          ; tx bias high warning flag
        txbiaslowwarning_flag        = BOOLEAN                          ; tx bias low warning flag
        lasertemphighalarm_flag      = BOOLEAN                          ; laser temperature high alarm flag
        lasertemplowalarm_flag       = BOOLEAN                          ; laser temperature low alarm flag
        lasertemphighwarning_flag    = BOOLEAN                          ; laser temperature high warning flag
        lasertemplowwarning_flag     = BOOLEAN                          ; laser temperature low warning flag
        prefecberhighalarm_flag      = BOOLEAN                          ; prefec ber high alarm flag
        prefecberlowalarm_flag       = BOOLEAN                          ; prefec ber low alarm flag
        prefecberhighwarning_flag    = BOOLEAN                          ; prefec ber high warning flag
        prefecberlowwarning_flag     = BOOLEAN                          ; prefec ber low warning flag
        postfecberhighalarm_flag     = BOOLEAN                          ; postfec ber high alarm flag
        postfecberlowalarm_flag      = BOOLEAN                          ; postfec ber low alarm flag
        postfecberhighwarning_flag   = BOOLEAN                          ; postfec ber high warning flag
        postfecberlowwarning_flag    = BOOLEAN                          ; postfec ber low warning flag
        biasxihighalarm_flag         = BOOLEAN                          ; bias xi high alarm flag
        biasxilowalarm_flag          = BOOLEAN                          ; bias xi low alarm flag
        biasxihighwarning_flag       = BOOLEAN                          ; bias xi high warning flag
        biasxilowwarning_flag        = BOOLEAN                          ; bias xi low warning flag
        biasxqhighalarm_flag         = BOOLEAN                          ; bias xq high alarm flag
        biasxqlowalarm_flag          = BOOLEAN                          ; bias xq low alarm flag
        biasxqhighwarning_flag       = BOOLEAN                          ; bias xq high warning flag
        biasxqlowwarning_flag        = BOOLEAN                          ; bias xq low warning flag
        biasxphighalarm_flag         = BOOLEAN                          ; bias xp high alarm flag
        biasxplowalarm_flag          = BOOLEAN                          ; bias xp low alarm flag
        biasxphighwarning_flag       = BOOLEAN                          ; bias xp high warning flag
        biasxplowwarning_flag        = BOOLEAN                          ; bias xp low warning flag
        biasyihighalarm_flag         = BOOLEAN                          ; bias yi high alarm flag
        biasyilowalarm_flag          = BOOLEAN                          ; bias yi low alarm flag
        biasyihighwarning_flag       = BOOLEAN                          ; bias yi high warning flag
        biasyilowwarning_flag        = BOOLEAN                          ; bias yi low warning flag
        biasyqhighalarm_flag         = BOOLEAN                          ; bias yq high alarm flag
        biasyqlowalarm_flag          = BOOLEAN                          ; bias yq low alarm flag
        biasyqhighwarning_flag       = BOOLEAN                          ; bias yq high warning flag
        biasyqlowwarning_flag        = BOOLEAN                          ; bias yq low warning flag
        biasyphighalarm_flag         = BOOLEAN                          ; bias yp high alarm flag
        biasyplowalarm_flag          = BOOLEAN                          ; bias yp low alarm flag
        biasyphighwarning_flag       = BOOLEAN                          ; bias yp high warning flag
        biasyplowwarning_flag        = BOOLEAN                          ; bias yp low warning flag
        cdshorthighalarm_flag        = BOOLEAN                          ; cd short high alarm flag
        cdshortlowalarm_flag         = BOOLEAN                          ; cd short low alarm flag
        cdshorthighwarning_flag      = BOOLEAN                          ; cd short high warning flag
        cdshortlowwarning_flag       = BOOLEAN                          ; cd short low warning flag
        cdlonghighalarm_flag         = BOOLEAN                          ; cd long high alarm flag
        cdlonglowalarm_flag          = BOOLEAN                          ; cd long low alarm flag
        cdlonghighwarning_flag       = BOOLEAN                          ; cd long high warning flag
        cdlonglowwarning_flag        = BOOLEAN                          ; cd long low warning flag
        dgdhighalarm_flag            = BOOLEAN                          ; dgd high alarm flag
        dgdlowalarm_flag             = BOOLEAN                          ; dgd low alarm flag
        dgdhighwarning_flag          = BOOLEAN                          ; dgd high warning flag
        dgdlowwarning_flag           = BOOLEAN                          ; dgd low warning flag
        sopmdhighalarm_flag          = BOOLEAN                          ; sopmd high alarm flag
        sopmdlowalarm_flag           = BOOLEAN                          ; sopmd low alarm flag
        sopmdhighwarning_flag        = BOOLEAN                          ; sopmd high warning flag
        sopmdlowwarning_flag         = BOOLEAN                          ; sopmd low warning flag
        pdlhighalarm_flag            = BOOLEAN                          ; pdl high alarm flag
        pdllowalarm_flag             = BOOLEAN                          ; pdl low alarm flag
        pdlhighwarning_flag          = BOOLEAN                          ; pdl high warning flag
        pdllowwarning_flag           = BOOLEAN                          ; pdl low warning flag
        osnrhighalarm_flag           = BOOLEAN                          ; osnr high alarm flag
        osnrlowalarm_flag            = BOOLEAN                          ; osnr low alarm flag
        osnrhighwarning_flag         = BOOLEAN                          ; osnr high warning flag
        osnrlowwarning_flag          = BOOLEAN                          ; osnr low warning flag
        esnrhighalarm_flag           = BOOLEAN                          ; esnr high alarm flag
        esnrlowalarm_flag            = BOOLEAN                          ; esnr low alarm flag
        esnrhighwarning_flag         = BOOLEAN                          ; esnr high warning flag
        esnrlowwarning_flag          = BOOLEAN                          ; esnr low warning flag
        cfohighalarm_flag            = BOOLEAN                          ; cfo high alarm flag
        cfolowalarm_flag             = BOOLEAN                          ; cfo low alarm flag
        cfohighwarning_flag          = BOOLEAN                          ; cfo high warning flag
        cfolowwarning_flag           = BOOLEAN                          ; cfo low warning flag
        txcurrpowerhighalarm_flag    = BOOLEAN                          ; txcurrpower high alarm flag
        txcurrpowerlowalarm_flag     = BOOLEAN                          ; txcurrpower low alarm flag
        txcurrpowerhighwarning_flag  = BOOLEAN                          ; txcurrpower high warning flag
        txcurrpowerlowwarning_flag   = BOOLEAN                          ; txcurrpower low warning flag
        rxtotpowerhighalarm_flag     = BOOLEAN                          ; rxtotpower high alarm flag
        rxtotpowerlowalarm_flag      = BOOLEAN                          ; rxtotpower low alarm flag
        rxtotpowerhighwarning_flag   = BOOLEAN                          ; rxtotpower high warning flag
        rxtotpowerlowwarning_flag    = BOOLEAN                          ; rxtotpower low warning flag
        rxsigpowerhighalarm_flag     = BOOLEAN                          ; rxsigpower high alarm flag
        rxsigpowerlowalarm_flag      = BOOLEAN                          ; rxsigpower low alarm flag
        rxsigpowerhighwarning_flag   = BOOLEAN                          ; rxsigpower high warning flag
        rxsigpowerlowwarning_flag    = BOOLEAN                          ; rxsigpower low warning flag
        ================================================================================
        """
        trans_status = super(CCmisApi,self).get_transceiver_status()
        trans_status['tuning_in_progress'] = self.get_tuning_in_progress()
        trans_status['wavelength_unlock_status'] = self.get_wavelength_unlocked()
        laser_tuning_summary = self.get_laser_tuning_summary()
        trans_status['target_output_power_oor'] = 'TargetOutputPowerOOR' in laser_tuning_summary
        trans_status['fine_tuning_oor'] = 'FineTuningOutOfRange' in laser_tuning_summary
        trans_status['tuning_not_accepted'] = 'TuningNotAccepted' in laser_tuning_summary
        trans_status['invalid_channel_num'] = 'InvalidChannel' in laser_tuning_summary
        trans_status['tuning_complete'] = 'TuningComplete' in laser_tuning_summary

        for vdm_key, trans_status_key_prefix in C_CMIS_DELTA_VDM_KEY_TO_DB_PREFIX_KEY_MAP.items():
            for i in range(5, 9):
                trans_status_key = trans_status_key_prefix + VDM_SUBTYPE_IDX_MAP[i]
                self._update_dict_if_vdm_key_exists(trans_status, trans_status_key, vdm_key, i)

        return trans_status

    def get_transceiver_pm(self):
        """
        Retrieves PM for this xcvr

        Returns:
            A dict containing the following keys/values :
        ========================================================================
        key                          = TRANSCEIVER_PM|ifname            ; information of PM on port
        ; field                      = value 
        prefec_ber_avg               = FLOAT                            ; prefec ber avg
        prefec_ber_min               = FLOAT                            ; prefec ber min
        prefec_ber_max               = FLOAT                            ; prefec ber max
        uncorr_frames_avg            = FLOAT                            ; uncorrected frames ratio avg
        uncorr_frames_min            = FLOAT                            ; uncorrected frames ratio min
        uncorr_frames_max            = FLOAT                            ; uncorrected frames ratio max
        cd_avg                       = FLOAT                            ; chromatic dispersion avg
        cd_min                       = FLOAT                            ; chromatic dispersion min
        cd_max                       = FLOAT                            ; chromatic dispersion max
        dgd_avg                      = FLOAT                            ; differential group delay avg
        dgd_min                      = FLOAT                            ; differential group delay min
        dgd_max                      = FLOAT                            ; differential group delay max
        sopmd_avg                    = FLOAT                            ; second order polarization mode dispersion avg
        sopmd_min                    = FLOAT                            ; second order polarization mode dispersion min
        sopmd_max                    = FLOAT                            ; second order polarization mode dispersion max
        pdl_avg                      = FLOAT                            ; polarization dependent loss avg
        pdl_min                      = FLOAT                            ; polarization dependent loss min
        pdl_max                      = FLOAT                            ; polarization dependent loss max
        osnr_avg                     = FLOAT                            ; optical signal to noise ratio avg
        osnr_min                     = FLOAT                            ; optical signal to noise ratio min
        osnr_max                     = FLOAT                            ; optical signal to noise ratio max
        esnr_avg                     = FLOAT                            ; electrical signal to noise ratio avg
        esnr_min                     = FLOAT                            ; electrical signal to noise ratio min
        esnr_max                     = FLOAT                            ; electrical signal to noise ratio max
        cfo_avg                      = FLOAT                            ; carrier frequency offset avg
        cfo_min                      = FLOAT                            ; carrier frequency offset min
        cfo_max                      = FLOAT                            ; carrier frequency offset max
        soproc_avg                   = FLOAT                            ; state of polarization rate of change avg
        soproc_min                   = FLOAT                            ; state of polarization rate of change min
        soproc_max                   = FLOAT                            ; state of polarization rate of change max
        tx_power_avg                 = FLOAT                            ; tx output power avg
        tx_power_min                 = FLOAT                            ; tx output power min
        tx_power_max                 = FLOAT                            ; tx output power max
        rx_tot_power_avg             = FLOAT                            ; rx total power avg
        rx_tot_power_min             = FLOAT                            ; rx total power min
        rx_tot_power_max             = FLOAT                            ; rx total power max
        rx_sig_power_avg             = FLOAT                            ; rx signal power avg
        rx_sig_power_min             = FLOAT                            ; rx signal power min
        rx_sig_power_max             = FLOAT                            ; rx signal power max
        ========================================================================
        """
        trans_pm = dict()
        PM_dict = self.get_pm_all()
        trans_pm['prefec_ber_avg'] = PM_dict['preFEC_BER_avg']
        trans_pm['prefec_ber_min'] = PM_dict['preFEC_BER_min']
        trans_pm['prefec_ber_max'] = PM_dict['preFEC_BER_max']
        trans_pm['uncorr_frames_avg'] = PM_dict['preFEC_uncorr_frame_ratio_avg']
        trans_pm['uncorr_frames_min'] = PM_dict['preFEC_uncorr_frame_ratio_min']
        trans_pm['uncorr_frames_max'] = PM_dict['preFEC_uncorr_frame_ratio_max']
        trans_pm['cd_avg'] = PM_dict['rx_cd_avg']
        trans_pm['cd_min'] = PM_dict['rx_cd_min']
        trans_pm['cd_max'] = PM_dict['rx_cd_max']
        trans_pm['dgd_avg'] = PM_dict['rx_dgd_avg']
        trans_pm['dgd_min'] = PM_dict['rx_dgd_min']
        trans_pm['dgd_max'] = PM_dict['rx_dgd_max']
        trans_pm['sopmd_avg'] = PM_dict['rx_sopmd_avg']
        trans_pm['sopmd_min'] = PM_dict['rx_sopmd_min']
        trans_pm['sopmd_max'] = PM_dict['rx_sopmd_max']
        trans_pm['pdl_avg'] = PM_dict['rx_pdl_avg']
        trans_pm['pdl_min'] = PM_dict['rx_pdl_min']
        trans_pm['pdl_max'] = PM_dict['rx_pdl_max']
        trans_pm['osnr_avg'] = PM_dict['rx_osnr_avg']
        trans_pm['osnr_min'] = PM_dict['rx_osnr_min']
        trans_pm['osnr_max'] = PM_dict['rx_osnr_max']
        trans_pm['esnr_avg'] = PM_dict['rx_esnr_avg']
        trans_pm['esnr_min'] = PM_dict['rx_esnr_min']
        trans_pm['esnr_max'] = PM_dict['rx_esnr_max']
        trans_pm['cfo_avg'] = PM_dict['rx_cfo_avg']
        trans_pm['cfo_min'] = PM_dict['rx_cfo_min']
        trans_pm['cfo_max'] = PM_dict['rx_cfo_max']
        trans_pm['evm_avg'] = PM_dict['rx_evm_avg']
        trans_pm['evm_min'] = PM_dict['rx_evm_min']
        trans_pm['evm_max'] = PM_dict['rx_evm_max']
        trans_pm['soproc_avg'] = PM_dict['rx_soproc_avg']
        trans_pm['soproc_min'] = PM_dict['rx_soproc_min']
        trans_pm['soproc_max'] = PM_dict['rx_soproc_max']
        trans_pm['tx_power_avg'] = PM_dict['tx_power_avg']
        trans_pm['tx_power_min'] = PM_dict['tx_power_min']
        trans_pm['tx_power_max'] = PM_dict['tx_power_max']
        trans_pm['rx_tot_power_avg'] = PM_dict['rx_power_avg']
        trans_pm['rx_tot_power_min'] = PM_dict['rx_power_min']
        trans_pm['rx_tot_power_max'] = PM_dict['rx_power_max']
        trans_pm['rx_sig_power_avg'] = PM_dict['rx_sigpwr_avg']
        trans_pm['rx_sig_power_min'] = PM_dict['rx_sigpwr_min']
        trans_pm['rx_sig_power_max'] = PM_dict['rx_sigpwr_max']
        return trans_pm
