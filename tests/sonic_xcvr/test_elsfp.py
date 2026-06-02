import pytest
from mock import MagicMock

from sonic_platform_base.sonic_xcvr.codes.public.elsfp import ElsfpCodes
from sonic_platform_base.sonic_xcvr.fields import consts, elsfp_consts
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.elsfp import ElsfpMemMap
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


class TestElsfpMemMap:
    mem_map = ElsfpMemMap(ElsfpCodes)

    def test_inherits_cmis_flat_pages(self):
        # CmisFlatMemMap adds page 00h lower + upper; ElsfpMemMap adds 6 more.
        assert len(self.mem_map.pages) == 8

    @pytest.mark.parametrize("page", [0x01, 0x02, 0x1A, 0x1B, 0x2F, 0x9F])
    def test_expected_pages_present(self, page):
        assert any(p.page == page for p in self.mem_map.pages)

    @pytest.mark.parametrize("page", [0x10, 0x11, 0x12, 0x13])
    def test_lane_datapath_pages_excluded(self, page):
        assert not any(p.page == page for p in self.mem_map.pages)

    @pytest.mark.parametrize("field", [
        consts.MODULE_FUNCTION_TYPE,
        consts.ADVERTISING_FIELD,
        consts.THRESHOLDS_FIELD,
        elsfp_consts.ELSFP_MODULE_ADVERTISEMENTS_FIELD,
        elsfp_consts.ELSFP_LANE_FAULTS_WARNINGS_FIELD,
        elsfp_consts.ELSFP_LASER_SAVE_RESTORE_FIELD,
        elsfp_consts.ELSFP_ALARMS_WARNINGS_MASKS_FIELD,
        elsfp_consts.ELSFP_LANE_CONTROLS_FIELD,
        elsfp_consts.ELSFP_OUTPUT_FIBER_CHECKED_FIELD,
        elsfp_consts.ELSFP_LANE_MAPPING_FREQ_POWER_FIELD,
        elsfp_consts.ELSFP_SETPOINTS_FIELD,
        elsfp_consts.ELSFP_MONITORS_FIELD,
    ])
    def test_field_resolvable(self, field):
        assert self.mem_map.get_field(field) is not None


class TestElsfpCodes:
    def test_inherits_cmis_codes(self):
        # ElsfpCodes extends CmisCodes; the parent VDM_TYPE table is inherited.
        assert 1 in ElsfpCodes.VDM_TYPE  # CMIS Laser Age entry
        assert 84 in ElsfpCodes.VDM_TYPE  # CMIS 5.3 ELS Input Power entry

    def test_elsfp_specific_codes_present(self):
        assert ElsfpCodes.CONTROL_MODE[0] == 'ACC'
        assert ElsfpCodes.CONTROL_MODE[1] == 'APC'
        assert 0 in ElsfpCodes.LANE_FAULT_CODE
        assert 0 in ElsfpCodes.LANE_WARNING_CODE
        assert ElsfpCodes.LANE_STATE[2] == 'Lane Output on'
