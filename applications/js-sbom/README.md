# SBOM graph basis, metadata, and integrity assertions

An SBOM inventories package identities and relationships from a selected source. Its listed archive digest does not by itself verify the current installed files. npm and pnpm use different graph and metadata sources, so identical package names cannot establish equivalent observation or completeness.

Native collection, retained-byte readback, and the bounded dual-model comparison are complete. Public snapshot and publication qualification remain separate. No product implementation, security audit, signature verification, or upstream correction is selected. Larger operation and scenario statuses remain pending.

## Selected question and fixture

The previously unlinked `npm.security/sbom` and `pnpm.security-license/sbom` operations need a graph-basis and evidence contract. Existing lock-mode and publication studies do not establish SBOM behavior. The discriminating question is whether reported package/hash metadata changes after actual code or installation visibility changes, and how explicit lock-only reporting differs.

The [collector](probe.py) uses pinned Node 26.13.1, npm 11.20.0, and pnpm 12.21.0. It installs three generated local archives, classified as production, development, and optional, in two owned projects. Scripts are disabled; installation is offline, and the configured registry is loopback port 9. This is a configuration boundary, not a network interception or proof of no global effects. Config/cache/state environment paths and retained quarantines are private. HOME and personal projects are unchanged.

The [capture](../evidence/js-sbom-20261126T065646155804Z/receipt.json) contains two installations, six fresh Node observations, and 18 SBOM requests. Eight deliberate mutations replace only a generated JavaScript file, move a top-level package entry aside and back, and move the owned root lock aside. The original archives, producers, streams, path/mode/link/byte images, and quarantined objects remain retained. Project images exclude mtime and external cache/global writes. All 26 recorded process groups were independently absent at final readback.

The replacement uses a new sibling and rename, avoiding in-place writes to possible shared backing. The package entry and lock are preserved outside the project, rather than deleted. The source ledger is [separately pinned](../sources/js-sbom-selections.json); acquisition, selected inspection, native operation, and source-to-binary correspondence are distinct claims.

## Observed outcomes

| Request/state | npm | pnpm |
| --- | --- | --- |
| Initial CycloneDX and SPDX reports | Succeed | Succeed |
| Filter production, excluding dev and optional | Lists production package only | Lists production package only |
| Replace production JavaScript, keep its package metadata | Report succeeds; archive hash and normalized report remain unchanged | Report succeeds; archive hash and normalized report remain unchanged |
| Move production top-level installation entry aside | Default report refuses with `ESBOMPROBLEMS`, naming the missing dependency | Default report still lists the locked production package |
| Explicit lock-only report while that entry is absent | Succeeds | Succeeds |
| Restore entry, move root lock aside | Default report refuses these local-tarball edges as invalid | Refuses with `ERR_PNPM_SBOM_NO_LOCKFILE` |
| Explicit lock-only report without root lock | Refuses and names the lock requirement | Refuses and names the lock requirement |
| Omit required format | Exits 1 with usage guidance | Exits 2 with required-argument guidance |

Every captured report/query leaves project entries equal. Installations and authored mutations are different effect scopes. This does not prove no cache/log/state effects outside the project.

Fresh Node observations independently read changed JavaScript bytes and its changed exported value. When the top-level entry is absent, a fresh observer reports `MODULE_NOT_FOUND`. SBOM after-state is not evidence that those files were present or verified.

## Graph and metadata sources

npm's selected command uses Arborist `loadActual` by default and `loadVirtual` in `--package-lock-only` mode. It checks selected nodes' outgoing edges for missing required or invalid dependencies before serialization. The default tree is not a general physical-content verifier, and this local-tarball profile still needs enough source-location evidence: removing the root lock leads to invalid edges. `dep-valid.js` explains that file edges compare the resolved tarball location, generally recovered from a lock, or a legacy request witness. The captured failure must remain visible rather than being normalized into a generic no-lock success.

pnpm requires a lock in both modes. It walks lock snapshots and enriches package metadata from virtual-store manifests by default; `--lockfile-only` skips that enrichment. The selected source also has platform and importer admission policies not exercised here. An absent top-level package link does not remove a lock snapshot or its stored metadata. This is a legitimate graph-basis distinction, not a demonstrated missing-file detection defect.

pnpm's default report includes the generated packages' MIT license metadata. The explicit lock-only report omits those leaf licenses while retaining the package/hash graph. npm's lock retains license metadata for this fixture. Missing license data means unavailable from that selected source; it is not a claim that the package has no license.

