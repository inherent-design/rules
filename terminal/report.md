# Terminal behavior findings and proposed empack rules

Empack already handles the main boundaries well in the cases tested: redirected structured results stay separate from progress, dry runs preserve project and durable state, approval is explicit, and cancellation does not erase an operation that completed. The useful next work is to make these guarantees consistent across commands and make failures name the affected input and safe next action. This study found no reason to replace the CLI with a package manager's command model.

This is a proposal and bounded comparison, not acceptance of production changes. [Coverage](coverage.md) and [claims](claims.json) identify the tested invocations and unresolved limits. Lean and Bend check the models and their named projections; they do not prove the implementations equivalent to those models for every input.

## What the comparison establishes

**An exit code does not describe effects.** In the fresh pnpm fixture, an unknown-name command goes through a dependency gate, installs the local dependency, and then fails because the requested command does not exist. The pinned source runs that gate before dispatching the requested script/command. This is an intentional command path, not evidence that pnpm's option parser executed an invalid option. It is still a counterexample to treating any refusal as rollback. [Pinned run dispatch](https://github.com/pnpm/pnpm/blob/b8d388835f9a40ee1ac53fbc2d4b58c3ebfa5600/pnpm/crates/cli/src/cli_args/run.rs), [gate](https://github.com/pnpm/pnpm/blob/b8d388835f9a40ee1ac53fbc2d4b58c3ebfa5600/pnpm/crates/cli/src/cli_args/verify_deps.rs).

The explicit package scripts provide the simpler example: each writes a marker before failing or receiving SIGINT. Reinstalling successfully afterward leaves that marker intact. Empack's cancellation cases establish the complementary distinction: cancellation while waiting for approval returned 130 without publication; cancellation observed during saving returned 0 after the change completed. The latter is a completed result, not a failed cancellation mechanism.

**Preview and resolution are different actions.** npm's install dry run leaves the project unchanged but writes logs and runtime caches. The pnpm dry run in the already-installed breadth fixture leaves project files unchanged. Yarn's `update-lockfile` mode actually writes the lock and cache while skipping the link phase. It should not be presented as an equivalent of empack's dry run. [Yarn install modes](https://yarnpkg.com/cli/install), [npm install dry run](https://docs.npmjs.com/cli/v11/commands/npm-install/).

**Stream capabilities must remain separate.** Empack accepts confirmation when stdin and stderr are TTYs even with stdout piped. Removing stderr's terminal makes it refuse approval with a useful `--yes`/`--dry-run` explanation. Its source detects result styling separately from stderr progress and prompt input. Preserve this design. A TTY is a device observation, not proof of a human or authorization. [Released capability implementation](https://github.com/inherent-design/empack/blob/9d0ba2d10340736c39fd94ad21958a03d693cf18/crates/empack-lib/src/terminal/capabilities.rs), [session input](https://github.com/inherent-design/empack/blob/9d0ba2d10340736c39fd94ad21958a03d693cf18/crates/empack-lib/src/application/session.rs).

**Machine output needs failure coverage.** The observed Yarn `info --json` succeeds with NDJSON after installation. With the required lock absent, it emits a human error/stack on stdout. A successful JSON test alone therefore cannot establish that automation can decode failure. In contrast, empack's malformed-lock `check --json` emits a parseable failure report on stdout, a diagnostic on stderr, and a nonzero status. Preserve that combination. Fully terminal merged output is a different profile and cannot establish either tool's original stdout bytes.

