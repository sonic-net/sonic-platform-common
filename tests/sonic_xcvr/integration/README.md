# xcvr-emu integration tests

These tests run the production SONiC transceiver stack against a live
[xcvr-emu](https://github.com/az-pz/xcvr-emu) CMIS transceiver emulator
instead of mocks.

```
CmisApi / XcvrApiFactory / CMIS memory maps   (code under test)
            |
    SfpOptoeBase.read_eeprom / write_eeprom   (EmulatedSfp, tests/.../emulator.py)
            |  linear offset -> (bank, page, offset)
        gRPC (SfpEmulatorService)
            |
        xcvr-emud                             (separate OS process)
```

`EmulatedSfp` implements only the two methods a vendor platform plugin has to
provide, `read_eeprom()` and `write_eeprom()`, translating the linear
(`optoe`-style) EEPROM offsets the memory maps produce into the CMIS
`(bank, page, offset)` triples the emulator speaks. Everything above that layer
is the real shipping code, so these tests cover address translation, field
decoding, and the module / data path state machines end to end.

## Running

The emulator runs as a plain OS process, not a container. Each test starts its
own `xcvr-emud` on an ephemeral loopback port and shuts it down afterwards,
because a single emulator process shares one CMIS memory map across all of its
transceivers.

```bash
pip install ".[testing]"   # Python 3.10+
pytest tests/sonic_xcvr/integration
```

Select or exclude them with the `integration` marker:

```bash
pytest -m integration        # only these tests
pytest -m "not integration"  # everything else
```

If `xcvr-emu` is not installed the module is skipped with an explanatory
message, so the default `pytest` run is unaffected.

## Files

| File | Purpose |
| --- | --- |
| `emulator.py` | `XcvrEmuDaemon` (process control), `XcvrEmuClient` (gRPC), `EmulatedSfp` (`SfpOptoeBase` adapter) |
| `xcvr_emu_config.yaml` | Emulated transceivers: index 0 plugged in, index 1 unplugged |
| `conftest.py` | Per-test daemon, client, SFP and `CmisApi` fixtures |
| `test_cmis_emulator.py` | The tests |

## Adding tests

Ask for `cmis_api` to get a `CmisApi` built by the production factory from the
emulated EEPROM, or `ready_cmis_api` for one whose module has already been
taken out of low power mode. `emu_client` gives raw `(bank, page, offset)`
access for seeding registers the emulator does not simulate — DOM samples, for
example — or for asserting which registers the API wrote.

The emulator applies writes from an asyncio task, so state changes are observed
asynchronously. Wrap such assertions in `emulator.wait_until()`.

Values asserted in `test_cmis_emulator.py` come from `xcvr_emu_config.yaml`;
keep the two in sync.
