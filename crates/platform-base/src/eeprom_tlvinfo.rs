//! `sonic_eeprom/eeprom_tlvinfo.py`: the ONIE TlvInfo EEPROM.
//!
//! What syseepromd publishes to `EEPROM_INFO|*` and what a chassis answers
//! for its name, serial and base MAC both come from here, so the decoded
//! strings, the field order and the error cases are Python's exactly.

use std::io::{Read, Seek, SeekFrom};
use std::sync::OnceLock;

use crate::db::Db;
use crate::io;
use crate::py::{Exc, PyErr, PyResult, PyVal};

pub const TLV_INFO_ID_STRING: &[u8] = b"TlvInfo\x00";
pub const TLV_INFO_VERSION: u8 = 0x01;
pub const TLV_INFO_HDR_LEN: usize = 11;
pub const TLV_INFO_MAX_LEN: usize = 2048;
pub const TLV_TOTAL_LEN_MAX: usize = TLV_INFO_MAX_LEN - TLV_INFO_HDR_LEN;

pub const TLV_CODE_PRODUCT_NAME: u8 = 0x21;
pub const TLV_CODE_PART_NUMBER: u8 = 0x22;
pub const TLV_CODE_SERIAL_NUMBER: u8 = 0x23;
pub const TLV_CODE_MAC_BASE: u8 = 0x24;
pub const TLV_CODE_MANUF_DATE: u8 = 0x25;
pub const TLV_CODE_DEVICE_VERSION: u8 = 0x26;
pub const TLV_CODE_LABEL_REVISION: u8 = 0x27;
pub const TLV_CODE_PLATFORM_NAME: u8 = 0x28;
pub const TLV_CODE_ONIE_VERSION: u8 = 0x29;
pub const TLV_CODE_MAC_SIZE: u8 = 0x2A;
pub const TLV_CODE_MANUF_NAME: u8 = 0x2B;
pub const TLV_CODE_MANUF_COUNTRY: u8 = 0x2C;
pub const TLV_CODE_VENDOR_NAME: u8 = 0x2D;
pub const TLV_CODE_DIAG_VERSION: u8 = 0x2E;
pub const TLV_CODE_SERVICE_TAG: u8 = 0x2F;
pub const TLV_CODE_UNDEFINED: u8 = 0xFC;
pub const TLV_CODE_VENDOR_EXT: u8 = 0xFD;
pub const TLV_CODE_CRC_32: u8 = 0xFE;

/// `hex(code)`: `0x21`, lower case, no padding.
pub fn hex(code: impl Into<i128>) -> String {
    let c: i128 = code.into();
    if c < 0 {
        format!("-0x{:x}", -c)
    } else {
        format!("0x{c:x}")
    }
}

/// `binascii.crc32(e) & 0xffffffff`.
pub fn crc32(data: &[u8]) -> u32 {
    let mut crc = 0xFFFF_FFFFu32;
    for &b in data {
        crc ^= u32::from(b);
        for _ in 0..8 {
            crc = if crc & 1 != 0 {
                (crc >> 1) ^ 0xEDB8_8320
            } else {
                crc >> 1
            };
        }
    }
    !crc
}

/// `bytes.decode("ascii")`.
fn ascii(b: &[u8]) -> PyResult<String> {
    match b.iter().position(|c| *c >= 0x80) {
        None => Ok(b.iter().map(|c| *c as char).collect()),
        Some(i) => Err(PyErr::other(
            "UnicodeDecodeError",
            format!(
                "'ascii' codec can't decode byte 0x{:02x} in position {i}: ordinal not in range(128)",
                b[i]
            ),
        )),
    }
}

/// A visitor over the decoded EEPROM, as `EepromDefaultVisitor`.
pub trait Visitor {
    fn visit_header(
        &mut self,
        _id: Option<&str>,
        _version: Option<u8>,
        _len: Option<usize>,
    ) -> PyResult<()> {
        Ok(())
    }
    fn visit_tlv(&mut self, _name: &str, _code: u8, _length: u8, _value: &str) -> PyResult<()> {
        Ok(())
    }
    fn visit_end(&mut self, _data: &[u8]) -> PyResult<()> {
        Ok(())
    }
    fn set_error(&mut self, _error: &str) {}
}

