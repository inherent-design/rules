# Cargo: preserve unit context and report surviving effects

Keep Cargo's package and compiler-unit model, configuration interpreter, and build-before-run admission. The recorded correctness issues belong to binary publication/result composition and configuration value/provenance selection. Correct those owners rather than introduce another resolver, build scheduler, or generic transaction manager.

This review uses Cargo 1.92.0 on macOS arm64 and source `344c4567c634a25837e3c3476aac08af84cf9203`. The [source ledger](../sources/cargo-architecture-selections.json) separates fresh inspection from reused earlier selections. Matching pinned tools and source behavior does not prove a reproducible source-to-binary build. Current upstream status has not been reviewed.

## Values, owners, and interfaces

| Boundary | Current values and owners | Target direction |
| --- | --- | --- |
| Package and source | `PackageId`, `SourceId`, lock resolution, and source acquisition | Preserve logical identity versus precise source selection and opaque external IDs. A lock is not complete build-input evidence. |
| Workspace and features | Request roots, workspace discovery, `CliFeatures`, `FeaturesFor`, and `UnitInner` | Carry the selection and compiler context with inspection. Do not flatten workspace metadata into a per-unit feature claim. |
| Configuration | `Value<T>`, `Definition`, `StringList`, and `PathAndArgs` | Select the winning typed value and its actual origin together through existing helpers. |
| Build and execution | Compilation result, artifacts, runner, harness/application, and child result | Preserve separate phase facts and raw child streams. A successful build is not successful execution. |
| Installed binaries | `InstallablePackage`, `Transaction`, `InstallTracker`, staged paths, and successful-bin set | Compose operation errors independently of tracking mode; make cleanup agree with surviving ownership and report per-binary effects. |

The proposed [contract records](architecture-targets.json) are research decisions, not a new Cargo SDK or serialized result schema. Existing models and native reports retain their own limits.

## Reproduced untracked replacement failure

A fresh dependency-free two-binary crate has an owned directory blocking binary A and no binary B. Without force, `cargo install --no-track` refuses and preserves the install root. With `--no-track --force`, compilation succeeds, B is installed, and replacing A fails. Cargo nevertheless exits **0** and prints **“Replaced”** for A. A remains the same directory with its marker intact. An independently launched B prints the expected fixture value.

The same source, target, and blocker shape in a separate tracked root returns **101** for the failed replacement. New B is then removed by cleanup even though tracking lists it. This tracked control also reproduces the previously recorded [mixed-new/replacement registration mismatch](../cargo-install/README.md); it is not a new general rollback claim.

The [six-command capture](../evidence/cargo-install-no-track-20261126T092200557280Z/receipt.json), [command images](../evidence/cargo-install-no-track-20261126T092200557280Z/commands.json), and [collector](../cargo-install/no_track_probe.py) retain the version read, refusal, two installation cases, fresh B execution, and tracked listing. All owned groups retired. Only generated source and private install/configuration/target roots were used; no user installation or desktop was involved.

The selected source stores the replacement error in `replace_result`, but propagates it only inside `if let Some(tracker)`. The untracked path reaches `installed.success()` and ordinary installed/replaced summaries without checking that result. `--force` permits the collision; it does not make a failed replacement successful. Disabling tracking legitimately removes registration and concurrency protection, not the obligation to report an operation error.

This is a bounded executable-boundary defect in the selected version. A focused correction should propagate the replacement outcome outside the tracking-only branch and render replacement success from confirmed per-binary effects. No new option is needed to make a failed replacement fail. Existing scripts may observe a formerly false success becoming nonzero; document that compatibility correction. New structured partial-result fields can remain opt-in or versioned.

## Tracking and cleanup need a separate publication decision

The earlier native mismatch shows why simply propagating another error is insufficient for all tracked cases. `Transaction` holds newly installed paths, not backups of successful replacements. Its drop removes those new paths unless `success()` disarms it. The tracked path can save successful-bin ownership and then return the replacement error, causing cleanup to remove a newly registered binary. Existing successful replacements can legitimately remain despite command failure.

Retaining successfully published new binaries after confirmed ownership publication is the existing finite candidate. Registering only post-cleanup survivors is an alternative. Choose and qualify one at this owner; do not promise whole-install rollback. Preserve exact package/source ownership, force admission, ordinary partial replacement, and unrelated files. `list` describes registration, while uninstall uses that registration as authority; neither currently authenticates arbitrary changed executable bytes.

Fresh source inspection adds two constraints to that choice:

