# Build-script freshness, effects, and generated inputs

This band extends the [initial Cargo study](README.md), using the same pinned Cargo 1.92.0 (`344c4567c634a25837e3c3476aac08af84cf9203`) and Rust 1.92.0 on macOS arm64. It examines one local package with no registry dependencies. It changes no Cargo or empack implementation. The [source ledger](../sources/cargo-freshness-selections.json), [native receipt](../evidence/cargo-freshness-20261125T074348425999Z/receipt.json), and [comparison](../evidence/cargo-freshness-conformance.json) identify the exact profile and evidence.

## Separate units and values

Cargo compiles a build script and runs it as different units. Its parsed stdout is retained metadata; files the script generates in `OUT_DIR` are another value. The Rust compilation unit consumes the generated file and an automatically tracked `option_env!` value. The last physical executable can remain present even when its build fingerprint is invalid.

The script declares a file, `RULES_TRACKED`, and `RULES_FAIL`. It deliberately omits the environment variable `RULES_HIDDEN`. It also writes a separate invocation journal outside `OUT_DIR`, solely to observe actual executions. Both choices violate ordinary completeness/output guidance and are controlled fixture choices, not Cargo defects. All paths are private; no user project or registry cache is used.

The [build-script message contract](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/doc/src/reference/external-tools.md#build-script-output) explicitly permits replaying cached output. The selected [compiler source](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/cargo/core/compiler/custom_build.rs) emits that metadata on both dirty and fresh branches. A `build-script-executed` JSON message therefore does not prove a new process ran.

## Native results

The one-shot collection ran 15 build attempts, the existing executable after each attempt, and one final clean: 31 commands. Every owned process group retired. The single target used one job, no debug info, and no incremental compilation. Cargo removed its own intermediates at the end. The remaining source, journal, and one small final binary occupy about 480 KiB. No unrelated build, VM, daemon, or cache was touched.

| Request/change | Physical script | Result |
| --- | --- | --- |
| Cold build | Runs | Script and app compile successfully. |
| Same inputs | Reused | Script metadata is still emitted; the app artifact is fresh. |
| Change only undeclared `RULES_HIDDEN` | Reused | App retains the old captured value. This is the intentional incomplete watch set. |
| Watched value absent → empty → value → absent | Runs each time | Missing and empty remain distinct observations. |
| Change only the `option_env!` value | Reused | Rust compiles the app with the new macro value. |
| Change the watched file | Runs | Generated data and app update. |
| Script writes generated data, then panics | Runs and fails | Exit 101; partial generated data remains; old executable remains runnable. |
| Retry the same failed script | Runs and fails again | Another physical invocation can write identical bytes. |
| Return to the previous successful input basis | Runs | Trust was invalidated; matching an old basis does not make the failed attempt fresh. The successful compilation produces the same binary bytes as before failure. |
| Delete only the generated include | Reused | Cached script metadata is emitted; Rust compilation fails. The old executable remains runnable. |
| Retry with the generated include still absent | Reused | Compilation fails again; no automatic generator rerun in this profile. |
| Change the watched file again | Runs | Generated input is restored and compilation succeeds. |
| Clean | No script | Target is removed; the explicit external journal and separately retained binary remain. |

The [fingerprint preparation source](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/cargo/core/compiler/fingerprint/mod.rs) clears an existing dirty fingerprint before work begins and writes it after success. Native snapshots show zero-length script-run and dependent-app fingerprints after the controlled script failure; missing generated input invalidates the app fingerprint while the script fingerprint remains valid. The model keeps a historical successful basis separate from current reuse eligibility.

The selected [watch guidance](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/doc/src/reference/build-scripts.md#change-detection) describes mtime-based file detection and declared environment tracking. Both file edits here changed bytes and increased native mtime. The model's file labels identify those controlled revisions; they do not implement content-based freshness or establish same-timestamp/rewound-clock behavior.

## Models and verification

[Lean](Freshness.lean) has 13 laws; [Bend](Freshness.bend) has 10. Both compare the 15 build attempts and clean. Fifteen separately executed runtime checks identify the physical binaries and their compiled values. Six DTO refusals, five changed input premises, and four changed native-observation controls protect the adapter.

The projection uses the actual journal, original Cargo JSON, generated-file hashes, fingerprint presence/length, and independently run binaries keyed by their byte hashes. Signature/data labels preserve the observed environment/file relations; they are not Cargo hashes. The retained basis is inferred from successful fixture executions, not decoded from Cargo's fingerprint JSON. A valid marker alone is not independent content verification.

One proposed negative control replaced a repeated failure's generated value with its preimage. Those bytes were already equal, so it was a no-op. The adapter rejected that as nondiscriminating and instead changes a genuinely different generated observation. The [disposition](../evidence/cargo-freshness-20261125T074348425999Z/projection-control-review.json) preserves that correction. No native outcome changed or native collection was repeated.

## Design and UX consequences

Keep compilation, script execution, metadata availability, generated backing, reuse eligibility, and the last runnable product separate. Cargo's existing watch contract remains appropriate: a tool cannot infer every script read from these declarations. Preserve its invalidation-before-work rule when simplifying a build engine; an old successful observation must not authorize reuse after incomplete work.

Consumers should label cached build-script metadata as available output, not new physical execution. If an upstream API later adds an explicit reuse indicator, it should be additive and version-qualified. Until then, a client must not manufacture a process-start event from `build-script-executed` or from a fresh custom-build compiler artifact.

A failed build can report both failure and a retained previous executable. It should not imply the current source produced that executable, nor hide partial generated effects. Conversely, identical executable bytes do not prove that compilation was skipped. The selected recovery case rebuilt successfully with identical bytes.

For empack's proposed operation interfaces, preserve input basis, invalidated work, retained results, and publication as distinct facts. Generated or cached content also has a role: it may be a required input to downstream work even when its producer is considered fresh. These observations support the existing [retention and observation distinctions](../COMPARISON.md); they do not select a new automatic repair or garbage-collection policy.

## Remaining qualification

Parent feature operations retain their prior statuses. This component does not qualify arbitrary dependency graphs, build-script/proc-macro trust, profiles or targets, concurrent builds, interruption/power loss, adversarial timestamp changes, checksum freshness, all generated-output repairs, registry/cache behavior, or Windows/Linux parity. Tool hashes and versions identify this execution; they do not prove complete compiler/sysroot reproducibility. A cold build after cleanup, partial-package cleanup, and general compiler dependency discovery remain separate controls.

Replay without running Cargo, rustc, or the fixture binary:

```sh
LEAN=/path/to/lean BEND=/path/to/bend python3 applications/cargo/freshness_conformance.py applications/evidence/cargo-freshness-20261125T074348425999Z
```

Do not rerun the completed one-shot collector. Its cleaned target and retained source/journal are intentional; new native cases need separate provenance.