/// `TlvInfoDecoder(path, start, status, ro)`.
pub struct TlvInfoDecoder {
    pub path: String,
    pub start: u64,
    pub status: String,
    pub read_only: bool,
    state_db: OnceLock<Db>,
}

impl TlvInfoDecoder {
    pub fn new(path: &str, start: u64, status: &str, read_only: bool) -> TlvInfoDecoder {
        TlvInfoDecoder {
            path: path.to_string(),
            start,
            status: status.to_string(),
            read_only,
            state_db: OnceLock::new(),
        }
    }

    /// `state_db`: STATE_DB, connected on first use.
    pub fn state_db(&self) -> PyResult<&Db> {
        if let Some(db) = self.state_db.get() {
            return Ok(db);
        }
        let db = Db::connect("STATE_DB")?;
        Ok(self.state_db.get_or_init(|| db))
    }

    /// `_redis_hget(key, field)`: trailing NULs stripped.
    pub fn redis_hget(&self, key: &str, field: &str) -> PyResult<Option<String>> {
        Ok(self
            .state_db()?
            .hget(key, field)?
            .map(|v| v.trim_end_matches('\0').to_string()))
    }

    /// `read_eeprom_bytes(byteCount, offset)`: there is never a cache file
    /// (`cache_name` is None), so it is the EEPROM itself.
    pub fn read_eeprom_bytes(&self, count: usize, offset: u64) -> PyResult<Vec<u8>> {
        let io_err = |e: std::io::Error| {
            PyErr::new(
                Exc::OSError("OSError"),
                vec![PyVal::Str(format!(
                    "Failed to read eeprom : {}",
                    PyErr::from_io(&e, Some(&self.path)).str()
                ))],
            )
        };
        let mut f = std::fs::File::open(io::real(&self.path)).map_err(io_err)?;
        f.seek(SeekFrom::Start(self.start + offset))
            .map_err(io_err)?;
        let mut buf = Vec::new();
        f.take(count as u64).read_to_end(&mut buf).map_err(io_err)?;
        if buf.len() != count {
            return Err(PyErr::runtime_error(format!(
                "Expected to read {count} bytes from {}, but only read {}",
                self.path,
                buf.len()
            )));
        }
        Ok(buf)
    }

    /// `read_eeprom()`: the header, and the TLVs its length names.
    pub fn read_eeprom(&self) -> PyResult<Vec<u8>> {
        let h = self.read_eeprom_bytes(TLV_INFO_HDR_LEN, 0)?;
        if !is_valid_tlvinfo_header(&h) {
            return Ok(h);
        }
        let size = (usize::from(h[9]) << 8) | usize::from(h[10]);
        let t = self.read_eeprom_bytes(size, TLV_INFO_HDR_LEN as u64)?;
        if t.len() != size {
            return Err(PyErr::runtime_error(format!(
                "expected to read {size} bytes from {}, but only read {}",
                self.path,
                t.len()
            )));
        }
        let mut out = h;
        out.extend(t);
        Ok(out)
    }

    /// `visit_eeprom(e, visitor)`.
    pub fn visit_eeprom(&self, e: &[u8], v: &mut dyn Visitor) -> PyResult<()> {
        if !is_valid_tlvinfo_header(e) {
            v.set_error("EEPROM does not contain data in a valid TlvInfo format.");
            return Ok(());
        }
        let total = (usize::from(e[9]) << 8) | usize::from(e[10]);
        let mut idx = TLV_INFO_HDR_LEN;
        let end = TLV_INFO_HDR_LEN + total;
        v.visit_header(Some(&ascii(&e[0..7])?), Some(e[8]), Some(total))?;
        while idx + 2 < e.len() && idx < end {
            if !is_valid_tlv(&e[idx..]) {
                v.set_error(&format!(
                    "Invalid TLV field starting at EEPROM offset {idx}"
                ));
                break;
            }
            let len = usize::from(e[idx + 1]);
            let tlv = &e[idx..(idx + 2 + len).min(e.len())];
            let (name, value) = decoder(tlv)?;
            v.visit_tlv(&name, tlv[0], tlv[1], &value)?;
            // `_TLV_CODE_QUANTA_CRC` is `_TLV_CODE_UNDEFINED`: it ends the walk too.
            if e[idx] == TLV_CODE_UNDEFINED || e[idx] == TLV_CODE_CRC_32 {
                break;
            }
            idx += len + 2;
        }
        v.visit_end(e)
    }

