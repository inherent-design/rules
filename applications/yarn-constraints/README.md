# Project constraints, explicit fixes, and convergence

This band investigates Yarn Berry 4.19.0's Modern JavaScript project constraints. It separates a callback's requested manifest values, reported conflicts, applied edits, repeated evaluation, and the command's final status. It is not a dependency-compatibility solver, Prolog study, arbitrary-rule verifier, or complete constraints feature qualification.

## Current model and source

The [source selection](../sources/yarn-constraints-selections.json) pins `commands/constraints.ts`, `ModernEngine.ts`, and `constraintUtils.ts` at `62edcb0e2f62c93b7b2ec2ef6a79edeaf2e06b3c`. The command restores project install state, selects the Modern engine when user configuration supplies a constraints callback, and processes its report. A workspace's `set` or `unset` requests a value; it does not immediately persist that field. Explicit errors and conflicting requests remain separate from unambiguous edits.

Without `--fix`, the command reports unmet fields. With `--fix`, it applies unambiguous changes and awaits changed workspace manifests before another pass. It does not roll back an earlier successful write when a later callback fails. The inspected loop selects ten passes for fixing and one for checking. It has no early break on an unchanged report. Its final status comes from the last report's remaining errors, computed before that pass's writes; a final write need not establish that the updated image satisfies the rules.

Proposal aggregation uses JavaScript map-key identity. The later current-value comparison uses `JSON.stringify`. Two object values with the same serialized meaning can therefore count as conflicting proposals when they are different references. Reusing the same object reference produces one proposal. This is a distinction between the request representation and manifest-value meaning, not a generic JSON or JavaScript defect.

## Executed fixture

The [collector](probe.py) reuses pinned Node 26.13.1 and Yarn 4.19.0. It creates six private dependency-free root/child projects, disables Yarn networking, scripts, telemetry, and shared caches, and installs only their workspace structure. The [receipt](../evidence/yarn-constraints-20261124T232837924143Z/receipt.json) records 23 commands, including 17 constraint commands, with every owned process group absent afterward. Generated work occupies 264 KiB, excluding the reused tools.

Each owned callback logs its entry image before proposing values or throwing. There are 143 workspace visits. This measures callback inputs, not disk writes at every pass or process-wide filesystem behavior. Independent before/after captures retain manifests, lock bytes, and the callback source. Checking leaves those measured files unchanged; the callback itself deliberately appends its trace, so general side-effect freedom is not claimed.

| Rule and operation                                      | Observed result                                                                                                                 |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Set the root and child licenses                         | Check reports errors. Fix writes both licenses and returns 0; the next check succeeds.                                          |
| Stable license rule under fix                           | The callback still runs ten times. Visits after the first see the requested licenses.                                           |
| Conflicting root license plus unambiguous child license | Fix preserves the child edit, leaves the root conflict unresolved, and returns 1.                                               |
| Increment the root counter until it reaches 12          | Fix returns 0 with the saved counter at 10 after ten passes. An immediate check returns 1 and preserves that image.             |
| Fix that chain again                                    | The counter reaches 12; evaluation nevertheless continues through ten passes. The next check succeeds.                          |
| Throw when a previous pass has saved counter 1          | Fix returns 1 on its second invocation, with counter 1 still present on disk.                                                   |
| Assign one shared object twice                          | Fix succeeds and saves the object.                                                                                              |
| Assign two structurally identical object literals       | Check and fix report a conflict; fix preserves the measured files and returns 1. The diagnostic displays identical JSON values. |

The [observation checker](observations.py) connects streams, callback traces, and final images. The capped-success/later-failed-check sequence is an executed outcome, not solely a source hypothesis. It demonstrates that this command's success does not always establish convergence for an admitted project rule. It does not establish corrupt manifests, unsafe dependency resolution, or lost user edits.

Six unmet checks selected with `--json` contain one human guidance line followed by JSON diagnostic records. The command describes this option as an NDJSON stream, but these stdout streams cannot be parsed wholly as NDJSON. The callbacks write only their owned trace file; they do not supply this prelude. The source sends guidance through a human `StreamReport` separately from the JSON tree. A later callback exception also emits a plain stack, whose outer CLI formatting is not modeled here.

The first setup used the unsupported spelling `--mode=skip-builds`. Yarn rejected it before any rule ran. Its original producer, unchanged images, error, and retired group are retained in a separate capture. The [correction record](../evidence/yarn-constraints-20261124T232837924143Z/setup-correction.json) binds that failure to the corrected `--mode=skip-build` run. No completed constraints workflow was repeated or reattributed.

