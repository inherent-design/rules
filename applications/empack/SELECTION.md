# Selection policy from catalog observation to application

This source map connects empack's current assessment, synchronization, update, and runtime-migration boundaries. The [18 source selections](../sources/empack-selection-policy-selections.json) pin unchanged Git blobs at `0b4462e3032b4f09230b15329722eabefb7f574c` and name the inspected functions and test bodies. Engine test bodies described here were read, not executed by this study. The separate [core policy comparison](selection/README.md) now exercises selected preference, intent-admission, and exact-update helpers. It does not establish catalog, CLI, native publication, or complete workflow behavior. No engine build or production change ran.

The missing design question is larger than an update label: which identity and policy did the caller request, what evidence was obtained, which exact candidate was interpreted, what could be prepared against retained state, and what was actually published? These are different values in the current implementation. Preserve them before changing commands or extracting a portable API.

## Owners and transitions

| Boundary | Current owner and values | What it establishes |
| --- | --- | --- |
| Requested scope | `AssessmentRequest::scope`, CLI `run_update` and `selections` | Existing logical keys; selected author roots or selected retained dependencies. No reinterpretation of a key as search text. |
| Automatic preference | `ProjectIntent::release_policy` | Operation override, then per-root preference, then project default. |
| Catalog interpretation | `compatible::parse_page` and `ProviderResolution::verify_compatibility` | Available observations, runtime eligibility, automatic preference, exact selection checks, and bounded resource accounting. |
| Deliberate selection | `observe_updates`, `analyze_provider_update` | Exact requested or held pins, or an eligible automatic candidate. Interactive choices must have been offered. |
| Required relationships | `resolve_required_closure_observed` call and declaration scan | Required closure state and observed declared incompatibilities, under one original allowance/deadline. |
| Normalized candidate | `ProviderAdditionOutcome`, `ProviderAddInput::for_update` | A group with retained canonical provider identity, content kind, requirements, and file participation. Unknown/conflicting required relations remain explicit. |
| Native preparation | `Engine::prepare`, `prepare_change`, core `AdditionPlan` | Fresh captured basis, content/path/evidence checks, retained-project compatibility, exact requested author-pin changes, and a proposed write footprint. |
| Publication | `publish_update` and the engine's existing authorization/execution boundary | Preview, approval, execution result, actual receipt, and possibly completed versus blocked independent groups. An assessment grants no write authority. |

The called closure algorithm, transports, codecs, acquisition, native writer, and authorization rules require their own evidence. Naming a call is not a proof of its implementation or of the whole pipeline.

## Scope is a product policy

An empty assessment-key list selects explicit author roots, not every retained lock entry. Explicit keys can select retained dependencies. Duplicates and missing keys are refused before catalog queries. Exact analysis selections must belong to the selected scope and match the provider's identity type.

The CLI requires dependency names or `--all`, with `--all` selecting explicit author roots. It can construct update inputs for local/URL content as well as provider content. Provider catalog observations therefore do not describe every requested source class. `retained_inventory` describes contextual locked records outside the selected roots; it is not an independent catalog scan of those records.

The CLI's `--pin KEY=ID` requires a requested provider dependency that is also an explicit author root. Analysis can consider an exact selected retained dependency without thereby authorizing a new persisted direct pin. Core update preparation separately admits only reviewed pin changes whose keys and resolved selections agree. These are different request boundaries, not inconsistent definitions of a pin.

`update` defaults to native preparation/preview; `--apply` requests application. Preview can still perform catalog, acquisition, and cache/state work required to prepare the proposal. It is not a whole-host read-only promise. The source binds resolution to a captured revision, then captures and checks that basis again for native preparation. The resulting private prepared operation retains the engine's existing execution authority.

## Preference, exact pins, and ordering

The automatic policies are `stable-only`, `prefer-stable`, and `any`. The selected source ranks eligible candidates by:

