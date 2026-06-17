import pytest
from unittest.mock import MagicMock, patch, Mock
from sonic_platform_base.sonic_xcvr.api.bailly.bailly_api import BaillyApi
from sonic_platform_base.sonic_xcvr.mem_maps.bailly.bailly_mem_map import BaillyMemMap
from sonic_platform_base.sonic_xcvr.codes.bailly.bailly_codes import BaillyCodes
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom

# Test BaillyCodes
class TestBaillyCodes:
    def setup_method(self):
        self.codes = BaillyCodes()

    def test_codes_inheritance(self):
        assert isinstance(self.codes, object)
        assert hasattr(self.codes, 'XCVR_IDENTIFIERS')
        assert hasattr(self.codes, 'XCVR_IDENTIFIER_ABBRV')

    def test_bailly_specific_identifiers(self):
        assert 128 in self.codes.XCVR_IDENTIFIERS
        assert 128 in self.codes.XCVR_IDENTIFIER_ABBRV

    def test_wavelength_grid_definitions(self):
        assert hasattr(self.codes, 'LASER_WAVELENGTH_GRID')
        assert isinstance(self.codes.LASER_WAVELENGTH_GRID, dict)

    def test_laser_count_definitions(self):
        assert hasattr(self.codes, 'LASER_COUNT')
        assert isinstance(self.codes.LASER_COUNT, dict)

# Test BaillyApi
NUM_CHANNELS = 8
class TestBaillyApi:
    def setup_method(self):
        self.mock_eeprom = MagicMock(spec=XcvrEeprom)
        self.api = BaillyApi(self.mock_eeprom)
        self.api.NUM_CHANNELS = NUM_CHANNELS

    def test_get_dpinit_pending(self):
        res = self.api.get_dpinit_pending()
        assert isinstance(res, dict)
        assert len(res) == NUM_CHANNELS
        for i in range(NUM_CHANNELS):
            assert f"DPInitPending{i+1}" in res
            assert res[f"DPInitPending{i+1}"] is True

    def test__format_revision_none(self):
        assert self.api._format_revision(None) is None

    def test__format_revision_values(self):
        assert self.api._format_revision(0x12) == "1.2"
        assert self.api._format_revision(0xF5) == "15.5"
        assert self.api._format_revision(0x00) == "0.0"

    def test_get_active_apsel_hostlane_with_zero_returns_current_map(self):
        app_values = [1, 2, 0, 3, 4, 5, 6, 7]
        with patch.object(self.api, 'get_application', side_effect=app_values):
            result = self.api.get_active_apsel_hostlane()
            assert len(result) == NUM_CHANNELS
            assert result['ActiveAppSelLane1'] == 1
            assert result['ActiveAppSelLane3'] == 0

    def test_get_active_apsel_hostlane_no_zero_calls_parent(self):
        app_values = [1, 1, 1, 1, 1, 1, 1, 1]
        fake_parent = {"key": "value"}

        with patch.object(self.api, 'get_application', side_effect=app_values):
            with patch.object(BaillyApi.__bases__[0], 'get_active_apsel_hostlane', return_value=fake_parent) as mock_super:
                result = self.api.get_active_apsel_hostlane()
                assert result == fake_parent
                mock_super.assert_called_once()

    def test_get_transceiver_info(self):
        with patch.object(self.api, 'get_els_info') as mock_els:
            mock_els.return_value = {}
            with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info') as mock_super:
                mock_super.return_value = {}
                self.api.get_transceiver_info()
                mock_super.assert_called_once()
                mock_els.assert_called_once()

    def test_get_els_info(self):
        self.mock_eeprom.read.return_value = 0
        result = self.api.get_els_info()
        assert isinstance(result, dict)

