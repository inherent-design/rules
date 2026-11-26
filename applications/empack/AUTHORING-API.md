# Authoring operations: current API and portable proposal

Keep the existing distinctions between author intent, exact selection, observed files, native preparation, approval, and publication. The current API already represents most of them. The portable design should extract semantic planning and introduce revision-bound draft edits, while retaining the native engine's private preparation and authorization boundary. Combining everything into an `update` operation would lose meaningful policies rather than simplify them.

This is a proposed design at empack `0b4462e3032b4f09230b15329722eabefb7f574c`. The [operation map](authoring-api-map.json) connects nine contracts to current symbols, [source ranges](../sources/empack-authoring-api-selections.json), existing models, and bounded observations. It is not a new public schema, implemented service, or complete feature qualification. The review reads fifteen pinned sources and eight installed CLI help outputs; it runs no new engine tests, native mutation fixture, or formal model.

## Retain distinct requests and effects

| Intent | Current implementation boundary | Preserve in the target |
| --- | --- | --- |
| Inspect selection information | `AssessmentRequest`, `UpdateAssessment` | Scoped catalog and relationship observations, including incomplete or failed evidence. An assessment is neither a ready native plan nor a compatibility certificate. |
| Add a request | `AddRequest`, `AdditionPlan`, `ExistingDependencyPolicy` | Explicit authored requests, canonical bindings, and replacement permission. Existing retained content does not mean the author request already exists. |
| Reconcile current intent | `SyncRequest::Recorded`, `AcquiredReferences`, `Supplied` | Valid exact selections, role-specific materialization/references, and fresh resolution only where required by changed intent. |
| Select changes | `UpdateRequest` and the update host | Requested scope, authored pins, permitted selections, explicit pin edits, and per-group results. “Different” need not mean “newer.” |
| Change pin policy | `SyncRequest::SelectionIntent` | Pin/unpin changes authored selection policy while retaining current exact selections. Unpinning does not perform an update. |
| Record existing files | `AdoptObservedRequest` | Verify the selected existing payloads, then publish their description. Do not install missing bytes or silently replace a local source. |
| Change runtime | `SyncRequest::Migration`, `MigrationOptions::compose` | Explicit target runtime and permitted provider replacements; retain unrelated roots, pins, and preferred Java, then validate them for the target. |
| Forget requests | `RemoveRequest`, `RemovalMode::ForgetRoots` | Remove author-root roles while retaining exact records and content. |
| Remove content | `RemoveRequest`, `RemovalMode::RemoveContent` | Explicit selected deletion with required-edge, evidence, content, ownership, and native publication checks. Acknowledging unknown evidence cannot override a known requirement. |

These are operation meanings, not nine new commands or crates. Keep the existing core planners and document codec as the interpretation owners. `SyncRequest::Migration` already reuses synchronization machinery while retaining its distinct basis and policy. `UpdatePreview` already separates changed selections from explicit author-pin edits. `RemovePreview` and `RemoveReceipt` already carry the mode and incomplete evidence. Reuse those facts before adding another planner or report subsystem.

Current CLI defaults remain deliberate: installed `update` prepares a preview unless `--apply` is present; `add`, `sync`, `adopt`, `migrate`, `remove`, `pin`, and `unpin` use their normal approval route and support `--dry-run`. `--yes` supplies noninteractive approval; it does not substitute for update's `--apply`. Installed help is retained with the review. A prose mention of `--apply` in add's help is guidance about update, not an add option.

## Values, bases, and authority

Preserve three bases rather than call all of them a revision:

1. **Editable image and attempt.** Project/session identity, immutable image identity, and edit epoch bind a background interpretation or draft proposal. Undo can return to an earlier image without reviving an old attempt. These are the proposed [authoring lifecycle](AUTHORING.md) values.
2. **Semantic selection.** Valid interpreted intent, exact records, logical/canonical bindings, file roles, and admitted provider observations determine a semantic candidate. Raw comments and absent-versus-empty bindings can matter to publication even when semantic selection is unchanged.
3. **Native read set.** Current `ProjectRevision` includes the selected root's object identity and raw intent, optional binding, and optional lock revisions. Captured file observations and native ownership remain additional preconditions. A portable image ID cannot replace them.

