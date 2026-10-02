import math
import struct

import pytest

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

    eeprom.put_str(INFO_PAGE, 129, 16, "BAILLY VENDOR")
    eeprom.put(INFO_PAGE, 145, "3B", 0x00, 0x90, 0xFB)
    eeprom.put_str(INFO_PAGE, 148, 16, "RLM-PN")
    eeprom.put_str(INFO_PAGE, 164, 2, "A1")
    eeprom.put_str(INFO_PAGE, 166, 16, "SN123")
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
        assert info["manufacturer"] == "BAILLY VENDOR"
        assert info["model"] == "RLM-PN"
        assert info["serial"] == "SN123"
        assert info["vendor_rev"] == "A1"
        assert info["vendor_oui"] == "00-90-fb"
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

    def test_set_lpmode_updates_only_control_bit(self, api, eeprom):
        eeprom.put(CONTROL_PAGE, 132, "B", 0xF0)
        assert api.set_lpmode(True)
        assert eeprom.byte(CONTROL_PAGE, 132) == 0xF1
        assert api.set_lpmode(False)
        assert eeprom.byte(CONTROL_PAGE, 132) == 0xF0

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

    def test_set_per_lane_enable_updates_selected_lasers(self, api, eeprom):
        eeprom.put(CONTROL_PAGE, 133, "B", 0b00000001)
        assert api.set_per_lane_enable(0b11110000, False)
        assert eeprom.byte(CONTROL_PAGE, 133) == 0b11110001
        assert api.set_per_lane_enable(0b00110001, True)
        assert eeprom.byte(CONTROL_PAGE, 133) == 0b11000000
        assert {offset for offset, _ in eeprom.writes} == {addr(CONTROL_PAGE, 133)}

    def test_set_per_lane_enable_upper_lasers(self, api, eeprom):
        program_rlm(eeprom, laser_count=16)
        assert api.set_per_lane_enable(0x0300, False)
        assert eeprom.byte(CONTROL_PAGE, 133) == 0
        assert eeprom.byte(CONTROL_PAGE, 134) == 0b11
        assert {offset for offset, _ in eeprom.writes} == {addr(CONTROL_PAGE, 134)}

    def test_set_per_lane_enable_rejects_lasers_beyond_count(self, api, eeprom):
        with pytest.raises(ValueError):
            api.set_per_lane_enable(0x100, False)
        assert eeprom.writes == []

    def test_read_failures(self, api, eeprom):
        eeprom.fail_reads = True
        assert api.get_elsfp_info() is None
        assert api.get_elsfp_dom_real_value() is None
        assert api.get_elsfp_threshold_info() is None
        assert api.get_elsfp_status() is None
        assert api.set_lpmode(True) is False
        assert api.set_per_lane_enable(0x1, False) is False
        assert eeprom.writes == []

    def test_reset_is_not_supported(self, api, eeprom):
        with pytest.raises(NotImplementedError):
            api.reset()
        assert eeprom.writes == []
