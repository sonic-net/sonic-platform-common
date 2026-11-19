//! [`FakeRedis`]: the SONiC redis instance, in process, speaking RESP2 on a
//! unix socket and on TCP.  There is one for the whole test run, as code under
//! test keeps its connections (ModuleBase's STATE_DB is one per process).  A
//! test puts it under its [`Root`]: the database config, and the instance's
//! socket linked to the server's.
//!
//! Beside the commands `db` sends it answers `FLUSHALL`; `RAW <reply>`, which
//! writes the reply verbatim; and `CLOSE`, which hangs up.  Any command naming
//! a key with `BROKEN` in it is an error reply, as a failing server's is.

use std::collections::{BTreeMap, HashMap};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::TcpListener;
use std::os::unix::net::UnixListener;
use std::path::PathBuf;
use std::sync::{Arc, Mutex, OnceLock};

use super::Root;
use crate::db::DB_CONFIG_FILE;

pub const CONFIG_DB: i64 = 4;
pub const STATE_DB: i64 = 6;

const SOCKET: &str = "/var/run/redis/redis.sock";

enum Value {
    Str(String),
    Hash(Vec<(String, String)>),
}

type Data = HashMap<i64, BTreeMap<String, Value>>;

pub struct FakeRedis {
    socket: PathBuf,
    port: u16,
    data: Arc<Mutex<Data>>,
}

static SERVER: OnceLock<FakeRedis> = OnceLock::new();

impl FakeRedis {
    /// The server, started on first use.
    pub fn get() -> &'static FakeRedis {
        SERVER.get_or_init(|| {
            let dir = std::env::temp_dir().join(format!("fake-redis-{}", std::process::id()));
            let _ = std::fs::remove_dir_all(&dir);
            std::fs::create_dir_all(&dir).expect("fake redis dir");
            let socket = dir.join("redis.sock");
            let data: Arc<Mutex<Data>> = Arc::default();
            let unix = UnixListener::bind(&socket).expect("fake redis socket");
            let tcp = TcpListener::bind("127.0.0.1:0").expect("fake redis port");
            let port = tcp.local_addr().expect("fake redis port").port();
            let d = data.clone();
            std::thread::spawn(move || {
                for s in unix.incoming().flatten() {
                    let d = d.clone();
                    std::thread::spawn(move || serve(s, &d));
                }
            });
            let d = data.clone();
            std::thread::spawn(move || {
                for s in tcp.incoming().flatten() {
                    let d = d.clone();
                    std::thread::spawn(move || serve(s, &d));
                }
            });
            FakeRedis { socket, port, data }
        })
    }

    pub fn port(&self) -> u16 {
        self.port
    }

    /// Under `root`: `database_config.json` naming APPL_DB, CONFIG_DB and
    /// STATE_DB on this server, and its socket where the config says.
    pub fn install(&self, root: &Root) {
        root.write(
            DB_CONFIG_FILE,
            &format!(
                r#"{{"INSTANCES": {{"redis": {{"hostname": "127.0.0.1", "port": {}, "unix_socket_path": "{SOCKET}"}}}},
"DATABASES": {{"APPL_DB": {{"id": 0, "separator": ":", "instance": "redis"}},
"CONFIG_DB": {{"id": {CONFIG_DB}, "separator": "|", "instance": "redis"}},
"STATE_DB": {{"id": {STATE_DB}, "separator": "|", "instance": "redis"}}}}}}"#,
                self.port
            ),
        );
        let link = root.real(SOCKET);
        let _ = std::fs::remove_file(&link);
        std::os::unix::fs::symlink(&self.socket, link).expect("socket link");
    }

    fn with<T>(&self, f: impl FnOnce(&mut Data) -> T) -> T {
        f(&mut self.data.lock().unwrap_or_else(|e| e.into_inner()))
    }

    pub fn flush(&self) {
        self.with(|d| d.clear());
    }

    pub fn set(&self, db: i64, key: &str, value: &str) {
        self.with(|d| {
            d.entry(db)
                .or_default()
                .insert(key.into(), Value::Str(value.into()))
        });
    }

    pub fn hset(&self, db: i64, key: &str, fields: &[(&str, &str)]) {
        self.with(|d| {
            for (f, v) in fields {
                hset(d.entry(db).or_default(), key, f, v);
            }
        });
    }

    pub fn hdel(&self, db: i64, key: &str, field: &str) {
        self.with(|d| {
            if let Some(Value::Hash(h)) = d.entry(db).or_default().get_mut(key) {
                h.retain(|(f, _)| f != field);
            }
        });
    }

    /// A hash's fields, in the order they were first written.
    pub fn hgetall(&self, db: i64, key: &str) -> Vec<(String, String)> {
        self.with(|d| match d.get(&db).and_then(|t| t.get(key)) {
            Some(Value::Hash(h)) => h.clone(),
            _ => Vec::new(),
        })
    }

    pub fn exists(&self, db: i64, key: &str) -> bool {
        self.with(|d| d.get(&db).is_some_and(|t| t.contains_key(key)))
    }
}

