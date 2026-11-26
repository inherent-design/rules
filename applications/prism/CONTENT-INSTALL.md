# Prism: local file installation and completion

The selected Prism 11.1.1 installation method can delete its existing destination before discovering that the source was a symlink to that same destination. In the owned fixture, it returns false, leaves the destination absent, and leaves the incoming link dangling. This is a reproduced selected-method failure, not a qualified full-launcher or GUI defect.

Two private proposals avoid that loss in the measured case. A canonical-file guard refuses the alias before deletion; staged copying captures the source before replacing the destination. Neither proposal is adopted into Prism or empack. Complete launcher, host, concurrency, and recovery qualification remain open.

## Source and executed scope

The [source ledger](../sources/prism-content-selections.json) pins Prism revision `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. Original `Resource` construction, parsing, type/validity getters, `ResourceFolderModel::installResource`, `dropMimeData`, and selected filesystem helpers execute against real QtCore 6.12.0 on macOS arm64, compiled with Apple Clang 21. The installed launcher and its bundled Qt 6.9.3 were not executed.

The fixture renames one install-method symbol so a wrapper can observe each child result. Its concrete resource context omits QObject reflection and lifecycle behavior. ASCII path conversion and display-size adapters are explicit; the unsupported fresh-folder copy adapter throws if reached and was never called. Watching and refresh are controlled inputs. This is a regular-file method study, with real filesystem effects, rather than a simulated installation or a complete application integration test.

`Resource::parseFile` classifies filesystem entries and filename suffixes. Its base `valid()` accepts a known type. This does not validate ZIP contents, mod metadata, Minecraft compatibility, pack selection, or runtime behavior. `Mod::valid()` has a separate parsed `mod_id` requirement; the fixture does not substitute base validity for that subclass contract.

## Observations

The [original capture](../evidence/prism-content-install-20261126T015852314941Z/receipt.json) contains eight cases. Independent Python `lstat`, byte hashes, and entry records corroborate the Qt before/after views.

| Request or context | Method result | Observed effect |
| --- | --- | --- |
| Fresh regular file | True | Source bytes appear at the destination. |
| Regular overwrite | True | New bytes replace the old destination. |
| Exact same source/destination path | False | Existing file record is unchanged. |
| Incoming symlink targets the destination | False | Destination is deleted; source link becomes dangling. |
| Existing disabled sibling only | True | New enabled file appears; the old `.disabled` file remains. |
| Drop with one existing and one missing source | Drop returns true; children return true/false | First copy remains; the missing item is not installed. |
| Drop with the destructive alias | Drop returns true; child returns false | The destination is lost. |
| Controlled refresh returns false | Install returns false | Copy has already completed; new bytes remain. |

The alias source and destination have different path strings but name the same backing file. The original lexical equality guard does not catch that relationship. The regular-file branch deletes the destination and then calls `QFile::copy`; the dangling source makes that copy fail. Both direct installation and drop reproduce the loss. Equal bytes at distinct regular paths are a different relation and should not trigger an identity refusal.

The disabled-neighbor observation is a policy question, not proof of duplicate loading or the final list shown by Prism. Likewise, the refresh callback's false result is not a rollback. Source inspection shows that `update()` can return false when work is already scheduled or when it cannot create a task. The controlled callback does not distinguish those real causes or execute the watcher/task system.

## Preserve three completion meanings

Keep **drop handled**, **per-file installation result**, and **refresh state** distinct. The selected Qt drop method returns true after handling its URL list, without aggregating child results. Changing that framework boolean to mean “all copies succeeded” would silently redefine its contract. Preserve the framework result and retain separate file outcomes for user feedback.

A proposed internal receipt can carry the affected source/destination, copy outcome, preservation outcome, and refresh evidence while keeping a compatibility boolean adapter for current callers. Do not infer a detailed refresh reason from the existing boolean. A completed copy with an unconfirmed refresh needs different feedback from a copy refusal or a lost target. Useful feedback would name the affected file, the completed or failed action, and whether a refresh or recovery is needed. A batch summary should retain successful items and failures rather than imply rollback from a final false result.

This does not require a new command, archive format, or general status framework. First identify existing task/error/reporting mechanisms in the real caller and reuse them where they can retain these facts. Caller/UI design and production implementation remain separate work.

## Private proposals and compatibility

The [proposal capture](../evidence/prism-content-candidate-20261126T020852548554Z/receipt.json) contains thirteen native cases: six shared controls for each proposal, plus a staged cancellation control.

**Canonical-file guard.** Before destructive work, compare nonempty canonical source and destination paths and refuse equality. Fresh copy, overwrite, and equal-byte distinct files still succeed. Exact self-path and the known symlink alias refuse without changing the old file record. This is a narrow identity check, not a defense against all aliases, hard links, path races, or concurrent changes. Refusal also changes the alias workflow: the caller needs actionable guidance rather than an unexplained false result.

**Staged copy.** Open the input, write bounded chunks to `QSaveFile`, close the input, and commit only after successful reading/writing. Explicitly disable direct-write fallback. Under the selected normal-return conditions, the alias's bytes are captured before destination replacement; its link remains usable. Fresh copy, overwrite, and equal-byte distinct files succeed. An authored cancellation hook before commit returns false and preserves the exact old destination record, with no staging residue in the owned after-state.

The [QSaveFile contract](https://doc.qt.io/qt-6/qsavefile.html) explains temporary writing, commit, destruction without commit, and the weaker direct-write fallback. Documentation supports the design choice; it does not prove all platform implementation or durability properties. The candidate does not qualify arbitrary IO faults, permission changes, ACLs, extended attributes, hard links, symlink destinations, disk exhaustion, external writers, interrupted processes, reboot, or all Qt versions. Review those behaviors before choosing staged replacement as a production correction. A larger [continuation](../evidence/prism-content-chunk-20261126T022625562938Z/receipt.json) reuses the identical verified binary to copy 131,084 bytes with 65,536-byte read requests. Its independent destination digest matches the source. This exercises the larger-input path; it does not observe physical read counts or prove arbitrary-size handling.

The **keep-current alternative** preserves current callers and replacement behavior, but retains the demonstrated loss. It is only defensible for a restricted context that excludes source/destination backing aliases before reaching the method; a filename-only comparison does not establish that restriction. Do not silently impose such a premise on arbitrary user-selected files.

No saved format change or migration is needed for either focused proposal. Before upstream work, check whether a newer Prism implementation already addresses this pinned behavior. Then qualify real callers, installed/bundled Qt, the supported hosts, permissions/metadata, cancellation, and file-list refresh. Keep mod validity, resource availability, game selection, and runtime compatibility separate.

## Models, replay, and preserved evidence

[Lean](ContentInstall.lean) states fourteen laws and [Bend](ContentInstall.bend) states thirteen. Their selected projection keeps policy, source relation, opaque payload identity, disabled sibling, drop handling, refresh, and cancellation separate. Zero means absence, not an empty file. Accepted IO and immutable input are explicit premises for the staged model; filesystem atomicity is not derived from a pure transfer rule.

The [proof gate](../evidence/prism-content-candidate-20261126T020852548554Z/proof-gate.json) checks two Lean modules and one Bend file. The [independent observer](content_observations.py) derives model requests from actual inputs and before-state relationships, and measured results from Qt/Python after-states. It checks source/body correspondence, binaries, frozen producers, streams, final private files, and group retirement in owner mode. The [replay](content_conformance.py) compares all 22 measured outcomes against both models and checks fifteen decoder refusals, five changed premises, and nine changed raw observations, including a coherent counterfactual that hides the original alias loss.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/prism/content_conformance.py
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/prism/content_conformance.py --public-only
```

