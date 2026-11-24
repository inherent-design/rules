# Recovery planning, approval, and retained images

This band compares 45 commands from the installed empack `0.8.8-beta` CLI with scoped Lean and Bend models. It preserves three separate facts: a recovery can be inspected, its changes can be planned, and the approved execution can still fail validation. A failed execution can preserve the project while changing private recovery scratch.

## Evidence and boundaries

The [collector](recovery_probe.py) creates 19 private roots with tiny, authored schema-5 journals. These are forensic inputs, not journals produced by an actual interrupted publication. One [setup helper](recovery_fixture_oracle.rs) reuses attributed source primitives to obtain real root/file identity and publish each root association. Recovery itself runs through the installed executable, including its inspection, preparation, confirmation, and execution paths. The helper is not the recovery implementation.

The [receipt](../evidence/empack-recovery-20261124T215915036620Z/receipt.json) binds the executable, generated helper, compiler, reused libraries, seven [selected source files](../sources/empack-recovery-selections.json), commands, images, and frozen producer. Those source files match both checkout `0b4462e3032b4f09230b15329722eabefb7f574c` and tag `v0.8.8-beta`. This establishes file correspondence, not a reproducible full-build claim for the installed binary.

There are 65 commands: one small helper compilation, 19 identity/association setups, and 45 CLI commands. The CLI records 29 zero exits and 16 refusals. Six commands use a private controlling PTY. Each waits for the actual recovery confirmation while the process is live, makes its explicit fixture edit, and then answers. All owned groups were observed retired. No launcher, game, public registry, live operation store, personal project, or Moment recovery data is accessed. The work occupies approximately 2.4 MiB of allocated local storage; no Cargo or full-engine build occurs.

The [checker](recovery_observations.py) verifies source/tool/artifact identities, streams, 172 images, and all 19 final private postimages. Thirty-nine CLI commands preserve project contents and metadata relative to their execution input; 36 preserve the complete captured fixture. These snapshots cover the fixture project, host state, cache, and retained originals. They are not process-wide write tracing or a rule that every refusal is effect-free. For prompted commands, the execution input is the image after the explicit external edit.

The current collector keeps an interrupted Popen handle in its owned registry if retirement fails. That small guard change follows the frozen successful collection; the original producer remains in the receipt. It neither reruns nor expands the native observations. The reused isolated-group retirement helper has separate controls in the [initializer band](INITIALIZATION.md).

## Domain and source contract

The source distinguishes a journal's root binding, operation identity, direction, changes, retained names, expected inventory, and committed state. A public recovery status is a coordinate for selection, not execution authority. A private `PreparedRecovery` holds the captured root, typed journal revision, observed files, action, plan, and resource estimate. It cannot be deserialized from an imported journal into an approved plan.

Inspection opens existing state and an existing shared publication lock. Preparation validates the selected journal and current inputs without modifying the project. The Engine binds the operation selected by inspection. Execution reacquires exclusive publication ownership and rechecks the prepared root, journal revision, and visible observations before applying the requested recovery. Runtime ownership, directory creation recovery, and general writer interruption remain separate paths.

The revision hashes the typed, reserialized journal. Harmless JSON formatting does not itself change that revision; changing an `applied` value does. Visible observations include file identity as well as content and permissions. Identical bytes on a replacement object do not inherit the original object's approval.

## Observed direction and image demand

| Input and action                                            | Observed result                                                                                                                                 |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Pending forward journal; finish                             | Publishes its after-image and commits.                                                                                                          |
| Pending forward journal; restore after a change             | Restores its before-image, persists inverse direction, and commits.                                                                             |
| Journal already restoring; finish or restore                | Both complete the saved inverse journal's after-image. Neither reverses it again.                                                               |
| Target already matches after; finish with missing candidate | Succeeds without reading an unnecessary candidate.                                                                                              |
| Target still before; finish with corrupt candidate          | Refuses preparation and execution without changing the project.                                                                                 |
| Restore an applied change with corrupt forward candidate    | Succeeds using the valid before-image. The unused corrupt forward candidate is not required.                                                    |
| Restore an applied change with corrupt before-image         | Preview succeeds; execution refuses before-image verification. Target and journal stay unchanged, but `restore-0` is added to retained scratch. |
| Restore a target already before, with corrupt before-image  | A zero-change restoration succeeds without copying the unused image.                                                                            |
| Changed target or same-byte replacement object              | Refuses without adopting the file.                                                                                                              |
| Unsupported journal schema                                  | Refuses inspection and recovery.                                                                                                                |
| Committed journal                                           | Inspection succeeds with no pending recovery; an explicit request for that no-longer-pending operation refuses.                                 |

