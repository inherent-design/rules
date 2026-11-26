# npm: installed metadata must describe materialized selections

The first correction belongs between Arborist's resolution-only work and hidden installed-index publication. Preserve npm's resolver and public lock meaning. The [native lock-mode study](../js-peers/LOCK-MODES.md) reproduces a subsequent ordinary installation that reports success while the physical package and fresh runtime remain at the old exact version. A more accurate success message alone cannot correct that state.

## Values and source owners

| Value | Meaning and current owner |
| --- | --- |
| Raw request and override | Author intent plus effective edge policy; preserve direct raw-declaration protection and nested ancestry. |
| Ideal tree and root lock | Desired exact selection; Arborist reification and its ideal-tree persistence path. |
| Actual-tree view | Filesystem-derived or admitted hidden-metadata graph; `arborist/load-actual.js`. |
| Hidden lock | `node_modules/.package-lock.json`, an installation accelerator whose claims must agree with actual selected backing. |
| Installed metadata and program bytes | Physical package metadata and fresh consumer observations; neither is established solely by a current root lock. |

In the pinned `reify.js`, `#reifyPackages` skips package work for `packageLockOnly`. Later code assigns the ideal tree into `actualTree` and saves its metadata as the hidden lock without the same mode guard. The selected actual-tree loader can accept that index and return a virtual tree before reading the physical tree. Presence/mtime checks and other options still matter; this is not a claim that every hidden file is admitted.

The observed hidden-file removal control forces a physical read and the next ordinary install reaches the requested version. `ci` also reaches it in the fixture, after its manifest/lock check. These controls support the mechanism; neither is a general cleanup or safe-repair recommendation for arbitrary projects.

## Correction and API direction

Keep root-lock publication separate from installed-index publication. A resolution-only result may record a new desired graph, but it must not publish that graph as observed installed state. The smallest producer direction is to skip that hidden-index write and invalidate an unestablished installed-index claim, while preserving package payloads and existing root-lock formats. `dryRun` must still prevent the invalidation itself. Filtered workspaces and linked strategies need their own ownership checks.

Preserving a previously valid actual index is another option, but its validity must already be established. Blind preservation can retain an index corrupted by an earlier affected run. The producer guard also does not by itself repair an already misleading index consumed by an ordinary install. The reader has an existing `forceActual` bypass; use the real filesystem path when the metadata's materialization basis is uncertain. A correctness-first fallback has a performance cost that must be measured before optimizing it away.

A new hidden-index provenance format is not selected. It would require mixed old/new writer tests: an old writer may preserve unknown fields while replacing the graph, so a version string or a Boolean marker alone is not necessarily sufficient. If future work chooses such a format, bind the claimed materialized image and qualify legacy fallback, partial writes, and old writers. Do not use process version, filename, or freshness alone as proof that the underlying selection is correct.

Preserve the established `Arborist.reify` return contract during a correction. Its historically named `actualTree` can represent the selected ideal tree in lock-only mode; renaming or reinterpreting that public property is a separate compatibility change. A scoped result adapter can state that resolution was saved and materialization was not requested, with separately observed installed-index effects. New result names here are conceptual; no new default JSON or SDK response is implemented.

## Wider operation results

The [SBOM study](../js-sbom/README.md) distinguishes artifact integrity assertions and inventory metadata from current installed-file equality. Preserve npm's missing/invalid edge refusals and explicit virtual-tree reporting. Its root CycloneDX display can use the physical placement name while its package reference identifies the authored package. Review the format's identity rules and downstream consumers before changing a displayed field; do not force reinstallation simply to produce inventory metadata.

The [publication study](../js-peers/PUBLICATION.md) separates acknowledged acceptance from later hook failure. Keep that acknowledgement attributable even when the process exits unsuccessfully; a lost response instead requires inspection before retry. Loopback acceptance is not proof of real registry durability. Existing credentials, policy, and auth routes are not changed by this proposal.

[Workspace selection and continuation](../js-scripts/WORKSPACES.md) also retain npm's own behavior. An opt-in result may identify selected workspaces and terminal outcomes from actual observations. Do not add a scheduler, invent a blocked reason from absence of a start event, or treat a process exit as proof that every child retired.

## Compatibility and falsifying checks

Keep manifest and root-lock formats, raw override rules, ordinary versus clean-install meanings, current acquisition/integrity policy, and default SDK/JSON shapes. A hidden index is replaceable optimization state; invalidating it does not authorize removing package payloads. Keep-current plus clearer output is insufficient for the reproduced stale-install sequence, though existing workflows remain available while a fix is reviewed.

Qualification must compare requested selection, root lock, hidden index, physical package metadata, and fresh runtime independently after lock-only followed by ordinary install. Cover an already bad legacy index as well as newly generated state; unchanged requests, index absence/staleness, filtered workspaces, linked/nested/hoisted strategies, dry-run, hooks, partial failure, interruption, and mixed writer versions can distinguish incomplete fixes. Measure filesystem-read cost separately from correctness. No production patch or current-latest behavior is claimed here.
