# Particle definitions and consumers

The selected Java releases separate a texture-list definition from its registered particle provider, sprite binding, particle admission, simulation, extracted render state, and backend submission. A definition cannot create missing gameplay behavior by itself. This family remains partial: the current native comparison qualifies an original sprite-set helper with identity adapters, while engine, reload, rendering, and provider relationships below are source interpretation.

The [source map](particle-sources.json) attributes 55 Java inspection views and three Polytone views to exact original class identities across five releases. Eleven selected Java classes have identities but pending source views. [Regeneration](particle_sources.py) uses existing private inputs. Missing candidate class names are recorded separately from missing source inspection; neither means an equivalent feature is absent under another owner. The private [later inspection procedure](inspect_particle_sources.py) reuses the attributed 1.21.11 named artifact and the original named 26.3 artifact. Renaming and decompilation are not verified translations.

## Definition and ownership map

| Surface | Source contract | Qualification still required |
| --- | --- | --- |
| `particles/<id>.json` | The selected description decoder reads optional `textures`; absence yields an empty list. Values become texture identifiers. Existing [decoder observations](DECODING.md) retain their own scope. | Full error/coercion grammar, resource precedence, pack overlays, and provider-specific extensions. |
| Registration | Particle types and actual factories are registered independently of texture-list JSON. Sprite-backed providers retain a mutable sprite set; other providers need no such set. | Concrete provider construction, required gameplay/level state, and whether an older runtime has the requested particle behavior. |
| Definition loading | The reviewed later loader ignores an identifier lacking a registered sprite set before opening its reader. A registered empty texture list is different: apply supplies the missing sprite. Missing referenced sprites also use the atlas fallback. | Original resource-reader/decoder/atlas execution, malformed inputs, and all ignored/missing-definition cases. |
| Sprite binding | Rebind copies an input list into the helper. Frame selection uses integer arithmetic; later helpers also expose `first()`. | The bounded original-helper comparison below. Real sprite contents, animation clocks, resource generations, and rendering remain separate. |
| Particle creation | `createParticle` can return a constructed particle after calling an admission method that may decline to queue it. A nonnull object is not proof of simulation or rendered admission. | Actual providers and queue/count behavior; source-only here. |
| Reload | Definition and atlas preparation, a barrier, clearing/callback work, and sequential rebinding have separate owners and failure points. | Actual scheduler/barrier ordering, partial apply/recovery, old generations, and backend retirement. |
| Render state | Later engines extract group state for a frame. Clearing a queue, logical render state, or registry does not establish retirement of every retained consumer or native use. | Actual frame ownership and completion protocol. The inspected 26.3 quad-storage clear resets its count and retains arrays; this is not a physical-memory measurement. |

## Versioned consumer differences

Java 1.21.1, 1.21.4, and 1.21.5 keep resource reload, provider registration, sprite sets, and particle queues in `ParticleEngine`. Their reviewed reload chain awaits definition work and atlas preparation, passes its preparation barrier, clears particles, uploads the atlas, and rebinds sets. Its bounded per-render-type queues use `EvictingQueue` with capacity 16384. Eviction, tracked-limit counters, custom callers, and old references need their own invariants; no count leak or runtime failure is established by this source map.

In 1.21.11, `ParticleResources` owns providers and sprite sets; `ParticleEngine` owns queues and simulation. Groups retain bounded evicting queues, while extracted state has its own owner under `renderer.state`. The resource apply callback precedes sequential sprite rebinding. This delegation must be followed through the actual callback registration, not assumed to be a universal cleanup barrier.

In 26.3, render-state classes move under `renderer.state.level`, and group admission changes materially. A group rejects at size 16384; at size 12288 and above it samples admission against a free-space expression. The engine compensates its tracked limit when a pending particle is rejected. Those are inspected source branches, not a proved probability distribution, general counter invariant, or native engine observation. They cannot be represented as the older eviction policy merely because the nominal capacity matches.

Both later resource owners consume atlas preparations through a shared reload state. A profiling label containing “upload” does not establish that this particular method owns the GPU upload. The earlier direct upload path, later atlas manager, CPU particle state, frame extraction, and actual device submission require distinct versioned edges.

## Original sprite-set comparison

[SpriteSetProbe.java](SpriteSetProbe.java) constructs the original private mutable sprite-set helper and invokes original `rebind`, frame `get`, and available `first` methods. Three original `TextureAtlasSprite` objects per profile are allocated without their constructors through `Unsafe.allocateInstance`, solely as distinct identity tokens. Their contents and fields remain uninitialized; no sprite field, render, upload, close, or animation method is called. This adapter does not create valid renderable sprites and is not a standard Java allocation guarantee. Incidental JVM/class/library effects remain outside the selected effect closure; see [class initialization](../java/CLASS-INITIALIZATION.md).

