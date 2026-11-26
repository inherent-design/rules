# VS Code: preserve resource, policy, and execution boundaries

Keep VS Code's working-copy models, history/save points, file services, configuration layers, extension hosts, and task system. The evidence supports focused fixes and clearer interfaces at those owners. It does not justify replacing them with one revision counter, trust flag, or generic operation engine.

The [contract map](architecture-targets.json) and [source ledger](../sources/vscode-architecture-selections.json) retain two profiles: desktop/web source `8a14f0cc1b08d531eb83255ea3764ae22aa932b5` for 1.147.0, and selected desktop extension/language source `661626d0e72f97806550790a98fb87116c9db825` for 1.148.0. Earlier observations are not relabeled as the later release. Current upstream fixes, build reproducibility, supported-platform parity, and most complete features remain unqualified. This pass adds source/interface analysis, not a new application or model run.

## Existing owners

| Value | Owner and meaning |
| --- | --- |
| Resource and model | URI, provider/handle binding, and working-copy incarnation identify different things. A reopened model or replaced provider can keep the same URI. |
| Edit and save state | Event version orders changes; alternative history identity recognizes a saved point; buffer, backing, and dirty observation remain distinct. |
| Prepared change | Provider computation, returned ranges, submission basis, mutation result, and later save have separate lifetimes. |
| Workspace and query | Provisional membership, confirmed roots, open-editor overlays, query settings, and provider scope differ. |
| Configuration | Declaration, present assignment, source target, resource/language context, merge rule, and effective result differ. |
| Extension | Package files, profile membership, enablement policy, full admission, host placement, activation, and running code differ. |
| Task | Registered execution, readiness, task/process events, stop request, terminal outcome, and provider-owned resources differ. |
| Browser storage | Visible draft, backup, remembered handle, permission, completed file write, and exported artifact differ. |

These are responsibilities, not a proposal to serialize every value into a new common schema. Reuse existing events and internal results where their actual scope is adequate. New public inspection must have a specific consumer, compatibility contract, and authority to expose the relevant state.

## Saves and external reconciliation

Preserve the [document study](README.md): undo can revisit a saved point while the event version increases. Do not derive dirty state from a raw version comparison. Serial file-backed edits, watchers, dirty-buffer preservation, and revert have native evidence; arbitrary history grouping and asynchronous save races do not.

