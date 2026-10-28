import pytest
from mock import MagicMock

from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoBase, CpoHardwareInfo, OeId
from sonic_platform_base.sonic_xcvr.cpo.cpo_optoe_base import OptoeOeBase, OptoeElsfpBase
from sonic_platform_base.sonic_xcvr.cpo.oe import OeBase
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpBase

# These tests don't depend on the specific ids (the factory's create methods
# are mocked); any valid id will do.
SOME_OE_ID = OeId.BROADCOM_DAVISSON
SOME_ELSFP_ID = None

# Low-power mode and reset hooks that the CPO base classes leave to platforms,
# as (method_name, args).
PLATFORM_HOOKS = [
    ("get_reset_status", ()),
    ("reset", ()),
    ("get_lpmode", ()),
    ("set_lpmode", (True,)),
]

# Tx-disable is a hook of the CPO virtual module only.
CPO_PLATFORM_HOOKS = PLATFORM_HOOKS + [
    ("get_tx_disable", ()),
    ("tx_disable", (True,)),
]


class TestOeBase(object):
    @pytest.mark.parametrize("method_name, args", PLATFORM_HOOKS)
    def test_platform_hooks_raise(self, method_name, args):
        oe = OeBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))

        with pytest.raises(NotImplementedError):
            getattr(oe, method_name)(*args)

    def test_get_api_refreshes_when_none(self):
        oe = OeBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        oe._api_factory.create_api = MagicMock(return_value=fake_api)

        result = oe.get_api()

        oe._api_factory.create_api.assert_called_once_with()
        assert result is fake_api

    def test_get_api_cached(self):
        oe = OeBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        oe._api_factory.create_api = MagicMock(return_value=fake_api)

        # First call populates the cache, second call should reuse it.
        first = oe.get_api()
        second = oe.get_api()

        oe._api_factory.create_api.assert_called_once_with()
        assert first is second is fake_api


class TestElsfpBase(object):
    @pytest.mark.parametrize("method_name, args", PLATFORM_HOOKS)
    def test_platform_hooks_raise(self, method_name, args):
        elsfp = ElsfpBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))

        with pytest.raises(NotImplementedError):
            getattr(elsfp, method_name)(*args)

    def test_get_api_refreshes_when_none(self):
        elsfp = ElsfpBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        elsfp._api_factory.create_api = MagicMock(return_value=fake_api)

        result = elsfp.get_api()

        elsfp._api_factory.create_api.assert_called_once_with()
        assert result is fake_api

    def test_get_api_cached(self):
        elsfp = ElsfpBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        elsfp._api_factory.create_api = MagicMock(return_value=fake_api)

        first = elsfp.get_api()
        second = elsfp.get_api()

        elsfp._api_factory.create_api.assert_called_once_with()
        assert first is second is fake_api


