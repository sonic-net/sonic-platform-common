//! A scratch root beneath every path the crate reads or writes, one test at
//! a time: [`io::set_root`] is process-wide, so a test holds the lock for as
//! long as its root is in place.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Mutex, MutexGuard};

use crate::io;

static LOCK: Mutex<()> = Mutex::new(());
static COUNTER: AtomicU64 = AtomicU64::new(0);

pub struct Root {
    _guard: MutexGuard<'static, ()>,
    pub dir: PathBuf,
}

impl Default for Root {
    fn default() -> Self {
        Root::new()
    }
}

impl Root {
    pub fn new() -> Root {
        let guard = LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let dir = std::env::temp_dir().join(format!(
            "platform-base-test-{}-{}",
            std::process::id(),
            COUNTER.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir_all(&dir).expect("scratch root");
        io::set_root(Some(dir.clone()));
        Root { _guard: guard, dir }
    }

    /// `path` (as the code names it) with `content`, parents made.
    pub fn write(&self, path: &str, content: &str) {
        let p = io::real(path);
        if let Some(parent) = p.parent() {
            std::fs::create_dir_all(parent).expect("parent");
        }
        std::fs::write(p, content).expect("write");
    }

    /// `path`'s content, if it is there.
    pub fn read(&self, path: &str) -> Option<String> {
        std::fs::read_to_string(io::real(path)).ok()
    }

    /// Where `path` really is.
    pub fn real(&self, path: &str) -> PathBuf {
        io::real(path)
    }

    /// Whether `path` is there.
    pub fn exists(&self, path: &str) -> bool {
        Path::new(&io::real(path)).exists()
    }
}

impl Drop for Root {
    fn drop(&mut self) {
        io::set_root(None);
        let _ = std::fs::remove_dir_all(&self.dir);
    }
}
