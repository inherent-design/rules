# Bedrock definition and consumer map

This is a separate edition lane. It maps declarations and documentation at the three exact Mojang sample-source tags in [targets.json](../targets.json). It has no native Bedrock client, renderer or provider execution, and supplies no Java compatibility claim.

| Source tag | Client JSON-schema files | Documentation modules | JSON example anchors |
| --- | ---: | ---: | ---: |
| `v1.21.90.3` | 73 | 16 | 17 |
| `v1.21.120.4` | 98 | 16 | 17 |
| `v1.26.30.5` | 106 | 20 | 17 |

[catalog.json](catalog.json) attributes 389 selected paths to their source commits, Git blobs, byte lengths and SHA-256 identities. Shared inputs are deduplicated into 358 private blobs, totaling 17,116,731 bytes. Selection includes **every client JSON-schema file and every documentation module** at those pins, plus source context and one JSON example per resource-family anchor. That predicate is complete; the intent's larger asset, domain and consumer closure remains incomplete.

[source-facts.json.gz](source-facts.json.gz) holds authored structural facts and candidates, without original source bodies or assets. Its 6,664 schema-node records and 2,613 source-reference candidates are discovery evidence. All recorded references have one candidate within the selected source scope. That does not execute a URI resolver, JSON Schema validator or client loader. These counts do not measure semantic coverage.

## Breadth and consumer boundaries

| Family | Selected source surface | Contract to reify and qualify |
| --- | --- | --- |
| Pack admission | Manifest anchor, add-on documentation | Pack identity, module type, dependency, capability, minimum engine, consent and selected pack stack |
| Geometry and culling | Versioned geometry sketches; block-culling schemas | Bone/cube/face identity, UVs, transforms, visibility, adjacent block/permutation context and actual mesh consumer |
| Animation and controllers | Animation documentation and controller/animation anchors | Molang expressions, transition state, time/delta, events, loops, blending and captured versus live actor state |
| Entities and attachments | Entity/attachable anchors and add-on context | Registry/entity context, geometry/material/texture names, render controllers and missing authoritative data |
| Textures and PBR | Texture-set documentation/sketches and texture anchor | Layer types, channels, required color, conflicts, pack-local image backing, pipeline-specific application and fallback |
| Render controllers | Controller anchor and schema sketches | Material/geometry/texture selection, arrays, expression scope and evaluation order |
| Client biomes | Versioned component/document schemas | Component grammar, biome identity, color maps, climate/presentation context and resource identifier resolution |
| Lighting and atmosphere | Biome identifier components; later lighting/atmospherics documentation | Global versus biome-selected settings, keyframes, light/material distinction, backend and gameplay-light boundaries |
| Water and color grading | Biome identifier components; later water/color-grading documentation | Per-biome lookup, curves, parameter domains, pipeline ownership, tonemapping and unavailable renderer behavior |
| Fog | Fog documentation and sample anchor | Distances, media/environment, priority, blending and lifetime of published settings |
| Particles | Client component schemas, particle/Molang documentation and anchor | Emitter/particle lifetime, shape, motion, expressions, material and event effects |
| Sound | Sound definition/event anchors | Named events, weighted resources, actor context, playback, streaming and native audio ownership |
| Text and UI | Language-list and UI anchors | Localization, binding, focus, accessibility and actual UI syntax/consumer; a strict JSON reader is insufficient for some samples |
| Server/domain context | Add-on, biome, block, entity and event documentation | Referenced gameplay data and authority; unrelated mechanics stay named boundaries |
| Host operations | Not supplied by a schema index | Acquisition, physical paths, archive admission, reload ordering, publication, cancellation, device completion, retained consumers and recovery |

These are distinct contracts. A successful parse does not resolve the actor or texture, evaluate an expression, publish a generation or establish rendered behavior. The host study's files, scheduling, networking, device and authority lanes remain applicable when an actual consumer reaches them.

## Source identity is more specific than a format label

The JSON schemas carry labels including `beta` and multiple release-format strings. A sample tag, a schema's `x-format-version`, a declared minimum engine, a documentation revision and an executable client are separate identities. Matching numeric strings do not establish matching semantics or introduction dates.

