# Association initialization, interruption, and retry

This intermediate source/native protocol band follows [state discovery](ROOT-STATE.md) at empack source `0b4462e3032b4f09230b15329722eabefb7f574c`. It executes the complete selected association initializer through a controlled child-termination boundary. It reproduces a stranded initialization slot in the current source and tests a private candidate against that window. Formal trace models and comparison remain pending; no production change is selected.

## Scope and provenance

The [collector](initializer_probe.py), [caller](initializer_oracle.rs), and [ledger](../sources/empack-initializer-selections.json) retain 12 source pins. The [receipt](../evidence/empack-initializer-20261124T205241728563Z/receipt.json) identifies the inherited source scaffold, exact additional selections, Rust compiler, reused dependencies, generated programs, binaries, commands, and input/output images. No Cargo or complete-engine build occurs.

The selected chain includes `retain_root_association`, `project_state`, association lookup, `associate_project_state`, and `associate_identity`. It uses the actual private-directory permissions, native root checks, no-follow lock primitive, runtime-marker predicate, temporary-file creation, record serialization, file synchronization, rename, and directory synchronization. The fixture provides an already-opened host capability; `Publisher::open`, the normal Engine/CLI request, and project publication are outside this test.

A wrapper delegates the actual `ensure_stopped` predicate, then pauses on a private stdin pipe after lock acquisition. A separate pause follows successful return from the selected initializer. The parent waits for the child's explicit phase, checks the owned process, and terminates only its isolated group with SIGKILL. This exercises process termination and kernel-lock release, not a reboot, power loss, or every interruption point.

The current and candidate generated programs differ by one call inside `associate_identity`: the candidate calls a dedicated association-lock helper. Both programs contain the same helper and instrumentation. The helper uses `state.lock`, the existing no-follow file primitive, a nonblocking OS lock, and the actual runtime predicate. Reader policy and Association schema remain unchanged. This is a private copied-source experiment, not a patched empack binary.

## Observed results

The capture has 23 cases across 25 commands. Nineteen ordinary result rows contain 13 successful API results and six expected refusals; four children are deliberately terminated. Two commands compile the small programs. A fixture process exiting zero means it recorded its result; the separate API outcome determines whether initialization succeeded.

| Boundary                                                             | Current selected source                                                              | Private candidate                                                                            |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Normal initialization and repeated call                              | Association published; repeated call preserves it.                                   | Association published; repeated call preserves it.                                           |
| Second initializer while the first holds its initialization lock     | Refuses the unassociated `operation.lock` slot.                                      | Reports the metadata initialization lock as busy.                                            |
| Termination after acquiring the lock, before writing the association | Leaves an empty `operation.lock`; fresh lookup and retry refuse without changing it. | Leaves an empty `state.lock`; fresh lookup observes no association, and retry publishes one. |
| Termination after the initializer returned successfully              | Association remains discoverable; retry succeeds without rewriting it.               | Association remains discoverable; retry succeeds without rewriting it.                       |
| Existing unknown journal and operation-lock footprint                | Refuses and preserves the unknown bytes.                                             | Refuses and preserves the unknown bytes.                                                     |

The candidate also reads an association published by the current variant without adding a file or rewriting it. Normal records have mode `0600`, their containing state directories have mode `0700`, and no temporary candidate remains after successful initialization on this Mac.

For the post-lock terminations, an independent `flock` attempt confirms the kernel lock is held before termination and available afterward. The lock file itself survives. All 25 owned command groups were observed absent when retired; those historical observations do not authorize later PID-based actions.

The [observation checker](initializer_observations.py) independently verifies pinned source and artifacts, the one-call difference between generated programs, streams, images, control outcomes, and final private fixture contents. The [summary](initializer-observations.json) keeps the source-source comparison, helper controls, and qualification limits separate. Input images preserve bytes, names, mode, inode/device, and modification time; access and change times are excluded.

## Finding and candidate direction

The current source's association writer creates ordinary operation-lock state before retaining the association needed to classify that state. Termination in this window leaves a new slot that this same source version refuses to discover or initialize. The reader's refusal is protective. The creating-version diagnostic does not provide a sufficient recovery path for this reproduced case.

Keep that refusal for unknown existing records. The candidate moves only association initialization to metadata coordination that the current reader already recognizes as an incomplete current slot. It prevents this new-writer window in the tested schedule and lets a later candidate initializer finish registration. It does not adopt or repair an old unassociated operation/journal footprint, and it does not establish general recovery authority.

The evidence supports investigating this focused protocol change before introducing another index, state schema, or migration mechanism. Preserving serialized Association meaning does not by itself prove coordination compatibility. Concurrent old/current and candidate initializers have not been tested together; the controlled contention cases use matching variants. Mixed-version behavior, normal Engine callers, and platform differences remain explicit obligations.

## Harness and remaining qualification

The collector now tracks its owned children for cleanup if its own work fails. A [separate helper check](../evidence/empack-initializer-20261124T205241728563Z/harness_cleanup_probe.py) verifies isolated-child retirement, an idempotent second cleanup, and refusal to kill a nonisolated process group. Its [result](../evidence/empack-initializer-20261124T205241728563Z/harness-cleanup-recheck.json) does not add initializer coverage. The original native capture retains its original producer; the later cleanup guard was tested separately, without rerunning these initializer cases.

Next, model the initializer phases and compare current and proposed traces against the captured states. Keep source API return, process exit, kernel ownership, persistent footprint, discovery, and retry as separate facts. A child terminated after a successful method return still has a terminated command outcome.

Before production adoption, exercise mixed-version initialization, malformed or nonregular metadata-lock inputs, ordinary Engine/CLI composition, failure around rename and synchronization, and supported native platforms. Complete publication, creation, approval/revision checks, retained-image recovery, and real reboot behavior remain pending. The source host capability is provided directly, and Windows privacy or directory semantics are not qualified by this Mac capture. Live projects, operation stores, Moment recovery data, launchers, games, and network services are untouched.