1. When tracking save fails but `replace_result` is successful, the current error branch adds context to an `Ok` result and can continue. The completion model records this source interpretation. No complete Cargo metadata-write failure has been induced here.
2. `InstallTracker::save` writes v1 and then v2, using separate seek/truncate/write operations. A failed save can leave partial metadata. Future loading synchronizes v2 from v1. A failed method return therefore does not establish that no ownership was saved, and a successful return alone does not establish crash durability.

Keep replacement and metadata-write errors independently available. Before cleanup, determine which ownership effects are confirmed, failed, or uncertain; preserve uncertain backing for explicit reconciliation rather than blindly deleting possibly registered files. A Boolean “saved” marker or moving one cleanup call cannot supply that evidence. The production correction must inspect both metadata formats, orphan cleanup, old/new clients, and the actual write/cleanup order. No new journal or repository format is selected by this review.

The [completion models](../cargo-install/Completion.lean) ([Bend](../cargo-install/Completion.bend)) isolate result composition after a new binary was published and a replacement requested. Two native cases compare command failure, new-file survival, and the replacement headline. Six finite cases also examine source-interpreted tracking outcomes. Proposed error/headline rules are model-only; they neither implement cleanup nor prove metadata atomicity. The older install model explicitly assumed successful tracking writes and remains unchanged.

Ten Lean and nine Bend laws pass. The [retained replay](../cargo-install/no_track_conformance.py) checks six measured completion fields, seven decoder refusals, and three changed-observation controls. It does not invoke Cargo, rustc, or a fixture executable. With pinned `LEAN` and `BEND`, run `python3 applications/cargo-install/no_track_conformance.py`; `--public-only` explicitly excludes installed-tool, current owned-install-content, and current known-source-file readbacks. Public and owner-local results agree after accounting for those exclusions. [Qualification](../evidence/cargo-install-no-track-20261126T092200557280Z/qualification.json).

## Keep configuration values and definitions together

The [run/configuration study](RUN-CONFIG.md) reproduces an environment runner winning over an explicit CLI runner, while an ordinary scalar control obeys the documented CLI priority. `PathAndArgs` obtains its program and arguments through `Value<StringList>`. The selected list path can replace elements from the environment while the separately deserialized definition follows a higher-priority origin. Relative-path consequences are source-only, not a reproduced native case.

Resolve the effective nonmergeable value and its `Definition` as one decision in the existing configuration helpers. Preserve mergeable arrays, per-item origins, environment syntax, empty/invalid-value handling, and configuration-relative paths. Review neighboring nonmergeable consumers before changing a shared helper; credential-provider or browser calls were not tested. A runner-only string override or second configuration evaluator would leave the ownership problem elsewhere.

Changing the conflicting runner's winner restores the documented rule but changes observed behavior. Keep current formats and CLI syntax, test scalar/array and relative origins, and review wrappers that rely on the old environment override. Explicitly removing the environment override is the existing profile's keep-current alternative.

## Inspection, execution, and staged compatibility

Preserve the context distinctions established by [workspaces](WORKSPACES.md), [features](FEATURES.md), [lock/source policy](LOCK-SOURCES.md), [freshness](FRESHNESS.md), and [test execution](TESTING.md). Existing metadata and compiler events have different scopes. Declared build-script inputs do not automatically include every actual read. A retained executable does not authorize running it after the current build fails. Test executable completion does not prove every body ran or that its assertions were meaningful.

An integration needing more context should retain the effective manifest/workspace, selected roots, feature roles, target/profile/mode, source basis, and observed phase outcomes. Reuse Cargo's existing types and outputs; public package IDs stay opaque. Preserve stdout from an arbitrary child separately from Cargo-owned JSON events. A consumer keyed only by a workspace path or lock can reuse the wrong context without Cargo's underlying policy being defective.

Apply changes in bands:

1. Fix demonstrated completion and ownership inconsistencies at their current owners. Compare normal successful installs, tracked partial replacement, untracked failure, and duplicate refusal independently.
2. Qualify tracking-save failures, cleanup failure, orphan handling, interruption, concurrent roots, and Windows replacement before asserting stronger recovery. Keep both existing tracking formats; no saved-state rewrite is required for truthful error propagation alone.
3. Correct configuration value/origin selection with its caller matrix and documented behavior change. Preserve build/run and invocation-directory contracts.
4. Add an opt-in/versioned inspection or result view only where existing interfaces cannot carry the needed facts. The existing metadata, tree, compiler-event, and diagnostic surfaces remain reasonable when a caller uses their scope correctly.

The broader Cargo and nine-application study remains incomplete. Registry/Git installation freshness, general source/feature solving, arbitrary scripts and extensions, all platforms, runtime containment, crash recovery, and production adoption retain their stated obligations. No upstream report or production patch has been made.
