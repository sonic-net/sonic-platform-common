"""
Regression tests for lane-count lookups on a sparse CMIS application
advertisement.

get_application_advertisement() is keyed by AppSel code (1-based) and may be
sparse, because the loop skips any AppSel whose host or media interface code
does not decode. Lookups must therefore test membership, not length.

Reference data below is the real lower-page 0h byte 86..117 AppSel table of an
NVIDIA CPO module that advertises media code 0xC0 for AppSel 5 and 6, which
yields the sparse key set {1, 2, 3, 4, 7, 8}.
"""
import pytest
from unittest.mock import MagicMock

from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.codes.public.sff8024 import Sff8024
from sonic_platform_base.sonic_xcvr.fields import consts

# AppSel -> (host code, media code, host_lanes, media_lanes, host_assign, media_assign)
APPL_TABLE = {
    1: (0x51, 0x56, 8, 8, 0x01, 0x01),
    2: (0x82, 0x77, 4, 4, 0x11, 0x01),
    3: (0x4f, 0x1c, 4, 4, 0x11, 0x11),
    4: (0x81, 0x75, 2, 2, 0x55, 0x55),
    5: (0x4e, 0xc0, 2, 2, 0x55, 0x55),   # 0xC0 does not decode -> entry skipped
    6: (0x4d, 0xc0, 2, 2, 0x55, 0x55),   # 0xC0 does not decode -> entry skipped
    7: (0x80, 0x73, 1, 1, 0xff, 0xff),
    8: (0x4b, 0x14, 1, 1, 0xff, 0xff),
}


def _make_api():
    """Build a CmisApi whose EEPROM returns the AppSel table above."""
    dic = {}
    for app, (host, media, hl, ml, ha, ma) in APPL_TABLE.items():
        dic["%s_%d" % (consts.HOST_ELECTRICAL_INTERFACE, app)] = \
            Sff8024.HOST_ELECTRICAL_INTERFACE.get(host, 'Unknown')
        dic["%s_%d" % (consts.MODULE_MEDIA_INTERFACE_SM, app)] = \
            Sff8024.SM_MEDIA_INTERFACE.get(media, 'Unknown')
        dic["%s_%d" % (consts.HOST_LANE_COUNT, app)] = hl
        dic["%s_%d" % (consts.MEDIA_LANE_COUNT, app)] = ml
        dic["%s_%d" % (consts.HOST_LANE_ASSIGNMENT_OPTION, app)] = ha
        dic["%s_%d" % (consts.MEDIA_LANE_ASSIGNMENT_OPTION, app)] = ma

    def _read(field):
        if field == consts.APPLS_ADVT_FIELD:
            return dict(dic)
        if field == consts.APPLS_ADVT_FIELD_PAGE01:
            return {}
        if field == consts.MEDIA_TYPE_FIELD:
            return Sff8024.MODULE_MEDIA_TYPE[2]      # sm_media_interface
        return None

    eeprom = MagicMock()
    eeprom.read.side_effect = _read
    api = CmisApi(eeprom)
    api.is_flat_memory = MagicMock(return_value=False)
    return api


def test_lane_getters_on_sparse_advertisement_from_eeprom():
    """End-to-end: a real sparse advertisement must not zero out a present
    application.

    AppSel 5 and 6 are skipped because 0xC0 does not decode, so the dict holds
    6 entries while the highest key is 8. A length-based guard reports
    media_lane_count 0 for AppSel 7, which drove the port to CMIS_STATE_FAILED.
    """
    api = _make_api()
    advt = api.get_application_advertisement()

    assert sorted(advt.keys()) == [1, 2, 3, 4, 7, 8]
    assert len(advt) == 6 and max(advt) == 8      # sparse: len < highest key

    for app in advt:
        assert api.get_media_lane_count(app) == APPL_TABLE[app][3]
        assert api.get_host_lane_count(app) == APPL_TABLE[app][2]
        assert api.get_media_lane_assignment_option(app) == APPL_TABLE[app][5]
        assert api.get_host_lane_assignment_option(app) == APPL_TABLE[app][4]

    # the application the failing ports selected
    assert api.get_media_lane_count(7) == 1
    assert api.get_media_lane_assignment_option(7) == 255
    assert api.get_host_lane_count(7) == 1


def test_absent_application_still_returns_zero():
    """An application that is genuinely not advertised must still yield 0."""
    api = _make_api()
    assert 5 not in api.get_application_advertisement()
    assert api.get_media_lane_count(5) == 0
    assert api.get_media_lane_assignment_option(5) == 0
    assert api.get_host_lane_count(5) == 0
    assert api.get_host_lane_assignment_option(5) == 0
    # and an index beyond anything advertised
    assert api.get_media_lane_count(15) == 0
    assert api.get_host_lane_count(15) == 0
