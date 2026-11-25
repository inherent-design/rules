# Registered definition families

The [source discovery index](registry-catalog.json) records 161 entries across the initial four profiles, with 136 attributed private source views and 162 associated-file field candidates. It expands the map from broad family names to individual dispatch names and implementation targets. It does **not** qualify those entries as complete schemas, compatible implementations, or functioning runtime capabilities. Semantic and consumer review remains pending.

| Selected source | Modern item nodes | Boolean properties | Select properties | Numeric properties | JSON tint sources | Special renderer types |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Vanilla 1.21.5 | 8 | 13 | 10 | 10 | 8 | 11 |
| Pinned Modefite | 6 | 14 | 9 | 10 | Not indexed as a separate dispatch | Not registered in its node mapper |
| Pinned Compat replacement | 6 | 14 | 9 | 10 | 3 | Not accepted by its node compiler |

These are counts of the inspected registrations, allowlists, or explicit dispatch branches. They are not counts of equivalent features. Bootstrap, loader, physical side, configuration, resource selection, native context, successful evaluation/bake, and publication remain separate premises. The modded rows describe their own definition paths, rather than the union of everything the Minecraft/NeoForge process might render.

Vanilla 1.21.1 has no corresponding modern item-program registry in its official client mappings. Its legacy model definitions, overrides, item-property functions, native item colors, and renderers remain relevant; the empty modern registry entries do not mean the baseline lacks item rendering or property-driven behavior.

## Distinctions to preserve

Vanilla registers model, empty, composite, condition, select, range-dispatch, special, and selected-bundle-item nodes. The pinned Modefite mapper registers the first six, and the Compat compiler accepts those six node labels with its own field checks and implementation. Presence of the same label does not establish compatible payloads, defaults, recursive behavior, failure policy, or rendered results.

Vanilla's select registry includes `minecraft:local_time`; that name is not registered in the pinned Modefite select registry. The conditional sets also differ: Modefite has `modefite:hovered_item` and `modefite:submerged`, while vanilla's conditional registry includes `minecraft:bundle/has_selected_item`. The entire lists and their associated implementation targets are in the index; these observations do not classify unknown-property behavior, which still requires the caller's fallback/refusal rules.

The pinned Modefite model leaf codec declares `type` and `model`. Its absence of a JSON tint dispatch does not remove Minecraft's native item colors. Compat's resource compiler has a per-leaf `tints` field and three explicit tint branches: constant, grass, and potion. Vanilla registers eight tint types. The leaf's ownership of tint functions, color representation, native game state, and model/render hooks must be modeled before calling these paths equivalent.

Both vanilla versions register five atlas-source types and five font-provider types in the inspected source. Equal type-name lists still do not prove equal schemas or operational behavior. Images, palettes, provider references, codepoint grids, rasterization, upload, and lifetime are separate consumers.

## Evidence boundary

[The indexer](catalog_sources.py) reads the already acquired private source views. It verifies the pinned official mapping digests and selected mod-artifact digests, checks the baseline absence of the six modern registry classes against the complete official client mapping, and fails on missing required views or unresolved associated types. It exports names, source hashes, field candidates, and attributed targets, without redistributing Java source, mappings, game binaries, libraries, artwork, or mod payloads.

Field candidates come from the **whole associated Java file**, including possible nested records and helper codecs. They are discovery leads, not complete per-type schemas or reviewed constraints. Defaults, value types, null/absent distinctions, bound checks, dynamic registries, recursive calls, and context reads still need explicit source clauses and laws. Missing categories in a refinement index are not automatic unsupported states or an instruction to merge all parent registrations.

Private decompilation is an inspection aid, not a source-to-binary equivalence proof. This index adds no native execution or model-conformance claim. The existing [decoding](DECODING.md) and [resource-selection](RESOURCES.md) comparisons keep their stated boundaries.

One lifecycle question remains source-only: the pinned Modefite registry's `clear()` clears the definition map and invalid-type set, while its separate root-definition map is not cleared there. Held-item swap hooks read the root map. This is not a full reload, leak, or visible-bug finding; initialization, replacement, hook admission, and observable effects need a bounded lifecycle comparison before deciding its meaning.

The next map layer covers source-derived contracts for the remaining resource families and the gameplay/context/native operations that consume them. The [expanded version/edition/provider research](intent.md) remains in progress; these initial nodes do not define its final target set. No backport is selected by this index.
