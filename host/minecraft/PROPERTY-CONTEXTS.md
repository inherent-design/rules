# Property values, context, and effects

This partial band follows [item programs](ITEM-PROGRAMS.md). Its selected property methods have not been invoked in a game. The separate host-free cache comparison matches 13 original scenarios and 41 action snapshots in Lean and Bend. The [contract map](property-context-contracts.json) records 33 selected Modefite handlers, 33 Compat adapter records, and 51 existing source-view identities against [provider-sources.json](provider-sources.json). Native game properties, full provider support, and rollout remain unqualified.

The item-program compiler delegates values to a provider. A syntactically admitted program therefore does not establish that its properties exist, that the required world/input/registry state is available, or that evaluation is pure. This map follows those dependencies before defining more proofs.

## Modefite's selected built-ins

The inspected registries declare nine select handlers, 14 condition handlers, and ten numeric handlers. Registration declarations do not establish the effective initialized handler map. An absent select handler returns null, an absent condition handler returns false, and an absent numeric handler returns zero. These fallback meanings must remain separate from unknown or unavailable evidence in a research adapter.

| Select property | Selected inputs and result boundary |
| --- | --- |
| `block_state` | Looks up the configured property name in the stack's block-state component; absent component or key yields null. |
| `charge_type` | Iterates charged projectiles with ordered arrow/rocket/spectral/unknown decisions. The two flags affect those branches; their names alone do not specify the policy. |
| `component` | Registry lookup, special entity-variant helper, component/string conversion, and warning deduplication. Compat replaces this path with explicit typed projections. |
| `context_dimension` | Requires a non-null supplied entity, then reads the client world's dimension rather than simply using that entity's world. |
| `context_entity_type` | Reads the supplied entity's registered type or returns null. |
| `custom_model_data` | Converts the baseline integer component to a string or returns null. It does not supply a later string-array component. |
| `display_context` | Serializes and lowercases the display enum. |
| `main_hand` | Uses the entity's main arm or the client's player-information option, then lowercases it. |
| `trim_material` | Reads the trim material's registered name or returns null. |

The selected zero-argument `toLowerCase()` calls have a host-locale dependency. Neither locale-independent spelling nor an observed locale failure has been established for these handlers. Typed identifier normalization and actual returned strings need their own comparison.

| Condition property | Selected inputs and effects |
| --- | --- |
| `broken` | Compares remaining damage capacity with one. Reachable stack constraints and integer arithmetic remain relevant. |
| `carried` | Requires a local player and compares the menu's carried stack by object identity. |
| `component` | Resolves a predicate type and decodes against connection registries; failures can update the shared warning set and log. |
| `custom_model_data` | Tests presence of the baseline integer component and records a warning about the representational difference. |
| `damaged` | Delegates to the stack's damage predicate. |
| `extended_view` | Reads Shift state through the screen API. |
| `fishing_rod/cast` | Tests whether a supplied player has a fishing hook. |
| `has_component` | Registry/component presence and optional patch membership; refusal/fallback warnings are effectful. |
| `keybind_down` | Reads the resolved key mapping's current pressed state; absent mapping yields false. |
| `selected` | Reads a player's used hand and compares the hand's stack by object identity. |
| `using_item` | Requires active use and the same stack object. |
| `view_entity` | Compares the supplied entity with the camera entity or client player. |
| `modefite:hovered_item` | Reads container-screen slots, mouse coordinates, GUI/window dimensions, and accessor-provided offsets; compares the hovered slot's stack by identity. |
| `modefite:submerged` | Uses the entity or stack representation, position/eye position, world fluid state, and configured fluid registry entry. |

| Numeric property | Selected inputs and effects |
| --- | --- |
| `bundle/fullness` | Delegates to the baseline bundle fullness display calculation. |
| `compass` | Uses holder, world/dimension, target position, rotation, game tick, optional random input, and mutable interpolation state. |
| `cooldown` | Reads player cooldown with the selected zero partial-tick argument; non-player yields zero. |
| `count` | Uses count and maximum stack size; chooses division or clamping from the normalization flag. |
| `crossbow/pull` | Uses charge state, holder-dependent charge duration, and ticks used. |
| `damage` | Uses damage and maximum damage; chooses division or clamping. |
| `time` | Uses source enum, world time/moon/random value, tick, and mutable angler state; missing holder/world/source yields zero. |
| `use_cycle` | Uses same-stack identity, remaining-use ticks, and the configured float period. |
| `use_duration` | Uses same-stack identity and either remaining ticks or duration minus remaining ticks. |
| `custom_model_data` | Returns the baseline integer as a float, with warning deduplication; absence yields zero. |

Numeric range, division, zero denominators, overflow, random algorithms, and actual game reachability are not inferred from method names. The selected [float subset](../java/FLOAT-ORDER.md) qualifies only its named atoms and operations.

## Compat's value adapter

The inspected `NativeResourceValues` admits eight ordinary select properties plus a separate component lane, 13 ordinary condition properties plus a separate component-predicate lane, and ten numeric properties. Each lane checks property-specific fields before constructing its value reader. Unknown properties and fields refuse. This is a refinement of the generic compiler's broader field allowance.

Ordinary select keys must be strings. Three identifier-valued properties normalize identifiers; `main_hand` restricts keys to left/right. Metadata is decoded through a deep copy whose recursive branches are replaced with empty nodes. That metadata parse is distinct from compiling the actual child programs. Current ordinary values delegate to the selected Modefite handlers.

