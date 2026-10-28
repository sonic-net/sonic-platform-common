import math
import struct

import pytest
from unittest.mock import patch

from sonic_platform_base.sonic_xcvr.api.broadcom.bailly_elsfp import BaillyElsfpApi
from sonic_platform_base.sonic_xcvr.api.public.elsfp import ElsfpApi
from sonic_platform_base.sonic_xcvr.codes.broadcom.bailly import BaillyCodes
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly import BaillyElsfpMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom

BASE_PAGE = 4
CONTROL_PAGE = 0xB0 + BASE_PAGE
INFO_PAGE = 0xB1 + BASE_PAGE
THRESHOLD_PAGE = 0xB2 + BASE_PAGE


def addr(page, offset):
    return page * 128 + offset


class FakeEeprom:
    def __init__(self):
        self.data = bytearray(256 * 128)
        self.writes = []
        self.fail_reads = False

    def read(self, offset, size):
        if self.fail_reads:
            return None
        return bytearray(self.data[offset:offset + size])

    def write(self, offset, size, buf):
        self.writes.append((offset, bytes(buf[:size])))
        self.data[offset:offset + size] = buf[:size]
        return True

    def put(self, page, offset, fmt, *values):
        packed = struct.pack(fmt, *values)
        start = addr(page, offset)
        self.data[start:start + len(packed)] = packed

    def put_str(self, page, offset, size, value):
        start = addr(page, offset)
        self.data[start:start + size] = value.ljust(size).encode()

    def byte(self, page, offset):
        return self.data[addr(page, offset)]


def program_rlm(eeprom, laser_count=8):
    eeprom.put(CONTROL_PAGE, 128, "B", 128)                    # CPO Bailly
    eeprom.put(CONTROL_PAGE, 129, "B", 0x12)                   # revision 1.2
    eeprom.put(CONTROL_PAGE, 130, "B", 0x10 | (laser_count - 1))
    eeprom.put(CONTROL_PAGE, 150, ">h", int(25.5 * 256))       # temperature
    eeprom.put(CONTROL_PAGE, 152, ">H", 33000)                 # 3.3 V
    for laser in range(16):
        eeprom.put(CONTROL_PAGE, 154 + 2 * laser, ">H", 25000 + laser)   # mA * 100
        eeprom.put(CONTROL_PAGE, 186 + laser, "B", 150 + laser)          # V * 100
        eeprom.put(CONTROL_PAGE, 203 + 2 * laser, ">H", 7000 + laser)    # mW * 100

    eeprom.put_str(INFO_PAGE, 129, 16, "TEST VENDOR")
    eeprom.put(INFO_PAGE, 145, "3B", 0x02, 0x00, 0x00)
    eeprom.put_str(INFO_PAGE, 148, 16, "TEST-PART")
    eeprom.put_str(INFO_PAGE, 164, 2, "A1")
    eeprom.put_str(INFO_PAGE, 166, 16, "TEST-SN-0001")
    eeprom.put_str(INFO_PAGE, 182, 8, "260102AB")
    eeprom.put(INFO_PAGE, 200, "B", 48)                        # 12 W

    eeprom.put(THRESHOLD_PAGE, 162, ">hhhh", 75 * 256, -5 * 256, 70 * 256, 0)
    eeprom.put(THRESHOLD_PAGE, 170, ">HHHH", 36300, 29700, 34650, 31350)
    eeprom.put(THRESHOLD_PAGE, 178, ">HHHH", 20000, 0, 15000, 100)
    eeprom.put(THRESHOLD_PAGE, 186, ">HH", 40000, 35000)


@pytest.fixture
def eeprom():
    fake = FakeEeprom()
    program_rlm(fake)
    return fake


@pytest.fixture
def api(eeprom):
    mem_map = BaillyElsfpMemMap(BaillyCodes, base_page=BASE_PAGE)
    return BaillyElsfpApi(XcvrEeprom(eeprom.read, eeprom.write, mem_map))


