import pytest
from unittest.mock import MagicMock
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.codes.public.sff8024 import Sff8024
from sonic_platform_base.sonic_xcvr.fields import consts

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

    def clear_cache(self, method_name=None):
        """
        Clear cached API return values for methods decorated with read_only_cached_api_return.
        """
        if method_name:
            cache_name = f'_{method_name}_cache'
            if hasattr(self.api, cache_name):
                delattr(self.api, cache_name)
        else:
            for attr in list(self.api.__dict__.keys()):
                if attr.startswith('_') and attr.endswith('_cache'):
                    delattr(self.api, attr)

    def test_clear_cache_for_get_model(self):
        # Ensure clear_cache('get_model') clears the cache so read() is re-called
        self.api.xcvr_eeprom.read.return_value = 'val1'
        _ = self.api.get_model()
        _ = self.api.get_model()
        assert self.api.xcvr_eeprom.read.call_count == 1
        # Clear only get_model cache
        self.clear_cache('get_model')
        self.api.xcvr_eeprom.read.return_value = 'val2'
        _ = self.api.get_model()
        assert self.api.xcvr_eeprom.read.call_count == 2
        assert self.api.get_model() == 'val2'

    def test_clear_all_caches(self):
        # Ensure clear_cache() clears all cached methods
        # Setup: get_model and get_cmis_rev use side effects
        self.api.xcvr_eeprom.read.side_effect = ['m1', 1, 2]
        _ = self.api.get_model()
        _ = self.api.get_cmis_rev()
        assert self.api.xcvr_eeprom.read.call_count == 3
        # Clear all caches
        self.clear_cache()
        # Reset read mock and provide new side effects
        self.api.xcvr_eeprom.read.reset_mock()
        self.api.xcvr_eeprom.read.side_effect = ['m2', 3, 4]
        m2 = self.api.get_model()
        rev = self.api.get_cmis_rev()
        assert m2 == 'm2'
        assert rev == '3.4'
        # Both methods should re-read their values
        assert self.api.xcvr_eeprom.read.call_count == 3

class TestReadOnlyCacheDictAndListDecorator:
    def setup_method(self):
        # Initialize CmisApi with a mock EEPROM and clear initial reads
        eeprom = MagicMock()
        self.api = CmisApi(eeprom)
        self.api.xcvr_eeprom.read.reset_mock()

    def clear_cache(self, method_name=None):
        """
        Clear cached API return values for methods decorated with read_only_cached_api_return.
        """
        if method_name:
            cache_name = f'_{method_name}_cache'
            if hasattr(self.api, cache_name):
                delattr(self.api, cache_name)
        else:
            for attr in list(self.api.__dict__.keys()):
                if attr.startswith('_') and attr.endswith('_cache'):
                    delattr(self.api, attr)

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
        media_type = Sff8024.MODULE_MEDIA_TYPE[1]     # e.g. "nm_850_media_interface"
        prefix    = consts.MODULE_MEDIA_INTERFACE_850NM
        raw = {
            f"{consts.HOST_ELECTRICAL_INTERFACE}_1":          "iface1",
            f"{prefix}_1":                                     "mod_iface1",
            f"{consts.MEDIA_LANE_COUNT}_1":                    2,
            f"{consts.HOST_LANE_COUNT}_1":                     1,
            f"{consts.HOST_LANE_ASSIGNMENT_OPTION}_1":         3,
            f"{consts.MEDIA_LANE_ASSIGNMENT_OPTION}_1":        4,
        }
        # Make read() return raw for APPLS_ADVT_FIELD and valid media type string for MEDIA_TYPE_FIELD
        def read_side_effect(field_name):
            if field_name == consts.APPLS_ADVT_FIELD:
                return raw
            if field_name == consts.MEDIA_TYPE_FIELD:
                # Return the module media type string that matches our prefix
                return Sff8024.MODULE_MEDIA_TYPE[1]
            return None
        self.api.xcvr_eeprom.read.side_effect = read_side_effect
        first = self.api.get_application_advertisement()
        second = self.api.get_application_advertisement()
        # The returned dict should be processed into the correct keys
        expected = {
            1: {
                'host_electrical_interface_id': 'iface1',
                'module_media_interface_id': 'mod_iface1',
                'media_lane_count': 2,
                'host_lane_count': 1,
                'host_lane_assignment_options': 3,
                'media_lane_assignment_options': 4
            }
        }
        assert first == expected
        assert second == expected
        # Should have read APPLS_ADVT_FIELD and MEDIA_TYPE_FIELD once each
        assert self.api.xcvr_eeprom.read.call_count == 2

    def test_clear_cache_for_get_application_advertisement(self):
        # Non-empty dict is cached, clear_cache should force re-read
        media_type = Sff8024.MODULE_MEDIA_TYPE[1]
        prefix = consts.MODULE_MEDIA_INTERFACE_850NM
        raw = {
            f"{consts.HOST_ELECTRICAL_INTERFACE}_1": 'iface1',
            f"{prefix}_1": 'mod_iface1',
            f"{consts.MEDIA_LANE_COUNT}_1": 2,
            f"{consts.HOST_LANE_COUNT}_1": 1,
            f"{consts.HOST_LANE_ASSIGNMENT_OPTION}_1": 3,
            f"{consts.MEDIA_LANE_ASSIGNMENT_OPTION}_1": 4,
        }
        def read_side_effect(field_name):
            if field_name == consts.APPLS_ADVT_FIELD:
                return raw
            if field_name == consts.MEDIA_TYPE_FIELD:
                return media_type
            return None
        self.api.xcvr_eeprom.read.side_effect = read_side_effect
        first = self.api.get_application_advertisement()
        second = self.api.get_application_advertisement()
        assert self.api.xcvr_eeprom.read.call_count == 2
        # Clear the specific cache and read again
        self.clear_cache('get_application_advertisement')
        third = self.api.get_application_advertisement()
        assert third == first
        assert self.api.xcvr_eeprom.read.call_count == 4