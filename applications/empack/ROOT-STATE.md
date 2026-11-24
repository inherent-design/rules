# Native state discovery and initialization boundaries

This bounded source/native/model band executes selected unchanged source at `0b4462e3032b4f09230b15329722eabefb7f574c` on macOS. Lean and Bend compare admission and selection with the retained views. It extends the [identity band](IDENTITY.md) from a binding-only predicate adapter to actual directory capabilities, root checks, bounded association reads, and lookup. It does not qualify a complete initialization, publication, interruption, or recovery workflow.

## Executed boundary

The [collector](root_state_probe.py), [caller](root_state_oracle.rs), and [source ledger](../sources/empack-root-state-selections.json) retain exact selected functions. They use the actual `Publisher` fields, `ProjectReadRoot::open/selected/check_binding`, native identity and no-follow file access, bounded copying, association codec and predicate, lookup, `find_project_state`, and `bound_root_key`. Existing attributed Rust dependencies include `cap_std` and `cap_fs_ext`. Only synchronous cancellation methods and a fresh uncancelled default are used. No Cargo or whole-engine build occurs.

The fixture supplies an already-opened host capability; it does not execute `Publisher::open`, private-directory initialization, or its normal composition root. All association records and journal/runtime-named sentinels are authored fixture data. They are not engine-generated operations and supply no recovery authority.

The [completed discovery capture](../evidence/empack-root-state-20261124T201312610313Z/receipt.json) contains 34 available cases. Each calls the actual resolver, finder, and bound-key method. Five resolve to no association, five select an association, and 24 refuse. A separate non-UTF-8 filename setup is unavailable: this filesystem rejects it with errno 92 before discovery runs. The [initial failed collection](../evidence/empack-root-state-20261124T201230642889Z/receipt.json) retains its 28 completed observations and setup failure. It is not a product failure or a passing whole run.

## Observed distinctions

**The retained physical slot can outlive a device label.** An authored old-device association is found using its original key and persistent token. None of the three discovery calls creates a current-key slot, moves the old directory, or rewrites the record. This is a synthetic prior-device record on the current host, not a reboot or remount.

**No association is different from unresolved state.** A current empty directory or one containing only `state.lock` is not selected. An old-key empty directory is unresolved, as is a current directory containing only `operation.lock`. A selected valid record does not conceal a second unresolved slot. Discovery itself initializes neither kind.

**A derived key is not proof that state exists.** With no selected association, `bound_root_key` returns the current key. With a selected old-device record, it returns that original physical slot. Callers must not interpret a returned key as an observed record or permission to create one.

**Admission precedes use.** Foreign current ownership, duplicate claims, misnamed records, unsupported schema, malformed or duplicate fields, nested unknown fields, and oversize records refuse. A valid record padded to exactly 1,024 bytes is accepted. Association symlinks, directories, and a FIFO refuse; a FIFO does not hang. Matching state entries that are files or symlinks also refuse. Unrelated corrupt entries are skipped by name filtering.

**The lookup limit covers the host directory.** With 4,096 immediate entries, including 4,095 unrelated empty files, a valid association is found. One additional unrelated entry causes refusal. The cap bounds enumeration before filtering; it is not a maximum number of records matching this project. This is a capacity boundary to explain and qualify, not permission to purge unknown history.

**Discovery is not coordination or recovery.** Lookup succeeds while an authored fixture `operation.lock` is held. Actual read/recovery callers acquire their own coordination afterward. A root moved away from its held selected location or replaced there refuses. Reopening a renamed root at its new selected location remains a separate joined test obligation; this fixture does not establish that renaming a project is unsupported.

The [observation checker](root_state_observations.py) verifies source, tools, artifacts, streams, and private postimages. Before/after snapshots compare path shape, file bytes, inode/device, mode, and modification time; access time is excluded. The limit fixture has two phases, so only its final image is a current postimage. All three source calls preserve each captured input image. Escaped diagnostic coordinates retain the embedded newline as data, without adding a false heading.

## Initialization prefix to investigate

The source `associate_identity` calls `lock(state)` before writing a missing association. That calls `lock_file(state, "operation.lock")`, acquires the file lock, and checks that no runtime marker exists. The reader's empty-slot exception permits only `state.lock`. These source paths therefore deserve a joined interruption test.

