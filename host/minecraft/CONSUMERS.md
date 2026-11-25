# Font and block-presentation consumers

This extension reads six additional original Java 26.3 class entries as data, producing two private inspection views. It executes no original class, game, loader or provider. The [receipt and findings](evidence/consumer-gap-findings.json) bind the client, class members, private views, tool, JDK and terminated inspection process. Decompiled text remains an inspection aid.

## A space font is an advance table

The selected `SpaceProvider.Definition` codec requires an `advances` map, with `ExtraCodecs.CODEPOINT` keys and `Codec.FLOAT` values. Its unpacking path supplies a loader that builds `SpaceProvider` from that map. The constructor associates each key with an `EmptyGlyph`; glyph lookup uses the key, and the supported-glyph set exposes an unmodifiable view.

This is a different dependency from an image, archive, native font handle or referenced font provider. The selected loader ignores its resource-manager argument. That source fact does not qualify the full font stack, codepoint grammar, floating-point edge cases, missing-glyph fallback, shaping, accessibility, cache invalidation or native glyph lifetime. No positivity rule should be invented from the word “advance”; the actual codec and consuming layout rules need separate comparisons.

The earlier registry reader missed this view because the implementation moved outside the selected GUI-font package. The extension resolves that source location. All 78 previously attributed source records remain unchanged; the one new record resolves the space-provider registration. The five registered font-provider IDs have not changed.

## Built-in presentation depends on the block registry

`BuiltInBlockModels.createBlockModels` creates a builder, installs its defaults, and returns the built map. The builder enumerates each selected block's possible states and calls its factory with block colors and the actual state. The selected method does not parse a pack-defined block-model graph.

Its defaults include air, heads, banners, shulker boxes, chests, copper golem statues, bells, conduits, decorated pots, enchanting tables, portal variants and flower beds. Those are source-selected registry families, not proof that an older runtime has their blocks, states, renderers or assets. The factory uses actual state properties, including facing, rotation, chest type, weather state and statue pose.

`SpecialModelFactory.create` combines a blockstate-model wrapper with a separately constructed special model. The blockstate wrapper carries block tint sources. Composite and conditional nodes therefore occur in this built-in consumer even without establishing a user resource-pack grammar. A Christmas condition selects chest presentation, and a display-context condition selects a flower-bed transformation. Their live context providers and timing remain unqualified.

`Map.copyOf` fixes the returned map's structure; it does not prove that every referenced registry, resource, context or renderer is an immutable snapshot. Resource-defined cuboid/blockstate inputs, these built-in factories, bake outputs and published generations still have separate owners and lifetimes.

## Typed dependencies and next qualification

| Edge | Meaning | Remaining check |
| --- | --- | --- |
| Font definition → advance map | Decoded input to a provider constructor | Original codec inputs and missing/invalid values |
| Advance map → glyph set | Layout metric ownership | Lookup, fallback and font-stack publication |
| Block registry → possible states | Required runtime domain data | Exact version/provider state universe |
| State + colors → factory result | Context-dependent construction | Actual factory output, tint and missing-context behavior |
| Special model + blockstate wrapper → composite | Ordered composition | Bake/render semantics and double-application controls |
| Condition + presentation alternatives → selection | Runtime context read | Clock/context identity and refresh behavior |
| Returned map → reload generation | Potential publication input | Admission, stale work, failure, retained consumers and retirement |

A future backport may reuse native blockstate presentation while supplying a missing special renderer or conversion. It must name the unavailable domain/context/assets rather than manufacture an older block or authoritative gameplay state. Keeping current native behavior is still an independent alternative. No renderer, backport or pack change is selected by this source extension.
