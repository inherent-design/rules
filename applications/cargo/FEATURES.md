# Cargo: feature requests and compilation contexts

This is an intermediate native/source record. The role/default/target models and formal replay are still pending. No inventory operation is promoted, and no production change is selected.

The fixture uses the pinned Cargo 1.92.0 source revision `344c4567c634a25837e3c3476aac08af84cf9203` and its recorded Rust compiler on macOS arm64. It extends the earlier [normal-feature band](README.md) and [workspace-selection band](WORKSPACES.md) with build/development roles, root defaults, dependency defaults, and resolver versions. It does not replace those earlier profiles or qualify the full resolver.

## Captured boundary

The [collector](features_probe.py) creates three local path-only packages: an app, a feature-reporting library, and a sibling that requests the library's defaults. The app uses that same library as a normal, build, development, and Windows-conditional dependency. Its manifest also forwards `extra` and `explicit` features by the dependency's TOML name. A build script captures the host library's flags; the app and its test executable report the normal library's flags and that captured value.

The [receipt](../evidence/cargo-features-20261124T181357949100Z/receipt.json) records tool hashes/versions, source configurations, actual commands, environment, source/lock observations, and ownership. Fifty-one commands include nine metadata queries, twenty builds/tests followed by twenty direct executions, one resolver-1 refusal, and owned target cleanup. The [artifact records](../evidence/cargo-features-20261124T181357949100Z/binaries.json) retain executable digests and compiler messages measured before cleanup. No registry or user project is used.

One target directory is reused across the whole fixture. Its peak allocation was 15,748 KiB, and `cargo clean` removed it. The retained executable paths are historical; the executables are no longer available there. Source/configuration and observed outputs remain. The earlier [partial capture](../evidence/cargo-features-20261124T181210814499Z/disposition.json) retains a refused qualified-feature request and its successful preceding observations. Its retired private work was moved on the same volume after verifying 69 files/links, bytes, modes, sizes, and modification times.

## Observed compilation features

The named tags below are ordinary fixture features, not compiler CPU features. `platform` is requested by the Windows-conditional declaration, while all executed programs run on this Mac. Feature arrays are reported by Cargo; the role labels are supported by the controlled declarations and build-script/runtime witnesses, not an invented JSON `UnitKind` field.

| Request from the app directory            | Resolver 1: normal and build library                        | Resolvers 2 and 3: normal library | Resolvers 2 and 3: build library |
| ----------------------------------------- | ----------------------------------------------------------- | --------------------------------- | -------------------------------- |
| Default app build                         | `normal, build, dev, platform, extra`                       | `normal, extra`                   | `build, extra`                   |
| App without root defaults                 | `normal, build, dev, platform`                              | `normal`                          | `build`                          |
| App without defaults, enabling `explicit` | `normal, build, dev, platform, explicit`                    | `normal, explicit`                | `build, explicit`                |
| App with all its features                 | `normal, build, dev, platform, extra, explicit`             | `normal, extra, explicit`         | `build, extra, explicit`         |
| Workspace build without defaults          | `normal, build, dev, platform, default, defaulted, sibling` | `normal, default, defaulted`      | `build`                          |
| App tests without defaults                | `normal, build, dev, platform`                              | `normal, dev`                     | `build`                          |

These are distinct request contexts. The lock alone does not identify their compiled features. A compiler-artifact message may report a reused artifact, so this table is not a count of new compiler executions or unique units. Resolver 1 can share a library with the same feature set across roles; the mere existence of two logical uses does not prove two physical builds.

Two details matter beyond a simple “resolver 2 splits build dependencies” rule:

