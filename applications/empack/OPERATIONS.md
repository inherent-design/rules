# Empack operation ownership, observations, and terminal results

The current runtime already separates operation ownership, observer delivery, worker retirement, retained results, and admitted publication receipts. This band exercises selected current-source paths, including a real blocking file owner. It also finds two narrower reporting issues: progress callbacks can update their observation cell after terminal completion, and a returned driver error replaces a simultaneous retirement error in the structured result.

The [source ledger](../sources/empack-operation-selections.json) pins empack `0b4462e3032b4f09230b15329722eabefb7f574c`. The fixture compiles the unchanged `engine/runtime.rs` and `engine/resources.rs`, plus unchanged `Interrupted` and `Cancellation` blocks, with a clearly identified study driver. It reuses cached dependencies with matching Rust 1.99.1. This is native execution of selected source modules, not a product build or an installed CLI/Engine test. No project, cache, durable operation store, runtime process adapter, publisher, or user file is opened.

The [native collection](../evidence/empack-operations-20261125T090212235915Z/observed.json) retains 24 snapshots from a 0.304-second execution. It uses two Tokio runtime threads and explicit worker gates. A [closure record](../evidence/empack-operations-20261125T090212235915Z/closure.json) verifies that the original process group is absent, no command references the private workspace, and its four-byte file remains intact. Private source/binary data occupy about 7 MiB. There is no live collector or desktop lease.

An [earlier compile-only attempt](../evidence/empack-operations-20261125T090143715136Z/unrun.json) used Rust 1.92 with dependencies built by 1.99.1. Its E0514 diagnostics and producer remain intact; no native case ran. The second capture uses the already installed matching compiler and does not rebuild dependencies. Direct compiler/dependency hashes are retained, but subordinate compiler and reproducible dependency-build provenance remain unproved. The quoted cancellation blocks retain their [Apache 2.0 license](../sources/licenses/empack-Apache-2.0.txt).

## Current ownership and lifecycle

| Boundary | Evidence in this band | Consequence for callers |
| --- | --- | --- |
| Started versus observed handle | Dropping an observed handle leaves cancellation false; dropping the original handle requests cancellation | The same Rust handle type has different destructor behavior depending on how it was obtained |
| Observation versus control | Source shows that both kinds expose explicit `cancel()` | An observed handle is not a read-only capability; only its drop behavior differs |
| Retirement barrier | A blocked file owner keeps its job/resource reservation and registry slot while phase is `Retiring`; releasing the gate permits terminal cancellation | A disconnected caller cannot reclaim the worker's reservation or evict the active entry |
| Result retention | A late observer obtains the same result Arc; explicit registry release removes lookup but an existing observer still reads that Arc | Registry membership and result lifetime are separate; terminal results consume capacity until release |
| Attempt acceptance | An old ordinary result is refused and its retained allowance is released | Freshness is an owner-side acceptance check, not an advisory worker claim |
| Admitted receipt collection | The owner collects a result after cancellation and attempt change through `accept_publication()` | This specialized collection preserves admitted effects; it is not public authority to bypass publication checks |
| Shutdown | Two concurrent shutdown callers remain pending behind the same blocked worker; new starts are closed | Closing admission is earlier than completed retirement |

The runtime stores the terminal result before notifying status watchers. `wait()` inspects retained status before waiting for a change, so a missed/coalesced notification does not lose the result. The native late-observer case verifies the same retained Arc before and after explicit registry release. This is process-local retention, not a persisted journal, crash-recovery claim, or permission to evict recovery data.

The real file-owner control writes `data`, syncs, and holds the open file behind a gate. During retirement, all four resource dimensions remain reserved, a new reservation is busy, a new operation hits the one-entry registry limit, and `release_completed()` refuses. After the gate opens, the file is reread by its owner, the worker exits, reservations return to zero, and terminal cancellation is observed. This joins caller drop, monitor ownership, resource lifetime, and file effects. It does not qualify arbitrary native descendants or cancellation of an uncooperative external executable.

Retained output has a separate allowance after a worker releases its job slot. The acceptance control observes `[0, 8, 4, 1]` for jobs, estimated memory, scratch, and files, then zero after rejecting a stale result. A later receipt keeps its allowance until its actual output owner drops. These are configured estimates and ownership accounting, not measured RAM or filesystem quotas. General admission fairness, all dimensions/limits, transfer errors, and actual adapter byte enforcement remain outside this band.

## Cancellation, ordinary results, and admitted receipts

`WorkScope.accept()` checks the acceptance gate, child cancellation, operation identity, attempt, and owning scope. `accept_publication()` and `accept_retirement()` instead require the matching operation and owning scope. Their narrower gate is deliberate: after an authoritative owner admitted publication or runtime retirement, cancellation must not erase the resulting receipt.

The native driver verifies ordinary stale-result refusal, retained allowance release, refusal after cancellation, and collection of an owner-bound value `42` through the specialized receipt path. That value is a controlled worker result, not evidence that a distribution was durably published or a game process retired. The surrounding Engine/publisher/runtime adapter must establish those meanings before invoking these owner-only methods.

The shutdown control observes both spawned shutdown tasks unfinished before releasing the worker, then joins both. It does not instrument the exact instruction each task had reached.

Closing a preparation's child scope cancels its workers without cancelling the parent operation token. Both that control and the shutdown control can still finish successfully: a cancellation request does not independently replace an actual driver result. Preserve the existing child/parent distinction and current result-first handling.

## Progress is a latest observation, not an ordered event stream

`report_progress()` and `progress_reporter()` write a separate mutex cell. Two writes before a read expose the latest observation, not both events. Neither write sends a status-watch notification. An escaped reporter holds that cell independently of the scope gate and result registry.

