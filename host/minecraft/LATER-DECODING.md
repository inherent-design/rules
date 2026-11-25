# Original 26.3 decoding

Forty distinct inputs were passed to selected methods and codecs from the unmodified Java 26.3 client. Both [Lean](LaterDecode.lean) and [Bend](LaterDecode.bend) match their bounded decoded-state and refusal projections. This is a method-level comparison on macOS arm64 with explicit Java 25, without a game, renderer, loader or provider launch.

The [canonical capture](evidence/later-codecs-26.3-20261125T064027971144Z/receipt.json) identifies the original client and class entries, 25 library artifacts, authored observer and collector, JDK tools, requests and raw channels. [Conformance](evidence/later-codec-conformance.json) binds those bytes to the model sources and replay adapter. The JVM returned zero with no observer errors; both recorded process groups were absent after completion. A 128 MiB heap and two active processors were process settings, not measurements of physical memory.

| Surface | Inputs | Observed boundary |
| --- | ---: | --- |
| Cuboid rotation | 13 | Missing origin and incomplete/invalid scalar forms refuse. Scalar members select the scalar branch even when XYZ members exist. An ordinary angle of 123 is accepted. Euler components default individually, and `rescale` survives decoding. |
| Shade override | 5 | Absence and legacy `shade: false` yield no override in this selected method. Lowercase `up` resolves; uppercase `UP` and an unknown name refuse. |
| Format endpoints | 10 | Omitted lower minor defaults to zero; omitted upper minor defaults to 2147483647. Empty, negative and 257-element examples refuse. A third component is accepted but not stored. Positive fractional components are coerced to integers in the observed codec. |
| Pack-format admission | 12 | Resource/data legacy thresholds are 64/81. New bounds must be paired and ordered. A modern-only range refuses deprecated `supported_formats`; the selected consistent mixed legacy range succeeds. |

## Interpretation and design consequences

The observations support a versioned dialect, rather than a shared “Euler supported” flag. A faithful adapter must preserve branch selection, scalar requirements, rescale and direction spelling. The selected Polytone source hook takes its XYZ path before scalar parsing and constructs it with rescale false. That makes mixed representation and rescale useful comparison witnesses; it does not establish an executed transformed-hook difference. Compat's whole-model admission has separate premises and refusals.

Format admission also needs separate endpoint and pack-type contracts. Treating both omitted minors as zero changes the accepted upper bound. Requiring integral JSON numbers would reject the observed fractional example; silently dropping extra components during an asset conversion would hide a lossy normalization. A future tool may deliberately adopt stricter authoring validation, but it must label that policy separately from native admission and preserve the original input and diagnostic.

The existing [artifact-version model](TARGETS.md) describes a client's declared format and Java requirement. This band describes selected input codecs. Neither proves that the admitted pack supplies valid assets, that references resolve, that an older runtime has the required gameplay data, or that output looks correct.

## Comparison boundary

The Python adapter derives model inputs from requests independently of outcomes. The Lean DTO rejects unsupported schema, action, numeric and threshold profiles. Bend receives the same projected requests. Nine decoder refusals, six adapter refusals and nine deliberately changed result projections exercise the comparison boundary. Refusal text remains in the original capture but is not predicted by these models.

The numeric profile contains nonnegative bounded integer magnitudes and positive decimals with one fractional digit. Negative fractions, overflow, arbitrary numeric/string syntax and the complete JSON codec grammar remain open. Rotation angles are bounded nonnegative integers; the selected origin is `[8,8,8]`, whose observed normalized value is `[0.5,0.5,0.5]`. These are explicit study restrictions, not limits attributed to Minecraft.

All 16 original JOML matrix components remain in the observation. The models predict rotation kind, axis, angles and rescale, not general floating-point geometry, cull orientation, lighting, shader effects or rendered equivalence. No complete cuboid model is decoded by the reflection calls. Pack metadata tests call the selected format codec; they do not qualify repository discovery, overlay-list validation or compatibility UI.

## Harness history and reproducibility

[Collector dispositions](evidence/later-collector-dispositions.json) retain all four executions. The first classpath omitted required utility dependencies; the next omitted Netty classes used during `Direction` initialization. Their 31 and five observer errors are harness failures, never product refusals. A five-input completion succeeded after adding the explicitly declared Java-only Netty artifacts. A fresh full JVM then supplied one consistent canonical basis because the earlier JVM had retained failed class initialization. The pure replay independently checks every earlier non-error row against that final basis.

Those executions contain 125 calls, with only 40 unique canonical inputs used for model comparison. Failed and partial outputs, their exact producers and the completion remain unchanged. Original client/library payloads and native class files stay private. The exported files contain authored research code, requests, observations and normalized attribution receipts.

Owner-run acquisition and collection use [acquire_later_libraries.py](acquire_later_libraries.py) and [native_later_codecs.py](native_later_codecs.py), with explicit artifact metadata and JDK selection. Ordinary CI runs only `python3 host/minecraft/later_codec_conformance.py` after the formal checker; it reads retained evidence and executes the models. It does not download libraries or start a JVM.

Actual provider composition, decoding on other host platforms, the independent 1.21.11 dialect, reload publication/retirement and rendering remain pending. No implementation or pack migration is selected.
