# Deduplication, version selection, and installed copies

The same “dedupe” label covers different selection policies. In these controlled projects, npm can select a newly advertised version while reducing copies, or update a version without reducing copies. Yarn chooses among saved locator candidates. pnpm preserves seeded selections where possible in the tested profiles. All three preserve the exact transitive constraint and the root author manifest. This is source-backed, bounded behavior, not a confirmed package-manager correctness defect or a general solver comparison.

## Versions and native inputs

The [main capture](../evidence/js-dedupe-20261125T120841191141Z/receipt.json) pins Node 26.13.1, npm 11.20.0, pnpm 12.21.0, and Yarn Berry 4.19.0 on this Mac. It uses six generated package archives and an owned loopback registry. The leaf publishes versions 1.0.0, 1.1.0, then 1.2.0. Two parent packages require either an overlapping `^1.0.0` range or exact `1.0.0`, and `^1.1.0`. Scripts are disabled and no peer/optional dependency, workspace, alias, or override is present.

Each project first installs one parent while only leaf 1.0.0 is advertised. It adds the second parent when 1.1.0 appears. Then the registry advertises 1.2.0 before preview, application, and a second preview. A fresh Node process reads each parent's actual resolution, package manifest, and source bytes before and after dedupe. The independent observer also reads the captured lock and file image.

The initial ordinary npm install had already consolidated the overlapping ranges at 1.1.0. That is a valid observation, not evidence that `npm dedupe` performed consolidation. A [separate control](../evidence/js-dedupe-20261125T121049582647Z/receipt.json) seeds npm with `--install-strategy=nested` and then invokes ordinary hoisted dedupe. This produces a positive consolidation case without rewriting the initial capture. pnpm explicitly uses `autoDedupe: false` to retain the two initial resolutions; it is a fixture policy, not a claim about its default.

| Tool/profile | Before A / B | After A / B | Copies before → after | Newly advertised version used? |
| --- | --- | --- | --- | --- |
| npm, ordinary overlapping setup | 1.1.0 / 1.1.0 | 1.1.0 / 1.1.0 | 1 → 1 | No. There was no duplicated package node to target. |
| npm, nested overlapping setup | 1.0.0 / 1.1.0 | 1.2.0 / 1.2.0 | 2 → 1 | Yes. |
| npm, exact A | 1.0.0 / 1.1.0 | 1.0.0 / 1.2.0 | 2 → 2 | Yes, for B. A's exact requirement remains satisfied. |
| pnpm, overlapping setup | 1.0.0 / 1.1.0 | 1.1.0 / 1.1.0 | 2 → 1 | No. |
| pnpm, exact A | 1.0.0 / 1.1.0 | 1.0.0 / 1.1.0 | 2 → 2 | No. |
| Yarn, overlapping setup | 1.0.0 / 1.1.0 | 1.1.0 / 1.1.0 | 2 → 1 | No. |
| Yarn, exact A | 1.0.0 / 1.1.0 | 1.0.0 / 1.1.0 | 2 → 2 | No. |

Both root parent packages stay at authored version 1.0.0. “Exact A” in the table refers to A's leaf requirement, not a change to A's own version.

“Copies” here means distinct canonical leaf entry paths seen by ordinary Node resolution. It is not allocated storage, cache count, content-addressed blob count, or a complete installed graph. Equal package bytes do not collapse peer contexts or authorize deleting another program's cache.

## The source policies differ

The [source ledger](../sources/js-dedupe-selections.json) identifies exact revisions, inspected ranges, and cached bytes. Three selected npm files match the installed files byte-for-byte. pnpm and Yarn source pins are separately attributed; a reproducible build correspondence to their native executables is not established.

npm's `Arborist.dedupe()` counts duplicated names in the virtual tree, falling back to the actual tree. It calls `reify` with `preferDedupe: true` and `update: { names }`. The CLI sets `save: false` to keep the author manifest. This is more than deleting an identical nested directory: the reifier can obtain another version for a targeted name. The selected `Node.canDedupe()` method separately protects bundle/shrinkwrap, replacement eligibility, and requested versions. The complete reifier and arbitrary constraints are not modeled here.

Yarn's `dedupeUtils` builds candidates from stored descriptor-to-locator resolutions, excludes virtual descriptors, applies requested patterns and persistence rules, and asks the resolver for satisfying sorted candidates. Its highest strategy reuses saved locators. Candidate existence in the lock is different from current file availability or a promise that no fetch can occur. This warm-cache run made no registry request during preview or application; other resolvers, missing archives, plugins, and PnP are outside the profile.

pnpm sets `UpdateSeedPolicy::KeepAllResolveAll`, disables the prefer-frozen path, and separates lock-only check from the installation pipeline. Its actual preview explains the proposed 1.0.0 → 1.1.0 edge and removed package snapshot. The full resolver ranking is not reconstructed from that one policy enum. The models use its independently captured preview as the plan and compare subsequent application with it. They do not silently assign pnpm Yarn's resolver policy.

## Preview status and effects

`npm find-dupes` is a successful dry-run query even when its JSON contains additions, removals, or version changes. pnpm and Yarn's explicit `dedupe --check` return 1 when this fixture has changes and 0 when it does not. These contracts serve different purposes. A consumer must inspect npm's diff rather than interpret status 0 as “nothing to do.” No status unification is proposed.