The component-select lane explicitly supports enchantments, stored enchantments, suspicious-stew effects, custom name, painting variant, and axolotl variant. Its typed projections preserve more structure than arbitrary component `toString()`. They still require the named native components and, for some values, registry/world availability. Enchantment levels and list lengths have their own bounds. Missing native data uses a dedicated absent object; it is not the same value as null, an empty map, or a failed research observation.

Component predicates admit selected enchantment/stored-enchantment forms and writable-book page-size constraints. A predicate can parse independently of registries, refuse immediately, or retain a deferred registry binding. Deferred binding uses provider object identity, can fail to produce a predicate, and can log. Cache clearing resets those retained bindings. The actual mutable-registry and thread ownership contracts remain open.

Three tint kinds are selected: constant, grass, and potion. Constant/color decoding, grass temperature/downfall, optional potion component data, fallback colors, and opaque-alpha behavior are separate contracts. A generic authored tint marker does not qualify them.

## State and observation are coupled

Clock and compass handlers retain interpolation state. A wobbly update is gated by game-tick equality; an instant clock can update every call. Random target generation and interpolation updates occur at different points. In particular, the selected random clock source can consume randomness before the angler's same-tick update guard. No-op interpolation does not imply no evaluation effects.

Compat's `ResourceValueCache` has a positive capacity, object-identity keys, per-kind projections, FIFO insertion order, and a dedicated absent result. A hit does not promote an entry in the insertion queue. Null components bypass projection. Successful null projection results become the absent sentinel; thrown projections and clear callbacks have separate partial-effect boundaries. The isolated cache comparison below qualifies selected cases; it does not establish actual component or registry behavior.

`ItemDefinitions` creates a capacity-1,024 cache per preparation. Its inspected binding path initializes the property registries and publishes an active epoch after building native root metadata. Logout/client-level-unload handling advances a session marker and clears active projections. Prepared maps are copied, but their contained value readers and cache are not thereby pure or deeply immutable. Owner-thread or synchronization assumptions remain explicit obligations.

The diagnostic `selectedModels` path calls the same root-layer selection used by resolution/rendering. By source inference, it can therefore exercise warning sets, caches, random sources, or interpolation state. A future probe must report that footprint or use a captured state. It cannot advertise observational purity from its return type. This is not a measured full-game defect or proof that a particular diagnostic changes pixels.

## Evidence qualification and next checks

[ResourceCache.lean](ResourceCache.lean) has 17 laws for admission/refusal, unchanged hits, absent versus missing, retained failure effects, callback registration, clearing, and callback suffix/count preservation. [ResourceCache.bend](ResourceCache.bend) supplies ten checked laws and the executable selected state transitions. Entries represent this cache's ownership, not all references or physical allocations. Callback failure counts belong to the authored fixture; they are not a universal model of arbitrary Java closures.

The original cache and its enum ran with equal-but-distinct string objects and non-reentrant authored callbacks. Thirteen scenarios include 41 project/register/clear action snapshots; constructor, getters, and setup are counted separately. Sixteen research-decoder refusals, one direct CLI refusal, two unneeded-unknown examples, four changed-input controls, and ten changed-observation controls accompany the comparison. Two observation mutations fail profile/shape checks; eight disagree with the model outcome. Model-internal cells and callback state are not claimed as directly inspected native fields.

The [retained comparison](evidence/resource-cache-conformance.json) and [role frame](evidence/resource-cache-identity-frames.json) bind those meanings. Research outcome labels distinguish constructor, projection, and clear failures; they are not new production error codes. Cache absence, a cached absent sentinel, no returned value after an exception, and unavailable observation evidence remain distinct.

Selected failures preserve their consequences. A throwing projection leaves an admitted cache entry, and a later projection can fill it. A throwing clear callback sees already-cleared entries and prevents later callbacks in that invocation; registrations remain available for retry. These failures were authored deliberately. They do not demonstrate that the game's actual clear callback throws, or that an application has a corruption bug.

The native profile is the pinned Java 21/macOS arm64 setup with explicit Gson and the delivered Compat artifact. One compiler and one JVM completed; both owned groups were absent. Exactly two original cache classes were loaded and byte-audited, with no Minecraft or NeoForge class. No live components, worlds, GUI, renderer, Windows/Linux cache runtime, Java 17/25 cache runtime, GC measurement, or physical-memory reclamation was exercised. The research decoder's capacity/trace/marker bounds and nonpositive-capacity projection remain distinct from the original constructor's positive-capacity policy.

The decompiled `ResourceComponents.variant` view appeared to cast its absent sentinel to a resource identifier. A bounded original-class `javap` inspection contains no such cast before `Objects.requireNonNullElse`. The attributed source also has no cast, and the existing compiled class matches the delivered class bytes. The apparent cast is not adopted as product behavior. The private disassembly receipt is `component-bytecode-20261125T194813125805Z`; its tool group retired. No target method was invoked by that inspection.

After `scripts/check-rules.py`, ordinary CI runs `resource_cache_conformance.py` and `property_contexts_check.py`. They use retained data and pure models. Owner-local `resource_cache_observations.py --check-export` independently verifies private source/tool/class/stream identities and normalized export fidelity; it starts no JVM. `resource_cache_probe.py` is the separately selected native collector and is excluded from ordinary CI.

The [owner-check receipt](evidence/property-cache-checks.json) binds the model, map, source-identity, and clean public replay checks. It claims no publication or remote CI result for this cohort.

Effective metadata null/default rules, all vanilla property/tint registries, handler initialization, registry replacement, transformed hooks, graphical input, rendering, and retirement still need their own evidence. A proposed diagnostic should distinguish an unavailable value from an observed fallback and disclose live state changes. A captured diagnostic snapshot or explicitly effectful live query remain independent design choices. Neither is selected for implementation. No provider replacement, pack change, or deployment is selected.
