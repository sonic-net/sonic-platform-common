//! `sonic_platform_base.sonic_storage`: the switch's disks, as stormond
//! reads them -- `StorageDevices` and the utility class per disk kind, with
//! the tools they run (smartctl, iSmart, SmartCmd, lsblk) and the files
//! they read.
//!
//! The readings keep their Python types -- a health parsed from smartctl is
//! a string, one computed from a vendor's counters a float -- because the
//! escape hatch writes `str()` of them, and `str(98.0)` is not `"98"`.

use std::collections::HashMap;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Mutex, RwLock};

use regex::Regex;

use crate::io;
use crate::logger::SysLogger;
use crate::py::{int_of_float, py_float, py_int, Exc, PyErr, PyResult, PyVal};

pub const BASE_PATH: &str = "/sys/block";
pub const BLKDEV_BASE_PATH: &str = "/dev";
const NOT_AVAILABLE: &str = "N/A";

fn na() -> PyVal {
    PyVal::str(NOT_AVAILABLE)
}

fn print(msg: &str) {
    use std::io::Write;
    let _ = writeln!(std::io::stdout(), "{msg}");
}

/// What the escape hatch asks of a disk.
pub trait StorageDisk: Send {
    fn fetch_parse_info(&mut self, diskdev: &str) -> PyResult<()>;
    fn get_model(&self) -> PyResult<PyVal>;
    fn get_serial(&self) -> PyResult<PyVal>;
    fn get_firmware(&self) -> PyResult<PyVal>;
    fn get_health(&self) -> PyResult<PyVal>;
    fn get_temperature(&self) -> PyResult<PyVal>;
    fn get_disk_io_reads(&self) -> PyResult<PyVal>;
    fn get_disk_io_writes(&self) -> PyResult<PyVal>;
    fn get_reserved_blocks(&self) -> PyResult<PyVal>;
    fn get_fs_io_reads(&self) -> PyResult<PyVal>;
    fn get_fs_io_writes(&self) -> PyResult<PyVal>;
}

// -- psutil.disk_io_counters(perdisk=True, nowrap=True) ----------------------

/// psutil's `_wrap_numbers` state for disk counters: the last raw values,
/// and what has been added to each counter for every time it went down.
#[derive(Default)]
struct Wrap {
    cache: Option<HashMap<String, Vec<i128>>>,
    reminders: HashMap<(String, usize), i128>,
}

static WRAP: Mutex<Option<Wrap>> = Mutex::new(None);

/// `(read_count, write_count)` per disk, after psutil's wrap correction.
fn disk_io_counters() -> PyResult<HashMap<String, (i128, i128)>> {
    let text = io::read_text("/proc/diskstats")?;
    let mut raw: Vec<(String, Vec<i128>)> = Vec::new();
    for line in text.split_inclusive('\n') {
        let f: Vec<&str> = line.split_whitespace().collect();
        let ints = |s: &[&str]| -> PyResult<Vec<i128>> { s.iter().map(|x| py_int(x)).collect() };
        let (name, vals) = match f.len() {
            15 => {
                let mut v = vec![py_int(f[2])?];
                v.extend(ints(&f[4..14])?);
                (f[3], v)
            }
            14 | 18.. => (f[2], ints(&f[3..14])?),
            7 => {
                let v = ints(&f[3..7])?;
                // reads, rbytes, writes, wbytes; the rest are zero.
                (f[2], vec![v[0], 0, v[1], 0, v[2], 0, v[3], 0, 0, 0, 0])
            }
            _ => {
                return Err(PyErr::value_error(format!(
                    "not sure how to interpret line {}",
                    crate::py::str_repr(line)
                )))
            }
        };
        // (reads, writes, rbytes, wbytes, rtime, wtime, rmerged, wmerged, busy)
        let t = (
            vals[0], vals[4], vals[2], vals[6], vals[3], vals[7], vals[1], vals[5], vals[9],
        );
        let row = vec![t.0, t.1, t.2 * 512, t.3 * 512, t.4, t.5, t.6, t.7, t.8];
        match raw.iter_mut().find(|(n, _)| n == name) {
            Some(e) => e.1 = row,
            None => raw.push((name.to_string(), row)),
        }
    }
    // Nothing read is nothing answered, and the wrap state is left as it
    // was: psutil returns before `_wrap_numbers` sees an empty reading, so
    // the corrections carry on past it.
    if raw.is_empty() {
        return Ok(HashMap::new());
    }
    let mut wrap = WRAP
        .lock()
        .map_err(|_| PyErr::runtime_error("psutil state poisoned"))?;
    let w = wrap.get_or_insert_with(Wrap::default);
    let mut out = HashMap::new();
    let prev = w.cache.take();
    for (name, vals) in &raw {
        let adjusted: Vec<i128> = match prev.as_ref().and_then(|c| c.get(name)) {
            None => vals.clone(),
            Some(old) => vals
                .iter()
                .enumerate()
                .map(|(i, v)| {
                    let key = (name.clone(), i);
                    if old.get(i).is_some_and(|o| v < o) {
                        *w.reminders.entry(key.clone()).or_insert(0) += old[i];
                    }
                    v + w.reminders.get(&key).copied().unwrap_or(0)
                })
                .collect(),
        };
        out.insert(name.clone(), (adjusted[0], adjusted[1]));
    }
    w.cache = Some(raw.into_iter().collect());
    w.reminders
        .retain(|(n, _), _| w.cache.as_ref().is_some_and(|c| c.contains_key(n)));
    Ok(out)
}

/// `StorageCommon`: the filesystem's view of a disk.
struct Common {
    storage_disk: String,
}

impl Common {
    fn new(diskdev: &str) -> Common {
        Common {
            storage_disk: diskdev.rsplit('/').next().unwrap_or(diskdev).to_string(),
        }
    }

    fn fs_io(&self, log: &SysLogger, reads: bool) -> PyVal {
        let what = if reads {
            "get_fs_io_reads"
        } else {
            "get_fs_io_writes"
        };
        let r = disk_io_counters().and_then(|d| {
            d.get(&self.storage_disk)
                .map(|(r, w)| if reads { *r } else { *w })
                .ok_or_else(|| PyErr::key_error(self.storage_disk.as_str()))
        });
        match r {
            Ok(v) => PyVal::Int(v),
            Err(e) => {
                log.log_warning(&format!("{what} exception: {}", e.str()));
                PyVal::Int(0)
            }
        }
    }
}

// -- the tools -------------------------------------------------------------------

/// Where a test keeps stand-ins for the tools: there, a bare name runs as
/// `sh <dir>/<name>`, and one the directory lacks is not found.  Unset, as on
/// a switch, the name is looked up in PATH, as Python's `Popen` does.
static TOOL_DIR: RwLock<Option<PathBuf>> = RwLock::new(None);

/// Run the tools from `dir`, or from PATH again with `None`.
#[cfg(any(test, feature = "testing"))]
pub fn set_tool_dir(dir: Option<PathBuf>) {
    if let Ok(mut d) = TOOL_DIR.write() {
        *d = dir;
    }
}

/// `Popen([prog, ...])`'s program.
fn command(prog: &str) -> Command {
    match TOOL_DIR.read().ok().and_then(|d| d.clone()) {
        Some(dir) if dir.join(prog).is_file() => {
            let mut c = Command::new("sh");
            c.arg(dir.join(prog));
            c
        }
        Some(dir) => Command::new(dir.join(prog)),
        None => Command::new(prog),
    }
}

// -- SsdUtil ------------------------------------------------------------------

const SMARTCTL: &str = "smartctl {} -a";
const INNODISK: &str = "iSmart -d {}";
const VIRTIUM: &str = "SmartCmd -m {}";

/// `subprocess.Popen(cmd.split(), universal_newlines=True, stdout=PIPE)`'s
/// output: decoded strictly with the locale's codec, newlines translated.
fn execute_shell(cmd: &str) -> PyResult<String> {
    let argv: Vec<&str> = cmd.split_whitespace().collect();
    let Some((prog, args)) = argv.split_first() else {
        return Err(PyErr::index_error("list index out of range"));
    };
    let out = command(prog)
        .args(args)
        .stdin(Stdio::inherit())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .output()
        .map_err(|e| PyErr::from_io(&e, Some(prog)))?;
    crate::subprocess::text(&out.stdout)
}

/// `_parse_re(pattern, buffer)`: `re.findall`'s first item, or "N/A".
fn parse_re(pattern: &str, buffer: &str) -> PyResult<String> {
    let re = Regex::new(pattern).map_err(|e| PyErr::runtime_error(e.to_string()))?;
    Ok(match re.captures(buffer) {
        Some(c) => c
            .get(1)
            .or_else(|| c.get(0))
            .map_or(String::new(), |m| m.as_str().to_string()),
        None => NOT_AVAILABLE.to_string(),
    })
}

/// `parse_id_number(id, buffer)`: the rest of the first line that starts,
/// once stripped, with the id -- sliced from the unstripped line.
fn parse_id_number(id: &str, buffer: &str) -> String {
    if !buffer.is_empty() {
        for line in buffer.split('\n') {
            if crate::py::strip(line).starts_with(id) {
                return line.chars().skip(id.chars().count()).collect();
            }
        }
    }
    NOT_AVAILABLE.to_string()
}

/// `s.split()[i]`, Python's negative indexes included.
fn word(s: &str, i: isize) -> PyResult<String> {
    let w: Vec<&str> = s.split_whitespace().collect();
    let idx = if i < 0 { w.len() as isize + i } else { i };
    usize::try_from(idx)
        .ok()
        .and_then(|i| w.get(i))
        .map(|s| s.to_string())
        .ok_or_else(|| PyErr::index_error("list index out of range"))
}

fn strip_chars<'a>(s: &'a str, chars: &str) -> &'a str {
    s.trim_matches(|c| chars.contains(c))
}

fn hex_id(id: u32) -> String {
    format!("[{}]", format!("{id:x}").to_uppercase())
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Vendor {
    Generic,
    InnoDisk,
    M2,
    StorFly,
    Virtium,
    Swissbit,
    Micron,
    Intel,
    Transcend,
    Atp,
}

impl Vendor {
    fn from_key(k: &str) -> Option<Vendor> {
        Some(match k {
            "Generic" => Vendor::Generic,
            "InnoDisk" => Vendor::InnoDisk,
            "M.2" => Vendor::M2,
            "StorFly" => Vendor::StorFly,
            "Virtium" => Vendor::Virtium,
            "Swissbit" => Vendor::Swissbit,
            "Micron" => Vendor::Micron,
            "Intel" => Vendor::Intel,
            "Transcend" => Vendor::Transcend,
            "ATP" => Vendor::Atp,
            _ => return None,
        })
    }
    fn utility(self) -> &'static str {
        match self {
            Vendor::InnoDisk | Vendor::M2 => INNODISK,
            Vendor::StorFly | Vendor::Virtium => VIRTIUM,
            _ => SMARTCTL,
        }
    }
}

/// `SsdUtil(diskdev)`.
pub struct SsdUtil {
    dev: String,
    log: SysLogger,
    common: Option<Common>,
    model: PyVal,
    serial: PyVal,
    firmware: PyVal,
    temperature: PyVal,
    health: PyVal,
    ssd_info: String,
    vendor_ssd_info: String,
    disk_io_reads: PyVal,
    disk_io_writes: PyVal,
    reserved_blocks: PyVal,
}

impl SsdUtil {
    /// The constructor parses once with its own logger, then
    /// `StorageCommon.__init__` replaces it: every later line is logged as
    /// "StorageCommon".
    pub fn new(diskdev: &str) -> PyResult<SsdUtil> {
        let mut s = SsdUtil {
            dev: diskdev.to_string(),
            log: SysLogger::new(Some("SsdUtil")),
            common: None,
            model: na(),
            serial: na(),
            firmware: na(),
            temperature: na(),
            health: na(),
            ssd_info: NOT_AVAILABLE.into(),
            vendor_ssd_info: NOT_AVAILABLE.into(),
            disk_io_reads: na(),
            disk_io_writes: na(),
            reserved_blocks: na(),
        };
        s.fetch(diskdev)?;
        s.log = SysLogger::new(Some("StorageCommon"));
        s.common = Some(Common::new(diskdev));
        Ok(s)
    }

    fn fetch(&mut self, diskdev: &str) -> PyResult<()> {
        self.ssd_info = execute_shell(&SMARTCTL.replace("{}", diskdev))?;
        self.parse_generic_ssd_info()?;
        if self.model.truthy() {
            let vendor = self.parse_vendor()?;
            if matches!(vendor, Some(Vendor::Virtium | Vendor::Atp | Vendor::Micron))
                && self.dev.contains("nvme")
            {
                return Ok(());
            }
            if let Some(v) = vendor {
                let r = (|| -> PyResult<()> {
                    self.vendor_ssd_info = execute_shell(&v.utility().replace("{}", diskdev))?;
                    self.parse_vendor_ssd_info(v)
                })();
                if let Err(e) = r {
                    self.log.log_error(&e.str());
                }
            }
        } else {
            self.model = PyVal::str("Unknown");
        }
        Ok(())
    }

    fn model_str(&self) -> String {
        self.model.py_str()
    }

