#!/bin/sh
# Every gate the platform API facade has, in the order a failure is cheapest
# to read.  CI runs this; so should anyone who edited the stub.
#
# generator/scope_scan.py is deliberately not here.  It reads the daemon, CLI
# and conformance-suite trees, which live in other repositories and are not
# present in this repo's CI job; it is a scoping tool for whoever edits the
# stub, not a per-commit gate.
set -e
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

echo '== the stub type-checks =='
mypy --config-file generator/mypy.ini platform_api/

echo '== the generated Python matches the stub =='
stubtest platform_api.facade --allowlist platform_api/stubtest_allowlist.txt

echo '== the generated files are what the generator produces =='
(cd generator && python3 generate.py --check)

# api_coverage.py reads only the checked-in inventory and the stub, so unlike
# scope_scan.py it does run here.  It fails on an omission nothing reaches any
# more -- a reason that has stopped being true.
echo '== the omissions still name something =='
python3 generator/api_coverage.py --check

echo '== the facade behaves =='
python3 -m pytest tests/platform_api_facade_test.py tests/platform_api_schema_test.py -q --no-cov

echo '== the Rust side builds clean =='
cargo clippy --manifest-path crates/platform-pyo3/Cargo.toml --all-targets -- -D warnings

echo '== Rust reads what Python wrote =='
cargo test --manifest-path crates/platform-pyo3/Cargo.toml
