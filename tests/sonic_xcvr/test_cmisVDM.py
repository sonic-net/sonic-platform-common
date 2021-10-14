from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.api.public.cmisVDM import CmisVdmApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.sff8024 import Sff8024
from sonic_platform_base.sonic_xcvr.codes.public.cmis_code import CmisCode

class TestVDM(object):

    def mock_vdm_api(self):
        codes = {'sff8024':Sff8024, 'cmis_code':CmisCode}
        mem_map = CmisMemMap(codes)
        reader = MagicMock(return_value=None)
        writer = MagicMock()
        xcvr_eeprom = XcvrEeprom(reader, writer, mem_map)
        api = CmisApi(xcvr_eeprom)
        api.vdm = CmisVdmApi(xcvr_eeprom)
        return api.vdm

    @pytest.mark.parametrize("input_param, expected", [
        (0x9200, 0.000512)
    ])
    def test_get_F16(self, input_param, expected):
        vdm = self.mock_vdm_api()      
        result = vdm.get_F16(input_param)
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        (
            [0x20, [0]*128],    # input_param
            [                   # mock_response
                (
                    16, 9, 16, 11, 16, 13, 16, 15,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                ),
                
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'), bytearray(b'\x00\x00'),
            ],
            {
                'Pre-FEC BER Minimum Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                'Pre-FEC BER Maximum Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                'Pre-FEC BER Average Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                'Pre-FEC BER Current Value Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                
            }
        )
    ])
    def test_get_VDM_page(self, input_param, mock_response, expected):
        vdm = self.mock_vdm_api()
        vdm.xcvr_eeprom.read_flexible = MagicMock()
        vdm.xcvr_eeprom.read_flexible.side_effect = mock_response
        result = vdm.get_VDM_page(*input_param)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            [   # mock_response
                0,  # vdm_page_supported_raw
                (   # VDM_flag_page
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                ),
                {   # VDM_current_page
                    'Pre-FEC BER Minimum Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                    'Pre-FEC BER Maximum Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                    'Pre-FEC BER Average Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                    'Pre-FEC BER Current Value Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                }
            ],
            {   # VDM_current_page
                'Pre-FEC BER Minimum Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                'Pre-FEC BER Maximum Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                'Pre-FEC BER Average Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                'Pre-FEC BER Current Value Media Input': {1: [0, 0, 0, 0, 0, False, False, False, False]},
            }

        )
    ])
    def test_get_VDM_allpage(self, mock_response, expected):
        vdm = self.mock_vdm_api()
        vdm.xcvr_eeprom.read = MagicMock()
        vdm.xcvr_eeprom.read.return_value = mock_response[0]
        vdm.xcvr_eeprom.read_flexible = MagicMock()
        vdm.xcvr_eeprom.read_flexible.return_value = mock_response[1]
        # input_param = [0x20, mock_response[1]]
        vdm.get_VDM_page = MagicMock()
        vdm.get_VDM_page.side_effect = mock_response[2:]
        result = vdm.get_VDM_allpage()
        assert result == expected