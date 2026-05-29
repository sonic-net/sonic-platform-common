from mock import MagicMock

from sonic_platform_base.sonic_xcvr.cpo_base import OeBase, ElsfpBase, CpoBase
from sonic_platform_base.sonic_xcvr.cpo_api_factory import CpoHardwareId, OeId, ElsfpId


class TestOeBase(object):
    def test_get_oe_api_refreshes_when_none(self):
        oe = OeBase(CpoHardwareId(oe_id=OeId.NVIDIA_SP6, elsfp_id=ElsfpId.EXAMPLE))
        fake_api = MagicMock()
        oe._oe_api_factory.create_oe_api = MagicMock(return_value=fake_api)

        result = oe.get_oe_api()

        oe._oe_api_factory.create_oe_api.assert_called_once_with()
        assert result is fake_api

    def test_get_oe_api_cached(self):
        oe = OeBase(CpoHardwareId(oe_id=OeId.NVIDIA_SP6, elsfp_id=ElsfpId.EXAMPLE))
        fake_api = MagicMock()
        oe._oe_api_factory.create_oe_api = MagicMock(return_value=fake_api)

        # First call populates the cache, second call should reuse it.
        first = oe.get_oe_api()
        second = oe.get_oe_api()

        oe._oe_api_factory.create_oe_api.assert_called_once_with()
        assert first is second is fake_api


class TestElsfpBase(object):
    def test_get_elsfp_api_refreshes_when_none(self):
        elsfp = ElsfpBase(CpoHardwareId(oe_id=OeId.NVIDIA_SP6, elsfp_id=ElsfpId.EXAMPLE))
        fake_api = MagicMock()
        elsfp._elsfp_api_factory.create_elsfp_api = MagicMock(return_value=fake_api)

        result = elsfp.get_elsfp_api()

        elsfp._elsfp_api_factory.create_elsfp_api.assert_called_once_with()
        assert result is fake_api

    def test_get_elsfp_api_cached(self):
        elsfp = ElsfpBase(CpoHardwareId(oe_id=OeId.NVIDIA_SP6, elsfp_id=ElsfpId.EXAMPLE))
        fake_api = MagicMock()
        elsfp._elsfp_api_factory.create_elsfp_api = MagicMock(return_value=fake_api)

        first = elsfp.get_elsfp_api()
        second = elsfp.get_elsfp_api()

        elsfp._elsfp_api_factory.create_elsfp_api.assert_called_once_with()
        assert first is second is fake_api


class TestCpoBase(object):
    def test_init(self):
        hardware_id = CpoHardwareId(oe_id=OeId.NVIDIA_SP6, elsfp_id=ElsfpId.EXAMPLE)
        oe = OeBase(hardware_id)
        elsfp = ElsfpBase(hardware_id)

        cpo = CpoBase(hardware_id, oe, elsfp)

        assert cpo.hardware_id is hardware_id
        assert cpo.oe is oe
        assert cpo.elsfp is elsfp
