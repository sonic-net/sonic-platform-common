import pytest
from sonic_platform_base.sfp_base import SfpBase
from unittest.mock import MagicMock

def test_remove_xcvr_api_and_refresh():
    """
    Test that remove_xcvr_api clears the cached API and that get_xcvr_api
    fetches a new API object on subsequent call.
    """
    # Create SfpBase instance and mock factory
    sfp = SfpBase()
    factory = MagicMock()
    api1 = object()
    api2 = object()
    factory.create_xcvr_api.side_effect = [api1, api2]
    sfp._xcvr_api_factory = factory

    # Initially cache should be empty
    assert sfp._xcvr_api is None

    # First call should build and cache api1
    result1 = sfp.get_xcvr_api()
    assert result1 is api1
    assert factory.create_xcvr_api.call_count == 1

    # Second call should return cached api1 without new factory call
    result2 = sfp.get_xcvr_api()
    assert result2 is api1
    assert factory.create_xcvr_api.call_count == 1

    # Removing the cached API should clear the cache
    sfp.remove_xcvr_api()
    assert sfp._xcvr_api is None

    # Next get_xcvr_api should fetch a fresh API (api2)
    result3 = sfp.get_xcvr_api()
    assert result3 is api2
    assert factory.create_xcvr_api.call_count == 2

def test_old_api_handle_survives_remove_xcvr_api():
    """
    Test that an old API handle continues to work after remove_xcvr_api and a new handle is created.
    """
    sfp = SfpBase()
    api1 = MagicMock()
    api2 = MagicMock()
    api1.get_transceiver_bulk_status.return_value = "bulk1"
    api2.get_transceiver_bulk_status.return_value = "bulk2"
    factory = MagicMock()
    factory.create_xcvr_api.side_effect = [api1, api2]
    sfp._xcvr_api_factory = factory

    # Thread 1 gets first API handle
    t1_api = sfp.get_xcvr_api()
    assert t1_api is api1

    # Thread 2 removes and recreates API
    sfp.remove_xcvr_api()
    t2_api = sfp.get_xcvr_api()
    assert t2_api is api2

    # Thread 1 still uses old handle without crashing
    assert t1_api.get_transceiver_bulk_status() == "bulk1"
    # New handle returns its own result
    assert t2_api.get_transceiver_bulk_status() == "bulk2" 
