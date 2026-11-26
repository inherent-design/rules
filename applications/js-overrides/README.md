# Overrides, resolution order, and saved authority

npm, pnpm, and Yarn apply different policies to the same generated dependency graph. A declared range, the rule that rewrites an effective edge, a locked selection, and installed bytes must remain separate values. A successful override command does not establish that every stricter validation mode accepts its result.

The native collection and bounded dual-model comparison are complete. Public snapshot and publication qualification are recorded separately. No production implementation or parent inventory status changes accompany this report. The [source ledger](../sources/js-overrides-selections.json) distinguishes inspected boundaries from acquired follow-up material and from actual native execution.

## Native fixture

The [collector](probe.py) reuses the checksum-pinned Node 26.13.1, npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0 tool set. It serves only generated packages from one temporary loopback registry per capture. Both parents request the leaf at `^1.0.0`; the registry offers leaf 1.0.0, 1.1.0, and 2.0.0. The direct-dependency profile instead requests that leaf directly at `^1.0.0`. Fresh Node processes read the actual installed modules and their physical filenames.

The [primary capture](../evidence/js-overrides-20261126T061550178588Z/receipt.json) contains 23 package-manager operations and 23 fresh runtime queries across seven isolated projects. The [Yarn check capture](../evidence/js-overrides-20261126T062133072880Z/receipt.json) adds five package-manager operations and four queries in one new project. The [pnpm range capture](../evidence/js-overrides-20261126T062409912906Z/receipt.json) adds three operations and three queries in another. These are workflow observations, not 61 independent integration tests.

Each capture retains the exact producer bytes that ran; the current collector adds the follow-up profiles and differs from the original primary producer. The [retained-data reader](observations.py) checks archive/file identity, native stream hashes, declared manifest preservation, author-edit continuity, and the actual module files named by fresh Node queries. It does not execute the package managers or treat installed versions as a complete lock-graph verification.

All projects use private config/cache/state paths, scripts disabled, and Yarn's node-modules linker. No HOME override, personal project, global package installation, GUI, build, or real registry publication is involved. Request bodies, package archives, stdout/stderr, author edits, project entry images, and tool identities are retained. Registry threads and recorded process groups retired. The primary registry recorded seven `/pnpm` self-metadata requests returning 404; generated dependency requests succeeded. Those are not dependency-resolution failures or evidence of a tool update being installed.

## Parent and global rules

Each graph profile first installs both parents with leaf 1.1.0. Then it authors a parent-specific rule forcing the left parent's leaf to 2.0.0. Finally it combines that rule with a global leaf rule selecting 1.0.0, and reverses their declaration order.

| Policy | npm: left / right | pnpm: left / right | Yarn: left / right |
| --- | --- | --- | --- |
| No override | 1.1.0 / 1.1.0 | 1.1.0 / 1.1.0 | 1.1.0 / 1.1.0 |
| Parent rule only | 2.0.0 / 1.1.0 | 2.0.0 / 1.1.0 | 2.0.0 / 1.1.0 |
| Global rule first, parent rule second | 2.0.0 / 1.0.0 | 2.0.0 / 1.0.0 | 1.0.0 / 1.0.0 |
| Parent rule first, global rule second | 2.0.0 / 1.0.0 | 2.0.0 / 1.0.0 | 2.0.0 / 1.0.0 |

The spellings are tool-specific: npm nested `overrides`, pnpm `parent>child` selectors, and Yarn `parent/child` resolution patterns. The original declared ranges remain unchanged during these installs. Author edits are recorded separately from tool effects; reversing npm/pnpm policy order had no subsequent project-entry effect in this profile.

Yarn's selected `Manifest` source stores resolutions as an ordered array, preserving JSON entry order on ingestion/export. `CorePlugin.reduceDependency` returns the first matching rule. The native order control agrees. Reordering otherwise equal key/value pairs can therefore change the selected graph. Preserve rule order in editors and serializers; replacing it with a general “most specific wins” algorithm would be a compatibility change, not merely cleanup. This says nothing about every pattern, source protocol, workspace, or linker.

## Direct declarations and convergence

With the leaf declared directly at `^1.0.0`, all tools first install 1.1.0. A persistent rule forcing 2.0.0 has different outcomes:

- npm refuses with `EOVERRIDE`, names the conflicting direct dependency, and leaves the captured project entries and installed 1.1.0 intact.
- pnpm and Yarn install 2.0.0 while preserving the raw direct declaration. Their authored policy changes the effective resolution; raw range versus locked selection alone cannot explain the result.

Keep npm's direct-declaration protection. Do not equate another tool's explicit override with permission to silently replace npm author intent. npm's reference overrides, aliases, linked roots, bundles, and shrinkwrap boundaries need their own comparisons; only selected source paths were inspected here.

pnpm's convergence selector is a different policy from an ordinary override. In the same two-parent graph, `leaf@` with exact value 2.0.0 does not force an incompatible version onto the `^1.0.0` edges: the observed result is 1.1.0 for both. Exact convergence value 1.0.0 instead selects 1.0.0 for both. Removing the preceding explicit override policy is part of these transitions; this is not a universal claim about lock reuse or update ordering.

The parser preserves the distinction between no range and an empty range. Its `converge` discriminator, exact-version admission, and range check matter to the interface. Do not normalize `leaf@` into `leaf`. Ordinary forcing, compatible convergence, removal, peer-group restriction, catalog references, and local source replacement are separate policies. Most of those variants remain source-only or unqualified.

## Yarn's lock-table override and stricter checking

`yarn set resolution leaf@npm:^1.0.0 npm:2.0.0` installs 2.0.0 immediately in this profile. The manifest remains byte-identical and gains no persistent `resolutions` rule; the lock now associates the original descriptor with 2.0.0. Removing the owned lock and reinstalling returns to 1.1.0 under the unchanged authored range. This agrees with the command's documented lock-table lifetime.

