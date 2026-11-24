# restic restore policy and target effects

Restore success means that restic completed the selected operation. It does not mean every existing target file matches the snapshot. This band compares restic 0.20.0 on the pinned macOS arm64 profile across overwrite policy, verification scope, filtered deletion, dry-run output, and one owned symlink control.

## Domain and native procedure

The snapshot owns recorded paths, file bytes, and metadata. The target has independently existing nodes and content. Selection, overwrite admission, content reuse, metadata restoration, deletion, and post-restore verification are different operations. A directory's deletion scope also matters: selecting a parent for recursive deletion can affect children that would not be selected independently.

The [collector](restore_probe.py) creates a new private repository and one generated snapshot containing three regular files and one directory. All file modification times are fixed; each restore gets a distinct fresh target. There are no user backups, personal files, remote services, or shared target directories. The explicit snapshot-subtree selector removes the source's absolute prefix from the destination layout. Patterns in this band are relative to that selected subtree, as the owning documentation specifies.

The [receipt](../evidence/restic-restore-20261124T123833241400Z/receipt.json) and [trace](../evidence/restic-restore-20261124T123833241400Z/trace.json) contain 20 native commands: help, repository initialization, backup, and 17 restore cases. The publisher-checksummed binary is revalidated before use. All 20 command processes were reaped, no lock remains, and the measured source image is unchanged. Repository/build correspondence is not reproduced by this experiment.

## Overwrite and verification results

The changed target file has different bytes but the same length as the snapshot. Its timestamp is equal, older, or newer according to the selected control. The other two files initially match. File bytes and timestamps are observed independently of the command status.

| Request and target                                         | Observed target content            | Status |
| ---------------------------------------------------------- | ---------------------------------- | ------ |
| Empty target, default `always --verify`                    | All three files match the snapshot | 0      |
| Existing changed file, `never --verify`                    | Existing changed bytes retained    | 0      |
| Changed bytes with equal size/mtime, `if-changed --verify` | Existing changed bytes retained    | 0      |
| Same target, `always --verify`                             | Snapshot bytes restored            | 0      |
| Older changed target, `if-newer --verify`                  | Snapshot bytes restored            | 0      |
| Newer or equal-mtime changed target, `if-newer --verify`   | Existing changed bytes retained    | 0      |
| Changed target with different mtime, `if-changed --verify` | Snapshot bytes restored            | 0      |

These results match the documented fast path. `if-changed` trusts equal size and mtime; it is not a byte comparison in that case. `if-newer` compares strictly, so equality does not authorize replacement. `never` preserves an existing file, while the model/source allow creating a missing one. The latter rule is source-modeled here; the empty native target uses `always`.

`VerifyFiles` only queues tracked regular files that were restored with content work. Policy-skipped files and metadata-only files are excluded. Therefore `--verify` does not override the chosen overwrite policy or independently audit every retained file. The same-size/mtime control deliberately demonstrates this boundary. This is expected policy, not a newly discovered authentication failure or a claim about arbitrary corruption recovery. No native read counter was instrumented; verification eligibility comes from the inspected source, while final bytes and status are native observations.

The JSON summary also counts directories in its restored-file total. The matching-content cases report one restored entry and three skipped files because the directory's metadata is restored. The pinned upstream tests and dry-run documentation explicitly include files/directories in these progress counts. Do not infer that an existing regular file's content was rewritten from that total alone.

## Selection and recursive deletion

Each deletion fixture starts with the correct snapshot files plus `extra.txt` and an unexpected `extra/` directory containing `protected.txt` and `unselected.txt`.

| Request                                                 | Observed extra target nodes                                                                           |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `--delete`                                              | All extras removed                                                                                    |
| `--delete --exclude /extra.txt`                         | Root extra file retained; extra directory and children removed                                        |
| `--delete --exclude /extra/protected.txt`               | Extra directory and both children removed, including the excluded child                               |
| `--delete --exclude /extra`                             | Directory and both children retained; root extra file removed                                         |
| `--delete --include /alpha.txt`                         | All extras retained                                                                                   |
| `--delete --exclude /extra/protected.txt --dry-run -vv` | Entire measured target image unchanged; output lists the planned deletions, including `protected.txt` |

The child-exclusion result is reproduced and follows the source: `removeUnexpectedFiles` applies `SelectFilter` to the unexpected entry, collects that directory's descendants, and calls `RemoveAll`. It does not reapply the filter at every descendant. Root-file and whole-directory exclusion controls establish that the general filter is active.

Importantly, the pinned `TestRestoreDelete` explicitly expects an unexpected selected directory and its child to be deleted even when the supplied filter does not independently select the child. This is a tested subtree-selection policy at the internal API, rather than an accidental ignored filter. The CLI's child-exclusion result remains surprising, but classifying it as an obvious implementation regression would discard that evidence. A stricter child-preserving rule needs an explicit compatibility decision.

