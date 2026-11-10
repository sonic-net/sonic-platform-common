// Shared build-script entry point for crates generated from the platform API.
use std::env;
use std::fs;
use std::path::Path;
use std::process::Command;

fn watch_sources(path: &Path, extension: Option<&str>) {
    println!("cargo:rerun-if-changed={}", path.display());
    let mut entries: Vec<_> = fs::read_dir(path)
        .unwrap_or_else(|error| panic!("cannot read generator input {}: {error}", path.display()))
        .map(|entry| entry.expect("generator input directory entry"))
        .collect();
    entries.sort_by_key(|entry| entry.file_name());
    for entry in entries {
        if matches!(
            entry.file_name().to_str(),
            Some("__pycache__" | "build" | "target")
        ) {
            continue;
        }
        let entry_path = entry.path();
        if entry.file_type().expect("generator input type").is_dir() {
            watch_sources(&entry_path, extension);
        } else if extension
            .is_none_or(|value| entry_path.extension().is_some_and(|ext| ext == value))
        {
            println!("cargo:rerun-if-changed={}", entry_path.display());
        }
    }
}

fn generate() {
    // Resolve the real repository even when a platform assembles the crates
    // using directory symlinks beside its native provider.
    let crate_dir = fs::canonicalize(env::var_os("CARGO_MANIFEST_DIR").expect("crate directory"))
        .expect("canonical crate directory");
    let crates_dir = crate_dir.parent().expect("common crates directory");
    let root = crates_dir.parent().expect("common repository directory");
    println!(
        "cargo:rerun-if-changed={}",
        crate_dir.join("build.rs").display()
    );
    println!(
        "cargo:rerun-if-changed={}",
        crates_dir.join("build_support.rs").display()
    );
    watch_sources(&root.join("generator"), None);
    watch_sources(&root.join("sonic_platform_api"), Some("pyi"));
    watch_sources(&root.join("sonic_platform_base"), Some("py"));
    println!("cargo:rerun-if-env-changed=SONIC_PLATFORM_GENERATOR_PYTHON");
    println!("cargo:rerun-if-env-changed=PYTHONPATH");
    let python = env::var_os("SONIC_PLATFORM_GENERATOR_PYTHON").unwrap_or_else(|| "python3".into());
    let crate_name = env::var("CARGO_PKG_NAME").expect("crate name");
    let output = env::var_os("OUT_DIR").expect("Cargo output directory");
    let status = Command::new(&python)
        .arg(root.join("generator/build.py"))
        .args(["--crate", &crate_name, "--out-dir"])
        .arg(&output)
        .env("PYTHONDONTWRITEBYTECODE", "1")
        .current_dir(root)
        .status()
        .unwrap_or_else(|error| {
            panic!(
                "cannot run platform generator using {python:?}: {error}; set SONIC_PLATFORM_GENERATOR_PYTHON to the host Python interpreter"
            )
        });
    assert!(
        status.success(),
        "platform generator failed for {crate_name}: {status}; the host Python must provide Jinja2 and the complete platform-common generator/stub sources; set SONIC_PLATFORM_GENERATOR_PYTHON to that interpreter"
    );
    // Missing or externally edited output must rerun generation as well.
    watch_sources(Path::new(&output), None);
}
