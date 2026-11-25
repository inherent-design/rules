# Item-program grammar and consumers

This band compares six selected Modefite/Compat node grammars, their context reads, dependency discovery, compilation, and layer selection. Both models agree with 36 retained original Compat compiler requests and 78 returned contexts, producing 67 layers. A separate source map covers the six node bodies at four modern vanilla milestones. These are partial contracts; whole renderers, effective property registries, provider composition, and a replacement mod remain unqualified.

## Inputs and ownership

Modefite's selected loader discovers `items/` followed by `modefite_items_override/`. It reads root hand-animation, GUI sizing, and swap-scale values, decodes the nested `model`, registers definitions, and discovers model dependencies. Its selected root record is distinct from the recursive node codecs. The root loader catches per-resource exceptions and logs them. Full reload publication and old registry state are not exercised here.

Compat's `ResourceDefinitions.compile` accepts a root object and a `Values<C>` implementation. The generic compiler owns grammar, recursive structure, bounds, model dependencies, and ordered output layers. The `Values` implementation owns select-key decoding, live select values, conditions, numeric properties, and tint functions. Its actual game adapter, `NativeResourceValues`, has further property-specific admission and context rules; a generic compiler witness cannot substitute for them.

The native study calls the original delivered Compat compiler with authored `Values<JsonObject>` callbacks. Those callbacks expose one string selector, Boolean condition, double-valued numeric input, and integer tint. Their event list records fixture callback activity, not arbitrary game effects. The contexts are explicit snapshots; no actual item, entity, registry, key binding, world, or renderer is supplied.

## Six node families

| Node | Modefite selected codec fields | Compat selected compiler contract |
| --- | --- | --- |
| Model | Required resource IDs `type` and `model`. | Required type/model; optional tint array, at most 32 entries. Each tint delegates to `Values.tint`. The model ID joins the compiler dependency set. |
| Empty | Required `type`. | No output layer. Extra node fields refuse. |
| Composite | Required `type` and recursive `models` list. | Compiles children in list order; appends their layers in that order. An empty list emits no layers. |
| Condition | Required type/property and both recursive branches; optional predicate/value/component/ignore-default/keybind/fluid fields. | Compiles a predicate through `Values.condition` and both branches; evaluation selects one branch. Property-specific interpretation remains with the values provider. |
| Select | Required type/property/cases; optional fallback, block-state property, ignore-default, ignore-unknown, and component. Each case contains model and scalar-or-list `when`. | Compiles a selector, cases, and fallback. The selector decodes each key; duplicate decoded keys and empty alternatives refuse. Evaluation performs key lookup, then uses the fallback. |
| Range dispatch | Required type/property/entries; optional fallback/target/wobble/normalize/source/period/remaining/scale. Each entry requires model and float threshold. | Finite float thresholds, bounded entries, duplicate policy, sorted dispatch, a numeric callback, float scale, and fallback. Evaluation uses float total ordering and explicitly handles NaN. |

The [field map](item-program-field-contracts.json) retains these 12 provider records, four nested forms, four vanilla root/context profiles, and 24 vanilla node-body records. Their [source ledger](item-program-sources.json) binds 36 selected private views and 83 original outer/nested class identities. These lists are not complete claims about every property or renderer in five vanilla releases. Polytone's custom-item-model language is a different override grammar, not a seventh node in this table. Custom renderer types and absent older gameplay state remain explicit dependencies.

Modefite's condition constructor supplies false for omitted `ignore_default`, water for omitted fluid, and null for omitted optional predicate/value/component/keybind. Keybind decoding resolves an actual key-binding map. Its select constructor defaults both ignore flags to false and the fallback to null. For selected resource-ID-valued properties it normalizes valid case strings through resource-ID parsing; malformed strings remain as strings. Each case's alternatives become a `HashSet`, while the case list keeps its order. The exact library treatment of malformed/null inputs and all game reachability still need their own comparisons.

Modefite's range constructor defaults wobble and normalization to true, period and scale to one, remaining to false, and target/source/fallback to null. The selected recursive resolver sorts entries by descending float threshold and tests `value >= threshold`. Select resolution walks case order. Missing select/range fallbacks can request a native missing model and mutate the warning-deduplication set. Its empty composite instead enters a missing-model path. Those are inspected consumer distinctions, not observations of a running Modefite client.