    /// `update_eeprom_db(e)`: 0 on success, -1 if the visit reported an error.
    pub fn update_eeprom_db(&self, e: &[u8]) -> PyResult<i128> {
        let mut v = RedisVisitor {
            db: self.state_db()?,
            vendor_ext: 0,
            error: None,
        };
        self.visit_eeprom(e, &mut v)?;
        Ok(if v.error.is_none() { 0 } else { -1 })
    }
}

/// `is_valid_tlvinfo_header(e)`.
pub fn is_valid_tlvinfo_header(e: &[u8]) -> bool {
    e.len() >= TLV_INFO_HDR_LEN
        && &e[0..8] == TLV_INFO_ID_STRING
        && e[8] == TLV_INFO_VERSION
        && ((usize::from(e[9]) << 8) | usize::from(e[10])) <= TLV_TOTAL_LEN_MAX
}

/// `is_valid_tlv(e)`.
pub fn is_valid_tlv(e: &[u8]) -> bool {
    e.len() >= 2 && 2 + usize::from(e[1]) <= e.len()
}

/// `is_checksum_valid(e)`: (valid, the CRC computed).
pub fn is_checksum_valid(e: &[u8]) -> (bool, u32) {
    if !is_valid_tlvinfo_header(e) {
        return (false, 0);
    }
    let offset = TLV_INFO_HDR_LEN + ((usize::from(e[9]) << 8) | usize::from(e[10]));
    if e.len() < offset || offset < 6 || e[offset - 6] != TLV_CODE_CRC_32 || e[offset - 5] != 4 {
        return (false, 0);
    }
    let crc = crc32(&e[..offset - 4]);
    let tlv_crc = u32::from(e[offset - 4]) << 24
        | u32::from(e[offset - 3]) << 16
        | u32::from(e[offset - 2]) << 8
        | u32::from(e[offset - 1]);
    (tlv_crc == crc, crc)
}

