"""OE/ELS boundary tests with real memory maps and file-independent EEPROM."""
import struct
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from sonic_platform_base.sonic_xcvr.api.broadcom.bailly_oe import BaillyOeApi
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.cpo.cmis import CpoCmisApi
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoHardwareInfo, OeId
from sonic_platform_base.sonic_xcvr.cpo.oe import OeApiFactory
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpApiFactory
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.fields.broadcom import bailly


@pytest.fixture
def endpoints():
    data = bytearray(1024 * 1024)
    reader = MagicMock(side_effect=lambda offset, size: bytearray(data[offset:offset + size]))
    writer = MagicMock(return_value=True)
    device = SimpleNamespace(bank=1, base_page=4, read_eeprom=reader, write_eeprom=writer,
                             hardware_id=CpoHardwareInfo(OeId.BROADCOM_BAILLY, None))
    oe = OeApiFactory(device).create_api()
    device.bank = 0
    els = ElsfpApiFactory(device).create_api()
    # CMIS reads byte 2; automatic ELS identification reads vendor and part number.
    assert reader.call_args_list == [call(2, 1), call(129, 16), call(148, 16)]
    reader.reset_mock()
    return data, reader, writer, oe, els


def test_factory_creates_separate_oe_and_els_maps(endpoints):
    _, reader, writer, oe, els = endpoints
    assert isinstance(oe, BaillyOeApi)
    assert isinstance(oe, CpoCmisApi)
    assert oe.xcvr_eeprom is not els.xcvr_eeprom
    assert oe.xcvr_eeprom.mem_map.bank == 1
    assert [page.page for page in els.xcvr_eeprom.mem_map.pages] == [0xB4, 0xB5, 0xB6]
    from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly_oe import BaillyOeMemMap
    assert isinstance(oe.xcvr_eeprom.mem_map, BaillyOeMemMap)
    assert {0xB4, 0xB5, 0xB6}.isdisjoint({page.page for page in oe.xcvr_eeprom.mem_map.pages})
    with pytest.raises(KeyError):
        oe.xcvr_eeprom.mem_map.get_field(bailly.CPO_MODULE_MONITORS_FIELD)
    with pytest.raises(KeyError):
        els.xcvr_eeprom.mem_map.get_field(consts.TEMPERATURE_FIELD)
    assert not hasattr(oe, "get_rlm_monitor_values")
    reader.assert_not_called()
    writer.assert_not_called()


def test_oe_factory_does_not_require_an_els_base_page():
    device = SimpleNamespace(bank=7, read_eeprom=MagicMock(), write_eeprom=MagicMock(),
                             hardware_id=CpoHardwareInfo(OeId.BROADCOM_BAILLY, None))
    api = OeApiFactory(device).create_api()
    assert api.xcvr_eeprom.mem_map.bank == 7


def test_module_dom_reads_each_endpoint_own_registers(endpoints):
    data, reader, writer, oe, els = endpoints
    temp = oe.xcvr_eeprom.mem_map.get_field(consts.TEMPERATURE_FIELD).get_offset()
    voltage = oe.xcvr_eeprom.mem_map.get_field(consts.VOLTAGE_FIELD).get_offset()
    data[temp:temp + 2] = struct.pack(">h", 48 * 256)
    data[voltage:voltage + 2] = struct.pack(">H", 32500)
    # Distinct ELS0/B0 and ELS1/B4 values detect accidental sharing or wrong base_page.
    for page, temperature in ((0xB0, 10), (0xB4, 27)):
        address = page * 128 + 150
        data[address:address + 4] = struct.pack(">hH", temperature * 256, 33000)
    with patch.object(oe, "get_temperature_support", return_value=True), \
            patch.object(oe, "get_voltage_support", return_value=True):
        dom = oe.get_non_banked_transceiver_dom_real_value()
    assert dom == {"temperature": 48.0, "voltage": 3.25}
    assert all(call.args[0] < 0xB0 * 128 for call in reader.call_args_list)
    reader.reset_mock()
    dom = els.get_non_banked_elsfp_dom_real_value()
    assert dom["temperature"] == 27.0
    assert dom["voltage"] == 3.3
    assert all(call.args[0] >= 0xB4 * 128 for call in reader.call_args_list)
    writer.assert_not_called()