    /// `_parse_vendor()`.
    fn parse_vendor(&self) -> PyResult<Option<Vendor>> {
        let model = self.model_str();
        let short = word(&model, 0)?;
        if let Some(v) = Vendor::from_key(&short) {
            return Ok(Some(v));
        }
        let first = model.split('_').next().unwrap_or("");
        let micron =
            Regex::new(r"(?i)\bmicron\b").map_err(|e| PyErr::runtime_error(e.to_string()))?;
        let intel =
            Regex::new(r"(?i)\bintel\b").map_err(|e| PyErr::runtime_error(e.to_string()))?;
        Ok(if model.starts_with("VSF") {
            Some(Vendor::Virtium)
        } else if model.starts_with("SFS") {
            Some(Vendor::Swissbit)
        } else if micron.is_match(first) {
            Some(Vendor::Micron)
        } else if intel.is_match(&model) {
            Some(Vendor::Intel)
        } else if model.starts_with("TS") {
            Some(Vendor::Transcend)
        } else {
            None
        })
    }

    fn parse_nvme_ssd_info(&mut self) -> PyResult<()> {
        let info = self.ssd_info.clone();
        self.model = PyVal::Str(parse_re(r"Model Number:\s*(.+?)\n", &info)?);
        let health_raw = parse_re(r"Percentage Used\s*(.+?)\n", &info)?;
        self.health = if health_raw == NOT_AVAILABLE {
            na()
        } else {
            let h = word(&health_raw, -1)?;
            PyVal::Float(100.0 - py_float(strip_chars(&h, "%"))?)
        };
        let temp_raw = parse_re(r"Temperature\s*(.+?)\n", &info)?;
        self.temperature = if temp_raw == NOT_AVAILABLE {
            na()
        } else {
            PyVal::Float(py_float(&word(&temp_raw, -2)?)?)
        };
        let spare = parse_re(r"Available Spare\s*(.+?)\n", &info)?;
        if spare != NOT_AVAILABLE {
            self.reserved_blocks = PyVal::Float(py_float(strip_chars(&word(&spare, -1)?, "%"))?);
        }
        let reads = parse_re(r"Data Units Read\s*(.+?)\n", &info)?;
        if reads != NOT_AVAILABLE {
            self.disk_io_reads =
                PyVal::Str(crate::py::strip(reads.rsplit(':').next().unwrap_or("")).to_string());
        }
        let writes = parse_re(r"Data Units Written\s*(.+?)\n", &info)?;
        if writes != NOT_AVAILABLE {
            self.disk_io_writes =
                PyVal::Str(crate::py::strip(writes.rsplit(':').next().unwrap_or("")).to_string());
        }
        Ok(())
    }

    fn parse_generic_ssd_info(&mut self) -> PyResult<()> {
        let info = self.ssd_info.clone();
        if self.dev.contains("nvme") {
            self.parse_nvme_ssd_info()?;
        } else {
            self.model = PyVal::Str(parse_re(r"Device Model:\s*(.+?)\n", &info)?);
            let mut health_raw = parse_re(r"Remaining_Lifetime_Perc\s*(.+?)\n", &info)?;
            if health_raw == NOT_AVAILABLE {
                for id in [169, 231] {
                    health_raw = parse_id_number(&id.to_string(), &info);
                    if health_raw != NOT_AVAILABLE {
                        break;
                    }
                }
                self.health = if health_raw == NOT_AVAILABLE {
                    na()
                } else {
                    PyVal::Str(word(&health_raw, -1)?)
                };
            } else {
                self.health = PyVal::Str(word(&health_raw, -1)?);
            }
            let temp_raw = parse_re(r"Temperature_Celsius\s*(.+?)\n", &info)?;
            self.temperature = if temp_raw == NOT_AVAILABLE {
                na()
            } else {
                PyVal::Str(word(&word(&temp_raw, 7)?, 0)?)
            };
            let r = parse_id_number("242", &info);
            self.disk_io_reads = if r == NOT_AVAILABLE {
                na()
            } else {
                PyVal::Str(word(&r, -1)?)
            };
            let w = parse_id_number("241", &info);
            self.disk_io_writes = if w == NOT_AVAILABLE {
                na()
            } else {
                PyVal::Str(word(&w, -1)?)
            };
            for id in [170, 232] {
                let rbc = parse_id_number(&id.to_string(), &info);
                if rbc == NOT_AVAILABLE {
                    self.reserved_blocks = na();
                } else {
                    self.reserved_blocks = PyVal::Str(word(&rbc, -1)?);
                    break;
                }
            }
        }
        self.serial = PyVal::Str(parse_re(r"Serial Number:\s*(.+?)\n", &info)?);
        self.firmware = PyVal::Str(parse_re(r"Firmware Version:\s*(.+?)\n", &info)?);
        Ok(())
    }

    fn is_na(v: &PyVal) -> bool {
        matches!(v, PyVal::Str(s) if s == NOT_AVAILABLE)
    }

    fn parse_vendor_ssd_info(&mut self, v: Vendor) -> PyResult<()> {
        match v {
            Vendor::Generic | Vendor::Transcend => self.parse_generic_ssd_info(),
            Vendor::InnoDisk | Vendor::M2 => self.parse_innodisk_info(),
            Vendor::StorFly | Vendor::Virtium => self.parse_virtium_info(),
            Vendor::Swissbit => self.parse_swissbit_info(),
            Vendor::Micron => self.parse_micron_info(),
            Vendor::Intel => self.parse_intel_info(),
            Vendor::Atp => self.parse_atp_info(),
        }
    }

    fn parse_innodisk_info(&mut self) -> PyResult<()> {
        let info = self.vendor_ssd_info.clone();
        if !info.is_empty() {
            if Self::is_na(&self.health) {
                self.health = PyVal::Str(parse_re(r"Health:\s*(.+?)%", &info)?);
            }
            if Self::is_na(&self.temperature) {
                self.temperature = PyVal::Str(parse_re(r"Temperature\s*\[\s*(.+?)\]", &info)?);
            }
            if Self::is_na(&self.firmware) {
                self.firmware = PyVal::Str(word(&parse_re(r".*FW.*", &info)?, -1)?);
            }
            if Self::is_na(&self.serial) {
                self.serial = PyVal::Str(word(&parse_re(r".*Serial.*", &info)?, -1)?);
            }
        }
        let field = |id: u32, idx: isize, strip_brackets: bool| -> PyResult<PyVal> {
            let raw = parse_id_number(&hex_id(id), &info);
            if raw == NOT_AVAILABLE {
                return Ok(na());
            }
            let w = word(&raw, idx)?;
            Ok(PyVal::Str(if strip_brackets {
                strip_chars(&w, "[]").to_string()
            } else {
                w
            }))
        };
        if Self::is_na(&self.health) {
            self.health = field(169, -2, true)?;
        }
        if Self::is_na(&self.temperature) {
            self.temperature = field(194, -6, false)?;
        }
        if Self::is_na(&self.disk_io_reads) {
            self.disk_io_reads = field(242, -2, true)?;
        }
        if Self::is_na(&self.disk_io_writes) {
            self.disk_io_writes = field(241, -2, true)?;
        }
        if Self::is_na(&self.reserved_blocks) {
            self.reserved_blocks = field(232, -2, true)?;
        }
        Ok(())
    }

    fn parse_virtium_info(&mut self) -> PyResult<()> {
        let info = self.vendor_ssd_info.clone();
        if info.is_empty() {
            return Ok(());
        }
        let temp = parse_re(r"Temperature_Celsius\s*\d*\s*(\d+?)\s+", &info)?;
        if temp != NOT_AVAILABLE {
            self.temperature = PyVal::Str(temp);
        }
        let model = self.model_str();
        if ["VSFDM8XC240G-V11-T", "Virtium VTSM24ABXI160-BM110006"].contains(&model.as_str()) {
            let raw = parse_id_number("231", &info);
            self.health = if raw == NOT_AVAILABLE {
                na()
            } else {
                PyVal::Float(py_float(&word(&raw, 2)?)?)
            };
        } else {
            let nand = parse_re(r"NAND_Endurance\s*\d*\s*(\d+?)\s+", &info)?;
            let avg = parse_re(r"Average_Erase_Count\s*\d*\s*(\d+?)\s+", &info)?;
            if nand != NOT_AVAILABLE && avg != NOT_AVAILABLE {
                let r = (|| -> PyResult<f64> {
                    let a = py_float(&avg)?;
                    let n = py_float(&nand)?;
                    if n == 0.0 {
                        return Err(PyErr::new(
                            Exc::ZeroDivisionError,
                            vec![PyVal::str("float division by zero")],
                        ));
                    }
                    Ok(100.0 - (a * 100.0 / n))
                })();
                match r {
                    Ok(h) => self.health = PyVal::Float(h),
                    Err(e) => self.log.log_info(&format!(
                        "SsdUtil parse_virtium_info exception: {}",
                        e.str()
                    )),
                }
            } else {
                let raw = parse_re(r"Remaining_Life_Left\s*\d*\s*(\d+?)\s+", &info)?;
                if raw == NOT_AVAILABLE {
                    self.health = na();
                } else {
                    match py_float(&word(&raw, -1)?) {
                        Ok(h) => self.health = PyVal::Float(h),
                        Err(e) => self.log.log_info(&format!(
                            "SsdUtil parse_virtium_info exception: {}",
                            e.str()
                        )),
                    }
                }
            }
        }
        let last = |id: &str| -> PyResult<PyVal> {
            let raw = parse_id_number(id, &info);
            if raw == NOT_AVAILABLE {
                Ok(na())
            } else {
                Ok(PyVal::Str(word(&raw, -1)?))
            }
        };
        if Self::is_na(&self.disk_io_reads) {
            self.disk_io_reads = last("242")?;
        }
        if Self::is_na(&self.disk_io_writes) {
            self.disk_io_writes = last("241")?;
        }
        if Self::is_na(&self.reserved_blocks) {
            self.reserved_blocks = last("232")?;
        }
        Ok(())
    }

    fn parse_swissbit_info(&mut self) -> PyResult<()> {
        let info = self.ssd_info.clone();
        if !info.is_empty() {
            let h = parse_id_number("248", &info);
            self.health = if h == NOT_AVAILABLE {
                na()
            } else {
                PyVal::Str(word(&h, -1)?)
            };
            let t = parse_id_number("194", &info);
            self.temperature = if t == NOT_AVAILABLE {
                na()
            } else {
                PyVal::Str(word(&t, 8)?)
            };
        }
        Ok(())
    }

    /// `parse_micron_info()`, whose fallback divides by `nand_endurance` --
    /// a name the method never defines.
    fn parse_micron_info(&mut self) -> PyResult<()> {
        let info = self.vendor_ssd_info.clone();
        if info.is_empty() {
            return Ok(());
        }
        let mut health_raw = parse_re(r"Percent_Lifetime_Used\s*(.+?)\n", &info)?;
        if health_raw == NOT_AVAILABLE {
            health_raw = parse_re(r"Percent_Lifetime_Remain\s*(.+?)\n", &info)?;
            self.health = PyVal::Str(word(&health_raw, -1)?);
        } else {
            self.health = PyVal::Str((100 - py_int(&word(&health_raw, -1)?)?).to_string());
        }
        if health_raw == NOT_AVAILABLE {
            let avg = parse_id_number("173", &info);
            let fail = parse_id_number("172", &info);
            if avg != NOT_AVAILABLE && fail != NOT_AVAILABLE {
                match py_float(&avg) {
                    Err(e) => self
                        .log
                        .log_info(&format!("SsdUtil parse_micron_info exception: {}", e.str())),
                    Ok(_) => {
                        return Err(PyErr::other(
                            "NameError",
                            "name 'nand_endurance' is not defined",
                        ))
                    }
                }
            }
        }
        let w = parse_id_number("246", &info);
        self.disk_io_writes = if w == NOT_AVAILABLE {
            na()
        } else {
            PyVal::Str(word(&w, -1)?)
        };
        for id in ["170", "180"] {
            let rbc = parse_id_number(id, &info);
            if rbc == NOT_AVAILABLE {
                self.reserved_blocks = na();
            } else {
                self.reserved_blocks = PyVal::Str(word(&rbc, -1)?);
                break;
            }
        }
        Ok(())
    }

    fn parse_intel_info(&mut self) -> PyResult<()> {
        let info = self.vendor_ssd_info.clone();
        if !info.is_empty() {
            let h = parse_id_number("233", &info);
            self.health = if h == NOT_AVAILABLE {
                na()
            } else {
                PyVal::Str(PyVal::Float(100.0 - py_float(&word(&h, -1)?)?).py_str())
            };
        }
        Ok(())
    }

    fn parse_atp_info(&mut self) -> PyResult<()> {
        let info = self.vendor_ssd_info.clone();
        if !info.is_empty() {
            let h = parse_id_number("248", &info);
            self.health = if h == NOT_AVAILABLE {
                na()
            } else {
                PyVal::Str(word(&h, -1)?)
            };
        }
        Ok(())
    }
}