## Compiler boundaries

Compat checks allowed root and node fields explicitly. Its root admits model, hand-animation, GUI sizing, and swap-scale fields. Missing required values and explicit null refuse; absent optional Boolean/number fields select declared defaults. Selected flags default to true/false and swap scale to one. Root swap scale must also remain finite after conversion to float. The latter check occurs after node compilation, so callbacks can have run before that final refusal.

Recursive node depth is bounded at 32, total compiled nodes at 4,096, select case/alternative counts at 512, range entries at 512, and tints at 32. The generic method does not itself establish the separate byte limit enforced by the JSON/resource-loading path. Do not infer raw parser, encoding, duplicate-member, resource-stack, or physical path admission from this method.

Compat select keys come from the chosen selector. Duplicate decoded keys refuse even if they occur in one case or target the same child. A missing fallback compiles to a built-in missing-model leaf. This differs from an empty node or empty composite. Its dependency set records explicit compiled model leaves; the built-in fallback is supplied separately. A dependency set is therefore not automatically the complete renderer retaining-root set.

Range entries with an equal float key and identical model JSON collapse; conflicting bodies refuse. The selected implementation distinguishes negative and positive zero as float keys. Entries are sorted, and binary dispatch uses `Float.compare`. NaN property values use the fallback. These policies need to be preserved or explicitly changed in any proposed conversion; matching node/type labels do not resolve the differences from another resolver's comparison operators.

## Captured original calls

The [exported capture](evidence/item-program-20261125T183811870111Z/receipt.json) contains 36 original compiler requests: 21 returned roots and 15 refusals. The returned roots produced 78 captured context results through the original layer consumer. It covers all six node types, list order, explicit and missing fallbacks, duplicate select keys, repeated/conflicting thresholds, signed-zero selection, NaN callback input, finite-float refusal, root/field policy, depth/node/case/tint limits, and selected identifier spelling. Both models match the selected results; this does not establish a general JSON codec correspondence.

The signed-zero case selects one layer for negative zero and another for positive zero; the NaN context selects the missing fallback. Those numeric values come from authored callbacks, not a claim that every game property can produce them. The empty composite returns no layers. A later root-scale refusal retains one earlier tint-factory event. That event is an authored log append; it does not prove surrounding IO, allocation rollback, or game state changes.

The generic identifier check accepts the selected `study:../owned` spelling. The witness performs no filesystem resolution. This is another lexical-ID versus host-path boundary, not a demonstrated traversal or authorization defect. Actual resource lookup and path guards remain separate consumers.

One bounded compiler and one JVM completed and their owned groups were absent. The fixture uses Temurin 21.0.13.1+2-LTS on macOS arm64 and Gson 2.10.1 with the pinned Compat artifact. Fourteen original compiler classes were loaded and byte-audited; no Minecraft or NeoForge class was loaded. Authored inputs, producers, original outputs, command channels, and normalized provenance are exported. Original classes, exact class paths, and the class-load log stay private. No production, pack, account, world, or live store changed.

## Versioned bodies and consumers

Java 1.21.1 has the legacy model pipeline but lacks the selected modern `ItemModels`/`ClientItem` registrations in the prior complete mapping review. The four newer references have independent source identities:

| Reference | Root and consumer distinctions |
| --- | --- |
| 1.21.4 | Required model and optional hand-animation flag. Selected properties receive a nullable living entity. |
| 1.21.5 | The same selected root fields; registry-context swapping and per-level value remapping refine condition/select consumption. Equal JSON field names do not establish equal live registry behavior. |
| 1.21.11 | Adds GUI oversizing and swap-animation scale to the selected root. The consumer receives an `ItemOwner`; condition/select derive a nullable living entity while numeric properties receive the owner directly. Even empty output can append internal model identity. |
| 26.3 | The selected nonempty node bodies add optional `transformation`, composed with the parent matrix during baking. This is a different field and owner from geometry-root `transform`. Cuboid leaves validate atlas use and retain transformation/material/tint obligations. |

