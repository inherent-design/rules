//! Study adapters around an unchanged raw ZIP preflight function and actual core path APIs.
//! No ZIP payload decoder, extraction capability, engine, or crypto witness is constructed here.
extern crate self as anyhow;
use std::{cell::Cell, error::Error, fmt, io::{self, Cursor, Read, Seek, SeekFrom}};
use empack_core::path::{ArchiveMemberName, PathSyntax, PortableRelPath};

pub type Result<T> = std::result::Result<T, Box<dyn Error>>;
#[derive(Debug)]
struct Message(String);
impl fmt::Display for Message {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { f.write_str(&self.0) }
}
impl Error for Message {}
pub fn message(value: String) -> Box<dyn Error> { Box::new(Message(value)) }
#[macro_export]
macro_rules! anyhow { ($($arg:tt)*) => { $crate::message(format!($($arg)*)) }; }
#[macro_export]
macro_rules! ensure { ($test:expr, $($arg:tt)*) => { if !$test { return Err($crate::anyhow!($($arg)*)); } }; }
pub trait Context<T> { fn context(self, text: &str) -> Result<T>; }
impl<T, E: fmt::Display> Context<T> for std::result::Result<T, E> {
    fn context(self, text: &str) -> Result<T> { self.map_err(|e| message(format!("{text}: {e}"))) }
}
impl<T> Context<T> for Option<T> {
    fn context(self, text: &str) -> Result<T> { self.ok_or_else(|| message(text.into())) }
}

// Source-compatible check callback, not empack's native Cancellation implementation.
pub struct Cancellation { after: Option<usize>, checks: Cell<usize> }
impl Cancellation {
    pub fn check(&self) -> Result<()> {
        let n = self.checks.get(); self.checks.set(n + 1);
        if self.after.is_some_and(|limit| n >= limit) {
            Err(message("fixture cancellation check refused".into()))
        } else { Ok(()) }
    }
}
#[path = "fragments.rs"] mod fragments;
#[path = "pathcases.rs"] mod pathcases;
struct Traced {
    input: Cursor<Vec<u8>>, bytes: usize, largest: usize, seeks: usize,
}
impl Read for Traced {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        self.largest = self.largest.max(buffer.len());
        let count = self.input.read(buffer)?; self.bytes += count; Ok(count)
    }
}
impl Seek for Traced {
    fn seek(&mut self, seek: SeekFrom) -> io::Result<u64> { self.seeks += 1; self.input.seek(seek) }
}

fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    match args.get(1).map(String::as_str) {
        Some("paths") => {
            for (id, bytes) in pathcases::cases() {
                let input = std::str::from_utf8(&bytes)?;
                let opaque = ArchiveMemberName::parse(input);
                let portable = PortableRelPath::parse(input, PathSyntax::ArchiveMember);
                if let Ok(ref name) = opaque { assert_eq!(name.as_str(), input); }
                if let Ok(ref path) = portable { assert_eq!(path.as_str(), input); }
                println!("{id}\t{}\t{}\t{}\t{}", opaque.is_ok(), portable.is_ok(),
                    opaque.err().map(|e| format!("{e:?}")).unwrap_or_default(),
                    portable.err().map(|e| format!("{e:?}")).unwrap_or_default());
            }
        }
        Some("preflight") => {
            let bytes = std::fs::read(args.get(2).ok_or_else(|| message("ZIP path required".into()))?)?;
            ensure!(bytes.len() <= 65536, "Study inputs are bounded to 64 KiB");
            let size = bytes.len() as u64;
            let entries = args.get(3).ok_or_else(|| message("Entry limit required".into()))?.parse()?;
            let after: i64 = args.get(4).ok_or_else(|| message("Cancellation check index required".into()))?.parse()?;
            let cancel = Cancellation { after: if after < 0 { None } else { Some(after as usize) }, checks: Cell::new(0) };
            let mut reader = Traced { input: Cursor::new(bytes), bytes: 0, largest: 0, seeks: 0 };
            let limits = fragments::ArchiveLimits { entries, ..Default::default() };
            let result = fragments::preflight_zip(&mut reader, size, limits, &cancel);
            let error = result.as_ref().err().map(ToString::to_string).unwrap_or_default().replace(['\n', '\t'], " ");
            println!("{}\t{}\t{}\t{}\t{}\t{error}", result.is_ok(), cancel.checks.get(), reader.bytes, reader.largest, reader.seeks);
        }
        _ => return Err(message("Use paths or preflight FILE ENTRIES CANCEL_AFTER".into())),
    }
    Ok(())
}