`AddRequest` and `UpdateRequest` allow an optional native `source_revision`; migration requires one, and acquired-reference synchronization may carry one. `AdoptObservedRequest` contains a resolved `AdditionGroup` while its engine preparation captures and verifies native state. Do not describe these signatures as uniformly caller-bound today, or label the optional forms defective without evaluating their intended capture-time semantics.

For portable extraction, make the distinction explicit at the boundary: an externally resolved proposal names its immutable image/interpretation basis, while a fresh native action is deliberately interpreted against the backend's new capture. A stale background result must not silently become the latter. Check authored constraints and actual native preconditions again when bridging a draft proposal to publication. The basis envelope is a proposed contract; this review does not implement its token format or change the current requests.

`PreparedOperation` has private owner, view, and retained data. `authorize` checks the exact plan, network/installer/runtime permission, and replacement footprint. `Engine::start` also checks the engine owner. Keep these checks. A JSON preview, copied `PlanId`, serialized draft proposal, or client-supplied Boolean cannot construct an approved native operation. A native frontend keeps an opaque handle owned by its backend session; worker or backend loss requires reconciliation or re-preparation, not reconstruction of a private Rust proof from display data.

The inspected authorization test body checks a different plan's grant and unchanged measured scopes. That is source evidence of the intended regression boundary, not a fresh test run or a proof of every transport wrapper. The [native document study](DOCUMENTS.md) and [identity study](IDENTITY.md) retain their own raw-basis and root-identity qualifications.

## Proposed portable facade

This refines the boundary sketch in the [target model](README.md). Names and parameters below describe responsibilities, not new existing callable APIs:

```text
Engine.interpret(project_image) -> interpretation + diagnostics
Engine.propose(image, typed_operation, interpretation_basis, observations) -> ProposedEdit
DraftSession.accept(proposed_edit) -> Changed | StaleBasis
ProjectStore.prepare_save(image, expected_store_revision) -> PreparedProjectSave
ProjectStore.commit(prepared_save) -> ProjectSaveOutcome

Native backend: Engine.prepare(selected_root, current_request) -> Preparation
PreparedOperation.authorize(exact_grant) -> ApprovedOperation
Engine.start(approved_operation) -> owned native outcome
```

`Engine.propose` dispatches to the existing operation-specific semantic owners; it is not a second resolver. A real implementation can expose separate typed methods instead of a catch-all public enum. Its result contains the basis, intended operation, changed author requests, proposed exact-selection facts, outstanding decisions, and required capabilities. It does not contain native execution authority.

Accepting an edit changes the editor's current immutable image. It neither saves that image nor installs it. Saving may preserve an incomplete raw draft and explicitly missing sources. Native preparation still requires valid operation inputs and a fresh native root/read set. Browser asset import verifies and retains selected bytes; it is not evidence that those bytes are already installed under native ownership and must not be presented as native adoption.

Keep installed-path, declared-source, and retained-asset roles separate in the operation's observation demand. For an ordinary local adoption, both source and installed bytes must agree. A URL with explicit first-observed policy can record the deliberately chosen installed observation without authenticating a publisher. For synchronization or update, the source may instead supply bytes to install. The [native adoption evidence](adoption-flow/README.md) checks these differences directly.

This facade belongs at the proposed engine/native/wasm boundaries. It does not require moving all code into a new crate immediately. Reuse the unchanged codec/core extractions already exercised in [portable documents](PORTABLE-DOCUMENTS.md), [shared core](PORTABLE-CORE.md), and the [joined authoring flow](PORTABLE-JOINED.md). Existing native APIs remain a supported implementation alternative while production portable extraction is incomplete.

## Reports and outcomes

Derive human and machine views from operation facts. At minimum, distinguish requested roots, retained exact records, changed selections, pin-policy edits, proposed file effects, actual publication, and wider project warnings. Unrelated health information cannot automatically become an operation blocker; potentially relevant unknown evidence still needs its explicit policy and known requirements remain enforced. This proposal does not invent an independence proof where none exists.

Use the existing `ExecutionOutcome` distinctions: completed, partially completed, needs input, failed before publication, interrupted before publication, execution uncertain, and recovery required. A batch receipt describes only its completed groups. A lost publication response must guide inspection before retry. Cancellation requested and resource retirement are different observations. A saved continuation retains inputs and a recipe, not execution authority.

