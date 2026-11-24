# Cross-application findings and design direction

The studies support simplifying boundaries between values, state, and evidence. They do not support replacing these programs with one package, document, or task model. Preserve each program's purpose and established policies; share host mechanisms only where their premises match.

This is a partial synthesis of the study through the evidence bands linked below; its initial synthesis used repository revision `f570f2ec68de818ee4c4e1fe700f0675e0d239e8`. The [inventory](inventory.json) remains the current coverage index, and [joined scenarios](scenarios.json) retain their larger obligations. Most operations remain pending, and no entire feature family is qualified. A proposed improvement below is not a production implementation decision.

## Evidence that supports this comparison

The owning reports link exact versions, raw observations, source selections, models, laws, adapters, counterexamples, and limitations. Reuse those records rather than treating their successful replays as another native execution.

| Application | Current evidence | Scope limit |
| --- | --- | --- |
| empack | [Core API and native ownership](empack/OWNERSHIP.md); [seed observation demand](empack/OBSERVATIONS.md); [source and projection decisions](empack/SOURCES.md); [portable-authoring design](empack/AUTHORING.md). | Actual core compilation at `0b4462e` and installed 0.8.8-beta CLI runs are separate evidence; their build correspondence is not proved. Portable authoring is proposed. |
| npm | [Peer bindings](js-peers/README.md), [removal/re-adoption](js-peers/REMOVAL.md), and [script policy](js-scripts/README.md), and [workspace execution](js-scripts/WORKSPACES.md), using 11.20.0. | Private offline local archives and node-modules workspaces/projects; selected hook profiles only, no registry publication or general resolver qualification. |
| pnpm | The same peer/removal, script-policy, and workspace-execution bands, using 12.21.0, with distinct context, hook, and missing-root behavior. | No store-reclamation, filtered deployment, complete peer resolution, or general script-policy qualification. |
| Yarn Berry | The same fixture families, using 4.19.0, plus immutable-install refusal and scoped dependency/root-hook controls. | Node-modules linker only; no PnP, patch publication, or general virtualization proof. |
| Cargo | [Workspace/unit selection, script freshness, and cleanup](cargo/README.md), plus [source packaging](cargo/PACKAGING.md), using 1.92.0. | Local packages/build script and five generated no-dependency packaging profiles; no cross-target execution or registry publication. |
| restic | [Explicit snapshot forget/prune/restore](restic/README.md) and [selection/group previews](restic/SELECTION.md), using 0.20.0. | Selected local snapshot/blob lifecycle plus six-snapshot filters and keep-last-one previews; general retention, concurrent owners, remote failures, and repair remain open. |
| MO2 | [Origin ordering](mo2/README.md) and [profile activation](mo2/PROFILES.md), from 2.5.2 source. | Unmodified bodies with fixture adapters; no supported Windows application, Qt delivery, VFS injection, or game execution. |
| Prism | [mrpack update planning](prism/README.md) and [launch-task lifecycle](prism/LAUNCH.md), from 11.1.1 source. | Update impacts are simulations after a source filter; launch uses supported real Qt with controlled steps. Neither is full GUI/game acceptance. |
| VS Code desktop / vscode.dev | [Serial file editing](vscode/README.md), [one untitled reload](vscode/WEB.md), [browser handle registration](vscode/HANDLES.md), [local configuration scopes](vscode/CONFIGURATION.md), and [extension trust predicates](vscode/TRUST.md), at 1.147.0. | Different native/UI/source-fragment scopes. The custom-provider save race remains unresolved; reload is not durable project or file-save evidence. Configuration trust/remote/UI are not qualified; documented null inspection disagrees with the correct getter. |

## Distinctions that must survive simplification

**Identity has a role.** The JavaScript peer fixtures use identical plugin content in different effective contexts. Cargo builds different units with the same lock. Prism's filter can match content at different destinations. Browser handle names can collide across entry kinds or provider lifetimes. Restic's historical parent and retaining tree have different roles despite using digest-shaped IDs. Using those values interchangeably would erase useful information.

