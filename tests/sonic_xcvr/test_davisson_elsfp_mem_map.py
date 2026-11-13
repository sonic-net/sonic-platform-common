import pytest

from sonic_platform_base.sonic_xcvr.codes.broadcom.davisson_elsfp import DavissonTh6ElsfpCodes
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.mem_maps.broadcom.davisson_elsfp import DavissonTh6ElsfpMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.consts import CMIS_EEPROM_PAGE_SIZE
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.page import CmisPage


class TestDavissonTh6ElsfpMemMap:
    """Davisson relocates CMIS lower memory onto page B0h."""

    @pytest.mark.parametrize("field, lower_memory_offset", [
        (consts.ID_FIELD, 0),
        (consts.MODULE_STATE, 3),
    ])
    def test_lower_memory_fields_are_in_upper_memory_page_b0(self, field, lower_memory_offset):
        mem_map = DavissonTh6ElsfpMemMap(DavissonTh6ElsfpCodes)
        # (0xB0 * page_size) + lower_memory_size + lower_memory_offset
        expected = (0xB0 * CMIS_EEPROM_PAGE_SIZE) + CMIS_EEPROM_PAGE_SIZE + lower_memory_offset
        assert CmisPage.linear_offset(0xB0, 0, CMIS_EEPROM_PAGE_SIZE + lower_memory_offset) == expected
        assert mem_map.get_field(field).get_offset() == expected
