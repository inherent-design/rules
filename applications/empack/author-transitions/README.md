# empack: authored policy during adoption

Adopting a proposed selection preserves existing author policy. An automatic root can accept a new exact selection without acquiring the incoming group's pin. An exact-pinned root refuses a different selection. Initial adoption also refuses a proposed group that leaves another authored root unresolved.

The [collector](probe.py) compiled a small [caller](oracle.rs) against the unchanged core library attributed by the earlier projection study, after checking the library, compiler, and eighteen core-source identities. The [capture](../../evidence/empack-author-transitions-20261126T052842353539Z/receipt.json) contains fifteen value-level calls, not observed-file or CLI operations. It uses the prior removal fixture with simple access wrappers: authored A requires B, unlisted C remains in the prior lock, exact provider IDs and digests are fictional, and revision tokens are supplied equality labels. Both members of A→B have matching complete evidence in the requested group. The earlier [removal study](../REMOVAL.md) covers different evidence and root-promotion boundaries.

## What ran

| Supplied request | Observed core outcome |
| --- | --- |
| Existing automatic A, same exact selection | Accepted; no exact record changes, no authored pin added. |
| Existing automatic A, new selection, incoming automatic or exact policy | Accepted; only A's record changes; original author intent remains equal. |
| Existing exact-pinned A, same selection | Accepted; author pin remains. |
| Existing exact-pinned A, different selection, incoming automatic or exact policy | Refused as an invalid resulting project. The incoming description does not authorize rewriting the authored pin. |
| Existing-lock adoption with different resolved runtime | Refused as a runtime mismatch. |
| Initial adoption, automatic A, incoming exact selection | Accepted; original automatic policy remains; A and B enter the first lock. |
| Initial adoption, matching authored exact pin | Accepted; original pin remains. |
| Initial adoption, contradictory authored pin or missing other authored root | Refused as an invalid resulting project. |
| Target intent with old runtime still in the supplied lock | Core `ResolvedProject::validate` refuses it. |
| Target intent and manually retagged lock runtime, automatic or matching exact pin | Core validation accepts the supplied internally consistent values. No provider compatibility was established. |
| Retagged target lock with a selection contradicting the authored pin | Core validation refuses it. |

The last four calls do **not** invoke migration composition, provider discovery, or `prepare_migration`. They deliberately show the boundary of structural validation. The fixture manually supplies `1.21.2` as the lock runtime while retaining its fictional selection. The core has no provider catalog observations from which to establish that selection's target eligibility. An accepted carrier cannot be presented as a verified runtime migration. The native engine's separate orchestration and validation obligations remain described in the [author-transition review](../AUTHOR-TRANSITIONS.md).

On every successful adoption in this profile, the whole resulting author intent equals the supplied source intent. Existing-lock adoption retains C; initial adoption has only its resolved A→B group. Binding/changed-record sets, selected version, root pin, roots, lock keys, runtime, required edges, and complete-coverage flags are observed separately. Full input debug images are compared before and after each call. This does not verify physical payload bytes, acquisition sources, native permissions, or every possible side effect.

## Models and checks

[Lean](Admission.lean) expresses nineteen scoped laws; [Bend](Admission.bend) expresses fourteen. The [research decoder](AdmissionCase.lean) admits the supplied-value fixture profile, preserving unsupported phases, versions, and missing-root/runtime combinations as refusals. It is not a production input format or universal resolver. The [replay](conformance.py) compares all fifteen retained outputs against each independent model, including nullable plans and full projected after-values. Ten reason-specific decoder controls and ten changed-observation controls exercise both interpretation and output comparisons.

The focused standard gate checked two Lean modules and one Bend file. Original streams, fixture/wrappers, caller, compiler invocation, artifact identities, and process-group retirement observations are retained. The small caller's work tree occupies 2,384 KiB on the observed Mac; it starts no daemon. The native collector is excluded from ordinary CI. Model/replay checks do not rerun the application or compiler that produced the native calls.

Owner-local replay can additionally verify the retained core library, compiler, native caller, generated fixture, and core source tree. A public-only replay explicitly excludes those private inputs and cannot claim to reproduce their provenance checks. The public model comparison uses retained streams and source identities instead. No metadata, digest, codec, identification, file-publication, or implementation-refinement proof follows from these finite models.

## API and UX consequence

Keep authored policy and an observed exact selection as separate inputs. Show a contradictory held pin as a specific policy decision; accepting observed bytes must not silently mean “replace my authored constraint.” Similarly, first-lock adoption should identify the unresolved authored roots rather than make a partial lock appear complete. Those recommendations preserve the existing checks; the deferred production UX intent remains unstarted.

For the portable target, preserve the distinction between a consistent supplied project value, observed provider eligibility, verified bytes, prepared native work, and actual publication. Reuse existing types and private preparation authority. Add a separate evidence-bearing interface only where an identified consumer needs it; do not promote `ResolvedProject::validate` into a catalog or execution certificate, or introduce another resolver to explain its scope.

Further work must compare the actual migration composer/resolver and byte-identification path, retained exact-pin failure on an incompatible target, local/URL/world variants, changed approvals, and publication/recovery. Those gaps are not filled by manually changing a runtime label. This component advances only the scoped preparation policy; complete adoption, migration, and the broader nine-application goal remain unqualified.