def test_oe_dom_contains_only_oe_measurements(endpoints):
    _, reader, _, oe, _ = endpoints
    with patch.object(oe, "get_module_temperature", return_value=48.0), \
            patch.object(oe, "get_voltage", return_value=3.25), \
            patch.object(oe, "get_tx_bias", return_value=[10.0] * 8), \
            patch.object(oe, "get_rx_power", return_value=[1.0] * 8), \
            patch.object(oe, "get_tx_power", return_value=[1.0] * 8):
        module = oe.get_non_banked_transceiver_dom_real_value()
        bank = oe.get_banked_transceiver_dom_real_value()
        assert oe.get_transceiver_dom_real_value() == {**module, **bank}
    assert len(bank) == 24
    assert not any(key.startswith(("els_", "rlm_")) for key in module.keys() | bank.keys())
    reader.assert_not_called()


def test_oe_keeps_community_software_controls():
    assert BaillyOeApi.set_lpmode is CmisApi.set_lpmode
    assert BaillyOeApi.reset is CmisApi.reset


def test_dpinit_pending_quirk(endpoints):
    oe = endpoints[3]
    assert oe.get_dpinit_pending() == {"DPInitPending%d" % lane: True for lane in range(1, 9)}


@pytest.mark.parametrize("applications", [[1, 2, 0, 3, 4, 5, 6, 7], [1] * 8, [15] * 7 + [0]])
def test_active_appsel_quirk_uses_one_selected_bank_read(endpoints, applications):
    data, reader, writer, oe, _ = endpoints
    start, size = oe._get_appl_sel_block()
    data[start:start + size] = bytearray((app << 4) | 0x09 for app in applications)
    # Exclude the cached flat-memory capability check from the AppSel I/O count.
    assert oe.is_flat_memory() is False
    reader.reset_mock()
    normal = {"ActiveAppSelLane%d" % lane: 2 for lane in range(1, 9)}
    with patch.object(CmisApi, "get_active_apsel_hostlane", return_value=normal) as parent:
        value = oe.get_active_apsel_hostlane()
    reader.assert_called_once_with(start, 8)
    writer.assert_not_called()
    if 0 in applications:
        assert value == {"ActiveAppSelLane%d" % (lane + 1): app for lane, app in enumerate(applications)}
        parent.assert_not_called()
    else:
        assert value == normal
        parent.assert_called_once_with()


@pytest.mark.parametrize("raw", [None, bytearray(7), bytearray()])
def test_active_appsel_failed_or_short_read_does_not_publish_partial_lanes(endpoints, raw):
    _, _, _, oe, _ = endpoints
    with patch.object(oe.xcvr_eeprom, "read_raw", return_value=raw), \
            patch.object(CmisApi, "get_active_apsel_hostlane") as parent:
        assert oe.get_active_apsel_hostlane() is None
    parent.assert_not_called()


def test_active_appsel_flat_memory_preserves_zero_sentinels_without_page_read(endpoints):
    _, reader, writer, oe, _ = endpoints
    with patch.object(oe, "is_flat_memory", return_value=True):
        assert oe.get_active_apsel_hostlane() == {"ActiveAppSelLane%d" % lane: 0 for lane in range(1, 9)}
    reader.assert_not_called()
    writer.assert_not_called()


def test_no_extra_power_up_info_reads(endpoints):
    _, reader, writer, oe, _ = endpoints
    reader.reset_mock()
    writer.reset_mock()
    assert oe.get_transceiver_info_after_power_up() == {}
    reader.assert_not_called()
    writer.assert_not_called()


def test_bailly_is_noncoherent_without_eeprom_detection(endpoints):
    _, reader, writer, oe, _ = endpoints
    reader.reset_mock()
    writer.reset_mock()
    with patch.object(CmisApi, "is_coherent_module", side_effect=AssertionError("Generic detection called")):
        assert oe.is_coherent_module() is False
    reader.assert_not_called()
    writer.assert_not_called()
