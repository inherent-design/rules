# Workspace selection, script execution, and partial results

This band compares npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0 with Node 26.13.1 on macOS arm64. Twenty-seven native commands include three private offline installations and 24 workspace runs. One root and four members form a generated project: A depends on B, C is independent, and D lacks the requested `probe` script. No user project, registry publication, or graphical application participates. Cargo's different workspace/build selection remains covered separately and needs further default-member and execution checks.

## Domain and source rules

Workspace membership, dependency edges, command selection, scripts present, scheduling, and actual completion are different facts. An exact workspace selector need not include dependencies. A selected package can have no applicable script, remain undispatched after a failure, or be blocked by a failed dependency. Script selection is not a filesystem sandbox: the fixture deliberately writes its effect log outside the package directories.

The [selected source](../sources/js-workspaces-selections.json) and native commands agree on these bounded profiles:

| Request | npm | pnpm | Yarn Berry |
| --- | --- | --- | --- |
| Ordinary root `run probe` | Root only. | Root only. | Root only. |
| Workspace-wide iteration | `--workspaces` excludes root by default. | `-r` excludes this workspace root by default. | `workspaces foreach --all` includes root. |
| Include root explicitly | `--include-workspace-root` with workspace iteration. | `--include-workspace-root` with recursive iteration. | Already included by `--all`. |
| Select A exactly | A only. | A only. | A only. |
| Select A and dependencies | No corresponding command is tested. | `--filter fixture-a...` runs B, then A. | `--from fixture-a --recursive --topological` runs B, then A. |
| Missing member script | An error unless `--if-present`; earlier members can already have run. | This recursive profile skips D; no matching script anywhere is an error. | The tested `foreach run` skips D without error. |
| Missing exact selection | Error, no fixture script started. | With explicit `--fail-if-no-match`, error, no script started. | Error, no script started. |

pnpm's source has explicit exceptions to root auto-exclusion, including root-only or absent workspace patterns and explicit filters. This fixture has a real workspace file with four nested members; its root-exclusion observation must not be generalized to every recursive context. Yarn's recursive selection follows dependency relations, while its worktree selection follows nested membership. Only the dependency route is tested here. npm's exact name/path/glob selection source was inspected, but only exact names and this generated workspace pattern were executed.

## Failure behavior and effects

The [native trace](../evidence/js-workspaces-20261124T074930267486Z/trace.json) retains exact argv, stream hashes, selected source/lock hashes, generated script events, statuses, and timings. Every script records start and completion/failure independently of the package manager's prose. The failing B records a failure and exits 7.

| Failed-B profile | Observed scripts | Aggregate status |
| --- | --- | --- |
| npm workspace iteration with `--if-present` | A succeeds, B fails, C succeeds. | 7 |
| pnpm serial recursive default | B fails; A and C do not start. | 1 |
| pnpm serial recursive `--no-bail` | B fails, C succeeds; A does not start. | 1 |
| Yarn serial topological `foreach --all` | B fails; A, C, and root do not start. | 1 |

npm's source catches each workspace error and continues the loop. It does not turn the declared A-to-B dependency into a prerequisite for that script iteration; A ran before B. pnpm's scheduler starts ready work through a FIFO queue and propagates a failed task to its transitive dependents when continuation-on-failure is disabled. `--no-bail` allows independent work to continue; it does not release A after B failed. Yarn sorts selected workspaces by identity, rescans for a ready workspace in the serial topological loop, and stops the loop when its report contains an error. These are different supported policies, not a new defect established by the study.

The native script log directly establishes who ran and the final process status. Selection membership and the reason A was blocked are separately attributed source/model interpretations. pnpm's displayed scope counts selected workspace projects, including D; it is not a count of scripts started. The model must not invent a native JSON result containing selection or block reasons that the command did not emit.

The missing-script npm run is another useful control: A, B, and C succeed before D produces an error. Selected source/lock files remain unchanged across every workspace run, while the independent effect log retains completed work. Nonzero status is not proof of no effects or rollback. No complete cache/log/global snapshot was taken. The three installs created their own local installation/lock state and are distinct from the later script commands.

