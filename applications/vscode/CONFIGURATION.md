# Configuration: source scope, effective values, and inspection

This band executes the configuration extension API in VS Code desktop 1.147.0 at `8a14f0cc1b08d531eb83255ea3764ae22aa932b5` on macOS arm64. One generated local multi-root workspace supplies two folders, two language contexts, and three registered settings. Eleven sequential phases capture 132 context/setting projections, their documented inspection fields, and the four source files. This qualifies neither the Settings UI nor remote, managed, or untrusted workspaces.

## Domain and current behavior

A setting declaration has a key, schema, default, and admitted scope. An assignment additionally belongs to a profile/source target and, optionally, a language selector. An effective lookup needs a resource and language context; it is not simply the last file edited. The write target and the winning read scope are different facts. Explicit `null`, an absent assignment, and a removed assignment must remain distinguishable.

The pinned [public API](https://github.com/microsoft/vscode/blob/8a14f0cc1b08d531eb83255ea3764ae22aa932b5/src/vscode-dts/vscode.d.ts) documents this low-to-high order for its eight inspection fields:

1. Default, user, workspace, and workspace-folder values.
2. Default-language, user-language, workspace-language, and workspace-folder-language values.

Objects recursively merge; arrays and other value types replace. Consequently, a language-specific default can mask an ordinary folder assignment. Removing one assignment exposes the next applicable value; it need not remove the empty language block from the source file. The native fixture confirms these distinctions for its registered keys. Registration scopes and the additional application, remote, memory, and policy layers have [selected source evidence](../sources/vscode-configuration-selections.json), not native qualification here. Combined language selectors remain outside the model.

## Native evidence

The successful [capture](../evidence/vscode-configuration-20261124T071100228669Z/observed.json) uses the [frozen extension](../evidence/vscode-configuration-20261124T071100228669Z/extension.cjs). It calls `getConfiguration()` with explicit resource/language scopes and `update()` with explicit user, workspace, or folder targets. Independent filesystem reads retain each complete source file after every phase. It does not click or assess the Settings UI.

| Transition | Observed result |
| --- | --- |
| Initial generic user/workspace/folder assignments | Plain-text contexts read their respective folder values. JavaScript contexts read the registered language default. |
| Add user, workspace, then folder JavaScript overrides | The selected language scope wins; folder A and B differ only where A has a folder-language assignment. |
| Edit a masked generic user value | The user file and inspection metadata change; none of the four effective views changes. The section notification is true while all captured scoped `affectsConfiguration()` results are false. |
| Remove language assignments in reverse order | Values fall back through workspace-language, user-language, and language-default values. Empty language containers remain in the files. |
| Remove folder A's ordinary scalar | Its plain-text view falls back to workspace; folder B stays unchanged. |
| Remove an explicit user null with `undefined` | The assignment disappears, and the default becomes effective. Null and removal differ. |
| Replace the workspace object with one omitting its array | Nested object properties merge from lower scopes. Folder A keeps its array; folder B falls back to the user array. |

The [replay](../evidence/vscode-configuration-20261124T071100228669Z/conformance.json) records one additional source change: `extensions.autoUpdate` moves from `false` to `"off"` during the nullable-removal phase. This was not an action requested by the fixture. Its exact trigger was not independently established, so it is not attributed to that nullable update. The adapter checks that observation explicitly rather than ignoring non-fixture keys.

The app exited normally after its extension requested quit. Only after confirmed retirement and a process-prefix check was its roughly 20 MiB private working directory moved into ignored capture storage. Original resource URIs retain their historical meaning; reopening the moved profile is not qualified. The [retention receipt](../evidence/vscode-configuration-20261124T071100228669Z/retention.json) and final source bytes remain attributable to that run.

The ordinary home directory was retained to avoid the earlier private-home keychain prompt. User-data and extension directories were private, and the supported `--use-inmemory-secretstorage` option was used. The app log nevertheless shows that the existing `~/.vscode-shared/sharedStorage` database was opened. Shared-storage writes were not measured. Do not describe this run as proving that all global application state stayed untouched. Normal user settings and documents were not selected or edited by the fixture. Workspace trust was disabled in the private profile; `isTrusted=true` establishes this fixture's context, not trust enforcement.

An [earlier attempt](../evidence/vscode-configuration-20261124T070819248153Z/disposition.json) failed before extension execution because its profile path exceeded macOS's 103-byte Unix-socket limit. It exited 1 and supplies no configuration cases. The successful run used a short private temporary path and a new capture identity. Both originals remain. The current producer also propagates nonzero app exit status after recording it; that later source change has syntax checks, not another graphical execution.

## Counterexample: documented inspection loses explicit-null provenance

Before nullable removal, all four contexts return an effective `null`. The saved user file contains the explicit null assignment. Yet the documented `inspect().globalValue` field is `undefined`, while `defaultValue` is the registered non-null default. Reconstructing effective values from those eight documented fields therefore yields the default instead of the observed null. This occurs in 36 captured projections: nine phases times four contexts.

The pinned [extension-host wrapper](https://github.com/microsoft/vscode/blob/8a14f0cc1b08d531eb83255ea3764ae22aa932b5/src/vs/workbench/api/common/extHostConfiguration.ts#L265) uses `config.user?.value ?? config.application?.value` for `globalValue`. Nullish fallback explains the lost documented field. Implementation-specific local/remote inspection fields exist in source but were not captured by this fixture. The finding is confined to the documented aggregate field and its reconstruction contract. It is not evidence of discarded source data, an incorrect effective getter, or an incorrect Settings UI display.

Preserve the current scope order, schema admission, explicit update targets, object merge, and actual getter. A focused candidate would preserve present-null in the aggregate inspection carrier rather than treating it as absence. Existing consumers might rely on the current fallback, and application/default-profile semantics need review before changing that wrapper. The keep-current alternative is to use the actual effective getter and exact source evidence when provenance matters, while documenting this inspection limitation. No upstream or empack source was changed.

## Models and verification

[Lean](Configuration.lean) models all eight ordered slots, recursive JSON-object merging, and replacement by arrays/scalars/null. Its replay matches all 132 raw-source effective projections. A separate replay of the documented inspection fields matches 96 and retains the 36 null counterexamples. Nine laws cover absent preservation, null presence, replacement, masking, and distinct current/proposed inspection behavior. The finite research decoder refuses unknown schemas, wrong scope counts, malformed presence carriers, and values outside its depth bound.

[Bend](Configuration.bend) independently projects only scalars: explicit null has a present tag distinct from absence, and the last applicable scope wins. It matches 88 raw-source scalar projections and all 88 inspection reconstructions, including their 36 disagreements with the native getter. Two controls distinguish current nullish inspection from the presence-preserving candidate. Four laws cover those carrier distinctions. Object merging is a Lean comparison, not a Bend claim.

Compile the models through the repository's formal check, then replay without launching VS Code:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/vscode/configuration_conformance.py applications/evidence/vscode-configuration-20261124T071100228669Z
```

The native evidence is one serial run. Replay is not another application execution. The [adapter](configuration_conformance.py) binds frozen producer, extension, raw observations, final source bytes, selected source hashes, and model versions separately. It keeps the original launch producer distinct from the current source-only exit guard. It rejects interpretations that every saved edit changes effective state, that folder settings always beat language defaults, that null means removal, or that a notification means a scoped effective change.

Before broader adoption, exercise the Settings UI and write-target feedback, nullable values at other scopes, application/default-profile behavior, remote and managed settings, combined language groups, concurrent external writers, rejected schema/scope updates, failed writes, and restart. Prove preservation of raw assignments and unsaved editor content independently of configuration notifications. Keybindings, workspace trust, settings sync, and configuration-triggered process authority remain pending.

## Consequences for empack

Keep raw authored assignments, source/layer identity, selected profile, effective interpretation, and captured operation basis separate. A successful source edit can be masked without being lost. An absent field in a lossy projection cannot establish that no declaration exists. Explain the winning source and edit destination near the affected value; show shadowed assignments without forcing needless deletion. For object-like schemas, define recursive merge, list replacement, null, and removal deliberately rather than borrowing editor behavior by accident.

This supports the proposed empack source/placement model and incomplete-draft boundary. It does not select a new merge policy for existing empack bindings, introduce a general settings service, or qualify portable/browser storage. Those changes require their own domain decisions and joined save/reopen/export evidence.
