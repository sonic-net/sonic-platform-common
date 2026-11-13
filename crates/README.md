# Building the platform API crates

`platform-api`, `platform-provider` and `platform-pyo3` are built from a full
sonic-platform-common checkout, used as a Cargo git dependency or a path
dependency. SONiC builds use this layout.

Build-time Rust generation requires the shared `crates/build_support.rs`,
`generator/`, `sonic_platform_api/*.pyi` and `sonic_platform_base/` sources,
plus a host Python interpreter with Jinja2. Select the interpreter with
`SONIC_PLATFORM_GENERATOR_PYTHON` when needed.

These crates are not published to a Cargo registry. Standalone `cargo package`
and `cargo vendor` layouts are not supported: they omit repository inputs
outside each crate directory. Vendor the complete repository and use path
dependencies when an offline source copy is needed.

Generated Rust sources live in Cargo `OUT_DIR`; they are not checked in.

The generated native `platform-base` crate uses the same full-checkout build
contract and is also not published to a Cargo registry.
