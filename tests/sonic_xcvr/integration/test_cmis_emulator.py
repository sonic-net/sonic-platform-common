"""
test_cmis_emulator.py

Integration tests that run the production SONiC transceiver stack
(``SfpOptoeBase`` -> ``XcvrApiFactory`` -> ``CmisApi`` -> CMIS memory maps)
against a live `xcvr-emu <https://github.com/az-pz/xcvr-emu>`_ CMIS
transceiver emulator.

Unlike the unit tests, nothing here is mocked: every read and write travels
over gRPC to an ``xcvr-emud`` process that maintains real CMIS EEPROM contents
and runs the module / data path state machines.
"""

import struct

import pytest

from sonic_platform_base.sonic_xcvr.api.public.cmis import CmisApi
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.consts import (
    CMIS_EEPROM_PAGE_SIZE,
    CMIS_NUM_NON_BANKED_PAGES,
    LANE_DATAPATH_CONFIG_PAGE,
    THRESHOLDS_PAGE,
)
from sonic_platform_base.sonic_xcvr.mem_maps.public.cmis.pages.page import CmisPage

from . import emulator
from .emulator import (
    ABSENT_XCVR_INDEX,
    BYTES_PER_BANK,
    PRESENT_XCVR_INDEX,
    EmulatedSfp,
    linear_to_page_address,
    wait_until,
)

pytestmark = pytest.mark.integration

if not emulator.is_available():
    pytest.skip(
        "xcvr-emu is not installed (%s); install test dependencies with "
        "'pip install \".[testing]\"'"
        % emulator.XCVR_EMU_IMPORT_ERROR,
        allow_module_level=True,
    )

# Lower memory DOM registers (CMIS 5.x Table 8-6).
TEMPERATURE_OFFSET = 14
VOLTAGE_OFFSET = 16

# Applications advertised by xcvr_emu_config.yaml.
APPSEL_400G_DR4 = 1
APPSEL_200G_DR4 = 2


class TestEmulatorHarness:
    """The emulator process and the gRPC transport it exposes."""

    def test_daemon_exposes_configured_transceivers(self, emu_client):
        """Both configured modules exist, with the configured presence state."""
        presence = {info.index: info.present for info in emu_client.list()}
        assert presence == {PRESENT_XCVR_INDEX: True, ABSENT_XCVR_INDEX: False}

    def test_sfp_reports_presence_from_emulator(self, sfp, absent_sfp):
        """Presence tracks the emulator's per-module state."""
        assert sfp.get_presence() is True
        assert absent_sfp.get_presence() is False


class TestLinearAddressTranslation:
    """`CmisPage.linear_offset` against the emulator's page/bank addressing.

    The optoe driver flattens CMIS ``(bank, page, offset)`` into a single linear
    EEPROM file. These tests confirm the offsets the memory maps compute land on
    the CMIS registers the emulator expects.
    """

    @pytest.mark.parametrize("bank", [0, 1, 2, 3])
    @pytest.mark.parametrize("page,offset", [
        (0x00, 0),
        (0x00, 127),
        (0x00, 128),
        (0x01, 200),
        (LANE_DATAPATH_CONFIG_PAGE, 145),
        (0x11, 255),
    ])
    def test_round_trip_matches_page_addressing(self, bank, page, offset, sfp, emu_client):
        """A linear offset addresses the CMIS register the memory map intends."""
        linear = CmisPage.linear_offset(page, bank, offset)

        # Pages below 10h are not banked, so the memory map clamps the bank to 0.
        expected_bank = 0 if page < CMIS_NUM_NON_BANKED_PAGES else bank
        assert linear_to_page_address(linear) == (expected_bank, page, offset)

        # Write through the emulator's native page addressing...
        emu_client.write(PRESENT_XCVR_INDEX, page, offset, b"\x5a", bank=expected_bank)
        # ...and read it back through the linear address space.
        assert bytes(sfp.read_eeprom(linear, 1)) == b"\x5a"

    def test_lower_memory_is_not_paged(self, sfp, emu_client):
        """Offsets below 128 always address page 00h lower memory on bank 0."""
        emu_client.write(PRESENT_XCVR_INDEX, 0x00, TEMPERATURE_OFFSET, b"\x12\x34")
        assert bytes(sfp.read_eeprom(TEMPERATURE_OFFSET, 2)) == b"\x12\x34"
        assert linear_to_page_address(TEMPERATURE_OFFSET) == (0, 0x00, TEMPERATURE_OFFSET)

    def test_read_spanning_page_boundary_is_split(self, sfp, emu_client):
        """A read crossing a page boundary is stitched from both pages."""
        emu_client.write(PRESENT_XCVR_INDEX, 0x10, 252, b"\xaa\xbb\xcc\xdd")
        emu_client.write(PRESENT_XCVR_INDEX, 0x11, 128, b"\x11\x22\x33\x44")

        linear = CmisPage.linear_offset(0x10, 0, 252)
        assert bytes(sfp.read_eeprom(linear, 8)) == b"\xaa\xbb\xcc\xdd\x11\x22\x33\x44"

    def test_write_spanning_page_boundary_is_split(self, sfp, emu_client):
        """A write crossing a page boundary lands in both pages."""
        linear = CmisPage.linear_offset(0x10, 0, 252)
        assert sfp.write_eeprom(linear, 8, bytearray(range(0xE0, 0xE8))) is True

        assert emu_client.read(PRESENT_XCVR_INDEX, 0x10, 252, 4) == b"\xe0\xe1\xe2\xe3"
        assert emu_client.read(PRESENT_XCVR_INDEX, 0x11, 128, 4) == b"\xe4\xe5\xe6\xe7"

    def test_banked_pages_are_isolated(self, emu_client):
        """Each bank is a distinct 32 KiB block in the linear address space."""
        page, offset = 0x12, 200
        for bank in range(4):
            emu_client.write(PRESENT_XCVR_INDEX, page, offset, bytes([0xA0 + bank]), bank=bank)

        for bank in range(4):
            banked_sfp = EmulatedSfp(emu_client, index=PRESENT_XCVR_INDEX, bank=bank)
            linear = CmisPage.linear_offset(page, bank, offset)
            assert linear == bank * BYTES_PER_BANK + (page + 1) * CMIS_EEPROM_PAGE_SIZE + (offset - CMIS_EEPROM_PAGE_SIZE)
            assert bytes(banked_sfp.read_eeprom(linear, 1)) == bytes([0xA0 + bank])


