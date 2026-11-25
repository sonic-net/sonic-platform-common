"""Platform additions must preserve common firmware reporting and API lifecycle."""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sonic_platform_base.sfp_base import SfpBase
from sonic_platform_base.sonic_xcvr import xcvr_api_factory
from sonic_platform_base.sonic_xcvr.api.innolight.fr_800g import CmisFr800gApi
from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.xcvr_api_factory import XcvrApiFactory


@pytest.fixture
def configs(monkeypatch, tmp_path):
    common = tmp_path / "common.yaml"
    common.write_text("QUALIFIED:\n  - REGISTER-OPTIC\n")
    platform = tmp_path / "platform.yaml"
    platform.write_text("QUALIFIED:\n  - PLATFORM-OPTIC\n")
    monkeypatch.setattr(xcvr_api_factory, "CMIS_FR800G_CONFIG_FILE", common)
    return common, platform


def set_identity(data, vendor, part):
    data[129:145] = vendor.encode().ljust(16, b" ")
    data[148:164] = part.encode().ljust(16, b" ")


@pytest.mark.parametrize("part,expected", [
    ("PLATFORM-OPTIC", CmisFr800gApi),
    ("REGISTER-OPTIC", CmisFr800gApi),
    ("OTHER", CmisApi),
])
def test_platform_additions_preserve_common_models(cmis_eeprom, configs, part, expected):
    data, reader, writer = cmis_eeprom
    set_identity(data, "QUALIFIED", part)
    factory = XcvrApiFactory(reader, writer, lambda: configs[1])
    assert type(factory.create_xcvr_api()) is expected
    writer.assert_not_called()


def test_platform_match_does_not_require_common_file(cmis_eeprom, configs):
    data, reader, writer = cmis_eeprom
    set_identity(data, "QUALIFIED", "PLATFORM-OPTIC")
    configs[0].unlink()
    assert type(XcvrApiFactory(reader, writer, lambda: configs[1]).create_xcvr_api()) is CmisFr800gApi
    writer.assert_not_called()


@pytest.mark.parametrize("contents", [
    None, "", "[", "[]", "QUALIFIED: PLATFORM-OPTIC", "QUALIFIED: [42]",
])
def test_missing_or_invalid_platform_file_keeps_default(
        cmis_eeprom, configs, contents, caplog):
    data, reader, writer = cmis_eeprom
    set_identity(data, "QUALIFIED", "OTHER")
    if contents is None:
        configs[1].unlink()
    else:
        configs[1].write_text(contents)
    assert type(XcvrApiFactory(reader, writer, lambda: configs[1]).create_xcvr_api()) is CmisApi
    assert str(configs[1]) in caplog.text
    writer.assert_not_called()


@pytest.mark.parametrize("callback", [
    None, lambda: None, lambda: 42, Mock(side_effect=RuntimeError("unavailable")),
])
def test_optional_or_broken_callback_keeps_default(cmis_eeprom, configs, callback):
    data, reader, writer = cmis_eeprom
    set_identity(data, "QUALIFIED", "OTHER")
    assert type(XcvrApiFactory(reader, writer, callback).create_xcvr_api()) is CmisApi
    writer.assert_not_called()


@pytest.mark.parametrize("vendor,part,expected", [
    ("OEM-QUALIFIED", "PLATFORM-OPTIC", CmisFr800gApi),
    ("oem-qualified", "PLATFORM-OPTIC", CmisApi),
    ("OEM-QUALIFIED", "platform-optic", CmisApi),
    ("OEM-QUALIFIED", "PLATFORM", CmisApi),
])
def test_platform_matching_uses_vendor_patterns_and_exact_parts(
        cmis_eeprom, configs, vendor, part, expected):
    data, reader, writer = cmis_eeprom
    configs[1].write_text('"*QUALIFIED*":\n  - PLATFORM-OPTIC\n')
    set_identity(data, vendor, part)
    assert type(XcvrApiFactory(reader, writer, lambda: configs[1]).create_xcvr_api()) is expected
    writer.assert_not_called()


