from mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.cpo.cpo_api_factory import (
    OeApiFactory,
    ElsfpApiFactory,
    CpoHardwareId,
)

# OeId/ElsfpId currently define no members; use sentinels to represent
# "an id is set" in tests that exercise the not-yet-supported code paths.
SOME_OE_ID = object()
SOME_ELSFP_ID = object()


class TestOeApiFactory(object):
    def test_create_oe_api_raises(self):
        oe = MagicMock()
        oe.hardware_id = CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=None)
        factory = OeApiFactory(oe)
        with pytest.raises(ValueError):
            factory.create_oe_api()


class TestElsfpApiFactory(object):
    def test_create_elsfp_api_raises_when_id_none(self):
        elsfp = MagicMock()
        elsfp.hardware_id = CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=None)
        factory = ElsfpApiFactory(elsfp)
        with pytest.raises(ValueError):
            factory.create_elsfp_api()

    def test_create_elsfp_api_raises_when_id_set(self):
        elsfp = MagicMock()
        elsfp.hardware_id = CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        factory = ElsfpApiFactory(elsfp)
        with pytest.raises(ValueError):
            factory.create_elsfp_api()