The [model](Restore.lean) keeps current recursive deletion separate from a proposed leaf-aware alternative. In the alternative, retaining the excluded child retains its parent, while the eligible sibling can still be removed. It is a tiny fixed-tree decision model, not an implemented recursive filesystem algorithm. General directory traversal, reparse points, aliases, hardlinks, permission failures, interrupted deletion, and concurrent target mutation remain unqualified. A real implementation must use admitted target observations and existing no-follow/path checks; it cannot safely substitute unrestricted path strings for those witnesses.

## Refusal and symlink controls

Combining include and exclude flags, or combining dry-run and verify, returns status 1 before changing the measured target. Those refusals name the incompatible options. They are useful existing behavior to preserve.

In one owned leaf-symlink case, `always --verify` replaces the target symlink with the snapshot's regular file and leaves the separate owned canary's hash unchanged. This does not qualify arbitrary symlink traversal, target-root replacement, hostile filesystems, Windows reparse points, or concurrent path races. No live link into personal data is created.

The pinned restore guide also overstates a root guard: it says `--target` with `--delete` requires an include or exclude, while the command's actual guard is specifically for cleaned target `/`. The generated non-root `--delete` case succeeds without filters. A documentation correction should name `/`; no test was run against the host root.

## Source, laws, and replay

[Four pinned sources](../sources/restic-restore-selections.json) identify revision `9c88ff768f10c192dc6a87619a65a16374080e33`, inspected ranges, and bytes. They cover the CLI, restorer policy/verification/deletion code, owning guide, and relevant upstream tests. The upstream Go tests were read, not executed. Cached third-party sources and the encrypted fixture repository remain outside Git.

[Lean](Restore.lean) proves 20 laws, and [Bend](Restore.bend) checks eight. Their per-file model distinguishes missing, matching, changed, and symlink targets; timestamp order; policy admission; metadata reuse; content replacement; and source-derived verification eligibility. Their fixed extra-tree model distinguishes root selection, parent selection, child selection, and recursive removal. It proves the current child-exclusion counterexample and the separately proposed preservation rule. These proofs depend on supplied content/time/filter witnesses and successful local operations; they do not implement restic's codecs, blob loading, filter grammar, metadata APIs, or filesystem authority.

The [pure replay](restore_conformance.py) matches both executable models against all 17 retained restore outcomes. It compares actual final file identity, presence of the four extra nodes, and exit status; it also checks untouched secondary file bytes, dry/refusal target images, the canary hash, producer/stream/source identities, and seven research-decoder refusals. Verification eligibility is deliberately not presented as a native measured read count.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/restic/restore_conformance.py \
  applications/evidence/restic-restore-20261124T123833241400Z
```

Compile `Restore.lean` into `.build/formal/applications/restic/Restore.olean` first. Ordinary CI runs pure rules, not the collector or restore commands. The replay's raw stream attribution requires retained ignored owner-local originals. Public streams mask the OS user/host as in the earlier restic bands. About 432 KiB of private repository, targets, cache, password, and originals are retained; no old evidence or recovery data is deleted.

## Per-application decisions and compatibility

Preserve overwrite choices and their documented performance tradeoff. Improve a completion summary to distinguish restored content, updated metadata/directories, and files intentionally skipped by policy. A verification result should identify that restored-file scope rather than imply an audit of all existing content. Reuse the existing progress and tracked-file information; do not add another content engine. Keep existing JSON field meanings stable, using an explicitly reviewed additive field or opt-in report if finer counts are required. Keeping current output with precise operator guidance is reasonable. Falsify a new summary with metadata-only changes, mixed skipped/restored files, hardlinks, partial failures, and larger multi-blob files.

For deletion, preserve the existing whole-directory rule unless a selected design changes it. At minimum, document that excluding a child does not protect it when its unexpected parent is recursively removed, and keep the current `--dry-run -vv` guidance. The stricter alternative should build one deletion plan through the existing filter, preserve excluded descendants and necessary ancestors, and apply only confirmed eligible removals. It must define empty-directory policy and failures with partial effects. Existing internal tests and callers make that a compatibility change, potentially suited to an explicit deletion mode rather than a silent replacement. No repository-schema migration is implied; CLI behavior, filter consumers, deletion progress, and retries do require review. No alternative was applied to a native target in this band.

For empack, retain its own managed/seed/unowned and world-group rules. Restic's timestamp trust, overwrite modes, or selected-directory deletion do not authorize broadening empack mutation rights. A grouped destructive operation must make its descendant scope explicit and preserve unrelated owned content under its own contract. The useful comparison is selection versus mutation scope and the basis of a completion claim, not adopting another program's defaults.

Full restore qualification still needs metadata/ACLs/xattrs, ownership mapping, hardlinks, sparse and large files, unavailable data/keys, backend failures, concurrent targets, interrupted publication, alternate hosts, and meaningful application-consistency checks. No production code changed, no user backup was restored, and no entire feature family is qualified.
