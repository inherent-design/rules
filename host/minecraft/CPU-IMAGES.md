# CPU image custody, pixel words, and close

This band observes one original Java Edition 1.21.1 `NativeImage` on macOS 26.7.1/aarch64, using Temurin 21.0.13.1 and the metadata-pinned LWJGL 3.3.3 core native library. The fixture constructs one zero-initialized 2×2 RGBA image, requests **16 bytes of pixel storage**, and records 16 ordered steps. That request does not measure allocator overhead, JVM RSS, physical memory, or GPU storage.

The [capture manifest](native-image-capture.json) binds the authored requests, observations, streams, and normalized receipt. [Owner audit](native_image_observations.py) rechecks the original signed client, two original class entries, mappings, exact Java libraries, native archive/library, JDK tools, frozen producer, compiled helper, and VM trace. Public observations omit only two absolute location fields; event fields and streams are unchanged. Full commands, original inputs, binaries, and VM logs remain private. No original game code or library binary is redistributed by this band.

## Measured lifecycle

| Operation | Observed result |
| --- | --- |
| Successful zero-initialized construction | Four zero pixel words, width 2, height 2, format RGBA. |
| Four in-bounds writes | Exact opaque 32-bit words round-trip; other cells retain their values. This does not establish channel conversion, color space, or rendered appearance. |
| Out-of-bounds read or write while live | `IllegalArgumentException`; subsequent in-bounds observation preserves all four words. |
| Close | Normal return. Subsequent width, height, and format getters still return the same metadata. |
| In-bounds read or write after close | `IllegalStateException` with “Image is not allocated.” No freed address is read by the fixture. |
| Out-of-bounds read or write after close | Bounds error takes precedence over the allocation guard. A bounds error alone therefore does not reveal whether backing is live. |
| Repeated close, then final cleanup close | Both return normally. No free-call count or physical reclamation is measured. |

There are 16 trace steps, not 16 total Java method invocations: each step also samples the three metadata getters, and each pre-close step samples four pixels. The helper suppresses snapshot pixel reads after a returned close. This is an explicit observation gate, not a direct pointer measurement. Separate guarded pixel calls after close establish the two measured error categories. Mathematical pixel history retained by a model never grants access to a native address.

The inspected original constructor uses the RGBA format, positive dimensions, `MemoryUtil.nmemCalloc`, and the non-STB free family. Original close calls `MemoryUtil.nmemFree` when that backing is present, then clears its pointer field; metadata fields remain. These source facts explain the selected observations, but they are not an instrumented allocator proof. Allocation failure, an exception during native free, concurrent access/close, escaped aliases, and other formats are outside this fixture.

## Effective native profile

The child selects `org.lwjgl.system.allocator=system` and an owned `org.lwjgl.librarypath`. Exact public method-handle descriptors avoid enumerating unrelated font, decoder, and GPU signatures. Only the original image and format classes load from the client. The VM trace records initialization of `MemoryManage$StdlibAllocator` and loading of the exact owned `liblwjgl.dylib`. Its logged native loads also include four JDK libraries. Those logs do not enumerate all transitive operating-system loader dependencies.

The native archive is the official metadata-pinned 48,620-byte macOS ARM64 classifier; its selected 303,600-byte Mach-O member is checked before use. Existing Java-only libraries are read from their cache and verified against official metadata. Nothing is installed into a launcher or global native path. No STB, FreeType, GLFW, or Tracy initializer appears in the selected VM trace. No decoder, game, GPU upload, window, or renderer is invoked. The missing SLF4J provider produces a captured no-op-logger warning; this does not qualify the game's effective logging configuration.

The compiler and execution groups exited, and the retained exact-capture process readback is empty. The child uses two active processors, a 96 MiB heap ceiling, private home/temp properties, controlled JVM startup variables, and a 30-second command timeout. These are fixture bounds, not host-wide concurrency or physical-memory measurements. Native inputs and consequential evidence remain required study material.

The [Java host integration](../java/README.md#managed-scopes-and-library-owned-native-addresses) keeps this library-owned allocation separate from Java 25 arenas. Java 17 remains the host baseline; this observation does not run the client on Java 17 or qualify Java 25, Windows, GNU/Linux, another allocator, another architecture, or modern clients' Tracy-dependent path. Their dependencies and lifetime contracts remain independent obligations.

## Rules and falsification

[CpuImage.lean](../java/CpuImage.lean), [CpuImage.bend](../java/CpuImage.bend), and the [typed research codec](NativeImageCase.lean) model one successfully allocated 2×2 image, opaque words, coordinate admission, ordered guards, metadata, and close. Fourteen Lean laws include parameterized close/history/metadata properties and selected cell examples. Nine Bend laws check closed terms. Neither model proves a JVM/JNI translation or native allocator correctness.

The codec admits exactly one initial construction and selected serial operations. Coordinates −1, 0, 1, and 2 are encoded as 0, 1, 2, and 3; this is a finite adapter, not arbitrary Java integer indexing. Needed unknown coordinates and words refuse. Unused fields may remain unknown. The profile identifies the observed client/JDK/host/library/allocator combination; it is not a generic support badge.

Both models match all 16 outcomes, returned words, four-cell snapshots where observed, and dimensions. Twelve unsupported DTOs refuse. Four changed premises and six changed raw observations are rejected, including fabricated post-close pixels, lost writes, cleared metadata, and conflated guard reasons. The [portable receipt](evidence/native-image-conformance.json) must equal the current computed receipt; a stale-receipt control also refuses. The public comparison needs only retained authored data and the formal toolchain.

After the formal gate:

```sh
python3 host/minecraft/native_image_conformance.py
```

Ordinary CI runs only that retained comparison. Native `native_image_probe.py` collection is owner-run, requires the selected private input receipts, never downloads inputs, and is outside ordinary CI. `native_image_observations.py --private .build/minecraft` audits retained evidence without running Java. `--export` and `native_image_conformance.py --refresh-receipt` are deliberate evidence/receipt refreshes.

## Design choices and remaining work

Preserve metadata inspection after close where it is useful, but make backing availability an independent state. Keep exact refusal reasons instead of deriving lifetime from one error. An ownership wrapper could reject all pixel operations after closure before calling the library; that deliberately changes the current bounds-before-allocation error order and needs its own compatibility tests. It is a proposal, not a patch.

Diagnostics should distinguish CPU backing close, decoder failure, upload admission, texture publication, and device retirement. Retain the affected image/operation identity and partial results. A “closed” CPU object or readable dimensions must not become a renderer-completion or physical-memory claim. Typed machine reasons should come from the same facts as human diagnostics, rather than parsing the captured English messages.

Full decoding, channel/color conversion, STB-backed images, borrowed buffers, callback/copy failure cleanup, generated sprite geometry, mipmaps, upload failure, provider coexistence, and final device reclamation remain open. This advances one component of `textures.images`; it does not complete that family or the broader host and resource intents. No production implementation, backport, installation, pack change, or rollout is selected.