class TestBaillyElsfpMemMap:
    def test_only_rlm_pages_are_mapped_at_base_page(self):
        mem_map = BaillyElsfpMemMap(BaillyCodes, base_page=BASE_PAGE)
        assert [page.page for page in mem_map.pages] == [CONTROL_PAGE, INFO_PAGE, THRESHOLD_PAGE]
        assert mem_map.base_page == BASE_PAGE
        assert mem_map.bank == 0
        with pytest.raises(KeyError):
            mem_map.get_field(consts.ID_FIELD)


class TestBaillyElsfpApi:
    def test_is_public_elsfp_api(self, api):
        assert isinstance(api, ElsfpApi)

    def test_lane_count(self, api, eeprom):
        assert api.get_lane_count() == 8
        program_rlm(eeprom, laser_count=16)
        assert api.get_lane_count() == 16

    def test_elsfp_info(self, api):
        info = api.get_elsfp_info()
        assert info["type"] == "CPO Bailly"
        assert info["hardware_rev"] == "1.2"
        assert info["manufacturer"] == "TEST VENDOR"
        assert info["model"] == "TEST-PART"
        assert info["serial"] == "TEST-SN-0001"
        assert info["vendor_rev"] == "A1"
        assert info["vendor_oui"] == "02-00-00"
        assert info["vendor_date"] == "2026-01-02 AB"
        assert info["ext_identifier"] == "12.0W Max"
        assert info["lane_count"] == 8
        assert info["control_mode"] == "N/A"

    def test_module_monitors(self, api):
        assert api.get_module_temperature() == 25.5
        assert api.get_module_voltage() == 3.3
        with pytest.raises(NotImplementedError):
            api.get_icc_monitor()

    def test_per_lane_monitors_use_public_names_and_units(self, api):
        bias = api.get_per_lane_bias_current_monitor()
        power = api.get_per_lane_opt_power_monitor()
        voltage = api.get_per_lane_voltage_monitor()
        assert sorted(bias) == ["BiasCurrentMonitor%d" % lane for lane in range(1, 9)]
        assert bias["BiasCurrentMonitor1"] == pytest.approx(0.25)
        assert power["OptPowerMonitor2"] == pytest.approx(70.01)
        assert voltage["VoltageMonitor8"] == pytest.approx(1.57)

    def test_dom_real_value(self, api):
        dom = api.get_elsfp_dom_real_value()
        assert dom["temperature"] == 25.5
        assert dom["voltage"] == 3.3
        assert dom["icc"] == "N/A"
        assert dom["laser_bias_current_lane1"] == 250.0
        assert dom["optical_power_lane1"] == round(10 * math.log10(70.0), 3)
        assert dom["voltage_lane8"] == 1.57
        assert "laser_bias_current_lane9" not in dom

    def test_threshold_info(self, api):
        thresholds = api.get_elsfp_threshold_info()
        assert thresholds["temperature_alarm_high"] == 75.0
        assert thresholds["temperature_alarm_low"] == -5.0
        assert thresholds["voltage_warn_low"] == 3.135
        assert thresholds["laser_bias_alarm_high"] == 400.0
        assert thresholds["laser_bias_warn_high"] == 350.0
        assert thresholds["optical_power_alarm_high"] == round(10 * math.log10(200.0), 3)
        assert thresholds["optical_power_alarm_low"] == float("-inf")
        assert thresholds["optical_power_warn_low"] == 0.0
        assert "laser_bias_alarm_low" not in thresholds

    @pytest.mark.parametrize("status_byte, state", [
        (0b10, "ModuleLowPwr"),
        (0b00, "ModuleReady"),
    ])
    def test_module_state(self, api, eeprom, status_byte, state):
        eeprom.put(CONTROL_PAGE, 131, "B", status_byte)
        assert api.get_module_state() == state
        assert api.get_elsfp_status()["module_state"] == state

    def test_lane_enable_and_state(self, api, eeprom):
        eeprom.put(CONTROL_PAGE, 133, "B", 0b00000101)   # lasers 0 and 2 disabled
        eeprom.put(CONTROL_PAGE, 135, "B", 0b11111010)   # lasers 0 and 2 inactive
        assert api.get_per_lane_enable() == [0, 1, 0, 1, 1, 1, 1, 1]
        state = api.get_per_lane_state()
        assert state["LaneState1"] == "Inactive"
        assert state["LaneState2"] == "Active"
        status = api.get_elsfp_status()
        assert status["enable_lane1"] is False
        assert status["enable_lane2"] is True
        assert status["state_lane3"] == "Inactive"

    def test_read_failures(self, api, eeprom):
        eeprom.fail_reads = True
        assert api.get_elsfp_info() is None
        assert api.get_elsfp_dom_real_value() is None
        assert api.get_elsfp_threshold_info() is None
        assert api.get_elsfp_status() is None
        assert eeprom.writes == []

    @pytest.mark.parametrize("control", [
        lambda api: api.reset(),
        lambda api: api.set_lpmode(True),
        lambda api: api.set_lpmode(False),
        lambda api: api.set_per_lane_enable(0x1, False),
        lambda api: api.set_per_lane_enable(0xFF, True),
    ])
    def test_controls_are_not_supported(self, api, eeprom, control):
        with pytest.raises(NotImplementedError):
            control(api)
        assert eeprom.writes == []