**Declared, selected, and effective state differ.** All three JavaScript tools can remove a direct leaf declaration while a parent still loads that leaf. MO2 installed mods and profile activation are separate from the winning effective file. Empack's authoring, exact selection, release, installed baseline, local choices, and runtime ownership need their own state owners. Inspection should explain those relationships instead of treating an absent declaration or root lookup as proof that content is unused. npm also normalizes an absolute local archive reference to a relative spelling during identical re-adoption; serialized spelling and target identity are separate.

**An event clock is not a saved image.** Native VS Code undo returns to a clean save point while its document version increases. Empack's proposed edit epoch rejects stale work, while saved-image identity answers whether the current draft is saved. Returning to the same image does not authorize an old attempt's background result. The file/provider incarnation and admitted storage revision remain separate.

**Creating an artifact is not qualifying it.** Cargo retains a local archive after a deliberately failed build check and permits packaging with verification skipped. Its transformed distribution manifest and original author manifest have different roles. Consumers need the actual checked outcome and exact artifact identity before delivery; an expected pathname alone cannot supply either.

**Completion is scoped to an effect.** Restic forget removes a reference before prune reclaims data. Cargo clean removes its target artifacts while an external script effect remains. MO2 dirty notifications can contain duplicate indices with no net edit. Prism can accept an abort before its base task finishes. A restored browser tab, in-memory handle, finalizer call, and confirmed stored project are different outcomes. Reports should name the affected resource and confirmed or unknown result.

**Permission and execution have scope.** The JavaScript hook study distinguishes dependency review, root hooks, explicit script requests, and command status. The three tools differ legitimately; a disabled default can still allow a particular explicit or workspace action. A failed command can retain selected files and hook-written output. A shared report should preserve those facts rather than impose one universal script switch.

**Evidence demand follows the operation.** Empack can preserve an existing seed without claiming its bytes match the publisher, while the publisher's bundled seed source still requires verified bytes. Cargo's freshness decision covers declared invalidation inputs, not arbitrary script reads. Browser API presence supplies neither permission nor a successful write. These findings support explicit required observations, capability admission, retained inputs, and completion evidence, not a broad “skip verification” switch.

**Retention follows typed ownership relations.** Restic's `Parent` is not a retaining root. A prepared export or editable undo state may need to retain assets deliberately. A dependency can remain reachable without a direct declaration. Neither following every relation nor ignoring every historical relation is a safe universal collection rule. Complete retaining roots and publication/reclamation coordination remain host premises.

## Application-specific decisions

### npm

Preserve Arborist's distinction between edge validity, placement, and the provider a module actually resolves. The observed shared plugin uses API 1 for both consumers even though the right workspace directly supplies API 2. That valid binding should not be relabeled a failed installation merely because another package manager creates distinct contexts.

A candidate inspection result should connect the direct declaration, requiring instance, actual provider, and retained reason. Removal could explain that a declaration disappeared while a parent still needs the package. Keep npm's observed missing-root no-op policy and successful identical re-adoption. Reuse `ls`/`explain` and existing reification data before inventing another graph or command.

Prefer additive reports that preserve established status and manifest/lock meaning. The keep-current alternative is extra graph inspection by callers. Falsify the candidate with hoisting, optional/peer edges, aliases, workspaces, partial reification, and incomplete evidence; do not infer cache deletion from root lookup. [Detailed basis and checks](js-peers/REMOVAL.md).

### pnpm

Preserve peer-context identity and the distinction between root visibility and retained reachability. In the fixture, the leaf stops being root-resolvable after direct removal while its parent still loads it. A root-level module lookup is therefore insufficient for either retention or absence claims.

A useful diagnostic can distinguish “not directly declared” from “not present” and identify requiring roots when the graph is known. Keep missing-root refusal and policy checks; do not force-remove transitives or reclaim store content to make the output look successful. The existing `PeerSet` distinction between declared and taken peers should survive any internal cleanup.

