# pnpm and Yarn: patch recipes and installed content

This study compares selected patch lifecycles and a separately proposed finalization policy. Its models match the retained native profile; full patch features and joined workflows remain unqualified. No production change is selected.

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

pnpm's source hashes normalized patch text; Yarn's source derives a short cache hash from parsed effects and applicable version ranges. These are different invalidation policies, not interchangeable content-authentication proofs. The replay decodes the selected native fields into opaque identity labels. It verifies pnpm's normalized hash against the captured patch text; Yarn's effects-based hash is not reimplemented. These are closed research readers, not general codecs or a hash-collision/integrity qualification.

For pnpm, investigate retaining the previous live target until the candidate patch completes, invalidating installation evidence after partial failure, and checking the actual selected target before an up-to-date success. Reuse existing materialization and state checks; do not introduce a second package resolver. First trace `prepare_modules_state` and the relevant linking/publication path to choose the smallest correct change. A proposed guard must distinguish failed candidate work from an admitted backing and must preserve recoverable partial effects.

For Yarn, clarify direct versus transitive saved references and report that a saved patch still needs installation. Keep immutable installation's refusal meaningful. For both programs, show which patch selector and base selection a prepared directory belongs to, whether existing modifications were imported, and whether commit also changed the runtime.

For empack, the corresponding design obligation is to preserve source identity, transformations, asserted/observed content, publication, and installed ownership separately. This comparison does not add patch execution to empack or activate the deferred UX implementation.

## Models and retained comparison

[Lean](Patches.lean) checks twenty laws; [Bend](Patches.bend) checks ten. The [comparison](comparison.json) matches both to 77 retained command outcomes and projected before/after images, including ten prepared-directory results and 33 separate fresh-process readbacks. Ten unsupported research inputs are refused. The [replay](conformance.py) recompiles its exact Lean dependency before use and runs no package manager or native collector.

The projected image preserves authored recipe, lock selection, live target, payload, and patch-file presence. It does not compare arbitrary package trees, cached state, scripts, or every incidental file effect. pnpm's live target is classified from the observed derived path; Yarn's flat path intentionally stays the same across different payloads. Patch selector admission and command options come from requests; measured statuses and outputs are used only for comparison.

The current pnpm model is a projection of the observed profile, not a reconstruction of every source admission condition. Source inspection identifies both the CLI shortcut and the install path's separate frozen-tree gate. The direct-link probe distinguishes present from dangling/missing entries; that classification alone does not establish the selected target. Other source gates inspect additional state. Which complete path supplies each native success is unresolved; the model must not imply that production literally checks only lock equality.

A separate conservative model leaves the old live scope intact after candidate failure and rematerializes without an admitted reuse proof. Seven individual projections differ from current observations. They are alternatives evaluated against each captured input, not replacement native results or a complete alternate native history. A two-step law separately checks failed private preparation followed by valid restoration. Efficient reuse needs an explicit valid backing/admission basis; a link with the expected identity can still have wrong bytes, and the model retains that counterexample. Native staging, ownership, finalization, and reusable receipts remain implementation obligations.

## Remaining verification

Extend the closed-profile models only with separately attributed source/native profiles. Keep raw patch selectors and complete derived locators separate from the equality labels used here. Qualify dependency metadata and efficient reuse without treating a directory's name, presence, or successful command status as content proof.

Trace the pnpm up-to-date and materialization path before assigning the exact implementation cause. Preserve native/source correspondence limits: binaries and official source pins are retained, but neither comparator was rebuilt here. Qualify PnP/unplug, transitive and multiple versions, aliases, workspaces, nested or optional patches, dependency-manifest changes, unsupported/binary hunks, unavailable inputs, concurrent writers, interrupted finalization, and other platforms before broader adoption. No complete patch feature or joined workspace workflow is qualified yet.
