import pytest
from unittest.mock import MagicMock, patch, Mock
from sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm import BaillyApi
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly_rlm import BaillyMemMap
from sonic_platform_base.sonic_xcvr.codes.broadcom.bailly_rlm import BaillyCodes
from sonic_platform_base.sonic_xcvr.fields.broadcom import bailly_rlm
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
        with patch.object(self.api, 'get_rlm_info') as mock_rlm:
            mock_rlm.return_value = {}
            with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info') as mock_super:
                mock_super.return_value = {}
                self.api.get_transceiver_info()
                mock_super.assert_called_once()
                mock_rlm.assert_called_once()

    def test_get_rlm_info(self):
        self.mock_eeprom.read.return_value = 0
        result = self.api.get_rlm_info()
        assert isinstance(result, dict)

    def test__format_float(self):
        assert self.api._format_float(None) is None
        assert self.api._format_float({'nested': 1}) is None
        assert self.api._format_float(12.34567) == 12.346

    def test_get_rlm_temperature(self):
        self.mock_eeprom.read.return_value = {
            bailly_rlm.MODULE_TEMPERATURE_MONITOR: 25.1234
        }
        assert self.api.get_rlm_temperature() == 25.123
        self.mock_eeprom.read.assert_called_with(bailly_rlm.CPO_MODULE_MONITORS_FIELD)

    def test_get_rlm_temperature_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_temperature() is None

    def test_get_rlm_single_read_apis(self):
        expected = {'value': 1}
        self.mock_eeprom.read.return_value = expected
        assert self.api.get_rlm_vendor_info() == expected
        self.mock_eeprom.read.assert_called_with(bailly_rlm.CPO_VENDOR_INFO_FIELD)
        assert self.api.get_rlm_laser_current() == expected
        self.mock_eeprom.read.assert_called_with(bailly_rlm.LASER_CURRENT_MONITOR_FIELD)
        assert self.api.get_rlm_laser_voltage() == expected
        self.mock_eeprom.read.assert_called_with(bailly_rlm.LASER_VOLTAGE_MONITOR_FIELD)
        assert self.api.get_rlm_laser_power() == expected
        self.mock_eeprom.read.assert_called_with(bailly_rlm.LASER_OPTICAL_POWER_MONITOR_FIELD)

    def test_get_rlm_monitor_values(self):
        self.mock_eeprom.read.return_value = {
            bailly_rlm.MODULE_TEMPERATURE_MONITOR: 25.1234,
            bailly_rlm.MODULE_SUPPLY_VOLTAGE_MONITOR: 3.3462,
            bailly_rlm.TEC_CURRENT_MONITOR: None,
        }
        assert self.api.get_rlm_monitor_values() == {
            'rlm_temperature': 25.123,
            'rlm_voltage': 3.346,
            'rlm_tec_current': None,
        }

    def test_get_rlm_monitor_values_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_monitor_values() is None

    def test_get_rlm_thresholds(self):
        thresholds = {
            bailly_rlm.RLM_TEMP_HIGH_ALARM_FIELD: 85.1234,
            bailly_rlm.RLM_TEMP_LOW_ALARM_FIELD: -5.0,
            bailly_rlm.RLM_TEMP_HIGH_WARNING_FIELD: 75.0,
            bailly_rlm.RLM_TEMP_LOW_WARNING_FIELD: 0.0,
            bailly_rlm.RLM_VCC_HIGH_ALARM_FIELD: 3.63,
            bailly_rlm.RLM_VCC_LOW_ALARM_FIELD: 2.97,
            bailly_rlm.RLM_VCC_HIGH_WARNING_FIELD: 3.465,
            bailly_rlm.RLM_VCC_LOW_WARNING_FIELD: 3.135,
            bailly_rlm.RLM_TX_POWER_HIGH_ALARM_FIELD: 7.0,
            bailly_rlm.RLM_TX_POWER_LOW_ALARM_FIELD: -6.9,
            bailly_rlm.RLM_TX_POWER_HIGH_WARNING_FIELD: 4.0,
            bailly_rlm.RLM_TX_POWER_LOW_WARNING_FIELD: -2.9,
            bailly_rlm.RLM_TX_BIAS_HIGH_ALARM_FIELD: 162.5,
            bailly_rlm.RLM_TX_BIAS_HIGH_WARNING_FIELD: 156.248,
        }
        self.mock_eeprom.read.return_value = {
            bailly_rlm.THRESHOLD_VALUES_FIELD: thresholds
        }
        assert self.api.get_rlm_thresholds() == {
            'rlm_temphighalarm': 85.123,
            'rlm_templowalarm': -5.0,
            'rlm_temphighwarning': 75.0,
            'rlm_templowwarning': 0.0,
            'rlm_vcchighalarm': 3.63,
            'rlm_vcclowalarm': 2.97,
            'rlm_vcchighwarning': 3.465,
            'rlm_vcclowwarning': 3.135,
            'rlm_txpowerhighalarm': 7.0,
            'rlm_txpowerlowalarm': -6.9,
            'rlm_txpowerhighwarning': 4.0,
            'rlm_txpowerlowwarning': -2.9,
            'rlm_txbiashighalarm': 162.5,
            'rlm_txbiashighwarning': 156.248,
        }

    def test_get_rlm_thresholds_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_thresholds() is None
        self.mock_eeprom.read.return_value = {}
        assert self.api.get_rlm_thresholds() is None

    def test_get_rlm_flags(self):
        self.mock_eeprom.read.return_value = {
            bailly_rlm.TEMP_HIGH_ALARM_FLAG: True,
            bailly_rlm.TEMP_LOW_ALARM_FLAG: False,
            bailly_rlm.TEMP_HIGH_WARN_FLAG: True,
            bailly_rlm.TEMP_LOW_WARN_FLAG: False,
            bailly_rlm.VOLTAGE_HIGH_ALARM_FLAG: True,
            bailly_rlm.VOLTAGE_LOW_ALARM_FLAG: False,
            bailly_rlm.VOLTAGE_HIGH_WARN_FLAG: True,
            bailly_rlm.VOLTAGE_LOW_WARN_FLAG: False,
        }
        assert self.api.get_rlm_flags() == {
            'rlm_tempHAlarm': True,
            'rlm_tempLAlarm': False,
            'rlm_tempHWarn': True,
            'rlm_tempLWarn': False,
            'rlm_vccHAlarm': True,
            'rlm_vccLAlarm': False,
            'rlm_vccHWarn': True,
            'rlm_vccLWarn': False,
        }

    def test_get_rlm_flags_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_flags() is None

    def test_get_rlm_status(self):
        self.mock_eeprom.read.return_value = {
            bailly_rlm.MODULE_LOW_POWER_STATE: 'Low power mode',
            bailly_rlm.INTL_INTERRUPT_STATUS: 'Interrupt event occurred',
        }
        assert self.api.get_rlm_status() == {
            'rlm_module_low_power_state': 'Low power mode',
            'rlm_interrupt_status': 'Interrupt event occurred',
        }

    def test_get_rlm_status_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_status() is None

    def test_get_transceiver_dom_real_value_adds_rlm_values(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_real_value') as mock_super:
            mock_super.return_value = {'temperature': 55.0}
            with patch.object(self.api, 'get_rlm_monitor_values', return_value={'rlm_temperature': 25.123, 'rlm_voltage': None}):
                assert self.api.get_transceiver_dom_real_value() == {
                    'temperature': 55.0,
                    'rlm_temperature': 25.123,
                }

    def test_get_transceiver_threshold_info_adds_rlm_thresholds(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_threshold_info') as mock_super:
            mock_super.return_value = {'temphighalarm': 85.0}
            with patch.object(self.api, 'get_rlm_thresholds', return_value={'rlm_temphighalarm': 90.0, 'rlm_templowalarm': None}):
                assert self.api.get_transceiver_threshold_info() == {
                    'temphighalarm': 85.0,
                    'rlm_temphighalarm': 90.0,
                }

    def test_get_transceiver_dom_flags_adds_rlm_flags(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_flags') as mock_super:
            mock_super.return_value = {'tempHAlarm': False}
            with patch.object(self.api, 'get_rlm_flags', return_value={'rlm_tempHAlarm': True, 'rlm_tempLAlarm': None}):
                assert self.api.get_transceiver_dom_flags() == {
                    'tempHAlarm': False,
                    'rlm_tempHAlarm': True,
                }

    def test_get_transceiver_status_flags_adds_rlm_flags_and_status(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_status_flags') as mock_super:
            mock_super.return_value = {'module_state': 'Ready'}
            with patch.object(self.api, 'get_rlm_flags', return_value={'rlm_tempHAlarm': True}):
                with patch.object(self.api, 'get_rlm_status', return_value={'rlm_interrupt_status': 'Interrupt event occurred'}):
                    assert self.api.get_transceiver_status_flags() == {
                        'module_state': 'Ready',
                        'rlm_tempHAlarm': True,
                        'rlm_interrupt_status': 'Interrupt event occurred',
                    }

    def test_get_transceiver_info_adds_rlm_info(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info') as mock_super:
            mock_super.return_value = {'type': 'CPO Bailly'}
            with patch.object(self.api, 'get_rlm_info') as mock_rlm:
                mock_rlm.return_value = {
                    'cpo_info': {
                        bailly_rlm.CPO_IDENTIFIER: 'RLM Identifier',
                        bailly_rlm.CPO_REVISION: 0x12,
                        bailly_rlm.LASER_WAVELENGTH_GRID: 'CWDM4',
                        bailly_rlm.LASER_COUNT: 8,
                    },
                    'rlm_vendor_info': {
                        bailly_rlm.VENDOR_NAME_ASCII_FIELD: 'BROADCOM ',
                        bailly_rlm.VENDOR_OUI_HEX_FIELD: 'ec-01-e2',
                        bailly_rlm.VENDOR_PART_NUMBER_ASCII_FIELD: 'ARLM ',
                        bailly_rlm.VENDOR_REVISION_ASCII_FIELD: 'A0 ',
                        bailly_rlm.VENDOR_SERIAL_NUMBER_ASCII_FIELD: 'SN ',
                        bailly_rlm.DATE_CODE_FIELD: '2024-02-26 ',
                        bailly_rlm.MAX_POWER_CONSUMPTION_FIELD: 12.0,
                    },
                    'laser_power_mode': {
                        bailly_rlm.LASER_POWER_MODE_CONTROL_BITS_FIELD: 0,
                    },
                }
                result = self.api.get_transceiver_info()
                assert result['type'] == 'CPO Bailly'
                assert result['rlm_identifier'] == 'RLM Identifier'
                assert result['rlm_revision'] == '1.2'
                assert result['rlm_laser_wavelength_grid'] == 'CWDM4'
                assert result['rlm_laser_count'] == 8
                assert result['rlm_vendor_name'] == 'BROADCOM'
                assert result['rlm_vendor_oui'] == 'ec-01-e2'
                assert result['rlm_vendor_pn'] == 'ARLM'
                assert result['rlm_vendor_rev'] == 'A0'
                assert result['rlm_vendor_sn'] == 'SN'
                assert result['rlm_date_code'] == '2024-02-26'
                assert result['rlm_max_power'] == 12.0
                assert result['rlm_laser_power_mode_control'] == 0

    def test_get_transceiver_info_parent_none(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info') as mock_super:
            mock_super.return_value = None
            assert self.api.get_transceiver_info() is None
