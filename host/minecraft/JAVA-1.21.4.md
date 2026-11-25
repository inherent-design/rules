# Independent Java 1.21.4 item and host contracts

This lane binds the exact original client and official mappings selected in [targets.json](targets.json). It independently maps 68 literal registrations, interprets the eight item-node families, and executes one original range-index consumer on 76 authored arrays. Source discovery, source interpretation, native method observations, and API permissions remain separate.

## Registrations and typed fields

The [registration map](java1214-registry-catalog.json) has eight item nodes, 12 conditional properties, nine select properties, ten numeric properties, eight tints, 11 special renderers, five atlas sources, and five font providers. Its 76 associated source identities are checked against the independent original-class census. The selected 1.21.5 conditional/select sets each add `minecraft:component`; the other selected ID sets match. This is a comparison of selected artifacts, not an introduction-date claim or semantic equivalence.

The [field and consumer map](java1214-findings.json) attributes twelve inspected source files. Whole-file field candidates in the discovery index remain candidates; this smaller map assigns meanings to specific objects.

| Item node | Selected source fields | Later obligation |
| --- | --- | --- |
| Empty | Unit unbaked codec | Empty model behavior, not arbitrary resource availability. |
| Model | Required `model` resource ID; optional `tints` list | Resolve/bake backing, then evaluate tints and set the render layer. |
| Composite | Required `models` list | Visit child dependencies and bake/update children. |
| Condition | Property dispatch plus required `on_true` and `on_false` | Actual item/level/entity/seed context determines the branch. |
| Select | Property-specific cases; optional fallback | Typed case values, map construction, missing model, and runtime selection are separate. |
| Range dispatch | Numeric property, optional scale, required threshold/model entries, optional fallback | Sort a copy during bake, evaluate the property, handle NaN, and select/update a model. |
| Special | Required `base` resource ID and nested renderer `model` | Base backing and entity-model-set/render contracts have separate owners. |
| Bundle selected item | Unit unbaked codec | Actual selected bundle contents and item resolver context. |

The outer `ClientItem` requires a `model` graph. Its source composes `hand_animation_on_swap` as an optional top-level Boolean with default true; the Java `Properties` record does not imply a nested JSON `properties` object. Similarly, `model` means a graph in the outer descriptor, a resource ID inside the model node, and a renderer specification inside the special node. A field name alone cannot select its type or consumer.

The inspected loader lists `items/*.json`, schedules per-resource reads, closes readers, logs errors inside its parse/open try, and omits null results after sequencing. This is not proof that every discovery, task-rejection, pre-try conversion, or error path is skipped. Selected resource handles do not prove immutable backing bytes, and the assembled table is not final renderer publication. Actual startup registration, loader/provider ordering, descriptor decoding, dependency resolution, bake, and rendering remain unexecuted here.

## An algorithm boundary changes duplicate selection

The [native receipt](evidence/range-1.21.4-20261125T093433562856Z/receipt.json) executes the original private `RangeSelectItemModel.lastIndexLessOrEqual` on sorted integer-valued float inputs. It does not evaluate a property, construct/bake item models, invoke render updates, or enter the game. The selected source's bake step sorts a copy before this consumer; actual callers and rendered output were not exercised.

| Sorted thresholds and query | Original observed index |
| --- | ---: |
| 15 equal thresholds, matching query | 14 |
| 16 equal thresholds, matching query | 7 |
| 17 equal thresholds, matching query | 8 |
| 32 equal thresholds, matching query | 15 |

The source uses a linear last-at-or-below loop below 16 entries and `Arrays.binarySearch` from 16. The [Java host contract](../java/ARRAY-SEARCH.md) permits any matching duplicate in the binary branch. Consequently, the [Lean](RangeIndex.lean) and [Bend](RangeIndex.bend) models **admit** all 76 recorded outcomes; they do not predict one stable duplicate index. Two unobserved legal alternatives also pass deliberately. A test that rejects every changed duplicate index would impose a stronger promise than the API provides.

Eight DTO refusals, five invalid-outcome controls, and five changed-readback refusals guard the comparison. An unpublished adapter initially relied on Python numeric equality, which could conflate Boolean false or signed zero with numeric zero. Its source/report remain private with an exclusion disposition. Explicit finite-number/type and positive-zero checks replace it; original native observations were not recollected or changed. Signed-zero semantics remain outside this selected profile.

Duplicate thresholds therefore need an explicit preservation decision for a future backport or converter. Keeping native behavior is valid. Rejecting ambiguous duplicate thresholds, choosing a stable last winner, or deduplicating entries would be separate behavior changes with possible visible consequences; none is selected or implemented. No full-game defect is claimed from the helper's observed indices.

## Host, runtime, and custody boundaries

The source inspection uses explicit Java 21 with two processors and 512 MiB heap settings. It covers 616 original class identities and 351 private views. The first discovery attempt failed because the reader assumed newer atlas registration syntax. The original 1.21.4 view uses `register(name,codec)`; the failed attempt and matching after-run producer copies remain private. This was extraction failure, not missing atlas support. Transformation completion is not semantic equivalence.

The [static host map](host-api-1.21.4.json) independently reads all 8,857 original classes using Java 25's Class-File API. It records 4,542 selected direct invocation instructions and 25,052 unresolved invokedynamic instructions. The client declares Java 21 and has 65.0 class headers; the scanner's Java 25 runtime does not upgrade that requirement. Counts are neither side-effect counts nor active backend selection. The selected 103 GLFW and 125 OpenGL direct calls do not qualify a loaded library, driver, window, or GPU.

The original method runs on the pinned Temurin 21/macOS arm64 profile, with a 256 MiB heap setting and two processors; the compiler uses 128 MiB. Both process groups retired, and an exact scoped argv audit found no remaining tool/collector process. The private class-loading log identifies 32 classes loaded from the original client. Class loading does not establish initialization, method execution, or a complete dependency/effect closure.

Twenty-two exact Java-only libraries total 35,038,355 logical bytes: 34,259,509 newly downloaded bytes and one read-only reused artifact. Original classes, transformed inspection text, mappings, libraries, and the raw class-loading log remain private. Public evidence contains authored procedures, observations, identities, and hashes. Numeric array readbacks agree before/after; this is not a host-wide no-effects claim. Tooling, logs, bytecode caches, and evidence files have their own writes. Heap settings are not measured RAM bounds.

The [source audit](evidence/java1214-source-checks.json), [retained contract comparison](evidence/range1214-conformance.json), source/census checks, and isolated formal gate have separate scopes. The [verification receipt](evidence/java1214-checks.json) records 30 Lean laws and 13 Bend laws across the shared array contract and its consumer. Ordinary CI runs only retained comparisons and formal tools. Other JVM/OS builds, floating-point edge cases, full item/context/pack behavior, actual provider coexistence, and rendering remain open. The broader host and Minecraft intents remain active.