## Formal comparison

[Lean](Constraints.lean) and [Bend](Constraints.bend) model the six selected rules and the inspected command loop. Their 16 Lean and eight Bend laws preserve check-only images, metadata conflicts, independent safe edits, earlier writes on a later failure, capped success without convergence, and reference-versus-value equality. These are scoped rules, not executable implementations of arbitrary callbacks or the whole engine.

The [research decoder](ConstraintsCase.lean) admits only this fixture's bounded modes and values. The [pure replay](conformance.py) compares both models with all 17 command outcomes, plus Lean's predicted callback-entry traces. Root counter/license and visited child license are measured there. Object presence has final disk observations; no per-pass object-value observation was recorded. The models also predict the human-guidance branch for all 17 outcomes. Eight malformed research inputs refuse, and ten changed outcome/input/presentation fields are detected. The [comparison receipt](../evidence/yarn-constraints-20261124T232837924143Z/conformance.json) retains inputs, measured outputs, source identities, and limits. No Yarn command runs during replay.

A separate proposed terminal rule validates the resulting image before announcing success. Both models reject the capped chain under that rule while retaining counter 10. This is pure candidate behavior, not a patched Yarn run. Actual re-evaluation can execute user code, throw, observe changed configuration or graph state, and have side effects; those boundaries require their own qualification. A final check must not imply that earlier edits were undone.

## Improvements and preservation decisions

Preserve explicit `--fix`, actionable field diagnostics, source locations, conflict refusal, and independent safe fixes. A conflict or later callback error can coexist with useful saved edits. Report that partial result instead of presenting nonzero status as proof that nothing changed.

The current `AnnotatedError` retains formatted `text` and `fixable`; the JSON tree then carries those strings and workspace labels. A possible internal extraction is a typed `ConstraintIssue` with kind, workspace, parsed field path, expected/current value, fixability, and contributing rule locations. Preserve custom callback errors as a distinct text-bearing case. The evaluator would return issues and proposed/applied edits; human and machine presenters would format the same facts. This representation is an unimplemented design candidate, not a property proved by the current fixture models. Keep existing output available or introduce an explicit format version, and test deletion versus null, conflicting values, callback errors, and partial persistence before adoption.

Keep JSON stdout parseable. Emit fix guidance as a documented structured record or send human guidance to stderr, while retaining the useful field and source-location diagnostics. Review consumers before changing record shapes. The exception path needs a separate outer-CLI review; the observed stack is not silently classified as a normal tree diagnostic.

The strongest improvement is an explicit convergence outcome. After exhausting the write budget, validate the captured final image or report that validation remains incomplete. Return success only for the promised condition. A possible human message is “Reached the 10-pass limit; project rules still fail. Review the saved changes before running again.” Actual changed-field counts, unresolved conflicts, iteration limits, callback failures, and unknown persistence need separate facts. Do not call a copy of the last pre-write report a post-write check.

A related simplification is to stop when a complete report proposes no changed manifest and the relevant inputs are stationary. Current stable rules still receive ten invocations. Early stopping must account for the callback/configuration and project graph, not only one field. It can change behavior for deliberately stateful callbacks, so document the intended contract and test that compatibility cost. Keeping the current bounded repetition but correcting success reporting is a narrower alternative.

For value aggregation, consider a validated manifest-value representation and a separate deletion sentinel. Coalesce structurally equivalent supported values before declaring a conflict, while retaining every contributing source location. Undefined deletion must stay distinct from a present `null`; arbitrary objects, prototypes, functions, and unsupported values need a deliberate policy. Retaining reference-based aggregation is possible, but then the API and diagnostic should explain why two equal-looking values conflict. Changing equality or convergence policy is a production decision, not selected by this study.

These candidates affect Modern engine reports, command-loop termination, and presentation. They should not require rewriting project manifests or lockfiles as a migration. Review plugin/API callers and existing scripts that interpret status or callback count. Qualify real patched execution with the same cases, deterministic and stateful rules, failures during manifest persistence, multiple changing fields/workspaces, external file changes, and dependency edits requiring a refreshed install. The current license/counter/object fixtures do not qualify those wider paths.

For empack and other authoring interfaces, the useful distinction is between proposed edits, saved effects, and a verified postcondition. A generic “apply succeeded” flag cannot substitute for all three. Preserve concise ordinary output, with complete structured details and a safe next step when edits remain or their result is uncertain. No production application is changed here.
