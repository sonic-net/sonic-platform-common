//! The native platform API of a build that carries none.
//!
//! `platform-provider` always has a native arm, so `--platform-api native`
//! parses on every image.  Which crate answers it is chosen when the image is
//! built: a vendor ships a crate named `platform-native` with the same two
//! items as this one, and the image builds the provider from a copy in which
//! the vendor's crate sits where this one does -- sonic-buildimage assembles
//! that copy per platform.  Every other build gets this crate, which cannot be
//! opened: [`Platform`] has no values, and [`open`] says why.

use platform_api::{PlatformApi, PlatformError};

/// A platform no build of this crate can construct.
///
/// Uninhabited rather than a unit struct, so that nothing -- a test, a later
/// edit to [`open`] -- can produce one and reach the trait's defaults, which
/// would answer every snapshot with an empty list instead of an error.
pub enum Platform {}

/// Every method keeps the trait's default; none of them can be reached,
/// because there is no `Platform` to call it on.
impl PlatformApi for Platform {}

/// Refuse.
///
/// The text is what an operator reads from a daemon that would not start, so
/// it names the cause: the switch asked for an implementation this image was
/// not built with.  It is the text the provider gave before this crate
/// existed, so a log search written against that still finds it.
pub fn open(_syslog_ident: &str) -> Result<Platform, PlatformError> {
    Err(PlatformError::NotSupported(
        "the native platform API is not compiled into this build".to_string(),
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_build_without_a_native_implementation_refuses_and_says_why() {
        match open("thermalctld") {
            Err(PlatformError::NotSupported(m)) => {
                assert_eq!(m, "the native platform API is not compiled into this build")
            }
            Err(e) => panic!("expected NotSupported, got {e:?}"),
            Ok(p) => match p {},
        }
    }
}
