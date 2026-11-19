//! The SONiC databases, as `swsscommon`'s connectors reach them.
//!
//! A small Redis client rather than a binding to libswsscommon: what platform
//! code does with the databases is a handful of hash reads and writes, and a
//! vendor crate linking the C++ library -- with the bindgen step that needs
//! -- for that would be a large price.  The behaviour that matters is kept:
//! which instance and which numeric database a name means comes from
//! `database_config.json`, keys are `TABLE<sep>key` with that database's
//! separator, and `ConfigDBConnector.connect()` waits for CONFIG_DB to be
//! initialised before it answers.

use std::io::{BufRead, BufReader, Read, Write};
use std::os::unix::net::UnixStream;
use std::sync::Mutex;
use std::thread::sleep;
use std::time::Duration;

use crate::io;
use crate::json;
use crate::py::{PyErr, PyResult, PyVal};

/// `SonicDBConfig`'s default file.
pub const DB_CONFIG_FILE: &str = "/var/run/redis/sonic-db/database_config.json";

/// A reply, as RESP2 spells it.
#[derive(Clone, Debug, PartialEq)]
pub enum Reply {
    Status(String),
    Int(i64),
    Bulk(Option<Vec<u8>>),
    Array(Option<Vec<Reply>>),
}

impl Reply {
    pub fn into_string(self) -> Option<String> {
        match self {
            Reply::Status(s) => Some(s),
            Reply::Bulk(Some(b)) => Some(String::from_utf8_lossy(&b).into_owned()),
            Reply::Int(i) => Some(i.to_string()),
            _ => None,
        }
    }
}

/// A hash's fields, in the order redis answers them.
pub type Fields = Vec<(String, String)>;

/// A connection, over the instance's unix socket or over TCP.
trait Stream: Read + Write + Send {}
impl<T: Read + Write + Send> Stream for T {}

/// One connection to one database.
pub struct Db {
    name: String,
    separator: String,
    stream: Mutex<BufReader<Box<dyn Stream>>>,
}

/// Where a database lives: its instance, number and separator.
struct Location {
    instance: PyVal,
    id: i64,
    separator: String,
}

/// The instance socket, database number and separator for `name`.
fn locate(name: &str) -> PyResult<(String, i64, String)> {
    let loc = locate_instance(name)?;
    let socket = json::index(&loc.instance, "unix_socket_path")?.py_str();
    Ok((socket, loc.id, loc.separator))
}

fn locate_instance(name: &str) -> PyResult<Location> {
    let cfg = json::load(DB_CONFIG_FILE)?;
    let dbs = json::index(&cfg, "DATABASES")?;
    let db = json::index(dbs, name)?;
    let id = match json::index(db, "id")? {
        PyVal::Int(i) => i64::try_from(*i).unwrap_or_default(),
        other => {
            return Err(PyErr::type_error(format!(
                "database id is {}",
                other.type_name()
            )))
        }
    };
    let sep = json::get(db, "separator").map_or(":".to_string(), PyVal::py_str);
    let inst = json::index(db, "instance")?.py_str();
    let instance = json::index(json::index(&cfg, "INSTANCES")?, &inst)?.clone();
    Ok(Location {
        instance,
        id,
        separator: sep,
    })
}

fn io_err(e: std::io::Error) -> PyErr {
    PyErr::other("ConnectionError", e.to_string())
}

impl Db {
    /// Connect to the database named `name` (`"STATE_DB"`, `"CONFIG_DB"`).
    pub fn connect(name: &str) -> PyResult<Db> {
        let (socket, id, separator) = locate(name)?;
        let stream = UnixStream::connect(io::real(&socket)).map_err(io_err)?;
        Db::open(name, separator, Box::new(stream), id)
    }

    /// Connect over TCP to the instance's `hostname:port`, as a
    /// `SonicV2Connector` made without `use_unix_socket_path` does -- the
    /// `host` it is given is ignored, as in swsscommon.
    pub fn connect_tcp(name: &str) -> PyResult<Db> {
        let loc = locate_instance(name)?;
        let host = json::index(&loc.instance, "hostname")?.py_str();
        let port = match json::index(&loc.instance, "port")? {
            PyVal::Int(p) => u16::try_from(*p).unwrap_or_default(),
            other => return Err(PyErr::type_error(format!("port is {}", other.type_name()))),
        };
        let stream = std::net::TcpStream::connect((host.as_str(), port)).map_err(io_err)?;
        Db::open(name, loc.separator, Box::new(stream), loc.id)
    }

    /// `redis.Redis(host, port, db)`: redis-py's own client, which knows
    /// nothing of the database config.
    pub fn connect_addr(host: &str, port: u16, db: i64) -> PyResult<Db> {
        let stream = std::net::TcpStream::connect((host, port)).map_err(io_err)?;
        Db::open(
            &format!("{host}:{port}/{db}"),
            ":".to_string(),
            Box::new(stream),
            db,
        )
    }

