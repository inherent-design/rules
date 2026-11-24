# Native state discovery and initialization boundaries

This intermediate band executes selected unchanged source at `0b4462e3032b4f09230b15329722eabefb7f574c` on macOS. Formal discovery models and replay remain pending. It extends the [identity band](IDENTITY.md) from a binding-only predicate adapter to actual directory capabilities, root checks, bounded association reads, and lookup. It does not qualify a complete initialization, publication, interruption, or recovery workflow.

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

Keep the reader conservative. A candidate writer change is dedicated association coordination compatible with the current empty-slot rule, followed by durable association publication before exposing ordinary operation-lock state. Reusing existing locking and record-writing primitives may suffice; an index, migration framework, or permissive adoption rule is not established as necessary. First qualify concurrent initializers, failure before and after record publication, existing foreign or unassociated state, lock ordering, and native directory durability. The current diagnostic's suggestion to use the creating version also needs review for this newly created prefix; no older version is demonstrated to repair it.

## Remaining work

Model discovery, bounded reads, original-key selection, unresolved claims, and the initialization prefix in Lean and Bend. Derive model inputs from raw fixture images, not selected names or returned error categories. Keep external JSON parsing and host observations attributable. Compare the retained results, with explicit unavailable and malformed-input cases; do not model this reader as a grant to recover or write.

Then join actual state initialization and interrupted publication/creation with retained-image validation, approval/revision checks, restoration direction, and coordination. Real reboot behavior, Linux/Windows providers, full root capture/revalidation, and recovery remain pending. Production changes require a separately selected decision. Live operation stores, user projects, and Moment recovery data are untouched.