/// `decoder(s, t)`: the field's name and its value as a string.
pub fn decoder(t: &[u8]) -> PyResult<(String, String)> {
    let len = usize::from(t.get(1).copied().unwrap_or(0));
    let body = |t: &[u8]| t.get(2..(2 + len).min(t.len())).unwrap_or(&[]).to_vec();
    let text = |name: &str| -> PyResult<(String, String)> { Ok((name.into(), ascii(&body(t))?)) };
    let byte = |i: usize| t.get(i).copied().unwrap_or(0);
    let (name, value) = match t[0] {
        TLV_CODE_PRODUCT_NAME => text("Product Name")?,
        TLV_CODE_PART_NUMBER => text("Part Number")?,
        TLV_CODE_SERIAL_NUMBER => text("Serial Number")?,
        TLV_CODE_MAC_BASE => (
            "Base MAC Address".into(),
            t.get(2..8.min(t.len()))
                .unwrap_or(&[])
                .iter()
                .map(|b| format!("{b:02x}"))
                .collect::<Vec<_>>()
                .join(":")
                .to_uppercase(),
        ),
        TLV_CODE_MANUF_DATE => text("Manufacture Date")?,
        // `str(t[2])`: an IndexError on a zero-length field, as in Python,
        // whose `t` is a slice of the `bytearray` `read_eeprom_bytes` answers.
        TLV_CODE_DEVICE_VERSION => (
            "Device Version".into(),
            t.get(2)
                .map(|b| b.to_string())
                .ok_or_else(|| PyErr::index_error("bytearray index out of range"))?,
        ),
        TLV_CODE_LABEL_REVISION => text("Label Revision")?,
        TLV_CODE_PLATFORM_NAME => text("Platform Name")?,
        TLV_CODE_ONIE_VERSION => text("ONIE Version")?,
        TLV_CODE_MAC_SIZE => {
            if t.len() < 4 {
                return Err(PyErr::index_error("bytearray index out of range"));
            }
            (
                "MAC Addresses".into(),
                ((u32::from(byte(2)) << 8) | u32::from(byte(3))).to_string(),
            )
        }
        TLV_CODE_MANUF_NAME => text("Manufacturer")?,
        TLV_CODE_MANUF_COUNTRY => text("Manufacture Country")?,
        TLV_CODE_VENDOR_NAME => text("Vendor Name")?,
        TLV_CODE_DIAG_VERSION => text("Diag Version")?,
        TLV_CODE_SERVICE_TAG => text("Service Tag")?,
        TLV_CODE_VENDOR_EXT => (
            "Vendor Extension".into(),
            body(t)
                .iter()
                .map(|c| format!("0x{c:02X} "))
                .collect::<String>()
                .trim_end()
                .to_string(),
        ),
        TLV_CODE_CRC_32 if t.len() == 6 => (
            "CRC-32".into(),
            format!(
                "0x{:08X}",
                (u32::from(t[2]) << 24)
                    | (u32::from(t[3]) << 16)
                    | (u32::from(t[4]) << 8)
                    | u32::from(t[5])
            ),
        ),
        // The Quanta codes all alias 0xFC, "undefined"; the first of them
        // matches by code alone only for the model name.
        TLV_CODE_UNDEFINED if t.len() == 3 => ("Magic Number".into(), format!("0x{:02X}", t[2])),
        TLV_CODE_UNDEFINED if t.len() == 4 => (
            "QUANTA-CRC".into(),
            format!("0x{:04X}", (u32::from(t[2]) << 8) + u32::from(t[3])),
        ),
        TLV_CODE_UNDEFINED if t.len() == 6 => (
            "Card Type".into(),
            format!(
                "0x{:08X}",
                (u32::from(t[2]) << 24)
                    | (u32::from(t[3]) << 16)
                    | (u32::from(t[4]) << 8)
                    | u32::from(t[5])
            ),
        ),
        TLV_CODE_UNDEFINED => text("Model Name")?,
        _ => (
            "Unknown".into(),
            body(t)
                .iter()
                .map(|c| format!("0x{c:02X} "))
                .collect::<String>(),
        ),
    };
    Ok((name, value.replace('\0', "")))
}

/// `EepromRedisVisitor`: what syseepromd writes to STATE_DB.
struct RedisVisitor<'a> {
    db: &'a Db,
    vendor_ext: usize,
    error: Option<String>,
}

impl RedisVisitor<'_> {
    /// `SonicV2Connector.hmset(db, key, dict)`: the dict reaches C++ as a
    /// `std::map`, so the fields go to redis in byte order of their names,
    /// not in the order Python built them -- and a small hash answers
    /// HGETALL in the order it was written.
    fn hmset(&self, key: &str, fvs: &[(String, String)]) -> PyResult<()> {
        let mut fvs: Vec<(&str, &str)> =
            fvs.iter().map(|(k, v)| (k.as_str(), v.as_str())).collect();
        fvs.sort_by(|a, b| a.0.as_bytes().cmp(b.0.as_bytes()));
        fvs.dedup_by(|a, b| a.0 == b.0);
        self.db.hset(key, &fvs)
    }
}

