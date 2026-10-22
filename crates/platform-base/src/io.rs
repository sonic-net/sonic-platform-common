//! The filesystem, as platform code sees it, under a root tests can move.
//!
//! Every path here is the one the Python code names -- `/var/run/hw-management/
//! thermal/fan1_speed_get` -- and that is the path errors carry, because that
//! is what Python logs.  Only the syscall is redirected: under a test,
//! [`set_root`] puts a scratch directory beneath every path, so a fake sysfs
//! tree is read through exactly the code a switch runs.

use std::fs;
use std::path::PathBuf;
use std::sync::RwLock;

use crate::py::{PyErr, PyResult};

static ROOT: RwLock<Option<PathBuf>> = RwLock::new(None);

/// Put `root` beneath every path from now on; `None` for the real filesystem.
pub fn set_root(root: Option<PathBuf>) {
    if let Ok(mut r) = ROOT.write() {
        *r = root;
    }
}

/// Where `path` really is.
pub fn real(path: &str) -> PathBuf {
    match ROOT.read().ok().and_then(|r| r.clone()) {
        Some(root) => root.join(path.trim_start_matches('/')),
        None => PathBuf::from(path),
    }
}

/// `open(path).read()`: the text, or the `OSError` Python raises.
pub fn read_text(path: &str) -> PyResult<String> {
    let bytes = fs::read(real(path)).map_err(|e| PyErr::from_io(&e, Some(path)))?;
    crate::py::codec::decode_text(&bytes)
}

/// `open(path, 'w').write(text)`.
///
/// The file is opened -- and truncated -- before the text is encoded, so
/// text the locale's codec cannot take leaves it empty, as in Python.
pub fn write_text(path: &str, text: &str) -> PyResult<()> {
    let mut f = fs::File::create(real(path)).map_err(|e| PyErr::from_io(&e, Some(path)))?;
    crate::py::codec::encode_check(crate::py::codec::locale(), text)?;
    std::io::Write::write_all(&mut f, text.as_bytes()).map_err(|e| PyErr::from_io(&e, Some(path)))
}

/// `os.path.exists(path)`: true for a dangling link's target only if it exists.
pub fn exists(path: &str) -> bool {
    real(path).exists()
}

/// `os.path.isfile(path)`.
pub fn is_file(path: &str) -> bool {
    real(path).is_file()
}

/// `os.path.isdir(path)`.
pub fn is_dir(path: &str) -> bool {
    real(path).is_dir()
}

/// `os.path.islink(path)`.
pub fn is_link(path: &str) -> bool {
    fs::symlink_metadata(real(path)).is_ok_and(|m| m.file_type().is_symlink())
}

/// `os.path.realpath(path)` (not strict): symlinks resolved as far as the
/// path exists, the rest kept as written.
pub fn realpath(path: &str) -> String {
    fn resolve(path: &str, depth: usize) -> String {
        let mut out = String::from("/");
        let parts: Vec<&str> = path
            .split('/')
            .filter(|p| !p.is_empty() && *p != ".")
            .collect();
        for (i, part) in parts.iter().enumerate() {
            if *part == ".." {
                if let Some(pos) = out.trim_end_matches('/').rfind('/') {
                    out.truncate(pos + 1);
                }
                continue;
            }
            let candidate = join(&out, part);
            let link =
                fs::symlink_metadata(real(&candidate)).is_ok_and(|m| m.file_type().is_symlink());
            if link && depth < 40 {
                if let Ok(target) = fs::read_link(real(&candidate)) {
                    let t = target.to_string_lossy().into_owned();
                    let base = if t.starts_with('/') {
                        t
                    } else {
                        join(&out, &t)
                    };
                    let rest = parts[i + 1..].join("/");
                    let full = if rest.is_empty() {
                        base
                    } else {
                        join(&base, &rest)
                    };
                    return resolve(&full, depth + 1);
                }
            }
            out = candidate;
        }
        out
    }
    let abs = if path.starts_with('/') {
        path.to_string()
    } else {
        let cwd = std::env::current_dir()
            .map(|p| p.to_string_lossy().into_owned())
            .unwrap_or_default();
        join(&cwd, path)
    };
    resolve(&abs, 0)
}

/// `os.readlink(path)`.
pub fn readlink(path: &str) -> PyResult<String> {
    fs::read_link(real(path))
        .map(|p| p.to_string_lossy().into_owned())
        .map_err(|e| PyErr::from_io(&e, Some(path)))
}

/// `os.listdir(path)`, in the order the directory returns them.
pub fn listdir(path: &str) -> PyResult<Vec<String>> {
    let rd = fs::read_dir(real(path)).map_err(|e| PyErr::from_io(&e, Some(path)))?;
    let mut out = Vec::new();
    for e in rd {
        let e = e.map_err(|e| PyErr::from_io(&e, Some(path)))?;
        out.push(e.file_name().to_string_lossy().into_owned());
    }
    Ok(out)
}

