# Association initialization, interruption, and retry

This source/native protocol band follows [state discovery](ROOT-STATE.md) at empack source `0b4462e3032b4f09230b15329722eabefb7f574c`. The selected initializer strands a new state slot when its child is terminated before association publication. A private metadata-lock candidate improves one window but fails at the next allocation boundary. Keep that failed scope explicit; no production change is selected.

## Scope and provenance

The [collector](initializer_probe.py), [caller](initializer_oracle.rs), and [ledger](../sources/empack-initializer-selections.json) retain 12 source pins. The [first receipt](../evidence/empack-initializer-20261124T205241728563Z/receipt.json) identifies the inherited scaffold, exact source selections, compiler, reused libraries, generated programs, binaries, commands, and images. No Cargo or complete-engine build occurs.

The selected chain includes `retain_root_association`, `project_state`, association lookup, `associate_project_state`, and `associate_identity`. It uses actual native root checks, no-follow locks, the runtime-marker predicate, private-directory permissions, temporary allocation, serialization, file synchronization, rename, and directory synchronization. The fixture supplies an already-opened host capability. `Publisher::open`, the normal Engine/CLI request, project publication, and recovery remain outside this execution.

The two copied-source programs differ by one call inside `associate_identity`. The candidate calls a dedicated helper using `state.lock`, the existing no-follow primitive, a nonblocking kernel lock, and the actual runtime predicate. Reader policy and Association schema remain unchanged. This is candidate A below, not a patched empack executable.

Controlled wrappers delegate actual source operations, then pause through private stdin after lock acquisition or temporary allocation. Another pause follows successful initializer return. The parent waits for explicit readiness and terminates only its isolated child group with SIGKILL. Historical process/group observations authorize no later PID action. These are termination tests on this Mac, not reboot or power-loss tests.

## First interruption window

The first capture contains 23 cases across 25 commands: two small compilations, 19 ordinary API results (13 successes and six refusals), and four deliberately terminated children. Two terminations follow successful initializer return. The fixture exits zero when it records a result; API success is a separate field.

| Boundary                                            | Current selected source                                           | Metadata-lock candidate A                                                   |
| --------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------- |
| Normal initialization and repeat                    | Publishes once; repeat preserves the record.                      | Publishes once; repeat preserves the record.                                |
| Same-variant contender while the lock is held       | Refuses the unassociated `operation.lock` slot.                   | Reports initialization as busy.                                             |
| Termination after lock, before temporary allocation | Leaves `operation.lock`; fresh lookup and retry refuse unchanged. | Leaves `state.lock`; lookup observes absence, and retry registers the root. |
| Termination after successful initializer return     | Record remains discoverable; retry preserves it.                  | Record remains discoverable; retry preserves it.                            |
| Authored unknown journal and operation lock         | Refuses and preserves unknown bytes.                              | Refuses and preserves unknown bytes.                                        |

An independent `flock` attempt confirms the initialization lock is held before termination and available afterward. The file remains. Candidate A also accepts a current-source published record without adding a file or rewriting it. Normal record and directory modes are `0600` and `0700`; successful initialization leaves no scratch file.

The [checker](initializer_observations.py) and [summary](initializer-observations.json) verify source/artifact identities, streams, images, protections, and final private postimages. Image comparisons retain paths, bytes, mode, inode/device, and modification time; access and change times are excluded.

## Mixed protocols do not share exclusion

The [mixed collector](initializer_mixed_probe.py) reuses those two binaries on four fresh roots, without recompiling them. Its [receipt](../evidence/empack-initializer-mixed-20261124T211709634681Z/receipt.json), [checker](initializer_mixed_observations.py), and [summary](initializer-mixed-observations.json) retain four schedules and 12 commands: nine ordinary API results (six successes and three refusals) and three deliberate terminations.

- Both kernel locks can be held simultaneously. A shared record format does not establish shared coordination.
- Current source can publish while candidate A waits at its own lock boundary. The candidate's second read accepts the record without rewriting it.
- A candidate admitted before the current-source footprint appears can finish after that current-source child dies. This is an admitted writer completing, not a fresh reader adopting unknown state.
- If both die before registration, the old `operation.lock` footprint remains. Fresh candidate lookup and retry refuse it unchanged.
- A current-first writer blocks a fresh candidate as unassociated. After current-source completion, candidate retry accepts the published record without changing it.