impl StorageDisk for SsdUtil {
    fn fetch_parse_info(&mut self, diskdev: &str) -> PyResult<()> {
        self.fetch(diskdev)
    }
    fn get_model(&self) -> PyResult<PyVal> {
        Ok(self.model.clone())
    }
    fn get_serial(&self) -> PyResult<PyVal> {
        Ok(self.serial.clone())
    }
    fn get_firmware(&self) -> PyResult<PyVal> {
        Ok(self.firmware.clone())
    }
    fn get_health(&self) -> PyResult<PyVal> {
        Ok(self.health.clone())
    }
    fn get_temperature(&self) -> PyResult<PyVal> {
        Ok(self.temperature.clone())
    }
    fn get_disk_io_reads(&self) -> PyResult<PyVal> {
        Ok(self.disk_io_reads.clone())
    }
    fn get_disk_io_writes(&self) -> PyResult<PyVal> {
        Ok(self.disk_io_writes.clone())
    }
    fn get_reserved_blocks(&self) -> PyResult<PyVal> {
        Ok(self.reserved_blocks.clone())
    }
    fn get_fs_io_reads(&self) -> PyResult<PyVal> {
        Ok(self
            .common
            .as_ref()
            .map_or(PyVal::Int(0), |c| c.fs_io(&self.log, true)))
    }
    fn get_fs_io_writes(&self) -> PyResult<PyVal> {
        Ok(self
            .common
            .as_ref()
            .map_or(PyVal::Int(0), |c| c.fs_io(&self.log, false)))
    }
}

// -- EmmcUtil -----------------------------------------------------------------

/// `EmmcUtil(key)`: what the MMC driver exports.
pub struct EmmcUtil {
    path: String,
    log: SysLogger,
    common: Common,
}

impl EmmcUtil {
    pub fn new(diskdev: &str) -> EmmcUtil {
        let base = diskdev.rsplit('/').next().unwrap_or(diskdev);
        EmmcUtil {
            path: io::join(BASE_PATH, base),
            log: SysLogger::new(Some("StorageCommon")),
            common: Common::new(diskdev),
        }
    }

    /// `_read_device_entry(entry)`: the file, right-stripped, or None when
    /// it will not open.  Only that: the `except OSError` there lets a file
    /// that will not decode raise.
    fn entry(&self, name: &str) -> PyResult<Option<String>> {
        match io::read_text(&io::join(&io::join(&self.path, "device"), name)) {
            Ok(s) => Ok(Some(s.trim_end().to_string())),
            Err(e) if e.exc.is_os_error() => Ok(None),
            Err(e) => Err(e),
        }
    }

    fn opt(v: Option<String>) -> PyVal {
        v.map_or(PyVal::None, PyVal::Str)
    }
}

/// `int(s, 0)`: a prefix picks the base; a decimal may not have leading zeros.
fn int_base0(s: &str) -> PyResult<i128> {
    crate::py::py_int_base(s, 0)
}

