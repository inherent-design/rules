# restic: retain scoped evidence and acknowledge actual effects

Keep restic's repository model, typed blob handles, operation-specific locks, backup policy, and explicit maintenance commands. The recorded problems concern search completion and output, ambiguous operation acknowledgements, and a source-qualified process probe. They do not justify replacing the backend, encryption, retention engine, or every ID type.

This review uses restic 0.20.0's existing native reports and source `9c88ff768f10c192dc6a87619a65a16374080e33`. It adds source/interface inspection, not another repository fixture or model replay. [Source selections](../sources/restic-architecture-selections.json) distinguish new official-source acquisition, fresh inspection, and reused evidence. Current upstream status and reproducible source-to-binary correspondence remain unreviewed. [Contract records](architecture-targets.json) describe proposed responsibilities and compatibility, not a new implemented SDK or wire schema.

## Current owners and values

| Boundary | Current owner and value | Preserve or change |
| --- | --- | --- |
| Repository and credentials | Backend location, authenticated config, format, master material, and access wrappers | Preserve repository identity versus access method. A wrapper label or current-key marker is not an authorization role. |
| Saved reference and content | `data.Snapshot`, snapshot ID, `Parent`, `Original`, `Tree`, node content, and typed `BlobHandle` | Preserve lineage/provenance versus retaining content. An operation's object role is not supplied by a hash alone. |
| Loading and mutation | `LoaderUnpacked`, generic `SaverUnpacked`/`RemoverUnpacked`, `Repository`, and blob loaders | Reuse existing scoped interfaces. Narrow a risky caller boundary before considering a global ID refactor. |
| Traversal and reports | `Finder`, `WalkVisitor`, `statefulOutput`, diff/statistics reducers, and terminal printer | Preserve selected scope and counting policy; repair incomplete-search status and JSON framing together. |
| Maintenance | Snapshot removal, remaining-root discovery, prune planning, lock admission, and stale removal | Distinguish a plan, each acknowledged effect, and later reclamation. Unknown input or owner evidence is not absence. |
| Restore | `Restorer`, overwrite/filter policy, tracked files, and `VerifyFiles` | Preserve explicit destructive scope and report the actual verification set. |

## Keep typed object roles without rewriting the repository

`Snapshot.Parent`, `Original`, and `Tree` use the same underlying ID type but have different meanings. The selected snapshot loader and saver fix their object-file roles; prune collects remaining snapshots' `Tree` roots rather than following `Parent`. Blob lookup already carries both ID and blob type. The [repository interfaces](https://github.com/restic/restic/blob/9c88ff768f10c192dc6a87619a65a16374080e33/internal/restic/repository.go) also separate several read and write surfaces. These are useful existing boundaries, not a role-free API that needs replacement.

Prefer preserving those interfaces, clearer argument/result names, and tests at role conversions. A narrow tree-root or snapshot-reference wrapper remains an option where it prevents an actual unsafe conversion. No namespace-substitution defect was reproduced. Go type changes would require caller and codec review; they would not themselves authenticate a publisher, prove a complete root set, or authorize deletion.

The earlier wrong-role `cat tree` request remains a collector error: current help already names its snapshot/subfolder input. That control does not justify changing the command.

