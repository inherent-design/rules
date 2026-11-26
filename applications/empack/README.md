# empack: current contracts and a portable target model

This is a design proposal within the application study. It preserves the checked-out native contracts at `0b4462e3032b4f09230b15329722eabefb7f574c` and considers the separate 0.9 portable-authoring candidate. The [source selections](../sources/empack-selections.json) identify the inspected files and ranges. This proposal changes no production code, schema, command, or release requirement. Most feature-level implementation comparisons remain pending in the [inventory](../inventory.json).

The separate [current ownership band](OWNERSHIP.md) has actual core API and installed-CLI evidence. The [synchronization scope band](SYNCHRONIZATION.md) separately models nonempty retained graphs, fresh resolution scope, alias rebinding, and exact runtime retention. It does not qualify the proposed portable-authoring implementation. The [Java policy band](JAVA.md) separately compares exact-game profiles, preference, constraint intersections, and actual-major admission; native engine probing and whole-modpack compatibility remain distinct.

The [removal/re-adoption band](REMOVAL.md) compares current core demotion, exact deletion, known/unknown evidence, and identical-request merges. It keeps author requests, retained selections, and actual file deletion separate; the deferred UX implementation remains unstarted.

The [author-transition review](AUTHOR-TRANSITIONS.md) traces observed-content adoption and explicit runtime migration through identification, authored policy, native preparation, and publication. It classifies existing test bodies without claiming a fresh run, and separates automatic retention of a locked version from preservation of an authored exact pin.

The later [released migration workflow](migration-flow/README.md) supplies two native target-validation branches: compatible-pin retention, incompatible-pin refusal, and explicit unpinning before reselection and publication. Its scoped models also retain a structured-preview global-flag ordering inconsistency. These are reference-only one-root workflows; they do not qualify gameplay, general graph migration, or the proposed parser correction.

The [native identity band](IDENTITY.md) separates live object equality, durable comparison, content observations, and recovery authority. Synthetic device changes preserve durable comparison while fresh live equality remains strict. This is source-function evidence, not a reboot, state lookup, or recovery qualification. The distinction must survive portable extraction; native evidence is not a portable project revision.

The [state discovery band](ROOT-STATE.md) compares actual directory lookup with Lean and Bend and retains a source-supported initialization-lock concern. The subsequent initializer band executes the selected writer chain and controlled interruptions; complete Engine/CLI composition remains pending. A returned state key alone supplies no observed state or execution authority.

The [initializer band](INITIALIZATION.md) reproduces current-source interruption windows through the selected writer chain. A private metadata-lock candidate improves post-lock retry but still strands at temporary allocation. Mixed schedules show distinct locks can coexist. The protocol models preserve these counterexamples; complete Engine callers, revised directory publication, and platform qualification remain pending.

The [channel band](CHANNELS.md) keeps incoming offer authentication, saved-envelope revalidation, durable observation, and installed release separate. Its candidate exact saved-floor check can reuse current authentication/equality; it does not require another trust system or change the no-expiry policy. Root, publication, and acquisition behavior remain implementation/verification obligations.

The proposed split is between editable project data, interpreted meaning, retained exact inputs, verified outputs, and host effects. It should make browser authoring possible without turning incomplete documents into valid intent or weakening native publication and process ownership.

The [recovery band](RECOVERY.md) exercises installed CLI inspection, planning, confirmation, and execution against tiny authored journals. It preserves saved direction, stale approval refusal, and role-specific image demand. A corrupt before-image can preview successfully, then fail with new private scratch while preserving the target and journal; earlier verification remains proposed. Actual interrupted producer and multi-file recovery remain pending.

The [portable-storage feasibility band](PORTABLE-STORAGE.md) executes real browser input, OPFS/IndexedDB save/reopen, worker-loss boundaries, and project-backup downloads in Chromium and WebKit. Restored selected inputs produce identical native Prism inventories. This component is a research host adapter, not browser distribution export or a production project format. Its scoped models match captured save/reopen boundaries; the later joined study composes a separate shared research engine.

