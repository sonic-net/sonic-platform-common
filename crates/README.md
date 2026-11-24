# Building the platform API crates

`platform-api`, `platform-provider` and `platform-pyo3` are built from a full
sonic-platform-common checkout, used as a Cargo git dependency or a path
dependency. SONiC builds use this layout.

Build-time Rust generation requires the shared `crates/build_support.rs`,
`generator/`, `sonic_platform_api/*.pyi` and `sonic_platform_base/` sources,
plus a host Python interpreter with Jinja2. Select the interpreter with
`SONIC_PLATFORM_GENERATOR_PYTHON` when needed.

The build-time generator runs with `PYTHONPATH` removed. Install Jinja2 in
the selected interpreter's system, user-site or virtual environment;
`pip install --target` plus `PYTHONPATH` alone is insufficient.

These crates are not published to a Cargo registry. Standalone `cargo package`
and `cargo vendor` layouts are not supported: they omit repository inputs
outside each crate directory. Vendor the complete repository and use path
dependencies when an offline source copy is needed.

Generated Rust sources live in Cargo `OUT_DIR`; they are not checked in.

Cargo tracks the generator entry point and every local Python module imported
during rendering, including transitive helpers. Add helpers with normal Python
imports so edits to them regenerate the Rust outputs. Runtime `PYTHONPATH`,
bytecode caches and developer-only shell scripts are not generator inputs.