class TestApiDiscovery:
    """`XcvrApiFactory` bootstrapping off a real CMIS EEPROM image."""

    def test_factory_builds_cmis_api(self, sfp):
        """The QSFP-DD identifier in lower memory selects the CMIS API."""
        assert isinstance(sfp.get_xcvr_api(), CmisApi)

    def test_no_api_when_module_absent(self, absent_sfp):
        """An unplugged module reads back as zeros, so no API is built."""
        assert bytes(absent_sfp.read_eeprom(0, 2)) == b"\x00\x00"
        assert absent_sfp.get_xcvr_api() is None

    def test_api_is_rebuilt_after_hot_plug(self, absent_sfp, emu_client):
        """Plugging a module in makes the factory produce an API for it."""
        assert absent_sfp.get_xcvr_api() is None

        emu_client.set_present(ABSENT_XCVR_INDEX, True)
        absent_sfp.remove_xcvr_api()

        assert absent_sfp.get_presence() is True
        assert isinstance(absent_sfp.get_xcvr_api(), CmisApi)

    def test_api_is_dropped_after_hot_unplug(self, sfp, emu_client):
        """Pulling a module out makes the factory stop producing an API."""
        assert isinstance(sfp.get_xcvr_api(), CmisApi)

        emu_client.set_present(PRESENT_XCVR_INDEX, False)
        sfp.remove_xcvr_api()

        assert sfp.get_presence() is False
        assert sfp.get_xcvr_api() is None


class TestTransceiverInfo:
    """Static EEPROM decoding, checked against xcvr_emu_config.yaml."""

    def test_identity_fields(self, sfp):
        """Vendor identity decodes to the values the emulator was configured with."""
        info = sfp.get_transceiver_info()

        assert info is not None
        assert info["manufacturer"] == "SONiC-EMU"
        assert info["model"] == "EMU-400G-DR4"
        assert info["serial"] == "EMUSN0000001"
        assert info["vendor_rev"] == "0A"
        assert info["vendor_oui"] == "00-17-9c"
        assert info["vendor_date"] == "2025-06-01 A1"

    def test_module_capability_fields(self, sfp):
        """Module type, CMIS revision and power class decode correctly."""
        info = sfp.get_transceiver_info()

        assert info["type_abbrv_name"] == "QSFP-DD"
        assert info["cmis_rev"] == "5.2"
        assert info["connector"] == "MPO 1x16"
        assert info["ext_identifier"] == "Power Class 8 (10.0W Max)"
        assert info["specification_compliance"] == "sm_media_interface"
        assert info["cable_length"] == 100.0

    def test_firmware_versions(self, sfp, cmis_api):
        """Active and inactive firmware revisions come back from page 00h."""
        assert cmis_api.get_module_active_firmware() == "2.3"
        assert cmis_api.get_module_inactive_firmware() == "2.1"
        # The emulated module does not advertise CDB, so the versions are read
        # straight out of the EEPROM rather than through a CDB command.
        assert cmis_api.is_cdb_supported() is False
        assert sfp.get_transceiver_info_firmware_versions() == {
            "active_firmware": "2.3",
            "inactive_firmware": "2.1",
        }

    def test_application_advertisement(self, cmis_api):
        """Both advertised applications are decoded from lower memory and page 01h."""
        advertisement = cmis_api.get_application_advertisement()

        assert set(advertisement) == {APPSEL_400G_DR4, APPSEL_200G_DR4}
        assert advertisement[APPSEL_400G_DR4] == {
            "host_electrical_interface_id": "400GAUI-4-S C2M (Annex 120G)",
            "module_media_interface_id": "400GBASE-DR4 (Cl 124)",
            "host_lane_count": 4,
            "media_lane_count": 4,
            "host_lane_assignment_options": 0b0001,
            "media_lane_assignment_options": 0b0001,
        }
        assert advertisement[APPSEL_200G_DR4] == {
            "host_electrical_interface_id": "200GBASE-CR2 (Clause 162)",
            "module_media_interface_id": "200GBASE-DR4 (Cl 121)",
            "host_lane_count": 2,
            "media_lane_count": 2,
            "host_lane_assignment_options": 0b0101,
            "media_lane_assignment_options": 0b0101,
        }

    def test_paged_memory_is_detected(self, cmis_api):
        """The module advertises paged (non-flat) memory, so upper pages are read."""
        assert cmis_api.is_flat_memory() is False