1. Release-class preference: stable first under `prefer-stable`; prereleases excluded from automatic choice under `stable-only`.
2. The first matching game in the authored primary-plus-accepted list.
3. Publication time, newest first.
4. Exact provider selection identity as a deterministic tie-breaker.

This is not semantic-version ordering. An older stable publication can outrank a newer prerelease, and a primary-game match can outrank a newer accepted-alternative match. Preserve the authored ordering and policy in reports; do not infer a numerical upgrade from a changed opaque ID or display version.

The runtime-compatible observation ignores release-class preference but still ranks the matching authored game and publication time. The upstream observation is separately selected without the requested runtime filter. Only runtime-eligible records reach the selected payload/placement admission in this parser. Unrelated historical payloads are not installation evidence for the candidate.

After a successful catalog observation, an explicit analysis pin takes precedence over a held author pin; otherwise an automatic candidate is used. Held pins remain exact. Exact resolution still checks provider identity, content kind, and runtime eligibility, although a deliberate pin can bypass automatic release-class preference. Interactive selection checks membership in its offered runtime-eligible observations. A direct exact request is a different route and is not established by an interactive list entry.

A pin does not skip the catalog phase or turn an unavailable catalog into a successful observation. Preserve its failure and the existing exact constraint separately. Valid intent does not combine an exact pin with a per-root automatic release preference. The owning `set_provider_pin` helper clears that preference; programmatically filling both fields is rejected. The native core comparison confirms this invariant. A preference is also not an instruction to rewrite existing exact selections during sync. The [synchronization study](SYNCHRONIZATION.md) already exercises the core retention rules; reuse that evidence rather than assume every policy edit authorizes an update.

## What assessment completion means

The assessment report separates current, permitted, runtime-compatible, and upstream observations. Its row categories give manual-source, conflict, incomplete observation, unavailable target, held selection, and available change distinct precedence. Summary counts use that same classification. Display names, dates, and labels do not determine exact-selection equality.

Required closure work runs after successful selected-root observations even when all roots are held or unchanged. A local/URL-only report can instead be not-applicable. Root-local evidence failures retain useful later catalog observations under the original shared allowance; access/service failures can stop later queries. Continuing after a local error does not restore spent transfer budget or extend the deadline.

`joint.state == validated` means the required closure was validated at this boundary. Declaration scanning is a separate completeness field. A nonempty declared-incompatibility list can coexist with both validated closure and a complete assessment. This is deliberate in the source: the report does not make a placement-aware, whole-retained-inventory compatibility claim.

The source tests explicitly compose a complete assessment and a normalized provider candidate with a retained incompatible record; core update preparation then refuses it. Therefore neither an available row nor an assessment's complete flag establishes an applicable update. Preserve assessment, normalization, and native preparation results in the interface instead of turning one Boolean into their combined success.

Even successful native preparation establishes metadata/content/path/publication conditions, not actual loader startup, configuration interaction, world safety during gameplay, or implementation-level compatibility among mods. Existing ownership, world, and runtime boundaries continue to apply.

## Update and migration preserve different intent

`ProviderAddInput::for_update` retains canonical project identity, content kind, authored preference, exact pin, requirements, and file placement. Retained non-root records use their recorded roles/placements; they are not automatically promoted to direct author roots. `analyze_provider_update` refuses changing identity or kind and refuses silently removing a held pin.

Core `prepare_update_with_pins` preserves current author intent, then changes only explicitly requested author pins admitted against the existing requested roots and exact proposed selections. A refreshed exact installation and a rewritten author pin are separate changes. Existing [removal/re-adoption evidence](REMOVAL.md) is also relevant: changing a retained installation is not the same operation as restoring a direct declaration.

Runtime migration instead composes a candidate intent. It requires a current lock, selects the requested runtime, preserves the current preferred Java unless explicitly overridden, and refuses an invalid retained Java preference with a request for review. An explicit provider-project replacement resets that root's selection to automatic; a replacement naming the existing project is refused. Reuse [Java](JAVA.md) and [synchronization](SYNCHRONIZATION.md) evidence at their actual boundaries. Migration is not permission to silently unpin unrelated roots or adopt changed on-disk files.

