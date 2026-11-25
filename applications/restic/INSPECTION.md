# Snapshot differences, search coverage, and size measures

This band inspects restic 0.20.0 at source `9c88ff768f10c192dc6a87619a65a16374080e33`. Three generated snapshots, their actual saved payloads, and two disposable repository copies distinguish query results from complete traversal and payload availability. No live repository was opened or modified. The [source selections](../sources/restic-comparison-selections.json), [original commands](../evidence/restic-comparison-20261125T031756971775Z/commands.json), [continuation receipt](../evidence/restic-comparison-20261125T031756971775Z/completion-receipt.json), and [independent verifier](comparison_observations.py) retain the boundaries.

## Command meanings

| Command                      | Selected meaning                                                                                                                                         |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `diff A B`                   | Compares two saved trees and reports path, type, content-reference, and optionally metadata changes. It does not read every file payload.                |
| `ls B /group`                | Lists saved entries under a snapshot path. The path is in the saved tree, not the host filesystem. Recursive selection and sorting are separate options. |
| `find --snapshot B keep.txt` | Searches saved paths. Date limits concern entries' modification times, independently of snapshot dates.                                                  |
| `stats --mode MODE B C`      | Measures selected snapshots according to a counting policy. Different modes count different things.                                                      |
| `cat tree B`                 | Loads a tree selected through a snapshot, optionally with a subfolder.                                                                                   |
| `cat blob TREE_ID`           | Reads a stored blob by its blob ID. A tree ID is not a snapshot selector.                                                                                |

The native fixtures use full snapshot IDs and relative backup targets. They do not qualify every selector, path syntax, pattern, or timestamp format. The `cat` help already documents its argument roles; the retained wrong-role command was a collector mistake, not a missing feature.

Snapshot A contains eleven regular files and two directories. B changes content and permissions, adds and removes paths, moves unchanged content, and replaces a file with a directory containing a new child. C captures the unchanged B tree under another snapshot ID/date. Every saved regular-file payload in A and B was read with `dump` and checked against the fixture's declared bytes.

## A successful search can have an invalid JSON result

In a verified byte-copy repository, the fixture temporarily moves the pack containing B's root tree out of its lookup path. Cache use is disabled. The original repository stays intact.

`restic --json find --snapshot B keep.txt` then returns status 0 and writes two human diagnostic lines followed by `[]` on stdout. The combined stdout is not JSON. `ls`, raw-data `stats`, and `dump` report failure under the same omission. Restoring the exact pack restores valid search output and successful payload reads.

The source explains the result. `Finder.findInSnapshot` prints a load failure through `printer.S` and returns `walker.ErrSkipNode`. The walker treats that root skip as successful completion. The terminal printer's `S` method writes to stdout even in JSON mode; JSON only changes its verbosity setting. The final search writer then appends an empty array.

This is a reproduced executable-boundary failure in the selected pattern-search path. A zero status does not establish a completed search, and the output cannot be interpreted as a valid empty result. Short-ID and ID-search modes, nested-tree failures, and multiple partially readable snapshots have separate test obligations.

A focused candidate would keep diagnostics on stderr, track skipped/unreadable trees, finish the ordinary JSON array, and return a failure status when traversal was incomplete. Preserve any matches already emitted. Reuse the existing visitor and result rendering; this does not require replacing the walker or adding a universal query framework. Returning the existing error status 1 is a compatibility decision to document, and callers currently relying on status 0 would need review. A keep-current alternative retains the demonstrated protocol violation and therefore is not recommended.

## Type changes expose a reference-counter gap

The default A-to-B diff emits a single `T` event for the new directory at `/type-change/`; it does not list its child as a separate addition. That event policy is independent of the blob counters.

The reported counters contain two new data blobs. Independently loaded tree closure contains three new data blobs, corroborated by raw-data statistics over the same snapshots. The omitted child's saved payload is ten bytes. The diff's added-byte counter is ten bytes below the full reachable-blob difference. Reverse comparison exposes the corresponding omission on the removed side. These are reporting differences; the child's actual payload is present and reads correctly.

`Comparer.diffTree` adds the type-changing directory's subtree handle but does not descend into it to collect its descendants' handles. Its ordinary directory recursion and common-subtree optimization otherwise collect reference sets. A full-reachability interpretation of “new/removed data blobs” therefore disagrees with this case. If only references encountered by the event traversal are intended, that narrower measure needs explicit documentation; it is not the same as the snapshot difference.

The proposed counter policy uses complete reachable typed-blob sets while preserving the existing event list. A focused implementation could reuse `collectDir` for directory endpoints of type-changing pairs rather than scan every tree again. It must propagate incomplete traversal or unavailable weights instead of silently certifying complete byte totals. Nested IO faults and shared data moved across a type boundary are remaining native regressions. A full-closure model also shows why the error need not always be an undercount: an unvisited old subtree can hide reuse and make an existing blob appear new.

## Size and count bases remain separate

