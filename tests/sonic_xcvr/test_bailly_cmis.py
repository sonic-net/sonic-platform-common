import pytest
from unittest.mock import MagicMock, patch, Mock
from sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm import BaillyApi
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly_rlm import BaillyMemMap
from sonic_platform_base.sonic_xcvr.codes.broadcom.bailly_rlm import BaillyCodes
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

    def test__format_float(self):
        assert self.api._format_float(None) is None
        assert self.api._format_float({"key": "value"}) is None
        assert self.api._format_float(1.23456) == 1.235
        assert self.api._format_float(3.14159) == 3.142

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

    def test_get_rlm_temperature(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_temperature() is None

        mock_monitors = {
            'MODULE_TEMPERATURE_MONITOR': 25.6789
        }
        self.mock_eeprom.read.return_value = mock_monitors
        with patch('sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm.bailly_rlm.MODULE_TEMPERATURE_MONITOR', 
                   'MODULE_TEMPERATURE_MONITOR'):
            assert self.api.get_rlm_temperature() == 25.679

    def test__get_nested_monitor_value(self):
        monitors = {}
        assert self.api._get_nested_monitor_value(monitors, 'group', 'value') is None

        monitors = {'group': {}}
        assert self.api._get_nested_monitor_value(monitors, 'group', 'value') is None

        monitors = {'group': {'value': {'value': 10.123}}}
        assert self.api._get_nested_monitor_value(monitors, 'group', 'value') == 10.123

        monitors = {'group': {'value': 20.456}}
        assert self.api._get_nested_monitor_value(monitors, 'group', 'value') == 20.456

    def test_get_rlm_monitor_values(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_monitor_values() is None

        mock_monitors = {
            'MODULE_TEMPERATURE_MONITOR': 25.1234,
            'MODULE_SUPPLY_VOLTAGE_MONITOR': 3.3456,
            'TEC_CURRENT_MONITOR': None 
        }
        self.mock_eeprom.read.return_value = mock_monitors
        with patch.multiple('sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm.bailly_rlm',
                            MODULE_TEMPERATURE_MONITOR='MODULE_TEMPERATURE_MONITOR',
                            MODULE_SUPPLY_VOLTAGE_MONITOR='MODULE_SUPPLY_VOLTAGE_MONITOR',
                            TEC_CURRENT_MONITOR='TEC_CURRENT_MONITOR'): 
            result = self.api.get_rlm_monitor_values()
            assert result == {
                "RLM_temperature": 25.123,
                "RLM_voltage": 3.346,
                "RLM_tec_current": None
            }

    def test_get_rlm_thresholds(self):
        """Test get_rlm_thresholds"""
        self.mock_eeprom.read.return_value = {}
        result = self.api.get_rlm_thresholds()
        assert result is None

    def test_get_rlm_temperature_thresholds(self):
        with patch.object(self.api, 'get_rlm_thresholds', return_value=None):
            assert self.api.get_rlm_temperature_thresholds() is None

        mock_thresholds = {
            "RLM_temphighalarm": 85.0,
            "RLM_templowalarm": -5.0,
            "RLM_temphighwarning": 75.0,
            "RLM_templowwarning": 0.0,
            "RLM_vcchighalarm": 3.6
        }
        with patch.object(self.api, 'get_rlm_thresholds', return_value=mock_thresholds):
            result = self.api.get_rlm_temperature_thresholds()
            assert result == {
                "temphighalarm": 85.0,
                "templowalarm": -5.0,
                "temphighwarning": 75.0,
                "templowwarning": 0.0
            }

    def test_get_rlm_flags(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_flags() is None

        mock_alarms = {
            'TEMP_HIGH_ALARM_FLAG': True,
            'TEMP_LOW_ALARM_FLAG': False,
            'TEMP_HIGH_WARN_FLAG': True,
            'TEMP_LOW_WARN_FLAG': False,
            'VOLTAGE_HIGH_ALARM_FLAG': True,
            'VOLTAGE_LOW_ALARM_FLAG': False,
            'VOLTAGE_HIGH_WARN_FLAG': True,
            'VOLTAGE_LOW_WARN_FLAG': False
        }
        self.mock_eeprom.read.return_value = mock_alarms
        with patch.multiple('sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm.bailly_rlm',
                            TEMP_HIGH_ALARM_FLAG='TEMP_HIGH_ALARM_FLAG',
                            TEMP_LOW_ALARM_FLAG='TEMP_LOW_ALARM_FLAG',
                            TEMP_HIGH_WARN_FLAG='TEMP_HIGH_WARN_FLAG',
                            TEMP_LOW_WARN_FLAG='TEMP_LOW_WARN_FLAG',
                            VOLTAGE_HIGH_ALARM_FLAG='VOLTAGE_HIGH_ALARM_FLAG',
                            VOLTAGE_LOW_ALARM_FLAG='VOLTAGE_LOW_ALARM_FLAG',
                            VOLTAGE_HIGH_WARN_FLAG='VOLTAGE_HIGH_WARN_FLAG',
                            VOLTAGE_LOW_WARN_FLAG='VOLTAGE_LOW_WARN_FLAG'):
            result = self.api.get_rlm_flags()
            assert result == {
                "RLM_tempHAlarm": True,
                "RLM_tempLAlarm": False,
                "RLM_tempHWarn": True,
                "RLM_tempLWarn": False,
                "RLM_vccHAlarm": True,
                "RLM_vccLAlarm": False,
                "RLM_vccHWarn": True,
                "RLM_vccLWarn": False
            }

    def test_get_rlm_temperature_flags(self):
        with patch.object(self.api, 'get_rlm_flags', return_value=None):
            assert self.api.get_rlm_temperature_flags() is None

        mock_flags = {
            "RLM_tempHAlarm": True,
            "RLM_tempLAlarm": False,
            "RLM_tempHWarn": True,
            "RLM_tempLWarn": False,
            "RLM_vccHAlarm": True
        }
        with patch.object(self.api, 'get_rlm_flags', return_value=mock_flags):
            result = self.api.get_rlm_temperature_flags()
            assert result == {
                "tempHAlarm": True,
                "tempLAlarm": False,
                "tempHWarn": True,
                "tempLWarn": False
            }

    def test_get_transceiver_dom_real_value(self):
        with patch.object(BaillyApi.__bases__[0], 'get_transceiver_dom_real_value', return_value=None):
            # 测试 rlm_monitors 为 None
            with patch.object(self.api, 'get_rlm_monitor_values', return_value=None):
                assert self.api.get_transceiver_dom_real_value() == {}
            
            mock_rlm_monitors = {
                "RLM_temperature": 25.123,
                "RLM_voltage": 3.346,
                "RLM_invalid": None
            }
            with patch.object(self.api, 'get_rlm_monitor_values', return_value=mock_rlm_monitors):
                result = self.api.get_transceiver_dom_real_value()
                assert result == {
                    "RLM_temperature": 25.123,
                    "RLM_voltage": 3.346
                }

        parent_dom = {"temp": 20.0}
        with patch.object(BaillyApi.__bases__[0], 'get_transceiver_dom_real_value', return_value=parent_dom):
            mock_rlm_monitors = {"RLM_temperature": 25.123}
            with patch.object(self.api, 'get_rlm_monitor_values', return_value=mock_rlm_monitors):
                result = self.api.get_transceiver_dom_real_value()
                assert result == {
                    "temp": 20.0,
                    "RLM_temperature": 25.123
                }

    def test_get_transceiver_dom_flags(self):
        with patch.object(BaillyApi.__bases__[0], 'get_transceiver_dom_flags', return_value=None):
            with patch.object(self.api, 'get_rlm_flags', return_value=None):
                assert self.api.get_transceiver_dom_flags() == {}
            
            mock_rlm_flags = {
                "RLM_tempHAlarm": True,
                "RLM_tempLAlarm": False,
                "RLM_invalid": None
            }
            with patch.object(self.api, 'get_rlm_flags', return_value=mock_rlm_flags):
                result = self.api.get_transceiver_dom_flags()
                assert result == {
                    "RLM_tempHAlarm": True,
                    "RLM_tempLAlarm": False
                }

        parent_flags = {"tx_fault": True}
        with patch.object(BaillyApi.__bases__[0], 'get_transceiver_dom_flags', return_value=parent_flags):
            mock_rlm_flags = {"RLM_tempHAlarm": True}
            with patch.object(self.api, 'get_rlm_flags', return_value=mock_rlm_flags):
                result = self.api.get_transceiver_dom_flags()
                assert result == {
                    "tx_fault": True,
                    "RLM_tempHAlarm": True
                }

    def test_get_transceiver_status_flags(self):
        with patch.object(BaillyApi.__bases__[0], 'get_transceiver_status_flags', return_value=None):
            with patch.object(self.api, 'get_rlm_flags', return_value=None):
                with patch.object(self.api, 'get_rlm_status', return_value=None):
                    assert self.api.get_transceiver_status_flags() == {}
            
            mock_rlm_flags = {
                "RLM_tempHAlarm": True,
                "RLM_tempLAlarm": False,
                "RLM_invalid": None
            }
            with patch.object(self.api, 'get_rlm_flags', return_value=mock_rlm_flags):
                with patch.object(self.api, 'get_rlm_status', return_value=None):
                    result = self.api.get_transceiver_status_flags()
                    assert result == {
                        "RLM_tempHAlarm": True,
                        "RLM_tempLAlarm": False
                    }

        parent_flags = {"rx_los": True}
        with patch.object(BaillyApi.__bases__[0], 'get_transceiver_status_flags', return_value=parent_flags):
            mock_rlm_flags = {"RLM_tempHAlarm": True}
            mock_rlm_status = {
                "RLM_module_low_power_state": False,
                "RLM_interrupt_status": True
            }
            with patch.object(self.api, 'get_rlm_flags', return_value=mock_rlm_flags):
                with patch.object(self.api, 'get_rlm_status', return_value=mock_rlm_status):
                    result = self.api.get_transceiver_status_flags()
                    assert result == {
                        "rx_los": True,
                        "RLM_tempHAlarm": True,
                        "RLM_module_low_power_state": False,
                        "RLM_interrupt_status": True
                    }

    def test_get_transceiver_threshold_info(self):
        with patch.object(BaillyApi.__bases__[0], 'get_transceiver_threshold_info', return_value=None):
            with patch.object(self.api, 'get_rlm_thresholds', return_value=None):
                assert self.api.get_transceiver_threshold_info() == {}
            
            mock_rlm_thresholds = {
                "RLM_temphighalarm": 85.0,
                "RLM_templowalarm": -5.0,
                "RLM_invalid": None
            }
            with patch.object(self.api, 'get_rlm_thresholds', return_value=mock_rlm_thresholds):
                result = self.api.get_transceiver_threshold_info()
                assert result == {
                    "RLM_temphighalarm": 85.0,
                    "RLM_templowalarm": -5.0
                }

        parent_thresholds = {"temp_high_alarm": 80.0}
        with patch.object(BaillyApi.__bases__[0], 'get_transceiver_threshold_info', return_value=parent_thresholds):
            mock_rlm_thresholds = {"RLM_temphighalarm": 85.0}
            with patch.object(self.api, 'get_rlm_thresholds', return_value=mock_rlm_thresholds):
                result = self.api.get_transceiver_threshold_info()
                assert result == {
                    "temp_high_alarm": 80.0,
                    "RLM_temphighalarm": 85.0
                }

    def test_get_rlm_vendor_info(self):
        self.mock_eeprom.read.return_value = {"vendor_name": "test_vendor"}
        with patch('sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm.bailly_rlm.CPO_VENDOR_INFO_FIELD', 
                   'CPO_VENDOR_INFO_FIELD'):
            result = self.api.get_rlm_vendor_info()
            assert result == {"vendor_name": "test_vendor"}
            self.mock_eeprom.read.assert_called_with('CPO_VENDOR_INFO_FIELD')

    def test_get_rlm_info(self):
        mock_cpo_info = {"cpo_id": 123}
        mock_vendor_info = {"vendor": "test"}
        mock_laser_mode = {"power_mode": "high"}
        
        with patch.object(self.api, 'get_rlm_vendor_info', return_value=mock_vendor_info):
            self.mock_eeprom.read.side_effect = [mock_cpo_info, mock_laser_mode]
            
            with patch.multiple('sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm.bailly_rlm',
                                CPO_INFO_FIELD='CPO_INFO_FIELD',
                                LASER_POWER_MODE_CONTROL_FIELD='LASER_POWER_MODE_CONTROL_FIELD'):
                result = self.api.get_rlm_info()
                assert result == {
                    "cpo_info": mock_cpo_info,
                    "rlm_vendor_info": mock_vendor_info,
                    "laser_power_mode": mock_laser_mode
                }

    def test_get_rlm_laser_current(self):
        self.mock_eeprom.read.return_value = 50.0
        with patch('sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm.bailly_rlm.LASER_CURRENT_MONITOR_FIELD', 
                   'LASER_CURRENT_MONITOR_FIELD'):
            result = self.api.get_rlm_laser_current()
            assert result == 50.0
            self.mock_eeprom.read.assert_called_with('LASER_CURRENT_MONITOR_FIELD')

    def test_get_rlm_laser_voltage(self):
        self.mock_eeprom.read.return_value = 2.5
        with patch('sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm.bailly_rlm.LASER_VOLTAGE_MONITOR_FIELD', 
                   'LASER_VOLTAGE_MONITOR_FIELD'):
            result = self.api.get_rlm_laser_voltage()
            assert result == 2.5
            self.mock_eeprom.read.assert_called_with('LASER_VOLTAGE_MONITOR_FIELD')

    def test_get_rlm_laser_power(self):
        self.mock_eeprom.read.return_value = 10.0
        with patch('sonic_platform_base.sonic_xcvr.api.broadcom.bailly_rlm.bailly_rlm.LASER_OPTICAL_POWER_MONITOR_FIELD', 
                   'LASER_OPTICAL_POWER_MONITOR_FIELD'):
            result = self.api.get_rlm_laser_power()
            assert result == 10.0
            self.mock_eeprom.read.assert_called_with('LASER_OPTICAL_POWER_MONITOR_FIELD')

    def test_get_transceiver_info(self):
        """Test get_transceiver_info combines parent and RLM info"""
        with patch.object(self.api, 'get_rlm_info') as mock_get_rlm:
            mock_get_rlm.return_value = {
                "cpo_info": None,
                "rlm_vendor_info": None,
                "laser_power_mode": None
            }
            result = self.api.get_transceiver_info()
            assert result is not None
            assert isinstance(result, dict)
