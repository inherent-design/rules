// Selected empack source; Apache-2.0. See ../../sources/licenses/empack-Apache-2.0.txt.
use crate::{Cancellation, Context, Result};
use std::io::{Read, Seek, SeekFrom};
#[derive(Debug, Clone, Copy)]
pub struct ArchiveLimits {
    pub compressed_bytes: u64,
    pub file_bytes: u64,
    pub total_bytes: u64,
    pub entries: usize,
    pub depth: usize,
}
impl Default for ArchiveLimits {
    fn default() -> Self {
        Self {
            compressed_bytes: 64 * 1024 * 1024 * 1024,
            file_bytes: 8 * 1024 * 1024 * 1024,
            total_bytes: 64 * 1024 * 1024 * 1024,
            entries: 100_000,
            depth: 128,
        }
    }
}
pub trait ArchiveRead: Read + Seek {}
impl<T: Read + Seek> ArchiveRead for T {}

pub(super) fn preflight_zip(
    source: &mut dyn ArchiveRead,
    size: u64,
    limits: ArchiveLimits,
    cancel: &Cancellation,
) -> Result<()> {
    let count = size.min(65535 + 22) as usize;
    source.seek(SeekFrom::End(-(count as i64)))?;
    let mut tail = vec![0; count];
    source.read_exact(&mut tail)?;
    let eocd = (0..count.saturating_sub(21))
        .rev()
        .find(|&offset| {
            tail[offset..].starts_with(b"PK\x05\x06")
                && offset
                    + 22
                    + usize::from(u16::from_le_bytes([tail[offset + 20], tail[offset + 21]]))
                    == count
        })
        .ok_or_else(|| anyhow::anyhow!("Missing ZIP end record"))?;
    let u16_at = |offset: usize| u16::from_le_bytes([tail[eocd + offset], tail[eocd + offset + 1]]);
    let u32_at = |offset: usize| {
        u32::from_le_bytes(tail[eocd + offset..eocd + offset + 4].try_into().unwrap())
    };
    ensure!(
        u16_at(4) == 0 && u16_at(6) == 0,
        "Multi-disk ZIP is unsupported"
    );
    let mut entries = u64::from(u16_at(10));
    let mut central_size = u64::from(u32_at(12));
    let mut central = u64::from(u32_at(16));
    let end_position = size - count as u64 + eocd as u64;
    let mut directory_boundary = end_position;
    let mut zip64_extension_bytes = 0;
    if entries == u64::from(u16::MAX)
        || central_size == u64::from(u32::MAX)
        || central == u64::from(u32::MAX)
    {
        ensure!(end_position >= 20, "Invalid ZIP64 locator");
        source.seek(SeekFrom::Start(end_position - 20))?;
        let mut locator = [0u8; 20];
        source.read_exact(&mut locator)?;
        ensure!(
            locator[..4] == *b"PK\x06\x07"
                && locator[4..8] == [0; 4]
                && u32::from_le_bytes(locator[16..20].try_into().unwrap()) == 1,
            "Invalid ZIP64 locator"
        );
        let record_position = u64::from_le_bytes(locator[8..16].try_into().unwrap());
        let locator_position = end_position - 20;
        ensure!(
            record_position
                .checked_add(56)
                .is_some_and(|end| end <= locator_position),
            "ZIP64 end record exceeds locator bounds"
        );
        source.seek(SeekFrom::Start(record_position))?;
        let mut record = [0u8; 56];
        source.read_exact(&mut record)?;
        ensure!(
            record[..4] == *b"PK\x06\x06" && record[16..24] == [0; 8],
            "Invalid ZIP64 end record"
        );
        let record_size = u64::from_le_bytes(record[4..12].try_into().unwrap());
        ensure!(record_size >= 44, "ZIP64 end record is too short");
        let record_end = record_position
            .checked_add(12)
            .and_then(|position| position.checked_add(record_size))
            .context("ZIP64 end record size overflow")?;
        ensure!(
            record_end == locator_position,
            "ZIP64 end record length disagrees with its locator"
        );
        zip64_extension_bytes = record_size - 44;
        directory_boundary = record_position;
        entries = u64::from_le_bytes(record[32..40].try_into().unwrap());
        central_size = u64::from_le_bytes(record[40..48].try_into().unwrap());
        central = u64::from_le_bytes(record[48..56].try_into().unwrap());
    }
    ensure!(
        entries <= limits.entries as u64,
        "Archive exceeds entry limit"
    );
    // Bound both the name index input and ZIP64 extensible data before
    // ZipArchive allocates either. Compressed-byte admission is not a metadata bound.
    ensure!(
        central_size
            .checked_add(zip64_extension_bytes)
            .is_some_and(|bytes| bytes <= 16 * 1024 * 1024),
        "ZIP metadata exceeds 16 MiB limit"
    );
    let central_end = central
        .checked_add(central_size)
        .ok_or_else(|| anyhow::anyhow!("ZIP directory overflow"))?;
    ensure!(
        central_end <= directory_boundary,
        "ZIP directory extends beyond its end record"
    );
    source.seek(SeekFrom::Start(central))?;
    let mut names = std::collections::BTreeSet::new();
    for _ in 0..entries {
        cancel.check()?;
        let mut header = [0u8; 46];
        source.read_exact(&mut header)?;
        ensure!(
            header[..4] == *b"PK\x01\x02",
            "Invalid ZIP central directory member"
        );
        let length = usize::from(u16::from_le_bytes(header[28..30].try_into().unwrap()));
        let extra = u16::from_le_bytes(header[30..32].try_into().unwrap());
        let comment = u16::from_le_bytes(header[32..34].try_into().unwrap());
        let mut name = vec![0; length];
        source.read_exact(&mut name)?;
        // A declared UTF-8 name cannot silently become a CP437 path in a new decoder.
        let flags = u16::from_le_bytes(header[8..10].try_into().unwrap());
        if flags & (1 << 11) != 0 {
            std::str::from_utf8(&name)
                .context("ZIP member declares UTF-8 but has invalid name bytes")?;
        }
        ensure!(names.insert(name), "Duplicate ZIP central directory member");
        source.seek(SeekFrom::Current(i64::from(extra) + i64::from(comment)))?;
        ensure!(
            source.stream_position()? <= central_end,
            "ZIP member exceeds directory bounds"
        );
    }
    ensure!(
        source.stream_position()? == central_end,
        "ZIP directory count differs from its records"
    );
    Ok(())
}
