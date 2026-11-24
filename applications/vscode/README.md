# VS Code: document versions, save points, and backing files

This first band covers VS Code desktop 1.147.0 at `8a14f0cc1b08d531eb83255ea3764ae22aa932b5` on macOS arm64. It compares one native file-backed document with serial edits, save, undo/redo, external changes, and explicit revert. A separate [browser band](WEB.md) observes an untitled draft across one page reload. Custom filesystem providers, asynchronous save races, and most editor/workspace features remain open.

## Separate state values

| Value | Meaning |
| --- | --- |
| Resource URI and document incarnation | Which resource/model the operation concerns. A URI alone does not identify a reopened model's lifetime. |
| `TextDocument.version` | Increasing edit/event version, including undo and redo. |
| Undo/save-point identity | Which history state corresponds to the last saved model state. It can be revisited while the event version increases. |
| Current buffer | Editable text, distinct from backing bytes and external actors. |
| Last resolved backing evidence | Observed file stat, encoding, and content basis used by the file model. |
| Dirty marker | The application's unsaved-change observation. It is not an independent fresh read of the filesystem. |

The pinned API definition matches the installed definition exactly. It documents the increasing version, dirty status, and Boolean save result. The inspected [`textFileEditorModel`](https://github.com/microsoft/vscode/blob/8a14f0cc1b08d531eb83255ea3764ae22aa932b5/src/vs/workbench/services/textfile/common/textFileEditorModel.ts) increments its version for content changes but uses `getAlternativeVersionId()` and `bufferSavedVersionId` to recognize return to a save point. Its successful-save handler only clears dirty state if the captured version still matches. Its error path preserves dirty content and records conflict/error state. Selected ranges and hashes are in [source selections](../sources/vscode-selections.json); the whole implementation is not qualified by those excerpts.

## Native observations

The [fixture](native-extension.cjs) used a separate VS Code process, user-data directory, extension directory, and generated project. It edited through the extension API and invoked the editor's undo/redo/revert commands. Independent Node filesystem reads captured backing text after each step. No user document or normal VS Code profile was edited.

| Step | API version | Dirty | Buffer / backing result |
| --- | --- | --- | --- |
| Open | 1 | No | Both contain the original text. |
| Edit, then save | 2 | Yes, then no | Save returns true and writes the first draft. |
| Edit again | 3 | Yes | Second draft is unsaved. |
| Undo | 4 | **No** | Returns to the first saved draft; backing is unchanged. |
| Redo, then save | 5 | Yes, then no | Returns to the second draft and saves it. |
| External write while clean | 6 | No | File watcher fires and the buffer reloads. |
| Edit locally, then external write | 7 | Yes | Buffer retains the local draft while backing changes. |
| Explicit revert | 8 | No | Buffer adopts the current external backing. |

The [twelve retained states](../evidence/vscode-native-20261124T014040385337Z/observed.json) include the open and quit snapshots. The native process exited 0, and a subsequent process inspection found no command referencing its private working directory. The window was closed before desktop access was released. The user reported a focus/selection change; the recorded text versions and contents match the commanded sequence, with no additional text edit observed.

The acquisition profile used a temporary `HOME`, which triggered a macOS dialog about storing “Code Key.” The user canceled it; no reset was requested. These observations therefore qualify the stated file operations, not keychain or credential behavior. The recorded runner source and actual launch arguments are retained. The current runner instead keeps the OS home, isolates VS Code's profile paths, and requests in-memory secret storage; that revised startup has not been exercised by this record. Do not relabel the old run as execution of the revised configuration.

## Models and checks

[Lean](Document.lean) separates event version, current and saved history points, and independently observed backing. Seven laws cover serial save, history movement, external dirty-buffer preservation, and revert. [Bend](Document.bend) executes the same serial projection with two checked laws. [Retained replay](conformance.py) compares all twelve native states with both models and rejects treating a larger API version than the last save's version as sufficient evidence of dirty content.

History-point keys in the adapter are admitted logical labels, not exported VS Code internal IDs. The model does not implement undo grouping/branching or prove every native version increment policy. This fixture uses one LF/ASCII file with serial actions and successful writes. It does not exercise save errors, encoding changes, conflict confirmation, a concurrent save, crash recovery, keyboard navigation, or screen readers.

Compile `Document.lean` to `.build/applications/vscode/Document.olean`, then replay with the pinned model tools:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/vscode/conformance.py applications/evidence/vscode-native-20261124T014040385337Z
```

Replay does not run VS Code. `native_fixture.py prepare` creates private fixture data. Launching it or requesting editor actions requires current re:desktop ownership; each action is separately gated by the operator. The runner's `request` operation waits for the recorded terminal result and directs inspection before retry on timeout. Desktop access does not come from the script itself.

## Custom-provider evidence stays separate

The earlier [host-provided fixture](../evidence/host-vscode-race-20261123/receipt.json) paused a custom provider's write, edited the document, and observed a false save result and clean marker with different buffer/backing text. Its source and observations were inspected, but it remains a provider/API-specific finding. The ordinary file-backed serial run neither reproduces nor closes that race. It must not be promoted into a general VS Code defect, or dismissed because the serial controls pass.

The source's save-completion guard and the provider adapter need a joined investigation: capture the exact serialized point, later edit identity, provider events and stats, settled model state, and another save/reopen. Include undo after a raced save and separate native/provider controls. Do not substitute the generic host model's monotonic counter for VS Code's history identity.

## Preservation and interface candidate

Preserve the separation already present in the implementation: edit ordering, save-point identity, resource incarnation, backing evidence, and dirty observation have different jobs. Preserve the demonstrated external-change behavior and existing conflict handling. This band establishes no new ordinary-file correctness defect.

An additive save receipt for automation is worth investigating. It could report the resource/provider/incarnation, captured edit basis, write outcome, saved point/evidence when known, current basis, and remaining unsaved work. Existing `save(): boolean` callers could remain supported. A false result should not require callers to guess whether nothing happened, a write failed, a newer edit remains, or a conflict needs a decision. The source already retains richer error/conflict and file-stat state; review existing internal events and APIs before adding another public surface.

The keep-current alternative is sound for ordinary editor use: the Boolean result and normal UI can be enough, while specialized extensions retain their own snapshots and inspect backing when their operation requires it. Any new receipt must avoid promising filesystem durability or independent freshness that the provider has not established. It must also preserve unsaved content, provider-specific capabilities, and unknown outcomes.

A general dirty-state rule should use the application's persisted projection or save-point identity. A monotonic operation clock still matters for invalidating stale work, but undo returning to saved content need not mean an unsaved change. The host owner has clarified that its forward-only edit/save projection does not model undo and that `newer_edit` means remaining divergence, not a raw API-version comparison.

No production editor or empack change was made. Most of VS Code's feature inventory remains pending, including general multi-root workspaces, extension trust/authority, tasks and terminals, SCM, save-as, provider permissions, and desktop/browser differences. The browser's served-version and one untitled reload are now observed separately; backing-file saves, permissions, and interruption recovery remain open. Desktop parity is not assumed.

A later [configuration band](CONFIGURATION.md) observes explicit settings targets and selected multi-root/language precedence through the native API. It preserves an explicit-null inspection counterexample. This does not qualify general workspace behavior, trust, or the Settings UI.

The [trust band](TRUST.md) models selected support-policy and trust-disable predicates from source with admitted adapters. It leaves installed trust enforcement, extension execution, and grant/revoke persistence unqualified.
