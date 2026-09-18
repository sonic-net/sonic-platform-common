# Rust checks for the crates under crates/.
#
# The Python half of this repository is driven by setup.py and pytest; nothing
# here touches it.  These targets exist so that the Rust checks are named and
# reproducible rather than remembered, and so that a contributor runs locally
# exactly what CI will run.  The target names match sonic-dash-ha's, which is
# the only other Rust in SONiC.
#
#   make ci-all
#
.ONESHELL:
SHELL = /bin/bash
.SHELLFLAGS += -e

CRATES = crates/platform-traits

.PHONY: ci-all ci-format ci-lint ci-build ci-doc ci-test format

ci-all: ci-format ci-lint ci-build ci-doc ci-test

# Formatting is not negotiable and not reviewed by hand: rustfmt.toml at the
# repository root is the policy, and this fails the build when a file departs
# from it.
ci-format:
	for c in $(CRATES); do cargo fmt --check --all --manifest-path $$c/Cargo.toml; done

# clippy::all denied, not warned.  --no-deps keeps the verdict about this
# repository's code rather than its dependencies'.
ci-lint:
	for c in $(CRATES); do \
	  cargo clippy --all-targets --all-features --no-deps --manifest-path $$c/Cargo.toml -- --deny "clippy::all"; \
	done

# The fixer, for local use.  CI never runs this one.
format:
	for c in $(CRATES); do cargo fmt --all --manifest-path $$c/Cargo.toml; done

# Warnings are errors.  Debug and release both, because a cfg or a lint can
# differ between the two and the shipped artifact is the release one.
#
# sonic-dash-ha runs `cargo clean` between the two passes; that is a disk-space
# measure for its agent pool, and it would throw away a contributor's build
# cache every time they ran this.  Omitted: debug and release use separate
# target directories, so they do not collide.
ci-build:
	for c in $(CRATES); do \
	  RUSTFLAGS="--deny warnings" cargo build --all-features --manifest-path $$c/Cargo.toml; \
	  RUSTFLAGS="--deny warnings" cargo build --all-features --release --manifest-path $$c/Cargo.toml; \
	done

# A broken intra-doc link is a broken link whether or not anything reads it.
# --no-deps keeps the verdict about this repository's documentation.
ci-doc:
	for c in $(CRATES); do \
	  RUSTDOCFLAGS="--deny warnings" cargo doc --all-features --no-deps --manifest-path $$c/Cargo.toml; \
	  RUSTDOCFLAGS="--deny warnings" cargo doc --all-features --no-deps --release --manifest-path $$c/Cargo.toml; \
	done

ci-test:
	for c in $(CRATES); do \
	  cargo test --all-features --manifest-path $$c/Cargo.toml; \
	  cargo test --all-features --release --manifest-path $$c/Cargo.toml; \
	done