The sync caller can revalidate prior exact provider selections against changed runtime context before looking for alternatives, and asks for implicit-library revalidation when that context changes. The full runtime resolver, replacement workflow, and pin/unpin publication need further direct comparison; this call map does not qualify them.

## Independent work and partial outcomes

`--continue-independent` reaches the engine's dependency-batch policy after discovery has produced usable normalized inputs. It does not promise an executable subset whenever a catalog or required-edge lookup fails. A shared unknown relation can prevent establishing independence even when a particular row's catalog succeeded. Preserve useful observations and the original failure rather than manufacture a subset from apparently unrelated names.

Where the native batch can prepare independent groups, author-pin changes and final receipts cover only completed groups. The source API test for a two-root pinned update gives one group broken content and verifies the other group's pin change and partial receipt. That is a defined test of an engine/API boundary, not a new observation of released CLI behavior or of catalog failure continuation.

The newly reported removal UX concern has the same relevance distinction: known blockers, potentially relevant unknown dependency evidence, and proven unrelated project health need different treatment. Its development intent remains deferred. This analysis neither changes deletion guards nor activates those fixes.

## Existing tests and evidence to reuse

| Inspected source test | Actual intended boundary | What is not established by reading it |
| --- | --- | --- |
| `changed_rows_require_joint_validation_and_pins_remain_exact` | Loopback catalog assessment before/after adding an exact author pin; closure and candidate fields. | Current execution success, native publication, or game compatibility. |
| `malformed_root_does_not_hide_independent_catalog_evidence` and the shared-transfer test | Root-local parse failure, surviving observations, and the same spent allowance. | Safe independent application or real-provider availability. |
| `analyzed_update_reuses_observed_closure_for_retained_candidate_validation` | Loopback observation counts, candidate normalization, retained conflict refusal, and unchanged encoded input lock. | Native filesystem publication or a complete CLI run. |
| `version_selection_refuses_unobserved_choices_and_keeps_the_original_deadline` | Controlled chooser, empty offers, unoffered choice, and expired shared deadline. | Real terminal interaction or a refreshed deadline grant. |
| `partial_pinned_update_publishes_only_successful_groups_author_pins` | Temporary native API project, broken one-group content, prepared/executed partial batch, and retained other intent. | Released-binary correspondence, provider discovery, or a new run in this study. |

The current core library/source studies already cover synchronization, addition/removal, layers and source projection, Java constraints, and operation lifecycles. The [JavaScript update comparison](../js-updates/README.md) supplies contrasting command and ordering policies, not empack's resolver semantics. Reuse those results without inheriting their product rules.

## Design direction and next verification

Keep one policy interpretation with explicit scope, canonical identities, automatic preference, requested exact choices, admitted observations, normalized candidate, prepared effects, and actual outcomes. Existing types already carry much of this information. First map their remaining caller gaps; a new resolver, universal report framework, or per-phase crate is not yet justified.

A portable authoring interface must preserve absent or failed observations, exact authority, file-role interpretation, and captured revision. Background catalog results can inform a draft; they cannot publish intent or install content merely because a row says change-available. Distinguish available information from a ready proposal and completed application in CLI, GUI, and API results. Keeping the current command model with better explanations is a viable alternative until a specific API/interaction defect is demonstrated.

Next compare the actual policy helpers and complete pipeline boundaries against models using discriminating cases: changed preference with retained exact selections, an explicitly different author pin, incompatible retained dependents, incomplete evidence with and without proven independence, source/role changes, stale approval, and partial publication. Identify what the retained tests already execute before adding a new case. No existing operation or scenario is promoted by this source map; formal policy composition, execution evidence, and target API decisions remain required.