The native control first reads `SavingCachedContent`, then completes with value `5`. A late callback changes progress to `PublishingChanges` while phase and retained outcome remain terminal. The status subscriber reports no change. After registry release, another callback changes the existing handle's progress to `RevalidatingInputs`; its same terminal result remains intact.

This does not turn progress into write authority or alter completed effects. The current CLI checks its terminal result before another progress tick, then drops its display; the inspected source does not establish a current CLI regression. An SDK or future UI that presents progress without checking terminal state can nevertheless display misleading late work.

The smallest preservation rule is to document last-value/coalesced progress and stop presenting it after terminal completion. The [proposed presentation guard](Operations.lean) models that rule separately from current writes. A richer future observation can carry operation, attempt, sequence, and phase basis if a caller needs to reject older-attempt progress. That extension needs actual observer use cases and compatibility review; this fixture does not justify a new event bus or scheduler.

## Structured failure priority loses a secondary fault

The current supervisor joins its driver and all retained worker monitors. Its result selection gives a returned driver error priority over a retirement error. The controlled matrix is:

| Driver outcome | Worker retirement outcome | Structured operation result |
| --- | --- | --- |
| Success | Panicked | Panicked |
| Cancelled | Panicked | Cancelled |
| Panicked | Panicked | Panicked |

Each worker panic is independently observed through its WorkHandle before the driver returns. All reservations reach zero, so this is not an observed detached-worker or resource leak. The panic hook still prints the worker fault to stderr. The loss is specifically that the structured `OperationOutcome` retains only `Cancelled` in the middle row.

Preserve both facts for embedders that need a complete terminal explanation. One candidate is an additive result carrier with the existing primary outcome plus separately attributed driver and retirement diagnostics. Keep completed/partial/publication receipts authoritative and do not infer uncertain effects merely from a joined Rust-task panic. The [proposed carrier projection](Operations.lean) preserves the existing headline while retaining both inputs; it is not a selected Rust API or serialized format.

The keep-current alternative is reasonable if priority is an intentional documented contract and callers retain another reliable fault channel. Stderr alone is weak for structured embedders. Before implementation, review every OperationOutcome/RuntimeError caller, retained error wrapper, exit classifier, and source-chain renderer. Test driver failure plus worker failure, publication receipts plus cleanup failure, cancellation races, panic-hook suppression, retained values after registry release, and actual Engine/CLI presentation. No new release-blocking CLI or durable-state defect is claimed from this selected-module fixture.

## Interface direction and compatibility

Keep OperationRuntime's bounded registry, independent worker monitors, explicit result release, weakly bound work tokens, and driver-only receipt collection. A future API could distinguish a cancelling owner from a result subscription more clearly. A separate read-only observer type would be a capability/API change: today's observed handles can explicitly cancel, so renaming alone cannot establish that restriction. Existing callers must choose whether to retain control rather than silently losing it.

A staged compatibility option is to preserve `OperationOutcome<T>` and its existing headline behavior, then expose immutable terminal diagnostics through a new handle accessor. `OperationHandle` already has private fields, so it can retain a sidecar without adding a variant to the public exhaustive outcome/error enums or a field to the publicly constructible status struct. Publish the sidecar before terminal notification, bind it to the exact operation/result, and retain it through existing observers after registry release. Review memory/resource ownership and every failure branch before selecting this design.

A new read-only subscription API could coexist with today's controlling `observe()` handle. Keep existing methods and destructor behavior for compatibility; callers deliberately choose a restricted subscription instead of losing cancellation silently. A future incompatible API can consolidate these types after that review. The in-process type split does not itself authenticate an external principal.

No persisted operation schema is changed by these proposals: this registry is process-local, and its opaque OperationId is not a durable recovery identity. No serialized event transport was qualified here. Any future transport needs its own version, identity, capability, and retained-result contract; it does not require an on-disk migration framework for this study.

For empack's portable-authoring candidate, bind background results and progress to their actual captured operation/image basis, and preserve terminal facts through view closure. A closed editor or disconnected event listener must not claim to have retired native work. Browser workers and native process adapters retain their own host evidence requirements. These are proposed integration rules, not adoption of a shared engine or permission to treat a model token as a native capability.

## Verification and remaining scope

The [29-file basis](operation-basis.json) fixes the retained evidence and research adapter identities. The [observer](operation_observations.py) checks the frozen producer, generated source, unchanged module bytes, selected Git objects, compiler/dependency/binary hashes, raw/public trace correspondence, panic diagnostics, private file, and closure records. The [Lean](Operations.lean) and [Bend](Operations.bend) models compare 19 measured projections over the 24 snapshots, two source-only owner refusals, and five proposed carrier/presentation cases. The pending-worker count is an admitted one-worker fixture/source fact; it is not derived from arbitrary resource totals. Initial running state and explicit gates are projection premises.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/empack/operation_conformance.py
```

The [verification record](operation-verification.json) retains 18 Lean laws, 12 Bend laws, eight decoder refusals, seven changed premises, and seven changed raw observations. Replay starts no Rust compiler, application, or operation worker; it reads retained artifacts and invokes the model tools. The native compiler failure remains a separate excluded acquisition record.

Preparation/request decoding, plan grants, ephemeral preparations, Engine start/observe/shutdown, full CLI rendering and exit status, engine destruction without awaited shutdown, every reservation/failure dimension, arbitrary attempts/owner interleavings, foreign real tokens, progress across attempt changes, other platforms, process trees, durable effects, and real crash recovery remain unqualified. The feature and joined scenario retain their pending parent statuses. No product code, deferred UX implementation, or live operation store was changed.