Neither command launches Prism, compiles a native fixture, or repeats filesystem installation. The frozen owner collectors additionally depend on the retained private acquisition manifest, source caches, and native toolchain; they are not advertised as a fresh-clone collection workflow. Public mode reproduces the same fact/basis artifacts and explicitly excludes unavailable private source, binary, and final-file readbacks. [Comparison artifacts](../evidence/prism-content-comparison/controls.json) retain that scope. The first [failed compilation](../evidence/prism-content-install-20261126T015803830720Z/commands.json) is preserved separately: an omitted adapter getter caused compile failure, and no method cases ran. A fresh corrected collection supplied the observations; no original failure was overwritten.

All recorded compiler/runtime groups retired; the later exact-work argument scans found no remaining fixture process. This is bounded retirement evidence, not a universal descendant census. Private generated upstream excerpts, binaries, sources, and final fixtures remain retained. No personal launcher instance, account, game, world, or production source was changed. Complete feature and scenario statuses remain pending.

For empack's portable-authoring proposal, the useful constraint is to retain the captured input image, destination authority, publication result, and later view refresh independently. Path labels and equal bytes are not sufficient backing identity. A false return cannot establish preservation, and accepted UI dispatch cannot establish successful publication. These are comparative obligations; this Prism finding does not establish an empack bug or select a new production API.
