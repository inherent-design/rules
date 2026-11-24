# restic snapshot filters and retention groups

“Latest” and “keep one” need a selection scope. This band compares six generated snapshots in a private local restic 0.20.0 repository. Hosts, source paths, tags, and timestamps vary deliberately. It preserves the difference between inspecting selected snapshots, previewing a retention policy, removing references, and reclaiming data.

## Native evidence

The [original receipt](../evidence/restic-selection-20261124T061409701179Z/receipt.json) covers 21 commands: initialization, six backups, queries, and retention previews. The exact [snapshots](../evidence/restic-selection-20261124T061409701179Z/snapshots.json), [cases](../evidence/restic-selection-20261124T061409701179Z/cases.json), [trace](../evidence/restic-selection-20261124T061409701179Z/trace.json), and streams retain their input identities and outcomes. The [collector](selection_probe.py) uses the publisher-checksummed Mac arm64 binary, private credentials/config/cache, generated text, and a new local repository.

A separately attributed [follow-up receipt](../evidence/restic-selection-20261124T061409701179Z/latest-selector/receipt.json) adds one read-only `snapshots latest` command against that completed fixture. Its [collector](latest_probe.py), streams, and hashes do not replace the original 21-command receipt. There were 22 native commands in total. Password values and encrypted repository contents remain in ignored work, about 196 KiB; no personal repository or remote backend was opened.

The fixture's timestamps are unique and ordered S1 through S6:

| Snapshot | Host | Source path | Tags |
| --- | --- | --- | --- |
| S1 | alpha | A | stable |
| S2 | alpha | A | canary |
| S3 | beta | A | stable |
| S4 | alpha | B | stable |
| S5 | alpha | A | stable |
| S6 | alpha | A | stable, review |

The native commands returned these selections:

| Request | Selected or retained snapshots |
| --- | --- |
| `snapshots --host alpha` | S1, S2, S4, S5, S6 |
| `snapshots --path A` | S1, S2, S3, S5, S6 |
| `snapshots --tag stable,review` | S6; tags within one argument use AND. |
| `snapshots --tag canary --tag review` | S2, S6; repeated tag arguments use OR. |
| `snapshots --host missing-fixture` | Empty list; exit 0. |
| `snapshots --latest 1 --group-by host,paths` | S3, S4, S6 |
| `snapshots --latest 1 --group-by ''` | S3, S4, S6; the inspection fallback still selects per host/path. |
| `snapshots latest` | S6 |
| `forget --keep-last 1 --dry-run` | Keep S3, S4, S6; three default host/path groups. |
| `forget --keep-last 1 --group-by '' --dry-run` | Keep S6; one global group. |
| `forget --keep-last 1 --group-by host,paths,tags --dry-run` | Keep S2, S3, S4, S5, S6; tag sets split the groups. |
| `forget --keep-last 1 --keep-tag canary --dry-run` | Keep S2, S3, S4, S6; matching tags are a union with the latest-per-group rule. |

A denotes the exact absolute fixture path in the receipt, not a literal relative-path command tested here. The original case named `latest-global` records the empty grouping argument; its name was a request label, not evidence of global behavior. The output and report preserve the contrary result.

Every query and preview leaves the captured snapshot-reference and encrypted-pack identities unchanged. Preview `remove` arrays describe proposed removal, not an applied deletion. Locks, cache, logs, and unrelated repository internals are outside that unchanged-state claim. This band performs no policy deletion or prune; the earlier [reference-removal/prune study](README.md) owns those separate observations.

## Source and models

The [source ledger](../sources/restic-selection-selections.json) pins revision `9c88ff768f10c192dc6a87619a65a16374080e33`. Snapshot matching combines host, path, and tag conditions. Host alternatives use OR, required paths use AND, and tag lists use OR between lists and AND inside each list. The special empty-string selector for untagged snapshots remains outside this fixture.

`GroupSnapshots` builds keys from the selected host/path/tag dimensions and sorts paths/tags for the key. `forget` defaults to host/path groups and applies its policy independently to each. An explicitly empty grouping creates one global group. The newest-first policy pass evaluates keep-tag and keep-last conditions as a union.

The `snapshots` command has a separate fallback: without display grouping, its `--latest` helper still partitions by host and paths. The explicit `latest` snapshot selector instead finds one newest matching snapshot. This is visible in source and the native outputs, and is consistent with the existing `--latest` help wording. It is not reported as a restic defect.

[Lean](Selection.lean) models snapshot identity, metadata, canonical group keys, filters, latest-per-group decisions, and keep/remove preview sets. Seven laws cover scope, input membership, tag preservation, and disjoint/complete preview dispositions. Unique timestamps and keep-last-one are explicit premises. [Bend](Selection.bend) checks four decision laws and consumes independently checked key/order/filter facts; it does not implement the JSON decoder, canonicalization, or full grouping algorithm.

The [replay](selection_conformance.py) compares 13 native selections/previews with Lean and 36 filter, 252 newer-in-group, and 42 keep decisions with Bend. It checks native group keys, exact IDs, timestamp order, streams, producer/source hashes, and scoped before/after state. The research input decoder refuses unknown schema, grouping, operation, empty-tag semantics, and tied timestamps rather than interpreting an unsupported projection. This is not a claim that restic refuses those supported cases. Comparisons use selected membership and group identity, not presentation order.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/restic/selection_conformance.py applications/evidence/restic-selection-20261124T061409701179Z
```

Compile the formal modules first with the pinned toolchain. Replay starts no restic process. Fresh collection is an owner-run procedure outside ordinary CI; do not point it at personal or remote repositories.

## Decisions and UX proposals

Preserve default host/path retention grouping: it protects independent backup sets from a global quota. Preserve explicit global grouping and the richer tag grouping when the operator requests them. Do not flatten inspection and retention into one universal “latest” policy merely because some flags have the same spelling.

An inspection or retention summary can make the effective scope explicit: “Latest per host and path” versus “Keep one across the selected snapshots.” Existing help already communicates part of this distinction, so the keep-current alternative is credible. A focused documentation example linking `snapshots latest`, per-group inspection, and a dry-run retention preview may provide enough clarity without a new command.

Keep the machine result's group keys, selected IDs, keep/remove sets, and reasons. Any additive receipt should identify preview versus apply and separately report reference removal and pruning. Avoid silently changing current defaults, JSON fields, saved repository format, or error classification. Test downstream parsers before changing presentation.

For empack and other project managers, the useful comparison is explicit scope and policy provenance, not importing backup retention semantics. A count without its project/profile/channel/group can imply the wrong effect. Reports should derive selected scope and confirmed outcomes from the actual operation, while retaining uncertainty and the original domain meaning.

Before adoption, verify multiple paths and tag permutations, untagged filters, equal/future timestamps, other retention counts/calendar buckets, filtered and partial groups, failed removals, concurrent changes, locks, and remote backend outcomes. Snapshot metadata selection does not prove content integrity or restoration. No production restic or empack changes are selected by this band.
