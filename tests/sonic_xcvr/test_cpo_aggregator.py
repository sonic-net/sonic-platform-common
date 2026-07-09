"""Behaviour tests for the CpoApi aggregator (sonic_xcvr.api.public.cpo)."""
from unittest.mock import MagicMock

import pytest

from sonic_platform_base.sonic_xcvr.api.public.cpo import CpoApi


AGGREGATOR_METHODS = [
    "get_transceiver_info",
    "get_transceiver_dom_real_value",
    "get_transceiver_threshold_info",
    "get_transceiver_dom_flags",
    "get_transceiver_status",
    "get_transceiver_status_flags",
]


def _make_cpo_api(oe_value, els_value):
    oe = MagicMock()
    els = MagicMock()
    for name in AGGREGATOR_METHODS:
        getattr(oe, name).return_value = oe_value
        getattr(els, name).return_value = els_value
    oe.xcvr_eeprom = MagicMock()
    return CpoApi(oe, els)


@pytest.mark.parametrize("method_name", AGGREGATOR_METHODS)
class TestCpoApiAggregator:
    def test_both_banks_none_returns_empty_dict(self, method_name):
        api = _make_cpo_api(None, None)
        assert getattr(api, method_name)() == {}

    def test_both_banks_empty_returns_empty_dict(self, method_name):
        api = _make_cpo_api({}, {})
        assert getattr(api, method_name)() == {}

    def test_oe_none_els_dict_returns_els_data(self, method_name):
        api = _make_cpo_api(None, {"els_temphighalarm": 80.0})
        assert getattr(api, method_name)() == {"els_temphighalarm": 80.0}

    def test_oe_dict_els_none_returns_oe_data(self, method_name):
        api = _make_cpo_api({"temphighalarm": 70.0}, None)
        assert getattr(api, method_name)() == {"temphighalarm": 70.0}

    def test_both_dicts_merge_with_els_override(self, method_name):
        api = _make_cpo_api(
            {"temphighalarm": 70.0, "vcchighalarm": 3.6},
            {"temphighalarm": 75.0, "els_temphighalarm": 80.0},
        )
        assert getattr(api, method_name)() == {
            "temphighalarm": 75.0,
            "vcchighalarm": 3.6,
            "els_temphighalarm": 80.0,
        }
