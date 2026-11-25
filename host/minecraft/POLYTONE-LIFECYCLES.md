# Polytone manager effects and consumers

The [lifecycle map](polytone-lifecycles.json) reviews all 28 built-in managers against the exact selected artifact/private views. It adds 93 typed source-effect relationships and method anchors to the existing [definition and hook map](POLYTONE-CONTRACTS.md). These are source interpretations, not executed manager transitions or a complete call, alias, retaining-root, or effect graph. Every manager remains incomplete.

## Feature and state owners

The table names each domain's publication and cleanup boundaries. Empty `applyWithLevel` does not mean that a feature has no effects: several managers register or mutate live state while parsing. Reset can restore prior values, clear an index, unregister an ID, or merely request later retirement. Those outcomes are not interchangeable.

| Manager | Changes and retained state | Separate consumer or qualification |
| --- | --- | --- |
| Configs | Worldless/world-aware rebuilds, retained file snapshot, thread-local config views, UI save and reload request. | Disk acknowledgement, pack overlays, view cleanup, and actual UI feedback. |
| Noises | Noise registry plus regenerated expression functions. | Retained function references and partial build failure. |
| Global expressions | Expression/value slots, last game-time gate, interval updates. | Clock domain, context, off-thread readers, and retained slots. |
| Sound types | CSV state during prepare; dynamic events/types during parse; sound reload request during apply. | Event registration, sound files, reload completion, and playback differ. |
| Biome ID mappers | Decoded mapping registry, cleared at reset. | Actual biome/registry identity and mapper arithmetic. |
| Colormaps | Builtins, iterative reference decoding, companion images, orphan defaults, platform resolvers. | Cycles, concurrent getters, image identity, and active renderer references. |
| Custom particles | Early model requests, factories/providers, sprite sets, lazy emitters, GPU renderers, prior-provider restoration. | CPU particle lifetime and deferred GPU closure are separate. |
| Colors | Direct vanilla presentation changes, captured prior values, cross-manager inputs, derived sheep colors; apply recreates stars. | Each color/fog/text/particle/render consumer and field-specific restoration. |
| Colored lights | Prepared texture-light candidates, typed target/alias maps, backend storage and light sources. | Selected backend, shader ownership, world/device generations, and resource retirement. |
| Block sets | Vanilla/custom providers and generated-name counter. | Provider references retained in modified blocks. |
| Block modifiers | Legacy conversions, cross-manager inputs, block changes, captured before-images, tick/sound/particle/tint tables. | Actual hooks, context, overlap, and restoration under partial failure. |
| Fluid modifiers | Legacy/own images, modifier tables, platform wrappers, captured water resolver. | NeoForge wrapper consumers and retained reader generations. |
| Custom models | Definitions and generated layer maps; layer build can fail after definition registration. | Later model-layer registration/bake/render and partial-result reporting. |
| Item modifiers | Early model requests, item changes, attached modifiers, captured prior properties. | Distinct tooltip/color/model/armor/pose/light consumers and prior-image lifetime. |
| Custom item models | Early requests, transferred modifier contributions, generated models and override lists. | Bake/model population, runtime selection, and provider overlap. |
| Biome modifiers | Effect plans, mutated biome objects, captured prior effects, fog parameters. | Current registry/level incarnation matters to restoration. |
| Variant textures | Block mappings, forced tint set and quad cache. | Biome/region context, atlas generations, retained quads/sprites. |
| Lightmaps | Image grouping/validation, map registry, current dimension/map selection. | Selection is reset by parse; table clearing alone does not clear every cached reference. |
| Dimension modifiers | Definitions, selected sky/fog/cloud/darkening behavior and inplace effect changes. | Dimension transitions and actual original-value restoration paths. |
| Particle modifiers | Modifier table and separately supplied XP-orb replacement state. | Existing particles and XP-orb fields have distinct roots. |
| GUI modifiers | Class/menu/title indexes and slot modifiers. | Named class lookup may initialize code before index publication; actual GUI target compatibility is separate. |
| Overlay modifiers | Heart metadata during prepare, blit table, active region and render index. | Interception order, index scope, GUI state and rendering cleanup. |
| Entity modifiers | Resolved entity-type modifier/emitter map and related light inputs. | Entity lifetime, tick timing and already emitted particles. |
| Creative tabs | CSV/new tab registration, queued sorting, captured attributes and cache invalidation. | Queued sorting is not completed sorting; open screens can retain references. |
| Post targets | Copied definitions and dirty state; targets allocate/resize later, reset destroys buffers. | Post-chain references and GPU completion are separate from `destroyBuffers`. |
| Post chains | Old-chain closure before effect decoding; later tick selects/loads chains and render/depth paths consume them. | Partial failure, target/sampler ownership, backend/device generation and final retirement. |
| Voxel volume | Callback admission, block/provider flags, volume/palette/compute helpers and change queue. | External callback effects, world/device generations, queue retirement and shared palette lifetime. |
| Shader uniforms | Parsed expression map, then a published per-shader map. | Expression evaluation and actual shader binding happen later. |

