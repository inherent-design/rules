# Core preference and exact-update policy

The current core already separates automatic preference, exact requested selection, retained dependency evidence, and admitted author intent. Native helper calls support preserving those boundaries. The useful interface improvement is to expose them coherently and use their existing owners; this study selects no new resolver, CLI rewrite, schema, or production change.

The [source map](../SELECTION.md) connects the larger catalog/preparation/publication pipeline. This comparison executes narrower current-core APIs using the retained library from the [projection study](../../evidence/empack-projection-20261124T063515339963Z/receipt.json). Before use, the producer checks the library, compiler, and all 18 core source identities against that capture and the current `0b4462e3032b4f09230b15329722eabefb7f574c` Git objects. Only a small caller is compiled. No Cargo or engine build runs.

## Values and actual boundaries

`ProjectIntent::release_policy` applies the operation override, root preference, and project default in that order. A missing or retained non-root key falls back to the project default at this helper boundary. That result does not admit an unknown command selection: `AssessmentRequest::scope` performs its own key validation.

An explicit pin and a per-root automatic release preference cannot coexist in valid intent. `DependencyIntent::set_provider_pin` clears the preference while setting the pin. A caller that directly fills both fields gets a validation error. A struct can represent an invalid draft or intermediate value; it does not establish valid request authority.

The [main native capture](../../evidence/empack-selection-20261125T210902424596Z/receipt.json) contains six preference cases, one rejected-intent case, and twelve update preparations. A separate [matching-evidence control](../../evidence/empack-selection-control-20261125T211013721874Z/receipt.json) adds one update case. These are 20 distinct value-level frames, not CLI commands or installed-pack transitions.

The fixture has installed A, B, and C at fictional exact identity `Version1`; only A is authored, A requires B, and C has no retained dependent. Complete dependency evidence is supplied as a fixture premise. Proposed groups have one root, except that the matching-evidence control also retains B as its unchanged prerequisite. `Version2` and `Version3` are equality labels, not version ordering or provider existence. Digests, byte counts, and semantic revision tokens are constructed values, not verified payloads or codec-computed revisions.

| Input or transition | Observed current-core result |
| --- | --- |
| Root preference with no operation override | Root policy wins. An operation override wins over both root and project policy. |
| Exact pin plus root release preference | Intent validation refuses the combination. |
| Automatic A, proposed different exact selection, no requested author pin | Preparation succeeds; author intent and root preference stay unchanged. |
| Automatic A, explicitly requested matching author pin | Preparation succeeds; the pin replaces the root preference. |
| Held A, different selection without a reviewed pin request | Preparation refuses the resulting intent/lock disagreement. |
| Held A with a matching reviewed pin request | Preparation succeeds and changes only the authorized selection-policy fields. |
| Requested pin disagrees with the proposed selection or names an unrequested key | Refused. |
| Requested pin names retained C, which is not an author root | Refused. Updating C without a new author pin succeeds without promoting it to a direct root. |
| Same exact A pin, contradictory complete required edges | Refused before pin equality could authorize anything. |
| Same exact A pin, matching retained evidence | Succeeds with no changed record. |
| A new identity, changed runtime, or different project occupying A's key | Refused by the respective update boundary. |

The caller then uses `AdditionPlan::resolve` with a synthetic revision to inspect a coherent value result. That method is not a document codec, native write, authorization grant, or observation of installed bytes. The changed-record set describes exact locked descriptions; it is not a native file-change footprint. Both successful and refused calls retain the original input values.

## Evidence equality is stronger than a pin label

The first same-pin case intentionally proposes complete empty requirements for A while the retained same exact selection says A requires B. Core `merge_evidence` refuses those inconsistent complete observations. The followup keeps the A-to-B edge and unchanged B; that same pin then succeeds without a changed record.

Do not turn the refusal into a rule that reapplying an exact pin is forbidden. Conversely, identity equality does not authorize discarding complete evidence. An interface should name the failed relationship or evidence invariant and preserve the proposed/current distinction. Reuse the existing core checks and retain unknown evidence as unknown.

## Preserved harness failures