The [prefix capture](../evidence/empack-root-state-20261124T201907525187Z/receipt.json) executes the actual `lock`, `lock_file`, and `ensure_stopped` functions against an empty current slot, then drops the lock before invoking discovery. The exact new effect is one empty `operation.lock` plus its parent-directory metadata change. No association, journal, or runtime marker is created. All three discovery methods then report unassociated state. The [summary](root-state-observations.json) retains the before image and exact change.

This demonstrates the primitive prefix and resulting refusal. It does not execute the complete association writer, terminate it at that point, test power-loss durability, or establish a complete recovery defect. The [first prefix compilation](../evidence/empack-root-state-20261124T201809705356Z/receipt.json) failed because the fixture scaffold omitted a `File` import; it ran no native program and remains retained separately.

The subsequent [initializer study](INITIALIZATION.md) executes the selected writer chain and terminates owned children after lock acquisition, temporary allocation, and API return. Its mixed schedules show independent kernel locks can coexist. The metadata-lock candidate improves the first window but still strands after scratch allocation, so it is incomplete as a general interruption fix. Complete Engine, platform, and recovery obligations remain separate.

Keep the reader conservative. Investigate complete private-directory preparation followed by identity-checked no-replace publication, while retaining unknown-state refusal, private orphan/capacity obligations, and historical incomplete slots. An index, migration framework, or permissive adoption rule is not established as necessary. The creating-version suggestion does not supply a demonstrated repair path for the reproduced initializer windows.

## Models and replay

The [Lean model](RootState.lean) provides 23 laws, including a general law that every immediate entry counts before name filtering. The [Bend model](RootState.bend) provides 14 laws. Both preserve current-empty versus unresolved state, original-key selection, malformed versus absent records, foreign ownership, duplicate claims, root replacement, inclusive byte limits, and fallback keys that do not establish state.

The [replay](root_state_conformance.py) derives all immediate entries from the raw images, including the 4,095 and 4,096 unrelated entries. Duplicate-preserving external JSON decoding projects strict typed record witnesses. The models do not parse JSON text or recreate native capabilities. The root relation uses presence/device/inode under the private fixture's quiescence and retained-root assumptions; birth, UUID, and durable-token stability for the same object remain premises. The actual native `check_binding` still compares its complete identity.

Both models match all 35 available native cases across the three entry points. The [comparison receipt](../evidence/empack-root-state-20261124T201312610313Z/conformance.json) also records 14 unsupported research-input refusals. Two additional views—the recorded pre-lock image and the proposed `state.lock`-only alternative—are model-only. Those views implement no writer. The later [initializer band](INITIALIZATION.md) separately executes a private copied-source candidate; production implementation and complete Engine qualification remain pending.

Admission, selected physical key, found state, and key fallback are compared. Native error chains remain retained separately. Directory enumeration order was not recorded, so the models do not claim the first diagnostic when several independent faults coexist. Complete quiescent views and the absence of additional enumeration/permission races are explicit premises.

Bend's checked interpreter exceeds its machine stack on the large boundary fixture, while type checking and the model's kernel verdict pass. Its native builder replays the same complete inputs successfully; no boundary case is removed. The [runtime record](../evidence/empack-root-state-20261124T201312610313Z/model-runtime.json) preserves that limitation. The replay records Bend's identity, generated source, output, and approximately 1.1 MB model executable. The builder's subordinate compiler invocation is not independently recorded. This is a local model comparison, not fresh empack or filesystem evidence.

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/empack/root_state_conformance.py
```

## API and interface direction

Retain the current distinction between a derived key, a selected association and held directory, a prepared recovery, and an authorized operation. Internal lookup already returns the information needed to preserve absence separately from selection; a string returned by the fallback helper must not become an existence or authority check in a new caller. Portable project/release identities cannot replace these host facts.

Explain capacity as an enumeration limit over the host directory, with a safe inspection route that preserves unknown and recovery data. For unassociated state, retain useful paths and uncertainty. The creating-version suggestion is insufficient for the reproduced initializer prefix; do not imply that an older executable has been shown to repair it. These are reporting candidates, not changes to ownership policy or a newly selected cleanup mechanism.

## Remaining work

Extend the selected initializer study beyond its controlled mixed-protocol schedules to ordinary Engine callers, private-directory publication, failure around rename and synchronization, and supported native platforms. Join interrupted publication/creation with retained-image validation, approval/revision checks, restoration direction, and coordination while keeping the current reader conservative. Real reboot behavior, Linux/Windows providers, full root capture/revalidation, and recovery remain pending. Production changes require a separately selected decision. Live operation stores, user projects, and Moment recovery data are untouched.
