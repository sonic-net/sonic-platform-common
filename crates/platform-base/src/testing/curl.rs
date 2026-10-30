//! [`FakeCurl`] stands in for `/usr/bin/curl` under a [`RedfishClient`]: a
//! shell script that answers each request from the replies a test sets, by
//! method and path, and records the requests in order.  It is run as
//! `sh <script>`, so no test ever executes a file another thread may still
//! hold open for writing.
//!
//! [`RedfishClient`]: crate::redfish_client::RedfishClient

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use crate::redfish_client::REDFISH_URI_SESSION_SERVICE;

static COUNTER: AtomicU64 = AtomicU64::new(0);

/// What cURL does for one request of a sequence.
#[derive(Clone, Copy, Debug)]
pub enum Answer<'a> {
    /// Answers with this HTTP status and body.
    Reply(u16, &'a str),
    /// Exits with this code, saying this on stderr.
    Fail(i32, &'a str),
}

/// The method is `-X`'s, else POST with data, else GET, as cURL's.
/// Answers from `<method><path>` with `/` as `_`: `.out` is printed (or
/// written to `--output`'s file) before the status line `-w` asks for, which
/// `.nostatus` leaves out; `.code` is the HTTP status; `.rc` makes cURL
/// itself fail with that exit code and `.err` on stderr.  With `.count`, the
/// answer is the next of `.1`, `.2`, ... and the last one repeats.  Anything
/// not set is a Redfish 404.  Every command line is logged whole, too.
const SCRIPT: &str = r#"d=$(dirname "$0"); m=; u=; data=; of=
printf '%s' "$*" | tr '\n' ' ' >> "$d/commands"; echo >> "$d/commands"
while [ $# -gt 0 ]; do
  case $1 in
    -X|--request) m=$2; shift ;;
    -d|--data|-F|--form) data=$2; shift ;;
    -o|--output) of=$2; shift ;;
    http://*|https://*) u=$1 ;;
  esac
  shift
