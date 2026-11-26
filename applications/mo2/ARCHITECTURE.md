# MO2: resolve operation context and preserve staged effects

Keep MO2's installed origins, profile-local activation, game-plugin policy, and virtualized file model. Correct backing replacement and callback ownership at their current owners. Make profile preparation, persistence, mapping installation, process waiting, and output adoption explicit before adding another coordination layer.

This target uses MO2 v2.5.2 at `9c130cbf2fc7225fb2916e46419af50671772aa0`. Existing source-method reports retain their adapter, Qt, and platform limits. The new [callback fragment](REFRESH-CALLBACKS.md) executes selected statements with Boost; it does not execute Windows MO2. Current upstream status, complete plugin contracts, supported dependencies, and reproducible application builds remain unreviewed. [Source selections](../sources/mo2-architecture-selections.json) and [target records](architecture-targets.json) preserve those distinctions.

## Values and state owners

| Value | Existing owner and meaning |
| --- | --- |
| Installed mod and backing | `ModInfo` and physical mod directories; an installed mod can be disabled in a profile. |
| Desired profile | `Profile::m_ModStatus`, order, local settings, and persisted profile files. Catalog indices refer to a particular admitted catalog. |
| Effective file view | `DirectoryEntry`, `FileEntry`, origins, archives, and game/plugin inputs. A computed winner is distinct from physically moving files. |
| Mapping request | `OrganizerCore::fileMapping`, selected content profile, current settings context, data paths, output target, and plugin rows. |
| Installed process view | `UsvfsConnector` mapping installation and actual injected-process observations; a mapping list alone does not establish it. |
| Process and output | `ProcessRunner`, lock/wait result, transferred handle, refresh, external writes, and later deliberate adoption. |

Mod priority, archive order, plugin load order, and callback group order are different policies. Preserve their existing comparisons instead of building one universal rank. The [origin study](README.md) already rejects priority-only winner selection; its finite ranking projection does not implement profile eligibility or Windows injection.

## Editing, refresh, and saving have different completion points

Preserve the [profile setters](PROFILES.md). Scalar normalization, ordered bulk requests, invalid-index handling, and intermediate notifications have distinct contracts. An enable-then-disable request can emit the same index twice while making no net edit. Keep listener order; derive human net-change counts from actual before/after state rather than notification length. Disabling a profile entry does not uninstall or authorize deleting its backing.

Use the existing directory refresher, callbacks, and ready signal. They already separate requested work from published structures. For an asynchronous consumer, retain which profile/catalog/environment basis a result belongs to; a callback or matching label alone cannot establish complete and stable inputs. UI/operation guards may already provide some of that ordering. Qualify them before introducing a new ticket or scheduler.

The [callback counterexample](REFRESH-CALLBACKS.md) identifies one narrower correction: the delivered batch must not disconnect future registrations accepted while it runs. A detached-batch alternative preserves those registrations in the controlled Boost fixture. It still needs exception, cancellation, thread, lifetime, and supported-application qualification. It does not prove profile persistence or view readiness.

Profile persistence needs an actual outcome. `writeModlistNow` invokes a delayed writer; `doWriteModlist` catches/report errors and returns void. Calling it is not a successful-file receipt. Preserve the current writer and safe-file helper, but inspect their actual commit/failure contract before constructing a launch-ready result. An optional internal save result or verified readback can carry confirmed, failed, or uncertain effects while legacy notification entry points remain available. No profile marker/order-format migration is selected.

## Mapping construction is not necessarily inspection

`beforeRun` saves current-profile data and asks for an immediate mod-list write before plugin veto and mapping installation. Its later false result therefore does not prove that nothing was saved or changed. A mapping/forced-library update can also fail after earlier preparation. Report the failed phase and prior effects rather than call the whole operation unapplied.

The temporary `Profile(QDir, ...)` constructed by `fileMapping` can create a missing mod list and calls game-specific profile initialization. Destruction flushes pending profile writing. Those source effects remain unexecuted by the earlier mapping fixture's profile adapter. A future read-only inspection surface should use admitted profile data or a deliberately separated loader; it should not silently call an initializing/persisting constructor. Reuse existing decoding and policy rather than write another profile parser.

If persistence is required for the requested launch, a save error should preserve its useful cause and make the choice explicit before spawning. A proposed UI can offer retry/cancel or a separately authorized use of the older saved state; an acknowledged error dialog is not automatically a verified save. Programmatic callers need the same distinction. This is a target contract, not current UI behavior or an executed Windows save-failure case.

## Resolve profile origins before choosing a stricter target policy

The [mapping study](ROUTING.md) uses requested-profile mods while local-save settings/path come from the current profile. `ProcessRunner::setFromFileOrExecutable` can also obtain executable customization from the current profile while forwarding a profile override. The plugin start entry point reaches that preparation path without automatically switching the UI profile.

A resolved launch context should identify the selected content profile, origins of executable/forced-library/output settings, local-save policy, catalog, game paths, and plugin contributions. Do not collapse these into one ambiguous profile name. The owner must choose whether an override means all profile-local behavior or deliberately combines a selected content profile with ambient executable policy. Using the requested profile everywhere and requiring current/requested equality are different compatibility choices; neither is adopted solely from the method fixture.

