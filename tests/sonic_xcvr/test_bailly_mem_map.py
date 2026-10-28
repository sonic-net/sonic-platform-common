"""Endpoint page ownership and compatibility of the legacy combined map."""
import pytest

from sonic_platform_base.sonic_xcvr.codes.broadcom.bailly import BaillyCodes
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.fields.broadcom import bailly
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.bailly import (
    BaillyElsfpMemMap, BaillyMemMap, BaillyOeMemMap,
)
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.page import CmisPage


@pytest.mark.parametrize("bank", [0, 1, 7])
def test_oe_map_keeps_public_cmis_pages_and_bank_addresses(bank):
    oe = BaillyOeMemMap(BaillyCodes, bank=bank)
    public = CmisMemMap(BaillyCodes, bank=bank)
    assert [(type(page), page.page, page.bank) for page in oe.pages] == [
        (type(page), page.page, page.bank) for page in public.pages
    ]
    assert oe.bank == bank
    assert oe.get_field(consts.TEMPERATURE_FIELD).get_offset() == public.get_field(
        consts.TEMPERATURE_FIELD).get_offset()
    assert oe.get_field(consts.TX_DISABLE_FIELD).get_offset() == CmisPage.linear_offset(0x10, bank, 130)
    for name in (bailly.CPO_INFO_FIELD, bailly.CPO_MODULE_MONITORS_FIELD, bailly.LASER_POWER_MODE_CONTROL_FIELD):
        with pytest.raises(KeyError):
            oe.get_field(name)


@pytest.mark.parametrize("bank", [0, 7])
@pytest.mark.parametrize("base_page", [0, 4])
def test_endpoint_maps_have_disjoint_pages_and_legacy_keeps_both(bank, base_page):
    oe = BaillyOeMemMap(BaillyCodes, bank=bank)
    els = BaillyElsfpMemMap(BaillyCodes, base_page=base_page)
    legacy = BaillyMemMap(BaillyCodes, bank=bank, base_page=base_page)
    oe_pages = {page.page for page in oe.pages}
    els_pages = {page.page for page in els.pages}
    assert els_pages == {0xB0 + base_page, 0xB1 + base_page, 0xB2 + base_page}
    assert oe_pages.isdisjoint(els_pages)
    assert {page.page for page in legacy.pages} == oe_pages | els_pages
    assert legacy.get_field(consts.TX_DISABLE_FIELD).get_offset() == oe.get_field(
        consts.TX_DISABLE_FIELD).get_offset()
    assert legacy.get_field(bailly.MODULE_TEMPERATURE_MONITOR).get_offset() == els.get_field(
        bailly.MODULE_TEMPERATURE_MONITOR).get_offset()