The source review intentionally leaves these obligations open. State-symbol presence and method anchors do not prove an edge's full transitive closure. The [original manager map](polytone-managers.json) retains static consumer-reference locators; these are not evidence that an injection ran.

## Shared scheduling and partial outcomes

The selected `PolytoneReloadManager` schedules child preparation futures, waits for all of them and the supplied preparation barrier, then stores prepared resources and chooses the worldless or world-aware path. Child `prepare` is not universally pure: sound CSV, texture-light candidates, legacy block properties, heart metadata, and creative-tab CSV can change manager state before that barrier. Background resource reads and image construction also have their own host effects and ownership.

With a world, reset runs before parse/apply. Per-child parse and apply `Exception`s are reported and accumulated while later callbacks continue, provided reporting/aggregation itself succeeds. A reset failure has a different path. `Error`s, preparation failures, rejection, and a reporting failure must not be silently grouped into that same continuation rule. The selected source supplies no whole-operation rollback. A failed reload can therefore require an account of earlier and later effects rather than a Boolean “applied nothing.” Actual native orchestration/failure traces remain pending.

Dependencies cross manager boundaries. Colors feed block and particle inputs; block parsing converts fluid/dimension inputs and adds colored lights; item/entity modifiers also add light definitions; custom item models consume earlier item-modifier contributions. A later callback or empty apply body does not establish that dependencies were untouched, complete, or validated. The current order is a concrete source contract, not proof that any reordered topological execution is equivalent.

## Deferred retirement and identity

`CustomParticlesManager.resetWithLevel` calls `GpuParticles.retireAll`. The selected delegate appends active renderer references to `pendingClose` and clears `active`. A later `GpuParticles.render` closes pending renderers and only then clears that list. `LevelRendererMixin` declares that call at the tail of `renderLevel`; actual injection and future callback availability are unqualified. A return from reset is not a renderer-close receipt or GPU-completion proof.

Post targets, post chains and voxel resources have different close paths. A buffer destruction call, clearing the active map, or setting a `closed` field does not establish retirement of every borrower, successful close of later resources, or completion of queued device work. Captured biome/item/block values also require the right object and registry/world incarnation. These source distinctions consume the existing [shared lifetime rules](../../common/Lifecycle.lean); they do not strengthen those rules into a claim about the unobserved GPU.

## Named classes and incidental execution

The GUI manager's original bytecode [confirms the default `Class.forName(String)` call](evidence/polytone-class-target-invoke-20261125T111850323262Z/receipt.json). The [Java host comparison](../java/CLASS-INITIALIZATION.md) uses authored classes on the pinned 17/21/25 builds to distinguish descriptor lookup, target initialization, controlled-loader effects, initialization failure, retry and loader identity. It does not execute a Polytone GUI definition.

The source consumer catches missing-class failure locally. That does not establish local handling of linkage or initialization errors. No arbitrary-code exploit, actual pack failure, or game crash is claimed. The independently selectable non-initializing lookup proposal and keep-current alternative are documented with their behavior changes and limits in the host report.

## Selectable design directions

1. **Report stages and partial effects.** Keep the existing stage order, but give each manager stable input, state-owner and effect records, with decoded/registered/applied/retirement-requested/retired outcomes distinct. Preserve the affected resource, original cause, partial state and a safe recovery action. A shared success/failure toast or overwritten log cannot replace those records. This needs actual caller/UI/logging traces before adoption.
2. **Prepare state per reload.** Investigate passing prepared manager data through the captured reload input instead of writing shared manager fields during preparation. This is a design change with dependencies on configuration and registry context, not a proved faithful refactor. Compare overlapping/rejected/interrupted reloads and retained prepared resources before proposing an implementation.
3. **Make retirement ownership explicit.** Give pending GPU resources a reachable shutdown/drain owner and receipts for the obligations that actually retire. Retain current resources while needed by independent consumers and in-flight work. Do not replace renderer/device-specific requirements with a universal “close means free” API. An explicit future-render dependency may remain valid if its absence has a selected fallback.
4. **Keep native domain behavior where justified.** Preserve existing precedence, legacy conversions, registry effects, and per-feature fallback when those semantics are desired. A possible combined mod should select these subsystems independently. Conversion, changed defaults, no-initialization lookup, backend replacement, and approximation need explicit compatibility dispositions and falsifiable consumer checks.

None selects implementation, installation, a pack change, or a provider replacement. Full source/field/consumer closure, native reload/rendering, provider coexistence, actual UX, and the broader host-platform requirements remain unfinished.

## Reinspection

`polytone_lifecycles.py --check` verifies the current public interpretation against its authored review, exact artifact, frozen private views, method bodies and original class identities. It performs no provider execution. One unpublished interpretation initially placed sheep-color regeneration in the apply hook; source review corrected it to parse and identified `createStars` in apply. The superseded map/disposition stays private; no native result was changed.

The Java host comparison and its original-caller scan have separate receipts and assumptions. Ordinary CI runs retained rule comparisons only, never these owner-run Java collectors or a game.
