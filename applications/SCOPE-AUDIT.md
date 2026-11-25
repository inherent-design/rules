# Application study: remaining scope and evidence gaps

The nine-application study remains incomplete. Its strongest result so far is a set of attributable component decisions and counterexamples, with a bounded shared-engine portable-authoring join. The next work must connect missing application policies and workflows, and reconcile the target designs. More proof counts or repeated happy paths would not establish that result.

This is an interim review of the selected intent against the canonical [inventory](inventory.json), [scenarios](scenarios.json), [comparison](COMPARISON.md), and their linked reports. The inventory baseline is application commit `8d6fcb5ad151f2b526ff283656a511a36fd1a53f`, on 2026-11-25. It is not a fresh verification of every implementation, source pin, or native capture. No parent status changes, production edits, application launches, or new evidence collections accompany this review.

## What the current records establish

The inventory contains nine applications, 208 feature families, and 972 operations. There are 301 operations with direct or scoped-component references and 671 without such links. Of the families, 111 have operation-linked evidence; another has related component evidence without an operation slice. These are reference counts, not completion counts. Pending operations can have useful partial evidence, and unlinked operations can have relevant material elsewhere.

Recorded operation statuses remain 799 pending, 143 native-observed, 22 source-modeled, and eight proposed. Neither native-observed nor a passing formal model establishes all inputs, hosts, consumers, or joined behavior. The [coverage guide](COVERAGE.md) explains these distinctions and how to query the current records instead of treating this dated snapshot as a live ledger.

| Application | Operations with references / total | Main remaining policy or workflow obligation |
| --- | --- | --- |
| empack | 111 / 264 | Provider identity, evidence and selection through assessment, sync, update, migration, release production, and instance application. Preserve native authority across portable boundaries. |
| npm | 28 / 101 | Complete resolution/source semantics and workspace release composition; separate account/registry authority from the existing loopback publication observations. |
| pnpm | 21 / 108 | Store/link topology and workspace selection through build permission, execution, and deployment. Existing alias, patch, peer, and deployment cases cover selected boundaries. |
| Yarn Berry | 25 / 76 | Project/linker and cache identity through constraints, patching, version decisions, and publication. Preserve reference identity and partial effects rather than infer convergence. |
| Mod Organizer 2 | 12 / 66 | Installation and profile selection through effective overlays, plugin order, tool launch, and output capture. Existing source-method fixtures do not qualify Windows/USVFS behavior. |
| Prism Launcher | 18 / 77 | Actual pack import/update through component/account/runtime admission, launch, cancellation, and user-state preservation. Controlled Qt helpers do not establish the complete launcher workflow. |
| Cargo | 26 / 79 | Source/lock/configuration and selected units through build-script freshness, execution, artifact ownership, and cleanup. Existing compile/install/package cases leave other publication and toolchain boundaries open. |
| restic | 31 / 68 | Backend/repository authority and concurrency through policy-selected retention, reclamation, restore, and interruption. Explicit-ID local fixtures do not establish remote or concurrently owned repository safety. |
| VS Code desktop/web | 29 / 133 | Documents, workspace/trust/configuration, extensions, tasks, search, and external changes as joined lifecycles. Language/debug/SCM/remote/agent surfaces need their own policies and capability evidence. |

The initial inventory is a research decomposition, not proof that each command exists with that spelling in every pinned release. Native help, selected sources, and plugin/version profiles must admit a feature before its behavior is claimed. Preserve unsupported or unavailable profiles explicitly; do not infer them from a blank evidence field.

## Review against the intent