@pytest.mark.parametrize("endpoint_class", [OeBase, ElsfpBase])
@pytest.mark.parametrize("method_name, args", PLATFORM_HOOKS)
def test_endpoint_hooks_can_be_overridden_without_creating_api(endpoint_class, method_name, args):
    implementation = MagicMock(return_value=True)

    def hook(self, *values):
        return implementation(*values)

    platform_class = type("PlatformEndpoint", (endpoint_class,), {method_name: hook})
    endpoint = platform_class(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
    endpoint._api_factory.create_api = MagicMock()

    assert getattr(endpoint, method_name)(*args) is True
    implementation.assert_called_once_with(*args)
    endpoint._api_factory.create_api.assert_not_called()


class TestCpoBase(object):
    def test_init(self):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        oe = OeBase(hardware_id)
        elsfp = ElsfpBase(hardware_id)

        cpo = CpoBase(hardware_id, oe, elsfp)

        assert cpo.hardware_id is hardware_id
        assert cpo.oe is oe
        assert cpo.elsfp is elsfp

    def test_get_xcvr_api_returns_oe_api(self):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        oe = OeBase(hardware_id)
        elsfp = ElsfpBase(hardware_id)
        oe_api = MagicMock()
        oe.get_api = MagicMock(return_value=oe_api)

        cpo = CpoBase(hardware_id, oe, elsfp)

        assert cpo.get_xcvr_api() is oe_api
        oe.get_api.assert_called_with()

    @pytest.mark.parametrize("method_name, args", CPO_PLATFORM_HOOKS)
    def test_platform_hooks_raise(self, method_name, args):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        oe, elsfp = OeBase(hardware_id), ElsfpBase(hardware_id)
        oe.get_api = MagicMock()
        elsfp.get_api = MagicMock()
        cpo = CpoBase(hardware_id, oe, elsfp)

        with pytest.raises(NotImplementedError):
            getattr(cpo, method_name)(*args)
        # The hooks do not fall back to the software path.
        oe.get_api.assert_not_called()
        elsfp.get_api.assert_not_called()

    def test_platform_hooks_can_be_implemented(self):
        class PlatformCpo(CpoBase):
            def set_lpmode(self, lpmode):
                return "platform"

        oe_api = MagicMock()
        cpo = PlatformCpo(None, MagicMock(get_api=MagicMock(return_value=oe_api)), MagicMock())

        assert cpo.set_lpmode(True) == "platform"
        oe_api.set_lpmode.assert_not_called()


class StubOptoeOe(OptoeOeBase):
    def get_eeprom_path(self):
        return "/unused-eeprom"


class StubOptoeElsfp(OptoeElsfpBase):
    def get_eeprom_path(self):
        return "/unused-eeprom"


@pytest.mark.parametrize("endpoint_class", [StubOptoeOe, StubOptoeElsfp])
@pytest.mark.parametrize("method_name, args", [
    ("set_lpmode", (True,)), ("set_lpmode", (False,)), ("reset", ()),
])
@pytest.mark.parametrize("result", [True, False])
def test_optoe_controls_forward_arguments_and_result(endpoint_class, method_name, args, result):
    endpoint = endpoint_class(CpoHardwareInfo(SOME_OE_ID, SOME_ELSFP_ID))
    api = MagicMock()
    getattr(api, method_name).return_value = result
    endpoint._api_factory.create_api = MagicMock(return_value=api)

    assert getattr(endpoint, method_name)(*args) is result
    getattr(api, method_name).assert_called_once_with(*args)


@pytest.mark.parametrize("endpoint_class", [StubOptoeOe, StubOptoeElsfp])
@pytest.mark.parametrize("method_name, args", [("set_lpmode", (True,)), ("reset", ())])
def test_optoe_controls_preserve_unsupported_api_operations(endpoint_class, method_name, args):
    endpoint = endpoint_class(CpoHardwareInfo(SOME_OE_ID, SOME_ELSFP_ID))
    api = MagicMock()
    getattr(api, method_name).side_effect = NotImplementedError("unsupported endpoint control")
    endpoint._api_factory.create_api = MagicMock(return_value=api)

    with pytest.raises(NotImplementedError, match="unsupported endpoint control"):
        getattr(endpoint, method_name)(*args)


@pytest.mark.parametrize("endpoint_class", [StubOptoeOe, StubOptoeElsfp])
@pytest.mark.parametrize("method_name, args", [("set_lpmode", (True,)), ("reset", ())])
def test_platform_override_bypasses_optoe_api_default(endpoint_class, method_name, args):
    hardware_control = MagicMock(return_value=True)

    def control(self, *values):
        return hardware_control(*values)

    platform_class = type("PlatformEndpoint", (endpoint_class,), {method_name: control})
    endpoint = platform_class(CpoHardwareInfo(SOME_OE_ID, SOME_ELSFP_ID))
    endpoint._api_factory.create_api = MagicMock()

    assert getattr(endpoint, method_name)(*args) is True
    hardware_control.assert_called_once_with(*args)
    endpoint._api_factory.create_api.assert_not_called()