These are copied-source protocol variants at one pinned revision, not independently qualified released versions or a proof of general concurrency safety. Events and views are separately ordered arrays; the frozen producer supplies their placement, not a fabricated shared timestamp sequence.

## Temporary allocation defeats the general fix

Actual `write_record` allocates a scratch file before writing association bytes. The [temporary profile receipt](../evidence/empack-initializer-20261124T212854359074Z/receipt.json) retains two new small compilations and six cases across eight commands. Two owned children are terminated after actual zero-byte allocation. All four subsequent lookup/retry calls refuse.

Both variants leave their coordination file and an empty `.empack-candidate-*` file, with no association. The reader tolerates only `state.lock` in an incomplete current slot; scratch remains unclassified. Both lookup and retry preserve that footprint. The [checker](initializer_temporary_observations.py) and [summary](initializer-temporary-observations.json) retain the counterexample.

**Candidate A is incomplete as a general interruption fix.** Its post-lock improvement remains observed, but simply changing the lock filename does not make initialization restartable. Do not weaken the reader, delete scratch by its name, or imply that an older executable repairs this state.

## Models and replay

[Lean](Initialization.lean) provides 23 laws and [Bend](Initialization.bend) provides 12. They model the selected successful-IO protocol phases. File presence, per-actor kernel ownership, API result, command acknowledgement/termination, association publication, and scratch retention remain separate. The laws retain both interruption counterexamples, same-variant contention, mixed-lock coexistence, second-read convergence, unknown-state refusal, and success followed by a killed command.

The [replay](initializer_conformance.py) derives footprints and matching record witnesses from the retained images and expected API/command results from native output. It reconstructs causal phases from the frozen producers. Receipt finish order is not actor start order. An awaited command branches on model state; its recorded expected success does not select the modeled branch. The [research decoder](InitializationCase.lean) bounds actors, events, masks, versions, and profiles.

Both models match 81 retained projections across 16 traces, covering the first capture, all four mixed schedules, and both temporary-allocation traces. Eleven unsupported research inputs refuse, and four changed observation expectations are detected. Model results, research-input refusals, observation mutation controls, and frozen basis identities belong in the [comparison receipt](../evidence/empack-initializer-20261124T205241728563Z/conformance.json). This is pure retained-data replay, not additional empack execution.

External decoding supplies a matching schema-1 association witness. The models neither parse native JSON text nor mint root/capability authority. Successful allocation/write/sync/rename is abstracted; unsampled partial bytes, IO failures, first-error priority, arbitrary schedules, and durable crash recovery remain outside the comparison. Observed marker changes count registrations in sampled views and cannot exclude unsampled rewrites.

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/empack/initializer_conformance.py
```

## Revised proposal and verification plan

Investigate preparing a complete association-bearing private directory outside the discoverable `project-*` namespace, then publishing it with identity-checked no-replace directory machinery. The [source-only primitive pin](../sources/empack-initializer-directory-proposal.json) identifies existing `native/creation.rs`; it was inspected, not invoked here. The abstract admission laws describe proposed requirements, not an implemented candidate B.

Preparation must retain and synchronize the complete image, revalidate the root and candidate identity, publish without replacing an existing target, and check/synchronize the parent. A racing matching record may be accepted through strict discovery; an unknown target must remain untouched. Preserve serialized Association meaning and physical keys unless a separate decision establishes a need to change them. No index or migration framework is justified by these results.

This moves incomplete preparation into a private orphan, which still needs ownership-qualified retention and cleanup. Never unlink a reused path through path-only cleanup after rename. Preserve unexpected/recovery content, and account for private candidates in the existing host-entry cap. Atomicity, identity, synchronization, and capacity are premises to qualify, not guarantees supplied by the model. An older writer can still leave its historical incomplete slot; the new design must not silently adopt it.

Before implementation selection, qualify existing-target races, identity changes, private orphan handling, failure around allocation/rename/synchronization, ordinary Engine/CLI composition, and supported native platforms. Add initialization to the broader recovery/approval/retained-image work without conflating those authorities. Real reboot behavior remains pending.

The [separate cleanup-helper check](../evidence/empack-initializer-20261124T205241728563Z/harness_cleanup_probe.py) verifies owned isolated-child retirement, idempotent cleanup, and refusal to kill a nonisolated group. Its [result](../evidence/empack-initializer-20261124T205241728563Z/harness-cleanup-recheck.json) adds no initializer coverage. Original producers and failed interpretations remain retained. Live projects, operation stores, Moment recovery, launchers, games, and network services are untouched.