The initial [compile attempt](../../evidence/empack-selection-20261125T210710572931Z/disposition.json) used a nonexistent `AdditionPlan::lock` getter and executed no policy cases. The corrected caller uses the public `resolve` method. A second [partial run](../../evidence/empack-selection-20261125T210753254393Z/disposition.json) emitted six preference rows, then its manually constructed pin-plus-preference fixture failed validation before any update call.

That second failure exposed an assumption in this harness, not an empack defect. The maintained caller now uses the owning setter, and the completed cohort includes an explicit negative admission case for the invalid combination. The six earlier rows match the completed capture's prefix exactly and are not counted again. Original producers, diagnostics, streams, and private artifacts remain unchanged. Added dispositions record their scope.

The generated helper module contains the earlier removal caller plus five access wrappers. Its old `main` is an unused module function; this run does not execute those removal cases or acquire their workflow coverage. Every recorded compiler/caller process group was absent at its terminal check. That is not reader custody or cleanup authority.

## Models and retained replay

[SelectionPolicy.lean](SelectionPolicy.lean), [SelectionPolicyCase.lean](SelectionPolicyCase.lean), and [SelectionPolicy.bend](SelectionPolicy.bend) contain 26 Lean and 18 Bend laws. Both models agree on 137 normalized native field projections across the 20 frames. The [conformance record](../../evidence/empack-selection-20261125T210902424596Z/conformance.json) identifies ten changed-observation sensitivity controls and six research-schema/profile refusals. These controls check the comparison's sensitivity and input boundary; they are not additional native workflows.

The model admits this frozen fixture profile. Its required-edge premise comes from the retained caller construction, not a generic graph decoder or provider observation. Optional result presence, rejected requests, root membership, exact selection, changed records, and preserved author fields remain separate. The observer reads original fields independently; it does not feed the native success/error result into the model's request.

One root preference is read from the captured Rust Debug witness. That is a bounded adapter over the pinned type, not a stable public codec. Research failure codes and message classification are also not production error codes. Unknown keys, unsupported versions, unknown preferences, and an inconsistent matching-evidence profile are refused by the research decoder.

Four Lean and two Bend laws separately model the source predicate for assessment completeness. They preserve the fact that complete required closure and a finished declaration scan can coexist with declared conflicts. Those laws are source-only. The native frames here execute no catalog or assessment pipeline, and the corresponding engine test bodies in the source map have not been rerun.

With the pinned tools and compiled model available:

```sh
LEAN_PATH="$PWD/.build/empack-selection-formal" python3 applications/empack/selection/conformance.py
```

Set `LEAN` and `BEND` when needed. The replay checks original streams, failed dispositions, fixture composition, compiler/library/source identities where present, and native/private artifact hashes. It executes Lean and Bend, not rustc, empack, a provider, or a new native collection. Artifact absence is explicit; a replay cannot become a fresh native run.

## Design and compatibility direction

Keep the existing setter and validation boundary. The source-level flat fields permit an invalid combination, but the actual valid-state rule is small and already owned. A semantic UI/API view can represent `Automatic { preference }` versus `Exact { pin }`, then lower an explicit action through the existing helper. This is an optional internal representation, not approval to change serialized project fields or every caller.

A raw editable draft can preserve an invalid pin-plus-preference document and its diagnostics. Saving that draft must not silently drop a field to manufacture valid intent. An explicit pin action can show that it replaces automatic preference; an automatic update must preserve it. The current root does not itself retain the previous preference after pinning, so a future unpin result must not claim to restore that previous value without separate evidence or an explicit choice.

Keep the current API alternative when validated callers and clear reporting suffice. If a semantic view is extracted for portable authoring, preserve exact IDs, per-operation scope, revision binding, source/placement/requirements, and errors. It must not grant native preparation or execution authority. Test the view against the same retained inputs, including invalid drafts and contradictory evidence, before adopting it.

## Remaining work

Catalog ranking and exact resolution, incomplete provider evidence, arbitrary graphs, aliases, custom file roles, requested batch scope, native update/partial publication, actual pin/unpin commands, runtime migration, codecs, recovery, other hosts, and loader/game compatibility remain separate obligations. Reuse the existing [synchronization](../SYNCHRONIZATION.md), [removal](../REMOVAL.md), and [JavaScript update](../../js-updates/README.md) studies at their own boundaries. This cohort does not complete their parent operations or the broader selection-policy review.
