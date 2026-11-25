# Independent Java 1.21.11 resource contracts

This lane uses the exact original 1.21.11 client and official mappings already selected in [targets.json](targets.json). It does not borrow native qualification from 1.21.5 or 26.3. Source inspection, original deserialization, a controlled CPU-consumer boundary and static host/API discovery have separate evidence.

## Definitions and source context

The [registry map](java12111-registry-catalog.json) contains 72 literal registrations in eight selected categories and 80 attributed associated source files. The [three-version comparison](java12111-findings.json) preserves each version's own source identity.

| Category | 1.21.5 | 1.21.11 | 26.3 | Selected literal difference |
| --- | ---: | ---: | ---: | --- |
| Item nodes | 8 | 8 | 8 | Same IDs; per-type semantics remain independent. |
| Conditions | 13 | 13 | 13 | Same IDs, without context/evaluation equivalence. |
| Select properties | 10 | 10 | 10 | Same IDs, without value-domain equivalence. |
| Numeric properties | 10 | 10 | 10 | Same IDs, without numeric/default equivalence. |
| Tints | 8 | 8 | 7 | `map_color` is absent from the selected 26.3 registry. |
| Special renderers | 11 | 13 | 13 | 1.21.11 adds `copper_golem_statue` and `player_head` relative to the inspected 1.21.5 set. 26.3 adds bell/book/end-cube entries and lacks bed/sign/hanging-sign entries. |
| Atlas sources | 5 | 5 | 5 | Same IDs; resource ownership/lookup remains separate. |
| Font providers | 5 | 5 | 5 | Same IDs, with independently located implementations. |

These are set differences at selected source artifacts, not introduction dates or unsupported-feature findings. The original-mapped 1.21.11 model-wrapper codec exposes model/tints; the inspected 26.3 wrapper separately exposes transformation. A shared `minecraft:model` identifier cannot select its grammar alone.

The private inspection slice covers 688 class entries and yields 377 views, including pack/reload, models, textures, fonts, sound, shader and particle consumers. The remapper/decompiler use explicit Java 21, two active processors and 512 MiB heaps, without Gradle. External inheritance warnings remain in the raw remap log. A completed transformation is not a proof of semantic preservation; no mapped class was executed.

## Original element and face decoding

The [first capture](evidence/elements-1.21.11-20261125T075852035159Z/receipt.json) executes the original element and face Gson deserializers on 40 authored parsed-JSON inputs. Original client signatures remain intact; only the authored observer is compiled. The exact 25 selected Java-only libraries are bound to the pinned launcher metadata. Shared identical library artifacts are reused read-only. The capture stops at deserialization, before resource lookup, game bootstrap, registry/world loading, or renderer launch.

| Boundary | Observed result |
| --- | --- |
| Extents | The tested coordinates outside -16..32 refuse; reversed from/to extents inside the range decode. Acceptance does not prove usable geometry. |
| Faces | Empty, missing and null face containers refuse. A named face whose value is null survives inside a nonempty decoded face map. |
| Face direction versus cull direction | An unknown face key refuses. An unknown or uppercase cull name decodes to no cull direction. Those names have different consumers. |
| Face payload | Missing texture, a 45-degree face rotation and a three-value UV refuse. Empty texture text, negative tint and extended four-value UVs decode. Their backing, layout and rendered behavior remain unqualified. |
| Shade | Boolean false survives; the selected string form refuses. The tested later shade-override field is ignored by this selected decoder. |
| Light emission | Numeric 1.9 becomes 1; -0.5 becomes 0. The tested 16, -1 and string value refuse. The selected diagnostic's integer wording is not a strict raw-number grammar. |
| Rotation | Euler, mixed scalar/XYZ selection and rescale retain their decoded states in the selected controls. Matrices are preserved as original output, not proved geometry. |

[Lean](Elements.lean) and [Bend](Elements.bend) match the bounded decisions, shade/light values, face/null/cull counts and selected rotation state. Coordinates and face metadata have separate readbacks. The models do not implement all Gson grammar, numeric overflow, arbitrary malformed shapes, diagnostics, texture references or every payload field. They reuse the already explicit rotation decision with this independently observed profile; they do not infer version equivalence from the reuse.

The reader's input profile uses bounded numeric magnitudes, one fractional digit for light, nonnegative integer rotation angles and the selected origin. Those restrictions belong to the study adapter. In particular, negative fractional light is admitted here; the earlier endpoint-codec study's DTO deliberately excluded negative fractions. Light values and format-version tokens are separate domains.

