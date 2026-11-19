use empack_core::digest::ContentId;
use empack_core::files::{FileCapabilities, FileContent, FilePermissions, ObservedPath};
use empack_core::instance::{FileDecision, FilePolicy, InstalledFile, ReleaseFile, plan_file};
fn content(id: u8) -> FileContent {
    FileContent {
        content: ContentId::from_sha256([id; 32]),
        bytes: 1,
        permissions: FilePermissions {
            readonly: false,
            executable: false,
        },
    }
}
fn content_id(file: &FileContent) -> u8 {
    (0..3)
        .find(|&id| content(id) == *file)
        .expect("unexpected file content")
}
fn record(n: u8) -> Option<(FileContent, FilePolicy)> {
    if n == 0 {
        None
    } else {
        Some((
            content((n - 1) % 3),
            if n <= 3 {
                FilePolicy::Managed
            } else {
                FilePolicy::Seed
            },
        ))
    }
}
fn main() {
    for old in 0..7 {
        for live in 0..5 {
            for next in 0..7 {
                let prior =
                    record(old).map(|(baseline, policy)| InstalledFile { baseline, policy });
                let path = match live {
                    0 => ObservedPath::Absent,
                    1 => ObservedPath::Directory,
                    _ => ObservedPath::File(content(live - 2)),
                };
                let incoming =
                    record(next).map(|(content, policy)| ReleaseFile { content, policy });
                let plan = plan_file(
                    prior.as_ref(),
                    &path,
                    incoming.as_ref(),
                    FileCapabilities {
                        executable_bits: true,
                    },
                );
                let name = match plan {
                    FileDecision::Create(file) => format!("Create{}", content_id(&file)),
                    FileDecision::Replace(file) => format!("Replace{}", content_id(&file)),
                    FileDecision::Conflict(c) => format!("{c:?}"),
                    other => format!("{other:?}"),
                };
                println!("{old} {live} {next} {name}");
            }
        }
    }
}
