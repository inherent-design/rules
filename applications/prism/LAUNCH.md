# Launch phases, task outcomes, and abort delivery

Prism 11.1.1's launch controller phase, base task outcome, instance flags, and operating-system processes describe different facts. This band executes pinned `Task` and `LaunchStep` code with real Qt 6.12 signals, selected unmodified `LaunchTask` methods, and controlled steps. It does not launch Prism's GUI or Minecraft.

## Source and acceptance environment

The [source selections](../sources/prism-launch-selections.json) pin revision `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. `LaunchStep` connects its `finished` signal to `LaunchTask::onStepFinished`. The controller starts steps sequentially and finalizes the started prefix in reverse order on completion or failure. `Task` separately owns its running/succeeded/failed/aborted outcome and terminal signals.

`LaunchTask` has its own `NotStarted/Running/Waiting/Failed/Aborted/Finished` phase. Its nonempty success/failure path delegates outcome publication to `Task` without updating that private phase. Its `abort()` delegates to the current step and sets the controller phase to `Aborted` after acceptance. The step's completion signal can arrive inside that call or remain pending.

The pinned build requires Qt 6.4 or newer and rejects other major versions. The [fixture receipt](../evidence/prism-launch-20261124T045858343366Z/receipt.json) records Qt 6.12.0, Apple Clang 21, macOS arm64, `-O0`, and `-DQT_NO_DEBUG`. Complete `Task` and `LaunchStep` sources and supporting headers are copied unchanged, using Qt's actual moc and signal delivery. The `LaunchTask` declaration, instance object, log handlers, and concrete steps are fixture adapters; executed lifecycle bodies remain unchanged. This matches the supported Qt major/minimum, not every dependency or configuration of a full Prism build.

The collector freezes its source at startup and records source, generated-code, executable, and stream identities. The executable hash is unchanged across execution. Generated work occupies about 456 KiB and is excluded from Git. There are no accounts, downloads, game files, profiler, terminal, or GUI operations.

## Observed sequences

Ten cases record initial, post-start, post-action, and post-event-loop snapshots, with ordered instrumentation and parent task signals.

| Sequence | Observed result |
| --- | --- |
| No steps | Succeeds without starting a step; controller phase becomes `Finished`. |
| Three immediate successes | Starts `0, 1, 2`; finalizes `2, 1, 0`; base task succeeds while controller phase remains `Running`. |
| Failure in the middle | Starts `0, 1`; finalizes `1, 0`; future step `2` never starts. |
| Ready request, then proceed | Waits, proceeds, and succeeds; phase remains `Waiting` after base completion. |
| Progress request, then proceed | Uses the same waiting phase but a different request signal; later succeeds. |
| Abort disabled | Returns false without calling the step's abort method; task remains active. |
| Step declines abort | Calls the step, returns false, and remains active. |
| Synchronous step abort | Finalization and parent failure publication occur inside the abort call; the call then returns true. |
| Queued step abort | Returns true with phase `Aborted`, while base task and instance-running flag remain active until delivery. |
| Abort after an earlier successful step | Finalizes the started prefix in reverse; the future step never starts. |

Both accepted abort behaviors reach the parent's **failed** base outcome with reason `Aborted`, not the parent's `aborted` outcome. The mirrored instance receives running=false and crashed=true. These are controller calls against an adapter, not evidence of actual Minecraft crashes, persisted metadata, or process retirement.

Refused/disabled synthetic hold steps are completed only after the primary observation. Separate cleanup snapshots confirm no fixture base task remains running before owner destruction. Those later effects are excluded from the tested abort result. Finalizers only record calls; they own no real process or external resource.

The real `LaunchController` source forwards success/failure, distinguishes ready/progress interactions, and asks through “Kill Minecraft?” before normal user-triggered abort. Preserve that force-stop intent. It differs from graceful server shutdown, and failure must not automatically become clean cancellation. Profiler, dialogs, and actual game steps remain unexecuted.

## Models and replay

[Lean](Launch.lean) checks eleven laws and predicts the controlled snapshots, request acceptance, outcomes, and event order. Controller phase and base outcome remain separate. Reverse finalizer calls do not prove that arbitrary resources retired.

[Bend](Launch.bend) checks four laws and two conditional projections. Given the independently observed started prefix and base completion, it predicts reverse finalization for ten cases. Given a controlled abort policy and delivery point, it predicts ten admission/pending/failure points. It does not implement the complete step interpreter.

The [replay](launch_conformance.py) checks retained identities, matches ten Lean traces and the Bend projections, and rejects an unknown step kind:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/prism/launch_conformance.py applications/evidence/prism-launch-20261124T045858343366Z
```

Compile `Launch.lean` to `.build/applications/prism/Launch.olean` first. Replay does not build Prism or start a game. Native collection is the separate owner-run `python3 applications/prism/launch_probe.py`, outside ordinary CI. It covers one same-thread attempt and an explicitly queued timer. Concrete production steps, repeated starts/callbacks, cross-thread delivery, callback-driven destruction, and finalizer failure remain outside the result.

## Preservation and improvement candidates

**Preserve cleanup ordering and outcome evidence.** Failure must not start future steps, and request acceptance must not imply retirement. Base task queries provide completion information that the launch phase alone does not. Keep the original error and actual finalization results when a stop request accompanies failure.

**Represent request, activity, and outcome separately.** An additive inspection result can contain current step, waiting reason, stop request/admission, base outcome, and finalization evidence. A future internal state can keep a pending stop request within an active phase and publish a separate completed result. Synchronous completion may precede the requesting method's return; consumers cannot assume acknowledgement always comes first. Bind both to the same operation identity.

**Name stopping actions for their actual effects.** Preserve force-stop confirmation. Before distinguishing preparation cancellation from stopping a running game, audit the concrete steps' capabilities and effects. “Stop requested” describes pending delivery; it is not a terminal result or promise of graceful shutdown. Human and structured reports should use the same facts.

The keep-current alternative is credible when callers consistently use `Task` completion and existing signals. A wrapper may provide the needed distinction without a scheduler rewrite. Internal consolidation requires an audit of phase/outcome consumers, concrete steps, restarts, QObject lifetimes, and plugins. This fixture justifies no saved instance format change.

Native qualification still needs actual preparation, downloads/cancellation, profiler/console dialogs, process termination and descendants, and platform resource ownership. Preparation, kill-game, and download-cancellation operations remain pending in the inventory. This controller component study cannot substitute for them.
