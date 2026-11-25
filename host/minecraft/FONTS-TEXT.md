# Font definitions, selection, and text consumers

The five selected Java releases register the same five font-provider names, but that list does not describe all their text capabilities or ownership. This band expands the field and consumer map, checks original option-filter behavior, and separates internal font descriptions from resource-pack JSON. Glyph loading, native rasterization, rendering, and provider coexistence remain unqualified.

The shared [source and field ledger](text-shader-sources.json) attributes font, language, and shader inspection views across all five releases. It contains 50 scoped font/language contract records, with fields, declared types/defaults, selected source rules, and source locations. Its additional type-scoped field clauses are discovery locators, not complete delegated codec grammars. [Regeneration](text_shader_sources.py) checks original class identities, frozen inspection inputs, source bytes, scope membership, and selected built-in JSON structures. Original code, assets, fonts, mappings, and binaries stay private. Renaming/decompilation remains an unverified inspection aid.

## Provider fields and required context

This source map separates definitions from the operations and context that consume them. Each edge retains the qualification limits below.

```mermaid
flowchart LR
  packs[Font resource stacks] --> decode[Definition decoding]
  decode --> prepare[Provider loading and reference resolution]
  prepare --> providers[Prepared provider generation]
  options[Font options] --> filter[Effective option filter]
  providers --> active[Active provider selection]
  filter --> active
  style[Resource font identifier] --> lookup[Font lookup]
  active --> lookup
  internal[Internal atlas or player description] --> context[Atlas or profile context]
  lookup --> glyph[Glyph source and metrics]
  context --> glyph
  locale[Injected language and bidi context] --> layout[Layout and glyph use]
  glyph --> layout
  layout --> bake[Bake and texture use]
  bake --> retirement[Separate frame and native retirement obligations]
```

| Definition | Reviewed fields and declared defaults | Consumer boundary |
| --- | --- | --- |
| Font container | Required `providers` list of conditional definitions. | Resource stacks, provider order, reference resolution, fallback, publication, and later active selection have separate rules. |
| Conditional definition | Provider dispatch plus optional `filter`, default empty. Selected option names are `uniform` and `jp`, each Boolean. | The filter controls active selection; loading and prewarming already have separate preparation paths. False does not mean no I/O or allocation. |
| Bitmap | Required `file`, `ascent`, and `chars`; integer `height` defaults to 8. | The grid must have rows and columns with equal Java code-point counts. The selected validator requires ascent no greater than height; do not invent an independent positive-height rule. File loading under `textures/`, pixel dimensions, glyph extraction, upload, and image close are separate. |
| TrueType | Required `file`; `size` 11, `oversample` 1, `shift` [0,0], and empty `skip`. Skip accepts a string or concatenated string list. Shift has exactly two floats in the declared [-512,512] range. | The file loads under `font/`. The float declarations do not by themselves prove valid native size/oversampling. FreeType face creation, retained resource bytes, rasterization, failure cleanup, and native library support need their actual contracts. |
| Space | Required `advances`, using the runtime code-point codec for keys and float values. | This loader builds advance-only glyphs without an image/font resource. No positivity constraint is declared here. Later width filtering and layout remain separate; see the earlier [space consumer review](CONSUMERS.md). |
| Unihex | Required `hex_file` and `size_overrides`. Each override has `from`, `to`, and flattened integer `left`/`right` dimensions. The selected range validator requires `from < to`. | The archive resource opens at the declared identifier, without an automatic `font/` prefix. ZIP entries, hex-line parsing, endpoint application, packed dimensions, overrides, allocation, and lifetime remain independent. |
| Reference | Required `id` identifying another font's provider list. | This unpacks into a dependency reference rather than a resource loader. Resolver ordering, missing/failed dependencies, cycles, and the consuming font still need qualification. |

These are selected source interpretations, not new parser comparisons. The earlier [decoder band](DECODING.md) retains its own bounded evidence. Delegated identifier, code-point, numeric, list, null/unknown-field, and library codec behavior is not silently expanded by the field table.

## Original filter behavior

`FontOption.Filter.merge` copies the other filter, then overwrites matching keys with the receiver's declared values. In the inspected reference caller, the referencing builder's filter is the receiver. A declared false value is a requirement that the option be disabled, not an absent entry. Merging contradictory requirements therefore differs from applying their logical conjunction.

For example, merging a receiver requiring `uniform: false` with a referenced filter requiring `uniform: true` admits the disabled-uniform state. Conjunction would admit neither state. This is current selected behavior, not a new defect or a proposed replacement policy. The native fixture compares filter APIs directly; actual full font-reference loading is source-only.

[FontFilterProbe.java](FontFilterProbe.java) calls original constructors, `apply`, and `merge` using authored HashMaps, HashSets, and the two actual enum constants. Across five releases it records 1,800 predicate results and 20 map-custody results: **1,820 comparisons**. The 360 predicate results per profile cover all nine two-option constraint maps, four option sets, and all ordered map pairs. Setup constructors and merge calls are distinct from these application-result counters.

The direct constructor retains its supplied map in this selected implementation. A controlled mutation changes its later result, while a previously merged filter retains its captured values. Those are direct API controls; the study does not establish that ordinary codec-produced maps are mutable or that gameplay exposes the same mutation path.