class TestBaillyElsfpSeparatedAggregates:
    def test_dom_has_rlm_tec_current_and_wavelength(self, api, eeprom):
        eeprom.put(CONTROL_PAGE, 250, ">h", 32767)
        assert api.get_elsfp_dom_real_value()["tec_current"] == 100.0
        assert api.get_elsfp_info()["laser_wavelength_grid"] == "DR4"

    @pytest.mark.parametrize("mask", [0, 0x55, 0xAA, 0xFF])
    def test_module_flags_read_rlm_not_oe_lower_memory(self, api, eeprom, mask):
        eeprom.put(0, 9, "B", (~mask) & 0xFF)
        eeprom.put(CONTROL_PAGE, 137, "B", mask)
        flags = api.get_non_banked_elsfp_dom_flags()
        names = ["temperature_alarm_high", "temperature_alarm_low", "temperature_warn_high", "temperature_warn_low",
                 "voltage_alarm_high", "voltage_alarm_low", "voltage_warn_high", "voltage_warn_low"]
        assert flags == {name: bool(mask & (1 << bit)) for bit, name in enumerate(names)}

    def test_flags_do_not_expose_unverified_per_laser_bits(self, api, eeprom):
        eeprom.put(CONTROL_PAGE, 138, "4B", 0xFF, 0xFF, 0xFF, 0xFF)
        with patch.object(api, "get_lane_count", side_effect=AssertionError("Per-laser alarms requested")):
            for method in (api.get_elsfp_dom_flags, api.get_elsfp_status_flags):
                flags = method()
                assert flags["temperature_alarm_high"] is False
                assert not any("_lane" in key for key in flags)
            assert api.get_banked_elsfp_dom_flags() == {}
            assert api.get_banked_elsfp_status_flags() == {}

    def test_interrupt_is_reported_by_els_status_and_flags(self, api, eeprom):
        eeprom.put(CONTROL_PAGE, 131, "B", 0x01)
        assert api.get_elsfp_status()["interrupt_status"] == "Interrupt event cleared"
        flags = api.get_elsfp_status_flags()
        assert flags["interrupt_status"] == "Interrupt event cleared"
        assert flags["temperature_alarm_high"] is False

    @pytest.mark.parametrize("method", ["get_non_banked_elsfp_dom_real_value", "get_elsfp_dom_flags",
                                        "get_elsfp_status_flags"])
    def test_new_aggregates_propagate_read_failure(self, api, eeprom, method):
        eeprom.fail_reads = True
        assert getattr(api, method)() is None
        assert eeprom.writes == []


