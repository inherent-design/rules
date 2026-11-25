# VS Code task execution and readiness

A task handle, discovery result, process event, readiness signal, stop request, and retired child establish different facts. This band exercises selected task extension APIs in the installed VS Code 1.147.0 desktop build, then compares their observed execution lists with the [Lean](Tasks.lean) and [Bend](Tasks.bend) projections. It does not qualify the entire task engine, terminal UI, or browser execution.

The [source ledger](../sources/vscode-task-selections.json) pins `8a14f0cc1b08d531eb83255ea3764ae22aa932b5`. It separates API declarations, Node and worker extension-host admission, task discovery, terminal events, and watching-background dependencies. Source checks are not a proof that this installed executable was compiled from those files.

## Native observations and preserved failure

The [original collection](../evidence/vscode-tasks-20261125T083319891600Z/observed.json) retains 12 observations from an 8.711-second run. Discovery returned no provider tasks with `task.autoDetect: off`; a newly created task without execution was refused; a custom pseudoterminal started and reported exit `7`. The collector then passed an absent fetched task to `executeTask()`, causing a TypeError. That final error is a fixture mistake, not a product defect. The original producer, trace, error, and normal app exit remain intact.

The separate [continuation](../evidence/vscode-tasks-continuation-20261125T084118001187Z/observed.json) retains 46 observations from a 34.834-second run. With the same provider registered, discovery was initially empty, then returned its task after the fixture changed detection to `on`. The source's `_isProvideTasksEnabled()` requires that setting. This is a controlled setting change, not evidence of a discovery race or a requirement to add arbitrary delays.

Both runs use disposable workspaces, extension directories, and user-data, ordinary OS home, and in-memory secret storage. Shared OS startup effects remain unmeasured. No personal profile, credential, game, or document was selected. Independent disposition records establish absent app groups and private-workspace process matches after exit; the continuation also checks all four actual positive child PIDs. Desktop access was released and unsubscribed. The continuation profile occupies about 20 MiB, with small frozen producers and logs retained; no app build or download was needed.

| Boundary | Native result | Remaining obligation |
| --- | --- | --- |
| Discovery and provider disposal | Detection off gives no task; on gives one; disposal removes discovery while its task remains active | General provider activation, timeouts, multiple providers, and concurrent disposal |
| Handle and task events | `executeTask()` returns a visible execution before its task-start event; process-end leaves it visible until task-end | General event interleavings, launch/RPC failures, restarts, and repeat identities |
| Custom execution | PTY reports result `7`; process events carry virtual PID `-1` | General custom-provider lifecycle, remote/browser execution, and real provider-owned child retirement |
| Process execution | Separate literal space, Unicode, and `$RULES_LITERAL` arguments arrive unchanged; child result `7` reaches API | Shell execution, arbitrary encodings/environments, Windows/Linux, and descendant trees |
| Stop request | `terminate()` returns before task-end; API exit status is absent after stop, while the child journal reports SIGHUP and exit `11` | All interruption paths, grace periods, grandchildren, and general signal/status translation |
| Background readiness | A configured dependent finishes with result `0` while its readiness-signaling background task is still active | Full matcher/diagnostic semantics, inputs, failure cycles, and parallel scheduling |

## Preserve task identity without inventing process authority

The source allocates an execution before dispatching the run. A returned handle therefore establishes a registered execution, not successful startup or completion. The API's active list retains that identity during the process-end callback and removes it for task-end. The native background dependency introduces another execution without a caller `executeTask()` return for that child; a consumer must also observe task-start events.

The custom PTY produces process-start and process-end events even though it has no OS process in this fixture. `ExtensionTerminalProcess.startSendingEvents()` explicitly emits PID `-1`, and the main task adapter forwards terminal process events. The declaration's description of tasks without an underlying process does not explain this virtual event path. That is a bounded documentation/consumer-contract gap. It is not evidence of a stray process or a general task-runtime failure.

Never pass an event PID directly to an OS signal operation. The proposed consumer guard rejects nonpositive PIDs and additionally requires an independently established ownership binding. A positive number alone is insufficient. The guard is a study proposal; it is not a change to VS Code's own termination implementation.

## Stop acceptance and owned-work retirement are separate

`TaskExecution.terminate()` returns `void`. In the continuation, the execution is still active when that call returns. After task-end, the custom provider's deliberately retained `workerAlive` Boolean is still true until its explicit cleanup callback. This is a controlled provider-responsibility negative: it is not a probe showing that a real worker leaked. The fixture sets and clears that Boolean itself.

The actual Python child journals supply independent evidence for the two process stops: each received SIGHUP and recorded exit `11`. Their task process-end callbacks instead carry an absent status. Keep unknown/absent API status distinct from numeric success and from the child journal's status. The observer checks all three sources separately; it does not fill absent API results from an assumed exit code.

## Readiness permits progress without producer exit

The background task emits `BEGIN`, waits for the fixture's explicit gate, then emits `READY`. The configured watching matcher becomes inactive, allowing the dependent task to run while the background task remains active. The source races dependency inactivity against execution completion. The native API does not directly expose that matcher-inactivity callback; its role is source-inferred from the fixed matcher, gate, child journal, and observed dependent execution.

A useful interface should retain “running and ready” as a state, rather than conflating readiness with completion. Stopping a dependent must not silently imply that every background dependency has retired. Keep task, terminal, provider-owned resource, and actual native-child ownership separate.

## Extension host capability matters more than window type

The selected Node extension-host source allows ProcessExecution, ShellExecution, and CustomExecution under later validation. It can also resolve a preserved task handle without an attached execution. The worker extension host accepts CustomExecution only and rejects a missing execution even with a preserved handle. A web window can use a remote Node host, so “web” alone is not the capability decision.

The sixteen admission rows in the replay are source-selected policy projections, not native worker/browser runs. Other DTO, task definition, workspace, trust, and task-system checks remain premises. Native execution here covers a local desktop Node host only. The fixture never calls the provider's `resolveTask()` path; discovery plus execution of an already supplied task does not qualify that operation.

## Verification and interface direction

Run the retained comparison with the pinned tools:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/vscode/task_conformance.py
```

The [35-file basis](task-basis.json) preserves the original records and research adapter identities. The [observer](task_observations.py) checks both frozen producers, source hashes, traces, task definitions, child identities, arguments, statuses, and closure records. The [verification record](task-verification.json) separates two native trace comparisons covering 58 snapshots, three native discovery comparisons, sixteen source admission cases, sixteen source dependency projections, and six proposed signal guards. Fifteen Lean laws and eleven Bend laws state the bounded model's properties. Nine decoder refusals, six changed premises, and six changed raw observations protect the comparison. Replay launches no application or child process.

The first pure replay needed explicit JSON defaults for the Lean decoder; the Bend projection needed affine-use annotations and a structurally decreasing argument order. A readiness negative control was corrected to keep process completion false, so changing readiness could affect its result. These were research adapter corrections, not changes to native observations. The failed native collector remains visible separately.

Preserve the existing task identities, start/end events, provider capabilities, and readiness support. For automation, document the handle/start/result distinction and virtual process events before inventing a new task scheduler. A richer receipt could distinguish a requested stop, terminal result, and verified owned-child retirement when a provider can supply those facts. It must leave unknown results unknown and support custom providers without pretending that every task has an OS process.

No production implementation, public API change, or empack adoption is selected. Full UI, accessibility, browser/remote task execution, configured unresolved task resolution, general shell quoting, task inputs, matcher diagnostics, dependency failures, persistence/reconnect, hostile providers, concurrent cancellation, and full descendant retirement remain pending.
