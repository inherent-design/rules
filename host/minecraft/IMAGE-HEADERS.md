# Original image-header admission and buffer effects

This band compares **165 original `PngInfo.validateHeader` calls**, 33 authored inputs on each of the five pinned Java clients. A separate 12-call arithmetic calibration uses actual Java 17, 21, and 25. Every input backing array is 33 bytes. No PNG is decoded, and no decoded image, STB allocation, GPU resource, game, or renderer is created.

The [capture manifest](image-header-captures.json) binds unchanged authored requests, raw observations, streams, and normalized receipts. Original clients, mappings, class-load traces, compiler outputs, tools, and frozen producers remain private. The [owner audit](image_header_observations.py) rechecks those inputs against their recorded digests and the preceding disassembly review. Only the selected original header class loads from each client; signatures remain intact. The Java 17 calibration loads no client class. All twelve compiler/JVM groups exited and were observed absent.

## Versioned predicates

| Client | Selected header method |
| --- | --- |
| 1.21.1, 1.21.4, 1.21.5 | Absolute reads check signature, IHDR length, and IHDR type. Short limits can throw `IndexOutOfBoundsException`. A matching 16-byte prefix returns normally. |
| 1.21.11 | Adds an explicit 16-byte limit guard that throws `IOException`; the selected successful predicate still stops after the three prefix checks. |
| 26.3 | Requires a limit of at least 33, checks individual bit-depth and color-type sets, and applies a selected 16-bit bounds estimate. |

The 26.3 source independently admits depth 1 and color type 6; it does not validate that pairing in this helper. The fixture also observes normal return with zero width, negative height at depth 8, altered CRC, and nonzero compression, filter, and interlace fields. These are **header-helper observations**, not assertions that those inputs are valid PNGs or that a later decoder accepts them. A 33-byte IHDR prefix is not a complete image.

Every observed call preserves position, limit, remaining count, capacity, read-only status, and backing bytes. The helper sets order to big endian and restores the prior order only after a normal return. A rejected little-endian buffer therefore remains big endian, including a read-only view. A valid prefix with position 32 and limit 33 still returns: these are absolute reads from index zero, not a parser of the remaining one-byte region. A read-only byte view does not establish immutable metadata or a pure predicate.

## Wrapped size is not an allocation bound

The inspected 26.3 method computes the selected depth-16 estimate as Java `4L * width * height * 2L`, then asks whether narrowing to `int` and widening back preserves that **already wrapped** `long`.

| Width × height, depth 16 | Mathematical estimate | Observed wrapped `long` | Narrowing round trip | Header result |
| --- | --- | --- | --- | --- |
| 2 × 3 | 48 | 48 | yes | return |
| 16384 × 16384 | 2147483648 | 2147483648 | no | `IOException` |
| 1073741825 × 2147483646 | 18446744073709551600 | -16 | yes | return |
| 1073763824 × 2147439649 | 18446744074555662208 | 846110592 | yes | return |

Actual Java 17.0.21.1, 21.0.13.1, and 25.0.4.1 calibrations agree on these four arithmetic outcomes. Their `Math.multiplyExact` chains throw on both long-overflow examples. The positive wrapped example means a nonnegative check alone would not establish the intended size bound. This estimate is a source expression, **not measured physical memory**. Downstream image-library checks, allocation behavior, reachability from a full decode, and security consequences have not been exercised.

The [Java host contract](../java/WORD64-AND-BUFFERS.md) separates signed widening, wrapped multiplication, narrowing, checked arithmetic, and buffer metadata. Native qualification is macOS 26.7.1/aarch64 only. The older four clients run on the pinned Java 21 build; 26.3 runs on Java 25. The Java 17 arithmetic calibration does not qualify newer client class files on Java 17. Windows, GNU/Linux, other JDK builds, direct/mapped buffers, concurrent access, and native allocators remain separate obligations.

## Rules, evidence, and proposals

[ImageHeader.lean](ImageHeader.lean), [ImageHeader.bend](ImageHeader.bend), and the shared [Word64 rules](../java/Word64.lean) provide 26 Lean and 20 Bend laws across these modules. The [typed research codec](ImageHeaderCase.lean) and [retained comparison](image_header_conformance.py) match 165 header outcomes and 12 arithmetic outcomes. Needed unknowns, unselected client/JDK profiles, invalid bounds, and duplicate IDs refuse. Short-circuited facts may remain unknown. Four changed-premise interpretations and seven changed raw observations are rejected. Eight additional word-boundary cases compare only the two models and carry no native qualification. The portable [receipt](evidence/image-header-conformance.json) must equal the current computed receipt; refreshing requires an explicit command.

Lean uses independent fixed-width arithmetic. Bend uses bounded 32-bit limbs and a two-word representation, avoiding large unary naturals. The initial unary draft was stopped by the owner after inspecting Bend's actual `Nat` implementation; it supports no conformance claim. The final word algorithm is checked by its laws and these bounded comparisons, not a universal compiler/JVM translation theorem. A preparation-only wrong class locator failed before any compiler/JVM invocation; its frozen producer and disposition remain private. No original observation was rewritten.

Independently selectable proposals remain unimplemented:

- Restore caller buffer order on every exit, or perform validation on an explicitly owned view; retain the selected absolute-index contract and test view/order behavior rather than assuming it.
- Compute positive dimensions and a checked mathematical byte bound before narrowing or allocating, then apply a separate explicit resource budget. Preserve PNG format validation and downstream decoder checks as distinct stages.
- Report header admission, decoder failure, CPU image custody, upload publication, and device retirement separately. Header success must not become a compatibility or safe-allocation badge.

No proposal changes the pinned clients or selects a backport. Full PNG/STB/NativeImage decoding, mipmaps, channel representation, provider coexistence, texture upload failure, and final GPU reclamation remain open. This advances one bounded component of `textures.images`, not its whole family.

## Reproduction boundaries

Ordinary CI runs `python3 host/minecraft/image_header_conformance.py` after the formal gate. It consumes retained authored data and invokes Lean/Bend only. The owner-only `image_header_probe.py` requires the existing private pinned input plan and libraries and never downloads them. `image_header_observations.py --private .build/minecraft` audits retained inputs without rerunning Java. `--export` deliberately refreshes public authored evidence; `image_header_conformance.py --refresh-receipt` deliberately refreshes the reviewed model receipt. Neither refresh is part of ordinary CI.