Preserve existing profile file names, catalog conventions, and plugin interfaces. If a captured index or backing changes, resolve it again through the existing catalog and present or refuse the changed operation; inventing persistent IDs or trusting an old index is unnecessary. Any readiness facts must originate from actual native observations and writer/backend results, not caller-supplied labels.

Target eligibility likewise needs the actual contract. The executable dialog filters special mods, but the method accepts an active nonregular custom name before deciding whether it contributes ordinary mappings. That API-shape case is not a supported UI write-loss finding. Validate ordinary writable backing or retain an explicit caller precondition, then qualify real plugin-provided targets separately.

Do not impose a global “exactly one create target” rule on the entire mapping list. Local-save and file-mapper plugins can contribute other flagged rows. Ordinary mod-data output, save output, and plugin mappings have different roles. Mapping assembly, backend installation, existing/new-file behavior, process execution, and stable output capture each require their own evidence.

## Preserve backing before sync reports a replacement

The [overwrite study](OUTPUTS.md) executes the sync dialog's remove-then-rename sequence with real Qt/macOS file operations. Failed source rename can leave the old destination absent. It also preserves partial batches and distinguishes don't-sync, missing origins, link objects, and untouched canaries. This is supplemental source-method evidence; shell moves and supported Windows/USVFS remain separate.

Correct this owner by preserving the prior destination until replacement is confirmed or by retaining verified recovery backing before destruction. Reuse an appropriate checked helper only after reviewing its semantics; its use elsewhere does not prove atomic replacement. A preview existence check cannot close later failure or replacement races. Do not weaken permissions or retry blindly after the destination disappeared.

The current void `apply` has no aggregate per-file outcome. A focused result should retain each selected origin/backing, completed move, failed remove/rename, skipped row, remaining source, and any recoverable prior bytes. Derive refresh and recovery guidance from those effects. Preserve still-useful source and successful rows; error does not mean rollback. Qualify path/object identity, cross-volume and permission failure, metadata, links, interruption, restart, and actual restoration on Windows before promising recovery.

Inspection, sync to chosen per-file origins, creation of a new mod, and shell-moving overwrite to one existing mod are separate operations. The source creates a new mod before its shell move and refreshes after the helper result; neither path is qualified by the sync dialog fixture. The inventory now separates the previous mixed inspection/apply record into inspection and `sync-existing-files`, and records `move-to-existing-mod` as pending source discovery. Both records share the original evidence where relevant; this is a scope correction, not another native run or doubled coverage.

## Keep plugin ingestion separate from completed actions

The [plugin study](PLUGINS.md) distinguishes raw enabled/order setters, index rebuilding, master-presence checks, write requests, and game-specific normalization. Preserve raw ingestion operations where their callers intentionally compose those stages. Master presence is not valid order or runtime compatibility, and lookup missing is not physical deletion evidence.

For an extension/UI action, a higher-level batch can validate its names/order against the current catalog and reuse existing fixups, writer, and refresh paths. The duplicate-name lookup counterexample remains an API-shape case with unresolved normal caller reachability. Decide whether to reject duplicates at that action boundary rather than change every raw setter. Partial-order fallback currently follows catalog order; changing it to old priority based only on a nearby comment would change captured behavior.

Expose completed stages and unresolved work without another plugin resolver. Keep existing listener order, game-specific files, load-order policy, and extension compatibility. A writer request or a generated-index adapter call cannot become a saved-game or valid-runtime receipt.

## Process results and staged compatibility

Preserve [process-policy distinctions](PROCESSES.md): running, completed, force-unlocked, cancelled, and error; a UI unlock request is not child retirement. Plugin `startApplication` transfers handle responsibility according to its existing contract, while waiting and refresh have their own entry points. Real Windows handles, descendants/jobs, VFS lifetime, and output stability still need qualification.

Apply changes in bands:

1. Correct destructive sync backing loss and callback-batch ownership at their existing owners, using bounded alternatives and actual host/caller qualification.
2. Resolve context and expose persistence/preparation results before producing a launch-ready claim. Keep current side effects visible after veto or failure.
3. Add an inspection/batch facade only where an existing caller needs it. Preserve raw setters, formats, listeners, and plugin contracts; do not create a second mapping, refresh, or process engine.
4. Exercise one joined supported-Windows workflow: two profiles, loose/archive conflicts, requested/current settings, injected tool reads/writes, confirmed process retirement, deliberate overwrite adoption, partial failure, save/reopen, and restoration. Observe actual physical bytes and keep original mods intact.

Keep-current is credible where existing guards and interfaces supply the needed guarantees. It is insufficient for the observed destructive sync path, and the callback fragment needs either delivered-batch cleanup or a justified/enforced caller restriction. Full supported-MO2 adoption, broader inventory features, and the nine-application goal remain incomplete. No production code, saved-state migration, or upstream report is selected here.
