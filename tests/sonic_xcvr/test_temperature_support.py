"""Temperature capabilities, readiness, and EEPROM read failure regressions."""
from unittest.mock import MagicMock, patch

import pytest

from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.api.public.sff8436 import Sff8436Api
from sonic_platform_base.sonic_xcvr.api.public.sff8472 import Sff8472Api
from sonic_platform_base.sonic_xcvr.api.public.sff8636 import Sff8636Api
from sonic_platform_base.sonic_xcvr.codes.public.cmis import CmisCodes
from sonic_platform_base.sonic_xcvr.codes.public.sff8472 import Sff8472Codes
from sonic_platform_base.sonic_xcvr.codes.public.sff8636 import Sff8636Codes
from sonic_platform_base.sonic_xcvr.fields import consts
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis import CmisMemMap
from sonic_platform_base.sonic_xcvr.mem_maps.public.sff8472 import Sff8472MemMap
from sonic_platform_base.sonic_xcvr.mem_maps.public.sff8636 import Sff8636MemMap
from sonic_platform_base.sonic_xcvr.xcvr_api_factory import XcvrApiFactory
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom


def temperature_api(api_class, values):
    # Isolate temperature methods from unrelated CDB and VDM initialization.
    api = api_class.__new__(api_class)
    api.xcvr_eeprom = MagicMock(spec=XcvrEeprom)
    api.xcvr_eeprom.read.side_effect = values.get
    api._temp_support = None
    api._is_copper = None
    return api


@pytest.mark.parametrize("api_class", [CmisApi, Sff8436Api, Sff8472Api, Sff8636Api])
@pytest.mark.parametrize("support, expected", [(None, None), (False, 'N/A')])
def test_temperature_unavailable_does_not_read_monitor(api_class, support, expected):
    api = temperature_api(api_class, {})
    with patch.object(api, 'get_temperature_support', return_value=support):
        assert api.get_module_temperature() == expected
    api.xcvr_eeprom.read.assert_not_called()


@pytest.mark.parametrize("api_class", [CmisApi, Sff8436Api, Sff8472Api, Sff8636Api])
@pytest.mark.parametrize("value", [None, -20.5, 0.0, 35.125])
def test_supported_temperature_read(api_class, value):
    api = temperature_api(api_class, {
        consts.DATA_NOT_READY_FIELD: False,
        consts.TEMPERATURE_FIELD: value,
    })
    with patch.object(api, 'get_temperature_support', return_value=True):
        assert api.get_module_temperature() == value


@pytest.mark.parametrize("ready", [True, None])
def test_sfp_not_ready_does_not_read_temperature(ready):
    api = temperature_api(Sff8472Api, {
        consts.DDM_SUPPORT_FIELD: True,
        consts.DATA_NOT_READY_FIELD: ready,
    })
    assert api.get_module_temperature() is None
    assert all(call.args[0] != consts.TEMPERATURE_FIELD
               for call in api.xcvr_eeprom.read.call_args_list)


def test_sfp_readiness_recovers_on_next_read():
    data = bytearray(512)
    data[92] = 0x60  # DDM supported, internally calibrated.
    data[352:354] = bytes([35, 128])
    data[366] = 1
    eeprom = XcvrEeprom(lambda offset, size: data[offset:offset + size],
                        MagicMock(), Sff8472MemMap(Sff8472Codes))
    api = Sff8472Api(eeprom)
    assert api.get_module_temperature() is None
    data[366] = 0
    assert api.get_module_temperature() == 35.5


@pytest.mark.parametrize("bank", [0, 1, 3])
@pytest.mark.parametrize("supported", [False, True])
def test_cmis_temperature_advertisement_raw_eeprom(bank, supported):
    data = bytearray(512)
    data[287] = 1 if supported else 0  # Page 01h, byte 159, bit 0.
    data[14:16] = bytes([35, 128])
    api = temperature_api(CmisApi, {})
    api.xcvr_eeprom = XcvrEeprom(
        lambda offset, size: data[offset:offset + size], MagicMock(),
        CmisMemMap(CmisCodes, bank=bank))
    assert api.get_temperature_support() is supported
    assert api.get_module_temperature() == (35.5 if supported else 'N/A')


@pytest.mark.parametrize("api_class", [Sff8436Api, Sff8636Api])
@pytest.mark.parametrize("copper, expected", [(None, None), (True, False)])
def test_copper_detection_failure_and_unsupported(api_class, copper, expected):
    api = temperature_api(api_class, {})
    with patch.object(api, 'is_copper', return_value=copper):
        assert api.get_temperature_support() is expected
    api.xcvr_eeprom.read.assert_not_called()


def test_sff8436_optical_temperature_supported():
    api = temperature_api(Sff8436Api, {})
    with patch.object(api, 'is_copper', return_value=False):
        assert api.get_temperature_support() is True


@pytest.mark.parametrize("revision", [7, 8, 9, 10])
@pytest.mark.parametrize("supported", [False, True])
def test_sff8636_revision_and_capability_raw_eeprom(revision, supported):
    data = bytearray(256)
    data[1] = revision
    data[220] = 0x20 if supported else 0
    api = temperature_api(Sff8636Api, {})
    api.xcvr_eeprom = XcvrEeprom(
        lambda offset, size: data[offset:offset + size], MagicMock(),
        Sff8636MemMap(Sff8636Codes))
    with patch.object(api, 'is_copper', return_value=False):
        assert api.get_temperature_support() is (supported if revision >= 8 else True)


@pytest.mark.parametrize("failed_field", [consts.REV_COMPLIANCE_RAW_FIELD,
                                         consts.TEMP_SUPPORT_FIELD])
def test_sff8636_failed_capability_read_is_retried(failed_field):
    values = {consts.REV_COMPLIANCE_RAW_FIELD: 9, consts.TEMP_SUPPORT_FIELD: True}
    api = temperature_api(Sff8636Api, values)
    recovered = values[failed_field]
    values[failed_field] = None
    with patch.object(api, 'is_copper', return_value=False):
        assert api.get_temperature_support() is None
        values[failed_field] = recovered
        assert api.get_temperature_support() is True


def test_qsfp_factory_unreadable_revision():
    factory = XcvrApiFactory(MagicMock(), MagicMock())
    with patch.object(factory.lower_memory_info, 'get_revision_compliance', return_value=None), \
            patch.object(factory, '_create_api') as create:
        assert factory._create_qsfp_api() is None
        create.assert_not_called()


@pytest.mark.parametrize("identifier", [0x0c, 0x17])
def test_legacy_qsfp_identifiers(identifier):
    factory = XcvrApiFactory(lambda offset, size: bytes([identifier]), MagicMock())
    assert isinstance(factory.create_xcvr_api(), Sff8436Api)


@pytest.mark.parametrize("identifier", [0x1f, 0x20, 0x21, 0x22, 0x26])
@pytest.mark.parametrize("bank", [0, 3])
def test_new_cmis_identifiers_preserve_bank(identifier, bank):
    factory = XcvrApiFactory(lambda offset, size: bytes([identifier]), MagicMock())
    with patch.object(factory, '_create_cmis_api') as create:
        assert factory.create_xcvr_api(bank=bank) is create.return_value
        create.assert_called_once_with(bank)


@pytest.mark.parametrize("identifier", [0x1a, 0xff])
def test_unmapped_identifiers_remain_unsupported(identifier):
    factory = XcvrApiFactory(lambda offset, size: bytes([identifier]), MagicMock())
    assert factory.create_xcvr_api() is None
