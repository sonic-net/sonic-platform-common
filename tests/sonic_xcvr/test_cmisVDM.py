from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.api.public.cmisVDM import CmisVdmApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes

class TestVDM(object):
    codes = CmisCodes
    mem_map = CmisMemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = CmisVdmApi(eeprom)

    @pytest.mark.parametrize("input_param, expected", [
        (0x9200, 0.000512)
    ])
    def test_get_F16(self, input_param, expected):
        result = self.api.get_F16(input_param)
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        (
            [0x20, [0]*128],    # input_param
            [                   # mock_response
                (
                    16, 9, 16, 11, 16, 13, 16, 15, 32, 10, 33, 10,  0,  0,  0,  0,
                    80,128, 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    160,143,0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
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
                'Pre-FEC BER Minimum Host Input': {
                    1: [0, 0, 0, 0, 0, False, False, False, False],
                    2: [0, 0, 0, 0, 0, False, False, False, False],
                },
                'Modulator Bias X/I [%]': {1: [0, 0, 0, 0, 0, False, False, False, False]},
                'Tx Power [dBm]': {1: [0, 0, 0, 0, 0, False, False, False, False]},               
            }
        )
    ])
    def test_get_vdm_page(self, input_param, mock_response, expected):
        self.api.xcvr_eeprom.read_raw = MagicMock()
        self.api.xcvr_eeprom.read_raw.side_effect = mock_response
        result = self.api.get_vdm_page(*input_param)
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        (
            [0x20, [0]*128],    # input_param
            [                   # mock_response
                (
                    16, 9, 16, 11, 16, 13, 16, 15, 32, 10, 33, 10,  0,  0,  0,  0,
                    80,128, 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    160,143,0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
                ),

                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            {}
        )
    ])
    def test_get_vdm_page_none_vdm_value_raw(self, input_param, mock_response, expected):
        self.api.xcvr_eeprom.read_raw = MagicMock()
        self.api.xcvr_eeprom.read_raw.side_effect = mock_response
        result = self.api.get_vdm_page(*input_param)
        assert result == expected

    @pytest.mark.parametrize("input_param, mock_response, expected", [
        (
            [0x20, [0]*128],    # input_param
            [                   # mock_response
                None,
            ],
            {}
        )
    ])
    def test_get_vdm_page_none_vdm_descriptor(self, input_param, mock_response, expected):
        self.api.xcvr_eeprom.read_raw = MagicMock()
        self.api.xcvr_eeprom.read_raw.side_effect = mock_response
        result = self.api.get_vdm_page(*input_param)
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
    def test_get_vdm_allpage(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.return_value = mock_response[0]
        self.api.xcvr_eeprom.read_raw = MagicMock()
        self.api.xcvr_eeprom.read_raw.return_value = mock_response[1]
        # input_param = [0x20, mock_response[1]]
        self.api.get_vdm_page = MagicMock()
        self.api.get_vdm_page.side_effect = mock_response[2:]
        result = self.api.get_vdm_allpage()
        assert result == expected
