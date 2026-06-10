from mock import MagicMock
import pytest

from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoHardwareInfo
from sonic_platform_base.sonic_xcvr.cpo.oe import OeApiFactory

# OeId/ElsfpId currently define no members; use sentinels to represent
# "an id is set" in tests that exercise the not-yet-supported code paths.
SOME_OE_ID = object()


class TestOeApiFactory(object):
    def test_create_api_raises(self):
        oe = MagicMock()
        oe.hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=None)
        factory = OeApiFactory(oe)
        with pytest.raises(ValueError):
            factory.create_api()
