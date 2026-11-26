# Retention policy through deletion, pruning, and restore

The JSON retention groups describe the policy's selected removals. They do not certify that those deletions succeeded. In this restic 0.20.0 fixture, both deletions fail, the same planned IDs remain under `remove`, the command exits 3, and pruning never starts. After correcting the owned permission fault, the combined operation succeeds and both retained backup groups restore correctly.

This joins the existing [selection/grouping](SELECTION.md) and [explicit-ID retention](README.md) bands. It uses the pinned macOS arm64 binary, Go 1.27.4, and source revision `9c88ff768f10c192dc6a87619a65a16374080e33`. It qualifies one generated local lifecycle, not all retention policies, backends, concurrent owners, or recovery situations.

## Selected procedure and evidence

A new private repository contains four snapshots: two chronological versions of each of two host/path groups. Every source has a shared file and a per-version state file. Dates are distinct; the request uses default host/path grouping and `--keep-last 1`. The five selected file-data blobs are read before the operation, independently checking their plaintext hashes.

All effects are confined to a newly generated repository, source directories, restore targets, and private cache/HOME. A random password stays in a mode-0600 file outside the captured scopes. Neither the password nor its hash enters the report or replay. Existing fixtures, repositories, source trees, credentials, and personal backups remain untouched. This is an owner-run fixture outside ordinary CI.

The [first capture](../evidence/restic-policy-join-20261125T235000202024Z/commands.json) contains 13 calls. The collector expected a generic exit 1 for deletion failure; the actual structured partial-operation status is 3. It stopped and restored the original snapshot-directory mode in `finally`. The frozen producer, original failure, streams, and authored permission changes remain retained.

The [completion capture](../evidence/restic-policy-join-20261125T235101268551Z/receipt.json) adds only the remaining ten calls. Its continuation checks the complete repository/source/target image against the retained post-restoration image before proceeding. None of the initial 13 calls is repeated. All 23 recorded process groups are absent; the original directory mode is restored.

| Boundary | Selected request | Observed result |
| --- | --- | --- |
| Preview | `forget --keep-last 1 --prune --max-unused 0 --dry-run` | One keeper and one planned removal per group; prune summary follows. Exit 0; repository bytes and references unchanged. |
| Deletion refusal | Same combined request without `--dry-run`, while the owned snapshot directory is read-only | Both removals fail. JSON still lists the two planned IDs; stderr reports the two permission failures and structured exit 3. Repository bytes and references remain unchanged; no prune summary appears. |
| Corrected application | Restore the original directory mode, then repeat the authorized combined request | Exit 0; the two old snapshot references disappear; the newest snapshot in each group remains. Prune summary follows. |
| Verification | `check --read-data` | Exit 0, zero reported errors. This verifies the remaining repository's data, not the removed snapshots. |
| Selected blob reads | Read all five selected file-data identities again | Shared/current blobs remain readable; both old exclusive file-data blobs are no longer found. |
| Consumer restoration | Restore each exact retained ID into its own target with `--verify` | Both exit 0. An independent target walk matches the source file hashes, sizes, modes, and entry kinds. |

`--max-unused 0` selects full reclamation for this fixture. The observations do not characterize the default unused-data allowance, partial repacking, all metadata, or whole-volume free space. The retained snapshot's `Parent` still names historical lineage; that reference does not keep an old snapshot's exclusive file data alive.

## Source and reporting phases

[Five source selections](../sources/restic-policy-join-selections.json) identify the relevant boundaries:

- `runForget` obtains an exclusive repository lock before selection and mutation. Unsafe no-lock modes are not used.
- Policy grouping and `ApplyPolicy` produce the keep/remove groups and planned snapshot IDs.
- `ParallelRemove` records deletion failures separately. Other removals may already have succeeded before the caller knows the batch failed.
- The group JSON is emitted before the failed-removal check. Any recorded removal failure returns before `runPruneWithRepo`.
- Successful combined pruning enumerates remaining snapshot `Tree` roots while excluding the removed IDs. `Parent` is historical metadata rather than a retaining edge.

