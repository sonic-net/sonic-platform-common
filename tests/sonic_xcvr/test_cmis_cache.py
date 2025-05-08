import pytest
from unittest.mock import MagicMock
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi

class TestReadOnlyCacheDecorator:
    def setup_method(self):
        # Initialize CmisApi with a mock EEPROM and clear initial reads
        eeprom = MagicMock()
        self.api = CmisApi(eeprom)
        self.api.xcvr_eeprom.read.reset_mock()

    def test_get_model_caching(self):
        # Ensure get_model value is cached and read() called only once
        self.api.xcvr_eeprom.read.return_value = 'model_val'
        first = self.api.get_model()
        second = self.api.get_model()
        assert first == 'model_val'
        assert second == 'model_val'
        assert self.api.xcvr_eeprom.read.call_count == 1

    def test_get_model_retry_on_none(self):
        # When initial read returns None, decorator should retry once
        self.api.xcvr_eeprom.read.side_effect = [None, 'model_retry']
        result = self.api.get_model()
        assert result == 'model_retry'
        assert self.api.xcvr_eeprom.read.call_count == 2

    def test_get_cmis_rev_caching(self):
        # get_cmis_rev reads major and minor once, then caches result
        # side_effect: first call returns major, second minor
        self.api.xcvr_eeprom.read.side_effect = [5, 3, 7, 9]
        v1 = self.api.get_cmis_rev()
        v2 = self.api.get_cmis_rev()
        assert v1 == '5.3'
        assert v2 == '5.3'
        # Only the first two reads (major and minor) should occur
        assert self.api.xcvr_eeprom.read.call_count == 2

class TestReadOnlyCacheDictAndListDecorator:
    def setup_method(self):
        # Initialize CmisApi with a mock EEPROM and clear initial reads
        eeprom = MagicMock()
        self.api = CmisApi(eeprom)
        self.api.xcvr_eeprom.read.reset_mock()

    def test_get_application_advertisement_no_cache_if_empty(self):
        # Empty dict should not be cached and read() should be called each time
        self.api.xcvr_eeprom.read.return_value = {}
        first = self.api.get_application_advertisement()
        second = self.api.get_application_advertisement()
        assert first == {}
        assert second == {}
        assert self.api.xcvr_eeprom.read.call_count == 2

    def test_get_application_advertisement_caching_if_non_empty(self):
        # Non-empty dict should be cached and read() should be called only once
        non_empty = {1: {'media_lane_count': 2}}
        self.api.xcvr_eeprom.read.return_value = non_empty
        first = self.api.get_application_advertisement()
        second = self.api.get_application_advertisement()
        assert first == non_empty
        assert second == non_empty
        assert self.api.xcvr_eeprom.read.call_count == 1