class TestBaillyElsfpLegacyAdapters:
    @pytest.mark.parametrize("failed", [False, True])
    @pytest.mark.parametrize("method", [
        "get_rlm_temperature", "get_rlm_vendor_info", "get_rlm_laser_current",
        "get_rlm_laser_voltage", "get_rlm_laser_power", "get_rlm_monitor_values",
        "get_rlm_thresholds", "get_rlm_flags", "get_rlm_status", "get_rlm_info",
    ])
    def test_raw_readers_match_legacy_api(self, api, eeprom, method, failed):
        from sonic_platform_base.sonic_xcvr.api.broadcom.bailly import BaillyApi
        from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly import BaillyMemMap

        legacy_map = BaillyMemMap(BaillyCodes, base_page=BASE_PAGE)
        legacy = BaillyApi(XcvrEeprom(eeprom.read, eeprom.write, legacy_map))
        eeprom.put(CONTROL_PAGE, 131, "B", 0x03)
        eeprom.put(CONTROL_PAGE, 137, "B", 0xA5)
        eeprom.put(THRESHOLD_PAGE, 128, "B", 1)
        eeprom.fail_reads = failed
        assert getattr(api, method)() == getattr(legacy, method)()
        assert eeprom.writes == []

    def test_temperature_delegates_without_new_register_read(self, api):
        with patch.object(api, "get_rlm_temperature", return_value=31.125) as legacy:
            with patch.object(api.xcvr_eeprom, "read", side_effect=AssertionError("Extra hardware read")):
                assert api.get_module_temperature() == 31.125
        legacy.assert_called_once_with()

    @pytest.mark.parametrize("count", [8, 16])
    @pytest.mark.parametrize("raw_method, public_method, raw_key, public_key, factor", [
        ("get_rlm_laser_current", "get_per_lane_bias_current_monitor",
         "Laser{}CurrentMonitor", "BiasCurrentMonitor", 0.001),
        ("get_rlm_laser_power", "get_per_lane_opt_power_monitor",
         "Laser{}OpticalPowerMonitor", "OptPowerMonitor", 1),
        ("get_rlm_laser_voltage", "get_per_lane_voltage_monitor",
         "Laser{}VoltageMonitor", "VoltageMonitor", 1),
    ])
    def test_monitor_adapters_rename_and_convert(
            self, api, count, raw_method, public_method, raw_key, public_key, factor):
        raw = {raw_key.format(laser): 100 + laser for laser in range(16)}
        with patch.object(api, raw_method, return_value=raw) as legacy:
            with patch.object(api, "get_lane_count", return_value=count):
                with patch.object(api.xcvr_eeprom, "read", side_effect=AssertionError("Extra hardware read")):
                    values = getattr(api, public_method)()
        assert values == pytest.approx({public_key + str(laser + 1): (100 + laser) * factor
                                       for laser in range(count)})
        assert len(raw) == 16
        legacy.assert_called_once_with()

    def test_module_values_adapt_legacy_dictionary(self, api):
        raw = {"els_temperature": 26.5, "els_voltage": 3.2, "rlm_tec_current": 12.5}
        with patch.object(api, "get_rlm_monitor_values", return_value=raw):
            with patch.object(api.xcvr_eeprom, "read", side_effect=AssertionError("Extra hardware read")):
                assert api.get_module_voltage() == 3.2
                assert api.get_non_banked_elsfp_dom_real_value() == {
                    "temperature": 26.5, "voltage": 3.2, "tec_current": 12.5,
                }
        assert raw == {"els_temperature": 26.5, "els_voltage": 3.2, "rlm_tec_current": 12.5}

    def test_partial_raw_module_values_do_not_become_successful_dom(self, api):
        from sonic_platform_base.sonic_xcvr.fields.broadcom import bailly

        with patch.object(api.xcvr_eeprom, "read", return_value={bailly.MODULE_TEMPERATURE_MONITOR: 26.5}):
            assert api.get_rlm_monitor_values() == {
                "els_temperature": 26.5, "els_voltage": None, "rlm_tec_current": None,
            }
            assert api.get_non_banked_elsfp_dom_real_value() is None

    @pytest.mark.parametrize("method, raw_method, result", [
        ("get_per_lane_bias_current_monitor", "get_rlm_laser_current", {"Laser0CurrentMonitor": None}),
        ("get_per_lane_opt_power_monitor", "get_rlm_laser_power", {}),
        ("get_per_lane_voltage_monitor", "get_rlm_laser_voltage", None),
        ("get_elsfp_threshold_info", "get_rlm_thresholds", {"els_temphighalarm": 75.0}),
        ("get_non_banked_elsfp_dom_flags", "get_rlm_flags", {}),
        ("get_module_state", "get_rlm_status", None),
    ])
    def test_incomplete_legacy_values_propagate_failure(self, api, method, raw_method, result):
        with patch.object(api, raw_method, return_value=result):
            with patch.object(api, "get_lane_count", return_value=8):
                assert getattr(api, method)() is None

    @pytest.mark.parametrize("control", [0, 1])
    def test_info_wraps_legacy_and_preserves_control_readback(self, api, eeprom, control):
        from sonic_platform_base.sonic_xcvr.fields.broadcom import bailly

        eeprom.put(THRESHOLD_PAGE, 128, "B", control)
        raw = api.get_rlm_info()
        with patch.object(api, "get_rlm_info", return_value=raw) as legacy:
            with patch.object(api.xcvr_eeprom, "read", side_effect=AssertionError("Extra hardware read")):
                info = api.get_elsfp_info()
        assert info["manufacturer"] == "TEST VENDOR"
        assert info["lane_count"] == 8
        assert info["rlm_laser_lpmode_control"] == raw["laser_power_mode"][bailly.LASER_POWER_MODE_CONTROL_BITS_FIELD]
        assert eeprom.writes == []
        legacy.assert_called_once_with()

    def test_legacy_module_status_does_not_replace_laser_status(self, api, eeprom):
        eeprom.put(CONTROL_PAGE, 133, "B", 0x01)
        eeprom.put(CONTROL_PAGE, 135, "B", 0x02)
        with patch.object(api, "get_rlm_status", return_value={
                "els_module_low_power_state": "Unused", "els_interrupt_status": "Unused"}):
            assert api.get_per_lane_enable()[:2] == [0, 1]
            assert api.get_per_lane_state()["LaneState1"] == "Inactive"
            assert api.get_per_lane_state()["LaneState2"] == "Active"


