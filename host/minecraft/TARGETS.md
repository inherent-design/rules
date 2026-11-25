# Selected edition and provider targets

[targets.json](targets.json) selects five exact Java release references, three Bedrock sample-source references, and eight NeoForge 1.21.1 provider variants. It replaces the four-profile stopping condition. The four historical names remain evidence aliases. A selected reference is a research obligation; it is not a qualified installation or compatibility claim.

## Original Java artifact facts

The official version manifest and per-release metadata identify the acquired original client JARs. Their own `version.json` entries agree with the launcher-declared Java major. [Identity checks](evidence/target-identities.json) retain the metadata and original-client digests. Original payloads and mappings stay private.

| Java release | Declared Java major | Declared resource format | Declared data format | Source encoding |
| --- | --- | --- | --- | --- |
| 1.21.1 | 21 | 34.0 | 48.0 | Legacy integer fields. |
| 1.21.4 | 21 | 46.0 | 61.0 | Legacy integer fields. |
| 1.21.5 | 21 | 55.0 | 71.0 | Legacy integer fields. |
| 1.21.11 | 21 | 75.0 | 94.1 | Separate major/minor fields. |
| 26.3 | 25 | 97.1 | 121.0 | Separate major/minor fields. |

These are game artifact declarations, not arbitrary `pack.mcmeta` schemas, compatibility ranges, repository admission, or successful rendering. In particular, dropping the nonzero minor loses real information. [ArtifactVersions.lean](ArtifactVersions.lean) and [ArtifactVersions.bend](ArtifactVersions.bend) normalize the two encodings and refuse lossless conversion to a legacy integer when the minor is nonzero.

The [pure comparison](evidence/artifact-version-conformance.json) covers all five metadata records at available Java majors 17, 21, and 25. Those fifteen calculations check only the declared major prerequisite. They are not JVM or game executions. Decoder, projection, and changed-result controls reject mixed fields, lossy minors, and an incorrect Java 25-on-21 prerequisite result.

The official manifest at the captured cutoff also lists 26.4-pre-1. Its applicability review remains pending; it is not silently folded into the selected 26.3 reference. Future additions must pin their own source and explain what changes in the comparison.

## Provider composition

NeoForge 21.1.265 remains the baseline loader declaration. Exact Modefite 1.0.1+1.21.1, Polytone 1.21-5.3.8 NeoForge, and selected Compat artifact identities are separate provider nodes. The eight variants include loader-only, each relevant independent provider, existing Modefite+Compat, and meaningful pair/triple overlaps. The deployment baseline remains Java NeoForge 1.21.1.

The [Polytone binary census](polytone-source-census.json) identifies 595 class entries and 21 content package areas. Its mod metadata declares Minecraft `[1.21.1]` and required client-side NeoForge, with optional Nautilus Studio and Veil dependencies. This selects sources for semantic investigation; class names, broad loader metadata, and declared optional dependencies do not establish active capabilities or coexistence. No Polytone installation was performed.

Each variant still needs configuration, hook order, definition ownership, active consumer, failure, reload/publication, and retirement evidence. Automatic Euler support, scalar-angle hooks, Compat's gated whole-model path, missing later gameplay data, and third-party renderers must have explicit coexistence and refusal rules. No generic “modern resources supported” flag substitutes for those contracts.

## Bedrock source references

The official [Mojang sample repository](https://github.com/Mojang/bedrock-samples) supplies pinned source tags v1.21.90.3, v1.21.120.4, and v1.26.30.5. The graph records each commit, Git tree object, API response digest, and observed resource folder families. These are distinct source milestones for Vibrant Visuals, documented PBR requirements, and later presentation changes. Java and Bedrock numbering does not establish equivalence.

`treeResponseSha256` identifies the exact retained API response; `treeResponseName` preserves its name for the commit-addressed request. `gitTree` identifies the actual tree object, reconstructed from entries and matched to the commit object's `tree`. The [identity correction](evidence/bedrock-tree-identities.json) supersedes the earlier mislabeled `gitTree` fields in the initial manifest and historical target-identities receipt; selected source blobs and bytes are unchanged. Neither identity identifies an installed Bedrock client. Native client artifacts, renderer behavior, historical schema availability, and feature toggles remain unqualified. A missing sample folder does not prove that a runtime lacks the feature. Current documentation also cannot silently establish an older release's contract.

The [Bedrock source map](bedrock/README.md) now derives structural facts from every client JSON-schema file and documentation module at those three pins, with one JSON example per resource-family anchor. It preserves source-tag, schema-label, documentation and sample identities separately. Source completeness within that acquisition predicate is narrower than the complete definition, consumer and asset coverage required by the intent.

## Host dependencies

The [26.3 static API map](HOST-APIS.md) starts from actual client bytecode rather than a guessed desktop stack. The [Java 25 overlay](../java/README.md) independently qualifies selected arena scope operations. A new stable host API witness does not prove that Minecraft uses it. Runtime declarations, class-file requirements, API use, native library selection, operating-system support, backend selection, and rendered effects remain separate dimensions.

The [expanded intent](intent.md) still requires complete selected-family and consumer mapping, attributable rules/proofs/comparisons, operational UX, and independently selectable design proposals. This target selection and static census do not complete those obligations.
