# Reload preparation, application, and failure

An aggregate reload future reports the selected listener operation. It is not a receipt for every listener's retirement, rollback, resource validity, or renderer completion. Across five original Minecraft clients, a preparation failure can complete that aggregate exceptionally while another listener future is pending; an application failure can retain an earlier authored effect. An empty listener set can finish while the initial gate is still pending. These qualify specific orchestration boundaries, not a full resource reload or product defect.

## Versioned interfaces and source consumers

[reload-sources.json](reload-sources.json) binds 64 original/named class pairings and 40 private decompiler views across the five selected Java releases. It covers listener interfaces, simple/profiled orchestrators, and reloadable/multiple-pack managers. Original bytecode and decompiler views stay private; source locators are not runtime observations or verified translations.

| Selected interface | Relevant contract |
| --- | --- |
| 1.21.1 | Listener reload receives a preparation barrier, resource manager, two profiler arguments, and preparation/application executors. |
| 1.21.4 and 1.21.5 | The selected listener reload has four arguments: barrier, manager, and two executors. |
| 1.21.11 and 26.3 | Reload receives shared state, task executor, barrier, and reload executor. The orchestrator calls every listener's `prepareSharedState` before invoking listener reloads. |

These are exact selected interfaces, not claims about the first introduction date or arbitrary later releases. The collector resolves their signatures through the official mappings where needed. The two shared-hook scenarios are explicitly skipped for the three older selected interfaces; no successful or failing runtime hook call is fabricated there.

The selected orchestrator invokes listener reloads and chains application barriers through the previous listener future. A listener must participate in its supplied preparation barrier to obtain that ordering. The fixture deliberately bypasses one barrier as an admitted interface-level control; it does not establish that a normal vanilla listener does so.

In every selected `ReloadableResourceManager.createReload` view, the method calls close on its current manager, assigns a new multiple-pack manager, then calls the reload factory. Those are inspected calls and assignments. Resource validity, close failures, retained old views, asynchronous consumers, caller fallback, and renderer/device retirement remain separate obligations. This method was not executed by the fixture. A source-level assignment before future completion is not a complete global publication or recovery protocol.

## Original orchestration with controlled listeners

[ReloadProbe.java](ReloadProbe.java) calls the original factory, barriers, and `ReloadInstance.done` through recorded bindings. Authored dynamic proxies implement listeners and an inert resource-manager interface. Manual futures supply preparation/initial gates; direct executors run callbacks synchronously. No resource-manager method, pack loader, real IO worker, game, GUI, or renderer is invoked by the authored plan. Incidental JVM/library effects are not exhaustively measured.

The input [case plan](reload-cases.json) contains requested completions and listener behavior, not expected results. Each private collection freezes that plan, the actual profile flag, observer and collector sources, original classes, JDK, libraries, commands, and raw channels. The public receipts bind loaded original classes and preserve the authored observation bytes. The first four clients use the recorded Temurin 21/macOS arm64 environment; 26.3 uses the recorded Temurin 25/macOS arm64 environment. The observer compiles for Java 21, so it adds no Java 17 native-runtime qualification.

| Client | Executed controlled cases | Captured snapshots |
| --- | --- | --- |
| 1.21.1 | Six; two interface-hook scenarios skipped | [20](evidence/reload-native-1.21.1-20261125T171404982601Z/observed.json) |
| 1.21.4 | Six; two interface-hook scenarios skipped | [20](evidence/reload-native-1.21.4-20261125T171406555515Z/observed.json) |
| 1.21.5 | Six; two interface-hook scenarios skipped | [20](evidence/reload-native-1.21.5-20261125T171408073404Z/observed.json) |
| 1.21.11 | Eight | [24](evidence/reload-native-1.21.11-20261125T171409740934Z/observed.json) |
| 26.3 | Eight | [24](evidence/reload-native-26.3-20261125T171347033489Z/observed.json) |

There are **34 executed cases, six profile-hook skips, and 108 snapshots**. These are not counts of every Java call. All ten compiler/observer command groups returned zero and were absent afterward. Pending futures are heap objects in the controlled fixture, not evidence of a running physical worker or leaked external resource.

