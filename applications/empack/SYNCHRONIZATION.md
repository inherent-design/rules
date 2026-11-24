# empack synchronization and retained selections

Synchronization decides which changed requests need resolution and which proposed differences are justified. It does not treat an automatic dependency as permission to select a different version, a removed root as deletion authority, or an omitted loader pin as a request to upgrade the locked runtime.

## Actual core observations

The [caller](synchronization_oracle.rs) uses the unchanged core library from the earlier [projection study](../evidence/empack-projection-20261124T063515339963Z/receipt.json), checking the artifact, compiler, and source identities before reuse. The [receipt](../evidence/empack-synchronization-20261124T095654053890Z/receipt.json), [commands](../evidence/empack-synchronization-20261124T095654053890Z/commands.json), and [24 observations](../evidence/empack-synchronization-20261124T095654053890Z/observed.stdout) identify the executed cases. One small caller is compiled; the engine is not built.

The base graph has an explicit root A, required dependency B, and retained unlisted record C. The selected Fabric loader is exact; the request initially omits a loader version. Provider IDs, version IDs, file assertions, and semantic revision tokens are fictional. `Version1` and `Version2` are equality labels, not evidence of chronological order or provider existence. Before/proposed snapshots pair the **current request** with the prior/proposed lock; the before snapshot is not a saved old author intent.

| Controlled proposal | Observed result |
| --- | --- |
| Metadata change, exact records retained | Accepted; no affected roots or changed records. |
| Automatic root receives a different exact selection | Refused as a change to a valid retained selection. |
| Root A removed, all old records retained | Accepted. Removing a root does not itself remove its installation record. |
| Removed root A or unlisted C discarded | Refused; synchronization cannot discard prior installations. |
| A's pin deliberately changes | A needs resolution; its changed exact record is accepted. |
| A changes and required implicit B changes with it | Accepted within the proposed required closure. |
| Unchanged C still requires the changed B | Refused until the retained dependent receives explicit resolution. |
| B is also a valid explicit root | Its protected selection cannot change merely because it lies in A's closure. |
| New root D requires existing B | D is admitted; unrelated new E is refused. |
| Proposed required graph gains an in-scope cycle | Accepted without nontermination; the unchanged B record is not listed as changed. |
| B's coverage changes inside A's justified closure | Accepted, but B is absent from the changed-record set when its dependency record is unchanged. |
| C's coverage, edges, or absent-to-empty edge entry changes outside scope | Refused as a retained-record metadata change. |
| Loader request remains unpinned but proposed loader changes | Refused; the still-valid exact runtime is retained. |
| Author explicitly changes the loader requirement | Fresh scope is admitted when the proposed runtime satisfies it. |
| Additional accepted game-version policy changes | Provider roots need fresh resolution; the candidate selection can differ. This is not proof of actual game compatibility. |
| Persisted fuzzy search plus changed overall semantic revision | Fresh scope is admitted; a different exact selection is permitted within it. |
| Same search revision plus a different selection | Refused as an unjustified retained-selection change. |
| Unique old provider label renamed | Identity, selected record, coverage, and graph references survive rebinding. |
| Requested new label is already occupied by another provider | The old label is not stolen; the proposed project fails source/identity validation. |
| Two requested aliases claim one retained identity | Rebinding refuses the ambiguity rather than returning a partial mapping. |

Twenty-two cases reach scope validation. One stops at proposed-project validation, and one at rebinding. Eleven pipelines return a scope result; thirteen return an error. These are pure value-level calls. No download, physical installation, native publication, or game operation occurred.

## Three distinct scopes

**Affected roots** describe requests that need fresh resolution. The actual policy includes changed runtime or accepted game versions, unsatisfied root selection, and a persisted `Search` whose overall semantic revision changed. An automatic source with a still-valid exact selection does not become affected just because another version exists.

**Allowed closure** follows the proposed required edges from those roots. It permits justified changes to implicit prerequisites while preserving valid explicit roots and rejecting changes that leave unresolved retained dependents. It does not prove that the provider supplied complete or correct compatibility metadata.

**Changed records** enumerate changed logical dependency records. They are not the complete lock delta or the set of copied files. Graph-only, coverage-only, runtime, revision, and label changes can have different footprints. The `coverage-inside` observation changes A's record and B's coverage but reports only A as changed.

The [source ledger](../sources/empack-synchronization-selections.json) pins `0b4462e3032b4f09230b15329722eabefb7f574c`. The inspected production `SynchronizationCandidate` paths consume the scope check, encode the **whole proposed lock**, and compare full lock equality when deciding preservation. They do not publish only the `changed()` set. This study therefore establishes a reporting distinction, not a dropped-publication defect.

