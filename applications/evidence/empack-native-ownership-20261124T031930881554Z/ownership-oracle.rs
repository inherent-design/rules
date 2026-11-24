//! Owner-run oracle over the actual dependency-free empack-core library.
//! Synthetic content IDs are equality labels, not verified native file bytes.
use empack_core::{
    digest::ContentId,
    files::{FileCapabilities, FileContent, FilePermissions, ObservedPath},
    instance::{FileConflict, FileDecision, FilePolicy, InstalledFile, ReleaseFile, plan_file},
};

fn content(id: u8, readonly: bool, executable: bool) -> FileContent {
    FileContent {
        content: ContentId::from_sha256([id; 32]),
        bytes: 1,
        permissions: FilePermissions { readonly, executable },
    }
}

fn decision(value: FileDecision) -> &'static str {
    match value {
        FileDecision::Unchanged => "unchanged",
        FileDecision::Preserve => "preserve",
        FileDecision::Create(after) => { assert_eq!(after, content(2, false, false)); "create" }
        FileDecision::Replace(after) => { assert_eq!(after, content(2, false, false)); "replace" }
        FileDecision::Remove => "remove",
        FileDecision::Conflict(reason) => match reason {
            FileConflict::UnownedDestination => "unowned",
            FileConflict::ModifiedManagedFile => "modified",
            FileConflict::WrongKind => "wrong-kind",
            FileConflict::SeedOwnership => "seed-ownership",
        },
    }
}

fn main() {
    let mut observations = vec![(0, 0, false, false, ObservedPath::Absent),
                                (1, 0, false, false, ObservedPath::Directory)];
    for id in 1..=3 {
        for readonly in [false, true] {
            for executable in [false, true] {
                observations.push((2, id, readonly, executable,
                                   ObservedPath::File(content(id, readonly, executable))));
            }
        }
    }
    for previous in 0..=2 {
        let prior = match previous {
            0 => None,
            policy => Some(InstalledFile {
                baseline: content(1, false, false),
                policy: if policy == 1 { FilePolicy::Managed } else { FilePolicy::Seed },
            }),
        };
        for incoming in 0..=2 {
            let next = match incoming {
                0 => None,
                policy => Some(ReleaseFile {
                    content: content(2, false, false),
                    policy: if policy == 1 { FilePolicy::Managed } else { FilePolicy::Seed },
                }),
            };
            for (kind, id, readonly, executable, current) in &observations {
                for executable_bits in [false, true] {
                    let result = plan_file(prior.as_ref(), current, next.as_ref(), FileCapabilities { executable_bits });
                    println!("{previous}\t{incoming}\t{kind}\t{id}\t{readonly}\t{executable}\t{executable_bits}\t{}", decision(result));
                }
            }
        }
    }
}
