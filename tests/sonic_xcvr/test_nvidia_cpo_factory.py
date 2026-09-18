"""Tests for the NVIDIA-CPO branches of XcvrApiFactory."""
from unittest.mock import MagicMock, patch

import pytest

from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.api.public.cpo import CpoApi
from sonic_platform_base.sonic_xcvr.api.public.elsfp_cmis import ElsfpCmisApi
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_oe import NvidiaCpoOeCmisApi
from sonic_platform_base.sonic_xcvr.api.nvidia.cpo_els import NvidiaCpoElsCmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_els import NvidiaCpoElsCmisMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.nvidia.cpo_oe import NvidiaCpoOeMemMap
from sonic_platform_base.sonic_xcvr.cdb.nvidia.cpo_els_memmap import NvidiaCpoElsCdbMemMap
from sonic_platform_base.sonic_xcvr.cdb.nvidia.cpo_oe_memmap import NvidiaCpoOeCdbMemMap
from sonic_platform_base.sonic_xcvr.xcvr_api_factory import (
    NVIDIA_ELS_ADMIN_UPPER_PAGE,
    NVIDIA_VENDOR_NAME,
    XcvrApiFactory,
)


def _make_factory():
    reader = MagicMock(return_value=b"\x00")
    writer = MagicMock(return_value=True)
    return XcvrApiFactory(reader, writer)


class TestBuildCpoOeApi:
    @patch.object(XcvrApiFactory, "_get_vendor_name", MagicMock(return_value=NVIDIA_VENDOR_NAME))
    def test_nvidia_oe_gets_nvidia_class_and_cdb_memmap(self):
        f = _make_factory()
        api, els_admin_upper_page = f._build_cpo_oe_api(bank_id=1)
        assert isinstance(api, NvidiaCpoOeCmisApi)
        assert isinstance(api.xcvr_eeprom.mem_map, NvidiaCpoOeMemMap)
        assert api.cdb_handler is not None
        assert isinstance(api.cdb_handler.mem_map, NvidiaCpoOeCdbMemMap)
        assert api.xcvr_eeprom.mem_map.bank == 1
        assert api._get_bank_id() == 1
        assert els_admin_upper_page == NVIDIA_ELS_ADMIN_UPPER_PAGE

    @patch.object(XcvrApiFactory, "_get_vendor_name", MagicMock(return_value="SomeOtherVendor"))
    def test_unknown_oe_falls_back_to_generic_cmis(self):
        f = _make_factory()
        api, els_admin_upper_page = f._build_cpo_oe_api(bank_id=0)
        assert isinstance(api, CmisApi)
        assert not isinstance(api, NvidiaCpoOeCmisApi)
        assert api.cdb_handler is None
        assert els_admin_upper_page is None


class TestBuildCpoElsApi:
    @patch.object(XcvrApiFactory, "_get_vendor_els_name", MagicMock(return_value=NVIDIA_VENDOR_NAME))
    def test_nvidia_els_gets_nvidia_class_and_cdb_memmap(self):
        f = _make_factory()
        api = f._build_cpo_els_api(NVIDIA_ELS_ADMIN_UPPER_PAGE, bank_id=2)
        assert isinstance(api, NvidiaCpoElsCmisApi)
        assert isinstance(api.xcvr_eeprom.mem_map, NvidiaCpoElsCmisMemMap)
        assert api.cdb_handler is not None
        assert isinstance(api.cdb_handler.mem_map, NvidiaCpoElsCdbMemMap)
        assert api.xcvr_eeprom.mem_map.bank == 2
        assert api.bank_id == 2

    @patch.object(XcvrApiFactory, "_get_vendor_els_name", MagicMock(return_value="SomeOtherVendor"))
    def test_unknown_els_falls_back_to_generic_elsfp(self):
        f = _make_factory()
        api = f._build_cpo_els_api(NVIDIA_ELS_ADMIN_UPPER_PAGE, bank_id=3)
        assert isinstance(api, ElsfpCmisApi)
        assert not isinstance(api, NvidiaCpoElsCmisApi)
        assert api.cdb_handler is None
        assert api.bank_id == 3


