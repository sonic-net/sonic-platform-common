import pytest
from mock import MagicMock, call

from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_els import NvidiaCpoElsCmisApi
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_oe import NvidiaCpoOeCmisApi
from sonic_platform_base.sonic_xcvr.api.public.cdb_fw import CmisCdbFw
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.cdb.nvidia.cpo_els_memmap import NvidiaCpoElsCdbMemMap
from sonic_platform_base.sonic_xcvr.cdb.nvidia.cpo_oe_memmap import NvidiaCpoOeCdbMemMap
from sonic_platform_base.sonic_xcvr.codes.nvidia.cpo_oe import NvidiaCpoOeCodes
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_els import NvidiaCpoElsCmisMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_oe import NvidiaCpoOeMemMap
from sonic_platform_base.sonic_xcvr.cpo.cpo_base import (
    CpoApiFactory,
    CpoBase,
    CpoHardwareInfo,
    OeId,
)
from sonic_platform_base.sonic_xcvr.cpo.oe import OeBase
from sonic_platform_base.sonic_xcvr.cpo.elsfp import ElsfpBase
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.elsfp.elsfp import ElsfpMemMap

# These tests don't depend on the specific ids (the factory's create methods
# are mocked); any valid id will do.
SOME_OE_ID = OeId.BROADCOM_DAVISSON
SOME_ELSFP_ID = None

# Methods that the *Base classes declare but leave for the platform to
# implement. Each entry is (method_name, args). Add a new abstract method
# here to get NotImplementedError coverage for it.
ABSTRACT_METHODS = [
    ("get_reset_status", ()),
    ("reset", ()),
    ("get_lpmode", ()),
    ("set_lpmode", (True,)),
]


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

    @pytest.mark.parametrize("method_name, args", ABSTRACT_METHODS)
    def test_abstract_methods_throw(self, method_name, args):
        oe = OeBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))

        with pytest.raises(NotImplementedError):
            getattr(oe, method_name)(*args)


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

    @pytest.mark.parametrize("method_name, args", ABSTRACT_METHODS)
    def test_abstract_methods_throw(self, method_name, args):
        elsfp = ElsfpBase(CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID))

        with pytest.raises(NotImplementedError):
            getattr(elsfp, method_name)(*args)


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

    @pytest.mark.parametrize("method_name, args", ABSTRACT_METHODS)
    def test_abstract_methods_throw(self, method_name, args):
        hardware_id = CpoHardwareInfo(oe_id=SOME_OE_ID, elsfp_id=SOME_ELSFP_ID)
        cpo = CpoBase(hardware_id, OeBase(hardware_id), ElsfpBase(hardware_id))

        with pytest.raises(NotImplementedError):
            getattr(cpo, method_name)(*args)


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

    def test_oe_api_is_the_nvidia_engine_on_the_requested_bank(self):
        for bank in range(4):
            oe = self._with_readable_eeprom(OeBase(self.HARDWARE_ID, bank=bank))

            api = oe.get_api()

            assert isinstance(api, NvidiaCpoOeCmisApi)
            assert isinstance(api.xcvr_eeprom.mem_map, NvidiaCpoOeMemMap)
            assert api.xcvr_eeprom.mem_map.bank == bank
            # The NVIDIA map and codes override nothing, so the engine still
            # answers as the standard CMIS module it is.
            assert isinstance(api, CmisApi)
            assert isinstance(api.xcvr_eeprom.mem_map, CmisMemMap)

    def test_elsfp_api_is_the_nvidia_laser_source(self):
        elsfp = self._with_readable_eeprom(ElsfpBase(self.HARDWARE_ID))

        api = elsfp.get_api()

        assert isinstance(api, NvidiaCpoElsCmisApi)
        assert isinstance(api.xcvr_eeprom.mem_map, NvidiaCpoElsCmisMemMap)
        # The laser source is reached for firmware operations, which are the
        # CMIS CDB ones, so the api has to carry the CDB firmware surface.
        assert isinstance(api, CmisCdbFw)
        # The factory identifies the source from lower memory before it
        # dispatches, for whichever vendor wants the answer. NVIDIA does not
        # need it - the engine's id already names both halves - so this only
        # pins that reaching the api does not depend on what it reads.
        assert elsfp.read_eeprom.call_args_list[:2] == [call(129, 16), call(148, 16)]


def _wire_eeprom(device):
    """The api constructors only need a callable pair; nothing is read here."""
    device.read_eeprom = MagicMock(return_value=bytearray(b"\x00"))
    device.write_eeprom = MagicMock(return_value=True)
    return device


class _FactoryWithoutACdbMap(CpoApiFactory):
    """Builds the NVIDIA OE api the way the real factory did before the vendor
    CDB map was passed down. Stubbed here rather than borrowing a vendor whose
    api happens to lack CDB, so the test turns on the missing map alone.
    """

    def create_api(self):
        return self._create_api(codes_class=NvidiaCpoOeCodes,
                                mem_map_class=NvidiaCpoOeMemMap,
                                api_class=NvidiaCpoOeCmisApi)


class _OeBuiltWithoutACdbMap(OeBase):
    def _make_api_factory(self):
        return _FactoryWithoutACdbMap(self)


class TestNvidiaCdbMemMapReachesTheApi(object):
    """The NVIDIA CPO halves talk CDB, so the factory that builds them has to
    hand the vendor CDB map down. Without it ``cdb_handler`` stays None and
    every CDB-backed getter silently answers nothing."""

    def test_oe_api_gets_the_nvidia_cdb_mem_map(self):
        oe = _wire_eeprom(OeBase(CpoHardwareInfo(oe_id=OeId.NVIDIA_SPC6_CPO,
                                                 elsfp_id=None)))

        api = oe.get_api()

        assert isinstance(api, NvidiaCpoOeCmisApi)
        assert api.cdb_handler is not None
        assert isinstance(api.cdb_handler.mem_map, NvidiaCpoOeCdbMemMap)

    def test_els_api_gets_the_nvidia_cdb_mem_map(self):
        elsfp = _wire_eeprom(ElsfpBase(CpoHardwareInfo(oe_id=OeId.NVIDIA_SPC6_CPO,
                                                       elsfp_id=None)))

        api = elsfp.get_api()

        assert isinstance(api, NvidiaCpoElsCmisApi)
        assert api.cdb_handler is not None
        assert isinstance(api.cdb_handler.mem_map, NvidiaCpoElsCdbMemMap)

    def test_a_half_without_a_vendor_cdb_map_has_no_handler(self):
        """The regression the three tests above guard against, from the other
        side: a factory that builds the very same api but leaves the map out
        yields an api whose every CDB-backed getter answers nothing.
        """
        oe = _wire_eeprom(_OeBuiltWithoutACdbMap(
            CpoHardwareInfo(oe_id=OeId.NVIDIA_SPC6_CPO, elsfp_id=None)))

        assert oe.get_api().cdb_handler is None
