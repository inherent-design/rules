# VS Code: edit basis, provider results, and application

A returned edit is a proposal. Its coordinates can outlive the text used to compute them. A successful apply call establishes that the selected application accepted that operation; it does not establish that the proposal still means what its author intended.

This band observes VS Code desktop **1.148.0**, source `661626d0e72f97806550790a98fb87116c9db825`, on macOS arm64. Preflight detected an installed update before launch. The initial 1.147.0 pins and earlier studies remain historical. Thirteen selected current-source identities and inspected ranges are in the [source ledger](../sources/vscode-language-edit-selections.json). Matching source and installed metadata/bundle hashes are not a reproducible-build claim.

## Native results

The fixture opens one generated file containing `alpha beta`, followed by a newline. It registers its own formatting and rename providers. Where delayed, each provider computes its edit before a gate, the fixture inserts `shift `, and only then releases the provider. Resets are separate scaffolding. These are native extension API and editor-command observations, not built-in language-engine tests or visual UI reviews.

| Request | Recorded result | Buffer after the request |
| --- | --- | --- |
| Fresh `WorkspaceEdit`, replace columns 0–5 | `true` | `EDIT beta` |
| Store that object, insert prefix, then apply | `true` | `EDIT alpha beta` |
| Same delayed object, explicit caller version check | Caller does not call apply | `shift alpha beta` |
| Two nonempty `TextEditor.edit` calls from the same version | `true, false` | `ONE beta` |
| Await the first edit, then create the second | `true, true` | `TWOeta` |
| Nonempty edit followed by an empty builder | `true, true` | `ONE beta` |
| Compute formatting edits only | Edits returned | `alpha beta` |
| Compute delayed formatting edits, then caller applies | `true` | `FMT(alpha) alpha beta` |
| Normal Format Document command with the same delayed provider | Provider cancellation observed; command returns `undefined` | `shift alpha beta` |
| Compute rename edits only | `WorkspaceEdit` returned | `alpha beta` |
| Compute delayed rename edits, then caller applies | `true` | `REN alpha beta` |

All displayed buffers retain their newline. The sequential `TWOeta` result is deliberate: both edits use columns 0–5, but the first replacement shortens the word. Awaiting a fresh version does not recalculate an appropriate range. The empty second edit succeeds without a second change. Neither result should be presented as evidence of semantic correctness or a persisted save.

## Keep computation, submission, and application distinct

`TextEditorEdit` captures the document version when the builder is created. Nonempty edits carry that version to `MainThreadTextEditor.applyEdits`, which refuses a mismatch. The empty-builder path returns `true` before reaching that check. The parallel native case exercises the refusal; the sequential and empty cases distinguish two reasons for a successful second response.

`workspace.applyEdit` converts the public object when submitted and obtains the then-current document version. It does not preserve the earlier computation version merely because the extension constructed the object earlier. The loaded-model text-edit path validates version information before and after preparation, but that is a submission basis. The fixture does not capture the internal RPC; this timing is established by the selected source and the immediate API snapshots. Multi-resource atomicity, closed models, resource creation/deletion, and concurrent external writers remain outside the native case.

The compute-only formatting command returns edits after minimal-edit processing. The representation changes: the fresh formatting result becomes two insertions; the delayed result becomes different ranges with the same effect as replacing the original columns 0–5 in the current text. The observer independently applies those returned ranges to the recorded preimage and checks that equivalence. The model does not implement the diff/minimization worker.

The rename compute command similarly returns a public edit object. The provider adapter serializes its result without the live version provider used by `workspace.applyEdit`; public reconstruction does not retain an earlier application guard. Computing these results is useful for previews and custom workflows. It does not apply them or promise an atomic computation-and-application transaction.

The normal formatting route creates an editor-state cancellation source for value and position changes and checks cancellation before application. Native cancellation was observed within the fixture's 500 ms window. The generated provider still returned, and its completion was awaited before the next case. This distinguishes cancellation notification, callback completion, and whether edits were applied. The case does not isolate content changes from position changes or establish general cancellation timing. Interactive rename has a separate source path and was not exercised through its widget.

## Preserve APIs; strengthen consumer obligations

Keep compute-only commands, Boolean edit results, and the normal formatting guard. Their distinct purposes do not justify merging them into one command or silently applying returned edits. Document the empty-success and submission-version cases near extension examples. A consumer that computes edits asynchronously should retain its computation basis and recalculate or refuse when that basis changes.

The explicit caller check in this fixture is an **authored policy example**, not a VS Code refusal or a newly atomic public API. A check followed by submission can itself race in more general settings. Strong compare-and-apply needs an admitted revision check at the actual mutation boundary, with resource/incarnation and coordinate semantics appropriate to that application. Do not replace this with automatic retries against different text.

For empack's proposed portable editor, keep the already proposed revision-bound plan and application boundary. A preview, language-service result, successful no-op, accepted mutation, save result, and independently verified backing state need distinct facts. This is design evidence for that proposal; it activates no deferred production intent and introduces no production patch or compatibility framework. Existing API users retain their current semantics.

## Reproduction, preservation, and limits

The [native record](../evidence/vscode-language-edit-20261126T005327358915Z/observed.json), frozen extension/runner, current product/bundle hashes, request receipts, and [closure](../evidence/vscode-language-edit-20261126T005327358915Z/closure.json) are retained. Eleven requests and quit finished; the wrapper exited 0, the original process group was absent, and an exact private-work argument scan was empty. Desktop access was released and unsubscribed. This is scoped retirement evidence, not a census of arbitrary detached descendants.

The earlier [preparation-only record](../evidence/vscode-language-edit-20261126T005228104843Z/meta.json) launched no process. Its provider was reviewed and corrected to compute before waiting, then a new capture was prepared. Do not count it as a native failed case. The frozen native logger's object spread overwrote its completion label with `format` or `rename`; the observer recognizes the exact completion-record shape. Repeated document-change callbacks at the same text/version are not counted as separate edits.

The [Lean model](LanguageEdit.lean) has twelve laws, and the [Bend model](LanguageEdit.bend) has ten. They reuse the existing workspace version predicates and cover the bounded ASCII fixture. The [retained replay](language_edit_conformance.py) compares eleven four-field outcomes, checks returned payload effects, and runs nine DTO refusals, three changed-premise controls, and six changed-raw-observation controls:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/vscode/language_edit_conformance.py
```

Add `--public-only` to exclude current installed/source-cache/private-profile readbacks explicitly. Neither mode launches Code, a browser, or a provider. The [proof gate](../evidence/vscode-language-edit-20261126T005327358915Z/proof-gate.json) checks three Lean modules and two Bend files, including the reused workspace model. Initial research syntax/proof failures were corrected without changing native observations: a reserved Lean identifier, affine-use annotations, and an explicit recursive natural-number equality proof.

Private profile paths and in-memory secret storage reduce interference; incidental shared host-store writes were not fully measured. No personal project, extension, account, or world was selected. Visual/accessibility behavior, completion, navigation, diagnostics, refactor providers, interactive rename, arbitrary language engines, Unicode coordinate handling, browser/remote hosts, undo grouping, general cancellation races, and multi-resource transactions remain pending. The parent feature and scenario statuses remain unchanged.
