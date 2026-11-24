# Browser handles: names, aliases, and retained identity

This band executes the pinned VS Code 1.147.0 handle registry and IndexedDB transaction methods with real Chromium OPFS handles and IndexedDB. It establishes six bounded source-fragment outcomes. It does not execute vscode.dev's normal picker, workspace switching, or editor save flow, and it does not reproduce an end-user data-loss incident.

## Current model and observations

The browser provider keeps separate in-memory maps for file and directory handles. Registration derives a resource path from the handle's name and checks collisions within the selected map. Both kinds use one persisted key space. Lookup tries the file map, then the directory map, then persisted storage. The [picker callers](https://github.com/microsoft/vscode/blob/8a14f0cc1b08d531eb83255ea3764ae22aa932b5/src/vs/workbench/services/dialogs/browser/fileDialogService.ts) pass native file and directory selections to that same provider. Full application admission, restoration order, and effects on editor state remain to be tested.

The fixture creates handles named `entry` under distinct private OPFS parents. A browser's real `isSameEntry()` establishes their identity relationships; their names alone do not. The [receipt](../evidence/vscode-handles-20261124T024804295Z/receipt.json) pins the application source, fragments, runner, Node, Playwright, browser, and observed bytes. The [raw outcomes](../evidence/vscode-handles-20261124T024804295Z/observed.json) distinguish current-memory lookup from lookup through a new provider object.

| Case | Returned aliases | Lookup through the first alias |
| --- | --- | --- |
| Same file twice | Both `/entry` | Same native entry in memory and persisted lookup. |
| Two distinct files, same name, one provider | `/entry`, `/entry-1` | First entry remains addressable. |
| File, then same-named directory | Both `/entry` | Current provider returns the file; a new provider returns the directory. |
| Directory, then same-named file | Both `/entry` | File shadows the original directory alias. |
| New provider registers another file before loading the old alias | Both `/entry` | Persisted alias now resolves to the second entry. |
| Transaction deliberately aborted during registration | `/entry` still returned | Handle works in memory; a new provider reports unavailable. The failure is logged. |

A new provider here means a new registry object in the same browser page, not a browser or application restart. The abort is explicitly injected into a real transaction. OPFS permission was granted; this does not qualify permission prompts or later revocation for user-selected local files. No user file, account, normal browser profile, or installed application data was touched.

The executed registry and transaction method bodies are unmodified, with fixture URI/path/error dependencies. These adapters admit only the tested exact-case root-level names. They do not implement the complete VS Code URI library, platform case-folding, or every error type. Source bodies and generated TypeScript/JavaScript remain in ignored working data; selected URLs and hashes are [recorded separately](../sources/vscode-selections.json).

## Models, controls, and scope

[Lean](Handles.lean) and [Bend](Handles.bend) project two equal-basename registrations into an initially empty registry, optionally replacing the receiver's memory between registrations. Five observed pairs agree with both models. They do not implement arbitrary suffix allocation, complete directory traversal, or concurrent registration. The aborted persistence case is checked directly against its retained observation rather than represented as a successful pair.

The [replay adapter](handles_conformance.py) rejects stronger interpretations that aliases always distinguish entries, that current-memory and persisted lookup always agree, and that a returned registration means it was persisted. It also rejects an impossible input claiming that one underlying entry is both a file and a directory. Replay never launches a browser:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/vscode/handles_conformance.py applications/evidence/vscode-handles-20261124T024804295Z
```

Compile `Handles.lean` to `.build/applications/vscode/Handles.olean` first. Seven Lean laws include the observed alias distinctions and the separate candidate binding rules. Three Bend laws check same-kind suffixing and immutable-slot rules. A passed model comparison qualifies this projection only.

Two earlier fixture runs remain excluded. `vscode-handles-20261124T024620992Z` stopped because the fixture assumed a file-as-directory lookup would return undefined; the provider threw unavailable. `vscode-handles-20261124T024650665Z` remained pending and its owned browser was terminated. Its error adapter was an object where the abort handler can construct an error; that mismatch is source-confirmed, but the exact pending step was not observed. Its final receipt also hashed a live edited runner file rather than the source captured at start. Both raw files and the attribution mismatch are retained; this run qualifies no case. The successful run fixes the error adapter, captures progress and page errors, and bounds evaluation. The current runner additionally freezes its source bytes at startup; that small attribution change has syntax checks but no new browser execution. These were fixture limitations, not product failures.

## Candidate: immutable identity, descriptive names

A candidate registry would assign stable opaque keys to native entry bindings and keep display names as attributes. All handle kinds would share that identity space. Reusing an occupied key for another entry would be refused; successful fresh registration would preserve every other binding. Persisted allocation must be transactional across competing owners. A read grant, a write grant, a usable in-memory handle, and a persisted binding would remain separate states.

The Lean candidate proves that an occupied key cannot be rebound, a fresh key can be bound, and other keys remain unchanged. Bend proves corresponding immutable-slot rules. These are candidate model laws, not an implemented allocator or persistence protocol. They assume that an admitted handle identity is truthful and that key allocation has the required ownership. Browser permission and storage finalization still require host evidence.

Registration could return a structured result containing resource identity, handle kind, local availability, and persistence outcome. An unavailable backing or permission should offer re-selection without implying that the visible draft was lost. Do not turn a transient failure to persist a handle into silent success for reopening. Existing source behavior deliberately retains the usable handle and logs the persistence failure; the keep-current alternative is reasonable for an ephemeral session, provided integrations do not interpret its URI as a durability receipt.

Existing serialized aliases are a compatibility constraint for a VS Code change. A transition would need to resolve and compare old handles before issuing new bindings, preserve references where identity is known, and request a decision where old aliases are ambiguous. Never infer which file was intended from the basename. This study changes no existing registry or saved state. For empack's new portable-authoring model, choose explicit resource identities before that ambiguity enters its project format; a name or host permission is neither a content identity nor saved-project evidence.

## Verification before adoption

Exercise normal file and directory pickers with equal basenames from different parents, reopened workspaces with unloaded handles, and two concurrent registering tabs. Capture the exact application URI, working-copy identity, persisted handle, permissions, and actual write target before and after each transition. Keep unsaved drafts and inspect backing bytes independently. Add quota failure, denied/revoked permission, failed transaction, and browser-process restart controls. Test case-folding and generated suffix names with the real URI implementation.

For a candidate registry, demonstrate atomic fresh-key allocation and refusal of rebinding while preserving existing drafts, recent-resource references, undo history, and pending operations. Then prove and exercise the joined open/edit/save/reopen path. The full UI reproduction remains outstanding; this band supports an identity-design concern and a concrete next test, not a claim that vscode.dev has been broadly qualified or that its current users lost data.
