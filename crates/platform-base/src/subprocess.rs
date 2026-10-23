//! The parts of Python's `subprocess` the base classes and vendors use, with
//! the exceptions it raises and their text: a command that fails is logged
//! by `str()` of the `CalledProcessError`, which quotes the whole argv.

use std::io::Read;
use std::os::unix::process::ExitStatusExt;
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant};

use crate::py::{codec, PyErr, PyResult, PyVal};

/// `Popen.returncode`: the exit code, or minus the signal that killed it.
pub fn returncode(st: ExitStatus) -> i32 {
    st.code().or_else(|| st.signal().map(|s| -s)).unwrap_or(-1)
}

/// `str(cmd)` of an argv list.
fn cmd_str(argv: &[&str]) -> String {
    PyVal::List(argv.iter().map(|a| PyVal::str(*a)).collect()).py_repr()
}

/// `repr(signal.Signals(n))`, or None for a number the enum lacks.
fn signal_repr(n: i32) -> Option<String> {
    const NAMES: [&str; 31] = [
        "SIGHUP",
        "SIGINT",
        "SIGQUIT",
        "SIGILL",
        "SIGTRAP",
        "SIGABRT",
        "SIGBUS",
        "SIGFPE",
        "SIGKILL",
        "SIGUSR1",
        "SIGSEGV",
        "SIGUSR2",
        "SIGPIPE",
        "SIGALRM",
        "SIGTERM",
        "SIGSTKFLT",
        "SIGCHLD",
        "SIGCONT",
        "SIGSTOP",
        "SIGTSTP",
        "SIGTTIN",
        "SIGTTOU",
        "SIGURG",
        "SIGXCPU",
        "SIGXFSZ",
        "SIGVTALRM",
        "SIGPROF",
        "SIGWINCH",
        "SIGIO",
        "SIGPWR",
        "SIGSYS",
    ];
    let name = match n {
        1..=31 => NAMES[(n - 1) as usize],
        34 => "SIGRTMIN",
        64 => "SIGRTMAX",
        _ => return None,
    };
    Some(format!("<Signals.{name}: {n}>"))
}

/// `CalledProcessError(returncode, cmd)`.
pub fn called_process_error(argv: &[&str], rc: i32) -> PyErr {
    let cmd = cmd_str(argv);
    let msg = if rc < 0 {
        match signal_repr(-rc) {
            Some(sig) => format!("Command '{cmd}' died with {sig}."),
            None => format!("Command '{cmd}' died with unknown signal {}.", -rc),
        }
    } else {
        format!("Command '{cmd}' returned non-zero exit status {rc}.")
    };
    PyErr::other("CalledProcessError", msg)
}

/// What `Popen()` raises before anything runs: an argument it cannot pass
/// to exec, or a program that is not there.
fn spawn(argv: &[&str], cmd: &mut Command) -> PyResult<Child> {
    for a in argv {
        codec::encode_check(codec::locale(), a)?;
        if a.contains('\0') {
            return Err(PyErr::value_error("embedded null byte"));
        }
    }
    cmd.spawn().map_err(|e| PyErr::from_io(&e, Some(argv[0])))
}

/// `check_call(argv, stdout=DEVNULL, stderr=PIPE)`: the pipe is never read,
/// only closed once the command is done.
pub fn check_call_quiet(argv: &[&str]) -> PyResult<()> {
    let mut child = spawn(
        argv,
        Command::new(argv[0])
            .args(&argv[1..])
            .stdout(Stdio::null())
            .stderr(Stdio::piped()),
    )?;
    let st = child.wait().map_err(|e| PyErr::from_io(&e, None))?;
    drop(child.stderr.take());
    match returncode(st) {
        0 => Ok(()),
        rc => Err(called_process_error(argv, rc)),
    }
}

/// `Popen(argv, stdout=PIPE, stderr=PIPE).communicate()`: no timeout.
pub fn communicate(argv: &[&str]) -> PyResult<Completed> {
    let child = spawn(
        argv,
        Command::new(argv[0])
            .args(&argv[1..])
            .stdin(Stdio::inherit())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped()),
    )?;
    let out = child
        .wait_with_output()
        .map_err(|e| PyErr::from_io(&e, None))?;
    Ok(Completed {
        returncode: returncode(out.status),
        stdout: out.stdout,
        stderr: out.stderr,
    })
}

/// `subprocess.run(argv, capture_output=True, timeout=...)`'s answer.
pub struct Completed {
    pub returncode: i32,
    pub stdout: Vec<u8>,
    pub stderr: Vec<u8>,
}

