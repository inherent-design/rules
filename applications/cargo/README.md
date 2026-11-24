# Cargo: resolution, selected units, and build evidence

This band compares Cargo 1.92.0 with its pinned source revision, `344c4567c634a25837e3c3476aac08af84cf9203`, on macOS arm64. It covers three local packages, normal dependency features under resolver 2, one build script, and cleanup. It does not qualify Cargo's full feature resolver, cache, or publication system. A separate [package-selection and verification band](PACKAGING.md) examines local source archives and selected build checks; registry publication remains unqualified.

## Domain distinctions

| Value or relation | Meaning in this band |
| --- | --- |
| Package identity and lock selection | Which package/version/source is resolved. The metadata ID is opaque. |
| Workspace selection | Which members participate in this build request. |
| Activated features | Features contributed by the selected dependency edges. |
| Build unit | A package target compiled with particular features, profile, mode, host/target kind, flags, and dependency context. |
| Artifact evidence | A unit plus the compiler/host and observed input basis. A lockfile alone cannot identify it. |
| Build-script watch set | Inputs Cargo has been told to observe, rather than all inputs the script actually reads. |
| Owned cleanup scope | The selected target directory. Arbitrary script effects elsewhere have separate ownership. |

The [unit source](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/cargo/core/compiler/unit.rs) stores features and build context separately from package identity. Its [fingerprint explanation](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/cargo/core/compiler/fingerprint/mod.rs) distinguishes unit separation from rebuild detection and describes the limits of timestamp and environment tracking. The model mirrors selected fields, not the exact Cargo cache key.

## Native observations

The retained [run](../evidence/cargo-20261124T005523371598Z/receipt.json) contains the exact probe source, tool hashes, environment, commands, stdout, stderr, and before/after observations. It used no registry or network dependency and no existing project. A private working directory outside the user's home excluded ancestor Cargo configuration; private `CARGO_HOME` alone would not do that. Build artifacts were removed by the fixture's own `cargo clean`.

The workspace has an app requesting `red`, a tool requesting `blue`, and their shared library. The library reports its compiled feature flags and a build-script-captured input.

| Request or change | Directly observed result |
| --- | --- |
| Cold `metadata --format-version=1 --offline` | Created a lockfile and reported both library features across the workspace. |
| Build app only | App reported `red=true`, `blue=false`. |
| Build workspace, run its app binary directly | App reported both features enabled. |
| Build app only again | App returned to `red=true`, `blue=false`. The lockfile stayed identical. |
| Change a deliberately undeclared external script input | Compiler artifacts were reported fresh; the app retained the old captured value. |
| Add the missing `rerun-if-changed` declaration | The app captured the current input; the next input edit also rebuilt correctly. |
| Clean | Removed the private target directory and preserved the script's deliberately misplaced output outside it. |

These results agree with the pinned [feature documentation](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/doc/src/reference/features.md) and [build-script guidance](https://github.com/rust-lang/cargo/blob/344c4567c634a25837e3c3476aac08af84cf9203/src/doc/src/reference/build-scripts.md). The fixture deliberately violated input completeness and the recommendation to write outputs inside `OUT_DIR`. Neither observation is presented as a Cargo defect. The metadata result also describes a different scope from the app-only build; it is not incorrect because the scopes differ.

## Models and checks

[Lean](Build.lean) defines selected features, build-unit identity, artifact evidence, cached script capture, and cleanup. Seven laws establish feature-sensitive unit identity, the selected-feature distinction, conditional cache validity, and cleanup's bounded effects. [Bend](Build.bend) has the executable feature/cache/cleanup projection and three checked laws. The [adapter](conformance.py) runs six projected native cases through both models and checks the recorded stream hashes.

Two negative interpretations are rejected by direct runtime output: treating workspace metadata as the app-only feature set, and treating a fresh artifact as proof that every actual input is unchanged. The cache law requires a complete signature as a premise; the undeclared-input case shows why that premise cannot be inferred from a successful build. Signature construction in the adapter projects the fixture's watched file contents. It does not implement or verify Cargo's timestamp/fingerprint machinery.

To replay retained evidence, compile `Build.lean` to `.build/applications/cargo/Build.olean` with the pinned Lean, then run:

```sh
LEAN=<pinned-lean> BEND=<pinned-bend> python3 applications/cargo/conformance.py applications/evidence/cargo-20261124T005523371598Z
```

This replay does not run Cargo. `python3 applications/cargo_probe.py` collects a new isolated native run and is an owner-run procedure outside ordinary CI. Its current acquisition profile is this Mac's pinned toolchain.

## Design and UX candidates

Preserve Cargo's separate package graph and build-unit concepts. A consumer of `cargo metadata` should label the graph's scope and capture its actual build request before describing activated features. An IDE or empack generator must not use an unchanged lockfile as sufficient evidence that an artifact still matches the requested configuration.

For Cargo itself, an optional machine-readable cleanup receipt could identify the target directory, selected scope, completion or uncertainty, and the limits of that scope. The current keep-output alternative is reasonable: Cargo cannot enumerate arbitrary side effects without a different execution boundary. This is an interface proposal, not a request to add a sandbox or undo build scripts. Review existing JSON cleanup interfaces and downstream expectations before proposing a concrete flag or schema.

Similarly, consumers should describe `fresh` as Cargo's reuse decision. They should avoid turning it into a stronger statement that generated content was independently verified against every source. Better input-declaration guidance is preferable to pretending the build tool can infer all script reads.

The shared host mapping needs distinct revision/content evidence, captured request scope, executable authority, and effects ownership. The existing host contracts can express those obligations; this band has not exposed a missing primitive. Build-script completeness is an application/domain obligation, rather than a generic host Boolean to assume.

## Remaining qualification

General workspace defaults/discovery, feature defaults, resolver 1/2/3 differences, target-conditioned dependencies, host/build dependency splits, profile changes, cross-compilation, failed scripts, concurrent builds, package/registry identity, lock/update policies, test/doc execution, plugins, and package publication remain pending. Future native checks must compare actual per-unit features and outputs, include failed or partial operations, and keep private Cargo configuration and credentials excluded. Any new receipt should be opt-in and additive; existing metadata fields and opaque package IDs retain their documented meaning. No production Cargo or empack code has changed.

The later [workspace-context band](WORKSPACES.md) observes selected root/virtual defaults, member context, explicit manifest paths, and CLI exclusion versus checked dependencies. It does not qualify general discovery or the full compiler-unit graph.
