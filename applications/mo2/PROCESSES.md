# MO2: launch context, waiting, and refresh decisions

This band follows MO2 v2.5.2 at `9c130cbf2fc7225fb2916e46419af50671772aa0`. It separates selected-source policy execution from inspected callers and unsupported Windows process behavior. It does not launch MO2, inject a process, run a game, or capture game output.

## What was executed

The [collector](process_probe.py) inserts the unchanged `ProcessRunner::shouldRefresh` and `postRun` bodies into an explicit [research driver](process_driver.cpp). Twenty authored cases exercise return values, effective lock reasons, waiting calls, presence of a lock-session pointer, `afterRun` calls, and event-loop connection/wait calls. The [receipt](../evidence/mo2-process-20261125T161939910466Z/receipt.json) binds inputs, selected cuts, generated source, compiler, executable, and separate command streams. All three recorded command groups exited and were absent afterward.

Unlike the [plugin band](PLUGINS.md), this driver does not link Qt. Its settings, flags, handles, wait routine, lock session, callbacks, and event loop are inert adapters. A wait result is injected; `exec()` records a call and returns immediately. Neither a recorded wait call nor a refresh callback is an independently observed lifecycle completion. The `Running` wait-result control is an admitted enum-shaped adversarial input; its reachability through the real wait loop is unqualified.

## Return and refresh are separate facts

| Selected policy input | Observed selected-method behavior |
| --- | --- |
| Unhooked, no force-wait flag | Returns `Running` before waiting or refreshing |
| No lock reason, no force-wait flag | Returns `Running`, including when UI locking is disabled |
| Hooked, lock reason set, locking disabled, no force-wait flag | Returns `ForceUnlocked` before reaching the refresh branch |
| Force-wait with no lock reason | Changes the effective reason to `LockUI` and calls the wait adapter |
| Force-wait, `PreventExit`, locking disabled | Waits with a null UI-session pointer |
| Wait reports completed or force-unlocked, refresh flag set | Calls `afterRun` |
| Wait reports cancelled, error, or running | Does not call `afterRun` |
| Refresh branch runs and wait-for-refresh flag is set | Connects a refresh callback and calls the event-loop adapter |
| Wait-for-refresh bit without refresh bit | Does not refresh or enter that event loop |

The early disabled-locking result and a force-unlocked wait result share the same returned enum but take different refresh paths. A standalone `shouldRefresh(ForceUnlocked)` result cannot establish that `postRun` reached that branch. The comparison retains actual branch order rather than composing independent predicates as though they always execute.

The inspected lock UI labels its actions `Unlock`, `Exit Now`, or `Cancel`, depending on purpose. Its handlers set the lock result and release the current lock. The inspected wait loop consumes those results. These handlers do not establish process termination. The source's wait helper attempts Windows job assignment, falls back to an initial handle if none succeeds, and selects interesting processes to monitor. Assignment coverage, child inheritance, process liveness, and retirement need actual Windows evidence. An `Exit Now` control in this lock UI must not be modeled as killing the launched application without that evidence.

## Which profile does a launch use?

The [earlier mapping band](ROUTING.md) found that a supplied profile name and ambient profile can affect different parts of a mapping. This caller trace narrows the outstanding reachability question:

- Both inspected GUI start actions call `setFromExecutable`, which reads executable customization from the active profile. Profile switching explicitly changes that active profile.
- Initial application setup selects the instance's profile. Forwarded command lines reject a requested instance or profile that differs from the running instance/profile. These paths do not demonstrate the mixed-profile launch constructed in the mapping fixture.
- `OrganizerProxy::startApplication` accepts a plugin-supplied profile and forwards it to `setFromFileOrExecutable`. That method records the supplied name but reads executable overwrite/forced-library settings from the ambient profile. `runBinary` supplies the ambient name only if the recorded name is empty, then forwards the selected name to `beforeRun`.

Thus, the plugin API provides a source-level route for a differing profile argument. Whether a real plugin uses it, which settings are deliberately ambient, and what a supported Windows launch reads or writes remain unresolved. This is not a reproduced GUI profile-loss defect. The proposed explicit launch context remains an API design question; an alternative is an enforced same-profile precondition for entry points that require it.

## Callers and partial effects

The inspected GUI uses `TriggerRefresh`; the command-line combination also forces waiting and requests waiting for refresh. The legacy executable/shortcut command paths ignore the returned `run()` result and return zero unless an exception is thrown. The named `run` command maps `Error` to failure but returns zero for other result values. This source-level result conversion deserves caller-specific documentation and supported-host testing; no Windows command-exit reproduction is claimed here.

The plugin launch API does not wait and transfers its handle to the plugin. Its separate `waitForApplication` reports success only for `Completed`; cancelled and force-unlocked returns are false. This is a clearer completion contract for a caller that requires output. Handle transfer still does not prove child-tree containment or retirement.

`beforeRun` saves current profile state and writes its mod list before a plugin can veto launch or mapping can fail. A launch refusal therefore cannot mean “no changes” across every scope. The inspected `afterRun` refreshes directory/plugin state and requests saving; executing the inert callback adapter does not qualify those effects. Keep preparation, launch, waiting, refresh, saved representation, and output adoption distinct.

## Models, comparisons, and limits

[Lean](Process.lean) models the selected return/lock/refresh decisions with fifteen laws. Its [closed research decoder](ProcessCase.lean) accepts only the interpreted flag, reason, Boolean, and result ranges. [Bend](Process.bend) provides seven laws and independent decision kernels. The [pure replay](process_conformance.py) compares all twenty retained outcomes and 180 scalar fields, reconstructs selected bodies, and checks source/artifact/stream identities. Ten changed-observation and decoder controls must fail. It never runs the compiler, driver, MO2, Qt, or a child program.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/mo2/process_conformance.py
```

Compile the model modules first. Missing private artifacts or source caches reduce available identity checks; they do not grant fresh execution evidence in another checkout. Caller bodies are inspected source, not executed model cases. The source ledger records those scopes separately.

Keep the existing entry points and clarify their guarantees before adding coordination. A proposed result should identify whether it describes spawn admission, waiting, an unlock/cancel choice, refresh completion, or saved output. Do not replace them all with “done.” Preserve the original wait result and uncertain child state; requesting a refresh does not make live output stable. For empack, this supports retaining the actual terminal operation result through cancellation and distinguishing it from requests to stop, independent retirement evidence, and later recovery.

Windows jobs, real handles/exit codes, process trees, Qt event delivery, output capture, actual profile files, VFS injection, plugins, refresh/save failures, and joined launch/adoption workflows remain pending. Recheck the caller contracts, enum/flag meanings, wait branches, and host adapters before changing source pins. No production patch, complete executable feature qualification, or new process framework is selected.
