from mock import MagicMock
from mock import patch
import pytest
from sonic_platform_base.sonic_xcvr.api.public.c_cmis import CCmisApi, C_CMIS_XCVR_INFO_DEFAULT_DICT
from sonic_platform_base.sonic_xcvr.mem_maps.public.c_cmis import CCmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes

class TestCCmis(object):
    codes = CmisCodes
    mem_map = CCmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = CCmisApi(eeprom)

    @pytest.mark.parametrize("mock_response, expected", [
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

    @pytest.mark.parametrize("mock_response, expected", [
        (
            [
                1000000, 10000, 1000, 8, 12,              # preFEC_BER
                10000, 100, 0, 0, 0,                      # uncorr_frame
                1400, 1300, 1500,                         # CD
                7.0, 5.5, 9.2,                            # DGD
                40, 20, 60,                               # SOPMD
                1.0, 0.8, 1.2,                            # PDL
                28, 26, 30,                               # OSNR
                17, 15, 18,                               # ESNR
                200, 150, 250,                            # CFO
                15, 13, 18,                               # EVM
                -10, -9.5, -10.5,                         # TX power
                -8, -7, -9,                               # RX total power
                -8, -7, -9,                               # RX channel power
                5, 3, 8,                                  # SOPROc
                0, 0, 0,                                  # MER                
            ],
            {
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
                'rx_mer_avg': 0, 'rx_mer_min': 0, 'rx_mer_max': 0
            }
        )
    ])
    def test_get_pm_all(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = mock_response
        result = self.api.get_pm_all()
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
                    'host_electrical_interface': '400GAUI-8 C2M (Annex 120E)',
                    'vendor_oui': 'xx-xx-xx',
                    'manufacturer': 'VENDOR_NAME',
                    'media_interface_technology': '1550 nm DFB',
                    'media_interface_code': '400ZR, DWDM, amplified',
                    'serial': '00000000',
                    'host_lane_count': 8,
                    **{f'active_apsel_hostlane{i}': 1 for i in range(1, 9)},
                    'hardware_rev': '0.0',
                    'cmis_rev': '5.0',
                    'media_lane_assignment_option': 1,
                    'connector': 'LC',
                    'host_lane_assignment_option': 1,
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
                'host_electrical_interface': '400GAUI-8 C2M (Annex 120E)',
                'vendor_oui': 'xx-xx-xx',
                'manufacturer': 'VENDOR_NAME',
                'media_interface_technology': '1550 nm DFB',
                'media_interface_code': '400ZR, DWDM, amplified',
                'serial': '00000000',
                'host_lane_count': 8,
                **{f'active_apsel_hostlane{i}': 1 for i in range(1, 9)},
                'hardware_rev': '0.0',
                'cmis_rev': '5.0',
                'media_lane_assignment_option': 1,
                'connector': 'LC',
                'host_lane_assignment_option': 1,
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
                    'laser_temperature': 40,
                    'prefec_ber': 0.001,
                    'postfec_ber': 0,
                },
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                    'Modulator Bias X/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'CD high granularity, short link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'CD low granularity, long link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'DGD [ps]':{1:[5, 30, 0, 25, 0, False, False, False, False]},
                    'SOPMD [ps^2]':{1:[5, 100, 0, 80, 0, False, False, False, False]},
                    'SOP ROC [krad/s]':{1: [0, 65535, 0, 65535, 0, False, False, False, False]},
                    'PDL [dB]':{1:[0.5, 3, 0, 2.5, 0, False, False, False, False]},
                    'OSNR [dB]':{1:[30, 100, 26, 80, 27, False, False, False, False]},
                    'eSNR [dB]':{1:[16, 100, 13, 80, 14, False, False, False, False]},
                    'CFO [MHz]':{1:[100, 5000, -5000, 4000, -4000, False, False, False, False]},
                    'Tx Power [dBm]':{1:[-10, 0, -18, -2, -16, False, False, False, False]},
                    'Rx Total Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]},
                    'Rx Signal Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]}
                },
                193100, 193100, -10
            ],
            {
                'temperature': 50,
                'voltage': 3.3,
                'txpower': 0.1,
                'rxpower': 0.09,
                'txbias': 70,
                'laser_temperature': 40,
                'prefec_ber': 0.001,
                'postfec_ber': 0,
                'biasxi': 50,
                'biasxq': 50,
                'biasxp': 50,
                'biasyi': 50,
                'biasyq': 50,
                'biasyp': 50,
                'cdshort': 1000,
                'cdlong': 1000,
                'dgd': 5,
                'sopmd': 5,
                'soproc': 0,
                'pdl': 0.5,
                'osnr': 30,
                'esnr': 16,
                'cfo': 100,
                'txcurrpower': -10,
                'rxtotpower': -10,
                'rxsigpower': -10,
                'laser_config_freq': 193100,
                'laser_curr_freq': 193100,
                'tx_config_power': -10
            }
        )
    ])
    @patch("sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_bulk_status")
    def test_get_transceiver_bulk_status(self, get_transceiver_bulk_status_func, mock_response, expected):
        get_transceiver_bulk_status_func.return_value = mock_response[0]
        self.api.vdm_dict = mock_response[1]
        self.api.get_laser_config_freq = MagicMock()
        self.api.get_laser_config_freq.return_value = mock_response[2]
        self.api.get_current_laser_freq = MagicMock()
        self.api.get_current_laser_freq.return_value = mock_response[3]
        self.api.get_tx_config_power = MagicMock()
        self.api.get_tx_config_power.return_value = mock_response[4]
        result = self.api.get_transceiver_bulk_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                {
                    'temphighalarm': 80, 'templowalarm': 0, 'temphighwarning': 75, 'templowwarning': 10,
                    'vcchighalarm': 3.5, 'vcclowalarm': 3.1, 'vcchighwarning': 3.45, 'vcclowwarning': 3.15,
                    'txpowerhighalarm': 1.0, 'txpowerlowalarm': 0.01, 'txpowerhighwarning': 0.7, 'txpowerlowwarning': 0.02,
                    'rxpowerhighalarm': 2.0, 'rxpowerlowalarm': 0.01, 'rxpowerhighwarning': 1.0, 'rxpowerlowwarning': 0.02,
                    'txbiashighalarm': 90, 'txbiaslowalarm': 10, 'txbiashighwarning': 80, 'txbiaslowwarning': 20,
                    'lasertemphighalarm': 80, 'lasertemplowalarm': 10, 'lasertemphighwarning': 75, 'lasertemplowwarning': 20,
                    'prefecberhighalarm': 0.0125, 'prefecberlowalarm': 0, 'prefecberhighwarning': 0.01, 'prefecberlowwarning': 0,
                    'postfecberhighalarm': 1, 'postfecberlowalarm': 0, 'postfecberhighwarning': 1, 'postfecberlowwarning': 0,
                    'soprochighalarm' : 65535, 'soproclowalarm' : 0, 'soprochighwarning' : 65535, 'soproclowwarning' : 0,
                },
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                    'Modulator Bias X/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'CD high granularity, short link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'CD low granularity, long link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'DGD [ps]':{1:[5, 30, 0, 25, 0, False, False, False, False]},
                    'SOPMD [ps^2]':{1:[5, 100, 0, 80, 0, False, False, False, False]},
                    'SOP ROC [krad/s]':{1: [0, 65535, 0, 65535, 0, False, False, False, False]},
                    'PDL [dB]':{1:[0.5, 3, 0, 2.5, 0, False, False, False, False]},
                    'OSNR [dB]':{1:[30, 100, 26, 80, 27, False, False, False, False]},
                    'eSNR [dB]':{1:[16, 100, 13, 80, 14, False, False, False, False]},
                    'CFO [MHz]':{1:[100, 5000, -5000, 4000, -4000, False, False, False, False]},
                    'Tx Power [dBm]':{1:[-10, 0, -18, -2, -16, False, False, False, False]},
                    'Rx Total Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]},
                }
            ],
            {
                'temphighalarm': 80, 'templowalarm': 0, 'temphighwarning': 75, 'templowwarning': 10,
                'vcchighalarm': 3.5, 'vcclowalarm': 3.1, 'vcchighwarning': 3.45, 'vcclowwarning': 3.15,
                'txpowerhighalarm': 1.0, 'txpowerlowalarm': 0.01, 'txpowerhighwarning': 0.7, 'txpowerlowwarning': 0.02,
                'rxpowerhighalarm': 2.0, 'rxpowerlowalarm': 0.01, 'rxpowerhighwarning': 1.0, 'rxpowerlowwarning': 0.02,
                'txbiashighalarm': 90, 'txbiaslowalarm': 10, 'txbiashighwarning': 80, 'txbiaslowwarning': 20,
                'lasertemphighalarm': 80, 'lasertemplowalarm': 10, 'lasertemphighwarning': 75, 'lasertemplowwarning': 20,
                'prefecberhighalarm': 0.0125, 'prefecberlowalarm': 0, 'prefecberhighwarning': 0.01, 'prefecberlowwarning': 0,
                'postfecberhighalarm': 1, 'postfecberlowalarm': 0, 'postfecberhighwarning': 1, 'postfecberlowwarning': 0,
                'biasxihighalarm': 90, 'biasxilowalarm': 10, 'biasxihighwarning': 85, 'biasxilowwarning': 15,
                'biasxqhighalarm': 90, 'biasxqlowalarm': 10, 'biasxqhighwarning': 85, 'biasxqlowwarning': 15,
                'biasxphighalarm': 90, 'biasxplowalarm': 10, 'biasxphighwarning': 85, 'biasxplowwarning': 15,
                'biasyihighalarm': 90, 'biasyilowalarm': 10, 'biasyihighwarning': 85, 'biasyilowwarning': 15,
                'biasyqhighalarm': 90, 'biasyqlowalarm': 10, 'biasyqhighwarning': 85, 'biasyqlowwarning': 15,
                'biasyphighalarm': 90, 'biasyplowalarm': 10, 'biasyphighwarning': 85, 'biasyplowwarning': 15,
                'cdshorthighalarm': 2000, 'cdshortlowalarm': 0, 'cdshorthighwarning': 1800, 'cdshortlowwarning': 0,
                'cdlonghighalarm': 2000, 'cdlonglowalarm': 0, 'cdlonghighwarning': 1800, 'cdlonglowwarning': 0,
                'dgdhighalarm': 30, 'dgdlowalarm': 0, 'dgdhighwarning': 25, 'dgdlowwarning': 0,
                'sopmdhighalarm': 100, 'sopmdlowalarm': 0, 'sopmdhighwarning': 80, 'sopmdlowwarning': 0,
                'pdlhighalarm': 3, 'pdllowalarm': 0, 'pdlhighwarning': 2.5, 'pdllowwarning': 0,
                'osnrhighalarm': 100, 'osnrlowalarm': 26, 'osnrhighwarning': 80, 'osnrlowwarning': 27,
                'esnrhighalarm': 100, 'esnrlowalarm': 13, 'esnrhighwarning': 80, 'esnrlowwarning': 14,
                'cfohighalarm': 5000, 'cfolowalarm': -5000, 'cfohighwarning': 4000, 'cfolowwarning': -4000,
                'txcurrpowerhighalarm': 0, 'txcurrpowerlowalarm': -18, 'txcurrpowerhighwarning': -2, 'txcurrpowerlowwarning': -16,
                'rxtotpowerhighalarm': 3, 'rxtotpowerlowalarm': -18, 'rxtotpowerhighwarning': 0, 'rxtotpowerlowwarning': -15,
                'rxsigpowerhighalarm': 'N/A', 'rxsigpowerlowalarm': 'N/A', 'rxsigpowerhighwarning': 'N/A', 'rxsigpowerlowwarning': 'N/A',
                'soprochighalarm': 65535, 'soproclowalarm': 0, 'soprochighwarning': 65535, 'soproclowwarning': 0
            }
        )
    ])
    @patch("sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_threshold_info")
    def test_get_transceiver_threshold_info(self, get_transceiver_threshold_info_func, mock_response, expected):
        get_transceiver_threshold_info_func.return_value = mock_response[0]
        self.api.vdm_dict = mock_response[1]
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
                    'txfault': False,
                    'txlos_hostlane1': False,
                    'txlos_hostlane2': False,
                    'txlos_hostlane3': False,
                    'txlos_hostlane4': False,
                    'txlos_hostlane5': False,
                    'txlos_hostlane6': False,
                    'txlos_hostlane7': False,
                    'txlos_hostlane8': False,
                    'txcdrlol_hostlane1': False,
                    'txcdrlol_hostlane2': False,
                    'txcdrlol_hostlane3': False,
                    'txcdrlol_hostlane4': False,
                    'txcdrlol_hostlane5': False,
                    'txcdrlol_hostlane6': False,
                    'txcdrlol_hostlane7': False,
                    'txcdrlol_hostlane8': False,
                    'rxlos': False,
                    'rxcdrlol': False,
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
                    'temphighalarm_flag': False, 'templowalarm_flag': False, 
                    'temphighwarning_flag': False, 'templowwarning_flag': False,
                    'vcchighalarm_flag': False, 'vcclowalarm_flag': False, 
                    'vcchighwarning_flag': False, 'vcclowwarning_flag': False,
                    'lasertemphighalarm_flag': False, 'lasertemplowalarm_flag': False, 
                    'lasertemphighwarning_flag': False, 'lasertemplowwarning_flag': False,
                    'txpowerhighalarm_flag': False, 'txpowerlowalarm_flag': False, 
                    'txpowerhighwarning_flag': False, 'txpowerlowwarning_flag': False,
                    'rxpowerhighalarm_flag': False, 'rxpowerlowalarm_flag': False, 
                    'rxpowerhighwarning_flag': False, 'rxpowerlowwarning_flag': False,
                    'txbiashighalarm_flag': False, 'txbiaslowalarm_flag': False, 
                    'txbiashighwarning_flag': False, 'txbiaslowwarning_flag': False,
                    'prefecberhighalarm_flag': False, 'prefecberlowalarm_flag': False, 
                    'prefecberhighwarning_flag': False, 'prefecberlowwarning_flag': False,
                    'postfecberhighalarm_flag': False, 'postfecberlowalarm_flag': False, 
                    'postfecberhighwarning_flag': False, 'postfecberlowwarning_flag': False,
                    'soprochighalarm_flag' : False, 'soproclowalarm_flag' : False,
                    'soprochighwarning_flag' : False, 'soproclowwarning_flag' : False,
                },
                False, False, ['TuningComplete'],
                {
                    'Pre-FEC BER Average Media Input':{1:[0.001, 0.0125, 0, 0.01, 0, False, False, False, False]},
                    'Errored Frames Average Media Input':{1:[0, 1, 0, 1, 0, False, False, False, False]},
                    'Modulator Bias X/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias X_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/I [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y/Q [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'Modulator Bias Y_Phase [%]':{1:[50, 90, 10, 85, 15, False, False, False, False]},
                    'CD high granularity, short link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'CD low granularity, long link [ps/nm]':{1:[1000, 2000, 0, 1800, 0, False, False, False, False]},
                    'DGD [ps]':{1:[5, 30, 0, 25, 0, False, False, False, False]},
                    'SOPMD [ps^2]':{1:[5, 100, 0, 80, 0, False, False, False, False]},
                    'SOP ROC [krad/s]':{1: [0, 65535, 0, 65535, 0, False, False, False, False]},
                    'PDL [dB]':{1:[0.5, 3, 0, 2.5, 0, False, False, False, False]},
                    'OSNR [dB]':{1:[30, 100, 26, 80, 27, False, False, False, False]},
                    'eSNR [dB]':{1:[16, 100, 13, 80, 14, False, False, False, False]},
                    'CFO [MHz]':{1:[100, 5000, -5000, 4000, -4000, False, False, False, False]},
                    'Tx Power [dBm]':{1:[-10, 0, -18, -2, -16, False, False, False, False]},
                    'Rx Total Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]},
                    'Rx Signal Power [dBm]':{1:[-10, 3, -18, 0, -15, False, False, False, False]}
                }
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
                'txfault': False,
                'txlos_hostlane1': False,
                'txlos_hostlane2': False,
                'txlos_hostlane3': False,
                'txlos_hostlane4': False,
                'txlos_hostlane5': False,
                'txlos_hostlane6': False,
                'txlos_hostlane7': False,
                'txlos_hostlane8': False,
                'txcdrlol_hostlane1': False,
                'txcdrlol_hostlane2': False,
                'txcdrlol_hostlane3': False,
                'txcdrlol_hostlane4': False,
                'txcdrlol_hostlane5': False,
                'txcdrlol_hostlane6': False,
                'txcdrlol_hostlane7': False,
                'txcdrlol_hostlane8': False,
                'rxlos': False,
                'rxcdrlol': False,
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
                'target_output_power_oor': False,
                'fine_tuning_oor': False,
                'tuning_not_accepted': False,
                'invalid_channel_num': False,
                'tuning_complete': True,
                'temphighalarm_flag': False, 'templowalarm_flag': False, 
                'temphighwarning_flag': False, 'templowwarning_flag': False,
                'vcchighalarm_flag': False, 'vcclowalarm_flag': False, 
                'vcchighwarning_flag': False, 'vcclowwarning_flag': False,
                'lasertemphighalarm_flag': False, 'lasertemplowalarm_flag': False, 
                'lasertemphighwarning_flag': False, 'lasertemplowwarning_flag': False,
                'txpowerhighalarm_flag': False, 'txpowerlowalarm_flag': False, 
                'txpowerhighwarning_flag': False, 'txpowerlowwarning_flag': False,
                'rxpowerhighalarm_flag': False, 'rxpowerlowalarm_flag': False, 
                'rxpowerhighwarning_flag': False, 'rxpowerlowwarning_flag': False,
                'txbiashighalarm_flag': False, 'txbiaslowalarm_flag': False, 
                'txbiashighwarning_flag': False, 'txbiaslowwarning_flag': False,
                'prefecberhighalarm_flag': False, 'prefecberlowalarm_flag': False, 
                'prefecberhighwarning_flag': False, 'prefecberlowwarning_flag': False,
                'postfecberhighalarm_flag': False, 'postfecberlowalarm_flag': False, 
                'postfecberhighwarning_flag': False, 'postfecberlowwarning_flag': False,
                'biasxihighalarm_flag': False, 'biasxilowalarm_flag': False, 
                'biasxihighwarning_flag': False, 'biasxilowwarning_flag': False,
                'biasxqhighalarm_flag': False, 'biasxqlowalarm_flag': False, 
                'biasxqhighwarning_flag': False, 'biasxqlowwarning_flag': False,
                'biasxphighalarm_flag': False, 'biasxplowalarm_flag': False, 
                'biasxphighwarning_flag': False, 'biasxplowwarning_flag': False,
                'biasyihighalarm_flag': False, 'biasyilowalarm_flag': False, 
                'biasyihighwarning_flag': False, 'biasyilowwarning_flag': False,
                'biasyqhighalarm_flag': False, 'biasyqlowalarm_flag': False, 
                'biasyqhighwarning_flag': False, 'biasyqlowwarning_flag': False,
                'biasyphighalarm_flag': False, 'biasyplowalarm_flag': False, 
                'biasyphighwarning_flag': False, 'biasyplowwarning_flag': False,
                'cdshorthighalarm_flag': False, 'cdshortlowalarm_flag': False, 
                'cdshorthighwarning_flag': False, 'cdshortlowwarning_flag': False,
                'cdlonghighalarm_flag': False, 'cdlonglowalarm_flag': False, 
                'cdlonghighwarning_flag': False, 'cdlonglowwarning_flag': False,
                'dgdhighalarm_flag': False, 'dgdlowalarm_flag': False, 
                'dgdhighwarning_flag': False, 'dgdlowwarning_flag': False,
                'sopmdhighalarm_flag': False, 'sopmdlowalarm_flag': False, 
                'sopmdhighwarning_flag': False, 'sopmdlowwarning_flag': False,
                'pdlhighalarm_flag': False, 'pdllowalarm_flag': False, 
                'pdlhighwarning_flag': False, 'pdllowwarning_flag': False,
                'osnrhighalarm_flag': False, 'osnrlowalarm_flag': False, 
                'osnrhighwarning_flag': False, 'osnrlowwarning_flag': False,
                'esnrhighalarm_flag': False, 'esnrlowalarm_flag': False, 
                'esnrhighwarning_flag': False, 'esnrlowwarning_flag': False,
                'cfohighalarm_flag': False, 'cfolowalarm_flag': False, 
                'cfohighwarning_flag': False, 'cfolowwarning_flag': False,
                'txcurrpowerhighalarm_flag': False, 'txcurrpowerlowalarm_flag': False, 
                'txcurrpowerhighwarning_flag': False, 'txcurrpowerlowwarning_flag': False,
                'rxtotpowerhighalarm_flag': False, 'rxtotpowerlowalarm_flag': False, 
                'rxtotpowerhighwarning_flag': False, 'rxtotpowerlowwarning_flag': False,
                'rxsigpowerhighalarm_flag': False, 'rxsigpowerlowalarm_flag': False, 
                'rxsigpowerhighwarning_flag': False, 'rxsigpowerlowwarning_flag': False,
                'soprochighalarm_flag' : False, 'soproclowalarm_flag' : False,
                'soprochighwarning_flag' : False, 'soproclowwarning_flag' : False
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
        self.api.get_laser_tuning_summary = MagicMock()
        self.api.get_laser_tuning_summary.return_value = mock_response[3]
        self.api.vdm_dict = mock_response[4]
        result = self.api.get_transceiver_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            {
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
            }
        )
    ])
    def test_get_transceiver_pm(self, mock_response, expected):
        self.api.get_pm_all = MagicMock()
        self.api.get_pm_all.return_value = mock_response
        result = self.api.get_transceiver_pm()
        assert result == expected

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

