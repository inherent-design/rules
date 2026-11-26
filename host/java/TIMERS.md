# Timer admission, cancellation results, and worker retirement

Canceling a never-scheduled `TimerTask` returns `false` and still prevents that object from being scheduled. The result describes its prior scheduling state, not whether cancellation changed anything. A canceled `Timer` likewise remains a Java object but refuses fresh tasks. Keep timer admission, task admission, cancellation response, and worker retirement separate.

The [Java 17 TimerTask contract](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/TimerTask.html#cancel()) documents task non-reuse and the Boolean result. The [Timer contract](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/Timer.html#cancel()) distinguishes cancellation from an executing task's completion and provides no real-time guarantee. The [Java 25 API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Timer.html) retains that timer contract. The baseline remains Java 17; observations on 21 and 25 are separate overlays.

## Selected observations

The same authored source compiles with `--release 17` and runs on each pinned JDK. It creates two named, non-daemon timers and six task objects, schedules only far-future work, and cancels both timers in `finally`. The [manifest](timer-captures.json) binds 16 events per runtime: 15 admission/cancellation operations and one independent thread-retirement observation.

| JDK | Actual runtime | Evidence |
| --- | --- | --- |
| 17 | 17.0.21.1 | [receipt](evidence/timer-17-20261126T013333429826Z/receipt.json) |
| 21 | 21.0.13.1 | [receipt](evidence/timer-21-20261126T013346687397Z/receipt.json) |
| 25 | 25.0.4.1 | [receipt](evidence/timer-25-20261126T013348428443Z/receipt.json) |

These are macOS/arm64 observations. This cohort did not record the OS build, so it does not inherit one from a neighboring study. JDK executables, release metadata, installed Timer/TimerTask source entries, frozen producers, and compiled helpers are checked by the [owner audit](timer_observations.py); source files and executables are not a proof of the complete JDK build. The authored class files have version 61.0. No game, UI, provider, service, account, or personal data is selected.

| Operation | Result on all three JDKs |
| --- | --- |
| Cancel fresh task | `false`; later scheduling of that same object throws `IllegalStateException`. |
| Schedule fresh task in the future | Normal return. Scheduling that object again refuses. |
| Cancel scheduled repeating task | `true`; repeating task cancellation returns `false`. |
| Move that canceled task to another timer | Refuses. A different timer does not reset task admission. |
| Negative delay or zero repeating period | `IllegalArgumentException`; correcting the arguments admits the same task object. |
| Cancel timer, then cancel it again | Both return normally. A fresh task on that timer refuses. |
| Fresh task on the other, still-open timer | Normal return. |

All 48 callback-count samples remain zero. After final cancellation, the fixture joins the two named threads with a bounded wait and observes both absent. That completed observation is separate from the return of `cancel`; the fixture does not run or interrupt a callback. All six compiler/JVM groups exited, and the exact-capture process scans are empty. Two processors, a 96 MiB Java heap ceiling, private home/temp properties, and 30-second command timeouts bound the selected procedure, not host-wide concurrency or physical memory.

## Model and adapter boundary

[TimerPolicy.lean](TimerPolicy.lean) and [TimerPolicy.bend](TimerPolicy.bend) model two timers and six unexecuted tasks. Their small numeric states are research labels, not observations of JDK private enum fields. Timer cancellation preserves modeled task history and revokes scheduling on that timer. Task cancellation changes task admission even when its response is false. The model contains no callback, queue reachability, worker, wall clock, scheduler latency, or physical-reclamation state.

Fourteen Lean laws and nine Bend laws cover selected transitions. Two Lean examples and one Bend example concern source/model-only combinations: invalid arguments on an already-canceled timer and cancellation of a task whose timer was canceled. They are not additional native cases. Lean includes parameterized state-preservation laws; Bend's laws are closed terms. This is no universal JDK implementation proof.

The [typed research codec](TimerPolicyCase.lean) admits the selected JDK labels, object pools, and operations. The operation map is derived from the frozen authored helper, not captured internal RPC or JDK state. It distinguishes one-shot and fixed-rate call arguments before projecting the selected validity witness. It does not implement arbitrary long arithmetic, date overloads, time conversion, or overflow checks. Needed unknown timer/task identities and argument validity refuse; facts unused by a cancellation operation may remain unknown.

The [portable comparison](evidence/timer-conformance.json) matches 45 admission outcomes: 45 error-class results and nine cancellation Booleans. Three thread-retirement witnesses and 48 zero-callback observations are checked independently, not predicted by the admission model. Eleven unsupported DTOs refuse; four changed premises and eight changed raw observations are rejected. The receipt must equal the current computed result, including formal and basis hashes; a stale-receipt control refuses.

Ordinary CI runs retained data and the formal tools only:

```sh
python3 host/java/timer_conformance.py
```

`timer_probe.py --jdk /selected/jdk --private .build/minecraft` is owner-run native collection outside CI. `timer_observations.py --private .build/minecraft` audits retained inputs without Java. Its `--export` flag and the comparison's `--refresh-receipt` flag deliberately refresh public evidence. Neither refresh is an automatic acceptance step.

## Consumer and design implications

The [notification consumer map](../minecraft/NOTIFICATIONS.md) connects these host obligations to two original Minecraft clients. It inspects registration and retained references without executing a notification manager. Native JDK evidence must not become a claim that a game reload or notification was exercised.

Preserve task non-reuse, invalid-argument refusal, independent timer ownership, and repeatable timer cancellation. A caller that needs another timer must allocate a new one deliberately; retaining a non-null field does not establish that it can schedule. A new timer also does not establish that an older callback or queued UI action has retired.

For diagnostics and APIs, distinguish “future execution canceled,” “not previously scheduled,” “task callback finished,” and “worker joined.” Retain the exact affected timer/task identity and response; do not present `false` as “nothing changed.” An application may add an operation receipt or generation guard using its existing lifetime model, but no generic replacement scheduler or production API is selected here. `ScheduledThreadPoolExecutor`, callback exceptions, active-callback cancellation, queue purging/GC, race schedules, clock changes, drift/catch-up, and native Windows/Linux behavior remain separate work.