/// `subprocess.run(argv, capture_output=True, timeout=timeout)`.  Past the
/// timeout -- counted until both pipes are closed, as `communicate()` counts
/// it -- the command is killed and reaped, and `TimeoutExpired` is raised.
pub fn run_capture(argv: &[&str], timeout: Duration) -> PyResult<Completed> {
    let mut child = spawn(
        argv,
        Command::new(argv[0])
            .args(&argv[1..])
            .stdin(Stdio::inherit())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped()),
    )?;
    let deadline = Instant::now() + timeout;
    let (tx, rx) = mpsc::channel();
    for (k, pipe) in [
        (
            0,
            child
                .stdout
                .take()
                .map(|p| Box::new(p) as Box<dyn Read + Send>),
        ),
        (
            1,
            child
                .stderr
                .take()
                .map(|p| Box::new(p) as Box<dyn Read + Send>),
        ),
    ] {
        let tx = tx.clone();
        if let Some(mut p) = pipe {
            thread::spawn(move || {
                let mut buf = Vec::new();
                let _ = p.read_to_end(&mut buf);
                let _ = tx.send((k, buf));
            });
        }
    }
    drop(tx);
    let mut out = [Vec::new(), Vec::new()];
    let mut closed = 0;
    let timed_out = loop {
        if closed == 2 {
            break false;
        }
        match rx.recv_timeout(deadline.saturating_duration_since(Instant::now())) {
            Ok((k, buf)) => {
                out[k] = buf;
                closed += 1;
            }
            Err(mpsc::RecvTimeoutError::Timeout) => break true,
            Err(mpsc::RecvTimeoutError::Disconnected) => break false,
        }
    };
    if !timed_out {
        // Both pipes closed; what is left of the wait counts too.
        loop {
            match child.try_wait() {
                Ok(Some(st)) => {
                    let [stdout, stderr] = out;
                    return Ok(Completed {
                        returncode: returncode(st),
                        stdout,
                        stderr,
                    });
                }
                Ok(None) if Instant::now() < deadline => thread::sleep(Duration::from_millis(5)),
                Ok(None) => break,
                Err(e) => return Err(PyErr::from_io(&e, None)),
            }
        }
    }
    let _ = child.kill();
    let _ = child.wait();
    Err(PyErr::other(
        "TimeoutExpired",
        format!(
            "Command '{}' timed out after {} seconds",
            cmd_str(argv),
            crate::py::float_repr(timeout.as_secs_f64()).trim_end_matches(".0")
        ),
    ))
}

/// `text=True`'s decoding: the locale's codec, strict, universal newlines.
pub fn text(b: &[u8]) -> PyResult<String> {
    codec::decode_text(b)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn failures_read_as_python_words_them() {
        assert_eq!(
            check_call_quiet(&["false"]).unwrap_err().str(),
            "Command '['false']' returned non-zero exit status 1."
        );
        assert_eq!(
            check_call_quiet(&["sh", "-c", "kill -9 $$"])
                .unwrap_err()
                .str(),
            "Command '['sh', '-c', 'kill -9 $$']' died with <Signals.SIGKILL: 9>."
        );
        assert_eq!(
            called_process_error(&["x"], -40).str(),
            "Command '['x']' died with unknown signal 40."
        );
        assert_eq!(
            check_call_quiet(&["/nonexistent/x"]).unwrap_err().str(),
            "[Errno 2] No such file or directory: '/nonexistent/x'"
        );
        assert_eq!(
            check_call_quiet(&["true", "a\0b"]).unwrap_err().str(),
            "embedded null byte"
        );
        assert!(check_call_quiet(&["sh", "-c", "echo hi >&2"]).is_ok());
    }

    #[test]
    fn run_capture_collects_and_times_out() {
        let c = run_capture(
            &["sh", "-c", "printf 'a\\r\\nb'; echo e >&2; exit 3"],
            Duration::from_secs(5),
        )
        .unwrap();
        assert_eq!(c.returncode, 3);
        assert_eq!(text(&c.stdout).unwrap(), "a\nb");
        assert_eq!(c.stderr, b"e\n");
        let t = Instant::now();
        let e = run_capture(&["sleep", "5"], Duration::from_millis(200))
            .err()
            .unwrap();
        assert!(t.elapsed() < Duration::from_secs(2));
        assert_eq!(
            e.str(),
            "Command '['sleep', '5']' timed out after 0.2 seconds"
        );
        assert_eq!(
            run_capture(&["sleep", "5"], Duration::from_secs(0))
                .err()
                .unwrap()
                .str(),
            "Command '['sleep', '5']' timed out after 0 seconds"
        );
        assert!(text(b"\xff").is_err());
        assert_eq!(
            check_call_quiet(&["true", "\u{e4}"]).unwrap_err().str(),
            "'ascii' codec can't encode character '\\xe4' in position 0: ordinal not in range(128)"
        );
    }
}
