#!/bin/sh
# Every gate the platform API facade has, in the order a failure is cheapest
# to read.  CI runs this; so should anyone who edited the stub.
#
# generator/scope_scan.py is deliberately not here.  It reads the daemon, CLI
# and conformance-suite trees, which live in other repositories and are not
# present in this repo's CI job; it is a scoping tool for whoever edits the
# stub, not a per-commit gate.
#
# --python-only skips the cargo steps, for a runner with the Python toolchain
# but no Rust one.  The crates need nothing else: libpython, and this checkout
# on PYTHONPATH.  CI runs them in a step of its own, with line coverage.
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

python_only=''
[ "${1:-}" = '--python-only' ] && python_only=1

# mypy is not in the base image; it arrives with the `testing` extra.  Saying so
# here is the difference between a readable failure and `No module named mypy`
# in the middle of a build log.
#
# Both tools run as modules of the interpreter that runs everything else here,
# not as commands on PATH: CI installs the extra without root, so pip puts the
# `mypy` and `stubtest` scripts in ~/.local/bin, which is not on PATH there.
if ! python3 -c 'import mypy.stubtest' 2>/dev/null; then
    echo "check.sh needs mypy and stubtest: pip3 install '.[testing]'" >&2
    exit 1
fi

echo '== the stub type-checks =='
python3 -m mypy --config-file generator/mypy.ini sonic_platform_api/

echo '== the generated Python matches the stub =='
python3 -m mypy.stubtest sonic_platform_api.facade \
    --allowlist sonic_platform_api/stubtest_allowlist.txt

echo '== the generated files are what the generator produces =='
(cd generator && python3 generate.py --check)

# api_coverage.py reads only the checked-in inventory and the stub, so unlike
# scope_scan.py it does run here.  It fails on an omission nothing reaches any
# more -- a reason that has stopped being true.
echo '== the omissions still name something =='
python3 generator/api_coverage.py --check

# pytest.ini's addopts write test-results.xml and the coverage reports.  CI
# runs this after the full suite and publishes those files afterwards, so this
# partial run must not write them over the full run's.
echo '== the facade behaves =='
python3 -m pytest tests/platform_api_facade_test.py tests/platform_api_schema_test.py -q -o addopts=''

[ -n "$python_only" ] && exit 0

# Formatting, of the hand-written Rust only: the generated files are declared
# `#[rustfmt::skip]` and held instead to what the generator writes, above.
echo '== the Rust side is formatted =='
cargo fmt --manifest-path crates/Cargo.toml --all -- --check

# The crates are one workspace (crates/Cargo.toml), linted and tested as one:
# --workspace makes every member a crate clippy lints, rather than a
# dependency it skips.
#
# --locked, as CI passes it: a manifest edited without the workspace lock, or
# the lock edited by hand, fails here rather than resolving afresh and passing
# on versions CI will refuse.
#
# The bridge's and the provider's tests import sonic_platform_api.facade, which
# is why PYTHONPATH is exported at the top of this file.
echo '== the Rust side builds clean =='
cargo clippy --locked --manifest-path crates/Cargo.toml --workspace --all-targets -- -D warnings

echo '== the trait, the bridge, the provider, the native stub, platform-base and platform-api-diff =='
cargo test --locked --manifest-path crates/Cargo.toml --workspace
