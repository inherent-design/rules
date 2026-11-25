# Prism: indexed content identity during mrpack updates

This band studies Prism Launcher 11.1.1 at `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. It covers a selected mrpack update filter and its empty-list staging guard. A full GUI import/update and the rest of Prism's instance, component, Java, account, task, and launch behavior remain pending.

A separate [launch lifecycle band](LAUNCH.md) studies sequencing and abort delivery with supported Qt 6 and controlled steps. It separates controller phase from base outcome and leaves actual game-process and GUI acceptance open.

A [cleanup and override-record band](CLEANUP.md) compares selected deletion and record helpers with disposable files and scoped models. It retains raw-path protection, recorded-destination, and partial-cleanup counterexamples; full-importer qualification remains pending.

The [component-decision band](COMPONENTS.md) compares protected selections, exact and suggested versions, activation flags, obsolete-dependency candidates, cached-state round trips, and removal failure through source functions and supported Qt. Its models match the selected retained comparisons; actual component loading, publication, and game launch remain separate obligations.

The [Java/settings band](JAVA.md) separates inherited and explicit settings, write-through probe fields, cache admission, invalid probe output, and compatibility decisions. Its Qt source-method fixtures leave real Java discovery, complete settings UI/persistence, and game launch pending.

The [account/session band](ACCOUNTS.md) retains selected account, session, refresh, claim, and profile-creation evidence. Live authentication and full GUI/launch behavior remain separate obligations.

## Current rule and counterexample

[`ModrinthCreationTask::updateInstance`](https://github.com/PrismLauncher/PrismLauncher/blob/7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4/launcher/modplatform/modrinth/ModrinthInstanceCreationTask.cpp) parses incoming and saved mrpack indexes. It removes a new/old pair from its download/deletion candidates when their SHA-512 values match. That comparison does not require equal paths. The remaining old entries are scheduled for deletion, while the remaining new entries are downloaded during staging.

`createInstance()` reparses the incoming manifest if the remaining new list is empty. That guard changes the result and must be retained when analyzing the filter.

The [retained probe](../evidence/launcher-fragments-20261124T012218677503Z/receipt.json) executes the unmodified filter body using real Qt 6.12 `QString` and `QByteArray` values and `std::vector`. The staging guard is projected separately under successful, required-only manifest parsing. No real instance, download, account, or GUI is involved.

| Fixture                                                        | Filter/staging result                                                         | Consequence under the explicit overlay simulation |
| -------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------- |
| Unchanged path plus another changed file                       | Reuses the unchanged pair and downloads the changed file.                     | Target inventory matches.                         |
| Same bytes moved to a new path, plus another changed file      | Drops the moved entry from downloads and drops its old entry from deletions.  | New path is missing; old path remains.            |
| Only one moved file                                            | Empty list triggers manifest reparse and download staging.                    | New path exists; old path remains.                |
| Two indexed paths exchange contents, plus another changed file | Hash matches remove both exchanged entries from download/deletion candidates. | Both existing paths keep the wrong content.       |

The fixture also covers unchanged indexes and a Unicode path move. [Simulated impacts](../evidence/launcher-fragments-20261124T012218677503Z/simulated-impact.json) keep predicted filesystem consequences separate from the executed filter output. The inspected caller deletes scheduled paths after staging succeeds; complete instance publication and any later reconciliation have not been executed or fully qualified here.

This establishes a source-level planning inconsistency for moved or reassigned indexed content. It is not presented as a reproduced full-launcher failure. A supported native update must verify the final installed inventory before this becomes an end-to-end defect claim.

## Domain and proposed rule

An indexed entry combines a destination path, content identity, environment selection, and acquisition information. Equal content does not establish equal placement. The saved index also describes publisher intent; it is not proof that current local bytes are still available.

The focused proposed rule is to require both path and hash equality before removing a pair as an unchanged placement. Reuse across different paths would need an explicit verified copy/move operation. The proposal deliberately leaves treatment of modified or missing local files as a separate policy decision; it does not silently turn every mrpack file into empack-managed content.

[Lean](Update.lean) implements the inspected hash-only plan, the proposed path-aware plan, the required-only reparse guard, and a labeled overlay simulation. Four laws cover path/hash requirements and the guard. [Bend](Update.bend) models the reuse decision with two checked laws; it does not implement the generic list plan. The [shared replay](../launchers/conformance.py) matches six Lean plans against the executed source fragment and checks 52 Bend reuse decisions. The proposed path-aware plan produces the six intended inventories in simulation. This is bounded proposal evidence, not a correctness proof for all imports.

The independent target is the incoming fixture inventory. Matching the current source plan alone would miss the problem. The negative controls therefore reject hash equality as sufficient placement identity and retain the empty-list guard instead of omitting an inconvenient branch.

## Overrides and user state

The same source explicitly schedules prior common and client overrides for deletion and stages incoming overrides. That flow does not supply a seed-ownership guarantee for settings such as `options.txt`. It should not be equated with an empack channel's managed/seed reconciliation. No live user settings were touched or tested by this source probe.

Preserve the distinction between managed-pack metadata, indexed downloads, overrides, launcher configuration, and user-written game data. Their roles and update rules differ. Any broader preservation policy needs explicit ownership and conflict decisions; it cannot be inferred merely from identical bytes or an unchanged pack version.

## Adoption and verification

The keep-current alternative avoids changing update selection, but retains the demonstrated planning counterexamples. The path-aware candidate changes selection only; it need not change mrpack format or saved index schema. Review parser path normalization, duplicate entries, disabled resources, optional environments, and downstream publication before an implementation decision. Determine whether an existing upstream correction supersedes the pinned behavior before proposing a patch.

A native regression should install a disposable pack A, update it to B with a moved indexed file and a second changed entry, and inspect both target paths and hashes. Add swapped-content, unchanged, single-file, disabled, missing/modified-local, and cancellation cases. Test the actual instance publication path and preserve prior usable content on failure. A Qt probe is an intermediate check; it cannot substitute for these GUI/application observations.

No production Prism or empack changes were made. The existing host contracts can carry destination/content identities, staged candidates, scoped effects, and publication evidence. The missing predicate is application-level placement compatibility, not a new host abstraction. Most of the Prism inventory and its full launch lifecycle remain open.

The [instance-library band](LIBRARY.md) separates display, directory, and UUID identity, grouping persistence, trash/delete effects, and undo references through selected Qt methods and private files. Its caller, watcher, OS-trash, and full GUI obligations remain open.
