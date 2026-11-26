# pnpm: admit real backing and protect real deployment inputs

pnpm's peer contexts, wanted/current graphs, install-state metadata, physical targets, and authored patch rules have different responsibilities. Preserve those distinctions. The two highest-priority findings are a wrong live backing after patch restoration and source loss through a case-aliased forced deployment. They need different owning checks, not a broader force flag or another resolver.

## Model and current owners

| Value | Owner and meaning |
| --- | --- |
| Request, overrides, catalogs, and build policy | Author/configuration policy; ordinary forcing and compatible convergence are distinct. |
| Wanted/current lock and shape | Selected graph and installation layout policy; importer/group/architecture settings participate. |
| Peer-context and patch identity | A selected package instance is more than a bare name/version. Preserve complete role-specific identity and existing normalized patch semantics. |
| Repeat/frozen admission | CLI repeat checks and `prepare_modules_state` decide whether materialization can be skipped. |
| Actual links and backing | Physical consumer targets; a present link or named directory alone does not establish the intended selected bytes. |
| Deployment target | A separate destination with explicit replacement scope and protected source resources. |

The inspected `frozen_tree_up_to_date` considers shape, directory snapshots, bins, policy, and other state. `install_already_up_to_date` and its records-only variant provide a separate repeat path. The patch report does not identify which complete path caused every native success. Keep this causal gap explicit rather than replace production's checks with the finite model's simplified equality rule.

## Patch restoration

The [patch study](../js-patches/README.md) observes failed patch installation changing the runtime backing; after exact good patch and lock bytes are restored, ordinary install succeeds while retaining the wrong target. A separately forced install restores the intended patched runtime. Fresh processes and captured realpaths/bytes rule out a stale Node module cache in that profile. Repeated invalid-patch attempts in a separate continuation still fail; this is not general acceptance of invalid patches.

The proposed owner is materialization/reuse admission across the existing repeat and frozen gates and the actual link publication path. A failed candidate must not become a valid installed-backing claim. Preserve the prior live target while candidate patching completes where the existing materializer supports staging; otherwise retain and report explicit partial effects and invalidate unsupported reuse evidence. A subsequent success must establish the selected target under its actual policy, not merely see that a link exists or the old lock was restored.

Do not independently resolve packages in the repair path. Reuse the selected lock, complete package/peer/patch identity, existing acquisition, and verification. A conservative rematerialization path is preferable to optimistic success without admitted backing. Efficient reuse needs a real evidence basis; no marker, directory name, or new Boolean proves content by itself. Native staging, the complete causal path, mutable-directory dependencies, hardlinks, and failure cleanup remain qualification work.

## Deployment

The [deployment study](../pnpm-deploy/README.md) reproduces success after source loss when `packages/app` and `packages/APP` identify the same resource on the selected macOS filesystem. The exact spelling is refused. Source guards compare normalized spelling, then `prepare_deploy_dir` can clear the admitted target before copying and installation finish.

Add protected-resource admission before that destructive boundary and retain/revalidate its basis through mutation. Otherwise-admitted targets must not alias protected source/root/cwd resources or relevant ancestors. Treat unknown physical identity as unresolved, not distinct. Preserve ordinary early refusals. Missing targets need an admitted parent/child basis; global Unix lowercasing and a one-time canonical string are insufficient, while case-sensitive hosts may legitimately have both names.

Final output-inventory verification is useful but cannot repair source deletion that already happened. Pre-mutation protection is the primary obligation. Test actual deletion/copy with aliases, ancestry, symlinks, missing parents, permission changes, and replacement races before claiming a safe native implementation. Keep the existing source/deploy distinction: a copied executable tree can run without the source and still be unable to reinstall from its retained source-addressed manifest.

## Policy and result compatibility

Preserve forcing versus compatible convergence and absent-versus-empty selector meaning from the [override study](../js-overrides/README.md). Its overlapping-range result remains bounded, with native causation and fresh ordering controls open. A generic overlap test is not containment, but changing the comparator without qualifying configuration order and warm-lock reuse could change existing graphs. Keep the current behavior while that specific policy correction remains undecided.

A result should distinguish lock changes, materialization, direct exposure, retained backing, and deployment replacement effects. The [SBOM study](../js-sbom/README.md) legitimately reports a lock graph with optional store enrichment; a successful inventory need not establish a physical install. Preserve those semantics and format-specific relationships rather than run installs to make a report look complete.

[Workspace execution](../js-scripts/WORKSPACES.md) and [publication](../js-peers/PUBLICATION.md) retain their command-specific policies. Attribute started work, terminal results, acknowledgement, and later failure separately; a shared result view must not infer unobserved scheduler or process-retirement facts.

Keep lock/store and modules-layout formats, patch keys/normalization, peer contexts, source protocols, build permissions, and public CLI/JSON compatibility. Result fields proposed here are not a new implemented schema. Correct target admission may refuse a formerly accepted destructive alias; that is a safety correction, not permission to broaden deletion. Extra physical probes and rematerialization can cost time; measure them separately from the corrected invariant.

Use the existing retained cases for old/candidate comparison, then qualify the exact unobserved ownership boundary. Unknown gate causation, concurrency, arbitrary store damage, other hosts/linkers, hooks, and full deployment/patch rollback remain open. No production change or generic transaction framework is selected.
