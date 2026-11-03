# Bazel wheel and source tests

`//:sonic_platform_common_wheel` builds `sonic_platform_common-1.0-py3-none-any.whl`
from this repository's complete Python package payload. It uses the standard
`rules_python` wheel rule, preserves `setup.py`'s runtime requirements, and includes
both license files. It does not execute `setup.py`, produce a Debian package, or
include dependencies inside the wheel. The existing Make/setuptools path remains
available.

The CI configuration is native Linux AMD64, Debian Trixie and Python
3.13, with Bazel 8.5.1. The wheel is pure Python; no artificial debug-symbol TAR
is produced. Other architectures are not covered by this new CI job.

## Build and consume

```sh
bazel build //:sonic_platform_common_wheel
```

Applications may use `//:sonic_platform_common` as a Python source library. Its
public modules also need the SONiC runtime declared in the wheel's
`Requires-Dist`: `sonic-py-common` and `sonic-config-engine`, including their
Common/native dependencies. Consumers supply those existing owner targets or
installed owner wheels; this repository does not compile another owner's code.
Optional hardware-specific dependencies retain their existing platform contract.
The source library also declares `psutil` for its storage modules; the wheel
retains the legacy metadata, whose builder supplied that dependency separately.

For the selected image, the existing source targets are
`//src/sonic-py-common:sonic_py_common` and
`//src/sonic-config-engine:sonic_config_engine` in `sonic-buildimage`.
The image installs the owner wheel directly; it does not require a DEB adapter.
SNMP uses this wheel at runtime. The existing eventd/MACsec Make paths use it
through sonic-utilities in their builder, which does not imply installing it in
those runtime containers.

## Test the installed wheel and original suite

```sh
cd tests/bazel
bazel test //:unit_tests //:installed_wheel_test --local_test_jobs=1
```

This separate test application uses the landed PR #64 image revision
`c743d7521e80fc1733e5cc0ffc24889b08f78444` and its actual Python/Common source
interfaces. Keeping image dependencies in this test root avoids a production
module cycle when `sonic-buildimage` consumes platform-common.

The original `tests/` suite and root `test_credo_aec_800g.py` run together. Existing
hardware mocks, assertions and skip markers remain intact. The runner copies
declared fixtures to a writable test directory rather than modifying the source
checkout. It records every collected case, outcomes, coverage, interpreter and
architecture.
The EEPROM fixture decodes its existing hex file with Python's standard library
instead of requiring the execution host's `xxd` and `rm` programs.
The port-file tests use a private database configuration pointing to an absent
test socket, exercising config-engine's existing file fallback without touching
the agent's live Redis configuration.

The installation test uses the existing image-owned wheel fixture. It installs
this exact wheel together with source-built py-common, config-engine and YANG
wheels, compares every declared owner Python file and dependency metadata against
`setup.py`, and imports installed EEPROM/SFP/chassis/PSU/thermal/Y-cable interfaces
with those owners' source directories removed. Declared third-party/native
runtime dependencies are borrowed from test runfiles; this proves the installed
owner wheel boundary, not an independently installed complete image environment.
Full SNMP container/service validation is tracked separately by buildimage #124.

## Dependency locks and evidence

The committed `requirements_lock.txt` files pin Python packages and hashes.
Regenerate intentionally with uv 0.12.18 for Python 3.13:

```sh
uv pip compile --generate-hashes --python-version 3.13 --no-annotate --no-header \
  --output-file requirements_lock.txt requirements.in
uv pip compile --generate-hashes --python-version 3.13 --no-annotate --no-header \
  --output-file tests/bazel/requirements_lock.txt tests/bazel/requirements.in
```

`MODULE.bazel.lock` is generated in each root and ignored. CI retains both locks,
resolved module graphs, the exact wheel, wheel hashes, test inventories/results,
coverage and source provenance in `sonic-platform-common-amd64`. Ordinary builds
may reuse Bazel's caches. No cache cleanup or whole-image rebuild is required to
validate this owner wheel.

To add an owner Python module, follow the existing package layout and update
`setup.py` where a new package is introduced. Bazel selects those directories
with a readable source glob; the independent package-contract test detects
missing or accidentally added wheel payload.
