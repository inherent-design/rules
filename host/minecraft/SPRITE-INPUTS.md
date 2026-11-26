# Sprite frames, transparency, and supplied-image ownership

This band observes original Java Edition 1.21.1 `SpriteContents` objects over tiny owned `NativeImage` inputs. It compares **26 scenarios, 130 transparency cells, two alias-mutation observations, and two guarded access failures**. The largest image requests 32 bytes of pixel storage; the 26 sequential constructions request 520 pixel bytes in aggregate. Neither figure measures allocator overhead, physical memory, or GPU storage.

The [manifest](sprite-inputs-capture.json) binds unchanged authored requests, observations, and streams. The [owner audit](sprite_inputs_observations.py) checks the original signed client, loaded original class entries, mappings, eleven existing metadata-pinned Java libraries, exact LWJGL core archive/library, JDK tools, frozen producer, compiled helper, and VM trace. Original binaries, source views, full commands, and logs remain private. This is Java 21.0.13.1 on macOS 26.7.1/aarch64 with LWJGL 3.3.3 and the system allocator; it does not qualify other clients, hosts, loaders, or providers.

## Constructed context and actual inputs

The fixture supplies an explicit original `FrameSize`, the original `ResourceMetadata.EMPTY`, and a null sprite name. That null name is a declared context adapter; no identifier is constructed or resolved. The original constructor and methods execute unchanged, but this is not a full resource-loading path or a decoded `.mcmeta` animation.

Each backing pixel is zero-initialized, then assigned either the all-zero or all-one 32-bit word. This isolates the selected transparent/opaque mask without claiming color space, channel conversion, partial-alpha behavior, image decoding, or rendered appearance. Sixteen cases cover every 2×2 mask. Five 3×2 masks preserve a wider grid, and four cases use two 2×2 frames stacked vertically. One additional case measures a retained input alias and close behavior.

| Selected input | Observed original behavior |
| --- | --- |
| One frame with empty metadata | `getUniqueFrames()` returns `[1]`. `isTransparent` uses the sole image without applying that frame label as a backing-image offset. The label must not be silently normalized to zero. |
| Two-frame backing with explicit 2×2 frame size | The original empty-metadata path generates labels `[0, 1]`; each label reads its own vertical frame's mask. |
| 3×2 frame | Six cells remain in row-major order; they are not coerced into a square or a 2×2 fixture. |
| Write to the supplied image after sprite construction | Sprite transparency changes from true to false at that cell. The constructor did not isolate this input through a private pixel copy. |
| Close the sprite while retaining the supplied image reference | A valid-coordinate pixel read through either reference throws `IllegalStateException`. Sprite width, height, and frame labels remain readable. Java reference retention does not preserve native backing access. |

The source and original bytecode confirm the singleton `IntStream.of(1)` path. The selected nonanimated coordinate path ignores that label. This is an observed implementation contract, not a claim that arbitrary frame indices are valid for animated sprites or that frame labels are counts.

## Lifetime and dependency boundary

The original constructor retains the supplied image and includes it in its mip-level array. Sprite close invokes close on that image. The native alias case demonstrates the resulting shared state for this selected construction; it does not inspect pointer values or count native free calls. The fixture closes every returned sprite and finally closes its owned image. Its source also closes an owned image if sprite construction fails; that failure path was not exercised. All selected constructions and cleanups returned normally; both compiler/JVM groups and the exact-capture process scan are terminal/empty.

The VM trace records 18 original class entries and the exact owned core native library alongside four logged JDK libraries. It shows no initialization of the forbidden client, rendering-system, direction, network-codec, or identifier classes. No STB, FreeType, GLFW, or Tracy initializer appears. The SLF4J no-provider warning is retained. Logged native loads do not enumerate all transitive operating-system dependencies.

The child uses two active processors, a 96 MiB Java heap ceiling, a 16 MiB direct-buffer ceiling, private home/temp properties, controlled JVM startup variables, and a 30-second command timeout. These do not bound arbitrary native allocation or host-wide concurrency. The input jars are reused read-only; no download, launcher installation, personal pack, world, account, or game process is selected.

The [generated-model linework](BREADTH-LINEWORK.md) consumes sprite dimensions, unique frames, and transparency before producing edges. Its original baseline span-facing enum initializes direction and codec helpers outside this fixture's selected dependency path. **No original edge generator, model baker, ticker, upload, or renderer executes here.** A later source-fragment adapter or full original invocation must retain its own dependency and evidence boundary. The 26.3 shared-material/model-state cache and modern per-pixel side-face behavior remain separate versioned comparisons.

## Models, comparison, and controls

[SpriteInputs.lean](SpriteInputs.lean), [SpriteInputs.bend](SpriteInputs.bend), and the [typed research codec](SpriteInputsCase.lean) preserve frame labels, backing-frame selection, mask cells, and the bounded alias lifecycle. They reuse the [CPU-image model](../java/CpuImage.lean) for the selected 2×2 alias access/close projection. Retained mathematical words after close are history, not permission to read native memory. The source/observed identity coupling is an explicit premise; the models are not a translation proof of the constructor or JNI allocator.

Thirteen new Lean laws and eleven Bend laws cover the selected rules. Lean uses natural-number division/powers for mask bits; Bend uses bounded unsigned words. The codec admits widths 2 or 3, height 2, one or two initialized masks, and at most eight backing pixels. It rejects needed unknown masks, oversized/foreign profiles, a decoded-metadata interpretation, and unsupported alias contexts. No image is allocated by a model run.

Both models match all 26 scenario outputs, including frame matrices, dimensions, and alias results. Fourteen unsupported DTOs refuse; four changed premises and eight changed raw observations are rejected. Controls include static label zero, lost opacity, altered animation order, a fabricated private copy, successful post-close access, cleared metadata, numeric values in Boolean cells, and omitted cleanup. A stale-receipt control also refuses. The initial research-only Bend match/map syntax failures were corrected without changing native observations; the final implementation uses explicit structural recursion for runtime mask mapping.

Ordinary CI runs retained data and the formal tools:

```sh
python3 host/minecraft/sprite_inputs_conformance.py
```

The [portable receipt](evidence/sprite-inputs-conformance.json) must equal the current computed result. Native `sprite_inputs_probe.py` collection is owner-run outside CI and requires existing private pinned input receipts. `sprite_inputs_observations.py --private .build/minecraft` audits without Java; `--export` and the comparison's `--refresh-receipt` are deliberate refresh operations.

## Design and remaining qualification

Treat supplied-image custody as part of the constructor contract. A caller retaining an alias needs an explicit agreement about mutation and close authority. Preserve the current consuming-image behavior when intended; alternatively, a wrapper may copy or introduce a scoped ownership agreement. Those choices add allocation or lifetime obligations and are proposals, not implementations. A live Java descriptor, readable metadata, and completed CPU close must remain distinct from usable backing, operation retirement, and final GPU reclamation.

Asset and editor diagnostics should distinguish metadata decoding, frame selection, CPU pixel access, geometry generation, baking, and rendering. Preserve actual frame labels and affected identities instead of inventing a default frame. If an operation fails after some inputs have been retained or closed, report those effects and the safe next step from actual state. Do not retry a closed image or stale sprite as though it were merely missing metadata.

Real identifiers, animation codecs/explicit frame lists, partial alpha/color semantics, interpolation, mipmaps, invalid-frame handling, concurrent mutation/close, generated geometry, material caches, provider coexistence, device lifetime, and other runtime/host profiles remain pending. This advances shared input evidence for `textures.images` and `models.generated`, using the same 26 cases once. It selects no production change, backport, provider installation, pack pin, or rollout.
