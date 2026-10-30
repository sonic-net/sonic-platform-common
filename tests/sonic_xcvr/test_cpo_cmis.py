import pytest

from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.cpo.cmis import CpoCmisApi
from sonic_platform_base.sonic_xcvr.fields.xcvr_field import RegBitField
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap

from .eeprom_utils import InMemoryEeprom

# Imported under a private alias so that pytest does not collect
# and run TestCmis's test cases when executing this file.
from .test_cmis import TestCmis as _TestCmis


class TestCpoCmis(_TestCmis):
    """
    Every test case of TestCmis, run against CpoCmisApi.

    This is intended to catch drift between CpoCmisApi and CmisApi. If a bug-fix
    is added to CmisApi, or a new feature added, then CpoCmisApi should be ideally
    updated with the same feature.
    """

    api = CpoCmisApi(_TestCmis.eeprom)


# Pages 10h-2Fh are selected per bank, so what they hold belongs to one port's
# lanes. The CDB message pages are addressed without a bank (see
# CmisPage.linear_offset), so they answer the same for the whole device.
BANKED_PAGES = frozenset(range(0x10, 0x30))
CDB_PAGES = frozenset(range(0x9F, 0xB0))


def page_of(offset):
    """The CMIS page a linear EEPROM offset falls on.

    The inverse of CmisPage.linear_offset for bank 0: lower memory is offsets
    0-127, and everything above it sits at (bank * 256 + page) * 128 + offset.
    """
    if offset < 128:
        return 0x00
    return (offset // 128 - 1) % 256


class TestTheBankedSplitReadsTheRightPages:
    """Which pages each half of the split actually reaches.

    A non-banked getter is read once and its answer handed to every port of the
    device, so it may only read what reads the same from every bank. Should one
    of them reach a banked page, every port is quietly given the values of
    whichever bank happened to be selected - a wrong reading rather than a slow
    one, and one that no reading of the field names would show up. So these
    tests take the pages from the addresses the getters actually go to.
    """

    FAMILIES = ('dom_real_value', 'dom_flags', 'status', 'status_flags')

    def _recording_api(self, api_class=CpoCmisApi):
        """An api over an in-memory module, and the pages it reads."""
        mem_map = CmisMemMap(CmisCodes)
        eeprom = InMemoryEeprom(mem_map)

        # A module that advertises everything it can. Left at zero, the getters
        # answer 'N/A' out of the advertising page and never reach the monitors
        # whose pages this is about.
        for name, field in mem_map._get_all_fields().items():
            if 'Support' in name and isinstance(field, RegBitField):
                eeprom.memory[field.get_offset()] |= 1 << (field.bitpos % 8)

        pages = set()
        reader = eeprom.eeprom.reader

        def recording_reader(offset, size):
            pages.update(page_of(byte) for byte in range(offset, offset + size))
            return reader(offset, size)

        eeprom.eeprom.reader = recording_reader
        return api_class(eeprom.eeprom), pages

    @pytest.mark.parametrize('family', FAMILIES)
    def test_the_non_banked_half_stays_off_the_banked_pages(self, family):
        api, pages = self._recording_api()
        pages.clear()

        getattr(api, f'get_non_banked_transceiver_{family}')()

        assert not pages & BANKED_PAGES, sorted(hex(page) for page in pages & BANKED_PAGES)
        assert not pages & CDB_PAGES, sorted(hex(page) for page in pages & CDB_PAGES)

    @pytest.mark.parametrize('family', FAMILIES)
    def test_the_banked_half_reads_a_banked_page(self, family):
        """The other direction: a half that reads nothing banked is a half whose
        fields are the same for the whole device, and paying for them once per
        port is the cost the split exists to avoid."""
        api, pages = self._recording_api()
        pages.clear()

        getattr(api, f'get_banked_transceiver_{family}')()

        assert pages & BANKED_PAGES, sorted(hex(page) for page in pages)

    @pytest.mark.parametrize('family', FAMILIES)
    def test_the_two_halves_hold_every_field_the_community_getter_does(self, family):
        """A field that landed in neither half would leave a CPO port publishing
        less than the transceiver it replaces, with nothing to say so."""
        cpo, _ = self._recording_api()
        community, _ = self._recording_api(CmisApi)

        halves = {**(getattr(cpo, f'get_non_banked_transceiver_{family}')() or {}),
                  **(getattr(cpo, f'get_banked_transceiver_{family}')() or {})}
        whole = getattr(community, f'get_transceiver_{family}')() or {}

        assert set(whole) - set(halves) == set()