class TestCreateCmisCpoApi:
    @patch.object(XcvrApiFactory, "_get_vendor_name", MagicMock(return_value=NVIDIA_VENDOR_NAME))
    @patch.object(XcvrApiFactory, "_get_vendor_els_name", MagicMock(return_value=NVIDIA_VENDOR_NAME))
    def test_nvidia_oe_and_els_returns_cpo_api(self):
        f = _make_factory()
        api = f._create_cmis_cpo_api(bank_id=3)
        assert isinstance(api, CpoApi)
        assert isinstance(api.optical_engine_xcvr_api, NvidiaCpoOeCmisApi)
        assert isinstance(api.external_laser_source_xcvr_api, NvidiaCpoElsCmisApi)
        assert api.optical_engine_xcvr_api.xcvr_eeprom.mem_map.bank == 3
        assert api.optical_engine_xcvr_api._get_bank_id() == 3
        assert api.external_laser_source_xcvr_api.xcvr_eeprom.mem_map.bank == 3
        assert api.external_laser_source_xcvr_api.bank_id == 3

    @patch.object(XcvrApiFactory, "_get_vendor_name", MagicMock(return_value="OtherOe"))
    @patch.object(XcvrApiFactory, "_get_vendor_els_name", MagicMock(return_value="OtherEls"))
    def test_unknown_vendors_still_produce_a_cpo_api(self):
        f = _make_factory()
        api = f._create_cmis_cpo_api(bank_id=0)
        assert isinstance(api, CpoApi)
        assert isinstance(api.optical_engine_xcvr_api, CmisApi)
        assert not isinstance(api.optical_engine_xcvr_api, NvidiaCpoOeCmisApi)
        assert isinstance(api.external_laser_source_xcvr_api, ElsfpCmisApi)
        assert not isinstance(api.external_laser_source_xcvr_api, NvidiaCpoElsCmisApi)

    @patch.object(XcvrApiFactory, "_get_vendor_name", MagicMock(return_value=NVIDIA_VENDOR_NAME))
    @patch.object(XcvrApiFactory, "_get_vendor_els_name", MagicMock(return_value="OtherEls"))
    def test_mixed_vendors_each_half_picks_independently(self):
        f = _make_factory()
        api = f._create_cmis_cpo_api(bank_id=2)
        assert isinstance(api.optical_engine_xcvr_api, NvidiaCpoOeCmisApi)
        assert isinstance(api.external_laser_source_xcvr_api, ElsfpCmisApi)
        assert not isinstance(api.external_laser_source_xcvr_api, NvidiaCpoElsCmisApi)
        assert api.optical_engine_xcvr_api.xcvr_eeprom.mem_map.bank == 2
        assert api.optical_engine_xcvr_api._get_bank_id() == 2
        assert api.external_laser_source_xcvr_api.xcvr_eeprom.mem_map.bank == 2
        assert api.external_laser_source_xcvr_api.bank_id == 2

    def test_bank_id_is_a_required_positional_argument(self):
        f = _make_factory()
        with pytest.raises(TypeError):
            f._create_cmis_cpo_api()


class TestCreateXcvrApiCpoIdentifier:
    @patch.object(XcvrApiFactory, "_get_vendor_name", MagicMock(return_value=NVIDIA_VENDOR_NAME))
    @patch.object(XcvrApiFactory, "_get_vendor_els_name", MagicMock(return_value=NVIDIA_VENDOR_NAME))
    def test_id_0x80_with_explicit_bank_id_propagates_to_memmaps(self):
        f = _make_factory()
        with patch.object(XcvrApiFactory, "_get_id",
                          MagicMock(return_value=0x80)):
            api = f.create_xcvr_api(bank_id=2)
        assert isinstance(api, CpoApi)
        assert isinstance(api.optical_engine_xcvr_api, NvidiaCpoOeCmisApi)
        assert isinstance(api.external_laser_source_xcvr_api, NvidiaCpoElsCmisApi)
        assert api.optical_engine_xcvr_api.xcvr_eeprom.mem_map.bank == 2
        assert api.optical_engine_xcvr_api._get_bank_id() == 2
        assert api.external_laser_source_xcvr_api.xcvr_eeprom.mem_map.bank == 2
        assert api.external_laser_source_xcvr_api.bank_id == 2

    @patch.object(XcvrApiFactory, "_get_vendor_name", MagicMock(return_value=NVIDIA_VENDOR_NAME))
    @patch.object(XcvrApiFactory, "_get_vendor_els_name", MagicMock(return_value=NVIDIA_VENDOR_NAME))
    def test_id_0x80_without_bank_id_defaults_to_zero(self):
        f = _make_factory()
        with patch.object(XcvrApiFactory, "_get_id",
                          MagicMock(return_value=0x80)):
            api = f.create_xcvr_api()
        assert isinstance(api, CpoApi)
        assert api.optical_engine_xcvr_api.xcvr_eeprom.mem_map.bank == 0
        assert api.optical_engine_xcvr_api._get_bank_id() == 0
        assert api.external_laser_source_xcvr_api.xcvr_eeprom.mem_map.bank == 0
        assert api.external_laser_source_xcvr_api.bank_id == 0