The [ID codec](https://github.com/restic/restic/blob/9c88ff768f10c192dc6a87619a65a16374080e33/internal/restic/id.go) has explicit string JSON encoding/decoding and full-ID parsing. Preserve that wire representation, optional snapshot fields, and command-specific abbreviated selection. Do not treat a display abbreviation as a universal object selector or replace hex strings with an array representation during a wrapper refactor.

`Repository.LoadRaw` explicitly permits returning data together with an invalid-data error. A returned buffer or parseable document must not silently become verified content while that error remains. Preserve useful diagnostic data and its failure state; a type wrapper alone cannot replace the actual admission result. This is an existing interface contract, not a newly injected corruption case.

Keep object levels distinct. A missing snapshot tree reference cannot establish an empty retained tree; the selected prune caller dereferences that reference and relies on its admission. By contrast, the tree iterator deliberately accepts `nodes: null` as a legacy empty tree and permits unknown keys. A blanket strict-schema change would reject intentionally supported data. These are source/codec constraints, not newly executed malformed-repository or panic cases. Any boundary refinement needs valid/invalid reference tests and legacy codec controls before adoption.

## Search needs a result owner through finalization

The [inspection study](INSPECTION.md) reproduces a pattern search returning zero with human tree-load diagnostics followed by `[]` on JSON stdout. A complete empty result and an unreadable search scope are different outcomes.

The focused owner is `Finder.findInSnapshot` plus its `runFind` caller and `statefulOutput`. Record a tree-read failure independently of intentional traversal pruning. `ErrSkipNode` is also valid policy control for branches that cannot match; treating every skip as incomplete would change legitimate filtering. ID searches have their own early-completion rule and are outside the reproduced pattern-search case.

Changing the read-error callback to return its error immediately is insufficient: `runFind` currently returns on traversal error before `Finish`. After earlier matches have opened a JSON array, that change can bypass closing it. Preserve partial matches and finalization as part of the same correction. Keep diagnostics on stderr, compose the terminal error after collecting the requested traversal outcome, and finish the existing array when the output writer still works. If writing itself fails, report failure and retain output uncertainty; no implementation can promise a complete JSON document through a failed pipe.

The selected `Finish` also discards its write errors. An error-returning finalizer or owned write-error accumulator must account for earlier writes as well; successful final punctuation alone does not verify the preceding stream. Keep that state with `statefulOutput` and its caller rather than infer transport success from traversal completion.

Use the Finder's error/reporting path rather than move every `terminalPrinter.S` call to stderr. Other commands use that method for ordinary output. An opt-in/versioned object can expose completion, affected scopes, and errors; changing the existing array into an object would break consumers. Returning nonzero for incomplete search corrects the false completion but still needs exit-status compatibility review. Keeping the current mixed stdout and false success is not an adequate alternative for that contract.

Before adoption, compare root and nested read failures, multiple snapshots with earlier matches, policy-pruned branches, cancellation, ID-search completion, and failed output writes. The finalization risk is source-supported, not a newly executed truncated-output trace or patched native result. Existing [comparison models](Comparison.lean) ([Bend](Comparison.bend)) retain their original projection and do not prove a streaming writer implementation.

## Count the requested thing and state its limits

The recorded type-change diff omits descendant references under the changed endpoint. A complete-reachability interpretation disagrees with that counter. Preserve the path event list while deciding whether counters mean complete typed closure or only references encountered by event traversal. A focused complete-closure candidate can reuse `collectDir` for directory endpoints; unavailable traversal or weights must remain incomplete. Keep this policy decision distinct from the confirmed search protocol failure.

Statistics likewise have different keys: restored entries, content sequences, location references, and unique typed blobs. The `blobs-per-file` observations and documented rename/reference goals require an explicit counting decision; removing a shared gate is not automatically the right correction. Preserve existing values until that meaning and downstream schema compatibility are settled.

Metadata query success does not establish payload availability, and indexed blob sizes do not establish physical reclaimable allocation. Reuse existing reducers and typed handles; no general query engine or universal size field is needed. A new result should name the selected snapshots, counting policy, read scope, completion, and unavailable measurements without claiming more than was read.

## Snapshot publication, forget, and prune are separate outcomes

Preserve the documented [backup metadata-reuse policy](BACKUP.md). Reused content, newly read content, processed bytes, new stored data, and a saved snapshot are different facts. A partial source capture can save a useful snapshot and return status 3. A dry-run summary can carry a simulated snapshot token without a saved reference. Existing `dry_run`, errors, summary, and status already supply much of this information; a wrapper must not announce a saved backup from `snapshot_id` alone.

This policy is appropriate to its backup contract. It does not establish exact current source bytes for a publisher input or authorize an old prepared write in empack. Retain the operation-specific capture requirement rather than import restic's ignore-metadata flags into another product.

For [forget/prune](POLICY-JOIN.md), retain requested IDs, selected IDs, per-reference removal results, and prune's later outcome separately. The current caller tracks failed removals and skips combined prune after such failures. Its JSON groups describe selection; they must not be reinterpreted as universal per-ID deletion receipts. Explicit-ID removal can be quiet without meaning no effect.

An opt-in receipt can expose confirmed removals, failures, unknown acknowledgements, and whether prune ran. Reuse existing removal callbacks and prune errors. A later failure does not undo earlier acknowledged removals; reference removal does not mean content was reclaimed. Preserve command-specific grouping, keep-rule unions, live tree roots, and exclusive maintenance. Neither a matching hash nor lineage is a replacement for complete root discovery and coordinated mutation. No new repository format or transaction service is selected.

The [copy study](COPY.md) also preserves metadata-sensitive skip policy and persistent copy origin. Origin is provenance used by that command, not authentication or authority in another repository. Name the existing compared metadata projection before changing which snapshots are considered equivalent.

## Owner observation is not retirement or cleanup authority

The [lock study](LOCKS.md) distinguishes publication, admission, refresh, creator observation, retirement, and removal. Preserve compatible appenders, exclusive maintenance, unreadable-record handling, and the separate age policy.

The selected Unix `processExists` sends SIGHUP and maps every signal error to false. A focused candidate would return a nonintrusive observation such as reachable, confirmed absent, denied, or unknown, and let `stale` apply policy. Preserve a nonexpired record on observation failure. This is a source-qualified concern; no permission-denied or PID-reuse incident was executed. An age-expired record follows a separate policy and cannot inherit an unconditional protection claim from that candidate.

Review every platform implementation and caller before changing the Boolean result. A positive PID probe does not by itself establish the same creator across reuse or reboot. Adding lifetime metadata cannot make older clients honor it. Keep encodings compatible unless a separately justified change is selected. A cleanup receipt can describe removed, retained-live, unreadable, or unknown records without promising that a successful unlock leaves no active locks. Do not signal unrelated processes or remove recovery objects to manufacture a case.

## Integrity, restore, keys, and migration keep their own contracts

The [integrity study](INTEGRITY.md) separates structural checks, selected/full data reads, index reconstruction, and content recovery. Repairing an index does not recreate missing payload. Preserve source scope and repair authority instead of adding a generic “healthy” Boolean.

For [restore](RESTORE.md), `VerifyFiles` skips untracked and metadata-only paths; its name does not mean every retained target byte was compared with the snapshot. Report the actual eligible set and existing overwrite policy. An explicit broader verification option would need its own implementation and compatibility decision.

The unexpected-directory deletion case follows a pinned internal test: selecting that parent can remove descendants without independently selecting each child. Preserve this evidence. A leaf-aware, child-preserving alternative changes destructive policy and needs explicit selection, target admission, and race/host qualification. Do not label it a safe string-only change or silently narrow the existing semantics.

The [key study](KEYS.md) preserves separate access wrappers, process-local current-key selection, and master material. A password change can leave another wrapper accepting the former password. Report exact replaced/saved wrapper IDs through existing `Key.ID()` and printers, preserving partial or uncertain effects after failure. No key rotation, revocation guarantee, new authorization model, or cryptographic audit follows from this proposal.

The [repository migration study](REPOSITORY.md) similarly favors per-name requested/applied/skipped/unknown/failed results. An unrecognized name can coexist with an independently applied upgrade. A stricter completion policy remains a compatibility choice; it does not imply preflight rejection or rollback. Preserve encrypted formats, identity, and existing upgrade backup/recovery behavior.

## Staged adoption and remaining checks

1. Correct the demonstrated pattern-search protocol/completion path, including finalization and partial results. Preserve current successful selection and array output.
2. Refine result ownership at existing callbacks for removal, backup, key, and migration operations. Keep additions opt-in/versioned where existing machine schemas or exit contracts would change.
3. Qualify owner-probe and narrow object-role admission at actual callers. Prefer existing interfaces when names/tests provide the needed protection; do not require a repository migration for internal clarity.
4. Resolve counting and destructive-restore policy choices explicitly. Compare current and proposed behavior on the same retained inputs before native implementation, then qualify the previously unobserved faults and hosts.

The full restic and nine-application study remains incomplete. General retention grouping, remote backend consistency, complete codecs/cryptography, interrupted publication, unknown acknowledgements, process identity, all platforms, and candidate implementation retain their obligations. No restic command, private repository, plaintext credential, new formal model/replay, or production patch was used by this synthesis.