“Finish” means complete the durable direction already selected by the journal. It does not always mean publish the original candidate. The source and CLI already explain an in-progress restoration separately; retain that behavior.

## Approval and partial effects

At the actual confirmation prompt, later target edits, same-byte object replacement, and typed journal progress all cause execution to refuse. They preserve the explicitly edited project state. Reformatting the journal succeeds. Corrupting a retained candidate after preparation is detected by execution even though the journal and visible target have not changed. Declining the prompt preserves the complete fixture.

The corrupt-before-image case is a useful counterexample to a broader reading of “preview” or “not applied.” Preparation shows the intended file change, but does not read every byte needed to perform it. Execution can create private scratch and then fail verification. This is not a demonstrated destructive-write defect: the target and journal remain intact in this fixture. It does establish that planning, payload verification, and zero effects are distinct promises.

A reporting candidate is to name the requested recovery and failed resource, keep the safe inspection route, and preserve whether project changes and private preparation effects occurred. Avoid implying that no runtime or host work happened merely because publication did not finish. This remains analysis; the separate deferred production UX work is not activated.

## Models and comparison

[Lean](Recovery.lean) provides 24 laws and [Bend](Recovery.bend) provides 11. They model one regular-file change with present, distinct before/after images. They separate persisted direction, target position, prior-object binding, role-specific image validity, captured versus current journal/visible observations, approval, final commitment, and new restore scratch. The [research decoder](RecoveryCase.lean) admits only that bounded profile.

The [replay](recovery_conformance.py) derives inputs from the captured journal, source-obtained identity witnesses, actual file images, command arguments, and explicit prompt interventions. Expected exit status, rendered change count, final target, journal direction/commitment, and scratch creation come independently from the recorded command and postimage. It compares all 45 CLI commands with both models. Research-input refusals, observation mutation controls, tool identities, and frozen inputs belong in the [comparison receipt](../evidence/empack-recovery-20261124T215915036620Z/conformance.json).

Object projection uses retained original files and quiescent private roots to distinguish the observed original from a new inode. It does not reconstruct durable tokens, mint native capabilities, or qualify reboot and reuse races. Source-level checks for complete inventory, cryptography, journal shape, locking, plan ownership, and native IO remain explicit premises. Tests for wrong Engine/approval objects are not supplied by a successful CLI confirmation.

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/empack/recovery_conformance.py
```

## Candidate and verification plan

A focused candidate is to verify a needed before-image during restoration preparation. Read it only when restoration will copy it: keep successful no-op recovery when the target already matches before, and keep the forward candidate irrelevant when restoring from before-images. Reuse the existing digest, byte-limit, and no-follow primitives through a small role-specific image verifier shared by preparation and copying. Bind failures to the image role, affected target, and operation; a generic corrupt-image message omits those useful facts. Keep plan-owned inputs and observed data distinct from a verification result. Execution must still recheck against changes after approval. The proposed predicate in both models is not an implemented native change.

The keep-current alternative is defensible if the interface accurately promises a plan while leaving final payload checks to execution. Earlier verification would give a more useful refusal before approval and avoid this failed scratch allocation. It also costs an extra read and can still race with later corruption. No journal schema change, migration framework, permissive adoption, or general recovery redesign is established as necessary.

Before adoption, qualify multi-file restoration, creation versus publication routing, exact operation mismatch, wrong-plan/Engine ownership, complete unchanged inventory, root replacement, supported platforms, and real interrupted producer output. Test failure while persisting inverse direction and while resuming that inverse, with independently observed project and host effects. Retained-image absence, nonregular files, lock/liveness changes, bounded resources, and native synchronization remain obligations. A broad recovery guarantee cannot be inferred from these one-file forensic fixtures.