impl Visitor for RedisVisitor<'_> {
    fn visit_header(
        &mut self,
        id: Option<&str>,
        version: Option<u8>,
        len: Option<usize>,
    ) -> PyResult<()> {
        if let Some(id) = id {
            self.hmset(
                "EEPROM_INFO|TlvHeader",
                &[
                    ("Id String".into(), id.into()),
                    ("Version".into(), version.unwrap_or(0).to_string()),
                    ("Total Length".into(), len.unwrap_or(0).to_string()),
                ],
            )?;
        }
        Ok(())
    }

    fn visit_tlv(&mut self, name: &str, code: u8, length: u8, value: &str) -> PyResult<()> {
        let fvs = if code == TLV_CODE_VENDOR_EXT {
            let i = self.vendor_ext;
            self.vendor_ext += 1;
            vec![
                (format!("Name_{i}"), name.to_string()),
                (format!("Len_{i}"), length.to_string()),
                (format!("Value_{i}"), value.to_string()),
            ]
        } else {
            vec![
                ("Name".into(), name.to_string()),
                ("Len".into(), length.to_string()),
                ("Value".into(), value.to_string()),
            ]
        };
        self.hmset(&format!("EEPROM_INFO|{}", hex(code)), &fvs)
    }

    fn visit_end(&mut self, data: &[u8]) -> PyResult<()> {
        if self.vendor_ext > 0 {
            self.hmset(
                &format!("EEPROM_INFO|{}", hex(TLV_CODE_VENDOR_EXT)),
                &[("Num_vendor_ext".into(), self.vendor_ext.to_string())],
            )?;
        }
        let valid = if is_checksum_valid(data).0 { "1" } else { "0" };
        self.hmset("EEPROM_INFO|Checksum", &[("Valid".into(), valid.into())])?;
        self.hmset("EEPROM_INFO|State", &[("Initialized".into(), "1".into())])
    }

    fn set_error(&mut self, error: &str) {
        self.error = Some(error.to_string());
        // `print(error)`.  Written, not `println!`: a daemon whose stdout has
        // gone would panic on it, where Python's print raises into a caller
        // that has nothing to do with the EEPROM.
        use std::io::Write;
        let _ = writeln!(std::io::stdout(), "{error}");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A TlvInfo image: header, product name, base MAC, vendor ext, CRC.
    fn image() -> Vec<u8> {
        let mut tlvs = vec![TLV_CODE_PRODUCT_NAME, 6];
        tlvs.extend(b"SN5600");
        tlvs.extend([TLV_CODE_MAC_BASE, 6, 0x1c, 0x34, 0xda, 0x0a, 0xbc, 0xde]);
        tlvs.extend([TLV_CODE_VENDOR_EXT, 3, 0x00, 0x00, 0x81]);
        let total = tlvs.len() + 6;
        let mut e = TLV_INFO_ID_STRING.to_vec();
        e.extend([TLV_INFO_VERSION, (total >> 8) as u8, total as u8]);
        e.extend(tlvs);
        e.extend([TLV_CODE_CRC_32, 4]);
        let crc = crc32(&e);
        e.extend(crc.to_be_bytes());
        e
    }

    struct Collect(Vec<(String, u8, String)>);
    impl Visitor for Collect {
        fn visit_tlv(&mut self, name: &str, code: u8, _l: u8, value: &str) -> PyResult<()> {
            self.0.push((name.into(), code, value.into()));
            Ok(())
        }
    }

    fn tlv(code: u8, value: &[u8]) -> Vec<u8> {
        let mut t = vec![code, value.len() as u8];
        t.extend(value);
        t
    }

    /// A header for `tlvs`, then them, then a CRC-32 field: `crc` if given,
    /// the right one otherwise.
    fn image_of(tlvs: &[Vec<u8>], crc: Option<u32>) -> Vec<u8> {
        let body: Vec<u8> = tlvs.concat();
        let total = body.len() + 6;
        let mut e = TLV_INFO_ID_STRING.to_vec();
        e.extend([TLV_INFO_VERSION, (total >> 8) as u8, total as u8]);
        e.extend(body);
        e.extend([TLV_CODE_CRC_32, 4]);
        let c = crc.unwrap_or_else(|| crc32(&e));
        e.extend(c.to_be_bytes());
        e
    }

    fn err<T>(r: PyResult<T>) -> (String, String) {
        match r {
            Ok(_) => panic!("an error expected"),
            Err(e) => (e.exc.name().to_string(), e.str()),
        }
    }

    #[test]
    fn every_field_decodes_to_python_s_name_and_string() {
        let cases: &[(Vec<u8>, &str, &str)] = &[
            (tlv(0x21, b"SN5600"), "Product Name", "SN5600"),
            (tlv(0x22, b"MSN5600-VS2FO"), "Part Number", "MSN5600-VS2FO"),
            (tlv(0x23, b"MT2401X00042"), "Serial Number", "MT2401X00042"),
            (
                tlv(0x24, &[0x1c, 0x34, 0xda, 0x0a, 0xbc, 0xde]),
                "Base MAC Address",
                "1C:34:DA:0A:BC:DE",
            ),
            (
                tlv(0x25, b"01/02/2026 10:00:00"),
                "Manufacture Date",
                "01/02/2026 10:00:00",
            ),
            (tlv(0x26, &[7]), "Device Version", "7"),
            (tlv(0x27, b"A1"), "Label Revision", "A1"),
            (
                tlv(0x28, b"x86_64-nvidia_sn5600-r0"),
                "Platform Name",
                "x86_64-nvidia_sn5600-r0",
            ),
            (tlv(0x29, b"2023.05"), "ONIE Version", "2023.05"),
            (tlv(0x2a, &[1, 2]), "MAC Addresses", "258"),
            (tlv(0x2b, b"Nvidia"), "Manufacturer", "Nvidia"),
            (tlv(0x2c, b"IL"), "Manufacture Country", "IL"),
            (tlv(0x2d, b"Mellanox"), "Vendor Name", "Mellanox"),
            (tlv(0x2e, b"1.0"), "Diag Version", "1.0"),
            (tlv(0x2f, b"tag"), "Service Tag", "tag"),
            (
                tlv(0xfd, &[0, 0, 0x81, 0x19]),
                "Vendor Extension",
                "0x00 0x00 0x81 0x19",
            ),
            (tlv(0xfe, &[0xde, 0xad, 0xbe, 0xef]), "CRC-32", "0xDEADBEEF"),
            // A CRC-32 of the wrong size is no CRC-32.
            (tlv(0xfe, &[1, 2]), "Unknown", "0x01 0x02 "),
            (tlv(0xfc, &[0x5a]), "Magic Number", "0x5A"),
            (tlv(0xfc, &[0x12, 0x34]), "QUANTA-CRC", "0x1234"),
            (tlv(0xfc, &[1, 2, 3, 4]), "Card Type", "0x01020304"),
            (tlv(0xfc, b"model"), "Model Name", "model"),
            (tlv(0x99, &[0xab]), "Unknown", "0xAB "),
            (tlv(0x21, b"a\0b"), "Product Name", "ab"),
        ];
        for (t, name, value) in cases {
            assert_eq!(
                decoder(t).unwrap(),
                (name.to_string(), value.to_string()),
                "{t:?}"
            );
        }
        assert_eq!(
            err(decoder(&tlv(0x26, &[]))),
            ("IndexError".into(), "bytearray index out of range".into())
        );
        assert_eq!(
            err(decoder(&tlv(0x2a, &[1]))),
            ("IndexError".into(), "bytearray index out of range".into())
        );
        assert_eq!(
            err(decoder(&tlv(0x21, &[b'a', 0xff]))),
            (
                "UnicodeDecodeError".into(),
                "'ascii' codec can't decode byte 0xff in position 1: ordinal not in range(128)"
                    .into()
            )
        );
        assert_eq!(
            (hex(0xfdu8), hex(-5i128)),
            ("0xfd".to_string(), "-0x5".to_string())
        );
    }

    #[derive(Default)]
    struct Record {
        header: Option<(Option<String>, Option<u8>, Option<usize>)>,
        tlvs: Vec<(String, u8, u8, String)>,
        errors: Vec<String>,
        ended: bool,
    }

    impl Visitor for Record {
        fn visit_header(
            &mut self,
            id: Option<&str>,
            version: Option<u8>,
            len: Option<usize>,
        ) -> PyResult<()> {
            self.header = Some((id.map(str::to_string), version, len));
            Ok(())
        }
        fn visit_tlv(&mut self, name: &str, code: u8, length: u8, value: &str) -> PyResult<()> {
            self.tlvs.push((name.into(), code, length, value.into()));
            Ok(())
        }
        fn visit_end(&mut self, _data: &[u8]) -> PyResult<()> {
            self.ended = true;
            Ok(())
        }
        fn set_error(&mut self, error: &str) {
            self.errors.push(error.into());
        }
    }

    struct Nothing;
    impl Visitor for Nothing {}

    #[test]
    fn a_visit_stops_at_the_crc_or_at_the_first_bad_field() {
        let d = TlvInfoDecoder::new("/x", 0, "", true);
        let mut e = image_of(&[tlv(0x21, b"SN5600")], None);
        e.extend(tlv(0x22, b"after the CRC"));
        let mut r = Record::default();
        d.visit_eeprom(&e, &mut r).unwrap();
        assert_eq!(r.header, Some((Some("TlvInfo".into()), Some(1), Some(14))));
        assert_eq!(r.tlvs.iter().map(|t| t.1).collect::<Vec<_>>(), [0x21, 0xfe]);
        assert!(r.ended && r.errors.is_empty());
        // So does 0xFC, the code every Quanta field shares.
        let quanta = image_of(
            &[
                tlv(0x21, b"SN5600"),
                tlv(0xfc, &[0x12, 0x34]),
                tlv(0x22, b"after"),
            ],
            None,
        );
        let mut r = Record::default();
        d.visit_eeprom(&quanta, &mut r).unwrap();
        assert_eq!(r.tlvs.iter().map(|t| t.1).collect::<Vec<_>>(), [0x21, 0xfc]);
        assert!(r.ended && r.errors.is_empty());
        // A field running past the data.
        let mut bad = image_of(&[], None);
        bad[11..].copy_from_slice(&[0x21, 9, 0, 0, 0, 0]);
        let mut r = Record::default();
        d.visit_eeprom(&bad, &mut r).unwrap();
        assert_eq!(r.errors, ["Invalid TLV field starting at EEPROM offset 11"]);
        assert!(r.ended);
        // No TlvInfo header: an error, and nothing else.
        let mut r = Record::default();
        d.visit_eeprom(b"not an eeprom image", &mut r).unwrap();
        assert_eq!(
            r.errors,
            ["EEPROM does not contain data in a valid TlvInfo format."]
        );
        assert!(r.header.is_none() && !r.ended);
        // The default visitor does nothing with any of it.
        d.visit_eeprom(&e, &mut Nothing).unwrap();
        d.visit_eeprom(&bad, &mut Nothing).unwrap();
    }

    #[test]
    fn headers_and_checksums_are_checked_as_python_checks_them() {
        let good = image_of(&[tlv(0x21, b"SN5600")], None);
        let crc = crc32(&good[..good.len() - 4]);
        assert_eq!(is_checksum_valid(&good), (true, crc));
        assert_eq!(
            is_checksum_valid(&image_of(&[tlv(0x21, b"SN5600")], Some(1))),
            (false, crc)
        );
        assert_eq!(is_checksum_valid(&good[..good.len() - 1]), (false, 0));
        assert_eq!(is_checksum_valid(b"TlvInfo"), (false, 0));
        // The last field is not a CRC-32.
        let mut no_crc = good.clone();
        let n = no_crc.len();
        no_crc[n - 6] = TLV_CODE_PRODUCT_NAME;
        assert_eq!(is_checksum_valid(&no_crc), (false, 0));
        let mut v2 = good.clone();
        v2[8] = 2;
        assert!(!is_valid_tlvinfo_header(&v2));
        let mut huge = good.clone();
        huge[9] = 0x08;
        assert!(!is_valid_tlvinfo_header(&huge));
        assert!(!is_valid_tlv(&[0x21]));
        assert!(is_valid_tlv(&[0x21, 0]));
    }

    fn write_bytes(root: &crate::testing::Root, path: &str, bytes: &[u8]) {
        let p = root.real(path);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        std::fs::write(p, bytes).unwrap();
    }

    #[test]
    fn the_eeprom_is_read_from_its_start_header_first() {
        let root = crate::testing::Root::new();
        let path = "/sys/bus/i2c/devices/0-0051/eeprom";
        let d = TlvInfoDecoder::new(path, 3, "", true);
        assert_eq!(
            err(d.read_eeprom()),
            (
                "OSError".into(),
                format!("Failed to read eeprom : [Errno 2] No such file or directory: '{path}'")
            )
        );
        let e = image_of(&[tlv(0x21, b"SN5600")], None);
        write_bytes(
            &root,
            path,
            &[[0xaa, 0xbb, 0xcc].as_slice(), &e, b"trailing"].concat(),
        );
        assert_eq!(d.read_eeprom().unwrap(), e);
        // Not TlvInfo: the header alone.
        write_bytes(&root, path, b"...0123456789abcdef");
        assert_eq!(d.read_eeprom().unwrap(), b"0123456789a");
        // Shorter than the header says, or than a header.
        write_bytes(
            &root,
            path,
            &[[0, 0, 0].as_slice(), &e[..e.len() - 2]].concat(),
        );
        assert_eq!(
            err(d.read_eeprom()),
            (
                "RuntimeError".into(),
                format!(
                    "Expected to read {} bytes from {path}, but only read {}",
                    e.len() - 11,
                    e.len() - 13
                )
            )
        );
        write_bytes(&root, path, b"...Tlv");
        assert_eq!(
            err(d.read_eeprom()),
            (
                "RuntimeError".into(),
                format!("Expected to read 11 bytes from {path}, but only read 3")
            )
        );
    }

    #[test]
    fn syseepromd_s_fields_reach_state_db_in_byte_order() {
        use crate::testing::{FakeRedis, STATE_DB};
        let root = crate::testing::Root::new();
        let redis = FakeRedis::get();
        redis.install(&root);
        let e = image_of(
            &[tlv(0x21, b"SN5600"), tlv(0xfd, &[1, 2]), tlv(0xfd, &[3])],
            None,
        );
        let d = TlvInfoDecoder::new("/x", 0, "", true);
        assert_eq!(d.update_eeprom_db(&e).unwrap(), 0);
        let fields = |k: &str| redis.hgetall(STATE_DB, k);
        let pairs = |v: &[(&str, &str)]| {
            v.iter()
                .map(|(a, b)| (a.to_string(), b.to_string()))
                .collect::<Vec<_>>()
        };
        assert_eq!(
            fields("EEPROM_INFO|TlvHeader"),
            pairs(&[
                ("Id String", "TlvInfo"),
                ("Total Length", &(e.len() - 11).to_string()),
                ("Version", "1")
            ])
        );
        assert_eq!(
            fields("EEPROM_INFO|0x21"),
            pairs(&[("Len", "6"), ("Name", "Product Name"), ("Value", "SN5600")])
        );
        assert_eq!(
            fields("EEPROM_INFO|0xfd"),
            pairs(&[
                ("Len_0", "2"),
                ("Name_0", "Vendor Extension"),
                ("Value_0", "0x01 0x02"),
                ("Len_1", "1"),
                ("Name_1", "Vendor Extension"),
                ("Value_1", "0x03"),
                ("Num_vendor_ext", "2"),
            ])
        );
        assert_eq!(fields("EEPROM_INFO|Checksum"), pairs(&[("Valid", "1")]));
        assert_eq!(fields("EEPROM_INFO|State"), pairs(&[("Initialized", "1")]));
        // A bad checksum is published as such; no TlvInfo at all is a -1.
        assert_eq!(d.update_eeprom_db(&image_of(&[], Some(7))).unwrap(), 0);
        assert_eq!(fields("EEPROM_INFO|Checksum"), pairs(&[("Valid", "0")]));
        assert_eq!(d.update_eeprom_db(b"garbage").unwrap(), -1);
        redis.hset(STATE_DB, "EEPROM_INFO|0x23", &[("Value", "MT1\0\0")]);
        assert_eq!(
            d.redis_hget("EEPROM_INFO|0x23", "Value")
                .unwrap()
                .as_deref(),
            Some("MT1")
        );
        assert_eq!(d.redis_hget("EEPROM_INFO|0x23", "nope").unwrap(), None);
    }

    #[test]
    fn a_tlvinfo_image_decodes_the_way_python_decodes_it() {
        let e = image();
        assert!(is_valid_tlvinfo_header(&e));
        assert!(is_checksum_valid(&e).0);
        let d = TlvInfoDecoder::new("/x", 0, "", true);
        let mut c = Collect(Vec::new());
        d.visit_eeprom(&e, &mut c).unwrap();
        assert_eq!(c.0[0], ("Product Name".into(), 0x21, "SN5600".into()));
        assert_eq!(
            c.0[1],
            ("Base MAC Address".into(), 0x24, "1C:34:DA:0A:BC:DE".into())
        );
        assert_eq!(
            c.0[2],
            ("Vendor Extension".into(), 0xfd, "0x00 0x00 0x81".into())
        );
        assert_eq!(c.0[3].0, "CRC-32");
        assert_eq!(hex(0x21u8), "0x21");
        assert_eq!(crc32(b"123456789"), 0xCBF4_3926);
    }
}