Both CycloneDX reports use lifecycle `build` by default and `pre-build` in explicit lock-only mode. Those phase labels are not a record of an installed-file verification operation. npm emits CycloneDX 1.5 and pnpm defaults to 1.7 in these pinned versions. Their development/optional scope mappings differ; the npm virtual-tree development component also differs from its actual-tree scope. npm's SPDX report types dependency relationships, while pnpm uses root-to-child `DEPENDS_ON` relationships for all three groups. The models preserve these representations; the reports do not carry interchangeable role information.

## Hash and identity boundaries

The reported SHA-512 values equal the generated archive digests. npm places them on components; pnpm places them on distribution references. They remain the original archive values after the installed JavaScript is replaced. Both SPDX reports say `filesAnalyzed: false`. These facts support artifact-source assertions, not current installed-file equivalence, absence of vulnerabilities, executable safety, or runtime compatibility.

npm's CycloneDX root also exposes two name sources: its `name` is the physical directory basename `project`, while its purl and `bom-ref` name the authored `rules-sbom-npm@1.0.0`. Its SPDX root uses the authored name. The selected CycloneDX writer uses `node.name` for display and package identity for the ID/purl. Record this as a bounded identity/presentation mismatch and a candidate for review; a directory-renaming control, aliases/workspaces, current upstream, and schema/consumer expectations remain unqualified. No full-tool defect attribution or patch is selected.

## Models and comparison

[Lean](Sbom.lean) has 20 laws, including quantified state-preservation, code-observation, and proposed identity laws. [Bend](Sbom.bend) has 23 finite laws. The [research decoder](SbomCase.lean) admits two selected formats, the three direct local archives, bounded request traces, canonical archive digests, and valid authored-action preconditions. These laws and the [comparison](comparison.json) do not establish a general installer or SBOM schema implementation.

Both traces start from an empty state and the original authored name, placement name, and verified archive digests. The initial successful installation is an admitted seed event. The models then consume the actual CLI options and ordered authored actions; native after-state is never used as a model input. Both models match all 18 report outcomes, 11 projected documents, and six fresh runtime observations. The eight authored events are modeled state changes, not additional native product commands.

The reader independently checks the retained archive/manifest/stream/project identities, the files read by Node, and the selected direct-graph reference closure in both formats. Normalizing UUID/time fields leaves the baseline and changed-code reports exactly equal. Twelve malformed research requests are refused. Seven input controls change the specific later report or runtime observation they affect; four result controls and seven raw-observation controls reject altered evidence, including a dangling reference, a changed integrity assertion, and false `filesAnalyzed`.

Run the pure comparison with `python3 applications/js-sbom/conformance.py`, using the pinned `LEAN` and `BEND` variables. `--private` additionally checks all 12 retained source-cache identities. It runs no package manager, Node process, installation, or network service. Formal outputs use the private `.build/js-sbom-formal` path. A verification-scope law is a model definition; it does not invent a native verification receipt. Graph/metadata-basis values come from inspected source and selected requests, not new provenance fields claimed to exist in native output.

## Candidate model and remaining checks

Keep `graphBasis`, `metadataBasis`, selected groups, source-location evidence, package identity, placement name, and archive integrity assertions separate from observed installation presence and current file digests. A successful report is not a Boolean named “verified installation.” A declared lock graph and an installed metadata graph can both be useful without making the same claim.

For npm, preserve direct missing/invalid-edge refusal and explicit virtual reporting. Investigate using the authored package identity for the CycloneDX root display name while retaining physical placement separately. Check aliases, workspace roots, existing name-based consumers, and format compatibility before adoption; purl and reference identities must remain coherent.

For pnpm, preserve useful lock-based generation and explicit lock-only enrichment policy. Candidate result facts should explain the graph source and unavailable metadata without requiring rematerialization or silently changing a report into an integrity scan. Any additive properties or sidecar report must preserve the selected standard output and distinguish unavailable evidence from a negative assertion.

For empack's design, reuse the distinction between selected inventory, retained artifact assertions, materialized paths, and actual verification demand. SBOM success cannot authorize repair, launch, or publication of unrelated state.

Complete graph/format validation, registry/Git/alias/workspace inputs, peer/platform behavior, stale metadata, concurrency, other hosts, and output-file publication remain open. The root-name correction has a model law, with no native patch or directory-renaming qualification. Changes to a field's displayed name or added provenance must be reviewed against existing serialized consumers; this study selects no production format change.
