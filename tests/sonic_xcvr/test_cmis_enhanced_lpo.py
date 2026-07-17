from unittest.mock import patch, MagicMock, call
import struct
import pytest

from sonic_platform_base.sonic_xcvr.api.arista.cmis_enhanced_lpo import CmisEnhancedLpoApi
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.mem_maps.arista.cmis_enhanced_lpo import CmisEnhancedLpoMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.fields import arista_lpo_consts as lpo
from sonic_platform_base.sonic_xcvr.xcvr_api_factory import XcvrApiFactory


def _test_vma_fields():
    return [
        lpo.LPO_HOST_INPUT_VMA_TX1, lpo.LPO_HOST_INPUT_VMA_TX2,
        lpo.LPO_HOST_INPUT_VMA_TX3, lpo.LPO_HOST_INPUT_VMA_TX4,
        lpo.LPO_HOST_INPUT_VMA_TX5, lpo.LPO_HOST_INPUT_VMA_TX6,
        lpo.LPO_HOST_INPUT_VMA_TX7, lpo.LPO_HOST_INPUT_VMA_TX8,
    ]


def _test_oma_fields():
    return [
        lpo.LPO_INPUT_OMA_RX1, lpo.LPO_INPUT_OMA_RX2,
        lpo.LPO_INPUT_OMA_RX3, lpo.LPO_INPUT_OMA_RX4,
        lpo.LPO_INPUT_OMA_RX5, lpo.LPO_INPUT_OMA_RX6,
        lpo.LPO_INPUT_OMA_RX7, lpo.LPO_INPUT_OMA_RX8,
    ]


def _test_vma_threshold_fields():
    return [
        lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_THRESHOLD,
        lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_THRESHOLD,
        lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_THRESHOLD,
        lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_THRESHOLD,
    ]


def _test_oma_threshold_fields():
    return [
        lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_THRESHOLD,
        lpo.LPO_RX_INPUT_OMA_LOW_ALARM_THRESHOLD,
        lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_THRESHOLD,
        lpo.LPO_RX_INPUT_OMA_LOW_WARNING_THRESHOLD,
    ]


def _test_vma_flag_fields():
    return [
        lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG,
        lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_FLAG,
        lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_FLAG,
        lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_FLAG,
    ]


def _test_oma_flag_fields():
    return [
        lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_FLAG,
        lpo.LPO_RX_INPUT_OMA_LOW_ALARM_FLAG,
        lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_FLAG,
        lpo.LPO_RX_INPUT_OMA_LOW_WARNING_FLAG,
    ]


