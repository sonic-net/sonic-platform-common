//! `sonic_platform_base.redfish_client`: the BMC's Redfish API through curl.
//!
//! Commands are built as strings, logged with secrets masked, split with
//! `shlex` and run; curl's stdout ends with an `HTTP Status Code:` line the
//! client parses off.  Responses are JSON of whatever shape the BMC sends,
//! so every test on them is Python's operator on a dynamic value
//! (`py::ops`): `'error' in response` on a string is a substring test, on a
//! number a `TypeError`, and which of those happens decides the next log line.
//!
//! The user and password callbacks are the BMC object's methods; they are
//! passed to each call that may log in, rather than held, since the BMC
//! object holds this client.

use std::sync::{Arc, Mutex};
use std::thread::sleep;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use regex::{NoExpand, Regex};

use crate::json;
use crate::logger::{self, Logger, ModuleLogger};
use crate::py::{ops, split_ws, splitlines, PyErr, PyResult, PyVal};
use crate::{shlex, subprocess};

pub const DEFAULT_TIMEOUT: i128 = 3;
pub const DEFAULT_LOGIN_TIMEOUT: i128 = 4;

pub const REDFISH_URI_FW_INVENTORY: &str = "/redfish/v1/UpdateService/FirmwareInventory";
pub const REDFISH_URI_CHASSIS_INVENTORY: &str = "/redfish/v1/Chassis";
pub const REDFISH_URI_TASKS: &str = "/redfish/v1/TaskService/Tasks";
pub const REDFISH_URI_UPDATE_SERVICE_UPDATE_MULTIPART: &str =
    "/redfish/v1/UpdateService/update-multipart";
pub const REDFISH_URI_UPDATE_SERVICE: &str = "/redfish/v1/UpdateService";
pub const REDFISH_URI_ACCOUNTS: &str = "/redfish/v1/AccountService/Accounts";
pub const REDFISH_URI_ACCOUNT_SERVICE: &str = "/redfish/v1/AccountService";
pub const REDFISH_URI_SESSION_SERVICE: &str = "/redfish/v1/SessionService/Sessions";
pub const REDFISH_BMC_LOG_DUMP: &str = "/redfish/v1/Managers/BMC_0/LogServices/Dump/Actions";
pub const REDFISH_REQUEST_SYSTEM_RESET: &str =
    "/redfish/v1/Systems/System_0/Actions/ComputerSystem.Reset";
pub const REDFISH_REQUEST_BMC_RESET: &str = "/redfish/v1/Managers/BMC_0/Actions/Manager.Reset";

pub const ERR_CODE_OK: i128 = 0;
pub const ERR_CODE_AUTH_FAILURE: i128 = -1;
pub const ERR_CODE_INVALID_JSON_FORMAT: i128 = -2;
pub const ERR_CODE_UNEXPECTED_RESPONSE: i128 = -3;
pub const ERR_CODE_CURL_FAILURE: i128 = -4;
pub const ERR_CODE_NOT_LOGIN: i128 = -5;
pub const ERR_CODE_TIMEOUT: i128 = -6;
pub const ERR_CODE_LOWER_VERSION: i128 = -7;
pub const ERR_CODE_PASSWORD_UNAVAILABLE: i128 = -8;
pub const ERR_CODE_URI_NOT_FOUND: i128 = -9;
pub const ERR_CODE_SERVER_UNREACHABLE: i128 = -10;
pub const ERR_CODE_UNSUPPORTED_PARAMETER: i128 = -11;
pub const ERR_CODE_GENERIC_ERROR: i128 = -12;
pub const ERR_CODE_IDENTICAL_VERSION: i128 = -13;

pub const READY_POLL_TIMEOUT: f64 = 300.0;
pub const READY_POLL_INTERVAL: f64 = 10.0;

const HTTP_STATUS_CODE_SUCCESS_EMPTY: &str = "204";

pub const REDFISH_BMC_GRACEFUL_RESTART: &str = "GracefulRestart";
pub const REDFISH_BMC_FORCE_RESTART: &str = "ForceRestart";

/// `CURL_TO_REDFISH_ERROR_MAP.get(rc, ERR_CODE_CURL_FAILURE)`.
fn curl_errors_to_redfish_errors(rc: i32) -> i128 {
    match rc {
        6 | 7 | 35 => ERR_CODE_SERVER_UNREACHABLE,
        28 => ERR_CODE_TIMEOUT,
        0 => ERR_CODE_OK,
        _ => ERR_CODE_CURL_FAILURE,
    }
}

/// The module's `logger = Logger('redfish_client')`.
pub static LOGGER: ModuleLogger = ModuleLogger::new();

/// `import sonic_platform_base.redfish_client`.
pub fn import() {
    logger::import("sonic_platform_base.redfish_client", || {
        let _ = LOGGER.set(Arc::new(Logger::new(Some("redfish_client"))));
    });
}

fn log() -> Arc<Logger> {
    import();
    LOGGER
        .get_or_init(|| Arc::new(Logger::new(Some("redfish_client"))))
        .clone()
}

fn notice(msg: &str) {
    log().log_notice(msg)
}

fn error(msg: &str) {
    log().log_error(msg)
}

/// `log_multi_line_str(msg)`.
pub fn log_multi_line_str(msg: Option<&str>) {
    if let Some(m) = msg {
        for line in splitlines(m) {
            notice(line);
        }
    }
}

/// `str()` of what may be None.
fn s(v: &Option<String>) -> String {
    v.clone().unwrap_or_else(|| "None".into())
}

/// `json.loads(x)` of a response that may be None.
fn loads(response: &Option<String>) -> PyResult<PyVal> {
    match response {
        Some(r) => json::loads(r),
        None => Err(PyErr::type_error(
            "the JSON object must be str, bytes or bytearray, not NoneType",
        )),
    }
}

fn is_json_error(e: &PyErr) -> bool {
    e.exc.name() == "JSONDecodeError"
}

fn re(p: &str) -> Regex {
    Regex::new(p).unwrap_or_else(|_| Regex::new("$^").unwrap_or_else(|_| unreachable!()))
}

/// `re.sub(pattern, replacement, text)` with a replacement of group refs.
fn sub(pattern: &str, replacement: &str, text: &str) -> String {
    re(pattern).replace_all(text, replacement).into_owned()
}

/// The user and password a login asks for: the BMC's callbacks.
pub trait Credentials {
    fn user(&self) -> PyResult<PyVal>;
    fn password(&self) -> PyResult<PyVal>;
}

/// What one curl run answers: `(ret, http_status_code, output_str, error_str)`.
#[derive(Clone, Debug)]
pub struct Exec {
    pub ret: i128,
    pub http: Option<String>,
    pub output: Option<String>,
    pub error: String,
}

/// `__wait_task_completion`'s result dict.
#[derive(Clone, Debug, Default)]
pub struct TaskResult {
    pub ret_code: i128,
    pub ret_msg: String,
    pub response: Option<String>,
    pub err_detected: bool,
    pub aborted: bool,
    pub identical_version: bool,
    pub lower_version: bool,
    pub updated_components: Option<Vec<PyVal>>,
}

#[derive(Default)]
struct Session {
    token: Option<String>,
    session_id: Option<String>,
}

pub struct RedfishClient {
    curl_path: String,
    svr_ip: String,
    session: Mutex<Session>,
}

/// `datetime.now().strftime("%H:%M:%S.%f")`.
fn now_hms_us() -> String {
    let d = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default();
    let t = d.as_secs() as libc::time_t;
    // SAFETY: localtime_r fills the tm we own.
    let mut tm: libc::tm = unsafe { std::mem::zeroed() };
    unsafe { libc::localtime_r(&t, &mut tm) };
    format!(
        "{:02}:{:02}:{:02}.{:06}",
        tm.tm_hour,
        tm.tm_min,
        tm.tm_sec,
        d.subsec_micros()
    )
}

fn time_now() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

fn sleep_secs(s: f64) {
    if s > 0.0 {
        sleep(Duration::from_secs_f64(s));
    }
}

impl RedfishClient {
    /// `RedfishClient(curl_path, ip_addr, user_callback, password_callback)`.
    pub fn new(curl_path: &str, ip_addr: &str) -> RedfishClient {
        let c = RedfishClient {
            curl_path: curl_path.to_string(),
            svr_ip: ip_addr.to_string(),
            session: Mutex::new(Session::default()),
        };
        notice(&format!(
            "RedfishClient instance (to {ip_addr}) is created\n"
        ));
        c
    }

    fn token(&self) -> Option<String> {
        self.session.lock().ok().and_then(|s| s.token.clone())
    }

    /// `get_login_token()`.
    pub fn get_login_token(&self) -> Option<String> {
        self.token()
    }

    /// `get_session_id()`.
    pub fn get_session_id(&self) -> Option<String> {
        self.session.lock().ok().and_then(|s| s.session_id.clone())
    }

    /// The token as an f-string shows it.
    fn tok(&self) -> String {
        s(&self.token())
    }

    fn build_login_cmd(&self, creds: &dyn Credentials, password: &PyVal) -> PyResult<String> {
        let user = creds.user()?;
        Ok(format!(
            "{} -m {DEFAULT_LOGIN_TIMEOUT} -k -D - -H \"Content-Type: application/json\" -X POST https://{}{REDFISH_URI_SESSION_SERVICE} -d '{{\"UserName\" : \"{}\", \"Password\" : \"{}\"}}'",
            self.curl_path,
            self.svr_ip,
            user.py_str(),
            password.py_str()
        ))
    }

    fn build_logout_cmd(&self, session_id: Option<&str>) -> String {
        let sid = match session_id {
            Some(s) if !s.is_empty() => s.to_string(),
            _ => s(&self.get_session_id()),
        };
        format!(
            "{} -k -H \"X-Auth-Token: {}\" -X DELETE https://{}{REDFISH_URI_SESSION_SERVICE}/{sid}",
            self.curl_path,
            self.tok(),
            self.svr_ip
        )
    }

    fn build_fw_update_multipart_cmd(
        &self,
        fw_image: &str,
        fw_ids: &[PyVal],
        force_update: bool,
    ) -> String {
        let targets_str = if fw_ids.is_empty() {
            String::new()
        } else {
            let targets: Vec<String> = fw_ids
                .iter()
                .map(|id| format!("\"{REDFISH_URI_FW_INVENTORY}/{}\"", id.py_str()))
                .collect();
            format!(", \"Targets\":[{}]", targets.join(", "))
        };
        let force = if force_update { "true" } else { "false" };
        format!(
            "{} -k -H \"X-Auth-Token: {}\" https://{}{REDFISH_URI_UPDATE_SERVICE_UPDATE_MULTIPART} --form 'UpdateParameters={{\"ForceUpdate\":{force}{targets_str}}};type=application/json' --form \"UpdateFile=@{fw_image};type=application/octet-stream\"",
            self.curl_path,
            self.tok(),
            self.svr_ip
        )
    }

    fn build_request_bmc_reset_cmd(&self, bmc_reset_type: &str) -> String {
        format!(
            "{} -k -H \"X-Auth-Token: {}\" -H \"Content-Type: application/json\" -X POST https://{}{REDFISH_REQUEST_BMC_RESET} -d '{{\"ResetType\": \"{bmc_reset_type}\"}}'",
            self.curl_path,
            self.tok(),
            self.svr_ip
        )
    }

    fn build_change_password_cmd(
        &self,
        creds: &dyn Credentials,
        new_password: &str,
        user: Option<&str>,
    ) -> PyResult<String> {
        let user = match user {
            Some(u) => u.to_string(),
            None => creds.user()?.py_str(),
        };
        Ok(format!(
            "{} -k -H \"X-Auth-Token: {}\" -H \"Content-Type: application/json\" -X PATCH https://{}{REDFISH_URI_ACCOUNTS}/{user} -d '{{\"Password\" : \"{new_password}\"}}'",
            self.curl_path,
            self.tok(),
            self.svr_ip
        ))
    }

    /// `json.dumps({"MinPasswordLength": min_length})`.
    fn build_set_min_password_length_cmd(&self, min_length: &PyVal) -> PyResult<String> {
        Ok(format!(
            "{} -k -H \"X-Auth-Token: {}\" -H \"Content-Type: application/json\" -X PATCH -d '{{\"MinPasswordLength\": {}}}' https://{}{REDFISH_URI_ACCOUNT_SERVICE}",
            self.curl_path,
            self.tok(),
            json_dumps(min_length)?,
            self.svr_ip
        ))
    }

    fn build_bmc_debug_log_dump_cmd(&self) -> String {
        format!(
            "{} -k -H \"X-Auth-Token: {}\" -H \"Content-Type: application/json\" -X POST https://{}{REDFISH_BMC_LOG_DUMP}/LogService.CollectDiagnosticData -d '{{\"DiagnosticDataType\":\"Manager\"}}'",
            self.curl_path,
            self.tok(),
            self.svr_ip
        )
    }

    fn build_get_cmd(&self, uri: &str, output_file: Option<&str>) -> String {
        let output_str = match output_file {
            Some(f) if !f.is_empty() => format!("--output {f}"),
            _ => String::new(),
        };
        format!(
            "{} -m {DEFAULT_TIMEOUT} -k -H \"X-Auth-Token: {}\" --request GET --location https://{}{uri} {output_str}",
            self.curl_path,
            self.tok(),
            self.svr_ip
        )
    }

