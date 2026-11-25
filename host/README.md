# Host behavior across boundaries

| Surface | User promise | Host operation and owning observation | Counterexample to a stronger promise |
| --- | --- | --- | --- |
| File | Open readers see a complete replacement | The directory owner renames a staged file; a later open sees its bytes. | A prior open can still read the old file. A check and a later rename allow an intervening edit. |
| Streams and children | Structured results can be piped while diagnostics remain interactive | The launcher connects each descriptor independently and the child queries each descriptor. | A terminal on stderr says nothing about stdin. Closing a pipe is distinct from child termination. |
| Scheduling | A timed wait returns control | The scheduler reports a timeout; an explicit completion object records whether the worker ended. | A worker can finish and commit after a timed wait or a request to cancel it. |
| Transport | An acknowledged operation took effect | A peer commits the operation and writes an application receipt with its ID. | EOF before the receipt is compatible with either commit or no commit. |
| Resources and devices | A finished submission may be used by the current consumer | The submitting queue reports completion; the consumer compares device/world identity and generation. | A completed job can belong to a retired generation. Releasing its old resources and publishing it are distinct decisions. |
| Authority | Only the change I reviewed is applied | The effect owner checks principal, target, basis, and current grant in the scope that performs the change. | A read-only hook sees the same target or a user edits it while approval is pending. |

## Reading the results

The [filesystem identity band](filesystem/README.md) adds a separate scoped guard rather than changing the older file-generation decision. Native owned fixtures distinguish case/normalization aliases, ancestry, missing identity, and rebinding after preflight. Java 17/21/25 same-file results have different preconditions from Python's object witness. Neither normalization nor a successful preflight supplies the actual mutation protocol.

The [profile matrix](../profiles/README.md) identifies the actual host, runtime layer, and untested cases. [Host.bend](../common/Host.bend) is the executable decision model. [Host.lean](../common/Host.lean) checks the invariants and supplies an independent finite model. Together they describe what can be reported from particular observations. Production integration remains a consumer decision. The probes execute real effects in private fixtures. This repository uses the emitted core during verification.

| Decision | Contract, assumptions, and observed failure case |
| --- | --- |
| File generation | In the fixture one writer replaces a known file in the same directory. A handle opened earlier reads A. A fresh open reads B. A prior successful content check followed by plain rename can overwrite an intervening C. Durable storage after power loss, all-volume atomicity, and an atomic expected-content write are separate claims. |
| Stream mask | Bits 0, 1, and 2 independently represent stdin, stdout, and stderr attachment. Decoding preserves all three observations. A piped stdout and PTY stderr can coexist with either kind of stdin. Eligibility for prompting also needs actual input ownership, policy, and an answer. |
| Completion | 0 means end unconfirmed and 1 means retirement witnessed. A stop request changes neither inference by itself. A completion witness needs its own identity, clock domain if timed, and owner. An operation that retired can still have failed. |
| Receipt | 0 means unknown, 1 confirmed refusal, and 2 confirmed commit of the named operation. Only a complete supported receipt with matching identity is usable. For a missing receipt, identical client evidence arose with two different server histories. Safe reconciliation needs an authoritative read or an idempotency key bound to the original request. |
| Product | 0 awaits successful owned completion, 1 withholds a completed product, and 2 admits publication. The selected consumer also requires its world and device generations and readiness. Allocate, dispatch, finish, release, and publish have different owners. An explicitly failed completion should take the host's failure/recovery path. |
| Reuse | For the healthy compatible pool case, retirement, sole pool ownership, and cleared uses are all required. Non-execution confirmed by the native owner can discharge a recording’s obligation. A retained publication, cache, or second lease can prevent reuse. The ledger probe exercises admission under a fixed ceiling, and the flock fixture exercises an exclusive resource under duplicated ownership. Neither measures physical driver memory. |
| Approval | A serialized statement combines current principal/grant, target, and basis. The SQL fixture applies one review once, rejects a stale replay, and reports its row count. The corresponding filesystem check followed by unconditional replacement has a race. The proof orders both events and exhibits their different results. |
| Scoped effect | 0 means the before/after comparison is unavailable, 1 means unchanged at those observations, and 2 means changed. A nonzero exit cannot establish any of these. Project files and incidental caches/logs are independent scopes. Equal snapshots can hide an intervening write. |

### Two consumers that changed the map

**empack.** The file planner handles an expected baseline, observed local state, and desired content. Comparing 245 normalized cases exercises its decision. Actual root confinement, serialized publication, and recovery are further obligations. Likewise, the process adapter requests termination and waits for its owned process tree to retire. An observation timeout explicitly retains the need for recovery. The stderr terminal capture alone could not represent a piped stdout and independent input. Empack's terminal-study owner and the host study agreed on the shared fixture below. [Planner and recovery](../empack/README.md) · [Process-tree retirement](../../empack/crates/empack-lib/src/application/process_runtime.rs)

