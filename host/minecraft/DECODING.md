# Resource decoding boundary

The first native band exercises **169 generated inputs across 15 resource families** against the original signed Minecraft clients: 76 calls in 1.21.1 and 93 in 1.21.5. These are headless parser and codec calls with explicit vanilla registry initialization. They do not start a game client, resolve a resource stack, bake models, allocate GPU targets, render a frame, join a server, or read an account or world.

The [Lean rules](Decoding.lean), [Bend rules](Decoding.bend), and [retained comparison](evidence/codec-conformance.json) cover **96 cases in eight families**, including selected decoded values. The remaining 73 observations are retained without claiming model agreement. The [expanded host research](intent.md) remains incomplete. These vanilla observations do not qualify modded profiles or later comparison targets.

## Findings and consequences

| Family | Observed boundary | Consequence for the host model |
| --- | --- | --- |
| Pack metadata | Both versions accept fractional numeric format values, narrowing 34.75 to 34, and accept a negative format number. Invalid optional supported ranges disappear while required fields still succeed. | Numeric decoding, optional-field recovery, compatibility presentation, and feature availability need separate rules. A format number is not a capability witness. |
| Resource identifiers | Both accept `minecraft:../fixture` and an empty path; uppercase namespace and the tested Unicode path fail. | Lexical identifiers do not establish safe filesystem admission, a resolvable resource, or a path escape. |
| Overlays | Empty entries succeed, missing entries fail, slash-containing directory fails with a partial result, and `..` passes the directory codec. | Directory decoding, overlay applicability, and physical resolution remain distinct. |
| Resource filters | An empty block list succeeds; malformed regex fails with a partial result. | A partial codec value is not full acceptance. The resource manager's filtering and stack behavior remain untested here. |
| GUI scaling | A scalar border of zero fails, while four explicit zero sides succeed. A nine-slice with no center fails. | Preserve scalar and record alternatives; equal-looking border values need not take the same validation path. |
| Atlas sources | Single, directory, filter, and palette examples decode. Unknown type and missing directory source fail; an empty source list succeeds. | Decoding an atlas operation does not load an image, resolve a palette, stitch, upload, or publish it. |
| Font definitions | Negative space advance succeeds. Multi-codepoint space keys and ragged bitmap grids fail; a reference succeeds without loading the referenced font. | Glyph-source grammar, reference closure, rasterization, texture ownership, and layout are separate consumers. |
| Animation | Legacy primitive `-1` frame index decodes; the successor rejects it. Both reject tested zero frame time/width and accept empty frames. | The baseline primitive path lacks the object's index check. Image/frame bounds are still enforced at a later boundary; no successful playback is inferred. |
| Texture metadata | Baseline numeric blur `1` becomes false and string `"true"` becomes true. Successor rejects both non-boolean forms. | Gson coercion and strict boolean codecs are different profile rules. |
| Particles | Empty or absent texture lists decode; an invalid identifier fails. | Successful description parsing does not establish a usable sprite set or simulation behavior. |
| Sounds | File/event examples and an absent sound list decode. Zero weight and negative volume fail. | Event registration, reference recursion, external audio bytes, loading, playback, and user volume policy remain distinct. |
| Model geometry | Both reject scalar angle 61, XYZ notation without an axis, and extent -17. Both accept the unknown `shade_direction_override` field. | Ignoring a field does not implement its shading semantics. Parent/texture resolution and baking remain outside this call. |
| Successor item programs | Empty, model, empty composite, condition, select, range, and special examples decode; missing model and unknown node fail. | These are selected registered grammar examples, not complete property/context or rendering qualification. |
| Equipment | Successor accepts a humanoid layer, rejects empty layers, empty groups, and an unknown group. | A nonempty known layer definition still needs assets, equipment state, a renderer, and native lifetime rules. |
| Post-effects | A target with zero width is accepted **as fullscreen**, while positive fixed dimensions select a fixed target. | The fixed-size codec can fall through to the fullscreen unit codec. Record the resulting variant; acceptance alone loses this distinction. |

The 96 modeled cases cover metadata, identifiers, GUI scaling, animation, texture metadata, geometry, equipment, and post-effect target alternatives. Formal functions consume explicit projected lexical/type/dimension facts. The [projection](codec_projection.py) rejects unsupported shapes; it is not a general Gson, DFU, regular-expression, component, floating-point, or resource-loader implementation. Extent and angle examples use bounded integers and exact half-degree inputs. The geometry projection admits only empty or one-element generated fixtures with a fixed face/origin shape. Post-effect comparison admits only zero or one target and no passes.

The models prove conditional domain rules and include counterexamples to treating parsing as consumer readiness. They do not prove that Minecraft implements the entire abstract model. Both models share the authored Python projection premises; agreement does not independently verify that adapter. Selected native fields, six decoder refusals, six adapter refusals, and nine changed-observation controls limit accidental agreement on the retained boundary.

## Source and execution identity

[Source selections](codec-selections.json) bind the reviewed canonical classes to original client class-entry hashes and privately retained readable inspection views. [Source acquisition](sources.json) pins the official clients, mappings, and asset indexes. Remapped/decompiled classes supplied inspection views; the probe executes the **untouched signed client JAR**, with the study observer in its own package and the exact cached official runtime libraries. No transformed client is executed. This does not assert equivalence of the decompiled view to the binary.

Each retained capture contains generated [baseline inputs](evidence/codecs-1.21.1-20261125T025026851737Z/cases.json) or [successor inputs](evidence/codecs-1.21.5-20261125T025106778996Z/cases.json), raw observed JSON, frozen authored producer files, original artifact/class/library/tool identities, and command outcomes. Full argv and mapping locator payloads stay private; their digests and the collector's argument construction are retained. Original game source, mappings, binaries, textures, libraries, and installation contents are excluded from Git. The two omitted successor Linux epoll native libraries are not required by this macOS decoding profile.

The [failed collector attempts](evidence/collector-failures.json) remain attributed separately. An unsigned observer in the client's default package encountered a signer collision before cases ran. Return-type ambiguity in legacy serializer mappings and a removed successor `fromString` method caused observer lookup failures, not native parser refusals. Gson's missing optional compile-time annotations also stopped one observer build before execution. Qualified captures use return-qualified bridge locators, the successor's actual `fromStream(Reader)` method, and compiler warnings as errors except dependency classfile annotation warnings. Original failed observations were retained privately, never rewritten into product outcomes.

## Verification and next boundary

After compiling the tracked formal sources with `python3 scripts/check-rules.py`, the pure comparison is:

```sh
python3 host/minecraft/codec_conformance.py
```

Set `LEAN` and `BEND` to the pinned tools if they are not on PATH. This command uses retained generated evidence only. `native_codecs.py` and `export_codecs.py` are owner-run collection/export tools; ordinary CI must not run them. Acquisition is explicit and private, and the collector does not download missing inputs.

The [resource-selection band](RESOURCES.md) adds scoped pack priority, resource-stack, filter, and metadata observations. Remaining work includes reload prepare/apply/failure behavior, full definition/property inventories, consumer/context relationships, sound/font/atlas merge policies, native lifetime boundaries, exact provider refinements/gates, and the expanded version/edition/provider audit. No backport or production change is selected.
