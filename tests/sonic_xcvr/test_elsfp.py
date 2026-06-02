from mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoHardwareId
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpApiFactory

# OeId/ElsfpId currently define no members; use sentinels to represent
# "an id is set" in tests that exercise the not-yet-supported code paths.
SOME_OE_ID = object()
SOME_ELSFP_ID = object()


class TestElsfpApiFactory(object):
    def test_create_api_raises_when_id_none(self):
        elsfp = MagicMock()
        elsfp.hardware_id = CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=None)
        factory = ElsfpApiFactory(elsfp)
        with pytest.raises(ValueError):
            factory.create_api()

    def test_create_api_raises_when_id_set(self):
        elsfp = MagicMock()
        elsfp.hardware_id = CpoHardwareId(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        factory = ElsfpApiFactory(elsfp)
        with pytest.raises(ValueError):
            factory.create_api()