Every selected project file remained byte-identical during all 14 preview commands. That measured scope includes the author manifest, lock, installation, and local cache files inside each project. It does not cover the separate cache/log directories or establish that all dry-run commands are globally effect-free. The public pnpm contract explicitly notes configuration-dependency exceptions; this fixture has none. [pnpm command documentation](https://pnpm.io/cli/dedupe).

Every root manifest remains unchanged during application. Where selected versions change, the lock and installed runtime agree afterward. The exact pnpm and Yarn applications also rewrite one installation-metadata file despite keeping the same lock and runtime selection. “No dependency change” is therefore more precise than “no writes.” The retained image maps keep those effects separate rather than weakening a checksum comparison to call everything unchanged.

The npm preview accurately reports the surprising changes: its exact-pin case describes 1.1.0 → 1.2.0, and its nested control lists two removals plus a new shared 1.2.0 placement. This supports a documentation/reporting clarification, not an assertion that npm lost a pin or lied about its plan. Broad compatibility within real package implementations is not established by these valid range relations. [npm command documentation](https://docs.npmjs.com/cli/v11/commands/npm-dedupe/), [Yarn command documentation](https://yarnpkg.com/cli/dedupe).

## Models, comparisons, and counterexamples

The [Lean model](Dedupe.lean) has 13 laws; the [Bend model](Dedupe.bend) has six. They separate the selected version pair, physical placement count, captured proposal, admitted constraints, check/apply operation, principal effects, and status contract. The plan belongs to the selected program. A generic bool or model result does not authorize filesystem writes or supply a resolver result.

The [pure comparison](conformance.py) checks 21 native preview/application boundaries against both models. Proposals come from original pre-application stdout; actual results come from separate fresh Node reads, captured locks, and file images. In the ordinary no-peer profile, shared version identity predicts one ordinary linked context; the actual paths then independently check that prediction. Neither lock equality nor identical bytes alone proves the same relation in arbitrary peer or linker contexts.

Two highest-candidate examples are explicitly model-only arithmetic over admitted labels. They are not an execution of Yarn's resolver or a semver proof. The concrete counterexamples retain the important differences:

- Two versions can remain necessary because one parent has an exact constraint.
- A successful npm dry run can describe a version update.
- An applied version update can leave the copy count unchanged.
- A candidate advertised by the registry need not be selected by saved-locator deduplication.
- A dependency no-op can still rewrite installation metadata.

The [conformance receipt](../evidence/js-dedupe-20261125T120841191141Z/conformance.json) records eight malformed DTO refusals, detection of seven changed observation fields, and detection of a changed captured digest. The [read-only observer](observations.py) checks archives/member hashes, actual served metadata, stream/file hashes, lock-to-runtime agreement, preview-to-application agreement, constraints, and unchanged preview images.

Its first checks exposed two observer assumptions, retained in the [correction record](../evidence/js-dedupe-20261125T120841191141Z/observer-review.json). Four pnpm self-package metadata probes returned the fixture's exact 404; required generated dependencies still returned 200. Separately, npm's preview names a package directory while Node resolves its `index.js` entry file. The observer now admits only the specific ancillary probes and compares those path roles correctly. No native input or outcome was changed or recollected to satisfy it.

```sh
# Compile the two model modules in a private directory using the pinned tools;
# record that directory in .build/js-dedupe-formal-current.
LEAN=<pinned-lean> BEND=<pinned-bend> \
  python3 applications/js-dedupe/conformance.py
```

The owner-run collectors executed 35 package-manager commands and 14 fresh Node reads. All command groups retired and both registry servers closed. Config/cache/global locations are explicitly private; no `HOME` override, real registry, global installation, personal project, dependency script, GUI, or live pack is selected. Original producers and the separate nested control remain retained. Collection stays outside ordinary CI; replay uses retained data and pure models.

## Internal and interface recommendations

Keep each tool's existing resolution policy and protect its own relations. npm's tree inventory and update-name scope, pnpm's lock importers/package snapshots and seeded installation, and Yarn's descriptors/locators are not interchangeable copies of one universal package entity.

For npm, use the existing reifier diff to explain version changes separately from physical compaction. The accurate `find-dupes` JSON already contains most of the necessary evidence. Clarify that duplicated names can be re-resolved and that copy count may remain unchanged. An optional human summary can show versions changed, copies added/removed, and the unchanged author manifest. Changing the default to reuse-only would need a separately approved policy and compatibility review; this study does not recommend silently changing it or adding a new solver.

For pnpm, preserve its explicit check contract and detailed edge/snapshot explanation. Keep incidental configuration/install-state effects separate from principal dependency changes, especially in automation. The selected caller already distinguishes check from installation; reuse those values before introducing a new command or broad result wrapper. Frozen locks, config dependencies, workspace filters, peer errors, and lock-only execution need their own remaining evidence.

For Yarn, preserve saved-locator highest selection, exact constraints, check status, and link-mode boundaries. The existing explanation names a changed descriptor and target. Avoid describing this as finding the latest registry release or proving that all physical copies are redundant. Peer virtualizations, PnP, missing cached content, and lock-only output need separate qualification. The inventory includes `dedupe` explicitly; the rest of its resolution family remains pending.

No manifest or lock migration is needed for these preservation/reporting proposals. If new machine fields are added, make them optional/versioned and preserve current fields and status codes. Falsifying checks include a preview/apply target mismatch, a changed exact constraint or author manifest, an invalid selected edge, a hidden version update described as mere copy removal, or a claimed finalized installation that disagrees with a fresh runtime read.

For empack, carry the same distinctions into authoring and update design: editable requirements, exact selection, source availability, captured plans, consumer placement, and applied effects. This does not imply that modpack files should adopt Node's module placement, that cache deduplication changes author intent, or that a shared digest grants deletion authority. `prune`, peer diagnosis, generic registry resolution, failed/partial installation, and other feature-family operations remain pending.
