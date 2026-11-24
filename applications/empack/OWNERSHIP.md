# Current native file ownership

This band compares the actual current `empack-core::instance::plan_file` API with models, and separately exercises the installed empack 0.8.8-beta CLI through a tiny producer/install/update/repair flow. Those are different evidence scopes. The source checkout is `0b4462e3032b4f09230b15329722eabefb7f574c`; its build correspondence with the installed release binary is not proved here.

## Domain and authority

A completed installation provides prior ownership and content. A selected release supplies desired content and policy. A fresh native observation supplies absence, regular-file content, or directory shape. Content comparison includes byte identity, length, read-only state, and executable state when the representation supports it. A policy decision is not native write authority.

The caller must establish the root, selected release, side/choices, collision rules, world protection, safe native observations, accepted local deviations, and exact authorization. Links are rejected before the pure function. An observation failure is not absence. This model does not replace those caller proofs or claim that every directory or seeded world is individually observed.

| Case | Current pure decision |
| --- | --- |
| Incoming seed, destination absent | Create the initial file. |
| Incoming seed, regular file already present | Preserve bytes and user ownership, including an old managed file. |
| Prior seed, incoming managed | Ownership conflict, even if missing or already byte-identical. |
| Incoming managed, unowned regular file | Ownership conflict; matching bytes do not establish adoption. |
| Incoming managed, current matches incoming | No content change, with source assertions still checked by the engine. |
| Incoming managed, current matches the prior managed baseline | Replace with the selected incoming content. |
| Incoming managed, current matches neither | Modified-file conflict. |
| Owned managed file retired by the release | Remove only an unchanged regular baseline; preserve absence or report conflict as appropriate. |
| Unowned content or prior seed omitted by the release | Preserve user state. |

An incoming file cannot replace a directory through this function. When no file is incoming, preserving an unowned or seed-owned directory is allowed; a blanket “every directory is a conflict” rule would be wrong. Native publication still cannot recursively delete a directory because a file vanished from a release.

## Actual core API comparison

[Lean](Ownership.lean) and [Bend](Ownership.bend) express the current decision ordering with typed policies, observations, contents, and decisions. Ten Lean laws and four Bend laws include seed preservation, creation, retirement, unowned protection, and ownership transitions. Lean also checks supported-attribute comparison properties.

The [oracle](ownership_oracle.rs) calls the actual public function from a standalone compilation of the dependency-free core. It uses the real `FileContent`, `ObservedPath`, `InstalledFile`, `ReleaseFile`, and capability types. No method body or equality implementation is mocked. Cargo and the full engine are not built. The source tree, compiler, commands, and output identities are in [the core receipt](../evidence/empack-native-ownership-20261124T031930881554Z/core-receipt.json).

The 252 cases vary prior ownership, incoming policy/removal, absent/directory/regular observations, three content labels, read-only/executable attributes, and executable-bit capability. Previous and incoming values have fixed labels, length one, and writable/non-executable attributes. The synthetic SHA-256-shaped values are equality labels, not verified physical file content. The complete crate source tree is fingerprinted, including test files that were not executed by the oracle. A false executable-bit capability parameter is not a native Windows filesystem test.

[Retained replay](ownership_conformance.py) compares every actual API result with both models. The oracle also verifies that every create/replace result carries the exact incoming postcondition. This finite comparison does not prove all values, all callers, or native filesystem publication.

## Native CLI flow

The [native receipt](../evidence/empack-native-ownership-20261124T031930881554Z/receipt.json), command logs, [raw progress](../evidence/empack-native-ownership-20261124T031930881554Z/progress.json), and exact executed probe retain fifteen main workflow commands. Preparation/help and the first init/build commands are recorded separately. The fixture uses private state/cache/project/instance directories and two authored text files; it does not run Java or a game.

Three native releases come from the normal producer, without hand-edited release descriptors:

