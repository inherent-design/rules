# Prism: keep instance, preparation, and publication results distinct

Preserve Prism's instance library, component metadata, task graph, settings overrides, and process ownership. The useful changes belong at the existing mutation and completion boundaries: retain retry references, propagate save results, preserve backing before replacement, and report the actual phase and effects. A second launcher engine or universal transaction layer would obscure these owners.

This proposal uses Prism 11.1.1 source `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. The [source ledger](../sources/prism-architecture-selections.json) separates newly inspected callers from earlier selections. The [contract map](architecture-targets.json) links each target to existing models, reports, compatibility choices, and remaining verification. This pass adds source/interface analysis, not a new launcher run, model, or production patch. Current upstream fixes, shipped-binary correspondence, and complete supported-platform behavior remain unreviewed.

## State owners and identities

| State | Existing owner | Distinction to preserve |
| --- | --- | --- |
| Instance library | `InstanceList`, `BaseInstance`, group file, watcher | Directory key, UUID selector, display label, discovered membership, and saved grouping differ. |
| Component intent | `PackProfile`, `Component`, `mmc-pack.json`, custom patches | Requested version, cached metadata/version, explicit/dependency-only selection, and effective launch contribution differ. |
| Effective settings | Registered `Setting` and `OverrideSetting` objects | Local absence, explicit empty value, override gate, effective value, and origin differ. |
| Runtime observation | Java selection/check/verification steps | Configured executable, saved probe, current probe, compatibility permission, and successful invocation differ. |
| Account and session | Selected `MinecraftAccount`, `AuthSession`, use lock | Actor identity, name, profile readiness, captured session, and provider authentication differ. |
| Work and processes | `Task`, `LaunchTask`, concrete steps, `LoggedProcess` | Request admission, active work, waiting interaction, final outcome, resource retirement, and logs differ. |
| Files and artifacts | Resource installation, instance staging, archive writer | Source backing, destination, partial effects, final output, and refreshed UI differ. |

These are domain roles, not proposed persistent IDs. Keep existing instance and pack formats unless a specific interface change requires otherwise. Do not apply empack's selected clean-break policy to Prism's installed user data.

## Instance lookup, metadata, and undo

The [library study](LIBRARY.md) establishes that directory IDs, UUID lookup, and labels are not interchangeable. The current first-match lookup accepts directory IDs or UUIDs; the grouping insertion can use the supplied UUID even though effective lookup and serialization use directory keys. The executed canonical-key candidate fixes that selected method case. Preserve the directory-keyed group format, and offer typed directory/UUID selection at new callers where ambiguity matters. Changing the legacy string helper's first-match behavior needs caller review.

Grouping, filesystem removal, discovery, and persistence have separate outcomes. A trash failure can follow a saved group removal. Undo can restore the main directory but fail on shortcuts, or fail the main rename after already popping its history. Preserve the retry reference and remaining obligations until each is resolved or explicitly abandoned. A retry must revalidate the current source and destination; history does not exclusively retain OS trash or authorize overwrite.

Reuse existing history, watcher, and save paths. An additive result can distinguish no work, completed restoration, partial restoration, and refusal, naming the actual restored destination and outstanding shortcuts or metadata. Preserve the old Boolean adapter where compatibility requires it. Keeping in-process references does not promise restart recovery or require a new persistent trash database.

## Component edits, loaded metadata, and saved images

Keep exact version spelling separate from suggestion rank. The [component study](COMPONENTS.md) retains order-sensitive suggestion ties, protected explicit/custom selections, dependency-only removal policy, disabled roots participating in requirement collection, and later disabled launch contributions. These are Prism policies; a generic dependency resolver or semantic-version normalizer is not a substitute.

The source distinguishes requested `m_version`, cached `m_cachedVersion`, loaded metadata, and serialized fields. `setVersion` can invalidate loaded metadata, while custom-file behavior differs. A getter or successful resolver callback does not independently establish that the requested image is loaded and saved. Expose those stages to consumers that need them instead of adding another mutable copy of component truth.

This pass inspects an additional save/reload boundary. `savePackProfile` checks `QSaveFile` open, write length, and commit. `save_internal` clears dirty only on success. Preserve those checks and the existing load-before-swap behavior. However, `saveNow` returns void, and `reload` calls it before invalidating the launch profile and calling `load`, without checking whether the flush succeeded. If saving fails while the earlier file remains readable, this source sequence can replace edited in-memory components with the earlier saved image. The dirty bit remaining true is not proof that the edited objects remain available. This is a source-derived counterexample condition, not a reproduced native save failure or a claim about every caller.

A focused result from the existing save owner should let reload stop and preserve the edited list on failure, or proceed only through an explicit discard/reload choice. Retain the useful IO cause and distinguish unchanged saved data from unsaved current edits. Do not fix this merely by clearing dirty earlier or by treating a request to save as confirmation. Destruction also calls `saveNow`; shutdown policy and recoverable failure need separate caller qualification.

The selected resolver also needs progress-aware error handling. Its removal loop ignores a false `remove` result and can revisit the same candidates. The earlier fixture observes that nonprogress prefix under permission failure. Stop with the failed component and completed removals, rather than retry indefinitely. `checkOnly` currently permits removal before its addition/change gate; decide whether to preserve that effectful launch preparation contract or introduce an actually read-only inspection entry point. Silently moving the gate changes behavior.

## Settings, Java, and command interfaces

Reuse the existing global/local override model. An enabled group override does not necessarily clear an omitted local field; an explicit empty string and absence differ. Show the effective value and origin where needed. The [Java study](JAVA.md) also retains saved observation fields after invalid probe output, with a later permissive compatibility decision in some cases. Label saved evidence accurately before considering a stricter launch policy or a new cache representation.

The keep-current option can preserve permissive probe policy with clearer evidence reporting. A structural alternative would associate a complete probe observation with its executable/signature and settings origin. That affects global and instance readers, automatic Java selection, persistence, and migration; no such change is selected here. Actual discovery, architecture consistency, downloaded Java, and invocation remain required tests.

For commands, preserve each consumer grammar. The [hook/wrapper study](COMMANDS.md) executes two different splitters, and the [producer/consumer follow-up](COMMAND-PATHS.md) identifies a Windows-style Java token losing separators in the wrapper parser on macOS. Internally structured program/argv values can avoid unnecessary parsing, but legacy configured strings need their own correct encoding and compatibility path. Do not silently normalize both grammars or interpret every hook as shell text.

Guard token-empty results after expansion before taking the program. Reuse `LoggedProcess` start state and error text so a missing executable does not produce a misleading exit-code-zero headline. Pre-command, game, and post-command are separate phases. The current sequence stops after a failed game step; post-command is not a guaranteed finally hook. A new always-run cleanup policy would require an explicit interface and migration of user expectations.

## Account capture and launch lifetime

The [account study](ACCOUNTS.md) demonstrates that claiming by session display name can hold another account actor in a controlled duplicate-name collection. Pass and retain the already selected actor through the existing use-lock mechanism. Keep account identity and session snapshot together without copying credentials into new reporting structures. Qualify object lifetime, removal, refresh notifications, and concurrent launches before adoption.

The profile-setup prefix also captures the session before setup completion. A dialog's accepted result alone does not establish updated account/profile data. The source-derived target is to admit actual profile state and then capture a usable session, not simply refill the same unchanged account. Live OAuth, entitlement, provider responses, and GUI admission remain unqualified; no personal account is needed for this source decision.

Keep `Task` outcome authoritative for its own completion, and expose `LaunchTask` phase as a distinct interaction fact. The [launch model](LAUNCH.md) observes stale controller phases and synchronous or delayed abort completion. Request acceptance, force-stop intent, base failure/aborted outcome, finalizer calls, and actual child retirement remain separate. Existing queries and an additive inspection facade may suffice; prove consumers need internal consolidation before rewriting the scheduler.

Newly inspected `PackProfile::reload` can request abort and reset an update-task pointer when changing network mode; `ComponentUpdateTask::abort` aggregates child requests. That source prefix does not prove child retirement, callback disconnection, or a complete race. Preserve task-specific ownership and qualify the old/new task handoff before treating reset as cancellation completion.

## File installation and pack updates

Use each operation's existing owner. The [content-install study](CONTENT-INSTALL.md) reproduces source/destination alias loss and distinguishes drop handling, per-file copy results, and refresh. The staged-copy and canonical guard alternatives have bounded native evidence, not all-host replacement guarantees. Preserve prior backing until a candidate is admitted, or refuse a known alias before destruction with useful guidance. Equal bytes at separate files are not equal backing identity.

Do not redefine Qt's handled-drop Boolean to mean every copy succeeded. Carry per-file effects and later refresh alongside it. This also prevents a successful copy followed by an unconfirmed refresh from appearing to be a wholly unapplied operation.

For mrpack updates, keep indexed placement, content identity, optional/environment selection, overrides, and current local bytes distinct. The [hash-filter counterexample](README.md) requires path as well as hash for unchanged placement; cross-path reuse needs an explicit verified move/copy. The [cleanup study](CLEANUP.md) requires safe destination admission before save protection or deletion and destination-preserving override records. Lexical normalization alone does not qualify symlinked ancestors or hostile archive extraction. Historical malformed records need a safe reconstruction/review path; never guess destructive targets.

The outer staging path adds another owner. `InstanceStaging` retries `commitStagedInstance`; overriding commits call `FS::overrideFolder`, whose selected implementation recursively copies with overwrite. It is not an atomic whole-instance replacement. Success then triggers discovery/selection and a void group save. Child failure/abort paths attempt staging deletion without retaining its Boolean result; exhausted commit retries follow a different path. These are newly inspected source branches, not executed overlay failures, crash recovery, or a complete reachability analysis.

Retain staged input, completed copies/deletions, remaining files, metadata-save result, and retry eligibility separately. Existing retry machinery can remain, but revalidate any partial prior attempt before promising that retry is harmless. Preserve user worlds/configuration according to an explicit pack policy. A complete staging folder or current publisher index does not itself define seed ownership, rollback, or user-file conflict handling.

## Export selection and publication

Preserve instance ZIP, distributable mrpack, remembered export preferences, and installed instance as distinct products. The [export study](../prism-export/README.md) executes actual archive payloads: hidden leaves differ from hidden-directory contents, following a link can read outside the instance, and failed/canceled writing can replace a previous output. The full GUI selection and outer Task remain unqualified.

Preview the actual selected inventory and source/link roles using the same admitted selection facts as the exporter. Remembering preferences on Cancel can remain intentional; it is not an archive receipt. Including currently omitted hidden files or changing link handling changes content/privacy semantics and needs an explicit policy decision.

A candidate artifact should replace the prior output only after successful finalization and the selected overwrite authorization. Reuse the archive writer and Task; do not change an empty optional error into a complete-success assertion without cancellation and close results. The outer source cleanup deletes failed/canceled output, so retaining the previous archive requires publication changes as well as better text. Replacement, durability, interruption, and recovery remain host obligations. No staged export implementation was executed in this pass.

## Compatibility and verification bands

1. Correct narrowly evidenced ownership boundaries: canonical group insertion, undo obligations, alias-safe resource replacement, removal-loop progress, empty parsed commands, actor retention, and path-aware update selection. Preserve existing formats and old wrapper interfaces where possible. Each candidate still needs actual caller and supported-host tests.
2. Propagate save, preparation, per-file, refresh, and final task results through existing owners. Qualify failed-save/reload before changing dirty-state handling. Keep errors, partial effects, and uncertain outcomes available to GUI and integrations.
3. Resolve explicit owner choices: effectful check-only preparation, profile setup readiness, permissive Java evidence, post-after-failure behavior, hidden/link export policy, and override/user-state preservation. Avoid silently combining them into a correctness patch.
4. Exercise joined isolated workflows through normal entry points: component edit/save/reload with failure; pack A-to-B update with moved paths and user changes; local content drop then launch; selected account through claim/finalization; export with existing output and cancellation; trash/partial undo/retry and discovery/save. Inspect actual installed/archive bytes and retained retry references, not only task headlines.

The [contract map](architecture-targets.json) gives a disposition to all 17 Prism families. Worlds, provider browsing, launcher self-update/cache cleanup, general diagnostics/redaction, themes/accessibility, and several CLI/integration paths still lack sufficient direct evidence. Their pending status remains visible. Prior finite laws and source-method captures do not qualify those features or the full nine-application goal. Production changes and upstream reports require a separate implementation decision.