class TestCmisEnhancedLpoApi:
    def setup_method(self):
        self.mem_map = CmisEnhancedLpoMemMap(CmisCodes)
        reader = MagicMock(return_value=None)
        writer = MagicMock()
        self.eeprom = XcvrEeprom(reader, writer, self.mem_map)
        self.api = CmisEnhancedLpoApi(self.eeprom)

    # ------------------------------------------------------------------
    # get_transceiver_info
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("lpo_reads, expected_lpo", [
        (
            # All fields readable
            {
                lpo.LPO_CAPABILITY: 0x1C,
                lpo.LPO_TX_POLARITY_INVERTED: 0b10000001,
                lpo.LPO_RX_POLARITY_INVERTED: 0b01000010,
                lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY: 15.0,
                lpo.LPO_RX_INPUT_OMA_MON_ACCURACY: 1.0,
                lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX: 5.0,
            },
            {
                lpo.LPO_TX_POLARITY_INVERTED: 0b10000001,
                lpo.LPO_RX_POLARITY_INVERTED: 0b01000010,
                lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY: 15.0,
                lpo.LPO_RX_INPUT_OMA_MON_ACCURACY: 1.0,
                lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX: 5.0,
            },
        ),
        (
            # Failed reads -> N/A
            {
                lpo.LPO_CAPABILITY: 0x1C,
                lpo.LPO_TX_POLARITY_INVERTED: None,
                lpo.LPO_RX_POLARITY_INVERTED: None,
                lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY: None,
                lpo.LPO_RX_INPUT_OMA_MON_ACCURACY: None,
                lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX: None,
            },
            {
                lpo.LPO_TX_POLARITY_INVERTED: 'N/A',
                lpo.LPO_RX_POLARITY_INVERTED: 'N/A',
                lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY: 'N/A',
                lpo.LPO_RX_INPUT_OMA_MON_ACCURACY: 'N/A',
                lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX: 'N/A',
            },
        ),
        (
            # Zero raw values -> zero scaled values
            {
                lpo.LPO_CAPABILITY: 0x1C,
                lpo.LPO_TX_POLARITY_INVERTED: 0x00,
                lpo.LPO_RX_POLARITY_INVERTED: 0x00,
                lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY: 0x00,
                lpo.LPO_RX_INPUT_OMA_MON_ACCURACY: 0x00,
                lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX: 0,
            },
            {
                lpo.LPO_TX_POLARITY_INVERTED: 0x00,
                lpo.LPO_RX_POLARITY_INVERTED: 0x00,
                lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY: 0.0,
                lpo.LPO_RX_INPUT_OMA_MON_ACCURACY: 0.0,
                lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX: 0.0,
            },
        ),
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info',
           return_value={'type': 'QSFP-DD', 'model': 'LPO-800G-2DR4'})
    def test_get_transceiver_info(self, mock_super, lpo_reads, expected_lpo):
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: lpo_reads.get(f))
        result = self.api.get_transceiver_info()
        for key, expected_val in expected_lpo.items():
            assert result[key] == expected_val

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info',
           return_value=None)
    def test_get_transceiver_info_super_returns_none(self, _):
        assert self.api.get_transceiver_info() is None

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info',
           return_value={'type': 'QSFP-DD', 'model': 'LPO-800G-2DR4'})
    def test_get_transceiver_info_capability_read_failed(self, mock_super):
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: None)
        assert self.api.get_transceiver_info() is None

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info',
           return_value={'type': 'QSFP-DD', 'model': 'LPO-800G-2DR4'})
    def test_get_transceiver_info_unsupported_capabilities(self, mock_super):
        supported_reads = {
            lpo.LPO_CAPABILITY: 0x00,
            lpo.LPO_TX_POLARITY_INVERTED: 0xAA,
            lpo.LPO_RX_POLARITY_INVERTED: 0x55,
        }
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: supported_reads.get(f))

        result = self.api.get_transceiver_info()

        assert result[lpo.LPO_TX_POLARITY_INVERTED] == 0xAA
        assert result[lpo.LPO_RX_POLARITY_INVERTED] == 0x55
        assert result[lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY] == 'N/A'
        assert result[lpo.LPO_RX_INPUT_OMA_MON_ACCURACY] == 'N/A'
        assert result[lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX] == 'N/A'
        assert call(lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY) not in self.api.xcvr_eeprom.read.call_args_list
        assert call(lpo.LPO_RX_INPUT_OMA_MON_ACCURACY) not in self.api.xcvr_eeprom.read.call_args_list
        assert call(lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX) not in self.api.xcvr_eeprom.read.call_args_list

    # ------------------------------------------------------------------
    # get_transceiver_dom_real_value
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("vma_raws, oma_raws, expected_vma, expected_oma", [
        (
            [10, 20, 30, 40, 50, 60, 70, 80],   # VMA raw counts
            [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000],  # OMA raw counts
            [50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0],   # mV
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],                  # mW
        ),
        (
            [None] * 8,
            [None] * 8,
            ['N/A'] * 8,
            ['N/A'] * 8,
        ),
        (
            [255] * 8,   # max U8 -> 255 * 5 = 1275 mV
            [65535] * 8, # max U16 -> 65535 * 0.0001 = 6.5535 mW, rounds to 6.554 at precision=3
            [1275.0] * 8,
            [6.554] * 8,
        ),
        (
            # Mixed: alternate None and non-None per lane
            [10, None, 30, None, 50, None, 70, None],
            [1000, None, 3000, None, 5000, None, 7000, None],
            [50.0, 'N/A', 150.0, 'N/A', 250.0, 'N/A', 350.0, 'N/A'],
            [0.1, 'N/A', 0.3, 'N/A', 0.5, 'N/A', 0.7, 'N/A'],
        ),
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_real_value',
           return_value={'temperature': 25.0, 'voltage': 3.3})
    def test_get_transceiver_dom_real_value(self, mock_super,
                                            vma_raws, oma_raws,
                                            expected_vma, expected_oma):
        vma_fields = [
            lpo.LPO_HOST_INPUT_VMA_TX1, lpo.LPO_HOST_INPUT_VMA_TX2,
            lpo.LPO_HOST_INPUT_VMA_TX3, lpo.LPO_HOST_INPUT_VMA_TX4,
            lpo.LPO_HOST_INPUT_VMA_TX5, lpo.LPO_HOST_INPUT_VMA_TX6,
            lpo.LPO_HOST_INPUT_VMA_TX7, lpo.LPO_HOST_INPUT_VMA_TX8,
        ]
        oma_fields = [
            lpo.LPO_INPUT_OMA_RX1, lpo.LPO_INPUT_OMA_RX2,
            lpo.LPO_INPUT_OMA_RX3, lpo.LPO_INPUT_OMA_RX4,
            lpo.LPO_INPUT_OMA_RX5, lpo.LPO_INPUT_OMA_RX6,
            lpo.LPO_INPUT_OMA_RX7, lpo.LPO_INPUT_OMA_RX8,
        ]
        read_map = {lpo.LPO_CAPABILITY: 0x1C}
        read_map.update({f: v for f, v in zip(vma_fields + oma_fields, expected_vma + expected_oma)})
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: read_map.get(f))

        result = self.api.get_transceiver_dom_real_value()
        for field, expected in zip(vma_fields, expected_vma):
            assert result[field] == expected
        for field, expected in zip(oma_fields, expected_oma):
            assert result[field] == expected

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_real_value',
           return_value=None)
    def test_get_transceiver_dom_real_value_super_returns_none(self, _):
        assert self.api.get_transceiver_dom_real_value() is None

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_real_value',
           return_value={'temperature': 25.0, 'voltage': 3.3})
    def test_get_transceiver_dom_real_value_capability_read_failed(self, mock_super):
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: None)
        assert self.api.get_transceiver_dom_real_value() is None

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_real_value',
           return_value={'temperature': 25.0, 'voltage': 3.3})
    def test_get_transceiver_dom_real_value_unsupported_capabilities(self, mock_super):
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: {lpo.LPO_CAPABILITY: 0x00}.get(f))

        result = self.api.get_transceiver_dom_real_value()

        for field in _test_vma_fields():
            assert result[field] == 'N/A'
            assert call(field) not in self.api.xcvr_eeprom.read.call_args_list
        for field in _test_oma_fields():
            assert result[field] == 'N/A'
            assert call(field) not in self.api.xcvr_eeprom.read.call_args_list

    # ------------------------------------------------------------------
    # get_transceiver_threshold_info
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("vma_raws, oma_raws, expected_vma_mv, expected_oma_mw", [
        (
            [200, 50, 180, 70],    # high alarm, low alarm, high warn, low warn (raw counts)
            [10000, 2000, 8000, 3000],
            [1000.0, 250.0, 900.0, 350.0],   # mV
            [1.0, 0.2, 0.8, 0.3],             # mW
        ),
        (
            [None, None, None, None],
            [None, None, None, None],
            ['N/A', 'N/A', 'N/A', 'N/A'],
            ['N/A', 'N/A', 'N/A', 'N/A'],
        ),
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_threshold_info',
           return_value={'temphighalarm': 80.0})
    def test_get_transceiver_threshold_info(self, mock_super,
                                            vma_raws, oma_raws,
                                            expected_vma_mv, expected_oma_mw):
        vma_threshold_fields = [
            lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_THRESHOLD,
            lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_THRESHOLD,
            lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_THRESHOLD,
            lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_THRESHOLD,
        ]
        oma_threshold_fields = [
            lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_THRESHOLD,
            lpo.LPO_RX_INPUT_OMA_LOW_ALARM_THRESHOLD,
            lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_THRESHOLD,
            lpo.LPO_RX_INPUT_OMA_LOW_WARNING_THRESHOLD,
        ]
        read_map = {lpo.LPO_CAPABILITY: 0x1C}
        read_map.update({f: v for f, v in zip(
            vma_threshold_fields + oma_threshold_fields,
            expected_vma_mv + expected_oma_mw,
        )})
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: read_map.get(f))

        result = self.api.get_transceiver_threshold_info()
        for field, expected in zip(vma_threshold_fields, expected_vma_mv):
            assert result[field] == expected
        for field, expected in zip(oma_threshold_fields, expected_oma_mw):
            assert result[field] == expected

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_threshold_info',
           return_value=None)
    def test_get_transceiver_threshold_info_super_returns_none(self, _):
        assert self.api.get_transceiver_threshold_info() is None

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_threshold_info',
           return_value={'temphighalarm': 80.0})
    def test_get_transceiver_threshold_info_capability_read_failed(self, mock_super):
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: None)
        assert self.api.get_transceiver_threshold_info() is None

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_threshold_info',
           return_value={'temphighalarm': 80.0})
    def test_get_transceiver_threshold_info_unsupported_capabilities(self, mock_super):
        fields = _test_vma_threshold_fields() + _test_oma_threshold_fields()
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: {lpo.LPO_CAPABILITY: 0x00}.get(f))

        result = self.api.get_transceiver_threshold_info()

        for field in fields:
            assert result[field] == 'N/A'
            assert call(field) not in self.api.xcvr_eeprom.read.call_args_list

    # ------------------------------------------------------------------
    # get_transceiver_dom_flags (per-lane flag unpacking)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("bitmask, expected_lanes", [
        (0xFF, {i: True for i in range(1, 9)}),   # all lanes set
        (0x00, {i: False for i in range(1, 9)}),  # no lanes set
        (0x01, {1: True,  2: False, 3: False, 4: False,
                5: False, 6: False, 7: False, 8: False}),  # lane 1 only
        (0x80, {1: False, 2: False, 3: False, 4: False,
                5: False, 6: False, 7: False, 8: True}),   # lane 8 only
        (0x81, {1: True,  2: False, 3: False, 4: False,
                5: False, 6: False, 7: False, 8: True}),   # lanes 1 and 8
    ])
    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_flags',
           return_value={})
    def test_get_transceiver_dom_flags_unpack(self, mock_super, bitmask, expected_lanes):
        def read_field(field):
            if field == lpo.LPO_CAPABILITY:
                return 0x1C
            return {"{}{}".format(field, lane): expected for lane, expected in expected_lanes.items()}

        self.api.xcvr_eeprom.read = MagicMock(side_effect=read_field)
        result = self.api.get_transceiver_dom_flags()

        flag_field_names = [
            lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG,
            lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_FLAG,
            lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_FLAG,
            lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_FLAG,
            lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_FLAG,
            lpo.LPO_RX_INPUT_OMA_LOW_ALARM_FLAG,
            lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_FLAG,
            lpo.LPO_RX_INPUT_OMA_LOW_WARNING_FLAG,
        ]
        for field_name in flag_field_names:
            for lane, expected_val in expected_lanes.items():
                key = "{}{}".format(field_name, lane)
                assert result[key] == expected_val, \
                    "bitmask=0x{:02x} field={} lane={}: got {}, want {}".format(
                        bitmask, field_name, lane, result[key], expected_val)

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_flags',
           return_value={})
    def test_get_transceiver_dom_flags_none_read(self, mock_super):
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: 0x1C if f == lpo.LPO_CAPABILITY else None)
        result = self.api.get_transceiver_dom_flags()
        all_flag_fields = [
            lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG,
            lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_FLAG,
            lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_FLAG,
            lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_FLAG,
            lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_FLAG,
            lpo.LPO_RX_INPUT_OMA_LOW_ALARM_FLAG,
            lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_FLAG,
            lpo.LPO_RX_INPUT_OMA_LOW_WARNING_FLAG,
        ]
        for field in all_flag_fields:
            for lane in range(1, 9):
                assert result["{}{}".format(field, lane)] == 'N/A'

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_flags',
           return_value=None)
    def test_get_transceiver_dom_flags_super_returns_none(self, _):
        assert self.api.get_transceiver_dom_flags() is None

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_flags',
           return_value={})
    def test_get_transceiver_dom_flags_capability_read_failed(self, mock_super):
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: None)
        assert self.api.get_transceiver_dom_flags() is None

    @patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_flags',
           return_value={})
    def test_get_transceiver_dom_flags_unsupported_capabilities(self, mock_super):
        fields = _test_vma_flag_fields() + _test_oma_flag_fields()
        self.api.xcvr_eeprom.read = MagicMock(side_effect=lambda f: {lpo.LPO_CAPABILITY: 0x00}.get(f))

        result = self.api.get_transceiver_dom_flags()

        for field in fields:
            assert call(field) not in self.api.xcvr_eeprom.read.call_args_list
            for lane in range(1, 9):
                assert result["{}{}".format(field, lane)] == 'N/A'

    # ------------------------------------------------------------------
    # mem_map: verify field offsets are registered correctly
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("field_name, expected_offset", [
        # Page 01h advertisement bytes (page=1, bank=0): offset = 1*128 + byte
        (lpo.LPO_EEPROM_COMPLIANCE,   1 * 128 + 195),
        (lpo.LPO_ENHANCED_SPEC_VERSION, 1 * 128 + 196),
        # Page C1h (page=0xC1=193, bank=0): offset = 193*128 + byte
        (lpo.LPO_CAPABILITY,                          193 * 128 + 128),
        (lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX,       193 * 128 + 129),
        (lpo.LPO_TX_POLARITY_INVERTED,                193 * 128 + 133),
        (lpo.LPO_RX_POLARITY_INVERTED,                193 * 128 + 134),
        (lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY,      193 * 128 + 135),
        (lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_THRESHOLD, 193 * 128 + 136),
        (lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_THRESHOLD,  193 * 128 + 137),
        (lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_THRESHOLD, 193 * 128 + 138),
        (lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_THRESHOLD,  193 * 128 + 139),
        (lpo.LPO_RX_INPUT_OMA_MON_ACCURACY,           193 * 128 + 140),
        (lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_THRESHOLD,   193 * 128 + 141),
        (lpo.LPO_RX_INPUT_OMA_LOW_ALARM_THRESHOLD,    193 * 128 + 143),
        (lpo.LPO_RX_INPUT_OMA_HIGH_WARNING_THRESHOLD, 193 * 128 + 145),
        (lpo.LPO_RX_INPUT_OMA_LOW_WARNING_THRESHOLD,  193 * 128 + 147),
        # Page C2h (page=0xC2=194, bank=0): offset = 194*128 + byte
        (lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG,  194 * 128 + 141),
        (lpo.LPO_TX_HOST_INPUT_VMA_LOW_ALARM_FLAG,   194 * 128 + 142),
        (lpo.LPO_TX_HOST_INPUT_VMA_HIGH_WARNING_FLAG, 194 * 128 + 143),
        (lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_FLAG,  194 * 128 + 144),
        (lpo.LPO_HOST_INPUT_VMA_TX1,                 194 * 128 + 145),
        (lpo.LPO_HOST_INPUT_VMA_TX8,                 194 * 128 + 152),
        (lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_MASK,  194 * 128 + 153),
        (lpo.LPO_TX_HOST_INPUT_VMA_LOW_WARNING_MASK, 194 * 128 + 156),
        (lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_FLAG,       194 * 128 + 157),
        (lpo.LPO_RX_INPUT_OMA_LOW_WARNING_FLAG,      194 * 128 + 160),
        (lpo.LPO_INPUT_OMA_RX1,                      194 * 128 + 161),
        (lpo.LPO_INPUT_OMA_RX8,                      194 * 128 + 175),
        (lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_MASK,       194 * 128 + 177),
        (lpo.LPO_RX_INPUT_OMA_LOW_WARNING_MASK,      194 * 128 + 180),
    ])
    def test_field_offsets(self, field_name, expected_offset):
        field = self.mem_map.get_field(field_name)
        assert field.get_offset() == expected_offset, \
            "field {} offset: got {}, want {}".format(field_name, field.get_offset(), expected_offset)

    @pytest.mark.parametrize("field_name, expected_size", [
        # U8 fields
        (lpo.LPO_EEPROM_COMPLIANCE, 1),
        (lpo.LPO_TX_POLARITY_INVERTED, 1),
        (lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_THRESHOLD, 1),
        (lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG, 1),
        (lpo.LPO_HOST_INPUT_VMA_TX1, 1),
        # U16 fields
        (lpo.LPO_RX_INPUT_OMA_HIGH_ALARM_THRESHOLD, 2),
        (lpo.LPO_INPUT_OMA_RX1, 2),
        (lpo.LPO_INPUT_OMA_RX8, 2),
    ])
    def test_field_sizes(self, field_name, expected_size):
        field = self.mem_map.get_field(field_name)
        assert field.get_size() == expected_size

    def test_field_decoders(self):
        raw_by_offset = {}

        def add_raw(field_name, raw):
            field = self.mem_map.get_field(field_name)
            raw_by_offset[field.get_offset()] = raw

        add_raw(lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY, bytes([0xF3]))
        add_raw(lpo.LPO_RX_INPUT_OMA_MON_ACCURACY, bytes([0xF5]))
        add_raw(lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX, bytes([50]))
        add_raw(lpo.LPO_HOST_INPUT_VMA_TX1, bytes([255]))
        add_raw(lpo.LPO_INPUT_OMA_RX1, struct.pack(">H", 65535))
        add_raw(lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG, bytes([0x81]))

        eeprom = XcvrEeprom(lambda offset, size: raw_by_offset.get(offset), MagicMock(), self.mem_map)

        assert eeprom.read(lpo.LPO_TX_HOST_INPUT_VMA_MON_ACCURACY) == 15.0
        assert eeprom.read(lpo.LPO_RX_INPUT_OMA_MON_ACCURACY) == 1.0
        assert eeprom.read(lpo.LPO_TX_OUTER_EXTINCTION_RATIO_MAX) == 5.0
        assert eeprom.read(lpo.LPO_HOST_INPUT_VMA_TX1) == 1275.0
        assert eeprom.read(lpo.LPO_INPUT_OMA_RX1) == 6.554

        decoded_flags = eeprom.read(lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG)
        assert decoded_flags[lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG + "1"] is True
        assert decoded_flags[lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG + "2"] is False
        assert decoded_flags[lpo.LPO_TX_HOST_INPUT_VMA_HIGH_ALARM_FLAG + "8"] is True

    # ------------------------------------------------------------------
    # factory dispatch
    # ------------------------------------------------------------------

    @patch('sonic_platform_base.sonic_xcvr.eeprom_rw.ModuleEepromLowerMemoryInfo.get_vendor_name',
           MagicMock(return_value='Arista'))
    @patch('sonic_platform_base.sonic_xcvr.eeprom_rw.ModuleEepromLowerMemoryInfo.get_vendor_part_num',
           MagicMock(return_value='LPO-800G-2DR4'))
    def test_factory_creates_arista_lpo_api(self):
        def mock_reader(start, length):
            return bytes([0x18])

        factory = XcvrApiFactory(mock_reader, MagicMock())
        api = factory.create_xcvr_api()
        assert isinstance(api, CmisEnhancedLpoApi)
