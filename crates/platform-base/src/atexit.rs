//! `atexit.register`, for a process that does not finalise an interpreter.
//!
//! The PyO3 bridge runs Python's `atexit` handlers from `finalize()`
//! (`platform_pyo3::run_python_atexit_handlers`), because a vendor registers
//! cleanup there -- mlnx's thermal updater removes the files it fed
//! hw-management.  A native implementation registers the same cleanup here,
//! at the point its Python counterpart called `atexit.register`, and
//! [`BaseFacade`](crate::BaseFacade)'s `finalize()` runs them: in reverse order
//! of registration, each once, as CPython does.

use std::sync::Mutex;

type Handler = Box<dyn FnOnce() + Send>;

static HANDLERS: Mutex<Vec<Handler>> = Mutex::new(Vec::new());

/// `atexit.register(f)`.
pub fn register<F: FnOnce() + Send + 'static>(f: F) {
    if let Ok(mut h) = HANDLERS.lock() {
        h.push(Box::new(f));
    }
}

/// `atexit._run_exitfuncs()`: last registered first, and each only once.
///
/// The list is taken whole, so no lock is held while a handler runs.  A
/// handler a handler registers is dropped, not run: CPython clears the list
/// once it has run it, newcomers included, and a second call finds nothing.
pub fn run() {
    let handlers = HANDLERS
        .lock()
        .map(|mut h| std::mem::take(&mut *h))
        .unwrap_or_default();
    for f in handlers.into_iter().rev() {
        f();
    }
    if let Ok(mut h) = HANDLERS.lock() {
        h.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

    /// One test, not two: the handlers are process-wide, and two tests
    /// running them at once would take each other's.
    #[test]
    fn handlers_run_last_first_and_only_once_and_newcomers_not_at_all() {
        let seen = Arc::new(Mutex::new(Vec::new()));
        for n in 1..=3 {
            let seen = seen.clone();
            register(move || {
                seen.lock().unwrap().push(n);
                if n == 2 {
                    // Registered while the handlers run: CPython drops it.
                    let seen = seen.clone();
                    register(move || seen.lock().unwrap().push(99));
                }
            });
        }
        run();
        run();
        assert_eq!(*seen.lock().unwrap(), vec![3, 2, 1]);
    }
}