[Lean](FontFilter.lean) has 12 laws, including field override identity, idempotence, associativity, and explicit noncommutativity/nonconjunction examples. [Bend](FontFilter.bend) has eight independently checked laws. The [case decoder](FontFilterCase.lean) admits only the selected two-option universe. The [pure comparison](font_filter_conformance.py) checks all 1,820 results, ten decoder refusals, and five changed observations. Its [receipt](evidence/font-filter-conformance.json) binds frozen producers, bindings, original class identities, raw channels, and owned process retirement. No glyph provider, font rasterizer, renderer, game, GUI, or live pack ran. Native evidence is macOS arm64 on explicit Java 21/25 builds; it does not make those client classes Java 17 compatible.

## Loading, active selection, and retirement

The inspected managers load provider definitions from font resource stacks, retain ordering/reversal at particular boundaries, resolve references, and add a fallback. Provider preparation and supported-glyph prewarming precede active option filtering. FontSet selection considers permitted providers and keeps those that supply glyphs under its precedence; the provider-close ledger belongs to FontManager. A provider omitted from active rendering is not automatically closed or unretained.

Option changes reset glyph/texture caches and reselect providers. FontSet closes its texture/stitching owner; FontManager separately closes providers. The later implementations add glyph-source caches and atlas/player providers. The selected width predicate distinguishes ordinary and “non-fishy” glyph choices; it is neither input-codec validation nor proof of finite/correct layout under every float. No universal shaping, kerning, Unicode-scalar, bidi, accessibility, rasterization, or pixel-fidelity result follows from the filter model.

Apply closes old font sets/providers before rebuilding and checking for the default font. Source sequencing does not promise rollback if construction or the default-font check fails. Previously returned glyph sources and queued frame work also need their actual generation and retaining-use contracts. No native leak, stale-frame failure, or completed device retirement is claimed from this source review.

## Font description is not a provider registration

The selected 1.21.11 and 26.3 managers route `FontDescription.Resource`, `AtlasSprite`, and `PlayerSprite` through distinct glyph sources. Atlas identity, sprite identity, a player/profile context, skin-render cache, and the hat flag are runtime dependencies. An ordinary resource-font ID cannot supply those domains merely by naming them.

The inspected `FontDescription.CODEC` accepts the runtime identifier codec and produces a Resource description. Encoding accepts Resource and returns an unsupported-type error for other variants. Thus the richer internal classes do not establish a resource-pack JSON union for atlas/player selectors. The Style font codec, internal description, actual glyph source, and renderer are separate contracts. The earlier three selected managers use resource identifiers on this path; other older UI/custom-renderer capabilities are not declared absent. No native description-codec or rich-glyph comparison was performed here.

## Language and visible text

Pack language metadata maps runtime-bounded 1..16 string codes to required nonempty `region` and `name` strings, with `bidirectional` defaulting to false. The metadata display component uses literal name/region text. Locale metadata, requested code, loaded translation resources, injected language, layout direction, glyph availability, and rendered output remain independent.

The inspected manager selects `en_us` first, followed by a recognized selected locale. Translation resources are read from each runtime namespace and its resource stack into a shared key map; later writes replace earlier values. Namespace iteration and stack ordering must come from the resource manager, not an invented universal winner across mods. The base loader also normalizes selected numeric-format placeholders. Deprecated-translation rewriting and downstream formatting/bidi operations have their own consumers.

In 26.3, `ClientLanguage` throws `EmptyTranslationsException` when a requested locale has no resource stack in any namespace. Despite the name, this is not a test that a present JSON object contains entries. LanguageManager's selected catch displays an ErrorScreen before a new language is injected; other failures log. This is source interpretation, not an exercised GUI/error path or a guarantee covering upstream recovery. The older selected path has different handling. Report the requested and actually injected language separately rather than infer either from a selected row or metadata list.

## Independent design choices and remaining scope

- Preserve receiver-precedence filters where compatibility requires them. An authoring diagnostic can expose conflicting declarations and effective provenance without silently replacing the rule with conjunction. A conjunction mode would be a separate behavior change.
- A candidate reload can validate complete new font sets before publication and retain old generations until readers/frame uses retire. It needs actual provider/native cleanup, failure, memory, and context evidence; it is not implemented here.
- Report definition decode, dependency resolution, provider load, option selection, glyph availability, bake/upload, and displayed language as separate outcomes. Include the failing font/provider/resource and safe retained state.
- Bitmap/space conversion, offline rasterization, and a runtime semantic backport are different candidates. Each needs preserved/lost metrics, code-point coverage, filters, layout context, resources, and fidelity tests. A static image cannot be advertised as a general TrueType or player-glyph replacement.
- Keep current native behavior when it supplies the required contract. Do not manufacture missing registries, profile data, rich JSON syntax, renderer capabilities, or native support.

Actual provider coexistence, complete field/delegated grammar and resolver closure, all concrete glyph paths, rendering/accessibility, language UI, Windows/Linux native execution, and independent Bedrock text contracts remain unfinished. No implementation, installation, pack change, or rollout was selected.