/// `os.path.join(a, b)`: an absolute `b` replaces `a`.
pub fn join(a: &str, b: &str) -> String {
    if b.starts_with('/') || a.is_empty() {
        b.to_string()
    } else if a.ends_with('/') {
        format!("{a}{b}")
    } else {
        format!("{a}/{b}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::testing::Root;
    use std::os::unix::fs::symlink;

    #[test]
    fn paths_are_the_ones_python_names_under_a_moved_root() {
        let root = Root::new();
        assert_eq!(real("/a/b"), root.dir.join("a/b"));
        root.write("/etc/x", "1\n");
        assert_eq!(read_text("/etc/x").unwrap(), "1\n");
        write_text("/etc/y", "two").unwrap();
        assert_eq!(root.read("/etc/y").as_deref(), Some("two"));
        write_text("/etc/y", "").unwrap();
        assert_eq!(root.read("/etc/y").as_deref(), Some(""));
        assert_eq!(
            read_text("/nope").unwrap_err().str(),
            "[Errno 2] No such file or directory: '/nope'"
        );
        assert_eq!(
            write_text("/nope/x", "1").unwrap_err().str(),
            "[Errno 2] No such file or directory: '/nope/x'"
        );
        assert!(exists("/etc/x") && is_file("/etc/x") && !is_dir("/etc/x") && !is_link("/etc/x"));
        assert!(exists("/etc") && is_dir("/etc") && !is_file("/etc"));
        assert!(!exists("/nope") && !is_file("/nope") && !is_dir("/nope") && !is_link("/nope"));
        symlink("/etc/missing", root.real("/etc/dangling")).unwrap();
        assert!(is_link("/etc/dangling") && !exists("/etc/dangling"));
        let mut names = listdir("/etc").unwrap();
        names.sort();
        assert_eq!(names, ["dangling", "x", "y"]);
        assert_eq!(
            listdir("/nope").unwrap_err().str(),
            "[Errno 2] No such file or directory: '/nope'"
        );
        assert_eq!(
            listdir("/etc/x").unwrap_err().str(),
            "[Errno 20] Not a directory: '/etc/x'"
        );
    }

    #[test]
    fn realpath_resolves_links_as_far_as_the_path_exists() {
        let root = Root::new();
        std::fs::create_dir_all(root.real("/sys/devices/pci0/ata1/host0/sda")).unwrap();
        std::fs::create_dir_all(root.real("/sys/block/sda")).unwrap();
        // Absolute and relative targets, a chain, `..` and `.`.
        symlink(
            "/sys/devices/pci0/ata1/host0/sda",
            root.real("/sys/block/sda/device"),
        )
        .unwrap();
        symlink("devices/pci0", root.real("/sys/pci")).unwrap();
        symlink("../devices/pci0", root.real("/sys/block/up")).unwrap();
        symlink("/sys/pci/ata1", root.real("/sys/ata")).unwrap();
        assert_eq!(
            realpath("/sys/block/sda/device"),
            "/sys/devices/pci0/ata1/host0/sda"
        );
        assert_eq!(realpath("/sys/block/up"), "/sys/devices/pci0");
        assert_eq!(
            realpath("/sys/block/sda/device/queue/x"),
            "/sys/devices/pci0/ata1/host0/sda/queue/x"
        );
        assert_eq!(realpath("/sys/ata/host0"), "/sys/devices/pci0/ata1/host0");
        assert_eq!(realpath("/sys/./block/../block//sda/"), "/sys/block/sda");
        assert_eq!(realpath("/../sys"), "/sys");
        assert_eq!(realpath("/not/there"), "/not/there");
        // A loop gives up after 40 links rather than going round for ever.
        symlink("/loop/b", root.real("/a")).unwrap();
        std::fs::create_dir_all(root.real("/loop")).unwrap();
        symlink("/a", root.real("/loop/b")).unwrap();
        assert!(realpath("/a").starts_with('/'));
        // A relative path is taken from the working directory.
        let cwd = std::env::current_dir()
            .unwrap()
            .to_string_lossy()
            .into_owned();
        assert_eq!(realpath("rel"), join(&cwd, "rel"));
    }

    #[test]
    fn join_is_os_path_join() {
        assert_eq!(join("/a", "b"), "/a/b");
        assert_eq!(join("/a/", "b"), "/a/b");
        assert_eq!(join("/a", "/b"), "/b");
        assert_eq!(join("", "b"), "b");
        assert_eq!(join("a", ""), "a/");
    }
}