The official [1.21.6 pre-release notes](https://www.minecraft.net/en-us/article/minecraft-1-21-6-pre-release-1) locate the GUI-oversizing addition between the selected 1.21.5 and 1.21.11 references. The [25w41a notes](https://www.minecraft.net/en-us/article/minecraft-snapshot-25w41a) locate the swap-scale addition. These are documentary boundary witnesses, not additional selected client executions. In the pinned 1.21.11 and 26.3 JARs, `spear_in_hand` names a geometry/model asset with a generated-item parent. Its description in the [1.21.11 notes](https://www.minecraft.net/en-us/article/minecraft-java-edition-1-21-11) does not add a registered item-program node; the ledger retains both asset-member identities separately from `ItemModels`.

Vanilla select-case validation matters before baking: the inspected property-type codec rejects an empty case list and duplicate decoded values. Map insertion in a later method does not imply that authored duplicates normally reach a last-wins consumer. Compat's generic empty case list instead returns its fallback. Vanilla range selection also retains a size-sensitive linear/binary search distinction; the selected source does not establish Compat's duplicate-body policy or a universal last-equal index. Property dispatch, null/unknown-field treatment through DFU, all tint types, raw parsing, and live game reachability remain incomplete.

## Models and verification

[ItemProgram.lean](ItemProgram.lean) and [ItemProgram.bend](ItemProgram.bend) model selected compilation, refusal order, explicit dependencies, callback events, bounds, ordered layers, and dispatch. Twenty-one Lean laws and eight Bend laws check those contracts. The shared [float-order model](../java/FLOAT-ORDER.md) contributes 15 Lean and eight Bend laws for minus ten, signed zero, plus ten, and one NaN class, with exact scaling by plus or minus one. It excludes arbitrary arithmetic, infinities, rounding, and NaN payloads.

The research decoder binds the source artifact, schema, and authored context contract. It admits a bounded postorder tree and role-specific model/key/body identities; it refuses unknown or inconsistent evidence. The [retained identity frame](evidence/item-program-identity-frames.json) makes those roles inspectable. Homogeneous empty-child runs are compressed only after verifying their exact no-callback/no-layer shape. Threshold-body equality is limited to numeric-free JSON. Generated raw token spellings are pinned; alternate numeric tokens, duplicate JSON members, and full Gson correspondence remain outside the projection. These are named premises, not a translation proof.

The [retained comparison](evidence/item-program-conformance.json) rejects 21 unsupported research packets, including one also checked through the direct CLI. Three unneeded-unknown examples remain admitted. Six changed-input controls and 12 changed-observation controls distinguish semantic disagreement from malformed observation shape. Native refusal codes remain valid captured outcomes; research-decoder exit 2 is a different result. Batched negative checks independently invoke the same decoder and do not invoke the original compiler again.

After `scripts/check-rules.py`, ordinary CI runs only:

```sh
python3 host/minecraft/item_program_conformance.py
python3 host/minecraft/item_program_contracts_check.py
```

Owner-local `item_program_observations.py`, `item_program_contracts_check.py --private`, and `export_item_program.py --check` separately recheck original bytes, private views, tools, class origins, and export fidelity without launching Java. Source-view identity and class origin do not prove decompiler correctness. A failed early mutual-helper Bend draft was replaced by an explicit task machine; its diagnostics remain private and are not a product finding.

The [owner-check receipt](evidence/item-program-checks.json) binds the model, source-map, export, and clean public-subset checks. It records no completed publication or remote CI result.

## Design choices and remaining work

A proposed converter or provider must name its field grammar, property/context source, equality and ordering policy, fallback, callback ownership, and layer/bake contract. Preserve originals and refuse unsupported transformation or context requirements with a useful location. Do not silently flatten duplicate rules, replace absent gameplay state, or infer physical state from empty error-result placeholders. A diagnostic should distinguish grammar refusal, missing context/reference, conversion loss, and renderer failure.

Keeping the present providers, extending one, converting a declared subset, and implementing a new combined provider remain independent options. None is selected. Complete raw/null/unknown policies, actual `NativeResourceValues`, property/tint registries, resource-stack publication, full reload, provider coexistence, and renderer retirement still need separate evidence. This band improves the common contracts without qualifying a whole provider or selecting an implementation or asset conversion.

The separate [property/context review](PROPERTY-CONTEXTS.md) now maps selected value readers and their state dependencies, with original host-free cache comparisons. That source map does not qualify actual game-value evaluation or close the remaining property/renderer obligations.