The acquisition helper recorded its producer hash at completion; its matching source was preserved afterward with an explicit attribution limit. The native collectors independently froze their producers and exact library receipts before compilation/execution, and an independent audit rechecked every selected coordinate, size, SHA-1 and SHA-256 against the pinned metadata and actual bytes. The helper now freezes its producer before future acquisitions; no native observation was repeated or rewritten for that improvement. The [host observation](evidence/java12111-host-after.json) was taken after collection and is labeled accordingly, rather than inserted retrospectively into the original receipts.

## An admitted null face is not always dormant

The [controlled consumer capture](evidence/element-consumer-1.21.11-20261125T080334688422Z/receipt.json) first deserializes each element, then invokes the original `SimpleUnbakedGeometry.bake`. Proxy implementations supply only `ModelBaker.sprites` and intercept `SpriteGetter.resolveSlot` before actual lookup. Texture slots, model state and debug context are unused before the tested stop/return boundaries. No full bake or real resource provider is supplied.

Forty-eight cases cover all eight zero/nonzero extent combinations and all six single-face directions with a null face. Twelve selected faces throw a null dereference after the `sprites` callback and before texture lookup. Thirty-six return empty quad collections with no adapter calls. Three non-null controls add two empty returns and one deliberate lookup interception. An intercepted lookup is not a successful texture resolution or completed bake.

The condition is specific: X-facing geometry needs nonzero Y and Z extents, Y-facing geometry needs X and Z, and Z-facing geometry needs X and Y. A zero-area face can remain untouched; an active null face cannot supply its texture. Both models predict all 51 recorded outcome/prefix projections. The Lean counterexample ties an admitted null face to a later consumer failure under named premises, giving the existing decoded-versus-prepared distinction an actual witness.

This is not a full-game crash claim. The inspected `ModelBakery` caller catches and logs selected block/item bake exceptions with model context and returns null. That caller, its map transformation, fallback and eventual user-visible presentation were not executed by this fixture. Preserve its existing diagnostics and qualify the whole path before proposing a product fix.

## Host and runtime differences

The [static 1.21.11 map](host-api-1.21.11.json) reads every original class with Java 25's Class-File API. Java 25 is the inspection tool runtime; the target declares Java 21, and its 10,291 observed class headers are 65.0. The scan does not define or execute a target class. The 40/51 method collections independently use the recorded Temurin 21 runtime on macOS arm64.

| Selected direct invocation owner family | 1.21.11 | 26.3 |
| --- | ---: | ---: |
| LWJGL GLFW | 105 | 0 |
| LWJGL SDL | 0 | 249 |
| LWJGL OpenGL | 164 | 200 |
| LWJGL Vulkan | 0 | 893 |
| RenderPearl | 0 | 5,537 |

These are static instruction counts inside the original JARs, including helpers and exception paths. They are not operations, costs, active backend selection or platform support. Reflection, invokedynamic targets, external libraries, loader/provider additions, native drivers and reachability remain unresolved. A scoped absence is not global absence. The 1.21.11 census has 4,840 selected direct calls and 29,041 unresolved invokedynamic instructions; the [26.3 map](HOST-APIS.md) retains its separate basis.

This makes host-version ownership concrete: window/input/context and GPU contracts must identify the actual wrapper/backend and selected runtime. An OpenGL/GLFW source witness cannot qualify SDL/Vulkan, and declared native libraries do not prove loadability on Windows, GNU/Linux or macOS. Windows Server CI still does not qualify Windows 11 LTSC, nor does replaying these facts execute Minecraft on those hosts.

## Selectable design directions and next work

Keeping native decoding and the current caller's diagnostics is a valid alternative. An authoring preflight could retain explicit null faces and report resource/face/geometry context before an active face reaches baking. Rejecting every null face would instead be a format-policy change and needs migration/preservation rules; removing faces can also turn a nonempty face map into an independently refused empty map. Do not silently rewrite that state.

A version-aware report can distinguish decoded, ignored-by-this-decoder, references unresolved, preparation failed, lookup intercepted and rendered-unqualified. The shader-override example especially needs an applied-versus-recognized distinction. Missing older gameplay data and custom renderer obligations remain separate from data conversion. These are proposals, not implemented validators or selected backports.

`element_conformance.py` replays retained observations with both models, including eight DTO refusals, adapter refusals, five changed premises and five changed native fields. `host_api_replay.py` checks both static maps. Ordinary CI runs those pure comparisons after formal compilation, without a JVM, game or studied application launch.

Complete per-type fields/values/defaults, actual reference and context resolution, pack/overlay native validation, parent/cycle behavior, reload publication/retirement, providers, other platforms and rendering remain open. The larger host/Minecraft intent remains active.
