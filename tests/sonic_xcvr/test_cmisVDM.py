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
                
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
                bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
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

    def test_get_vdm_page_observable_type_basic_only(self):
        """Test get_vdm_page with VDM_OBSERVABLE_BASIC filters out statistic observables"""
        # Descriptor: typeIDs at odd positions: 9(S), 11(S), 13(S), 15(B), 10(S), 10(S), 0, 0
        # Only typeID 15 is basic ('B')
        descriptor = (
            16, 9, 16, 11, 16, 13, 16, 15, 32, 10, 33, 10,  0,  0,  0,  0,
            80,128, 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            160,143,0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        )
        mock_responses = [
            descriptor,
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
        ]
        self.api.xcvr_eeprom.read_raw = MagicMock(side_effect=mock_responses)
        result = self.api.get_vdm_page(0x20, [0]*128, observable_type=CmisVdmApi.VDM_OBSERVABLE_BASIC)
        # Only basic observable (ID 15: Pre-FEC BER Current Value Media Input) should be present
        assert 'Pre-FEC BER Current Value Media Input' in result
        # Statistic observables should be filtered out
        assert 'Pre-FEC BER Minimum Media Input' not in result
        assert 'Pre-FEC BER Maximum Media Input' not in result
        assert 'Pre-FEC BER Average Media Input' not in result
        assert 'Pre-FEC BER Minimum Host Input' not in result

    def test_get_vdm_page_observable_type_statistic_only(self):
        """Test get_vdm_page with VDM_OBSERVABLE_STATISTIC filters out basic observables"""
        descriptor = (
            16, 9, 16, 11, 16, 13, 16, 15, 32, 10, 33, 10,  0,  0,  0,  0,
            80,128, 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            160,143,0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
            0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
        )
        mock_responses = [
            descriptor,
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
            bytearray(b'\x00\x00'), bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00'),
        ]
        self.api.xcvr_eeprom.read_raw = MagicMock(side_effect=mock_responses)
        result = self.api.get_vdm_page(0x20, [0]*128, observable_type=CmisVdmApi.VDM_OBSERVABLE_STATISTIC)
        # Statistic observables should be present
        assert 'Pre-FEC BER Minimum Media Input' in result
        assert 'Pre-FEC BER Maximum Media Input' in result
        assert 'Pre-FEC BER Average Media Input' in result
        assert 'Pre-FEC BER Minimum Host Input' in result
        # Basic observable (ID 15) should be filtered out
        assert 'Pre-FEC BER Current Value Media Input' not in result

    @pytest.mark.parametrize("vdm_supported, groups_raw, descriptor, expected", [
        # Case 1: VDM not supported
        (0, None, None, False),
        # Case 2: VDM supported but groups_raw is None
        (1, None, None, False),
        # Case 3: VDM supported, descriptor has only basic types (ID 15=B)
        (1, 0, bytearray([16, 15] + [0]*126), False),
        # Case 4: VDM supported, descriptor has a statistic type (ID 9=S)
        (1, 0, bytearray([16, 9] + [0]*126), True),
        # Case 5: VDM supported, descriptor is None/empty
        (1, 0, None, False),
    ])
    def test_is_vdm_statistic_supported(self, vdm_supported, groups_raw, descriptor, expected):
        self.api.xcvr_eeprom.read = MagicMock(side_effect=[vdm_supported, groups_raw])
        self.api.xcvr_eeprom.read_raw = MagicMock(return_value=descriptor)
        result = self.api.is_vdm_statistic_supported()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
        (
            [   # mock_response
                1,  # vdm_pages_supported
                0,  # vdm_groups_supported_raw
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

        ),
        ([
            0,
            None,
            None,
            None
        ],
        None)
    ])
    def test_get_vdm_allpage(self, mock_response, expected):
        self.api.xcvr_eeprom.read = MagicMock()
        self.api.xcvr_eeprom.read.side_effect = (mock_response[0], mock_response[1])
        self.api.xcvr_eeprom.read_raw = MagicMock()
        self.api.xcvr_eeprom.read_raw.return_value = mock_response[2]
        # input_param = [0x20, mock_response[1]]
        self.api.get_vdm_page = MagicMock()
        self.api.get_vdm_page.side_effect = mock_response[3:]
        result = self.api.get_vdm_allpage()
        assert result == expected
