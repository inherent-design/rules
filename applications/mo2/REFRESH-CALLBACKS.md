# MO2: callback delivery and future registrations

The selected MO2 v2.5.2 callback API can accept a forced future registration during delivery and then disconnect it as part of the current batch's cleanup. This record executes the registration body and three completion statements with real Boost on macOS. It is a source-fragment counterexample, not a supported Windows MO2 or full refresh workflow.

## Source and executed boundary

The selected source is `9c130cbf2fc7225fb2916e46419af50671772aa0`. `onNextRefresh` connects while a directory update is active or the caller forces waiting; otherwise it invokes the callback immediately. The header describes the forced mode as waiting for the next refresh when none is running. Callback groups are ordered core, internal, and external.

`onDirectoryRefreshed` sets `m_DirectoryUpdate` false, invokes the live callback signal, and disconnects all its slots. The [collector](refresh_callbacks_probe.py) extracts the unchanged registration body and those three statements. Its [driver](refresh_callbacks_driver.cpp) supplies the signal, flag, closed callbacks, and observations. It omits directory building/swapping, logging, Qt, list refresh, UI readiness, and game/VFS work. The [source header](https://github.com/ModOrganizer2/modorganizer/blob/9c130cbf2fc7225fb2916e46419af50671772aa0/src/organizercore.h) and selected C++ file remain separately pinned.

The [qualifying capture](../evidence/mo2-refresh-callbacks-20261126T101529108336Z/receipt.json) records one compilation and one observation process. Both groups retired. Boost 1.92.0 headers, the actual compiler invocation and resolved binary, SDK, generated source/binary, and 1,693 compiler dependencies are identified. Dependency hashes are post-run readbacks, not a reproducible build or supported MO2 dependency claim. The generated source and binary remain in an owned private fixture; no personal profile or desktop was accessed.

The [earlier linker-only failure](../evidence/mo2-refresh-callbacks-20261126T101407822977Z/disposition.json) is excluded. Resolving `clang++` to its `clang` target changed the driver's invocation spelling and omitted C++ runtime linkage. The corrected producer preserves the invocation path and records resolved identity separately. No method ran in the failed attempt, and it is not an MO2 failure.

## Observed traces

Each scenario has an initial snapshot and two explicit calls to the selected completion block. Those calls do not establish that a real directory worker or Qt refresh completed.

| Scenario | Current source fragment | Detached-batch research alternative |
| --- | --- | --- |
| One queued callback | Runs once; connection discharged. | Same. |
| Immediate registration while idle | Runs during registration; nothing queued. | Same. |
| Callback 1 registers forced future callback 2 | First drain runs 1, then disconnects 2. The next drain cannot run 2. | First drain leaves 2 connected; next drain runs it once. |
| Callback 1 registers immediate callback 2 | Runs 1 then 2 during the first drain. | Same. |
| External/core/internal registration order | Executes core/internal/external order. | Same. |

The [raw output](../evidence/mo2-refresh-callbacks-20261126T101529108336Z/observe.stdout) measures event order, connection state, and pending count. In the forced reentrant case, the current fragment's child connection is already disconnected after the first drain. This is not merely an absent log or an unobserved later job.

The alternative swaps the old signal into a local batch before invoking it. Registrations made through `onNextRefresh` then belong to the live pending signal; destroying the delivered batch leaves those registrations intact. It executes in the same research adapter and Boost installation. It is not a patched MO2 build or general exception/concurrency-safe implementation.

## Model fidelity

[Lean](RefreshCallbacks.lean) predicts request registration, stable group ordering, immediate leaf actions, emission snapshots, current global cleanup, and detached-batch ownership. [Bend](RefreshCallbacks.bend) independently executes that projection. Eleven Lean laws and nine Bend laws retain one-shot behavior, immediate policy, current lost registration, candidate retention, and next-drain execution.

The model input comes from the frozen driver's controlled requests, not from its emitted traces. Both models match ten source/alternative records and all thirty before/first/second snapshots. Unique tokens name controlled registrations, not arbitrary function identity. Inputs admit one level of child registration, successful allocations, single-threaded delivery, and callbacks that do not throw, cancel, disconnect others, or invoke nested completion. These are explicit scope premises, not guards enforced on arbitrary MO2 plugins.

The [pure comparison](refresh_callbacks_conformance.py) reads retained records and executes only Lean/Bend. Ten decoder refusals and four changed-observation controls pass for their intended reasons. `--public-only` excludes current source-cut reconstruction, private generated/binary readback, and compiler/header dependency checks. Public and owner-local comparison results agree apart from those explicit exclusions. No C++ compiler, Qt, MO2, or game is run by replay.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> \
  python3 applications/mo2/refresh_callbacks_conformance.py --public-only
```

## API and compatibility decision

Cleanup should retire the delivered batch rather than registrations accepted for future work. Reuse the existing registration modes, group ordering, and connection handles; another scheduler is unnecessary for that invariant. Keep the immediate path and ordinary one-shot completion. The existing profile/catalog/environment readiness predicates remain separate: delivering a callback does not establish a matching effective view, saved profile, installed VFS, or retired process.

Before adopting a batch change, qualify throwing callbacks, disconnect/cancel operations, nested delivery, object destruction, cross-thread registration, connection lifetime, supported Boost/Windows dependencies, and real caller reachability. Swapping a batch can change which uncalled callbacks survive an exception; the passing no-throw fixture does not resolve that policy. Do not promise that a later ready signal establishes all work requested by reentrant callbacks.

The source-compatible keep-current option requires a caller restriction against forced future registration during delivery, explicitly documented and enforced where relevant. No such restriction was established in this study. Whether existing application/plugin workflows reach the counterexample remains open; preserve that distinction when describing the issue.
