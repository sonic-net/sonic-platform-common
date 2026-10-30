"""Bailly OE provisioning is identical through legacy and endpoint APIs."""
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest

from sonic_platform_base.sonic_xcvr.api.broadcom.bailly import BaillyApi
from sonic_platform_base.sonic_xcvr.api.broadcom.bailly_oe import BaillyOeApi
from sonic_platform_base.sonic_xcvr.api.broadcom.bailly_elsfp import BaillyElsfpApi
from sonic_platform_base.sonic_xcvr.codes.broadcom.bailly import BaillyCodes
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly import BaillyMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly_oe import BaillyOeMemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom


@pytest.fixture(params=[(BaillyApi, BaillyMemMap), (BaillyOeApi, BaillyOeMemMap)])
def endpoint(request):
    api_class, map_class = request.param
    data = bytearray(1024 * 1024)
    reader = MagicMock(side_effect=lambda offset, size: data[offset:offset + size])

    def write(offset, size, value):
        data[offset:offset + size] = value[:size]
        return True

    writer = MagicMock(side_effect=write)
    mem_map = map_class(BaillyCodes, bank=2)
    api = api_class(XcvrEeprom(reader, writer, mem_map))
    reader.reset_mock()
    module = api_class.__module__
    with patch(module + '.time.sleep') as sleep:
        yield SimpleNamespace(api=api, data=data, reader=reader, writer=writer, sleep=sleep)


@pytest.mark.parametrize('code,ec,expected', [
    (1, 0, [0x10] * 4 + [0x18] * 4),
    (1, 1, [0x11] * 4 + [0x19] * 4),
    (6, 0, [0x60] * 8),
    (6, 1, [0x61] * 8),
    (15, 0, [0xF0] * 4 + [0xF8] * 4),
])
def test_application_writes_entire_selected_bank(endpoint, code, ec, expected):
    api = endpoint.api
    start = api.xcvr_eeprom.mem_map.get_field(consts.STAGED_CTRL_APSEL_FIELD + '_0_1').get_offset()
    assert api.set_application(0x01, code, ec)
    endpoint.writer.assert_called_once_with(start, 8, bytearray(expected))
    assert endpoint.data[start:start + 8] == bytearray(expected)
    assert all(start <= c.args[0] < start + 8 for c in endpoint.reader.call_args_list
               if c.args != (2, 1))
    # No writes to another bank or to an ELS page.
    assert endpoint.data[:start] == bytearray(start)
    assert endpoint.data[start + 8:] == bytearray(len(endpoint.data) - start - 8)
    endpoint.sleep.assert_not_called()


@pytest.mark.parametrize('channel,code', [(0, 1), (0x100, 1), (0xFF, -1), (0xFF, 16)])
def test_invalid_application_does_not_touch_hardware(endpoint, channel, code):
    assert not endpoint.api.set_application(channel, code)
    endpoint.reader.assert_not_called()
    endpoint.writer.assert_not_called()


def test_application_field_absent_returns_failure(endpoint):
    with patch.object(endpoint.api.xcvr_eeprom.mem_map, 'get_field', side_effect=KeyError('absent')):
        assert not endpoint.api.set_application(0xFF, 1)
    endpoint.writer.assert_not_called()


def test_non_contiguous_application_block_returns_failure(endpoint):
    fields = [SimpleNamespace(get_offset=lambda: 100),
              SimpleNamespace(get_offset=lambda: 108, get_size=lambda: 1)]
    with patch.object(endpoint.api, '_get_appl_sel_field', side_effect=fields):
        assert not endpoint.api.set_application(0xFF, 1)
    endpoint.writer.assert_not_called()


def test_unreadable_application_block_does_not_write(endpoint):
    endpoint.reader.return_value = None
    endpoint.reader.side_effect = lambda offset, size: bytearray([0]) if offset == 2 else None
    assert not endpoint.api.set_application(0xFF, 1)
    endpoint.writer.assert_not_called()


def test_application_write_failure_is_reported(endpoint):
    endpoint.writer.side_effect = OSError('test write failure')
    assert not endpoint.api.set_application(0xFF, 1)
    endpoint.sleep.assert_not_called()


def test_application_readback_retries_then_succeeds(endpoint):
    expected = bytearray([0x10] * 4 + [0x18] * 4)
    with patch.object(endpoint.api, '_get_all_application_raw',
                      side_effect=[bytearray(8), None, bytearray(8), expected]) as reads:
        assert endpoint.api.set_application(0xFF, 1)
    assert reads.call_count == 4
    assert endpoint.sleep.call_args_list == [call(0.1), call(0.1)]


def test_application_readback_failure_is_bounded(endpoint):
    with patch.object(endpoint.api, '_get_all_application_raw', return_value=bytearray(8)) as reads:
        assert not endpoint.api.set_application(0xFF, 1)
    assert reads.call_count == 4
    assert endpoint.sleep.call_args_list == [call(0.1)] * 3


@pytest.mark.parametrize('channel,value', [(0, 0), (1, 0xFF), (0x80, 0xFF), (0xFF, 0xFF)])
def test_dpinit_applies_bank_wide_and_does_not_verify_self_clearing_bit(endpoint, channel, value):
    field = endpoint.api.xcvr_eeprom.mem_map.get_field(consts.STAGED_CTRL_APPLY_DPINIT_FIELD + '_0')
    assert endpoint.api.scs_apply_datapath_init(channel)
    endpoint.writer.assert_called_once_with(field.get_offset(), 1, bytearray([value]))
    endpoint.reader.assert_not_called()
    endpoint.sleep.assert_called_once_with(0.01)


@pytest.mark.parametrize('error', [False, OSError('test write failure')])
def test_dpinit_write_failure_does_not_report_success(endpoint, error):
    if isinstance(error, Exception):
        endpoint.writer.side_effect = error
    else:
        endpoint.writer.side_effect = None
        endpoint.writer.return_value = False
    assert not endpoint.api.scs_apply_datapath_init(0xFF)
    endpoint.sleep.assert_not_called()


def test_els_does_not_acquire_oe_provisioning_overrides():
    assert 'set_application' not in BaillyElsfpApi.__dict__
    assert 'scs_apply_datapath_init' not in BaillyElsfpApi.__dict__