    fn obfuscate_login_response(response: &str) -> String {
        let o = re(r"X-Auth-Token: [^\r\n]+")
            .replace_all(response, NoExpand("X-Auth-Token: ******"))
            .into_owned();
        let o = sub(
            r"(Location: [^\r\n]*SessionService/Sessions/)[^\r\n\s]+",
            "${1}******",
            &o,
        );
        let o = sub(
            r#"("@odata\.id": "[^"]*SessionService/Sessions/)[^"]*(")"#,
            "${1}******${2}",
            &o,
        );
        let o = sub(r#"("Id": ")[^"]*(")"#, "${1}******${2}", &o);
        let o = sub(r#"("UserName": ")[^"]*(")"#, "${1}******${2}", &o);
        re(r#""token": "[^"]*""#)
            .replace_all(&o, NoExpand(r#""token": "******""#))
            .into_owned()
    }

    fn obfuscate_logout_response(response: &str) -> String {
        let o = re(r"User '[^']+'")
            .replace_all(response, NoExpand("User '******'"))
            .into_owned();
        let o = sub(
            r#"("data": "User ')[^']+(' logged out")"#,
            "${1}******${2}",
            &o,
        );
        sub(
            r#"(SessionService/Sessions/)[^\s"}\r\n]+"#,
            "${1}******",
            &o,
        )
    }

    fn obfuscate_user_password(cmd: &str) -> String {
        let o = re(r#""UserName" : "[^"]*", "Password" : "[^"]*""#)
            .replace_all(
                cmd,
                NoExpand(r#""UserName" : "******", "Password" : "******""#),
            )
            .into_owned();
        re(r"-u [!-~]+:[!-~]+")
            .replace_all(&o, NoExpand("-u ******:******"))
            .into_owned()
    }

    fn obfuscate_auth_token(cmd: &str) -> String {
        re(r#"X-Auth-Token: [^"]+"#)
            .replace_all(cmd, NoExpand("X-Auth-Token: ******"))
            .into_owned()
    }

    fn obfuscate_password(cmd: &str) -> String {
        re(r#""Password" : "[^"]*""#)
            .replace_all(cmd, NoExpand(r#""Password" : "******""#))
            .into_owned()
    }

    fn obfuscate_username_in_url(cmd: &str) -> String {
        re(r"/AccountService/Accounts/[^/\s]+")
            .replace_all(cmd, NoExpand("/AccountService/Accounts/******"))
            .into_owned()
    }

    fn obfuscate_session_id_in_url(cmd: &str) -> String {
        re(r"/SessionService/Sessions/[^/\s]+")
            .replace_all(cmd, NoExpand("/SessionService/Sessions/******"))
            .into_owned()
    }

    /// `__parse_curl_output`: the body and the status code curl appended.
    fn parse_curl_output(curl_output: &str) -> (Option<String>, Option<String>) {
        match re(r"(?m)([\s\S]*?)(?:\n)?HTTP Status Code: (\d+)$").captures(curl_output) {
            Some(c) => (
                Some(c.get(1).map_or("", |m| m.as_str()).to_string()),
                Some(c.get(2).map_or("", |m| m.as_str()).to_string()),
            ),
            None => (None, None),
        }
    }

    /// `__get_headers_and_body_from_curl_output`: lower-cased header names,
    /// a later header replacing an earlier one in place.
    fn get_headers_and_body(curl_output: &str) -> (Vec<(String, String)>, String) {
        let mut headers: Vec<(String, String)> = Vec::new();
        let r = re(r"\r?\n\r?\n");
        let Some(m) = r.find(curl_output) else {
            return (headers, curl_output.to_string());
        };
        let (section, body) = (&curl_output[..m.start()], &curl_output[m.end()..]);
        for line in section.split('\n') {
            let line = crate::py::strip(line);
            if let Some((k, v)) = line.split_once(':') {
                let (k, v) = (
                    crate::py::strip(k).to_lowercase(),
                    crate::py::strip(v).to_string(),
                );
                match headers.iter_mut().find(|(k2, _)| *k2 == k) {
                    Some(e) => e.1 = v,
                    None => headers.push((k, v)),
                }
            }
        }
        (headers, body.to_string())
    }

    fn update_token_in_command(&self, cmd: &str) -> PyResult<String> {
        // `'X-Auth-Token: ' + self.__token`: None there is a TypeError.
        let token = self.token().ok_or_else(|| {
            PyErr::type_error("can only concatenate str (not \"NoneType\") to str")
        })?;
        Ok(re(r#"X-Auth-Token:\s*[^\s"']+"#)
            .replace_all(cmd, NoExpand(&format!("X-Auth-Token: {token}")))
            .into_owned())
    }

    /// `__exec_curl_cmd_internal(cmd)`.
    fn exec_internal(&self, cmd: &str) -> PyResult<Exec> {
        let task_mon = cmd.contains(REDFISH_URI_TASKS);
        let login_cmd = cmd.contains(REDFISH_URI_SESSION_SERVICE) && cmd.contains("POST");
        let logout_cmd = cmd.contains(REDFISH_URI_SESSION_SERVICE) && cmd.contains("DELETE");
        let password_change = cmd.contains(REDFISH_URI_ACCOUNTS) && cmd.contains("PATCH");
        let mut ob = Self::obfuscate_user_password(cmd);
        ob = Self::obfuscate_auth_token(&ob);
        if password_change {
            ob = Self::obfuscate_username_in_url(&ob);
            ob = Self::obfuscate_password(&ob);
        }
        if logout_cmd {
            ob = Self::obfuscate_session_id_in_url(&ob);
        }
        if !task_mon {
            notice(&format!("Execute cURL command: {ob}"));
        }
        let full = format!("{cmd} -w \"\nHTTP Status Code: %{{http_code}}\"");
        let argv = shlex::split(&full)?;
        let argv: Vec<&str> = argv.iter().map(String::as_str).collect();
        if argv.is_empty() {
            return Err(PyErr::index_error("list index out of range"));
        }
        let done = subprocess::communicate(&argv)?;
        let utf8 = crate::py::codec::Codec::Utf8;
        let (output_str, http) =
            Self::parse_curl_output(&crate::py::codec::decode(utf8, &done.stdout)?);
        let mut error_str = crate::py::codec::decode(utf8, &done.stderr)?;
        let ret;
        if done.returncode == 0 {
            // curl prints its transfer statistics on stderr.
            error_str = String::new();
            ret = ERR_CODE_OK;
            let shown = match &output_str {
                Some(o) if login_cmd => Some(Self::obfuscate_login_response(o)),
                Some(o) if logout_cmd => Some(Self::obfuscate_logout_response(o)),
                // re.sub() on the None that no status line leaves.
                None if login_cmd || logout_cmd => {
                    return Err(PyErr::type_error(
                        "expected string or bytes-like object, got 'NoneType'",
                    ))
                }
                other => other.clone(),
            };
            if http.is_none() {
                error("HTTP status code not found");
                notice("cURL output:");
                log_multi_line_str(shown.as_deref());
                return Ok(Exec {
                    ret: ERR_CODE_CURL_FAILURE,
                    http,
                    output: output_str,
                    error: "Unexpected curl output".into(),
                });
            }
            if !task_mon {
                notice(&format!("HTTP status code: {}", s(&http)));
                notice("cURL output:");
                log_multi_line_str(shown.as_deref());
            }
        } else {
            notice("cURL error:");
            log_multi_line_str(Some(&error_str));
            ret = curl_errors_to_redfish_errors(done.returncode);
        }
        Ok(Exec {
            ret,
            http,
            output: output_str,
            error: error_str,
        })
    }

    /// `exec_curl_cmd(cmd)`: retried with a longer `-m` on a timeout, and
    /// once more after logging in again on a 401.
    pub fn exec_curl_cmd(&self, creds: &dyn Credentials, cmd: &str) -> PyResult<Exec> {
        let max_retries = 2;
        let mut cmd = cmd.to_string();
        let is_login_cmd = cmd.contains(REDFISH_URI_SESSION_SERVICE) && cmd.contains("POST");
        if !self.has_login() && !is_login_cmd {
            error("Need to login first before executing cURL command");
            return Ok(Exec {
                ret: ERR_CODE_NOT_LOGIN,
                http: None,
                output: Some("Not login".into()),
                error: "Not login".into(),
            });
        }
        let mut r = self.exec_internal(&cmd)?;
        let mut i = 0;
        while i < max_retries && r.ret == ERR_CODE_TIMEOUT {
            if let Some(c) = re(r"-m\s*(\d+)").captures(&cmd) {
                let t: i128 = c.get(1).and_then(|m| m.as_str().parse().ok()).unwrap_or(0) + 2;
                cmd = re(r"-m\s*\d+")
                    .replace_all(&cmd, NoExpand(&format!("-m {t}")))
                    .into_owned();
            }
            r = self.exec_internal(&cmd)?;
            i += 1;
        }
        if r.http.as_deref() != Some("401") {
            return Ok(r);
        }
        if is_login_cmd {
            return Ok(Exec {
                ret: ERR_CODE_AUTH_FAILURE,
                http: r.http,
                output: Some("Authentication failure".into()),
                error: "Authentication failed".into(),
            });
        }
        notice("Re-login and retry last command...");
        self.invalidate_session();
        let ret = self.login(creds, true)?;
        if ret == ERR_CODE_OK {
            notice("Login successfully. Rerun last command\n");
            cmd = self.update_token_in_command(&cmd)?;
            let r = self.exec_internal(&cmd)?;
            if r.ret != ERR_CODE_OK {
                notice(&format!("Command rerun returns error {}\n", r.ret));
            } else if r.http.as_deref() == Some("401") {
                notice("Command rerun fails as authentication failure\n");
                self.invalidate_session();
            }
            Ok(Exec {
                ret: ERR_CODE_AUTH_FAILURE,
                http: r.http,
                output: Some("Authentication failure".into()),
                error: "Authentication failure".into(),
            })
        } else if ret == ERR_CODE_AUTH_FAILURE {
            notice("Failed to login. Return as authentication failure\n");
            self.invalidate_session();
            Ok(Exec {
                ret,
                http: r.http,
                output: Some("Authentication failure".into()),
                error: "Authentication failure".into(),
            })
        } else {
            notice(&format!("Failed to login, error : {ret}\n"));
            self.invalidate_session();
            Ok(Exec {
                ret,
                http: r.http,
                output: Some("Login failure".into()),
                error: "Login failure".into(),
            })
        }
    }

    /// `invalidate_session()`.
    pub fn invalidate_session(&self) {
        notice("Invalidate login token and session");
        if let Ok(mut s) = self.session.lock() {
            *s = Session::default();
        }
    }

    /// `open_session()`: `(ret, (msg, (session_id, token)))`.
    pub fn open_session(&self, creds: &dyn Credentials) -> PyResult<PyVal> {
        self.login(creds, true)?;
        if !self.has_login() {
            return Ok(PyVal::Tuple(vec![
                PyVal::Int(ERR_CODE_NOT_LOGIN),
                PyVal::Tuple(vec![PyVal::str("Failed to open session"), PyVal::None]),
            ]));
        }
        let sid = self.get_session_id().map_or(PyVal::None, PyVal::Str);
        let tok = self.token().map_or(PyVal::None, PyVal::Str);
        Ok(PyVal::Tuple(vec![
            PyVal::Int(ERR_CODE_OK),
            PyVal::Tuple(vec![
                PyVal::str("Login successful"),
                PyVal::Tuple(vec![sid, tok]),
            ]),
        ]))
    }

    /// `close_session(session_id)`: `(ret, msg)`.
    pub fn close_session(
        &self,
        creds: &dyn Credentials,
        session_id: &str,
    ) -> PyResult<(i128, String)> {
        let r = (|| -> PyResult<(i128, String)> {
            if !self.has_login() {
                return Ok((ERR_CODE_NOT_LOGIN, "Not logged in".into()));
            }
            let cmd = self.build_get_cmd(REDFISH_URI_SESSION_SERVICE, None);
            let e = self.exec_curl_cmd(creds, &cmd)?;
            if e.ret != ERR_CODE_OK {
                let msg = format!("Failed to get session list: {}", e.error);
                error(&msg);
                return Ok((e.ret, msg));
            }
            let json_response = loads(&e.output)?;
            let members = ops::get(&json_response, "Members", PyVal::List(vec![]))?;
            let mut session_exists = false;
            for member in ops::iterate(&members)? {
                let id = ops::get(&member, "@odata.id", PyVal::str(""))?;
                if ops::as_str(&id, "endswith")?.ends_with(&format!("/{session_id}")) {
                    session_exists = true;
                    break;
                }
            }
            if !session_exists {
                notice(&format!(
                    "Session {session_id} does not exist, no logout needed"
                ));
                return Ok((ERR_CODE_OK, "Session does not exist".into()));
            }
            let res = self.logout(creds, Some(session_id))?;
            if res != ERR_CODE_OK {
                let msg = format!("Failed to close session: {res}");
                error(&msg);
                return Ok((res, msg));
            }
            Ok((ERR_CODE_OK, "Session closed successfully".into()))
        })();
        r.or_else(|e| {
            if !is_exception(&e) {
                return Err(e);
            }
            let msg = format!("Failed to close session: {}", e.str());
            error(&msg);
            Ok((ERR_CODE_GENERIC_ERROR, msg))
        })
    }

    /// `has_login()`.
    pub fn has_login(&self) -> bool {
        self.session
            .lock()
            .map(|s| s.token.is_some() && s.session_id.is_some())
            .unwrap_or(false)
    }

    /// `login(log_errors=...)`.
    pub fn login(&self, creds: &dyn Credentials, log_errors: bool) -> PyResult<i128> {
        if self.has_login() {
            return Ok(ERR_CODE_OK);
        }
        let log_fn = |m: &str| if log_errors { error(m) } else { notice(m) };
        let password = match creds.password() {
            Ok(p) => p,
            Err(e) if is_exception(&e) => {
                log_fn(&e.str());
                return Ok(ERR_CODE_PASSWORD_UNAVAILABLE);
            }
            Err(e) => return Err(e),
        };
        let cmd = self.build_login_cmd(creds, &password)?;
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if e.ret != 0 {
            log_fn(&format!("Login failure: code {}, {}", e.ret, e.error));
            return Ok(e.ret);
        }
        let response = match &e.output {
            Some(r) if !r.is_empty() => r.clone(),
            _ => {
                log_fn("Got empty Redfish login response");
                return Ok(ERR_CODE_UNEXPECTED_RESPONSE);
            }
        };
        let (headers, body) = Self::get_headers_and_body(&response);
        if !body.is_empty() {
            let parsed = (|| -> PyResult<Option<i128>> {
                let json_response = json::loads(&body)?;
                if ops::has(&json_response, "error")? {
                    let msg = ops::item(&ops::item(&json_response, "error")?, "message")?;
                    log_fn(&format!("Login failure: {}", msg.py_str()));
                    log_multi_line_str(Some(&response));
                    return Ok(Some(ERR_CODE_GENERIC_ERROR));
                }
                Ok(None)
            })();
            match parsed {
                Ok(Some(code)) => return Ok(code),
                Ok(None) => {}
                Err(e) if is_exception(&e) => {
                    log_fn(&format!(
                        "Login failure: Exception during parsing body: {}",
                        e.str()
                    ));
                    log_multi_line_str(Some(&response));
                }
                Err(e) => return Err(e),
            }
        }
        let header = |k: &str| headers.iter().find(|(h, _)| h == k).map(|(_, v)| v.clone());
        let token = match header("x-auth-token") {
            Some(t) if !t.is_empty() => t,
            _ => {
                log_fn("Login failure: no \"X-Auth-Token\" header found");
                log_multi_line_str(Some(&response));
                return Ok(ERR_CODE_UNEXPECTED_RESPONSE);
            }
        };
        let location = match header("location") {
            Some(l) if !l.is_empty() => l,
            _ => {
                log_fn("Login failure: no \"Location\" header found");
                log_multi_line_str(Some(&response));
                return Ok(ERR_CODE_UNEXPECTED_RESPONSE);
            }
        };
        let session_id = location.rsplit('/').next().unwrap_or("").to_string();
        if session_id.is_empty() {
            log_fn("Login failure: could not extract session ID from Location header");
            log_multi_line_str(Some(&response));
            return Ok(ERR_CODE_UNEXPECTED_RESPONSE);
        }
        if let Ok(mut s) = self.session.lock() {
            s.token = Some(token);
            s.session_id = Some(session_id);
        }
        notice("Redfish login successfully with session token and session ID updated");
        Ok(ERR_CODE_OK)
    }

    /// `logout(session_id=None)`.
    pub fn logout(&self, creds: &dyn Credentials, session_id: Option<&str>) -> PyResult<i128> {
        let session_id = session_id.filter(|s| !s.is_empty());
        match session_id {
            Some(sid) => notice(&format!("Close the following session {sid}")),
            None => notice("Close the current session"),
        }
        if session_id.is_none() && !self.has_login() {
            return Ok(ERR_CODE_OK);
        }
        notice("Logout redfish session");
        let cmd = self.build_logout_cmd(session_id);
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if session_id.is_none() {
            self.invalidate_session();
        }
        if e.ret != 0 {
            notice("Logout failure: curl command returns error\n");
            return Ok(e.ret);
        }
        let response = match &e.output {
            Some(r) if !r.is_empty() => r.clone(),
            _ => {
                error("Logout failed: Empty response");
                return Ok(ERR_CODE_UNEXPECTED_RESPONSE);
            }
        };
        let r = (|| -> PyResult<i128> {
            let json_response = json::loads(&response)?;
            if ops::has(&json_response, "error")? {
                let msg = ops::item(&ops::item(&json_response, "error")?, "message")?;
                error(&format!("Logout failed: {}", msg.py_str()));
                log_multi_line_str(Some(&response));
                return Ok(ERR_CODE_GENERIC_ERROR);
            }
            if ops::has(&json_response, "@Message.ExtendedInfo")? {
                for info in ops::iterate(&ops::item(&json_response, "@Message.ExtendedInfo")?)? {
                    let message_id = ops::get(&info, "MessageId", PyVal::str(""))?;
                    if ops::contains(&message_id, &PyVal::str("Success"))? {
                        notice("Redfish logout successful");
                        return Ok(ERR_CODE_OK);
                    }
                }
                error("Logout failed: No success message in response");
                log_multi_line_str(Some(&response));
                return Ok(ERR_CODE_UNEXPECTED_RESPONSE);
            }
            error("Logout failed: No Message.ExtendedInfo in response");
            log_multi_line_str(Some(&response));
            Ok(ERR_CODE_UNEXPECTED_RESPONSE)
        })();
        r.or_else(|e| {
            if !is_exception(&e) {
                return Err(e);
            }
            error(&format!("Logout failed: exception {}", e.str()));
            log_multi_line_str(Some(&response));
            Ok(ERR_CODE_UNEXPECTED_RESPONSE)
        })
    }

    /// `wait_until_redfish_ready(timeout, interval)`.
    pub fn wait_until_redfish_ready(
        &self,
        creds: &dyn Credentials,
        timeout: f64,
        interval: f64,
    ) -> PyResult<i128> {
        self.invalidate_session();
        let deadline = time_now() + timeout;
        loop {
            let last_code = self.login(creds, false)?;
            if last_code == ERR_CODE_OK {
                self.logout(creds, None)?;
                notice("BMC Redfish service is ready");
                return Ok(ERR_CODE_OK);
            }
            if last_code == ERR_CODE_PASSWORD_UNAVAILABLE {
                return Ok(last_code);
            }
            let remaining = deadline - time_now();
            if remaining <= 0.0 {
                return Ok(last_code);
            }
            notice("Waiting for BMC Redfish service to become ready...");
            sleep_secs(interval.min(remaining));
        }
    }

    /// `__get_uri_from_response(response)`: `(ret, err_msg, uri)`.
    fn get_uri_from_response(
        response: &Option<String>,
    ) -> PyResult<(i128, String, Option<String>)> {
        let json_response = match loads(response) {
            Ok(v) => v,
            Err(e) if is_exception(&e) => {
                return Ok((
                    ERR_CODE_INVALID_JSON_FORMAT,
                    "Error: Invalid JSON format".into(),
                    None,
                ))
            }
            Err(e) => return Err(e),
        };
        if !ops::has(&json_response, "Payload")? {
            return Ok((
                ERR_CODE_UNEXPECTED_RESPONSE,
                "Error: Missing 'Payload' field".into(),
                None,
            ));
        }
        let payload = ops::item(&json_response, "Payload")?;
        if !ops::has(&payload, "HttpHeaders")? {
            return Ok((
                ERR_CODE_UNEXPECTED_RESPONSE,
                "Error: Missing 'HttpHeaders' field".into(),
                None,
            ));
        }
        let mut uri: Option<PyVal> = None;
        for header in ops::iterate(&ops::item(&payload, "HttpHeaders")?)? {
            if ops::has(&header, "Location")? {
                let parts = split_ws(ops::as_str(&header, "split")?);
                let last = parts
                    .last()
                    .ok_or_else(|| PyErr::index_error("list index out of range"))?;
                uri = Some(PyVal::str(*last));
            }
        }
        match uri {
            Some(PyVal::Str(u)) if !u.is_empty() => Ok((ERR_CODE_OK, String::new(), Some(u))),
            _ => Ok((
                ERR_CODE_UNEXPECTED_RESPONSE,
                "Error: Missing 'Location' field".into(),
                None,
            )),
        }
    }

    /// `__wait_task_completion(task_id, timeout, progress_callback=None)`,
    /// without the callback: nothing in the base class passes one.
    fn wait_task_completion(
        &self,
        creds: &dyn Credentials,
        task_id: &PyVal,
        timeout: f64,
    ) -> PyResult<TaskResult> {
        let sleep_timeout = 2.0;
        let uri = format!("{REDFISH_URI_TASKS}/{}", task_id.py_str());
        let cmd = self.build_get_cmd(&uri, None);
        let ob = Self::obfuscate_auth_token(&cmd);
        let mut prev_status = PyVal::None;
        let mut prev_percent = PyVal::None;
        let start_tm = time_now();
        let mut timeout_cnt = 0;
        loop {
            let mut result = TaskResult::default();
            let timestamp = now_hms_us();
            let e = self.exec_curl_cmd(creds, &cmd)?;
            result.response = e.output.clone();
            if e.ret == ERR_CODE_TIMEOUT && timeout_cnt < 10 {
                timeout_cnt += 1;
                notice(&format!(
                    "Timeout on checking task {} status, retry count {timeout_cnt}",
                    task_id.py_str()
                ));
                sleep_secs(sleep_timeout);
                continue;
            }
            timeout_cnt = 0;
            if e.ret != ERR_CODE_OK {
                result.ret_code = e.ret;
                result.ret_msg = format!("Error: {}", e.error);
                return Ok(result);
            }
            let json_response = match loads(&e.output) {
                Ok(v) => v,
                Err(err) if is_exception(&err) => {
                    result.ret_code = ERR_CODE_INVALID_JSON_FORMAT;
                    result.ret_msg = "Error: Invalid JSON format".into();
                    return Ok(result);
                }
                Err(err) => return Err(err),
            };
            for attr in ["PercentComplete", "TaskStatus", "Messages"] {
                if !ops::has(&json_response, attr)? {
                    result.ret_code = ERR_CODE_INVALID_JSON_FORMAT;
                    result.ret_msg =
                        format!("Error: Missing '{attr}' field in task status response");
                    return Ok(result);
                }
            }
            for msg in ops::iterate(&ops::item(&json_response, "Messages")?)? {
                self.dispatch_event(&msg, &mut result)?;
            }
            let status = ops::item(&json_response, "TaskStatus")?;
            let percent = ops::item(&json_response, "PercentComplete")?;
            let changed = !prev_status.py_eq(&status) || !prev_percent.py_eq(&percent);
            if changed {
                notice(&format!("Execute cURL command at {timestamp}: {ob}"));
                notice(&format!("HTTP status code: {}", s(&e.http)));
                notice("cURL output:");
                log_multi_line_str(e.output.as_deref());
                prev_status = status.clone();
                prev_percent = percent.clone();
            }
            if !status.py_eq(&PyVal::str("OK")) {
                result.ret_code = ERR_CODE_GENERIC_ERROR;
                if !result.err_detected {
                    if result.aborted {
                        result.ret_msg += "Error: The task has been aborted\n";
                    } else {
                        result.ret_msg = format!(
                            "Error: Fail to execute the task - Taskstatus={}",
                            status.py_str()
                        );
                    }
                }
                result.ret_msg = crate::py::strip(&result.ret_msg).to_string();
                return Ok(result);
            }
            if percent.is_none() {
                // Polled again at once: no sleep, no timeout check.
                continue;
            }
            if percent.py_eq(&PyVal::Int(100)) {
                return Ok(result);
            }
            if time_now() - start_tm > timeout {
                result.ret_code = ERR_CODE_TIMEOUT;
                result.ret_msg += "Error: Wait task completion timeout\n";
                notice(&format!(
                    "Task {} status polling timeout after {} seconds",
                    task_id.py_str(),
                    fmt_num(timeout)
                ));
                return Ok(result);
            }
            sleep_secs(sleep_timeout);
        }
    }

    /// `__validate_message_args(event_msg)`.
    fn validate_message_args(event_msg: &PyVal) -> PyResult<(bool, String)> {
        let msg_id = ops::item(event_msg, "MessageId")?;
        if !ops::has(event_msg, "MessageArgs")? {
            return Ok((
                false,
                format!("Error: Missing 'MessageArgs' field for {}", msg_id.py_str()),
            ));
        }
        if ops::len(&ops::item(event_msg, "MessageArgs")?)? < 2 {
            return Ok((
                false,
                format!(
                    "Error: 'MessageArgs' field for {} has less than 2 elements",
                    msg_id.py_str()
                ),
            ));
        }
        Ok((true, String::new()))
    }

    /// `__dispatch_event(event_msg, context)` and its handlers.
    fn dispatch_event(&self, event_msg: &PyVal, ctx: &mut TaskResult) -> PyResult<(i128, String)> {
        if !ops::has(event_msg, "MessageId")? {
            return Ok((
                ERR_CODE_INVALID_JSON_FORMAT,
                "Error: Missing 'MessageId' field".into(),
            ));
        }
        let msg_id = ops::item(event_msg, "MessageId")?;
        let event_name = ops::as_str(&msg_id, "split")?
            .rsplit('.')
            .next()
            .unwrap_or("")
            .to_string();
        match event_name.as_str() {
            "UpdateSuccessful" => {
                let (valid, err) = Self::validate_message_args(event_msg)?;
                if !valid {
                    return Ok((ERR_CODE_INVALID_JSON_FORMAT, err));
                }
                let comp_id = ops::getitem(&ops::item(event_msg, "MessageArgs")?, &PyVal::Int(0))?;
                ctx.updated_components
                    .get_or_insert_with(Vec::new)
                    .push(comp_id);
                Ok((ERR_CODE_OK, String::new()))
            }
            "ComponentUpdateSkipped" => {
                let (valid, err) = Self::validate_message_args(event_msg)?;
                if !valid {
                    return Ok((ERR_CODE_INVALID_JSON_FORMAT, err));
                }
                ctx.identical_version = true;
                Ok((ERR_CODE_OK, String::new()))
            }
            "ResourceErrorsDetected" => {
                let (valid, err) = Self::validate_message_args(event_msg)?;
                if !valid {
                    return Ok((ERR_CODE_INVALID_JSON_FORMAT, err));
                }
                let err_str = ops::getitem(&ops::item(event_msg, "MessageArgs")?, &PyVal::Int(1))?;
                let mut err_msg = format!("Error: {}", err_str.py_str());
                if ops::contains(&err_str, &PyVal::str("Component image is identical"))? {
                    ctx.identical_version = true;
                    return Ok((ERR_CODE_OK, String::new()));
                }
                if ops::contains(
                    &err_str,
                    &PyVal::str("lower than the firmware component comparison stamp"),
                )? {
                    ctx.lower_version = true;
                    err_msg = "Error: The target image has lower version\n".into();
                }
                // 'ret_msg' is always in the context, so the message is
                // appended -- with a newline -- unless already there.
                if !ctx.ret_msg.contains(&err_msg) {
                    ctx.ret_msg = format!("{}{err_msg}\n", ctx.ret_msg);
                }
                ctx.err_detected = true;
                Ok((ERR_CODE_OK, String::new()))
            }
            "TaskAborted" => {
                ctx.aborted = true;
                Ok((ERR_CODE_OK, String::new()))
            }
            _ => Ok((ERR_CODE_OK, String::new())),
        }
    }

    /// `redfish_api_get_firmware_list()`: `(ret, [(fw_id, version)])`.
    pub fn redfish_api_get_firmware_list(
        &self,
        creds: &dyn Credentials,
    ) -> PyResult<(i128, Vec<(PyVal, PyVal)>)> {
        let cmd = self.build_get_cmd(REDFISH_URI_FW_INVENTORY, None);
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if e.ret != ERR_CODE_OK {
            error(&format!("Fail to get firmware list: {}", e.error));
            return Ok((e.ret, vec![]));
        }
        let item_list = match loads(&e.output).and_then(|j| ops::item(&j, "Members")) {
            Ok(v) => v,
            Err(err) if is_json_error(&err) => return Ok((ERR_CODE_INVALID_JSON_FORMAT, vec![])),
            Err(err) if is_exception(&err) => return Ok((ERR_CODE_UNEXPECTED_RESPONSE, vec![])),
            Err(err) => return Err(err),
        };
        let mut fw_list = Vec::new();
        for item in ops::iterate(&item_list)? {
            let id = ops::item(&item, "@odata.id")?;
            let fw_id = ops::as_str(&id, "split")?
                .rsplit('/')
                .next()
                .unwrap_or("")
                .to_string();
            let (ret, mut version) = self.redfish_api_get_firmware_version(creds, &fw_id)?;
            if ret != ERR_CODE_OK {
                version = PyVal::str("N/A");
            }
            fw_list.push((PyVal::Str(fw_id), version));
        }
        Ok((ERR_CODE_OK, fw_list))
    }

    /// `redfish_api_get_firmware_version(fw_id)`: `(ret, version)`.
    pub fn redfish_api_get_firmware_version(
        &self,
        creds: &dyn Credentials,
        fw_id: &str,
    ) -> PyResult<(i128, PyVal)> {
        let mut version = PyVal::str("N/A");
        let uri = format!("{REDFISH_URI_FW_INVENTORY}/{fw_id}");
        let cmd = self.build_get_cmd(&uri, None);
        let e = self.exec_curl_cmd(creds, &cmd)?;
        let mut ret = e.ret;
        if ret == ERR_CODE_OK {
            let r = loads(&e.output).and_then(|j| {
                if ops::has(&j, "Version")? {
                    version = ops::item(&j, "Version")?;
                } else {
                    // sonic-net/sonic-platform-common#764, merged upstream and
                    // not yet in this tree's Python, which answers `(OK, 'N/A')`
                    // here with an ERROR: the reason
                    // `json_response.get('error', {}).get('code', '').rsplit('.', 1)[-1]`
                    // decides the code, and a body that is not a dict raises
                    // AttributeError, caught below.
                    let error = ops::get(&j, "error", PyVal::Dict(vec![]))?;
                    let code = ops::get(&error, "code", PyVal::str(""))?;
                    let reason = ops::as_str(&code, "rsplit")?
                        .rsplit('.')
                        .next()
                        .unwrap_or("");
                    ret = if matches!(reason, "ResourceNotFound" | "ResourceMissingAtURI") {
                        ERR_CODE_URI_NOT_FOUND
                    } else {
                        ERR_CODE_UNEXPECTED_RESPONSE
                    };
                    notice(&format!(
                        "Version not found in Redfish response on querying {fw_id} version"
                    ));
                }
                Ok(())
            });
            match r {
                Ok(()) => {}
                Err(err) if is_json_error(&err) => {
                    notice(&format!(
                        "Error: Invalid Redfish response JSON format on querying {fw_id} version"
                    ));
                    ret = ERR_CODE_INVALID_JSON_FORMAT;
                }
                Err(err) if is_exception(&err) => {
                    notice(&format!(
                        "Error: Exception {} caught on querying {fw_id} version",
                        err.str()
                    ));
                    ret = ERR_CODE_UNEXPECTED_RESPONSE;
                }
                Err(err) => return Err(err),
            }
        } else {
            error(&format!(
                "Got error {ret} on querying {fw_id} version: {}",
                e.error
            ));
        }
        Ok((ret, version))
    }

    /// `redfish_api_update_firmware(fw_image, fw_ids, force_update=True,
    /// timeout=1800, progress_callback=None)`: `(ret, error_msg,
    /// updated_components)`.  Without the callback: nothing in the base class
    /// passes one.
    pub fn redfish_api_update_firmware(
        &self,
        creds: &dyn Credentials,
        fw_image: &str,
        fw_ids: &[PyVal],
        force_update: bool,
        timeout: f64,
    ) -> PyResult<(i128, String, Vec<PyVal>)> {
        let cmd = self.build_fw_update_multipart_cmd(fw_image, fw_ids, force_update);
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if e.ret != ERR_CODE_OK {
            return Ok((e.ret, format!("Error: {}", e.error), vec![]));
        }
        let json_response = match loads(&e.output) {
            Ok(v) => v,
            Err(err) if is_exception(&err) => {
                return Ok((
                    ERR_CODE_INVALID_JSON_FORMAT,
                    "Error: Invalid JSON format".into(),
                    vec![],
                ))
            }
            Err(err) => return Err(err),
        };
        let mut task_id = PyVal::str("");
        if ops::has(&json_response, "error")? {
            let err = ops::item(&json_response, "error")?;
            let (ret, err_msg) = if ops::has(&err, "message")? {
                (ERR_CODE_GENERIC_ERROR, ops::item(&err, "message")?.py_str())
            } else {
                (
                    ERR_CODE_UNEXPECTED_RESPONSE,
                    "Missing 'message' field".to_string(),
                )
            };
            return Ok((ret, format!("Error: {err_msg}"), vec![]));
        } else if ops::has(&json_response, "TaskStatus")? {
            let status = ops::item(&json_response, "TaskStatus")?;
            if status.py_eq(&PyVal::str("OK")) {
                task_id = ops::item(&json_response, "Id")?;
            } else {
                return Ok((
                    ERR_CODE_GENERIC_ERROR,
                    format!("Error: Return status is {}", status.py_str()),
                    vec![],
                ));
            }
        }
        let mut result = self.wait_task_completion(creds, &task_id, timeout)?;
        if result.lower_version {
            result.ret_code = ERR_CODE_LOWER_VERSION;
        } else if result.identical_version && !result.err_detected {
            result.ret_code = ERR_CODE_IDENTICAL_VERSION;
            result.ret_msg = String::new();
        }
        Ok((
            result.ret_code,
            result.ret_msg,
            result.updated_components.unwrap_or_default(),
        ))
    }

    /// `redfish_api_trigger_bmc_debug_log_dump()`: `(ret, (task_id, err))`.
    pub fn redfish_api_trigger_bmc_debug_log_dump(
        &self,
        creds: &dyn Credentials,
    ) -> PyResult<(i128, (PyVal, PyVal))> {
        let task_id = PyVal::str("-1");
        let cmd = self.build_bmc_debug_log_dump_cmd();
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if e.ret != ERR_CODE_OK {
            return Ok((e.ret, (task_id, PyVal::Str(format!("Error: {}", e.error)))));
        }
        let json_response = match loads(&e.output) {
            Ok(v) => v,
            Err(err) if is_exception(&err) => {
                return Ok((
                    ERR_CODE_INVALID_JSON_FORMAT,
                    (task_id, PyVal::str("Error: Invalid JSON format")),
                ))
            }
            Err(err) => return Err(err),
        };
        if ops::has(&json_response, "error")? {
            let err = ops::item(&json_response, "error")?;
            let (ret, err_msg) = if ops::has(&err, "message")? {
                (ERR_CODE_GENERIC_ERROR, ops::item(&err, "message")?.py_str())
            } else {
                (
                    ERR_CODE_UNEXPECTED_RESPONSE,
                    "Missing 'message' field".to_string(),
                )
            };
            Ok((ret, (task_id, PyVal::Str(format!("Error: {err_msg}")))))
        } else if ops::has(&json_response, "TaskStatus")? {
            let status = ops::item(&json_response, "TaskStatus")?;
            if status.py_eq(&PyVal::str("OK")) {
                let id = ops::get(&json_response, "Id", PyVal::str(""))?;
                Ok((ERR_CODE_OK, (id, PyVal::None)))
            } else {
                Ok((
                    ERR_CODE_GENERIC_ERROR,
                    (
                        task_id,
                        PyVal::Str(format!("Error: Return status is {}", status.py_str())),
                    ),
                ))
            }
        } else {
            Ok((
                ERR_CODE_UNEXPECTED_RESPONSE,
                (
                    task_id,
                    PyVal::str("Error: Missing 'error' or 'TaskStatus' field in response"),
                ),
            ))
        }
    }

    /// `redfish_api_get_bmc_debug_log_dump(task_id, filename, file_path,
    /// timeout)`: `(ret, error_msg)`.
    pub fn redfish_api_get_bmc_debug_log_dump(
        &self,
        creds: &dyn Credentials,
        task_id: &str,
        filename: &str,
        file_path: &str,
        timeout: f64,
    ) -> PyResult<(i128, String)> {
        let result = self.wait_task_completion(creds, &PyVal::str(task_id), timeout)?;
        if result.ret_code != ERR_CODE_OK {
            return Ok((result.ret_code, result.ret_msg));
        }
        let (ret, error_msg, uri) = Self::get_uri_from_response(&result.response)?;
        if ret != ERR_CODE_OK {
            return Ok((ret, error_msg));
        }
        let Some(mut uri) = uri else {
            return Ok((ERR_CODE_GENERIC_ERROR, error_msg));
        };
        let output_file = format!("{file_path}/{filename}");
        uri += "/attachment";
        let cmd = self.build_get_cmd(&uri, Some(&output_file));
        let e = self.exec_curl_cmd(creds, &cmd)?;
        Ok((e.ret, e.error))
    }

    /// `redfish_api_get_eeprom_list()`: `(ret, [(name, info)])`.
    pub fn redfish_api_get_eeprom_list(
        &self,
        creds: &dyn Credentials,
    ) -> PyResult<(i128, Vec<(String, PyVal)>)> {
        let cmd = self.build_get_cmd(REDFISH_URI_CHASSIS_INVENTORY, None);
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if e.ret != ERR_CODE_OK {
            error(&format!("Fail to get eeprom list: {}", e.error));
            return Ok((e.ret, vec![]));
        }
        let item_list = match loads(&e.output).and_then(|j| ops::item(&j, "Members")) {
            Ok(v) => v,
            Err(err) if is_json_error(&err) => return Ok((ERR_CODE_INVALID_JSON_FORMAT, vec![])),
            Err(err) if is_exception(&err) => return Ok((ERR_CODE_UNEXPECTED_RESPONSE, vec![])),
            Err(err) => return Err(err),
        };
        let mut eeprom_list = Vec::new();
        for item in ops::iterate(&item_list)? {
            let url = ops::get(&item, "@odata.id", PyVal::None)?;
            if !url.truthy() {
                continue;
            }
            let name = ops::as_str(&url, "split")?
                .rsplit('/')
                .next()
                .unwrap_or("")
                .to_string();
            if !name.contains("eeprom") {
                continue;
            }
            let (_, values) = self.redfish_api_get_eeprom_info(creds, &name)?;
            eeprom_list.push((name, values));
        }
        Ok((ERR_CODE_OK, eeprom_list))
    }

    /// `redfish_api_get_eeprom_info(component_name)`: `(ret, info)`, every
    /// value `str()`ed but the status's three fields, which are taken as the
    /// BMC answered them -- a `null` `State` is `None`, as in Python.
    pub fn redfish_api_get_eeprom_info(
        &self,
        creds: &dyn Credentials,
        component_name: &str,
    ) -> PyResult<(i128, PyVal)> {
        let uri = format!("{REDFISH_URI_CHASSIS_INVENTORY}/{component_name}");
        let cmd = self.build_get_cmd(&uri, None);
        let e = self.exec_curl_cmd(creds, &cmd)?;
        let bad = || PyVal::Dict(vec![(PyVal::str("State"), PyVal::str("Fail"))]);
        if e.ret != ERR_CODE_OK {
            error(&format!(
                "Fail to get eeprom info for {component_name}: {}",
                e.error
            ));
            return Ok((e.ret, bad()));
        }
        let json_response = match loads(&e.output) {
            Ok(v) => v,
            Err(err) if is_json_error(&err) => return Ok((ERR_CODE_INVALID_JSON_FORMAT, bad())),
            Err(err) if is_exception(&err) => return Ok((ERR_CODE_UNEXPECTED_RESPONSE, bad())),
            Err(err) => return Err(err),
        };
        if ops::has(&json_response, "error")? {
            let err = ops::item(&json_response, "error")?;
            let not_found = ops::has(&err, "code")?
                && ops::contains(&ops::item(&err, "code")?, &PyVal::str("ResourceNotFound"))?;
            let ret = if not_found {
                ERR_CODE_URI_NOT_FOUND
            } else {
                ERR_CODE_GENERIC_ERROR
            };
            error(&format!(
                "Got redfish error response for {component_name} query"
            ));
            return Ok((ret, bad()));
        }
        let mut info: Vec<(PyVal, PyVal)> = Vec::new();
        let mut put = |k: String, v: PyVal| match info
            .iter_mut()
            .find(|(k2, _)| matches!(k2, PyVal::Str(x) if *x == k))
        {
            Some(slot) => slot.1 = v,
            None => info.push((PyVal::Str(k), v)),
        };
        for (key, value) in ops::items(&json_response)? {
            if value.py_str().contains("@odata") || key.py_str().contains("@odata") {
                continue;
            }
            if key.py_eq(&PyVal::str("Status")) {
                continue;
            }
            put(key.py_str(), PyVal::Str(value.py_str()));
        }
        let status = ops::get(&json_response, "Status", PyVal::Dict(vec![]))?;
        put(
            "State".into(),
            ops::get(&status, "State", PyVal::str("Ok"))?,
        );
        put(
            "Health".into(),
            ops::get(&status, "Health", PyVal::str("Ok"))?,
        );
        put(
            "HealthRollup".into(),
            ops::get(&status, "HealthRollup", PyVal::str("Ok"))?,
        );
        Ok((ERR_CODE_OK, PyVal::Dict(info)))
    }

    /// `redfish_api_change_login_password(new_password, user=None)`.
    pub fn redfish_api_change_login_password(
        &self,
        creds: &dyn Credentials,
        new_password: &str,
        user: Option<&str>,
    ) -> PyResult<(i128, PyVal)> {
        notice("Changing BMC password\n");
        let cmd = self.build_change_password_cmd(creds, new_password, user)?;
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if e.http.as_deref() == Some(HTTP_STATUS_CODE_SUCCESS_EMPTY) {
            notice(&format!(
                "Password changed successfully (HTTP {})",
                s(&e.http)
            ));
            return Ok((ERR_CODE_OK, PyVal::str("")));
        }
        if e.ret != ERR_CODE_OK {
            error(&format!("Fail to change login password: {}", e.error));
            return Ok((e.ret, PyVal::Str(format!("Error: {}", e.error))));
        }
        let r = (|| -> PyResult<(i128, PyVal)> {
            let j = loads(&e.output)?;
            if ops::has(&j, "error")? {
                let msg = ops::item(&ops::item(&j, "error")?, "message")?;
                error(&format!("Fail to change login password: {}", msg.py_str()));
                return Ok((ERR_CODE_GENERIC_ERROR, msg));
            }
            if ops::has(&j, "Password@Message.ExtendedInfo")? {
                for info in ops::iterate(&ops::item(&j, "Password@Message.ExtendedInfo")?)? {
                    let id = ops::item(&info, "MessageId")?;
                    if ops::as_str(&id, "endswith")?.ends_with("Error") {
                        let msg = ops::item(&info, "Message")?;
                        error(&format!("Fail to change login password: {}", msg.py_str()));
                        let resolution = ops::item(&info, "Resolution")?;
                        error(&format!("Resolution: {}", resolution.py_str()));
                        return Ok((ERR_CODE_GENERIC_ERROR, msg));
                    }
                }
            }
            if ops::has(&j, "@Message.ExtendedInfo")? {
                for info in ops::iterate(&ops::item(&j, "@Message.ExtendedInfo")?)? {
                    let id = ops::item(&info, "MessageId")?;
                    if ops::as_str(&id, "endswith")?.ends_with("Success") {
                        notice("Password changed successfully");
                        return Ok((ERR_CODE_OK, PyVal::str("")));
                    }
                }
            }
            let msg = "Error: Unexpected response format";
            error(&format!("Fail to change login password. {msg}"));
            Ok((ERR_CODE_UNEXPECTED_RESPONSE, PyVal::str(msg)))
        })();
        r.or_else(|err| {
            if is_json_error(&err) {
                Ok((
                    ERR_CODE_INVALID_JSON_FORMAT,
                    PyVal::str("Error: Invalid JSON format"),
                ))
            } else if is_exception(&err) {
                Ok((
                    ERR_CODE_UNEXPECTED_RESPONSE,
                    PyVal::str("Error: Unexpected response format"),
                ))
            } else {
                Err(err)
            }
        })
    }

    /// `redfish_api_set_min_password_length(min_length)`.
    pub fn redfish_api_set_min_password_length(
        &self,
        creds: &dyn Credentials,
        min_length: &PyVal,
    ) -> PyResult<(i128, PyVal)> {
        let ml = min_length.py_str();
        notice(&format!("Setting BMC minimum password length to {ml}"));
        let cmd = self.build_set_min_password_length_cmd(min_length)?;
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if e.http.as_deref() == Some(HTTP_STATUS_CODE_SUCCESS_EMPTY) {
            notice(&format!(
                "Minimum password length set to {ml} successfully (HTTP {})",
                s(&e.http)
            ));
            return Ok((ERR_CODE_OK, PyVal::str("")));
        }
        if e.ret != ERR_CODE_OK {
            error(&format!("Fail to set minimum password length: {}", e.error));
            return Ok((e.ret, PyVal::Str(format!("Error: {}", e.error))));
        }
        let r = (|| -> PyResult<(i128, PyVal)> {
            let j = loads(&e.output)?;
            if ops::has(&j, "error")? {
                let msg = ops::get(
                    &ops::item(&j, "error")?,
                    "message",
                    PyVal::str("Missing 'message' field"),
                )?;
                error(&format!(
                    "Fail to set minimum password length: {}",
                    msg.py_str()
                ));
                return Ok((ERR_CODE_GENERIC_ERROR, msg));
            }
            if ops::has(&j, "@Message.ExtendedInfo")? {
                for info in ops::iterate(&ops::item(&j, "@Message.ExtendedInfo")?)? {
                    let id = ops::get(&info, "MessageId", PyVal::str(""))?;
                    if ops::as_str(&id, "endswith")?.ends_with("Success") {
                        notice(&format!("Minimum password length set to {ml} successfully"));
                        return Ok((ERR_CODE_OK, PyVal::str("")));
                    }
                }
            }
            let msg = "Error: Unexpected response format";
            error(&format!("Fail to set minimum password length: {msg}"));
            Ok((ERR_CODE_UNEXPECTED_RESPONSE, PyVal::str(msg)))
        })();
        r.or_else(|err| {
            if is_json_error(&err) {
                Ok((
                    ERR_CODE_INVALID_JSON_FORMAT,
                    PyVal::str("Error: Invalid JSON format"),
                ))
            } else if is_exception(&err) {
                Ok((
                    ERR_CODE_UNEXPECTED_RESPONSE,
                    PyVal::Str(format!("Error: {}", err.str())),
                ))
            } else {
                Err(err)
            }
        })
    }

    /// `redfish_api_get_min_password_length()`: `(ret, length or message)`.
    pub fn redfish_api_get_min_password_length(
        &self,
        creds: &dyn Credentials,
    ) -> PyResult<(i128, PyVal)> {
        let cmd = self.build_get_cmd(REDFISH_URI_ACCOUNT_SERVICE, None);
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if e.ret != ERR_CODE_OK {
            error(&format!("Fail to get minimum password length: {}", e.error));
            return Ok((e.ret, PyVal::Str(format!("Error: {}", e.error))));
        }
        let r = (|| -> PyResult<(i128, PyVal)> {
            let j = loads(&e.output)?;
            if ops::has(&j, "error")? {
                let msg = ops::get(
                    &ops::item(&j, "error")?,
                    "message",
                    PyVal::str("Missing 'message' field"),
                )?;
                error(&format!(
                    "Fail to get minimum password length: {}",
                    msg.py_str()
                ));
                return Ok((ERR_CODE_GENERIC_ERROR, msg));
            }
            let min_length = ops::get(&j, "MinPasswordLength", PyVal::None)?;
            if min_length.is_none() {
                return Ok((
                    ERR_CODE_UNEXPECTED_RESPONSE,
                    PyVal::str("Error: MinPasswordLength not found in response"),
                ));
            }
            Ok((ERR_CODE_OK, min_length))
        })();
        r.or_else(|err| {
            if is_json_error(&err) {
                Ok((
                    ERR_CODE_INVALID_JSON_FORMAT,
                    PyVal::str("Error: Invalid JSON format"),
                ))
            } else if is_exception(&err) {
                Ok((
                    ERR_CODE_UNEXPECTED_RESPONSE,
                    PyVal::Str(format!("Error: {}", err.str())),
                ))
            } else {
                Err(err)
            }
        })
    }

    /// `redfish_api_request_bmc_reset(bmc_reset_type)`: `(ret, err_msg)`.
    pub fn redfish_api_request_bmc_reset(
        &self,
        creds: &dyn Credentials,
        bmc_reset_type: &str,
    ) -> PyResult<(i128, PyVal)> {
        let cmd = self.build_request_bmc_reset_cmd(bmc_reset_type);
        let e = self.exec_curl_cmd(creds, &cmd)?;
        if e.ret != ERR_CODE_OK {
            notice(&format!(
                "Reset BMC return not OK, ret {}, response {}, err msg {}",
                e.ret,
                s(&e.output),
                e.error
            ));
            return Ok((e.ret, PyVal::Str(e.error)));
        }
        let response = match &e.output {
            Some(r) if !r.is_empty() => r.clone(),
            _ => {
                notice(&format!(
                    "Reset BMC return OK, ret {}, err msg {}",
                    e.ret, e.error
                ));
                return Ok((ERR_CODE_OK, PyVal::str("")));
            }
        };
        notice(&format!(
            "After requesting BMC {bmc_reset_type}, got response {response} and error {}",
            e.error
        ));
        let j = match json::loads(&response) {
            Ok(v) => v,
            Err(err) if is_json_error(&err) => {
                return Ok((
                    ERR_CODE_INVALID_JSON_FORMAT,
                    PyVal::str("Error: Invalid JSON format"),
                ))
            }
            Err(err) if is_exception(&err) => {
                return Ok((
                    ERR_CODE_UNEXPECTED_RESPONSE,
                    PyVal::str("Error: unexpected response"),
                ))
            }
            Err(err) => return Err(err),
        };
        let mut ret = e.ret;
        let mut err_msg = PyVal::Str(e.error);
        if ops::has(&j, "error")? {
            let err = ops::item(&j, "error")?;
            if ops::has(&err, "message")? {
                err_msg = ops::item(&err, "message")?;
                ret = ERR_CODE_GENERIC_ERROR;
                let code = ops::get(&err, "code", PyVal::str(""))?;
                if ops::contains(&code, &PyVal::str("ActionParameterUnknown"))? {
                    ret = ERR_CODE_UNSUPPORTED_PARAMETER;
                }
            } else {
                ret = ERR_CODE_UNEXPECTED_RESPONSE;
                err_msg = PyVal::str("Missing 'message' field");
            }
        }
        Ok((ret, err_msg))
    }
}

/// `except Exception`: what it does not catch.
pub fn is_exception(e: &PyErr) -> bool {
    !matches!(
        e.exc.name(),
        "SystemExit" | "KeyboardInterrupt" | "GeneratorExit"
    )
}

/// `json.dumps(v)` for the scalar a min length is.  What JSON has no form
/// for -- bytes, a platform object -- is Python's `TypeError`.
fn json_dumps(v: &PyVal) -> PyResult<String> {
    Ok(match v {
        PyVal::None => "null".into(),
        PyVal::Bool(true) => "true".into(),
        PyVal::Bool(false) => "false".into(),
        PyVal::Int(i) => i.to_string(),
        PyVal::Float(f) if f.is_nan() => "NaN".into(),
        PyVal::Float(f) if f.is_infinite() => {
            if *f > 0.0 {
                "Infinity".into()
            } else {
                "-Infinity".into()
            }
        }
        PyVal::Float(f) => crate::py::float_repr(*f),
        PyVal::Str(s) => json_str(s),
        PyVal::List(v) | PyVal::Tuple(v) => {
            format!(
                "[{}]",
                v.iter()
                    .map(json_dumps)
                    .collect::<PyResult<Vec<_>>>()?
                    .join(", ")
            )
        }
        PyVal::Dict(d) => format!(
            "{{{}}}",
            d.iter()
                .map(|(k, v)| Ok(format!("{}: {}", json_key(k)?, json_dumps(v)?)))
                .collect::<PyResult<Vec<_>>>()?
                .join(", ")
        ),
        other => {
            return Err(PyErr::type_error(format!(
                "Object of type {} is not JSON serializable",
                other.type_name()
            )))
        }
    })
}

/// A dict key as `json.dumps` writes it: strings, and scalars as strings.
fn json_key(k: &PyVal) -> PyResult<String> {
    match k {
        PyVal::Str(s) => Ok(json_str(s)),
        PyVal::None | PyVal::Bool(_) | PyVal::Int(_) | PyVal::Float(_) => {
            Ok(json_str(&json_dumps(k)?))
        }
        other => Err(PyErr::type_error(format!(
            "keys must be str, int, float, bool or None, not {}",
            other.type_name()
        ))),
    }
}

/// `json.dumps(v)`, for the tests that script a BMC.
#[cfg(test)]
pub fn tests_json_dumps(v: &PyVal) -> String {
    json_dumps(v).expect("a script is JSON")
}

/// A JSON string as `json.dumps` writes it: ASCII only.
fn json_str(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            c if (c as u32) < 0x20 || (c as u32) > 0x7e => {
                let mut buf = [0u16; 2];
                for u in c.encode_utf16(&mut buf) {
                    out.push_str(&format!("\\u{u:04x}"));
                }
            }
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// `str()` of a number Python formats with `{}`: an int stays an int.
fn fmt_num(f: f64) -> String {
    if f.fract() == 0.0 && f.abs() < 1e16 {
        format!("{}", f as i64)
    } else {
        crate::py::float_repr(f)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn curl_output_and_headers_parse_as_python() {
        let (o, c) = RedfishClient::parse_curl_output("{\"a\": 1}\nHTTP Status Code: 200");
        assert_eq!(
            (o.as_deref(), c.as_deref()),
            (Some("{\"a\": 1}"), Some("200"))
        );
        let (o, c) = RedfishClient::parse_curl_output("\nHTTP Status Code: 000");
        assert_eq!((o.as_deref(), c.as_deref()), (Some(""), Some("000")));
        assert_eq!(RedfishClient::parse_curl_output("garbage").0, None);
        let (h, b) = RedfishClient::get_headers_and_body("HTTP/1.1 201 Created\r\nX-Auth-Token: t0k\r\nLocation: /redfish/v1/SessionService/Sessions/s1\r\n\r\n{\"x\": 1}");
        // The status line has no ':', so it is not a header.
        assert_eq!(h.len(), 2);
        assert_eq!(h[0], ("x-auth-token".to_string(), "t0k".to_string()));
        assert_eq!(b, "{\"x\": 1}");
    }

    #[test]
    fn secrets_are_masked_as_python_masks_them() {
        let c = r#"/usr/bin/curl -m 4 -k -D - -H "Content-Type: application/json" -X POST https://1.2.3.4/redfish/v1/SessionService/Sessions -d '{"UserName" : "u", "Password" : "p"}'"#;
        assert_eq!(
            RedfishClient::obfuscate_user_password(c),
            r#"/usr/bin/curl -m 4 -k -D - -H "Content-Type: application/json" -X POST https://1.2.3.4/redfish/v1/SessionService/Sessions -d '{"UserName" : "******", "Password" : "******"}'"#
        );
        assert_eq!(
            RedfishClient::obfuscate_auth_token(r#"-H "X-Auth-Token: abc" -X"#),
            r#"-H "X-Auth-Token: ******" -X"#
        );
        assert_eq!(
            RedfishClient::obfuscate_login_response("Location: /redfish/v1/SessionService/Sessions/abc\r\n{\"Id\": \"abc\", \"UserName\": \"u\"}"),
            "Location: /redfish/v1/SessionService/Sessions/******\r\n{\"Id\": \"******\", \"UserName\": \"******\"}"
        );
        assert_eq!(json_dumps(&PyVal::Int(12)).unwrap(), "12");
        assert_eq!(json_str("é\""), "\"\\u00e9\\\"\"");
    }

    struct Creds;

    impl Credentials for Creds {
        fn user(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("nosuser"))
        }
        fn password(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("pw"))
        }
    }

    const FW_X: &str = "/redfish/v1/UpdateService/FirmwareInventory/FW_X";

    fn version_of(c: &RedfishClient) -> (i128, String) {
        let (ret, version) = c.redfish_api_get_firmware_version(&Creds, "FW_X").unwrap();
        (ret, version.py_repr())
    }

    /// A reply without a `Version` is an error, which one by the Redfish
    /// reason in its body -- a BMC may answer a missing member with 400.
    #[test]
    fn a_firmware_member_without_a_version_is_an_error_named_by_its_reason() {
        let curl = crate::testing::FakeCurl::new();
        let c = RedfishClient::new(&curl.path(), "169.254.0.1");
        assert_eq!(c.login(&Creds, true).unwrap(), ERR_CODE_OK);
        let na = "'N/A'".to_string();
        let cases: &[(u16, &str, i128, &str)] = &[
            (
                200,
                r#"{"Id": "FW_X", "Version": "1.2"}"#,
                ERR_CODE_OK,
                "'1.2'",
            ),
            (200, r#"{"Version": null}"#, ERR_CODE_OK, "None"),
            (
                400,
                r#"{"error": {"code": "Base.1.18.ResourceMissingAtURI"}}"#,
                ERR_CODE_URI_NOT_FOUND,
                &na,
            ),
            (
                404,
                r#"{"error": {"code": "Base.1.8.ResourceNotFound"}}"#,
                ERR_CODE_URI_NOT_FOUND,
                &na,
            ),
            // The reason is the last dotted part, or the whole code.
            (
                400,
                r#"{"error": {"code": "ResourceNotFound"}}"#,
                ERR_CODE_URI_NOT_FOUND,
                &na,
            ),
            (
                400,
                r#"{"error": {"code": "Base.1.8.ResourceNotFoundX"}}"#,
                ERR_CODE_UNEXPECTED_RESPONSE,
                &na,
            ),
            (
                400,
                r#"{"error": {"code": "Base.1.8.GeneralError"}}"#,
                ERR_CODE_UNEXPECTED_RESPONSE,
                &na,
            ),
            (200, r#"{"Id": "FW_X"}"#, ERR_CODE_UNEXPECTED_RESPONSE, &na),
            (200, r#"{"error": {}}"#, ERR_CODE_UNEXPECTED_RESPONSE, &na),
            // `.get` on a str and `.rsplit` on an int raise, and are caught.
            (200, r#"{"error": "x"}"#, ERR_CODE_UNEXPECTED_RESPONSE, &na),
            (
                200,
                r#"{"error": {"code": 5}}"#,
                ERR_CODE_UNEXPECTED_RESPONSE,
                &na,
            ),
            (200, "[1, 2]", ERR_CODE_UNEXPECTED_RESPONSE, &na),
            (200, "{bad", ERR_CODE_INVALID_JSON_FORMAT, &na),
        ];
        for (status, body, ret, version) in cases {
            curl.reply("GET", FW_X, *status, body);
            assert_eq!(version_of(&c), (*ret, version.to_string()), "{body}");
        }
        // cURL failing is the error it maps to.
        curl.fail("GET", FW_X, 7, "curl: (7) Failed to connect");
        assert_eq!(
            version_of(&c),
            (curl_errors_to_redfish_errors(7), na.clone())
        );
        // Without a session nothing is asked.
        c.invalidate_session();
        curl.take_requests();
        assert_eq!(version_of(&c), (ERR_CODE_NOT_LOGIN, na));
        assert!(curl.take_requests().is_empty());
    }

    use crate::testing::{Answer, FakeCurl};

    const SESSIONS: &str = REDFISH_URI_SESSION_SERVICE;
    const LOGIN: &str = "POST /redfish/v1/SessionService/Sessions";
    const LOGOUT: &str = "DELETE /redfish/v1/SessionService/Sessions/s1";
    const X: &str = "/redfish/v1/X";
    const TASK9: &str = "/redfish/v1/TaskService/Tasks/9";

    /// A password callback that raises `class`.
    struct NoPassword(&'static str);

    impl Credentials for NoPassword {
        fn user(&self) -> PyResult<PyVal> {
            Ok(PyVal::str("nosuser"))
        }
        fn password(&self) -> PyResult<PyVal> {
            Err(PyErr::other(self.0, "no TPM"))
        }
    }

    fn client(curl: &FakeCurl) -> RedfishClient {
        RedfishClient::new(&curl.path(), "169.254.0.1")
    }

    fn logged_in(curl: &FakeCurl) -> RedfishClient {
        let c = client(curl);
        assert_eq!(c.login(&Creds, true).unwrap(), ERR_CODE_OK);
        curl.take_requests();
        curl.take_commands();
        c
    }

    fn get(path: &str) -> String {
        format!("GET {path}")
    }

    fn login_reply(headers: &str, body: &str) -> String {
        format!("HTTP/1.1 201 Created\r\n{headers}\r\n\r\n{body}")
    }

    fn ok_login() -> String {
        login_reply(
            &format!("X-Auth-Token: tok1\r\nLocation: {SESSIONS}/s1"),
            r#"{"Id": "s1"}"#,
        )
    }

    fn repr2(r: (i128, PyVal)) -> String {
        PyVal::Tuple(vec![PyVal::Int(r.0), r.1]).py_repr()
    }

    fn pairs(v: Vec<(PyVal, PyVal)>) -> String {
        PyVal::List(
            v.into_iter()
                .map(|(a, b)| PyVal::Tuple(vec![a, b]))
                .collect(),
        )
        .py_repr()
    }

    #[test]
    fn login_needs_a_password_a_token_and_a_session_id() {
        let curl = FakeCurl::new();
        let c = client(&curl);
        assert_eq!(
            c.login(&NoPassword("Exception"), true).unwrap(),
            ERR_CODE_PASSWORD_UNAVAILABLE
        );
        assert_eq!(
            c.login(&NoPassword("Exception"), false).unwrap(),
            ERR_CODE_PASSWORD_UNAVAILABLE
        );
        assert_eq!(
            c.login(&NoPassword("SystemExit"), true)
                .map_err(|e| e.exc.name()),
            Err("SystemExit")
        );
        assert!(curl.take_requests().is_empty());
        let cases: &[(u16, String, i128)] = &[
            (401, String::new(), ERR_CODE_AUTH_FAILURE),
            (201, String::new(), ERR_CODE_UNEXPECTED_RESPONSE),
            (
                400,
                r#"{"error": {"message": "Invalid username or password"}}"#.into(),
                ERR_CODE_GENERIC_ERROR,
            ),
            (
                201,
                login_reply(&format!("Location: {SESSIONS}/s1"), "{}"),
                ERR_CODE_UNEXPECTED_RESPONSE,
            ),
            (
                201,
                login_reply("X-Auth-Token: tok1", "{}"),
                ERR_CODE_UNEXPECTED_RESPONSE,
            ),
            (
                201,
                login_reply(&format!("X-Auth-Token: \r\nLocation: {SESSIONS}/s1"), ""),
                ERR_CODE_UNEXPECTED_RESPONSE,
            ),
            (
                201,
                login_reply(&format!("X-Auth-Token: tok1\r\nLocation: {SESSIONS}/"), ""),
                ERR_CODE_UNEXPECTED_RESPONSE,
            ),
        ];
        for (log_errors, (status, out, ret)) in [true, false].into_iter().cycle().zip(cases) {
            curl.reply_raw("POST", SESSIONS, *status, out);
            assert_eq!(c.login(&Creds, log_errors).unwrap(), *ret, "{out}");
            assert!(!c.has_login());
        }
        curl.fail("POST", SESSIONS, 7, "curl: (7) Failed to connect");
        assert_eq!(c.login(&Creds, true).unwrap(), ERR_CODE_SERVER_UNREACHABLE);
        // No status line: Python's re.sub() on the None that leaves.
        curl.reply_without_status("POST", SESSIONS, "garbage");
        assert_eq!(
            c.login(&Creds, true).map_err(|e| e.exc.name()),
            Err("TypeError")
        );
        // A body that is no help is logged; the headers still log in.
        for body in ["{bad", r#"{"error": {}}"#, r#""text""#, "5"] {
            let headers = format!("X-Auth-Token: tok2\r\nLocation: {SESSIONS}/s2");
            curl.reply_raw("POST", SESSIONS, 201, &login_reply(&headers, body));
            c.invalidate_session();
            assert_eq!(c.login(&Creds, true).unwrap(), ERR_CODE_OK, "{body}");
            assert_eq!(
                (c.get_login_token(), c.get_session_id()),
                (Some("tok2".into()), Some("s2".into()))
            );
        }
        curl.take_requests();
        assert_eq!(c.login(&Creds, true).unwrap(), ERR_CODE_OK);
        assert!(curl.take_requests().is_empty());
    }

    #[test]
    fn logout_reads_the_bmc_s_answer() {
        let curl = FakeCurl::new();
        let c = client(&curl);
        assert_eq!(c.logout(&Creds, None).unwrap(), ERR_CODE_OK);
        assert_eq!(c.logout(&Creds, Some("")).unwrap(), ERR_CODE_OK);
        assert!(curl.take_requests().is_empty());
        assert_eq!(c.logout(&Creds, Some("s9")).unwrap(), ERR_CODE_NOT_LOGIN);
        let c = logged_in(&curl);
        assert_eq!(c.logout(&Creds, None).unwrap(), ERR_CODE_OK);
        assert_eq!(curl.take_requests(), [LOGOUT]);
        assert!(!c.has_login());
        let s1 = format!("{SESSIONS}/s1");
        let cases: &[(&str, i128)] = &[
            (
                r#"{"error": {"message": "no such session"}}"#,
                ERR_CODE_GENERIC_ERROR,
            ),
            (
                r#"{"@Message.ExtendedInfo": [{"MessageId": "Base.1.15.Failure"}, {}]}"#,
                ERR_CODE_UNEXPECTED_RESPONSE,
            ),
            (
                r#"{"data": "User 'x' logged out"}"#,
                ERR_CODE_UNEXPECTED_RESPONSE,
            ),
            ("{bad", ERR_CODE_UNEXPECTED_RESPONSE),
            ("", ERR_CODE_UNEXPECTED_RESPONSE),
        ];
        for (body, ret) in cases {
            curl.reply("DELETE", &s1, 200, body);
            let c = logged_in(&curl);
            assert_eq!(c.logout(&Creds, None).unwrap(), *ret, "{body}");
            assert!(!c.has_login());
        }
        // Another session's: this one stays.
        let c = logged_in(&curl);
        assert_eq!(
            c.logout(&Creds, Some("s9")).unwrap(),
            ERR_CODE_GENERIC_ERROR
        );
        assert_eq!(curl.take_requests(), [format!("DELETE {SESSIONS}/s9")]);
        assert!(c.has_login());
        curl.fail("DELETE", &s1, 7, "");
        assert_eq!(c.logout(&Creds, None).unwrap(), ERR_CODE_SERVER_UNREACHABLE);
        assert!(!c.has_login());
    }

    #[test]
    fn a_timeout_is_retried_twice_with_longer_timeouts() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let cmd = c.build_get_cmd(X, None);
        curl.fail("GET", X, 28, "curl: (28) Operation timed out");
        let e = c.exec_curl_cmd(&Creds, &cmd).unwrap();
        assert_eq!(
            (e.ret, e.error.as_str()),
            (ERR_CODE_TIMEOUT, "curl: (28) Operation timed out")
        );
        let timeouts: Vec<String> = curl
            .take_commands()
            .iter()
            .map(|c| {
                c.split(' ')
                    .skip_while(|w| *w != "-m")
                    .nth(1)
                    .unwrap_or("")
                    .to_string()
            })
            .collect();
        assert_eq!(timeouts, ["3", "5", "7"]);
        curl.take_requests();
        curl.answers("GET", X, &[Answer::Fail(28, ""), Answer::Reply(200, "{}")]);
        let e = c.exec_curl_cmd(&Creds, &cmd).unwrap();
        assert_eq!(
            (e.ret, e.http.as_deref(), e.output.as_deref()),
            (ERR_CODE_OK, Some("200"), Some("{}"))
        );
        assert_eq!(curl.take_requests(), [get(X), get(X)]);
        // Output without the status line -w adds.
        curl.reply_without_status("GET", X, "garbage");
        let e = c.exec_curl_cmd(&Creds, &cmd).unwrap();
        assert_eq!(
            (e.ret, e.error.as_str()),
            (ERR_CODE_CURL_FAILURE, "Unexpected curl output")
        );
        for (rc, ret) in [
            (6, ERR_CODE_SERVER_UNREACHABLE),
            (35, ERR_CODE_SERVER_UNREACHABLE),
            (52, ERR_CODE_CURL_FAILURE),
        ] {
            curl.fail("GET", X, rc, "");
            assert_eq!(c.exec_curl_cmd(&Creds, &cmd).unwrap().ret, ret);
        }
        assert_eq!(curl_errors_to_redfish_errors(0), ERR_CODE_OK);
    }

    #[test]
    fn a_401_logs_in_again_and_retries_once() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let cmd = c.build_get_cmd(X, None);
        // The retry's answer is not passed on: the call is an authentication
        // failure, as in Python.
        curl.answers(
            "GET",
            X,
            &[Answer::Reply(401, ""), Answer::Reply(200, "{}")],
        );
        let e = c.exec_curl_cmd(&Creds, &cmd).unwrap();
        assert_eq!(
            (e.ret, e.http.as_deref(), e.output.as_deref()),
            (
                ERR_CODE_AUTH_FAILURE,
                Some("200"),
                Some("Authentication failure")
            )
        );
        assert_eq!(curl.take_requests(), [get(X), LOGIN.into(), get(X)]);
        assert!(c.has_login());
        // 401 again: the new session is dropped.
        curl.reply("GET", X, 401, "");
        assert_eq!(
            c.exec_curl_cmd(&Creds, &cmd).unwrap().ret,
            ERR_CODE_AUTH_FAILURE
        );
        assert!(!c.has_login());
        let c = logged_in(&curl);
        curl.answers("GET", X, &[Answer::Reply(401, ""), Answer::Fail(7, "")]);
        assert_eq!(
            c.exec_curl_cmd(&Creds, &cmd).unwrap().ret,
            ERR_CODE_AUTH_FAILURE
        );
        // Logging in again is refused, or fails.
        let ok = ok_login();
        for (relogin, ret, out) in [
            (
                Answer::Reply(401, ""),
                ERR_CODE_AUTH_FAILURE,
                "Authentication failure",
            ),
            (
                Answer::Fail(7, ""),
                ERR_CODE_SERVER_UNREACHABLE,
                "Login failure",
            ),
        ] {
            curl.answers("POST", SESSIONS, &[Answer::Reply(201, &ok), relogin]);
            let c = logged_in(&curl);
            curl.reply("GET", X, 401, "");
            let e = c.exec_curl_cmd(&Creds, &cmd).unwrap();
            assert_eq!((e.ret, e.output.as_deref()), (ret, Some(out)));
            assert!(!c.has_login());
        }
        // A login refused is not retried.
        curl.reply("POST", SESSIONS, 401, "");
        let c = client(&curl);
        let login = c.build_login_cmd(&Creds, &PyVal::str("pw")).unwrap();
        curl.take_requests();
        let e = c.exec_curl_cmd(&Creds, &login).unwrap();
        assert_eq!(
            (e.ret, e.error.as_str()),
            (ERR_CODE_AUTH_FAILURE, "Authentication failed")
        );
        assert_eq!(curl.take_requests(), [LOGIN]);
    }

    #[test]
    fn waiting_for_redfish_is_logging_in_until_it_works() {
        let curl = FakeCurl::new();
        let c = client(&curl);
        assert_eq!(
            c.wait_until_redfish_ready(&Creds, 1.0, 0.1).unwrap(),
            ERR_CODE_OK
        );
        assert_eq!(curl.take_requests(), [LOGIN, LOGOUT]);
        assert_eq!(
            c.wait_until_redfish_ready(&NoPassword("Exception"), 1.0, 0.1)
                .unwrap(),
            ERR_CODE_PASSWORD_UNAVAILABLE
        );
        curl.reply("POST", SESSIONS, 401, "");
        assert_eq!(
            c.wait_until_redfish_ready(&Creds, 0.25, 0.1).unwrap(),
            ERR_CODE_AUTH_FAILURE
        );
        assert!(curl.take_requests().len() >= 2);
    }

    #[test]
    fn sessions_open_and_close() {
        let curl = FakeCurl::default();
        let c = client(&curl);
        assert_eq!(
            c.open_session(&Creds).unwrap().py_repr(),
            "(0, ('Login successful', ('s1', 'tok1')))"
        );
        assert_eq!(
            client(&curl).close_session(&Creds, "s1").unwrap(),
            (ERR_CODE_NOT_LOGIN, "Not logged in".into())
        );
        let s2 = format!("{SESSIONS}/s2");
        curl.reply(
            "GET",
            SESSIONS,
            200,
            r#"{"Members": [{"@odata.id": "/redfish/v1/SessionService/Sessions/s2"}, {}]}"#,
        );
        assert_eq!(
            c.close_session(&Creds, "s3").unwrap(),
            (ERR_CODE_OK, "Session does not exist".into())
        );
        curl.reply(
            "DELETE",
            &s2,
            200,
            r#"{"@Message.ExtendedInfo": [{"MessageId": "Base.1.15.Success"}]}"#,
        );
        curl.take_requests();
        assert_eq!(
            c.close_session(&Creds, "s2").unwrap(),
            (ERR_CODE_OK, "Session closed successfully".into())
        );
        assert_eq!(
            curl.take_requests(),
            [get(SESSIONS), format!("DELETE {s2}")]
        );
        assert!(c.has_login());
        curl.forget("DELETE", &s2);
        assert_eq!(
            c.close_session(&Creds, "s2").unwrap(),
            (
                ERR_CODE_GENERIC_ERROR,
                "Failed to close session: -12".into()
            )
        );
        curl.reply("GET", SESSIONS, 200, "{bad");
        let (ret, msg) = c.close_session(&Creds, "s2").unwrap();
        assert_eq!(ret, ERR_CODE_GENERIC_ERROR);
        assert!(
            msg.starts_with("Failed to close session: Expecting"),
            "{msg}"
        );
        curl.fail("GET", SESSIONS, 7, "no route");
        assert_eq!(
            c.close_session(&Creds, "s2").unwrap(),
            (
                ERR_CODE_SERVER_UNREACHABLE,
                "Failed to get session list: no route".into()
            )
        );
        curl.reply("POST", SESSIONS, 401, "");
        assert_eq!(
            client(&curl).open_session(&Creds).unwrap().py_repr(),
            "(-5, ('Failed to open session', None))"
        );
    }

    #[test]
    fn the_firmware_list_is_each_member_s_version() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let inv = REDFISH_URI_FW_INVENTORY;
        curl.reply(
            "GET",
            inv,
            200,
            r#"{"Members": [{"@odata.id": "/x/FW_A"}, {"@odata.id": "/x/FW_B"}]}"#,
        );
        curl.reply("GET", &format!("{inv}/FW_A"), 200, r#"{"Version": "1.0"}"#);
        let (ret, list) = c.redfish_api_get_firmware_list(&Creds).unwrap();
        assert_eq!(
            (ret, pairs(list)),
            (ERR_CODE_OK, "[('FW_A', '1.0'), ('FW_B', 'N/A')]".into())
        );
        for (body, ret) in [
            ("{bad", ERR_CODE_INVALID_JSON_FORMAT),
            ("{}", ERR_CODE_UNEXPECTED_RESPONSE),
        ] {
            curl.reply("GET", inv, 200, body);
            let (r, list) = c.redfish_api_get_firmware_list(&Creds).unwrap();
            assert_eq!((r, list.len()), (ret, 0), "{body}");
        }
        curl.reply("GET", inv, 200, r#"{"Members": [{}]}"#);
        assert_eq!(
            c.redfish_api_get_firmware_list(&Creds)
                .map_err(|e| e.exc.name())
                .err(),
            Some("KeyError")
        );
        curl.fail("GET", inv, 7, "");
        assert_eq!(
            c.redfish_api_get_firmware_list(&Creds).unwrap().0,
            ERR_CODE_SERVER_UNREACHABLE
        );
    }

    #[test]
    fn eeproms_are_the_chassis_members_named_eeprom() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let ch = REDFISH_URI_CHASSIS_INVENTORY;
        let bmc = format!("{ch}/BMC_eeprom");
        curl.reply(
            "GET",
            ch,
            200,
            r#"{"Members": [{"@odata.id": "/redfish/v1/Chassis/BMC_eeprom"}, {"@odata.id": "/redfish/v1/Chassis/Card1"}, {}, {"@odata.id": "/redfish/v1/Chassis/FRU_eeprom"}]}"#,
        );
        curl.reply(
            "GET",
            &bmc,
            200,
            r#"{"@odata.id": "/redfish/v1/Chassis/BMC_eeprom", "Id": "BMC_eeprom", "Model": "P4501", "PartNumber": 69, "Links": {"ManagedBy": [{"@odata.id": "/x"}]}, "Oem": {"Nvidia": {"x": 1}}, "Status": {"State": "Enabled", "Health": "OK"}}"#,
        );
        let (ret, list) = c.redfish_api_get_eeprom_list(&Creds).unwrap();
        assert_eq!(ret, ERR_CODE_OK);
        assert_eq!(
            pairs(list.into_iter().map(|(k, v)| (PyVal::Str(k), v)).collect()),
            r#"[('BMC_eeprom', {'Id': 'BMC_eeprom', 'Model': 'P4501', 'PartNumber': '69', 'Oem': "{'Nvidia': {'x': 1}}", 'State': 'Enabled', 'Health': 'OK', 'HealthRollup': 'Ok'}), ('FRU_eeprom', {'State': 'Fail'})]"#
        );
        let info = |body: &str| {
            curl.reply("GET", &bmc, 200, body);
            repr2(c.redfish_api_get_eeprom_info(&Creds, "BMC_eeprom").unwrap())
        };
        assert_eq!(
            info(r#"{"Model": "M"}"#),
            "(0, {'Model': 'M', 'State': 'Ok', 'Health': 'Ok', 'HealthRollup': 'Ok'})"
        );
        assert_eq!(
            info(r#"{"error": {"code": "Base.1.8.ResourceNotFound"}}"#),
            "(-9, {'State': 'Fail'})"
        );
        assert_eq!(
            info(r#"{"error": {"code": "Base.1.8.GeneralError"}}"#),
            "(-12, {'State': 'Fail'})"
        );
        assert_eq!(info(r#"{"error": {}}"#), "(-12, {'State': 'Fail'})");
        assert_eq!(info("{bad"), "(-2, {'State': 'Fail'})");
        curl.reply("GET", &bmc, 200, "[1]");
        assert_eq!(
            c.redfish_api_get_eeprom_info(&Creds, "BMC_eeprom")
                .map_err(|e| e.exc.name())
                .err(),
            Some("AttributeError")
        );
        curl.fail("GET", &bmc, 7, "");
        assert_eq!(
            repr2(c.redfish_api_get_eeprom_info(&Creds, "BMC_eeprom").unwrap()),
            "(-10, {'State': 'Fail'})"
        );
        for (body, ret) in [
            ("{bad", ERR_CODE_INVALID_JSON_FORMAT),
            ("{}", ERR_CODE_UNEXPECTED_RESPONSE),
        ] {
            curl.reply("GET", ch, 200, body);
            assert_eq!(
                c.redfish_api_get_eeprom_list(&Creds).unwrap().0,
                ret,
                "{body}"
            );
        }
        curl.fail("GET", ch, 7, "");
        assert_eq!(
            c.redfish_api_get_eeprom_list(&Creds).unwrap().0,
            ERR_CODE_SERVER_UNREACHABLE
        );
    }

    fn task(percent: &str, status: &str, messages: &str) -> String {
        format!(
            r#"{{"PercentComplete": {percent}, "TaskStatus": "{status}", "Messages": [{messages}]}}"#
        )
    }

    fn event(id: &str, args: &str) -> String {
        format!(r#"{{"MessageId": "{id}", "MessageArgs": [{args}]}}"#)
    }

    fn update(c: &RedfishClient, timeout: f64) -> String {
        let (ret, msg, updated) = c
            .redfish_api_update_firmware(
                &Creds,
                "/tmp/bmc.fwpkg",
                &[PyVal::str("MGX_FW_BMC_0")],
                true,
                timeout,
            )
            .unwrap();
        PyVal::Tuple(vec![PyVal::Int(ret), PyVal::Str(msg), PyVal::List(updated)]).py_repr()
    }

    #[test]
    fn a_firmware_update_follows_its_task_to_the_end() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let mp = REDFISH_URI_UPDATE_SERVICE_UPDATE_MULTIPART;
        curl.reply(
            "POST",
            mp,
            202,
            r#"{"TaskStatus": "OK", "Id": "9", "TaskState": "Running"}"#,
        );
        // A percentage not known yet is asked for again at once.
        let first = task(
            "null",
            "OK",
            &event("Update.1.0.TargetDetermined", r#""a", "b""#),
        );
        let last = task(
            "100",
            "OK",
            &event(
                "ResourceEvent.1.0.UpdateSuccessful",
                r#""MGX_FW_BMC_0", "x""#,
            ),
        );
        curl.answers(
            "GET",
            TASK9,
            &[Answer::Reply(200, &first), Answer::Reply(200, &last)],
        );
        assert_eq!(update(&c, 60.0), "(0, '', ['MGX_FW_BMC_0'])");
        let cmds = curl.take_commands();
        assert!(cmds[0].contains(
            r#"UpdateParameters={"ForceUpdate":true, "Targets":["/redfish/v1/UpdateService/FirmwareInventory/MGX_FW_BMC_0"]};type=application/json"#
        ));
        assert!(cmds[0].contains("UpdateFile=@/tmp/bmc.fwpkg;type=application/octet-stream"));
        assert_eq!(
            curl.take_requests(),
            [format!("POST {mp}"), get(TASK9), get(TASK9)]
        );
        let r = c
            .redfish_api_update_firmware(&Creds, "/tmp/bmc.fwpkg", &[], false, 60.0)
            .unwrap();
        assert_eq!(r.0, ERR_CODE_OK);
        assert!(curl.take_commands()[0].contains(r#"UpdateParameters={"ForceUpdate":false};type"#));
        let cases: &[(String, &str)] = &[
            (
                task(
                    "100",
                    "OK",
                    &event("Update.1.0.ComponentUpdateSkipped", r#""a", "b""#),
                ),
                "(-13, '', [])",
            ),
            (
                task(
                    "100",
                    "OK",
                    &event(
                        "Base.1.0.ResourceErrorsDetected",
                        r#""a", "Component image is identical""#,
                    ),
                ),
                "(-13, '', [])",
            ),
            (
                task(
                    "100",
                    "Exception",
                    &event(
                        "Base.1.0.ResourceErrorsDetected",
                        r#""a", "version lower than the firmware component comparison stamp""#,
                    ),
                ),
                "(-7, 'Error: The target image has lower version', [])",
            ),
            (
                task(
                    "100",
                    "Exception",
                    &[
                        event("Base.1.0.ResourceErrorsDetected", r#""a", "flash failed""#),
                        event("Base.1.0.ResourceErrorsDetected", r#""a", "flash failed""#),
                    ]
                    .join(", "),
                ),
                "(-12, 'Error: flash failed', [])",
            ),
            (
                task(
                    "100",
                    "Cancelled",
                    r#"{"MessageId": "TaskEvent.1.0.TaskAborted"}"#,
                ),
                "(-12, 'Error: The task has been aborted', [])",
            ),
            (
                task("100", "Warning", ""),
                "(-12, 'Error: Fail to execute the task - Taskstatus=Warning', [])",
            ),
            (
                task(
                    "100",
                    "OK",
                    &[
                        r#"{"MessageId": "ResourceEvent.1.0.UpdateSuccessful"}"#.to_string(),
                        event("ResourceEvent.1.0.UpdateSuccessful", r#""a""#),
                        event("Update.1.0.ComponentUpdateSkipped", ""),
                        event("Base.1.0.ResourceErrorsDetected", r#""a""#),
                        r#"{"x": 1}"#.to_string(),
                    ]
                    .join(", "),
                ),
                "(0, '', [])",
            ),
            (
                r#"{"TaskStatus": "OK", "Messages": []}"#.into(),
                "(-2, \"Error: Missing 'PercentComplete' field in task status response\", [])",
            ),
            ("{bad".into(), "(-2, 'Error: Invalid JSON format', [])"),
        ];
        for (answer, want) in cases {
            curl.reply("GET", TASK9, 200, answer);
            assert_eq!(update(&c, 60.0), *want, "{answer}");
        }
        curl.fail("GET", TASK9, 7, "no route");
        assert_eq!(update(&c, 60.0), "(-10, 'Error: no route', [])");
        // Not finished within the timeout.
        curl.reply("GET", TASK9, 200, &task("50", "OK", ""));
        assert_eq!(
            update(&c, 0.0),
            "(-6, 'Error: Wait task completion timeout\\n', [])"
        );
        // What starting the update can answer.
        let starts: &[(&str, &str)] = &[
            ("{bad", "(-2, 'Error: Invalid JSON format', [])"),
            (
                r#"{"error": {"message": "busy"}}"#,
                "(-12, 'Error: busy', [])",
            ),
            (
                r#"{"error": {}}"#,
                "(-3, \"Error: Missing 'message' field\", [])",
            ),
            (
                r#"{"TaskStatus": "Exception"}"#,
                "(-12, 'Error: Return status is Exception', [])",
            ),
            (
                "{}",
                "(-2, \"Error: Missing 'PercentComplete' field in task status response\", [])",
            ),
        ];
        for (answer, want) in starts {
            curl.reply("POST", mp, 202, answer);
            assert_eq!(update(&c, 60.0), *want, "{answer}");
        }
        curl.fail("POST", mp, 26, "curl: (26) read error");
        assert_eq!(update(&c, 60.0), "(-4, 'Error: curl: (26) read error', [])");
    }

    #[test]
    fn task_polling_waits_out_a_timeout_and_an_unfinished_task() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let mp = REDFISH_URI_UPDATE_SERVICE_UPDATE_MULTIPART;
        curl.reply("POST", mp, 202, r#"{"TaskStatus": "OK", "Id": "9"}"#);
        let half = task("50", "OK", "");
        let done = task("100", "OK", "");
        let t = Answer::Fail(28, "");
        curl.answers(
            "GET",
            TASK9,
            &[
                t,
                t,
                t,
                Answer::Reply(200, &half),
                Answer::Reply(200, &done),
            ],
        );
        assert_eq!(update(&c, 60.0), "(0, '', [])");
        assert_eq!(curl.take_requests().len(), 6);
    }

    #[test]
    fn a_debug_log_dump_is_triggered_then_downloaded() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let dump = format!("{REDFISH_BMC_LOG_DUMP}/LogService.CollectDiagnosticData");
        let trigger = |answer: Option<&str>| {
            match answer {
                Some(a) => curl.reply("POST", &dump, 202, a),
                None => curl.fail("POST", &dump, 7, "no route"),
            }
            let (ret, (id, err)) = c.redfish_api_trigger_bmc_debug_log_dump(&Creds).unwrap();
            PyVal::Tuple(vec![PyVal::Int(ret), PyVal::Tuple(vec![id, err])]).py_repr()
        };
        assert_eq!(
            trigger(Some(
                r#"{"TaskStatus": "OK", "Id": "7", "TaskState": "Running"}"#
            )),
            "(0, ('7', None))"
        );
        assert!(curl.take_commands()[0].contains(r#"-d {"DiagnosticDataType":"Manager"}"#));
        assert_eq!(trigger(Some(r#"{"TaskStatus": "OK"}"#)), "(0, ('', None))");
        assert_eq!(
            trigger(Some(r#"{"TaskStatus": "Exception"}"#)),
            "(-12, ('-1', 'Error: Return status is Exception'))"
        );
        assert_eq!(
            trigger(Some(r#"{"error": {"message": "busy"}}"#)),
            "(-12, ('-1', 'Error: busy'))"
        );
        assert_eq!(
            trigger(Some(r#"{"error": {}}"#)),
            "(-3, ('-1', \"Error: Missing 'message' field\"))"
        );
        assert_eq!(
            trigger(Some("{}")),
            "(-3, ('-1', \"Error: Missing 'error' or 'TaskStatus' field in response\"))"
        );
        assert_eq!(
            trigger(Some("{bad")),
            "(-2, ('-1', 'Error: Invalid JSON format'))"
        );
        assert_eq!(trigger(None), "(-10, ('-1', 'Error: no route'))");
        let task7 = "/redfish/v1/TaskService/Tasks/7";
        let entry = "/redfish/v1/Managers/BMC_0/LogServices/Dump/Entries/3";
        let dir = curl.dir().to_str().unwrap().to_string();
        let download = |answer: &str| {
            curl.reply("GET", task7, 200, answer);
            let (ret, msg) = c
                .redfish_api_get_bmc_debug_log_dump(&Creds, "7", "dump.tar", &dir, 60.0)
                .unwrap();
            repr2((ret, PyVal::Str(msg)))
        };
        curl.reply("GET", &format!("{entry}/attachment"), 200, "DUMP");
        curl.take_requests();
        curl.take_commands();
        let headers = format!(r#"{{"HttpHeaders": ["Content-Type: x", "Location: {entry}"]}}"#);
        assert_eq!(
            download(&format!(
                r#"{{"PercentComplete": 100, "TaskStatus": "OK", "Messages": [], "Payload": {headers}}}"#
            )),
            "(0, '')"
        );
        assert_eq!(
            std::fs::read_to_string(curl.dir().join("dump.tar")).unwrap(),
            "DUMP"
        );
        assert_eq!(
            curl.take_requests(),
            [get(task7), format!("GET {entry}/attachment")]
        );
        assert!(curl.take_commands()[1].contains(&format!("--output {dir}/dump.tar")));
        assert_eq!(
            download(&task("100", "OK", "")),
            "(-3, \"Error: Missing 'Payload' field\")"
        );
        assert_eq!(
            download(
                r#"{"PercentComplete": 100, "TaskStatus": "OK", "Messages": [], "Payload": {}}"#
            ),
            "(-3, \"Error: Missing 'HttpHeaders' field\")"
        );
        assert_eq!(
            download(
                r#"{"PercentComplete": 100, "TaskStatus": "OK", "Messages": [], "Payload": {"HttpHeaders": ["Content-Type: x"]}}"#
            ),
            "(-3, \"Error: Missing 'Location' field\")"
        );
        assert_eq!(
            download(&task("100", "Exception", "")),
            "(-12, 'Error: Fail to execute the task - Taskstatus=Exception')"
        );
        assert_eq!(
            RedfishClient::get_uri_from_response(&None).unwrap(),
            (
                ERR_CODE_INVALID_JSON_FORMAT,
                "Error: Invalid JSON format".into(),
                None
            )
        );
    }

    #[test]
    fn a_password_change_reads_the_bmc_s_verdict() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let acc = format!("{REDFISH_URI_ACCOUNTS}/nosuser");
        let change = |status: u16, body: &str| {
            curl.reply("PATCH", &acc, status, body);
            repr2(
                c.redfish_api_change_login_password(&Creds, "N3w!", None)
                    .unwrap(),
            )
        };
        assert_eq!(change(204, ""), "(0, '')");
        assert_eq!(curl.take_requests(), [format!("PATCH {acc}")]);
        assert!(curl.take_commands()[0].contains(r#"-d {"Password" : "N3w!"}"#));
        assert_eq!(
            change(
                200,
                r#"{"@Message.ExtendedInfo": [{"MessageId": "Base.1.15.Success"}]}"#
            ),
            "(0, '')"
        );
        assert_eq!(
            change(400, r#"{"error": {"message": "weak"}}"#),
            "(-12, 'weak')"
        );
        assert_eq!(
            change(
                400,
                r#"{"Password@Message.ExtendedInfo": [{"MessageId": "Base.1.15.PropertyValueFormatError", "Message": "too short", "Resolution": "longer"}]}"#
            ),
            "(-12, 'too short')"
        );
        assert_eq!(
            change(
                200,
                r#"{"Password@Message.ExtendedInfo": [{"MessageId": "Base.1.15.Note"}], "@Message.ExtendedInfo": [{"MessageId": "Base.1.15.Created"}]}"#
            ),
            "(-3, 'Error: Unexpected response format')"
        );
        assert_eq!(change(200, "{bad"), "(-2, 'Error: Invalid JSON format')");
        assert_eq!(
            change(200, r#"{"error": {}}"#),
            "(-3, 'Error: Unexpected response format')"
        );
        curl.fail("PATCH", &acc, 7, "no route");
        assert_eq!(
            repr2(
                c.redfish_api_change_login_password(&Creds, "N3w!", None)
                    .unwrap()
            ),
            "(-10, 'Error: no route')"
        );
        curl.reply("PATCH", &format!("{REDFISH_URI_ACCOUNTS}/root"), 204, "");
        assert_eq!(
            repr2(
                c.redfish_api_change_login_password(&Creds, "N3w!", Some("root"))
                    .unwrap()
            ),
            "(0, '')"
        );
    }

    #[test]
    fn the_minimum_password_length_is_read_and_set() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let svc = REDFISH_URI_ACCOUNT_SERVICE;
        let set = |status: u16, body: &str| {
            curl.reply("PATCH", svc, status, body);
            repr2(
                c.redfish_api_set_min_password_length(&Creds, &PyVal::Int(12))
                    .unwrap(),
            )
        };
        assert_eq!(set(204, ""), "(0, '')");
        assert!(curl.take_commands()[0].contains(r#"-d {"MinPasswordLength": 12}"#));
        assert_eq!(
            set(
                200,
                r#"{"@Message.ExtendedInfo": [{"MessageId": "Base.1.15.Success"}]}"#
            ),
            "(0, '')"
        );
        assert_eq!(
            set(
                200,
                r#"{"@Message.ExtendedInfo": [{"MessageId": "Base.1.15.Fail"}, {}]}"#
            ),
            "(-3, 'Error: Unexpected response format')"
        );
        assert_eq!(
            set(400, r#"{"error": {"message": "too long"}}"#),
            "(-12, 'too long')"
        );
        assert_eq!(
            set(400, r#"{"error": {}}"#),
            "(-12, \"Missing 'message' field\")"
        );
        assert_eq!(set(200, "{bad"), "(-2, 'Error: Invalid JSON format')");
        assert_eq!(
            set(200, r#"{"@Message.ExtendedInfo": 5}"#),
            "(-3, \"Error: 'int' object is not iterable\")"
        );
        assert_eq!(
            set(200, r#"{"error": 5}"#),
            "(-3, \"Error: 'int' object has no attribute 'get'\")"
        );
        curl.fail("PATCH", svc, 7, "no route");
        assert_eq!(
            repr2(
                c.redfish_api_set_min_password_length(&Creds, &PyVal::Int(12))
                    .unwrap()
            ),
            "(-10, 'Error: no route')"
        );
        let read = |body: &str| {
            curl.reply("GET", svc, 200, body);
            repr2(c.redfish_api_get_min_password_length(&Creds).unwrap())
        };
        assert_eq!(read(r#"{"MinPasswordLength": 12}"#), "(0, 12)");
        assert_eq!(
            read("{}"),
            "(-3, 'Error: MinPasswordLength not found in response')"
        );
        assert_eq!(
            read(r#"{"error": {"message": "denied"}}"#),
            "(-12, 'denied')"
        );
        assert_eq!(
            read(r#"{"error": {}}"#),
            "(-12, \"Missing 'message' field\")"
        );
        assert_eq!(read("{bad"), "(-2, 'Error: Invalid JSON format')");
        assert_eq!(
            read("[1]"),
            "(-3, \"Error: 'list' object has no attribute 'get'\")"
        );
        curl.fail("GET", svc, 7, "no route");
        assert_eq!(
            repr2(c.redfish_api_get_min_password_length(&Creds).unwrap()),
            "(-10, 'Error: no route')"
        );
    }

    #[test]
    fn a_bmc_reset_reads_the_bmc_s_answer() {
        let curl = FakeCurl::new();
        let c = logged_in(&curl);
        let reset = |status: u16, body: &str| {
            curl.reply("POST", REDFISH_REQUEST_BMC_RESET, status, body);
            repr2(
                c.redfish_api_request_bmc_reset(&Creds, REDFISH_BMC_GRACEFUL_RESTART)
                    .unwrap(),
            )
        };
        assert_eq!(reset(204, ""), "(0, '')");
        assert!(curl.take_commands()[0].contains(r#"-d {"ResetType": "GracefulRestart"}"#));
        assert_eq!(reset(200, "{}"), "(0, '')");
        assert_eq!(
            reset(
                400,
                r#"{"error": {"message": "bad type", "code": "Base.1.8.ActionParameterUnknown"}}"#
            ),
            "(-11, 'bad type')"
        );
        assert_eq!(
            reset(400, r#"{"error": {"message": "busy"}}"#),
            "(-12, 'busy')"
        );
        assert_eq!(
            reset(400, r#"{"error": {}}"#),
            "(-3, \"Missing 'message' field\")"
        );
        assert_eq!(reset(200, "{bad"), "(-2, 'Error: Invalid JSON format')");
        curl.fail("POST", REDFISH_REQUEST_BMC_RESET, 7, "no route");
        assert_eq!(
            repr2(
                c.redfish_api_request_bmc_reset(&Creds, REDFISH_BMC_FORCE_RESTART)
                    .unwrap()
            ),
            "(-10, 'no route')"
        );
    }

    #[test]
    fn secrets_in_responses_and_urls_are_masked() {
        assert_eq!(
            RedfishClient::obfuscate_login_response(
                "X-Auth-Token: abc\r\nLocation: /redfish/v1/SessionService/Sessions/s1\r\n\r\n{\"@odata.id\": \"/redfish/v1/SessionService/Sessions/s1\", \"Id\": \"s1\", \"UserName\": \"u\", \"token\": \"t\"}"
            ),
            "X-Auth-Token: ******\r\nLocation: /redfish/v1/SessionService/Sessions/******\r\n\r\n{\"@odata.id\": \"/redfish/v1/SessionService/Sessions/******\", \"Id\": \"******\", \"UserName\": \"******\", \"token\": \"******\"}"
        );
        assert_eq!(
            RedfishClient::obfuscate_logout_response(
                "{\"data\": \"User 'admin' logged out\", \"x\": \"/redfish/v1/SessionService/Sessions/s1\"}"
            ),
            "{\"data\": \"User '******' logged out\", \"x\": \"/redfish/v1/SessionService/Sessions/******\"}"
        );
        assert_eq!(
            RedfishClient::obfuscate_password(r#"-d '{"Password" : "p"}'"#),
            r#"-d '{"Password" : "******"}'"#
        );
        assert_eq!(
            RedfishClient::obfuscate_username_in_url(
                "https://h/redfish/v1/AccountService/Accounts/root -d"
            ),
            "https://h/redfish/v1/AccountService/Accounts/****** -d"
        );
        assert_eq!(
            RedfishClient::obfuscate_session_id_in_url(
                "https://h/redfish/v1/SessionService/Sessions/s1 -k"
            ),
            "https://h/redfish/v1/SessionService/Sessions/****** -k"
        );
        assert_eq!(
            RedfishClient::obfuscate_user_password("curl -u admin:secret -k"),
            "curl -u ******:****** -k"
        );
        let (h, b) = RedfishClient::get_headers_and_body("no blank line");
        assert_eq!((h.len(), b.as_str()), (0, "no blank line"));
        let (h, _) = RedfishClient::get_headers_and_body("A: 1\nB: 2\nA: 3\n\nbody");
        assert_eq!(
            h,
            [
                ("a".to_string(), "3".to_string()),
                ("b".to_string(), "2".to_string())
            ]
        );
    }

    #[test]
    fn json_and_numbers_are_written_as_python_writes_them() {
        let dict = PyVal::Dict(vec![
            (PyVal::str("a"), PyVal::Int(1)),
            (PyVal::Int(2), PyVal::Bool(true)),
        ]);
        let cases = [
            (PyVal::None, "null"),
            (PyVal::Bool(false), "false"),
            (PyVal::Float(1.5), "1.5"),
            (PyVal::Float(f64::NAN), "NaN"),
            (PyVal::Float(f64::INFINITY), "Infinity"),
            (PyVal::Float(f64::NEG_INFINITY), "-Infinity"),
            (
                PyVal::str("\u{e9}\n\r\t\u{8}\u{c}\u{1}\\\u{1f600}"),
                r#""\u00e9\n\r\t\b\f\u0001\\\ud83d\ude00""#,
            ),
            (
                PyVal::List(vec![PyVal::Int(1), PyVal::str("a")]),
                r#"[1, "a"]"#,
            ),
            (PyVal::Tuple(vec![]), "[]"),
            (dict, r#"{"a": 1, "2": true}"#),
        ];
        for (v, want) in cases {
            assert_eq!(json_dumps(&v).unwrap(), want);
        }
        // What JSON has no form for raises, as `json.dumps` does.
        let refused = |v: PyVal| {
            json_dumps(&v)
                .map_err(|e| (e.exc.name(), e.str()))
                .unwrap_err()
        };
        assert_eq!(
            refused(PyVal::Bytes(b"x".to_vec())),
            (
                "TypeError",
                "Object of type bytes is not JSON serializable".to_string()
            )
        );
        assert_eq!(
            refused(PyVal::Dict(vec![(PyVal::Tuple(vec![]), PyVal::Int(1))])),
            (
                "TypeError",
                "keys must be str, int, float, bool or None, not tuple".to_string()
            )
        );
        assert_eq!(
            (fmt_num(0.0), fmt_num(2.5), fmt_num(1e20)),
            ("0".into(), "2.5".into(), "1e+20".into())
        );
        assert_eq!(s(&None), "None");
        assert_eq!(
            loads(&None).map_err(|e| e.exc.name()).err(),
            Some("TypeError")
        );
        log_multi_line_str(None);
        assert!(!is_exception(&PyErr::other("KeyboardInterrupt", "")));
        assert_eq!(now_hms_us().len(), 15);
    }
}
