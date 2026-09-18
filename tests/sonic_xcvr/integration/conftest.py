"""
conftest.py

Fixtures for the xcvr-emu backed integration tests.

Every test gets its own ``xcvr-emud`` process: the emulator shares a single CMIS
memory map across all of its transceivers, so a fresh daemon is the only way to
guarantee a test starts from the configured defaults.
"""

import pytest

from .emulator import (
    ABSENT_XCVR_INDEX,
    PRESENT_XCVR_INDEX,
    EmulatedSfp,
    XcvrEmuClient,
    XcvrEmuDaemon,
)


@pytest.fixture(autouse=True)
def _no_sleep():
    """Neutralise the unit-test fixture that stubs out ``time.sleep``.

    ``tests/sonic_xcvr/conftest.py`` patches ``time.sleep`` so the unit tests do
    not actually wait. These tests poll a live emulator, so real sleeps are
    required.
    """
    yield


@pytest.fixture(scope="function")
def emu_daemon():
    """Start a dedicated ``xcvr-emud`` process for one test.

    Yields:
        XcvrEmuDaemon: the running daemon.
    """
    with XcvrEmuDaemon() as daemon:
        yield daemon


@pytest.fixture(scope="function")
def emu_client(emu_daemon):
    """Connect a gRPC client to the per-test emulator.

    Yields:
        XcvrEmuClient: a connected client.
    """
    with XcvrEmuClient(emu_daemon.target) as client:
        yield client


@pytest.fixture(scope="function")
def sfp(emu_client):
    """An :class:`EmulatedSfp` bound to the transceiver that starts plugged in.

    Returns:
        EmulatedSfp: SFP object for PRESENT_XCVR_INDEX on bank 0.
    """
    return EmulatedSfp(emu_client, index=PRESENT_XCVR_INDEX)


@pytest.fixture(scope="function")
def absent_sfp(emu_client):
    """An :class:`EmulatedSfp` bound to the transceiver that starts unplugged.

    Returns:
        EmulatedSfp: SFP object for ABSENT_XCVR_INDEX on bank 0.
    """
    return EmulatedSfp(emu_client, index=ABSENT_XCVR_INDEX)


@pytest.fixture(scope="function")
def cmis_api(sfp):
    """The ``CmisApi`` the production factory builds for the emulated module.

    Returns:
        CmisApi: the API instance created from the emulated EEPROM.
    """
    api = sfp.get_xcvr_api()
    assert api is not None, "XcvrApiFactory did not create an API for the emulated module"
    return api


@pytest.fixture(scope="function")
def ready_cmis_api(cmis_api):
    """A ``CmisApi`` whose module has been brought out of low power mode.

    Returns:
        CmisApi: an API whose module reports ModuleReady.
    """
    assert cmis_api.set_lpmode(False) is True
    assert cmis_api.get_module_state() == "ModuleReady"
    return cmis_api