The [shared-core band](PORTABLE-CORE.md) runs the same unchanged Rust inventory core and research adapter natively and in actual Chromium/WebKit WASM workers. All 32 packet results agree; the existing projection models cover the semantic subset. This component does not itself qualify document interpretation, layout/byte verification, consumer assembly, or the save/reopen/export join. The later document and joined studies supply their own bounded evidence.

The [shared-document band](PORTABLE-DOCUMENTS.md) then runs the unchanged current document codec and submodules across those hosts, preserving author/binding composition, encoding, raw/semantic identity, inspection, and selected edits. Its 34 requests agree exactly. This document component does not itself qualify consumer assembly or the project-store/export join; use the later joined study for that research workflow.

The [manual acquisition and saved-build band](PENDING.md) compares isolated installed-CLI inspection, partial retention, exact selection, damaged retained-byte refusal, and discovery through archive publication. Retained metadata is not byte verification, a saved recipe is not an execution grant, and recipe cleanup is not content collection. Whole pending/cache workflows remain unqualified.

The [archive band](ARCHIVES.md) separates raw metadata, opaque names, portable destinations, and member evidence. Actual core APIs, an attributed raw-parser harness, and disposable native imports cover selected name/budget/encoding/collision/CRC boundaries. Decoder-wide, private-witness, allocation, extraction-race, and platform obligations remain explicit.

The [bootstrap band](BOOTSTRAP.md) compares actual packaged invocation/local/cache gates and delegated cancellation, with controlled script peers and four separately limited real native checks. Selected code, capability, acquired bytes, process lifetime, and final outcomes remain distinct; official acquisition and real runtime supervision are not qualified.

The [joined portable-authoring band](PORTABLE-JOINED.md) now exercises actual import, invalid/valid save and reopen, metadata/path edits, captured-image Prism export, and browser downloads with a shared Rust research engine. Native, Chromium, WebKit, and an isolated installed0.8.8 reference produce the same fixture archive. This advances the selected research join; production format, provider/recipe breadth, authority, crash/concurrency/quota, and consumer launch remain open. Earlier component reports retain their original evidence scope.

The [selection-policy source map](SELECTION.md) connects catalog scope and ordering, exact pins, required relationships, update preparation, synchronization, migration, and partial application. It identifies existing test boundaries without claiming a new test run or broader native conformance.

The [author-to-recipient band](update-flow/README.md) joins one released-CLI provider update, delayed materialization, bundled/reference Prism snapshots, and first native recipient preparation. It compares saved selections with actual payloads and scoped checks. No bootstrap, Prism, or game launch ran; an existing recipient's later update and subscribed delivery remain pending.

The later [local signed-input join](subscribed-flow/README.md) reuses earlier native exports through key setup/staging, explicit enrollment, saved offers, first installation, failed local acquisition, later installation, old-consumer ensure, and rollback. It qualifies those selected game-layout transitions without hosted transport or launch. The earlier Prism join remains a separate profile.

The [saved-offer follow-up](saved-offer/README.md) confirms a selected forensic validation gap in the released CLI: a valid saved envelope can be used with an older, disagreeing floor through local preview, installation, and a passing consistency check. Its exact-saved correction remains proposed; no ordinary producer/crash origin or remote exploit is established.

## Keep the current guarantees

The current `DocumentCodec` composes author and binding documents, validates intent, and retains raw bytes and semantic revisions separately. The [document/approval band](DOCUMENTS.md) shows why: comment-only or absent-to-empty binding changes can preserve semantic lock currency while invalidating an old raw-bound write. `DecodedIntent` keeps those values private; `ProjectIntent` remains a programmatically editable value that must be validated at its boundaries. Do not replace strict decoding with a parser that drops invalid sections to manufacture a usable project.

`PreparedOperation` retains private engine-owned data. Authorization checks the exact plan, network/installer/runtime permission, and replacement footprint. `Engine::start` checks the owning engine. These distinctions survive extraction: a preview, serialized plan description, imported project, or UI Boolean cannot construct the execution proof.

`ContentLease` retains private bytes and verifies copies. `DependencyContent` distinguishes materialized bytes from admissible remote obligations; local and archive-member content require materialization. Keep that distinction when a consumer can distribute references. “Export ready” does not always mean that every remote mod has been downloaded locally, while a custom local JAR cannot become a filename-only reference.