An additive result need not change lock/store formats. Keeping current commands plus explicit graph inspection is reasonable. Verify workspace filters, shared consumers, optional peers, incomplete metadata, and store ownership before generalizing; none was established by this local node-modules fixture. [Peer context](js-peers/README.md), [declaration edits](js-peers/REMOVAL.md).

### Yarn Berry

Preserve descriptors, resolved packages, virtual peer contexts, and materialization as different values. Same archive contents do not remove the need for context-specific identity. Immutable installation refuses a changed lock basis; it does not roll back the author's edited manifest or prove no incidental cache effect.

Explore a context explanation that connects the requiring descriptor, effective peer provider, selected linker, and direct declaration. Keep workspace-scoped removal/refusal and identical re-adoption. Review existing peer explanations and project structures before adding API surface. Do not transfer node-modules observations to PnP.

Keep serialized locators and immutable-mode semantics stable. The keep-current alternative is the existing inspection workflow. Qualification must cover PnP, patches, workspace selectors, virtual-package round trips, and immutable failure/partial effects. [Detailed findings](js-peers/README.md), [removal comparison](js-peers/REMOVAL.md).

Workspace runs add selected membership, scripts present, dependency readiness, dispatch, and completion as separate facts. npm continues its workspace loop after B fails; pnpm no-bail permits independent C while blocking A that needs B; the tested Yarn serial topological loop stops. Root inclusion and missing-script policy differ. Preserve those policies and make completed, blocked, and undispatched outcomes visible through existing reporter mechanisms before inventing another scheduler. [Native scope and terminal-results candidate](js-scripts/WORKSPACES.md).

### Cargo

Preserve `PackageId`, resolved graph, activated features, compiler `Unit`, and freshness evidence separately. The native app changes compiled features while its lock stays identical. An undeclared external build-script input can change while Cargo still reuses the previous artifact. This is evidence about the declared watch set, not a demand that Cargo infer every arbitrary file read.

For internal consumers, carry the selected unit/request and declared input basis. For operators, a candidate cleanup receipt can name the target root and confirmed scope without promising to undo external script effects. Existing JSON and cleanup APIs need review before choosing a new flag or schema.

Keep existing metadata IDs and package/lock formats. The current approach plus accurate input-declaration guidance is a credible alternative. Verify resolver/profile/target differences, failed scripts, undeclared effects, and cross-compilation before broad artifact claims. A target build or check is not target execution. [Model, native flow, and limits](cargo/README.md).

Local source packaging adds another boundary: Cargo can leave an archive after failed verification, and unchecked creation does not establish compilability. A candidate failure report can identify the retained archive and its failed check while preserving the current exit status. Keep the existing flags and source/normalized-manifest distinction; inspect existing package output before adding an API. Registry acceptance remains separate and untested. [Packaging evidence and verification plan](cargo/PACKAGING.md).

### restic

Preserve reference removal, reachable data, physical packs, and restore as distinct operations. The local run removes snapshot A, leaves pack bytes unchanged, and later prunes A-only data while retaining snapshot B's shared/new data. B's historical parent relation does not retain A's content.

Candidate snapshot/tree/blob/pack ID wrappers can protect high-risk internal boundaries without changing digest bytes on disk. This is a typing opportunity, not a reproduced namespace bug. An optional explicit-ID deletion receipt could distinguish preview, confirmed reference removal, unknown backend acceptance, and requested pruning; the tested explicit-ID JSON commands were silent.

Do not rewrite backup repositories for an internal wrapper. Keep file-type-scoped APIs and post-command inspection if new reports add more complexity than value. Validate remote/partial outcomes, retention grouping, incomplete roots, lock conflicts, and restore after collection; the selected three-blob projection cannot supply those proofs. [Detailed proposal](restic/README.md).