def test_sff_discovery_does_not_resolve_cmis_policy(cmis_eeprom, configs):
    data, reader, writer = cmis_eeprom
    data[0] = 0x03
    callback = Mock(side_effect=AssertionError("Unexpected CMIS policy lookup"))
    assert XcvrApiFactory(reader, writer, callback).create_xcvr_api() is not None
    callback.assert_not_called()
    writer.assert_not_called()


def test_routine_reporting_only_changes_for_matching_models(cmis_eeprom, configs):
    data, reader, writer = cmis_eeprom
    set_identity(data, "QUALIFIED", "PLATFORM-OPTIC")
    with patch.object(CmisApi, "is_cdb_supported", return_value=True), patch.object(
            CmisApi, "get_module_fw_info") as query:
        api = XcvrApiFactory(reader, writer, lambda: configs[1]).create_xcvr_api()
        assert type(api) is CmisFr800gApi
        assert api.get_transceiver_info_firmware_versions() == {
            "active_firmware": "172.133.0", "inactive_firmware": "171.132.0"}
        query.assert_not_called()

        set_identity(data, "QUALIFIED", "OTHER")
        query.return_value = {"result": (0, 0, 0, 0, 0, 0, 0, 0, "3.2.1", "2.1.0")}
        control = XcvrApiFactory(reader, writer, lambda: configs[1]).create_xcvr_api()
        assert type(control) is CmisApi
        assert control.get_transceiver_info_firmware_versions() == {
            "active_firmware": "3.2.1", "inactive_firmware": "2.1.0"}
        query.assert_called_once_with()
    writer.assert_not_called()


def test_sfp_policy_is_lazy_and_rechecked_after_removal(cmis_eeprom, configs):
    data, reader, writer = cmis_eeprom
    callback = Mock(return_value=configs[1])

    class PlatformSfp(SfpBase):
        def __init__(self):
            super().__init__()
            self.ready = True

        def get_cmis_firmware_config_path(self):
            assert self.ready
            return callback()

        def read_eeprom(self, offset, size):
            return reader(offset, size)

        def write_eeprom(self, offset, size, value):
            return writer(offset, size, value)

    sfp = PlatformSfp()
    callback.assert_not_called()
    reader.assert_not_called()
    set_identity(data, "QUALIFIED", "PLATFORM-OPTIC")
    first = sfp.get_xcvr_api()
    assert type(first) is CmisFr800gApi
    assert sfp.get_xcvr_api() is first
    callback.assert_called_once_with()

    set_identity(data, "QUALIFIED", "OTHER")
    sfp.remove_xcvr_api()
    assert type(sfp.get_xcvr_api()) is CmisApi
    assert callback.call_count == 2
    writer.assert_not_called()


def test_common_match_does_not_consult_platform(cmis_eeprom, configs):
    _, reader, writer = cmis_eeprom
    callback = Mock(side_effect=AssertionError("Common model needs no platform policy"))
    assert type(XcvrApiFactory(reader, writer, callback).create_xcvr_api()) is CmisFr800gApi
    callback.assert_not_called()
    writer.assert_not_called()


@pytest.mark.parametrize("missing_offset", [129, 148])
def test_partial_identity_retries_without_removal(cmis_eeprom, configs, missing_offset):
    data, reader, writer = cmis_eeprom
    set_identity(data, "QUALIFIED", "PLATFORM-OPTIC")
    callback = Mock(return_value=configs[1])
    sfp = SfpBase()
    sfp._xcvr_api_factory = XcvrApiFactory(reader, writer, callback)
    reader.side_effect = lambda offset, size: (
        None if offset == missing_offset else data[offset:offset + size])
    assert sfp.get_xcvr_api() is None
    callback.assert_not_called()

    reader.side_effect = lambda offset, size: data[offset:offset + size]
    assert type(sfp.get_xcvr_api()) is CmisFr800gApi
    callback.assert_called_once_with()
    writer.assert_not_called()