The existing native publisher, instance reconciler, and process supervisor retain their own authority. A portable source path is not a native root, an accepted local edit is not publisher content, and cancelling a task is not proof that its process or writer retired. No generic host callback may attest all of these by returning success.

## Target values and owners

| Boundary | Proposed values and relations | Owning responsibility |
| --- | --- | --- |
| Editable project | `DraftDocumentSet`, stable authored-entry keys, source mappings, unresolved requests, profiles, choices, extension data | Preserve all editable meaning and original bytes, including absent versus empty bindings. |
| Editor session | Project identity, session incarnation, edit epoch, current immutable `ProjectImage`, history, selected saved image | Order work and preserve drafts; present save state without using an edit counter as a content comparison. |
| Interpretation | `Interpretation` with image basis, validated intent when available, diagnostics, unresolved decisions | Reuse strict semantic validation; an invalid interpretation does not prevent saving raw work. |
| Exact selection | Runtime, logical dependency keys, provider identities, pins, file roles, placements, closure evidence | Preserve sync, update, adoption, and runtime migration as distinct policies. |
| Sources and assets | Declared source obligations, immutable retained assets, original assertions, observed content IDs, portable attributes | Separate requested content, observed bytes, authenticity, availability, and physical backing ownership. |
| Prepared work | Target-specific required inputs, capabilities, immutable capture, plan identity, exact authorization | A sealed operation owns its inputs; changing the editor cannot mutate them. |
| Verified output | Consumer inventory, portable attributes, consumer evidence, immutable artifact bytes | Verify the chosen recipe and its representational losses before delivery. |
| Delivery and publication | Destination-bound finalization, native publication receipts, recovery state | Report actual effects and uncertainty; do not treat writer start or object creation as completion. |
| Installation | Exact release, side, choices, managed/seed ownership, local deviations, retained history | Preserve the recipient's state and update authority independently of author editing. |
| Execution | Host-selected program, runtime compatibility, owned process group/job, terminal and instance leases | Native execution and recovery stay native; browser capability absence is explicit. |

`ProjectImage` identifies the complete saveable project projection: raw authoring inputs, virtual source mappings, authored policies, unresolved decisions, and relevant extension state. Its exact wire representation and hash are not selected here. The project format must explicitly decide which session/history state persists; saving the current image is not a blanket claim that undo history was backed up. Display names, native inodes, and an edit counter are unsuitable identities. Live permissions and storage availability are observed host state, with attributed saved observations; they are not perpetual properties of an image.

An `AssetId` addresses an immutable captured asset. A `ContentId` describes observed bytes; an asset can also carry source assertions and original provenance. Physical backing identities and leases belong to storage. Several placements or selections can use the same payload without becoming the same dependency, entry, or deletion authority. The JavaScript peer-context and restic lineage studies explain why bytes and provenance edges cannot substitute for every other relation.

The [source/placement and projection study](SOURCES.md) compares 32 actual pure-core cases and explains how virtual sources, bindings, profiles, and template interpretation fit this boundary. It does not qualify the native/browser adapters. The [template band](TEMPLATES.md) separately compares standalone Prism builds, exact addressing and encoder source, and Java-properties readbacks. Mode selection, output-language quoting, consumer interpretation, and publication retain their own evidence limits.

[Observation demand](OBSERVATIONS.md) also depends on the operation's role. A protected installed seed can be preserved without claiming its byte identity; the publisher's source for that seed still requires bytes when exporting a bundled distribution. Shape, byte evidence, retained inputs, and publication authority must remain distinct during extraction.

## Session and operation interfaces

These are boundary sketches, not existing Rust signatures:

