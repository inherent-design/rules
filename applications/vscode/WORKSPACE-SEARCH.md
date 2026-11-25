# VS Code workspace searches and staged edits

VS Code's workspace view, open editors, stored files, search observations, prepared edit ranges, applied edits, and saved files have different lifecycles. This band executes the installed 1.147.0 desktop extension APIs in one disposable multi-root profile. It records 21 states, including 18 selected API actions and three context/cleanup states. It does not operate the Search UI or a personal workspace.

The [source selections](../sources/vscode-search-selections.json) pin commit `8a14f0cc1b08d531eb83255ea3764ae22aa932b5`. The [native record](../evidence/vscode-search-20261125T061429674973Z/observed.json) and [normal exit](../evidence/vscode-search-20261125T061429674973Z/exit.json) cover one 3.656-second run. Independent [post-exit reads](../evidence/vscode-search-20261125T061429674973Z/host-observed.json) verify the final files/workspace and absent process group. Desktop access was released and the subscription removed after closure. The private profile occupies about 20 MiB; no engine or application build was needed.

The fixture disables autosave, workspace trust, updates, telemetry, and AI features. It uses separate user-data/extensions, ordinary OS home, and in-memory secret storage. OS-shared startup writes remain incompletely measured, as in the earlier configuration band. No normal profile, account, or user document was edited. An earlier prepared setup was superseded before launch; its retained marker does not count as another native run.

## Domain and operation boundaries

| Boundary | What the record exercises | What it does not establish |
| --- | --- | --- |
| Workspace membership | Add C after A/B, reject duplicate C, and remove B in an existing multi-root workspace | First-root transitions/restarts, remote identity, arbitrary names, concurrent writers, or general save durability |
| File discovery | Default, disabled, and relative-root file exclusions; membership after confirmation; pre-canceled request | Directory walking, ignore/glob/encoding engines, live cancellation, or process retirement |
| Text search | Explicitly enabled proposed `findTextInFiles`, configured exclusions, open dirty buffer, and an open outside file | Search UI, regex/whole-word/multiline behavior, RelativePattern text scope, all providers, or a stable API guarantee |
| Workspace edit | Stale ranges, missing text target, grouped file refusal, and interleaved partial effects | Every all-or-nothing case, arbitrary provider failures, rollback, undo, concurrent edits, or persisted publication |

The [observer](search_observations.py) checks the unchanged producer/extension, installed file identities, source hashes, initial settings and inputs, API positions/previews, buffer versus disk snapshots, final workspace, and retained effects. Match/glob/URI admission and prepared operation-group facts are explicit model premises. The [comparison](search_conformance.py) is a pure replay, not a new native run.

## Request acceptance exposes a provisional workspace

`updateWorkspaceFolders()` returns whether a valid request was started. The inspected extension host creates an unconfirmed workspace immediately; `workspaceFolders` can already show it while the main side completes the edit. A second request while confirmation is pending is refused. The confirmation event and failure handler settle that provisional state.

In the native fixture, adding C returns true and immediately exposes A/B/C, followed by an event adding C. Adding the same URI again returns false with no event. Removing B immediately exposes A/C, then reports B's removal. The final workspace file independently contains A/C. This supports the selected serial API flow; it does not turn every true return or provisional read into a persisted receipt.

Preserve confirmed and provisional membership separately in an automation model. Wait for the documented event before another request. A failed main-side edit should clear provisional state and remain visible to the caller. The current API already provides that distinction; no new universal workspace transaction type is needed for this fixture.

## Search scope includes both settings and observed editor state

Stable `findFiles()` uses `files.exclude` when its exclude argument is omitted, while ignoring `search.exclude`. Passing `null` disables those default file exclusions. The fixture's relative pattern limits file discovery to A. Adding and removing workspace roots changes subsequent file discovery after the awaited event.

The proposed legacy `findTextInFiles()` behaves differently in this pinned build. Its type definition says `useDefaultExcludes` defaults to true, but the inspected mapping sets `disregardExcludeSettings` to true when the option is omitted. The native default query includes both the file-excluded and search-excluded fixture. Explicit `useDefaultExcludes: true` filters the file-excluded entry while leaving the search-excluded entry. The source separately disables search-exclude settings by default. This is a bounded documentation/default mismatch on the selected proposed API, not a finding about the Search UI or newer search APIs.

The minimal improvement is to document the actual default and explain which exclusion settings that API uses. Changing runtime defaults could silently alter existing extension scope, so it needs a compatibility decision. Keep an explicit effective-scope record for automation instead of inferring identical behavior from similarly named searches.

