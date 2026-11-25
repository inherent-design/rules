# Reading application coverage

The canonical [inventory](inventory.json) decomposes application features into operations. The [joined scenarios](scenarios.json) describe obligations across features. Reports, model laws, source selections, and captures establish different things; their links must not silently promote an operation or its parent feature.

Query the current records without running an application:

```sh
python3 applications/query_inventory.py
python3 applications/query_inventory.py --app cargo
python3 applications/query_inventory.py --feature empack.manual-pending
python3 applications/query_inventory.py --feature cargo.freshness --json
```

Human and JSON output use the same derived facts. The query does not write another coverage ledger. Counts describe inventory references, not completion, test quality, implementation correctness, or a percentage of the goal.

## Three different relationships

| Record | What it establishes |
| --- | --- |
| Operation references | The operation explicitly names a model, laws, source comparisons, observations, controls, or UX assessment. Its recorded status and proof premises still matter. |
| Component operation slice | A retained study relates to a named part of that operation. `operationSlices` gives the exact boundary; `remaining` preserves the larger obligation. |
| Related component only | The study informs the feature, but exercises none of its declared operation boundaries. `relationOnly` explains why the relationship is useful. |

For example, the saved-build study relates to exact input association and continuation. Its ordinary download scan does not establish scan-limit or weak-assertion behavior. The bootstrap's controlled child lifecycle informs terminal supervision, but does not qualify native foreground transfer or runtime-tree cleanup. That component has no operation slice under `empack.process-console`.

A pending operation can therefore have useful scoped evidence. An operation with no inventory references is a discovery target; the query does not prove that no relevant implementation or evidence exists elsewhere. Review the retained reports before collecting another fixture or assigning a new status.

## Reference fidelity

Run the existing checker after editing inventory links:

```sh
python3 applications/check_inventory.py
```

It checks that declared module and evidence paths exist, simple law names occur in the declared model modules, component slices name actual feature operations, and empty slice maps have an explicit relation-only explanation. References are repository-local and cannot escape the repository. File prefixes are application-relative, including helper references such as `prism/cleanup_conformance.py:…`; an unqualified helper basename is not resolved by guessing its owning directory.

Narrative control descriptions remain narrative. A file fragment or named field identifies a place to inspect; the checker does not execute that control or prove its meaning. Law-name lookup is not Lean/Bend verification, and a valid path is not source/native conformance. Use the actual model checks and profile-specific replay where relevant. Completion still requires the full intent's requirement audit.

The checker's negative controls must fail for the intended reason. A missing model cannot pass its negative control merely because an unrelated component was also invalid. Scope and evidence statuses are not inferred from link counts, a parent feature, or a joined scenario.

## Advancing the study

Keep unresolved operations visible. Choose the next investigation from the actual implementation, existing evidence, domain importance, and missing host distinctions. Preserve each application's purpose and policy; a shared host concept does not supply application behavior.

Before advancing a recorded status, identify the particular API or workflow, admitted version/host/input profile, observed or source-derived transitions, laws and their premises, meaningful controls, UX implications, and remaining verification. Reuse existing evidence when it answers the question. A bookkeeping repair or additional slice link alone changes no application evidence status and qualifies no broader workflow.
