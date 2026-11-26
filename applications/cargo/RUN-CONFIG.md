# Configuration, compilation, and `cargo run`

A successful Cargo build does not establish that its runner or application succeeded. Conversely, a retained executable does not authorize `cargo run` to launch it after the current build fails. This band observes those boundaries with Cargo/Rust 1.92.0 on macOS arm64, plus a specific mismatch between documented CLI configuration priority and the pinned runner implementation.

The earlier [freshness study](FRESHNESS.md) ran retained binaries separately after build failures. The [testing study](TESTING.md) exercises selected test/harness paths. This fixture adds actual `cargo run`, configuration discovery, runner overrides, independent runner/application journals, and command outcomes. No Cargo, Rust, empack, or host contract was changed.

## Profile and native procedure

The primary fixture creates one dependency-free Rust binary and one owned Python runner in a fresh private directory. Cargo, rustc, and Python identities are retained; Cargo/rustc hashes match the existing tool selection. It uses private child HOME, CARGO_HOME, target and temporary directories, one build job, no debug info or incremental compilation, and offline mode. No user Cargo configuration, registry, project, cache, or toolchain is modified.

The `.cargo/config.toml` sets a scalar `target.aarch64-apple-darwin.runner` string. Selected environment and CLI values name distinguishable runner labels. Controlled configuration paths contain no spaces; the application arguments deliberately contain a space, Japanese text, a Greek character, and a literal flag. This does not qualify arbitrary shell quoting, runner arrays, cross-target configuration, signals, or Windows behavior.

The runner logs its label, binary spelling, arguments, and working directory before either refusing with status 9 or replacing itself with the application. The application writes a separate journal before exiting with status 0 or 7. Cargo's original JSON, raw streams, binary hashes, source edits, and both journals remain independent observations.

| Request | Build/artifact report | Independent execution and final outcome |
| --- | --- | --- |
| Invoke in the project | Build succeeds; artifact reported non-fresh. | Project runner and application run; exit 0. |
| Add environment runner | Build succeeds; artifact reported fresh. | Environment runner executes; exit 0. |
| Add CLI runner while environment runner remains | Build succeeds; artifact reported fresh. | Environment runner still executes; exit 0. This contradicts the general documented priority. |
| Invoke in the parent with `--manifest-path` | Build succeeds; artifact reported fresh. | Child project configuration is not discovered. Application runs directly with the parent working directory. |
| Add the explicit configuration file from the parent | Build succeeds; artifact reported fresh. | Project runner executes; application still has the parent working directory. |
| Runner refuses | Build succeeds; artifact reported fresh. | Runner journal grows; application journal does not. Exit 9. |
| Break the Rust source | Build fails; compiler error and unsuccessful build event appear. | Neither runner nor application starts. Exit 101; the old binary's bytes remain unchanged. |
| Restore the source | Build succeeds; artifact reported non-fresh. | Runner/application run; exit 0. Binary bytes match the previous successful image. |
| Application returns 7 | Build succeeds; artifact reported fresh. | Both journals grow; application records status 7. Final exit 7. |

Artifact `fresh` values are Cargo's reports. This band does not independently count physical rustc processes or implement the fingerprint algorithm. The binary comparisons establish these exact bytes at the observed boundaries, not reproducible builds across roots or toolchains.

The [primary capture](../evidence/cargo-run-config-20261126T001855041022Z/receipt.json) has nine run requests and one incidental clean. A [separate fresh control capture](../evidence/cargo-run-config-20261126T002203646988Z/receipt.json) adds three run requests and its own clean:

- The CLI runner alone executes its CLI label, proving the argument is accepted.
- `CARGO_BUILD_JOBS=0` refuses before a build-finished event or any runner/application event, with exit 101 and a jobs diagnostic.
- Adding `--config build.jobs=1` over that invalid environment value succeeds and uses the project runner. Ordinary scalar priority works in this control.

These controls do not repeat a primary case or mutate its completed fixture. All 14 process groups are absent. Each clean removes only its newly generated target directory after preserving the selected small binary. Source, configuration, journals, and retained binaries remain; each private fixture occupies about 552 KiB.

## Selection and source boundaries

[Seven selected source identities](../sources/cargo-run-config-selections.json) pin revision `344c4567c634a25837e3c3476aac08af84cf9203`. Matching entrypoint identities and selected source behavior do not establish a reproducible source-to-binary build, and latest upstream status has not been checked.

`cargo_run::run` calls compilation with error propagation before creating the target process. The selected runner wraps the binary and forwarded arguments. The run operation explicitly sets the process working directory to the invocation directory. Configuration discovery likewise begins at that directory and searches its ancestors and CARGO_HOME. Selecting a manifest is a different operation from changing the configuration or runtime directory.

