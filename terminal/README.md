# Terminal application study

This study compares npm, pnpm, Yarn Berry, and empack through the same disposable terminal fixtures. It joins the requested action, communication, exit status, persistent effects, and safe next action. The empirical results describe the pinned programs and profiles; the proofs describe bounded models. Neither establishes correctness of an entire application.

Start with [the report](report.md) and [coverage](coverage.md). [Journey definitions](journeys.md) record the initial comparison, including operations that have no equivalent. [Claims](claims.json) connect observations, sources, models, and proposed UX decisions. Native command records are under `evidence/`; each record contains its request, before/after snapshots, independent channel bytes, and outcome. `safeNext` is reviewer advice, not output attributed to the program.

## Reproduce the checks

Run from the repository root:

```sh
LEAN=/path/to/lean BEND=/path/to/bend terminal/check
```

The checked versions are Lean 4.34.0 and Bend 2.0.40. The command checks six Lean modules, two Bend modules with their proof kernel, five real-subprocess fixture checks, retained native observations, and candidate decision agreement. The final [verification receipt](verification.json) records 86 native/model checks and 24 candidate combinations. It does not rerun package managers or touch user projects. [Replay](replay.py) rejects three deliberately broken observations: assumed rollback after refusal, cancellation erasing completion, and progress mixed into JSON.

The tool-specific Lean models are [npm](Npm.lean), [pnpm](Pnpm.lean), [Yarn](Yarn.lean), and [empack](Empack.lean). [Native.bend](Native.bend) executes a finite projection of their named native cases. The proposed boundary has both [Lean](Candidate.lean) and [Bend](Candidate.bend) versions. Its approval and evidence witnesses are supplied by the host; the model does not manufacture them from a terminal flag.

## Reproduce native observations

[Tool pins](tools/pins.json) identify the observed executables, runtime, platform, and locale. [Shell provenance](tools/shell.json) identifies the npm wrapper's shell. npm and Yarn use the pinned Node; pnpm is a native executable, with Node used by the fixture scripts. Yarn is Berry 4.19.0, not Classic. Native runners verify the pinned executable hashes before running. They require those local tools; the offline check above does not.

```sh
python3 terminal/study.py --stdin pipe
python3 terminal/study.py --stdin tty
python3 terminal/journeys.py --stdin pipe
python3 terminal/journeys.py --stdin tty
python3 terminal/profiles.py
python3 terminal/edges.py
python3 terminal/color.py
```

These create new, isolated work directories beneath `terminal/evidence/`, with private HOME, cache, durable state, and temporary roots. The fixtures use tiny local packages or resource packs and known scripts. They do not install global tools or change a real pack. This is environment separation, not an OS security sandbox: pnpm's default first-run behavior can contact the public registry. Corrected lifecycle runs set `pnpm_config_pm_on_fail=ignore` to use the pinned executable; Yarn disables network access. Scripts are requested explicitly only in the lifecycle experiments.

The first breadth pass uses the parent's `scripts/host-streams`. [The terminal extension](streams.py) adds independent stream modes, a fixed PTY width, and marker-triggered input or group SIGINT. It never attaches to a human terminal. A timeout is group SIGKILL, separately recorded. Fully terminal output merges the channels and therefore cannot establish which original stream contained a byte. Input events and reads have timestamps; they do not establish a total causal order across streams.

## Evidence and maintenance

Retain receipts, channel bytes, input/output identities, qualification exclusions, and useful negative cases. The first run's npm cases and empack preview were harness mistakes and are explicitly excluded. A later lifecycle run also records cold offline pnpm refusal and two invalid command forms; those are not successful lifecycle evidence. The corrected runs remain separately identified.

Generated tool archives, extracted Yarn, and native work trees are ignored. Small source snapshots and their digests are research provenance, with upstream revision references in `sources/`. Upstream tag resolution is not proof that a local binary was reproducibly built from that commit. The first profile entrypoint copies were retained after execution from unchanged scripts and are labeled as supplements, rather than runtime attestations.

No production empack source, installed packs, host tool installations, or other owners' rule files changed. This study does not activate the deferred dependency UX implementation intent. Any proposed CLI/API change requires a separate implementation decision.
