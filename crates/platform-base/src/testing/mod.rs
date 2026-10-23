//! Test doubles: a scratch filesystem root, and stand-ins for the tools and
//! services platform code talks to.  Built for this crate's tests, and for a
//! vendor crate's with the `testing` feature.

mod curl;
mod redis;
mod root;

pub use curl::{Answer, FakeCurl};
pub use redis::{FakeRedis, CONFIG_DB, STATE_DB};
pub use root::Root;