The roughly 2.8 MiB private fixture tree was moved into ignored capture storage only after every command retired and a process-prefix check found no remaining reader. The [receipt](../evidence/js-workspaces-20261124T074930267486Z/retention.json) retains the original path. Native CWDs keep their historical meaning; installed links and caches are not promised usable after relocation. No historical user, recovery, world, or application state was removed.

## Models, laws, and limits

[Lean](Workspaces.lean) separates selection, dependency readiness, pending/ready work, dispatched scripts, failures, and failed-dependency blocking. It compares all 24 observed start orders, failure identities, and exit statuses. npm and pnpm use the admitted fixture discovery order; Yarn uses its name order. pnpm's serial ready queue and Yarn's serial rescan remain distinct. Six laws cover exact versus expanded selection, explicit root selection, member exclusion, required selected dependencies, dependency-agnostic execution, and empty-selection effects.

The [research decoder](WorkspacesCase.lean) deliberately admits only the captured root/four-member graph and request profiles. The executable model contains reusable graph/state functions, but general graph construction, globbing, cycles, arbitrary package names, and every scheduler policy are not qualified. Sixteen steps suffice for this five-node graph. Pre/post hooks, multiple scripts, binary fallback, dev/optional/peer edges, task declarations, resume, parallel workers, cancellation, and other hosts remain pending.

[Bend](Workspaces.bend) compares seven local continuation decisions from the four failed-B runs: whether independent C starts afterward and, for the dependency-aware profiles, whether A starts. Four laws preserve the different continuation policies. npm's A ran before B failed, so it is not counted as evidence of later dependent admission. Bend does not reimplement the complete ordered scheduler.

Replay the retained evidence after compiling the models with the pinned formal check:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/js-scripts/workspaces_conformance.py applications/evidence/js-workspaces-20261124T074930267486Z
```

Replay launches only Lean and Bend. It checks source pins, producer and stream hashes, original fixture identity, unchanged selected source/lock files, graph admission, and five invalid research inputs. Selected source files must be available at their recorded hashes in the ignored source cache. npm's three inspected files also match the installed source at qualification. pnpm/Yarn source refs and entrypoint identities are independently attributed; this is not a reproducible-build proof.

## Preserve policy and improve result clarity

Keep these programs' distinct root, script-presence, dependency-order, and continuation policies. A shared “run all” abstraction that erases them would be less useful than their existing commands. Reuse existing script and workspace mechanisms before proposing another execution service.

A focused reporting/API improvement would expose the selected scope and terminal per-package results: completed, failed, missing script, blocked dependency, and not dispatched after stopping. Derive that view from actual scheduler facts rather than an optimistic pre-run count. Preserve each program's established exit-status policy. Existing stdout/stderr already contains useful workspace-specific command and failure details; an additive structured summary should complement those streams and keep child output attributable. Review current dry-run, structured reporter, and recursive-summary interfaces before adding a new format.

The keep-current alternative is reasonable for interactive users and existing automation that understands each tool's documented policy. Better help can distinguish ordinary root execution, recursive membership, dependency closure, and topological ordering without changing commands or saved files. Any structured addition needs schema stability, wrapper behavior, caller compatibility, and honest partial/unknown outcomes; no package, lock, or workspace migration is selected.

Before adoption, test failed independent work, multiple simultaneous failures, parallel jobs already running when bail occurs, signals and retirement, cycles, scriptless dependency bridges, changed manifests during a run, nested and root-only workspaces, filters/exclusions, dry-run and existing JSON reporters, and multiple platforms. Compare both process outcomes and scoped effects. Do not infer retirement of arbitrary script descendants from a package manager's final message.

For empack, preserve target selection, prerequisites, actual work, publication, and completion separately. A progress count of selected dependencies or outputs does not establish that each one ran or finished. A terminal summary should retain completed effects and explain blocked or undispatched work. This supports the existing operation/diagnostic model and portable-authoring proposal; it does not select a generic scheduler, parallel-execution feature, or weaker dependency policy.
