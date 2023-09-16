from unittest.mock import patch
from mock import MagicMock
import pytest
from sonic_platform_base.sonic_xcvr.sfp_optoe_base import SfpOptoeBase

class TestSfpOptoeBase(object):
    optoebase = SfpOptoeBase()

    def test_set_optoe_write_max_with_exception(self):
        self.optoebase.set_optoe_write_max(1)
