import pytest
from mock import MagicMock

from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoBase, CpoHardwareInfo, OeId
from sonic_platform_base.sonic_xcvr.cpo.oe import OeBase
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpBase

# These tests don't depend on the specific ids (the factory's create methods
# are mocked); any valid id will do.
SOME_OE_ID = OeId.BROADCOM_DAVISSON
SOME_ELSFP_ID = None

# Methods that the *Base classes declare but leave for the platform to
# implement. Each entry is (method_name, args). Add a new abstract method
# here to get NotImplementedError coverage for it.
ABSTRACT_METHODS = [
    ("get_reset_status", ()),
    ("reset", ()),
    ("get_lpmode", ()),
    ("set_lpmode", (True,)),
]


class TestOeBase(object):
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

    @pytest.mark.parametrize("method_name, args", ABSTRACT_METHODS)
    def test_abstract_methods_throw(self, method_name, args):
        oe = OeBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))

        with pytest.raises(NotImplementedError):
            getattr(oe, method_name)(*args)


class TestElsfpBase(object):
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

    @pytest.mark.parametrize("method_name, args", ABSTRACT_METHODS)
    def test_abstract_methods_throw(self, method_name, args):
        elsfp = ElsfpBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))

        with pytest.raises(NotImplementedError):
            getattr(elsfp, method_name)(*args)


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

    @pytest.mark.parametrize("method_name, args", ABSTRACT_METHODS)
    def test_abstract_methods_throw(self, method_name, args):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        cpo = CpoBase(hardware_id, OeBase(hardware_id), ElsfpBase(hardware_id))

        with pytest.raises(NotImplementedError):
            getattr(cpo, method_name)(*args)