    fn open(name: &str, separator: String, stream: Box<dyn Stream>, id: i64) -> PyResult<Db> {
        let db = Db {
            name: name.to_string(),
            separator,
            stream: Mutex::new(BufReader::new(stream)),
        };
        db.cmd(&["SELECT", &id.to_string()])?;
        Ok(db)
    }

    /// `ConfigDBConnector.connect()`: and then wait until CONFIG_DB says it
    /// has been loaded, as the connector does by default.
    ///
    /// "Says" is any value at all: swsscommon waits only while
    /// `CONFIG_DB_INITIALIZED` is missing or empty
    /// (`ConfigDBConnector_Native::db_connect`), so the `"0"` the database
    /// container writes before config-setup has run already counts.
    pub fn connect_config_db() -> PyResult<Db> {
        let db = Db::connect("CONFIG_DB")?;
        loop {
            let flag = db.cmd(&["GET", "CONFIG_DB_INITIALIZED"])?.into_string();
            if flag.is_some_and(|f| !f.is_empty()) {
                return Ok(db);
            }
            sleep(Duration::from_secs(1));
        }
    }

    pub fn name(&self) -> &str {
        &self.name
    }

    pub fn separator(&self) -> &str {
        &self.separator
    }

    /// `TABLE<sep>key`.
    pub fn key(&self, table: &str, key: &str) -> String {
        format!("{table}{}{key}", self.separator)
    }

    /// One command, and its reply; a Redis error reply is a `ResponseError`.
    pub fn cmd(&self, args: &[&str]) -> PyResult<Reply> {
        let mut req = format!("*{}\r\n", args.len());
        for a in args {
            req.push_str(&format!("${}\r\n{a}\r\n", a.len()));
        }
        let mut s = self
            .stream
            .lock()
            .map_err(|_| PyErr::runtime_error("database connection poisoned"))?;
        s.get_mut().write_all(req.as_bytes()).map_err(io_err)?;
        read_reply(&mut s)
    }

    /// `HGETALL key`, in the order Redis answers.
    pub fn hgetall(&self, key: &str) -> PyResult<Vec<(String, String)>> {
        let Reply::Array(Some(items)) = self.cmd(&["HGETALL", key])? else {
            return Ok(Vec::new());
        };
        let mut out = Vec::new();
        let mut it = items.into_iter();
        while let (Some(k), Some(v)) = (it.next(), it.next()) {
            out.push((
                k.into_string().unwrap_or_default(),
                v.into_string().unwrap_or_default(),
            ));
        }
        Ok(out)
    }

    pub fn hget(&self, key: &str, field: &str) -> PyResult<Option<String>> {
        Ok(self.cmd(&["HGET", key, field])?.into_string())
    }

    pub fn hset(&self, key: &str, fields: &[(&str, &str)]) -> PyResult<()> {
        let mut args = vec!["HSET", key];
        for (f, v) in fields {
            args.push(f);
            args.push(v);
        }
        self.cmd(&args).map(|_| ())
    }

    pub fn hdel(&self, key: &str, fields: &[&str]) -> PyResult<()> {
        let mut args = vec!["HDEL", key];
        args.extend_from_slice(fields);
        self.cmd(&args).map(|_| ())
    }

    pub fn del(&self, key: &str) -> PyResult<()> {
        self.cmd(&["DEL", key]).map(|_| ())
    }

    pub fn exists(&self, key: &str) -> PyResult<bool> {
        Ok(matches!(self.cmd(&["EXISTS", key])?, Reply::Int(n) if n > 0))
    }

    /// `KEYS pattern`.
    pub fn keys(&self, pattern: &str) -> PyResult<Vec<String>> {
        let Reply::Array(Some(items)) = self.cmd(&["KEYS", pattern])? else {
            return Ok(Vec::new());
        };
        Ok(items.into_iter().filter_map(Reply::into_string).collect())
    }

    /// Every `table|key` hash, by key, as redis answers them -- the part of
    /// `ConfigDBConnector.get_table(table)` its callers here need.  Not the
    /// rest: the table name is not upper-cased, the rows come in KEYS order
    /// rather than sorted, and the fields are the raw strings, without
    /// `raw_to_typed`'s lists or `deserialize_key`'s tuples.
    pub fn get_table(&self, table: &str) -> PyResult<Vec<(String, Fields)>> {
        let prefix = format!("{table}{}", self.separator);
        let mut out = Vec::new();
        for k in self.keys(&format!("{prefix}*"))? {
            let fields = self.hgetall(&k)?;
            out.push((k[prefix.len()..].to_string(), fields));
        }
        Ok(out)
    }
}