**Terminal audit finding.** The empack owner found a pnpm 12.21.0 invocation of `pnpm terminal-unknown-command` that exited 1 yet created the project lockfile and installed the local dependency. Inspection of the same run's before/after inventory also showed new cache entries. This exposed a missing rule. The shared effect decision now takes an independently observed scope; the native negative control uses identical exit codes with different project effects. The terminal owner keeps the original receipt (case `pnpm/refusal`, run `20261123T224740171810Z`, SHA-256 `d4b52e44a06978c2ef65199cae367a890aba06e509496f5c7a5e928e499c3943`). It establishes that invocation, without attributing causation to a specific pnpm source branch.

**Playground.** Owner review at d7a1c99 identified two distinct boundaries. A streaming job can ignore cancellation and retain a memory charge until the worker retires. Its consumer also checks the generation, demand, required readiness, and output bound. For a GPU target, even an idle GPU and a retired submission leave the target unavailable for recycling while a published image holds it. The native target pool checks its own ownership count and outstanding texture uses. We incorporated those qualifications into separate publication and reuse laws. The tick/halo rules still require a coherent input root and usable neighbor coverage. Their scoped grid proofs and the native ledger check establish different claims. [Streaming consumer](../../playground/src/world/Streaming.cpp) · [Held worker fixture](../../playground/tests/world/streaming.cpp) · [Published-image regression](../../playground/tests/rendering/gpu_device.cpp) · [Pool owner](../../playground/src/platform/sdl/GPUInternal.cpp) · [Grid and halo models](../playground/README.md)

### Wire and host boundaries

The shared trace envelope has `v`, `surface`, `case`, `observed`, and `outcome`. The surface defines the data contract. The host decision verifier requires named Boolean facts and checks the numeric decision against the emitted module. A missing flag, unrecognized surface, or absent/unknown major version is refused. Use a separately admitted translator when an older producer lacks a necessary fact. Guessing false would turn an unknown into a decision. A scoped effect with no comparable basis remains unknown. Transport receipts additionally bind an attempt; the loopback fixture has a single known peer and does not implement production authentication.

The fixture `scripts/host-streams --stdin pipe|tty -- command args` uses a private non-controlling PTY on stderr and a pipe on stdout. Pipe stdin receives EOF, while tty stdin uses the slave independently of stdout. The result records all three descriptor facts, base64 channel bytes, exit code or signal, timeout, and capture completeness. The PTY may translate LF to CRLF. Capture does not establish a total order across channels. A fixture timeout forcibly ends the owned process group. It cannot stand in for a user's graceful interrupt. The terminal study owns input/width/interrupt extensions.

A subscriber must retain the baseline, authorized interest, and sequence required to interpret the next update. If the host can only observe EOF, distinguish an unknown application outcome from a known rejection. A hook observing a new revision may explain the cause, but applying another change needs a current grant and a fresh basis. The existing [replica delta model](../playground/Workflow.lean) and [replay laws](../common/README.md) give the corresponding receiver-side checks.

### Reproduction

Use the toolchain in the [repository index](../README.md). From the rules root:

```sh
scripts/check-host
host/java/check "$(/usr/libexec/java_home -v 17)" 17 > .build/java17.jsonl
host/java/check "$(/usr/libexec/java_home -v 21)" 21 > .build/java21.jsonl
host/java/check "$(/usr/libexec/java_home -v 25)" 25 > .build/java25.jsonl
node host/compare.mjs .build/java{17,21,25}.jsonl
```

On Ubuntu use the corresponding installed JDK home and run `python3 host/native.py` in the same repo layout with `scripts/host-streams` present. Copy the JSON lines to the verifier when the native runner has no proof toolchain. On a qualified Windows machine, compile [WinProbe.c](WinProbe.c) with its documented compiler line, run the resulting executable with the selected standard handles, capture stdout and stderr separately, and pass its JSON lines to the same verifier. The POSIX PTY launcher does not claim Windows console parity.

Requalify changes to a surface, its codecs, and the consuming profile together. Preserve the negative cases for missing facts, wrong or incomplete receipts, refused publication, and failed commands with effects. Every Boolean input is enumerated for differential comparison of the Lean and emitted Bend classifiers. That comparison is finite and exhaustive for the declared input types only. The independent Bend verdict checks its stated laws. Native probes qualify named operations and actual builds. [Recorded run](evidence.md)