1. A contains a seed configuration and a managed payload. It installs normally.
2. B changes both authored files. A launcher/player-style seed edit and an unowned note survive; unchanged managed content advances. Preview preserves the measured instance files.
3. A local managed edit blocks ordinary application. Explicit preserve records an accepted local override; `instance check` verifies that override. C changes the payload's authored policy to seed after normal sync/build. Applying C preserves the local bytes without an override decision.
4. Returning to B requests seed-to-managed ownership and is refused. An explicit replace approves that transition. Removing the now-managed file and repairing restores B's exact content, preserves the seed/note, and leaves B selected.

All three descriptors deliberately retain the same human version label. They have one pack identity and three distinct payload digests. The release identity, not its display version, determines exact content and policy. The final check reports one verified managed file, one player-owned entry, no remaining accepted override, and B's exact release identity. This is snapshot installation, not channel authentication or automatic update qualification.

The two conflict diagnostics name `game/payload.txt`, explain the cause, and offer preserve/replace/merge commands with the correct game-relative selector. That is useful current behavior worth preserving. This flow does not establish every conflict action for every file shape, and does not activate the separately deferred removal/re-adoption or update-preview work.

The first init attempt correctly refused an explicitly supplied state directory with mode `0755`. The state directory remained empty and the project did not exist. The owned fixture was corrected to `0700`, then init succeeded. A later fixture assertion incorrectly expected a `.zip` suffix after a successful native build; the archive is named `.empack`. The current usage guide already documents that suffix correctly. Neither fixture issue is a product regression.

Preview/refusal equality compares regular-file bytes, modes, and modification times in the instance. It does not establish no cache/log effects, every extended attribute, or observation of every intermediate byte state. The executed probe's assertions retain those narrower file-content checks. No world groups, Prism layout, signed channels, native crash recovery, runtime processes, or other operating systems were exercised.

## Preservation and improvement candidate

Keep seed semantics and explicit adoption. Do not relax all configuration files or images into unmanaged data. Keep instance repair pinned to the completed release, and preserve the distinction between publisher content and an explicitly accepted local deviation. The current conflict explanations and valid scoped choices should remain derived from typed facts.

One reporting opportunity is visible in the policy-only C transition. Both game files retain their bytes, but the CLI reports `File changes: 2`. Source inspection shows the renderer counts every native `FilePlan` change, including installation records and retained descriptors. The count is legitimate; it is easy to read as two game files being rewritten.

A candidate shared `InstanceChangeSummary` would classify the existing typed `ManagedPath` changes into game content, instance metadata, and consumer/runtime metadata, and retain explicit ownership/preservation dispositions. The engine has the prior/incoming policies and observations while planning; derive the summary there rather than inferring it later from rendered text or filename prefixes. Protected world roots must remain compact preservation facts, without traversing unrelated player data merely to count it.

Human output could distinguish “Game files unchanged; installation record updated” from actual content writes, while details retain destinations, policies, exact release identity, and authorization requirements. The public preview and automation report should use the same facts. Inspect existing report schemas and callers before adding fields; retain the meaning of existing totals, or explicitly version a changed schema. A keep-current alternative is to label the existing total as all installation-file changes and provide a detailed typed breakdown. Neither option changes reconciliation or publication authority.

The explicit-state refusal could also name the selected path and observed/required mode. Its security boundary should remain strict. This is a small operational diagnostic opportunity, not a reason to adopt unsafe state or widen the plan's read set.

## Remaining verification

Exercise world-group initialization/retirement, optional choices, unchanged/missing seed adoption, user-edited accepted overrides, conflict merge sources, source assertions, side/layout transitions, permission changes, release retirement, and interrupted publication. Keep direct snapshots, authenticated channels, rollback, and prelaunch updates separate. Confirm actual consumer behavior where a recipe adds constraints beyond this neutral native release. Preserve unknown, unavailable, and unsupported states in both APIs and presentation.

Compile `Ownership.lean` to `.build/applications/empack/Ownership.olean`, then replay with the pinned tools:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/empack/ownership_conformance.py applications/evidence/empack-native-ownership-20261124T031930881554Z
```

Replay does not execute native empack or rustc. `native_ownership_probe.py` is a one-shot continuation of the explicitly prepared private fixture; it refuses to restart an already-started run. Inspect retained state after failure before choosing further actions. All native collection stays outside ordinary CI.