**Familiar conventions are not universal laws.** npm's top-level `--help` prints help and exits 1 in this release. Yarn's script supervisor maps the observed signal-terminated script to 129, while npm/pnpm are observed as signal 2 at the subprocess boundary. Those are actual differences, not grounds for making empack imitate them. [npm entry point](https://github.com/npm/cli/blob/d12b9434dd010b5fb7044c3cc149cdda317813f8/lib/cli/entry.js). The Yarn source excerpt is tied to the distribution digest in `sources/yarn-signal-excerpt.txt` and `tools/pins.json`.

## Proposed empack decisions

### Preserve result, effects, and recovery as separate facts

Keep the current rule that the actual terminal result wins over a late cancellation token. Do not weaken retirement or durable ownership handling to produce a simpler interrupted message. Also avoid a global rule that nonzero means nothing changed, or that successful installation undoes a failed external command.

The candidate [Lean](Candidate.lean) and [Bend](Candidate.bend) boundaries separate inspect, preview, and apply. Applying requires current captured input, sufficient evidence, and approval bound to the exact prepared target. Changed input requires a fresh plan; unavailable evidence remains a refusal. The proofs assume the host establishes those witnesses. They are not a replacement for native revalidation or a proposal to change every mutating verb into `--apply`.

Status: result preservation is **already satisfied in the tested paths**. Target-bound approval and complete-evidence gating are **preservation requirements**, with broad native concurrency qualification still pending. Effects reported as unknown must remain unknown until inspected. The shared model's recovery advice means inspect retained evidence first, not that every unknown observation needs a destructive repair.

Acceptance: retain the early/late cancellation cases; add fault-injected partial publication and retained ownership failures in a separately authorized implementation pass. Check final exit, both streams, durable evidence, and actual content together. A useful negative test must fail if cancellation overwrites a completed result or if an error summary drops known partial effects.

### Make failure identify the input and next action

The missing-source `--continue-independent` probe refused before publishing either input. Its diagnostic was:

```text
Error: Cannot read direct dependency input: No such file or directory (os error 2)
```

That refusal is safe, but it does not name which supplied path failed. A proposed message is:

```text
Cannot read ./supplied/missing.zip: the file does not exist.
Check the path, then retry the missing addition.
```

The safe next step must depend on the actual outcome. If independent work did publish, name what was saved and what remains before suggesting retry. Do not use the example above to claim this fixture exercised partial publication—it did not. The same principle applies to structured diagnostics: retain a stable code and phase, and populate the affected input/key where known. A `null` object is not a substitute for already-available context.

Status: **proposed improvement**, supported by the captured missing-source failure and consistent with the deferred dependency diagnostic work. It does not activate that intent. Alternative: leave the short error unchanged and rely on debug logs; this saves implementation but leaves users with several possible inputs to inspect. The recommended change is a bounded context improvement, not another error hierarchy.

Acceptance: two valid local inputs and one missing input; capture no-change and genuinely independent partial-success cases separately. Assert the named path, preserved cause/code, saved targets, nonzero status, and safe retry scope. No config/lock migration is needed. Any serialized field change must be reviewed explicitly for machine callers.

### Keep structured results usable on both success and failure

Continue routing results to stdout and progress/interactive feedback to stderr. Preserve valid failure reports, not only successful reports. A malformed source should not make a machine-mode command unexpectedly switch to prose on stdout. Explicit color intent should affect display styling without corrupting serialized values.

Status: **already satisfied for the observed empack check paths**; a command-wide guarantee remains **pending an inventory of each machine-mode command**. Do not claim all commands have the same JSON schema or that arbitrary child output is structured merely because the parent has a JSON option. Yarn's observed error is a useful negative comparison, not an implementation template.

Acceptance: separated streams, stdin independently piped/TTY, forced/disabled styling, successful and failed reports, and an intentional contaminating progress prefix that the parser must reject. Preserve typed status codes and diagnostic facts. A human summary can be shorter than the machine report without deleting facts from it.

### Keep prompts about their actual decision

In pnpm's configured prompt gate, declining installation still permits the explicitly requested script to run. That is consistent with its gate source, but a user could read “no” as cancelling the whole command. Empack should retain the narrower, explicit approval of the displayed plan. Do not borrow automatic prerequisite installation or infer approval from device presence to make workflows appear smoother.

The input-only TTY pnpm profile exited 1 without a captured explanation. This is a **confirmed observation of a non-controlling PTY profile**, not a confirmed defect on a real user's terminal. Its relevance to empack is to retain a diagnostic when input cannot be obtained. The tested empack refusal does that already.

Acceptance: refusal, decline, explicit acceptance, EOF, cancellation, and unavailable prompt output should have distinct observable consequences. A declined plan must preserve project files. Do not force a choice by replaying a guessed default. Human navigation and screen-reader behavior still require their own evidence.

## What should stay separate

Keep authoring intent, exact dependency selection, local verification, distribution export, and installed-instance ownership separate. The package fixtures do not establish mod compatibility, startup, worlds, or consumer acceptance. A lockfile-only operation, normal installation, local integrity check, and a dependency update answer different questions even if other tools group them under one command.

Do not turn this study into a CLI rewrite, live registry service, new migration framework, or 0.9 implementation. No defaults, serialized schemas, exit codes, or production files were changed. The candidate is review material. The deferred removal/re-adoption and update-preview intent remains unstarted.

## Evidence quality and remaining limits

The first run revealed two harness errors, which are excluded rather than presented as application defects. The next lifecycle attempt revealed pnpm's cold offline tool-management prerequisite, an unsupported Yarn flag, and empack's deliberate rejection of parent-relative supplied paths. Corrected invocations are separately retained. npm's full implementation tree and entrypoint, Node, the native pnpm binary, Yarn bundle, and empack binary are identified by digests; source references and their limits are recorded.

The check combines model proofs, finite native conformance, negative controls, and real subprocess tests of the observation fixture. It does not prove source/binary equivalence, absence of transient/external writes, process-tree retirement, or all-platform UX. The native coverage is macOS, private PTYs, a small local graph, and controlled scripts. No real Minecraft, Prism, signed channel, browser, human accessibility session, or crash-recovery acceptance is claimed.

The next owner decision is whether to implement the bounded diagnostic and machine-mode consistency work. There is no evidence here requiring a new terminal, solver, or recovery architecture.