class TestBaillyElsfpThresholdAdapters:
    @pytest.mark.parametrize("method, expected", [
        ("get_laser_bias_high_alarm", 0.4),
        ("get_laser_bias_high_warn", 0.35),
        ("get_optical_power_high_alarm", 200.0),
        ("get_optical_power_low_alarm", 0.0),
        ("get_optical_power_high_warn", 150.0),
        ("get_optical_power_low_warn", 1.0),
    ])
    def test_leaf_threshold_reads_use_legacy_rlm_values(self, api, method, expected):
        assert getattr(api, method)() == pytest.approx(expected)

    @pytest.mark.parametrize("method", [
        "get_laser_bias_high_alarm", "get_laser_bias_high_warn",
        "get_optical_power_high_alarm", "get_optical_power_low_alarm",
        "get_optical_power_high_warn", "get_optical_power_low_warn",
    ])
    @pytest.mark.parametrize("raw", [None, {}])
    def test_missing_threshold_values_propagate_failure(self, api, method, raw):
        with patch.object(api, "get_rlm_thresholds", return_value=raw) as legacy:
            with patch.object(api.xcvr_eeprom, "read", side_effect=AssertionError("Extra EEPROM read")):
                assert getattr(api, method)() is None
        legacy.assert_called_once_with()

    @pytest.mark.parametrize("method", [
        "get_laser_bias_low_alarm", "get_laser_bias_low_warn", "get_module_fault_cause",
    ])
    def test_unavailable_values_report_not_implemented_without_access(self, api, eeprom, method):
        with patch.object(api.xcvr_eeprom, "read", side_effect=AssertionError("Unsupported EEPROM read")):
            with pytest.raises(NotImplementedError):
                getattr(api, method)()
        assert eeprom.writes == []