The [pinned text-file owner](https://github.com/microsoft/vscode/blob/8a14f0cc1b08d531eb83255ea3764ae22aa932b5/src/vs/workbench/services/textfile/common/textFileEditorModel.ts) already serializes saves, snapshots content, checks completion versions, and retains conflict/error state. Its cancellation path can cancel save participants without canceling a running write. It also offers retained-baseline external reconciliation, with version, encoding, backing-stat, cancellation, and diff-quality checks, followed by stale/conflict/unavailable outcomes. Preserve and qualify these mechanisms before proposing another merger. This is newly inspected source, not a native reconciliation or durability result.

An automation receipt may still help distinguish write outcome, saved basis, current unsaved work, provider/incarnation, and useful failure evidence. It should reuse actual save events and state, not infer a successful write from a clean marker or a false Boolean. Keep existing `save(): boolean` semantics for current callers. A successful write can coexist with later edits; a failed request can retain partial provider effects or a conflict needing a decision.

The earlier custom-provider race remains unresolved. Its false save result and clean observation with different buffer/backing cannot be promoted to an ordinary-file defect, and serial controls cannot dismiss it. A joined investigation must capture serialized content, provider events/stats, later history identity, settled state, another save/reopen, and undo. Source guards alone do not close that obligation.

## Provider registration, input custody, and writes

The [filesystem study](FILESYSTEMS.md) separates live registration from capability knowledge. The ordered bridge forwards historical capabilities on removal; a narrow invalidation candidate clears that entry in the source comparison. Prefer that correction to a new generation framework for this measured ordering. Qualify out-of-order RPC and provider replacement before claiming a stronger protocol.

A writable hint does not grant authority or prove a provider is present. Scheme-level read-only admission and per-resource backend permission are different checks. Preserve the provider's obligation to enforce actual permissions. A deliberately permissive provider is not an editor permission-bypass finding.

Pending work captures more than a URI. The native queue control writes to the old provider after disposal and re-registration, and mutating a submitted byte array can change later observed bytes. Consumers requiring a specific image should retain immutable input and the admitted provider incarnation. Do not silently reroute pending work to a replacement provider or infer cancellation from unregistration.

Keep actual effects visible: a rejected file write can leave a newly created parent. Removing that parent automatically would require its own ownership/concurrency evidence. Use existing file-service errors and per-operation results before inventing a transaction or rollback promise.

## Browser bindings and working copies

The [handle fragment](HANDLES.md) observes same-name alias collisions across kinds and registry instances, and memory/persisted disagreement after an injected transaction abort. Normal picker/workspace/save consequences remain unqualified. Names describe handles; they are not immutable backing identity or proof that a binding was persisted.

The candidate is one identity space for immutable entry bindings, with kind/name as attributes and transactional allocation. Preserve existing drafts and pending operations when a handle becomes unavailable. Permission, current handle usability, persisted binding, and resource content remain separate results. Returning an ephemeral usable URI can remain valid, provided it is not advertised as a reopen guarantee.

Unlike empack's new project format, VS Code already has serialized aliases and recent resources. Migration would need to resolve old bindings against actual entries, retain references where identity is known, and ask for re-selection when ambiguous. Never guess the intended file from its basename. The current candidate laws do not implement that migration, allocator, or concurrent-tab protocol.

The [vscode.dev reload](WEB.md) retains a visible dirty untitled draft in one profile. It does not qualify complete model bytes, browser-process restart, quota, eviction, local save, or export. Preserve the useful backup mechanism and its dirty presentation. A backup observation or browser API's presence is not a completed user-file or saved-project receipt.

## Workspaces, search, and computed edits

Preserve [provisional workspace membership](WORKSPACE-SEARCH.md). A true update result means an admitted request; a later event confirms the main-side change. Consumers should use the existing confirmation boundary before issuing another request, rather than interpret an immediate `workspaceFolders` read as durable publication.

Queries need effective scope, source, and context. File discovery and proposed text-search APIs have different exclusion defaults. Open editors can mask provider results, including an observed no-match, and the captured broad query can include an open outside file. A caller with root-limited authority must validate identities against its own admitted scope; this is not evidence of unrestricted filesystem access or a Search UI defect. Keep actual getters, explicit options, and observed editor/provider provenance rather than adding one universal search Boolean.

Change the proposed API's documentation/default only through a deliberate compatibility choice. Changing scope silently can change what existing extensions read or edit. Relative text-search scope, ignore/regex engines, and real cancellation remain required evidence.

The [language-edit study](LANGUAGE-EDITS.md) distinguishes computation from application. Current public workspace edits can acquire version information at submission, after an extension computed stale coordinates. Normal formatting has a different cancellation/application route. Preserve compute-only commands, no-op success, normal editor guards, and current-range callers. Do not silently apply or rebase returned proposals.

For frozen previews or asynchronous providers, retain computation basis, resource/incarnation, coordinate semantics, and intended edits. An additive expected-version API could reuse actual mutation-boundary checks, while preserving existing semantics. A caller check followed by submission is not a generally atomic compare-and-apply. Multi-resource edits, closed models, notebooks, Unicode coordinates, undo, and external writers need explicit verification.

Mixed-resource bulk edits also retain ordered effects when a later group fails. The native record contrasts that with narrower preflight refusals that leave the fixture unchanged. A richer result can identify completed groups and failed or unknown effects, but should not retrofit universal rollback onto existing provider operations. Retry must inspect the affected state first.

## Configuration provenance

Preserve [registered scopes, explicit targets, and merge rules](CONFIGURATION.md). Null, absence, removal, arrays, and recursive objects are distinct. A source file can change while every selected effective view remains unchanged; a notification is not necessarily an effective-value change for a given resource/language.

The native explicit-null counterexample concerns the documented aggregate inspection carrier, not the effective getter or saved source. A presence-aware carrier is a focused candidate; review application/default-profile and local/remote precedence before changing nullish fallback. Existing integrations can keep using the actual getter and source evidence where adequate. Do not delete shadowed assignments just to force one visible winner or introduce another settings resolver.

Any new origin report must name the lookup context and write destination. Profiles, remote policy, managed settings, combined language selectors, and Settings UI behavior remain separate. The configuration run's shared-store writes were not fully measured; private user-data paths did not prove complete OS isolation.

## Extensions: files, policy, placement, and activity

The [extension CLI study](EXTENSIONS.md) separates membership from retained package files. Uninstall removes the profile entry while version directories can remain; an exit-zero skipped downgrade is not a new installation. Reuse the existing extension manager and its actual diagnostics. Neither directory presence nor CLI completion proves admission or code execution.

Host placement is also independent. Ordered extension kinds, entry points, local/remote availability, development preference, trust, and later admission gates affect the chosen host. A browser window can have a remote Node host; a desktop window can host workers. Keep per-host capabilities instead of inferring them from the window's appearance or public `ExtensionKind` alone.

The [native activation flow](ACTIVATION.md) demonstrates saved workspace disablement while code continues running until normal shutdown, and enablement without automatic activation. Preserve that restart/reload model and the actual scope of “All” commands. Instant unload would be a new lifecycle guarantee, with unsaved work and blocked deactivation to consider. Use fresh execution and process evidence when continued activity or retirement matters; settled `isActive` is not a general liveness authority, and false during pending activation does not prove that code is absent.

An additive management inspection could reuse saved policy, full `EnablementState`, current runtime action/reason, affected IDs, workspace/profile, and separately observed host incarnation. Preserve existing API/SQLite meanings and do not silently restart hosts. Check existing UI and management APIs before adding another public envelope. Individual UI controls, concurrent writers, failed activation/deactivation, crashes, remote hosts, and worker retirement remain open.

The [trust predicates](TRUST.md) establish no correctness defect. Preserve explicit false, limited support, exact-version overrides, workspace-local restrictions, and the complete admission pipeline. Support declaration, trust decision, enablement, and actual execution are not interchangeable. Revocation does not automatically prove running-code retirement or a security sandbox. The selected function matrix and trust-disabled native profiles do not qualify installed grant/revoke enforcement.

## Tasks and native capabilities

Keep the [task system's existing identities and readiness](TASKS.md). An execution handle can precede a start event; process-end can precede task-end; a ready background dependency can remain active after its dependent finishes. These are useful policies, not reasons to replace the scheduler.

Custom PTYs can expose virtual PID `-1`. Never use an event PID as signaling authority; a positive PID still needs an independently admitted ownership binding. `terminate()` returning does not establish child retirement. Preserve absent API status separately from a child journal, and do not manufacture exit zero. Provider-owned resources and detached descendants require their own termination evidence.

The source profiles admit different task execution kinds in Node and worker hosts. A web window with a remote Node host is different from browser-only execution. Expose capability and the useful reason a requested operation is unavailable at its actual host boundary. Remote connection, terminal reconnect, general task resolution, shell grammar, debugging, and browser execution remain pending; local desktop task traces do not qualify them.

## Compatibility and verification bands

1. Address narrow evidenced interfaces at their owners: provider capability invalidation, explicit-null inspection, and handle-binding identity. Keep source candidates, installed observations, normal caller reachability, and serialization compatibility separate.
2. Improve consumer contracts without rewriting engines: save/write evidence, frozen edit basis, mixed-edit effects, query scope, extension policy/runtime state, and task readiness/retirement. Existing Boolean/void interfaces remain compatible unless a separately reviewed API decision changes them.
3. Qualify normal joined paths on each selected host: raced save and undo/reopen; picker aliases through actual writes; delayed edit preview/application with concurrent changes; policy update/activation/restart; task stop with real provider-owned children; and draft recovery under quota/process loss. Verify backing, saved settings, and actual lifecycle observations independently.
4. Handle serialized changes only where needed. Browser aliases require a real legacy-reference strategy. New inspection fields need API compatibility and permissions. Ordinary save/history and configuration policies should remain unchanged where the evidence supports them.

All 25 VS Code feature families have dispositions in the map. SCM, debug/test, remote connections, profile synchronization, agent sessions/tools/continuity, general terminal/UI/accessibility, browser previews, and launcher maintenance lack complete direct coverage. No feature is qualified merely because another uses the same host primitive. The full nine-application objective and empack's production/current/portable design obligations remain open. No implementation or upstream issue is selected by this review.