```text
DraftSession.capture() -> RetainedProjectImage
Engine.interpret(image) -> Interpretation { basis, valid_intent?, diagnostics, decisions }
Engine.propose(image, edit_request) -> ProposedEdit { basis, change_set, evidence }
DraftSession.accept(proposed_edit) -> Changed | StaleBasis

Engine.prepare_export(image, recipe, decisions, capabilities)
    -> Ready(PreparedExport) | NeedsInput | UnsupportedCapability
PreparedExport.authorize(exact_grant) -> ApprovedExport
Engine.start(approved_export) -> OwnedOperation<VerifiedOutput>

ProjectStore.prepare_save(image, expected_saved_revision) -> PreparedProjectSave
ProjectStore.commit(prepared_save) -> ProjectSaveOutcome
DraftSession.observe(save_receipt) -> UpdatedSavedBasis | HistoricalReceipt | ForeignBasis
```

An asynchronous worker takes a captured image rather than holding a mutable editor borrow across its work. Background interpretation may be retained historically, but only a matching session/epoch/image basis may replace the current interpretation. An edit proposal requires explicit acceptance against its basis. Diagnostics and a proposal are not write authorization.

The [VS Code language-edit case](../vscode/LANGUAGE-EDITS.md) supplies a concrete counterexample to substituting submission freshness for that captured basis: an accepted workspace edit can still carry old coordinates. Keep the existing target sketch's basis check at `DraftSession.accept`, where the mutation is authorized. A caller-side preflight check alone is not an atomic compare-and-apply contract. An empty success or a returned formatting/rename proposal also cannot mark an image changed, saved, or semantically correct. This supports the proposed boundary; it selects no new production API or migration mechanism.

Publisher observation and instance application need separate result stages in the target API. The signed-input join confirms that an accepted floor can outlive an unsuccessful installation, and rollback need not lower that floor. Derive each stage's result from its actual receipt/current record; do not collapse it into one update-success Boolean or add another persistent status file. Native enrollment, key custody, root-bound selection, and write authority remain host capabilities rather than properties granted by an imported project image. A future portable signing host needs its own custody/admission profile before it can supply those proofs.

Authentication must also name its role. Incoming-offer admission may advance a floor; revalidating an already saved observation must establish exact agreement with that saved floor. Structural decoding, valid signatures, a matching native root, and unchanged record bytes do not supply that agreement by themselves. Reuse the current verifier with an exact saved-role check; an additional proof wrapper is useful only if callers need to carry that distinction. Keep inspection and explicit recovery available without granting installation authority from inconsistent data.

The [Prism task study](../prism/LAUNCH.md) also separates a stop request, its acknowledgement, terminal outcome, finalization, and physical process retirement. Preserve empack's separate runtime-ownership and cleanup obligations through extraction. A portable event can report a pending stop request without marking its effects retired; synchronous completion may also precede the request method's return. Human and SDK results must retain the actual outcome and cleanup evidence in either order. The [VS Code activation follow-up](../vscode/ACTIVATION.md) adds native evidence that saved policy and admitted descriptions can change independently of already running code. Preserve empack’s own authority, leases, and explicit retirement receipts; a saved author or instance choice does not attest a game’s runtime state.

Saving project data is not native valid-project initialization. A new native draft-restoration operation must coordinate its files and host metadata recoverably without constructing a valid resolved project from malformed inputs. Existing initialize/import/publication operations retain their current stricter proofs. A portable project archive cannot supply a native recovery journal or a trusted tool execution request.

The [authoring lifecycle model](AUTHORING.md) separates edit ordering, saved images, receipt ordering, incomplete drafts, and retained plan inputs. An export deliberately captured at image A may finish while the editor moves to B, provided the operation owns every required immutable input and its other proofs remain valid. Its receipt names A. It cannot mark B exported or saved. This is an additional portable snapshot boundary; an ordinary native plan still revalidates its native root/read set and cannot bypass a changed file by calling it an old snapshot.

The [current operation-runtime band](OPERATIONS.md) checks caller/observer drop, retained results, a blocked file owner, attempt acceptance, late progress, simultaneous faults, and concurrent shutdown. It preserves those source/native facts separately from the boundary sketches above; full Engine/CLI and portable integration remain unqualified.

## Feature coverage and extraction boundaries

The [boundary map](boundaries.json) assigns all 52 inventoried empack feature families to the following owners. It is a target-design map, not implementation or test coverage.

