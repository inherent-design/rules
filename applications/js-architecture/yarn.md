# Yarn Berry: bind results to the phase that established them

Preserve descriptors, locators and virtual peer contexts, ordered resolution rules, separate resolve/fetch/link phases, and deferred version policy. The main design requirement is to connect each result to its actual authority: evaluation, saved manifest, installed backing, or consumed decision. A single successful command status cannot supply all four.

This review uses Yarn 4.19.0's pinned source and existing native reports. Recent graph fixtures use the node-modules linker; PnP and arbitrary plugins retain separate obligations. Names below describe proposed result responsibilities, not new existing APIs or wire keys.

## Deferred version application

The [version study](../yarn-version/README.md) reproduces a selected deferred patch decision being consumed before a controlled installation failure, while the manifest remains unchanged. The retry then has no remaining decision. Current source mutates/reports in-memory targets, clears or updates version files, and only afterward calls `installWithNewReport`.

Keep relative release records as policy until apply. They legitimately resolve against current workspace versions, and multiple suggestions choose the greatest target. At apply, capture the exact resolved targets, dependent range edits, and relevant before-images. A downgrade still needs apply-time force; an earlier recording does not grant durable permission.

Tie decision consumption to verified publication of the corresponding manifest effects. Waiting until the *entire install command* succeeds is not sufficient: `Project.install` persists project data before linking, install-state persistence, post-install validation, and `afterAllInstalled`. A later failure can therefore coexist with saved versions. Leaving a relative decision pending after those effects could make a blind retry compute another bump. This is a source-supported design counterexample to that proposed ordering, not a newly executed late-failure trace.

The correction needs a phase-specific result: exact planned manifest targets, confirmed/failed/unknown writes, the exact decisions consumed, and later install/hook outcomes. `Project.persist` writes the lock and workspace manifests concurrently; its aggregate failure does not identify an atomic project outcome. Per-file readback and a retained partial/uncertain result are necessary before consumption or retry is described as complete. A first `Promise.all` rejection also does not retire its sibling writes. Wait for their owned outcomes, or retain explicit uncertainty, before treating a readback as the final affected image. This is an adapter obligation, not a newly reproduced native write race.

The existing [version model](../yarn-version/Versions.lean) already separates exact target confirmation, conflict, unknown outcome, and a retry that retains the resolved target. Its confirmation premise must cover the complete affected manifest/range set under the correct basis; an announcement or global exit code cannot supply it. This review refines that adapter obligation and leaves the model unchanged.

First fix the observed pre-persistence loss at this existing owner. Strong crash/restart guarantees need a separately qualified way to retain the exact target/basis and reconcile ambiguous writes; an in-memory receipt or moving one `unlink` cannot supply them. Do not silently rerun relative decisions, restore all records after any nonzero exit, or invent a general transaction service. Existing Git/version files and default CLI semantics remain intact until a concrete format or recovery change is reviewed.

## Constraint fixes

The [constraints study](../yarn-constraints/README.md) separates applied safe edits from a verified postcondition. `constraints --fix` runs at most ten passes, persists changed manifests, and can exit successfully after its last edits without evaluating the resulting state again. A following explicit check can still fail.

Expose the evaluation basis and persisted-edit basis separately. If no evaluation ran after the last edit, report that postcondition as unverified, not satisfied or definitely false. Default behavior should not silently add another user callback evaluation: constraints are executable user code and may be stateful. Preserve the bounded loop and partial safe edits. Existing callers can explicitly request the separate check; a stricter future mode or structured result needs its own compatibility decision.

The existing [strict candidate](../yarn-constraints/Constraints.lean) checks the final image symbolically. It is an alternative contract, not evidence that another real callback evaluation is harmless or that a native fix already implements it. Preserve that separation when choosing an opt-in verification mode.

Do not replace all value comparison with a generic deep-equality helper. Proposal conflict maps use JavaScript value identity; applying a single proposal compares serialized values. Those are distinct source decisions. Resolution-rule order can itself affect semantics, so sorting object keys or ignoring order globally would be unsafe. Any change to equal-object conflict handling needs field-specific meaning and source provenance, not just a more convenient serializer.

## Configuration targets and effective values

The [configuration study](../js-config/README.md) observes a successful home write whose headline displays the environment-masked effective value as the value set. Report the destination and saved assignment separately from effective evaluation. Reuse existing interpretation/provenance and secret redaction. Printing raw requested values as a quick correction could expose a secret that the current effective getter redacts; a destination-only acknowledgement is safer when a redacted stored view is unavailable.

Its custom-basename control also finds that the home writer follows the configured rc basename while home loading uses the canonical basename. Prefer preserving existing home-reading behavior and routing the writer to the same explicit path, unless a separately reviewed contract deliberately expands home-basename semantics. Factor the path owner so reader and writer agree. Do not merge or delete existing conflicting home files, and do not build a second evaluator to infer the winner from equal strings. Supporting custom home basenames instead changes read precedence and may alter active authentication configuration; qualify that compatibility choice explicitly.

## Resolution and installation

Preserve ordered first-match `Manifest.resolutions` behavior and the [manual lock-table choice's lifetime](../js-overrides/README.md). Saving that choice, installing it, and performing stricter resolution checks are separate operations. A later strict check may correctly refuse a command's accepted selection. A universal specificity sort or mandatory check would change policy and is not selected.

Keep immutable-lock policy separate from immutable-cache and from physical installation. Update-lockfile mode can persist selection while explicitly skipping linking. A new result can identify descriptor/locator, source policy and lifetime, persisted graph, selected linker, and link/build outcome using existing phase owners. Preserve current public result/JSON contracts unless an opt-in versioned surface is introduced. No new scheduler or resolver is needed for that reporting.

[Workspace execution](../js-scripts/WORKSPACES.md) retains Yarn's selected-root, dependency-closure, missing-script, and continuation policies. A structured result can report selected workspaces and observed starts or terminal outcomes, but a missing start alone does not identify a blocked reason. Do not infer parallel scheduling, child retirement, or rollback from the retained sequential fixture. Preserve explicit script execution as a different policy surface from installation build permissions.

## Compatibility and verification

Keep manifests/locks, relative deferred records, direct versus transitive patch behavior, resolution order, user plugin/callback policy, and current command distinctions. Clarify recursive version help to match observed dependency traversal rather than silently change write scope. Source-backed defects need corrections; unrelated intentional differences should remain.

Before adoption, test pre-persist failure, one failed manifest among successful writes, failure after persistence, exact and relative decisions on retry, downgrade permission, dependent range edits, and process loss. Constraint checks need last-pass edits, callback errors/statefulness, conflicts, partial persistence, and explicit verification. Configuration needs masked/secret values, canonical/custom/both home files, nested settings and write failure. Linker, plugin, workspace and platform matrices remain explicit; existing node-modules fixtures do not qualify PnP. No production implementation or fresh native conformance is claimed by this synthesis.