The documented scalar priority is CLI, environment, then discovered files. Runner retrieval uses `PathAndArgs`, which deserializes through `Value<StringList>`. The inspected `StringList` path loads the config value and then calls `get_env_list`; the nonmergeable-runner branch clears existing items before adding the environment value. This explains the pinned native CLI-plus-environment result and differs from the ordinary scalar control.

`ValueDeserializer` separately chooses the higher-priority definition. Consequently, the selected source can pair a CLI definition with environment-supplied runner elements. That provenance consequence is source-qualified; this fixture uses absolute program paths and does not reproduce relative-path effects. Other nonmergeable consumers, including credential-provider and browser settings, need separate caller review. No credential or browser operation is exercised here.

## Model fidelity and replay

[RunConfig.lean](RunConfig.lean), [RunConfig.bend](RunConfig.bend), and the [decoder](RunConfigCase.lean) project configuration admission, current runner choice, launch gating, child outcome, and application working directory. Twelve Lean laws and ten Bend laws preserve configuration refusal, failed-build gating, the absence of fallback authority from a retained binary, runner/application failures after a successful build, invocation-directory semantics, and current versus proposed priority.

The compiler result is an admitted phase witness: absent when the configuration refuses, false after the controlled compiler failure, and true after successful compilation. Replay obtains it from Cargo's build-finished records and validates the known fixture source. It compares consequences against independent runner/application journals, actual process status, and application working directory. It does not call this a Rust compiler model or count the copied build result as new conformance evidence.

Both models match 60 launch/status/working-directory values across 12 run requests. Twelve derived stage labels are checked separately. Twelve proposed selector values are model-only; they do not come from patched Cargo. Six changed-output controls and four decoder refusals protect the comparison. Configuration-not-attempted and build-failed remain distinct; unsupported witness combinations and generated child statuses are refused.

The [comparison](../evidence/cargo-run-config-20261126T002203646988Z/conformance.json), [phase details](../evidence/cargo-run-config-20261126T002203646988Z/phase-details.json), [basis](../evidence/cargo-run-config-20261126T002203646988Z/basis.json), and [controls](../evidence/cargo-run-config-20261126T002203646988Z/controls.json) retain the exact scope. Replay executes only Lean/Bend and retained-data readers:

```sh
LEAN=/path/to/pinned/lean BEND=/path/to/pinned/bend \
  python3 applications/cargo/run_config_conformance.py
```

`--public-only` excludes installed tool identities, latest private source/journal/binary readbacks, and cached original source bodies. It preserves the retained request, artifact, phase, source-edit, journal, byte-identity, and dual-model checks. Neither replay starts Cargo, rustc, the runner, or the application.

The generated application emits JSON deliberately. Its output follows the compiler records on the same stdout stream. That fixture choice does not give Cargo ownership of an arbitrary application's output format; integrations need to preserve the compiler/runtime boundary and raw child streams.

## Decisions, compatibility, and follow-up

Preserve current build-before-run admission, explicit runner execution, child status propagation, manifest/configuration separation, and invocation-directory behavior. A failed run should identify configuration, compilation, runner, or application failure using the evidence actually available. A generic exit 101 alone does not identify the phase. A build-finished success event describes compilation, not the eventual whole-command outcome.

The runner-priority mismatch is a bounded defect relative to the inspected documented expectation. A candidate correction should resolve both typed value and definition under the same priority rule. Review the existing nonmergeable-list helper and its callers, preserving mergeable arrays, per-item definitions, environment syntax, and relative-root semantics. Avoid a runner-only string patch or another configuration framework.

Before adoption, test scalar and array CLI runners against environment values, repeated CLI overrides, explicit configuration-file origins, empty/invalid explicit values, and neighboring nonmergeable consumers. Relative paths need controls that independently establish which origin supplied the actual program. Changing conflicting-runner priority changes observed behavior even if it restores the documented rule; downstream wrappers that rely on the current environment override need review. Unsetting the environment runner for an explicit CLI invocation is the observed-profile keep-current alternative. No upstream issue, patch, release, or current-upstream defect claim is made here.

For empack and other frontends, keep effective configuration, build selection, retained artifact identity, runtime launch, and final outcome separate. Reuse existing phase and source facts; do not label every nonzero process status a compilation error or launch retained bytes after a failed current preparation. This band selects no production API or implementation change.

General source resolution, build-script/proc-macro execution, arbitrary quoting, cfg-runner conflicts, foreign targets, runner-spawn errors, cancellations, descendant containment, remote execution, and other hosts remain unqualified. The larger nine-application study and parent operation/scenario statuses remain unchanged.
