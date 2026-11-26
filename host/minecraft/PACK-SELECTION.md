# Pack choices, repository order, and application

Pack discovery, displayed choices, repository membership/order, saved user options, opened resources, and completed application are different states. This source map follows their consuming boundaries. It extends the [five-release linework](BREADTH-LINEWORK.md) and [detector comparison](PACK-DETECTION.md); it does not promote those comparisons to pack-selection or full-game conformance.

The [source ledger](pack-selection-sources.json) reuses ten attributed repository/UI-model views across Java 1.21.1, 1.21.4, 1.21.5, 1.21.11, and 26.3. Eight additional retained views cover selected downstream clauses in 1.21.1 and 1.21.5. Their original classes, mappings, and view bytes have separate identities. The older downstream translations' acquisition producers were not newly recovered, so their source interpretation retains that limitation. Two original `Options.loadSelectedResourcePacks` methods were additionally disassembled as data to resolve one branch. No Minecraft method, UI, resource reload, game, provider combination, or renderer ran for this band. There are no new proofs or native-conformance claims.

## Repository selection and required placement

In all five inspected repository views, discovery builds a map keyed by pack ID. A later emitted pack with the same ID replaces the earlier value in that map. This does not establish loader/provider composition order or which artifact wins in a real modded environment. The available map and selected list retain different roles.

`setSelected` maps requested IDs through the available map, drops unavailable IDs, and retains the order and repeated occurrences of the remaining requests. It then inserts required packs not already contained in the resulting list, using each pack's default position and fixed-placement policy. The source does not check compatibility in this method. Compatibility admission happens in other consumers; a repository selection call is insufficient evidence of consent or compatibility.

`getSelectedPacks` exposes the selected collection, whereas `getSelectedIds` collects IDs into an immutable set. That projection loses multiplicity and must not be used as an ordered resource-stack receipt. Direct `addPack` and `removePack` have narrower membership checks than a rebuild; in particular, the raw removal method does not itself enforce the UI's required-pack guard. A later rebuild can reinsert a required pack. This is an API distinction, not evidence that the ordinary UI permits removing a required pack.

Repository reload captures selected IDs, rediscovers available packs, and rebuilds selection. A request's continued presence does not establish unchanged bytes, metadata, supplier, or applied resources. Pack equality, available-map keys, selected objects, and physical backing also need their own identities; do not substitute filename or ID equality for all of them.

Java 1.21.4 adds `isAbleToClearAnyPack`, comparing the current selected list against rebuilding an empty request. It does not promise that selection becomes empty. Java 26.3 changes selected pack opening from one resource object per pack to flattening each pack's resource stream. This is a resource/ownership API change, not just a return-type spelling change. Partial opening, stream ownership, and cleanup need consumer qualification.

## Displayed order, guards, and callback effects

The UI model starts with repository selection in reverse order for display. Its unselected list starts from available packs with selected entries removed. Updating the repository reverses the displayed selected list back into requested IDs. A model move changes its local list and invokes the list-change callback; that method does not itself update the repository. Commit updates the repository first and then calls the output consumer.

A raw toggle removes an entry from one list, inserts it into the other, invokes the callback, updates repository selection, and finally handles the high-contrast option. These are sequential effects, not an atomic transaction. If a callback throws, source order does not imply restoration of earlier list edits. Likewise, an output callback failure can follow a repository update. Actual callback behavior and reachable exceptions have not been exercised here.

The baseline `TransferableSelectionList` source checks `canSelect`, `canUnselect`, or `canMove*` before its corresponding action. Incompatible selection opens a confirmation screen and selects only on acceptance. Raw entry methods and their guarded callers therefore need different contracts. A deliberately invalid direct call cannot by itself establish an ordinary UI defect. Mouse visibility, keyboard actions, selection focus, and required/fixed placement also have separate guards.

The baseline screen's close path commits before closing its directory watcher. The source order alone does not guarantee watcher cleanup if commit fails. Directory changes schedule a later refresh; that refresh rediscovers packs and updates list presentation. This is not evidence that a saved selection or applied resource generation already changed.

The first three UI-model views use a `Runnable` list-change callback. In 1.21.11 it becomes a consumer of the entry, which 26.3 retains. That is an additional callback input; callback ownership and the current model generation remain relevant. Later screen/widget consumers have not been inspected for this follow-up and must not inherit baseline UI qualification.

## Saved choices and compatibility memory

