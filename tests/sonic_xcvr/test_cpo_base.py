from mock import MagicMock, call

from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_els import NvidiaCpoElsCmisApi
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_oe import NvidiaCpoOeCmisApi
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.api.public.elsfp import ElsfpApi
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_els import NvidiaCpoElsCmisMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_oe import NvidiaCpoOeMemMap
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import CpoBase, CpoHardwareInfo, OeId
from sonic_platform_base.sonic_xcvr.cpo.oe import OeBase
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpBase
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.elsfp.elsfp import ElsfpMemMap

# These tests don't depend on the specific ids (the factory's create methods
# are mocked); any valid id will do.
SOME_OE_ID = OeId.BROADCOM_DAVISSON
SOME_ELSFP_ID = None


class TestOeBase(object):
    def test_get_api_refreshes_when_none(self):
        oe = OeBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        oe._api_factory.create_api = MagicMock(return_value=fake_api)

        result = oe.get_api()

        oe._api_factory.create_api.assert_called_once_with()
        assert result is fake_api

    def test_get_api_cached(self):
        oe = OeBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        oe._api_factory.create_api = MagicMock(return_value=fake_api)

        # First call populates the cache, second call should reuse it.
        first = oe.get_api()
        second = oe.get_api()

        oe._api_factory.create_api.assert_called_once_with()
        assert first is second is fake_api


class TestElsfpBase(object):
    def test_get_api_refreshes_when_none(self):
        elsfp = ElsfpBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        elsfp._api_factory.create_api = MagicMock(return_value=fake_api)

        result = elsfp.get_api()

        elsfp._api_factory.create_api.assert_called_once_with()
        assert result is fake_api

    def test_get_api_cached(self):
        elsfp = ElsfpBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))
        fake_api = MagicMock()
        elsfp._api_factory.create_api = MagicMock(return_value=fake_api)

        first = elsfp.get_api()
        second = elsfp.get_api()

        elsfp._api_factory.create_api.assert_called_once_with()
        assert first is second is fake_api


class TestCpoBase(object):
    def test_init(self):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        oe = OeBase(hardware_id)
        elsfp = ElsfpBase(hardware_id)

        cpo = CpoBase(hardware_id, oe, elsfp)

        assert cpo.hardware_id is hardware_id
        assert cpo.oe is oe
        assert cpo.elsfp is elsfp

    def test_get_xcvr_api_returns_oe_api(self):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        oe = OeBase(hardware_id)
        elsfp = ElsfpBase(hardware_id)
        oe_api = MagicMock()
        oe.get_api = MagicMock(return_value=oe_api)

        cpo = CpoBase(hardware_id, oe, elsfp)

        assert cpo.get_xcvr_api() is oe_api
        oe.get_api.assert_called_with()


class TestNvidiaSpc6(object):
    """The real factories, for the ids the NVIDIA SPC6 CPO platform declares."""

    # The laser source declares no id of its own, so the engine's id is the
    # whole hardware identity and selects both apis.
    HARDWARE_ID = CpoHardwareInfo(oe_id=OeId.NVIDIA_SPC6_CPO, elsfp_id=None)

    @staticmethod
    def _with_readable_eeprom(device):
        """CmisApi reads the EEPROM as it is built, so give it bytes to read."""
        device.read_eeprom = MagicMock(side_effect=lambda offset, size: bytearray(size))
        device.write_eeprom = MagicMock(return_value=True)
        return device

    def test_oe_api_is_standard_cmis_on_the_requested_bank(self):
        for bank in range(4):
            oe = self._with_readable_eeprom(OeBase(self.HARDWARE_ID, bank=bank))

            api = oe.get_api()

            assert isinstance(api, NvidiaCpoOeCmisApi)
            assert isinstance(api.xcvr_eeprom.mem_map, NvidiaCpoOeMemMap)
            assert api.xcvr_eeprom.mem_map.bank == bank
            # The NVIDIA classes override nothing yet, so the engine answers as
            # the standard CMIS module it is. What the names buy is somewhere
            # for the vendor pages to land without touching the factory again.
            assert isinstance(api, CmisApi)
            assert isinstance(api.xcvr_eeprom.mem_map, CmisMemMap)

    def test_elsfp_api_is_the_nvidia_laser_source(self):
        elsfp = self._with_readable_eeprom(ElsfpBase(self.HARDWARE_ID))

        api = elsfp.get_api()

        assert isinstance(api, NvidiaCpoElsCmisApi)
        assert isinstance(api.xcvr_eeprom.mem_map, NvidiaCpoElsCmisMemMap)
        # Same here: the generic ELSFP surface, under the name the vendor
        # tables will arrive behind.
        assert isinstance(api, ElsfpApi)
        assert isinstance(api.xcvr_eeprom.mem_map, ElsfpMemMap)
        # The factory identifies the source from lower memory before it
        # dispatches, for whichever vendor wants the answer. NVIDIA does not
        # need it - the engine's id already names both halves - so this only
        # pins that reaching the api does not depend on what it reads.
        assert elsfp.read_eeprom.call_args_list == [call(129, 16), call(148, 16)]
