from mock import MagicMock

from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoBase, CpoHardwareId
from sonic_platform_base.sonic_xcvr.cpo.oe import OeBase
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpBase

# OeId/ElsfpId currently define no members; these tests don't depend on the
# specific ids (the factory's create methods are mocked), so use sentinels.
SOME_OE_ID = object()
SOME_ELSFP_ID = object()


class TestOeBase(object):
    def test_get_api_refreshes_when_none(self):
        oe = OeBase(CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        oe._api_factory.create_api = MagicMock(return_value=fake_api)

        result = oe.get_api()

        oe._api_factory.create_api.assert_called_once_with()
        assert result is fake_api

    def test_get_api_cached(self):
        oe = OeBase(CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        oe._api_factory.create_api = MagicMock(return_value=fake_api)

        # First call populates the cache, second call should reuse it.
        first = oe.get_api()
        second = oe.get_api()

        oe._api_factory.create_api.assert_called_once_with()
        assert first is second is fake_api


class TestElsfpBase(object):
    def test_get_api_refreshes_when_none(self):
        elsfp = ElsfpBase(CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        elsfp._api_factory.create_api = MagicMock(return_value=fake_api)

        result = elsfp.get_api()

        elsfp._api_factory.create_api.assert_called_once_with()
        assert result is fake_api

    def test_get_api_cached(self):
        elsfp = ElsfpBase(CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        elsfp._api_factory.create_api = MagicMock(return_value=fake_api)

        first = elsfp.get_api()
        second = elsfp.get_api()

        elsfp._api_factory.create_api.assert_called_once_with()
        assert first is second is fake_api


class TestCpoBase(object):
    def test_init(self):
        hardware_id = CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        oe = OeBase(hardware_id)
        elsfp = ElsfpBase(hardware_id)

        cpo = CpoBase(hardware_id, oe, elsfp)

        assert cpo.hardware_id is hardware_id
        assert cpo.oe is oe
        assert cpo.elsfp is elsfp
