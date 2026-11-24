# restic: file capture and snapshot publication

This band studies restic 0.20.0 on macOS arm64 using a new local repository and generated files. It separates a parent snapshot's content, live source metadata, rereading, deduplication, the resulting tree, and publication. It does not open a user backup or qualify a live filesystem as an atomic snapshot.

## Source and native basis

The [source ledger](../sources/restic-backup-selections.json) pins three files at `9c88ff768f10c192dc6a87619a65a16374080e33`: the archiver, backup command, and backup guide. The selected binary matches the previously retained official asset identity; correspondence to a reproducible source build is not established.

The [collector](backup_probe.py) owns the new repository, password, source, cache, and processes. Its [receipt](../evidence/restic-backup-20261124T140738773237Z/receipt.json) records 38 commands and 14 backup cases. Explicit parent IDs prevent unrelated later backups from changing the comparison basis. `--force` deliberately overrides that parent selection. Each published result is inspected through a fresh `ls` and `dump` invocation, alongside independent repository snapshot-entry observations. Source bytes and measured mode, inode, size, mtime, and ctime remain unchanged during each command; the producer alone stages the differences between commands.

| Case                                                  | Resulting main-file bytes                  | New saved snapshot | Status |
| ----------------------------------------------------- | ------------------------------------------ | ------------------ | ------ |
| First backup                                          | Original                                   | Yes                | 0      |
| Unchanged file                                        | Original                                   | Yes                | 0      |
| Equal-size edit with restored mtime, default policy   | Modified                                   | Yes                | 0      |
| Same edit with `--ignore-ctime`                       | **Original**                               | Yes                | 0      |
| Same edit with forced reread                          | Modified                                   | Yes                | 0      |
| New inode with restored size/mtime, ignore ctime only | Modified                                   | Yes                | 0      |
| Same replacement with `--ignore-inode`                | **Original**                               | Yes                | 0      |
| Changed mtime despite `--ignore-inode`                | Modified                                   | Yes                | 0      |
| Added unreadable file                                 | Modified main file; unreadable file absent | **Yes, partial**   | **3**  |
| Explicitly excluded unreadable file                   | Modified main file; excluded file absent   | Yes                | 0      |
| Forced dry-run                                        | No saved-content claim                     | No                 | 0      |
| Fresh forced baseline                                 | Modified                                   | Yes                | 0      |
| Identical tree with `--skip-if-unchanged`             | No new saved-content claim                 | No                 | 0      |
| Missing root                                          | No capture                                 | No                 | 1      |

The ctime and inode controls matter independently. The first edit preserves the original inode, size, and mtime while ctime changes. The replacement retains size/mtime but has a different inode. The fixture verifies these facts before interpreting the policies. In the two old-content results, the emitted node nevertheless contains current measured metadata, including ctime and inode. An apparently fresh metadata record therefore does not establish that its content was freshly read.

The forced reread reports zero new data blobs because those modified bytes were already present from a prior case. This is not evidence of skipped reading. New data, processed bytes, fresh source reads, and published references measure different things. Syscall counts and chunk boundaries were not instrumented.

The partial case emits a structured archival error and exit error on stderr, while stdout supplies a snapshot summary and ID. A fresh reader confirms the new snapshot contains the good file and omits the unreadable file. This is useful retained work with an explicit incomplete result. The excluded-file control reports success because that file is outside the requested selection; it does not prove all files in the source directory were captured.

The dry-run summary also contains `snapshot_id`, marked `dry_run: true`, while the repository's snapshot set remains unchanged. The token describes a simulated result, not a saved reference. An unchanged-skip result has neither a new entry nor a snapshot ID. The missing-root path emits one plain warning before its structured exit error; this stderr stream is not wholly JSON Lines.

## Policy and models

The [backup guide](https://github.com/restic/restic/blob/9c88ff768f10c192dc6a87619a65a16374080e33/doc/040_backup.rst#file-change-detection) documents metadata-based reuse and its overrides. Preserve that explicit performance policy rather than calling the ignore-metadata cases corruption. This profile is Unix-specific; the documented Windows policy has different premises and was not run here.

[Lean](Backup.lean) checks 18 laws; [Bend](Backup.bend) checks nine. The capture model treats metadata equality as a reuse decision, independently of live-byte identity. The source also requires indexed prior blobs before reuse. Missing index membership disables reuse in the model; this fixture did not damage an index or qualify that recovery path. A successful read is an admitted immutable content identity, not a complete file reader or race-detection algorithm.

The publication model separates a refused attempt, planned dry-run, unchanged skip, and saved reference. Partial source errors can accompany publication and status 3. Fatal refusal does not imply that all repository/cache state is unchanged: this model does not account for unreferenced blobs or partial uploads. Exact tree equality, not only identical main-file bytes, controls unchanged skipping.

The [comparison](backup_conformance.py) checks both models against the [14 retained outcomes](../evidence/restic-backup-20261124T140738773237Z/conformance.json), verifies current node metadata in 11 saved snapshots, and refuses three malformed research inputs. Model reuse decisions are source interpretations; native byte, metadata, entry, status, and reported-ID observations are kept separate. For dry-run/skip, modeled content is not presented as an observed saved payload. Fresh Lean compilation prevents stale imported artifacts. Replay invokes no restic, native fixture, or network.

The [projection disposition](../evidence/restic-backup-20261124T140738773237Z/disposition.json) records a harness correction before publication: the first assembled observation table included raw local account fields from `ls`. Its original bytes remain private, and the public table now applies the captured stream redactor. Native results did not change or rerun. The reusable producer applies that redaction when writing future tables. Raw/public equivalence requires owner-local originals; public readers can inspect the retained redacted streams and their identities.

## Decisions and verification plan

Preserve restic's explicit metadata policy, forced reread, selection, partial snapshot retention, and unchanged suppression. No product defect or production patch is selected by these results.

A useful reporting refinement would distinguish reused content from reread content and new stored data, and label simulated snapshot tokens consistently in human and machine output. Existing `dry_run`, summary, archival errors, and exit code already provide much of the needed information. Reuse them rather than inventing a second backup state machine. Review existing JSON consumers before adding or renaming fields; a wrapper should never announce a saved backup from `snapshot_id` alone.

For empack's proposed source capture, a saved image needs exact retained content identities and attributed read/capture evidence. Backup-oriented metadata reuse is not automatically suitable for validating a publisher input or authorizing an old prepared write. Keep this comparison separate from empack's current seed-preservation policy: preserving destination bytes needs different observations from publishing new source bytes. The result motivates an explicit operation-specific capture policy, not copying restic's flags into empack.

Further qualification needs source mutation during reads, missing parent/index data, multiple files/chunks, interruptions, failed publication, unreadable directories, file-type replacement, symlinks, metadata failures, real exclusions, and remote acknowledgements. Establish whether a candidate represents a stable captured image or a documented best-effort live read. Do not claim rollback, durable remote publication, or whole-source completeness from these small local cases. Broader backup, recovery, and joined retention/restore work remain pending in the inventory.
