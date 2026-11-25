# Documented texture-set contracts

This is a bounded interpretation of two Microsoft documentation files at [revision 80b7b17](https://github.com/MicrosoftDocs/minecraft-creator/tree/80b7b1713df821debb4a8022e32e6b0ad840a273). It adds [Lean](TextureSets.lean), [Bend](TextureSets.bend), and [authored expected cases](texture-cases.json). There are **no native client observations** in this band. Matching models establish their agreement with the selected interpretations, not Bedrock runtime conformance.

The [source record](texture-sources.json) binds exact Git blobs, SHA-256 values, paths, and interpreted sections. The two documentation inputs total 12,163 bytes; the owner-run acquisition preserves its producer before fetching. Three earlier selected sample-document identities remain separate. Current documentation does not retroactively qualify those clients, and a format string is not a pipeline or engine-build identity.

## Rules that need separate owners

| Boundary | Selected interpretation | Remaining qualification |
| --- | --- | --- |
| Layer validity | Color is required; normal/height and MER/MERS are alternatives. | Complete grammar, parsing, engine diagnostics, and fallback. |
| Backing | Image references belong to the definition's pack. | Physical admission, actual bytes, parsing, and lifetime. |
| Extension choice | TGA precedes PNG, JPG, and JPEG among eligible local candidates. | Duplicate physical-key policy, path normalization, and races. |
| Definition priority | Eligible definitions replace rather than merge their fields. | Discovery, eligibility, and invalid-higher-definition fallback. |
| Channel representation | Images and uniform values have different selected channel declarations. | Image decoding, hexadecimal parsing, conversion, and actual pipeline use. |
| Consumer context | Heightmaps have a documented texture-object restriction in Vibrant Visuals; uniform MERS has a distinct variation limit. | Actual object classification, variations, and rendered effects. |
| Material channels | The documented larger metal/subsurface value wins; ties favor subsurface. | Pixel decoding, floating-point/shader implementation, and rendering. |
| Pack declarations | The PBR authoring floor and the `raytraced` alternative remain independent evidence. | Installed-engine admission, hardware/backend, selected settings, and device availability. |

The issue mask is a research reporting proposal. It accumulates independent facts and holds unknown backing separately from demonstrated unavailability. Its bits, ordering, and zero result are not existing Bedrock error codes or a complete preparation certificate. In particular, zero means no selected modeled issue; it does not mean rendered, compatible, or installed.

Image records carry logical pack, name, extension, and content tokens. They do not grant file access, prove byte equality, or retain a resource. The model assumes unique physical candidates and receives eligible definitions in priority order. It deliberately does not decide whether an invalid higher definition exposes a lower definition. The [host lifecycle contracts](../../lifecycles/README.md) still own physical admission, captured backing, publication, and retirement when an actual consumer reaches those boundaries.

## Counterexamples and preserved limits

The cases distinguish a local PNG from a foreign-pack TGA, even when that foreign image has the preferred extension. Replacing a definition preserves the selected record as a whole; it does not fill missing layers from a lower record. Neither example is a claim about an unexecuted resource-stack implementation.

The source sketch marks color optional while its validity prose requires it. That disagreement was already retained in the broader map. This model selects the prose's later validity obligation; it does not reinterpret the sketch as an executed schema. MERS and consumer restrictions from the selected Microsoft documentation must not be silently projected onto older sample sketches.

Review caught an overbroad initial declaration projection: it applied one PBR authoring floor to the `raytraced` alternative too. The unpublished candidate and its passing model comparison remain private with an exclusion disposition. The corrected output keeps two evidence fields. A distinguishing old-floor/raytraced case preserves the alternative without claiming that an old client supports Vibrant Visuals. This correction involved no native observations.

The model does not infer that Classic applies extra layers or that RTX applies MERS. It also avoids deciding which RGB components, if any, an RTX path might salvage from a MERS declaration. The documentation's pipeline-specific statements require an actual selected consumer before a conversion or replacement claim.

## Verification and selectable designs

Run `texture_conformance.py` after compiling the formal modules with the pinned toolchain. It checks authored expectations, source/edition boundaries, rejected DTOs, and changed premises without fetching documentation or launching a client. The owner-run `texture_sources.py` separately rechecks original private source bytes before deriving attribution. These are different checks.

The [verification receipt](texture-verification.json) records 44 case comparisons, eight DTO refusals, four source/qualification refusals, and five changed-premise controls. The existing tracked gate checked 165 Lean modules and 73 Bend files; an isolated gate checked the two added Lean modules and one Bend file. All 241 formal input hashes were rechecked unchanged. This avoids repeating the whole gate while preserving the exact combined input boundary; combined remote CI waits for a coherent publication batch.

A future authoring tool could show definition ownership, local backing, selected extension, layer issues, and unresolved consumer requirements together. It should retain original definitions and report conversions or dropped semantics explicitly. Keeping current engine validation is also a valid choice. Cross-pack image substitution, field merging, unconditional MERS conversion, or adding gameplay data would be independent behavior changes; none is selected here.

Native parser, actual stack/provider selection, missing-reference diagnostics, variations, reload/retirement, and supported-platform/pipeline observations remain open. The broader host and Minecraft intents remain active.
