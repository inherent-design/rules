# Whole-world protection before file planning

The installed empack 0.8.8-beta preserves an initialized world as a group. Update, repair, rollback, omission, and later reintroduction did not refill missing world members in the disposable workflow. An ordinary missing seed configuration was restored by repair. Those are intentionally different ownership rules, not inconsistent seed behavior. This band establishes no new product defect.

## Domain and ordering

An explicit `world_root` groups publisher files into one initialization unit. The normal producer assigns it to conventional `world`, `world_nether`, `world_the_end`, and `saves/<name>` trees. World dependencies can supply custom roots through coherent member placements. World content must use seed policy; source policy and release validation reject managed replacement data.

The [selected current source](../sources/empack-worlds-selections.json) establishes this order:

1. Project the selected release by side and choices.
2. Combine recorded initialized roots with world roots from the previous inventory.
3. Protect incoming groups that overlap protected roots or have an occupied destination. Empty directories, regular files, symlinks, and non-directory ancestors count as occupied.
4. For a genuinely new absent group, capture its absence. Observation errors are failures, not absence.
5. Remove protected members from both old and incoming file reconciliation. Missing members do not become repair requests, and omitted old members do not become deletion requests.
6. Carry forward initialized roots and add incoming groups to the candidate instance record. This is planned metadata until successful publication; preparation does not persist it.

Protection precedes ordinary per-file observations and seed decisions. Portable overlap uses canonical Unicode caseless collision keys plus component boundaries; ASCII lowercase or a bare string prefix is not an equivalent implementation. The native fixture below uses simple names and does not qualify all Unicode overlaps or custom placements.

## Native snapshot workflow

The [capture](../evidence/empack-worlds-20261125T132516653266Z/progress.json) retains 18 logged workflow commands: 17 succeeded, and one incorrectly omitted the required rollback release argument and returned usage status 2. An additional retained help query identified the exact retained-release SHA-256 argument. The guarded continuation verified the instance still matched its post-repair snapshot before resuming. Original and continuation producers have separate frozen hashes; the failed invocation remains unchanged.

The host binary's SHA-256 is recorded. The source checkout is independently pinned at `0b4462e3032b4f09230b15329722eabefb7f574c`; reproducible source-to-installed-binary correspondence is not established.

Three releases were produced normally from one author project and one pack identity, with the same display version and distinct release identities. Release descriptors were not hand-edited. They contain ordinary text marker bytes named like world files, not playable Minecraft data. No Java, game, installer, live consumer, channel, or EULA workflow ran. State, cache, author sources, and instances are in the named private fixture root, without overriding HOME or changing host empack.

| Step | Observed result |
| --- | --- |
| Install A into a fresh instance | Both `world` and `saves/Study` receive initial members and appear in `initialized_worlds`. |
| Edit level data, delete a region, add runtime output, then preview/install B | Preview preserves the measured instance files. Played data and runtime output survive; neither the missing region nor B's new region appears. An unrelated managed file advances. |
| Delete an ordinary seed config and repair B | The config is restored. Missing world regions remain missing. |
| Roll back to A by its retained release digest | Managed content returns to A while played world data and runtime output survive. |
| Delete the fixture's synthetic `world`, install C without worlds, then reintroduce B | Initialized roots persist. The deleted world is not recreated. `saves/Study` retains its original bytes. |
| Install A with an occupied empty world directory | No template members are added to that directory. |
| Install A with a regular file at `world` | Its bytes remain unchanged. |
| Install A with a symlink at `world` | The link remains. The producer checks that its private outside sentinel is unchanged; a separate outside postimage was not exported. |
| Install A with a regular file blocking the `saves` ancestor | The file remains; the nested world is not materialized. |

The final `instance check` reports world members as `player-owned`, not required publisher-byte matches, even with the synthetic world absent. That verifies the API result, not an independent system-call trace proving no reads. The observer's own snapshots inspect these disposable directories and must not be confused with the engine's read footprint.

All 18 logged command groups were absent after completion. The private fixtures and durable records remain retained. Preview equality covers captured entry types and regular-file bytes, modes, and modification times; it does not establish all metadata or every transient effect.

## Models and verification

[Lean](Worlds.lean) supplies nine laws and [Bend](Worlds.bend) five. A basis contains recorded/old group evidence, selected incoming membership, an already computed overlap result, and occupancy only where needed. Initialization is candidate metadata interpreted after successful completion. Admitting new world seeding is different from allowing an entire installation: protected worlds can coexist with other applied changes.

The [case decoder](WorldsCase.lean) admits `occupied: null` only when protection or omission bypasses that observation. It refuses an unknown occupancy needed to initialize a new root. The internal unused Boolean does not mean the root was observed absent. Actual observation errors remain outside this admitted profile.

[Retained comparison](worlds_conformance.py) checks 20 group rows from ten successful installations/repairs/rollback stages. Each row's initialized membership comes from the completed native record. Protection, member-planning, and new-seed authorization are source projections, checked against the independently inspected native file effects; they are not exported native planner states. [Per-row provenance](../evidence/empack-worlds-20261125T132516653266Z/model-provenance.json) makes that boundary explicit. The first fresh-root absence is supported by the frozen producer's new empty instance creation, rather than an independent before-image.

Four further rows are model-only: old-inventory fallback, overlapping roots, stale captured absence, and missing absence evidence. The selected existing late-creation test was read, not run. In total, 96 scalar comparisons match both models. Three invalid/unknown input controls and four changed-effect controls are refused. [Conformance](../evidence/empack-worlds-20261125T132516653266Z/conformance.json) and [basis hashes](../evidence/empack-worlds-20261125T132516653266Z/basis.json) retain those scopes.

Compile the two Lean modules to `.build/empack-worlds-formal` with the pinned tools, then replay:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/empack/worlds_conformance.py
```

Replay reads evidence and executes pure models. It does not run empack. `worlds_probe.py` is a separate native collector; its continuation mode is restricted to the recorded missing-argument failure and rejects a changed instance. Do not reuse that mode to restart an arbitrary failed or uncertain workflow.

## Preserve and improve

Keep whole-group protection before per-file planning and the persisted initialization history. A missing world is not permission to reinitialize it; a rollback changes managed pack content, not gameplay history. Keep ordinary seed repair distinct. Do not turn cleanup, a new release label, or an explicit managed-file override into authority over a played world.

The earlier [ownership summary candidate](OWNERSHIP.md) can include compact protected-world facts and their source: previous initialization, prior inventory, overlap, or occupied destination. The protection pass already has those facts. Retaining them for reporting would avoid reconstructing preservation from a short file-change count or traversing user data merely to count it. Reuse one typed change summary instead of adding a separate world policy system. This is an API/reporting proposal, not an implemented change.

Actual game-format validation, custom world dependencies, all side/choice transitions, Unicode collisions, permission-error paths, approval-time concurrent creation, runtime writes during preparation, crash recovery, signed channels, and cross-platform consumers remain open. The current snapshot rules and focused native outcomes should survive portable-authoring extraction; they do not by themselves qualify that future engine.