class TestModuleStateMachine:
    """Module state transitions driven through page 00h byte 26."""

    def test_module_boots_into_low_power(self, cmis_api):
        """A freshly plugged module comes up in ModuleLowPwr."""
        assert cmis_api.get_module_state() == "ModuleLowPwr"
        assert cmis_api.get_lpmode() is True

    def test_exit_low_power_moves_module_to_ready(self, cmis_api):
        """Clearing LowPwrRequestSW brings the module to ModuleReady."""
        assert cmis_api.set_lpmode(False) is True

        assert cmis_api.get_module_state() == "ModuleReady"
        assert cmis_api.get_lpmode() is False

    def test_enter_low_power_returns_module_to_low_power(self, ready_cmis_api):
        """Setting LowPwrRequestSW takes the module back to ModuleLowPwr."""
        assert ready_cmis_api.set_lpmode(True) is True

        assert ready_cmis_api.get_module_state() == "ModuleLowPwr"
        assert ready_cmis_api.get_lpmode() is True

    def test_reset_returns_module_to_low_power(self, ready_cmis_api):
        """A software reset re-runs module initialisation."""
        assert ready_cmis_api.reset() is True

        assert ready_cmis_api.get_module_state() == "ModuleLowPwr"

    def test_no_module_fault_reported(self, ready_cmis_api):
        """A healthy emulated module reports no fault."""
        assert ready_cmis_api.get_module_fault_cause() == "No Fault detected"