impl StorageDisk for EmmcUtil {
    fn fetch_parse_info(&mut self, _diskdev: &str) -> PyResult<()> {
        Ok(())
    }
    fn get_model(&self) -> PyResult<PyVal> {
        Ok(Self::opt(self.entry("name")?))
    }
    fn get_serial(&self) -> PyResult<PyVal> {
        Ok(Self::opt(self.entry("serial")?))
    }
    fn get_firmware(&self) -> PyResult<PyVal> {
        Ok(Self::opt(self.entry("fwrev")?))
    }
    fn get_health(&self) -> PyResult<PyVal> {
        let Some(data) = self.entry("life_time")? else {
            return Err(PyErr::not_implemented());
        };
        let slc = self
            .entry("enhanced_area_offset")?
            .is_some_and(|s| !s.is_empty());
        let value = int_base0(&word(&data, if slc { 0 } else { 1 })?)?;
        Ok(PyVal::Float((100 - 10 * (value - 1)) as f64))
    }
    fn get_temperature(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_disk_io_reads(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_disk_io_writes(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_reserved_blocks(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_fs_io_reads(&self) -> PyResult<PyVal> {
        Ok(self.common.fs_io(&self.log, true))
    }
    fn get_fs_io_writes(&self) -> PyResult<PyVal> {
        Ok(self.common.fs_io(&self.log, false))
    }
}

// -- UsbUtil, over blkinfo -----------------------------------------------------

const DISK_FILTERS: [&str; 19] = [
    "name",
    "kname",
    "fstype",
    "label",
    "mountpoint",
    "size",
    "maj:min",
    "rm",
    "model",
    "vendor",
    "serial",
    "hctl",
    "tran",
    "rota",
    "type",
    "ro",
    "owner",
    "group",
    "mode",
];

/// `bytes.decode("unicode_escape")`, or None where Python raises
/// UnicodeDecodeError: a truncated `\x`, `\u` or `\U`, a code point past
/// U+10FFFF, a trailing backslash.  Bytes outside an escape are Latin-1; an
/// unknown escape is kept as written.  `\N{name}` needs Unicode's name table
/// and is refused (lsblk only ever writes `\xHH`); a lone surrogate becomes
/// U+FFFD, which a Rust string can hold.
fn unicode_escape(b: &[u8]) -> Option<String> {
    let mut out = String::new();
    let mut i = 0;
    let hex = |s: &[u8]| -> Option<u32> {
        if s.iter().all(u8::is_ascii_hexdigit) {
            u32::from_str_radix(std::str::from_utf8(s).ok()?, 16).ok()
        } else {
            None
        }
    };
    while i < b.len() {
        if b[i] != b'\\' {
            out.push(char::from(b[i]));
            i += 1;
            continue;
        }
        let e = *b.get(i + 1)?;
        i += 2;
        let simple = match e {
            b'\n' => Some('\n'),
            b'\\' => Some('\\'),
            b'\'' => Some('\''),
            b'"' => Some('"'),
            b'a' => Some('\x07'),
            b'b' => Some('\x08'),
            b'f' => Some('\x0c'),
            b'n' => Some('\n'),
            b'r' => Some('\r'),
            b't' => Some('\t'),
            b'v' => Some('\x0b'),
            _ => None,
        };
        if let Some(c) = simple {
            // A backslash before a line break joins the lines.
            if e != b'\n' {
                out.push(c);
            }
            continue;
        }
        match e {
            b'0'..=b'7' => {
                let mut v = u32::from(e - b'0');
                for _ in 0..2 {
                    match b.get(i) {
                        Some(d @ b'0'..=b'7') => {
                            v = v * 8 + u32::from(d - b'0');
                            i += 1;
                        }
                        _ => break,
                    }
                }
                out.push(char::from_u32(v)?);
            }
            b'x' | b'u' | b'U' => {
                let n = match e {
                    b'x' => 2,
                    b'u' => 4,
                    _ => 8,
                };
                let v = hex(b.get(i..i + n)?)?;
                i += n;
                if v > 0x10ffff {
                    return None;
                }
                out.push(char::from_u32(v).unwrap_or('\u{fffd}'));
            }
            b'N' => return None,
            _ => {
                out.push('\\');
                i -= 1;
            }
        }
    }
    Some(out)
}

/// One disk of blkinfo's tree.
struct BlkDisk {
    fields: HashMap<&'static str, String>,
    children: usize,
    parents: Vec<String>,
}

/// `subprocess.check_output(argv)`.
fn check_output(argv: &[&str]) -> PyResult<Vec<u8>> {
    let out = command(argv[0])
        .args(&argv[1..])
        .stderr(Stdio::inherit())
        .output()
        .map_err(|e| PyErr::from_io(&e, Some(argv[0])))?;
    if !out.status.success() {
        // `subprocess`'s own words, a signal included: "died with
        // <Signals.SIGKILL: 9>." rather than a made-up exit status.
        return Err(crate::subprocess::called_process_error(
            argv,
            crate::subprocess::returncode(out.status),
        ));
    }
    Ok(out.stdout)
}

/// `LsBlkWrapper._build_disk_tree()`: the disks lsblk lists, then their
/// hierarchy from its tree view.
fn build_disk_tree() -> PyResult<Vec<(String, BlkDisk)>> {
    let cols = DISK_FILTERS.join(",").to_uppercase();
    let listing = match check_output(&["lsblk", "-a", "-n", "-r", "-b", "-o", &cols]) {
        Ok(o) => o,
        Err(e) if e.exc.name() == "CalledProcessError" => return Ok(Vec::new()),
        Err(e) => return Err(e),
    };
    let mut tree: Vec<(String, BlkDisk)> = Vec::new();
    let lines: Vec<&[u8]> = listing.split(|c| *c == b'\n').collect();
    for di in &lines[..lines.len().saturating_sub(1)] {
        // A field Python cannot decode is a ValueError, which empties the tree.
        let Some(params) = di
            .split(|c| *c == b' ')
            .map(|p| unicode_escape(p).map(|s| crate::py::strip(&s).to_string()))
            .collect::<Option<Vec<String>>>()
        else {
            return Ok(Vec::new());
        };
        let dn = params.first().cloned().unwrap_or_default();
        let fields: HashMap<&'static str, String> =
            DISK_FILTERS.iter().copied().zip(params).collect();
        let d = BlkDisk {
            fields,
            children: 0,
            parents: Vec::new(),
        };
        match tree.iter_mut().find(|(n, _)| *n == dn) {
            Some(e) => e.1 = d,
            None => tree.push((dn, d)),
        }
    }
    let hierarchy = check_output(&["lsblk", "-a", "-n", "-i", "-o", "NAME"])?;
    let hierarchy = crate::py::codec::decode(crate::py::codec::Codec::Utf8, &hierarchy)?;
    let mut stack: Vec<(String, usize)> = Vec::new();
    for line in hierarchy.split('\n') {
        let level = line
            .chars()
            .take_while(|c| ['`', '|', '-', ' '].contains(c))
            .count();
        let name: String = line.chars().skip(level).collect();
        while let Some(p) = stack.pop() {
            if p.1 < level {
                let missing = |n: &str| PyErr::key_error(n);
                let pi = tree
                    .iter()
                    .position(|(n, _)| *n == p.0)
                    .ok_or_else(|| missing(&p.0))?;
                let ci = tree
                    .iter()
                    .position(|(n, _)| *n == name)
                    .ok_or_else(|| missing(&name))?;
                tree[pi].1.children += 1;
                tree[ci].1.parents.push(p.0.clone());
                stack.push(p);
                break;
            }
        }
        stack.push((name, level));
    }
    Ok(tree)
}

/// `_add_iscsi_info()`: what it reads is never used, so only how it fails
/// matters -- an iSCSI disk's /sys/block link, its host and session in that
/// link, and a connection under the session.
fn add_iscsi_info(tree: &[(String, BlkDisk)]) -> PyResult<()> {
    for (_, d) in tree {
        let get = |k: &str| d.fields.get(k).cloned().unwrap_or_default();
        if get("type") != "disk" || get("tran") != "iscsi" {
            continue;
        }
        let link = io::readlink(&format!("/sys/block/{}", get("name")))?;
        let parts: Vec<&str> = link.split('/').collect();
        let (Some(host), Some(session)) = (parts.get(3), parts.get(4)) else {
            return Err(PyErr::index_error("list index out of range"));
        };
        // `glob(...connection*)[0]`
        let dir = format!("/sys/devices/platform/{host}/{session}");
        if !io::listdir(&dir)
            .unwrap_or_default()
            .iter()
            .any(|n| n.starts_with("connection"))
        {
            return Err(PyErr::index_error("list index out of range"));
        }
    }
    Ok(())
}

/// `BlkDiskInfo().get_disks({'name': name})[0]`: model (vendor and model
/// merged, as blkinfo merges them), serial and vendor of the one disk.
fn blk_disk(name: &str) -> PyResult<(String, String, String)> {
    // `LsBlkWrapper()`: an OSError anywhere in building the tree -- either
    // lsblk run -- is lsblk missing.
    let tree = match build_disk_tree() {
        Err(e) if e.exc.is_os_error() => {
            return Err(PyErr::other(
                "NoLsblkFound",
                "lsblk command-line tool from util-linux package is not found.",
            ))
        }
        r => r?,
    };
    add_iscsi_info(&tree)?;
    // `_add_disk_stats()`: what it adds is never read here, but the file has
    // to open.
    io::read_text("/proc/diskstats")?;
    let get = |d: &BlkDisk, k: &str| d.fields.get(k).cloned().unwrap_or_default();
    let mut blacklist: Vec<String> = Vec::new();
    for (_, d) in &tree {
        let t = get(d, "type");
        if t == "mpath" {
            blacklist.extend(d.parents.iter().cloned());
        } else if t.starts_with("raid") {
            let only_child = d.parents.iter().all(|p| {
                tree.iter()
                    .find(|(n, _)| n == p)
                    .is_some_and(|(_, pd)| pd.children == 1)
            });
            if only_child {
                blacklist.extend(d.parents.iter().cloned());
            }
        }
    }
    let want = io::join(BASE_PATH, name);
    let mut seen: Vec<String> = Vec::new();
    for (dn, d) in &tree {
        let t = get(d, "type");
        if (!["disk", "rom", "mpath"].contains(&t.as_str()) && !t.starts_with("raid"))
            || blacklist.contains(dn)
        {
            continue;
        }
        let dname = get(d, "name");
        if t.starts_with("raid") || t == "mpath" {
            if seen.contains(&dname) {
                continue;
            }
            seen.push(dname.clone());
        }
        if io::join(BASE_PATH, &dname) != want || !io::exists(&want) {
            continue;
        }
        let model = format!("{} {}", get(d, "vendor").trim(), get(d, "model").trim());
        return Ok((model.clone(), get(d, "serial"), model));
    }
    Err(PyErr::index_error("list index out of range"))
}

/// `UsbUtil(diskdev)`.
pub struct UsbUtil {
    diskdev: String,
    log: SysLogger,
    common: Common,
    model: PyVal,
    serial: PyVal,
}

impl UsbUtil {
    pub fn new(diskdev: &str) -> PyResult<UsbUtil> {
        let mut u = UsbUtil {
            diskdev: diskdev.to_string(),
            log: SysLogger::new(Some("StorageCommon")),
            common: Common::new(diskdev),
            model: na(),
            serial: na(),
        };
        u.fetch()?;
        Ok(u)
    }

    fn fetch(&mut self) -> PyResult<()> {
        let base = self
            .diskdev
            .rsplit('/')
            .next()
            .unwrap_or(&self.diskdev)
            .to_string();
        let (model, serial, _vendor) = blk_disk(&base)?;
        self.model = PyVal::Str(model);
        self.serial = PyVal::Str(serial);
        Ok(())
    }
}

impl StorageDisk for UsbUtil {
    fn fetch_parse_info(&mut self, _diskdev: &str) -> PyResult<()> {
        self.fetch()
    }
    fn get_model(&self) -> PyResult<PyVal> {
        Ok(self.model.clone())
    }
    fn get_serial(&self) -> PyResult<PyVal> {
        Ok(self.serial.clone())
    }
    fn get_firmware(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_health(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_temperature(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_disk_io_reads(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_disk_io_writes(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_reserved_blocks(&self) -> PyResult<PyVal> {
        Ok(na())
    }
    fn get_fs_io_reads(&self) -> PyResult<PyVal> {
        Ok(self.common.fs_io(&self.log, true))
    }
    fn get_fs_io_writes(&self) -> PyResult<PyVal> {
        Ok(self.common.fs_io(&self.log, false))
    }
}

// -- StorageDevices -------------------------------------------------------------

/// `StorageDevices()`: every disk under /sys/block but boot partitions and
/// loop devices, each with its utility object or None.
pub struct StorageDevices {
    pub devices: Vec<(String, Option<Box<dyn StorageDisk>>)>,
}

impl StorageDevices {
    pub fn new() -> PyResult<StorageDevices> {
        let log = SysLogger::new(Some("StorageDevices"));
        let mut devices = Vec::new();
        for fd in io::listdir(BASE_PATH)? {
            if fd.contains("boot") || fd.contains("loop") {
                continue;
            }
            let obj = factory(&log, &fd);
            match devices
                .iter_mut()
                .find(|(n, _): &&mut (String, Option<Box<dyn StorageDisk>>)| *n == fd)
            {
                Some(e) => e.1 = obj,
                None => devices.push((fd, obj)),
            }
        }
        Ok(StorageDevices { devices })
    }
}

/// `_storage_device_object_factory(key)`.
fn factory(log: &SysLogger, key: &str) -> Option<Box<dyn StorageDisk>> {
    let blkdev = io::join(BLKDEV_BASE_PATH, key);
    let diskdev = io::join(BASE_PATH, key);
    let warn = |what: &str, e: &PyErr| {
        let msg = format!("Failed to instantiate {what} object. Error: {}", e.str());
        log.log_warning(&msg);
        print(&msg);
    };
    if key.starts_with("sd") || key.starts_with("nvme") {
        let real = io::realpath(&io::join(&diskdev, "device"));
        if real.contains("ata") || real.contains("nvme") {
            match SsdUtil::new(&blkdev) {
                Ok(s) => return Some(Box::new(s)),
                Err(e) => warn("SsdUtil", &e),
            }
        } else if real.contains("usb") {
            match UsbUtil::new(&blkdev) {
                Ok(u) => return Some(Box::new(u)),
                Err(e) => warn("UsbUtil", &e),
            }
        }
    } else if key.contains("mmcblk") {
        return Some(Box::new(EmmcUtil::new(key)));
    }
    None
}

/// `int(x)` on a reading, as the hatch's `_count` takes it.
pub fn int_of(v: &PyVal) -> PyResult<i128> {
    match v {
        PyVal::Int(i) => Ok(*i),
        PyVal::Bool(b) => Ok(i128::from(*b)),
        PyVal::Float(f) => int_of_float(*f),
        PyVal::Str(s) => py_int(s),
        other => Err(PyErr::type_error(format!(
            "int() argument must be a string, a bytes-like object or a real number, not '{}'",
            other.type_name()
        ))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::testing::Root;
    use std::os::unix::fs::symlink;

    /// A scratch root, with the tools run from a directory of shell scripts
    /// and psutil's wrap state forgotten.
    struct Bench {
        root: Root,
        tools: PathBuf,
    }

    impl Bench {
        fn new() -> Bench {
            let root = Root::new();
            let tools = root.dir.join("tools");
            std::fs::create_dir_all(&tools).expect("tools");
            set_tool_dir(Some(tools.clone()));
            *WRAP.lock().unwrap_or_else(|e| e.into_inner()) = None;
            Bench { root, tools }
        }

        /// The tool `name` runs `script`.
        fn tool(&self, name: &str, script: &str) {
            std::fs::write(self.tools.join(name), script).expect("tool");
        }

        /// The tool `name` prints `output`, whatever it is asked.
        fn prints(&self, name: &str, output: &str) {
            let out = self.tools.join(format!("{name}.out"));
            std::fs::write(&out, output).expect("output");
            self.tool(name, &format!("cat '{}'\n", out.display()));
        }

        /// smartctl answers each disk with its own output.
        fn smartctl(&self, outputs: &[(&str, &str)]) {
            for (disk, out) in outputs {
                std::fs::write(self.tools.join(format!("smartctl.{disk}")), out).expect("output");
            }
            self.tool("smartctl", "f=\"$(dirname \"$0\")/smartctl.$(basename \"$1\")\"\n[ -f \"$f\" ] && cat \"$f\"\nexit 0\n");
        }

        /// lsblk lists `raw` (its `-r` view) over the hierarchy `tree`.
        fn lsblk(&self, raw: &str, tree: &str) {
            std::fs::write(self.tools.join("lsblk.raw"), raw).expect("output");
            std::fs::write(self.tools.join("lsblk.tree"), tree).expect("output");
            self.tool(
                "lsblk",
                "d=$(dirname \"$0\")\ncase \" $* \" in *\" -r \"*) cat \"$d/lsblk.raw\" ;; *) cat \"$d/lsblk.tree\" ;; esac\n",
            );
        }

        /// /sys/block/<name>, its `device` a link to `device` when given.
        fn disk(&self, name: &str, device: Option<&str>) {
            let dir = self.root.real(&format!("{BASE_PATH}/{name}"));
            std::fs::create_dir_all(&dir).expect("disk");
            if let Some(d) = device {
                symlink(d, dir.join("device")).expect("link");
            }
        }
    }

    impl Drop for Bench {
        fn drop(&mut self) {
            set_tool_dir(None);
        }
    }

    fn reading(d: &dyn StorageDisk) -> String {
        let r = (|| -> PyResult<PyVal> {
            Ok(PyVal::List(vec![
                d.get_model()?,
                d.get_serial()?,
                d.get_firmware()?,
                d.get_health()?,
                d.get_temperature()?,
                d.get_disk_io_reads()?,
                d.get_disk_io_writes()?,
                d.get_reserved_blocks()?,
            ]))
        })();
        match r {
            Ok(v) => v.py_repr(),
            Err(e) => format!("raise {}: {}", e.exc.name(), e.str()),
        }
    }

    fn ssd_reading(dev: &str) -> String {
        match SsdUtil::new(dev) {
            Ok(s) => reading(&s),
            Err(e) => format!("raise {}: {}", e.exc.name(), e.str()),
        }
    }

    /// An `SsdUtil` as Python's tests make one by patching the class: no
    /// fetch, every reading N/A.
    fn blank(dev: &str) -> SsdUtil {
        SsdUtil {
            dev: dev.to_string(),
            log: SysLogger::new(Some("SsdUtil")),
            common: None,
            model: na(),
            serial: na(),
            firmware: na(),
            temperature: na(),
            health: na(),
            ssd_info: NOT_AVAILABLE.into(),
            vendor_ssd_info: NOT_AVAILABLE.into(),
            disk_io_reads: na(),
            disk_io_writes: na(),
            reserved_blocks: na(),
        }
    }

    /// A canned tool output by name: those of Python's own tests
    /// (tests/test_ssd.py), and `fx_*` from the sandbox's fixture.
    fn data(name: &str) -> &'static str {
        match name {
            "Innodisk_missing_names_ssd" => {
                include_str!("../tests/data/storage/Innodisk_missing_names_ssd.txt")
            }
            "Innodisk_ssd" => include_str!("../tests/data/storage/Innodisk_ssd.txt"),
            "Innodisk_vendor_info" => {
                include_str!("../tests/data/storage/Innodisk_vendor_info.txt")
            }
            "atp_nvme_ssd" => include_str!("../tests/data/storage/atp_nvme_ssd.txt"),
            "atp_ssd" => include_str!("../tests/data/storage/atp_ssd.txt"),
            "fx_atp" => include_str!("../tests/data/storage/fx_atp.txt"),
            "fx_broken_nvme" => include_str!("../tests/data/storage/fx_broken_nvme.txt"),
            "fx_broken_temp" => include_str!("../tests/data/storage/fx_broken_temp.txt"),
            "fx_generic_named" => include_str!("../tests/data/storage/fx_generic_named.txt"),
            "fx_innodisk" => include_str!("../tests/data/storage/fx_innodisk.txt"),
            "fx_intel" => include_str!("../tests/data/storage/fx_intel.txt"),
            "fx_ismart" => include_str!("../tests/data/storage/fx_ismart.txt"),
            "fx_ismart_ids" => include_str!("../tests/data/storage/fx_ismart_ids.txt"),
            "fx_m2" => include_str!("../tests/data/storage/fx_m2.txt"),
            "fx_micron5300" => include_str!("../tests/data/storage/fx_micron5300.txt"),
            "fx_micron_counts" => include_str!("../tests/data/storage/fx_micron_counts.txt"),
            "fx_micron_remain" => include_str!("../tests/data/storage/fx_micron_remain.txt"),
            "fx_micron_used" => include_str!("../tests/data/storage/fx_micron_used.txt"),
            "fx_smartcmd" => include_str!("../tests/data/storage/fx_smartcmd.txt"),
            "fx_smartcmd_remaining" => {
                include_str!("../tests/data/storage/fx_smartcmd_remaining.txt")
            }
            "fx_smartcmd_zero_nand" => {
                include_str!("../tests/data/storage/fx_smartcmd_zero_nand.txt")
            }
            "fx_storfly" => include_str!("../tests/data/storage/fx_storfly.txt"),
            "fx_swissbit" => include_str!("../tests/data/storage/fx_swissbit.txt"),
            "fx_transcend" => include_str!("../tests/data/storage/fx_transcend.txt"),
            "fx_unknown" => include_str!("../tests/data/storage/fx_unknown.txt"),
            "fx_virtium_nvme" => include_str!("../tests/data/storage/fx_virtium_nvme.txt"),
            "intel_ssd" => include_str!("../tests/data/storage/intel_ssd.txt"),
            "lack_info_ssd" => include_str!("../tests/data/storage/lack_info_ssd.txt"),
            "micron_ssd" => include_str!("../tests/data/storage/micron_ssd.txt"),
            "nvme_ssd" => include_str!("../tests/data/storage/nvme_ssd.txt"),
            "smartcmd_vitrium_error" => {
                include_str!("../tests/data/storage/smartcmd_vitrium_error.txt")
            }
            "ssd" => include_str!("../tests/data/storage/ssd.txt"),
            "ssd2" => include_str!("../tests/data/storage/ssd2.txt"),
            "ssd_leading_trailing_spaces" => {
                include_str!("../tests/data/storage/ssd_leading_trailing_spaces.txt")
            }
            "swissbit_vendor" => include_str!("../tests/data/storage/swissbit_vendor.txt"),
            "transcend_vendor" => include_str!("../tests/data/storage/transcend_vendor.txt"),
            "virtium_generic" => include_str!("../tests/data/storage/virtium_generic.txt"),
            "virtium_generic_trick_number" => {
                include_str!("../tests/data/storage/virtium_generic_trick_number.txt")
            }
            "virtium_generic_vsfdm8xc240g_v11_t" => {
                include_str!("../tests/data/storage/virtium_generic_vsfdm8xc240g_v11_t.txt")
            }
            "virtium_generic_vtsm24abxi160_bm110006" => {
                include_str!("../tests/data/storage/virtium_generic_vtsm24abxi160_bm110006.txt")
            }
            "virtium_invalid_nand_endurance" => {
                include_str!("../tests/data/storage/virtium_invalid_nand_endurance.txt")
            }
            "virtium_invalid_remain_life" => {
                include_str!("../tests/data/storage/virtium_invalid_remain_life.txt")
            }
            "virtium_no_remain_life" => {
                include_str!("../tests/data/storage/virtium_no_remain_life.txt")
            }
            "virtium_vendor" => include_str!("../tests/data/storage/virtium_vendor.txt"),
            "virtium_vendor_trick_number" => {
                include_str!("../tests/data/storage/virtium_vendor_trick_number.txt")
            }
            "virtium_vendor_vsfdm8xc240g_v11_t" => {
                include_str!("../tests/data/storage/virtium_vendor_vsfdm8xc240g_v11_t.txt")
            }
            "virtium_vendor_vtsm24abxi160_bm110006" => {
                include_str!("../tests/data/storage/virtium_vendor_vtsm24abxi160_bm110006.txt")
            }
            "vitrium_nvme_generic" => {
                include_str!("../tests/data/storage/vitrium_nvme_generic.txt")
            }
            _ => panic!("no canned output {name}"),
        }
    }

    /// `(device, smartctl, iSmart, SmartCmd, what Python's SsdUtil reads)`,
    /// a tool being a canned output, "" for no output, None for not there.
    #[allow(clippy::type_complexity)]
    const SSD_CASES: &[(&str, Option<&str>, Option<&str>, Option<&str>, &str)] = &[
        (
            "/dev/sda",
            Some("Innodisk_missing_names_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['M.2 (S42) 3ME4', 'YCA12003110020080', 'L17606', '94', '30', '42566', '14452', '72']"#,
        ),
        (
            "/dev/sda",
            Some("Innodisk_missing_names_ssd"),
            None,
            None,
            r#"['M.2 (S42) 3ME4', 'YCA12003110020080', 'L17606', '94', 'N/A', '42566', '14452', '72']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("Innodisk_missing_names_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'YCA12003110020080', 'L17606', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("Innodisk_missing_names_ssd"),
            None,
            None,
            r#"['N/A', 'YCA12003110020080', 'L17606', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("Innodisk_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['InnoDisk Corp. - mSATA 3IE3', 'BCA11802090990501', 'S16425cG', '92', '30', '73954', '150370', '59']"#,
        ),
        (
            "/dev/sda",
            Some("Innodisk_ssd"),
            None,
            None,
            r#"['InnoDisk Corp. - mSATA 3IE3', 'BCA11802090990501', 'S16425cG', '92', '30', '73954', '150370', '59']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("Innodisk_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'BCA11802090990501', 'S16425cG', 'N/A', 0.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("Innodisk_ssd"),
            None,
            None,
            r#"['N/A', 'BCA11802090990501', 'S16425cG', 'N/A', 0.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("Innodisk_vendor_info"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'BCA11802090990501', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("Innodisk_vendor_info"),
            None,
            None,
            r#"['N/A', 'BCA11802090990501', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("Innodisk_vendor_info"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '30]'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("Innodisk_vendor_info"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '30]'"#,
        ),
        (
            "/dev/sda",
            Some("atp_nvme_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', '23090214-000325', '42A4SB6G', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("atp_nvme_ssd"),
            None,
            None,
            r#"['N/A', '23090214-000325', '42A4SB6G', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("atp_nvme_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['ATP AF240GSTJA-AW1', '23090214-000325', '42A4SB6G', 94.0, 47.0, '44,586,180 [22.8 TB]', '18,202,849 [9.31 TB]', 100.0]"#,
        ),
        (
            "/dev/nvme0n1",
            Some("atp_nvme_ssd"),
            None,
            None,
            r#"['ATP AF240GSTJA-AW1', '23090214-000325', '42A4SB6G', 94.0, 47.0, '44,586,180 [22.8 TB]', '18,202,849 [9.31 TB]', 100.0]"#,
        ),
        (
            "/dev/sda",
            Some("atp_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['ATP AF32GSAIA-AW1', '22110247-000144', 'V1ST0100', '98', '33', '75560121447', '77937125888', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("atp_ssd"),
            None,
            None,
            r#"['ATP AF32GSAIA-AW1', '22110247-000144', 'V1ST0100', '98', '33', '75560121447', '77937125888', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("atp_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("atp_ssd"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/sda",
            Some("fx_atp"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['ATP I-Temp mSATA', 'SN123456', 'FW1.0', '88', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_atp"),
            None,
            None,
            r#"['ATP I-Temp mSATA', 'SN123456', 'FW1.0', '88', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_atp"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_atp"),
            None,
            None,
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_broken_nvme"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_broken_nvme"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_broken_nvme"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: 'n/a'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_broken_nvme"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: 'n/a'"#,
        ),
        (
            "/dev/sda",
            Some("fx_broken_temp"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['InnoDisk Corp. - mSATA 3ME', 'SN123456', 'FW1.0', '92.725', 'x', '73954', '150370', '0']"#,
        ),
        (
            "/dev/sda",
            Some("fx_broken_temp"),
            None,
            None,
            r#"['InnoDisk Corp. - mSATA 3ME', 'SN123456', 'FW1.0', 'N/A', 'x', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_broken_temp"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_broken_temp"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/sda",
            Some("fx_generic_named"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Generic SSD 32G', 'SN123456', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/sda",
            Some("fx_generic_named"),
            None,
            None,
            r#"['Generic SSD 32G', 'SN123456', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_generic_named"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_generic_named"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("fx_innodisk"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['InnoDisk Corp. - mSATA 3ME', 'BCA11712190600251', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/sda",
            Some("fx_innodisk"),
            None,
            None,
            r#"['InnoDisk Corp. - mSATA 3ME', 'BCA11712190600251', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_innodisk"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_innodisk"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("fx_intel"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['INTEL SSDSC2KB480G8', 'SN123456', 'FW1.0', '3.0', '29', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_intel"),
            None,
            None,
            r#"['INTEL SSDSC2KB480G8', 'SN123456', 'FW1.0', '3.0', '29', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_intel"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_intel"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/sda",
            Some("fx_ismart"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'BCA11712190600251', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_ismart"),
            None,
            None,
            r#"['N/A', 'BCA11712190600251', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_ismart"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'BCA11712190600251', 'N/A', 'N/A', 36.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_ismart"),
            None,
            None,
            r#"['N/A', 'BCA11712190600251', 'N/A', 'N/A', 36.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_ismart_ids"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_ismart_ids"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_ismart_ids"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 0.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_ismart_ids"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 0.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_m2"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['M.2 (S80) 3TE6', 'SN123456', 'FW1.0', '92.725', '35', '73954', '150370', '0']"#,
        ),
        (
            "/dev/sda",
            Some("fx_m2"),
            None,
            None,
            r#"['M.2 (S80) 3TE6', 'SN123456', 'FW1.0', 'N/A', '35', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_m2"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_m2"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/sda",
            Some("fx_micron5300"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Micron_5300_MTFDDAK480TDS', 'SN123456', 'FW1.0', 'N/A', '33', 'N/A', 'N/A', '100']"#,
        ),
        (
            "/dev/sda",
            Some("fx_micron5300"),
            None,
            None,
            r#"['Micron_5300_MTFDDAK480TDS', 'SN123456', 'FW1.0', 'N/A', '33', 'N/A', 'N/A', '100']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_micron5300"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_micron5300"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("fx_micron_counts"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Micron_M600_MTFDDAK256MBF', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_micron_counts"),
            None,
            None,
            r#"['Micron_M600_MTFDDAK256MBF', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_micron_counts"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_micron_counts"),
            None,
            None,
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_micron_remain"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Micron_M600_MTFDDAK256MBF', 'SN123456', 'FW1.0', '93', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_micron_remain"),
            None,
            None,
            r#"['Micron_M600_MTFDDAK256MBF', 'SN123456', 'FW1.0', '93', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_micron_remain"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_micron_remain"),
            None,
            None,
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_micron_used"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Micron_M600_MTFDDAK256MBF', 'SN123456', 'FW1.0', '93', 'N/A', 'N/A', '42', '12']"#,
        ),
        (
            "/dev/sda",
            Some("fx_micron_used"),
            None,
            None,
            r#"['Micron_M600_MTFDDAK256MBF', 'SN123456', 'FW1.0', '93', 'N/A', 'N/A', '42', '12']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_micron_used"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_micron_used"),
            None,
            None,
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_smartcmd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/sda",
            Some("fx_smartcmd"),
            None,
            None,
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_smartcmd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 194.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_smartcmd"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 194.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_smartcmd_remaining"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_smartcmd_remaining"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_smartcmd_remaining"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_smartcmd_remaining"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_smartcmd_zero_nand"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_smartcmd_zero_nand"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_smartcmd_zero_nand"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_smartcmd_zero_nand"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_storfly"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['StorFly VSF302XC032G-MLX', 'SN123456', 'FW1.0', 87.78, '17', '0', '1111', '0']"#,
        ),
        (
            "/dev/sda",
            Some("fx_storfly"),
            None,
            None,
            r#"['StorFly VSF302XC032G-MLX', 'SN123456', 'FW1.0', '96', 'N/A', 'N/A', '1111', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_storfly"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_storfly"),
            None,
            None,
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_swissbit"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['SFSA032GU1AA1TO-I-OC-216-STD', 'SN123456', 'FW1.0', '99', '1', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_swissbit"),
            None,
            None,
            r#"['SFSA032GU1AA1TO-I-OC-216-STD', 'SN123456', 'FW1.0', '99', '1', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_swissbit"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 8.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_swissbit"),
            None,
            None,
            r#"['N/A', 'SN123456', 'FW1.0', 'N/A', 8.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_transcend"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['TS32GMTS400S', 'SN123456', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/sda",
            Some("fx_transcend"),
            None,
            None,
            r#"['TS32GMTS400S', 'SN123456', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_transcend"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_transcend"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("fx_unknown"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Acme Disk 32G', 'SN123456', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/sda",
            Some("fx_unknown"),
            None,
            None,
            r#"['Acme Disk 32G', 'SN123456', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_unknown"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_unknown"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("fx_virtium_nvme"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'X1', 'F1', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_virtium_nvme"),
            None,
            None,
            r#"['N/A', 'X1', 'F1', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_virtium_nvme"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Virtium VTPM24CEXI080-BM110006', 'X1', 'F1', 98.0, 44.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_virtium_nvme"),
            None,
            None,
            r#"['Virtium VTPM24CEXI080-BM110006', 'X1', 'F1', 98.0, 44.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("intel_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['INTEL SSDSCKKB240G8', 'BTYH12260KTW240J', 'XC311132', '100.0', '34', '18922', '44554', '0']"#,
        ),
        (
            "/dev/sda",
            Some("intel_ssd"),
            None,
            None,
            r#"['INTEL SSDSCKKB240G8', 'BTYH12260KTW240J', 'XC311132', '100.0', '34', '18922', '44554', '0']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("intel_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("intel_ssd"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("lack_info_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("lack_info_ssd"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("lack_info_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("lack_info_ssd"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("micron_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Micron_M550_MTFDDAT064MAY', 'MSA1827061P', 'MU01', '75', '32', 'N/A', '9607694422', '475']"#,
        ),
        (
            "/dev/sda",
            Some("micron_ssd"),
            None,
            None,
            r#"['Micron_M550_MTFDDAT064MAY', 'MSA1827061P', 'MU01', '75', '32', 'N/A', '9607694422', '475']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("micron_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("micron_ssd"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("nvme_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'A0221030722410000027', 'COT6OQ', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("nvme_ssd"),
            None,
            None,
            r#"['N/A', 'A0221030722410000027', 'COT6OQ', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("nvme_ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['SFPC020GM1EC2TO-I-5E-11P-STD', 'A0221030722410000027', 'COT6OQ', 100.0, 37.0, '1,546,369 [791 GB]', '7,118,163 [3.64 TB]', 100.0]"#,
        ),
        (
            "/dev/nvme0n1",
            Some("nvme_ssd"),
            None,
            None,
            r#"['SFPC020GM1EC2TO-I-5E-11P-STD', 'A0221030722410000027', 'COT6OQ', 100.0, 37.0, '1,546,369 [791 GB]', '7,118,163 [3.64 TB]', 100.0]"#,
        ),
        (
            "/dev/sda",
            Some("smartcmd_vitrium_error"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("smartcmd_vitrium_error"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("smartcmd_vitrium_error"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("smartcmd_vitrium_error"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['(S42) 3IE3', 'BCA11712280210689', 'S16425i', '95', '30', '760991', '178564', '146']"#,
        ),
        (
            "/dev/sda",
            Some("ssd"),
            None,
            None,
            r#"['(S42) 3IE3', 'BCA11712280210689', 'S16425i', '95', '30', '760991', '178564', '146']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("ssd"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'BCA11712280210689', 'S16425i', 'N/A', 0.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("ssd"),
            None,
            None,
            r#"['N/A', 'BCA11712280210689', 'S16425i', 'N/A', 0.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("ssd2"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['SATA SSD', 'SPG210902J8', 'FW1241', '0', '30', '37584067165', '196534949930', '29']"#,
        ),
        (
            "/dev/sda",
            Some("ssd2"),
            None,
            None,
            r#"['SATA SSD', 'SPG210902J8', 'FW1241', '0', '30', '37584067165', '196534949930', '29']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("ssd2"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("ssd2"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/sda",
            Some("ssd_leading_trailing_spaces"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', '760991', '178564', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("ssd_leading_trailing_spaces"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', '760991', '178564', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("ssd_leading_trailing_spaces"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("ssd_leading_trailing_spaces"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("swissbit_vendor"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['SFSA160GM2AK2TO-I-8C-22K-STD', '00006022750795000010', 'SBR15004', '100', '25', '2257141451', '1186450104', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("swissbit_vendor"),
            None,
            None,
            r#"['SFSA160GM2AK2TO-I-8C-22K-STD', '00006022750795000010', 'SBR15004', '100', '25', '2257141451', '1186450104', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("swissbit_vendor"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("swissbit_vendor"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("transcend_vendor"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['TS120GMTS420S', 'I074710927', 'R0522A0', '100', '33', '16734', '5068', '100']"#,
        ),
        (
            "/dev/sda",
            Some("transcend_vendor"),
            None,
            None,
            r#"['TS120GMTS420S', 'I074710927', 'R0522A0', '100', '33', '16734', '5068', '100']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("transcend_vendor"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("transcend_vendor"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['StorFly VSF302XC016G-MLX1', '52586-0705', '0202-001', 87.78, '17', '1482095', '629509', '100']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic"),
            None,
            None,
            r#"['StorFly VSF302XC016G-MLX1', '52586-0705', '0202-001', 'N/A', '19', '1482095', '629509', '100']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_generic"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_generic"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '-'"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic_trick_number"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', '42', 'N/A', '18782480803', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic_trick_number"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', '42', 'N/A', '18782480803', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_generic_trick_number"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_generic_trick_number"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic_vsfdm8xc240g_v11_t"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['VSFDM8XC240G-V11-T', '60237-0037', '0913-000', 'N/A', '17', '45606297', '302116658', '0']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic_vsfdm8xc240g_v11_t"),
            None,
            None,
            r#"['VSFDM8XC240G-V11-T', '60237-0037', '0913-000', '100', '34', '45606297', '302116658', '0']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_generic_vsfdm8xc240g_v11_t"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_generic_vsfdm8xc240g_v11_t"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic_vtsm24abxi160_bm110006"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Virtium VTSM24ABXI160-BM110006', '62996-0010', 'AB00A000', 'N/A', '17', '1411138737', '8770891932', '0']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic_vtsm24abxi160_bm110006"),
            None,
            None,
            r#"['Virtium VTSM24ABXI160-BM110006', '62996-0010', 'AB00A000', '100', '50', '1411138737', '8770891932', '0']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_generic_vtsm24abxi160_bm110006"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_generic_vtsm24abxi160_bm110006"),
            None,
            None,
            r#"raise ValueError: could not convert string to float: '(Min/Max'"#,
        ),
        (
            "/dev/sda",
            Some("virtium_invalid_nand_endurance"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_invalid_nand_endurance"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_invalid_nand_endurance"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_invalid_nand_endurance"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_invalid_remain_life"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_invalid_remain_life"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_invalid_remain_life"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_invalid_remain_life"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_no_remain_life"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/sda",
            Some("virtium_no_remain_life"),
            None,
            None,
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_no_remain_life"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 100.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_no_remain_life"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 100.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_vendor"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/sda",
            Some("virtium_vendor"),
            None,
            None,
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_vendor"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 100.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_vendor"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 100.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_vendor_trick_number"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/sda",
            Some("virtium_vendor_trick_number"),
            None,
            None,
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_vendor_trick_number"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 100.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_vendor_trick_number"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 100.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_vendor_vsfdm8xc240g_v11_t"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/sda",
            Some("virtium_vendor_vsfdm8xc240g_v11_t"),
            None,
            None,
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_vendor_vsfdm8xc240g_v11_t"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 48.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_vendor_vsfdm8xc240g_v11_t"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 48.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_vendor_vtsm24abxi160_bm110006"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/sda",
            Some("virtium_vendor_vtsm24abxi160_bm110006"),
            None,
            None,
            r#"raise IndexError: list index out of range"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_vendor_vtsm24abxi160_bm110006"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', 36.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("virtium_vendor_vtsm24abxi160_bm110006"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 36.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("vitrium_nvme_generic"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['N/A', '64008-0094', 'CE00A400', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("vitrium_nvme_generic"),
            None,
            None,
            r#"['N/A', '64008-0094', 'CE00A400', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("vitrium_nvme_generic"),
            Some("Innodisk_vendor_info"),
            Some("virtium_vendor"),
            r#"['Virtium VTPM24CEXI080-BM110006', '64008-0094', 'CE00A400', 100.0, 53.0, '253,310 [129 GB]', '598,492 [306 GB]', 100.0]"#,
        ),
        (
            "/dev/nvme0n1",
            Some("vitrium_nvme_generic"),
            None,
            None,
            r#"['Virtium VTPM24CEXI080-BM110006', '64008-0094', 'CE00A400', 100.0, 53.0, '253,310 [129 GB]', '598,492 [306 GB]', 100.0]"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic_vsfdm8xc240g_v11_t"),
            None,
            Some("virtium_vendor_vsfdm8xc240g_v11_t"),
            r#"['VSFDM8XC240G-V11-T', '60237-0037', '0913-000', 98.0, '34', '45606297', '302116658', '0']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic_vtsm24abxi160_bm110006"),
            None,
            Some("virtium_vendor_vtsm24abxi160_bm110006"),
            r#"['Virtium VTSM24ABXI160-BM110006', '62996-0010', 'AB00A000', 100.0, '50', '1411138737', '8770891932', '0']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic"),
            None,
            Some("virtium_no_remain_life"),
            r#"['StorFly VSF302XC016G-MLX1', '52586-0705', '0202-001', 99.42, '35', '1482095', '629509', '100']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic"),
            None,
            Some("virtium_invalid_nand_endurance"),
            r#"['StorFly VSF302XC016G-MLX1', '52586-0705', '0202-001', 'N/A', '19', '1482095', '629509', '100']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic"),
            None,
            Some("virtium_invalid_remain_life"),
            r#"['StorFly VSF302XC016G-MLX1', '52586-0705', '0202-001', 'N/A', '19', '1482095', '629509', '100']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic"),
            None,
            Some(""),
            r#"['StorFly VSF302XC016G-MLX1', '52586-0705', '0202-001', 'N/A', '19', '1482095', '629509', '100']"#,
        ),
        (
            "/dev/sda",
            Some("virtium_generic_trick_number"),
            None,
            Some("virtium_vendor_trick_number"),
            r#"['N/A', 'N/A', 'N/A', 'N/A', '42', 'N/A', '18782480803', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some("vitrium_nvme_generic"),
            None,
            Some("smartcmd_vitrium_error"),
            r#"['Virtium VTPM24CEXI080-BM110006', '64008-0094', 'CE00A400', 100.0, 53.0, '253,310 [129 GB]', '598,492 [306 GB]', 100.0]"#,
        ),
        (
            "/dev/nvme0n1",
            Some("fx_virtium_nvme"),
            None,
            Some("fx_smartcmd"),
            r#"['Virtium VTPM24CEXI080-BM110006', 'X1', 'F1', 98.0, 44.0, 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_storfly"),
            None,
            Some("fx_smartcmd"),
            r#"['StorFly VSF302XC032G-MLX', 'SN123456', 'FW1.0', 95.0, '37', '999', '1111', '12']"#,
        ),
        (
            "/dev/sda",
            Some("fx_storfly"),
            None,
            Some("fx_smartcmd_zero_nand"),
            r#"['StorFly VSF302XC032G-MLX', 'SN123456', 'FW1.0', '96', 'N/A', 'N/A', '1111', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_storfly"),
            None,
            Some("fx_smartcmd_remaining"),
            r#"['StorFly VSF302XC032G-MLX', 'SN123456', 'FW1.0', 93.0, 'N/A', 'N/A', '1111', 'N/A']"#,
        ),
        (
            "/dev/sda",
            Some("fx_innodisk"),
            Some("fx_ismart"),
            None,
            r#"['InnoDisk Corp. - mSATA 3ME', 'BCA11712190600251', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/sda",
            Some("fx_innodisk"),
            Some("fx_ismart_ids"),
            None,
            r#"['InnoDisk Corp. - mSATA 3ME', 'BCA11712190600251', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/sda",
            Some("fx_innodisk"),
            Some(""),
            None,
            r#"['InnoDisk Corp. - mSATA 3ME', 'BCA11712190600251', 'FW1.0', '97', '38', '654321', '123456', '100']"#,
        ),
        (
            "/dev/sda",
            Some("fx_m2"),
            Some("fx_ismart"),
            None,
            r#"['M.2 (S80) 3TE6', 'SN123456', 'FW1.0', '98.2', '35', '12345', '54321', '77']"#,
        ),
        (
            "/dev/sda",
            Some("fx_m2"),
            Some("fx_ismart_ids"),
            None,
            r#"['M.2 (S80) 3TE6', 'SN123456', 'FW1.0', '98', '35', '12345', '54321', '77']"#,
        ),
        (
            "/dev/sda",
            Some("Innodisk_missing_names_ssd"),
            Some("Innodisk_vendor_info"),
            None,
            r#"['M.2 (S42) 3ME4', 'YCA12003110020080', 'L17606', '94', '30', '42566', '14452', '72']"#,
        ),
        (
            "/dev/sda",
            Some("Innodisk_missing_names_ssd"),
            Some(""),
            None,
            r#"['M.2 (S42) 3ME4', 'YCA12003110020080', 'L17606', '94', 'N/A', '42566', '14452', '72']"#,
        ),
        (
            "/dev/sda",
            Some("lack_info_ssd"),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/sda",
            None,
            None,
            None,
            r#"raise FileNotFoundError: [Errno 2] No such file or directory: 'smartctl'"#,
        ),
        (
            "/dev/sda",
            Some(""),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
        (
            "/dev/nvme0n1",
            Some(""),
            None,
            None,
            r#"['N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"#,
        ),
    ];

    #[test]
    fn ssd_readings_are_python_s_for_every_canned_output() {
        let mut bad = Vec::new();
        for &(dev, smartctl, ismart, smartcmd, want) in SSD_CASES {
            let b = Bench::new();
            for (tool, out) in [
                ("smartctl", smartctl),
                ("iSmart", ismart),
                ("SmartCmd", smartcmd),
            ] {
                match out {
                    Some("") => b.tool(tool, "true\n"),
                    Some(n) => b.prints(tool, data(n)),
                    None => {}
                }
            }
            let got = ssd_reading(dev);
            if got != want {
                bad.push(format!(
                    "{dev} {smartctl:?} {ismart:?} {smartcmd:?}\n  python {want}\n  native {got}"
                ));
            }
        }
        assert!(bad.is_empty(), "{}", bad.join("\n"));
    }

    // Python's own tests that patch an `SsdUtil` after it is made
    // (tests/test_ssd.py), with their expectations.

    #[test]
    fn innodisk_attributes_missing_from_the_vendor_tool_stay_na() {
        let b = Bench::new();
        b.prints("smartctl", data("Innodisk_ssd"));
        b.prints("iSmart", data("Innodisk_ssd"));
        let mut s = SsdUtil::new("/dev/sda").unwrap();
        s.disk_io_reads = na();
        s.disk_io_writes = na();
        s.reserved_blocks = na();
        s.vendor_ssd_info = data("Innodisk_vendor_info")
            .replace("[E8]  Percentage os spare remaining               [    0]         [E80300640100000000000000]\n", "")
            .replace("[F1]  Total LBAs Written                          [150370]         [F102006401624B0200000000]\n", "")
            .replace("[F2]  Total LBAs Read                             [73954]         [F202006401E2200100000000]\n", "");
        s.parse_innodisk_info().unwrap();
        assert_eq!(
            (
                s.disk_io_reads.py_repr(),
                s.disk_io_writes.py_repr(),
                s.reserved_blocks.py_repr()
            ),
            ("'N/A'".into(), "'N/A'".into(), "'N/A'".into())
        );
    }

    #[test]
    fn innodisk_readings_come_from_the_vendor_tool_alone() {
        let mut s = blank("/dev/sda");
        s.model = PyVal::str("InnoDisk");
        s.vendor_ssd_info = data("Innodisk_vendor_info").to_string();
        s.parse_vendor_ssd_info(s.parse_vendor().unwrap().unwrap())
            .unwrap();
        assert_eq!(
            reading(&s),
            "['InnoDisk', 'BCA11802090990501', 'S16425cG', '92.725', '30', '73954', '150370', '0']"
        );
    }

    #[test]
    fn innodisk_without_vendor_output_keeps_smartctl_s() {
        for vendor in ["", "ERROR message from cmd"] {
            let b = Bench::new();
            b.prints("smartctl", data("Innodisk_missing_names_ssd"));
            b.prints("iSmart", data("Innodisk_missing_names_ssd"));
            let mut s = SsdUtil::new("/dev/sda").unwrap();
            s.vendor_ssd_info = vendor.to_string();
            s.parse_vendor_ssd_info(Vendor::InnoDisk).unwrap();
            assert_eq!(
                (s.health.py_repr(), s.temperature.py_repr()),
                ("'94'".into(), "'N/A'".into())
            );
        }
    }

    #[test]
    fn transcend_is_read_as_generic() {
        let b = Bench::new();
        b.prints("smartctl", data("transcend_vendor"));
        let mut s = SsdUtil::new("/dev/sda").unwrap();
        s.vendor_ssd_info = data("transcend_vendor").to_string();
        s.parse_vendor_ssd_info(Vendor::Transcend).unwrap();
        assert_eq!(
            (
                s.health.py_repr(),
                s.model.py_repr(),
                s.firmware.py_repr(),
                s.temperature.py_repr(),
                s.serial.py_repr()
            ),
            (
                "'100'".into(),
                "'TS120GMTS420S'".into(),
                "'R0522A0'".into(),
                "'33'".into(),
                "'I074710927'".into()
            )
        );
    }

    #[test]
    fn virtium_attributes_missing_from_the_vendor_tool_stay_na() {
        let b = Bench::new();
        b.prints("smartctl", data("virtium_generic"));
        b.prints("SmartCmd", data("virtium_vendor"));
        let mut s = SsdUtil::new("/dev/sda").unwrap();
        s.disk_io_reads = na();
        s.disk_io_writes = na();
        s.reserved_blocks = na();
        s.vendor_ssd_info = data("virtium_vendor")
            .replace(
                "232           Reserved_Attribute          0        100   100   100         0 \n",
                "",
            )
            .replace(
                "241           Total_LBAs_Written          0     629509   100   100         0 \n",
                "",
            )
            .replace(
                "242              Total_LBAs_Read          0    1482095   100   100         0 \n",
                "",
            );
        s.parse_virtium_info().unwrap();
        assert_eq!(
            (
                s.disk_io_reads.py_repr(),
                s.disk_io_writes.py_repr(),
                s.reserved_blocks.py_repr()
            ),
            ("'N/A'".into(), "'N/A'".into(), "'N/A'".into())
        );
        // No vendor output at all changes nothing.
        s.vendor_ssd_info = String::new();
        s.parse_virtium_info().unwrap();
        s.parse_micron_info().unwrap();
        assert_eq!(s.disk_io_reads.py_repr(), "'N/A'");
    }

    #[test]
    fn a_vendor_is_named_by_the_model() {
        let vendor = |m: &str| {
            let mut s = blank("/dev/sda");
            s.model = PyVal::str(m);
            s.parse_vendor().map_err(|e| e.str())
        };
        assert_eq!(vendor("Generic X"), Ok(Some(Vendor::Generic)));
        assert_eq!(vendor("M.2 (S80) 3TE6"), Ok(Some(Vendor::M2)));
        assert_eq!(vendor("StorFly VSF302XC032G"), Ok(Some(Vendor::StorFly)));
        assert_eq!(vendor("Virtium VTSM24"), Ok(Some(Vendor::Virtium)));
        assert_eq!(vendor("Swissbit X"), Ok(Some(Vendor::Swissbit)));
        assert_eq!(vendor("Micron X"), Ok(Some(Vendor::Micron)));
        assert_eq!(vendor("Intel X"), Ok(Some(Vendor::Intel)));
        assert_eq!(vendor("Transcend X"), Ok(Some(Vendor::Transcend)));
        assert_eq!(vendor("ATP X"), Ok(Some(Vendor::Atp)));
        assert_eq!(vendor("VSFDM8XC240G-V11-T"), Ok(Some(Vendor::Virtium)));
        assert_eq!(vendor("SFSA160GM2AK2TO"), Ok(Some(Vendor::Swissbit)));
        assert_eq!(vendor("MICRON_5300 x"), Ok(Some(Vendor::Micron)));
        assert_eq!(vendor("Microns_5300"), Ok(None));
        assert_eq!(vendor("SSD intel inside"), Ok(Some(Vendor::Intel)));
        assert_eq!(vendor("TS32GMTS400S"), Ok(Some(Vendor::Transcend)));
        assert_eq!(vendor("Acme"), Ok(None));
        assert_eq!(vendor(""), Err("list index out of range".to_string()));
        assert_eq!(Vendor::from_key("Nope"), None);
        for (v, tool) in [
            (Vendor::M2, INNODISK),
            (Vendor::StorFly, VIRTIUM),
            (Vendor::Atp, SMARTCTL),
        ] {
            assert_eq!(v.utility(), tool);
        }
    }

    #[test]
    fn the_parse_helpers_are_python_s() {
        assert_eq!(parse_re(r"Model:\s*(.+?)\n", "Model: X\n").unwrap(), "X");
        assert_eq!(
            parse_re(r".*FW.*", "a\nFW Version: 1\n").unwrap(),
            "FW Version: 1"
        );
        assert_eq!(parse_re(r"Nope(.)", "x").unwrap(), "N/A");
        assert_eq!(parse_re(r"(", "x").unwrap_err().exc.name(), "RuntimeError");
        // The rest of the unstripped line, as `line[len(str(id)):]` slices it.
        assert_eq!(parse_id_number("242", "  242 Total 5\n241 x"), "42 Total 5");
        assert_eq!(parse_id_number("9", ""), "N/A");
        assert_eq!(parse_id_number("9", "1 2\n"), "N/A");
        assert_eq!(word(" a b c ", 0).unwrap(), "a");
        assert_eq!(word("a b c", -1).unwrap(), "c");
        assert_eq!(word("a b c", -3).unwrap(), "a");
        assert_eq!(
            word("a b c", 3).unwrap_err().str(),
            "list index out of range"
        );
        assert_eq!(
            word("a b c", -4).unwrap_err().str(),
            "list index out of range"
        );
        assert_eq!(strip_chars("[[12]]", "[]"), "12");
        assert_eq!(hex_id(169), "[A9]");
        assert_eq!(
            execute_shell("").unwrap_err().str(),
            "list index out of range"
        );
    }

    #[test]
    fn disk_counters_are_psutil_s_with_wraps_undone() {
        let b = Bench::new();
        // psutil 7.0's disk_io_counters(perdisk=True, nowrap=True) over the
        // same files, one after the other.
        let steps: [(&str, &str); 7] = [
            (
                "   8       0 sda 100 2 3000 40 200 5 6000 70 0 90 110\n\
                 \x20  8       1 sda1 10 0 300 4 20 0 600 7 0 9 11 0 0 0 0 0 0\n\
                 \x20259       0 nvme0n1 500 0 9000 10 600 0 12000 20 0 30 40 0 0 0 0 0 0 0 0 0\n\
                 \x20  8      16 sdb 7 8 9 10\n\
                 \x20  3       0 39082680 hda 8 1 2 3 4 5 6 7 8 9 10\n",
                "[('hda', 39082680, 3), ('nvme0n1', 500, 600), ('sda', 100, 200), ('sda1', 10, 20), ('sdb', 7, 9)]",
            ),
            (
                "   8       0 sda 50 2 3000 40 300 5 6000 70 0 90 110\n\
                 \x20259       0 nvme0n1 400 0 9000 10 100 0 12000 20 0 30 40 0 0 0 0 0 0 0 0 0\n",
                "[('nvme0n1', 900, 700), ('sda', 150, 300)]",
            ),
            (
                "   8       0 sda 60 2 3000 40 250 5 6000 70 0 90 110\n\
                 \x20259       0 nvme0n1 450 0 9000 10 700 0 12000 20 0 30 40 0 0 0 0 0 0 0 0 0\n\
                 \x20  8      16 sdb 1 8 2 10\n",
                "[('nvme0n1', 950, 1300), ('sda', 160, 550), ('sdb', 1, 2)]",
            ),
            ("", "[]"),
            // The corrections survive an empty reading.
            (
                "   8       0 sda 60 2 3000 40 250 5 6000 70 0 90 110\n\
                 \x20259       0 nvme0n1 450 0 9000 10 700 0 12000 20 0 30 40 0 0 0 0 0 0 0 0 0\n",
                "[('nvme0n1', 950, 1300), ('sda', 160, 550)]",
            ),
            (
                "   8       0 sda 60 2 3000 40 250 5 6000 70 0 90 110\n   8       0 sdz 1 2\n",
                "raise ValueError: not sure how to interpret line '   8       0 sdz 1 2\\n'",
            ),
            (
                "   8       0 sda 6x 2 3000 40 250 5 6000 70 0 90 110\n",
                "raise ValueError: invalid literal for int() with base 10: '6x'",
            ),
        ];
        for (text, want) in steps {
            b.root.write("/proc/diskstats", text);
            let got = match disk_io_counters() {
                Ok(m) => {
                    let mut v: Vec<_> = m.into_iter().collect();
                    v.sort();
                    PyVal::List(
                        v.into_iter()
                            .map(|(n, (r, w))| {
                                PyVal::Tuple(vec![PyVal::Str(n), PyVal::Int(r), PyVal::Int(w)])
                            })
                            .collect(),
                    )
                    .py_repr()
                }
                Err(e) => format!("raise {}: {}", e.exc.name(), e.str()),
            };
            assert_eq!(got, want, "{text:?}");
        }
    }

    #[test]
    fn filesystem_counters_are_zero_for_a_disk_they_lack() {
        let b = Bench::new();
        b.prints("smartctl", data("fx_innodisk"));
        let s = SsdUtil::new("/dev/sda").unwrap();
        // No /proc/diskstats at all.
        assert_eq!(
            (
                s.get_fs_io_reads().unwrap().py_repr(),
                s.get_fs_io_writes().unwrap().py_repr()
            ),
            ("0".into(), "0".into())
        );
        b.root.write(
            "/proc/diskstats",
            "   8       0 sda 100 2 3000 40 200 5 6000 70 0 90 110\n",
        );
        assert_eq!(
            (
                s.get_fs_io_reads().unwrap().py_repr(),
                s.get_fs_io_writes().unwrap().py_repr()
            ),
            ("100".into(), "200".into())
        );
        let other = SsdUtil::new("/dev/sdb").unwrap();
        assert_eq!(other.get_fs_io_reads().unwrap().py_repr(), "0");
        let mut again = blank("/dev/sda");
        assert_eq!(again.get_fs_io_reads().unwrap().py_repr(), "0");
        again.fetch_parse_info("/dev/sda").unwrap();
        assert_eq!(
            again.get_model().unwrap().py_repr(),
            "'InnoDisk Corp. - mSATA 3ME'"
        );
    }

    #[test]
    fn emmc_readings_are_the_driver_s_files() {
        let b = Bench::new();
        let dev = "/sys/block/mmcblk0/device";
        let e = EmmcUtil::new("mmcblk0");
        assert_eq!(reading(&e), "raise NotImplementedError: ");
        assert_eq!(e.get_model().unwrap().py_repr(), "None");
        b.root.write(&format!("{dev}/name"), "S0J56X\n");
        b.root.write(&format!("{dev}/serial"), "0x1b2c3d\n");
        b.root
            .write(&format!("{dev}/fwrev"), "0x0400000000000000\n");
        b.root.write(&format!("{dev}/life_time"), "0x02 0x03\n");
        assert_eq!(
            reading(&e),
            "['S0J56X', '0x1b2c3d', '0x0400000000000000', 80.0, 'N/A', 'N/A', 'N/A', 'N/A']"
        );
        // An SLC part counts its first figure.
        b.root.write(&format!("{dev}/enhanced_area_offset"), "x\n");
        assert_eq!(e.get_health().unwrap().py_repr(), "90.0");
        b.root.write(&format!("{dev}/enhanced_area_offset"), "\n");
        assert_eq!(e.get_health().unwrap().py_repr(), "80.0");
        b.root.write(&format!("{dev}/life_time"), "01 0x0C\n");
        assert_eq!(e.get_health().unwrap().py_repr(), "-10.0");
        b.root.write(&format!("{dev}/life_time"), "0x01 02\n");
        assert_eq!(
            e.get_health().unwrap_err().str(),
            "invalid literal for int() with base 0: '02'"
        );
        b.root.write(&format!("{dev}/life_time"), "0x0B\n");
        assert_eq!(e.get_health().unwrap_err().str(), "list index out of range");
        let mut e = EmmcUtil::new("/dev/mmcblk0");
        e.fetch_parse_info("x").unwrap();
        b.root.write(
            "/proc/diskstats",
            " 179       0 mmcblk0 5 0 40 1 6 0 48 2 0 3 3\n",
        );
        assert_eq!(
            (
                e.get_fs_io_reads().unwrap().py_repr(),
                e.get_fs_io_writes().unwrap().py_repr()
            ),
            ("5".into(), "6".into())
        );
    }

    #[test]
    fn int_base0_is_int_with_base_0() {
        // Python 3.13's int(s, 0).
        let cases: [(&str, Result<i128, &str>); 33] = [
            ("0x02", Ok(2)),
            ("0X1F", Ok(31)),
            ("03", Err("invalid literal for int() with base 0: '03'")),
            ("3", Ok(3)),
            ("0", Ok(0)),
            ("00", Ok(0)),
            ("0_0", Ok(0)),
            ("1_000", Ok(1000)),
            ("0b11", Ok(3)),
            ("0o17", Ok(15)),
            ("-0x10", Ok(-16)),
            ("+7", Ok(7)),
            (" 12 ", Ok(12)),
            ("08", Err("invalid literal for int() with base 0: '08'")),
            ("0x", Err("invalid literal for int() with base 0: '0x'")),
            ("", Err("invalid literal for int() with base 0: ''")),
            ("abc", Err("invalid literal for int() with base 0: 'abc'")),
            ("0x_1f", Ok(31)),
            ("99999", Ok(99999)),
            ("1__0", Err("invalid literal for int() with base 0: '1__0'")),
            ("_1", Err("invalid literal for int() with base 0: '_1'")),
            ("1_", Err("invalid literal for int() with base 0: '1_'")),
            ("0_", Err("invalid literal for int() with base 0: '0_'")),
            ("0_3", Err("invalid literal for int() with base 0: '0_3'")),
            (
                "0x__1",
                Err("invalid literal for int() with base 0: '0x__1'"),
            ),
            ("0x_", Err("invalid literal for int() with base 0: '0x_'")),
            ("0x-1", Err("invalid literal for int() with base 0: '0x-1'")),
            ("-+5", Err("invalid literal for int() with base 0: '-+5'")),
            ("0b_1", Ok(1)),
            ("  -0x_f  ", Ok(-15)),
            ("\u{663}", Ok(3)),
            ("0x\u{661}", Ok(1)),
            ("1\u{a0}", Ok(1)),
        ];
        for (s, want) in cases {
            assert_eq!(
                int_base0(s).map_err(|e| e.str()),
                want.map_err(String::from),
                "{s:?}"
            );
        }
    }

    /// `lsblk -r` and `lsblk -i` as blkinfo reads them, over disks whose
    /// readings Python's UsbUtil gave (blkinfo with the same lsblk).
    const LSBLK_RAW: &str = "\
loop0 loop0   0 16008609792 7:0 1 Ultra\\x20Fit SanDisk 4C530001 1:0:0:0 usb 1 disk 0 root disk brw-rw----
loop1 loop1 vfat USB  16007561216 7:1 1   4C530001  usb 1 part 0 root disk brw-rw----
loop2 loop2   0 100 7:2 0 Disk\\x20Two ACME S2 2:0:0:0 sata 0 disk 0 root disk brw-rw----
loop3 loop3   0 100 7:3 0 Disk\\x20Three ACME S3 3:0:0:0 sata 0 disk 0 root disk brw-rw----
mpatha mpatha   0 100 253:0 0 MP ACME SM - - 0 mpath 0 root disk brw-rw----
loop4 loop4   0 100 7:4 0 Four ACME S4 4:0:0:0 sata 0 disk 0 root disk brw-rw----
loop5 loop5   0 100 7:5 0 Five ACME S5 5:0:0:0 sata 0 disk 0 root disk brw-rw----
md0 md0   0 100 9:0 0 RAID ACME SR - - 0 raid1 0 root disk brw-rw----
loop6 loop6   0 100 7:6 0 Six  S6 6:0:0:0 sata 0 rom 0 root disk brw-rw----
";
    const LSBLK_TREE: &str =
        "loop0\n`-loop1\nloop2\n`-mpatha\nloop3\n`-mpatha\nloop4\n`-md0\nloop5\n`-md0\nloop6\n";

    #[test]
    fn usb_readings_are_blkinfo_s() {
        let b = Bench::new();
        b.lsblk(LSBLK_RAW, LSBLK_TREE);
        for n in 0..8 {
            b.disk(&format!("loop{n}"), None);
        }
        b.root.write("/proc/diskstats", "");
        let usb = |dev: &str| match UsbUtil::new(dev) {
            Ok(u) => reading(&u),
            Err(e) => format!("raise {}: {}", e.exc.name(), e.str()),
        };
        let index_error = "raise IndexError: list index out of range";
        assert_eq!(
            usb("/dev/loop0"),
            "['SanDisk Ultra Fit', '4C530001', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"
        );
        // A partition is no disk; the parents of a multipath or of a raid
        // whose only child it is are hidden.
        for dev in [
            "/dev/loop1",
            "/dev/loop2",
            "/dev/loop3",
            "/dev/loop4",
            "/dev/loop5",
            "/dev/loop7",
        ] {
            assert_eq!(usb(dev), index_error, "{dev}");
        }
        assert_eq!(
            usb("/dev/loop6"),
            "[' Six', 'S6', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A', 'N/A']"
        );
        let mut u = UsbUtil::new("/dev/loop0").unwrap();
        u.fetch_parse_info("/dev/loop0").unwrap();
        b.root.write(
            "/proc/diskstats",
            "   7       0 loop0 3 0 40 1 4 0 48 2 0 3 3\n",
        );
        assert_eq!(
            (
                u.get_fs_io_reads().unwrap().py_repr(),
                u.get_fs_io_writes().unwrap().py_repr()
            ),
            ("3".into(), "4".into())
        );
        // lsblk failing lists nothing; lsblk missing is blkinfo's error.
        b.tool("lsblk", "exit 1\n");
        assert_eq!(usb("/dev/loop0"), index_error);
        std::fs::remove_file(b.tools.join("lsblk")).unwrap();
        assert_eq!(
            usb("/dev/loop0"),
            "raise NoLsblkFound: lsblk command-line tool from util-linux package is not found."
        );
    }

    /// The rest of `LsBlkWrapper()`, after the tree: a second lsblk that
    /// fails, an iSCSI disk's links, /proc/diskstats.
    #[test]
    fn blkinfo_fails_where_python_s_fails() {
        let b = Bench::new();
        b.disk("loop0", None);
        b.root.write("/proc/diskstats", "");
        let usb = |dev: &str| match UsbUtil::new(dev) {
            Ok(u) => reading(&u),
            Err(e) => format!("raise {}: {}", e.exc.name(), e.str()),
        };
        let raw = "loop0 loop0   0 100 7:0 0 M V S 1:0:0:0 usb 0 disk 0 root disk brw-rw----\n";
        let tree_cmd = "['lsblk', '-a', '-n', '-i', '-o', 'NAME']";
        // The tree view failing is its CalledProcessError; lsblk gone by then
        // is lsblk missing.
        std::fs::write(b.tools.join("lsblk.raw"), raw).unwrap();
        b.tool("lsblk", "d=$(dirname \"$0\")\ncase \" $* \" in *\" -r \"*) cat \"$d/lsblk.raw\" ;; *) exit 2 ;; esac\n");
        assert_eq!(
            usb("/dev/loop0"),
            format!(
                "raise CalledProcessError: Command '{tree_cmd}' returned non-zero exit status 2."
            )
        );
        b.tool(
            "lsblk",
            "d=$(dirname \"$0\")\ncat \"$d/lsblk.raw\"; rm -f \"$0\"\n",
        );
        assert_eq!(
            usb("/dev/loop0"),
            "raise NoLsblkFound: lsblk command-line tool from util-linux package is not found."
        );
        // A field Python cannot decode empties the listing.
        b.lsblk(
            "loop0 loop0   0 100 7:0 0 M\\x4 V S 1:0:0:0 usb 0 disk 0 root disk brw-rw----\n",
            "loop0\n",
        );
        assert_eq!(
            usb("/dev/loop0"),
            "raise IndexError: list index out of range"
        );
        // No /proc/diskstats.
        b.lsblk(raw, "loop0\n");
        assert!(usb("/dev/loop0").starts_with("['V M'"));
        std::fs::remove_file(b.root.real("/proc/diskstats")).unwrap();
        assert_eq!(
            usb("/dev/loop0"),
            "raise FileNotFoundError: [Errno 2] No such file or directory: '/proc/diskstats'"
        );
        b.root.write("/proc/diskstats", "");
        // An iSCSI disk: its link, the host and session in it, a connection.
        let iscsi = "loop0 loop0   0 100 7:0 0 M V S 1:0:0:0 iscsi 0 disk 0 root disk brw-rw----\n";
        b.lsblk(iscsi, "loop0\n");
        // A directory is no link; then no entry at all.
        assert_eq!(
            usb("/dev/loop0"),
            "raise OSError: [Errno 22] Invalid argument: '/sys/block/loop0'"
        );
        let link = b.root.real("/sys/block/loop0");
        std::fs::remove_dir(&link).unwrap();
        assert_eq!(
            usb("/dev/loop0"),
            "raise FileNotFoundError: [Errno 2] No such file or directory: '/sys/block/loop0'"
        );
        symlink("../devices", &link).unwrap();
        assert_eq!(
            usb("/dev/loop0"),
            "raise IndexError: list index out of range"
        );
        std::fs::remove_file(&link).unwrap();
        let target = "../devices/platform/host2/session1/target2:0:0/block/loop0";
        std::fs::create_dir_all(b.root.real(&format!("/sys/block/{target}"))).unwrap();
        symlink(target, &link).unwrap();
        assert_eq!(
            usb("/dev/loop0"),
            "raise IndexError: list index out of range"
        );
        std::fs::create_dir_all(
            b.root
                .real("/sys/devices/platform/host2/session1/connection1:0"),
        )
        .unwrap();
        assert!(usb("/dev/loop0").starts_with("['V M'"));
    }

    #[test]
    fn unicode_escape_decodes_as_python_decodes() {
        // Python 3.13's bytes.decode("unicode_escape"); None where it raises.
        let cases: [(&[u8], Option<&str>); 15] = [
            (b"Ultra\\x20Fit", Some("Ultra Fit")),
            (b"caf\xe9", Some("caf\u{e9}")),
            (b"\\101\\7", Some("A\x07")),
            (b"\\q", Some("\\q")),
            (b"\\n\\t\\\\\\'\\\"", Some("\n\t\\'\"")),
            (b"\\a\\b\\f\\r\\v", Some("\x07\x08\x0c\r\x0b")),
            (b"a\\\nb", Some("ab")),
            (b"\\u00e9\\U0001F600", Some("\u{e9}\u{1f600}")),
            (b"\\ud800", Some("\u{fffd}")),
            (b"a\\x4", None),
            (b"\\xZZ", None),
            (b"\\u00", None),
            (b"\\U00110000", None),
            (b"a\\", None),
            (b"\\N{BULLET}", None),
        ];
        for (b, want) in cases {
            assert_eq!(
                unicode_escape(b).as_deref(),
                want,
                "{:?}",
                String::from_utf8_lossy(b)
            );
        }
    }

    #[test]
    fn each_disk_gets_the_utility_its_kind_needs() {
        let b = Bench::new();
        // blkinfo opens it for any USB disk, as a switch always has it.
        b.root.write("/proc/diskstats", "");
        b.smartctl(&[
            ("sda", data("fx_innodisk")),
            ("nvme0n1", data("nvme_ssd")),
            ("sdd", data("fx_smartcmd")),
        ]);
        b.prints("iSmart", data("fx_ismart"));
        b.lsblk(
            "sdb sdb   0 16008609792 8:16 1 Ultra\\x20Fit SanDisk 4C530001 1:0:0:0 usb 1 disk 0 root disk brw-rw----\n",
            "sdb\n",
        );
        b.disk("sda", Some("/sys/devices/pci0000:00/ata1/host0/sda"));
        b.disk("nvme0n1", Some("/sys/devices/pci0000:00/nvme/nvme0"));
        b.disk("sdb", Some("/sys/devices/pci0000:00/usb1/1-1/sdb"));
        b.disk("sdc", Some("/sys/devices/virtual/sdc"));
        b.disk("sdd", Some("/sys/devices/pci0000:00/ata2/host1/sdd"));
        b.disk("sde", Some("/sys/devices/pci0000:00/usb2/2-1/sde"));
        b.disk("xvda", None);
        b.disk("loop0", None);
        b.disk("mmcblk0boot0", None);
        b.root.write("/sys/block/mmcblk0/device/name", "S0J56X\n");
        let mut got: Vec<(String, String)> = StorageDevices::new()
            .unwrap()
            .devices
            .into_iter()
            .map(|(n, d)| {
                (
                    n,
                    d.map_or("None".to_string(), |d| d.get_model().unwrap().py_repr()),
                )
            })
            .collect();
        got.sort();
        let want: Vec<(String, String)> = [
            ("mmcblk0", "'S0J56X'"),
            ("nvme0n1", "'SFPC020GM1EC2TO-I-5E-11P-STD'"),
            ("sda", "'InnoDisk Corp. - mSATA 3ME'"),
            ("sdb", "'SanDisk Ultra Fit'"),
            // A virtual disk is none of these; smartctl's and lsblk's
            // failures leave theirs out.
            ("sdc", "None"),
            ("sdd", "None"),
            ("sde", "None"),
            ("xvda", "None"),
        ]
        .iter()
        .map(|(a, b)| (a.to_string(), b.to_string()))
        .collect();
        assert_eq!(got, want);
        std::fs::remove_dir_all(b.root.real("/sys/block")).unwrap();
        assert_eq!(
            StorageDevices::new().err().unwrap().str(),
            "[Errno 2] No such file or directory: '/sys/block'"
        );
    }

    #[test]
    fn without_a_tool_directory_tools_come_from_path() {
        let _root = Root::new();
        assert_eq!(execute_shell("echo hi").unwrap(), "hi\n");
        assert_eq!(
            execute_shell("no-such-tool-anywhere x").unwrap_err().str(),
            "[Errno 2] No such file or directory: 'no-such-tool-anywhere'"
        );
    }

    #[test]
    fn a_reading_converts_as_int_does() {
        assert_eq!(int_of(&PyVal::Int(5)).unwrap(), 5);
        assert_eq!(int_of(&PyVal::Bool(true)).unwrap(), 1);
        assert_eq!(int_of(&PyVal::Float(98.7)).unwrap(), 98);
        assert_eq!(int_of(&PyVal::str(" 12 ")).unwrap(), 12);
        assert_eq!(
            int_of(&PyVal::str("N/A")).unwrap_err().str(),
            "invalid literal for int() with base 10: 'N/A'"
        );
        assert_eq!(
            int_of(&PyVal::None).unwrap_err().str(),
            "int() argument must be a string, a bytes-like object or a real number, not 'NoneType'"
        );
    }
}
