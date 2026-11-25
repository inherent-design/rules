# Polytone definitions and consumers

The exact uninstalled NeoForge artifact selected in [targets](targets.json), Polytone 1.21-5.3.8, contains 595 class entries. Private inspection produced 403 Java views including nested classes. Decompiled views are inspection aids, not matching upstream source or verified inverses of compilation. A bounded comparison executes one unchanged policy class under explicit data/logging adapters. No provider installation, full game, renderer, GUI, account, world, or personal configuration operation occurred.

[polytone-managers.json](polytone-managers.json) indexes all 28 built-in content-manager registrations, their actual reload order, constructor resource roots, codec-reference candidates, phase declarations, and static consumer-reference locations. Its source identities bind original class entries and private views. Folder literals were independently found in their corresponding original class entries. Method names and references are locators for semantic work, not qualified user operations or proofs of active injection. Every manager remains incomplete.

## Definition families

| Manager | Definition entry | Consumer and effect to qualify |
| --- | --- | --- |
| Configs | `config_entries` | Pack settings, main-menu controls, saved `polytone_options.json`, reload requests and conditional definitions. |
| Noises | `noises` | Named noise construction and expression sampling. |
| Global expressions | `global_expressions` | Tick-time values, named slots, context and refresh ordering. |
| Sound types | `custom_sound_types`, `sound_types` | Named sounds and their actual playback/registration consumers. |
| Biome ID mappers | `biome_id_mappers` | Biome identity lookup for colormap consumers. |
| Colormaps | `colormaps` | Images, references, compound mappings, color sampling and cache lifetime. |
| Custom particles | `custom_particles` | Factories, sprite collection, preview/spawn and particle retirement. |
| Colors | `color.properties`, `colors.json` | Color/fog/UI overrides across Polytone, Colormatic, Vanadium and OptiFine-style resource roots. |
| Colored lights | `colored_lights` | Block/entity/item/particle lights, aliases, shader patching and renderer-specific gates. |
| Block sets | `custom_block_sets`, `block_sets` | Named block-set data and registry consumers. |
| Block modifiers | `block_modifiers`, `block_properties` | Tints, visual offsets, particle tickers, properties and reset of captured values. |
| Fluid modifiers | `fluid_modifiers`, `fluid_properties` | Fluid colors/properties, platform extension wrappers and reset. |
| Custom models | `custom_models` | Model/layer definitions, lookup and consuming renderer. |
| Item modifiers | `item_modifiers`, `item_properties` | Item presentation/property changes, generated-model relationships and restoration. |
| Custom item models | `custom_item_models` | Early generated models, bake registration and live item override selection. |
| Biome modifiers | `biome_modifiers`, `biome_effects` | Biome presentation, fog parameters and original-value restoration. |
| Variant textures | `variant_textures` | Texture selection and tint interaction under actual item/entity context. |
| Lightmaps | `lightmaps` | Light texture modification, GUI context, images and renderer state. |
| Dimension modifiers | `dimension_modifiers`, `dimension_effects` | Sky, sunset, weather/fog/cloud behavior and dimension transitions. |
| Particle modifiers | `particle_modifiers` | Existing particle changes, colors, replacement and lifecycle. |
| GUI modifiers | `gui_modifiers` | Screen/slot/widget targeting, position/color changes and interaction expectations. |
| Overlay modifiers | `overlay_modifiers` | Blits, hearts/sprites, overlay phases and render-state restoration. |
| Entity modifiers | `entity_modifiers` | Entity tick/presentation consumers and reset. |
| Creative tabs | `creative_tab_modifiers` | Tab contents, ordering, predicates and insertion failure feedback. |
| Post targets | `post_targets` | Target creation, resize, destruction and consumers retaining target references. |
| Post chains | `post_chains`, `post_shaders` | Effect loading, target binding, processing, depth capture and later rendering. |
| Voxel volume | Callback-derived; no constructor resource directory | World/packet changes, dirty regions, callback ownership and GPU volume lifecycle. |
| Shader uniforms | `shader_modifiers` | Expression uniforms, per-frame updates, binding and active shader compatibility. |