| Required result | Present basis | Remaining obligation |
| --- | --- | --- |
| Feature inventories and exact profiles | All nine applications are decomposed; initial help/source/version bases are retained. | Confirm each selected feature against its actual version and interface. Review missing domain features without growing the inventory by analogy alone. |
| Values, relations, owners, and transitions | Feature questions and scoped reports distinguish many important entities. | Complete each application's model across features, including failed publication, retry, and surviving children or retained assets. A list of commands is not a domain model. |
| Executable rules and Lean laws | Linked model modules express selected current and proposed decisions with premises. | Cover missing meaningful boundaries and compose existing rules. A projection proven in isolation is not an implementation-refinement proof. |
| Source/native comparisons and counterexamples | Retained streams, source identities, independent observations, and controls support bounded findings. | Qualify missing entry points and hosts, or state the exact unavailable observation and how it would falsify the claim. Do not rerun unchanged fixtures for a larger count. |
| UX and API consequences | The comparison records candidates and keep-current alternatives for all nine applications. | Tie remaining operations to actual user expectations, visible timing/effects, affected callers, and verification. A reporting label alone cannot repair an ambiguous command policy. |
| Cross-feature workflows | Fifteen scenario records retain components and explicit remaining work. | Establish the missing joins; none of the scenario parents claims full qualification. Retain partial native/source/model status rather than combine independent successes into an unobserved run. |
| Host integration | Shared witness mappings and versioned host contracts exist. | Admit application-specific witnesses under their real preconditions. Filesystem identity, content identity, saved revision, and execution authority remain distinct. |
| Coherent empack target | The [target model](empack/README.md) describes drafts, images, interpretation, selection, assets, work, output, delivery, and native execution. | Reconcile the remaining policy/API families and map decisions to affected current types and callers. Complete the implementation sequence and falsifying checks before production adoption. |
| Improvements beyond empack | Per-application candidates and compatibility considerations are present in the comparison. | Keep each proposal meaningful in its own product; distinguish confirmed defects, policy choices, and proposed alternatives. Check current upstream status before an upstream change. |
| Completion and operations | The canonical inventory, scope checker, retained evidence, and owner boundaries are in use. | Perform a final requirement and evidence review. Keep one task checkpoint, preserve protected data, and leave implementation and release activation separate. |

## Reuse the joins already established

The [portable-authoring join](empack/PORTABLE-JOINED.md) already exercises a shared research engine through import, invalid and valid save/reopen, metadata/path edits, captured-image Prism export, and finalized browser downloads. It is not necessary to build another demonstration of that same sequence. Production project encoding, more providers and recipes, custody of signing material, storage limits, concurrent writers, crash behavior, and actual consumer launch remain separate obligations.

Earlier component reports describe what their own run did not establish. A later component can fill part of that gap without changing an earlier receipt or making its original observation broader. Current summaries should link the later evidence instead of presenting the earlier limitation as a newly missing experiment. Frozen producers, failures, and raw records remain unchanged.

The other scenario records leave these specific joins open:

- empack: reference release and enrollment through instance update; restricted acquisition through publication; bootstrap selection through real runtime supervision.
- npm, pnpm, and Yarn: workspace publication; filtered task/deployment; patch and version-decision release composition.
- Mod Organizer 2 and Prism: profile/tool output and pack/runtime transitions at the actual supported host boundary.
- Cargo: build-script and generated-backing freshness through the selected build/execution lifecycle.
- restic: policy-selected retention, reclamation, and restore with concurrent-owner and backend distinctions.
- VS Code: edit/save/external changes, trust/agent/task admission, and workspace search/edit with actual backing and process effects.

These are not all-or-nothing acceptance matrices. Compose a bounded current rule and a discriminating failure case at each join, then record what the run actually exercised. A source-only method, simulated host, native component, and full product workflow remain different evidence categories.

## Work order after this audit

1. **Close the empack selection-policy gap first.** Trace provider evidence, exact identities and pins, assessment scope, sync retention, deliberate update, runtime migration, and independent partial application as one policy map. Reuse [synchronization](empack/SYNCHRONIZATION.md), [removal/re-adoption](empack/REMOVAL.md), [source projection](empack/SOURCES.md), and [JavaScript updates](js-updates/README.md) at their existing boundaries. The inventory has no direct study links for provider-policy, assessment, or update. Check existing current source/tests before choosing any new fixture. The output should define what each request promises and what each result can actually claim, not start another resolver or implement the deferred CLI goal.
2. **Connect author selection to release and consumer effects.** Trace the missing release-production, delivery, and instance transition APIs. Reuse archive, world, ownership, channel, and bootstrap evidence. Keep author intent, prepared inventory, signed metadata, retained bytes, installed ownership, and actual launch separate. This is the point to determine which small local join would add evidence beyond the existing studies.
3. **Continue each comparator in coherent feature groups.** Use the application-specific gaps above and the canonical operations. Reuse prior models and identify the smallest missing policy or host distinction before a native run. Do not reduce the broader selected scope to the features most convenient to execute on this Mac.
4. **Reconcile the target designs as the groups finish.** Update current and proposed types, ownership, operation meaning, caller/API consequences, compatibility, keep-current alternatives, and checks together. Preserve the selected clean break for a future empack project format; comparator compatibility and native recovery authority have different obligations. No production migration framework is implied.

Before collecting another case, name the unanswered claim, its existing evidence, the discriminating observation, its host/profile and effect scope, and the decision it could change. Prefer a source comparison or retained-data replay when it answers that question. A new executable probe should add information, not reproduce a successful predicate or compensate for a missing inventory link.

The full study remains active. This audit changes the order of investigation and clarifies evidence reuse; it does not narrow the intent, approve a production design, or declare the pending operations complete.
