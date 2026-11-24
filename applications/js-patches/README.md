# pnpm and Yarn: patch recipes and installed content

This is an intermediate source/native record. Lean/Bend models and formal replay are still pending. No inventory operation is promoted, and no production change is selected.

The selected tools are pnpm 12.21.0, Yarn Berry 4.19.0, and Node 26.13.1. [Tool pins](../sources/local-pins.json) identify the actual executables; [source selections](../sources/js-patches-selections.json) identify inspected pinned source and remaining omissions. The native profile is one generated local tarball, one direct dependency, one ordinary text hunk, the `node-modules` linker, private home/configuration/cache/store, disabled scripts, and offline or disabled network. No user package or registry is changed.

## Recorded lifecycles

| Record                                                                                              | Scope                                                                                                                                                                            |
| --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Installed help](../evidence/js-patches-help-20261124T173628320229Z/receipt.json)                   | Six help commands; not patch behavior.                                                                                                                                           |
| [First partial run](../evidence/js-patches-20261124T173819947477Z/capture-review.json)              | Sixteen commands; the collector incorrectly expected removal by a versioned key to match the recorded bare-name key. The actual refusal is retained.                             |
| [Main partial run](../evidence/js-patches-20261124T173857262805Z/capture-review.json)               | Thirty-six commands; stopped when Yarn correctly refused `unplug` with this linker. Includes commit/install, preparation variants, invalid hunks, restoration, and pnpm removal. |
| [Private-fixture continuation](../evidence/js-patches-followup-20261124T174112934092Z/receipt.json) | Ten commands; verified the retained before image, completed Yarn unpatch, and retried pnpm's invalid patch.                                                                      |
| [Fresh pnpm reduction](../evidence/js-patches-control-20261124T174304431021Z/receipt.json)          | Fifteen commands; excludes secondary preparation, removal, and Yarn. Adds forced repair after valid restoration.                                                                 |

Original producers, streams, input edits, and failures remain retained. The continuation changes only its verified owned fixture; it does not relabel the original collector's exit. [Observation checks](verify_observations.py) verify content-addressed file snapshots, stream identities, source/tool pins, and fresh-process runtime reads. These are 77 package/runtime commands plus six help commands, not 83 independent feature tests or formal proofs.

## Meaning of preparation and commit

Both preparation commands extract editable content without changing the observed installed package. Their defaults differ: pnpm reapplies an existing patch unless `--ignore-existing` is supplied; Yarn starts from the unpatched locator unless `--update` is supplied. The native controls retain both prepared contents. The selected bare pnpm request records a bare-name patch key; guessing a versioned removal key correctly fails. This single version does not qualify multi-version selection or apply-to-all prompts.

pnpm's commit helper records `patchedDependencies`, updates snapshots, and its caller runs a re-resolving install. In this fixture, successful commit leaves the patched runtime installed and a subsequent frozen install succeeds.

Yarn's saved commit writes a patch file and persists a patch descriptor. For this direct workspace dependency, the actual manifest dependency is rewritten; the top-level `resolutions` description in command help is incomplete for this case. The source separately handles transitive resolution entries. Commit alone leaves the old lock and runtime unchanged. `install --immutable` then correctly refuses the required lock change; ordinary installation applies the patch. This is a legitimate save/install distinction, not a failed patch commit.

Removing pnpm's registered patch also runs installation and removes its unneeded patch file. Yarn's comparison restores the original dependency reference explicitly and then installs; its historical patch file remains. `unplug` is not an unpatch command, and this selected linker refuses it. PnP unpacking behavior remains untested.

## Bounded pnpm restoration defect

The main run and fresh reduction independently observe this sequence:

| Step                                                          | Status                                  | Fresh runtime observation                                            |
| ------------------------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------- |
| Install the valid patch                                       | Success                                 | `patched`, through the valid patch's installed backing.              |
| Change its deletion context so the hunk cannot apply; install | Failure                                 | `base`, through a different backing carrying the invalid patch hash. |
| Restore the exact original patch bytes; ordinary install      | Success, reporting “Already up to date” | Still `base`, through the invalid patch's backing.                   |
| Force installation in the fresh reduction                     | Success                                 | `patched`, through the valid patch's backing again.                  |

The good lock bytes and original patch bytes match exactly before and after restoration. The runtime reads use new Node processes and agree with the captured installed file bytes and resolved paths. The fresh reduction has a separate project/store and omits both secondary patch-preparation commands. Thus the successful restoration with an unchanged wrong live target is a bounded installed-product defect, not an inference from a stale in-process module cache or an effect of the secondary preparation steps.

A separate continuation starts with the unpatched lock, restores only authored recipe inputs with the invalid hunk, and attempts installation twice. Both attempts fail. Restoring the valid patch then succeeds with patched bytes. Do not generalize the finding to “invalid patches are silently accepted.” The problematic success is specifically restoration to a previously current valid lock while the live installation still points elsewhere.

The source dispatch includes an optimistic up-to-date modules-state path, but the complete state-preparation/materialization mechanism is not yet traced. The observations support the defect; they do not identify every responsible function or prove general cache corruption. Forced repair is an observed control in this fixture, not a universally qualified repair command for arbitrary projects or hooks.

Yarn's invalid mandatory hunk fails while retaining the previously observed patched runtime in this profile. Its fetcher source builds a copied archive and discards a failed patch's changes. This does not establish transactional rollback of every Yarn installation, optional-patch behavior, or unrelated file effects.

## Identity and proposed direction

Keep the selected base package, patch selector, authored patch file, derived locator, lock selection, admitted installation record, live link, and executable bytes separate. A hash-bearing directory name does not prove that the patch finished or that the current link matches the selected lock. Likewise, a saved patch descriptor is not proof of installation.

pnpm's source hashes normalized patch text; Yarn's source derives a short cache hash from parsed effects and applicable version ranges. These are different invalidation policies, not interchangeable content-authentication proofs. The source relations and native hash fields still need a bounded codec/model comparison; no general hash-collision or integrity claim is made here.

For pnpm, investigate retaining the previous live target until the candidate patch completes, invalidating installation evidence after partial failure, and checking the actual selected target before an up-to-date success. Reuse existing materialization and state checks; do not introduce a second package resolver. First trace `prepare_modules_state` and the relevant linking/publication path to choose the smallest correct change. A proposed guard must distinguish failed candidate work from an admitted backing and must preserve recoverable partial effects.

For Yarn, clarify direct versus transitive saved references and report that a saved patch still needs installation. Keep immutable installation's refusal meaningful. For both programs, show which patch selector and base selection a prepared directory belongs to, whether existing modifications were imported, and whether commit also changed the runtime.

For empack, the corresponding design obligation is to preserve source identity, transformations, asserted/observed content, publication, and installed ownership separately. This comparison does not add patch execution to empack or activate the deferred UX implementation.

## Remaining verification

Model observed transitions and the separately proposed repair/admission rule in Lean and Bend. Compare full prepared, recipe, lock, live-target, and runtime observations; include a counterexample to lock-equality-only success. Check selectors and patch-file persistence without confusing derived keys with display names. Keep failure and successful restoration separate.

Trace the pnpm up-to-date and materialization path before assigning the exact implementation cause. Preserve native/source correspondence limits: binaries and official source pins are retained, but neither comparator was rebuilt here. Qualify PnP/unplug, transitive and multiple versions, aliases, workspaces, nested or optional patches, dependency-manifest changes, unsupported/binary hunks, unavailable inputs, concurrent writers, interrupted finalization, and other platforms before broader adoption. No complete patch feature or joined workspace workflow is qualified yet.
