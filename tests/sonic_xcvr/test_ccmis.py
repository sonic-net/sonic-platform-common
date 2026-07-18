from mock import MagicMock
from mock import patch
import pytest
from sonic_platform_base.sonic_xcvr.api.public.c_cmis import CCmisApi, C_CMIS_XCVR_INFO_DEFAULT_DICT
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.c_cmis import CCmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.fields import consts


# Page 42h "Impl" advertisement bits for the *newly added* Page 35h monitors.
# The original Page 34h/35h fields are always read (no advertisement gating).
_PM_IMPL_CONSTS = [
    consts.RX_CLOCK_REC_IMPL, consts.RX_LG_SOPMD_IMPL, consts.RX_SNR_MARGIN_IMPL,
    consts.RX_QFACTOR_IMPL, consts.RX_QMARGIN_IMPL,
]

# Page 3Ah host-interface counters are ungated: always present in get_pm_all().
_PAGE_3AH_EXPECTED = {
    'tx_bits_pm': 2000000, 'tx_bits_subint_pm': 20000, 'tx_corr_bits_pm': 2000,
    'tx_min_corr_bits_subint_pm': 16, 'tx_max_corr_bits_subint_pm': 24,
    'tx_frames_pm': 20000, 'tx_frames_subint_pm': 200, 'tx_frames_uncorr_err_pm': 0,
    'tx_min_frames_uncorr_err_subint_pm': 0, 'tx_max_frames_uncorr_err_subint_pm': 0,
    'tx_corrected_frames_pm': 5, 'tx_corrected_frames_subint_pm': 1,
}

# Raw Page 34h RX FEC counters: always present (ungated, mirror the ratio reads).
_PAGE_34_RAW_EXPECTED = {
    'rx_bits_pm': 1000000, 'rx_bits_subint_pm': 10000, 'rx_corr_bits_pm': 1000,
    'rx_min_corr_bits_subint_pm': 8, 'rx_max_corr_bits_subint_pm': 12,
    'rx_frames_pm': 10000, 'rx_frames_subint_pm': 100, 'rx_frames_uncorr_err_pm': 0,
    'rx_min_frames_uncorr_err_subint_pm': 0, 'rx_max_frames_uncorr_err_subint_pm': 0,
}

# Original Page 34h/35h keys: always emitted by get_pm_all() (no advertisement gating).
_PAGE_34_35_OLD_EXPECTED = {
    'preFEC_BER_avg': 0.001, 'preFEC_BER_min': 0.0008, 'preFEC_BER_max': 0.0012,
    'preFEC_uncorr_frame_ratio_avg': 0, 'preFEC_uncorr_frame_ratio_min': 0, 'preFEC_uncorr_frame_ratio_max': 0,
    'rx_cd_avg': 1400, 'rx_cd_min': 1300, 'rx_cd_max': 1500,
    'rx_dgd_avg': 7.0, 'rx_dgd_min': 5.5, 'rx_dgd_max': 9.2,
    'rx_sopmd_avg': 40, 'rx_sopmd_min': 20, 'rx_sopmd_max': 60,
    'rx_pdl_avg': 1.0, 'rx_pdl_min': 0.8, 'rx_pdl_max': 1.2,
    'rx_osnr_avg': 28, 'rx_osnr_min': 26, 'rx_osnr_max': 30,
    'rx_esnr_avg': 17, 'rx_esnr_min': 15, 'rx_esnr_max': 18,
    'rx_cfo_avg': 200, 'rx_cfo_min': 150, 'rx_cfo_max': 250,
    'rx_evm_avg': 15, 'rx_evm_min': 13, 'rx_evm_max': 18,
    'tx_power_avg': -10, 'tx_power_min': -9.5, 'tx_power_max': -10.5,
    'rx_power_avg': -8, 'rx_power_min': -7, 'rx_power_max': -9,
    'rx_sigpwr_avg': -8, 'rx_sigpwr_min': -7, 'rx_sigpwr_max': -9,
    'rx_soproc_avg': 5, 'rx_soproc_min': 3, 'rx_soproc_max': 8,
    'rx_mer_avg': 0, 'rx_mer_min': 0, 'rx_mer_max': 0,
}

