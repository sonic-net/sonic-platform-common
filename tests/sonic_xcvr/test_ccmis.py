from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.api.public.c_cmis import CCmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.sff8024 import Sff8024
from sonic_platform_base.sonic_xcvr.codes.public.cmis_code import CmisCode

class TestCCmis(object):

    def mock_ccmis_api(self):
        codes = {'sff8024':Sff8024, 'cmis_code':CmisCode}
        mem_map = CmisMemMap(codes)
        reader = MagicMock(return_value=None)
        writer = MagicMock()
        xcvr_eeprom = XcvrEeprom(reader, writer, mem_map)
        api = CmisApi(xcvr_eeprom)
        api.ccmis = CCmisApi(xcvr_eeprom)
        return api.ccmis

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
    def test_get_PM_all(self, mock_response, expected):
        ccmis = self.mock_ccmis_api()
        ccmis.xcvr_eeprom.read = MagicMock()
        ccmis.xcvr_eeprom.read.side_effect = mock_response
        result = ccmis.get_PM_all()
        assert result == expected
    # TODO: call other methods in the api