- **Feature forwarding follows matching dependency uses.** The app's `fixture-flags/extra` and `fixture-flags/explicit` requests reach both admitted normal and build uses. Resolver 2 keeps their declaration-specific `normal` and `build` features separate; it does not make a forwarded request normal-only. The inspected `activate_dep_feature` method iterates matching dependency names and activates the feature in each returned dependency context.
- **Disabling one default does not forbid another positive request.** The sibling's ordinary dependency still enables the library's `default` and `defaulted` features in the workspace build. Resolver 2's `--no-default-features` disables selected workspace roots' own defaults, including the sibling's `sibling` forwarding; it does not negate the sibling dependency's request for library defaults. Resolver 1's current-package scope differs.

Resolver 3 has the same feature results as resolver 2 here. Its separate Rust-version fallback policy is documented in the [source ledger](../sources/cargo-features-selections.json), but this local one-version fixture cannot qualify registry selection or MSRV fallback.

## Metadata and command scope

Every retained metadata query reports the library's broader feature union: `normal, build, dev, platform, extra, default, defaulted, sibling`. This differs from the app's selected compilation contexts. Native-host and Windows platform filters do not change that feature list in this workspace.

The same library is reachable through several dependency kinds, including an unconditional normal edge. Its retained `deps[].dep_kinds` also lists all four declarations in these queries. This is not a discriminating test of a conditional-only package being omitted by `--filter-platform`. Do not turn this result into either “the platform filter is broken” or a general metadata filtering guarantee. The metadata graph, declaration information, and a selected compiler unit have different scopes.

From the app member directory, resolver 1 refuses `--features fixture-app/explicit`, describing `fixture-app` as a missing dependency. The bare `--features explicit` succeeds there. The qualified form succeeds under resolvers 2 and 3. This is a bounded command-context observation; the fixture does not adjudicate every multi-package qualified-feature example in the documentation. The original collector's wrong success expectation is retained, not recast as a product fix.

The test target prints the observed feature values and exits successfully. Its test-summary success alone is not a feature-policy assertion. The [observation checker](features_observations.py) independently matches those values to compiler-reported library feature sets. The [retained summary](features-observations.json) preserves all twenty executed results. Formal policy comparison remains pending.

## Internal and interface direction

Preserve package identity, requested package roots, dependency kind, target condition, forwarded feature requests, activated feature context, compiler mode, and artifact evidence separately. The current `FeatureValue`, `FeaturesFor`, `CliFeatures`, and `UnitInner` boundaries already express relevant distinctions. Reuse them instead of maintaining a second global feature resolver in a frontend.

For consumers of Cargo, bind a report to its exact command, working/manifest context, resolver, feature options, target, and build/test mode. Label metadata as the resolved graph rather than the compiled unit's feature set. A single package can have several feature contexts without becoming several package identities. Preserve opaque package IDs rather than parsing display names or paths as identity.

Cargo's existing feature documentation and `cargo tree` inspection options are useful keep-current alternatives. A tool that needs per-unit facts can retain compiler-artifact messages and actual build-script/runtime evidence where appropriate. Review those existing surfaces before proposing a new flag or duplicating their policies. A generated command should not casually substitute qualified and bare feature syntax across legacy resolver contexts.

For empack's current/0.9 design, retain recipe/side/runtime/request context alongside exact selection. A broader saved graph does not establish readiness for a particular artifact or host operation. Cargo's additive feature defaults must not be copied into unrelated negative constraints such as exact pins or ownership policies merely because both use Boolean fields.

## Remaining work

Model the selected declaration and forwarding graph, role admission, positive default contributions, CLI context, metadata scope, and observed compiler/runtime projections in Lean and Bend. Keep the metadata constant-union observations as a bounded scope counterexample, not conformance of the complete metadata resolver. Include malformed research inputs and explain the premises of any set/identity laws.

Optional/weak features, renamed dependencies, proc-macros, artifact dependencies, conditional-only packages, actual Windows/cross-target compilation, target CPU features, arbitrary defaults/membership, registry/version/MSRV selection, concurrency, compiler/cache failures, and general fingerprint/ABI behavior remain pending. The binary reports the pinned Cargo source commit, but this study does not rebuild Cargo or prove its complete implementation. No whole feature family or joined workspace workflow is qualified yet.