The all-refused native case exercises the early return with no reference changes. A partial-subset failure is source-modeled and appears in a separate executable example; no native subset-failure claim is made. The observed numeric exit 3 belongs to this pinned executable's structured error. The global error mapper and other versions are not newly qualified.

Preview and successful `--json` output contain two JSON values: the retention-group array followed by a typed prune-summary object. The refusal contains the group array and a separate structured stderr error. Treat the command as a phase stream rather than calling one whole-stdout JSON decoder or interpreting the array as a completion receipt. Raw bytes and each parsed value stay available in the retained evidence.

## Models, premises, and replay

[PolicyJoin.lean](PolicyJoin.lean) and [PolicyJoin.bend](PolicyJoin.bend) compose the existing Selection and Retention rules. Eight new Lean laws and eight Bend laws distinguish preview, planned IDs, completed reference removals, surviving roots, selected backing, prune admission, and final status. The source-only partial-refusal example removes one reference, preserves backing, and refuses pruning. It is deliberately excluded from native comparison.

Lean computes group-relative selection. Bend reuses the existing decision predicate over adapter-supplied same-group/newer witnesses. The adapter checks the exact native group membership and distinct timestamps; Bend does not independently implement the native grouping or repository decoder.

Three native boundaries agree with both models on four snapshot IDs' membership in the planned, removed, and surviving sets, five selected file-data identities, prune phase, and exit code: 57 membership and phase values. Six changed-output controls and four decoder refusals protect the comparison. The decoder rejects unsupported schema, duplicate IDs/ranks, incomplete selected reachability, and unknown refusal identities.

The reachability projection is a closed witness from the owned backup inputs, backup summaries, before/after blob reads, and keeper restore readbacks. This band does not decode every native tree/index/pack to reconstruct the complete graph. General repository reachability, cryptography, process coordination, and backend consistency remain separate obligations. Formal pruning uses the existing exclusive, stationary-root premise; it does not prove restic's entire lock implementation or admit unsafe overrides.

The [comparison](../evidence/restic-policy-join-20261125T235101268551Z/conformance.json), [basis hashes](../evidence/restic-policy-join-20261125T235101268551Z/basis.json), and [controls](../evidence/restic-policy-join-20261125T235101268551Z/controls.json) bind this scope. Replay invokes only Lean/Bend and retained-data readers:

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/restic/policy_join_conformance.py
```

`--public-only` excludes installed-binary, cached-source, and latest private-tree readbacks. It still validates streams, phase framing, snapshot IDs, permission-change lineage, selected blobs, target snapshots, model results, and controls. No replay reads the password file or reruns a backup, deletion, prune, or restore.

## UX and compatibility decisions

Preserve the existing retention policy, default grouping, exit status, JSON group shape, and refusal to prune after deletion errors. The useful improvement is to distinguish a policy plan from the completed deletion result. A final human summary could name planned, removed, failed, and retained snapshot counts and state that pruning was skipped. Partial success must remain visible; an error does not imply every reference survived.

The command already retains `removeSnIDs` and `failedSnIDs`. A future reporting change can derive confirmed outcomes from those existing sets. An additive terminal event is a candidate; changing the meaning or name of `remove` in the existing array would require a compatibility review of downstream parsers. A focused guide explaining the phase stream and exit 3 is a credible keep-current alternative. No new generic transaction or recovery framework is needed for this reporting distinction.

For empack, preserve the same separation among selected work, successful writes, retained ownership, later phases, and final command status. Reuse actual operation facts when reporting partial publication or skipped follow-up work. Backup grouping and data reclamation remain restic-specific policies; this observation selects no production empack API or implementation change.

Before adoption, test partial-subset deletion, stale selection/current-root changes, interrupted prune, failed repack/index publication, concurrent readers/writers, and relevant remote backend outcomes. Preserve source and cache ownership, original error fields, exact identities, and safe retry guidance. The full application study and larger scenario remain incomplete; parent operation statuses are unchanged.
