"""Optional ELS operations share one contract across platform backends."""

from unittest.mock import Mock

import pytest

from sonic_platform_base.sonic_xcvr.api.broadcom.bailly import BaillyApi
from sonic_platform_base.sonic_xcvr.api.public.elsfp import ElsfpApi
from sonic_platform_base.sonic_xcvr.api.public.elsfp_base import ElsfpApiBase
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoBase
from sonic_platform_base.sonic_xcvr.fields import consts


class OtherPlatformApi(ElsfpApiBase):
    pass


@pytest.mark.parametrize("api_class", [OtherPlatformApi, BaillyApi])
@pytest.mark.parametrize("method, args", [
    ("set_elsfp_lpmode", (True,)),
    ("reset_elsfp", ()),
    ("set_per_lane_enable", (0b11, False)),
    ("get_per_lane_state", ()),
    ("get_elsfp_module_state", ()),
])
def test_unsupported_els_operations_do_not_touch_hardware(api_class, method, args):
    eeprom = Mock()
    api = api_class(eeprom)
    # CMIS initialization may read Flat_mem; the optional operation must not.
    eeprom.read.reset_mock()
    assert isinstance(api, ElsfpApiBase)
    with pytest.raises(NotImplementedError, match="ELS.*not implemented"):
        getattr(api, method)(*args)
    eeprom.read.assert_not_called()
    eeprom.write.assert_not_called()


@pytest.mark.parametrize("method", [
    "get_elsfp_info", "get_elsfp_status", "get_elsfp_dom_real_value",
    "get_elsfp_threshold_info", "get_per_lane_bias_current_monitor",
    "get_per_lane_opt_power_monitor", "get_per_lane_voltage_monitor",
])
def test_unimplemented_reads_have_public_placeholders(method):
    with pytest.raises(NotImplementedError, match="ELS"):
        getattr(OtherPlatformApi(None), method)()


@pytest.mark.parametrize("api_class, supported", [
    (OtherPlatformApi, False), (BaillyApi, False), (ElsfpApi, True),
])
def test_lane_enable_support_query_does_not_write(api_class, supported):
    eeprom = Mock()
    api = api_class(eeprom)
    eeprom.read.reset_mock()
    assert api.supports_per_lane_enable() is supported
    eeprom.read.assert_not_called()
    eeprom.write.assert_not_called()


def test_platform_can_implement_optional_controls():
    class SupportedApi(OtherPlatformApi):
        def set_per_lane_enable(self, lane_mask, enabled):
            return self.xcvr_eeprom.write("platform-lane-enable", (lane_mask, enabled))

        def reset_elsfp(self):
            return self.xcvr_eeprom.write("platform-els-reset", True)

    eeprom = Mock()
    eeprom.write.return_value = True
    api = SupportedApi(eeprom)
    assert api.supports_per_lane_enable() is True
    assert api.set_per_lane_enable(0b101, False) is True
    eeprom.write.assert_called_with("platform-lane-enable", (0b101, False))
    assert api.reset_elsfp() is True
    eeprom.write.assert_called_with("platform-els-reset", True)


def test_public_els_module_state_uses_existing_els_reader():
    eeprom = Mock()
    eeprom.read.return_value = "ModuleReady"
    assert ElsfpApi(eeprom).get_elsfp_module_state() == "ModuleReady"
    eeprom.read.assert_called_once_with(consts.MODULE_STATE)


@pytest.mark.parametrize("method, args", [("set_elsfp_lpmode", (True,)), ("reset_elsfp", ())])
def test_public_els_api_inherits_optional_control_stubs(method, args):
    with pytest.raises(NotImplementedError, match="ELS.*not implemented"):
        getattr(ElsfpApi(Mock()), method)(*args)


def test_cpo_page_mapping_is_explicitly_unsupported_by_default():
    cpo = CpoBase(None, Mock(), Mock())
    with pytest.raises(NotImplementedError, match="ELS EEPROM page mapping"):
        cpo.get_els_base_page()