The additional native check distinguishes command success from stricter validation:

1. The ordinary baseline passes `install --immutable --check-resolutions`.
2. `set resolution` successfully installs 2.0.0.
3. A subsequent immutable resolution check exits 1 with `YN0078`, identifying the descriptor and incompatible selection. Captured project entries remain equal, and a fresh Node process still reads 2.0.0.
4. Regenerating the owned lock returns to 1.1.0.

This is an intentional validation distinction supported by the selected command and resolver sources, not a reproduced rollback defect. A failed check does not repair or uninstall the observed selection. Keep the existing distinction between current lock-table choice and durable manifest policy. Help and result APIs should make the install effect, policy lifetime, and validation scope discoverable without implying that the command merely edits a declaration.

## pnpm range-precedence discrepancy

The pinned source says narrower target ranges sort before broader ranges. Its comparator calls the overlap predicate in both directions, which appears unable to distinguish strict containment for overlapping ranges. This is a source-supported concern, not a proven upstream-library defect.

A separate native profile supplies two matching selectors: `leaf@>=1.0.0` selects 1.0.0, while the narrower `leaf@^1.0.0` selects 2.0.0. Both parents still declare `^1.0.0`. A broad-first install selects 1.0.0 for both; reversing those entries in the same already-installed project retains 1.0.0. The first result disagrees with the source's stated narrower-first policy. The second is a warm-project observation and does not establish fresh-root ordering.

Qualify a fresh narrower-first root, narrow-only control, configuration ordering, and lock reuse before assigning the complete cause or selecting a correction. An actual containment comparison could change existing graphs; it needs tie, overlap, protocol, and lock-setting compatibility checks. Preserve current native results and the keep-current alternative. No pnpm patch or upstream report is selected here, and current-latest upstream behavior is unverified.

## Models and evidence limits

[Lean](Overrides.lean) has 20 laws, including four state-preservation laws quantified over arbitrary model states; [Bend](Overrides.bend) has 19 checked finite laws. The [research decoder](OverridesCase.lean) admits this generated three-version, caret-range profile. The [comparison](comparison.json) binds the requests, observed results, sources, producer bytes, and controls. Run the pure owner comparison with `python3 applications/js-overrides/conformance.py`; add `--private` to verify the 14 locally retained source-cache files. `LEAN` and `BEND` select the pinned formal tools. This invokes neither a package manager nor Node, and it uses private formal output under `.build/js-overrides-formal`.

The models start each of the nine traces with no installation or manual selection. Subsequent inputs are the actual authored policy order and command arguments, including the two deliberate lock removals. Native after-state is an observation, not a model input. Both models predict all 31 command exit statuses and 28 of the 30 runtime version pairs uniquely. The remaining two pnpm range pairs are only admitted among the matching alternatives: the model neither predicts their winner nor qualifies the apparent comparator cause. Eight independently decoded Yarn lock blocks compare saved selection with the modeled lifecycle.

The retained reader verifies archive members without extracting them, generated manifests and registry catalogs, response and stream hashes, captured project bytes, author-edit continuity, and the files named by fresh Node reads. Nine invalid research inputs are refused. Five changed-input controls distinguish order, direct protection, convergence, lock lifetime, and validation; four changed-result and four raw-observation controls fail as expected. The source cache includes one update-test file acquired but not inspected; checking its digest does not convert it into an inspected or executed test.

The proposed strict-containment branch has two laws in each language. They demonstrate a narrow-first result for this exact pair, independent of input order. They do not implement general interval containment or establish a native correction. Current admission and this proposed policy remain separate functions.

## Design consequences and remaining work

Report the original declaration, applicable policy, selected locator, installed content, and policy lifetime separately. Preserve each tool's protective checks and intentional exceptions. A shared Boolean named “pinned” or “valid” cannot represent all these states.

For npm, keep the root override guard and nested override ancestry. The existing `EOVERRIDE` refusal is actionable in this fixture. An additive explanation may expose the raw edge and effective policy, but no relaxation or new lock format is recommended.

For pnpm, keep a typed selector distinction between ordinary forcing and compatible convergence throughout parse, configuration storage, effective-edge selection, and reporting. The proposed narrower-first comparator must use actual containment rather than overlap. Before adoption, isolate the native cause, define ties and incomparable ranges, inspect configuration ordering and lock-setting fingerprints, and compare old versus new graphs on explicit refresh. Keep-current is a valid compatibility choice while that work remains open. Changing the comparator silently in a routine install could select a different graph; a format change is not automatically necessary, but saved-setting invalidation and update admission require review.

For Yarn, preserve the ordered `Manifest.resolutions` sequence and its first-match rule across editors, public APIs, and serialization. Additive command/report facts should identify `set resolution` as installation plus a lock-table choice, its regeneration lifetime, and whether stricter resolution checking ran. Keep the current no-validation command and explicit check as distinct operations. A universal specificity sort or mandatory validation would change accepted behavior and needs an explicit compatibility decision. Neither is selected here.

For empack's proposed portable authoring boundary, interpretation must own ordering and source-specific policy meaning. Unknown objects cannot be alphabetically canonicalized merely because their syntax is JSON, and absent versus empty selectors cannot be collapsed without an admitted policy. Preserve the existing distinction between authored exact pins and observed selections; these JavaScript tools do not authorize adding a generic force mechanism to empack.

Source protocols, peer and optional groups, workspace roots, references/catalogs, immutable/frozen modes beyond the selected Yarn check, scripts enabled, cache failures, concurrent writers, other linkers/platforms, and full solver correctness remain unqualified. No production API, serialized format, deferred UX intent, or sibling project is changed by this study.
