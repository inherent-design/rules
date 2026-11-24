# restic: snapshot references, retained data, and physical packs

This is the first bounded feature band within the larger [application study](../README.md). It does not complete restic's inventory or qualify its other backends, general retention policies, repairs, or key operations. A later [snapshot-selection and grouping band](SELECTION.md) covers selected filters and keep-last-one previews.

## Current domain and evidence

The selected program is restic 0.20.0, compiled with Go 1.27.4 for macOS arm64. The isolated binary matches the publisher's release-asset digest and checksum file; GPG provenance was not verified. The fixture uses only a new local repository, two fake text files, generated private credentials, and explicit full snapshot IDs. Credentials and the encrypted test repository remain in ignored work storage.

The source revision is `9c88ff768f10c192dc6a87619a65a16374080e33`. `internal/data/snapshot.go` gives snapshots both a `Parent` and a `Tree`. `cmd/restic/cmd_prune.go:getUsedBlobs` enumerates remaining snapshots, gathers their `Tree` roots, and traverses their blob reachability. It does not follow `Parent` as a retained snapshot root. The source locations and digests are retained in `../sources/restic-selections.json`.

The native lifecycle at `../evidence/restic-20261124T001750826529Z/` establishes these selected facts:

- Both snapshots' three selected file-data blobs were readable before reference removal.
- Dry-run forgetting retained both snapshot references and exact pack bytes.
- Actual forgetting removed snapshot A while leaving all four pack files byte-for-byte unchanged.
- Snapshot B's parent still named A. That historical relation did not keep A's exclusive data alive.
- Prune repacked one partially used pack and removed unused data. The repository had three packs afterward; B's shared/new file blobs remained readable, and the old exclusive blob was no longer found.
- A full `check --read-data` and restore of B passed. Restored file bytes matched B's source hashes; the live fixture source was unchanged.

The 16 KiB to 12 KiB pack allocation sample is filesystem accounting for this tiny fixture, not a whole-volume space claim or a general compression result. Snapshot references, plaintext blob availability, and encrypted pack identity are different projections. [Repository design](https://restic.readthedocs.io/en/stable/100_references.html), [reference removal and prune](https://restic.readthedocs.io/en/stable/060_forget.html).

## Models and premises

[Lean](Retention.lean) and [Bend](Retention.bend) model snapshot IDs, optional lineage, selected reachable data, forgetting, and guarded pruning. Lean checks six laws: forgetting preserves availability; missing exclusive coordination cannot reclaim; retained available data survives; a live snapshot holds its selected data; changing lineage does not change retention; and pruning is idempotent under a stationary root set.

[Conformance](conformance.py) feeds actual snapshot/blob IDs from the native fixture into both executable models. It compares their results with pre/post native blob reads, exact pack observations, and restored bytes. Treating the historical parent as a retaining edge predicts the wrong result and is rejected. The no-exclusive case preserves all data in the model; it is not a native concurrent-lock test.

The reachability input is a **selected three-file-data-blob projection**. The fixture selected `prune --max-unused 0`; partial-prune policies can legitimately retain additional unused data and are outside this function. A complete repository tree/index/pack decoder and exclusive-lock correctness remain premises. The no-exclusive branch expresses a proposed safe admission rule; it does not claim that restic's unsafe `--no-lock` override enforces it. These models do not implement encryption, compression, object loading, generic retention grouping, network consistency, or repair. They cannot establish safety for unknown or omitted roots.

```sh
LEAN=/path/to/lean BEND=/path/to/bend \
  python3 applications/restic/conformance.py \
  applications/evidence/restic-20261124T001750826529Z
```

Compile `Retention.lean` into `.build/applications/restic/Retention.olean` first. Conformance executes only Lean/Bend and retained cases, not restic. Native collection is the separately selected `python3 applications/restic_probe.py`; it creates a new ignored repository rather than opening a user backup.

## Preservation decisions and proposed improvements

**Preserve typed relation meaning and two-stage retirement.** Do not make every historical or provenance link keep its target alive. Do not replace forget/prune with an indiscriminate delete operation. A combined operation can remain available when explicitly selected, but its receipt must distinguish reference removal from pack reclamation. This is a useful domain distinction, not a defect in restic's existing reachability design.

**Investigate typed IDs at the snapshot-to-tree boundary.** The inspected `Snapshot.Parent` and `Snapshot.Tree` use the same underlying `restic.ID` type, while the loader/operation context gives them different roles. A proposed internal change is explicit snapshot/tree/blob/pack ID wrappers at high-risk boundaries, preserving the existing hexadecimal wire representation. That could make accidental namespace or retention-edge substitution harder. No such defect was reproduced. Keeping the current file-type-scoped APIs and strengthening their boundary tests is a reasonable alternative if wrapper conversions add more complexity than protection. This candidate is not yet implemented or separately proved; inspect callers and codecs before deciding. Internal wrappers should not require rewriting existing backup repositories, but Go callers, JSON codecs, and plugin-facing interfaces need compatibility review.

**Provide an optional explicit-ID deletion receipt.** In this version, both `forget SNAPSHOT --dry-run --json` and actual `forget SNAPSHOT --json` returned 0 with empty stdout/stderr in the fixture. The following snapshot inspection established their different effects. That is a concrete automation limitation, not evidence that the deletion failed. The root flag promises JSON for supported output; this study does not assume every command form currently promises a document.

A proposed opt-in report should identify the selected repository/IDs, preview versus apply, per-reference confirmed/unknown effects, and whether prune was requested. A possible human summary is “Removed one snapshot reference; pack data was not pruned.” Unknown backend acknowledgements must remain unknown. Adding an opt-in format is safer than unexpectedly changing the output of existing scripts. Keeping the current interface and requiring an explicit post-command snapshot query is the alternative, with the cost of extra calls and concurrent-state ambiguity.

Acceptance should include exact-ID and policy-group forms, missing IDs, changed selection, partial/unknown backend outcomes, and independent pack accounting. A preview must not claim removal; successful reference removal must not claim reclaimed content. The new receipt/type candidates remain proposed work, not changes to this program.

## Remaining feature work

General snapshot grouping and policy evaluation beyond the selected keep-last-one fixtures, scans and partial backup, general multiple readers/writers and stale-lock decisions, remote backends, corruption and repair, keys, format migration, mount/dump, copy, exclusions/metadata, and cache/resource policy remain pending. The inventory keeps those entries separate. A passing local restore does not qualify them.

A later [lock/interruption band](LOCKS.md) tests selected compatible appenders, exclusive maintenance refusal, retry, known-process cleanup, and published-versus-admitted evidence. Backend/identity/age/refresh and partial-data recovery remain open.

The later [restore-policy band](RESTORE.md) separately compares overwrite/mtime admission, verification scope, filtered deletion, dry-run effects, and a leaf-symlink control. Those observations do not expand this earlier retention projection’s premises.

The later [backup-capture band](BACKUP.md) distinguishes metadata-based content reuse, forced reading, partial snapshot publication, dry-run result IDs, and unchanged suppression. These fixed local cases do not qualify general backup or live-source consistency.