class TestDatapathProvisioning:
    """Application selection and data path state machine transitions."""

    def test_default_application_activates_host_lanes(self, ready_cmis_api):
        """The module's default AppSel activates the first application's lanes."""
        assert ready_cmis_api.get_active_apsel_hostlane() == {
            "ActiveAppSelLane1": APPSEL_400G_DR4,
            "ActiveAppSelLane2": APPSEL_400G_DR4,
            "ActiveAppSelLane3": APPSEL_400G_DR4,
            "ActiveAppSelLane4": APPSEL_400G_DR4,
            "ActiveAppSelLane5": 0,
            "ActiveAppSelLane6": 0,
            "ActiveAppSelLane7": 0,
            "ActiveAppSelLane8": 0,
        }

        datapath_state = ready_cmis_api.get_datapath_state()
        assert [datapath_state["DP%dState" % lane] for lane in range(1, 5)] == \
            ["DataPathActivated"] * 4
        assert [datapath_state["DP%dState" % lane] for lane in range(5, 9)] == \
            ["DataPathDeactivated"] * 4

    def test_datapath_deinit_deactivates_lanes(self, ready_cmis_api):
        """Asserting DPDeinit tears the active data paths down."""
        ready_cmis_api.set_datapath_deinit(0xFF)

        assert wait_until(
            lambda: all(
                state == "DataPathDeactivated"
                for state in ready_cmis_api.get_datapath_state().values()
            )
        )
        assert ready_cmis_api.get_datapath_deinit() == [True] * 8

    def test_decommission_all_datapaths(self, ready_cmis_api):
        """Decommissioning clears every AppSel and deactivates every data path."""
        ready_cmis_api.decommission_all_datapaths()

        assert ready_cmis_api.get_active_apsel_hostlane() == {
            "ActiveAppSelLane%d" % lane: 0 for lane in range(1, 9)
        }
        assert ready_cmis_api.get_datapath_state() == {
            "DP%dState" % lane: "DataPathDeactivated" for lane in range(1, 9)
        }

    def test_provision_alternate_application(self, ready_cmis_api):
        """Staging AppSel 2 and applying DPInit brings the new data path up."""
        ready_cmis_api.decommission_all_datapaths()

        host_lane_mask = 0b0011
        ready_cmis_api.set_application(host_lane_mask, APPSEL_200G_DR4)
        assert ready_cmis_api.get_application(0) == APPSEL_200G_DR4
        assert ready_cmis_api.get_application(1) == APPSEL_200G_DR4

        assert ready_cmis_api.scs_apply_datapath_init(host_lane_mask) is True
        assert wait_until(
            lambda: ready_cmis_api.get_active_apsel_hostlane()["ActiveAppSelLane1"]
            == APPSEL_200G_DR4
        )

        config_status = ready_cmis_api.get_config_datapath_hostlane_status()
        assert config_status["ConfigStatusLane1"] == "ConfigSuccess"
        assert config_status["ConfigStatusLane2"] == "ConfigSuccess"

        ready_cmis_api.set_datapath_init(host_lane_mask)
        assert wait_until(
            lambda: ready_cmis_api.get_datapath_state()["DP1State"] == "DataPathActivated"
        )

        datapath_state = ready_cmis_api.get_datapath_state()
        assert datapath_state["DP1State"] == "DataPathActivated"
        assert datapath_state["DP2State"] == "DataPathActivated"
        assert datapath_state["DP3State"] == "DataPathDeactivated"

    def test_error_description_tracks_datapath_health(self, ready_cmis_api):
        """`get_error_description` reports OK only while the data path is up."""
        ready_cmis_api.decommission_all_datapaths()

        host_lane_mask = 0b0011
        ready_cmis_api.set_application(host_lane_mask, APPSEL_200G_DR4)
        ready_cmis_api.scs_apply_datapath_init(host_lane_mask)
        ready_cmis_api.set_datapath_init(host_lane_mask)
        assert wait_until(
            lambda: ready_cmis_api.get_datapath_state()["DP1State"] == "DataPathActivated"
        )
        assert ready_cmis_api.get_error_description() == "OK"

        ready_cmis_api.set_datapath_deinit(host_lane_mask)
        assert wait_until(
            lambda: ready_cmis_api.get_datapath_state()["DP1State"] == "DataPathDeactivated"
        )
        assert ready_cmis_api.get_error_description() == "DataPathDeactivated"

    def test_staged_control_set_is_written_to_page_10h(self, ready_cmis_api, emu_client):
        """`set_application` writes AppSel codes to the staged control set on page 10h."""
        ready_cmis_api.decommission_all_datapaths()
        ready_cmis_api.set_application(0b0011, APPSEL_200G_DR4)

        # Page 10h bytes 145-146 hold AppSel for host lanes 1 and 2.
        staged = emu_client.read(PRESENT_XCVR_INDEX, LANE_DATAPATH_CONFIG_PAGE, 145, 2)
        assert [byte >> 4 for byte in staged] == [APPSEL_200G_DR4, APPSEL_200G_DR4]


class TestDomDecoding:
    """DOM and threshold decoding driven by EEPROM contents in the emulator."""

    def test_module_temperature_and_voltage(self, sfp, cmis_api, emu_client):
        """Raw DOM registers decode into engineering units."""
        emu_client.write(
            PRESENT_XCVR_INDEX, 0x00, TEMPERATURE_OFFSET, struct.pack(">h", int(31.5 * 256))
        )
        emu_client.write(PRESENT_XCVR_INDEX, 0x00, VOLTAGE_OFFSET, struct.pack(">H", 33000))

        assert cmis_api.get_module_temperature() == 31.5
        assert cmis_api.get_voltage() == 3.3

        dom = sfp.get_transceiver_dom_real_value()
        assert dom["temperature"] == 31.5
        assert dom["voltage"] == 3.3

    def test_negative_temperature_is_signed(self, cmis_api, emu_client):
        """Sub-zero temperatures decode as signed 16-bit values."""
        emu_client.write(
            PRESENT_XCVR_INDEX, 0x00, TEMPERATURE_OFFSET, struct.pack(">h", int(-12.5 * 256))
        )

        assert cmis_api.get_module_temperature() == -12.5

    def test_thresholds_from_page_02h(self, sfp, emu_client):
        """Threshold registers are read from page 02h."""
        emu_client.write(
            PRESENT_XCVR_INDEX, THRESHOLDS_PAGE, 128, struct.pack(">h", int(75.0 * 256))
        )
        emu_client.write(
            PRESENT_XCVR_INDEX, THRESHOLDS_PAGE, 130, struct.pack(">h", int(-5.0 * 256))
        )

        thresholds = sfp.get_transceiver_threshold_info()
        assert thresholds["temphighalarm"] == 75.0
        assert thresholds["templowalarm"] == -5.0
