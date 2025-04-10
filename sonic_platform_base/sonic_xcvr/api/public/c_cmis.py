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

    def get_transceiver_dom_real_value(self):
        """
        Retrieves DOM sensor values for this transceiver

        The returned dictionary contains floating-point values corresponding to various
        DOM sensor readings, as defined in the TRANSCEIVER_DOM_SENSOR table in STATE_DB.

        Returns:
            Dictionary
        """
        trans_dom = super(CCmisApi,self).get_transceiver_dom_real_value()

        trans_dom['laser_config_freq'] = self.get_laser_config_freq()
        trans_dom['laser_curr_freq'] = self.get_current_laser_freq()
        trans_dom['tx_config_power'] = self.get_tx_config_power()
        return trans_dom

    def get_transceiver_status(self):
        """
        Retrieves the current status of the transceiver module.

        Accesses non-latched registers to gather information about the module's state,
        fault causes, and datapath-level statuses, including TX and RX statuses.

        Returns:
            dict: A dictionary containing boolean values for various status fields, as defined in
                the TRANSCEIVER_STATUS table in STATE_DB.
        If there is an issue with reading the xcvr, None should be returned.
        """
        trans_status = super(CCmisApi,self).get_transceiver_status()
        trans_status['tuning_in_progress'] = self.get_tuning_in_progress()
        trans_status['wavelength_unlock_status'] = self.get_wavelength_unlocked()

        return trans_status

    def get_transceiver_status_flags(self):
        """
        Retrieves the current flag status of the transceiver module.

        Accesses latched registers to gather information about both
        module-level and datapath-level states (including TX/RX related flags).

        Returns:
            dict: A dictionary containing boolean values for various flags, as defined in
                the TRANSCEIVER_STATUS_FLAGS table in STATE_DB.
        """
        status_flags_dict = super().get_transceiver_status_flags()

        laser_tuning_summary = self.get_laser_tuning_summary()
        status_flags_dict.update({
            'target_output_power_oor': 'TargetOutputPowerOOR' in laser_tuning_summary,
            'fine_tuning_oor': 'FineTuningOutOfRange' in laser_tuning_summary,
            'tuning_not_accepted': 'TuningNotAccepted' in laser_tuning_summary,
            'invalid_channel_num': 'InvalidChannel' in laser_tuning_summary,
            'tuning_complete': 'TuningComplete' in laser_tuning_summary
        })

        return status_flags_dict

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