Scope is also part of selection. In the private fixture, empty grouping still leaves `snapshots --latest 1` selecting per host/path, while `forget --keep-last 1` with empty grouping previews one global survivor. `snapshots latest` selects one newest snapshot. Preserve those command-specific contracts and the protective default retention groups; explain effective scope before adding flags or changing defaults. Keep-tag is a union condition, and a preview remains distinct from deletion. [Source/native comparison and compatibility plan](restic/SELECTION.md).

### Mod Organizer 2

Preserve profile-local activation, installed metadata, eligible origins, backing-kind rank, plugin rules, and the effective view. The source ordering compares loose/archive kinds and their own rank, rather than only mod priority. The activation source also shows why dirty notification history cannot supply a unique net-change count.

A candidate inspection result should identify the profile/catalog/environment basis, winning origin and alternatives, comparison rule, skipped requests, and net effects. Keep existing ordered callbacks for listeners. Reuse refresh/ready mechanisms and existing conflict views before adding another scheduler or interface. A profile update is not proof of saved profile files or completed VFS state.

Leave saved profile markers and priority interpretation intact. The keep-current option is credible if existing views and refresh guards already supply the needed facts. Supported Windows tests must join activation/reorder, write/reopen, profile switching during work, actual injected reads, and output ownership. Mac source fragments do not close that requirement. [Ordering](mo2/README.md), [activation/completion](mo2/PROFILES.md).

### Prism Launcher

Preserve destination identity alongside content identity. The pinned mrpack filter drops equal-hash pairs without requiring equal paths; its empty-list reparse guard repairs some cases but not the moved/swapped-content cases with other pending work. The focused candidate is path-plus-hash reuse, with explicit verified copy/move if cross-path reuse is later wanted. It changes selection, not mrpack's format, and remains unimplemented. Verify the complete installed inventory and current upstream state before proposing a production patch.

Separately preserve task outcome, launch phase, waiting reason, stop request, and concrete process ownership. A queued abort is accepted before task completion in the Qt fixture. An additive inspection result can expose pending admission and actual terminal result without turning failure into clean cancellation or weakening force-stop confirmation.

The keep-current launch option uses existing base-task completion and signals consistently; internal consolidation requires a consumer/lifetime audit. The update keep-current option retains the demonstrated source planning counterexamples. Both need actual GUI/game/update qualification, modified/missing file cases, and callback/process failure tests. External mrpack overrides do not acquire empack seed semantics. [Update findings](prism/README.md), [task findings](prism/LAUNCH.md).

### VS Code desktop and vscode.dev

Preserve resource/incarnation, event version, undo/save point, current buffer, backing observations, and provider capabilities. Native serial undo/source behavior is consistent with these distinctions. The earlier custom-provider false-save/clean-marker mismatch remains provider-scoped and unresolved; passing ordinary-file controls neither proves nor dismisses it. The browser untitled reload supplies no file-save or durable project receipt.

Two candidates address different boundaries. An additive save result could expose captured basis, actual write outcome, current unsaved work, and uncertainty already known internally. A browser registry could use immutable entry keys shared across handle kinds, descriptive names, transactional allocation, and separate in-memory/persisted outcomes. Source-fragment alias collisions and aborted registration motivate the latter; normal picker/save consequences remain unqualified.

Keep the Boolean save API and normal UI for existing callers where sufficient. Registry changes must preserve known old bindings, refuse ambiguous rebindings, and request re-selection where identity is unknown; a basename cannot migrate a saved resource. Verify delayed/failed saves, undo, real pickers, permissions, concurrent tabs, quota/restart, and exact write targets. [Desktop](vscode/README.md), [browser recovery](vscode/WEB.md), [handles](vscode/HANDLES.md).

Configuration adds a separate provenance boundary: a saved lower-scope edit can remain masked, language defaults can beat ordinary folder values, and a documented inspection field can omit a present null that the getter correctly returns. Preserve source assignments, effective scope, write target, and presence separately. A focused inspection-carrier correction is a candidate, with existing aggregate/application semantics to review; do not change the demonstrated getter or infer missing source from lossy metadata. [Configuration evidence and candidate](vscode/CONFIGURATION.md).