The search service first observes open editors and then masks disk-provider results for every admitted open-editor identity. A recorded no-match is significant: the dirty A buffer contains `buffer-only`, while disk still contains `needle`. Searching `needle` omits A rather than falling back to the disk match; searching `buffer-only` returns A. Absence of an editor observation and an observed no-match therefore need different representations.

Showing `outside.txt` in this window also lets the broad `**/*.txt` text query return it, although it is outside the registered workspace roots. The source's open-editor predicate evaluates global query patterns separately from provider folder enumeration. Callers whose authority is restricted to particular roots must validate result identities; this band does not establish whether a RelativePattern text query supplies the necessary restriction. That is a specific remaining source/native control, not a claim of unrestricted access or a confirmed security incident.

## An edit's planning basis is earlier than its submission basis

The fixture prepares a replacement for `needle` at columns 0–6 while A contains `needle base`. It then inserts `prefix ` before calling `applyEdit()` with the old range. The API returns true and the buffer becomes `fixed needle base`: the old coordinates replaced `prefix`, leaving `needle` intact. Disk remains `needle base` until the separately recorded cleanup save.

The inspected extension-host converter captures the current document version when submitting the edit. The backend validates that submitted version; it has not received the earlier caller's planning version. This is consistent with an API accepting explicit ranges in the current document. It is not evidence that VS Code promises, or fails, to rebase arbitrary caller plans. The submission version in this study is source-derived from the immediate API observation, not an intercepted RPC field.

Automation that requires a frozen search/preview plan should retain resource/incarnation, planning version, ranges, and intended content. It should revalidate that basis before applying. An additive expected-version option could reuse the internal `ResourceTextEdit.versionId` guard while preserving existing current-range callers. That would need a reviewed public contract for reopened documents, multiple resources, snippets, notebooks, and undo. It is a proposal, not an implemented API or an adopted empack design.

For empack's authoring candidate, a successful host edit or export request must remain bound to its captured draft and inputs. A version captured only when execution starts cannot retroactively establish that an earlier proposal is still current. Reuse the existing host revision/admission laws; preserve save-point identity separately from monotonic operation order, as established by the document band.

## Failure and partial effects

A text-only batch targeting A and a missing file returns false without changing A. Two adjacent create operations, the second targeting an existing file, also return false without retaining the first new file in this fixture. The [retained native diagnostics](../evidence/vscode-search-20261125T061429674973Z/diagnostic-excerpts.json) identify the missing target and two existing-file refusals. These are selected refusal controls, not a proof of arbitrary provider rollback or every internal preparation step.

An interleaved batch creates a new file, changes A's buffer, then fails to create an existing file before a later text operation. It returns false while retaining the empty new file and the earlier dirty-buffer prefix. The final text operation is not applied. The source groups edits by resource kind and executes groups in order; later failure does not erase earlier group effects. A Boolean result alone does not distinguish these two kinds of false outcome.

The keep-current alternative preserves the documented ordered resource-edit behavior and lets extensions inspect their affected resources before retrying. A richer receipt could report completed groups/resources, failed phase, and unknown effects. It must not promise rollback or storage durability that the provider did not establish. Pure text preflight and ordered mixed-resource effects should stay distinct.

## Models, controls, and remaining work

[Lean](WorkspaceSearch.lean) has 16 laws for provisional membership, result masking, version bases, and effect prefixes. [Bend](WorkspaceSearch.bend) has nine laws and executes the same selected decision projections. Both compare against 18 native API actions; the three remaining rows establish initial/draft context and an explicit cleanup save. The replay refuses 17 unsupported research inputs and detects five changed premises and five changed native observation fields. Native evidence is immutable; the initial research DTO's missing default-valued fields were corrected in the adapter before comparison, without rerunning the app.

```sh
python3 applications/vscode/search_observations.py
LEAN=/path/to/lean BEND=/path/to/bend python3 applications/vscode/search_conformance.py
```

The original collection used `search_probe.py prepare`, then `search_probe.py launch <prepared-directory>` while holding re:desktop access. The fixture's final save is recorded as cleanup and is not attributed to the earlier `applyEdit()` calls.

General workspace editing, UI preview/replace, source/encoding engines, relative text-search scope, providers and permissions, real races/cancellation, document reincarnation, persistent recovery, and desktop/browser/platform parity remain open. The inventory adds scoped evidence to workspace, search, and document features while leaving their complete operation records pending. No product source or release policy changed.