done
[ -z "$m" ] && { [ -n "$data" ] && m=POST || m=GET; }
p=/${u#*://*/}
echo "$m $p" >> "$d/requests"
k=$(printf '%s%s' "$m" "$p" | tr '/' '_')
if [ -f "$d/$k.count" ]; then
  n=$(( $(cat "$d/$k.n" 2>/dev/null || echo 0) + 1 ))
  [ "$n" -gt "$(cat "$d/$k.count")" ] && n=$(cat "$d/$k.count")
  echo "$n" > "$d/$k.n"; k=$k.$n
fi
if [ -f "$d/$k.rc" ]; then
  cat "$d/$k.err" >&2 2>/dev/null
  exit "$(cat "$d/$k.rc")"
fi
if [ -f "$d/$k.out" ]; then
  src="$d/$k.out"; code=$(cat "$d/$k.code")
else
  src="$d/default.out"; code=404
fi
if [ -n "$of" ]; then cat "$src" > "$of"; else cat "$src"; fi
[ -f "$d/$k.nostatus" ] || printf '\nHTTP Status Code: %s' "$code"
"#;

/// A scripted cURL in a scratch directory, removed when dropped.
pub struct FakeCurl {
    dir: PathBuf,
}

impl Default for FakeCurl {
    fn default() -> Self {
        FakeCurl::new()
    }
}

impl FakeCurl {
    /// A cURL whose BMC lets anyone log in -- as session `s1`, token
    /// `tok1` -- and out again.
    pub fn new() -> FakeCurl {
        let dir = std::env::temp_dir().join(format!(
            "fake-curl-{}-{}",
            std::process::id(),
            COUNTER.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir_all(&dir).expect("fake curl dir");
        std::fs::write(dir.join("curl"), SCRIPT).expect("fake curl script");
        std::fs::write(
            dir.join("default.out"),
            r#"{"error": {"code": "Base.1.8.ResourceNotFound", "message": "not found"}}"#,
        )
        .expect("fake curl default");
        let c = FakeCurl { dir };
        c.reply_raw(
            "POST",
            REDFISH_URI_SESSION_SERVICE,
            201,
            &format!(
                "HTTP/1.1 201 Created\r\nX-Auth-Token: tok1\r\nLocation: {REDFISH_URI_SESSION_SERVICE}/s1\r\n\r\n{{\"Id\": \"s1\"}}"
            ),
        );
        c.reply(
            "DELETE",
            &format!("{REDFISH_URI_SESSION_SERVICE}/s1"),
            200,
            r#"{"@Message.ExtendedInfo": [{"MessageId": "Base.1.15.Success"}]}"#,
        );
        c
    }

    /// What to give `RedfishClient::new` as the cURL path.
    pub fn path(&self) -> String {
        format!("sh {}", self.dir.join("curl").display())
    }

    /// The file holding `ext` of the answer to `method path` (a path may
    /// hold dots, so not `with_extension`).
    fn file(&self, method: &str, path: &str, ext: &str) -> PathBuf {
        self.dir.join(format!(
            "{}.{ext}",
            format!("{method}{path}").replace('/', "_")
        ))
    }

    /// The scratch directory, for files a test has cURL write.
    pub fn dir(&self) -> &Path {
        &self.dir
    }

    /// `method path` answers `status` with `body` (headers included, if
    /// the request dumps them).
    pub fn reply_raw(&self, method: &str, path: &str, status: u16, body: &str) {
        self.forget(method, path);
        std::fs::write(self.file(method, path, "out"), body).expect("reply");
        std::fs::write(self.file(method, path, "code"), status.to_string()).expect("reply");
    }

    /// `method path` prints `output` and no status line.
    pub fn reply_without_status(&self, method: &str, path: &str, output: &str) {
        self.reply_raw(method, path, 200, output);
        std::fs::write(self.file(method, path, "nostatus"), "").expect("reply");
    }

    /// `method path` answers each of `answers` in turn, the last again and
    /// again.
    pub fn answers(&self, method: &str, path: &str, answers: &[Answer]) {
        self.forget(method, path);
        for (i, a) in answers.iter().enumerate() {
            let n = i + 1;
            match *a {
                Answer::Reply(status, body) => {
                    std::fs::write(self.file(method, path, &format!("{n}.out")), body)
                        .expect("answer");
                    std::fs::write(
                        self.file(method, path, &format!("{n}.code")),
                        status.to_string(),
                    )
                    .expect("answer");
                }
                Answer::Fail(rc, stderr) => {
                    std::fs::write(self.file(method, path, &format!("{n}.rc")), rc.to_string())
                        .expect("answer");
                    std::fs::write(self.file(method, path, &format!("{n}.err")), stderr)
                        .expect("answer");
                }
            }
        }
        std::fs::write(self.file(method, path, "count"), answers.len().to_string())
            .expect("answer");
    }

    /// `method path` answers `status` with a JSON `body`.
    pub fn reply(&self, method: &str, path: &str, status: u16, body: &str) {
        self.reply_raw(method, path, status, body);
    }

    /// `method path` makes cURL exit with `rc`, saying `stderr`.
    pub fn fail(&self, method: &str, path: &str, rc: i32, stderr: &str) {
        self.forget(method, path);
        std::fs::write(self.file(method, path, "rc"), rc.to_string()).expect("fail");
        std::fs::write(self.file(method, path, "err"), stderr).expect("fail");
    }

    /// `method path` is answered by the default 404 again.
    pub fn forget(&self, method: &str, path: &str) {
        for ext in ["out", "code", "rc", "err", "nostatus", "count", "n"] {
            let _ = std::fs::remove_file(self.file(method, path, ext));
        }
    }

    /// The requests so far, `METHOD path` each, and forget them.
    pub fn take_requests(&self) -> Vec<String> {
        let f = self.dir.join("requests");
        let r = std::fs::read_to_string(&f).unwrap_or_default();
        let _ = std::fs::remove_file(f);
        r.lines().map(str::to_string).collect()
    }
}

impl FakeCurl {
    /// The command lines so far, each whole (a newline in an argument
    /// becomes a space), and forget them.
    pub fn take_commands(&self) -> Vec<String> {
        let f = self.dir.join("commands");
        let r = std::fs::read_to_string(&f).unwrap_or_default();
        let _ = std::fs::remove_file(f);
        r.lines().map(str::to_string).collect()
    }
}

impl Drop for FakeCurl {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.dir);
    }
}