# Newly added Page 35h keys: only emitted when advertised implemented in Page 42h.
_PAGE_35_NEW_EXPECTED = {
    'rx_clockrec_avg': 1.5, 'rx_clockrec_min': 1.0, 'rx_clockrec_max': 2.0,
    'rx_lg_sopmd_avg': 41, 'rx_lg_sopmd_min': 21, 'rx_lg_sopmd_max': 61,
    'rx_snr_margin_avg': 3.0, 'rx_snr_margin_min': 2.0, 'rx_snr_margin_max': 4.0,
    'rx_qfactor_avg': 10.0, 'rx_qfactor_min': 9.0, 'rx_qfactor_max': 11.0,
    'rx_qmargin_avg': 1.0, 'rx_qmargin_min': 0.5, 'rx_qmargin_max': 1.5,
}


def _pm_all_read_map():
    """Const -> mocked xcvr_eeprom.read() return value, with everything implemented."""
    values = {
        # Page 34h - media FEC PM raw counters
        consts.RX_BITS_PM: 1000000, consts.RX_BITS_SUB_INTERVAL_PM: 10000,
        consts.RX_CORR_BITS_PM: 1000, consts.RX_MIN_CORR_BITS_SUB_INTERVAL_PM: 8,
        consts.RX_MAX_CORR_BITS_SUB_INTERVAL_PM: 12,
        consts.RX_FRAMES_PM: 10000, consts.RX_FRAMES_SUB_INTERVAL_PM: 100,
        consts.RX_FRAMES_UNCORR_ERR_PM: 0, consts.RX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM: 0,
        consts.RX_MAX_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM: 0,
        # Page 35h - media lane link PM
        consts.RX_AVG_CD_PM: 1400, consts.RX_MIN_CD_PM: 1300, consts.RX_MAX_CD_PM: 1500,
        consts.RX_AVG_DGD_PM: 7.0, consts.RX_MIN_DGD_PM: 5.5, consts.RX_MAX_DGD_PM: 9.2,
        consts.RX_AVG_SOPMD_PM: 40, consts.RX_MIN_SOPMD_PM: 20, consts.RX_MAX_SOPMD_PM: 60,
        consts.RX_AVG_PDL_PM: 1.0, consts.RX_MIN_PDL_PM: 0.8, consts.RX_MAX_PDL_PM: 1.2,
        consts.RX_AVG_OSNR_PM: 28, consts.RX_MIN_OSNR_PM: 26, consts.RX_MAX_OSNR_PM: 30,
        consts.RX_AVG_ESNR_PM: 17, consts.RX_MIN_ESNR_PM: 15, consts.RX_MAX_ESNR_PM: 18,
        consts.RX_AVG_CFO_PM: 200, consts.RX_MIN_CFO_PM: 150, consts.RX_MAX_CFO_PM: 250,
        consts.RX_AVG_EVM_PM: 15, consts.RX_MIN_EVM_PM: 13, consts.RX_MAX_EVM_PM: 18,
        consts.TX_AVG_POWER_PM: -10, consts.TX_MIN_POWER_PM: -9.5, consts.TX_MAX_POWER_PM: -10.5,
        consts.RX_AVG_POWER_PM: -8, consts.RX_MIN_POWER_PM: -7, consts.RX_MAX_POWER_PM: -9,
        consts.RX_AVG_SIG_POWER_PM: -8, consts.RX_MIN_SIG_POWER_PM: -7, consts.RX_MAX_SIG_POWER_PM: -9,
        consts.RX_AVG_SOPROC_PM: 5, consts.RX_MIN_SOPROC_PM: 3, consts.RX_MAX_SOPROC_PM: 8,
        consts.RX_AVG_MER_PM: 0, consts.RX_MIN_MER_PM: 0, consts.RX_MAX_MER_PM: 0,
        consts.RX_AVG_CLOCK_REC_PM: 1.5, consts.RX_MIN_CLOCK_REC_PM: 1.0, consts.RX_MAX_CLOCK_REC_PM: 2.0,
        consts.RX_AVG_LG_SOPMD_PM: 41, consts.RX_MIN_LG_SOPMD_PM: 21, consts.RX_MAX_LG_SOPMD_PM: 61,
        consts.RX_AVG_SNR_MARGIN_PM: 3.0, consts.RX_MIN_SNR_MARGIN_PM: 2.0, consts.RX_MAX_SNR_MARGIN_PM: 4.0,
        consts.RX_AVG_QFACTOR_PM: 10.0, consts.RX_MIN_QFACTOR_PM: 9.0, consts.RX_MAX_PM_QFACTOR: 11.0,
        consts.RX_AVG_QMARGIN_PM: 1.0, consts.RX_MIN_QMARGIN_PM: 0.5, consts.RX_MAX_QMARGIN_PM: 1.5,
        # Page 3Ah - data path host interface PM
        consts.TX_BITS_PM: 2000000, consts.TX_BITS_SUB_INTERVAL_PM: 20000, consts.TX_CORR_BITS_PM: 2000,
        consts.TX_MIN_CORR_BITS_SUB_INTERVAL_PM: 16, consts.TX_MAX_CORR_BITS_SUB_INTERVAL_PM: 24,
        consts.TX_FRAMES_PM: 20000, consts.TX_FRAMES_SUB_INTERVAL_PM: 200, consts.TX_FRAMES_UNCORR_ERR_PM: 0,
        consts.TX_MIN_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM: 0, consts.TX_MAX_FRAMES_UNCORR_ERR_SUB_INTERVAL_PM: 0,
        consts.TX_CORRECTED_FRAMES_PM: 5, consts.TX_CORRECTED_FRAMES_SUB_INTERVAL_PM: 1,
    }
    for impl in _PM_IMPL_CONSTS:
        values[impl] = True
    return values