Git object kinds need the same care. The initial target manifest mistakenly copied a commit-addressed tree API response's name into `gitTree`. The [correction](../evidence/bedrock-tree-identities.json) retains those responses and records the actual commit-to-tree relationship. Reconstructed hashes agree with the three commit objects, including checks of 1,685 nested tree objects. The pure check now reconstructs each retained root and refuses four altered identities. [GitHub's commit-object contract](https://docs.github.com/en/rest/git/commits#get-a-commit-object) distinguishes the commit from its tree. This correction changes provenance interpretation, not the selected blob identities or acquired source bytes.

There is a concrete example in the block-culling records. The earliest selected tag includes a schema labeled `1.20.60` with condition-related fields; later tags also supply a separately labeled `1.21.80` schema. The latest selected `1.21.80` source adds a `true` default annotation for `cull_against_full_and_opaque`, absent from the earlier selected declaration of that field. An annotation does not establish that an engine inserts a value or applies that culling behavior. Preserve the exact source and consuming phase before deciding compatibility or conversion.

Texture-set sources need the same care. All three tags' dedicated texture-set documentation sketches omit the MERS field, while their aggregate `schemas.json` sketches include it. The sketches mark `color` optional, while accompanying prose describes color as necessary for a usable texture set. That can reflect different validation phases; it is not enough to infer a runtime defect or select one source silently. Keep syntax admission, semantic validity, resource resolution and pipeline use separate.

The current [Learn texture-set reference](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/texturesetsreference/texturesetsconcepts/texturesetsintroduction?view=minecraft-bedrock-stable) also distinguishes Classic, RTX and Vibrant Visuals behavior. It documents pack-local backing and replacement rather than merged texture-set definitions. Those are current documented consumer requirements, pending native comparison at the selected runtime. They are not a declaration that every older source tag implements the current contract.

The current [Vibrant Visuals pack guide](https://learn.microsoft.com/en-us/minecraft/creator/documents/vibrantvisuals/vvresourcepacks?view=minecraft-bedrock-stable) asks for `pbr` capability and minimum engine 1.21.120 or later. The ordinary sample manifest anchors do not declare that capability. That difference describes the selected sample, not absence of PBR in the runtime. The [lighting guide](https://learn.microsoft.com/en-us/minecraft/creator/documents/vibrantvisuals/lightingcustomization?view=minecraft-bedrock-stable) separately identifies biome-selected lighting and distinguishes gameplay light emission from material emissivity. Renderer and gameplay effects need different consumer edges.

## Reading and checking the map

The compressed facts retain JSON Pointer scope for schema declarations, required-name lists, types, enums, bounds, default annotations and keyword presence. They preserve unmodeled keywords by name; they are not a complete executable grammar. Documentation candidates deliberately lack inferred parent ownership: repeated field names from different nested objects must not be merged into one schema. Example roots and format values remain examples, not normative rules.

The study reader removes a UTF-8 BOM when present. It leaves comment-bearing examples unparsed and records the limitation. Neither normalization nor strict-reader refusal is attributed to a Bedrock parser. An initial research traversal incorrectly treated property maps with a field named `type` as schema-keyword objects. That generated candidate and its producer remain private with a disposition; schema-location traversal and a counterexample now guard the corrected map. Original source bytes are unchanged.

```sh
python3 host/minecraft/bedrock/check.py
python3 -c 'import gzip,json; d=json.load(gzip.open("host/minecraft/bedrock/source-facts.json.gz")); print(d.keys())'
```

The check verifies provenance relationships, edition/source boundaries, declaration shape, reference candidates, counts and five deliberately broken maps. It does not fetch source or invoke a schema validator or client. Owner-run [acquisition](acquire.py) uses two network workers, checks exact Git-blob identities and SHA-256, bounds individual/total inputs, excludes artwork and binaries, and preserves incomplete attempts. [catalog.py](catalog.py) derives the facts from those private inputs.

The first [bounded texture-set models](TEXTURE-SETS.md) interpret an independently pinned Microsoft documentation revision. They cover local reference ownership, eligible definition replacement, selected layer/channel restrictions, and separate declaration evidence. Authored cases are not native observations, and current documentation does not qualify the earlier sample tags.

The [culling and biome models](SCHEMAS.md) separately compare 274 retained Draft 7 validator-library results on 18 original schemas. They expose same-format declaration differences, open unknown properties, default annotations, and string-versus-resource resolution. A schema validator is not the native client or renderer.

Continue interpreting bounded rules across the other families, with exact consumer/context and pipeline premises. Native admission, reference resolution, behavior, reload and rendered checks remain unqualified. A faithful backport, restricted asset conversion, explicit approximation and unsupported/unknown outcome must remain independently selectable; no combined mod implementation or pack change is selected.