A zero-change preview can still verify content; the adoption fixture's two unchanged previews omit candidate detail. Preserve those fields as unreported rather than synthesize a reported digest. A renderer can say that no changes are proposed without implying that no inspection ran. A failed update observation must not be replaced by an older successful catalog row without attribution. Existing `DependencyAssessment` already separates current, permitted, compatible, upstream, completeness, provider problems, and reasons; preserve that information when simplifying its presentation.

Extend existing diagnostic context where necessary: logical key, source or destination role, exact affected path/identity, failed phase, scoped effects, and a safe next action. Keep stable codes and structured fields, redact secret-bearing locators, and keep progress off JSON stdout. A versioned frontend result envelope may carry the operation and basis alongside an existing preview/outcome. It must not flatten these outcomes into a single success Boolean or serialize an execution proof.

## Composition counterexamples and preserved decisions

| Existing evidence | Decision for the composed API |
| --- | --- |
| [Removal/re-adoption](REMOVAL.md): the same exact locked record can remain while an add request restores an author root. | Report request-role changes separately from selection changes. Reuse addition planning; do not substitute observed-file adoption or interpret zero changed records as no author edit. |
| [Native adoption](adoption-flow/README.md): a changed local destination alone refuses, while matching changes to source and destination can be recorded. | Ask which role supplies authoritative bytes; preserve the current checks while making the diagnostic actionable. |
| [Migration](migration-flow/README.md): an authored incompatible pin blocks the target; explicit unpinning precedes a separate accepted migration. | Keep policy edit, runtime proposal, and target validation distinct. No automatic unpin or “update everything” fallback. |
| [Synchronization](SYNCHRONIZATION.md): reporting's changed-record set can be empty while other lock metadata changes. | Carry the complete candidate and its actual document effects; never publish only the display summary. |
| [Draft lifecycle](AUTHORING.md), supported by VS Code observations: edit clocks and saved-image identity differ. | Bind async proposals to image and attempt; a completed old export names its captured image without claiming the current draft was exported. |
| [Native preparation](DOCUMENTS.md): semantically equivalent raw edits can invalidate an old approved write. | Preserve raw native publication preconditions after semantic planning. Re-preparation is not silent approval of a changed footprint. |

The comparator applications motivate these boundaries without imposing one package-manager policy on every product. npm/pnpm/Yarn distinguish author constraints, locks, installed graphs, and ordered overrides; Cargo separates selected units, artifacts, and execution; restic separates snapshot selection from reclamation and restore; MO2 profiles select effective views; Prism selection differs from serialized content; VS Code separates visible edits, saved state, and provider authority. Their owning reports remain the evidence, with their platform and source-method limits intact.

## Compatibility and implementation sequence

First keep the current request enums, planners, strict codec validation, raw-document identities, evidence policies, native ownership, and outcome variants. Map each frontend route to an explicit operation and basis. A library-only cleanup with improved reports is the keep-current alternative; it improves current clients but does not satisfy incomplete portable drafts.

Next extract image-bound semantic proposal construction over the existing core and codec. Implement draft acceptance, save, and native publication as distinct actions. Compare current and proposed candidates on the same retained inputs, including request-only changes, unknown evidence, authored pins, and unchanged exact records. Introduce no parallel interpretation path.

Then qualify the actual native/wasm adapters and their failure boundaries: changed editor image/epoch, same semantic but different raw basis, unavailable or replaced source, retained-dependent conflict, permission change, partial group completion, backend loss, and uncertain publication. Reuse existing observations before adding a new fixture. Run source/API tests at their actual contract level; do not count pure model agreement as native execution or broaden the deferred test-strategy intent here.

The selected new portable project format remains a clean break. It needs explicit versioning and preservation/refusal for unsupported data, not a general migration framework. The existing `migrate` command changes Minecraft/runtime intent; it is not a project-format migration or native-state adoption mechanism. Browser drafts cannot take ownership of legacy native recovery records. Signing, hosted publication, runtime execution, and consumer ownership keep their separate authority and unresolved capability requirements.

This review completes a source-grounded API direction for this authoring group, not all 264 empack operations or the nine-application study. Provider/CORS routes, broader sources/roles, serialized project/result formats, native bridge transport, authorization UI, supported-host concurrency/recovery, and complete comparator proposals remain open. No production edit, command change, deployment, or release is selected here.