Trust predicates reinforce that support metadata is not full admission. Explicit user/product policy, version eligibility, extension location, and other enablement gates remain distinct. The selected source predicates are internally consistent; a provenance/disable-reason explanation is a candidate. No installed trust revocation, running-code retirement, or sandbox guarantee was exercised. [Trust scope and verification plan](vscode/TRUST.md).

### empack

Preserve the current authority boundaries. The native core/CLI comparison supports seed preservation, explicit managed adoption, retained overrides, and exact repair under its stated scope. Publication, world protection, root observations, grants, and runtime ownership remain separate obligations. The sparse seed refusal identifies a read-footprint limitation, not data loss or permission to weaken verification.

The [coherent target](empack/README.md) separates saveable raw drafts, immutable project images, interpretation, exact selection, retained assets, prepared work, verified output, delivery, installation, and native execution. Edit epochs reject stale attempts; saved-image identity supports undo; host-admitted saved revisions order receipts. Required observations depend on the selected operation and source/destination role. Portable export does not mint native initialization, recovery, or execution authority.

Keep current native proofs and strict author schemas while introducing a new versioned project format. The selected clean break needs unknown-version refusal and preservation of unsupported/recovery data, not a general migration framework. The keep-current native-library option is useful but does not satisfy incomplete browser authoring. Actual local-JAR/config import through save/reopen and equivalent consumer export remains required. [Authoring laws and implementation obligations](empack/AUTHORING.md), [ownership](empack/OWNERSHIP.md), [observation demand](empack/OBSERVATIONS.md).

The actual core projection band supports retaining the current layer/choice algorithm: flat views use side/shared-override/common precedence, while mrpack/native containers keep applicable layers and choices. Selection and representation completion are separate, and neither verifies actual bytes or grants publication. Virtual sources should feed that same interpretation after attributable capture. Keep bindings/raw documents, placements, template interpretation, and retained assets distinct; the local-JAR save/reopen/export flow remains an implementation obligation. [Source/API evidence and portable boundary](empack/SOURCES.md).

## Compatibility and implementation order

Start by mapping existing state owners, APIs, and reports to these distinctions. Preserve opaque IDs and established saved meaning. A clarification or additive result is preferable when it supplies the facts without a new subsystem. Public receipts still need versioning, unknown/partial outcomes, and exact basis; they must not become a second resolver, save model, or authorization path.

Stable comparator applications need their own compatibility decisions: existing callers and backup/lock/profile formats remain supported unless their owners choose otherwise. VS Code's serialized handle aliases need a specific reconciliation design. Empack's selected new project-format break has a different policy; it does not authorize deletion or silent adoption of old native state.

Before adoption, compare current and proposed behavior against the same retained inputs, then run discriminating native boundaries: fresh versus stale basis, identity collision, missing evidence, callback order, failed finalization, and independently observed scoped effects. Reuse pure replays for model comparisons. Do not count another replay as a fresh browser, Windows, consumer, or release test, and do not replace a missing native check with more model happy paths.

For empack, first preserve constructor authority and native baselines, then implement draft/image/retention boundaries, actual host publication, and the required joined consumer flow. Network/auth routes, quotas, permissions, restricted inputs, and native-only capabilities remain explicit work. No new publication service, companion application, generic scheduler, or production migration framework is selected by this comparison.

## Remaining work

This comparison covers the completed bounded bands, not every capability in the inventory. General script trust beyond the selected local-hook profiles, package publication, multi-owner storage, component/runtime selection, native recovery, game/tool output ownership, full provider saves, and many other feature models still need source/native evidence or explicit unavailable-platform obligations. Joined component evidence must not promote an entire scenario.

The next design work should fill missing domain models and cross-feature transitions, rather than repeatedly adding assertions to these same small fixtures. Review the whole target and its evidence with the host owner before selecting production implementation. Deferred dependency UX work and the 0.9 implementation remain separate decisions.
