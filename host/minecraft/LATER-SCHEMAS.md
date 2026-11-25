# Later Java definitions and consumers

This source band starts from the selected original Java 26.3 client and a private inspection slice of 431 class entries, producing 236 Java views. It adds source discovery to the earlier 1.21.1/1.21.5 parser observations. Its separate [later decoding band](LATER-DECODING.md) now executes selected original 26.3 methods and codecs. Renderer, loader and provider execution remain unqualified. Decompiled views are inspection aids, not verified inverses of compilation.

[later-registry-catalog.json](later-registry-catalog.json) enumerates 71 literal registrations in eight selected categories, with 78 associated source identities. One associated font-provider view remains unavailable. Registration, bootstrap reachability, per-type schema, actual consumer behavior and rendered output are separate obligations.

| Selected category | 26.3 registrations | Difference from the inspected 1.21.5 registry |
| --- | --- | --- |
| Item nodes | 8 | Same registered IDs; associated types and fields still need comparison. |
| Conditions | 13 | Same IDs; runtime state and semantics remain independently versioned. |
| Select properties | 10 | Same IDs, without a semantic equivalence claim. |
| Numeric properties | 10 | Same IDs, without a semantic equivalence claim. |
| Tints | 7 | `minecraft:map_color` is absent from this selected registry. |
| Special renderers | 13 | `bed`, `hanging_sign` and `standing_sign` are absent; `bell`, `book`, `copper_golem_statue`, `end_cube` and `player_head` are added. |
| Atlas sources | 5 | Same registered IDs; resource ownership and execution remain open. |
| Font providers | 5 | Same IDs; the associated `SpaceProvider.Definition` view lies outside the acquired slice and remains pending. |

These are literal set differences, not unsupported-feature or asset-availability claims. For example, the original default red-bed item asset now uses two ordinary model nodes in a composite. Its second model has a translation. The selected oak-sign item assets reference ordinary cuboid item models. Those three original asset facts do not prove a conversion for every bed/sign variant or supply assets and gameplay context to an older runtime.

The shared reader now recognizes both `ResourceLocation.withDefaultNamespace` and `Identifier.withDefaultNamespace` in registration statements. It preserves the earlier 161-registration index's profile data, source identities and field candidates when regenerated. This spelling support does not equate the two identifier APIs. Missing-view diagnostics preserve the requested qualified class name; they no longer collapse it to a package root.

## Grammar and execution are separate

[later-source-findings.json](later-source-findings.json) binds six inspected contracts to original class-member and private-view digests. It retains the six original source predictions and adds separately attributed follow-up evidence. The vanilla half of those selected comparisons now has original-method observations; the Polytone/Compat hook comparisons remain unexecuted. The retained initial prediction status describes its original research phase, not current qualification.

The cuboid rotation decoder chooses the scalar branch when either `axis` or `angle` is present, requiring both. Otherwise it requires at least one XYZ component and defaults missing components to zero. Polytone's selected injection chooses its XYZ branch whenever an XYZ member is present. A mixed scalar/XYZ input therefore distinguishes the two selected source paths. Native transformed-hook comparison remains necessary.

26.3's cuboid rotation retains rescale and computes per-axis factors after rotation when needed. Polytone's selected XYZ construction passes false, while Compat's whole-model path refuses rescale. A shared Euler multiplication order alone cannot establish equivalent decoded state, geometry, culling or shading.

The selected element decoder reads `shade_direction_override` and does not read the old `shade` member. The model-wrapper codec also has an optional `transformation`, whereas the inspected 1.21.5 associated codec exposes model/tints without that member. Unknown-field admission, deliberate conversion, faithful semantics and unsupported cases need their own results; a matching type name does not establish them.

Pack metadata has another independent boundary. `PackFormat` supplies different default minors at lower and upper endpoints, and uses legacy transition thresholds of 64 for resources and 81 for data. Pack and overlay validators have different premises; an overlay list can impose a condition on multiple entries. The existing [artifact-version model](TARGETS.md) preserves declared game format minors, but it does not implement this `pack.mcmeta` grammar or its admission rules.

The inspection also found a useful limit on structural inference. `ModelManager.reload` loads resource-defined cuboid models, blockstate models and client item info separately. Its `BlockModel.Unbaked` contents come from `BuiltInBlockModels.createBlockModels` in the selected path. The presence of `CompositeBlockModel` and `ConditionalBlockModel` classes therefore does not itself establish a user-authored resource-pack graph grammar. The factory and other consumers still need inspection.

## Next comparisons

Extend the bounded original-method comparisons to actual provider hooks, full model/pack admission and the remaining grammars. Keep decoding distinct from baking, resource discovery, reload publication and retirement. Extend the selected source slice for the missing font provider and actual block-presentation factory. Then compare 1.21.11 through its own original artifact/mappings rather than treating 26.3 as its contract.

The native collectors must use explicit JDK selection, private inputs, small heaps, bounded concurrency and confirmed process-tree retirement. No Gradle daemon is needed for these inspection procedures. Ordinary CI continues to compile the formal models and replay retained facts; it does not acquire these private inputs or run applications.