fn hset(t: &mut BTreeMap<String, Value>, key: &str, field: &str, value: &str) -> i64 {
    let e = t
        .entry(key.into())
        .or_insert_with(|| Value::Hash(Vec::new()));
    if let Value::Str(_) = e {
        *e = Value::Hash(Vec::new());
    }
    let Value::Hash(h) = e else { return 0 };
    match h.iter_mut().find(|(f, _)| f == field) {
        Some(slot) => {
            slot.1 = value.into();
            0
        }
        None => {
            h.push((field.into(), value.into()));
            1
        }
    }
}

/// `pattern` as a redis glob: `*` and `?`.
fn glob(pattern: &[u8], s: &[u8]) -> bool {
    match (pattern.first(), s.first()) {
        (None, None) => true,
        (Some(b'*'), _) => glob(&pattern[1..], s) || (!s.is_empty() && glob(pattern, &s[1..])),
        (Some(b'?'), Some(_)) => glob(&pattern[1..], &s[1..]),
        (Some(p), Some(c)) if p == c => glob(&pattern[1..], &s[1..]),
        _ => false,
    }
}

fn bulk(s: &str) -> String {
    format!("${}\r\n{s}\r\n", s.len())
}

fn array(items: &[String]) -> String {
    let mut out = format!("*{}\r\n", items.len());
    for i in items {
        out.push_str(&bulk(i));
    }
    out
}

/// One command's reply; None hangs up.
fn reply(d: &Mutex<Data>, db: &mut i64, args: &[String]) -> Option<String> {
    let cmd = args.first().map(|c| c.to_uppercase()).unwrap_or_default();
    let arg = |i: usize| args.get(i).map_or("", String::as_str);
    if args.iter().skip(1).any(|a| a.contains("BROKEN")) {
        return Some("-ERR broken key\r\n".into());
    }
    match cmd.as_str() {
        "SELECT" => {
            *db = arg(1).parse().unwrap_or_default();
            return Some("+OK\r\n".into());
        }
        "RAW" => return Some(arg(1).into()),
        "CLOSE" => return None,
        _ => {}
    }
    let mut d = d.lock().unwrap_or_else(|e| e.into_inner());
    if cmd == "FLUSHALL" {
        d.clear();
        return Some("+OK\r\n".into());
    }
    let t = d.entry(*db).or_default();
    Some(match cmd.as_str() {
        "GET" => match t.get(arg(1)) {
            Some(Value::Str(v)) => bulk(v),
            _ => "$-1\r\n".into(),
        },
        "SET" => {
            t.insert(arg(1).into(), Value::Str(arg(2).into()));
            "+OK\r\n".into()
        }
        "HGET" => match t.get(arg(1)) {
            Some(Value::Hash(h)) => h
                .iter()
                .find(|(f, _)| f == arg(2))
                .map_or("$-1\r\n".into(), |(_, v)| bulk(v)),
            _ => "$-1\r\n".into(),
        },
        "HSET" => {
            let added: i64 = args[2..]
                .chunks(2)
                .map(|fv| hset(t, arg(1), &fv[0], fv.get(1).map_or("", String::as_str)))
                .sum();
            format!(":{added}\r\n")
        }
        "HDEL" => {
            let mut n = 0;
            if let Some(Value::Hash(h)) = t.get_mut(arg(1)) {
                for f in &args[2..] {
                    let before = h.len();
                    h.retain(|(k, _)| k != f);
                    n += before - h.len();
                }
                if h.is_empty() {
                    t.remove(arg(1));
                }
            }
            format!(":{n}\r\n")
        }
        "HGETALL" => match t.get(arg(1)) {
            Some(Value::Hash(h)) => array(
                &h.iter()
                    .flat_map(|(f, v)| [f.clone(), v.clone()])
                    .collect::<Vec<_>>(),
            ),
            _ => "*0\r\n".into(),
        },
        "DEL" => format!(
            ":{}\r\n",
            args[1..]
                .iter()
                .filter(|k| t.remove(k.as_str()).is_some())
                .count()
        ),
        "EXISTS" => format!(":{}\r\n", i64::from(t.contains_key(arg(1)))),
        "KEYS" => array(
            &t.keys()
                .filter(|k| glob(arg(1).as_bytes(), k.as_bytes()))
                .cloned()
                .collect::<Vec<_>>(),
        ),
        other => format!("-ERR unknown command '{other}'\r\n"),
    })
}

/// A RESP array of bulk strings, as a client sends a command; None at EOF.
fn read_command(r: &mut impl BufRead) -> Option<Vec<String>> {
    let mut line = String::new();
    r.read_line(&mut line).ok().filter(|n| *n > 0)?;
    let n: usize = line.trim_end().strip_prefix('*')?.parse().ok()?;
    let mut args = Vec::with_capacity(n);
    for _ in 0..n {
        line.clear();
        r.read_line(&mut line).ok()?;
        let len: usize = line.trim_end().strip_prefix('$')?.parse().ok()?;
        let mut buf = vec![0u8; len + 2];
        r.read_exact(&mut buf).ok()?;
        buf.truncate(len);
        args.push(String::from_utf8_lossy(&buf).into_owned());
    }
    Some(args)
}

fn serve<S: Read + Write>(stream: S, data: &Mutex<Data>) {
    let mut r = BufReader::new(stream);
    let mut db = 0;
    while let Some(args) = read_command(&mut r) {
        let Some(out) = reply(data, &mut db, &args) else {
            return;
        };
        if r.get_mut().write_all(out.as_bytes()).is_err() {
            return;
        }
    }
}