Default directory managers prefix these folders with `polytone/` under the resource namespace. The color manager instead scans its stated roots using suffixes and resource stacks. This table follows reload registration order, which differs from static field construction order. Public add-on manager registration remains an extension boundary; these 28 records do not enumerate arbitrary add-ons.

These are constructor roots, not an exhaustive schema or input-path claim. Custom prepare methods, legacy conversions, callback producers and renderer integrations need their own semantic rows. No manager advances to complete because its constructor and consumers appear in the map.

## Shared rules that need distinct contracts

The common parser reads enablement conditions and priority separately from content. Conditions include `polytone_ignore`, a version range, required mods, and a required config. Disabled content is not always exempt from decoding: the selected `parseAlways` path supplies the same codec for enabled and disabled cases, while the enabled-only path can skip content decoding. The actual caller determines which policy applies.

The selected per-ID map also has more rules than “last one wins.” A first entry can be disabled. A later disabled entry does not replace an existing entry. An enabled replacement must have strictly greater priority; equal priority preserves the existing one. Consequently, an existing high-priority disabled entry can remain ahead of a lower-priority enabled candidate. Iteration sorts by priority while preserving insertion order for ties. The [bounded original-class comparison](polytone-priority/README.md) qualifies those method decisions under its adapters. Ordinary loading reachability and UX remain open; these are not accepted defects.

Folder alias order is a different stage: default directory scans merge each successive folder map with `putAll`. Single-file colors traverse resource stacks, warn on duplicates, and log per-file decode failures while continuing. Those policies must not be collapsed into the later parsed-entry priority rule or ordinary pack priority.

Preparation uses parallel futures and a barrier. Later work stores prepared resources, resets children, parses in child order, then applies in child order. Per-child parse/apply exceptions are collected while subsequent children continue; the accumulated error is thrown afterward. Reset exceptions and preparation failures have different paths. There is no shared rollback transaction in this selected method. Whether a particular child restores its own earlier state or leaves partial effects requires that child's full contract and evidence.

World/tag reception and logout are separate entrypoints. Configs can parse without a world; most default manager hooks do nothing in that phase. Source inspection also finds log-file writes and failure toasts. The saved log, accumulated exception, UI message, completed future and resulting resource state need separate observations; one error flag cannot stand for all of them.

## Automatic rotations and coexistence

The selected common mixin descriptor names the decoder, rotation-data and face-baking mixins. The decoder recognizes any of `x`, `y`, or `z`, defaults missing components to zero, and constructs an extended rotation without requiring a separate pack config. Its selected constructor passes `rescale=false`; preserving arbitrary authored rescale semantics is a separate obligation. Scalar `angle` decoding is also unrestricted by another hook. The face-baking wrapper uses JOML `rotateZYX` and conditionally bypasses winding recalculation.

This is concrete source-level automatic Euler support, not a claim of faithful 1.21.11 geometry on every asset or renderer. Parent models, inherited elements, culling, normals, rescaling, model transforms, rendering and later shade-direction semantics still require comparisons. Modefite also intercepts scalar angle decoding, while Compat has a gated whole-model path with its own refusals. Descriptor declarations do not establish hook application order, ownership, equivalence or safe composition.

No `shade_direction_override` literal was found in the selected original Polytone class entries or their private views. This is a scoped implementation search, not a proof about all dependencies, arbitrary shaders, or complete 26.3 graphics equivalence. Later vanilla and separate Bedrock contracts remain first-class comparisons.

## Next evidence

Qualify the remaining common parser/reload decisions against original method behavior under explicit adapters, then connect each feature's codec, live consumer, owned state, reset/retirement and UI behavior. Keep synthetic/source-fragment results separate from loader-transformed execution. Native resource reclamation needs the host lifetime contracts; a `destroyBuffers` call alone does not prove all consumers or GPU work retired. Proposed preservation or publication changes remain independently selectable designs rather than a replacement mod implementation.