| Area | Preserve through the target model |
| --- | --- |
| Authoring and selection | Schema/identity rules, source-specific assertions, stable selectors and file roles, layers, optionality, templates, exact pins, and distinct sync/update/adopt/remove/runtime-migration effects. |
| Consumer and publisher | Recipe-specific inventory, reference versus bundled delivery, immutable native releases, publisher trust, channel observation/sequence, and generated automation. Signing still needs explicit key custody. |
| Installation and recovery | Native roots, release baselines, seed/world protection, local decisions, exact repair, deliberate update, rollback versus interrupted-publication recovery, and runtime ownership. |
| Services and host use | Bounded archives/network, manual-input continuation, cache/retention, Java and installers, bootstrap, process/terminal handling, batch effects, configuration, diagnostics, and operation lifetimes. |
| Portable authoring | Raw incomplete drafts, immutable assets, undo/redo, background work, project save/reopen, verified export/delivery, browser routes, and the joined native/browser workflow. |

Extract by authority boundary, not by copying a command handler into each host. Keep pure validated values and planners in core, shared interpretation/recipes/verification in the portable engine, and root capture/publication/processes in native services. Browser storage implements the agreed host retention and publication protocol. The CLI and graphical clients translate requests, decisions, progress, and terminal results; they do not maintain independent resolvers or reconciliation rules.

Producer tools and game-specific validation can attach attributed results to an exact image, selection, or verified inventory through the existing extension boundary. Their findings do not authenticate source bytes, prove an empack artifact, or certify gameplay. External generators remain deliberate native tool operations where needed; this proposal does not add arbitrary command execution from project metadata or a second browser compiler.

## Interface consequences

Show distinct facts: “Not saved yet,” “Unsaved changes,” “Saved,” “Content missing,” and “Export ready” answer different questions. A restored draft is still editable even if content or permissions are missing. A completed older save updates the known stored basis without discarding newer edits. Stale background work cannot replace current diagnostics. An older export is labeled with its captured project image, not presented as the current draft's result.

Keep ordinary results concise and actionable. Details and structured output retain the same typed facts, source basis, uncertainty, and effect scope. A failed command may have cache/log effects or verified partial results; a nonzero process status does not prove no effects. Native recovery, terminal cleanup, and runtime retirement remain separately reported facts. No progress notification determines completion.

Existing command meanings and the recorded deferred UX work remain separate from this proposal. This study does not activate the deferred removal/re-adoption or update-preview implementation intent. Review CLI naming and grouping against the shared operation model before introducing additional commands or aliases.

## Adoption and verification plan

1. Audit the existing public constructor boundaries and strict codecs against their actual tests. Move reusable semantics without relaxing proofs. Establish native behavior baselines before extracting implementation.
2. Add immutable draft images and operation-specific interpretation as new concepts. Preserve original raw documents and missing references. Keep current native author schemas strict; the first new project format needs an explicit version and unknown-version refusal, not a speculative migration framework.
3. Implement the retention/session protocol with fault tests. Include stale work, undo returning to the saved image, late/out-of-order receipts, quota failure, worker loss, competing tabs, permission changes, and incomplete source discovery.
4. Prove and exercise the local-JAR/configuration import, placement editing, preview, project save/reopen, and Prism export flow on actual native and browser adapters. Compare semantic inventory, required attributes, and consumer interpretation. A simulated protocol or native in-memory adapter does not establish browser support.
5. Integrate the remaining provider, consumer, native installation, runtime, and publisher operations using their existing obligations and explicit capability admissions. Review the full target and evidence graph with the host owner before selecting production implementation.

The keep-current alternative remains useful: improve native library boundaries and expose typed operations while leaving browser project editing unimplemented. That avoids claiming unsupported capabilities, but does not satisfy the 0.9 portable-authoring candidate. A GUI-only wrapper around today's valid-project native model would still be unable to preserve incomplete editable projects correctly.

This design chooses no new service, generic plugin scheduler, publication platform, or migration framework. Unsupported current internal state must remain protected; a clean format break is not deletion authority. Most feature-level models, native comparisons, joined flows, and application-specific proposals across the broader study remain open.