The inspected 1.21.1 and 1.21.5 `Options.updateResourcePacks` bodies derive saved user IDs from selected packs excluding fixed-position entries. They separately retain incompatible IDs, attempt to save options, and request a resource reload when the saved user list differs from its previous value. An unchanged ID list is not a byte-identity comparison. The selected 1.21.5 save body catches an exception and logs failure; its normal return is not a durable-write receipt. Original disk-failure behavior was not exercised.

Loading saved choices is another operation. The selected bodies try the requested ID, then a `file/`-prefixed fallback for a missing unprefixed ID. They remove missing entries and incompatible entries lacking a remembered allowance. The selected accumulator is a linked set, so this path deduplicates admitted IDs even though direct repository `setSelected` preserves repeated requests. Compatibility memory uses the original saved string in the inspected conditions; the resolved pack ID may differ after the fallback.

One branch needs explicit preservation in future rules. In both original 1.21.1 and 1.21.5 method disassemblies, a currently compatible pack whose saved string remains in the incompatibility list has that marker removed, then jumps past the selected-set insertion. The bytecode removes at offset 189, jumps at 195 to loop continuation 210, and skips insertion beginning at 198. At the end it submits the accumulated set to the repository at 215. Thus this branch does not itself add that occurrence to the requested selection; required-pack rebuilding is a later operation.

This is a static control-flow fact, not a reproduced startup/UI defect. Actual caller state, repeated saved entries, required membership, subsequent calls, and user-visible persistence can change the consequence. No claim about later releases, normal reachability, or a production correction follows. A proposed change to retain the now-compatible entry needs an original-method control and a caller-level compatibility review first.

## Applying resources and recovering from failure

The selected baseline and 1.21.5 client reload bodies first handle an existing/pending reload, then refresh the repository and open its selected resources before constructing the reload overlay. The returned asynchronous operation and the already changed selection are different facts. Joining or returning that operation is not evidence that every consumer has applied, rendered, or retired its old resources.

The baseline resource-manager source closes its old manager before constructing and assigning a replacement and starting listener reload. Its multi-pack manager keeps a copy of the supplied pack list and dispatches namespaces/filters; its close iterates packs. These clauses do not prove all-or-nothing publication, full close after a throwing child, native retirement, or stable resource bytes. The existing [resource rules](RESOURCES.md) and [reload scheduling study](RELOAD-SCHEDULING.md) qualify their own narrower boundaries.

The selected client error path named `rollbackResourcePacks` conditionally invokes recovery. Recovery requests an empty repository selection, clears saved user pack and incompatibility lists, attempts to save, and starts a recovery reload. Required packs can remain through repository rebuilding. This is clearing/rebuilding selection, not restoration of the previous user-selected stack. Downloaded-pack recovery callbacks and failure UI are additional effects. The 1.21.5 follow-up toast explicitly uses the client executor; the baseline uses the selected future's continuation path. Neither source clause establishes rendering or callback completion here.

## Rules and UX to qualify next

The next bounded model and comparison should preserve the whole selection path, with separate observations for:

- Requested IDs, available pack identities, required/fixed placement, ordered selected objects, and the lossy selected-ID set.
- Displayed lists and pending moves, guarded actions and compatibility consent, repository mutation, output callbacks, and focus/watcher cleanup.
- Saved user IDs, remembered incompatibility, save acknowledgement, requested reload, opened resources, and the applied generation.
- Failure stage, effects already completed, recovery selection, retained resources, and confirmed retirement.

Meaningful controls include duplicate/unavailable IDs, required insertion, fixed placement, same-ID replacement, a declined incompatible selection, a callback failure after a local edit, output failure after repository update, the now-compatible remembered entry, unchanged IDs with changed backing, opening failure, and recovery with required packs. A source-derived simulator must remain separate from original-method, source-fragment, and full-client evidence.

Human and machine feedback should say whether choices were edited, selected in the repository, saved, awaiting application, applied, or cleared during recovery. A save or reload failure should identify remaining choices and effects and offer a safe retry or reconciliation step. Do not say the old configuration was restored from the recovery method's name. Preserving a user's prior selection for review is a candidate UX improvement; it has not been implemented or selected as a compatibility break.

The five-family and expanded-goal requirements remain incomplete. This map adds consumer structure and one bytecode-qualified branch; it does not close metadata/compatibility codecs, later UI/client paths, provider composition, pack-content stability, callbacks, whole reload, backend behavior, or native platform qualification.