| Mode                |                         Observed B result | Meaning of the selected measure                                                                                |
| ------------------- | ----------------------------------------: | -------------------------------------------------------------------------------------------------------------- |
| `restore-size`      |             120 bytes, 14 counted entries | Logical size across saved entries; the historically named file-count field includes directories.               |
| `files-by-contents` |             102 bytes, 10 content classes | Globally deduplicates content sequences. Empty content also groups directory/empty-file nodes in this profile. |
| `blobs-per-file`    | 102 bytes, 9 counted locations/references | Its per-path accumulator is gated by the shared global content-sequence set.                                   |
| `raw-data`          |                     2,444 bytes, 13 blobs | Indexed ciphertext lengths of unique reachable data and tree blobs, including tree metadata.                   |

Two distinct B files contain the same eighteen-byte payload. The global content gate skips the second before the per-path accumulator runs. The [pinned manual](https://github.com/restic/restic/blob/9c88ff768f10c192dc6a87619a65a16374080e33/doc/manual_rest.rst) describes both sensitivity to multiple file references and resilience to renames. Those promises need a deliberate counting definition: simply removing the gate would count coexisting paths, but could also count an old and renamed path separately across snapshots.

Separate mode-specific accumulators would make this policy visible: restored entries, unique content sequences, per-location blob references, and unique typed blobs have different keys. The proposed strict per-location alternative is a policy choice, not an automatically accepted fix. Keep current values until that meaning and compatibility cost are settled. Source-reducer examples with shared multi-blob file versions additionally show order sensitivity from the combined content/path state; that is not a native multi-chunk CLI result in this cohort.

Selecting B and C doubles restore size to 240 bytes but leaves raw-data size at 2,444 bytes because their tree/content references are identical. Neither number predicts physical space reclaimed by deleting a snapshot. Pack headers, indexes, keys, other snapshots, and later pruning are separate concerns.

## Metadata availability is not payload availability

The second verified copy temporarily omits only a data pack. Listing, search, and raw-data statistics still succeed because their required tree/index metadata is available. Reading the affected file fails. After the exact pack is restored, the payload reads correctly again.

This behavior is appropriate to the query scopes. A metadata result should not claim successful restoration or data-integrity verification. Conversely, a listing failure can still expose a useful snapshot header. Preserve decoded partial facts, completion under the particular read scope, protocol validity, and exit status separately.

## Verification boundary

The original collector's invalid backup-time argument and later `cat tree` argument-role error remain retained. A separate completion producer performs the remaining reads and copy controls without rerunning the successful 44-command prefix or changing its outputs. The combined record has 85 commands, including the preserved wrong-role failure. Missing source preimages held only in the terminated process were not reconstructed or invented. Snapshot contents, actual saved payloads, later source bytes, and repository byte images provide the stated evidence instead.

Both non-hardlinked copies were returned to their complete original byte images. This is external fixture restoration, not a restic repair result or proof of metadata/inode restoration. Read locks may have incidental effects; final byte equality does not prove no filesystem writes occurred. Public receipts and streams are redacted, with exact originals and transformation hashes retained privately.

[The Lean model](Comparison.lean) and [Bend model](Comparison.bend) separate typed blob handles, saved path components, counting modes, event policy, reference closure, and query outcomes. The [pure replay](comparison_conformance.py) compares both models with 32 retained native outcomes: sixteen statistics requests, four diffs, eight omitted-pack queries, and four successful reads after pack restoration. Five additional rows evaluate explicitly proposed counter, location-reference, and search-completion policies over the saved facts. They are not patched native results. The [conformance record](../evidence/restic-comparison-20261125T031756971775Z/conformance.json) retains exact inputs, results, source/tool hashes, fifteen schema refusals, four changed-premise controls, and six changed-observation controls.

Twenty Lean laws and thirteen Bend laws include the type-boundary counterexamples, content/path counting choices, typed blob namespaces, unavailable weights, and invalid search completion. Equal-tree comparisons legitimately need no weights; unavailable measurements for a nonempty difference remain unknown. The multi-chunk order examples are model-only. The selected macOS nodes also contain extended attributes; the finite metadata-equality witness preserves their exact name/value distinctions. It is not a general attribute codec or platform proof.

The models do not formalize every query parser or selection policy. The independent observer checks the selected listing/search paths and all emitted node fields against saved tree records. It separately checks compression ratios and percentages against integer weights; the models do not substitute low-precision floating arithmetic. Bend uses a checked saved-path ordering witness, while Lean orders paired saved paths itself. General hardlinks, special files, arbitrary codecs and patterns, remote backends, nested faults, and other platform behavior remain open. No production changes or upstream report were made.

To rerun only the retained comparison, supply the existing pinned tools:

```sh
LEAN=/path/to/lean BEND=/path/to/bend python3 applications/restic/comparison_conformance.py
```

This command executes the models and reads the retained isolated evidence. It does not run restic, create snapshots, alter repository contents, or collect new native observations. The private originals and copied fixture repositories are required for its ownership and restoration checks; public receipts alone do not replace them. Ordinary CI continues to check pure rules rather than rerun application collection.