The recorded-only candidate also refuses reuse when changed intent still contains an unresolved search. It requires fresh resolution. The pure scope accepting a supplied search result does not establish that an ordinary CLI command silently queried a catalog or updated a real pack. Provider lookup, selection policy, content evidence, and native approval remain separate obligations.

## Preserve record presence when it matters

An absent required-edge entry and a present empty entry have the same outgoing adjacency in this fixture, yet retained-lock comparison distinguishes their stored shape. Both examples have explicitly complete coverage; absence must not be relabeled as unknown coverage merely to explain the result.

The [initial capture](../evidence/empack-synchronization-20261124T095253864370Z/disposition.json) lost that distinction when projecting both to an empty list. It could display two apparently equal inputs with different scope outcomes. The revised producer adds `edgesPresent`; the [capture review](../evidence/empack-synchronization-20261124T095654053890Z/projection-review.json) verifies all 24 outcomes unchanged after this observation correction. The original source, warning, streams, and result remain retained. This was a research adapter defect, not a product fix.

## Models and verification

[Lean](Synchronization.lean) models the fixed provider-mod profile: exact runtime retention, provider/search roots, unique alias rebinding, proposed closure, retained records and metadata, retained dependents, and justified new nodes. Fifteen laws include cyclic reachability, unchanged identity through aliasing, root demotion, stored edge presence, and the limits of the changed-record set. Unsupported research keys are refused rather than silently dropped by the finite-key model.

The [comparison](synchronization_conformance.py) matches all 24 pipeline outcomes, affected/changed sets, normalized records, and failure stages against Lean. Its [decoder](SynchronizationCase.lean) restricts the input to captured roles and rejects six unsupported research cases. Native diagnostic strings are classified into research reasons; those names are not new production error codes.

[Bend](Synchronization.bend) independently checks six local scope laws and 22 aggregate scope decisions. Its adapter traverses the proposed graph separately, using request/prior/proposed inputs rather than native affected/changed outputs to construct scope. Alias normalization and pre-scope failures remain the Lean comparison's responsibility. Neither model implements a catalog resolver or codec.

These cases use Modrinth-shaped IDs, mod content, common/required participation, automatic placement, and version-only dependency-record changes. Same-pin file assertion changes and additive negative evidence have additional source rules; the research decoder explicitly excludes them. Unknown coverage, other content kinds/providers, selector/file policies, arbitrary labels, and larger graphs require further profiles or general proofs. A research refusal is not a claim that production rejects those capabilities.

The raw Rust debug records are bounded equality observations, not a proposed portable wire format. Synthetic semantic revisions exercise equality conditions; they do not qualify canonical document hashing. The private caller binaries and temporary homes occupy about 2.4 MiB per capture, with the attributed core artifact reused. Both runs retired; neither selected user state. Ordinary rules CI runs pure models and retained comparisons, not the compiler or application collector.

## Design and UX direction

Keep synchronization, explicit update, and deliberate removal distinct. When a dependency is held, explain whether it is an unchanged explicit request, a retained prerequisite, a shared dependency needing dependent resolution, or an unlisted record retained without deletion authority. Do not present “not affected,” “not changed,” and “no lock changes” as interchangeable results.

Candidate structured reports should expose resolution roots, record changes, graph/coverage changes, runtime changes, and alias rebinding as separately attributable facts. This need not become another scheduler or resolver. First improve the names and views of existing facts; retain current scope checks and full-lock publication. The keep-current implementation remains valid.

Use “selection change” or “runtime change” when only identity inequality is established. Calling a change an upgrade or downgrade requires the relevant catalog/version policy; opaque provider IDs do not supply that ordering.

For the current/0.9 target, preserve logical authored labels, canonical provider identity, exact selection, file assertions, coverage, required edges, and materialized bytes as separate values. Label edits must not lose graph references or invent a new provider identity. A prepared resolver result needs the captured intent/runtime/selection-policy basis before admission. Search results specifically depend on the policy's whole semantic revision today; a portable cache cannot silently replace that rule with query-text equality.

If a narrower search invalidation policy or new graph normalization is proposed later, compare it explicitly with current behavior, define its author-visible meaning, and qualify the affected codec/caller paths before adoption. This study selects no production change or migration mechanism. The deferred removal/re-adoption and update-preview UX implementation remains unstarted.

Further work must connect real provider evidence, nonempty content materialization, codecs, approval, and publication to these scope rules. The earlier [document/approval tests](DOCUMENTS.md) cover different native boundaries; neither band alone proves the complete joined workflow or a complete feature family.