class TestCCmis(object):
    codes = CmisCodes
    mem_map = CCmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)

    api = CCmisApi(eeprom, init_cdb_fw_handler=False)

    @pytest.mark.parametrize("mock_response, expected", [
        (8, 150),
        (7, 75),
        (6, 33),
        (5, 100),
        (4, 50),
        (3, 25),
        (2, 12.5),
        (1, 6.25),
        (0, 3.125),
        (None, None)
    ])
    def test_get_freq_grid(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_freq_grid()
        assert result == expected


    @pytest.mark.parametrize("mock_response1, mock_response2, expected", [
        (75, 12, 193400),
        (75, -30, 192350),
        (100, 10, 194100),
    ])
    def test_get_laser_config_freq(self, mock_response1, mock_response2, expected):
        self.api.get_freq_grid = MagicMock()
        self.api.get_freq_grid.return_value = mock_response1
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response2
        result = self.api.get_laser_config_freq()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (193100, 193100)
    ])
    def test_get_current_laser_freq(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_current_laser_freq()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, False)
    ])
    def test_get_tuning_in_progress(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_tuning_in_progress()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, False)
    ])
    def test_get_wavelength_unlocked(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_wavelength_unlocked()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (1, ['TuningComplete']),
        (62, ['TargetOutputPowerOOR', 'FineTuningOutOfRange', 'TuningNotAccepted',
              'InvalidChannel', 'WavelengthUnlocked']),
    ])
    def test_get_laser_tuning_summary(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_laser_tuning_summary()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        ([190, -72, 120], (190, -72, 120, 191300, 196100))
    ])
    def test_get_supported_freq_config(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_supported_freq_config()
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response",[
        ((193100,75), (0xff, -72, 120, 191300, 196100)),
        ((195950,100), (0xff, -72, 120, 191300, 196100)),
    ])
    def test_set_laser_freq(self, input_param, mock_response):
        self.api.is_flat_memory = MagicMock()
        self.api.is_flat_memory.return_value = False
        self.api.get_lpmode_support = MagicMock()
        self.api.get_lpmode_support.return_value = False
        self.api.get_supported_freq_config = MagicMock()
        self.api.get_supported_freq_config.return_value = mock_response
        self.api.set_laser_freq(input_param[0], input_param[1])

    @pytest.mark.parametrize("input_param, mock_response",[
        (-10, (-14, -9)),
        (-8, (-12, -8)),
    ])
    def test_set_tx_power(self, input_param, mock_response):
        self.api.get_supported_power_config = MagicMock()
        self.api.get_supported_power_config.return_value = mock_response
        self.api.set_tx_power(input_param)

    def test_get_pm_all_all_implemented(self):
        values = _pm_all_read_map()
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda c: values.get(c))
        # Clear any read_only_cached_api_return caches so each test's mock is honored
        # (the shared api instance persists across tests).
        for attr in [a for a in vars(self.api) if a.endswith('_cache')]:
            setattr(self.api, attr, {})
        with patch.object(self.api, 'is_flat_memory', return_value=False), \
             patch.object(self.api, 'is_coherent_module', return_value=True):
            result = self.api.get_pm_all()
        expected = dict(_PAGE_34_35_OLD_EXPECTED)
        expected.update(_PAGE_34_RAW_EXPECTED)
        expected.update(_PAGE_35_NEW_EXPECTED)
        expected.update(_PAGE_3AH_EXPECTED)
        assert result == expected

    def test_get_pm_all_unimplemented_new_fields_omitted(self):
        values = _pm_all_read_map()
        # Advertise two of the newly added Page 35h monitors as NOT implemented.
        values[consts.RX_QFACTOR_IMPL] = False
        values[consts.RX_CLOCK_REC_IMPL] = False
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda c: values.get(c))
        # Clear any read_only_cached_api_return caches so each test's mock is honored
        # (the shared api instance persists across tests).
        for attr in [a for a in vars(self.api) if a.endswith('_cache')]:
            setattr(self.api, attr, {})
        with patch.object(self.api, 'is_flat_memory', return_value=False), \
             patch.object(self.api, 'is_coherent_module', return_value=True):
            result = self.api.get_pm_all()
        # Unimplemented new-field trios are omitted entirely.
        for key in ('rx_qfactor_avg', 'rx_qfactor_min', 'rx_qfactor_max',
                    'rx_clockrec_avg', 'rx_clockrec_min', 'rx_clockrec_max'):
            assert key not in result
        # Other implemented new fields carry their values.
        assert result['rx_qmargin_avg'] == 1.0
        assert result['rx_snr_margin_avg'] == 3.0
        # Original Page 34h/35h fields are always present (no advertisement gating).
        for key, val in _PAGE_34_35_OLD_EXPECTED.items():
            assert result[key] == val
        # Raw Page 34h counters are always present too.
        for key, val in _PAGE_34_RAW_EXPECTED.items():
            assert result[key] == val
        # Page 3Ah counters are always present regardless of advertisement.
        assert result['tx_bits_pm'] == 2000000

    def test_get_pm_all_flat_memory_keeps_legacy_fields(self):
        values = _pm_all_read_map()
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda c: values.get(c))
        # Clear any read_only_cached_api_return caches so each test's mock is honored
        # (the shared api instance persists across tests).
        for attr in [a for a in vars(self.api) if a.endswith('_cache')]:
            setattr(self.api, attr, {})
        with patch.object(self.api, 'is_flat_memory', return_value=True):
            result = self.api.get_pm_all()
        # Flat-memory omits every advertisement-gated new Page 35h field...
        for key in _PAGE_35_NEW_EXPECTED:
            assert key not in result
        # ...while the original Page 34h/35h fields and Page 3Ah counters remain.
        expected = dict(_PAGE_34_35_OLD_EXPECTED)
        expected.update(_PAGE_34_RAW_EXPECTED)
        expected.update(_PAGE_3AH_EXPECTED)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            (
                {   # EEPROM DATA
                    'type': 'QSFP-DD Double Density 8X Pluggable Transceiver',
                    'type_abbrv_name': 'QSFP-DD',
                    'model': 'ABCD',
                    'encoding': 'N/A',
                    'ext_identifier': 'Power Class 8 (20.0W Max)',
                    'ext_rateselect_compliance': 'N/A',
                    'cable_type': 'Length Cable Assembly(m)',
                    'cable_length': 0.0,
                    'nominal_bit_rate': 'N/A',
                    'specification_compliance': 'sm_media_interface',
                    'application_advertisement': 'N/A',
                    'media_lane_count': 1,
                    'vendor_rev': '0.0',
                    'vendor_oui': 'xx-xx-xx',
                    'manufacturer': 'VENDOR_NAME',
                    'media_interface_technology': '1550 nm DFB',
                    'serial': '00000000',
                    'host_lane_count': 8,
                    **{f'active_apsel_hostlane{i}': 1 for i in range(1, 9)},
                    'hardware_rev': '0.0',
                    'cmis_rev': '5.0',
                    'connector': 'LC',
                    'vendor_date': '21010100',
                    'vdm_supported': True,
                },
                (-20, 0),
                (0xff, -72, 120, 191300, 196100)
            ),
            {   # Expected Result
                'type': 'QSFP-DD Double Density 8X Pluggable Transceiver',
                'type_abbrv_name': 'QSFP-DD',
                'model': 'ABCD',
                'encoding': 'N/A',
                'ext_identifier': 'Power Class 8 (20.0W Max)',
                'ext_rateselect_compliance': 'N/A',
                'cable_type': 'Length Cable Assembly(m)',
                'cable_length': 0.0,
                'nominal_bit_rate': 'N/A',
                'specification_compliance': 'sm_media_interface',
                'application_advertisement': 'N/A',
                'media_lane_count': 1,
                'vendor_rev': '0.0',
                'vendor_oui': 'xx-xx-xx',
                'manufacturer': 'VENDOR_NAME',
                'media_interface_technology': '1550 nm DFB',
                'serial': '00000000',
                'host_lane_count': 8,
                **{f'active_apsel_hostlane{i}': 1 for i in range(1, 9)},
                'hardware_rev': '0.0',
                'cmis_rev': '5.0',
                'connector': 'LC',
                'vendor_date': '21010100',
                'vdm_supported': True,
                'supported_min_laser_freq': 191300,
                'supported_max_laser_freq': 196100,
                'supported_max_tx_power': 0,
                'supported_min_tx_power': -20,
            }
        )
    ])
    @patch("sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info")
    def test_get_transceiver_info(self, get_transceiver_info_func, mock_response, expected):
        # Mock the base class method to return initial transceiver data
        get_transceiver_info_func.return_value = mock_response[0]

        # Mock the power and frequency configurations
        self.api.get_supported_power_config = MagicMock(return_value = mock_response[1])
        self.api.get_supported_freq_config = MagicMock(return_value = mock_response[2])

        # Call function under test
        result = self.api.get_transceiver_info()
        assert result == expected

        # Test result is same as default dictionary length
        assert len(C_CMIS_XCVR_INFO_DEFAULT_DICT) == len(result)


    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                {
                    'temperature': 50,
                    'voltage': 3.3,
                    'txpower': 0.1,
                    'rxpower': 0.09,
                    'txbias': 70,
                },
                193100, 193100, -10
            ],
            {
                'temperature': 50,
                'voltage': 3.3,
                'txpower': 0.1,
                'rxpower': 0.09,
                'txbias': 70,
                'laser_config_freq': 193100,
                'laser_curr_freq': 193100,
                'tx_config_power': -10
            }
        )
    ])
    @patch("sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_real_value")
    def test_get_transceiver_dom_real_value(self, get_transceiver_dom_real_value_func, mock_response, expected):
        get_transceiver_dom_real_value_func.return_value = mock_response[0]
        self.api.get_laser_config_freq = MagicMock()
        self.api.get_laser_config_freq.return_value = mock_response[1]
        self.api.get_current_laser_freq = MagicMock()
        self.api.get_current_laser_freq.return_value = mock_response[2]
        self.api.get_tx_config_power = MagicMock()
        self.api.get_tx_config_power.return_value = mock_response[3]
        result = self.api.get_transceiver_dom_real_value()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                {
                    'temphighalarm': 80, 'templowalarm': 0, 'temphighwarning': 75, 'templowwarning': 10,
                    'vcchighalarm': 3.5, 'vcclowalarm': 3.1, 'vcchighwarning': 3.45, 'vcclowwarning': 3.15,
                    'txpowerhighalarm': 1.0, 'txpowerlowalarm': 0.01, 'txpowerhighwarning': 0.7, 'txpowerlowwarning': 0.02,
                    'rxpowerhighalarm': 2.0, 'rxpowerlowalarm': 0.01, 'rxpowerhighwarning': 1.0, 'rxpowerlowwarning': 0.02,
                    'txbiashighalarm': 90, 'txbiaslowalarm': 10, 'txbiashighwarning': 80, 'txbiaslowwarning': 20
                },
            ],
            {
                'temphighalarm': 80, 'templowalarm': 0, 'temphighwarning': 75, 'templowwarning': 10,
                'vcchighalarm': 3.5, 'vcclowalarm': 3.1, 'vcchighwarning': 3.45, 'vcclowwarning': 3.15,
                'txpowerhighalarm': 1.0, 'txpowerlowalarm': 0.01, 'txpowerhighwarning': 0.7, 'txpowerlowwarning': 0.02,
                'rxpowerhighalarm': 2.0, 'rxpowerlowalarm': 0.01, 'rxpowerhighwarning': 1.0, 'rxpowerlowwarning': 0.02,
                'txbiashighalarm': 90, 'txbiaslowalarm': 10, 'txbiashighwarning': 80, 'txbiaslowwarning': 20,
            }
        )
    ])
    @patch("sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_threshold_info")
    def test_get_transceiver_threshold_info(self, get_transceiver_threshold_info_func, mock_response, expected):
        get_transceiver_threshold_info_func.return_value = mock_response[0]
        result = self.api.get_transceiver_threshold_info()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                {
                    'module_state': 'ModuleReady',
                    'module_fault_cause': 'No Fault detected',
                    'datapath_firmware_fault': False,
                    'module_firmware_fault': False,
                    'module_state_changed': True,
                    'datapath_hostlane1': 'DataPathActivated',
                    'datapath_hostlane2': 'DataPathActivated',
                    'datapath_hostlane3': 'DataPathActivated',
                    'datapath_hostlane4': 'DataPathActivated',
                    'datapath_hostlane5': 'DataPathActivated',
                    'datapath_hostlane6': 'DataPathActivated',
                    'datapath_hostlane7': 'DataPathActivated',
                    'datapath_hostlane8': 'DataPathActivated',
                    'txoutput_status': True,
                    'rxoutput_status_hostlane1': True,
                    'rxoutput_status_hostlane2': True,
                    'rxoutput_status_hostlane3': True,
                    'rxoutput_status_hostlane4': True,
                    'rxoutput_status_hostlane5': True,
                    'rxoutput_status_hostlane6': True,
                    'rxoutput_status_hostlane7': True,
                    'rxoutput_status_hostlane8': True,
                    'config_state_hostlane1': 'ConfigSuccess',
                    'config_state_hostlane2': 'ConfigSuccess',
                    'config_state_hostlane3': 'ConfigSuccess',
                    'config_state_hostlane4': 'ConfigSuccess',
                    'config_state_hostlane5': 'ConfigSuccess',
                    'config_state_hostlane6': 'ConfigSuccess',
                    'config_state_hostlane7': 'ConfigSuccess',
                    'config_state_hostlane8': 'ConfigSuccess',
                    'dpinit_pending_hostlane1': False,
                    'dpinit_pending_hostlane2': False,
                    'dpinit_pending_hostlane3': False,
                    'dpinit_pending_hostlane4': False,
                    'dpinit_pending_hostlane5': False,
                    'dpinit_pending_hostlane6': False,
                    'dpinit_pending_hostlane7': False,
                    'dpinit_pending_hostlane8': False,
                },
                False, False,
            ],
            {
                'module_state': 'ModuleReady',
                'module_fault_cause': 'No Fault detected',
                'datapath_firmware_fault': False,
                'module_firmware_fault': False,
                'module_state_changed': True,
                'datapath_hostlane1': 'DataPathActivated',
                'datapath_hostlane2': 'DataPathActivated',
                'datapath_hostlane3': 'DataPathActivated',
                'datapath_hostlane4': 'DataPathActivated',
                'datapath_hostlane5': 'DataPathActivated',
                'datapath_hostlane6': 'DataPathActivated',
                'datapath_hostlane7': 'DataPathActivated',
                'datapath_hostlane8': 'DataPathActivated',
                'txoutput_status': True,
                'rxoutput_status_hostlane1': True,
                'rxoutput_status_hostlane2': True,
                'rxoutput_status_hostlane3': True,
                'rxoutput_status_hostlane4': True,
                'rxoutput_status_hostlane5': True,
                'rxoutput_status_hostlane6': True,
                'rxoutput_status_hostlane7': True,
                'rxoutput_status_hostlane8': True,
                'config_state_hostlane1': 'ConfigSuccess',
                'config_state_hostlane2': 'ConfigSuccess',
                'config_state_hostlane3': 'ConfigSuccess',
                'config_state_hostlane4': 'ConfigSuccess',
                'config_state_hostlane5': 'ConfigSuccess',
                'config_state_hostlane6': 'ConfigSuccess',
                'config_state_hostlane7': 'ConfigSuccess',
                'config_state_hostlane8': 'ConfigSuccess',
                'dpinit_pending_hostlane1': False,
                'dpinit_pending_hostlane2': False,
                'dpinit_pending_hostlane3': False,
                'dpinit_pending_hostlane4': False,
                'dpinit_pending_hostlane5': False,
                'dpinit_pending_hostlane6': False,
                'dpinit_pending_hostlane7': False,
                'dpinit_pending_hostlane8': False,
                'tuning_in_progress': False,
                'wavelength_unlock_status': False,
            }
        )
    ])
    @patch("sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_status")
    def test_get_transceiver_status(self, get_transceiver_status_func, mock_response, expected):
        get_transceiver_status_func.return_value = dict(mock_response[0])
        self.api.get_tuning_in_progress = MagicMock()
        self.api.get_tuning_in_progress.return_value = mock_response[1]
        self.api.get_wavelength_unlocked = MagicMock()
        self.api.get_wavelength_unlocked.return_value = mock_response[2]
        result = self.api.get_transceiver_status()
        assert result == expected

    @pytest.mark.parametrize(
        "module_faults, tx_fault, tx_los, tx_cdr_lol, tx_eq_fault, rx_los, rx_cdr_lol, laser_tuning_summary, expected_result",
        [
            # Test case 1: All flags present for lanes 1 to 8
            (
                (True, False, True),
                [True, False, True, False, True, False, True, False],
                [False, True, False, True, False, True, False, True],
                [True, False, True, False, True, False, True, False],
                [False, True, False, True, False, True, False, True],
                [True, False, True, False, True, False, True, False],
                [False, True, False, True, False, True, False, True],
                ['TargetOutputPowerOOR', 'FineTuningOutOfRange', 'TuningNotAccepted', 'InvalidChannel', 'TuningComplete'],
                {
                    'datapath_firmware_fault': True,
                    'module_firmware_fault': False,
                    'module_state_changed': True,
                    'tx1fault': True,
                    'tx2fault': False,
                    'tx3fault': True,
                    'tx4fault': False,
                    'tx5fault': True,
                    'tx6fault': False,
                    'tx7fault': True,
                    'tx8fault': False,
                    'rx1los': True,
                    'rx2los': False,
                    'rx3los': True,
                    'rx4los': False,
                    'rx5los': True,
                    'rx6los': False,
                    'rx7los': True,
                    'rx8los': False,
                    'tx1los_hostlane': False,
                    'tx2los_hostlane': True,
                    'tx3los_hostlane': False,
                    'tx4los_hostlane': True,
                    'tx5los_hostlane': False,
                    'tx6los_hostlane': True,
                    'tx7los_hostlane': False,
                    'tx8los_hostlane': True,
                    'tx1cdrlol_hostlane': True,
                    'tx2cdrlol_hostlane': False,
                    'tx3cdrlol_hostlane': True,
                    'tx4cdrlol_hostlane': False,
                    'tx5cdrlol_hostlane': True,
                    'tx6cdrlol_hostlane': False,
                    'tx7cdrlol_hostlane': True,
                    'tx8cdrlol_hostlane': False,
                    'tx1_eq_fault': False,
                    'tx2_eq_fault': True,
                    'tx3_eq_fault': False,
                    'tx4_eq_fault': True,
                    'tx5_eq_fault': False,
                    'tx6_eq_fault': True,
                    'tx7_eq_fault': False,
                    'tx8_eq_fault': True,
                    'rx1cdrlol': False,
                    'rx2cdrlol': True,
                    'rx3cdrlol': False,
                    'rx4cdrlol': True,
                    'rx5cdrlol': False,
                    'rx6cdrlol': True,
                    'rx7cdrlol': False,
                    'rx8cdrlol': True,
                    'target_output_power_oor': True,
                    'fine_tuning_oor': True,
                    'tuning_not_accepted': True,
                    'invalid_channel_num': True,
                    'tuning_complete': True,
                }
            ),
        ]
    )
    def test_get_transceiver_status_flags(self, module_faults, tx_fault, tx_los, tx_cdr_lol, tx_eq_fault, rx_los, rx_cdr_lol, laser_tuning_summary, expected_result):
        self.api.get_module_firmware_fault_state_changed = MagicMock(return_value=module_faults)
        self.api.get_tx_fault = MagicMock(return_value=tx_fault)
        self.api.get_tx_los = MagicMock(return_value=tx_los)
        self.api.get_tx_cdr_lol = MagicMock(return_value=tx_cdr_lol)
        self.api.get_rx_los = MagicMock(return_value=rx_los)
        self.api.get_rx_cdr_lol = MagicMock(return_value=rx_cdr_lol)
        self.api.get_laser_tuning_summary = MagicMock(return_value=laser_tuning_summary)
        with patch.object(self.api, 'get_tx_adaptive_eq_fail_flag', return_value=tx_eq_fault), \
             patch.object(self.api, 'is_flat_memory', return_value=False):
            result = self.api.get_transceiver_status_flags()
            assert result == expected_result

    @pytest.mark.parametrize("mock_response, expected", [
        (
            {
                **_PAGE_34_35_OLD_EXPECTED,
                **_PAGE_34_RAW_EXPECTED,
                **_PAGE_35_NEW_EXPECTED,
                **_PAGE_3AH_EXPECTED,
            },
            {
                'prefec_ber_avg': 0.001, 'prefec_ber_min': 0.0008, 'prefec_ber_max': 0.0012,
                'uncorr_frames_avg': 0, 'uncorr_frames_min': 0, 'uncorr_frames_max': 0,
                'cd_avg': 1400, 'cd_min': 1300, 'cd_max': 1500,
                'dgd_avg': 7.0, 'dgd_min': 5.5, 'dgd_max': 9.2,
                'sopmd_avg': 40, 'sopmd_min': 20, 'sopmd_max': 60,
                'pdl_avg': 1.0, 'pdl_min': 0.8, 'pdl_max': 1.2,
                'osnr_avg': 28, 'osnr_min': 26, 'osnr_max': 30,
                'esnr_avg': 17, 'esnr_min': 15, 'esnr_max': 18,
                'cfo_avg': 200, 'cfo_min': 150, 'cfo_max': 250,
                'evm_avg': 15, 'evm_min': 13, 'evm_max': 18,
                'tx_power_avg': -10, 'tx_power_min': -9.5, 'tx_power_max': -10.5,
                'rx_tot_power_avg': -8, 'rx_tot_power_min': -7, 'rx_tot_power_max': -9,
                'rx_sig_power_avg': -8, 'rx_sig_power_min': -7, 'rx_sig_power_max': -9,
                'soproc_avg': 5, 'soproc_min': 3, 'soproc_max': 8,
                'clockrec_avg': 1.5, 'clockrec_min': 1.0, 'clockrec_max': 2.0,
                'lg_sopmd_avg': 41, 'lg_sopmd_min': 21, 'lg_sopmd_max': 61,
                'snr_margin_avg': 3.0, 'snr_margin_min': 2.0, 'snr_margin_max': 4.0,
                'qfactor_avg': 10.0, 'qfactor_min': 9.0, 'qfactor_max': 11.0,
                'qmargin_avg': 1.0, 'qmargin_min': 0.5, 'qmargin_max': 1.5,
                **_PAGE_3AH_EXPECTED,
                **_PAGE_34_RAW_EXPECTED,
            }
        )
    ])
    def test_get_transceiver_pm(self, mock_response, expected):
        self.api.get_pm_all = MagicMock()
        self.api.get_pm_all.return_value = mock_response
        result = self.api.get_transceiver_pm()
        assert result == expected

    def test_get_transceiver_pm_unimplemented_new_fields_are_none(self):
        # get_pm_all() omits unimplemented *new* Page 35h keys; get_transceiver_pm()
        # must not KeyError and should surface them as None. The original Page
        # 34h/35h fields and Page 3Ah counters carry their values.
        pm = dict(_PAGE_34_35_OLD_EXPECTED)
        pm.update(_PAGE_34_RAW_EXPECTED)
        pm.update(_PAGE_3AH_EXPECTED)
        self.api.get_pm_all = MagicMock(return_value=pm)
        result = self.api.get_transceiver_pm()
        # Omitted new fields surface as None.
        assert result['qmargin_max'] is None
        assert result['clockrec_avg'] is None
        assert result['snr_margin_min'] is None
        # Original fields and Page 3Ah counters are present.
        assert result['cd_avg'] == 1400
        assert result['prefec_ber_avg'] == 0.001
        assert result['tx_bits_pm'] == 2000000

    @pytest.mark.parametrize("mock_response, expected", [
        (0, 0),
        (1, 1),
    ])
    def test_get_vdm_freeze_status(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_vdm_freeze_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, 0),
        (1, 1),
    ])
    def test_get_vdm_unfreeze_status(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response
        result = self.api.get_vdm_unfreeze_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, 0),
        (1, 1),
    ])
    def test_freeze_vdm_stats(self, mock_response, expected):
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.write.return_value = mock_response
        result = self.api.freeze_vdm_stats()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (0, 0),
        (1, 1),
    ])
    def test_unfreeze_vdm_stats(self, mock_response, expected):
        self.api.xcvr_eeprom.write = MagicMock()
        self.api.xcvr_eeprom.write.return_value = mock_response
        result = self.api.unfreeze_vdm_stats()
        assert result == expected

