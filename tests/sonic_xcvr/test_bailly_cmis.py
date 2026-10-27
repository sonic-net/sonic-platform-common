import pytest
from unittest.mock import MagicMock, patch, Mock
from sonic_platform_base.sonic_xcvr.api.broadcom.bailly import BaillyApi
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly import BaillyMemMap
from sonic_platform_base.sonic_xcvr.codes.broadcom.bailly import BaillyCodes
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.fields.broadcom import bailly
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
            bailly.MODULE_TEMPERATURE_MONITOR: 25.1234
        }
        assert self.api.get_rlm_temperature() == 25.123
        self.mock_eeprom.read.assert_called_with(bailly.CPO_MODULE_MONITORS_FIELD)

    def test_get_rlm_temperature_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_temperature() is None

    def test_get_rlm_single_read_apis(self):
        expected = {'value': 1}
        self.mock_eeprom.read.return_value = expected
        assert self.api.get_rlm_vendor_info() == expected
        self.mock_eeprom.read.assert_called_with(bailly.CPO_VENDOR_INFO_FIELD)
        assert self.api.get_rlm_laser_current() == expected
        self.mock_eeprom.read.assert_called_with(bailly.LASER_CURRENT_MONITOR_FIELD)
        assert self.api.get_rlm_laser_voltage() == expected
        self.mock_eeprom.read.assert_called_with(bailly.LASER_VOLTAGE_MONITOR_FIELD)
        assert self.api.get_rlm_laser_power() == expected
        self.mock_eeprom.read.assert_called_with(bailly.LASER_OPTICAL_POWER_MONITOR_FIELD)

    def test_get_rlm_monitor_values(self):
        self.mock_eeprom.read.return_value = {
            bailly.MODULE_TEMPERATURE_MONITOR: 25.1234,
            bailly.MODULE_SUPPLY_VOLTAGE_MONITOR: 3.3462,
            bailly.TEC_CURRENT_MONITOR: None,
        }
        assert self.api.get_rlm_monitor_values() == {
            'els_temperature': 25.123,
            'els_voltage': 3.346,
            'rlm_tec_current': None,
        }

    def test_get_rlm_monitor_values_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_monitor_values() is None

    def test_get_rlm_thresholds(self):
        thresholds = {
            bailly.RLM_TEMP_HIGH_ALARM_FIELD: 85.1234,
            bailly.RLM_TEMP_LOW_ALARM_FIELD: -5.0,
            bailly.RLM_TEMP_HIGH_WARNING_FIELD: 75.0,
            bailly.RLM_TEMP_LOW_WARNING_FIELD: 0.0,
            bailly.RLM_VCC_HIGH_ALARM_FIELD: 3.63,
            bailly.RLM_VCC_LOW_ALARM_FIELD: 2.97,
            bailly.RLM_VCC_HIGH_WARNING_FIELD: 3.465,
            bailly.RLM_VCC_LOW_WARNING_FIELD: 3.135,
            bailly.RLM_TX_POWER_HIGH_ALARM_FIELD: 7.0,
            bailly.RLM_TX_POWER_LOW_ALARM_FIELD: -6.9,
            bailly.RLM_TX_POWER_HIGH_WARNING_FIELD: 4.0,
            bailly.RLM_TX_POWER_LOW_WARNING_FIELD: -2.9,
            bailly.RLM_TX_BIAS_HIGH_ALARM_FIELD: 162.5,
            bailly.RLM_TX_BIAS_HIGH_WARNING_FIELD: 156.248,
        }
        self.mock_eeprom.read.return_value = {
            bailly.THRESHOLD_VALUES_FIELD: thresholds
        }
        assert self.api.get_rlm_thresholds() == {
            'els_temphighalarm': 85.123,
            'els_templowalarm': -5.0,
            'els_temphighwarning': 75.0,
            'els_templowwarning': 0.0,
            'els_vcchighalarm': 3.63,
            'els_vcclowalarm': 2.97,
            'els_vcchighwarning': 3.465,
            'els_vcclowwarning': 3.135,
            'els_txpowerhighalarm': 7.0,
            'els_txpowerlowalarm': -6.9,
            'els_txpowerhighwarning': 4.0,
            'els_txpowerlowwarning': -2.9,
            'els_txbiashighalarm': 162.5,
            'els_txbiashighwarning': 156.248,
        }

    def test_get_rlm_thresholds_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_thresholds() is None
        self.mock_eeprom.read.return_value = {}
        assert self.api.get_rlm_thresholds() is None

    def test_get_rlm_flags(self):
        self.mock_eeprom.read.return_value = {
            bailly.TEMP_HIGH_ALARM_FLAG: True,
            bailly.TEMP_LOW_ALARM_FLAG: False,
            bailly.TEMP_HIGH_WARN_FLAG: True,
            bailly.TEMP_LOW_WARN_FLAG: False,
            bailly.VOLTAGE_HIGH_ALARM_FLAG: True,
            bailly.VOLTAGE_LOW_ALARM_FLAG: False,
            bailly.VOLTAGE_HIGH_WARN_FLAG: True,
            bailly.VOLTAGE_LOW_WARN_FLAG: False,
        }
        assert self.api.get_rlm_flags() == {
            'els_tempHAlarm': True,
            'els_tempLAlarm': False,
            'els_tempHWarn': True,
            'els_tempLWarn': False,
            'els_vccHAlarm': True,
            'els_vccLAlarm': False,
            'els_vccHWarn': True,
            'els_vccLWarn': False,
        }

    def test_get_rlm_flags_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_flags() is None

    def test_get_rlm_status(self):
        self.mock_eeprom.read.return_value = {
            bailly.MODULE_LOW_POWER_STATE: 'Low power mode',
            bailly.INTL_INTERRUPT_STATUS: 'Interrupt event occurred',
        }
        assert self.api.get_rlm_status() == {
            'els_module_low_power_state': 'Low power mode',
            'els_interrupt_status': 'Interrupt event occurred',
        }

    def test_get_rlm_status_none(self):
        self.mock_eeprom.read.return_value = None
        assert self.api.get_rlm_status() is None

    def test_get_transceiver_dom_real_value_adds_rlm_values(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_real_value') as mock_super:
            mock_super.return_value = {'temperature': 55.0}
            with patch.object(self.api, 'get_rlm_monitor_values', return_value={'els_temperature': 25.123, 'els_voltage': None}):
                assert self.api.get_transceiver_dom_real_value() == {
                    'temperature': 55.0,
                    'els_temperature': 25.123,
                }

    def test_get_transceiver_threshold_info_adds_rlm_thresholds(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_threshold_info') as mock_super:
            mock_super.return_value = {'temphighalarm': 85.0}
            with patch.object(self.api, 'get_rlm_thresholds', return_value={'els_temphighalarm': 90.0, 'els_templowalarm': None}):
                assert self.api.get_transceiver_threshold_info() == {
                    'temphighalarm': 85.0,
                    'els_temphighalarm': 90.0,
                }

    def test_get_transceiver_dom_flags_adds_rlm_flags(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_dom_flags') as mock_super:
            mock_super.return_value = {'tempHAlarm': False}
            with patch.object(self.api, 'get_rlm_flags', return_value={'els_tempHAlarm': True, 'els_tempLAlarm': None}):
                assert self.api.get_transceiver_dom_flags() == {
                    'tempHAlarm': False,
                    'els_tempHAlarm': True,
                }

    def test_get_transceiver_status_flags_adds_rlm_flags_and_status(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_status_flags') as mock_super:
            mock_super.return_value = {'module_state': 'Ready'}
            with patch.object(self.api, 'get_rlm_flags', return_value={'els_tempHAlarm': True}):
                with patch.object(self.api, 'get_rlm_status', return_value={'els_interrupt_status': 'Interrupt event occurred'}):
                    assert self.api.get_transceiver_status_flags() == {
                        'module_state': 'Ready',
                        'els_tempHAlarm': True,
                        'els_interrupt_status': 'Interrupt event occurred',
                    }

    def test_get_transceiver_info_adds_rlm_info(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info') as mock_super:
            mock_super.return_value = {'type': 'CPO Bailly'}
            with patch.object(self.api, 'get_rlm_info') as mock_rlm:
                mock_rlm.return_value = {
                    'cpo_info': {
                        bailly.CPO_IDENTIFIER: 'ELS Identifier',
                        bailly.CPO_REVISION: 0x12,
                        bailly.LASER_WAVELENGTH_GRID: 'CWDM4',
                        bailly.LASER_COUNT: 8,
                    },
                    'rlm_vendor_info': {
                        bailly.VENDOR_NAME_ASCII_FIELD: 'BROADCOM ',
                        bailly.VENDOR_OUI_HEX_FIELD: 'ec-01-e2',
                        bailly.VENDOR_PART_NUMBER_ASCII_FIELD: 'ARLM ',
                        bailly.VENDOR_REVISION_ASCII_FIELD: 'A0 ',
                        bailly.VENDOR_SERIAL_NUMBER_ASCII_FIELD: 'SN ',
                        bailly.DATE_CODE_FIELD: '2024-02-26 ',
                        bailly.MAX_POWER_CONSUMPTION_FIELD: 12.0,
                    },
                    'laser_power_mode': {
                        bailly.LASER_POWER_MODE_CONTROL_BITS_FIELD: 0,
                    },
                }
                result = self.api.get_transceiver_info()
                assert result['type'] == 'CPO Bailly'
                assert result['els_identifier'] == 'ELS Identifier'
                assert result['els_revision'] == '1.2'
                assert result['els_laser_count'] == 8
                assert result['els_vendor_name'] == 'BROADCOM'
                assert result['els_vendor_oui'] == 'ec-01-e2'
                assert result['els_vendor_pn'] == 'ARLM'
                assert result['els_vendor_rev'] == 'A0'
                assert result['els_vendor_sn'] == 'SN'
                assert result['els_date_code'] == '2024-02-26'
                assert result['els_max_power'] == 12.0
                assert result['rlm_laser_wavelength_grid'] == 'CWDM4'
                assert result['rlm_laser_lpmode_control'] == 0

    def test_get_transceiver_info_parent_none(self):
        with patch('sonic_platform_base.sonic_xcvr.api.public.cmis.CmisApi.get_transceiver_info') as mock_super:
            mock_super.return_value = None
            assert self.api.get_transceiver_info() is None


# Test BaillyApi staged control set (set_application / scs_apply_datapath_init)
BAILLY_MODULE = 'sonic_platform_base.sonic_xcvr.api.broadcom.bailly'
APSEL_BLOCK_START = 2193
DPINIT_FIELD_NAME = "{}_0".format(consts.STAGED_CTRL_APPLY_DPINIT_FIELD)

class TestBaillyStagedControlSet:
    @pytest.fixture(autouse=True)
    def _no_sleep(self):
        with patch('{}.time.sleep'.format(BAILLY_MODULE)):
            yield

    def setup_method(self):
        self.mock_eeprom = MagicMock(spec=XcvrEeprom)
        self.mock_eeprom.mem_map = MagicMock()
        self.api = BaillyApi(self.mock_eeprom)
        self.api.NUM_CHANNELS = NUM_CHANNELS
        self.api.is_flat_memory = MagicMock(return_value=False)

        ap_sel_fields = {}
        for lane in range(1, NUM_CHANNELS + 1):
            field = MagicMock()
            field.get_offset.return_value = APSEL_BLOCK_START + lane - 1
            field.get_size.return_value = 1
            ap_sel_fields["{}_{}_{}".format(consts.STAGED_CTRL_APSEL_FIELD, 0, lane)] = field
        self.mock_eeprom.mem_map.get_field.side_effect = ap_sel_fields.get

    def _expect_reg_value(self, *values):
        self.mock_eeprom.read_raw.return_value = tuple(values)

    def test_set_application_writes_whole_ap_sel_block(self):
        self._expect_reg_value(*(0x10,) * 4 + (0x18,) * 4)
        self.mock_eeprom.write_raw.return_value = True

        assert self.api.set_application(0xff, 1, 0) is True
        self.mock_eeprom.write_raw.assert_called_once_with(
            APSEL_BLOCK_START, NUM_CHANNELS, bytearray([0x10] * 4 + [0x18] * 4))

    def test_set_application_800g_has_no_lane_group_bit(self):
        self._expect_reg_value(*(0x61,) * NUM_CHANNELS)
        self.mock_eeprom.write_raw.return_value = True

        assert self.api.set_application(0xff, 6, 1) is True
        assert self.mock_eeprom.write_raw.call_args[0][2] == bytearray([0x61] * NUM_CHANNELS)

    def test_set_application_ec_bit(self):
        self._expect_reg_value(*(0x11,) * 4 + (0x19,) * 4)
        self.mock_eeprom.write_raw.return_value = True

        assert self.api.set_application(0x0f, 1, 1) is True
        assert self.mock_eeprom.write_raw.call_args[0][2] == bytearray([0x11] * 4 + [0x19] * 4)

    def test_set_application_no_lane_selected(self):
        assert self.api.set_application(0, 1, 0) is False
        self.mock_eeprom.write_raw.assert_not_called()

    def test_set_application_invalid_appl_code(self):
        assert self.api.set_application(0xff, 0x10, 0) is False
        self.mock_eeprom.write_raw.assert_not_called()

    def test_set_application_flat_memory(self):
        self.api.is_flat_memory.return_value = True
        assert self.api.set_application(0xff, 1, 0) is False
        self.mock_eeprom.write_raw.assert_not_called()

    def test_set_application_missing_ap_sel_field(self):
        self.mock_eeprom.mem_map.get_field.side_effect = None
        self.mock_eeprom.mem_map.get_field.return_value = None
        assert self.api.set_application(0xff, 1, 0) is False
        self.mock_eeprom.write_raw.assert_not_called()

    def test_set_application_write_raw_failed(self):
        self._expect_reg_value(*(0x00,) * NUM_CHANNELS)
        self.mock_eeprom.write_raw.return_value = False
        assert self.api.set_application(0xff, 1, 0) is False

    def test_set_application_verify_retry_success(self):
        self.mock_eeprom.write_raw.return_value = True
        # 首次回读为旧值, 重试后读回写入值
        self.mock_eeprom.read_raw.side_effect = [
            tuple([0x00] * NUM_CHANNELS),
            tuple([0x00] * NUM_CHANNELS),
            tuple([0x10] * 4 + [0x18] * 4),
        ]
        assert self.api.set_application(0xff, 1, 0) is True

    def test_set_application_verify_failed(self):
        self.mock_eeprom.write_raw.return_value = True
        self._expect_reg_value(*(0x00,) * NUM_CHANNELS)
        assert self.api.set_application(0xff, 1, 0) is False

    def test_set_application_verify_read_error(self):
        self.mock_eeprom.write_raw.return_value = True
        self.mock_eeprom.read_raw.side_effect = Exception('read failed')
        assert self.api.set_application(0xff, 1, 0) is False

    def test_scs_apply_datapath_init_writes_full_lane_mask(self):
        self.mock_eeprom.write.return_value = True
        assert self.api.scs_apply_datapath_init(0x0f) is True
        self.mock_eeprom.write.assert_called_once_with(DPINIT_FIELD_NAME, 0xff)

    def test_scs_apply_datapath_init_zero_channel(self):
        self.mock_eeprom.write.return_value = True
        assert self.api.scs_apply_datapath_init(0) is True
        self.mock_eeprom.write.assert_called_once_with(DPINIT_FIELD_NAME, 0)

    def test_scs_apply_datapath_init_write_failed(self):
        self.mock_eeprom.write.return_value = False
        assert self.api.scs_apply_datapath_init(0xff) is False

    def test_scs_apply_datapath_init_write_error(self):
        self.mock_eeprom.write.side_effect = Exception('write failed')
        assert self.api.scs_apply_datapath_init(0xff) is False

    def test_get_all_application_raw(self):
        self._expect_reg_value(*(0x11,) * NUM_CHANNELS)
        assert self.api._get_all_application_raw() == bytearray([0x11] * NUM_CHANNELS)
        self.mock_eeprom.read_raw.assert_called_once_with(APSEL_BLOCK_START, NUM_CHANNELS)