fn read_line(s: &mut BufReader<Box<dyn Stream>>) -> PyResult<String> {
    let mut line = String::new();
    s.read_line(&mut line).map_err(io_err)?;
    if line.is_empty() {
        return Err(PyErr::other(
            "ConnectionError",
            "Connection closed by server.",
        ));
    }
    Ok(line.trim_end_matches("\r\n").to_string())
}

fn read_reply(s: &mut BufReader<Box<dyn Stream>>) -> PyResult<Reply> {
    let line = read_line(s)?;
    let (kind, rest) = line.split_at(1.min(line.len()));
    match kind {
        "+" => Ok(Reply::Status(rest.to_string())),
        "-" => Err(PyErr::other("ResponseError", rest.to_string())),
        ":" => Ok(Reply::Int(rest.parse().unwrap_or_default())),
        "$" => {
            let n: i64 = rest.parse().unwrap_or(-1);
            if n < 0 {
                return Ok(Reply::Bulk(None));
            }
            let mut buf = vec![0u8; usize::try_from(n).unwrap_or_default() + 2];
            s.read_exact(&mut buf).map_err(io_err)?;
            buf.truncate(buf.len().saturating_sub(2));
            Ok(Reply::Bulk(Some(buf)))
        }
        "*" => {
            let n: i64 = rest.parse().unwrap_or(-1);
            if n < 0 {
                return Ok(Reply::Array(None));
            }
            let mut items = Vec::new();
            for _ in 0..n {
                items.push(read_reply(s)?);
            }
            Ok(Reply::Array(Some(items)))
        }
        _ => Err(PyErr::other(
            "ConnectionError",
            format!("unexpected reply {line:?}"),
        )),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::testing::{FakeRedis, Root, CONFIG_DB, STATE_DB};

    fn err<T>(r: PyResult<T>) -> (String, String) {
        match r {
            Ok(_) => panic!("an error expected"),
            Err(e) => (e.exc.name().to_string(), e.str()),
        }
    }

    #[test]
    fn a_database_is_found_by_name_and_spoken_to_in_resp() {
        let root = Root::new();
        let redis = FakeRedis::get();
        redis.install(&root);
        redis.flush();
        let db = Db::connect("STATE_DB").unwrap();
        assert_eq!((db.name(), db.separator()), ("STATE_DB", "|"));
        let key = db.key("PSU_INFO", "PSU 1");
        assert_eq!(key, "PSU_INFO|PSU 1");
        db.hset(&key, &[("presence", "true"), ("model", "X")])
            .unwrap();
        db.hset(&db.key("PSU_INFO", "PSU 2"), &[("presence", "false")])
            .unwrap();
        assert_eq!(
            redis.hgetall(STATE_DB, &key),
            [
                ("presence".into(), "true".into()),
                ("model".into(), "X".into())
            ]
        );
        assert_eq!(db.hget(&key, "model").unwrap().as_deref(), Some("X"));
        assert_eq!(db.hget(&key, "nope").unwrap(), None);
        assert_eq!(db.hgetall(&key).unwrap(), redis.hgetall(STATE_DB, &key));
        assert_eq!(db.hgetall("absent").unwrap(), []);
        assert_eq!(
            db.keys("PSU_INFO|*").unwrap(),
            ["PSU_INFO|PSU 1", "PSU_INFO|PSU 2"]
        );
        let table = db.get_table("PSU_INFO").unwrap();
        assert_eq!(
            table[1],
            (
                "PSU 2".to_string(),
                vec![("presence".to_string(), "false".to_string())]
            )
        );
        db.hdel(&key, &["model"]).unwrap();
        assert_eq!(
            db.hgetall(&key).unwrap(),
            [("presence".to_string(), "true".to_string())]
        );
        assert!(db.exists(&key).unwrap());
        db.del(&key).unwrap();
        assert!(!db.exists(&key).unwrap());
        assert_eq!(db.cmd(&["GET", "missing"]).unwrap().into_string(), None);
        // A failing command is the ResponseError redis-py raises.
        assert_eq!(
            err(db.hget("BROKEN", "f")),
            ("ResponseError".into(), "ERR broken key".into())
        );
    }

    #[test]
    fn every_reply_kind_is_read_as_resp2_spells_it() {
        let root = Root::new();
        let redis = FakeRedis::get();
        redis.install(&root);
        let db = Db::connect("APPL_DB").unwrap();
        assert_eq!(db.separator(), ":");
        let raw = |r: &str| db.cmd(&["RAW", r]);
        assert_eq!(raw("+PONG\r\n").unwrap(), Reply::Status("PONG".into()));
        assert_eq!(
            raw("+PONG\r\n").unwrap().into_string().as_deref(),
            Some("PONG")
        );
        assert_eq!(raw(":-7\r\n").unwrap().into_string().as_deref(), Some("-7"));
        assert_eq!(raw("$-1\r\n").unwrap(), Reply::Bulk(None));
        assert_eq!(raw("*-1\r\n").unwrap(), Reply::Array(None));
        assert_eq!(raw("*-1\r\n").unwrap().into_string(), None);
        assert_eq!(
            raw("*2\r\n:1\r\n$2\r\nab\r\n").unwrap(),
            Reply::Array(Some(vec![Reply::Int(1), Reply::Bulk(Some(b"ab".to_vec()))]))
        );
        assert_eq!(
            err(raw("-WRONGTYPE no\r\n")),
            ("ResponseError".into(), "WRONGTYPE no".into())
        );
        assert_eq!(
            err(raw("?\r\n")),
            ("ConnectionError".into(), "unexpected reply \"?\"".into())
        );
        // The server hanging up.
        assert_eq!(
            err(db.cmd(&["CLOSE"])),
            (
                "ConnectionError".into(),
                "Connection closed by server.".into()
            )
        );
    }

    #[test]
    fn tcp_connections_reach_the_same_databases() {
        let root = Root::new();
        let redis = FakeRedis::get();
        redis.install(&root);
        redis.set(CONFIG_DB, "CONFIG_DB_INITIALIZED", "1");
        redis.hset(
            CONFIG_DB,
            "DEVICE_METADATA|localhost",
            &[("hwsku", "SKU-TCP")],
        );
        let db = Db::connect_tcp("CONFIG_DB").unwrap();
        assert_eq!(
            db.hget("DEVICE_METADATA|localhost", "hwsku")
                .unwrap()
                .as_deref(),
            Some("SKU-TCP")
        );
        let db = Db::connect_addr("127.0.0.1", redis.port(), CONFIG_DB).unwrap();
        assert_eq!(db.name(), format!("127.0.0.1:{}/4", redis.port()));
        assert_eq!(
            db.cmd(&["GET", "CONFIG_DB_INITIALIZED"]).unwrap(),
            Reply::Bulk(Some(b"1".to_vec()))
        );
    }

    /// It waits while the flag is missing or empty, and only then: the "0"
    /// the database container writes first already counts, as it does for
    /// swsscommon.
    #[test]
    fn config_db_answers_once_it_says_anything_about_being_initialised() {
        let root = Root::new();
        let redis = FakeRedis::get();
        redis.install(&root);
        redis.set(CONFIG_DB, "CONFIG_DB_INITIALIZED", "");
        let t = std::thread::spawn(|| {
            std::thread::sleep(Duration::from_millis(300));
            FakeRedis::get().set(CONFIG_DB, "CONFIG_DB_INITIALIZED", "0");
        });
        let db = Db::connect_config_db().unwrap();
        t.join().unwrap();
        assert_eq!(db.name(), "CONFIG_DB");
        assert_eq!(
            db.cmd(&["GET", "CONFIG_DB_INITIALIZED"]).unwrap(),
            Reply::Bulk(Some(b"0".to_vec()))
        );
    }

    /// A missing or malformed database config is an error, not a hang or a
    /// default.  These are this crate's errors: swsscommon raises its own
    /// (`RuntimeError`, `IndexError`) from `SonicDBConfig`, with C++ text.
    #[test]
    fn a_missing_or_malformed_config_is_an_error() {
        let root = Root::new();
        assert_eq!(err(Db::connect("STATE_DB")).0, "FileNotFoundError");
        let cfg = |instance: &str, db: &str| {
            root.write(
                DB_CONFIG_FILE,
                &format!(
                    r#"{{"INSTANCES": {{"redis": {instance}}}, "DATABASES": {{"STATE_DB": {db}}}}}"#
                ),
            )
        };
        cfg(
            r#"{"unix_socket_path": "/nowhere.sock", "hostname": "127.0.0.1", "port": "x"}"#,
            r#"{"id": "6", "instance": "redis"}"#,
        );
        assert_eq!(
            err(Db::connect("STATE_DB")),
            ("TypeError".into(), "database id is str".into())
        );
        assert_eq!(
            err(Db::connect("CONFIG_DB")),
            ("KeyError".into(), "'CONFIG_DB'".into())
        );
        cfg(
            r#"{"unix_socket_path": "/nowhere.sock", "hostname": "127.0.0.1", "port": "x"}"#,
            r#"{"id": 6, "instance": "redis"}"#,
        );
        assert_eq!(
            err(Db::connect_tcp("STATE_DB")),
            ("TypeError".into(), "port is str".into())
        );
        assert_eq!(err(Db::connect("STATE_DB")).0, "ConnectionError");
    }
}
