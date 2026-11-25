# Prism: hook commands, wrapper arguments, and terminal results

This band follows Prism 11.1.1 source `7d2d3c1ec6fcf8255ebacd02d9f792688575dfb4`. It executes original pre/post hook classes, `LoggedProcess`, and the custom argument splitter with real Qt 6.12.0 on macOS arm64. Instance/environment construction and Task outcome publication are [explicit adapters](commands_adapter.h). The [driver](commands_driver.cpp) also executes the unchanged wrapper-selection block with an adapter completion handler. No Prism GUI, game, Java, shell, account, or personal instance runs.

The [source ledger](../sources/prism-command-selections.json) separates compiled files, selected functions, and inspected callers. The [receipt](../evidence/prism-commands-20261125T165137028675Z/receipt.json) binds source selection, generated source, compiler/moc, Qt framework, inputs, executables, and streams. Runtime `qVersion()` agrees with the selected package. Both `QT_NO_DEBUG` and assertion-enabled helpers use `-O0`; neither establishes correspondence with a shipped Prism binary or current upstream head.

The recorded latest-release lookup still identifies [11.1.1](https://github.com/PrismLauncher/PrismLauncher/releases/tag/11.1.1), published September 28, 2026. Unreleased changes have not been requalified.

## Execution and argument observations

| Boundary | Retained observation |
| --- | --- |
| Pre/post helper exits zero | Hook reports success |
| Pre/post helper exits seven | Hook reports failure; the observation runner itself completes normally |
| Missing pre/post executable | Detailed log names the start failure; hook headline says “failed with code 0” |
| Abort after the owned child publishes its witness | `abort()` returns true, the hook fails, and the owned child is confirmed absent |
| Empty or whitespace-only wrapper configuration | Wrapper block starts the supplied Java-data executable directly |
| Nonempty wrapper | Wrapper receives its arguments, then the selected Java path and original game arguments |
| Missing wrapper executable | Wrapper block reports refusal before starting a child |

The wrapper child records its invocation instead of launching Java. The same disposable executable fills both program roles, so this comparison qualifies the argument handoff, not selection between distinct executable binaries. Game handshake, detachment, descendants, and real Java/runtime behavior remain open.

All nine child witnesses retain argv, private working directory, environment value, and PID. Unicode and an argument containing spaces survive the selected handoffs. This is not Windows, C-locale, or JVM argument qualification.

Hooks call `QProcess::splitCommand`; wrappers call Prism's `Commandline::splitArgs`. Five literal observations preserve their differences. Single quotes group words for the wrapper parser but remain literal characters for the hook parser. A tab separates hook arguments but remains inside one wrapper token. Both drop the tested empty quoted argument. Expansion happens before splitting: an unquoted two-word value becomes two arguments; a quoted value becomes one. These finite examples do not qualify either complete grammar or arbitrary interpolation values.

## Empty tokens are not a safe refusal

The hook's inspected caller admits a nonempty configured string. The hook then substitutes variables, splits, and calls `takeFirst()` without checking the resulting list. The wrapper trims before expansion but also takes the first token without a subsequent empty-list check.

Five isolated helper cases reached that unmet precondition: whitespace pre-command in both variants, empty quoted post-command in release, and wrapper expansion to whitespace in both variants. Release helpers terminated with SIGSEGV; assertion-enabled helpers with SIGABRT. Each preserved its before-execution packet; none produced a terminal hook result or child witness. Core dumps were disabled.

This is a reproduced selected-source failure with controlled configuration strings and the recorded Qt build. Full settings-page admission, shipped-binary behavior, and a complete launcher reproduction remain unqualified. The model classifies the unmet precondition; it does not claim undefined behavior always produces a particular signal or silently represent the crash as a successful refusal.

A focused proposed guard checks parsed tokens before taking a program. Keep raw empty hooks omitted and whitespace wrappers on their existing direct-launch path. Reject a configured command that becomes token-empty after expansion with a persistent actionable error. This is a design classifier, not an implemented or natively tested fix. Review current upstream changes before proposing an upstream patch.

## Context and sequence contracts

The inspected settings code uses one override gate for pre, wrapper, and post commands. `OverrideSetting::get` delegates to the global value when disabled; when enabled, an absent local value still falls back through `defValue`, while a stored empty string can clear it. This is source inspection, not a native settings-storage comparison. A group override must not be assumed to clear every omitted field. Empack's [template study](../empack/TEMPLATES.md) leaves complete Prism-consumer acceptance open; its [pinned source context](../sources/prism-command-context.json) writes pre/wrapper entries and omits post-exit. Clarify and test that interaction before changing defaults.

The inspected launch sequence places pre-command before update/game work and post-command after the game step. `LaunchTask` stops advancing after a failed step. The game step fails on crash, abort, or a nonzero normal exit, so post-exit is not a general `finally` cleanup path in this sequence. A later post-command failure also concerns a different phase from the already exited game. This band does not execute that joined controller/game workflow; its source-derived eligibility law is separately labeled.

Preserve phase, start failure, process exit, abort request, and observed retirement. A missing executable has no meaningful successful exit code merely because `LoggedProcess` initializes its numeric field to zero. Reuse the existing state and error string for reporting. Detailed logs retain the cause here; improve the summary rather than inventing another process state machine. An accepted abort is distinct from terminal completion and from proof about arbitrary descendants.

## Models and retained comparisons

[Lean](Commands.lean) has fifteen laws; [Bend](Commands.bend) has seven. The [closed decoder](CommandsCase.lean) admits interpreted fixture roles and token identities. Parsed token lists are observed premises, not output from a reimplemented parser. Seventeen classification/outcome records and 102 Bend fields match: twelve defined execution cases and five empty-list boundaries. Nine child-argument lists are checked against independent child witnesses. The five parser observations remain literal source/library comparisons outside that formal conformance count. Eight changed-observation/decoder controls must fail.

The [pure replay](commands_conformance.py) verifies streams, inputs, available sources/artifacts, selected-source reconstruction, and formal inputs without compiling or launching an application. Source-only configuration/sequence conclusions and the proposed guard do not become native qualification through replay.

An [earlier fixture compile](../evidence/prism-commands-20261125T165058035388Z/failure.json) omitted the task declaration's `m_instance` field. Its eight tool groups retired before any native case ran. Original code and compiler diagnostics remain; the corrected declaration collected a fresh cohort. This was a study adapter error, not a Prism failure. All 31 groups and nine children in the completed cohort retired; no exact-work-path process remained. Its private allocation was 784 KiB, and the inputs/artifacts remain retained.

## Design and remaining verification

Keep structured program/argv values internally where available, and render them for the actual consumer's grammar at its boundary. A common parser is a possible future API decision, but changing either existing grammar silently can alter user commands. Reuse current command getters, setting states, process wrappers, and typed outcomes; no second launcher or generic orchestration framework is selected.

Remaining work includes settings/storage admission, complete UI save paths, post-after-crash behavior, distinct wrapper/Java binaries, failed starts and cancellation across the real controller, process-tree ownership/detachment, fragmented output attribution, and Windows/Linux parity. Any correction must retain the exact input and partial logs, preserve deliberate global/local choices, and verify the joined operation before claiming launcher-wide behavior.

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/prism/commands_conformance.py
```

Compile the formal modules first. Never replay the one-shot native collector over a completed capture.