Nine programs per release produce **196 retained boundaries**: 186 original helper method calls and ten authored input-list mutations. The frozen runner also constructs nine helpers and allocates three identity objects per profile as setup; those operations are outside the method-call counter. The three older profiles have 38 rows each; 1.21.11 and 26.3 have 41 each because their helper exposes `first`. Absence of that method in an older helper does not prove absence of all first-sprite behavior elsewhere.

Observed distinctions include:

- Unbound access, an admitted empty list, denominator zero, and an invalid index fail differently. These states remain separate.
- Successful rebind copies the input. Later input-list mutation does not change the helper's binding. This is a binding snapshot, not a deep copy of sprite resources or a lease on their contents.
- A null input or null element rejects rebinding while preserving the prior binding. Duplicate nonnull identities remain admitted.
- Frame arithmetic truncates toward zero. For three sprites, index -1 and maximum 3 select the first sprite in this fixture. A singleton can return its only identity for otherwise out-of-range finite frame values. These observations do not authorize arbitrary frame inputs or require a stricter wrapper.
- Later `first()` distinguishes unbound access from an admitted empty list.

[Lean](SpriteSet.lean) has 13 laws, including general preservation of binding by input mutation, null rebinding, and reads. [Bend](SpriteSet.bend) has eight independently checked laws. Both executable models match every retained boundary, binding image, input image, and selected identity. The [case decoder](SpriteSetCase.lean) restricts identities, list lengths, signed operands, helper availability, and input-mutation premises. Products remain within the selected nonoverflow range; the model does not qualify arbitrary signed multiplication, random selection, or animation timing. Exact captured exception names remain available; the model compares their selected categories.

The [pure replay](sprite_set_conformance.py) checks 13 research decoder refusals and seven changed observations. It launches only Lean/Bend and reads retained data. Native evidence is macOS arm64 using explicit Java 21/25 builds, existing manifest-checked libraries, bounded heaps, and two processors. All compiler/execution groups retired; no game, GUI, native particle engine, renderer, provider, or live pack was launched.

The initial collector omitted a separate digest of its derived request file. It did freeze and hash the plan and producer; that producer deterministically writes the request from the frozen plan. Independent review found the actual private request bytes identical to the hashed plan in all five captures. Replay also requires exact equality of every observed step with that plan. Original receipts remain unchanged, and the maintained collector records the request digest for future runs. This is an explicit input-attribution limit rather than a fabricated historical digest or a native rerun.

One source-inspection preparation incorrectly required the 26.3 render-state package names on 1.21.11 and stopped before starting a decompiler. Its frozen inputs and failure remain in the [disposition ledger](evidence/particle-source-dispositions.json). The corrected selector includes both namespaces and records absent candidate names. Earlier valid 26.3 slices remain attributable and superseded for this map, with no claim that their observations became invalid.

## Provider and host obligations

Polytone's selected custom-particle manager registers types/providers, can replace vanilla factories, creates GPU renderers, and manages later restoration/unregistration. Reset moves active GPU renderers into a pending-close list. The next reviewed render path closes that list before processing active renderers. A retirement request is not the later close, and close alone is not native completion of every submitted use. A throwing close can also leave the pending list partially processed; actual failure/retry behavior is unqualified. Renderer allocation, shader state, heightmap ownership, context loss, logout without another render, and coexistence still require their actual owner contracts.

Modefite and Compat interactions remain pending qualification. Resource-stack changes, angle/model hooks, custom rendering, or gameplay-context absence cannot be declared irrelevant merely because no dedicated particle hook was selected. Java and Bedrock particle definitions remain independent edition contracts.

For the broader host map, keep type/factory availability, constructed object identity, admission, queue membership, simulation, frame extraction, submission, completion, and final retirement separate. The original helper supports only one of those boundaries. The source map identifies where further Windows, Darwin, GNU/Linux, Java, and backend evidence belongs; it does not extend macOS observations to those hosts.

## Independent design choices

- Preserve existing frame selection where compatibility requires it. A stricter authoring wrapper can reject invalid frame/maximum pairs with a structured diagnostic, but must state its changed behavior, including singleton and negative-fraction cases.
- Publish a complete validated sprite binding after required resources are available. A binding snapshot still needs the resource generation and retained backing owners; copied list membership alone is insufficient.
- Distinguish ignored definitions, missing registered behavior, fallback textures, declined particle admission, and renderer failures in reports. A parser success or nonnull object is insufficient evidence for “particle applied.” Retain the failed resource/provider identity and safe recovery state.
- A possible combined provider can expose an explicit retirement service that drains pending renderers under the correct context even when ordinary rendering stops. Thread/context authority, partial close, device completion, and retry custody need qualification before adopting it.
- Keep the existing provider and queue policies when their contracts are appropriate. A different capacity, admission, or degradation policy requires its own visual, scheduling, counter, and compatibility evidence.

These are independent proposals. No mod implementation, pack change, provider installation, or rollout was selected. Definition/provider coverage, complete fields and concrete consumers, GPU/native evidence, cross-platform execution, coexistence, UX, and the full research intent remain unfinished.