| Controlled journey | Original result | Boundary preserved |
| --- | --- | --- |
| Prepare listener 1 before 0, with initial gate pending | No application until both preparations arrive and the initial gate succeeds; effects then occur in listener order 0, 1. | Preparation order, application dependency, and initial readiness differ. |
| Fail listener 0 preparation | Overall future fails while listener 1's future remains pending, including after its own preparation succeeds. | Fail-fast summary is not a peer join or cancellation receipt. |
| Fail listener 0 application after its recorded effect | Overall and both listener futures fail; the first effect remains, and listener 1 does not apply. | Exceptional completion does not undo prior effects. Effects here are authored callback-log appends, not asset writes. |
| Fail the initial gate before preparations arrive | Overall remains pending until the preparation barrier can propagate the failure. | An upstream failure need not immediately complete every dependent future. |
| Let listener 0 bypass its barrier | Its effect occurs while the initial gate is pending; listener 1 remains pending after later completions. | Barrier participation is a caller obligation. This is not a reproduced vanilla-listener defect or an elapsed-time liveness proof. |
| Select no listeners | Overall succeeds while the initial gate is pending. | Selected-listener completion does not imply all unrelated work has completed. |
| Invoke newer shared hooks | Both hooks see the same context object before either listener reload is invoked. | Context sharing and listener application are separate stages; context values and consumer correctness are not qualified. |
| Throw from the second newer shared hook | Factory throws synchronously; neither listener reload is invoked and no aggregate future is returned. | Factory failure differs from a returned exceptional future. Earlier shared hooks already ran; no global zero-effect claim follows. |

## Models, projection, and controls

[ReloadSchedule.lean](ReloadSchedule.lean) has 14 laws, including general empty-set and barrier-bypass properties plus explicit selected counterexamples. [ReloadSchedule.bend](ReloadSchedule.bend) has eight kernel-checked laws and a separately implemented decision function. The [research decoder](ReloadScheduleCase.lean) distinguishes pending, successful, failed, and uncreated future slots. It refuses needed unknown evidence and incompatible shared-hook requests; an empty listener set or a known synchronous shared-hook failure does not need unrelated future inputs.

[reload_conformance.py](reload_conformance.py) derives snapshot premises from the frozen request and one-time completion actions, independently of observed future results. Both models match all 108 result vectors. Separate checks retain requested gate states, complete controlled callback traces, barrier arrival order, shared-context identity observations, and invocation/effect membership. Fourteen malformed/unresolved requests and nine altered observations are rejected; three unused-unknown examples remain admissible. [The conformance receipt](evidence/reload-conformance.json) binds the source and data basis.

Both models share the inspected Python request projection. Adapter fidelity, decompiler translation, JVM correctness, and arbitrary listener graphs are not formally proved. The selected profile has zero or two listeners, listener 1 always uses its barrier and never fails application, each gate completes once, profiling is disabled, and execution is direct. Some laws are explicit examples, not universal claims about schedulers or every reload. Placeholder slots for absent listeners mean no listener future was returned in that slot, not a census of every internally allocated future. Future exception causes, progress counters, and physical worker liveness were not captured; the factory error class and selected future completion states were captured separately.

The ordinary proof lane can replay these data after compiling the models:

```sh
python3 host/minecraft/reload_conformance.py
```

The collector and source inspector are separate owner-run procedures. The proof lane must not launch them. Draft Bend quantity/type errors and a relative-path report-serialization error were corrected without recollecting native cases, changing observations, or weakening controls. The first owner-local conformance result is retained privately before public-basis regeneration.

## Host and possible-provider design

The shared host contract already distinguishes a stop request, owned completion, publication conditions, and final reuse. This consumer supplies a concrete reason to keep an aggregate result separate from each relevant operation's completion and retained ownership. It supplies neither a native resource lease nor a physical retirement receipt. There is no new generic scheduler or change to the existing common predicate.

For a possible combined provider, keep preparation, shared-context initialization where supported, barrier arrival, application, externally visible effects, summary outcome, and retirement explicit. Reuse the native listener/barrier path when its contract suffices. If older-host adapters need shared context, define its owner, lifetime, dependencies, and failure effects deliberately; copying a newer method name into the 1.21.1 baseline does not supply that API or missing gameplay state.

Diagnostics should distinguish initialization that threw before returning an operation, returned operations still pending, failed preparation, partial application, and a completed selected listener set. Preserve original failure details and known effects. Do not label an aggregate failure “rolled back,” an empty summary “all resources ready,” or a cancelled future “all workers stopped.” Human and machine reports should use the same stage/outcome facts and identify the affected resource/provider generation where the actual consumer can establish it.

One option is to keep current orchestration and document caller obligations. Another is owner-scoped diagnostics for missing barrier participation and incomplete retirement. Forcing a failed listener's barrier to complete or silently retrying application would change dependency and effect semantics; it is not a safe generic repair. Any transactional preparation/publication design needs actual content, owner, native, and consumer evidence before adoption.

Real concurrent workers, cancellation, interruption, duplicate listeners, arbitrary graphs, profiler paths, resource-manager replacement/close failures, pack fallback and UI, provider coexistence, library/native leases, device work, and renderer retirement remain open. No production modification, pack change, backport, installation, or rollout is selected by this band.
